import { Page, Locator, expect } from '@playwright/test';

export class DeckViewPage {
    private readonly page: Page;
    
    // Locators - prefer test IDs and ARIA roles
    private readonly resourceNodes: Locator;
    private readonly inspector: Locator;
    private readonly tooltip: Locator;
    
    constructor(page: Page) {
        this.page = page;
        
        // If test-ids are not available, use these patterns:
        this.resourceNodes = page.getByTestId('deck-resource').or(
            page.locator('.resource-node:not(.is-root)')
        );
        this.inspector = page.getByTestId('resource-inspector').or(
            page.locator('app-resource-inspector-panel')
        );
        this.tooltip = page.getByRole('tooltip').or(
            page.locator('.resource-tooltip')
        );
    }
    
    async getFirstResource(): Promise<DeckResource> {
        const node = this.resourceNodes.first();
        await expect(node).toBeVisible({ timeout: 15000 });
        return new DeckResource(this.page, node);
    }
    
    async getResources(): Promise<DeckResource[]> {
        const count = await this.resourceNodes.count();
        const resources: DeckResource[] = [];
        for (let i = 0; i < count; i++) {
            resources.push(new DeckResource(this.page, this.resourceNodes.nth(i)));
        }
        return resources;
    }
    
    async assertInspectorVisible(): Promise<void> {
        await expect(this.inspector).toBeVisible({ timeout: 10000 });
    }
    
    async assertInspectorShowsResource(resource: DeckResource): Promise<void> {
        const name = await resource.getName();
        expect(name, 'Resource name should be defined').toBeTruthy();
        await expect(this.inspector).toContainText(name!);
    }
    
    async assertTooltipVisible(): Promise<void> {
        await expect(this.tooltip).toBeVisible({ timeout: 5000 });
    }
    
    async assertTooltipShowsResource(resource: DeckResource): Promise<void> {
        const name = await resource.getName();
        expect(name, 'Resource name should be defined').toBeTruthy();
        const header = this.tooltip.locator('.tooltip-header, [data-testid="tooltip-title"]');
        await expect(header).toContainText(name!);
    }
    
    // Deep state verification
    async getInspectorData(): Promise<ResourceInspectorData | null> {
        return await this.page.evaluate(() => {
            const cmp = (window as any).ng?.getComponent(
                document.querySelector('app-resource-inspector-panel')
            );
            if (!cmp?.selectedResource) return null;
            return {
                id: cmp.selectedResource.id,
                name: cmp.selectedResource.name,
                type: cmp.selectedResource.type,
                slot: cmp.selectedResource.slot,
                contents: cmp.selectedResource.contents
            };
        });
    }
}

export class DeckResource {
    constructor(
        private readonly page: Page,
        private readonly locator: Locator
    ) {}
    
    async click(): Promise<void> {
        await this.locator.click();
    }
    
    async hover(): Promise<void> {
        await this.locator.hover();
    }
    
    async getName(): Promise<string | null> {
        return (
            await this.locator.getAttribute('data-resource-name') ||
            await this.locator.getAttribute('title')
        );
    }
    
    async getId(): Promise<string | null> {
        return await this.locator.getAttribute('data-resource-id');
    }
}

interface ResourceInspectorData {
    id: string;
    name: string;
    type: string;
    slot: string;
    contents?: unknown[];
}
