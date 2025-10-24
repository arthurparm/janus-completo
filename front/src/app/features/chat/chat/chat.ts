import {Component, OnInit, inject} from '@angular/core'
import {CommonModule} from '@angular/common'
import {FormsModule} from '@angular/forms'
import {JanusApiService, ChatMessage, ChatHistoryResponse} from '../../../services/janus-api.service'

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.html',
  styleUrl: './chat.scss'
})
export class ChatComponent implements OnInit {
  private api = inject(JanusApiService)

  conversationId: string | null = null
  messages: ChatMessage[] = []
  inputText = ''
  loading = false
  error: string | null = null

  ngOnInit() {
    this.startChat()
  }

  startChat() {
    this.loading = true
    this.error = null
    this.api.startChat('Janus Chat')
      .subscribe({
        next: (resp) => {
          this.conversationId = resp.conversation_id
          this.loadHistory()
        },
        error: (err) => {
          this.error = 'Falha ao iniciar conversa'
          this.loading = false
          console.error(err)
        }
      })
  }

  loadHistory() {
    if (!this.conversationId) { this.loading = false; return }
    this.api.getChatHistory(this.conversationId)
      .subscribe({
        next: (resp: ChatHistoryResponse) => {
          this.messages = resp.messages || []
          this.loading = false
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

    this.api.sendChatMessage(this.conversationId, content)
      .subscribe({
        next: (resp) => {
          const assistant = resp.assistant_message || resp.message
          if (assistant) {
            this.messages = [...this.messages, assistant]
          } else if (resp.messages && resp.messages.length) {
            this.messages = resp.messages
          }
          this.loading = false
        },
        error: (err) => {
          this.error = 'Falha ao enviar mensagem'
          this.loading = false
          console.error(err)
        }
      })
  }
}
