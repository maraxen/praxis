# Protocol Wizard E2E Test Failure - Deep Recon Required

## Context

The Protocol Simulation Matrix E2E test (`e2e/specs/protocol-simulation-matrix.spec.ts`) is failing. The test navigates through the protocol wizard but gets stuck after the machine selection step.

**Test output pattern:**
```
[Matrix] Selecting protocol: Selective Transfer
[Matrix] Clicked Continue (step 1)
[Matrix] Clicked Continue (step 2)
[Matrix] Selected machine/backend option
[Matrix] Clicked Continue (step 3)
[Matrix] Continue is disabled - need more selections
[Matrix] No advancement buttons visible/enabled on step 3
... (repeats for steps 4-14, never finding Start button)
```

**Recent changes:**
1. Added `seed_sample_resources()` to `scripts/generate_browser_db.py` - seeds 3 sample resources (Plate, TipRack, Trough)
2. Updated `sqlite-opfs.service.ts` to call `seedDefaultAssets()` on database load
3. Created `Justfile` with `generate-db` command using `uv run --with pylibftdi`

**Database state:**
- `praxis.db` has 148 resource definitions, 21 machine definitions, 6 protocols, 49 backends
- `praxis.db` has 3 seeded resources (Sample Plate, Sample TipRack, Sample Trough)
- `praxis.db` has 0 pre-seeded machines (by design - machines are created ephemerally)

## Required Reconnaissance

Before proposing any fixes, thoroughly investigate:

### 1. Wizard Step Structure
- Read `run-protocol.component.ts` and map out ALL wizard steps (mat-step components)
- Identify step indices and their corresponding form groups
- Understand what makes each step valid/invalid

### 2. Machine Selection Step (Step 3)
- Review `MachineArgumentSelectorComponent` deeply
- Understand how it builds requirements, filters backends, creates ephemeral machines
- Trace the `selectBackend()` async flow and when `validChange` emits
- Check if machine creation could be failing silently

### 3. Post-Machine Steps (Step 4+)
- Identify what step comes after machine selection for different protocols
- Check if there's a parameters step, wells step, or other intermediate steps
- Understand what form validation is blocking progress

### 4. Test Selector Analysis
- Review what selectors the test uses (`.option-card`, `.asset-card`, etc.)
- Check if these selectors actually exist in the wizard components
- Verify the test's button detection logic matches the wizard's actual buttons

### 5. Protocol Requirements
- Check what the "Selective Transfer" protocol requires (first protocol the test runs)
- Map its asset requirements to wizard steps
- Understand if this protocol has wells selection, special parameters, etc.

## Files to Investigate

- `praxis/web-client/src/app/features/run-protocol/run-protocol.component.ts`
- `praxis/web-client/src/app/shared/components/machine-argument-selector/machine-argument-selector.component.ts`
- `praxis/web-client/e2e/specs/protocol-simulation-matrix.spec.ts`
- `praxis/protocol/protocols/selective_transfer/selective_transfer.py` (protocol definition)
- `praxis/web-client/src/assets/db/praxis.db` (query for protocol requirements)

## Success Criteria

After recon, produce a plan that:
1. Identifies the exact step where the wizard gets stuck
2. Explains why Continue is disabled at that step
3. Proposes targeted fixes (could be test logic, component logic, or data seeding)
4. Includes verification commands to confirm the fix

## Commands for Verification

```bash
# Run the specific test with trace
cd praxis/web-client && npx playwright test e2e/specs/protocol-simulation-matrix.spec.ts --trace=on --reporter=list

# Query protocol requirements
sqlite3 praxis/web-client/src/assets/db/praxis.db "SELECT name, assets FROM function_protocol_definitions WHERE name LIKE '%selective%'"

# Check database state
sqlite3 praxis/web-client/src/assets/db/praxis.db "SELECT COUNT(*), 'resources' FROM resources UNION SELECT COUNT(*), 'machines' FROM machines UNION SELECT COUNT(*), 'backends' FROM machine_backend_definitions"
```
