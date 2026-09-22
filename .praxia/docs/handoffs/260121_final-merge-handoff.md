---
title: 'FINAL MERGE HANDOFF - v0.1-alpha'
---

# FINAL MERGE HANDOFF - v0.1-alpha

**Date**: 2026-01-21
**Branch**: `angular_refactor` → `main`
**Target Milestone**: v0.1-alpha (PyLabPraxis → Praxis rename)

---

## 🔥 CRITICAL PATH ITEMS

These must be completed before the merge:

### 1. ✅ Jules Integration (COMPLETED)

- **50 overnight sessions** processed
- **9 extraction agents** completed
- **E2E specs created**: data-visualization, workcell-dashboard, protocol-library, deck-setup
- **Extraction reports**: machine_registration, plr_audit, browser_interrupt, geometry_heuristics

### 2. 🚨 PROTOCOL-CRITICAL (End-to-End Execution)

*These are needed for protocols to work with real hardware*

| Session | Task | What It Does | Action |
|---------|------|--------------|--------|
| `12408408457884280509` | **Infinite Consumables** | Allows tip pools to be treated as unlimited | Extract logic, create fresh migration |
| `12822272099245934316` | **Selective Transfer** | `requires_linked_indices` for source/dest pairing | Extract logic, create fresh migration |

**Details**:

- Infinite Consumables adds `infinite_consumables: bool` to `AssetOrm`
- Selective Transfer adds `requires_linked_indices: bool` to `FunctionProtocolDefinitionOrm`  
- Both had migration conflicts - logic must be extracted and applied to fresh baseline

### 3. 🔄 Outstanding Work Needing Dispatch

*Items from Jules sessions that need manual integration or redispatch*

| Session | Task | Status | Action Needed |
|---------|------|--------|---------------|
| `15718507772184055229` | Docstrings (90 files) | Completed | **DISPATCH to antigravity** - too large for --apply |
| `17486039806276221924` | Pause/Resume Protocol | Completed | `jules remote pull --apply` |
| `9570037443858871469` | PLR Category Audit | Completed | `jules remote pull --apply` |
| `7169150082809541249` | Error Boundary | Completed | `jules remote pull --apply` |
| `9326114167496894643` | Error Boundary 2 | Completed | `jules remote pull --apply` |
| `7966319430585451351` | Browser Interrupt | Awaiting | Manual integrate from extraction report |
| `16235462376134233538` | Geometry Heuristics | Paused | Manual integrate from extraction report |
| `7833557422181935314` | Import Ordering | Completed | Or just run `ruff format praxis/backend/models/` |

---

## 📋 MERGE PREP CHECKLIST

*Items to dispatch/coordinate before final merge*

### A. Repo Structure Review
>
> **Goal**: Determine what should be removed/moved before merge

- [ ] Dispatch: Scan for orphan files, dead code, temp artifacts
- [ ] Dispatch: Check for files that should be in `.gitignore`
- [ ] Dispatch: Identify docs that are outdated or duplicated
- [ ] **Manual check**: Review `.agent/backups/` for cleanup

### B. Documentation Audit (Multi-Agent Librarian Review)
>
> **Goal**: Multiple librarians review different doc sets simultaneously

