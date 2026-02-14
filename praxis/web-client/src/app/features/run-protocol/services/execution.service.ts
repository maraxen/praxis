import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ModeService } from '@core/services/mode.service';
import { PythonRuntimeService } from '@core/services/python-runtime.service';
import { SqliteService } from '@core/services/sqlite';
import { environment } from '@env/environment';
import { Observable, Subject, of, firstValueFrom, throwError } from 'rxjs';
import { catchError, map, retry, switchMap, tap } from 'rxjs/operators';
import { WebSocketSubject, webSocket } from 'rxjs/webSocket';
import { ExecutionError, ExecutionErrorType, ExecutionMessage, ExecutionState, ExecutionStatus } from '../models/execution.models';
import { MachineCompatibility } from '../models/machine-compatibility.models';
import { ProtocolsService } from '@api/services/ProtocolsService';
import { calculateDiff } from '@core/utils/state-diff';
import { assetUrl } from '@core/utils/asset-url';
import { ApiWrapperService } from '@core/services/api-wrapper.service';
import { ProtocolRun } from '@core/db/schema';

import { WizardStateService } from './wizard-state.service';

@Injectable({
  providedIn: 'root'
})
export class ExecutionService {
  private modeService = inject(ModeService);
  private pythonRuntime = inject(PythonRuntimeService);
  private sqliteService = inject(SqliteService);
  private http = inject(HttpClient);
  private wizardState = inject(WizardStateService);
  private snackBar = inject(MatSnackBar);

  private readonly WS_URL = environment.wsUrl;
  private readonly API_URL = environment.apiUrl;

  private socket$: WebSocketSubject<any> | null = null;
  private messagesSubject = new Subject<ExecutionMessage>();

  // Use signals for reactive state
  private _currentRun = signal<ExecutionState | null>(null);
  private _isConnected = signal<boolean>(false);
  private lastSavedState: any = null;

  // Public computed signals
  readonly currentRun = this._currentRun.asReadonly();
  readonly isConnected = this._isConnected.asReadonly();
  readonly isRunning = computed(() => this._currentRun()?.status === ExecutionStatus.RUNNING);
  readonly isPaused = computed(() => this._currentRun()?.status === ExecutionStatus.PAUSED);

  messages$ = this.messagesSubject.asObservable();

  private apiWrapper = inject(ApiWrapperService);
  private heartbeatInterval?: ReturnType<typeof setInterval>;

  /**
   * Start sending heartbeats to the database
   */
  private startHeartbeat(runId: string): void {
    this.heartbeatInterval = setInterval(() => {
      this.sqliteService.protocolRuns.pipe(
        switchMap(repo => repo.findById(runId)),
        switchMap(run => {
          if (run) {
            const metadata = (run.properties_json || {}) as any;
            metadata.lastHeartbeat = Date.now();
            return this.sqliteService.protocolRuns.pipe(
              switchMap(repo => repo.update(runId, { properties_json: metadata } as any))
            );
          }
          return of(null);
        })
      ).subscribe({
        error: err => console.warn('[ExecutionService] Heartbeat update failed:', err)
      });
    }, 5000); // Every 5 seconds
  }

  /**
   * Stop sending heartbeats
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = undefined;
    }
  }

  /**
   * Fetch protocol blob from backend or static assets
   * ERROR PATH: execution.service.ts:95/106 -> Network error or 404/500
   */
  fetchProtocolBlob(id: string): Observable<ArrayBuffer> {
    if (this.modeService.isBrowserMode()) {
      // Fetch from static assets in browser/offline mode
      // Use relative path (no leading slash) to respect base href on GitHub Pages
      return this.http.get(assetUrl(`assets/protocols/${id}.pkl`), {
        responseType: 'arraybuffer'
      }).pipe(
        catchError(err => throwError(() => new ExecutionError(
          ExecutionErrorType.PROTOCOL_NOT_FOUND,
          `Failed to fetch protocol ${id} from assets`,
          err
        )))
      );
    }
    // Default: Fetch from backend API
    return this.http.get(`${this.API_URL}/api/v1/protocols/definitions/${id}/code/binary`, {
      responseType: 'arraybuffer'
    }).pipe(
      catchError(err => throwError(() => new ExecutionError(
        ExecutionErrorType.NETWORK_ERROR,
        `Failed to fetch protocol ${id} from API`,
        err
      )))
    );
  }

