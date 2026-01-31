# Pyodide Snapshot/Restore Optimization (P2)

> **Stream**: 3 - Performance  
> **Effort**: L (4-6 hours)  
> **Priority**: P2  
> **Approach**: TDD - Write tests first, then implement

---

## Objective

Dramatically reduce Pyodide bootstrap time from ~30s to <5s by pre-computing and caching an initialized environment snapshot. This enables:
1. Near-instant Pyodide startup for returning users
2. Faster E2E tests (mock or snapshot restore)
3. Better user experience in Playground

---

## Context Files (Read First)

1. `src/app/features/playground/services/playground-jupyterlite.service.ts` → Bootstrap logic
2. `src/assets/jupyterlite/config-utils.js` → JupyterLite config loading
3. `src/assets/python/web_serial_shim.py` → Python shims loaded at bootstrap
4. Knowledge item: "Praxis Web-Client Technical Reference" → Pyodide optimization section

---

## Background Research

### Pyodide Snapshot API
Pyodide supports serialization of interpreter state via `pyodide.dumpSnapshot()` and `pyodide.loadSnapshot()`:

```javascript
// Create snapshot after initialization
const snapshot = await pyodide.dumpSnapshot();
await indexedDB.put('pyodide-snapshot', snapshot);

// Restore from snapshot (much faster than fresh init)
const snapshot = await indexedDB.get('pyodide-snapshot');
await pyodide.loadSnapshot(snapshot);
```

### Current Bootstrap Sequence
1. Download Pyodide WASM (~8MB) → 5-10s
2. Initialize interpreter → 5-10s  
3. Load micropip → 3-5s
4. Load shims (web_serial, web_usb, web_ftdi) → 2-3s
5. Setup BroadcastChannel → <1s

**Total**: 15-30s depending on network/cache

### Optimized Sequence (with snapshot)
1. Check for cached snapshot → <100ms
2. If exists: Load snapshot → 1-3s
3. If not: Full bootstrap → 15-30s, then create snapshot

---

## TDD Approach

### Step 1: Write Unit Tests First

Create `src/app/features/playground/services/pyodide-snapshot.service.spec.ts`:

```typescript
import { TestBed } from '@angular/core/testing';
import { PyodideSnapshotService } from './pyodide-snapshot.service';

describe('PyodideSnapshotService', () => {
    let service: PyodideSnapshotService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [PyodideSnapshotService]
        });
        service = TestBed.inject(PyodideSnapshotService);
    });

    describe('hasSnapshot', () => {
        it('returns false when no snapshot exists', async () => {
            const result = await service.hasSnapshot();
            expect(result).toBe(false);
        });

        it('returns true after snapshot is saved', async () => {
            await service.saveSnapshot(new Uint8Array([1, 2, 3]));
            const result = await service.hasSnapshot();
            expect(result).toBe(true);
        });
    });

    describe('getSnapshot', () => {
        it('returns null when no snapshot exists', async () => {
            const result = await service.getSnapshot();
            expect(result).toBeNull();
        });

        it('returns saved snapshot data', async () => {
            const data = new Uint8Array([1, 2, 3]);
            await service.saveSnapshot(data);
            const result = await service.getSnapshot();
            expect(result).toEqual(data);
        });
    });

    describe('invalidateSnapshot', () => {
        it('removes existing snapshot', async () => {
            await service.saveSnapshot(new Uint8Array([1, 2, 3]));
            await service.invalidateSnapshot();
            const result = await service.hasSnapshot();
            expect(result).toBe(false);
        });
    });

    describe('getSnapshotVersion', () => {
        it('returns version string for cache busting', async () => {
            const version = service.getSnapshotVersion();
            expect(typeof version).toBe('string');
            expect(version.length).toBeGreaterThan(0);
        });
    });
});
```

### Step 2: Run Tests (Should Fail)

```bash
npm run test -- --include="**/pyodide-snapshot.service.spec.ts"
```

---

## Implementation Steps

### 1. Create Snapshot Service

