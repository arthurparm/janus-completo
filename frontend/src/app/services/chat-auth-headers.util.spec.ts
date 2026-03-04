import { AUTH_TOKEN_KEY } from './api.config'
import { buildChatStreamAuthHeaders } from './chat-auth-headers.util'

describe('buildChatStreamAuthHeaders', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  it('deve montar headers com bearer, x-user-id e x-project-id', () => {
    const payload = btoa(JSON.stringify({ user_id: 42 }))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/g, '')
    const fakeToken = `${payload}.ignored.signature`
    localStorage.setItem(AUTH_TOKEN_KEY, fakeToken)

    const headers = buildChatStreamAuthHeaders({ projectId: 'p-1' })

    expect(headers.get('Authorization')).toBe(`Bearer ${fakeToken}`)
    expect(headers.get('X-User-Id')).toBe('42')
    expect(headers.get('X-Project-Id')).toBe('p-1')
    expect(headers.get('X-Request-ID')).toBeTruthy()
    expect(headers.get('traceparent')).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/)
  })

  it('deve retornar headers de rastreio mesmo sem token', () => {
    const headers = buildChatStreamAuthHeaders()
    expect(headers.get('Authorization')).toBeNull()
    expect(headers.get('X-User-Id')).toBeNull()
    expect(headers.get('X-Request-ID')).toBeTruthy()
    expect(headers.get('traceparent')).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/)
  })

  it('deve usar token de sessionStorage quando localStorage estiver vazio', () => {
    const payload = btoa(JSON.stringify({ user_id: 7 }))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/g, '')
    const fakeToken = `${payload}.ignored.signature`
    sessionStorage.setItem(AUTH_TOKEN_KEY, fakeToken)

    const headers = buildChatStreamAuthHeaders()

    expect(headers.get('Authorization')).toBe(`Bearer ${fakeToken}`)
    expect(headers.get('X-User-Id')).toBe('7')
  })
})
