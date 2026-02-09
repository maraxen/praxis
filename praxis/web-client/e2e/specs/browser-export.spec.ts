import { test, expect } from '../fixtures/worker-db.fixture';
import { SettingsPage } from '../page-objects/settings.page';
import { AssetsPage } from '../page-objects/assets.page';
import * as fs from 'fs';
import * as path from 'path';

test.describe('Browser Mode Database Export', () => {
    let settingsPage: SettingsPage;

    test.beforeEach(async ({ page }, testInfo) => {
        settingsPage = new SettingsPage(page, testInfo);
        await settingsPage.goto();
        await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
    });

    test('Export Database triggers download', async ({ page }) => {
        const downloadPromise = page.waitForEvent('download');
        await settingsPage.exportButton.click();
        const download = await downloadPromise;

        expect(download.suggestedFilename()).toMatch(/praxis-backup-.*\.db/);
        await expect(page.getByText('Database exported')).toBeVisible();
    });

    test('Export Database produces a valid SQLite file', async ({ page }) => {
        const downloadPromise = page.waitForEvent('download');
        await settingsPage.exportButton.click();
        const download = await downloadPromise;

        const downloadPath = await download.path();
        expect(downloadPath).toBeTruthy();

        const stats = fs.statSync(downloadPath);
        expect(stats.size).toBeGreaterThan(0);

        const buffer = fs.readFileSync(downloadPath);
        const magicBytes = buffer.toString('utf8', 0, 16);
        expect(magicBytes).toContain('SQLite format 3');
    });

    test('Import Database opens confirmation dialog and can be cancelled', async () => {
        await settingsPage.openImportDialogAndCancel();
    });
});

test.describe('Import Database - Full Path', () => {
    let settingsPage: SettingsPage;
    let assetsPage: AssetsPage;

    test.beforeEach(async ({ page }, testInfo) => {
        settingsPage = new SettingsPage(page, testInfo);
        assetsPage = new AssetsPage(page, testInfo);
        await settingsPage.goto();
    });

    test('successfully imports and restores data', async ({ page }, testInfo) => {
        const testDbPath = path.join(__dirname, '../fixtures/test-praxis.db');
        
        await settingsPage.importDatabase(testDbPath);
        
        // Verify by navigating to assets and checking for the fixture data
        await assetsPage.goto();
        await assetsPage.verifyAssetVisible('fixture-asset');
    });

    test.afterEach(async ({ page }, testInfo) => {
        const settingsPage = new SettingsPage(page, testInfo);
        await settingsPage.goto();
        await settingsPage.resetState();
    });
});

test.describe('Import/Reset - Error and Edge Case Coverage', () => {
    let settingsPage: SettingsPage;

    test.beforeEach(async ({ page }, testInfo) => {
        settingsPage = new SettingsPage(page, testInfo);
        await settingsPage.goto();
    });

    test('rejects non-SQLite file upload', async ({ page }) => {
        const fileChooserPromise = page.waitForEvent('filechooser');
        await page.getByRole('button', { name: 'Import Database' }).click();
        const fileChooser = await fileChooserPromise;

        await fileChooser.setFiles({
            name: 'not_a_database.txt',
            mimeType: 'text/plain',
            buffer: Buffer.from('This is not a database')
        });
        
        const dialog = page.getByRole('dialog', { name: /Import Database/i });
        await expect(dialog).toBeVisible();
        await page.getByRole('button', { name: 'Import and Refresh' }).click();

        await expect(page.getByText(/Import failed/i)).toBeVisible();
    });
});
