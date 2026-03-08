import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { AuthService } from './auth.service'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'
import { firstValueFrom, filter, take } from 'rxjs'

describe('AuthService', () => {
  let http: HttpTestingController

  beforeEach(() => {
    localStorage.clear()
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    })
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    http.verify()
    localStorage.clear()
  })

  it('deve fazer login com email/senha e salvar token local', async () => {
    const svc = TestBed.inject(AuthService)
    http.expectNone(`${API_BASE_URL}/v1/auth/local/me`)

    const promise = svc.loginWithPassword('a@b.com', '123456', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({ email: 'a@b.com', password: '123456' })
    req.flush({ token: 'janus.jwt', user: { id: 'uid-123', email: 'a@b.com', roles: ['user'] } })

    const ok = await promise
    expect(ok).toBe(true)
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
  })

  it('deve restaurar sessao quando existir token local', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/me`)
    expect(req.request.method).toBe('GET')
    req.flush({ id: 'uid-123', email: 'a@b.com', roles: ['user'] })

    await firstValueFrom(svc.authReady$.pipe(filter(Boolean), take(1)))
    expect(svc.isAuthenticated()).toBe(true)
    expect(svc.currentUserValue?.email).toBe('a@b.com')
  })

  it('deve limpar sessao quando restauracao com token falhar', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/me`)
    expect(req.request.method).toBe('GET')
    req.flush({ detail: 'unauthorized' }, { status: 401, statusText: 'Unauthorized' })

    await firstValueFrom(svc.authReady$.pipe(filter(Boolean), take(1)))
    expect(svc.isAuthenticated()).toBe(false)
    expect(svc.currentUserValue).toBeNull()
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('deve retornar false e manter sessao limpa quando login falhar', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', 'bad-password', true)

    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    expect(req.request.method).toBe('POST')
    req.flush({ detail: 'invalid credentials' }, { status: 401, statusText: 'Unauthorized' })

    const ok = await promise
    expect(ok).toBe(false)
    expect(svc.isAuthenticated()).toBe(false)
    expect(svc.currentUserValue).toBeNull()
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('deve retornar reset_token no request de recuperacao quando backend fornecer', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.requestPasswordReset('a@b.com')

    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/request-reset`)
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({ email: 'a@b.com' })
    req.flush({ status: 'ok', reset_token: 'token-123' })

    const token = await promise
    expect(token).toBe('token-123')
  })

  it('deve retornar null no request de recuperacao quando backend falhar', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.requestPasswordReset('a@b.com')

    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/request-reset`)
    req.flush({ detail: 'error' }, { status: 500, statusText: 'Server Error' })

    const token = await promise
    expect(token).toBeNull()
  })

  it('deve retornar true no reset de senha quando status for ok', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.resetPassword('token-123', 'NovaSenha@123')

    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/reset`)
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({ token: 'token-123', password: 'NovaSenha@123' })
    req.flush({ status: 'ok' })

    const ok = await promise
    expect(ok).toBe(true)
  })

  it('deve retornar false no reset de senha quando backend falhar', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.resetPassword('token-123', 'NovaSenha@123')

    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/reset`)
    req.flush({ detail: 'invalid token' }, { status: 400, statusText: 'Bad Request' })

    const ok = await promise
    expect(ok).toBe(false)
  })
})
