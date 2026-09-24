---
title: 'E2E Test Suite Debug & Realistic User Interaction Plan'
---

# E2E Test Suite Debug & Realistic User Interaction Plan

> **Session Recovery**: If interrupted, resume by reading this file and continuing from the Progress Tracker below.

## Progress Tracker

- [x] **Phase 1**: Fix selectWizardCard() in assets.page.ts
- [x] **Phase 1**: Remove Angular Tier 3 fallbacks from assets.page.ts
- [x] **Phase 2**: Replace hardcoded waits in assets.page.ts (ALL removed)
- [x] **Phase 2**: Fix functional-asset-selection.spec.ts
- [x] **Phase 2**: Refactor wizard.page.ts and base.page.ts
- [x] **Final**: Run E2E tests to verify - `functional-asset-selection.spec.ts` PASSES
- [ ] **Phase 3**: Add data-testid to asset-wizard component
- [ ] **Phase 3**: Add data-testid to run-protocol components
- [ ] **Phase 3**: Update page objects to use getByTestId()
- [ ] **Phase 4**: Add afterEach cleanup hooks to all specs

---

## Problem Summary

The E2E test suite has **critical reliability issues** and **unrealistic interaction patterns** that undermine its value:

1. **1 actively failing test** (`functional-asset-selection.spec.ts`) blocking the suite
2. **50+ hardcoded waits** causing flakiness and slow execution
3. **Angular form manipulation fallbacks** bypassing actual UI interactions
4. **No cleanup hooks** causing state pollution between tests
5. **Inconsistent locator strategies** with fragile CSS selectors

---

## Phase 1: Fix Blocking Failure (P1)

### Target: `functional-asset-selection.spec.ts`

**Root Cause**: Element visibility race condition in wizard card selection - the `selectWizardCard()` method in `assets.page.ts` uses a complex retry loop with `evaluate()` and `force: true` clicks that mask timing issues.

**Files to modify**:
- `praxis/web-client/e2e/page-objects/assets.page.ts:34-95` - Refactor `selectWizardCard()` method
- `praxis/web-client/e2e/specs/functional-asset-selection.spec.ts:46` - Replace `waitForTimeout(2000)` with proper assertion

**Specific Changes**:
1. **selectWizardCard()** (lines 34-95): Replace manual retry loop with:
   ```typescript
   await cards.first().waitFor({ state: 'visible' });
   await cards.first().click();
   await expect(nextButton).toBeEnabled();
   ```
2. Remove dual-click pattern (native + dispatchEvent) at lines 62-73
3. Remove `waitForTimeout(600)` at line 75 - use `toBeEnabled()` assertion
4. Remove `waitForTimeout(500)` at lines 90, 117 - use proper state checks

---

## Phase 2: Remove Anti-Patterns from Page Objects (P1)

### 2.1 Eliminate Hardcoded Waits in `assets.page.ts`

**Target**: 20+ occurrences across the file

| Line | Current | Replace With |
|------|---------|--------------|
| 75 | `waitForTimeout(600)` | `await expect(nextButton).toBeEnabled()` |
| 90 | `waitForTimeout(500)` | Remove (in retry loop) |
| 117 | `waitForTimeout(500)` | `await expect(step).toBeVisible()` |
| 146, 151, 156, 161, 166 | `waitForTimeout(300)` | `await expect(tab).toHaveAttribute('aria-selected', 'true')` |
| 181, 219 | `waitForTimeout(1000)` | `await expect(wizard).toBeVisible()` |
| 239 | `waitForTimeout(1000)` | `await expect(cards.first()).toBeVisible()` |
| 292, 299, 363 | `waitForTimeout(500)` | `await expect(card).toHaveClass(/selected/)` |
| 324, 404 | `waitForTimeout(300)` | Remove (after Angular fallback) |
| 452, 481 | `waitForTimeout(500)` | `await expect(row).not.toBeVisible()` |
| 499, 511, 521 | `waitForTimeout(300)` | Proper filter/search assertions |

### 2.2 Remove Angular Form Manipulation (Tier 3 Fallbacks)

**Files**:
- `assets.page.ts:310-329` - `wizardSelectType()` Tier 3 fallback
- `assets.page.ts:383-405` - `wizardSelectCategory()` Tier 3 fallback

**Action**: DELETE the Angular `ng.getComponent()` manipulation entirely. If UI clicks don't work, the test should fail - that indicates a real bug. Add `data-testid` to frontend instead.

### 2.3 Simplify selectWizardCard() Method

**Current** (lines 34-95): 60-line method with 3 retry tiers, evaluate(), dual-click pattern
**Target**: 10-15 lines using proper Playwright locators

```typescript
private async selectWizardCard(selector = '.results-grid .praxis-card.result-card'): Promise<void> {
  const wizard = this.page.locator('app-asset-wizard');
  const card = wizard.locator(selector).first();

  await card.waitFor({ state: 'visible', timeout: 15000 });
  await card.scrollIntoViewIfNeeded();
  await card.click();

  const nextButton = wizard.getByRole('button', { name: /Next/i });
  await expect(nextButton).toBeEnabled({ timeout: 5000 });
}
```

---

## Phase 3: Add `data-testid` Attributes to Frontend (P2)

### 3.1 Asset Wizard Component

**File**: `src/app/shared/components/asset-wizard/asset-wizard.ts`

Add `data-testid` to:
- Type selection cards: `data-testid="wizard-type-card-machine"`, `data-testid="wizard-type-card-resource"`
- Category cards: `data-testid="wizard-category-card-{category}"`
- Result cards: `data-testid="wizard-result-card"`
- Next/Back buttons: `data-testid="wizard-next-btn"`, `data-testid="wizard-back-btn"`
- Create button: `data-testid="wizard-create-btn"`

