function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/** Overview of every active course and how many upcoming (not-past-due)
 * assignments/exams each one has right now — counts come pre-computed
 * from the backend (app.py's do_refresh) so this stays purely
 * presentational, same pattern as the deadline tables below it.
 *
 * Clicking the card itself opens that course's NTUCOOL page. The two
 * count pills sit on top of that same click target, so they stopPropagation
 * and instead scrollIntoView to the matching 作業/考試 section below (see
 * the id="assignments-section"/"exams-section" targets in App.jsx). */
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
          <div
            className={`course-card${c.html_url ? ' course-card-link' : ''}`}
            key={c.name}
            onClick={() => c.html_url && window.open(c.html_url, '_blank', 'noopener')}
          >
            <div className="course-card-name">{c.name}</div>
            <div className="course-card-counts">
              <button
                type="button"
                className={`course-count ${c.assignment_count > 0 ? 'has' : ''}`}
                onClick={(e) => {
                  e.stopPropagation()
                  scrollToSection('assignments-section')
                }}
              >
                作業 {c.assignment_count}
              </button>
              <button
                type="button"
                className={`course-count ${c.exam_count > 0 ? 'has' : ''}`}
                onClick={(e) => {
                  e.stopPropagation()
                  scrollToSection('exams-section')
                }}
              >
                考試 {c.exam_count}
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
