import { Page, Locator, expect, TestInfo } from '@playwright/test';
import { BasePage } from './base.page';

export class SettingsPage extends BasePage {
    readonly exportButton: Locator;
    readonly importButton: Locator;
    readonly importInput: Locator;
    readonly clearDataButton: Locator;
    readonly opfsToggle: Locator;

    constructor(page: Page, testInfo?: TestInfo) {
        super(page, '/settings', testInfo);
        this.exportButton = page.getByRole('button', { name: /Export Database/i });
        this.importButton = page.getByRole('button', { name: /Import Database/i });
        this.importInput = page.locator('input[type="file"]');
        this.clearDataButton = page.getByRole('button', { name: /Reset to Defaults/i });
        this.opfsToggle = page.getByRole('switch', { name: /Database Backend/i });
    }

    async toggleOpfs(enabled: boolean): Promise<void> {
        const isCurrentlyChecked = await this.opfsToggle.isChecked();
        if (isCurrentlyChecked !== enabled) {
            await this.opfsToggle.click();
            // Wait for snackbar and click Reload
            await this.page.getByRole('button', { name: 'Reload' }).click();
            await this.page.waitForLoadState('domcontentloaded');
        }
    }

    async isOpfsEnabled(): Promise<boolean> {
        return this.opfsToggle.isChecked();
    }

    async exportDatabase() {
        const downloadPromise = this.page.waitForEvent('download');
        await this.exportButton.click();
        const download = await downloadPromise;
        return await download.path();
    }

    async importDatabase(filePath: string) {
        // Use setInputFiles on the hidden input
        await this.importInput.setInputFiles(filePath);
        
        // Wait for confirmation dialog and confirm
        const dialog = this.page.getByRole('dialog', { name: /Import Database/i });
        await expect(dialog).toBeVisible({ timeout: 5000 });
        
        const confirmBtn = dialog.getByRole('button', { name: 'Import and Refresh' });
        await confirmBtn.click();
        
        // Navigation/Reload happens after import
        await this.page.waitForLoadState('domcontentloaded');
    }

    async openImportDialogAndCancel() {
        // We need to set a file to trigger the change event and thus the dialog
        await this.importInput.setInputFiles({
            name: 'dummy.db',
            mimeType: 'application/x-sqlite3',
            buffer: Buffer.from('SQLite format 3\0', 'binary')
        });

        const dialog = this.page.getByRole('dialog', { name: /Import Database/i });
        await expect(dialog).toBeVisible({ timeout: 5000 });

        const cancelBtn = dialog.getByRole('button', { name: /Cancel/i });
        await cancelBtn.click();

        await expect(dialog).not.toBeVisible();
    }

    async resetState() {
        // If there's a UI button
        if (await this.clearDataButton.isVisible()) {
            await this.clearDataButton.click();
            
            // Wait for confirmation dialog
            const dialog = this.page.getByRole('dialog', { name: /Reset Inventory/i });
            await expect(dialog).toBeVisible({ timeout: 5000 });
            
            const confirmBtn = dialog.getByRole('button', { name: /Reset Everything/i });
            await confirmBtn.click();
            
            await this.page.waitForLoadState('domcontentloaded');
        } else {
            // Manual clear
            await this.page.evaluate(() => {
                localStorage.clear();
                // IndexDB clear is harder via evaluate without specialized code or library
                // But for "Browser Mode Specifics", we might just rely on import overwriting existing data
            });
        }
    }
}
