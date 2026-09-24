---
title: 'Research Report: Infinite Consumables & Resource Depletion'
---

# Research Report: Infinite Consumables & Resource Depletion

## 1. Executive Summary

Currently, **"Infinite Consumables" is the default behavior** in both the Backend and Browser-Only modes.

* **Depletion Logic**: There is no mechanism that persists the consumption of tips or liquids (volume reduction) back to the `Resources` database table after a protocol run.
* **Browser Mode**: The `web_bridge.py` layer instantiates new PyLabRobot (PLR) resource objects for every run based on static definitions. It does not load previous state (e.g., used tips), meaning every run starts with full tip racks and fresh liquids.
* **Backend Mode**: While the `WorkcellRuntime` tracks state in memory and saves a full state snapshot to the `Workcell` table (`latest_state_json`), this state is not decomposed to update individual `Resource` records. Subsequent runs do not re-hydrate from the `Workcell` snapshot in a way that affects `ConsumableAssignmentService`.

## 2. Analysis of Depletion Logic

### 2.1 Backend Mode

* **Location**: `praxis/backend/core/workcell_runtime/`
* **Mechanism**: The `WorkcellRuntime` maintains `_active_resources` (live PLR objects). The `StateSyncMixin` periodically serializes the entire workcell state and saves it to the `Workcells` table column `latest_state_json`.
* **Missing Link**:
  * The `ConsumableAssignmentService` (`praxis/backend/core/consumable_assignment.py`) queries the `Resources` table to find compatible assets.
  * The `AssetManager.release_resource` method (`praxis/backend/core/asset_manager/resource_manager.py`) updates the resource **status** (e.g., `AVAILABLE_IN_STORAGE`) but does NOT update the `properties_json` or `plr_state` with the final tip count/volume.
  * Consequently, the `Resources` table always reflects the static definition (full capacity), leading to "infinite" behavior.

### 2.2 Browser-Only Mode

* **Location**: `praxis/web-client/src/assets/python/web_bridge.py` and `praxis/web-client/src/app/features/run-protocol/services/execution.service.ts`
* **Mechanism**:
  * `ExecutionService` generates a Python script that calls `resolve_parameters` in `web_bridge.py`.
  * `resolve_parameters` iterates through input arguments and instantiates **fresh** PLR objects (e.g., `res.TipRack(...)`) using only the `num_items` and dimensions from the definition.
  * There is no code to fetch `initial_state_json` (e.g., previously used tips) and apply it to the new PLR objects.
  * `web_bridge.py` emits `WELL_STATE_UPDATE` to the UI for visualization, which is logged to `function_call_logs`, but `SqliteService` does not parse this to update the `Resources` inventory.

## 3. Implementing Finite Consumables (Depletion)

To implement "Finite Consumables" (tracking depletion), the following changes would be required:

1. **Persistence (Browser & Backend)**:
    * **Backend**: In `_finalize_protocol_run`, extract the final state of all consumables (tip racks, reservoirs) from the `WorkcellRuntime` and pass it to `AssetManager.release_resource` via `final_properties_json_update` to update the `Resources` table.
    * **Browser**: In `ExecutionService`, after a run completes, parse the final `WELL_STATE_UPDATE` or `final_state_json` and use `SqliteService` to update the local `Resources` table `properties_json`.

2. **Re-hydration**:
    * **Backend**: `ConsumableAssignmentService` must respect `properties_json` (e.g., `tips_used_mask`) when checking availability.
    * **Browser**: `web_bridge.py`'s `resolve_parameters` must accept an `initial_state` dictionary (loaded from DB) and apply it to the instantiated PLR objects (e.g., removing tips that are marked as used).

## 4. Option to Skip Depletion (Simulation Mode)

Since "Infinite Consumables" is the current state, creating an option to **skip** depletion would simply mean **retaining the current behavior** for Simulation runs once Persistence is implemented.

* **Design**:
  * Add a flag `update_inventory: bool` to `ProtocolRun` or execution context.
  * **If `update_inventory=False` (Simulation)**: Do not perform the "Persistence" step described above. The DB remains untouched.
  * **If `update_inventory=True` (Physical/Tracked)**: Perform the DB update.

## 5. Runtime Unique ID Creation

The requirement to "allow runtime unique ID creation for tip racks" addresses the need to track *specific* physical tip racks (e.g., "TipRack A vs TipRack B").

* Currently, `ConsumableAssignmentService` selects existing resources.
* To support runtime creation, the frontend `GuidedSetup` or `DeckSetupWizard` should allow users to "Register New Consumable" on the fly, generating a UUID and creating a `Resource` record before the run starts.

## 6. Recommendations

1. **Acknowledge Current State**: Inform users that "Infinite Consumables" is currently the only supported mode.
2. **Implementation Plan**:
    * Implement **State Re-hydration** first (make PLR objects load state from DB).
    * Implement **State Persistence** second (save state to DB on run completion).
    * Add the **Simulation Gate** to prevent persistence during simulation runs.
