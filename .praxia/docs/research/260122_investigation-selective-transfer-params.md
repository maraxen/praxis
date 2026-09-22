# Investigation Report: Selective Transfer Parameter Persistence

**Date**: 2026-01-21  
**Task ID**: 260121185700  
**Persona**: Oracle  

## Executive Summary

The investigation confirms that the `transfer_pattern` and `replicate_count` parameters **DO NOT** exist in the current codebase or the generated database file on disk. Their appearance in the application is identified as a **client-side caching artifact** caused by `SqliteService` prioritizing stale IndexedDB data over the fresh `praxis.db` file.

## Findings

### 1. Codebase Audit (Passed)

- **Source File**: `praxis/protocol/protocols/selective_transfer.py` was inspected.
- **Parameters Found**: `liquid_handler`, `source_plate`, `dest_plate`, `tip_rack`, `indices`, `transfer_volume_ul`, `state`.
- **Result**: `transfer_pattern` and `replicate_count` are **NOT** present in the source code.

### 2. Database Audit (Passed)

- **Database File**: `praxis/web-client/src/assets/db/praxis.db` (Generated 2026-01-21 18:31).
- **Table**: `parameter_definitions` queried for "Selective Transfer" protocol.
- **Result**: Only `indices` and `transfer_volume_ul` (plus system params) were found. The unwanted parameters are **ABSENT** from the disk database.

### 3. Root Cause Analysis: Frontend Persistence

- **Component**: `SqliteService` (`praxis/web-client/src/app/core/services/sqlite.service.ts`)
- **Mechanism**: The service attempts to load a persisted database from specific browser storage (IndexedDB) *before* falling back to the `praxis.db` file on disk.
- **Validation Gap**: The service currently only validates that the `machine_definitions` table exists. It **does not** verify if the persisted schema version or generation timestamp matches the file on server.
- **Outcome**: A browser that previously loaded the old schema will continue to use it, ignoring the new clean database generated on the backend.

## Recommendations

### Immediate Workaround (For User)

Force a database reset in the browser to clear the stale cache:

1. Append `?resetdb=1` to the application URL (e.g., `http://localhost:4200/?resetdb=1`).
2. Refresh the page.
3. This triggers `SqliteService.clearStore()` and reloads fresh definitions from disk.

### Systemic Fix (For Engineering)

Update `SqliteService` to perform a robust freshness check:

1. Fetch `praxis.db` headers or a separate `metadata.json` first.
2. Compare a version/timestamp token against the persisted `_schema_metadata`.
3. If the server version is newer, auto-trigger `clearStore()`.

## Conclusion

The "regression" is a local environment state issue, not a codebase defect. No code changes are required in `selective_transfer.py` or `.agent` files. The fix is operational (browser cache clear).
