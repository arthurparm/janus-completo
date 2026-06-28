import { TestBed } from '@angular/core/testing'
import { provideHttpClient, withInterceptors } from '@angular/common/http'
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing'

import { ChatApiService } from './chat-api-service'
import { AppLoggerService } from '../../core/services/app-logger.service'
import { AUTH_TOKEN_KEY } from '../api.config'
import { authInterceptor } from '../../core/interceptors/auth.interceptor'

function makeFakeToken(userId: number): string {
  const payload = btoa(JSON.stringify({ user_id: userId }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')
  return `${payload}.ignored.signature`
}

describe('ChatApiService (contract)', () => {
  let http: HttpTestingController
  let svc: ChatApiService

  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
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
    localStorage.clear()
    sessionStorage.clear()
  })

  it('startChat deve chamar POST /api/v1/chat/start com body coerente', () => {
    svc.startChat('Nova conversa', 'orchestrator', 'proj-1').subscribe()
    const req = http.expectOne('/api/v1/chat/start')
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({
      title: 'Nova conversa',
      persona: 'orchestrator',
      project_id: 'proj-1',
    })
    req.flush({ conversation_id: 'c1' })
  })

  it('sendChatMessage deve chamar POST /api/v1/chat/message e trimar conversation_id', () => {
    svc.sendChatMessage('  c1  ', 'oi', 'reasoner', 'high_quality', 30, 'proj-1').subscribe()
    const req = http.expectOne('/api/v1/chat/message')
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({
      conversation_id: 'c1',
      message: 'oi',
      role: 'reasoner',
      priority: 'high_quality',
      timeout_seconds: 30,
      project_id: 'proj-1',
    })
    req.flush({ response: 'ok' })
  })

  it('deve anexar Bearer e nao enviar identidade legada nos endpoints criticos de chat', () => {
    const fakeToken = makeFakeToken(7)
    localStorage.setItem(AUTH_TOKEN_KEY, fakeToken)

    svc.startChat('Nova conversa').subscribe()
    const startReq = http.expectOne('/api/v1/chat/start')
    expect(startReq.request.headers.get('Authorization')).toBe(`Bearer ${fakeToken}`)
    expect(startReq.request.headers.has('X-User-Id')).toBe(false)
    startReq.flush({ conversation_id: 'c1' })

    svc.sendChatMessage('c1', 'oi').subscribe()
    const messageReq = http.expectOne('/api/v1/chat/message')
    expect(messageReq.request.headers.get('Authorization')).toBe(`Bearer ${fakeToken}`)
    expect(messageReq.request.headers.has('X-User-Id')).toBe(false)
    messageReq.flush({ response: 'ok' })

    svc.getChatHistoryPaginated('c1', { limit: 80, offset: 0 }).subscribe()
    const historyReq = http.expectOne('/api/v1/chat/c1/history/paginated?limit=80')
    expect(historyReq.request.headers.get('Authorization')).toBe(`Bearer ${fakeToken}`)
    expect(historyReq.request.headers.has('X-User-Id')).toBe(false)
    historyReq.flush({
      conversation_id: 'c1',
      messages: [],
      total_count: 0,
      has_more: false,
      limit: 80,
      offset: 0,
    })
  })

  it('getChatHistoryPaginated deve chamar /history/paginated e preservar metadados de paginação', () => {
    svc.getChatHistoryPaginated('conv-1', { limit: 80, offset: 0, before_ts: 123 }).subscribe((resp) => {
      expect(resp).toEqual({
        conversation_id: 'conv-1',
        messages: [
          {
            message_id: 'm1',
            role: 'assistant',
            text: 'ok',
            timestamp: 321,
            citations: undefined,
            citation_status: undefined,
            reasoning: undefined,
            ui: undefined,
            understanding: undefined,
            confirmation: undefined,
            agent_state: undefined,
            delivery_status: undefined,
            failure_classification: undefined,
            provider: undefined,
            model: undefined,
          },
        ],
        total_count: 1,
        has_more: false,
        next_offset: undefined,
        limit: 80,
        offset: 0,
      })
    })

    const req = http.expectOne('/api/v1/chat/conv-1/history/paginated?limit=80&before_ts=123')
    expect(req.request.method).toBe('GET')
    req.flush({
      conversation_id: 'conv-1',
      messages: [{ message_id: 'm1', role: 'assistant', text: 'ok', timestamp: 321 }],
      total_count: 1,
      has_more: false,
      next_offset: null,
      limit: 80,
      offset: 0,
    })
  })
})

