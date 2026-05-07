import { Injectable, computed, inject, signal } from '@angular/core'

import { AuthService } from '../../core/auth/auth.service'
import type { AgentEvent } from '../../core/services/agent-events.service'
import type {
  AutonomyStatusResponse,
  ConversationMeta,
  DocListItem,
  DocSearchResultItem,
  GenerativeMemoryItem,
  Goal,
  MemoryItem,
  Tool
} from '../../services/backend-api.service'
import { conversationUpdatedAt, isConversationMemory } from './conversations.utils'
import type {
  AdvancedRailTab,
  ChatMessageView,
  CustomerTab,
  FeedbackUiState,
  RagMode,
  RagResultViewTab,
  RagUiResult,
  RailNotice,
  ThoughtStreamItem
} from './conversations.types'

@Injectable({ providedIn: 'root' })
export class ConversationStateFacade {
  private auth = inject(AuthService)

  readonly listLoading = signal(true)
  readonly historyLoading = signal(false)
  readonly contextLoading = signal(false)
  readonly sending = signal(false)
  readonly error = signal('')
  readonly search = signal('')

  readonly conversations = signal<ConversationMeta[]>([])
  readonly messages = signal<ChatMessageView[]>([])
  readonly events = signal<AgentEvent[]>([])
  readonly docs = signal<DocListItem[]>([])
  readonly memoryUser = signal<MemoryItem[]>([])
  readonly docSearchResults = signal<DocSearchResultItem[]>([])
  readonly generativeMemoryResults = signal<GenerativeMemoryItem[]>([])
  readonly ragResult = signal<RagUiResult | null>(null)
  readonly docsNotice = signal<RailNotice | null>(null)
  readonly memoryNotice = signal<RailNotice | null>(null)
  readonly ragNotice = signal<RailNotice | null>(null)
  readonly autonomyNotice = signal<RailNotice | null>(null)

  readonly selectedId = signal<string | null>(null)
  readonly streamStatus = signal('idle')
  readonly streamTyping = signal(false)
  readonly selectedRole = signal('orchestrator')
  readonly selectedPriority = signal('fast_and_cheap')
  readonly streamingEnabled = signal(true)
  readonly latestCognitiveState = signal<string>('')
  readonly latestToolStatus = signal<string>('')
  readonly pendingActionLoading = signal<Record<number, boolean>>({})
  readonly showAdvanced = signal(false)
  readonly advancedRailTab = signal<AdvancedRailTab>('cliente')
  readonly customerTab = signal<CustomerTab>('docs')
  readonly copiedCitation = signal('')
  readonly autonomyLoading = signal(false)
  readonly autonomySaving = signal(false)
  readonly autonomyStatus = signal<AutonomyStatusResponse | null>(null)
  readonly autonomyGoals = signal<Goal[]>([])
  readonly autonomyTools = signal<Tool[]>([])
  readonly autonomyError = signal('')
  readonly goalCreateTitle = signal('')
  readonly goalCreateDescription = signal('')
  readonly goalCreateLoading = signal(false)
  readonly goalCreateError = signal('')

  readonly docUploadInFlight = signal(false)
  readonly docUploadProgress = signal<number | null>(null)
  readonly docUploadError = signal('')
  readonly docLinkUrl = signal('')
  readonly docLinkLoading = signal(false)
  readonly docLinkError = signal('')
  readonly docSearchQuery = signal('')
  readonly docSearchLoading = signal(false)
  readonly docSearchError = signal('')
  readonly deletingDocIds = signal<Record<string, boolean>>({})

  readonly memoryDraft = signal('')
  readonly memoryImportance = signal<number | null>(null)
  readonly memoryType = signal('episodic')
  readonly memoryAddLoading = signal(false)
  readonly memoryAddError = signal('')
  readonly memorySearchQuery = signal('')
  readonly memorySearchLimit = signal(5)
  readonly memorySearchLoading = signal(false)
  readonly memorySearchError = signal('')

  readonly ragMode = signal<RagMode>('hybrid_search')
  readonly ragQuery = signal('')
  readonly ragLoading = signal(false)
  readonly ragError = signal('')
  readonly ragResultViewTab = signal<RagResultViewTab>('resposta')

  readonly feedbackStateByMessageId = signal<Record<string, FeedbackUiState>>({})
  readonly feedbackCommentDraftByMessageId = signal<Record<string, string>>({})

  readonly selectedUploadFile = signal<File | null>(null)
  readonly traceSteps = signal<any[]>([])
  readonly showTrace = signal(false)
  readonly thoughtStream = signal<ThoughtStreamItem[]>([])

  readonly user = this.auth.user
  readonly isAdmin = this.auth.isAdmin

  readonly displayName = computed(() => {
    const user = this.user()
    return user?.display_name || user?.username || user?.email || 'Operador'
  })

  readonly filteredConversations = computed(() => {
    const term = this.search().trim().toLowerCase()
    const items = this.conversations()
      .slice()
      .sort((a, b) => conversationUpdatedAt(b) - conversationUpdatedAt(a))
    if (!term) return items
    return items.filter((conv) => {
      const title = String(conv.title || '')
      const id = String(conv.conversation_id || '')
      return title.toLowerCase().includes(term) || id.toLowerCase().includes(term)
    })
  })

  readonly selectedConversation = computed(() => {
    const id = this.selectedId()
    if (!id) return null
    return this.conversations().find((conv) => conv.conversation_id === id) || null
  })

  readonly isSimpleMode = computed(() => !this.showAdvanced())

  readonly latestAssistantMessage = computed(() => {
    const items = this.messages()
    for (let idx = items.length - 1; idx >= 0; idx -= 1) {
      if (items[idx].role === 'assistant') return items[idx]
    }
    return null
  })

  readonly conversationMemory = computed(() => {
    const conversationId = this.selectedId()
    const items = this.memoryUser()
    if (!conversationId) return []
    return items
      .filter((item) => isConversationMemory(item, conversationId))
      .slice(0, 6)
  })

  readonly userMemory = computed(() => {
    const conversationId = this.selectedId()
    const items = this.memoryUser()
    const filtered = conversationId
      ? items.filter((item) => !isConversationMemory(item, conversationId))
      : items
    return filtered.slice(0, 6)
  })

  readonly autonomyActiveGoals = computed(() => this.autonomyGoals()
    .filter((goal) => goal.status === 'pending' || goal.status === 'in_progress')
    .slice(0, 6))

  readonly autonomyEnabledTools = computed(() => this.autonomyTools()
    .filter((tool) => tool.enabled !== false)
    .slice(0, 8))

  readonly hasConversationSelected = computed(() => Boolean(this.selectedId()))

  readonly selectedTitle = computed(() => {
    const selected = this.selectedConversation()
    if (selected?.title) return selected.title
    const id = this.selectedId()
    if (!id) return 'Nova conversa'
    return `Conversa ${id.slice(0, 8)}`
  })

  readonly avatarState = computed(() => {
    if (this.streamTyping()) return 'speaking'
    const status = this.streamStatus()
    if (status === 'connecting' || status === 'retrying' || status === 'open') return 'thinking'
    return 'idle'
  })

  readonly streamBadge = computed(() => {
    const status = this.streamStatus()
    if (status === 'streaming') return { label: 'Streaming', variant: 'success' as const }
    if (status === 'connecting' || status === 'retrying') return { label: 'Conectando', variant: 'warning' as const }
    if (status === 'error') return { label: 'Erro', variant: 'error' as const }
    if (status === 'open') return { label: 'Pronto', variant: 'info' as const }
    return { label: 'Aguardando', variant: 'neutral' as const }
  })
}
