---
title: 'Jules Integration Plan - 2026-01-21'
---

# Jules Integration Plan - 2026-01-21

## Summary

- **Total Sessions Analyzed**: 32 (with >0 files)
- **Safe to Merge**: 15 sessions
- **Require Manual Merge (Conflicts)**: 4 groups
- **Scaffolds to Extract**: 6 sessions (E2E Tests)

## 1. Clean Applies (Safe to Merge)

_Documentation, Skills, Research Reports, and Isolated Scaffolds. No code conflicts._

| Session ID | Task | Files | Action |
|------------|------|-------|--------|
| `10483287677521851158` | .agent/README.md | 1 | **Apply** |
| `17528057938872959418` | Connection Persistence Tests (Report) | 1 | **Apply** |
| `693011006660131583` | Hardware Testing Guide | 1 | **Apply** |
| `5758405153110470721` | Alembic Migration Guide | 2 | **Apply** |
| `2946937954468200048` | Multi-Stage Workflow Skill | 1 | **Apply** |
| `16249831400007417250` | Maintenance Audit Prompt | 1 | **Apply** |
| `4091292972154822687` | Theme Manifest Format | 1 | **Apply** |
| `18333554910223635761` | Labware Library Schema | 1 | **Apply** |
| `10964805792793165164` | Pyodide Integration Patterns | 1 | **Apply** |
| `15033366457735355048` | Artifact Template | 1 | **Apply** |
| `954639313672326160` | Accessibility Attributes (Wizard) | 1 | **Apply** |
| `7169150082809541249` | Error Boundary Component | 3 | **Apply** |
| `9326114167496894643` | Error Boundary (Python Runtime) | 4 | **Apply** |
| `18100194563593856842` | Typescript Interfaces (Python Bridge) | 1 | **Apply** |
| `8053431069385739941` | State History Storage Opt | 2 | **Apply** |

## 2. Global Refactors (Apply with Caution)

_Wide surface area. Apply these before feature work._

| Session ID | Task | Files | Note |
|------------|------|-------|------|
| `15718507772184055229` | **Docstrings** | **90** | Apply FIRST. Massive change. |
| `7833557422181935314` | Import Ordering | 2 | Apply second. |
| `2675599457561484882` | Ruff Lint Errors | 2 | Conflict with `11789340521090048069` on `machine.py`. |
| `11789340521090048069` | Machine Base Class Type Hints | 1 | Conflict with above. |

## 3. Scaffolds to Extract (E2E Tests)

_These Jills modified project config files (`package.json`, `angular.json`) which causes conflicts. Extract ONLY the `.spec.ts` files._

| Session ID | Task | Target File |
|------------|------|-------------|
| `15023855711672891138` | Data Visualization | `e2e/specs/data-visualization.spec.ts` |
| `9868075249617187364` | Workcell Dashboard | `e2e/specs/workcell-dashboard.spec.ts` |
| `1955602947950537137` | Protocol Library | `e2e/specs/protocol-library.spec.ts` |
| `5772657439955006749` | Deck Setup | `e2e/specs/deck-setup.spec.ts` |
| `11930790793989115694` | Asset Wizard | `e2e/specs/asset-wizard.spec.ts` |

## 4. CRITICAL CONFLICTS - MANUAL MERGE REQUIRED

### 🔴 Case A: Conflicting Migrations

Both sessions attempted to create the **same migration file** (`alembic/versions/3a1fe0851e06...`).

- 12822272099245934316 (Selective Transfer Heuristic)
- 12408408457884280509 (Infinite Consumables)
**Action**: Rename one migration, manually merge changes.

### 🔴 Case B: Protocol Execution Service

Both sessions heavily modified `execution.service.ts` and `live-dashboard.component.ts`.

- 17486039806276221924 (Pause/Resume)
- 7966319430585451351 (Browser Interrupt)
**Action**: Apply "Pause/Resume" first, then manually layer "Browser Interrupt" logic on top.

### 🔴 Case C: PLR Categories vs. Machine Registration

Both touch `praxis/backend/models` and potentially core filters.

- 9570037443858871469 (PLR Category Audit)
- 7588975548984364060 (Backend Machine Registration)
**Action**: Review `pydantic_internals/filters.py` for conflicts.

## Recommended Execution Order

1. Apply **Group 1** (Clean Applies).
2. Apply **Group 2** (Global Refactors) - resolve `machine.py` conflict.
3. Extract **Group 3** (E2E Specs) - discarding config changes.
4. Manually merge **Group 4** (Conflicts).
