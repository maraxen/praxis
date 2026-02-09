import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { AssetsPage } from '../page-objects/assets.page';
import { WelcomePage } from '../page-objects/welcome.page';
import { WizardPage } from '../page-objects/wizard.page';
import { ProtocolPage } from '../page-objects/protocol.page';
import { ExecutionMonitorPage } from '../page-objects/monitor.page';

test.describe('User Journeys', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    // 1. Bypass login token check if needed
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'fake-token');
      localStorage.setItem('auth_user', JSON.stringify({ username: 'test_user' }));
    });

    // 2. Initial Navigation with browser mode + worker DB isolation
    await gotoWithWorkerDb(page, '/app/home', testInfo);

    // 3. Handle Welcome Dialog
    const welcomePage = new WelcomePage(page, testInfo);

    // 4. Ensure Shell is loaded as a sanity check
    await expect(page.locator('.sidebar-rail')).toBeVisible({ timeout: 10000 });
  });

  test('Asset Management: View and Create Machine', async ({ page }, testInfo) => {
    const assetsPage = new AssetsPage(page, testInfo);

    // Navigate with proper isolation
    await gotoWithWorkerDb(page, '/app/assets', testInfo);
    await assetsPage.navigateToMachines();

    // Create using POM method (already handles all wizard steps)
    await assetsPage.createMachine('New Robot', 'LiquidHandler');

    // Verify persistence (Phase 3)
    await assetsPage.verifyAssetVisible('New Robot');

    // Optional: Deep verification via evaluate
    const assetExists = await page.evaluate(async () => {
      const e2e = (window as any).__e2e;
      if (!e2e) return false;
      const rows = await e2e.query("SELECT name FROM machines WHERE name = 'New Robot'");
      return rows.length > 0;
    });
    expect(assetExists).toBe(true);
  });

  test('Protocol Workflow: Select and Run', async ({ page }, testInfo) => {
    const wizard = new WizardPage(page, testInfo);
    const protocolPage = new ProtocolPage(page, testInfo);

    await gotoWithWorkerDb(page, '/app/protocols', testInfo);

    // Click run on Simple Transfer
    await protocolPage.runProtocol('Simple Transfer');

    await page.waitForURL(/.*\/run/);

    // Use WizardPage methods
    // In Browser mode, the wizard starts at step 1 even if protocol is pre-selected
    await wizard.completeProtocolStep();
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

  test('Protocol Workflow: Completion and Logs Validation', async ({ page }, testInfo) => {
    const wizard = new WizardPage(page, testInfo);
    const protocolPage = new ProtocolPage(page, testInfo);
    const monitor = new ExecutionMonitorPage(page, testInfo);

    await gotoWithWorkerDb(page, '/app/protocols', testInfo);

    // Click run on Simple Transfer
    await protocolPage.runProtocol('Simple Transfer');
    await page.waitForURL(/.*\/run/);

    // Complete wizard
    await wizard.completeProtocolStep();
    await wizard.completeParameterStep();
    await wizard.selectFirstCompatibleMachine();
    await wizard.waitForAssetsAutoConfigured();
    await wizard.advanceDeckSetup();
    await wizard.openReviewStep();
    await wizard.startExecution();

    // Verify execution started
    await page.waitForURL('**/run/live');

    // Wait for completion (using the newly added method in monitor.page.ts)
    await monitor.assertProtocolCompleted();

    // Verify logs
    const logPanel = page.getByTestId('log-panel');
    const logs = await logPanel.textContent();
    expect(logs).toContain('[Protocol Execution Complete]');
    expect(logs).toContain('[Browser Mode] Execution completed successfully.');
  });
});