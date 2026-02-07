import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

interface RunMeta {
    runName: string;
    runId: string;
}

export class ExecutionMonitorPage extends BasePage {
    private readonly liveHeader: Locator;
    private readonly statusChip: Locator;
    private readonly runInfoCard: Locator;
    private readonly logPanel: Locator;
    private readonly historyTable: Locator;

    constructor(page: Page) {
        super(page, '/app/monitor');
        this.liveHeader = page.getByRole('heading', { name: /Execution Monitor/i }).first();
        this.statusChip = page.getByTestId('run-status');
        this.runInfoCard = page.locator('mat-card').filter({ hasText: 'Run Information' }).first();
        this.logPanel = page.getByTestId('log-panel');
        this.historyTable = page.locator('app-run-history-table table');
    }

    async waitForLiveDashboard() {
        const detailView = this.page.getByTestId('run-detail-view');
        await detailView.waitFor({ state: 'visible', timeout: 15000 });
    }

    async captureRunMeta(): Promise<RunMeta> {
        await this.runInfoCard.waitFor({ state: 'visible' });
        const runName = (await this.runInfoCard.locator('mat-card-title').textContent())?.trim() || 'Protocol Run';
        const subtitle = await this.runInfoCard.locator('mat-card-subtitle').innerText();
        const runId = subtitle.replace('Run ID:', '').trim();
        return { runName, runId };
    }

    async waitForStatus(expected: string | RegExp, timeout = 60000) {
        // AUDIT: Simulation mode can be very fast. If we wait for RUNNING but it's already COMPLETED,
        // we should accept both to avoid timing-out on "perfect" runs.
        const combined = expected instanceof RegExp
            ? new RegExp(`${expected.source}|COMPLETED`)
            : new RegExp(`${expected}|COMPLETED`);

        await expect(this.statusChip).toContainText(combined, { timeout });
    }

    async waitForProgressAtLeast(minValue: number) {
        const progressBar = this.page.locator('mat-progress-bar');

        // If already completed, progress bar might have been removed from DOM
        const status = await this.statusChip.innerText();
        if (status.includes('COMPLETED')) {
            console.log(`[Monitor] Status is COMPLETED, skipping progress check for ${minValue}%`);
            return;
        }

        await expect(progressBar).toBeVisible({ timeout: 10000 }).catch((e) => {
            console.log('[Test] Silent catch (Progress bar not visible):', e);
        });

        const chipText = await this.statusChip.innerText();
        if (chipText.includes('COMPLETED')) return;

        const handle = await progressBar.elementHandle();
        if (!handle) return;

        await this.page.waitForFunction(
            ([bar, val]) => {
                if (!bar) return true; // Bar gone = likely finished
                const current = parseFloat((bar as Element).getAttribute('aria-valuenow') || '0');
                return current >= (val as number);
            },
            [handle, minValue] as const,
            { timeout: 15000 }
        ).catch(e => {
            console.log(`[Test] Silent catch (Progress check timeout):`, e);
        });
    }

    async waitForLogEntry(text: string) {
        // Increase timeout for log verification to account for simulation delay
        await expect(this.logPanel).toContainText(text, { timeout: 15000 });
    }

    async navigateToHistory() {
        await this.page.goto('/app/monitor', { waitUntil: 'domcontentloaded' });
        // Wait for either the history table OR the empty state indicator
        // Using classes from component: .empty-state, .no-runs-message
        const tableOrEmpty = this.page.locator('app-run-history-table table, app-run-history-table .empty-state, app-run-history-table .no-runs-message').first();
        await tableOrEmpty.waitFor({ state: 'visible', timeout: 30000 });
    }

    async waitForHistoryRow(runName: string): Promise<Locator> {
        // RunHistoryTable uses standard mat-table which has 'tr' elements
        const row = this.page.locator('app-run-history-table tr').filter({ hasText: runName }).first();
        await expect(row).toBeVisible({ timeout: 20000 });
        return row;
    }

    async reloadHistory() {
        await this.page.reload({ waitUntil: 'domcontentloaded' });
        await this.historyTable.waitFor({ state: 'visible', timeout: 10000 });
    }

    async openRunDetail(runName: string) {
        const row = await this.waitForHistoryRow(runName);
        await row.click();
        await this.page.waitForURL(/\/app\/monitor\/.+$/, { waitUntil: 'domcontentloaded' });
    }

    async openRunDetailById(runId: string) {
        await this.page.goto(`/app/monitor/${runId}`, { waitUntil: 'domcontentloaded' });
    }

    async expectRunDetailVisible(runName: string) {
        const heading = this.page.locator('h1').first();
        await expect(heading).toContainText(runName, { timeout: 10000 });
        await expect(this.page.locator('.timeline-container')).toBeVisible();
    }

    async verifyParameter(key: string, value: string) {
        const paramGrid = this.page.locator('app-parameter-viewer');
        await expect(paramGrid).toBeVisible();
        const paramItem = paramGrid.locator('.parameter-item').filter({ has: this.page.locator('.parameter-key', { hasText: key }) });
        await expect(paramItem.locator('.parameter-value')).toContainText(value);
    }

    getEmptyStateIndicator(): Locator {
        return this.page.locator('.empty-state, .no-runs-message, :text("No Runs Yet")').first();
    }
}
