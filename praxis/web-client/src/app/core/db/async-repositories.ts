import { Observable, map, switchMap, forkJoin, of } from 'rxjs';
import { SqliteOpfsService } from '@core/services/sqlite';
import { SqliteAsyncRepository, type QueryOptions } from './sqlite-async-repository';
import { BaseEntity } from './base-sqlite-repository';
import type {
    ProtocolRun,
    FunctionProtocolDefinition,
    FunctionCallLog,
    Machine,
    MachineDefinitionCatalog,
    MachineFrontendDefinition,
    MachineBackendDefinition,
    Resource,
    ResourceDefinitionCatalog,
    Deck,
    DeckDefinitionCatalog,
    DeckPositionDefinition,
    Workcell,
    FunctionDataOutput,
    ParameterDefinition,
    ProtocolAssetRequirement,
} from './schema';
import type { ProtocolRunStatus, MachineStatus, ResourceStatus } from './enums';
import type { ProtocolDefinition, SimulationResult } from '@features/protocols/models/protocol.models';

// Re-type interfaces with index signature for repository compatibility
type WithIndex<T> = T & BaseEntity;

/**
 * Repository for Protocol Runs with specialized queries
 */
export class AsyncProtocolRunRepository extends SqliteAsyncRepository<WithIndex<ProtocolRun>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'protocol_runs', 'accession_id');
    }

    /**
     * Find protocol runs by status
     */
    findByStatus(statuses: ProtocolRunStatus[]): Observable<ProtocolRun[]> {
        const placeholders = statuses.map(() => '?').join(', ');
        const sql = `SELECT * FROM ${this.tableName} WHERE status IN (${placeholders}) ORDER BY created_at DESC`;
        return this.executeQuery(sql, statuses);
    }

    /**
     * Find recent protocol runs
     */
    findRecent(limit: number = 10): Observable<ProtocolRun[]> {
        return this.findAll({
            orderBy: { column: 'created_at', direction: 'DESC' },
            limit
        });
    }

    /**
     * Find protocol runs for a specific protocol definition
     */
    findByProtocolDefinition(protocolDefinitionId: string): Observable<ProtocolRun[]> {
        return this.findBy(
            { top_level_protocol_definition_accession_id: protocolDefinitionId } as Partial<ProtocolRun>,
            { orderBy: { column: 'created_at', direction: 'DESC' } }
        );
    }

    /**
     * Find running protocol runs
     */
    findRunning(): Observable<ProtocolRun[]> {
        return this.findByStatus(['RUNNING', 'PREPARING', 'RESUMING'] as ProtocolRunStatus[]);
    }

    /**
     * Find completed protocol runs in a date range
     */
    findCompletedInRange(startDate: string, endDate: string): Observable<ProtocolRun[]> {
        const sql = `
            SELECT * FROM ${this.tableName}
            WHERE status = 'COMPLETED'
            AND end_time >= ?
            AND end_time <= ?
            ORDER BY end_time DESC
        `;
        return this.executeQuery(sql, [startDate, endDate]);
    }
}


/**
 * Maps raw SQLite protocol row to ProtocolDefinition domain object
 * Handles JSON deserialization and field name normalization
 */
function mapProtocolEntity(row: any): ProtocolDefinition {
    // Parse simulation_result_json if it's a string (SQLite TEXT column)
    let simulationResult: SimulationResult | undefined = undefined;

    if (row.simulation_result_json) {
        try {
            // Check if already parsed
            simulationResult = typeof row.simulation_result_json === 'string'
                ? JSON.parse(row.simulation_result_json)
                : row.simulation_result_json;
        } catch (e) {
            console.error('Failed to parse simulation_result_json', e);
        }
    }

    // Inferred requirements and failure modes
    let inferredRequirements: any[] = [];
    if (row.inferred_requirements_json) {
        try {
            inferredRequirements = typeof row.inferred_requirements_json === 'string'
                ? JSON.parse(row.inferred_requirements_json)
                : row.inferred_requirements_json;
        } catch (e) {
            console.error('Failed to parse inferred_requirements_json', e);
        }
    }

    let failureModes: any[] = [];
    if (row.failure_modes_json) {
        try {
            failureModes = typeof row.failure_modes_json === 'string'
                ? JSON.parse(row.failure_modes_json)
                : row.failure_modes_json;
        } catch (e) {
            console.error('Failed to parse failure_modes_json', e);
        }
    }

    return {
        ...row,
        // Map JSON columns to domain properties
        simulation_result: simulationResult,
        inferred_requirements: inferredRequirements,
        failure_modes: failureModes,
        // Remove raw DB fields to prevent confusion
        simulation_result_json: undefined,
        inferred_requirements_json: undefined,
        failure_modes_json: undefined
    } as ProtocolDefinition;
}

