import { test, expect } from '../fixtures/worker-db.fixture';
import { SmokePage } from '../page-objects/smoke.page';

test.describe('Smoke Test', () => {
  test('should load the dashboard and display navigation', async ({ page, workerIndex }) => {
    const smoke = new SmokePage(page, workerIndex);
    await smoke.goto('/');
    await smoke.handleSplashScreen();
    await expect(smoke.navRail).toBeVisible({ timeout: 3000 });
    await expect(page).toHaveTitle(/Praxis/);

    // Verify navigation sidebar is visible (icon-based rail nav)
    await expect(page.locator('.sidebar-rail, nav, [role="navigation"]').first()).toBeVisible();
    // Verify dashboard header content
    await expect(page.getByText('Welcome back')).toBeVisible();
    await page.screenshot({ path: '/tmp/e2e-smoke/landing_dashboard.png' });
  });

  test('should navigate to Assets and display tables with data', async ({
    page,
    workerIndex,
  }) => {
    const smoke = new SmokePage(page, workerIndex);
    await smoke.goto('/assets');
    await smoke.handleSplashScreen();
    await expect(smoke.assetsComponent).toBeVisible({ timeout: 3000 });

    // Check for Tabs
    await expect(smoke.machinesTab).toBeVisible();
    await expect(smoke.resourcesTab).toBeVisible();
    await expect(smoke.registryTab).toBeVisible();

    // Check Machine List for data
    await smoke.machinesTab.click();
    await smoke.verifyMachineTableHasData();
    // Mat-Table uses mat-row elements, not tbody tr
    const rowCount = await smoke.machineTable.locator('mat-row, tr.mat-mdc-row, .mat-mdc-row').count();
    expect(rowCount).toBeGreaterThan(0);
    await page.screenshot({ path: '/tmp/e2e-smoke/assets_list.png' });
  });

  test('should navigate to Protocols and display library', async ({
    page,
    workerIndex,
  }) => {
    const smoke = new SmokePage(page, workerIndex);
    await smoke.goto('/protocols');
    await smoke.handleSplashScreen();
    await expect(smoke.protocolLibrary).toBeVisible({ timeout: 3000 });
    // Verify the Protocol Library heading is visible
    await expect(page.getByText('Protocol Library')).toBeVisible();
    // Check for search input as functional indicator
    await expect(page.getByPlaceholder(/Search/i)).toBeVisible();
    await page.screenshot({ path: '/tmp/e2e-smoke/protocol_list.png' });
  });

  test('should navigate to Run Protocol wizard', async ({ page, workerIndex }) => {
    const smoke = new SmokePage(page, workerIndex);
    await smoke.goto('/run');
    await smoke.handleSplashScreen();
    await expect(smoke.runProtocolComponent).toBeVisible({ timeout: 3000 });

    // Check page header
    await expect(page.getByText('Execute Protocol')).toBeVisible();
    // Check for stepper steps text
    await expect(page.getByText('Select Protocol')).toBeVisible();
    await expect(page.getByText('Configure Parameters')).toBeVisible();
    await page.screenshot({ path: '/tmp/e2e-smoke/run_protocol.png' });
  });
});