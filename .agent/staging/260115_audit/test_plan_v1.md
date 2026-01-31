# Interaction Test Plan v1

**Date:** 2026-01-15
**Goal:** Establish a robust suite of interaction tests for critical browser-mode and backend-integrated flows using Playwright and Vitest.

## 1. Tooling & Configuration

### 1.1. Playwright Configuration (`playwright.config.ts`)
- **Default Browser:** Chromium.
- **Mode:** Headless.
- **Parallelism:** Enabled.
- **Base URL:** `http://localhost:4200`.

### 1.2. Directory Structure
- `e2e/specs/interactions/`: New home for complex multi-page interaction tests.
- `e2e/page-objects/`: Shared abstractions for UI elements (refactor existing ones).

## 2. High-Value Test Scenarios (The "Core 10")

| ID | Feature | Scenario | Importance |
|:---|:--------|:---------|:-----------|
| T1 | Onboarding | First-time user sees welcome, clears splash, and lands on dashboard. | High |
| T2 | Machine Creation | User clicks "Add Machine", selects Opentrons STAR, configures name, and sees it in Machine List. | Critical |
| T3 | Resource Creation | User adds a "96 Well Plate", configures it, and verifies it in the Resource Accordion. | High |
| T4 | Protocol Selection | User navigates to Library, selects "Plate Transfer", and enters the Setup Wizard. | Critical |
| T5 | Setup Wizard | User completes parameter entry, machine selection, and deck setup steps. | Critical |
| T6 | Protocol Execution | User starts a run, monitors real-time logs, and sees "COMPLETED" status. | Critical |
| T7 | State Inspection | User clicks a completed run, opens "State Inspector", and clicks timeline steps to see deck changes. | High |
| T8 | Workcell Dashboard | User selects a machine in Workcell, verifies "Deck View" renders, and clicks a well to see details. | Medium |
| T9 | Browser Persistence | User creates an asset, reloads page, and verifies asset still exists (SQLite persistence). | High |
| T10| Failure Monitoring | User executes a protocol that fails, verifies "FAILED" status and error log visibility. | Medium |

## 3. Implementation Priorities

### 3.1. Phase 1: Fix Existing Assets Tests
- Existing `02-asset-management.spec.ts` is likely broken due to the `AddAssetDialog` refactor.
- **Action**: Update `AssetsPage` object to support the new `mat-stepper` based unified dialog.

### 3.2. Phase 2: Live View & Workcell Tests
- Implement **T8** (Workcell Dashboard) to verify that the `plr_definition` synthesis (Turn 05) actually works in the real UI.

### 3.3. Phase 3: Time Travel / State History
- Implement **T7** to verify the new `state-history` API and UI integration (Turn 04).

## 4. Execution Steps (07 E)

1.  Create `e2e/specs/interactions/state-inspection.spec.ts`.
2.  Update `e2e/page-objects/assets.page.ts` to support the new stepper flow.
3.  Add `e2e/specs/interactions/workcell-dashboard.spec.ts`.
4.  Verify all tests pass in Headless Chromium.
