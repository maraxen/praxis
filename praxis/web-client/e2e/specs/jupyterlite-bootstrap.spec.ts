
import { test, expect } from '../fixtures/worker-db.fixture';
import { PlaygroundPage } from '../page-objects/playground.page';

test.describe('@slow JupyterLite Bootstrap Verification', () => {
  test('JupyterLite Seamless Bootstrap Validation', async ({ page }, testInfo) => {
    const consoleLogs: string[] = [];
    page.on('console', msg => consoleLogs.push(msg.text()));

    const playground = new PlaygroundPage(page, testInfo);
    await playground.goto();
    await playground.waitForBootstrapComplete(consoleLogs);

    // Kernel Execution: print("hello world")
    await playground.jupyter.executeCode('print("hello world")');
    await expect.poll(() => consoleLogs.some(log => log.includes('hello world')), {
      timeout: 15000, message: 'Expected "hello world" output'
    }).toBe(true);

    // PyLabRobot Import
    await playground.jupyter.executeCode('import pylabrobot; print(f"PLR v{pylabrobot.__version__}")');
    await expect.poll(() => consoleLogs.some(log => log.includes('PLR v')), {
      timeout: 15000, message: 'Expected pylabrobot version'
    }).toBe(true);

    // web_bridge Validation
    await playground.jupyter.executeCode('import web_bridge; print("web_bridge:", hasattr(web_bridge, "request_user_interaction"))');
    await expect.poll(() => consoleLogs.some(log => log.includes('web_bridge: True')), {
      timeout: 15000, message: 'Expected web_bridge import'
    }).toBe(true);
  });

  test('Phase 2 Bootstrap: Full payload received', async ({ page }, testInfo) => {
    const consoleLogs: string[] = [];
    page.on('console', msg => consoleLogs.push(msg.text()));

    const playground = new PlaygroundPage(page, testInfo);
    await playground.goto();
    await playground.waitForBootstrapComplete(consoleLogs);

    // Phase 2 specific signals
    await expect.poll(() => {
      const readySignal = consoleLogs.some(log => log.includes('✓ Ready signal sent'));
      const assetInjection = consoleLogs.some(log => log.includes('✓ Asset injection ready'));
      return readySignal && assetInjection;
    }, { timeout: 30000, message: 'Phase 2 signals not detected' }).toBe(true);
  });

  test('Wheel Installation: pylabrobot.whl fetched successfully', async ({ page }, testInfo) => {
    const wheelRequests: { url: string; status: number }[] = [];

    page.on('response', response => {
      if (response.url().includes('.whl')) {
        wheelRequests.push({ url: response.url(), status: response.status() });
      }
    });

    const playground = new PlaygroundPage(page, testInfo);
    await playground.goto();
    await playground.waitForBootstrapComplete([]);

    // Verify wheel was fetched successfully
    const pylabrobotWheel = wheelRequests.find(r => r.url.includes('pylabrobot'));
    expect(pylabrobotWheel, 'pylabrobot wheel request not found').toBeDefined();
    expect(pylabrobotWheel!.status).toBe(200);
  });

  test('Error Handling: Python syntax error shows traceback', async ({ page }, testInfo) => {
    const consoleLogs: string[] = [];
    page.on('console', msg => consoleLogs.push(msg.text()));

    const playground = new PlaygroundPage(page, testInfo);
    await playground.goto();
    await playground.waitForBootstrapComplete(consoleLogs);

    // Execute invalid syntax
    await playground.jupyter.executeCode('print("unclosed');

    // Verify error appears (SyntaxError in console)
    await expect.poll(() =>
      consoleLogs.some(log => log.includes('SyntaxError') || log.includes('EOL while scanning')),
      { timeout: 10000, message: 'Expected SyntaxError in console' }
    ).toBe(true);
  });

  test('Asset Injection: praxis:execute message is processed', async ({ page }, testInfo) => {
    const consoleLogs: string[] = [];
    page.on('console', msg => consoleLogs.push(msg.text()));

    const playground = new PlaygroundPage(page, testInfo);
    await playground.goto();
    await playground.waitForBootstrapComplete(consoleLogs);

    // Inject code via BroadcastChannel (simulating Angular host)
    await page.evaluate(() => {
      const channel = new BroadcastChannel('praxis_repl');
      channel.postMessage({
        type: 'praxis:execute',
        code: 'TEST_INJECTION = 42; print("Injected:", TEST_INJECTION)'
      });
    });

    await expect.poll(() => consoleLogs.some(log => log.includes('Injected: 42')), {
      timeout: 10000, message: 'Expected injected code output'
    }).toBe(true);
  });
});
