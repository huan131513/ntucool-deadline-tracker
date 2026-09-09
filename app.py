#!/usr/bin/env python3
"""
NTUCOOL Deadline Dashboard — JSON API backend for the React app in frontend/.

Run it: python3 app.py, then open http://localhost:5050
It serves the built frontend (frontend/dist/, produced by `npm run build`
inside frontend/) and answers the /api/* routes that frontend calls.

Only meant to run on your own machine — it reads your local Chrome's cookie
store, same constraint as main.py's "chrome" auth mode.

Frontend dev workflow (hot reload instead of rebuilding each time):
    cd frontend && npm run dev   # opens :5173, proxies /api to this server
This server itself never needs restarting for frontend-only changes.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from main import (
    BASE_DIR,
    AuthError,
    ConfigError,
    collect_exams,
    collect_upcoming_assignments,
    load_config,
    run_notification_check,
)

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
DATA_PATH = BASE_DIR / "dashboard_data.json"

app = Flask(__name__, static_folder=str(FRONTEND_DIST), static_url_path="")


# ---------------------------------------------------------------- snapshot --

def load_snapshot():
    if DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_snapshot(snapshot):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def do_refresh():
    """Trigger the same chrome-cookie → Canvas API fetch main.py does, and
    persist the result so the dashboard has something to show on next load."""
    prev = load_snapshot() or {}
    now_str = datetime.now().astimezone().isoformat()

    try:
        cfg = load_config()
        items, _now = collect_upcoming_assignments(cfg)
        exams, hints = collect_exams(cfg)
    except (ConfigError, AuthError) as e:
        snapshot = {**prev, "last_refresh": now_str, "ok": False, "error": str(e)}
        save_snapshot(snapshot)
        return snapshot

    # New Quizzes (NTUCOOL's exam tool) come back from the Assignments API
    # tagged is_quiz — route those into the exam list instead of homework.
    assignment_items = [it for it in items if not it.get("is_quiz")]
    quiz_assignments = [it for it in items if it.get("is_quiz")]

    all_exams = exams + [
        {
            "id": f"newquiz:{it['id']}",
            "name": it["name"],
            "course": it["course"],
            "due_at": it["due_at"],
            "html_url": it["html_url"],
            "kind": "new_quiz",
        }
        for it in quiz_assignments
    ]
    all_exams.sort(key=lambda x: x["due_at"] or datetime.max.replace(tzinfo=timezone.utc))

    snapshot = {
        "last_refresh": now_str,
        "ok": True,
        "error": None,
        "assignments": [
            {
                "course": it["course"],
                "name": it["name"],
                "due_at": it["due_at"].isoformat() if it["due_at"] else None,
                "html_url": it["html_url"],
            }
            for it in assignment_items
        ],
        "exams": [
            {
                "course": e["course"],
                "name": e["name"],
                "due_at": e["due_at"].isoformat() if e["due_at"] else None,
                "html_url": e["html_url"],
                "kind": e["kind"],
            }
            for e in all_exams
        ],
        "hints": hints,
    }
    save_snapshot(snapshot)
    return snapshot


# --------------------------------------------------------- view shaping ----
# Urgency/day-left math stays server-side so the frontend is purely
# presentational — it just renders whatever fields come back.

def _urgency_rows(entries):
    now = datetime.now(timezone.utc)
    rows = []
    for e in entries:
        due_at = datetime.fromisoformat(e["due_at"]) if e.get("due_at") else None
        if due_at is not None:
            days_left = (due_at - now).total_seconds() / 86400
            due_str = due_at.astimezone().strftime("%Y-%m-%d %H:%M")
            if days_left < 0:
                urgency = "past"
            elif days_left <= 1:
                urgency = "critical"
            elif days_left <= 3:
                urgency = "soon"
            else:
                urgency = "normal"
            days_str = f"{days_left:+.1f} 天"
        else:
            due_str, days_str, urgency, days_left = "(未設定)", "—", "normal", float("inf")

        rows.append(
            {
                "course": e["course"],
                "name": e["name"],
                "due_str": due_str,
                "days_str": days_str,
                "urgency": urgency,
                "html_url": e.get("html_url"),
                "kind": e.get("kind"),
                "sort_key": days_left,
            }
        )
    rows.sort(key=lambda r: r["sort_key"])
    for r in rows:
        del r["sort_key"]
    return rows


def build_state(snapshot):
    if snapshot is None:
        return {
            "has_data": False, "ok": None, "error": None, "last_refresh": None,
            "assignments": [], "exams": [], "hints": [],
        }

    last_refresh = snapshot.get("last_refresh")
    if last_refresh:
        last_refresh = datetime.fromisoformat(last_refresh).strftime("%Y-%m-%d %H:%M:%S")

    hints = []
    for h in snapshot.get("hints", []):
        posted = h.get("posted_at")
        hints.append(
            {
                **h,
                "posted_str": datetime.fromisoformat(posted).astimezone().strftime("%Y-%m-%d") if posted else "—",
            }
        )

    return {
        "has_data": True,
        "ok": snapshot.get("ok"),
        "error": snapshot.get("error"),
        "last_refresh": last_refresh,
        "assignments": _urgency_rows(snapshot.get("assignments", [])),
        "exams": _urgency_rows(snapshot.get("exams", [])),
        "hints": hints,
    }


# --------------------------------------------------------------- API -------

@app.route("/api/state")
def api_state():
    return jsonify(build_state(load_snapshot()))


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    snapshot = do_refresh()
    state = build_state(snapshot)
    state["message"] = (
        {"text": "已重新抓取 Canvas 資料。", "category": "ok"}
        if snapshot.get("ok")
        else {"text": f"抓取失敗:{snapshot.get('error')}", "category": "bad"}
    )
    return jsonify(state)


@app.route("/api/notify", methods=["POST"])
def api_notify():
    try:
        cfg = load_config()
        result = run_notification_check(cfg)
    except (ConfigError, AuthError) as e:
        return jsonify({"message": {"text": f"檢查失敗:{e}", "category": "bad"}})

    if result["sent"]:
        names = "、".join(f"{s['course']}《{s['name']}》" for s in result["sent"])
        message = {"text": f"已發送 {len(result['sent'])} 則 Telegram 提醒:{names}", "category": "ok"}
    elif result["failed"]:
        message = {"text": f"{len(result['failed'])} 則提醒發送失敗,下次會重試。", "category": "bad"}
    else:
        message = {"text": "目前沒有進入提醒門檻、且尚未通知過的項目。", "category": "ok"}
    return jsonify({"message": message})


# ------------------------------------------------------ serve built SPA ----

@app.route("/")
def index():
    if not (FRONTEND_DIST / "index.html").exists():
        return (
            "frontend/dist not found. Run: cd frontend && npm install && npm run build",
            500,
        )
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def spa(path):
    if path.startswith("api/"):
        return jsonify({"error": "not found"}), 404
    candidate = Path(app.static_folder) / path
    if candidate.is_file():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
