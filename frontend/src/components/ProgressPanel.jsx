const ICON = { running: '◐', success: '✓', error: '✕' }

/** Live (polled) view of whichever Canvas fetch is running right now, or
 * the most recently finished one — same data regardless of whether it was
 * triggered by a button click here or the hourly launchd job in the
 * background. See main.py's progress_start/progress_step/progress_done. */
export default function ProgressPanel({ progress }) {
  if (!progress || progress.steps.length === 0) return null

  return (
    <div className="progress-panel">
      <div className="progress-head">
        <span className={`progress-dot ${progress.running ? 'running' : 'done'}`} />
        <span className="progress-label">{progress.label ?? '抓取進度'}</span>
        {!progress.running && <span className="progress-done-tag">已完成</span>}
      </div>
      <ul className="progress-steps">
        {progress.steps.map((s, i) => (
          <li key={i} className={`progress-step ${s.status}`}>
            <span className="progress-icon">{ICON[s.status] ?? '·'}</span>
            <span className="progress-name">{s.name}</span>
            {s.detail && <span className="progress-detail">{s.detail}</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}
