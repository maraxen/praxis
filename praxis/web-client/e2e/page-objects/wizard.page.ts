import { expect, Locator, Page } from '@playwright/test';

import { TestInfo } from '@playwright/test';

export class WizardPage {
    private readonly page: Page;
    private readonly testInfo?: TestInfo;
    private readonly parameterStep: Locator;
    private readonly machineStep: Locator;
    private readonly assetsStep: Locator;
    private readonly wellStep: Locator;
    private readonly deckStep: Locator;
    private readonly reviewHeading: Locator;
    private readonly reviewProtocolName: Locator;
    private readonly runProtocolRoot: Locator;

    constructor(page: Page, testInfo?: TestInfo) {
        this.page = page;
        this.testInfo = testInfo;
        this.parameterStep = page.locator('[data-tour-id="run-step-params"]');
        this.machineStep = page.locator('[data-tour-id="run-step-machine"]');
        this.assetsStep = page.locator('[data-tour-id="run-step-assets"]');
        this.wellStep = page.locator('[data-tour-id="run-step-wells"]');
        this.deckStep = page.locator('[data-tour-id="run-step-deck"]');
        this.reviewHeading = page.locator('h2', { hasText: 'Ready to Launch' });
        this.reviewProtocolName = page.getByTestId('review-protocol-name').first();
        this.runProtocolRoot = page.locator('app-run-protocol').first();
    }

    async completeProtocolStep() {
        // Step 1: Select Protocol (should already be selected via query param)
        const protocolStep = this.page.locator('.mat-step-header').filter({ hasText: /Protocol|Select/i }).first();
        const continueButton = this.page.getByRole('button', { name: /Continue/i }).first();
        if (await continueButton.isVisible() && await continueButton.isEnabled()) {
            await continueButton.click();
        }
    }

    async getFormState() {
        const protocolContinue = this.parameterStep.getByRole('button', { name: /Continue/i }).first();
        const machineContinue = this.machineStep.getByRole('button', { name: /Continue/i }).first();
        const assetsContinue = this.assetsStep.getByRole('button', { name: /Continue/i }).first();
        const deckSkip = this.deckStep.getByRole('button', { name: /Skip Setup/i }).first();
        const deckContinue = this.deckStep.getByRole('button', { name: /Continue/i }).last();
        const reviewTab = this.page.getByRole('tab', { name: /Review & Run/i }).first();
        const stepper = this.page.locator('mat-horizontal-stepper').first();

        const [protocolEnabled, machineEnabled, assetsEnabled, deckSkipVisible, deckContinueEnabled, reviewEnabled, reviewSelected, linearAttr, isBrowserMode] = await Promise.all([
            protocolContinue.isEnabled(),
            machineContinue.isEnabled(),
            assetsContinue.isEnabled(),
            deckSkip.isVisible(),
            deckContinue.isEnabled(),
            reviewTab.isEnabled(),
            reviewTab.getAttribute('aria-selected'),
            stepper.getAttribute('ng-reflect-linear'),
            this.page.evaluate(() => {
                const cmp = (window as any).ng?.getComponent?.(document.querySelector('app-run-protocol'));
                return cmp?.modeService?.isBrowserMode?.() ?? null;
            }),
        ]);

        return {
            protocolEnabled,
            machineEnabled,
            assetsEnabled,
            deckSkipVisible,
            deckContinueEnabled,
            reviewEnabled,
            reviewSelected,
            linearAttr,
            isBrowserMode,
        };
    }

    private async markAssetsValid() {
        console.log('[Wizard] Verifying asset selection validity via UI...');
        const continueButton = this.assetsStep.getByRole('button', { name: /Continue/i }).first();
        if (await continueButton.isVisible() && !(await continueButton.isEnabled())) {
            console.warn('[Wizard] Assets not valid via UI, attempting manual selection...');
            await this.autoConfigureAssetsManual();
        }
        await expect(continueButton).toBeEnabled({ timeout: 10000 });
    }

