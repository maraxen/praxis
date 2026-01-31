import { Injectable, signal } from '@angular/core';

interface WarmWorkerState {
    worker: Worker;
    ready: Promise<void>;
    status: 'warming' | 'ready' | 'claimed';
}

/**
 * PyodidePoolService - Pre-warms Pyodide workers for instant availability
 * 
 * Strategy:
 * - On app init, start warming a worker in background (non-blocking)
 * - When PythonRuntimeService needs a worker, check pool first
 * - After claiming a warm worker, immediately start warming another
 * 
 * This eliminates 15-30s cold start when user navigates to Playground.
 */
@Injectable({
    providedIn: 'root'
})
export class PyodidePoolService {
    private warmWorker: WarmWorkerState | null = null;
    private initPromiseResolver: (() => void) | null = null;

    // Observable status for debugging
    poolStatus = signal<'idle' | 'warming' | 'ready'>('idle');

    /**
     * Called on app bootstrap (non-blocking).
     * Starts warming a Pyodide worker in background.
     */
    preWarm(): void {
        if (this.warmWorker) {
            return; // Already warming or ready
        }
        this.startWarming();
    }

    /**
     * Get a pre-warmed worker if available, otherwise returns null.
     * Caller should fall back to creating fresh worker if null.
     */
    async claimWarmWorker(): Promise<Worker | null> {
        if (!this.warmWorker) {
            return null;
        }

        const state = this.warmWorker;

        // Wait for worker to be ready
        try {
            await state.ready;
        } catch (err) {
            console.error('[PyodidePool] Warm worker failed during init:', err);
            this.warmWorker = null;
            this.poolStatus.set('idle');
            return null;
        }

        if (state.status !== 'ready') {
            return null;
        }

        // Claim the worker
        state.status = 'claimed';
        const worker = state.worker;
        this.warmWorker = null;

        // Start warming the next one
        this.startWarming();

        console.log('[PyodidePool] Worker claimed, starting next warm cycle');
        return worker;
    }

    /**
     * Check if a warm worker is available immediately.
     */
    hasWarmWorker(): boolean {
        return this.warmWorker?.status === 'ready';
    }

    private startWarming(): void {
        this.poolStatus.set('warming');
        console.log('[PyodidePool] Starting warm cycle...');

        const worker = new Worker(
            new URL('../workers/python.worker', import.meta.url),
            { type: 'module' }
        );

        const ready = new Promise<void>((resolve, reject) => {
            this.initPromiseResolver = resolve;

            const timeout = setTimeout(() => {
                console.error('[PyodidePool] Warm worker init timeout (60s)');
                this.warmWorker = null;
                this.poolStatus.set('idle');
                reject(new Error('Warm worker init timeout'));
            }, 60000);

            worker.onmessage = ({ data }) => {
                if (data.type === 'INIT_COMPLETE') {
                    clearTimeout(timeout);
                    if (this.warmWorker) {
                        this.warmWorker.status = 'ready';
                    }
                    this.poolStatus.set('ready');
                    console.log('[PyodidePool] Warm worker ready');
                    resolve();
                }
            };

            worker.onerror = (err) => {
                clearTimeout(timeout);
                console.error('[PyodidePool] Warm worker error:', err);
                this.warmWorker = null;
                this.poolStatus.set('idle');
                reject(err);
            };
        });

        this.warmWorker = {
            worker,
            ready,
            status: 'warming'
        };

        // Send INIT message to start Pyodide loading
        worker.postMessage({ type: 'INIT', id: 'pool-init' });
    }

    /**
     * Terminate any warm worker (for cleanup).
     */
    dispose(): void {
        if (this.warmWorker) {
            this.warmWorker.worker.terminate();
            this.warmWorker = null;
            this.poolStatus.set('idle');
        }
    }
}
