import { PLR_RESOURCE_DEFINITIONS, PLR_MACHINE_DEFINITIONS } from '@assets/browser-data/plr-definitions';

/**
 * Returns a set of all valid PLR resource and machine FQNs.
 */
export function getValidPLRClassNames(): Set<string> {
    const names = new Set<string>();
    PLR_RESOURCE_DEFINITIONS.forEach(d => names.add(d.fqn));
    PLR_MACHINE_DEFINITIONS.forEach(d => names.add(d.fqn));
    return names;
}

/**
 * Validates if a given FQN is a known and supported PLR class.
 */
export function validatePLRClassName(fqn: string, validNames: Set<string>): boolean {
    return validNames.has(fqn);
}
