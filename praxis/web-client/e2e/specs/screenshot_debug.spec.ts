import { test, expect } from '@playwright/test';

test('capture screenshot', async ({ page }) => {
    const dbName = 'praxis-worker-screenshot';
    await page.goto(`/?mode=browser&dbName=${dbName}`);
    await page.waitForTimeout(10000); // Wait for things to load
    await page.screenshot({ path: 'debug_screenshot.png', fullPage: true });
    
    // Check if dialog is present
    const dialog = page.getByRole('dialog');
    if (await dialog.isVisible()) {
        console.log('Dialog is visible');
        const text = await dialog.innerText();
        console.log('Dialog text:', text);
        await page.screenshot({ path: 'debug_dialog.png' });
    } else {
        console.log('No dialog visible');
    }

    await page.goto(`/app/protocols?mode=browser&dbName=${dbName}`);
    await page.waitForTimeout(5000);
    await page.screenshot({ path: 'debug_protocols.png', fullPage: true });
    const cards = page.locator('app-protocol-card');
    console.log('Protocol cards count:', await cards.count());
});
