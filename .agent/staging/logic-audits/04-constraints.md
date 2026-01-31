# Constraint Validation Audit

## Deck Drop Validation

[deck-constraint.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/run-protocol/services/deck-constraint.service.ts)

### Logic

```typescript
validateDrop(resource, target, rootDeck): ValidationResult {
  if (isRail(target)) {
    // Rails: Only Carriers allowed
    // Check compatibleCarrierTypes if defined
  } else {
    // Slots: Check slot type restrictions
    // Check dimension fit (with 1mm tolerance)
  }
}
```

### Validation Rules

| Target | Rule |
|--------|------|
| **Rail** | Only `Carrier` types allowed |
| **Rail** | Must match `compatibleCarrierTypes` if defined |
| **Slot (Trash)** | Only trash containers allowed |
| **Slot** | Resource dimensions must fit slot dimensions |

### Assessment: ✅ Sound but Limited

**Strengths:**
- Clear type checking for rails
- Dimension validation with tolerance
- Returns structured ValidationResult

**Limitations:**
- No constraint matching for protocol asset requirements vs inventory
- Carrier compatibility is string-based matching
