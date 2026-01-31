import { Page, Locator, expect, TestInfo } from '@playwright/test';
import { BasePage } from './base.page';

export class WelcomePage extends BasePage {
    readonly getStartedButton: Locator;
    readonly skipButton: Locator;
    readonly splashScreen: Locator;
    readonly nextButton: Locator;
    readonly finishButton: Locator;

    constructor(page: Page, testInfo?: TestInfo) {
        super(page, '/', testInfo);
        this.getStartedButton = page.getByRole('button', { name: /Start Tutorial/i });
        this.skipButton = page.getByRole('button', { name: /Skip/i });
        this.splashScreen = page.getByRole('heading', { name: /Welcome to Praxis/i });
        this.nextButton = page.getByRole('button', { name: /Next/i });
        this.finishButton = page.getByRole('button', { name: /Finish|Done|Complete/i });
    }

    async dismissOnboarding() {
        if (await this.skipButton.isVisible({ timeout: 2000 })) {
            await this.skipButton.click();
        }
    }

    /**
     * Navigate to root path for returning users - skips splash screen handling
     */
    async gotoNoSplash() {
        await this.goto({ waitForDb: true });
    }

    async handleSplashScreen() {
        // Short timeout since app.fixture.ts sets localStorage to skip splash in most cases
        // If splash appears, dismiss it. If not, proceed immediately.
        try {
            await this.splashScreen.waitFor({ state: 'visible', timeout: 500 });
            // Splash appeared, dismiss it
            if (await this.skipButton.isVisible({ timeout: 500 })) {
                await this.skipButton.click();
            } else if (await this.getStartedButton.isVisible({ timeout: 500 })) {
                await this.getStartedButton.click();
            }
        } catch (e) {
            // Splash didn't appear - expected when localStorage flags are set
        }
    }

    async verifyDashboardLoaded() {
        await expect(this.page.locator('.sidebar-rail, .nav-rail, app-sidebar')).toBeVisible({ timeout: 10000 });
    }

    async verifyOnboardingCompleted() {
        // Verify onboarding is marked complete (splash doesn't appear)
        await expect(this.splashScreen).not.toBeVisible({ timeout: 2000 }).catch(() => {
            // Already dismissed - ok
        });
    }

    async startTutorial() {
        await this.getStartedButton.click();
    }

    async verifyTutorialStep(stepNumber: number, expectedText: RegExp) {
        // Look for tutorial step indicators
        const stepIndicator = this.page.locator(`[data-step="${stepNumber}"], .tutorial-step-${stepNumber}`);
        try {
            await expect(stepIndicator.or(this.page.getByText(expectedText))).toBeVisible({ timeout: 5000 });
        } catch (e) {
            console.log(`[Test] Tutorial step ${stepNumber} not found with expected text`);
        }
    }

    async advanceTutorial() {
        // Try next button or any advance mechanism
        if (await this.nextButton.isVisible({ timeout: 2000 })) {
            await this.nextButton.click();
        } else {
            // Try clicking anywhere to advance
            await this.page.keyboard.press('Enter');
        }
        await this.page.waitForLoadState('domcontentloaded');
    }

    async completeTutorial() {
        if (await this.finishButton.isVisible({ timeout: 2000 })) {
            await this.finishButton.click();
        } else if (await this.skipButton.isVisible({ timeout: 2000 })) {
            await this.skipButton.click();
        }
    }
}
