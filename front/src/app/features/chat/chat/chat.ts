import {Component, OnInit, inject, ViewChild, ElementRef, ChangeDetectionStrategy, ChangeDetectorRef} from '@angular/core'
import {CommonModule} from '@angular/common'
import {FormsModule} from '@angular/forms'
import {JanusApiService, ChatMessage, ChatHistoryResponse} from '../../../services/janus-api.service'
import { ChatStreamService } from '../../../services/chat-stream.service'
import { UxMetricsService } from '../../../services/ux-metrics.service'
import { NotificationService } from '../../../core/notifications/notification.service'
import { FEATURE_SSE } from '../../../services/api.config'
import { ActivatedRoute, Router, RouterLink } from '@angular/router'

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './chat.html',
  styleUrl: './chat.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ChatComponent implements OnInit {
  private api = inject(JanusApiService)
  private stream = inject(ChatStreamService)
  private ux = inject(UxMetricsService)
  private notify = inject(NotificationService)
  private route = inject(ActivatedRoute)
  private router = inject(Router)

  conversationId: string | null = null
  messages: ChatMessage[] = []
  inputText = ''
  loading = false
  error: string | null = null
  streaming = false
  typingActive = false
  reconnecting = false
  sseEnabled = FEATURE_SSE
  webrtcStatus: string | null = null
  mediaEnabled = false
  localStream: MediaStream | null = null
  remoteStream: MediaStream | null = null
  sidebarOpen = false
  voiceActive = false
  dropZoneActive = false
  modelTemperature = 0.7
  
  @ViewChild('localVideo', { static: false }) localVideo?: ElementRef<HTMLVideoElement>
  @ViewChild('remoteVideo', { static: false }) remoteVideo?: ElementRef<HTMLVideoElement>
  @ViewChild('fileInput', { static: false }) fileInput?: ElementRef<HTMLInputElement>
  @ViewChild('messageInput', { static: false }) messageInput?: ElementRef<HTMLTextAreaElement>
  @ViewChild('messagesContainer', { static: false }) messagesContainer?: ElementRef<HTMLElement>
  
  // Session controls
  // Attachments
  attachments: { doc_id: string; file_name?: string; chunks: number }[] = []
  uploading = false
  uploadProgress = 0
  citationsByIndex: Record<number, any[]> = {}
  attachmentsLoading = false
  attachmentsError: string | null = null

  ngOnInit() {
    const cid = this.route.snapshot.paramMap.get('conversationId')
    if (cid) { this.conversationId = cid; this.loadHistory() } else { this.startChat() }
    this.initMedia()
    this.stream.status().subscribe(st => {
      this.streaming = st === 'streaming' || st === 'open'
      this.reconnecting = st === 'retrying'
    })
    this.stream.typing().subscribe(t => { this.typingActive = !!t })
    this.stream.partials().subscribe(p => {
      // TTFT em primeiro partial
      const anyMsg = this.messages[this.messages.length - 1]
      if (anyMsg && anyMsg.role === 'user' && !this.loading) {
        // no-op
      }
      const last = this.messages[this.messages.length - 1]
      if (last && last.role !== 'user') {
        const merged = { role: 'assistant', content: (last.content || '') + p.text }
        this.messages = [...this.messages.slice(0, -1), merged]
      } else {
        this.messages = [...this.messages, { role: 'assistant', content: p.text }]
      }
    })
    this.stream.done().subscribe((d) => {
      this.ux.record({ outcome: 'success', timestamp: Date.now() })
      this.loading = false; this.streaming = false; this.typingActive = false
      // attach citations to last assistant message
      const idx = this.messages.length - 1
      if (idx >= 0 && d?.citations) {
        this.citationsByIndex[idx] = d.citations as any[]
      }
    })
    this.stream.errors().subscribe(e => { this.error = e.error; this.ux.record({ outcome: 'error', timestamp: Date.now() }) })
  }

  statusLabel(): 'Nova'|'Em andamento'|'Resolvida' {
    const hasMsg = this.messages && this.messages.length > 0
    if (!hasMsg) return 'Nova'
    try {
      const last = this.messages[this.messages.length - 1]
      const ts = last?.timestamp ? Date.parse(String(last.timestamp)) : Date.now()
      const days = (Date.now() - ts) / (1000 * 60 * 60 * 24)
      if (days > 7) return 'Resolvida'
    } catch {}
    return 'Em andamento'
  }

  startChat() {
    this.loading = true
    this.error = null
    this.api.startChat('Janus Chat')
      .subscribe({
        next: (resp) => {
          this.conversationId = resp.conversation_id
          try { this.router.navigate(['/chat', this.conversationId]) } catch {}
          this.loadHistory()
        },
        error: (err) => {
          this.error = 'Falha ao iniciar conversa'
          this.loading = false
          console.error(err)
        }
      })
  }

  initMedia() {
    this.api.initJanus({ serverUrl: 'http://localhost:8088/janus', debug: false })
      .subscribe(s => {
        this.webrtcStatus = s.status
        if (s.status === 'initialized') {
          this.api.attachPlugin('videoroom').subscribe(st => {
            this.webrtcStatus = st.status
          })
          this.api.startLocalMedia()
            .then(stream => {
              this.localStream = stream
              this.mediaEnabled = true
            })
            .catch(() => {
              this.mediaEnabled = false
            })
        }
      })
    this.api.localStream$().subscribe(s => {
      this.localStream = s || null
      const el = this.localVideo?.nativeElement
      if (el) el.srcObject = this.localStream as any
    })
    this.api.remoteStream$().subscribe(s => {
      this.remoteStream = s || null
      const el = this.remoteVideo?.nativeElement
      if (el) el.srcObject = this.remoteStream as any
    })
    this.api.webrtcErrors$().subscribe(e => { this.error = e })
  }

  loadHistory() {
    if (!this.conversationId) { this.loading = false; return }
    this.api.getChatHistory(this.conversationId)
      .subscribe({
        next: (resp: ChatHistoryResponse) => {
          this.messages = resp.messages || []
          this.loading = false
          this.loadAttachments()
        },
        error: (err) => {
          this.error = 'Falha ao carregar histórico'
          this.loading = false
          console.error(err)
        }
      })
  }

  sendMessage() {
    const content = this.inputText?.trim()
    if (!content) return
    if (!this.conversationId) { this.startChat(); return }

    // append user message optimistically
    const userMsg: ChatMessage = { role: 'user', content }
    this.messages = [...this.messages, userMsg]
    this.inputText = ''
    this.loading = true
    this.error = null
    if (this.sseEnabled && typeof window !== 'undefined' && 'EventSource' in window) {
      this.stream.start({ conversationId: this.conversationId, text: content })
    } else {
      this.api.sendChatMessage(this.conversationId, content)
        .subscribe({
          next: (resp) => {
            const assistant = resp.assistant_message || resp.message
            if (assistant) {
              const idx = this.messages.length
              this.messages = [...this.messages, assistant]
              const cits: any[] = (resp as any)?.citations || []
              if (cits && cits.length) this.citationsByIndex[idx] = cits
            } else if (resp.messages && resp.messages.length) {
              this.messages = resp.messages
            }
            this.ux.record({ outcome: 'success', timestamp: Date.now() })
            this.loading = false
          },
          error: (err) => {
            this.error = 'Falha ao enviar mensagem'
            this.ux.record({ outcome: 'error', timestamp: Date.now() })
            this.loading = false
            console.error(err)
          }
        })
    }
  }

  cancelStreaming() {
    this.stream.stop()
    this.streaming = false
    this.typingActive = false
    this.loading = false
    this.ux.record({ outcome: 'cancel', timestamp: Date.now() })
  }

  onEnter(ev: KeyboardEvent) {
    if (!ev.shiftKey) {
      ev.preventDefault()
      if (!this.loading && !this.streaming) this.sendMessage()
    }
  }

  stopMedia() {
    this.api.stopLocalMedia()
    this.mediaEnabled = false
  }

  // Attachments helpers
  onFilesSelected(ev: Event) {
    const input = ev.target as HTMLInputElement
    const files = input?.files
    if (!files || !this.conversationId) return
    const f = files[0]
    this.uploadFile(f)
  }

  onDrop(ev: DragEvent) {
    ev.preventDefault()
    if (!ev.dataTransfer || !ev.dataTransfer.files || !this.conversationId) return
    const f = ev.dataTransfer.files[0]
    this.uploadFile(f)
  }

  allowDrop(ev: DragEvent) { ev.preventDefault() }

  onDropzoneKey(ev: KeyboardEvent) {
    if (ev.key === 'Enter' || ev.key === ' ') {
      ev.preventDefault()
      const el = this.fileInput?.nativeElement
      if (el) el.click()
    }
  }

  uploadFile(file: File) {
    if (!file || !this.conversationId) return
    const allowed = ['text/plain','text/html','application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','image/png','image/jpeg','image/gif']
    const ct = (file.type || '').toLowerCase()
    if (!allowed.some(a => ct.startsWith(a))) { this.error = 'Tipo de arquivo não suportado'; return }
    this.uploading = true
    this.uploadProgress = 0
    this.api.uploadAttachmentWithProgress(this.conversationId, file)
      .subscribe({
        next: (ev) => {
          if (typeof ev.progress === 'number') this.uploadProgress = ev.progress
          if (ev.response) { this.uploading = false; this.uploadProgress = 0; this.loadAttachments() }
        },
        error: () => { this.error = 'Falha no upload'; this.uploading = false; this.notify.notifyError('Falha no upload') }
      })
  }

  loadAttachments() {
    if (!this.conversationId) return
    const id = String(this.conversationId || '')
    if (!id) { return }
    this.attachmentsLoading = true
    this.attachmentsError = null
    this.api.listAttachments(id)
      .subscribe({
        next: (resp) => { this.attachments = (resp.items || []).map(it => ({ doc_id: it.doc_id, file_name: it.file_name, chunks: it.chunks })); this.attachmentsLoading = false },
        error: (err) => {
          this.attachmentsLoading = false
          this.attachmentsError = 'Anexos indisponíveis'
          this.notify.notifyError('Anexos indisponíveis', 'Falha ao consultar anexos')
        }
      })
  }

  deleteAttachment(it: { doc_id: string }) {
    this.api.deleteAttachment(it.doc_id).subscribe({ next: () => { this.loadAttachments() }, error: () => { this.error = 'Falha ao excluir anexo'; this.notify.notifyError('Falha ao excluir anexo') } })
  }

  copyMessage(index: number) {
    const m = this.messages[index]
    if (!m || !m.content) return
    try {
      navigator.clipboard.writeText(m.content)
      this.notify.notifyInfo('Conteúdo copiado')
    } catch {
      this.notify.notifyError('Não foi possível copiar')
    }
  }

  // Missing methods from template
  toggleSidebar() {
    this.sidebarOpen = !this.sidebarOpen
  }

  setQuickAction(action: string) {
    this.inputText = `Por favor, me ajude com ${action}.`
    setTimeout(() => {
      this.messageInput?.nativeElement.focus()
    }, 100)
  }

  regenerateMessage(index: number) {
    // TODO: Implement regenerate functionality
    console.log('Regenerate message:', index)
  }

  formatTimestamp(timestamp: string | number | undefined): string {
    if (!timestamp) return ''
    const date = new Date(Number(timestamp))
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  }

  clearAttachments() {
    this.attachments = []
  }

  toggleVoiceInput() {
    this.voiceActive = !this.voiceActive
    if (this.voiceActive) {
      // TODO: Implement voice input
      console.log('Voice input activated')
    }
  }

  onInputChange() {
    // Auto-resize textarea
    const textarea = this.messageInput?.nativeElement
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
    }
  }

  onDragEnter(event: DragEvent) {
    event.preventDefault()
    this.dropZoneActive = true
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault()
    this.dropZoneActive = false
  }

  clearError() {
    this.error = null
  }

  clearAttachmentsError() {
    this.attachmentsError = null
  }
}
