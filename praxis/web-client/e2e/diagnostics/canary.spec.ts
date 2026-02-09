/**
 * @canary Temporary diagnostic spec for validating E2E infrastructure fixes.
 *
 * NOT a CI smoke test — delete after stabilization is complete.
 * Run with: bunx playwright test canary.spec.ts --timeout=20000
 */
import { test, expect } from '@playwright/test';

test.describe('@canary Infrastructure Diagnostics', () => {
    test('splash bypass: localStorage is pre-seeded', async ({ page }) => {
        // This validates that the praxis.fixture addInitScript works
        await page.addInitScript(() => {
            localStorage.setItem('praxis_onboarding_completed', 'true');
            localStorage.setItem('praxis_tutorial_completed', 'true');
        });
        await page.goto('/app/home?mode=browser');
        // Should land on /app/home directly without splash redirect
        await expect(page).toHaveURL(/\/app\/home/, { timeout: 15_000 });
    });

    test('sidebar: .sidebar-rail is visible on /app/home', async ({ page }) => {
        await page.addInitScript(() => {
            localStorage.setItem('praxis_onboarding_completed', 'true');
            localStorage.setItem('praxis_tutorial_completed', 'true');
        });
        await page.goto('/app/home?mode=browser');
        await expect(page.locator('.sidebar-rail, .nav-rail').first()).toBeVisible({ timeout: 15_000 });
    });

    test('DB: [data-sqlite-ready] attaches within 15s', async ({ page }) => {
        await page.addInitScript(() => {
            localStorage.setItem('praxis_onboarding_completed', 'true');
        });
        await page.goto('/?mode=browser');
        await page.locator('[data-sqlite-ready="true"]').waitFor({
            state: 'attached',
            timeout: 15_000,
        });
    });

    test('protocols: at least one protocol card renders', async ({ page }) => {
        await page.addInitScript(() => {
            localStorage.setItem('praxis_onboarding_completed', 'true');
            localStorage.setItem('praxis_tutorial_completed', 'true');
        });
        await page.goto('/app/protocols?mode=browser');
        await page.locator('[data-sqlite-ready="true"]').waitFor({
            state: 'attached',
            timeout: 15_000,
        });
        await expect(page.locator('app-protocol-card, app-protocol-library, [data-testid="protocol-list"]').first()).toBeVisible({ timeout: 10_000 });
    });

    test('assets: asset table loads', async ({ page }) => {
        await page.addInitScript(() => {
            localStorage.setItem('praxis_onboarding_completed', 'true');
            localStorage.setItem('praxis_tutorial_completed', 'true');
        });
        await page.goto('/app/assets?mode=browser');
        await page.locator('[data-sqlite-ready="true"]').waitFor({
            state: 'attached',
            timeout: 15_000,
        });
        // Any content indicator — the table, a card list, or the asset component itself
        await expect(page.locator('app-asset-table, app-asset-list, table, [role="table"], .asset-grid, app-assets').first()).toBeVisible({ timeout: 10_000 });
    });
});
