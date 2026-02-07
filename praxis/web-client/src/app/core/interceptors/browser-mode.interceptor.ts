import { HttpRequest, HttpHandlerFn, HttpEvent, HttpResponse } from '@angular/common/http';
import { Observable, of, delay, switchMap, map } from 'rxjs';
import { inject } from '@angular/core';
import { ModeService } from '@core/services/mode.service';
import { SqliteService } from '@core/services/sqlite';
import { Machine, ProtocolRun } from '@core/db/schema';

// Import new request body interfaces
import {
  isConnectHardwareBody,
  isCreateProtocolRunBody,
  isRegisterHardwareBody,
  isReplCommandBody,
  MockMachine
} from './interceptor.models';

// Import mock data for fallback

import { MOCK_RESOURCES, MOCK_RESOURCE_DEFINITIONS } from '@assets/browser-data/resources';
import { MOCK_MACHINES } from '@assets/browser-data/machines';
import { PLR_RESOURCE_DEFINITIONS, PLR_MACHINE_DEFINITIONS } from '@assets/browser-data/plr-definitions';

const LATENCY_MS = 150;


/**
 * Get mock response for a given URL and method
 */
function getMockResponse(req: HttpRequest<unknown>, sqliteService: SqliteService): Observable<unknown> {
    const url = req.url;
    const method = req.method;

    // Protocol definitions - return list from SQLite
    if (url.includes('/protocols/definitions') && method === 'GET') {
        return sqliteService.getProtocols();
    }

    // Protocol run queue - return active/running runs
    if (url.includes('/protocols/runs/queue') && method === 'GET') {
        return sqliteService.getProtocolRuns().pipe(
            map((runs: ProtocolRun[]) => {
                const activeRuns = runs.filter((r: ProtocolRun) =>
                    r.status && ['PENDING', 'PREPARING', 'QUEUED', 'RUNNING', 'PAUSED'].includes(r.status.toUpperCase())
                ).map(r => ({
                    accession_id: r.accession_id,
                    name: r.name,
                    status: r.status,
                    created_at: r.created_at,
                    protocol_name: r.name, // Using run name as protocol name for now as they are usually same or similar
                }));

                return {
                    items: activeRuns,
                    total: activeRuns.length,
                    page: 1,
                    size: 50
                };
            })
        );
    }

    // Protocol run records (history) - return all runs for pagination
    if (url.includes('/protocols/runs/records') && method === 'GET') {
        const recordMatch = url.match(/\/protocols\/runs\/records\/([a-f0-9-]+)$/);
        if (recordMatch) {
            const runId = recordMatch[1];
            return sqliteService.getProtocolRun(runId).pipe(
                map(run => {
                    if (run) {
                        return {
                            ...run,
                            // Ensure fields match expectation
                            name: run.name,
                            protocol_name: run.name,
                            start_time: run.start_time,
                            end_time: run.end_time,
                            duration_ms: run.duration_ms, // Should be in DB or calculated
                            logs: [] // Logs populated separately via /transfer-logs usually
                        };
                    }
                    // Return explicit 404 if not found
                    throw new HttpResponse({ status: 404, statusText: 'Not Found' });
                })
            );
        }

        return sqliteService.getProtocolRuns().pipe(
            map((runs: ProtocolRun[]) => {
                return {
                    items: runs.map((r: ProtocolRun) => ({
                        accession_id: r.accession_id,
                        name: r.name,
                        status: r.status,
                        created_at: r.created_at,
                        start_time: r.start_time,
                        end_time: r.end_time,
                        duration_ms: r.duration_ms,
                        protocol_name: r.name,
                        protocol_accession_id: r.top_level_protocol_definition_accession_id
                    })),
                    total: runs.length,
                    page: 1,
                    size: 50
                };
            })
        );
    }

    // Protocol runs - return array from SQLite (legacy fallback)
    if (url.includes('/protocols/runs') && method === 'GET' && !url.match(/\/protocols\/runs\/[a-f0-9-]+$/)) {
        return sqliteService.getProtocolRuns();
    }

    // PLR Resource type definitions (comprehensive list)
    if (url.includes('/resources/type-definitions') && method === 'GET') {
        return of(PLR_RESOURCE_DEFINITIONS);
    }

    // Resource definitions (for AssetSelector filtering) - must come before /resources
    if (url.includes('/resources/definitions') && method === 'GET') {
        // Combine curated definitions with comprehensive PLR definitions
        return of([...MOCK_RESOURCE_DEFINITIONS, ...PLR_RESOURCE_DEFINITIONS]);
    }

    // Resources - return array directly
    if (url.includes('/resources') && !url.includes('type-definitions') && !url.includes('definitions') && method === 'GET') {
        return of(MOCK_RESOURCES);
    }

    // PLR Machine type definitions (comprehensive list)
    if (url.includes('/machines/type-definitions') && method === 'GET') {
        return of(PLR_MACHINE_DEFINITIONS);
    }

    // Machines - return array from SQLite
    if (url.includes('/machines') && !url.includes('type-definitions') && !url.includes('definitions') && method === 'GET') {
        return sqliteService.getMachines();
    }

    // Machine definitions
    if (url.includes('/machines/definitions') && method === 'GET') {
        return of([...MOCK_MACHINES, ...PLR_MACHINE_DEFINITIONS]);
    }

    // Discovery - type definitions (trigger sync - in browser mode just return success)
    if (url.includes('/discovery/sync-all') && method === 'POST') {
        return of({
            message: 'Browser mode - PLR definitions loaded',
            synced: true,
            resources: PLR_RESOURCE_DEFINITIONS.length,
            machines: PLR_MACHINE_DEFINITIONS.length,
        });
    }

    // Discovery - get type definitions
    if (url.includes('/discovery/type-definitions') && method === 'GET') {
        return of({
            resources: PLR_RESOURCE_DEFINITIONS,
            machines: PLR_MACHINE_DEFINITIONS,
        });
    }

    // Resource facets - dynamically generated from PLR definitions
    if (url.includes('/facets')) {
        const categories = [...new Set(PLR_RESOURCE_DEFINITIONS.map(r => r.plr_category))];
        const vendors = [...new Set(PLR_RESOURCE_DEFINITIONS.map(r => r.vendor).filter(Boolean))];
        return of({
            category: categories,
            brand: vendors,
            vendor: vendors,
        });
    }

    // User info
    if (url.includes('/auth/me') || url.includes('/auth/user')) {
        return of({
            id: 'local-user',
            username: 'local',
            email: 'local@praxis.local',
            roles: ['user', 'browser-mode'],
            name: 'Local User',
        });
    }

    // POST protocol run - simulate creation
    if (url.includes('/protocols/runs') && method === 'POST') {
        const body = req.body;
        const newRun: ProtocolRun = {
            accession_id: crypto.randomUUID(),
            protocol_definition_accession_id: (isCreateProtocolRunBody(body) ? body.protocol_definition_accession_id : undefined) || 'unknown',
            name: (isCreateProtocolRunBody(body) ? body.name : undefined) || 'Run',
            status: 'QUEUED',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            properties_json: {},
            input_parameters_json: (isCreateProtocolRunBody(body) ? body.parameters : undefined) || {},
            top_level_protocol_definition_accession_id: (isCreateProtocolRunBody(body) ? body.protocol_definition_accession_id : undefined) || 'unknown',
            start_time: null,
            end_time: null,
            duration_ms: null,
            data_directory_path: null,
            resolved_assets_json: null,
            output_data_json: null,
            initial_state_json: null,
            final_state_json: null,
            created_by_user: null,
            previous_accession_id: null
        };
        return sqliteService.createProtocolRun(newRun);
    }

    // Transfer logs
    const transferLogsMatch = url.match(/\/protocols\/runs\/([a-f0-9-]+)\/transfer-logs$/);
    if (transferLogsMatch && method === 'GET') {
        return sqliteService.getTransferLogs(transferLogsMatch[1]);
    }

    // Workcell
    if (url.includes('/workcell') && method === 'GET') {
        return of({
            name: 'Default Workcell',
            status: 'AVAILABLE',
            machines: MOCK_MACHINES.slice(0, 2),
        });
    }

    // Scheduler - queue
    if (url.includes('/scheduler/queue') && method === 'GET') {
        return of([]);
    }

    // Decks
    if (url.includes('/decks') && method === 'GET') {
        return of([]);
    }

    // Hardware discovery
    if (url.includes('/hardware/discover') && method === 'GET') {
        const simulators = PLR_MACHINE_DEFINITIONS
            .filter(m => m.fqn.includes('simulation') || m.properties_json?.['simulated'])
            .map(m => ({
                id: `sim-${m.accession_id}`,
                name: m.name,
                connection_type: 'simulator',
                status: 'available',
                manufacturer: m.vendor || 'PyLabRobot',
                model: m.name,
                plr_backend: m.fqn,
                properties: m.properties_json,
            }));

        // Add simulated hardware entries
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

        return of({
            devices: simulatedDevices,
            total: simulatedDevices.length,
            serial_count: 1,
            simulator_count: simulators.length,
            network_count: 1,
        });
    }

    // Hardware connection (browser mode - always succeed)
    if (url.includes('/hardware/connect') && method === 'POST') {
        const body = req.body;
        return of({
            device_id: (isConnectHardwareBody(body) ? body.device_id : undefined) || 'unknown',
            status: 'connected',
            message: 'Connected successfully (browser mode)',
            connection_handle: `local-handle-${Date.now()}`,
        });
    }

    // Hardware connections list
    if (url.includes('/hardware/connections') && method === 'GET') {
        return of([]);
    }

    // Hardware registration
    if (url.includes('/hardware/register') && method === 'POST') {
        const body = req.body;
        const registrationBody = isRegisterHardwareBody(body) ? body : {};
        console.log('[BrowserModeIntercepter] Hardware register body:', registrationBody);
        return sqliteService.createMachine({
            name: registrationBody?.name || 'Registered Machine',
            plr_backend: registrationBody?.plr_backend || '',
            connection_type: registrationBody?.connection_type,
            configuration: registrationBody?.configuration
        });
    }

    // Protocol compatibility check - return compatible machines from SQLite
    if (url.match(/\/protocols\/[a-f0-9-]+\/compatibility$/) && method === 'GET') {
        // Return compatibility data based on actual machines in SQLite
        return sqliteService.getMachines().pipe(
            map(machines => {
                return machines.map((machine: MockMachine) => ({
                    machine: {
                        accession_id: machine.accession_id,
                        name: machine.name,
                        machine_category: machine.machine_category || machine.machine_type || 'LiquidHandler',
                        // Add other fields needed by MachineCard / MachineSelection
                        is_simulation_override: machine.is_simulation_override || true,
                        backend_definition: machine.backend_definition
                    },
                    compatibility: {
                        is_compatible: true, // In browser mode, we assume compatibility or handle it in frontend
                        missing_capabilities: [],
                        matched_capabilities: ['liquid_handling', 'pipetting'],
                        warnings: [],
                    }
                }));
            })
        );
    }

    // Hardware REPL command
    if (url.includes('/hardware/repl') && method === 'POST') {
        const body = req.body;
        const replBody = isReplCommandBody(body) ? body : {};
        return of({
            device_id: replBody?.device_id || 'unknown',
            command: replBody?.command || '',
            output: `[Browser Playground] Executed: ${replBody?.command}\n> OK`,
            success: true,
            error: null,
        });
    }

    return of(null);
}

