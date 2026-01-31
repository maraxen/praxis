# Fix Empty State Detection (P1)

> **Stream**: 1 - PageObject Infrastructure  
> **Effort**: S (1-2 hours)  
> **Priority**: P1

---

## Objective

Add explicit content loading waits to PageObjects for pages that show navigation early but render content late, fixing flaky tests in workcell-dashboard and data-visualization specs.

---

## Context Files (Read First)

1. `.agent/staging/e2e_persistent_bugs.md` → Root cause #5
2. `e2e/page-objects/` → Existing PageObjects
3. `e2e/specs/workcell-dashboard.spec.ts` → Affected spec
4. `e2e/specs/data-visualization.spec.ts` → Affected spec

---

## Root Cause Analysis

**Problem**: Page loads (nav visible) but content area empty or slow to render. Tests click on elements that aren't ready.

**Evidence**: Navigation elements are visible but main content area is still loading data.

**Pattern**: Angular lazy loading + async data fetch creates window where nav is ready but content isn't.

---

## Scope

### Change
- Create `e2e/helpers/wait-for-content.ts` with generic content waiting utility
- Update affected PageObjects to use the helper
- Update `workcell-dashboard.spec.ts` and `data-visualization.spec.ts` if needed

### Do NOT Change
- Source application code
- Other unaffected specs
- Core navigation logic

---

## Implementation Steps

1. **Create wait helper**
   ```typescript
   // e2e/helpers/wait-for-content.ts
   export async function waitForContentReady(page: Page, options?: {
     contentSelector?: string;
     timeout?: number;
   }): Promise<void> {
     const selector = options?.contentSelector || '[data-testid="main-content"]';
     const timeout = options?.timeout || 10000;
     
     // Wait for loading indicators to disappear
     await page.locator('.loading-spinner, .skeleton, mat-progress-bar')
       .waitFor({ state: 'hidden', timeout });
     
     // Wait for content to be visible
     await page.locator(selector).waitFor({ state: 'visible', timeout });
   }
   ```

2. **Identify content selectors for affected pages**
   ```bash
   grep -r "data-testid" src/app/features/workcell --include="*.html" | head -10
   grep -r "data-testid" src/app/features/data-visualization --include="*.html" | head -10
   ```

3. **Update PageObjects**
   - Add `waitForContentReady()` call after navigation
   - Use page-specific content selectors

4. **Run affected specs**
   ```bash
   npx playwright test workcell-dashboard.spec.ts data-visualization.spec.ts --reporter=line 2>&1 | tail -15
   ```

---

## Verification

```bash
# Run specs multiple times to check for flakiness
for i in {1..3}; do
  npx playwright test workcell-dashboard.spec.ts --reporter=line 2>&1 | tail -5
done
```

**Expected**: Consistent pass rate across runs

---

## Success Criteria

- [ ] `waitForContentReady()` helper created
- [ ] `workcell-dashboard.spec.ts` passes consistently
- [ ] `data-visualization.spec.ts` passes consistently
- [ ] No increase in test duration >30%
