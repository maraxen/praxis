/**
 * Execution Browser E2E Tests
 *
 * Tests verify run history persistence across navigation in browser mode.
 * Depends on SqliteService sessionStorage fallback for dbName persistence
 * across full page reloads (page.goto without query params).
 */
import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { ProtocolPage } from '../page-objects/protocol.page';
import { WizardPage } from '../page-objects/wizard.page';
import { ExecutionMonitorPage } from '../page-objects/monitor.page';

test.describe('Execution Browser (Modern)', () => {
  test.setTimeout(180000);

  test('should execute a protocol and record it in history', async ({ page }, testInfo) => {
    await gotoWithWorkerDb(page, '/app/home', testInfo, { resetdb: true, timeout: 60000 });

    const protocolPage = new ProtocolPage(page, testInfo);
    const wizardPage = new WizardPage(page, testInfo);
    const monitorPage = new ExecutionMonitorPage(page, testInfo);

    await protocolPage.goto();
    await protocolPage.ensureSimulationMode();
    const protocolName = await protocolPage.selectProtocol('Simple Transfer');
    await wizardPage.completeParameterStep();
    await wizardPage.selectFirstCompatibleMachine();
    await wizardPage.waitForAssetsAutoConfigured();
    await wizardPage.completeWellSelectionStep();
    await wizardPage.advanceDeckSetup();
    await wizardPage.openReviewStep();
    await wizardPage.startExecution();

    await expect(page).toHaveURL(/\/app\/monitor\/[a-f0-9-]+/, { timeout: 15000 });
    // Wait for execution to at least start persisting
    await page.waitForTimeout(3000);

    // Navigate to history — sessionStorage preserves dbName across reload
    await monitorPage.navigateToHistory();

    // Retry: the history table queries OPFS which is async
    await expect(async () => {
      const rows = page.locator('app-run-history-table tr').filter({ hasText: protocolName });
      const count = await rows.count();
      if (count === 0) {
        // Reload the page to re-trigger loadRuns()
        await page.reload({ waitUntil: 'domcontentloaded' });
        throw new Error('Row not yet visible');
      }
    }).toPass({ timeout: 30000, intervals: [2000, 3000, 5000] });

    const row = page.locator('app-run-history-table tr').filter({ hasText: protocolName }).first();
    await expect(row).toBeVisible();
  });

  test('should display seeded execution history correctly', async ({ page }, testInfo) => {
    await gotoWithWorkerDb(page, '/app/home', testInfo, { resetdb: true, timeout: 60000 });

    // Seed a completed run via __e2e API
    await page.evaluate(async () => {
      const e2e = (window as any).__e2e;
      if (!e2e) throw new Error('__e2e test API not found');

      const protos = await e2e.query("SELECT accession_id FROM function_protocol_definitions LIMIT 1");
      const protoId = protos[0]?.accession_id;
      if (!protoId) throw new Error('No protocols found');

      const now = new Date().toISOString();
      const hourAgo = new Date(Date.now() - 3600000).toISOString();

      await e2e.exec(
        `INSERT OR REPLACE INTO protocol_runs 
         (accession_id, top_level_protocol_definition_accession_id, status, name, start_time, end_time, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        ['run-completed-001', protoId, 'completed', 'Completed Protocol', hourAgo, now, hourAgo, now]
      );
    });

    // Navigate to history — sessionStorage preserves dbName across reload
    const monitorPage = new ExecutionMonitorPage(page, testInfo);
    await monitorPage.navigateToHistory();

    // Retry: OPFS query is async, may need a reload
    await expect(async () => {
      const rows = page.locator('app-run-history-table tr').filter({ hasText: /Completed Protocol/i });
      const count = await rows.count();
      if (count === 0) {
        await page.reload({ waitUntil: 'domcontentloaded' });
        throw new Error('Seeded row not yet visible');
      }
    }).toPass({ timeout: 30000, intervals: [2000, 3000, 5000] });

    const completedRow = page.locator('app-run-history-table tr').filter({ hasText: /Completed Protocol/i }).first();
    await expect(completedRow).toBeVisible();
    await expect(completedRow).toContainText(/completed/i);

    await completedRow.click();
    await expect(page).toHaveURL(/\/app\/monitor\/.+$/);
    await monitorPage.expectRunDetailVisible('Completed Protocol');
  });
});
