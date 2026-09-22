---
title: 'E2E Database Seeding Issue - Handoff'
---

# E2E Database Seeding Issue - Handoff

## The Problem

E2E tests show **"No protocols found"** in the Protocol Library page despite `praxis.db` containing 6 protocols.

## Quick Answer: What Does "Worker deletes OPFS file before import" Mean?

The browser uses **OPFS (Origin Private File System)** to persist the SQLite database. When importing a new database file:

1. The old database file in OPFS might not be properly overwritten by `importDb()`
2. So we tried adding a `poolUtil.unlink(dbName)` call to delete the old file first
3. But this fix didn't work - the table still doesn't exist after import

## What We Know For Certain

### Evidence from Diagnostic Script

```
BROWSER: [SqliteOpfsService] No protocols found. Loading fresh database from praxis.db...
BROWSER: [SqliteOpfsService] Loading prebuilt database (905216 bytes)...
BROWSER: [SqliteOpfsService] Prebuilt database loaded successfully.
BROWSER: [SqliteOpfsWorker] Error: no such table: function_protocol_definitions
```

**Key Finding:** The 905KB `praxis.db` file IS being fetched and passed to the worker, but after "successful" import, queries still fail with "no such table".

### What We Tried (Both Failed)

1. **Service fix** (`sqlite-opfs.service.ts`): Changed `ensureSchemaAndSeeds()` to check protocol count instead of table count → This correctly triggers database reload
2. **Worker fix** (`sqlite-opfs.worker.ts`): Added `poolUtil.unlink()` before `importDb()` → Import still doesn't persist

### The Real Issue (Hypothesis)

The `poolUtil.importDb()` function from SQLite WASM's opfs-sahpool VFS isn't actually persisting the imported data. Either:

- The import API is being used incorrectly
- The database handle isn't being properly attached to the imported file
- There's a VFS-specific issue with the SAH Pool

## Files to Study

### Core Files

| File | Purpose |
|------|---------|
| `src/app/core/workers/sqlite-opfs.worker.ts` | Web Worker that handles SQLite operations |
| `src/app/core/services/sqlite/sqlite-opfs.service.ts` | Service that communicates with the worker |
| `src/assets/db/praxis.db` | Prebuilt database with protocols (905KB, 6 protocols) |

### Key Functions to Trace

1. `handleImport()` in worker - lines 192-239
2. `poolUtil.importDb()` - from @sqlite.org/sqlite-wasm SAH Pool VFS
3. `initializeFreshDatabase()` in service - lines 125-150

## Debugging Strategy for Fresh Session

### Phase 1: Understand the VFS

1. **Read SQLite WASM documentation** for opfs-sahpool VFS
   - <https://sqlite.org/wasm/doc/trunk/persistence.md>
   - Focus on `importDb` API and its contract
2. **Check if `importDb` returns a promise that resolves correctly**
3. **Verify the file actually exists in OPFS after import** using `poolUtil.getFileNames()`

### Phase 2: Trace Data Flow

1. Add logging to verify:
   - `data.byteLength` before import matches expected (905216)
   - `poolUtil.getFileNames()` after import shows the file
   - Query `SELECT * FROM sqlite_master LIMIT 5` immediately after re-opening
2. Check if the database is being re-opened with correct VFS

### Phase 3: Alternative Approaches

If importDb is broken, consider:

1. **Clear OPFS completely** before import using `poolUtil.wipeFiles()`
2. **Use lower-level OPFS API** instead of poolUtil
3. **Force E2E tests to use fresh storage** via Playwright configuration

## Recommended Skills to Invoke

```
/systematic-debugging  # Follow root cause methodology
/webapp-testing        # For creating Playwright diagnostic scripts
/playwright-skill      # For browser automation patterns
```

## Files Modified (May Need Revert)

1. `src/app/core/services/sqlite/sqlite-opfs.service.ts` - ensureSchemaAndSeeds() fix
2. `src/app/core/workers/sqlite-opfs.worker.ts` - handleImport() unlink addition

## Commands to Reproduce

```bash
# Start dev server
cd /Users/mar/Projects/praxis/praxis/web-client
npm run start:browser -- --port 4200

# Run smoke tests (will fail with current state)
npx playwright test specs/smoke.spec.ts --grep "should navigate to Protocols" --reporter=list

# Check prebuilt DB has protocols
sqlite3 src/assets/db/praxis.db "SELECT COUNT(*) FROM function_protocol_definitions;"
# Should return: 6
```

## Key Diagnostic Script

See `/tmp/playwright-test-db.js` - captures browser console and queries service state.
