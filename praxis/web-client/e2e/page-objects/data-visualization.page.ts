// e2e/page-objects/data-visualization.page.ts
import { Page, TestInfo, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { waitForContentReady, waitForComponentLoaded } from '../helpers/wait-for-content';

export class DataVisualizationPage extends BasePage {
    // Locators
    readonly heading: Locator;
    readonly chart: Locator;
    readonly xAxisSelect: Locator;
    readonly yAxisSelect: Locator;
    readonly exportButton: Locator;
    readonly emptyStateMessage: Locator;
    readonly selectedPointInfo: Locator;
    readonly runHistoryTable: Locator;
    readonly wellSelectorButton: Locator;

    constructor(page: Page, testInfo?: TestInfo) {
        super(page, '/app/data', testInfo);

        this.heading = page.getByRole('heading', { level: 1, name: 'Data Visualization' });
        this.chart = page.locator('plotly-plot').first();
        this.xAxisSelect = page.locator('mat-select').first();
        this.yAxisSelect = page.locator('mat-select').nth(1);
        this.exportButton = page.getByRole('button', { name: /export/i });
        this.emptyStateMessage = page.getByText('No data available to display.');
        this.selectedPointInfo = page.locator('.selected-point-info');
        this.runHistoryTable = page.locator('.run-table');
        this.wellSelectorButton = page.locator('.well-filter button').first();
    }

    /**
     * Navigate to the data visualization page and wait for content to load.
     */
    override async goto(options: { waitForDb?: boolean } = {}) {
        await super.goto(options);

        // Wait for content to be fully loaded (handles Angular lazy loading timing)
        await waitForContentReady(this.page, {
            contentSelector: 'app-data-visualization',
            timeout: 15000
        });
    }

    /**
     * Wait for the page component to be fully loaded.
     */
    async waitForLoad() {
        await waitForComponentLoaded(this.page, 'app-data-visualization', { timeout: 15000 });
        await expect(this.heading).toBeVisible({ timeout: 10000 });
    }

    async selectXAxis(option: string) {
        await this.xAxisSelect.click();
        await this.page.getByRole('option', { name: option }).click();
        // Wait for chart to re-render
        await this.waitForChartLoad();
    }

    async waitForChartLoad() {
        // Wait for Plotly to finish rendering (check for plot container with data)
        await this.page.waitForFunction(() => {
            const plotDiv = document.querySelector('.js-plotly-plot');
            return plotDiv && (plotDiv as any).data?.length > 0;
        }, null, { timeout: 10000 });
    }

    async selectRunByIndex(index: number) {
        const rows = this.runHistoryTable.locator('tr[mat-row]');
        await rows.nth(index).click();
        await this.waitForChartLoad();
    }

    async getChartDataPointCount(): Promise<number> {
        return await this.page.evaluate(() => {
            const plotDiv = document.querySelector('.js-plotly-plot') as any;
            return plotDiv?.data?.[0]?.x?.length ?? 0;
        });
    }

    async hasChartData(): Promise<boolean> {
        return (await this.getChartDataPointCount()) > 0;
    }

    async getRunCount(): Promise<number> {
        const rows = this.runHistoryTable.locator('tr[mat-row]');
        return await rows.count();
    }

    async exportAndVerify(): Promise<void> {
        const downloadPromise = this.page.waitForEvent('download');
        await this.exportButton.click();
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toBe('chart.png');
    }
}
