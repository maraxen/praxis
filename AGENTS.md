# AGENTS.md

> This project is managed by the **Orbital Velocity Orchestrator** at `~/Projects`.

---

## Command Execution Best Practices

**CRITICAL: Use background mode with output filtering.**

```bash
# Long-running commands - use timeout and background mode
time timeout 60 npx playwright test --reporter=line 2>&1 | tee /tmp/e2e-run.txt | tail -20

# Fast commands - grep/filter output
bun run build 2>&1 | grep -E "error|warning|built" | head -20

# Multi-step with tee for evidence
bun run lint 2>&1 | tee /tmp/lint.log | tail -5
```

**Filtering patterns:**
- `| tail -N` - Last N lines (test summaries)
- `| head -N` - First N lines (compilation errors)
- `| grep -E "pattern"` - Specific patterns
- `| tee /tmp/file.log` - Save for evidence while filtering

---

## AST-Grep for Structural Code Search

Use `ast-grep` for structural code search (superior to text grep).

### Quick Patterns

```bash
# Find signal declarations
ast-grep run --pattern 'signal<$TYPE>($INIT)' --lang typescript src/

# Find all service injections
ast-grep run --pattern 'inject($SERVICE)' --lang typescript src/

# Find console.log calls
ast-grep run --pattern 'console.log($ARG)' --lang typescript src/
```

### Complex Rules (always use `stopBy: end`)

```bash
# Find async functions containing await
ast-grep scan --inline-rules "id: async-await
language: typescript
rule:
  kind: function_declaration
  has:
    pattern: await \$EXPR
    stopBy: end" src/
```

### Debug AST Structure

```bash
ast-grep run --pattern 'class $NAME { $$$BODY }' --lang typescript --debug-query=cst
```

### Metavariables
- `$VAR` - Single named node
- `$$VAR` - Single unnamed node (operators)
- `$$$MULTI` - Zero or more nodes

---

## Project: Praxis

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Angular 19 (standalone, signals, zoneless) |
| **Language** | TypeScript (strict mode) |
| **Build** | Angular CLI / esbuild |
| **Unit Tests** | Vitest |
| **E2E Tests** | Playwright |
| **Persistence** | SQLite WASM + OPFS |
| **Python Runtime** | JupyterLite + Pyodide |

### Commands

| Action | Command |
|--------|---------|
| Dev Server | `cd praxis/web-client && bun start` |
| Build | `bun run build` |
| E2E Tests | `npx playwright test` |
| E2E (smoke) | `npx playwright test smoke.spec.ts` |

### Codebase Structure

```text
praxis/web-client/
├── src/app/
│   ├── core/            # Services, workers, SQLite, Pyodide
│   ├── features/        # Feature modules (protocols, assets)
│   ├── shared/          # Shared components, pipes
│   └── layout/          # App shell, navigation
├── e2e/
│   ├── specs/           # Test files (*.spec.ts)
│   ├── page-objects/    # Page Object Model classes
│   ├── fixtures/        # worker-db.fixture for isolation
│   └── helpers/         # Wizard helpers
└── src/assets/browser-data/  # PLR definitions, seed data
```

---

## Autonomous Mode Development Cycle

> **Activation:** When the prompt specifies "autonomous mode", follow this cycle continuously until all issues are resolved.

### Phase 1: RECON (Audit & Research)

**Goal:** Understand the full landscape before making any changes.

```bash
# Run ALL specs to get comprehensive picture
timeout 600 npx playwright test --reporter=line 2>&1 | tee /tmp/full-audit.log

# Categorize results
grep -E "passed|failed|skipped" /tmp/full-audit.log
```

**Document for each failing spec:**
1. **Error type:** Missing method, timeout, selector, assertion
2. **Source logic:** Does the underlying feature work correctly?
3. **Test logic:** Is the test testing the right thing?
4. **Classification:**
   - `STALE` - Test references removed/renamed UI elements
   - `OUTDATED` - Test logic doesn't match current behavior
   - `REDUNDANT` - Test duplicates another test's coverage
   - `BROKEN_SOURCE` - Actual feature bug
   - `INFRASTRUCTURE` - Test helper/fixture issue

### Phase 2: PLAN (Prioritized Fixes)

**Triage Order:**
1. **Infrastructure** (PageObjects, fixtures) - Unblocks many tests
2. **Critical paths** (execution, persistence, deployment)
3. **Core value** (asset management, protocols)
4. **Nice-to-have** (visual, optimization tests)

**For each fix, document:**
- **Assumption:** "I assume X because Y"
- **Decision:** "I chose A over B because..."
- **Risk:** How might this break?

### Phase 3: EXECUTE (Test-Driven Fixes)

**Iron Rule:** Fix ONE spec at a time.

