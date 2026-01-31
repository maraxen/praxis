import { test, expect } from '../fixtures/worker-db.fixture';

/**
 * GitHub Pages Deployment Verification Tests
 * 
 * These tests validate that the production build works correctly when deployed
 * to the /praxis/ subdirectory, simulating the actual GitHub Pages environment.
 * 
 * IMPORTANT: These tests require the GH Pages simulation server running.
 * Use: npx playwright test --config=playwright.ghpages.config.ts
 * 
 * The simulation server provides:
 *   - Content served from /praxis/ subdirectory
 *   - COOP/COEP headers for SharedArrayBuffer (Pyodide)
 *   - SPA routing rewrites
 */

test.describe('GitHub Pages Deployment Verification', () => {

    test.describe('JupyterLite Path Resolution (Critical)', () => {

        test.fixme('@slow no 404 errors for JupyterLite core resources', async ({ page }) => {
            // FIXME: Requires full Pyodide bootstrap - need mock or snapshot/restore
            test.slow();
            const failedResources: { url: string; status: number }[] = [];

            // Monitor all responses for JupyterLite resource failures
            page.on('response', (response) => {
                const url = response.url();
                const status = response.status();

                // Track 404s specifically for JupyterLite resources
                if (status === 404 && url.includes('jupyterlite')) {
                    failedResources.push({ url, status });
                }
            });

            await page.goto('playground');

            // Wait for JupyterLite iframe to load
            await expect(page.locator('app-playground iframe')).toBeVisible({ timeout: 30000 });
            // Wait for network to settle (JupyterLite resources)
            await page.waitForLoadState('networkidle', { timeout: 45000 });

            // Assert no failed resources
            if (failedResources.length > 0) {
                console.log('Failed JupyterLite resources:', failedResources);
            }
            expect(failedResources,
                `JupyterLite resources returned 404:\n${failedResources.map(r => `  ${r.url}`).join('\n')}`
            ).toHaveLength(0);
        });

        test.fixme('@slow no path doubling in resource URLs', async ({ page }) => {
            // FIXME: Requires full Pyodide bootstrap - need mock or snapshot/restore
            test.slow();
            const doubledPaths: string[] = [];

            // Monitor all requests for path doubling patterns
            page.on('request', (request) => {
                const url = request.url();

                // Pattern 1: /praxis/.../praxis/
                if (url.match(/\/praxis\/[^/]+\/praxis\//)) {
                    doubledPaths.push(url);
                }

                // Pattern 2: /assets/jupyterlite/.../assets/jupyterlite/
                if (url.match(/\/assets\/jupyterlite\/[^/]+\/assets\/jupyterlite\//)) {
                    doubledPaths.push(url);
                }

                // Pattern 3: Relative path escaping the jupyterlite directory
                // e.g., /praxis/assets/build instead of /praxis/assets/jupyterlite/build
                if (url.includes('/praxis/assets/build/') && !url.includes('/jupyterlite/')) {
                    doubledPaths.push(`Path escaped jupyterlite: ${url}`);
                }
            });

            await page.goto('playground');
            // Wait for iframe to load and network to settle
            await expect(page.locator('app-playground iframe')).toBeVisible({ timeout: 30000 });
            await page.waitForLoadState('networkidle', { timeout: 45000 });

            expect(doubledPaths,
                `Doubled paths detected:\n${doubledPaths.join('\n')}`
            ).toHaveLength(0);
        });

        test('theme CSS loads from correct absolute path', async ({ page }) => {
            // Direct request to verify the expected path works
            const response = await page.goto(
                'assets/jupyterlite/build/themes/@jupyterlab/theme-light-extension/index.css'
            );

            expect(response?.status()).toBe(200);
            expect(response?.headers()['content-type']).toContain('text/css');
        });

        test('schemas JSON loads from correct absolute path', async ({ page }) => {
            const response = await page.goto('assets/jupyterlite/build/schemas/all.json');

            expect(response?.status()).toBe(200);
            expect(response?.headers()['content-type']).toContain('application/json');
        });

        test('REPL config has correct absolute path resolution for GH Pages', async ({ page }) => {
            // Verify the nested REPL config exists and has the right absolute paths
            const response = await page.goto('assets/jupyterlite/repl/jupyter-lite.json');
            expect(response?.status()).toBe(200);

            const config = await response?.json();
            const configData = config['jupyter-config-data'];

            // GH Pages REPL uses absolute paths to prevent path doubling
            expect(configData['settingsUrl']).toBe('/praxis/assets/jupyterlite/build/schemas');
            expect(configData['themesUrl']).toBe('/praxis/assets/jupyterlite/build/themes');
        });

        test('root config uses absolute paths for GH Pages', async ({ page }) => {
            const response = await page.goto('assets/jupyterlite/jupyter-lite.json');
            expect(response?.status()).toBe(200);

            const config = await response?.json();
            const configData = config['jupyter-config-data'];

            // GH Pages deployment uses absolute paths for reliable resolution
            expect(configData['baseUrl']).toBe('/praxis/assets/jupyterlite/');
            expect(configData['fullStaticUrl']).toBe('/praxis/assets/jupyterlite/build');
        });
    });

    test.describe('Angular SPA Routing', () => {

        test('app home loads correctly with browser mode', async ({ page }) => {
            const response = await page.goto('app/home?mode=browser');
            expect(response?.ok()).toBeTruthy();

            // Should not redirect outside /praxis/
            expect(page.url()).toContain('/praxis/');
        });

        test('playground route loads correctly', async ({ page }) => {
            const response = await page.goto('playground');
            expect(response?.ok()).toBeTruthy();

            await expect(page.locator('app-playground')).toBeVisible({ timeout: 15000 });
        });

        test('direct deep link to run-protocol works', async ({ page }) => {
            await page.goto('app/run-protocol?mode=browser');

            // Should load without 404
            expect(page.url()).toContain('/praxis/');
        });

        test('base href does not break core Angular assets', async ({ page }) => {
            test.slow(); // Initial page load can be slow
            const failedAssets: string[] = [];

            page.on('response', (response) => {
                const url = response.url();
                const status = response.status();

                // Track failed JS/CSS/font assets
                if (status >= 400 && (
                    url.endsWith('.js') ||
                    url.endsWith('.css') ||
                    url.endsWith('.woff2') ||
                    url.endsWith('.wasm')
                )) {
                    failedAssets.push(`${status} ${url}`);
                }
            });

            await page.goto('app/home?mode=browser');
            await page.waitForLoadState('networkidle');

            if (failedAssets.length > 0) {
                console.log('Failed assets:', failedAssets);
            }
            expect(failedAssets, `Failed assets: ${failedAssets.join(', ')}`).toHaveLength(0);
        });

        test('invalid route does not break app (stays in /praxis/)', async ({ page }) => {
            const response = await page.goto('app/nonexistent-route-xyz');
            // App should handle gracefully - either redirect or show content
            expect(response?.ok()).toBeTruthy();
            // Verify we stay within /praxis/ subdirectory (not escaped to root)
            expect(page.url()).toContain('/praxis/');
        });

        test('sqlite3-opfs-async-proxy.js loads from correct path', async ({ page }) => {
            // Verify the worker script is served correctly
            const response = await page.goto('sqlite3-opfs-async-proxy.js');
            expect(response?.status()).toBe(200);
            const text = await response?.text();
            expect(text).toContain('OPFS'); // Should contain OPFS-related code
        });
    });

    test.describe('Pyodide/SharedArrayBuffer Headers', () => {

        test('COOP header is set correctly', async ({ page }) => {
            const response = await page.goto('app/home');
            const headers = response?.headers();

            expect(headers?.['cross-origin-opener-policy']).toBe('same-origin');
        });

        test('COEP header is set correctly', async ({ page }) => {
            const response = await page.goto('app/home');
            const headers = response?.headers();

            expect(headers?.['cross-origin-embedder-policy']).toBe('require-corp');
        });
    });

    test.describe('Branding & Logo', () => {

        test('logo renders on splash/home', async ({ page }) => {
            await page.goto('app/home?mode=browser');

            // Wait for the shell to render
            await page.waitForSelector('app-unified-shell', { timeout: 15000 });

            // The logo should be visible (either as img or inline SVG)
            const logo = page.getByTestId('praxis-logo');
            await expect(logo).toBeVisible();
        });
    });

    test.describe('SQLite/Browser Mode Initialization', () => {

        test('SqliteService becomes ready', async ({ page }) => {
            await page.goto('app/home?mode=browser');

            // Wait for the service to be ready via data attribute (preferred method)
            await page.locator('[data-sqlite-ready="true"]').waitFor({ state: 'attached', timeout: 60000 });

            // Verify attribute is set correctly
            const isReady = await page.locator('[data-sqlite-ready="true"]').isVisible();

            expect(isReady).toBeTruthy();
        });
    });
});