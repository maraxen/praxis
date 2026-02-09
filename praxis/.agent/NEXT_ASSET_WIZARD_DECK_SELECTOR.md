# Asset Wizard: Deck Selection Step

> **Priority:** Must be done BEFORE debugging remaining E2E tests (post Wave 0.5)
> **Status:** Not started

## Problem

When instantiating a **Liquid Handler** machine via the Asset Wizard, users currently cannot select which compatible deck to use. If multiple deck options exist, the wizard should present a selection step.

## Requirements

1. **New wizard step: Deck Selection** — inserted after Driver (Backend) and before Config
   - Flow: Type → Category → Machine Type → Driver → **Deck** → Config → Review
2. **Liquid Handler only** — this step only appears for the `LiquidHandler` category; other machine categories skip it entirely
3. **Auto-skip on single option** — if only one compatible deck exists, auto-select it and skip the step (same pattern as Type auto-skip when using "Add Machine" button)
4. **Reference implementation** — the Run Protocol wizard flow already has deck selection logic in `wizard.page.ts` / `run-step-deck`; use that as the model for how compatible decks are resolved and presented

## Research Needed

- [ ] Where does deck compatibility data live? (machine definition → compatible decks mapping)
- [ ] How does the Run Protocol flow resolve compatible decks for a selected machine?
- [ ] What component renders deck options in the Run Protocol wizard?
- [ ] What changes are needed in the Asset Wizard stepper component?

## Test Impact

- `createMachine()` in `assets.page.ts` needs a deck selection step for LiquidHandler flows
- `asset-inventory.spec.ts` persistence test calls `createMachine('LiquidHandler')` — will need updating
- New E2E test coverage for: multi-deck selection, single-deck auto-skip, non-LiquidHandler bypass

## Context

Identified during E2E stabilization Wave 0.5 (conversation `e12b9431`). The `asset-inventory` test was already failing pre-changes; this feature gap is likely a contributing factor.
