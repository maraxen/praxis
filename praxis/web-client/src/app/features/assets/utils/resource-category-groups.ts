/**
 * Utility for mapping PLR resource categories to UI-friendly groups.
 */

export type ResourceUiGroup = 'Carriers' | 'Holders' | 'Plates' | 'TipRacks' | 'Containers' | 'Other';

export const UI_GROUP_ORDER: ResourceUiGroup[] = [
    'Carriers',
    'Holders',
    'Plates',
    'TipRacks',
    'Containers',
    'Other',
];

// Categories to HIDE from Add Resource UI
// These are sub-elements that don't exist independently
export const HIDDEN_CATEGORIES: Set<string> = new Set([
    'deck',
    'resource',     // Base Resource class or generic utility functions
    'well',         // Sub-element of Plate
    'tip_spot',     // Sub-element of TipRack
]);

/**
 * Convert PascalCase/camelCase/kebab-case to snake_case.
 * Examples:
 *   TipCarrier → tip_carrier
 *   plateCarrier → plate_carrier
 *   mfx-carrier → mfx_carrier
 */
function toSnakeCase(str: string): string {
    return str
        // Insert underscore between lowercase and uppercase (camelCase/PascalCase)
        .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
        // Insert underscore between consecutive uppercase and following lowercase (e.g., MFXCarrier → MFX_Carrier)
        .replace(/([A-Z]+)([A-Z][a-z])/g, '$1_$2')
        .toLowerCase()
        // Convert kebab-case to snake_case
        .replace(/-/g, '_');
}

export const CATEGORY_TO_UI_GROUP: Record<string, ResourceUiGroup> = {
    // Carriers (hold labware on deck)
    'plate_carrier': 'Carriers',
    'tip_carrier': 'Carriers',
    'trough_carrier': 'Carriers',
    'tube_carrier': 'Carriers',
    'carrier': 'Carriers',
    'mfx_carrier': 'Carriers',      // Hamilton MFX carriers
    'mfx_module': 'Carriers',       // Hamilton MFX modules

    // Holders (racks for tubes, etc.)
    'tube_rack': 'Holders',
    'aluminum_block': 'Holders',    // PCR blocks, cooling blocks

    // Plates (primary consumable)
    'plate': 'Plates',

    // TipRacks (primary consumable)
    'tip_rack': 'TipRacks',

    // Containers (simple vessels, lids)
    'trough': 'Containers',
    'tube': 'Containers',           // Tubes have independent life from TubeRack
    'lid': 'Containers',
    'petri_dish': 'Containers',
    'container': 'Containers',
    'reservoir': 'Containers',
    'trash': 'Containers',
};

/**
 * Check if a resource category should be hidden from the UI.
 * Case-insensitive.
 */
export function shouldHideCategory(plrCategory: string | null | undefined): boolean {
    if (!plrCategory) return true;
    const normalized = toSnakeCase(plrCategory);
    return HIDDEN_CATEGORIES.has(normalized);
}

/**
 * Get the standardized UI group for a PLR category.
 */
export function getUiGroup(plrCategory: string | null | undefined): ResourceUiGroup {
    if (!plrCategory) return 'Other';
    const normalized = toSnakeCase(plrCategory);
    // Direct match
    if (CATEGORY_TO_UI_GROUP[normalized]) return CATEGORY_TO_UI_GROUP[normalized];
    // Suffix match: "tecan_tip_carrier" ends with "tip_carrier" → Carriers
    for (const [key, group] of Object.entries(CATEGORY_TO_UI_GROUP)) {
        if (normalized.endsWith(key)) return group;
    }
    return 'Other';
}

/**
 * Get the sub-category (e.g., 'plate_carrier', 'tip_carrier') for hierarchical display.
 * Returns normalized snake_case category.
 */
export function getSubCategory(plrCategory: string | null | undefined): string {
    if (!plrCategory) return 'other';
    return toSnakeCase(plrCategory);
}
