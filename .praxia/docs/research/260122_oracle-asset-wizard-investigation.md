# Oracle Advisory: Asset Wizard Investigation Report

**Date:** 2026-01-21  
**Dispatch ID:** d260121182523962_fa3b  
**Task ID:** 260121181800  
**Advisory Type:** Architecture & Debugging

---

## Executive Summary

This investigation analyzed the Asset Wizard and Run Protocol guided setup components to evaluate five reported issues. The "No definitions found" bug has been resolved, but the architecture reveals opportunities for improvement in the simulated toggle, category filtering, and terminology clarification.

---

## Issue Analysis

### 1. ✅ "No definitions found" Bug - RESOLVED

**Current Implementation (Lines 131-149 of asset-wizard.ts):**

```typescript
const assetType$ = this.typeStepFormGroup.get('assetType')!.valueChanges.pipe(startWith(''));
const category$ = this.categoryStepFormGroup.get('category')!.valueChanges.pipe(startWith(''));
const query$ = this.searchSubject.pipe(startWith(''), debounceTime(300), distinctUntilChanged());

this.searchResults$ = combineLatest([assetType$, category$, query$]).pipe(
  switchMap(([assetType, category, query]) => {
    if (!assetType) return of([]);
    if (assetType === 'MACHINE') {
      return this.assetService.searchMachineDefinitions(query).pipe(
        map(defs => defs.filter(d => d.plr_category === 'Machine'))
      );
    } else {
      return this.assetService.searchResourceDefinitions(query, category);
    }
  })
);
```

**Assessment:** The logic is **robust**. Key safeguards:

- ✅ Uses `combineLatest` ensuring all three streams have values before emitting
- ✅ `startWith('')` provides initial values, preventing cold-start issues
- ✅ Guard clause `if (!assetType) return of([])` handles empty state
- ✅ Machine definitions properly filtered to exclude raw backends (`plr_category === 'Machine'`)

**Minor Recommendations:**

1. Consider adding error handling with `catchError` to prevent stream termination on API errors
2. Add loading state indicator during search

---

### 2. ⚠️ Missing Simulated Toggle in Asset Wizard

**Context:** The Machine Registry (`machine-filters.component.ts`) has a mature simulated toggle implementation (lines 92-114), but the Asset Wizard lacks this feature.

**Current State:**

- `MachineFiltersComponent` has a 3-state toggle: All / Physical / Simulated
- `AssetWizard` has no equivalent filter during definition selection

**Recommendation:**

```xml
<advice type="architecture">
<question>Should the Asset Wizard include a simulated/physical filter?</question>
<context>
- The wizard creates new asset instances from definitions
- Browser mode auto-selects simulated backends (line 186-190)
- Definition cards show "Simulated" or "Real Only" badges (lines 140-147 in HTML)
</context>
<options>
  <option name="Add toggle to Step 3 (Definition)">
    <pros>Consistent with machine filters UX; reduces cognitive load</pros>
    <cons>Adds UI complexity; redundant given badge indicators</cons>
  </option>
  <option name="Keep current approach (badges only)">
    <pros>Simpler UI; badges provide at-a-glance info</pros>
    <cons>No way to filter when many definitions exist</cons>
  </option>
</options>
<recommendation>Add toggle ONLY if definition count exceeds 20 items</recommendation>
<reasoning>
The wizard already auto-selects simulated backends in browser mode.
The "Simulated/Real Only" badges on cards provide visual distinction.
A toggle becomes valuable only with many definitions.
</reasoning>
<risks>Low - Either approach works well for current scale</risks>
</advice>
```

---

### 3. ⚠️ Category Filtering Not Applied to Machine Definitions

**Current Behavior:**

- Step 2 selects a category (e.g., "LiquidHandler")
- Step 3 searches **all** machine definitions, ignoring the selected category

**Root Cause (line 142-144):**

```typescript
return this.assetService.searchMachineDefinitions(query).pipe(
  map(defs => defs.filter(d => d.plr_category === 'Machine'))  // Only filters by type, not category!
);
```

**Comparison with Resources (line 146):**

```typescript
return this.assetService.searchResourceDefinitions(query, category);  // ✅ Category is passed
```

**Recommendation:**

```xml
<advice type="debugging">
<symptom>Machine category selection doesn't filter definitions</symptom>
<hypotheses>
  <hypothesis likelihood="high">
    <cause>searchMachineDefinitions() doesn't accept category parameter</cause>
    <test>Check AssetService.searchMachineDefinitions signature</test>
  </hypothesis>
</hypotheses>
<recommended_approach>
1. Add machine_category filter to searchMachineDefinitions:
   ```typescript
   searchMachineDefinitions(query: string, category?: string): Observable<MachineDefinition[]> {
     return this.getMachineDefinitions().pipe(
       map(defs => defs.filter(d =>
         (d.name.toLowerCase().includes(query.toLowerCase()) || ...) &&
         (!category || d.machine_category === category)
       ))
     );
   }
   ```

2. Update asset-wizard.ts line 142:

   ```typescript
   return this.assetService.searchMachineDefinitions(query, category).pipe(
     map(defs => defs.filter(d => d.plr_category === 'Machine'))
   );
   ```

</recommended_approach>
</advice>

```

---