/**
 * Repository for Parameter Definitions
 */
export class AsyncParameterRepository extends SqliteAsyncRepository<WithIndex<ParameterDefinition>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'parameter_definitions', 'accession_id');
    }

    /**
     * Find parameters for a specific protocol definition
     */
    findByProtocolDefinition(protocolDefinitionId: string): Observable<ParameterDefinition[]> {
        return this.findBy(
            { protocol_definition_accession_id: protocolDefinitionId } as Partial<ParameterDefinition>,
            { orderBy: { column: 'name', direction: 'ASC' } }
        );
    }
}

/**
 * Repository for Protocol Asset Requirements
 */
export class AsyncProtocolAssetRequirementRepository extends SqliteAsyncRepository<WithIndex<ProtocolAssetRequirement>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'protocol_asset_requirements', 'accession_id');
    }

    /**
     * Find asset requirements for a specific protocol definition
     */
    findByProtocolDefinition(protocolDefinitionId: string): Observable<ProtocolAssetRequirement[]> {
        return this.findBy(
            { protocol_definition_accession_id: protocolDefinitionId } as Partial<ProtocolAssetRequirement>,
            { orderBy: { column: 'name', direction: 'ASC' } }
        );
    }
}

/**
 * Repository for Protocol Definitions
 */
export class AsyncProtocolDefinitionRepository extends SqliteAsyncRepository<WithIndex<FunctionProtocolDefinition>> {
    private parameterRepo: AsyncParameterRepository;
    private assetRequirementRepo: AsyncProtocolAssetRequirementRepository;

    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'function_protocol_definitions', 'accession_id');
        this.parameterRepo = new AsyncParameterRepository(opfs);
        this.assetRequirementRepo = new AsyncProtocolAssetRequirementRepository(opfs);
    }

    /**
     * Find top-level (executable) protocols with associations
     */
    findTopLevel(): Observable<ProtocolDefinition[]> {
        return this.findBy({ is_top_level: true } as Partial<FunctionProtocolDefinition>).pipe(
            switchMap(rows => {
                if (rows.length === 0) return of([]);
                // For list view, we usually just want the basic data, 
                // but the wizards expect parameters. 
                // To keep it simple and correct, we'll fetch for all in this list.
                return forkJoin(rows.map(row => this.fetchAssociations(row)));
            })
        );
    }

    /**
     * Find protocols by category
     */
    findByCategory(category: string): Observable<ProtocolDefinition[]> {
        return this.findBy({ category } as Partial<FunctionProtocolDefinition>).pipe(
            switchMap(rows => {
                if (rows.length === 0) return of([]);
                return forkJoin(rows.map(row => this.fetchAssociations(row)));
            })
        );
    }

    /**
     * Find active (non-deprecated) protocols
     */
    findActive(): Observable<ProtocolDefinition[]> {
        return this.findBy({ deprecated: false } as Partial<FunctionProtocolDefinition>).pipe(
            switchMap(rows => {
                if (rows.length === 0) return of([]);
                return forkJoin(rows.map(row => this.fetchAssociations(row)));
            })
        );
    }

    /**
     * Search protocols by name or description
     */
    search(query: string): Observable<ProtocolDefinition[]> {
        const sql = `
            SELECT * FROM ${this.tableName}
            WHERE name LIKE ? OR description LIKE ? OR fqn LIKE ?
            ORDER BY name ASC
        `;
        const pattern = `%${query}%`;
        return this.executeQuery(sql, [pattern, pattern, pattern]).pipe(
            switchMap(rows => {
                if (rows.length === 0) return of([]);
                return forkJoin(rows.map(row => this.fetchAssociations(row)));
            })
        );
    }

    override findAll(options?: QueryOptions<WithIndex<FunctionProtocolDefinition>>): Observable<WithIndex<FunctionProtocolDefinition>[]> {
        return (super.findAll(options) as any).pipe(
            switchMap((rows: any[]) => {
                if (rows.length === 0) return of([]);
                return forkJoin(rows.map(row => this.fetchAssociations(row)));
            })
        );
    }

    override findById(id: string): Observable<WithIndex<FunctionProtocolDefinition> | null> {
        return (super.findById(id) as any).pipe(
            switchMap((row: any) => {
                if (!row) return of(null);
                return this.fetchAssociations(row);
            })
        );
    }

    /**
     * Fetches parameters and assets for a protocol row and maps it to a domain object
     */
    private fetchAssociations(row: any): Observable<ProtocolDefinition> {
        const id = row.accession_id;
        console.log(`[AsyncProtocolDefinitionRepository] Fetching associations for protocol: ${row.name} (${id})`);
        return forkJoin({
            parameters: this.parameterRepo.findByProtocolDefinition(id),
            assets: this.assetRequirementRepo.findByProtocolDefinition(id)
        }).pipe(
            map(({ parameters, assets }) => {
                console.log(`[AsyncProtocolDefinitionRepository] Protocol ${row.name}: Found ${parameters.length} parameters, ${assets.length} assets`);
                const protocol = mapProtocolEntity(row);
                return {
                    ...protocol,
                    parameters: parameters.map(p => this.mapParameter(p)),
                    assets: assets.map(a => this.mapAssetRequirement(a))
                };
            })
        );
    }

    private mapParameter(p: any): any {
        console.log(`[AsyncProtocolDefinitionRepository] Mapping parameter: ${p.name}`);
        let constraints = {};
        if (p.constraints_json) {
            constraints = typeof p.constraints_json === 'string' ? JSON.parse(p.constraints_json) : p.constraints_json;
        }

        let itemizedSpec = undefined;
        if (p.itemized_spec_json) {
            itemizedSpec = typeof p.itemized_spec_json === 'string' ? JSON.parse(p.itemized_spec_json) : p.itemized_spec_json;
        }

        let uiHint = undefined;
        if (p.ui_hint_json) {
            uiHint = typeof p.ui_hint_json === 'string' ? JSON.parse(p.ui_hint_json) : p.ui_hint_json;
        }

        return {
            ...p,
            constraints,
            itemized_spec: itemizedSpec,
            ui_hint: uiHint
        };
    }

    private mapAssetRequirement(a: any): any {
        let constraints = {};
        if (a.constraints_json) {
            constraints = typeof a.constraints_json === 'string' ? JSON.parse(a.constraints_json) : a.constraints_json;
        }

        let locationConstraints = {};
        if (a.location_constraints_json) {
            locationConstraints = typeof a.location_constraints_json === 'string' ? JSON.parse(a.location_constraints_json) : a.location_constraints_json;
        }

        return {
            ...a,
            constraints,
            location_constraints: locationConstraints
        };
    }
}

