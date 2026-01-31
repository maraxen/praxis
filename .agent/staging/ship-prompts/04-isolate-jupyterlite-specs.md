# Isolate JupyterLite Specs (P2)

> **Stream**: 4 - Test Cleanup & Isolation  
> **Effort**: S (30 min)  
> **Priority**: P2

---

## Objective

Tag JupyterLite/Pyodide specs with `@slow` to skip in CI, preventing 180s+ timeouts from blocking pipeline.

---

## Context Files (Read First)

1. `.agent/staging/e2e_persistent_bugs.md` → Root cause #4
2. `.agent/staging/logic-audits/06-jupyterlite.md` → Bootstrap architecture
3. `playwright.config.ts` → Current config
4. `e2e/specs/jupyterlite-*.spec.ts` → Target specs

---

## Root Cause Analysis

**Problem**: JupyterLite/Pyodide doesn't bootstrap reliably in test context, causing 180s+ timeouts.

**Why**: WASM loading + Python package installation is inherently slow and flaky in headless browsers.

**Strategy**: Don't block ship on fixing this - isolate for separate investigation.

---

## Scope

### Change
- `e2e/specs/jupyterlite-bootstrap.spec.ts`
- `e2e/specs/jupyterlite-paths.spec.ts`
- `e2e/specs/jupyterlite-optimization.spec.ts`
- `e2e/specs/playground-direct-control.spec.ts`
- `playwright.config.ts` (add grep config for CI)

### Do NOT Change
- JupyterLite service code
- Test logic within the specs
- Other specs

---

## Implementation Steps

1. **Add @slow tag to each JupyterLite spec**
   ```typescript
   // jupyterlite-bootstrap.spec.ts
   test.describe('@slow JupyterLite Bootstrap', () => {
     // ... existing tests
   });
   ```

2. **Update playwright.config.ts for CI**
   ```typescript
   export default defineConfig({
     // ... existing config
     
     // Skip slow tests in CI
     grep: process.env.CI ? /^(?!.*@slow)/ : undefined,
     // Or use grepInvert
     grepInvert: process.env.CI ? /@slow/ : undefined,
   });
   ```

3. **Verify local run includes slow**
   ```bash
   npx playwright test jupyterlite-bootstrap.spec.ts --list
   ```

4. **Verify CI mode excludes slow**
   ```bash
   CI=true npx playwright test --list 2>&1 | grep -c jupyterlite
   # Should be 0
   ```

---

## Verification

```bash
# List tests without @slow
npx playwright test --grep-invert @slow --list 2>&1 | head -20

# Confirm JupyterLite specs are excluded
npx playwright test --grep-invert @slow --list 2>&1 | grep jupyterlite
# Should return nothing
```

---

## Success Criteria

- [ ] All 4 JupyterLite specs tagged with `@slow`
- [ ] `playwright.config.ts` updated for CI
- [ ] CI run excludes JupyterLite specs
- [ ] Local run still includes them (for manual testing)
