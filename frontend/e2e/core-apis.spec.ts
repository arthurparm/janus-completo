import { expect, test } from '@playwright/test'

import { requireOidcAccessTokenOrSkip } from './support/auth'

test.describe('E2E Integration - Core APIs Check', () => {
  test('valida identidade OIDC em /users/me', async ({ request }) => {
    const accessToken = requireOidcAccessTokenOrSkip()
    const response = await request.get('/api/v1/users/me', {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    expect(response.status()).toBe(200)
    const data = await response.json()
    expect(data).toHaveProperty('id')
  })

  test('valida status permitido ao perfil user', async ({ request }) => {
    const accessToken = requireOidcAccessTokenOrSkip()
    const response = await request.get('/api/v1/system/status/user', {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    expect(response.status()).toBe(200)
  })

  test('bloqueia endpoint control-plane no perfil user', async ({ request }) => {
    const accessToken = requireOidcAccessTokenOrSkip()
    const response = await request.get('/api/v1/autonomy/status', {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    expect(response.status()).toBe(404)
  })
})
