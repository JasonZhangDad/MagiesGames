const TOKEN_KEY = 'mg_token'

export function getToken() { return localStorage.getItem(TOKEN_KEY) }
export function setToken(t) { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY) }

async function req(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(path, { ...opts, headers })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `请求失败(${res.status})`)
  return data
}

export const api = {
  guest: (nickname) => req('/api/auth/guest', { method: 'POST', body: JSON.stringify({ nickname }) }),
  me: () => req('/api/me'),
  rooms: () => req('/api/rooms'),
  leaderboard: () => req('/api/leaderboard'),
  profile: (id) => req(`/api/profile/${id}`),
}
