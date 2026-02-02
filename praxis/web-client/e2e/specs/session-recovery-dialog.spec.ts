/**
 * Session Recovery Dialog E2E Tests
 * 
 * TDD Approach: These tests are written FIRST, before implementation.
 * They should initially FAIL, proving the feature is not yet implemented.
 * 
 * The dialog should appear when:
 * - A protocol run has status 'running', 'pausing', or 'resuming'
 * - AND the lastHeartbeat in properties_json is stale (>30s old)
 */
import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';

test.describe('Session Recovery Dialog', () => {

    test('shows recovery dialog when orphaned run exists', async ({ page, workerIndex }) => {
        // Seed an orphaned run via localStorage injection before navigation
        // The app checks for orphaned runs on init, so we need to seed before goto
        const staleHeartbeat = Date.now() - 60000; // 60 seconds ago (stale)

        // Navigate with resetdb to start fresh
        await gotoWithWorkerDb(page, '/app/home', { workerIndex }, { resetdb: true });

        // Seed orphaned run directly via browser context
        await page.evaluate(async (heartbeat) => {
            const service = (window as any).sqliteService;
            if (!service) throw new Error('sqliteService not exposed');

            // Wait for protocolRuns repository
            const repoPromise = new Promise((resolve) => {
                service.protocolRuns.subscribe((repo: any) => {
                    if (repo) resolve(repo);
                });
            });
            const repo = await repoPromise as any;

            // Insert orphaned run with stale heartbeat
            await repo.insert({
                accession_id: 'orphaned-run-e2e-1',
                name: 'Test Protocol Run',
                status: 'running',
                properties_json: { lastHeartbeat: heartbeat },
                top_level_protocol_definition_accession_id: 'test-protocol-def'
            });
        }, staleHeartbeat);

        // Reload to trigger session recovery check
        await page.reload({ waitUntil: 'domcontentloaded' });

        // Wait for SQLite ready again
        await page.waitForFunction(() => {
            const service = (window as any).sqliteService;
            return typeof service?.isReady === 'function' && service.isReady() === true;
        }, null, { timeout: 10000 });

        // Verify dialog appears
        const dialog = page.getByRole('dialog');
        await expect(dialog).toBeVisible({ timeout: 5000 });
        await expect(page.getByText(/Protocol.*interrupted|interrupted/i)).toBeVisible();

        // Verify action buttons
        await expect(page.getByRole('button', { name: /Mark.*Failed/i })).toBeVisible();
        await expect(page.getByRole('button', { name: /Dismiss/i })).toBeVisible();
    });

    test('marks run as failed when button clicked', async ({ page, workerIndex }) => {
        const staleHeartbeat = Date.now() - 60000;

        // Navigate with resetdb
        await gotoWithWorkerDb(page, '/app/home', { workerIndex }, { resetdb: true });

        // Seed orphaned run
        await page.evaluate(async (heartbeat) => {
            const service = (window as any).sqliteService;
            if (!service) throw new Error('sqliteService not exposed');

            const repoPromise = new Promise((resolve) => {
                service.protocolRuns.subscribe((repo: any) => {
                    if (repo) resolve(repo);
                });
            });
            const repo = await repoPromise as any;

            await repo.insert({
                accession_id: 'orphaned-run-e2e-2',
                name: 'Test Protocol Run 2',
                status: 'running',
                properties_json: { lastHeartbeat: heartbeat },
                top_level_protocol_definition_accession_id: 'test-protocol-def'
            });
        }, staleHeartbeat);

        // Reload to trigger session recovery
        await page.reload({ waitUntil: 'domcontentloaded' });

        await page.waitForFunction(() => {
            const service = (window as any).sqliteService;
            return typeof service?.isReady === 'function' && service.isReady() === true;
        }, null, { timeout: 10000 });

        // Wait for dialog and click Mark as Failed
        const dialog = page.getByRole('dialog');
        await expect(dialog).toBeVisible({ timeout: 5000 });

        await page.getByRole('button', { name: /Mark.*Failed/i }).click();

        // Dialog should close
        await expect(dialog).not.toBeVisible({ timeout: 3000 });

        // Verify run status updated in database
        const status = await page.evaluate(async () => {
            const service = (window as any).sqliteService;
            const repoPromise = new Promise((resolve) => {
                service.protocolRuns.subscribe((repo: any) => {
                    if (repo) resolve(repo);
                });
            });
            const repo = await repoPromise as any;
            const run = await repo.findById('orphaned-run-e2e-2');
            return run?.status;
        });

        expect(status).toBe('failed');
    });

    test('dismiss closes dialog without changing status', async ({ page, workerIndex }) => {
        const staleHeartbeat = Date.now() - 60000;

        await gotoWithWorkerDb(page, '/app/home', { workerIndex }, { resetdb: true });

        // Seed orphaned run
        await page.evaluate(async (heartbeat) => {
            const service = (window as any).sqliteService;
            if (!service) throw new Error('sqliteService not exposed');

            const repoPromise = new Promise((resolve) => {
                service.protocolRuns.subscribe((repo: any) => {
                    if (repo) resolve(repo);
                });
            });
            const repo = await repoPromise as any;

            await repo.insert({
                accession_id: 'orphaned-run-e2e-3',
                name: 'Test Protocol Run 3',
                status: 'running',
                properties_json: { lastHeartbeat: heartbeat },
                top_level_protocol_definition_accession_id: 'test-protocol-def'
            });
        }, staleHeartbeat);

        await page.reload({ waitUntil: 'domcontentloaded' });

        await page.waitForFunction(() => {
            const service = (window as any).sqliteService;
            return typeof service?.isReady === 'function' && service.isReady() === true;
        }, null, { timeout: 10000 });

        const dialog = page.getByRole('dialog');
        await expect(dialog).toBeVisible({ timeout: 5000 });

        // Click Dismiss
        await page.getByRole('button', { name: /Dismiss/i }).click();

        // Dialog should close
        await expect(dialog).not.toBeVisible({ timeout: 3000 });

        // Status should still be 'running' (not changed)
        const status = await page.evaluate(async () => {
            const service = (window as any).sqliteService;
            const repoPromise = new Promise((resolve) => {
                service.protocolRuns.subscribe((repo: any) => {
                    if (repo) resolve(repo);
                });
            });
            const repo = await repoPromise as any;
            const run = await repo.findById('orphaned-run-e2e-3');
            return run?.status;
        });

        expect(status).toBe('running');
    });

    test('does not show dialog when no orphaned runs', async ({ page, workerIndex }) => {
        // Navigate with resetdb for clean state - no orphaned runs
        await gotoWithWorkerDb(page, '/app/home', { workerIndex }, { resetdb: true });

        // Short wait to ensure dialog would have appeared if it was going to
        await page.waitForTimeout(2000);

        // Dialog should NOT be visible
        const dialog = page.getByRole('dialog');
        await expect(dialog).not.toBeVisible({ timeout: 1000 });
    });
});
