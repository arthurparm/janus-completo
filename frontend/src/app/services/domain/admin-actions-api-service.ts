import { HttpClient } from '@angular/common/http'
import { Injectable } from '@angular/core'
import { Observable } from 'rxjs'

import { ApiContextService } from '../api-context.service'

export interface AdminActionOptions {
  pathParams?: Record<string, string | number>
  queryParams?: Record<string, string | number | boolean | string[] | number[]>
  payload?: Record<string, unknown>
}

@Injectable({ providedIn: 'root' })
export class AdminActionsApiService {
  constructor(
    private readonly http: HttpClient,
    private readonly apiContext: ApiContextService,
  ) {}

  execute<T>(operationId: string, options: AdminActionOptions = {}): Observable<T> {
    return this.http.post<T>(this.apiContext.buildUrl('/api/v1/admin-actions'), this.requestBody(operationId, options))
  }

  executeText(operationId: string, options: AdminActionOptions = {}): Observable<string> {
    return this.http.post(this.apiContext.buildUrl('/api/v1/admin-actions'), this.requestBody(operationId, options), {
      responseType: 'text',
    })
  }

  private requestBody(operationId: string, options: AdminActionOptions): Record<string, unknown> {
    return {
      operation_id: operationId,
      path_params: options.pathParams ?? {},
      query_params: options.queryParams ?? {},
      payload: options.payload ?? {},
    }
  }
}
