import { test, expect } from '../fixtures/worker-db.fixture';
import { AssetsPage } from '../page-objects/assets.page';
import { WelcomePage } from '../page-objects/welcome.page';

test.describe('Asset Inventory', () => {
    // Run tests serially to avoid sandbox slowness and DB contention
    test.describe.configure({ mode: 'serial' });

    let assetsPage: AssetsPage;

    test.beforeEach(async ({ page }, testInfo) => {
        // Increase timeout for DB reset
        test.setTimeout(120000);

        assetsPage = new AssetsPage(page, testInfo, '/app/assets');
        // Ensure fresh DB for each test to avoid cross-contamination
        await assetsPage.goto({ resetdb: true });

        const welcomePage = new WelcomePage(page);
        await welcomePage.handleSplashScreen();

        await assetsPage.navigateToRegistry();
    });

    test.describe('Persistence', () => {
        test('should persist created machine across reloads', async () => {
            const testMachineName = `Machine-${Date.now()}`;
            await assetsPage.createMachine(testMachineName);

            await assetsPage.navigateToRegistry();
            await assetsPage.selectRegistryTab('Machines');
            await assetsPage.search(testMachineName);
            await assetsPage.verifyAssetVisible(testMachineName);

            // Reload WITHOUT resetdb
            await assetsPage.goto({ resetdb: false });
            await assetsPage.selectRegistryTab('Machines');
            await assetsPage.search(testMachineName);
            await assetsPage.verifyAssetVisible(testMachineName);
        });

        test('should persist created resource across reloads', async () => {
            const testResourceName = `Resource-${Date.now()}`;
            await assetsPage.createResource(testResourceName, 'Plate', '96');

            await assetsPage.navigateToRegistry();
            await assetsPage.selectRegistryTab('Resources');
            await assetsPage.search(testResourceName);
            await assetsPage.verifyAssetVisible(testResourceName);

            // Reload WITHOUT resetdb
            await assetsPage.goto({ resetdb: false });
            await assetsPage.selectRegistryTab('Resources');
            await assetsPage.search(testResourceName);
            await assetsPage.verifyAssetVisible(testResourceName);
        });
    });

    test.describe('Filtering and Sorting', () => {
        test('should display seeded items correctly', async () => {
            await assetsPage.selectRegistryTab('Resource Types');
            // Search for Hamilton specifically to bring it to the first page
            await assetsPage.search('Hamilton');
            await expect(assetsPage.page.getByRole('cell', { name: /Hamilton/i }).first()).toBeVisible();

            // Search for Corning specifically
            await assetsPage.search('Cor_96_wellplate_360ul_Fb');
            await expect(assetsPage.page.getByRole('cell', { name: 'Cor_96_wellplate_360ul_Fb' }).first()).toBeVisible();
        });

        test('should filter resource types by name', async () => {
            await assetsPage.selectRegistryTab('Resource Types');
            await assetsPage.search('384');
            await expect(assetsPage.page.getByRole('cell', { name: /384/i }).first()).toBeVisible();
            // Should not show Cor_96 when searching for 384
            await expect(assetsPage.page.getByRole('cell', { name: 'Cor_96_wellplate_360ul_Fb' })).not.toBeVisible();
        });

        test('should sort resource types by name', async () => {
            await assetsPage.selectRegistryTab('Resource Types');

            const firstRow = assetsPage.page.locator('tbody tr').first();
            await expect(firstRow).toBeVisible();
            const initialText = await (await firstRow.innerText()).trim();

            // Toggle sort order
            const sortToggle = assetsPage.page.locator('.sort-order-btn').first();
            await sortToggle.click();

            // Wait for the text to change (meaning sort applied)
            await expect(async () => {
                const newText = await (await firstRow.innerText()).trim();
                if (newText === initialText) {
                    throw new Error('Sort did not change the first item');
                }
            }).toPass({ timeout: 10000 });
        });
    });

    test.describe('Pagination', () => {
        test('should support pagination for resource types', async () => {
            await assetsPage.selectRegistryTab('Resource Types');

            const paginator = assetsPage.page.locator('mat-paginator');
            await expect(paginator).toBeVisible();

            // Should show something like "1 – 10 of"
            const rangeLabel = paginator.locator('.mat-mdc-paginator-range-label');
            await expect(rangeLabel).toContainText('1 – 10 of');

            // Go to next page
            const nextButton = paginator.locator('button.mat-mdc-paginator-navigation-next');
            await nextButton.click();

            await expect(rangeLabel).toContainText('11 – 20 of');
        });
    });
});
