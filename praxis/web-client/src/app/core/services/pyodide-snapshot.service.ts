// src/app/core/services/pyodide-snapshot.service.ts
import { Injectable } from '@angular/core';

const SNAPSHOT_DB = 'praxis-pyodide-snapshots';
const SNAPSHOT_STORE = 'snapshots';
const DEFAULT_KEY = 'pyodide-initialized';

/**
 * Manages Pyodide snapshots in IndexedDB for fast restarts.
 * 
 * Supports multiple snapshot keys for different runtime contexts:
 * - 'pyodide-jupyterlite' - JupyterLite/Playground snapshots
 * - 'pyodide-worker' - Protocol execution worker snapshots
 */
@Injectable({ providedIn: 'root' })
export class PyodideSnapshotService {
    private dbPromise: Promise<IDBDatabase> | null = null;

    private async getDb(): Promise<IDBDatabase> {
        if (!this.dbPromise) {
            this.dbPromise = new Promise((resolve, reject) => {
                const request = indexedDB.open(SNAPSHOT_DB, 1);
                request.onerror = () => reject(request.error);
                request.onsuccess = () => resolve(request.result);
                request.onupgradeneeded = () => {
                    request.result.createObjectStore(SNAPSHOT_STORE);
                };
            });
        }
        return this.dbPromise;
    }

    async hasSnapshot(key: string = DEFAULT_KEY): Promise<boolean> {
        try {
            const db = await this.getDb();
            return new Promise((resolve) => {
                const tx = db.transaction(SNAPSHOT_STORE, 'readonly');
                const store = tx.objectStore(SNAPSHOT_STORE);
                const request = store.get(key);
                request.onsuccess = () => resolve(!!request.result);
                request.onerror = () => resolve(false);
            });
        } catch {
            return false;
        }
    }

    async getSnapshot(key: string = DEFAULT_KEY): Promise<Uint8Array | null> {
        try {
            const isValid = await this.validateOrInvalidate(key);
            if (!isValid) {
                return null;
            }

            const db = await this.getDb();
            return new Promise((resolve) => {
                const tx = db.transaction(SNAPSHOT_STORE, 'readonly');
                const store = tx.objectStore(SNAPSHOT_STORE);
                const request = store.get(key);
                request.onsuccess = () => resolve(request.result?.data ?? null);
                request.onerror = () => resolve(null);
            });
        } catch {
            return null;
        }
    }

    async saveSnapshot(data: Uint8Array, key: string = DEFAULT_KEY): Promise<void> {
        const db = await this.getDb();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(SNAPSHOT_STORE, 'readwrite');
            const store = tx.objectStore(SNAPSHOT_STORE);
            const request = store.put({
                data,
                version: this.getSnapshotVersion(),
                createdAt: Date.now()
            }, key);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async invalidateSnapshot(key: string = DEFAULT_KEY): Promise<void> {
        try {
            const db = await this.getDb();
            return new Promise((resolve) => {
                const tx = db.transaction(SNAPSHOT_STORE, 'readwrite');
                const store = tx.objectStore(SNAPSHOT_STORE);
                store.delete(key);
                tx.oncomplete = () => resolve();
            });
        } catch {
            // Ignore errors during invalidation
        }
    }

    getSnapshotVersion(): string {
        // Version based on app version + shim hashes
        // Invalidate when shims or Pyodide version changes
        // TODO: This should be a dynamic value, but the necessary build-time information is not available.
        // For now, we'll use a hardcoded value and rely on manual cache clearing for updates.
        return 'v1.0.0';
    }

    async validateOrInvalidate(key: string = DEFAULT_KEY): Promise<boolean> {
        const currentVersion = this.getSnapshotVersion();
        try {
            const db = await this.getDb();
            const storedVersion = await new Promise<string | null>((resolve) => {
                const tx = db.transaction(SNAPSHOT_STORE, 'readonly');
                const store = tx.objectStore(SNAPSHOT_STORE);
                const request = store.get(key);
                request.onsuccess = () => resolve(request.result?.version ?? null);
                request.onerror = () => resolve(null);
            });

            if (storedVersion !== currentVersion) {
                console.log(`[Pyodide] Snapshot version mismatch for '${key}'. Stored: ${storedVersion}, Current: ${currentVersion}. Invalidating.`);
                await this.invalidateSnapshot(key);
                return false;
            }

            return true;
        } catch {
            return false;
        }
    }
}
