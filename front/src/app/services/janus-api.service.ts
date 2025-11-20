import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import { API_BASE_URL } from './api.config'
import {Observable, BehaviorSubject, Subject} from 'rxjs';
declare const Janus: any;

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
export interface ConsentItem { scope: string; granted: boolean; expires_at?: string|null }
export interface ConsentsListResponse { user_id: number; consents: ConsentItem[] }

// Poison pill stats
export interface PoisonPillStats {
  total: number;
  by_queue: Record<string, { count: number; last_quarantined_at?: string }>;
}

export interface ContextInfo { [key: string]: any }
export interface WebSearchResult { [key: string]: any }
export interface WebCacheStatus { [key: string]: any }

export interface ChatStartResponse { conversation_id: string }
export interface ChatMessage { role: string; content: string; timestamp?: string; citations?: Citation[] }
export interface ChatMessageResponse { message?: ChatMessage; assistant_message?: ChatMessage; messages?: ChatMessage[] }
export interface ChatHistoryResponse { conversation_id: string; messages: ChatMessage[] }
export interface ConversationMeta { 
  conversation_id: string; 
  title?: string; 
  last_message_at?: string; 
  created_at?: number; 
  updated_at?: number; 
  last_message?: ChatMessage
  message_count?: number
  tags?: string[]
}
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
export interface UserStatusResponse { user_id: string; conversations: number; messages: number; approx_in_tokens: number; approx_out_tokens: number; vector_points: number }

// Documents / RAG
export interface UploadResponse { doc_id: string; chunks: number; status: string; consolidation?: Record<string, any> | null }
export interface DocListItem { doc_id: string; file_name?: string; chunks: number; conversation_id?: string; last_index_ts?: number }
export interface DocListResponse { items: DocListItem[] }
export interface Citation { id?: string; title?: string; url?: string; snippet?: string; score?: number; source_type?: string; doc_id?: string; file_path?: string; origin?: string }

export interface WorkersStatusResponse { workers: WorkerStatusResponse[] }

@Injectable({providedIn: 'root'})
export class JanusApiService {
  constructor(private http: HttpClient) {}
  private buildUrl(path: string): string {
    const p = String(path || '')
    if (p === '/healthz') return p
    if (p.startsWith('/api/')) return p
    if (p.startsWith('/v1/')) return `${API_BASE_URL}${p}`
    return `${API_BASE_URL}${p.startsWith('/') ? '' : '/'}${p}`
  }

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
  private _persona?: string
  private _role?: string
  private _priority?: string

  setProjectId(project_id?: string) { this._projectId = project_id || undefined }
  setSessionId(session_id?: string) { this._sessionId = session_id || undefined }
  setConversationId(conversation_id?: string) { this._conversationId = conversation_id || undefined }
  setPersona(persona?: string) { this._persona = persona || undefined }
  setRole(role?: string) { this._role = role || undefined }
  setPriority(priority?: string) { this._priority = priority || undefined }
  clearContext() { this._projectId = undefined; this._sessionId = undefined; this._conversationId = undefined }

  private headersFor(userId?: number | string): Record<string, string> {
    const h: Record<string, string> = { 'X-Request-ID': this._reqId() }
    if (typeof userId !== 'undefined') h['X-User-Id'] = String(userId)
    if (this._projectId) h['X-Project-Id'] = this._projectId
    if (this._sessionId) h['X-Session-Id'] = this._sessionId
    if (this._conversationId) h['X-Conversation-Id'] = this._conversationId
    if (this._persona) h['X-Persona'] = this._persona
    if (this._role) h['X-Role'] = this._role
    if (this._priority) h['X-Priority'] = this._priority
    return h
  }

  // Basic API health (useful for quick checks)
  health(): Observable<{status: string}> {
    return this.http.get<{status: string}>(this.buildUrl(`/healthz`));
  }

  // System status overview
  getSystemStatus(): Observable<SystemStatus> {
    return this.http.get<SystemStatus>(this.buildUrl(`/api/v1/system/status`));
  }

  // Services health breakdown
  getServicesHealth(): Observable<ServiceHealthResponse> {
    return this.http.get<ServiceHealthResponse>(this.buildUrl(`/api/v1/system/health/services`));
  }

  // Workers orchestration
  getWorkersStatus(): Observable<WorkersStatusResponse> {
    return this.http.get<WorkersStatusResponse>(this.buildUrl(`/api/v1/workers/status`));
  }

