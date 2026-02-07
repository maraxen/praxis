import { expect, test } from '../fixtures/worker-db.fixture';
import type { Page } from '@playwright/test';
import { WelcomePage } from '../page-objects/welcome.page';
import { ProtocolPage } from '../page-objects/protocol.page';
import { ExecutionMonitorPage } from '../page-objects/monitor.page';
import { WizardPage } from '../page-objects/wizard.page';

test.describe.serial('Protocol Execution E2E', () => {
    test.beforeEach(async ({ page }) => {
        page.on('console', msg => {
            const text = msg.text();
            if (msg.type() === 'error' || text.includes('[Python') || text.includes('[Worker]') || text.includes('[Browser]')) {
                console.log(`[Browser Console] ${text}`);
            }
        });
        await page.goto('/');
        // In browser mode, we expect a redirect to /app/home
        await page.waitForURL('**/app/home', { timeout: 15000 }).catch((e) => {
            console.log('[Test] Silent catch (waitForURL home):', e);
        });

        // Ensure shell layout is visible
        await expect(page.locator('.sidebar-rail')).toBeVisible({ timeout: 10000 });

        // Handle Welcome Dialog if present (Browser Mode)
        const welcomeDialog = page.getByRole('dialog', { name: /Welcome to Praxis/i });
        if (await welcomeDialog.isVisible({ timeout: 5000 })) {
            console.log('Dismissing Welcome Dialog...');
            await page.getByRole('button', { name: /Skip for Now/i }).click();
            await expect(welcomeDialog).not.toBeVisible();
        }
    });

    test.afterEach(async ({ page }) => {
        // Dismiss any open dialogs/overlays to ensure clean state
        await page.keyboard.press('Escape').catch((e) => console.log('[Test] Silent catch (Escape):', e));
    });

    test('select protocol from library', async ({ page }) => {
        const protocolPage = new ProtocolPage(page);
        await protocolPage.goto();
        await protocolPage.ensureSimulationMode();
        const protocolName = await protocolPage.selectFirstProtocol();
        await protocolPage.continueFromSelection();
        await expect(page.locator('[data-tour-id="run-step-params"]')).toBeVisible();
        await page.screenshot({ path: '/tmp/e2e-protocol/03-spec-01-selection.png' });
    });

    test('complete setup wizard steps', async ({ page }) => {
        const { protocolName } = await prepareExecution(page);
        await expect(page.getByRole('tab', { name: /Review & Run/i })).toHaveAttribute('aria-selected', 'true');
        await expect(page.locator('button', { hasText: 'Start Execution' })).toBeVisible();
        await expect(page.locator('h2', { hasText: 'Ready to Launch' })).toBeVisible();
        await expect(page.locator('[data-testid="review-protocol-name"]')).toHaveText(protocolName);
        await page.screenshot({ path: '/tmp/e2e-protocol/03-spec-02-wizard-complete.png' });
    });

    test('execute protocol and monitor lifecycle', async ({ page }) => {
        // 1. Launch Execution
        const { monitor, protocolName, runName, runId } = await launchExecution(page);

        // 2. Monitor status transitions
        console.log('[Spec] Waiting for RUNNING or COMPLETED...');
        await monitor.waitForStatus(/RUNNING|COMPLETED/);
        expect(runName).toContain(protocolName);

        // 3. Verify Progress and Logs (only if still running or just finished)
        await monitor.waitForProgressAtLeast(50);
        await monitor.waitForLogEntry('Executing protocol');

        // 4. Wait for Completion
        console.log('[Spec] Waiting for COMPLETED...');
        await monitor.waitForStatus(/COMPLETED/);
        await monitor.waitForLogEntry('Execution completed successfully');

        // 5. Verify History and Details
        await monitor.navigateToHistory();
        await monitor.waitForHistoryRow(runName);
        await monitor.openRunDetailById(runId);
        await monitor.expectRunDetailVisible(runName);

        await page.screenshot({ path: '/tmp/e2e-protocol/03-spec-lifecycle-complete.png' });
    });

    test('parameter values reach execution', async ({ page }) => {
        const protocolPage = new ProtocolPage(page);
        const wizardPage = new WizardPage(page);

        await protocolPage.goto();
        await protocolPage.ensureSimulationMode();
        // Use 'Simple Transfer' which we know has a volume_ul parameter
        await protocolPage.selectProtocolByName('Simple Transfer');
        await protocolPage.continueFromSelection();

        // Configure parameter
        const testVolume = '123.45';
        await protocolPage.configureParameter('volume_ul', testVolume);

        await wizardPage.completeParameterStep();
        await wizardPage.selectFirstCompatibleMachine();
        await wizardPage.waitForAssetsAutoConfigured();
        await wizardPage.completeWellSelectionStep();
        await wizardPage.advanceDeckSetup();
        await wizardPage.openReviewStep();

        // Start execution
        await wizardPage.startExecution();

        const monitor = new ExecutionMonitorPage(page);
        await monitor.waitForLiveDashboard();
        const { runId, runName } = await monitor.captureRunMeta();

        // Navigate to details and verify parameter
        await monitor.navigateToHistory();
        await monitor.waitForHistoryRow(runName);
        await monitor.openRunDetailById(runId);

        await monitor.verifyParameter('volume_ul', testVolume);
        await page.screenshot({ path: '/tmp/e2e-protocol/03-spec-06-parameter-verification.png' });
    });
});

async function prepareExecution(page: Page) {
    const protocolPage = new ProtocolPage(page);
    const wizardPage = new WizardPage(page);
    await protocolPage.goto();
    await protocolPage.ensureSimulationMode();
    const protocolName = await protocolPage.selectFirstProtocol();
    await protocolPage.continueFromSelection();
    await wizardPage.completeParameterStep();
    await wizardPage.selectFirstCompatibleMachine();
    await wizardPage.waitForAssetsAutoConfigured();
    await wizardPage.completeWellSelectionStep();
    await wizardPage.advanceDeckSetup();
    await wizardPage.openReviewStep();
    await wizardPage.assertReviewSummary(protocolName);
    return { protocolName, wizardPage };
}

async function launchExecution(page: Page) {
    const { protocolName, wizardPage } = await prepareExecution(page);
    await wizardPage.startExecution();
    const monitor = new ExecutionMonitorPage(page);
    await monitor.waitForLiveDashboard();
    const meta = await monitor.captureRunMeta();
    return { monitor, protocolName, runName: meta.runName, runId: meta.runId };
}
