import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  globalSetup: require.resolve('./e2e/global-setup'),
  timeout: 60000,  // 60s is sufficient with proper waits

  // Skip @slow tests in CI (JupyterLite/Pyodide = 180s+ WASM bootstrap)
  grepInvert: process.env.CI ? /@slow/ : undefined,
  testDir: './e2e/specs',
  outputDir: 'test-results/',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'list',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:4200',

    /* Collect trace on failure - provides comprehensive debugging context */
    trace: 'retain-on-failure',

    /* Record video on failure - helps visualize timing and interaction issues */
    video: 'retain-on-failure',

    /* Force Headless Mode */
    headless: true,

    /* Capture screenshot - on CI only on failure, locally always */
    screenshot: process.env.CI ? 'only-on-failure' : 'on',

    /* Standardized viewport for consistent AI-parseable screenshots */
    viewport: { width: 1920, height: 1080 },
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        headless: true
      },
    },
    {
      name: 'smoke',
      testMatch: /smoke\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        headless: true,
        viewport: { width: 1280, height: 720 },  // Smaller = faster rendering
        screenshot: 'off',  // Skip for speed runs
      },
      retries: 0,
      timeout: 30000, // Increased from 15s - DB init can take 1-2s
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'npm run start:browser -- --port 4200',
    url: 'http://localhost:4200',
    reuseExistingServer: true,
    timeout: 180000,
  },
});
