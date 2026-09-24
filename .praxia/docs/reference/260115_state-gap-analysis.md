---
title: 'State Inspection & Simulation Reporting Gap Analysis'
---

# State Inspection & Simulation Reporting Gap Analysis

**Date:** 2026-01-15
**Goal:** Identify why "STATE INSPECTION and simulation reporting still lacks what i have specified".

## 1. Executive Summary

The analysis confirms a critical gap in both backend state emission and frontend visualization. While the architecture supports state tracking, the **real-time connection** between the running protocol and the user interface is missing for key physical states (liquid levels, tip presence).

| Component | Status | Critical Gap |
| :--- | :--- | :--- |
| **Backend Emission** | 🔴 Incomplete | `well_state_update` is ONLY emitted by `MockTelemetryService`. Real `WorkcellRuntime` executions do not broadcast state changes to the WebSocket. |
| **Frontend Monitor** | 🔴 Incomplete | `ExecutionMonitor` dashboard and `RunDetail` view do NOT utilize `DeckViewComponent`. Users have no spatial visualization of the deck. |
| **Data Availability** | 🟡 Partial | State is saved to DB (`latest_state_json`) but not pushed to the client in real-time. |

---

## 2. Detailed Technical Findings

### 2.1 Backend Emission Gap

**Current Behavior:**

- `praxis/backend/api/websockets.py` serves the execution WebSocket.
- It polls `ProtocolRun` status and logs.
- **CRITICAL**: It attempts to send `well_state_update` **only if** `mock_telemetry_service` is active.
- There is NO logic to fetch or subscribe to `WorkcellRuntime` state updates for real hardware or physics-based simulation runs.

**Missing Implementation:**

- `WorkcellRuntime` needs to broadcast state changes (likely via an EventBus or direct hook) when `serialize_all_state()` changes.
- `api/websockets.py` must subscribe to these real events instead of relying solely on `MockTelemetryService`.

### 2.2 Frontend Visualization Gap

**Current Behavior:**

- `ExecutionMonitorComponent` displays:
  - Active Runs List (`ActiveRunsPanelComponent`)
  - Run History (`RunHistoryTableComponent`)
  - Statistics (`RunStatsPanelComponent`)
- `RunDetailComponent` displays:
  - Timeline (`StateHistoryTimelineComponent`)
  - State Inspector (`StateInspectorComponent`) -> Textual/JSON diffs only.
  - Logs.

**Missing Implementation:**

- `DeckViewComponent` (which is fully capable of visualizing liquid levels and tips) is **not used** in any of these components.
- The user sees a text log or JSON tree, but not the physical deck state.

### 2.3 State Consumption Gap

- `ExecutionService` (Frontend) is already implemented to handle `well_state_update` messages and update a `wellState` signal.
- **Gap**: This signal is unused by the Monitor UI because `DeckView` is missing from the template.

---

## 3. Recommendations

### Phase 1: Enable Real-Time State Emission (Backend)

1. **Event Broadcasting**: Modify `WorkcellRuntime` (specifically `StateSyncMixin`) to emit a `WORKCELL_STATE_UPDATE` event whenever state is updated (not just DB writes).
2. **WebSocket Integration**: Update `orchestrator` or `websockets.py` to listen for these events and broadcast `well_state_update` frames to connected clients.

### Phase 2: Integrate Deck Visualization (Frontend)

1. **Add DeckView**: Insert `<app-deck-view>` into `RunDetailComponent` (perhaps in a new "Live View" tab).
2. **Connect State**: Bind `[state]="executionService.currentRun().wellState"` to the DeckView.
3. **Visualization Mode**: Ensure `DeckView` can handle the "compressed bitmask" format if it doesn't already (currently `DeckView` logic seems compat, but needs verification).

### Phase 3: Enhance Simulation Reporting

1. **Report Generation**: Use the captured state history (which is currently viewed in `StateInspector`) to generate a visual PDF/HTML report post-run, possibly re-using `DeckView` logic for "snapshots" at critical steps.

---

## 4. Conclusion

The user's observation is correct. The system simulates execution and tracks state in the DB, but **drops the ball** on the last mile: delivering that state to the user's eyeballs in real-time.
