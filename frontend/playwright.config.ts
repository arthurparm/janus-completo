import { defineConfig, devices } from '@playwright/test';

const externalBaseUrl = process.env.E2E_BASE_URL;
const useExternalBaseUrl = Boolean(externalBaseUrl);

/**
 * See https://playwright.dev/documentation/test-configuration.
 */
export default defineConfig({
  testDir: './e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/documentation/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/documentation/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('')`. */
    baseURL: externalBaseUrl || 'http://localhost:4200',

    /* Collect trace when retrying the failed test. See https://playwright.dev/documentation/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: useExternalBaseUrl
    ? undefined
    : {
      command: 'npm run start',
      url: 'http://localhost:4200',
      reuseExistingServer: !process.env.CI,
      timeout: 120000, // 2 minutes to start Angular server
    },
});
