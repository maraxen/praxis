# Inventory Search Logic Investigation - Root Cause Analysis

## Executive Summary

The "No definitions matching search" error in the Playground inventory adder is caused by a logic error in `AssetWizard`, which attempts to filter machine definitions using a non-existent property (`plr_category`). The data exists in the SQLite database but is filtered out by the UI component.

## Data Verification

- **Seed Data**: Confirmed presence of ~79 definitions in `plr-definitions.ts`.
- **Seeding Logic**: `SqliteService.initDb()` performs `INSERT OR IGNORE` from these definitions.
- **Data Shape**:
  - `PLR_MACHINE_DEFINITIONS` uses `machine_type` (e.g., 'LiquidHandler').
  - `SqliteService` maps this to `machine_category` column.
  - `MachineDefinition` interface has optional `plr_category` and `machine_category`.
  - In Browser Mode, objects returned by `AssetService` will have `machine_category` populated, but `plr_category` is **undefined**.

## Root Cause

In `AssetWizard.ngOnInit` (Line 123):

```typescript
// Faulty Logic
return this.assetService.searchMachineDefinitions(query).pipe(
  map(defs => defs.filter(d => d.plr_category === 'Machine')) 
);
```

1. **Property Mismatch**: `d.plr_category` is undefined for machine definitions.
2. **Incorrect Value**: Even if it existed, valid categories are 'LiquidHandler', 'PlateReader', etc., not 'Machine'.
3. **Filter Ignoring User Selection**: The logic hardcodes the check, ignoring the user's selected category dropdown.

## Recommended Fix

Update `AssetWizard` to filter by the selected `machine_category` instead of the hardcoded `plr_category === 'Machine'`.

**File**: `praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts`

```typescript
// Corrected Logic
return this.assetService.searchMachineDefinitions(query).pipe(
  map(defs => defs.filter(d => !category || d.machine_category === category))
);
```

This change will:

1. Respect the user's category selection (e.g., "LiquidHandler").
2. correctly match against the populated `machine_category` property.
3. Allow search results to appear.
