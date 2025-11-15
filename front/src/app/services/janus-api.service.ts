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
export interface ReviewerMetricsResponse { user_id: number; decisions_total: number; approvals: number; rejections: number; synonyms: number; approval_rate: number; rejection_rate: number; avg_latency_ms: number }
export interface PeriodReportResponse { period: string; buckets: { bucket: string; total: number; promote: number; reject: number; synonym: number }[] }

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
export interface ProductivityLimitUsage { max_per_day: number; used: number; remaining: number }
export interface ProductivityLimitsStatusResponse { user_id: string; limits: Record<string, ProductivityLimitUsage> }
export interface GoogleOAuthStartResponse { authorize_url: string }
export interface GoogleOAuthCallbackResponse { status: string; state?: string }
export interface CalendarEvent { title: string; start_ts: number; end_ts: number; location?: string; notes?: string }
export interface CalendarAddRequest { user_id: number; event: CalendarEvent; index?: boolean }
export interface MailMessage { to: string; subject: string; body: string }
export interface MailSendRequest { user_id: number; message: MailMessage; index?: boolean }
export interface QueueAck { status: string; task_id?: string }
export interface ExperimentWinnerResponse { winner: any; arms: any[]; metric: string; p_value?: number | null }
export interface AssignmentResponse { experiment_id: number; user_id: string; arm_id: number }
export interface FeedbackSubmitResponse { id: number; status: string }
export interface DeploymentStageResponse { model_id: string; status: string; rollout_percent: number }
export interface DeploymentPublishResponse { model_id: string; status: string; rollout_percent: number }
export interface GPUBudgetResponse { user_id: string; budget: number }
export interface GPUUsageResponse { used: number; updated_at?: string | null }
export interface ABExperimentSetResponse { status: string; LLM_AB_EXPERIMENT_ID: number }

export interface WorkersStatusResponse { workers: WorkerStatusResponse[] }

@Injectable({providedIn: 'root'})
export class JanusApiService {
  constructor(private http: HttpClient) {}

  private _reqId(): string {
    const s = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
    return s.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0
      const v = c === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  }

  private _projectId?: string
  private _sessionId?: string
  private _conversationId?: string

  setProjectId(project_id?: string) { this._projectId = project_id || undefined }
  setSessionId(session_id?: string) { this._sessionId = session_id || undefined }
  setConversationId(conversation_id?: string) { this._conversationId = conversation_id || undefined }
  clearContext() { this._projectId = undefined; this._sessionId = undefined; this._conversationId = undefined }

  private headersFor(userId?: number | string): Record<string, string> {
    const h: Record<string, string> = { 'X-Request-ID': this._reqId() }
    if (typeof userId !== 'undefined') h['X-User-Id'] = String(userId)
    if (this._projectId) h['X-Project-Id'] = this._projectId
    if (this._sessionId) h['X-Session-Id'] = this._sessionId
    if (this._conversationId) h['X-Conversation-Id'] = this._conversationId
    return h
  }

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

  getReviewerMetrics(user_id: number, start_ts?: number, end_ts?: number): Observable<ReviewerMetricsResponse> {
    const qs = new URLSearchParams()
    qs.set('user_id', String(user_id))
    if (typeof start_ts !== 'undefined') qs.set('start_ts', String(start_ts))
    if (typeof end_ts !== 'undefined') qs.set('end_ts', String(end_ts))
    return this.http.get<ReviewerMetricsResponse>(`/api/v1/observability/hitl/metrics/reviewer?${qs.toString()}`)
  }

  getHitlReports(period: 'daily'|'weekly'|'monthly' = 'daily', start_ts?: number, end_ts?: number): Observable<PeriodReportResponse> {
    const qs = new URLSearchParams()
    qs.set('period', period)
    if (typeof start_ts !== 'undefined') qs.set('start_ts', String(start_ts))
    if (typeof end_ts !== 'undefined') qs.set('end_ts', String(end_ts))
    return this.http.get<PeriodReportResponse>(`/api/v1/observability/hitl/reports?${qs.toString()}`)
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
    const headers = this.headersFor(user_id)
    return this.http.post<TokenResponse>(`/api/v1/auth/token`, { user_id, expires_in }, { headers })
  }