  // Consolidated System Overview
  getSystemOverview(): Observable<SystemOverviewResponse> {
    return this.http.get<SystemOverviewResponse>(this.buildUrl(`/api/v1/system/overview`));
  }

  private _webrtcInitialized$ = new BehaviorSubject<{ status: string; error?: string } | null>(null)
  private _janus?: any
  private _pluginHandle?: any
  private _serverUrl?: string
  private _localStream$ = new BehaviorSubject<MediaStream | null>(null)
  private _remoteStream$ = new BehaviorSubject<MediaStream | null>(null)
  private _connectionState$ = new BehaviorSubject<string>('idle')
  private _webrtcError$ = new Subject<string>()

  webrtcInitialized$(): Observable<{ status: string; error?: string } | null> { return this._webrtcInitialized$.asObservable() }
  localStream$(): Observable<MediaStream | null> { return this._localStream$.asObservable() }
  remoteStream$(): Observable<MediaStream | null> { return this._remoteStream$.asObservable() }
  connectionState$(): Observable<string> { return this._connectionState$.asObservable() }
  webrtcErrors$(): Observable<string> { return this._webrtcError$.asObservable() }

  initJanus(opts: { serverUrl: string; debug?: boolean }): Observable<{ status: string; error?: string }> {
    this._serverUrl = opts.serverUrl
    const out$ = new BehaviorSubject<{ status: string; error?: string }>({ status: 'initializing' })
    try {
      if (typeof Janus === 'undefined') {
        const err = 'JanusJS indisponível'
        this._webrtcInitialized$.next({ status: 'unavailable', error: err })
        out$.next({ status: 'unavailable', error: err })
        return out$.asObservable()
      }
      Janus.init({ debug: !!opts.debug, callback: () => {
        out$.next({ status: 'initialized' })
        this._webrtcInitialized$.next({ status: 'initialized' })
        try {
          this._janus = new Janus({
            server: this._serverUrl,
            success: () => { this._connectionState$.next('session_ready') },
            error: (e: any) => { const msg = String(e); this._webrtcError$.next(msg); this._connectionState$.next('session_error'); },
            destroyed: () => { this._connectionState$.next('session_destroyed') }
          })
        } catch (e) {
          const msg = String(e)
          this._webrtcError$.next(msg)
          this._connectionState$.next('session_error')
        }
      }})
    } catch (e) {
      const msg = String(e)
      this._webrtcInitialized$.next({ status: 'failed', error: msg })
      out$.next({ status: 'failed', error: msg })
    }
    return out$.asObservable()
  }

  attachPlugin(plugin: 'videoroom' | 'videocall', opaqueId?: string): Observable<{ status: string; error?: string }> {
    const out$ = new BehaviorSubject<{ status: string; error?: string }>({ status: 'attaching' })
    if (!this._janus) { out$.next({ status: 'failed', error: 'JanusSession ausente' }); return out$.asObservable() }
    try {
      const pluginName = plugin === 'videocall' ? 'janus.plugin.videocall' : 'janus.plugin.videoroom'
      this._janus.attach({
        plugin: pluginName,
        opaqueId,
        success: (handle: any) => {
          this._pluginHandle = handle
          out$.next({ status: 'attached' })
          this._connectionState$.next('attached')
        },
        error: (cause: any) => {
          const msg = String(cause)
          this._webrtcError$.next(msg)
          out$.next({ status: 'failed', error: msg })
          this._connectionState$.next('attach_error')
        },
        webrtcState: (on: boolean) => {
          this._connectionState$.next(on ? 'webrtc_up' : 'webrtc_down')
        },
        onlocalstream: (stream: MediaStream) => {
          this._localStream$.next(stream)
        },
        onremotestream: (stream: MediaStream) => {
          this._remoteStream$.next(stream)
        }
      })
    } catch (e) {
      const msg = String(e)
      this._webrtcError$.next(msg)
      out$.next({ status: 'failed', error: msg })
    }
    return out$.asObservable()
  }

  createPeerConnection(iceServers?: RTCIceServer[]): RTCPeerConnection {
    const pc = new RTCPeerConnection({ iceServers })
    pc.oniceconnectionstatechange = () => { this._connectionState$.next(pc.iceConnectionState) }
    pc.ontrack = (ev) => {
      const [stream] = ev.streams
      if (stream) this._remoteStream$.next(stream)
    }
    return pc
  }

