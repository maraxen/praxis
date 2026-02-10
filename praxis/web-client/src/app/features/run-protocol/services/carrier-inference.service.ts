import { Injectable } from '@angular/core';
import { ProtocolDefinition, AssetRequirement as ProtocolAssetRequirement } from '@features/protocols/models/protocol.models';
import { PlrResource } from '@core/models/plr.models';
import { DeckCarrier, CarrierSlot, CarrierDefinition, CarrierType } from '../models/deck-layout.models';
import { CarrierRequirement, SlotAssignment, StackingHint, DeckSetupResult } from '../models/carrier-inference.models';
import { DeckCatalogService } from './deck-catalog.service';

/**
 * Compatibility rules mapping carrier types to compatible resource types.
 */
const CARRIER_COMPATIBILITY: Record<string, string[]> = {
    'plate': ['Plate', 'Microplate', 'WellPlate', 'Lid', 'PlateAdapter'],
    'tip': ['TipRack', 'NestedTipRack', 'Tips'],
    'trough': ['Trough', 'Reservoir'],
    'tube': ['TubeRack', 'Tube'],
    'mfx': ['Plate', 'TipRack', 'Trough', 'Reservoir'],  // Multi-function
};

/**
 * Reverse mapping: resource type to compatible carrier types.
 */
const RESOURCE_TO_CARRIER: Record<string, CarrierType[]> = {
    'Plate': ['plate', 'mfx'],
    'Microplate': ['plate', 'mfx'],
    'WellPlate': ['plate', 'mfx'],
    'Lid': ['plate'],
    'PlateAdapter': ['plate'],
    'TipRack': ['tip', 'mfx'],
    'NestedTipRack': ['tip'],
    'Tips': ['tip'],
    'Trough': ['trough', 'mfx'],
    'Reservoir': ['trough', 'mfx'],
    'TubeRack': ['tube'],
    'Tube': ['tube'],
};

/**
 * Service for inferring carrier requirements from protocol assets.
 */
@Injectable({
    providedIn: 'root'
})
export class CarrierInferenceService {

    constructor(private deckCatalog: DeckCatalogService) { }

    /**
     * Analyze protocol requirements and calculate minimum carriers needed.
     */
    inferRequiredCarriers(
        protocol: ProtocolDefinition,
        deckType: string = 'HamiltonSTARDeck'
    ): CarrierRequirement[] {
        const requirements: CarrierRequirement[] = [];
        const availableCarriers = this.deckCatalog.getCompatibleCarriers(deckType);

        if (!protocol.assets || protocol.assets.length === 0) {
            return [];
        }

        // Group assets by resource type
        const assetsByType = this.groupAssetsByType(protocol.assets);

        // Track used rails to avoid conflicts
        let nextAvailableRail = 5; // Start at rail 5

        // For each type, calculate minimum carriers
        for (const [resourceType, assets] of Object.entries(assetsByType)) {
            const compatibleCarriers = this.findCompatibleCarriers(resourceType, availableCarriers);

            if (compatibleCarriers.length === 0) {
                console.warn(`No compatible carriers for resource type: ${resourceType}`);
                continue;
            }

            // Find optimal carrier (most slots to minimize carrier count)
            const bestCarrier = this.findOptimalCarrier(compatibleCarriers, assets.length);
            const slotsNeeded = assets.length;
            const carriersNeeded = Math.ceil(slotsNeeded / bestCarrier.numSlots);

            // Calculate suggested rail positions
            const suggestedRails: number[] = [];
            for (let i = 0; i < carriersNeeded; i++) {
                suggestedRails.push(nextAvailableRail);
                nextAvailableRail += bestCarrier.railSpan + 1; // Leave gap between carriers
            }

            requirements.push({
                resourceType,
                count: carriersNeeded,
                carrierFqn: bestCarrier.fqn,
                carrierType: bestCarrier.type,
                carrierName: bestCarrier.name,
                slotsNeeded,
                slotsAvailable: bestCarrier.numSlots * carriersNeeded,
                suggestedRails,
                placed: false
            });
        }

        return requirements;
    }

    /**
     * Auto-assign resources to optimal slots on carriers.
     */
    assignResourcesToSlots(
        assets: ProtocolAssetRequirement[],
        carriers: DeckCarrier[]
    ): SlotAssignment[] {
        const assignments: SlotAssignment[] = [];

        // Create a flat pool of available slots
        const slotPool: Array<{ slot: CarrierSlot; carrier: DeckCarrier }> = [];
        for (const carrier of carriers) {
            for (const slot of carrier.slots) {
                if (!slot.occupied) {
                    slotPool.push({ slot, carrier });
                }
            }
        }

        let placementOrder = 0;

        for (const asset of assets) {
            const resourceType = this.inferResourceType(asset);

            // Find compatible slot
            const compatibleSlotEntry = slotPool.find(entry =>
                this.isSlotCompatibleWithType(entry.slot, entry.carrier.type, resourceType) &&
                !entry.slot.occupied
            );

            if (!compatibleSlotEntry) {
                console.warn(`No compatible slot for asset: ${asset.name}`);
                continue;
            }

            const { slot, carrier } = compatibleSlotEntry;

            // Mark slot as occupied
            slot.occupied = true;

            // Create placeholder resource
            const resource: PlrResource = {
                name: asset.name,
                type: resourceType,
                location: { x: slot.position.x, y: slot.position.y, z: slot.position.z },
                size_x: slot.dimensions.width,
                size_y: slot.dimensions.height,
                size_z: 10,
                children: [],
                slot_id: slot.id,
                fqn: undefined  // Filled from selected inventory resource; asset.fqn is a backend module path, not PLR
            };

            slot.resource = resource;

            assignments.push({
                resource,
                slot,
                carrier,
                placementOrder: placementOrder++,
                placed: false
            });
        }

        return assignments;
    }

