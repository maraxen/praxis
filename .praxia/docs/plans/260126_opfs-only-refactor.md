---
title: 'Implementation Plan: OPFS-Only Browser Mode'
description: 'Plan to make OPFS the only browser-mode persistence layer, removing the legacy sql.js + IndexedDB path'
status: archived
task_id: 260922_debt-1293-docs-migration
---
# Implementation Plan: OPFS-Only Browser Mode

**Objective**: Refactor browser mode persistence to use **OPFS exclusively**, removing the legacy sql.js + IndexedDB path.

**Created**: 2026-01-23
**Status**: Planning Complete (Revised after critique)

---

## Context and Background

### Current State (Broken Hybrid)

The Praxis browser mode currently has **two persistence paths**:

| Path | Library | Storage | Status |
|------|---------|---------|--------|
| **Legacy** | `sql.js` + sync repos | IndexedDB | ⚠️ Still active, blocks UI on large DBs |
| **OPFS** | `@sqlite.org/sqlite-wasm` + async repos | OPFS worker | ✅ Built but NOT wired to services |

**The Problem**: When OPFS mode is toggled ON, services like `AssetService` still use the legacy sync path because they were never updated to use `SqliteService.getAsyncRepositories()`.

### Desired State (OPFS-Only)

- All browser mode database operations go through `SqliteOpfsService` → Web Worker → OPFS
- Legacy sql.js and IndexedDB code removed (or gated behind emergency debug flag)
- Single code path simplifies maintenance and testing

### Decision: Feature Flag Disposition

**Keep `praxis_use_opfs` as emergency fallback** but:

- Default to `true` (OPFS enabled)
- Only used if OPFS fails to initialize (browser compatibility fallback)
- Document in troubleshooting guide

---

## Pre-Requisites

Before starting, the executing agent MUST:

1. **Read the project README**:

   ```bash
   view_file /Users/mar/Projects/praxis/.agent/README.md
   ```

2. **Review relevant skills**:

   ```bash
   view_file /Users/mar/Projects/praxis/.agent/skills/verification-before-completion/SKILL.md
   view_file /Users/mar/Projects/praxis/.agent/skills/test-fixing/SKILL.md
   view_file /Users/mar/Projects/praxis/.agent/skills/systematic-debugging/SKILL.md
   ```

3. **Review knowledge artifacts**:

   ```bash
   view_file ~/.gemini/antigravity/knowledge/praxis_browser_persistence_architecture/artifacts/overview.md
   view_file ~/.gemini/antigravity/knowledge/praxis_browser_persistence_architecture/artifacts/implementation/async_repository_refactor.md
   view_file ~/.gemini/antigravity/knowledge/praxis_e2e_test_infrastructure/artifacts/overview.md
   ```

4. **Verify current failure state** (establishes baseline):

   ```bash
   cd /Users/mar/Projects/praxis/praxis/web-client
   npx playwright test e2e/specs/05-opfs-persistence.spec.ts --project=chromium --reporter=list
   ```

   Expected: Tests fail with "No machines matching the current filters" because OPFS path not wired.

5. **Discover existing unit tests**:

   ```bash
   find /Users/mar/Projects/praxis/praxis/web-client/src -name "*.spec.ts" | xargs grep -l "SqliteService\|AssetService" | head -10
   ```

---

## Affected Files

### Primary Targets (Services to Refactor)

| File | Current Behavior | Required Change |
|------|-----------------|-----------------|
| `src/app/features/assets/services/asset.service.ts` | Uses sync repos via `this.sqliteService.machines`, `.resources`, etc. | Switch to async repos via `getAsyncRepositories()` |
| `src/app/features/execution-monitor/services/run-history.service.ts` | Uses sync repos | Switch to async repos |
| `src/app/features/run-protocol/services/execution.service.ts` | Uses sync repos | Switch to async repos |

### Key Infrastructure Files (Reference Only)

| File | Role | Changes Needed |
|------|------|----------------|
| `src/app/core/services/sqlite.service.ts` | Entry point for repos | Phase 3 cleanup only |
| `src/app/core/services/sqlite-opfs.service.ts` | OPFS worker wrapper | **None** - already complete |
| `src/app/core/db/async-repositories.ts` | Async repo implementations | **None** - already complete |
| `src/app/core/db/repositories.ts` | Legacy sync repos | Phase 3 removal candidate |

---

## Critical Architecture Notes

### OPFS Initialization Flow

```
App Bootstrap
    ↓
SqliteService.constructor() 
    ↓ (creates legacy db$ Observable)
    
First call to getAsyncRepositories()
    ↓
SqliteOpfsService.init()
    ↓ (lazy - creates Web Worker)
    ↓
OpfsMigrationService.performMigrationIfNeeded()
    ↓ (migrates IndexedDB → OPFS if needed)
    ↓
Returns AsyncRepositories
```