  // Productivity limits status
  getProductivityLimitsStatus(user_id: number): Observable<ProductivityLimitsStatusResponse> {
    const headers = this.headersFor(user_id)
    return this.http.get<ProductivityLimitsStatusResponse>(`/api/v1/productivity/limits/status?user_id=${encodeURIComponent(String(user_id))}`, { headers })
  }

  // Google OAuth
  googleOAuthStart(user_id: number, scope: 'calendar' | 'mail' | 'notes' = 'calendar'): Observable<GoogleOAuthStartResponse> {
    const headers = this.headersFor(user_id)
    const qs = new URLSearchParams({ user_id: String(user_id), scope })
    return this.http.get<GoogleOAuthStartResponse>(`/api/v1/productivity/oauth/google/start?${qs.toString()}`, { headers })
  }

  googleOAuthCallback(code: string, state: string): Observable<GoogleOAuthCallbackResponse> {
    return this.http.post<GoogleOAuthCallbackResponse>(`/api/v1/productivity/oauth/google/callback`, { code, state })
  }

  // Calendar and Mail operations (queued)
  calendarAddEvent(req: CalendarAddRequest): Observable<QueueAck> {
    const headers = this.headersFor(req.user_id)
    return this.http.post<QueueAck>(`/api/v1/productivity/calendar/events/add`, req, { headers })
  }

  mailSend(req: MailSendRequest): Observable<QueueAck> {
    const headers = this.headersFor(req.user_id)
    return this.http.post<QueueAck>(`/api/v1/productivity/mail/messages/send`, req, { headers })
  }

  // A/B Testing
  getExperimentWinner(experiment_id: number, metric_name: string = 'accuracy'): Observable<ExperimentWinnerResponse> {
    const qs = new URLSearchParams({ metric_name })
    return this.http.get<ExperimentWinnerResponse>(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/winner?${qs.toString()}`)
  }

  assignUserToExperiment(experiment_id: number, user_id: string): Observable<AssignmentResponse> {
    return this.http.post<AssignmentResponse>(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/assign`, { user_id })
  }

  submitExperimentFeedback(experiment_id: number, user_id: string, rating: number, notes?: string): Observable<FeedbackSubmitResponse> {
    return this.http.post<FeedbackSubmitResponse>(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/feedback`, { user_id, rating, notes })
  }

  getExperimentFeedbackStats(experiment_id: number): Observable<any> {
    return this.http.get<any>(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/feedback/stats`)
  }

  // Deployment
  stageDeployment(model_id: string, rollout_percent: number): Observable<DeploymentStageResponse> {
    return this.http.post<DeploymentStageResponse>(`/api/v1/deployment/stage`, { model_id, rollout_percent })
  }

  publishDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.http.post<DeploymentPublishResponse>(`/api/v1/deployment/publish?model_id=${encodeURIComponent(model_id)}`, {})
  }

  rollbackDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.http.post<DeploymentPublishResponse>(`/api/v1/deployment/rollback?model_id=${encodeURIComponent(model_id)}`, {})
  }

  precheckDeployment(model_id: string): Observable<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }> {
    return this.http.post<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }>(`/api/v1/deployment/precheck?model_id=${encodeURIComponent(model_id)}`, {})
  }

  // GPU resources
  getGPUUsage(user_id: string): Observable<GPUUsageResponse> {
    return this.http.get<GPUUsageResponse>(`/api/v1/resources/gpu/usage/${encodeURIComponent(user_id)}`)
  }

  setGPUBudget(user_id: string, budget: number): Observable<GPUBudgetResponse> {
    return this.http.post<GPUBudgetResponse>(`/api/v1/resources/gpu/budget`, { user_id, budget })
  }

  // LLM A/B experiment
  setLLMABExperiment(experiment_id: number): Observable<ABExperimentSetResponse> {
    return this.http.post<ABExperimentSetResponse>(`/api/v1/llm/ab/set-experiment`, { experiment_id })
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
