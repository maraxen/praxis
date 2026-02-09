import { test, expect } from '../../fixtures/worker-db.fixture';
import { WelcomePage } from '../../page-objects/welcome.page';
import { ExecutionMonitorPage } from '../../page-objects/monitor.page';
import { launchSimulatedExecution } from '../../helpers/wizard.helper';

/**
 * Interaction tests for execution controls (Pause, Resume, Abort).
 */
test.describe('Execution Controls Interaction', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        const welcomePage = new WelcomePage(page, testInfo);
        await welcomePage.goto();
    });

    test.afterEach(async ({ page }) => {
        // Force abort any running execution to prevent state leakage
        const abortBtn = page.getByRole('button', { name: /stop|abort/i });
        if (await abortBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
            await abortBtn.click();
            const confirmBtn = page.getByRole('button', { name: /confirm|yes/i });
            if (await confirmBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
                await confirmBtn.click();
            }
        }
    });

    test('should pause and resume a simulated run', async ({ page }, testInfo) => {
        const monitorPage = new ExecutionMonitorPage(page, testInfo);

        // 1. Prepare and launch execution
        await launchSimulatedExecution(page, testInfo);
        await monitorPage.waitForLiveDashboard();
        
        // 2. Click Pause
        const pauseBtn = page.getByRole('button', { name: /pause/i }).first();
        await expect(pauseBtn).toBeVisible({ timeout: 15000 });

        // Capture progress before pause
        const progressBefore = await page.locator('mat-progress-bar').getAttribute('aria-valuenow');
        await pauseBtn.click();
        await expect(pauseBtn).toBeHidden({ timeout: 5000 });

        // 3. Verify status changes to PAUSED
        await monitorPage.waitForStatus(/PAUSED/);
        
        // 4. Click Resume
        const resumeBtn = page.getByRole('button', { name: /resume/i }).first();
        await expect(resumeBtn).toBeVisible({ timeout: 15000 });
        await resumeBtn.click();
        await expect(resumeBtn).toBeHidden({ timeout: 5000 });

        // 5. Verify status returns to RUNNING or progresses to COMPLETED
        await monitorPage.waitForStatus(/RUNNING|COMPLETED/);

        // Verify progress maintained or advanced
        const progressAfter = await page.locator('mat-progress-bar').getAttribute('aria-valuenow');
        expect(Number(progressAfter)).toBeGreaterThanOrEqual(Number(progressBefore));
    });

    test('should abort a simulated run', async ({ page }, testInfo) => {
        const monitorPage = new ExecutionMonitorPage(page, testInfo);

        // 1. Prepare and launch execution
        await launchSimulatedExecution(page, testInfo);
        await monitorPage.waitForLiveDashboard();
        const { runName } = await monitorPage.captureRunMeta();
        
        // 2. Click Abort/Stop
        const abortBtn = page.getByRole('button', { name: /stop|abort|cancel/i }).first();
        await expect(abortBtn).toBeVisible({ timeout: 15000 });
        await abortBtn.click();

        // 3. Handle confirmation if any
        const confirmBtn = page.getByRole('button', { name: /confirm|yes|abort/i }).first();
        if (await confirmBtn.isVisible({ timeout: 2000 })) {
            await confirmBtn.click();
        }

        // 4. Verify status changes to CANCELLED/FAILED
        await monitorPage.waitForStatus(/CANCELLED|FAILED/);

        // 5. Verify run appears in history with correct status
        await monitorPage.navigateToHistory();
        const row = await monitorPage.waitForHistoryRow(runName);
        await expect(row).toContainText(/CANCELLED|ABORTED/i);
    });

    test('should continue running when abort is cancelled', async ({ page }, testInfo) => {
        const monitorPage = new ExecutionMonitorPage(page, testInfo);

        await launchSimulatedExecution(page, testInfo);
        await monitorPage.waitForLiveDashboard();

        const abortBtn = page.getByRole('button', { name: /stop|abort/i });
        await abortBtn.click();
        
        const cancelBtn = page.getByRole('button', { name: /cancel|no|nevermind/i });
        await cancelBtn.click();
        
        await monitorPage.waitForStatus(/RUNNING/);
    });

    test('should allow abort while paused', async ({ page }, testInfo) => {
        const monitorPage = new ExecutionMonitorPage(page, testInfo);

        await launchSimulatedExecution(page, testInfo);
        await monitorPage.waitForLiveDashboard();

        const pauseBtn = page.getByRole('button', { name: /pause/i }).first();
        await pauseBtn.click();
        await monitorPage.waitForStatus(/PAUSED/);

        const abortBtn = page.getByRole('button', { name: /stop|abort/i });
        await abortBtn.click();
        
        const confirmBtn = page.getByRole('button', { name: /confirm|yes|abort/i }).first();
        if (await confirmBtn.isVisible({ timeout: 2000 })) {
            await confirmBtn.click();
        }

        await monitorPage.waitForStatus(/CANCELLED|FAILED/);
    });
});
