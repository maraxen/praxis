import { Page, FrameLocator, Locator, expect } from '@playwright/test';

export class JupyterlitePage {
  readonly page: Page;
  readonly frame: FrameLocator;
  readonly codeInput: Locator;
  readonly kernelIdleIndicator: Locator;

  constructor(page: Page) {
    this.page = page;
    this.frame = page.frameLocator('iframe.notebook-frame');
    this.codeInput = this.frame.locator('.jp-CodeConsole-input .jp-InputArea-editor');
    this.kernelIdleIndicator = this.frame.locator('.jp-mod-idle').first();
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
    await expect(this.codeInput).toBeVisible();
    await this.codeInput.click();
    await this.page.keyboard.type(code);
    await this.page.keyboard.press('Shift+Enter');
  }

  async assertKernelDialogNotVisible(timeout = 5000): Promise<void> {
    const kernelDialog = this.frame.locator('.jp-Dialog').filter({ hasText: /kernel|select/i });
    await expect(kernelDialog).not.toBeVisible({ timeout });
  }
}
