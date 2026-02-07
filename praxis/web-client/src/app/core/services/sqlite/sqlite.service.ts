import { Injectable, inject, signal } from '@angular/core';
import { Observable, of, firstValueFrom } from 'rxjs';
import { filter, map, shareReplay, switchMap, take } from 'rxjs/operators';
import { toObservable } from '@angular/core/rxjs-interop';

// Type imports
import type { ResourceDefinitionCatalog, MachineDefinitionCatalog } from '@core/db/schema';
import type {
    FunctionProtocolDefinition,
    FunctionCallLog,
    ProtocolRun,
    Machine,
    Resource
} from '@core/db/schema';

import type { InferredRequirement, FailureMode, SimulationResult } from '@core/models/simulation.models';
import { SqliteStatus } from './sqlite.types';

import { SqliteOpfsService } from './sqlite-opfs.service';
import { AsyncRepositories, createAsyncRepositories } from '@core/db/async-repositories';
import {
    AsyncProtocolRunRepository,
    AsyncProtocolDefinitionRepository,
    AsyncFunctionCallLogRepository,
    AsyncMachineRepository,
    AsyncMachineDefinitionRepository,
    AsyncMachineFrontendDefinitionRepository,
    AsyncMachineBackendDefinitionRepository,
    AsyncResourceRepository,
    AsyncResourceDefinitionRepository,
    AsyncDeckRepository,
    AsyncDeckDefinitionRepository,
    AsyncDeckPositionRepository,
    AsyncWorkcellRepository,
    AsyncDataOutputRepository,
    AsyncParameterRepository,
    AsyncProtocolAssetRequirementRepository,
} from '@core/db/async-repositories';

@Injectable({ providedIn: 'root' })
export class SqliteService {
    private asyncRepositories: AsyncRepositories | null = null;
    private opfs = inject(SqliteOpfsService);

    // Cached URL parameters (captured at construction because redirects may clear them)
    private readonly cachedDbName: string | undefined;
    private readonly cachedResetDb: boolean = false;

    // Modern Angular Signals
    private readonly _status = signal<SqliteStatus>({
        initialized: false,
        source: 'none',
        tableCount: 0
    });

    /** Signal-based status */
    public readonly status = this._status.asReadonly();

    /** Signal that emits true when database is ready */
    public readonly isReady = signal<boolean>(false);

    /** Observable for RxJS interop - use `isReady` signal where possible */
    public readonly isReady$ = toObservable(this.isReady);

    constructor() {
        if (typeof window !== 'undefined') {
            (window as any).sqliteService = this;

            // Compatibility layer for E2E tests - allows running raw SQL queries
            // NOTE: This implementation is ASYNC, so tests must await the results
            (window as any).sqliteService.db = {
                exec: async (sql: string, bind?: any[]) => {
                    const res = await firstValueFrom(this.opfs.exec(sql, bind));
                    // Return in sql.js-compatible format for existing E2E tests
                    return [{
                        columns: res.columnNames,
                        values: res.resultRows.map((row: any) => res.columnNames.map((col: any) => row[col]))
                    }];
                },
                sync: async () => {
                    // No-op - OPFS auto-syncs
                }
            };
        }

        // Capture URL parameters immediately (before any redirects occur)
        this.cachedDbName = this.getDbNameFromUrl();
        this.cachedResetDb = this.getResetDbFromUrl();

        if (this.cachedDbName) {
            console.log(`[SqliteService] Using database from URL: ${this.cachedDbName}`);
        }
        if (this.cachedResetDb) {
            console.log('[SqliteService] Force reset requested via URL (resetdb=1)');
        }

        // Initialize OPFS and sync status.
        // The isReady$ signal is now emitted *after* opfs.init() completes,
        // which includes schema creation and seeding.
        console.log('[SqliteService] Starting OPFS init subscription...');

        const init$ = this.opfs.init(this.cachedDbName);
        const setup$ = this.cachedResetDb
            ? init$.pipe(switchMap(() => this.opfs.resetToDefaults()))
            : init$;

        setup$.subscribe({
            next: () => {
                this._status.set({
                    initialized: true,
                    source: 'opfs',
                    tableCount: 0 // Note: tableCount is not accurately tracked here yet.
                });
                console.log(`[SqliteService] OPFS ${this.cachedResetDb ? 'reset & ' : ''}init complete, signaling DB is ready.`);
                this.isReady.set(true);
            },
            error: (err) => {
                console.error('[SqliteService] OPFS init error:', err);
                this._status.set({
                    initialized: false,
                    source: 'none',
                    tableCount: 0,
                    error: err.message
                });
                // Ensure isReady remains false on error
                this.isReady.set(false);
            },
            complete: () => {
                console.log('[SqliteService] OPFS init subscription completed');
            }
        });
    }

