import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { AuthService } from './auth.service'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'

describe('AuthService', () => {
  let http: HttpTestingController

  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    })
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    http.verify()
    localStorage.clear()
    sessionStorage.clear()
  })

  it('deve fazer login com remember=true e salvar token no localStorage', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', '123456', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({ email: 'a@b.com', password: '123456' })
    req.flush({ token: 'janus.jwt', user: { id: 'uid-123', email: 'a@b.com', roles: ['user'] } })

    const ok = await promise
    expect(ok).toBe(true)
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('deve fazer login com remember=false e salvar token no sessionStorage', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', '123456', false)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush({ token: 'janus.jwt', user: { id: 'uid-123', email: 'a@b.com', roles: ['user'] } })

    const ok = await promise
    expect(ok).toBe(true)
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('deve restaurar sessao quando existir token local', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/me`)
    expect(req.request.method).toBe('GET')
    req.flush({ id: 'uid-123', email: 'a@b.com', roles: ['user'] })

    await Promise.resolve()
    expect(svc.isAuthenticated()).toBe(true)
    expect(svc.currentUserValue?.email).toBe('a@b.com')
  })

  it('deve restaurar sessao quando existir token na sessionStorage', async () => {
    sessionStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/me`)
    expect(req.request.method).toBe('GET')
    req.flush({ id: 'uid-123', email: 'a@b.com', roles: ['user'] })

    await Promise.resolve()
    expect(svc.isAuthenticated()).toBe(true)
    expect(svc.currentUserValue?.email).toBe('a@b.com')
  })
})
