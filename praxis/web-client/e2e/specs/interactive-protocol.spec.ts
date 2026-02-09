import { test, expect } from '../fixtures/worker-db.fixture';
import { PlaygroundPage } from '../page-objects/playground.page';
import { InteractionDialogHelper } from '../page-objects/interaction-dialog.helper';
import { WelcomePage } from '../page-objects/welcome.page';

test.describe('Interactive Protocol Execution', () => {
    test.setTimeout(300000); // 300s timeout for WASM boot
  let playground: PlaygroundPage;
  let dialogHelper: InteractionDialogHelper;
  let welcomePage: WelcomePage;

  test.beforeEach(async ({ page }, testInfo) => {
    playground = new PlaygroundPage(page, testInfo);
    dialogHelper = new InteractionDialogHelper(page);
    welcomePage = new WelcomePage(page, testInfo);

    // Capture console logs for debugging
    page.on('console', msg => {
        if (msg.text().includes('PRAXIS') || msg.text().includes('[REPL]')) {
            console.log(`[BROWSER] ${msg.text()}`);
        }
    });
    
    await playground.goto();
    await playground.waitForJupyterReady();
  });

  test.afterEach(async ({ page }) => {
    // Force close any lingering dialogs to clean the OverlayContainer
    // This prevents "Zombie Overlays" from interfering with subsequent tests
    await page.evaluate(() => {
        const dialogs = document.querySelectorAll('.cdk-overlay-container');
        dialogs.forEach(d => {
            if (d instanceof HTMLElement) d.innerHTML = '';
        });
    });
  });

  test('should display error for invalid Python syntax', async ({ page }) => {
    // Type broken code
    await playground.typeCode('await pause("test" invalid syntax');
    await playground.runCode();
    
    // Verify error appears in output area (not as a dialog)
    await playground.waitForOutput('SyntaxError');
  });

  test('should handle pause and resume', async ({ page }) => {
    await playground.typeCode('from praxis.interactive import pause; await pause("Please wait")');
    await playground.runCode();

    await dialogHelper.waitForPause('Please wait');
    await dialogHelper.resume();
    await dialogHelper.expectDismissed();
  });

  test('should handle confirm dialog (Yes)', async ({ page }) => {
    await playground.typeCode('from praxis.interactive import confirm; res = await confirm("Proceed?"); print(f"Result: {res}")');
    await playground.runCode();

    await dialogHelper.waitForConfirm('Proceed?');
    await dialogHelper.confirmYes();
    await playground.waitForOutput('Result: True');
  });

  test('should handle input dialog', async ({ page }) => {
    await playground.typeCode('from praxis.interactive import input; val = await input("Enter name"); print(f"Hello {val}")');
    await playground.runCode();

    await dialogHelper.waitForInput('Enter name');
    await dialogHelper.submitInput('Jules');
    await playground.waitForOutput('Hello Jules');
  });
});
