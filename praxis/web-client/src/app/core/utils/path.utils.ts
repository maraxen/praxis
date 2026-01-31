/**
 * Path utilities for consistent URL/path handling across the application.
 * Critical for GitHub Pages deployments where baseHref variations can break asset loading.
 */
export class PathUtils {
    /**
     * Normalizes baseHref to have both leading and trailing slashes.
     * This ensures consistent path resolution across different deployment contexts.
     *
     * @param baseHref - The base href value, typically from document.querySelector('base')?.getAttribute('href')
     * @returns Normalized baseHref with leading and trailing slashes
     *
     * @example
     * PathUtils.normalizeBaseHref('praxis')    // '/praxis/'
     * PathUtils.normalizeBaseHref('/praxis')   // '/praxis/'
     * PathUtils.normalizeBaseHref('praxis/')   // '/praxis/'
     * PathUtils.normalizeBaseHref('/praxis/')  // '/praxis/'
     * PathUtils.normalizeBaseHref('')          // '/'
     * PathUtils.normalizeBaseHref('/')         // '/'
     * PathUtils.normalizeBaseHref(null)        // '/'
     * PathUtils.normalizeBaseHref(undefined)   // '/'
     */
    static normalizeBaseHref(baseHref: string | null | undefined): string {
        if (!baseHref || baseHref === '/') {
            return '/';
        }

        let normalized = baseHref;

        // Ensure leading slash
        if (!normalized.startsWith('/')) {
            normalized = '/' + normalized;
        }

        // Ensure trailing slash
        if (!normalized.endsWith('/')) {
            normalized = normalized + '/';
        }

        return normalized;
    }
}
