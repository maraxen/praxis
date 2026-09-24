---
title: 'E2E Test Failure Audit Report (260129)'
---

# E2E Test Failure Audit Report (260129)

## Summary

Full E2E suite executed after OPFS optimizations. Initial setup passed but significant failures observed, culminating in test runner timeout.

## Failure Summary Table

| Spec File | Test Name | Status | Duration | Cause |
|-----------|-----------|--------|----------|-------|
| `02-asset-management.spec.ts` | should open Add Machine dialog | ❌ | 27.3s | Timeout |
| `02-asset-management.spec.ts` | should open Add Resource dialog | ❌ | 27.0s | Timeout |
| `02-asset-management.spec.ts` | CRUD: should add a new machine | ❌ | 29.5s | Timeout |
| `02-asset-management.spec.ts` | CRUD: should add a new resource | ❌ | 30.8s | Timeout |
| `02-asset-management.spec.ts` | CRUD: should delete a machine | ❌ | 28.5s | Timeout |
| `02-asset-management.spec.ts` | CRUD: should persist machine after page reload | ❌ | 29.2s | Timeout |
| `03-protocol-execution.spec.ts` | execute protocol and monitor lifecycle | ❌ | 2.1m | Timeout |
| `04-browser-persistence.spec.ts` | should export and import database | ❌ | 29.0s | Timeout |
| `asset-inventory.spec.ts` | should persist created machine | ❌ | 20.2s | Timeout |
| `asset-inventory.spec.ts` | should persist created resource | ❌ | 16.9s | Timeout |
| `asset-wizard.spec.ts` | Hamilton STAR wizard | ❌ | 2.0m | Timeout |
| `capture-remaining.spec.ts` | 13. protocol-upload-dialog.png | ❌ | 31.3s | Timeout |
| `capture-remaining.spec.ts` | 15. hardware-discovery-dialog.png | ❌ | 409ms | Element not found |
| `capture-remaining.spec.ts` | 17. welcome-dialog.png | ❌ | 467ms | Element not found |
| `catalog-workflow.spec.ts` | show catalog tab | ❌ | 428ms | Element not found |
| `data-visualization.spec.ts` | (6 tests) | ❌ | <500ms | Element not found |
| `deck-setup.spec.ts` | navigate to deck setup | ❌ | 418ms | Element not found |
| `execution-browser.spec.ts` | (2 tests) | ❌ | <500ms | Element not found |
| `functional-asset-selection.spec.ts` | identify assets | ❌ | 453ms | Element not found |

## Root Cause Clusters

### 1. Asset Management Timeouts (HIGH)
- Tests hitting ~30s timeout waiting for UI updates after DB operations
- OPFS logs confirm DB interaction, but UI not receiving/reacting to data
- **Hypothesis:** Race condition between fast OPFS writes and Angular change detection

### 2. Rapid Failures / Cascading Effect (HIGH)
- Large group failing <500ms with "element not found"
- Suggests app in broken state after earlier failure
- **Hypothesis:** Previous test failure leaves app in unrecoverable state

### 3. Complex Workflow Timeouts (LOW)
- Protocol execution (2.1m) and asset wizard (2.0m)
- Deep-seated bugs in multi-step journeys
- **Defer** until foundational issues fixed

### 4. Browser Persistence (MEDIUM)
- Export/import database failing
- May be affected by OPFS changes

## Recommended Fix Priority

1. **Isolate rapid failures** - Run `data-visualization.spec.ts` solo to determine if cascading
2. **Stabilize asset management** - Add detailed logging to trace DB→UI data flow
3. **Defer complex workflows** - Fix foundational issues first
