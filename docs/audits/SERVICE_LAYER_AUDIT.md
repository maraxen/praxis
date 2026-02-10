# Service Layer Audit

## Objective
This document provides a comprehensive audit of the Angular services in the `praxis/web-client` application, focusing on service inventory, dependency analysis, circular dependency risks, and provider patterns.

## Scope
The audit covers all services located in `praxis/web-client/src/app/core/services/` and `praxis/web-client/src/app/features/*/services/`.

## 1. Service Inventory

### Core Services (`core/services/`)

| Service Name                  | Dependencies                                                                                                                              | Provider Pattern        | Notes                                                               |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ------------------------------------------------------------------- |
| `ApiConfigService`            | `OpenAPI` (from generated client)                                                                                                         | `providedIn: 'root'`    | Singleton. Configures the base path for API calls.                |
| `ApiWrapperService`           | `ApiError` (from generated client)                                                                                                        | `providedIn: 'root'`    | Singleton. Wraps `CancelablePromise` in RxJS `Observable`.          |
| `BrowserService`              | `WINDOW` injection token                                                                                                                  | `providedIn: 'root'`    | Singleton. Abstracts browser-specific APIs for testability.     |
| `CommandRegistryService`      | `signal` (from `@angular/core`)                                                                                                           | `providedIn: 'root'`    | Singleton. Manages a global registry of commands.                   |
| `CustomIconRegistryService`   | `MatIconRegistry`, `DomSanitizer`                                                                                                         | `providedIn: 'root'`    | Singleton. Registers custom SVG icons.                              |
| `HardwareDiscoveryService`    | `ApiWrapperService`                                                                                                                       | `providedIn: 'root'`    | Singleton. Manages WebSerial/WebUSB hardware discovery.             |
| `InteractionService`          | `MatDialog`                                                                                                                               | `providedIn: 'root'`    | Singleton. Handles user interaction dialogs.                        |
| `KeyboardService`             | `MatDialog`, `Router`, `CommandRegistryService`, `RendererFactory2`, `AppStore`                                                             | `providedIn: 'root'`    | Singleton. Manages global keyboard shortcuts.                       |
| `LocalStorageAdapter`         | `BehaviorSubject` (from `rxjs`)                                                                                                           | `providedIn: 'root'`    | Singleton. Provides a localStorage-based persistence layer.       |
| `MachineDefinitionService`    | (none)                                                                                                                                    | `providedIn: 'root'`    | Singleton. Provides machine method definitions.                     |
| `MockTelemetryService`        | `interval` (from `rxjs`)                                                                                                                  | `providedIn: 'root'`    | Singleton. Provides mock telemetry data.                          |
| `ModeService`                 | `environment` (from `@env/environment`)                                                                                                   | `providedIn: 'root'`    | Singleton. Detects and manages application mode.                    |
| `OnboardingService`           | `LocalStorageAdapter`, `BrowserService`                                                                                                   | `providedIn: 'root'`    | Singleton. Manages user onboarding state.                         |
| `PlaygroundRuntimeService`    | `ApiWrapperService`, `webSocket` (from `rxjs/webSocket`)                                                                                  | `providedIn: 'root'`    | Singleton. Manages the backend Python REPL connection.              |
| `PythonRuntimeService`        | `HardwareDiscoveryService`, `InteractionService`                                                                                          | `providedIn: 'root'`    | Singleton. Manages the in-browser Pyodide runtime.                  |
| `SerialManagerService`        | `BroadcastChannel`                                                                                                                        | `providedIn: 'root'`    | Singleton. Manages serial connections for the Pyodide worker.       |
| `SqliteService`               | `SqliteOpfsService`                                                                                                                       | `providedIn: 'root'`    | Singleton. Manages the SQLite database via OPFS.                    |
| `TelemetryService`            | (none)                                                                                                                                    | `providedIn: 'root'`    | Singleton. (Placeholder)                                            |
| `TutorialService`             | (none)                                                                                                                                    | `providedIn: 'root'`    | Singleton. Manages tutorial state.                                  |
| `WebBridge`                   | (none)                                                                                                                                    | (not a service)         | Utility for Pyodide-browser communication.                          |

