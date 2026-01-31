# Machine Instantiation in JupyterLite (P1)

> **Stream**: 7 - Test Coverage  
> **Effort**: M (2-3 hours)  
> **Priority**: P1

---

## Objective

Create E2E tests that verify machine instantiation completes successfully in JupyterLite/Pyodide context, validating the ChatterboxBackend and simulated frontend instantiation path.

---

## Context Files (Read First)

1. `.agent/staging/logic-audits/simulated_machine_instantiation_recon.md` → Instantiation flow
2. `e2e/specs/jupyterlite-bootstrap.spec.ts` → JupyterLite tests
3. `e2e/specs/playground-direct-control.spec.ts` → Direct control tests
4. `src/app/features/playground/services/direct-control-kernel.service.ts`

---

## What to Test

| Scenario | Expected Result |
|----------|-----------------|
| Simulated Hamilton STAR instantiation | LiquidHandler created with ChatterboxBackend |
| Simulated OT-2 instantiation | LiquidHandler created with ChatterboxBackend |
| Machine setup() completes | No Python errors, ready signal received |
| Machine stop() completes | Clean teardown, resources released |

---

## Scope

### Change
- Create `e2e/specs/jupyterlite-machine-instantiation.spec.ts`
- OR extend `playground-direct-control.spec.ts`

### Do NOT Change
- Backend instantiation logic
- Python shims
- JupyterLite service

---

## Implementation Steps

1. **Review existing coverage**
   ```bash
   grep -r "instantiat\|LiquidHandler\|ChatterboxBackend" e2e/specs/ --include="*.ts"
   ```

2. **Create instantiation test**
   ```typescript
   // e2e/specs/jupyterlite-machine-instantiation.spec.ts
   import { test, expect } from '@playwright/test';
   
   test.describe('@slow JupyterLite Machine Instantiation', () => {
     test.beforeEach(async ({ page }) => {
       // Set longer timeout for JupyterLite bootstrap
       test.setTimeout(180000);
     });
     
     test('instantiates simulated Hamilton STAR', async ({ page }) => {
       await page.goto('/app/playground');
       
       // Wait for JupyterLite ready
       await expect(page.locator('[data-testid="jupyterlite-ready"]'))
         .toBeVisible({ timeout: 60000 });
       
       // Select simulated Hamilton
       await page.locator('[data-testid="machine-selector"]').click();
       await page.locator('[data-testid="machine-hamilton-star-sim"]').click();
       
       // Click connect/instantiate
       await page.locator('[data-testid="connect-machine"]').click();
       
       // Wait for instantiation complete
       await expect(page.locator('[data-testid="machine-status"]'))
         .toContainText('Connected', { timeout: 30000 });
       
       // Verify no errors in console
       const errors = await page.evaluate(() => 
         (window as any).__pythonErrors || []
       );
       expect(errors).toHaveLength(0);
     });
     
     test('machine setup() completes without error', async ({ page }) => {
       // ... similar setup ...
       
       // Click setup
       await page.locator('[data-testid="setup-machine"]').click();
       
       // Wait for setup complete
       await expect(page.locator('[data-testid="machine-status"]'))
         .toContainText('Ready', { timeout: 30000 });
     });
     
     test('machine stop() cleans up correctly', async ({ page }) => {
       // ... setup machine first ...
       
       // Click stop/disconnect
       await page.locator('[data-testid="disconnect-machine"]').click();
       
       // Verify disconnected state
       await expect(page.locator('[data-testid="machine-status"]'))
         .toContainText('Disconnected', { timeout: 10000 });
     });
   });
   ```

3. **Add Python error capture**
   ```typescript
   // In test setup, inject error capture
   await page.addInitScript(() => {
     (window as any).__pythonErrors = [];
     const originalError = console.error;
     console.error = (...args) => {
       if (args.some(a => String(a).includes('Python') || String(a).includes('Pyodide'))) {
         (window as any).__pythonErrors.push(args.join(' '));
       }
       originalError.apply(console, args);
     };
   });
   ```

4. **Tag as @slow**
   - JupyterLite tests require long bootstrap time
   - Skip in regular CI runs

---

## Verification

```bash
# Run instantiation tests (slow, local only)
npx playwright test jupyterlite-machine-instantiation.spec.ts --reporter=line --timeout=180000 2>&1 | tail -20
```

---

## Success Criteria

- [ ] Hamilton STAR sim instantiates successfully
- [ ] OT-2 sim instantiates successfully  
- [ ] setup() completes without Python errors
- [ ] stop() cleans up correctly
- [ ] No regression in other JupyterLite tests

---

## Notes

This test depends on JupyterLite bootstrap working. If bootstrap tests are failing (@slow tagged), fix those first.

The simulated backends use ChatterboxBackend which should always succeed - if tests fail, it indicates a shim loading or FQN resolution issue.
