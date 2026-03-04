import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { loginWithE2ECredentials, requireE2ECredentialsOrSkip } from './support/auth'

type FixtureConversation = {
  conversation_id: string
  title: string
  updated_at: number
  messages: Array<{ role: string; text: string; timestamp: number; [key: string]: unknown }>
}

const markdownHistoryFixture = JSON.parse(
  readFileSync(resolve(process.cwd(), 'e2e/fixtures/conversation-history-markdown.json'), 'utf8'),
) as FixtureConversation

test.describe('Demo Agentic Flow', () => {
  test('renderiza confirmação estruturada + citation_status (UX da demo)', async ({ page }) => {
    let convoId = 'demo-conv-1'
    let historyMessages: Array<{ role: string; text: string; timestamp: number; [key: string]: unknown }> = []
    const demoPrompt = 'Fazer deploy em produção'
    const assistantText = 'Pedido classificado como alto risco. Confirme o objetivo e o escopo antes de seguir.'
    const confirmationPayload = {
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
    }

    const persistConversationHistory = (promptText: string): void => {
      const now = Date.now()
      historyMessages = [
        { role: 'user', text: promptText, timestamp: now - 1000 },
        {
          role: 'assistant',
          text: assistantText,
          timestamp: now,
          ...confirmationPayload,
        },
      ]
    }

    await page.addInitScript(() => {
      localStorage.setItem('JANUS_AUTH_TOKEN', 'mock-token')
    })

    await page.route('**/api/v1/auth/local/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: '1',
          email: 'demo@janus.local',
          roles: ['admin'],
          display_name: 'Demo User',
        }),
      })
    })

    await page.route('**/api/v1/chat/conversations**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            conversation_id: convoId,
            title: 'Demo Conversa',
            updated_at: Date.now(),
            last_message: historyMessages[historyMessages.length - 1] || undefined,
          },
        ]),
      })
    })

    await page.route('**/api/v1/chat/*/history**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          conversation_id: convoId,
          messages: historyMessages,
        }),
      })
    })

    await page.route('**/api/v1/knowledge/stats**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
    })
    await page.route('**/api/v1/autonomy/status**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
    })
    await page.route('**/api/v1/reflexion/summary**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
    })
    await page.route('**/api/v1/memory/timeline**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    })
    await page.route('**/api/v1/documents/list**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    })
    await page.route('**/api/v1/autonomy/goals**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    })
    await page.route('**/api/v1/tools/**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tools: [] }) })
    })
    await page.route('**/api/v1/chat/*/events**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: 'event: connected\\ndata: {}\\n\\n',
      })
    })
    await page.route('**/api/v1/chat/stream/**', async (route) => {
      const url = new URL(route.request().url())
      const promptText = url.searchParams.get('message') || demoPrompt
      persistConversationHistory(promptText)

      const sse = [
        'event: start',
        '',
        'event: protocol',
        'data: {"version":"2025-11.v1","supports_partial":true}',
        '',
        `event: ack`,
        `data: {"conversation_id":"${convoId}"}`,
        '',
        'event: cognitive_status',
        'data: {"state":"thinking","timestamp":1}',
        '',
        'event: cognitive_status',
        'data: {"state":"waiting_confirmation","requires_confirmation":true,"reason":"high_risk","timestamp":2}',
        '',
        'event: partial',
        `data: ${JSON.stringify({ text: assistantText })}`,
        '',
        'event: done',
        `data: ${JSON.stringify({
          conversation_id: convoId,
          provider: 'janus',
          model: 'agent',
          citations: [],
          ...confirmationPayload,
        })}`,
        '',
      ].join('\n')
      await route.fulfill({ status: 200, contentType: 'text/event-stream', body: sse })
    })
    await page.route('**/api/v1/system/status**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ok' }) })
    })
    await page.route('**/api/v1/system/health/services**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ services: [] }) })
    })

    await page.route('**/api/v1/chat/start', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ conversation_id: convoId }),
      })
    })

    await page.route('**/api/v1/chat/message', async (route) => {
      persistConversationHistory(demoPrompt)
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          response: assistantText,
          provider: 'janus',
          model: 'agent',
          role: 'assistant',
          conversation_id: convoId,
          citations: [],
          ...confirmationPayload,
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

    await page.goto('/conversations')
    await page.waitForTimeout(800)

    const openAdvanced = page.getByRole('button', { name: /Abrir painel avançado|Abrir painel avancado/i })
    if (await openAdvanced.count()) {
      await openAdvanced.click()
      await page.waitForTimeout(400)
    }

    const streamingCheckbox = page.getByLabel('Streaming')
    if (await streamingCheckbox.count()) {
      await streamingCheckbox.uncheck({ force: true })
      await expect(streamingCheckbox).not.toBeChecked()
    }

    await page.getByRole('textbox', { name: /Descreva a tarefa/i }).fill(demoPrompt)
    await page.getByRole('button', { name: /Enviar/i }).click()

    const confirmationCard = page.locator('.confirmation-card').last()
    await expect(confirmationCard).toBeVisible({ timeout: 15_000 })
    await expect(confirmationCard).toContainText('Confirmação de ação', { timeout: 15_000 })
    await expect(page.getByText('Ação classificada como alto risco; confirmação obrigatória.')).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByText('Sem citação rastreável (obrigatória)')).toBeVisible()
    await page.getByRole('button', { name: 'Atualizar' }).click()
    await expect(confirmationCard).toBeVisible({ timeout: 15_000 })
    await expect(confirmationCard.getByRole('button', { name: 'Aprovar' })).toBeVisible()

    await confirmationCard.getByRole('button', { name: 'Aprovar' }).click()
    await expect(page.getByText(/Ação pendente #123 aprovada/i)).toBeVisible({ timeout: 15_000 })
  })

  test('fluxo real da demo (opcional, backend real)', async ({ page }) => {
    test.skip(process.env.E2E_DEMO_REAL !== '1', 'Set E2E_DEMO_REAL=1 para rodar com backend real')

    const credentials = requireE2ECredentialsOrSkip()
    await loginWithE2ECredentials(page, credentials)
    await page.goto('/conversations')
    await page.waitForTimeout(1000)

    // Este teste depende de um prompt de ambiente que realmente gere pending action de risco.
    // Mantemos como smoke da fatia vertical real; a versão determinística acima valida a UX.
    await expect(page.getByRole('heading', { name: /Converse com o Janus/i })).toBeVisible()
  })

  test('renderiza fixture de historico markdown sem artefatos', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('JANUS_AUTH_TOKEN', 'mock-token')
    })

    await page.route('**/api/v1/auth/local/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'fixture-user',
          email: 'fixture@janus.local',
          roles: ['admin'],
          display_name: 'Fixture User',
        }),
      })
    })

    await page.route('**/api/v1/chat/conversations**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            conversation_id: markdownHistoryFixture.conversation_id,
            title: markdownHistoryFixture.title,
            updated_at: markdownHistoryFixture.updated_at,
            last_message: markdownHistoryFixture.messages[markdownHistoryFixture.messages.length - 1],
          },
        ]),
      })
    })

    await page.route('**/api/v1/chat/*/history**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          conversation_id: markdownHistoryFixture.conversation_id,
          messages: markdownHistoryFixture.messages,
        }),
      })
    })

    await page.route('**/api/v1/knowledge/stats**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
    })
    await page.route('**/api/v1/autonomy/status**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
    })
    await page.route('**/api/v1/reflexion/summary**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
    })
    await page.route('**/api/v1/memory/timeline**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    })
    await page.route('**/api/v1/documents/list**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    })
    await page.route('**/api/v1/autonomy/goals**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    })
    await page.route('**/api/v1/tools/**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tools: [] }) })
    })
    await page.route('**/api/v1/chat/*/events**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: 'event: connected\\ndata: {}\\n\\n',
      })
    })

    await page.goto(`/conversations/${markdownHistoryFixture.conversation_id}`)
    await page.waitForTimeout(700)

    await expect(page.getByText('Status dos Componentes')).toBeVisible()
    await expect(page.locator('.message-text table')).toHaveCount(1)
    await expect(page.locator('.code-block-wrapper')).toHaveCount(1)

    const pageText = await page.locator('body').innerText()
    expect(pageText).not.toContain('[object Object]')
    expect(pageText).not.toContain(']undefined')
  })
})
