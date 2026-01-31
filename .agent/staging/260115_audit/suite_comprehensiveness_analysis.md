# Test Suite Comprehensiveness Analysis

**Date:** 2026-01-15
**Status:** Evaluation Complete
**Verdict:** **Strong Core Coverage (80%)**, with critical gaps in Post-Run Analysis and Dashboard Monitoring.

## 1. Executive Summary

The current interaction test suite (`e2e/specs/interactions/` + `e2e/specs/`) successfully covers the "Critical Path" of the application: Onboarding, Asset Creation, Protocol Setup, Execution, and Failure Handling.

However, to be "Truly Comprehensive" per the "Deep Reconnaissance" standard, two major user-facing pillars remain under-tested:

1. **State Inspection (Time Travel)**: We verify the detailed view opens, but we do **not** verify that interacting with the timeline actually updates the deck state (Deep Verification).
2. **Workcell Dashboard (Standalone)**: We verify the Deck View *during* a run, but we do **not** verify the standalone Workcell Explorer (checking machine status/deck view when idle).

## 2. Coverage Heatmap

| Feature | Scenario (Test Plan v1) | Coverage Status | Notes |
| :--- | :--- | :--- | :--- |
| **Onboarding** | T1: Splash, DB Init | 🟢 **Covered** | `01-onboarding.spec.ts` |
| **Asset Mgmt** | T2, T3: Create Machine/Resource | 🟢 **Covered** | `02-asset-management.spec.ts`, `interactions/03-asset-forms.spec.ts` |
| **Protocol Setup** | T4, T5: Selection, Wizard | 🟢 **Covered** | `03-protocol-execution.spec.ts` |
| **Execution** | T6: Run, Logs, Completion | 🟢 **Covered** | `03-protocol-execution.spec.ts`, `interactions/01-execution-controls.spec.ts` |
| **Resilience** | T10: Errors, Persistence | 🟢 **Covered** | `interactions/04-error-handling.spec.ts`, `04-browser-persistence.spec.ts` |
| **Live View** | T6/T8: Real-time Deck View | 🟡 **Partial** | `interactions/02-deck-view.spec.ts` tests click/hover, but only during runs. |
| **State Inspection** | T7: History, Time Travel | 🔴 **Missing Deep Check** | Tests open detail page but **do not** interact with timeline steps or verify state changes. |
| **Workcell Dash** | T8: Explorer, Status Badges | 🔴 **Missing** | No test for the main Workcell Dashboard (Machine Explorer). |

## 3. Gap Analysis

### 3.1. Weakness: State Inspection (Time Travel)

**The Risk:** This is a complex feature involving huge state diffs. If the frontend fails to rehydrate the state correctly when clicking a timeline step, the user sees incorrect data. Currently, we only check that the page loads, not that the data changes.
**Missing Test:** `interactions/05-state-inspection.spec.ts`

- Open completed run.
- Assert initial state (Time 0).
- Click specific step (Step 5: Aspirate).
- Assert Deck View updates (e.g., "Well A1 volume decreases").

### 3.2. Weakness: Workcell Dashboard (Standalone)

**The Risk:** Users spend time monitoring their lab here. If the machine list is empty or the "Deck View" fails to synthesize for simulated machines (a known complex logic), the feature is broken.
**Missing Test:** `interactions/06-workcell-dashboard.spec.ts`

- Navigate to `/app/workcell`.
- Select a Simulated Machine.
- Verify "Live/Idle" badge.
- Verify Deck View renders even when machine is idle.

## 4. Recommendations

To achieve 100% "True Comprehensiveness", I recommend a **Phase 2 Implementation**:

1. **Enhance `ExecutionMonitorPage` Object**:
    - Add `clickTimelineStep(index: number)`
    - Add `getDeckWellState(wellName: string)`
2. **Create `WorkcellPage` Object**:
    - Abstractions for Sidebar, Machine List, and Main View.
3. **Implement 2 New Interaction Tests**:
    - `interactions/05-state-inspection.spec.ts`
    - `interactions/06-workcell-dashboard.spec.ts`

**Decision Point:**

- **Option A:** Mark current suite as "Completed MVP" and log these gaps as future chores.
- **Option B:** Proceed immediately to implement these 2 missing tests to certify strictly "Comprehensive".
