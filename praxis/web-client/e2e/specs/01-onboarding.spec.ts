import { test, expect } from '../fixtures/worker-db.fixture';
import { WelcomePage } from '../page-objects/welcome.page';
import { TutorialPage } from '../page-objects/tutorial.page';

test.describe('First-Time User Experience', () => {
    test('should show welcome screen and navigate to dashboard', async ({ page }, testInfo) => {
        const welcomePage = new WelcomePage(page, testInfo);
        await welcomePage.goto();
        await welcomePage.handleSplashScreen(); // Skips tutorial
        await welcomePage.verifyDashboardLoaded();
        await welcomePage.verifyOnboardingCompleted();
    });

    test('should complete tutorial flow when clicking Start Tutorial', async ({ page }, testInfo) => {
        const welcomePage = new WelcomePage(page, testInfo);
        const tutorialPage = new TutorialPage(page);

        await welcomePage.goto();
        
        // Click Start Tutorial on the welcome dialog
        await welcomePage.startTutorial();

        // Step through tutorial
        // 1. Intro step
        await tutorialPage.verifyStepVisible(/This is your dashboard overview/i);
        await tutorialPage.startTour();
      
        // 2. Next step (Asset Management)
        await tutorialPage.verifyStepVisible(/Click here to manage your lab inventory/i);
        await tutorialPage.skipSection();
        
        // 3. Next step (Protocols)
        await tutorialPage.verifyStepVisible(/Click here to access your protocol library/i);
        await tutorialPage.skipSection();

        // 4. Next step (Run)
        await tutorialPage.verifyStepVisible(/Ready to experiment?/i);
        await tutorialPage.skipSection();

        // 5. Next step (Playground)
        await tutorialPage.verifyStepVisible(/For direct control and testing/i);
        await tutorialPage.skipSection();

        // 6. Next step (Settings Navigation)
        await tutorialPage.verifyStepVisible(/look at your preferences/i);
        await tutorialPage.next();

        // 7. Last step (Finish)
        await tutorialPage.verifyStepVisible(/preferences anytime/i);
        await tutorialPage.finish();

        await tutorialPage.verifyClosed();
    });

    test('should bypass splash for returning user', async ({ page }, testInfo) => {
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
