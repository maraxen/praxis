import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class ProtocolLibraryPage extends BasePage {
  readonly searchInput: Locator;
  readonly table: Locator;
  readonly loadingSpinner: Locator;
  readonly uploadButton: Locator;
  readonly detailDialog: Locator;

  constructor(page: Page) {
    super(page, '/app/protocols');
    this.searchInput = page.getByPlaceholder(/Search/i);
    this.table = page.getByRole('table');
    this.loadingSpinner = page.locator('mat-spinner');
    this.uploadButton = page.locator('[data-tour-id="import-protocol-btn"]');
    this.detailDialog = page.getByRole('dialog');
  }

  async waitForTableReady(timeout = 30000): Promise<void> {
    // Wait for table or card view to render
    await expect(this.table.or(this.page.locator('app-protocol-card'))).toBeVisible({ timeout });
    await expect(this.loadingSpinner).not.toBeVisible({ timeout: 5000 });
  }

  /** Returns all visible protocol rows (excludes header) */
  getProtocolRows(): Locator {
    return this.table.getByRole('row').filter({ hasNotText: /^Name.*Version.*Description/i });
  }

  /** Returns a specific protocol row by name */
  getRowByName(name: string): Locator {
    return this.getProtocolRows().filter({ hasText: name });
  }

  async searchProtocol(query: string): Promise<void> {
    await expect(this.searchInput).toBeVisible();
    await this.searchInput.fill(query);
    // Wait for filter to apply by checking row content
    await this.page.waitForFunction(
      (q) => {
        const rows = Array.from(document.querySelectorAll('tr[mat-row]'));
        return rows.length === 0 || rows.some(r => r.textContent?.toLowerCase().includes(q.toLowerCase()));
      },
      query,
      { timeout: 10000 }
    );
  }

  /**
   * Opens a multiselect filter dropdown from the ViewControls bar.
   *
   * The PraxisMultiselectComponent wraps a MatSelect which renders as
   * a combobox with an accessible name matching the filter label (e.g. "Status", "Category").
   * When opened, options appear as role="option" inside a role="listbox".
   */
  private async openFilter(label: RegExp): Promise<void> {
    const combobox = this.page.getByRole('combobox', { name: label });
    await expect(combobox).toBeVisible({ timeout: 5000 });
    await combobox.click();

    // Wait for the listbox to appear with options
    await expect(this.page.getByRole('option').first()).toBeVisible({ timeout: 5000 });
  }

  async openStatusFilter(): Promise<void> {
    await this.openFilter(/Status/i);
  }

  async openCategoryFilter(): Promise<void> {
    await this.openFilter(/Category/i);
  }

  /**
   * Selects a filter option from an open multiselect dropdown.
   * Options render as role="option" in the listbox panel.
   */
  async selectFilterOption(optionName: string): Promise<void> {
    const option = this.page.getByRole('option', { name: new RegExp(optionName, 'i') });
    await expect(option).toBeVisible({ timeout: 5000 });
    await option.click();
  }

  async filterByStatus(status: string): Promise<void> {
    await this.selectFilterOption(status);

    // Close the dropdown by pressing Escape
    await this.page.keyboard.press('Escape');

    // Wait for filter to apply
    await this.page.waitForTimeout(500);
  }

  async filterByCategory(category: string): Promise<void> {
    await this.selectFilterOption(category);

    // Close the dropdown
    await this.page.keyboard.press('Escape');

    // Wait for filter to apply
    await this.page.waitForTimeout(500);
  }

  async openProtocolDetails(name?: string): Promise<void> {
    const row = name ? this.getRowByName(name) : this.getProtocolRows().first();
    await row.click();
    await expect(this.detailDialog).toBeVisible({ timeout: 10000 });
  }

  async runProtocolFromTable(name?: string): Promise<void> {
    const row = name ? this.getRowByName(name) : this.getProtocolRows().first();
    const playButton = row.getByRole('button').filter({ has: this.page.locator('mat-icon:has-text("play_arrow")') });
    await playButton.click();
    await expect(this.page).toHaveURL(/\/run/, { timeout: 10000 });
  }

  /**
   * Toggles to card view using the ViewTypeToggle (MatButtonToggleGroup).
   * The toggle group has aria-label="View Type" with individual toggles
   * for card, list, and table views.
   */
  async toggleToCardView(): Promise<void> {
    const toggleGroup = this.page.getByLabel('View Type');
    const cardToggle = toggleGroup.locator('mat-button-toggle[value="card"]');

    if (await cardToggle.isVisible({ timeout: 3000 }).catch(() => false)) {
      await cardToggle.click();
      await expect(this.page.locator('app-protocol-card').first()).toBeVisible({ timeout: 10000 });
    }
  }

  async getDisplayedProtocolCount(): Promise<number> {
    return await this.getProtocolRows().count();
  }

  async assertDialogHasRunButton(): Promise<void> {
    const runButton = this.detailDialog.getByRole('button', { name: /Run Protocol/i });
    await expect(runButton).toBeVisible({ timeout: 5000 });
  }

  async assertDialogContent(expectedName: string): Promise<void> {
    await expect(this.detailDialog).toContainText(expectedName, { timeout: 5000 });
  }
}
