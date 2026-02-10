# Dispatch Prompt: Implement Typed Execution Manifest for Pyodide Protocols

## Context
E2E stabilization revealed that bridging wizard state to the Pyodide worker via generated Python strings (in `WizardStateService:serializeToPython`) and type-guessing by parameter name (in `web_bridge.py:resolve_parameters`) is brittle. A specific `TypeError` in `STARLetDeck(name="deck")` is currently breaking 8+ E2E tests.

## Objective
Replace string-based serialization with a **Typed Execution Manifest** (JSON) that the worker "materializes" into a live PLR context.

## Technical Specification

### 1. The Manifest Structure

**Key design principle**: The deck belongs to the LiquidHandler (passed as `LiquidHandler(backend=..., deck=deck)`). Each machine entry owns its deck. This supports multiple machines, each with their own deck configuration.

```typescript
interface ExecutionManifest {
  protocol: { fqn: string; requires_deck: boolean };
  machines: MachineEntry[];        // one per machine parameter the protocol needs
  parameters: ParameterEntry[];    // scalar + resource params
}

interface MachineEntry {
  param_name: string;              // matches the protocol function parameter name (e.g. 'liquid_handler')
  machine_type: string;            // 'LiquidHandler' | 'PlateReader' | 'HeaterShaker' etc.
  backend_fqn: string;            // e.g. 'pylabrobot.liquid_handling.backends.hamilton.STAR'
  port_id?: string;
  is_simulated: boolean;
  deck?: DeckManifest;             // only for machines that use a deck (LiquidHandler)
}

interface DeckManifest {
  fqn: string;                     // e.g. 'pylabrobot.resources.hamilton.STARlet.STARLetDeck'
  layout_type: 'rail-based' | 'slot-based';
  layout: CarrierEntry[] | SlotEntry[];
}

// Rail-based (Hamilton, Tecan): Deck → Carrier → Resource
interface CarrierEntry {
  carrier_fqn: string;
  name: string;
  rails: number;
  children: ResourceEntry[];
}

interface ResourceEntry {
  resource_fqn: string;
  name: string;                    // the name the protocol uses to reference this resource
  slot: number;
}

// Slot-based (Opentrons): Deck → Resource directly
interface SlotEntry {
  resource_fqn: string;
  name: string;
  slot: number;
}

interface ParameterEntry {
  name: string;                    // protocol function param name
  value: any;                      // scalar value OR resource reference name
  type_hint: string;               // from ProtocolDefinition
  fqn?: string;                    // for PLR resource types
  is_deck_resource?: boolean;      // true = resolve from constructed deck by name
}
```

#### Example: Hamilton STARlet — `LiquidHandler` with deck

```json
{
  "protocol": { "fqn": "protocols.serial_dilution", "requires_deck": true },
  "machines": [
    {
      "param_name": "liquid_handler",
      "machine_type": "LiquidHandler",
      "backend_fqn": "pylabrobot.liquid_handling.backends.hamilton.STAR",
      "is_simulated": true,
      "deck": {
        "fqn": "pylabrobot.resources.hamilton.STARlet.STARLetDeck",
        "layout_type": "rail-based",
        "layout": [
          {
            "carrier_fqn": "pylabrobot.resources.hamilton.PLT_CAR_L5AC_A00",
            "name": "plate_carrier_1",
            "rails": 7,
            "children": [
              { "resource_fqn": "pylabrobot.resources.corning.Cor_96_wellplate_360ul_Fb", "name": "source_plate", "slot": 0 },
              { "resource_fqn": "pylabrobot.resources.corning.Cor_96_wellplate_360ul_Fb", "name": "dest_plate", "slot": 1 }
            ]
          },
          {
            "carrier_fqn": "pylabrobot.resources.hamilton.TIP_CAR_480_A00",
            "name": "tip_carrier_1",
            "rails": 1,
            "children": [
              { "resource_fqn": "pylabrobot.resources.hamilton.HTF_L", "name": "tip_rack", "slot": 0 }
            ]
          }
        ]
      }
    }
  ],
  "parameters": [
    { "name": "volume", "value": 50.0, "type_hint": "float" },
    { "name": "source_plate", "value": "source_plate", "type_hint": "Plate", "is_deck_resource": true },
    { "name": "tip_rack", "value": "tip_rack", "type_hint": "TipRack", "is_deck_resource": true }
  ]
}
```

