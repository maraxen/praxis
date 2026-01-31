import { Page, Locator, expect } from '@playwright/test';

export class ThemeSwitcherComponent {
  readonly themeToggle: Locator;

  constructor(private readonly page: Page) {
    this.themeToggle = page.locator('[data-tour-id="theme-toggle"]');
  }

  async setDarkTheme(): Promise<void> {
    await expect(this.themeToggle).toBeVisible();
    await this.themeToggle.click();
    await expect(this.page.locator('body')).toHaveClass(/dark-theme/, { timeout: 10000 });
  }

  async setLightTheme(): Promise<void> {
    await expect(this.themeToggle).toBeVisible();
    const isDark = await this.page.locator('body').evaluate(body => body.classList.contains('dark-theme'));
    if (isDark) {
        await this.themeToggle.click();
        await this.themeToggle.click();
    }
    await expect(this.page.locator('body')).not.toHaveClass(/dark-theme/, { timeout: 10000 });
  }
}
