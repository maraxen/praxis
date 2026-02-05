import { expect, type Page, type Locator } from '@playwright/test';
import { BasePage } from './base.page';
import { buildWorkerUrl } from '../fixtures/worker-db.fixture';
import { WelcomePage } from './welcome.page';

export class SmokePage extends BasePage {
  workerIndex: number;

  constructor(page: Page, workerIndex: number) {
    super(page, '/');
    this.workerIndex = workerIndex;
  }

  /**
   * OVERRIDE: Navigate using 'browser' mode with pre-seeded database.
   * Using resetdb=false to preserve the seeded praxis.db data.
   */
  async goto(path: string): Promise<void> {
    const url = buildWorkerUrl(path, this.workerIndex, {
      resetdb: false,
      mode: 'browser',
    });
    await this.page.goto(url, { waitUntil: 'domcontentloaded' });

    // Wait for SQLite ready signal using modern attribute-based selector
    // This is more robust than waitForFunction polling window objects
    await this.page.locator('[data-sqlite-ready="true"]').waitFor({
      state: 'attached',
      timeout: 30000
    });
  }

  async handleSplashScreen(): Promise<void> {
    const welcome = new WelcomePage(this.page);
    await welcome.handleSplashScreen();
  }

  // Dashboard
  get appShell(): Locator {
    return this.page.locator('app-unified-shell, app-main-layout');
  }

  get navRail(): Locator {
    return this.page.locator('.sidebar-rail, .nav-rail').first();
  }

  // Assets
  get assetsComponent(): Locator {
    return this.page.locator('app-assets');
  }

  get machinesTab(): Locator {
    return this.page.getByRole('tab', { name: /Machines/i });
  }

  get resourcesTab(): Locator {
    return this.page.getByRole('tab', { name: /Resources/i });
  }

  get registryTab(): Locator {
    return this.page.getByRole('tab', { name: /Registry/i });
  }

  get machineTable(): Locator {
    // Mat-Table can render as either <table mat-table> or use mat-row elements
    return this.page.locator('app-machine-list table, app-machine-list mat-table');
  }

  // Protocols
  get protocolLibrary(): Locator {
    return this.page.locator('app-protocol-library');
  }

  get protocolTable(): Locator {
    return this.page.locator('app-protocol-library table');
  }

  // Run Wizard
  get runProtocolComponent(): Locator {
    return this.page.locator('app-run-protocol');
  }

  get stepper(): Locator {
    return this.page.locator('mat-stepper');
  }

  stepHeader(name: string): Locator {
    return this.page.getByRole('listitem', { name: new RegExp(name, 'i') });
  }

  // Verification helpers
  async verifyDashboardLoaded(): Promise<void> {
    await expect(this.appShell).toBeVisible();
    await expect(this.navRail).toBeVisible();
  }

  async verifyMachineTableHasData(): Promise<void> {
    // Mat-Table uses mat-row elements, not traditional tbody tr
    await expect(this.machineTable.locator('mat-row, tr.mat-mdc-row, .mat-mdc-row').first()).toBeVisible({ timeout: 10000 });
  }
}
