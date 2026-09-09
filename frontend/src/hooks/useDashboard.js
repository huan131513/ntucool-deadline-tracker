import { useCallback, useEffect, useState } from 'react'
import { getState, notify as apiNotify, refresh as apiRefresh } from '../api.js'

/** All dashboard state + actions in one hook, so App.jsx stays pure layout. */
export function useDashboard() {
  const [state, setState] = useState(null)
  const [message, setMessage] = useState(null)
  const [loading, setLoading] = useState({ initial: true, refresh: false, notify: false })
  const [connectionError, setConnectionError] = useState(false)

  useEffect(() => {
    getState()
      .then(setState)
      .catch(() => setConnectionError(true))
      .finally(() => setLoading((l) => ({ ...l, initial: false })))
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

  return { state, message, loading, connectionError, refresh, notify }
}
