import { AUTH_TOKEN_KEY } from './api.config'

export function decodeTokenUserId(token: string | null): number | null {
  if (!token) return null
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const body = parts[0]
    const padded = body + '='.repeat((4 - (body.length % 4)) % 4)
    const jsonStr = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
    const payload = JSON.parse(jsonStr)
    const uid = Number(payload?.user_id)
    return Number.isFinite(uid) ? uid : null
  } catch {
    return null
  }
}

export function getStoredAuthToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY) || sessionStorage.getItem(AUTH_TOKEN_KEY)
  } catch {
    return null
  }
}

export function storeAuthToken(token: string, rememberSession: boolean): void {
  try {
    if (rememberSession) {
      localStorage.setItem(AUTH_TOKEN_KEY, token)
      sessionStorage.removeItem(AUTH_TOKEN_KEY)
      return
    }
    sessionStorage.setItem(AUTH_TOKEN_KEY, token)
    localStorage.removeItem(AUTH_TOKEN_KEY)
  } catch {
    // no-op
  }
}

export function clearStoredAuthToken(): void {
  try {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    sessionStorage.removeItem(AUTH_TOKEN_KEY)
  } catch {
    // no-op
  }
}

export function decodeTokenExp(token: string | null): number | null {
  if (!token) return null
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const body = parts[0]
    const padded = body + '='.repeat((4 - (body.length % 4)) % 4)
    const jsonStr = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
    const payload = JSON.parse(jsonStr)
    const exp = Number(payload?.exp)
    return Number.isFinite(exp) ? exp : null
  } catch {
    return null
  }
}
