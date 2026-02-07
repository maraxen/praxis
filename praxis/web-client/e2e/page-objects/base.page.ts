import { Page, Locator, TestInfo, expect } from '@playwright/test';

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
    async goto(options: { waitForDb?: boolean; resetdb?: boolean; dbOverride?: string } = {}) {
        const { waitForDb = true, resetdb = false, dbOverride } = options;

        // Ensure we are using a valid URL for the constructor
        const currentUrl = this.page.url();
        const urlObj = currentUrl && currentUrl !== 'about:blank'
            ? new URL(currentUrl)
            : new URL('http://localhost:4200');

        // Use provided path or current path
        const basePath = this.url.startsWith('http') ? new URL(this.url).pathname : this.url;
        urlObj.pathname = basePath;

        const params = urlObj.searchParams;
        params.set('mode', 'browser');

        // Add worker-indexed database name for isolation
        if (dbOverride) {
            params.set('dbName', dbOverride);
        } else if (this.testInfo) {
            const dbName = `praxis-worker-${this.testInfo.workerIndex}`;
            params.set('dbName', dbName);
        }

        if (resetdb) {
            params.set('resetdb', '1');
        } else {
            params.delete('resetdb');
        }

        const finalUrl = urlObj.toString();

        // PRE-CONDITION: Mark onboarding as completed to avoid blocking splash screens
        await this.page.addInitScript(() => {
            window.localStorage.setItem('praxis_onboarding_completed', 'true');
        });

        await this.page.goto(finalUrl, { waitUntil: 'domcontentloaded' });

        // Wait for SQLite service ready signal - the definitive indicator that:
        // 1. OPFS initialized, 2. Worker active, 3. Schema migrated, 4. Seeding complete
        if (waitForDb && finalUrl.includes('mode=browser')) {
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
                { timeout: 30000, polling: 500 }  // Increased timeout to 30s
            );
        }
    }

    async getTitle(): Promise<string> {
        return await this.page.title();
    }

    /**
     * Dismisses the Welcome/Onboarding dialog if it appears.
     * Uses a short timeout as the dialog might not always be present.
     */
    async dismissWelcomeDialogIfPresent(): Promise<void> {
        // Wait a bit for potential dialog to appear (animations)
        await this.page.waitForTimeout(1000);

        const dialog = this.page.getByRole('dialog');
        const isVisible = await dialog.isVisible().catch(() => false);

        if (isVisible) {
            // Check if it's the welcome dialog
            const welcomeHeading = this.page.getByRole('heading', { name: /Welcome/i });
            const hasWelcome = await welcomeHeading.isVisible().catch(() => false);

            if (hasWelcome) {
                console.log('[BasePage] Welcome dialog detected, dismissing...');
                const skipButton = this.page.getByRole('button', { name: /Skip/i });
                const hasSkip = await skipButton.isVisible().catch(() => false);
                if (hasSkip) {
                    await skipButton.click();
                    // Wait for it to disappear
                    await expect(dialog).not.toBeVisible({ timeout: 5000 });
                }
            }
        }
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
