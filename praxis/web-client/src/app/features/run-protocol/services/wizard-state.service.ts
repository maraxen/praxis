import { Injectable, signal, computed } from '@angular/core';
import { ProtocolDefinition } from '@features/protocols/models/protocol.models';
import { CarrierRequirement, SlotAssignment, DeckSetupResult } from '../models/carrier-inference.models';
import { CarrierInferenceService } from './carrier-inference.service';
import { DeckCatalogService } from './deck-catalog.service';
import { ConsumableAssignmentService } from './consumable-assignment.service';
import { getValidPLRClassNames, validatePLRClassName } from '@core/utils/plr-validator';

export type WizardStep = 'carrier-placement' | 'resource-placement' | 'verification';

export interface WizardState {
    currentStep: WizardStep;
    protocol: ProtocolDefinition | null;
    deckType: string;
    carrierRequirements: CarrierRequirement[];
    slotAssignments: SlotAssignment[];
    currentResourceIndex: number;
    isComplete: boolean;
    skipped: boolean;
}

/**
 * Service to manage the Guided Deck Setup wizard state.
 */
@Injectable({
    providedIn: 'root'
})
export class WizardStateService {
    // State signals
    private _currentStep = signal<WizardStep>('carrier-placement');
    private _protocol = signal<ProtocolDefinition | null>(null);
    private _deckType = signal<string>('HamiltonSTARDeck');
    private _carrierRequirements = signal<CarrierRequirement[]>([]);
    private _slotAssignments = signal<SlotAssignment[]>([]);
    private _currentResourceIndex = signal<number>(0);
    private _isComplete = signal<boolean>(false);
    private _skipped = signal<boolean>(false);

    // Public readonly signals
    readonly currentStep = this._currentStep.asReadonly();
    readonly protocol = this._protocol.asReadonly();
    readonly deckType = this._deckType.asReadonly();
    readonly carrierRequirements = this._carrierRequirements.asReadonly();
    readonly slotAssignments = this._slotAssignments.asReadonly();
    readonly currentResourceIndex = this._currentResourceIndex.asReadonly();
    readonly isComplete = this._isComplete.asReadonly();
    readonly skipped = this._skipped.asReadonly();

    // Computed values
    readonly allCarriersPlaced = computed(() =>
        this._carrierRequirements().length > 0 &&
        this._carrierRequirements().every(r => r.placed)
    );

    readonly allResourcesPlaced = computed(() =>
        this._slotAssignments().length > 0 &&
        this._slotAssignments().every(a => a.placed)
    );

    readonly currentAssignment = computed(() =>
        this._slotAssignments()[this._currentResourceIndex()] || null
    );

    readonly pendingCarriers = computed(() =>
        this._carrierRequirements().filter(r => !r.placed)
    );

    readonly pendingResources = computed(() =>
        this._slotAssignments().filter(a => !a.placed)
    );

    readonly progress = computed(() => {
        const carriers = this._carrierRequirements();
        const resources = this._slotAssignments();
        const totalItems = carriers.length + resources.length;
        if (totalItems === 0) return 0;

        const placedCarriers = carriers.filter(c => c.placed).length;
        const placedResources = resources.filter(r => r.placed).length;
        return Math.round(((placedCarriers + placedResources) / totalItems) * 100);
    });

    constructor(
        private carrierInference: CarrierInferenceService,
        private deckCatalog: DeckCatalogService,
        private consumableAssignment: ConsumableAssignmentService
    ) { }

    /**
     * Initialize wizard with protocol.
     */
    initialize(protocol: ProtocolDefinition, deckType: string = 'HamiltonSTARDeck', assetMap: Record<string, any> = {}): void {
        this._protocol.set(protocol);
        this._deckType.set(deckType);
        this._currentStep.set('carrier-placement');
        this._currentResourceIndex.set(0);
        this._isComplete.set(false);
        this._skipped.set(false);

        // Use CarrierInferenceService to calculate requirements
        const setup = this.carrierInference.createDeckSetup(protocol, deckType);

        // Pre-fill assignments from assetMap, but ensure they are not marked as 'placed' yet
        // The wizard is about verifying physical placement.
        const assignments = setup.slotAssignments.map(assignment => {
            // Find if this assignment corresponds to a protocol asset
            // The assignment resource name usually matches the protocol asset name
            const assetReq = protocol.assets?.find(a => a.name === assignment.resource.name);
            if (assetReq && assetMap[assetReq.accession_id]) {
                const selected = assetMap[assetReq.accession_id];
                // selected is the Inventory Resource object
                // We want its accession_id as the assignedAssetId
                return {
                    ...assignment,
                    assignedAssetId: selected.accession_id,
                    placed: false // Explicitly ensure false at start of wizard
                };
            }
            return {
                ...assignment,
                placed: false
            };
        });

        this._carrierRequirements.set(setup.carrierRequirements);
        this._slotAssignments.set(assignments);
    }

