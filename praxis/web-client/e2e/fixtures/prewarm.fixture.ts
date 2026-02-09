import { test as base } from '@playwright/test';
import { PlaygroundPage } from '../page-objects/playground.page';

/**
 * Fixture to prewarm JupyterLite environment.
 * Ensures the JupyterLab shell is fully bootstrapped before tests begin.
 */
export const jupyterPrewarmTest = base.extend<{ jupyterReady: void }>({
    jupyterReady: async ({ page }, use, testInfo) => {
        console.log('[Fixture] Prewarming JupyterLite via PlaygroundPage...');
        const playground = new PlaygroundPage(page, testInfo);

        // Navigate to playground with resetdb=false to preserve state but ensure environment exists
        await playground.goto({ resetdb: false });

        // Use robust bootstrap detection from POM
        await playground.waitForJupyterReady();

        console.log('[Fixture] JupyterLite ready.');
        await use();
    }
});
