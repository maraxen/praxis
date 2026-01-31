import { Page, Locator, TestInfo } from '@playwright/test';

/**
 * Base page object for E2E tests with worker-indexed DB isolation.
 * 
 * KEY CHANGE: Supports parallel test execution via worker-specific database files.
 * Each Playwright worker gets its own database (praxis-worker-{index}.db) to prevent
 * OPFS contention between parallel tests.
 */
export abstract class BasePage {
    protected page: Page;
    protected testInfo?: TestInfo;
    readonly url: string;

    /**
     * @param page - Playwright page
     * @param url - Base URL for this page
     * @param testInfo - Optional TestInfo for worker index (enables isolated DBs)
     */
    constructor(page: Page, url: string = '/', testInfo?: TestInfo) {
        this.page = page;
        this.url = url;
        this.testInfo = testInfo;
    }

    /**
     * Navigate to this page with proper mode and database isolation.
     * 
     * Database Isolation Strategy:
     * - If testInfo is provided, uses worker-indexed database name
     * - This prevents race conditions when tests run in parallel
     */
    async goto(options: { waitForDb?: boolean } = {}) {
        const { waitForDb = true } = options;
        let targetUrl = this.url;

        // Ensure mode=browser is set
        if (!targetUrl.includes('mode=')) {
            targetUrl += `${targetUrl.includes('?') ? '&' : '?'}mode=browser`;
        }

        // Add worker-indexed database name for isolation
        if (this.testInfo && !targetUrl.includes('dbName=')) {
            const dbName = `praxis-worker-${this.testInfo.workerIndex}`;
            targetUrl += `${targetUrl.includes('?') ? '&' : '?'}dbName=${dbName}`;
            console.log(`[BasePage] Worker ${this.testInfo.workerIndex} using DB: ${dbName}`);
        }

        // NOTE: resetdb is NOT added by default to preserve seeded data
        // Tests that need a fresh database should explicitly pass resetdb=1

        await this.page.goto(targetUrl, { waitUntil: 'domcontentloaded' });

        // Wait for SQLite service ready signal - the definitive indicator that:
        // 1. OPFS initialized, 2. Worker active, 3. Schema migrated, 4. Seeding complete
        if (waitForDb && targetUrl.includes('mode=browser')) {
            await this.page.waitForFunction(
                () => {
                    const service = (window as any).sqliteService;
                    const hasService = !!service;
                    // Signal check first (isReady is a function in Angular signals)
                    const isSignal = typeof service?.isReady === 'function';
                    const hasGetValue = typeof service?.isReady$?.getValue === 'function';
                    const value = isSignal
                        ? service.isReady()
                        : (hasGetValue ? service.isReady$.getValue() : undefined);

                    // Debug output visible in browser console
                    console.log('[E2E] DB Ready check:', { hasService, isSignal, hasGetValue, value });

                    return value === true;
                },
                null,
                { timeout: 15000, polling: 500 }  // Poll every 500ms with 15s max
            );
        }
    }

    async getTitle(): Promise<string> {
        return await this.page.title();
    }

    async waitForOverlay(options: { timeout?: number; dismissWithEscape?: boolean } = {}): Promise<void> {
        const { timeout = 10000, dismissWithEscape = true } = options;
        const overlay = this.page.locator('.cdk-overlay-backdrop');

        // Try to wait for overlay to disappear naturally
        try {
            await overlay.waitFor({ state: 'hidden', timeout });
        } catch (e) {
            console.log('[Test] Caught (Overlay check):', (e as Error).message);
            // Overlay didn't disappear in time
            if (dismissWithEscape) {
                console.log('[Base] Overlay persisted, attempting Escape key dismiss...');
                await this.page.keyboard.press('Escape');
                // Wait for overlay to hide after escape
                await overlay.waitFor({ state: 'hidden', timeout: 2000 }).catch((e) => {
                    console.log('[Test] Silent catch (Overlay still visible):', e);
                });
            }
        }
    }
}
