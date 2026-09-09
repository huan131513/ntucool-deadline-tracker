const KIND_LABEL = { quiz: '測驗', event: '行事曆', new_quiz: '測驗' }

/** Shared table for both the "作業" and "考試" sections — same row shape
 * comes back from /api/state for both (see app.py's _urgency_rows). */
export default function DeadlineTable({ title, itemLabel, rows, emptyText, showKind, ok }) {
  return (
    <>
      <section className="section-head-wrap">
        <div className="section-head">
          <h2>{title}</h2>
          <span className="count">{rows?.length ?? 0}</span>
        </div>
      </section>

      {rows && rows.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th>{itemLabel}</th>
              <th>{showKind ? '時間' : '截止時間'}</th>
              <th>剩餘</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>
                  {showKind && r.kind && <span className="kind-tag">{KIND_LABEL[r.kind] ?? ''}</span>}
                  {r.html_url ? (
                    <a className="link" href={r.html_url} target="_blank" rel="noreferrer">
                      {r.name}
                    </a>
                  ) : (
                    r.name
                  )}
                  <div className="course">{r.course}</div>
                </td>
                <td>{r.due_str}</td>
                <td>
                  <span className={`pill ${r.urgency}`}>{r.days_str}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : ok ? (
        <div className="empty">{emptyText}</div>
      ) : null}
    </>
  )
}
