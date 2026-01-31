# Protocol Simulation Completion Tests (P1)

> **Stream**: 7 - Test Coverage  
> **Effort**: M (3-4 hours)  
> **Priority**: P1

---

## Objective

Create E2E tests that run ALL seeded protocols in browser simulation mode and verify they complete successfully. This validates the full execution path without requiring hardware.

---

## Context Files (Read First)

1. `e2e/specs/execution-browser.spec.ts` → Existing browser execution tests
2. `e2e/specs/protocol-execution.spec.ts` → Protocol execution tests
3. `src/app/core/db/seed-data/` → Seeded protocol definitions
4. `src/assets/protocols/` → Protocol files

---

## Root Cause Analysis

**Gap**: Current tests may cover specific protocols but don't systematically validate ALL protocols complete in simulation mode.

**Risk**: A protocol that works in dev may fail in simulation due to missing shims, incorrect resource instantiation, or Python errors.

---

## Scope

### Change
- Create `e2e/specs/protocol-simulation-matrix.spec.ts`
- Test each seeded protocol through full simulation run

### Do NOT Change
- Protocol files
- Execution service logic
- Seed data

---

## Implementation Steps

1. **Identify all seeded protocols**
   ```bash
   find src/assets/protocols -name "*.pickle" -o -name "*.py" | head -20
   # OR query seed data
   grep -r "protocol" src/app/core/db/seed-data/ --include="*.ts" | head -10
   ```

2. **Create matrix test**
   ```typescript
   // e2e/specs/protocol-simulation-matrix.spec.ts
   import { test, expect } from '@playwright/test';
   
   const PROTOCOLS_TO_TEST = [
     { name: 'Simple Transfer', id: 'simple-transfer-uuid' },
     { name: 'Serial Dilution', id: 'serial-dilution-uuid' },
     // ... add all protocols
   ];
   
   test.describe('@slow Protocol Simulation Matrix', () => {
     for (const protocol of PROTOCOLS_TO_TEST) {
       test(`runs ${protocol.name} to completion`, async ({ page }) => {
         // Navigate to run wizard
         await page.goto('/app/run');
         
         // Select protocol
         await page.locator(`[data-testid="protocol-${protocol.id}"]`).click();
         
         // Select simulated machine
         await page.locator('[data-testid="machine-simulated"]').click();
         
         // Configure any required parameters (may need per-protocol config)
         
         // Start execution
         await page.locator('[data-testid="start-run"]').click();
         
         // Wait for completion (with generous timeout)
         await expect(page.locator('[data-testid="run-status"]'))
           .toContainText('Completed', { timeout: 120000 });
       });
     }
   });
   ```

3. **Handle protocol-specific parameters**
   - Create fixture data for each protocol's required inputs
   - Skip protocols that require real hardware parameters

4. **Tag as @slow**
   - These tests will be slow (2+ minutes each)
   - Skip in CI, run nightly or pre-release

---

## Verification

```bash
# Run matrix tests (locally, slow)
npx playwright test protocol-simulation-matrix.spec.ts --reporter=line --timeout=180000 2>&1 | tee /tmp/protocol-matrix.log
```

---

## Success Criteria

- [ ] All seeded protocols identified and listed
- [ ] Each protocol has a test case
- [ ] Tests pass with simulated backend
- [ ] Failures indicate specific protocol + error

---

## Notes

If no seeded protocols exist, this test validates the execution path still works with a minimal test protocol. Create one if needed.
