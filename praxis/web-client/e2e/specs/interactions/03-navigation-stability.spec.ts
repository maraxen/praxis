import { test, expect } from '../../fixtures/worker-db.fixture';
import { WelcomePage } from '../../page-objects/welcome.page';
import { ProtocolPage } from '../../page-objects/protocol.page';
import { WizardPage } from '../../page-objects/wizard.page';
import { ExecutionMonitorPage } from '../../page-objects/monitor.page';
import { SettingsPage } from '../../page-objects/settings.page';

test.describe('Navigation Stability', () => {
  test.beforeEach(async ({ page }) => {
    page.on('console', msg => {
      if (msg.type() === 'error' || msg.type() === 'warning' || msg.text().includes('[RunProtocol]')) {
        console.log(`[Browser ${msg.type()}] ${msg.text()}`);
      }
    });
  });

  test('should remain live when navigating away and back during execution', async ({ page }, testInfo) => {
    const protocolPage = new ProtocolPage(page, testInfo);
    const wizardPage = new WizardPage(page);
    const monitorPage = new ExecutionMonitorPage(page, testInfo);
    const settingsPage = new SettingsPage(page, testInfo);

    // 1. Start execution
    await protocolPage.goto();
    const welcomePage = new WelcomePage(page, testInfo);
    await welcomePage.handleSplashScreen();

    await protocolPage.ensureSimulationMode();
    await protocolPage.selectFirstProtocol();
    await protocolPage.continueFromSelection();
    await wizardPage.completeParameterStep();
    await wizardPage.selectFirstCompatibleMachine();
    await wizardPage.waitForAssetsAutoConfigured();
    await wizardPage.completeWellSelectionStep();
    await wizardPage.advanceDeckSetup();
    await wizardPage.openReviewStep();
    await wizardPage.startExecution();

    await monitorPage.waitForLiveDashboard();
    await monitorPage.waitForStatus(/RUNNING/);

    // 2. Navigate away to Settings
    await settingsPage.goto();
    await expect(page).toHaveURL(/\/settings/);

    // 3. Navigate back to Monitor
    await monitorPage.goto();
    await monitorPage.waitForLiveDashboard();

    // 4. Verify status is still visible and running
    await monitorPage.waitForStatus(/RUNNING|COMPLETED/);
  });

  test('should block navigation when wizard has progress', async ({ page }, testInfo) => {
    const protocolPage = new ProtocolPage(page, testInfo);

    // 1. Start wizard
    await protocolPage.goto();
    const welcomePage = new WelcomePage(page, testInfo);
    await welcomePage.handleSplashScreen();

    await protocolPage.ensureSimulationMode();
    await protocolPage.selectFirstProtocol();
    await protocolPage.continueFromSelection();

    // 2. Try to navigate to Settings via sidebar
    await page.locator('[data-tour-id="nav-settings"]').click();

    // 3. Confirm dialog appears
    const dialog = page.getByRole('dialog').filter({ hasText: /Unsaved Changes/i });
    await expect(dialog).toBeVisible();

    // 4. Stay on page
    await dialog.getByRole('button', { name: /Stay/i }).click();
    await expect(page).toHaveURL(/\/run/);

    // 5. Try again and leave
    await page.locator('[data-tour-id="nav-settings"]').click();
    await page.getByRole('dialog').filter({ hasText: /Unsaved Changes/i }).getByRole('button', { name: /Leave/i }).click();
    await expect(page).toHaveURL(/\/settings/);
  });

  test('should hydrate wizard state after navigating away and back', async ({ page }, testInfo) => {
    const protocolPage = new ProtocolPage(page, testInfo);
    const wizardPage = new WizardPage(page);

    // 1. Progress wizard to a deep step
    await protocolPage.goto();
    const welcomePage = new WelcomePage(page, testInfo);
    await welcomePage.handleSplashScreen();

    await protocolPage.ensureSimulationMode();
    const name = await protocolPage.selectFirstProtocol();
    await protocolPage.continueFromSelection();
    await wizardPage.completeParameterStep();

    // Now on Machine Step
    await expect(page.locator('[data-tour-id="run-step-machine"]')).toBeVisible();

    // 2. Navigate away (confirming the dialog)
    await page.locator('[data-tour-id="nav-settings"]').click();
    await page.getByRole('dialog').filter({ hasText: /Unsaved Changes/i }).getByRole('button', { name: /Leave/i }).click();
    await expect(page).toHaveURL(/\/settings/);

    // 3. Navigate back to Run
    await page.locator('[data-tour-id="nav-run"]').click();

    // 4. Verify state is hydrated (should still be on Machine Step)
    await expect(page.locator('[data-tour-id="run-step-machine"]')).toBeVisible({ timeout: 10000 });
    
    // 5. Verify protocol selection is preserved
    await expect(page.locator('app-run-protocol')).toContainText(name);
  });
});
