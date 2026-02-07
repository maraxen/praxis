import { test, expect } from '../fixtures/worker-db.fixture';
import { ProtocolPage } from '../page-objects/protocol.page';
import { WizardPage } from '../page-objects/wizard.page';
import { WelcomePage } from '../page-objects/welcome.page';

test.describe('Run Protocol - Machine Selection', () => {
    test('should navigate and select a simulated machine', async ({ page }) => {
        const welcomePage = new WelcomePage(page);
        const protocolPage = new ProtocolPage(page);
        const wizardPage = new WizardPage(page);

        await protocolPage.goto();
        await welcomePage.handleSplashScreen();

        await protocolPage.selectFirstProtocol();
        await protocolPage.continueFromSelection();

        await wizardPage.completeParameterStep();

        // Machine selection assertions using wizard methods
        await wizardPage.verifyMachineStepVisible();
        await wizardPage.selectFirstSimulatedMachine();
        await wizardPage.verifyContinueEnabled();
        // Now, let's verify the selection was persisted
        const machineCard = page.locator('app-machine-card').filter({ hasText: /Simulated/i }).first();
        const accessionId = await machineCard.getAttribute('data-accession-id');
        expect(accessionId).not.toBeNull();
        await wizardPage.verifyMachineSelected(accessionId!);
    });

    test('should prevent selection of incompatible machine', async ({ page }) => {
        const welcomePage = new WelcomePage(page);
        const protocolPage = new ProtocolPage(page);
        const wizardPage = new WizardPage(page);

        await protocolPage.goto();
        await welcomePage.handleSplashScreen();

        // This protocol is known to have machine requirements
        await protocolPage.selectProtocolByName('Kinetic Assay');
        await protocolPage.continueFromSelection();

        await wizardPage.completeParameterStep();
        await wizardPage.verifyMachineStepVisible();

        await wizardPage.selectIncompatibleMachine();

        // Assert that selection did not change and continue is disabled
        const continueButton = page.locator('[data-tour-id="run-step-machine"]').getByRole('button', { name: /Continue/i });
        await expect(continueButton).toBeDisabled();
    });

    test('should block simulated machines in physical mode', async ({ page }) => {
        const welcomePage = new WelcomePage(page);
        const protocolPage = new ProtocolPage(page);
        const wizardPage = new WizardPage(page);

        await page.goto('/app/run?mode=physical');
        await welcomePage.handleSplashScreen();

        await protocolPage.selectFirstProtocol();
        await protocolPage.continueFromSelection();

        await wizardPage.completeParameterStep();
        await wizardPage.verifyMachineStepVisible();

        // Assert simulated machines are disabled
        const simulatedCard = page
            .locator('app-machine-card')
            .filter({ hasText: /Simulated/i })
            .first();
        const isDisabled = await simulatedCard.evaluate(el => el.classList.contains('disabled'));
        expect(isDisabled).toBe(true);

        // Attempt to click and verify no selection change
        await simulatedCard.click({ force: true }); // Force click to ensure no selection
        await wizardPage.verifyMachineSelected('');
    });

    test('should handle machine fetch failure gracefully', async ({ page }) => {
        // Intercept and fail the machine list request
        await page.route('**/api/machines**', route => route.abort());

        const welcomePage = new WelcomePage(page);
        const protocolPage = new ProtocolPage(page);
        const wizardPage = new WizardPage(page);

        await protocolPage.goto();
        await welcomePage.handleSplashScreen();

        await protocolPage.selectFirstProtocol();
        await protocolPage.continueFromSelection();

        await wizardPage.completeParameterStep();
        await wizardPage.verifyMachineStepVisible();

        // Verify error state
        await expect(page.getByText(/Failed to load machines/i)).toBeVisible();
    });
});
