import { expect, test } from '@playwright/test'

const TEST_USER = {
  email: process.env.E2E_USER_EMAIL || 'arthur.paraiso.mar@gmail.com',
  password: process.env.TEST_PASSWORD || 'Kawai312967@',
}

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  await page.fill('input[type="email"]', TEST_USER.email)
  await page.fill('input[type="password"]', TEST_USER.password)
  const loginResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes('/auth/local/login') && response.request().method() === 'POST',
  )
  await page.click('button[type="submit"]')
  await loginResponsePromise
  await page.waitForTimeout(800)
}

test.describe('Demo Agentic Flow', () => {
  test('renderiza confirmação estruturada + citation_status (UX da demo)', async ({ page }) => {
    let convoId = 'demo-conv-1'

    await page.route('**/api/v1/chat/start', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ conversation_id: convoId }),
      })
    })

    await page.route('**/api/v1/chat/message', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          response:
            'Pedido classificado como alto risco. Confirme o objetivo e o escopo antes de seguir.',
          provider: 'janus',
          model: 'agent',
          role: 'assistant',
          conversation_id: convoId,
          citations: [],
          citation_status: {
            mode: 'required',
            status: 'missing_required',
            count: 0,
            reason: 'no_retrievable_sources',
          },
          understanding: {
            intent: 'action_request',
            summary: 'Executar deploy em produção',
            confidence: 0.81,
            confidence_band: 'high',
            requires_confirmation: true,
            confirmation_reason: 'high_risk',
            risk: {
              level: 'high',
              source: 'heuristic',
              summary: 'Ação classificada como alto risco; confirmação obrigatória.',
              requires_confirmation: true,
            },
            confirmation: {
              required: true,
              reason: 'high_risk',
              source: 'pending_actions_sql',
              pending_action_id: 123,
              approve_endpoint: '/api/v1/pending_actions/action/123/approve',
              reject_endpoint: '/api/v1/pending_actions/action/123/reject',
            },
          },
          confirmation: {
            required: true,
            reason: 'high_risk',
            source: 'pending_actions_sql',
            pending_action_id: 123,
          },
          agent_state: {
            state: 'waiting_confirmation',
            requires_confirmation: true,
            reason: 'high_risk',
          },
        }),
      })
    })

    await page.route('**/api/v1/pending_actions/action/123/approve', async (route) => {
      await route.fulfill({
        status: 202,
        contentType: 'application/json',
        body: JSON.stringify({
          source: 'sql',
          action_id: 123,
          status: 'approved',
          message: 'Action approved.',
          risk_level: 'high',
          risk_summary: 'Alto risco',
        }),
      })
    })

    await login(page)
    await page.goto('/conversations')
    await page.waitForTimeout(500)

    const streamingCheckbox = page.getByLabel('Streaming')
    if (await streamingCheckbox.count()) {
      const checked = await streamingCheckbox.isChecked()
      if (checked) await streamingCheckbox.click()
    }

    await page.getByRole('textbox', { name: /Descreva a tarefa/i }).fill('Fazer deploy em produção')
    await page.getByRole('button', { name: /Enviar/i }).click()

    await expect(page.getByText('Confirmação de ação')).toBeVisible()
    await expect(page.getByText('Ação classificada como alto risco; confirmação obrigatória.')).toBeVisible()
    await expect(page.getByText('Sem citação rastreável (obrigatória)')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Aprovar' })).toBeVisible()

    await page.getByRole('button', { name: 'Aprovar' }).click()
    await expect(page.getByText(/Ação pendente #123 aprovada/i)).toBeVisible()
  })

  test('fluxo real da demo (opcional, backend real)', async ({ page }) => {
    test.skip(process.env.E2E_DEMO_REAL !== '1', 'Set E2E_DEMO_REAL=1 para rodar com backend real')

    await login(page)
    await page.goto('/conversations')
    await page.waitForTimeout(1000)

    // Este teste depende de um prompt de ambiente que realmente gere pending action de risco.
    // Mantemos como smoke da fatia vertical real; a versão determinística acima valida a UX.
    await expect(page.getByRole('heading', { name: /Converse com o Janus/i })).toBeVisible()
  })
})

