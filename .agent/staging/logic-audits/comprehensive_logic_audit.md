# Comprehensive Logic Audit Report

> **Date**: 2026-01-31  
> **Scope**: Asset Wizard, Protocol Execution, Deck Setup, Run State Machine, Asset Constraints

---

## Table of Contents

1. [MachineDefinition vs MachineFrontendDefinition](#machinedefinition-vs-machinefrontenddefinition)
2. [Asset Wizard: Resource Definition Chain](#asset-wizard-resource-definition-chain)
3. [Protocol Parameter Resolution](#protocol-parameter-resolution)
4. [Deck Setup Script Generation](#deck-setup-script-generation)
5. [Run State Machine](#run-state-machine)
6. [Asset Constraint Matching](#asset-constraint-matching)

---

## MachineDefinition vs MachineFrontendDefinition

### Key Distinction

| Aspect | `MachineDefinition` | `MachineFrontendDefinition` |
|--------|---------------------|------------------------------|
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

> ⚠️ **Potential Issue**: If categories in both tables drift out of sync, users may see categories with no matching frontends.

---

## Asset Wizard: Resource Definition Chain

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

### Key Code ([asset-wizard.ts:203-213](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts#L203-213))

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

---

## Protocol Parameter Resolution

### Location

[web_bridge.py:24-108](file:///Users/mar/Projects/praxis/praxis/web-client/src/assets/python/web_bridge.py#L24-108)

### Logic Flow

```
┌────────────────────────────────────────────────────────────────────┐
│  resolve_parameters(params, metadata, asset_reqs, asset_specs)     │
├────────────────────────────────────────────────────────────────────┤
│  For each param:                                                   │
│    1. Get type_hint from metadata                                  │
│    2. Get asset_type from asset_reqs                               │
│    3. effective_type = type_hint || asset_type                     │
│    4. is_resource = contains("plate"|"tiprack"|"resource"|"container") │
│    5. If is_resource:                                              │
│       a. If value is dict → extract fqn, instantiate by heuristic │
│       b. If value is UUID → lookup in asset_specs                  │
│          - Use num_items to infer geometry (96→12x8, 384→24x16)   │
│          - Create Plate/TipRack/Container with computed dims       │
│       c. Fallback → create generic resource                        │
│    6. Else → pass through unchanged                                │
└────────────────────────────────────────────────────────────────────┘
```

### Assessment: ⚠️ Heuristic-Based

**Strengths:**
- Handles both dict and UUID value formats
- Uses asset_specs for metadata when available
- Reasonable geometry inference (96-well → 12x8)

**Concerns:**
- Type matching is string-based (`"plate" in effective_type`)
- Fallback creates generic resources that may not match protocol expectations
- No validation that instantiated resource matches protocol requirements

---

## Deck Setup Script Generation

### Flow

Deck setup scripts are passed from `python-runtime.service.ts` to `python.worker.ts`:

```
PythonRuntimeService.executeProtocolBlob()
    ↓
postMessage({ type: 'execute_blob', payload: { deck_setup_script, ... }})
    ↓
python.worker.ts: exec(js.deck_setup_script, setup_ns)
```

### Key Code ([python.worker.ts:239-243](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/workers/python.worker.ts#L239-243))

```python
if js.deck_setup_script:
    setup_ns = {'lh': lh, 'deck': lh.deck}
    exec(js.deck_setup_script, setup_ns)
```

### Assessment: ✅ Straightforward

- Script executed in isolated namespace (`setup_ns`)
- Has access to `lh` (LiquidHandler) and `deck` objects
- Allows arbitrary resource placement

---

## Run State Machine

### Protocol Run Status Enum

13 states covering full lifecycle ([enums.ts:209-238](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/db/enums.ts#L209-238)):

```
┌────────────────────────────────────────────────────────────────┐
│                    Protocol Run State Machine                  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  queued ──→ pending ──→ preparing ──→ running                  │
│                                           │                    │
│                                     ┌─────┼─────┐              │
│                                     ↓     ↓     ↓              │
│                               pausing  canceling  intervention │
│                                     ↓     ↓         │          │
│                                  paused cancelled   │          │
│                                     ↓               ↓          │
│                                 resuming   requires_intervention│
│                                     ↓                          │
│                                  running ──→ completed         │
│                                     │                          │
│                                     └──→ failed                │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### States

| Status | Description |
|--------|-------------|
| `queued` | Waiting in queue |
| `pending` | Awaiting resources |
| `preparing` | Setting up execution environment |
| `running` | Actively executing |
| `pausing` | Transition to paused |
| `paused` | User paused |
| `resuming` | Transition from paused |
| `completed` | Successfully finished |
| `failed` | Error occurred |
| `canceling` | User cancellation in progress |
| `cancelled` | User cancelled |
| `intervening` | Handling intervention |
| `requires_intervention` | Waiting for user action |

### Assessment: ✅ Comprehensive

- Covers all lifecycle stages
- Includes transition states (pausing, resuming, canceling)
- Supports intervention workflow

---

## Asset Constraint Matching

### Deck Drop Validation

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

---

## Summary of Findings

| Area | Status | Notes |
|------|--------|-------|
| MachineDefinition vs Frontend | ⚠️ | Legacy vs 3-tier coexistence |
| Resource Wizard Chain | ✅ | Sound reactive design |
| Parameter Resolution | ⚠️ | Heuristic-based, may create fallbacks |
| Deck Setup Script | ✅ | Straightforward exec() |
| Run State Machine | ✅ | 13 comprehensive states |
| Deck Constraint Validation | ✅ | Limited but sound |

---

## References

| Component | Path |
|-----------|------|
| Asset Models | [asset.models.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/assets/models/asset.models.ts) |
| Asset Wizard | [asset-wizard.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/shared/components/asset-wizard/asset-wizard.ts) |
| Web Bridge | [web_bridge.py](file:///Users/mar/Projects/praxis/praxis/web-client/src/assets/python/web_bridge.py) |
| Python Worker | [python.worker.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/workers/python.worker.ts) |
| Enums | [enums.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/db/enums.ts) |
| Deck Constraints | [deck-constraint.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/run-protocol/services/deck-constraint.service.ts) |

---

## GitHub Pages Implementation Pathing

### baseHref Calculation Patterns

Found **3 different implementations** across the codebase:

| Location | Pattern | Notes |
|----------|---------|-------|
| `asset.service.ts:545` | `baseHref.endsWith('/') ? baseHref : baseHref + '/'` | Ensures trailing slash |
| `playground-jupyterlite.service.ts:363` | `baseHref.startsWith('/') ? baseHref : '/' + baseHref` | Ensures leading slash only |
| `playground.component.ts:893-894` | Same as above | Duplicate of jupyterlite service |

### calculateHostRoot Logic

[playground-jupyterlite.service.ts:354-367](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/playground/services/playground-jupyterlite.service.ts#L354-367)

```typescript
private calculateHostRoot(): string {
  const href = window.location.href;
  const anchor = '/assets/jupyterlite/';

  // If already in jupyterlite iframe, extract parent origin
  if (href.includes(anchor)) {
    return href.split(anchor)[0] + '/';
  }

  // Otherwise compute from <base> tag
  const baseHref = document.querySelector('base')?.getAttribute('href') || '/';
  const cleanBase = baseHref.startsWith('/') ? baseHref : '/' + baseHref;
  const finalBase = cleanBase.endsWith('/') ? cleanBase : cleanBase + '/';

  return window.location.origin + finalBase;
}
```

### Assessment: ⚠️ Inconsistent Patterns

**Issue**: Three different slash normalization approaches could lead to edge-case failures:
- `asset.service.ts` only ensures trailing slash
- `jupyterlite.service.ts` only ensures leading slash
- `calculateHostRoot` ensures both

**Recommendation**: Unify into a single `PathUtils.normalizeBaseHref()` helper.

---

## JupyterLite Loading and Environment Setup

### Bootstrap Architecture: 2-Phase BroadcastChannel

```
┌─────────────────────────────────────────────────────────────────┐
│                    JupyterLite Bootstrap Flow                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: Minimal Bootstrap (via URL ?code= param)              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. Import js, pyodide.ffi                                 │  │
│  │ 2. Create BroadcastChannel("praxis_repl")                 │  │
│  │ 3. Set onmessage handler for "praxis:bootstrap"           │  │
│  │ 4. Send "praxis:boot_ready" → Angular                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  Phase 2: Full Bootstrap (via BroadcastChannel)                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. Angular receives boot_ready                            │  │
│  │ 2. Angular sends "praxis:bootstrap" + full code           │  │
│  │ 3. exec(code) runs getOptimizedBootstrap()                │  │
│  │    → Install pylabrobot wheel                             │  │
│  │    → Load shims (web_serial, web_usb, web_ftdi)           │  │
│  │    → Patch pylabrobot.io                                  │  │
│  │    → Setup message handlers                               │  │
│  │ 4. Send "praxis:ready" → Angular                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Code Locations

| Component | File | Lines |
|-----------|------|-------|
| Minimal Bootstrap | [playground-jupyterlite.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/playground/services/playground-jupyterlite.service.ts#L95-120) | 95-120 |
| Ready Listener | [playground-jupyterlite.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/playground/services/playground-jupyterlite.service.ts#L51-70) | 51-70 |
| Full Bootstrap | [playground-jupyterlite.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/playground/services/playground-jupyterlite.service.ts#L173-351) | 173-351 |

### Shim Loading Order

```
1. web_serial_shim.py → builtins.WebSerial
2. web_usb_shim.py → builtins.WebUSB
3. web_ftdi_shim.py → builtins.WebFTDI
4. web_bridge.py → written to virtual FS
5. Patch pylabrobot.io.serial.Serial = WebSerial
6. Patch pylabrobot.io.usb.USB = WebUSB
7. Patch pylabrobot.io.ftdi.FTDI = WebFTDI
```

### Assessment: ✅ Sound but Complex

**Strengths:**
- 2-phase approach avoids URL length limits
- BroadcastChannel works across iframe boundary
- 30-second timeout with fallback

**Concerns:**
- Complex error paths if BroadcastChannel fails
- No retry mechanism for failed shim loads

---

## Hardware Discovery and Instantiation

### Architecture Overview

[hardware-discovery.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/services/hardware-discovery.service.ts)

```
┌─────────────────────────────────────────────────────────────────┐
│                  Hardware Discovery Flow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Discovery Methods:                                             │
│  1. requestSerialPort() → User picks from browser dialog        │
│  2. requestUsbDevice() → User picks from browser dialog         │
│  3. discoverAll() → Combine authorized ports + backend API      │
│                                                                 │
│  Device Identification:                                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. Get VID/PID from port.getInfo() or USBDevice           │  │
│  │ 2. Format key: "0xVVVV:0xPPPP"                             │  │
│  │ 3. Lookup in KNOWN_DEVICES table                          │  │
│  │ 4. inferBackendDefinition() → PLR_BACKEND_DEFINITIONS     │  │
│  │ 5. Link to MachineFrontendDefinition via accession_id     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Connection Lifecycle:                                          │
│  available → connecting → connected → busy → disconnected       │
│      ↓                                                          │
│  requires_config (if configSchema exists)                       │
│      ↓                                                          │
│  error (on failure)                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Known Device Table

| VID:PID | Manufacturer | Model | PLR Backend |
|---------|--------------|-------|-------------|
| `0x08BB:0x0106` | Hamilton | STAR | hamilton.STAR |
| `0x08BB:0x0107` | Hamilton | Starlet | hamilton.Starlet |
| `0x04D8:0xE11A` | Opentrons | OT-2 | opentrons.OT2 |
| `0x0856:0xAC11` | Hamilton | via B&B Adapter | hamilton.STAR |
| `0x0403:0xBB68` | BMG LABTECH | CLARIOstar | clario_star_backend |
| `0x08AF:0x8000` | Hamilton | via MCT Adapter | hamilton.STAR |
| `0x1A86:0x7523` | Generic | CH340 | (none) |
| `0x0403:0x6001` | FTDI | FT232 | (none) |
| `0x067B:0x2303` | Prolific | PL2303 | (none) |

### Device Status Values

| Status | Description |
|--------|-------------|
| `available` | Ready to connect |
| `connected` | Active connection |
| `connecting` | Connection in progress |
| `disconnected` | Connection closed |
| `busy` | In use by another process |
| `error` | Connection failed |
| `requires_config` | Needs configuration before use |
| `unknown` | State undetermined |

### Low-Level I/O API

For WebBridgeIO integration:

```typescript
// Open port and get stream handles
await openPort(portId, { baudRate: 9600 });

// Write raw bytes
await writeToPort(portId, new Uint8Array([0x01, 0x02]));

// Read bytes (returns Uint8Array)
const data = await readFromPort(portId, 10);

// Close and release
await closePort(portId);
```

### Assessment: ✅ Well-Structured

**Strengths:**
- Reactive signals for device state
- VID/PID → PLR backend mapping is extensible
- Parallel discovery (browser APIs + backend)
- Proper stream reader/writer lifecycle management

**Concerns:**
- Static KNOWN_DEVICES table requires manual updates
- No auto-detection for devices not in table

---

## Updated Summary

| Area | Status | Notes |
|------|--------|-------|
| MachineDefinition vs Frontend | ⚠️ | Legacy vs 3-tier coexistence |
| Resource Wizard Chain | ✅ | Sound reactive design |
| Parameter Resolution | ⚠️ | Heuristic-based, may create fallbacks |
| Deck Setup Script | ✅ | Straightforward exec() |
| Run State Machine | ✅ | 13 comprehensive states |
| Deck Constraint Validation | ✅ | Limited but sound |
| **GitHub Pages Pathing** | ⚠️ | **3 inconsistent baseHref patterns** |
| **JupyterLite Bootstrap** | ✅ | **2-phase BroadcastChannel** |
| **Hardware Discovery** | ✅ | **VID/PID lookup + reactive state** |

---

## Additional References

| Component | Path |
|-----------|------|
| JupyterLite Service | [playground-jupyterlite.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/playground/services/playground-jupyterlite.service.ts) |
| Hardware Discovery | [hardware-discovery.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/services/hardware-discovery.service.ts) |
| Direct Control Kernel | [direct-control-kernel.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/playground/services/direct-control-kernel.service.ts) |
| PLR Definitions | [plr-definitions.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/assets/browser-data/plr-definitions.ts) |

---

## Extended Audit: VID/PID Lookup Completeness

### Comparison: KNOWN_DEVICES vs PLR_BACKEND_DEFINITIONS

| Metric | Count |
|--------|-------|
| `KNOWN_DEVICES` entries | **9** |
| `PLR_BACKEND_DEFINITIONS` entries | **33** |
| Coverage gap | **~73%** of backends have no VID/PID mapping |

### KNOWN_DEVICES Table (9 entries)

| VID:PID | Device | Has PLR Backend |
|---------|--------|-----------------|
| `0x08BB:0x0106` | Hamilton STAR | ✅ hamilton.STAR |
| `0x08BB:0x0107` | Hamilton Starlet | ✅ hamilton.Starlet |
| `0x04D8:0xE11A` | Opentrons OT-2 | ✅ opentrons.OT2 |
| `0x0856:0xAC11` | Hamilton via B&B | ✅ hamilton.STAR |
| `0x0403:0xBB68` | BMG CLARIOstar | ✅ clario_star_backend |
| `0x08AF:0x8000` | Hamilton via MCT | ✅ hamilton.STAR |
| `0x1A86:0x7523` | Generic CH340 | ❌ none |
| `0x0403:0x6001` | FTDI FT232 | ❌ none |
| `0x067B:0x2303` | Prolific PL2303 | ❌ none |

### Assessment: ⚠️ Significant Gap

The VID/PID table covers **only 5 unique PLR backends** out of 33 total. Missing backends include:
- Tecan backends (EVO, Freedom)
- Inheco backends (various heaters/shakers)
- Agilent backends
- Many plate readers and specialized equipment

**Recommendation**: Consider auto-discovery from PLR package or backend API fallback.

---

## Extended Audit: Deck State Serialization

### serializeToPython() Function

[wizard-state.service.ts:397-479](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/run-protocol/services/wizard-state.service.ts#L397-479)

### Generated Python Structure

```python
import pylabrobot.resources as res
from pylabrobot.resources.hamilton import HamiltonSTARDeck, *

def setup_deck():
    deck = HamiltonSTARDeck()
    
    # Carriers (from uniqueCarriers)
    plt_carrier_1 = PLT_CAR_L5AC_A00(name="Carrier A")
    deck.assign_child_resource(plt_carrier_1, rails=3)
    
    # Labware (from slotAssignments)
    labware_0 = res.Plate(name="source_plate", size_x=127.0, size_y=85.0, size_z=14.5)
    plt_carrier_1[0] = labware_0
    
    return deck

deck = setup_deck()
```

### Supported Deck Types

| Deck Type | Import | Instantiation |
|-----------|--------|---------------|
| HamiltonSTAR* | `from pylabrobot.resources.hamilton import HamiltonSTARDeck` | `HamiltonSTARDeck()` |
| OTDeck | `from pylabrobot.resources.opentrons import OTDeck` | `OTDeck()` |
| (other) | — | `res.Deck()` |

### Assessment: ✅ Functional but Heuristic

**Strengths:**
- Generates valid Python for common deck types
- Tracks unique carriers to avoid duplication
- Supports both carrier-based (Hamilton) and slot-based (OT-2) layouts

**Concerns:**
- Class name inference is heuristic: `carrier.fqn.split('.').pop()?.toUpperCase()`
- Resource type → PLR class mapping is limited (Plate, TipRack, Resource)
- No validation that generated FQNs match actual PLR classes

---

## Extended Audit: WellSelector Serialization

### WellSelectorDialogComponent

[well-selector-dialog.component.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/shared/components/well-selector-dialog/well-selector-dialog.component.ts)

### Data Flow

```
WellSelectorDialogData                   WellSelectorDialogResult
────────────────────────                 ────────────────────────
plateType: '96' | '384'                  wells: string[]
initialSelection: string[]         →     confirmed: boolean
mode: 'single' | 'multi'
title?: string
plateLabel?: string
```

### Integration with run-protocol.component.ts

```typescript
// run-protocol.component.ts:1446-1469
openWellSelector(param: any) {
  // ...
  this.dialog.open(WellSelectorDialogComponent, { data: dialogData })
    .afterClosed().subscribe((result: WellSelectorDialogResult) => {
      if (result?.confirmed) {
        this.wellSelections.update(s => ({ ...s, [param.name]: result.wells }));
      }
    });
}
```

### Serialization Format

Well selections are stored as **string arrays** (e.g., `["A1", "A2", "B1"]`) in the `wellSelections` signal, keyed by parameter name.

### Assessment: ✅ Sound

- Clear data contract with typed interfaces
- Selection persisted in component signal state
- Auto-detects plate type from configured assets

---

## Extended Audit: IndexSelector Generalization

### ItemizedResourceSpec Interface

[index-selector.component.ts:26-35](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/shared/components/index-selector/index-selector.component.ts#L26-35)

```typescript
export interface ItemizedResourceSpec {
  /** Number of columns (e.g., 12 for 96-well plate) */
  itemsX: number;
  /** Number of rows (e.g., 8 for 96-well plate) */
  itemsY: number;
  /** Optional label for the resource */
  label?: string;
  /** Optional ID to link with other selectors */
  linkId?: string;
}
```

### Dual Output Format

```typescript
@Output() selectionChange = new EventEmitter<number[]>();   // Flat indices
@Output() wellIdsChange = new EventEmitter<string[]>();     // e.g., ["A1", "B2"]
```

### LinkedSelectorService

Enables **synchronized selection** across multiple IndexSelector instances via `linkId`:

```typescript
if (this.spec.linkId) {
  this.linkedSelectorService.registerSelector(this.spec.linkId, this.instanceId);
  this.linkSubscription = this.linkedSelectorService
    .getSelection$(this.spec.linkId, this.instanceId)
    .subscribe(indices => {
      this.selectedIndices = indices;
      this.syncGridFromIndices();
    });
}
```

### Assessment: ✅ Well-Generalized

- Works for any grid dimensions (not just 96/384-well)
- Supports up to 26² rows via `indexToRowLabel()` extension
- Linked selection allows source/destination plate pairing
- Formly integration via `IndexSelectorFieldComponent`

---

## Extended Audit: Protocol Run-to-Completion

### Browser Execution Flow

[execution.service.ts:206-316](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/run-protocol/services/execution.service.ts#L206-316)

```
┌────────────────────────────────────────────────────────────────┐
│            executeBrowserProtocol() Flow                        │
├────────────────────────────────────────────────────────────────┤
│  1. setStatus(RUNNING)                                          │
│  2. getProtocolRun(runId) → extract resolved_assets_json        │
│  3. Build machineConfig: { backend_fqn, port_id, baudrate }     │
│  4. fetchProtocolBlob(protocolId)                               │
│  5. wizardState.serializeToPython() → deckSetupScript           │
│  6. pythonRuntime.executeBlob(blob, runId, machineConfig, deck) │
│     ├── stdout → addLog()                                       │
│     ├── stderr → addLog() + hasError = true                     │
│     ├── well_state_update → _currentRun.set()                   │
│     ├── function_call_log → handleFunctionCallLog()             │
│     └── complete → setStatus(COMPLETED) or reject               │
│  7. Update DB: protocolRuns.update(runId, { status })           │
└────────────────────────────────────────────────────────────────┘
```

### Output Message Types

| Type | Handler |
|------|---------|
| `stdout` | Logged to UI |
| `stderr` | Logged as error, sets hasError flag |
| `result` | Logged as result |
| `well_state_update` | Updates run wellState for visualization |
| `function_call_log` | Records function call for timeline |

### E2E Test Coverage

**46 E2E spec files** found in `/praxis/web-client/e2e/`, including:
- `execution-browser.spec.ts` - Browser execution scenarios
- `protocol-execution.spec.ts` - Protocol execution flow
- `deck-setup.spec.ts` - Deck setup wizard
- `jupyterlite-bootstrap.spec.ts` - JupyterLite initialization
- `jupyterlite-paths.spec.ts` - Path resolution

### Assessment: ✅ Comprehensive

- Full lifecycle handling from preparation to completion
- Multiple output channels for different data types
- Good E2E coverage for browser mode scenarios

---

## Extended Audit: Backend Argument Serialization

### Machine Config Flow

```typescript
// execution.service.ts:235-242
machineConfig = {
  backend_fqn: definition.fqn,
  port_id: instance?.backend_config?.port_id,
  baudrate: instance?.backend_config?.baudrate,
  is_simulated: definition.is_simulation_override || false
};
```

### Storage in Machine Instances

`backend_config` is stored as a JSON object in `MachineInstance`:

```typescript
// MachineCreate.ts
backend_config?: (Record<string, any> | null);

// Example values:
{
  "port_id": "adc98e2f-...",
  "baudrate": 9600
}
```

### Assessment: ✅ Straightforward

- Config passed through cleanly to web_bridge.py
- Port ID maps to HardwareDiscoveryService device
- Baudrate and other params flow through unchanged

---

## Updated Summary

| Area | Status | Key Finding |
|------|--------|-------------|
| VID/PID Completeness | ⚠️ | 9 entries vs 33 backends (~73% gap) |
| JupyterLite Coverage | ✅ | 15 simulated frontends, ChatterboxBackend universal |
| Protocol Run-to-Completion | ✅ | Full lifecycle + 46 E2E specs |
| Deck State Serialization | ✅ | serializeToPython() works for Hamilton/OT-2 |
| Backend Arg Serialization | ✅ | port_id + baudrate passthrough |
| WellSelector | ✅ | string[] well IDs in signal state |
| IndexSelector | ✅ | ItemizedResourceSpec generalizes to any grid |

---

## Recommendations

### High Priority

1. **VID/PID Table Expansion**: Add missing device mappings or implement auto-discovery fallback via backend API

2. **baseHref Unification**: Create `PathUtils.normalizeBaseHref()` to consolidate 3 different patterns

### Medium Priority

3. **Deck Serialization Validation**: Add runtime check that generated FQNs match actual PLR classes

4. **Bootstrap Retry Logic**: Add retry mechanism for failed shim loads in JupyterLite

### Low Priority

5. **KNOWN_DEVICES Auto-Sync**: Consider generating VID/PID table from PLR package metadata

