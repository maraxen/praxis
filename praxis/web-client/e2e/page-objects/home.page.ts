import { expect, Page, TestInfo } from '@playwright/test';
import { BasePage } from './base.page';

export class HomePage extends BasePage {
    constructor(page: Page, testInfo?: TestInfo) {
        super(page, '/app/home', testInfo);
    }

    readonly recentActivityPlaceholder = this.page.getByText('No recent activity');

    async assertNoRecentActivity() {
        await expect(this.recentActivityPlaceholder).toBeVisible();
    }
}
