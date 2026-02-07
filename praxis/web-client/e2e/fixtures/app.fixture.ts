/**
 * App Fixture — Core test fixture for Praxis E2E tests
 *
 * Re-exports test/expect from worker-db fixture and provides
 * utility functions for URL building and DB readiness.
 */

import { test, expect, buildWorkerUrl } from './worker-db.fixture';
import type { TestInfo, Page } from '@playwright/test';

/**
 * Build an isolated URL with worker-specific database params
 */
export function buildIsolatedUrl(
    basePath: string,
    testInfo: TestInfo,
    resetdb: boolean = false
): string {
    return buildWorkerUrl(basePath, testInfo.workerIndex, { resetdb });
}

/**
 * Wait for the SQLite database to be ready
 */
export async function waitForDbReady(page: Page, timeout = 60000): Promise<void> {
    await page.locator('[data-sqlite-ready="true"]').waitFor({
        state: 'attached',
        timeout
    });
}

export { test, expect };
