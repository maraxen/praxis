import { test, expect } from '../../fixtures/worker-db.fixture';
import { WelcomePage } from '../../page-objects/welcome.page';
import { AssetsPage } from '../../page-objects/assets.page';
import { Locator } from '@playwright/test';

test.describe('Asset Forms Interaction', () => {
  let assetsPage: AssetsPage;

  test.beforeEach(async ({ page }) => {
    const welcomePage = new WelcomePage(page);
    await welcomePage.goto();
    await welcomePage.handleSplashScreen();
    assetsPage = new AssetsPage(page);
    await assetsPage.goto();
    await assetsPage.navigateToMachines();
  });

  test('should successfully create a machine through the wizard', async ({ page }) => {
    const machineName = `Test-Machine-${Date.now()}`;
    await assetsPage.createMachine(machineName, 'LiquidHandler');

    // Verify machine appears in the table
    await assetsPage.verifyAssetVisible(machineName);

    // Cleanup
    await assetsPage.deleteMachine(machineName);
  });

  test.describe('Machine Wizard Validation', () => {
    let wizard: Locator;

    test.beforeEach(async ({ page }) => {
      wizard = await assetsPage.navigateToConfigStep();
    });

    test('name field is required', async ({ page }) => {
      const nameInput = wizard.getByTestId('input-instance-name');
      await nameInput.clear();

      const nextBtn = wizard.getByTestId('wizard-next-button');
      await expect(nextBtn).toBeDisabled();

      await expect(wizard.locator('mat-error')).toHaveText(/Name is required/i);
    });

    test('valid name enables progression', async ({ page }) => {
      const nameInput = wizard.getByTestId('input-instance-name');
      await nameInput.fill('My New Machine');

      const nextBtn = wizard.getByTestId('wizard-next-button');
      await expect(nextBtn).toBeEnabled();
    });

    test('should show validation error for invalid JSON', async ({ page }) => {
      const advancedToggle = wizard.getByRole('button', { name: /Advanced/i });
  
      if (!await advancedToggle.isVisible({ timeout: 2000 })) {
        test.skip(true, 'Advanced JSON configuration not available for this backend');
        return;
      }
  
      await advancedToggle.click();

      const jsonInput = wizard.locator('textarea[formcontrolname="connection_info"]');
      await jsonInput.fill('{ invalid json }');

      await expect(wizard.locator('mat-error')).toBeVisible();
      await expect(wizard.getByTestId('wizard-next-button')).toBeDisabled();
    });

    test('should handle creation failure gracefully', async ({ page }) => {
      await wizard.getByTestId('input-instance-name').fill('Test Machine');
      await wizard.getByTestId('wizard-next-button').click();
      
      // Mock the asset creation to fail
      await page.route('**/api/machines', (route) => {
          route.fulfill({
              status: 500,
              body: JSON.stringify({ error: 'Internal Server Error' }),
          });
      });
      
      const createBtn = wizard.getByTestId('wizard-create-btn');
      await createBtn.click();
      
      // Verify error feedback
      await expect(page.getByText(/failed|error/i)).toBeVisible();
      // Wizard should remain open
      await expect(wizard).toBeVisible();
    });

    test('should prevent duplicate machine names', async ({ page }) => {
      const duplicateName = 'Duplicate-Test-Machine';
      
      // Create first machine
      await assetsPage.createMachine(duplicateName);
      
      // Try to create second with same name
      const wizard2 = await assetsPage.navigateToConfigStep();
      await wizard2.getByTestId('input-instance-name').fill(duplicateName);
      await wizard2.getByTestId('wizard-next-button').click();

      const createBtn = wizard2.getByTestId('wizard-create-btn');
      await createBtn.click();
      
      // Verify error feedback
      await expect(page.getByText(/already exists/i)).toBeVisible();
      // Wizard should remain open
      await expect(wizard2).toBeVisible();
    });
  });
});
