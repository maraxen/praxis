import { Page } from '@playwright/test';

export function createPathDoublingMonitor(page: Page) {
    const failedRequests: string[] = [];
    const doubledPaths: string[] = [];
    
    page.on('response', (response) => {
        const url = response.url();
        if (url.includes('jupyterlite') && response.status() === 404) {
            failedRequests.push(url);
        }
        if (url.match(/\/praxis\/.*\/praxis\//)) {
            doubledPaths.push(url);
        }
    });
    
    return { failedRequests, doubledPaths };
}
