# Investigation Report: Backend Categories in Inventory

**Task ID**: 260121152847
**Status**: INVESTIGATION COMPLETE
**Review**: Fix was INCOMPLETE and introduced regressions in Browser Mode.

## 1. Original Fix Analysis

- **Commit**: `40375a78` "feat(app): standardize PLR category filtering..."
- **Change**: Updated `AssetWizard.ts` to filter search results using `map(defs => defs.filter(d => d.plr_category === 'Machine'))`.
- **Finding**: This fix effectively hides backend definitions from the **search results**, BUT only if the `plr_category` field is present.

## 2. Issues Identified

### A. Browser Mode Regression (Critical)

In Browser Mode (using `SqliteService`), the `MachineDefinition` objects retrieved from SQLite **DO NOT have the `plr_category` field populated**.

- `sqlite.service.ts` seeds from `PLR_MACHINE_DEFINITIONS`.
- `PLR_MACHINE_DEFINITIONS` in `plr-definitions.ts` lacks the `plr_category` property (it uses `machine_type`).
- **Consequence**: `d.plr_category` is `undefined`.
- **Result**: `d.plr_category === 'Machine'` evaluates to `false` for ALL machines.
- **Impact**: **Users in Browser Mode cannot find ANY machines in the Asset Wizard.**

### B. Incomplete Category Filtering (The Reported Issue)

The user report states "Categories STILL showing backend types". This refers to the **Category Dropdown** in the wizard.

- **Code Path**: `AssetWizard.ngOnInit` -> `this.categories$`.
- **Source**: `AssetService.getMachineFacets()`.
- **Browser Mode Logic**: Counts `machine_category` from definitions.
- **Production Mode Logic**: Calls `MachinesService.getMachineDefinitionFacets...`.
- **Finding**:
  - The `categories$` observable is **NOT filtered** by `plr_category === 'Machine'` in `AssetWizard.ts`.
  - If the Backend API (Production) returns facets for "Backend" or uses "Backend" as a `machine_category` for backend definitions, they will appear in the dropdown.
  - The "Fix" only applied to `searchMachineDefinitions` (the result list), NOT `getMachineFacets` (the category list).

## 3. Root Cause

1. **Browser Mode**: Data Integrity Issue. `plr_category` is missing from SQLite seed data/mapping.
2. **General/Production**: Incomplete UI Logic. The `categories$` stream is not filtered to exclude non-Machine categories, relying entirely on the backend to filter facets (which it apparently isn't fully doing, or returns mixed types).

## 4. Recommendations

### Immediate Fixes

1. **Polyfill Browser Mode**: Update `AssetService.getMachineDefinitions` (in the `isBrowserMode` block) to manually inject `plr_category: 'Machine'` for all definitions coming from the `machine_definitions` table (which is safe as it only stores machines).
2. **Filter Dropdown**: Update `AssetWizard.ts` to filter the `categories$` stream to exclude known backend types if they leak through, OR update `AssetService.getMachineFacets` to strictly filter its source data before counting.

### Long Term

- Standardize `MachineDefinition` to always include `plr_category` in all layers (DB, API, Types).
- Add explicit test coverage for Browser Mode asset searching.

## 5. Verification

- **Browser Mode**: Verify `AssetWizard` search works again (currently broken).
- **Inventory**: Verify "Backend" is gone from the Category list.
