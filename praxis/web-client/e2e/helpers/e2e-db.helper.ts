import { Page } from '@playwright/test';

/**
 * E2E Database Helper — wraps the __e2e test API exposed by SqliteService.
 *
 * The __e2e API is defined in sqlite.service.ts and provides:
 *   - query(sql, params?)  → Promise<Record<string, any>[]>  (SELECT)
 *   - exec(sql, params?)   → Promise<void>                    (INSERT/UPDATE/DELETE)
 *   - count(table, where?) → Promise<number>                  (COUNT shortcut)
 *   - isReady()            → boolean                          (DB readiness check)
 *
 * For service-layer calls (getProtocols, getMachines, etc.), we access the
 * sqliteService directly and use its built-in Observable-to-Promise conversion
 * via the subscriber pattern (no dynamic import('rxjs') needed).
 *
 * Table Reference (praxis.db schema):
 *   function_protocol_definitions  (NOT "protocol_definitions")
 *   protocol_runs                  (NOT "run_history")
 *   machines                       (instances)
 *   machine_definitions            (catalog)
 *   machine_frontend_definitions   (frontend bindings)
 *   machine_backend_definitions    (backend/driver bindings)
 *   resources                      (instances)
 *   resource_definitions           (catalog)
 *   decks, deck_definition_catalog, deck_position_definitions
 *   workcells, function_call_logs, function_data_outputs
 *   well_data_outputs, parameter_definitions
 *   protocol_asset_requirements, state_resolution_log
 *   protocol_source_repositories, file_system_protocol_sources
 */

// ─────────────────────────────────────────────────────────────────────────────
// Core DB operations (via __e2e API)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Wait for SQLite OPFS service to be ready.
 */
export async function waitForDbReady(page: Page, timeout = 60000): Promise<void> {
    await page.waitForFunction(
        () => {
            const e2e = (window as any).__e2e;
            return e2e?.isReady() === true;
        },
        null,
        { timeout }
    );
}

/**
 * Execute a SELECT query via the __e2e test API.
 * Returns rows as an array of objects with named keys.
 */
export async function dbQuery(page: Page, sql: string, params?: any[]): Promise<Record<string, any>[]> {
    return page.evaluate(
        async ({ sql, params }) => {
            const e2e = (window as any).__e2e;
            if (!e2e) throw new Error('__e2e test API not found on window');
            return e2e.query(sql, params);
        },
        { sql, params }
    );
}

/**
 * Execute a write statement (INSERT/UPDATE/DELETE) via the __e2e test API.
 */
export async function dbExec(page: Page, sql: string, params?: any[]): Promise<void> {
    await page.evaluate(
        async ({ sql, params }) => {
            const e2e = (window as any).__e2e;
            if (!e2e) throw new Error('__e2e test API not found on window');
            await e2e.exec(sql, params);
        },
        { sql, params }
    );
}

/**
 * Execute a query and return a single scalar value (first column of first row).
 */
export async function dbQueryScalar<T = number>(page: Page, sql: string, params?: any[]): Promise<T> {
    const rows = await dbQuery(page, sql, params);
    if (rows.length === 0) throw new Error(`dbQueryScalar: no rows returned for: ${sql}`);
    const firstRow = rows[0];
    const keys = Object.keys(firstRow);
    return firstRow[keys[0]] as T;
}

/**
 * Get count of rows in a table.
 */
export async function dbCount(page: Page, table: string, where?: string, params?: any[]): Promise<number> {
    return page.evaluate(
        async ({ table, where, params }) => {
            const e2e = (window as any).__e2e;
            if (!e2e) throw new Error('__e2e test API not found on window');
            return e2e.count(table, where, params);
        },
        { table, where, params }
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Service-layer helpers (via sqliteService — uses subscriber pattern, no rxjs import)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Helper that subscribes to a service-layer Observable and returns the first value.
 * This avoids needing `import('rxjs')` inside page.evaluate().
 */
async function callServiceMethod(page: Page, methodName: string, args?: any[]): Promise<any> {
    return page.evaluate(
        async ({ methodName, args }) => {
            const service = (window as any).sqliteService;
            if (!service) throw new Error('sqliteService not found on window');
            const method = service[methodName];
            if (!method) throw new Error(`sqliteService.${methodName} not found`);

            // Subscribe to the Observable and return the first emitted value
            return new Promise((resolve, reject) => {
                const obs = args ? method.call(service, ...args) : method.call(service);
                const sub = obs.subscribe({
                    next: (val: any) => { resolve(val); sub.unsubscribe(); },
                    error: (err: any) => { reject(err); sub.unsubscribe(); }
                });
            });
        },
        { methodName, args }
    );
}

/** Get all protocols via the service layer. */
export async function getProtocols(page: Page): Promise<any[]> {
    return callServiceMethod(page, 'getProtocols');
}

/** Get all machines via the service layer. */
export async function getMachines(page: Page): Promise<any[]> {
    return callServiceMethod(page, 'getMachines');
}

/** Get all resources via the service layer. */
export async function getResources(page: Page): Promise<any[]> {
    return callServiceMethod(page, 'getResources');
}

/** Get protocol runs via the service layer. */
export async function getProtocolRuns(page: Page): Promise<any[]> {
    return callServiceMethod(page, 'getProtocolRuns');
}

/** Create a protocol run via the service layer. */
export async function createProtocolRun(page: Page, entity: Record<string, any>): Promise<any> {
    return callServiceMethod(page, 'createProtocolRun', [entity]);
}

/** Get machine definitions (catalog) via the service layer. */
export async function getMachineDefinitions(page: Page): Promise<any[]> {
    return callServiceMethod(page, 'getMachineDefinitions');
}

/** Get resource definitions (catalog) via the service layer. */
export async function getResourceDefinitions(page: Page): Promise<any[]> {
    return callServiceMethod(page, 'getResourceDefinitions');
}

/** Reset database to defaults via the service layer. */
export async function resetDatabase(page: Page): Promise<void> {
    await callServiceMethod(page, 'resetToDefaults');
}

/** Get the current database name. */
export async function getDatabaseName(page: Page): Promise<string> {
    return page.evaluate(() => {
        const service = (window as any).sqliteService;
        return service?.getDatabaseName?.() || 'unknown';
    });
}
