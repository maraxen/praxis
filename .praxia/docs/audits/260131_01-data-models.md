# Data Models Audit

## MachineDefinition vs MachineFrontendDefinition

### Key Distinction

| Aspect | `MachineDefinition` | `MachineFrontendDefinition` |
|--------|---------------------|----------------------------|
| **Role** | Legacy catalog entry | 3-tier architecture component |
| **Table** | `machine_definitions` | `machine_frontend_definitions` |
| **Purpose** | Monolithic machine spec | Abstract machine interface |
| **Relationship** | Standalone | Has 1:N relationship with backends |

### Data Model Comparison

```typescript
// LEGACY: MachineDefinition (monolithic)
interface MachineDefinition {
  compatible_backends?: string[];       // ❌ Legacy: backends as strings
  frontend_fqn?: string;                // ❌ Redundant: points to frontend
  is_simulated_frontend?: boolean;      // ❌ Mixed concerns
  available_simulation_backends?: string[];
}

// 3-TIER: MachineFrontendDefinition (clean separation)
interface MachineFrontendDefinition {
  accession_id: string;                 // ✅ Primary key
  fqn: string;                          // ✅ PyLabRobot FQN
  machine_category?: string;            // ✅ Category for filtering
  has_deck?: boolean;                   // ✅ Deck capability
  // Backends linked via MachineBackendDefinition.frontend_definition_accession_id
}
```

### Current Usage

- **Category facets**: Sourced from `MachineDefinitions` (via `getMachineFacets()`)
- **Frontend list**: Sourced from `MachineFrontendDefinitions` (via `getMachineFrontendDefinitions()`)
- **Backend list**: FK query via `getBackendsForFrontend(frontendId)`

### Assessment: ⚠️ Migration Needed

> If categories in both tables drift out of sync, users may see categories with no matching frontends.

### References

| File | Description |
|------|-------------|
| [asset.models.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/assets/models/asset.models.ts) | Type definitions |
