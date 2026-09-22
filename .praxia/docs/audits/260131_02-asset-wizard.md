# Asset Wizard Audit

## Resource Definition Chain

### Subscription Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  combineLatest([assetType$, category$, query$])                 │
│      ↓                                                          │
│  switchMap → if RESOURCE → searchResourceDefinitions(q, cat)    │
│      ↓                                                          │
│  searchResults$ → template renders definition cards             │
└─────────────────────────────────────────────────────────────────┘
```

### Key Code

[asset-wizard.ts:203-213](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts#L203-213)

```typescript
this.searchResults$ = combineLatest([assetType$, category$, query$]).pipe(
  switchMap(([assetType, category, query]) => {
    if (!assetType || assetType !== 'RESOURCE') return of([]);
    return this.assetService.searchResourceDefinitions(query, category);
  })
);
```

### Assessment: ✅ Sound

- Uses `startWith` to emit initial values
- Uses `debounceTime(300)` on search query
- Uses `distinctUntilChanged()` to prevent duplicate requests
- Uses `switchMap` to cancel in-flight requests

### References

| File | Description |
|------|-------------|
| [asset-wizard.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts) | Main wizard component |
