import { Page, Locator, expect } from '@playwright/test';

export class LogoPageObject {
  private readonly page: Page;
  readonly logoElement: Locator;

  constructor(page: Page) {
    this.page = page;
    this.logoElement = page.getByTestId('app-logo');
  }

  async waitForLogoVisible(timeout = 15000): Promise<void> {
    await expect(this.logoElement).toBeVisible({ timeout });
  }

  async getLogoSvgCssVariable(): Promise<string> {
    return this.logoElement.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.getPropertyValue('--logo-svg');
    });
  }

  async getMaskImage(): Promise<string> {
    return this.logoElement.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.getPropertyValue('mask-image') || 
             style.getPropertyValue('-webkit-mask-image');
    });
  }

  async assertLogoRenderedCorrectly(): Promise<void> {
    const logoSvg = await this.getLogoSvgCssVariable();
    
    // 1. CSS variable is not default
    expect(logoSvg).not.toBe('none');
    expect(logoSvg).not.toBe('');
    
    // 2. Valid SVG data URI format
    expect(logoSvg).toContain('url("data:image/svg+xml');
    
    // 3. Not marked as unsafe by Angular
    expect(logoSvg).not.toContain('unsafe:');
  }
}
