import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { RunProtocolPage } from '../page-objects/run-protocol.page';
import { ExecutionMonitorPage } from '../page-objects/monitor.page';
import { waitForDbReady, dbExec, dbQueryScalar } from '../helpers/e2e-db.helper';

test.describe('Execution Browser (Modern)', () => {
  test.setTimeout(180000);

  test('should execute a protocol and record it in history', async ({ page }, testInfo) => {
    // 1. Navigate with worker-scoped database
    await gotoWithWorkerDb(page, '/app/home', testInfo, { resetdb: true, timeout: 60000 });

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

    // 6. Verify in History — navigate away and back to force fresh component mount
    await page.waitForTimeout(3000);
    await page.goto('/app/home', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const monitorPage = new ExecutionMonitorPage(page, testInfo);
    await monitorPage.navigateToHistory();

    // Wait for auto-refresh (10s interval) to pick up the new run
    // Use toPass for retry, checking every 2s
    await expect(async () => {
      const rows = page.locator('app-run-history-table tr').filter({ hasText: protoName! });
      const count = await rows.count();
      if (count === 0) {
        // Force reload and re-navigate
        await page.goto('/app/monitor', { waitUntil: 'domcontentloaded' });
        throw new Error('Row not yet visible');
      }
    }).toPass({ timeout: 30000, intervals: [2000, 3000, 5000] });

    const row = page.locator('app-run-history-table tr').filter({ hasText: protoName! }).first();
    await expect(row).toBeVisible();
    console.log(`[Test] Successfully verified ${protoName} in history.`);
  });

  test('should display seeded execution history correctly', async ({ page }, testInfo) => {
    // 1. Reset and navigate
    await gotoWithWorkerDb(page, '/app/home', testInfo, { resetdb: true, timeout: 60000 });
    await waitForDbReady(page);

    // 2. Seed mock data via OPFS worker pipeline (correct table: function_protocol_definitions)
    console.log('[Test] Seeding mock execution data via OPFS exec...');
    await page.evaluate(async () => {
      const e2e = (window as any).__e2e;
      if (!e2e) throw new Error('__e2e test API not found');

      // Get a valid protocol ID from the correct table
      const protos = await e2e.query("SELECT accession_id FROM function_protocol_definitions LIMIT 1");
      const protoId = protos[0]?.accession_id;
      if (!protoId) throw new Error('No protocols found in function_protocol_definitions');

      const now = new Date().toISOString();
      const hourAgo = new Date(Date.now() - 3600000).toISOString();

      // Insert into the correct table: protocol_runs (not run_history)
      await e2e.exec(
        `INSERT OR REPLACE INTO protocol_runs 
         (accession_id, top_level_protocol_definition_accession_id, status, name, start_time, end_time, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        ['run-completed-001', protoId, 'completed', 'Completed Protocol', hourAgo, now, hourAgo, now]
      );

      console.log('[Seed] Protocol run seeded via __e2e API');
    });

    // 3. Navigate away and back to force component re-init with seeded data
    await page.goto('/app/home', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const monitorPage = new ExecutionMonitorPage(page, testInfo);
    await monitorPage.navigateToHistory();

    // Wait for the seeded data to appear with retry logic
    await expect(async () => {
      const rows = page.locator('app-run-history-table tr').filter({ hasText: /Completed Protocol/i });
      const count = await rows.count();
      if (count === 0) {
        await page.goto('/app/monitor', { waitUntil: 'domcontentloaded' });
        throw new Error('Seeded row not yet visible');
      }
    }).toPass({ timeout: 30000, intervals: [2000, 3000, 5000] });

    console.log('[Test] Verifying seeded "Completed Protocol"');
    const completedRow = page.locator('app-run-history-table tr').filter({ hasText: /Completed Protocol/i }).first();
    await expect(completedRow).toBeVisible();
    await expect(completedRow).toContainText(/completed/i);

    // 4. Verify Detail Navigation
    await completedRow.click();
    await expect(page).toHaveURL(/\/app\/monitor\/.+$/);
    await monitorPage.expectRunDetailVisible('Completed Protocol');
    console.log('[Test] Seeded history and details verified.');
  });
});
