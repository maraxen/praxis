---
title: 'Machine Simulation Architecture Audit'
---

# Machine Simulation Architecture Audit

**Date:** 2026-01-15
**Status:** 🔴 Critical Architecture Gaps Identified

## 1. Executive Summary

The current utilization of "Simulated" machines is rigid and architecturally flawed. While the Frontend (`MachineDialogComponent`) presents a UI for selecting a "Frontend" (e.g. LiquidHandler) and a "Backend" (e.g. Simulator/Chatterbox), the Backend (`WorkcellRuntime`) lacks the mechanism to honor this selection. Furthermore, a critical mismatch in the usage of "Fully Qualified Name" (FQN) between the database and the runtime prevents user-created machines from being instantiated by the python backend.

## 2. Critical Findings

### 2.1. FQN Usage Mismatch (Crash Risk)

* **Database/Frontend**: Treats `Machine.fqn` as a unique **Instance Identifier** (e.g., `machines.user.ot2_1234`).
* **Backend (`WorkcellRuntime`)**: Treats `Machine.fqn` as a **Python Class Path** (e.g., `pylabrobot.liquid_handling.LiquidHandler`).
* **Impact**: Any user-created machine (and most seeded default assets) will cause `WorkcellRuntime` to crash during acquisition with an `ImportError` because it attempts to import `machines.user...`.

### 2.2. Missing Backend Instantiation Logic

* **Current Logic**: `WorkcellRuntime.initialize_machine` simply imports the class specified by `machine.fqn` and instantiates it with `**properties_json`.

    ```python
    target_class = get_class_from_fqn(machine_model.fqn)
    machine_instance = target_class(**valid_init_params)
    ```

* **The Gap**: optional properties like `backend` (e.g., for `LiquidHandler`) require a **constructed Python Object** (e.g., `ChatterboxBackend()`), not a dictionary or string. The runtime currently has no logic to:
    1. Read the selected "Backend Driver" FQN from configuration.
    2. Instantiate that Backend class.
    3. Pass it to the Frontend class constructor.
* **Impact**: It is currently impossible to instantiate a machine with a specific backend (like a Simulator) unless the Machine class itself is a specialized subclass that hardcodes the backend (which defeats the purpose of "Configurable Backends").

### 2.3. Rigid Seeding Logic

* **Frontend**: `SqliteService` auto-seeds ~70 machines, one for every definition in `PLR_MACHINE_DEFINITIONS`.
* **Logic**: It explicitly hardcodes "Simulated" vs "Native" checks but fundamentally creates specific asset instances for every theoretical machine type, cluttering the inventory.

### 2.4. Data Model Coupling

* **Frontend**: `MachineDialogComponent` stores the backend selection in `connection_info.plr_backend` or `simulation_backend_name`.
* **Backend**: `Machine` model has `simulation_backend_name` and `connection_info`, but `WorkcellRuntime` ignores `simulation_backend_name` during instantiation.

## 3. Architecture Proposal: Configurable Backends

To support "Configurable Backends" on the fly, the architecture must change:

1. **Strict Separation of Type vs Instance**:
    * `Machine.fqn` -> Instance ID (keep as is).
    * `MachineDefinition.fqn` -> Frontend Class Path (e.g., `pylabrobot.liquid_handling.LiquidHandler`).
    * `Machine.machine_definition` -> Link to the Class Path.
2. **Runtime Factory Logic**:
    * `WorkcellRuntime` must look up the `MachineDefinition.fqn` to know *what* to instantiate.
    * `WorkcellRuntime` must inspect `Machine.connection_info` (or `simulation_backend_name`) to instantiate the correct **Backend Driver**.
    * `WorkcellRuntime` must inject the Backend instance into the Machine constructor.

## 4. Remediation Plan

1. **Update WorkcellRuntime**: Refactor `initialize_machine` to separate Frontend Class resolution from Instance config.
2. **Implement Backend Factory**: Add logic to instantiate `StarletBackend`, `OT2Backend`, `ChatterboxBackend` etc., based on `connection_info`.
3. **Fix Database Seeding**: Stop seeding instances; seed only Definitions. Allow users to "Add Machine" -> "Simulated OT-2" which creates 1 instance correctly.