  startLocalMedia(constraints: MediaStreamConstraints = { audio: true, video: true }): Promise<MediaStream> {
    return navigator.mediaDevices.getUserMedia(constraints)
      .then((stream) => { this._localStream$.next(stream); return stream })
      .catch((e) => { const msg = String(e); this._webrtcError$.next(msg); throw e })
  }

  stopLocalMedia(): void {
    const s = this._localStream$.getValue()
    if (!s) return
    s.getTracks().forEach(t => t.stop())
    this._localStream$.next(null)
  }

  startAllWorkers(): Observable<any> {
    return this.http.post(this.buildUrl(`/api/v1/workers/start-all`), {});
  }

  stopAllWorkers(): Observable<any> {
    return this.http.post(this.buildUrl(`/api/v1/workers/stop-all`), {});
  }
  // LLM subsystem
  listLLMProviders(): Observable<LLMProvidersResponse> {
    return this.http.get<LLMProvidersResponse>(this.buildUrl(`/api/v1/llm/providers`))
  }

  getLLMHealth(): Observable<LLMSubsystemHealth> {
    return this.http.get<LLMSubsystemHealth>(this.buildUrl(`/api/v1/llm/health`))
  }

  getLLMCacheStatus(): Observable<LLMCacheStatusResponse> {
    return this.http.get<LLMCacheStatusResponse>(this.buildUrl(`/api/v1/llm/cache/status`))
  }

  getLLMCircuitBreakers(): Observable<CircuitBreakerStatus[]> {
    return this.http.get<CircuitBreakerStatus[]>(this.buildUrl(`/api/v1/llm/circuit-breakers`))
  }

  // Observability
  getObservabilitySystemHealth(): Observable<ObservabilitySystemHealth> {
    return this.http.get<ObservabilitySystemHealth>(this.buildUrl(`/api/v1/observability/health/system`))
  }

  getObservabilityMetricsSummary(): Observable<MetricsSummary> {
    return this.http.get<MetricsSummary>(this.buildUrl(`/api/v1/observability/metrics/summary`))
  }

  getQuarantinedMessages(queue?: string): Observable<QuarantinedMessagesResponse> {
    const params = queue ? `?queue=${encodeURIComponent(queue)}` : ''
    return this.http.get<QuarantinedMessagesResponse>(this.buildUrl(`/api/v1/observability/poison-pills/quarantined${params}`))
  }

  cleanupQuarantine(): Observable<any> {
    return this.http.post(this.buildUrl(`/api/v1/observability/poison-pills/cleanup`), {})
  }

  getPoisonPillStats(queue?: string): Observable<PoisonPillStats> {
    const params = queue ? `?queue=${encodeURIComponent(queue)}` : ''
    return this.http.get<PoisonPillStats>(this.buildUrl(`/api/v1/observability/poison-pills/stats${params}`))
  }

  // HITL / Observability: Graph quarantine & actions
  listGraphQuarantine(limit: number = 100, offset: number = 0, filters?: { type?: string; reason?: string; confidence_ge?: number }): Observable<GraphQuarantineListResponse> {
    const qs = new URLSearchParams()
    qs.set('limit', String(limit))
    qs.set('offset', String(offset))
    if (filters?.type) qs.set('type', filters.type)
    if (filters?.reason) qs.set('reason', filters.reason)
    if (typeof filters?.confidence_ge !== 'undefined') qs.set('confidence_ge', String(filters?.confidence_ge))
    return this.http.get<GraphQuarantineListResponse>(this.buildUrl(`/api/v1/observability/graph/quarantine?${qs.toString()}`))
  }

  promoteQuarantine(node_id: number): Observable<any> {
    return this.http.post(this.buildUrl(`/api/v1/observability/graph/quarantine/promote`), { node_id })
  }

  rejectQuarantine(node_id: number, reason: string): Observable<any> {
    return this.http.post(this.buildUrl(`/api/v1/observability/graph/quarantine/reject`), { node_id, reason })
  }

  registerSynonym(label: string, alias: string, canonical: string): Observable<any> {
    return this.http.post(this.buildUrl(`/api/v1/observability/graph/entities/synonym`), { label, alias, canonical })
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
    return this.http.get<AuditEventsResponse>(this.buildUrl(`/api/v1/observability/audit/events?${qs.toString()}`))
  }

