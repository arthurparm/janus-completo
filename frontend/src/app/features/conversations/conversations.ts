import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, ViewChild, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormControl, ReactiveFormsModule } from '@angular/forms'
import { ActivatedRoute, Router } from '@angular/router'
import { firstValueFrom, of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'

import { AgentEventsService } from '../../core/services/agent-events.service'
import { ChatStreamService, StreamDone } from '../../services/chat-stream.service'
import { BackendApiService } from '../../services/backend-api.service'
import {
  ChatAgentState,
  ChatConfirmationState,
  ChatMessage,
  ChatStudyJobRef,
  ChatStudyJobResponse,
  ChatUnderstanding,
  ConversationMeta,
  CitationStatus,
  FeedbackQuickResponse,
  PendingAction,
  Citation
} from '../../models'
import { Header } from '../../core/layout/header/header'
import { UiButtonComponent } from '../../shared/components/ui/button/button.component'
import { UiBadgeComponent } from '../../shared/components/ui/ui-badge/ui-badge.component'
import { JarvisAvatarComponent } from '../../shared/components/jarvis-avatar/jarvis-avatar.component'
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component'
import { MarkdownPipe } from '../../shared/pipes/markdown.pipe'
import { parseAdminCodeQaCommand } from './admin-code-qa.util'
import { ConversationStateFacade } from './conversations-state.facade'
import { ConversationsAutonomyService } from './conversations-autonomy.service'
import { ConversationsContextService } from './conversations-context.service'
import { ConversationsDocsService } from './conversations-docs.service'
import { ConversationsMemoryService } from './conversations-memory.service'
import { ConversationsNoticeService } from './conversations-notice.service'
import { ConversationsRagService } from './conversations-rag.service'
import type {
  AdvancedRailTab,
  ChatMessageView,
  ChatRole,
  CustomerTab,
  FeedbackUiState,
  PendingActionResolution,
  PriorityOption,
  RagResultViewTab,
  RoleOption,
  TabGroup,
  ThoughtKind,
  ThoughtStreamItem
} from './conversations.types'
import {
  coerceDateInputToMs,
  cognitiveStatusText,
  conversationUpdatedAt,
  createConversationViewId,
  extractErrorMessage,
  sanitizeChatText,
  sanitizeDiagnosticText,
  sanitizeStreamingText
} from './conversations.utils'

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
  private route = inject(ActivatedRoute)
  private router = inject(Router)
  private destroyRef = inject(DestroyRef)
  private eventsService = inject(AgentEventsService)
  private stream = inject(ChatStreamService)
  private state = inject(ConversationStateFacade)
  private notices = inject(ConversationsNoticeService)
  private context = inject(ConversationsContextService)

  readonly docsFlow = inject(ConversationsDocsService)
  readonly memoryFlow = inject(ConversationsMemoryService)
  readonly ragFlow = inject(ConversationsRagService)
  readonly autonomyFlow = inject(ConversationsAutonomyService)

  @ViewChild('messageList') messageList?: ElementRef<HTMLDivElement>

  readonly prompt = new FormControl('', { nonNullable: true })
  readonly listLoading = this.state.listLoading
  readonly historyLoading = this.state.historyLoading
  readonly contextLoading = this.state.contextLoading
  readonly sending = this.state.sending
  readonly error = this.state.error
  readonly search = this.state.search

  readonly conversations = this.state.conversations
  readonly messages = this.state.messages
  readonly events = this.state.events
  readonly docs = this.state.docs
  readonly memoryUser = this.state.memoryUser
  readonly docSearchResults = this.state.docSearchResults
  readonly generativeMemoryResults = this.state.generativeMemoryResults
  readonly ragResult = this.state.ragResult
  readonly docsNotice = this.state.docsNotice
  readonly memoryNotice = this.state.memoryNotice
  readonly ragNotice = this.state.ragNotice
  readonly autonomyNotice = this.state.autonomyNotice

  readonly selectedId = this.state.selectedId
  readonly streamStatus = this.state.streamStatus
  readonly streamTyping = this.state.streamTyping
  readonly selectedRole = this.state.selectedRole
  readonly selectedPriority = this.state.selectedPriority
  readonly streamingEnabled = this.state.streamingEnabled
  readonly latestCognitiveState = this.state.latestCognitiveState
  readonly latestToolStatus = this.state.latestToolStatus
  readonly pendingActionLoading = this.state.pendingActionLoading
  readonly showAdvanced = this.state.showAdvanced
  readonly advancedRailTab = this.state.advancedRailTab
  readonly customerTab = this.state.customerTab
  readonly copiedCitation = this.state.copiedCitation
  readonly autonomyLoading = this.state.autonomyLoading
  readonly autonomySaving = this.state.autonomySaving
  readonly autonomyStatus = this.state.autonomyStatus
  readonly autonomyGoals = this.state.autonomyGoals
  readonly autonomyTools = this.state.autonomyTools
  readonly autonomyError = this.state.autonomyError
  readonly goalCreateTitle = this.state.goalCreateTitle
  readonly goalCreateDescription = this.state.goalCreateDescription
  readonly goalCreateLoading = this.state.goalCreateLoading
  readonly goalCreateError = this.state.goalCreateError

  readonly docUploadInFlight = this.state.docUploadInFlight
  readonly docUploadProgress = this.state.docUploadProgress
  readonly docUploadError = this.state.docUploadError
  readonly docLinkUrl = this.state.docLinkUrl
  readonly docLinkLoading = this.state.docLinkLoading
  readonly docLinkError = this.state.docLinkError
  readonly docSearchQuery = this.state.docSearchQuery
  readonly docSearchLoading = this.state.docSearchLoading
  readonly docSearchError = this.state.docSearchError
  readonly deletingDocIds = this.state.deletingDocIds

  readonly memoryDraft = this.state.memoryDraft
  readonly memoryImportance = this.state.memoryImportance
  readonly memoryType = this.state.memoryType
  readonly memoryAddLoading = this.state.memoryAddLoading
  readonly memoryAddError = this.state.memoryAddError
  readonly memorySearchQuery = this.state.memorySearchQuery
  readonly memorySearchLimit = this.state.memorySearchLimit
  readonly memorySearchLoading = this.state.memorySearchLoading
  readonly memorySearchError = this.state.memorySearchError

  readonly ragMode = this.state.ragMode
  readonly ragQuery = this.state.ragQuery
  readonly ragLoading = this.state.ragLoading
  readonly ragError = this.state.ragError
  readonly ragResultViewTab = this.state.ragResultViewTab

  readonly feedbackStateByMessageId = this.state.feedbackStateByMessageId
  readonly feedbackCommentDraftByMessageId = this.state.feedbackCommentDraftByMessageId

  readonly selectedUploadFile = this.state.selectedUploadFile
  readonly traceSteps = this.state.traceSteps
  readonly showTrace = this.state.showTrace
  readonly thoughtStream = this.state.thoughtStream
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

  readonly user = this.state.user
  readonly isAdmin = this.state.isAdmin
  readonly displayName = this.state.displayName
  readonly filteredConversations = this.state.filteredConversations
  readonly selectedConversation = this.state.selectedConversation
  readonly isSimpleMode = this.state.isSimpleMode
  readonly latestAssistantMessage = this.state.latestAssistantMessage
  readonly conversationMemory = this.state.conversationMemory
  readonly userMemory = this.state.userMemory
  readonly autonomyActiveGoals = this.state.autonomyActiveGoals
  readonly autonomyEnabledTools = this.state.autonomyEnabledTools
  readonly hasConversationSelected = this.state.hasConversationSelected
  readonly selectedTitle = this.state.selectedTitle
  readonly avatarState = this.state.avatarState
  readonly streamBadge = this.state.streamBadge

  private streamingBuffer = ''
  private streamingMessageId: string | null = null
  private streamingConversationId: string | null = null
  private pendingConversationRouteId: string | null = null
  private scrollQueued = false
  private responseStartedAt: number | null = null
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
      this.context.loadContext(id)
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
    this.api.chat.getConversationTrace(conversationId).pipe(
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
      this.context.loadContext(id)
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
    this.notices.clear('docs')
    this.notices.clear('memory')
    this.notices.clear('rag')
    this.notices.clear('autonomy')
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
    this.context.loadContext(id)
    if (this.showTrace()) {
      this.loadTrace(id)
    }
  }

  private loadConversations(): void {
    this.listLoading.set(true)
    this.api.chat.listConversations({ limit: 60 })
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
    this.api.chat.getChatHistoryPaginated(conversationId, { limit: 80, offset: 0 })
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
    const userId = this.context.userIdString()
    const comment = this.feedbackCommentDraft(msg.id).trim() || undefined

    this.feedbackStateByMessageId.update((curr) => ({
      ...curr,
      [msg.id]: { ...(curr[msg.id] || {}), rating, submitting: true, error: '', serverMessage: '' }
    }))

    const request$ = rating === 'positive'
      ? this.api.feedback.thumbsUpFeedback({ conversation_id: conversationId, message_id: messageId, comment, user_id: userId })
      : this.api.feedback.thumbsDownFeedback({ conversation_id: conversationId, message_id: messageId, comment, user_id: userId })

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
    try {
      const response = await firstValueFrom(
        this.api.chat.startChat().pipe(catchError(() => of(null)))
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
    this.api.chat.sendChatMessage(conversationId, message, this.selectedRole(), this.selectedPriority())
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
    this.api.autonomy.askAutonomyAdminCodeQa({
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

    this.api.chat.getChatStudyJob(jobId)
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
    const isLowConfidence = conf.reason === 'low_confidence' || msg.understanding?.low_confidence === true
    if (!hasPendingAction && !hasEndpoints && !isLowConfidence) return null
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
    this.api.observability.approvePendingAction(action)
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
    this.api.observability.rejectPendingAction(action)
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
}
