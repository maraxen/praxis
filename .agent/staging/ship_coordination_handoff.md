# Praxis Ship Readiness - Coordination Handoff

> Generated: 2026-01-31T09:40

## Purpose
This handoff instructs fresh sessions to coordinate work across logic audits and E2E findings to create a **parallelizable work plan** for achieving ship-ready state.

---

## Input Documents

### Logic Audits (`.agent/staging/logic-audits/`)
| File | Focus |
|------|-------|
| `01-data-models.md` | Data model consistency |
| `02-asset-wizard.md` | Wizard flow logic |
| `03-protocol-execution.md` | Protocol runner |
| `04-constraints.md` | Validation rules |
| `05-github-pages.md` | Deployment config |
| `06-jupyterlite.md` | JupyterLite integration |
| `07-hardware-discovery.md` | Device detection |
| `08-serialization.md` | State persistence |
| `09-recommendations.md` | Priority fixes |
| `10-import-export.md` | DB import/export |
| `11-15-*.md` | Error handling, session recovery, memory, ports, storage |
| `comprehensive_logic_audit.md` | Full audit (34KB) |
| `asset_wizard_filtering_logic_recon.md` | Wizard filtering |

### E2E Findings (`.agent/staging/`)
| File | Content |
|------|---------|
| `e2e_persistent_bugs.md` | Root causes for 31 failing tests |
| `e2e_static_analysis.md` | Redundant/outdated tests |
| `critical_features.md` | Feature priority matrix |
| `playwright-angular-best-practices-2026.md` | Test patterns |

---

## Immediate Actions Completed
- [x] Deleted 6 low-value E2E specs
- [x] Fixed data-visualization route

---

## Next Session Instructions

### Phase 1: Audit & Synthesize
1. **Read all logic-audits/** - understand logic gaps
2. **Read e2e_persistent_bugs.md** - understand test failures
3. **Cross-reference** - map logic issues to test failures

### Phase 2: Generate Work Plan
Create `ship_work_plan.md` with:
- **Parallelizable work streams** (can be done independently)
- **Dependencies** (must be done in order)
- **Effort estimates** (S/M/L)
- **Priority** (P0/P1/P2)

### Phase 3: Create Dispatch Prompts
Create `.agent/staging/ship-prompts/` folder with targeted subagent prompts:

```
ship-prompts/
├── 01-fix-asset-wizard-filtering.md
├── 02-fix-protocol-execution-flow.md
├── 03-fix-createMachine-pageobject.md
├── 04-investigate-jupyterlite-timeout.md
├── 05-fix-data-model-inconsistencies.md
└── ...
```

Each prompt should include:
- **Objective**: Clear deliverable
- **Context files**: What to read first
- **Scope**: What to change (and NOT change)
- **Verification**: How to confirm fix works

---

## Success Criteria
- Work plan with ≤5 parallel streams
- Each stream has clear owner/prompt
- All P0/P1 items have prompts
- Estimated time to ship-ready: X hours

---

## Key Constraints
- JupyterLite specs timeout (180s+) - may need isolation
- createMachine PageObject is shared across 6 specs
- DB seeding missing some categories (PlateReader)
