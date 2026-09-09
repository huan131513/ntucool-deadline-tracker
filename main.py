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
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def log(msg, *, err=False):
    """Timestamped line for launchd.log — lets us later see exactly when auth
    started/stopped succeeding, e.g. to size how long the Chrome cookie lasts."""
    ts = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"[{ts}] {msg}", file=sys.stderr if err else sys.stdout)


def load_config():
    if not CONFIG_PATH.exists():
        sys.exit(
            f"Missing {CONFIG_PATH}.\n"
            f"Copy config.example.json to config.json and fill in your tokens first."
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
            sys.exit(
                "canvas_auth_mode is 'chrome' but the 'browser_cookie3' package isn't "
                "installed. Run: pip install browser_cookie3"
            )
        domain = cfg.get("canvas_cookie_domain", "cool.ntu.edu.tw")
        try:
            cj = browser_cookie3.chrome(domain_name=domain)
        except Exception as e:
            sys.exit(
                f"Failed to read cookies from Chrome ({e}).\n"
                f"Make sure Chrome is installed, you're logged into {domain} there, "
                f"and you approve any macOS Keychain prompt for cookie decryption."
            )
        cookie_value = "; ".join(f"{c.name}={c.value}" for c in cj)
        if not cookie_value:
            sys.exit(
                f"No cookies found for {domain} in Chrome. Log into "
                f"https://{domain} in Chrome first, then try again."
            )
        session.headers.update({"Cookie": cookie_value})
    elif auth_mode == "cookie":
        cookie_value = cfg.get("canvas_cookie", "")
        if not cookie_value:
            sys.exit("canvas_auth_mode is 'cookie' but canvas_cookie is empty in config.json.")
        session.headers.update({"Cookie": cookie_value})
    else:
        token = cfg.get("canvas_access_token", "")
        if not token:
            sys.exit("canvas_auth_mode is 'token' but canvas_access_token is empty in config.json.")
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


def collect_upcoming_assignments(cfg):
    session = build_session(cfg)

    try:
        courses = fetch_courses(session, cfg)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 419):
            log("AUTH FAILED (401/419) — Chrome cookie is no longer valid. "
                "Log into cool.ntu.edu.tw again and this will pick it back up "
                "on the next scheduled run.", err=True)
            sys.exit(1)
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

    cfg = load_config()

    if args.list:
        cmd_list(cfg)
    else:
        cmd_check(cfg, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
