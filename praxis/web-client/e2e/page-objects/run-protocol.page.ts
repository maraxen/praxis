import { expect, Locator, Page } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Page object for the Run Protocol wizard flow.
 * Used for browser mode execution testing.
 */
export class RunProtocolPage extends BasePage {
    readonly protocolCards: Locator;
    readonly machineSelection: Locator;
    readonly continueButton: Locator;
    readonly startExecutionButton: Locator;

    constructor(page: Page) {
        super(page, '/run');
        this.protocolCards = page.locator('.protocol-card, [data-testid="protocol-card"]');
        this.machineSelection = page.locator('app-machine-selection, [data-testid="machine-selection"]');
        this.continueButton = page.locator('button:has-text("Continue"), button:has-text("Next")');
        this.startExecutionButton = page.locator('button:has-text("Start"), button:has-text("Run")');
    }

    /**
     * Wait for protocols to be loaded in the wizard
     */
    async waitForProtocolsLoaded(): Promise<void> {
        await this.page.waitForSelector('.protocol-card, [data-testid="protocol-card"], app-protocol-selector', {
            timeout: 30000,
            state: 'visible',
        }).catch(() => {
            // Protocol cards may not exist, that's ok
        });
        // Ensure UI is stable
        await this.page.waitForLoadState('domcontentloaded');
    }

    /**
     * Select the first available protocol
     */
    async selectFirstProtocol(): Promise<void> {
        const firstCard = this.protocolCards.first();
        if (await firstCard.isVisible({ timeout: 5000 })) {
            await firstCard.click();
        } else {
            // Try alternative: table row
            const tableRow = this.page.locator('table tbody tr').first();
            if (await tableRow.isVisible({ timeout: 2000 })) {
                await tableRow.click();
            }
        }
    }

    /**
     * Select the first available machine
     */
    async selectFirstMachine(): Promise<void> {
        const machineCard = this.page.locator('.machine-card, [data-testid="machine-card"]').first();
        if (await machineCard.isVisible({ timeout: 5000 })) {
            await machineCard.click();
        } else {
            // Try alternative: radio button or list item
            const radioBtn = this.machineSelection.locator('input[type="radio"]').first();
            if (await radioBtn.isVisible({ timeout: 2000 })) {
                await radioBtn.click();
            }
        }
    }

    /**
     * Advance to the next step in the wizard
     */
    async advanceStep(): Promise<void> {
        await this.continueButton.click();
        // Wait for step transition to complete
        await this.page.waitForLoadState('domcontentloaded');
    }

    /**
     * Start the protocol execution
     */
    async startExecution(): Promise<void> {
        await expect(this.startExecutionButton).toBeEnabled({ timeout: 10000 });
        await this.startExecutionButton.click();
    }
}
