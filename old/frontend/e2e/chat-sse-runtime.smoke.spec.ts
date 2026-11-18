import { expect, test, type APIRequestContext } from '@playwright/test'
import { writeFileSync } from 'node:fs'

type ChatStartResponse = {
  conversation_id: string
}

type SseEvent = {
  event: string
  data: unknown
}

type DonePayload = {
  conversation_id?: string
  provider?: string
  model?: string
  citation_status?: {
    mode?: string
    status?: string
    count?: number
  }
  agent_state?: {
    state?: string
  }
}

type RuntimePreflight = {
  http_status: number
  status: string | null
  kernel_state: string | null
  degraded_dependency_count: number
  degraded_dependencies: string[]
}

const RUN_REAL_CHAT_E2E = process.env.JANUS_RUN_REAL_CHAT_E2E === 'true'
const OIDC_ACCESS_TOKEN = (process.env.JANUS_USER_ACCESS_TOKEN || '').trim()
const MAX_LIGHT_CHAT_MS = Number(process.env.JANUS_LIGHT_CHAT_E2E_MAX_MS || 35_000)
const TEST_TIMEOUT_MS = Math.max(60_000, MAX_LIGHT_CHAT_MS + 15_000)

function getStringField(value: unknown, field: string): string | null {
  if (!value || typeof value !== 'object' || !(field in value)) {
    return null
  }
  const fieldValue = (value as Record<string, unknown>)[field]
  return typeof fieldValue === 'string' ? fieldValue : null
}

function getNestedStringField(value: unknown, parent: string, field: string): string | null {
  if (!value || typeof value !== 'object' || !(parent in value)) {
    return null
  }
  return getStringField((value as Record<string, unknown>)[parent], field)
}

function getNestedRecord(value: unknown, parent: string, field: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || !(parent in value)) {
    return {}
  }
  const nested = (value as Record<string, unknown>)[parent]
  if (!nested || typeof nested !== 'object' || !(field in nested)) {
    return {}
  }
  const record = (nested as Record<string, unknown>)[field]
  return record && typeof record === 'object' ? (record as Record<string, unknown>) : {}
}

async function expectRuntimeAvailable(request: APIRequestContext): Promise<RuntimePreflight> {
  let response
  try {
    response = await request.get('/healthz', { timeout: 5_000 })
  } catch (error) {
    throw new Error(
      `Janus runtime indisponivel para smoke SSE: GET /healthz falhou antes do fluxo de chat. ` +
        `Verifique PC2 -> PC1, frontend na porta do E2E_BASE_URL e API backend. Causa: ${String(error)}`,
    )
  }

  if (!response.ok()) {
    const body = await response.text()
    throw new Error(
      `Janus runtime indisponivel para smoke SSE: GET /healthz retornou HTTP ${response.status()}. ` +
        `Corpo: ${body.slice(0, 500)}`,
    )
  }

  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    body = null
  }
  const degradedDependencies = Object.keys(
    getNestedRecord(body, 'dependencies', 'degraded_dependencies'),
  ).sort()

  return {
    http_status: response.status(),
    status: getStringField(body, 'status'),
    kernel_state: getNestedStringField(body, 'dependencies', 'kernel_state'),
    degraded_dependency_count: degradedDependencies.length,
    degraded_dependencies: degradedDependencies,
  }
}

function parseSseEvents(raw: string): SseEvent[] {
  return raw
    .split(/\r?\n\r?\n/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      const eventLine = block.split(/\r?\n/).find((line) => line.startsWith('event:'))
      const dataLine = block.split(/\r?\n/).find((line) => line.startsWith('data:'))
      const event = eventLine?.replace(/^event:\s*/, '').trim() || 'message'
      const dataText = dataLine?.replace(/^data:\s*/, '').trim() || ''
      let data: unknown = dataText
      if (dataText) {
        try {
          data = JSON.parse(dataText)
        } catch {
          data = dataText
        }
      }
      return { event, data }
    })
}

async function startConversation(
  request: APIRequestContext,
  token: string,
): Promise<ChatStartResponse> {
  const response = await request.post('/api/v1/chat/start', {
    headers: { Authorization: `Bearer ${token}` },
    data: { persona: 'assistant' },
  })

  expect(response.status()).toBe(200)
  return response.json() as Promise<ChatStartResponse>
}

test.describe('Runtime chat SSE smoke', () => {
  test('emite token e done para mensagem leve usando LLM real', async ({ request }, testInfo) => {
    test.setTimeout(TEST_TIMEOUT_MS)
    test.skip(
      !RUN_REAL_CHAT_E2E,
      'Defina JANUS_RUN_REAL_CHAT_E2E=true para executar smoke real com backend/Ollama.',
    )
    test.skip(!OIDC_ACCESS_TOKEN, 'Defina JANUS_USER_ACCESS_TOKEN com um access token OIDC válido.')

    const runtimePreflight = await expectRuntimeAvailable(request)
    expect(runtimePreflight.http_status).toBe(200)
    expect(runtimePreflight.status).toBe('ok')
    expect(runtimePreflight.kernel_state).toBe('healthy')
    expect(runtimePreflight.degraded_dependency_count).toBe(0)
    expect(runtimePreflight.degraded_dependencies).toEqual([])

    const conversation = await startConversation(request, OIDC_ACCESS_TOKEN)

    const start = Date.now()
    const response = await request.post(`/api/v1/chat/stream/${conversation.conversation_id}`, {
      headers: { Authorization: `Bearer ${OIDC_ACCESS_TOKEN}` },
      data: {
        message: 'Ola',
        role: 'orchestrator',
        priority: 'fast_and_cheap',
      },
      timeout: MAX_LIGHT_CHAT_MS,
    })
    const elapsedMs = Date.now() - start
    const raw = await response.text()
    const events = parseSseEvents(raw)
    const doneEvents = events.filter((event) => event.event === 'done')
    const errorEvents = events.filter((event) => event.event === 'error')
    const tokenEvents = events.filter((event) => event.event === 'token')
    const done = doneEvents.at(-1)?.data as DonePayload | undefined
    const evidence = {
      conversation_id: conversation.conversation_id,
      elapsed_ms: elapsedMs,
      max_light_chat_ms: MAX_LIGHT_CHAT_MS,
      test_timeout_ms: TEST_TIMEOUT_MS,
      http_status: response.status(),
      token_event_count: tokenEvents.length,
      done_event_count: doneEvents.length,
      error_event_count: errorEvents.length,
      provider: done?.provider || null,
      model: done?.model || null,
      citation_status: done?.citation_status || null,
      agent_state: done?.agent_state || null,
      runtime_preflight: runtimePreflight,
      checked_at: new Date().toISOString(),
    }
    const evidencePath = testInfo.outputPath('chat-sse-runtime-evidence.json')
    writeFileSync(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`, 'utf8')
    await testInfo.attach('chat-sse-runtime-evidence', {
      path: evidencePath,
      contentType: 'application/json',
    })

    expect(response.status()).toBe(200)
    expect(elapsedMs).toBeLessThan(MAX_LIGHT_CHAT_MS)
    expect(errorEvents, raw).toEqual([])
    expect(tokenEvents.length, raw).toBeGreaterThan(0)
    expect(done, raw).toBeTruthy()
    expect(done?.conversation_id).toBe(String(conversation.conversation_id))
    expect(done?.provider, raw).toBeTruthy()
    expect(done?.model, raw).toBeTruthy()
    expect(done?.citation_status?.status).toBe('not_applicable')
    expect(done?.agent_state?.state).toBe('completed')
  })
})
