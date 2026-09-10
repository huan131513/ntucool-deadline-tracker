import { useCallback, useEffect, useRef, useState } from 'react'
import { getProgress, getState, notify as apiNotify, refresh as apiRefresh } from '../api.js'

const POLL_RUNNING_MS = 800 // tight polling while a fetch is actively in progress
const POLL_IDLE_MS = 4000 // still poll at rest — catches the hourly launchd job too

/** All dashboard state + actions in one hook, so App.jsx stays pure layout. */
export function useDashboard() {
  const [state, setState] = useState(null)
  const [message, setMessage] = useState(null)
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState({ initial: true, refresh: false, notify: false })
  const [connectionError, setConnectionError] = useState(false)
  const wasRunningRef = useRef(false)

  useEffect(() => {
    getState()
      .then(setState)
      .catch(() => setConnectionError(true))
      .finally(() => setLoading((l) => ({ ...l, initial: false })))
  }, [])

  // Poll /api/progress continuously — this is what lets the panel show a
  // fetch that launchd triggered in the background, not just ones started
  // from this browser tab. Speeds up while something is actually running.
  useEffect(() => {
    let cancelled = false
    let timer

    async function tick() {
      try {
        const p = await getProgress()
        if (cancelled) return
        setProgress(p)
        // Transition running -> not running means a fetch just finished
        // somewhere (this tab or not) — pull the latest data automatically.
        if (wasRunningRef.current && !p.running) {
          getState().then((s) => !cancelled && setState(s)).catch(() => {})
        }
        wasRunningRef.current = p.running
        timer = setTimeout(tick, p.running ? POLL_RUNNING_MS : POLL_IDLE_MS)
      } catch {
        if (!cancelled) timer = setTimeout(tick, POLL_IDLE_MS)
      }
    }

    tick()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [])

  const refresh = useCallback(async () => {
    setLoading((l) => ({ ...l, refresh: true }))
    setConnectionError(false)
    try {
      const data = await apiRefresh()
      setMessage(data.message)
      setState(data)
    } catch {
      setConnectionError(true)
    } finally {
      setLoading((l) => ({ ...l, refresh: false }))
    }
  }, [])

  const notify = useCallback(async () => {
    setLoading((l) => ({ ...l, notify: true }))
    setConnectionError(false)
    try {
      const data = await apiNotify()
      setMessage(data.message)
    } catch {
      setConnectionError(true)
    } finally {
      setLoading((l) => ({ ...l, notify: false }))
    }
  }, [])

  return { state, message, progress, loading, connectionError, refresh, notify }
}