    private async markDeckValid() {
        console.log('[Wizard] Advancing deck setup step...');
        const skipButton = this.deckStep.getByRole('button', { name: /Skip Setup|Continue/i }).first();
        if (await skipButton.isVisible()) {
            await skipButton.click();
        }
    }

    async completeParameterStep() {
        await this.parameterStep.waitFor({ state: 'visible' });
        const continueButton = this.parameterStep.getByRole('button', { name: /Continue/i }).first();
        await expect(continueButton).toBeEnabled();
        await continueButton.click();
        // Wait for transition to Machine step
        const machineHeader = this.page.locator('.mat-step-header').filter({ hasText: /Select Machines/i }).first();
        await expect(machineHeader).toHaveAttribute('aria-selected', 'true', { timeout: 10000 });
    }

    async selectFirstCompatibleMachine() {
        await this.machineStep.waitFor({ state: 'visible' });
        const spinner = this.machineStep.locator('mat-spinner');
        if (await spinner.count() > 0) {
            await expect(spinner).not.toBeVisible({ timeout: 15000 });
        }

        // Target new selector sections first
        const sections = this.machineStep.locator('.machine-arg-section');
        const sectionCount = await sections.count();

        if (sectionCount > 0) {
            console.log(`[Wizard] Found ${sectionCount} machine requirement sections.`);
            for (let i = 0; i < sectionCount; i++) {
                const section = sections.nth(i);
                await section.scrollIntoViewIfNeeded();

                // If not already complete/selected
                const isComplete = await section.evaluate(el => el.classList.contains('complete'));
                if (!isComplete) {
                    await section.click(); // Expand if needed
                    const options = section.locator('.option-card:not(.disabled)');
                    // Wait for options or a "no options" message
                    const noOptions = section.locator('.empty-state, .no-machines-state');
                    await Promise.race([
                        options.first().waitFor({ state: 'visible', timeout: 5000 }),
                        noOptions.first().waitFor({ state: 'visible', timeout: 5000 })
                    ]).catch(() => {
                        // Neither options nor empty state appeared - continue anyway
                    });

                    if (await options.count() > 0) {
                        // Prefer simulation/chatterbox in simulation mode
                        const simulationOption = options.filter({ hasText: /Simulation|Chatterbox|Simulated/i }).first();
                        const target = (await simulationOption.count()) ? simulationOption : options.first();

                        console.log(`[Wizard] Selecting machine option for section ${i}...`);
                        await target.click();
                        await this.handleConfigureSimulationDialog();
                    }
                }
            }
        } else {
            // Fallback: check if we just have a "no machines" state or if continue is enabled
            const noMachines = this.machineStep.locator('.no-machines-state, .empty-state');
            const machineCards = this.machineStep.locator('app-machine-card, .option-card');
            const continueButton = this.machineStep.getByRole('button', { name: /Continue/i }).first();

            await Promise.race([
                machineCards.first().waitFor({ state: 'visible', timeout: 5000 }),
                noMachines.first().waitFor({ state: 'visible', timeout: 5000 }),
                expect(continueButton).toBeEnabled({ timeout: 5000 })
            ]).catch(() => {
                // None of the conditions met - continue anyway
            });

            if (await machineCards.count() > 0) {
                const simulationCard = machineCards.filter({ hasText: /Simulation|Simulated|Chatterbox/i }).first();
                const target = (await simulationCard.count()) ? simulationCard : machineCards.first();
                await target.click();
                await this.handleConfigureSimulationDialog();
            }
        }


        const continueButton = this.machineStep.getByRole('button', { name: /Continue/i }).first();
        await expect(continueButton).toBeEnabled({ timeout: 10000 });
        await continueButton.click();
        // Wait for transition to Assets step
        const assetsHeader = this.page.locator('.mat-step-header').filter({ hasText: /Select Assets/i }).first();
        await expect(assetsHeader).toHaveAttribute('aria-selected', 'true', { timeout: 10000 });
    }

