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

  async openStatusFilter(): Promise<Locator> {
    const statusCombobox = this.page.getByRole('combobox', { name: /Status/i });
    await expect(statusCombobox).toBeVisible({ timeout: 5000 });
    await statusCombobox.click();
    const panel = this.page.getByRole('listbox');
    await expect(panel).toBeVisible({ timeout: 10000 });
    return panel;
  }

  async filterByStatus(status: string): Promise<void> {
    // This method assumes the filter panel is already open
    const option = this.page.getByRole('option', { name: new RegExp(status, 'i') });
    await expect(option).toBeVisible({ timeout: 5000 });
    await option.click();
    
    // Wait for filter to apply - by waiting for the spinner to show and then hide.
    // Use a small timeout for appearance as it might be quick.
    await expect(this.loadingSpinner).toBeVisible({ timeout: 2000 }).catch(() => {
      // Ignore errors if the spinner is too fast to be caught, proceed to wait for it to be gone.
      console.log('[Test] Spinner not caught, proceeding.');
    });
    await expect(this.loadingSpinner).not.toBeVisible({ timeout: 15000 });
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

  async toggleToCardView(): Promise<void> {
    const cardViewToggle = this.page.getByRole('button', { name: /Card/i })
      .or(this.page.locator('[aria-label*="card"]'));
    if (await cardViewToggle.isVisible({ timeout: 3000 }).catch(() => false)) {
      await cardViewToggle.click();
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
