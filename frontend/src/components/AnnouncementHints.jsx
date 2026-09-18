/** Generic low-confidence keyword-hit list — used for both "公告中可能提到
 * 的考試" (announcement exam-keyword scan) and "課程首頁可能提到的作業"
 * (course Home-page assignment-keyword scan). Same shape either way:
 * {course, title, posted_at/posted_str, html_url, matched_keyword}. */
export default function AnnouncementHints({ title, disclaimer, hints, ok }) {
  return (
    <>
      <section className="section-head-wrap">
        <div className="section-head">
          <h2>{title}</h2>
          <span className="count">{hints?.length ?? 0}</span>
        </div>
        <div className="disclaimer">{disclaimer}</div>
      </section>

      {hints && hints.length > 0 ? (
        <div className="hint-list">
          {hints.map((h, i) => (
            <div className="hint" key={i}>
              <div className="h-top">
                <span className="h-title">
                  {h.html_url ? (
                    <a className="link" href={h.html_url} target="_blank" rel="noreferrer">
                      {h.title}
                    </a>
                  ) : (
                    h.title
                  )}
                </span>
                <span className="h-meta">
                  {h.course} · {h.posted_str}
                </span>
              </div>
              <div className="h-kw">命中關鍵字:「{h.matched_keyword}」</div>
            </div>
          ))}
        </div>
      ) : ok ? (
        <div className="empty">無資料</div>
      ) : null}
    </>
  )
}
