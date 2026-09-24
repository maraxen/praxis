---
title: 'AUDIT-01: Run Protocol & Wizard'
---

# AUDIT-01: Run Protocol & Wizard

This audit analyzes the user journey, component architecture, and test coverage for the "Run Protocol" feature in the Praxis web client.

## 1. Component Map

The "Run Protocol" feature is a multi-step wizard composed of several modular components and services.

| File Path | Purpose | Dependencies | Services Injected |
|---|---|---|---|
| `run-protocol.component.ts` | Main container for the wizard stepper. Manages overall state and flow between steps. | `MachineSelectionComponent`, `ParameterConfigComponent`, `DeckSetupWizardComponent`, `ProtocolCardComponent`, `ProtocolSummaryComponent`, `GuidedSetupComponent` | `ProtocolService`, `ExecutionService`, `DeckGeneratorService`, `WizardStateService`, `ModeService`, `AssetService`, `AppStore` |
| `components/deck-setup-wizard/deck-setup-wizard.component.ts` | A 3-step sub-wizard for guided deck layout configuration. | `CarrierPlacementStepComponent`, `ResourcePlacementStepComponent`, `VerificationStepComponent`, `DeckViewComponent`, `SetupInstructionsComponent`, `RequirementsPanelComponent` | `WizardStateService` |
| `components/guided-setup/guided-setup.component.ts` | Component for assigning inventory items to protocol asset requirements. | `PraxisAutocompleteComponent` | `AssetService` |
| `components/machine-selection/machine-selection.component.ts` | Displays a grid of compatible machines and handles user selection. | `MachineCardComponent` | - |
| `components/parameter-config/parameter-config.component.ts` | Dynamically generates a form for user-configurable protocol parameters. | - | - |
| `components/protocol-card/protocol-card.component.ts` | A card component to display a protocol in the selection list. | - | - |
| `components/protocol-summary/protocol-summary.component.ts` | Displays a summary of the selected protocol and configuration for final review. | - | - |
| `live-dashboard.component.ts` | Displays real-time progress, logs, and telemetry for a running protocol. | `LogViewerComponent`, `StateVisualizerComponent` | `ExecutionService`, `ActivatedRoute` |
| `services/execution.service.ts` | Handles the logic for starting, monitoring, and stopping protocol runs in both browser and production modes. Manages WebSocket communication. | - | `ModeService`, `PythonRuntimeService`, `SqliteService`, `ApiWrapperService`, `WizardStateService` |
| `services/wizard-state.service.ts` | Manages the state of the deck setup sub-wizard, including carrier and resource placements. | - | `CarrierInferenceService`, `DeckCatalogService`, `ConsumableAssignmentService` |
| `services/deck-catalog.service.ts` | Provides information about deck layouts for different machines. | - | - |
| `services/deck-generator.service.ts` | Generates deck layouts based on protocol requirements. | - | `DeckCatalogService` |
| `services/carrier-inference.service.ts` | Infers carrier and resource requirements from a protocol definition. | - | - |
| `services/consumable-assignment.service.ts` | Matches required consumables with available inventory. | - | `AssetService` |

## 2. User Flow Diagram



## 3. Gap/Limitation List

This section details identified gaps and limitations in the current implementation, categorized by severity.

| Severity | Category | Issue | File Path & Line Reference |
|---|---|---|---|
| 🔴 **Blocker** | Validation | No validation to prevent starting a physical run with a simulated machine. |  (The  computed property exists, but the 'Start Execution' button is not always disabled by it) |
| 🟠 **Major** | Error Handling | No visual feedback or error handling if the WebSocket connection fails during a run. The UI would just stop updating. |  (The  method has a , but it doesn't propagate the error state to the UI) |
| 🟠 **Major** | UX | The user can get stuck in the deck setup wizard if they make a mistake, as there is no 'reset' or 'clear' button for placements. |  |
| 🟡 **Minor** | UX | Parameters in the  component are not grouped or organized, which could be confusing for complex protocols. |  |
| 🟡 **Minor** | Validation | No client-side validation for parameter inputs (e.g., min/max values from protocol constraints). |  (The component creates the form but doesn't apply all constraints from the protocol definition) |
| 🟡 **Minor** | Accessibility | Keyboard navigation in the machine selection and protocol selection grids is not implemented. | ,  |

