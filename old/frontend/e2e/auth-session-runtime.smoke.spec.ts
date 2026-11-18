import { writeFileSync } from 'node:fs'
import { expect, test, type Page } from '@playwright/test'

type ApiEvent = {
  method: string
  status: number
  url: string
  hasAuth: boolean
}

const API_FAILURE_ALLOWLIST: RegExp[] = []
const CONSOLE_WARNING_ALLOWLIST: RegExp[] = []
const CONSOLE_ERROR_ALLOWLIST: RegExp[] = []
const MAX_CHAT_RESPONSE_MS = Number(process.env.JANUS_CHAT_RUNTIME_E2E_MAX_MS || 60_000)
const TEST_TIMEOUT_MS = Math.max(180_000, MAX_CHAT_RESPONSE_MS + 90_000)
const OIDC_ACCESS_TOKEN = (process.env.JANUS_USER_ACCESS_TOKEN || '').trim()

function isAllowlisted(patterns: RegExp[], text: string): boolean {
  return patterns.some((pattern) => pattern.test(text))
}

async function expectAuthenticatedRoute(page: Page, path: string, expectedText: RegExp): Promise<void> {
  await page.goto(path)
  await expect(page).not.toHaveURL(/\/login/i)
  await expect(page.getByText(expectedText).first()).toBeVisible({ timeout: 30_000 })
  await expect.poll(() => page.evaluate(() => Boolean(sessionStorage.getItem('JANUS_AUTH_TOKEN')))).toBe(true)
}

async function readConversationHistory(page: Page, conversationId: string): Promise<{
  messages?: Array<{ role?: string; text?: string; delivery_status?: string; provider?: string; model?: string }>
}> {
  return page.evaluate(async (id) => {
    const token = sessionStorage.getItem('JANUS_AUTH_TOKEN')
    const response = await fetch(`/api/v1/chat/${id}/history/paginated?limit=80`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!response.ok) {
      throw new Error(`history request failed: ${response.status}`)
    }
    return response.json()
  }, conversationId)
}

