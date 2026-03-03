import { AUTH_TOKEN_KEY } from './api.config'
import { decodeTokenUserId } from './auth.utils'

export interface ChatStreamAuthHeadersOptions {
  projectId?: string | null
  requestId?: string
  traceparent?: string
  tracestate?: string
}

function randomHex(size: number): string {
  let output = ''
  for (let i = 0; i < size; i += 1) {
    output += Math.floor(Math.random() * 16).toString(16)
  }
  return output
}

export function generateRequestId(): string {
  const s = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
  return s.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

export function generateTraceparent(): string {
  const traceId = randomHex(32)
  const spanId = randomHex(16)
  return `00-${traceId}-${spanId}-01`
}

export function buildChatStreamAuthHeaders(
  options: ChatStreamAuthHeadersOptions = {},
): Headers {
  const headers = new Headers()
  const requestId = options.requestId || generateRequestId()
  headers.set('X-Request-ID', requestId)
  headers.set('traceparent', options.traceparent || generateTraceparent())
  if (options.tracestate) {
    headers.set('tracestate', options.tracestate)
  }
  try {
    const token = localStorage.getItem(AUTH_TOKEN_KEY)
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
      const uid = decodeTokenUserId(token)
      if (uid !== null) {
        headers.set('X-User-Id', String(uid))
      }
    }
  } catch {
    /* noop */
  }

  if (options.projectId) {
    headers.set('X-Project-Id', String(options.projectId))
  }

  return headers
}
