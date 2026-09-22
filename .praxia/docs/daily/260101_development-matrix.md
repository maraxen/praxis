# Development Matrix

| ID | Status | Priority | Difficulty | Mode | Description | Created | Updated |
|---|---|---|---|---|---|---|---|
| 260120200035 | DONE | P2 | medium | agent | Phase 6 E2E Test Fix: Two issues identified:
1. **FIXED** - BroadcastChannel registration: web_bridge now properly registers the channel for USER_INTERACTION messages
2. **NEW ISSUE** - Test keyboard input: The iframe keyboard focus issue causes the first line of typed code to be lost. The import statement `from praxis.interactive import pause, confirm, input` doesn't appear in the cell.

Root causes:
- Channel issue: web_bridge.py checked js._praxis_channel but channel was a Python local variable
- Keyboard issue: page.keyboard sends to main page, not the iframe where the editor lives | 2026-01-20 | 2026-01-23 14:15:22 |
| 260120204145 | DONE | P2 | medium | librarian | Machine Frontend Analysis: Use ast-grep and ripgrep to identify all Machine frontend class files. Document: (1) All classes extending Machine/MachineFrontend abstract base, (2) Method signatures and types, (3) Constraints/limitations in the abstract base, (4) Current UI rendering patterns. Output: Comprehensive inventory markdown in .agent/research/ | 2026-01-20 | 2026-01-21 01:45:26 |
| 260120204151 | TODO | P2 | medium | deep-researcher | Research: Bespoke Machine Frontend UI - Investigate approaches for generating/rendering custom UI for each machine type based on its methods and capabilities. Consider: dynamic form generation, method introspection, capability flags, production vs browser mode differences. | 2026-01-20 | 2026-01-20 |
| 260120204444 | DONE | P3 | medium | deep-researcher | Research: Lite Mode Strategy - Evaluate SQLite support options for standalone/offline operation. Compare: (1) Browser-only with IndexedDB (current), (2) SQLite via sql.js/absurd-sql, (3) Hybrid approach. Consider use cases: education/demos, air-gapped labs, offline-first scenarios. Output: Decision document with pros/cons and recommendation. | 2026-01-20 | 2026-01-21 02:05:16 |
| 260121002630 | TODO | P2 | easy | code | Validate 1-of-each labware seeding in browser mode. Source: DEVELOPMENT_MATRIX.md P2 Feature Enhancements. | 2026-01-21 | 2026-01-21 |
| 260121002631 | TODO | P2 | medium | code | Sync tests with schema changes. Source: DEVELOPMENT_MATRIX.md P2 Technical Debt. | 2026-01-21 | 2026-01-21 |
| 260121002632 | TODO | P2 | medium | code | Validation, Vantage deck, and UX improvements. Source: DEVELOPMENT_MATRIX.md P2 Technical Debt. | 2026-01-21 | 2026-01-21 |
| 260121002633 | TODO | P2 | hard | code | WebSerial/WebUSB device enumeration in browser. Source: DEVELOPMENT_MATRIX.md P2 Hardware Validation. | 2026-01-21 | 2026-01-21 |
| 260121002634 | TODO | P2 | hard | code | Validate with Hamilton hardware. Source: DEVELOPMENT_MATRIX.md P2 Hardware Validation. | 2026-01-21 | 2026-01-21 |
| 260121002635 | TODO | P3 | medium | code | Test maintenance system. Source: DEVELOPMENT_MATRIX.md P3 State & Monitoring. | 2026-01-21 | 2026-01-21 |
| 260121002638 | TODO | P2 | medium | code | PostgreSQL verification, SQLModel warnings. Source: DEVELOPMENT_MATRIX.md P2 Technical Debt. | 2026-01-21 | 2026-01-21 |
| 260121002639 | TODO | P2 | medium | code | Validation, Vantage deck, and UX improvements. Source: DEVELOPMENT_MATRIX.md P2 Technical Debt. | 2026-01-21 | 2026-01-21 |
| 260121002640 | TODO | P2 | medium | code | Connections persist across sessions. Source: DEVELOPMENT_MATRIX.md P2 Hardware Validation. | 2026-01-21 | 2026-01-21 |
| 260121002641 | TODO | P2 | hard | code | Interactive hardware control from playground. Source: DEVELOPMENT_MATRIX.md P2 Hardware Validation. | 2026-01-21 | 2026-01-21 |
| 260121002644 | TODO | P2 | medium | code | Audit and replace 'as any' usage. Source: DEVELOPMENT_MATRIX.md P2 Technical Debt. | 2026-01-21 | 2026-01-21 |
| 260121002646 | TODO | P2 | easy | code | Add is_reusable to ResourceDefinition. Source: DEVELOPMENT_MATRIX.md P2 Technical Debt. | 2026-01-21 | 2026-01-21 |
| 260121002648 | TODO | P2 | medium | code | Validation, Vantage deck, and UX improvements. Source: DEVELOPMENT_MATRIX.md P2 Technical Debt. | 2026-01-21 | 2026-01-21 |
| 260121002650 | TODO | P2 | medium | code | Connections persist across sessions. Source: DEVELOPMENT_MATRIX.md P2 Hardware Validation. | 2026-01-21 | 2026-01-21 |
| 260121002654 | TODO | P2 | hard | code | Validate with Hamilton hardware. Source: DEVELOPMENT_MATRIX.md P2 Hardware Validation. | 2026-01-21 | 2026-01-21 |
| 260121002656 | TODO | P2 | hard | code | Interactive hardware control from playground. Source: DEVELOPMENT_MATRIX.md P2 Hardware Validation. | 2026-01-21 | 2026-01-21 |
| 260121002658 | TODO | P3 | medium | code | Implement multi-stage (Inspect -> Plan -> Exec) development workflow. Source: DEVELOPMENT_MATRIX.md P3 Agentic Infrastructure. | 2026-01-21 | 2026-01-21 |
| 260121132339 | TODO | P1 | easy | fixer | Fix and apply Linked Indices Tracer: Fix InvalidWellSetsError definition bug in errors.py (defined 3x, references PraxisError before definition), then apply the tracer from session 16296747416823548932 | 2026-01-21 | 2026-01-21 |
| 260121132341 | TODO | P1 | medium | fixer | Review and apply Multi-Vendor Deck diff: Session 6138709097205002465 creates DeckConfigurationService and DeckVisitor. Verify no conflicts with existing DeckTypeDefinitionService, then apply selectively. | 2026-01-21 | 2026-01-21 |
| 260121132343 | TODO | P2 | easy | fixer | Create @simulate_output decorator: Implement Python decorator in praxis/backend/core/decorators/ that declares simulation metadata (shape, range, strategy) per the Browser Simulation research spec. | 2026-01-21 | 2026-01-21 |
| 260121132344 | TODO | P2 | medium | fixer | Create praxis/simulators/ module: Implement PlateReaderSimulator and LiquidHandlerSimulator classes per Browser Simulation research spec. These mirror PLR APIs but generate fake data. | 2026-01-21 | 2026-01-21 |
| 260121132347 | DONE | P2 | easy | fixer | Extend PraxisRunContext with simulation_state: Add is_simulation flag, simulation_state dict, get_simulation_state() and update_simulation_state() methods per Browser Simulation research spec. | 2026-01-21 | 2026-01-21 18:30:43 |
| 260121132355 | TODO | P1 | medium | deep-researcher | Research Infinite Consumables (Browser Mode): Locate where tip rack/consumable depletion happens in browser mode. Implement option to skip DB depletion in simulation + allow runtime unique ID creation for tip racks. | 2026-01-21 | 2026-01-21 |
| 260121144246 | TODO | P1 | easy | fixer | Fix backend API test fixture: test_resource_filtering.py uses 'client' fixture that doesn't exist. Either add conftest.py with TestClient fixture or refactor test to use direct function calls. File: praxis/backend/tests/api/test_resource_filtering.py | 2026-01-21 | 2026-01-21 |
| 260121144248 | TODO | P1 | easy | code | E2E Smoke Test Verification: Run praxis/web-client e2e/smoke.spec.ts in headless mode, capture screenshots of key pages (landing, dashboard, protocol list), save to /tmp/e2e-smoke/. Report pass/fail status and any console errors. | 2026-01-21 | 2026-01-21 |
| 260121144249 | TODO | P1 | medium | code | E2E Browser Execution Test: Run praxis/web-client e2e/execution-browser.spec.ts in headless mode. Capture screenshots at: protocol load, run start, run completion. Save to /tmp/e2e-browser-exec/. Report any failures with stack traces. | 2026-01-21 | 2026-01-21 |
| 260121144251 | TODO | P1 | easy | code | E2E Asset Inventory Test: Run praxis/web-client e2e/asset-inventory.spec.ts in headless mode. Capture screenshots of: asset list view, asset detail view, filter interactions. Save to /tmp/e2e-asset/. Report pass/fail with details. | 2026-01-21 | 2026-01-21 |
| 260121144253 | TODO | P1 | medium | code | E2E User Journeys Test: Run praxis/web-client e2e/user-journeys.spec.ts in headless mode. This covers critical user flows. Capture screenshots at key checkpoints. Save to /tmp/e2e-journeys/. Report comprehensive pass/fail results. | 2026-01-21 | 2026-01-21 |
| 260121144254 | TODO | P1 | medium | code | E2E Deck Setup Test: Run praxis/web-client e2e/specs/deck-setup.spec.ts in headless mode. Capture screenshots of: empty deck, deck with placements, deck configuration dialog. Save to /tmp/e2e-deck/. Report all assertions. | 2026-01-21 | 2026-01-21 |
| 260121144256 | TODO | P1 | medium | code | E2E Protocol Execution Test: Run praxis/web-client e2e/specs/protocol-execution.spec.ts AND e2e/specs/03-protocol-execution.spec.ts in headless mode. Capture execution flow screenshots. Save to /tmp/e2e-protocol/. This is critical path for v0.1-alpha. | 2026-01-21 | 2026-01-21 |
| 260121144301 | TODO | P1 | easy | code | Frontend Build Verification: Run 'npm run build' in praxis/web-client. Capture any TypeScript errors, bundle size stats. Verify build succeeds without errors. Report full build output summary. | 2026-01-21 | 2026-01-21 |
| 260121151719 | TODO | P1 | medium | code | Create shared Playwright fixture for universal welcome dialog handling. Create e2e/fixtures/app.fixture.ts that exports a custom test object with beforeEach hook that: 1) Waits for app shell to load, 2) Detects and dismisses "Welcome to Praxis" dialog if present, 3) Waits for overlays to clear, 4) Sets localStorage flag to disable tours. Update existing specs to import this fixture instead of plain @playwright/test. | 2026-01-21 | 2026-01-21 |
| 260121151722 | TODO | P1 | easy | code | Enable Playwright globalSetup and add tour disablement. In playwright.config.ts: 1) Uncomment line 7 to enable globalSetup, 2) In e2e/global-setup.ts, add localStorage.setItem calls to disable welcome tour/onboarding before tests run. This prevents the tour overlay from blocking all tests. | 2026-01-21 | 2026-01-21 |
| 260121151724 | TODO | P1 | easy | fixer | Fix smoke.spec.ts selector drift. In e2e/specs/smoke.spec.ts line 35: Change expect(page.locator('app-main-layout')) to use a more resilient selector that works with either app-unified-shell or app-main-layout, or use the sidebar-rail which is already checked. The app now uses UnifiedShellComponent (app-unified-shell) as the main shell. | 2026-01-21 | 2026-01-21 |
| 260121151726 | TODO | P1 | easy | fixer | Fix smoke.spec.ts Assets navigation test. In e2e/specs/smoke.spec.ts lines 40-53: The test navigates to /assets and expects app-machine-list to be visible immediately, but /assets now defaults to Overview tab. Fix by: 1) Click the "Machines" tab explicitly after navigation, OR 2) Navigate to /assets?type=machines or equivalent query param. Verify the table appears after correct tab navigation. | 2026-01-21 | 2026-01-21 |
| 260121151729 | TODO | P1 | easy | code | Rename duplicate test suite names for clear reporting. Files: 1) e2e/specs/protocol-execution.spec.ts - change test.describe name from "Protocol Execution Flow" to "Protocol Wizard Flow", 2) e2e/specs/03-protocol-execution.spec.ts - change test.describe.serial name from "Protocol Execution Flow" to "Protocol Execution E2E". This eliminates report collisions. | 2026-01-21 | 2026-01-21 |
| 260121151732 | TODO | P1 | medium | code | Add Configure Simulation dialog handler to wizard.page.ts. In e2e/page-objects/wizard.page.ts: Add a method handleConfigureSimulationDialog() that: 1) Detects if the "Configure Simulation" dialog is visible (look for dialog with title containing "Simulation" or "Configure"), 2) Fills any required fields (instance name), 3) Clicks "Create Simulation" or equivalent confirm button, 4) Waits for dialog to close. Integrate this into the selectMachine or proceedToNextStep flow. | 2026-01-21 | 2026-01-21 |
| 260121151735 | TODO | P1 | medium | code | Add Angular Material stepper animation handling to wizard tests. Issue: mat-form-field elements appear as "hidden" during stepper transitions due to Angular animations. Fix: In wizard.page.ts, add a waitForStepContent() method that waits for the active step content to be fully visible: 1) Wait for .mat-step-content with ng-reflect-expanded="true" or aria-expanded="true", 2) Add 300ms buffer after step transitions for animations, 3) Use more specific locators scoped to the active step panel. | 2026-01-21 | 2026-01-21 |
| 260121151748 | TODO | P1 | medium | code | Enhance base.page.ts overlay handling for CDK backdrops. In e2e/page-objects/base.page.ts: Improve waitForOverlay() method to: 1) Handle multiple overlays (.cdk-overlay-backdrop), 2) Add retries with exponential backoff, 3) Optionally dismiss overlays by pressing Escape if they persist >5s, 4) Log when force-dismissal is used. This prevents overlays from blocking button clicks. | 2026-01-21 | 2026-01-21 |
| 260121151753 | TODO | P2 | easy | recon | RECON: Audit hardcoded CSS values vs themed CSS variables. Major violator is the Settings page. Scan praxis/web-client/src for: 1) Hardcoded color values (#hex, rgb(), rgba()) that should use CSS variables, 2) Hardcoded font-sizes/spacing that should use design tokens, 3) Components not respecting the theme system. Output: Report listing each file, line numbers, and the hardcoded values that need migration to CSS variables. Focus on *.component.scss and *.component.css files. | 2026-01-21 | 2026-01-21 |
| 260121151902 | TODO | P1 | medium | deep-researcher | INVESTIGATE: Protocol Run Wizard simulation selection is still buggy despite prior fixes. Deep-dive into the simulation machine setup flow to identify root causes. Verify the correct pipeline: 1) User selects machine type in frontend, 2) Frontend queries backend/database for available backends, 3) User configures simulation parameters. Check for: hardcoded machine sets instead of database-driven queries, race conditions in MachineService.getSimulators(), frontend state not reflecting backend truth, ConfigureSimulationDialog not properly creating MachineInstance records. Files to audit: wizard.component.ts, machine.service.ts, machine-selection components, simulation dialog. Output: Root cause analysis with specific code locations and fix recommendations. | 2026-01-21 | 2026-01-21 |
| 260121151940 | TODO | P1 | medium | deep-researcher | INVESTIGATE: "Create Simulation" button not working in Execute Protocol flow. Related to simulation selection bugs. Debug the button click handler: 1) Find the Create Simulation button component/template, 2) Trace the click event handler, 3) Check if it's calling MachineService correctly, 4) Verify dialog opens and form submits, 5) Check if MachineInstance is being created in DB. May be related to overlay/z-index issues or broken event bindings. Files: machine-selection.component.ts, configure-simulation-dialog.component.ts, machine.service.ts. | 2026-01-21 | 2026-01-21 |
| 260121152034 | TODO | P1 | medium | deep-researcher | INVESTIGATE: Run Protocol wizard shows wrong machine types for protocols. Example: Plate Reader Assay only shows LiquidHandlers in Select Machine step, not PlateReaders. Root cause: Machine filtering logic not matching protocol requirements to machine capabilities. Check: 1) How protocol.required_machines is defined, 2) How machine selection filters by capability/type, 3) Whether MachineDefinition.machine_type is being used correctly, 4) Database seeding of machine types. Files: machine-selection.component.ts, protocol.service.ts, machine.service.ts. | 2026-01-21 | 2026-01-21 |
| 260121152037 | TODO | P1 | medium | deep-researcher | INVESTIGATE: No per-machine argument configuration in Select Machine step of Run Protocol wizard. Users should be able to configure machine-specific parameters (ports, connection settings, simulation options) for each machine they select. Check: 1) What happens after machine is selected - is there a config step?, 2) MachineInstance vs MachineDefinition parameter handling, 3) Whether machine args are being passed to execution context. This may be a missing feature or broken UI. | 2026-01-21 | 2026-01-21 |
| 260121152041 | TODO | P1 | easy | recon | INVESTIGATE: Asset selection inspection not working in Run Protocol wizard. Users cannot click to inspect/view details of selected assets. Check: 1) Asset cards/list items - do they have click handlers?, 2) Is there an asset detail dialog/panel?, 3) Are click events being captured by parent overlay?, 4) What SHOULD happen when user clicks an asset in selection? | 2026-01-21 | 2026-01-21 |
| 260121152841 | TODO | P1 | easy | recon | RECON: 404 Docs Error for production markdown files. Error: Http failure response for /assets/docs/getting-started/quickstart-production.md: 404. Tasks: 1) List all expected *-production.md paths being requested, 2) Check if these files exist in src/assets/docs/, 3) Determine if we need to create them OR prevent the request, 4) Find where these requests originate (docs service, routing). Output: List of missing files and recommendation (create vs suppress). | 2026-01-21 | 2026-01-21 |
| 260121152845 | TODO | P1 | easy | recon | RECON: Playground Add Inventory Wizard current implementation analysis. The wizard is described as 'UGLY and unlike other components'. Tasks: 1) Find the component files (add-inventory-dialog or similar), 2) Screenshot/document current UI structure, 3) Compare against app design patterns (cards, chips, etc.), 4) List specific UI violations (spacing, colors, responsiveness). Prepare handoff for designer agent. | 2026-01-21 | 2026-01-21 |
| 260121152847 | TODO | P1 | medium | deep-researcher | INVESTIGATE: Categories STILL showing backend types in Playground inventory adder. This was supposedly fixed days ago. Tasks: 1) Find the original fix commit/PR, 2) Check if fix was actually merged, 3) Verify the category filtering logic in current code, 4) Trace data flow from API to UI, 5) Identify why backends are still visible. Output: Root cause + whether fix was reverted, never applied, or insufficient. | 2026-01-21 | 2026-01-21 |
| 260121152849 | TODO | P1 | medium | deep-researcher | INVESTIGATE: 'No definitions matching search' in Playground inventory adder. When searching, no results appear. Tasks: 1) Check ResourceDefinition/MachineDefinition seed data in browser SQLite, 2) Verify definitions are being loaded on app init, 3) Check search/filter logic in the component, 4) Determine if this is data issue or UI filtering bug. Output: Root cause analysis. | 2026-01-21 | 2026-01-21 |
| 260121152851 | TODO | P1 | medium | deep-researcher | INVESTIGATE: No simulation definition on-the-fly creation in Playground inventory. Feature gap: Users should be able to create simulation definitions dynamically for all categories (machines, resources). Tasks: 1) Check if create-definition UI exists anywhere, 2) Identify what API endpoints would be needed, 3) Document what on-the-fly creation means for each category, 4) Assess effort to implement. Output: Feature spec + implementation estimate. | 2026-01-21 | 2026-01-21 |
| 260121152852 | TODO | P1 | medium | recon | INVESTIGATE: Resources cannot be added in Playground inventory. Similar to machines issue. Tasks: 1) Check ResourceDefinition availability, 2) Check the add-resource flow vs add-machine flow, 3) Identify any differences that might cause one to fail, 4) Test both flows side by side. Output: Comparison analysis. | 2026-01-21 | 2026-01-21 |
| 260121152858 | TODO | P1 | medium | designer | DESIGN: Playground Add Inventory Wizard redesign spec. Current wizard is ugly and inconsistent with app design. Create a comprehensive design spec including: 1) Card-based layout for category selection, 2) Chip components for filters/tags, 3) Responsive grid for definition browsing, 4) Search with autocomplete, 5) Quick-create simulation option, 6) Visual consistency with existing dialogs (Asset dialogs, Run Wizard). Output: Design spec document with component hierarchy, mock descriptions, and interaction patterns. | 2026-01-21 | 2026-01-21 |
| 260121153043 | BLOCKED | P2 | easy | code | BLOCKED: Verify Configuration Menu functionality in Playground. Cannot test until resources can be added to the deck. Depends on: investigation of 'No definitions matching search' (260121152849) and 'Resources cannot be added' (260121152852) being resolved first. | 2026-01-21 | 2026-01-21 |
| 260121153047 | BLOCKED | P2 | easy | code | BLOCKED: Verify Direct Control functionality in Playground. Cannot test until machines/resources can be added to the deck. Depends on: investigation of 'No definitions matching search' (260121152849) and machine/resource add issues being resolved first. | 2026-01-21 | 2026-01-21 |
| 260121160424 | TODO | P1 | easy | fixer | FIX: Simulation backend matching logic in Run Protocol wizard.

