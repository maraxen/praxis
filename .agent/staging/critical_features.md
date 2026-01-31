# Critical Features Inventory

> **Created:** 2026-01-31T00:52:00 | **Updated:** 2026-01-31T00:54:00

This document tracks ALL critical features that must work correctly based on source code analysis.

---

## 🧭 Unified Shell Navigation (Main Routes)

| Route | Feature | Test Coverage | Status |
|-------|---------|---------------|--------|
| `/app/run` | Run Protocol wizard | `03-protocol-execution.spec.ts`, `run-protocol-machine-selection.spec.ts` | 🔍 |
| `/app/monitor` | Execution Monitor | `monitor-detail.spec.ts`, `interactions/02-execution-monitoring.spec.ts` | 🔍 |
| `/app/assets` | Asset Management (machines, resources) | `02-asset-management.spec.ts`, `asset-wizard.spec.ts`, `asset-inventory.spec.ts` | 🔍 |
| `/app/protocols` | Protocol Library | `protocol-library.spec.ts` | 🔍 |
| `/app/workcell` | Workcell View | `workcell-dashboard.spec.ts` | 🔍 |
| `/app/data` | Data Visualization | `data-visualization.spec.ts`, `viz-review.spec.ts` | 🔍 |
| `/docs` | Documentation | (none) | 🔍 |
| `/app/playground` | Interactive Playground | `playground-direct-control.spec.ts` | 🔍 |
| `/app/settings` | Settings | `settings-functionality.spec.ts` | 🔍 |

---

## 🏭 Asset Management

| Feature | Test Coverage | Status |
|---------|---------------|--------|
| Machine frontend/backend linkage logic | `machine-frontend-backend.spec.ts` (19KB!) | 🔍 |
| Definition population from seed data | `health-check.spec.ts`, `asset-inventory.spec.ts` | 🔍 |
| Resource FQNs serialize correctly (`pylabrobot.resources.*`) | `asset-wizard.spec.ts` | 🔍 |
| Asset wizard category → type → definition flow | `asset-wizard.spec.ts`, `functional-asset-selection.spec.ts` | 🔍 |
| Machine catalog workflow | `catalog-workflow.spec.ts` | 🔍 |
| Deck setup and view | `deck-setup.spec.ts`, `interactions/02-deck-view.spec.ts` | 🔍 |
| CRUD operations (create, update, delete) | `02-asset-management.spec.ts` | 🔍 |

---

## 📚 Protocol Library

| Feature | Test Coverage | Status |
|---------|---------------|--------|
| Protocol list display | `protocol-library.spec.ts` | 🔍 |
| Protocol detail view | `protocol-library.spec.ts` | 🔍 |
| Protocol upload | `protocol-library.spec.ts` | 🔍 |
| Protocol filtering/search | `protocol-library.spec.ts` | 🔍 |

---

## 🚀 Protocol Execution (Run Protocol)

| Feature | Test Coverage | Status |
|---------|---------------|--------|
| Protocols present correct options for parameters | `03-protocol-execution.spec.ts`, `protocol-execution.spec.ts` | 🔍 |
| Protocols present correct options for machines | `run-protocol-machine-selection.spec.ts` | 🔍 |
| Protocols present correct options for assets | `functional-asset-selection.spec.ts` | 🔍 |
| Parameters serialize into run command correctly | `protocol-execution.spec.ts` | 🔍 |
| PLR asset definitions serialize into command | `protocol-execution.spec.ts` | 🔍 |
| Interactive parameters during execution | `interactive-protocol.spec.ts` | 🔍 |
| Execution controls (start/pause/stop) | `interactions/01-execution-controls.spec.ts` | 🔍 |

---

## 📊 Data Visualization

| Feature | Test Coverage | Status |
|---------|---------------|--------|
| Chart rendering | `data-visualization.spec.ts` | 🔍 |
| Data source integration | `data-visualization.spec.ts` | 🔍 |
| Visualization review | `viz-review.spec.ts` | 🔍 |

---

## 🖥️ Execution Monitor

| Feature | Test Coverage | Status |
|---------|---------------|--------|
| Run list/history | `monitor-detail.spec.ts` | 🔍 |
| Run detail view | `monitor-detail.spec.ts` | 🔍 |
| State transitions | `interactions/02-execution-monitoring.spec.ts` | 🔍 |
| Real-time updates | (needs verification) | 🔍 |

