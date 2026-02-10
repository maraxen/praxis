# Audit Task: Identify and Eliminate Brittle/Hardcoded Logic

## Objective
The discovery of the `STARLetDeck(name="deck")` bug (which caused `TypeError`) highlight a systemic risk: hardcoded strings and brittle internal assumptions. Conduct a deep audit of the protocol execution and serialization layer to replace "magic strings" and "name-guessing" with typed, metadata-driven logic.

## Audit Targets

### 1. Brittle String Matching (The "Hamilton Problem")
Find logic that branches based on string contents instead of typed enums or FQNs.
- **File**: `wizard-state.service.ts`
- **Pattern**: `deckType.includes('HamiltonSTAR')`, `OTDeck`, etc.
- **Fix**: Replace with `DeckCatalogService.getDeckDefinition(fqn).layoutType` or similar typed checks.

### 2. Name-Guessing in Worker
Find where parameters are resolved by name-string contents.
- **File**: `python.worker.ts`, `web_bridge.py`
- **Pattern**: `if 'plate' in param_name.lower()`, `if 'tip' in param_name.lower()`.
- **Fix**: Use the provided `type_hint` from the protocol definition.

### 3. Invalid Factory Signatures
Ensure no other PLR resources are being instantiated with invalid hardcoded keyword arguments.
- **Target**: Calls to `Plate()`, `TipRack()`, `HeaterShaker()`, etc.
- **Audit Tool**: `ast-grep --pattern 'new $NAME(name: $VAL)'` or similar to find TS-side object creation that might be echoed into Python.

### 4. Over-Broad `try/except` Blocks
Find blocks that swallow initialization errors, leading to "empty deck" fallbacks that cause `IndexError` later.
- **File**: `python.worker.ts`
- **Pattern**: `except Exception as e: print(e); deck = create_browser_deck()`.
- **Fix**: Re-throw critical initialization errors OR fail fast if the deck is mandatory.

## Deliverables
1. **Critical Bug Fixes**: Immediate removal of any other discovered invalid signatures (like the `name` kwarg for `STARLetDeck`).
2. **Hardening PR**: Refactor of `WizardStateService` and `web_bridge.py` to use a unified `ExecutionManifest`.