**Problem**: "Create Simulation" button silently fails because backend matching uses exact name comparison that never matches.

**File**: `praxis/web-client/src/app/features/run-protocol/run-protocol.component.ts`

**Issue**: In `configureSimulationTemplate`, the code tries to match:
- `result.simulation_backend_name` (e.g., `pylabrobot.liquid_handling.backends.ChatterboxBackend`)
- Against `b.name` (e.g., `Simulated Liquid Handler`) or `b.fqn`

**Fix options**:
1. Relax matching to fallback to any simulator backend if exact match fails
2. Add backend class names as searchable aliases in PLR_BACKEND_DEFINITIONS
3. Use `backend_type === 'simulator'` as primary match, name as secondary

**Report**: .agent/reports/simulation_selection_investigation.md | 2026-01-21 | 2026-01-21 |
| 260121160429 | TODO | P1 | medium | designer | STYLE: Implement Inventory Wizard (AssetWizard) CSS from design spec.

**Problem**: ~20+ CSS classes in HTML are unimplemented, making wizard visually broken.

**Files**:
- `praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.scss`
- `praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.html` (minor adjustments)

**Missing classes to implement**:
- `.asset-wizard-container` - Layout container
- `.type-selection`, `.type-card` - Card grid for Machine/Resource selection
- `.category-selection` - Category dropdown area
- `.results-grid`, `.result-card` - Search results grid with cards
- `.step-content`, `.step-actions` - Stepper content areas
- `.search-container`, `.form-grid` - Form layouts

