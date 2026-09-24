---
title: 'E2E Test Coverage Reconnaissance Report'
---

# E2E Test Coverage Reconnaissance Report

## 1. Test Inventory

*This section catalogues all existing E2E test specifications.*

- **`01-onboarding.spec.ts`**: Simulates a first-time user experience by clearing `localStorage`. It verifies that the welcome screen appears and that the user can successfully navigate to the main dashboard.
- **`02-asset-management.spec.ts`**: Covers the Asset Management section. It verifies that the user can navigate between tabs, open the "Add Machine" and "Add Resource" dialogs, and perform full CRUD (Create, Read, Update, Delete) operations on assets. It also checks for data persistence after a page reload.
- **`03-protocol-execution.spec.ts`**: Provides a comprehensive test of the protocol execution workflow. It covers selecting a protocol, completing the setup wizard, starting the execution, monitoring its progress, and viewing the completed run's details in the history.
- **`04-browser-persistence.spec.ts`**: Focuses on browser-mode functionality. It tests the ability to export the local IndexedDB database, clear it, and then import the data back, verifying that the application state is correctly restored.
- **`asset-inventory.spec.ts`**: Specifically tests the persistence of assets (both machines and resources) across page reloads. This is crucial for validating the browser-side database functionality.
- **`asset-wizard-visual.spec.ts`**: A visual regression test that captures screenshots of each step in the asset wizard. This helps to catch unintended UI changes and ensure visual consistency.
- **`asset-wizard.spec.ts`**: Tests the full, end-to-end user journey of creating a new machine using the asset wizard. It leverages mocked API calls to provide a controlled test environment.
- **`browser-export.spec.ts`**: Covers the database export and import functionality on the Settings page. It verifies that clicking "Export" triggers a download and that "Import" opens the file chooser and a confirmation dialog.
- **`capture-remaining.spec.ts`**: A specialized test designed to capture screenshots of various dialog boxes (like protocol upload, hardware discovery, and the welcome dialog) that may not be covered in other workflow-oriented tests.
- **`catalog-workflow.spec.ts`**: Tests the user flow of adding a simulated machine from the catalog directly into the user's inventory.
- **`data-visualization.spec.ts`**: Covers the data visualization features, including rendering charts, changing axes, exporting the chart as an image, and handling empty data states.
- **`deck-setup.spec.ts`**: A visual test that navigates through the protocol setup wizard specifically to capture screenshots of the deck configuration step.
- **`execution-browser.spec.ts`**: Focuses on the protocol execution workflow within the browser-mode simulation environment.
- **`interactive-protocol.spec.ts`**: Tests the interactive protocol commands (`pause`, `confirm`, `input`) by running Python code in the Playground and verifying that the correct dialogs appear and respond to user interaction.
- **`inventory-dialog.spec.ts`**: Focuses on the inventory dialog accessed from the Playground. It verifies tab navigation and the workflow of adding a new simulated machine to the inventory.
- **`low-priority-capture.spec.ts`**: A test designed to capture screenshots of lower-priority UI elements, such as the settings page and snackbar notifications.
- **`machine-frontend-backend.spec.ts`**: A thorough test of the 3-step machine creation process, ensuring that the frontend/backend separation is correctly handled in the UI. It covers navigation, data loading, and the full creation workflow.
- **`medium-priority-capture.spec.ts`**: This test is designed to capture screenshots of various medium-priority UI states, such as empty lists, loading spinners, and data visualization components like charts and heatmaps.
- **`mock-removal-verification.spec.ts`**: A specific test to verify that mock data (protocols, run history) has been successfully removed from the application, ensuring a clean and realistic test environment.
- **`playground-direct-control.spec.ts`**: Tests the workflow of adding a new machine via the inventory dialog within the Playground and then interacting with it using the "Direct Control" feature.
- **`protocol-library.spec.ts`**: Covers the Protocol Library page, testing features like searching, filtering by category, viewing protocol details, and initiating a run.
- **`run-protocol-machine-selection.spec.ts`**: Focuses on the machine selection step within the "Run Protocol" wizard, verifying that simulated machines are displayed and can be selected.
- **`screenshot_recon.spec.ts`**: A reconnaissance test designed to capture full-page screenshots of each step in the protocol execution wizard.
- **`smoke.spec.ts`**: A high-level smoke test that verifies the basic loading and visibility of the main application pages: Dashboard, Assets, Protocols, and the Run Protocol wizard.
- **`user-journeys.spec.ts`**: Tests two critical user workflows: viewing and creating a new machine in the asset management section, and selecting and running a protocol from the library.
- **`verify-inventory.spec.ts`**: A detailed verification test for the inventory dialog. It ensures that machine definitions (frontends) are loaded correctly from the database and that filtering by category populates the asset list as expected.
- **`viz-review.spec.ts`**: A visual review test that captures screenshots of various application pages and UI elements, including different themes (light/dark mode) and responsive layouts.
- **`workcell-dashboard.spec.ts`**: Tests the main features of the Workcell Dashboard, including the hierarchical explorer for navigating workcell components and the ability to click on a machine card to enter a detailed "focus view" with deck state visualization.