/**
 * Repository for Function Call Logs
 */
export class AsyncFunctionCallLogRepository extends SqliteAsyncRepository<WithIndex<FunctionCallLog>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'function_call_logs', 'accession_id');
    }

    /**
     * Find logs for a protocol run, ordered by sequence
     */
    findByProtocolRun(protocolRunId: string): Observable<FunctionCallLog[]> {
        return this.findBy(
            { protocol_run_accession_id: protocolRunId } as Partial<FunctionCallLog>,
            { orderBy: { column: 'sequence_in_run', direction: 'ASC' } }
        );
    }

    /**
     * Find child calls of a parent function call
     */
    findChildren(parentCallId: string): Observable<FunctionCallLog[]> {
        return this.findBy(
            { parent_function_call_log_accession_id: parentCallId } as Partial<FunctionCallLog>,
            { orderBy: { column: 'sequence_in_run', direction: 'ASC' } }
        );
    }
}

/**
 * Repository for Machines
 */
export class AsyncMachineRepository extends SqliteAsyncRepository<WithIndex<Machine>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'machines', 'accession_id');
    }

    /**
     * Find machines by status
     */
    private get joinedSelect() {
        return `SELECT m.* FROM ${this.tableName} m`;
    }

    /**
     * Find all machines with asset details
     */
    override findAll(options?: QueryOptions<WithIndex<Machine>>): Observable<WithIndex<Machine>[]> {
        let sql = this.joinedSelect;
        if (options?.orderBy) sql += this.buildOrderByClause(options.orderBy);
        if (options?.limit !== undefined) sql += ` LIMIT ${options.limit}`;
        if (options?.offset !== undefined) sql += ` OFFSET ${options.offset}`;
        return this.executeQuery(sql);
    }

    /**
     * Find machine by ID with asset details
     */
    override findById(id: string): Observable<WithIndex<Machine> | null> {
        const sql = `${this.joinedSelect} WHERE m.accession_id = ?`;
        return this.executeQuery(sql, [id]).pipe(
            map(results => results.length > 0 ? results[0] : null)
        );
    }

    /**
     * Find machines by status
     */
    findByStatus(statuses: MachineStatus[]): Observable<Machine[]> {
        const placeholders = statuses.map(() => '?').join(', ');
        const sql = `${this.joinedSelect} WHERE m.status IN (${placeholders})`;
        return this.executeQuery(sql, statuses);
    }

    /**
     * Find available machines
     */
    findAvailable(): Observable<Machine[]> {
        return this.findByStatus(['AVAILABLE'] as MachineStatus[]);
    }

    /**
     * Find machines in a workcell
     */
    findByWorkcell(workcellId: string): Observable<Machine[]> {
        return this.findBy({ workcell_accession_id: workcellId } as Partial<Machine>);
    }

    /**
     * Find machines by category
     */
    findByCategory(category: string): Observable<Machine[]> {
        return this.findBy({ machine_category: category } as Partial<Machine>);
    }

    /**
     * Create a new machine (overrides generic create for flattened schema).
     * Inserts directly into the 'machines' table.
     */
    override create(entity: Omit<WithIndex<Machine>, 'created_at' | 'updated_at'>): Observable<WithIndex<Machine>> {
        // Flattened schema: Insert directly into machines table
        const machineFields = [
            'accession_id', 'asset_type', 'name', 'fqn', 'location',
            'plr_state', 'plr_definition', 'properties_json',
            'machine_category', 'description', 'manufacturer', 'model',
            'serial_number', 'installation_date', 'status', 'status_details',
            'connection_info', 'is_simulation_override', 'user_configured_capabilities',
            'workcell_accession_id', 'resource_counterpart_accession_id',
            'deck_child_accession_id', 'deck_child_definition_accession_id',
            'last_seen_online', 'current_protocol_run_accession_id',
            'maintenance_enabled', 'maintenance_schedule_json'
        ];

        const machineData: Record<string, any> = {};
        machineFields.forEach(f => {
            if (f in entity) machineData[f] = entity[f];
        });

        const machineCols = Object.keys(machineData);
        if (machineCols.length > 0) {
            const machineVals = Object.values(machineData).map(v => this.serializeValue(v));
            const machinePlaceholders = machineCols.map(() => '?').join(', ');
            const machineSql = `INSERT INTO machines (${machineCols.join(', ')}) VALUES (${machinePlaceholders})`;

            return this.opfs.exec(machineSql, machineVals).pipe(
                switchMap(() => this.findById(entity['accession_id'] as string)),
                map(res => {
                    if (!res) throw new Error("Failed to create machine");
                    return res as WithIndex<Machine>;
                })
            );
        }

        throw new Error("No machine columns to insert");
    }
}

