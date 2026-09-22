---
title: 'v0.1-Alpha Orchestrator Handoff'
---

# v0.1-Alpha Orchestrator Handoff

**Created**: 2026-01-21 18:45  
**Session**: Bug Triage & Dispatch  
**Status**: VERY CLOSE - Multiple regressions and new issues identified

---

## 🔴🔴🔴 SUPER TOP PRIORITY (P0) 🔴🔴🔴

### 0. Playground Inventory vs Asset Management - DIFFERENT FLOWS NEEDED

**URGENT**: User needs to test PlateReader connection from Jupyter kernel before going home.

**Current Problem**: Asset Wizard in Playground tries to CREATE new assets when it should let user SELECT EXISTING machines from DB.

#### Required UX/Architecture

| Context | Machine Flow | Resource Flow |
|---------|--------------|---------------|
| **Asset Management** | Create NEW from definition | Create NEW from definition |
| **Playground Inventory** | Select EXISTING from DB | Create NEW (same as Asset Mgmt) |
| | OR simulate on-the-fly | OR select existing |

#### Key Requirements

1. **Playground Machine Selection**:
   - Index and display EXISTING machines from database
   - User picks an already-created machine instance
   - Definition/config step ONLY for simulation mode
   - Both simulated AND real machines must be selectable

2. **Simulation Support**:
   - If user wants to SIMULATE a machine in Playground, they can
   - This is the ONLY case where definition/config applies in Playground

3. **Resource Flow**:
   - Same in both contexts (create new OR select existing)
   - No special conditional logic needed

4. **Machine Flow Conditional Logic**:
   - Detect context: `isPlaygroundContext` vs `isAssetManagementContext`
   - Playground + Machine → Show existing DB machines + simulate option
   - Asset Management + Machine → Show definitions for creation

5. **Backend Types Bug**:
   - STILL showing backend types in lists
   - Filter to `plr_category === 'Machine'` must be enforced

#### Implementation Hints

```typescript
// In AssetWizard or caller
if (this.context === 'playground' && this.assetType === 'MACHINE') {
  // Show existing machines from machines table
  this.machines$ = this.assetService.getMachines(); // NOT definitions
  // Add "Simulate New..." option at bottom
} else {
  // Current flow: show definitions for creation
  this.searchResults$ = this.assetService.searchMachineDefinitions(...);
}
```

---

## 🔴 CRITICAL BLOCKERS (P0)

### 1. Backend Types RETURNED to Category List (REGRESSION)

**Status**: Was supposedly fixed, now broken again  
**Impact**: Asset Wizard shows backend types mixed with user-facing definitions  
**Symptom**: Backends appearing in category selection, mixing simulated/real incorrectly

### 2. Run Protocol Machine Selection - NO CHOICES VISIBLE

**Status**: BLOCKING  
**Impact**: Cannot proceed with protocol execution at all  
**Symptom**: Machine selection shows empty list, cannot assess downstream steps

### 3. Protocol Run "Selective Transfer" Regression

**Status**: CRITICAL REGRESSION  
**Symptom**: `transfer_pattern` and `replicate_count` parameters RESTORED to Selective Transfer  
**Impact**: Parameters that were removed are back, unclear how this happened

---

## 🔴 Critical Errors from Console

### 4. Direct Control Component Crash

```
ERROR TypeError: Cannot read properties of undefined (reading 'forEach')
    at _DirectControlComponent.buildForm (direct-control.component.ts:88:17)
    at _DirectControlComponent.onMethodSelected (direct-control.component.ts:83:10)
```

**Impact**: Direct Control crashes when selecting a method

### 5. Direct Control Shows Wrong UI

**Symptom**: "Select method" shows simulated types and backends, NOT methods with arguments  
**Expected**: Should show machine methods with argument forms

### 6. NG0100 ExpressionChangedAfterItHasBeenCheckedError

```
ERROR RuntimeError: NG0100: Expression has changed after it was checked
Expression location: _DirectControlComponent component
```

**Impact**: Causes Angular change detection issues, unstable UI

### 7. Missing Table: machine_frontend_definitions

```
[SqliteService] Definition tables may not exist yet: Error: no such table: machine_frontend_definitions
```

**Impact**: May affect machine definition loading

---

## 🟡 Medium Priority Issues

### 8. Asset Creation Error UX

**Current**: Raw error `UNIQUE constraint failed: resources.name` shown in console  
**Expected**: User-friendly message "Please rename - this name already exists"  
**Additional**: Default instance name should have unique ID appended

### 9. SharedArrayBuffer Not Defined

```
python.worker.ts:17 Uncaught ReferenceError: SharedArrayBuffer is not defined
```

**Impact**: Python worker fails to initialize (may affect REPL execution)

---

## ✅ Verified Working (from earlier testing)

| Feature | Status |
|---------|--------|
| Empty search shows all definitions | ✅ (your manual fix) |
| Category filtering passes param | ✅ (your manual fix) |
| combineLatest reactive chain | ✅ |

---

## 📋 Dispatched Tasks (Pending Completion)

| Dispatch ID | Priority | Issue | Status |
|-------------|----------|-------|--------|
| `d260121182523962_fa3b` | P1 | Run Protocol selection (oracle) | Pending |
| `d260121182707788_6a04` | P1 | Asset Wizard backend/frontend mixing | Pending |
| `d260121182711853_5752` | P1 | Build error - isSelectiveTransferProtocol | Pending |
| `d260121182715791_144f` | P1 | protocol_runs schema missing column | Pending |
| `d260121182720378_5c17` | P2 | Selective Transfer 2 well args | Pending |
| `d260121182724155_98d9` | P2 | Autocomplete display value | Pending |
| `d260121182727767_2aa0` | P2 | Autocomplete positioning | Pending |
| `d260121182727776_02d4` | P2 | Deck Setup highlighting | Pending |
| `d260121182926564_7a3e` | P1 | Machine category filter | Pending |
| `d260121182938779_7bd0` | P2 | Chatterbox → Simulated terminology | Pending |

---

## 🎯 Recommended Priority for Fresh Orchestrator

### IMMEDIATE (Fix before anything else)

1. **Direct Control Component Crash** - `direct-control.component.ts:88` - forEach on undefined
2. **Run Protocol Machine Selection Empty** - Cannot proceed without machines
3. **Backend Types in Category List** - Filter by `plr_category === 'Machine'` regression

### THEN

1. Check `machine_frontend_definitions` table existence
2. Add unique ID suffix to default asset instance names
3. Add user-friendly error messages for asset creation

### VERIFY

- Check why `transfer_pattern` and `replicate_count` returned to Selective Transfer
- Verify dispatched fixes completed successfully

---

## 📁 Key Files to Investigate

```
# Direct Control Crash
praxis/web-client/src/app/features/playground/components/direct-control/direct-control.component.ts:88

# Machine Selection Empty
praxis/web-client/src/app/features/run-protocol/components/guided-setup/

# Asset Wizard Category Filtering
praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts

# Schema Issue
praxis/web-client/src/assets/db/schema.sql
scripts/generate_browser_schema.py
```

---

## 💾 Quick Commands

```bash
# Check dispatch status
dispatch(action: "status")

# Regenerate DB
uv run scripts/generate_browser_db.py

# Check DB for table
sqlite3 praxis/web-client/src/assets/db/praxis.db ".tables"

# Run dev server
cd praxis/web-client && npm run start:browser
```

---

## 📊 Session Statistics

| Metric | Count |
|--------|-------|
| Tasks created | 12 |
| Dispatches sent | 10 |
| Critical blockers | 3 |
| Regressions identified | 2 |
| Console errors | 4 |
