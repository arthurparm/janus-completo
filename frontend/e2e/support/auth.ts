import { expect, test, type Page } from '@playwright/test'

export type E2ECredentials = {
  email: string
  password: string
}

export function requireE2ECredentialsOrSkip(): E2ECredentials {
  const email = (process.env.E2E_USER_EMAIL || '').trim()
  const password = (process.env.E2E_USER_PASSWORD || '').trim()
  test.skip(!email || !password, 'Defina E2E_USER_EMAIL e E2E_USER_PASSWORD para rodar este teste.')
  return { email, password }
}

export async function loginWithE2ECredentials(page: Page, credentials: E2ECredentials): Promise<void> {
  await page.goto('/login')
  await page.fill('input[type="email"]', credentials.email)
  await page.fill('input[type="password"]', credentials.password)

  const loginResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes('/auth/local/login') && response.request().method() === 'POST',
    { timeout: 30_000 },
  )
  await page.click('button[type="submit"]')
  const loginResponse = await loginResponsePromise
  expect(loginResponse.status()).toBe(200)
}
