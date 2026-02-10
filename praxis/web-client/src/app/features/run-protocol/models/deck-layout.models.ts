import { PlrResource } from '@core/models/plr.models';

// ============================================================================
// Legacy Interfaces (retained for backward compatibility)
// ============================================================================

export interface DeckResource {
    name: string;
    type: 'plate' | 'tip_rack' | 'other';
    color?: string;
    category?: string;
}

export interface DeckSlot {
    id: string;
    x: number;
    y: number;
    width: number;
    height: number;
    resource?: DeckResource;
}

export interface DeckLayout {
    width: number;
    height: number;
    slots: DeckSlot[];
}

// ============================================================================
// Semantic Deck Model - Rails → Carriers → Slots Hierarchy
// ============================================================================

/**
 * Rail definition from hardware specs.
 * Rails are the vertical mounting channels on a deck (e.g., 30 rails on Hamilton STAR).
 */
export interface DeckRail {
    /** 0-based rail index (e.g., 0-29 for Hamilton STAR) */
    index: number;
    /** X position in mm from deck origin */
    xPosition: number;
    /** Rail width in mm (typically 22.5mm) */
    width: number;
    /** List of carrier FQNs compatible with this rail */
    compatibleCarrierTypes: string[];
}

/**
 * Carrier type classification.
 */
export type CarrierType = 'plate' | 'tip' | 'trough' | 'tube' | 'mfx';

/**
 * Carrier with explicit slots.
 * Carriers are physical bars that slide into rails and hold labware.
 */
export interface DeckCarrier {
    /** Unique identifier for this carrier instance */
    id: string;
    /** PLR fully qualified name (e.g., "pylabrobot.resources.hamilton.plate_carriers.PLT_CAR_L5AC_A00") */
    fqn: string;
    /** Human-readable display name */
    name: string;
    /** Carrier type classification */
    type: CarrierType;
    /** Starting rail index where carrier is mounted */
    railPosition: number;
    /** Number of rails this carrier spans (typically 1-3) */
    railSpan: number;
    /** Ordered list of slots on this carrier */
    slots: CarrierSlot[];
    /** Physical dimensions in mm */
    dimensions: {
        width: number;
        height: number;
        depth: number;
    };
}

/**
 * Individual slot on a carrier.
 * Slots are discrete positions where labware can be placed.
 */
export interface CarrierSlot {
    /** Unique slot identifier (e.g., "plt_car_l5ac_slot_1") */
    id: string;
    /** 0-based position index on the carrier */
    index: number;
    /** Display name (e.g., "Position 1") */
    name: string;
    /** List of PLR resource FQNs/categories compatible with this slot */
    compatibleResourceTypes: string[];
    /** Whether this slot currently has a resource */
    occupied: boolean;
    /** The resource occupying this slot, if any */
    resource?: PlrResource | null;
    /** Position relative to carrier origin in mm */
    position: {
        x: number;
        y: number;
        z: number;
    };
    /** Slot dimensions in mm */
    dimensions: {
        width: number;
        height: number;
    };
}

/**
 * Complete deck configuration.
 * This is the top-level semantic model for a laboratory deck.
 */
export interface DeckConfiguration {
    /** PLR deck fully qualified name */
    deckType: string;
    /** Human-readable deck name */
    deckName: string;
    /** Hardware-defined rails */
    rails: DeckRail[];
    /** Carriers currently placed on the deck */
    carriers: DeckCarrier[];
    /** Physical deck dimensions in mm */
    dimensions: {
        width: number;
        height: number;
        depth: number;
    };
    /** Total number of rails on this deck */
    numRails: number;
}

/**
 * Deck layout type discriminator.
 * - 'rail-based': Uses rails and carriers (e.g., Hamilton STAR)
 * - 'slot-based': Uses numbered slots in a grid (e.g., Opentrons OT-2)
 */
export type DeckLayoutType = 'rail-based' | 'slot-based';

/**
 * Slot specification for slot-based decks.
 * Defines a discrete position where labware can be placed.
 */
export interface DeckSlotSpec {
    /** Slot number (1-indexed, e.g., 1-12 for OT-2) */
    slotNumber: number;
    /** Display label (e.g., "1", "Trash") */
    label: string;
    /** Slot type for styling/compatibility */
    slotType: 'standard' | 'trash' | 'module' | 'fixed';
    /** Position in mm from deck origin (bottom-left) */
    position: { x: number; y: number; z: number };
    /** Slot dimensions in mm */
    dimensions: { width: number; height: number };
    /** Compatible resource types */
    compatibleResourceTypes: string[];
}

/**
 * Deck definition specification from hardware catalog.
 * Used by DeckCatalogService.
 */
export interface DeckDefinitionSpec {
    /** PLR fully qualified name */
    fqn: string;
    /** Human-readable name */
    name: string;
    /** Manufacturer name */
    manufacturer: string;
    /** Deck layout type */
    layoutType: DeckLayoutType;
    /** Physical dimensions in mm */
    dimensions: {
        width: number;
        height: number;
        depth: number;
    };
    // === Rail-based deck properties ===
    /** Number of rails on this deck (rail-based only) */
    numRails?: number;
    /** Distance between rail centers in mm (rail-based only) */
    railSpacing?: number;
    /** Exact X positions for each rail (rail-based only) */
    railPositions?: number[];
    /** List of compatible carrier FQNs (rail-based only) */
    compatibleCarriers?: string[];
    // === Slot-based deck properties ===
    /** Slot specifications (slot-based only) */
    slots?: DeckSlotSpec[];
    /** Number of slots (slot-based only) */
    numSlots?: number;
}

/**
 * Carrier definition from hardware catalog.
 */
export interface CarrierDefinition {
    /** PLR fully qualified name */
    fqn: string;
    /** Human-readable name */
    name: string;
    /** Carrier type */
    type: CarrierType;
    /** Number of rails this carrier spans */
    railSpan: number;
    /** Number of slots on this carrier */
    numSlots: number;
    /** List of compatible resource types */
    compatibleResourceTypes: string[];
    /** Physical dimensions in mm */
    dimensions: {
        width: number;
        height: number;
        depth: number;
    };
}
