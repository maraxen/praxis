import { test, expect } from '../fixtures/worker-db.fixture';

test.describe('Inventory Dialog', () => {
    test.beforeEach(async ({ page }) => {
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

    test('should open inventory dialog and verify tabs', async ({ page }) => {
        // 1. Opening inventory dialog from playground - button is "Browse Inventory"
        const openButton = page.getByRole('button', { name: 'Browse Inventory' });
        await expect(openButton).toBeVisible({ timeout: 10000 });
        await openButton.click();

        // Wait for dialog to open
        const dialog = page.getByRole('dialog');
        await expect(dialog).toBeVisible({ timeout: 5000 });

        // 2. Verifying tabs are visible: Quick Add, Browse & Add, Current Items
        await expect(page.getByRole('tab', { name: 'Quick Add' })).toBeVisible();
        await expect(page.getByRole('tab', { name: 'Browse & Add' })).toBeVisible();
        await expect(page.getByRole('tab', { name: 'Current Items' })).toBeVisible();
    });

    test('should select machine type and add a simulated machine', async ({ page }) => {
        // Open inventory dialog
        await page.getByRole('button', { name: 'Browse Inventory' }).click();

        // Wait for dialog to open
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

        // Navigate to Browse & Add
        await page.getByRole('tab', { name: 'Browse & Add' }).click();

        // Step 1: Selecting machine type
        const machineTypeCard = page.locator('.type-card').filter({ hasText: /Machine/i });
        await expect(machineTypeCard).toBeVisible({ timeout: 10000 });
        await machineTypeCard.click();
        await page.getByRole('button', { name: 'Continue' }).click();

        // Step 2: Selecting Category
        const categoryOption = page.locator('mat-chip-option').first();
        await expect(categoryOption).toBeVisible({ timeout: 5000 });
        await categoryOption.click();
        await page.getByRole('button', { name: 'Continue' }).click();

        // Step 3: Selecting Asset
        // Asset items use mat-list-option
        const simulatedMachineOption = page.locator('mat-list-option').filter({ hasText: /Simulated/i }).first();

        if (!(await simulatedMachineOption.isVisible({ timeout: 5000 }))) {
            const firstOption = page.locator('mat-list-option').first();
            await expect(firstOption).toBeVisible({ timeout: 5000 });
            await firstOption.click();
        } else {
            await simulatedMachineOption.click();
        }
        await page.getByRole('button', { name: 'Continue' }).click();

        // Step 4: Specs and Add
        const addButton = page.getByRole('button', { name: 'Add to Inventory', exact: true });
        await expect(addButton).toBeVisible();
        await addButton.click();

        // 5. Verifying machine appears in Current Items
        // The dialog automatically switches to Current Items tab after addToList()
        await expect(page.getByRole('tab', { name: 'Current Items' })).toBeVisible();

        // Verify the item is listed in Current Items
        const currentItems = page.locator('.inventory-card-item');
        await expect(currentItems.first()).toBeVisible({ timeout: 5000 });
    });
});
