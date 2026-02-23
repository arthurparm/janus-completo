import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { RouterLink } from '@angular/router'
import { FormControl, ReactiveFormsModule } from '@angular/forms'
import { of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { Router } from '@angular/router'

import { AuthService } from '../../core/auth/auth.service'
import {
  ConversationMeta,
  BackendApiService
} from '../../services/backend-api.service'
import { UiBadgeComponent } from '../../shared/components/ui/ui-badge/ui-badge.component'
import { UiButtonComponent } from '../../shared/components/ui/button/button.component'
import { Header } from '../../core/layout/header/header'
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component'

// Widgets
import { KnowledgeWidget } from './widgets/knowledge-widget/knowledge-widget'
import { AutonomyWidget } from './widgets/autonomy-widget/autonomy-widget'
import { LearningWidget } from './widgets/learning-widget/learning-widget'

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    UiBadgeComponent,
    UiButtonComponent,
    Header,
    SkeletonComponent,
    KnowledgeWidget,
    AutonomyWidget,
    LearningWidget
  ],
  templateUrl: './home.html',
  styleUrls: ['./home.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HomeComponent {
  private api = inject(BackendApiService)
  private auth = inject(AuthService)
  private destroyRef = inject(DestroyRef)
  private router = inject(Router)

  readonly prompt = new FormControl('', { nonNullable: true })
  readonly loading = signal(true)
  readonly actionLoading = signal(false)
  readonly error = signal('')
  readonly notice = signal('')
  
  readonly conversations = signal<ConversationMeta[]>([])

  readonly user = this.auth.user
  readonly suggestions = [
    'Criar um novo agente de vendas',
    'Analisar os logs de erro de hoje',
    'Resumir o documento de arquitetura',
    'Gerar testes para o módulo de pagamentos'
  ]

  readonly displayName = computed(() => {
    const user = this.user()
    return user?.display_name || user?.username || user?.email?.split('@')[0] || 'Criador'
  })

  constructor() {
    this.loadRecentConversations()
  }

  applySuggestion(value: string) {
    this.prompt.setValue(value)
  }

  startChat() {
    if (this.actionLoading()) return
    const intent = this.prompt.value.trim()
    
    this.actionLoading.set(true)
    this.notice.set('')
    this.error.set('')
    
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    
    // Se tiver intenção, passamos como mensagem inicial (ainda não suportado diretamente no startChat pelo front, 
    // mas vamos criar e depois enviar mensagem ou assumir que o fluxo de chat lida com isso. 
    // Por enquanto, criamos a conversa e navegamos.)
    
    this.api.startChat(undefined, undefined, userId)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError(() => {
          this.error.set('Falha ao iniciar conversa.')
          this.actionLoading.set(false)
          return of(null)
        })
      )
      .subscribe((resp) => {
        if (resp) {
          // Se tiver intenção, poderíamos enviar a mensagem aqui, mas vamos deixar o usuário digitar lá
          // ou passar via query param se o chat suportar.
          this.router.navigate(['/conversations', resp.conversation_id], {
             queryParams: intent ? { initialPrompt: intent } : undefined 
          })
        }
        this.actionLoading.set(false)
      })
  }

  openConversation(conversationId: string) {
    if (!conversationId) return
    this.router.navigate(['/conversations', conversationId])
  }

  private loadRecentConversations() {
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    this.api.listConversations(userId ? { user_id: userId, limit: 4 } : { limit: 4 })
      .pipe(
        map((resp) => resp.conversations || []),
        catchError(() => of([]))
      )
      .subscribe(convs => {
        this.conversations.set(convs)
        this.loading.set(false)
      })
  }
}
