# Technical Debt
<!-- Migrated to MCP database on 2026-01-21 -->

This document tracks known issues, temporary patches, and required follow-up work for the Praxis project.

## Models & Database

- [x] **SQLModel/PostgreSQL Verification**: Unified `PraxisBase` and Alembic metadata integration have only been verified against SQLite. Full verification against a live PostgreSQL instance is required when infrastructure is available. <!-- id: 101 --> *(Migrated to `.agent/tasks/260115_tech_debt/database_models/`)*
- [x] **Silence SQLModel Field Shadowing Warnings**: Silence `UserWarning: Field name "..." in "..." shadows an attribute in parent "..."`. <!-- id: 102 --> *(Migrated to `.agent/tasks/260115_tech_debt/database_models/`)*
  - Reason: Field re-declarations (e.g., `deck_accession_id` in `DeckRead`) are necessary for the current architecture but trigger runtime warnings in SQLModel.
  - Priority: Medium
  - Notes: Investigate using `warnings.filterwarnings` or SQLModel configuration to suppress these specific shadowing warnings while keeping other warnings active.

## Tests

- [x] Review REPL tests in `tests/core/test_repl_session.py` and migrate them to a frontend/integration test suite; these tests require PyLabRobot runtime and interactive imports and are skipped in backend CI.<!-- id: 201 --> *(Migrated to `.agent/backlog/testing.md`)*
  - Reason: REPL depends on environment and GUI/interactive backends that belong to integration or frontend testing.
  - Owner: TBD
  - Priority: low
  - Notes: Consider creating a small Docker-based integration job that installs `pylabrobot` and runs these tests in an environment that can import hardware simulation backends.

## Backend Sync

- [x] **Backend Test & File Sync**: Update backend tests and files implicated by recent schema and naming convention changes (e.g., `_json` suffix alignment and `ProtocolRunRead` field additions). <!-- id: 301 --> *(Migrated to `.agent/tasks/260115_tech_debt/backend_sync/`)*
  - Reason: Frontend schema alignment (SQLModel unification) has introduced discrepancies in backend expectations.
  - Priority: Medium
  - Notes: Ensure that all backend repositories, services, and tests are updated to handle the new field names and consistent JSONB suffixing.

## Frontend / Web Client

- [x] **Audit "as any" Usage**: unexpected uses of `any` and `as any` have proliferated in the web client codebase, particularly in services interfacing with the API (e.g., `simulation-results.service.ts`). <!-- id: 401 --> *(Migrated to `.agent/tasks/260115_tech_debt/frontend_type_safety/`)*
  - Reason: Urgent schema alignment required bypassing some type checks. These patches reduce type safety and need to be resolved by proper type definitions.
  - Priority: Medium
  - Notes: Search for `as any` and `: any` in `praxis/web-client/src`. Replace with proper types from `schema.ts` or dedicated interfaces.

## Agentic Infrastructure

- [x] **Maintenance Audit Prompt**: Create a generic reusable prompt that conducts audits to see what maintenance or other reusable prompts should be used, or if the `.agent/archive` needs to be decluttered. <!-- id: 501 --> *(Migrated to `.agent/backlog/agentic_infrastructure.md`)*
  - Reason: Ensure the agentic workspace remains clean, efficient, and that common maintenance tasks are standardized through reusable prompts.
  - Priority: Low
  - Notes: This prompt should analyze the state of `.agent/prompts`, `.agent/archive`, and `.agent/artifacts` to suggest cleanup or improvements.
- [x] **Structured Agentic Multi-Stage Workflow**: Implement a new skill or reusable prompt that formalizes the end-to-end development cycle. <!-- id: 502 --> *(Migrated to `.agent/backlog/agentic_infrastructure.md`)*
  - Reason: Improve consistency and traceability of complex feature implementations by breaking them into discrete, auditable stages.
  - Priority: Medium
  - Notes: The workflow should follow this strict process:
    1. **Clarifying Questions**: Agent asks clarifying questions to fully understand the user's goals/issues.
    2. **Specification & Inspection**: Once the issue is fully specified, use inspection prompts to generate discovery artifacts (output to `.agent/artifacts`). Update backlog and `DEVELOPMENT_MATRIX.md` as appropriate.
    3. **Planning**: Use discovery artifacts to spawn in-depth planning prompts.
    4. **Implementation**: Planning prompts spawn implementation prompts (leveraging templates like `agent_prompt.md`). It is from these prompts that issues are resolved.
    - **Action Item**: Create an artifact template (`.agent/templates/artifact.md`) as we currently lack one.
