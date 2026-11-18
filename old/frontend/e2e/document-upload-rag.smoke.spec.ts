import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { expect, test } from '@playwright/test'
import { authenticateWithOidcToken, requireOidcAccessTokenOrSkip } from './support/auth'

// Fecha uma lacuna conhecida: upload -> indexacao -> busca RAG nunca foram
// validados de ponta a ponta contra o backend real (ver CHANGELOG.md, Ciclo 37,
// "Risco Residual"). Testes de contrato em qa/ mockam o KnowledgeService; este
// spec sobe um arquivo de verdade pela UI e confirma que o trecho indexado
// volta na busca por similaridade.

async function openFreshConversation(page: import('@playwright/test').Page): Promise<void> {
  await page.goto('/conversations')
  await expect(page.getByRole('heading', { name: /Converse com o Janus/i })).toBeVisible({
    timeout: 30_000,
  })
  await page.getByRole('button', { name: /Nova conversa/i }).first().click()
  await expect(page).toHaveURL(/\/conversations\/[^/?#]+/, { timeout: 30_000 })
}

async function openDocsTab(page: import('@playwright/test').Page): Promise<void> {
  const openAdvanced = page.getByRole('button', { name: /Abrir painel avancado|Abrir painel avançado/i })
  if (await openAdvanced.count()) {
    await openAdvanced.first().click()
  }
  await page.getByRole('tab', { name: 'Cliente' }).click()
  await page.getByRole('tab', { name: 'Docs' }).click()
  await expect(page.locator('#customer-tabpanel-docs')).toBeVisible({ timeout: 10_000 })
}

test.describe.serial('Document upload + RAG retrieval smoke', () => {
  test('upload real vira contexto pesquisavel por similaridade', async ({ page }) => {
    test.setTimeout(120_000)
    const accessToken = requireOidcAccessTokenOrSkip()

    const marker = `janus-e2e-marker-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const fixtureDir = join(tmpdir(), 'janus-e2e-fixtures')
    if (!existsSync(fixtureDir)) mkdirSync(fixtureDir, { recursive: true })
    const filePath = join(fixtureDir, `${marker}.txt`)
    writeFileSync(
      filePath,
      `Documento de smoke test do Janus.\nToken unico de verificacao: ${marker}\nEste arquivo existe apenas para provar que upload, indexacao e busca RAG funcionam de ponta a ponta.`,
      'utf-8',
    )

    await authenticateWithOidcToken(page, accessToken)
    await openFreshConversation(page)
    await openDocsTab(page)

    await page.locator('input[type="file"]').setInputFiles(filePath)
    await expect(page.getByText(marker.concat('.txt'))).toBeVisible({ timeout: 5_000 }).catch(() => {})
    await page.getByRole('button', { name: /^Upload$|Enviando\.\.\./ }).click()
    await expect(page.getByText('Upload concluído.')).toBeVisible({ timeout: 60_000 })

    // A indexacao (chunking + embeddings) roda apos o upload responder 200,
    // entao a busca pode nao encontrar nada nos primeiros segundos. A busca
    // e por similaridade (nao substring exata), entao outros documentos de
    // execucoes anteriores do smoke (mesmo texto-molde) podem aparecer junto;
    // o que importa e que o resultado do upload atual esteja presente.
    const searchInput = page.getByPlaceholder('Buscar por conteúdo/index...')
    const searchButton = page.getByRole('button', { name: 'Buscar', exact: true })
    const matchingResult = page.locator('.doc-search-item').filter({ hasText: marker })
    await expect(async () => {
      await searchInput.fill('')
      await searchInput.fill(marker)
      await searchButton.click()
      await expect(matchingResult.first()).toBeVisible({ timeout: 5_000 })
    }).toPass({ timeout: 60_000, intervals: [2_000] })
  })
})
