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

## Bun Development Guidelines

---
description: Use Bun instead of Node.js, npm, pnpm, or vite.
globs: "*.ts, *.tsx, *.html, *.css, *.js, *.jsx, package.json"
alwaysApply: false
---

Default to using Bun instead of Node.js.

- Use `bun <file>` instead of `node <file>` or `ts-node <file>`
- Use `bun test` instead of `jest` or `vitest`
- Use `bun build <file.html|file.ts|file.css>` instead of `webpack` or `esbuild`
- Use `bun install` instead of `npm install` or `yarn install` or `pnpm install`
- Use `bun run <script>` instead of `npm run <script>` or `yarn run <script>` or `pnpm run <script>`
- Use `bunx <package> <command>` instead of `npx <package> <command>`
- Bun automatically loads .env, so don't use dotenv.

### APIs

- `Bun.serve()` supports WebSockets, HTTPS, and routes. Don't use `express`.
- `bun:sqlite` for SQLite. Don't use `better-sqlite3`.
- `Bun.redis` for Redis. Don't use `ioredis`.
- `Bun.sql` for Postgres. Don't use `pg` or `postgres.js`.
- `WebSocket` is built-in. Don't use `ws`.
- Prefer `Bun.file` over `node:fs`'s readFile/writeFile
- Bun.$`ls` instead of execa.

### Testing

Use `bun test` to run tests.

```ts
// index.test.ts
import { test, expect } from "bun:test";

test("hello world", () => {
  expect(1).toBe(1);
});
```

### Frontend

Use HTML imports with `Bun.serve()`. Don't use `vite`. HTML imports fully support React, CSS, Tailwind.

Server:

```ts
// index.ts
import index from "./index.html"

Bun.serve({
  routes: {
    "/": index,
    "/api/users/:id": {
      GET: (req) => {
        return new Response(JSON.stringify({ id: req.params.id }));
      },
    },
  },
  // optional websocket support
  websocket: {
    open: (ws) => {
      ws.send("Hello, world!");
    },
    message: (ws, message) => {
      ws.send(message);
    },
    close: (ws) => {
      // handle close
    }
  },
  development: {
    hmr: true,
    console: true,
  }
})
```

HTML files can import .tsx, .jsx or .js files directly and Bun's bundler will transpile & bundle automatically. `<link>` tags can point to stylesheets and Bun's CSS bundler will bundle.

```html
<!-- index.html -->
<html>
  <body>
    <h1>Hello, world!</h1>
    <script type="module" src="./frontend.tsx"></script>
  </body>
</html>
```

With the following `frontend.tsx`:

```tsx
// frontend.tsx
import React from "react";
import { createRoot } from "react-dom/client";

// import .css files directly and it works
import './index.css';

const root = createRoot(document.body);

export default function Frontend() {
  return <h1>Hello, world!</h1>;
}

root.render(<Frontend />);
```

Then, run index.ts

```sh
bun --hot ./index.ts
```

For more information, read the Bun API docs in `node_modules/bun-types/docs/**.mdx`.

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
- AGENTS.md: Updated with Bun development guidelines
- AGENTS.md: Removed Autonomous Mode Development Cycle

