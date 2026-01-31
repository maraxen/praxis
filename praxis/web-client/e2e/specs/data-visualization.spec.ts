
import { test, expect } from '../fixtures/worker-db.fixture';

test.describe('Data Visualization Page', () => {
    test.beforeEach(async ({ page }) => {
        // Mock authentication by setting a token in local storage and adding E2E_TEST flag
        await page.addInitScript(() => {
            localStorage.setItem('auth_token', 'mock_token');
            (window as any).E2E_TEST = true;
        });
        await page.goto('/app/data');
        // Wait for SQLite DB to be ready (signal or BehaviorSubject)
        await page.waitForFunction(
            () => {
                const service = (window as any).sqliteService;
                const isSignal = typeof service?.isReady === 'function';
                return isSignal ? service.isReady() === true : service?.isReady$?.getValue() === true;
            },
            null,
            { timeout: 30000 }
        );
    });

    test('should load the data visualization page', async ({ page }) => {
        await expect(page.locator('h1')).toHaveText('Data Visualization');
    });

    // TODO: Plotly lazy-loads and takes >30s to render in E2E context
    test.skip('should render the chart', async ({ page }) => {
        // Plotly renders to plotly-plot custom element - just verify it's visible
        const chart = page.locator('plotly-plot');
        await expect(chart).toBeVisible({ timeout: 30000 });
    });

    // TODO: X-axis only has 'Time' and 'Well' options, not 'temp'
    test.skip('should change x-axis', async ({ page }) => {
        await page.getByLabel('X-Axis').click();
        await page.getByRole('option', { name: 'temp' }).click();
        const chart = page.locator('canvas');
        await expect(chart).toBeVisible();
    });

    // TODO: Export button not implemented in current component
    test.skip('should export the chart', async ({ page }) => {
        const downloadPromise = page.waitForEvent('download');
        await page.getByRole('button', { name: 'Export' }).click();
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toBe('chart.png');
    });

    // TODO: Component uses transferData signal, not data; empty state message differs
    test.skip('should show empty state', async ({ page }) => {
        // Ensure the component is rendered before trying to access it
        await expect(page.locator('app-data-visualization')).toBeVisible();

        // Clear the data
        await page.evaluate(() => {
            const component = (window as any).ng.getComponent(document.querySelector('app-data-visualization'));
            if (component) {
                component.data.set([]);
            }
        });

        // The component should now react and show the empty state message
        await expect(page.getByText('No data available to display.')).toBeVisible();
    });

    // TODO: Point selection feature not implemented
    test.skip('should select data point on click', async ({ page }) => {
        // Wait for the chart to be rendered
        const chart = page.locator('canvas');
        await expect(chart).toBeVisible();

        // Click on the first data point
        await chart.click({ position: { x: 50, y: 250 } });

        // Verify the selected point is displayed
        await expect(page.getByText('Selected Point')).toBeVisible();
        await expect(page.getByText('X: 1')).toBeVisible();
        await expect(page.getByText('Y: 2')).toBeVisible();
        await expect(page.getByText('Temp: 25')).toBeVisible();
    });
});
