import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { RagUserChatResponse, RagUserChatV2Response, KnowledgeHealthResponse, KnowledgeHealthDetailedResponse, KnowledgeSpace, KnowledgeSpaceStatus, KnowledgeSpaceCreateRequest, KnowledgeSpaceListResponse, KnowledgeSpaceAttachRequest, KnowledgeSpaceConsolidationResponse, KnowledgeSpaceQueryResponse, RagSearchResponse, RagHybridResponse, KnowledgeStats, EntityRelationshipsResponse, KnowledgeNodeTypesResponse } from '../../models';
import { AdminActionsApiService } from './admin-actions-api-service';

@Injectable({ providedIn: 'root' })
export class KnowledgeApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService,
    private adminActions: AdminActionsApiService
  ) {}

createKnowledgeSpace(payload: KnowledgeSpaceCreateRequest): Observable<KnowledgeSpace> {
    const headers = this.apiContext.headersFor()
    return this.http.post<KnowledgeSpace>(
      this.apiContext.buildUrl('/api/v1/knowledge/spaces'),
      payload,
      { headers }
    )
  }

listKnowledgeSpaces(limit: number = 100): Observable<KnowledgeSpaceListResponse> {
    const qs = new URLSearchParams()
    qs.set('limit', String(limit))
    const headers = this.apiContext.headersFor()
    return this.http.get<KnowledgeSpaceListResponse>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces?${qs.toString()}`),
      { headers }
    )
  }

getKnowledgeSpaceStatus(knowledgeSpaceId: string): Observable<KnowledgeSpaceStatus> {
    const qs = new URLSearchParams()
    const headers = this.apiContext.headersFor()
    return this.http.get<KnowledgeSpaceStatus>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}${qs.toString() ? '?' + qs.toString() : ''}`),
      { headers }
    )
  }

attachDocumentToKnowledgeSpace(
    knowledgeSpaceId: string,
    docId: string,
    payload: KnowledgeSpaceAttachRequest = {},
  ): Observable<{ status: string; document: Record<string, unknown> }> {
    const headers = this.apiContext.headersFor()
    return this.http.post<{ status: string; document: Record<string, unknown> }>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/documents/${encodeURIComponent(docId)}/attach`),
      payload,
      { headers }
    )
  }

consolidateKnowledgeSpace(
    knowledgeSpaceId: string,
    payload: { limit_docs?: number } = {},
  ): Observable<KnowledgeSpaceConsolidationResponse> {
    const headers = this.apiContext.headersFor()
    return this.http.post<KnowledgeSpaceConsolidationResponse>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/consolidate`),
      payload,
      { headers }
    )
  }

queryKnowledgeSpace(
    knowledgeSpaceId: string,
    payload: { question: string; mode?: string; limit?: number },
  ): Observable<KnowledgeSpaceQueryResponse> {
    const headers = this.apiContext.headersFor()
    return this.http.post<KnowledgeSpaceQueryResponse>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/query`),
      payload,
      { headers }
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
    session_id?: string
    role?: string
    limit?: number
    min_score?: number
  }): Observable<RagUserChatResponse> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    if (params.session_id) qs.set('session_id', params.session_id)
    if (params.role) qs.set('role', params.role)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    return this.http.get<RagUserChatResponse>(this.apiContext.buildUrl(`/api/v1/rag/user-chat?${qs.toString()}`))
  }

ragUserChatV2(params: {
    query: string
    session_id?: string
    start_ts_ms?: number
    end_ts_ms?: number
    limit?: number
    min_score?: number
  }): Observable<RagUserChatV2Response> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    if (params.session_id) qs.set('session_id', params.session_id)
    if (params.start_ts_ms != null) qs.set('start_ts_ms', String(params.start_ts_ms))
    if (params.end_ts_ms != null) qs.set('end_ts_ms', String(params.end_ts_ms))
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    const headers = this.apiContext.headersFor()
    return this.http.get<RagUserChatV2Response>(
      this.apiContext.buildUrl(`/api/v1/rag/user-chat?${qs.toString()}`),
      { headers }
    )
  }

ragHybridSearch(params: {
    query: string
    limit?: number
    min_score?: number
  }): Observable<RagHybridResponse> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    const headers = this.apiContext.headersFor()
    return this.http.get<RagHybridResponse>(
      this.apiContext.buildUrl(`/api/v1/rag/hybrid_search?${qs.toString()}`),
      { headers }
    )
  }

ragProductivitySearch(params: {
    query: string
    limit?: number
    min_score?: number
  }): Observable<RagSearchResponse> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    const headers = this.apiContext.headersFor()
    return this.http.get<RagSearchResponse>(this.apiContext.buildUrl(`/api/v1/rag/productivity?${qs.toString()}`), { headers })
  }

getKnowledgeStats(): Observable<KnowledgeStats> {
    return this.adminActions.execute<KnowledgeStats>('get_knowledge_stats_api_v1_knowledge_stats_get')
  }

getKnowledgeNodeTypes(): Observable<KnowledgeNodeTypesResponse> {
    return this.adminActions.execute<KnowledgeNodeTypesResponse>('get_node_types_api_v1_knowledge_node_types_get')
  }

getEntityRelationships(entityName: string): Observable<EntityRelationshipsResponse> {
    return this.adminActions.execute<EntityRelationshipsResponse>('get_entity_relationships_api_v1_knowledge_entity__entity_name__relationships_get', {
      pathParams: { entity_name: entityName },
      queryParams: { max_depth: 1, limit: 20 },
    })
  }

getKnowledgeHealth(): Observable<KnowledgeHealthResponse> {
    return this.adminActions.execute<KnowledgeHealthResponse>('knowledge_health_api_v1_knowledge_health_get')
  }

getKnowledgeHealthDetailed(): Observable<KnowledgeHealthDetailedResponse> {
    return this.adminActions.execute<KnowledgeHealthDetailedResponse>('detailed_health_check_api_v1_knowledge_health_detailed_get')
  }

resetKnowledgeCircuitBreaker(): Observable<{ message: string }> {
    return this.adminActions.execute<{ message: string }>('reset_circuit_breaker_api_v1_knowledge_health_reset_circuit_breaker_post')
  }
}
