# State Inspection & Simulation Reporting Gap Analysis

**Date:** 2026-01-15
**Scope:** Backend Execution vs. Frontend "State Inspector" Expectations

## 1. Executive Summary

The "State Inspection" and "Time Travel" features currently visible in the Frontend (`RunDetailComponent`, `StateInspectorComponent`) are **not supported by the current Backend architecture**. These features rely on granular `state_before` and `state_after` snapshots for each operation, which are currently only generated in "Browser Mode" (via Pyodide/SqliteService).

The Backend emits real-time state updates for the *current* state via WebSockets, but it does **not persist** the incremental state history required for post-run analysis or step-by-step replay.

## 2. Detailed Gaps

### 2.1. Missing "State History" API
- **Frontend Expectation:** Calls `SimulationResultsService.getStateHistory(runId)`.
- **Backend Reality:** No such endpoint exists. `SimulationResultsService` logs a warning and returns `null` in API mode.
- **Impact:** The "Operation Timeline" and "State Inspector" tabs in the Run Detail view are empty for backend-executed runs.

### 2.2. Lack of Granular State Persistence
- **Frontend Requirement:** Needs `OperationStateSnapshot` (state before/after each step).
- **Backend Model:** `FunctionCallLog` only stores `input_args_json` and `return_value_json`.
- **Gap:** The Backend orchestrator does not capture or store the full `Workcell` state snapshot at the beginning and end of each function call.
- **Complexity:** Storing full state snapshots (JSON) for every operation in a long protocol could be storage-intensive.

### 2.3. Real-Time Timeline Updates
- **Frontend Expectation:** The "Operation Timeline" should ideally update in real-time.
- **Backend Reality:** WebSocket sends `well_state_update` (current state) and `status` updates, but does not emit `operation_complete` events with diffs/snapshots.
- **Impact:** The timeline is static and only available (theoretically) after the run, whereas the Deck View is live.

### 2.4. Data Structure Mismatch (Potential)
- **Frontend `DeckViewComponent`:** Expects `volumes` (array) or `liquid_mask` (hex bitmask), and `tips` (array) or `tip_mask` (hex bitmask).
- **Backend `WorkcellRuntime`:** Emits `serialize_state()` from PyLabRobot objects.
- **Gap:** Standard PLR `serialize_state()` often returns `liquids` (list of tuples) rather than flat `volumes` arrays.
- **Verification Needed:** Confirm if `ExecutionService` or `web_bridge.py` transforms standard PLR state into the `wellState` format expected by the UI.

## 3. Recommendations

### 3.1. Implement "State Capture" Mode
Modify `ExecutionMixin` to optionally capture state snapshots during execution if a flag (`trace_state=True`) is set.
- **Action:** Add `state_before_json` and `state_after_json` (nullable) to `FunctionCallLog` table.
- **Action:** In `_execute_protocol_main_logic`, capture `workcell.serialize_all_state()` before and after `callable_protocol_func` (or hook into `ProtocolFunctionWrapper` for granular steps).

### 3.2. Create State History Endpoint
Implement `GET /api/v1/protocols/runs/{id}/state-history` in the backend.
- **Logic:** Query `FunctionCallLog` items for the run.
- **Transform:** Map logs to `StateHistory` / `OperationStateSnapshot` models.

### 3.3. Optimize Storage
Instead of storing full state, store **State Deltas** (diffs) in the database to save space, or only store snapshots for "significant" operations (e.g., liquid handling, not just calculations).

### 3.4. Align WebSocket Messages
Ensure the WebSocket `well_state_update` payload strictly matches the `DeckViewComponent`'s expected interface, or implement a transformer in `ExecutionService` to normalize PLR state to UI state.
