# E2E Test Status Report - Praxis

## Summary
- **Date**: 2026-01-28 (Fresh Run)
- **Total Files**: 39
- **Passing**: 26 (66%)
- **Failing**: 13
- **Primary Failure Mode**: Test timeouts (60s exceeded) in application wizards

## Failure Clusters (Fresh Results)

| Cluster | Files | Root Cause | Priority |
|---------|-------|------------|----------|
| **Timeouts** | 10 | Wizard/asset dialogs not rendering | P1 |
| **TypeError** | 1 | MonitorPage constructor | P2 |
| **Visual Regression** | 1 | 13918px diff | P3 |
| **Element Not Found** | 2 | Missing elements | P2 |

### Timeout Failures (10 files) — "The Wizard Cluster"

These tests fail because the application does not render elements fast enough under automation:

| File | Issue |
|------|-------|
| `02-asset-management.spec.ts` | 5 tests - Add Machine/Resource CRUD operations timeout |
| `03-protocol-execution.spec.ts` | Setup wizard steps timeout |
| `04-browser-persistence.spec.ts` | DB Export/Import timeout |
| `asset-wizard.spec.ts` | Machine creation timeout |
| `catalog-workflow.spec.ts` | Catalog tab visibility timeout |
| `deck-setup.spec.ts` | Asset placement timeout |
| `execution-browser.spec.ts` | Execution flow timeout |
| `protocol-execution.spec.ts` | Simulated execution timeout |
| `protocol-library.spec.ts` | Category/Name filtering timeout (2 tests) |

### Other Failures

| File | Type | Error |
|------|------|-------|
| `monitor-detail.spec.ts` | TypeError | `MonitorPage is not a constructor` |
| `asset-wizard-visual.spec.ts` | Visual Regression | 13,918 pixels differ |
| `capture-remaining.spec.ts` | Element Not Found | Missing element |
| `run-protocol-machine-selection.spec.ts` | Element Not Found | Missing element |

---

## Root Cause Analysis (Detailed)

### 1. Asset Management & Persistence
- **Symptoms**: "Add Machine" or "Resource" dialogs fail to complete.
- **Log Evidence**: `createMachine` succeeds, `getMachines` returns correct count.
- **Fault Point**: UI layer sync — `Asset "..." not visible in search results, but may exist`.
- **Specs**: `02-asset-management.spec.ts`, `asset-wizard.spec.ts`

### 2. Database & Export/Import
- **Symptoms**: Export/Import triggers fail; confirmation dialogs don't appear.
- **Spec**: `browser-export.spec.ts`

### 3. Protocol Execution Flow
- **Symptoms**: Setup wizard incomplete; protocol cards missing.
- **Key Error**: `Failed to find protocol cards`
- **Specs**: `03-protocol-execution.spec.ts`, `protocol-library.spec.ts`

### 4. JupyterLite / Python Integration (Critical)
- **Symptoms**: Severe plugin activation failures.
- **Errors**:
  - `Plugin '@jupyterlab/codemirror-extension:commands' failed to activate`
  - `No provider for: @jupyterlab/notebook:INotebookTracker`
  - `SQLITE_ERROR: no such table: function_protocol_definitions`

### 5. Interaction & UX Timeouts
- **Symptoms**: Pause/Abort controls and Deck View interactions timeout.
- **Context**: Often linked to slow JupyterLite initialization.

### 6. Deployment & Routing (GH Pages)
- **Symptoms**: Deep link resolution and home loading failures.
- **Config**: `playwright.ghpages.config.ts`

---

## Remediation Plan

| Dispatch | Target | Scope |
|----------|--------|-------|
| Jules #1 | Timeout Cluster | Investigate wizard performance/rendering |
| Jules #2 | TypeError Fix | Fix `MonitorPage` constructor |
| Jules #3 | Visual Regression | Review asset-wizard visual diff |
| Jules #4 | Element Not Found | Investigate missing elements |

## Technical Details
- **Log File**: `/tmp/playwright_full.log`
- **Runner**: Playwright (Chromium)
- **Environment**: Local Dev Server (Vite/Angular)