**Requirements**:
1. Use CSS variables (var(--mat-sys-*)) for theming/dark mode
2. Implement hover/focus states for interactive cards
3. Responsive grid (3-4 cols desktop, 2 cols tablet, 1 col mobile)
4. Match styling of other dialogs (Asset Management, Run Wizard)

**Reports**:
- .agent/reports/inventory_wizard_recon.md
- .agent/reports/inventory_wizard_design_spec.md | 2026-01-21 | 2026-01-21 |
| 260121160439 | DONE | P1 | easy | fixer | FIX: SqliteService plr_category seeding - Root cause of all "No definitions matching search" bugs. 

**Problem**: The `plr_category` column is NULL in browser SQLite for both machines and resources. Frontend filters expect this field.

**Files to modify**: `praxis/web-client/src/app/core/services/sqlite.service.ts`

**Changes needed**:
1. In machine_definitions INSERT: Add `plr_category = 'Machine'` for all machine definitions
2. In resource_definitions INSERT: Map `plr_category = def.resource_type` or `def.category` 
3. Ensure both tables have the column populated during initDb()

**Verification**: After fix, AssetWizard should show machine/resource definitions when searching.

**Reports**: 
- .agent/reports/inventory_search_investigation.md
- .agent/reports/resource_vs_machine_flow_investigation.md
- .agent/reports/backend_categories_investigation.md | 2026-01-21 | 2026-01-21 21:07:48 |
| 260121160521 | TODO | P1 | medium | fixer | FIX: Machine type filtering - Plate Reader Assay shows wrong machine types.

**Problem**: Plate Reader Assay shows LiquidHandlers instead of PlateReaders despite `requires_deck=False` logic.

**Hypothesis**: `requires_deck` property is lost during SqliteService mapping.

**Files**: 
- `praxis/web-client/src/app/core/services/sqlite.service.ts` - check getProtocols() mapping

**Report**: .agent/reports/machine_type_filtering_investigation.md | 2026-01-21 | 2026-01-21 |
| 260121161814 | TODO | P1 | hard | deep-researcher | DEEP INVESTIGATION: Frontend vs Backend Type Confusion Across Codebase

**Overview**: Multiple UI components are incorrectly displaying backend types instead of frontend machine types. This appears to be a systemic architectural issue affecting:
1. Run Protocol machine selection
2. Asset Wizard categories  
3. Simulation configuration
4. Deck selection

**Key Symptoms**:
- Categories show backend types (ChatterboxBackend) instead of frontend (LiquidHandler)
- Simulation backends render as "[", "]" or individual letters (JSON parse error?)
- "UNIQUE constraint failed: machines.serial_number" when creating simulation
- Multi-machine selection not supported
- +Machine/+Resource doesn't bypass type step
- "Slot-based layout editing coming soon" always shown for non-Hamilton decks

**Investigation Scope**:
1. Map data flow from PLR_BACKEND_DEFINITIONS → SqliteService → UI components
2. Identify where frontend vs backend distinction is lost
3. Document the correct architecture: Frontend Types → Backend Selection
4. Find all places Backend types leak into user-facing UI

**Files of Interest**:
- run-protocol.component.ts (machine selection, simulation creation)
- asset-wizard.ts (category handling)
- sqlite.service.ts (data seeding)
- plr-definitions.ts (source of truth)
- execution.service.ts (compatibility logic)

**Reports to create**: .agent/reports/frontend_backend_type_architecture.md | 2026-01-21 | 2026-01-21 |
| 260121161816 | TODO | P1 | easy | fixer | FIX: Simulation backend dropdown shows corrupted strings ("[", "]", individual letters)

**Symptom**: In Run Protocol wizard, simulation backend selection shows malformed options like "[" and "]" or individual characters instead of backend names.

**Root Cause Hypothesis**: JSON array is being rendered directly as options, OR string is being split character-by-character.

**Files to check**:
- run-protocol.component.ts - how available_simulation_backends is processed
- simulation-config-dialog.component.ts - how dropdown options are built

**Expected**: Dropdown should show "ChatterboxBackend", "SimulatorBackend", etc.

**Report**: .agent/reports/simulation_backend_dropdown_bug.md | 2026-01-21 | 2026-01-21 |
| 260121161821 | TODO | P1 | easy | fixer | FIX: "UNIQUE constraint failed: machines.serial_number" on simulation creation

**Error**: run-protocol.component.ts:1150 - UNIQUE constraint failed

**Root Cause**: Simulation machine creation uses the same serial_number for multiple instances, OR doesn't generate unique serial numbers.

**Fix needed**: Generate unique serial_number (UUID or timestamp-based) for each simulation machine instance.

**File**: sqlite.service.ts or MachineRepository.create() | 2026-01-21 | 2026-01-21 |
| 260121161825 | TODO | P2 | easy | fixer | FIX: Asset Wizard +Machine/+Resource should bypass first step

**Issue**: When clicking "+Machine" or "+Resource" in Playground, wizard should start at category selection (step 2), not type selection (step 1).

**Current behavior**: Shows unnecessary Machine vs Resource selection
**Expected**: Skip to category/definition selection with type pre-selected

**File**: asset-wizard.ts - check for mode/type input and stepper initialization

**Changes**:
1. Accept optional input for pre-selected type (Machine/Resource)
2. If provided, skip first step using MatStepper.selectedIndex = 1
3. PlaygroundComponent should pass the type when opening dialog | 2026-01-21 | 2026-01-21 |
| 260121161826 | TODO | P2 | medium | recon | INVESTIGATE: Deck layout "coming soon" message always shown for non-Hamilton decks

**Symptom**: After selecting a deck in simulation, message "Slot-based layout editing is coming soon. For now, a standard layout is provided." appears for all non-Hamilton/rails decks.

**Questions**:
1. What determines if a deck supports slot-based editing?
2. Is this a feature flag or deck capability?
3. Should this message be hidden, or is the feature actually missing?

**Files**: deck-setup components, deck service, deck type definitions | 2026-01-21 | 2026-01-21 |
| 260121161831 | TODO | P2 | easy | fixer | REMOVE: Transfer pattern argument in selective transfer protocol

**Requested**: Eliminate transfer_pattern arg from selective transfer protocol.

**Action**: Remove the parameter from protocol definition and any calling code.

**Files**: selective_transfer.py or relevant protocol file | 2026-01-21 | 2026-01-21 |
| 260121162014 | TODO | P1 | medium | designer | FIX: Asset Wizard card styling must match Protocol cards (gold standard)

**Problem**: Asset Wizard cards don't match the visual styling of Protocol cards. Category selection uses dropdown instead of chips.

**Requirements**:
1. Audit Protocol card styling in protocol-list or protocol-card components
2. Update Asset Wizard result-card and type-card to use same patterns
3. Replace category dropdown with chip selection or card-based grid
4. Ensure visual consistency across all card-based UIs

**Files**:
- asset-wizard.scss (update styles)
- Protocol card components (reference for gold standard)

**Visual goals**: Same elevation, border-radius, hover effects, typography as protocol cards | 2026-01-21 | 2026-01-21 |
| 260121162018 | DONE | P1 | easy | fixer | FIX: Docs 404 errors from speculative -production.md loading

**Problem**: Docs pages trigger 404s when speculatively loading non-existent *-production.md files, causing ErrorInterceptor to display errors.

**Solution from investigation**: Implement HttpContext token to suppress error handling for these specific speculative requests.

**Files**:
- docs service or doc loader component
- error.interceptor.ts

**Report**: .agent/reports/docs_404_investigation.md

**Implementation**:
1. Add HttpContext token: SUPPRESS_ERROR_HANDLING
2. Set token on speculative doc requests
3. ErrorInterceptor checks for token and skips error display | 2026-01-21 | 2026-01-21 21:24:34 |
| 260121162021 | TODO | P1 | easy | fixer | FIX: Asset Wizard category selection - use chips instead of dropdown

**Problem**: Category selection in Asset Wizard is a dropdown, which is unintuitive. Should use chip selection or card-based selection like other parts of the app.

**Requirements**:
1. Replace mat-select dropdown with mat-chip-listbox or card grid
2. Show all categories at once for quick visual scanning
3. Allow single selection with clear visual feedback
4. Match the interaction pattern used in Run Protocol wizard

