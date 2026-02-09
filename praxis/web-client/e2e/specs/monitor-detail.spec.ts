import { test, expect, buildIsolatedUrl, waitForDbReady } from '../fixtures/app.fixture';
import { gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { ExecutionMonitorPage } from '../page-objects/monitor.page';

/**
 * Seeding helper to inject a fake protocol run directly into the browser SQLite DB.
 * Uses the __e2e API instead of sqliteService for reliability.
 */
async function seedFakeRun(page: any, runId: string, runName: string, status = 'COMPLETED') {
  console.log(`[Seeding] Starting for run ${runId}...`);
  const result = await page.evaluate(async ({ id, name, runStatus }: { id: string; name: string; runStatus: string }) => {
    const e2e = (window as any).__e2e;
    if (!e2e) throw new Error('__e2e API not found');

    // 1. Ensure protocol definition exists
    const protocols = await e2e.query("SELECT * FROM function_protocol_definitions WHERE name = 'Kinetic Assay'");
    let protocolId = 'proto-kinetic-assay';
    if (!protocols || protocols.length === 0) {
      console.log('[Seeding] Protocol not found, creating dummy...');
      await e2e.exec(
        `INSERT INTO function_protocol_definitions (accession_id, name, fqn, version, description, source_file_path, module_name, function_name, is_top_level, solo_execution, preconfigure_deck, requires_deck, deprecated)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [protocolId, 'Kinetic Assay', 'pylabrobot.protocols.kinetic_assay', '1.0.0', 'Seeded for E2E testing', 'kinetic_assay.py', 'kinetic_assay', 'run', 1, 1, 1, 1, 0]
      );
    } else {
      protocolId = protocols[0].accession_id;
    }

    // 2. Create state history
    const stateBefore = { tips: { tips_loaded: false, tips_count: 0 }, liquids: {}, on_deck: [] };
    const stateAfter = { tips: { tips_loaded: true, tips_count: 8 }, liquids: {}, on_deck: [] };
    const stateHistory = {
      run_id: id,
      protocol_name: name,
      operations: [
        {
          operation_index: 0,
          operation_id: 'op_0',
          method_name: 'pick_up_tips',
          resource: 'tip_rack',
          status: 'completed',
          state_before: stateBefore,
          state_after: stateAfter,
          timestamp: new Date().toISOString(),
          duration_ms: 500
        }
      ],
      final_state: stateAfter
    };

    // 3. Create the protocol run
    console.log('[Seeding] Creating run record...');
    const now = new Date().toISOString();
    const inputParams = JSON.stringify({ "Output Directory": "/tmp/output", "Volume": 50 });
    const properties = JSON.stringify({
      notes: "Seeded for E2E testing",
      simulation_mode: true,
      state_history: stateHistory
    });

    await e2e.exec(
      `INSERT INTO protocol_runs (accession_id, protocol_definition_accession_id, top_level_protocol_definition_accession_id, name, status, created_at, start_time, end_time, input_parameters_json, properties_json, resolved_assets_json)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [id, protocolId, protocolId, name, runStatus, now, now, runStatus === 'COMPLETED' ? now : null, inputParams, properties, '[]']
    );

    return { success: true };
  }, { id: runId, name: runName, runStatus: status });
  console.log('[Seeding] Completed:', result);
}

test.describe('Run Detail View (using seeded data)', () => {
  let monitorPage: ExecutionMonitorPage;
  const SEEDED_RUN_ID = 'e2e00000000000000000000000000001';
  const SEEDED_RUN_NAME = 'Seeded Kinetic Assay';

  test.beforeEach(async ({ page }, testInfo) => {
    monitorPage = new ExecutionMonitorPage(page, testInfo);
  });

  test.afterEach(async ({ page }) => {
    await page.keyboard.press('Escape').catch(() => { });
  });

  test('verifies seeded run details', async ({ page }, testInfo) => {
    page.on('console', msg => console.log(`[Browser] ${msg.type()}: ${msg.text()}`));

    // 1. Navigate to monitor page with worker DB isolation
    await gotoWithWorkerDb(page, '/app/monitor', testInfo, { resetdb: true });
    await waitForDbReady(page, 30000);

    // 2. Seed data
    await seedFakeRun(page, SEEDED_RUN_ID, SEEDED_RUN_NAME);

    // 3. Reload to pick up seeded data
    console.log('[Test] Reloading page...');
    await gotoWithWorkerDb(page, '/app/monitor', testInfo, { resetdb: false });
    await waitForDbReady(page, 30000);

    // 4. Verify in history table
    const row = await monitorPage.waitForHistoryRow(SEEDED_RUN_NAME);
    await expect(row).toBeVisible();

    // 5. Open detail view
    console.log('[Test] Clicking row...');
    await row.click();
    await page.waitForURL(/\/app\/monitor\/.+$/, { timeout: 15000 });

    console.log('[Test] Current URL:', page.url());

    // Check for "Run not found"
    if (await page.getByText('Run not found').isVisible()) {
      console.error('[Test] Run NOT FOUND on detail page!');
      const content = await page.content();
      console.log('[Test] Page content:', content);
    }

    // 6. Verify header and status
    const header = page.locator('h1');
    await expect(header).toBeVisible({ timeout: 15000 });
    await expect(header).toContainText(SEEDED_RUN_NAME);

    const statusChip = page.getByTestId('run-status');
    await expect(statusChip).toBeVisible({ timeout: 15000 });
    await expect(statusChip).toContainText(/COMPLETED/i);

    // 7. Verify timeline and major components
    await expect(page.locator('.timeline-container')).toBeVisible();

    // 8. Verify parameters
    await monitorPage.verifyParameter('Output Directory', '/tmp/output');

    // 9. Verify state history timeline (Operation Timeline)
    await expect(page.locator('.operation-item')).toHaveCount(1, { timeout: 15000 });
    await expect(page.locator('.operation-item')).toContainText('pick_up_tips');
  });
});

test.describe('Monitor Detail Error Handling', () => {
  test('displays error for invalid run ID format', async ({ page }) => {
    await page.goto('/app/monitor/invalid-run-id?mode=browser');
    await expect(page.getByText('Run not found')).toBeVisible({ timeout: 20000 });
  });

  test('displays error for non-existent UUID', async ({ page }) => {
    const fakeUUID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';
    await page.goto(`/app/monitor/${fakeUUID}?mode=browser`);
    await expect(page.getByText('Run not found')).toBeVisible({ timeout: 20000 });
  });

  test('handles empty run history gracefully', async ({ page }) => {
    await page.goto('/app/monitor?mode=browser&resetdb=1');
    await expect(page.locator('p', { hasText: /No runs|No executions|Empty/i })).toBeVisible({ timeout: 20000 });
  });
});
