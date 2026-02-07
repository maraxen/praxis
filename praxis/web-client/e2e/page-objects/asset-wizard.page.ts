import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class AssetWizardPage extends BasePage {
  readonly dialog: Locator;
  readonly stepper: Locator;

  // Step indicators (resolved dynamically via waitForStep)

  // Type Step
  readonly machineTypeCard: Locator;
  readonly resourceTypeCard: Locator;

  // Navigation
  readonly nextButton: Locator;
  readonly backButton: Locator;
  readonly createButton: Locator;

  // Config Step
  readonly instanceNameInput: Locator;

  constructor(page: Page) {
    super(page, '/app/playground?mode=worker');

    this.dialog = page.locator('app-asset-wizard');
    this.stepper = page.locator('mat-stepper');

    // Type step cards
    this.machineTypeCard = page.locator('[data-testid="type-card-machine"]');
    this.resourceTypeCard = page.locator('[data-testid="type-card-resource"]');

    // Navigation buttons
    this.nextButton = page.locator('[data-testid="wizard-next-button"]:not([disabled])');
    this.backButton = page.locator('[data-testid="wizard-back-button"]');
    this.createButton = page.locator('[data-testid="wizard-create-btn"]');

    // Config inputs
    this.instanceNameInput = page.locator('[data-testid="input-instance-name"]');
  }

  /**
   * Waits for dialog animation to complete before interaction.
   * Material CDK dialogs use ~200ms enter animation.
   */
  async waitForDialogReady(): Promise<void> {
    // Wait for overlay backdrop (indicates dialog is opening)
    const backdrop = this.page.locator('.cdk-overlay-backdrop');
    await backdrop.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
      // Backdrop may not always be present
    });
    // Wait for animation to complete (CDK uses ~200ms)
    await this.page.waitForTimeout(250);
    // Wait for dialog container to stabilize
    const dialogContainer = this.page.locator('.cdk-overlay-pane:has(app-asset-wizard)');
    await dialogContainer.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
      // May not be in a dialog overlay
    });
  }

  async openFromPlaygroundHeader(type: 'machine' | 'resource' | 'browse' = 'machine') {
    const ariaLabels: Record<string, string> = {
      machine: 'Add Machine',
      resource: 'Add Resource',
      browse: 'Browse Inventory'
    };
    await this.page.getByRole('button', { name: ariaLabels[type] }).click();
    await this.waitForDialogReady();
    await expect(this.dialog).toBeVisible({ timeout: 5000 });
  }

  async selectAssetType(type: 'MACHINE' | 'RESOURCE') {
    const card = type === 'MACHINE' ? this.machineTypeCard : this.resourceTypeCard;
    await card.click();
    await this.nextButton.click();
  }

  async selectCategory(category: string) {
    await this.waitForDialogReady();
    const categoryCard = this.page.locator(`[data-testid="category-card-${category}"]`);
    await expect(categoryCard).toBeVisible({ timeout: 20000 });
    await categoryCard.waitFor({ state: 'attached' });
    await categoryCard.click({ timeout: 5000 });
    await this.nextButton.click();
  }

  async selectFrontend(index: number = 0) {
    const frontendCards = this.page.locator('.result-card');
    await frontendCards.nth(index).click();
    await this.nextButton.click();
  }

  async selectBackend(preferSimulator: boolean = true) {
    if (preferSimulator) {
      // Select the simulated backend
      const simulatorCard = this.page.locator('.result-card:has-text("Simulated")').first();
      if (await simulatorCard.isVisible()) {
        await simulatorCard.click();
      } else {
        // Fall back to first backend
        await this.page.locator('.result-card').first().click();
      }
    } else {
      await this.page.locator('.result-card').first().click();
    }
    await this.nextButton.click();
  }

  async configureAsset(name: string, description?: string) {
    await this.instanceNameInput.fill(name);
    if (description) {
      await this.page.locator('textarea[formControlName="description"]').fill(description);
    }
    await this.nextButton.click();
  }

  async createAsset() {
    await this.createButton.click();
  }

  async waitForDialogClose() {
    await expect(this.dialog).not.toBeVisible({ timeout: 10000 });
  }

  async waitForStep(stepLabel: string) {
    const stepHeader = this.page.locator('mat-step-header[aria-selected="true"]');
    await expect(stepHeader).toBeVisible({ timeout: 15000 });
    await expect(stepHeader).toContainText(stepLabel, { timeout: 5000 });
  }
}