#### Example: PlateReader — no deck

```json
{
  "protocol": { "fqn": "protocols.plate_reader_assay", "requires_deck": false },
  "machines": [
    {
      "param_name": "plate_reader",
      "machine_type": "PlateReader",
      "backend_fqn": "pylabrobot.plate_reading.chatterbox.PlateReaderChatterboxBackend",
      "is_simulated": true
    }
  ],
  "parameters": [
    { "name": "wavelength", "value": 450, "type_hint": "int" }
  ]
}
```

#### Example: Multi-machine protocol

```json
{
  "machines": [
    {
      "param_name": "liquid_handler",
      "machine_type": "LiquidHandler",
      "backend_fqn": "pylabrobot.liquid_handling.backends.hamilton.STAR",
      "is_simulated": true,
      "deck": { "fqn": "pylabrobot.resources.hamilton.STARlet.STARLetDeck", "layout_type": "rail-based", "layout": [...] }
    },
    {
      "param_name": "plate_reader",
      "machine_type": "PlateReader",
      "backend_fqn": "pylabrobot.plate_reading.chatterbox.PlateReaderChatterboxBackend",
      "is_simulated": true
    }
  ]
}
```

### 2. Data Sources

| Manifest Field | Source in Angular |
|---|---|
| `machines[].param_name` | `ProtocolDefinition.assets[].name` where `type_hint_str` matches a machine type |
| `machines[].machine_type` | `ProtocolDefinition.assets[].type_hint_str` (e.g. `'LiquidHandler'`) |
| `machines[].backend_fqn` | Machine selection in `RunProtocolComponent` |
| `machines[].deck.fqn` | `DeckCatalogService.getDeckTypeForMachine(selectedMachine)` |
| `machines[].deck.layout_type` | `DeckCatalogService.getDeckDefinition(fqn).layoutType` |
| `machines[].deck.layout` | `WizardStateService._carrierRequirements()` + `_slotAssignments()` |
| `parameters[].type_hint` | `ProtocolDefinition.parameters[].type_hint` |
| `parameters[].fqn` | `ProtocolDefinition.parameters[].fqn` or `assets[].fqn` |

### 3. Changes in `wizard-state.service.ts`
- **Replace** `serializeToPython()` with `buildExecutionManifest(): ExecutionManifest`
- Build `machines[].deck.layout` from `_carrierRequirements()` + `_slotAssignments()`
- Use `DeckCatalogService.getDeckDefinition(fqn).layoutType` for `layout_type`

### 4. Changes in `execution.service.ts`
- Call `wizardState.buildExecutionManifest()` instead of `serializeToPython()`
- Pass manifest JSON to `pythonRuntime.executeBlob()` via a `manifest` payload field

### 5. Changes in `python.worker.ts` & `web_bridge.py`
- **Worker**: Pass manifest dict to `web_bridge.materialize_context(manifest)`
- **`materialize_context(manifest)`**:
  1. For each machine in `machines`:
     - If machine has `deck`:
       - Import deck factory from `deck.fqn`, call with NO `name` kwarg
       - Populate deck from `layout` (carriers → resources or slots → resources)
     - Import backend from `backend_fqn`, instantiate
     - Create machine: e.g. `LiquidHandler(backend=backend, deck=deck)`
     - Store in `kwargs[param_name]`
  2. Resolve `parameters`:
     - If `is_deck_resource`: find the named resource on the constructed deck
     - If scalar: pass value directly
     - If resource but not on deck: instantiate standalone from `fqn`
  3. Return `kwargs` for `protocol_func(**kwargs)`

### 6. Hamilton Deck Signature
`STARLetDeck` factory in `external/pylabrobot/.../hamilton_decks.py` accepts: `(origin, with_trash, with_trash96, with_teaching_rack, core_grippers)`. **NO `name` kwarg.**

## Verification
```bash
npx playwright test e2e/specs/interactions/ --reporter=line --workers=1
```
Must verify: `IndexError` and `TypeError` no longer appear in Pyodide logs.
