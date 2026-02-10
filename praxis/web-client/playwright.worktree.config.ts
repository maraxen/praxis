import { defineConfig, devices } from '@playwright/test';

/**
 * Worktree-specific config — targets port 4201 for the tooltip-sidebar-refactor branch.
 */
export default defineConfig({
    timeout: 60000,
    testDir: './e2e/specs',
    outputDir: 'test-results/',
    fullyParallel: true,
    forbidOnly: false,
    retries: 0,
    workers: 4,
    reporter: 'list',
    use: {
        baseURL: 'http://localhost:56106',
        trace: 'retain-on-failure',
        video: 'retain-on-failure',
        headless: true,
        screenshot: 'on',
        viewport: { width: 1920, height: 1080 },
    },
    projects: [
        {
            name: 'chromium',
            use: {
                ...devices['Desktop Chrome'],
                headless: true
            },
        },
    ],
    // No webServer block — we manage the dev server manually on 4201
});
