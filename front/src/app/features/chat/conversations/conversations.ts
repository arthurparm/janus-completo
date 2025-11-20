import { Component, OnInit, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { JanusApiService, ConversationsListResponse, ConversationMeta } from '../../../services/janus-api.service'
import { Router } from '@angular/router'

@Component({
  selector: 'app-conversations',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './conversations.html',
  styleUrl: './conversations.scss'
})
export class ConversationsComponent implements OnInit {
  private api = inject(JanusApiService)
  private router = inject(Router)
  items: ConversationMeta[] = []
  filtered: ConversationMeta[] = []
  q = ''
  projectId = ''
  startDate?: string
  endDate?: string
  page = 1
  pageSize = 10
  sortKey: 'updated_at' | 'created_at' | 'last_message_at' = 'updated_at'
  sortDir: 'asc' | 'desc' = 'desc'
  loading = false
  error: string | null = null

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
    const base = !q ? this.items : this.items.filter(it => {
      const t = (it.title || '').toLowerCase()
      const c = (it.last_message?.content || '').toLowerCase()
      return t.includes(q) || c.includes(q)
    })
    const sd = this.startDate ? Date.parse(this.startDate) : undefined
    const ed = this.endDate ? Date.parse(this.endDate) : undefined
    const dateFiltered = base.filter(it => {
      const val = Number(it.updated_at || it.created_at || 0)
      if (sd && val < sd) return false
      if (ed && val > ed) return false
      return true
    })
    const sorted = dateFiltered.sort((a, b) => {
      const ka = Number((this.sortKey === 'last_message_at' ? Date.parse(a.last_message_at || '') : (a[this.sortKey] || 0)))
      const kb = Number((this.sortKey === 'last_message_at' ? Date.parse(b.last_message_at || '') : (b[this.sortKey] || 0)))
      return this.sortDir === 'asc' ? ka - kb : kb - ka
    })
    this.filtered = sorted
    this.page = 1
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
}
