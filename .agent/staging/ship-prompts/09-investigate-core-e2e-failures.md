# Investigate Core E2E Test Failures (P0)

> **Stream**: Test Stability  
> **Effort**: M (2-4h)  
> **Priority**: P0 - Blocking ship

---

## Objective

Investigate and fix the root cause of smoke/onboarding/health-check test failures that are blocking the core P0 specs from passing.

---

## Symptoms

| Spec | Error | Line |
|------|-------|------|
| `smoke.spec.ts` | `TimeoutError: page.waitForFunction: Timeout 10000ms exceeded` | waitForAppReady |
| `01-onboarding.spec.ts` | `'.sidebar-rail, .nav-rail, app-sidebar'` not visible with timeout 10000ms | Line 50 |
| `health-check.spec.ts` | `Test timeout of 15000ms exceeded` | Line 9 |

All failures share a common pattern: **page/app not rendering or becoming ready before assertions**.

---

## Context Files (Read First)

1. `e2e/page-objects/welcome.page.ts` → `waitForAppReady()` method
2. `e2e/page-objects/smoke.page.ts` → `navRail` locator definition
3. `e2e/fixtures/worker-db.fixture.ts` → DB initialization flow
4. `e2e/specs/smoke.spec.ts` → Failing test code
5. `e2e/specs/01-onboarding.spec.ts` → Failing test code
6. `e2e/specs/health-check.spec.ts` → Failing test code

---

## Investigation Steps

### 1. Reproduce and Capture

```bash
# Run with trace enabled to see what's happening
npx playwright test smoke.spec.ts --trace on --headed

# View the trace
npx playwright show-trace test-results/*/trace.zip
```

### 2. Check Selector Validity

```bash
# Start dev server if not running
cd praxis/web-client && npm start

# In browser DevTools, check if selectors exist:
# - document.querySelector('.sidebar-rail')
# - document.querySelector('.nav-rail')
# - document.querySelector('app-sidebar')
```

### 3. Analyze waitForAppReady()

Look at `welcome.page.ts` - what condition is it waiting for?
- Is it waiting for a specific DOM element?
- Is it waiting for a JavaScript variable/signal?
- Does the timeout match reality?

### 4. Check DB Initialization Path

The `worker-db.fixture.ts` initializes SQLite via URL params. Check:
- Is the `dbName` being set correctly?
- Is `resetdb=1` triggering proper cleanup?
- Are the async operations timing out?

---

## Hypothesis Tree

```
Tests failing with timeout
├── Page never loads
│   ├── Dev server issues (check port 4200)
│   └── Build/bundle errors (check console)
├── Page loads but selectors wrong
│   ├── UI changed, selectors stale
│   └── Wrong component rendering
├── Page loads but slow to become "ready"
│   ├── DB init taking too long
│   ├── waitForAppReady() condition never met
│   └── Race condition in fixture setup
└── Parallel worker interference
    ├── DB name collision
    └── Port conflicts
```

---

## Expected Deliverables

1. **Root cause identified** with evidence (screenshot/trace)
2. **Fix applied** to correct selectors or wait conditions
3. **Verification** that smoke.spec.ts, 01-onboarding.spec.ts, health-check.spec.ts pass
4. **Regression check** on other specs

---

## Success Criteria

- [ ] `smoke.spec.ts` passes (4 tests)
- [ ] `01-onboarding.spec.ts` passes (1 test)
- [ ] `health-check.spec.ts` passes (1 test)
- [ ] No regressions in other passing specs
