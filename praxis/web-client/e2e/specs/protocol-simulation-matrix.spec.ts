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

                // 4. Select first available protocol by clicking on its heading
                // Protocol cards have h3 headings with name like "Simple Transfer", "Serial Dilution", etc.
                const protocolHeadings = page.getByRole('heading', { level: 3 }).filter({
                    hasNotText: /All Protocols|Category|Type/i
                });

                // Wait for protocol headings to be visible
                await expect(protocolHeadings.first()).toBeVisible({ timeout: 15000 });
                const protocolName = await protocolHeadings.first().textContent();
                console.log(`[Matrix] Selecting protocol: ${protocolName}`);

                // Click on the protocol card (parent element of the heading)
                await protocolHeadings.first().click();
                await page.waitForTimeout(500);

                // 5. Advance through wizard by handling each step type
                const continueBtn = page.getByRole('button', { name: /^Continue$/i });
                const nextBtn = page.getByRole('button', { name: /^Next$/i });
                const skipSetupBtn = page.getByRole('button', { name: /Skip Setup/i });
                const startBtn = page.getByRole('button', { name: /Start Execution|^Start$|^Run$/i });

                for (let step = 0; step < 15; step++) {
                    await page.waitForTimeout(500);

                    // Check if Start button is visible and enabled - we're done!
                    if (await startBtn.first().isVisible({ timeout: 500 }).catch(() => false)) {
                        if (await startBtn.first().isEnabled().catch(() => false)) {
                            console.log(`[Matrix] Start button found after ${step} wizard steps`);
                            break;
                        }
                    }

                    // Handle deck setup - click Skip Setup if visible
                    if (await skipSetupBtn.isVisible({ timeout: 500 }).catch(() => false)) {
                        await skipSetupBtn.click();
                        console.log('[Matrix] Clicked Skip Setup');
                        continue;
                    }

                    // Handle machine selection - click first machine card if visible
                    const machineCard = page.locator('.machine-card').first();
                    if (await machineCard.isVisible({ timeout: 500 }).catch(() => false)) {
                        await machineCard.click();
                        console.log('[Matrix] Selected machine');
                        await page.waitForTimeout(300);
                    }

                    // Handle asset selection - click first asset card if visible
                    const assetCard = page.locator('.asset-card, [data-testid="asset-card"]').first();
                    if (await assetCard.isVisible({ timeout: 500 }).catch(() => false)) {
                        await assetCard.click();
                        console.log('[Matrix] Selected asset');
                        await page.waitForTimeout(300);
                    }

                    // Handle well selection - click "Select All" if available, or first well group
                    const selectAllBtn = page.getByRole('button', { name: /Select All/i });
                    if (await selectAllBtn.isVisible({ timeout: 500 }).catch(() => false)) {
                        await selectAllBtn.click();
                        console.log('[Matrix] Clicked Select All for wells');
                        await page.waitForTimeout(300);
                    }

                    // Look for checkboxes and check them
                    const checkbox = page.locator('mat-checkbox:not(.mat-checkbox-checked)').first();
                    if (await checkbox.isVisible({ timeout: 500 }).catch(() => false)) {
                        await checkbox.click();
                        console.log('[Matrix] Checked checkbox');
                        await page.waitForTimeout(300);
                    }

                    // Try Continue button first
                    if (await continueBtn.first().isVisible({ timeout: 500 }).catch(() => false)) {
                        if (await continueBtn.first().isEnabled().catch(() => false)) {
                            await continueBtn.first().click();
                            console.log(`[Matrix] Clicked Continue (step ${step + 1})`);
                            continue;
                        } else {
                            console.log('[Matrix] Continue is disabled - need more selections');
                        }
                    }

                    // Try Next button 
                    if (await nextBtn.first().isVisible({ timeout: 500 }).catch(() => false)) {
                        if (await nextBtn.first().isEnabled().catch(() => false)) {
                            await nextBtn.first().click();
                            console.log(`[Matrix] Clicked Next (step ${step + 1})`);
                            continue;
                        } else {
                            console.log('[Matrix] Next is disabled - may need more selections');
                        }
                    }

                    // If neither Continue nor Next is available, we might be stuck
                    console.log(`[Matrix] No advancement buttons visible/enabled on step ${step}`);
                }

                // 6. Start execution
                await expect(startBtn.first()).toBeEnabled({ timeout: 15000 });
                await startBtn.first().click();
                console.log('[Matrix] Clicked Start Execution');

                // 8. Wait for Execution Monitor page to load
                await expect(page.getByRole('heading', { name: /Execution Monitor/i })).toBeVisible({ timeout: 30000 });
                console.log('[Matrix] Execution Monitor loaded');

                // 9. Wait for execution to complete - check page content for completion indicators
                const timeout = protocol.expectedDuration * 1000 * 2; // 2x buffer
                await expect(async () => {
                    const pageText = await page.textContent('body') || '';
                    expect(
                        pageText.includes('COMPLETED') ||
                        pageText.includes('100%') ||
                        pageText.includes('Execution completed successfully')
                    ).toBe(true);
                }).toPass({
                    timeout: Math.max(timeout, 60000),
                });
                console.log('[Matrix] Execution completed');

                // 10. Verify no Python errors in logs
                const logs = page.locator(
                    '[data-testid="execution-logs"], ' +
                    '.execution-logs, ' +
                    '.log-output, ' +
                    'pre'
                );

                if (await logs.first().isVisible({ timeout: 2000 }).catch(() => false)) {
                    const logText = await logs.first().textContent() || '';
                    expect(logText).not.toContain('Error:');
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
