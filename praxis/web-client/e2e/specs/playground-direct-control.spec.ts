import { test, expect } from '../fixtures/worker-db.fixture';
import { PlaygroundPage } from '../page-objects/playground.page';
import { WelcomePage } from '../page-objects/welcome.page';

test.describe('@slow Playground Direct Control', () => {
    let playgroundPage: PlaygroundPage;
    let welcomePage: WelcomePage;

    test.beforeEach(async ({ page }) => {
        playgroundPage = new PlaygroundPage(page);
        welcomePage = new WelcomePage(page);
        await playgroundPage.goto('worker');
        await welcomePage.handleSplashScreen();
    });

    test('should allow adding a machine and using direct control', async ({ page }) => {
        test.setTimeout(180000);
        const machineName = 'Hamilton STAR';

        // 1. Open inventory and add a new machine
        const inventoryDialog = await playgroundPage.openInventory();
        await inventoryDialog.addMachine(machineName, 'LiquidHandler', 'STAR');

        // 2. Select the machine in the playground
        await playgroundPage.selectModule(machineName);

        // 3. Domain Verification: Check backend instantiation
        await playgroundPage.verifyBackendInstantiation(machineName);

        // 4. Execute a method
        await playgroundPage.executeCurrentMethod(/Setup/i);

        // 5. Verify the successful result
        await playgroundPage.waitForSuccess(/OK: Setup complete/i);
    });

    test('should display an error if backend initialization fails', async ({ page }) => {
        test.setTimeout(180000);
        const machineName = 'Faulty Hamilton STAR';

        // Mock the machine definition to have an invalid backend FQN
        // This will cause the client-side instantiation to fail.
        await page.route('**/api/v1/machines/definitions?*', async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([
                    {
                        accession_id: 'mach_test_002',
                        name: 'Hamilton STAR',
                        fqn: 'pylabrobot.liquid_handling.backends.hamilton.INVALID_BACKEND', // Deliberately wrong
                        plr_category: 'Machine',
                        machine_category: 'LiquidHandler',
                        manufacturer: 'Hamilton',
                        description: 'A faulty Hamilton STAR liquid handler',
                        available_simulation_backends: ['Simulated']
                    }
                ])
            });
        });

        // 1. Open inventory and add the machine with the faulty definition
        const inventoryDialog = await playgroundPage.openInventory();
        await inventoryDialog.addMachine(machineName, 'LiquidHandler', 'STAR');

        // 2. Select the machine in the playground
        await playgroundPage.selectModule(machineName);

        // 3. Verify that an error is shown in a snackbar or the component
        const errorSnackbar = page.locator('simple-snack-bar');
        const componentError = page.locator('app-direct-control .mat-error, app-direct-control .error-message');

        await expect(errorSnackbar.or(componentError).first()).toBeVisible({ timeout: 15000 });
        await expect(errorSnackbar.or(componentError).first()).toContainText(/Failed to initialize backend|Could not find module/i);
    });
});
