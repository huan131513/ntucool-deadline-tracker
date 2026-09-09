#!/usr/bin/env python3
"""
NTUCOOL (Canvas LMS) Assignment Deadline Reminder
--------------------------------------------------
Pulls all assignments from all your active courses via the official Canvas
REST API (no HTML scraping, no password handling — you authenticate in your
own browser and this script only ever sees a token/cookie you copy over) and
sends Telegram reminders as deadlines approach.

Setup:
    1. Copy config.example.json to config.json and fill in your values.
    2. pip install -r requirements.txt
    3. python main.py --list        # sanity-check: show all upcoming assignments
    4. python main.py               # check thresholds & send Telegram reminders
    5. Schedule it (cron / launchd) to run e.g. once a day.

See README.md for how to get a Canvas access token and a Telegram bot token.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# Free-text markers we scan announcement titles/bodies for. This is a best-
# effort heuristic, NOT a reliable data source — see fetch_announcement_hints.
EXAM_KEYWORDS = [
    "期中考", "期末考", "期中", "期末", "小考", "考試", "考卷",
    "midterm", "final exam", "final", "exam",
]

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


class ConfigError(Exception):
    """Something's wrong with config.json itself (missing/incomplete)."""


class AuthError(Exception):
    """Couldn't get an authenticated Canvas session (bad/expired cookie, etc.).

    Raised instead of calling sys.exit() directly so callers other than the
    CLI (e.g. the web dashboard) can catch it and show a friendly status
    instead of the whole process dying mid-request.
    """


def log(msg, *, err=False):
    """Timestamped line for launchd.log — lets us later see exactly when auth
    started/stopped succeeding, e.g. to size how long the Chrome cookie lasts."""
    ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"[{ts}] {msg}", file=sys.stderr if err else sys.stdout)


def load_config():
    if not CONFIG_PATH.exists():
        raise ConfigError(
            f"Missing {CONFIG_PATH}. Copy config.example.json to config.json "
            f"and fill in your values first."
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state(path):
    p = BASE_DIR / path
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"notified": {}}  # {"<assignment_id>:<threshold_days>": true}


