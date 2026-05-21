import { Injectable, inject } from '@angular/core'
import { forkJoin, of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'

import { BackendApiService } from '../../services/backend-api.service'
import type { MemoryItem } from '../../models'
import { isConversationMemory } from './conversations.utils'
import { ConversationStateFacade } from './conversations-state.facade'
import { ConversationsAutonomyService } from './conversations-autonomy.service'

@Injectable({ providedIn: 'root' })
export class ConversationsContextService {
  private api = inject(BackendApiService)
  private state = inject(ConversationStateFacade)
  private autonomy = inject(ConversationsAutonomyService)

  loadContext(conversationId: string): void {
    this.state.contextLoading.set(true)
    const userId = this.userIdString()
    forkJoin({
      docs: this.api.documents.listDocuments(conversationId, userId).pipe(
        map((resp) => resp.items || []),
        catchError(() => of([]))
      ),
      memory: this.api.memory.getMemoryTimeline({
        limit: 24,
        user_id: userId,
        conversation_id: conversationId
      }).pipe(
        map((items) => items.filter((item) => isConversationMemory(item, conversationId))),
        catchError(() => of([] as MemoryItem[]))
      )
    }).subscribe((result) => {
      this.state.docs.set(result.docs)
      this.state.memoryUser.set(result.memory)
      this.state.contextLoading.set(false)
    })
    this.autonomy.loadAutonomyContext()
  }

  refreshSelectedContext(): void {
    const id = this.state.selectedId()
    if (!id) return
    this.loadContext(id)
  }

  userIdString(): string | undefined {
    const id = this.state.user()?.id
    return id != null ? String(id) : undefined
  }
}