  /**
   * Check protocol compatibility with available machines
   * ERROR PATH: execution.service.ts:143/151 -> DB error (Browser) or API error (Prod)
   */
  getCompatibility(protocolId: string): Observable<MachineCompatibility[]> {
    // In browser mode, return mock compatibility data
    // In browser mode, return all definitions as templates
    if (this.modeService.isBrowserMode()) {
      return this.sqliteService.machineDefinitions.pipe(
        switchMap(repo => repo.findAll()),
        map((definitions: any[]) => definitions.map(def => ({
          machine: {
            accession_id: `template-${def.accession_id}`,
            name: def.name,
            machine_category: def.machine_category,
            is_simulation_override: true,
            // Use backend from definition or default
            simulation_backend_name: (def.available_simulation_backends?.[0]) || 'Chatterbox',
            description: def.description,
            machine_definition_accession_id: def.accession_id,
            is_template: true
          } as any,
          compatibility: {
            is_compatible: true,
            missing_capabilities: [],
            matched_capabilities: [],
            warnings: []
          }
        } as MachineCompatibility))),
        catchError(err => throwError(() => new ExecutionError(
          ExecutionErrorType.PERSISTENCE_ERROR,
          'Failed to load machine definitions for compatibility check',
          err
        )))
      );
    }
    return (this.apiWrapper.wrap(ProtocolsService.getProtocolCompatibilityApiV1ProtocolsAccessionIdCompatibilityGet(protocolId)) as Observable<MachineCompatibility[]>).pipe(
      catchError(err => throwError(() => new ExecutionError(
        ExecutionErrorType.NETWORK_ERROR,
        'Failed to check protocol compatibility via API',
        err
      )))
    );
  }

  /**
   * Start a new protocol run
   * ERROR PATH: execution.service.ts:181 -> Validation error
   * ERROR PATH: execution.service.ts:200 -> Browser run start failure
   * ERROR PATH: execution.service.ts:210 -> API start run failure
   */
  startRun(
    protocolId: string,
    runName: string,
    parameters?: Record<string, unknown>,
    simulationMode: boolean = true,
    notes?: string,
    protocol?: any
  ): Observable<{ run_id: string }> {
    // AUDIT-01: Defense-in-depth validation
    if (!simulationMode && parameters) {
      const hasSimulatedConfig = Object.values(parameters).some((val: any) =>
        val && typeof val === 'object' && val.is_simulated === true
      );

      if (hasSimulatedConfig) {
        return throwError(() => new ExecutionError(
          ExecutionErrorType.VALIDATION_ERROR,
          'Cannot start physical run with simulated machine configuration'
        ));
      }
    }

    // Browser mode: execute via Pyodide
    if (this.modeService.isBrowserMode()) {
      return this.startBrowserRun(protocolId, runName, parameters, notes, protocol);
    }

    // Production mode: use HTTP API
    return this.apiWrapper.wrap(ProtocolsService.startProtocolRunApiV1ProtocolsRunsActionsStartPost({
      protocol_definition_accession_id: protocolId,
      name: runName,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      parameters: parameters as Record<string, any>,
      simulation_mode: simulationMode
    })).pipe(
      tap(response => {
        this._currentRun.set({
          runId: response.run_id,
          protocolName: runName,
          status: ExecutionStatus.PENDING,
          progress: 0,
          logs: []
        });
        this.connectWebSocket(response.run_id);
      }),
      catchError(err => throwError(() => new ExecutionError(
        ExecutionErrorType.NETWORK_ERROR,
        'Failed to start protocol run via API',
        err
      )))
    );
  }

