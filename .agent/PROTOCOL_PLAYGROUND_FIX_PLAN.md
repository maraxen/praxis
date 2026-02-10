# Protocol Execution & Playground Fix Plan

**Date**: 2026-02-09
**Status**: Ready for Implementation

---

## Executive Summary

Two code paths have the same root cause - **wrong FQNs in the database**.

### Root Cause: `generate_browser_db.py` CRITICAL_DECKS has wrong FQNs

```python
# WRONG (currently in generate_browser_db.py:272):
"fqn": "pylabrobot.liquid_handling.backends.hamilton.STARlet.STARLetDeck"

# CORRECT:
"fqn": "pylabrobot.resources.hamilton.STARLetDeck"
```

The path `pylabrobot.liquid_handling.backends.hamilton.STARlet` **doesn't exist**.
Decks are in `pylabrobot.resources`, not `pylabrobot.liquid_handling.backends`.

### Correct FQNs (verified from PLR source)
- ✅ `pylabrobot.resources.hamilton.STARLetDeck` (re-exported from `__init__.py`)
- ✅ `pylabrobot.resources.hamilton.hamilton_decks.STARLetDeck` (direct path)
- ✅ `pylabrobot.resources.hamilton.HamiltonSTARDeck` (class)
- ✅ `pylabrobot.resources.hamilton.VantageDeck` (from vantage_decks.py)
- ✅ `pylabrobot.resources.opentrons.deck.OTDeck` (class)
- ❌ `pylabrobot.resources.hamilton.STARlet.STARLetDeck` (NO SUCH MODULE)
- ❌ `pylabrobot.liquid_handling.backends.hamilton.STARlet.STARLetDeck` (WRONG PATH)

---

## Fixes Applied

### Fix 1: generate_browser_db.py - CRITICAL_DECKS FQNs ✅

```python
# BEFORE (WRONG):
"fqn": "pylabrobot.liquid_handling.backends.hamilton.STARlet.STARLetDeck"

# AFTER (CORRECT):
"fqn": "pylabrobot.resources.hamilton.STARLetDeck"
```

### Fix 2: deck-catalog.service.ts - Detection and Spec FQNs ✅

```typescript
// Line 70 - Fixed detection to include correct FQN
if (fqn === 'pylabrobot.resources.hamilton.STARLetDeck' ||
    fqn === 'pylabrobot.resources.hamilton.hamilton_decks.STARLetDeck' ||

// Line 352 - Fixed returned FQN in getHamiltonSTARLetSpec()
fqn: 'pylabrobot.resources.hamilton.STARLetDeck',
```

### Fix 3: Regenerated praxis.db ✅

Database now contains correct FQNs:
```
HamiltonSTARDeck|pylabrobot.resources.hamilton.HamiltonSTARDeck
STARLetDeck|pylabrobot.resources.hamilton.STARLetDeck
VantageDeck|pylabrobot.resources.hamilton.VantageDeck
OTDeck|pylabrobot.resources.opentrons.deck.OTDeck
```

### No Changes Needed: playground-asset.service.ts ✅

The service correctly uses `machine.deck_type` which flows from:
1. `deck_definition_catalog.fqn` (DB) →
2. `selectedDeckType.fqn` (wizard) →
3. `machine.deck_type` (asset) →
4. `deckFqn` (code generation)

---

## Issue 2: wizard-state.service.ts - Already Correct

### Location
`praxis/web-client/src/app/features/run-protocol/services/wizard-state.service.ts:648`

### Status: ✅ CORRECT
```typescript
case 'HamiltonSTARLetDeck': return 'pylabrobot.resources.hamilton.STARLetDeck';
```

---

## Issue 3: Playground code generation uses deckConfigId

### Location
`praxis/web-client/src/app/features/playground/services/playground-asset.service.ts:165-170`

### Current Flow
```typescript
const deckFqn = deckConfigId || (machine as any).deck_type;
// ...
const parts = deckFqn.split('.');
const deckClass = parts.pop()!;
const deckModule = parts.join('.');
lines.push(`from ${deckModule} import ${deckClass}`);
```

### Analysis
- If `deckConfigId` is `'pylabrobot.resources.hamilton.STARLetDeck'` → Works ✅
- If `deckConfigId` is `'HamiltonSTARLetDeck'` → Generates `from  import HamiltonSTARLetDeck` ❌

