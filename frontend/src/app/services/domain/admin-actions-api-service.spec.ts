import { provideHttpClient } from '@angular/common/http'
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'

import { AdminActionsApiService } from './admin-actions-api-service'

describe('AdminActionsApiService', () => {
  let service: AdminActionsApiService
  let http: HttpTestingController

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] })
    service = TestBed.inject(AdminActionsApiService)
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => http.verify())

  it('envia somente operation_id e parâmetros estruturados para a fachada', () => {
    service.execute('get_goal', {
      pathParams: { goal_id: 'goal-1' },
      queryParams: { include_history: true },
      payload: { reason: 'review' },
    }).subscribe()

    const request = http.expectOne('/api/v1/admin-actions')
    expect(request.request.method).toBe('POST')
    expect(request.request.body).toEqual({
      operation_id: 'get_goal',
      path_params: { goal_id: 'goal-1' },
      query_params: { include_history: true },
      payload: { reason: 'review' },
    })
    request.flush({ ok: true })
  })
})
