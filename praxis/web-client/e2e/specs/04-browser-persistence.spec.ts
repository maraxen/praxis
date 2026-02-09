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

        // 1. Create a machine
        await gotoWithWorkerDb(page, '/app/assets', testInfo, { resetdb: false });
        await page.waitForFunction(async () => {
            const e2e = (window as any).__e2e;
            if (!e2e?.isReady()) return false;
            try {
                return (await e2e.count('machine_definitions')) > 0;
            } catch { return false; }
        }, null, { timeout: 15000 });
        await assetsPage.createMachine(machineName);

        // Wait for DB to confirm machine was persisted
        await page.waitForFunction(async (name) => {
            const e2e = (window as any).__e2e;
            if (!e2e?.isReady()) return false;
            try {
                const machines = await e2e.query('SELECT name FROM machines');
                return machines.some((m: any) => m.name === name);
            } catch { return false; }
        }, machineName, { timeout: 10000 });

        // Reload to ensure UI reflects latest DB state
        await gotoWithWorkerDb(page, '/app/assets', testInfo, { resetdb: false });
        await assetsPage.navigateToMachines();
        await assetsPage.verifyAssetVisible(machineName);

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

        // 5. Import DB
        await gotoWithWorkerDb(page, '/app/settings', testInfo, { resetdb: false });
        await settingsPage.importDatabase(downloadPath!);

        // 6. Verify Data Restored (UI)
        await gotoWithWorkerDb(page, '/app/assets', testInfo, { resetdb: false });
        await assetsPage.navigateToMachines();
        await assetsPage.verifyAssetVisible(machineName);

        // 7. Verify Data Restored (DB state)
        const postImportCount = await page.evaluate(async () => {
            const e2e = (window as any).__e2e;
            if (!e2e) return 0;
            return await e2e.count('machines');
        });
        expect(postImportCount).toBe(preExportCount);
    });
});

