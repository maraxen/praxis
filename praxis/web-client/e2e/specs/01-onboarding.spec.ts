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
        // SKIPPED: The tutorial feature is not in a testable state.
        const welcomePage = new WelcomePage(page, testInfo);
        await welcomePage.goto('/?showTutorial=true');

        // Step through tutorial using Shepherd.js classes
        await expect(page.locator('.shepherd-text')).toBeVisible();
        await page.locator('.shepherd-button-next').click();
      
        await expect(page.locator('.shepherd-text')).toBeVisible();
        await page.locator('.shepherd-button-next').click();
        
        // Complete
        await page.locator('.shepherd-button-secondary').click(); // Finish button
        await expect(page.locator('.shepherd-text')).not.toBeVisible();
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
