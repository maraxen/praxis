# Machine Type Filtering Investigation Report

## Status

**In Progress - Diagnosis Phase**

We have identified a contradiction between the codebase logic and the reported behavior. The code explicitly attempts to filter *out* LiquidHandlers for deck-less protocols, yet the user reports seeing *only* LiquidHandlers.

## Key Findings

### 1. Code Logic Contradiction

In `praxis/web-client/src/app/features/run-protocol/run-protocol.component.ts`, the filtering logic explicitly handles `requires_deck === false`:

```typescript
// Filter based on deck requirement
if (protocol?.requires_deck === false) {
  // If deck not required, hide LiquidHandlers
  allCompat = allCompat.filter(d =>
    d.machine.machine_category !== 'LiquidHandler' &&
    d.machine.machine_category !== 'HamiltonSTAR'
  );
}
```

This logic *should* prevent LiquidHandlers from appearing for the "Plate Reader Assay". The fact that they *do* appear suggests one of two critical failures:

1. **Property Loss:** The `requires_deck` property is returning `true` or `undefined` at runtime for the Plate Reader Assay.
2. **Category Mismatch:** The "Simulated Plate Reader" is not being loaded, leaving only specific fallback templates that might be hardcoded elsewhere.

### 2. Protocol and Database Definition

The source of truth appears correct:

- **Protocol Source (`plate_reader_assay.py`)**: Explicitly sets `requires_deck=False` and `param_metadata` for a `PlateReader`.
- **Database Generation (`generate_browser_db.py`)**: Correctly parses this property and inserts it into the `function_protocol_definitions` table.
- **Seed Data (`plr-definitions.ts`)**: Contains a `Simulated Plate Reader` with `machine_type: 'PlateReader'`.

### 3. Debugging Obstacles

Attempts to verify runtime state via E2E tests (`debug-machine-filtering.spec.ts`) have been blocked by environmental instability:

- The "Plate Reader Assay" card was not visible in the test environment Protocol List, causing the test to fail before entering the wizard.
- This suggests the `SqliteService` might not be successfully loading the generated `praxis.db` or `schema.sql` in the test runner's browser instance, potentially falling back to an empty state or legacy defaults.

## Hypotheses & Next Steps

### Hypothesis A: `requires_deck` is lost in `SqliteService` transformation

The `SqliteService.getProtocols()` method maps raw DB rows to `FunctionProtocolDefinition` objects. If the boolean mapping `p['requires_deck'] === 1` is incorrect or the column is missing in the query, it might default to `undefined` (falsy), but the filter checks `=== false`.

**Action:** Audit `SqliteService.getProtocols()` mapping logic for `requires_deck`.

### Hypothesis B: Mock Data Templates are Incomplete

In `ExecutionService.getCompatibility()` (Browser Mode), we map `machineDefinitions` to compatibility templates. If `sqliteService.machineDefinitions` returns only default LiquidHandlers, the filtering logic has nothing else to show (or shows nothing, and maybe there's a separate "show default" fallback I missed).

**Action:** Verify the `Simulated Plate Reader` definition is actually making it into `machine_definitions` table in the browser.

## Recommendations for Orchestrator

1. **Manual Verification**: If possible, manually load the app and check the Network tab/Console logs for the `requires_deck` property on the selected protocol.
2. **Fix E2E Data Loading**: The E2E tests need a guaranteed way to ensure the database is seeded. We should consider a `test.beforeEach` that forces a DB reset/seed.
3. **Review `SqliteService` Mapping**: A targeted code review of the `resultToObjects` and specific field mapping in `sqlite.service.ts` is the highest ROI next step.
