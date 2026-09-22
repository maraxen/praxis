# Resource Management Error Log & Audit

**Date:** 2026-01-15
**Feature:** Asset Management / Add Asset Flow

## 1. Executive Summary

The "Add Asset", "Add Machine", and "Add Resource" functionalities are broken due to a combination of architectural shifts (Factory Pattern vs. Static Seeding), incomplete service-to-dialog wiring, and discrepancies between Browser Mode (SQLite) and API Mode expectations.

## 2. Identified Issues & Root Causes

### 2.1. Unwired "Add Asset" Dialogs
- **Component**: `AssetsComponent` (`praxis/web-client/src/app/features/assets/assets.component.ts`)
- **Issue**: `openUnifiedDialog` opens `AddAssetDialogComponent`. However, `AddAssetDialogComponent` is a complex multi-step stepper, while `MachineDialogComponent` and `ResourceDialogComponent` seem to be older, potentially more functional alternatives that are currently **orphaned** or bypassed.
- **Root Cause**: The project has two sets of dialogs for the same purpose. `AddAssetDialogComponent` (new) vs `MachineDialogComponent` (old). The UI calls the new one, but the new one might not be fully implemented or compatible with the `AssetService` expectations.

### 2.2. Browser Mode (SQLite) Persistence Gap
- **Component**: `AssetService` (`praxis/web-client/src/app/features/assets/services/asset.service.ts`)
- **Issue**: `createMachine` and `createResource` in browser mode call `repo.create(newMachine as any)`, but the `SqliteService` signals (e.g., `this.sqliteService.machines`) are **Observables**, not live collections that automatically refresh the UI.
- **Root Cause**: Adding an item to the SQLite repository does not trigger an emission from the `machines` observable in other components unless they re-subscribe or the service manually refreshes them. The `finalize(() => this.machineList?.loadMachines())` in `AssetsComponent` might be failing if the subscription hasn't updated yet.

### 2.3. Schema Mismatch (is_consumable)
- **Component**: `SqliteService` (`praxis/web-client/src/app/core/services/sqlite.service.ts`)
- **Issue**: In `seedDefinitionCatalogs`, there's a comment `FIXED: Removed is_reusable to align with schema.sql`.
- **Root Cause**: Recent schema changes (adding `state_before_json` etc.) might have caused silent failures in SQLite insertions if the `INSERT` statements in `SqliteService` (which are raw SQL) weren't updated.

### 2.4. Machine focus View / Deck View Disconnect
- **Issue**: Discussed in turn 05, but relevant here. If a user "adds" a machine, it has no `plr_definition`, so clicking it shows a blank deck. This "feels" like a broken feature even if the database record was created.

## 3. Suspected Culprits (File/Line)

| File | Line(s) | Description |
|:-----|:--------|:------------|
| `assets.component.ts` | 335-365 | `openUnifiedDialog` logic needs to ensure it calls the correct service methods and refreshes the view. |
| `asset.service.ts` | 85-105 | `createMachine` (Browser Mode) uses `repo.create` but doesn't guarantee the observable stream emits the new value immediately to listeners. |
| `add-asset-dialog.component.ts` | 165-200 | `save()` logic maps UI fields to service models. Discrepancy in `machine_type` vs `machine_category`. |

## 4. Recommendations for Fix (06 E)

1.  **Consolidate Dialogs**: Choose either `AddAssetDialogComponent` or the specialized `MachineDialogComponent`/`ResourceDialogComponent`. The specialized ones (Step 1 -> Frontend Type, Step 2 -> Backend) are actually better for the PLR-heavy architecture.
2.  **Reactive Refresh**: Update `AssetService` to use `BehaviorSubject` for cached lists in browser mode, or ensure `SqliteService` repos emit a new signal after `save()`.
3.  **Synthesize Metadata**: Ensure `createMachine` automatically populates default metadata (like `plr_definition` from Turn 05) so the machine is immediately visible in the Workcell dashboard.
4.  **Fix JSON Handling**: Ensure `connection_info` and `capabilities` are correctly stringified/parsed across the boundary (Browser vs Backend).
