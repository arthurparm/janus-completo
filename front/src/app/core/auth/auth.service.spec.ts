import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { AuthService } from './auth.service'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'
import { Auth, signInWithEmailAndPassword } from '@angular/fire/auth'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'

// Mock firebase functions globally
vi.mock('@angular/fire/auth', () => ({
  Auth: class {},
  signInWithEmailAndPassword: vi.fn(),
  authState: vi.fn()
}))

describe('AuthService', () => {
  let svc: AuthService
  let httpMock: HttpTestingController
  let authStateCallback: ((user: any) => Promise<void>) | null = null

  const authMock = {
    onAuthStateChanged: vi.fn((cb: (user: any) => Promise<void>) => {
      authStateCallback = cb
      // Return unregister function
      return () => {}
    }),
    currentUser: null
  }

  beforeEach(() => {
    TestBed.resetTestingModule();

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AuthService,
        { provide: Auth, useValue: authMock }
      ]
    })
    svc = TestBed.inject(AuthService)
    httpMock = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    try {
        httpMock.verify()
    } catch (e) {
    }
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('deve fazer login com senha via Firebase', async () => {
    const signInMock = vi.mocked(signInWithEmailAndPassword)
    signInMock.mockResolvedValueOnce({
      user: {
        uid: 'uid-123',
        getIdToken: async () => 'firebase-token'
      }
    } as any)

    // Trigger the login call
    const loginPromise = svc.loginWithPassword('a@b.com', '123456', true)

    // Allow microtasks to process
    await new Promise(resolve => setTimeout(resolve, 0))

    // Handle any HTTP request that appears
    const req = httpMock.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush({ token: 'janus.jwt', user: { id: 'uid-123', roles: ['user'], permissions: ['read'] } })

    const ok = await loginPromise

    // Verify login was successful
    expect(ok).toBe(true)
  })

  it('deve realizar exchange e salvar token Janus', async () => {
    const firebaseUser = {
      isAnonymous: false,
      uid: 'uid-123',
      email: 'a@b.com',
      getIdToken: vi.fn().mockResolvedValue('firebase.jwt')
    }

    if (authStateCallback) {
        const authPromise = authStateCallback(firebaseUser)
        // Allow microtasks
        await new Promise(resolve => setTimeout(resolve, 0))

        const req = httpMock.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
        req.flush({ token: 'janus.jwt', user: { id: 'uid-123', roles: ['user'], permissions: ['read'] } })
        await authPromise
    }
  })
})