**File**: asset-wizard.html, asset-wizard.ts, asset-wizard.scss | 2026-01-21 | 2026-01-21 |
| 260121165407 | TODO | P1 | easy | fixer | FIX: Normalize plr_category values in generate_browser_db.py - ensure Title Case (Plate, TipRack, Deck, Carrier) and filter out method entries (get_*, set_*) | 2026-01-21 | 2026-01-21 |
| 260121165409 | TODO | P1 | medium | fixer | REFACTOR: Remove backends from machine_definitions table - backends should only exist in machine_backend_definitions, not pollute machine_definitions with plr_category='Backend' | 2026-01-21 | 2026-01-21 |
| 260121165411 | DONE | P1 | easy | fixer | FIX: Asset Wizard category dropdown should filter out plr_category='Backend' values - only show frontend-friendly categories (Machine, LiquidHandler, PlateReader, etc.) | 2026-01-21 | 2026-01-21 22:00:24 |
| 260121165416 | TODO | P1 | easy | fixer | FIX: Asset Dashboard bypass - AssetsComponent openUnifiedDialog should pass preselectedType like Playground when clicking +Machine or +Resource buttons | 2026-01-21 | 2026-01-21 |
| 260121165418 | TODO | P2 | easy | designer | STYLE: Asset Wizard category selection - replace mat-select dropdown with mat-chip-listbox for quick visual scanning and selection | 2026-01-21 | 2026-01-21 |
| 260121165421 | TODO | P2 | easy | designer | STYLE: Asset Wizard type cards spacing - reduce horizontal card width and improve responsive grid layout | 2026-01-21 | 2026-01-21 |
| 260121171535 | TODO | P1 | medium | designer | STYLE: Asset Wizard categories - replace chips with icon cards grid (max 4 columns, flex container with max-width), include appropriate category icons | 2026-01-21 | 2026-01-21 |
| 260121171536 | TODO | P1 | easy | fixer | FIX: Asset Wizard dialog size - prevent dialog from expanding when selection is made, use fixed/max height container | 2026-01-21 | 2026-01-21 |
| 260121171537 | TODO | P1 | medium | fixer | FIX: Run Protocol asset selection render bug - autocomplete updates but UI doesn't reflect new selection visually | 2026-01-21 | 2026-01-21 |
| 260121171538 | TODO | P2 | easy | fixer | FIX: Run Protocol asset clear button - add explicit clear action per asset row to reset selection | 2026-01-21 | 2026-01-21 |
| 260121171541 | TODO | P2 | easy | fixer | FIX: Run Protocol hover tooltip - extend tooltip area to cover entire asset row instead of only the selection chip | 2026-01-21 | 2026-01-21 |
| 260121173038 | TODO | P2 | easy | fixer | FIX: Playground Asset Wizard dialog size - match width/height to Assets page dialog | 2026-01-21 | 2026-01-21 |
| 260121173042 | TODO | P2 | easy | fixer | FIX: Playground Asset Wizard dialog size - match width/height to Assets page dialog | 2026-01-21 | 2026-01-21 |
| 260121173046 | TODO | P1 | medium | fixer | FIX: Asset autocomplete display value - after selection, show selected asset name instead of original search text | 2026-01-21 | 2026-01-21 |
| 260121173051 | DONE | P1 | easy | fixer | FIX: Asset autocomplete easy clear - allow clearing selected text easily to search and reselect a different asset | 2026-01-21 | 2026-01-21 22:41:06 |
| 260121173053 | TODO | P2 | easy | fixer | FIX: Asset autocomplete dropdown positioning - fix left-aligned dropdown, should be centered or right-aligned with input | 2026-01-21 | 2026-01-21 |
| 260121173054 | TODO | P1 | easy | fixer | FIX: Add Clear All Selections button for asset form - single button to reset all asset selections, not duplicated per autocomplete | 2026-01-21 | 2026-01-21 |
| 260121173055 | TODO | P1 | medium | fixer | FIX: Add Auto-fill buttons - global Auto-fill All button plus per-asset Auto-fill button in each requirement card | 2026-01-21 | 2026-01-21 |
| 260121173056 | TODO | P1 | easy | fixer | FIX: protocol_runs schema - add missing protocol_definition_accession_id column to schema.sql and praxis.db | 2026-01-21 | 2026-01-21 |
| 260121173057 | TODO | P1 | medium | fixer | FIX: Selective transfer single indices parameter - protocol shows source_wells and target_wells separately when should show single indices param with one well selection | 2026-01-21 | 2026-01-21 |
| 260121173058 | TODO | P2 | easy | fixer | FIX: Tooltip hover delay - increase matTooltipShowDelay for information-dense tooltips in asset selection step | 2026-01-21 | 2026-01-21 |
| 260121173104 | DONE | P1 | medium | fixer | FIX: Deck Setup ghosted items not rendering - resources confirmed in guided deck setup should appear on deck visualization after Done click | 2026-01-21 | 2026-01-21 22:40:59 |
| 260121173253 | DONE | P1 | easy | fixer | FIX: 'Live Experiments' and 'View Run Details' links incorrect destination - should navigate to Execution Monitor (e.g. /runs/:id) instead of Run Protocol wizard | 2026-01-21 | 2026-01-21 22:42:01 |
| 260121180700 | TODO | P1 | hard | oracle | 🔴 CRITICAL BLOCKER: Deep Reconnaissance - 'No definitions found' in Asset Wizard

SYMPTOM: Asset Wizard Step 2 shows 'No definitions found matching ""' for all Machine/Resource searches.

IMPACT: Cannot add machines/resources in Asset Wizard, blocks testing live instrument interface and REPL hardware connection.

INVESTIGATION SCOPE:
1. Verify generate_browser_db.py correctly populates plr_category
2. Check DB state: sqlite3 praxis.db "SELECT COUNT(*), plr_category FROM machine_definitions GROUP BY plr_category"
3. Trace AssetWizard.searchResults$ Observable chain in asset-wizard.ts
4. Examine SqliteService query methods for filtering logic
5. Check AssetService.searchDefinitions() or similar
6. Verify sqlite-repository.ts handles category filtering correctly
7. Look for any frontend transformation/filtering that could drop results

KEY FILES:
- praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts
- praxis/web-client/src/app/features/assets/services/asset.service.ts
- praxis/web-client/src/app/core/services/sqlite.service.ts
- praxis/web-client/src/app/core/db/sqlite-repository.ts
- scripts/generate_browser_db.py

DELIVERABLE: Root cause analysis report with specific code locations and recommended fix. | 2026-01-21 | 2026-01-21 |
| 260121181800 | TODO | P1 | hard | oracle | 🔴 Run Protocol Machine/Resource Selection UI Issues

MULTIPLE ISSUES in the Run Protocol asset selection flow:

1. **Missing Simulated Toggle**: Need a toggle to switch between simulated vs real backends
2. **Category Filtering Broken**: Definitions shown should be filtered based on selected category (Machine vs Resource)
3. **Scope**: Fix must apply to BOTH machine AND resource selection workflows
4. **Simulated Showing as Real**: Some simulated backends are incorrectly appearing in the real options list
5. **Chatterbox vs Simulated Ambiguity**: Redundancy/confusion between 'simulated backend' and 'chatterbox' terminology in run protocol context

INVESTIGATION NEEDED:
- How is the asset list populated for Run Protocol?
- Where should the simulated/real toggle live?
- How is category filtering supposed to work?
- What distinguishes a 'simulated backend' from 'chatterbox'?
- What's the data model for is_simulated or similar flags?

KEY FILES:
- praxis/web-client/src/app/features/run-protocol/
- praxis/web-client/src/app/features/run-protocol/components/guided-setup/
- Asset selection components
- Backend/machine definition models

DELIVERABLE: Root cause analysis + implementation plan for toggle and proper filtering | 2026-01-21 | 2026-01-21 |
| 260121182030 | TODO | P1 | medium | fixer | Asset Wizard Empty Search Default State Fix

BUG: Empty search bar shows 'No definitions found' instead of all items

CURRENT BEHAVIOR:
- Empty search bar → 'No definitions found matching ""'
- Type a letter → Results populate and filtering works

EXPECTED BEHAVIOR:
- Empty search bar → Show ALL definitions (default state)
- As user types → Filter the displayed list

ROOT CAUSE LIKELY:
- searchResults$ Observable only triggers on non-empty input
- OR debounce/filter logic skips empty string
- Need to emit all results when query is empty/initial

ALSO FIX:
- Backend/frontend type mixing in results (filtering by plr_category may still be incomplete)

KEY FILES:
- praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts
- Look for searchControl.valueChanges or similar
- Check filter/debounce operators in the Observable chain

FIX: Ensure empty query returns all definitions for the selected category | 2026-01-21 | 2026-01-21 |
| 260121182637 | TODO | P1 | medium | fixer | Asset Wizard Backend/Frontend Type Mixing

BUG: Backend types (like Chatterbox, SimulatedBackend) are appearing mixed with frontend-facing Machine/Resource definitions.

EXPECTED: Only user-facing definitions should appear, filtered by plr_category.

FIX:
- Filter results by plr_category in asset-wizard.ts
- Ensure plr_category='Machine' for machines, plr_category='Resource' for resources
- Exclude backend implementation types from user-visible lists

KEY FILES:
- praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts
- praxis/web-client/src/app/features/assets/services/asset.service.ts | 2026-01-21 | 2026-01-21 |
| 260121182643 | TODO | P1 | medium | fixer | Asset Wizard Backend/Frontend Type Mixing

BUG: Backend types appearing mixed with frontend-facing Machine/Resource definitions.

FIX: Filter results by plr_category in asset-wizard.ts | 2026-01-21 | 2026-01-21 |
| 260121182644 | TODO | P1 | easy | fixer | FIX: Build Error - isSelectiveTransferProtocol missing method in run-protocol.component.ts:685 | 2026-01-21 | 2026-01-21 |
| 260121182645 | TODO | P1 | easy | fixer | FIX: protocol_runs schema missing protocol_definition_accession_id column | 2026-01-21 | 2026-01-21 |
| 260121182646 | TODO | P2 | medium | fixer | Selective Transfer shows 2 well args instead of single indices parameter | 2026-01-21 | 2026-01-21 |
| 260121182647 | TODO | P2 | easy | fixer | Autocomplete display value not updating after selection | 2026-01-21 | 2026-01-21 |
| 260121182651 | TODO | P2 | easy | fixer | Autocomplete dropdown positioning - push left and maintain consistent size | 2026-01-21 | 2026-01-21 |
| 260121182653 | TODO | P2 | medium | fixer | Deck Setup Resource Dialog - add step-by-step dynamic highlighting like Step 2 | 2026-01-21 | 2026-01-21 |
| 260121182916 | TODO | P1 | easy | fixer | FIX: Machine category filter not applied in Asset Wizard

BUG: Step 2 category selection (LiquidHandler, PlateReader, etc) is ignored when searching Machine definitions.

ROOT CAUSE:
- asset-wizard.ts line 142: searchMachineDefinitions(query) doesn't pass category
- Compare to line 146 for Resources: searchResourceDefinitions(query, category) ✅

FIX:
1. Update AssetService.searchMachineDefinitions to accept optional category param
2. Filter by machine_category field when category provided
3. Update asset-wizard.ts to pass category to the search

FILES:
- praxis/web-client/src/app/features/assets/services/asset.service.ts
- praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts | 2026-01-21 | 2026-01-21 |
| 260121182931 | TODO | P2 | easy | fixer | Normalize Chatterbox -> Simulated terminology in UI

ISSUE: Mixed terminology confuses users. PLR uses 'Chatterbox' internally but users understand 'Simulated'.

FIX:
- Map 'Chatterbox' to 'Simulated' in UI display labels
- Keep 'Chatterbox' in code/logs for developer context
- Check asset-wizard.ts availableSimulationBackends array

FILES:
- praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts | 2026-01-21 | 2026-01-21 |
| 260121185629 | TODO | P1 | medium | oracle | Investigate why `transfer_pattern` and `replicate_count` parameters returned to Selective Transfer protocol.

**Investigation Path:**
1. Check protocol definition in database:
   ```sql
   sqlite3 praxis/web-client/src/assets/db/praxis.db "SELECT name, parameters FROM function_protocol_definitions WHERE name LIKE '%Selective%'"
   ```
