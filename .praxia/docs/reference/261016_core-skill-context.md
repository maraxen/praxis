---
title: 'Core skill context: TDD, systematic debugging, verification'
description: The test-first, root-cause-first and verify-before-claiming procedures, for agents without the superpowers skills.
status: active
task_id: 261016_harness-fleet-audit
date: '261016'
---

*(Moved verbatim from AGENTS.md on 261016. Claude Code sessions get the same rules from the superpowers skills; Codex, Cursor and agy read this file.)*

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