/**
 * Repository for Machine Definitions (catalog)
 */
export class AsyncMachineDefinitionRepository extends SqliteAsyncRepository<WithIndex<MachineDefinitionCatalog>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'machine_definitions', 'accession_id');
    }

    /**
     * Find by fully qualified name
     */
    findByFqn(fqn: string): Observable<MachineDefinitionCatalog | null> {
        return this.findOneBy({ fqn } as Partial<MachineDefinitionCatalog>);
    }

    /**
     * Find by category
     */
    findByCategory(category: string): Observable<MachineDefinitionCatalog[]> {
        return this.findBy({ machine_category: category } as Partial<MachineDefinitionCatalog>);
    }

    /**
     * Find machines with decks
     */
    findWithDecks(): Observable<MachineDefinitionCatalog[]> {
        return this.findBy({ has_deck: true } as Partial<MachineDefinitionCatalog>);
    }
}

/**
 * Repository for Machine Frontend Definitions (catalog)
 */
export class AsyncMachineFrontendDefinitionRepository extends SqliteAsyncRepository<WithIndex<MachineFrontendDefinition>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'machine_frontend_definitions', 'accession_id');
    }

    /**
     * Find by fully qualified name
     */
    findByFqn(fqn: string): Observable<MachineFrontendDefinition | null> {
        return this.findOneBy({ fqn } as Partial<MachineFrontendDefinition>);
    }

    /**
     * Find by category
     */
    findByCategory(category: string): Observable<MachineFrontendDefinition[]> {
        return this.findBy({ machine_category: category } as Partial<MachineFrontendDefinition>);
    }
}

