const API_BASE = import.meta.env.VITE_API_URL ?? '/api/v1'
const TOKEN_KEY = 'vetpet_access_token'
export const SESSION_EXPIRED_FLAG = 'vetpet_session_expired'
export const SESSION_EXPIRED_EVENT = 'auth:session-expired'

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

/** Only a request that carried a token can have expired — an anonymous 401 (e.g. a wrong OTP) isn't a session expiry. */
function notifyIfSessionExpired(status: number, hadToken: boolean) {
  if (status !== 401 || !hadToken) return
  tokenStore.clear()
  try {
    sessionStorage.setItem(SESSION_EXPIRED_FLAG, '1')
  } catch {
    /* sessionStorage unavailable (private browsing, etc.) — the redirect still works, just without the banner */
  }
  window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = tokenStore.get()
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    throw new ApiError('Unable to reach Madina Vet Pet. Is the backend running?', 0)
  }

  const body = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    notifyIfSessionExpired(response.status, Boolean(token))
    const detail = body && typeof body.detail === 'string' ? body.detail : 'Request failed.'
    throw new ApiError(detail, response.status)
  }
  return body as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  /** For a resource that legitimately may not exist yet (e.g. "no consultation written yet") —
   * returns null on 404 instead of throwing, and still throws on every other failure. */
  getOptional: async <T>(path: string): Promise<T | null> => {
    try {
      return await request<T>(path)
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null
      throw error
    }
  },
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'POST', body: data === undefined ? undefined : JSON.stringify(data) }),
  patch: <T>(path: string, data: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(data) }),
  put: <T>(path: string, data: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(data) }),
  upload: <T>(path: string, data: FormData) => request<T>(path, { method: 'POST', body: data }),
  blob: async (path: string) => {
    const token = tokenStore.get()
    const response = await fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token ?? ''}` } })
    if (!response.ok) {
      notifyIfSessionExpired(response.status, Boolean(token))
      throw new ApiError('Unable to download protected media.', response.status)
    }
    return response.blob()
  },
  delete: (path: string) => request<void>(path, { method: 'DELETE' }),
}
