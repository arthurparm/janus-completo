import { HttpRequest, HttpResponse } from '@angular/common/http'
import { TestBed } from '@angular/core/testing'
import { firstValueFrom, of } from 'rxjs'
import { vi } from 'vitest'
import { baseUrlInterceptor } from './base-url.interceptor'

describe('baseUrlInterceptor', () => {
  async function interceptedUrl(url: string): Promise<string> {
    TestBed.configureTestingModule({})
    const next = vi.fn((request: HttpRequest<unknown>) =>
      of(new HttpResponse({ status: 200, url: request.url })),
    )
    const request = new HttpRequest('GET', url)

    await firstValueFrom(
      TestBed.runInInjectionContext(() => baseUrlInterceptor(request, next)),
    )

    return next.mock.calls[0][0].url
  }

  it.each([
    ['/public-api/api/v1/auth/oidc-config', '/public-api/api/v1/auth/oidc-config'],
    ['/api/v1/users/me', '/api/v1/users/me'],
    ['/v1/users/me', '/api/v1/users/me'],
    ['https://idp.example/.well-known/openid-configuration', 'https://idp.example/.well-known/openid-configuration'],
  ])('maps %s to %s', async (input, expected) => {
    expect(await interceptedUrl(input)).toBe(expected)
  })
})