    async selectAssetForRequirement(requirementName: string, assetName: string) {
        await this.assetsStep.waitFor({ state: 'visible' });

        // Find the requirement section/row
        // Note: Selector depends on actual DOM structure. Adjusting based on common patterns or assumptions from previous context.
        // Assuming a list of requirements, each with a selector.
        // If the UI uses distinct cards for requirements:
        const requirementCard = this.assetsStep.locator('.requirement-card, .asset-requirement').filter({ hasText: requirementName });
        await expect(requirementCard).toBeVisible({ timeout: 5000 });

        // Click to open selection if needed (e.g. dropdown or modal)
        // If it's a dropdown:
        const select = requirementCard.locator('mat-select, [role="combobox"]');
        if (await select.isVisible()) {
            await select.click();
            await this.page.getByRole('option', { name: assetName }).click();
        } else {
            // Maybe it's a list of radio buttons or cards inside the requirement block
            const assetOption = requirementCard.locator('.asset-option, .candidate-card').filter({ hasText: assetName });
            await assetOption.click();
        }
    }

    async autoConfigureAssetsManual() {
        await this.assetsStep.waitFor({ state: 'visible' });

        const requirements = this.assetsStep.locator('.requirement-item');
        const count = await requirements.count();

        for (let i = 0; i < count; i++) {
            const req = requirements.nth(i);
            const name = await req.locator('.req-name').innerText().catch((e) => {
                console.log('[Test] Silent catch (Requirement name innerText):', e);
                return 'Unknown';
            });
            const isCompleted = await req.evaluate(el => el.classList.contains('completed') || el.classList.contains('autofilled'));

            if (!isCompleted) {
                console.log(`[Wizard] Manually configuring requirement: ${name}`);

                // Open dropdown/autocomplete
                const input = req.locator('input[placeholder*="Search inventory"]');
                if (await input.isVisible()) {
                    await input.click();

                    // Wait for dropdown options to appear
                    const options = this.page.locator('mat-option');
                    await options.first().waitFor({ state: 'visible', timeout: 5000 }).catch((e) => console.log('[Test] Silent catch (Asset options waitFor):', e));

                    if (await options.count() > 0) {
                        await options.first().click();
                        // Wait for option to be selected
                        await expect(input).not.toHaveValue('', { timeout: 3000 }).catch((e) => console.log('[Test] Silent catch (Input value expect):', e));
                    } else {
                        console.log(`[Wizard] No options found for ${name}`);
                    }
                }
            }
        }
    }

    async waitForAssetsAutoConfigured() {
        await this.assetsStep.waitFor({ state: 'visible' });

        // Try manual config if not ready
        await this.autoConfigureAssetsManual();

        // Wait for the "Continue" button to be enabled
        const continueButton = this.assetsStep.getByRole('button', { name: /Continue/i }).first();
        await expect(continueButton).toBeEnabled({ timeout: 20000 });
        await continueButton.click();
        // Transition might be to Wells or Deck Setup
        console.log('[Wizard] Assets continued, waiting for next step...');
    }

