import { RouteReuseStrategy, ActivatedRouteSnapshot, DetachedRouteHandle } from '@angular/router';

/**
 * Custom RouteReuseStrategy that preserves the PlaygroundComponent (and its
 * JupyterLite iframe + kernel) when the user navigates away and back.
 *
 * Without this, Angular destroys the component on navigation, killing the
 * Pyodide kernel, losing all state, and requiring a full re-bootstrap (~10s).
 *
 * Only the 'playground' route is cached — all other routes use default behavior.
 */
export class PlaygroundRouteReuseStrategy implements RouteReuseStrategy {
    private storedHandles = new Map<string, DetachedRouteHandle>();

    /** Decide whether the route should be detached (stored) on leave. */
    shouldDetach(route: ActivatedRouteSnapshot): boolean {
        return route.routeConfig?.path === 'playground';
    }

    /** Store the detached route handle. */
    store(route: ActivatedRouteSnapshot, handle: DetachedRouteHandle | null): void {
        if (handle && route.routeConfig?.path === 'playground') {
            this.storedHandles.set('playground', handle);
        }
    }

    /** Check if we have a stored handle for this route. */
    shouldAttach(route: ActivatedRouteSnapshot): boolean {
        return route.routeConfig?.path === 'playground'
            && this.storedHandles.has('playground');
    }

    /** Return the stored handle. */
    retrieve(route: ActivatedRouteSnapshot): DetachedRouteHandle | null {
        if (route.routeConfig?.path === 'playground') {
            return this.storedHandles.get('playground') || null;
        }
        return null;
    }

    /** Default reuse behavior for all other routes. */
    shouldReuseRoute(
        future: ActivatedRouteSnapshot,
        curr: ActivatedRouteSnapshot
    ): boolean {
        return future.routeConfig === curr.routeConfig;
    }
}
