import { Injectable, signal, computed } from '@angular/core';
import { ProtocolDefinition } from '@features/protocols/models/protocol.models';
import { CarrierRequirement, SlotAssignment, DeckSetupResult } from '../models/carrier-inference.models';
import { PlrResource } from '@core/models/plr.models';
import { CarrierInferenceService } from './carrier-inference.service';
import { DeckCatalogService } from './deck-catalog.service';
import { ConsumableAssignmentService } from './consumable-assignment.service';
import { getValidPLRClassNames, validatePLRClassName } from '@core/utils/plr-validator';

// =============================================================================
// Typed Execution Manifest Interfaces
// =============================================================================

export interface ParameterEntry {
    name: string;                    // protocol function param name
    value: any;                      // scalar value OR resource reference name
    type_hint: string;               // from ProtocolDefinition
    fqn?: string;                    // for PLR resource types
    is_deck_resource?: boolean;      // true = resolve from constructed deck by name
}

export interface ResourceEntry {
    resource_fqn: string;
    name: string;                    // the name the protocol uses to reference this resource
    slot: number;
}

export interface CarrierEntry {
    carrier_fqn: string;
    name: string;
    rails: number;
    children: ResourceEntry[];
}

export interface SlotEntry {
    resource_fqn: string;
    name: string;
    slot: number;
}

export interface DeckManifest {
    fqn: string;                     // e.g. 'pylabrobot.resources.hamilton.STARlet.STARLetDeck'
    layout_type: 'rail-based' | 'slot-based';
    layout: CarrierEntry[] | SlotEntry[];
}

export interface MachineEntry {
    param_name: string;              // matches the protocol function parameter name (e.g. 'liquid_handler')
    machine_type: string;            // 'LiquidHandler' | 'PlateReader' | 'HeaterShaker' etc.
    backend_fqn: string;            // e.g. 'pylabrobot.liquid_handling.backends.hamilton.STAR'
    port_id?: string;
    is_simulated: boolean;
    deck?: DeckManifest;             // only for machines that use a deck (LiquidHandler)
}

