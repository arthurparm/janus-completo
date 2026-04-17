import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { ContextualGraphResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class GraphApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getContextualGraph(query?: string, conversationId?: string, hops: number = 1): Observable<ContextualGraphResponse> {
    const qs = new URLSearchParams();
    if (query) qs.set('query', query);
    if (conversationId) qs.set('conversation_id', conversationId);
    qs.set('hops', String(hops));
    return this.http.get<ContextualGraphResponse>(this.apiContext.buildUrl(`/api/v1/admin/graph/contextual?${qs.toString()}`));
  }
}
