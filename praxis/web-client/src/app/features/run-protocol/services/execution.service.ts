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
import { ExecutionMessage, ExecutionState, ExecutionStatus } from '../models/execution.models';
import { MachineCompatibility } from '../models/machine-compatibility.models';
import { ProtocolsService } from '@api/services/ProtocolsService';
import { calculateDiff } from '@core/utils/state-diff';
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
      ).subscribe();
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
   */
  fetchProtocolBlob(id: string): Observable<ArrayBuffer> {
    if (this.modeService.isBrowserMode()) {
      // Fetch from static assets in browser/offline mode
      // Use relative path (no leading slash) to respect base href on GitHub Pages
      return this.http.get(`assets/protocols/${id}.pkl`, {
        responseType: 'arraybuffer'
      });
    }
    // Default: Fetch from backend API
    return this.http.get(`${this.API_URL}/api/v1/protocols/definitions/${id}/code/binary`, {
      responseType: 'arraybuffer'
    });
  }

  /**
   * Check protocol compatibility with available machines
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
        } as MachineCompatibility)))
      );
    }
    return this.apiWrapper.wrap(ProtocolsService.getProtocolCompatibilityApiV1ProtocolsAccessionIdCompatibilityGet(protocolId)) as Observable<MachineCompatibility[]>;
  }

  /**
   * Start a new protocol run
   */
  startRun(
    protocolId: string,
    runName: string,
    parameters?: Record<string, unknown>,
    simulationMode: boolean = true,
    _notes?: string
  ): Observable<{ run_id: string }> {
    // AUDIT-01: Defense-in-depth validation
    if (!simulationMode && parameters) {
      const hasSimulatedConfig = Object.values(parameters).some((val: any) =>
        val && typeof val === 'object' && val.is_simulated === true
      );

      if (hasSimulatedConfig) {
        return throwError(() => new Error('Cannot start physical run with simulated machine configuration'));
      }
    }

    // Browser mode: execute via Pyodide
    if (this.modeService.isBrowserMode()) {
      return this.startBrowserRun(protocolId, runName, parameters, _notes);
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
      })
    );
  }

  /**
   * Execute protocol in browser mode using Pyodide
   */
  private startBrowserRun(
    protocolId: string,
    runName: string,
    parameters?: Record<string, unknown>,
    notes?: string
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
      status: 'queued',
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

    this.sqliteService.protocolRuns.pipe(
      switchMap(repo => repo.create(runRecord as any))
    ).subscribe({
      error: (err) => console.warn('[ExecutionService] Failed to persist run:', err)
    });

    // Execute asynchronously
    this.executeBrowserProtocol(protocolId, runId, parameters);

    // Start heartbeat
    this.startHeartbeat(runId);

    return of({ run_id: runId });
  }

  /**
   * Execute protocol code in Pyodide worker
   */
  private async executeBrowserProtocol(
    protocolId: string,
    runId: string,
    parameters?: Record<string, unknown>
  ): Promise<void> {
    try {
      // Update status to running
      this.updateRunState({ status: ExecutionStatus.RUNNING });
      this.addLog('[Browser Mode] Loading protocol...');

      // 1. Retrieve the ProtocolRun record to get resolved assets
      const run = await firstValueFrom(this.sqliteService.getProtocolRun(runId));

      // 2. Extract machine config if assets are resolved
      let machineConfig: any = null;
      if (run?.resolved_assets_json) {
        try {
          const resolvedAssets = typeof run.resolved_assets_json === 'string'
            ? JSON.parse(run.resolved_assets_json)
            : run.resolved_assets_json;

          // Find machine asset (look for machine_instance or definition)
          const assets = Array.isArray(resolvedAssets) ? resolvedAssets : Object.values(resolvedAssets);
          const machineAsset = assets.find((a: any) => a.machine_instance || a.definition);

          if (machineAsset) {
            const instance = machineAsset.machine_instance;
            const definition = machineAsset.definition;

            machineConfig = {
              backend_fqn: definition.fqn,
              port_id: instance?.backend_config?.port_id,
              baudrate: instance?.backend_config?.baudrate,
              is_simulated: definition.is_simulation_override || false
            };
            this.addLog(`[Browser Mode] Using machine: ${definition.name} (${definition.fqn})`);
          }
        } catch (e) {
          console.warn('[ExecutionService] Failed to parse resolved_assets_json:', e);
        }
      }

      // Fetch protocol blob
      const blob = await firstValueFrom(this.fetchProtocolBlob(protocolId));

      // NEW: Get serialized deck setup from WizardStateService
      const { script: deckSetupScript, warnings } = this.wizardState.serializeToPython();

      if (warnings.length > 0) {
        this.snackBar.open(`Deck Serialization Warnings:\n- ${warnings.join('\n- ')}`, 'Close', {
          duration: 10000, // 10 seconds
          panelClass: ['warning-snackbar']
        });
        this.addLog(`[Deck Setup] Warnings: ${warnings.join(', ')}`);
      }

      this.addLog(`[Browser Mode] Executing protocol binary`);
      this.updateRunState({ progress: 20, currentStep: 'Running protocol' });

      await new Promise<void>((resolve, reject) => {
        let hasError = false;

        this.pythonRuntime.executeBlob(blob, runId, machineConfig, deckSetupScript).subscribe({
          next: (output) => {
            if (output.type === 'stdout') {
              this.addLog(output.content);
            } else if (output.type === 'stderr') {
              this.addLog(`[Error] ${output.content}`);
              hasError = true;
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

      // Success
      this.updateRunState({
        status: ExecutionStatus.COMPLETED,
        progress: 100,
        endTime: new Date().toISOString()
      });
      this.addLog('[Browser Mode] Execution completed successfully.');

      // Update run status in DB
      this.sqliteService.protocolRuns.pipe(
        switchMap(repo => repo.update(runId, { status: 'completed', end_time: new Date().toISOString() }))
      ).subscribe();
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
      this.sqliteService.protocolRuns.pipe(
        switchMap(repo => repo.update(runId, { status: 'failed', end_time: new Date().toISOString() }))
      ).subscribe();
      this.stopHeartbeat();
    }
  }

  /**
   * Build Python code to execute a protocol
   */
  private buildProtocolExecutionCode(
    protocol: any, // ProtocolDefinition
    parameters?: Record<string, unknown>,
    assetSpecs?: Record<string, any>,
    runId?: string
  ): string {
    const moduleName = protocol.module_name || protocol.fqn.split('.').slice(0, -1).join('.');
    const functionName = protocol.function_name || protocol.fqn.split('.').pop() || 'run';

    // Serialize parameters and metadata for Python
    const paramsStr = parameters ? JSON.stringify(parameters) : '{}';
    const assetSpecsStr = assetSpecs ? JSON.stringify(assetSpecs) : '{}';

    // Extract parameter metadata (name -> type_hint)
    const metadata: Record<string, string> = {};
    if (protocol.parameters) {
      protocol.parameters.forEach((p: any) => {
        metadata[p.name] = p.type_hint;
      });
    }

    // Extract asset requirements (accession_id -> type_hint)
    const assetRequirements: Record<string, string> = {};
    if (protocol.assets) {
      protocol.assets.forEach((a: any) => {
        assetRequirements[a.accession_id] = a.type_hint_str;
      });
    }

    const metadataStr = JSON.stringify(metadata);
    const assetReqsStr = JSON.stringify(assetRequirements);

    return `
# Browser mode protocol execution
import json
import time
from web_bridge import resolve_parameters, patch_state_emission, patch_function_call_logging

print("[Browser] Setting up simulation environment...")

# Import the protocol module
try:
    from ${moduleName} import ${functionName}
except ImportError as e:
    print(f"[Browser] Protocol import not available in browser: {e}")
    print("[Browser] Running simulation placeholder instead...")

    # Simulation placeholder
    def ${functionName}(*args, **kwargs):
        print("[Simulation] Protocol started")
        return {"status": "simulated"}

# Parse parameters and metadata
params = json.loads('''${paramsStr}''')
metadata = json.loads('''${metadataStr}''')
asset_reqs = json.loads('''${assetReqsStr}''')
asset_specs = json.loads('''${assetSpecsStr}''')

# Resolve parameters (instantiate PLR objects for plates/etc)
print("[Browser] Resolving parameters...")
resolved_params = resolve_parameters(params, metadata, asset_reqs, asset_specs)

# Patch for real-time state emission (searching for LiquidHandler in resolved_params)
for p_value in resolved_params.values():
    try:
        from pylabrobot.liquid_handling import LiquidHandler
        if isinstance(p_value, LiquidHandler):
            patch_state_emission(p_value)
            patch_function_call_logging(p_value, '${runId}')
    except ImportError:
        pass

# Execute the protocol
print("[Browser] Executing protocol...")
result = ${functionName}(**resolved_params) if resolved_params else ${functionName}()
print(f"[Browser] Protocol finished with result: {result}")
`;
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
        this._errors.next(error);
        return of();
      })
    ).subscribe({
      next: (message) => this.handleMessage(message),
      error: (err) => console.error('WebSocket subscription error:', err)
    });
  }


  /**
   * Handle incoming WebSocket messages
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
      })
    );
  }

  cancel(runId: string): Observable<void> {
    if (this.modeService.isBrowserMode()) {
      // Browser mode: stop Python runtime
      this.pythonRuntime.interrupt();
      return of(undefined);
    }
    return this.apiWrapper.wrap(ProtocolsService.cancelProtocolRunApiV1ProtocolsRunsRunIdCancelPost(runId))
      .pipe(map(() => undefined));
  }

  // TODO(Jules): The pause and resume endpoints are not yet included in the
  // generated OpenAPI client. Using raw HttpClient as a temporary measure.
  // These should be updated to use the ApiWrapperService and generated client
  // once the client is updated.
  pause(runId: string): Observable<void> {
    if (this.modeService.isBrowserMode()) {
      return of(undefined).pipe(tap(() => console.warn('Pause is not supported in browser mode.')));
    }
    return this.http.post<void>(`${this.API_URL}/api/v1/execution/runs/${runId}/pause`, {});
  }

  resume(runId: string): Observable<void> {
    if (this.modeService.isBrowserMode()) {
      return of(undefined).pipe(tap(() => console.warn('Resume is not supported in browser mode.')));
    }
    return this.http.post<void>(`${this.API_URL}/api/v1/execution/runs/${runId}/resume`, {});
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
        this.sqliteService.protocolRuns.pipe(
          switchMap(repo => repo.update(runId, { initial_state_json: JSON.stringify(logData.state_before) as any }))
        ).subscribe();
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
        status: logData.status === 'completed' ? 'COMPLETED' : 'FAILED',
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
