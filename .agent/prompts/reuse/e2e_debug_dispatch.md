# Jules E2E Test Debug Dispatch

**Purpose:** Run and debug a specific Playwright E2E test in the Praxis web-client.

---

## Environment Configuration

### Browser Mode (Default)
- **Dev server**: Already running on `http://localhost:4200`
- **Working directory**: `praxis/web-client`
- **Config**: Default `playwright.config.ts`

### GH Pages Simulation Mode
- **Simulation URL**: `http://localhost:8080/praxis/`
- **Config**: `playwright.ghpages.config.ts` (webServer config auto-starts simulation)
- No need to manually start a server - the config handles it.

---

## Test Commands

### Browser Environment
```bash
cd praxis/web-client
timeout 120 bunx playwright test <SPEC_FILE> --project=chromium --reporter=list 2>&1 | tail -60
```

### GH Pages Environment  
```bash
cd praxis/web-client
timeout 120 bunx playwright test <SPEC_FILE> --config=playwright.ghpages.config.ts --project=ghpages-chromium --reporter=list 2>&1 | tail -60
```

> **CRITICAL**: Always use `--project=chromium` or `--project=ghpages-chromium`. Do NOT run all projects.

---

## Database Context

The E2E tests use **OPFS-backed SQLite** with pre-seeded data:

| Database | Size | Contents |
|----------|------|----------|
| `praxis.db` | 897KB | Protocols, machines, resources, registry items |

### Isolation Mechanism
- Each Playwright worker gets isolated DB: `praxis-worker-{workerIndex}`
- Fresh import from `src/assets/db/praxis.db` on `?resetdb=1`
- Page objects handle worker-scoped DB automatically via `worker-db.fixture.ts`

### Key Services
- `SqliteOpfsService` - Main persistence service
- `SqliteOpfsWorker` - Web worker for OPFS operations
- Look for `[SqliteOpfsService]` and `[SqliteOpfsWorker]` prefixes in console logs

---

## Analysis Framework

When investigating test failures, address each of these:

### 1. Test Coverage Assessment
- What user journey does this test cover?
- Is the test exercising realistic user behavior?
- Are assertions checking meaningful outcomes?

### 2. Error Isolation Analysis
- Is this error specific to this test, or likely affecting other tests?
- Check for common infrastructure issues:
  - SQLite timeout (increase if seeing `[data-sqlite-ready]` timeout)
  - Route resolution (verify `app/` prefix for GH Pages compatibility)
  - Asset loading (check for 404s on wasm/db files)

### 3. Root Cause Classification

| Category | Indicators | Action |
|----------|------------|--------|
| **Test Flakiness** | Passes sometimes, timing-dependent | Add explicit waits, increase timeouts |
| **Selector Drift** | Element not found but page loaded | Update selector, check responsive breakpoints |
| **Infrastructure** | Multiple tests fail same way | Fix root cause in fixtures/page objects |
| **App Bug** | Consistent failure, app logic issue | Fix in source code, not test |

### 4. Debugging Commands

```bash
# View error context (if test failed)
cat test-results/<test-folder>/error-context.md

# View trace (interactive)
bunx playwright show-trace test-results/<test-folder>/trace.zip

# View screenshot (if captured)
ls test-results/<test-folder>/*.png
```

---

## Orchestrator Context

<!-- ORCHESTRATOR: Replace this section with test-specific context -->

**Test File**: `<SPEC_FILE>`

**Test Purpose**: <!-- What this test validates -->

**Key Assertions**: <!-- What the test checks -->

**Known Issues**: <!-- Any known flakiness or gotchas -->

**Related Tests**: <!-- Other tests that share infrastructure -->

**Special Considerations**: <!-- e.g., protocol execution tests verify serialization AND full step completion -->

---

## Deliverables

1. **Test Execution Summary**
   - Pass/fail status for each test case
   - Failure messages with line numbers

2. **Root Cause Analysis** (if failures)
   - Classification from framework above
   - Evidence (screenshots, logs, traces)

3. **Fix Proposal** (if applicable)
   - Code changes with file paths
   - Verification command after fix

4. **Systemic Observations**
   - Any patterns indicating broader issues
   - Recommendations for test infrastructure

---

## Example Dispatch

```markdown
## Orchestrator Context

**Test File**: `e2e/specs/protocol-execution.spec.ts`

**Test Purpose**: Validates complete protocol execution flow from selection through completion.

**Key Assertions**:
- Protocol selection wizard navigates correctly
- Input parameters are serialized and passed to Pyodide correctly  
- All protocol steps execute in sequence
- Execution completes with success status (not just "started")

**Known Issues**: 
- Pyodide loading can be slow (60s+ on first load)
- OPFS lock contention if parallel workers hit same DB

**Related Tests**: `interactive-protocol.spec.ts`, `protocol-simulation-matrix.spec.ts`

**Special Considerations**: 
This test covers the FULL execution lifecycle. Partial success (e.g., step 1/3 completes) 
is a FAILURE. Pay attention to the execution monitor showing "Completed" vs "Running".
```
