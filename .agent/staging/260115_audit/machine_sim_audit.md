# Machine Simulation Architecture Audit & Refactor Proposal

**Status:** Draft / Inspection Complete
**Date:** 2026-01-15
**Author:** Antigravity Agent

## 1. Executive Summary

This document analyzes the current machines simulation architecture and proposes a shift from **"Pre-Seeded Instances"** to a **"Factory Pattern"**. Currently, the application clutters the inventory by auto-generating ~70 simulated machine instances. We will shift to "Definition Placeholders" that allow users to configure simulation traits (backend, deck type) on-the-fly during a protocol run.

## 2. Current State Analysis

### 2.1. The Seeding Problem (`SqliteService`)

The current logic unconditionally iterates through **all** `machine_definitions` and creates a `machines` table entry for each one. This clutters the inventory and restricts flexibility.

### 2.2. Frontend Logic

The `MachineDialogComponent` already supports a robust "Factory" flow for manual machine registration. However, the protocol run selection flow currently lacks a way to configure a simulation from a "Template" (Definition) without it already being in inventory.

## 3. Proposed Changes (Technical Plan)

### 3.1. Stop the Seeding & Cleanup

- **SqliteService**:
  - Disable the machine seeding loop in `seedDefaultAssets`.
  - Implement a migration to delete existing auto-seeded junk:

      ```sql
      DELETE FROM machines WHERE is_simulation_override = 1 AND properties_json LIKE '%"is_default":true%';
      ```

### 3.2. Runtime Simulation Configuration

- **SimulationConfigDialogComponent [NEW]**:
  - A lightweight dialog for "just-in-time" simulation setup.
  - Fields: `simulation_backend_name` (Chatterbox, Simulator), Deck Type selection, and name.
- **MachineSelectionComponent**:
  - Inject "Virtual Templates" for each compatible `MachineDefinition`.
  - Clicking a template opens the configuration dialog instead of selecting an existing instance.
- **RunProtocolComponent**:
  - If a template is configured, call `AssetService.createMachine` to generate a temporary inventory item for the run.

## 4. Verification Plan

### Automated

- **Backend Tests**: Verify `SqliteService` no longer creates machine rows on init.
- **Frontend Tests**: E2E flow for selecting a "Hamilton STAR" placeholder and configuring it.

### Manual

1. Clear browser DB storage.
2. Confirm "Execute Protocol" shows category placeholders but no pre-seeded machines.
3. Successfully start a simulation run using a configured placeholder.
