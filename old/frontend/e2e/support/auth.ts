import { expect, test, type Page } from '@playwright/test'

export function requireOidcAccessTokenOrSkip(): string {
  const token = (process.env.JANUS_USER_ACCESS_TOKEN || '').trim()
  test.skip(!token, 'Defina JANUS_USER_ACCESS_TOKEN com um access token OIDC válido.')
  return token
}

export async function authenticateWithOidcToken(page: Page, token: string): Promise<void> {
  await page.addInitScript((accessToken) => {
    sessionStorage.setItem('JANUS_AUTH_TOKEN', accessToken)
  }, token)
  const currentUser = page.waitForResponse(
    (response) => response.url().includes('/api/v1/users/me') && response.request().method() === 'GET',
    { timeout: 30_000 },
  )
  await page.goto('/')
  expect((await currentUser).status()).toBe(200)
}
