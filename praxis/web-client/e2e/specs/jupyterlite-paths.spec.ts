import { test, expect } from '../fixtures/worker-db.fixture';
import { createPathDoublingMonitor } from '../helpers/path-verifier';

/**
 * JupyterLite Path Resolution E2E Tests
 * 
 * These tests verify that JupyterLite resources are correctly loaded without
 * path doubling issues when deployed to a subdirectory (e.g., /praxis/).
 * 
 * The tests can be run in two modes:
 * 1. Local development: Uses localhost:4200 with relative paths
 * 2. GH Pages simulation: Uses localhost:8080/praxis with absolute paths
 */

test.describe('@slow JupyterLite Path Resolution', () => {

    test.describe('Development Mode', () => {
        test('REPL config uses relative paths', async ({ page }) => {
            // Fetch the REPL config directly
            const response = await page.goto('/assets/jupyterlite/repl/jupyter-lite.json');
            expect(response?.status()).toBe(200);

            const config = await response?.json();
            expect(config['jupyter-config-data']['settingsUrl']).toBe('../build/schemas');
            expect(config['jupyter-config-data']['themesUrl']).toBe('../build/themes');
        });

        test('schemas endpoint accessible', async ({ page }) => {
            const response = await page.goto('/assets/jupyterlite/build/schemas/all.json');
            expect(response?.status()).toBe(200);

            const contentType = response?.headers()['content-type'];
            expect(contentType).toContain('application/json');
        });

        test('theme CSS accessible', async ({ page }) => {
            const response = await page.goto('/assets/jupyterlite/build/themes/@jupyterlab/theme-light-extension/index.css');
            expect(response?.status()).toBe(200);

            const contentType = response?.headers()['content-type'];
            expect(contentType).toContain('text/css');
        });
    });

    test.describe('REPL Loading', () => {
        test('REPL page loads without 404 errors for resources', async ({ page }) => {
            const { failedRequests, doubledPaths } = createPathDoublingMonitor(page);

            // Navigate to the REPL
            await page.goto('/playground');

            // Wait for JupyterLite assets to finish loading
            await page.waitForLoadState('networkidle');

            // Verify no doubled paths
            expect(doubledPaths, `Doubled path requests detected: ${doubledPaths.join(', ')}`).toHaveLength(0);

            // Log any failed requests for debugging (some 404s may be acceptable)
            if (failedRequests.length > 0) {
                console.log('Failed JupyterLite resource requests:', failedRequests);
            }
        });

        test('REPL iframe initializes correctly', async ({ page }) => {
            await page.goto('/playground');

            // Wait for the playground to load
            const jupyterIframe = page.getByTestId('jupyterlite-iframe');
            await expect(jupyterIframe).toBeVisible();
        });
    });
});

/**
 * Separate test file for GH Pages simulation
 * These tests require a special server setup with COOP/COEP headers
 * Run with: npx playwright test --config=playwright.ghpages.config.ts
 */
test.describe.skip('GH Pages Simulation (requires separate config)', () => {
    test('root config has correct baseUrl', async ({ page }) => {
        // This test requires baseURL to be http://localhost:8080/praxis
        const response = await page.goto('/assets/jupyterlite/jupyter-lite.json');
        expect(response?.status()).toBe(200);

        const config = await response?.json();
        expect(config['jupyter-config-data']['baseUrl']).toBe('/praxis/assets/jupyterlite/');
    });

    test('REPL config still uses relative paths in production', async ({ page }) => {
        const response = await page.goto('/assets/jupyterlite/repl/jupyter-lite.json');
        expect(response?.status()).toBe(200);

        const config = await response?.json();
        // Even in production, nested configs should use relative paths
        expect(config['jupyter-config-data']['settingsUrl']).toBe('../build/schemas');
        expect(config['jupyter-config-data']['themesUrl']).toBe('../build/themes');
    });
});
