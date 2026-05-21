import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'

import { KnowledgeApiService } from './knowledge-api-service'

describe('KnowledgeApiService (contract)', () => {
  let http: HttpTestingController
  let svc: KnowledgeApiService

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    })
    http = TestBed.inject(HttpTestingController)
    svc = TestBed.inject(KnowledgeApiService)
  })

  afterEach(() => {
    http.verify()
  })

  it('getKnowledgeHealth deve chamar GET /api/v1/knowledge/health', () => {
    svc.getKnowledgeHealth().subscribe()
    const req = http.expectOne('/api/v1/knowledge/health')
    expect(req.request.method).toBe('GET')
    req.flush({ status: 'ok' })
  })

  it('getKnowledgeHealthDetailed deve chamar GET /api/v1/knowledge/health/detailed', () => {
    svc.getKnowledgeHealthDetailed().subscribe()
    const req = http.expectOne('/api/v1/knowledge/health/detailed')
    expect(req.request.method).toBe('GET')
    req.flush({ status: 'ok' })
  })

  it('resetKnowledgeCircuitBreaker deve chamar POST /api/v1/knowledge/health/reset-circuit-breaker', () => {
    svc.resetKnowledgeCircuitBreaker().subscribe()
    const req = http.expectOne('/api/v1/knowledge/health/reset-circuit-breaker')
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({})
    req.flush({ message: 'ok' })
  })
})

