# Technical Debt / Missing Features

## Testing

- **Database Export/Import**: `tests/backend/api/test_database_export.py` contains stub tests marked `xfail`.
  - [ ] Implement Admin API for export/import

  - [x] Browser mode export button implementation (tested in `tests/integration/test_browser_export.py`)

## Playground

- **Programmatic Well Selection**: Support generic programmatic selection of wells (e.g., via API or Python context) instead of just UI interaction.
  - [ ] Define API for programmatic selection
  - [ ] Implement selection state synchronization

## Simulation & Workcell Visualization

- **Deck Configuration Visualizer**: Improve the UX and robustness of the workcell deck configuration view.
  - [ ] Add validation to deck states to prevent invalid configurations.
  - [ ] Improve overall UX of the visualizer (interactions, layout, feedback).
  - [ ] Add missing deck definitions to simulation options (e.g., Vantage deck and others).

## Documentation & UX Stability

- **Missing Production Docs**: Many `*-production.md` files are missing from `docs/`, causing snackbar errors when navigated to.
  - [ ] Create missing `*-production.md` documentation files.
  - [ ] Silence 404 snackbar errors for missing doc files specifically in **browser mode**.

- **Unified Documentation View**: Currently using Sphinx for docs/API and Material for MkDocs for potential blog/guides.
  - [ ] Consolidate all documentation generation to a single tool (likely MkDocs) for consistent theming and easier maintenance.
  - [ ] Ensure the "Blog" section is integrated into the main documentation site.

## Agent / Task Infrastructure

- **Progressive Disclosure for Tasks**: Implement a progressive disclosure mechanism for task creation/management to allow for more in-depth notes without cluttering the primary view.
  - [ ] Design UX for progressive disclosure (e.g., expandable sections, modals, or drill-down).
  - [ ] Implement support for deep metadata/notes in `.agent/tasks`.

- **Standardized Agent Workflows**: Create and document standardized workflows (via `.agent/workflows/`) for core agent activities.
  - [ ] Inspection Workflow (e.g., `/inspect`)
  - [ ] Planning Workflow (e.g., `/plan`)
  - [ ] Execution Workflow (e.g., `/execute`)
  - [ ] Testing & Verification Workflow (e.g., `/verify`)

## Asset Selection UI

- **Expand Asset Selection**: Add a button next to the current selection dropdown that triggers a full Dialog Series (similar to Inventory Dialog) to handle complex asset filtering and simulation configuration more gracefully. This should complement, not replace, the existing quick-select functionality.

## Protocol Logic & Indices

- **Complex Index Mapping (1:1)**: Currently, the Well Selector logic for selective transfers attempts 1:1 mapping between source and destination indices, which is brittle and complex to maintain.
  - [ ] Refactor protocols to use a single index argument where possible.
  - [ ] Revisit 1:1 mapping logic when the simulation engine can robustly infer indices from the tracers.
  - [ ] Indices inference from simulation mode inspection and tracers should be formalized.

## Tooling & Build Scripts

- **Refactor Generation Logic**: The scripts for generating browser databases, schemas, and OpenAPI definitions are currently monolithic and contain ad-hoc patches.
  - [ ] Audit `scripts/generate_browser_db.py`, `scripts/generate_browser_schema.py`, and `scripts/generate_openapi.py`.
  - [ ] Identify ways to make the generation logic more robust and less patchy.
  - [ ] Split monolithic scripts into reusable submodules (e.g., in a `praxis.gen` or equivalent package).
  - [ ] Implement validation for generated artifacts.
