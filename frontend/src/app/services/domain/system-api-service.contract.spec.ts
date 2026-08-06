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

  it('health deve chamar GET /healthz/user', () => {
    svc.health().subscribe()
    const req = http.expectOne('/healthz/user')
    expect(req.request.method).toBe('GET')
    req.flush({ status: 'ok' })
  })

  it('getSystemStatus deve chamar GET /api/v1/system/status/user com ngsw-bypass', () => {
    svc.getSystemStatus().subscribe()
    const req = http.expectOne('/api/v1/system/status/user')
    expect(req.request.method).toBe('GET')
    expect(req.request.headers.get('ngsw-bypass')).toBe('true')
    req.flush({ status: 'ok' })
  })

  it('getSystemOverview deve usar a fachada administrativa', () => {
    svc.getSystemOverview().subscribe()
    const req = http.expectOne('/api/v1/admin-actions')
    expect(req.request.method).toBe('POST')
    expect(req.request.body.operation_id).toBe('get_system_overview_api_v1_system_overview_get')
    req.flush({ system_status: { status: 'ok' }, services_status: [], workers_status: [] })
  })
})

