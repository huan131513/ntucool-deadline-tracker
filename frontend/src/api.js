const BASE = '/api'

async function request(path, options) {
  const resp = await fetch(BASE + path, options)
  if (!resp.ok) {
    throw new Error(`API ${path} failed: ${resp.status}`)
  }
  return resp.json()
}

export const getState = () => request('/state')
export const refresh = () => request('/refresh', { method: 'POST' })
export const notify = () => request('/notify', { method: 'POST' })
