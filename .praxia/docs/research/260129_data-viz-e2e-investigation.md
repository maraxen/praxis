# Data Visualization E2E Investigation

## 1. Root Cause of Canvas Not Rendering

The `data-visualization.spec.ts` test fails because the `DataVisualizationComponent` does not render a `<canvas>` element when it has no data to display. The investigation revealed the following:

- **Component Dependency:** The `DataVisualizationComponent` directly depends on the `ProtocolService` to fetch run data. The `ngOnInit` method calls `protocolService.getRuns()`.
- **No Test Data:** The E2E test does not provide any mock data for the `ProtocolService`. It navigates to the page and expects the chart to be visible immediately.
- **Empty State:** When the `ProtocolService` returns no data (as it does in the test environment), the component's fallback logic (`generateFallbackData`) is executed. However, this method only logs a console warning and does not generate any data for the chart.
- **No Canvas:** Because the `plotly-plot` component receives no data, it does not render a chart, and therefore no `<canvas>` element is ever created in the DOM. The test's `expect(chart).toBeVisible()` assertion times out and fails.

The root cause is the lack of mock data in the test environment for a component that requires data to render its primary visual element.

## 2. Proposed Fix

The recommended fix is to modify the E2E test to provide mock data. This can be achieved by intercepting the HTTP request made by the `ProtocolService` and returning a mock response.

```typescript
// in data-visualization.spec.ts

test.beforeEach(async ({ page }) => {
    // Mock the API endpoint for fetching runs
    await page.route('**/api/runs', route => {
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify([
                {
                    id: 'run-1',
                    name: 'Mock Run 1',
                    status: 'completed',
                    start_time: new Date().toISOString(),
                    end_time: new Date().toISOString(),
                }
            ]),
        });
    });

    // Mock the API endpoint for transfer logs
    await page.route('**/api/runs/run-1/transfer-logs', route => {
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify([
                {
                    timestamp: new Date().toISOString(),
                    well: 'A1',
                    volume_transferred: 10,
                    cumulative_volume: 10,
                }
            ]),
        });
    });

    // Mock authentication
    await page.addInitScript(() => {
        localStorage.setItem('auth_token', 'mock_token');
        (window as any).E2E_TEST = true;
    });

    await page.goto('/data');

    // Wait for the chart to render after data is loaded
    await page.waitForSelector('canvas');
});
```

This approach ensures the component receives the data it needs to render the chart, allowing the test to verify its visibility and functionality correctly without being dependent on a live backend or a seeded database.

## 3. Dependencies That Need Mocking

The following dependencies need to be mocked for the test to pass reliably:

1.  **`ProtocolService.getRuns()`:** This service method is called on component initialization. It should be mocked to return an array of `MockRun` objects. In a real test, this would be an API call to `/api/runs`.
2.  **`ProtocolService.getTransferLogs(runId)`:** This is called after a run is selected. It should be mocked to return transfer log data for the selected run. In a real test, this would be an API call to `/api/runs/{runId}/transfer-logs`.

By mocking these service calls at the network level, we decouple the test from the backend and ensure it runs quickly and reliably.