  getReviewerMetrics(user_id: number, start_ts?: number, end_ts?: number): Observable<ReviewerMetricsResponse> {
    const qs = new URLSearchParams()
    qs.set('user_id', String(user_id))
    if (typeof start_ts !== 'undefined') qs.set('start_ts', String(start_ts))
    if (typeof end_ts !== 'undefined') qs.set('end_ts', String(end_ts))
    return this.http.get<ReviewerMetricsResponse>(this.buildUrl(`/api/v1/observability/hitl/metrics/reviewer?${qs.toString()}`))
  }

  getHitlReports(period: 'daily'|'weekly'|'monthly' = 'daily', start_ts?: number, end_ts?: number): Observable<PeriodReportResponse> {
    const qs = new URLSearchParams()
    qs.set('period', period)
    if (typeof start_ts !== 'undefined') qs.set('start_ts', String(start_ts))
    if (typeof end_ts !== 'undefined') qs.set('end_ts', String(end_ts))
    return this.http.get<PeriodReportResponse>(this.buildUrl(`/api/v1/observability/hitl/reports?${qs.toString()}`))
  }

  // Consents API
  listConsents(user_id: number): Observable<ConsentsListResponse> {
    return this.http.get<ConsentsListResponse>(this.buildUrl(`/api/v1/consents/?user_id=${encodeURIComponent(String(user_id))}`))
  }
  grantConsent(user_id: number, scope: string, granted: boolean = true, expires_at?: string): Observable<any> {
    const body: any = { user_id: String(user_id), scope, granted: granted ? 'True' : 'False' }
    if (expires_at) body.expires_at = expires_at
    return this.http.post(this.buildUrl(`/api/v1/consents/`), body)
  }
  revokeConsent(consent_id: number): Observable<any> {
    return this.http.post(this.buildUrl(`/api/v1/consents/${encodeURIComponent(String(consent_id))}/revoke`), {})
  }

  // Context
  getCurrentContext(): Observable<ContextInfo> {
    return this.http.get<ContextInfo>(this.buildUrl(`/api/v1/context/current`))
  }

  searchWeb(query: string, max_results: number = 5, search_depth: 'basic' | 'advanced' = 'basic'): Observable<WebSearchResult> {
    const params = new URLSearchParams({ query, max_results: String(max_results), search_depth })
    return this.http.get<WebSearchResult>(this.buildUrl(`/api/v1/context/web-search?${params.toString()}`))
  }

  getWebCacheStatus(): Observable<WebCacheStatus> {
    return this.http.get<WebCacheStatus>(this.buildUrl(`/api/v1/context/web-cache/status`))
  }

  invalidateWebCache(query?: string): Observable<any> {
    return this.http.post(this.buildUrl(`/api/v1/context/web-cache/invalidate`), { query })
  }

  // Chat API
  startChat(title?: string, persona?: string, user_id?: string, project_id?: string): Observable<ChatStartResponse> {
    const body: any = { title }
    if (persona) body.persona = persona
    if (user_id) body.user_id = user_id
    if (project_id) body.project_id = project_id
    return this.http.post<ChatStartResponse>(this.buildUrl(`/api/v1/chat/start`), body)
  }

  sendChatMessage(conversation_id: string, content: string, role: string = 'orchestrator', priority: string = 'fast_and_cheap', timeout_seconds?: number, user_id?: string, project_id?: string): Observable<ChatMessageResponse & { citations?: Citation[] }> {
    const body: any = { conversation_id, message: content, role, priority }
    if (typeof timeout_seconds !== 'undefined') body.timeout_seconds = timeout_seconds
    if (user_id) body.user_id = user_id
    if (project_id) body.project_id = project_id
    return this.http.post<ChatMessageResponse & { citations?: Citation[] }>(this.buildUrl(`/api/v1/chat/message`), body)
  }

