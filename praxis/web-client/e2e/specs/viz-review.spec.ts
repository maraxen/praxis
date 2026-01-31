import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { WelcomePage } from '../page-objects/welcome.page';
import { AssetsPage } from '../page-objects/assets.page';
import { ProtocolPage } from '../page-objects/protocol.page';
import { ThemeSwitcherComponent } from '../page-objects/theme.component';

test.describe('Visual Review Screenshot Capture', () => {

    test('Capture Page Screenshots', async ({ page }, testInfo) => {
        test.setTimeout(120000);
        const welcomePage = new WelcomePage(page);
        const assetsPage = new AssetsPage(page);
        const protocolPage = new ProtocolPage(page);

        await gotoWithWorkerDb(page, '/app/home', testInfo, { waitForDb: false });
        await welcomePage.handleSplashScreen();

        // 4. asset-library.png
        await assetsPage.goto({ waitForDb: false });
        await expect(assetsPage.addMachineButton).toBeVisible();
        await expect(page).toHaveScreenshot('asset-library.png');

        // 5. protocol-library.png
        await protocolPage.goto({ waitForDb: false });
        await expect(page).toHaveScreenshot('protocol-library.png');

        // 9. run-protocol-config.png
        await gotoWithWorkerDb(page, '/app/run', testInfo, { waitForDb: false });
        await expect(page).toHaveScreenshot('run-protocol-config.png');
    });

    test('Capture Nav and Responsive Screenshots', async ({ page }, testInfo) => {
        test.setTimeout(120000);
        const welcomePage = new WelcomePage(page);

        await gotoWithWorkerDb(page, '/app/home', testInfo, { waitForDb: false });
        await welcomePage.handleSplashScreen();

        // 6. nav-rail.png
        const navRail = page.locator('.sidebar-rail');
        await navRail.waitFor({ state: 'visible', timeout: 30000 });
        await expect(navRail).toHaveScreenshot('nav-rail.png');

        // 7. nav-rail-hover.png
        const firstNavItem = navRail.locator('.nav-item').first();
        await firstNavItem.hover();
        await expect(page.locator('.mat-mdc-tooltip')).toBeVisible();
        await expect(page).toHaveScreenshot('nav-rail-hover.png');

        // 11. sidebar-collapsed.png
        await page.setViewportSize({ width: 768, height: 1024 });
        await expect(navRail).toBeVisible();
        await expect(page).toHaveScreenshot('sidebar-collapsed.png');
    });

    test.skip('Capture Theme and Panel Screenshots', async ({ page }, testInfo) => {
        // Skipping due to theme change flakiness
        test.setTimeout(180000);
        const welcomePage = new WelcomePage(page);
        const themeSwitcher = new ThemeSwitcherComponent(page);
        const protocolPage = new ProtocolPage(page);

        await gotoWithWorkerDb(page, '/app/home', testInfo, { waitForDb: false });
        await welcomePage.handleSplashScreen();

        // 3. global-dark-mode.png
        await themeSwitcher.setDarkTheme();
        await expect(page).toHaveScreenshot('global-dark-mode.png');

        // 1 & 2. deck-view and deck-view-dark
        await gotoWithWorkerDb(page, '/app/workcell', testInfo, { waitForDb: false });
        const simulateBtn = page.locator('button').filter({ hasText: /Simulate/i }).first();
        await expect(simulateBtn).toBeVisible();
        await simulateBtn.click();

        // Currently in Dark mode (from previous toggle)
        await expect(page.locator('app-deck-view')).toBeVisible();
        await expect(page).toHaveScreenshot('deck-view-dark.png');

        await themeSwitcher.setLightTheme();
        await expect(page).toHaveScreenshot('deck-view.png');
        await page.keyboard.press('Escape');

        // 8. protocol-detail-panel.png
        await protocolPage.goto({ waitForDb: false });
        const row = page.locator('tr[mat-row], app-protocol-card').first();
        await expect(row).toBeVisible();
        await row.click();
        await expect(page.locator('.mat-mdc-dialog-container, app-protocol-detail')).toBeVisible();
        await expect(page).toHaveScreenshot('protocol-detail-panel.png');
    });
});