  /**
   * Execute protocol in browser mode using Pyodide
   * ERROR PATH: execution.service.ts:275 -> persistence failure
   */
  private startBrowserRun(
    protocolId: string,
    runName: string,
    parameters?: Record<string, unknown>,
    notes?: string,
    protocol?: any
  ): Observable<{ run_id: string }> {
    const runId = crypto.randomUUID();

    // Initialize run state
    this._currentRun.set({
      runId,
      protocolName: runName,
      status: ExecutionStatus.PENDING,
      progress: 0,
      logs: ['[Browser Mode] Starting execution...']
    });

    // Persist run to IndexedDB
    const runRecord: ProtocolRun & { protocol_definition_accession_id: string } = {
      accession_id: runId,
      protocol_definition_accession_id: protocolId,
      name: runName,
      status: ExecutionStatus.QUEUED,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      start_time: null,
      end_time: null,
      data_directory_path: null,
      input_parameters_json: (parameters || {}) as Record<string, unknown>,
      properties_json: { notes, simulation_mode: true } as Record<string, unknown>,
      top_level_protocol_definition_accession_id: protocolId,
      duration_ms: null,
      resolved_assets_json: null,
      output_data_json: null,
      initial_state_json: null,
      final_state_json: null,
      created_by_user: null,
      previous_accession_id: null
    };

    return this.sqliteService.protocolRuns.pipe(
      switchMap(repo => repo.create(runRecord as any)),
      tap(() => {
        // Execute asynchronously
        this.executeBrowserProtocol(protocolId, runId, parameters);

        // Start heartbeat
        this.startHeartbeat(runId);
      }),
      map(() => ({ run_id: runId })),
      catchError(err => {
        console.warn('[ExecutionService] Failed to persist run:', err);
        return throwError(() => new ExecutionError(
          ExecutionErrorType.PERSISTENCE_ERROR,
          'Failed to persist protocol run to local database',
          err
        ));
      })
    );
  }

