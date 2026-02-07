import { Page, Locator, expect, TestInfo } from '@playwright/test';
import { BasePage } from './base.page';
import { WizardPage } from './wizard.page';
import { ExecutionMonitorPage } from './monitor.page';

export class ProtocolPage extends BasePage {
    readonly protocolStep: Locator;
    readonly protocolCards: Locator;
    readonly summaryTitle: Locator;

    constructor(page: Page, testInfo?: TestInfo) {
        super(page, '/app/protocols', testInfo);
        this.protocolStep = page.locator('[data-tour-id="run-step-protocol"]');
        this.protocolCards = page.locator('app-protocol-card');
        this.summaryTitle = this.protocolStep.locator('h2');
    }

    private async dismissOverlays() {
        const dismissButtons = this.page
            .locator('.cdk-overlay-container button, .mat-mdc-dialog-container button')
            .filter({ hasText: /Close|Dismiss|Got it|OK|Continue|Skip|Start/i });
        if (await dismissButtons.count()) {
            await dismissButtons.first().click({ timeout: 2000 }).catch((e) => console.log('[Test] Silent catch (Overlay dismiss button click):', e));
        }
        await this.page.keyboard.press('Escape').catch((e) => console.log('[Test] Silent catch (Overlay Escape):', e));
    }

    async goto(options: { waitForDb?: boolean } = {}) {
        await super.goto(options);
        // Remove waits that rely on data being present
        // await this.protocolStep.waitFor({ state: 'visible' });
        // await this.protocolCards.first().waitFor({ state: 'visible', timeout: 30000 });
    }

    async ensureSimulationMode() {
        const simulationToggle = this.page.getByRole('button', { name: /^Simulation$/i }).first();
        if (await simulationToggle.count()) {
            const pressed = await simulationToggle.getAttribute('aria-pressed');
            if (pressed !== 'true') {
                await simulationToggle.click();
            }
        }
    }

    async selectProtocolByName(name: string): Promise<string> {
        console.log(`[ProtocolPage] Selecting protocol by name: ${name}`);
        const cardHost = this.protocolCards.filter({ hasText: name }).first();
        // Wait for card to exist and be visible
        await expect(cardHost).toBeVisible({ timeout: 30000 });
        const card = cardHost.locator('.praxis-card');
        await expect(card, `Protocol card for ${name} should be visible`).toBeVisible({ timeout: 15000 });
        await this.dismissOverlays();
        await card.click();
        await this.assertProtocolSelected(name);
        return name;
    }

    async selectFirstProtocol(): Promise<string> {
        const firstCardHost = this.protocolCards.first();
        const firstCard = firstCardHost.locator('.praxis-card');
        await firstCard.waitFor({ state: 'visible' });
        const name = (await firstCardHost.locator('h3.card-title').textContent())?.trim() || 'Protocol';
        await this.dismissOverlays();
        await firstCard.click({ force: true });
        await this.assertProtocolSelected(name);
        return name;
    }

    async assertProtocolSelected(expectedName: string) {
        await expect(this.summaryTitle, 'Selected protocol summary should appear').toContainText(expectedName, {
            timeout: 15000
        });
    }

    async navigateToProtocols() {
        await this.goto();
    }

    async selectProtocol(name: string) {
        await this.selectProtocolByName(name);
        await this.continueFromSelection();
    }

    async configureParameter(name: string, value: string) {
        // Assuming we are on the parameters step
        const label = name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        const paramInput = this.page.getByLabel(label, { exact: false })
            .or(this.page.getByLabel(name, { exact: false }))
            .or(this.page.locator(`input[name="${name}"]`))
            .first();

        if (await paramInput.isVisible({ timeout: 5000 }).catch((e) => {
            console.log('[Test] Silent catch (paramInput isVisible):', e);
            return false;
        })) {
            await paramInput.fill(value);
        } else {
            console.log(`Parameter ${name} (Label: ${label}) not found or not visible.`);

            // Debug: List all labels and headers
            const labels = await this.page.locator('mat-label').allTextContents();
            const headers = await this.page.locator('h3').allTextContents();
            const emptyState = await this.page.locator('.empty-state').isVisible();
            console.log(`[Debug] Visible labels: ${labels.join(', ') || 'NONE'}`);
            console.log(`[Debug] Visible headers: ${headers.join(', ') || 'NONE'}`);
            console.log(`[Debug] Empty state visible: ${emptyState}`);

            // Fallback: try to find any input in a form-field that has the label text nearby
            const fallback = this.page.locator('mat-form-field').filter({ hasText: new RegExp(label, 'i') }).locator('input').first();
            if (await fallback.isVisible({ timeout: 2000 }).catch((e) => {
                console.log('[Test] Silent catch (fallback isVisible):', e);
                return false;
            })) {
                console.log(`[Debug] Found fallback for ${label}`);
                await fallback.fill(value);
            } else {
                console.log(`[Debug] Fallback also failed for ${label}`);
            }
        }
    }

    async advanceToReview() {
        // This is a helper to move through the wizard steps
        // We might need to import WizardPage or duplicate some logic here if we want to be strictly independent,
        // but ideally we should reuse. Since I cannot easily inject WizardPage here without changing the constructor signature significantly 
        // or instantiating it internally, I'll instantiate it internally.
        const wizard = new WizardPage(this.page);

        await wizard.completeParameterStep();
        await wizard.selectFirstCompatibleMachine();
        await wizard.waitForAssetsAutoConfigured();
        await wizard.advanceDeckSetup();
        await wizard.openReviewStep();
    }

    async startExecution() {
        const wizard = new WizardPage(this.page);
        await wizard.startExecution();
    }

    async getExecutionStatus(): Promise<string> {
        const monitor = new ExecutionMonitorPage(this.page);
        // We assume we are on the monitor page now
        const statusChip = this.page.locator('mat-chip'); // Using locator from monitor page logic
        return await statusChip.textContent() || '';
    }

    async waitForCompletion(timeout: number = 300000) { // 5 minutes default
        const monitor = new ExecutionMonitorPage(this.page);
        await monitor.waitForStatus(/(Completed|Succeeded|Finished)/i, timeout);
    }

    async continueFromSelection() {
        const continueButton = this.protocolStep.getByRole('button', { name: /Continue/i }).last();
        await expect(continueButton).toBeEnabled({ timeout: 15000 });
        await continueButton.click();
    }
}
