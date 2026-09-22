# Jules Stage 1 Dispatch Prompts

## Session 1A: Interceptor Type Safety

**Target:** `praxis` repo  
**Files:** `browser-mode.interceptor.ts`, `browser-mock-router.ts`

### Prompt
```
# Type Safety: HTTP Interceptors

## Context
The browser-mode interceptor and mock router use excessive `as any` type assertions that bypass TypeScript's type checking.

## Files to Modify
- `praxis/web-client/src/app/core/interceptors/browser-mode.interceptor.ts`
- `praxis/web-client/src/app/core/interceptors/browser-mock-router.ts`

## Requirements
1. Replace all `as any` with proper type definitions
2. Add interfaces for request/response body shapes where needed
3. Use type guards instead of casting where appropriate
4. Ensure no TypeScript errors after changes

## Verification
```bash
cd praxis/web-client && npm run build
npm run test -- --run
```

## Constraints
- Do NOT modify the logic, only improve types
- All existing tests must pass
```

---

## Session 1B: Dead Code Removal

**Target:** `praxis` repo  
**Files:** AuthService, ProtocolListSkeletonComponent, orphan barrels

### Prompt
```
# Dead Code Removal

## Context
The DEAD_CODE_AUDIT.md identified unused code that should be removed.

## Files to Delete
1. `praxis/web-client/src/app/features/auth/services/auth.service.ts` (unused)
2. `praxis/web-client/src/app/features/protocols/components/protocol-list-skeleton.component.ts` (unused)
3. `praxis/web-client/src/app/shared/components/view-controls/index.ts` (orphan barrel)
4. `praxis/web-client/src/app/shared/components/protocol-warning-badge/index.ts` (orphan barrel)
5. `praxis/web-client/src/app/shared/components/confirmation-dialog/index.ts` (orphan barrel)

## Requirements
1. Delete each file
2. Remove any imports referencing deleted files
3. Remove any module declarations for deleted components/services
4. Ensure build passes after deletion

## Verification
```bash
cd praxis/web-client && npm run build
npm run test -- --run
```

## Constraints
- Only delete files listed above
- If a file IS actually used, skip it and document why
```

---

## Session 1C: Shared Component Type Safety

**Target:** `praxis` repo  
**Files:** autocomplete, machine-card, filter-chip components

### Prompt
```
# Type Safety: Shared Components

## Context
Several shared components use `as any` casts that should be replaced with proper types.

## Files to Modify
- `praxis/web-client/src/app/shared/components/praxis-autocomplete/praxis-autocomplete.component.ts`
- `praxis/web-client/src/app/shared/components/machine-card/machine-card.component.ts`
- `praxis/web-client/src/app/shared/components/filter-chip/filter-chip.component.ts`
- `praxis/web-client/src/app/shared/components/filter-chip-bar/filter-chip-bar.component.ts`
- `praxis/web-client/src/app/shared/formly-types/asset-selector.component.ts`

## Requirements
1. Replace `as any` with proper interface types
2. Add missing type definitions for component inputs/outputs
3. Use generics where appropriate for reusable components
4. Ensure strict null checks pass

## Verification
```bash
cd praxis/web-client && npm run build
npm run test -- --run
```
```

---

## Session 1D: Worker Type Assertions

**Target:** `praxis` repo  
**Files:** python.worker.ts

### Prompt
```
# Type Safety: Python Worker

## Context
The Python worker uses `as any` for postMessage payloads and global assignments.

## File to Modify
- `praxis/web-client/src/app/core/workers/python.worker.ts`

## Requirements
1. Define proper interfaces for all message payloads (PLR_COMMAND, WELL_STATE_UPDATE, FUNCTION_CALL_LOG, USER_INTERACTION)
2. Replace `(self as any)` with properly typed worker scope
3. Type the handlePythonOutput function properly
4. Add type definitions for protocol_bytes, machine_config, deck_setup_script

## Verification
```bash
cd praxis/web-client && npm run build
```

## Constraints
- Do NOT modify worker logic
- Only improve type definitions
```

---

## Session 1E: SQLite Service Types

**Target:** `praxis` repo  
**Files:** sqlite.service.ts, async-repositories.ts

### Prompt
```
# Type Safety: SQLite Services

## Context
The SQLite service layer uses `as any` for query results and partial updates.

## Files to Modify
- `praxis/web-client/src/app/core/services/sqlite/sqlite.service.ts`
- `praxis/web-client/src/app/core/db/async-repositories.ts`

## Requirements
1. Define result row types for SQLite queries
2. Replace `as any` in repository methods with proper generics
3. Type the properties_json and state_history accessors
4. Use Partial<T> for update operations instead of `as any`

## Verification
```bash
cd praxis/web-client && npm run build
npm run test -- --run
```

## Constraints
- Do NOT modify sqlite-opfs.service.ts (recently refactored)
- Only improve types, not logic
```