2. If stale params exist, check `generate_browser_db.py` for parameter extraction logic
3. Check if there's a seeding or migration that reintroduces these params
4. Trace from Python protocol definition to DB seeding

**Expected:** Selective Transfer should only have `indices` parameter.

**Output:** Report with findings and cleanup steps. | 2026-01-21 | 2026-01-21 |
| 260121185643 | TODO | P1 | easy | fixer | Direct Control component crashes at line 88 when `method.args` is undefined.

**Location:** `praxis/web-client/src/app/features/playground/components/direct-control/direct-control.component.ts:88`

**Problem:**
```typescript
buildForm(method: MethodInfo) {
  const group: any = {};
  method.args.forEach(arg => {  // Crashes if args is undefined
```

**Fix:**
```typescript
buildForm(method: MethodInfo) {
  const group: any = {};
  (method.args || []).forEach(arg => {
```

Also add same guard in `runCommand()` at line 108. | 2026-01-21 | 2026-01-21 |
| 260121185649 | TODO | P1 | medium | oracle | Run Protocol shows empty machine selection list - users cannot proceed.

**Location:** `praxis/web-client/src/app/features/run-protocol/run-protocol.component.ts:935-1038`

**Investigation Path:**
1. Check browser console for `[RunProtocol] Debug Machine Filtering:` logs
2. Trace `loadCompatibility()` function
3. Check if `executionService.getCompatibility()` returns data
4. Check protocol's `assets` array for `required_plr_category`
5. Check filtering logic at lines 986-1011

**Potential Root Causes:**
- Protocol missing `required_plr_category` in assets
- `requiredCategories` set constructed but empty
- Filtering too aggressive (line 1006-1011)
- `requires_deck === false` filtering removes all machines (line 1015-1023)

**Output:** Advisory report with root cause and recommended fix. | 2026-01-21 | 2026-01-21 |
| 260121185654 | TODO | P1 | easy | fixer | Verify that backend types are properly filtered from Asset Wizard category list.

**Location:** `praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts:143`

**Current Filter:**
```typescript
return this.assetService.searchMachineDefinitions(query, category).pipe(
  map(defs => defs.filter(d => d.plr_category === 'Machine'))
);
```

**Verification Steps:**
1. Open Asset Wizard in browser
2. Select MACHINE type
3. Check if backend types (Chatterbox*, etc.) appear in definition list
4. If backends appear, check DB values: `sqlite3 praxis/web-client/src/assets/db/praxis.db "SELECT name, plr_category FROM machine_definitions LIMIT 20"`
5. If plr_category values are wrong, regenerate: `uv run scripts/generate_browser_db.py`

**Expected:** Only definitions with `plr_category === 'Machine'` shown. | 2026-01-21 | 2026-01-21 |
| 260121185700 | TODO | P1 | medium | oracle | Investigate why `transfer_pattern` and `replicate_count` parameters returned to Selective Transfer protocol.

**Investigation Path:**
1. Check protocol definition in database:
   ```sql
   sqlite3 praxis/web-client/src/assets/db/praxis.db "SELECT name, parameters FROM function_protocol_definitions WHERE name LIKE '%Selective%'"
   ```
2. If stale params exist, check `generate_browser_db.py` for parameter extraction logic
3. Check if there's a seeding or migration that reintroduces these params
4. Trace from Python protocol definition to DB seeding

**Expected:** Selective Transfer should only have `indices` parameter.

**Output:** Report with findings and cleanup steps. | 2026-01-21 | 2026-01-21 |
| 260121185706 | TODO | P1 | hard | fixer | Asset Wizard needs to support two contexts with different flows:

**Contexts:**
- `asset-management`: Create NEW assets from definitions (current behavior)
- `playground`: SELECT EXISTING machines from DB or simulate new

**Implementation:**
1. Add `@Input() context: 'playground' | 'asset-management' = 'asset-management';` to AssetWizard
2. Add conditional logic in `ngOnInit()` for playground context
3. For playground + MACHINE: Show existing machines from `assetService.getMachines()`
4. Add 'Simulate New...' option at bottom of existing machines list
5. Skip definition/config steps unless 'Simulate New' chosen

**Files:**
- `praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts`
- `praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.html`
- Caller in playground component

**Acceptance:**
- Playground shows existing machines for selection
- Asset Management shows definitions for creation
- Both support simulation option | 2026-01-21 | 2026-01-21 |
| 260121185708 | TODO | P1 | medium | fixer | Direct Control shows backend types instead of machine methods.

**Problem:** The component attempts to load methods from `/api/v1/machines/definitions/${defId}/methods` but:
1. May not have correct definition ID
2. API endpoint may not exist in browser mode
3. Shows wrong data in template

**Location:** `praxis/web-client/src/app/features/playground/components/direct-control/direct-control.component.ts:57-79`

**Investigation:**
1. Check how `machine_definition_accession_id` is populated on machine objects
2. Check if methods API exists in browser mode
3. If not, methods need to come from machine_frontend_definitions table

**Fix Path:**
- Use SqliteService to query machine methods from frontend definitions
- OR mock methods based on machine category | 2026-01-21 | 2026-01-21 |
| 260121185711 | DONE | P2 | easy | fixer | Append unique suffix to default asset instance names to prevent UNIQUE constraint failures.

**Location:** `praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts:177-179`

**Current:**
```typescript
this.configStepFormGroup.patchValue({
  name: def.name,  // Uses definition name directly
  description: def.description || ''
});
```

**Fix:**
```typescript
const uniqueSuffix = Math.random().toString(36).substring(2, 6).toUpperCase();
this.configStepFormGroup.patchValue({
  name: `${def.name} ${uniqueSuffix}`,
  description: def.description || ''
});
```

**Also:** Add user-friendly error toast when UNIQUE constraint fails. | 2026-01-21 | 2026-01-22 00:10:34 |
| 260121185712 | TODO | P2 | easy | fixer | Show user-friendly error messages when asset creation fails.

**Problem:** Raw errors like `UNIQUE constraint failed: resources.name` shown in console only.

**Location:** `praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts:228-229`

**Fix:**
1. Add MatSnackBar injection
2. Catch specific error patterns in createAsset()
3. Show appropriate toast:
   - UNIQUE constraint -> 'An asset with this name already exists. Please use a different name.'
   - Generic -> 'Failed to create asset. Please try again.'

```typescript
import { MatSnackBar } from '@angular/material/snack-bar';

private snackBar = inject(MatSnackBar);

catch (error: any) {
  const msg = error?.message || '';
  if (msg.includes('UNIQUE constraint')) {
    this.snackBar.open('An asset with this name already exists.', 'OK', { duration: 5000 });
  } else {
    this.snackBar.open('Failed to create asset.', 'OK', { duration: 5000 });
  }
}
``` | 2026-01-21 | 2026-01-21 |
| 260121185717 | TODO | P3 | easy | fixer | Document SharedArrayBuffer limitation and COOP/COEP header requirements.

**Issue:** `python.worker.ts:17 Uncaught ReferenceError: SharedArrayBuffer is not defined`

**Cause:** SharedArrayBuffer requires Cross-Origin-Opener-Policy (COOP) and Cross-Origin-Embedder-Policy (COEP) headers.

**Resolution Options:**
1. Add headers to dev server in angular.json
2. Document as known limitation
3. Add fallback for non-SAB environments

