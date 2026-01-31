# Fix Data Visualization Route/Selector Mismatches (P1)

> **Stream**: 2 - Route & Page Fixes  
> **Effort**: S (1-2 hours)  
> **Priority**: P1

---

## Objective

Fix selector and route mismatches in `data-visualization.spec.ts` and `monitor-detail.spec.ts` that cause 0% pass rate in these specs.

---

## Context Files (Read First)

1. `.agent/staging/e2e_persistent_bugs.md` → Root cause #2
2. `e2e/specs/data-visualization.spec.ts` → Failing spec
3. `e2e/specs/monitor-detail.spec.ts` → Failing spec
4. `src/app/app.routes.ts` → Actual route definitions

---

## Root Cause Analysis

**Problem**: Tests navigate to routes that have different structure than expected.

**Evidence**:
- `/run/data-visualization` - page loads but `h1` selector fails
- Tests reference selectors for old UI layout

---

## Scope

### Change
- `e2e/specs/data-visualization.spec.ts`
- `e2e/specs/monitor-detail.spec.ts`
- Associated PageObjects if they exist

### Do NOT Change
- Source component code
- Route definitions
- Other spec files

---

## Implementation Steps

1. **Verify actual routes**
   ```bash
   grep -r "data-visualization\|data\/" src/app/app.routes.ts src/app/**/routes.ts | head -10
   ```

2. **Check actual page content**
   ```bash
   npx playwright test data-visualization.spec.ts --debug
   # Or use browser tool to navigate and inspect
   ```

3. **Identify correct selectors**
   - Check actual `<h1>` text on the page
   - Check actual element IDs/classes
   - Update spec to match reality

4. **Fix selectors in spec**
   ```typescript
   // Before (example)
   await expect(page.locator('h1')).toHaveText('Data Visualization');
   
   // After (verify actual text)
   await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
   ```

5. **Repeat for monitor-detail.spec.ts**

---

## Verification

```bash
npx playwright test data-visualization.spec.ts monitor-detail.spec.ts --reporter=line 2>&1 | tail -10
```

**Expected**: Tests pass or have clear actionable failures

---

## Success Criteria

- [ ] `data-visualization.spec.ts` passes or has <2 failures
- [ ] `monitor-detail.spec.ts` passes or has <2 failures
- [ ] Routes verified against `app.routes.ts`
