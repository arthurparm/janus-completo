import { expect, test } from '@playwright/test'

import { authenticateWithOidcToken, requireOidcAccessTokenOrSkip } from './support/auth'

type ApiCall = { url: string; status: number; method: string }

test.describe('E2E Smoke Test - API Health Check', () => {
  test('Deve logar e verificar saúde das APIs críticas', async ({ page }) => {
    const accessToken = requireOidcAccessTokenOrSkip()
    const apiCalls: ApiCall[] = []

    await page.route('**/api/v1/**', async (route) => {
      const response = await route.fetch()
      apiCalls.push({
        url: response.url(),
        status: response.status(),
        method: route.request().method(),
      })
      await route.fulfill({ response })
    })

    await authenticateWithOidcToken(page, accessToken)
    await page.waitForTimeout(1500)

    const failedApis = apiCalls.filter((api) => api.status >= 400)
    expect(
      failedApis,
      `Falhas inesperadas de API:\n${failedApis
        .map((api) => `${api.method} ${api.url} -> ${api.status}`)
        .join('\n')}`,
    ).toEqual([])

    await page.unrouteAll({ behavior: 'ignoreErrors' })
  })
})
