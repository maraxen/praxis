import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for GitHub Pages deployment testing.
 * 
 * This configuration tests the application as deployed to the /praxis/
 * subdirectory, simulating the actual GitHub Pages environment.
 * 
 * Prerequisites:
 *   1. Run: npm run build:gh-pages
 *   2. Run: ../../../scripts/simulate-ghpages.sh
 *   
 * Or the webServer config below will handle it automatically.
 * 
 * Usage:
 *   npx playwright test --config=playwright.ghpages.config.ts
 *   npx playwright test --config=playwright.ghpages.config.ts --headed
 */

export default defineConfig({
    testDir: './e2e',

    // Only run GH Pages specific tests and JupyterLite path tests
    testMatch: [
        /ghpages-.*\.spec\.ts/,
        /jupyterlite-.*\.spec\.ts/,
        /smoke\.spec\.ts/,
    ],

    // Serialize tests for stability with complex resource loading
    fullyParallel: false,
    workers: 1,

    // Allow retry for flaky network conditions
    retries: 1,

    // Extended timeout for Pyodide initialization
    timeout: 60000,

    // Use list reporter for clean CI output
    reporter: [
        ['list'],
        ['html', { outputFolder: 'test-results/ghpages-report' }],
    ],

    use: {
        // Base URL points to the /praxis/ subdirectory
        baseURL: 'http://localhost:8080/praxis/',

        // Capture artifacts for debugging
        trace: 'on-first-retry',
        screenshot: 'on',
        video: 'retain-on-failure',

        // Extended navigation timeout for cold starts
        navigationTimeout: 30000,
    },

    // Output directory for test artifacts
    outputDir: 'test-results/ghpages',

    projects: [
        {
            name: 'ghpages-chromium',
            use: {
                ...devices['Desktop Chrome'],
                // Ensure we test with the same headers GH Pages would have
                contextOptions: {
                    ignoreHTTPSErrors: true,
                },
            },
        },
        {
            name: 'ghpages-smoke',
            testMatch: /smoke\.spec\.ts/,
            use: {
                ...devices['Desktop Chrome'],
                contextOptions: {
                    ignoreHTTPSErrors: true,
                },
            },
        },
    ],

    // Web server configuration - can start the simulation automatically
    webServer: {
        command: '../../scripts/simulate-ghpages.sh --no-build',
        url: 'http://localhost:8080/praxis/',
        reuseExistingServer: !process.env.CI,
        timeout: 120000,
        stdout: 'pipe',
        stderr: 'pipe',
    },
});
