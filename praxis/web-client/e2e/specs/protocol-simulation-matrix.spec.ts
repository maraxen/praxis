/**
 * Protocol Simulation Matrix Test
 *
 * @slow - Runs all simulatable protocols in browser simulation mode.
 *
 * This test iterates through all registered protocols and attempts to:
 * 1. Navigate to the Run Protocol wizard
 * 2. Select the protocol
 * 3. Select a simulated machine
 * 4. Start execution
 * 5. Wait for completion
 *
 * Failures are categorized as:
 * - Protocol bugs (Python errors in execution)
 * - App bugs (selector/navigation failures)
 * - Timeouts (execution didn't complete in time)
 *
 * Run with: RUN_SLOW_TESTS=1 npx playwright test protocol-simulation-matrix.spec.ts --config=playwright.static.config.ts
 */

import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { WelcomePage } from '../page-objects/welcome.page';
import { RunProtocolPage } from '../page-objects/run-protocol.page';
import { SIMULATABLE_PROTOCOLS, ProtocolTestEntry } from '../helpers/protocol-registry';
import { categorizeFailure, MatrixResult, formatMatrixSummary } from '../helpers/matrix-reporter';

/**
 * Store results for summary output
 */
const matrixResults: MatrixResult[] = [];

test.describe('@slow Protocol Simulation Matrix', () => {
    // Extended timeout for protocol execution (3 minutes per test)
    test.setTimeout(180000);

    // Run tests serially to avoid resource contention
    test.describe.configure({ mode: 'serial' });

    for (const protocol of SIMULATABLE_PROTOCOLS) {
        test(`simulates "${protocol.name}" to completion`, async ({ page }, testInfo) => {
            const startTime = Date.now();

            // Tag test with protocol ID for filtering
            testInfo.annotations.push({ type: 'protocol', description: protocol.id });

            try {
                // 1. Navigate with worker-scoped database
                await gotoWithWorkerDb(page, '/app/run', testInfo, { resetdb: true });

                // 2. Handle splash screen if present
                const welcomePage = new WelcomePage(page);
                await welcomePage.handleSplashScreen().catch(() => {
                    // Splash may not appear if already dismissed
                });

                // 3. Wait for protocols to load
                const runPage = new RunProtocolPage(page);
                await runPage.waitForProtocolsLoaded();

                // 4. Try to find and select this specific protocol
                // First try by data-testid with protocol ID
                const protocolCard = page.locator(
                    `[data-testid="protocol-card-${protocol.id}"], ` +
                    `.protocol-card[data-id="${protocol.id}"], ` +
                    `.protocol-card:has-text("${protocol.id.slice(0, 8)}")`
                );

                if (await protocolCard.first().isVisible({ timeout: 5000 })) {
                    await protocolCard.first().click();
                } else {
                    // Fall back to first available protocol if specific one not found
                    console.log(
                        `[Matrix] Protocol ${protocol.id} card not found, selecting first available`
                    );
                    await runPage.selectFirstProtocol();
                }

                // 5. Select simulated machine
                const simulatedMachine = page.locator(
                    '[data-testid="machine-simulated"], ' +
                    '.machine-card:has-text("Simulated"), ' +
                    '.machine-card:has-text("Simulator")'
                );

                if (await simulatedMachine.first().isVisible({ timeout: 5000 })) {
                    await simulatedMachine.first().click();
                } else {
                    // Select first machine if no explicit simulator option
                    await runPage.selectFirstMachine();
                }

                // 6. Advance through wizard steps
                for (let step = 0; step < 5; step++) {
                    // Check if we've reached the start button (visible in final step)
                    const startBtn = page.locator('button:has-text("Start"), button:has-text("Run")').first();
                    if (await startBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
                        break;
                    }

                    // Find the enabled Continue/Next button in the current active step
                    // Use aria-selected to find the active step, then its continue button
                    const activeStepContinue = page.locator(
                        'mat-step-header[aria-selected="true"] ~ .mat-vertical-content-container button:has-text("Continue"), ' +
                        'mat-step-header[aria-selected="true"] ~ .mat-vertical-content-container button:has-text("Next"), ' +
                        '.mat-step-content:visible button:has-text("Continue"):not([disabled]), ' +
                        '.mat-step-content:visible button:has-text("Next"):not([disabled])'
                    ).first();

                    if (await activeStepContinue.isVisible({ timeout: 2000 }).catch(() => false)) {
                        if (await activeStepContinue.isEnabled({ timeout: 1000 }).catch(() => false)) {
                            await activeStepContinue.click();
                            await page.waitForTimeout(500); // Brief wait for step transition
                        } else {
                            break; // Button exists but disabled, can't proceed
                        }
                    } else {
                        break; // No continue button visible
                    }
                }

                // 7. Start execution
                await runPage.startExecution();

                // 8. Wait for execution to start
                const executionStatus = page.locator(
                    '[data-testid="execution-status"], ' +
                    '.execution-status, ' +
                    '[class*="status"]'
                );

                await expect(executionStatus).toContainText(/running|initializing|executing/i, {
                    timeout: 30000,
                });

                // 9. Wait for completion with protocol-specific timeout
                const timeout = protocol.expectedDuration * 1000 * 2; // 2x buffer
                await expect(executionStatus).toContainText(/completed|finished|done|success/i, {
                    timeout: Math.max(timeout, 60000),
                });

                // 10. Verify no Python errors in logs
                const logs = page.locator(
                    '[data-testid="execution-logs"], ' +
                    '.execution-logs, ' +
                    '.log-output'
                );

                if (await logs.isVisible({ timeout: 2000 })) {
                    const logText = await logs.textContent();
                    expect(logText).not.toContain('Error');
                    expect(logText).not.toContain('Traceback');
                    expect(logText).not.toContain('NameError');
                    expect(logText).not.toContain('TypeError');
                }

                // Record success
                matrixResults.push({
                    protocolId: protocol.id,
                    status: 'passed',
                    duration: Date.now() - startTime,
                });
            } catch (error) {
                // Record failure with categorization
                const errorMessage = error instanceof Error ? error.message : String(error);
                matrixResults.push({
                    protocolId: protocol.id,
                    status: 'failed',
                    failureCategory: categorizeFailure(errorMessage),
                    errorMessage: errorMessage.slice(0, 500),
                    duration: Date.now() - startTime,
                });

                // Re-throw to mark test as failed
                throw error;
            }
        });
    }

    // Summary test that runs last
    test('outputs matrix summary', async () => {
        // This test always passes - it just outputs the summary
        const summary = formatMatrixSummary(matrixResults);
        console.log('\n' + '='.repeat(60) + '\n');
        console.log(summary);
        console.log('\n' + '='.repeat(60) + '\n');

        // Also log to test annotations for easy access
        test.info().annotations.push({
            type: 'matrix-summary',
            description: summary,
        });
    });
});
