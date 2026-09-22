# Simulation Selection Investigation

## Button Location

- **File**: `praxis/web-client/src/app/features/run-protocol/components/simulation-config-dialog/simulation-config-dialog.component.ts`
- **Line**: 74
- **Text**: "Create Simulation"

## Logic Trace

1. **Click Handler**: `(click)="confirm()"` calls `confirm()` in `SimulationConfigDialogComponent`.
2. **Dialog Close**: `confirm()` verifies form validity and calls `this.dialogRef.close(this.form.value)`.
3. **Parent Component Handling**:
   - `RunProtocolComponent` (in `praxis/web-client/src/app/features/run-protocol/run-protocol.component.ts`) opens the dialog via `configureSimulationTemplate`.
   - Subscribes to `dialogRef.afterClosed()`.
   - If result exists, proceeds to create ephemeral machine.

## Findings

### 1. Backend Matching Logic Mismatch (High Probability)

In `configureSimulationTemplate`, the code attempts to find a matching backend definition:

```typescript
const backend = backends.find(b => 
  b.backend_type === 'simulator' && 
  (b.name === result.simulation_backend_name || b.fqn.includes(result.simulation_backend_name.toLowerCase()))
);
```

- **Observed Data**:
  - `result.simulation_backend_name` (from `available_simulation_backends`): typically `pylabrobot.liquid_handling.backends.ChatterboxBackend`.
  - `b.name` (from `PLR_BACKEND_DEFINITIONS`): derived from machine name, e.g., "Simulated Liquid Handler".
  - `b.fqn` (from `PLR_BACKEND_DEFINITIONS`): matches machine FQN, e.g., `praxis.simulated.LiquidHandler`.

- **Result**: The match fails (`backend` is `undefined`) because:
  - "Simulated Liquid Handler" !== "pylabrobot.liquid_handling.backends.ChatterboxBackend"
  - "praxis.simulated.LiquidHandler" does not include "pylabrobot..."

- **Consequence**: `ids.backendId` is `undefined`. While `SqliteService.createMachine` appears to handle missing definition IDs gracefully (by falling back to string-based FQN lookup or defaults), passing `undefined` to the `createMachine` API (if in production mode) or strictly typed internals could cause issues.

### 2. Silent Failure Risk

The `configureSimulationTemplate` method has error handling that logs to console (`console.error('Failed to create simulation machine', err)`), but it does not provide UI feedback. If the observable chain fails (e.g., if `getMachineFrontendDefinitions` throws or returns empty), the user sees no effect.

### 3. Form Validation

The "Create Simulation" button is disabled if `configForm` is invalid.

- Requires `name` and `simulation_backend_name`.
- `simulation_backend_name` options come from `definition.available_simulation_backends`.
- `Simulated Liquid Handler` defines these options, so the form should be valid.

## Recommended Fix

1. **Update Backend Matching Logic**:
   Relax the matching logic in `run-protocol.component.ts` to fallback to any simulator backend if a precise name match isn't found, or update `PLR_BACKEND_DEFINITIONS` to include the specific backend class names as aliases.

2. **UI Feedback**:
   Add a snackbar or alert in the `error` block of `configureSimulationTemplate` to notify the user if creation fails.

3. **Verify Observables**:
   Ensure `getMachineFrontendDefinitions` and `getBackendsForFrontend` are returning data correctly in the browser-mode `SqliteService`.

## Resolution (2026-01-21)

- **Backend Matching Logic Fixed**: Updated `RunProtocolComponent.configureSimulationTemplate` to include an exact match check followed by a fallback to the first available simulator backend for the given machine type.
- **UI Feedback Added**: Integrated `MatSnackBar` to provide real-time feedback when:
  - A compatible simulator backend is not found (fallback warning or error).
  - The simulation machine creation fails (using an error snackbar).
- **Improved Robustness**: Changed `fqn.includes(...)` to `fqn === ...` for exact matching, reducing ambiguity while ensuring fallbacks handle mismatched metadata gracefully.
