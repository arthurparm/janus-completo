import { CUSTOM_ELEMENTS_SCHEMA, provideZonelessChangeDetection, signal } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router'
import { BehaviorSubject, of } from 'rxjs'
import { vi } from 'vitest'

import { AuthService } from '../../core/auth/auth.service'
import { AgentEventsService } from '../../core/services/agent-events.service'
import { Header } from '../../core/layout/header/header'
import { ChatStreamService } from '../../services/chat-stream.service'
import { BackendApiService } from '../../services/backend-api.service'
import { ConversationsComponent } from './conversations'

describe('ConversationsComponent', () => {
  let routeParams$: BehaviorSubject<ReturnType<typeof convertToParamMap>>
  let routerNavigateSpy: ReturnType<typeof vi.fn>
  let apiStub: Record<string, ReturnType<typeof vi.fn>>

  beforeEach(async () => {
    routeParams$ = new BehaviorSubject(convertToParamMap({ conversationId: 'legacy' }))
    routerNavigateSpy = vi.fn()
    apiStub = {
      listConversations: vi.fn(() => of({ conversations: [] })),
      startChat: vi.fn(() => of({ conversation_id: 'fresh' })),
      getChatHistoryPaginated: vi.fn(() => of({ conversation_id: 'legacy', messages: [] })),
      listDocuments: vi.fn(() => of({ items: [] })),
      getMemoryTimeline: vi.fn(() => of([])),
      getAutonomyStatus: vi.fn(() => of(null)),
      listGoals: vi.fn(() => of([])),
      getTools: vi.fn(() => of({ tools: [] })),
      getConversationTrace: vi.fn(() => of([]))
    }

    await TestBed.configureTestingModule({
      imports: [ConversationsComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            user: signal({ id: 2, name: 'arthur' }),
            isAdmin: signal(true)
          }
        },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: routeParams$.asObservable()
          }
        },
        {
          provide: Router,
          useValue: {
            navigate: routerNavigateSpy
          }
        },
        {
          provide: AgentEventsService,
          useValue: {
            events$: of([]),
            connect: vi.fn(),
            disconnect: vi.fn()
          }
        },
        {
          provide: ChatStreamService,
          useValue: {
            status: vi.fn(() => of('idle')),
            typing: vi.fn(() => of(false)),
            partials: vi.fn(() => of()),
            done: vi.fn(() => of()),
            errors: vi.fn(() => of()),
            cognitive: vi.fn(() => of('')),
            toolStatus: vi.fn(() => of('')),
            start: vi.fn(),
            stop: vi.fn()
          }
        },
        {
          provide: BackendApiService,
          useValue: apiStub
        }
      ]
    })
      .overrideComponent(ConversationsComponent, {
        remove: { imports: [Header] },
        add: { schemas: [CUSTOM_ELEMENTS_SCHEMA] }
      })
      .compileComponents()
  })

  it('clears stale state and loads the new conversation when creating from an active thread', async () => {
    const fixture = TestBed.createComponent(ConversationsComponent)
    const component = fixture.componentInstance as any
    fixture.detectChanges()

    component.messages.set([
      { id: 'old-message', role: 'assistant', text: 'legacy state', timestamp: Date.now() }
    ])
    component.docs.set([{ doc_id: 'doc-legacy', chunks: 1, conversation_id: 'legacy' }])
    component.memoryUser.set([{ id: 'mem-legacy' }])

    await component.createConversation()

    expect(component.selectedId()).toBe('fresh')
    expect(component.messages()).toEqual([])
    expect(component.docs()).toEqual([])
    expect(component.memoryUser()).toEqual([])
    expect(apiStub.getChatHistoryPaginated).toHaveBeenCalledWith('fresh', { limit: 80, offset: 0 })
    expect(apiStub.listDocuments).toHaveBeenCalledWith('fresh', '2')
    expect(routerNavigateSpy).toHaveBeenCalledWith(['/conversations', 'fresh'], { replaceUrl: true })
  })
})
