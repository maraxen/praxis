import { test as base, expect } from './worker-db.fixture';
import { ProtocolPage } from '../page-objects/protocol.page';
import { WizardPage } from '../page-objects/wizard.page';
import { ExecutionMonitorPage } from '../page-objects/monitor.page';

type ExecutionReadyFixtures = {
    executionContext: {
        protocolPage: ProtocolPage;
        wizardPage: WizardPage;
        monitorPage: ExecutionMonitorPage;
    };
};

export const test = base.extend<ExecutionReadyFixtures>({
    executionContext: async ({ page }, use, testInfo) => {
        // The app.fixture has already handled login, welcome dialogs, and DB setup.
        // We can proceed directly to the test-specific setup.

        const protocolPage = new ProtocolPage(page, testInfo);
        const wizardPage = new WizardPage(page);
        const monitorPage = new ExecutionMonitorPage(page, testInfo);

        await protocolPage.goto();
        await expect(protocolPage.protocolCards.first()).toBeVisible({ timeout: 30000 });
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

        await use({ protocolPage, wizardPage, monitorPage });

        // Cleanup: None needed for read-only deck inspection
    }
});

export { expect };
