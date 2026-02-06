import { test, expect } from '../fixtures/worker-db.fixture';
import { AssetsPage } from '../page-objects/assets.page';
import { gotoWithWorkerDb } from '../fixtures/worker-db.fixture';

/**
 * Asset Wizard E2E Test
 *
 * This test verifies the end-to-end journey of adding a new machine
 * using the Asset Wizard in the laboratory inventory.
 *
 * It uses the worker-db.fixture for isolated, parallel-safe execution.
 */
test.describe('Asset Wizard Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Bypass onboarding splash screen
    await page.addInitScript(() => {
      localStorage.setItem('praxis_onboarding_completed', 'true');
      localStorage.setItem('praxis_tutorial_completed', 'true');
    });
  });

  test('should guide the user through creating a Hamilton STAR machine', async ({ page }, testInfo) => {
    // Use waitForDb: true to ensure SQLite is ready
    await gotoWithWorkerDb(page, '/assets', testInfo, { waitForDb: true });

    const assetsPage = new AssetsPage(page);

    // Wait for any initial overlays to dismiss
    await assetsPage.waitForOverlaysToDismiss();

    // Click Add Machine button (skips Type step)
    await expect(assetsPage.addMachineButton).toBeVisible({ timeout: 15000 });
    await assetsPage.addMachineButton.click();

    // Wait for the wizard to appear
    const wizard = page.locator('app-asset-wizard');
    await expect(wizard).toBeVisible({ timeout: 15000 });

    // Step 1: Select Category (Liquid Handler)
    await assetsPage.selectWizardCard(wizard, 'category-card-LiquidHandler');
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Machine Type/i);

    // Step 2: Select Machine Type (Frontend)
    const frontendCard = wizard.getByTestId(/frontend-card-/).filter({ hasText: /Liquid/i }).first();
    await expect(frontendCard).toBeVisible({ timeout: 15000 });
    await frontendCard.click();
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Driver/i);

    // Step 3: Select Driver (Backend)
    const backendCard = wizard.getByTestId(/backend-card-/).filter({ hasText: /STAR/i }).first();
    await expect(backendCard).toBeVisible({ timeout: 15000 });
    await backendCard.click();
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Config/i);

    // Step 4: Configuration
    const nameInput = wizard.getByLabel('Instance Name');
    await expect(nameInput).toBeVisible({ timeout: 10000 });
    await nameInput.fill('Hamilton STAR Test');
    const nextButton = wizard.getByTestId('wizard-next-button').filter({ visible: true }).first();
    await expect(nextButton).toBeEnabled();
    await nextButton.click();
    await assetsPage.waitForStepTransition(wizard, /Review/i);

    // Step 5: Summary and Create
    await expect(wizard.locator('.review-card')).toContainText(/STAR/i);
    const createButton = wizard.getByRole('button', { name: 'Create Asset' });
    await expect(createButton).toBeEnabled();
    await createButton.click();

    // 6. Verify result
    await expect(wizard).not.toBeVisible({ timeout: 15000 });
    await assetsPage.verifyAssetVisible('Hamilton STAR Test');

    // 7. Domain Verification: Check SQLite Database via service
    const machineData = await page.evaluate(async (name) => {
      const service = (window as any).sqliteService;
      if (!service) return null;
      
      return new Promise((resolve) => {
        service.getMachines().subscribe((machines: any[]) => {
          resolve(machines.find(m => m.name === name));
        });
      });
    }, 'Hamilton STAR Test');

    expect(machineData).toBeDefined();
    expect((machineData as any).machine_category).toBe('LiquidHandler');
    expect((machineData as any).name).toBe('Hamilton STAR Test');

    // 8. Persistence Verification: Reload and check
    await page.reload();
    await assetsPage.verifyAssetVisible('Hamilton STAR Test', 15000);
  });

  test('should handle wizard cancellation gracefully', async ({ page }, testInfo) => {
    await gotoWithWorkerDb(page, '/assets', testInfo, { waitForDb: true });
    const assetsPage = new AssetsPage(page);
    await assetsPage.waitForOverlaysToDismiss();

    // 1. Open wizard
    await assetsPage.addMachineButton.click();
    const dialog = page.getByRole('dialog');

    // Wait for wizard content to appear
    await expect(dialog.getByTestId(/category-card-/).first()).toBeVisible({ timeout: 15000 });

    // 2. Close wizard via Escape
    await page.keyboard.press('Escape');

    // 3. Verify wizard is closed
    await expect(dialog).not.toBeVisible({ timeout: 10000 });

    // 4. Verify no asset was created
    const machineCount = await page.evaluate(async () => {
      const service = (window as any).sqliteService;
      if (!service) return 0;
      return new Promise((resolve) => {
        service.getMachines().subscribe((machines: any[]) => {
          resolve(machines.length);
        });
      });
    });
    expect(machineCount).toBe(0);
  });

  test('should prevent creation with empty instance name', async ({ page }, testInfo) => {
    await gotoWithWorkerDb(page, '/assets', testInfo, { waitForDb: true });
    const assetsPage = new AssetsPage(page);
    await assetsPage.waitForOverlaysToDismiss();

    // Navigate to the configuration step
    await assetsPage.addMachineButton.click();
    const wizard = page.locator('app-asset-wizard');
    
    await assetsPage.selectWizardCard(wizard, 'category-card-LiquidHandler');
    await assetsPage.clickNextButton(wizard);
    
    const frontendCard = wizard.getByTestId(/frontend-card-/).filter({ hasText: /Liquid/i }).first();
    await expect(frontendCard).toBeVisible({ timeout: 15000 });
    await frontendCard.click();
    await assetsPage.clickNextButton(wizard);
    
    const backendCard = wizard.getByTestId(/backend-card-/).filter({ hasText: /STAR/i }).first();
    await expect(backendCard).toBeVisible({ timeout: 15000 });
    await backendCard.click();
    await assetsPage.clickNextButton(wizard);
    
    await assetsPage.waitForStepTransition(wizard, /Config/i);

    // Verify Next button is disabled (name is required and it auto-fills, but let's clear it)
    const nameInput = wizard.getByLabel('Instance Name');
    await nameInput.fill('');
    
    const nextButton = wizard.getByTestId('wizard-next-button').filter({ visible: true }).first();
    await expect(nextButton).toBeDisabled();

    // Fill the name and verify the button is enabled
    await nameInput.fill('Test Name');
    await expect(nextButton).toBeEnabled();
  });

  test('should display empty state when no definitions match', async ({ page }, testInfo) => {
    // This test is more suitable for Resources where we have a search box
    await gotoWithWorkerDb(page, '/assets', testInfo, { waitForDb: true });
    const assetsPage = new AssetsPage(page);
    await assetsPage.waitForOverlaysToDismiss();

    // Navigate to the search step for Resources
    await assetsPage.addResourceButton.click();
    const wizard = page.locator('app-asset-wizard');
    
    // Select category
    await assetsPage.selectWizardCard(wizard, 'category-card-Plate');
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Definition/i);

    // Search for a non-existent resource
    const searchInput = wizard.getByPlaceholder(/Plate, Tip/i);
    await searchInput.fill('XYZ_NONEXISTENT_PLATE_TYPE');

    // Verify empty state message
    const emptyState = wizard.getByText(/No definitions found/i);
    await expect(emptyState).toBeVisible({ timeout: 5000 });

    // Verify Next button is disabled
    const nextButton = wizard.getByTestId('wizard-next-button').filter({ visible: true }).first();
    await expect(nextButton).toBeDisabled();
  });
});
