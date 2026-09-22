---
title: 'Investigation: Deck Layout "Coming Soon" Message for Non-Hamilton Decks'
description: 'Found the coming-soon message for non-Hamilton decks intentional: slot-based layout editing was unimplemented'
status: archived
task_id: 260922_debt-1293-docs-migration
---
# Investigation: Deck Layout "Coming Soon" Message for Non-Hamilton Decks

## 1. Executive Summary

This investigation confirms that the "coming soon" message displayed when selecting non-Hamilton (notably Opentrons) decks in the deck simulation dialog is **intentional** and accurately reflects the current development status. The feature "Slot-based layout editing" is indeed unimplemented, and the system correctly identifies these decks to inform the user.

## 2. Findings

### 2.1 Message Location

The "coming soon" message is located in the `DeckSimulationDialogComponent`:

- **File**: `praxis/web-client/src/app/features/run-protocol/components/simulation-config-dialog/deck-simulation-dialog.component.ts`
- **Line Number**: 106
- **Content**: `Slot-based layout editing is coming soon. For now, a standard layout is provided.`

### 2.2 Trigger Condition

The message is displayed conditionally via an `*ngIf="isSlotBased()"` block. The `isSlotBased` property is a computed signal defined as:

```typescript
isSlotBased = computed(() => {
  const type = this.configForm.get('deckType')?.value;
  return type?.includes('OT') || type?.includes('Opentrons');
});
```

- When a deck FQN containing "OT" (e.g., `pylabrobot.resources.opentrons.deck.OTDeck`) or "Opentrons" is selected, this condition evaluates to `true`.
- Hamilton decks (e.g., `pylabrobot.liquid_handling.backends.hamilton.STAR.STARDeck`) do not match this pattern and thus bypass the message, showing the rail-based editing tools instead.

### 2.3 Implementation Status

The "slot-based layout editing" feature is **genuinely missing**.
The current `DeckSimulationDialogComponent` implements a `rail-based` workflow where users add carriers to specific rails. For `slot-based` decks (like the OT-2), a different interaction pattern is required (dragging labware into numbered slots 1-12), which has not yet been built.

The standard layout provided as a fallback is the default deck state defined in `DeckCatalogService.getOTDeckSpec()`.

## 3. Recommendation

- **UI/UX**: The message is accurate and should remain until the slot-based editor is implemented.
- **Code Quality**: The `isSlotBased()` detection logic in `deck-simulation-dialog.component.ts` is somewhat fragile as it relies on string matching (FQNs). A more robust approach would be to check the `layoutType` property from the `DeckDefinitionSpec` object, although the current logic is functional for existing definitions.
- **Priority**: If Opentrons support is a high priority for v0.1-alpha, development for a `SlotBasedPaletteComponent` should be scheduled. Otherwise, the current fallback is acceptable.

## 4. References

- `praxis/web-client/src/app/features/run-protocol/components/simulation-config-dialog/deck-simulation-dialog.component.ts`
- `praxis/web-client/src/app/features/run-protocol/services/deck-catalog.service.ts`
- `praxis/web-client/src/app/features/run-protocol/models/deck-layout.models.ts`
