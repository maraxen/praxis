/**
 * Worker-scoped Database Fixture for Parallel Test Isolation
 *
 * Problem: OPFS (Origin Private File System) is origin-scoped, not context-scoped.
 * All parallel Playwright workers share the same OPFS directory (/praxis-data/).
 * This causes race conditions when multiple tests reset or access the database.
 *
 * Solution: Use Playwright's workerIndex to create isolated database files.
 * Each worker gets its own database: praxis-worker-0.db, praxis-worker-1.db, etc.
 *
 * Usage:
 * - Import { test, expect } from './fixtures/worker-db.fixture';
 * - Use test.use({ dbName: 'custom-name' }) to override per-project
 */

import { test as baseTest, expect, Page } from '@playwright/test';

/**
 * Extended test options with database configuration
 */
interface WorkerDbOptions {
    /** Custom database name (defaults to worker-indexed name) */
    dbName: string;
}

/**
 * Wait for SQLite service to be ready with the specified database
 */
async function waitForSqliteReady(page: Page, timeout = 10000): Promise<void> {
    await page.waitForFunction(
        () => {
            const service = (window as any).sqliteService;
            // Signal check first (isReady is a function in Angular signals)
            const isSignal = typeof service?.isReady === 'function';
            const hasGetValue = typeof service?.isReady$?.getValue === 'function';
            return isSignal
                ? service.isReady() === true
                : (hasGetValue && service.isReady$.getValue() === true);
        },
        null,
        { timeout }
    );
}

/**
 * Test-scoped fixtures
 */
interface TestFixtures {
    /** Worker index exposed to tests */
    workerIndex: number;
}

/**
 * Extended test fixture with worker-scoped database isolation
 */
export const test = baseTest.extend<TestFixtures, WorkerDbOptions>({
    // Test-scoped workerIndex - accessible in every test
    workerIndex: async ({ }, use, testInfo) => {
        await use(testInfo.workerIndex);
    },

    // Worker-scoped database name - unique per parallel worker
    dbName: [
        async ({ }, use, testInfo) => {
            // Create unique database name for this worker
            const workerDbName = `praxis-worker-${testInfo.workerIndex}`;
            console.log(
                `[WorkerDB] Worker ${testInfo.workerIndex} using database: ${workerDbName}`
            );
            await use(workerDbName);

            // Cleanup is handled by the test's resetdb=1 on next run
            // No explicit cleanup needed as each test navigates with resetdb=1
        },
        { scope: 'worker' },
    ],
});

/**
 * Helper to build URL with worker-specific database
 */
export function buildWorkerUrl(
    basePath: string,
    workerIndex: number,
    options: { resetdb?: boolean; mode?: string } = {}
): string {
    const { resetdb = false, mode = 'browser' } = options;
    const dbName = `praxis-worker-${workerIndex}`;

    const params = new URLSearchParams();
    params.set('mode', mode);
    params.set('dbName', dbName);
    if (resetdb) {
        params.set('resetdb', '1');
    }

    const separator = basePath.includes('?') ? '&' : '?';
    return `${basePath}${separator}${params.toString()}`;
}

/**
 * Helper to navigate with worker-specific database
 * Use this in tests instead of page.goto() for proper isolation
 */
export async function gotoWithWorkerDb(
    page: Page,
    path: string,
    testInfo: { workerIndex: number },
    options: { resetdb?: boolean; waitForDb?: boolean; timeout?: number; mode?: string } = {}
): Promise<void> {
    const { resetdb = false, waitForDb = true, timeout = 10000, mode = 'browser' } = options;

    const url = buildWorkerUrl(path, testInfo.workerIndex, { resetdb, mode });
    console.log(`[WorkerDB] Navigating to: ${url}`);

    await page.goto(url, { waitUntil: 'domcontentloaded' });

    if (waitForDb) {
        await waitForSqliteReady(page, timeout);
    }
}

export { expect };
