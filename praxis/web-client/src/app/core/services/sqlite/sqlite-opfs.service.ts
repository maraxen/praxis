import { Injectable } from '@angular/core';
import { Observable, Subject, filter, take, switchMap, map, from, of, concatMap, last, catchError } from 'rxjs';
import {
    SqliteWorkerRequest,
    SqliteWorkerResponse,
    SqliteExecResult,
    RowMode,
    SqliteExecRequest,
    SqliteInitRequest,
    SqliteImportRequest,
    SqliteBatchExecRequest,
    SqliteSchemaMismatchPayload,
    CURRENT_SCHEMA_VERSION
} from '@core/workers/sqlite-opfs.types';

import { assetUrl } from '@core/utils/asset-url';
import {
    OFFLINE_CAPABILITY_OVERRIDES,
    PLR_MACHINE_DEFINITIONS,
    PLR_RESOURCE_DEFINITIONS,
    PLR_FRONTEND_DEFINITIONS,
    PLR_BACKEND_DEFINITIONS
} from '@assets/browser-data/plr-definitions';

@Injectable({
    providedIn: 'root'
})
export class SqliteOpfsService {
    private worker: Worker | null = null;
    private responses$ = new Subject<SqliteWorkerResponse>();
    private initPromise: Promise<void> | null = null;
    /** Track current database name to detect when a different DB is requested */
    private currentDbName: string | undefined = undefined;

    constructor() { }

    /**
     * Initialize the SQLite worker and open/initialize the database.
     * Lazy initialization of the Web Worker occurs on the first call.
     * 
     * OPFS is now the ONLY storage mechanism for browser mode.
     * The legacy sql.js + IndexedDB path has been removed.
     * 
     * @param dbName Optional database name (defaults to 'praxis.db' in worker)
     * @returns Observable that completes when initialization is successful
     */
    init(dbName?: string): Observable<void> {
        // Critical: If a different database is requested, reset the cached promise
        // This prevents parallel workers with different dbNames from sharing promises
        if (this.initPromise && this.currentDbName !== dbName) {
            console.log(`[SqliteOpfsService] Database changed from ${this.currentDbName} to ${dbName}, resetting init promise`);
            this.initPromise = null;
        }

        if (this.initPromise) {
            return from(this.initPromise);
        }

        this.currentDbName = dbName;

        this.initPromise = new Promise<void>((resolve, reject) => {
            if (!this.worker) {
                // Initialize the worker using the standard Angular worker pattern.
                // Note: The bundler (esbuild/webpack) detects this pattern to chunk the worker.
                this.worker = new Worker(new URL('../../workers/sqlite-opfs.worker', import.meta.url), {
                    type: 'module'
                });

                this.worker.onmessage = ({ data }: { data: SqliteWorkerResponse }) => {
                    this.responses$.next(data);
                };

                this.worker.onerror = (err) => {
                    // Log but don't reject - Vite dev server fires harmless 'export' syntax errors
                    // during worker module loading that don't actually break the worker.
                    // Actual failures are handled via message-based error responses.
                    console.warn('[SqliteOpfsService] Worker error (non-fatal):', err);
                };
            }

            console.time('DB_INIT_TOTAL');
            const payload: SqliteInitRequest = { dbName };
            this.sendRequest<unknown>('init', payload).pipe(
                switchMap((result: any) => {
                    // Check for schema mismatch response
                    if (result?.type === 'schema_mismatch') {
                        const mismatch = result as SqliteSchemaMismatchPayload;
                        console.warn(`[SqliteOpfsService] Schema version mismatch: DB=${mismatch.currentVersion}, App=${mismatch.expectedVersion}`);
                        return this.handleSchemaMismatch(mismatch.currentVersion, mismatch.expectedVersion);
                    }
                    return this.ensureSchemaAndSeeds();
                })
            ).subscribe({
                next: () => {
                    console.timeEnd('DB_INIT_TOTAL');
                    console.log('[SqliteOpfsService] Database initialized successfully.');
                    resolve();
                },
                error: (err) => {
                    console.error('[SqliteOpfsService] Database initialization failed:', err);
                    this.initPromise = null; // Reset promise so it can be retried
                    reject(err);
                }
            });
        });

        return from(this.initPromise);
    }

