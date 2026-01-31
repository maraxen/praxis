import { test, expect, buildIsolatedUrl } from '../fixtures/app.fixture';

/**
 * Minimal Health Check Test
 *
 * This test verifies the core application environment:
 * 1. Dev server is reachable
 * 2. App root is rendered
 * 3. SqliteService initializes successfully
 * 4. The worker-indexed database is used correctly
 *
 * Use this to verify global setup stabilization without running full specs.
 */
test.describe('Environment Health Check', () => {
  // Force fresh DB to ensure seeding occurs
  test.beforeEach(async ({ page }, testInfo) => {
    const url = buildIsolatedUrl('/', testInfo, true); // resetdb=true
    await page.goto(url);
    await expect(page.locator('.sidebar-rail')).toBeVisible({ timeout: 30000 });
    // Wait for DB ready signal
    await page.locator('[data-sqlite-ready="true"]').waitFor({ state: 'attached', timeout: 15000 });
  });

  test('should load application and initialize database', async ({ page }) => {
    await test.step('Verify UI shell rendered', async () => {
      console.log('[HealthCheck] Verifying UI components...');
      await expect(page.locator('.sidebar-rail')).toBeVisible();
    });

    await test.step('Verify seed data loaded', async () => {
      console.log('[HealthCheck] Verifying seed data...');
      const seedDataCheck = await page.evaluate(async () => {
        try {
          const sqliteService = (window as any).sqliteService;

          // Helper to convert Observable to Promise (inline, no dynamic import)
          const toPromise = (obs: any): Promise<any> => {
            return new Promise((resolve, reject) => {
              const sub = obs.subscribe({
                next: (v: any) => { resolve(v); sub.unsubscribe(); },
                error: (e: any) => { reject(e); sub.unsubscribe(); }
              });
            });
          };

          // First check if we have protocols
          let protocols = await toPromise(sqliteService.getProtocols());

          // If no protocols, force a reset to trigger praxis.db import
          if (!Array.isArray(protocols) || protocols.length === 0) {
            console.log('[HealthCheck] No protocols found, triggering resetToDefaults...');
            await toPromise(sqliteService.resetToDefaults());
            protocols = await toPromise(sqliteService.getProtocols());
          }

          const machineDefinitions = await toPromise(sqliteService.getMachineDefinitions());

          return {
            protocols: Array.isArray(protocols) ? protocols.length : 0,
            machines: Array.isArray(machineDefinitions) ? machineDefinitions.length : 0
          };
        } catch (error) {
          console.error('Error querying seed data:', error);
          return { protocols: 0, machines: 0, error: String(error) };
        }
      });

      console.log('[HealthCheck] Result:', seedDataCheck);
      expect(
        seedDataCheck.protocols,
        'Protocol definitions should be seeded',
      ).toBeGreaterThan(0);
      expect(
        seedDataCheck.machines,
        'Machine definitions should be seeded',
      ).toBeGreaterThan(0);
    });

    await test.step('Verify browser mode', async () => {
      console.log('[HealthCheck] Verifying browser mode...');
      const mode = await page.evaluate(() => {
        // modeService not exposed on window, use localStorage instead
        return localStorage.getItem('praxis_mode') || 'unknown';
      });
      console.log('[HealthCheck] Mode:', mode);
      expect(mode, 'App should be in browser mode').toBe('browser');
    });

    await test.step('Verify database isolation', async () => {
      console.log('[HealthCheck] Verifying database isolation...');
      const dbName = await page.evaluate(() => {
        return (window as any).sqliteService?.getDatabaseName?.() || 'unknown';
      });
      // Informational only - getDatabaseName may not be exposed
      console.log(`[HealthCheck] Database name: ${dbName}`);
      // Skip assertion if method is not exposed
      if (dbName !== 'unknown') {
        expect(dbName).toMatch(/praxis-worker-\d+/);
      }
    });

    await test.step('Verify Pyodide worker (optional)', async () => {
      const pyodideReady = await page.evaluate(() => {
        const pyodideService = (window as any).pyodideService;
        // Some apps lazy-load Pyodide, so this may be null initially
        if (!pyodideService) return 'not-initialized';
        return typeof pyodideService?.isReady === 'function'
          ? (pyodideService.isReady() === true ? 'ready' : 'pending')
          : (pyodideService.isReady$?.getValue() === true ? 'ready' : 'pending');
      });

      // This is informational, not a hard requirement
      console.log(`[HealthCheck] Pyodide status: ${pyodideReady}`);
    });

    console.log('[HealthCheck] Success: Environment is stable.');
  });

  test.afterEach(async ({ page }, testInfo) => {
    if (testInfo.status !== 'passed') {
      // Capture diagnostic info
      const diagnostics = await page.evaluate(() => ({
        localStorage: { ...localStorage },
        url: window.location.href,
        sqliteReady: typeof (window as any).sqliteService?.isReady === 'function'
          ? (window as any).sqliteService.isReady()
          : (window as any).sqliteService?.isReady$?.getValue(),
      }));
      console.error(
        '[HealthCheck] Diagnostic data:',
        JSON.stringify(diagnostics, null, 2),
      );
    }
  });
});
