import { Component, OnInit, inject, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { JanusApiService, ConversationsListResponse, ConversationMeta } from '../../../services/janus-api.service'
import { Router } from '@angular/router'
import { MatMenuModule } from '@angular/material/menu'
import { MatIconModule } from '@angular/material/icon'

@Component({
  selector: 'app-conversations',
  standalone: true,
  imports: [CommonModule, FormsModule, MatMenuModule, MatIconModule],
  templateUrl: './conversations.html',
  styleUrl: './conversations.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConversationsComponent implements OnInit {
  private api = inject(JanusApiService)
  private router = inject(Router)
  items: ConversationMeta[] = []
  filtered: ConversationMeta[] = []
  conversations: ConversationMeta[] = [] // Alias for items
  q = ''
  projectId = ''
  startDate?: string
  endDate?: string
  page = 1
  pageSize = 10
  sortKey: 'updated_at' | 'created_at' | 'last_message_at' | 'title' | 'message_count' = 'updated_at'
  sortDir: 'asc' | 'desc' = 'desc'
  loading = false
  error: string | null = null
  viewMode: 'grid' | 'list' = 'grid'
  statusFilter: 'new' | 'progress' | 'done' | '' = ''

  ngOnInit() { this.load() }

  load() {
    this.loading = true
    this.api.listConversations({ project_id: this.projectId || undefined }).subscribe({
      next: (resp: ConversationsListResponse) => {
        this.items = (resp.conversations || []).slice()
        this.applyFilters()
        this.loading = false
      },
      error: () => { this.error = 'Falha ao carregar conversas'; this.loading = false }
    })
  }

  applyFilters() {
    const q = this.q.trim().toLowerCase()
    let base = !q ? this.items : this.items.filter(it => {
      const t = (it.title || '').toLowerCase()
      const c = (it.last_message?.content || '').toLowerCase()
      return t.includes(q) || c.includes(q)
    })
    
    // Apply status filter
    if (this.statusFilter) {
      base = base.filter(it => {
        const status = this.statusChip(it).toLowerCase()
        return status === this.getStatusFilterLabel(this.statusFilter)
      })
    }
    
    const sd = this.startDate ? Date.parse(this.startDate) : undefined
    const ed = this.endDate ? Date.parse(this.endDate) : undefined
    const dateFiltered = base.filter(it => {
      const val = Number(it.updated_at || it.created_at || 0)
      if (sd && val < sd) return false
      if (ed && val > ed) return false
      return true
    })
    const sorted = dateFiltered.sort((a, b) => {
      let ka: number, kb: number
      
      if (this.sortKey === 'last_message_at') {
        ka = Date.parse(a.last_message_at || '')
        kb = Date.parse(b.last_message_at || '')
      } else if (this.sortKey === 'title') {
        ka = (a.title || '').toLowerCase().charCodeAt(0) || 0
        kb = (b.title || '').toLowerCase().charCodeAt(0) || 0
      } else if (this.sortKey === 'message_count') {
        ka = a.message_count || 0
        kb = b.message_count || 0
      } else {
        ka = Number(a[this.sortKey] || 0)
        kb = Number(b[this.sortKey] || 0)
      }
      
      return this.sortDir === 'asc' ? ka - kb : kb - ka
    })
    
    this.filtered = sorted
    this.conversations = this.items // Update alias
    this.page = 1
  }

  private getStatusFilterLabel(filter: string): string {
    switch (filter) {
      case 'new': return 'nova'
      case 'progress': return 'em andamento'
      case 'done': return 'resolvida'
      default: return ''
    }
  }

  rename(it: ConversationMeta) {
    const nt = prompt('Novo título:', it.title || '')
    if (!nt || nt.trim() === '') return
    this.api.renameConversation(it.conversation_id, nt.trim()).subscribe({
      next: () => { this.load() },
      error: () => { this.error = 'Falha ao renomear' }
    })
  }

  remove(it: ConversationMeta) {
    const ok = confirm('Excluir conversa?')
    if (!ok) return
    this.api.deleteConversation(it.conversation_id).subscribe({
      next: () => { this.load() },
      error: () => { this.error = 'Falha ao excluir' }
    })
  }

  setSort(key: 'updated_at' | 'created_at') { this.sortKey = key; this.applyFilters() }
  toggleDir() { this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'; this.applyFilters() }
  nextPage() { const max = Math.ceil(this.filtered.length / this.pageSize); if (this.page < max) this.page += 1 }
  prevPage() { if (this.page > 1) this.page -= 1 }

  startNew() {
    this.loading = true
    this.api.startChat('Nova conversa').subscribe({
      next: (resp) => { try { this.router.navigate(['/chat', resp.conversation_id]) } catch {} this.loading = false },
      error: () => { this.error = 'Falha ao iniciar conversa'; this.loading = false }
    })
  }

  open(it: ConversationMeta) { try { this.router.navigate(['/chat', it.conversation_id]) } catch {} }

  statusChip(it: ConversationMeta): 'Nova'|'Em andamento'|'Resolvida' {
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
    if (!timestamp) return ''
    const date = new Date(Number(timestamp))
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
    if (!timestamp) return ''
    return new Date(Number(timestamp)).toLocaleDateString('pt-BR')
  }

  truncateText(text: string, maxLength: number): string {
    if (!text) return ''
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  duplicate(conversation: ConversationMeta) {
    // TODO: Implement duplicate functionality
    console.log('Duplicate conversation:', conversation)
  }

  export(conversation: ConversationMeta) {
    // TODO: Implement export functionality
    console.log('Export conversation:', conversation)
  }

  firstPage() {
    this.page = 1
  }

  lastPage() {
    const maxPage = Math.ceil(this.filtered.length / this.pageSize)
    this.page = maxPage
  }

  goToPage(pageNum: number) {
    this.page = pageNum
  }

  onPageSizeChange() {
    this.page = 1
  }

  getVisiblePages(): number[] {
    const totalPages = Math.ceil(this.filtered.length / this.pageSize)
    const currentPage = this.page
    const maxVisible = 5
    
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2))
    let end = Math.min(totalPages, start + maxVisible - 1)
    
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
    return Math.min(this.page * this.pageSize, this.filtered.length)
  }
}
