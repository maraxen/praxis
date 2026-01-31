import { test, expect } from '../../fixtures/worker-db.fixture';
import { WelcomePage } from '../../page-objects/welcome.page';
import { ProtocolPage } from '../../page-objects/protocol.page';
import { WizardPage } from '../../page-objects/wizard.page';
import { ExecutionMonitorPage } from '../../page-objects/monitor.page';
import { SettingsPage } from '../../page-objects/settings.page';

test.describe('Navigation Stability', () => {
  test.beforeEach(async ({ page }) => {
    const welcomePage = new WelcomePage(page);
    await welcomePage.goto();
    await welcomePage.handleSplashScreen();
  });

  test('should remain live when navigating away and back during execution', async ({ page }) => {
    const protocolPage = new ProtocolPage(page);
    const wizardPage = new WizardPage(page);
    const monitorPage = new ExecutionMonitorPage(page);
    const settingsPage = new SettingsPage(page);

    // 1. Start execution
    await protocolPage.goto();
    await protocolPage.ensureSimulationMode();
    await protocolPage.selectFirstProtocol();
    await protocolPage.continueFromSelection();
    await wizardPage.completeParameterStep();
    await wizardPage.selectFirstCompatibleMachine();
    await wizardPage.waitForAssetsAutoConfigured();
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
});
