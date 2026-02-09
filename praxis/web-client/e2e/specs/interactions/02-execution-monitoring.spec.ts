import { test, expect } from '../../fixtures/worker-db.fixture';
import { WelcomePage } from '../../page-objects/welcome.page';
import { ProtocolPage } from '../../page-objects/protocol.page';
import { WizardPage } from '../../page-objects/wizard.page';
import { ExecutionMonitorPage } from '../../page-objects/monitor.page';

test.describe('Execution Monitoring', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    const welcomePage = new WelcomePage(page, testInfo);
    await welcomePage.goto();
  });

  test('should display execution log panel during protocol run', async ({ page }, testInfo) => {
    const protocolPage = new ProtocolPage(page, testInfo);
    const wizardPage = new WizardPage(page, testInfo);
    const monitorPage = new ExecutionMonitorPage(page, testInfo);

    // 1. Navigate to protocols and start a run
    await protocolPage.goto();
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

    // 2. Verify the log panel is visible
    // The execution logs section has a heading 'Execution Logs' followed by log entry divs
    const logHeading = page.getByText('Execution Logs');
    await expect(logHeading).toBeVisible({ timeout: 30000 });

    // Verify at least one log entry exists beneath
    const logEntry = page.locator('.execution-logs >> div, [class*="log-entry"]').first();
    await expect(logEntry).toBeVisible({ timeout: 10000 });
  });
});
