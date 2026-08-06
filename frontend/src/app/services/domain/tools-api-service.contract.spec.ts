import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'

import { ToolsApiService } from './tools-api-service'

describe('ToolsApiService (contract)', () => {
  let http: HttpTestingController
  let svc: ToolsApiService

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    })
    http = TestBed.inject(HttpTestingController)
    svc = TestBed.inject(ToolsApiService)
  })

  afterEach(() => {
    http.verify()
  })

  it('getTools deve enviar filtros estruturados para a fachada', () => {
    svc.getTools('system', 'admin', 'a,b').subscribe()
    const req = http.expectOne('/api/v1/admin-actions')
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({
      operation_id: 'list_tools_api_v1_tools__get',
      path_params: {},
      query_params: { category: 'system', permission_level: 'admin', tags: 'a,b' },
      payload: {},
    })
    req.flush({ tools: [] })
  })
})