**Key Insight**: `getAsyncRepositories()` returns `Observable<AsyncRepositories>`, so calls must wait for initialization. This is already handled by the Observable chain.

### Error Handling Pattern

If OPFS fails to initialize:

```typescript
this.sqliteService.getAsyncRepositories().pipe(
  catchError(err => {
    console.error('[AssetService] OPFS init failed, operation aborted:', err);
    return throwError(() => new Error('Database not available'));
  })
)
```

Services should NOT silently fall back to legacy - this masks the problem.

---

## Implementation Strategy

### Phase 1: AssetService Refactor (Proof of Concept)

**Goal**: Prove the pattern works end-to-end with `AssetService`.

#### Step 1.1: Add Dependency

Ensure `SqliteOpfsService` doesn't need to be injected separately - it's already used internally by `SqliteService.getAsyncRepositories()`.

#### Step 1.2: Refactor Pattern

**BEFORE (sync, legacy)**:

```typescript
getMachines(): Observable<Machine[]> {
  if (this.modeService.isBrowserMode()) {
    return this.sqliteService.machines.pipe(
      map(repo => {
        const results = repo.findAll();  // Sync call!
        return results.map(m => ({ ...m, status: m.status || 'OFFLINE' }));
      })
    );
  }
  return this.apiWrapper.wrap(...);
}
```

**AFTER (async, OPFS)**:

```typescript
getMachines(): Observable<Machine[]> {
  if (this.modeService.isBrowserMode()) {
    return this.sqliteService.getAsyncRepositories().pipe(
      switchMap(repos => repos.machines.findAll()),  // Returns Observable!
      map(machines => machines.map(m => ({ ...m, status: m.status || 'OFFLINE' })))
    );
  }
  return this.apiWrapper.wrap(...);
}
```

**BEFORE (create with sync save)**:

```typescript
createMachine(machine: MachineCreate): Observable<Machine> {
  if (this.modeService.isBrowserMode()) {
    return this.sqliteService.machines.pipe(
      switchMap(async repo => {
        const newMachine = { /* ... */ };
        repo.create(newMachine as any);  // Sync!
        await this.sqliteService.save();  // Saves to IndexedDB!
        return newMachine;
      })
    );
  }
  return this.apiWrapper.wrap(...);
}
```

**AFTER (async create)**:

```typescript
createMachine(machine: MachineCreate): Observable<Machine> {
  if (this.modeService.isBrowserMode()) {
    return this.sqliteService.getAsyncRepositories().pipe(
      switchMap(repos => {
        const newMachine: Machine = {
          accession_id: crypto.randomUUID(),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          /* ... rest of fields ... */
        };
        return repos.machines.create(newMachine);  // Returns Observable<Machine>!
        // No explicit save - OPFS worker persists automatically
      })
    );
  }
  return this.apiWrapper.wrap(...);
}
```

#### Step 1.3: Full Method List for AssetService

| Method | Line | Action |
|--------|------|--------|
| `getMachines()` | ~62 | Refactor to async |
| `createMachine()` | ~85 | Refactor to async, remove `save()` call |
| `deleteMachine()` | ~131 | Refactor to async |
| `updateMachine()` | ~142 | Add browser mode implementation using async |
| `getResources()` | ~153 | Refactor to async |
| `createResource()` | ~175 | Refactor to async, remove `save()` call |
| `deleteResource()` | ~203 | Refactor to async |
| `getWorkcells()` | ~215 | Refactor to async |
| `getMachineDefinitions()` | ~233 | Refactor to async |
| `getMachineFrontendDefinitions()` | ~254 | Refactor to async |
| `getMachineBackendDefinitions()` | ~271 | Refactor to async |
| `getBackendsForFrontend()` | ~299 | Refactor to async |
| `getResourceDefinitions()` | ~316 | Refactor to async |
| `getResourceDefinition()` | ~364 | Refactor to async |

#### Step 1.4: Verify Phase 1

After completing AssetService:

```bash
# Run E2E tests
cd /Users/mar/Projects/praxis/praxis/web-client
npx playwright test e2e/specs/05-opfs-persistence.spec.ts --project=chromium --reporter=list

# Expected: Test 1 should now pass (data persists when OPFS enabled)
```

**GO/NO-GO**: Proceed to Phase 2 only if Test 1 passes.

---

### Phase 2: Remaining Services

Apply the same pattern to:

#### run-history.service.ts

Location: `src/app/features/execution-monitor/services/run-history.service.ts`

Methods to update (search for `isBrowserMode()`):

- `getProtocolRuns()` → use `repos.protocolRuns.findAll()`
- `getProtocolRun()` → use `repos.protocolRuns.findById()`
- `createProtocolRun()` → use `repos.protocolRuns.create()`
- Other browser mode branches

#### execution.service.ts

Location: `src/app/features/run-protocol/services/execution.service.ts`

Methods to update:

