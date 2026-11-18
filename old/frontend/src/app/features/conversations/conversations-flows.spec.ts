import { provideZonelessChangeDetection, signal } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { of } from 'rxjs'
import { vi } from 'vitest'

import { AuthService } from '../../core/auth/auth.service'
import { BackendApiService } from '../../services/backend-api.service'
import { ConversationStateFacade } from './conversations-state.facade'
import { ConversationsAutonomyService } from './conversations-autonomy.service'
import { ConversationsContextService } from './conversations-context.service'
import { ConversationsDocsService } from './conversations-docs.service'
import { ConversationsMemoryService } from './conversations-memory.service'
import { ConversationsNoticeService } from './conversations-notice.service'
import { ConversationsRagService } from './conversations-rag.service'

describe('Conversation subflows', () => {
  let apiStub: any
  let state: ConversationStateFacade

  beforeEach(() => {
    apiStub = {
      documents: {
        listDocuments: vi.fn(() => of({ items: [] })),
        linkUrl: vi.fn(() => of({ status: 'ok' })),
        uploadDocument: vi.fn(() => of({ response: { status: 'ok' } })),
        searchDocuments: vi.fn(() => of({ results: [] })),
        deleteDocument: vi.fn(() => of({ ok: true }))
      },
      memory: {
        getMemoryTimeline: vi.fn(() => of([])),
        addGenerativeMemory: vi.fn(() => of({ ok: true })),
        getGenerativeMemories: vi.fn(() => of([]))
      },
      knowledge: {
        ragSearch: vi.fn(() => of({ answer: '', citations: [] })),
        ragUserChat: vi.fn(() => of({ answer: '', citations: [] })),
        ragUserChatV2: vi.fn(() => of({ results: [] })),
        ragProductivitySearch: vi.fn(() => of({ answer: '', citations: [] })),
        ragHybridSearch: vi.fn(() => of({ answer: '', citations: [] }))
      },
      autonomy: {
        getAutonomyStatus: vi.fn(() => of(null)),
        listGoals: vi.fn(() => of([])),
        createGoal: vi.fn(() => of({ id: 'g1', title: 'meta', status: 'pending' })),
        startAutonomy: vi.fn(() => of({ ok: true })),
        stopAutonomy: vi.fn(() => of({ ok: true })),
        updateGoalStatus: vi.fn(() => of({ id: 'g1', title: 'meta', status: 'completed' }))
      },
      tools: {
        getTools: vi.fn(() => of({ tools: [] }))
      },
      feedback: {
        thumbsUpFeedback: vi.fn(() => of({ message: 'ok' })),
        thumbsDownFeedback: vi.fn(() => of({ message: 'ok' }))
      },
      chat: {
        listConversations: vi.fn(() => of({ conversations: [] })),
        startChat: vi.fn(() => of({ conversation_id: 'c1' })),
        getChatHistoryPaginated: vi.fn(() => of({ conversation_id: 'c1', messages: [] })),
        getConversationTrace: vi.fn(() => of([]))
      }
    }

    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        {
          provide: AuthService,
          useValue: {
            user: signal({ id: 2, name: 'arthur' }),
            isAdmin: signal(true)
          }
        },
        {
          provide: BackendApiService,
          useValue: apiStub
        },
        ConversationsNoticeService,
        ConversationsAutonomyService,
        ConversationsContextService,
        ConversationsDocsService,
        ConversationsMemoryService,
        ConversationsRagService
      ]
    })

    state = TestBed.inject(ConversationStateFacade)
  })

  it('docs link requires url', () => {
    const docs = TestBed.inject(ConversationsDocsService)
    state.selectedId.set('c1')
    state.docLinkUrl.set('')

    docs.linkDocumentUrl()

    expect(state.docLinkError()).toBeTruthy()
    expect(apiStub.documents.linkUrl).not.toHaveBeenCalled()
  })

  it('docs link requires conversation selection', () => {
    const docs = TestBed.inject(ConversationsDocsService)
    state.selectedId.set(null)
    state.docLinkUrl.set('https://example.com')

    docs.linkDocumentUrl()

    expect(state.docLinkError()).toBeTruthy()
    expect(apiStub.documents.linkUrl).not.toHaveBeenCalled()
  })

  it('memory add requires content', () => {
    const memory = TestBed.inject(ConversationsMemoryService)
    state.memoryDraft.set('   ')

    memory.addMemory()

    expect(state.memoryAddError()).toBeTruthy()
    expect(apiStub.memory.addGenerativeMemory).not.toHaveBeenCalled()
  })

  it('rag query requires input', () => {
    const rag = TestBed.inject(ConversationsRagService)
    state.ragQuery.set('')

    rag.runRagQuery()

    expect(state.ragError()).toBeTruthy()
  })

  it('goal creation requires title', () => {
    const autonomy = TestBed.inject(ConversationsAutonomyService)
    state.goalCreateTitle.set('   ')

    autonomy.createGoal()

    expect(state.goalCreateError()).toBeTruthy()
    expect(apiStub.autonomy.createGoal).not.toHaveBeenCalled()
  })
})