    /**
     * Ensure the database has the required schema and initial data.
     * 
     * CRITICAL: We check for protocols specifically, not just tables.
     * Protocols ONLY exist in the prebuilt praxis.db - the TypeScript fallback
     * seeds machines/resources but NOT protocols. Without this check, E2E tests
     * with stale OPFS state would have tables but no protocols.
     */
    private ensureSchemaAndSeeds(): Observable<void> {
        // Check for protocols specifically - they only exist in praxis.db
        return this.exec("SELECT COUNT(*) as count FROM function_protocol_definitions").pipe(
            catchError(() => {
                // Table doesn't exist yet - need full initialization
                return of({ resultRows: [{ count: 0 }] } as SqliteExecResult);
            }),
            switchMap(result => {
                const count = (result.resultRows[0] as any)?.count || 0;
                if (count === 0) {
                    console.log('[SqliteOpfsService] No protocols found. Loading fresh database from praxis.db...');
                    return this.initializeFreshDatabase();
                }
                console.log(`[SqliteOpfsService] Database has ${count} protocols. Checking for assets...`);
                // Even if protocols exist, we might be missing inventory assets
                return this.seedDefaultAssets().pipe(
                    map(() => {
                        console.log('[SqliteOpfsService] Asset check/seeding complete. Ready.');
                    })
                );
            })
        );
    }

    /**
     * Initialize a fresh database, preferring the prebuilt praxis.db from the generator.
     * Falls back to schema.sql + TypeScript seeding if prebuilt is unavailable.
     * 
     * The prebuilt database contains:
     * - All discovered protocols with full parameter metadata
     * - Complete deck geometry definitions
     * - Backend→Frontend relationships from static analysis
     * - Richer definition catalogs than TypeScript arrays
     */
    private initializeFreshDatabase(): Observable<void> {
        console.log('[SqliteOpfsService] Attempting to load prebuilt database...');

        return from(fetch(assetUrl('assets/db/praxis.db'))).pipe(
            switchMap(res => {
                if (!res.ok) {
                    console.warn(`[SqliteOpfsService] Prebuilt DB fetch failed (${res.status}), falling back to schema + seeds`);
                    return this.initializeFromSchema();
                }
                return from(res.arrayBuffer()).pipe(
                    map(ab => new Uint8Array(ab)),
                    switchMap(data => {
                        console.log(`[SqliteOpfsService] Loading prebuilt database (${data.length} bytes)...`);
                        return this.importDatabase(data);
                    }),
                    map(() => {
                        console.log('[SqliteOpfsService] Prebuilt database loaded successfully.');
                    })
                );
            }),
            catchError(err => {
                console.warn('[SqliteOpfsService] Prebuilt DB load error:', err);
                return this.initializeFromSchema();
            })
        );
    }

    /**
     * Handle schema version mismatch by prompting user to reset.
     * For now, we auto-reset; a production app would show a dialog.
     */
    private handleSchemaMismatch(currentVersion: number, expectedVersion: number): Observable<void> {
        console.warn(`[SqliteOpfsService] Schema mismatch detected: v${currentVersion} -> v${expectedVersion}. Resetting database...`);
        // TODO: In production, show a dialog to let user choose
        // For now, auto-reset to avoid broken state
        return this.resetToDefaults();
    }

    /**
     * Fallback initialization: apply schema.sql and seed from TypeScript definitions.
     */
    private initializeFromSchema(): Observable<void> {
        console.log('[SqliteOpfsService] Initializing from schema.sql + TypeScript seeds...');
        return from(fetch(assetUrl('assets/db/schema.sql'))).pipe(
            switchMap(res => res.text()),
            switchMap(schema => this.exec(schema)),
            switchMap(() => this.exec(`PRAGMA user_version = ${CURRENT_SCHEMA_VERSION}`)),
            switchMap(() => this.seedDefinitionCatalogs()),
            switchMap(() => this.seedDefaultAssets()),
            map(() => {
                console.log('[SqliteOpfsService] Schema + seeds initialization complete.');
            })
        );
    }

    /**
     * Reset the database to factory defaults by clearing and reloading from prebuilt.
     * This wipes all user data (custom machines, resources, protocol runs).
     * 
     * @returns Observable that completes when reset is done
     */
    resetToDefaults(): Observable<void> {
        console.log('[SqliteOpfsService] Resetting database to defaults...');

        // Close current connection, clear OPFS, and reinitialize
        return this.sendRequest<void>('clear', {}).pipe(
            switchMap(() => this.initializeFreshDatabase()),
            map(() => {
                console.log('[SqliteOpfsService] Database reset complete.');
            })
        );
    }

