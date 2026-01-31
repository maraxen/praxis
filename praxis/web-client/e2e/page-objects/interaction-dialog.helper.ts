import { Page, Locator, expect } from '@playwright/test';

export class InteractionDialogHelper {
    readonly dialog: Locator;

    constructor(page: Page) {
        this.dialog = page.locator('app-interaction-dialog');
    }

    async waitForPause(expectedMessage: string): Promise<void> {
        await expect(this.dialog).toBeVisible({ timeout: 15000 });
        await expect(this.dialog).toContainText(expectedMessage);
        await expect(this.dialog.getByRole('button', { name: 'Resume' })).toBeVisible();
    }

    async resume(): Promise<void> {
        await this.dialog.getByRole('button', { name: 'Resume' }).click();
    }

    async waitForConfirm(expectedMessage: string): Promise<void> {
        await expect(this.dialog).toBeVisible({ timeout: 10000 });
        await expect(this.dialog).toContainText(expectedMessage);
    }

    async confirmYes(): Promise<void> {
        await this.dialog.getByRole('button', { name: 'Yes' }).click();
    }

    async confirmNo(): Promise<void> {
        await this.dialog.getByRole('button', { name: 'No' }).click();
    }

    async waitForInput(expectedPrompt: string): Promise<void> {
        await expect(this.dialog).toBeVisible({ timeout: 10000 });
        await expect(this.dialog).toContainText(expectedPrompt);
    }

    async submitInput(value: string): Promise<void> {
        await this.dialog.locator('input').fill(value);
        await this.dialog.getByRole('button', { name: 'Submit' }).click();
    }

    async expectDismissed(): Promise<void> {
        await expect(this.dialog).not.toBeVisible({ timeout: 10000 });
    }
}
