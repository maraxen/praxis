# Asset Wizard Definition Filtering Logic Audit

> **Status**: ✅ Logic Appears Sound with Minor Concerns  
> **Date**: 2026-01-31  
> **Scope**: `AssetWizard` component and underlying `AssetService` data chain

---

## Summary

The asset wizard filtering logic for machine type → category → frontend → backend flows correctly. The FK-based backend filtering is properly implemented. However, there's a **subtle data source mismatch** between category facets and frontend definitions that could cause empty results in edge cases.

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          ASSET WIZARD FLOW                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Step 1: TYPE SELECTION                                                  │
│  ┌─────────────┐                                                        │
│  │  MACHINE    │ ──→ triggers getMachineFacets()                        │
│  │  RESOURCE   │ ──→ triggers getFacets()                               │
│  └─────────────┘                                                        │
│                                                                          │
│  Step 2: CATEGORY SELECTION                                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ getMachineFacets() returns machine_category from:               │    │
│  │   ↓                                                              │    │
│  │  ┌─────────────────────────┐                                    │    │
│  │  │ MachineDefinitions      │  ← Source table                    │    │
│  │  │ (machine_definitions)   │                                    │    │
│  │  └─────────────────────────┘                                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Step 3: FRONTEND SELECTION (Machines only)                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ getMachineFrontendDefinitions() returns ALL frontends           │    │
│  │   ↓                                                              │    │
│  │ Client-side filter: f.machine_category === category             │    │
│  │   ↓                                                              │    │
│  │  ┌─────────────────────────┐                                    │    │
│  │  │ MachineFrontendDefs     │  ← Different table!                │    │
│  │  │ (machine_frontend_defs) │                                    │    │
│  │  └─────────────────────────┘                                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Step 4: BACKEND SELECTION (Machines only)                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ getBackendsForFrontend(frontendId) uses FK query:               │    │
│  │   SELECT * FROM machine_backend_definitions                      │    │
│  │   WHERE frontend_definition_accession_id = ?                     │    │
│  │   ↓                                                              │    │
│  │  ┌─────────────────────────┐                                    │    │
│  │  │ MachineBackendDefs      │  ← FK lookup ✅                    │    │
│  │  │ (machine_backend_defs)  │                                    │    │
│  │  └─────────────────────────┘                                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Step 5: CONFIGURATION → CREATE                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Findings

### ✅ Correct: Backend FK Query

The `findByFrontend` method correctly uses the FK relationship:

```typescript
// async-repositories.ts:544-546
findByFrontend(frontendId: string): Observable<MachineBackendDefinition[]> {
    return this.findBy({ frontend_definition_accession_id: frontendId } ...);
}
```

### ✅ Correct: Reactive Subscription Chain

The wizard properly uses RxJS subscriptions to react to selections:

```typescript
// asset-wizard.ts:175-181
categoryStepFormGroup.get('category')?.valueChanges.subscribe(category => {
    if (assetType === 'MACHINE' && category) {
        this.frontends$ = this.assetService.getMachineFrontendDefinitions().pipe(
            map(frontends => frontends.filter(f => f.machine_category === category))
        );
    }
});
```

### ⚠️ Potential Issue: Data Source Mismatch

**Categories come from `MachineDefinitions`**, but **filtering applies to `MachineFrontendDefinitions`**:

| Step | Data Source | Table |
|------|-------------|-------|
| Categories | `getMachineFacets()` | `machine_definitions` |
| Frontends | `getMachineFrontendDefinitions()` | `machine_frontend_definitions` |

If categories in `machine_definitions` differ from categories in `machine_frontend_definitions`, users may see categories in step 2 that have **no matching frontends in step 3**.

**Seed data verification** ([plr-definitions.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/assets/browser-data/plr-definitions.ts)):
- Frontend definitions use categories: `'LiquidHandler' | 'PlateReader' | 'Shaker' | 'Centrifuge' | 'Incubator' | 'Other'`
- Machine definitions use matching categories

**Current status**: Seed data appears consistent, but this could break if definitions are added/modified independently.

### ⚠️ Potential Issue: Client-Side Async Race

The frontend filtering is done client-side after fetching all definitions:

```typescript
this.frontends$ = this.assetService.getMachineFrontendDefinitions().pipe(
    map(frontends => frontends.filter(f => f.machine_category === category))
);
```

If `getMachineFrontendDefinitions()` returns before the DB is ready, or if there's a timing issue, the filter may run on an empty array.

**Mitigation**: The service uses `isReady$.pipe(filter(ready => ready), take(1))` pattern which should prevent this.

---

## Validation Summary

| Component | Logic | Status |
|-----------|-------|--------|
| Type → Categories | `getMachineFacets()` extracts from definitions | ✅ Correct |
| Category → Frontends | Client-side `machine_category` filter | ✅ Correct |
| Frontend → Backends | FK query `findByFrontend(id)` | ✅ Correct |
| Form validation | `[stepControl]` with required validators | ✅ Correct |
| Selection state | `selectedFrontend`, `selectedBackend` signals | ✅ Correct |
| Asset creation | Links `frontend_definition_accession_id` + `backend_definition_accession_id` | ✅ Correct |

---

## Code References

| Component | Path |
|-----------|------|
| Asset Wizard | [asset-wizard.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts) |
| Asset Wizard Template | [asset-wizard.html](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.html) |
| Asset Service | [asset.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/assets/services/asset.service.ts) |
| Async Repositories | [async-repositories.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/db/async-repositories.ts) |
| PLR Definitions (Seed) | [plr-definitions.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/assets/browser-data/plr-definitions.ts) |

---

## Recommendations

1. **Consider unifying category sources** — Either:
   - Derive categories from `MachineFrontendDefinitions` instead of `MachineDefinitions`
   - Or keep both tables' categories in sync via seed data validation

2. **Add empty-state handling** — The template already has `@if ((frontends$ | async)?.length === 0)` which shows "No machine types found" — this is good UX.

3. **E2E test coverage** — The `machine-frontend-backend.spec.ts` test validates this flow.
