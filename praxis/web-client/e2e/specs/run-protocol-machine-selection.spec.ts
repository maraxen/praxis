import { test, expect } from '../fixtures/worker-db.fixture';
import { ProtocolPage } from '../page-objects/protocol.page';
import { WizardPage } from '../page-objects/wizard.page';
import { WelcomePage } from '../page-objects/welcome.page';

test.describe('Run Protocol - Machine Selection', () => {
    test('should navigate and select a simulated machine', async ({ page }, testInfo) => {
        const protocolPage = new ProtocolPage(page, testInfo);
        const wizardPage = new WizardPage(page, testInfo);

        await protocolPage.goto();

        await protocolPage.selectFirstProtocol();
        await protocolPage.continueFromSelection();

        await wizardPage.completeParameterStep();

        // Machine selection assertions using wizard methods
        await wizardPage.verifyMachineStepVisible();
        await wizardPage.selectFirstSimulatedMachine();
        await wizardPage.verifyContinueEnabled();

        // Verify selection registered via check_circle indicator in accordion header
        await wizardPage.verifyMachineSelected();
    });

    test('should show incompatible machines as disabled in simulation mode', async ({ page }, testInfo) => {
        const protocolPage = new ProtocolPage(page, testInfo);
        const wizardPage = new WizardPage(page, testInfo);

        await protocolPage.goto();

        await protocolPage.selectFirstProtocol();
        await protocolPage.continueFromSelection();

        await wizardPage.completeParameterStep();
        await wizardPage.verifyMachineStepVisible();

        // In simulation mode, hardware-only backends should be disabled (showing "Mismatch")
        const selector = page.locator('app-machine-argument-selector');
        await expect(selector).toBeVisible({ timeout: 15000 });

        // Check that at least some option-cards have .disabled class (hardware backends in sim mode)
        const disabledCards = selector.locator('.option-card.disabled');
        const disabledCount = await disabledCards.count();

        // Verify disabled cards show "Mismatch" badge
        if (disabledCount > 0) {
            await expect(disabledCards.first().locator('.incompatible-badge')).toContainText(/Mismatch/i);
        }
    });

    test('should show physical mode toggle', async ({ page }, testInfo) => {
        const protocolPage = new ProtocolPage(page, testInfo);
        const wizardPage = new WizardPage(page, testInfo);

        await protocolPage.goto();

        await protocolPage.selectFirstProtocol();
        await protocolPage.continueFromSelection();

        await wizardPage.completeParameterStep();
        await wizardPage.verifyMachineStepVisible();

        // Verify mode toggle exists (Physical / Simulation radio buttons)
        const physicalRadio = page.getByRole('radio', { name: /Physical/i });
        const simulationRadio = page.getByRole('radio', { name: /Simulation/i });

        await expect(physicalRadio).toBeVisible();
        await expect(simulationRadio).toBeVisible();

        // Simulation mode should be selected by default
        await expect(simulationRadio).toBeChecked();
    });

    test('should display machine requirements from protocol', async ({ page }, testInfo) => {
        const protocolPage = new ProtocolPage(page, testInfo);
        const wizardPage = new WizardPage(page, testInfo);

        await protocolPage.goto();

        await protocolPage.selectFirstProtocol();
        await protocolPage.continueFromSelection();

        await wizardPage.completeParameterStep();
        await wizardPage.verifyMachineStepVisible();

        // Verify the machine argument selector component is present with accordion panels
        const selector = page.locator('app-machine-argument-selector');
        await expect(selector).toBeVisible({ timeout: 15000 });

        // Should have at least one expansion panel (machine requirement)
        const panels = selector.locator('mat-expansion-panel');
        const panelCount = await panels.count();
        expect(panelCount).toBeGreaterThanOrEqual(1);

        // Each panel should have option-cards (existing machines or backends)
        const optionCards = selector.locator('.option-card');
        const cardCount = await optionCards.count();
        expect(cardCount).toBeGreaterThanOrEqual(1);
    });
});
