/* eslint-disable no-console */
import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { JanusApiService, ConversationMeta } from '../../../services/janus-api.service'
import { ConversationStore } from '../store/conversation.store'
import { Router, NavigationEnd } from '@angular/router'
import { MatMenuModule } from '@angular/material/menu'
import { MatIconModule } from '@angular/material/icon'
import { ConversationRefreshService } from '../../../services/conversation-refresh.service'
import { DemoService } from '../../../core/services/demo.service'
import { UiService } from '../../../shared/services/ui.service'
import { filter, Subject, takeUntil } from 'rxjs'

@Component({
  selector: 'app-conversations',
  standalone: true,
  imports: [CommonModule, FormsModule, MatMenuModule, MatIconModule],
  templateUrl: './conversations.html',
  styleUrl: './conversations.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConversationsComponent implements OnInit, OnDestroy {
  private api = inject(JanusApiService)
  public store = inject(ConversationStore) // Public for template access
  private router = inject(Router)
  private cdr = inject(ChangeDetectorRef)
  private destroy$ = new Subject<void>()
  private refreshService = inject(ConversationRefreshService)
  private demoService = inject(DemoService)
  private ui = inject(UiService)

  // UI State for Template (Proxies to Store)
  get items() { return this.store.items() }
  get filtered() { return this.store.filteredConversations() }
  get conversationsCount() { return this.store.totalCount() }
  get filteredCount() { return this.store.filteredCount() }
  get loading() { return this.store.loading() }
  get error() { return this.store.error() }
  get isOffline() {
    return this.demoService.isOffline()
  }

  q = ''
  projectId = ''
  startDate?: string
  endDate?: string
  page = 1
  pageSize = 10
  sortKey: 'updated_at' | 'created_at' | 'last_message_at' | 'title' | 'message_count' = 'updated_at'
  sortDir: 'asc' | 'desc' = 'desc'
  viewMode: 'grid' | 'list' = 'grid'
  statusFilter: 'new' | 'progress' | 'done' | '' = ''

  ngOnInit() {
    console.log('🔄 ConversationsComponent: ngOnInit called')
    this.load()

    // Refresh conversations when navigating back to this component
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd),
      takeUntil(this.destroy$)
    ).subscribe((event: NavigationEnd) => {
      if (event.urlAfterRedirects === '/conversations' || event.urlAfterRedirects.includes('/chat/conversations')) {
        console.log('🔄 ConversationsComponent: Navigation detected, refreshing conversations')
        this.refreshConversations()
      }
    })

    // Refresh when window/tab gains focus (user returns to this tab)
    window.addEventListener('focus', this.handleWindowFocus)

    // Listen for refresh events from other components
    this.refreshService.refreshConversations.pipe(
      takeUntil(this.destroy$)
    ).subscribe(() => {
      console.log('🔄 ConversationsComponent: Refresh event received from service')
      this.refreshConversations()
    })
  }

  handleWindowFocus = () => {
    console.log('🔄 ConversationsComponent: Window focus detected, refreshing conversations')
    this.refreshConversations()
  }

  ngOnDestroy() {
    this.destroy$.next()
    this.destroy$.complete()
    window.removeEventListener('focus', this.handleWindowFocus)
  }

  load() {
    if (this.demoService.isOffline()) {
      return
    }
    // Store handles auth dependency via switchMap
    this.store.load(this.projectId || undefined)
  }

  refreshConversations() {
    console.log('🔄 ConversationsComponent: Refreshing conversations list')
    this.load()
  }

  clearFilters() {
    this.q = ''
    this.statusFilter = ''
    this.sortKey = 'updated_at'
    this.applyFilters()
  }

  applyFilters() {
    // Sync UI state to Store
    this.store.setFilter({
      query: this.q,
      status: this.statusFilter,
      startDate: this.startDate,
      endDate: this.endDate
    });
    this.store.setSort(this.sortKey);
    this.page = 1;
  }

  // UI State
  editingId: string | null = null
  newTitleTemp = ''

  rename(it: ConversationMeta) {
    this.editingId = it.conversation_id
    this.newTitleTemp = it.title || ''
  }

  saveRename(it: ConversationMeta) {
    if (!this.newTitleTemp || !this.newTitleTemp.trim()) return
    this.store.renameConversation(it.conversation_id, this.newTitleTemp.trim())
    this.editingId = null
  }

  cancelRename() {
    this.editingId = null
    this.newTitleTemp = ''
  }

  duplicate(it: ConversationMeta) {
    if (!confirm(`Deseja duplicar a conversa "${it.title}"?`)) return

    this.api.startChat(`Cópia de ${it.title}`).subscribe({
      next: (resp) => {
        this.router.navigate(['/chat', resp.conversation_id])
      },
      error: (err) => {
        // Handle error via toast or alert if needed
        console.error('Failed to duplicate', err)
      }
    })
  }

  remove(it: ConversationMeta) {
    const title = it.title || 'conversa sem título'
    this.ui.showConfirm({
      title: 'Confirmar exclusão',
      message: `Tem certeza que deseja excluir permanentemente a conversa "${title}"?\n\nEsta ação não pode ser desfeita. Todo o histórico será perdido.`,
      confirmText: 'Sim, excluir',
      cancelText: 'Cancelar',
      confirmColor: 'warn'
    }).subscribe(confirmed => {
      if (!confirmed) return
      this.store.removeConversation(it.conversation_id)
    })
  }

  setSort(key: 'updated_at' | 'created_at') { this.sortKey = key; this.applyFilters() }
  toggleDir() { this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'; this.applyFilters() }
  nextPage() { const max = Math.ceil(this.filteredCount / this.pageSize); if (this.page < max) this.page += 1 }
  prevPage() { if (this.page > 1) this.page -= 1 }

  startNew() {
    this.api.startChat('Nova conversa').subscribe({
      next: (resp) => {
        this.router.navigate(['/chat', resp.conversation_id])
      },
      error: (err) => {
        console.error('Failed to start chat', err)
      }
    })
  }

  open(it: ConversationMeta) {
    this.router.navigate(['/chat', it.conversation_id])
  }

  statusChip(it: ConversationMeta): 'Nova' | 'Em andamento' | 'Resolvida' {
    const hasMsg = !!it.last_message
    const updated = Number(it.updated_at || 0)
    const now = Date.now()
    const days = (now - updated) / (1000 * 60 * 60 * 24)

    if (!hasMsg) return 'Nova'
    if (days > 7) return 'Resolvida'
    return 'Em andamento'
  }

  // Missing methods from template
  clearSearch() {
    this.q = ''
    this.applyFilters()
  }

  setViewMode(mode: 'grid' | 'list') {
    this.viewMode = mode
  }

  retryLoad() {
    this.load()
  }

  formatTimeAgo(timestamp: string | number | undefined): string {
    const date = this.parseDate(timestamp)
    if (!date) return ''

    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'agora'
    if (diffMins < 60) return `${diffMins}m atrás`
    if (diffHours < 24) return `${diffHours}h atrás`
    if (diffDays < 7) return `${diffDays}d atrás`
    return date.toLocaleDateString('pt-BR')
  }

  formatDate(timestamp: string | number | undefined): string {
    const date = this.parseDate(timestamp)
    if (!date) return ''
    return date.toLocaleDateString('pt-BR')
  }

  private parseDate(timestamp: string | number | undefined): Date | null {
    if (!timestamp) return null
    const num = Number(timestamp)
    if (!isNaN(num)) {
      if (num < 946684800000) {
        return new Date(num * 1000)
      }
      return new Date(num)
    }
    const date = new Date(timestamp)
    if (isNaN(date.getTime())) return null
    return date
  }

  truncateText(text: string, maxLength: number): string {
    if (!text) return ''
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  export(conversation: ConversationMeta) {
    console.log('Export conversation:', conversation)
  }

  firstPage() {
    this.page = 1
  }

  lastPage() {
    const maxPage = Math.ceil(this.filteredCount / this.pageSize)
    this.page = maxPage
  }

  goToPage(pageNum: number) {
    this.page = pageNum
  }

  onPageSizeChange() {
    this.page = 1
  }

  getVisiblePages(): number[] {
    const totalPages = Math.ceil(this.filteredCount / this.pageSize)
    const currentPage = this.page
    const maxVisible = 5

    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2))
    const end = Math.min(totalPages, start + maxVisible - 1)

    if (end - start < maxVisible - 1) {
      start = Math.max(1, end - maxVisible + 1)
    }

    const pages = []
    for (let i = start; i <= end; i++) {
      pages.push(i)
    }

    return pages
  }

  getEndIndex(): number {
    return Math.min(this.page * this.pageSize, this.filteredCount)
  }
}
