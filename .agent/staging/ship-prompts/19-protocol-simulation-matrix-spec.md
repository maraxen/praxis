# Protocol Simulation Matrix Test Spec (P1)

> **Stream**: 7 - Test Coverage  
> **Effort**: M (2-3 hours)  
> **Priority**: P1  
> **Approach**: TDD - Write tests first, categorize failures  
> **Isolation**: Use git worktree before starting

---

## Objective

Create the actual `protocol-simulation-matrix.spec.ts` that runs ALL seeded protocols in simulation mode. The goal is to identify which protocols fail due to:
1. **Protocol Issues** - Bugs in the protocol definition itself
2. **Application Issues** - Bugs in the execution logic

This separates "the test harness works" from "the protocols work".

---

## Context Files (Read First)

1. `praxis/web-client/playwright.static.config.ts` → Static test config (already created)
2. `src/app/core/db/seed-data/protocols/` → Seeded protocol definitions
3. `src/assets/protocols/` → Protocol pickle/Python files
4. `e2e/specs/execution-browser.spec.ts` → Existing execution tests
5. `.agent/skills/using-git-worktrees/SKILL.md` → Worktree setup

---

## Worktree Setup (REQUIRED FIRST STEP)

```bash
# Create isolated worktree for this feature
git worktree add .worktrees/protocol-matrix -b feat/protocol-simulation-matrix
cd .worktrees/protocol-matrix/praxis/web-client
npm install
```

---

## Implementation Steps

### Step 1: Discover All Seeded Protocols

```bash
# Find all protocol seed data
grep -r "id:" src/app/core/db/seed-data/protocols/ --include="*.ts" | head -20

# Find all protocol files
find src/assets/protocols -name "*.pickle" -o -name "*.py" | head -20
```

### Step 2: Create Protocol Registry Helper

```typescript
// e2e/helpers/protocol-registry.ts
export interface ProtocolTestEntry {
  id: string;
  name: string;
  requiresHardware: boolean;
  expectedDuration: number; // seconds
  knownIssues?: string[];
}

export const PROTOCOL_TEST_REGISTRY: ProtocolTestEntry[] = [
  // Auto-seed from discovery, then manually annotate
  { id: 'simple-transfer', name: 'Simple Transfer', requiresHardware: false, expectedDuration: 30 },
  { id: 'serial-dilution', name: 'Serial Dilution', requiresHardware: false, expectedDuration: 45 },
  // ... add all discovered protocols
];

export const SIMULATABLE_PROTOCOLS = PROTOCOL_TEST_REGISTRY.filter(p => !p.requiresHardware);
```

### Step 3: Create Matrix Test Spec

```typescript
// e2e/specs/protocol-simulation-matrix.spec.ts
import { test, expect } from '../fixtures/worker-db.fixture';
import { SIMULATABLE_PROTOCOLS, ProtocolTestEntry } from '../helpers/protocol-registry';

test.describe('@slow Protocol Simulation Matrix', () => {
  // Extended timeout for protocol execution
  test.setTimeout(180000);

  for (const protocol of SIMULATABLE_PROTOCOLS) {
    test(`simulates "${protocol.name}" to completion`, async ({ page }, testInfo) => {
      // Tag test with protocol ID for filtering
      testInfo.annotations.push({ type: 'protocol', description: protocol.id });

      // Navigate to run wizard
      await page.goto('/app/run');

      // Select the protocol
      await page.getByTestId(`protocol-card-${protocol.id}`).click();
      
      // Select simulated machine
      await page.getByTestId('machine-simulated').click();
      await page.getByRole('button', { name: 'Next' }).click();
      
      // Skip deck setup for simple protocols (or configure if needed)
      await page.getByRole('button', { name: 'Start' }).click();

      // Wait for execution to start
      await expect(page.getByTestId('execution-status')).toContainText('Running', { timeout: 30000 });

      // Wait for completion (with protocol-specific timeout)
      const timeout = protocol.expectedDuration * 1000 * 2; // 2x buffer
      await expect(page.getByTestId('execution-status')).toContainText('Completed', { timeout });

      // Verify no Python errors
      const logs = await page.getByTestId('execution-logs').textContent();
      expect(logs).not.toContain('Error');
      expect(logs).not.toContain('Traceback');
    });
  }
});
```

### Step 4: Create Failure Categorization Report

After running the matrix, failures fall into categories:

```typescript
// e2e/helpers/matrix-reporter.ts
export interface MatrixResult {
  protocolId: string;
  status: 'passed' | 'failed' | 'skipped';
  failureCategory?: 'protocol_bug' | 'app_bug' | 'timeout' | 'setup_error';
  errorMessage?: string;
  duration: number;
}

// Custom reporter that outputs categorized results
export class MatrixReporter {
  onTestEnd(test, result) {
    if (result.status === 'failed') {
      const category = this.categorizeFailure(result.error);
      console.log(`[${category}] ${test.title}: ${result.error.message}`);
    }
  }

  categorizeFailure(error: Error): string {
    const msg = error.message.toLowerCase();
    if (msg.includes('traceback') || msg.includes('python')) return 'protocol_bug';
    if (msg.includes('timeout')) return 'timeout';
    if (msg.includes('locator') || msg.includes('selector')) return 'app_bug';
    return 'unknown';
  }
}
```

---

## Running the Matrix

```bash
# Run all simulatable protocols (slow - run overnight or in CI)
RUN_SLOW_TESTS=1 npx playwright test protocol-simulation-matrix.spec.ts \
  --config=playwright.static.config.ts \
  --reporter=list \
  --timeout=180000 \
  2>&1 | tee /tmp/protocol-matrix-results.log

# Run a specific protocol for debugging
npx playwright test protocol-simulation-matrix.spec.ts \
  --grep "Simple Transfer" \
  --config=playwright.static.config.ts \
  --debug
```

---

## Expected Output

After running, produce a categorized report:

```markdown
# Protocol Simulation Matrix Results

## Summary
- Total: 15 protocols
- Passed: 10
- Failed (Protocol Bug): 3
- Failed (App Bug): 1  
- Skipped (Hardware Required): 1

## Protocol Bugs (to fix in protocol definitions)
- `hamilton-cherry-pick`: NameError: 'plate_1' not defined
- `serial-dilution-96`: IndexError: list index out of range

## Application Bugs (to fix in execution logic)
- `pcr-amplification`: Timeout waiting for 'deck-setup' step

## Skipped (require real hardware)
- `usb-device-calibration`
```

---

## Verification

```bash
# Dry run to check test discovery
npx playwright test protocol-simulation-matrix.spec.ts --list

# Quick smoke of first 3 protocols
npx playwright test protocol-simulation-matrix.spec.ts --grep "Simple|Serial|Basic" --config=playwright.static.config.ts
```

---

## Merge Back

```bash
cd /Users/mar/Projects/praxis
git checkout main
git merge feat/protocol-simulation-matrix
git worktree remove .worktrees/protocol-matrix
```

---

## Success Criteria

- [ ] All seeded protocols identified and registered
- [ ] Matrix test spec runs each protocol dynamically
- [ ] Failures are categorized (protocol vs app vs timeout)
- [ ] Report clearly separates issues by category
- [ ] At least one full run completed with results documented
- [ ] Known protocol bugs documented for future fixes
