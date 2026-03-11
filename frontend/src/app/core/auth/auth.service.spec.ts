import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { AuthService } from './auth.service'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'

describe('AuthService', () => {
  let http: HttpTestingController
  const meEndpoint = `${API_BASE_URL}/v1/auth/local/me`

  const waitForAuthReady = async (svc: AuthService, maxTicks = 8): Promise<void> => {
    for (let i = 0; i < maxTicks; i += 1) {
      if (svc.authReady()) return
      await Promise.resolve()
    }
  }

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

    const result = await promise
    expect(result.ok).toBe(true)
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('deve fazer login com remember=false e salvar token no sessionStorage', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', '123456', false)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush({ token: 'janus.jwt', user: { id: 'uid-123', email: 'a@b.com', roles: ['user'] } })

    const result = await promise
    expect(result.ok).toBe(true)
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('deve retornar erro mapeado para 401', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', '123456', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' })

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.statusCode).toBe(401)
    expect(result.reason).toBe('invalid_credentials')
  })

  it('deve retornar erro mapeado para 422', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('bad-email', '123456', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush({ detail: 'validation error' }, { status: 422, statusText: 'Unprocessable Content' })

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.statusCode).toBe(422)
    expect(result.reason).toBe('invalid_request')
  })

  it('deve mapear 401 com orientacao para recuperar acesso', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', '12345678', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' })

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.error).toContain('Recuperar acesso')
  })

  it('deve mapear 422 com erro de senha minima', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', '123', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
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
    const req = http.expectOne(meEndpoint)
    expect(req.request.method).toBe('GET')
    req.flush({ id: 'uid-123', email: 'a@b.com', roles: ['user'] })

    await waitForAuthReady(svc)
    expect(svc.isAuthenticated()).toBe(true)
    expect(svc.currentUserValue?.email).toBe('a@b.com')
    expect(svc.authReady()).toBe(true)
  })

  it('deve restaurar sessao quando existir token na sessionStorage', async () => {
    sessionStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(meEndpoint)
    expect(req.request.method).toBe('GET')
    req.flush({ id: 'uid-123', email: 'a@b.com', roles: ['user'] })

    await waitForAuthReady(svc)
    expect(svc.isAuthenticated()).toBe(true)
    expect(svc.currentUserValue?.email).toBe('a@b.com')
    expect(svc.authReady()).toBe(true)
  })

  it('deve concluir inicializacao sem chamar /me quando nao houver token persistido', async () => {
    const svc = TestBed.inject(AuthService)

    http.expectNone(meEndpoint)
    await waitForAuthReady(svc)

    expect(svc.isAuthenticated()).toBe(false)
    expect(svc.currentUserValue).toBeNull()
    expect(svc.authReady()).toBe(true)
  })

  it('deve limpar sessao persistida quando restauracao via /me falhar', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')
    sessionStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(meEndpoint)
    expect(req.request.method).toBe('GET')
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' })

    await waitForAuthReady(svc)

    expect(svc.isAuthenticated()).toBe(false)
    expect(svc.currentUserValue).toBeNull()
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
    expect(svc.authReady()).toBe(true)
  })
})
