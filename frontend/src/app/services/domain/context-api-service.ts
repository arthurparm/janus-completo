import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { ContextInfo, WebSearchResult, WebCacheStatus } from '../../models';

@Injectable({ providedIn: 'root' })
export class ContextApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getCurrentContext(): Observable<ContextInfo> {
    return this.http.get<ContextInfo>(this.apiContext.buildUrl(`/api/v1/context/current`))
  }

searchWeb(query: string, max_results: number = 5, search_depth: 'basic' | 'advanced' = 'basic'): Observable<WebSearchResult> {
    const params = new URLSearchParams({ query, max_results: String(max_results), search_depth })
    return this.http.get<WebSearchResult>(this.apiContext.buildUrl(`/api/v1/context/web-search?${params.toString()}`))
  }

getWebCacheStatus(): Observable<WebCacheStatus> {
    return this.http.get<WebCacheStatus>(this.apiContext.buildUrl(`/api/v1/context/web-cache/status`))
  }

invalidateWebCache(query?: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.apiContext.buildUrl(`/api/v1/context/web-cache/invalidate`), { query })
  }
}
