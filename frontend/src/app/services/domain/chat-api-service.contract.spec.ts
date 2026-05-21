import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'

import { ChatApiService } from './chat-api-service'
import { AppLoggerService } from '../../core/services/app-logger.service'

describe('ChatApiService (contract)', () => {
  let http: HttpTestingController
  let svc: ChatApiService

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        {
          provide: AppLoggerService,
          useValue: {
            debug: () => undefined,
            info: () => undefined,
            warn: () => undefined,
            error: () => undefined,
          },
        },
      ],
    })
    http = TestBed.inject(HttpTestingController)
    svc = TestBed.inject(ChatApiService)
  })

  afterEach(() => {
    http.verify()
  })

  it('startChat deve chamar POST /api/v1/chat/start com body coerente', () => {
    svc.startChat('Nova conversa', 'orchestrator', 'user-1', 'proj-1').subscribe()
    const req = http.expectOne('/api/v1/chat/start')
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({
      title: 'Nova conversa',
      persona: 'orchestrator',
      user_id: 'user-1',
      project_id: 'proj-1',
    })
    req.flush({ conversation_id: 'c1' })
  })

  it('sendChatMessage deve chamar POST /api/v1/chat/message e trimar conversation_id', () => {
    svc.sendChatMessage('  c1  ', 'oi', 'reasoner', 'high_quality', 30, 'user-1', 'proj-1').subscribe()
    const req = http.expectOne('/api/v1/chat/message')
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({
      conversation_id: 'c1',
      message: 'oi',
      role: 'reasoner',
      priority: 'high_quality',
      timeout_seconds: 30,
      user_id: 'user-1',
      project_id: 'proj-1',
    })
    req.flush({ response: 'ok' })
  })
})