### Fix: Add FQN resolver
```typescript
private resolveDeckFqn(deckType: string | null | undefined): string | null {
    if (!deckType) return null;

    // Already a full FQN
    if (deckType.includes('pylabrobot.')) return deckType;

    // Map short names to FQNs
    const DECK_FQN_MAP: Record<string, string> = {
        'HamiltonSTARDeck': 'pylabrobot.resources.hamilton.HamiltonSTARDeck',
        'HamiltonSTARLetDeck': 'pylabrobot.resources.hamilton.STARLetDeck',
        'STARLetDeck': 'pylabrobot.resources.hamilton.STARLetDeck',
        'STARDeck': 'pylabrobot.resources.hamilton.HamiltonSTARDeck',
        'VantageDeck': 'pylabrobot.resources.hamilton.VantageDeck',
        'OTDeck': 'pylabrobot.resources.opentrons.deck.OTDeck',
        'EVO100Deck': 'pylabrobot.resources.tecan.EVO100Deck',
        'EVO150Deck': 'pylabrobot.resources.tecan.EVO150Deck',
        'EVO200Deck': 'pylabrobot.resources.tecan.EVO200Deck',
    };

    return DECK_FQN_MAP[deckType] || null;
}
```

---

## Issue 4: Protocol Execution - Verify is_deck_resource Flow

### Status: Needs Verification

The recon showed parameter resolution should work, but let me verify the actual flow:

1. **Manifest Building** (`wizard-state.service.ts:618`):
   ```typescript
   is_deck_resource: isResource  // Set based on type hint matching
   ```

2. **Parameter Resolution** (`web_bridge.py:104-112`):
   ```python
   if p.get("is_deck_resource") and deck:
       resource = deck.get_resource(p["name"])
   ```

### Potential Issues
- If type hint doesn't include 'plate', 'tiprack', or 'resource' → `is_deck_resource` won't be set
- If manifest parameter name doesn't match resource name on deck → lookup fails

### Debugging Steps
1. Add console.log in `buildExecutionManifest()` to see manifest shape
2. Add print in `materialize_context()` to see incoming parameters
3. Verify resource names match between manifest and deck layout

---

## Implementation Order

### Phase 1: Fix FQN (Quick Fix)

**File 1**: `deck-catalog.service.ts`
- Line 70: `STARlet.STARLetDeck` → `STARLetDeck`
- Line 352: `STARlet.STARLetDeck` → `STARLetDeck`

**Estimated Effort**: 2 minutes

### Phase 2: Add FQN Resolver to Playground

**File 2**: `playground-asset.service.ts`
- Add `resolveDeckFqn()` method
- Update `generateMachineCode()` to use resolver

**Estimated Effort**: 10 minutes

### Phase 3: Validate Protocol Execution

**Test Command**:
```bash
cd praxis/web-client && npx playwright test e2e/specs/user-journeys.spec.ts --grep "protocol execution"
```

**Manual Test**:
1. Open Praxis UI
2. Start a protocol run with simple_transfer
3. Verify resources are instantiated and passed to protocol function

---

## Files to Modify

| File | Changes |
|------|---------|
| `deck-catalog.service.ts` | Fix STARLetDeck FQN (lines 70, 352) |
| `playground-asset.service.ts` | Add `resolveDeckFqn()` helper, update `generateMachineCode()` |

---

## Verification Checklist

### Playground Path
- [ ] `from pylabrobot.resources.hamilton import STARLetDeck` imports without error
- [ ] `STARLetDeck()` factory creates valid deck
- [ ] Generated machine code runs in JupyterLite REPL

### Protocol Execution Path
- [ ] Manifest includes correct `is_deck_resource` flags
- [ ] Resources instantiated on deck via carriers
- [ ] `deck.get_resource(name)` returns nested resources
- [ ] Protocol function receives all required arguments

### E2E Tests
- [ ] `user-journeys.spec.ts` protocol execution tests pass
- [ ] `workcell-dashboard.spec.ts` deck selection tests pass
- [ ] JupyterLite bootstrap tests pass

---

## Next Steps

1. Apply fixes to `deck-catalog.service.ts` and `playground-asset.service.ts`
2. Test playground machine instantiation manually
3. Run E2E suite to validate protocol execution
4. Document any additional issues found during testing
