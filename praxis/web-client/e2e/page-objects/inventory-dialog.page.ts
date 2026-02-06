import { Page, Locator, expect } from '@playwright/test';

export class InventoryDialogPage {
    private readonly page: Page;
    private readonly dialog: Locator;
    private readonly wizard: Locator;

    constructor(page: Page) {
        this.page = page;
        this.dialog = page.getByRole('dialog');
        this.wizard = page.locator('app-asset-wizard');
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
        if (await this.dialog.isVisible({ timeout: 1000 }).catch(() => false)) {
            await this.page.keyboard.press('Escape');
            await expect(this.dialog).not.toBeVisible({ timeout: 5000 });
        }
    }

    /**
     * Clicks the Next button in the current wizard step.
     */
    async clickNext(): Promise<void> {
        // Try multiple ways to find the visible next button
        const nextButton = this.page.locator('button').filter({ hasText: /^Next$/ }).filter({ visible: true }).first();
        const nextButtonById = this.wizard.getByTestId('wizard-next-button').filter({ visible: true }).first();
        
        // Prefer the one that is visible
        if (await nextButtonById.isVisible()) {
            await expect(nextButtonById).toBeEnabled({ timeout: 10000 });
            await nextButtonById.click();
        } else {
            await expect(nextButton).toBeVisible({ timeout: 10000 });
            await expect(nextButton).toBeEnabled({ timeout: 10000 });
            await nextButton.click();
        }
    }

    /**
     * Selects an asset type (MACHINE or RESOURCE).
     */
    async selectAssetType(type: 'MACHINE' | 'RESOURCE'): Promise<void> {
        const typeCard = this.wizard.getByTestId(`type-card-${type.toLowerCase()}`);
        await expect(typeCard).toBeVisible({ timeout: 10000 });
        await typeCard.click();
        // Wait for selection to be reflected (class 'selected' is added)
        await expect(typeCard).toHaveClass(/selected/, { timeout: 5000 });
        await this.clickNext();
    }

    /**
     * Selects a category by its test ID.
     */
    async selectCategory(category: string): Promise<void> {
        const categoryCard = this.wizard.getByTestId(`category-card-${category}`);
        await expect(categoryCard).toBeVisible({ timeout: 10000 });
        await categoryCard.click();
        await expect(categoryCard).toHaveClass(/selected/, { timeout: 5000 });
        await this.clickNext();
    }

    /**
     * Selects a machine type (frontend) by name.
     */
    async selectMachineType(namePattern: string | RegExp): Promise<void> {
        // In Step 3, machine types are cards with frontend-card- testids
        const frontendCard = this.wizard.getByTestId(/frontend-card-/).filter({ hasText: namePattern }).first();
        if (!(await frontendCard.isVisible({ timeout: 5000 }))) {
            // Fallback to any frontend card if pattern doesn't match
            const anyCard = this.wizard.getByTestId(/frontend-card-/).first();
            await expect(anyCard).toBeVisible({ timeout: 10000 });
            await anyCard.click();
        } else {
            await frontendCard.click();
        }
        await this.clickNext();
    }

    /**
     * Selects a driver (backend) by name.
     */
    async selectDriver(namePattern: string | RegExp): Promise<void> {
        const backendCard = this.wizard.getByTestId(/backend-card-/).filter({ hasText: namePattern }).first();
        if (!(await backendCard.isVisible({ timeout: 5000 }))) {
            const anyCard = this.wizard.getByTestId(/backend-card-/).first();
            await expect(anyCard).toBeVisible({ timeout: 10000 });
            await anyCard.click();
        } else {
            await backendCard.click();
        }
        await this.clickNext();
    }

    /**
     * Fills the instance name in the config step.
     */
    async fillInstanceName(name: string): Promise<void> {
        const nameInput = this.wizard.getByTestId('input-instance-name');
        await expect(nameInput).toBeVisible({ timeout: 10000 });
        await nameInput.fill(name);
        await this.clickNext();
    }

    /**
     * Clicks the final Create Asset button.
     */
    async createAsset(): Promise<void> {
        const createBtn = this.wizard.getByTestId('wizard-create-btn');
        await expect(createBtn).toBeEnabled({ timeout: 10000 });
        await createBtn.click();
        await expect(this.dialog).not.toBeVisible({ timeout: 15000 });
    }

    /**
     * Legacy method for selecting a tab. 
     * Since the new wizard uses a stepper, this now just waits for the wizard to be ready
     * or performs a no-op to avoid breaking older tests immediately.
     * @deprecated Use specific wizard step methods instead.
     */
    async selectTab(tabName: string) {
        console.warn(`[InventoryDialogPage] selectTab('${tabName}') is deprecated. The wizard now uses a stepper.`);
        await this.waitForDialogVisible();
    }
}
