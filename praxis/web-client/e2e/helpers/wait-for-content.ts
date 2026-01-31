import { Page, Locator } from '@playwright/test';

/**
 * Options for waiting for content to be ready.
 */
export interface WaitForContentOptions {
    /** 
     * Selector for the main content area to wait for.
     * Default: '[data-testid="main-content"]' or component-specific fallback.
     */
    contentSelector?: string;

    /**
     * Additional loading indicator selectors to wait for (must disappear).
     * Merged with default indicators.
     */
    loadingIndicators?: string[];

    /**
     * Timeout in milliseconds.
     * Default: 15000
     */
    timeout?: number;
}

/**
 * Default loading indicator selectors used across the app.
 * These are common Angular Material and custom loading patterns.
 */
const DEFAULT_LOADING_INDICATORS = [
    '.loading-spinner',
    '.skeleton',
    'mat-progress-bar',
    'mat-spinner',
    '.animate-spin',           // Tailwind spinner class
    '.animate-pulse',          // Loading text pulse animation  
    '[class*="loading"]',      // Generic loading class patterns
];

/**
 * Waits for page content to be fully loaded and ready for interaction.
 * 
 * This utility addresses the "empty state detection" problem where navigation
 * elements appear before main content is rendered. It:
 * 1. Waits for all loading indicators to disappear
 * 2. Waits for the main content selector to become visible
 * 
 * @example
 * ```typescript
 * // In a PageObject after navigation:
 * await waitForContentReady(this.page, {
 *   contentSelector: 'app-workcell-dashboard',
 *   timeout: 15000
 * });
 * ```
 */
export async function waitForContentReady(
    page: Page,
    options: WaitForContentOptions = {}
): Promise<void> {
    const {
        contentSelector,
        loadingIndicators = [],
        timeout = 15000,
    } = options;

    // Merge default and custom loading indicators
    const allIndicators = [...DEFAULT_LOADING_INDICATORS, ...loadingIndicators];
    const indicatorSelector = allIndicators.join(', ');

    // Wait for all loading indicators to disappear
    const loadingElements = page.locator(indicatorSelector);

    try {
        // First check if any loading indicators are present
        const indicatorCount = await loadingElements.count();

        if (indicatorCount > 0) {
            // Wait for each visible indicator to disappear
            await loadingElements.first().waitFor({
                state: 'hidden',
                timeout
            });
        }
    } catch (e) {
        // Loading indicators may not be present at all, which is fine
        console.log('[waitForContentReady] No loading indicators found or already hidden');
    }

    // If a content selector was provided, wait for it to be visible
    if (contentSelector) {
        await page.locator(contentSelector).waitFor({
            state: 'visible',
            timeout
        });
    }
}

/**
 * Waits specifically for component loading state to complete.
 * Useful for components that use Angular signals for loading state.
 * 
 * @param page - Playwright Page
 * @param componentSelector - The component's root selector (e.g., 'app-workcell-dashboard')
 * @param options - Additional options
 */
export async function waitForComponentLoaded(
    page: Page,
    componentSelector: string,
    options: { timeout?: number } = {}
): Promise<void> {
    const { timeout = 15000 } = options;

    // Wait for the component to be present
    await page.locator(componentSelector).waitFor({
        state: 'visible',
        timeout
    });

    // Wait for any loading indicators within the component to disappear
    const componentLoadingIndicators = page.locator(componentSelector).locator('.animate-spin, .animate-pulse, mat-spinner');

    try {
        const count = await componentLoadingIndicators.count();
        if (count > 0) {
            await componentLoadingIndicators.first().waitFor({
                state: 'hidden',
                timeout: timeout / 2
            });
        }
    } catch {
        // No loading indicators or already hidden
    }
}

/**
 * Waits for the SQLite service to be ready.
 * This is a common prerequisite for pages that load data from IndexedDB/OPFS.
 * 
 * @param page - Playwright Page  
 * @param options - Timeout options
 */
export async function waitForDatabaseReady(
    page: Page,
    options: { timeout?: number; polling?: number } = {}
): Promise<void> {
    const { timeout = 15000, polling = 500 } = options;

    await page.waitForFunction(
        () => {
            const service = (window as any).sqliteService;
            if (!service) return false;

            // Check for Angular signal (function) or BehaviorSubject
            const isSignal = typeof service?.isReady === 'function';
            const hasGetValue = typeof service?.isReady$?.getValue === 'function';

            const value = isSignal
                ? service.isReady()
                : (hasGetValue ? service.isReady$.getValue() : undefined);

            return value === true;
        },
        null,
        { timeout, polling }
    );
}
