import { Page, Locator } from '@playwright/test';
import { BasePage } from './base.page';

export class DashboardPage extends BasePage {
  readonly telemetryChart: Locator;
  readonly plateHeatmap: Locator;

  constructor(page: Page) {
    super(page);
    this.telemetryChart = page.getByTestId('telemetry-chart');
    this.plateHeatmap = page.getByTestId('plate-heatmap');
  }

  async waitForChartsLoaded(): Promise<void> {
    await this.telemetryChart.waitFor({ state: 'visible' });
    // Add a more specific wait here if necessary, e.g., for canvas to be rendered
  }
}
