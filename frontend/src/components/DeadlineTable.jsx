const KIND_LABEL = { quiz: '測驗', event: '行事曆', new_quiz: '測驗' }

/** Shared table for both the "作業" and "考試" sections — same row shape
 * comes back from /api/state for both (see app.py's _urgency_rows).
 * showCompleted adds a 已完成/未完成 column. r.completed is null for rows
 * with no real per-user submission status to report (classic quizzes,
 * calendar events) — those show "—" rather than a guessed 未完成.
 *
 * `id` gives the section a scroll target (the 課程 panel's 作業/考試 pills
 * jump here). `isNew`/`onRowSeen` drive a red dot per row — each
 * assignment/exam gets its own, not one for the whole section — see
 * useSeenTracker.js for how "new" is decided and cleared. `isPdfGuessDone`/
 * `onTogglePdfGuess` back a manual 已完成/未完成 pill for r.source ===
 * "pdf_guess" rows — those were never a real Canvas Assignment, so there's
 * no submission status to read (see usePdfGuessStatus.js). */
export default function DeadlineTable({
  id,
  title,
  itemLabel,
  rows,
  emptyText,
  showKind,
  showCompleted,
  ok,
  isNew,
  onRowSeen,
  isPdfGuessDone,
  onTogglePdfGuess,
}) {
  return (
    <section id={id} className="deadline-section">
      <div className="section-head-wrap">
        <div className="section-head">
          <h2>{title}</h2>
          <span className="count">{rows?.length ?? 0}</span>
        </div>
      </div>

      {rows && rows.length > 0 ? (
        <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{itemLabel}</th>
              <th>{showKind ? '時間' : '截止時間'}</th>
              <th>剩餘</th>
              {showCompleted && <th>狀態</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={i}
                className={r.html_url ? 'row-link' : ''}
                onClick={() => {
                  onRowSeen?.(r)
                  if (r.html_url) window.open(r.html_url, '_blank', 'noopener')
                }}
              >
                <td>
                  {isNew?.(r) && <span className="new-dot" title="新資料" />}
                  {showKind && r.kind && <span className="kind-tag">{KIND_LABEL[r.kind] ?? ''}</span>}
                  {r.source === 'pdf_guess' && (
                    <span
                      className="kind-tag guess"
                      title="截止日期是從課程首頁附的 PDF 裡自動判讀的，不是 Canvas 正式登記的資料，可能不準，請自行點進去確認"
                    >
                      PDF 推測
                    </span>
                  )}
                  {r.html_url ? (
                    <a
                      className="link"
                      href={r.html_url}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => {
                        e.stopPropagation()
                        onRowSeen?.(r)
                      }}
                    >
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
                {showCompleted && (
                  <td>
                    {r.source === 'pdf_guess' ? (
                      <button
                        type="button"
                        className={`pill pill-toggle ${isPdfGuessDone?.(r) ? 'done' : 'todo'}`}
                        title="沒有正式的 Canvas 作業可以查完成狀態，自己點一下記錄"
                        onClick={(e) => {
                          e.stopPropagation()
                          onTogglePdfGuess?.(r)
                        }}
                      >
                        {isPdfGuessDone?.(r) ? '已完成' : '未完成'}
                      </button>
                    ) : r.completed === null || r.completed === undefined ? (
                      <span className="pill unknown">—</span>
                    ) : (
                      <span className={`pill ${r.completed ? 'done' : 'todo'}`}>
                        {r.completed ? '已完成' : '未完成'}
                      </span>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      ) : ok ? (
        <div className="empty">{emptyText}</div>
      ) : null}
    </section>
  )
}
