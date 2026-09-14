import { describe, it, expect } from 'vitest';
import { extractUniqueNameParts } from './name-parser';

describe('extractUniqueNameParts', () => {
    it('should extract unique suffix when names share a common prefix', () => {
        const names = ['Hamilton Core96 Tip Rack', 'Hamilton Core96 Plate'];
        const result = extractUniqueNameParts(names);
        expect(result.get('Hamilton Core96 Tip Rack')).toBe('Tip Rack');
        expect(result.get('Hamilton Core96 Plate')).toBe('Plate');
    });

    it('should extract unique prefix when names share a common suffix', () => {
        const names = ['Corning 384 Well', 'Falcon 384 Well'];
        const result = extractUniqueNameParts(names);
        expect(result.get('Corning 384 Well')).toBe('Corning');
        expect(result.get('Falcon 384 Well')).toBe('Falcon');
    });

    it('should extract middle part when names share prefix and suffix', () => {
        const names = ['Hamilton 1000ul Tip', 'Hamilton 50ul Tip'];
        const result = extractUniqueNameParts(names);
        expect(result.get('Hamilton 1000ul Tip')).toBe('1000ul');
        expect(result.get('Hamilton 50ul Tip')).toBe('50ul');
    });

    it('should handle names with no common parts', () => {
        const names = ['Alpha', 'Beta', 'Gamma'];
        const result = extractUniqueNameParts(names);
        expect(result.get('Alpha')).toBe('Alpha');
        expect(result.get('Beta')).toBe('Beta');
        expect(result.get('Gamma')).toBe('Gamma');
    });

    it('should handle single name', () => {
        const names = ['Single Asset'];
        const result = extractUniqueNameParts(names);
        expect(result.get('Single Asset')).toBe('Single Asset');
    });

    it('should handle empty list', () => {
        const result = extractUniqueNameParts([]);
        expect(result.size).toBe(0);
    });

    it('should fallback to full name if stripping prefix/suffix causes collisions', () => {
        const names = ['Plate 1', 'Plate 2', 'Box Plate 1'];
        // Common prefix: none
        // Common suffix: ' 1' (for 1 and 3) but common across ALL is none
        const result = extractUniqueNameParts(names);
        expect(result.get('Plate 1')).toBe('Plate 1');
        expect(result.get('Plate 2')).toBe('Plate 2');
        expect(result.get('Box Plate 1')).toBe('Box Plate 1');
    });

    it('should handle cases where subset of names have common prefix but all dont', () => {
        const names = ['ABC 1', 'ABC 2', 'XYZ 3'];
        const result = extractUniqueNameParts(names);
        // No common prefix across all
        expect(result.get('ABC 1')).toBe('ABC 1');
        expect(result.get('ABC 2')).toBe('ABC 2');
        expect(result.get('XYZ 3')).toBe('XYZ 3');
    });

    it('should handle array with empty strings', () => {
        const names = ['', 'A', ''];
        const result = extractUniqueNameParts(names);
        expect(result.get('')).toBe('');
        expect(result.get('A')).toBe('A');
    });

    it('should handle names with special characters', () => {
        const names = ['Wrapper #1', 'Wrapper #2'];
        const result = extractUniqueNameParts(names);
        // Tokens: ['Wrapper', ' ', '#1'] vs ['Wrapper', ' ', '#2']
        // Common prefix: 'Wrapper', ' '
        expect(result.get('Wrapper #1')).toBe('#1');
        expect(result.get('Wrapper #2')).toBe('#2');
    });

    it('should handle very long strings', () => {
        // Note: The parser relies on delimiters (space, _, -) to split tokens.
        // Long strings without delimiters are treated as single tokens.
        const prefix = 'A'.repeat(100) + ' ';
        const suffix = ' ' + 'B'.repeat(100);
        const names = [prefix + 'Unique1' + suffix, prefix + 'Unique2' + suffix];
        const result = extractUniqueNameParts(names);
        expect(result.get(names[0])).toBe('Unique1');
        expect(result.get(names[1])).toBe('Unique2');
    });

    it('should handle Unicode characters', () => {
        const names = ['µL Tip', 'mL Tip'];
        const result = extractUniqueNameParts(names);
        // ' Tip' is common suffix.
        expect(result.get('µL Tip')).toBe('µL');
        expect(result.get('mL Tip')).toBe('mL');
    });

    it('should handle duplicate names by falling back to full name', () => {
         const names = ['Same', 'Same'];
         const result = extractUniqueNameParts(names);
         expect(result.get('Same')).toBe('Same');
    });

    it('should handle mixed delimiters but similar structure', () => {
        const names = ['A-Middle1-B', 'A_Middle2_B'];
        const result = extractUniqueNameParts(names);
        // Prefix A, Suffix B. Middle: -Middle1- and _Middle2_.
        // Trimming separators -> Middle1, Middle2
        expect(result.get('A-Middle1-B')).toBe('Middle1');
        expect(result.get('A_Middle2_B')).toBe('Middle2');
    });
});
