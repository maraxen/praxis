import { Page, Locator, expect } from '@playwright/test';

export class InventoryDialogPage {
    private readonly page: Page;
    private readonly dialog: Locator;

    // Tab Locators
    readonly catalogTab: Locator;
    readonly quickAddTab: Locator;
    readonly browseAddTab: Locator;
    readonly currentItemsTab: Locator;

    constructor(page: Page) {
        this.page = page;
        this.dialog = page.locator('app-inventory-dialog');

        this.catalogTab = page.getByRole('tab', { name: 'Catalog' });
        this.quickAddTab = page.getByRole('tab', { name: 'Quick Add' });
        this.browseAddTab = page.getByRole('tab', { name: 'Browse & Add' });
        this.currentItemsTab = page.getByRole('tab', { name: 'Current Items' });
    }

    /**
     * Waits for the inventory dialog to become visible.
     */
    async waitForDialogVisible(): Promise<void> {
        await expect(this.dialog).toBeVisible({ timeout: 15000 });
    }

    /**
     * Closes the inventory dialog if it's open.
     */
    async close(): Promise<void> {
        const closeBtn = this.page.locator('app-inventory-dialog button').filter({ hasText: /close|cancel/i }).first();
        if (await this.dialog.isVisible({ timeout: 1000 }).catch(() => false)) {
            if (await closeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
                await closeBtn.click();
            } else {
                await this.page.keyboard.press('Escape');
            }
            await expect(this.dialog).not.toBeVisible({ timeout: 5000 });
        }
    }

    async open() {
        await this.page.getByLabel('Open Inventory Dialog').click();
        await this.dialog.waitFor({ state: 'visible' });
    }

    async selectTab(tabName: 'Catalog' | 'Quick Add' | 'Browse & Add' | 'Current Items') {
        const tab = this.page.getByRole('tab', { name: tabName });
        await tab.click();
        await expect(tab).toHaveAttribute('aria-selected', 'true');
    }

    async getCatalogItems(): Promise<Locator> {
        await this.catalogTab.click();
        const items = this.page.locator('[data-testid="catalog-item"]');
        await items.first().waitFor({ state: 'visible', timeout: 15000 });
        return items;
    }

    async addSimulatedMachine(index: number = 0) {
        const addButtons = this.page.getByRole('button', { name: 'Add Simulated' });
        await addButtons.nth(index).click();
    }

    async getMachinesInInventory(): Promise<string[]> {
        await this.selectTab('Current Items');
        const machines = this.page.locator('[data-testid="inventory-machine-name"]');
        const count = await machines.count();
        const names: string[] = [];
        for (let i = 0; i < count; i++) {
            names.push(await machines.nth(i).innerText());
        }
        return names;
    }

    async assertMachineInInventory(namePattern: string | RegExp) {
        await this.selectTab('Current Items');
        const matcher = typeof namePattern === 'string'
            ? new RegExp(namePattern, 'i')
            : namePattern;
        await expect(this.page.getByText(matcher).first()).toBeVisible({ timeout: 10000 });
    }
}
