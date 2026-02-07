import { test, expect } from '../fixtures/worker-db.fixture';
import { PlaygroundPage } from '../page-objects/playground.page';
import { InventoryDialogPage } from '../page-objects/inventory-dialog.page';

test.describe('Inventory Dialog Verification', () => {
  // FIXME: This spec references 8+ unimplemented InventoryDialogPage methods
  // (selectBrowseTab, continue, getCategories, waitForAssetList, selectAsset, addSelectedAsset).
  // Skipped until the page object API is implemented.
  test.fixme();

  // Increase the timeout for this test file due to persistent flakiness in the environment.
  test.slow();

  test('should load definitions and allow filtering by machine category', async ({ page }, testInfo) => {
    const playground = new PlaygroundPage(page, testInfo);
    await playground.goto();
    await playground.waitForBootstrapComplete();

    // Explicitly wait for the button to be ready to handle slow UI hydration.
    await expect(playground.inventoryButton).toBeVisible({ timeout: 60000 });

    const inventoryDialog = await playground.openInventory();

    await inventoryDialog.selectBrowseTab();
    await inventoryDialog.selectMachineType();
    await inventoryDialog.continue();

    const categories = await inventoryDialog.getCategories();
    expect(categories.length).toBeGreaterThan(0);
    expect(categories).toContain('Liquid Handler');

    await inventoryDialog.selectCategory('Liquid Handler');
    await inventoryDialog.continue();
    await inventoryDialog.waitForAssetList();
  });

  test('should add selected asset to playground', async ({ page }, testInfo) => {
    const playground = new PlaygroundPage(page, testInfo);
    await playground.goto();
    await playground.waitForBootstrapComplete();

    // Explicitly wait for the button to be ready to handle slow UI hydration.
    await expect(playground.inventoryButton).toBeVisible({ timeout: 60000 });

    const inventoryDialog = await playground.openInventory();

    await inventoryDialog.selectBrowseTab();
    await inventoryDialog.selectMachineType();
    await inventoryDialog.continue();
    await inventoryDialog.selectCategory('Liquid Handler');
    await inventoryDialog.continue();
    await inventoryDialog.waitForAssetList();

    // Select a known asset and add it
    await inventoryDialog.selectAsset(/Opentrons OT-2/i);
    await inventoryDialog.addSelectedAsset();

    // Verify UI state
    await expect(inventoryDialog.dialog).toBeHidden();
    await expect(page.getByTestId('playground-asset-card')).toBeVisible();

    // Verify internal state
    // Verify internal state via page evaluate
    const assets = await page.evaluate(() => {
      return (window as any).__praxis_playground_assets ?? [];
    });
    expect(assets).toHaveLength(1);
    const firstAsset = assets[0] as { definition: { name: string } };
    expect(firstAsset.definition.name).toBe('Opentrons OT-2');
  });

  test('should have database integrity', async ({ page }, testInfo) => {
    const playground = new PlaygroundPage(page, testInfo);
    await playground.goto();
    // Bootstrap is necessary to ensure the database is seeded before we query it.
    await playground.waitForBootstrapComplete();

    const dbResult = await page.evaluate(async () => {
      const db = await (window as any).sqliteService?.getDatabase();
      if (!db) {
        return { tables: [], machineCount: 0 };
      }
      const tablesResult = db.exec("SELECT name FROM sqlite_master WHERE type='table'");
      const machineCountResult = db.exec("SELECT COUNT(*) FROM machine_definitions");

      return {
        tables: tablesResult[0]?.values.flat() || [],
        machineCount: machineCountResult[0]?.values[0][0] || 0,
      };
    });

    expect(dbResult.tables).toContain('machine_definitions');
    expect(dbResult.machineCount).toBeGreaterThan(5);
  });
});