def save_state(path, state):
    p = BASE_DIR / path
    with open(p, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def canvas_get(session, base_url, path, params=None):
    """GET from Canvas API, following pagination via the Link header."""
    url = f"{base_url}{path}"
    results = []
    while url:
        resp = session.get(url, params=params, timeout=30)
        params = None  # only needed on first request; next url already has query
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            results.extend(data)
        else:
            return data
        url = None
        for link in resp.links.values():
            if link.get("rel") == "next":
                url = link["url"]
    return results


def build_session(cfg):
    """Build a requests.Session authenticated against Canvas.

    NTUCOOL does not support Canvas's native personal access tokens, so this
    supports three modes (canvas_auth_mode in config.json):
      - "chrome": read the current session cookie straight out of your local
        Chrome's cookie store (no password, no manual copy/paste — just stay
        logged into NTUCOOL in Chrome as usual). Only works when this script
        runs on your own machine.
      - "cookie": use a session cookie string you copied manually from
        DevTools. Expires (~24h); you refresh it by hand.
      - "token": Canvas's native personal access token, for Canvas instances
        that do support it.
    This script never sees or handles your NTU password in any mode.
    """
    session = requests.Session()
    auth_mode = cfg.get("canvas_auth_mode", "token")

    if auth_mode == "chrome":
        try:
            import browser_cookie3
        except ImportError:
            raise ConfigError(
                "canvas_auth_mode is 'chrome' but the 'browser_cookie3' package isn't "
                "installed. Run: pip install browser_cookie3"
            )
        domain = cfg.get("canvas_cookie_domain", "cool.ntu.edu.tw")
        try:
            cj = browser_cookie3.chrome(domain_name=domain)
        except Exception as e:
            raise AuthError(
                f"Failed to read cookies from Chrome ({e}). Make sure Chrome is installed, "
                f"you're logged into {domain} there, and you approve any macOS Keychain "
                f"prompt for cookie decryption."
            )
        cookie_value = "; ".join(f"{c.name}={c.value}" for c in cj)
        if not cookie_value:
            raise AuthError(
                f"No cookies found for {domain} in Chrome. Log into "
                f"https://{domain} in Chrome first, then try again."
            )
        session.headers.update({"Cookie": cookie_value})
    elif auth_mode == "cookie":
        cookie_value = cfg.get("canvas_cookie", "")
        if not cookie_value:
            raise ConfigError("canvas_auth_mode is 'cookie' but canvas_cookie is empty in config.json.")
        session.headers.update({"Cookie": cookie_value})
    else:
        token = cfg.get("canvas_access_token", "")
        if not token:
            raise ConfigError("canvas_auth_mode is 'token' but canvas_access_token is empty in config.json.")
        session.headers.update({"Authorization": f"Bearer {token}"})

    session.headers.update({"Accept": "application/json"})
    return session


def fetch_courses(session, cfg):
    params = {"per_page": 100}
    if cfg.get("only_active_courses", True):
        params["enrollment_state"] = "active"
    return canvas_get(session, cfg["canvas_base_url"], "/api/v1/courses", params)


def fetch_assignments(session, cfg, course_id):
    params = {"per_page": 100, "order_by": "due_at"}
    return canvas_get(
        session, cfg["canvas_base_url"], f"/api/v1/courses/{course_id}/assignments", params
    )


def fetch_quizzes(session, cfg, course_id):
    params = {"per_page": 100}
    return canvas_get(session, cfg["canvas_base_url"], f"/api/v1/courses/{course_id}/quizzes", params)


def fetch_calendar_events(session, cfg, course_ids):
    """Course calendar entries (type=event) for the next 180 days — where a
    teacher manually adds e.g. "期中考" as an event, this is how it's caught."""
    if not course_ids:
        return []
    now = datetime.now(timezone.utc)
    params = {
        "type": "event",
        "start_date": now.date().isoformat(),
        "end_date": (now + timedelta(days=180)).date().isoformat(),
        "per_page": 100,
        "context_codes[]": [f"course_{cid}" for cid in course_ids],
    }
    return canvas_get(session, cfg["canvas_base_url"], "/api/v1/calendar_events", params)


def _strip_html(html):
    return re.sub(r"<[^>]+>", " ", html or "")


def fetch_announcement_hints(session, cfg, course_id, course_name):
    """Best-effort keyword scan over recent announcements. This is NOT a
    structured data source — a matched announcement means "go read this
    yourself", not a confirmed exam date. Never feed these into Telegram
    reminders the way real Assignment/Quiz due dates are."""
    params = {"context_codes[]": f"course_{course_id}", "per_page": 30}
    try:
        anns = canvas_get(session, cfg["canvas_base_url"], "/api/v1/announcements", params)
    except requests.HTTPError:
        return []

    hints = []
    for a in anns:
        text = f"{a.get('title', '')} {_strip_html(a.get('message', ''))}".lower()
        matched = next((kw for kw in EXAM_KEYWORDS if kw.lower() in text), None)
        if matched:
            hints.append(
                {
                    "course": course_name,
                    "title": a.get("title", "(untitled)"),
                    "posted_at": a.get("posted_at"),
                    "html_url": a.get("html_url"),
                    "matched_keyword": matched,
                }
            )
    return hints


def collect_exams(cfg):
    """Exams from the two structured Canvas sources: Quizzes and Calendar
    Events. Also runs the announcement keyword scan and returns its (low
    confidence) hits separately — see fetch_announcement_hints."""
    session = build_session(cfg)

    try:
        courses = fetch_courses(session, cfg)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 419):
            raise AuthError(
                "Canvas authentication failed (401/419). Your session cookie has "
                "probably expired — log into cool.ntu.edu.tw again in Chrome."
            )
        raise

    exams = []
    for course in courses:
        course_name = course.get("name") or course.get("course_code") or f"Course {course.get('id')}"
        try:
            quizzes = fetch_quizzes(session, cfg, course["id"])
        except requests.HTTPError as e:
            # Many Canvas instances (NTUCOOL included) have retired the legacy
            # Quizzes API in favor of New Quizzes, which surface as regular
            # graded Assignments instead — see is_quiz_assignment above. A
            # blanket 404 here just means "nothing to fetch", not an error.
            if e.response is None or e.response.status_code != 404:
                print(f"  [warn] failed to fetch quizzes for {course_name}: {e}", file=sys.stderr)
            continue
        for q in quizzes:
            due_at = q.get("due_at") or q.get("lock_at")
            if not due_at:
                continue
            exams.append(
                {
                    "id": f"quiz:{q['id']}",
                    "name": q.get("title") or "(untitled quiz)",
                    "course": course_name,
                    "due_at": datetime.fromisoformat(due_at.replace("Z", "+00:00")),
                    "html_url": q.get("html_url"),
                    "kind": "quiz",
                }
            )

    course_ids = [c["id"] for c in courses]
    course_name_by_id = {
        c["id"]: (c.get("name") or c.get("course_code") or f"Course {c['id']}") for c in courses
    }
    try:
        events = fetch_calendar_events(session, cfg, course_ids)
    except requests.HTTPError as e:
        print(f"  [warn] failed to fetch calendar events: {e}", file=sys.stderr)
        events = []
    for ev in events:
        start_at = ev.get("start_at")
        if not start_at:
            continue
        context_code = ev.get("context_code", "")
        course_id = int(context_code.split("_", 1)[1]) if context_code.startswith("course_") else None
        exams.append(
            {
                "id": f"event:{ev['id']}",
                "name": ev.get("title") or "(untitled event)",
                "course": course_name_by_id.get(course_id, "—"),
                "due_at": datetime.fromisoformat(start_at.replace("Z", "+00:00")),
                "html_url": ev.get("html_url"),
                "kind": "event",
            }
        )

    exams.sort(key=lambda x: x["due_at"])

    hints = []
    for course in courses:
        course_name = course.get("name") or course.get("course_code") or f"Course {course['id']}"
        hints.extend(fetch_announcement_hints(session, cfg, course["id"], course_name))
    hints.sort(key=lambda h: h.get("posted_at") or "", reverse=True)

    return exams, hints


