import { test, expect } from '../fixtures/workcell.fixture';
import { WorkcellPage } from '../page-objects/workcell.page';
import { WelcomePage } from '../page-objects/welcome.page';
import { buildWorkerUrl } from '../fixtures/worker-db.fixture';

test.describe('Workcell Dashboard - Empty State', () => {
    let workcellPage: WorkcellPage;

    test.beforeEach(async ({ page }, testInfo) => {
        workcellPage = new WorkcellPage(page, testInfo);
        await workcellPage.goto(testInfo);
        const welcomePage = new WelcomePage(page, testInfo);
    });

    test('should load the dashboard page and display empty state', async () => {
        await workcellPage.waitForLoad();
        await expect(workcellPage.emptyStateMessage).toBeVisible();
    });
});

test.describe('Workcell Dashboard - Populated State', () => {
    let workcellPage: WorkcellPage;

    test.beforeEach(async ({ page, testMachineData }, testInfo) => {
        workcellPage = new WorkcellPage(page, testInfo);

        // 1. Navigate to the page and wait for DB initialization
        const url = buildWorkerUrl('/app/workcell', testInfo.workerIndex, { resetdb: false });
        await page.goto(url, { waitUntil: 'networkidle' });

        // Wait for __e2e to be available
        await page.waitForFunction(() => (window as any).__e2e, { timeout: 10000 });
        const welcomePage = new WelcomePage(page, testInfo);

        // 2. Seed the machine data using __e2e API
        await page.evaluate(async (machine) => {
            const e2e = (window as any).__e2e;
            if (!e2e) throw new Error('__e2e API not found');

            // Clean up any existing machines from previous tests in the same worker session
            await e2e.exec("DELETE FROM machines");

            await e2e.exec(
                `INSERT INTO machines (accession_id, name, machine_category, status, fqn, asset_type, location, maintenance_enabled, maintenance_schedule_json, is_simulation_override, serial_number, properties_json)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [machine.id, machine.name, 'LiquidHandler', 'IDLE', 'pylabrobot.hamilton.STAR', 'MACHINE', 'Bench 1', 0, JSON.stringify({ intervals: [], enabled: false }), 0, 'SN-E2E', '{}']
            );
        }, testMachineData);

        // 3. Reload to pick up seeded data
        await page.reload({ waitUntil: 'networkidle' });
        await page.waitForTimeout(1000); // Small buffer for worker sync
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
