import { test, expect, buildIsolatedUrl, waitForDbReady } from '../fixtures/app.fixture';
import { ExecutionMonitorPage } from '../page-objects/monitor.page';

/**
 * Seeding helper to inject a fake protocol run directly into the browser SQLite DB.
 */
async function seedFakeRun(page: any, runId: string, runName: string, status = 'COMPLETED') {
  console.log(`[Seeding] Starting for run ${runId}...`);
  const result = await page.evaluate(async ({ id, name, runStatus }: { id: string; name: string; runStatus: string }) => {
    const sqlite = (window as any).sqliteService;
    if (!sqlite) throw new Error('sqliteService not found on window');

    // 1. Get Repositories
    const repos = await new Promise<any>((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Timeout getting repositories')), 20000);
      sqlite.getAsyncRepositories().subscribe({
        next: (r: any) => {
          clearTimeout(timeout);
          resolve(r);
        },
        error: (err: any) => {
          clearTimeout(timeout);
          reject(err);
        }
      });
    });

    // 2. Ensure Protocol exists
    const protocols = await new Promise<any[]>(resolve => {
      repos.protocolDefinitions.findAll().subscribe({
        next: (p: any) => resolve(p || []),
        error: () => resolve([])
      });
    });
    let protocol = protocols.find((p: any) => p.name === 'Kinetic Assay');

    if (!protocol) {
      console.log('[Seeding] Protocol not found, creating dummy...');
      protocol = await new Promise<any>(resolve => {
        repos.protocolDefinitions.create({
          accession_id: 'proto-kinetic-assay',
          name: 'Kinetic Assay',
          fqn: 'pylabrobot.protocols.kinetic_assay',
          version: '1.0.0',
          description: 'Seeded for E2E testing',
          source_file_path: 'kinetic_assay.py',
          module_name: 'kinetic_assay',
          function_name: 'run',
          is_top_level: 1,
          solo_execution: 1,
          preconfigure_deck: 1,
          requires_deck: 1,
          deprecated: 0
        }).subscribe((p: any) => resolve(p));
      });
    }

    // 3. Create the protocol run
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

    console.log('[Seeding] Creating run record...');
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Timeout creating run')), 10000);
      repos.protocolRuns.create({
        accession_id: id,
        protocol_definition_accession_id: protocol.accession_id,
        top_level_protocol_definition_accession_id: protocol.accession_id,
        name: name,
        status: runStatus,
        created_at: new Date().toISOString(),
        start_time: new Date().toISOString(),
        end_time: runStatus === 'COMPLETED' ? new Date().toISOString() : null,
        input_parameters_json: { "Output Directory": "/tmp/output", "Volume": 50 },
        properties_json: {
          notes: "Seeded for E2E testing",
          simulation_mode: true,
          state_history: stateHistory
        },
        resolved_assets_json: []
      }).subscribe({
        next: () => {
          clearTimeout(timeout);
          resolve();
        },
        error: (err: any) => {
          clearTimeout(timeout);
          reject(err);
        }
      });
    });

    return { success: true };
  }, { id: runId, name: runName, runStatus: status });
  console.log('[Seeding] Completed:', result);
}

test.describe('Run Detail View (using seeded data)', () => {
  let monitorPage: ExecutionMonitorPage;
  const SEEDED_RUN_ID = 'e2e00000000000000000000000000001';
  const SEEDED_RUN_NAME = 'Seeded Kinetic Assay';

  test.beforeEach(async ({ page }) => {
    monitorPage = new ExecutionMonitorPage(page);
  });

  test.afterEach(async ({ page }) => {
    await page.keyboard.press('Escape').catch(() => { });
  });

  test('verifies seeded run details', async ({ page }) => {
    page.on('console', msg => console.log(`[Browser] ${msg.type()}: ${msg.text()}`));

    // 1. Navigate to monitor page first to get DB context
    await page.goto('/app/monitor?mode=browser');
    await waitForDbReady(page, 30000);

    // 2. Seed data
    await seedFakeRun(page, SEEDED_RUN_ID, SEEDED_RUN_NAME);

    // 3. Reload to pick up seeded data
    console.log('[Test] Reloading page...');
    await page.reload();
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
