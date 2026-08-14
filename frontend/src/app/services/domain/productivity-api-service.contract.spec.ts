import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'

import { ProductivityApiService } from './productivity-api-service'

describe('ProductivityApiService (Google OAuth contract)', () => {
  let http: HttpTestingController
  let service: ProductivityApiService

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [HttpClientTestingModule] })
    http = TestBed.inject(HttpTestingController)
    service = TestBed.inject(ProductivityApiService)
  })

  afterEach(() => http.verify())

  it('consulta o estado local do ator autenticado', () => {
    service.googleOAuthStatus().subscribe()
    const req = http.expectOne('/api/v1/productivity/oauth/google/status')
    expect(req.request.method).toBe('GET')
    req.flush({
      local_status: 'disconnected',
      capabilities: { calendar: false, mail: false },
      provider_verified: false,
    })
  })

  it('envia código e state ao callback e desconecta sem identidade fornecida pelo cliente', () => {
    service.googleOAuthCallback('code', 'state').subscribe()
    const callback = http.expectOne('/api/v1/productivity/oauth/google/callback')
    expect(callback.request.method).toBe('POST')
    expect(callback.request.body).toEqual({ code: 'code', state: 'state' })
    callback.flush({ status: 'ok' })

    service.googleOAuthDisconnect().subscribe()
    const disconnect = http.expectOne('/api/v1/productivity/oauth/google/disconnect')
    expect(disconnect.request.method).toBe('POST')
    expect(disconnect.request.body).toEqual({})
    disconnect.flush({
      status: 'disconnected',
      provider_revoked: true,
      retry_required: false,
      warning: null,
    })
  })
})
