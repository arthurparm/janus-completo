import { expect, test } from '@playwright/test'

import { loginWithE2ECredentials, requireE2ECredentialsOrSkip } from './support/auth'

test.describe('E2E Integration - Core APIs Check', () => {
  test.beforeEach(async ({ page }) => {
    const credentials = requireE2ECredentialsOrSkip()
    await loginWithE2ECredentials(page, credentials)
    await page.waitForTimeout(800)
  })

  test('Deve validar endpoint de Autonomia (/autonomy/status)', async ({ request }) => {
    const response = await request.get('/api/v1/autonomy/status')
    expect(response.status()).toBe(200)
    const data = await response.json()

    expect(data).toHaveProperty('active')
    expect(data).toHaveProperty('config')
  })

  test('Deve validar endpoint de Tarefas (/tasks/health/rabbitmq)', async ({ request }) => {
    const response = await request.get('/api/v1/tasks/health/rabbitmq')
    expect(
      [200, 503],
      `Status inesperado em /tasks/health/rabbitmq: ${response.status()}`,
    ).toContain(response.status())

    if (response.status() === 200) {
      const data = await response.json()
      expect(data.status).toBe('healthy')
    }
  })

  test('Deve validar endpoint de Conhecimento (/knowledge/health)', async ({ request }) => {
    const response = await request.get('/api/v1/knowledge/health')
    expect(response.status()).toBe(200)
    const data = await response.json()

    expect(data).toHaveProperty('status')
    expect(data).toHaveProperty('neo4j_connected')
    expect(data).toHaveProperty('qdrant_connected')
  })
})
