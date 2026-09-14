import { useEffect, useState } from 'react'

// Rows don't carry a stable numeric id from the API, but html_url is a
// unique Canvas link when present; fall back to a composite key for the
// rare row without one (e.g. a calendar-event exam with no link).
function rowKey(r) {
  return r.html_url || `${r.course}|${r.name}|${r.due_str}`
}

function loadSeen(storageKey) {
  try {
    const raw = localStorage.getItem(storageKey)
    return raw ? new Set(JSON.parse(raw)) : new Set()
  } catch {
    return new Set() // private browsing / storage disabled — just treat everything as new
  }
}

function saveSeen(storageKey, keys) {
  try {
    localStorage.setItem(storageKey, JSON.stringify(keys))
  } catch {
    // ignore — worst case the red dot just doesn't persist across reloads
  }
}

/** Tracks whether any row in `rows` is one the user hasn't "seen" yet
 * (localStorage-backed per browser, not per Canvas account) — drives the
 * red dot on the 作業/考試 section headings. Call markSeen() to clear it,
 * e.g. when the user clicks into that section. */
export function useSeenTracker(rows, storageKey) {
  const [hasNew, setHasNew] = useState(false)

  useEffect(() => {
    if (!rows) return
    const seen = loadSeen(storageKey)
    setHasNew(rows.some((r) => !seen.has(rowKey(r))))
  }, [rows, storageKey])

  const markSeen = () => {
    if (!rows) return
    saveSeen(storageKey, rows.map(rowKey))
    setHasNew(false)
  }

  return { hasNew, markSeen }
}
