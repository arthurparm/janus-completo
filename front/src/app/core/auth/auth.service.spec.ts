import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { AuthService } from './auth.service'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'
import { vi } from 'vitest'

describe('AuthService', () => {
  let svc: AuthService
  let http: HttpTestingController

  beforeEach(() => {
    localStorage.clear()
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AuthService]
    })
    svc = TestBed.inject(AuthService)
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    http.verify()
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('deve inicializar como não autenticado se não houver token', () => {
    expect(svc.currentUserValue).toBeNull()
  })

  it('deve fazer login via API local', async () => {
    const loginPromise = svc.loginWithPassword('a@b.com', '123456', true)

    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({ email: 'a@b.com', password: '123456' })

    req.flush({ token: 'janus.jwt', user: { id: '123', email: 'a@b.com', roles: ['user'] } })

    const ok = await loginPromise
    expect(ok).toBe(true)
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
    expect(svc.currentUserValue?.email).toBe('a@b.com')
  })

  it('deve validar token existente na inicialização', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'existing.jwt')

    // Re-create service to trigger constructor logic
    TestBed.resetTestingModule()
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AuthService]
    })
    svc = TestBed.inject(AuthService)
    http = TestBed.inject(HttpTestingController)

    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/me`)
    expect(req.request.method).toBe('GET')
    req.flush({ id: '123', email: 'existing@b.com' })

    // Wait for async initialization
    await new Promise(resolve => setTimeout(resolve, 0))

    expect(svc.currentUserValue?.email).toBe('existing@b.com')
  })
})
