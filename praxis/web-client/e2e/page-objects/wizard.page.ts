import { expect, Locator, Page } from '@playwright/test';

export class WizardPage {
    private readonly page: Page;
    private readonly parameterStep: Locator;
    private readonly machineStep: Locator;
    private readonly assetsStep: Locator;
    private readonly wellStep: Locator;
    private readonly deckStep: Locator;
    private readonly reviewHeading: Locator;
    private readonly reviewProtocolName: Locator;
    private readonly runProtocolRoot: Locator;

    constructor(page: Page) {
        this.page = page;
        this.parameterStep = page.locator('[data-tour-id="run-step-params"]');
        this.machineStep = page.locator('[data-tour-id="run-step-machine"]');
        this.assetsStep = page.locator('[data-tour-id="run-step-assets"]');
        this.wellStep = page.locator('[data-tour-id="run-step-wells"]');
        this.deckStep = page.locator('[data-tour-id="run-step-deck"]');
        this.reviewHeading = page.locator('h2', { hasText: 'Ready to Launch' });
        this.reviewProtocolName = page.getByTestId('review-protocol-name').first();
        this.runProtocolRoot = page.locator('app-run-protocol').first();
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
            protocolContinue.isEnabled().catch(() => false),
            machineContinue.isEnabled().catch(() => false),
            assetsContinue.isEnabled().catch(() => false),
            deckSkip.isVisible().catch(() => false),
            deckContinue.isEnabled().catch(() => false),
            reviewTab.isEnabled().catch(() => false),
            reviewTab.getAttribute('aria-selected').catch(() => null),
            stepper.getAttribute('ng-reflect-linear').catch(() => null),
            this.page.evaluate(() => {
                const cmp = (window as any).ng?.getComponent?.(document.querySelector('app-run-protocol'));
                return cmp?.modeService?.isBrowserMode?.();
            }).catch((e) => {
                console.log('[Test] Silent catch (isBrowserMode evaluate):', e);
                return null;
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
    }

    async selectFirstCompatibleMachine() {
        await this.machineStep.waitFor({ state: 'visible' });
        const spinner = this.machineStep.locator('mat-spinner');
        await spinner.waitFor({ state: 'detached', timeout: 15000 }).catch((e) => console.log('[Test] Silent catch (Machine step spinner):', e));

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
                    ]).catch((e) => console.log('[Test] Silent catch (Machine options race):', e));

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
            ]).catch((e) => console.log('[Test] Silent catch (Machine cards fallback race):', e));

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
    }

    async completeWellSelectionStep() {
        // Only wait and complete if the step is visible
        if (await this.wellStep.isVisible({ timeout: 5000 }).catch((e) => {
            console.log('[Test] Silent catch (wellStep isVisible):', e);
            return false;
        })) {
            console.log('[Wizard] Completing Well Selection step...');

            // Check if there are "Click to select wells" buttons
            const selectButtons = this.wellStep.getByRole('button', { name: /select wells/i });
            const count = await selectButtons.count();

            for (let i = 0; i < count; i++) {
                const btn = selectButtons.nth(i);
                await btn.click();

                // Dialog should open
                const dialog = this.page.getByRole('dialog').filter({ hasText: /Select Wells/i });
                await dialog.waitFor({ state: 'visible' });

                // Select first available well
                const well = dialog.locator('.well.available').first();
                if (await well.isVisible()) {
                    await well.click();
                }

                // Confirm selection
                await dialog.getByRole('button', { name: /Confirm/i }).click();
                await dialog.waitFor({ state: 'hidden' });
            }

            const continueButton = this.wellStep.getByRole('button', { name: /Continue/i }).first();
            await expect(continueButton).toBeEnabled({ timeout: 5000 });
            await continueButton.click();
        }
    }

    async advanceDeckSetup() {
        await this.deckStep.waitFor({ state: 'visible' });

        // Click Skip Setup if visible
        const skipButton = this.deckStep.getByRole('button', { name: /Skip Setup/i }).first();
        if (await skipButton.isVisible({ timeout: 5000 }).catch((e) => {
            console.log('[Test] Silent catch (skipButton isVisible):', e);
            return false;
        })) {
            await skipButton.click();
        }

        // Click Continue to Review if visible (some flows show this after skip)
        const continueButton = this.deckStep.getByRole('button', { name: /Continue to Review|Continue/i }).first();
        if (await continueButton.isVisible({ timeout: 2000 }).catch((e) => {
            console.log('[Test] Silent catch (continueButton isVisible):', e);
            return false;
        })) {
            await continueButton.click();
        }
        // Don't call markDeckValid() - we've already advanced
    }

    async openReviewStep() {
        const reviewTab = this.page.getByRole('tab', { name: /Review & Run/i }).first();
        await expect(reviewTab).toBeVisible({ timeout: 15000 });

        // Check if we're already on the review step
        const isSelected = await reviewTab.getAttribute('aria-selected');
        if (isSelected === 'true') {
            console.log('[Wizard] Already on review step');
            // Just wait for review content
            await this.reviewHeading.waitFor({ state: 'visible', timeout: 10000 }).catch((e) => {
                console.log('[Test] Silent catch (reviewHeading waitFor):', e);
            });
            return;
        }

        // Need to navigate to review
        await expect(reviewTab).toBeEnabled({ timeout: 15000 });
        await reviewTab.click();
        await this.reviewHeading.waitFor({ state: 'visible', timeout: 10000 });
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
        await Promise.all([
            this.page.waitForURL('**/run/live', { waitUntil: 'domcontentloaded' }),
            startButton.click()
        ]);
    }

    async handleConfigureSimulationDialog(): Promise<boolean> {
        // Check if Configure Simulation dialog is visible
        const dialog = this.page.getByRole('dialog').filter({ hasText: /Configure Simulation|Simulation/i });

        if (await dialog.isVisible({ timeout: 2000 }).catch((e) => {
            console.log('[Test] Silent catch (Simulation dialog isVisible):', e);
            return false;
        })) {
            console.log('[Wizard] Handling Configure Simulation dialog...');

            // Fill instance name if required
            const nameInput = dialog.locator('input[formcontrolname="instanceName"], input[name="name"]');
            if (await nameInput.isVisible({ timeout: 1000 }).catch((e) => {
                console.log('[Test] Silent catch (nameInput isVisible):', e);
                return false;
            })) {
                await nameInput.fill('E2E Simulation');
            }

            // Click create/confirm button
            await dialog.getByRole('button', { name: /Create|Confirm|Continue|OK/i }).first().click();

            // Wait for dialog to close
            await dialog.waitFor({ state: 'hidden', timeout: 5000 });
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

    async selectFirstSimulatedMachine(): Promise<void> {
        const machineCard = this.page
            .locator('app-machine-card')
            .filter({ hasText: /Simulated/i })
            .first();
        await machineCard.click();
        await expect(machineCard).toHaveClass(/border-primary|selected/);
    }

    async selectIncompatibleMachine(): Promise<void> {
        // For negative testing
        const incompatibleCard = this.page
            .locator('app-machine-card')
            .filter({ has: this.page.locator('[data-incompatible="true"]') })
            .first();
        await incompatibleCard.click();
    }

    async verifyContinueEnabled(): Promise<void> {
        const machineStep = this.page.locator(
            '[data-tour-id="run-step-machine"]'
        );
        const continueButton = machineStep.getByRole('button', {
            name: /Continue/i,
        });
        await expect(continueButton).toBeEnabled();
    }

    async verifyMachineSelected(expectedAccessionId: string): Promise<void> {
        const selectedId = await this.page.evaluate(() => {
            const runStepComponent = document.querySelector(
                'app-run-step-machine'
            );
            if (!runStepComponent) return null;
            const component = (window as any).ng.getComponent(runStepComponent);
            return component?.selectedMachine?.machine?.accession_id;
        });
        expect(selectedId).toBe(expectedAccessionId);
    }
}