    async completeWellSelectionStep() {
        console.log('[Wizard] Checking for Well Selection step...');

        // Wait for well step header to be selected or at least visible
        const wellHeader = this.page.locator('.mat-step-header').filter({ hasText: /Select Wells/i }).first();
        const wellStepSelected = (await wellHeader.count() > 0)
            ? (await wellHeader.getAttribute('aria-selected')) === 'true'
            : false;

        if (!wellStepSelected) {
            const isVisible = await this.wellStep.isVisible({ timeout: 2000 });
            if (!isVisible) {
                console.log('[Wizard] Well Selection step not active or visible, skipping');
                return;
            }
        }

        console.log('[Wizard] Well Selection step is active, completing...');

        // Select buttons might have labels like "Click to select wells..." or "5 wells selected"
        // Try multiple locators for the well selection buttons
        const selectButtons = this.wellStep.locator('button').filter({
            has: this.page.locator('mat-icon', { hasText: /grid_on/i })
        });

        // Fallback: any button in the well-selection-required area
        const fallbackButtons = this.wellStep.locator('button:has-text("select wells")');

        const effectiveButtons = (await selectButtons.count()) > 0 ? selectButtons : fallbackButtons;

        const count = await effectiveButtons.count();
        console.log(`[Wizard] Found ${count} well selection buttons`);

        for (let i = 0; i < count; i++) {
            const btn = effectiveButtons.nth(i);
            const btnText = await btn.innerText();
            console.log(`[Wizard] Clicking well selection button ${i}: "${btnText}"`);
            await btn.click();

            // Dialog should open
            const dialog = this.page.getByRole('dialog').filter({ hasText: /Select Wells/i });
            await dialog.waitFor({ state: 'visible', timeout: 10000 });

            // Select first well (A1)
            // The well buttons in the dialog might have different classes
            const well = dialog.locator('.well-btn, .well-item, [data-testid="well-cell"]').first();
            await well.waitFor({ state: 'visible', timeout: 5000 });
            await well.click();

            // Confirm selection
            const confirmBtn = dialog.getByRole('button', { name: /Confirm Selection|Confirm|Select|OK/i }).last();
            await expect(confirmBtn).toBeEnabled();
            await confirmBtn.click();

            await dialog.waitFor({ state: 'hidden', timeout: 10000 });
        }

        // Wait for validation to propagate and "Continue" to be enabled
        const continueButton = this.wellStep.getByRole('button', { name: /^Continue$/i }).first();

        // If "Continue" is not enabled, maybe there's a problem
        try {
            await expect(continueButton).toBeEnabled({ timeout: 10000 });
        } catch (e) {
            console.log('[Wizard] Continue button not enabled on Well Step. Validation failed?');
            // Log what we see
            const html = await this.wellStep.innerHTML();
            console.log('[Wizard] Well Step HTML:', html);
            throw e;
        }

        console.log('[Wizard] Clicking Well Step Continue button...');
        await continueButton.click();

        // Wait for transition to next step
        await expect(wellHeader).toHaveAttribute('aria-selected', 'false', { timeout: 10000 });
    }

    async advanceDeckSetup() {
        console.log('[Wizard] Advancing Deck Setup...');

        const deckHeader = this.page.locator('.mat-step-header').filter({ hasText: /Deck/i }).first();

        // Check if Deck Setup step even exists (it might not for some protocols)
        if (await deckHeader.count() === 0) {
            console.log('[Wizard] No Deck Setup step found, skipping');
            return;
        }

        // Check if already on Deck Setup
        const isSelected = await deckHeader.getAttribute('aria-selected');
        if (isSelected !== 'true') {
            console.log('[Wizard] Not yet on Deck Setup, attempting to navigate...');

            // Try clicking the Deck Setup header directly to advance
            const isDeckDisabled = await deckHeader.getAttribute('aria-disabled');
            if (isDeckDisabled !== 'true') {
                await deckHeader.click();
                await this.page.waitForTimeout(500);
            } else {
                // Deck is disabled — might need to advance from current step first
                // Find any Continue button in the current active step
                const activeContent = this.page.locator('.mat-horizontal-stepper-content[style*="visibility: visible"], .mat-horizontal-stepper-content-current').first();
                const continueBtn = activeContent.getByRole('button', { name: /Continue/i }).first();
                if (await continueBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
                    await continueBtn.click();
                    await this.page.waitForTimeout(500);
                }
            }

            // Wait for Deck Setup to become selected (with retry)
            try {
                await expect(deckHeader).toHaveAttribute('aria-selected', 'true', { timeout: 15000 });
            } catch {
                console.log('[Wizard] Deck Setup still not selected after navigation attempt, trying direct click...');
                await deckHeader.click({ force: true });
                await expect(deckHeader).toHaveAttribute('aria-selected', 'true', { timeout: 10000 });
            }
        }

        console.log('[Wizard] On Deck Setup step');

        // Click Skip Setup if visible
        const skipButton = this.deckStep.getByRole('button', { name: /Skip Setup/i }).first();
        if (await skipButton.isVisible({ timeout: 5000 }).catch(() => false)) {
            await skipButton.click();
        }

        // Click Continue to Review if visible (some flows show this after skip)
        const continueButton = this.deckStep.getByRole('button', { name: /Continue to Review|Continue/i }).first();
        if (await continueButton.isVisible({ timeout: 2000 }).catch(() => false)) {
            await continueButton.click();
        }
    }