  /**
   * Execute protocol code in Pyodide worker
   * ERROR PATH: execution.service.ts:303 -> DB update failure (Silent)
   * ERROR PATH: execution.service.ts:312 -> Protocol load failure (IndexedDB or Assets)
   * ERROR PATH: execution.service.ts:456/468 -> Python runtime error or critical stderr
   * ERROR PATH: execution.service.ts:502/521 -> DB update failure (Silent)
   */
  private async executeBrowserProtocol(
    protocolId: string,
    runId: string,
    parameters?: Record<string, unknown>,
    protocol?: any
  ): Promise<void> {
    try {
      // Update status to running
      this.updateRunState({ status: ExecutionStatus.RUNNING });

      // Update status in DB as well
      // SILENT FAILURE FIX: Add error handling
      this.sqliteService.protocolRuns.pipe(
        switchMap(repo => repo.update(runId, { status: ExecutionStatus.RUNNING, start_time: new Date().toISOString() }))
      ).subscribe({
        error: err => console.error('[ExecutionService] Failed to update run status to RUNNING in DB:', err)
      });

      this.addLog('[Browser Mode] Loading protocol...');

      // 1. Retrieve the ProtocolRun record to get resolved assets
      const run = await firstValueFrom(this.sqliteService.getProtocolRun(runId));

      // 2. Build machine configuration from resolved assets or defaults
      const machineEntries: any[] = [];
      if (run?.resolved_assets_json) {
        try {
          const resolvedAssets = typeof run.resolved_assets_json === 'string'
            ? JSON.parse(run.resolved_assets_json)
            : run.resolved_assets_json;

          const assets = Array.isArray(resolvedAssets) ? resolvedAssets : Object.values(resolvedAssets);

          assets.forEach((a: any) => {
            const definition = a.definition;
            const instance = a.machine_instance;

            if (definition) {
              // Determine machine type from FQN or category
              let machineType = 'LiquidHandler'; // Default
              if (definition.fqn?.includes('Reader')) machineType = 'PlateReader';
              if (definition.fqn?.includes('HeaterShaker')) machineType = 'HeaterShaker';

              machineEntries.push({
                param_name: a.param_name || 'liquid_handler', // Fallback
                machine_type: machineType,
                backend_fqn: definition.fqn,
                port_id: instance?.backend_config?.port_id,
                is_simulated: definition.is_simulation_override || false
              });
              this.addLog(`[Browser Mode] Using machine: ${definition.name} (${definition.fqn})`);
            }
          });
        } catch (e) {
          console.warn('[ExecutionService] Failed to parse resolved_assets_json:', e);
        }
      }

      // Extract machine configs from input parameters (wizard passes _create_from_backend objects)
      if (machineEntries.length === 0 && run?.input_parameters_json) {
        try {
          const inputParams = typeof run.input_parameters_json === 'string'
            ? JSON.parse(run.input_parameters_json)
            : run.input_parameters_json;
          for (const [paramName, val] of Object.entries(inputParams || {})) {
            if (val && typeof val === 'object' && (val as any)._create_from_backend) {
              const cfg = val as any;
              machineEntries.push({
                param_name: paramName,
                machine_type: 'LiquidHandler',
                backend_fqn: cfg.simulation_backend_name || 'pylabrobot.liquid_handling.backends.chatterbox.LiquidHandlerChatterboxBackend',
                is_simulated: cfg.is_simulated ?? true
              });
              this.addLog(`[Browser Mode] Machine from wizard: ${paramName} (backend=${cfg.simulation_backend_name})`);
            }
          }
        } catch (e) {
          console.warn('[ExecutionService] Failed to parse input_parameters_json for machines:', e);
        }
      }

      // If no machines found anywhere, add a default simulator (ChatterBox for browser mode)
      if (machineEntries.length === 0) {
        machineEntries.push({
          param_name: 'liquid_handler',
          machine_type: 'LiquidHandler',
          backend_fqn: 'pylabrobot.liquid_handling.backends.chatterbox.LiquidHandlerChatterboxBackend',
          is_simulated: true
        });
      }

      // Fetch protocol blob
      const blob = await firstValueFrom(this.fetchProtocolBlob(protocolId));

      // Load PLR serialized definitions for resource deserialization
      let plrJsonMap: Map<string, string> | undefined;
      let typeFqnMap: Map<string, string> | undefined;
      if (this.modeService.isBrowserMode()) {
        try {
          const repos = await firstValueFrom(this.sqliteService.getAsyncRepositories());
          const defs = await firstValueFrom(repos.resourceDefinitions.findAll());
          plrJsonMap = new Map<string, string>();
          typeFqnMap = new Map<string, string>();
          for (const def of defs) {
            const plrJson = (def as any).plr_definition_details_json;
            if (def.fqn && plrJson) {
              const jsonStr = typeof plrJson === 'string' ? plrJson : JSON.stringify(plrJson);
              plrJsonMap.set(def.fqn, jsonStr);
            }
            // Build type→FQN map: first definition per category wins (like playground's definition lookup)
            const cat = ((def as any).plr_category || '').toLowerCase();
            if (def.fqn && cat && !typeFqnMap.has(cat)) {
              typeFqnMap.set(cat, def.fqn);
            }
          }
          console.log(`[ExecutionService] Loaded ${plrJsonMap.size} PLR definitions, ${typeFqnMap.size} type→FQN mappings`);
        } catch (e) {
          console.warn('[ExecutionService] Failed to load PLR definitions, falling back to FQN-only:', e);
        }
      }

      // BUILD EXECUTION MANIFEST
      const manifest = this.wizardState.buildExecutionManifest(machineEntries, plrJsonMap, typeFqnMap);

      // Patch manifest with actual user parameter values
      // IMPORTANT: Skip deck_resource params — their value must remain as the resource NAME
      // (for registry lookup). The wizard passes UUIDs here which would break resolution.
      if (parameters) {
        manifest.parameters.forEach(p => {
          if (p.is_deck_resource) return; // Don't override deck resource names with UUIDs
          if (parameters[p.name] !== undefined) {
            p.value = parameters[p.name];
          }
        });
      }

      this.addLog(`[Browser Mode] Executing protocol with Typed Manifest`);
      this.updateRunState({ progress: 20, currentStep: 'Running protocol' });

      // Artificial delay to make simulation testable in E2E
      await new Promise(r => setTimeout(r, 1000));

      await new Promise<void>((resolve, reject) => {
        let hasError = false;

        this.pythonRuntime.executeBlob(blob, runId, manifest).subscribe({
          next: (output) => {
            if (output.type === 'stdout') {
              this.addLog(output.content);
            } else if (output.type === 'stderr') {
              this.addLog(`[Error] ${output.content}`);
              // Only flag critical errors — not all stderr (Python logs warnings/debug to stderr)
              const content = output.content;
              if (content.includes('TypeError:') || content.includes('SyntaxError:') ||
                content.includes('ImportError:') || content.includes('RuntimeError:') ||
                content.includes('AttributeError:') || content.includes('NameError:') ||
                content.includes('Traceback (most recent call last)')) {
                hasError = true;
              }
            } else if (output.type === 'result') {
              this.addLog(`[Result] ${output.content}`);
            } else if (output.type === 'well_state_update') {
              try {
                const wellState = JSON.parse(output.content);
                const currentState = this._currentRun();
                if (currentState) {
                  this._currentRun.set({
                    ...currentState,
                    wellState
                  });
                }
              } catch (err) {
                console.error('[ExecutionService] Error parsing browser state update:', err);
              }
            } else if (output.type === 'function_call_log') {
              try {
                const logData = JSON.parse(output.content);
                this.handleFunctionCallLog(runId, logData);
              } catch (err) {
                console.error('[ExecutionService] Error parsing function call log:', err);
              }
            }
          },
          error: (err) => {
            this.addLog(`[Error] Execution failed: ${err}`);
            reject(err);
          },
          complete: () => {
            if (hasError) {
              reject(new Error('Protocol execution had errors'));
            } else {
              resolve();
            }
          }
        });
      });

      // Allow async logs to flush
      await new Promise(resolve => setTimeout(resolve, 200));
      this.addLog('[Protocol Execution Complete]');

      // Success
      this.updateRunState({
        status: ExecutionStatus.COMPLETED,
        progress: 100,
        endTime: new Date().toISOString()
      });
      this.addLog('[Browser Mode] Execution completed successfully.');

      // Update run status in DB
      // SILENT FAILURE FIX: Add error handling
      this.sqliteService.protocolRuns.pipe(
        switchMap(repo => repo.update(runId, { status: ExecutionStatus.COMPLETED, end_time: new Date().toISOString() }))
      ).subscribe({
        error: err => console.error('[ExecutionService] Failed to update final run status to COMPLETED in DB:', err)
      });
      this.stopHeartbeat();
    } catch (error) {
      console.error('[Browser Execution Error]', error);
      const current = this._currentRun();
      if (current) {
        this._currentRun.set({
          ...current,
          status: ExecutionStatus.FAILED,
          logs: [...current.logs, `[Error] ${String(error)}`]
        });
      }

      // Update run status in DB
      // SILENT FAILURE FIX: Add error handling
      this.sqliteService.protocolRuns.pipe(
        switchMap(repo => repo.update(runId, { status: ExecutionStatus.FAILED, end_time: new Date().toISOString() }))
      ).subscribe({
        error: err => console.error('[ExecutionService] Failed to update run status to FAILED in DB:', err)
      });
      this.stopHeartbeat();
    }
  }


