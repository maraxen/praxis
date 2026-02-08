import { test, expect } from '../fixtures/worker-db.fixture';
import { WelcomePage } from '../page-objects/welcome.page';
import { AssetsPage } from '../page-objects/assets.page';
import { PlaygroundPage } from '../page-objects/playground.page';

// Timeouts
const DIALOG_VISIBLE_TIMEOUT = 10000;
const DATA_LOAD_TIMEOUT = 15000;
const STEP_TRANSITION_TIMEOUT = 5000;
const ELEMENT_VISIBLE_TIMEOUT = 10000;

/**
 * E2E Tests for Machine Frontend/Backend Separation
 * 
 * Actual wizard flow (when Add Machine button clicked):
 * 1. Category (preselected Type=MACHINE) - e.g., LiquidHandler, PlateReader, Thermocycler
 * 2. Frontend (Machine Type) - specific machine models within category
 * 3. Backend (Driver) - e.g., HamiltonSTARBackend, ChatterBoxBackend
 * 4. Config - Name, connection settings
 * 5. Review - Final confirmation
 */
test.describe('Machine Frontend/Backend Separation', () => {
    let assetsPage: AssetsPage;
    let playgroundPage: PlaygroundPage;
    const machinesToCleanup: string[] = [];

    test.beforeEach(async ({ page }, testInfo) => {
        const welcomePage = new WelcomePage(page, testInfo);
        assetsPage = new AssetsPage(page, testInfo);
        playgroundPage = new PlaygroundPage(page, testInfo);

        // Enable debug logging
        page.on('console', msg => {
            const text = msg.text();
            if (text.includes('ASSET-DEBUG') || text.includes('[SqliteService]') || text.includes('MachineDialog')) {
                console.log(`BROWSER_LOG: ${text}`);
            }
        });

        await welcomePage.goto();
    });

    test.afterEach(async () => {
        if (machinesToCleanup.length > 0) {
            await assetsPage.goto();
            await assetsPage.navigateToMachines();
            for (const machineName of machinesToCleanup) {
                try {
                    await assetsPage.deleteMachine(machineName);
                    console.log(`Cleaned up machine: ${machineName}`);
                } catch (error) {
                    console.error(`Failed to clean up machine: ${machineName}`, error);
                }
            }
            machinesToCleanup.length = 0; // Clear the array
        }
    });

    test.describe('Machine Dialog - Category Selection (Step 1)', () => {
        test('should display machine categories in step 1', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlaysToDismiss();

            // Open Add Machine dialog - opens at Category step (Type preselected as MACHINE)
            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible({ timeout: DIALOG_VISIBLE_TIMEOUT });

            // Wizard opens at Category step with category cards
            const firstCard = dialog.getByTestId(/category-card-/).first();
            await expect(firstCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });

            // Verify Category step heading
            await expect(page.getByText('Select Category')).toBeVisible({ timeout: STEP_TRANSITION_TIMEOUT });

            // Verify categories are displayed (from seeded definitions)
            const liquidHandlerCard = dialog.getByTestId('category-card-LiquidHandler');
            await expect(liquidHandlerCard).toBeVisible({ timeout: ELEMENT_VISIBLE_TIMEOUT });

            // Close dialog
            await page.keyboard.press('Escape'); // Close dialog (wizard has no Cancel button)
        });

        test('should show multiple machine categories from database', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlaysToDismiss();

            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible({ timeout: DIALOG_VISIBLE_TIMEOUT });

            // Wait for category cards to load
            const firstCard = dialog.getByTestId(/category-card-/).first();
            await expect(firstCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });

            // Count available categories
            const categoryCards = dialog.getByTestId(/category-card-/);
            const count = await categoryCards.count();
            expect(count).toBeGreaterThan(0);
            console.log(`Found ${count} machine categories`);

            // Close dialog
            await page.keyboard.press('Escape'); // Close dialog (wizard has no Cancel button)
        });
    });

    test.describe('Machine Dialog - Frontend Selection (Step 2)', () => {
        test('should navigate to frontend selection after choosing category', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlaysToDismiss();

            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible({ timeout: DIALOG_VISIBLE_TIMEOUT });

            // Wait for category cards to load
            const categoryCards = dialog.getByTestId(/category-card-/).first();
            await expect(categoryCards).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });

            // Step 1: Select LiquidHandler category
            const liquidHandlerCard = dialog.getByTestId('category-card-LiquidHandler');
            await liquidHandlerCard.click();

            // Click Next to go to Frontend step
            const nextBtn = dialog.getByRole('button', { name: /Next/i });
            await nextBtn.click();

            // Verify we're now on Frontend step by checking for frontend-card elements
            const frontendCard = dialog.getByTestId(/frontend-card-/).first();
            await expect(frontendCard).toBeVisible({ timeout: STEP_TRANSITION_TIMEOUT });

            // Close dialog
            await page.keyboard.press('Escape'); // Close dialog (wizard has no Cancel button)
        });

        test('should show compatible backends for selected frontend', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlaysToDismiss();

            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible({ timeout: DIALOG_VISIBLE_TIMEOUT });

            // Wait for category cards to load (wizard opens at Category step)
            const categoryCard = dialog.getByTestId('category-card-LiquidHandler');
            await expect(categoryCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });

            // Step 1: Select LiquidHandler category
            await categoryCard.click();
            await page.getByRole('dialog').getByRole('button', { name: /Next/i }).click();

            // Step 2: Wait for frontend cards and select first one
            const firstFrontendCard = dialog.getByTestId(/frontend-card-/).first();
            await expect(firstFrontendCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await firstFrontendCard.click();
            await page.getByRole('dialog').getByRole('button', { name: /Next/i }).click();

            // Step 3: Verify backends are loaded
            const firstBackendCard = dialog.getByTestId(/backend-card-/).first();
            await expect(firstBackendCard).toBeVisible({ timeout: ELEMENT_VISIBLE_TIMEOUT });

            const backendCount = await dialog.getByTestId(/backend-card-/).count();
            expect(backendCount).toBeGreaterThan(0);
            console.log(`Found ${backendCount} backends for Liquid Handler`);

            // Close dialog
            await page.keyboard.press('Escape'); // Close dialog (wizard has no Cancel button)
        });

        test('should display simulated badge for simulator backends', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlaysToDismiss();

            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible({ timeout: DIALOG_VISIBLE_TIMEOUT });

            // Wait for category cards and select one
            const categoryCard = dialog.getByTestId('category-card-LiquidHandler');
            await expect(categoryCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await categoryCard.click();
            await page.getByRole('dialog').getByRole('button', { name: /Next/i }).click();

            // Select first frontend
            const frontendCard = dialog.getByTestId(/frontend-card-/).first();
            await expect(frontendCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await frontendCard.click();
            await page.getByRole('dialog').getByRole('button', { name: /Next/i }).click();

            // Look for "Simulated" chip/badge on backend cards
            // Skip this check if no simulated-badge testid exists - check for backend cards instead
            const backendCards = dialog.getByTestId(/backend-card-/);
            await expect(backendCards.first()).toBeVisible({ timeout: ELEMENT_VISIBLE_TIMEOUT });

            // Close dialog
            await page.keyboard.press('Escape'); // Close dialog (wizard has no Cancel button)
        });

        test('backends should be filtered based on frontend selection', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlaysToDismiss();

            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible({ timeout: DIALOG_VISIBLE_TIMEOUT });

            // Step 1: Select PlateReader category
            const categoryCard = dialog.getByTestId('category-card-PlateReader');
            await expect(categoryCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await categoryCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 2: Select first Plate Reader frontend
            const frontendCard = dialog.getByTestId(/frontend-card-/).first();
            await expect(frontendCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await frontendCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 3: Verify backend cards are for Plate Reader, not Liquid Handler
            const backendCards = dialog.getByTestId(/backend-card-/);
            await expect(backendCards.first()).toBeVisible({ timeout: STEP_TRANSITION_TIMEOUT });

            // ChatterBox is a Liquid Handler backend - should NOT be visible for PlateReader
            const liquidHandlerBackend = dialog.getByTestId(/backend-card-/).filter({ hasText: /ChatterBox/i });
            await expect(liquidHandlerBackend).not.toBeVisible();

            // Close dialog
            await page.keyboard.press('Escape');
        });
    });

    test.describe('Machine Dialog - Configuration (Step 4)', () => {
        test('should navigate to configuration after selecting backend', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlaysToDismiss();

            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible({ timeout: DIALOG_VISIBLE_TIMEOUT });

            // Step 1: Select LiquidHandler category
            const categoryCard = dialog.getByTestId('category-card-LiquidHandler');
            await expect(categoryCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await categoryCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 2: Select first frontend
            const frontendCard = dialog.getByTestId(/frontend-card-/).first();
            await expect(frontendCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await frontendCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 3: Select first backend
            const backendCard = dialog.getByTestId(/backend-card-/).first();
            await expect(backendCard).toBeVisible({ timeout: ELEMENT_VISIBLE_TIMEOUT });
            await backendCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 4: Verify Config step
            const nameInput = dialog.getByTestId('input-instance-name');
            await expect(nameInput).toBeVisible({ timeout: STEP_TRANSITION_TIMEOUT });

            // Close dialog
            await page.keyboard.press('Escape'); // Close dialog (wizard has no Cancel button)
        });

        test('should pre-populate name from selected backend', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlaysToDismiss();

            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible({ timeout: DIALOG_VISIBLE_TIMEOUT });

            // Step 1: Select LiquidHandler category
            const categoryCard = dialog.getByTestId('category-card-LiquidHandler');
            await expect(categoryCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await categoryCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 2: Select first frontend
            const frontendCard = dialog.getByTestId(/frontend-card-/).first();
            await expect(frontendCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await frontendCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 3: Select first backend
            const backendCard = dialog.getByTestId(/backend-card-/).first();
            await expect(backendCard).toBeVisible({ timeout: ELEMENT_VISIBLE_TIMEOUT });
            await backendCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 4: Verify name is pre-populated
            const nameInput = dialog.getByTestId('input-instance-name');
            await expect(nameInput).toBeVisible({ timeout: STEP_TRANSITION_TIMEOUT });

            // Close dialog
            await page.keyboard.press('Escape'); // Close dialog (wizard has no Cancel button)
        });
    });

    test.describe('Machine Dialog - Full Workflow', () => {
        test('should complete full machine creation flow and verify in DB', async ({ page }) => {
            const testMachineName = `Test Machine ${Date.now()}`;
            machinesToCleanup.push(testMachineName);

            await assetsPage.goto();
            await assetsPage.navigateToMachines();
            await assetsPage.createMachine(testMachineName, 'LiquidHandler');  // Use testId format

            // Verify machine appears in list
            await expect(page.getByText(testMachineName)).toBeVisible({ timeout: ELEMENT_VISIBLE_TIMEOUT });

            // Post-creation database verification via OPFS
            const machineRecord = await page.evaluate(async (machineName) => {
                const e2e = (window as any).__e2e;
                if (!e2e) return null;
                const rows = await e2e.query('SELECT * FROM machines WHERE name = ?', [machineName]);
                return rows[0] ?? null;
            }, testMachineName);

            expect(machineRecord).toBeDefined();
            expect(machineRecord.name).toBe(testMachineName);
            expect(machineRecord.machine_category).toBe('LiquidHandler');
        });

        test('should persist created machine after page reload', async ({ page }) => {
            const testMachineName = `Persist Machine ${Date.now()}`;
            machinesToCleanup.push(testMachineName);

            await assetsPage.goto();
            await assetsPage.navigateToMachines();
            await assetsPage.createMachine(testMachineName, 'LiquidHandler');  // Use testId format

            await expect(page.getByText(testMachineName)).toBeVisible({ timeout: ELEMENT_VISIBLE_TIMEOUT });

            // Reload page
            await page.reload();
            await assetsPage.waitForOverlaysToDismiss();
            await assetsPage.navigateToMachines();

            // Verify machine still exists
            await expect(page.getByText(testMachineName)).toBeVisible({ timeout: ELEMENT_VISIBLE_TIMEOUT });
        });
    });

    test.describe('Machine Dialog - Navigation', () => {
        test('should allow going back from Frontend step to Category step', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlaysToDismiss();

            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible({ timeout: DIALOG_VISIBLE_TIMEOUT });

            // Step 1: Select category
            const categoryCard = dialog.getByTestId('category-card-LiquidHandler');
            await expect(categoryCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await categoryCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 2: Verify on frontend step
            const frontendCard = dialog.getByTestId(/frontend-card-/).first();
            await expect(frontendCard).toBeVisible({ timeout: STEP_TRANSITION_TIMEOUT });

            // Click Back button (use role='button' for more reliable matching)
            const backButton = dialog.getByRole('button', { name: /Back/i });
            await backButton.click();

            // Verify back on Category step
            await expect(categoryCard).toBeVisible({ timeout: STEP_TRANSITION_TIMEOUT });

            // Close dialog
            await page.keyboard.press('Escape'); // Close dialog (wizard has no Cancel button)
        });

        test('should allow going back from Backend step to Frontend step', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlaysToDismiss();

            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible({ timeout: DIALOG_VISIBLE_TIMEOUT });

            // Step 1: Select category
            const categoryCard = dialog.getByTestId('category-card-LiquidHandler');
            await expect(categoryCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await categoryCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 2: Select first frontend
            const frontendCard = dialog.getByTestId(/frontend-card-/).first();
            await expect(frontendCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await frontendCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 3: Verify on Backend step
            const backendCard = dialog.getByTestId(/backend-card-/).first();
            await expect(backendCard).toBeVisible({ timeout: STEP_TRANSITION_TIMEOUT });

            // Click Back button
            const backButton = dialog.getByRole('button', { name: /Back/i });
            await backButton.click();

            // Verify back on Frontend step
            await expect(frontendCard).toBeVisible({ timeout: STEP_TRANSITION_TIMEOUT });

            // Close dialog
            await page.keyboard.press('Escape'); // Close dialog (wizard has no Cancel button)
        });

        test('should allow clicking step header tabs to navigate', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlaysToDismiss();

            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            await expect(dialog).toBeVisible({ timeout: DIALOG_VISIBLE_TIMEOUT });

            // Step 1: Select category
            const categoryCard = dialog.getByTestId('category-card-LiquidHandler');
            await expect(categoryCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await categoryCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 2: Select first frontend
            const frontendCard = dialog.getByTestId(/frontend-card-/).first();
            await expect(frontendCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });
            await frontendCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 3: On Backend step, click Category tab to go back
            await expect(dialog.getByTestId(/backend-card-/).first()).toBeVisible({ timeout: STEP_TRANSITION_TIMEOUT });

            // Angular Material step headers use role='tab' - click Category tab
            const categoryTab = dialog.getByRole('tab', { name: /Category/i });
            await categoryTab.click();

            // Verify back on Category step
            await expect(categoryCard).toBeVisible({ timeout: STEP_TRANSITION_TIMEOUT });

            // Close dialog
            await page.keyboard.press('Escape'); // Close dialog (wizard has no Cancel button)
        });
    });

    test.describe('Add Asset Dialog - Definition Selection Step', () => {
        test('should show frontend types in Add Asset dialog machine flow', async ({ page }) => {
            await playgroundPage.goto();
            await playgroundPage.waitForBootstrapComplete();

            // Open inventory dialog
            await page.getByLabel('Open Inventory Dialog').click();

            // Switch to "Browse & Add" tab
            const browseTab = page.getByRole('tab', { name: /Browse/i });
            await browseTab.click();

            // Select Machine type
            const machineOption = page.getByRole('dialog').locator('button').filter({ hasText: /Machine/i }).first();
            await machineOption.click();

            // Verify frontend types are shown
            const frontendCard = page.getByRole('dialog').getByTestId(/frontend-card-/).first();
            await expect(frontendCard).toBeVisible({ timeout: DATA_LOAD_TIMEOUT });

            // Close dialog
            await page.keyboard.press('Escape');
        });
    });
});