export interface ExecutionManifest {
    protocol: { fqn: string; requires_deck: boolean };
    machines: MachineEntry[];        // one per machine parameter the protocol needs
    parameters: ParameterEntry[];    // scalar + resource params
}

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

    /**
     * Reactively builds a PlrResource tree from the current wizard placement state.
     * DeckViewComponent consumes this to render placed carriers and resources on the deck preview.
     */
    readonly deckResource = computed<PlrResource>(() => {
        const deckType = this._deckType();
        const carriers = this._carrierRequirements();
        const assignments = this._slotAssignments();

        // Get deck spec for dimensions and rail spacing
        const spec = this.deckCatalog.getDeckDefinition(deckType);
        const railSpacing = spec?.railSpacing ?? 22.5;
        const railOffset = 100.0; // Standard rail offset

        // Build deck shell
        const deck: PlrResource = {
            name: 'deck',
            type: deckType,
            location: { x: 0, y: 0, z: 0, type: 'Coordinate' },
            size_x: spec?.dimensions?.width ?? 1200,
            size_y: spec?.dimensions?.height ?? 653.5,
            size_z: spec?.dimensions?.depth ?? 500,
            num_rails: spec?.numRails ?? 30,
            children: []
        };

        // Only add placed carriers as deck children
        const placedCarriers = carriers.filter(c => c.placed);
        for (const carrierReq of placedCarriers) {
            // Find assignments belonging to this carrier
            const carrierAssignments = assignments.filter(
                a => a.carrier.fqn === carrierReq.carrierFqn
            );

            // Get carrier info from first assignment (all share same carrier)
            const firstAssignment = carrierAssignments[0];
            if (!firstAssignment) continue;

            const carrierInfo = firstAssignment.carrier;
            const carrierX = railOffset + (carrierInfo.railPosition * railSpacing);

            const carrierResource: PlrResource = {
                name: carrierReq.carrierName,
                type: carrierInfo.fqn.split('.').pop() || 'Carrier',
                location: { x: carrierX, y: 63, z: 0, type: 'Coordinate' },
                size_x: carrierInfo.dimensions.width,
                size_y: carrierInfo.dimensions.height,
                size_z: carrierInfo.dimensions.depth,
                children: []
            };

            // Add placed resources as carrier children
            for (const assignment of carrierAssignments) {
                if (assignment.placed) {
                    carrierResource.children.push({
                        ...assignment.resource,
                        location: { ...assignment.resource.location, type: 'Coordinate' }
                    });
                }
            }

            deck.children.push(carrierResource);
        }

        return deck;
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
     * Builds a Typed Execution Manifest representing the protocol and configured deck state.
     * This manifest is "materialized" by the Pyodide worker into a live PLR context.
     * 
     * @param machineConfigs Pre-built machine entries containing backend/port info (from ExecutionService)
     */
    buildExecutionManifest(machineConfigs: MachineEntry[]): ExecutionManifest {
        const protocol = this._protocol();
        const assignments = this._slotAssignments();
        const deckType = this._deckType();
        const isSkipped = this._skipped();

        if (!protocol) {
            throw new Error('Cannot build manifest: protocol not initialized');
        }

        // 1. Build Deck Layout
        const deckSpec = this.deckCatalog.getDeckDefinition(deckType);
        const layoutType = deckSpec?.layoutType || 'rail-based';

        let layout: CarrierEntry[] | SlotEntry[] = [];

        if (layoutType === 'rail-based') {
            // Group assignments by carrier
            const carrierMap = new Map<string, CarrierEntry>();

            assignments.forEach(a => {
                if (!a.placed && !isSkipped) return;

                let carrierEntry = carrierMap.get(a.carrier.id);
                if (!carrierEntry) {
                    carrierEntry = {
                        carrier_fqn: a.carrier.fqn,
                        name: a.carrier.name,
                        rails: a.carrier.railPosition,
                        children: []
                    };
                    carrierMap.set(a.carrier.id, carrierEntry);
                }

                carrierEntry.children.push({
                    resource_fqn: a.resource.fqn || 'pylabrobot.resources.Resource', // Fallback
                    name: a.resource.name,
                    slot: a.slot.index
                });
            });
            layout = Array.from(carrierMap.values());
        } else {
            // Slot-based
            layout = assignments
                .filter(a => a.placed || isSkipped)
                .map(a => ({
                    resource_fqn: a.resource.fqn || 'pylabrobot.resources.Resource',
                    name: a.resource.name,
                    slot: a.slot.index
                }));
        }

        const deckManifest: DeckManifest = {
            fqn: deckType.includes('.') ? deckType : this.getDeckFqnForType(deckType),
            layout_type: layoutType,
            layout: layout
        };

        // 2. Map machines and attach deck to LiquidHandler
        const machines = machineConfigs.map(m => {
            if (m.machine_type === 'LiquidHandler') {
                return { ...m, deck: deckManifest };
            }
            return m;
        });

        // 3. Map parameters and assets
        const parameters: ParameterEntry[] = [];

        // Add scalar parameters
        if (protocol.parameters) {
            protocol.parameters.forEach(p => {
                const typeHintLower = p.type_hint.toLowerCase();
                const isResource = typeHintLower.includes('plate') ||
                    typeHintLower.includes('tiprack') ||
                    typeHintLower.includes('resource');

                parameters.push({
                    name: p.name,
                    value: p.default_value_repr, // ExecutionService will overwrite with actual user values
                    type_hint: p.type_hint,
                    fqn: p.fqn,
                    is_deck_resource: isResource
                });
            });
        }

        // Add non-parameter assets that might be needed
        if (protocol.assets) {
            protocol.assets.forEach(a => {
                // If it's a machine, it's already in machines[] (via ExecutionService)
                // If it's labware on deck, protocol likely references it via parameter name.
                // We ensure it's detectable.
            });
        }

        return {
            protocol: {
                fqn: protocol.fqn || `${protocol.module_name}.${protocol.function_name}`,
                requires_deck: protocol.requires_deck !== false
            },
            machines: machines,
            parameters: parameters
        };
    }

    /**
     * Helper to map short deck type names to PLR FQNs if not already FQN.
     */
    private getDeckFqnForType(type: string): string {
        switch (type) {
            case 'HamiltonSTARDeck': return 'pylabrobot.resources.hamilton.STARDeck';
            case 'HamiltonSTARLetDeck': return 'pylabrobot.resources.hamilton.STARLetDeck';
            case 'OTDeck': return 'pylabrobot.resources.opentrons.OTDeck';
            default: return 'pylabrobot.resources.Deck';
        }
    }
}
