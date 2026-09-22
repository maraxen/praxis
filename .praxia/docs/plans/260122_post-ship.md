# Post-Ship Roadmap (v0.1-Alpha+)

This document outlines the priority tasks and architectural improvements planned for after the initial v0.1-Alpha release.

## Database & Schema Infrastructure

### 1. Robust Generation Pipeline

- **Audit Generation Logic**: Perform a deep audit of `generate_browser_db`, `generate_browser_schema`, and `generate_openapi`.
- **Modularization**: Refactor the monolithic script logic into a structured `praxis.gen` package.
- **Robustness**: Replace ad-hoc string manipulations and "patchy" fixes with a robust, AST-aware or template-based generation system.
- **Validation**: Integrate automated validation steps to ensure generated schemas and databases are internally consistent and match the source truth.

## Agentic Capabilities

- [ ] (Reserved for upcoming agent infrastructure improvements)

## UI/UX Polish

- [ ] (Reserved for visual refinements and post-launch feedback)
