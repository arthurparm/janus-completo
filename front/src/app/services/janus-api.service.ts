import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {Observable} from 'rxjs';

export interface SystemStatus {
  app_name: string;
  version: string;
  environment: string;
  status: string;
  timestamp?: string;
  uptime_seconds?: number;
  system?: Record<string, any>;
  process?: Record<string, any>;
  performance?: Record<string, any>;
  config?: Record<string, any>;
}

export interface ServiceHealthItem {
  key: string;
  name: string;
  status: string;
  metric_text?: string | null;
}

export interface ServiceHealthResponse {
  services: ServiceHealthItem[];
}

export interface WorkerStatusResponse {
  id: string;
  status: string;
  last_heartbeat: Date;
  tasks_processed: number;
}

export interface SystemOverviewResponse {
  system_status: SystemStatus;
  services_status: ServiceHealthItem[];
  workers_status: WorkerStatusResponse[];
}

// LLM providers
export interface LLMProviderMeta { priority?: number; enabled?: boolean; models?: string[]; type?: string }
export type LLMProvidersResponse = Record<string, LLMProviderMeta>;

// LLM health
export interface LLMSubsystemHealth {
  status: string;
  providers?: Record<string, { status: string; latency_ms?: number; error?: string | null }>;
}

export interface LLMCacheEntry { [key: string]: any }
export interface LLMCacheStatusResponse { total_cached: number; cache_entries: LLMCacheEntry[] }
export interface CircuitBreakerStatus { provider: string; state: string; failure_count: number; last_failure_time?: number | null }

export interface MetricsSummary {
  llm: { cached_llms: number; circuit_breakers: Record<string, { state: string; failure_count: number }> };
  multi_agent: { active_agents: number; workspace_tasks: number; workspace_artifacts: number };
  poison_pills: Record<string, any>;
}

// Observability health
export interface ObservabilitySystemHealth {
  status: string;
  dependencies?: Record<string, { status: string; details?: Record<string, unknown> }>;
}

export interface QuarantinedMessage {
  message_id: string; queue: string; reason: string; failure_count: number; quarantined_at: string;
}

export interface QuarantinedMessagesResponse {
  total_quarantined: number; messages: QuarantinedMessage[];
}

export interface GraphQuarantineItem { node_id: number; reason?: string; type?: string; from_name?: string; to_name?: string; confidence?: number; source_snippet?: string }
export type GraphQuarantineListResponse = GraphQuarantineItem[]

export interface AuditEvent { id: number; user_id?: number; endpoint?: string; action?: string; tool?: string; status?: string; latency_ms?: number; trace_id?: string; created_at?: number }
export interface AuditEventsResponse { total: number; events: AuditEvent[] }

// Poison pill stats
export interface PoisonPillStats {
  total: number;
  by_queue: Record<string, { count: number; last_quarantined_at?: string }>;
}

export interface ContextInfo { [key: string]: any }
export interface WebSearchResult { [key: string]: any }
export interface WebCacheStatus { [key: string]: any }

export interface ChatStartResponse { conversation_id: string }
export interface ChatMessage { role: string; content: string; timestamp?: string }
export interface ChatMessageResponse { message?: ChatMessage; assistant_message?: ChatMessage; messages?: ChatMessage[] }
export interface ChatHistoryResponse { conversation_id: string; messages: ChatMessage[] }
export interface ConversationMeta { conversation_id: string; title?: string; last_message_at?: string }
export interface ConversationsListResponse { conversations: ConversationMeta[] }
export interface UserRolesResponse { user_id: number; roles: string[] }
export interface TokenResponse { token: string }

export interface WorkersStatusResponse { workers: WorkerStatusResponse[] }

@Injectable({providedIn: 'root'})
export class JanusApiService {
  constructor(private http: HttpClient) {}

  // Basic API health (useful for quick checks)
  health(): Observable<{status: string}> {
    return this.http.get<{status: string}>(`/healthz`);
  }

  // System status overview
  getSystemStatus(): Observable<SystemStatus> {
    return this.http.get<SystemStatus>(`/api/v1/system/status`);
  }

  // Services health breakdown
  getServicesHealth(): Observable<ServiceHealthResponse> {
    return this.http.get<ServiceHealthResponse>(`/api/v1/system/health/services`);
  }

  // Workers orchestration
  getWorkersStatus(): Observable<WorkersStatusResponse> {
    return this.http.get<WorkersStatusResponse>(`/api/v1/workers/status`);
  }

  // Consolidated System Overview
  getSystemOverview(): Observable<SystemOverviewResponse> {
    return this.http.get<SystemOverviewResponse>(`/api/v1/system/overview`);
  }

  startAllWorkers(): Observable<any> {
    return this.http.post(`/api/v1/workers/start-all`, {});
  }

  stopAllWorkers(): Observable<any> {
    return this.http.post(`/api/v1/workers/stop-all`, {});
  }
  // LLM subsystem
  listLLMProviders(): Observable<LLMProvidersResponse> {
    return this.http.get<LLMProvidersResponse>(`/api/v1/llm/providers`)
  }

  getLLMHealth(): Observable<LLMSubsystemHealth> {
    return this.http.get<LLMSubsystemHealth>(`/api/v1/llm/health`)
  }

  getLLMCacheStatus(): Observable<LLMCacheStatusResponse> {
    return this.http.get<LLMCacheStatusResponse>(`/api/v1/llm/cache/status`)
  }

  getLLMCircuitBreakers(): Observable<CircuitBreakerStatus[]> {
    return this.http.get<CircuitBreakerStatus[]>(`/api/v1/llm/circuit-breakers`)
  }

