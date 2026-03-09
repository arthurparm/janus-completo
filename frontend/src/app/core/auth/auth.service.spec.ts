import { TestBed } from '@angular/core/testing'
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing'
import { provideHttpClient } from '@angular/common/http'
import { AuthService } from './auth.service'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'
import { firstValueFrom, filter } from 'rxjs'

describe('AuthService', () => {
  let http: HttpTestingController

  beforeEach(() => {
    localStorage.clear()
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    http.verify()
    localStorage.clear()
  })

  it('deve fazer login com email/senha e salvar token local', async () => {
    const svc = TestBed.inject(AuthService)
    await waitForAuthReady(svc)
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

    await waitForAuthReady(svc)
    expect(svc.isAuthenticated()).toBe(true)
    expect(svc.currentUserValue?.email).toBe('a@b.com')
  })

  it('deve retornar false quando login falhar por erro da API', async () => {
    const svc = TestBed.inject(AuthService)
    await waitForAuthReady(svc)

    const promise = svc.loginWithPassword('a@b.com', 'senha-invalida', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    expect(req.request.method).toBe('POST')
    req.flush({ detail: 'unauthorized' }, { status: 401, statusText: 'Unauthorized' })

    await expectAsync(promise).toBeResolvedTo(false)
    expect(svc.isAuthenticated()).toBe(false)
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('deve limpar sessao quando token persistido for invalido', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'invalid.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/me`)
    expect(req.request.method).toBe('GET')
    req.flush({ detail: 'token expired' }, { status: 401, statusText: 'Unauthorized' })

    await waitForAuthReady(svc)
    expect(svc.isAuthenticated()).toBe(false)
    expect(svc.currentUserValue).toBeNull()
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })
})

async function waitForAuthReady(svc: AuthService): Promise<void> {
  if (svc.authReady()) {
    return
  }
  await firstValueFrom(svc.authReady$.pipe(filter(Boolean)))
}
