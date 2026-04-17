import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiContextService } from './api-context.service';
import { SystemApiService } from './domain/system-api-service';
import { ChatApiService } from './domain/chat-api-service';
import { KnowledgeApiService } from './domain/knowledge-api-service';
import { DocumentsApiService } from './domain/documents-api-service';
import { AutonomyApiService } from './domain/autonomy-api-service';
import { ObservabilityApiService } from './domain/observability-api-service';
import { ToolsApiService } from './domain/tools-api-service';
import { WebRTCApiService } from './domain/web-rtcapi-service';
import { LlmApiService } from './domain/llm-api-service';
import { MemoryApiService } from './domain/memory-api-service';
import { ProductivityApiService } from './domain/productivity-api-service';
import { UsersApiService } from './domain/users-api-service';
import { ContextApiService } from './domain/context-api-service';
import { ExperimentApiService } from './domain/experiment-api-service';
import { GraphApiService } from './domain/graph-api-service';
import { FeedbackApiService } from './domain/feedback-api-service';

import { MailSendRequest, Citation, MetricsSummary, Tool, KnowledgeSpaceConsolidationResponse, KnowledgeHealthDetailedResponse, AdminBacklogSprintType, ReviewerMetricsResponse, CircuitBreakerStatus, ChatMessageResponse, AdminBacklogSyncResponse, UserRolesResponse, UploadResponse, ChatStudyJobResponse, KnowledgeSpaceListResponse, FeedbackQuickRequest, AutonomyPlanResponse, ServiceHealthResponse, MetaAgentLatestReportResponse, KnowledgeHealthResponse, AssignmentResponse, TraceStep, DbValidationResponse, RagSearchResponse, RagUserChatV2Response, SelfStudyStatusResponse, KnowledgeSpace, MemoryItem, ChatMessage, RagUserChatResponse, PendingAction, AutonomyStartRequest, FeedbackSubmitResponse, WebCacheStatus, AutonomyStatusResponse, LLMCacheStatusResponse, DeploymentStageResponse, DocListResponse, KnowledgeSpaceCreateRequest, SelfStudyRun, GoogleOAuthCallbackResponse, GraphQuarantineListResponse, GPUUsageResponse, ChatStartResponse, AutoAnalysisResponse, GoogleOAuthStartResponse, ConsentsListResponse, FeedbackQuickResponse, AuditEventsResponse, DeploymentPublishResponse, ContextualGraphResponse, ObservabilitySystemHealth, PostSprintSummaryResponse, TokenResponse, AdminCodeQaResponse, PeriodReportResponse, WebSearchResult, ToolStats, GenerativeMemoryItem, QueueAck, KnowledgeStats, ContextInfo, KnowledgeSpaceAttachRequest, UserPreferenceMemoryItem, WorkersStatusResponse, KnowledgeSpaceStatus, ChatHistoryResponse, DocSearchResponse, GoalCreateRequest, AutonomyPolicyUpdateRequest, RagHybridResponse, QuarantinedMessagesResponse, UserStatusResponse, ProductivityLimitsStatusResponse, SystemStatus, ConversationsListResponse, MetaAgentHeartbeatStatus, ABExperimentSetResponse, QueueInfoResponse, Goal, ToolListResponse, PoisonPillStats, KnowledgeSpaceQueryResponse, GPUBudgetResponse, LLMProvidersResponse, SystemOverviewResponse, EntityRelationshipsResponse, ExperimentWinnerResponse, CalendarAddRequest, LLMSubsystemHealth } from '../models';
export * from '../models';