  /**
   * Helper to update run state
   */
  private updateRunState(updates: Partial<ExecutionState>): void {
    const current = this._currentRun();
    if (current) {
      this._currentRun.set({ ...current, ...updates });
    }
  }

  /**
   * Helper to add a log message
   */
  private addLog(message: string): void {
    const current = this._currentRun();
    if (current) {
      this._currentRun.set({
        ...current,
        logs: [...current.logs, message]
      });
      // Also emit as message for subscribers
      this.messagesSubject.next({
        type: 'log',
        payload: { message },
        timestamp: new Date().toISOString()
      });
    }
  }

  /**
   * Connect to WebSocket for real-time updates
   * ERROR PATH: execution.service.ts:583 -> Max retries reached
   */
  // Error stream for UI feedback
  private _errors = new Subject<Error>();
  errors$ = this._errors.asObservable();

  connectWebSocket(runId: string) {
    if (this.socket$) {
      this.socket$.complete();
      this.socket$ = null;
    }

    this.socket$ = webSocket(`${this.WS_URL}/ws/runs/${runId}`);
    this._isConnected.set(true);

    this.socket$.pipe(
      retry({ delay: 3000, count: 3 }),
      catchError(error => {
        console.error('WebSocket error:', error);
        this._isConnected.set(false);
        this._errors.next(new ExecutionError(
          ExecutionErrorType.WEBSOCKET_ERROR,
          'WebSocket connection failed after retries',
          error
        ));
        return of();
      })
    ).subscribe({
      next: (message) => this.handleMessage(message),
      error: (err) => console.error('WebSocket subscription error:', err)
    });
  }


