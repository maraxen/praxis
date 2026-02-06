import { test, expect } from '../fixtures/worker-db.fixture';
import * as path from 'path';
import * as fs from 'fs';

const SCREENSHOT_DIR = '/tmp/e2e-deck';

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

test.describe('E2E Deck Setup', () => {

    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        // In browser mode, we expect a redirect to /app/home
        await page.waitForURL('**/app/home', { timeout: 15000 }).catch((e) => {
            console.log('[Test] Silent catch (waitForURL home):', e);
        });
        // Wait for SQLite DB to be ready
        await page.locator('[data-sqlite-ready="true"]').waitFor({ state: 'attached', timeout: 30000 });
        // Ensure shell layout is visible
        await expect(page.locator('.sidebar-rail')).toBeVisible({ timeout: 10000 });
        // Handle Welcome Dialog if present (Browser Mode)
        const welcomeDialog = page.getByRole('dialog', { name: /Welcome to Praxis/i });
        if (await welcomeDialog.isVisible({ timeout: 5000 })) {
            console.log('Dismissing Welcome Dialog...');
            await page.getByRole('button', { name: /Skip for Now/i }).click();
            await expect(welcomeDialog).not.toBeVisible();
        }
    });

    test.afterEach(async ({ page }) => {
        // Dismiss any open dialogs/overlays to ensure clean state
        await page.keyboard.press('Escape').catch((e) => console.log('[Test] Silent catch (Escape):', e));
    });

    test('should navigate to deck setup and capture screenshots', async ({ page }) => {
        // Navigate to Run Protocol
        await page.goto('/app/run');

        // Select first protocol
        const protocolCard = page.locator('app-protocol-card').first();
        await expect(protocolCard).toBeVisible({ timeout: 10000 });
        await protocolCard.click();

        // Continue through steps
        const continueBtn = page.getByRole('button', { name: /Continue/i });

        // Step 1: Protocol -> Parameters
        await continueBtn.click();

        // Step 2: Parameters -> Machine
        // Wait for step content to be stable before continuing
        await expect(continueBtn).toBeEnabled();
        await continueBtn.click();

        // Step 3: Machine Selection -> Assets
        // Select first available machine/backend that is not disabled
        const machineCard = page.locator('.option-card:not(.disabled)').first();
        await expect(machineCard).toBeVisible({ timeout: 10000 });
        await machineCard.click();
        
        await expect(continueBtn).toBeEnabled();
        await continueBtn.click();

        // Step 4: Asset Selection -> Wells (or Deck)
        // If it's not enabled, try clicking "Auto-fill All" in Guided Setup
        try {
            await expect(continueBtn).toBeEnabled({ timeout: 5000 });
        } catch (e) {
            console.log('[Test] Assets not auto-filled, attempting manual auto-fill all...');
            const autoFillBtn = page.getByRole('button', { name: /Auto-fill All/i });
            if (await autoFillBtn.isVisible()) {
                await autoFillBtn.click();
                await expect(continueBtn).toBeEnabled({ timeout: 5000 });
            }
        }
        await continueBtn.click();

        // Handle optional Well Selection
        try {
            await expect(page.locator('app-deck-setup-wizard')).toBeVisible({ timeout: 3000 });
        } catch (e) {
            // If not visible, maybe we are at Well Selection?
            const wellSelectionHeading = page.getByRole('heading', { name: 'Well Selection' });
            if (await wellSelectionHeading.isVisible()) {
                await continueBtn.click();
                await expect(page.locator('app-deck-setup-wizard')).toBeVisible({ timeout: 5000 });
            } else {
                console.log('Protocol might not require deck setup or we are lost');
            }
        }

        // Capture Empty Deck (Wizard start) - wait for deck visualization to render
        await expect(page.locator('app-deck-setup-wizard')).toBeVisible();
        await expect(page.locator('app-deck-view .deck-container')).toBeVisible({ timeout: 10000 });
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_empty_deck.png') });

        // Capture Deck Configuration Dialog (Wizard view)
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_deck_config_dialog.png') });

        // "deck with placements" -> Just capturing the wizard view which shows the deck
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_deck_with_placements.png') });

    });
});
