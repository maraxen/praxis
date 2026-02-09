
## Programmatic Deck Type Detection from PyLabRobot
**Severity:** Medium | **Added:** 2026-02-07 | **Tags:** praxis, deck-catalog, pylabrobot, hardcoded

DeckCatalogService uses hardcoded string-matching to resolve backend FQNs → compatible deck types (`getCompatibleDeckTypes()`) and provides hardcoded deck specifications. This should be replaced with programmatic detection:

1. Parse PyLabRobot's resource hierarchy at build time to discover all `Deck` subclasses and their specs
2. Store deck definitions in the `deck_definition_catalog` SQLite table (schema already exists)
3. Use `backend_definition → deck_definition` FK relationships instead of FQN string matching
4. Currently hardcoded: Hamilton STAR (56-rail), STARLet (32-rail), Vantage (54-rail), Opentrons OTDeck (12-slot), Tecan EVO100 (30-rail), EVO150 (45-rail), EVO200 (69-rail)
5. Missing: Tecan Fluent decks, any future PyLabRobot deck additions

**Ref:** `pylabrobot/resources/hamilton/hamilton_decks.py`, `pylabrobot/resources/tecan/tecan_decks.py`, `pylabrobot/resources/hamilton/vantage_decks.py`, `pylabrobot/resources/opentrons/deck.py`
