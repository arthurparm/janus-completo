import { Injectable, inject } from '@angular/core'
import { of } from 'rxjs'
import { catchError } from 'rxjs/operators'

import type { DocSearchResultItem } from '../../models'
import { BackendApiService } from '../../services/backend-api.service'
import { ConversationStateFacade } from './conversations-state.facade'
import { ConversationsContextService } from './conversations-context.service'
import { ConversationsNoticeService } from './conversations-notice.service'
import { extractErrorMessage } from './conversations.utils'

@Injectable({ providedIn: 'root' })
export class ConversationsDocsService {
  private api = inject(BackendApiService)
  private state = inject(ConversationStateFacade)
  private context = inject(ConversationsContextService)
  private notices = inject(ConversationsNoticeService)

  onDocLinkInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.state.docLinkUrl.set(target?.value || '')
  }

  onDocSearchInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.state.docSearchQuery.set(target?.value || '')
  }

  onDocFileSelected(event: Event): void {
    const target = event.target as HTMLInputElement | null
    const file = target?.files?.[0] || null
    this.state.selectedUploadFile.set(file)
    this.state.docUploadError.set('')
  }

  uploadSelectedDoc(): void {
    const file = this.state.selectedUploadFile()
    if (!file) {
      this.state.docUploadError.set('Selecione um arquivo para upload.')
      return
    }
    const userId = this.context.userIdString()
    this.state.docUploadError.set('')
    this.notices.clear('docs')
    this.state.docUploadInFlight.set(true)
    this.state.docUploadProgress.set(0)
    this.api.documents.uploadDocument(file, this.state.selectedId() || undefined, userId || undefined)
      .pipe(catchError((err) => {
        this.state.docUploadError.set(extractErrorMessage(err, 'Falha no upload do documento.'))
        this.state.docUploadInFlight.set(false)
        this.state.docUploadProgress.set(null)
        return of(null)
      }))
      .subscribe((evt) => {
        if (!evt) return
        if (typeof evt.progress === 'number') {
          this.state.docUploadProgress.set(evt.progress)
        }
        if (evt.response) {
          const status = String(evt.response.status || '')
          if (status === 'file_too_large') {
            this.state.docUploadError.set('Arquivo maior que o limite permitido.')
          } else if (status === 'quota_exceeded') {
            this.state.docUploadError.set('Quota de documentos excedida para este usuário.')
          } else {
            this.state.docUploadError.set('')
            this.notices.set('docs', 'success', 'Upload concluído.')
          }
          this.state.docUploadInFlight.set(false)
          this.state.docUploadProgress.set(status ? 100 : null)
          this.state.selectedUploadFile.set(null)
          this.context.refreshSelectedContext()
        }
      })
  }

  linkDocumentUrl(): void {
    const url = this.state.docLinkUrl().trim()
    const conversationId = this.state.selectedId()
    if (!url) {
      this.state.docLinkError.set('Informe uma URL para vincular.')
      return
    }
    if (!conversationId) {
      this.state.docLinkError.set('Selecione ou crie uma conversa antes de vincular URL.')
      return
    }
    this.state.docLinkError.set('')
    this.notices.clear('docs')
    this.state.docLinkLoading.set(true)
    this.api.documents.linkUrl(conversationId, url, this.context.userIdString() || undefined)
      .pipe(catchError((err) => {
        this.state.docLinkError.set(extractErrorMessage(err, 'Falha ao vincular URL.'))
        this.state.docLinkLoading.set(false)
        return of(null)
      }))
      .subscribe((resp) => {
        if (!resp) return
        this.state.docLinkLoading.set(false)
        if (resp.status === 'file_too_large') {
          this.state.docLinkError.set('Conteúdo remoto acima do limite.')
        } else if (resp.status === 'quota_exceeded') {
          this.state.docLinkError.set('Quota de documentos excedida.')
        } else {
          this.state.docLinkUrl.set('')
          this.state.docLinkError.set('')
          this.notices.set('docs', 'success', 'Documento vinculado.')
        }
        this.context.refreshSelectedContext()
      })
  }

  searchDocs(): void {
    const query = this.state.docSearchQuery().trim()
    if (!query) {
      this.state.docSearchError.set('Digite um termo para buscar documentos.')
      this.state.docSearchResults.set([])
      return
    }
    this.state.docSearchError.set('')
    this.notices.clear('docs')
    this.state.docSearchLoading.set(true)
    this.api.documents.searchDocuments(query, undefined, undefined, this.context.userIdString())
      .pipe(catchError((err) => {
        this.state.docSearchError.set(extractErrorMessage(err, 'Falha ao buscar documentos.'))
        this.state.docSearchLoading.set(false)
        return of({ results: [] as DocSearchResultItem[] })
      }))
      .subscribe((resp) => {
        this.state.docSearchResults.set(resp.results || [])
        this.state.docSearchLoading.set(false)
        if ((resp.results || []).length > 0) {
          this.notices.set('docs', 'info', 'Busca concluída.')
        }
      })
  }

  deleteDoc(docId: string): void {
    if (!docId) return
    if (typeof window !== 'undefined' && !window.confirm('Excluir este documento?')) return
    this.state.deletingDocIds.update((curr) => ({ ...curr, [docId]: true }))
    this.api.documents.deleteDocument(docId, this.context.userIdString())
      .pipe(catchError((err) => {
        this.state.docSearchError.set(extractErrorMessage(err, 'Falha ao excluir documento.'))
        this.state.deletingDocIds.update((curr) => {
          const next = { ...curr }
          delete next[docId]
          return next
        })
        return of(null)
      }))
      .subscribe((resp) => {
        this.state.deletingDocIds.update((curr) => {
          const next = { ...curr }
          delete next[docId]
          return next
        })
        if (!resp) return
        this.state.docs.update((items) => items.filter((d) => d.doc_id !== docId))
        this.state.docSearchResults.update((items) => items.filter((d) => String(d.doc_id) !== docId))
        this.notices.set('docs', 'success', 'Documento removido.')
      })
  }

  isBusinessDocError(message: string | null | undefined): boolean {
    const value = String(message || '').toLowerCase()
    return value.includes('quota') || value.includes('limite') || value.includes('maior')
  }
}

