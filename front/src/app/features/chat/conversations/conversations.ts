import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { JanusApiService, ConversationsListResponse, ConversationMeta } from '../../../services/janus-api.service'
import { Router, NavigationEnd } from '@angular/router'
import { MatMenuModule } from '@angular/material/menu'
import { MatIconModule } from '@angular/material/icon'
import { AuthService } from '../../../core/auth/auth.service'
import { ConversationRefreshService } from '../../../services/conversation-refresh.service'
import { DemoService } from '../../../core/services/demo.service'
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
  private router = inject(Router)
  private auth = inject(AuthService)
  private cdr = inject(ChangeDetectorRef)
  private destroy$ = new Subject<void>()
  private refreshService = inject(ConversationRefreshService)
  private demoService = inject(DemoService)

  // User state management
  private currentUser: any = null
  private userLoaded = false

  items: ConversationMeta[] = []
  filtered: ConversationMeta[] = []

  // Safe getter for template to avoid ExpressionChangedAfterItHasBeenCheckedError
  get conversationsCount(): number {
    return this.items?.length || 0
  }
  get filteredCount(): number {
    return this.filtered?.length || 0
  }
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
  loading = false
  error: string | null = null
  viewMode: 'grid' | 'list' = 'grid'
  statusFilter: 'new' | 'progress' | 'done' | '' = ''

  ngOnInit() {
    console.log('🔄 ConversationsComponent: ngOnInit called')
    // Initialize arrays to prevent ExpressionChangedAfterItHasBeenCheckedError
    this.items = []
    this.filtered = []
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
    // Remove event listener to prevent memory leaks
    window.removeEventListener('focus', this.handleWindowFocus)
  }

  load() {
    this.loading = true
    this.error = null

    if (this.demoService.isOffline()) {
      this.loading = false
      this.items = []
      this.filtered = []
      return
    }

    // Get the current user from auth service
    this.auth.user$.subscribe(user => {
      const userId = user?.id || undefined

      const params = {
        user_id: userId,
        project_id: this.projectId || undefined
      }

      this.api.listConversations(params).subscribe({
        next: (resp: ConversationsListResponse) => {
          console.log('✅ ConversationsComponent: Conversations loaded:', resp.conversations?.length)
          this.items = (resp.conversations || []).slice()
          this.applyFilters()
          this.loading = false
          // Force change detection
          this.cdr.detectChanges()
        },
        error: (err) => {
          console.error('❌ ConversationsComponent: API error', err)
          if (err.status === 0 || err.status === 504) {
            this.demoService.enableOfflineMode();
            this.loading = false;
            this.items = [];
            this.filtered = [];
          } else {
            this.error = 'Falha ao carregar conversas'
            this.loading = false
          }
          this.cdr.detectChanges()
        }
      })
    })
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
    // Handle empty strings as undefined
    if (this.startDate === '') {
      this.startDate = undefined
    }
    if (this.endDate === '') {
      this.endDate = undefined
    }

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
        const filterLabel = this.getStatusFilterLabel(this.statusFilter)
        return status === filterLabel
      })
    }

    const sd = this.startDate ? Date.parse(this.startDate) : undefined
    const ed = this.endDate ? Date.parse(this.endDate) : undefined

    const dateFiltered = base.filter(it => {
      const updatedAt = it.updated_at || it.created_at
      const val = Number(updatedAt || 0)

      if (!updatedAt) {
        return false
      }

      const startMatch = !sd || val >= sd
      const endMatch = !ed || val <= ed
      return startMatch && endMatch
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

    // Update filtered array - items array is already updated in load()
    this.filtered = sorted
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

  // UI State
  editingId: string | null = null
  newTitleTemp = ''

  showDeleteModal = false
  conversationToDelete: ConversationMeta | null = null

  rename(it: ConversationMeta) {
    this.editingId = it.conversation_id
    this.newTitleTemp = it.title || ''
    // Focus will be handled by template directive or we can just let user click
  }

  saveRename(it: ConversationMeta) {
    if (!this.newTitleTemp || !this.newTitleTemp.trim()) return

    // Optimistic update
    const oldTitle = it.title
    it.title = this.newTitleTemp.trim()
    this.editingId = null

    this.api.renameConversation(it.conversation_id, this.newTitleTemp.trim()).subscribe({
      next: () => {
        // Success
      },
      error: () => {
        it.title = oldTitle // Revert on error
        this.error = 'Falha ao renomear'
        this.cdr.markForCheck()
      }
    })
  }

  cancelRename() {
    this.editingId = null
    this.newTitleTemp = ''
  }

  duplicate(it: ConversationMeta) {
    // Keep confirm for duplicate as receiving a modal is too much? 
    // Or we can use a simpler toast. Let's stick to confirm for now as it's less frequent
    // but the plan said replace confirm. The user asked for "excluir conversas, editar nome" improvements specifically.
    // I will leave duplicate as is for now unless asked, to focus on the requested items.
    if (!confirm(`Deseja duplicar a conversa "${it.title}"?`)) return

    this.loading = true
    // Create new conversation
    this.api.startChat(`Cópia de ${it.title}`).subscribe({
      next: (resp) => {
        this.router.navigate(['/chat', resp.conversation_id])
        this.loading = false
      },
      error: (err) => {
        this.error = 'Falha ao duplicar conversa'
        this.loading = false
      }
    })
  }

  remove(it: ConversationMeta) {
    this.conversationToDelete = it
    this.showDeleteModal = true
  }

  confirmDelete() {
    if (!this.conversationToDelete) return

    const id = this.conversationToDelete.conversation_id
    this.api.deleteConversation(id).subscribe({
      next: () => {
        this.load()
        this.closeDeleteModal()
      },
      error: () => {
        this.error = 'Falha ao excluir'
        this.closeDeleteModal()
      }
    })
  }

  closeDeleteModal() {
    this.showDeleteModal = false
    this.conversationToDelete = null
  }

  setSort(key: 'updated_at' | 'created_at') { this.sortKey = key; this.applyFilters() }
  toggleDir() { this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'; this.applyFilters() }
  nextPage() { const max = Math.ceil(this.filteredCount / this.pageSize); if (this.page < max) this.page += 1 }
  prevPage() { if (this.page > 1) this.page -= 1 }

  startNew() {
    this.loading = true
    this.api.startChat('Nova conversa').subscribe({
      next: (resp) => {
        this.router.navigate(['/chat', resp.conversation_id])
        this.loading = false
      },
      error: (err) => {
        this.error = 'Falha ao iniciar conversa'
        this.loading = false
      }
    })
  }


  debugShowDateAnalysis() {
    console.log('🔍 DEBUG: Complete Date Analysis')
    console.log('=====================================')

    console.log('Current filters:')
    console.log('  startDate:', this.startDate)
    console.log('  endDate:', this.endDate)
    console.log('  sortKey:', this.sortKey)
    console.log('  sortDir:', this.sortDir)
    console.log('  statusFilter:', this.statusFilter)

    console.log('\nRaw items from API:')
    this.items.forEach((item, index) => {
      console.log(`  [${index}] ${item.title}:`)
      console.log(`    conversation_id: ${item.conversation_id}`)
      console.log(`    created_at: ${item.created_at} (${item.created_at ? new Date(item.created_at).getTime() : 'INVALID'})`)
      console.log(`    updated_at: ${item.updated_at} (${item.updated_at ? new Date(item.updated_at).getTime() : 'INVALID'})`)
      console.log(`    last_message: ${item.last_message ? 'YES' : 'NO'}`)
      if (item.last_message) {
        console.log(`      timestamp: ${item.last_message.timestamp}`)
      }
      console.log(`    message_count: ${item.message_count}`)
    })

    console.log('\nFiltered results:')
    this.filtered.forEach((item, index) => {
      console.log(`  [${index}] ${item.title} (id: ${item.conversation_id})`)
    })

    console.log('\nDate parsing test:')
    if (this.startDate) {
      const parsed = Date.parse(this.startDate)
      console.log(`  startDate parse: ${parsed} (${parsed ? new Date(parsed).toISOString() : 'INVALID'})`)
    }
    if (this.endDate) {
      const parsed = Date.parse(this.endDate)
      console.log(`  endDate parse: ${parsed} (${parsed ? new Date(parsed).toISOString() : 'INVALID'})`)
    }

    console.log('=====================================')
  }

  // Debug method to test date input changes
  debugTestDateInputChange() {
    console.log('🧪 DEBUG: Testing date input changes')

    // Test with a simple date
    this.startDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0] // 7 days ago
    this.endDate = new Date().toISOString().split('T')[0] // today

    console.log('🧪 DEBUG: Set dates to:', { startDate: this.startDate, endDate: this.endDate })
    this.applyFilters()
  }

  // Public method to force change detection
  forceChangeDetection() {
    console.log('🔄 Public: Forcing change detection')
    this.cdr.markForCheck()
  }

  // Debug method to compare data structure
  debugCompareDataStructures() {
    console.log('🔍 DEBUG: Comparing data structures - Mock vs Real')
    console.log('=====================================')

    console.log('Mock data structure (working):')
    const mockData = [
      {
        conversation_id: '20',
        title: 'Conversa Mock ID 20',
        created_at: Date.now() - 86400000,
        updated_at: Date.now() - 3600000,
        last_message: {
          role: 'assistant',
          content: 'Esta é uma mensagem mock da conversa 20',
          timestamp: String(Date.now() - 3600000)
        },
        message_count: 5,
        tags: ['mock', 'test']
      }
    ]

    console.log('Mock data sample:')
    console.log(JSON.stringify(mockData[0], null, 2))

    console.log('\nReal data structure (not working):')
    if (this.items.length > 0) {
      console.log('Real data sample:')
      console.log(JSON.stringify(this.items[0], null, 2))

      console.log('\n🔍 Key differences analysis:')
      const mock = mockData[0]
      const real = this.items[0]

      console.log(`conversation_id type: mock=${typeof mock.conversation_id}, real=${typeof real.conversation_id}`)
      console.log(`created_at type: mock=${typeof mock.created_at}, real=${typeof real.created_at}`)
      console.log(`updated_at type: mock=${typeof mock.updated_at}, real=${typeof real.updated_at}`)
      console.log(`message_count type: mock=${typeof mock.message_count}, real=${typeof real.message_count}`)

      if (real.last_message) {
        console.log(`last_message.timestamp type: mock=${typeof mock.last_message?.timestamp}, real=${typeof real.last_message.timestamp}`)
      }
    } else {
      console.log('No real data available for comparison')
    }

    console.log('=====================================')


    // Test with current date
    const today = new Date().toISOString().split('T')[0]
    console.log('🧪 Setting startDate to today:', today)
    this.startDate = today
    this.applyFilters()

    setTimeout(() => {
      console.log('🧪 Clearing startDate')
      this.startDate = undefined
      this.applyFilters()
    }, 1000)
  }

  // Debug method to test with specific user ID
  debugTestWithUserId() {
    console.log('🧪 DEBUG: Testing with specific user ID')

    // Test with user ID 1 (common test user)
    const testUserId = '1'
    console.log('🧪 Loading conversations with user_id:', testUserId)

    this.loading = true
    this.error = null

    const params = {
      user_id: testUserId,
      project_id: this.projectId || undefined
    }

    this.api.listConversations(params).subscribe({
      next: (resp: ConversationsListResponse) => {
        console.log('✅ DEBUG: API response with user_id 1')
        console.log('📊 Response data:', {
          conversationsCount: resp.conversations?.length || 0,
          hasConversations: !!resp.conversations,
          firstConversation: resp.conversations?.[0]
        })

        this.items = (resp.conversations || []).slice()
        this.applyFilters()
        this.loading = false

        console.log('✅ DEBUG: Test completed successfully')
      },
      error: (err) => {
        console.error('❌ DEBUG: API error with user_id 1', err)
        this.error = 'Falha ao carregar conversas com user_id 1'
        this.loading = false
      }
    })
  }

  // Debug method to test with multiple user IDs
  debugTestMultipleUserIds() {
    console.log('🧪 DEBUG: Testing with multiple user IDs')

    const testUserIds = ['1', '2', 'current-user', 'admin']
    let currentIndex = 0

    const testNextUser = () => {
      if (currentIndex >= testUserIds.length) {
        console.log('✅ DEBUG: All user ID tests completed')
        return
      }

      const userId = testUserIds[currentIndex]
      console.log(`🧪 Testing user_id: ${userId} (${currentIndex + 1}/${testUserIds.length})`)

      this.loading = true
      this.error = null

      const params = {
        user_id: userId,
        project_id: this.projectId || undefined
      }

      this.api.listConversations(params).subscribe({
        next: (resp: ConversationsListResponse) => {
          console.log(`✅ DEBUG: User ${userId} returned ${resp.conversations?.length || 0} conversations`)

          if (resp.conversations && resp.conversations.length > 0) {
            console.log('📋 First conversation:', {
              id: resp.conversations[0].conversation_id,
              title: resp.conversations[0].title,
              updated_at: resp.conversations[0].updated_at
            })
          }

          currentIndex++
          this.loading = false

          // Test next user after a short delay
          setTimeout(testNextUser, 500)
        },
        error: (err) => {
          console.error(`❌ DEBUG: API error with user_id ${userId}:`, err)
          currentIndex++
          this.loading = false

          // Continue with next user even if this one failed
          setTimeout(testNextUser, 500)
        }
      })
    }

    testNextUser()
  }

  // Debug method to test with NO filters (show all conversations)
  debugTestNoFilters() {
    console.log('🧪 DEBUG: Testing with NO filters - should show all conversations')

    this.loading = true
    this.error = null

    const params = {
      // No user_id, no project_id - should return all conversations
    }

    console.log('🧪 Making API call with NO filters:', params)

    this.api.listConversations(params).subscribe({
      next: (resp: ConversationsListResponse) => {
        console.log('✅ DEBUG: No filters test completed')
        console.log('📊 Raw response object:', resp)
        console.log('📊 Response data:', {
          conversationsCount: resp.conversations?.length || 0,
          hasConversations: !!resp.conversations,
          firstConversation: resp.conversations?.[0],
          conversationsType: typeof resp.conversations,
          isConversationsArray: Array.isArray(resp.conversations)
        })

        if (resp.conversations && resp.conversations.length > 0) {
          console.log('📋 All conversations returned:')
          resp.conversations.forEach((conv, index) => {
            console.log(`  [${index}] ID: ${conv.conversation_id}, Title: "${conv.title}", Updated: ${conv.updated_at}`)
          })
        }

        this.items = (resp.conversations || []).slice()
        this.applyFilters()
        this.loading = false

        console.log('✅ DEBUG: No filters test completed successfully')
      },
      error: (err) => {
        console.error('❌ DEBUG: API error with no filters:', err)
        this.error = 'Falha ao carregar conversas sem filtros'
        this.loading = false
      }
    })
  }

  // DEBUG METHOD - Test ID 20
  debugTestId20() {
    console.log('🐛 DEBUG: Testing navigation to ID 20...')
    console.log('🐛 DEBUG: Current router state:', this.router.url)
    console.log('🐛 DEBUG: Attempting navigation to /chat/20...')

    try {
      this.router.navigate(['/chat', '20']).then(
        success => {
          console.log('🐛 DEBUG: Navigation result:', success)
          if (success) {
            console.log('🐛 DEBUG: Navigation to ID 20 successful!')
          } else {
            console.log('🐛 DEBUG: Navigation to ID 20 failed!')
          }
        },
        error => {
          console.error('🐛 DEBUG: Navigation error:', error)
        }
      )
    } catch (err) {
      console.error('🐛 DEBUG: Exception during navigation:', err)
    }
  }

  // DEBUG METHOD - Clear date filters
  debugClearDateFilters() {
    console.log('🐛 DEBUG: Clearing date filters...')
    console.log('🐛 DEBUG: Before clear - startDate:', this.startDate, 'endDate:', this.endDate)

    this.startDate = undefined
    this.endDate = undefined

    console.log('🐛 DEBUG: After clear - startDate:', this.startDate, 'endDate:', this.endDate)
    console.log('🐛 DEBUG: Reapplying filters...')

    this.applyFilters()
  }

  // DEBUG METHOD - Load mock data to test frontend logic
  debugLoadMockData() {
    console.log('🐛 DEBUG: Loading mock data...')

    const mockConversations = [
      {
        conversation_id: '20',
        title: 'Conversa Mock ID 20',
        created_at: Date.now() - 86400000, // 1 day ago
        updated_at: Date.now() - 3600000,  // 1 hour ago
        last_message: {
          role: 'assistant',
          content: 'Esta é uma mensagem mock da conversa 20',
          timestamp: String(Date.now() - 3600000)
        },
        message_count: 5,
        tags: ['mock', 'test']
      },
      {
        conversation_id: '26',
        title: 'Conversa Mock ID 26',
        created_at: Date.now() - 172800000, // 2 days ago
        updated_at: Date.now() - 7200000,   // 2 hours ago
        last_message: {
          role: 'user',
          content: 'Esta é uma mensagem mock da conversa 26',
          timestamp: String(Date.now() - 7200000)
        },
        message_count: 3,
        tags: ['mock']
      }
    ]

    console.log('🐛 DEBUG: Mock conversations created:', mockConversations)

    // Set the mock data directly
    this.items = mockConversations
    console.log('🐛 DEBUG: Set items to mock data, length:', this.items.length)

    // Apply filters to see what happens
    this.applyFilters()
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

    // Check if it's a number or numeric string
    const num = Number(timestamp)
    if (!isNaN(num)) {
      // If timestamp is small (e.g., < 100 billion), it's likely seconds (Python time.time())
      // 100 billion is year 5138 in seconds, but 1973 in milliseconds. 
      // Safe threshold: if less than year 2000 in ms (9.4e11), treat as seconds if > 0
      if (num < 946684800000) {
        return new Date(num * 1000)
      }
      return new Date(num)
    }

    // Try standard string parsing (ISO dates)
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
    // TODO: Implement export functionality
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
    return Math.min(this.page * this.pageSize, this.filteredCount)
  }
}
