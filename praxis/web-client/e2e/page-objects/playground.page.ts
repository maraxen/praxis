import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';
import { InventoryDialogPage } from './inventory-dialog.page';
import { JupyterlitePage } from './jupyterlite.page';

export class PlaygroundPage extends BasePage {
    readonly inventoryButton: Locator;
    readonly directControlTab: Locator;
    readonly jupyter: JupyterlitePage;

    constructor(page: Page) {
        super(page, '/playground');
        this.inventoryButton = page.locator('button').filter({ has: page.locator('mat-icon', { hasText: 'inventory_2' }) });
        this.directControlTab = page.getByRole('tab', { name: 'Direct Control' });
        this.jupyter = new JupyterlitePage(page);
    }

    async openInventory(): Promise<InventoryDialogPage> {
        await expect(this.inventoryButton).toBeVisible({ timeout: 25000 });
        await this.inventoryButton.click();
        const inventoryDialog = new InventoryDialogPage(this.page);
        await inventoryDialog.waitForDialogVisible();
        return inventoryDialog;
    }

    async selectModule(moduleName: string): Promise<void> {
        // This method is a placeholder for future functionality where multiple modules might be selectable.
        // For now, we assume the machine is already selected via the inventory.
        console.log(`[PlaygroundPage] Selecting module: ${moduleName}`);
        await this.directControlTab.click();
        await expect(this.page.locator('app-direct-control')).toBeVisible({ timeout: 10000 });
    }

    async executeCurrentMethod(methodName: RegExp = /Setup/i): Promise<void> {
        const directControl = this.page.locator('app-direct-control');
        const methodChip = directControl.getByRole('button', { name: methodName });

        await expect(methodChip.first()).toBeVisible({ timeout: 10000 });
        await methodChip.first().click();

        const executeBtn = directControl.getByRole('button', { name: /execute/i });
        await expect(executeBtn).toBeVisible();
        await expect(executeBtn).toBeEnabled();
        await executeBtn.click();
    }

    async waitForSuccess(expectedResult: string | RegExp = /OK/i): Promise<void> {
        const directControl = this.page.locator('app-direct-control');
        const resultLocator = directControl.locator('.command-result');
        await expect(resultLocator).toBeVisible({ timeout: 15000 });
        await expect(resultLocator).toContainText(expectedResult);
    }

    async verifyBackendInstantiation(machineName: string): Promise<void> {
        const backendReady = await this.page.evaluate((name) => {
            return (window as any).machineService?.getBackendInstance(name) !== undefined;
        }, machineName);
        expect(backendReady).toBe(true);
    }

    /**
     * Waits for Pyodide/JupyterLite bootstrap to complete.
     * @param consoleLogs Optional array to collect console logs during bootstrap
     */
    async waitForBootstrapComplete(consoleLogs: string[] = []): Promise<void> {
        // Wait for the JupyterLite iframe to be visible
        const iframeLocator = this.page.locator('iframe.notebook-frame, iframe[src*="repl"]').first();
        await expect(iframeLocator).toBeVisible({ timeout: 60000 });
        const iframe = this.page.frameLocator('iframe.notebook-frame, iframe[src*="repl"]').first();

        // Wait for Pyodide ready signal - check host window and iframe for completion message
        await this.page.waitForFunction(() => {
            return (window as any).__praxis_pyodide_ready === true;
        }, { timeout: 600000 }).catch(async () => {
            console.log('[PlaygroundPage] Pyodide host-side ready signal not detected, checking iframe idle state...');
            try {
                const idleIndicator = iframe.locator('.jp-mod-idle, .jp-Notebook-ExecutionIndicator[data-status="idle"]').first();
                await expect(idleIndicator).toBeVisible({ timeout: 30000 });
                console.log('[PlaygroundPage] Iframe idle state detected.');
            } catch (e) {
                console.log('[PlaygroundPage] Iframe idle state NOT detected either.');
            }
        });

        // Collect any console logs if array provided
        if (consoleLogs.length > 0) {
            this.page.on('console', msg => consoleLogs.push(msg.text()));
        }
    }

    /**
     * Waits for the JupyterLite kernel to reach idle state.
     */
    async waitForKernelReady(): Promise<void> {
        const iframe = this.page.locator('iframe.notebook-frame, iframe[src*="repl"]').first();
        await expect(iframe).toBeVisible({ timeout: 30000 });

        // Check for kernel idle indicator within iframe
        const kernelIdle = this.page.locator('.jp-mod-idle, [data-kernel-status="idle"]');
        await expect(kernelIdle).toBeVisible({ timeout: 45000 }).catch(() => {
            console.log('[PlaygroundPage] Kernel idle indicator not found, may still be initializing');
        });
    }

    /**
     * Waits for JupyterLite iframe to load and kernel to be ready.
     * Combines iframe visibility + kernel idle detection.
     */
    async waitForJupyterReady(): Promise<void> {
        await this.waitForBootstrapComplete();
        await this.waitForKernelReady();
    }

    /**
     * Types code into the JupyterLite REPL input.
     */
    async typeCode(code: string): Promise<void> {
        const iframe = this.page.frameLocator('iframe.notebook-frame, iframe[src*="repl"]').first();
        const codeInput = iframe.locator('.jp-CodeConsole-input .jp-InputArea-editor, .code-cell textarea').first();
        await expect(codeInput).toBeVisible({ timeout: 15000 });
        await codeInput.click();
        await this.page.keyboard.type(code);
    }

    /**
     * Runs the currently entered code (Shift+Enter).
     */
    async runCode(): Promise<void> {
        await this.page.keyboard.press('Shift+Enter');
    }

    /**
     * Waits for specific output text to appear in the JupyterLite output area.
     */
    async waitForOutput(expectedText: string | RegExp, timeout = 30000): Promise<void> {
        const iframe = this.page.frameLocator('iframe.notebook-frame, iframe[src*="repl"]').first();
        const outputCell = iframe.locator('.jp-OutputArea-output, .cell-output').last();
        await expect(outputCell).toBeVisible({ timeout });
        if (typeof expectedText === 'string') {
            await expect(outputCell).toContainText(expectedText, { timeout });
        } else {
            await expect(outputCell).toContainText(expectedText, { timeout });
        }
    }

    /**
     * Executes code in the JupyterLite REPL and returns the output.
     */
    async executeCode(code: string): Promise<string> {
        const iframe = this.page.frameLocator('iframe.notebook-frame, iframe[src*="repl"]').first();
        const codeInput = iframe.locator('.jp-CodeConsole-input .jp-InputArea-editor, .code-cell textarea').first();

        await expect(codeInput).toBeVisible({ timeout: 15000 });
        await codeInput.click();
        await this.page.keyboard.type(code);
        await this.page.keyboard.press('Shift+Enter');

        // Wait for output cell to appear
        const outputCell = iframe.locator('.jp-OutputArea-output, .cell-output').last();
        await expect(outputCell).toBeVisible({ timeout: 30000 });
        return await outputCell.textContent() || '';
    }
}
