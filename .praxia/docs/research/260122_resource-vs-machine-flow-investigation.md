# Investigation: Add Resource vs. Add Machine Flow in Playground

## Executive Summary

Both "Add Machine" and "Add Resource" flows in the Playground are broken due to the same root cause: a schema mismatch in the SQLite `initDb` seeding logic where the `plr_category` column is left `NULL`, causing frontend filters to return empty results.

## Comparison

| Feature | Status | Root Cause |
| :--- | :--- | :--- |
| **Add Machine** | **Broken** | `AssetWizard` filters by `plr_category === 'Machine'`, but SQLite maps `machine_type` -> `machine_category`. `plr_category` is NULL. |
| **Add Resource** | **Broken** | `AssetService` filters by `plr_category === category`, but SQLite maps `plr_category` -> `resource_type`. `plr_category` is NULL. |

## Detailed Analysis

### 1. Add Machine Flow

- **UI Logic**: `AssetWizard` hardcodes a filter: `defs.filter(d => d.plr_category === 'Machine')`.
- **Data State**: In SQLite `machine_definitions` table, `plr_category` is NULL. The category data resides in `machine_category`.
- **Result**: Filter returns 0 results. User sees "No definitions matching search".

### 2. Add Resource Flow

- **UI Logic**: `AssetWizard` calls `assetService.searchResourceDefinitions(query, category)`.
- **Service Logic**: `AssetService` executes: `defs.filter(d => d.plr_category === plrCategory)`.
- **Data State**: In SQLite `resource_definitions` table, `plr_category` is NULL. The category data from `PLR_RESOURCE_DEFINITIONS` is mapped to the `resource_type` column during seeding.
- **Result**: Filter returns 0 results. User sees "No definitions matching search".

### 3. Common Issues

- **Schema Mapping**: The `SqliteService` seeding logic maps the category field to a specific column (`machine_category` / `resource_type`) but the valid `plr_category` column (present in the schema) is ignored and left NULL.
- **Frontend Expectation**: The frontend consistently expects `plr_category` to be populated for filtering, which aligns with the generated API schema but contradicts the browser-mode data seeding.

## Recommendations

1. **Fix SQLite Seeding**: Update `SqliteService.ts` to populate the `plr_category` column for both machines and resources during seeding.
    - Map `def.machine_type` -> `plr_category` (and `machine_category`).
    - Map `def.plr_category` -> `plr_category` (and `resource_type`).

2. **Fix Frontend Logic (Machines)**: Update `AssetWizard` to use `machine_category` or remove the redundant 'Machine' filter entirely, as `searchMachineDefinitions` only returns machines.

3. **Fix Frontend Logic (Resources)**: Update `AssetService.getResourceDefinitions` (Browser Mode branch) to fallback to `resource_type` if `plr_category` is missing, or rely on the DB fix.