### Feature Services (`features/*/services/`)

| Service Name                      | Dependencies                                     | Provider Pattern     | Feature Area        |
| --------------------------------- | ------------------------------------------------ | -------------------- | ------------------- |
| `AssetSearchService`              | (none)                                           | `providedIn: 'root'` | `assets`            |
| `AssetService`                    | `ApiWrapperService`, `SqliteService`, `ModeService` | `providedIn: 'root'` | `assets`            |
| `AuthService`                     | `KeycloakService`                                | `providedIn: 'root'` | `auth`              |
| `RunHistoryService`               | `SqliteService`, `ModeService`                   | `providedIn: 'root'` | `execution-monitor` |
| `DirectControlKernelService`      | `PythonRuntimeService`                           | `providedIn: 'root'` | `playground`        |
| `JupyterChannelService`           | (none)                                           | `providedIn: 'root'` | `playground`        |
| `PlaygroundAssetService`          | `AssetService`                                   | `providedIn: 'root'` | `playground`        |
| `PlaygroundJupyterliteService`    | (none)                                           | `providedIn: 'root'` | `playground`        |
| `ProtocolService`                 | `ApiWrapperService`, `SqliteService`, `ModeService` | `providedIn: 'root'` | `protocols`         |
| `CarrierInferenceService`         | `DeckCatalogService`                             | `providedIn: 'root'` | `run-protocol`      |
| `ConsumableAssignmentService`     | `SqliteService`                                  | `providedIn: 'root'` | `run-protocol`      |
| `DeckCatalogService`              | `SqliteService`                                  | `providedIn: 'root'` | `run-protocol`      |
| `DeckConstraintService`           | (none)                                           | `providedIn: 'root'` | `run-protocol`      |
| `DeckGeneratorService`            | `DeckCatalogService`, `AssetService`, `CarrierInferenceService` | `providedIn: 'root'` | `run-protocol`      |
| `ExecutionService`                | `ModeService`, `PythonRuntimeService`, `SqliteService`, `HttpClient`, `WizardStateService`, `ApiWrapperService` | `providedIn: 'root'` | `run-protocol`      |
| `WizardStateService`              | `CarrierInferenceService`, `DeckCatalogService`, `ConsumableAssignmentService` | `providedIn: 'root'` | `run-protocol`      |
| `WorkcellViewService`             | `AssetService`, `DeckCatalogService`             | `providedIn: 'root'` | `workcell`          |

## 2. Dependency Analysis

The service layer is well-structured, with a clear distinction between core and feature services. The dependency flow is generally unidirectional, with feature services depending on core services, and core services having minimal cross-dependencies.

- **Data Access**: `SqliteService` and `ApiWrapperService` are the primary data access points. `ModeService` is used to switch between them.
- **State Management**: State is managed within individual services using Angular Signals and RxJS `BehaviorSubject`.
- **Cross-Feature Communication**: Communication between features is handled by core services (e.g., `CommandRegistryService`) or by routing.

## 3. Circular Dependency Risks

No direct circular dependencies were identified at the constructor injection level. The use of `providedIn: 'root'` for all services ensures that they are singletons and that Angular's dependency injection system would throw an error on startup if a direct circular dependency were introduced.

However, it is still possible to create circular dependencies at runtime through method calls. For example, if `ServiceA` calls a method on `ServiceB`, and `ServiceB` calls a method on `ServiceA`, a circular dependency could occur. This is not currently the case, but it is a risk to be aware of as the application grows.

## 4. Provider Patterns

All services in the audited scope use the `providedIn: 'root'` provider pattern. This is the recommended approach for providing services in Angular, as it makes services tree-shakable and ensures that they are singletons across the application.

This pattern is used correctly in all cases, and there are no instances of services being provided in component-level or module-level injectors. This consistency simplifies the dependency graph and makes the application easier to reason about.

## 5. Conclusion

The service layer of the `praxis/web-client` application is well-architected and follows modern Angular best practices. The use of `providedIn: 'root'` for all services, a clear separation between core and feature services, and a unidirectional dependency flow all contribute to a robust and maintainable codebase. No immediate action is required, but developers should remain vigilant about introducing circular dependencies through method calls as the application evolves.
