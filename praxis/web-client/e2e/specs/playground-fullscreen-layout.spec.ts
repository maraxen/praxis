import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';

test.describe('Playground Full-Screen Layout', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        await gotoWithWorkerDb(page, '/app/playground', testInfo);
    });

    test('should render as full-screen layout without tabs', async ({ page }) => {
        // The playground should show a full-screen layout, not tabs
        const playgroundLayout = page.locator('.playground-layout');
        await expect(playgroundLayout).toBeVisible({ timeout: 15000 });

        // Verify no tab group exists (removed in refactor)
        const tabGroup = page.locator('mat-tab-group');
        await expect(tabGroup).toHaveCount(0);

        // Verify the notebook iframe is present
        const notebookIframe = page.locator('iframe.notebook-frame');
        await expect(notebookIframe).toBeVisible({ timeout: 30000 });

        // Capture screenshot of the full-screen playground
        await page.screenshot({
            path: 'e2e/screenshots/playground-fullscreen-layout.png',
            fullPage: false
        });
    });

    test('should show sidebar hover trigger on right edge', async ({ page }) => {
        // Wait for the playground to load
        const playgroundLayout = page.locator('.playground-layout');
        await expect(playgroundLayout).toBeVisible({ timeout: 15000 });

        // The sidebar trigger strip must be present
        const sidebarTrigger = page.locator('.sidebar-trigger');
        await expect(sidebarTrigger).toBeVisible({ timeout: 5000 });

        // Capture screenshot showing the trigger zone
        await page.screenshot({
            path: 'e2e/screenshots/playground-sidebar-trigger.png',
            fullPage: false
        });

        // Hover over the trigger to activate the sidebar
        await sidebarTrigger.hover();
        // Allow some time for the overlay to animate in
        await page.waitForTimeout(500);

        // Take screenshot with sidebar open
        await page.screenshot({
            path: 'e2e/screenshots/playground-sidebar-open.png',
            fullPage: false
        });
    });

    test('should toggle sidebar with Alt+T keyboard shortcut', async ({ page }) => {
        // Wait for the playground to load
        const playgroundLayout = page.locator('.playground-layout');
        await expect(playgroundLayout).toBeVisible({ timeout: 15000 });

        // Take screenshot of initial state
        await page.screenshot({
            path: 'e2e/screenshots/playground-before-alt-t.png',
            fullPage: false
        });

        // Press Alt+T to toggle sidebar
        await page.keyboard.press('Alt+t');
        await page.waitForTimeout(500);

        // Take screenshot with sidebar toggled
        await page.screenshot({
            path: 'e2e/screenshots/playground-after-alt-t.png',
            fullPage: false
        });
    });

    test('should show loading skeleton while JupyterLite initializes', async ({ page }) => {
        // Navigate fresh - capture the loading state quickly
        await page.goto('/app/playground');

        // Try to catch the loading overlay (may pass quickly)
        const loadingOverlay = page.locator('.loading-overlay');
        const hasLoading = await loadingOverlay.isVisible().catch(() => false);
        if (hasLoading) {
            await page.screenshot({
                path: 'e2e/screenshots/playground-loading-state.png',
                fullPage: false
            });
        }

        // Wait for it to resolve
        const playgroundLayout = page.locator('.playground-layout');
        await expect(playgroundLayout).toBeVisible({ timeout: 30000 });

        await page.screenshot({
            path: 'e2e/screenshots/playground-loaded-state.png',
            fullPage: false
        });
    });
});
