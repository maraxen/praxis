import { test as base } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

export const test = base.extend<{ screenshotDir: string }>({
  screenshotDir: async ({}, use, testInfo) => {
    const dir = path.join(process.cwd(), 'e2e/screenshots', testInfo.titlePath[0] || 'default');
    fs.mkdirSync(dir, { recursive: true });
    await use(dir);
    // Optional: cleanup old screenshots
  },
});