  /**
   * Handle incoming WebSocket messages
   * ERROR PATH: execution.service.ts:646 -> Backend error message
   */
  private handleMessage(message: ExecutionMessage) {
    this.messagesSubject.next(message);

    const currentState = this._currentRun();
    if (!currentState) return;

    switch (message.type) {
      case 'status':
        this._currentRun.set({
          ...currentState,
          status: message.payload.status,
          currentStep: message.payload.step,
          plr_definition: message.payload.plr_definition
        });
        break;

      case 'log':
        this._currentRun.set({
          ...currentState,
          logs: [...currentState.logs, message.payload.message]
        });
        break;

      case 'progress':
        this._currentRun.set({
          ...currentState,
          progress: message.payload.progress
        });
        break;

      case 'complete':
        this._currentRun.set({
          ...currentState,
          status: ExecutionStatus.COMPLETED,
          progress: 100,
          endTime: message.timestamp
        });
        this.disconnect();
        break;

      case 'error':
        this._currentRun.set({
          ...currentState,
          status: ExecutionStatus.FAILED,
          logs: [...currentState.logs, `ERROR: ${message.payload.error}`]
        });
        this.disconnect();
        break;

      case 'telemetry':
        this._currentRun.set({
          ...currentState,
          telemetry: {
            temperature: message.payload.temperature,
            absorbance: message.payload.absorbance
          }
        });
        break;

      case 'well_state_update':
        // Compressed bitmask format for efficient well/tip state sync
        this._currentRun.set({
          ...currentState,
          wellState: message.payload
        });
        break;
    }
  }

  /**
   * Pause the current run
   */
  pauseRun(): Observable<void> {
    const runId = this._currentRun()?.runId;
    if (!runId) return of(void 0);

    return this.http.post<void>(`${this.API_URL}/api/v1/execution/runs/${runId}/pause`, {});
  }

  /**
   * Resume the current run
   */
  resumeRun(): Observable<void> {
    const runId = this._currentRun()?.runId;
    if (!runId) return of(void 0);

    return this.http.post<void>(`${this.API_URL}/api/v1/execution/runs/${runId}/resume`, {});
  }

  /**
   * Stop the current run
   * ERROR PATH: execution.service.ts:725 -> API cancellation failure
   */
  stopRun(): Observable<unknown> {
    const runId = this._currentRun()?.runId;
    if (!runId) return of(void 0);

    // Browser mode: Use interrupt buffer
    if (runId.startsWith('browser-')) {
      this.pythonRuntime.interrupt();
      const current = this._currentRun();
      if (current) {
        this._currentRun.set({
          ...current,
          status: ExecutionStatus.CANCELLED
        });
      }
      return of(void 0);
    }

    // Production mode: use HTTP API
    return this.apiWrapper.wrap(ProtocolsService.cancelProtocolRunApiV1ProtocolsRunsRunIdCancelPost(runId)).pipe(
      tap(() => {
        const current = this._currentRun();
        if (current) {
          this._currentRun.set({
            ...current,
            status: ExecutionStatus.CANCELLED
          });
        }
        this.disconnect();
      }),
      catchError(err => throwError(() => new ExecutionError(
        ExecutionErrorType.NETWORK_ERROR,
        'Failed to stop protocol run via API',
        err
      )))
    );
  }