---

## 2. Feature Coverage Matrix

*This matrix maps the inventoried tests to their corresponding application features and routes.*

| Feature | Route(s) | Test Spec File(s) | Coverage Level | Notes |
|---|---|---|---|---|
| **Core App Shell** | `/`, `/app/home` | `smoke.spec.ts`, `user-journeys.spec.ts` | ✅ **Good** | Basic navigation, dashboard loading, and shell visibility are well-covered. |
| **Onboarding** | `/`, `/app/home` | `01-onboarding.spec.ts` | ✅ **Good** | Simulates a first-time user and verifies the welcome flow. |
| **Asset Management** | `/assets` | `02-asset-management.spec.ts`, `asset-inventory.spec.ts`, `asset-wizard.spec.ts`, `machine-frontend-backend.spec.ts`, `verify-inventory.spec.ts` | ✅ **Excellent** | Full CRUD, persistence, and the complex 3-step creation wizard are thoroughly tested. |
| **Protocol Library**| `/protocols` | `protocol-library.spec.ts`, `smoke.spec.ts` | 🟡 **Partial** | Basic viewing, searching, and filtering are covered. Deeper interactions like metadata display could be improved. |
| **Protocol Execution**| `/run` | `03-protocol-execution.spec.ts`, `deck-setup.spec.ts`, `execution-browser.spec.ts`, `run-protocol-machine-selection.spec.ts`, `user-journeys.spec.ts` | 🟡 **Partial** | The "happy path" of a successful run is well-tested. However, there's a lack of coverage for user interventions (pause/cancel) and error states. |
| **Interactive Protocols** | `/app/playground`| `interactive-protocol.spec.ts` | ✅ **Good** | The core interactive commands (`pause`, `confirm`, `input`) are tested. |
| **Playground** | `/app/playground`| `inventory-dialog.spec.ts`, `playground-direct-control.spec.ts` | ✅ **Good** | Covers the inventory dialog and direct machine control features. |
| **Workcell Dashboard** | `/workcells/:id`| `workcell-dashboard.spec.ts` | ✅ **Basic** | Basic navigation and view switching are covered. |
| **Data Visualization** | `/run/data-visualization` | `data-visualization.spec.ts` | ✅ **Good** | Chart rendering, interaction, and export are well-tested. |
| **Browser Persistence**| `/app/settings` | `04-browser-persistence.spec.ts`, `browser-export.spec.ts` | ✅ **Excellent** | IndexedDB export, import, and data persistence are thoroughly verified. |
| **Visual Regression** | various | `asset-wizard-visual.spec.ts`, `capture-remaining.spec.ts`, `low-priority-capture.spec.ts`, `medium-priority-capture.spec.ts`, `screenshot_recon.spec.ts`, `viz-review.spec.ts` | 🟡 **Partial** | Numerous screenshot tests exist, but they are not integrated into a formal visual regression testing framework. |
| **Mock Data Verification** | various | `mock-removal-verification.spec.ts` | ✅ **Good** | Verifies that mock data is not present in the application. |


