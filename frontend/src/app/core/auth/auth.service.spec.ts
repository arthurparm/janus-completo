import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { AuthService } from './auth.service'
import { API_BASE_URL, AUTH_TOKEN_KEY, PUBLIC_API_BASE_URL } from '../../services/api.config'

describe('AuthService OIDC PKCE', () => {
  let http: HttpTestingController

  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    TestBed.configureTestingModule({ imports: [HttpClientTestingModule] })
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    http.verify()
    localStorage.clear()
    sessionStorage.clear()
  })

  it('starts unauthenticated without an access token', async () => {
    const service = TestBed.inject(AuthService)
    await Promise.resolve()
    expect(service.isAuthenticated()).toBe(false)
    expect(service.authReady()).toBe(true)
  })

  it('validates state, exchanges the authorization code, and keeps only the access token in session', async () => {
    sessionStorage.setItem('JANUS_OIDC_PKCE_VERIFIER', 'verifier-value')
    sessionStorage.setItem('JANUS_OIDC_STATE', 'expected-state')
    sessionStorage.setItem('JANUS_OIDC_REDIRECT', '/conversations')
    const service = TestBed.inject(AuthService)

    const callback = service.handleCallback('authorization-code', 'expected-state')
    http.expectOne(`${PUBLIC_API_BASE_URL}/api/v1/auth/oidc-config`).flush({
      issuer: 'https://idp.example',
      client_id: 'janus-spa',
      audience: 'janus-user-api',
      scopes: ['openid', 'profile'],
      authorization_endpoint: 'https://idp.example/authorize',
      response_type: 'code',
      code_challenge_method: 'S256'
    })
    await Promise.resolve()
    http.expectOne('https://idp.example/.well-known/openid-configuration').flush({
      token_endpoint: 'https://idp.example/token'
    })
    await Promise.resolve()
    const tokenRequest = http.expectOne('https://idp.example/token')
    expect(tokenRequest.request.method).toBe('POST')
    expect(tokenRequest.request.body).toContain('code_verifier=verifier-value')
    tokenRequest.flush({ access_token: 'signed-access-token', token_type: 'Bearer', expires_in: 300 })
    await Promise.resolve()
    http.expectOne(`${API_BASE_URL}/v1/users/me`).flush({
      id: '42', email: 'user@example.com', roles: ['USER']
    })

    expect(await callback).toBe('/conversations')
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBe('signed-access-token')
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
    expect(service.isAuthenticated()).toBe(true)
  })

  it('rejects a forged callback state before contacting the IdP', async () => {
    sessionStorage.setItem('JANUS_OIDC_PKCE_VERIFIER', 'verifier-value')
    sessionStorage.setItem('JANUS_OIDC_STATE', 'expected-state')
    const service = TestBed.inject(AuthService)
    await expect(service.handleCallback('code', 'forged-state')).rejects.toThrow()
    expect(service.isAuthenticated()).toBe(false)
  })

  it('never accepts an access token from persistent local storage', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'persistent-token')
    const service = TestBed.inject(AuthService)
    await Promise.resolve()
    expect(service.isAuthenticated()).toBe(false)
  })
})
