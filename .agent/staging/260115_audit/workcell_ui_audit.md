# Workcell Interface & Deck View Audit

**Date:** 2026-01-15
**Feature:** Workcell Dashboard / Machine Focus View

## 1. Executive Summary

The "Deck View" is currently disconnected in the Workcell Interface because the frontend data model expects a `plr_definition` (PyLabRobot Resource tree) on the `Machine` object, but this property is never populated by the `WorkcellViewService` or `AssetService`. Additionally, the dashboard lacks a "Global Deck View" that would show the entire workcell layout.

## 2. Component Hierarchy

- **WorkcellDashboardComponent**
  - **WorkcellExplorerComponent** (Sidebar)
  - **Main Content Switcher**:
    - `viewMode === 'grid'`: **MachineCardComponent** (Array)
    - `viewMode === 'list'`: **MachineCardMiniComponent** (Array)
    - `viewMode === 'focus'`: **MachineFocusViewComponent** (Selected Machine)
      - **DeckViewComponent** (The missing visual)
      - **ProtocolProgressPanelComponent**
      - **ResourceInspectorPanelComponent**

## 3. Rendering Logic & Gaps

### 3.1. `MachineFocusViewComponent` Condition
```html
@if (machine.plr_definition) {
  <app-deck-view [resource]="machine.plr_definition" ... />
} @else {
  <mat-icon>grid_off</mat-icon>
  <p>No deck definition available</p>
}
```
- **Issue**: `machine.plr_definition` is undefined for simulated machines (and likely all machines unless manually injected).
- **Simulated Machines**: While they use `is_simulation_override: True`, they do not automatically trigger a "Template" or "Static" deck layout in the UI.

### 3.2. Data Flow Gaps
- **`WorkcellViewService`**: Loads machines and workcells via `AssetService`.
  - **Gap**: It copies properties but does **not** generate or fetch `plr_definition`.
- **`AssetService`**: 
  - **Gap**: Maps API/SQLite results to `Machine`. The backend `Machine` model does not contain `plr_definition`.
- **Backend `Machine` model**:
  - **Gap**: `Machine` entity has `deck_child_definition` and `machine_definition` pointers, but no materialized `plr_definition` JSON.

## 4. Proposed Fixes

### 4.1. Immediate Fix (Focus View)
In `WorkcellViewService`, if a machine lacks `plr_definition` but has a `machine_category` (e.g., 'HamiltonSTAR'), use `DeckGeneratorService` to create a default "Background Deck" for visualization.

### 4.2. Enhancing simulated Machines
Ensure that when a simulated machine is "created" (from turn 01), it either:
1.  Stores a static `plr_definition` in its JSON properties.
2.  Provides enough metadata for the UI to reconstruct the deck layout dynamically.

### 4.3. Workcell "Global View"
The `WorkcellDashboard` currently only shows individual machines. 
- **Proposal**: Add a `viewMode === 'workcell'` that displays all machines in a single 2D space, using their `location` coordinates.

## 5. Verification Items for Plan (05 P)
- [ ] Verify `Machine` interface has `plr_definition` field (Confirmed).
- [ ] Implement `plr_definition` population in `WorkcellViewService`.
- [ ] Add "Global Deck" button to dashboard.