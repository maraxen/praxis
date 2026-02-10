/**
 * Verify every protocol executes successfully with Chatterbox backend.
 * Runs each protocol through wizard → execution → COMPLETED status.
 */
import { expect, test, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import type { Page, TestInfo } from '@playwright/test';
import { ProtocolPage } from '../page-objects/protocol.page';
import { ExecutionMonitorPage } from '../page-objects/monitor.page';
import { WizardPage } from '../page-objects/wizard.page';

// All protocol display names (as shown in the UI protocol cards)
const ALL_PROTOCOLS = [
    'Selective Transfer',
    'Serial Dilution',
    'Kinetic Assay',
    'Plate Preparation',
    'Plate Reader Assay',
];

for (const protocolName of ALL_PROTOCOLS) {
    test.describe(`Protocol: ${protocolName}`, () => {
        test(`executes ${protocolName} to completion`, async ({ page }, testInfo) => {
            // Collect all Python stdout/stderr
            const logs: string[] = [];
            page.on('console', msg => {
                const text = msg.text();
                if (text.includes('[Python') || text.includes('[Browser]')) {
                    logs.push(text);
                    console.log(`[Console] ${text}`);
                }
            });

            await gotoWithWorkerDb(page, '/app/home', testInfo);
            await expect(page.locator('.sidebar-rail')).toBeVisible({ timeout: 10000 });

            // Wizard flow
            const protocolPage = new ProtocolPage(page, testInfo);
            const wizardPage = new WizardPage(page, testInfo);
            await protocolPage.goto();
            await protocolPage.ensureSimulationMode();

            const displayName = await protocolPage.selectProtocol(protocolName);
            console.log(`[Test] Selected: ${displayName}`);

            await wizardPage.completeParameterStep();
            await wizardPage.selectFirstCompatibleMachine();
            await wizardPage.waitForAssetsAutoConfigured();
            await wizardPage.completeWellSelectionStep();
            await wizardPage.advanceDeckSetup();
            await wizardPage.openReviewStep();
            await wizardPage.assertReviewSummary(displayName);

            // Execute
            await wizardPage.startExecution();
            const monitor = new ExecutionMonitorPage(page, testInfo);
            await monitor.waitForLiveDashboard();

            // Wait for terminal status — expect COMPLETED
            await monitor.waitForStatus(/COMPLETED|FAILED/, 90000);

            // Extract final status
            const finalStatus = await page.getByTestId('run-status').innerText();
            console.log(`[Test] ${protocolName} final status: ${finalStatus}`);

            // Log the execution trace
            const pythonLogs = logs.filter(l => l.includes('[Python STDOUT]'));
            console.log(`\n===== EXECUTION LOG: ${protocolName} =====`);
            for (const line of pythonLogs) {
                // Strip the prefix for readability
                const cleaned = line.replace(/\[Python STDOUT\][:]?\s?/, '');
                console.log(cleaned);
            }
            console.log(`===== END: ${protocolName} (${finalStatus}) =====\n`);

            // Check for errors in stderr
            const stderrErrors = logs
                .filter(l => l.includes('[Python STDERR]'))
                .filter(l => l.includes('TypeError') || l.includes('AttributeError') ||
                    l.includes('IndexError') || l.includes('Traceback'));

            if (stderrErrors.length > 0) {
                console.log(`[Test] STDERR ERRORS for ${protocolName}:`);
                stderrErrors.forEach(e => console.log(`  ${e}`));
            }

            // Assert completed (not just "doesn't crash")
            expect(finalStatus.toLowerCase()).toBe('completed');

            await page.screenshot({ path: `/tmp/e2e-protocol/03b-${protocolName.replace(/\s+/g, '-').toLowerCase()}.png` });
        });
    });
}
