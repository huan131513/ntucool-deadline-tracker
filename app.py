#!/usr/bin/env python3
"""
NTUCOOL Deadline Dashboard — a tiny local web UI on top of main.py.

Run it: python3 app.py, then open http://localhost:5050
Click "重新整理" to trigger a fresh Canvas fetch (reads your Chrome cookie,
same as the scheduled main.py run) and see the result on the page.

Only meant to run on your own machine — it reads your local Chrome's cookie
store, same constraint as main.py's "chrome" auth mode.
"""
import json
from datetime import datetime, timezone

from flask import Flask, redirect, render_template_string, url_for

from main import BASE_DIR, AuthError, ConfigError, collect_exams, collect_upcoming_assignments, load_config

app = Flask(__name__)
DATA_PATH = BASE_DIR / "dashboard_data.json"


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
        snapshot = {
            **prev,
            "last_refresh": now_str,
            "ok": False,
            "error": str(e),
        }
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


@app.route("/")
def index():
    snapshot = load_snapshot()
    return render_template_string(TEMPLATE, **build_view(snapshot))


@app.route("/refresh", methods=["POST"])
def refresh():
    do_refresh()
    return redirect(url_for("index"))


KIND_LABEL = {"quiz": "測驗", "event": "行事曆", "new_quiz": "測驗"}


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
                "kind_label": KIND_LABEL.get(e.get("kind"), ""),
                "sort_key": days_left,
            }
        )
    rows.sort(key=lambda r: r["sort_key"])
    return rows


def build_view(snapshot):
    if snapshot is None:
        return {
            "has_data": False, "ok": None, "error": None, "last_refresh": None,
            "rows": [], "exam_rows": [], "hints": [],
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
        "rows": _urgency_rows(snapshot.get("assignments", [])),
        "exam_rows": _urgency_rows(snapshot.get("exams", [])),
        "hints": hints,
    }


