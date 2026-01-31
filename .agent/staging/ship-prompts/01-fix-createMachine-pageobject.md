# Fix createMachine PageObject Timing (P0)

> **Stream**: 1 - PageObject Infrastructure  
> **Effort**: M (2-3 hours)  
> **Priority**: P0 - Blocks 10+ tests

---

## Objective

Fix the `createMachine` PageObject timing issues that cause category card visibility timeouts, unblocking ~10 tests including user-journeys, 02-asset-management, and machine-frontend-backend specs.

---

## Context Files (Read First)

1. `.agent/staging/e2e_persistent_bugs.md` → Root cause #1
2. `e2e/page-objects/createMachine.ts` → Current implementation
3. `e2e/specs/machine-frontend-backend.spec.ts` → Canonical test (483 lines)
4. `.agent/staging/logic-audits/asset_wizard_filtering_logic_recon.md` → Wizard flow

---

## Root Cause Analysis

**Problem**: `createMachine` PageObject times out on category card visibility in step 1 of the wizard.

**Why**: Dialog animation timing creates race condition between:
- Dialog open animation (Material CDK)
- Category card rendering (async data load)
- Test click action

**Evidence**: Tests pass when run slowly but fail in parallel batches.

---

## Scope

### Change
- `e2e/page-objects/createMachine.ts`
  - Add explicit wait for wizard dialog to be stable
  - Add wait for category cards to be visible *and* clickable
  - Add `waitForDialogAnimation()` helper method

### Do NOT Change
- Wizard component source code (`asset-wizard.ts`)
- Test logic in spec files (only PO internals)
- Other PageObjects unless they share this pattern

---

## Implementation Steps

1. **Audit current implementation**
   ```bash
   cat e2e/page-objects/createMachine.ts
   ```

2. **Add dialog stability wait**
   ```typescript
   async waitForDialogReady(): Promise<void> {
     // Wait for dialog backdrop
     await this.page.locator('.cdk-overlay-backdrop').waitFor({ state: 'visible' });
     // Wait for animation to complete (CDK uses 200ms)
     await this.page.waitForTimeout(250);
     // Wait for wizard content
     await this.page.locator('app-asset-wizard').waitFor({ state: 'visible' });
   }
   ```

3. **Improve category card selector**
   ```typescript
   async selectCategory(category: string): Promise<void> {
     await this.waitForDialogReady();
     const card = this.page.locator(`[data-testid="category-card-${category}"]`);
     await card.waitFor({ state: 'visible', timeout: 10000 });
     await card.click();
   }
   ```

4. **Verify with canonical test**
   ```bash
   npx playwright test machine-frontend-backend.spec.ts --reporter=line 2>&1 | tee /tmp/po-fix.log
   ```

5. **Run dependent specs**
   ```bash
   npx playwright test user-journeys.spec.ts 02-asset-management.spec.ts --reporter=line 2>&1 | tee /tmp/po-related.log
   ```

---

## Verification

### Primary Test
```bash
npx playwright test machine-frontend-backend.spec.ts --reporter=line 2>&1 | tail -10
```
**Expected**: All 10+ tests pass

### Regression Check
```bash
npx playwright test --grep "asset|machine" --reporter=line 2>&1 | tail -10
```
**Expected**: No regressions in related specs

---

## Success Criteria

- [ ] `machine-frontend-backend.spec.ts` passes all tests
- [ ] `user-journeys.spec.ts` CRUD tests pass
- [ ] `02-asset-management.spec.ts` passes
- [ ] No increase in test duration >20%

---

## Rollback

If fix causes regressions:
```bash
git checkout e2e/page-objects/createMachine.ts
```
