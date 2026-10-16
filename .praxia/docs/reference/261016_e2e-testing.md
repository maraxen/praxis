---
title: 'Web-client Playwright E2E guidelines and pre-ship checklist'
description: E2E commands, priority classes, assertion and timeout rules, Playwright wait strategies, and the pre-ship checklist for praxis/web-client; moved verbatim out of the always-on harness file.
status: active
task_id: 261016_harness-fleet-audit
date: '261016'
---

Provenance (261016): the former CLAUDE.md judged `npx playwright test` as the E2E entry point stale ("there is no npm `e2e` script. The browser gate is Python/Playwright-driven through `scripts/repl_smoke.py`, orchestrated by `repl.yml`"). The specs under `praxis/web-client/e2e/` still exist; the text below is the web-client suite only, not the CI gate.

### Commands (E2E rows)

| Action | Command |
|--------|---------|
| E2E Tests | `npx playwright test` |
| E2E (smoke) | `npx playwright test smoke.spec.ts` |

## E2E Testing Guidelines

### Priority Classification

| Priority | Tests | Target |
|----------|-------|--------|
| **P0** | `smoke.spec.ts`, `01-onboarding.spec.ts` | <20s, 100% pass |
| **P1** | `03-protocol-execution.spec.ts`, `protocol-library.spec.ts` | Core value |
| **P2** | `asset-wizard.spec.ts`, `asset-inventory.spec.ts` | Data management |
| **P3+** | `jupyterlite-*.spec.ts`, `playground-*.spec.ts` | Advanced |

### Assertions (Web-First)

```typescript
// ✅ Good - auto-waits
await expect(page.locator('.result')).toBeVisible();
await expect(page).toHaveURL(/\/dashboard/);

// ❌ Bad - manual waits
await page.waitForTimeout(2000);
```

### Timeout Guidelines

- Element visibility: **5-10s**
- Page loads: **15s**
- DB operations: **10s**
- Pyodide init: **30s** (with justification)

### User Journey Validation

- [ ] Start from Home/Library (no deep-linking)
- [ ] Verify data persistence after actions
- [ ] Verify PLR parameters match UI selections

### Playwright Best Practices

**Server Detection First:**
```bash
# Always detect running dev servers before testing
node -e "require('./lib/helpers').detectDevServers()"
```

**Wait Strategies:**
```typescript
// ✅ Preferred - state-driven waits
await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
await page.waitForURL('**/dashboard');

// For heavy init (SQLite WASM)
await page.locator('[data-sqlite-ready="true"]').waitFor({ state: 'attached' });
```

**Worker Isolation:**
- Each parallel worker needs unique DB name: `praxis-worker-${workerIndex}.db`
- 10s safety margin for 4+ concurrent workers

## Pre-Ship Checklist

1. **`npx playwright test smoke.spec.ts`** - Must pass
2. **`npx playwright test 01-onboarding.spec.ts`** - Must pass
3. **`npx playwright test protocol-library.spec.ts`** - Must pass
4. **`bun run build`** - No errors
5. **`bun run lint`** - Clean
6. **Browser DevTools** - No console errors
