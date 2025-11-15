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