import { Injectable, inject } from '@angular/core'
import { of } from 'rxjs'
import { catchError } from 'rxjs/operators'

import type { GenerativeMemoryItem, MemoryItem } from '../../models'
import { BackendApiService } from '../../services/backend-api.service'
import { ConversationStateFacade } from './conversations-state.facade'
import { ConversationsContextService } from './conversations-context.service'
import { ConversationsNoticeService } from './conversations-notice.service'
import {
  coerceDateInputToMs,
  extractErrorMessage,
  sanitizeDiagnosticText
} from './conversations.utils'

@Injectable({ providedIn: 'root' })
export class ConversationsMemoryService {
  private api = inject(BackendApiService)
  private state = inject(ConversationStateFacade)
  private context = inject(ConversationsContextService)
  private notices = inject(ConversationsNoticeService)

  onMemoryDraftInput(event: Event): void {
    const target = event.target as HTMLTextAreaElement | null
    this.state.memoryDraft.set(target?.value || '')
  }

  onMemoryImportanceInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    const raw = target?.value?.trim() || ''
    if (!raw) {
      this.state.memoryImportance.set(null)
      return
    }
    const n = Number(raw)
    this.state.memoryImportance.set(Number.isFinite(n) ? n : null)
  }

  onMemoryTypeChange(event: Event): void {
    const target = event.target as HTMLSelectElement | null
    this.state.memoryType.set(target?.value || 'episodic')
  }

  onMemorySearchQueryInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.state.memorySearchQuery.set(target?.value || '')
  }

  addMemory(): void {
    const content = this.state.memoryDraft().trim()
    if (!content) {
      this.state.memoryAddError.set('Digite uma memória para adicionar.')
      return
    }
    this.state.memoryAddError.set('')
    this.notices.clear('memory')
    this.state.memoryAddLoading.set(true)
    const importance = this.state.memoryImportance()
    const userId = this.context.userIdString()
    const conversationId = this.state.selectedId() || undefined
    this.api.memory.addGenerativeMemory(content, {
      type: this.state.memoryType(),
      importance: typeof importance === 'number' ? importance : undefined,
      userId,
      conversationId,
      sessionId: conversationId
    })
      .pipe(catchError((err) => {
        this.state.memoryAddError.set(extractErrorMessage(err, 'Falha ao adicionar memória.'))
        this.state.memoryAddLoading.set(false)
        return of(null)
      }))
      .subscribe((resp) => {
        if (!resp) return
        this.state.memoryDraft.set('')
        this.state.memoryAddLoading.set(false)
        this.notices.set('memory', 'success', 'Memória adicionada.')
        this.context.refreshSelectedContext()
        if (this.state.memorySearchQuery().trim()) {
          this.searchGenerativeMemory()
        }
      })
  }

  searchGenerativeMemory(): void {
    const query = this.state.memorySearchQuery().trim()
    if (!query) {
      this.state.memorySearchError.set('Digite um termo para buscar memória generativa.')
      this.state.generativeMemoryResults.set([])
      return
    }
    this.state.memorySearchError.set('')
    this.notices.clear('memory')
    this.state.memorySearchLoading.set(true)
    this.api.memory.getGenerativeMemories(query, this.state.memorySearchLimit(), {
      userId: this.context.userIdString(),
      conversationId: this.state.selectedId() || undefined
    })
      .pipe(catchError((err) => {
        this.state.memorySearchError.set(extractErrorMessage(err, 'Falha ao buscar memória generativa.'))
        this.state.memorySearchLoading.set(false)
        return of([] as GenerativeMemoryItem[])
      }))
      .subscribe((items) => {
        const next = items || []
        this.state.generativeMemoryResults.set(next)
        this.state.memorySearchLoading.set(false)
        this.notices.set('memory', 'info', next.length ? 'Busca concluída.' : 'Consulta concluída sem resultados.')
      })
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
    const snippet = sanitizeDiagnosticText(item.content, 'memory').slice(0, 48)
    return `${normalizedTs}:${snippet}:${index}`
  }
}
