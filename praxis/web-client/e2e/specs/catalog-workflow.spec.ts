import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { InventoryDialogPage } from '../page-objects/inventory-dialog.page';

test.describe('Catalog to Inventory Workflow', () => {
    test.setTimeout(120000);

    test('should add simulated machine from wizard', async ({ page }, testInfo) => {
        // Navigate with worker DB — splash/onboarding bypass handled by addInitScript
        await gotoWithWorkerDb(page, '/app/playground', testInfo);

        // Open the Asset Wizard via the "Add Machine" button in the playground header
        const addMachineBtn = page.getByRole('button', { name: /Add Machine/i });
        await expect(addMachineBtn).toBeVisible({ timeout: 15000 });
        await addMachineBtn.click();

        // Wait for wizard dialog
        const wizard = page.locator('app-asset-wizard');
        await expect(wizard).toBeVisible({ timeout: 10000 });
        const dialog = page.getByRole('dialog');

        // Step 1: Select Category (wizard opens pre-selected as MACHINE in playground context)
        const categoryCard = wizard.getByTestId(/category-card-/).first();
        await expect(categoryCard).toBeVisible({ timeout: 15000 });
        await categoryCard.click();
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Step 2: Select Machine Type (Frontend)
        const frontendCard = wizard.getByTestId(/frontend-card-/).first();
        await expect(frontendCard).toBeVisible({ timeout: 10000 });
        await frontendCard.click();
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Step 3: Select Driver (Backend) — pick first (simulated)
        const backendCard = wizard.getByTestId(/backend-card-/).first();
        await expect(backendCard).toBeVisible({ timeout: 10000 });
        await backendCard.click();
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Step 3B (conditional): Select Deck — if deck step appears, pick first
        const deckStep = wizard.getByTestId('wizard-step-deck');
        const deckStepVisible = await deckStep.isVisible().catch(() => false);
        if (deckStepVisible) {
            const deckCard = wizard.getByTestId(/deck-card-/).first();
            await expect(deckCard).toBeVisible({ timeout: 10000 });
            await deckCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();
        }

        // Step 4: Config — fill name
        const nameInput = wizard.getByTestId('input-instance-name');
        await expect(nameInput).toBeVisible({ timeout: 10000 });
        const machineName = `TestMachine-${Date.now()}`;
        await nameInput.fill(machineName);
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Step 5: Review/Create
        const createBtn = wizard.getByTestId('wizard-create-btn');
        await expect(createBtn).toBeVisible({ timeout: 10000 });
        await createBtn.click();
        await expect(wizard).not.toBeVisible({ timeout: 15000 });

        // Verify machine was persisted in SQLite
        const machineCount = await page.evaluate(async () => {
            const e2e = (window as any).__e2e;
            if (!e2e) return 0;
            return await e2e.count('machines');
        });
        expect(machineCount).toBeGreaterThan(0);
    });

    test('simulated machine persists after reload', async ({ page }, testInfo) => {
        // Add machine via wizard
        await gotoWithWorkerDb(page, '/app/playground', testInfo);

        const addMachineBtn = page.getByRole('button', { name: /Add Machine/i });
        await expect(addMachineBtn).toBeVisible({ timeout: 15000 });
        await addMachineBtn.click();

        const wizard = page.locator('app-asset-wizard');
        await expect(wizard).toBeVisible({ timeout: 10000 });
        const dialog = page.getByRole('dialog');
        const inventory = new InventoryDialogPage(page);

        // Walk through wizard quickly
        const categoryCard = wizard.getByTestId(/category-card-/).first();
        await expect(categoryCard).toBeVisible({ timeout: 10000 });
        await categoryCard.click();
        await dialog.getByRole('button', { name: /Next/i }).click();

        const frontendCard = wizard.getByTestId(/frontend-card-/).first();
        await expect(frontendCard).toBeVisible({ timeout: 10000 });
        await frontendCard.click();
        await dialog.getByRole('button', { name: /Next/i }).click();

        const backendCard = wizard.getByTestId(/backend-card-/).first();
        await expect(backendCard).toBeVisible({ timeout: 10000 });
        await backendCard.click();
        await dialog.getByRole('button', { name: /Next/i }).click();

        // Deck step (conditional)
        const deckStep = wizard.getByTestId('wizard-step-deck');
        if (await deckStep.isVisible().catch(() => false)) {
            await wizard.getByTestId(/deck-card-/).first().click();
            await dialog.getByRole('button', { name: /Next/i }).click();
        }

        const nameInput = wizard.getByTestId('input-instance-name');
        await expect(nameInput).toBeVisible({ timeout: 10000 });
        await nameInput.fill('PersistenceTest Machine');
        await dialog.getByRole('button', { name: /Next/i }).click();

        const createBtn = wizard.getByTestId('wizard-create-btn');
        await expect(createBtn).toBeVisible({ timeout: 10000 });
        await createBtn.click();
        await expect(wizard).not.toBeVisible({ timeout: 15000 });

        // Reload page WITHOUT resetting the DB
        await gotoWithWorkerDb(page, '/app/playground', testInfo, { resetdb: false });

        // Verify persistence: check SQLite directly
        const machineCount = await page.evaluate(async () => {
            const e2e = (window as any).__e2e;
            if (!e2e) return 0;
            return await e2e.count('machines');
        });
        expect(machineCount).toBeGreaterThan(0);
    });

    test('handles wizard open without errors', async ({ page }, testInfo) => {
        // Verify the wizard opens cleanly and shows expected UI elements
        await gotoWithWorkerDb(page, '/app/playground', testInfo);

        const addMachineBtn = page.getByRole('button', { name: /Add Machine/i });
        await expect(addMachineBtn).toBeVisible({ timeout: 15000 });
        await addMachineBtn.click();

        const wizard = page.locator('app-asset-wizard');
        await expect(wizard).toBeVisible({ timeout: 10000 });

        // Verify wizard structure
        await expect(wizard.getByTestId(/category-card-/).first()).toBeVisible({ timeout: 10000 });

        // Close wizard
        await page.keyboard.press('Escape');
        await expect(wizard).not.toBeVisible({ timeout: 5000 });
    });
});
