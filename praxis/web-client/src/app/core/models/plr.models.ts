import { DeckRail, DeckCarrier } from '@features/run-protocol/models/deck-layout.models';

export interface PlrLocation {
    x: number;
    y: number;
    z: number;
    type?: string; // "Coordinate"
}

export interface PlrResource {
    name: string;
    type: string;
    location: PlrLocation;
    size_x: number;
    size_y: number;
    size_z: number;
    children: PlrResource[];
    fqn?: string;
    color?: string; // Optional override
    /** Optional: ID of the slot this resource occupies (for slot-based placement) */
    slot_id?: string;
    // Specific to certain types
    num_rails?: number;
    num_items_x?: number;
    num_items_y?: number;
    max_volume?: number;
    volume?: number;
    cross_section_type?: string;
    is_ghost?: boolean;
}

/**
 * State dictionary keyed by resource name.
 * Values can include:
 * - volume: number (for wells)
 * - has_tip: boolean (for tip spots)
 * - tips: boolean[] (for tip racks - array per child)
 * - tip_mask: string (hex bitmask for compressed tip state)
 * - liquid_mask: string (hex bitmask for wells with liquid)
 * - volumes: number[] (sparse volume array)
 */
export interface PlrState {
    [resourceName: string]: any;
}

/**
 * Extended details for resource inspection.
 */
export interface PlrResourceDetails {
    name: string;
    type: string;
    location: PlrLocation;
    dimensions: { x: number; y: number; z: number };
    // Well/Spot specific
    volume?: number;
    maxVolume?: number;
    liquidClass?: string;
    hasTip?: boolean;
    // Parent info
    parentName?: string;
    slotId?: string;
}

/**
 * Complete deck data structure.
 * Conforms to backend Rails/Slots definitions for Carriers and Sites.
 */
export interface PlrDeckData {
    resource: PlrResource;
    state: PlrState;
    /** Hardware-defined rails (optional, for semantic model) */
    rails?: DeckRail[];
    /** Carriers currently placed on the deck (optional, for semantic model) */
    carriers?: DeckCarrier[];
}
