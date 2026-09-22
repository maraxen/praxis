# Investigation Report: Per-Machine Argument Configuration

**Task ID:** 260121152037
**Status:** COMPLETE
**Finding:** MISSING_FEATURE

## Summary

The investigation into the "Run Protocol" wizard confirmed that there is currently no mechanism for users to configure machine-specific parameters (e.g., ports, connection settings, simulation options) during the machine selection step.

While the backend and data models (`Machine`, `MachineDefinition`) support these configurations via `backend_config` and `connection_config` fields, the frontend UI does not expose these fields to the user.

## Detailed Findings

### 1. Machine Selection Flow

- In `RunProtocolComponent`, the **Select Machine** step uses `MachineSelectionComponent`.
- When a machine is selected:
  - If it's a **Template**, it opens `SimulationConfigDialogComponent`.
  - If it's an **Existing Machine**, it simply sets the selection and allows the user to click "Continue".
- There is no "Configure" step or dialog for existing machines.

### 2. Dialog Limitations

- `SimulationConfigDialogComponent` is currently restricted to only two fields:
  - `name` (Instance Name)
  - `simulation_backend_name` (e.g., "Chatterbox", "Simulator")
- It ignores the `connection_config` schema available in the `MachineBackendDefinition`.

### 3. Model & Service Support

- **Models:** Files like `asset.models.ts` and `schema.ts` define `backend_config` (Record) and `capabilities_config` (JSON) which are intended for this purpose.
- **Services:** `AssetService` provides methods to create and update machines with these configurations.
- **Execution:** `ExecutionService` (browser mode) already looks for `port_id` and `baudrate` in the `backend_config` of the resolved machine asset:

  ```typescript
  // From execution.service.ts
  machineConfig = {
    backend_fqn: definition.fqn,
    port_id: instance?.backend_config?.port_id,
    baudrate: instance?.backend_config?.baudrate,
    is_simulated: definition.is_simulation_override || false
  };
  ```

  Since the UI never populates `backend_config`, these values are always `undefined`.

## Conclusion

The issue is a **MISSING_FEATURE**. The infrastructure for machine configuration exists in the data layer but is not yet wired up in the Run Protocol wizard's UI.

## Recommended Next Steps

1. **Implement Dynamic Form:** Create a component that renders a form based on `MachineCapabilityConfigSchema`.
2. **Expand Simulation Dialog:** Update `SimulationConfigDialogComponent` to include the dynamic form for backend/connection settings.
3. **Add Edit Capability to Wizard:** Allow users to "Configure" an existing machine selection in the wizard step if they need to change connection parameters (e.g., swapping a serial port).
4. **Execution Mapping:** Ensure that when a run is started, the specific `backend_config` for that machine instance is correctly passed to the execution environment.
