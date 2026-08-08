import { TestBed } from '@angular/core/testing'
import { vi } from 'vitest'

import { AUTH_TOKEN_KEY } from './api.config'
import { ChatStreamService } from './chat-stream.service'
import { AppLoggerService } from '../core/services/app-logger.service'

function makeFakeToken(userId: number): string {
  const payload = btoa(JSON.stringify({ sub: String(userId) }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')
  return `header.${payload}.signature`
}

describe('ChatStreamService', () => {
  const encoder = new TextEncoder()

  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    TestBed.configureTestingModule({
      providers: [
        ChatStreamService,
        {
          provide: AppLoggerService,
          useValue: {
            debug: vi.fn(),
            info: vi.fn(),
            warn: vi.fn(),
            error: vi.fn(),
          },
        },
      ],
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    localStorage.clear()
    sessionStorage.clear()
  })

  it('envia o stream principal via POST com payload JSON e sem prompt na URL', async () => {
    sessionStorage.setItem(AUTH_TOKEN_KEY, makeFakeToken(7))
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => {
      const chunk = encoder.encode('event: done\ndata: {"conversation_id":"conv-1"}\n\n')
      return {
        ok: true,
        body: {
          getReader: () => ({
            read: vi.fn()
              .mockResolvedValueOnce({ value: chunk, done: false })
              .mockResolvedValueOnce({ value: undefined, done: true }),
          }),
        },
      } as Response
    })
    vi.stubGlobal('fetch', fetchMock)

    const service = TestBed.inject(ChatStreamService)
    service.start({
      conversationId: 'conv-1',
      text: 'segredo do usuario',
      role: 'orchestrator',
      priority: 'fast_and_cheap',
      projectId: 'project-1',
      knowledgeSpaceId: 'ks-1',
    })

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/v1/chat/stream/conv-1')
    expect(url).not.toContain('?')
    expect(url).not.toContain('segredo')
    expect(init.method).toBe('POST')
    expect(init.body).toBeTruthy()

    const payload = JSON.parse(String(init.body)) as Record<string, unknown>
    expect(payload).toMatchObject({
      message: 'segredo do usuario',
      role: 'orchestrator',
      priority: 'fast_and_cheap',
      project_id: 'project-1',
      knowledge_space_id: 'ks-1',
    })

    const headers = init.headers as Headers
    expect(headers.get('Authorization')).toContain('Bearer ')
    expect(headers.get('Accept')).toBe('text/event-stream')
    expect(headers.get('Content-Type')).toBe('application/json')
    expect(headers.get('Idempotency-Key')).toBe(headers.get('X-Request-ID'))
  })

  it('refaz retry com o mesmo payload estruturado sem query string', async () => {
    vi.useFakeTimers()
    sessionStorage.setItem(AUTH_TOKEN_KEY, makeFakeToken(8))
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => {
      return {
        ok: false,
        status: 500,
        text: vi.fn().mockResolvedValue(''),
      } as unknown as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(Math, 'random').mockReturnValue(0)

    const service = TestBed.inject(ChatStreamService)
    service.start({
      conversationId: 'conv-retry',
      text: 'prompt sensivel',
      role: 'orchestrator',
      priority: 'fast_and_cheap',
    })

    await vi.runAllTimersAsync()

    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
    const firstCall = fetchMock.mock.calls[0] as [string, RequestInit]
    const secondCall = fetchMock.mock.calls[1] as [string, RequestInit]

    for (const [url, init] of [firstCall, secondCall]) {
      expect(url).toContain('/v1/chat/stream/conv-retry')
      expect(url).not.toContain('?')
      expect(init.method).toBe('POST')
      expect(JSON.parse(String(init.body))).toMatchObject({
        message: 'prompt sensivel',
        role: 'orchestrator',
        priority: 'fast_and_cheap',
      })
    }
    const firstHeaders = firstCall[1].headers as Headers
    const secondHeaders = secondCall[1].headers as Headers
    expect(firstHeaders.get('Idempotency-Key')).toBeTruthy()
    expect(secondHeaders.get('Idempotency-Key')).toBe(
      firstHeaders.get('Idempotency-Key'),
    )
  })

  it('retoma o retry a partir do ultimo id SSE persistido', async () => {
    vi.useFakeTimers()
    sessionStorage.setItem(AUTH_TOKEN_KEY, makeFakeToken(9))
    let call = 0
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => {
      call += 1
      if (call === 1) {
        const chunk = encoder.encode('id: 7\nevent: token\ndata: {"text":"parte"}\n\n')
        return {
          ok: true,
          body: {
            getReader: () => ({
              read: vi.fn()
                .mockResolvedValueOnce({ value: chunk, done: false })
                .mockRejectedValueOnce(new Error('connection lost')),
            }),
          },
        } as unknown as Response
      }
      return {
        ok: true,
        body: {
          getReader: () => ({
            read: vi.fn().mockResolvedValueOnce({
              value: encoder.encode(
                'id: 8\nevent: done\ndata: {"conversation_id":"conv-cursor"}\n\n',
              ),
              done: false,
            }).mockResolvedValueOnce({ value: undefined, done: true }),
          }),
        },
      } as unknown as Response
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(Math, 'random').mockReturnValue(0)

    const service = TestBed.inject(ChatStreamService)
    service.start({
      conversationId: 'conv-cursor',
      text: 'continuar',
      role: 'orchestrator',
      priority: 'fast_and_cheap',
    })

    await vi.runAllTimersAsync()

    expect(fetchMock).toHaveBeenCalledTimes(2)
    const firstHeaders = (fetchMock.mock.calls[0][1] as RequestInit).headers as Headers
    const secondHeaders = (fetchMock.mock.calls[1][1] as RequestInit).headers as Headers
    expect(secondHeaders.get('Idempotency-Key')).toBe(
      firstHeaders.get('Idempotency-Key'),
    )
    expect(secondHeaders.get('Last-Event-ID')).toBe('7')
  })
})
