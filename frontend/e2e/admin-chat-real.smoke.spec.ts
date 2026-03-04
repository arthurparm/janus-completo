import { expect, test, type Locator, type Page } from '@playwright/test'

const E2E_USER_EMAIL = process.env.E2E_USER_EMAIL || ''
const E2E_USER_PASSWORD = process.env.E2E_USER_PASSWORD || process.env.TEST_PASSWORD || ''
const MAX_PENDING_ATTEMPTS = 2

const CONSOLE_ERROR_WHITELIST = [
  /\/api\/v1\/auth\/local\/me/i,
  /Failed to load resource: the server responded with a status of 401/i,
]

function isWhitelistedConsoleError(text: string): boolean {
  return CONSOLE_ERROR_WHITELIST.some((pattern) => pattern.test(text))
}

async function login(page: Page): Promise<void> {
  await page.goto('/login')
  await page.getByRole('textbox', { name: /Email de acesso/i }).fill(E2E_USER_EMAIL)
  await page.getByRole('textbox', { name: /Senha de acesso/i }).fill(E2E_USER_PASSWORD)
  const loginResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes('/auth/local/login') && response.request().method() === 'POST',
    { timeout: 30_000 },
  )
  await page.getByRole('button', { name: /ENTRAR NO JANUS/i }).click()
  const loginResponse = await loginResponsePromise
  expect(loginResponse.status()).toBe(200)
}

async function openFreshConversation(page: Page): Promise<void> {
  await page.goto('/conversations')
  await expect(page.getByRole('heading', { name: /Converse com o Janus/i })).toBeVisible({
    timeout: 30_000,
  })
  await expect(page.getByText('Modo Admin')).toBeVisible({ timeout: 20_000 })
  await page.getByRole('button', { name: /Nova conversa/i }).first().click()
  await expect(page).toHaveURL(/\/conversations\/[^/?#]+/, { timeout: 30_000 })
}

async function ensureAdvancedPanelOpen(page: Page): Promise<void> {
  const openAdvanced = page.getByRole('button', { name: /Abrir painel avancado|Abrir painel avançado/i })
  if (await openAdvanced.count()) {
    await openAdvanced.first().click()
    await expect(page.getByLabel('Streaming')).toBeVisible({ timeout: 10_000 })
  }
}

async function setStreamingMode(page: Page, enabled: boolean): Promise<void> {
  await ensureAdvancedPanelOpen(page)
  const streamingCheckbox = page.getByLabel('Streaming')
  if (enabled) {
    await streamingCheckbox.check({ force: true })
    await expect(streamingCheckbox).toBeChecked()
    return
  }
  await streamingCheckbox.uncheck({ force: true })
  await expect(streamingCheckbox).not.toBeChecked()
}

async function sendPrompt(page: Page, prompt: string): Promise<void> {
  await page.getByRole('textbox', { name: /Descreva a tarefa/i }).fill(prompt)
  await page.getByRole('button', { name: /Enviar/i }).click()
}

async function findPendingCard(page: Page): Promise<Locator | null> {
  const card = page.locator('.confirmation-card').filter({
    has: page.getByRole('button', { name: 'Aprovar' }),
  }).last()
  const visible = await card.isVisible({ timeout: 20_000 }).catch(() => false)
  return visible ? card : null
}

async function waitForPendingCardWithRetry(page: Page, prompt: string): Promise<Locator> {
  for (let attempt = 1; attempt <= MAX_PENDING_ATTEMPTS; attempt += 1) {
    await sendPrompt(page, prompt)
    const card = await findPendingCard(page)
    if (card) return card
  }

  const lastAssistant = await page.locator('.message.assistant .message-text').last().innerText().catch(() => '')
  throw new Error(
    `Nao foi possivel gerar confirmação pendente apos ${MAX_PENDING_ATTEMPTS} tentativas. Ultima resposta: ${lastAssistant}`,
  )
}

test.describe.serial('Admin chat real smoke', () => {
  test('executa fluxo real de stream + aprovar + rejeitar pendencias', async ({ page }) => {
    test.setTimeout(180_000)
    test.skip(
      !E2E_USER_EMAIL || !E2E_USER_PASSWORD,
      'Defina E2E_USER_EMAIL e E2E_USER_PASSWORD para executar smoke real.',
    )

    const nonWhitelistedConsoleErrors: string[] = []
    let sseRequestCount = 0
    const sseResponseContentTypes: string[] = []

    page.on('request', (req) => {
      const url = req.url()
      const isChatStreamPost = url.includes('/api/v1/chat/stream/') && req.method() === 'POST'
      const isChatEventsGet = /\/api\/v1\/chat\/[^/]+\/events/.test(url) && req.method() === 'GET'
      if (isChatStreamPost || isChatEventsGet) {
        sseRequestCount += 1
      }
    })
    page.on('response', (response) => {
      const url = response.url()
      const method = response.request().method()
      const isChatStreamPost = url.includes('/api/v1/chat/stream/') && method === 'POST'
      const isChatEventsGet = /\/api\/v1\/chat\/[^/]+\/events/.test(url) && method === 'GET'
      if (isChatStreamPost || isChatEventsGet) {
        sseResponseContentTypes.push(response.headers()['content-type'] || '')
      }
    })
    page.on('console', (msg) => {
      if (msg.type() !== 'error') return
      const text = msg.text()
      if (isWhitelistedConsoleError(text)) return
      nonWhitelistedConsoleErrors.push(text)
    })

    await login(page)
    await openFreshConversation(page)

    await setStreamingMode(page, true)
    await sendPrompt(page, 'Check de streaming E2E: responda com OK.')
    await expect
      .poll(() => sseRequestCount, { timeout: 60_000 })
      .toBeGreaterThan(0)
    if (sseResponseContentTypes.length) {
      const hasExpectedType = sseResponseContentTypes.some(
        (ct) => ct.includes('text/event-stream') || ct.includes('application/json'),
      )
      expect(hasExpectedType).toBe(true)
    }

    // Evita flake de capacidade SSE no ambiente de teste durante os passos de aprovação/rejeição.
    await setStreamingMode(page, false)

    const approvePrompt = 'Aprovação E2E: fazer deploy em produção agora sem janela de mudança.'
    const approveCard = await waitForPendingCardWithRetry(page, approvePrompt)
    await expect(approveCard).toContainText(/Confirmação de ação|Confirmacao de acao/i)
    await approveCard.getByRole('button', { name: 'Aprovar' }).click()
    await expect(page.getByText(/Ação pendente #\d+ aprovada/i)).toBeVisible({ timeout: 30_000 })

    const rejectPrompt = 'Rejeição E2E: aplicar manutenção crítica em produção imediatamente.'
    const rejectCard = await waitForPendingCardWithRetry(page, rejectPrompt)
    await rejectCard.getByRole('button', { name: 'Rejeitar' }).click()
    await expect(page.getByText(/Ação pendente #\d+ rejeitada/i)).toBeVisible({ timeout: 30_000 })

    expect(
      nonWhitelistedConsoleErrors,
      `Console errors nao-whitelisted:\n${nonWhitelistedConsoleErrors.join('\n')}`,
    ).toEqual([])
  })
})
