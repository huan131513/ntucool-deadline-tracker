const BASE = '/api'

async function request(path, options) {
  const resp = await fetch(BASE + path, options)
  if (!resp.ok) {
    throw new Error(`API ${path} failed: ${resp.status}`)
  }
  return resp.json()
}

export const getState = () => request('/state')
export const getProgress = () => request('/progress')
export const refresh = () => request('/refresh', { method: 'POST' })
// Always sends one "all incomplete assignments" digest — no threshold, no
// dedup. The hourly launchd job uses /api/notify (threshold-based) instead.
export const notify = () => request('/notify-digest', { method: 'POST' })
