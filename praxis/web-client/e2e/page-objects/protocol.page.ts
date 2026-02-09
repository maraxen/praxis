import { Page, Locator, expect, TestInfo } from '@playwright/test';
import { BasePage } from './base.page';
import { WizardPage } from './wizard.page';
import { ExecutionMonitorPage } from './monitor.page';

export class ProtocolPage extends BasePage {
    readonly protocolStep: Locator;
    readonly protocolCards: Locator;
    readonly summaryTitle: Locator;

    constructor(page: Page, testInfo?: TestInfo) {
        // Navigate to /app/run (Execute Protocol wizard) where protocolStep/protocolCards selectors exist
        super(page, '/app/run', testInfo);
        this.protocolStep = page.locator('[data-tour-id="run-step-protocol"]');
        this.protocolCards = page.locator('app-protocol-card');
        this.summaryTitle = this.protocolStep.locator('h2');
    }

    private async dismissOverlays() {
        const dismissButtons = this.page
            .locator('.cdk-overlay-container button, .mat-mdc-dialog-container button')
            .filter({ hasText: /Close|Dismiss|Got it|OK|Continue|Skip|Start/i });
        if (await dismissButtons.count() > 0) {
            await dismissButtons.first().click({ timeout: 2000 });
        }
        // Only press Escape if an overlay backdrop is visible
        const backdrop = this.page.locator('.cdk-overlay-backdrop');
        if (await backdrop.count() > 0 && await backdrop.first().isVisible()) {
            await this.page.keyboard.press('Escape');
        }
    }

    override async goto(options: { waitForDb?: boolean } = {}) {
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
        await expect(cardHost).toBeVisible({ timeout: 30000 });
        const card = cardHost.locator('.praxis-card');
        await expect(card, `Protocol card for ${name} should be visible`).toBeVisible({ timeout: 15000 });
        await this.dismissOverlays();

        // Click and wait for selection to render (h2 inside @if block)
        await card.click({ delay: 50 });
        await this.assertProtocolSelected(name);

        return name;
    }

    async selectFirstProtocol(): Promise<string> {
        // Wait for protocol cards (wizard view)
        const firstCardVisible = await this.protocolCards.first().isVisible({ timeout: 5000 });
        if (firstCardVisible) {
            const firstCardHost = this.protocolCards.first();
            const firstCard = firstCardHost.locator('.praxis-card');
            await firstCard.waitFor({ state: 'visible' });
            await this.dismissOverlays();

            // Click card to trigger selection — name will be read from h2 summary after render
            await firstCard.click({ delay: 50 });
            const name = await this.waitForProtocolSelected();

            return name;
        }

        // Fallback for Library view (table) if we ended up there
        const tableRow = this.page.locator('[data-tour-id="protocol-table"] tbody tr').first();
        const tableVisible = await tableRow.isVisible({ timeout: 5000 });
        if (tableVisible) {
            await tableRow.click();
            const runButton = this.page.getByRole('button', { name: /Run Protocol/i });
            await expect(runButton).toBeVisible({ timeout: 10000 });
            await runButton.click();
            const name = await this.waitForProtocolSelected();
            return name;
        }

        throw new Error('No protocols found in either card or table view');
    }

    /**
     * Waits for the protocol summary h2 to appear (renders inside @if(selectedProtocol()) block)
     * and returns the protocol name from it. This is the authoritative source — the h2 only
     * contains {{ selectedProtocol()?.name }}, free of badge text like "Top Level".
     */
    async waitForProtocolSelected(): Promise<string> {
        const summaryEl = this.protocolStep.getByRole('heading', { level: 2 });
        await expect(summaryEl, 'Selected protocol summary should appear').toBeVisible({ timeout: 15000 });
        const name = (await summaryEl.innerText())?.trim() || 'Protocol';
        return name;
    }

    /**
     * Asserts protocol is selected by checking the h2 heading contains the expected name.
     */
    async assertProtocolSelected(expectedName: string) {
        const summaryEl = this.protocolStep.getByRole('heading', { level: 2 });
        await expect(summaryEl, 'Selected protocol summary should appear').toContainText(expectedName, {
            timeout: 15000
        });
    }

    async navigateToProtocols() {
        await this.goto();
    }

    /** Navigate to the Protocol Library page (table view at /app/protocols) */
    async navigateToLibrary() {
        const url = new URL(this.page.url() || 'http://localhost:4200');
        url.pathname = '/app/protocols';
        url.searchParams.set('mode', 'browser');
        if (this.testInfo) {
            url.searchParams.set('dbName', `praxis-worker-${this.testInfo.workerIndex}`);
        }
        await this.page.goto(url.toString(), { waitUntil: 'domcontentloaded' });
    }

    async selectProtocol(name: string): Promise<string> {
        await this.selectProtocolByName(name);
        await this.continueFromSelection();
        return name;
    }

    async configureParameter(name: string, value: string) {
        // Assuming we are on the parameters step
        const label = name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        const paramInput = this.page.getByLabel(label, { exact: false })
            .or(this.page.getByLabel(name, { exact: false }))
            .or(this.page.locator(`input[name="${name}"]`))
            .first();

        const isVisible = await paramInput.isVisible({ timeout: 5000 });
        if (isVisible) {
            await paramInput.fill(value);
        } else {
            console.log(`[ProtocolPage] Parameter ${name} (Label: ${label}) not found. Trying fallback.`);
            // Fallback: find any input in a form-field that has the label text nearby
            const fallback = this.page.locator('mat-form-field').filter({ hasText: new RegExp(label, 'i') }).locator('input').first();
            await expect(fallback, `Parameter input for '${label}' should be visible`).toBeVisible({ timeout: 5000 });
            await fallback.fill(value);
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
        await monitor.waitForLiveDashboard();
        const statusEl = this.page.getByTestId('run-status');
        return await statusEl.textContent() || '';
    }

    async waitForCompletion(timeout: number = 300000) { // 5 minutes default
        const monitor = new ExecutionMonitorPage(this.page);
        await monitor.waitForStatus(/(completed|succeeded|finished)/i, timeout);
    }

    /**
     * Asserts that a protocol with the given name is available in the library.
     */
    async assertProtocolAvailable(name: string): Promise<void> {
        const card = this.protocolCards.filter({ hasText: name });
        await expect(card.first()).toBeVisible({ timeout: 15000 });
    }

    /**
     * Finds a protocol by name and initiates a run.
     * Works with both card view (clicks card → Run) and table view (clicks row → Run Protocol button).
     */
    async runProtocol(name: string): Promise<void> {
        // Try card view first
        const card = this.protocolCards.filter({ hasText: name }).first();
        const cardVisible = await card.isVisible({ timeout: 5000 });
        if (cardVisible) {
            await this.dismissOverlays();
            await card.locator('.praxis-card').click();
            const runBtn = this.page.getByRole('button', { name: /Run|Start/i }).first();
            await expect(runBtn).toBeVisible({ timeout: 5000 });
            await runBtn.click();
            return;
        }

        // Fallback: table view
        const row = this.page.locator('tr').filter({ hasText: name }).first();
        await expect(row).toBeVisible({ timeout: 10000 });
        await row.click();
        const runProtocolBtn = this.page.getByRole('button', { name: /Run Protocol/i });
        await expect(runProtocolBtn).toBeVisible({ timeout: 5000 });
        await runProtocolBtn.click();
    }

    async continueFromSelection() {
        const continueButton = this.protocolStep.getByRole('button', { name: /Continue/i }).last();
        await expect(continueButton).toBeEnabled({ timeout: 15000 });
        await continueButton.click();
    }
}
