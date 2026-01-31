import { chromium, type FullConfig } from '@playwright/test';

/**
 * Global setup for Playwright tests.
 * 
 * SIMPLIFIED APPROACH (Parallel Test Compatible):
 * This setup ONLY verifies that the dev server is reachable.
 * Database initialization is deferred to individual tests via worker-indexed isolation.
 * 
 * WHY: OPFS is origin-scoped, not context-scoped. All parallel workers share the
 * same OPFS directory. Attempting to initialize a shared DB here causes race
 * conditions when multiple workers run simultaneously.
 * 
 * SOLUTION: Each test navigates with `dbName=praxis-worker-{index}` to create
 * isolated database files per worker.
 * 
 * @see e2e/fixtures/worker-db.fixture.ts
 */
export default async function globalSetup(config: FullConfig) {
    const { baseURL } = config.projects[0].use;
    const targetUrl = baseURL || 'http://localhost:4200';

    console.log(`[Global Setup] Verifying dev server is reachable at ${targetUrl}...`);
    const browser = await chromium.launch();
    const page = await browser.newPage();

    try {
        // Simple health check - just verify the server responds
        const response = await page.goto(targetUrl, {
            waitUntil: 'domcontentloaded',
            timeout: 30000
        });

        if (!response || response.status() >= 400) {
            throw new Error(
                `[Global Setup] Dev server returned error: ${response?.status() || 'no response'}`
            );
        }

        // Wait briefly for Angular to bootstrap
        await page.waitForSelector('app-root', { timeout: 15000 });

        // NOTE: Pre-warming OPFS here is ineffective because each Playwright worker gets
        // its own browser context with isolated OPFS. Tests must init their own DBs.

        console.log('[Global Setup] Success: Dev server is ready. Database init deferred to tests.');

    } catch (error) {
        console.error('[Global Setup] FATAL: Dev server not reachable');
        console.error(error);
        throw error;
    } finally {
        await browser.close();
    }
}
