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
    console.log('[ChatComponent] Inicializando componente de chat')
    const cid = this.route.snapshot.paramMap.get('conversationId')
    console.log('[ChatComponent] Conversation ID obtido:', cid)
    
    if (cid) { 
      console.log('[ChatComponent] Carregando conversa existente:', cid)
      this.conversationId = cid; 
      this.loadHistory() 
    } else { 
      console.log('[ChatComponent] Iniciando nova conversa')
      this.startChat() 
    }
    
    this.initMedia()
    
    this.stream.status().subscribe(st => {
      console.log('[ChatComponent] Stream status mudou:', st)
      this.streaming = st === 'streaming' || st === 'open'
      this.reconnecting = st === 'retrying'
    })
    
    this.stream.typing().subscribe(t => { 
      console.log('[ChatComponent] Typing status:', t)
      this.typingActive = !!t 
    })
    
    this.stream.partials().subscribe(p => {
      console.log('[ChatComponent] Recebendo partial:', p)
      const anyMsg = this.messages[this.messages.length - 1]
      if (anyMsg && anyMsg.role === 'user' && !this.loading) {
        console.log('[ChatComponent] Processando partial para mensagem do usuário')
      }
      const last = this.messages[this.messages.length - 1]
      if (last && last.role !== 'user') {
        const merged = { role: 'assistant', content: (last.content || '') + p.text }
        console.log('[ChatComponent] Atualizando mensagem do assistente:', merged)
        this.messages = [...this.messages.slice(0, -1), merged]
      } else {
        console.log('[ChatComponent] Adicionando nova mensagem do assistente:', p.text)
        this.messages = [...this.messages, { role: 'assistant', content: p.text }]
      }
    })
    
    this.stream.done().subscribe((d) => {
      console.log('[ChatComponent] Stream finalizado:', d)
      this.ux.record({ outcome: 'success', timestamp: Date.now() })
      this.loading = false; this.streaming = false; this.typingActive = false
      const idx = this.messages.length - 1
      if (idx >= 0 && d?.citations) {
        console.log('[ChatComponent] Adicionando citações:', d.citations)
        this.citationsByIndex[idx] = d.citations as any[]
      }
    })
    
    this.stream.errors().subscribe(e => { 
      console.error('[ChatComponent] Erro no stream:', e)
      this.error = e.error; 
      this.ux.record({ outcome: 'error', timestamp: Date.now() }) 
    })
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
    console.log('[ChatComponent] Iniciando nova conversa')
    this.loading = true
    this.error = null
    this.api.startChat('Janus Chat')
      .subscribe({
        next: (resp) => {
          console.log('[ChatComponent] Conversa iniciada com sucesso:', resp.conversation_id)
          this.conversationId = resp.conversation_id
          try { this.router.navigate(['/chat', this.conversationId]) } catch {}
          this.loadHistory()
        },
        error: (err) => {
          console.error('[ChatComponent] Erro ao iniciar conversa:', err)
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
    if (!this.conversationId) { 
      console.log('[ChatComponent] Nenhuma conversationId, skip loadHistory')
      this.loading = false; 
      return 
    }
    console.log('[ChatComponent] Carregando histórico da conversa:', this.conversationId)
    this.api.getChatHistory(this.conversationId)
      .subscribe({
        next: (resp: ChatHistoryResponse) => {
          console.log('[ChatComponent] Histórico carregado com sucesso:', resp.messages?.length, 'mensagens')
          this.messages = resp.messages || []
          this.loading = false
          this.loadAttachments()
        },
        error: (err) => {
          console.error('[ChatComponent] Erro ao carregar histórico:', err)
          this.error = 'Falha ao carregar histórico'
          this.loading = false
          console.error(err)
        }
      })
  }

  sendMessage() {
    const content = this.inputText?.trim()
    console.log('[ChatComponent] Tentando enviar mensagem:', content)
    if (!content) {
      console.log('[ChatComponent] Mensagem vazia, não enviando')
      return
    }
    
    if (!this.conversationId) { 
      console.log('[ChatComponent] Sem conversationId, iniciando nova conversa')
      this.startChat(); 
      return 
    }

    console.log('[ChatComponent] Enviando mensagem para conversa:', this.conversationId)
    // append user message optimistically
    const userMsg: ChatMessage = { role: 'user', content }
    this.messages = [...this.messages, userMsg]
    console.log('[ChatComponent] Mensagem do usuário adicionada:', userMsg)
    this.inputText = ''
    this.loading = true
    this.error = null
    
    if (this.sseEnabled && typeof window !== 'undefined' && 'EventSource' in window) {
      console.log('[ChatComponent] Usando streaming SSE')
      console.log('[ChatComponent] SSE habilitado:', this.sseEnabled)
      console.log('[ChatComponent] Window disponível:', typeof window !== 'undefined')
      console.log('[ChatComponent] EventSource disponível:', 'EventSource' in window)
      this.stream.start({ conversationId: this.conversationId, text: content })
      console.log('[ChatComponent] Stream iniciado para conversa:', this.conversationId)
    } else {
      console.log('[ChatComponent] Usando API tradicional')
      this.api.sendChatMessage(this.conversationId, content)
        .subscribe({
          next: (resp) => {
            console.log('[ChatComponent] Resposta recebida:', resp)
            const assistant = resp.assistant_message || resp.message
            if (assistant) {
              const idx = this.messages.length
              console.log('[ChatComponent] Adicionando resposta do assistente:', assistant)
              this.messages = [...this.messages, assistant]
              const cits: any[] = (resp as any)?.citations || []
              if (cits && cits.length) {
                console.log('[ChatComponent] Adicionando citações:', cits)
                this.citationsByIndex[idx] = cits
              }
            } else if (resp.messages && resp.messages.length) {
              console.log('[ChatComponent] Atualizando todas as mensagens:', resp.messages.length)
              this.messages = resp.messages
            }
            this.ux.record({ outcome: 'success', timestamp: Date.now() })
            this.loading = false
            console.log('[ChatComponent] Mensagem enviada com sucesso')
          },
          error: (err) => {
            console.error('[ChatComponent] Erro ao enviar mensagem:', err)
            this.error = 'Falha ao enviar mensagem'
            this.ux.record({ outcome: 'error', timestamp: Date.now() })
            this.loading = false
            console.error(err)
          }
        })
    }
  }

  cancelStreaming() {
    console.log('[ChatComponent] Cancelando streaming')
    this.stream.stop()
    this.streaming = false
    this.typingActive = false
    this.loading = false
    this.ux.record({ outcome: 'cancel', timestamp: Date.now() })
    console.log('[ChatComponent] Streaming cancelado')
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
    console.log('[ChatComponent] Arquivos selecionados via input')
    const input = ev.target as HTMLInputElement
    const files = input?.files
    if (!files || !this.conversationId) {
      console.log('[ChatComponent] Nenhum arquivo ou conversationId inválido')
      return
    }
    const f = files[0]
    console.log('[ChatComponent] Arquivo selecionado:', f.name, f.type, f.size)
    this.uploadFile(f)
  }

  onDrop(ev: DragEvent) {
    console.log('[ChatComponent] Arquivo dropado')
    ev.preventDefault()
    if (!ev.dataTransfer || !ev.dataTransfer.files || !this.conversationId) {
      console.log('[ChatComponent] Drop inválido - dados ou conversationId ausentes')
      return
    }
    const f = ev.dataTransfer.files[0]
    console.log('[ChatComponent] Arquivo dropado:', f.name, f.type, f.size)
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
    console.log('[ChatComponent] Iniciando upload do arquivo:', file.name)
    if (!file || !this.conversationId) {
      console.log('[ChatComponent] Upload cancelado - arquivo ou conversationId inválido')
      return
    }
    
    const allowed = ['text/plain','text/html','application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','image/png','image/jpeg','image/gif']
    const ct = (file.type || '').toLowerCase()
    if (!allowed.some(a => ct.startsWith(a))) { 
      console.log('[ChatComponent] Tipo de arquivo não suportado:', ct)
      this.error = 'Tipo de arquivo não suportado'; 
      return 
    }
    
    this.uploading = true
    this.uploadProgress = 0
    console.log('[ChatComponent] Upload iniciado para conversation:', this.conversationId)
    
    this.api.uploadAttachmentWithProgress(this.conversationId, file)
      .subscribe({
        next: (ev) => {
          if (typeof ev.progress === 'number') {
            this.uploadProgress = ev.progress
            console.log('[ChatComponent] Progresso do upload:', this.uploadProgress + '%')
          }
          if (ev.response) { 
            console.log('[ChatComponent] Upload concluído com sucesso')
            this.uploading = false; 
            this.uploadProgress = 0; 
            this.loadAttachments() 
          }
        },
        error: (err) => { 
          console.error('[ChatComponent] Erro no upload:', err)
          this.error = 'Falha no upload'; 
          this.uploading = false; 
          this.notify.notifyError('Falha no upload') 
        }
      })
  }

  loadAttachments() {
    if (!this.conversationId) {
      console.log('[ChatComponent] Sem conversationId, skip loadAttachments')
      return
    }
    
    const id = String(this.conversationId || '')
    if (!id) { 
      console.log('[ChatComponent] ID inválido para carregar anexos')
      return 
    }
    
    console.log('[ChatComponent] Carregando anexos da conversa:', id)
    this.attachmentsLoading = true
    this.attachmentsError = null
    
    this.api.listAttachments(id)
      .subscribe({
        next: (resp) => { 
          console.log('[ChatComponent] Anexos carregados:', resp.items?.length || 0)
          this.attachments = (resp.items || []).map(it => ({ 
            doc_id: it.doc_id, 
            file_name: it.file_name, 
            chunks: it.chunks 
          }))
          this.attachmentsLoading = false 
        },
        error: (err) => {
          console.error('[ChatComponent] Erro ao carregar anexos:', err)
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
    console.log('[ChatComponent] Copiando mensagem index:', index)
    const m = this.messages[index]
    if (!m || !m.content) {
      console.log('[ChatComponent] Mensagem inválida para cópia')
      return
    }
    try {
      console.log('[ChatComponent] Copiando conteúdo:', m.content.substring(0, 50) + '...')
      navigator.clipboard.writeText(m.content)
      this.notify.notifyInfo('Conteúdo copiado')
      console.log('[ChatComponent] Conteúdo copiado com sucesso')
    } catch (err) {
      console.error('[ChatComponent] Erro ao copiar:', err)
      this.notify.notifyError('Não foi possível copiar')
    }
  }

  // Missing methods from template
  toggleSidebar() {
    this.sidebarOpen = !this.sidebarOpen
    console.log('[ChatComponent] Sidebar toggled:', this.sidebarOpen)
  }

  setQuickAction(action: string) {
    console.log('[ChatComponent] Quick action selecionada:', action)
    this.inputText = `Por favor, me ajude com ${action}.`
    setTimeout(() => {
      this.messageInput?.nativeElement.focus()
      console.log('[ChatComponent] Focus movido para input após quick action')
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
    console.log('[ChatComponent] Input mudou, redimensionando textarea')
    // Auto-resize textarea
    const textarea = this.messageInput?.nativeElement
    if (textarea) {
      const previousHeight = textarea.style.height
      textarea.style.height = 'auto'
      const newHeight = Math.min(textarea.scrollHeight, 200)
      textarea.style.height = newHeight + 'px'
      console.log('[ChatComponent] Textarea redimensionada:', previousHeight, '->', newHeight)
    }
  }

  onDragEnter(event: DragEvent) {
    console.log('[ChatComponent] Drag enter detectado')
    event.preventDefault()
    this.dropZoneActive = true
    console.log('[ChatComponent] Drop zone ativado:', this.dropZoneActive)
  }

  onDragLeave(event: DragEvent) {
    console.log('[ChatComponent] Drag leave detectado')
    event.preventDefault()
    this.dropZoneActive = false
    console.log('[ChatComponent] Drop zone desativado:', this.dropZoneActive)
  }

  clearError() {
    console.log('[ChatComponent] Limpando erro:', this.error)
    this.error = null
  }

  clearAttachmentsError() {
    console.log('[ChatComponent] Limpando erro de anexos:', this.attachmentsError)
    this.attachmentsError = null
  }
}
