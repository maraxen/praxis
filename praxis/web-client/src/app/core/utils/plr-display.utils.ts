/**
 * Display utilities for PLR identifiers.
 *
 * Transforms PascalCase enum values, snake_case normalized names,
 * and PLR resource identifiers into human-readable display strings.
 *
 * IMPORTANT: These are DISPLAY-ONLY transforms. All matching/filtering
 * logic should continue using raw enum values or snake_case keys.
 */

/** Known abbreviations and unit replacements */
const UNIT_MAP: Record<string, string> = {
    'ul': 'µL',
    'ml': 'mL',
    'mm': 'mm',
    'pcr': 'PCR',
    'plr': 'PLR',
    'mfx': 'MFX',
    'ot': 'OT',
    'usb': 'USB',
    'ftdi': 'FTDI',
    'hid': 'HID',
};

/**
 * Convert PascalCase to spaced words.
 * @example "LiquidHandler" → "Liquid Handler"
 * @example "HeaterShaker" → "Heater Shaker"
 * @example "MFXCarrier" → "MFX Carrier"
 */
export function fromPascalCase(str: string): string {
    return str
        .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
        .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
}

/**
 * Convert snake_case to Title Case with unit awareness.
 * @example "tip_carrier" → "Tip Carrier"
 * @example "corning_96_wellplate_360ul_flat" → "Corning 96 Wellplate 360µL Flat"
 */
export function fromSnakeCase(str: string): string {
    return str
        .split('_')
        .map(word => UNIT_MAP[word.toLowerCase()] ?? capitalize(word))
        .join(' ');
}

/**
 * Smart humanize — detects input format and applies the right transform.
 * @example "LiquidHandler" → "Liquid Handler"
 * @example "tip_carrier" → "Tip Carrier"
 * @example "corning_96_wellplate_360ul_flat" → "Corning 96 Wellplate 360µL Flat"
 */
export function humanize(identifier: string | null | undefined): string {
    if (!identifier) return '';

    // If contains underscores, treat as snake_case / PLR name
    if (identifier.includes('_')) {
        return fromSnakeCase(identifier);
    }

    // If has internal camelCase boundary, treat as PascalCase
    if (/[a-z][A-Z]/.test(identifier)) {
        return fromPascalCase(identifier);
    }

    // Already a single word or already humanized
    return capitalize(identifier);
}

/** Capitalize first letter, lowercase rest */
function capitalize(word: string): string {
    if (!word) return '';
    return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
}
