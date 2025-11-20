import { ComponentFixture, TestBed } from '@angular/core/testing'
import { ConversationsComponent } from './conversations'
import { JanusApiService } from '../../../services/janus-api.service'
import { LoadingStateService } from '../../../core/services/loading-state.service'
import { Router } from '@angular/router'
import { FormsModule } from '@angular/forms'
import { of, throwError } from 'rxjs'
import { SkeletonComponent } from '../../../shared/components/skeleton/skeleton.component'

class MockJanusApiService {
  listConversations(params?: any) {
    return of({
      conversations: [
        {
          conversation_id: 'conv1',
          title: 'Conversation 1',
          created_at: Date.parse('2024-01-01T00:00:00Z'),
          updated_at: Date.parse('2024-01-02T00:00:00Z'),
          last_message: { content: 'Hello world', role: 'user' }
        },
        {
          conversation_id: 'conv2',
          title: 'Conversation 2',
          created_at: Date.parse('2024-01-03T00:00:00Z'),
          updated_at: Date.parse('2024-01-04T00:00:00Z')
        }
      ]
    })
  }

  startChat(title: string) {
    return of({ conversation_id: 'new-conv' })
  }

  renameConversation(id: string, title: string) {
    return of({ success: true })
  }

  deleteConversation(id: string) {
    return of({ success: true })
  }
}

class MockLoadingStateService {
  private loadingStates = new Map<string, any>()

  startLoading(key: string, config?: any): void {
    this.loadingStates.set(key, { isLoading: true, ...config })
  }

  stopLoading(key: string): void {
    if (this.loadingStates.has(key)) {
      this.loadingStates.get(key).isLoading = false
    }
  }

  isKeyLoading(key: string): boolean {
    return this.loadingStates.has(key) && this.loadingStates.get(key).isLoading
  }
}

class MockRouter {
  navigate(commands: any[]) {
    return Promise.resolve(true)
  }
}

