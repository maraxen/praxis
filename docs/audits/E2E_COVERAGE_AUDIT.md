# E2E Spec Coverage Audit

## 1. Spec to Feature Mapping

| Spec File | Feature Module(s) |
| --- | --- |
| `01-onboarding.spec.ts` | `splash`, `home` |
| `02-asset-management.spec.ts` | `assets` |
| `03-protocol-execution.spec.ts` | `protocols`, `run-protocol`, `execution-monitor` |
| `04-browser-persistence.spec.ts` | `assets`, `settings` |
| `asset-inventory.spec.ts` | `assets` |
| `asset-wizard-visual.spec.ts` | `assets` |
| `asset-wizard.spec.ts` | `assets` |
| `browser-export.spec.ts` | `settings` |
| `capture-remaining.spec.ts` | `home`, `protocols` |
| `catalog-workflow.spec.ts` | `playground` |
| `data-visualization.spec.ts` | `data` |
| `deck-setup.spec.ts` | `run-protocol` |
| `execution-browser.spec.ts` | `run-protocol` |
| `functional-asset-selection.spec.ts` | `assets`, `run-protocol` |
| `ghpages-deployment.spec.ts` | `playground`, `run-protocol`, `home`, `splash` |
| `interactions/01-execution-controls.spec.ts` | `execution-monitor`, `run-protocol` |
| `interactions/02-deck-view.spec.ts` | `execution-monitor`, `run-protocol` |
| `interactions/03-asset-forms.spec.ts` | `assets` |
| `interactions/04-error-handling.spec.ts` | `protocols`, `run-protocol`, `execution-monitor`, `settings` |

## 2. Feature Modules with No E2E Coverage

*   `auth`
*   `docs`
*   `stress-test`
*   `workcell`

## 3. Critical User Flows Without Test Coverage

*   **User Authentication:** No tests for login, logout, session expiration, or role-based access control.
*   **Workcell Dashboard:** The entire `workcell` feature is untested.
*   **Documentation Access:** The `docs` feature is untested.
*   **Stress Testing:** The `stress-test` feature is not covered.
*   **Protocol Failure and Recovery:** No tests simulate a protocol failing mid-run.
*   **Editing and Deleting Resources:** The full lifecycle of editing and deleting all types of resources is not consistently covered.
*   **Advanced Search and Filtering:** No dedicated tests for search and filtering in the protocol library and asset management pages.
*   **Direct Control in Playground:** The interactive "direct control" features in the playground are not tested.

## 4. Recommendations for New Specs

*   **`auth.spec.ts`**: Cover the entire authentication workflow.
*   **`workcell-dashboard.spec.ts`**: Test the `workcell` feature's dashboard functionality.
*   **`docs-viewer.spec.ts`**: Ensure the documentation viewer renders correctly.
*   **`protocol-failure.spec.ts`**: Test the application's behavior when a protocol fails.
*   **`asset-lifecycle.spec.ts`**: Cover the full lifecycle of assets, including editing and deleting.
*   **`search-and-filter.spec.ts`**: Test search and filtering functionality.
*   **`playground-direct-control.spec.ts`**: Test the direct control features in the playground.
