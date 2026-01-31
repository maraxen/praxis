# Cleanup Redundant Specs (P0)

> **Stream**: 4 - Test Cleanup & Isolation  
> **Effort**: S (30 min)  
> **Priority**: P0 (quick win)

---

## Objective

Delete 6 low-value E2E specs that are either one-off verifications, screenshot capture tools, or duplicates of other coverage.

---

## Context Files (Read First)

1. `.agent/staging/e2e_static_analysis.md` → Removal candidates
2. `e2e/specs/` directory listing

---

## Specs to Delete

| File | Reason |
|------|--------|
| `verify-logo-fix.spec.ts` | One-off fix verification, smoke covers this |
| `screenshot_recon.spec.ts` | Recon tool, not a test |
| `low-priority-capture.spec.ts` | Screenshot capture only |
| `medium-priority-capture.spec.ts` | Screenshot capture only |
| `capture-remaining.spec.ts` | Screenshot capture only |
| `mock-removal-verification.spec.ts` | One-time verification |

---

## Scope

### Change
- DELETE the 6 files listed above

### Do NOT Change
- Any other spec files
- Page objects
- Fixtures

---

## Implementation Steps

1. **Verify files exist**
   ```bash
   ls -la e2e/specs/ | grep -E "verify-logo|screenshot_recon|capture|mock-removal"
   ```

2. **Delete files**
   ```bash
   cd /Users/mar/Projects/praxis/praxis/web-client
   rm e2e/specs/verify-logo-fix.spec.ts
   rm e2e/specs/screenshot_recon.spec.ts
   rm e2e/specs/low-priority-capture.spec.ts
   rm e2e/specs/medium-priority-capture.spec.ts
   rm e2e/specs/capture-remaining.spec.ts
   rm e2e/specs/mock-removal-verification.spec.ts
   ```

3. **Verify deletions**
   ```bash
   ls e2e/specs/ | grep -E "capture|verify-logo|mock-removal"
   # Should be empty
   ```

4. **Update test count**
   ```bash
   ls e2e/specs/*.spec.ts | wc -l
   ```

---

## Verification

```bash
# Should list fewer specs now
npx playwright test --list 2>&1 | tail -10

# Full suite should still work
npx playwright test smoke.spec.ts --reporter=line 2>&1 | tail -5
```

---

## Success Criteria

- [ ] All 6 files deleted
- [ ] No references to deleted files in config
- [ ] Smoke test still passes
- [ ] `npx playwright test --list` runs without errors

---

## Git Commit

```bash
git add -A
git commit -m "chore(e2e): remove 6 low-value specs per static analysis"
```
