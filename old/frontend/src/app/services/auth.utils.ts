import { AUTH_TOKEN_KEY } from './api.config'

export function getStoredAuthToken(): string | null {
  try {
    return sessionStorage.getItem(AUTH_TOKEN_KEY)
  } catch {
    return null
  }
}

export function storeAuthToken(token: string): void {
  try {
    sessionStorage.setItem(AUTH_TOKEN_KEY, token)
  } catch {
    // Browser storage may be unavailable under restrictive privacy settings.
  }
}

export function clearStoredAuthToken(): void {
  try {
    sessionStorage.removeItem(AUTH_TOKEN_KEY)
  } catch {
    // Browser storage may be unavailable under restrictive privacy settings.
  }
}

export function decodeTokenExp(token: string | null): number | null {
  if (!token) return null
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const body = parts[1]
    const padded = body + '='.repeat((4 - (body.length % 4)) % 4)
    const payload = JSON.parse(atob(padded.replace(/-/g, '+').replace(/_/g, '/')))
    const exp = Number(payload?.exp)
    return Number.isFinite(exp) ? exp : null
  } catch {
    return null
  }
}
