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
        wizardPage = new WizardPage(page);

        await welcomePage.goto();
        await welcomePage.handleSplashScreen();
    });

    test.afterEach(async ({ page }, testInfo) => {
        await page.keyboard.press('Escape').catch(() => {});

        const testId = testInfo.testId;
        const sourcePlateName = `Source Plate ${testId}`;
        const destPlateName = `Dest Plate ${testId}`;
        const tipRackName = `Tip Rack ${testId}`;

        const assetsPage = new AssetsPage(page, testInfo);
        await assetsPage.goto();

        await assetsPage.navigateToResources();
        await assetsPage.deleteResource(sourcePlateName).catch(() => {});
        await assetsPage.deleteResource(destPlateName).catch(() => {});
        await assetsPage.deleteResource(tipRackName).catch(() => {});

        await assetsPage.navigateToMachines();
        await assetsPage.deleteMachine('MyHamilton').catch(() => {});
    });

    test.setTimeout(300000); // 5 minutes for full E2E flow
    test('should identify assets, auto-fill them, and show in review', async ({ page }, testInfo) => {
        const testId = testInfo.testId;
        const sourcePlateName = `Source Plate ${testId}`;
        const destPlateName = `Dest Plate ${testId}`;
        const tipRackName = `Tip Rack ${testId}`;

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

        console.log('Creating tip rack...');
        await assetsPage.createResource(tipRackName, 'TipRack', 'TipRack');

        // Verify assets were created by checking they're visible in the resources tab
        await assetsPage.verifyAssetVisible(tipRackName);

        const dbAssets = await page.evaluate(async () => {
            const db = (window as any).sqliteService;
            const resources = await db.query('SELECT name, category FROM resources');
            const machines = await db.query('SELECT name, driver_type FROM machines');
            return { resources, machines };
        });

        expect(dbAssets.resources).toContainEqual(
            expect.objectContaining({ name: sourcePlateName, category: 'Plate' })
        );
        expect(dbAssets.machines).toContainEqual(
            expect.objectContaining({ name: 'MyHamilton', driver_type: 'Hamilton' })
        );

        // 2. Select protocol
        await protocolPage.goto();
        await protocolPage.ensureSimulationMode();
        await protocolPage.selectProtocolByName('Simple Transfer');
        await protocolPage.continueFromSelection();

        // 3. Wizard Steps
        await wizardPage.completeParameterStep();
        await wizardPage.selectFirstCompatibleMachine();

        // 4. Asset Selection Step (NO STUB)
        console.log('Entering asset selection step...');
        const assetsStep = page.locator('[data-tour-id="run-step-assets"]');
        await expect(assetsStep).toBeVisible({ timeout: 15000 });

        // Wait for auto-fill to happen
        // Wait for assets to be auto-filled or configure them manually
        await wizardPage.autoConfigureAssetsManual();

        const continueButton = assetsStep.getByRole('button', { name: /Continue/i }).first();
        await expect(continueButton).toBeEnabled({ timeout: 15000 });
        await continueButton.click();

        const assetState = await page.evaluate(() => {
            const cmp = (window as any).ng?.getComponent?.(
                document.querySelector('app-asset-selection-step')
            );
            return cmp?.selectedAssets;
        });
        expect(assetState).toHaveProperty('source_plate');
        expect(assetState).toHaveProperty('dest_plate');
        expect(assetState).toHaveProperty('tip_rack');

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

        const reviewState = await page.evaluate(() => {
            const cmp = (window as any).ng?.getComponent?.(
                document.querySelector('app-protocol-summary')
            );
            return cmp?.protocolConfig;
        });
        expect(reviewState.protocolName).toBe('Simple Transfer');
        expect(reviewState.assets).toHaveLength(3);

        console.log('Review step reached successfully - wizard flow complete');

        await page.screenshot({ path: '/tmp/e2e-protocol/functional-asset-selection.png' }).catch((e) => console.log('[Test] Silent catch (Screenshot):', e));
    });
});