- [x] **.agent folder optimization and workflow redesign**: Consolidate the I-P-E-T (Inspect-Plan-Execute-Test) workflow into unified task directories/prompts and remove redundant context instructions. <!-- id: 504 --> *(Migrated to `.agent/backlog/agentic_infrastructure.md` - Partially implemented via `unified_task.md` template)*
  - Reason: The current multi-file I-P-E structure is becoming fragmented. Moving to a directory-based "Task" structure with unified prompts improves traceability and allows for better state management across start/stop cycles.
  - Priority: Medium
  - Notes: Redefine prompt templates to include all phases (Inspect/Plan/Execute/Test) in a single document with clear stage-gates. Transition from flat `.agent/prompts/YYMMDD/` to `.agent/tasks/task_name/` or similar.
- [x] **Project Management Separation of Concerns**: Establish single sources of truth for items at each scale (Roadmap, Matrix, Backlog, Artifacts, Prompts). <!-- id: 503 --> *(Migrated to `.agent/backlog/agentic_infrastructure.md`)*
  - Reason: Prevent desyncing between different levels of project tracking.
  - Priority: Low
  - Notes: Define clear boundaries:
    - `ROADMAP.md`: Strategic phases and high-level milestones.
    - `DEVELOPMENT_MATRIX.md`: Current iteration work items with priority/difficulty.
    - `backlog/`: Detailed tracking of specific issues.
    - `artifacts/`: Design documents and discovery outputs.
    - `prompts/`: actionable execution units.
    - Ensure processes (like the Multi-Stage Workflow) enforce updating the correct document type at the correct stage.

## Schema & Browser Mode

- [x] **Data Model Alignment**: The `is_reusable` column was removed from the frontend's browser-mode database to match the current backend schema. It needs to be officially added to the backend models and then reintroduced to the frontend. <!-- id: 601 --> *(Migrated to `.agent/tasks/260115_tech_debt/schema_alignment/`)*
  - Reason: `is_reusable` is used in the frontend UI but is missing from the backend source-of-truth. It was temporarily patched via migration but removed for strict schema compliance.
  - Priority: Medium
  - Notes:
    1. Update Backend `ResourceDefinition` model to include `is_reusable: bool`.
    2. Generate migration (Alembic).
    3. Update `schema.sql` (generated).
    4. Re-enable usage in `SqliteService` (add to `INSERT`, enable in `ResourceDefinition` interface).

## Protocols & Logic

- [x] **Selective Transfer Heuristic Replacement**: "Selective Transfer" protocols are currently detected via string matching on name/FQN. This must be replaced by formal backend metadata capabilities. <!-- id: 701 --> *(Migrated to `.agent/backlog/protocol_heuristics.md`)*
  - Reason: Heuristics are brittle. Logic needs to be explicit in `ProtocolDefinition` (e.g. `requires_linked_indices: boolean`).
  - Priority: Low
  - Notes: See `protocol_execution_ux_plan.md` for context.

- [x] **(Backend/Python)**: Replace hardcoded geometry heuristics in `web_bridge.py` with database-driven lookups via `resolved_assets_spec`. <!-- id: 702 --> *(Migrated to `.agent/backlog/protocol_heuristics.md`)*
  - Reason: Currently `web_bridge.py` assumes all plates are 96-well. We implemented a heuristic workaround in the factory pattern refactor, but it should read dimensions from the definition database.
  - Priority: Medium
  - Notes: See `web_bridge.py` lines 70-100.

- [x] **(Backend/Python)**: Audit and replace hardcoded simulation values in `web_bridge.py` and `ExecutionService`. <!-- id: 703 --> *(Migrated to `.agent/backlog/protocol_heuristics.md`)*
  - Reason: Several places in the browser execution bridge rely on hardcoded defaults/mocks rather than reading from the configured definitions.
  - Priority: Low

- [x] **(Backend/Python)**: Audit and replace hardcoded simulation values across the codebase. <!-- id: 704 --> *(Migrated to `.agent/backlog/protocol_heuristics.md`)*
  - Reason: Several places in the rely on hardcoded defaults/mocks rather than reading from the configured definitions in the database.
  - Priority: Low

