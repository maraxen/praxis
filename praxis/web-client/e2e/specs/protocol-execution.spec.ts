import { test, expect } from '../fixtures/app.fixture';
import { ProtocolPage } from '../page-objects/protocol.page';
import { WizardPage } from '../page-objects/wizard.page';

test.describe('Protocol Wizard Flow', () => {
    let protocolPage: ProtocolPage;
    let wizardPage: WizardPage;

    test.beforeEach(async ({ page }) => {
        protocolPage = new ProtocolPage(page);
        wizardPage = new WizardPage(page);
        // The app fixture navigates and handles the welcome dialog automatically.
        // We can now expect to be on the home page.
        await expect(page).toHaveURL(/\/app\/home/, { timeout: 15000 });
        await protocolPage.ensureSimulationMode();
    });

    test.afterEach(async ({ page }) => {
        // Dismiss any open dialogs/overlays to ensure clean state
        await page.keyboard.press('Escape').catch((e) => console.log('[Test] Silent catch (Escape):', e));
    });

    test('should display protocol library', async ({ page }) => {
        await protocolPage.navigateToProtocols();
        await expect(protocolPage.protocolCards.first()).toBeVisible();
        
        await test.info().attach('protocol-library', {
            body: await page.screenshot(),
            contentType: 'image/png'
        });

        // Verify at least one protocol is available
        expect(await protocolPage.protocolCards.count()).toBeGreaterThan(0);
    });

    test('should complete simulated execution', async ({ page }) => {
        test.setTimeout(120000); // Allow extra time for full flow

        await test.step('Navigate to Protocols', async () => {
            await protocolPage.goto();
            await wizardPage.assertOnStep('protocol');
            await test.info().attach('navigate-protocols', {
                body: await page.screenshot(),
                contentType: 'image/png'
            });
        });

        await test.step('Select and Configure Protocol', async () => {
            const protocolName = 'Simple Transfer';
            await protocolPage.assertProtocolAvailable(protocolName);
            await protocolPage.selectProtocol(protocolName);
            await wizardPage.assertOnStep('params');

            // Configure Minimal Parameters (if any are required/visible)
            // For Simple Transfer, defaults might be fine.
            // We'll advance through the wizard using the helper we added
            await protocolPage.advanceToReview();
            await wizardPage.assertOnStep('review');
            await test.info().attach('review-step', {
                body: await page.screenshot(),
                contentType: 'image/png'
            });
        });

        await test.step('Start Execution', async () => {
            await protocolPage.startExecution();
            // Status might take a moment to appear
            const status = await protocolPage.getExecutionStatus();
            expect(status).toMatch(/Initializing|Running|Queued|Starting/i);
            await test.info().attach('execution-started', {
                body: await page.screenshot(),
                contentType: 'image/png'
            });
        });

        await test.step('Monitor Execution Progress', async () => {
            // Wait for running state if not already
            // The monitor page usually shows progress
            await expect(page.locator('mat-progress-bar')).toBeVisible({ timeout: 10000 });
            await test.info().attach('execution-progress', {
                body: await page.screenshot(),
                contentType: 'image/png'
            });
        });

        await test.step('Complete Execution', async () => {
            await protocolPage.waitForCompletion();
            const finalStatus = await protocolPage.getExecutionStatus();
            expect(finalStatus).toMatch(/(Completed|Succeeded|Finished)/i);
            await test.info().attach('execution-completed', {
                body: await page.screenshot(),
                contentType: 'image/png'
            });
        });

        await test.step('Verify run persisted to database', async () => {
            const runRecord = await page.evaluate(async () => {
                const db = await (window as any).sqliteService.getDatabase();
                const result = db.exec("SELECT id, status FROM run_history ORDER BY created_at DESC LIMIT 1");
                return result[0]?.values[0];
            });
            expect(runRecord).toBeTruthy();
            expect(runRecord[1]).toMatch(/COMPLETED|SUCCEEDED/i);
        });

        await test.step('Verify parameter serialization', async () => {
            const runParams = await page.evaluate(async () => {
                const db = await (window as any).sqliteService.getDatabase();
                const result = db.exec("SELECT parameters FROM run_history ORDER BY created_at DESC LIMIT 1");
                return result[0]?.values[0]?.[0];
            });
            expect(runParams).toBeTruthy();
            const parsed = JSON.parse(runParams);
            // Verify expected structure exists
            expect(parsed).toHaveProperty('protocol');
        });
    });

    test('should handle no compatible machines gracefully', async ({ page }) => {
        await protocolPage.goto();
        // This protocol is assumed to exist and have no compatible machines in the default test setup.
        // A more robust solution would be to seed this protocol state.
        await protocolPage.selectProtocol('Hardware-Only Protocol');
        
        const noMachinesState = page.locator('.no-machines-state, .empty-state');
        await expect(noMachinesState).toBeVisible();
        
        // Verify Continue is disabled
        const continueBtn = page.getByRole('button', { name: /Continue/i });
        await expect(continueBtn).toBeDisabled();
    });

    test('should handle execution cancellation', async ({ page }) => {
        await protocolPage.goto();
        await protocolPage.selectProtocol('Simple Transfer');
        await protocolPage.advanceToReview();
        await protocolPage.startExecution();
      
        // Wait for running state
        await expect(page.locator('[data-testid="run-status"]')).toContainText(/RUNNING/i, { timeout: 15000 });
      
        // Click abort button
        await page.getByRole('button', { name: /Abort|Cancel|Stop/i }).click();
      
        // Confirm in dialog
        await page.getByRole('button', { name: /Confirm/i }).click();
      
        // Verify aborted state
        await expect(page.locator('[data-testid="run-status"]')).toContainText(/ABORTED|CANCELLED/i, { timeout: 15000 });
    });
});
