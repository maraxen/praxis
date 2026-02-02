import { PLR_RESOURCE_DEFINITIONS } from '@assets/browser-data/plr-definitions';

export function getValidPLRClassNames(): Set<string> {
  const classes = new Set<string>();
  for (const def of PLR_RESOURCE_DEFINITIONS) {
    const className = def.fqn.split('.').pop();
    if (className) {
      classes.add(className);
    }
  }
  return classes;
}

export function validatePLRClassName(fqn: string, validClasses: Set<string>): boolean {
  const className = fqn.split('.').pop();
  return !!className && validClasses.has(className);
}