/**
 * Browser Mode HTTP Interceptor (functional style)
 *
 * In browser mode, intercepts API requests and returns mock data instead of
 * making actual network requests. This enables the application to run
 * entirely client-side without a backend.
 */
export const browserModeInterceptor = (req: HttpRequest<unknown>, next: HttpHandlerFn): Observable<HttpEvent<unknown>> => {
    const modeService = inject(ModeService);
    const url = req.url;

    // Debug logging for troubleshooting mode detection
    if (url.includes('/api/') && !url.includes('assets/')) {
        console.debug(`[BrowserModeIntercepter] Request: ${req.method} ${url}, IsBrowserMode: ${modeService.isBrowserMode()}`);
    }

    // Only intercept in browser modes
    if (!modeService.isBrowserMode()) {
        return next(req);
    }

    // Only intercept API requests (exclude assets)
    if (!req.url.includes('/api/') || req.url.includes('assets/')) {
        return next(req);
    }

    const sqliteService = inject(SqliteService);
    const method = req.method;

    // Route to mock handlers
    return getMockResponse(req, sqliteService).pipe(
        delay(LATENCY_MS),
        switchMap(response => {
            if (response !== null) {
                return of(new HttpResponse({
                    status: 200,
                    body: response,
                }));
            }
            // If no mock handler, log warning and return empty response
            console.warn(`[BrowserModeInterceptor] No mock handler for: ${method} ${url}`);
            return of(new HttpResponse({
                status: 200,
                body: { message: 'Browser mode - endpoint not mocked', url, method },
            }));
        })
    );
};
