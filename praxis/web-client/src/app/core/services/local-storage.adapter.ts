import { Injectable, signal } from '@angular/core';
import { Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { toObservable } from '@angular/core/rxjs-interop';

/**
 * Storage key prefixes for different entity types
 */
const STORAGE_KEYS = {
    PROTOCOLS: 'praxis_protocols',
    PROTOCOL_RUNS: 'praxis_protocol_runs',
    RESOURCES: 'praxis_resources',
    MACHINES: 'praxis_machines',
    STATE_VERSION: 'praxis_state_version'
} as const;

const CURRENT_STATE_VERSION = 1;

/**
 * LocalStorage persistence adapter for browser mode.
 * 
 * Provides a lightweight alternative to SqliteService for pure browser deployments.
 * Data persists across page refreshes using browser LocalStorage.
 * 
 * Key features:
 * - CRUD operations for protocols, runs, resources, machines
 * - State export/import (JSON) for session management
 * - Observable-based API compatible with existing services
 */
@Injectable({ providedIn: 'root' })
export class LocalStorageAdapter {
    // Change signals to notify subscribers of updates (increment to trigger)
    private readonly protocolsVersion = signal(0);
    private readonly runsVersion = signal(0);
    private readonly resourcesVersion = signal(0);
    private readonly machinesVersion = signal(0);

    // Observable triggers for RxJS interop
    private readonly protocolsChanged$ = toObservable(this.protocolsVersion);
    private readonly runsChanged$ = toObservable(this.runsVersion);
    private readonly resourcesChanged$ = toObservable(this.resourcesVersion);
    private readonly machinesChanged$ = toObservable(this.machinesVersion);

    constructor() {
        this.initializeIfNeeded();
    }

    /**
     * Initialize storage with empty arrays if not present
     */
    private initializeIfNeeded(): void {
        const version = localStorage.getItem(STORAGE_KEYS.STATE_VERSION);

        if (!version) {
            // First time - initialize empty state
            localStorage.setItem(STORAGE_KEYS.STATE_VERSION, String(CURRENT_STATE_VERSION));
            this.setItems(STORAGE_KEYS.PROTOCOLS, []);
            this.setItems(STORAGE_KEYS.PROTOCOL_RUNS, []);
            this.setItems(STORAGE_KEYS.RESOURCES, []);
            this.setItems(STORAGE_KEYS.MACHINES, []);
            console.log('[LocalStorageAdapter] Initialized empty state');
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Generic CRUD helpers
    // ─────────────────────────────────────────────────────────────────────────

    private getItems<T>(key: string): T[] {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            console.error(`[LocalStorageAdapter] Failed to parse ${key}:`, e);
            return [];
        }
    }

    private setItems<T>(key: string, items: T[]): void {
        try {
            localStorage.setItem(key, JSON.stringify(items));
        } catch (e) {
            console.error(`[LocalStorageAdapter] Failed to save ${key}:`, e);
            // Handle quota exceeded
            if (e instanceof DOMException && e.name === 'QuotaExceededError') {
                console.error('[LocalStorageAdapter] Storage quota exceeded!');
            }
        }
    }

    private findById<T extends { accession_id: string }>(key: string, id: string): T | undefined {
        return this.getItems<T>(key).find(item => item.accession_id === id);
    }

    private addItem<T extends { accession_id: string }>(key: string, item: T): T {
        const items = this.getItems<T>(key);
        // Replace if exists, otherwise add
        const existingIndex = items.findIndex(i => i.accession_id === item.accession_id);
        if (existingIndex >= 0) {
            items[existingIndex] = item;
        } else {
            items.push(item);
        }
        this.setItems(key, items);
        return item;
    }

    private updateItem<T extends { accession_id: string }>(key: string, id: string, updates: Partial<T>): T | null {
        const items = this.getItems<T>(key);
        const index = items.findIndex(i => i.accession_id === id);
        if (index < 0) return null;

        items[index] = { ...items[index], ...updates };
        this.setItems(key, items);
        return items[index];
    }

    private deleteItem<T extends { accession_id: string }>(key: string, id: string): boolean {
        const items = this.getItems<T>(key);
        const filtered = items.filter(i => i.accession_id !== id);
        if (filtered.length === items.length) return false;

        this.setItems(key, filtered);
        return true;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Protocols
    // ─────────────────────────────────────────────────────────────────────────

    getProtocols(): Observable<any[]> {
        return this.protocolsChanged$.pipe(
            map(() => this.getItems(STORAGE_KEYS.PROTOCOLS))
        );
    }

    getProtocol(id: string): Observable<any | null> {
        return of(this.findById(STORAGE_KEYS.PROTOCOLS, id) || null);
    }

    createProtocol(protocol: any): Observable<any> {
        const created = this.addItem(STORAGE_KEYS.PROTOCOLS, {
            ...protocol,
            accession_id: protocol.accession_id || crypto.randomUUID()
        });
        this.protocolsVersion.update(v => v + 1);
        return of(created);
    }

    updateProtocol(id: string, updates: any): Observable<any | null> {
        const updated = this.updateItem(STORAGE_KEYS.PROTOCOLS, id, updates);
        if (updated) this.protocolsVersion.update(v => v + 1);
        return of(updated);
    }

    deleteProtocol(id: string): Observable<boolean> {
        const deleted = this.deleteItem(STORAGE_KEYS.PROTOCOLS, id);
        if (deleted) this.protocolsVersion.update(v => v + 1);
        return of(deleted);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Protocol Runs
    // ─────────────────────────────────────────────────────────────────────────

    getProtocolRuns(): Observable<any[]> {
        return this.runsChanged$.pipe(
            map(() => this.getItems(STORAGE_KEYS.PROTOCOL_RUNS))
        );
    }

    getProtocolRun(id: string): Observable<any | null> {
        return of(this.findById(STORAGE_KEYS.PROTOCOL_RUNS, id) || null);
    }

    createProtocolRun(run: any): Observable<any> {
        const created = this.addItem(STORAGE_KEYS.PROTOCOL_RUNS, {
            ...run,
            accession_id: run.accession_id || crypto.randomUUID(),
            created_at: run.created_at || new Date().toISOString(),
            status: run.status || 'QUEUED'
        });
        this.runsVersion.update(v => v + 1);
        return of(created);
    }

    updateProtocolRun(id: string, updates: any): Observable<any | null> {
        const updated = this.updateItem(STORAGE_KEYS.PROTOCOL_RUNS, id, updates);
        if (updated) this.runsVersion.update(v => v + 1);
        return of(updated);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Resources
    // ─────────────────────────────────────────────────────────────────────────

    getResources(): Observable<any[]> {
        return this.resourcesChanged$.pipe(
            map(() => this.getItems(STORAGE_KEYS.RESOURCES))
        );
    }

    getResource(id: string): Observable<any | null> {
        return of(this.findById(STORAGE_KEYS.RESOURCES, id) || null);
    }

    createResource(resource: any): Observable<any> {
        const created = this.addItem(STORAGE_KEYS.RESOURCES, {
            ...resource,
            accession_id: resource.accession_id || crypto.randomUUID()
        });
        this.resourcesVersion.update(v => v + 1);
        return of(created);
    }

    updateResource(id: string, updates: any): Observable<any | null> {
        const updated = this.updateItem(STORAGE_KEYS.RESOURCES, id, updates);
        if (updated) this.resourcesVersion.update(v => v + 1);
        return of(updated);
    }

    deleteResource(id: string): Observable<boolean> {
        const deleted = this.deleteItem(STORAGE_KEYS.RESOURCES, id);
        if (deleted) this.resourcesVersion.update(v => v + 1);
        return of(deleted);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Machines
    // ─────────────────────────────────────────────────────────────────────────

    getMachines(): Observable<any[]> {
        return this.machinesChanged$.pipe(
            map(() => this.getItems(STORAGE_KEYS.MACHINES))
        );
    }

    getMachine(id: string): Observable<any | null> {
        return of(this.findById(STORAGE_KEYS.MACHINES, id) || null);
    }

    createMachine(machine: any): Observable<any> {
        const created = this.addItem(STORAGE_KEYS.MACHINES, {
            ...machine,
            accession_id: machine.accession_id || crypto.randomUUID()
        });
        this.machinesVersion.update(v => v + 1);
        return of(created);
    }

    updateMachine(id: string, updates: any): Observable<any | null> {
        const updated = this.updateItem(STORAGE_KEYS.MACHINES, id, updates);
        if (updated) this.machinesVersion.update(v => v + 1);
        return of(updated);
    }

    deleteMachine(id: string): Observable<boolean> {
        const deleted = this.deleteItem(STORAGE_KEYS.MACHINES, id);
        if (deleted) this.machinesVersion.update(v => v + 1);
        return of(deleted);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // State Export/Import
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Export entire state as JSON string for download/backup
     */
    exportState(): string {
        const state = {
            version: CURRENT_STATE_VERSION,
            exportedAt: new Date().toISOString(),
            protocols: this.getItems(STORAGE_KEYS.PROTOCOLS),
            protocolRuns: this.getItems(STORAGE_KEYS.PROTOCOL_RUNS),
            resources: this.getItems(STORAGE_KEYS.RESOURCES),
            machines: this.getItems(STORAGE_KEYS.MACHINES)
        };
        return JSON.stringify(state, null, 2);
    }

    /**
     * Import state from JSON string (e.g., from file upload)
     * @param json JSON string from exportState()
     * @param merge If true, merge with existing data; if false, replace entirely
     */
    importState(json: string, merge = false): boolean {
        try {
            const state = JSON.parse(json);

            if (!state.version) {
                console.error('[LocalStorageAdapter] Invalid state file: missing version');
                return false;
            }

            if (merge) {
                // Merge: add new items, skip existing
                const existing = {
                    protocols: this.getItems<any>(STORAGE_KEYS.PROTOCOLS),
                    runs: this.getItems<any>(STORAGE_KEYS.PROTOCOL_RUNS),
                    resources: this.getItems<any>(STORAGE_KEYS.RESOURCES),
                    machines: this.getItems<any>(STORAGE_KEYS.MACHINES)
                };

                (state.protocols || []).forEach((p: any) => {
                    if (!existing.protocols.find((e: any) => e.accession_id === p.accession_id)) {
                        this.addItem(STORAGE_KEYS.PROTOCOLS, p);
                    }
                });
                (state.protocolRuns || []).forEach((r: any) => {
                    if (!existing.runs.find((e: any) => e.accession_id === r.accession_id)) {
                        this.addItem(STORAGE_KEYS.PROTOCOL_RUNS, r);
                    }
                });
                (state.resources || []).forEach((r: any) => {
                    if (!existing.resources.find((e: any) => e.accession_id === r.accession_id)) {
                        this.addItem(STORAGE_KEYS.RESOURCES, r);
                    }
                });
                (state.machines || []).forEach((m: any) => {
                    if (!existing.machines.find((e: any) => e.accession_id === m.accession_id)) {
                        this.addItem(STORAGE_KEYS.MACHINES, m);
                    }
                });
            } else {
                // Replace entirely
                this.setItems(STORAGE_KEYS.PROTOCOLS, state.protocols || []);
                this.setItems(STORAGE_KEYS.PROTOCOL_RUNS, state.protocolRuns || []);
                this.setItems(STORAGE_KEYS.RESOURCES, state.resources || []);
                this.setItems(STORAGE_KEYS.MACHINES, state.machines || []);
            }

            // Notify all subscribers
            this.protocolsVersion.update(v => v + 1);
            this.runsVersion.update(v => v + 1);
            this.resourcesVersion.update(v => v + 1);
            this.machinesVersion.update(v => v + 1);

            console.log(`[LocalStorageAdapter] State imported (${merge ? 'merged' : 'replaced'})`);
            return true;
        } catch (e) {
            console.error('[LocalStorageAdapter] Failed to import state:', e);
            return false;
        }
    }

    /**
     * Clear all stored data
     */
    clearAll(): void {
        localStorage.removeItem(STORAGE_KEYS.PROTOCOLS);
        localStorage.removeItem(STORAGE_KEYS.PROTOCOL_RUNS);
        localStorage.removeItem(STORAGE_KEYS.RESOURCES);
        localStorage.removeItem(STORAGE_KEYS.MACHINES);
        localStorage.removeItem(STORAGE_KEYS.STATE_VERSION);

        this.initializeIfNeeded();

        this.protocolsVersion.update(v => v + 1);
        this.runsVersion.update(v => v + 1);
        this.resourcesVersion.update(v => v + 1);
        this.machinesVersion.update(v => v + 1);

        console.log('[LocalStorageAdapter] All data cleared');
    }

    /**
     * Get storage usage statistics
     */
    getStorageStats(): { used: number; quota: number; percentage: number } {
        let used = 0;
        for (const key of Object.values(STORAGE_KEYS)) {
            const item = localStorage.getItem(key);
            if (item) used += item.length * 2; // UTF-16 = 2 bytes per char
        }

        // Most browsers allow ~5MB for localStorage
        const quota = 5 * 1024 * 1024;
        return {
            used,
            quota,
            percentage: Math.round((used / quota) * 100)
        };
    }
}
