import { useCallback, useState } from 'react'

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

function saveSeen(storageKey, set) {
  try {
    localStorage.setItem(storageKey, JSON.stringify([...set]))
  } catch {
    // ignore — worst case the red dot just doesn't persist across reloads
  }
}

/** Per-row "seen" tracking (localStorage-backed per browser, not per Canvas
 * account) — each 作業/考試 row gets its own red dot until markSeen(row) is
 * called for it (e.g. the user clicks that row), rather than one dot for
 * the whole section. */
export function useSeenTracker(storageKey) {
  const [seen, setSeen] = useState(() => loadSeen(storageKey))

  const isNew = useCallback((row) => !seen.has(rowKey(row)), [seen])

  const markSeen = useCallback(
    (row) => {
      const key = rowKey(row)
      if (seen.has(key)) return
      const next = new Set(seen)
      next.add(key)
      setSeen(next)
      saveSeen(storageKey, next)
    },
    [seen, storageKey]
  )

  return { isNew, markSeen }
}
