import { test, expect } from '../fixtures/worker-db.fixture';
import { AssetsPage } from '../page-objects/assets.page';
import { WelcomePage } from '../page-objects/welcome.page';
import { WizardPage } from '../page-objects/wizard.page';
import { ProtocolPage } from '../page-objects/protocol.page';

test.describe('User Journeys', () => {
  test.beforeEach(async ({ page }) => {
    // 1. Bypass login token check if needed
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'fake-token');
      localStorage.setItem('auth_user', JSON.stringify({ username: 'test_user' }));
    });

    // 2. Initial Navigation with browser mode - manually to avoid base.page.ts issue
    await page.goto('/?mode=browser'); // Start at root
    await page.waitForURL('**/app/home**'); // Wait for redirect to home

    // 3. Handle Welcome Dialog
    const welcomePage = new WelcomePage(page);
    await welcomePage.handleSplashScreen();

    // 4. Ensure Shell is loaded as a sanity check
    await expect(page.locator('.sidebar-rail')).toBeVisible({ timeout: 10000 });
  });

  test('Asset Management: View and Create Machine', async ({ page }) => {
    const assetsPage = new AssetsPage(page);

    // Navigate with proper isolation
    await page.goto('/assets?mode=browser');
    await assetsPage.navigateToMachines();

    // Create using POM method (already handles all wizard steps)
    await assetsPage.createMachine('New Robot', 'LiquidHandler');

    // Verify persistence (Phase 3)
    await assetsPage.verifyAssetVisible('New Robot');

    // Optional: Deep verification via evaluate
    const assetExists = await page.evaluate(async () => {
      const db = (window as any).sqliteService?.db;
      if (!db) return false;
      const result = db.exec("SELECT name FROM machines WHERE name = 'New Robot'");
      return result.length > 0 && result[0].values.length > 0;
    });
    expect(assetExists).toBe(true);
  });

  test('Protocol Workflow: Select and Run', async ({ page }) => {
    const wizard = new WizardPage(page);
    const protocolPage = new ProtocolPage(page);

    await page.goto('/protocols?mode=browser');

    // Click run on Simple Transfer
    await protocolPage.runProtocol('Simple Transfer');

    await page.waitForURL(/.*\/run/);

    // Use WizardPage methods
    await wizard.completeParameterStep();
    await wizard.selectFirstCompatibleMachine();
    await wizard.waitForAssetsAutoConfigured();
    await wizard.advanceDeckSetup();
    await wizard.openReviewStep();
    await wizard.startExecution();

    // Verify execution started
    await page.waitForURL('**/run/live');

    // Verify execution status indicator
    await expect(page.getByTestId('execution-status')).toBeVisible();

    // Verify run appears in history (eventual consistency)
    await expect(async () => {
      const statusText = await page.getByTestId('execution-status').textContent();
      expect(['Running', 'Queued', 'Starting']).toContain(statusText);
    }).toPass({ timeout: 10000 });
  });
});