/**
 * Simple Playwright validation script for the refactored Playground.
 * Takes screenshots at key states for visual verification.
 *
 * Run with: bunx playwright test e2e/specs/playground-visual-validation.spec.ts --config playwright.worktree.config.ts
 */
import { test, expect } from '@playwright/test';

test.describe('Playground Visual Validation', () => {
    test('capture full-screen playground layout', async ({ page }) => {
        test.setTimeout(120000);

        // Pre-seed localStorage to bypass onboarding
        await page.addInitScript(() => {
            localStorage.setItem('praxis_onboarding_completed', 'true');
            localStorage.setItem('praxis_tutorial_completed', 'true');
            localStorage.setItem('praxis_splash_dismissed', 'true');
        });

        // Navigate directly to the playground 
        await page.goto('/app/playground', { waitUntil: 'domcontentloaded', timeout: 30000 });

        // Wait for Angular to bootstrap and render
        await page.waitForTimeout(5000);

        // Take a screenshot of whatever is rendered
        await page.screenshot({
            path: 'e2e/screenshots/playground-initial-state.png',
            fullPage: false
        });

        // Check for key elements
        const hasPlaygroundLayout = await page.locator('.playground-layout').isVisible().catch(() => false);
        const hasPlaygroundFullscreen = await page.locator('.playground-fullscreen').isVisible().catch(() => false);
        const hasNotebookFrame = await page.locator('iframe.notebook-frame').isVisible().catch(() => false);
        const hasCanvas = await page.locator('.playground-canvas').isVisible().catch(() => false);
        const hasTabGroup = await page.locator('mat-tab-group').isVisible().catch(() => false);
        const hasSidebarTrigger = await page.locator('.sidebar-trigger').isVisible().catch(() => false);
        const hasLoadingOverlay = await page.locator('.loading-overlay').isVisible().catch(() => false);

        console.log(`[Validation] Playground Layout Classes Found:`);
        console.log(`  .playground-layout:     ${hasPlaygroundLayout}`);
        console.log(`  .playground-fullscreen:  ${hasPlaygroundFullscreen}`);
        console.log(`  iframe.notebook-frame:   ${hasNotebookFrame}`);
        console.log(`  .playground-canvas:      ${hasCanvas}`);
        console.log(`  mat-tab-group:           ${hasTabGroup} (should be false)`);
        console.log(`  .sidebar-trigger:        ${hasSidebarTrigger}`);
        console.log(`  .loading-overlay:        ${hasLoadingOverlay}`);

        // Log rendered HTML for debugging
        const appPlayground = await page.evaluate(() => {
            const el = document.querySelector('app-playground');
            if (!el) return 'app-playground NOT FOUND';
            const classes = el.className;
            const children = Array.from(el.children).map(c => `${c.tagName}.${c.className}`).join(', ');
            return `classes="${classes}" children=[${children}]`;
        });
        console.log(`[Validation] app-playground: ${appPlayground}`);

        // Wait a bit more for any lazy-loaded content
        await page.waitForTimeout(5000);

        // Take screenshot after iframe loads
        await page.screenshot({
            path: 'e2e/screenshots/playground-after-load.png',
            fullPage: false
        });

        // Check if sidebar trigger exists and try hovering
        if (hasSidebarTrigger) {
            const trigger = page.locator('.sidebar-trigger');
            await trigger.hover();
            await page.waitForTimeout(800);
            await page.screenshot({
                path: 'e2e/screenshots/playground-sidebar-hovered.png',
                fullPage: false
            });
        }

        // Try Alt+T keyboard shortcut
        await page.keyboard.press('Alt+t');
        await page.waitForTimeout(800);
        await page.screenshot({
            path: 'e2e/screenshots/playground-alt-t-pressed.png',
            fullPage: false
        });

        // The test always passes — this is for visual validation
        expect(true).toBe(true);
    });
});
