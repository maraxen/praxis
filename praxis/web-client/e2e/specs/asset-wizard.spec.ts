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
  test('should guide the user through creating a Hamilton STAR machine', async ({ page }, testInfo) => {
    await gotoWithWorkerDb(page, '/assets', testInfo, { waitForDb: false });

    try {
      const dismissBtn = page.getByRole('button', { name: /Get Started|Skip|Close/i }).first();
      if (await dismissBtn.isVisible({ timeout: 5000 })) {
        await dismissBtn.click();
      }
    } catch (e) {
      console.log('Welcome dialog not found or could not be dismissed.');
    }

    const assetsPage = new AssetsPage(page);

    // Mock API calls to ensure test stability
    await page.route('**/api/v1/machines/definitions/facets', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          machine_category: [{ value: 'Liquid Handler', count: 1 }],
          manufacturer: [{ value: 'Hamilton', count: 1 }]
        })
      });
    });

    await page.route('**/api/v1/machines/definitions?*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            accession_id: 'mach_test_001',
            name: 'Hamilton STAR',
            fqn: 'pylabrobot.liquid_handling.backends.hamilton.STAR',
            plr_category: 'Machine',
            machine_category: 'Liquid Handler',
            manufacturer: 'Hamilton',
            description: 'Hamilton STAR liquid handler',
            available_simulation_backends: ['Simulated']
          }
        ])
      });
    });

    // Wait for any initial overlays to dismiss
    await assetsPage.waitForOverlaysToDismiss();

    // Click Add Asset button
    await expect(assetsPage.addMachineButton).toBeVisible({ timeout: 15000 });
    await assetsPage.addMachineButton.click();

    // Wait for the wizard to appear and the first card to be visible
    const wizard = page.locator('app-asset-wizard');
    await expect(wizard.locator('mat-card').first()).toBeVisible({ timeout: 15000 });

    // Step 1: Select Asset Type (Machine)
    await assetsPage.selectWizardCard(wizard, 'asset-type-card-Machine');
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Select Category/i);

    // Step 2: Select Category (Liquid Handler)
    await assetsPage.selectWizardCard(wizard, 'category-card-LiquidHandler');
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Select Machine Type/i);

    // Step 3: Search and Select STAR
    await wizard.getByLabel('Search Definitions').fill('STAR');
    const resultCard = wizard.locator('.result-card').first();
    await expect(resultCard).toBeVisible({ timeout: 5000 }); // Wait for search debounce
    await resultCard.click();
    await expect(resultCard).toHaveClass(/selected/);
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Select Driver/i);


    // Step 4: Verify Simulated backend and proceed
    const backendSelect = wizard.getByLabel('Backend (Driver)');
    await expect(backendSelect).toContainText(/Simulated/i);
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Configuration/i);


    // Step 5: Configuration
    await wizard.getByLabel('Instance Name').fill('Hamilton STAR Test');
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Summary/i);


    // Step 6: Summary and Create
    await expect(wizard.locator('.review-card')).toContainText('Hamilton STAR');
    const createButton = wizard.getByRole('button', { name: 'Create Asset' });
    await expect(createButton).toBeEnabled();
    await createButton.click();

    // 7. Verify result
    await expect(wizard).not.toBeVisible({ timeout: 15000 });
    await assetsPage.verifyAssetVisible('Hamilton STAR Test');

    // 8. Domain Verification: Check SQLite Database
    const machineData = await page.evaluate(async (name) => {
      const db = (window as any).sqliteService;
      const result = await db.query(
        'SELECT * FROM machines WHERE instance_name = ?',
        [name]
      );
      return result[0];
    }, 'Hamilton STAR Test');

    expect(machineData).toBeDefined();
    expect(machineData.category).toBe('LiquidHandler');
    expect(machineData.frontend_fqn).toContain('STAR');

    // 9. Persistence Verification: Reload and check
    await page.reload();
    await assetsPage.verifyAssetVisible('Hamilton STAR Test', 15000);
  });

  test('should handle wizard cancellation gracefully', async ({ page }, testInfo) => {
    await gotoWithWorkerDb(page, '/assets', testInfo, { waitForDb: false });
    try {
      const dismissBtn = page.getByRole('button', { name: /Get Started|Skip|Close/i }).first();
      if (await dismissBtn.isVisible({ timeout: 5000 })) {
        await dismissBtn.click();
      }
    } catch (e) {
      console.log('Welcome dialog not found or could not be dismissed.');
    }
    const assetsPage = new AssetsPage(page);
    await assetsPage.waitForOverlaysToDismiss();

    // 1. Open wizard - Add Machine button skips Type step, opens at Category
    await assetsPage.addMachineButton.click();
    const wizard = page.locator('app-asset-wizard');
    const dialog = page.getByRole('dialog');

    // Wait for category cards to appear (wizard opens at Category step)
    const categoryCard = wizard.getByTestId(/category-card-/).first();
    await expect(categoryCard).toBeVisible({ timeout: 15000 });

    // 2. Close wizard via Escape (no Cancel button exists)
    await page.keyboard.press('Escape');

    // 3. Verify wizard is closed
    await expect(dialog).not.toBeVisible({ timeout: 10000 });

    // 4. Verify no asset was created
    const machineCount = await page.evaluate(async () => {
      const db = (window as any).sqliteService;
      const result = await db.query('SELECT COUNT(*) as count FROM machines');
      return result[0].count;
    });
    expect(machineCount).toBe(0);
  });

  test('should prevent creation with empty instance name', async ({ page }, testInfo) => {
    await gotoWithWorkerDb(page, '/assets', testInfo, { waitForDb: false });
    try {
      const dismissBtn = page.getByRole('button', { name: /Get Started|Skip|Close/i }).first();
      if (await dismissBtn.isVisible({ timeout: 5000 })) {
        await dismissBtn.click();
      }
    } catch (e) {
      console.log('Welcome dialog not found or could not be dismissed.');
    }
    const assetsPage = new AssetsPage(page);
    await assetsPage.waitForOverlaysToDismiss();

    // Mock APIs
    await page.route('**/api/v1/machines/definitions?*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            accession_id: 'mach_test_001',
            name: 'Hamilton STAR',
            fqn: 'pylabrobot.liquid_handling.backends.hamilton.STAR',
            plr_category: 'Machine',
            machine_category: 'Liquid Handler',
            manufacturer: 'Hamilton',
            description: 'Hamilton STAR liquid handler',
            available_simulation_backends: ['Simulated']
          }
        ])
      });
    });

    // Navigate to the configuration step
    await assetsPage.addMachineButton.click();
    const wizard = page.locator('app-asset-wizard');
    await expect(wizard.locator('mat-card').first()).toBeVisible({ timeout: 15000 });
    await assetsPage.selectWizardCard(wizard, 'asset-type-card-Machine');
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Select Category/i);
    await assetsPage.selectWizardCard(wizard, 'category-card-LiquidHandler');
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Select Machine Type/i);
    await wizard.getByLabel('Search Definitions').fill('STAR');
    const resultCard = wizard.locator('.result-card').first();
    await expect(resultCard).toBeVisible({ timeout: 5000 });
    await resultCard.click();
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Select Driver/i);
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Configuration/i);

    // Verify Next button is disabled
    const nextButton = wizard.locator('.mat-step-content:visible').first().getByTestId('wizard-next-button');
    await expect(nextButton).toBeDisabled();

    // Fill the name and verify the button is enabled
    await wizard.getByLabel('Instance Name').fill('Test Name');
    await expect(nextButton).toBeEnabled();
  });

  test('should display empty state when no definitions match', async ({ page }, testInfo) => {
    await gotoWithWorkerDb(page, '/assets', testInfo, { waitForDb: false });
    try {
      const dismissBtn = page.getByRole('button', { name: /Get Started|Skip|Close/i }).first();
      if (await dismissBtn.isVisible({ timeout: 5000 })) {
        await dismissBtn.click();
      }
    } catch (e) {
      console.log('Welcome dialog not found or could not be dismissed.');
    }
    const assetsPage = new AssetsPage(page);
    await assetsPage.waitForOverlaysToDismiss();

    // Mock API to return empty array
    await page.route('**/api/v1/machines/definitions?*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    // Navigate to the search step
    await assetsPage.addMachineButton.click();
    const wizard = page.locator('app-asset-wizard');
    await expect(wizard.locator('mat-card').first()).toBeVisible({ timeout: 15000 });
    await assetsPage.selectWizardCard(wizard, 'asset-type-card-Machine');
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Select Category/i);
    await assetsPage.selectWizardCard(wizard, 'category-card-LiquidHandler');
    await assetsPage.clickNextButton(wizard);
    await assetsPage.waitForStepTransition(wizard, /Select Machine Type/i);

    // Search for a non-existent machine
    await wizard.getByLabel('Search Definitions').fill('XYZ_NONEXISTENT');

    // Verify empty state message
    const emptyState = wizard.getByText('No definitions found');
    await expect(emptyState).toBeVisible({ timeout: 5000 });

    // Verify Next button is disabled
    const nextButton = wizard.locator('.mat-step-content:visible').first().getByTestId('wizard-next-button');
    await expect(nextButton).toBeDisabled();
  });
});
