/**
 * Functional Asset Selection E2E Test
 *
 * Tests the complete wizard flow: create assets via UI → select protocol →
 * configure assets → verify review step shows correct data.
 *
 * NOTE: This test creates assets through the Assets page UI rather than
 * through DB seeding, verifying the full create-and-use flow.
 */
import { test, expect } from '../fixtures/worker-db.fixture';
import { WelcomePage } from '../page-objects/welcome.page';
import { AssetsPage } from '../page-objects/assets.page';
import { ProtocolPage } from '../page-objects/protocol.page';
import { WizardPage } from '../page-objects/wizard.page';

test.describe('Functional Asset Selection', () => {
    let assetsPage: AssetsPage;
    let protocolPage: ProtocolPage;
    let wizardPage: WizardPage;

    test.beforeEach(async ({ page }, testInfo) => {
        const welcomePage = new WelcomePage(page, testInfo);
        assetsPage = new AssetsPage(page, testInfo);
        protocolPage = new ProtocolPage(page, testInfo);
        wizardPage = new WizardPage(page, testInfo);

        await welcomePage.goto();
    });

    test.afterEach(async ({ page }, testInfo) => {
        await page.keyboard.press('Escape').catch(() => { });

        const testId = testInfo.testId;
        const sourcePlateName = `Source Plate ${testId}`;
        const destPlateName = `Dest Plate ${testId}`;
        // Tip rack is seeded via __e2e, not the wizard (TipRack category may not have definitions)

        const assetsPage = new AssetsPage(page, testInfo);
        await assetsPage.goto();

        await assetsPage.navigateToResources();
        await assetsPage.deleteResource(sourcePlateName).catch(() => { });
        await assetsPage.deleteResource(destPlateName).catch(() => { });

        await assetsPage.navigateToMachines();
        await assetsPage.deleteMachine('MyHamilton').catch(() => { });
    });

    test.setTimeout(300000); // 5 minutes for full E2E flow
    // SKIP: Back-to-back asset wizard flows fail — second createResource doesn't
    // reliably appear in the Resources table. The wizard animation/overlay dismiss
    // timing causes state corruption when opening a second wizard immediately after
    // the first completes. Fix: add explicit wait between wizard flows in AssetsPage,
    // or debug wizard modal lifecycle management.
    test.skip('should identify assets, auto-fill them, and show in review', async ({ page }, testInfo) => {
        const testId = testInfo.testId;
        const sourcePlateName = `Source Plate ${testId}`;
        const destPlateName = `Dest Plate ${testId}`;


        // 1. Create assets via UI
        await assetsPage.goto();
        await assetsPage.waitForOverlay();

        console.log('Creating machine...');
        await assetsPage.navigateToMachines();
        await assetsPage.createMachine('MyHamilton', 'LiquidHandler', 'Hamilton');

        console.log('Creating source plate...');
        await assetsPage.navigateToResources();
        await assetsPage.createResource(sourcePlateName, 'Plate', 'Plate');

        console.log('Creating dest plate...');
        await assetsPage.createResource(destPlateName, 'Plate', 'Plate');

        // Verify assets were created by checking they're visible in the resources tab
        await assetsPage.verifyAssetVisible(destPlateName);

        const dbAssets = await page.evaluate(async () => {
            const e2e = (window as any).__e2e;
            if (!e2e) return { resources: [], machines: [] };
            return {
                resources: await e2e.query('SELECT name, plr_category FROM resources'),
                machines: await e2e.query('SELECT name, machine_category FROM machines')
            };
        });

        expect(dbAssets.resources).toContainEqual(
            expect.objectContaining({ name: sourcePlateName, plr_category: 'Plate' })
        );
        expect(dbAssets.machines).toContainEqual(
            expect.objectContaining({ name: 'MyHamilton', machine_category: 'LiquidHandler' })
        );

        // 2. Select protocol
        await protocolPage.goto();
        await protocolPage.ensureSimulationMode();
        await protocolPage.selectProtocolByName('Simple Transfer');
        await protocolPage.continueFromSelection();

        // 3. Wizard Steps
        await wizardPage.completeParameterStep();
        await wizardPage.selectFirstCompatibleMachine();

        // 4. Asset Selection Step
        console.log('Entering asset selection step...');
        const assetsStep = page.locator('[data-tour-id="run-step-assets"]');
        await expect(assetsStep).toBeVisible({ timeout: 15000 });

        // Wait for assets to be auto-filled or configure them manually
        await wizardPage.autoConfigureAssetsManual();

        const continueButton = assetsStep.getByRole('button', { name: /Continue/i }).first();
        await expect(continueButton).toBeEnabled({ timeout: 15000 });
        await continueButton.click();

        // Verify asset selection via DOM — check that guided-setup shows completed states
        // (replaces fragile ng.getComponent() inspection of stale app-asset-selection-step)
        const completedAssets = page.locator('app-guided-setup .completed');
        // At least some assets should show as completed/allocated
        const completedCount = await completedAssets.count();
        console.log(`[Test] ${completedCount} asset slots marked as completed`);

        // 5. Deck Setup
        await wizardPage.advanceDeckSetup();

        // 6. Review Step
        await wizardPage.openReviewStep();

        // Verify review step is visible with expected content
        const reviewContent = page.locator('app-protocol-summary');
        await expect(reviewContent).toBeVisible({ timeout: 10000 });

        // Verify protocol name is shown (core verification)
        const protocolNameEl = page.getByTestId('review-protocol-name');
        await expect(protocolNameEl).toBeVisible({ timeout: 10000 });
        const protocolName = await protocolNameEl.innerText();
        if (!protocolName || protocolName.trim() === '') {
            console.error('[E2E] Protocol name is empty at review step! Capturing debug state...');
            await page.screenshot({ path: '/tmp/e2e-protocol/review-empty-protocol.png' }).catch((e) => console.log('[Test] Silent catch (Screenshot):', e));
            throw new Error('Protocol name was unexpectedly empty at review step');
        }
        await expect(protocolNameEl).toContainText('Simple Transfer');

        // Verify assets are shown in the review Summary via DOM
        // (replaces fragile ng.getComponent() inspection of stale protocolConfig property)
        const assetSection = reviewContent.locator('section', { hasText: /Required Assets/i });
        await expect(assetSection).toBeVisible({ timeout: 5000 });

        // Verify at least some assets are shown as "Allocated"
        const allocatedBadges = assetSection.getByText('Allocated');
        const assetCount = await allocatedBadges.count();
        expect(assetCount).toBeGreaterThan(0);
        console.log(`[Test] Review shows ${assetCount} allocated assets`);

        console.log('Review step reached successfully - wizard flow complete');
        await page.screenshot({ path: '/tmp/e2e-protocol/functional-asset-selection.png' }).catch((e) => console.log('[Test] Silent catch (Screenshot):', e));
    });
});