### 4. 📊 Data Model Analysis: `plr_category` vs `machine_category`

**Findings from `generate_browser_db.py`:**

| Field | Usage | Example Values |
|-------|-------|----------------|
| `plr_category` | Distinguishes Machine vs Resource vs Backend | `"Machine"`, `"Plate"`, `"TipRack"` |
| `machine_category` | Specific machine type | `"LiquidHandler"`, `"PlateReader"`, `"Centrifuge"` |

**Current Filter Logic:**
- `asset-wizard.ts:143` filters by `plr_category === 'Machine'` to exclude backends
- `generate_browser_db.py:210` sets `plr_category = "Machine"` for all frontends

**Assessment:** The data model is **correct and intentional**:
- `plr_category` serves as an asset-type discriminator
- `machine_category` provides granular type classification
- This dual-field approach enables both broad (Machine/Resource) and narrow (LiquidHandler/PlateReader) filtering

---

### 5. 🔤 Chatterbox vs Simulated Terminology

**Findings:**

| Term | Definition | Usage Pattern |
|------|------------|---------------|
| **Simulated** | Generic term for any non-hardware backend | UI-facing, user-friendly |
| **Chatterbox** | Specific PLR backend class naming convention | Code-facing, PLR-specific |

**Evidence:**
- `generate_browser_db.py:686`: `backend_type = "simulator" if "Chatterbox" in backend.fqn`
- Frontend refers to "Simulated" in UI labels
- `availableSimulationBackends` in wizard: `['Simulated', 'Chatterbox']`

**Recommendation:**

```xml
<advice type="architecture">
<question>How should we handle Chatterbox vs Simulated terminology?</question>
<context>
- PLR uses "Chatterbox" as the class suffix for simulation backends
- End users understand "Simulated" better than "Chatterbox"
- Current system mixes both terms
</context>
<options>
  <option name="Normalize to 'Simulated' in UI">
    <pros>User-friendly; consistent mental model</pros>
    <cons>May confuse developers familiar with PLR</cons>
  </option>
  <option name="Keep hybrid approach">
    <pros>Technical accuracy preserved</pros>
    <cons>Inconsistent UX</cons>
  </option>
</options>
<recommendation>Normalize to "Simulated" in UI, preserve "Chatterbox" in code/logs</recommendation>
<reasoning>
Users don't need to know internal PLR naming conventions.
Backend type classification already uses "simulator" vs "hardware".
The mapping already exists in generate_browser_db.py.
</reasoning>
<risks>None - purely cosmetic change</risks>
</advice>
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Asset Wizard Flow                           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
    ┌──────────────┐    ┌──────────▼──────────┐    ┌──────────────────┐
    │  Step 1:     │    │     Step 2:         │    │    Step 3:       │
    │  Type        │───▶│     Category        │───▶│    Definition    │
    │  [Machine/   │    │  [LiquidHandler/    │    │  [Hamilton STAR/ │
    │   Resource]  │    │   PlateReader/...]  │    │   OT-2/...]      │
    └──────────────┘    └──────────┬──────────┘    └────────┬─────────┘
                                   │                        │
                                   │                        ▼
┌──────────────────────────────────┼─────────────────────────────────────┐
│                          Observable Chain                              │
├────────────────────────────────────────────────────────────────────────┤
│  combineLatest([assetType$, category$, query$])                        │
│       │                                                                │
│       ▼                                                                │
│  if (!assetType) → []                                                  │
│  if (MACHINE)    → searchMachineDefinitions(query)                     │
│                       .filter(plr_category === 'Machine')              │
│                       ⚠️ MISSING: .filter(machine_category === cat)    │
│  if (RESOURCE)   → searchResourceDefinitions(query, category) ✅       │
└────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Data Layer (SQLite/API)                          │
├─────────────────────────────────────────────────────────────────────────┤
│  machine_definitions:                                                   │
│    - accession_id, name, fqn                                           │
│    - plr_category  (Machine | Backend)  ← for type filtering           │
│    - machine_category (LiquidHandler, etc.) ← for category filtering   │
│    - available_simulation_backends []                                   │
│                                                                         │
│  resource_definitions:                                                  │
│    - accession_id, name, fqn                                           │
│    - plr_category (Plate, TipRack, Trough, etc.)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

| Priority | Issue | Action | Effort | Files |
|----------|-------|--------|--------|-------|
| **P1** | Category filter for machines | Add `category` param to `searchMachineDefinitions()` | 30 min | `asset.service.ts`, `asset-wizard.ts` |
| **P2** | Terminology normalization | Map "Chatterbox" → "Simulated" in UI display | 15 min | `asset-wizard.ts` |
| **P3** | Simulated toggle | Add optional toggle to Definition step | 1 hr | `asset-wizard.ts`, `asset-wizard.html` |
| **P4** | Error handling | Add `catchError` to `searchResults$` | 15 min | `asset-wizard.ts` |

---

## Conclusion

The Asset Wizard is architecturally sound with one **functional gap**: category filtering for machine definitions. The terminology confusion (Chatterbox vs Simulated) is cosmetic but should be addressed for UX consistency. The "No definitions found" bug is resolved, and the Observable chain is robust.

**Oracle Recommendation:** Proceed with P1 (category filter) as the primary fix. Other items can be addressed in subsequent iterations.
