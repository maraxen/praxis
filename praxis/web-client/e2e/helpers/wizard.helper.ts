import { Page, expect, TestInfo } from '@playwright/test';
import { ProtocolPage } from '../page-objects/protocol.page';
import { WizardPage } from '../page-objects/wizard.page';

/**
 * Helper utilities for wizard step transitions and overlay handling.
 * Uses state-driven waits, NO hardcoded timeouts.
 */

/**
 * Wait for a Material stepper animation to complete and a specific step heading to be visible.
 *
 * @param page - Playwright Page
 * @param stepHeading - The heading text of the target step (e.g., "Select Machine")
 * @param options - Optional timeout configuration
 */
export async function waitForStepTransition(
    page: Page,
    stepHeading: string,
    options: { timeout?: number } = {}
): Promise<void> {
    const { timeout = 10000 } = options;

    // Wait for any stepper animation to settle (look for .mat-stepper-horizontal-line-active or similar)
    const stepper = page.locator('mat-horizontal-stepper, mat-vertical-stepper').first();

    // Wait for the step heading to become visible
    const heading = page.locator('h2, h3, .step-title, .mat-step-label').filter({ hasText: stepHeading });
    await expect(heading.first()).toBeVisible({ timeout });

    // Ensure the step content is fully rendered (not animating)
    const activeStep = stepper.locator('.mat-step-content[ng-reflect-is-selected="true"], .mat-step-content:not([hidden])').first();
    await activeStep.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
        // Fallback: just ensure heading is visible
        console.log('[WizardHelper] Step content selector did not match, relying on heading visibility');
    });
}

/**
 * Wait for all Material CDK overlays (dialogs, menus, tooltips) to dismiss.
 * Uses state-driven detection, not arbitrary timeouts.
 *
 * @param page - Playwright Page
 * @param options - Optional timeout and escape key dismissal
 */
export async function waitForOverlaysToDismiss(
    page: Page,
    options: { timeout?: number; dismissWithEscape?: boolean } = {}
): Promise<void> {
    const { timeout = 10000, dismissWithEscape = true } = options;

    const backdrop = page.locator('.cdk-overlay-backdrop');
    const overlayPane = page.locator('.cdk-overlay-pane');

    // Check if any overlay is currently visible
    const isBackdropVisible = await backdrop.first().isVisible({ timeout: 500 }).catch(() => false);
    const isOverlayVisible = await overlayPane.first().isVisible({ timeout: 500 }).catch(() => false);

    if (!isBackdropVisible && !isOverlayVisible) {
        // No overlays to wait for
        return;
    }

    // Wait for backdrop to be hidden
    try {
        await backdrop.first().waitFor({ state: 'hidden', timeout });
    } catch {
        // Backdrop persisted - try dismissing with Escape
        if (dismissWithEscape) {
            console.log('[WizardHelper] Overlay persisted, attempting Escape key dismiss...');
            await page.keyboard.press('Escape');
            await backdrop.first().waitFor({ state: 'hidden', timeout: 2000 }).catch(() => {
                console.warn('[WizardHelper] Overlay still visible after Escape');
            });
        }
    }
}

/**
 * Wait for a specific dialog to appear and be ready for interaction.
 *
 * @param page - Playwright Page
 * @param dialogName - Accessible name or text content of the dialog
 * @param options - Optional timeout
 */
export async function waitForDialogReady(
    page: Page,
    dialogName: string | RegExp,
    options: { timeout?: number } = {}
): Promise<void> {
    const { timeout = 10000 } = options;

    const dialog = page.getByRole('dialog', { name: dialogName });
    await expect(dialog).toBeVisible({ timeout });

    // Wait for dialog content to be ready (not loading)
    const spinner = dialog.locator('mat-spinner, .loading-spinner');
    await spinner.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {
        // No spinner found or already hidden
    });
}

export async function launchSimulatedExecution(
    page: Page,
    testInfo: TestInfo,
    options?: { protocolName?: string }
): Promise<void> {
    const protocolPage = new ProtocolPage(page, testInfo);
    const wizardPage = new WizardPage(page, testInfo);

    await protocolPage.goto();
    await protocolPage.ensureSimulationMode();
    
    if (options?.protocolName) {
        await protocolPage.selectProtocolByName(options.protocolName);
    } else {
        await protocolPage.selectFirstProtocol();
    }
    await protocolPage.continueFromSelection();
    
    await wizardPage.completeParameterStep();
    await wizardPage.selectFirstCompatibleMachine();
    await wizardPage.waitForAssetsAutoConfigured();
    await wizardPage.advanceDeckSetup();
    await wizardPage.openReviewStep();
    await wizardPage.startExecution();
}
