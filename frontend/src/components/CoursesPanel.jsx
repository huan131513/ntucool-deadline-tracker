/** Overview of every active course and how many upcoming (not-past-due)
 * assignments/exams each one has right now — counts come pre-computed
 * from the backend (app.py's do_refresh) so this stays purely
 * presentational, same pattern as the deadline tables below it. */
export default function CoursesPanel({ courses }) {
  if (!courses || courses.length === 0) return null

  return (
    <section className="courses-panel">
      <div className="section-head-wrap">
        <div className="section-head">
          <h2>課程</h2>
          <span className="count">{courses.length}</span>
        </div>
      </div>
      <div className="course-grid">
        {courses.map((c) => (
          <div className="course-card" key={c.name}>
            <div className="course-card-name">{c.name}</div>
            <div className="course-card-counts">
              <span className={`course-count ${c.assignment_count > 0 ? 'has' : ''}`}>
                作業 {c.assignment_count}
              </span>
              <span className={`course-count ${c.exam_count > 0 ? 'has' : ''}`}>
                考試 {c.exam_count}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
