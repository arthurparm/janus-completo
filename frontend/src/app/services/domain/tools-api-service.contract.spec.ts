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

  it('getTools deve montar querystring para /api/v1/tools/', () => {
    svc.getTools('system', 'admin', 'a,b').subscribe()
    const req = http.expectOne('/api/v1/tools/?category=system&permission_level=admin&tags=a%2Cb')
    expect(req.request.method).toBe('GET')
    req.flush({ tools: [] })
  })
})

