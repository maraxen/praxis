import { test, expect } from '../fixtures/workcell.fixture';
import { WorkcellPage } from '../page-objects/workcell.page';
import { WelcomePage } from '../page-objects/welcome.page';
import { buildWorkerUrl } from '../fixtures/worker-db.fixture';

test.describe('Workcell Dashboard - Empty State', () => {
    let workcellPage: WorkcellPage;

    test.beforeEach(async ({ page }, testInfo) => {
        workcellPage = new WorkcellPage(page);
        await workcellPage.goto(testInfo);
        const welcomePage = new WelcomePage(page);
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

        // 1. Navigate to the page with resetdb=1 to start clean
        const url = buildWorkerUrl('/app/workcell', testInfo.workerIndex, { resetdb: true });
        await page.goto(url, { waitUntil: 'networkidle' });
        const welcomePage = new WelcomePage(page);

        // 2. Seed the machine data using the real SqliteService and refresh UI
        await page.evaluate(async (machine) => {
            const service = (window as any).sqliteService;
            if (!service) throw new Error('SqliteService not found');

            const firstValue = <T>(obs: any): Promise<T> => new Promise((resolve, reject) => {
                const sub = obs.subscribe({
                    next: (val: T) => { resolve(val); sub.unsubscribe(); },
                    error: (err: any) => { reject(err); sub.unsubscribe(); }
                });
            });

            const repos = await firstValue<any>(service.getAsyncRepositories());

            // Clean up any existing machines from previous tests in the same worker session
            await (window as any).__e2e.exec("DELETE FROM machines");

            await firstValue(repos.machines.create({
                accession_id: machine.id,
                name: machine.name,
                machine_category: 'LiquidHandler',
                status: 'IDLE',
                fqn: 'pylabrobot.hamilton.STAR',
                asset_type: 'MACHINE',
                location: 'Bench 1',
                maintenance_enabled: 0,
                maintenance_schedule_json: JSON.stringify({ intervals: [], enabled: false }),
                is_simulation_override: 0,
                serial_number: 'SN-E2E',
                properties_json: '{}'
            }));

            // Refresh UI via the exposed dashboard component
            const dashboard = (window as any).dashboard;
            if (dashboard && dashboard.viewService) {
                await firstValue(dashboard.viewService.loadWorkcellGroups());
            }
        }, testMachineData);
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
