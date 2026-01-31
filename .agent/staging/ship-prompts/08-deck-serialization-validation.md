# Add Deck Serialization Validation (P2)

> **Stream**: 3 - Protocol Execution Quality  
> **Effort**: M (2-3 hours)  
> **Priority**: P2

---

## Objective

Add runtime validation that generated deck setup Python FQNs match actual PyLabRobot classes, preventing silent failures when serialized class names don't exist.

---

## Context Files (Read First)

1. `.agent/staging/logic-audits/comprehensive_logic_audit.md` → Section "Deck State Serialization"
2. `src/app/features/run-protocol/services/wizard-state.service.ts:397-479`
3. `src/assets/python/web_bridge.py`
4. `src/assets/browser-data/plr-definitions.ts`

---

## Root Cause Analysis

**Problem**: `serializeToPython()` generates class names heuristically:

```typescript
carrier.fqn.split('.').pop()?.toUpperCase()
```

**Risk**: If the FQN doesn't match an actual PLR class, the deck setup script will fail at runtime with cryptic Python errors.

---

## Scope

### Change
- Add validation in `wizard-state.service.ts` before returning serialized script
- Create mapping of valid PLR class names from `plr-definitions.ts`
- Add clear error messages for invalid FQNs

### Do NOT Change
- Python runtime code
- Deck UI components
- Asset wizard

---

## Implementation Steps

1. **Extract valid class names from PLR definitions**
   ```typescript
   // src/app/core/utils/plr-validator.ts
   import { PLR_RESOURCE_DEFINITIONS } from '@assets/browser-data/plr-definitions';
   
   export function getValidPLRClassNames(): Set<string> {
     const classes = new Set<string>();
     for (const def of PLR_RESOURCE_DEFINITIONS) {
       const className = def.fqn.split('.').pop();
       if (className) classes.add(className);
     }
     return classes;
   }
   
   export function validatePLRClassName(fqn: string, validClasses: Set<string>): boolean {
     const className = fqn.split('.').pop();
     return className ? validClasses.has(className) : false;
   }
   ```

2. **Add validation to serializeToPython()**
   ```typescript
   // In wizard-state.service.ts
   serializeToPython(): { script: string; warnings: string[] } {
     const warnings: string[] = [];
     const validClasses = getValidPLRClassNames();
     
     // ... existing serialization logic ...
     
     // Validate each carrier/resource FQN
     for (const carrier of uniqueCarriers) {
       if (!validatePLRClassName(carrier.fqn, validClasses)) {
         warnings.push(`Unknown carrier class: ${carrier.fqn}`);
       }
     }
     
     return { script, warnings };
   }
   ```

3. **Surface warnings in UI**
   - Show warning toast when deck script has validation warnings
   - Don't block execution (run anyway with warning)

4. **Add unit tests**
   ```bash
   npm run test -- --include="**/plr-validator.spec.ts"
   ```

---

## Verification

```bash
# Run deck-setup spec
npx playwright test deck-setup.spec.ts --reporter=line 2>&1 | tail -10

# Run protocol execution spec
npx playwright test protocol-execution.spec.ts --reporter=line 2>&1 | tail -10
```

---

## Success Criteria

- [ ] `plr-validator.ts` created with tests
- [ ] `serializeToPython()` returns warnings array
- [ ] Invalid FQNs produce visible warning (not silent failure)
- [ ] Existing deck-setup tests still pass
