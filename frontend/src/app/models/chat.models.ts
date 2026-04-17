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