**Output:** Update README or create known-issues doc with:
- Explanation of the issue
- Impact on Python worker
- Workaround or fix instructions | 2026-01-21 | 2026-01-21 |
| 260122092729 | TODO | P1 | medium | fixer | CRITICAL BUG: Protocol Runner displays 'This protocol has no machine requirements' incorrectly | 2026-01-22 | 2026-01-22 14:28:15 |
| 260122092731 | TODO | P1 | easy | recon | Recon: pylabrobot.io types not yet shimmed for browser mode | 2026-01-22 | 2026-01-22 14:28:03 |
| 260122092735 | TODO | P1 | medium | fixer | Implement plate reader open/close methods in Direct Control | 2026-01-22 | 2026-01-22 14:28:15 |
| 260122152143 | IN_PROGRESS | P1 | trivial | code | The WebHID shim is fully implemented at praxis/web-client/src/assets/shims/web_hid_shim.py but TECHNICAL_DEBT.md incorrectly lists it as 'Missing'. Remove or update the HID Transport Shim entry to reflect its completed status. Reference: .agent/reports/recon_hid_shim_status.md | 2026-01-22 | 2026-01-22 20:29:18 |
| 260122152148 | IN_PROGRESS | P1 | trivial | code | In praxis/web-client/playwright.config.ts, change screenshot option from 'only-on-failure' to 'on'. Also explicitly set outputDir: 'test-results/' for clarity. Reference: .agent/reports/recon_e2e_infrastructure.md | 2026-01-22 | 2026-01-22 20:29:18 |
| 260122152152 | IN_PROGRESS | P1 | trivial | code | Add 'test-results/' to praxis/web-client/.gitignore to prevent Playwright test artifacts from being committed. Reference: .agent/reports/recon_e2e_infrastructure.md | 2026-01-22 | 2026-01-22 20:29:19 |
| 260122152153 | IN_PROGRESS | P1 | trivial | code | In root .gitignore, correct the typo 'praxis/web-client/e2e/screenshot/' to 'praxis/web-client/e2e/screenshots/' (plural). Reference: .agent/reports/recon_gitignore.md | 2026-01-22 | 2026-01-22 20:29:19 |
| 260122152154 | IN_PROGRESS | P1 | trivial | code | Add '*.db' pattern to root .gitignore to prevent SQLite database files (praxis.db) from being tracked. Also add '.agent/scripts/jules-diff-tool/jules-diff-tool' to ignore the compiled binary. Reference: .agent/reports/recon_gitignore.md | 2026-01-22 | 2026-01-22 20:29:20 |
| 260122152156 | IN_PROGRESS | P1 | trivial | code | Delete the following stale files from repository root: modified_changes.diff, temp_state_size_test.py, test_resolve_params.py. These are temporary/orphaned files that should not be tracked. Reference: .agent/reports/recon_repo_cleanup.md | 2026-01-22 | 2026-01-22 20:29:20 |
| 260122152159 | TODO | P2 | trivial | code | Move RUNWAY.md to .agent/archive/ as it documents the completed repository rename from pylabpraxis to praxis and is no longer relevant. Reference: .agent/reports/recon_root_markdown.md | 2026-01-22 | 2026-01-22 |
| 260122152220 | TODO | P2 | easy | code | Update CONTRIBUTING.md to use 'uv run' commands instead of 'make' commands to match README.md. Replace 'make test', 'make lint', 'make typecheck', 'make docs' with their uv equivalents. Reference: .agent/reports/recon_root_markdown.md | 2026-01-22 | 2026-01-22 |
| 260122152223 | TODO | P1 | easy | code | Update all documentation files to use correct Docker service names. Change 'db' to 'praxis-db' in: docs/getting-started/installation-production.md (line 27), docs/reference/troubleshooting.md (line 19), docs/reference/cli-commands.md (line 7), docs/development/contributing.md (line 23), docs/development/testing.md (line 13). Reference: .agent/reports/recon_documentation.md | 2026-01-22 | 2026-01-22 |
| 260122152225 | TODO | P1 | easy | code | Fix incorrect file paths in documentation: docs/getting-started/quickstart.md line 15 'cd praxis/praxis/web-client' should be 'cd praxis/web-client'. docs/development/contributing.md line 91 'praxis/praxis/' should remove extra 'praxis/'. docs/reference/cli-commands.md line 179 'praxis/praxis/web-client' should be 'praxis/web-client'. Reference: .agent/reports/recon_documentation.md | 2026-01-22 | 2026-01-22 |
| 260122152228 | TODO | P2 | easy | code | Standardize uvicorn commands across docs to use 'uvicorn main:app --reload --port 8000'. Update: docs/getting-started/quickstart.md line 24, docs/development/contributing.md line 27, docs/reference/cli-commands.md line 12. Reference: .agent/reports/recon_documentation.md | 2026-01-22 | 2026-01-22 |
| 260122152231 | TODO | P2 | easy | code | Create CHANGELOG.md at repository root following Keep a Changelog format. Include header with format links, [Unreleased] section with Added/Changed/Fixed subsections, and [v0.1-alpha] entry documenting initial setup, PyLabRobot support, asset management, and WebSocket monitoring. Reference: .agent/reports/recon_changelog_setup.md | 2026-01-22 | 2026-01-22 |
| 260122152239 | TODO | P3 | trivial | code | Add clarifying sentences at the top of ROADMAP.md, POST_SHIP.md, and TECHNICAL_DEBT.md explaining each file's scope and linking to the others. Example for ROADMAP.md: 'For immediate post-release plans, see POST_SHIP.md. For known issues, see TECHNICAL_DEBT.md.' Reference: .agent/reports/recon_root_markdown.md | 2026-01-22 | 2026-01-22 |
| 260122152241 | TODO | P1 | medium | code | Replace hardcoded Tailwind colors with theme variables in run-protocol.component.ts. Specific replacements: text-blue-400 -> var(--sys-tertiary), !from-green-500 !to-emerald-600 -> var(--gradient-primary), shadow-green-500/* -> theme shadow vars, .border-green-500-30 -> var(--theme-status-success-border), .bg-green-500-05 -> var(--theme-status-success-muted). Reference: .agent/reports/recon_protocol_runner_visual.md | 2026-01-22 | 2026-01-22 |
| 260122152244 | TODO | P1 | easy | code | Replace hardcoded RGB values with theme variables in guided-setup.component.ts. Replace rgb(34, 197, 94) with var(--theme-status-success) on lines 268, 272, 300, 310. Replace rgb(251, 191, 36) with var(--theme-status-warning) on line 306. Reference: .agent/reports/recon_protocol_runner_visual.md | 2026-01-22 | 2026-01-22 |
| 260122152247 | TODO | P2 | easy | code | Replace Tailwind color classes with theme variables in protocol-summary.component.ts. Replace bg-green-500/10, text-green-500, border-green-500/20 with --theme-status-success-* variants. Replace text-red-500 with var(--status-error). Reference: .agent/reports/recon_protocol_runner_visual.md | 2026-01-22 | 2026-01-22 |
| 260122152249 | TODO | P2 | easy | code | Replace Tailwind color classes in live-dashboard.component.ts: text-green-600 -> var(--theme-status-success), text-gray-400 -> var(--theme-text-tertiary), bg-green-100 -> var(--theme-status-success-muted), bg-red-100 -> var(--theme-status-error-muted), bg-gray-900 -> var(--mat-sys-surface-container). Reference: .agent/reports/recon_protocol_runner_visual.md | 2026-01-22 | 2026-01-22 |
| 260122152255 | TODO | P1 | trivial | code | Replace text-yellow-500 Tailwind class with proper themed class using var(--theme-status-warning) in protocol-detail-dialog.component.ts around line 200. Reference: .agent/reports/recon_theme_variables.md | 2026-01-22 | 2026-01-22 |
| 260122152300 | TODO | P2 | trivial | code | Replace text-green-600 and dark:text-green-400 Tailwind classes with proper themed class using var(--theme-status-success) in settings.component.ts around line 136. Reference: .agent/reports/recon_theme_variables.md | 2026-01-22 | 2026-01-22 |
| 260122152302 | TODO | P3 | easy | code | Create praxis_logo_gradient.svg by editing praxis/web-client/src/assets/logo/praxis_logo.svg: Add <defs> section with <linearGradient id='praxis-gradient'> containing stops for #ED7A9B (0%), #ff8fa8 (50%), #73A9C2 (100%) at 135deg angle. Change fill='#000000' to fill='url(#praxis-gradient)' on all paths. Save as praxis_logo_gradient.svg in same directory. Reference: .agent/reports/recon_logo_branding.md | 2026-01-22 | 2026-01-22 |
| 260122152303 | TODO | P3 | trivial | code | Move port_docstrings.py from repository root to scripts/ directory. This is a one-off utility script that belongs with other scripts. Reference: .agent/reports/recon_repo_cleanup.md | 2026-01-22 | 2026-01-22 |
| 260122152322 | TODO | P3 | trivial | code | Move walkthrough.md from repository root to docs/getting-started/ directory. This is user documentation and should be co-located with other guides. Reference: .agent/reports/recon_repo_cleanup.md | 2026-01-22 | 2026-01-22 |
| 260122154157 | TODO | P2 | M | code | Reconnaissance task to audit all relative paths in the web client (imports, assets, SCSS) and document replacement strategy with tsconfig path aliases. RECON ONLY - no code changes. | 2026-01-22 | 2026-01-22 |
| 260122192955 | TODO | P2 | medium | deep-researcher | **Jules Sessions:** 6157768886739134846, 9771678729768842088, 13961897869952292814, 10591135620949413674, 10102345080306532279, 584843506203529508

**Summary:** These 6 sessions replace hardcoded Tailwind colors (text-green-600, text-yellow-500, bg-green-100, etc.) with CSS theme variables (--theme-status-success, --theme-status-warning, etc.).

**Review Questions:**
1. Are all affected theme variables (--theme-status-success, --theme-status-warning, --theme-status-error, muted variants, border variants) properly defined in styles.scss or a central theme file?
2. Do the inline [style.color] bindings in Angular templates follow the project's established patterns, or should these be CSS classes?
3. Are there remaining hardcoded colors in these components that were missed?
4. Is the gradient-success class properly defined with fallback values for both light and dark themes?
5. Does the approach align with Material 3 theme token conventions being used elsewhere?

**Risks:**
- Theme variable undefined in some theme configurations
- Inline style bindings harder to override than CSS classes
- Inconsistent patterns: some use [style.X] bindings, some use CSS classes

**Acceptance Criteria:**
- Confirm all theme variables exist in theme definitions
- Identify any pattern inconsistencies
- Recommend standardization approach | 2026-01-22 | 2026-01-22 |
| 260122193018 | TODO | P2 | M | code | **Jules Sessions:** 6157768886739134846, 9771678729768842088, 13961897869952292814, 10591135620949413674, 10102345080306532279, 584843506203529508

**Summary:** These 6 sessions replace hardcoded Tailwind colors (text-green-600, text-yellow-500, bg-green-100, etc.) with CSS theme variables (--theme-status-success, --theme-status-warning, etc.).

**Review Questions:**
1. Are all affected theme variables (--theme-status-success, --theme-status-warning, --theme-status-error, muted variants, border variants) properly defined in styles.scss or a central theme file?
2. Do the inline [style.color] bindings in Angular templates follow the project's established patterns, or should these be CSS classes?
3. Are there remaining hardcoded colors in these components that were missed?
4. Is the gradient-success class properly defined with fallback values for both light and dark themes?
5. Does the approach align with Material 3 theme token conventions being used elsewhere?

**Risks:**
- Theme variable undefined in some theme configurations
- Inline style bindings harder to override than CSS classes
- Inconsistent patterns: some use [style.X] bindings, some use CSS classes

**Acceptance Criteria:**
- Confirm all theme variables exist in theme definitions
- Identify any pattern inconsistencies
- Recommend standardization approach | 2026-01-22 | 2026-01-22 |
| 260122193029 | DONE | P2 | M | code | **Jules Sessions:** 1274029087648840399

**Summary:** Session adds `is_reusable` column back to the browser SQLite INSERT statement for resource_definitions.

**Deep Review Questions:**
1. **Root Cause Analysis:** Why was `is_reusable` removed previously? Was it intentional schema change or accidental deletion?
2. **Schema Alignment:** Does the browser sqlite.service.ts schema match:
   - The production PostgreSQL schema (Alembic migrations)
   - The OpenAPI spec (for API-generated types)
   - The PLR_RESOURCE_DEFINITIONS seed data structure
3. **Single Source of Truth:** Should there be a shared schema definition that generates both browser and production schemas?
4. **Testing Gap:** Is there automated testing to catch schema drift between browser and production modes?
5. **OpenAPI Generation:** Should `npm run generate-api` regenerate types that include this field?

**Risks:**
- Band-aid fix: patching INSERT statement without addressing root cause
- Schema drift: browser and production schemas may diverge again
- Missing field in API types could cause runtime errors

**Acceptance Criteria:**
- Document schema alignment status
- Recommend permanent solution (shared schema definition or automated sync)
- Identify if additional fields are missing | 2026-01-22 | 2026-01-23 00:40:46 |
| 260122193039 | IN_PROGRESS | P1 | M | code | **BLOCKING BUILD ERROR - Elevated from Jules Session Review**

## 🚨 BLOCKING ISSUES DISCOVERED (Jan 22, 2026)

**1. Build Error - Missing File:**
```
cp: cannot stat 'src/assets/jupyterlite/jupyter-lite.gh-pages.json': No such file or directory
```
- The file exists locally but may NOT be tracked in git
- GitHub Actions fails on fresh checkout

**2. Base Href Navigation Bug:**
- `/praxis/` redirects to `/app/home` instead of `/praxis/app/home`
- Angular Router ignoring baseHref during navigation
- Likely in splash.component.ts or app.routes.ts redirect logic

**3. Logo Data URI Rendering (Unknown):**
- Logo uses inline SVG data URI in splash.component.ts and unified-shell.component.ts
- Cannot verify rendering until build succeeds

## Related Jules Sessions
- 10286476551144916116: Proposes replacing `cp` with Python patching script
- 6905771359917291210: Package-lock.json peer:true removals

## Investigation Questions
1. **File Status:** Is `jupyter-lite.gh-pages.json` tracked in git?
2. **Navigation Fix:** Check `router.navigate()` calls - are they using absolute paths without respecting baseHref?
3. **Jules Session 10286476551144916116:** This session proposes replacing the `cp` command with a Python patching script - is this the right fix?

## Acceptance Criteria
- [ ] Build passes in GitHub Actions
- [ ] `/praxis/` correctly shows splash OR redirects to `/praxis/app/home`
- [ ] Logo renders correctly on deployed site
- [ ] JupyterLite/REPL loads without 404s | 2026-01-22 | 2026-01-23 00:34:55 |
| 260122193051 | TODO | P2 | M | code | **Jules Sessions:** 11264751302847526296

**Summary:** Session modifies python.worker.ts to add pyodide_io_patch.py to the shims list and explicitly imports it after shim loading. Also has a concerning duplicate method in web_serial_shim.py.

**Deep Review Questions:**
1. **Regression Check:** The diff shows web_serial_shim.py has a duplicate `async def read()` method removed then re-added. Is this a merge artifact or intentional?
2. **IO Patch Purpose:** What does pyodide_io_patch.py do? Is it required for serial/USB/HID communication in browser mode?
3. **Shim Loading Order:** Does the order of shim loading matter? Should pyodide_io_patch be loaded before or after hardware shims?
4. **Current Shim Status:** Check KI (state/io_shimming_status.md) for current shimming architecture and whether this aligns.
5. **Worker Initialization:** Is the explicit `import pyodide_io_patch` after shim loading the correct pattern?

**Risks:**
- Duplicate method breaks serial communication
- IO patch may conflict with existing WebSerial/WebUSB/WebHID shims
- Order-dependent initialization bugs

**Acceptance Criteria:**
- Confirm web_serial_shim.py state (should have single read method)
- Verify pyodide_io_patch.py purpose and necessity
- Recommend extract/reject/partial-apply | 2026-01-22 | 2026-01-22 |
| 260122193057 | TODO | P2 | M | code | **Jules Sessions:** 15855936720499606576, 6070242121770811241, 15327645851105609408, 10702741255854910008, 1658842845177458112, 12156375213058893132, 17260636961604471221

**Summary:** 7 sessions making documentation and repository cleanup changes:
- Cross-reference sentences in roadmap files
- uvicorn command standardization (adding --port 8000)
- File path corrections (praxis/praxis/ -> praxis/)
- Docker service name fixes (db -> praxis-db)
- CONTRIBUTING.md command updates (make -> uv run)
- Archive RUNWAY.md to .agent/archive/
- Move port_docstrings.py to scripts/

**Deep Review Questions:**
1. **Accuracy Check:** Are the new paths correct? Does `praxis/web-client` exist or is it `praxis/praxis/web-client`?
2. **Docker Service Names:** Is the service actually named `praxis-db` in compose.yaml or is this an error?
3. **Command Migration:** The CONTRIBUTING.md changes from `make` to `uv run` - is the Makefile deprecated?
4. **Backup File Creation:** Session 15327645851105609408 creates quickstart.md.bak - should this be deleted instead of committed?
5. **Archive Pattern:** Is .agent/archive/ the correct location for RUNWAY.md?

**Risks:**
- Low risk changes but high volume
- Potential inaccuracies if source of truth wasn't verified
- May introduce inconsistencies if partially applied

**Acceptance Criteria:**
- Verify docker-compose.yaml service names
- Verify correct paths in codebase
- Batch all valid changes for atomic commit | 2026-01-22 | 2026-01-22 |
| 260122193100 | DONE | P2 | M | code | **Jules Sessions:** 6905719756252915550

**Summary:** Fixes the `isMachineRequirement()` method to correctly identify PlateReader as a machine (not a resource), and adds comprehensive unit tests.

**Deep Review Questions:**
1. **Fix Correctness:** The change adds `&& !lowerCat.includes('reader')` to the plate exclusion. Does this correctly handle:
   - PlateReader (should be machine) ✓
   - Plate (should NOT be machine) ✓
   - MyPlateReader (should be machine) ✓
   - PlateReaderCarrier (edge case?)
2. **Test Coverage:** Do the tests cover all PLRCategory values that exist?
3. **Regression Risk:** Could this fix break other categorization logic?
4. **Underlying Architecture:** Is string-based category matching the right approach, or should there be explicit machine category enums?

**Risks:**
- Low risk, well-tested fix
- String matching is fragile long-term

**Acceptance Criteria:**
- Verify fix logic is sound
- Confirm tests pass
- Note any architectural debt for future refactoring | 2026-01-22 | 2026-01-23 13:30:06 |
| 260122193102 | TODO | P2 | M | code | **Jules Sessions:** 16838706707851110095, 13244136027907636654

**Summary:** Two sessions improving test infrastructure:
- Move test-results gitignore from root to web-client
- Enable screenshots on all test runs (not just failures)
- Add outputDir to playwright config

**Deep Review Questions:**
1. **GitIgnore Deduplication:** Is it correct to remove patterns from root .gitignore if they're in web-client/.gitignore?
2. **Screenshot Strategy:** Is `screenshot: 'on'` appropriate for CI? This increases artifact size significantly.
3. **Output Directory:** Does `outputDir: 'test-results/'` conflict with existing path expectations?
4. **Agent Workflow:** Does this align with the jules_playwright_guide.md in the E2E testing KI?

**Risks:**
- Low risk infrastructure changes
- Screenshot overhead on CI may slow builds

**Acceptance Criteria:**
- Verify paths are correct
- Confirm CI implications
- Apply as atomic infra commit | 2026-01-22 | 2026-01-22 |
| 260122193107 | TODO | P2 | M | code | **Jules Sessions:** 5219871126636334321

**Summary:** Creates a new gradient-styled SVG logo at `assets/logo/praxis_logo_gradient.svg`.

**Deep Review Questions:**
1. **Quality Check:** Is the SVG well-formed with proper gradient definitions?
2. **Integration:** Are there components that should use this logo? (app header, splash screen, etc.)
3. **Existing Logo:** What logo is currently being used? Is this a replacement or addition?
4. **Brand Consistency:** Does the gradient (ED7A9B -> ff8fa8 -> 73A9C2) match the documented brand palette?

**Risks:**
- Zero risk, new asset only

**Acceptance Criteria:**
- Verify SVG renders correctly
- Document where logo should be used
- Apply immediately | 2026-01-22 | 2026-01-22 |
| 260123084748 | TODO | P1 | easy | research | Research the official @sqlite.org/sqlite-wasm package and document the available Virtual File System (VFS) options:

1. Analyze `opfs` VFS (requires SharedArrayBuffer + COOP/COEP headers)
2. Analyze `opfs-sahpool` VFS (better browser compatibility)
3. Document browser compatibility matrix for each option
4. Research COOP/COEP header requirements and implications for our deployment
5. Create a decision document at `.agent/research/opfs_vfs_decision.md`

**Deliverable**: Research document with VFS recommendation for Praxis. | 2026-01-23 | 2026-01-23 |
| 260123084756 | DONE | P1 | easy | research | **OPFS-1: Research and Document OPFS VFS Options**

Research the official @sqlite.org/sqlite-wasm package and document the available Virtual File System (VFS) options:

1. Analyze `opfs` VFS (requires SharedArrayBuffer + COOP/COEP headers)
2. Analyze `opfs-sahpool` VFS (better browser compatibility)
3. Document browser compatibility matrix for each option
4. Research COOP/COEP header requirements and implications for our deployment
5. Create a decision document at `.agent/research/opfs_vfs_decision.md`

**Deliverable**: Research document with VFS recommendation for Praxis.

**Dependencies**: None (this is the first task)
**Blocks**: OPFS-2, OPFS-3 | 2026-01-23 | 2026-01-23 15:12:53 |
| 260123084806 | DONE | P1 | easy | agent | Replace the sql.js dependency with the official SQLite WASM package:

1. Remove `sql.js` and `@types/sql.js` from package.json
2. Add `@sqlite.org/sqlite-wasm` to package.json
3. Update Angular asset configuration to copy WASM files
4. Verify WASM files are correctly served in development mode
5. Update any build scripts that reference sql.js

**Files to modify**:
- `praxis/web-client/package.json`
- `praxis/web-client/angular.json` (asset configuration)

**Testing**: Build should complete without errors. | 2026-01-23 | 2026-01-23 15:12:53 |
| 260123084811 | DONE | P1 | medium | agent | Create a dedicated Web Worker for SQLite OPFS operations:

1. Create `praxis/web-client/src/app/core/workers/sqlite-opfs.worker.ts`
2. Implement worker initialization with @sqlite.org/sqlite-wasm
3. Set up OPFS VFS (use opfs-sahpool for compatibility)
4. Implement message protocol for DB operations:
   - `init`: Initialize database
   - `exec`: Execute SQL statements
   - `prepare`/`run`: Prepared statements
   - `export`: Export database to Uint8Array
   - `import`: Import database from Uint8Array
5. Add TypeScript types for worker messages

**Files to create**:
- `praxis/web-client/src/app/core/workers/sqlite-opfs.worker.ts`
- `praxis/web-client/src/app/core/workers/sqlite-opfs.types.ts`

**Testing**: Worker should initialize without errors in browser console. | 2026-01-23 | 2026-01-23 15:50:39 |
| 260123084815 | TODO | P1 | medium | agent | Create an Angular service that wraps the OPFS worker with Observables:

1. Create `praxis/web-client/src/app/core/services/sqlite-opfs.service.ts`
2. Implement worker lifecycle management (start/terminate)
3. Create Observable-based API matching current SqliteService interface:
   - `getDatabase()`: Returns proxy for DB operations
   - `getRepositories()`: Same typed repository pattern
   - All repository accessors (protocolRuns, machines, etc.)
4. Handle worker message serialization/deserialization
5. Implement error handling and retry logic

**Files to create**:
- `praxis/web-client/src/app/core/services/sqlite-opfs.service.ts`

**Testing**: Unit tests should pass. | 2026-01-23 | 2026-01-23 |
| 260123084820 | TODO | P1 | medium | agent | Refactor the repository layer to work with both sync (sql.js) and async (worker) patterns:

1. Create `praxis/web-client/src/app/core/db/sqlite-worker-repository.ts`
2. Implement proxy pattern to send SQL to worker and receive results
3. Ensure type compatibility with existing Repository interfaces
4. Handle prepared statements via worker messaging

**Files to modify**:
- `praxis/web-client/src/app/core/db/sqlite-repository.ts` (extract interface)
- `praxis/web-client/src/app/core/db/repositories.ts` (add factory)

**Files to create**:
- `praxis/web-client/src/app/core/db/sqlite-worker-repository.ts`

**Testing**: Repository operations should work identically. | 2026-01-23 | 2026-01-23 |
| 260123084825 | TODO | P1 | medium | agent | Create migration logic to move existing data from IndexedDB to OPFS:

1. Add migration check on first load with new system
2. Detect existing `praxis_db` in IndexedDB
3. Export existing db.export() data
4. Import into OPFS using worker
5. Mark migration as complete
6. Clean up old IndexedDB data (optional, after validation)

**Files to create**:
- `praxis/web-client/src/app/core/db/opfs-migration.service.ts`

**Files to modify**:
- `praxis/web-client/src/app/core/services/sqlite-opfs.service.ts`

**Testing**: Existing browser data should survive upgrade. | 2026-01-23 | 2026-01-23 |
| 260123084828 | DONE | P2 | easy | agent | Create feature flag system to toggle between old and new implementations:

1. Add `SQLITE_OPFS_ENABLED` environment variable
2. Create provider factory that selects SqliteService or SqliteOpfsService
3. Add localStorage override for testing (`praxis_use_opfs`)
4. Add UI toggle in Settings page for advanced users
5. Default to old implementation, opt-in to OPFS

**Files to modify**:
- `praxis/web-client/src/environments/environment.ts`
- `praxis/web-client/src/environments/environment.prod.ts`
- `praxis/web-client/src/app/app.config.ts` (or providers module)
- Settings component

**Testing**: Both implementations should be selectable. | 2026-01-23 | 2026-01-23 17:14:20 |
| 260123084831 | TODO | P2 | easy | agent | Create Playwright E2E tests to validate OPFS implementation:

1. Test database persistence across page refreshes
2. Test large data handling (>50MB synthetic test)
3. Test migration from IndexedDB
4. Test export/import functionality
5. Test concurrent tab behavior

**Files to create**:
- `praxis/web-client/e2e/specs/opfs-persistence.spec.ts`

**Testing**: All E2E tests should pass in headed mode. | 2026-01-23 | 2026-01-23 |
| 260123084833 | TODO | P3 | easy | agent | Update architecture documentation to reflect new OPFS implementation:

1. Update `backend-browser.md` with OPFS details
2. Update `overview-browser.md` with new persistence model
3. Add troubleshooting guide for OPFS issues
4. Document browser compatibility requirements
5. Update any diagrams showing data flow

**Files to modify**:
- `praxis/web-client/src/assets/docs/architecture/backend-browser.md`
- `praxis/web-client/src/assets/docs/architecture/overview-browser.md`

**Files to create**:
- `praxis/web-client/src/assets/docs/troubleshooting/opfs-storage.md`

**Testing**: Documentation builds correctly. | 2026-01-23 | 2026-01-23 |
| 260123084837 | TODO | P3 | easy | agent | After OPFS is stable and validated, remove old sql.js implementation:

1. Remove sql.js related services and code
2. Remove SqlitePersistenceService (IndexedDB-based)
3. Update all imports and references
4. Remove feature flag logic (make OPFS the only option)
5. Final cleanup of package.json

**NOTE**: Only execute after OPFS has been validated in production for 2+ weeks.

**Files to delete**:
- `praxis/web-client/src/app/core/db/sqlite-persistence.service.ts`

**Files to modify**:
- `praxis/web-client/src/app/core/services/sqlite.service.ts` (rename/replace)

**Testing**: Full test suite passes. | 2026-01-23 | 2026-01-23 |
| 260123091500 | TODO | P1 | hard | agent | Fix Pyodide bootstrapping instability causing BadZipFile and ModuleNotFoundError. Verify reliable wheel loading and praxis module injection. High priority, to be done after VFS refactoring. | 2026-01-23 14:18:12 | 2026-01-23 14:18:12 |
| 260123104210 | TODO | P1 | medium | deep-researcher | Investigate why the Praxis logo renders as a gradient blob instead of the 'P' shape in GH-Pages deployment.

**Symptoms:**
- Logo appears as a colored rectangle/gradient square
- The '-webkit-mask-size: contain' fix was applied but still not working

**Investigation Areas:**
1. Verify CSS variable `--logo-svg` is correctly populated at runtime (inspect in DevTools)
2. Check if the SVG viewBox/path in the data URI is valid and renderable
3. Test if mask-image shorthand works vs explicit mask-image property
4. Compare behavior between Chrome/Safari/Firefox
5. Verify the SVG data URI encoding is correct (check for malformed URL encoding)

**Files to inspect:**
- `src/app/shared/constants/logo.ts` - the SVG data URI
- `src/app/layout/unified-shell.component.ts` - logo styling lines 270-279
- `src/app/features/splash/splash.component.ts` - logo styling lines 258-267

**Output:** Root cause analysis and recommended fix approach. | 2026-01-23 | 2026-01-23 |
| 260123104237 | TODO | P2 | M | code | RECON: Diagnose Logo SVG Mask Rendering Failure - Investigate why the Praxis logo renders as a gradient blob instead of the 'P' shape in GH-Pages deployment. Symptoms: Logo appears as colored rectangle. Investigation: (1) Verify --logo-svg CSS var populated at runtime, (2) Check SVG viewBox/path validity, (3) Test mask-image shorthand vs explicit, (4) Verify URL encoding. Files: logo.ts, unified-shell.component.ts L270-279, splash.component.ts L258-267. | 2026-01-23 | 2026-01-23 |
| 260123104239 | TODO | P2 | M | code | FIX: JupyterLite Pyodide Kernel Auto-Start in GH-Pages - Pyodide kernel doesn't auto-initialize; user must manually select. Compare dev vs prod JupyterLite config for kernel settings. Verify kernel=python URL param passed through iframe. Files: repl/jupyter-lite.json, jupyter-lite.gh-pages.json, repl.component.ts. | 2026-01-23 | 2026-01-23 |
| 260123104241 | TODO | P2 | M | code | FIX: Environment Bootstrap Script Injection in GH-Pages - Bootstrap code (micropip, shims, praxis module) isn't running in prod. Locate boot script injection in repl/playground component, compare dev vs prod behavior, fix timing/path issues. May depend on OPFS task 260123084831. | 2026-01-23 | 2026-01-23 |
| 260123104243 | TODO | P2 | M | code | CREATE: E2E Test repl-loading.spec.ts - Basic smoke test: navigate to /app/playground, wait for kernel idle status, run print('Hello'), verify output. Reference interactive-protocol.spec.ts patterns. | 2026-01-23 | 2026-01-23 |
| 260123104247 | TODO | P2 | M | code | FIX: Theme CSS Path Doubling in JupyterLite - Cosmetic 404 for themes/@jupyterlab/theme-light-extension/index.css shows path doubling /assets/jupyterlite/assets/jupyterlite/. Fix themesUrl config resolution in jupyter-lite.json and config-utils.js. | 2026-01-23 | 2026-01-23 |
| 260123110821 | DONE | P1 | medium | code | Create SqliteOpfsService Angular service to wrap the sqlite-opfs.worker.ts. The service acts as the bridge between Angular app code (main thread) and the Web Worker. Requirements:

1. **File Location**: `src/app/core/services/sqlite-opfs.service.ts`

2. **Core API**:
   - `init(dbName?: string): Observable<void>` - Initialize worker and database
   - `exec<T>(sql: string, bind?: any[], rowMode?: RowMode): Observable<SqliteExecResult>` - Execute SQL
   - `exportDatabase(): Observable<Uint8Array>` - Export database as binary
   - `importDatabase(data: Uint8Array): Observable<void>` - Import database from binary
   - `close(): Observable<void>` - Close database and terminate worker

3. **Implementation Details**:
   - Use `Subject<SqliteWorkerResponse>` to handle incoming worker messages
   - Create unique request IDs using `crypto.randomUUID()` for request/response correlation
   - Filter responses by ID to match requests with their responses
   - Use `firstValueFrom()` or `Observable.pipe(take(1))` patterns for one-shot operations
   - Handle errors by checking response type === 'error' and throwing appropriately
   - Provide `Injectable({ providedIn: 'root' })` for singleton usage

4. **Worker Management**:
   - Lazy worker instantiation in the `init()` call
   - Worker path should use `assetUrl()` utility for correct GitHub Pages base path
   - Terminate worker on `close()` and clean up references

5. **Type Imports**: Import types from `../workers/sqlite-opfs.types`

6. **Reference**: See worker protocol in `src/app/core/workers/sqlite-opfs.worker.ts` and `sqlite-opfs.types.ts` | 2026-01-23 | 2026-01-23 16:13:22 |
| 260123111736 | TODO | P1 | easy | code | Logo Rendering Recon: Inspect the live Angular simulation (http://localhost:8080/praxis/) to identify why the CSS mask logo appears as a solid gradient blob. Tasks: (1) Inspect the .logo-mark or .logo-image element's computed styles, (2) Check if --logo-svg variable is populated correctly, (3) Look for Angular sanitization artifacts (e.g., 'unsafe:' prefix in mask-image), (4) Check browser console for sanitization warnings, (5) Compare with repro_logo.html behavior. Report findings and await approval before proceeding to implementation. | 2026-01-23 | 2026-01-23 |
| 260123111746 | TODO | P1 | easy | code | Logo Rendering Recon: Inspect the live Angular simulation (http://localhost:8080/praxis/) to identify why the CSS mask logo appears as a solid gradient blob. Tasks: (1) Inspect the .logo-mark or .logo-image element's computed styles, (2) Check if --logo-svg variable is populated correctly, (3) Look for Angular sanitization artifacts (e.g., 'unsafe:' prefix in mask-image), (4) Check browser console for sanitization warnings, (5) Compare with repro_logo.html behavior. Report findings and await approval before proceeding to implementation. | 2026-01-23 | 2026-01-23 |
| 260123111747 | TODO | P1 | easy | code | Logo Rendering Plan: Based on recon findings, create an implementation plan to fix the logo rendering in SplashComponent and UnifiedShellComponent. Consider: (1) DomSanitizer.bypassSecurityTrustStyle() for the SVG data URI, (2) Moving from [style.--logo-svg] binding to direct style application, (3) Alternative approaches like inline SVG or static mask-image. Document the plan and await user approval before execution. | 2026-01-23 | 2026-01-23 |
| 260123111750 | DONE | P1 | medium | code | Logo Rendering Fix: Fixed the Praxis logo rendering in GitHub Pages deployment. Root cause was CSS syntax error from unescaped single quotes in SVG data URI. Fixed by changing url() wrapper quotes from single to double in `unified-shell.component.ts` and `splash.component.ts`. Verified fix in GH-Pages simulation (http://localhost:8080/praxis/) - 'P' shape now renders correctly instead of solid gradient blob. | 2026-01-23 | 2026-01-23 18:12:32 |
| 260123122224 | TODO | P1 | medium | agent | OPFS-8: E2E Testing - Create Playwright tests for OPFS persistence stability and IndexedDB-to-OPFS migration. Verify toggle → create data → reload → data persists workflow. Test migration path and graceful degradation when OPFS unavailable. | 2026-01-23 | 2026-01-23 |
| 260123122228 | TODO | P2 | easy | agent | OPFS-9: Documentation Update - Update architecture docs for SqliteOpfsService worker, create troubleshooting guide for OPFS failures, update knowledge base artifacts. Cover worker message protocol, feature flag behavior, and common failure modes. | 2026-01-23 | 2026-01-23 |
