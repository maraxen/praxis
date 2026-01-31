import { test, expect } from '../fixtures/app.fixture';
import { ExecutionMonitorPage } from '../page-objects/monitor.page';

// TODO: Main tests require full protocol execution in beforeAll which times out (>60s)
// The beforeAll runs: splash screen → protocol selection → machine config → deck setup → start execution
// This is too heavy for E2E test setup. Consider using seeded run data instead.
test.describe.skip('Run Detail View (requires protocol execution)', () => {
  let monitorPage: ExecutionMonitorPage;

  test.beforeAll(async ({ browser }, testInfo) => {
    // This setup takes >60s and causes timeouts
    const { WelcomePage } = await import('../page-objects/welcome.page');
    const { ProtocolPage } = await import('../page-objects/protocol.page');
    const { WizardPage } = await import('../page-objects/wizard.page');

    const page = await browser.newPage();
    const welcomePage = new WelcomePage(page);
    await welcomePage.goto(testInfo);
    await welcomePage.handleSplashScreen();

    const protocolPage = new ProtocolPage(page);
    await protocolPage.goto(testInfo);
    await protocolPage.selectProtocolByName('Kinetic Assay');
    await protocolPage.continueFromSelection();

    const wizardPage = new WizardPage(page);
    await wizardPage.selectFirstCompatibleMachine();
    await wizardPage.waitForAssetsAutoConfigured();
    await wizardPage.advanceDeckSetup();
    await wizardPage.openReviewStep();
    await wizardPage.startExecution();
    await page.close();
  });

  test.beforeEach(async ({ page }) => {
    monitorPage = new ExecutionMonitorPage(page);
  });

  test.afterEach(async ({ page }) => {
    await page.keyboard.press('Escape').catch(() => { });
  });

  test('navigates to the run detail page', async ({ page }) => {
    await monitorPage.navigateToHistory();

    const firstRow = monitorPage.historyTable.locator('tbody tr').first();
    await expect(firstRow).toBeVisible({ timeout: 10000 });

    const runName = await firstRow.locator('td').first().textContent();

    await monitorPage.openRunDetail(runName || '');

    await monitorPage.expectRunDetailVisible(runName || '');
  });

  test('navigates to the run detail page and verifies data', async ({ page }) => {
    await monitorPage.navigateToHistory();

    const firstRow = monitorPage.historyTable.locator('tbody tr').first();
    await expect(firstRow).toBeVisible();

    const expectedName = await firstRow.locator('td:nth-child(1)').textContent();
    const expectedStatus = await firstRow.locator('td:nth-child(3)').textContent();

    await firstRow.click();
    await page.waitForURL(/\/app\/monitor\/.+$/);

    await expect(page.locator('h1')).toContainText(expectedName!);
    await expect(page.getByTestId('run-status')).toContainText(expectedStatus!);

    await expect(page.locator('.timeline-container')).toBeVisible();

    await expect(page.getByTestId('log-panel')).toBeVisible();
  });

  test('displays run parameters correctly', async ({ page }) => {
    await monitorPage.navigateToHistory();
    const firstRow = monitorPage.historyTable.locator('tbody tr').first();
    await expect(firstRow).toBeVisible();
    const runName = await firstRow.locator('td').first().textContent();
    await monitorPage.openRunDetail(runName || '');

    await monitorPage.verifyParameter('Output Directory', '/tmp/output');
  });
});

// Error handling tests work standalone without beforeAll
test.describe('Monitor Detail Error Handling', () => {
  test('displays error for invalid run ID format', async ({ page }) => {
    await page.goto('/app/monitor/invalid-run-id?mode=browser');
    await expect(page.getByText('Run not found')).toBeVisible({ timeout: 15000 });
  });

  test('displays error for non-existent UUID', async ({ page }) => {
    const fakeUUID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';
    await page.goto(`/app/monitor/${fakeUUID}?mode=browser`);
    await expect(page.getByText('Run not found')).toBeVisible({ timeout: 15000 });
  });

  test('handles empty run history gracefully', async ({ page }) => {
    // Navigate with reset DB to ensure empty state
    await page.goto('/app/monitor?mode=browser&resetdb=1');
    await expect(page.getByText(/No runs|No executions|Empty/i)).toBeVisible({ timeout: 15000 });
  });
});