/**
 * Repository for Machine Backend Definitions (catalog)
 */
export class AsyncMachineBackendDefinitionRepository extends SqliteAsyncRepository<WithIndex<MachineBackendDefinition>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'machine_backend_definitions', 'accession_id');
    }

    /**
     * Find by fully qualified name
     */
    findByFqn(fqn: string): Observable<MachineBackendDefinition | null> {
        return this.findOneBy({ fqn } as Partial<MachineBackendDefinition>);
    }

    /**
     * Find by frontend definition
     */
    findByFrontend(frontendId: string): Observable<MachineBackendDefinition[]> {
        return this.findBy({ frontend_definition_accession_id: frontendId } as Partial<MachineBackendDefinition>);
    }
}

/**
 * Repository for Resources
 */
export class AsyncResourceRepository extends SqliteAsyncRepository<WithIndex<Resource>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'resources', 'accession_id');
    }

    /**
     * Find resources by status
     */
    private get joinedSelect() {
        return `SELECT r.* FROM ${this.tableName} r`;
    }

    /**
     * Find all resources with asset details
     */
    override findAll(options?: QueryOptions<WithIndex<Resource>>): Observable<WithIndex<Resource>[]> {
        let sql = this.joinedSelect;
        if (options?.orderBy) sql += this.buildOrderByClause(options.orderBy);
        if (options?.limit !== undefined) sql += ` LIMIT ${options.limit}`;
        if (options?.offset !== undefined) sql += ` OFFSET ${options.offset}`;
        return this.executeQuery(sql);
    }

    /**
     * Find resource by ID with asset details
     */
    override findById(id: string): Observable<WithIndex<Resource> | null> {
        const sql = `${this.joinedSelect} WHERE r.accession_id = ?`;
        return this.executeQuery(sql, [id]).pipe(
            map(results => results.length > 0 ? results[0] : null)
        );
    }

    /**
     * Find resources by status
     */
    findByStatus(statuses: ResourceStatus[]): Observable<Resource[]> {
        const placeholders = statuses.map(() => '?').join(', ');
        const sql = `${this.joinedSelect} WHERE r.status IN (${placeholders})`;
        return this.executeQuery(sql, statuses);
    }

    /**
     * Find resources on a deck
     */
    findByDeck(deckId: string): Observable<Resource[]> {
        return this.findBy({ deck_accession_id: deckId } as Partial<Resource>);
    }

    /**
     * Find children of a parent resource
     */
    findChildren(parentId: string): Observable<Resource[]> {
        return this.findBy({ parent_accession_id: parentId } as Partial<Resource>);
    }

    /**
     * Create a new resource
     */
    override create(entity: Omit<WithIndex<Resource>, 'created_at' | 'updated_at'>): Observable<WithIndex<Resource>> {
        // Flattened schema: Insert directly into resources table
        const resourceFields = [
            'accession_id', 'asset_type', 'name', 'fqn', 'location',
            'plr_state', 'plr_definition', 'properties_json',
            'resource_definition_accession_id', 'parent_accession_id',
            'status', 'status_details', 'current_protocol_run_accession_id',
            'current_deck_position_name', 'machine_location_accession_id',
            'deck_accession_id', 'workcell_accession_id'
        ];

        const resourceData: Record<string, any> = {};
        resourceFields.forEach(f => {
            if (f in entity) resourceData[f] = entity[f];
        });

        const resourceCols = Object.keys(resourceData);
        if (resourceCols.length > 0) {
            const resourceVals = Object.values(resourceData).map(v => this.serializeValue(v));
            const resourcePlaceholders = resourceCols.map(() => '?').join(', ');
            const resourceSql = `INSERT INTO resources (${resourceCols.join(', ')}) VALUES (${resourcePlaceholders})`;

            return this.opfs.exec(resourceSql, resourceVals).pipe(
                switchMap(() => this.findById(entity['accession_id'] as string)),
                map(res => {
                    if (!res) throw new Error("Failed to create resource");
                    return res as WithIndex<Resource>;
                })
            );
        }

        throw new Error("No resource columns to insert");
    }
}