    /**
     * Mark a carrier as placed.
     */
    markCarrierPlaced(carrierFqn: string, placed: boolean = true): void {
        this._carrierRequirements.update(reqs =>
            reqs.map(req =>
                req.carrierFqn === carrierFqn ? { ...req, placed } : req
            )
        );
    }

    /**
     * Mark a resource as placed.
     */
    markResourcePlaced(resourceName: string, placed: boolean = true): void {
        this._slotAssignments.update(assignments =>
            assignments.map(a =>
                a.resource.name === resourceName ? { ...a, placed } : a
            )
        );
    }

    /**
     * Move to next resource in placement sequence.
     */
    nextResource(): void {
        const current = this._currentResourceIndex();
        const total = this._slotAssignments().length;
        if (current < total - 1) {
            this._currentResourceIndex.set(current + 1);
        }
    }

    /**
     * Move to previous resource in placement sequence.
     */
    previousResource(): void {
        const current = this._currentResourceIndex();
        if (current > 0) {
            this._currentResourceIndex.set(current - 1);
        }
    }

    /**
     * Navigate to next step.
     */
    nextStep(): void {
        const current = this._currentStep();
        if (current === 'carrier-placement') {
            this._currentStep.set('resource-placement');
        } else if (current === 'resource-placement') {
            this._currentStep.set('verification');
        } else if (current === 'verification') {
            this._isComplete.set(true);
        }
    }

    /**
     * Navigate to previous step.
     */
    previousStep(): void {
        const current = this._currentStep();
        if (current === 'verification') {
            this._currentStep.set('resource-placement');
        } else if (current === 'resource-placement') {
            this._currentStep.set('carrier-placement');
        }
    }

    /**
     * Skip the wizard entirely.
     */
    skip(): void {
        this._skipped.set(true);
        this._isComplete.set(true);
    }

    /**
     * Complete the wizard.
     */
    complete(): void {
        this._isComplete.set(true);
    }

    /**
     * Reset wizard state.
     */
    reset(): void {
        this._currentStep.set('carrier-placement');
        this._protocol.set(null);
        this._carrierRequirements.set([]);
        this._slotAssignments.set([]);
        this._currentResourceIndex.set(0);
        this._isComplete.set(false);
        this._skipped.set(false);
    }

    /**
     * Get full wizard state for persistence.
     */
    getState(): WizardState {
        return {
            currentStep: this._currentStep(),
            protocol: this._protocol(),
            deckType: this._deckType(),
            carrierRequirements: this._carrierRequirements(),
            slotAssignments: this._slotAssignments(),
            currentResourceIndex: this._currentResourceIndex(),
            isComplete: this._isComplete(),
            skipped: this._skipped()
        };
    }

    /**
     * Restore wizard state from persistence.
     */
    restoreState(state: WizardState): void {
        this._currentStep.set(state.currentStep);
        this._protocol.set(state.protocol);
        this._deckType.set(state.deckType);
        this._carrierRequirements.set(state.carrierRequirements);
        this._slotAssignments.set(state.slotAssignments);
        this._currentResourceIndex.set(state.currentResourceIndex);
        this._isComplete.set(state.isComplete);
        this._skipped.set(state.skipped);
    }

    // ========================================================================
    // LocalStorage Persistence
    // ========================================================================

    private readonly STORAGE_KEY = 'praxis_deck_setup_wizard';

