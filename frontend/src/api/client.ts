// Typed fetch wrapper: sends the session cookie and the CSRF header on every request.

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  readonly status: number
  /** Seconds from the Retry-After header, when the server sent one (e.g. on 429). */
  readonly retryAfter: number | null

  constructor(status: number, message: string, retryAfter: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.retryAfter = retryAfter
  }
}

/** Turn FastAPI's `detail` (a string, or a list of validation errors) into one message. */
function detailMessage(body: unknown): string | null {
  if (!body || typeof body !== 'object' || !('detail' in body)) return null
  const { detail } = body
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d: unknown) =>
        d && typeof d === 'object' && 'msg' in d && typeof d.msg === 'string' ? d.msg : null,
      )
      .filter((m): m is string => m !== null)
    if (messages.length) return messages.join('; ')
  }
  return null
}

/** Build an ApiError from a non-2xx response. */
export async function errorFromResponse(response: Response): Promise<ApiError> {
  let message = response.statusText || `Request failed (${response.status})`
  try {
    message = detailMessage(await response.json()) ?? message
  } catch {
    // non-JSON error body; keep the status text
  }
  const retryHeader = response.headers.get('Retry-After')
  const retryAfter = retryHeader && /^\d+$/.test(retryHeader) ? Number(retryHeader) : null
  return new ApiError(response.status, message, retryAfter)
}

/** fetch() against the API with credentials and the CSRF header; returns the raw Response. */
export function apiRequest(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  headers.set('X-Requested-With', 'XMLHttpRequest')
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  return fetch(`${API_BASE_URL}${path}`, { ...init, headers, credentials: 'include' })
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiRequest(path, init)
  if (!response.ok) throw await errorFromResponse(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return 'Something went wrong'
}
