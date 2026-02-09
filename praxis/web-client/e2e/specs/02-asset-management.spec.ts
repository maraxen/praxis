import { test, expect } from '../fixtures/worker-db.fixture';
import { WelcomePage } from '../page-objects/welcome.page';
import { AssetsPage } from '../page-objects/assets.page';

/**
 * E2E Tests for Asset Management
 * 
 * These tests verify the Asset Management UI in Browser Mode.
 * Note: Full CRUD operations require seeded definition data in the browser-side SQLite.
 */
test.describe('Asset Management Flow', () => {
    let assetsPage: AssetsPage;

    test.beforeEach(async ({ page }, testInfo) => {
        const welcomePage = new WelcomePage(page, testInfo);
        assetsPage = new AssetsPage(page, testInfo);

        await welcomePage.goto();

        // Capture debug logs
        page.on('console', msg => {
            const text = msg.text();
            if (text.includes('ASSET-DEBUG') || text.includes('[SqliteService]')) {
                console.log(`BROWSER_LOG: ${text}`);
            }
        });
    });

    test('should navigate to Assets page and see tabs', async ({ page }) => {
        // Navigate to Assets
        await assetsPage.goto();
        await assetsPage.waitForOverlay();

        // Verify tabs are visible
        await expect(assetsPage.overviewTab).toBeVisible({ timeout: 10000 });
        await expect(assetsPage.machinesTab).toBeVisible();
        await expect(assetsPage.resourcesTab).toBeVisible();
        await expect(assetsPage.registryTab).toBeVisible();
    });

    test('should open Add Machine dialog', async ({ page }) => {
        // Navigate to Assets
        await assetsPage.goto();
        await assetsPage.waitForOverlay();

        // Click Add Machine button
        await expect(assetsPage.addMachineButton).toBeVisible({ timeout: 10000 });
        await assetsPage.addMachineButton.click();

        // Verify dialog opens with wizard (Category step visible first due to preselected type)
        const dialog = page.getByRole('dialog');
        await expect(dialog).toBeVisible({ timeout: 5000 });

        // Verify category cards are shown (wizard opens at Category step)
        const categoryCard = dialog.getByTestId(/category-card-/).first();
        await expect(categoryCard).toBeVisible({ timeout: 10000 });

        // Close dialog via Escape (wizard has no Cancel button)
        await page.keyboard.press('Escape');
        await expect(dialog).not.toBeVisible({ timeout: 5000 });
    });

    test('should open Add Resource dialog', async ({ page }) => {
        // Navigate to Assets
        await assetsPage.goto();
        await assetsPage.waitForOverlay();

        // Click Add Resource button
        await expect(assetsPage.addResourceButton).toBeVisible({ timeout: 10000 });
        await assetsPage.addResourceButton.click();

        // Verify dialog opens
        const dialog = page.getByRole('dialog');
        await expect(dialog).toBeVisible({ timeout: 5000 });

        // Close dialog via Escape
        await page.keyboard.press('Escape');
        await expect(dialog).not.toBeVisible({ timeout: 5000 });
    });

    test('should navigate between tabs', async ({ page }) => {
        // Navigate to Assets
        await assetsPage.goto();
        await assetsPage.waitForOverlay();

        // Navigate to Machines tab
        await assetsPage.navigateToMachines();
        await expect(assetsPage.machinesTab).toBeVisible();

        // Navigate to Resources tab
        await assetsPage.navigateToResources();
        await expect(assetsPage.resourcesTab).toBeVisible();

        // Navigate to Registry tab
        await assetsPage.navigateToRegistry();
        await expect(assetsPage.registryTab).toBeVisible();

        // Navigate back to Overview
        await assetsPage.navigateToOverview();
        await expect(assetsPage.overviewTab).toBeVisible();
    });

    // CRUD Operations tests - Database is seeded with PLR definitions on startup
    test.describe('CRUD Operations', () => {

        test('should add a new machine', async ({ page }) => {
            const machineName = `Test Machine ${Date.now()}`;
            await assetsPage.goto();
            await assetsPage.waitForOverlay();
            await assetsPage.navigateToMachines();
            await assetsPage.createMachine(machineName);
            await assetsPage.verifyAssetVisible(machineName);

            // Verify data integrity via __e2e test API (correct table: machines)
            const machineData = await page.evaluate(async (name) => {
                const e2e = (window as any).__e2e;
                if (!e2e) return null;
                // Readiness wait
                let retries = 0;
                while (!e2e.isReady() && retries < 10) {
                    await new Promise(r => setTimeout(r, 500));
                    retries++;
                }
                const rows = await e2e.query(`SELECT accession_id, machine_category, name FROM machines WHERE name = ?`, [name]);
                return rows[0] ?? null;
            }, machineName);

            expect(machineData).not.toBeNull();
            expect(machineData!.machine_category).toBe('LiquidHandler');
        });

        test('should add a new resource', async ({ page }) => {
            const resourceName = `Test Resource ${Date.now()}`;
            await assetsPage.goto();
            await assetsPage.waitForOverlay();
            await assetsPage.navigateToResources();

            // Count resources before creation
            const countBefore = await page.evaluate(async () => {
                return (window as any).__e2e.count('resources');
            });

            await assetsPage.createResource(resourceName);

            // Verify resource was created in database
            const countAfter = await page.evaluate(async () => {
                return (window as any).__e2e.count('resources');
            });
            expect(countAfter).toBe(countBefore + 1);

            // Verify the specific resource exists by name
            const resourceExists = await page.evaluate(async (name) => {
                const rows = await (window as any).__e2e.query(
                    'SELECT name FROM resources WHERE name = ?', [name]
                );
                return rows.length > 0;
            }, resourceName);
            expect(resourceExists).toBe(true);
        });

        test('should delete a machine', async ({ page }) => {
            const machineName = `Delete Machine ${Date.now()}`;
            await assetsPage.goto();
            await assetsPage.waitForOverlay();
            await assetsPage.navigateToMachines();
            await assetsPage.createMachine(machineName);
            await assetsPage.verifyAssetVisible(machineName);
            await assetsPage.deleteMachine(machineName);
            await assetsPage.verifyAssetNotVisible(machineName);
        });

        test('should persist machine after page reload', async ({ page }) => {
            const machineName = `Persist Machine ${Date.now()}`;
            await assetsPage.goto();
            await assetsPage.waitForOverlay();
            await assetsPage.navigateToMachines();
            await assetsPage.createMachine(machineName);
            await assetsPage.verifyAssetVisible(machineName);

            // Get the ID before reload
            const machineId = await page.evaluate(async (name) => {
                const e2e = (window as any).__e2e;
                if (!e2e) return null;
                // Readiness wait
                let retries = 0;
                while (!e2e.isReady() && retries < 10) {
                    await new Promise(r => setTimeout(r, 500));
                    retries++;
                }
                const rows = await e2e.query(`SELECT accession_id FROM machines WHERE name = ?`, [name]);
                return rows[0]?.accession_id ?? null;
            }, machineName);

            await page.reload();
            await assetsPage.waitForOverlay();

            // NEW: Verify same ID exists after reload (proves OPFS persistence)
            const persistedId = await page.evaluate(async (name) => {
                const e2e = (window as any).__e2e;
                if (!e2e) return null;
                // Readiness wait
                let retries = 0;
                while (!e2e.isReady() && retries < 10) {
                    await new Promise(r => setTimeout(r, 500));
                    retries++;
                }
                const rows = await e2e.query(`SELECT accession_id FROM machines WHERE name = ?`, [name]);
                return rows[0]?.accession_id ?? null;
            }, machineName);

            expect(persistedId).toBe(machineId);
            await assetsPage.navigateToMachines();
            await assetsPage.verifyAssetVisible(machineName);
        });
    });

    test.describe('Validation & Error Handling', () => {

        test('should prevent machine creation with empty name', async ({ page }) => {
            await assetsPage.goto();
            await assetsPage.waitForOverlay();
            await assetsPage.navigateToMachines();
            await assetsPage.addMachineButton.click();

            const dialog = page.getByRole('dialog');
            const wizard = dialog.locator('app-asset-wizard');
            await expect(wizard).toBeVisible({ timeout: 15000 });

            // Step 1: Category — select LiquidHandler (known good combo)
            const categoryCard = wizard.getByTestId('category-card-LiquidHandler');
            await expect(categoryCard).toBeVisible({ timeout: 10000 });
            await categoryCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 2: Frontend (Machine Type)
            const frontendCard = wizard.getByTestId(/frontend-card-/).first();
            await expect(frontendCard).toBeVisible({ timeout: 10000 });
            await frontendCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 3: Backend (Driver)
            const backendCard = wizard.getByTestId(/backend-card-/).first();
            await expect(backendCard).toBeVisible({ timeout: 10000 });
            await backendCard.click();
            await dialog.getByRole('button', { name: /Next/i }).click();

            // Step 3B (conditional): Deck — only shown for LiquidHandlers with compatible decks
            const deckStep = wizard.getByTestId('wizard-step-deck');
            if (await deckStep.isVisible().catch(() => false)) {
                const deckCard = wizard.getByTestId(/deck-card-/).first();
                await expect(deckCard).toBeVisible({ timeout: 10000 });
                await deckCard.click();
                await dialog.getByRole('button', { name: /Next/i }).click();
            }

            // Step 4: Config — clear the name input
            const nameInput = wizard.getByTestId('input-instance-name');
            await expect(nameInput).toBeVisible({ timeout: 10000 });
            await nameInput.clear();

            // Verify Next button is disabled when name is empty
            const nextBtn = dialog.getByRole('button', { name: /Next/i });
            await expect(nextBtn).toBeDisabled({ timeout: 5000 });

            // Close dialog
            await page.keyboard.press('Escape');
        });

        test('should cancel delete when dialog is dismissed', async ({ page }) => {
            const machineName = `Cancel Delete ${Date.now()}`;
            await assetsPage.goto();
            await assetsPage.waitForOverlay();
            await assetsPage.navigateToMachines();
            await assetsPage.createMachine(machineName);
            await assetsPage.verifyAssetVisible(machineName);

            // Navigate back to Machines tab to ensure table is visible
            await assetsPage.navigateToMachines();

            // Set up dialog handler to REJECT deletion
            page.once('dialog', dialog => dialog.dismiss());

            // Find the row with the machine name and click delete button
            const row = page.locator('tr').filter({ hasText: machineName });
            await expect(row).toBeVisible({ timeout: 5000 });
            const deleteBtn = row.getByRole('button', { name: /delete/i }).or(
                row.locator('button[mattooltip*="Delete"]')
            );

            // Use the same pattern as deleteMachine page object
            if (await deleteBtn.isVisible({ timeout: 2000 })) {
                await deleteBtn.click();
            } else {
                // Try context menu approach
                const moreBtn = row.getByRole('button').filter({ hasText: /more_vert/i });
                if (await moreBtn.isVisible({ timeout: 1000 })) {
                    await moreBtn.click();
                    await page.getByRole('menuitem', { name: /Delete/i }).click();
                }
            }

            // Verify machine still exists after dismissing the dialog
            await expect(row).toBeVisible({ timeout: 5000 });
        });
    });
});