  /**
   * Cancel a protocol run
   * ERROR PATH: execution.service.ts:750 -> DB update failure
   * ERROR PATH: execution.service.ts:760 -> API cancellation failure
   */
  cancel(runId: string): Observable<void> {
    if (this.modeService.isBrowserMode()) {
      // Browser mode: stop Python runtime
      this.pythonRuntime.interrupt();

      // Update local state and DB immediately for UI responsiveness
      this.updateRunState({ status: ExecutionStatus.CANCELLED });
      this.stopHeartbeat();

      return this.sqliteService.protocolRuns.pipe(
        switchMap(repo => repo.update(runId, { status: ExecutionStatus.CANCELLED, end_time: new Date().toISOString() })),
        map(() => void 0),
        catchError(err => throwError(() => new ExecutionError(
          ExecutionErrorType.PERSISTENCE_ERROR,
          'Failed to update run status to CANCELLED in local DB',
          err
        )))
      );
    }
    return this.apiWrapper.wrap(ProtocolsService.cancelProtocolRunApiV1ProtocolsRunsRunIdCancelPost(runId))
      .pipe(
        map(() => undefined),
        catchError(err => throwError(() => new ExecutionError(
          ExecutionErrorType.NETWORK_ERROR,
          'Failed to cancel protocol run via API',
          err
        )))
      );
  }

  /**
   * PROPOSED PAUSE/RESUME IMPLEMENTATION PLAN:
   * 
   * 1. Production Mode:
   *    - Once the OpenAPI client is updated, replace raw HttpClient calls in pause() and resume()
   *      with ProtocolsService methods wrapped in apiWrapper.
   *    - The backend handles the state machine transitions (RUNNING <-> PAUSED).
   * 
   * 2. Browser Mode (Pyodide):
   *    - Current implementation only updates UI/DB status, but Python execution continues.
   *    - Real Pause Implementation:
   *      - Utilize the Interrupt Buffer (already used for stop/cancel).
   *      - Python-side: The PLR backend or the bootstrap code should periodically check
   *        a "pause_flag" in a SharedArrayBuffer.
   *      - If pause_flag is set, Python enters a busy-wait loop or uses a blocking read
   *        on an Atomic until the flag is cleared.
   *    - Real Resume Implementation:
   *      - Clear the pause_flag in the SharedArrayBuffer.
   *      - If Python was in a blocking wait, signal it to continue.
   *    - State Management:
   *      - Ensure function_call_logs accurately reflect the pause duration by adjusting
   *        start/end times or adding a 'paused' interval record.
   */
  // TODO(Jules): The pause and resume endpoints are not yet included in the
  // generated OpenAPI client. Using raw HttpClient as a temporary measure.
  // These should be updated to use the ApiWrapperService and generated client
  // once the client is updated.
  /**
   * Pause a protocol run
   * ERROR PATH: execution.service.ts:784 -> DB update failure
   * ERROR PATH: execution.service.ts:792 -> API pause failure
   */
  pause(runId: string): Observable<void> {
    if (this.modeService.isBrowserMode()) {
      // Mock pause in browser mode for UI/E2E consistency
      this.updateRunState({ status: ExecutionStatus.PAUSED });
      return this.sqliteService.protocolRuns.pipe(
        switchMap(repo => repo.update(runId, { status: ExecutionStatus.PAUSED })),
        map(() => void 0),
        catchError(err => throwError(() => new ExecutionError(
          ExecutionErrorType.PERSISTENCE_ERROR,
          'Failed to update run status to PAUSED in local DB',
          err
        )))
      );
    }
    return this.http.post<void>(`${this.API_URL}/api/v1/execution/runs/${runId}/pause`, {}).pipe(
      catchError(err => throwError(() => new ExecutionError(
        ExecutionErrorType.NETWORK_ERROR,
        'Failed to pause protocol run via API',
        err
      )))
    );
  }

