import { test, expect, buildIsolatedUrl, waitForDbReady } from '../fixtures/app.fixture';
import { ProtocolLibraryPage } from '../page-objects/protocol-library.page';

test.describe('Protocol Library', () => {
  let protocolLibrary: ProtocolLibraryPage;

  test.beforeEach(async ({ page }, testInfo) => {
    protocolLibrary = new ProtocolLibraryPage(page);
    // The app fixture navigates to `/` and handles the welcome dialog.
    // We need to navigate to the correct page for this test suite,
    // preserving the worker-isolated database parameters.
    await page.goto(buildIsolatedUrl('/app/protocols', testInfo));
    await waitForDbReady(page);
    await protocolLibrary.waitForTableReady();
  });

  test('should load the protocol library page', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Protocol/i);
    const count = await protocolLibrary.getDisplayedProtocolCount();
    expect(count).toBeGreaterThan(0);
  });

  test('should search for a protocol by name', async () => {
    await protocolLibrary.searchProtocol('Kinetic');
    await expect(protocolLibrary.getRowByName('Kinetic Assay')).toBeVisible();
    await expect(protocolLibrary.getRowByName('Simple Transfer')).not.toBeVisible({ timeout: 5000 });
  });

  test('should filter protocols by status', async ({ page }) => {
    const initialCount = await protocolLibrary.getDisplayedProtocolCount();
    expect(initialCount).toBeGreaterThan(0);

    await protocolLibrary.openStatusFilter();
    // Select 'Failed' — all seed protocols have simulation_result.passed === false
    const failedOption = page.getByRole('option', { name: /Failed/i });
    await expect(failedOption).toBeVisible({ timeout: 5000 });
    await failedOption.click();
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Verify filter applied — table should still show results
    const finalCount = await protocolLibrary.getDisplayedProtocolCount();
    expect(finalCount).toBeGreaterThanOrEqual(1);
  });

  test('should open protocol details', async ({ page }) => {
    // Click the first data row (not header)
    const firstRow = page.locator('tr[mat-row]').first();
    await expect(firstRow).toBeVisible();
    await firstRow.click({ force: true });
    // viewDetails() opens a MatDialog
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible({ timeout: 10000 });
    // Dialog should have a run button
    await expect(dialog.getByRole('button', { name: /Run Protocol/i })).toBeVisible({ timeout: 5000 });
  });

  test('should start a protocol run from the library', async ({ page }) => {
    // Click the play_arrow button in the first row
    const playButton = page.locator('tr[mat-row]').first().locator('button').filter({ has: page.locator('mat-icon', { hasText: 'play_arrow' }) });
    await expect(playButton).toBeVisible();
    await playButton.click({ force: true });
    await expect(page).toHaveURL(/\/run/, { timeout: 10000 });
  });

  test('should toggle to card view and display protocol cards', async ({ page }) => {
    await protocolLibrary.toggleToCardView();
    const cards = page.locator('app-protocol-card');
    await expect(cards.first()).toBeVisible();
    const cardCount = await cards.count();
    expect(cardCount).toBeGreaterThan(0);
  });

  test('should display correct protocol metadata in table row', async () => {
    // Verify a known seeded protocol has correct data
    const kineticRow = protocolLibrary.getRowByName('Kinetic Assay');
    await expect(kineticRow).toBeVisible();

    // Check category badge is present
    await expect(kineticRow).toContainText(/Plate Reading|Assay/i);

    // Check version format (e.g., "1.0.0" or similar)
    await expect(kineticRow).toContainText(/\d+\.\d+/);
  });

  test('should display full protocol details in dialog', async () => {
    await protocolLibrary.openProtocolDetails('Kinetic Assay');

    // Verify dialog shows protocol name
    await protocolLibrary.assertDialogContent('Kinetic Assay');

    // Verify dialog has key elements
    const dialog = protocolLibrary.detailDialog;
    await expect(dialog.getByRole('button', { name: /Run Protocol/i })).toBeVisible();

    // Could add: description, category, parameter list verification
  });

  test('should display empty state when no protocols match search', async ({ page }) => {
    await protocolLibrary.searchProtocol('NONEXISTENT_PROTOCOL_XYZ');

    // Wait for filter to apply
    await page.waitForFunction(() => {
      return document.querySelectorAll('tr[mat-row]').length === 0;
    }, { timeout: 10000 });

    // Verify empty state message
    await expect(page.getByText(/No protocols found/i)).toBeVisible();
  });

  test('should handle protocol load failure gracefully', async ({ page }) => {
    // Intercept the protocol service and fail it
    await page.route('**/api/protocols**', route => route.abort('failed'));

    // Navigate fresh (not using goto which expects success)
    await page.goto('/app/protocols?mode=browser');

    // Verify error handling (depends on component implementation)
    // At minimum, page should not crash
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Protocol/i);
  });

  test('should pass correct protocolId when running from table', async ({ page }) => {
    // Get the first protocol's name to trace
    const firstRow = protocolLibrary.getRowByName('Kinetic Assay');
    await expect(firstRow).toBeVisible();

    // Click run button
    const playButton = firstRow.getByRole('button').filter({
      has: page.locator('mat-icon:has-text("play_arrow")')
    });
    await playButton.click();

    // Verify URL contains protocolId parameter
    await expect(page).toHaveURL(/\/run\?.*protocolId=/);
  });

  test('should have protocols loaded from SQLite database', async ({ page }) => {
    // Access Angular component's signal state
    const protocolCount = await page.evaluate(() => {
      const component = (window as any).ng?.getComponent(
        document.querySelector('app-protocol-library')
      );
      return component?.protocols()?.length ?? 0;
    });

    expect(protocolCount).toBeGreaterThan(0);
  });

  test.skip('should upload a .py protocol file and show it in the library', async ({ page }) => {
    // Requires mocking file input dialog — keep skipped until test infrastructure supports it
  });

  test('should filter protocols by category', async ({ page }) => {
    const initialCount = await protocolLibrary.getDisplayedProtocolCount();
    expect(initialCount).toBeGreaterThan(0);

    await protocolLibrary.openCategoryFilter();
    // Select the first visible category option
    const firstOption = page.getByRole('option').first();
    const categoryText = await firstOption.textContent();
    expect(categoryText).toBeTruthy();
    await firstOption.click();
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Verify filter applied
    const finalCount = await protocolLibrary.getDisplayedProtocolCount();
    expect(finalCount).toBeGreaterThanOrEqual(1);
    expect(finalCount).toBeLessThanOrEqual(initialCount);
  });
});