  getChatHistory(conversation_id: string): Observable<ChatHistoryResponse> {
    return this.http.get<ChatHistoryResponse>(this.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}/history`))
  }

  listConversations(params: { user_id?: string; project_id?: string; limit?: number } = {}): Observable<ConversationsListResponse> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.project_id) qs.set('project_id', params.project_id)
    qs.set('limit', String(params.limit ?? 50))
    return this.http.get<ConversationsListResponse>(this.buildUrl(`/api/v1/chat/conversations?${qs.toString()}`))
  }

  renameConversation(conversation_id: string, new_title: string): Observable<{ status: string }> {
    return this.http.put<{ status: string }>(this.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}/rename`), { new_title })
  }

  deleteConversation(conversation_id: string): Observable<{ status: string }> {
    return this.http.delete<{ status: string }>(this.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}`))
  }

  // Users
  getUserRoles(user_id: number): Observable<UserRolesResponse> {
    return this.http.get<UserRolesResponse>(`/api/v1/users/${encodeURIComponent(String(user_id))}/roles`)
  }

  // Auth
  issueToken(user_id: number, expires_in: number = 3600): Observable<TokenResponse> {
    const headers = this.headersFor(user_id)
    return this.http.post<TokenResponse>(this.buildUrl(`/api/v1/auth/token`), { user_id, expires_in }, { headers })
  }

  // Productivity limits status
  getProductivityLimitsStatus(user_id: number): Observable<ProductivityLimitsStatusResponse> {
    const headers = this.headersFor(user_id)
    return this.http.get<ProductivityLimitsStatusResponse>(this.buildUrl(`/api/v1/productivity/limits/status?user_id=${encodeURIComponent(String(user_id))}`), { headers })
  }

  // Google OAuth
  googleOAuthStart(user_id: number, scope: 'calendar' | 'mail' | 'notes' = 'calendar'): Observable<GoogleOAuthStartResponse> {
    const headers = this.headersFor(user_id)
    const qs = new URLSearchParams({ user_id: String(user_id), scope })
    return this.http.get<GoogleOAuthStartResponse>(this.buildUrl(`/api/v1/productivity/oauth/google/start?${qs.toString()}`), { headers })
  }

  googleOAuthCallback(code: string, state: string): Observable<GoogleOAuthCallbackResponse> {
    return this.http.post<GoogleOAuthCallbackResponse>(this.buildUrl(`/api/v1/productivity/oauth/google/callback`), { code, state })
  }

  // Calendar and Mail operations (queued)
  calendarAddEvent(req: CalendarAddRequest): Observable<QueueAck> {
    const headers = this.headersFor(req.user_id)
    return this.http.post<QueueAck>(this.buildUrl(`/api/v1/productivity/calendar/events/add`), req, { headers })
  }

  mailSend(req: MailSendRequest): Observable<QueueAck> {
    const headers = this.headersFor(req.user_id)
    return this.http.post<QueueAck>(this.buildUrl(`/api/v1/productivity/mail/messages/send`), req, { headers })
  }

  // A/B Testing
  getExperimentWinner(experiment_id: number, metric_name: string = 'accuracy'): Observable<ExperimentWinnerResponse> {
    const qs = new URLSearchParams({ metric_name })
    return this.http.get<ExperimentWinnerResponse>(this.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/winner?${qs.toString()}`))
  }

  assignUserToExperiment(experiment_id: number, user_id: string): Observable<AssignmentResponse> {
    return this.http.post<AssignmentResponse>(this.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/assign`), { user_id })
  }

  submitExperimentFeedback(experiment_id: number, user_id: string, rating: number, notes?: string): Observable<FeedbackSubmitResponse> {
    return this.http.post<FeedbackSubmitResponse>(this.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/feedback`), { user_id, rating, notes })
  }

  getExperimentFeedbackStats(experiment_id: number): Observable<any> {
    return this.http.get<any>(this.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/feedback/stats`))
  }

  // Deployment
  stageDeployment(model_id: string, rollout_percent: number): Observable<DeploymentStageResponse> {
    return this.http.post<DeploymentStageResponse>(this.buildUrl(`/api/v1/deployment/stage`), { model_id, rollout_percent })
  }

  publishDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.http.post<DeploymentPublishResponse>(this.buildUrl(`/api/v1/deployment/publish?model_id=${encodeURIComponent(model_id)}`), {})
  }

  rollbackDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.http.post<DeploymentPublishResponse>(this.buildUrl(`/api/v1/deployment/rollback?model_id=${encodeURIComponent(model_id)}`), {})
  }

  precheckDeployment(model_id: string): Observable<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }> {
    return this.http.post<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }>(this.buildUrl(`/api/v1/deployment/precheck?model_id=${encodeURIComponent(model_id)}`), {})
  }

  // GPU resources
  getGPUUsage(user_id: string): Observable<GPUUsageResponse> {
    return this.http.get<GPUUsageResponse>(this.buildUrl(`/api/v1/resources/gpu/usage/${encodeURIComponent(user_id)}`))
  }

  setGPUBudget(user_id: string, budget: number): Observable<GPUBudgetResponse> {
    return this.http.post<GPUBudgetResponse>(this.buildUrl(`/api/v1/resources/gpu/budget`), { user_id, budget })
  }

  // LLM A/B experiment
  setLLMABExperiment(experiment_id: number): Observable<ABExperimentSetResponse> {
    return this.http.post<ABExperimentSetResponse>(this.buildUrl(`/api/v1/llm/ab/set-experiment`), { experiment_id })
  }

  // System/User status
  getUserStatus(user_id: string): Observable<UserStatusResponse> {
    const qs = new URLSearchParams({ user_id })
    return this.http.get<UserStatusResponse>(this.buildUrl(`/api/v1/system/status/user?${qs.toString()}`))
  }

  // Observability
  exportAuditCSV(params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number }): Observable<string> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', String(params.user_id))
    if (params.tool) qs.set('tool', String(params.tool))
    if (params.status) qs.set('status', String(params.status))
    if (params.start_ts != null) qs.set('start_ts', String(params.start_ts))
    if (params.end_ts != null) qs.set('end_ts', String(params.end_ts))
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.offset != null) qs.set('offset', String(params.offset))
    return this.http.get(this.buildUrl(`/api/v1/observability/audit/export?${qs.toString()}`), { responseType: 'text' })
  }

  exportAuditEvents(
    format: 'csv'|'json',
    params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number; fields?: string[] } = {}
  ): Observable<string> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', String(params.user_id))
    if (params.tool) qs.set('tool', String(params.tool))
    if (params.status) qs.set('status', String(params.status))
    if (params.start_ts != null) qs.set('start_ts', String(params.start_ts))
    if (params.end_ts != null) qs.set('end_ts', String(params.end_ts))
    qs.set('limit', String(params.limit ?? 1000))
    qs.set('offset', String(params.offset ?? 0))
    qs.set('format', format)
    if (params.fields && params.fields.length) qs.set('fields', params.fields.join(','))
    return this.http.get(this.buildUrl(`/api/v1/observability/audit/export?${qs.toString()}`), { responseType: 'text' })
  }

  // Documents
  uploadAttachmentWithProgress(conversation_id: string, file: File, user_id?: string): Observable<{ progress?: number; response?: UploadResponse }> {
    const form = new FormData()
    form.append('file', file)
    form.append('conversation_id', conversation_id)
    if (user_id) form.append('user_id', user_id)
    return this.http.post<UploadResponse>(this.buildUrl(`/api/v1/documents/upload`), form, { reportProgress: true, observe: 'events' }).pipe(
      (source: any) => new Observable<{ progress?: number; response?: UploadResponse }>((observer) => {
        source.subscribe({
          next: (event: any) => {
            const t = event?.type
            if (t === 1 && typeof event?.loaded === 'number' && typeof event?.total === 'number') {
              const pct = Math.round((event.loaded / Math.max(1, event.total)) * 100)
              observer.next({ progress: pct })
            } else if (t === 4) {
              observer.next({ response: event?.body as UploadResponse })
              observer.complete()
            }
          },
          error: (err: any) => observer.error(err),
          complete: () => observer.complete(),
        })
      })
    )
  }

  listAttachments(conversation_id: string, user_id?: string): Observable<DocListResponse> {
    const qs = new URLSearchParams()
    if (user_id) qs.set('user_id', user_id)
    qs.set('conversation_id', conversation_id)
    return this.http.get<DocListResponse>(this.buildUrl(`/api/v1/documents/list?${qs.toString()}`))
  }

  deleteAttachment(doc_id: string, user_id?: string): Observable<{ status: string }> {
    const headers = this.headersFor(user_id)
    return this.http.delete<{ status: string }>(this.buildUrl(`/api/v1/documents/${encodeURIComponent(doc_id)}`), { headers })
  }

  linkUrl(conversation_id: string, url: string, user_id?: string): Observable<UploadResponse> {
    const form = new FormData()
    form.append('url', url)
    form.append('conversation_id', conversation_id)
    if (user_id) form.append('user_id', user_id)
    return this.http.post<UploadResponse>(this.buildUrl(`/api/v1/documents/link-url`), form)
  }
}

export type WorkersStatusItem = WorkerStatusResponse;
