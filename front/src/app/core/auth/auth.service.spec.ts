import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { AuthService } from './auth.service'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'

describe('AuthService', () => {
  let svc: AuthService
  let http: HttpTestingController

  beforeEach(() => {
    // Ensure clean state before service init
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
  })

  it('deve fazer login com senha via API', async () => {
    const mockResponse = {
      token: 'fake-jwt-token',
      user: {
        id: '123',
        email: 'test@example.com',
        roles: ['user']
      }
    }

    const loginPromise = svc.loginWithPassword('test@example.com', '123456', true)

    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({
      email: 'test@example.com',
      password: '123456'
    })

    req.flush(mockResponse)

    const result = await loginPromise
    expect(result).toBe(true)
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('fake-jwt-token')
  })

  it('deve inicializar sem token (sessão limpa)', () => {
    // initializeAuth is called in constructor.
    // Since we cleared localStorage in beforeEach, no request should be made.
    // We just verify the state.
    expect(svc.isAuthenticated()).toBe(false)
    expect(svc.currentUserValue).toBeNull()
  })

  it('deve recuperar sessão se token existir no localStorage', async () => {
    // We need to re-create the service to trigger constructor with token
    localStorage.setItem(AUTH_TOKEN_KEY, 'existing-token')

    // Reset the testing module to inject a new instance
    TestBed.resetTestingModule()
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AuthService]
    })

    svc = TestBed.inject(AuthService)
    http = TestBed.inject(HttpTestingController)

    // Expect the 'me' call
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/me`)
    expect(req.request.method).toBe('GET')

    req.flush({
      id: '123',
      email: 'existing@example.com',
      roles: ['admin']
    })

    // Wait for promise resolution (initializeAuth is async but not awaited in constructor)
    // We can't await the constructor, but we can wait for the http flush to be processed
    await new Promise(resolve => setTimeout(resolve, 0))

    expect(svc.isAuthenticated()).toBe(true)
    expect(svc.currentUserValue?.email).toBe('existing@example.com')
  })
})