  // Observability
  getObservabilitySystemHealth(): Observable<ObservabilitySystemHealth> {
    return this.http.get<ObservabilitySystemHealth>(`/api/v1/observability/health/system`)
  }

  getObservabilityMetricsSummary(): Observable<MetricsSummary> {
    return this.http.get<MetricsSummary>(`/api/v1/observability/metrics/summary`)
  }

  getQuarantinedMessages(queue?: string): Observable<QuarantinedMessagesResponse> {
    const params = queue ? `?queue=${encodeURIComponent(queue)}` : ''
    return this.http.get<QuarantinedMessagesResponse>(`/api/v1/observability/poison-pills/quarantined${params}`)
  }

  cleanupQuarantine(): Observable<any> {
    return this.http.post(`/api/v1/observability/poison-pills/cleanup`, {})
  }

  getPoisonPillStats(queue?: string): Observable<PoisonPillStats> {
    const params = queue ? `?queue=${encodeURIComponent(queue)}` : ''
    return this.http.get<PoisonPillStats>(`/api/v1/observability/poison-pills/stats${params}`)
  }

  // HITL / Observability: Graph quarantine & actions
  listGraphQuarantine(limit: number = 100, offset: number = 0, filters?: { type?: string; reason?: string; confidence_ge?: number }): Observable<GraphQuarantineListResponse> {
    const qs = new URLSearchParams()
    qs.set('limit', String(limit))
    qs.set('offset', String(offset))
    if (filters?.type) qs.set('type', filters.type)
    if (filters?.reason) qs.set('reason', filters.reason)
    if (typeof filters?.confidence_ge !== 'undefined') qs.set('confidence_ge', String(filters?.confidence_ge))
    return this.http.get<GraphQuarantineListResponse>(`/api/v1/observability/graph/quarantine?${qs.toString()}`)
  }

  promoteQuarantine(node_id: number): Observable<any> {
    return this.http.post(`/api/v1/observability/graph/quarantine/promote`, { node_id })
  }

  rejectQuarantine(node_id: number, reason: string): Observable<any> {
    return this.http.post(`/api/v1/observability/graph/quarantine/reject`, { node_id, reason })
  }

  registerSynonym(label: string, alias: string, canonical: string): Observable<any> {
    return this.http.post(`/api/v1/observability/graph/entities/synonym`, { label, alias, canonical })
  }

  listAuditEvents(params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number } = {}): Observable<AuditEventsResponse> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.tool) qs.set('tool', params.tool)
    if (params.status) qs.set('status', params.status)
    if (typeof params.start_ts !== 'undefined') qs.set('start_ts', String(params.start_ts))
    if (typeof params.end_ts !== 'undefined') qs.set('end_ts', String(params.end_ts))
    qs.set('limit', String(params.limit ?? 100))
    qs.set('offset', String(params.offset ?? 0))
    return this.http.get<AuditEventsResponse>(`/api/v1/observability/audit/events?${qs.toString()}`)
  }

  // Context
  getCurrentContext(): Observable<ContextInfo> {
    return this.http.get<ContextInfo>(`/api/v1/context/current`)
  }

  searchWeb(query: string, max_results: number = 5, search_depth: 'basic' | 'advanced' = 'basic'): Observable<WebSearchResult> {
    const params = new URLSearchParams({ query, max_results: String(max_results), search_depth })
    return this.http.get<WebSearchResult>(`/api/v1/context/web-search?${params.toString()}`)
  }

  getWebCacheStatus(): Observable<WebCacheStatus> {
    return this.http.get<WebCacheStatus>(`/api/v1/context/web-cache/status`)
  }

  invalidateWebCache(query?: string): Observable<any> {
    return this.http.post(`/api/v1/context/web-cache/invalidate`, { query })
  }

  // Chat API
  startChat(title?: string): Observable<ChatStartResponse> {
    return this.http.post<ChatStartResponse>(`/api/v1/chat/start`, { title })
  }

  sendChatMessage(conversation_id: string, content: string): Observable<ChatMessageResponse> {
    return this.http.post<ChatMessageResponse>(`/api/v1/chat/message`, { conversation_id, content })
  }

  getChatHistory(conversation_id: string): Observable<ChatHistoryResponse> {
    return this.http.get<ChatHistoryResponse>(`/api/v1/chat/${encodeURIComponent(conversation_id)}/history`)
  }

  listConversations(): Observable<ConversationsListResponse> {
    return this.http.get<ConversationsListResponse>(`/api/v1/chat/conversations`)
  }

  // Users
  getUserRoles(user_id: number): Observable<UserRolesResponse> {
    return this.http.get<UserRolesResponse>(`/api/v1/users/${encodeURIComponent(String(user_id))}/roles`)
  }

  // Auth
  issueToken(user_id: number, expires_in: number = 3600): Observable<TokenResponse> {
    const headers = { 'X-User-Id': String(user_id) }
    return this.http.post<TokenResponse>(`/api/v1/auth/token`, { user_id, expires_in }, { headers })
  }
}

export type WorkersStatusItem = WorkerStatusResponse;
  exportAuditEvents(format: 'csv'|'json', params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number; fields?: string[] } = {}): Observable<any> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.tool) qs.set('tool', params.tool)
    if (params.status) qs.set('status', params.status)
    if (typeof params.start_ts !== 'undefined') qs.set('start_ts', String(params.start_ts))
    if (typeof params.end_ts !== 'undefined') qs.set('end_ts', String(params.end_ts))
    qs.set('limit', String(params.limit ?? 1000))
    qs.set('offset', String(params.offset ?? 0))
    qs.set('format', format)
    if (params.fields && params.fields.length) qs.set('fields', params.fields.join(','))
    return this.http.get(`/api/v1/observability/audit/export?${qs.toString()}`, { responseType: 'text' })
  }
