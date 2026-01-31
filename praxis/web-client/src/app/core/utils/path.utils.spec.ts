import { describe, expect, it } from 'vitest';
import { PathUtils } from './path.utils';

describe('PathUtils', () => {
    describe('normalizeBaseHref', () => {
        it('should add leading and trailing slashes when both are missing', () => {
            expect(PathUtils.normalizeBaseHref('praxis')).toBe('/praxis/');
        });

        it('should add trailing slash when only leading slash exists', () => {
            expect(PathUtils.normalizeBaseHref('/praxis')).toBe('/praxis/');
        });

        it('should add leading slash when only trailing slash exists', () => {
            expect(PathUtils.normalizeBaseHref('praxis/')).toBe('/praxis/');
        });

        it('should return unchanged when both slashes exist', () => {
            expect(PathUtils.normalizeBaseHref('/praxis/')).toBe('/praxis/');
        });

        it('should handle nested paths', () => {
            expect(PathUtils.normalizeBaseHref('org/praxis')).toBe('/org/praxis/');
            expect(PathUtils.normalizeBaseHref('/org/praxis')).toBe('/org/praxis/');
            expect(PathUtils.normalizeBaseHref('/org/praxis/')).toBe('/org/praxis/');
        });

        it('should return "/" for empty string', () => {
            expect(PathUtils.normalizeBaseHref('')).toBe('/');
        });

        it('should return "/" for root path', () => {
            expect(PathUtils.normalizeBaseHref('/')).toBe('/');
        });

        it('should return "/" for null', () => {
            expect(PathUtils.normalizeBaseHref(null)).toBe('/');
        });

        it('should return "/" for undefined', () => {
            expect(PathUtils.normalizeBaseHref(undefined)).toBe('/');
        });

        // Edge case: whitespace-only strings
        it('should handle whitespace in paths (real case)', () => {
            // Whitespace in baseHref is unlikely but should be preserved if present
            expect(PathUtils.normalizeBaseHref(' praxis ')).toBe('/ praxis /');
        });
    });
});
