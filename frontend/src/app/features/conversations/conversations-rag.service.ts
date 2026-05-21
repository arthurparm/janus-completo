import { Injectable, inject } from '@angular/core'
import { Observable, of } from 'rxjs'
import { catchError } from 'rxjs/operators'

import type {
  RagHybridResponse,
  RagSearchResponse,
  RagUserChatResponse,
  RagUserChatV2Response
} from '../../models'
import { BackendApiService } from '../../services/backend-api.service'
import { ConversationStateFacade } from './conversations-state.facade'
import type { RagMode } from './conversations.types'
import { ConversationsContextService } from './conversations-context.service'
import { ConversationsNoticeService } from './conversations-notice.service'
import { extractErrorMessage } from './conversations.utils'

@Injectable({ providedIn: 'root' })
export class ConversationsRagService {
  private api = inject(BackendApiService)
  private state = inject(ConversationStateFacade)
  private context = inject(ConversationsContextService)
  private notices = inject(ConversationsNoticeService)

  onRagQueryInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.state.ragQuery.set(target?.value || '')
  }

  onRagModeChange(event: Event): void {
    const target = event.target as HTMLSelectElement | null
    const value = (target?.value || 'hybrid_search') as RagMode
    this.state.ragMode.set(value)
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

  runRagQuery(): void {
    const query = this.state.ragQuery().trim()
    if (!query) {
      this.state.ragError.set('Digite uma consulta para executar no RAG.')
      this.state.ragResult.set(null)
      return
    }
    const mode = this.state.ragMode()
    const userId = this.context.userIdString()
    const conversationId = this.state.selectedId() || undefined
    this.state.ragError.set('')
    this.notices.clear('rag')
    this.state.ragResultViewTab.set('resposta')
    this.state.ragLoading.set(true)

    let request$: Observable<unknown>

    if (mode === 'search') {
      request$ = this.api.knowledge.ragSearch({ query, limit: 5 })
    } else if (mode === 'user-chat') {
      if (!userId) {
        this.state.ragLoading.set(false)
        this.state.ragError.set('Usuário autenticado necessário para RAG user-chat.')
        this.notices.set('rag', 'warning', 'Entre com usuário autenticado para usar este modo.')
        return
      }
      request$ = this.api.knowledge.ragUserChat({ query, user_id: userId, session_id: conversationId, limit: 5 })
    } else if (mode === 'user_chat') {
      request$ = this.api.knowledge.ragUserChatV2({ query, user_id: userId || undefined, session_id: conversationId, limit: 5 })
    } else if (mode === 'productivity') {
      if (!userId) {
        this.state.ragLoading.set(false)
        this.state.ragError.set('Usuário autenticado necessário para RAG productivity.')
        this.notices.set('rag', 'warning', 'Entre com usuário autenticado para usar este modo.')
        return
      }
      request$ = this.api.knowledge.ragProductivitySearch({ query, user_id: userId, limit: 5 })
    } else {
      request$ = this.api.knowledge.ragHybridSearch({ query, user_id: userId || undefined, limit: 5 })
    }

    request$
      .pipe(catchError((err) => {
        this.state.ragError.set(extractErrorMessage(err, 'Falha ao executar consulta RAG.'))
        this.state.ragLoading.set(false)
        return of(null)
      }))
      .subscribe((resp: unknown) => {
        this.state.ragLoading.set(false)
        if (!resp) {
          this.state.ragResult.set(null)
          return
        }
        if (typeof resp === 'object' && resp !== null && 'results' in resp) {
          const v2 = resp as RagUserChatV2Response
          const results = (v2.results || []) as Record<string, unknown>[]
          this.state.ragResult.set({ mode, results })
          this.notices.set('rag', 'info', results.length ? 'Consulta RAG concluída.' : 'Consulta concluída sem resultados.')
          return
        }
        if (typeof resp === 'object' && resp !== null && 'answer' in resp) {
          const standard = resp as RagSearchResponse | RagUserChatResponse | RagHybridResponse
          const answer = standard.answer || ''
          const citations = standard.citations || []
          this.state.ragResult.set({ mode, answer, citations })
          const hasAnswer = Boolean(answer.trim())
          const hasCitations = citations.length > 0
          this.notices.set('rag', 'info', hasAnswer || hasCitations ? 'Consulta RAG concluída.' : 'Consulta concluída sem resultados.')
          return
        }
        this.state.ragResult.set({ mode, results: [] })
        this.notices.set('rag', 'info', 'Consulta concluída sem resultados.')
      })
  }
}

