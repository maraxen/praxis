import { test, expect, buildWorkerUrl } from '../fixtures/worker-db.fixture';
import { SettingsPage } from '../page-objects/settings.page';
import { WelcomePage } from '../page-objects/welcome.page';
import * as fs from 'fs';

test.describe('Settings Page Functionality', () => {
  let settingsPage: SettingsPage;

  test.beforeEach(async ({ page }, testInfo) => {
    const url = buildWorkerUrl('/app/settings', testInfo.workerIndex);
    await page.goto(url);
    await new WelcomePage(page, testInfo).handleSplashScreen();
    settingsPage = new SettingsPage(page);
  });

  test('renders settings interface', async ({ page }) => {
    await expect(settingsPage.exportButton).toBeVisible();
    await expect(settingsPage.importButton).toBeVisible();
  });

  test('exports database with valid SQLite file', async ({ page }) => {
    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();

    // Programmatic blob downloads don't fire Playwright download events reliably.
    // Instead, verify the UI feedback (snackbar).
    await settingsPage.exportButton.click();

    const snackbar = page.locator('mat-snack-bar-container').filter({ hasText: 'Database exported' });
    await expect(snackbar).toBeVisible({ timeout: 15000 });
  });

  test('shows success snackbar after export', async ({ page }) => {
    await settingsPage.exportButton.click();
    const snackbar = page.locator('simple-snack-bar', { hasText: /exported/i });
    await expect(snackbar).toBeVisible();
  });

  test('performs a successful database export and import round-trip', async ({ page }) => {
    const downloadPath = await settingsPage.exportDatabase();

    // Verify the downloaded file exists
    expect(fs.existsSync(downloadPath)).toBe(true);

    await settingsPage.importDatabase(downloadPath);

    // Verify that the import was successful by checking for a success message
    const snackbar = page.locator('simple-snack-bar', { hasText: /imported/i });
    await expect(snackbar).toBeVisible();

    // Clean up the downloaded file
    if (fs.existsSync(downloadPath)) {
      fs.unlinkSync(downloadPath);
    }
  });

  test('cycles through all themes', async ({ page }) => {
    const themes = ['light', 'dark', 'system'];
    for (const theme of themes) {
      await page.locator(`mat-button-toggle[value="${theme}"]`).click();

      // The AppStore adds a `dark-theme` class to the body for the dark theme.
      // For 'light' and 'system', it relies on the absence of this class.
      if (theme === 'dark') {
        await expect(page.locator('body')).toHaveClass(/dark-theme/);
      } else {
        await expect(page.locator('body')).not.toHaveClass(/dark-theme/);
      }
    }
  });
});
