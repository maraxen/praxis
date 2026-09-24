---
title: 'v0.1-alpha Debug Handoff'
---

# v0.1-alpha Debug Handoff

**Created**: 2026-01-21 18:04
**Session**: Orchestrator Bug Triage & Dispatch

---

## 🔴 CRITICAL BLOCKERS (P0)

### 1. "No definitions found" - All Definition Searches Broken

**Impact**: Cannot add machines/resources in Asset Wizard, blocks testing live instrument interface and REPL hardware connection

**Symptom**: Asset Wizard Step 2 shows "No definitions found matching ''" for all searches

**Root Cause Investigation Needed**:

- `generate_browser_db.py` now seeds `plr_category` correctly
- DB shows correct data: 20 machines with `plr_category='Machine'`, 141 resources
- Frontend filtering may still be broken
- Check: `AssetWizard.searchResults$` Observable chain
- Check: `SqliteService` or `AssetService` query methods

**Dispatch Recommendation**: Use `@oracle` persona for deep reconnaissance

---

### 2. protocol_runs Schema Missing Column

**Error**: `table protocol_runs has no column named protocol_definition_accession_id`

**Impact**: Cannot create protocol runs, execution fails

**Fix Needed**:

- Add column to `praxis/web-client/src/assets/db/schema.sql`
- Regenerate `praxis.db`
- May also need to update `generate_browser_schema.py`

---

### 3. Build Error - Missing Method

**Error**: `Property 'isSelectiveTransferProtocol' does not exist on type 'RunProtocolComponent'`
**File**: `run-protocol.component.ts:685`

**Fix**: Add missing method or remove the call

---

## 🟡 Medium Priority Issues

### 4. Selective Transfer Still Shows 2 Well Args (4.1)

**Expected**: Single `indices` parameter
**Actual**: Still showing `source_wells` and `target_wells` separately
**May need**: Protocol regeneration or parameter definition update

### 5. Autocomplete Display Value Not Updating (2.5.1)

**Expected**: Show selected asset name after selection
**Actual**: Still shows first/original item

### 6. Autocomplete Dropdown Positioning (2.5.3)

**Issues**:

- Should be pushed further left
- Should stay same size with selected items

### 7. Deck Setup Resource Dialog Style (5.1)

**Current**: Items visible but no dynamic highlighting as each is confirmed
**Expected**: Same step-by-step highlighting as Step 2, one item at a time with Done

### 8. Run Not Found After Creation (6.1)

**Symptom**: Execution Monitor says "Run not found"
**Likely Related To**: #2 (protocol_runs schema issue)

---

## ✅ Working/Verified

| Feature | Status |
|---------|--------|
| Category icon cards in Asset Wizard | ✅ |
| Dialog size parity (Playground vs Assets) | ✅ |
| Dialog size stability | ✅ |
| Autocomplete clear button (X) | ✅ |
| "Clear All" button | ✅ |
| "Auto-fill All" button | ✅ |
| Tooltip hover delay | ✅ |
| Deck items visible after confirm | ✅ (partially - no dynamic change) |
| Live Experiments → Execution Monitor nav | ✅ (but run not found) |
| Backend types filtered from categories | ✅ |
| Asset Wizard bypass first step | ✅ |

---

## 📁 Key Files for Investigation

```
# Definition Search (CRITICAL)
praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts
praxis/web-client/src/app/features/assets/services/asset.service.ts
praxis/web-client/src/app/core/services/sqlite.service.ts
praxis/web-client/src/app/core/db/sqlite-repository.ts

# Schema Fix
praxis/web-client/src/assets/db/schema.sql
scripts/generate_browser_schema.py
scripts/generate_browser_db.py

# Build Error
praxis/web-client/src/app/features/run-protocol/run-protocol.component.ts:685

# Parameter UI
praxis/protocol/protocols/selective_transfer.py
```

---

## 🎯 Recommended Next Session Priority

1. **FIRST**: Fix build error (`isSelectiveTransferProtocol`)
2. **SECOND**: Deep recon on "No definitions found" with `@oracle`
3. **THIRD**: Fix `protocol_runs` schema
4. **THEN**: Address remaining UX issues

---

## 💾 Quick Commands

```bash
# Regenerate DB
uv run scripts/generate_browser_db.py

# Check DB contents
sqlite3 praxis/web-client/src/assets/db/praxis.db "SELECT COUNT(*), plr_category FROM machine_definitions GROUP BY plr_category"

# Run dev server
cd praxis/web-client && npm run start:browser
```

---

## 📊 Session Statistics

| Metric | Count |
|--------|-------|
| Phases completed | 1 (Phase 1) |
| Phases partially complete | 4 (2, 2.5, 3, 4, 5) |
| Tasks created | ~15 |
| Dispatches sent | ~20 |
| Critical blockers remaining | 3 |
| Medium issues remaining | 5 |

---

## 🔗 Related Reports

- `.agent/reports/jules_handover_20260121.md` - Earlier session handoff
- `.agent/reports/inventory_search_investigation.md` - Previous definition search analysis
- `.agent/reports/backend_categories_investigation.md` - plr_category root cause