test.describe.serial('Runtime OIDC session smoke', () => {
  test('restaura sessao OIDC e confirma chat real persistido', async ({ page }, testInfo) => {
    test.setTimeout(TEST_TIMEOUT_MS)
    test.skip(!OIDC_ACCESS_TOKEN, 'Defina JANUS_USER_ACCESS_TOKEN com um access token OIDC válido.')

    const suffix = Date.now().toString().slice(-8)
    const apiEvents: ApiEvent[] = []
    const consoleFailures: string[] = []
    let chatConversationId: string | null = null
    let streamResponseStatus: number | null = null

    page.on('console', (msg) => {
      const text = msg.text()
      if (msg.type() === 'error' && !isAllowlisted(CONSOLE_ERROR_ALLOWLIST, text)) {
        consoleFailures.push(`console:error ${text}`)
      }
      if (msg.type() === 'warning' && !isAllowlisted(CONSOLE_WARNING_ALLOWLIST, text)) {
        consoleFailures.push(`console:warning ${text}`)
      }
    })
    page.on('pageerror', (error) => {
      consoleFailures.push(`pageerror:${error.message}`)
    })
    page.on('response', (response) => {
      const url = response.url()
      if (!url.includes('/api/v1/')) return
      const request = response.request()
      apiEvents.push({
        method: request.method(),
        status: response.status(),
        url,
        hasAuth: Boolean(request.headers().authorization),
      })
      const streamMatch = url.match(/\/api\/v1\/chat\/stream\/([^/?#]+)/)
      if (streamMatch) {
        chatConversationId = streamMatch[1] || streamMatch[2] || chatConversationId
        streamResponseStatus = response.status()
      }
    })

    await page.addInitScript((token) => {
      sessionStorage.setItem('JANUS_AUTH_TOKEN', token)
    }, OIDC_ACCESS_TOKEN)
    await page.goto('/')

    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect(page).not.toHaveURL(/\/login/i)
    await expect(page.getByText(/O que vamos criar, analisar ou explorar hoje/i)).toBeVisible({
      timeout: 30_000,
    })
    await expect.poll(() => page.evaluate(() => Boolean(sessionStorage.getItem('JANUS_AUTH_TOKEN')))).toBe(true)

    await expectAuthenticatedRoute(page, '/conversations', /Converse com o Janus/i)
    await expectAuthenticatedRoute(page, '/tools', /Visibilidade de Ferramentas/i)
    await expectAuthenticatedRoute(page, '/observability', /Observability Dashboard/i)

    await page.goto('/admin/autonomia')
    await expect(page).toHaveURL(/\/$/)
    await expect(page).not.toHaveURL(/\/login/i)

    await page.goto('/conversations')
    await page.locator('textarea, input[placeholder*="mensagem" i], input[placeholder*="tarefa" i]').first()
      .fill('Responda apenas: OK smoke frontend')
    const chatStartedAt = Date.now()
    await page.getByRole('button', { name: /Enviar/i }).click()

    await expect.poll(() => chatConversationId, { timeout: 30_000 }).not.toBeNull()
    const conversationId = String(chatConversationId)
    expect(streamResponseStatus).toBe(200)

    await expect.poll(
      async () => {
        const history = await readConversationHistory(page, conversationId)
        const assistant = history.messages?.findLast((message) => message.role === 'assistant')
        return assistant?.text || ''
      },
      { timeout: MAX_CHAT_RESPONSE_MS },
    ).toContain('OK smoke frontend')
    const chatElapsedMs = Date.now() - chatStartedAt
    expect(chatElapsedMs).toBeLessThan(MAX_CHAT_RESPONSE_MS)

    const history = await readConversationHistory(page, conversationId)
    const assistant = history.messages?.findLast((message) => message.role === 'assistant')
    expect(history.messages?.some((message) => message.role === 'user')).toBe(true)
    expect(assistant?.text).toContain('OK smoke frontend')
    expect(assistant?.provider).toBeTruthy()
    expect(assistant?.model).toBeTruthy()
    expect(assistant?.delivery_status).toBe('completed')

    await expect(page).toHaveURL(new RegExp(`/conversations/${conversationId}$`))
    await expect(page.getByText(/OK smoke frontend/i).last()).toBeVisible()
    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect(page.getByText(/OK smoke frontend/i).last()).toBeVisible({ timeout: 30_000 })

    const memoryMarker = `memoria-runtime-${suffix}`
    const memoryContent = `${memoryMarker}: prefere respostas objetivas e auditaveis`
    await page.getByRole('button', { name: /Abrir painel avancado/i }).click()
    await page.getByRole('tab', { name: 'Cliente', exact: true }).click()
    await page.getByRole('tab', { name: 'Memoria', exact: true }).click()

    const memoryPanel = page.locator('#customer-tabpanel-memoria')
    await memoryPanel.getByPlaceholder(/Fato.*contexto importante/i).fill(memoryContent)
    await memoryPanel.getByPlaceholder(/Import.ncia 0-10/i).fill('8')
    await memoryPanel.locator('select').selectOption('semantic')

    const memoryAddStartedAt = Date.now()
    const memoryAddResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes('/api/v1/memory/generative') &&
        response.request().method() === 'POST',
      { timeout: 30_000 },
    )
    await memoryPanel.getByRole('button', { name: 'Adicionar', exact: true }).click()
    const memoryAddResponse = await memoryAddResponsePromise
    expect(memoryAddResponse.status()).toBe(200)
    await expect(memoryPanel.getByText(/Mem.ria adicionada/i)).toBeVisible({ timeout: 30_000 })

    await memoryPanel.getByPlaceholder(/prefer.ncias do cliente/i).fill(memoryMarker)
    const memorySearchResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes('/api/v1/memory/generative?') &&
        response.request().method() === 'GET',
      { timeout: 30_000 },
    )
    await memoryPanel.getByRole('button', { name: 'Buscar', exact: true }).click()
    const memorySearchResponse = await memorySearchResponsePromise
    expect(memorySearchResponse.status()).toBe(200)
    await expect(memoryPanel.getByText(memoryContent, { exact: true })).toBeVisible({ timeout: 30_000 })
    const memoryElapsedMs = Date.now() - memoryAddStartedAt

    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect(page.getByText(memoryContent, { exact: true })).toBeVisible({ timeout: 30_000 })

    const evidence = {
      conversation_id: conversationId,
      chat_elapsed_ms: chatElapsedMs,
      max_chat_response_ms: MAX_CHAT_RESPONSE_MS,
      test_timeout_ms: TEST_TIMEOUT_MS,
      stream_http_status: streamResponseStatus,
      provider: assistant?.provider || null,
      model: assistant?.model || null,
      delivery_status: assistant?.delivery_status || null,
      memory_marker: memoryMarker,
      memory_add_http_status: memoryAddResponse.status(),
      memory_search_http_status: memorySearchResponse.status(),
      memory_elapsed_ms: memoryElapsedMs,
      memory_persisted_after_reload: true,
      api_event_count: apiEvents.length,
      console_failure_count: consoleFailures.length,
      persisted_after_reload: true,
      checked_at: new Date().toISOString(),
    }
    const evidencePath = testInfo.outputPath('chat-runtime-evidence.json')
    writeFileSync(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`, 'utf8')
    await testInfo.attach('chat-runtime-evidence', {
      path: evidencePath,
      contentType: 'application/json',
    })

    const unexpectedApiFailures = apiEvents.filter((event) => {
      if (event.status < 400) return false
      return !isAllowlisted(API_FAILURE_ALLOWLIST, event.url)
    })
    expect(
      unexpectedApiFailures,
      `Falhas inesperadas de API:\n${unexpectedApiFailures
        .map((event) => `${event.method} ${event.url} -> ${event.status}`)
        .join('\n')}`,
    ).toEqual([])

    expect(
      consoleFailures,
      `Console warnings/errors nao-whitelisted:\n${consoleFailures.join('\n')}`,
    ).toEqual([])
  })
})