```
FOR each failing spec:
  1. RUN spec in isolation → capture exact error
  2. INVESTIGATE source vs test logic mismatch
  3. IF source wrong → fix source, verify test
     IF test wrong → fix test, verify source
     IF redundant → mark for removal
  4. RUN spec again → confirm green
  5. RUN related specs → no regressions
```

**Delete, Don't Fix:**
- Tests with no corresponding feature
- Duplicate coverage
- Tests for deprecated APIs

### Phase 4: EVALUATE (Verification Gate)

```bash
# Full suite pass
npx playwright test --reporter=line 2>&1 | tail -10

# Build verification
bun run build && bun run lint
```

**Exit Criteria:**
- [ ] All P0/P1 tests passing
- [ ] P2 tests at ≥80% pass rate
- [ ] Build clean
- [ ] No regressions in previously passing tests

---

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

---

## Core Skill Context

### Test-Driven Development (TDD)

**Iron Law:** `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST`

**Cycle:** RED → GREEN → REFACTOR

```typescript
// RED: Write failing test
test('should serialize machine FQN', async () => {
    const result = await serializeMachine(machine);
    expect(result.fqn).toMatch(/^pylabrobot\./);
});
// Verify it fails for the RIGHT reason (feature missing, not typo)

// GREEN: Minimal code to pass - no over-engineering

// REFACTOR: Clean up, keep tests green
```

**Red Flags (STOP and delete code):**
- Code before test
- Test passes immediately
- "Just this once"
- "Tests after achieve same goals"

---

### Systematic Debugging

**Iron Law:** `NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST`

**Four Phases:**

1. **Root Cause Investigation**
   - Read error messages COMPLETELY
   - Reproduce consistently
   - Check recent changes (`git diff`)
   - Add diagnostic instrumentation at component boundaries

2. **Pattern Analysis**
   - Find working examples in codebase
   - Compare differences

3. **Hypothesis Testing**
   - Form single hypothesis: "X is root cause because Y"
   - Test SMALLEST possible change
   - One variable at a time

4. **Implementation**
   - Create failing test case FIRST
   - Single fix for root cause
   - If 3+ fixes failed → **question the architecture**

**Red Flags:**
- "Quick fix for now, investigate later"
- "Just try changing X"
- Multiple fixes at once
- "One more fix attempt" (after 2+ failures)

---

### Verification Before Completion

**Iron Law:** `NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE`

**Gate Function:**
```
BEFORE claiming any status:
1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh)
3. READ: Full output, check exit code
4. VERIFY: Does output confirm claim?
5. ONLY THEN: Make the claim
```

**Common Failures:**

| Claim | Requires | NOT Sufficient |
|-------|----------|----------------|
| Tests pass | Output: 0 failures | Previous run, "should pass" |
| Build succeeds | Exit code 0 | Linter passing |
| Bug fixed | Test symptom passes | Code changed |

**Red Flags:**
- Using "should", "probably", "seems to"
- Expressing satisfaction before verification
- "Great!", "Perfect!", "Done!" without evidence

---

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

---

## Angular Patterns (Praxis)

### Signals

```typescript
protocols = signal<Protocol[]>([]);
loading = signal(false);
filteredProtocols = computed(() => 
    this.protocols().filter(p => p.status === 'active')
);

// Template
@if (loading()) { <mat-spinner /> }
```

### Deferred Initialization

```typescript
// For heavy workers (Pyodide, Plotly) - don't init in constructor
private async ensureReady(): Promise<void> {
    if (!this.worker && this.status() === 'idle') {
        this.initWorker();
    }
}
```

---

## Pre-Ship Checklist

1. **`npx playwright test smoke.spec.ts`** - Must pass
2. **`npx playwright test 01-onboarding.spec.ts`** - Must pass
3. **`npx playwright test protocol-library.spec.ts`** - Must pass
4. **`bun run build`** - No errors
5. **`bun run lint`** - Clean
6. **Browser DevTools** - No console errors

---

## Current State (2026-01-31)

**✅ Passing:**
- `smoke.spec.ts` (4 tests, ~6s)
- `01-onboarding.spec.ts` (1 test, ~4s)  
- `health-check.spec.ts` (1 test, ~10s) - Fixed Observable pattern
- `protocol-library.spec.ts` (8 tests, ~21s)

**❌ Needs Attention:**
- `jupyterlite-bootstrap.spec.ts` - Missing PageObject method
- `ghpages-deployment.spec.ts` - Path resolution, SPA routing
- `asset-wizard.spec.ts` - Stale selectors (layout drift)
- `playground-direct-control.spec.ts` - Infrastructure issue

**Active Handoff:** `.agent/staging/e2e_autonomous_handoff.md`

**Recent Fixes:**
- health-check.spec.ts: Replaced dynamic RxJS import with inline toPromise()
- health-check.spec.ts: Use localStorage for mode check
- AGENTS.md: Added Autonomous Mode Development Cycle

