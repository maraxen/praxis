# web-client File Splitting Candidates Report

This report identifies the best candidates for splitting based on line count and architectural complexity within the `web-client` application.

## Top Candidates Summary

| File Path | Lines | Potential Splitting Strategy |
| :--- | :--- | :--- |
| `src/app/features/run-protocol/run-protocol.component.ts` | 1506 | Extract compatibility logic, simulation configuration, and wizard state management. Split into sub-components for wizard steps. |
| `src/app/features/playground/playground.component.ts` | 1169 | Extract Python code generation logic and JupyterLite communication protocol to dedicated services. |
| `src/app/features/data/data-visualization.component.ts` | 932 | Separate table view logic from chart visualization. Extract data models and mock data generation. |
| `src/app/features/run-protocol/components/guided-setup/guided-setup.component.ts` | 921 | Split into smaller step-specific components. |
| `src/app/shared/components/deck-view/deck-view.component.ts` | 871 | Decompose complex SVG/canvas rendering logic into smaller, focused components. |
| `src/app/core/services/hardware-discovery.service.ts` | 858 | Extract device definitions (`KNOWN_DEVICES`) and interface models to separate files. |
| `src/app/core/db/async-repositories.ts` | 837 | **High Priority Architectural Split**: Move each repository class (e.g., `AsyncProtocolRunRepository`) into its own file in a `repositories/` directory. |
| `src/app/shared/components/well-selector-dialog/well-selector-dialog.component.ts` | 835 | Refactor interaction logic into sub-components for specific plate types or selection modes. |

---

## Detailed Analysis & Recommendations

### 1. Unified Run Protocol Wizard (`run-protocol.component.ts`)
*   **Issues**: This file is massive because it handles the entire "Run Protocol" flow, including protocol selection, machine compatibility checks, simulation template generation, and wizard navigation.
*   **Recommendation**:
    *   Move `FilterOption` and `FilterCategory` to `models.ts`.
    *   Extract the compatibility check logic (currently ~120 lines in `loadCompatibility`) into a `ProtocolCompatibilityService`.
    *   Extract simulation template logic into a `SimulationTemplateService`.

### 2. JupyterLite Playground (`playground.component.ts`)
*   **Issues**: Contains heavy boilerplate for JupyterLite integration and substantial logic for generating Python code strings for machine/resource injection.
*   **Recommendation**:
    *   Create a `PythonCodeGeneratorService` to house `generateMachineCode` and `generateResourceCode`.
    *   Move JupyterLite URL construction and theme sync logic to a utility or localized service.

### 3. Database Repositories (`async-repositories.ts`)
*   **Issues**: This file currently houses nearly the entire async database layer. It violates the single responsibility principle at the file level.
*   **Recommendation**:
    *   This is the "cleanest" win. Move each class (`AsyncProtocolRunRepository`, `AsyncParameterRepository`, etc.) to individual files.
    *   This improves modularity and makes it easier to find/update specific data access logic.

### 4. Data Visualization (`data-visualization.component.ts`)
*   **Issues**: Mixes data table management with complex chart rendering (likely via Plotly or similar).
*   **Recommendation**:
    *   Split into `RunDataTableComponent` and `RunChartsComponent`.
    *   Move `MockRun` and `TransferDataPoint` interfaces to a localized `models.ts`.

### 5. Hardware Discovery (`hardware-discovery.service.ts`)
*   **Issues**: Contains a large constant `KNOWN_DEVICES` which accounts for a significant portion of the file length and is likely to grow.
*   **Recommendation**:
    *   Move `KNOWN_DEVICES` to `src/app/core/services/hardware-definitions.ts`.
    *   Extract discovery models (interfaces) to `hardware-discovery.models.ts`.