@Injectable({ providedIn: 'root' })
export class BackendApiService {
  constructor(
    private apiContext: ApiContextService,
    private systemApiService: SystemApiService,
    private chatApiService: ChatApiService,
    private knowledgeApiService: KnowledgeApiService,
    private documentsApiService: DocumentsApiService,
    private autonomyApiService: AutonomyApiService,
    private observabilityApiService: ObservabilityApiService,
    private toolsApiService: ToolsApiService,
    private webRTCApiService: WebRTCApiService,
    private llmApiService: LlmApiService,
    private memoryApiService: MemoryApiService,
    private productivityApiService: ProductivityApiService,
    private usersApiService: UsersApiService,
    private contextApiService: ContextApiService,
    private experimentApiService: ExperimentApiService,
    private graphApiService: GraphApiService,
    private feedbackApiService: FeedbackApiService
  ) {}

  buildUrl(...args: any[]): any { return (this.apiContext as any).buildUrl(...args); }
  headersFor(...args: any[]): any { return (this.apiContext as any).headersFor(...args); }
  setProjectId(...args: any[]): void { (this.apiContext as any).setProjectId(...args); }
  setSessionId(...args: any[]): void { (this.apiContext as any).setSessionId(...args); }
  setConversationId(...args: any[]): void { (this.apiContext as any).setConversationId(...args); }
  setPersona(...args: any[]): void { (this.apiContext as any).setPersona(...args); }
  setRole(...args: any[]): void { (this.apiContext as any).setRole(...args); }
  setPriority(...args: any[]): void { (this.apiContext as any).setPriority(...args); }
  clearContext(...args: any[]): void { (this.apiContext as any).clearContext(...args); }
  getConversationTrace(conversationId: string): Observable<TraceStep[]> {
    return this.chatApiService.getConversationTrace(conversationId);
  }

  getContextualGraph(query?: string, conversationId?: string, hops: number = 1): Observable<ContextualGraphResponse> {
    return this.graphApiService.getContextualGraph(query, conversationId, hops);
  }

  health(): Observable<{ status: string }> {
    return this.systemApiService.health();
  }

  getSystemStatus(): Observable<SystemStatus> {
    return this.systemApiService.getSystemStatus();
  }

  getServicesHealth(): Observable<ServiceHealthResponse> {
    return this.systemApiService.getServicesHealth();
  }

  getWorkersStatus(): Observable<WorkersStatusResponse> {
    return this.systemApiService.getWorkersStatus();
  }

  getQueueInfo(queueName: string): Observable<QueueInfoResponse> {
    return this.systemApiService.getQueueInfo(queueName);
  }

  getSystemOverview(): Observable<SystemOverviewResponse> {
    return this.systemApiService.getSystemOverview();
  }

  getMetaAgentLatestReport(): Observable<MetaAgentLatestReportResponse> {
    return this.autonomyApiService.getMetaAgentLatestReport();
  }

  getMetaAgentHeartbeatStatus(): Observable<MetaAgentHeartbeatStatus> {
    return this.autonomyApiService.getMetaAgentHeartbeatStatus();
  }

  webrtcInitialized$(): Observable<{ status: string; error?: string } | null> {
    return this.webRTCApiService.webrtcInitialized$();
  }

  localStream$(): Observable<MediaStream | null> {
    return this.webRTCApiService.localStream$();
  }

  remoteStream$(): Observable<MediaStream | null> {
    return this.webRTCApiService.remoteStream$();
  }

  connectionState$(): Observable<string> {
    return this.webRTCApiService.connectionState$();
  }

  webrtcErrors$(): Observable<string> {
    return this.webRTCApiService.webrtcErrors$();
  }

  initJanus(opts: { serverUrl: string; debug?: boolean }): Observable<{ status: string; error?: string }> {
    return this.webRTCApiService.initJanus(opts);
  }

  attachPlugin(plugin: 'videoroom' | 'videocall', opaqueId?: string): Observable<{ status: string; error?: string }> {
    return this.webRTCApiService.attachPlugin(plugin, opaqueId);
  }

  createPeerConnection(iceServers?: RTCIceServer[]): RTCPeerConnection {
    return this.webRTCApiService.createPeerConnection(iceServers);
  }

  startLocalMedia(constraints: MediaStreamConstraints = { audio: true, video: true }): Promise<MediaStream> {
    return this.webRTCApiService.startLocalMedia(constraints);
  }

