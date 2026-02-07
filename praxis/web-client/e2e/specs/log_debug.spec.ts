import { test, expect } from '@playwright/test';

test('capture logs and screenshot', async ({ page }) => {
    page.on('console', msg => console.log(`[BROWSER] ${msg.type()}: ${msg.text()}`));
    
    const dbName = 'praxis-worker-log-debug';
    await page.goto(`/?mode=browser&dbName=${dbName}`);
    
    // Wait for DB ready signal
    await page.waitForFunction(() => (window as any).sqliteService?.isReady() === true, { timeout: 30000 });
    
    console.log('DB is ready');

    await page.goto(`/app/protocols?mode=browser&dbName=${dbName}`);
    await page.waitForTimeout(5000);
    
    const cards = page.locator('app-protocol-card');
    console.log('Protocol cards count:', await cards.count());
    
    if (await cards.count() === 0) {
        console.log('No protocol cards found. Checking database content...');
        const count = await page.evaluate(async () => {
            const service = (window as any).sqliteService;
            if (!service) return 'No service';
            try {
                const res = await service.exec("SELECT COUNT(*) as count FROM function_protocol_definitions").toPromise();
                return res.resultRows[0].count;
            } catch (e) {
                return 'Error: ' + e.message;
            }
        });
        console.log('Protocol count in DB:', count);
        
        const tables = await page.evaluate(async () => {
             const service = (window as any).sqliteService;
             if (!service) return [];
             try {
                 const res = await service.exec("SELECT name FROM sqlite_master WHERE type='table'").toPromise();
                 return res.resultRows.map(r => r.name);
             } catch (e) {
                 return [e.message];
             }
        });
        console.log('Tables in DB:', tables);
    }
});
