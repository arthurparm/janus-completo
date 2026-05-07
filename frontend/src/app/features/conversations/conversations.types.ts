import type {
  ChatAgentState,
  ChatConfirmationState,
  ChatUnderstanding,
  Citation,
  CitationStatus
} from '../../services/backend-api.service'

export type ChatRole = 'user' | 'assistant' | 'system' | 'event'

export interface ChatMessageView {
  id: string
  backendMessageId?: string
  role: ChatRole
  text: string
  timestamp: number
  estimated_wait_seconds?: number
  estimated_wait_range_seconds?: number[]
  processing_profile?: string
  processing_notice?: string
  citations?: Citation[]
  understanding?: ChatUnderstanding
  citation_status?: CitationStatus
  confirmation?: ChatConfirmationState
  agent_state?: ChatAgentState
  latency_ms?: number
  provider?: string
  model?: string
  delivery_status?: string
  failure_classification?: string
  streaming?: boolean
  error?: boolean
}

export type ThoughtKind = 'agent' | 'stream' | 'system'

export interface ThoughtStreamItem {
  id: string
  kind: ThoughtKind
  title: string
  text: string
  timestamp: number
}

export type RagMode = 'search' | 'user-chat' | 'user_chat' | 'hybrid_search' | 'productivity'
export type AdvancedRailTab = 'insights' | 'cliente' | 'autonomia'
export type CustomerTab = 'docs' | 'memoria' | 'rag'
export type TabGroup = 'advancedRail' | 'customer' | 'ragResult'
export type RailNoticeKind = 'success' | 'info' | 'warning' | 'error'
export type RailNoticeSection = 'docs' | 'memory' | 'rag' | 'autonomy'
export type RagResultViewTab = 'resposta' | 'fontes' | 'raw'

export interface FeedbackUiState {
  rating?: 'positive' | 'negative'
  commentOpen?: boolean
  submitting?: boolean
  submitted?: boolean
  error?: string
  serverMessage?: string
}

export interface RagUiResult {
  mode: RagMode
  answer?: string
  citations?: Citation[]
  results?: Record<string, unknown>[]
}

export interface RailNotice {
  kind: RailNoticeKind
  message: string
  visible: boolean
}

export interface RoleOption {
  value: string
  label: string
}

export interface PriorityOption {
  value: string
  label: string
}

export type GoalStatus = 'pending' | 'in_progress' | 'completed' | 'failed'
export type PendingActionResolution = 'approved' | 'rejected'