    async openReviewStep() {
        // MDC Stepper uses .mat-step-header instead of role="tab" in some versions
        const reviewTab = this.page.locator('.mat-step-header').filter({ hasText: /Review & Run/i }).first();
        await expect(reviewTab).toBeVisible({ timeout: 15000 });

        // Check if we're already on the review step
        const isSelected = await reviewTab.getAttribute('aria-selected');
        if (isSelected === 'true') {
            console.log('[Wizard] Already on review step');
            if (await this.reviewHeading.count() > 0) {
                await expect(this.reviewHeading).toBeVisible({ timeout: 10000 });
            }
            return;
        }

        // Need to navigate to review
        await expect(reviewTab).toBeEnabled({ timeout: 20000 });
        await reviewTab.click();
        await this.reviewHeading.waitFor({ state: 'visible', timeout: 15000 });
    }

    async assertReviewSummary(protocolName: string) {
        try {
            await expect(this.reviewProtocolName).toHaveText(protocolName, { timeout: 15000 });
        } catch (e) {
            const text = await this.reviewProtocolName.innerText().catch((e) => {
                console.log('[Test] Silent catch (reviewProtocolName innerText):', e);
                return 'NULL';
            });
            const html = await this.page.locator('[data-tour-id="run-step-ready"], .mat-step-content').last().innerHTML().catch((e) => {
                console.log('[Test] Silent catch (Review step innerHTML):', e);
                return 'NULL';
            });
            console.error(`[Wizard] Review protocol name mismatch. Expected: "${protocolName}", Found: "${text}"`);
            console.error(`[Wizard] Review step HTML: ${html}`);
            throw e;
        }
    }

    async waitForStartReady(): Promise<Locator> {
        const startButton = this.page.getByRole('button', { name: /Start Execution/i }).first();
        await expect(startButton).toBeEnabled({ timeout: 20000 });
        return startButton;
    }

    async startExecution() {
        const startButton = await this.waitForStartReady();
        console.log('[Wizard] Clicking Start Execution button...');
        await startButton.click();

        console.log('[Wizard] Waiting for monitor page navigation (handling potential Unsaved Changes dialog)...');

        // The "Unsaved Changes" canDeactivate guard dialog can appear at any point during navigation.
        // Handle it concurrently with the URL wait using a polling approach.
        const leaveButton = this.page.getByRole('button', { name: /Leave/i });

        // Set up a background watcher for the dialog
        const dialogDismisser = (async () => {
            for (let i = 0; i < 30; i++) {
                // Use page.evaluate to directly search the CDK overlay DOM
                const found = await this.page.evaluate(() => {
                    const overlay = document.querySelector('.cdk-overlay-container');
                    if (!overlay) return false;
                    const buttons = overlay.querySelectorAll('button');
                    for (const btn of buttons) {
                        if (btn.textContent?.trim().toLowerCase() === 'leave') {
                            (btn as HTMLButtonElement).click();
                            return true;
                        }
                    }
                    return false;
                }).catch(() => false);

                if (found) {
                    console.log('[Wizard] Dismissed "Unsaved Changes" dialog via CDK overlay');
                    return;
                }
                await this.page.waitForTimeout(500);
            }
        })();

        // Wait for monitor URL (this will resolve after dialog is dismissed)
        await Promise.all([
            dialogDismisser,
            this.page.waitForURL(/\/app\/monitor\/[a-f0-9-]+/, {
                waitUntil: 'domcontentloaded',
                timeout: 30000
            })
        ]);

        console.log('[Wizard] Successfully navigated to monitor page:', this.page.url());
    }

