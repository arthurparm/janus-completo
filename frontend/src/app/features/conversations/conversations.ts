import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, ViewChild, computed, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormControl, ReactiveFormsModule } from '@angular/forms'
import { ActivatedRoute, Router } from '@angular/router'
import { firstValueFrom, forkJoin, of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { Observable } from 'rxjs'

import { AuthService } from '../../core/auth/auth.service'
import { AgentEvent, AgentEventsService } from '../../core/services/agent-events.service'
import { ChatStreamService, StreamDone } from '../../services/chat-stream.service'
import {
  BackendApiService,
  ChatAgentState,
  ChatConfirmationState,
  ChatMessage,
  ChatStudyJobRef,
  ChatStudyJobResponse,
  ChatUnderstanding,
  ConversationMeta,
  CitationStatus,
  DocListItem,
  DocSearchResultItem,
  FeedbackQuickResponse,
  GenerativeMemoryItem,
  MemoryItem,
  PendingAction,
  Citation,
  AutonomyStatusResponse,
  Goal,
  RagHybridResponse,
  RagSearchResponse,
  RagUserChatResponse,
  RagUserChatV2Response,
  Tool
} from '../../services/backend-api.service'
import { Header } from '../../core/layout/header/header'
import { UiButtonComponent } from '../../shared/components/ui/button/button.component'
import { UiBadgeComponent } from '../../shared/components/ui/ui-badge/ui-badge.component'
import { JarvisAvatarComponent } from '../../shared/components/jarvis-avatar/jarvis-avatar.component'
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component'
import { MarkdownPipe } from '../../shared/pipes/markdown.pipe'
import { parseAdminCodeQaCommand } from './admin-code-qa.util'
import {
  coerceDateInputToMs,
  cognitiveStatusText,
  conversationUpdatedAt,
  createConversationViewId,
  extractErrorMessage,
  isConversationMemory,
  sanitizeChatText,
  sanitizeDiagnosticText,
  sanitizeStreamingText
} from './conversations.utils'

type ChatRole = 'user' | 'assistant' | 'system' | 'event'

interface ChatMessageView {
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

type ThoughtKind = 'agent' | 'stream' | 'system'

interface ThoughtStreamItem {
  id: string
  kind: ThoughtKind
  title: string
  text: string
  timestamp: number
}

type RagMode = 'search' | 'user-chat' | 'user_chat' | 'hybrid_search' | 'productivity'
type AdvancedRailTab = 'insights' | 'cliente' | 'autonomia'
type CustomerTab = 'docs' | 'memoria' | 'rag'
type TabGroup = 'advancedRail' | 'customer' | 'ragResult'
type RailNoticeKind = 'success' | 'info' | 'warning' | 'error'
type RailNoticeSection = 'docs' | 'memory' | 'rag' | 'autonomy'
type RagResultViewTab = 'resposta' | 'fontes' | 'raw'

interface FeedbackUiState {
  rating?: 'positive' | 'negative'
  commentOpen?: boolean
  submitting?: boolean
  submitted?: boolean
  error?: string
  serverMessage?: string
}

interface RagUiResult {
  mode: RagMode
  answer?: string
  citations?: Citation[]
  results?: Record<string, unknown>[]
}

interface RailNotice {
  kind: RailNoticeKind
  message: string
  visible: boolean
}

interface RoleOption {
  value: string
  label: string
}

interface PriorityOption {
  value: string
  label: string
}

type GoalStatus = 'pending' | 'in_progress' | 'completed' | 'failed'
type PendingActionResolution = 'approved' | 'rejected'

@Component({
  selector: 'app-conversations',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    Header,
    UiButtonComponent,
    UiBadgeComponent,
    JarvisAvatarComponent,
    SkeletonComponent,
    MarkdownPipe
  ],
  templateUrl: './conversations.html',
  styleUrls: ['./conversations.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConversationsComponent {
  private static readonly PENDING_ACTION_RESOLUTION_RE =
    /a[cç][aã]o pendente\s+#(\d+)\s+(aprovada|rejeitada)\b/i

  private api = inject(BackendApiService)
  private auth = inject(AuthService)
  private route = inject(ActivatedRoute)
  private router = inject(Router)
  private destroyRef = inject(DestroyRef)
  private eventsService = inject(AgentEventsService)
  private stream = inject(ChatStreamService)

  @ViewChild('messageList') messageList?: ElementRef<HTMLDivElement>

  readonly prompt = new FormControl('', { nonNullable: true })
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
  private readonly advancedRailTabOrder: AdvancedRailTab[] = ['insights', 'cliente', 'autonomia']
  private readonly customerTabOrder: CustomerTab[] = ['docs', 'memoria', 'rag']
  private readonly ragResultTabOrder: RagResultViewTab[] = ['resposta', 'fontes', 'raw']

  readonly roleOptions: RoleOption[] = [
    { value: 'orchestrator', label: 'Orchestrator' },
    { value: 'reasoner', label: 'Reasoner' },
    { value: 'code_generator', label: 'Code Generator' },
    { value: 'knowledge_curator', label: 'Knowledge Curator' },
    { value: 'security_auditor', label: 'Security Auditor' }
  ]

  readonly priorityOptions: PriorityOption[] = [
    { value: 'fast_and_cheap', label: 'Fast + Cheap' },
    { value: 'high_quality', label: 'High Quality' },
    { value: 'local_only', label: 'Local Only' }
  ]

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

  private streamingBuffer = ''
  private streamingMessageId: string | null = null
  private streamingConversationId: string | null = null
  private pendingConversationRouteId: string | null = null
  private scrollQueued = false
  private responseStartedAt: number | null = null
  private readonly noticeTimers = new Map<RailNoticeSection, ReturnType<typeof setTimeout>>()
  private readonly studyPollTimers = new Map<string, ReturnType<typeof setTimeout>>()
  readonly quickPrompts = [
    'Resuma esta conversa em 5 pontos.',
    'Quais sao os proximos passos recomendados para este tema?',
    'Me explique de forma simples, sem jargao tecnico.'
  ]

  constructor() {
    this.restoreAdvancedModePreference()
    this.restoreRailTabPreferences()
    this.loadConversations()

    this.route.paramMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const id = params.get('conversationId')
        this.selectConversation(id)
      })

    this.stream.status()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((status) => this.handleStreamStatus(status))

    this.stream.typing()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((typing) => this.streamTyping.set(typing))

    this.stream.partials()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((partial) => this.handleStreamPartial(partial.text))

    this.stream.done()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((done) => this.handleStreamDone(done))

    this.stream.errors()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((err) => this.handleStreamError(err.error))

    this.stream.cognitive()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((evt) => {
        const state = String(evt?.state || '')
        this.latestCognitiveState.set(state)
        if (state) {
          this.appendThought('agent', 'Estado cognitivo', cognitiveStatusText(state, evt.reason))
        }
      })

    this.stream.toolStatus()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((evt) => {
        const label = [evt.status, evt.tool_name].filter(Boolean).join(' · ')
        this.latestToolStatus.set(label)
        if (label) {
          this.appendThought('agent', 'Ferramenta', label)
        }
      })

    this.eventsService.events$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((event) => {
        this.events.update((items) => [event, ...items].slice(0, 24))
        this.appendThought('agent', event.agent_role || 'agent', event.content || 'evento sem descricao', event.timestamp)
      })

    this.destroyRef.onDestroy(() => {
      this.noticeTimers.forEach((timer) => clearTimeout(timer))
      this.noticeTimers.clear()
      this.studyPollTimers.forEach((timer) => clearTimeout(timer))
      this.studyPollTimers.clear()
      this.eventsService.disconnect()
      this.stream.stop()
    })
  }

  async sendMessage(): Promise<void> {
    if (this.sending()) return
    const message = this.prompt.value.trim()
    if (!message) return
    this.error.set('')
    this.sending.set(true)

    const conversationId = await this.ensureConversationId(false, false)
    if (!conversationId) {
      this.error.set('Falha ao criar conversa.')
      this.sending.set(false)
      return
    }

    const now = Date.now()
    this.appendMessage({
      id: createConversationViewId(),
      role: 'user',
      text: message,
      timestamp: now
    })
    this.updateConversationPreview(conversationId, 'user', message, now)
    this.prompt.setValue('')
    this.queueScroll()
    this.responseStartedAt = Date.now()

    const adminCodeQa = parseAdminCodeQaCommand(message, this.isAdmin())
    if (adminCodeQa.enabled) {
      if (!adminCodeQa.question) {
        const nowHelp = Date.now()
        const helpText = 'Para consultar codigo no modo admin, use: /code sua pergunta.'
        this.appendMessage({
          id: createConversationViewId(),
          role: 'assistant',
          text: helpText,
          timestamp: nowHelp
        })
        this.updateConversationPreview(conversationId, 'assistant', helpText, nowHelp)
        this.sending.set(false)
        this.flushPendingConversationNavigation(conversationId)
        this.queueScroll()
        return
      }

      this.sendAdminCodeQa(conversationId, adminCodeQa.question)
      return
    }

    if (this.streamingEnabled()) {
      this.startStreaming(conversationId, message)
    } else {
      this.sendClassic(conversationId, message)
    }
  }

  onComposerKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      this.sendMessage()
    }
  }

  clearComposer(): void {
    this.prompt.setValue('')
  }

  onSearchChange(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.search.set(target?.value || '')
  }

  clearSearch(): void {
    this.search.set('')
  }

  refresh(): void {
    this.loadConversations()
    const id = this.selectedId()
    if (id) {
      this.loadHistory(id)
      this.loadContext(id)
    }
  }

  openConversation(conv: ConversationMeta): void {
    if (!conv?.conversation_id) return
    this.router.navigate(['/conversations', conv.conversation_id])
  }

  async createConversation(): Promise<void> {
    if (this.sending()) return
    this.sending.set(true)
    const id = await this.ensureConversationId(true)
    if (!id) this.error.set('Falha ao criar conversa.')
    this.sending.set(false)
  }

  formatTime(timestamp?: number): string {
    if (!timestamp) return '--:--'
    return new Date(timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  }

  formatDate(timestamp?: number): string {
    if (!timestamp) return '--'
    return new Date(timestamp).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
  }

  formatLatency(latencyMs?: number): string {
    if (!latencyMs || latencyMs <= 0) return '--'
    if (latencyMs < 1000) return `${Math.round(latencyMs)} ms`
    return `${(latencyMs / 1000).toFixed(1)} s`
  }

  conversationPreviewText(conv: ConversationMeta): string {
    const text = sanitizeChatText(conv.last_message?.text || '')
    if (!text) return 'Sem mensagens ainda'
    return text.length > 110 ? `${text.slice(0, 110)}...` : text
  }

  conversationLastActivity(conv: ConversationMeta): string {
    const ts = conversationUpdatedAt(conv)
    if (!ts) return '--'
    const now = Date.now()
    if (Math.abs(now - ts) < 24 * 60 * 60 * 1000) return this.formatTime(ts)
    return this.formatDate(ts)
  }

  assistantRuntimeLabel(message: ChatMessageView): string {
    const provider = String(message.provider || '').trim()
    const model = String(message.model || '').trim()
    if (provider && model) return `${provider} / ${model}`
    if (provider) return provider
    if (model) return model
    return 'motor padrao'
  }

  authorLabel(message: ChatMessageView): string {
    if (message.role === 'assistant') return 'Janus'
    if (message.role === 'system') return 'Sistema'
    return this.displayName()
  }

  understandingIntentLabel(understanding?: ChatUnderstanding): string {
    const intent = String(understanding?.intent || '')
    if (intent === 'reminder') return 'Lembrete'
    if (intent === 'documentation_query') return 'Consulta de documentação'
    if (intent === 'action_request') return 'Solicitação de ação'
    if (intent === 'question') return 'Pergunta'
    return 'Geral'
  }

  understandingConfidence(understanding?: ChatUnderstanding): string {
    const confidence = Number(understanding?.confidence ?? 0)
    if (!Number.isFinite(confidence) || confidence <= 0) return '--'
    return `${Math.round(confidence * 100)}%`
  }

  understandingConfidenceBand(understanding?: ChatUnderstanding): 'high' | 'medium' | 'low' {
    const band = String(understanding?.confidence_band || '').toLowerCase()
    if (band === 'high' || band === 'medium' || band === 'low') return band
    const confidence = Number(understanding?.confidence ?? 0)
    if (confidence >= 0.8) return 'high'
    if (confidence >= 0.6) return 'medium'
    return 'low'
  }

  understandingConfidenceLabel(understanding?: ChatUnderstanding): string {
    const band = this.understandingConfidenceBand(understanding)
    if (band === 'high') return 'Confianca alta'
    if (band === 'medium') return 'Confianca media'
    return 'Confianca baixa'
  }

  citationTitle(cite: Citation): string {
    const base = cite.file_path || cite.title || cite.doc_id || 'fonte'
    const line = this.citationLine(cite)
    return line ? `${base}:${line}` : base
  }

  citationLine(cite: Citation): string {
    const start = cite.line_start ?? cite.line
    const end = cite.line_end
    if (start == null && end == null) return ''
    if (start != null && end != null && String(start) !== String(end)) {
      return `${start}-${end}`
    }
    return String(start ?? end ?? '')
  }

  citationScore(cite: Citation): string {
    const score = Number(cite.score)
    if (!Number.isFinite(score) || score <= 0) return '--'
    return `${Math.round(score * 100)}%`
  }

  citationReference(cite: Citation): string {
    const line = this.citationLine(cite)
    const base = cite.file_path || cite.title || cite.doc_id || 'fonte'
    if (!line) return base
    return `${base}:${line}`
  }

  copyCitation(cite: Citation): void {
    const reference = this.citationReference(cite)
    const clipboard = typeof navigator !== 'undefined' ? navigator.clipboard : null
    if (!clipboard?.writeText) return
    clipboard.writeText(reference).then(() => {
      this.copiedCitation.set(reference)
      setTimeout(() => {
        if (this.copiedCitation() === reference) {
          this.copiedCitation.set('')
        }
      }, 1400)
    }).catch(() => {
      this.copiedCitation.set('')
    })
  }

  confirmLowConfidence(): void {
    this.prompt.setValue('Confirmo. Pode prosseguir com a acao solicitada.')
  }

  toggleAdvanced(): void {
    this.showAdvanced.update((value) => {
      const next = !value
      this.persistAdvancedModePreference(next)
      return next
    })
  }

  useQuickPrompt(text: string): void {
    this.prompt.setValue(text)
  }

  setAdvancedRailTab(tab: AdvancedRailTab): void {
    this.advancedRailTab.set(tab)
    this.persistRailTabPreference(this.advancedRailTabStorageKey, tab)
  }

  onAdvancedRailTabKeydown(event: KeyboardEvent): void {
    this.moveTabSelection<AdvancedRailTab>(
      event,
      this.advancedRailTab(),
      this.advancedRailTabOrder,
      (tab) => this.setAdvancedRailTab(tab),
      'advancedRail'
    )
  }

  setCustomerTab(tab: CustomerTab): void {
    this.customerTab.set(tab)
    this.persistRailTabPreference(this.customerTabStorageKey, tab)
  }

  onCustomerTabKeydown(event: KeyboardEvent): void {
    this.moveTabSelection<CustomerTab>(
      event,
      this.customerTab(),
      this.customerTabOrder,
      (tab) => this.setCustomerTab(tab),
      'customer'
    )
  }

  onDocLinkInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.docLinkUrl.set(target?.value || '')
  }

  onDocSearchInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.docSearchQuery.set(target?.value || '')
  }

  onMemoryDraftInput(event: Event): void {
    const target = event.target as HTMLTextAreaElement | null
    this.memoryDraft.set(target?.value || '')
  }

  onMemoryImportanceInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    const raw = target?.value?.trim() || ''
    if (!raw) {
      this.memoryImportance.set(null)
      return
    }
    const n = Number(raw)
    this.memoryImportance.set(Number.isFinite(n) ? n : null)
  }

  onMemoryTypeChange(event: Event): void {
    const target = event.target as HTMLSelectElement | null
    this.memoryType.set(target?.value || 'episodic')
  }

  onMemorySearchQueryInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.memorySearchQuery.set(target?.value || '')
  }

  onRagQueryInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.ragQuery.set(target?.value || '')
  }

  onRagModeChange(event: Event): void {
    const target = event.target as HTMLSelectElement | null
    const value = (target?.value || 'hybrid_search') as RagMode
    this.ragMode.set(value)
  }

  ragModeLabel(mode: RagMode): string {
    if (mode === 'hybrid_search') return 'Híbrido (Vetor + Grafo)'
    if (mode === 'search') return 'Busca vetorial'
    if (mode === 'user-chat') return 'Chat pessoal (v1)'
    if (mode === 'user_chat') return 'Chat pessoal (v2)'
    return 'Produtividade'
  }

  ragModeHint(mode: RagMode): string {
    if (mode === 'hybrid_search') return 'Combina busca vetorial e grafo para contexto mais completo.'
    if (mode === 'search') return 'Busca vetorial direta em documentos e memória indexada.'
    if (mode === 'user-chat') return 'Consulta contexto pessoal legado (v1).'
    if (mode === 'user_chat') return 'Consulta contexto pessoal atual (v2).'
    return 'Consulta dados de produtividade do usuário.'
  }

  memoryTypeLabel(value: string | null | undefined): string {
    if (value === 'episodic') return 'Episódica'
    if (value === 'semantic') return 'Semântica'
    if (value === 'procedural') return 'Procedural'
    return value || 'Memória'
  }

  generativeMemoryMetaLine(item: GenerativeMemoryItem): string {
    const parts = [this.memoryTypeLabel(item.type)]

    const meta = item.metadata || {}
    const rawImportance = typeof meta === 'object'
      ? (meta as Record<string, unknown>)['importance']
      : undefined
    const importance = typeof rawImportance === 'number'
      ? rawImportance
      : typeof rawImportance === 'string'
        ? Number(rawImportance)
        : NaN
    if (Number.isFinite(importance)) {
      parts.push(`Importância ${Math.round(importance)}`)
    }

    const scoreValue = item['score']
    const score = typeof scoreValue === 'number'
      ? scoreValue
      : typeof scoreValue === 'string'
        ? Number(scoreValue)
        : NaN
    if (Number.isFinite(score)) {
      parts.push(`Score ${score.toFixed(2)}`)
    }

    const timestamp = coerceDateInputToMs(item.created_at ?? item.updated_at)
    if (timestamp) {
      parts.push(new Date(timestamp).toLocaleString('pt-BR', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      }))
    }

    return parts.join(' · ')
  }

  memoryTrackKey(item: MemoryItem, index: number): string {
    const compositeId = String(item.composite_id || '').trim()
    if (compositeId) return compositeId
    const ts = Number(item.ts_ms)
    const normalizedTs = Number.isFinite(ts) ? ts : (coerceDateInputToMs(item.metadata?.timestamp) || 0)
    const content = sanitizeDiagnosticText(item.content, 'memory').slice(0, 48)
    return `${normalizedTs}:${content}:${index}`
  }

  setRagResultViewTab(tab: RagResultViewTab): void {
    this.ragResultViewTab.set(tab)
  }

  onRagResultTabKeydown(event: KeyboardEvent): void {
    this.moveTabSelection<RagResultViewTab>(
      event,
      this.ragResultViewTab(),
      this.ragResultTabOrder,
      (tab) => this.setRagResultViewTab(tab),
      'ragResult'
    )
  }

  ragHasAnswer(): boolean {
    return Boolean(this.ragResult()?.answer?.trim())
  }

  ragHasSources(): boolean {
    return Boolean(this.ragResult()?.citations?.length)
  }

  ragHasRows(): boolean {
    return Boolean(this.ragResult()?.results?.length)
  }

  isBusinessDocError(message: string | null | undefined): boolean {
    const value = String(message || '').toLowerCase()
    return value.includes('quota') || value.includes('limite') || value.includes('maior')
  }

  onGoalCreateTitleInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.goalCreateTitle.set(target?.value || '')
  }

  onGoalCreateDescriptionInput(event: Event): void {
    const target = event.target as HTMLTextAreaElement | null
    this.goalCreateDescription.set(target?.value || '')
  }

  onDocFileSelected(event: Event): void {
    const target = event.target as HTMLInputElement | null
    const file = target?.files?.[0] || null
    this.selectedUploadFile.set(file)
    this.docUploadError.set('')
  }

  uploadSelectedDoc(): void {
    const file = this.selectedUploadFile()
    if (!file) {
      this.docUploadError.set('Selecione um arquivo para upload.')
      return
    }
    const userId = this.userIdString()
    this.docUploadError.set('')
    this.clearNotice('docs')
    this.docUploadInFlight.set(true)
    this.docUploadProgress.set(0)
    this.api.uploadDocument(file, this.selectedId() || undefined, userId || undefined)
      .pipe(catchError((err) => {
        this.docUploadError.set(extractErrorMessage(err, 'Falha no upload do documento.'))
        this.docUploadInFlight.set(false)
        this.docUploadProgress.set(null)
        return of(null)
      }))
      .subscribe((evt) => {
        if (!evt) return
        if (typeof evt.progress === 'number') {
          this.docUploadProgress.set(evt.progress)
        }
        if (evt.response) {
          const status = String(evt.response.status || '')
          if (status === 'file_too_large') {
            this.docUploadError.set('Arquivo maior que o limite permitido.')
          } else if (status === 'quota_exceeded') {
            this.docUploadError.set('Quota de documentos excedida para este usuário.')
          } else {
            this.docUploadError.set('')
            this.setNotice('docs', 'success', 'Upload concluído.')
          }
          this.docUploadInFlight.set(false)
          this.docUploadProgress.set(status ? 100 : null)
          this.selectedUploadFile.set(null)
          this.refreshConversationContext()
        }
      })
  }

  linkDocumentUrl(): void {
    const url = this.docLinkUrl().trim()
    const conversationId = this.selectedId()
    if (!url) {
      this.docLinkError.set('Informe uma URL para vincular.')
      return
    }
    if (!conversationId) {
      this.docLinkError.set('Selecione ou crie uma conversa antes de vincular URL.')
      return
    }
    this.docLinkError.set('')
    this.clearNotice('docs')
    this.docLinkLoading.set(true)
    this.api.linkUrl(conversationId, url, this.userIdString() || undefined)
      .pipe(catchError((err) => {
        this.docLinkError.set(extractErrorMessage(err, 'Falha ao vincular URL.'))
        this.docLinkLoading.set(false)
        return of(null)
      }))
      .subscribe((resp) => {
        if (!resp) return
        this.docLinkLoading.set(false)
        if (resp.status === 'file_too_large') {
          this.docLinkError.set('Conteúdo remoto acima do limite.')
        } else if (resp.status === 'quota_exceeded') {
          this.docLinkError.set('Quota de documentos excedida.')
        } else {
          this.docLinkUrl.set('')
          this.docLinkError.set('')
          this.setNotice('docs', 'success', 'Documento vinculado.')
        }
        this.refreshConversationContext()
      })
  }

  searchDocs(): void {
    const query = this.docSearchQuery().trim()
    if (!query) {
      this.docSearchError.set('Digite um termo para buscar documentos.')
      this.docSearchResults.set([])
      return
    }
    this.docSearchError.set('')
    this.clearNotice('docs')
    this.docSearchLoading.set(true)
    this.api.searchDocuments(query, undefined, undefined, this.userIdString())
      .pipe(catchError((err) => {
        this.docSearchError.set(extractErrorMessage(err, 'Falha ao buscar documentos.'))
        this.docSearchLoading.set(false)
        return of({ results: [] as DocSearchResultItem[] })
      }))
      .subscribe((resp) => {
        this.docSearchResults.set(resp.results || [])
        this.docSearchLoading.set(false)
        if ((resp.results || []).length > 0) {
          this.setNotice('docs', 'info', 'Busca concluída.')
        }
      })
  }

  deleteDoc(docId: string): void {
    if (!docId) return
    if (typeof window !== 'undefined' && !window.confirm('Excluir este documento?')) return
    this.deletingDocIds.update((curr) => ({ ...curr, [docId]: true }))
    this.api.deleteDocument(docId, this.userIdString())
      .pipe(catchError((err) => {
        this.docSearchError.set(extractErrorMessage(err, 'Falha ao excluir documento.'))
        this.deletingDocIds.update((curr) => {
          const next = { ...curr }
          delete next[docId]
          return next
        })
        return of(null)
      }))
      .subscribe((resp) => {
        this.deletingDocIds.update((curr) => {
          const next = { ...curr }
          delete next[docId]
          return next
        })
        if (!resp) return
        this.docs.update((items) => items.filter((d) => d.doc_id !== docId))
        this.docSearchResults.update((items) => items.filter((d) => String(d.doc_id) !== docId))
        this.setNotice('docs', 'success', 'Documento removido.')
      })
  }

  addMemory(): void {
    const content = this.memoryDraft().trim()
    if (!content) {
      this.memoryAddError.set('Digite uma memória para adicionar.')
      return
    }
    this.memoryAddError.set('')
    this.clearNotice('memory')
    this.memoryAddLoading.set(true)
    const importance = this.memoryImportance()
    const userId = this.userIdString()
    const conversationId = this.selectedId() || undefined
    this.api.addGenerativeMemory(content, {
      type: this.memoryType(),
      importance: typeof importance === 'number' ? importance : undefined,
      userId,
      conversationId,
      sessionId: conversationId
    })
      .pipe(catchError((err) => {
        this.memoryAddError.set(extractErrorMessage(err, 'Falha ao adicionar memória.'))
        this.memoryAddLoading.set(false)
        return of(null)
      }))
      .subscribe((resp) => {
        if (!resp) return
        this.memoryDraft.set('')
        this.memoryAddLoading.set(false)
        this.setNotice('memory', 'success', 'Memória adicionada.')
        this.refreshConversationContext()
        if (this.memorySearchQuery().trim()) {
          this.searchGenerativeMemory()
        }
      })
  }

  searchGenerativeMemory(): void {
    const query = this.memorySearchQuery().trim()
    if (!query) {
      this.memorySearchError.set('Digite um termo para buscar memória generativa.')
      this.generativeMemoryResults.set([])
      return
    }
    this.memorySearchError.set('')
    this.clearNotice('memory')
    this.memorySearchLoading.set(true)
    this.api.getGenerativeMemories(query, this.memorySearchLimit(), {
      userId: this.userIdString(),
      conversationId: this.selectedId() || undefined
    })
      .pipe(catchError((err) => {
        this.memorySearchError.set(extractErrorMessage(err, 'Falha ao buscar memória generativa.'))
        this.memorySearchLoading.set(false)
        return of([] as GenerativeMemoryItem[])
      }))
      .subscribe((items) => {
        const next = items || []
        this.generativeMemoryResults.set(next)
        this.memorySearchLoading.set(false)
        this.setNotice('memory', 'info', next.length ? 'Busca concluída.' : 'Consulta concluída sem resultados.')
      })
  }

  runRagQuery(): void {
    const query = this.ragQuery().trim()
    if (!query) {
      this.ragError.set('Digite uma consulta para executar no RAG.')
      this.ragResult.set(null)
      return
    }
    const mode = this.ragMode()
    const userId = this.userIdString()
    const conversationId = this.selectedId() || undefined
    this.ragError.set('')
    this.clearNotice('rag')
    this.ragResultViewTab.set('resposta')
    this.ragLoading.set(true)

    let request$: Observable<unknown>

    if (mode === 'search') {
      request$ = this.api.ragSearch({ query, limit: 5 })
    } else if (mode === 'user-chat') {
      if (!userId) {
        this.ragLoading.set(false)
        this.ragError.set('Usuário autenticado necessário para RAG user-chat.')
        this.setNotice('rag', 'warning', 'Entre com usuário autenticado para usar este modo.')
        return
      }
      request$ = this.api.ragUserChat({ query, user_id: userId, session_id: conversationId, limit: 5 })
    } else if (mode === 'user_chat') {
      request$ = this.api.ragUserChatV2({ query, user_id: userId || undefined, session_id: conversationId, limit: 5 })
    } else if (mode === 'productivity') {
      if (!userId) {
        this.ragLoading.set(false)
        this.ragError.set('Usuário autenticado necessário para RAG productivity.')
        this.setNotice('rag', 'warning', 'Entre com usuário autenticado para usar este modo.')
        return
      }
      request$ = this.api.ragProductivitySearch({ query, user_id: userId, limit: 5 })
    } else {
      request$ = this.api.ragHybridSearch({ query, user_id: userId || undefined, limit: 5 })
    }

    request$
      .pipe(catchError((err) => {
        this.ragError.set(extractErrorMessage(err, 'Falha ao executar consulta RAG.'))
        this.ragLoading.set(false)
        return of(null)
      }))
      .subscribe((resp: unknown) => {
        this.ragLoading.set(false)
        if (!resp) {
          this.ragResult.set(null)
          return
        }
        if (typeof resp === 'object' && resp !== null && 'results' in resp) {
          const v2 = resp as RagUserChatV2Response
          const results = (v2.results || []) as Record<string, unknown>[]
          this.ragResult.set({ mode, results })
          this.setNotice('rag', 'info', results.length ? 'Consulta RAG concluída.' : 'Consulta concluída sem resultados.')
          return
        }
        if (typeof resp === 'object' && resp !== null && 'answer' in resp) {
          const standard = resp as RagSearchResponse | RagUserChatResponse | RagHybridResponse
          const answer = standard.answer || ''
          const citations = standard.citations || []
          this.ragResult.set({ mode, answer, citations })
          const hasAnswer = Boolean(answer.trim())
          const hasCitations = citations.length > 0
          this.setNotice('rag', 'info', hasAnswer || hasCitations ? 'Consulta RAG concluída.' : 'Consulta concluída sem resultados.')
          return
        }
        this.ragResult.set({ mode, results: [] })
        this.setNotice('rag', 'info', 'Consulta concluída sem resultados.')
      })
  }

  feedbackState(message: ChatMessageView): FeedbackUiState {
    return this.feedbackStateByMessageId()[message.id] || {}
  }

  feedbackCommentDraft(messageId: string): string {
    return this.feedbackCommentDraftByMessageId()[messageId] || ''
  }

  onFeedbackCommentInput(messageId: string, event: Event): void {
    const target = event.target as HTMLTextAreaElement | null
    const value = target?.value || ''
    this.feedbackCommentDraftByMessageId.update((curr) => ({ ...curr, [messageId]: value }))
  }

  toggleFeedbackComment(messageId: string): void {
    this.feedbackStateByMessageId.update((curr) => {
      const prev = curr[messageId] || {}
      return { ...curr, [messageId]: { ...prev, commentOpen: !prev.commentOpen } }
    })
  }

  sendThumbsUp(msg: ChatMessageView): void {
    this.submitFeedback(msg, 'positive')
  }

  sendThumbsDown(msg: ChatMessageView): void {
    this.submitFeedback(msg, 'negative')
  }

  createGoal(): void {
    const title = this.goalCreateTitle().trim()
    const description = this.goalCreateDescription().trim()
    if (!title) {
      this.goalCreateError.set('Informe um título para a meta.')
      return
    }
    this.goalCreateError.set('')
    this.clearNotice('autonomy')
    this.goalCreateLoading.set(true)
    this.api.createGoal({
      title,
      description,
      priority: 2
    })
      .pipe(catchError((err) => {
        this.goalCreateError.set(extractErrorMessage(err, 'Falha ao criar meta.'))
        this.goalCreateLoading.set(false)
        return of(null)
      }))
      .subscribe((goal) => {
        this.goalCreateLoading.set(false)
        if (!goal) return
        this.goalCreateTitle.set('')
        this.goalCreateDescription.set('')
        this.autonomyGoals.update((items) => [goal, ...items])
        this.setNotice('autonomy', 'success', 'Meta criada.')
      })
  }

  refreshAutonomy(): void {
    this.loadAutonomyContext()
  }

  toggleAutonomyLoop(): void {
    if (this.autonomySaving()) return
    this.autonomySaving.set(true)
    this.autonomyError.set('')
    this.clearNotice('autonomy')
    const active = Boolean(this.autonomyStatus()?.active)
    const request$ = active
      ? this.api.stopAutonomy()
      : this.api.startAutonomy({
        interval_seconds: 60,
        risk_profile: 'balanced',
        user_id: this.user()?.id ? String(this.user()?.id) : undefined
      })
    request$
      .pipe(catchError((err) => {
        this.autonomyError.set(extractErrorMessage(err, 'Falha ao atualizar autonomia.'))
        return of(null)
      }))
      .subscribe(() => {
        this.autonomySaving.set(false)
        this.setNotice('autonomy', 'success', active ? 'Loop autônomo interrompido.' : 'Loop autônomo iniciado.')
        this.loadAutonomyContext()
      })
  }

  markGoalStatus(goal: Goal, status: GoalStatus): void {
    if (!goal?.id || this.autonomySaving()) return
    this.autonomySaving.set(true)
    this.autonomyError.set('')
    this.clearNotice('autonomy')
    this.api.updateGoalStatus(goal.id, status)
      .pipe(catchError((err) => {
        this.autonomyError.set(extractErrorMessage(err, 'Falha ao atualizar meta.'))
        return of(null)
      }))
      .subscribe((updated) => {
        if (updated) {
          this.autonomyGoals.update((items) => items.map((item) => item.id === updated.id ? updated : item))
          this.setNotice('autonomy', 'success', 'Status da meta atualizado.')
        }
        this.autonomySaving.set(false)
      })
  }

  goalStatusLabel(goal: Goal): string {
    if (goal.status === 'in_progress') return 'Em andamento'
    if (goal.status === 'completed') return 'Concluida'
    if (goal.status === 'failed') return 'Falhou'
    return 'Pendente'
  }

  readonly traceSteps = signal<any[]>([])
  readonly showTrace = signal(false)
  readonly thoughtStream = signal<ThoughtStreamItem[]>([])
  private readonly advancedModeStorageKey = 'janus.conversations.show_advanced_mode'
  private readonly advancedRailTabStorageKey = 'janus.conversations.advanced_rail_tab'
  private readonly customerTabStorageKey = 'janus.conversations.customer_tab'

  // ... (inside class)

  toggleTrace() {
    this.showTrace.update(v => !v)
    if (this.showTrace() && this.selectedId()) {
      this.loadTrace(this.selectedId()!)
    }
  }

  private loadTrace(conversationId: string): void {
    this.api.getConversationTrace(conversationId).pipe(
      catchError(() => of([]))
    ).subscribe(steps => {
      this.traceSteps.set(steps)
    })
  }

  // Hook into selectConversation to clear/reload trace
  private selectConversation(id: string | null): void {
    if (id === this.selectedId()) return

    // During "create conversation + send first message", router param updates can arrive mid-stream.
    // Avoid tearing down the active stream/UI state for that transient navigation synchronization.
    if (!id && this.sending() && this.streamingMessageId && this.streamingConversationId) {
      return
    }

    this.selectedId.set(id)

    const preserveActiveStreamForTarget = Boolean(
      id &&
      this.sending() &&
      this.streamingMessageId &&
      this.streamingConversationId === id
    )

    if (preserveActiveStreamForTarget && id) {
      this.eventsService.connect(id)
      this.loadContext(id)
      if (this.showTrace()) {
        this.loadTrace(id)
      }
      return
    }

    this.messages.set([])
    this.events.set([])
    this.docs.set([])
    this.memoryUser.set([])
    this.docSearchResults.set([])
    this.generativeMemoryResults.set([])
    this.ragResult.set(null)
    this.ragError.set('')
    this.ragResultViewTab.set('resposta')
    this.docSearchError.set('')
    this.memorySearchError.set('')
    this.clearNotice('docs')
    this.clearNotice('memory')
    this.clearNotice('rag')
    this.clearNotice('autonomy')
    this.traceSteps.set([]) // Clear trace
    this.thoughtStream.set([])
    this.copiedCitation.set('')
    this.feedbackStateByMessageId.set({})
    this.feedbackCommentDraftByMessageId.set({})
    this.stream.stop()
    this.sending.set(false)
    this.responseStartedAt = null
    this.streamingBuffer = ''
    this.streamingMessageId = null
    this.streamingConversationId = null

    if (!id) {
      this.eventsService.disconnect()
      this.historyLoading.set(false)
      this.contextLoading.set(false)
      return
    }

    this.eventsService.connect(id)
    this.loadHistory(id)
    this.loadContext(id)
    if (this.showTrace()) {
      this.loadTrace(id)
    }
  }

  private loadConversations(): void {
    this.listLoading.set(true)
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    this.api.listConversations(userId ? { user_id: userId, limit: 60 } : { limit: 60 })
      .pipe(
        map((resp) => resp.conversations || []),
        catchError(() => of([]))
      )
      .subscribe((items) => {
        this.conversations.set(items)
        this.listLoading.set(false)
      })
  }

  private loadHistory(conversationId: string): void {
    this.historyLoading.set(true)
    this.api.getChatHistoryPaginated(conversationId, { limit: 80, offset: 0 })
      .pipe(
        map((resp) => resp.messages || []),
        catchError(() => of([]))
      )
      .subscribe((items) => {
        const mapped = items.map((msg) => this.mapMessage(msg))
        this.messages.set(this.reconcileResolvedPendingActions(mapped))
        this.historyLoading.set(false)
        this.queueScroll()
      })
  }

  private loadContext(conversationId: string): void {
    this.contextLoading.set(true)
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    forkJoin({
      docs: this.api.listDocuments(conversationId, userId).pipe(
        map((resp) => resp.items || []),
        catchError(() => of([]))
      ),
      memory: this.api.getMemoryTimeline({
        limit: 24,
        user_id: userId,
        conversation_id: conversationId
      }).pipe(
        map((items) => items.filter((item) => isConversationMemory(item, conversationId))),
        catchError(() => of([] as MemoryItem[]))
      )
    }).subscribe((result) => {
      this.docs.set(result.docs)
      this.memoryUser.set(result.memory)
      this.contextLoading.set(false)
    })
    this.loadAutonomyContext()
  }

  private refreshConversationContext(): void {
    const id = this.selectedId()
    if (!id) return
    this.loadContext(id)
  }

  private userIdString(): string | undefined {
    const id = this.user()?.id
    return id != null ? String(id) : undefined
  }

  private setNotice(section: RailNoticeSection, kind: RailNoticeKind, message: string, autoHideMs = 2800): void {
    const setter = this.noticeSignal(section)
    const existingTimer = this.noticeTimers.get(section)
    if (existingTimer) {
      clearTimeout(existingTimer)
      this.noticeTimers.delete(section)
    }
    setter.set({ kind, message, visible: true })
    if (kind === 'error') return
    const timer = setTimeout(() => {
      setter.set(null)
      this.noticeTimers.delete(section)
    }, autoHideMs)
    this.noticeTimers.set(section, timer)
  }

  private clearNotice(section: RailNoticeSection): void {
    const existingTimer = this.noticeTimers.get(section)
    if (existingTimer) {
      clearTimeout(existingTimer)
      this.noticeTimers.delete(section)
    }
    this.noticeSignal(section).set(null)
  }

  private noticeSignal(section: RailNoticeSection) {
    if (section === 'docs') return this.docsNotice
    if (section === 'memory') return this.memoryNotice
    if (section === 'rag') return this.ragNotice
    return this.autonomyNotice
  }

  private moveTabSelection<T extends string>(
    event: KeyboardEvent,
    current: T,
    order: readonly T[],
    setter: (tab: T) => void,
    group: TabGroup
  ): void {
    const key = event.key
    const currentIndex = order.indexOf(current)
    if (currentIndex < 0) return

    let nextIndex = currentIndex
    if (key === 'ArrowRight') nextIndex = (currentIndex + 1) % order.length
    else if (key === 'ArrowLeft') nextIndex = (currentIndex - 1 + order.length) % order.length
    else if (key === 'Home') nextIndex = 0
    else if (key === 'End') nextIndex = order.length - 1
    else if (key === 'Enter' || key === ' ') nextIndex = currentIndex
    else return

    event.preventDefault()
    const nextTab = order[nextIndex]
    setter(nextTab)

    if (typeof document === 'undefined') return
    const targetId = this.tabDomId(group, nextTab)
    document.getElementById(targetId)?.focus()
  }

  private tabDomId(group: TabGroup, tab: string): string {
    if (group === 'advancedRail') return `advanced-tab-${tab}`
    if (group === 'customer') return `customer-tab-${tab}`
    return `rag-view-tab-${tab}`
  }

  private submitFeedback(msg: ChatMessageView, rating: 'positive' | 'negative'): void {
    if (msg.role !== 'assistant') return
    const conversationId = this.selectedId()
    if (!conversationId) return
    const state = this.feedbackState(msg)
    if (state.submitting || state.submitted) return
    const messageId = String(msg.backendMessageId || msg.id)
    const userId = this.userIdString()
    const comment = this.feedbackCommentDraft(msg.id).trim() || undefined

    this.feedbackStateByMessageId.update((curr) => ({
      ...curr,
      [msg.id]: { ...(curr[msg.id] || {}), rating, submitting: true, error: '', serverMessage: '' }
    }))

    const request$ = rating === 'positive'
      ? this.api.thumbsUpFeedback({ conversation_id: conversationId, message_id: messageId, comment, user_id: userId })
      : this.api.thumbsDownFeedback({ conversation_id: conversationId, message_id: messageId, comment, user_id: userId })

    request$
      .pipe(catchError((err) => {
        const errorMsg = extractErrorMessage(err, 'Falha ao enviar feedback.')
        this.feedbackStateByMessageId.update((curr) => ({
          ...curr,
          [msg.id]: { ...(curr[msg.id] || {}), rating, submitting: false, submitted: false, error: errorMsg }
        }))
        return of(null as FeedbackQuickResponse | null)
      }))
      .subscribe((resp) => {
        if (!resp) return
        this.feedbackStateByMessageId.update((curr) => ({
          ...curr,
          [msg.id]: {
            ...(curr[msg.id] || {}),
            rating,
            submitting: false,
            submitted: true,
            error: '',
            serverMessage: resp.message || 'Feedback enviado.',
            commentOpen: false
          }
        }))
      })
  }

  private async ensureConversationId(
    forceCreate = false,
    navigateImmediately = true
  ): Promise<string | null> {
    const current = this.selectedId()
    if (current && !forceCreate) return current
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    try {
      const response = await firstValueFrom(
        this.api.startChat(undefined, undefined, userId).pipe(catchError(() => of(null)))
      )
      const conversationId = response?.conversation_id
      if (!conversationId) return null
      const now = Date.now()
      const meta: ConversationMeta = {
        conversation_id: conversationId,
        title: undefined,
        created_at: now,
        updated_at: now
      }
      this.conversations.update((items) => [meta, ...items])
      this.selectConversation(conversationId)
      if (navigateImmediately) {
        this.pendingConversationRouteId = null
        this.router.navigate(['/conversations', conversationId], { replaceUrl: true })
      } else {
        this.pendingConversationRouteId = conversationId
      }
      return conversationId
    } catch {
      return null
    }
  }

  private startStreaming(conversationId: string, message: string): void {
    this.streamingBuffer = ''
    this.streamingMessageId = createConversationViewId()
    this.streamingConversationId = conversationId
    this.appendMessage({
      id: this.streamingMessageId,
      role: 'assistant',
      text: '',
      timestamp: Date.now(),
      streaming: true
    })
    this.queueScroll()
    this.stream.start({
      conversationId,
      text: message,
      role: this.selectedRole(),
      priority: this.selectedPriority()
    })
  }

  private sendClassic(conversationId: string, message: string): void {
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    this.api.sendChatMessage(conversationId, message, this.selectedRole(), this.selectedPriority(), undefined, userId)
      .pipe(catchError(() => of(null)))
      .subscribe((resp) => {
        const latencyMs = this.consumeResponseLatency()
        if (!resp) {
          this.appendMessage({
            id: createConversationViewId(),
            role: 'assistant',
            text: 'Falha ao enviar mensagem.',
            timestamp: Date.now(),
            error: true
          })
        } else {
          const now = Date.now()
          const cleanText = sanitizeChatText(resp.response)
          const raw = resp as unknown as Record<string, unknown>
          const backendMessageId = typeof raw['message_id'] === 'string'
            ? String(raw['message_id'])
            : (typeof raw['id'] === 'string' ? String(raw['id']) : undefined)
          const localMessageId = createConversationViewId()
          this.appendMessage({
            id: localMessageId,
            backendMessageId,
            role: 'assistant',
            text: cleanText,
            timestamp: now,
            citations: resp.citations || [],
            citation_status: resp.citation_status,
            understanding: resp.understanding,
            confirmation: resp.confirmation ?? resp.understanding?.confirmation,
            agent_state: resp.agent_state,
            latency_ms: latencyMs,
            provider: resp.provider,
            model: resp.model,
            delivery_status: resp.delivery_status,
            failure_classification: resp.failure_classification
          })
          this.updateConversationPreview(conversationId, 'assistant', cleanText, now)
          if (resp.delivery_status === 'pending_study' && resp.study_job) {
            this.startStudyPolling(resp.study_job, localMessageId)
            this.showStudyNotice(resp.study_notice || resp.study_job.placeholder_message || 'Estudando a base para responder com seguranca; isso pode demorar.')
          }
        }
        this.sending.set(false)
        this.flushPendingConversationNavigation(conversationId)
        this.queueScroll()
      })
  }

  private sendAdminCodeQa(conversationId: string, message: string): void {
    this.api.askAutonomyAdminCodeQa({
      question: message,
      limit: 12,
      citation_limit: 8
    })
      .pipe(catchError(() => of(null)))
      .subscribe((resp) => {
        const latencyMs = this.consumeResponseLatency()
        if (!resp) {
          this.appendMessage({
            id: createConversationViewId(),
            role: 'assistant',
            text: 'Falha ao consultar codigo no modo admin.',
            timestamp: Date.now(),
            error: true
          })
        } else {
          const now = Date.now()
          const cleanText = sanitizeChatText(resp.answer)
          this.appendMessage({
            id: createConversationViewId(),
            role: 'assistant',
            text: cleanText,
            timestamp: now,
            citations: resp.citations || [],
            latency_ms: latencyMs,
            provider: 'admin',
            model: 'code-qa'
          })
          this.updateConversationPreview(conversationId, 'assistant', cleanText, now)
        }
        this.sending.set(false)
        this.flushPendingConversationNavigation(conversationId)
        this.queueScroll()
      })
  }

  private handleStreamPartial(chunk: string): void {
    if (!this.streamingMessageId) return
    if (!this.streamingBuffer) {
      this.appendThought('stream', 'Resposta', 'Janus iniciou a geracao da resposta.')
    }
    this.streamingBuffer = sanitizeStreamingText(`${this.streamingBuffer}${chunk}`)
    this.updateMessage(this.streamingMessageId, {
      text: this.streamingBuffer,
      streaming: true
    })
    this.queueScroll()
  }

  private handleStreamDone(done: StreamDone): void {
    const latencyMs = this.consumeResponseLatency()
    const finalText = this.streamingBuffer
    if (this.streamingMessageId) {
      this.updateMessage(this.streamingMessageId, {
        backendMessageId: done.message_id,
        text: finalText,
        streaming: false,
        estimated_wait_seconds: done.estimated_wait_seconds,
        estimated_wait_range_seconds: done.estimated_wait_range_seconds,
        processing_profile: done.processing_profile,
        processing_notice: done.processing_notice || undefined,
        citations: done.citations || [],
        citation_status: done.citation_status,
        understanding: done.understanding,
        confirmation: done.confirmation ?? done.understanding?.confirmation,
        agent_state: done.agent_state,
        latency_ms: latencyMs,
        provider: done.provider,
        model: done.model
      })
      this.updateConversationPreview(done.conversation_id || this.selectedId() || '', 'assistant', finalText, Date.now())
    }
    this.streamingBuffer = ''
    this.streamingMessageId = null
    this.streamingConversationId = null
    this.sending.set(false)
    const modelParts = [done.provider, done.model].filter(Boolean)
    const modelLabel = modelParts.length ? ` (${modelParts.join(' / ')})` : ''
    const citationsCount = done.citations?.length || 0
    if (done.processing_notice) {
      this.appendThought('agent', 'Estimativa', done.processing_notice)
    }
    this.appendThought('stream', 'Resposta concluida', `Streaming finalizado${modelLabel}. Citacoes: ${citationsCount}.`)
    this.queueScroll()
    this.loadConversations()
    this.flushPendingConversationNavigation(done.conversation_id || this.selectedId())
  }

  private handleStreamError(reason: string): void {
    this.consumeResponseLatency()
    const id = this.streamingMessageId || createConversationViewId()
    if (!this.streamingMessageId) {
      this.appendMessage({
        id,
        role: 'assistant',
        text: `Erro no streaming: ${reason}`,
        timestamp: Date.now(),
        error: true
      })
    } else {
      this.updateMessage(id, {
        text: `${this.streamingBuffer}\n\n[Erro no streaming: ${reason}]`,
        streaming: false,
        error: true
      })
    }
    this.streamingBuffer = ''
    this.streamingMessageId = null
    this.streamingConversationId = null
    this.sending.set(false)
    this.appendThought('system', 'Falha no streaming', reason || 'erro desconhecido')
    this.flushPendingConversationNavigation(this.selectedId())
  }

  private flushPendingConversationNavigation(targetId?: string | null): void {
    const pendingId = this.pendingConversationRouteId
    if (!pendingId) return
    const nextId = targetId || pendingId
    if (!nextId || pendingId !== nextId) return
    this.pendingConversationRouteId = null
    this.router.navigate(['/conversations', nextId], { replaceUrl: true })
  }

  private appendMessage(message: ChatMessageView): void {
    this.messages.update((items) => [...items, message])
  }

  private updateMessage(id: string, patch: Partial<ChatMessageView>): void {
    this.messages.update((items) => {
      const idx = items.findIndex((msg) => msg.id === id)
      if (idx < 0) return items
      const next = items.slice()
      next[idx] = { ...next[idx], ...patch }
      return next
    })
  }

  private updateConversationPreview(conversationId: string, role: string, text: string, timestamp: number): void {
    if (!conversationId) return
    this.conversations.update((items) => items.map((conv) => {
      if (conv.conversation_id !== conversationId) return conv
      return {
        ...conv,
        updated_at: timestamp,
        last_message: {
          role,
          text,
          timestamp
        }
      }
    }))
  }

  private mapMessage(msg: ChatMessage): ChatMessageView {
    const raw = msg as unknown as Record<string, unknown>
    const latencyMsRaw = Number(raw['latency_ms'])
    const backendMessageId = typeof raw['message_id'] === 'string'
      ? String(raw['message_id'])
      : (typeof raw['id'] === 'string' ? String(raw['id']) : undefined)
    return {
      id: createConversationViewId(),
      backendMessageId,
      role: (msg.role as ChatRole) || 'assistant',
      text: sanitizeChatText(msg.text),
      timestamp: msg.timestamp,
      citations: msg.citations || [],
      citation_status: (raw['citation_status'] as CitationStatus | undefined),
      understanding: msg.understanding,
      confirmation: (raw['confirmation'] as ChatConfirmationState | undefined) ?? msg.understanding?.confirmation,
      agent_state: (raw['agent_state'] as ChatAgentState | undefined),
      latency_ms: Number.isFinite(latencyMsRaw) && latencyMsRaw > 0 ? latencyMsRaw : undefined,
      provider: typeof raw['provider'] === 'string' ? String(raw['provider']) : undefined,
      model: typeof raw['model'] === 'string' ? String(raw['model']) : undefined,
      delivery_status: typeof raw['delivery_status'] === 'string' ? String(raw['delivery_status']) : undefined,
      failure_classification: typeof raw['failure_classification'] === 'string' ? String(raw['failure_classification']) : undefined
    }
  }

  private reconcileResolvedPendingActions(messages: ChatMessageView[]): ChatMessageView[] {
    const resolved = new Map<number, PendingActionResolution>()

    for (const msg of messages) {
      if (msg.role !== 'system') continue
      const match = ConversationsComponent.PENDING_ACTION_RESOLUTION_RE.exec(msg.text || '')
      if (!match) continue
      const actionId = Number(match[1])
      const status = match[2]?.toLowerCase() === 'aprovada' ? 'approved' : 'rejected'
      if (Number.isFinite(actionId)) {
        resolved.set(actionId, status)
      }
    }

    if (!resolved.size) return messages

    return messages.map((msg) => {
      if (msg.role !== 'assistant') return msg
      const confirmation = msg.confirmation || msg.understanding?.confirmation
      const actionId = confirmation?.pending_action_id
      if (typeof actionId !== 'number') return msg

      const resolution = resolved.get(actionId)
      if (!resolution) return msg

      const nextConfirmation: ChatConfirmationState = {
        ...(confirmation || { required: true }),
        required: false,
        status: resolution,
      }
      delete nextConfirmation.approve_endpoint
      delete nextConfirmation.reject_endpoint

      const nextUnderstanding = msg.understanding
        ? {
            ...msg.understanding,
            requires_confirmation: false,
            confirmation: {
              ...(msg.understanding.confirmation || nextConfirmation),
              required: false,
              status: resolution,
            },
          }
        : msg.understanding

      if (nextUnderstanding?.confirmation) {
        delete nextUnderstanding.confirmation.approve_endpoint
        delete nextUnderstanding.confirmation.reject_endpoint
      }

      return {
        ...msg,
        confirmation: nextConfirmation,
        understanding: nextUnderstanding,
        agent_state: {
          ...(msg.agent_state || { state: 'completed' }),
          state: 'completed',
          requires_confirmation: false,
          reason: resolution,
        },
      }
    })
  }

  private showStudyNotice(message: string): void {
    this.autonomyNotice.set({ kind: 'info', message, visible: true })
  }

  private startStudyPolling(job: ChatStudyJobRef, localMessageId: string): void {
    const jobId = String(job.job_id || '')
    if (!jobId) return
    const existing = this.studyPollTimers.get(jobId)
    if (existing) clearTimeout(existing)

    this.api.getChatStudyJob(jobId)
      .pipe(catchError(() => of(null)))
      .subscribe((resp) => {
        if (!resp) {
          this.scheduleStudyPoll(jobId, localMessageId, 2500)
          return
        }
        this.applyStudyJobUpdate(localMessageId, resp)
      })
  }

  private scheduleStudyPoll(jobId: string, localMessageId: string, delayMs: number): void {
    const timer = setTimeout(() => this.startStudyPolling({
      job_id: jobId,
      status: 'running',
      poll_url: '',
      conversation_id: this.selectedId() || ''
    }, localMessageId), delayMs)
    this.studyPollTimers.set(jobId, timer)
  }

  private applyStudyJobUpdate(localMessageId: string, job: ChatStudyJobResponse): void {
    const jobId = String(job.job_id || '')
    if (!jobId) return
    if (job.status === 'completed' && job.final_response) {
      const finalResponse = job.final_response
      const finalText = sanitizeChatText(finalResponse.response)
      this.updateMessage(localMessageId, {
        backendMessageId: finalResponse.message_id,
        text: finalText,
        citations: finalResponse.citations || [],
        citation_status: finalResponse.citation_status,
        understanding: finalResponse.understanding,
        confirmation: finalResponse.confirmation ?? finalResponse.understanding?.confirmation,
        agent_state: finalResponse.agent_state,
        provider: finalResponse.provider,
        model: finalResponse.model,
        delivery_status: finalResponse.delivery_status,
        failure_classification: finalResponse.failure_classification
      })
      this.updateConversationPreview(job.conversation_id, 'assistant', finalText, Date.now())
      this.studyPollTimers.delete(jobId)
      this.autonomyNotice.set(null)
      this.queueScroll()
      return
    }
    if (job.status === 'failed') {
      this.updateMessage(localMessageId, {
        text: job.error || 'Falha ao concluir o estudo automatico dessa resposta.',
        error: true,
        delivery_status: 'failed',
        failure_classification: job.failure_classification
      })
      this.studyPollTimers.delete(jobId)
      return
    }
    if (job.placeholder_message) {
      this.updateMessage(localMessageId, {
        text: sanitizeChatText(job.placeholder_message),
        delivery_status: 'pending_study',
        failure_classification: job.failure_classification
      })
    }
    this.scheduleStudyPoll(jobId, localMessageId, 2500)
  }

  private queueScroll(): void {
    if (this.scrollQueued) return
    this.scrollQueued = true
    requestAnimationFrame(() => {
      this.scrollQueued = false
      this.scrollToBottom()
    })
  }

  private scrollToBottom(): void {
    const el = this.messageList?.nativeElement
    if (!el) return
    el.scrollTop = el.scrollHeight
  }

  thoughtIcon(item: ThoughtStreamItem): string {
    if (item.kind === 'agent') return 'smart_toy'
    if (item.kind === 'stream') return 'bolt'
    return 'info'
  }

  private handleStreamStatus(status: string): void {
    const previous = this.streamStatus()
    this.streamStatus.set(status)
    if (status === previous) return
    if (status === 'connecting') this.appendThought('stream', 'Conexao', 'Conectando ao stream de resposta...')
    if (status === 'retrying') this.appendThought('system', 'Reconexao', 'Tentando restabelecer o stream...')
    if (status === 'open') this.appendThought('stream', 'Conectado', 'Canal SSE ativo e pronto.')
    if (status === 'error') this.appendThought('system', 'Erro de stream', 'Falha de conexao com o stream.')
  }

  private appendThought(kind: ThoughtKind, title: string, text: string, timestamp?: number): void {
    const safeTitleRaw = sanitizeDiagnosticText(title, 'Evento').slice(0, 120)
    const safeTitle = safeTitleRaw.toLowerCase() === 'unknown' ? 'Agente' : safeTitleRaw
    const safeText = sanitizeDiagnosticText(text, 'Evento tecnico recebido')
    const item: ThoughtStreamItem = {
      id: createConversationViewId(),
      kind,
      title: safeTitle || 'Evento',
      text: safeText,
      timestamp: coerceDateInputToMs(timestamp) || Date.now()
    }
    this.thoughtStream.update((items) => [item, ...items].slice(0, 40))
  }

  messageAgentState(msg: ChatMessageView): string {
    const explicit = String(msg.agent_state?.state || '').trim()
    if (explicit) return explicit
    if (msg.streaming) return 'streaming_response'
    const confirmation = this.messageConfirmation(msg)
    if (confirmation?.required && typeof confirmation.pending_action_id === 'number') return 'waiting_confirmation'
    if (msg.understanding?.low_confidence) return 'low_confidence'
    return ''
  }

  messageConfirmation(msg: ChatMessageView): ChatConfirmationState | null {
    const conf = msg.confirmation || msg.understanding?.confirmation
    if (!conf) return null
    const hasPendingAction = typeof conf.pending_action_id === 'number'
    const hasEndpoints = typeof conf.approve_endpoint === 'string' && typeof conf.reject_endpoint === 'string'
    if (!hasPendingAction && !hasEndpoints) return null
    if (conf.required === false && !hasPendingAction && !hasEndpoints) return null
    return conf
  }

  messageRiskSummary(msg: ChatMessageView): string {
    const risk = msg.understanding?.risk
    if (risk?.summary) return String(risk.summary)
    const reason = this.messageConfirmation(msg)?.reason
    if (reason === 'high_risk') return 'Ação classificada como alto risco; confirmação obrigatória.'
    if (reason === 'low_confidence') return 'Baixa confiança para executar ação; confirme antes de prosseguir.'
    return 'Ação requer confirmação antes de prosseguir.'
  }

  citationStatusLabel(status?: CitationStatus): string {
    const s = String(status?.status || '')
    if (s === 'present') return `Fontes: ${status?.count ?? 0}`
    if (s === 'missing_required') return 'Sem citação rastreável (obrigatória)'
    if (s === 'retrieval_failed') return 'Falha ao recuperar citações'
    return 'Sem citação'
  }

  citationStatusVariant(status?: CitationStatus): 'success' | 'warning' | 'error' | 'neutral' {
    const s = String(status?.status || '')
    if (s === 'present') return 'success'
    if (s === 'missing_required') return 'warning'
    if (s === 'retrieval_failed') return 'error'
    return 'neutral'
  }

  isPendingActionBusy(actionId?: number): boolean {
    if (typeof actionId !== 'number') return false
    return Boolean(this.pendingActionLoading()[actionId])
  }

  approvePendingActionForMessage(msg: ChatMessageView): void {
    const conf = this.messageConfirmation(msg)
    const actionId = conf?.pending_action_id
    if (typeof actionId !== 'number') return
    this.setPendingActionBusy(actionId, true)
    const action: PendingAction = { status: 'pending', source: 'sql', action_id: actionId }
    this.api.approvePendingAction(action)
      .pipe(catchError(() => of(null)))
      .subscribe((resp) => {
        this.setPendingActionBusy(actionId, false)
        if (!resp) {
          this.updateMessage(msg.id, { error: true, text: `${msg.text}\n\n[Falha ao aprovar ação pendente]` })
          return
        }
        this.updateMessage(msg.id, {
          confirmation: { ...(conf || { required: true }), required: false, pending_action_id: actionId, reason: conf?.reason, status: 'approved' },
          agent_state: { state: 'completed', reason: 'approved' }
        })
        this.appendMessage({
          id: createConversationViewId(),
          role: 'system',
          text: `Ação pendente #${actionId} aprovada. ${resp.message || ''}`.trim(),
          timestamp: Date.now()
        })
      })
  }

  rejectPendingActionForMessage(msg: ChatMessageView): void {
    const conf = this.messageConfirmation(msg)
    const actionId = conf?.pending_action_id
    if (typeof actionId !== 'number') return
    this.setPendingActionBusy(actionId, true)
    const action: PendingAction = { status: 'pending', source: 'sql', action_id: actionId }
    this.api.rejectPendingAction(action)
      .pipe(catchError(() => of(null)))
      .subscribe((resp) => {
        this.setPendingActionBusy(actionId, false)
        if (!resp) {
          this.updateMessage(msg.id, { error: true, text: `${msg.text}\n\n[Falha ao rejeitar ação pendente]` })
          return
        }
        this.updateMessage(msg.id, {
          confirmation: { ...(conf || { required: true }), required: false, pending_action_id: actionId, reason: conf?.reason, status: 'rejected' },
          agent_state: { state: 'completed', reason: 'rejected' }
        })
        this.appendMessage({
          id: createConversationViewId(),
          role: 'system',
          text: `Ação pendente #${actionId} rejeitada. ${resp.message || ''}`.trim(),
          timestamp: Date.now()
        })
      })
  }

  private setPendingActionBusy(actionId: number, busy: boolean): void {
    this.pendingActionLoading.update((curr) => {
      const next = { ...curr }
      if (busy) next[actionId] = true
      else delete next[actionId]
      return next
    })
  }

  private restoreAdvancedModePreference(): void {
    try {
      const saved = localStorage.getItem(this.advancedModeStorageKey)
      if (saved === '1') this.showAdvanced.set(true)
      if (saved === '0') this.showAdvanced.set(false)
    } catch {
      this.showAdvanced.set(false)
    }
  }

  private restoreRailTabPreferences(): void {
    try {
      const advanced = localStorage.getItem(this.advancedRailTabStorageKey)
      if (advanced === 'insights' || advanced === 'cliente' || advanced === 'autonomia') {
        this.advancedRailTab.set(advanced)
      }
      const customer = localStorage.getItem(this.customerTabStorageKey)
      if (customer === 'docs' || customer === 'memoria' || customer === 'rag') {
        this.customerTab.set(customer)
      }
    } catch {
      this.advancedRailTab.set('cliente')
      this.customerTab.set('docs')
    }
  }

  private persistAdvancedModePreference(enabled: boolean): void {
    try {
      localStorage.setItem(this.advancedModeStorageKey, enabled ? '1' : '0')
    } catch {
      // no-op
    }
  }

  private persistRailTabPreference(key: string, value: string): void {
    try {
      localStorage.setItem(key, value)
    } catch {
      // no-op
    }
  }

  private consumeResponseLatency(): number | undefined {
    if (!this.responseStartedAt) return undefined
    const latencyMs = Math.max(0, Date.now() - this.responseStartedAt)
    this.responseStartedAt = null
    return latencyMs
  }

  private loadAutonomyContext(): void {
    this.autonomyLoading.set(true)
    forkJoin({
      status: this.api.getAutonomyStatus().pipe(catchError(() => of(null))),
      goals: this.api.listGoals().pipe(catchError(() => of([] as Goal[]))),
      tools: this.api.getTools().pipe(
        map((resp) => resp.tools || []),
        catchError(() => of([] as Tool[]))
      )
    }).subscribe((result) => {
      this.autonomyStatus.set(result.status)
      this.autonomyGoals.set(result.goals)
      this.autonomyTools.set(result.tools)
      this.autonomyLoading.set(false)
    })
  }
}
