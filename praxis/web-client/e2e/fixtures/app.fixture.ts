import { test as base, expect } from '@playwright/test';

/**
 * Custom Playwright fixture for parallel-safe E2E tests.
 * 
 * KEY FEATURES:
 * 1. Worker-indexed database isolation (each worker gets unique DB)
 * 2. Automatic dialog dismissal
 * 3. Overlay stabilization
 * 
 * Database Isolation:
 * - Uses `workerIndex` to create unique database files per worker
 * - Prevents OPFS contention in parallel test runs
 * - Each test navigates with `dbName=praxis-worker-{index}`
 */
export const test = base.extend({
    // Ensure each page navigation includes worker-specific DB
    page: async ({ page, browser }, use, testInfo) => {
        // Add init script to set localStorage flags before any navigation
        await page.addInitScript(() => {
            // Welcome dialog / Onboarding flags - set ALL possible variants
            localStorage.setItem('praxis_tour_finished', 'true');
            localStorage.setItem('praxis_onboarding_seen', 'true');
            localStorage.setItem('praxis_onboarding_complete', 'true');
            localStorage.setItem('praxis_onboarding_completed', 'true');
            localStorage.setItem('praxis_welcome_dialog_dismissed', 'true');
            localStorage.setItem('praxis_welcome_shown', 'true');
            localStorage.setItem('praxis_tutorial_completed', 'true');

            // Disable any pending tutorials
            localStorage.removeItem('praxis_pending_tutorial');

            // Common smoke test auth bypass
            if (!localStorage.getItem('auth_token')) {
                localStorage.setItem('auth_token', 'fake-smoke-token');
                localStorage.setItem('auth_user', JSON.stringify({
                    username: 'smoke_user',
                    email: 'smoke@test.com'
                }));
            }
        });

        await use(page);
    },
});

/**
 * Helper to build a worker-isolated URL.
 * Use this in tests that need to navigate with proper DB isolation.
 * @param resetdb - If true, wipes and reinitializes DB. Default false to reuse cached DB.
 */
export function buildIsolatedUrl(basePath: string, testInfo: { workerIndex: number }, resetdb = false): string {
    const dbName = `praxis-worker-${testInfo.workerIndex}`;
    const params = new URLSearchParams();
    params.set('mode', 'browser');
    params.set('dbName', dbName);
    if (resetdb) {
        params.set('resetdb', '1');
    }

    const separator = basePath.includes('?') ? '&' : '?';
    return `${basePath}${separator}${params.toString()}`;
}

/**
 * Helper to wait for SQLite service to be ready.
 * Uses data-testid attribute on app-root for clean detection.
 */
export async function waitForDbReady(page: import('@playwright/test').Page, timeout = 30000): Promise<void> {
    await page.locator('[data-sqlite-ready="true"]').waitFor({ state: 'attached', timeout });
}

test.beforeEach(async ({ page }, testInfo) => {
    // Build URL with worker-specific database
    const dbName = `praxis-worker-${testInfo.workerIndex}`;
    console.log(`[Fixture] Worker ${testInfo.workerIndex} initializing with DB: ${dbName}`);

    // Navigate to root to start the app sequence (no resetdb = reuse cached DB)
    await page.goto(`/?mode=browser&dbName=${dbName}`);

    // Wait for app shell to load (check for .sidebar-rail)
    await expect(page.locator('.sidebar-rail')).toBeVisible({ timeout: 30000 });

    // Wait for database to be ready
    await waitForDbReady(page);

    // Robust Welcome Dialog dismissal with retry logic
    const dismissWelcomeDialog = async (maxRetries = 3): Promise<void> => {
        for (let attempt = 0; attempt < maxRetries; attempt++) {
            const dialogVisible = await page.getByRole('dialog', { name: /Welcome to Praxis/i })
                .isVisible({ timeout: 1000 })
                .catch((e) => {
                    console.log('[Test] Silent catch (Welcome dialog isVisible):', e);
                    return false;
                });

            if (!dialogVisible) {
                return;
            }

            console.log(`[Fixture] Dismissing Welcome Dialog (attempt ${attempt + 1})...`);

            const buttonPatterns = [
                page.getByRole('button', { name: /Skip for Now/i }),
                page.getByRole('button', { name: /Close/i }),
                page.getByRole('button', { name: /Get Started/i }),
                page.getByRole('button', { name: /Dismiss/i }),
                page.locator('mat-dialog-actions button').first(),
            ];

            for (const btn of buttonPatterns) {
                if (await btn.isVisible({ timeout: 500 }).catch((e) => {
                    console.log('[Test] Silent catch (Welcome dialog button isVisible):', e);
                    return false;
                })) {
                    await btn.click({ force: true });
                    await page.waitForLoadState('domcontentloaded');
                    break;
                }
            }

            const stillVisible = await page.getByRole('dialog', { name: /Welcome to Praxis/i })
                .isVisible({ timeout: 500 })
                .catch((e) => {
                    console.log('[Test] Silent catch (Welcome dialog stillVisible):', e);
                    return false;
                });

            if (!stillVisible) {
                return;
            }
        }
    };

    await dismissWelcomeDialog();

    // Wait for CDK overlays to clear (prevents click interception)
    await expect(page.locator('.cdk-overlay-backdrop')).not.toBeVisible({ timeout: 10000 });
});

export { expect };