    /**
     * Sort assignments by Z-axis for optimal placement order.
     * Lower Z resources should be placed first (they're at the bottom).
     */
    sortByZAxis(assignments: SlotAssignment[]): SlotAssignment[] {
        return [...assignments].sort((a, b) => {
            const zA = a.resource.location?.z ?? a.slot.position.z;
            const zB = b.resource.location?.z ?? b.slot.position.z;
            return zA - zB;
        }).map((assignment, index) => ({
            ...assignment,
            placementOrder: index
        }));
    }

    /**
     * Detect stacking situations and provide placement hints.
     */
    detectStackingOrder(assignments: SlotAssignment[]): StackingHint[] {
        const hints: StackingHint[] = [];

        // Group by slot
        const bySlot = new Map<string, SlotAssignment[]>();
        for (const assignment of assignments) {
            const existing = bySlot.get(assignment.slot.id) || [];
            existing.push(assignment);
            bySlot.set(assignment.slot.id, existing);
        }

        // Detect stacking
        for (const [slotId, items] of bySlot.entries()) {
            if (items.length > 1) {
                const sorted = this.sortByZAxis(items);
                hints.push({
                    slotId,
                    order: sorted.map(a => a.resource.name),
                    reason: 'Stacked resources - place bottom first'
                });
            }
        }

        return hints;
    }

    /**
     * Complete deck setup workflow.
     */
    createDeckSetup(
        protocol: ProtocolDefinition,
        deckType: string = 'HamiltonSTARDeck'
    ): DeckSetupResult {
        const carrierRequirements = this.inferRequiredCarriers(protocol, deckType);

        // Create carrier instances from requirements
        const carriers: DeckCarrier[] = [];
        for (const req of carrierRequirements) {
            const carrierDef = this.deckCatalog.getCompatibleCarriers(deckType)
                .find(c => c.fqn === req.carrierFqn);

            if (carrierDef) {
                for (let i = 0; i < req.count; i++) {
                    const carrier = this.deckCatalog.createCarrierFromDefinition(
                        carrierDef,
                        `${req.carrierType}_carrier_${i}`,
                        req.suggestedRails[i] || 5 + (i * 7)
                    );
                    carriers.push(carrier);
                }
            }
        }

        // Assign resources to slots
        const slotAssignments = this.assignResourcesToSlots(
            protocol.assets || [],
            carriers
        );

        // Detect stacking
        const stackingHints = this.detectStackingOrder(slotAssignments);

        // Sort by Z-axis
        const sortedAssignments = this.sortByZAxis(slotAssignments);

        return {
            carrierRequirements,
            slotAssignments: sortedAssignments,
            stackingHints,
            complete: false
        };
    }

    // ========================================================================
    // Private Helpers
    // ========================================================================

    private groupAssetsByType(assets: ProtocolAssetRequirement[]): Record<string, ProtocolAssetRequirement[]> {
        const groups: Record<string, ProtocolAssetRequirement[]> = {};

        for (const asset of assets) {
            const type = this.inferResourceType(asset);
            if (!groups[type]) {
                groups[type] = [];
            }
            groups[type].push(asset);
        }

        return groups;
    }

    private inferResourceType(asset: ProtocolAssetRequirement): string {
        // Try type_hint_str first
        if (asset.type_hint_str) {
            // Extract base type from hint
            const hint = asset.type_hint_str;
            if (hint.includes('Plate') || hint.includes('plate')) return 'Plate';
            if (hint.includes('Tip') || hint.includes('tip')) return 'TipRack';
            if (hint.includes('Trough') || hint.includes('trough')) return 'Trough';
            if (hint.includes('Reservoir') || hint.includes('reservoir')) return 'Reservoir';
            if (hint.includes('Tube') || hint.includes('tube')) return 'TubeRack';
        }

        // Fall back to name-based inference
        const name = asset.name.toLowerCase();
        if (name.includes('plate')) return 'Plate';
        if (name.includes('tip')) return 'TipRack';
        if (name.includes('trough') || name.includes('reservoir')) return 'Trough';
        if (name.includes('tube')) return 'TubeRack';

        // Default to Plate
        return 'Plate';
    }

    private findCompatibleCarriers(resourceType: string, availableCarriers: CarrierDefinition[]): CarrierDefinition[] {
        const compatibleTypes = RESOURCE_TO_CARRIER[resourceType] || ['plate'];
        return availableCarriers.filter(c => compatibleTypes.includes(c.type));
    }

    private findOptimalCarrier(carriers: CarrierDefinition[], slotsNeeded: number): CarrierDefinition {
        // Prefer carrier that fits all resources with minimum waste
        const sorted = [...carriers].sort((a, b) => {
            const wasteA = (Math.ceil(slotsNeeded / a.numSlots) * a.numSlots) - slotsNeeded;
            const wasteB = (Math.ceil(slotsNeeded / b.numSlots) * b.numSlots) - slotsNeeded;
            return wasteA - wasteB;
        });
        return sorted[0];
    }

    private isSlotCompatibleWithType(slot: CarrierSlot, carrierType: CarrierType, resourceType: string): boolean {
        const compatibleResources = CARRIER_COMPATIBILITY[carrierType] || [];
        return compatibleResources.some(r =>
            resourceType === r ||
            resourceType.includes(r) ||
            r.includes(resourceType)
        );
    }
}
