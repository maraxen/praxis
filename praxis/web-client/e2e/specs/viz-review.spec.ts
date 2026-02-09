import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { DataVisualizationPage } from '../page-objects/data-visualization.page';
import { WelcomePage } from '../page-objects/welcome.page';

test.describe('Visualization Review Panel', () => {
    test.setTimeout(120000);

    test.beforeEach(async ({ page }, testInfo) => {
        const welcomePage = new WelcomePage(page, testInfo);
        const vizPage = new DataVisualizationPage(page, testInfo);

        // 1. Initial navigation (isolated DB handles clean state mostly, but we use resetdb=true for certainty)
        await gotoWithWorkerDb(page, '/app/data', testInfo, { resetdb: true });

        // 2. Wait for component to be present
        await page.waitForSelector('app-data-visualization', { timeout: 10000 });

        // 3. Seed mock data using __e2e API (sqliteService is not exposed in test builds)
        await page.evaluate(async () => {
            console.log('[E2E Seed] Starting seeding via __e2e API...');
            const e2e = (window as any).__e2e;
            if (!e2e) throw new Error("__e2e API not found");

            const runId = 'e2e-run-' + Date.now();
            console.log(`[E2E Seed] Creating run ${runId}`);

            // Insert test run directly via SQL
            await e2e.query(
                `INSERT INTO protocol_runs (accession_id, name, status, created_at, top_level_protocol_definition_accession_id)
                 VALUES (?, ?, ?, ?, ?)`,
                [runId, 'PCR Prep Test', 'COMPLETED', new Date().toISOString(), 'kinetic-assay']
            );
            console.log(`[E2E Seed] Run ${runId} inserted`);
        });

        // 4. Reload to pick up seeded data
        await gotoWithWorkerDb(page, '/app/data', testInfo, { resetdb: false });
        await page.waitForSelector('app-data-visualization', { timeout: 10000 });

        // 5. Wait for the run to appear in the table
        await expect(vizPage.runHistoryTable.locator('tr').filter({ hasText: 'PCR Prep Test' })).toBeVisible({ timeout: 20000 });
    });

    test('should display execution data and render visualization', async ({ page }, testInfo) => {
        const vizPage = new DataVisualizationPage(page, testInfo);

        // Verify assertions about the review panel
        await expect(vizPage.heading).toBeVisible();
        await expect(page.locator('.stat-card')).toHaveCount(4);

        // Check if chart becomes visible
        await expect(vizPage.chart).toBeVisible({ timeout: 60000 });
    });

    test('should allow well selection and filtering', async ({ page }, testInfo) => {
        const vizPage = new DataVisualizationPage(page, testInfo);

        await expect(vizPage.wellSelectorButton).toBeVisible();
        await vizPage.wellSelectorButton.click();

        // Verify dialog opens
        await expect(page.locator('mat-dialog-container')).toBeVisible();
        await expect(page.getByText('Select Wells for Visualization')).toBeVisible();

        // Close dialog
        await page.keyboard.press('Escape');
    });
});
