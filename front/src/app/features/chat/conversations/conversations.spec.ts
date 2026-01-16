import { ComponentFixture, TestBed } from '@angular/core/testing'
import { computed, signal } from '@angular/core'
import { Router } from '@angular/router'
import { of, Subject } from 'rxjs'
import { vi } from 'vitest'
import { ConversationsComponent } from './conversations'
import { ConversationStore, ConversationsFilter, ConversationsSort } from '../store/conversation.store'
import { JanusApiService, ConversationMeta } from '../../../services/janus-api.service'
import { ConversationRefreshService } from '../../../services/conversation-refresh.service'
import { DemoService } from '../../../core/services/demo.service'
import { UiService } from '../../../shared/services/ui.service'

class MockConversationStore {
  private _items = signal<ConversationMeta[]>([])
  private _loading = signal(false)
  private _error = signal<string | null>(null)
  private _filter = signal<ConversationsFilter>({
    query: '',
    status: '',
    startDate: undefined,
    endDate: undefined
  })
  private _sort = signal<ConversationsSort>({
    key: 'updated_at',
    direction: 'desc'
  })

  readonly items = this._items.asReadonly()
  readonly loading = this._loading.asReadonly()
  readonly error = this._error.asReadonly()
  readonly filter = this._filter.asReadonly()
  readonly sort = this._sort.asReadonly()

  readonly filteredConversations = computed(() => {
    const items = this._items()
    const filter = this._filter()
    const sort = this._sort()

    let result = items
    const q = filter.query.toLowerCase().trim()
    if (q) {
      result = result.filter(it => {
        const t = (it.title || '').toLowerCase()
        const c = (it.last_message?.text || '').toLowerCase()
        return t.includes(q) || c.includes(q)
      })
    }

    if (filter.startDate || filter.endDate) {
      const sd = filter.startDate ? Date.parse(filter.startDate) : undefined
      const ed = filter.endDate ? Date.parse(filter.endDate) : undefined

      result = result.filter(it => {
        const updatedAt = it.updated_at || it.created_at
        const val = Number(updatedAt || 0)
        if (!updatedAt) return false

        const startMatch = !sd || val >= sd
        const endMatch = !ed || val <= ed
        return startMatch && endMatch
      })
    }

    result = [...result].sort((a, b) => {
      let ka: string | number
      let kb: string | number

      if (sort.key === 'last_message_at') {
        ka = Date.parse(a.last_message_at || '')
        kb = Date.parse(b.last_message_at || '')
      } else if (sort.key === 'title') {
        ka = (a.title || '').toLowerCase()
        kb = (b.title || '').toLowerCase()
      } else if (sort.key === 'message_count') {
        ka = a.message_count || 0
        kb = b.message_count || 0
      } else {
        ka = Number(a[sort.key] || 0)
        kb = Number(b[sort.key] || 0)
      }

      if (ka > kb) return sort.direction === 'asc' ? 1 : -1
      if (ka < kb) return sort.direction === 'asc' ? -1 : 1
      return 0
    })

    return result
  })

  readonly totalCount = computed(() => this._items().length)
  readonly filteredCount = computed(() => this.filteredConversations().length)

  load = vi.fn((_projectId?: string) => {})
  setFilter = vi.fn((changes: Partial<ConversationsFilter>) => {
    this._filter.update(current => ({ ...current, ...changes }))
  })
  setSort = vi.fn((key: ConversationsSort['key']) => {
    this._sort.update(current => {
      if (current.key === key) {
        return { ...current, direction: current.direction === 'asc' ? 'desc' : 'asc' }
      }
      return { key, direction: 'desc' }
    })
  })
  removeConversation = vi.fn((id: string) => {
    this._items.update(items => items.filter(it => it.conversation_id !== id))
  })
  renameConversation = vi.fn((id: string, title: string) => {
    this._items.update(items => items.map(it => it.conversation_id === id ? { ...it, title } : it))
  })

