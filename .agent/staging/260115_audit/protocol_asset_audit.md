# Protocol Asset Audit

**Date:** 2026-01-15
**Status:** Inspection Complete

## 1. Browser Mode Asset Selection

**File:** `praxis/web-client/src/app/features/run-protocol/run-protocol.component.ts`

**Findings:**
- The `selectProtocol` method has a specific branch for `browserMode`.
- **Current State:** It sets `this.assetsFormGroup.patchValue({ valid: false });`, which correctly *enables* the Asset Selection step (making it required).
- **Observation:** The "Browser Mode Bypass" mentioned in previous context seems to have been removed or fixed in the current codebase. The user is forced to select assets.

## 2. Parameter Compilation & Resolution

**File:** `praxis/web-client/src/app/features/run-protocol/services/execution.service.ts`

**Findings:**
- `buildProtocolExecutionCode` constructs a Python script.
- It injects `parameters`, `metadata`, and `asset_reqs` as JSON strings.
- It calls `resolve_parameters(params, metadata, asset_reqs)` in Python.

**File:** `praxis/web-client/src/assets/python/web_bridge.py`

**Findings:**
- `resolve_parameters` exists.
- **Critical Limitation:** It instantiates `Plate` and `TipRack` with **hardcoded dimensions** (`size_x=12, size_y=8` aka 96-well) whenever it detects "plate" or "tiprack" in the type hint.
- It does **not** use the actual properties of the selected resource (e.g., 384-well plates, custom tuberacks).
- It attempts to handle both Dictionary inputs (if full object passed) and String inputs (UUIDs).

## 3. Gaps & Recommendations

| Gap | Severity | Recommendation |
| :--- | :--- | :--- |
| **Hardcoded Geometry** | High | `web_bridge.py` assumes 96-well format for all plates/tips. |
| **Missing Definition Data** | High | `ExecutionService` does not pass the dimensions/specs of the selected assets to Python. |

**Plan:**
1.  Modify `ExecutionService.startBrowserRun` (or `executeBrowserProtocol`) to:
    *   Look up the *full* resource definition for each selected asset (using `AssetService` or `SqliteService`).
    *   Construct a `resolved_assets_spec` dictionary containing: `name`, `fqn`, `num_items`, `size_x`, `size_y`, `well_count` (or derived from `num_items`).
    *   Pass this `resolved_assets_spec` to the Python script.
2.  Update `web_bridge.py`:
    *   Update `resolve_parameters` to accept `resolved_assets_spec`.
    *   Use this spec to instantiate `Plate` / `TipRack` with correct `num_items_x`, `num_items_y`.