    /**
     * Seed definition catalogs from PLR definitions.
     */
    private seedDefinitionCatalogs(): Observable<void> {
        console.log('[SqliteOpfsService] Seeding definition catalogs (Batched)...');

        const operations: { sql: string; bind: any[] }[] = [];

        // 1. Resources
        const insertResDef = `
            INSERT OR IGNORE INTO resource_definitions
            (accession_id, name, fqn, resource_type, vendor, description, properties_json, is_consumable, num_items, plr_category, is_reusable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `;
        for (const def of PLR_RESOURCE_DEFINITIONS) {
            operations.push({
                sql: insertResDef,
                bind: [
                    def.accession_id,
                    def.name,
                    def.fqn,
                    def.plr_category,
                    def.vendor || null,
                    def.description || null,
                    JSON.stringify(def.properties_json),
                    def.is_consumable ? 1 : 0,
                    def.num_items || null,
                    def.plr_category,
                    def.is_reusable ? 1 : 0
                ]
            });
        }

        // 2. Machines
        const insertMachDef = `
            INSERT OR IGNORE INTO machine_definitions
            (accession_id, name, fqn, machine_category, manufacturer, description, has_deck, properties_json, capabilities_config, frontend_fqn, is_simulated_frontend, available_simulation_backends, plr_category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `;
        for (const def of PLR_MACHINE_DEFINITIONS) {
            let capConfig = def.capabilities_config;
            if (!capConfig && OFFLINE_CAPABILITY_OVERRIDES[def.fqn]) {
                capConfig = OFFLINE_CAPABILITY_OVERRIDES[def.fqn];
            }
            operations.push({
                sql: insertMachDef,
                bind: [
                    def.accession_id,
                    def.name,
                    def.fqn,
                    def.machine_type,
                    def.vendor || null,
                    def.description || null,
                    def.has_deck ? 1 : 0,
                    JSON.stringify(def.properties_json),
                    capConfig ? JSON.stringify(capConfig) : null,
                    def.frontend_fqn || null,
                    def.is_simulated_frontend ? 1 : 0,
                    def.available_simulation_backends ? JSON.stringify(def.available_simulation_backends) : null,
                    'Machine'
                ]
            });
        }

        // 3. Frontends
        const insertFrontendDef = `
            INSERT OR IGNORE INTO machine_frontend_definitions
            (accession_id, name, fqn, machine_category, description, has_deck, capabilities, capabilities_config, plr_category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        `;
        for (const def of PLR_FRONTEND_DEFINITIONS) {
            operations.push({
                sql: insertFrontendDef,
                bind: [
                    def.accession_id,
                    def.name,
                    def.fqn,
                    def.machine_category,
                    def.description || null,
                    def.has_deck ? 1 : 0,
                    def.capabilities ? JSON.stringify(def.capabilities) : null,
                    def.capabilities_config ? JSON.stringify(def.capabilities_config) : null,
                    'Machine'
                ]
            });
        }

        // 4. Backends
        const insertBackendDef = `
            INSERT OR IGNORE INTO machine_backend_definitions
            (accession_id, fqn, name, description, backend_type, connection_config, manufacturer, model, frontend_definition_accession_id, is_deprecated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        `;
        for (const def of PLR_BACKEND_DEFINITIONS) {
            operations.push({
                sql: insertBackendDef,
                bind: [
                    def.accession_id,
                    def.fqn,
                    def.name,
                    def.description || null,
                    def.backend_type,
                    def.connection_config ? JSON.stringify(def.connection_config) : null,
                    def.manufacturer || null,
                    def.model || null,
                    def.frontend_definition_accession_id
                ]
            });
        }

        return this.execBatch(operations).pipe(
            map(() => {
                console.log(`[SqliteOpfsService] Seeded ${operations.length} definitions via batch.`);
            })
        );
    }

    /**
     * Seed default assets if none exist.
     * 
     * NOTE: This seeding is for BROWSER MODE ONLY. The prebuilt praxis.db
     * should contain resources, but this acts as a fallback when the database
     * is reset or the prebuilt file is unavailable.
     * 
     * TODO: Add a configuration toggle to disable auto-seeding for production
     * environments where inventory should be managed explicitly.
     */
    private seedDefaultAssets(): Observable<void> {
        return this.exec("SELECT COUNT(*) as count FROM resources").pipe(
            switchMap(result => {
                const count = (result.resultRows[0] as any)?.count || 0;
                if (count > 0) return of(void 0);

                return this.exec("SELECT accession_id, name, fqn FROM resource_definitions").pipe(
                    switchMap(resDefs => {
                        const rows = resDefs.resultRows;
                        if (rows.length === 0) {
                            console.warn('[SqliteOpfsService] No resource definitions found for asset seeding.');
                            return of(void 0);
                        }

                        const now = new Date().toISOString();
                        const tasks: Observable<any>[] = [];
                        tasks.push(this.exec('BEGIN TRANSACTION'));

                        const insertResource = `
                            INSERT OR IGNORE INTO resources (accession_id, asset_type, name, fqn, created_at, updated_at, properties_json, resource_definition_accession_id, status)
                            VALUES (?, 'RESOURCE', ?, ?, ?, ?, ?, ?, ?)
                        `;

                        for (const row of rows) {
                            const assetId = crypto.randomUUID();
                            const cleanName = (row.name as string).replace(/\s+/g, '_').toLowerCase();
                            const instanceFqn = `resources.default.${cleanName}`;

                            tasks.push(this.exec(insertResource, [
                                assetId,
                                row.name,
                                instanceFqn,
                                now,
                                now,
                                JSON.stringify({ is_default: true }),
                                row.accession_id,
                                'available'
                            ]));
                        }

                        tasks.push(this.exec('COMMIT'));
                        return from(tasks).pipe(
                            concatMap(t => t),
                            last(),
                            map(() => void 0)
                        );
                    })
                );
            })
        );
    }

