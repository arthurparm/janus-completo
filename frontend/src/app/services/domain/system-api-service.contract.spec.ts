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

  it('startAllWorkers deve preservar o contrato tipado dos handles registrados', () => {
    svc.startAllWorkers().subscribe((response) => {
      expect(response.count).toBe(1)
      expect(response.workers[0].registered_at).toBe('2026-08-18T12:30:00Z')
    })
    const req = http.expectOne('/api/v1/admin-actions')
    expect(req.request.body.operation_id).toBe('start_workers_api_v1_workers_start_all_post')
    req.flush({
      status: 'started',
      count: 1,
      workers: [{
        name: 'memory_maintenance',
        registered_at: '2026-08-18T12:30:00Z',
        running: true,
        done: false,
        cancelled: false,
        exception: null,
        state: 'running',
      }],
    })
  })

  it('stopAllWorkers deve preservar contagens reais do backend', () => {
    svc.stopAllWorkers().subscribe((response) => {
      expect(response.stopped_count).toBe(1)
      expect(response.ignored).toBe(0)
    })
    const req = http.expectOne('/api/v1/admin-actions')
    expect(req.request.body.operation_id).toBe('stop_workers_api_v1_workers_stop_all_post')
    req.flush({ status: 'stopped', stopped_count: 1, ignored: 0 })
  })
})
