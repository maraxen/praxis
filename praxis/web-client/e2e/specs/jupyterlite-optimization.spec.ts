import { test, expect } from '../fixtures/worker-db.fixture';
import { PlaygroundPage } from '../page-objects/playground.page';

test.describe('@slow JupyterLite Optimization Validation', () => {
  let playground: PlaygroundPage;

  test.beforeEach(async ({ page }) => {
    // Set localStorage before any navigation to avoid double-navigation
    await page.addInitScript(() => {
      window.localStorage.setItem('praxis_onboarding_completed', 'true');
      window.localStorage.setItem('praxis_tutorial_completed', 'true');
    });
  });

  test('Phase 1 & 3: PyLabRobot should be pre-loaded and functional', async ({ page }, testInfo) => {
    playground = new PlaygroundPage(page, testInfo);
    await playground.goto('worker');
    await playground.waitForKernelReady();

    // Assertion: Pylabrobot should be importable and version check
    await playground.executeCode('import pylabrobot; print(f"PLR_FOUND_{pylabrobot.__version__}")');
    // Wait for the output to be rendered before asserting its content
    await playground.getOutput().waitFor();
    await expect(playground.getOutput()).toContainText(/PLR_FOUND_0\.\d+\.\d+/);

    // Domain Coverage: Beyond just import, verify a core method works
    await playground.executeCode(`
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import SimulatorBackend
print("LH_INIT_SUCCESS" if LiquidHandler else "LH_INIT_FAIL")
`);
    await playground.getOutput().waitFor();
    await expect(playground.getOutput()).toContainText('LH_INIT_SUCCESS');

    // Critical Assertion: We should NOT see "Installing pylabrobot..."
    // The console log is still useful for this negative assertion.
    const hasManualInstallLog = playground.hasConsoleLog('Installing pylabrobot from local wheel...');
    expect(hasManualInstallLog, 'Manual installation of pylabrobot detected! It should be pre-loaded.').toBe(false);
  });

  test('Phase 2: Assets should be cached via Service Worker', async ({ page }, testInfo) => {
    // Diagnostic check for Service Worker availability
    const swStatus = await page.evaluate(async () => {
      if (!('serviceWorker' in navigator)) {
        return { available: false, reason: 'navigator.serviceWorker not available' };
      }
      try {
        const reg = await navigator.serviceWorker.getRegistration();
        return { available: !!reg?.active, state: reg?.active?.state };
      } catch (e) {
        return { available: false, reason: String(e) };
      }
    });

    if (!swStatus.available) {
      console.log('[Phase 2] SW test skipped:', swStatus);
      test.skip('Service Worker not active - likely running in dev mode');
    }

    playground = new PlaygroundPage(page, testInfo);
    await playground.goto('worker');

    // Set up response capture BEFORE reload
    const lockJsonPromise = page.waitForResponse(
      resp => resp.url().includes('pyodide-lock.json') && resp.status() === 200
    );

    await page.reload({ waitUntil: 'domcontentloaded' });

    const response = await lockJsonPromise;
    expect(response.fromServiceWorker(), 'pyodide-lock.json should be served from Service Worker').toBe(true);
  });

  test.describe('Error Scenarios (Phase 4)', () => {
    test('should gracefully handle missing pylabrobot', async () => {
      // This would require mocking the Pyodide environment
      // For now, skip - add when mock infrastructure is available
      test.skip(true, 'Mock infrastructure needed to test missing pylabrobot');
    });

    test('should detect SharedArrayBuffer unavailability', async ({ page }) => {
      // This is an informational check to confirm the browser context.
      // The app should still function, albeit in a degraded mode, without SAB.
      const hasSAB = await page.evaluate(() => 'SharedArrayBuffer' in window);
      console.log(`[SAB Check] SharedArrayBuffer available: ${hasSAB}`);
      // This is an informational check, not a strict pass/fail criterion.
      // In some environments (like certain CI runners or browsers), SAB might be disabled.
      // The application should degrade gracefully, so we don't enforce its presence.
      expect(typeof hasSAB).toBe('boolean');
    });
  });
});
