import { test, expect } from '@playwright/test';
import { WizardPage } from '../page-objects/wizard.page';

/**
 * Advanced Protocol Workflow E2E
 * 
 * This test verifies the complex multi-step protocol execution flow in browser mode.
 * It covers protocol selection, parameter configuration, machine selection, 
 * asset mapping, and execution launch.
 */
test.describe('Advanced Protocol Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // 300s timeout to allow for Pyodide/WASM bootstrap
    test.setTimeout(300000);

    // Enable browser mode and bypass onboarding/splash
    await page.addInitScript(() => {
      localStorage.setItem('praxis_mode_override', 'browser');
      localStorage.setItem('praxis_onboarding_finished', 'true');
      localStorage.setItem('praxis_splash_finished', 'true');
    });
    
    // Wait for the app to load and DB to hydrate
    await page.goto('/app/home');
    await page.waitForSelector('app-root');
    // Allow extra time for SQLite/WASM hydration
    await page.waitForTimeout(10000);
  });

  test('should complete complex protocol wizard flow', async ({ page }) => {
    const wizard = new WizardPage(page);
    
    console.log('[Test] Navigating to Protocol Execution...');
    await page.goto('/app/run');
    
    // Wait for protocol cards to load
    await expect(page.locator('app-protocol-card')).not.toHaveCount(0, { timeout: 60000 });
    
    // Select protocol
    const targetProtocol = 'Simple Transfer';
    console.log(`[Test] Selecting protocol: ${targetProtocol}`);
    
    const card = page.locator('app-protocol-card').filter({ hasText: targetProtocol }).first();
    await card.scrollIntoViewIfNeeded();
    await card.click({ force: true });
    
    // Wait for selection to reflect in UI
    await expect(page.locator('h2').filter({ hasText: targetProtocol })).toBeVisible({ timeout: 20000 });
    
    // Step 1: Protocol Selection Continue
    console.log('[Step 1] Clicking Continue...');
    const step1Continue = page.locator('button').filter({ hasText: /Continue/i }).filter({ visible: true }).first();
    await expect(step1Continue).toBeVisible({ timeout: 20000 });
    await step1Continue.click({ force: true });

    // Step 2: Configure Parameters
    console.log('[Step 2] Parameter Configuration');
    await wizard.completeParameterStep();
    
    // Step 3: Machine Selection
    console.log('[Step 3] Machine Selection');
    await wizard.selectFirstCompatibleMachine();
    
    // Step 4: Asset Selection
    console.log('[Step 4] Asset Selection');
    await wizard.waitForAssetsAutoConfigured();
    
    // Step 5: Well Selection
    console.log('[Step 5] Well Selection');
    await wizard.completeWellSelectionStep();
    
    // Step 6: Deck Setup
    console.log('[Step 6] Deck Setup');
    await wizard.advanceDeckSetup();
    
    // Step 7: Review & Run
    console.log('[Step 7] Review & Run');
    await wizard.openReviewStep();
    
    console.log('[Test] Clicking Start Execution');
    const startButton = page.getByRole('button', { name: /Start Execution/i }).filter({ visible: true }).first();
    await expect(startButton).toBeEnabled({ timeout: 20000 });
    await startButton.click({ force: true });
    
    // Verify Live Dashboard navigation
    console.log('[Test] Waiting for Live Dashboard navigation...');
    await expect(page).toHaveURL(/.*\/run\/live/, { timeout: 30000 });
    
    // Verify status tag appears (meaning execution started successfully in worker)
    console.log('[Test] Verifying execution started...');
    await expect(page.locator('.status-tag, .execution-status')).toBeVisible({ timeout: 120000 });
    
    console.log('[Test] Protocol workflow completed successfully!');
  });
});
