import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { API_BASE_URL } from './api.config'
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { JanusStatic, JanusSession, JanusPluginHandle } from '../core/types';
import { AppLoggerService } from '../core/services/app-logger.service';
declare const Janus: JanusStatic;

export interface SystemStatus {
  app_name: string;
  version: string;
  environment: string;
  status: string;
  timestamp?: string;
  uptime_seconds?: number;
  system?: Record<string, unknown>;
  process?: Record<string, unknown>;
  performance?: Record<string, unknown>;
  config?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ServiceHealthItem {
  key: string;
  name: string;
  status: string;
  metric_text?: string;
}

export interface ServiceHealthResponse {
  services: ServiceHealthItem[];
}

export interface WorkerStatusResponse {
  id: string;
  status: string;
  last_heartbeat: string | Date; // Backend sends datetime string, but frontend might parse it
  tasks_processed: number;
}

export interface OrchestratorWorkerTaskStatus {
  name: string;
  running: boolean;
  done: boolean;
  cancelled: boolean;
  exception?: string | null;
  state: string;
  reason?: string;
  detail?: string;
  composite?: boolean;
  children?: OrchestratorWorkerTaskStatus[];
}

export interface QueueInfoResponse {
  name: string;
  messages: number;
  consumers: number;
}

export interface SystemOverviewResponse {
  system_status: SystemStatus;
  services_status: ServiceHealthItem[];
  workers_status: WorkerStatusResponse[];
}

// Database Validation
export interface DbValidationCheck {
  table: string;
  name: string;
  kind: string;
  exists: boolean;
}

export interface DbValidationResponse {
  status: string;
  checks: DbValidationCheck[];
}

// Knowledge Health
export interface KnowledgeHealthResponse {
  status: string;
  neo4j_connected: boolean;
  qdrant_connected: boolean;
  circuit_breaker_open: boolean;
  total_nodes: number;
  total_relationships: number;
}

export interface KnowledgeHealthDetailedResponse {
  timestamp: string;
  overall_status: string;
  basic_health: KnowledgeHealthResponse;
  detailed_status: {
    offline: boolean;
    circuit_breaker_open: boolean;
    metrics: Record<string, unknown>;
  };
  monitoring: Record<string, unknown> | null;
  recommendations: string[];
}

// Meta-Agent
export interface MetaAgentRecommendation {
  id: string;
  category?: string;
  title: string;
  description?: string;
  rationale?: string;
  estimated_impact?: string;
  priority?: number;
  suggested_agent?: string | null;
  created_at?: string;
}

export interface MetaAgentExecutionResult {
  title?: string;
  status?: string;
  [key: string]: unknown;
}

export interface MetaAgentReport {
  cycle_id: string;
  timestamp: string;
  overall_status: string;
  health_score: number;
  issues_detected: Record<string, unknown>[];
  recommendations: MetaAgentRecommendation[];
  summary: string;
  metrics_snapshot: Record<string, unknown>;
  execution_results?: MetaAgentExecutionResult[];
}

export interface MetaAgentLatestReportResponse {
  message: string;
  report: MetaAgentReport | null;
}

export interface MetaAgentHeartbeatStatus {
  heartbeat_active: boolean;
  total_cycles_executed: number;
  last_analysis?: string | null;
}

// LLM providers
export interface LLMProviderMeta { priority?: number; enabled?: boolean; models?: string[]; type?: string }
export type LLMProvidersResponse = Record<string, LLMProviderMeta>;

// LLM health
export interface LLMSubsystemHealth {
  status: string;
  providers?: Record<string, { status: string; latency_ms?: number; error?: string | null }>;
}

export interface LLMCacheEntry { [key: string]: unknown }
export interface LLMCacheStatusResponse { total_cached: number; cache_entries: LLMCacheEntry[] }
export interface CircuitBreakerStatus { provider: string; state: string; failure_count: number; last_failure_time?: number | null }

export interface MetricsSummary {
  llm: { cached_llms: number; circuit_breakers: Record<string, { state: string; failure_count: number }> };
  multi_agent: { active_agents: number; workspace_tasks: number; workspace_artifacts: number };
  poison_pills: Record<string, unknown>;
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
export interface ConsentItem { scope: string; granted: boolean; expires_at?: string | null }
export interface ConsentsListResponse { user_id: number; consents: ConsentItem[] }
export interface PendingAction {
  source?: 'langgraph' | 'sql' | string;
  thread_id?: string;
  action_id?: number;
  status: string;
  message?: string | null;
  user_id?: string;
  tool_name?: string;
  args_json?: string;
  created_at?: string;
  risk_level?: 'low' | 'medium' | 'high' | string;
  risk_summary?: string;
  scope_summary?: string;
  scope_targets?: string[];
  simulation?: Record<string, unknown> | null;
}

// Poison pill stats
export interface PoisonPillStats {
  total: number;
  by_queue: Record<string, { count: number; last_quarantined_at?: string }>;
}

export interface ContextInfo { [key: string]: unknown }
export interface WebSearchResult { [key: string]: unknown }
export interface WebCacheStatus { [key: string]: unknown }

export interface ChatStartResponse {
  conversation_id: string
  created_at?: number
  updated_at?: number
}
export interface ChatStartRequest {
  persona?: string;
  user_id?: string;
  project_id?: string;
  title?: string;
}

export interface ChatMessageRequest {
  conversation_id: string;
  message: string;
  role?: string;
  priority?: string;
  timeout_seconds?: number;
  user_id?: string;
  project_id?: string;
  knowledge_space_id?: string;
}
export interface CitationStatus {
  mode: 'required' | 'optional' | string;
  status: 'present' | 'missing_required' | 'not_applicable' | 'retrieval_failed' | string;
  count: number;
  reason?: string | null;
}
export interface ChatRoutingState {
  requested_role?: string;
  selected_role?: string;
  route_applied?: boolean;
  intent?: string;
  risk_level?: string;
  confidence?: number;
  [key: string]: unknown;
}
export interface ChatRiskState {
  level?: 'low' | 'medium' | 'high' | string;
  source?: string;
  summary?: string;
  requires_confirmation?: boolean;
  [key: string]: unknown;
}
export interface ChatConfirmationState {
  required: boolean;
  status?: string;
  reason?: string | null;
  source?: string;
  pending_action_id?: number | null;
  approve_endpoint?: string | null;
  reject_endpoint?: string | null;
  [key: string]: unknown;
}
export interface ChatAgentState {
  state: 'thinking' | 'using_tool' | 'waiting_confirmation' | 'low_confidence' | 'streaming_response' | 'completed' | 'error' | string;
  confidence_band?: 'high' | 'medium' | 'low' | string;
  requires_confirmation?: boolean;
  reason?: string;
  [key: string]: unknown;
}
export interface ChatUnderstanding {
  intent: string;
  summary: string;
  confidence?: number;
  confidence_band?: 'high' | 'medium' | 'low' | string;
  low_confidence?: boolean;
  requires_confirmation?: boolean;
  confirmation_reason?: string | null;
  signals?: string[];
  routing?: ChatRoutingState;
  risk?: ChatRiskState;
  confirmation?: ChatConfirmationState;
  [key: string]: unknown;
}
export interface ChatMessage {
  message_id?: string;
  role: string;
  text: string;
  timestamp: number;
  knowledge_space_id?: string;
  mode_used?: string;
  base_used?: string;
  estimated_wait_seconds?: number;
  estimated_wait_range_seconds?: number[];
  processing_profile?: string;
  processing_notice?: string | null;
  source_scope?: Record<string, unknown> | null;
  gaps_or_conflicts?: string[];
  citations?: Citation[]
  citation_status?: CitationStatus;
  reasoning?: string;
  ui?: { type: string; data: any };
  understanding?: ChatUnderstanding;
  confirmation?: ChatConfirmationState;
  agent_state?: ChatAgentState;
  delivery_status?: string;
  failure_classification?: string;
  provider?: string;
  model?: string;
}

export interface Tool {
  name: string;
  description: string;
  args_schema?: Record<string, unknown>;
  category?: string;
  permission_level?: string;
  rate_limit_per_minute?: number;
  requires_confirmation?: boolean;
  tags?: string[];
  enabled?: boolean;
}

export interface ToolListResponse {
  tools: Tool[];
}

export interface ChatStudyJobRef {
  job_id: string;
  status: string;
  poll_url: string;
  conversation_id: string;
  message_id?: string;
  placeholder_message?: string;
}

export interface ChatStudyJobResponse {
  job_id: string;
  status: string;
  progress: number;
  conversation_id: string;
  message_id?: string;
  placeholder_message?: string;
  failure_classification?: string;
  final_response?: ChatMessageResponse;
  error?: string;
  updated_at?: number;
}

export interface ChatMessageResponse {
  response: string;
  provider: string;
  model: string;
  role: string;
  conversation_id: string;
  message_id?: string;
  knowledge_space_id?: string;
  mode_used?: string;
  base_used?: string;
  estimated_wait_seconds?: number;
  estimated_wait_range_seconds?: number[];
  processing_profile?: string;
  processing_notice?: string | null;
  source_scope?: Record<string, unknown> | null;
  gaps_or_conflicts?: string[];
  citations: Citation[];
  citation_status?: CitationStatus;
  ui?: { type: string; data: any };
  understanding?: ChatUnderstanding;
  confirmation?: ChatConfirmationState;
  agent_state?: ChatAgentState;
  delivery_status?: string;
  study_job?: ChatStudyJobRef;
  study_notice?: string;
  failure_classification?: string;
}
export interface ChatHistoryResponse { conversation_id: string; messages: ChatMessage[] }
export interface ChatListItem {
  conversation_id: string;
  title?: string;
  created_at?: number;
  updated_at?: number;
  last_message?: ChatMessage;
}

export interface ChatHistoryPaginatedResponse {
  conversation_id: string;
  persona?: string;
  messages: ChatMessage[];
  total_count: number;
  has_more: boolean;
  next_offset?: number;
  limit: number;
  offset: number;
}
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
export interface ExperimentArmStats {
  arm_id: number;
  name: string;
  model_spec: string;
  n: number;
  mean: number;
  var: number;
  values?: number[];
}
export interface ExperimentWinnerResponse { winner: ExperimentArmStats; arms: ExperimentArmStats[]; metric: string; p_value?: number | null }
export interface AssignmentResponse { experiment_id: number; user_id: string; arm_id: number }
export interface FeedbackSubmitResponse { id: number; status: string }
export interface DeploymentStageResponse { model_id: string; status: string; rollout_percent: number }
export interface DeploymentPublishResponse { model_id: string; status: string; rollout_percent: number }
export interface GPUBudgetResponse { user_id: string; budget: number }
export interface GPUUsageResponse { used: number; updated_at?: string | null }
export interface ABExperimentSetResponse { status: string; LLM_AB_EXPERIMENT_ID: number }
export interface UserStatusResponse { user_id: string; conversations: number; messages: number; approx_in_tokens: number; approx_out_tokens: number; vector_points: number }

// Documents / RAG
export interface UploadResponse { doc_id: string; chunks: number; status: string; consolidation?: Record<string, unknown> | null }
export interface DocListItem { doc_id: string; file_name?: string; chunks: number; conversation_id?: string; last_index_ts?: number }
export interface DocListResponse { items: DocListItem[] }
export interface Citation {
  id?: string;
  title?: string;
  url?: string;
  snippet?: string;
  score?: number;
  source_type?: string;
  doc_id?: string;
  file_path?: string;
  origin?: string;
  type?: string;
  line?: number | string;
  line_start?: number | string;
  line_end?: number | string;
}

export interface DocSearchResultItem {
  id: string;
  score: number;
  doc_id: string;
  file_name?: string;
  index?: number;
  timestamp?: number;
  [key: string]: unknown;
}

export interface DocSearchResponse {
  results: DocSearchResultItem[];
}

export interface KnowledgeSpace {
  knowledge_space_id: string;
  user_id: string;
  name: string;
  source_type: string;
  source_id?: string | null;
  edition_or_version?: string | null;
  language?: string | null;
  parent_collection_id?: string | null;
  description?: string | null;
  consolidation_status: string;
  consolidation_summary?: string | null;
  last_consolidated_at?: string | null;
}

export interface KnowledgeSpaceStatus extends KnowledgeSpace {
  documents_total: number;
  documents_indexed: number;
  documents_processing: number;
  documents_queued: number;
  documents_failed: number;
  chunks_total: number;
  chunks_indexed: number;
  progress: number;
}

export interface KnowledgeSpaceCreateRequest {
  name: string;
  user_id?: string;
  source_type?: string;
  source_id?: string;
  edition_or_version?: string;
  language?: string;
  parent_collection_id?: string;
  description?: string;
}

export interface KnowledgeSpaceListResponse {
  items: KnowledgeSpace[];
}

export interface KnowledgeSpaceAttachRequest {
  user_id?: string;
  source_type?: string;
  source_id?: string;
  edition_or_version?: string;
  language?: string;
  parent_collection_id?: string;
}

export interface KnowledgeSpaceConsolidationResponse {
  message: string;
  stats: {
    status: string;
    task_id?: string;
    status_url?: string;
    [key: string]: unknown;
  };
}

export interface KnowledgeSpaceQueryResponse {
  answer: string;
  mode_used: string;
  base_used: string;
  source_scope: Record<string, unknown>;
  citations: Citation[];
  confidence: number;
  gaps_or_conflicts: string[];
}

export interface GenerativeMemoryItem {
  id?: string;
  content: string;
  score?: number;
  type?: string;
  created_at?: string | number;
  updated_at?: string | number;
  metadata?: {
    importance?: number | string;
    user_id?: string;
    conversation_id?: string;
    session_id?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface UserPreferenceMemoryItem {
  id?: string;
  content: string;
  ts_ms?: number;
  preference_kind?: 'do' | 'dont' | string;
  instruction_text?: string;
  scope?: string;
  confidence?: number;
  user_id?: string;
  conversation_id?: string;
  session_id?: string;
  active?: boolean;
  origin?: string;
  dedupe_key?: string;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface RagSearchResponse {
  answer: string;
  citations: Citation[];
}

export interface RagUserChatResponse {
  answer: string;
  citations: Citation[];
}

export interface RagUserChatV2Result {
  id?: string;
  score?: number;
  role?: string;
  session_id?: string;
  timestamp?: number;
  [key: string]: unknown;
}

export interface RagUserChatV2Response {
  results: RagUserChatV2Result[];
}

export interface RagHybridResponse {
  answer: string;
  citations: Citation[];
}

export interface FeedbackQuickRequest {
  conversation_id: string;
  message_id: string;
  comment?: string;
  user_id?: string;
}

export interface FeedbackQuickResponse {
  id: string;
  rating: string;
  message: string;
}

// Goals
export interface Goal {
  id: string
  title: string
  description: string
  priority: number
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  success_criteria?: string
  deadline_ts?: number
  created_at: number
  updated_at: number
}

export interface GoalCreateRequest {
  title: string
  description: string
  priority?: number
  success_criteria?: string
  deadline_ts?: number
}

export interface WorkersStatusResponse {
  tracked: number;
  workers: OrchestratorWorkerTaskStatus[];
}

// Autonomy
export interface AutonomyStartRequest {
  interval_seconds?: number
  user_id?: string
  project_id?: string
  risk_profile?: 'conservative' | 'balanced' | 'aggressive'
  auto_confirm?: boolean
  allowlist?: string[]
  blocklist?: string[]
  max_actions_per_cycle?: number
  max_seconds_per_cycle?: number
  plan?: { tool: string; args: Record<string, unknown> }[]
}

export interface AutonomyConfig {
  risk_profile?: string;
  interval_seconds?: number;
  max_actions_per_cycle?: number;
  [key: string]: unknown;
}

export interface AutonomyStatusResponse {
  active: boolean
  cycle_count: number
  last_cycle_at?: number | null
  config: AutonomyConfig
}

export interface AutonomyPlanResponse {
  status: string
  active: boolean
  steps_count: number
  plan: { tool: string; args: Record<string, unknown> }[]
}

export interface AutonomyPolicyUpdateRequest {
  risk_profile?: string
  auto_confirm?: boolean
  allowlist?: string[]
  blocklist?: string[]
  max_actions_per_cycle?: number
  max_seconds_per_cycle?: number
}

export interface AdminBacklogSyncResponse {
  created: number
  deduped: number
  capped: number
  closed: number
  fallback_used_count: number
  findings_total: number
}

export interface AdminBacklogTask {
  id: string
  title: string
  description: string
  status: string
  priority: number
  source_kind?: string | null
  source_fingerprint?: string | null
  area?: string | null
  severity?: string | null
  auto_created?: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface AdminBacklogSprint {
  id: string
  name: string
  status: string
  start_ts?: number | null
  end_ts?: number | null
  tasks: AdminBacklogTask[]
}

export interface AdminBacklogSprintType {
  sprint_type: { id: string; name: string; slug: string }
  sprints: AdminBacklogSprint[]
}

export interface SelfStudyRunFile {
  id: number
  file_path: string
  change_type?: string | null
  sha_before?: string | null
  sha_after?: string | null
  summary_status: string
  error?: string | null
}

export interface SelfStudyRun {
  id: number
  trigger_type: string
  mode: 'incremental' | 'full' | string
  status: string
  files_total: number
  files_processed: number
  error?: string | null
  base_commit?: string | null
  target_commit?: string | null
  created_at?: string | null
  finished_at?: string | null
  files?: SelfStudyRunFile[]
}

export interface SelfStudyStatusResponse {
  last_studied_commit?: string | null
  last_success_at?: string | null
  running?: {
    id: number
    status: string
    mode: string
    created_at?: string | null
    files_total?: number
    files_processed?: number
    current_file_path?: string | null
    current_file_index?: number | null
  } | null
  recent_runs: SelfStudyRun[]
}

export interface AdminCodeQaResponse {
  answer: string
  citations: Citation[]
  self_memory: Array<{ file_path?: string; summary?: string; updated_at?: string | number }>
}

// Auto Analysis
export interface HealthInsight {
  issue: string
  severity: string
  suggestion: string
  estimated_impact: string
}

export interface AutoAnalysisResponse {
  timestamp: string
  overall_health: string
  insights: HealthInsight[]
  fun_fact: string
}

// Knowledge Graph
export interface KnowledgeStats {
  total_nodes: number
  total_relationships: number
  labels: Record<string, number>
}

export interface EntityRelationshipItem {
  related_entity: string
  related_type: string
  relationship: string
  distance: number
}

export interface EntityRelationshipsResponse {
  results: EntityRelationshipItem[]
}

// Reflexion
export interface ReflexionLesson {
  id: string
  content: string
  score?: number
  metadata?: Record<string, unknown>
}

export interface PostSprintSummaryResponse {
  lessons: ReflexionLesson[]
  meta_report?: Record<string, unknown>
}

export interface MemoryItem {
  content: string;
  ts_ms: number;
  composite_id?: string;
  metadata?: {
    type?: string;
    user_id?: string;
    conversation_id?: string;
    session_id?: string;
    role?: string;
    timestamp?: number;
    [key: string]: unknown;
  };
}

export interface TraceStep {
  stepId: string;
  timestamp: number;
  agent: string;
  type: string;
  content: any;
  metadata?: {
    task_id?: string;
    trace_id?: string;
    model?: string;
  };
}

export interface GraphNode {
  data: {
    id: string;
    label: string;
    type?: string;
    color?: string;
  };
}

export interface GraphEdge {
  data: {
    source: string;
    target: string;
    label: string;
  };
}

export interface ContextualGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

@Injectable({ providedIn: 'root' })
export class BackendApiService {
  constructor(private http: HttpClient, private logger: AppLoggerService) { }
  // ... existing methods ...

  getConversationTrace(conversationId: string): Observable<TraceStep[]> {
    return this.http.get<TraceStep[]>(this.buildUrl(`/api/v1/chat/${encodeURIComponent(conversationId)}/trace`));
  }

  getContextualGraph(query?: string, conversationId?: string, hops: number = 1): Observable<ContextualGraphResponse> {
    const qs = new URLSearchParams();
    if (query) qs.set('query', query);
    if (conversationId) qs.set('conversation_id', conversationId);
    qs.set('hops', String(hops));
    return this.http.get<ContextualGraphResponse>(this.buildUrl(`/api/v1/admin/graph/contextual?${qs.toString()}`));
  }

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

  private _traceparent(): string {
    const hex = (size: number) => {
      let out = ''
      for (let i = 0; i < size; i += 1) {
        out += Math.floor(Math.random() * 16).toString(16)
      }
      return out
    }
    return `00-${hex(32)}-${hex(16)}-01`
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
    const h: Record<string, string> = {
      'X-Request-ID': this._reqId(),
      traceparent: this._traceparent(),
    }
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
  health(): Observable<{ status: string }> {
    return this.http.get<{ status: string }>(this.buildUrl(`/healthz`));
  }

  // System status overview

  /**
    * Obtém o status geral do sistema, incluindo versão, ambiente e métricas de desempenho.
    * @returns Observable com SystemStatus contendo uptime e carga.
    */
  getSystemStatus(): Observable<SystemStatus> {
    return this.http.get<SystemStatus>(this.buildUrl(`/api/v1/system/status`), {
      headers: { 'ngsw-bypass': 'true' }
    });
  }

  // Services health breakdown
  getServicesHealth(): Observable<ServiceHealthResponse> {
    return this.http.get<ServiceHealthResponse>(this.buildUrl(`/api/v1/system/health/services`));
  }

  // Workers orchestration
  getWorkersStatus(): Observable<WorkersStatusResponse> {
    return this.http.get<WorkersStatusResponse>(this.buildUrl(`/api/v1/workers/status`));
  }

  getQueueInfo(queueName: string): Observable<QueueInfoResponse> {
    return this.http.get<QueueInfoResponse>(
      this.buildUrl(`/api/v1/tasks/queue/${encodeURIComponent(queueName)}`)
    );
  }

  // Consolidated System Overview
  getSystemOverview(): Observable<SystemOverviewResponse> {
    return this.http.get<SystemOverviewResponse>(this.buildUrl(`/api/v1/system/overview`), {
      headers: { 'ngsw-bypass': 'true' }
    });
  }

  // Meta-Agent
  getMetaAgentLatestReport(): Observable<MetaAgentLatestReportResponse> {
    return this.http.get<MetaAgentLatestReportResponse>(this.buildUrl(`/api/v1/meta-agent/report/latest`));
  }

  getMetaAgentHeartbeatStatus(): Observable<MetaAgentHeartbeatStatus> {
    return this.http.get<MetaAgentHeartbeatStatus>(this.buildUrl(`/api/v1/meta-agent/heartbeat/status`));
  }

  private _webrtcInitialized$ = new BehaviorSubject<{ status: string; error?: string } | null>(null)
  private _janus?: JanusSession
  private _pluginHandle?: JanusPluginHandle
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
      Janus.init({
        debug: !!opts.debug, callback: () => {
          out$.next({ status: 'initialized' })
          this._webrtcInitialized$.next({ status: 'initialized' })
          try {
            this._janus = new Janus({
              server: this._serverUrl || '',
              success: () => { this._connectionState$.next('session_ready') },
              error: (e: unknown) => { const msg = String(e); this._webrtcError$.next(msg); this._connectionState$.next('session_error'); },
              destroyed: () => { this._connectionState$.next('session_destroyed') }
            })
          } catch (e) {
            const msg = String(e)
            this._webrtcError$.next(msg)
            this._connectionState$.next('session_error')
          }
        }
      })
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
        success: (handle: JanusPluginHandle) => {
          this._pluginHandle = handle
          out$.next({ status: 'attached' })
          this._connectionState$.next('attached')
        },
        error: (cause: unknown) => {
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

  startAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.http.post<{ status: string; workers: string[] }>(this.buildUrl(`/api/v1/workers/start-all`), {});
  }

  stopAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.http.post<{ status: string; workers: string[] }>(this.buildUrl(`/api/v1/workers/stop-all`), {});
  }

  // Autonomy Loop
  /**
    * Inicia o loop de autonomia do agente.
    * @param req Configurações de inicialização (intervalo, perfil de risco).
    * @returns Status de confirmação e intervalo configurado.
    */
  startAutonomy(req: AutonomyStartRequest): Observable<{ status: string; interval_seconds: number }> {
    return this.http.post<{ status: string; interval_seconds: number }>(this.buildUrl(`/api/v1/autonomy/start`), req)
  }

  /**
    * Interrompe o loop de autonomia imediatamente.
    * @returns Confirmação de parada.
    */
  stopAutonomy(): Observable<{ status: string }> {
    return this.http.post<{ status: string }>(this.buildUrl(`/api/v1/autonomy/stop`), {})
  }

  getAutonomyStatus(): Observable<AutonomyStatusResponse> {
    return this.http.get<AutonomyStatusResponse>(this.buildUrl(`/api/v1/autonomy/status`))
  }

  getAutonomyPlan(): Observable<AutonomyPlanResponse> {
    return this.http.get<AutonomyPlanResponse>(this.buildUrl(`/api/v1/autonomy/plan`))
  }

  updateAutonomyPlan(plan: { tool: string; args: Record<string, unknown> }[]): Observable<{ status: string; steps_count: number }> {
    return this.http.put<{ status: string; steps_count: number }>(this.buildUrl('/api/v1/autonomy/plan'), { plan })
  }

  updateAutonomyPolicy(req: AutonomyPolicyUpdateRequest): Observable<{ status: string; policy: Record<string, unknown> }> {
    return this.http.put<{ status: string; policy: Record<string, unknown> }>(this.buildUrl(`/api/v1/autonomy/policy`), req)
  }


  runAutoAnalysis(): Observable<AutoAnalysisResponse> {
    return this.http.get<AutoAnalysisResponse>(this.buildUrl(`/api/v1/auto-analysis/health-check`))
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

  // Alias for convenience
  getMetricsSummary(): Observable<MetricsSummary> {
    return this.getObservabilityMetricsSummary()
  }

  getBudgetSummary(): Observable<any> {
    return this.http.get(this.buildUrl(`/api/v1/llm/budget/summary`))
  }

  getQuarantinedMessages(queue?: string): Observable<QuarantinedMessagesResponse> {
    const params = queue ? `?queue=${encodeURIComponent(queue)}` : ''
    return this.http.get<QuarantinedMessagesResponse>(this.buildUrl(`/api/v1/observability/poison-pills/quarantined${params}`))
  }

  cleanupQuarantine(): Observable<{ status: string; count: number }> {
    return this.http.post<{ status: string; count: number }>(this.buildUrl(`/api/v1/observability/poison-pills/cleanup`), {})
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

  promoteQuarantine(node_id: number): Observable<{ status: string; node_id: number }> {
    return this.http.post<{ status: string; node_id: number }>(this.buildUrl(`/api/v1/observability/graph/quarantine/promote`), { node_id })
  }

  rejectQuarantine(node_id: number, reason: string): Observable<{ status: string; node_id: number }> {
    return this.http.post<{ status: string; node_id: number }>(this.buildUrl(`/api/v1/observability/graph/quarantine/reject`), { node_id, reason })
  }

  registerSynonym(label: string, alias: string, canonical: string): Observable<{ status: string; synonym_id: number }> {
    return this.http.post<{ status: string; synonym_id: number }>(this.buildUrl(`/api/v1/observability/graph/entities/synonym`), { label, alias, canonical })
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

  // Pending actions (human approvals)
  listPendingActions(params: {
    include_graph?: boolean;
    include_sql?: boolean;
    user_id?: string;
    pending_status?: string;
    limit?: number;
  } = {}): Observable<PendingAction[]> {
    const qs = new URLSearchParams()
    if (typeof params.include_graph !== 'undefined') qs.set('include_graph', String(params.include_graph))
    if (typeof params.include_sql !== 'undefined') qs.set('include_sql', String(params.include_sql))
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.pending_status) qs.set('pending_status', params.pending_status)
    if (typeof params.limit !== 'undefined') qs.set('limit', String(params.limit))
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    return this.http.get<PendingAction[]>(this.buildUrl(`/api/v1/pending_actions/${suffix}`))
  }

  approvePendingAction(action: PendingAction): Observable<PendingAction> {
    if (typeof action?.action_id === 'number') {
      return this.http.post<PendingAction>(
        this.buildUrl(`/api/v1/pending_actions/action/${encodeURIComponent(String(action.action_id))}/approve`),
        {}
      )
    }
    if (!action?.thread_id) {
      throw new Error('Invalid pending action: missing action_id/thread_id')
    }
    return this.http.post<PendingAction>(
      this.buildUrl(`/api/v1/pending_actions/${encodeURIComponent(action.thread_id)}/approve`),
      {}
    )
  }

  rejectPendingAction(action: PendingAction): Observable<PendingAction> {
    if (typeof action?.action_id === 'number') {
      return this.http.post<PendingAction>(
        this.buildUrl(`/api/v1/pending_actions/action/${encodeURIComponent(String(action.action_id))}/reject`),
        {}
      )
    }
    if (!action?.thread_id) {
      throw new Error('Invalid pending action: missing action_id/thread_id')
    }
    return this.http.post<PendingAction>(
      this.buildUrl(`/api/v1/pending_actions/${encodeURIComponent(action.thread_id)}/reject`),
      {}
    )
  }

  getReviewerMetrics(user_id: number, start_ts?: number, end_ts?: number): Observable<ReviewerMetricsResponse> {
    const qs = new URLSearchParams()
    qs.set('user_id', String(user_id))
    if (typeof start_ts !== 'undefined') qs.set('start_ts', String(start_ts))
    if (typeof end_ts !== 'undefined') qs.set('end_ts', String(end_ts))
    return this.http.get<ReviewerMetricsResponse>(this.buildUrl(`/api/v1/observability/hitl/metrics/reviewer?${qs.toString()}`))
  }

  getHitlReports(period: 'daily' | 'weekly' | 'monthly' = 'daily', start_ts?: number, end_ts?: number): Observable<PeriodReportResponse> {
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
  grantConsent(user_id: number, scope: string, granted: boolean = true, expires_at?: string): Observable<{ status: string; scope: string }> {
    const body: Record<string, unknown> = { user_id: String(user_id), scope, granted: granted ? 'True' : 'False' }
    if (expires_at) body['expires_at'] = expires_at
    return this.http.post<{ status: string; scope: string }>(this.buildUrl(`/api/v1/consents/`), body)
  }
  revokeConsent(consent_id: number): Observable<{ status: string; consent_id: string }> {
    return this.http.post<{ status: string; consent_id: string }>(this.buildUrl(`/api/v1/consents/${encodeURIComponent(String(consent_id))}/revoke`), {})
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

  invalidateWebCache(query?: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.buildUrl(`/api/v1/context/web-cache/invalidate`), { query })
  }

  // Chat API
  startChat(title?: string, persona?: string, user_id?: string, project_id?: string): Observable<ChatStartResponse> {
    const body: ChatStartRequest = { title }
    if (persona) body.persona = persona
    if (user_id) body.user_id = user_id
    if (project_id) body.project_id = project_id
    return this.http.post<ChatStartResponse>(this.buildUrl(`/api/v1/chat/start`), body)
  }

  sendChatMessage(conversation_id: string, content: string, role: string = 'orchestrator', priority: string = 'fast_and_cheap', timeout_seconds?: number, user_id?: string, project_id?: string, knowledge_space_id?: string): Observable<ChatMessageResponse & { citations?: Citation[] }> {
    // Validate required fields
    // Validate required fields
    if (!conversation_id || conversation_id.trim().length < 1) {
      this.logger.error('[BackendApiService] Invalid conversation_id provided to sendChatMessage', { conversation_id });
      throw new Error(`Invalid conversation_id: ${conversation_id}`);
    }

    this.logger.debug('[BackendApiService] Sending chat message', {
      conversation_id_raw: conversation_id,
      conversation_id_trimmed: conversation_id.trim(),
      role,
      priority,
    });

    const body: ChatMessageRequest = {
      conversation_id: conversation_id.trim(),
      message: content,
      role: role || 'orchestrator',
      priority: priority || 'fast_and_cheap'
    };

    if (typeof timeout_seconds !== 'undefined') body.timeout_seconds = timeout_seconds
    if (user_id) body.user_id = user_id
    if (project_id) body.project_id = project_id
    if (knowledge_space_id) body.knowledge_space_id = knowledge_space_id

    this.logger.debug('[BackendApiService] Sending chat message payload', body);

    return this.http.post<ChatMessageResponse>(this.buildUrl(`/api/v1/chat/message`), body).pipe(
      tap({
        next: (res) => this.logger.debug('[BackendApiService] Chat message success', res),
        error: (err) => this.logger.error('[BackendApiService] Chat message failed', err)
      })
    )
  }

  getChatStudyJob(jobId: string): Observable<ChatStudyJobResponse> {
    return this.http.get<ChatStudyJobResponse>(this.buildUrl(`/api/v1/chat/study-jobs/${encodeURIComponent(jobId)}`))
  }

  getChatHistory(conversation_id: string): Observable<ChatHistoryResponse> {
    return this.http.get<ChatHistoryResponse>(this.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}/history`)).pipe(
      map((resp) => {
        const msgs = Array.isArray(resp?.messages) ? resp.messages : []
        const mapped = msgs.map((m) => ({
          message_id: typeof m?.message_id === 'string' ? String(m.message_id) : undefined,
          role: String(m?.role || ''),
          text: this.normalizeChatText(m?.text),
          timestamp: m?.timestamp != null ? Number(m.timestamp) : 0,
          citations: m?.citations,
          citation_status: m?.citation_status,
          reasoning: m?.reasoning,
          ui: m?.ui,
          understanding: m?.understanding,
          confirmation: m?.confirmation,
          agent_state: m?.agent_state,
          delivery_status: typeof m?.delivery_status === 'string' ? String(m.delivery_status) : undefined,
          failure_classification: typeof m?.failure_classification === 'string' ? String(m.failure_classification) : undefined,
          provider: typeof m?.provider === 'string' ? String(m.provider) : undefined,
          model: typeof m?.model === 'string' ? String(m.model) : undefined,
        }))
        return { conversation_id: String(resp?.conversation_id || conversation_id), messages: mapped } as ChatHistoryResponse
      })
    )
  }

  getChatHistoryPaginated(conversation_id: string, params: {
    limit?: number;
    offset?: number;
    before_ts?: number;
    after_ts?: number;
  } = {}): Observable<{
    conversation_id: string;
    messages: ChatMessage[];
    total_count: number;
    has_more: boolean;
    next_offset?: number;
    limit: number;
    offset: number;
  }> {
    const qs = new URLSearchParams()
    if (params.limit) qs.set('limit', String(params.limit))
    if (params.offset) qs.set('offset', String(params.offset))
    if (params.before_ts) qs.set('before_ts', String(params.before_ts))
    if (params.after_ts) qs.set('after_ts', String(params.after_ts))

    const url = this.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}/history${qs.toString() ? '?' + qs.toString() : ''}`)

    return this.http.get<ChatHistoryPaginatedResponse>(url).pipe(
      map((resp) => {
        const msgs = Array.isArray(resp?.messages) ? resp.messages : []
        const mapped = msgs.map((m) => ({
          message_id: typeof m?.message_id === 'string' ? String(m.message_id) : undefined,
          role: String(m?.role || ''),
          text: this.normalizeChatText(m?.text),
          timestamp: m?.timestamp != null ? Number(m.timestamp) : 0,
          citations: m?.citations,
          citation_status: m?.citation_status,
          reasoning: m?.reasoning,
          ui: m?.ui,
          understanding: m?.understanding,
          confirmation: m?.confirmation,
          agent_state: m?.agent_state,
          delivery_status: typeof m?.delivery_status === 'string' ? String(m.delivery_status) : undefined,
          failure_classification: typeof m?.failure_classification === 'string' ? String(m.failure_classification) : undefined,
          provider: typeof m?.provider === 'string' ? String(m.provider) : undefined,
          model: typeof m?.model === 'string' ? String(m.model) : undefined,
        }))

        return {
          conversation_id: String(resp?.conversation_id || conversation_id),
          messages: mapped,
          total_count: Number(resp?.total_count || 0),
          has_more: Boolean(resp?.has_more || false),
          next_offset: resp?.next_offset != null ? Number(resp.next_offset) : undefined,
          limit: Number(resp?.limit || params.limit || 50),
          offset: Number(resp?.offset || params.offset || 0)
        }
      })
    )
  }

  checkChatHealth(): Observable<{ status: string, repository_accessible: boolean, total_conversations: number }> {
    return this.http.get<{ status: string, repository_accessible: boolean, total_conversations: number }>(this.buildUrl('/api/v1/chat/health'))
  }

  listConversations(params: { user_id?: string; project_id?: string; limit?: number } = {}): Observable<ConversationsListResponse> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.project_id) qs.set('project_id', params.project_id)
    qs.set('limit', String(params.limit ?? 50))

    return this.http.get<ChatListItem[] | { conversations: ChatListItem[] }>(this.buildUrl(`/api/v1/chat/conversations?${qs.toString()}`)).pipe(
      map((resp) => {
        // Backend now returns array directly, not {conversations: [...]}
        const items = Array.isArray(resp) ? resp : (resp as { conversations: ChatListItem[] }).conversations || []

        const mapped = items.map((it) => {
          const lm = it?.last_message
          const last_message: ChatMessage | undefined = lm && typeof lm === 'object' ? {
            role: String(lm?.role || ''),
            text: this.normalizeChatText(lm?.text),
            timestamp: lm?.timestamp != null ? Number(lm.timestamp) : 0,
            citations: lm?.citations,
            citation_status: lm?.citation_status,
            reasoning: lm?.reasoning,
            ui: lm?.ui,
            understanding: lm?.understanding,
            confirmation: lm?.confirmation,
            agent_state: lm?.agent_state,
          } : undefined
          return {
            conversation_id: String(it?.conversation_id || ''),
            title: it?.title,
            created_at: it?.created_at,
            updated_at: it?.updated_at,
            last_message,
            message_count: undefined, // Not in backend response
            tags: undefined, // Not in backend response
          } as ConversationMeta
        })

        return { conversations: mapped } as ConversationsListResponse
      })
    )
  }

  renameConversation(conversation_id: string, new_title: string): Observable<{ status: string }> {
    return this.http.put<{ status: string }>(this.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}/rename`), { new_title })
  }

  deleteConversation(conversation_id: string): Observable<{ status: string }> {
    return this.http.delete<{ status: string }>(this.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}`))
  }

  private normalizeChatText(value: unknown): string {
    if (value === null || value === undefined) return ''
    if (typeof value === 'string') return value
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
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
    return this.http.get<ProductivityLimitsStatusResponse>(
      this.buildUrl(`/api/v1/productivity/limits/status?user_id=${encodeURIComponent(String(user_id))}`),
      { headers }
    )
  }

  getProductivityLimitsStatusSelf(): Observable<ProductivityLimitsStatusResponse> {
    return this.http.get<ProductivityLimitsStatusResponse>(
      this.buildUrl(`/api/v1/productivity/limits/status`)
    )
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

  getExperimentFeedbackStats(experiment_id: number): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(this.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/feedback/stats`))
  }

  // Deployment
  /**
    * Carrega um modelo para o ambiente de Staging.
    * @param model_id ID do modelo (ex: 'gpt-4-turbo-custom-v2').
    * @param rollout_percent Percentual inicial de tráfego (0-100).
    */
  stageDeployment(model_id: string, rollout_percent: number): Observable<DeploymentStageResponse> {
    return this.http.post<DeploymentStageResponse>(this.buildUrl(`/api/v1/deployment/stage`), { model_id, rollout_percent })
  }

  /**
    * Promove o modelo de Staging para Produção (100% tráfego).
    * @param model_id ID do modelo a ser promovido.
    */
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
    format: 'csv' | 'json',
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

  // Documents - consolidated below


  linkUrl(conversation_id: string, url: string, user_id?: string): Observable<UploadResponse> {
    const form = new FormData()
    form.append('url', url)
    form.append('conversation_id', conversation_id)
    if (user_id) form.append('user_id', user_id)
    return this.http.post<UploadResponse>(this.buildUrl(`/api/v1/documents/link-url`), form)
  }

  // Goals CRUD
  listGoals(status?: string): Observable<Goal[]> {
    const qs = new URLSearchParams()
    if (status) qs.set('status', status)
    return this.http.get<Goal[]>(this.buildUrl(`/api/v1/autonomy/goals${qs.toString() ? '?' + qs.toString() : ''}`))
  }

  getGoal(goal_id: string): Observable<Goal> {
    return this.http.get<Goal>(this.buildUrl(`/api/v1/autonomy/goals/${encodeURIComponent(goal_id)}`))
  }

  createGoal(req: GoalCreateRequest): Observable<Goal> {
    return this.http.post<Goal>(this.buildUrl(`/api/v1/autonomy/goals`), req)
  }

  updateGoalStatus(goal_id: string, status: 'pending' | 'in_progress' | 'completed' | 'failed'): Observable<Goal> {
    return this.http.patch<Goal>(this.buildUrl(`/api/v1/autonomy/goals/${encodeURIComponent(goal_id)}/status`), { status })
  }

  deleteGoal(goal_id: string): Observable<{ status: string; goal_id: string }> {
    return this.http.delete<{ status: string; goal_id: string }>(this.buildUrl(`/api/v1/autonomy/goals/${encodeURIComponent(goal_id)}`))
  }

  syncAutonomyAdminBacklog(): Observable<AdminBacklogSyncResponse> {
    return this.http.post<AdminBacklogSyncResponse>(this.buildUrl(`/api/v1/autonomy/admin/backlog/sync`), {})
  }

  getAutonomyAdminBoard(params: { status?: string; limit?: number } = {}): Observable<{ items: AdminBacklogSprintType[] }> {
    const qs = new URLSearchParams()
    if (params.status) qs.set('status', String(params.status))
    qs.set('limit', String(params.limit ?? 200))
    return this.http.get<{ items: AdminBacklogSprintType[] }>(this.buildUrl(`/api/v1/autonomy/admin/board?${qs.toString()}`))
  }

  runAutonomyAdminSelfStudy(req: { mode: 'incremental' | 'full'; reason?: string }): Observable<{ status: string; run_id: number }> {
    return this.http.post<{ status: string; run_id: number }>(this.buildUrl(`/api/v1/autonomy/admin/self-study/run`), req)
  }

  getAutonomyAdminSelfStudyStatus(): Observable<SelfStudyStatusResponse> {
    return this.http.get<SelfStudyStatusResponse>(this.buildUrl(`/api/v1/autonomy/admin/self-study/status`))
  }

  listAutonomyAdminSelfStudyRuns(limit: number = 20): Observable<{ items: SelfStudyRun[] }> {
    const qs = new URLSearchParams()
    qs.set('limit', String(limit))
    return this.http.get<{ items: SelfStudyRun[] }>(this.buildUrl(`/api/v1/autonomy/admin/self-study/runs?${qs.toString()}`))
  }

  askAutonomyAdminCodeQa(req: { question: string; limit?: number; citation_limit?: number }): Observable<AdminCodeQaResponse> {
    return this.http.post<AdminCodeQaResponse>(this.buildUrl(`/api/v1/autonomy/admin/code-qa`), req)
  }



  // Tools API
  getTools(category?: string, permissionLevel?: string, tags?: string): Observable<ToolListResponse> {
    const qs = new URLSearchParams()
    if (category) qs.set('category', category)
    if (permissionLevel) qs.set('permission_level', permissionLevel)
    if (tags) qs.set('tags', tags)
    return this.http.get<ToolListResponse>(this.buildUrl(`/api/v1/tools/${qs.toString() ? '?' + qs.toString() : ''}`))
  }

  getToolDetails(toolName: string): Observable<Tool> {
    return this.http.get<Tool>(this.buildUrl(`/api/v1/tools/${encodeURIComponent(toolName)}`))
  }

  getToolStats(): Observable<ToolStats> {
    return this.http.get<ToolStats>(this.buildUrl(`/api/v1/tools/stats/usage`))
  }

  getToolCategories(): Observable<{ categories: string[] }> {
    return this.http.get<{ categories: string[] }>(this.buildUrl(`/api/v1/tools/categories/list`))
  }

  getToolPermissions(): Observable<{ permission_levels: string[] }> {
    return this.http.get<{ permission_levels: string[] }>(this.buildUrl(`/api/v1/tools/permissions/list`))
  }

  // Memory API
  getMemoryTimeline(params: {
    start_date?: string
    end_date?: string
    query?: string
    limit?: number
    min_score?: number
    user_id?: string
    conversation_id?: string
  } = {}): Observable<MemoryItem[]> {
    const qs = new URLSearchParams()
    if (params.start_date) qs.set('start_date', params.start_date)
    if (params.end_date) qs.set('end_date', params.end_date)
    if (params.query) qs.set('query', params.query)
    if (params.limit) qs.set('limit', String(params.limit))
    if (params.min_score !== undefined) qs.set('min_score', String(params.min_score))
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.conversation_id) qs.set('conversation_id', params.conversation_id)
    const headers = params.user_id ? this.headersFor(params.user_id) : undefined
    return this.http.get<MemoryItem[]>(
      this.buildUrl(`/api/v1/memory/timeline${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }

  getGenerativeMemories(
    query: string,
    limit: number = 10,
    filters: { type?: string; userId?: string; conversationId?: string } = {}
  ): Observable<GenerativeMemoryItem[]> {
    const qs = new URLSearchParams()
    qs.set('query', query)
    qs.set('limit', String(limit))
    if (filters.type) qs.set('type', String(filters.type))
    if (filters.userId) qs.set('user_id', String(filters.userId))
    if (filters.conversationId) qs.set('conversation_id', String(filters.conversationId))
    return this.http.get<GenerativeMemoryItem[]>(this.buildUrl(`/api/v1/memory/generative?${qs.toString()}`))
  }

  addGenerativeMemory(
    content: string,
    opts: { importance?: number; type?: string; userId?: string; conversationId?: string; sessionId?: string } = {}
  ): Observable<GenerativeMemoryItem> {
    const qs = new URLSearchParams()
    qs.set('content', content)
    if (typeof opts.importance === 'number') qs.set('importance', String(opts.importance))
    if (opts.type) qs.set('type', String(opts.type))
    if (opts.userId) qs.set('user_id', String(opts.userId))
    if (opts.conversationId) qs.set('conversation_id', String(opts.conversationId))
    if (opts.sessionId) qs.set('session_id', String(opts.sessionId))
    return this.http.post<GenerativeMemoryItem>(this.buildUrl(`/api/v1/memory/generative?${qs.toString()}`), {})
  }

  getUserPreferences(params: {
    userId?: string
    conversationId?: string
    query?: string
    limit?: number
    activeOnly?: boolean
  } = {}): Observable<UserPreferenceMemoryItem[]> {
    const qs = new URLSearchParams()
    if (params.userId) qs.set('user_id', String(params.userId))
    if (params.conversationId) qs.set('conversation_id', String(params.conversationId))
    if (params.query) qs.set('query', String(params.query))
    if (typeof params.limit === 'number') qs.set('limit', String(params.limit))
    if (typeof params.activeOnly === 'boolean') qs.set('active_only', String(params.activeOnly))
    const headers = params.userId ? this.headersFor(params.userId) : undefined
    return this.http.get<UserPreferenceMemoryItem[]>(
      this.buildUrl(`/api/v1/memory/preferences${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }

  // Documents API
  listDocuments(conversationId?: string, userId?: string): Observable<DocListResponse> {
    const qs = new URLSearchParams();
    if (conversationId) qs.set('conversation_id', conversationId);
    if (userId) qs.set('user_id', userId);
    const headers = this.headersFor(userId);
    return this.http.get<DocListResponse>(this.buildUrl(`/api/v1/documents/list${qs.toString() ? '?' + qs.toString() : ''}`), { headers });
  }

  uploadDocument(file: File, conversationId?: string, userId?: string): Observable<{ progress?: number; response?: UploadResponse }> {
    const form = new FormData();
    form.append('file', file);
    if (conversationId) form.append('conversation_id', conversationId);
    if (userId) form.append('user_id', userId);

    const headers = this.headersFor(userId);
    this.logger.debug('[BackendApiService] uploadDocument params', { userId, userHeader: headers['X-User-Id'] });
    return this.http.post<UploadResponse>(this.buildUrl(`/api/v1/documents/upload`), form, { headers, reportProgress: true, observe: 'events' }).pipe(
      map((event: HttpEvent<UploadResponse>) => {
        if (event.type === HttpEventType.UploadProgress) {
          const pct = Math.round((event.loaded / Math.max(1, event.total || 1)) * 100)
          return { progress: pct }
        } else if (event.type === HttpEventType.Response) {
          return { response: event.body || undefined }
        }
        return {}
      })
    )
  }

  searchDocuments(query: string, minScore?: number, docId?: string, userId?: string): Observable<DocSearchResponse> {
    const qs = new URLSearchParams()
    qs.set('query', query)
    if (minScore !== undefined) qs.set('min_score', String(minScore))
    if (docId) qs.set('doc_id', docId)
    if (userId) qs.set('user_id', String(userId))
    const headers = userId ? this.headersFor(userId) : undefined
    return this.http.get<DocSearchResponse>(
      this.buildUrl(`/api/v1/documents/search?${qs.toString()}`),
      headers ? { headers } : undefined
    )
  }

  deleteDocument(docId: string, userId?: string): Observable<{ status: string; doc_id: string }> {
    const qs = new URLSearchParams()
    if (userId) qs.set('user_id', String(userId))
    const headers = userId ? this.headersFor(userId) : undefined
    return this.http.delete<{ status: string; doc_id: string }>(
      this.buildUrl(`/api/v1/documents/${encodeURIComponent(docId)}${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }

  createKnowledgeSpace(payload: KnowledgeSpaceCreateRequest): Observable<KnowledgeSpace> {
    const headers = payload.user_id ? this.headersFor(payload.user_id) : undefined
    return this.http.post<KnowledgeSpace>(
      this.buildUrl('/api/v1/knowledge/spaces'),
      payload,
      headers ? { headers } : undefined
    )
  }

  listKnowledgeSpaces(userId?: string, limit: number = 100): Observable<KnowledgeSpaceListResponse> {
    const qs = new URLSearchParams()
    if (userId) qs.set('user_id', String(userId))
    qs.set('limit', String(limit))
    const headers = userId ? this.headersFor(userId) : undefined
    return this.http.get<KnowledgeSpaceListResponse>(
      this.buildUrl(`/api/v1/knowledge/spaces?${qs.toString()}`),
      headers ? { headers } : undefined
    )
  }

  getKnowledgeSpaceStatus(knowledgeSpaceId: string, userId?: string): Observable<KnowledgeSpaceStatus> {
    const qs = new URLSearchParams()
    if (userId) qs.set('user_id', String(userId))
    const headers = userId ? this.headersFor(userId) : undefined
    return this.http.get<KnowledgeSpaceStatus>(
      this.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }

  attachDocumentToKnowledgeSpace(
    knowledgeSpaceId: string,
    docId: string,
    payload: KnowledgeSpaceAttachRequest = {},
  ): Observable<{ status: string; document: Record<string, unknown> }> {
    const headers = payload.user_id ? this.headersFor(payload.user_id) : undefined
    return this.http.post<{ status: string; document: Record<string, unknown> }>(
      this.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/documents/${encodeURIComponent(docId)}/attach`),
      payload,
      headers ? { headers } : undefined
    )
  }

  consolidateKnowledgeSpace(
    knowledgeSpaceId: string,
    payload: { user_id?: string; limit_docs?: number } = {},
  ): Observable<KnowledgeSpaceConsolidationResponse> {
    const headers = payload.user_id ? this.headersFor(payload.user_id) : undefined
    return this.http.post<KnowledgeSpaceConsolidationResponse>(
      this.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/consolidate`),
      payload,
      headers ? { headers } : undefined
    )
  }

  queryKnowledgeSpace(
    knowledgeSpaceId: string,
    payload: { user_id?: string; question: string; mode?: string; limit?: number },
  ): Observable<KnowledgeSpaceQueryResponse> {
    const headers = payload.user_id ? this.headersFor(payload.user_id) : undefined
    return this.http.post<KnowledgeSpaceQueryResponse>(
      this.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/query`),
      payload,
      headers ? { headers } : undefined
    )
  }

  // RAG API
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
    return this.http.get<RagSearchResponse>(this.buildUrl(`/api/v1/rag/search?${qs.toString()}`))
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
    return this.http.get<RagUserChatResponse>(this.buildUrl(`/api/v1/rag/user-chat?${qs.toString()}`))
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
    const headers = params.user_id ? this.headersFor(params.user_id) : undefined
    return this.http.get<RagUserChatV2Response>(
      this.buildUrl(`/api/v1/rag/user_chat?${qs.toString()}`),
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
    const headers = params.user_id ? this.headersFor(params.user_id) : undefined
    return this.http.get<RagHybridResponse>(
      this.buildUrl(`/api/v1/rag/hybrid_search?${qs.toString()}`),
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
    const headers = this.headersFor(params.user_id)
    return this.http.get<RagSearchResponse>(this.buildUrl(`/api/v1/rag/productivity?${qs.toString()}`), { headers })
  }

  thumbsUpFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    const qs = new URLSearchParams()
    if (req.user_id) qs.set('user_id', String(req.user_id))
    return this.http.post<FeedbackQuickResponse>(
      this.buildUrl(`/api/v1/feedback/thumbs-up${qs.toString() ? '?' + qs.toString() : ''}`),
      {
        conversation_id: req.conversation_id,
        message_id: req.message_id,
        comment: req.comment,
      }
    )
  }

  thumbsDownFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    const qs = new URLSearchParams()
    if (req.user_id) qs.set('user_id', String(req.user_id))
    return this.http.post<FeedbackQuickResponse>(
      this.buildUrl(`/api/v1/feedback/thumbs-down${qs.toString() ? '?' + qs.toString() : ''}`),
      {
        conversation_id: req.conversation_id,
        message_id: req.message_id,
        comment: req.comment,
      }
    )
  }

  getKnowledgeStats(): Observable<KnowledgeStats> {
    return this.http.get<KnowledgeStats>(this.buildUrl(`/api/v1/knowledge/stats`))
  }

  getEntityRelationships(entityName: string): Observable<EntityRelationshipsResponse> {
    const qs = new URLSearchParams({ max_depth: '1', limit: '20' })
    return this.http.get<EntityRelationshipsResponse>(this.buildUrl(`/api/v1/knowledge/entity/${encodeURIComponent(entityName)}/relationships?${qs.toString()}`))
  }

  getReflexionSummary(limit: number = 10): Observable<PostSprintSummaryResponse> {
    const qs = new URLSearchParams({ limit: String(limit) })
    return this.http.get<PostSprintSummaryResponse>(this.buildUrl(`/api/v1/reflexion/summary/post_sprint?${qs.toString()}`))
  }

  // System - Database Validation
  getSystemDbValidate(): Observable<DbValidationResponse> {
    return this.http.get<DbValidationResponse>(this.buildUrl(`/api/v1/system/db/validate`))
  }

  // Knowledge - Health Endpoints
  getKnowledgeHealth(): Observable<KnowledgeHealthResponse> {
    return this.http.get<KnowledgeHealthResponse>(this.buildUrl(`/api/v1/knowledge/health`))
  }

  getKnowledgeHealthDetailed(): Observable<KnowledgeHealthDetailedResponse> {
    return this.http.get<KnowledgeHealthDetailedResponse>(this.buildUrl(`/api/v1/knowledge/health/detailed`))
  }

  resetKnowledgeCircuitBreaker(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(this.buildUrl(`/api/v1/knowledge/health/reset-circuit-breaker`), {})
  }
}

export type WorkersStatusItem = WorkerStatusResponse;

export interface ToolStats {
  total_tools_registered?: number;
  total_calls?: number;
  successful_calls?: number;
  success_rate?: number;
  tool_usage?: Record<string, { total: number; success: number; avg_duration: number }>;
}
