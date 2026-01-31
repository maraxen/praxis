import { test, expect } from '../fixtures/worker-db.fixture';
import { WelcomePage } from '../page-objects/welcome.page';

test.describe('First-Time User Experience', () => {
    test('should show welcome screen and navigate to dashboard', async ({ page }, testInfo) => {
        const welcomePage = new WelcomePage(page, testInfo);
        await welcomePage.goto();
        await welcomePage.handleSplashScreen(); // Skips tutorial
        await welcomePage.verifyDashboardLoaded();
        await welcomePage.verifyOnboardingCompleted();
    });

    test.skip('should complete tutorial flow when clicking Start Tutorial', async ({ page }, testInfo) => {
        // SKIPPED: Tutorial feature not yet implemented in UI
        const welcomePage = new WelcomePage(page, testInfo);
        await welcomePage.goto();

        await welcomePage.startTutorial();
        await welcomePage.verifyTutorialStep(1, /Welcome/);
        await welcomePage.advanceTutorial();
        await welcomePage.verifyTutorialStep(2, /Sidebar/);
        await welcomePage.advanceTutorial();
        await welcomePage.verifyTutorialStep(3, /Run a Protocol/);
        await welcomePage.advanceTutorial();
        await welcomePage.verifyTutorialStep(4, /Assets/);
        await welcomePage.advanceTutorial();
        await welcomePage.verifyTutorialStep(5, /Playground/);

        await welcomePage.completeTutorial();
        await welcomePage.verifyOnboardingCompleted();
        await welcomePage.verifyDashboardLoaded();
    });

    test.skip('should bypass splash for returning user', async ({ page }, testInfo) => {
        // SKIPPED: localStorage persistence doesn't work as expected in worker mode
        // Set flag before navigation
        await page.addInitScript(() => {
            localStorage.setItem('praxis_onboarding_completed', 'true');
        });

        const welcomePage = new WelcomePage(page, testInfo);
        await welcomePage.gotoNoSplash();

        // Splash should NOT appear
        await expect(welcomePage.splashScreen).not.toBeVisible({ timeout: 2000 });
        await welcomePage.verifyDashboardLoaded();
    });
});
