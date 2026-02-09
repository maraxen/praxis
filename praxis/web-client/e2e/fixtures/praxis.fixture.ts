/**
 * Unified Praxis E2E test fixture.
 *
 * ALL specs should import { test, expect } from this file instead of
 * @playwright/test or worker-db.fixture. This provides:
 *
 * 1. Pre-seeded localStorage (bypasses splash/onboarding/tutorial)
 * 2. Consistent test isolation foundation
 * 3. Single source of truth for shared test setup
 *
 * When auth is added, this will be upgraded to use storageState
 * with a Playwright setup project.
 */
import { test as base, expect } from '@playwright/test';

export { expect };

export const test = base.extend({
    page: async ({ page }, use) => {
        // Pre-seed localStorage BEFORE any navigation.
        // This eliminates splash screen, welcome dialog, and tutorial prompts.
        await page.addInitScript(() => {
            localStorage.setItem('praxis_onboarding_completed', 'true');
            localStorage.setItem('praxis_tutorial_completed', 'true');
            localStorage.setItem('praxis_splash_dismissed', 'true');
        });
        await use(page);
    },
});
