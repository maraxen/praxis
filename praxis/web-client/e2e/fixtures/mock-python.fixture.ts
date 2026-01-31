import { test as base } from '@playwright/test';

/**
 * Mock Python Fixture
 * 
 * Use this fixture for E2E tests that don't need real Pyodide execution.
 * This avoids the 15-30s Pyodide init overhead for UI-focused tests.
 * 
 * Usage:
 * ```typescript
 * import { test, expect } from '../fixtures/mock-python.fixture';
 * 
 * test('should show asset dialog', async ({ page }) => {
 *   // Pyodide routes are mocked - no WASM loading
 *   await page.goto('/playground');
 *   // Test UI without waiting for Python
 * });
 * ```
 */
export const test = base.extend<{ mockPython: void }>({
    mockPython: [async ({ page }, use) => {
        // Block Pyodide WASM and large asset downloads
        await page.route('**/*.wasm', route => route.fulfill({
            status: 200,
            contentType: 'application/wasm',
            body: Buffer.from([])
        }));

        await page.route('**/pyodide/**', route => {
            const url = route.request().url();
            // Allow lock file (tiny), block everything else
            if (url.includes('lock.json')) {
                return route.continue();
            }
            return route.fulfill({
                status: 200,
                body: JSON.stringify({ packages: {} })
            });
        });

        // Set a flag so the app knows Pyodide is mocked
        await page.addInitScript(() => {
            (window as any).PRAXIS_PYODIDE_MOCKED = true;
            // Mock the PythonRuntimeService ready state
            Object.defineProperty(window, '__PRAXIS_MOCK_PYTHON__', {
                value: true,
                writable: false
            });
        });

        await use();
    }, { auto: true }]
});

export { expect } from '@playwright/test';

/**
 * Use this for specs that should run WITHOUT Pyodide.
 * The Pyodide requests are blocked, making tests much faster.
 * 
 * Specs that NEED real Pyodide should use the regular fixture
 * and be tagged with @slow.
 */
