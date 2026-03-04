import { expect, test } from '@playwright/test'

import { loginWithE2ECredentials, requireE2ECredentialsOrSkip } from './support/auth'

type ApiCall = { url: string; status: number; method: string }

const FAILED_API_ALLOWLIST: RegExp[] = [
  /\/api\/v1\/auth\/local\/me/i,
]

function isAllowlistedFailure(api: ApiCall): boolean {
  if (api.status !== 401) return false
  return FAILED_API_ALLOWLIST.some((pattern) => pattern.test(api.url))
}

test.describe('E2E Smoke Test - API Health Check', () => {
  test('Deve logar e verificar saúde das APIs críticas', async ({ page }) => {
    const credentials = requireE2ECredentialsOrSkip()
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

    await loginWithE2ECredentials(page, credentials)
    await page.waitForTimeout(1500)

    const failedApis = apiCalls.filter((api) => api.status >= 400)
    const unexpectedFailedApis = failedApis.filter((api) => !isAllowlistedFailure(api))

    expect(
      unexpectedFailedApis,
      `Falhas inesperadas de API:\n${unexpectedFailedApis
        .map((api) => `${api.method} ${api.url} -> ${api.status}`)
        .join('\n')}`,
    ).toEqual([])

    await page.unrouteAll({ behavior: 'ignoreErrors' })
  })
})