### 3.2 Protocol Run Wizard Components

**Files**:
- `src/app/features/run-protocol/run-protocol.component.ts`
- `src/app/features/run-protocol/components/machine-selection/machine-selection.component.ts`
- `src/app/features/run-protocol/components/parameter-config/parameter-config.component.ts`
- `src/app/features/run-protocol/components/guided-setup/guided-setup.component.ts`
- `src/app/features/run-protocol/components/protocol-summary/protocol-summary.component.ts`

Add `data-testid` to:
- Protocol cards: `data-testid="protocol-card-{name}"`
- Machine option cards: `data-testid="machine-option-card"`
- Parameter inputs: `data-testid="param-input-{name}"`
- Step containers: `data-testid="wizard-step-{name}"`
- Continue buttons: `data-testid="step-continue-btn"`

### 3.3 Update Page Objects to Use `getByTestId()`

After adding `data-testid` attributes, update page objects:
```typescript
// Before (fragile)
const card = wizard.locator('.type-card').filter({ hasText: /Machine/i });

// After (reliable)
const card = wizard.getByTestId('wizard-type-card-machine');
```

---

## Phase 4: Add Test Isolation (P2)

### 4.1 Add Cleanup Hooks to All Specs

**Specs needing `afterEach` cleanup** (create data without cleanup):
- `functional-asset-selection.spec.ts` - Creates 4 assets
- `02-asset-management.spec.ts` - Creates machines/resources
- `03-protocol-execution.spec.ts` - May create executions
- `asset-wizard.spec.ts` - Creates test assets
- `playground-direct-control.spec.ts` - Creates machines

**Standard cleanup pattern**:
```typescript
test.afterEach(async ({ page }) => {
  // Dismiss any open dialogs/overlays
  await page.keyboard.press('Escape').catch(() => {});
  // If specific cleanup needed, call page object methods
});
```

### 4.2 Add `resetdb=1` Query Param

**Files missing reset behavior**:
- Check all specs in `e2e/specs/` that don't use `BasePage.goto()` with reset param
- Ensure `BasePage.goto()` includes `resetdb=1` by default for browser mode

### 4.3 Ensure Test Independence

Each test should:
1. Start with known database state (via `resetdb=1`)
2. Clean up any dialogs/overlays in `afterEach`
3. Not rely on state from previous tests (no `.serial()` dependencies unless necessary)

---

## Phase 5: Realistic User Interaction Patterns (P2)

### 5.1 Replace Force Clicks with Proper Waits

```typescript
// BAD - masks real issues
await element.click({ force: true });

// GOOD - waits for element to be interactable
await element.waitFor({ state: 'visible' });
await expect(element).toBeEnabled();
await element.click();
```

### 5.2 Simulate Realistic User Timing

```typescript
// Add human-like interaction gaps where appropriate
await page.getByRole('textbox').fill(value);
await page.getByRole('textbox').blur(); // User moves to next field
```

### 5.3 Test Error Recovery Paths

Add tests for:
- Form validation errors
- Network failures (mock)
- Timeout handling
- User cancellation flows

---

## Critical Files (Execution Order)

### Priority 1: Fix Blocking Test
| File | Changes |
|------|---------|
| `e2e/page-objects/assets.page.ts` | Simplify `selectWizardCard()`, remove Angular fallbacks, replace hardcoded waits |
| `e2e/specs/functional-asset-selection.spec.ts` | Replace `waitForTimeout(2000)`, add afterEach cleanup |

### Priority 2: Page Object Refactoring
| File | Changes |
|------|---------|
| `e2e/page-objects/wizard.page.ts` | Remove circular dep, extend BasePage, fix waits |
| `e2e/page-objects/monitor.page.ts` | Replace any hardcoded waits |
| `e2e/page-objects/protocol.page.ts` | Replace any hardcoded waits |
| `e2e/page-objects/base.page.ts` | Improve `waitForOverlay()` to use native Playwright waits |

### Priority 3: Frontend data-testid
| File | Changes |
|------|---------|
| `src/app/shared/components/asset-wizard/asset-wizard.ts` | Add data-testid to cards/buttons |
| `src/app/features/run-protocol/run-protocol.component.ts` | Add data-testid to wizard steps |
| `src/app/features/run-protocol/components/machine-selection/machine-selection.component.ts` | Add data-testid |
| `src/app/features/run-protocol/components/parameter-config/parameter-config.component.ts` | Add data-testid |

### Priority 4: Test Isolation
| File | Changes |
|------|---------|
| All specs in `e2e/specs/` | Add afterEach cleanup hooks |

---

## Success Criteria

1. `functional-asset-selection.spec.ts` passes consistently
2. All 39 spec files pass without flaky failures
3. Zero `waitForTimeout()` calls with arbitrary delays (>300ms)
4. Zero Angular form manipulation fallbacks (Tier 3 code removed)
5. All data-interactive elements have `data-testid` attributes
6. All specs have `afterEach` cleanup hooks
7. Test execution time reduced by ~30% (removing unnecessary waits)

---

## Execution Order

1. **Immediate**: Fix `assets.page.ts` selectWizardCard() - unblocks the failing test
2. **Then**: Remove all Angular fallbacks in `assets.page.ts`
3. **Then**: Replace hardcoded waits across page objects
4. **Then**: Add `data-testid` to frontend components
5. **Then**: Update page objects to use `getByTestId()`
6. **Finally**: Add cleanup hooks to all specs

Run tests after each phase to verify no regressions.

---

## Quick Resume Commands

```bash
# Run the failing test to check progress
cd praxis/web-client && npx playwright test functional-asset-selection --headed

# Run all E2E tests
cd praxis/web-client && npx playwright test

# Run with debug mode
cd praxis/web-client && npx playwright test --debug
```