```typescript
// src/app/features/playground/services/pyodide-snapshot.service.ts
import { Injectable } from '@angular/core';

const SNAPSHOT_DB = 'praxis-pyodide-snapshots';
const SNAPSHOT_STORE = 'snapshots';
const SNAPSHOT_KEY = 'pyodide-initialized';

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

    async hasSnapshot(): Promise<boolean> {
        try {
            const db = await this.getDb();
            return new Promise((resolve) => {
                const tx = db.transaction(SNAPSHOT_STORE, 'readonly');
                const store = tx.objectStore(SNAPSHOT_STORE);
                const request = store.get(SNAPSHOT_KEY);
                request.onsuccess = () => resolve(!!request.result);
                request.onerror = () => resolve(false);
            });
        } catch {
            return false;
        }
    }

    async getSnapshot(): Promise<Uint8Array | null> {
        try {
            const db = await this.getDb();
            return new Promise((resolve) => {
                const tx = db.transaction(SNAPSHOT_STORE, 'readonly');
                const store = tx.objectStore(SNAPSHOT_STORE);
                const request = store.get(SNAPSHOT_KEY);
                request.onsuccess = () => resolve(request.result?.data ?? null);
                request.onerror = () => resolve(null);
            });
        } catch {
            return null;
        }
    }

    async saveSnapshot(data: Uint8Array): Promise<void> {
        const db = await this.getDb();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(SNAPSHOT_STORE, 'readwrite');
            const store = tx.objectStore(SNAPSHOT_STORE);
            const request = store.put({
                data,
                version: this.getSnapshotVersion(),
                createdAt: Date.now()
            }, SNAPSHOT_KEY);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async invalidateSnapshot(): Promise<void> {
        try {
            const db = await this.getDb();
            return new Promise((resolve) => {
                const tx = db.transaction(SNAPSHOT_STORE, 'readwrite');
                const store = tx.objectStore(SNAPSHOT_STORE);
                store.delete(SNAPSHOT_KEY);
                tx.oncomplete = () => resolve();
            });
        } catch {
            // Ignore errors during invalidation
        }
    }

    getSnapshotVersion(): string {
        // Version based on app version + shim hashes
        // Invalidate when shims or Pyodide version changes
        return 'v1.0.0'; // TODO: Compute from build info
    }
}
```

### 2. Integrate with JupyterLite Service

Modify `playground-jupyterlite.service.ts`:

```typescript
private async initializePyodide(): Promise<void> {
    const snapshotService = inject(PyodideSnapshotService);
    
    // Try to restore from snapshot
    if (await snapshotService.hasSnapshot()) {
        try {
            const snapshot = await snapshotService.getSnapshot();
            if (snapshot) {
                console.log('[Pyodide] Restoring from snapshot...');
                await this.pyodide.loadSnapshot(snapshot);
                console.log('[Pyodide] Snapshot restored in <3s');
                return;
            }
        } catch (err) {
            console.warn('[Pyodide] Snapshot restore failed, doing fresh init:', err);
            await snapshotService.invalidateSnapshot();
        }
    }
    
    // Fresh initialization
    console.log('[Pyodide] Fresh initialization...');
    await this.loadMicropip();
    await this.loadShims();
    await this.setupBroadcastChannel();
    
    // Save snapshot for next time
    try {
        const snapshot = await this.pyodide.dumpSnapshot();
        await snapshotService.saveSnapshot(snapshot);
        console.log('[Pyodide] Snapshot saved for future fast-start');
    } catch (err) {
        console.warn('[Pyodide] Failed to save snapshot:', err);
    }
}
```

### 3. Add Version-Based Invalidation

```typescript
// In PyodideSnapshotService
async validateOrInvalidate(): Promise<boolean> {
    const currentVersion = this.getSnapshotVersion();
    const db = await this.getDb();
    
    return new Promise((resolve) => {
        const tx = db.transaction(SNAPSHOT_STORE, 'readonly');
        const store = tx.objectStore(SNAPSHOT_STORE);
        const request = store.get(SNAPSHOT_KEY);
        
        request.onsuccess = () => {
            const stored = request.result;
            if (!stored || stored.version !== currentVersion) {
                this.invalidateSnapshot().then(() => resolve(false));
            } else {
                resolve(true);
            }
        };
        request.onerror = () => resolve(false);
    });
}
```

---

## Verification

```bash
# Run unit tests
npm run test -- --include="**/pyodide-snapshot.service.spec.ts"

# Manual verification
# 1. Clear browser storage (DevTools > Application > Clear storage)
# 2. Open /app/playground?mode=browser
# 3. Time the first Pyodide initialization (~30s)
# 4. Reload the page
# 5. Time the second initialization (<5s with snapshot)
```

---

## Success Criteria

- [ ] Unit tests written first and initially failing
- [ ] `PyodideSnapshotService` created with full IndexedDB implementation
- [ ] Snapshot created after first successful bootstrap
- [ ] Snapshot restored on subsequent page loads
- [ ] Version-based invalidation prevents stale snapshots
- [ ] Cold start: ~30s (unchanged)
- [ ] Warm start with snapshot: <5s
- [ ] All unit tests pass
- [ ] E2E tests can optionally mock Pyodide using snapshot

---

## Future Enhancements (Out of Scope)

1. **Pre-built snapshot bundling**: Ship a pre-computed snapshot with the app
2. **Worker pool**: Maintain warm Pyodide workers for instant availability
3. **Differential snapshots**: Only store changes from base environment