    async handleConfigureSimulationDialog(): Promise<boolean> {
        // Check if Configure Simulation dialog is visible
        const dialog = this.page.getByRole('dialog').filter({ hasText: /Configure Simulation|Simulation/i });

        const dialogVisible = await dialog.isVisible({ timeout: 2000 });
        if (dialogVisible) {
            console.log('[Wizard] Handling Configure Simulation dialog...');

            // Fill instance name if required
            const nameInput = dialog.locator('input[formcontrolname="instanceName"], input[name="name"]');
            if (await nameInput.count() > 0 && await nameInput.isVisible()) {
                await nameInput.fill('E2E Simulation');
            }

            // Click create/confirm button
            await dialog.getByRole('button', { name: /Create|Confirm|Continue|OK/i }).first().click();

            // Wait for dialog to close
            await expect(dialog).not.toBeVisible({ timeout: 5000 });
            return true;
        }
        return false;
    }

    async verifyMachineStepVisible(): Promise<void> {
        const machineStep = this.page.locator(
            '[data-tour-id="run-step-machine"]'
        );
        await expect(machineStep).toBeVisible();
        await expect(
            this.page.getByText(/Select Execution Machine/i)
        ).toBeVisible();
    }

    /**
     * Select a simulated backend option-card in MachineArgumentSelectorComponent.
     * The component renders .option-card divs inside accordion panels,
     * with simulation backends having .type-badge.sim containing "Sim".
     */
    async selectFirstSimulatedMachine(): Promise<void> {
        const selector = this.page.locator('app-machine-argument-selector');
        await expect(selector).toBeVisible({ timeout: 15000 });

        // Target option-cards that have a "Sim" badge (simulator backends)
        const simCard = selector
            .locator('.option-card')
            .filter({ hasText: /Sim/ })
            .filter({ hasNot: this.page.locator('.disabled') })
            .first();
        await expect(simCard).toBeVisible({ timeout: 10000 });

        // 3-tier click pattern
        await simCard.evaluate((el: HTMLElement) => {
            el.scrollIntoView({ block: 'center', behavior: 'instant' });
            el.click();
        });

        try {
            await expect(simCard).toHaveClass(/selected/, { timeout: 3000 });
            return;
        } catch { /* Tier 2 fallback */ }

        await simCard.click({ force: true, delay: 100 });
        await expect(simCard).toHaveClass(/selected/, { timeout: 5000 });
    }

    async selectIncompatibleMachine(): Promise<void> {
        const selector = this.page.locator('app-machine-argument-selector');
        // Target option-cards that have .disabled class (incompatible mode)
        const incompatibleCard = selector
            .locator('.option-card.disabled')
            .first();
        await expect(incompatibleCard).toBeVisible({ timeout: 10000 });
        // Force click — disabled cards have pointer-events: none
        await incompatibleCard.click({ force: true });
    }

    async verifyContinueEnabled(): Promise<void> {
        const machineStep = this.page.locator(
            '[data-tour-id="run-step-machine"]'
        );
        const continueButton = machineStep.getByRole('button', {
            name: /Continue/i,
        });
        await expect(continueButton).toBeEnabled({ timeout: 10000 });
    }

    /**
     * Asserts that the wizard is currently on the expected step.
     * @param stepId Identifier like 'protocol', 'params', 'machine', 'assets', 'wells', 'deck', 'review'
     */
    async assertOnStep(stepId: string): Promise<void> {
        const stepMap: Record<string, RegExp> = {
            'protocol': /Protocol|Select/i,
            'params': /Param|Config/i,
            'machine': /Machine/i,
            'assets': /Asset/i,
            'wells': /Well/i,
            'deck': /Deck/i,
            'review': /Review/i,
        };
        const label = stepMap[stepId] || new RegExp(stepId, 'i');
        await expect(this.page.getByRole('tab', { selected: true })).toContainText(label);
    }

    /**
     * Verify a machine selection was registered by checking for .selected card
     * or check_circle icon in the accordion header.
     */
    async verifyMachineSelected(expectedName?: string): Promise<void> {
        const selector = this.page.locator('app-machine-argument-selector');
        // A valid selection shows check_circle in the panel header
        const selectedIndicator = selector.locator('.status-indicator.complete');
        await expect(selectedIndicator.first()).toBeVisible({ timeout: 5000 });

        if (expectedName) {
            // Verify the selection summary shows the expected name
            await expect(selector.locator('.selection-summary')).toContainText(expectedName);
        }
    }
}
