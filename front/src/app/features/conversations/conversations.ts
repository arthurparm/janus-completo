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
import { JanusApiService, ChatMessage, ChatUnderstanding, ConversationMeta, DocListItem, MemoryItem, Citation } from '../../services/janus-api.service'
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
  streaming?: boolean
  error?: boolean
}

interface RoleOption {
  value: string
  label: string
}

interface PriorityOption {
  value: string
  label: string
}

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
  private api = inject(JanusApiService)
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
  readonly memory = signal<MemoryItem[]>([])

  readonly selectedId = signal<string | null>(null)
  readonly streamStatus = signal('idle')
  readonly streamTyping = signal(false)
  readonly selectedRole = signal('orchestrator')
  readonly selectedPriority = signal('fast_and_cheap')
  readonly streamingEnabled = signal(true)

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

  readonly displayName = computed(() => {
    const user = this.user()
    return user?.display_name || user?.username || user?.email || 'Operador'
  })

  readonly filteredConversations = computed(() => {
    const term = this.search().trim().toLowerCase()
    const items = this.conversations()
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
    if (status === 'open') return { label: 'Conectado', variant: 'info' as const }
    return { label: 'Idle', variant: 'neutral' as const }
  })

  private streamingBuffer = ''
  private streamingMessageId: string | null = null
  private scrollQueued = false

  constructor() {
    this.loadConversations()

    this.route.paramMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const id = params.get('conversationId')
        this.selectConversation(id)
      })

    this.stream.status()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((status) => this.streamStatus.set(status))

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

  readonly traceSteps = signal<any[]>([])
  readonly showTrace = signal(false)

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
    this.memory.set([])
    this.traceSteps.set([]) // Clear trace
    this.stream.stop()
    this.sending.set(false)
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
      this.memory.set(result.memory)
      this.contextLoading.set(false)
    })
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
          this.appendMessage({
            id: this.createId(),
            role: 'assistant',
            text: resp.response,
            timestamp: now,
            citations: resp.citations || [],
            understanding: resp.understanding
          })
          this.updateConversationPreview(conversationId, 'assistant', resp.response, now)
        }
        this.sending.set(false)
        this.queueScroll()
      })
  }

  private handleStreamPartial(chunk: string): void {
    if (!this.streamingMessageId) return
    this.streamingBuffer += chunk
    this.updateMessage(this.streamingMessageId, {
      text: this.streamingBuffer,
      streaming: true
    })
    this.queueScroll()
  }

  private handleStreamDone(done: StreamDone): void {
    if (this.streamingMessageId) {
      this.updateMessage(this.streamingMessageId, {
        streaming: false,
        citations: done.citations || [],
        understanding: done.understanding
      })
      this.updateConversationPreview(done.conversation_id || this.selectedId() || '', 'assistant', this.streamingBuffer, Date.now())
    }
    this.streamingBuffer = ''
    this.streamingMessageId = null
    this.sending.set(false)
    this.queueScroll()
    this.loadConversations()
  }

  private handleStreamError(reason: string): void {
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
    return {
      id: this.createId(),
      role: (msg.role as ChatRole) || 'assistant',
      text: msg.text,
      timestamp: msg.timestamp,
      citations: msg.citations || [],
      understanding: msg.understanding
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
}