/**
 * Repository for Resource Definitions (catalog)
 */
export class AsyncResourceDefinitionRepository extends SqliteAsyncRepository<WithIndex<ResourceDefinitionCatalog>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'resource_definitions', 'accession_id');
    }

    /**
     * Find by fully qualified name
     */
    findByFqn(fqn: string): Observable<ResourceDefinitionCatalog | null> {
        return this.findOneBy({ fqn } as Partial<ResourceDefinitionCatalog>);
    }

    /**
     * Find consumables
     */
    findConsumables(): Observable<ResourceDefinitionCatalog[]> {
        return this.findBy({ is_consumable: true } as Partial<ResourceDefinitionCatalog>);
    }

    /**
     * Find by PLR category
     */
    findByPlrCategory(category: string): Observable<ResourceDefinitionCatalog[]> {
        return this.rawQuery(`SELECT * FROM ${this.tableName} WHERE LOWER(plr_category) = LOWER(?)`, [category]);
    }

    /**
     * Find by vendor
     */
    findByVendor(vendor: string): Observable<ResourceDefinitionCatalog[]> {
        return this.findBy({ vendor } as Partial<ResourceDefinitionCatalog>);
    }

    /**
     * Search by name or FQN
     */
    search(query: string): Observable<ResourceDefinitionCatalog[]> {
        const sql = `
            SELECT * FROM ${this.tableName}
            WHERE name LIKE ? OR fqn LIKE ?
            ORDER BY name ASC
        `;
        const pattern = `%${query}%`;
        return this.executeQuery(sql, [pattern, pattern]);
    }

    /**
     * Find plates by well count
     */
    findPlatesByWellCount(numWells: number): Observable<ResourceDefinitionCatalog[]> {
        return this.findBy({ num_items: numWells, plr_category: 'Plate' } as Partial<ResourceDefinitionCatalog>);
    }
}

/**
 * Repository for Decks
 */
export class AsyncDeckRepository extends SqliteAsyncRepository<WithIndex<Deck>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'decks', 'accession_id');
    }

    /**
     * Find decks for a machine
     */
    findByMachine(machineId: string): Observable<Deck[]> {
        return this.findBy({ parent_machine_accession_id: machineId } as Partial<Deck>);
    }
}

/**
 * Repository for Deck Definitions (catalog)
 */
export class AsyncDeckDefinitionRepository extends SqliteAsyncRepository<WithIndex<DeckDefinitionCatalog>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'deck_definition_catalog', 'accession_id');
    }

    /**
     * Find by fully qualified name
     */
    findByFqn(fqn: string): Observable<DeckDefinitionCatalog | null> {
        return this.findOneBy({ fqn } as Partial<DeckDefinitionCatalog>);
    }
}