    /**
     * Execute a SQL statement with optional bindings and row mode.
     * 
     * @param sql The SQL query string
     * @param bind Values to bind to SQL parameters
     * @param rowMode 'object' (default) or 'array'
     * @returns Observable of the execution results
     */
    exec<T>(sql: string, bind?: any[], rowMode: RowMode = 'object'): Observable<SqliteExecResult> {
        const payload: SqliteExecRequest = {
            sql,
            bind,
            rowMode,
            returnValue: 'resultRows'
        };
        return this.sendRequest<SqliteExecResult>('exec', payload);
    }

    /**
     * Execute multiple SQL statements in a single transaction.
     * 
     * @param operations List of SQL strings and optional parameter bindings
     * @returns Observable that completes when the batch is finished
     */
    execBatch(operations: { sql: string; bind?: any[] }[]): Observable<void> {
        const payload: SqliteBatchExecRequest = { operations };
        return this.sendRequest<void>('execBatch', payload);
    }

    /**
     * Export the current database state as a binary buffer.
     * 
     * @returns Observable of the raw database bytes
     */
    exportDatabase(): Observable<Uint8Array> {
        return this.sendRequest<Uint8Array>('export', {});
    }

    /**
     * Import a database from a binary buffer, overwriting the current state.
     * 
     * @param data The raw database bytes to import
     * @returns Observable that completes when the import is finished
     */
    importDatabase(data: Uint8Array): Observable<void> {
        const payload: SqliteImportRequest = { data };
        return this.sendRequest<void>('import', payload);
    }

    /**
     * Get the status of the SQLite OPFS worker (VFS info, etc.)
     */
    getStatus(): Observable<any> {
        return this.sendRequest<any>('status', {});
    }

    /**
     * Close the database and terminate the worker thread.
     * 
     * @returns Observable that completes when the worker has been terminated
     */
    close(): Observable<void> {
        return new Observable<void>(subscriber => {
            if (!this.worker) {
                subscriber.next();
                subscriber.complete();
                return;
            }

            this.sendRequest<void>('close', {}).subscribe({
                next: () => {
                    this.terminateWorker();
                    subscriber.next();
                    subscriber.complete();
                },
                error: (err) => {
                    // Even if close fails (e.g. timeout), we should terminate the worker
                    this.terminateWorker();
                    subscriber.error(err);
                }
            });
        });
    }

    /**
     * Internal helper to send requests to the worker and correlate responses using UUIDs.
     * Implements the request/response pattern over a message-based channel.
     */
    private sendRequest<T>(type: SqliteWorkerRequest['type'], payload: any): Observable<T> {
        return new Observable<T>(subscriber => {
            if (!this.worker) {
                subscriber.error(new Error('SQLite Worker not initialized. Call init() first.'));
                return;
            }

            const id = crypto.randomUUID();

            const sub = this.responses$.pipe(
                filter(response => response.id === id),
                take(1)
            ).subscribe({
                next: (response) => {
                    if (response.type === 'error') {
                        // Include original SQL if available in payload for better debugging
                        const errorMsg = response.payload.message || 'Unknown SQLite error';
                        subscriber.error(new Error(`[SqliteOpfsService] ${errorMsg}`));
                    } else {
                        subscriber.next(response.payload as T);
                        subscriber.complete();
                    }
                },
                error: (err) => subscriber.error(err)
            });

            this.worker.postMessage({ id, type, payload } as SqliteWorkerRequest);

            // Unsubscribe logic to prevent memory leaks if the consumer unsubscribes early
            return () => sub.unsubscribe();
        });
    }

    /**
     * Terminate the worker and clean up references.
     */
    private terminateWorker() {
        if (this.worker) {
            this.worker.terminate();
            this.worker = null;
        }
    }
}
