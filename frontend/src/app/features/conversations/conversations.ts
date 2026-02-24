import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, ViewChild, computed, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormControl, ReactiveFormsModule } from '@angular/forms'
import { ActivatedRoute, Router } from '@angular/router'
import { firstValueFrom, forkJoin, of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'

import { AuthService } from '../../core/auth/auth.service'
import { AgentEvent, AgentEventsService } from '../../core/services/agent-events.service'
import { ChatStreamService, StreamDone } from '../../services/chat-stream.service'
import {
  BackendApiService,
  ChatMessage,
  ChatUnderstanding,
  ConversationMeta,
  DocListItem,
  MemoryItem,
  Citation,
  AutonomyStatusResponse,
  Goal,
  Tool
} from '../../services/backend-api.service'
import { Header } from '../../core/layout/header/header'
import { UiButtonComponent } from '../../shared/components/ui/button/button.component'
import { UiBadgeComponent } from '../../shared/components/ui/ui-badge/ui-badge.component'
import { JarvisAvatarComponent } from '../../shared/components/jarvis-avatar/jarvis-avatar.component'
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component'
import { MarkdownPipe } from '../../shared/pipes/markdown.pipe'

type ChatRole = 'user' | 'assistant' | 'system' | 'event'

interface ChatMessageView {
  id: string
  role: ChatRole
  text: string
  timestamp: number
  citations?: Citation[]
  understanding?: ChatUnderstanding
  latency_ms?: number
  provider?: string
  model?: string
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

interface RoleOption {
  value: string
  label: string
}

interface PriorityOption {
  value: string
  label: string
}

type GoalStatus = 'pending' | 'in_progress' | 'completed' | 'failed'

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

  readonly selectedId = signal<string | null>(null)
  readonly streamStatus = signal('idle')
  readonly streamTyping = signal(false)
  readonly selectedRole = signal('orchestrator')
  readonly selectedPriority = signal('fast_and_cheap')
  readonly streamingEnabled = signal(true)
  readonly showAdvanced = signal(false)
  readonly copiedCitation = signal('')
  readonly autonomyLoading = signal(false)
  readonly autonomySaving = signal(false)
  readonly autonomyStatus = signal<AutonomyStatusResponse | null>(null)
  readonly autonomyGoals = signal<Goal[]>([])
  readonly autonomyTools = signal<Tool[]>([])
  readonly autonomyError = signal('')

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
      .sort((a, b) => this.conversationUpdatedAt(b) - this.conversationUpdatedAt(a))
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
    return items.filter((item) => this.isConversationMemory(item, conversationId))
  })
  readonly userMemory = computed(() => this.memoryUser())
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
  private scrollQueued = false
  private responseStartedAt: number | null = null
  readonly quickPrompts = [
    'Resuma esta conversa em 5 pontos.',
    'Quais sao os proximos passos recomendados para este tema?',
    'Me explique de forma simples, sem jargao tecnico.'
  ]

  constructor() {
    this.restoreAdvancedModePreference()
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

    this.eventsService.events$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((event) => {
        this.events.update((items) => [event, ...items].slice(0, 24))
        this.appendThought('agent', event.agent_role || 'agent', event.content || 'evento sem descricao', event.timestamp)
      })

    this.destroyRef.onDestroy(() => {
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

    const conversationId = await this.ensureConversationId()
    if (!conversationId) {
      this.error.set('Falha ao criar conversa.')
      this.sending.set(false)
      return
    }

    const now = Date.now()
    this.appendMessage({
      id: this.createId(),
      role: 'user',
      text: message,
      timestamp: now
    })
    this.updateConversationPreview(conversationId, 'user', message, now)
    this.prompt.setValue('')
    this.queueScroll()
    this.responseStartedAt = Date.now()

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
    const text = this.sanitizeChatText(conv.last_message?.text || '')
    if (!text) return 'Sem mensagens ainda'
    return text.length > 110 ? `${text.slice(0, 110)}...` : text
  }

  conversationLastActivity(conv: ConversationMeta): string {
    const ts = this.conversationUpdatedAt(conv)
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

  refreshAutonomy(): void {
    this.loadAutonomyContext()
  }

  toggleAutonomyLoop(): void {
    if (this.autonomySaving()) return
    this.autonomySaving.set(true)
    this.autonomyError.set('')
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
        this.autonomyError.set(this.extractErrorMessage(err, 'Falha ao atualizar autonomia.'))
        return of(null)
      }))
      .subscribe(() => {
        this.autonomySaving.set(false)
        this.loadAutonomyContext()
      })
  }

  markGoalStatus(goal: Goal, status: GoalStatus): void {
    if (!goal?.id || this.autonomySaving()) return
    this.autonomySaving.set(true)
    this.autonomyError.set('')
    this.api.updateGoalStatus(goal.id, status)
      .pipe(catchError((err) => {
        this.autonomyError.set(this.extractErrorMessage(err, 'Falha ao atualizar meta.'))
        return of(null)
      }))
      .subscribe((updated) => {
        if (updated) {
          this.autonomyGoals.update((items) => items.map((item) => item.id === updated.id ? updated : item))
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
    this.selectedId.set(id)
    this.messages.set([])
    this.events.set([])
    this.docs.set([])
    this.memoryUser.set([])
    this.traceSteps.set([]) // Clear trace
    this.thoughtStream.set([])
    this.copiedCitation.set('')
    this.stream.stop()
    this.sending.set(false)
    this.responseStartedAt = null
    this.streamingBuffer = ''
    this.streamingMessageId = null

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
        this.messages.set(items.map((msg) => this.mapMessage(msg)))
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
      memory: this.api.getMemoryTimeline({ limit: 6, user_id: userId }).pipe(
        catchError(() => of([] as MemoryItem[]))
      )
    }).subscribe((result) => {
      this.docs.set(result.docs)
      this.memoryUser.set(result.memory)
      this.contextLoading.set(false)
    })
    this.loadAutonomyContext()
  }

  private async ensureConversationId(forceCreate = false): Promise<string | null> {
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
      this.selectedId.set(conversationId)
      this.router.navigate(['/conversations', conversationId], { replaceUrl: true })
      return conversationId
    } catch {
      return null
    }
  }

  private startStreaming(conversationId: string, message: string): void {
    this.streamingBuffer = ''
    this.streamingMessageId = this.createId()
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
            id: this.createId(),
            role: 'assistant',
            text: 'Falha ao enviar mensagem.',
            timestamp: Date.now(),
            error: true
          })
        } else {
          const now = Date.now()
          const cleanText = this.sanitizeChatText(resp.response)
          this.appendMessage({
            id: this.createId(),
            role: 'assistant',
            text: cleanText,
            timestamp: now,
            citations: resp.citations || [],
            understanding: resp.understanding,
            latency_ms: latencyMs,
            provider: resp.provider,
            model: resp.model
          })
          this.updateConversationPreview(conversationId, 'assistant', cleanText, now)
        }
        this.sending.set(false)
        this.queueScroll()
      })
  }

  private handleStreamPartial(chunk: string): void {
    if (!this.streamingMessageId) return
    if (!this.streamingBuffer) {
      this.appendThought('stream', 'Resposta', 'Janus iniciou a geracao da resposta.')
    }
    this.streamingBuffer += this.sanitizeChatText(chunk)
    this.updateMessage(this.streamingMessageId, {
      text: this.streamingBuffer,
      streaming: true
    })
    this.queueScroll()
  }

  private handleStreamDone(done: StreamDone): void {
    const latencyMs = this.consumeResponseLatency()
    if (this.streamingMessageId) {
      this.updateMessage(this.streamingMessageId, {
        streaming: false,
        citations: done.citations || [],
        understanding: done.understanding,
        latency_ms: latencyMs,
        provider: done.provider,
        model: done.model
      })
      this.updateConversationPreview(done.conversation_id || this.selectedId() || '', 'assistant', this.streamingBuffer, Date.now())
    }
    this.streamingBuffer = ''
    this.streamingMessageId = null
    this.sending.set(false)
    const modelParts = [done.provider, done.model].filter(Boolean)
    const modelLabel = modelParts.length ? ` (${modelParts.join(' / ')})` : ''
    const citationsCount = done.citations?.length || 0
    this.appendThought('stream', 'Resposta concluida', `Streaming finalizado${modelLabel}. Citacoes: ${citationsCount}.`)
    this.queueScroll()
    this.loadConversations()
  }

  private handleStreamError(reason: string): void {
    this.consumeResponseLatency()
    const id = this.streamingMessageId || this.createId()
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
    this.sending.set(false)
    this.appendThought('system', 'Falha no streaming', reason || 'erro desconhecido')
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

  private conversationUpdatedAt(conv: ConversationMeta): number {
    const updated = Number(conv.updated_at)
    if (Number.isFinite(updated) && updated > 0) return updated
    const lastTimestamp = Number(conv.last_message?.timestamp)
    if (Number.isFinite(lastTimestamp) && lastTimestamp > 0) return lastTimestamp
    const created = Number(conv.created_at)
    if (Number.isFinite(created) && created > 0) return created
    return 0
  }

  private mapMessage(msg: ChatMessage): ChatMessageView {
    const raw = msg as unknown as Record<string, unknown>
    const latencyMsRaw = Number(raw['latency_ms'])
    return {
      id: this.createId(),
      role: (msg.role as ChatRole) || 'assistant',
      text: this.sanitizeChatText(msg.text),
      timestamp: msg.timestamp,
      citations: msg.citations || [],
      understanding: msg.understanding,
      latency_ms: Number.isFinite(latencyMsRaw) && latencyMsRaw > 0 ? latencyMsRaw : undefined,
      provider: typeof raw['provider'] === 'string' ? String(raw['provider']) : undefined,
      model: typeof raw['model'] === 'string' ? String(raw['model']) : undefined
    }
  }

  private createId(): string {
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
      return crypto.randomUUID()
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`
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
    const item: ThoughtStreamItem = {
      id: this.createId(),
      kind,
      title,
      text,
      timestamp: Number(timestamp || Date.now())
    }
    this.thoughtStream.update((items) => [item, ...items].slice(0, 40))
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

  private persistAdvancedModePreference(enabled: boolean): void {
    try {
      localStorage.setItem(this.advancedModeStorageKey, enabled ? '1' : '0')
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

  private isConversationMemory(item: MemoryItem, conversationId: string): boolean {
    const metadata = item.metadata || {}
    const sessionId = String(metadata.session_id || '')
    const threadId = String(metadata['thread_id'] || '')
    const convoId = String(metadata['conversation_id'] || '')
    const taskId = String(metadata['task_id'] || '')
    const compositeId = String(item.composite_id || '')
    return [sessionId, threadId, convoId, taskId, compositeId].some((value) => value.includes(conversationId))
  }

  private extractErrorMessage(error: unknown, fallback: string): string {
    if (!error || typeof error !== 'object') return fallback
    const maybe = error as { error?: { detail?: string } }
    const detail = maybe.error?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    return fallback
  }

  private sanitizeChatText(value: unknown): string {
    if (value === null || value === undefined) return ''
    if (typeof value === 'string') {
      const cleaned = value.replace(/\[object Object\]/g, '').replace(/\n{3,}/g, '\n\n')
      return cleaned.trim() ? cleaned : ''
    }
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }
}