def collect_upcoming_assignments(cfg):
    session = build_session(cfg)

    try:
        courses = fetch_courses(session, cfg)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 419):
            log("AUTH FAILED (401/419) — Chrome cookie is no longer valid.", err=True)
            raise AuthError(
                "Canvas authentication failed (401/419). Your session cookie has "
                "probably expired — log into cool.ntu.edu.tw again in Chrome."
            )
        raise

    log(f"AUTH OK — {len(courses)} active course(s) fetched.")
    now = datetime.now(timezone.utc)

    items = []
    for course in courses:
        course_name = course.get("name") or course.get("course_code") or f"Course {course.get('id')}"
        try:
            assignments = fetch_assignments(session, cfg, course["id"])
        except requests.HTTPError as e:
            print(f"  [warn] failed to fetch assignments for {course_name}: {e}", file=sys.stderr)
            continue

        for a in assignments:
            due_at = a.get("due_at")
            if not due_at:
                if not cfg.get("include_courses_without_due_date", False):
                    continue
                due_dt = None
            else:
                due_dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))

            items.append(
                {
                    "id": a["id"],
                    "name": a.get("name", "(untitled)"),
                    "course": course_name,
                    "due_at": due_dt,
                    "html_url": a.get("html_url"),
                    # New Quizzes (NTUCOOL's exam tool) show up here, not in the
                    # legacy /quizzes API — flagged so callers can route them
                    # into an "exams" view instead of the plain assignment list.
                    "is_quiz": bool(a.get("is_quiz_assignment")),
                    "has_submitted": bool(
                        a.get("submission", {}).get("workflow_state") not in (None, "unsubmitted")
                    ) if isinstance(a.get("submission"), dict) else None,
                }
            )

    items.sort(key=lambda x: (x["due_at"] is None, x["due_at"]))
    return items, now


def send_telegram(cfg, text):
    token = cfg["telegram_bot_token"]
    chat_id = cfg["telegram_chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=15,
    )
    if not resp.ok:
        print(f"  [warn] telegram send failed: {resp.status_code} {resp.text}", file=sys.stderr)
    return resp.ok


def cmd_list(cfg):
    items, now = collect_upcoming_assignments(cfg)
    print(f"Found {len(items)} assignments across your courses:\n")
    for it in items:
        if it["due_at"] is None:
            due_str = "(no due date)"
        else:
            delta = it["due_at"] - now
            days = delta.days
            due_str = it["due_at"].astimezone().strftime("%Y-%m-%d %H:%M") + f"  ({days:+d} days)"
        print(f"- [{it['course']}] {it['name']} — due {due_str}")


def cmd_check(cfg, dry_run=False):
    items, now = collect_upcoming_assignments(cfg)
    thresholds = sorted(cfg.get("remind_before_days", [7, 3, 1]))
    state = load_state(cfg.get("state_file", "state.json"))

    to_send = []
    for it in items:
        if it["due_at"] is None:
            continue
        days_left = (it["due_at"] - now).total_seconds() / 86400
        if days_left < 0:
            continue  # already past due, skip

        for threshold in thresholds:
            key = f"{it['id']}:{threshold}"
            if days_left <= threshold and key not in state["notified"]:
                to_send.append((key, it, threshold, days_left))
                break  # only notify for the nearest crossed threshold per run

    if not to_send:
        log("No new deadline reminders to send.")
        return

    sent_count = 0
    for key, it, threshold, days_left in to_send:
        due_str = it["due_at"].astimezone().strftime("%Y-%m-%d %H:%M")
        msg = (
            f"⏰ <b>作業截止提醒</b>\n"
            f"課程:{it['course']}\n"
            f"作業:{it['name']}\n"
            f"截止時間:{due_str}\n"
            f"剩餘:約 {days_left:.1f} 天\n"
        )
        if it.get("html_url"):
            msg += f"連結:{it['html_url']}"

        print(f"--- reminder ---\n{msg}\n")
        if dry_run:
            continue

        # Only mark as notified once Telegram actually confirms delivery —
        # a failed send (Telegram-side, not cookie-side) should retry next run.
        if send_telegram(cfg, msg):
            state["notified"][key] = True
            sent_count += 1
        else:
            log(f"Telegram send failed for '{it['name']}' — will retry next run.", err=True)

    if not dry_run and sent_count:
        save_state(cfg.get("state_file", "state.json"), state)
        log(f"Sent {sent_count} reminder(s).")


def main():
    parser = argparse.ArgumentParser(description="NTUCOOL assignment deadline reminder")
    parser.add_argument(
        "--list", action="store_true", help="List all upcoming assignments (no notifications sent)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be sent without sending or saving state"
    )
    args = parser.parse_args()

    try:
        cfg = load_config()
        if args.list:
            cmd_list(cfg)
        else:
            cmd_check(cfg, dry_run=args.dry_run)
    except (ConfigError, AuthError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
