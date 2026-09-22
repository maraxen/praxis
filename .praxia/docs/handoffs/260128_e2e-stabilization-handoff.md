---
title: E2E Test Suite Stabilization - Session Handoff
created: 2026-01-27T15:17:00-05:00
priority: high
status: archived
original_status: 'in-progress'
---

# E2E Test Suite Stabilization - Handoff

## Broader Context & Goals

This session is part of the **v0.1-alpha Ship Readiness** initiative. The goal is to ensure 100% pass rate for the **P0 Critical Suite** (Wizard flow, Asset selection, Execution monitoring) to provide baseline confidence for the upcoming release.

## Last Known Test Status

| Spec | Results | Status |
|------|---------|--------|
| `functional-asset-selection.spec.ts` | 5/5 passed | ✅ Clean Pass |
| `03-protocol-execution.spec.ts` | 3/4 passed | ⚠️ Blocked by disk space/refactor |
| `smoke.spec.ts` | 2/4 passed | ⚠️ Blocked by disk space |

## Known Flakiness & Root Causes

- **Monitor Page Object**: Previously failed because it looked for `mat-chip` for status, but `RunDetailComponent` uses a `span` with `.font-semibold`. This has been fixed with `data-testid="run-status"`.
- **Smoke Test Timing**: The dashboard and asset list often time out during initial load. Timeouts have been increased, but it remains sensitive to local environment performance.
- **Execution Log Waits**: Simulation mode can be faster than Playwright's polling. Hardened monitor logic to handle RUNNING -> COMPLETED rapid transitions.

## Immediate Next Steps

1. **Run P0 Suite** (disk space resolved):

   ```bash
   cd /Users/mar/Projects/praxis/praxis/web-client
   npx playwright test e2e/specs/03-protocol-execution.spec.ts --project=chromium
   npx playwright test e2e/specs/functional-asset-selection.spec.ts --project=chromium
   npx playwright test e2e/specs/smoke.spec.ts --project=chromium
   ```

2. **Verify `03-spec` atomic flow** - Tests were refactored into a single "lifecycle" test to avoid serial state pollution.

3. **Complete Phase 4** - Document results and create ship readiness checklist.

---

## Session Summary

- **`clearProtocol()` guard fix**: Strengthened guard in `run-protocol.component.ts` to prevent clearing during initialization races.
- **Unit test fix**: Updated stale test at `run-protocol.component.spec.ts:171`.
- **Monitor POM hardening**: Updated `monitor.page.ts` with `data-testid` selectors and flexible heading waits.
- **03-spec refactor**: Combined 3 fragmented execution tests into single atomic "lifecycle" test.
- **`data-testid` additions**: Added `run-status` and `execution-logs` to `run-detail.component.ts`.
- **Test prioritization**: Categorized 35 specs into P0/P1/P2 tiers.

### Blockers Resolved

- **EPERM**: User removed manually.
- **ENOSPC**: Disk full (cleaned `test-results/` and `/tmp/e2e-*`).

---

## Key Files Modified

| File | Change |
|------|--------|
| `run-protocol.component.ts` | `clearProtocol()` guard strengthened |
| `run-protocol.component.spec.ts` | Unit test updated for new guard |
| `monitor.page.ts` | Selectors updated, `waitForLiveDashboard` improved |
| `run-detail.component.ts` | Added `data-testid` for status/logs |
| `03-protocol-execution.spec.ts` | Refactored to atomic lifecycle test |

---

## Artifacts

- [task.md](file:///Users/mar/.gemini/antigravity/brain/0f5c40bf-64b0-473d-98db-d0216296fcde/task.md)
- [implementation_plan.md](file:///Users/mar/.gemini/antigravity/brain/0f5c40bf-64b0-473d-98db-d0216296fcde/implementation_plan.md)
- [test_prioritization.md](file:///Users/mar/.gemini/antigravity/brain/0f5c40bf-64b0-473d-98db-d0216296fcde/test_prioritization.md)
