import { TestBed } from '@angular/core/testing'
import { vi } from 'vitest'

import { AUTH_TOKEN_KEY } from '../../services/api.config'
import { AgentEventsService } from './agent-events.service'
import { AppLoggerService } from './app-logger.service'

function makeFakeToken(userId: number): string {
  const payload = btoa(JSON.stringify({ user_id: userId }))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')
  return `${payload}.ignored.signature`
}

describe('AgentEventsService', () => {
  const encoder = new TextEncoder()

  async function waitFor(condition: () => boolean): Promise<void> {
    for (let attempt = 0; attempt < 20; attempt += 1) {
      if (condition()) return
      await new Promise((resolve) => setTimeout(resolve, 0))
    }
  }

  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    TestBed.configureTestingModule({
      providers: [
        AgentEventsService,
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
    vi.unstubAllGlobals()
    localStorage.clear()
    sessionStorage.clear()
  })

  it('conecta com fetch autenticado e publica eventos SSE', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, makeFakeToken(7))
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => {
      const chunk = encoder.encode(
        'event: agent_event\ndata: {"task_id":"task-1","agent_role":"dev","event_type":"agent_event","content":"thinking","conversation_id":"conv-1","timestamp":123}\n\n'
      )
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

    const service = TestBed.inject(AgentEventsService)
    const received: Array<{ content: string; conversation_id: string }> = []
    service.events$.subscribe((event) => {
      received.push({ content: event.content, conversation_id: event.conversation_id })
    })

    service.connect('conv-1')
    await waitFor(() => received.length === 1)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toContain('/v1/chat/conv-1/events')
    const init = fetchMock.mock.calls[0][1] as RequestInit
    const headers = init.headers as Headers
    expect(headers.get('Authorization')).toContain('Bearer ')
    expect(received).toEqual([{ content: 'thinking', conversation_id: 'conv-1' }])
  })

  it('aborta a conexao atual ao desconectar', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, makeFakeToken(9))
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => {
      await new Promise(() => undefined)
      return new Response(null, { status: 200 })
    })
    vi.stubGlobal('fetch', fetchMock)

    const service = TestBed.inject(AgentEventsService)
    service.connect('conv-2')
    await new Promise((resolve) => setTimeout(resolve, 0))

    const init = fetchMock.mock.calls[0][1] as RequestInit
    const signal = init.signal as AbortSignal
    expect(signal.aborted).toBe(false)

    service.disconnect()

    expect(signal.aborted).toBe(true)
  })
})