---

## 3. Critical Path Gaps

*The following critical user workflows lack E2E test coverage:*

1.  **Protocol Execution Failure and Recovery:** The current tests almost exclusively cover the "happy path" of a successful protocol run. There are no tests for what happens when a protocol **fails mid-run**, or for user actions like **pausing, resuming, or cancelling** a run. This is the most significant gap in the current test suite.
2.  **User Authentication:** The tests consistently bypass authentication by setting a fake token in `localStorage`. There is no E2E test for the actual **login/logout flow**, which is a critical vulnerability in the test coverage.
3.  **Form Validation and Error Handling:** The tests do not attempt to submit forms with invalid data to check for proper validation and user feedback. For example, creating an asset with a blank name should display an error message.
4.  **Empty and Edge Case States:** While some empty states are captured in screenshots, there is a lack of functional tests that verify the application's behavior when no data is present (e.g., no protocols in the library, no machines in the inventory).
5.  **Real Backend Interaction:** Most tests rely on mocked or browser-mode data. While this is good for component-level E2E, there's a lack of tests that verify true end-to-end data flow from the UI to a mock backend and back. This is a lower priority, as the browser-mode tests are quite comprehensive, but it is still a gap.

---

## 4. Flaky Test Candidates

*The following tests or patterns may lead to instability:*

-   **Heavy Reliance on `waitForTimeout`**: Many tests use `page.waitForTimeout()` to wait for UI updates. This is a common source of flakiness, as the wait time may not be sufficient in all environments. These should be replaced with more robust waiting mechanisms, such as waiting for a specific element to be visible or for a network request to complete.
-   **Complex `beforeEach` Hooks**: Several tests have complex `beforeEach` hooks that handle navigation, authentication, and dialog dismissal. This can make it difficult to debug test failures and can also lead to race conditions.
-   **Inconsistent Use of Page Objects**: While some tests use the Page Object Model (POM) to abstract away page details, others interact with the page directly. This makes the tests harder to maintain and less readable.
-   **Lack of a Centralized Test Data Management Strategy**: Test data is often hardcoded within the tests, making it difficult to manage and update. A more centralized approach to test data management would improve the maintainability of the tests.
-   **Redundant Screenshot Tests**: There are multiple tests that capture screenshots of the same or similar UI components. While screenshots are valuable, they should be consolidated and managed within a formal visual regression testing framework to be effective.

---

## 5. Priority Additions

*The following tests should be added to improve coverage, in order of priority:*

1.  **High Priority - Protocol Execution Failure and Recovery:**
    -   A test that starts a protocol, **pauses** it, verifies the paused state, **resumes** it, and waits for completion.
    -   A test that starts a protocol and immediately **cancels** it, verifying the cancelled state.
    -   A test that simulates a protocol failure and verifies that the UI displays an appropriate error message.
2.  **High Priority - User Authentication:**
    -   A test that navigates to the login page, enters credentials, verifies successful login and redirection, and then logs out.
3.  **Medium Priority - Form Validation:**
    -   A test that attempts to create a machine with a blank name and verifies that a validation error is shown and the form is not submitted.
4.  **Medium Priority - Empty and Edge Case States:**
    -   A functional test that verifies the application's behavior when no protocols are available in the library.
    -   A functional test that verifies the application's behavior when no machines are available in the inventory.
5.  **Low Priority - Visual Regression Framework:**
    -   Integrate a formal visual regression testing framework (e.g., Percy, Applitools) to manage and compare screenshots, rather than just capturing them.