    /**
     * Save current state to LocalStorage.
     */
    saveToStorage(): void {
        try {
            const state = this.getState();
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(state));
        } catch (e) {
            console.warn('Failed to save wizard state to LocalStorage:', e);
        }
    }

    /**
     * Load state from LocalStorage if available.
     * Returns true if state was loaded, false otherwise.
     */
    loadFromStorage(protocolId?: string): boolean {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (!stored) return false;

            const state = JSON.parse(stored) as WizardState;

            // Only restore if it's for the same protocol (or no filter specified)
            if (protocolId && state.protocol?.accession_id !== protocolId) {
                return false;
            }

            this.restoreState(state);
            return true;
        } catch (e) {
            console.warn('Failed to load wizard state from LocalStorage:', e);
            return false;
        }
    }

    /**
     * Clear stored state from LocalStorage.
     */
    clearStorage(): void {
        try {
            localStorage.removeItem(this.STORAGE_KEY);
        } catch (e) {
            console.warn('Failed to clear wizard state from LocalStorage:', e);
        }
    }

    /**
     * Check if there's a saved state for a protocol.
     */
    hasSavedState(protocolId?: string): boolean {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (!stored) return false;

            const state = JSON.parse(stored) as WizardState;
            if (protocolId && state.protocol?.accession_id !== protocolId) {
                return false;
            }
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Auto-assign consumables to slots based on requirements.
     * Uses ConsumableAssignmentService to find best matches in inventory.
     */
    async autoAssignConsumables(): Promise<void> {
        const protocol = this._protocol();
        const assignments = this._slotAssignments();

        if (!protocol || !protocol.assets) return;

        // Clone assignments to update logic
        const updatedAssignments = [...assignments];
        let changed = false;

        for (const asset of protocol.assets) {
            // Find assignment for this asset
            const index = updatedAssignments.findIndex(a => a.resource.name === asset.name);
            if (index !== -1) {
                const assignment = updatedAssignments[index];
                // If not already assigned an asset ID
                if (!assignment.assignedAssetId) {
                    const suggestedId = await this.consumableAssignment.findCompatibleConsumable(asset);
                    if (suggestedId) {
                        updatedAssignments[index] = { ...assignment, assignedAssetId: suggestedId };
                        changed = true;
                    }
                }
            }
        }

        if (changed) {
            this._slotAssignments.set(updatedAssignments);
        }
    }

    /**
     * Get asset map for RunProtocolComponent.
     * Maps Protocol Asset ID -> Physical Asset Info (including resolved accession_id)
     */
    getAssetMap(): Record<string, any> {
        const map: Record<string, any> = {};
        const assignments = this._slotAssignments();

        // Map protocol assets to the resources in the assignments
        // Since we don't have inventory selection in wizard yet, we just map 
        // using the asset accession_id if we can find it, or just use the name as key/value
        // But RunProtocolComponent expects keys to be accession_ids

        const protocol = this._protocol();
        if (protocol && protocol.assets) {
            protocol.assets.forEach(asset => {
                // Find if this asset is placed
                // We assume resource names in wizard match asset names
                const assignment = assignments.find(a => a.resource.name === asset.name);
                if (assignment && assignment.placed) {
                    map[asset.accession_id] = {
                        name: asset.name,
                        accession_id: assignment.assignedAssetId || undefined,
                        physically_placed: true
                    };
                }
            });
        }

        return map;
    }

    /**
     * Serialize the current deck state into a Python script.
     * This script rebuilds the deck layout in the worker.
     *
     * Architecture Note (Feb 2026):
     * - Uses PLR factory functions (STARLetDeck/STARDeck) for proper defaults
     * - When wizard is skipped, serializes from protocol.assets instead of empty deck
     * - This prevents empty deck issues and ensures resources are available
     */
    serializeToPython(): { script: string; warnings: string[] } {
        const assignments = this._slotAssignments();
        const deckType = this._deckType();
        const protocol = this._protocol();
        const isSkipped = this._skipped();
        const warnings: string[] = [];
        const validClasses = getValidPLRClassNames();

        // Check if we have placed resources from wizard
        const hasPlacedResources = assignments.some(a => a.placed);

        // Start building the Python script
        let code = 'import pylabrobot.resources as res\n';

        // Import deck factory functions (preferred over raw constructors)
        if (deckType.includes('HamiltonSTAR')) {
            code += 'from pylabrobot.resources.hamilton import STARLetDeck, STARDeck\n';
            code += 'from pylabrobot.resources.hamilton import *\n';
        } else if (deckType.includes('OTDeck')) {
            code += 'from pylabrobot.resources.opentrons import OTDeck\n';
        }

        code += '\ndef setup_deck():\n';

        // Instantiate Deck using factory functions with proper defaults
        // Note: Disable trash/teaching_rack for browser simulation (simpler deck)
        if (deckType.includes('HamiltonSTAR')) {
            // Use STARLetDeck (32 rails) for STARLet, STARDeck (56 rails) for STAR
            if (deckType.includes('Let') || deckType === 'HamiltonSTARDeck') {
                code += '    deck = STARLetDeck(name="deck")\n';
            } else {
                code += '    deck = STARDeck(name="deck")\n';
            }
        } else if (deckType.includes('OTDeck')) {
            code += '    deck = OTDeck(name="deck")\n';
        } else {
            code += '    deck = res.Deck()\n';
        }

        // === CASE 1: Wizard completed with placed resources ===
        if (hasPlacedResources && !isSkipped) {
            // Track placed carriers
            const carrierVarNames = new Map<string, string>();
            const uniqueCarriers = new Map<string, any>();

            assignments.forEach(a => {
                if (a.placed && a.carrier) {
                    uniqueCarriers.set(a.carrier.id, a.carrier);
                }
            });

            // Instantiate Carriers
            uniqueCarriers.forEach((carrier, id) => {
                const varName = id.replace(/[^a-zA-Z0-9_]/g, '_');
                carrierVarNames.set(id, varName);

                if (!validatePLRClassName(carrier.fqn, validClasses)) {
                    warnings.push(`Unknown carrier class: ${carrier.fqn}`);
                }

                // Heuristic for class name from FQN
                const className = carrier.fqn.split('.').pop() || 'Carrier';

                code += `    ${varName} = ${className}(name="${carrier.name}")\n`;

                if (carrier.railPosition !== undefined) {
                    code += `    deck.assign_child_resource(${varName}, rails=${carrier.railPosition})\n`;
                }
            });

            // Instantiate Labware
            assignments.forEach((assign, index) => {
                if (assign.placed) {
                    const varName = `labware_${index}`;
                    const carrierVar = carrierVarNames.get(assign.carrier.id);

                    if (carrierVar) {
                        // Map resource types to PLR classes
                        let className = 'Resource';
                        if (assign.resource.type === 'Plate' || assign.resource.type === 'Trough' || assign.resource.type === 'Reservoir') {
                            className = 'Plate';
                        } else if (assign.resource.type === 'TipRack') {
                            className = 'TipRack';
                        }

                        code += `    ${varName} = res.${className}(name="${assign.resource.name}", size_x=${assign.resource.size_x}, size_y=${assign.resource.size_y}, size_z=${assign.resource.size_z})\n`;
                        code += `    ${carrierVar}[${assign.slot.index}] = ${varName}\n`;
                    } else if (deckType.includes('OTDeck')) {
                        // OT-2 direct placement
                        let className = 'Resource';
                        if (assign.resource.type === 'Plate') className = 'Plate';
                        else if (assign.resource.type === 'TipRack') className = 'TipRack';

                        code += `    ${varName} = res.${className}(name="${assign.resource.name}", size_x=${assign.resource.size_x}, size_y=${assign.resource.size_y}, size_z=${assign.resource.size_z})\n`;
                        code += `    deck.assign_child_at_slot(${varName}, ${assign.slot.index + 1})\n`;
                    }
                }
            });
        }
        // === CASE 2: Wizard skipped OR no resources placed - use protocol.assets ===
        else if (protocol?.assets && protocol.assets.length > 0) {
            code += '    # Wizard skipped - creating resources from protocol.assets\n';

            let railPosition = 1; // Starting rail for direct assignment
            protocol.assets.forEach((asset, index) => {
                const varName = asset.name.replace(/[^a-zA-Z0-9_]/g, '_');

                // Determine resource class from type_hint_str
                let className = 'Resource';
                const typeHint = (asset.type_hint_str || '').toLowerCase();
                if (typeHint.includes('plate') || typeHint.includes('reservoir') || typeHint.includes('trough')) {
                    className = 'Plate';
                } else if (typeHint.includes('tiprack') || typeHint.includes('tip_rack')) {
                    className = 'TipRack';
                }

                // Standard labware dimensions (127x85mm footprint for SBS plates)
                const sizeX = className === 'TipRack' ? 127.0 : 127.0;
                const sizeY = className === 'TipRack' ? 85.0 : 85.0;
                const sizeZ = className === 'TipRack' ? 100.0 : 14.0;

                code += `    ${varName} = res.${className}(name="${asset.name}", size_x=${sizeX}, size_y=${sizeY}, size_z=${sizeZ})\n`;

                // For Hamilton decks, assign directly to deck at sequential rails
                // Note: Resources will be spaced 5 rails apart (approx 112.5mm)
                if (deckType.includes('HamiltonSTAR')) {
                    code += `    deck.assign_child_resource(${varName}, rails=${railPosition})\n`;
                    railPosition += 5;
                } else if (deckType.includes('OTDeck')) {
                    code += `    deck.assign_child_at_slot(${varName}, ${index + 1})\n`;
                }
            });

            warnings.push('Deck setup skipped - using default resource positions from protocol.assets');
        }

        code += '    return deck\n\ndeck = setup_deck()\n';
        return { script: code, warnings };
    }
}
