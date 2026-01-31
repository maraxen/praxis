import { expect, Locator, Page } from '@playwright/test';

export class DeckSetupPage {
    private readonly page: Page;
    private readonly wizardRoot: Locator;
    private readonly carrierStep: Locator;
    private readonly resourceStep: Locator;
    private readonly verificationStep: Locator;
    private readonly skipButton: Locator;
    private readonly nextButton: Locator;
    private readonly backButton: Locator;
    private readonly confirmButton: Locator;

    constructor(page: Page) {
        this.page = page;
        this.wizardRoot = page.locator('app-deck-setup-wizard');
        this.carrierStep = page.locator('app-carrier-placement-step');
        this.resourceStep = page.locator('app-resource-placement-step');
        this.verificationStep = page.locator('app-verification-step');
        this.skipButton = this.wizardRoot.getByRole('button', { name: /Skip Setup/i });
        this.nextButton = this.wizardRoot.getByRole('button', { name: /Next/i });
        this.backButton = this.wizardRoot.getByRole('button', { name: /Back/i });
        this.confirmButton = this.wizardRoot.getByRole('button', { name: /Confirm & Continue/i });
    }

    async waitForWizardVisible() {
        await expect(this.wizardRoot).toBeVisible({ timeout: 15000 });
    }

    async isOnCarrierStep(): Promise<boolean> {
        return this.carrierStep.isVisible({ timeout: 2000 }).catch(() => false);
    }

    async isOnResourceStep(): Promise<boolean> {
        return this.resourceStep.isVisible({ timeout: 2000 }).catch(() => false);
    }

    async isOnVerificationStep(): Promise<boolean> {
        return this.verificationStep.isVisible({ timeout: 2000 }).catch(() => false);
    }

    async getProgress(): Promise<number> {
        const bar = this.wizardRoot.locator('mat-progress-bar');
        const value = await bar.getAttribute('aria-valuenow');
        return value ? parseInt(value, 10) : 0;
    }

    async markCarrierPlaced(carrierName: string) {
        const carrierItem = this.carrierStep.locator('.carrier-item', { hasText: carrierName });
        const checkbox = carrierItem.locator('mat-checkbox, input[type="checkbox"]');
        await checkbox.check();
    }

    async markAllCarriersPlaced() {
        const items = this.carrierStep.locator('.carrier-item');
        const count = await items.count();
        for (let i = 0; i < count; i++) {
            const checkbox = items.nth(i).locator('mat-checkbox, input[type="checkbox"]');
            if (!(await checkbox.isChecked())) {
                await checkbox.check();
            }
        }
    }

    async advanceToResourceStep() {
        await this.markAllCarriersPlaced();
        await this.nextButton.click();
        await expect(this.resourceStep).toBeVisible({ timeout: 5000 });
    }

    async markAllResourcesPlaced() {
        const items = this.resourceStep.locator('.assignment-item');
        const count = await items.count();
        for (let i = 0; i < count; i++) {
            const checkbox = items.nth(i).locator('mat-checkbox, input[type="checkbox"]');
            if (!(await checkbox.isChecked())) {
                await checkbox.check();
            }
        }
    }

    async advanceToVerificationStep() {
        await this.markAllResourcesPlaced();
        await this.nextButton.click();
        await expect(this.verificationStep).toBeVisible({ timeout: 5000 });
    }

    async confirmSetup() {
        await expect(this.confirmButton).toBeEnabled();
        await this.confirmButton.click();
    }

    async skipSetup() {
        await this.skipButton.click();
    }

    async getWizardState(): Promise<{currentStep: string, progress: number}> {
        return this.page.evaluate(() => {
            const cmp = (window as any).ng?.getComponent?.(document.querySelector('app-deck-setup-wizard'));
            return {
                currentStep: cmp?.wizardState?.currentStep?.() || 'unknown',
                progress: cmp?.wizardState?.progress?.() || 0
            };
        });
    }
}
