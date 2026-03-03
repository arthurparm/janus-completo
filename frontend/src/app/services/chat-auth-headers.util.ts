import { AUTH_TOKEN_KEY } from './api.config'
import { decodeTokenUserId } from './auth.utils'

export interface ChatStreamAuthHeadersOptions {
  projectId?: string | null
}

export function buildChatStreamAuthHeaders(
  options: ChatStreamAuthHeadersOptions = {},
): Headers {
  const headers = new Headers()
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