    // ============================================
    // Private Helpers
    // ============================================

    /**
     * Extract database name from URL query parameters.
     * Used for E2E test isolation - each Playwright worker uses a unique DB.
     * Format: ?dbName=praxis-worker-0
     */
    private getDbNameFromUrl(): string | undefined {
        if (typeof window === 'undefined') return undefined;
        const params = new URLSearchParams(window.location.search);
        const dbName = params.get('dbName');
        return dbName ? `/${dbName}.db` : undefined;
    }

    /**
     * Check if database reset is requested via URL.
     */
    private getResetDbFromUrl(): boolean {
        if (typeof window === 'undefined') return false;
        const params = new URLSearchParams(window.location.search);
        return params.get('resetdb') === '1' || params.get('resetdb') === 'true';
    }

    /**
     * Get the current database name.
     */
    public getDatabaseName(): string {
        const name = this.cachedDbName;
        return name ? name.replace(/^\//, '').replace(/\.db$/, '') : 'praxis';
    }

    // ============================================
    // Core Repository Access
    // ============================================

    /**
     * Get async repositories (OPFS Worker backed)
     */
    public getAsyncRepositories(): Observable<AsyncRepositories> {
        return this.isReady$.pipe(
            filter(ready => ready),
            take(1),
            map(() => {
                if (!this.asyncRepositories) {
                    this.asyncRepositories = createAsyncRepositories(this.opfs);
                }
                return this.asyncRepositories;
            }),
            shareReplay(1)
        );
    }

    /**
     * @deprecated Use getAsyncRepositories()
     */
    public getRepositories(): Observable<AsyncRepositories> {
        return this.getAsyncRepositories();
    }

    // ============================================
    // Repository Accessors
    // ============================================

    public get protocolRuns(): Observable<AsyncProtocolRunRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.protocolRuns));
    }

    public get protocolDefinitions(): Observable<AsyncProtocolDefinitionRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.protocolDefinitions));
    }

    public get machines(): Observable<AsyncMachineRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.machines));
    }

    public get machineDefinitions(): Observable<AsyncMachineDefinitionRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.machineDefinitions));
    }

    public get machineFrontendDefinitions(): Observable<AsyncMachineFrontendDefinitionRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.machineFrontendDefinitions));
    }

    public get machineBackendDefinitions(): Observable<AsyncMachineBackendDefinitionRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.machineBackendDefinitions));
    }

    public get resources(): Observable<AsyncResourceRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.resources));
    }

    public get resourceDefinitions(): Observable<AsyncResourceDefinitionRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.resourceDefinitions));
    }

    public get decks(): Observable<AsyncDeckRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.decks));
    }

    public get deckDefinitions(): Observable<AsyncDeckDefinitionRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.deckDefinitions));
    }

    public get deckPositions(): Observable<AsyncDeckPositionRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.deckPositions));
    }

    public get workcells(): Observable<AsyncWorkcellRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.workcells));
    }

    public get dataOutputs(): Observable<AsyncDataOutputRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.dataOutputs));
    }

    public get functionCallLogs(): Observable<AsyncFunctionCallLogRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.functionCallLogs));
    }

    public get parameters(): Observable<AsyncParameterRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.parameters));
    }

    public get assetRequirements(): Observable<AsyncProtocolAssetRequirementRepository> {
        return this.getAsyncRepositories().pipe(map(r => r.assetRequirements));
    }

    // ============================================
    // Convenience Query Methods
    // ============================================

    public getProtocols(): Observable<FunctionProtocolDefinition[]> {
        return this.getAsyncRepositories().pipe(
            switchMap(repos => repos.protocolDefinitions.findAll())
        );
    }

    public getProtocolById(accessionId: string): Observable<FunctionProtocolDefinition | null> {
        return this.getAsyncRepositories().pipe(
            switchMap(repos => repos.protocolDefinitions.findById(accessionId))
        );
    }

    public getProtocolRuns(): Observable<ProtocolRun[]> {
        return this.getAsyncRepositories().pipe(
            switchMap(repos => repos.protocolRuns.findAll())
        );
    }

    public getTransferLogs(runId: string): Observable<FunctionCallLog[]> {
        return this.getAsyncRepositories().pipe(
            switchMap(repos => repos.functionCallLogs.findByProtocolRun(runId))
        );
    }

    public getProtocolRun(id: string): Observable<ProtocolRun | undefined> {
        return this.getAsyncRepositories().pipe(
            switchMap(repos => repos.protocolRuns.findById(id)),
            map(run => run || undefined)
        );
    }

    public getResources(): Observable<Resource[]> {
        return this.getAsyncRepositories().pipe(
            switchMap(repos => repos.resources.findAll())
        );
    }

    public getMachines(): Observable<Machine[]> {
        return this.getAsyncRepositories().pipe(
            switchMap(repos => repos.machines.findAll())
        );
    }

    public getResourceDefinitions(): Observable<ResourceDefinitionCatalog[]> {
        return this.getAsyncRepositories().pipe(
            switchMap(repos => repos.resourceDefinitions.findAll())
        );
    }

    public getMachineDefinitions(): Observable<MachineDefinitionCatalog[]> {
        return this.getAsyncRepositories().pipe(
            switchMap(repos => repos.machineDefinitions.findAll())
        );
    }

    public getProtocolSimulationData(protocolId: string): Observable<{
        inferred_requirements: InferredRequirement[];
        failure_modes: FailureMode[];
        simulation_result: SimulationResult | null;
    } | null> {
        return this.getAsyncRepositories().pipe(
            switchMap(repos => repos.protocolDefinitions.findById(protocolId)),
            map(protocol => {
                if (!protocol) return null;
                const props = (protocol as any).properties_json || {};
                return {
                    inferred_requirements: props.inferred_requirements || [],
                    failure_modes: props.failure_modes || [],
                    simulation_result: props.simulation_result || null,
                };
            })
        );
    }

    // ============================================
    // Database Operations (Delegate to OPFS)
    // ============================================

    /**
     * Create a new protocol run (convenience wrapper)
     */
    public createProtocolRun(entity: any): Observable<ProtocolRun> {
        return this.protocolRuns.pipe(
            switchMap(repo => repo.create(entity))
        );
    }

    /**
     * Create a new machine (convenience wrapper)
     */
    public createMachine(entity: any): Observable<Machine> {
        return this.machines.pipe(
            switchMap(repo => repo.create(entity))
        );
    }

    /**
     * Update protocol run status (convenience wrapper)
     */
    public updateProtocolRunStatus(runId: string, status: string): Observable<void> {
        return this.protocolRuns.pipe(
            switchMap(repo => repo.update(runId, { status } as any)),
            map(() => { })
        );
    }

    /**
     * Save state resolution (convenience wrapper)
     */
    public saveStateResolution(runId: string, resolution: any): Observable<void> {
        // Implementation pending in repositories, mock for now to fix build
        console.warn('saveStateResolution: NOT YET IMPLEMENTED', runId, resolution);
        return of(undefined);
    }

    /**
     * Get state history for a run (convenience wrapper)
     */
    public getRunStateHistory(runId: string): Observable<any> {
        return this.protocolRuns.pipe(
            switchMap(repo => repo.findById(runId)),
            map(run => (run?.properties_json as any)?.state_history || null)
        );
    }

    /**
     * Export database as Uint8Array
     */
    public exportDatabase(): Observable<Uint8Array> {
        return this.opfs.exportDatabase();
    }

    /**
     * Import database from Uint8Array
     */
    public importDatabase(data: Uint8Array): Observable<void> {
        return this.opfs.importDatabase(data);
    }

    /**
     * Close database connection
     */
    public close(): Observable<void> {
        return this.opfs.close();
    }

    /**
     * Reset database to factory defaults.
     * Clears all user data and reloads from the prebuilt praxis.db.
     */
    public resetToDefaults(): Observable<void> {
        console.log('[SqliteService] Resetting database to defaults...');
        this.isReady.set(false);
        return this.opfs.resetToDefaults().pipe(
            map(() => {
                console.log('[SqliteService] Reset complete, signaling DB is ready.');
                this.isReady.set(true);
            })
        );
    }
}
