# Standardize E2E Fixtures (P1)

> **Stream**: 3 - Fixture & Context Standardization  
> **Effort**: M (2-3 hours)  
> **Priority**: P1

---

## Objective

Ensure `gotoWithWorkerDb` fixture produces the same UI state as standard navigation, fixing ~8 tests in asset-wizard, inventory-dialog, and workcell-dashboard specs.

---

## Context Files (Read First)

1. `.agent/staging/e2e_persistent_bugs.md` → Root cause #3
2. `e2e/fixtures/worker-db.fixture.ts` → DB isolation fixture
3. `e2e/specs/asset-wizard.spec.ts` → Affected spec
4. `e2e/specs/inventory-dialog.spec.ts` → Affected spec
5. `e2e/specs/workcell-dashboard.spec.ts` → Affected spec

---

## Root Cause Analysis

**Problem**: `gotoWithWorkerDb` and custom fixtures create different page states than standard `goto`.

**Evidence**:
- `asset-wizard.spec.ts` shows "Add Asset" instead of "Add Machine"
- Flexible locator (`.or()`) was tried but caused regressions

**Hypothesis**: Fixture initialization sequence differs from production flow.

---

## Scope

### Change
- `e2e/fixtures/worker-db.fixture.ts`
- Test specs that use the fixture (update locators if needed post-fix)

### Do NOT Change
- Source application code
- Database seeding logic (unless clearly broken)
- Other fixtures

---

## Implementation Steps

1. **Audit fixture implementation**
   ```bash
   cat e2e/fixtures/worker-db.fixture.ts
   ```

2. **Compare navigation sequences**
   - Standard: `page.goto('/app/assets')` → waits for hydration
   - Fixture: May apply DB before navigation?

3. **Identify UI state difference**
   - Run with debug mode:
     ```bash
     npx playwright test asset-wizard.spec.ts --debug
     ```
   - Check what text is rendered on buttons

4. **Fix fixture to match production flow**
   - Ensure DB is ready before navigation completes
   - Use `waitForURL` or `waitForLoadState('networkidle')`

5. **Update specs if button text legitimately differs by context**
   - Use semantic locators: `getByRole('button', { name: /add/i })`

---

## Verification

```bash
npx playwright test asset-wizard.spec.ts inventory-dialog.spec.ts workcell-dashboard.spec.ts --reporter=line 2>&1 | tail -10
```

**Expected**: All 3 specs pass

---

## Success Criteria

- [ ] `asset-wizard.spec.ts` passes (0 failures)
- [ ] `inventory-dialog.spec.ts` passes (0 failures)
- [ ] `workcell-dashboard.spec.ts` passes (0 failures)
- [ ] Fixture produces consistent UI state