/**
 * Repository for Deck Position Definitions
 */
export class AsyncDeckPositionRepository extends SqliteAsyncRepository<WithIndex<DeckPositionDefinition>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'deck_position_definitions', 'accession_id');
    }

    /**
     * Find positions for a deck type
     */
    findByDeckType(deckTypeId: string): Observable<DeckPositionDefinition[]> {
        return this.findBy({ deck_type_id: deckTypeId } as Partial<DeckPositionDefinition>);
    }
}

/**
 * Repository for Workcells
 */
export class AsyncWorkcellRepository extends SqliteAsyncRepository<WithIndex<Workcell>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'workcells', 'accession_id');
    }

    /**
     * Find active workcells
     */
    findActive(): Observable<Workcell[]> {
        return this.findBy({ status: 'active' } as Partial<Workcell>);
    }
}

/**
 * Repository for Function Data Outputs
 */
export class AsyncDataOutputRepository extends SqliteAsyncRepository<WithIndex<FunctionDataOutput>> {
    constructor(opfs: SqliteOpfsService) {
        super(opfs, 'function_data_outputs', 'accession_id');
    }

    /**
     * Find outputs for a protocol run
     */
    findByProtocolRun(protocolRunId: string): Observable<FunctionDataOutput[]> {
        return this.findBy(
            { protocol_run_accession_id: protocolRunId } as Partial<FunctionDataOutput>,
            { orderBy: { column: 'measurement_timestamp', direction: 'ASC' } }
        );
    }

    /**
     * Find outputs for a function call
     */
    findByFunctionCall(functionCallId: string): Observable<FunctionDataOutput[]> {
        return this.findBy({ function_call_log_accession_id: functionCallId } as Partial<FunctionDataOutput>);
    }
}

/**
 * Repository factory - creates all async repositories for a service
 */
export interface AsyncRepositories {
    protocolRuns: AsyncProtocolRunRepository;
    protocolDefinitions: AsyncProtocolDefinitionRepository;
    functionCallLogs: AsyncFunctionCallLogRepository;
    machines: AsyncMachineRepository;
    machineDefinitions: AsyncMachineDefinitionRepository;
    machineFrontendDefinitions: AsyncMachineFrontendDefinitionRepository;
    machineBackendDefinitions: AsyncMachineBackendDefinitionRepository;
    resources: AsyncResourceRepository;
    resourceDefinitions: AsyncResourceDefinitionRepository;
    decks: AsyncDeckRepository;
    deckDefinitions: AsyncDeckDefinitionRepository;
    deckPositions: AsyncDeckPositionRepository;
    workcells: AsyncWorkcellRepository;
    dataOutputs: AsyncDataOutputRepository;
    parameters: AsyncParameterRepository;
    assetRequirements: AsyncProtocolAssetRequirementRepository;
}

/**
 * Create all repositories for a service
 */
export function createAsyncRepositories(opfs: SqliteOpfsService): AsyncRepositories {
    return {
        protocolRuns: new AsyncProtocolRunRepository(opfs),
        protocolDefinitions: new AsyncProtocolDefinitionRepository(opfs),
        functionCallLogs: new AsyncFunctionCallLogRepository(opfs),
        machines: new AsyncMachineRepository(opfs),
        machineDefinitions: new AsyncMachineDefinitionRepository(opfs),
        machineFrontendDefinitions: new AsyncMachineFrontendDefinitionRepository(opfs),
        machineBackendDefinitions: new AsyncMachineBackendDefinitionRepository(opfs),
        resources: new AsyncResourceRepository(opfs),
        resourceDefinitions: new AsyncResourceDefinitionRepository(opfs),
        decks: new AsyncDeckRepository(opfs),
        deckDefinitions: new AsyncDeckDefinitionRepository(opfs),
        deckPositions: new AsyncDeckPositionRepository(opfs),
        workcells: new AsyncWorkcellRepository(opfs),
        dataOutputs: new AsyncDataOutputRepository(opfs),
        parameters: new AsyncParameterRepository(opfs),
        assetRequirements: new AsyncProtocolAssetRequirementRepository(opfs),
    };
}
