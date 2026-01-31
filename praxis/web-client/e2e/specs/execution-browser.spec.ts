import { test, expect, gotoWithWorkerDb } from '../fixtures/worker-db.fixture';
import { RunProtocolPage } from '../page-objects/run-protocol.page';
import { WelcomePage } from '../page-objects/welcome.page';

test.describe('Browser Mode Execution', () => {
  test('should select a protocol and start execution', async ({ page }, testInfo) => {
    // 1. Initial navigation and setup using the worker-db fixture
    await gotoWithWorkerDb(page, '/', testInfo);

    // 2. Handle the splash screen using the WelcomePage POM
    const welcomePage = new WelcomePage(page);
    await welcomePage.handleSplashScreen();
    await welcomePage.verifyDashboardLoaded();

    // 3. Navigate to the "Run Protocol" page by clicking the sidebar link
    const runLink = page.getByRole('link', { name: 'Run' });
    await expect(runLink).toBeEnabled({ timeout: 10000 });
    await runLink.click();

    const runPage = new RunProtocolPage(page);
    await runPage.waitForProtocolsLoaded();

    // 4. Select the first available protocol
    const selectedProtocolName = await runPage.protocolCards.first().locator('.protocol-name').textContent();
    await runPage.selectFirstProtocol();

    // 5. Verify that the wizard state reflects the selection
    const wizardProtocolName = await page.evaluate(() => {
      const state = (window as any).wizardStateService?.selectedProtocol();
      return state?.name;
    });
    expect(wizardProtocolName).toEqual(selectedProtocolName);

    // 6. Advance through the wizard steps
    // This loop is robust against different wizard lengths.
    for (let i = 0; i < 4; i++) { // Max 4 steps to prevent infinite loops
      if (await runPage.startExecutionButton.isVisible({ timeout: 1000 })) {
        break; // Reached the final "Review & Run" step
      }

      // If the machine selection step is present, select the first machine
      if (await runPage.machineSelection.isVisible({ timeout: 1000 })) {
        await runPage.selectFirstMachine();
      }

      // If we can still continue, advance to the next step
      if (await runPage.continueButton.isEnabled()) {
        await runPage.advanceStep();
      } else {
        break; // Cannot advance, stop trying
      }
    }

    // 6. Start the execution and verify it has begun
    await runPage.startExecution();

    // 7. Verify execution state using a robust async assertion
    await expect(async () => {
      const executionState = await page.evaluate(() => {
        return (window as any).appStore?.executionState();
      });
      expect(executionState).toMatch(/running|initializing/);
    }).toPass({ timeout: 10000 });
  });
});