  setItems(items: ConversationMeta[]) {
    this._items.set(items)
  }

  setSortState(sort: ConversationsSort) {
    this._sort.set(sort)
  }
}

class MockJanusApiService {
  startChat = vi.fn((title: string) => of({ conversation_id: 'new-conv' }))
}

class MockRouter {
  events = new Subject()
  navigate = vi.fn((_commands: any[]) => Promise.resolve(true))
  navigateByUrl = vi.fn((_url: string) => Promise.resolve(true))
}

class MockConversationRefreshService {
  refreshConversations = new Subject<void>()
}

class MockDemoService {
  isOffline = vi.fn(() => false)
}

class MockUiService {
  showConfirm = vi.fn(() => of(true))
}

describe('ConversationsComponent', () => {
  let component: ConversationsComponent
  let fixture: ComponentFixture<ConversationsComponent>
  let store: MockConversationStore
  let apiService: MockJanusApiService
  let router: MockRouter
  let demoService: MockDemoService
  let uiService: MockUiService

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConversationsComponent],
      providers: [
        { provide: ConversationStore, useClass: MockConversationStore },
        { provide: JanusApiService, useClass: MockJanusApiService },
        { provide: Router, useClass: MockRouter },
        { provide: ConversationRefreshService, useClass: MockConversationRefreshService },
        { provide: DemoService, useClass: MockDemoService },
        { provide: UiService, useClass: MockUiService }
      ]
    }).compileComponents()

    fixture = TestBed.createComponent(ConversationsComponent)
    component = fixture.componentInstance
    store = TestBed.inject(ConversationStore) as any
    apiService = TestBed.inject(JanusApiService) as any
    router = TestBed.inject(Router) as any
    demoService = TestBed.inject(DemoService) as any
    uiService = TestBed.inject(UiService) as any
  })

  it('should create', () => {
    fixture.detectChanges()
    expect(component).toBeTruthy()
  })

  describe('initialization', () => {
    it('should load conversations on init', () => {
      const loadSpy = vi.spyOn(component, 'load')
      fixture.detectChanges()
      expect(loadSpy).toHaveBeenCalled()
    })

    it('should initialize with default values', () => {
      fixture.detectChanges()
      expect(component.page).toBe(1)
      expect(component.pageSize).toBe(10)
      expect(component.sortKey).toBe('updated_at')
      expect(component.sortDir).toBe('desc')
      expect(component.q).toBe('')
      expect(component.projectId).toBe('')
      expect(component.loading).toBe(false)
      expect(component.error).toBe(null)
    })
  })

  describe('load method', () => {
    it('should call store.load when online', () => {
      component.load()
      expect(store.load).toHaveBeenCalledWith(undefined)
    })

    it('should skip load when offline', () => {
      demoService.isOffline.mockReturnValue(true)
      component.load()
      expect(store.load).not.toHaveBeenCalled()
    })
  })

  describe('filtering', () => {
    beforeEach(() => {
      store.setItems([
        {
          conversation_id: 'conv1',
          title: 'Angular Testing',
          created_at: Date.parse('2024-01-01T00:00:00Z'),
          updated_at: Date.parse('2024-01-02T00:00:00Z'),
          last_message: { text: 'Testing Angular components', role: 'user' }
        },
        {
          conversation_id: 'conv2',
          title: 'React Discussion',
          created_at: Date.parse('2024-01-03T00:00:00Z'),
          updated_at: Date.parse('2024-01-04T00:00:00Z'),
          last_message: { text: 'React hooks are great', role: 'user' }
        }
      ])
    })

    it('should filter by query in title', () => {
      component.q = 'Angular'
      component.applyFilters()

      expect(component.filtered.length).toBe(1)
      expect(component.filtered[0].title).toContain('Angular')
    })

    it('should filter by query in content', () => {
      component.q = 'hooks'
      component.applyFilters()

      expect(component.filtered.length).toBe(1)
      expect(component.filtered[0].last_message?.text).toContain('hooks')
    })

    it('should be case insensitive', () => {
      component.q = 'ANGULAR'
      component.applyFilters()

      expect(component.filtered.length).toBe(1)
      expect(component.filtered[0].title).toContain('Angular')
    })

    it('should reset page to 1 when filtering', () => {
      component.page = 3
      component.q = 'test'
      component.applyFilters()

      expect(component.page).toBe(1)
    })
  })

  describe('date filtering', () => {
    beforeEach(() => {
      store.setItems([
        {
          conversation_id: 'conv1',
          title: 'Old Conversation',
          created_at: Date.parse('2024-01-01T00:00:00Z'),
          updated_at: Date.parse('2024-01-01T00:00:00Z'),
          last_message: undefined
        },
        {
          conversation_id: 'conv2',
          title: 'New Conversation',
          created_at: Date.parse('2024-01-15T00:00:00Z'),
          updated_at: Date.parse('2024-01-15T00:00:00Z'),
          last_message: undefined
        }
      ])
    })

    it('should filter by start date', () => {
      component.startDate = '2024-01-10'
      component.applyFilters()

      expect(component.filtered.length).toBe(1)
      expect(component.filtered[0].title).toBe('New Conversation')
    })

    it('should filter by end date', () => {
      component.endDate = '2024-01-10'
      component.applyFilters()

      expect(component.filtered.length).toBe(1)
      expect(component.filtered[0].title).toBe('Old Conversation')
    })

    it('should filter by date range', () => {
      component.startDate = '2024-01-05'
      component.endDate = '2024-01-20'
      component.applyFilters()

      expect(component.filtered.length).toBe(1)
      expect(component.filtered[0].title).toBe('New Conversation')
    })
  })

  describe('sorting', () => {
    beforeEach(() => {
      store.setItems([
        {
          conversation_id: 'conv1',
          title: 'First',
          created_at: Date.parse('2024-01-01T00:00:00Z'),
          updated_at: Date.parse('2024-01-03T00:00:00Z'),
          last_message: undefined
        },
        {
          conversation_id: 'conv2',
          title: 'Second',
          created_at: Date.parse('2024-01-02T00:00:00Z'),
          updated_at: Date.parse('2024-01-01T00:00:00Z'),
          last_message: undefined
        }
      ])
    })

    it('should sort by updated_at desc by default', () => {
      expect(component.filtered[0].conversation_id).toBe('conv1')
      expect(component.filtered[1].conversation_id).toBe('conv2')
    })

    it('should request sort by created_at when key changes', () => {
      component.setSort('created_at')
      expect(store.setSort).toHaveBeenCalledWith('created_at')
    })

    it('should toggle sort direction', () => {
      expect(component.sortDir).toBe('desc')
      component.toggleDir()
      expect(component.sortDir).toBe('asc')
      component.toggleDir()
      expect(component.sortDir).toBe('desc')
    })
  })

  describe('pagination', () => {
    beforeEach(() => {
      store.setItems(Array.from({ length: 25 }, (_, i) => ({
        conversation_id: `conv${i}`,
        title: `Conversation ${i}`,
        created_at: Date.parse(new Date(2024, 0, i + 1).toISOString()),
        updated_at: Date.parse(new Date(2024, 0, i + 1).toISOString()),
        last_message: undefined
      })))
      component.pageSize = 10
      component.applyFilters()
    })

    it('should show correct number of items per page', () => {
      expect(component.filtered.length).toBe(25)
      const firstPageItems = component.filtered.slice(0, 10)
      expect(firstPageItems.length).toBe(10)
    })

    it('should navigate to next page', () => {
      expect(component.page).toBe(1)
      component.nextPage()
      expect(component.page).toBe(2)
    })

    it('should navigate to previous page', () => {
      component.page = 3
      component.prevPage()
      expect(component.page).toBe(2)
    })

    it('should disable next button on last page', () => {
      component.page = 3
      const canGoNext = (component.page * component.pageSize) < component.filtered.length
      expect(canGoNext).toBe(false)
    })

    it('should disable previous button on first page', () => {
      expect(component.page).toBe(1)
      const canGoPrev = component.page > 1
      expect(canGoPrev).toBe(false)
    })
  })

  describe('conversation actions', () => {
    beforeEach(() => {
      store.setItems([{
        conversation_id: 'conv1',
        title: 'Test Conversation',
        created_at: Date.parse('2024-01-01T00:00:00Z'),
        updated_at: Date.parse('2024-01-02T00:00:00Z'),
        last_message: undefined
      }])
    })

    it('should enter rename mode', () => {
      component.rename(component.items[0])
      expect(component.editingId).toBe('conv1')
      expect(component.newTitleTemp).toBe('Test Conversation')
    })

    it('should save rename', () => {
      component.rename(component.items[0])
      component.newTitleTemp = 'New Title'
      component.saveRename(component.items[0])
      expect(store.renameConversation).toHaveBeenCalledWith('conv1', 'New Title')
      expect(component.editingId).toBe(null)
      expect(component.newTitleTemp).toBe('New Title')
    })

    it('should remove conversation when confirmed', () => {
      uiService.showConfirm.mockReturnValue(of(true))
      component.remove(component.items[0])
      expect(uiService.showConfirm).toHaveBeenCalled()
      expect(store.removeConversation).toHaveBeenCalledWith('conv1')
    })

    it('should not remove conversation when confirmation is cancelled', () => {
      uiService.showConfirm.mockReturnValue(of(false))
      component.remove(component.items[0])
      expect(store.removeConversation).not.toHaveBeenCalled()
    })
  })

  describe('startNew conversation', () => {
    it('should start new conversation successfully', () => {
      component.startNew()
      expect(apiService.startChat).toHaveBeenCalledWith('Nova conversa')
      expect(router.navigate).toHaveBeenCalledWith(['/chat', 'new-conv'])
    })
  })

  describe('statusChip', () => {
    it('should return "Nova" for conversations without messages', () => {
      const conversation = {
        conversation_id: 'conv1',
        title: 'New Conversation',
        created_at: Date.parse(new Date().toISOString()),
        updated_at: Date.parse(new Date().toISOString()),
        last_message: undefined
      }

      const status = component.statusChip(conversation)
      expect(status).toBe('Nova')
    })

    it('should return "Resolvida" for old conversations', () => {
      const oldDate = new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString()
      const conversation = {
        conversation_id: 'conv1',
        title: 'Old Conversation',
        created_at: Date.parse(oldDate),
        updated_at: Date.parse(oldDate),
        last_message: { text: 'Old message', role: 'user' }
      }

      const status = component.statusChip(conversation)
      expect(status).toBe('Resolvida')
    })

    it('should return "Em andamento" for recent conversations with messages', () => {
      const recentDate = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString()
      const conversation = {
        conversation_id: 'conv1',
        title: 'Recent Conversation',
        created_at: Date.parse(recentDate),
        updated_at: Date.parse(recentDate),
        last_message: { text: 'Recent message', role: 'user' }
      }

      const status = component.statusChip(conversation)
      expect(status).toBe('Em andamento')
    })
  })

  describe('open conversation', () => {
    it('should navigate to conversation', () => {
      const conversation = {
        conversation_id: 'conv123',
        title: 'Test Conversation',
        created_at: Date.parse('2024-01-01T00:00:00Z'),
        updated_at: Date.parse('2024-01-02T00:00:00Z'),
        last_message: undefined
      }

      component.open(conversation)

      expect(router.navigate).toHaveBeenCalledWith(['/chat', 'conv123'])
    })
  })
})
