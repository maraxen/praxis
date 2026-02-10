/**
 * Centralized machine/resource display configuration.
 *
 * Single source of truth for icon, color, and label mappings by PLR category.
 * Uses Material System tokens (not hardcoded Tailwind) for dark mode safety.
 */

export interface AssetDisplayConfig {
    icon: string;
    bgClass: string;
    textClass: string;
    label: string;
}

/** Machine category display mappings */
const MACHINE_DISPLAY: Record<string, AssetDisplayConfig> = {
    'LiquidHandler': {
        icon: 'precision_manufacturing',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-primary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-primary)]',
        label: 'Liquid Handler',
    },
    'PlateReader': {
        icon: 'visibility',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-secondary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-secondary)]',
        label: 'Plate Reader',
    },
    'HeaterShaker': {
        icon: 'thermostat',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-tertiary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-tertiary)]',
        label: 'Heater Shaker',
    },
    'Shaker': {
        icon: 'vibration',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-tertiary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-tertiary)]',
        label: 'Shaker',
    },
    'Centrifuge': {
        icon: 'rotate_right',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-secondary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-secondary)]',
        label: 'Centrifuge',
    },
    'Incubator': {
        icon: 'thermostat_auto',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-tertiary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-tertiary)]',
        label: 'Incubator',
    },
    'TemperatureController': {
        icon: 'device_thermostat',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-tertiary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-tertiary)]',
        label: 'Temperature Controller',
    },
    'Thermocycler': {
        icon: 'cycle',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-tertiary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-tertiary)]',
        label: 'Thermocycler',
    },
    'Pump': {
        icon: 'water',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-primary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-primary)]',
        label: 'Pump',
    },
};

/** Resource category display mappings */
const RESOURCE_DISPLAY: Record<string, AssetDisplayConfig> = {
    'Plate': {
        icon: 'grid_view',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-tertiary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-tertiary)]',
        label: 'Plate',
    },
    'TipRack': {
        icon: 'view_in_ar',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-secondary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-secondary)]',
        label: 'Tip Rack',
    },
    'Trough': {
        icon: 'water_drop',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-primary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-primary)]',
        label: 'Trough',
    },
    'Reservoir': {
        icon: 'water_drop',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-primary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-primary)]',
        label: 'Reservoir',
    },
    'Carrier': {
        icon: 'apps',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-on-surface)_8%,transparent)]',
        textClass: 'text-[var(--mat-sys-on-surface-variant)]',
        label: 'Carrier',
    },
    'Deck': {
        icon: 'dashboard',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-on-surface)_8%,transparent)]',
        textClass: 'text-[var(--mat-sys-on-surface-variant)]',
        label: 'Deck',
    },
    'Tube': {
        icon: 'science',
        bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-tertiary)_12%,transparent)]',
        textClass: 'text-[var(--mat-sys-tertiary)]',
        label: 'Tube',
    },
};

const DEFAULT_MACHINE_DISPLAY: AssetDisplayConfig = {
    icon: 'precision_manufacturing',
    bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-on-surface)_8%,transparent)]',
    textClass: 'text-[var(--mat-sys-on-surface-variant)]',
    label: 'Laboratory Machine',
};

const DEFAULT_RESOURCE_DISPLAY: AssetDisplayConfig = {
    icon: 'science',
    bgClass: 'bg-[color-mix(in_srgb,var(--mat-sys-tertiary)_12%,transparent)]',
    textClass: 'text-[var(--mat-sys-tertiary)]',
    label: 'Resource',
};

/**
 * Get display configuration for a machine category.
 * @param category - PascalCase machine category (e.g., 'LiquidHandler')
 */
export function getMachineDisplay(category: string | null | undefined): AssetDisplayConfig {
    if (!category) return DEFAULT_MACHINE_DISPLAY;
    return MACHINE_DISPLAY[category] ?? DEFAULT_MACHINE_DISPLAY;
}

/**
 * Get display configuration for a resource category.
 * @param category - PascalCase resource category (e.g., 'Plate', 'TipRack')
 */
export function getResourceDisplay(category: string | null | undefined): AssetDisplayConfig {
    if (!category) return DEFAULT_RESOURCE_DISPLAY;
    return RESOURCE_DISPLAY[category] ?? DEFAULT_RESOURCE_DISPLAY;
}

/**
 * Get the icon name for any category (machine or resource).
 * Convenience function for templates that only need the icon.
 */
export function getCategoryIcon(category: string | null | undefined): string {
    if (!category) return 'extension';
    return MACHINE_DISPLAY[category]?.icon
        ?? RESOURCE_DISPLAY[category]?.icon
        ?? 'extension';
}
