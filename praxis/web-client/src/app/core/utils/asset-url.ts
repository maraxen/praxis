/**
 * Utility for resolving asset paths that respect the app's base href.
 * This is critical for GitHub Pages deployments where the app is served
 * from a subdirectory (e.g., /praxis/).
 */
import { environment } from '../../../environments/environment';

/**
 * Get the base href from the document's <base> tag.
 * Falls back to '/' if not set.
 */
export function getBaseHref(): string {
    // Prefer environment configuration if available
    if ((environment as any).baseHref) {
        return (environment as any).baseHref;
    }

    if (typeof document === 'undefined') {
        return '/';
    }

    const baseEl = document.querySelector('base');
    if (baseEl) {
        const href = baseEl.getAttribute('href');
        if (href) {
            return href;
        }
    }

    // Fallback: try document.baseURI
    try {
        const baseUri = new URL(document.baseURI);
        return baseUri.pathname;
    } catch {
        return '/';
    }
}

/**
 * Resolve an asset path to be relative to the app's base href.
 * 
 * @param assetPath - The asset path, e.g., '/assets/wasm/file.wasm' or 'assets/db/praxis.db'
 * @returns The fully resolved path including base href
 * 
 * @example
 * // With base href '/praxis/'
 * assetUrl('/assets/wasm/sql-wasm.wasm') // => '/praxis/assets/wasm/sql-wasm.wasm'
 * assetUrl('assets/db/praxis.db')        // => '/praxis/assets/db/praxis.db'
 */
export function assetUrl(assetPath: string): string {
    const base = getBaseHref();

    // Remove leading slash from asset path if present
    const cleanPath = assetPath.startsWith('/') ? assetPath.slice(1) : assetPath;

    // Ensure base ends with slash
    const cleanBase = base.endsWith('/') ? base : base + '/';

    return cleanBase + cleanPath;
}

/**
 * Create a locateFile function for libraries like sql.js that need to resolve WASM files.
 * 
 * @example
 * const SQL = await initSqlJs({
 *   locateFile: createWasmLocator('assets/wasm/')
 * });
 */
export function createWasmLocator(wasmDir: string = 'assets/wasm/'): (file: string) => string {
    return (file: string) => assetUrl(`${wasmDir}${file}`);
}
