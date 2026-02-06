import { test, expect } from '../fixtures/worker-db.fixture';
import { InventoryDialogPage } from '../page-objects/inventory-dialog.page';

test.describe('Inventory Dialog', () => {
    let inventoryDialog: InventoryDialogPage;

    test.beforeEach(async ({ page }) => {
        inventoryDialog = new InventoryDialogPage(page);

        // Navigate to playground in browser mode
        await page.goto('/app/playground?mode=browser');

        // Handle onboarding splash / tours
        try {
            // Wait for page to stabilize
            await page.waitForLoadState('domcontentloaded');

            // Check for various ways to dismiss overlays
            const skipButton = page.getByRole('button', { name: /skip|dismiss|close/i });
            const tourExit = page.locator('.shepherd-button:has-text("Exit")').or(page.locator('.shepherd-button:has-text("Skip")'));

            if (await skipButton.isVisible()) {
                await skipButton.click();
            } else if (await tourExit.isVisible()) {
                await tourExit.click();
            }

            // Wait for any backdrop to disappear
            await expect(page.locator('.cdk-overlay-backdrop')).not.toBeVisible({ timeout: 5000 });
        } catch (e) {
            // Overlays not visible or already handled
        }
    });

    test('should open inventory dialog and verify initial step', async ({ page }) => {
        // 1. Opening inventory dialog from playground - button is "Browse Inventory"
        const openButton = page.getByRole('button', { name: 'Browse Inventory' });
        await expect(openButton).toBeVisible({ timeout: 10000 });
        await openButton.click();

        // Wait for dialog to open
        await inventoryDialog.waitForDialogVisible();

        // 2. Verifying initial step is "Type"
        const activeStep = page.locator('.mat-step-header[aria-selected="true"]');
        await expect(activeStep).toContainText('Type');
        
        await expect(page.getByTestId('type-card-machine')).toBeVisible();
        await expect(page.getByTestId('type-card-resource')).toBeVisible();
    });

    test('should select machine type and add a simulated machine', async ({ page }) => {
        // Open inventory dialog
        const openButton = page.getByRole('button', { name: 'Browse Inventory' });
        await expect(openButton).toBeVisible({ timeout: 10000 });
        await openButton.click();

        // Wait for dialog to open
        await inventoryDialog.waitForDialogVisible();

        // Step 1: Selecting machine type
        await inventoryDialog.selectAssetType('MACHINE');

        // Step 2: Selecting Category
        // We'll use LiquidHandler as it's common
        await inventoryDialog.selectCategory('LiquidHandler');

        // Step 3: Selecting Machine Type (Frontend)
        await inventoryDialog.selectMachineType(/./); // Select any available machine type

        // Step 4: Selecting Driver (Backend)
        // We look for 'Simulated' or any available driver
        await inventoryDialog.selectDriver(/./);

        // Step 5: Configuration
        await inventoryDialog.fillInstanceName('E2E Test Machine');

        // Step 6: Review and Create
        await inventoryDialog.createAsset();

        // 5. Verifying machine appears in the environment (Toast or close)
        // Since we are in the playground, we can check if a snackbar appeared
        await expect(page.locator('mat-snack-bar-container')).toContainText(/Inserted/i, { timeout: 10000 });
    });
});
