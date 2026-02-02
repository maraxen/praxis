import { getValidPLRClassNames, validatePLRClassName } from './plr-validator';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the PLR_RESOURCE_DEFINITIONS
vi.mock('@assets/browser-data/plr-definitions', () => ({
  PLR_RESOURCE_DEFINITIONS: [
    { fqn: 'pylabrobot.resources.hamilton.carriers.PLT_CAR_L5AC_A00' },
    { fqn: 'pylabrobot.resources.corning_costar.plates.Cor_96_wellplate_360ul_Fb' },
  ],
}));

describe('PLR Validator', () => {
  describe('getValidPLRClassNames', () => {
    it('should extract class names from definitions', () => {
      const classNames = getValidPLRClassNames();
      expect(classNames).toBeInstanceOf(Set);
      expect(classNames.has('PLT_CAR_L5AC_A00')).toBe(true);
      expect(classNames.has('Cor_96_wellplate_360ul_Fb')).toBe(true);
    });

    it('should not include uppercase versions of class names', () => {
      const classNames = getValidPLRClassNames();
      expect(classNames.has('PLT_CAR_L5AC_A00')).toBe(true);
      expect(classNames.has('COR_96_WELLPLATE_360UL_FB')).toBe(false);
    });
  });

  describe('validatePLRClassName', () => {
    let validClasses: Set<string>;

    beforeEach(() => {
      validClasses = getValidPLRClassNames();
    });

    it('should return true for a valid FQN', () => {
      const isValid = validatePLRClassName('pylabrobot.resources.hamilton.carriers.PLT_CAR_L5AC_A00', validClasses);
      expect(isValid).toBe(true);
    });

    it('should return false for an invalid FQN', () => {
      const isValid = validatePLRClassName('pylabrobot.resources.non_existent.Carrier', validClasses);
      expect(isValid).toBe(false);
    });

    it('should return false for a malformed FQN', () => {
      const isValid = validatePLRClassName('InvalidFQN', validClasses);
      expect(isValid).toBe(false);
    });

    it('should return false for an empty string', () => {
      const isValid = validatePLRClassName('', validClasses);
      expect(isValid).toBe(false);
    });
  });
});
