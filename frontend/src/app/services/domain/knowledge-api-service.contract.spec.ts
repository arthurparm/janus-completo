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

  function expectAdminAction(operationId: string) {
    const req = http.expectOne('/api/v1/admin-actions')
    expect(req.request.method).toBe('POST')
    expect(req.request.body.operation_id).toBe(operationId)
    return req
  }

  it('getKnowledgeHealth deve usar a fachada administrativa', () => {
    svc.getKnowledgeHealth().subscribe()
    const req = expectAdminAction('knowledge_health_api_v1_knowledge_health_get')
    req.flush({ status: 'ok' })
  })

  it('getKnowledgeHealthDetailed deve chamar GET /api/v1/knowledge/health/detailed', () => {
    svc.getKnowledgeHealthDetailed().subscribe()
    const req = expectAdminAction('detailed_health_check_api_v1_knowledge_health_detailed_get')
    req.flush({ status: 'ok' })
  })

  it('resetKnowledgeCircuitBreaker deve chamar POST /api/v1/knowledge/health/reset-circuit-breaker', () => {
    svc.resetKnowledgeCircuitBreaker().subscribe()
    const req = expectAdminAction('reset_circuit_breaker_api_v1_knowledge_health_reset_circuit_breaker_post')
    req.flush({ message: 'ok' })
  })

  it('getKnowledgeStats deve chamar GET /api/v1/knowledge/stats', () => {
    svc.getKnowledgeStats().subscribe()
    const req = expectAdminAction('get_knowledge_stats_api_v1_knowledge_stats_get')
    req.flush({ total_nodes: 1, total_relationships: 0 })
  })

  it('getKnowledgeNodeTypes deve chamar GET /api/v1/knowledge/node-types', () => {
    svc.getKnowledgeNodeTypes().subscribe()
    const req = expectAdminAction('get_node_types_api_v1_knowledge_node_types_get')
    req.flush({ types: ['Entity'] })
  })
})

