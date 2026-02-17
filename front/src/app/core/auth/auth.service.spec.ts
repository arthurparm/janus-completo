import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { AuthService } from './auth.service'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'
import { Auth, signInWithEmailAndPassword } from '@angular/fire/auth'
import { vi } from 'vitest'

describe('AuthService', () => {
  let svc: AuthService
  let http: HttpTestingController
  let authStateCallback: ((user: any) => Promise<void>) | null = null
  const authMock = {
    onAuthStateChanged: vi.fn((cb: (user: any) => Promise<void>) => {
      authStateCallback = cb
      return () => {}
    })
  }

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [{ provide: Auth, useValue: authMock }]
    })
    svc = TestBed.inject(AuthService)
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    http.verify()
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('deve fazer login com senha via Firebase', async () => {
    vi.mocked(signInWithEmailAndPassword).mockResolvedValueOnce({} as any)
    const loginPromise = svc.loginWithPassword('a@b.com', '123456', true)

    // Expect the HTTP request triggered by loginWithPassword
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    expect(req.request.method).toBe('POST')
    req.flush({ token: 'janus.jwt', user: { id: 'uid-123' } })

    const ok = await loginPromise

    expect(ok).toBe(true)
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
  })
})