- `startExecution()` browser mode branch
- `getExecutionState()` browser mode branch
- Any other `isBrowserMode()` checks

#### Verification Gate

```bash
# Run unit tests
cd /Users/mar/Projects/praxis/praxis/web-client
npm run test -- --run

# Run full E2E suite
npx playwright test --project=chromium --reporter=list
```

**GO/NO-GO**: Proceed to Phase 3 only if all tests pass.

---

### Phase 3: Legacy Cleanup (DEFERRED)

**⚠️ IMPORTANT**: This phase should be done as a **separate task** after Phase 1-2 are stable in production.

Candidates for removal:

- `SqliteService.save()` method
- `SqliteService.saveToStore()` and `persistToIndexedDB()` methods  
- `SqliteService.machines`, `.resources`, etc. (sync repo accessors)
- `src/app/core/db/repositories.ts` (entire file)
- sql.js dependency from package.json

**Do NOT execute Phase 3 in this task.**

---

## Testing Strategy

### Unit Tests (Vitest)

#### Mock Pattern for getAsyncRepositories

```typescript
// In test file
const mockMachineRepo = {
  findAll: vi.fn().mockReturnValue(of([mockMachine1, mockMachine2])),
  create: vi.fn().mockImplementation(m => of(m)),
  delete: vi.fn().mockReturnValue(of(undefined)),
  findById: vi.fn().mockReturnValue(of(mockMachine1)),
};

const mockAsyncRepos = {
  machines: mockMachineRepo,
  resources: { /* ... */ },
  // ... other repos
};

const mockSqliteService = {
  getAsyncRepositories: vi.fn().mockReturnValue(of(mockAsyncRepos)),
};

// In test setup
providers: [
  { provide: SqliteService, useValue: mockSqliteService },
]
```

### E2E Tests (Playwright)

**Primary verification**: `e2e/specs/05-opfs-persistence.spec.ts`

```bash
cd /Users/mar/Projects/praxis/praxis/web-client
npx playwright test e2e/specs/05-opfs-persistence.spec.ts --project=chromium --reporter=list
```

**Full regression**:

```bash
npx playwright test --project=chromium
```

### Manual Verification Checklist

Per `verification-before-completion` skill, MUST verify before claiming done:

- [ ] **Create flow**: Asset Wizard → Create Machine → Appears in table
- [ ] **Persistence**: Page reload → Machine still visible
- [ ] **OPFS storage**: DevTools → Application → Storage → OPFS → Contains `praxis.db`
- [ ] **Console logs**: `[SqliteOpfsWorker]` messages appear during init
- [ ] **No errors**: No uncaught exceptions in console

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking production API mode | Low | High | All changes inside `isBrowserMode()` guards |
| Data loss during migration | Low | High | `OpfsMigrationService` already handles this |
| Async/Observable errors | Medium | Medium | Use `catchError` in all chains |
| Type mismatches | Medium | Low | Async repos have same type signatures |
| Browser compatibility | Low | Medium | `opfs-sahpool` VFS works without COOP/COEP |

---

## Definition of Done

### Required (Blocking)

- [ ] All `AssetService` browser mode methods use `getAsyncRepositories()`
- [ ] All `RunHistoryService` browser mode methods use `getAsyncRepositories()`
- [ ] All `ExecutionService` browser mode methods use `getAsyncRepositories()`
- [ ] E2E test `05-opfs-persistence.spec.ts` passes all 3 tests
- [ ] Unit tests pass: `npm run test -- --run`
- [ ] Manual verification checklist complete

### Recommended (Non-Blocking)

- [ ] Update DEBUG_STATUS.md with completion notes
- [ ] Update knowledge item `praxis_browser_persistence_architecture`
- [ ] Create atomic git commit(s) with descriptive messages

---

## Execution Summary for Fresh Session

1. **Read pre-requisites** (skills, knowledge items, README)
2. **Verify baseline** - run E2E test to confirm current failure
3. **Refactor AssetService** - all browser mode methods to async repos
4. **Test** - run E2E `05-opfs-persistence.spec.ts`
5. **If passing**, refactor `RunHistoryService`
6. **Test** - run unit tests
7. **If passing**, refactor `ExecutionService`
8. **Final verification** - manual checklist
9. **Commit** - atomic commits per service
10. **Update documentation**

---

## References

- **Plan Location**: `/Users/mar/Projects/praxis/praxis/web-client/.agent/plans/opfs-only-refactor.md`
- **Debug Status**: `/Users/mar/Projects/praxis/praxis/web-client/DEBUG_STATUS.md`
- **Knowledge**: `~/.gemini/antigravity/knowledge/praxis_browser_persistence_architecture/`
- **Async Repos**: `src/app/core/db/async-repositories.ts`
- **OPFS Service**: `src/app/core/services/sqlite-opfs.service.ts`
- **E2E Tests**: `e2e/specs/05-opfs-persistence.spec.ts`
