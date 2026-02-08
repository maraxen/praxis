import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { AssetsPage } from '../page-objects/assets.page';
import { SettingsPage } from '../page-objects/settings.page';

test.describe('Browser Mode Specifics (DB Persistence)', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        await gotoWithWorkerDb(page, '/app/home', testInfo);
    });

    test('should export and import database preserving data', async ({ page }, testInfo) => {
        const assetsPage = new AssetsPage(page, testInfo, '/app/assets');
        const settingsPage = new SettingsPage(page, testInfo);
        const machineName = `Persist-Machine-${Date.now()}`;
        const resourceName = `Persist-Resource-${Date.now()}`;

        // 1. Create Data
        await gotoWithWorkerDb(page, '/app/assets', testInfo, { resetdb: false });
        await page.waitForFunction(async () => {
            const e2e = (window as any).__e2e;
            if (!e2e?.isReady()) return false;
            try {
                return (await e2e.count('machine_definitions')) > 0;
            } catch { return false; }
        }, null, { timeout: 15000 });
        await assetsPage.createMachine(machineName);
        await assetsPage.createResource(resourceName);
        await assetsPage.navigateToRegistry();
        await assetsPage.verifyAssetVisible(machineName);
        await assetsPage.verifyAssetVisible(resourceName);

        // 2. Verify DB state before export
        const preExportCount = await page.evaluate(async () => {
            const e2e = (window as any).__e2e;
            if (!e2e) return 0;
            return await e2e.count('machines');
        });
        expect(preExportCount).toBeGreaterThan(0);

        // 3. Export DB
        await gotoWithWorkerDb(page, '/app/settings', testInfo, { resetdb: false });
        const downloadPath = await settingsPage.exportDatabase();
        expect(downloadPath).toBeTruthy();

        // 4. Clear Data (use fresh DB via navigation with resetdb=1)
        await gotoWithWorkerDb(page, '/app/assets', testInfo, { resetdb: true });
        await assetsPage.navigateToMachines();
        await assetsPage.verifyAssetNotVisible(machineName);
        await assetsPage.verifyAssetNotVisible(resourceName);

        // 5. Import DB
        await gotoWithWorkerDb(page, '/app/settings', testInfo, { resetdb: false });
        await settingsPage.importDatabase(downloadPath!);

        // 6. Verify Data Restored (UI)
        await gotoWithWorkerDb(page, '/app/assets', testInfo, { resetdb: false });
        await assetsPage.navigateToMachines();
        await assetsPage.verifyAssetVisible(machineName);
        await assetsPage.navigateToRegistry();
        await assetsPage.verifyAssetVisible(resourceName);

        // 7. Verify Data Restored (DB state)
        const postImportCount = await page.evaluate(async () => {
            const e2e = (window as any).__e2e;
            if (!e2e) return 0;
            return await e2e.count('machines');
        });
        expect(postImportCount).toBe(preExportCount);
    });
});
