import { Page, FrameLocator, Locator, expect } from '@playwright/test';

export class JupyterlitePage {
  readonly page: Page;
  readonly frame: FrameLocator;
  readonly codeInput: Locator;
  readonly kernelIdleIndicator: Locator;

  constructor(page: Page) {
    this.page = page;
    this.frame = page.frameLocator('iframe.notebook-frame, iframe[src*="repl"]').first();
    this.codeInput = this.frame.locator('.jp-CodeConsole-input .cm-content, .jp-CodeConsole-input .jp-InputArea-editor, .jp-Repl-input .cm-content').first();
    this.kernelIdleIndicator = this.frame.locator('.jp-mod-idle, .jp-Notebook-ExecutionIndicator[data-status="idle"]').first();
  }

  async waitForFrameAttached(timeout = 20000): Promise<void> {
    const frameElement = this.page.locator('iframe.notebook-frame');
    await expect(frameElement).toBeVisible({ timeout });
  }

  async waitForKernelIdle(timeout = 45000): Promise<void> {
    await this.kernelIdleIndicator.waitFor({ timeout, state: 'visible' });
  }

  async dismissDialogs(maxAttempts = 3): Promise<void> {
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const okButton = this.frame.getByRole('button', { name: 'OK' });
        if (await okButton.isVisible({ timeout: 1000 })) {
          await okButton.click();
          await this.frame.locator('.jp-Dialog').waitFor({ state: 'hidden', timeout: 2000 }).catch(() => {});
        }
      } catch {
        break; // No more dialogs
      }
    }
  }

  async executeCode(code: string): Promise<void> {
    await this.dismissDialogs();
    await expect(this.codeInput).toBeVisible({ timeout: 30000 });
    
    // Ensure the editor is focused
    await this.codeInput.click({ force: true });
    await this.page.waitForTimeout(500);
    
    // Clear existing code if any (Select All + Backspace)
    await this.page.keyboard.down('Control');
    await this.page.keyboard.press('a');
    await this.page.keyboard.up('Control');
    await this.page.keyboard.press('Backspace');

    // Type new code
    await this.page.keyboard.type(code, { delay: 5 });
    await this.page.waitForTimeout(200);
    await this.page.keyboard.press('Shift+Enter');
  }

  async assertKernelDialogNotVisible(timeout = 5000): Promise<void> {
    const kernelDialog = this.frame.locator('.jp-Dialog').filter({ hasText: /kernel|select/i });
    await expect(kernelDialog).not.toBeVisible({ timeout });
  }
}
