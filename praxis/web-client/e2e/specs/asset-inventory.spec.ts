import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { AssetsPage } from '../page-objects/assets.page';
import { WelcomePage } from '../page-objects/welcome.page';

/**
 * E2E Tests for Asset Inventory Persistence
 * 
 * These tests verify that Machines and Resources created in the UI persist
 * across page reloads, simulating the JupyterLite environment reading from
 * the browser-side SQLite database.
 */
test.describe('Asset Inventory Persistence', () => {
    let assetsPage: AssetsPage;
    const testMachineName = `E2E-Machine-${Date.now()}`;
    const testResourceName = `E2E-Resource-${Date.now()}`;

    test.beforeEach(async ({ page }, testInfo) => {
        await gotoWithWorkerDb(page, '/app/assets', testInfo);
        const welcomePage = new WelcomePage(page);
        await welcomePage.handleSplashScreen();
        assetsPage = new AssetsPage(page);
    });

    test.afterEach(async () => {
        // Cleanup created assets
        await assetsPage.navigateToMachines();
        await assetsPage.deleteMachine(testMachineName).catch(() => {});
        await assetsPage.navigateToRegistry();
        await assetsPage.deleteResource(testResourceName).catch(() => {});
    });

    test('should persist created machine across reloads', async ({ page }) => {
        await assetsPage.createMachine(testMachineName, 'LiquidHandler', 'STAR');
        
        await assetsPage.navigateToMachines();
        await expect(page.getByText(testMachineName)).toBeVisible();

        // Verify DB integrity
        const dbRecord = await page.evaluate((name) => 
            (window as any).sqliteService.execSync(
                'SELECT * FROM machines WHERE name = ?', [name]
            ), testMachineName);
        expect(dbRecord.length).toBe(1);

        // Persistence after reload
        await page.reload();
        await assetsPage.navigateToMachines();
        await expect(page.getByText(testMachineName)).toBeVisible();
    });

    test('should persist created resource across reloads', async ({ page }) => {
        await assetsPage.createResource(testResourceName, 'Plate', '96');
        
        await assetsPage.navigateToRegistry();
        await expect(page.getByText(testResourceName)).toBeVisible();

        // Verify DB integrity for resources
        const dbRecord = await page.evaluate((name) => 
            (window as any).sqliteService.execSync(
                'SELECT * FROM resources WHERE name = ?', [name]
            ), testResourceName);
        expect(dbRecord.length).toBe(1);

        await page.reload();
        await assetsPage.navigateToRegistry();
        await expect(page.getByText(testResourceName)).toBeVisible();
    });
});
