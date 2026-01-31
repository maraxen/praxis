import { test, expect } from '../../fixtures/execution-ready.fixture';
import { DeckViewPage } from '../../page-objects/deck-view.page';
import { ProtocolPage } from '../../page-objects/protocol.page';
import { WizardPage } from '../../page-objects/wizard.page';
import { ExecutionMonitorPage } from '../../page-objects/monitor.page';

test.describe('Deck View Interaction', () => {
    test('should show resource details when clicking labware', async ({ page, executionContext }) => {
        const deckView = new DeckViewPage(page);
        
        const resource = await deckView.getFirstResource();
        await resource.click();
        
        await deckView.assertInspectorVisible();
        await deckView.assertInspectorShowsResource(resource);
    });

    test('should display correct resource type in inspector', async ({ page, executionContext }) => {
        const deckView = new DeckViewPage(page);
        const resource = await deckView.getFirstResource();
        
        await resource.click();
        await deckView.assertInspectorVisible();
        
        // Deep verification
        const inspectorData = await deckView.getInspectorData();
        expect(inspectorData).not.toBeNull();
        expect(inspectorData!.type).toMatch(/Plate|TipRack|Reservoir|Tube/i);
        expect(inspectorData!.slot).toBeTruthy();
    });

    test('should switch inspector content when clicking different resources', async ({ page, executionContext }) => {
        const deckView = new DeckViewPage(page);
        const resources = await deckView.getResources();
        
        expect(resources.length).toBeGreaterThan(1);
        
        // Click first resource
        await resources[0].click();
        await deckView.assertInspectorVisible();
        const firstData = await deckView.getInspectorData();
        
        // Click second resource
        await resources[1].click();
        const secondData = await deckView.getInspectorData();
        
        // Verify data switched
        expect(secondData!.id).not.toBe(firstData!.id);
    });

    test('should correlate inspector data with simulation state', async ({ page, executionContext }) => {
        const deckView = new DeckViewPage(page);
        const resource = await deckView.getFirstResource();
        
        const resourceId = await resource.getId();
        await resource.click();
        
        const inspectorData = await deckView.getInspectorData();
        
        // Verify the inspector is showing data for the clicked resource
        expect(inspectorData!.id).toBe(resourceId);
        
        // Verify against simulation state
        const simulationState = await page.evaluate((id) => {
            const runService = (window as any).runService;
            const deck = runService?.currentRun?.deckState;
            return deck?.resources?.find((r: any) => r.id === id);
        }, resourceId);
        
        expect(simulationState).not.toBeNull();
        expect(inspectorData!.name).toBe(simulationState.name);
    });

    test('should hide tooltip when mouse leaves resource', async ({ page, executionContext }) => {
        const deckView = new DeckViewPage(page);
        const resource = await deckView.getFirstResource();
        
        await resource.hover();
        await deckView.assertTooltipVisible();
        
        // Move mouse away
        await page.mouse.move(0, 0);
        
        await expect(page.locator('.resource-tooltip')).toBeHidden({ timeout: 2000 });
    });

    test('should maintain inspector state during execution pause', async ({ page, executionContext }) => {
        const deckView = new DeckViewPage(page);
        const { monitorPage } = executionContext;
        
        const resource = await deckView.getFirstResource();
        await resource.click();
        
        const dataBefore = await deckView.getInspectorData();
        
        // Pause execution
        await page.getByRole('button', { name: /Pause/i }).click();
        await expect(page.getByTestId('run-status')).toContainText(/Paused/i);
        
        // Inspector should still show same data
        const dataAfter = await deckView.getInspectorData();
        expect(dataAfter!.id).toBe(dataBefore!.id);
    });
    test('should show empty state when no resources on deck', async ({ page }, testInfo) => {
        const protocolPage = new ProtocolPage(page, testInfo);
        await protocolPage.goto();
        await expect(protocolPage.protocolCards.first()).toBeVisible({ timeout: 30000 });
        await protocolPage.selectProtocolByName('Empty Deck Protocol');
        await protocolPage.continueFromSelection();
    
        const wizardPage = new WizardPage(page);
        await wizardPage.completeParameterStep();
        await wizardPage.selectFirstCompatibleMachine();
        await wizardPage.waitForAssetsAutoConfigured();
        await wizardPage.advanceDeckSetup();
        await wizardPage.openReviewStep();
        await wizardPage.startExecution();
    
        const monitorPage = new ExecutionMonitorPage(page, testInfo);
        await monitorPage.waitForLiveDashboard();
    
        const deckView = new DeckViewPage(page);
        const resources = await deckView.getResources();
    
        expect(resources.length).toBe(0);
        await expect(page.getByTestId('deck-empty-state')).toBeVisible();
    });
});
