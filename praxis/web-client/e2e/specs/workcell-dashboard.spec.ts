import { test, expect } from '../fixtures/workcell.fixture';
import { WorkcellPage } from '../page-objects/workcell.page';
import { WelcomePage } from '../page-objects/welcome.page';

test.describe('Workcell Dashboard - Empty State', () => {
    let workcellPage: WorkcellPage;

    test.beforeEach(async ({ page }, testInfo) => {
        workcellPage = new WorkcellPage(page);
        await workcellPage.goto(testInfo);
        const welcomePage = new WelcomePage(page);
        await welcomePage.handleSplashScreen();
    });

    test('should load the dashboard page and display empty state', async () => {
        await workcellPage.waitForLoad();
        await expect(workcellPage.emptyStateMessage).toBeVisible();
    });
});

test.describe('Workcell Dashboard - Populated State', () => {
    let workcellPage: WorkcellPage;

    test.beforeEach(async ({ page, testMachineData }, testInfo) => {
        workcellPage = new WorkcellPage(page);

        await page.addInitScript((machine) => {
            const mockDb = {
                run: async () => ({ changes: 1 }),
                all: async (sql: string) => {
                    if (sql.includes('FROM machines')) {
                        return [{
                            id: machine.id,
                            name: machine.name,
                            type: 'LiquidHandler',
                            backend: 'ChatterBox',
                            is_simulated: 1,
                            disabled: 0
                        }];
                    }
                    return [];
                }
            };

            (window as any).sqliteService = {
                getDatabase: async () => mockDb,
                isReady$: { getValue: () => true }
            };
        }, testMachineData);
        
        await workcellPage.goto(testInfo);
        const welcomePage = new WelcomePage(page);
        await welcomePage.handleSplashScreen();
        await page.reload();
        await welcomePage.handleSplashScreen();
    });

    test('should load the dashboard page and display machine cards', async () => {
        await workcellPage.waitForLoad();
        await expect(workcellPage.machineCards).toHaveCount(1);
    });

    test('should display machine name and type', async ({ page, testMachineData }) => {
        const card = workcellPage.machineCards.first();
        await expect(card).toContainText(testMachineData.name);
        await expect(card).toContainText('Liquid Handler');
    });
    
    test('should switch between view modes', async ({ page }) => {
        const gridBtn = page.getByRole('button', { name: /Grid/i });
        const listBtn = page.getByRole('button', { name: /List/i });
        
        await listBtn.click();
        await expect(page.locator('.list-view')).toBeVisible();
        
        await gridBtn.click();
        await expect(page.locator('.grid-view')).toBeVisible();
    });

    test('should filter machines by search query', async ({ testMachineData }) => {
        await workcellPage.searchMachines('Liquid');
        await expect(workcellPage.machineCards).toHaveCount(1);
        
        await workcellPage.searchMachines('nonexistent');
        await expect(workcellPage.emptyStateMessage).toBeVisible();
    });

    test('should display explorer sidebar', async () => {
        await expect(workcellPage.explorer).toBeVisible({ timeout: 10000 });
        await expect(workcellPage.searchInput).toBeVisible();
    });

    test('should navigate to machine focus view on card click', async () => {
        await workcellPage.selectMachine(0);
        await expect(workcellPage.focusView).toBeVisible();
    });
});
