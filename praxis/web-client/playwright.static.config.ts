import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for FAST E2E testing using pre-built static bundle.
 * 
 * This is significantly faster and more stable than the dev server approach:
 *   - Pre-built bundle (no Vite cold start)
 *   - Simple static server (predictable startup)
 *   - Extended timeouts for SQLite WASM initialization
 *   - Serial execution option for stability
 * 
 * Usage:
 *   # Build and test (recommended workflow):
 *   npm run build:browser && npx playwright test --config=playwright.static.config.ts
 *   
 *   # Quick re-test without rebuild:
 *   npx playwright test --config=playwright.static.config.ts
 *   
 *   # Run specific test file:
 *   npx playwright test smoke.spec.ts --config=playwright.static.config.ts
 */

export default defineConfig({
    testDir: './e2e/specs',
    outputDir: 'test-results/static',

    // Parallel by default, but can be overridden for debugging
    fullyParallel: true,
    workers: process.env.CI ? 1 : undefined,

    // Extended timeout for WASM initialization (SQLite, Pyodide)
    timeout: 60000,

    // Retry for transient failures
    retries: process.env.CI ? 2 : 0,

    // Skip @slow tests unless explicitly requested
    grepInvert: process.env.RUN_SLOW_TESTS ? undefined : /@slow/,

    reporter: [
        ['list'],
        ['html', { outputFolder: 'test-results/static-report' }],
    ],

    use: {
        baseURL: 'http://localhost:8080',

        // Capture artifacts for debugging
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
        video: 'retain-on-failure',

        // Extended navigation timeout for initial load
        navigationTimeout: 30000,

        // Headless by default
        headless: true,

        // Standard viewport
        viewport: { width: 1920, height: 1080 },
    },

    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
        // Fast smoke project with smaller viewport
        {
            name: 'smoke',
            testMatch: /smoke\.spec\.ts/,
            use: {
                ...devices['Desktop Chrome'],
                viewport: { width: 1280, height: 720 },
            },
            retries: 0,
            timeout: 45000,
        },
    ],

    // Static server configuration
    // Uses 'serve' with COOP/COEP headers for SharedArrayBuffer support
    // Note: --single enables SPA mode (fallback to index.html)
    webServer: {
        command: `echo '{"headers":[{"source":"**/*","headers":[{"key":"Cross-Origin-Opener-Policy","value":"same-origin"},{"key":"Cross-Origin-Embedder-Policy","value":"require-corp"}]}]}' > /tmp/serve-static.json && npx -y serve dist/web-client/browser -l 8080 -c /tmp/serve-static.json --single`,
        url: 'http://localhost:8080',
        reuseExistingServer: !process.env.CI,
        timeout: 30000,
    },
});