## Browser Mode & Resource Management

- [ ] **Infinite Consumables Implementation**: The `infiniteConsumables` flag currently only affects UI display (∞ symbol), not actual resource behavior. <!-- id: 901 -->
  - Reason: When enabled, consumables should auto-replenish or allow on-the-fly instantiation during protocol execution/asset selection.
  - Priority: Medium
  - Current State: UI shows ∞, but users still need actual resource instances
  - Proposed Behavior:
    - During asset selection: Allow custom-named instances to be created on-the-fly
    - During execution: Auto-replenish consumed instances (browser mode) or don't track depletion
    - Track "consumed count" separately from "available instances" for analytics
  - Notes: This would eliminate need for creating multiple tip rack instances and improve browser mode UX

## Development Process & Tooling

- [ ] **Alembic Migration Workflow Without Live Database**: Improve workflow for generating Alembic migrations when PostgreSQL infrastructure is unavailable. <!-- id: 1001 -->
  - Reason: `alembic revision --autogenerate` requires active database connection, blocking schema development when infrastructure isn't running.
  - Priority: Medium
  - Current Blockers:
    - Autogenerate requires connecting to PostgreSQL (configured in alembic.ini)
    - `--sql` flag incompatible with `--autogenerate`
    - Using SQLite via `DATABASE_URL="sqlite+aiosqlite:///./test.db"` requires existing migrations to be applied first
    - Batch operations on non-existent tables cause reflection errors
  - What Worked (2026-01-16 - TD-601 implementation):
    - Manual migration creation following existing migration patterns
    - Using `scripts/generate_browser_schema.py` for browser schema (works without DB)
    - Creating SQLite test DB then upgrading with existing migrations before autogenerate (partially successful)
  - What Didn't Work:
    - `alembic revision --autogenerate --sql` (flags incompatible)
    - Direct autogenerate without database (no 'script_location' error when run from wrong directory)
    - Fresh SQLite DB with autogenerate (tables don't exist for batch reflection)
  - Lessons Learned:
    - Alembic env.py tries to connect even for autogenerate (not offline mode)
    - Manual migrations are reliable but require understanding of SQLAlchemy column types
    - Browser schema generation is decoupled and works independently
  - Proposed Solutions:
    1. Document manual migration workflow in developer docs
    2. Create helper script: `scripts/create_migration.py` that:
       - Accepts model diffs as input
       - Generates migration file from template
       - Auto-increments revision IDs
    3. Add offline mode support to alembic env.py for autogenerate
    4. Use SQLite in-memory DB for autogenerate when PostgreSQL unavailable
    5. Set up lightweight PostgreSQL container for development (docker-compose)
  - Files:
    - `alembic/env.py` - Migration environment config
    - `alembic.ini` - Database URL configuration
    - `scripts/generate_browser_schema.py` - Working offline schema generator

## State Inspection & Reporting

- [x] **State History Storage Optimization**: Current backend state inspection stores full JSON snapshots for every decorated function call. <!-- id: 801 --> *(Migrated to `.agent/tasks/260115_feature_enhancements/state_inspection_backend/` - noted as risk mitigation)*
  - Reason: For long protocols, this will cause database bloat.
  - Priority: Medium
  - Notes: Implement state delta compression (diffing) or optional "trace mode" flags.
- [x] **PLR to UI State Transformation**: The backend currently passes raw `serialize_state()` from PyLabRobot objects directly to the UI. <!-- id: 802 --> *(Migrated to `.agent/tasks/260115_feature_enhancements/state_inspection_backend/` - noted as risk mitigation)*
  - Reason: `DeckViewComponent` expects a specific format (e.g. `volumes` array), while PLR might provide lists of tuples.
  - Priority: Medium
  - Notes: Implement a formal transformation layer in `WorkcellRuntime` or `ExecutionMixin` to ensure consistent data structures for the frontend.
- [x] **Interactive Timeline Updates**: The "Operation Timeline" in the Run Detail view is currently static (loaded after the run or periodically). <!-- id: 803 --> *(Migrated to `.agent/tasks/260115_feature_enhancements/state_inspection_backend/` - future enhancement)*
  - Reason: It should ideally update via WebSockets as operations complete.
  - Priority: Low
  - Notes: Emit `operation_complete` events with step details over the execution WebSocket.

# Technical Debt Log

## E2E Testing

- [ ] **Data Seeding in Browser Mode**: The E2E tests for charts (`medium-priority-capture.spec.ts`) fail because the mock database is not reliably seeded with protocol runs when `resetdb=true` is used. This prevents the "Capture Charts" test from finding protocol cards to execute.
  - **Impact**: Cannot automatically validate charts/visualizations in E2E pipeline.
  - **Mitigation**: Manually verify charts or fix `SqliteService` seeding logic in browser mode.

## Browser Execution

- [ ] **Browser Protocol Interruption**: `PythonRuntimeService.interrupt()` is currently a placeholder - cannot kill browser-mode execution without terminating and restarting the Web Worker. <!-- id: 1101 -->
  - Reason: The `stopRun()` method works for backend executions but browser-side interruption is marked as TODO.
  - Priority: Medium
  - Files: `praxis/web-client/src/app/core/services/python-runtime.service.ts`
  - Notes: Will likely require `pyodide.setInterruptBuffer` or similar signaling mechanism within the worker's event loop.

- [ ] **Pause/Resume Protocol Execution**: No implementation exists for pausing or resuming a running Pyodide worker. <!-- id: 1102 -->
  - Reason: LiveDashboard lacks Pause/Resume buttons, and no service methods exist.
  - Priority: Medium
  - Files: `praxis/web-client/src/app/features/run-protocol/services/execution.service.ts`, `praxis/web-client/src/app/features/run-protocol/components/live-dashboard.component.ts`
  - Notes: Required for complete browser-mode protocol execution control.

- [ ] **Browser Protocol Execution Architecture Review**: Current approach uses cloudpickle to serialize decorated protocol functions; Pyodide needs stub modules for `praxis.backend.*` to satisfy import references. <!-- id: 1103 -->
  - Reason: Created minimal stubs in `praxis/web-client/src/assets/python/praxis/backend/` but this increases bundle size and maintenance burden.
  - Priority: Medium
  - Files: `praxis/web-client/src/app/core/workers/python.worker.ts`, `praxis/web-client/src/assets/python/praxis/backend/`
  - Research Alternatives:
    1. Serialize raw functions before decoration
    2. Generate browser-compatible code at build time
    3. Use `cloudpickle.register_pickle_by_value()` selectively
    4. Create browser-specific `@browser_protocol` decorator


## Hardware Integration

- [ ] **Backend Machine Registration Placeholder**: The `register_machine` endpoint in the backend API is a placeholder - discovered hardware cannot be formally added to the system database via the UI. <!-- id: 1201 -->
  - Reason: Endpoint at line 458 in `praxis/backend/api/hardware.py` has TODO comment.
  - Priority: Medium
  - Notes: "TODO: Integrate with MachineService to create actual machine record."

- [ ] **REPL for Real Hardware Not Implemented**: Interactive hardware control via REPL is not yet implemented for real hardware. <!-- id: 1202 -->
  - Reason: `execute_repl_command` at line 503 in `praxis/backend/api/hardware.py` states "REPL execution not yet implemented for real hardware."
  - Priority: Low
  - Notes: Requires WebSocket integration which is currently a TODO.

## Hardware Transport Shims

- [x] **HID Transport Shim**: `WebHID` implementation for `pylabrobot.io.hid.HID`.
  - Note: Implemented at `praxis/web-client/src/assets/shims/web_hid_shim.py`.
- [ ] **Socket/TCP Transport Shim**: Browsers don't support raw TCP sockets used by `pylabrobot.io.socket.Socket`.
  - Impact: Blocks PreciseFlex arms and other ethernet-controlled hardware.
  - Priority: High (Blocker for specific hardware)
  - Notes: Requires a WebSocket-to-TCP proxy or intermediate bridge service.
- [ ] **Global Module Shimming for Direct Imports**: Many backends (`BioShake`, etc.) perform `import serial` directly, bypassing the `pylabrobot.io.Serial` abstraction.
  - Impact: These backends crash on import in Pyodide even if `pylabrobot.io.Serial` is patched.
  - Fix: Update `pyodide_io_patch.py` to inject shims into `sys.modules['serial']`, `sys.modules['usb']`, etc.
- [ ] **Missing Pyserial/PyUSB Constants**: Current shims (e.g., `WebSerial`) are missing standard constants like `EIGHTBITS`, `PARITY_NONE` which backends expect.
  - Impact: `AttributeError` when backend try to configure serial parameters.
