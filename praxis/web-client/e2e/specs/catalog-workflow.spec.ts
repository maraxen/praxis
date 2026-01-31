import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { InventoryDialogPage } from '../page-objects/inventory-dialog.page';
import { WelcomePage } from '../page-objects/welcome.page';

test.describe('Catalog to Inventory Workflow', () => {
    test('should add simulated machine from catalog', async ({ page }, testInfo) => {
        // Setup
        await gotoWithWorkerDb(page, '/app/playground', testInfo, { waitForDb: false, mode: 'worker' });
        const welcomePage = new WelcomePage(page);
        await welcomePage.dismissOnboarding();
        
        // Open inventory and verify catalog
        const inventory = new InventoryDialogPage(page);
        await inventory.open();
        
        await expect(inventory.catalogTab).toBeVisible();
        await expect(inventory.catalogTab).toHaveAttribute('aria-selected', 'true');
        
        // Add simulated machine
        await inventory.addSimulatedMachine(0);
        
        // Verify navigation to Browse & Add
        await expect(inventory.browseAddTab).toHaveAttribute('aria-selected', 'true');
        
        // Post-Action Verification
        await inventory.selectTab('Current Items');
        const machines = await inventory.getMachinesInInventory();
        expect(machines.length).toBeGreaterThan(0);
        expect(machines.some(m => /simulation|simulated/i.test(m))).toBe(true);

        // SQLite State Verification
        const machineCount = await page.evaluate(async () => {
            const sqliteService = (window as any).sqliteService;
            if (!sqliteService?.db) return 0;
            const result = await sqliteService.db.exec(
                "SELECT COUNT(*) as count FROM machines WHERE type = 'simulation'"
            );
            return result[0]?.values?.[0]?.[0] ?? 0;
        });
        expect(machineCount).toBeGreaterThan(0);
    });

    test('simulated machine persists after reload', async ({ page }, testInfo) => {
        // Add machine via catalog
        await gotoWithWorkerDb(page, '/app/playground', testInfo, { waitForDb: false, mode: 'worker' });
        const welcomePage = new WelcomePage(page);
        await welcomePage.dismissOnboarding();
        const inventory = new InventoryDialogPage(page);
        await inventory.open();
        await inventory.addSimulatedMachine(0);
        
        // Reload page (without resetdb to preserve data)
        await gotoWithWorkerDb(page, '/app/playground', testInfo, { resetdb: false, waitForDb: false, mode: 'worker' });
        
        await inventory.open();
        await inventory.assertMachineInInventory(/Simulation/);
    });

    test('handles catalog load failure gracefully', async ({ page }, testInfo) => {
        // Intercept catalog API and force failure
        await page.route('**/api/catalog/machines', route => {
            route.fulfill({ status: 500, body: 'Internal Server Error' });
        });
        
        await gotoWithWorkerDb(page, '/app/playground', testInfo, { waitForDb: false, mode: 'worker' });
        const welcomePage = new WelcomePage(page);
        await welcomePage.dismissOnboarding();
        const inventory = new InventoryDialogPage(page);
        await inventory.open();
        
        // Should show error state, not blank/broken UI
        await expect(page.getByText(/failed to load|error|try again/i)).toBeVisible();
    });
});
