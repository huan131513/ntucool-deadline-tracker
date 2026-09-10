const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']
// Any given day's dot uses whichever item on it is most urgent — reuses
// the urgency classes already computed server-side (see app.py's
// _urgency_rows), so the color language stays consistent with the
// tables below.
const URGENCY_PRIORITY = { critical: 0, soon: 1, past: 2, normal: 3 }

function buildMonthGrid(year, month) {
  const startWeekday = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells = Array(startWeekday).fill(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  return cells
}

function collectDueDates(rows) {
  const map = {}
  for (const r of rows || []) {
    if (!r.due_str || r.due_str.length < 10) continue
    const dateKey = r.due_str.slice(0, 10)
    if (!map[dateKey] || URGENCY_PRIORITY[r.urgency] < URGENCY_PRIORITY[map[dateKey]]) {
      map[dateKey] = r.urgency
    }
  }
  return map
}

export default function MiniCalendar({ assignments, exams }) {
  const today = new Date()
  const year = today.getFullYear()
  const month = today.getMonth()
  const cells = buildMonthGrid(year, month)
  const dueMap = collectDueDates([...(assignments ?? []), ...(exams ?? [])])
  const todayKey = today.toISOString().slice(0, 10)

  return (
    <div className="mini-cal">
      <div className="cal-header">
        {year}{'年'}{month + 1}{'月'}
      </div>
      <div className="cal-weekdays">
        {WEEKDAYS.map((w) => (
          <span key={w} className="cal-weekday">
            {w}
          </span>
        ))}
      </div>
      <div className="cal-grid">
        {cells.map((d, i) => {
          if (d === null) return <div key={i} className="cal-cell" />
          const dateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
          const urgency = dueMap[dateKey]
          return (
            <div key={i} className="cal-cell">
              <span className={`cal-day-num${dateKey === todayKey ? ' cal-today' : ''}`}>{d}</span>
              {urgency && <span className={`cal-dot ${urgency}`} />}
            </div>
          )
        })}
      </div>
    </div>
  )
}
