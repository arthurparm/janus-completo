import { HttpContext, HttpErrorResponse, HttpRequest, HttpResponse } from '@angular/common/http'
import { TestBed } from '@angular/core/testing'
import { Router } from '@angular/router'
import { firstValueFrom, of, throwError } from 'rxjs'
import { vi } from 'vitest'
import { AuthService } from '../auth/auth.service'
import { NotificationService } from '../notifications/notification.service'
import { SKIP_AUTH_SESSION, authSessionInterceptor } from './auth-session.interceptor'

describe('authSessionInterceptor OIDC', () => {
  it('ignora tratamento de sessÃ£o quando SKIP_AUTH_SESSION estiver ativo', async () => {
    TestBed.configureTestingModule({})
    const next = vi.fn(() => of(new HttpResponse({ status: 200, body: { ok: true } })))
    const req = new HttpRequest('GET', '/public-api/api/v1/auth/oidc-config', null, {
      context: new HttpContext().set(SKIP_AUTH_SESSION, true)
    })

    const response = await firstValueFrom(
      TestBed.runInInjectionContext(() => authSessionInterceptor(req, next))
    )

    expect(response).toBeInstanceOf(HttpResponse)
    expect(next).toHaveBeenCalledTimes(1)
  })

  it('encerra a sessÃ£o e exige novo OIDC em 401 sem repetir a requisiÃ§Ã£o', async () => {
    const logout = vi.fn().mockResolvedValue(undefined)
    const navigate = vi.fn()
    const notifyWarning = vi.fn()
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: { logout } },
        { provide: Router, useValue: { url: '/private', navigate } },
        { provide: NotificationService, useValue: { notifyWarning } }
      ]
    })
    const next = vi.fn(() =>
      throwError(() => new HttpErrorResponse({ status: 401, statusText: 'Unauthorized' }))
    )

    const request = new HttpRequest('GET', '/api/v1/users/me')
    const output = TestBed.runInInjectionContext(() => authSessionInterceptor(request, next))

    await expect(firstValueFrom(output)).rejects.toBeInstanceOf(HttpErrorResponse)
    expect(logout).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith(['/login'], expect.objectContaining({ replaceUrl: true }))
    expect(notifyWarning).toHaveBeenCalledTimes(1)
    expect(next).toHaveBeenCalledTimes(1)
  })
})
