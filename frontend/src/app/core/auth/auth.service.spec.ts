import { TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing'
import { AuthService } from './auth.service'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'
import { filter, firstValueFrom, take } from 'rxjs'

const LOGIN_URL = `${API_BASE_URL}/v1/auth/local/login`
const PROFILE_URL = `${API_BASE_URL}/v1/auth/local/me`

async function waitAuthReady(svc: AuthService): Promise<void> {
  await firstValueFrom(svc.authReady$.pipe(filter(Boolean), take(1)))
}

describe('AuthService', () => {
  let http: HttpTestingController

  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
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
    http.expectNone(PROFILE_URL)
    const promise = svc.loginWithPassword('a@b.com', '123456', true)
    const req = http.expectOne(LOGIN_URL)
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({ email: 'a@b.com', password: '123456' })
    req.flush({ token: 'janus.jwt', user: { id: 'uid-123', email: 'a@b.com', roles: ['user'] } })

    const result = await promise
    expect(result.ok).toBe(true)
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('deve fazer login com remember=false e salvar token no sessionStorage', async () => {
    const svc = TestBed.inject(AuthService)
    http.expectNone(PROFILE_URL)
    const promise = svc.loginWithPassword('a@b.com', '123456', false)
    const req = http.expectOne(LOGIN_URL)
    req.flush({ token: 'janus.jwt', user: { id: 'uid-123', email: 'a@b.com', roles: ['user'] } })

    const result = await promise
    expect(result.ok).toBe(true)
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('deve retornar erro mapeado para 401', async () => {
    const svc = TestBed.inject(AuthService)
    http.expectNone(PROFILE_URL)
    const promise = svc.loginWithPassword('a@b.com', '123456', true)
    const req = http.expectOne(LOGIN_URL)
    req.flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' })

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.statusCode).toBe(401)
    expect(result.reason).toBe('invalid_credentials')
  })

  it('deve retornar erro mapeado para 422', async () => {
    const svc = TestBed.inject(AuthService)
    http.expectNone(PROFILE_URL)
    const promise = svc.loginWithPassword('bad-email', '123456', true)
    const req = http.expectOne(LOGIN_URL)
    req.flush({ detail: 'validation error' }, { status: 422, statusText: 'Unprocessable Content' })

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.statusCode).toBe(422)
    expect(result.reason).toBe('invalid_request')
  })

  it('deve mapear 401 com orientacao para recuperar acesso', async () => {
    const svc = TestBed.inject(AuthService)
    http.expectNone(PROFILE_URL)
    const promise = svc.loginWithPassword('a@b.com', '12345678', true)
    const req = http.expectOne(LOGIN_URL)
    req.flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' })

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.error).toContain('Recuperar acesso')
  })

  it('deve mapear 422 com erro de senha minima', async () => {
    const svc = TestBed.inject(AuthService)
    http.expectNone(PROFILE_URL)
    const promise = svc.loginWithPassword('a@b.com', '123', true)
    const req = http.expectOne(LOGIN_URL)
    req.flush(
      { detail: [{ msg: 'String should have at least 8 characters', loc: ['body', 'password'] }] },
      { status: 422, statusText: 'Unprocessable Content' }
    )

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.error).toContain('minimo 8')
  })

  it('deve mapear reset com token invalido', async () => {
    const svc = TestBed.inject(AuthService)
    http.expectNone(PROFILE_URL)
    const promise = svc.resetPassword('invalid', 'NovaSenha@123')
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/reset`)
    req.flush({ detail: 'Invalid token' }, { status: 400, statusText: 'Bad Request' })

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.error).toContain('Token invalido ou expirado')
  })

  it('deve restaurar sessao quando existir token local', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(PROFILE_URL)
    expect(req.request.method).toBe('GET')
    req.flush({ id: 'uid-123', email: 'a@b.com', roles: ['user'] })

    await waitAuthReady(svc)
    expect(svc.isAuthenticated()).toBe(true)
    expect(svc.currentUserValue?.email).toBe('a@b.com')
  })

  it('deve restaurar sessao quando existir token na sessionStorage', async () => {
    sessionStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(PROFILE_URL)
    expect(req.request.method).toBe('GET')
    req.flush({ id: 'uid-123', email: 'a@b.com', roles: ['user'] })

    await waitAuthReady(svc)
    expect(svc.isAuthenticated()).toBe(true)
    expect(svc.currentUserValue?.email).toBe('a@b.com')
  })

  it('deve limpar sessao quando token persistido for invalido', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'expired.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(PROFILE_URL)
    req.flush({ detail: 'Token invalid' }, { status: 401, statusText: 'Unauthorized' })

    await waitAuthReady(svc)
    expect(svc.isAuthenticated()).toBe(false)
    expect(svc.currentUserValue).toBeNull()
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })
})
