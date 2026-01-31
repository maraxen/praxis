import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { WelcomePage } from '../page-objects/welcome.page';
import { AssetsPage } from '../page-objects/assets.page';
import { SettingsPage } from '../page-objects/settings.page';

test.describe('Browser Mode Specifics (DB Persistence)', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        await gotoWithWorkerDb(page, '/', testInfo, { waitForDb: false });
        const welcomePage = new WelcomePage(page, testInfo);
        await welcomePage.handleSplashScreen();
    });

    test('should export and import database preserving data', async ({ page }, testInfo) => {
        const assetsPage = new AssetsPage(page, testInfo);
        const settingsPage = new SettingsPage(page, testInfo);
        const machineName = `Persist-Machine-${Date.now()}`;
        const resourceName = `Persist-Resource-${Date.now()}`;

        // 1. Create Data
        await gotoWithWorkerDb(page, '/assets', testInfo, { waitForDb: false, resetdb: false });
        await page.waitForFunction(() => {
            const db = (window as any).sqliteService?.db;
            if (!db) return false;
            const result = db.exec('SELECT COUNT(*) as count FROM asset_definitions');
            return result[0]?.values[0]?.[0] > 0;
        }, null, { timeout: 15000 });
        await assetsPage.createMachine(machineName);
        await assetsPage.createResource(resourceName);
        await assetsPage.navigateToRegistry();
        await assetsPage.verifyAssetVisible(machineName);
        await assetsPage.verifyAssetVisible(resourceName);

        // 2. Verify DB state before export
        const preExportCount = await page.evaluate(() => {
            const db = (window as any).sqliteService?.db;
            return db ? db.exec('SELECT COUNT(*) FROM assets')[0]?.values[0]?.[0] : 0;
        });
        expect(preExportCount).toBeGreaterThan(0);

        // 3. Export DB
        await gotoWithWorkerDb(page, '/settings', testInfo, { waitForDb: false, resetdb: false });
        const downloadPath = await settingsPage.exportDatabase();
        expect(downloadPath).toBeTruthy();

        // 4. Clear Data (use fresh DB via navigation with resetdb=1)
        await gotoWithWorkerDb(page, '/assets', testInfo, { resetdb: true, waitForDb: false });
        await assetsPage.navigateToMachines();
        await assetsPage.verifyAssetNotVisible(machineName);
        await assetsPage.verifyAssetNotVisible(resourceName);

        // 5. Import DB
        await gotoWithWorkerDb(page, '/settings', testInfo, { waitForDb: false, resetdb: false });
        await settingsPage.importDatabase(downloadPath!);

        // 6. Verify Data Restored (UI)
        await gotoWithWorkerDb(page, '/assets', testInfo, { waitForDb: false, resetdb: false });
        await assetsPage.navigateToMachines();
        await assetsPage.verifyAssetVisible(machineName);
        await assetsPage.navigateToRegistry();
        await assetsPage.verifyAssetVisible(resourceName);


        // 7. Verify Data Restored (DB state)
        const postImportCount = await page.evaluate(() => {
            const db = (window as any).sqliteService?.db;
            return db ? db.exec('SELECT COUNT(*) FROM assets')[0]?.values[0]?.[0] : 0;
        });
        expect(postImportCount).toBe(preExportCount);
    });
});
