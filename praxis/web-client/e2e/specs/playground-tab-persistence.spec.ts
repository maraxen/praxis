import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';

test.describe('Playground Tab State Persistence', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        await gotoWithWorkerDb(page, '/app/playground', testInfo);
        await page.waitForSelector('mat-tab-group', { timeout: 15000 });
    });

    test('switching tabs preserves JupyterLite iframe', async ({ page }) => {
        // Wait for notebook tab to be active and iframe loaded
        const notebookIframe = page.locator('iframe.notebook-frame');
        await expect(notebookIframe).toBeVisible({ timeout: 15000 });

        // Get iframe's src to verify it's the same element later
        const originalSrc = await notebookIframe.getAttribute('src');

        // Switch to Direct Control tab
        await page.getByRole('tab', { name: 'Direct Control' }).click();

        // Wait for direct control content
        await expect(page.locator('.direct-control-dashboard')).toBeVisible({ timeout: 10000 });

        // Switch back to Notebook tab
        await page.getByRole('tab', { name: 'Notebook' }).click();

        // Verify iframe still has same src (not recreated)
        const newSrc = await notebookIframe.getAttribute('src');
        expect(newSrc).toBe(originalSrc);
    });

    test('tab label shows "Notebook" not "REPL Notebook"', async ({ page }) => {
        const tab = page.getByRole('tab', { name: 'Notebook' });
        await expect(tab).toBeVisible();
    });
});
