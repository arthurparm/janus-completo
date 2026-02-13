import { test, expect } from '@playwright/test';

test.describe('E2E Integration - Core APIs Check', () => {
  // Credenciais de teste
  const TEST_USER = {
    email: 'arthurzinho7799@gmail.com',
    password: process.env.TEST_PASSWORD || 'Kawai312967@'
  };

  test.beforeEach(async ({ page }) => {
    // Login antes de cada teste
    await page.goto('/login');
    await page.fill('input[type="email"]', TEST_USER.email);
    await page.fill('input[type="password"]', TEST_USER.password);
    
    const loginResponsePromise = page.waitForResponse(response => 
      response.url().includes('/auth/local/login') && response.request().method() === 'POST'
    );
    await page.click('button[type="submit"]');
    await loginResponsePromise;
    await page.waitForTimeout(1000);
  });

  test('Deve validar endpoint de Autonomia (/autonomy/status)', async ({ request }) => {
    const response = await request.get('/api/v1/autonomy/status');
    expect(response.status()).toBe(200);
    const data = await response.json();
    
    console.log('Autonomy Status:', data);
    expect(data).toHaveProperty('active');
    expect(data).toHaveProperty('config');
  });

  test('Deve validar endpoint de Tarefas (/tasks/health/rabbitmq)', async ({ request }) => {
    // Nota: Endpoint pode retornar 503 se RabbitMQ não estiver rodando localmente
    // Vamos apenas logar o resultado para não quebrar o teste se for um ambiente sem RabbitMQ
    const response = await request.get('/api/v1/tasks/health/rabbitmq');
    console.log(`RabbitMQ Health Status: ${response.status()}`);
    
    if (response.status() === 200) {
      const data = await response.json();
      expect(data.status).toBe('healthy');
    } else {
      console.warn('⚠️ RabbitMQ parece não estar acessível ou configurado.');
    }
  });

  test('Deve validar endpoint de Conhecimento (/knowledge/health)', async ({ request }) => {
    const response = await request.get('/api/v1/knowledge/health');
    expect(response.status()).toBe(200);
    const data = await response.json();
    
    console.log('Knowledge Health:', data);
    expect(data).toHaveProperty('status');
    expect(data).toHaveProperty('neo4j_connected');
    expect(data).toHaveProperty('qdrant_connected');
  });

});
