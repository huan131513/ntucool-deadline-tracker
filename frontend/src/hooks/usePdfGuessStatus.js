import { useCallback, useState } from 'react'

// Same key strategy as useSeenTracker.js — html_url is unique per Canvas
// item when present, otherwise fall back to a composite key.
function rowKey(r) {
  return r.html_url || `${r.course}|${r.name}|${r.due_str}`
}

function load(storageKey) {
  try {
    const raw = localStorage.getItem(storageKey)
    return raw ? new Set(JSON.parse(raw)) : new Set()
  } catch {
    return new Set()
  }
}

function save(storageKey, set) {
  try {
    localStorage.setItem(storageKey, JSON.stringify([...set]))
  } catch {
    // ignore — worst case the toggle just doesn't persist across reloads
  }
}

/** Manual 已完成/未完成 toggle for "pdf_guess" 作業 rows (see app.py's
 * do_refresh) — these were never registered as a real Canvas Assignment,
 * so there's no submission status to read; the user marks it done
 * themselves instead. localStorage-backed per browser, same as
 * useSeenTracker.js. */
export function usePdfGuessStatus(storageKey = 'ntucool_pdf_guess_completed') {
  const [completed, setCompleted] = useState(() => load(storageKey))

  const isCompleted = useCallback((row) => completed.has(rowKey(row)), [completed])

  const toggle = useCallback(
    (row) => {
      const key = rowKey(row)
      const next = new Set(completed)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      setCompleted(next)
      save(storageKey, next)
    },
    [completed, storageKey]
  )

  return { isCompleted, toggle }
}