  stopLocalMedia(): void {
    return this.webRTCApiService.stopLocalMedia();
  }

  startAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.systemApiService.startAllWorkers();
  }

  stopAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.systemApiService.stopAllWorkers();
  }

  startAutonomy(req: AutonomyStartRequest): Observable<{ status: string; interval_seconds: number }> {
    return this.autonomyApiService.startAutonomy(req);
  }

  stopAutonomy(): Observable<{ status: string }> {
    return this.autonomyApiService.stopAutonomy();
  }

  getAutonomyStatus(): Observable<AutonomyStatusResponse> {
    return this.autonomyApiService.getAutonomyStatus();
  }

  getAutonomyPlan(): Observable<AutonomyPlanResponse> {
    return this.autonomyApiService.getAutonomyPlan();
  }

  updateAutonomyPlan(plan: { tool: string; args: Record<string, unknown> }[]): Observable<{ status: string; steps_count: number }> {
    return this.autonomyApiService.updateAutonomyPlan(plan);
  }

  updateAutonomyPolicy(req: AutonomyPolicyUpdateRequest): Observable<{ status: string; policy: Record<string, unknown> }> {
    return this.autonomyApiService.updateAutonomyPolicy(req);
  }

  runAutoAnalysis(): Observable<AutoAnalysisResponse> {
    return this.systemApiService.runAutoAnalysis();
  }

  listLLMProviders(): Observable<LLMProvidersResponse> {
    return this.llmApiService.listLLMProviders();
  }

  getLLMHealth(): Observable<LLMSubsystemHealth> {
    return this.llmApiService.getLLMHealth();
  }

  getLLMCacheStatus(): Observable<LLMCacheStatusResponse> {
    return this.llmApiService.getLLMCacheStatus();
  }

  getLLMCircuitBreakers(): Observable<CircuitBreakerStatus[]> {
    return this.llmApiService.getLLMCircuitBreakers();
  }

  getObservabilitySystemHealth(): Observable<ObservabilitySystemHealth> {
    return this.observabilityApiService.getObservabilitySystemHealth();
  }

  getObservabilityMetricsSummary(): Observable<MetricsSummary> {
    return this.observabilityApiService.getObservabilityMetricsSummary();
  }

  getMetricsSummary(): Observable<MetricsSummary> {
    return this.observabilityApiService.getMetricsSummary();
  }

  getBudgetSummary(): Observable<any> {
    return this.llmApiService.getBudgetSummary();
  }

  getQuarantinedMessages(queue?: string): Observable<QuarantinedMessagesResponse> {
    return this.observabilityApiService.getQuarantinedMessages(queue);
  }

  cleanupQuarantine(): Observable<{ status: string; count: number }> {
    return this.observabilityApiService.cleanupQuarantine();
  }

  getPoisonPillStats(queue?: string): Observable<PoisonPillStats> {
    return this.observabilityApiService.getPoisonPillStats(queue);
  }

  listGraphQuarantine(limit: number = 100, offset: number = 0, filters?: { type?: string; reason?: string; confidence_ge?: number }): Observable<GraphQuarantineListResponse> {
    return this.observabilityApiService.listGraphQuarantine(limit, offset, filters);
  }

  promoteQuarantine(node_id: number): Observable<{ status: string; node_id: number }> {
    return this.observabilityApiService.promoteQuarantine(node_id);
  }

  rejectQuarantine(node_id: number, reason: string): Observable<{ status: string; node_id: number }> {
    return this.observabilityApiService.rejectQuarantine(node_id, reason);
  }

  registerSynonym(label: string, alias: string, canonical: string): Observable<{ status: string; synonym_id: number }> {
    return this.observabilityApiService.registerSynonym(label, alias, canonical);
  }

  listAuditEvents(params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number } = {}): Observable<AuditEventsResponse> {
    return this.observabilityApiService.listAuditEvents(params);
  }

  listPendingActions(params: {
    include_graph?: boolean;
    include_sql?: boolean;
    user_id?: string;
    pending_status?: string;
    limit?: number;
  } = {}): Observable<PendingAction[]> {
    return this.observabilityApiService.listPendingActions(params);
  }

  approvePendingAction(action: PendingAction): Observable<PendingAction> {
    return this.observabilityApiService.approvePendingAction(action);
  }

  rejectPendingAction(action: PendingAction): Observable<PendingAction> {
    return this.observabilityApiService.rejectPendingAction(action);
  }

  getReviewerMetrics(user_id: number, start_ts?: number, end_ts?: number): Observable<ReviewerMetricsResponse> {
    return this.observabilityApiService.getReviewerMetrics(user_id, start_ts, end_ts);
  }

  getHitlReports(period: 'daily' | 'weekly' | 'monthly' = 'daily', start_ts?: number, end_ts?: number): Observable<PeriodReportResponse> {
    return this.observabilityApiService.getHitlReports(period, start_ts, end_ts);
  }

  listConsents(user_id: number): Observable<ConsentsListResponse> {
    return this.observabilityApiService.listConsents(user_id);
  }

  grantConsent(user_id: number, scope: string, granted: boolean = true, expires_at?: string): Observable<{ status: string; scope: string }> {
    return this.observabilityApiService.grantConsent(user_id, scope, granted, expires_at);
  }

  revokeConsent(consent_id: number): Observable<{ status: string; consent_id: string }> {
    return this.observabilityApiService.revokeConsent(consent_id);
  }

  getCurrentContext(): Observable<ContextInfo> {
    return this.contextApiService.getCurrentContext();
  }

  searchWeb(query: string, max_results: number = 5, search_depth: 'basic' | 'advanced' = 'basic'): Observable<WebSearchResult> {
    return this.contextApiService.searchWeb(query, max_results, search_depth);
  }

  getWebCacheStatus(): Observable<WebCacheStatus> {
    return this.contextApiService.getWebCacheStatus();
  }

  invalidateWebCache(query?: string): Observable<Record<string, unknown>> {
    return this.contextApiService.invalidateWebCache(query);
  }

  startChat(title?: string, persona?: string, user_id?: string, project_id?: string): Observable<ChatStartResponse> {
    return this.chatApiService.startChat(title, persona, user_id, project_id);
  }

  sendChatMessage(conversation_id: string, content: string, role: string = 'orchestrator', priority: string = 'fast_and_cheap', timeout_seconds?: number, user_id?: string, project_id?: string, knowledge_space_id?: string): Observable<ChatMessageResponse & { citations?: Citation[] }> {
    return this.chatApiService.sendChatMessage(conversation_id, content, role, priority, timeout_seconds, user_id, project_id, knowledge_space_id);
  }

  getChatStudyJob(jobId: string): Observable<ChatStudyJobResponse> {
    return this.chatApiService.getChatStudyJob(jobId);
  }

  getChatHistory(conversation_id: string): Observable<ChatHistoryResponse> {
    return this.chatApiService.getChatHistory(conversation_id);
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
    return this.chatApiService.getChatHistoryPaginated(conversation_id, params);
  }

  checkChatHealth(): Observable<{ status: string, repository_accessible: boolean, total_conversations: number }> {
    return this.chatApiService.checkChatHealth();
  }

  listConversations(params: { user_id?: string; project_id?: string; limit?: number } = {}): Observable<ConversationsListResponse> {
    return this.chatApiService.listConversations(params);
  }

  renameConversation(conversation_id: string, new_title: string): Observable<{ status: string }> {
    return this.chatApiService.renameConversation(conversation_id, new_title);
  }

  deleteConversation(conversation_id: string): Observable<{ status: string }> {
    return this.chatApiService.deleteConversation(conversation_id);
  }

  normalizeChatText(value: unknown): string {
    return this.chatApiService.normalizeChatText(value);
  }

  getUserRoles(user_id: number): Observable<UserRolesResponse> {
    return this.usersApiService.getUserRoles(user_id);
  }

  issueToken(user_id: number, expires_in: number = 3600): Observable<TokenResponse> {
    return this.usersApiService.issueToken(user_id, expires_in);
  }

  getProductivityLimitsStatus(user_id: number): Observable<ProductivityLimitsStatusResponse> {
    return this.productivityApiService.getProductivityLimitsStatus(user_id);
  }

  getProductivityLimitsStatusSelf(): Observable<ProductivityLimitsStatusResponse> {
    return this.productivityApiService.getProductivityLimitsStatusSelf();
  }

  googleOAuthStart(user_id: number, scope: 'calendar' | 'mail' | 'notes' = 'calendar'): Observable<GoogleOAuthStartResponse> {
    return this.productivityApiService.googleOAuthStart(user_id, scope);
  }

  googleOAuthCallback(code: string, state: string): Observable<GoogleOAuthCallbackResponse> {
    return this.productivityApiService.googleOAuthCallback(code, state);
  }

  calendarAddEvent(req: CalendarAddRequest): Observable<QueueAck> {
    return this.productivityApiService.calendarAddEvent(req);
  }

  mailSend(req: MailSendRequest): Observable<QueueAck> {
    return this.productivityApiService.mailSend(req);
  }

  getExperimentWinner(experiment_id: number, metric_name: string = 'accuracy'): Observable<ExperimentWinnerResponse> {
    return this.experimentApiService.getExperimentWinner(experiment_id, metric_name);
  }

  assignUserToExperiment(experiment_id: number, user_id: string): Observable<AssignmentResponse> {
    return this.experimentApiService.assignUserToExperiment(experiment_id, user_id);
  }

  submitExperimentFeedback(experiment_id: number, user_id: string, rating: number, notes?: string): Observable<FeedbackSubmitResponse> {
    return this.experimentApiService.submitExperimentFeedback(experiment_id, user_id, rating, notes);
  }

  getExperimentFeedbackStats(experiment_id: number): Observable<Record<string, unknown>> {
    return this.experimentApiService.getExperimentFeedbackStats(experiment_id);
  }

  stageDeployment(model_id: string, rollout_percent: number): Observable<DeploymentStageResponse> {
    return this.llmApiService.stageDeployment(model_id, rollout_percent);
  }

  publishDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.llmApiService.publishDeployment(model_id);
  }

  rollbackDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.llmApiService.rollbackDeployment(model_id);
  }

  precheckDeployment(model_id: string): Observable<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }> {
    return this.llmApiService.precheckDeployment(model_id);
  }

  getGPUUsage(user_id: string): Observable<GPUUsageResponse> {
    return this.llmApiService.getGPUUsage(user_id);
  }

  setGPUBudget(user_id: string, budget: number): Observable<GPUBudgetResponse> {
    return this.llmApiService.setGPUBudget(user_id, budget);
  }

  setLLMABExperiment(experiment_id: number): Observable<ABExperimentSetResponse> {
    return this.llmApiService.setLLMABExperiment(experiment_id);
  }

  getUserStatus(user_id: string): Observable<UserStatusResponse> {
    return this.usersApiService.getUserStatus(user_id);
  }

  exportAuditCSV(params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number }): Observable<string> {
    return this.observabilityApiService.exportAuditCSV(params);
  }

  exportAuditEvents(format: 'csv' | 'json', params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number; fields?: string[] } = {}): Observable<string> {
    return this.observabilityApiService.exportAuditEvents(format, params);
  }

  linkUrl(conversation_id: string, url: string, user_id?: string): Observable<UploadResponse> {
    return this.documentsApiService.linkUrl(conversation_id, url, user_id);
  }

  listGoals(status?: string): Observable<Goal[]> {
    return this.autonomyApiService.listGoals(status);
  }

  getGoal(goal_id: string): Observable<Goal> {
    return this.autonomyApiService.getGoal(goal_id);
  }

  createGoal(req: GoalCreateRequest): Observable<Goal> {
    return this.autonomyApiService.createGoal(req);
  }

  updateGoalStatus(goal_id: string, status: 'pending' | 'in_progress' | 'completed' | 'failed'): Observable<Goal> {
    return this.autonomyApiService.updateGoalStatus(goal_id, status);
  }

  deleteGoal(goal_id: string): Observable<{ status: string; goal_id: string }> {
    return this.autonomyApiService.deleteGoal(goal_id);
  }

  syncAutonomyAdminBacklog(): Observable<AdminBacklogSyncResponse> {
    return this.autonomyApiService.syncAutonomyAdminBacklog();
  }

  getAutonomyAdminBoard(params: { status?: string; limit?: number } = {}): Observable<{ items: AdminBacklogSprintType[] }> {
    return this.autonomyApiService.getAutonomyAdminBoard(params);
  }

  runAutonomyAdminSelfStudy(req: { mode: 'incremental' | 'full'; reason?: string }): Observable<{ status: string; run_id: number }> {
    return this.autonomyApiService.runAutonomyAdminSelfStudy(req);
  }

  getAutonomyAdminSelfStudyStatus(): Observable<SelfStudyStatusResponse> {
    return this.autonomyApiService.getAutonomyAdminSelfStudyStatus();
  }

  listAutonomyAdminSelfStudyRuns(limit: number = 20): Observable<{ items: SelfStudyRun[] }> {
    return this.autonomyApiService.listAutonomyAdminSelfStudyRuns(limit);
  }

  askAutonomyAdminCodeQa(req: { question: string; limit?: number; citation_limit?: number }): Observable<AdminCodeQaResponse> {
    return this.autonomyApiService.askAutonomyAdminCodeQa(req);
  }

  getTools(category?: string, permissionLevel?: string, tags?: string): Observable<ToolListResponse> {
    return this.toolsApiService.getTools(category, permissionLevel, tags);
  }

  getToolDetails(toolName: string): Observable<Tool> {
    return this.toolsApiService.getToolDetails(toolName);
  }

  getToolStats(): Observable<ToolStats> {
    return this.toolsApiService.getToolStats();
  }

  getToolCategories(): Observable<{ categories: string[] }> {
    return this.toolsApiService.getToolCategories();
  }

  getToolPermissions(): Observable<{ permission_levels: string[] }> {
    return this.toolsApiService.getToolPermissions();
  }

  getMemoryTimeline(params: {
    start_date?: string
    end_date?: string
    query?: string
    limit?: number
    min_score?: number
    user_id?: string
    conversation_id?: string
  } = {}): Observable<MemoryItem[]> {
    return this.memoryApiService.getMemoryTimeline(params);
  }

  getGenerativeMemories(query: string, limit: number = 10, filters: { type?: string; userId?: string; conversationId?: string } = {}): Observable<GenerativeMemoryItem[]> {
    return this.memoryApiService.getGenerativeMemories(query, limit, filters);
  }

  addGenerativeMemory(content: string, opts: { importance?: number; type?: string; userId?: string; conversationId?: string; sessionId?: string } = {}): Observable<GenerativeMemoryItem> {
    return this.memoryApiService.addGenerativeMemory(content, opts);
  }

  getUserPreferences(params: {
    userId?: string
    conversationId?: string
    query?: string
    limit?: number
    activeOnly?: boolean
  } = {}): Observable<UserPreferenceMemoryItem[]> {
    return this.memoryApiService.getUserPreferences(params);
  }

  listDocuments(conversationId?: string, userId?: string): Observable<DocListResponse> {
    return this.documentsApiService.listDocuments(conversationId, userId);
  }

  uploadDocument(file: File, conversationId?: string, userId?: string): Observable<{ progress?: number; response?: UploadResponse }> {
    return this.documentsApiService.uploadDocument(file, conversationId, userId);
  }

  searchDocuments(query: string, minScore?: number, docId?: string, userId?: string): Observable<DocSearchResponse> {
    return this.documentsApiService.searchDocuments(query, minScore, docId, userId);
  }

  deleteDocument(docId: string, userId?: string): Observable<{ status: string; doc_id: string }> {
    return this.documentsApiService.deleteDocument(docId, userId);
  }

  createKnowledgeSpace(payload: KnowledgeSpaceCreateRequest): Observable<KnowledgeSpace> {
    return this.knowledgeApiService.createKnowledgeSpace(payload);
  }

  listKnowledgeSpaces(userId?: string, limit: number = 100): Observable<KnowledgeSpaceListResponse> {
    return this.knowledgeApiService.listKnowledgeSpaces(userId, limit);
  }

  getKnowledgeSpaceStatus(knowledgeSpaceId: string, userId?: string): Observable<KnowledgeSpaceStatus> {
    return this.knowledgeApiService.getKnowledgeSpaceStatus(knowledgeSpaceId, userId);
  }

  attachDocumentToKnowledgeSpace(knowledgeSpaceId: string, docId: string, payload: KnowledgeSpaceAttachRequest = {}): Observable<{ status: string; document: Record<string, unknown> }> {
    return this.knowledgeApiService.attachDocumentToKnowledgeSpace(knowledgeSpaceId, docId, payload);
  }

  consolidateKnowledgeSpace(knowledgeSpaceId: string, payload: { user_id?: string; limit_docs?: number } = {}): Observable<KnowledgeSpaceConsolidationResponse> {
    return this.knowledgeApiService.consolidateKnowledgeSpace(knowledgeSpaceId, payload);
  }

  queryKnowledgeSpace(knowledgeSpaceId: string, payload: { user_id?: string; question: string; mode?: string; limit?: number }): Observable<KnowledgeSpaceQueryResponse> {
    return this.knowledgeApiService.queryKnowledgeSpace(knowledgeSpaceId, payload);
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
    return this.knowledgeApiService.ragSearch(params);
  }

  ragUserChat(params: {
    query: string
    user_id: string
    session_id?: string
    role?: string
    limit?: number
    min_score?: number
  }): Observable<RagUserChatResponse> {
    return this.knowledgeApiService.ragUserChat(params);
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
    return this.knowledgeApiService.ragUserChatV2(params);
  }

  ragHybridSearch(params: {
    query: string
    user_id?: string
    limit?: number
    min_score?: number
  }): Observable<RagHybridResponse> {
    return this.knowledgeApiService.ragHybridSearch(params);
  }

  ragProductivitySearch(params: {
    query: string
    user_id: string
    limit?: number
    min_score?: number
  }): Observable<RagSearchResponse> {
    return this.knowledgeApiService.ragProductivitySearch(params);
  }

  thumbsUpFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    return this.feedbackApiService.thumbsUpFeedback(req);
  }

  thumbsDownFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    return this.feedbackApiService.thumbsDownFeedback(req);
  }

  getKnowledgeStats(): Observable<KnowledgeStats> {
    return this.knowledgeApiService.getKnowledgeStats();
  }

  getEntityRelationships(entityName: string): Observable<EntityRelationshipsResponse> {
    return this.knowledgeApiService.getEntityRelationships(entityName);
  }

  getReflexionSummary(limit: number = 10): Observable<PostSprintSummaryResponse> {
    return this.observabilityApiService.getReflexionSummary(limit);
  }

  getSystemDbValidate(): Observable<DbValidationResponse> {
    return this.systemApiService.getSystemDbValidate();
  }

  getKnowledgeHealth(): Observable<KnowledgeHealthResponse> {
    return this.knowledgeApiService.getKnowledgeHealth();
  }

  getKnowledgeHealthDetailed(): Observable<KnowledgeHealthDetailedResponse> {
    return this.knowledgeApiService.getKnowledgeHealthDetailed();
  }

  resetKnowledgeCircuitBreaker(): Observable<{ message: string }> {
    return this.knowledgeApiService.resetKnowledgeCircuitBreaker();
  }

}
