# Extend Pyodide Snapshot to Protocol Execution (P2)

> **Stream**: 3 - Performance  
> **Effort**: M (2-3 hours)  
> **Priority**: P2  
> **Approach**: TDD - Write tests first, then implement  
> **Isolation**: Use git worktree before starting

---

## Objective

Extend the Pyodide snapshot/restore capability to the protocol execution path. Currently, snapshots only benefit the Playground; protocol execution still does a full 30s Pyodide bootstrap every time.

---

## Context Files (Read First)

1. `src/app/features/playground/services/pyodide-snapshot.service.ts` → Existing snapshot service
2. `src/app/features/run-protocol/services/execution.service.ts` → Protocol execution entry point
3. `src/app/features/run-protocol/services/python-runtime.service.ts` → Python runtime for protocols (if exists)
4. `src/assets/jupyterlite/` → JupyterLite/Pyodide assets
5. `.agent/skills/test-driven-development/SKILL.md` → TDD workflow

---

## Worktree Setup (REQUIRED FIRST STEP)

```bash
git worktree add .worktrees/protocol-snapshot -b feat/protocol-snapshot-restore
cd .worktrees/protocol-snapshot/praxis/web-client
npm install
```

---

## Background

### Current Architecture

**Playground Path**:
```
User opens Playground → JupyterLite iframe → Pyodide boots (30s) → Snapshot saved
User revisits → Snapshot restored (3s) ✅
```

**Protocol Execution Path**:
```
User starts protocol → ExecutionService → Pyodide boots (30s) → Protocol runs
User runs again → Pyodide boots (30s) again ❌ No snapshot
```

### Desired Architecture

Both paths should share the snapshot:
```
First use (either path) → Pyodide boots → Snapshot saved
Subsequent use (any path) → Snapshot restored (3s)
```

---

## TDD Approach

### Step 1: Write Unit Tests First

```typescript
// execution.service.spec.ts additions
describe('Pyodide Snapshot Integration', () => {
  it('restores from snapshot when available', async () => {
    const snapshotService = TestBed.inject(PyodideSnapshotService);
    
    // Pre-populate snapshot
    await snapshotService.saveSnapshot(mockSnapshotData);
    
    const service = TestBed.inject(ExecutionService);
    const startTime = Date.now();
    
    await service.initializePython();
    
    const elapsed = Date.now() - startTime;
    expect(elapsed).toBeLessThan(5000); // Should be fast
    expect(logSpy).toHaveBeenCalledWith(expect.stringContaining('Restoring from snapshot'));
  });

  it('saves snapshot after fresh initialization', async () => {
    const snapshotService = TestBed.inject(PyodideSnapshotService);
    const saveSpy = vi.spyOn(snapshotService, 'saveSnapshot');
    
    const service = TestBed.inject(ExecutionService);
    await service.initializePython();
    
    expect(saveSpy).toHaveBeenCalled();
  });
});
```

### Step 2: Run Tests (Should Fail)

```bash
npm run test -- --include="**/execution.service.spec.ts" --grep "Snapshot"
```

---

## Implementation Steps

### 1. Refactor Snapshot Service to Shared Location

Move from playground-specific to core:

```bash
# Move service to shared location
mv src/app/features/playground/services/pyodide-snapshot.service.ts \
   src/app/core/services/pyodide-snapshot.service.ts
mv src/app/features/playground/services/pyodide-snapshot.service.spec.ts \
   src/app/core/services/pyodide-snapshot.service.spec.ts

# Update imports in playground-jupyterlite.service.ts
```

### 2. Create Shared Pyodide Bootstrap Helper

```typescript
// src/app/core/utils/pyodide-bootstrap.ts
import { PyodideSnapshotService } from '../services/pyodide-snapshot.service';

export interface PyodideInstance {
  runPython: (code: string) => any;
  loadSnapshot: (data: Uint8Array) => Promise<void>;
  dumpSnapshot: () => Promise<Uint8Array>;
  // ... other Pyodide methods
}

export async function bootstrapPyodideWithSnapshot(
  snapshotService: PyodideSnapshotService,
  config: { shimUrls: string[] }
): Promise<PyodideInstance> {
  // Try snapshot restore first
  if (await snapshotService.hasSnapshot()) {
    try {
      const snapshot = await snapshotService.getSnapshot();
      if (snapshot) {
        console.log('[Pyodide] Restoring from snapshot...');
        const pyodide = await loadPyodideBasic();
        await pyodide.loadSnapshot(snapshot);
        console.log('[Pyodide] Snapshot restored');
        return pyodide;
      }
    } catch (err) {
      console.warn('[Pyodide] Snapshot restore failed:', err);
      await snapshotService.invalidateSnapshot();
    }
  }

  // Fresh bootstrap
  console.log('[Pyodide] Fresh initialization...');
  const pyodide = await loadPyodide();
  await loadShims(pyodide, config.shimUrls);

  // Save snapshot for next time
  try {
    const snapshot = await pyodide.dumpSnapshot();
    await snapshotService.saveSnapshot(snapshot);
    console.log('[Pyodide] Snapshot saved');
  } catch (err) {
    console.warn('[Pyodide] Failed to save snapshot:', err);
  }

  return pyodide;
}
```

### 3. Integrate with ExecutionService

```typescript
// In execution.service.ts
import { bootstrapPyodideWithSnapshot } from '@core/utils/pyodide-bootstrap';
import { PyodideSnapshotService } from '@core/services/pyodide-snapshot.service';

@Injectable({ providedIn: 'root' })
export class ExecutionService {
  private snapshotService = inject(PyodideSnapshotService);
  private pyodide?: PyodideInstance;

  async initializePython(): Promise<void> {
    if (this.pyodide) return; // Already initialized

    this.pyodide = await bootstrapPyodideWithSnapshot(
      this.snapshotService,
      { shimUrls: ['/assets/python/web_serial_shim.py', ...] }
    );
  }
}
```

### 4. Handle Worker Context

If ExecutionService runs Pyodide in a Web Worker, the snapshot logic needs to be in the worker:

```typescript
// If worker-based, send snapshot via postMessage
worker.postMessage({ type: 'RESTORE_SNAPSHOT', snapshot: snapshotData });

// In worker:
self.onmessage = async (e) => {
  if (e.data.type === 'RESTORE_SNAPSHOT') {
    await pyodide.loadSnapshot(e.data.snapshot);
    self.postMessage({ type: 'READY' });
  }
};
```

---

## Verification

```bash
# Run unit tests
npm run test -- --include="**/execution.service.spec.ts"

# E2E: Run a protocol twice and check timing
# First run: ~30s (fresh bootstrap)
# Second run: <5s (snapshot restore)

# Check console for "[Pyodide] Restoring from snapshot..." on second run
```

---

## Merge Back

```bash
cd /Users/mar/Projects/praxis
git checkout main
git merge feat/protocol-snapshot-restore
git worktree remove .worktrees/protocol-snapshot
```

---

## Success Criteria

- [ ] PyodideSnapshotService moved to shared location
- [ ] ExecutionService uses snapshot restore when available
- [ ] First protocol run: ~30s (same as before)
- [ ] Second protocol run: <5s (snapshot restored)
- [ ] Console shows "[Pyodide] Restoring from snapshot..." messages
- [ ] No regression in Playground snapshot behavior
- [ ] Unit tests pass

---

## Future Enhancements (Out of Scope)

1. **Shared worker pool** - Single Pyodide instance shared between Playground and Execution
2. **Protocol-specific snapshots** - Snapshot after protocol shims loaded (even faster)
3. **IndexedDB storage sharing** - Ensure both paths use same DB key
