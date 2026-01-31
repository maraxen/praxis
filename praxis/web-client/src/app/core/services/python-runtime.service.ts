import { Injectable, inject, signal } from '@angular/core';
import { Observable, Subject, from, of } from 'rxjs';
import { ReplOutput, ReplRuntime, CompletionItem, SignatureInfo } from './repl-runtime.interface';
import { HardwareDiscoveryService } from './hardware-discovery.service';
import { InteractionService } from './interaction.service';
import { PyodidePoolService } from './pyodide-pool.service';

interface WorkerResponse {
  type: string;
  id?: string;
  payload?: any;
}

interface RawIOPayload {
  command: 'OPEN' | 'CLOSE' | 'WRITE' | 'READ' | 'READLINE';
  port_id: string;
  data?: number[];
  size?: number;
  timeout?: number;
  request_id?: string;
  baudRate?: number;
}

@Injectable({
  providedIn: 'root'
})
export class PythonRuntimeService implements ReplRuntime {
  private worker: Worker | null = null;
  private responseMap = new Map<string, (value: any) => void>();
  private errorMap = new Map<string, (reason: any) => void>();
  private stdoutSubjects = new Map<string, Subject<ReplOutput>>();

  private hardwareService = inject(HardwareDiscoveryService);
  private interactionService = inject(InteractionService);
  private poolService = inject(PyodidePoolService);

  isReady = signal(false);

  // AUDIT-06: Status signaling for UI recovery
  status = signal<'idle' | 'loading' | 'ready' | 'error'>('idle');
  lastError = signal<string | null>(null);

  constructor() {
    // DEFERRED INIT: Don't load Pyodide until first use
    // This saves ~2-3s on pages that don't need Python execution
    // Worker will be initialized lazily in ensureReady()
  }

