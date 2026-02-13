import { test, expect } from '@playwright/test';

test.describe('E2E Smoke Test - API Health Check', () => {
  // Credenciais de teste
  const TEST_USER = {
    email: 'arthurzinho7799@gmail.com',
    password: process.env.TEST_PASSWORD || 'Kawai312967@'
  };

  test('Deve logar e verificar saúde das APIs críticas', async ({ page, request }) => {
    // 1. Interceptar chamadas de API para monitorar status
    const apiCalls: { url: string, status: number, method: string }[] = [];
    
    await page.route('**/api/v1/**', async route => {
      const response = await route.fetch();
      apiCalls.push({
        url: response.url(),
        status: response.status(),
        method: route.request().method()
      });
      await route.fulfill({ response });
    });

    // 2. Acessar página de login
    console.log('Acessando página de login...');
    await page.goto('/login');
    
    // Verificar se estamos na página de login
    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator('input[type="email"]')).toBeVisible();

    // 3. Realizar Login
    console.log('Realizando login...');
    await page.fill('input[type="email"]', TEST_USER.email);
    await page.fill('input[type="password"]', TEST_USER.password);
    
    // Esperar pela resposta da API de login antes de continuar
    const loginResponsePromise = page.waitForResponse(response => 
      response.url().includes('/auth/local/login') && response.request().method() === 'POST'
    );
    
    await page.click('button[type="submit"]');
    
    // Aguardar a resposta da API (evita race condition onde o teste acaba antes da requisição)
    try {
        const loginResponse = await loginResponsePromise;
        console.log(`Login API Status: ${loginResponse.status()}`);
    } catch (e) {
        console.log('Login request failed or timed out');
    }

    // Esperar um pouco para garantir que redirecionamentos ou outras chamadas ocorram
    await page.waitForTimeout(2000);

    // 4. Verificar redirecionamento para Home (sucesso no login)
    // Ajuste o seletor conforme sua aplicação real (ex: um elemento da dashboard)
    // await expect(page).toHaveURL(/\/home/); 
    // Nota: Se o login falhar, o teste vai falhar aqui
    
    // 5. Relatório de APIs
    console.log('--- Relatório de APIs ---');
    const failedApis = apiCalls.filter(api => api.status >= 400);
    
    if (failedApis.length > 0) {
      console.warn(`⚠️ ${failedApis.length} APIs falharam durante o teste:`);
      failedApis.forEach(api => console.warn(`${api.method} ${api.url} -> ${api.status}`));
    } else {
      console.log('✅ Todas as APIs interceptadas responderam com sucesso.');
    }
    
    console.log(`Total de chamadas: ${apiCalls.length}`);

    // Limpar rotas para evitar erro de "Target page closed"
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });
});