  /**
   * Resume a protocol run
   * ERROR PATH: execution.service.ts:812 -> DB update failure
   * ERROR PATH: execution.service.ts:820 -> API resume failure
   */
  resume(runId: string): Observable<void> {
    if (this.modeService.isBrowserMode()) {
      // Mock resume in browser mode
      this.updateRunState({ status: ExecutionStatus.RUNNING });
      return this.sqliteService.protocolRuns.pipe(
        switchMap(repo => repo.update(runId, { status: ExecutionStatus.RUNNING })),
        map(() => void 0),
        catchError(err => throwError(() => new ExecutionError(
          ExecutionErrorType.PERSISTENCE_ERROR,
          'Failed to update run status to RUNNING in local DB',
          err
        )))
      );
    }
    return this.http.post<void>(`${this.API_URL}/api/v1/execution/runs/${runId}/resume`, {}).pipe(
      catchError(err => throwError(() => new ExecutionError(
        ExecutionErrorType.NETWORK_ERROR,
        'Failed to resume protocol run via API',
        err
      )))
    );
  }

  /**
   * Disconnect WebSocket connection
   */
  disconnect() {
    if (this.socket$) {
      this.socket$.complete();
      this.socket$ = null;
    }
    this._isConnected.set(false);
  }

  /**
   * Clear the current run state
   */
  clearRun() {
    this._currentRun.set(null);
    this.lastSavedState = null;
    this.disconnect();
  }

  /**
   * Persist a function call log entry to browser SQLite.
   * ERROR PATH: execution.service.ts:875 -> DB update failure (initial state) (Silent)
   * ERROR PATH: execution.service.ts:919 -> DB create failure (log entry) (Silent)
   */
  private handleFunctionCallLog(runId: string, logData: {
    call_id: string;
    run_id: string;
    sequence: number;
    method_name: string;
    args: Record<string, unknown>;
    state_before: Record<string, unknown> | null;
    state_after: Record<string, unknown> | null;
    status: string;
    start_time: number;
    end_time?: number;
    duration_ms?: number;
    error_message?: string;
  }): void {
    // Only persist completed entries (with state_after) or failures
    if (logData.status !== 'running') {
      // 1. Capture initial state if not already done
      if (!this.lastSavedState && logData.state_before) {
        // SILENT FAILURE FIX: Add error handling
        this.sqliteService.protocolRuns.pipe(
          switchMap(repo => repo.update(runId, { initial_state_json: JSON.stringify(logData.state_before) as any }))
        ).subscribe({
          error: err => console.error('[ExecutionService] Failed to update initial state in DB:', err)
        });
        this.lastSavedState = logData.state_before;
      }

      // 2. Calculate diffs relative to lastSavedState
      let state_before_json: string | null = null;
      if (logData.state_before) {
        const diff = calculateDiff(this.lastSavedState, logData.state_before);
        if (diff) {
          state_before_json = JSON.stringify({ _is_diff: true, diff });
        }
        this.lastSavedState = logData.state_before;
      }

      let state_after_json: string | null = null;
      if (logData.state_after) {
        const diff = calculateDiff(this.lastSavedState, logData.state_after);
        if (diff) {
          state_after_json = JSON.stringify({ _is_diff: true, diff });
        }
        this.lastSavedState = logData.state_after;
      }

      const record = {
        accession_id: logData.call_id,
        protocol_run_accession_id: runId,
        function_protocol_definition_accession_id: 'browser_execution',
        sequence_in_run: logData.sequence,
        name: logData.method_name,
        status: logData.status === 'completed' ? ExecutionStatus.COMPLETED : ExecutionStatus.FAILED,
        start_time: new Date(logData.start_time * 1000).toISOString(),
        end_time: logData.end_time ? new Date(logData.end_time * 1000).toISOString() : null,
        duration_ms: logData.duration_ms ?? null,
        input_args_json: JSON.stringify(logData.args),
        state_before_json,
        state_after_json,
        error_message_text: logData.error_message ?? null,
      };

      // Cast to any because the partial match is looser than strict type checking
      this.sqliteService.functionCallLogs.pipe(
        switchMap(repo => repo.create(record as any))
      ).subscribe({
        error: (err: any) => console.warn('[ExecutionService] Failed to persist function call log:', err)
      });
    }
  }
}
