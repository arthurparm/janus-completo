import { HttpErrorResponse, HttpRequest, HttpResponse } from '@angular/common/http'
import { TestBed } from '@angular/core/testing'
import { firstValueFrom, of, throwError } from 'rxjs'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NotificationService } from '../notifications/notification.service'
import { DemoService } from '../services/demo.service'
import { errorMappingInterceptor } from './error-mapping.interceptor'

describe('errorMappingInterceptor', () => {
  const demoService = {
    enableOfflineMode: vi.fn(),
    resetMode: vi.fn(),
    isOffline: vi.fn(() => false),
  }
  const notifications = { notify: vi.fn() }

  beforeEach(() => {
    vi.clearAllMocks()
    TestBed.configureTestingModule({
      providers: [
        { provide: DemoService, useValue: demoService },
        { provide: NotificationService, useValue: notifications },
      ],
    })
  })

  async function run(url: string, responseStatus = 200): Promise<void> {
    const request = new HttpRequest('GET', url)
    const next = responseStatus < 400
      ? () => of(new HttpResponse({ status: responseStatus, url }))
      : () => throwError(() => new HttpErrorResponse({ status: responseStatus, url }))

    await firstValueFrom(
      TestBed.runInInjectionContext(() => errorMappingInterceptor(request, next)),
    )
  }

  it('clears a stale offline state after a successful backend response', async () => {
    await run('/api/v1/users/me')

    expect(demoService.resetMode).toHaveBeenCalledOnce()
  })

  it('marks the app offline when the Janus backend is unavailable', async () => {
    await expect(run('/healthz/user', 503)).rejects.toBeInstanceOf(HttpErrorResponse)

    expect(demoService.enableOfflineMode).toHaveBeenCalledOnce()
  })

  it('does not label an application-level HTTP 500 as a disconnected backend', async () => {
    await expect(run('/api/v1/optional-widget', 500)).rejects.toBeInstanceOf(HttpErrorResponse)

    expect(demoService.enableOfflineMode).not.toHaveBeenCalled()
  })

  it('does not let an external identity-provider failure control backend status', async () => {
    await expect(run('http://localhost:8400/token', 503)).rejects.toBeInstanceOf(HttpErrorResponse)

    expect(demoService.enableOfflineMode).not.toHaveBeenCalled()
    expect(demoService.resetMode).not.toHaveBeenCalled()
  })
})
