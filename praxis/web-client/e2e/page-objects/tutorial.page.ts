import { Page, Locator, expect } from '@playwright/test';

export class TutorialPage {
    readonly page: Page;
    readonly stepContent: Locator;

    constructor(page: Page) {
        this.page = page;
        this.stepContent = page.locator('.shepherd-text');
    }

    async verifyStepVisible(text: string | RegExp) {
        await expect(this.page.getByText(text)).toBeVisible();
    }

    async startTour() {
        await this.page.getByRole('button', { name: 'Start Tour' }).click();
    }

    async next() {
        await this.page.getByRole('button', { name: 'Next' }).click();
    }

    async skipSection() {
        // Shepherd often has multiple elements in DOM during transition
        await this.page.getByRole('button', { name: 'Skip Section' }).first().click();
    }

    async finish() {
        await this.page.getByRole('button', { name: 'Finish' }).click();
    }

    async verifyClosed() {
        await expect(this.stepContent).not.toBeVisible();
    }
}
