# Serialization Audit

## Deck State → Python

### serializeToPython() Function

[wizard-state.service.ts:397-479](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/run-protocol/services/wizard-state.service.ts#L397-479)

**Generated Python:**

```python
import pylabrobot.resources as res
from pylabrobot.resources.hamilton import HamiltonSTARDeck, *

def setup_deck():
    deck = HamiltonSTARDeck()
    plt_carrier_1 = PLT_CAR_L5AC_A00(name="Carrier A")
    deck.assign_child_resource(plt_carrier_1, rails=3)
    labware_0 = res.Plate(name="source_plate", size_x=127.0, size_y=85.0, size_z=14.5)
    plt_carrier_1[0] = labware_0
    return deck

deck = setup_deck()
```

**Assessment**: ⚠️ Class name inference is heuristic (`fqn.split('.').pop()?.toUpperCase()`)

---

## WellSelector

[well-selector-dialog.component.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/shared/components/well-selector-dialog/well-selector-dialog.component.ts)

**Data Flow:**

```
WellSelectorDialogData → WellSelectorDialogResult
─────────────────────    ────────────────────────
plateType: '96'|'384'    wells: string[]  (e.g., ["A1", "B2"])
mode: 'single'|'multi'   confirmed: boolean
```

**Assessment**: ✅ Clear typed interfaces, persisted in signal state

---

## IndexSelector

[index-selector.component.ts:26-35](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/shared/components/index-selector/index-selector.component.ts#L26-35)

```typescript
export interface ItemizedResourceSpec {
  itemsX: number;  // Columns
  itemsY: number;  // Rows
  label?: string;
  linkId?: string; // For synchronized selection
}

// Dual output
@Output() selectionChange = new EventEmitter<number[]>();  // Flat indices
@Output() wellIdsChange = new EventEmitter<string[]>();    // ["A1", "B2"]
```

**Assessment**: ✅ Generalizes to any grid, supports linked selection

---

## Backend Arguments

```typescript
// execution.service.ts:235-242
machineConfig = {
  backend_fqn: definition.fqn,
  port_id: instance?.backend_config?.port_id,
  baudrate: instance?.backend_config?.baudrate,
  is_simulated: definition.is_simulation_override || false
};
```

**Assessment**: ✅ Config flows through cleanly to web_bridge.py
