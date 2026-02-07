import { Page, Locator, expect, TestInfo } from '@playwright/test';
import { BasePage } from './base.page';

export class AssetsPage extends BasePage {
    readonly addMachineButton: Locator;
    readonly addResourceButton: Locator;
    readonly machinesTab: Locator;
    readonly resourcesTab: Locator;
    readonly registryTab: Locator;
    readonly overviewTab: Locator;
    readonly spatialViewTab: Locator;

    constructor(page: Page, testInfo?: TestInfo, url: string = '/assets') {
        super(page, url, testInfo);
        this.addMachineButton = page.getByRole('button', { name: /Add Machine/i });
        this.addResourceButton = page.getByRole('button', { name: /Add Resource/i });
        this.machinesTab = page.getByRole('tab', { name: /Machines/i });
        this.resourcesTab = page.getByRole('tab', { name: /Resources/i });
        this.registryTab = page.getByRole('tab', { name: /Registry/i });
        this.overviewTab = page.getByRole('tab', { name: /Overview/i });
        this.spatialViewTab = page.getByRole('tab', { name: /Spatial View/i });
    }

    /**
     * Waits for the dialog container and animation to complete before interaction.
     * Material CDK dialogs use ~200ms enter animation.
     */
    async waitForDialogReady(): Promise<void> {
        // Wait for overlay backdrop (indicates dialog is opening)
        const backdrop = this.page.locator('.cdk-overlay-backdrop');
        await backdrop.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
            // Backdrop may not always be present for inline wizards
        });
        // Wait for animation to complete (CDK uses ~200ms)
        await this.page.waitForTimeout(250);
        // Wait for dialog container to stabilize
        const dialogContainer = this.page.locator('.cdk-overlay-pane:has(app-asset-wizard)');
        await dialogContainer.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
            // May not be in a dialog overlay
        });
    }

    /**
     * Waits for the asset wizard to appear and be ready for interaction.
     * The wizard may start at Type step or Category step (when preselectedType is passed).
     */
    async waitForWizard() {
        // First ensure dialog animation is complete
        await this.waitForDialogReady();
        const wizard = this.page.locator('app-asset-wizard');
        await expect(wizard).toBeVisible({ timeout: 15000 });
        // Wait for the stepper to be visible (mat-stepper is always visible, individual mat-step elements are not)
        const stepper = wizard.locator('mat-stepper');
        await expect(stepper).toBeVisible({ timeout: 10000 });
        return wizard;
    }

    /**
     * Selects the asset type (MACHINE or RESOURCE) in Step 1 and advances to Step 2 (Category).
     */
    async selectAssetType(wizard: Locator, type: 'MACHINE' | 'RESOURCE'): Promise<void> {
        const typeCard = wizard.getByTestId(`type-card-${type.toLowerCase()}`);
        await expect(typeCard).toBeVisible({ timeout: 10000 });
        await typeCard.click();
        await expect(typeCard).toHaveClass(/selected/);
        await this.clickNextButton(wizard);
        // Wait for Category step to be visible
        await expect(wizard.getByTestId('wizard-step-category')).toBeVisible({ timeout: 10000 });
    }

    /**
     * Opens the Add Machine dialog and returns the dialog locator.
     * Use this when you need direct control over wizard navigation in tests.
     */
    async openMachineDialog(): Promise<Locator> {
        await this.addMachineButton.click();
        const wizard = await this.waitForWizard();
        return this.page.getByRole('dialog');
    }

    /**
     * Navigates through Category step to reach the Frontend selection step.
     * Note: When using Add Machine button, wizard opens at Category step (Type is preselected).
     * @param dialog The dialog locator
     * @param category The category to select (e.g., 'LiquidHandler', 'PlateReader')
     */
    async navigateToFrontendStep(dialog: Locator, category: string = 'LiquidHandler'): Promise<void> {
        const wizard = dialog.locator('app-asset-wizard');

        // Wizard opens at Category step (Type is preselected)
        // Select category card
        const categoryCard = wizard.getByTestId(`category-card-${category}`);
        await expect(categoryCard).toBeVisible({ timeout: 15000 });
        await categoryCard.click();

        // Click Next to go to Frontend step
        await this.clickNextButton(wizard);

        // Wait for frontend cards to appear
        await expect(dialog.getByTestId(/frontend-card-/).first()).toBeVisible({ timeout: 15000 });
    }

    /**
     * Selects a frontend (machine type) by name pattern.
     */
    async selectFrontend(dialog: Locator, namePattern: string): Promise<void> {
        const frontendCard = dialog.getByRole('button', { name: new RegExp(namePattern, 'i') }).or(
            dialog.getByTestId(/frontend-card-/).filter({ hasText: new RegExp(namePattern, 'i') })
        ).first();
        await expect(frontendCard).toBeVisible({ timeout: 10000 });
        await frontendCard.click();
    }

    /**
     * Selects a backend (driver) by name pattern.
     */
    async selectBackend(dialog: Locator, namePattern: string): Promise<void> {
        const backendCard = dialog.getByTestId(/backend-card-/).filter({ hasText: new RegExp(namePattern, 'i') }).first();
        await expect(backendCard).toBeVisible({ timeout: 10000 });
        await backendCard.click();
    }

    /**
     * Clicks the Next button in the dialog.
     */
    async clickNext(dialog: Locator): Promise<void> {
        const nextBtn = dialog.getByRole('button', { name: /Next/i });
        await expect(nextBtn).toBeEnabled({ timeout: 5000 });
        await nextBtn.click();
    }

    /**
     * Gets the 'Next' button in the current wizard step.
     */
    getNextButton(wizard: Locator): Locator {
        return wizard.locator('.mat-step-content:visible, [role="tabpanel"]:visible').first().getByTestId('wizard-next-button');
    }

    /**
     * Clicks the 'Next' button in the current wizard step, ensuring it's enabled first.
     */
    async clickNextButton(wizard: Locator): Promise<void> {
        const nextButton = this.getNextButton(wizard);
        await expect(nextButton).toBeEnabled({ timeout: 10000 });
        await nextButton.click();
        await this.waitForOverlaysToDismiss();
    }

    /**
     * Selects a card in the wizard and waits for the next step to be ready.
     */
    async selectWizardCard(wizard: Locator, testId: string): Promise<void> {
        const card = wizard.getByTestId(testId);
        await expect(card).toBeVisible({ timeout: 15000 });

        // Ensure card is stable before click
        await card.waitFor({ state: 'attached' });
        await this.page.waitForTimeout(500); // Wait for transitions

        await card.click({ force: true });

        // Wait for selected state with retry
        await expect(async () => {
            const hasClass = await card.evaluate(el => el.classList.contains('selected') || el.classList.contains('active'));
            if (!hasClass) {
                await card.click({ force: true }).catch(() => { });
                throw new Error('Card not selected');
            }
        }).toPass({ timeout: 5000 });
    }

    /**
     * Waits for any overlays (dialogs, spinners) to dismiss before continuing.
     */
    async waitForOverlaysToDismiss(): Promise<void> {
        // Wait for any loading spinners to disappear
        const spinner = this.page.locator('mat-spinner, .loading-overlay, .cdk-overlay-backdrop');
        await expect(spinner).not.toBeVisible({ timeout: 10000 }).catch(() => {
            // Spinner might not exist - that's fine
        });
    }

    /**
     * Waits for wizard step transition by checking step header text.
     */
    async waitForStepTransition(wizard: Locator, stepPattern: RegExp): Promise<void> {
        const stepHeader = wizard.locator('.mat-step-label-selected, .mat-step-content:visible h2, .mat-step-content:visible h3').first();
        await expect(stepHeader).toContainText(stepPattern, { timeout: 10000 });
    }


    async navigateToOverview() {
        await this.overviewTab.click();
        await expect(this.overviewTab).toHaveAttribute('aria-selected', 'true', { timeout: 5000 });
    }

    async navigateToSpatialView() {
        await this.spatialViewTab.click();
        await expect(this.spatialViewTab).toHaveAttribute('aria-selected', 'true', { timeout: 5000 });
    }

    async navigateToMachines() {
        await this.machinesTab.click();
        await expect(this.machinesTab).toHaveAttribute('aria-selected', 'true', { timeout: 5000 });
    }

    async navigateToResources() {
        await this.resourcesTab.click();
        await expect(this.resourcesTab).toHaveAttribute('aria-selected', 'true', { timeout: 5000 });
    }

    async navigateToRegistry() {
        await this.registryTab.click();
        await expect(this.registryTab).toHaveAttribute('aria-selected', 'true', { timeout: 5000 });
        await this.waitForLoadingComplete();
    }

    /**
     * Waits for all Material loading indicators to disappear
     */
    async waitForLoadingComplete() {
        await this.page.waitForSelector('mat-spinner', { state: 'detached', timeout: 10000 }).catch(() => { });
        await this.page.waitForTimeout(500); // Wait for potential animations
    }

    async selectRegistryTab(tabName: 'Resources' | 'Resource Types' | 'Machines') {
        const tab = this.page.getByRole('tab', { name: tabName });
        await tab.click();
        await expect(tab).toHaveAttribute('aria-selected', 'true', { timeout: 5000 });
        await this.waitForLoadingComplete();
    }

    async search(query: string) {
        // Try to find search input that is visible
        const searchInput = this.page.locator('input[placeholder*="Search"]:visible').first();
        await searchInput.fill(query);
        await this.page.waitForTimeout(1000); // Increased debounce for stability
    }

    /** @deprecated Use navigateToOverview instead */
    async navigateToDashboard() {
        await this.navigateToOverview();
    }

    async createMachine(name: string, categoryName: string = 'LiquidHandler', modelQuery: string = 'STAR') {
        await this.navigateToOverview();
        await this.addMachineButton.click();
        const wizard = await this.waitForWizard();
        const dialog = this.page.getByRole('dialog');

        // Skip Type step - Add Machine button passes preselectedType: 'MACHINE' which auto-skips to Category
        // Step 1 (visible): Select Category
        const anyCategoryCard = wizard.getByTestId(/category-card-/).first();
        await expect(anyCategoryCard).toBeVisible({ timeout: 15000 });
        await anyCategoryCard.waitFor({ state: 'attached' });

        const categoryCard = wizard.getByTestId(`category-card-${categoryName}`);
        await expect(categoryCard).toBeVisible({ timeout: 5000 });
        await categoryCard.click({ timeout: 5000 });
        await this.waitForOverlaysToDismiss();
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Step 2: Select Machine Type (Frontend)
        const frontendCard = wizard.getByTestId(/frontend-card-/).first();
        await expect(frontendCard).toBeVisible({ timeout: 15000 });
        await frontendCard.click();
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Step 3: Select Driver (Backend)
        const backendCard = wizard.getByTestId(/backend-card-/).first();
        await expect(backendCard).toBeVisible({ timeout: 15000 });
        await backendCard.click();
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Step 4: Config
        const nameInput = wizard.getByTestId('input-instance-name');
        await expect(nameInput).toBeVisible({ timeout: 10000 });
        await nameInput.fill(name);
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Step 5: Review/Create
        const createBtn = wizard.getByTestId('wizard-create-btn');
        await expect(createBtn).toBeVisible({ timeout: 10000 });
        await createBtn.click();
        await expect(wizard).not.toBeVisible({ timeout: 15000 });
    }

    async createResource(name: string, categoryName: string = 'Plate', modelQuery: string = '96') {
        await this.navigateToOverview();
        await this.addResourceButton.click();
        const wizard = await this.waitForWizard();

        // Skip Type step - Add Resource button passes preselectedType: 'RESOURCE' which auto-skips to Category
        // Step 1 (visible): Select Category
        await this.selectWizardCard(wizard, `category-card-${categoryName}`);
        await this.clickNextButton(wizard);

        // Step 3: Select Definition
        const searchInput = wizard.getByRole('textbox', { name: /search/i });
        await searchInput.fill(modelQuery);
        const resultsGrid = wizard.getByTestId('results-grid');
        const definitionCard = resultsGrid.locator('[data-testid^="definition-card-"]').first();
        await expect(definitionCard).toBeVisible({ timeout: 15000 });
        await definitionCard.click();
        await this.clickNextButton(wizard);

        // Step 4: Config
        await wizard.getByTestId('input-instance-name').fill(name);
        await this.clickNextButton(wizard);

        // Step 5: Create
        await wizard.getByTestId('wizard-create-btn').click();
        await expect(wizard).not.toBeVisible({ timeout: 15000 });
    }

    /**
     * Delete a machine by name. Handles the browser confirm() dialog.
     * Must be called from the Machines tab.
     */
    async deleteMachine(name: string) {
        await this.navigateToMachines();
        // Set up dialog handler BEFORE triggering the delete
        this.page.once('dialog', dialog => dialog.accept());

        // Find the row with the machine name and click delete button
        const row = this.page.locator('tr').filter({ hasText: name });
        const deleteBtn = row.getByRole('button', { name: /delete/i }).or(
            row.locator('button[mattooltip*="Delete"]')
        );

        if (await deleteBtn.isVisible({ timeout: 2000 })) {
            await deleteBtn.click();
        } else {
            // Try context menu approach
            const moreBtn = row.getByRole('button').filter({ hasText: /more_vert/i });
            if (await moreBtn.isVisible({ timeout: 1000 })) {
                await moreBtn.click();
                await this.page.getByRole('menuitem', { name: /Delete/i }).click();
            }
        }

        // Wait for the row to disappear after deletion
        await expect(row).not.toBeVisible({ timeout: 5000 });
    }

    /**
     * Delete a resource by name. Handles the browser confirm() dialog.
     * Must be called from the Registry/Resources tab.
     */
    async deleteResource(name: string) {
        await this.navigateToResources();
        // Set up dialog handler BEFORE triggering the delete
        this.page.once('dialog', async dialog => {
            if (dialog.type() === 'beforeunload') return;
            await dialog.accept().catch(() => { });
        });

        // Find the row with the resource name and click delete button
        const row = this.page.locator('tr').filter({ hasText: name });
        const deleteBtn = row.getByRole('button', { name: /delete/i }).or(
            row.locator('button[mattooltip*="Delete"]')
        );

        if (await deleteBtn.isVisible({ timeout: 2000 })) {
            await deleteBtn.click();
        } else {
            // Try context menu approach
            const moreBtn = row.getByRole('button').filter({ hasText: /more_vert/i });
            if (await moreBtn.isVisible({ timeout: 1000 })) {
                await moreBtn.click();
                await this.page.getByRole('menuitem', { name: /Delete/i }).click();
            }
        }

        // Wait for the row to disappear after deletion
        await expect(row).not.toBeVisible({ timeout: 5000 });
    }

    /**
     * Legacy method - use deleteMachine or deleteResource instead
     * @deprecated
     */
    async deleteAsset(name: string) {
        await this.deleteMachine(name);
    }

    // Filter chip interaction
    /**
     * Select a category filter chip by its label text
     */
    async selectCategoryFilter(category: string) {
        const chip = this.page.locator('app-filter-chip').filter({ hasText: new RegExp(category, 'i') });
        await chip.click();
        // Wait for chip to show selected state
        await expect(chip).toHaveClass(/selected|active/, { timeout: 5000 }).catch(() => {
            // Some implementations may not use a class - just ensure click was processed
        });
    }

    /**
     * Clear all active filters by clicking the clear button
     */
    async clearFilters() {
        const clearBtn = this.page.getByRole('button', { name: /Clear/i }).or(
            this.page.locator('button').filter({ hasText: /clear/i })
        );
        if (await clearBtn.isVisible({ timeout: 1000 })) {
            await clearBtn.click();
            // Wait for clear button to disappear or filters to reset
            await expect(clearBtn).not.toBeVisible({ timeout: 5000 }).catch(() => {
                // Button may stay visible - that's OK
            });
        }
    }

    /**
     * Type in the search input to filter assets
     */
    async searchAssets(query: string) {
        const searchInput = this.page.getByPlaceholder(/search/i);
        await searchInput.fill(query);
        // Wait for search to take effect - table content should update
        await expect(searchInput).toHaveValue(query, { timeout: 2000 });
    }

    // Count helpers
    /**
     * Get the count of visible machines in the table
     */
    async getMachineCount(): Promise<number> {
        const rows = this.page.locator('table tr').filter({ has: this.page.locator('td') });
        return await rows.count();
    }

    /**
     * Get the count of visible resources in the table
     */
    async getResourceCount(): Promise<number> {
        const rows = this.page.locator('table tr').filter({ has: this.page.locator('td') });
        return await rows.count();
    }

    /**
     * Opens the Add Machine dialog and navigates through wizard steps
     * (Category → Frontend → Backend) to reach the Config step (name input).
     * Returns the wizard locator positioned at the config step.
     */
    async navigateToConfigStep(): Promise<Locator> {
        await this.addMachineButton.click();
        const wizard = await this.waitForWizard();
        const dialog = this.page.getByRole('dialog');

        // Step 1: Category (Type is preselected via "Add Machine")
        const categoryCard = wizard.getByTestId(/category-card-/).first();
        await expect(categoryCard).toBeVisible({ timeout: 15000 });
        await categoryCard.click();
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Step 2: Frontend
        const frontendCard = wizard.getByTestId(/frontend-card-/).first();
        await expect(frontendCard).toBeVisible({ timeout: 15000 });
        await frontendCard.click();
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Step 3: Backend
        const backendCard = wizard.getByTestId(/backend-card-/).first();
        await expect(backendCard).toBeVisible({ timeout: 15000 });
        await backendCard.click();
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Now at Step 4: Config — wait for name input
        await expect(wizard.getByTestId('input-instance-name')).toBeVisible({ timeout: 10000 });

        return wizard;
    }

    async verifyAssetVisible(name: string) {
        await expect(this.page.getByText(name).first()).toBeVisible({ timeout: 10000 });
    }

    async verifyAssetNotVisible(name: string, timeout: number = 5000) {
        await expect(this.page.getByText(name)).not.toBeVisible({ timeout });
    }
}
