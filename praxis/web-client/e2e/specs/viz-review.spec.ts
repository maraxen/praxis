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
        await welcomePage.handleSplashScreen();

        // 2. Wait for component to be present
        await page.waitForSelector('app-data-visualization', { timeout: 10000 });

        // 3. Seed mock data
        await page.evaluate(async () => {
            console.log('[E2E Seed] Starting seeding...');
            const service = (window as any).sqliteService;
            if (!service) throw new Error("sqliteService not found");

            const repos = await new Promise(resolve => service.getAsyncRepositories().subscribe(resolve)) as any;
            
            // Create a mock run
            const runId = 'e2e-run-' + Date.now();
            console.log(`[E2E Seed] Creating run ${runId}`);
            await new Promise(resolve => repos.protocolRuns.create({
                accession_id: runId,
                name: 'PCR Prep Test',
                status: 'COMPLETED',
                created_at: new Date().toISOString(),
                top_level_protocol_definition_accession_id: 'kinetic-assay'
            }).subscribe(resolve));
            
            // Force component to refresh runs
            const el = document.querySelector('app-data-visualization');
            if (!el) {
                console.warn('[E2E Seed] app-data-visualization element not found');
                return;
            }
            
            const ng = (window as any).ng;
            if (!ng) {
                console.warn('[E2E Seed] window.ng not found (production build?)');
                return;
            }

            const component = ng.getComponent(el);
            if (component) {
                console.log('[E2E Seed] Found component, refreshing runs...');
                // We have to wait for the next tick for the DB to be updated
                setTimeout(() => {
                    (window as any).protocolService?.getRuns().subscribe((runs: any) => {
                        console.log(`[E2E Seed] Got ${runs.length} runs from service`);
                        // Component mapping logic
                        const mappedRuns = runs.map((r: any) => ({
                            id: r.accession_id,
                            protocolName: r.name || 'Unknown Protocol',
                            status: (r.status || 'failed').toLowerCase(),
                            startTime: new Date(r.created_at),
                            wellCount: 96,
                            totalVolume: 1000
                        }));
                        component.runs.set(mappedRuns);
                        // Select the first run
                        if (mappedRuns.length > 0) {
                            console.log('[E2E Seed] Selecting first run');
                            component.selectRun(mappedRuns[0]);
                        }
                    });
                }, 200);
            } else {
                console.warn('[E2E Seed] Could not get component instance');
            }
        });
        
        // Wait for the table to appear in the same page load
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
