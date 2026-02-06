
import { test, expect } from '../fixtures/worker-db.fixture';

test.describe('Data Visualization Page', () => {
    test.slow();

    test.beforeEach(async ({ page }) => {
        // Mock authentication by setting a token in local storage and adding E2E_TEST flag
        await page.addInitScript(() => {
            localStorage.setItem('auth_token', 'mock_token');
            (window as any).E2E_TEST = true;
        });
        await page.goto('/app/data');

        // Close any possible overlays (onboarding, etc)
        await page.keyboard.press('Escape');

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

    test('should render the chart', async ({ page }) => {
        // Plotly renders to plotly-plot custom element - just verify it's visible
        const chart = page.locator('plotly-plot');
        await expect(chart).toBeVisible({ timeout: 30000 });
    });

    test('should change x-axis', async ({ page }) => {
        // Ensure any loading overlays are gone
        await page.locator('.cdk-overlay-backdrop').waitFor({ state: 'detached', timeout: 5000 }).catch(() => {});

        // Use keyboard to interact with mat-select for better reliability
        const select = page.locator('mat-select').first();
        await select.focus();
        await page.keyboard.press('Enter');

        // Wait for the overlay and select 'Well' (which is the second option)
        // Options are 'Time' (timestamp) and 'Well' (well)
        await page.keyboard.press('ArrowDown');
        await page.keyboard.press('Enter');

        const chart = page.locator('plotly-plot');
        await expect(chart).toBeVisible();
    });

    test('should export the chart', async ({ page }) => {
        // Ensure any loading overlays are gone
        await page.locator('.cdk-overlay-backdrop').waitFor({ state: 'detached', timeout: 5000 }).catch(() => {});

        const downloadPromise = page.waitForEvent('download');
        // Click via evaluate to bypass overlays
        await page.locator('button:has-text("Export")').evaluate(el => (el as HTMLElement).click());
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toBe('chart.png');
    });

    test('should show empty state', async ({ page }) => {
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

    test('should select data point on click', async ({ page }) => {
        // Wait for the chart to be rendered
        const chart = page.locator('plotly-plot');
        await expect(chart).toBeVisible();

        // Mock a point click event since clicking exact coordinates on Plotly is flaky in CI
        await page.evaluate(() => {
            const component = (window as any).ng.getComponent(document.querySelector('app-data-visualization'));
            if (component) {
                component.onPointClick({
                    points: [{
                        x: '1',
                        y: '2',
                        fullData: { name: 'A1' },
                        customdata: { temp: 25 }
                    }]
                });
            }
        });

        // Verify the selected point is displayed
        await expect(page.getByText('Selected Point')).toBeVisible();
        await expect(page.getByText('X: 1')).toBeVisible();
        await expect(page.getByText('Y: 2')).toBeVisible();
        await expect(page.getByText('Temp: 25')).toBeVisible();
    });
});
