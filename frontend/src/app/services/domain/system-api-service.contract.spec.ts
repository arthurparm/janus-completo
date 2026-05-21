import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'

import { SystemApiService } from './system-api-service'

describe('SystemApiService (contract)', () => {
  let http: HttpTestingController
  let svc: SystemApiService

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    })
    http = TestBed.inject(HttpTestingController)
    svc = TestBed.inject(SystemApiService)
  })

  afterEach(() => {
    http.verify()
  })

  it('health deve chamar GET /healthz', () => {
    svc.health().subscribe()
    const req = http.expectOne('/healthz')
    expect(req.request.method).toBe('GET')
    req.flush({ status: 'ok' })
  })

  it('getSystemStatus deve chamar GET /api/v1/system/status com ngsw-bypass', () => {
    svc.getSystemStatus().subscribe()
    const req = http.expectOne('/api/v1/system/status')
    expect(req.request.method).toBe('GET')
    expect(req.request.headers.get('ngsw-bypass')).toBe('true')
    req.flush({ status: 'ok' })
  })

  it('getSystemOverview deve chamar GET /api/v1/system/overview com ngsw-bypass', () => {
    svc.getSystemOverview().subscribe()
    const req = http.expectOne('/api/v1/system/overview')
    expect(req.request.method).toBe('GET')
    expect(req.request.headers.get('ngsw-bypass')).toBe('true')
    req.flush({ system_status: { status: 'ok' }, services_status: [], workers_status: [] })
  })
})

