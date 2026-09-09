export default function AnnouncementHints({ hints, ok }) {
  return (
    <>
      <section className="section-head-wrap">
        <div className="section-head">
          <h2>公告中可能提到的考試</h2>
          <span className="count">{hints?.length ?? 0}</span>
        </div>
        <div className="disclaimer">關鍵字比對公告文字,不是結構化資料,請自行點進去確認日期是否正確。</div>
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