---

## 🐍 Pyodide/JupyterLite

| Feature | Test Coverage | Status |
|---------|---------------|--------|
| JupyterLite bootstrap | `jupyterlite-bootstrap.spec.ts` | 🔍 |
| Cloudpickled protocols instantiate | `jupyterlite-bootstrap.spec.ts` | 🔍 |
| Protocols run to completion | `execution-browser.spec.ts` | 🔍 |
| JupyterLite paths | `jupyterlite-paths.spec.ts` | 🔍 |
| Optimization/performance | `jupyterlite-optimization.spec.ts` | 🔍 |

---

## 💾 Persistence

| Feature | Test Coverage | Status |
|---------|---------------|--------|
| Data survives page reload (OPFS) | `04-browser-persistence.spec.ts` | 🔍 |
| Import/export DB integrity | `browser-export.spec.ts` | 🔍 |
| Database reset with seed data | `health-check.spec.ts` | 🔍 |
| Asset persistence across reloads | `asset-inventory.spec.ts` | 🔍 |

---

## 🌐 Deployment

| Feature | Test Coverage | Status |
|---------|---------------|--------|
| GH Pages paths resolve correctly | `ghpages-deployment.spec.ts` | 🔍 |
| COOP/COEP headers for SharedArrayBuffer | `ghpages-deployment.spec.ts` | 🔍 |
| SPA routing works | `ghpages-deployment.spec.ts` | 🔍 |
| Logo rendering | `verify-logo-fix.spec.ts` | 🔍 |

---

## 🎨 UI/UX Core

| Feature | Test Coverage | Status |
|---------|---------------|--------|
| Command palette | Registered in unified-shell → needs explicit test | ⚠️ |
| Navigation and routing | `01-onboarding.spec.ts`, `smoke.spec.ts` | 🔍 |
| Theme cycling | `smoke.spec.ts` (?) | 🔍 |
| Welcome dialog/onboarding | `01-onboarding.spec.ts` | 🔍 |
| Tutorial flow | `01-onboarding.spec.ts` (?) | 🔍 |
| Error handling | `interactions/04-error-handling.spec.ts` | 🔍 |

---

## 🎭 Playground

| Feature | Test Coverage | Status |
|---------|---------------|--------|
| Direct control of machines | `playground-direct-control.spec.ts` | 🔍 |
| Inventory dialog | `inventory-dialog.spec.ts` | 🔍 |
| Machine selection | (via inventory dialog) | 🔍 |
| Method execution | `playground-direct-control.spec.ts` | 🔍 |

---

## ⚙️ Settings

| Feature | Test Coverage | Status |
|---------|---------------|--------|
| Theme settings | `settings-functionality.spec.ts` | 🔍 |
| Mode settings | `settings-functionality.spec.ts` | 🔍 |
| Export/Import | `browser-export.spec.ts` | 🔍 |

---

## Test Files Summary (44 total: 38 + 6 in interactions/)

| Category | Files | Count |
|----------|-------|-------|
| Core User Journey | `smoke`, `01-onboarding`, `user-journeys` | 3 |
| Asset Management | `02-asset-management`, `asset-*`, `machine-*`, `deck-*`, `catalog-*` | 9 |
| Protocols | `protocol-library`, `protocol-execution`, `03-protocol-execution` | 3 |
| Execution | `run-protocol-*`, `execution-*`, `interactive-*` | 4 |
| Persistence | `04-browser-persistence`, `browser-export`, `health-check` | 3 |
| JupyterLite | `jupyterlite-*` | 3 |
| Data/Viz | `data-visualization`, `viz-review` | 2 |
| Deployment | `ghpages-deployment`, `verify-logo-fix` | 2 |
| Playground | `playground-direct-control`, `inventory-dialog` | 2 |
| Other | `settings-*`, `smoke`, `workcell-*`, `monitor-*`, `capture-*`, `low-*`, `medium-*`, `mock-*`, `screenshot-*` | 7 |
| Interactions | `01-execution-controls`, `02-*`, `03-*`, `04-*` | 6 |

---

## Legend

- 🔍 **Audit** - Needs investigation during test run
- ✅ **PASS** - Feature works, tests pass
- ⚠️ **PARTIAL** - Feature exists but test coverage gap or needs fix
- ❌ **FAIL** - Feature/tests broken
- 🗑️ **DELETE** - Feature removed, delete test
