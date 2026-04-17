import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { RagUserChatResponse, RagUserChatV2Response, KnowledgeHealthResponse, KnowledgeHealthDetailedResponse, KnowledgeSpace, KnowledgeSpaceStatus, KnowledgeSpaceCreateRequest, KnowledgeSpaceListResponse, KnowledgeSpaceAttachRequest, KnowledgeSpaceConsolidationResponse, KnowledgeSpaceQueryResponse, RagSearchResponse, RagHybridResponse, KnowledgeStats, EntityRelationshipsResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class KnowledgeApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

createKnowledgeSpace(payload: KnowledgeSpaceCreateRequest): Observable<KnowledgeSpace> {
    const headers = payload.user_id ? this.apiContext.headersFor(payload.user_id) : undefined
    return this.http.post<KnowledgeSpace>(
      this.apiContext.buildUrl('/api/v1/knowledge/spaces'),
      payload,
      headers ? { headers } : undefined
    )
  }

listKnowledgeSpaces(userId?: string, limit: number = 100): Observable<KnowledgeSpaceListResponse> {
    const qs = new URLSearchParams()
    if (userId) qs.set('user_id', String(userId))
    qs.set('limit', String(limit))
    const headers = userId ? this.apiContext.headersFor(userId) : undefined
    return this.http.get<KnowledgeSpaceListResponse>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces?${qs.toString()}`),
      headers ? { headers } : undefined
    )
  }

getKnowledgeSpaceStatus(knowledgeSpaceId: string, userId?: string): Observable<KnowledgeSpaceStatus> {
    const qs = new URLSearchParams()
    if (userId) qs.set('user_id', String(userId))
    const headers = userId ? this.apiContext.headersFor(userId) : undefined
    return this.http.get<KnowledgeSpaceStatus>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }

attachDocumentToKnowledgeSpace(
    knowledgeSpaceId: string,
    docId: string,
    payload: KnowledgeSpaceAttachRequest = {},
  ): Observable<{ status: string; document: Record<string, unknown> }> {
    const headers = payload.user_id ? this.apiContext.headersFor(payload.user_id) : undefined
    return this.http.post<{ status: string; document: Record<string, unknown> }>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/documents/${encodeURIComponent(docId)}/attach`),
      payload,
      headers ? { headers } : undefined
    )
  }

consolidateKnowledgeSpace(
    knowledgeSpaceId: string,
    payload: { user_id?: string; limit_docs?: number } = {},
  ): Observable<KnowledgeSpaceConsolidationResponse> {
    const headers = payload.user_id ? this.apiContext.headersFor(payload.user_id) : undefined
    return this.http.post<KnowledgeSpaceConsolidationResponse>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/consolidate`),
      payload,
      headers ? { headers } : undefined
    )
  }

queryKnowledgeSpace(
    knowledgeSpaceId: string,
    payload: { user_id?: string; question: string; mode?: string; limit?: number },
  ): Observable<KnowledgeSpaceQueryResponse> {
    const headers = payload.user_id ? this.apiContext.headersFor(payload.user_id) : undefined
    return this.http.post<KnowledgeSpaceQueryResponse>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/query`),
      payload,
      headers ? { headers } : undefined
    )
  }

ragSearch(params: {
    query: string
    type?: string
    origin?: string
    doc_id?: string
    file_path?: string
    limit?: number
    min_score?: number
  }): Observable<RagSearchResponse> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    if (params.type) qs.set('type', params.type)
    if (params.origin) qs.set('origin', params.origin)
    if (params.doc_id) qs.set('doc_id', params.doc_id)
    if (params.file_path) qs.set('file_path', params.file_path)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    return this.http.get<RagSearchResponse>(this.apiContext.buildUrl(`/api/v1/rag/search?${qs.toString()}`))
  }

ragUserChat(params: {
    query: string
    user_id: string
    session_id?: string
    role?: string
    limit?: number
    min_score?: number
  }): Observable<RagUserChatResponse> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    qs.set('user_id', params.user_id)
    if (params.session_id) qs.set('session_id', params.session_id)
    if (params.role) qs.set('role', params.role)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    return this.http.get<RagUserChatResponse>(this.apiContext.buildUrl(`/api/v1/rag/user-chat?${qs.toString()}`))
  }

ragUserChatV2(params: {
    query: string
    user_id?: string
    session_id?: string
    start_ts_ms?: number
    end_ts_ms?: number
    limit?: number
    min_score?: number
  }): Observable<RagUserChatV2Response> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.session_id) qs.set('session_id', params.session_id)
    if (params.start_ts_ms != null) qs.set('start_ts_ms', String(params.start_ts_ms))
    if (params.end_ts_ms != null) qs.set('end_ts_ms', String(params.end_ts_ms))
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    const headers = params.user_id ? this.apiContext.headersFor(params.user_id) : undefined
    return this.http.get<RagUserChatV2Response>(
      this.apiContext.buildUrl(`/api/v1/rag/user_chat?${qs.toString()}`),
      headers ? { headers } : undefined
    )
  }

ragHybridSearch(params: {
    query: string
    user_id?: string
    limit?: number
    min_score?: number
  }): Observable<RagHybridResponse> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    const headers = params.user_id ? this.apiContext.headersFor(params.user_id) : undefined
    return this.http.get<RagHybridResponse>(
      this.apiContext.buildUrl(`/api/v1/rag/hybrid_search?${qs.toString()}`),
      headers ? { headers } : undefined
    )
  }

ragProductivitySearch(params: {
    query: string
    user_id: string
    limit?: number
    min_score?: number
  }): Observable<RagSearchResponse> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    qs.set('user_id', params.user_id)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    const headers = this.apiContext.headersFor(params.user_id)
    return this.http.get<RagSearchResponse>(this.apiContext.buildUrl(`/api/v1/rag/productivity?${qs.toString()}`), { headers })
  }

getKnowledgeStats(): Observable<KnowledgeStats> {
    return this.http.get<KnowledgeStats>(this.apiContext.buildUrl(`/api/v1/knowledge/stats`))
  }

getEntityRelationships(entityName: string): Observable<EntityRelationshipsResponse> {
    const qs = new URLSearchParams({ max_depth: '1', limit: '20' })
    return this.http.get<EntityRelationshipsResponse>(this.apiContext.buildUrl(`/api/v1/knowledge/entity/${encodeURIComponent(entityName)}/relationships?${qs.toString()}`))
  }

getKnowledgeHealth(): Observable<KnowledgeHealthResponse> {
    return this.http.get<KnowledgeHealthResponse>(this.apiContext.buildUrl(`/api/v1/knowledge/health`))
  }

getKnowledgeHealthDetailed(): Observable<KnowledgeHealthDetailedResponse> {
    return this.http.get<KnowledgeHealthDetailedResponse>(this.apiContext.buildUrl(`/api/v1/knowledge/health/detailed`))
  }

resetKnowledgeCircuitBreaker(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(this.apiContext.buildUrl(`/api/v1/knowledge/health/reset-circuit-breaker`), {})
  }
}
