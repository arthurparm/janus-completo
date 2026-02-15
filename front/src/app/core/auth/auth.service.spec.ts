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

    // Expect the call to local auth that follows successful login logic
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush({ token: 'janus.jwt', user: { id: 1, email: 'a@b.com' } })

    const ok = await loginPromise

    expect(ok).toBe(true)
  })

  it('deve realizar exchange e salvar token Janus', async () => {
    const firebaseUser = {
      isAnonymous: false,
      uid: 'uid-123',
      email: 'a@b.com',
      getIdToken: vi.fn().mockResolvedValue('firebase.jwt')
    }

    const authPromise = authStateCallback?.(firebaseUser)
    await Promise.resolve()
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/firebase/exchange`)
    expect(req.request.body).toEqual({ token: 'firebase.jwt' })
    req.flush({ token: 'janus.jwt', user: { id: 'uid-123', roles: ['user'], permissions: ['read'] } })

    if (authPromise) await authPromise

    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
  })
})
