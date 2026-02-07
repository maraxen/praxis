/**
 * Browser Mock Router
 * 
 * Centralizes mock data routing for browser mode.
 * Extracts the routing logic from the HTTP interceptor to be reusable
 * by both the interceptor (for HttpClient requests) and the request.ts
 * (for generated API client requests that use native fetch).
 * 
 * IMPORTANT: This class can be used in two contexts:
 * 1. Via Angular DI (when sqliteService is passed in)
 * 2. Via direct instantiation (when called from request.ts outside DI)
 * 
 * In the second case, we lazy-load SqliteService ourselves.
 */

import { Injectable } from '@angular/core';
import { Observable, of, map, forkJoin } from 'rxjs';
import { SqliteService } from '@core/services/sqlite';
import { ProtocolRun, Machine, Resource, MachineDefinition } from '@core/db/schema';
import { GlobalInjector } from '@core/utils/global-injector';
import { ProtocolDefinition } from '@features/protocols/models/protocol.models';

import {
    isConnectHardwareBody,
    isCreateProtocolRunBody,
    isRegisterHardwareBody,
    isReplCommandBody,
    RegisterHardwareRequestBody,
} from './interceptor.models';

function getSqliteService(): SqliteService {
    return GlobalInjector.get(SqliteService);
}

@Injectable({
    providedIn: 'root'
})
export class BrowserMockRouter {
    /**
     * Route a request to the appropriate mock handler.
     * Returns null if no handler is found.
     *
     * @param url - The request URL
     * @param method - The HTTP method
     * @param body - The request body (for POST/PUT)
     * @param sqliteService - SqliteService instance (can be null, will lazy-load)
     */
    route<T>(
        url: string,
        method: string,
        body: unknown,
        sqliteService: SqliteService | null
    ): Observable<T> | null {
        console.log('[BrowserMockRouter] Routing:', method, url);
        // Lazy-load SqliteService if not provided
        const db = sqliteService ?? getSqliteService();

        // Protocol definitions - return list from SQLite
        if (url.includes('/protocols/definitions') && method === 'GET') {
            return db.getProtocols().pipe(
                map(protocols => {
                    const domainProtocols = protocols as unknown as ProtocolDefinition[];
                    console.log(`[BrowserMockRouter] Returning ${domainProtocols.length} protocols`);
                    domainProtocols.forEach(p => {
                        console.log(`[BrowserMockRouter] Protocol: ${p.name}, Parameters: ${p.parameters?.length || 0}`);
                    });
                    return domainProtocols;
                })
            ) as unknown as Observable<T>;
        }

        // Protocol run queue - return active/running runs
        if (url.includes('/protocols/runs/queue') && method === 'GET') {
            return db.getProtocolRuns().pipe(
                map(runs => {
                    return runs.filter((r: ProtocolRun) =>
                        ['pending', 'preparing', 'queued', 'running'].includes(r.status || '')
                    ).map((r: ProtocolRun) => ({
                        accession_id: r.accession_id,
                        name: r.name,
                        status: r.status,
                        created_at: r.created_at,
                        protocol_name: r.name,
                    }));
                })
            ) as Observable<T>;
        }

        // Protocol run records (history) - return all runs for pagination
        if (url.includes('/protocols/runs/records') && method === 'GET') {
            const recordMatch = url.match(/\/protocols\/runs\/records\/([a-f0-9-]+)$/);
            if (recordMatch) {
                const runId = recordMatch[1];
                return db.getProtocolRun(runId).pipe(
                    map(run => {
                        if (run) {
                            return {
                                ...run,
                                name: run.name,
                                start_time: run.created_at, // Approximation if started_at missing
                                end_time: run.updated_at,
                                duration_ms: run.status === 'COMPLETED' ? 262000 : null,
                                logs: [
                                    'Starting protocol execution...',
                                    'Initializing liquid handler...',
                                    'Loading deck configuration...',
                                    `Executing ${run.name}...`,
                                    run.status === 'COMPLETED' ? 'Protocol completed successfully.' : 'Protocol execution in progress...',
                                ],
                            };
                        }
                        return null;
                    })
                ) as Observable<T>;
            }
            // Return list with consistent field names
            return db.getProtocolRuns().pipe(
                map(runs => runs.map((r: ProtocolRun) => ({
                    accession_id: r.accession_id,
                    name: r.name,
                    status: r.status,
                    created_at: r.created_at,
                    start_time: r.created_at,
                    end_time: r.updated_at,
                    duration_ms: r.status === 'COMPLETED' ? 262000 : null,
                    protocol_name: r.name,
                    protocol_accession_id: r.top_level_protocol_definition_accession_id,
                })))
            ) as Observable<T>;
        }

        // Protocol runs - return array from SQLite (legacy fallback)
        if (url.includes('/protocols/runs') && method === 'GET' && !url.match(/\/protocols\/runs\/[a-f0-9-]+$/)) {
            return db.getProtocolRuns() as Observable<T>;
        }

        // Single protocol run by ID
        const singleRunMatch = url.match(/\/protocols\/runs\/([a-f0-9-]+)$/);
        if (singleRunMatch && method === 'GET') {
            const runId = singleRunMatch[1];
            return db.getProtocolRun(runId).pipe(
                map(run => {
                    if (run) {
                        return {
                            ...run,
                            name: run.name,
                            start_time: run.created_at,
                            end_time: run.updated_at,
                            duration_ms: run.status === 'COMPLETED' ? 262000 : null,
                        };
                    }
                    return null;
                })
            ) as Observable<T>;
        }

        // PLR Resource type definitions (comprehensive list)
        if (url.includes('/resources/type-definitions') && method === 'GET') {
            return db.getResourceDefinitions() as Observable<T>;
        }

        // Resource definitions (for AssetSelector filtering)
        if (url.includes('/resources/definitions') && method === 'GET') {
            return db.getResourceDefinitions() as Observable<T>;
        }

        // Resources - return array from database
        if (url.includes('/resources') && !url.includes('type-definitions') && !url.includes('definitions') && method === 'GET') {
            return db.getResources() as Observable<T>;
        }

        // PLR Machine type definitions (comprehensive list)
        if (url.includes('/machines/type-definitions') && method === 'GET') {
            return db.getMachineDefinitions() as Observable<T>;
        }

        // Machines - return array from database
        if (url.includes('/machines') && !url.includes('type-definitions') && !url.includes('definitions') && method === 'GET') {
            return db.getMachines() as Observable<T>;
        }

        // Machine definitions
        if (url.includes('/machines/definitions') && method === 'GET') {
            return db.getMachineDefinitions() as Observable<T>;
        }

        // Discovery - type definitions (trigger sync)
        if (url.includes('/discovery/sync-all') && method === 'POST') {
            return forkJoin({
                resources: db.getResourceDefinitions(),
                machines: db.getMachineDefinitions()
            }).pipe(
                map(({ resources, machines }) => ({
                    message: 'Browser mode - PLR definitions loaded (SQLite)',
                    synced: true,
                    resources: resources.length,
                    machines: machines.length,
                }))
            ) as Observable<T>;
        }

        // Discovery - get type definitions
        if (url.includes('/discovery/type-definitions') && method === 'GET') {
            return forkJoin({
                resources: db.getResourceDefinitions(),
                machines: db.getMachineDefinitions()
            }).pipe(
                map(({ resources, machines }) => ({
                    resources,
                    machines
                }))
            ) as Observable<T>;
        }

        // Machine facets
        if (url.includes('/machines/definitions/facets') && method === 'GET') {
            return of({
                machine_category: [
                    { value: 'Liquid Handler', count: 1 },
                    { value: 'Plate Reader', count: 1 }
                ],
                manufacturer: [
                    { value: 'Hamilton', count: 1 },
                    { value: 'Opentrons', count: 1 }
                ]
            }) as Observable<T>;
        }

        // Resource facets
        if (url.includes('/facets')) {
            return db.getResourceDefinitions().pipe(
                map(defs => {
                    const categories = [...new Set(defs.map(r => r.plr_category))];
                    const vendors = [...new Set(defs.map(r => r.vendor).filter((v): v is string => !!v))];
                    return {
                        category: categories,
                        brand: vendors,
                        vendor: vendors,
                    };
                })
            ) as Observable<T>;
        }

        // User info
        if (url.includes('/auth/me') || url.includes('/auth/user')) {
            return of({
                id: 'local-user',
                username: 'local',
                email: 'local@praxis.local',
                roles: ['user', 'browser-mode'],
                name: 'Local User',
            }) as Observable<T>;
        }

        // POST protocol run - simulate creation
        if (url.includes('/protocols/runs') && method === 'POST') {
            const runBody = isCreateProtocolRunBody(body) ? body : {};
            const newRun = {
                accession_id: crypto.randomUUID(),
                status: 'queued',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                name: runBody.name || 'New Run',
                protocol_definition_accession_id: runBody.protocol_definition_accession_id || '',
                ...(runBody as object),
            } as ProtocolRun;
            return db.createProtocolRun(newRun) as Observable<T>;
        }

        // Transfer logs
        const transferLogsMatch = url.match(/\/protocols\/runs\/([a-f0-9-]+)\/transfer-logs$/);
        if (transferLogsMatch && method === 'GET') {
            return db.getTransferLogs(transferLogsMatch[1]) as Observable<T>;
        }

        // Workcell
        if (url.includes('/workcell') && method === 'GET') {
            return db.getMachines().pipe(
                map(machines => ({
                    name: 'Default Workcell',
                    status: 'AVAILABLE',
                    machines: machines.slice(0, 2),
                }))
            ) as Observable<T>;
        }

        // Scheduler - queue
        if (url.includes('/scheduler/queue') && method === 'GET') {
            return of([]) as Observable<T>;
        }

        // Decks
        if (url.includes('/decks') && method === 'GET') {
            return of([]) as Observable<T>;
        }

        // Hardware discovery
        if (url.includes('/hardware/discover') && method === 'GET') {
            return db.getMachineDefinitions().pipe(
                map(defs => {
                    const simulators = defs
                        .filter((m: MachineDefinition) => m.fqn.includes('simulation') || (m.properties_json as { simulated?: boolean })?.['simulated'])
                        .map((m: MachineDefinition) => ({
                            id: `sim-${m.accession_id}`,
                            name: m.name,
                            connection_type: 'simulator',
                            status: 'available',
                            manufacturer: m.manufacturer || 'PyLabRobot',
                            model: m.name,
                            plr_backend: m.fqn,
                            properties: m.properties_json,
                        }));

                    const simulatedDevices = [
                        ...simulators,
                        {
                            id: 'sim-ot2',
                            name: 'Opentrons OT-2 (Simulated)',
                            connection_type: 'network',
                            status: 'available',
                            ip_address: '192.168.1.100',
                            manufacturer: 'Opentrons',
                            model: 'OT-2',
                            plr_backend: 'pylabrobot.liquid_handling.backends.opentrons.OT2',
                            properties: { simulated: true },
                        },
                        {
                            id: 'sim-star',
                            name: 'Hamilton STAR (Simulated)',
                            connection_type: 'serial',
                            status: 'available',
                            port: '/dev/ttyUSB0',
                            manufacturer: 'Hamilton',
                            model: 'STAR',
                            plr_backend: 'pylabrobot.liquid_handling.backends.hamilton.STAR',
                            properties: { simulated: true },
                        },
                    ];

                    return {
                        devices: simulatedDevices,
                        total: simulatedDevices.length,
                        serial_count: 1,
                        simulator_count: simulators.length,
                        network_count: 1,
                    };
                })
            ) as Observable<T>;
        }

        // Hardware connection
        if (url.includes('/hardware/connect') && method === 'POST') {
            const devId = (isConnectHardwareBody(body) ? body.device_id : undefined) || 'unknown';
            console.log(`[BrowserMockRouter] Mock connecting to hardware: ${devId}`);
            return of({
                device_id: devId,
                status: 'connected',
                message: devId.includes('sim') ? 'Simulator connected' : 'Physical hardware mock connected',
                connection_handle: `local-handle-${Date.now()}`,
                capabilities: ['liquid_handling', 'plate_reading', 'shaking']
            }) as Observable<T>;
        }

        // Hardware status
        if (url.includes('/hardware/status') && method === 'GET') {
            const devIdMatch = url.match(/\/hardware\/status\/([a-f0-9-]+)$/);
            return of({
                device_id: devIdMatch ? devIdMatch[1] : 'unknown',
                status: 'ready',
                uptime_seconds: 3600,
                diagnostics: {
                    temp: 24.5,
                    voltages: [5.0, 12.0, 24.0],
                    errors: []
                }
            }) as Observable<T>;
        }

        // Hardware connections list
        if (url.includes('/hardware/connections') && method === 'GET') {
            return of([]) as Observable<T>;
        }

        // Hardware registration
        if (url.includes('/hardware/register') && method === 'POST') {
            let payload: RegisterHardwareRequestBody = {};
            if (isRegisterHardwareBody(body)) {
                if (typeof body === 'string') {
                    payload = JSON.parse(body);
                } else {
                    payload = body;
                }
            }

            console.log('[BrowserMockRouter] Hardware register payload (parsed):', payload);
            return db.createMachine({
                name: payload.name || 'Registered Machine',
                plr_backend: payload.plr_backend || '',
                connection_type: payload.connection_type,
                configuration: payload.configuration
            }) as Observable<T>;
        }

        // Protocol compatibility check
        if (url.match(/\/protocols\/[a-f0-9-]+\/compatibility$/) && method === 'GET') {
            return db.getMachines().pipe(
                map(machines => {
                    const liquidHandlers = machines.filter((m: Machine) => m.asset_type === 'MACHINE' || m.asset_type === 'GENERIC_ASSET'); // Broaden filer
                    return liquidHandlers.map((machine: Machine) => ({
                        machine: {
                            accession_id: machine.accession_id,
                            name: machine.name,
                            machine_type: machine.asset_type || 'liquid_handler',
                        },
                        compatibility: {
                            is_compatible: true,
                            missing_capabilities: [],
                            matched_capabilities: ['liquid_handling', 'pipetting'],
                            warnings: [],
                        }
                    }));
                })
            ) as Observable<T>;
        }

        // Hardware REPL command
        if (url.includes('/hardware/repl') && method === 'POST') {
            const payload = isReplCommandBody(body) ? body : {};
            return of({
                device_id: payload.device_id || 'unknown',
                command: payload.command || '',
                output: `[Browser Playground] Executed: ${payload.command}\n> OK`,
                success: true,
                error: null,
            }) as Observable<T>;
        }

        // No handler found
        return null;
    }
}
