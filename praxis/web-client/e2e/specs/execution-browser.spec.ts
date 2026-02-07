import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { WelcomePage } from '../page-objects/welcome.page';
import { RunProtocolPage } from '../page-objects/run-protocol.page';
import { ExecutionMonitorPage } from '../page-objects/monitor.page';

test.describe('Execution Browser (Modern)', () => {
  test.setTimeout(180000);

  test('should execute a protocol and record it in history', async ({ page }, testInfo) => {
    // 1. Force a clean reset to ensure protocols are loaded from praxis.db
    await gotoWithWorkerDb(page, '/', testInfo, { resetdb: true, timeout: 60000 });

    const welcomePage = new WelcomePage(page);
    await welcomePage.handleSplashScreen();
    
    // 2. Navigate to Run Protocol
    await page.locator('[data-tour-id="nav-run"]').click();
    const runPage = new RunProtocolPage(page);
    await runPage.waitForProtocolsLoaded();
    
    // Verify protocols loaded
    const count = await runPage.protocolCards.count();
    expect(count).toBeGreaterThan(0);
    
    // 3. Select first protocol
    const protocolCard = runPage.protocolCards.first();
    const protoName = (await protocolCard.locator('.card-title, .protocol-name, h3').textContent())?.trim();
    console.log(`[Test] Selected protocol: ${protoName}`);
    await runPage.selectFirstProtocol();
    
    // 4. Advance through wizard
    for (let i = 0; i < 15; i++) {
        const startBtn = page.getByRole('button', { name: /Start Execution/i });
        if (await startBtn.isVisible({ timeout: 500 }).catch(() => false)) break;

        const nextBtn = page.locator('button:has-text("Continue"), button:has-text("Next"), button:has-text("Skip Setup")').filter({ visible: true }).first();
        if (await nextBtn.isVisible() && await nextBtn.isEnabled()) {
            await nextBtn.click();
            await page.waitForTimeout(1000);
        } else {
            // Might need to select a machine
            if (await runPage.machineSelection.first().isVisible().catch(() => false)) {
                await runPage.selectFirstMachine();
                await page.waitForTimeout(1000);
            }
        }
    }

    // 5. Start Execution
    const startBtn = page.getByRole('button', { name: /Start Execution/i });
    await expect(startBtn).toBeVisible({ timeout: 20000 });
    await startBtn.click();
    
    // Wait for navigation to live view
    await expect(page).toHaveURL(/.*\/live/, { timeout: 30000 });
    
    // 6. Verify in History
    await page.locator('[data-tour-id="nav-monitor"]').click();
    const monitorPage = new ExecutionMonitorPage(page);
    await monitorPage.navigateToHistory();
    
    // Give it a moment and reload if needed to ensure persistence is visible
    await page.waitForTimeout(2000);
    await page.reload();
    await monitorPage.navigateToHistory();

    const row = await monitorPage.waitForHistoryRow(protoName!);
    await expect(row).toBeVisible();
    console.log(`[Test] Successfully verified ${protoName} in history.`);
  });

  test('should display seeded execution history correctly', async ({ page }, testInfo) => {
    // 1. Reset and navigate
    await gotoWithWorkerDb(page, '/', testInfo, { resetdb: true, timeout: 60000 });
    const welcomePage = new WelcomePage(page);
    await welcomePage.handleSplashScreen();

    // 2. Seed mock data
    console.log('[Test] Seeding mock execution data...');
    await page.evaluate(async () => {
      const sqlite = (window as any).sqliteService;
      const repos = await new Promise<any>((resolve) => {
          sqlite.getAsyncRepositories().subscribe(resolve);
      });

      const protocols = await new Promise<any[]>((resolve) => {
          repos.protocolDefinitions.findAll().subscribe(resolve);
      });

      const protoId = protocols[0]?.accession_id;
      if (!protoId) throw new Error('No protocols found in database to seed against');
      
      const runs = [
        {
          accession_id: 'run-completed-001',
          top_level_protocol_definition_accession_id: protoId,
          status: 'completed',
          name: 'Completed Protocol',
          start_time: new Date(Date.now() - 3600000).toISOString(),
          end_time: new Date(Date.now() - 3500000).toISOString(),
          input_parameters_json: { vol: 100 },
          created_at: new Date(Date.now() - 3600000).toISOString()
        }
      ];

      for (const run of runs) {
        await new Promise((resolve) => {
            repos.protocolRuns.create(run).subscribe(resolve);
        });
      }
    });

    // 3. Navigate to Monitor and verify
    const monitorPage = new ExecutionMonitorPage(page);
    await monitorPage.navigateToHistory();
    
    // Give it a moment and reload to ensure seeding is visible
    await page.waitForTimeout(2000);
    await page.reload();
    await monitorPage.navigateToHistory();

    console.log('[Test] Verifying seeded "Completed Protocol"');
    const completedRow = await monitorPage.waitForHistoryRow('Completed Protocol');
    await expect(completedRow).toContainText(/completed/i);
    
    // 4. Verify Detail Navigation
    await completedRow.click();
    await expect(page).toHaveURL(/\/app\/monitor\/.+$/);
    await monitorPage.expectRunDetailVisible('Completed Protocol');
    console.log('[Test] Seeded history and details verified.');
  });
});
