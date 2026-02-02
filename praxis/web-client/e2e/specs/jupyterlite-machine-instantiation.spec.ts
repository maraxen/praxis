
import { test, expect } from '../fixtures/worker-db.fixture';
import { PlaygroundPage } from '../page-objects/playground.page';

test.describe('@slow JupyterLite Machine Instantiation', () => {
  let playground: PlaygroundPage;

  test.beforeEach(async ({ page }, testInfo) => {
    // Set longer timeout for JupyterLite bootstrap
    test.setTimeout(180000);

    // Capture Python errors
    await page.addInitScript(() => {
      (window as any).__pythonErrors = [];
      const originalError = console.error;
      console.error = (...args) => {
        if (args.some(a => String(a).includes('Python') || String(a).includes('Pyodide'))) {
          (window as any).__pythonErrors.push(args.join(' '));
        }
        originalError.apply(console, args);
      };
    });
    
    playground = new PlaygroundPage(page, testInfo);
    await playground.goto();
    await playground.waitForBootstrapComplete();
  });

  test.beforeEach(async ({ page }) => {
    // Common setup for all tests in this suite
    await expect(page.locator('app-jupyterlite-terminal')).toBeVisible({ timeout: 60000 });
  });

  test('instantiates simulated Hamilton STAR', async ({ page }) => {
    // Select simulated Hamilton
    await page.locator('[data-testid="machine-selector"]').click();
    await page.locator('[data-testid="machine-hamilton-star-sim"]').click();

    // Click connect/instantiate
    await page.locator('[data-testid="connect-machine"]').click();

    // Wait for instantiation complete
    await expect(page.locator('[data-testid="machine-status"]'))
      .toContainText('Connected', { timeout: 30000 });

    // Verify no errors in console
    const errors = await page.evaluate(() => (window as any).__pythonErrors || []);
    expect(errors).toHaveLength(0);
  });

  test('instantiates simulated OT-2', async ({ page }) => {
    // Select simulated OT-2
    await page.locator('[data-testid="machine-selector"]').click();
    await page.locator('[data-testid="machine-ot-2-sim"]').click();

    // Click connect/instantiate
    await page.locator('[data-testid="connect-machine"]').click();

    // Wait for instantiation complete
    await expect(page.locator('[data-testid="machine-status"]'))
      .toContainText('Connected', { timeout: 30000 });

    // Verify no errors in console
    const errors = await page.evaluate(() => (window as any).__pythonErrors || []);
    expect(errors).toHaveLength(0);
  });

  test.describe('with instantiated machine', () => {
    test.beforeEach(async ({ page }) => {
      // Instantiate a machine before each test in this block
      await page.locator('[data-testid="machine-selector"]').click();
      await page.locator('[data-testid="machine-hamilton-star-sim"]').click();
      await page.locator('[data-testid="connect-machine"]').click();
      await expect(page.locator('[data-testid="machine-status"]'))
        .toContainText('Connected', { timeout: 30000 });
    });

    test('machine setup() completes without error', async ({ page }) => {
      // Click setup
      await page.locator('[data-testid="setup-machine"]').click();

      // Wait for setup complete
      await expect(page.locator('[data-testid="machine-status"]'))
        .toContainText('Ready', { timeout: 30000 });

      // Verify no new errors
      const errors = await page.evaluate(() => (window as any).__pythonErrors || []);
      expect(errors).toHaveLength(0);
    });

    test('machine stop() cleans up correctly', async ({ page }) => {
      // Setup the machine first
      await page.locator('[data-testid="setup-machine"]').click();
      await expect(page.locator('[data-testid="machine-status"]'))
        .toContainText('Ready', { timeout: 30000 });

      // Click stop/disconnect
      await page.locator('[data-testid="disconnect-machine"]').click();

      // Verify disconnected state
      await expect(page.locator('[data-testid="machine-status"]'))
        .toContainText('Disconnected', { timeout: 10000 });

      // Verify no new errors
      const errors = await page.evaluate(() => (window as any).__pythonErrors || []);
      expect(errors).toHaveLength(0);
    });
  });
});
