# E2E Persistent Bugs - Full Audit

> Generated: 2026-01-31T08:55

## Audit Summary

| Batch | Passed | Failed | Pass% |
|-------|--------|--------|-------|
| machine-frontend-backend | 10 | 4 | 71% |
| 02-asset-management | 5 | 5 | 50% |
| smoke+settings+health | 12 | 1 | **92%** ✅ |
| workcell+protocol+deck | 12 | 4 | 75% |
| 01+03+04 core | 1 | 2 | 33% |
| data-viz+user-journeys+monitor | 0 | 9 | **0%** ⚠️ |
| jupyterlite/playground | timeout | - | N/A |
| asset-wizard | 0 | 4 | 0% |
| inventory-dialog | 0 | 2 | 0% |

**Total estimated: ~40 passed, ~31 failed (~56% pass rate)**

---

## Fixed in This Session (+10)
- machine-frontend-backend: Cancel→Escape, category-card, getByRole
- 02-asset-management: Cancel→Escape, category-card, element visibility

---

## Root Cause Categories

### 1. PageObject Timing Issues
**Affected**: user-journeys, 02-asset-management (CRUD), machine-frontend-backend (Full Workflow)  
**Root cause**: `createMachine` PageObject times out on category card visibility  
**Tried**: Explicit waits, getByRole for buttons  
**Status**: Needs deeper investigation of dialog animation timing

### 2. Route/Page Mismatches
**Affected**: data-visualization, monitor-detail  
**Root cause**: Tests navigate to routes that have different structure than expected  
**Example**: `/run/data-visualization` - page loads but h1 selector fails  
**Status**: Need to verify actual page routes and update selectors

### 3. Fixture/Context Issues
**Affected**: asset-wizard, inventory-dialog, workcell-dashboard  
**Root cause**: `gotoWithWorkerDb` and custom fixtures create different page states  
**Example**: asset-wizard shows "Add Asset" instead of "Add Machine"  
**Tried**: Flexible locator (.or()) - **caused regression**  
**Status**: Needs fixture investigation

### 4. JupyterLite Initialization
**Affected**: jupyterlite-*, playground-*, inventory-dialog  
**Root cause**: JupyterLite/Pyodide doesn't bootstrap in test context (>180s timeout)  
**Status**: Needs separate investigation of WASM loading

### 5. Empty State Detection  
**Affected**: workcell-dashboard, data-visualization  
**Root cause**: Page loads (nav visible) but content area empty or slow to render  
**Status**: May need explicit waits for content loading

---

## Recommended Next Steps

### Immediate
1. **Verify routes**: Check if `/run/data-visualization` exists and what the actual h1 text is
2. **Add debug logging**: Add console.log to PageObject methods to trace where timing fails

### Short-term
3. **Fix createMachine**: Add explicit wait for wizard content before clicking cards
4. **Standardize fixtures**: Ensure gotoWithWorkerDb produces same button text as standard goto

### Longer-term
5. **JupyterLite isolation**: Skip JupyterLite specs in CI, run separately
6. **Page load waits**: Add generic "wait for content" helper to all page objects

---

## Quick Wins Already Applied

| Pattern | Fix | Impact |
|---------|-----|--------|
| Cancel button | `keyboard.press('Escape')` | +5 tests |
| Step 1 is Category | `category-card-*` | +3 tests |
| Next/Back buttons | `getByRole('button', {...})` | +2 tests |