  restartWorker() {
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
    }
    this.isReady.set(false);
    this.status.set('idle');
    this.lastError.set(null);
    this.initWorker();
  }

  private async initWorker() {
    if (typeof Worker === 'undefined') {
      console.warn('Web Workers are not supported in this environment.');
      this.status.set('error');
      this.lastError.set('Web Workers not supported');
      return;
    }

    this.status.set('loading');

    try {
      // Try to claim a pre-warmed worker from the pool first
      const warmWorker = await this.poolService.claimWarmWorker();

      if (warmWorker) {
        console.log('[PythonRuntime] Using pre-warmed worker from pool');
        this.worker = warmWorker;
        this.worker.onmessage = ({ data }: { data: WorkerResponse }) => {
          this.handleMessage(data);
        };
        this.worker.onerror = (evt) => {
          console.error('[PythonRuntime] Worker error:', evt);
          this.status.set('error');
          this.lastError.set(evt.message);
        };
        // Worker already initialized, mark as ready
        this.isReady.set(true);
        this.status.set('ready');
        return;
      }

      // No warm worker available, create fresh one
      console.log('[PythonRuntime] No warm worker, creating fresh');
      this.worker = new Worker(new URL('../workers/python.worker', import.meta.url), {
        type: 'module'
      });

      this.worker.onmessage = ({ data }: { data: WorkerResponse }) => {
        this.handleMessage(data);
      };

      // Listen for worker errors (loading/parsing errors)
      this.worker.onerror = (evt) => {
        console.error('[PythonRuntime] Worker error:', evt);
        this.status.set('error');
        this.lastError.set(evt.message);
      };

      await this.sendMessage('INIT');
      this.isReady.set(true);
      this.status.set('ready');
      console.log('[PythonRuntime] Pyodide ready');
    } catch (err: any) {
      console.error('[PythonRuntime] Failed to initialize Pyodide:', err);
      this.status.set('error');
      this.lastError.set(err.message || String(err));
    }
  }

  // ReplRuntime Implementation
  connect(): Observable<void> {
    return this.isReady() ? of(void 0) : from(this.ensureReady());
  }

  disconnect(): void {
    // We don't want to terminate the main worker easily as it's shared,
    // but we could. For now, just a placeholder.
  }

  execute(code: string): Observable<ReplOutput> {
    const id = crypto.randomUUID();
    const subject = new Subject<ReplOutput>();
    this.stdoutSubjects.set(id, subject);

    this.ensureReady().then(() => {
      if (!this.worker) {
        subject.error('Worker not active');
        return;
      }
      this.worker.postMessage({ type: 'EXEC', id, payload: { code } });

      this.responseMap.set(id, (result) => {
        subject.next({ type: 'result', content: result });
        subject.complete();
        this.cleanupMaps(id);
      });

      this.errorMap.set(id, (error) => {
        subject.next({ type: 'error', content: error });
        subject.complete();
        this.cleanupMaps(id);
      });
    });

    return subject.asObservable();
  }

  executeBlob(blob: ArrayBuffer, id?: string, machineConfig?: any, deckSetupScript?: string): Observable<ReplOutput> {
    const runId = id || crypto.randomUUID();
    const subject = new Subject<ReplOutput>();
    this.stdoutSubjects.set(runId, subject);

    this.ensureReady().then(() => {
      if (!this.worker) {
        subject.error('Worker not active');
        return;
      }
      this.worker.postMessage({
        type: 'EXECUTE_BLOB',
        id: runId,
        payload: {
          blob,
          machine_config: machineConfig,
          deck_setup_script: deckSetupScript
        }
      });

      this.responseMap.set(runId, (result) => {
        subject.next({ type: 'result', content: result });
        subject.complete();
        this.cleanupMaps(runId);
      });

      this.errorMap.set(runId, (error) => {
        subject.next({ type: 'error', content: error });
        subject.complete();
        this.cleanupMaps(runId);
      });
    });

    return subject.asObservable();
  }

  interrupt(): void {
    if (this.worker) {
      this.worker.postMessage({ type: 'INTERRUPT' });
    }
  }

  async getCompletions(code: string, _cursor: number): Promise<CompletionItem[]> {
    if (!this.worker) return [];

    const id = crypto.randomUUID();
    const worker = this.worker; // Capture for closure
    return new Promise((resolve) => {
      return new Promise((resolve) => {
        const timeoutId = setTimeout(() => {
          worker?.removeEventListener('message', handler);
          resolve([]);
        }, 5000);

        const handler = ({ data }: MessageEvent) => {
          if (data.id === id && data.type === 'COMPLETE_RESULT') {
            worker?.removeEventListener('message', handler);
            clearTimeout(timeoutId);
            // Matches are now CompletionItem[] from the updated worker
            const matches = data.payload.matches || [];
            resolve(matches);
          }
        };

        worker!.addEventListener('message', handler);
        worker!.postMessage({ type: 'COMPLETE', id, payload: { code } });
      });
    });
  }

  async getSignatures(code: string, _cursor: number): Promise<SignatureInfo[]> {
    if (!this.worker) return [];

    const id = crypto.randomUUID();
    const worker = this.worker;
    return new Promise((resolve) => {
      return new Promise((resolve) => {
        const timeoutId = setTimeout(() => {
          worker?.removeEventListener('message', handler);
          resolve([]);
        }, 5000);

        const handler = ({ data }: MessageEvent) => {
          if (data.id === id && data.type === 'SIGNATURE_RESULT') {
            worker?.removeEventListener('message', handler);
            clearTimeout(timeoutId);
            resolve(data.payload.signatures || []);
          }
        };

        worker!.addEventListener('message', handler);
        worker!.postMessage({ type: 'SIGNATURES', id, payload: { code } });
      });
    });
  }

  // Legacy/Internal methods
  async install(packages: string[]): Promise<void> {
    await this.ensureReady();
    return this.sendMessage('INSTALL', { packages });
  }

  private ensureReady(): Promise<void> {
    // Lazy init: start worker on first use if not already started
    if (!this.worker && this.status() === 'idle') {
      this.initWorker();
    }

    if (this.isReady()) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        clearInterval(interval);
        reject(new Error('Pyodide initialization timeout (30s)'));
      }, 30000);

      const interval = setInterval(() => {
        if (this.isReady()) {
          clearInterval(interval);
          clearTimeout(timeout);
          resolve();
        } else if (this.status() === 'error') {
          clearInterval(interval);
          clearTimeout(timeout);
          reject(new Error(this.lastError() || 'Pyodide initialization failed'));
        }
      }, 100);
    });
  }

  private sendMessage(type: string, payload?: any): Promise<any> {
    if (!this.worker) return Promise.reject('Worker not active');

    const id = crypto.randomUUID();
    return new Promise((resolve, reject) => {
      this.responseMap.set(id, resolve);
      this.errorMap.set(id, reject);

      this.worker!.postMessage({ type, id, payload });
    });
  }

  private handleMessage(data: WorkerResponse) {
    const { type, id, payload } = data;

    if (type === 'STDOUT' && id) {
      this.stdoutSubjects.get(id)?.next({ type: 'stdout', content: payload });
      return;
    }

    if (type === 'STDERR' && id) {
      this.stdoutSubjects.get(id)?.next({ type: 'stderr', content: payload });
      return;
    }

    // Handle WELL_STATE_UPDATE messages from Python - forward as well_state_update
    if (type === 'WELL_STATE_UPDATE' && id && payload) {
      this.stdoutSubjects.get(id)?.next({ type: 'well_state_update', content: JSON.stringify(payload) });
      return;
    }

    // Handle FUNCTION_CALL_LOG messages from Python - forward as function_call_log
    if (type === 'FUNCTION_CALL_LOG' && id && payload) {
      this.stdoutSubjects.get(id)?.next({ type: 'function_call_log', content: JSON.stringify(payload) });
      return;
    }

    // Handle RAW_IO messages from Python - route to HardwareDiscoveryService
    if (type === 'RAW_IO' && payload) {
      this.handleRawIO(payload as RawIOPayload);
      return;
    }

    // Handle USER_INTERACTION messages from Python
    if (type === 'USER_INTERACTION' && payload) {
      console.log('[PythonRuntime] USER_INTERACTION received from worker:', payload);
      this.handleUserInteraction(payload);
      return;
    }

    if (type === 'ERROR' && id) {
      const reject = this.errorMap.get(id);
      if (reject) {
        reject(payload);
      }
      return;
    }

    if (id) {
      const resolve = this.responseMap.get(id);
      if (resolve) {
        resolve(payload);
      }
    }
  }

  /**
   * Handle RAW_IO commands from Python and route to WebSerial via HardwareDiscoveryService
   */
  private async handleRawIO(payload: RawIOPayload) {
    const { command, port_id, data, size, request_id, baudRate } = payload;

    try {
      switch (command) {
        case 'OPEN':
          await this.hardwareService.openPort(port_id, { baudRate: baudRate || 9600 });
          console.log(`[RAW_IO] Opened port ${port_id}`);
          break;

        case 'CLOSE':
          await this.hardwareService.closePort(port_id);
          console.log(`[RAW_IO] Closed port ${port_id}`);
          break;

        case 'WRITE':
          if (data) {
            await this.hardwareService.writeToPort(port_id, new Uint8Array(data));
            console.log(`[RAW_IO] Wrote ${data.length} bytes to ${port_id}`);
          }
          break;

        case 'READ':
          if (size !== undefined && request_id) {
            const result = await this.hardwareService.readFromPort(port_id, size);
            // Send response back to Python worker
            this.worker?.postMessage({
              type: 'RAW_IO_RESPONSE',
              payload: { request_id, data: Array.from(result) }
            });
            console.log(`[RAW_IO] Read ${result.length} bytes from ${port_id}`);
          }
          break;

        case 'READLINE':
          if (request_id) {
            const result = await this.hardwareService.readLineFromPort(port_id);
            this.worker?.postMessage({
              type: 'RAW_IO_RESPONSE',
              payload: { request_id, data: Array.from(result) }
            });
            console.log(`[RAW_IO] Read line from ${port_id}`);
          }
          break;
      }
    } catch (error) {
      console.error(`[RAW_IO] Error handling ${command} on ${port_id}:`, error);
      // Send error response back to Python if there's a request_id
      if (request_id) {
        this.worker?.postMessage({
          type: 'RAW_IO_RESPONSE',
          payload: { request_id, data: [], error: String(error) }
        });
      }
    }
  }

  /**
   * Handle USER_INTERACTION requests from Python and show UI dialogs
   */
  private async handleUserInteraction(payload: any) {
    console.log('[PythonRuntime] Calling InteractionService.handleInteraction for:', payload.interaction_type);
    const result = await this.interactionService.handleInteraction({
      interaction_type: payload.interaction_type,
      payload: payload.payload
    });

    console.log('[PythonRuntime] Interaction result obtained:', result);

    this.worker?.postMessage({
      type: 'USER_INTERACTION_RESPONSE',
      payload: { request_id: payload.id, value: result }
    });
  }

  private cleanupMaps(id: string) {
    this.responseMap.delete(id);
    this.errorMap.delete(id);
    this.stdoutSubjects.delete(id);
  }
}

