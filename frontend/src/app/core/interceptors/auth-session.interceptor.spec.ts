import { HttpErrorResponse, HttpHeaders, HttpRequest, HttpResponse } from '@angular/common/http'
import { TestBed } from '@angular/core/testing'
import { Router } from '@angular/router'
import { firstValueFrom, of, throwError } from 'rxjs'
import { vi } from 'vitest'
import { AuthService } from '../auth/auth.service'
import { NotificationService } from '../notifications/notification.service'
import { authSessionInterceptor } from './auth-session.interceptor'
import { AUTH_TOKEN_KEY } from '../../services/api.config'

describe('authSessionInterceptor', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  it('deve fazer refresh em 401 e repetir a requisicao original', async () => {
    const refreshAccessToken = vi.fn().mockImplementation(async () => {
      localStorage.setItem(AUTH_TOKEN_KEY, 'new.jwt')
      return true
    })
    const captureRateLimit = vi.fn()

    TestBed.configureTestingModule({
      providers: [
        {
          provide: AuthService,
          useValue: {
            isAuthRateLimited: () => false,
            authRateLimitRemainingSeconds: () => 0,
            isVisitorSession: () => false,
            refreshAccessToken,
            captureRateLimit
          }
        },
        { provide: Router, useValue: { url: '/private', navigate: vi.fn() } },
        { provide: NotificationService, useValue: { notifyWarning: vi.fn() } }
      ]
    })

    localStorage.setItem(AUTH_TOKEN_KEY, 'old.jwt')

    let calls = 0
    const next = vi.fn((req: HttpRequest<unknown>) => {
      calls += 1
      if (calls === 1) {
        return throwError(() => new HttpErrorResponse({ status: 401, statusText: 'Unauthorized', url: req.url }))
      }
      expect(req.headers.get('Authorization')).toBe('Bearer new.jwt')
      return of(new HttpResponse({ status: 200, body: { ok: true } }))
    })

    const req = new HttpRequest('GET', '/api/v1/chat/history', null, {
      headers: new HttpHeaders({ Authorization: 'Bearer old.jwt' })
    })
    const out$ = TestBed.runInInjectionContext(() => authSessionInterceptor(req, next))
    const resp = await firstValueFrom(out$)

    expect(resp).toBeInstanceOf(HttpResponse)
    expect(refreshAccessToken).toHaveBeenCalledTimes(1)
    expect(next).toHaveBeenCalledTimes(2)
  })

  it('deve capturar rate limit em 429', async () => {
    const captureRateLimit = vi.fn()

    TestBed.configureTestingModule({
      providers: [
        {
          provide: AuthService,
          useValue: {
            isAuthRateLimited: () => false,
            authRateLimitRemainingSeconds: () => 0,
            isVisitorSession: () => false,
            refreshAccessToken: vi.fn(),
            captureRateLimit
          }
        },
        { provide: Router, useValue: { url: '/private', navigate: vi.fn() } },
        { provide: NotificationService, useValue: { notifyWarning: vi.fn() } }
      ]
    })

    const next = vi.fn(() =>
      throwError(
        () =>
          new HttpErrorResponse({
            status: 429,
            statusText: 'Too Many Requests',
            headers: new HttpHeaders({ 'Retry-After': '3' })
          })
      )
    )

    const req = new HttpRequest('GET', '/api/v1/chat/history')
    const out$ = TestBed.runInInjectionContext(() => authSessionInterceptor(req, next))

    await expect(firstValueFrom(out$)).rejects.toBeInstanceOf(HttpErrorResponse)
    expect(captureRateLimit).toHaveBeenCalledTimes(1)
  })

  it('nao tenta refresh nem redireciona quando visitante recebe 401 de recurso privado', async () => {
    const refreshAccessToken = vi.fn()
    const navigate = vi.fn()
    const notifyWarning = vi.fn()

    TestBed.configureTestingModule({
      providers: [
        {
          provide: AuthService,
          useValue: {
            isAuthRateLimited: () => false,
            authRateLimitRemainingSeconds: () => 0,
            isVisitorSession: () => true,
            refreshAccessToken,
            captureRateLimit: vi.fn()
          }
        },
        { provide: Router, useValue: { url: '/conversations', navigate } },
        { provide: NotificationService, useValue: { notifyWarning } }
      ]
    })

    const next = vi.fn((req: HttpRequest<unknown>) =>
      throwError(() => new HttpErrorResponse({ status: 401, statusText: 'Unauthorized', url: req.url }))
    )

    const req = new HttpRequest('GET', '/api/v1/chat/conversations')
    const out$ = TestBed.runInInjectionContext(() => authSessionInterceptor(req, next))

    await expect(firstValueFrom(out$)).rejects.toBeInstanceOf(HttpErrorResponse)
    expect(refreshAccessToken).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalled()
    expect(notifyWarning).not.toHaveBeenCalled()
    expect(next).toHaveBeenCalledTimes(1)
  })
})
