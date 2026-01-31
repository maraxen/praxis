
import { Locator, Page, expect, TestInfo } from '@playwright/test';
import { BasePage } from './base.page';
import { buildWorkerUrl } from '../fixtures/worker-db.fixture';
import { waitForContentReady, waitForComponentLoaded } from '../helpers/wait-for-content';

export class WorkcellPage extends BasePage {
    readonly heading: Locator;
    readonly explorer: Locator;
    readonly searchInput: Locator;
    readonly machineCards: Locator;
    readonly emptyStateMessage: Locator;
    readonly focusView: Locator;

    constructor(page: Page) {
        super(page);
        this.heading = page.getByRole('heading', { name: /Workcell Dashboard/i });
        this.explorer = page.locator('app-workcell-explorer');
        this.searchInput = page.getByRole('searchbox').or(page.locator('app-workcell-explorer input[type="text"]'));
        this.machineCards = page.locator('app-machine-card');
        this.emptyStateMessage = page.getByText(/No machines found/i);
        this.focusView = page.locator('app-machine-focus-view');
    }

    async goto(testInfo: TestInfo) {
        const url = buildWorkerUrl('/app/workcell', testInfo.workerIndex);
        await this.page.goto(url, { waitUntil: 'networkidle' });
        
        // Wait for content to be fully loaded (handles Angular lazy loading timing)
        await waitForContentReady(this.page, {
            contentSelector: 'app-workcell-dashboard',
            timeout: 15000
        });
    }

    async waitForLoad() {
        // Wait for component to finish loading (spinner disappears)
        await waitForComponentLoaded(this.page, 'app-workcell-dashboard', { timeout: 15000 });
        await expect(this.heading).toBeVisible({ timeout: 15000 });
    }

    async selectMachine(index = 0) {
        await this.machineCards.nth(index).click();
        await expect(this.focusView).toBeVisible({ timeout: 10000 });
    }

    async searchMachines(query: string) {
        await this.searchInput.fill(query);
    }
}