TEMPLATE = """
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NTUCOOL 截止面板</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root{
  --bg:#f6f3ec; --raise:#ffffff; --ink:#1c231f; --ink-soft:#52584f; --ink-faint:#8b9086;
  --line:#dcd6c8; --accent:#1f5c42; --accent-soft:#e4ede2;
  --crit:#b3412c; --crit-soft:#f7e2dd; --soon:#a15a1f; --soon-soft:#f3e6d5; --past:#7a7166; --past-soft:#e9e4d8;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#141a16; --raise:#1b2320; --ink:#eef1ea; --ink-soft:#a9b0a4; --ink-faint:#6c756c;
    --line:#2c352f; --accent:#6fbd93; --accent-soft:#1f2e26;
    --crit:#e08a76; --crit-soft:#33201c; --soon:#d9a15f; --soon-soft:#2c2419; --past:#8a8f85; --past-soft:#242a24;
  }
}
*{ box-sizing:border-box; }
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:'IBM Plex Sans', -apple-system, 'Noto Sans TC', sans-serif;
}
.wrap{ max-width:820px; margin:0 auto; padding:44px 24px 64px; display:flex; flex-direction:column; gap:26px; }
header{ display:flex; justify-content:space-between; align-items:flex-end; gap:16px; flex-wrap:wrap; }
h1{
  font-family:'Fraunces', 'Noto Serif TC', serif; font-weight:700; font-size:clamp(24px,3.4vw,32px);
  margin:0; letter-spacing:-.01em;
}
.meta{ font-family:'IBM Plex Mono', monospace; font-size:12.5px; color:var(--ink-faint); margin-top:6px; }
button{
  font-family:'IBM Plex Sans', sans-serif; font-weight:600; font-size:14.5px;
  background:var(--accent); color:var(--accent-soft); border:none; border-radius:10px;
  padding:11px 20px; cursor:pointer; box-shadow:0 1px 2px rgba(0,0,0,.08);
}
button:hover{ filter:brightness(1.08); }
button:active{ filter:brightness(.96); }

.status{
  display:flex; align-items:center; gap:10px;
  background:var(--raise); border:1px solid var(--line); border-radius:12px; padding:14px 18px;
  font-size:14px;
}
.dot{ width:9px; height:9px; border-radius:50%; flex-shrink:0; }
.dot.ok{ background:var(--accent); }
.dot.bad{ background:var(--crit); }
.dot.none{ background:var(--ink-faint); }
.status .err{ color:var(--crit); }

table{ width:100%; border-collapse:collapse; background:var(--raise); border:1px solid var(--line); border-radius:14px; overflow:hidden; }
thead th{
  text-align:left; font-family:'IBM Plex Mono', monospace; font-size:11.5px; letter-spacing:.06em;
  text-transform:uppercase; color:var(--ink-faint); font-weight:600; padding:12px 16px; border-bottom:1px solid var(--line);
}
tbody td{ padding:13px 16px; border-bottom:1px solid var(--line); font-size:14.5px; vertical-align:top; }
tbody tr:last-child td{ border-bottom:none; }
tbody tr:hover{ background:var(--accent-soft); }
.course{ color:var(--ink-soft); font-size:13px; }
.pill{
  font-family:'IBM Plex Mono', monospace; font-size:12px; font-weight:600;
  padding:3px 9px; border-radius:20px; white-space:nowrap; display:inline-block;
}
.pill.critical{ color:var(--crit); background:var(--crit-soft); }
.pill.soon{ color:var(--soon); background:var(--soon-soft); }
.pill.past{ color:var(--past); background:var(--past-soft); }
.pill.normal{ color:var(--ink-soft); background:var(--accent-soft); }
a.link{ color:var(--accent); text-decoration:none; font-size:13px; }
a.link:hover{ text-decoration:underline; }
.empty{ padding:32px 20px; text-align:center; color:var(--ink-faint); font-size:14px; }
table{ overflow-x:auto; display:block; }
@media(min-width:1px){ table{ display:table; } .wrap{ overflow-x:auto; } }

.section-head{ display:flex; align-items:baseline; gap:9px; }
.section-head h2{
  font-family:'Fraunces', serif; font-weight:600; font-size:19px; margin:0;
}
.section-head .count{ font-family:'IBM Plex Mono', monospace; font-size:12px; color:var(--ink-faint); }
.kind-tag{
  font-family:'IBM Plex Mono', monospace; font-size:10.5px; letter-spacing:.04em;
  color:var(--ink-faint); background:var(--accent-soft); border-radius:5px; padding:1px 6px; margin-right:6px;
}

.hint-list{ display:flex; flex-direction:column; gap:10px; }
.hint{
  background:var(--raise); border:1px solid var(--line); border-left:3px solid var(--soon);
  border-radius:0 10px 10px 0; padding:12px 16px; font-size:13.5px;
}
.hint .h-top{ display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; }
.hint .h-title{ font-weight:600; }
.hint .h-meta{ color:var(--ink-faint); font-size:12px; font-family:'IBM Plex Mono', monospace; white-space:nowrap; }
.hint .h-kw{ color:var(--soon); font-size:12px; margin-top:3px; }
.disclaimer{ font-size:12.5px; color:var(--ink-faint); margin-top:-6px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>NTUCOOL 截止面板</h1>
      {% if last_refresh %}<div class="meta">上次更新 {{ last_refresh }}</div>{% endif %}
    </div>
    <form method="post" action="/refresh">
      <button type="submit">↻ 重新整理</button>
    </form>
  </header>

  {% if not has_data %}
    <div class="status"><span class="dot none"></span> 還沒有資料,點右上角「重新整理」抓一次。</div>
  {% elif ok %}
    <div class="status"><span class="dot ok"></span> Canvas 連線正常</div>
  {% else %}
    <div class="status"><span class="dot bad"></span> <span class="err">{{ error }}</span></div>
  {% endif %}

  {% if has_data %}
  <section>
    <div class="section-head"><h2>作業</h2><span class="count">{{ rows|length }}</span></div>
  </section>
  {% if rows %}
  <table>
    <thead><tr><th>作業</th><th>截止時間</th><th>剩餘</th></tr></thead>
    <tbody>
      {% for r in rows %}
      <tr>
        <td>
          {% if r.html_url %}<a class="link" href="{{ r.html_url }}" target="_blank">{{ r.name }}</a>{% else %}{{ r.name }}{% endif %}
          <div class="course">{{ r.course }}</div>
        </td>
        <td>{{ r.due_str }}</td>
        <td><span class="pill {{ r.urgency }}">{{ r.days_str }}</span></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% elif ok %}
    <div class="empty">目前所有課程都沒有設截止日的作業。</div>
  {% endif %}

  <section>
    <div class="section-head"><h2>考試</h2><span class="count">{{ exam_rows|length }}</span></div>
  </section>
  {% if exam_rows %}
  <table>
    <thead><tr><th>考試 / 測驗</th><th>時間</th><th>剩餘</th></tr></thead>
    <tbody>
      {% for r in exam_rows %}
      <tr>
        <td>
          <span class="kind-tag">{{ r.kind_label }}</span>
          {% if r.html_url %}<a class="link" href="{{ r.html_url }}" target="_blank">{{ r.name }}</a>{% else %}{{ r.name }}{% endif %}
          <div class="course">{{ r.course }}</div>
        </td>
        <td>{{ r.due_str }}</td>
        <td><span class="pill {{ r.urgency }}">{{ r.days_str }}</span></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% elif ok %}
    <div class="empty">來自 Canvas 測驗(New Quizzes)與行事曆事件,目前查無資料。</div>
  {% endif %}

  <section>
    <div class="section-head"><h2>公告中可能提到的考試</h2><span class="count">{{ hints|length }}</span></div>
    <div class="disclaimer">關鍵字比對公告文字,不是結構化資料,請自行點進去確認日期是否正確。</div>
  </section>
  {% if hints %}
  <div class="hint-list">
    {% for h in hints %}
    <div class="hint">
      <div class="h-top">
        <span class="h-title">
          {% if h.html_url %}<a class="link" href="{{ h.html_url }}" target="_blank">{{ h.title }}</a>{% else %}{{ h.title }}{% endif %}
        </span>
        <span class="h-meta">{{ h.course }} · {{ h.posted_str }}</span>
      </div>
      <div class="h-kw">命中關鍵字:「{{ h.matched_keyword }}」</div>
    </div>
    {% endfor %}
  </div>
  {% elif ok %}
    <div class="empty">最近的公告裡沒有掃到考試相關字眼。</div>
  {% endif %}
  {% endif %}
</div>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