| Doc Set | Scope | Librarian Focus |
|---------|-------|-----------------|
| **Frontend** | `praxis/web-client/src/app/` | Component architecture, services, patterns |
| **Backend** | `praxis/backend/` | API routes, models, services |
| **E2E Tests** | `praxis/web-client/e2e/` | Test coverage, gaps, flaky tests |
| **.agent/** | `.agent/`, `AGENTS.md` | Workflow docs, skills, prompts |
| **Root** | `README.md`, `CONTRIBUTING.md` | User-facing docs |

### C. Unified Panel Component Audit
>
> **Goal**: Full checklist of each panel component's status

- [ ] Dispatch librarians for each panel component:
  - `PlaygroundComponent`
  - `AssetManagementComponent`
  - `RunProtocolComponent`
  - `ProtocolLibraryComponent`
  - `WorkcellDashboardComponent`
  - `VizReviewComponent`
- [ ] Each report notes:
  - `MOCK DATA` or hardcoded values
  - `TODO` comments
  - Missing error handling
  - Incomplete features
  - Things requiring manual verification

### D. GitHub Pages Setup
>
> **Goal**: Deploy static docs/demo to gh-pages

- [ ] Research: Current gh-pages branch status
- [ ] Create: `.github/workflows/deploy-pages.yml`
- [ ] Document: Setup instructions for USER
- [ ] Test: Local build and preview

### E. Branch Cleanup
>
> **Goal**: Merge angular_refactor → main, archive stale branches

- [ ] Merge `angular_refactor` to `main`
- [ ] Archive branches (list identified: 25+ stale remotes)
- [ ] Preserve `gh-pages` branch
- [ ] Delete local-only branches after merge

### F. Repo Rename (pylabpraxis → praxis)
>
> **Goal**: Coordinate rename with GitHub Pages

- [ ] Document: GitHub repo rename steps
- [ ] Find/replace: All occurrences of `pylabpraxis`
- [ ] Update: Import paths, package.json, pyproject.toml
- [ ] Update: GitHub Pages CNAME if applicable
- [ ] Coordinate: Update any external links/references

---

## 🗺️ ROADMAP STRUCTURE

*Further detail to be added - this is the skeleton*

### v0.1-alpha (Current Target)

- Merge angular_refactor
- Repo rename to Praxis
- Basic functionality working
- Browser-native execution stable

### v0.2 (Near-term: Weeks)

- Machine registration complete
- PLR category filtering
- Pause/resume protocol execution
- Hardware validation with Hamilton

### v0.5 (Intermediate: Months)

- Full E2E test coverage
- Plugin/extension system foundation
- Multi-workcell support
- Advanced data visualization

### v1.0 (Long-term: Quarters)

- Production deployment mode
- Full documentation
- Community-ready release
- External hardware vendor support

---

## 📊 CURRENT STATE SUMMARY

### Completed (This Session)

- ✅ All 9 extraction agents finished
- ✅ E2E specs created: 4 files
- ✅ Extraction reports: 4 files
- ✅ Alembic baseline reset
- ✅ Ghost dispatch cleanup

### In MCP Database

- **Tasks**: 17+ items in various states
- **Technical Debt**: 19 items (6 resolved, 13 open)
- **Dispatches**: 2 pending (CLI), several "failed" (cleanup needed)

### Files Created This Session

```
praxis/web-client/e2e/specs/
├── data-visualization.spec.ts
├── workcell-dashboard.spec.ts
├── protocol-library.spec.ts
└── deck-setup.spec.ts

.agent/reports/
├── extracted_machine_registration.md
├── extracted_plr_audit.md
├── extracted_browser_interrupt.md
├── extracted_geometry_heuristics.md
├── jules_integration_plan.md
└── jules_handover_20260121.md
```

---

## 🚀 NEXT ACTIONS (Priority Order)

1. **Apply Global Refactors**
   - Docstrings (90 files) first
   - Import ordering second
   - Resolve machine.py conflicts

2. **Dispatch Documentation Librarians**
   - 5-6 parallel antigravity dispatches
   - Each produces component report

3. **Dispatch Repo Structure Review**
   - 1 deep-researcher session
   - Identify cleanup before merge

4. **Dispatch GitHub Pages Setup**
   - 1 fixer session
   - Create workflow + instructions

5. **Apply Remaining Jules Work**
   - Pause/Resume (session `17486039806276221924`)
   - Browser Interrupt (layer on top)
   - Geometry Heuristics (from extraction report)

6. **Final Integration**
   - Compile all librarian reports → USER checklist
   - Execute merge to main
   - Create release tag v0.1-alpha

---

## ⚠️ KNOWN ISSUES

1. **MCP `execute=true` Bug**: Does not actually spawn CLI processes (TD-19)
2. **Migration Conflicts**: Two sessions created same migration file
3. **Path Discrepancies**: Some diffs reference old paths (see PLR audit)
4. **Deck Setup Spec**: Currently just a placeholder (8 lines)

---

*This document is the coordination artifact for the v0.1-alpha merge. Update as work progresses.*