describe('ConversationsComponent', () => {
  let component: ConversationsComponent
  let fixture: ComponentFixture<ConversationsComponent>
  let apiService: MockJanusApiService
  let loadingState: MockLoadingStateService
  let router: MockRouter

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConversationsComponent, FormsModule, SkeletonComponent],
      providers: [
        { provide: JanusApiService, useClass: MockJanusApiService },
        { provide: LoadingStateService, useClass: MockLoadingStateService },
        { provide: Router, useClass: MockRouter }
      ]
    }).compileComponents()

    fixture = TestBed.createComponent(ConversationsComponent)
    component = fixture.componentInstance
    apiService = TestBed.inject(JanusApiService) as any
    loadingState = TestBed.inject(LoadingStateService) as any
    router = TestBed.inject(Router) as any
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  describe('initialization', () => {
    it('should load conversations on init', () => {
      spyOn(component, 'load').and.callThrough()
      component.ngOnInit()
      expect(component.load).toHaveBeenCalled()
    })

    it('should initialize with default values', () => {
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
    it('should load conversations successfully', () => {
      spyOn(apiService, 'listConversations').and.callThrough()
      spyOn(loadingState, 'startLoading').and.callThrough()
      spyOn(loadingState, 'stopLoading').and.callThrough()

      component.load()

      expect(loadingState.startLoading).toHaveBeenCalledWith('conversations', { message: 'Carregando conversas...' })
      expect(apiService.listConversations).toHaveBeenCalled()
      
      setTimeout(() => {
        expect(loadingState.stopLoading).toHaveBeenCalledWith('conversations')
        expect(component.items.length).toBe(2)
        expect(component.filtered.length).toBe(2)
        expect(component.error).toBe(null)
      }, 100)
    })

    it('should handle loading error', () => {
      spyOn(apiService, 'listConversations').and.returnValue(throwError(() => new Error('API Error')))
      spyOn(loadingState, 'stopLoading').and.callThrough()

      component.load()

      setTimeout(() => {
        expect(loadingState.stopLoading).toHaveBeenCalledWith('conversations')
        expect(component.error).toBe('Falha ao carregar conversas')
        expect(component.items.length).toBe(0)
      }, 100)
    })
  })

  describe('filtering', () => {
    beforeEach(() => {
      component.items = [
        {
          conversation_id: 'conv1',
          title: 'Angular Testing',
          created_at: Date.parse('2024-01-01T00:00:00Z'),
          updated_at: Date.parse('2024-01-02T00:00:00Z'),
          last_message: { content: 'Testing Angular components', role: 'user' }
        },
        {
          conversation_id: 'conv2',
          title: 'React Discussion',
          created_at: Date.parse('2024-01-03T00:00:00Z'),
          updated_at: Date.parse('2024-01-04T00:00:00Z'),
          last_message: { content: 'React hooks are great', role: 'user' }
        }
      ]
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
      expect(component.filtered[0].last_message?.content).toContain('hooks')
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
      component.items = [
        {
          conversation_id: 'conv1',
          title: 'Old Conversation',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          last_message: null
        },
        {
          conversation_id: 'conv2',
          title: 'New Conversation',
          created_at: '2024-01-15T00:00:00Z',
          updated_at: '2024-01-15T00:00:00Z',
          last_message: null
        }
      ]
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
      component.items = [
        {
          conversation_id: 'conv1',
          title: 'First',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-03T00:00:00Z',
          last_message: null
        },
        {
          conversation_id: 'conv2',
          title: 'Second',
          created_at: '2024-01-02T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          last_message: null
        }
      ]
    })

    it('should sort by updated_at desc by default', () => {
      component.applyFilters()
      
      expect(component.filtered[0].conversation_id).toBe('conv1')
      expect(component.filtered[1].conversation_id).toBe('conv2')
    })

    it('should sort by created_at asc', () => {
      component.sortKey = 'created_at'
      component.sortDir = 'asc'
      component.applyFilters()
      
      expect(component.filtered[0].conversation_id).toBe('conv1')
      expect(component.filtered[1].conversation_id).toBe('conv2')
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
      component.items = Array.from({ length: 25 }, (_, i) => ({
        conversation_id: `conv${i}`,
        title: `Conversation ${i}`,
        created_at: new Date(2024, 0, i + 1).toISOString(),
        updated_at: new Date(2024, 0, i + 1).toISOString(),
        last_message: null
      }))
      component.pageSize = 10
      component.applyFilters()
    })

    it('should show correct number of items per page', () => {
      expect(component.filtered.length).toBe(25)
      // First page
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
      component.page = 3 // Last page (items 21-25)
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
      component.items = [{
        conversation_id: 'conv1',
        title: 'Test Conversation',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z',
        last_message: null
      }]
      spyOn(window, 'prompt').and.returnValue('New Title')
      spyOn(window, 'confirm').and.returnValue(true)
    })

    it('should rename conversation', () => {
      spyOn(apiService, 'renameConversation').and.callThrough()
      spyOn(component, 'load').and.callThrough()

      component.rename(component.items[0])

      expect(window.prompt).toHaveBeenCalledWith('Novo título:', 'Test Conversation')
      expect(apiService.renameConversation).toHaveBeenCalledWith('conv1', 'New Title')
      // Should reload after successful rename
      setTimeout(() => {
        expect(component.load).toHaveBeenCalled()
      }, 100)
    })

    it('should not rename when prompt is cancelled', () => {
      spyOn(apiService, 'renameConversation')
      spyOn(window, 'prompt').and.returnValue(null)

      component.rename(component.items[0])

      expect(apiService.renameConversation).not.toHaveBeenCalled()
    })

    it('should delete conversation', () => {
      spyOn(apiService, 'deleteConversation').and.callThrough()
      spyOn(component, 'load').and.callThrough()

      component.remove(component.items[0])

      expect(window.confirm).toHaveBeenCalledWith('Excluir conversa?')
      expect(apiService.deleteConversation).toHaveBeenCalledWith('conv1')
      // Should reload after successful deletion
      setTimeout(() => {
        expect(component.load).toHaveBeenCalled()
      }, 100)
    })

    it('should not delete when confirmation is cancelled', () => {
      spyOn(apiService, 'deleteConversation')
      spyOn(window, 'confirm').and.returnValue(false)

      component.remove(component.items[0])

      expect(apiService.deleteConversation).not.toHaveBeenCalled()
    })
  })

  describe('startNew conversation', () => {
    it('should start new conversation successfully', () => {
      spyOn(apiService, 'startChat').and.callThrough()
      spyOn(router, 'navigate').and.callThrough()
      spyOn(loadingState, 'startLoading').and.callThrough()
      spyOn(loadingState, 'stopLoading').and.callThrough()

      component.startNew()

      expect(loadingState.startLoading).toHaveBeenCalledWith('start-new-conversation', { message: 'Iniciando nova conversa...' })
      expect(apiService.startChat).toHaveBeenCalledWith('Nova conversa')
      
      setTimeout(() => {
        expect(router.navigate).toHaveBeenCalledWith(['/chat', 'new-conv'])
        expect(loadingState.stopLoading).toHaveBeenCalledWith('start-new-conversation')
      }, 100)
    })

    it('should handle error when starting new conversation', () => {
      spyOn(apiService, 'startChat').and.returnValue(throwError(() => new Error('API Error')))
      spyOn(loadingState, 'stopLoading').and.callThrough()

      component.startNew()

      setTimeout(() => {
        expect(loadingState.stopLoading).toHaveBeenCalledWith('start-new-conversation')
        expect(component.error).toBe('Falha ao iniciar conversa')
      }, 100)
    })
  })

  describe('statusChip', () => {
    it('should return "Nova" for conversations without messages', () => {
      const conversation = {
        conversation_id: 'conv1',
        title: 'New Conversation',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        last_message: null
      }
      
      const status = component.statusChip(conversation)
      expect(status).toBe('Nova')
    })

    it('should return "Resolvida" for old conversations', () => {
      const oldDate = new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString() // 8 days ago
      const conversation = {
        conversation_id: 'conv1',
        title: 'Old Conversation',
        created_at: oldDate,
        updated_at: oldDate,
        last_message: { content: 'Old message', role: 'user' }
      }
      
      const status = component.statusChip(conversation)
      expect(status).toBe('Resolvida')
    })

    it('should return "Em andamento" for recent conversations with messages', () => {
      const recentDate = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString() // 2 days ago
      const conversation = {
        conversation_id: 'conv1',
        title: 'Recent Conversation',
        created_at: recentDate,
        updated_at: recentDate,
        last_message: { content: 'Recent message', role: 'user' }
      }
      
      const status = component.statusChip(conversation)
      expect(status).toBe('Em andamento')
    })
  })

  describe('open conversation', () => {
    it('should navigate to conversation', () => {
      spyOn(router, 'navigate').and.callThrough()
      
      const conversation = {
        conversation_id: 'conv123',
        title: 'Test Conversation',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z',
        last_message: null
      }
      
      component.open(conversation)
      
      expect(router.navigate).toHaveBeenCalledWith(['/chat', 'conv123'])
    })
  })
})