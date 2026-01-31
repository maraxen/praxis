# Protocol Execution Audit

## Parameter Resolution

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
│    4. is_resource = contains("plate"|"tiprack"|"resource")         │
│    5. If is_resource:                                              │
│       a. If value is dict → extract fqn, instantiate by heuristic │
│       b. If value is UUID → lookup in asset_specs                  │
│          - Use num_items to infer geometry (96→12x8, 384→24x16)   │
│       c. Fallback → create generic resource                        │
│    6. Else → pass through unchanged                                │
└────────────────────────────────────────────────────────────────────┘
```

### Assessment: ⚠️ Heuristic-Based

**Strengths:**
- Handles both dict and UUID value formats
- Uses asset_specs for metadata when available

**Concerns:**
- Type matching is string-based (`"plate" in effective_type`)
- Fallback creates generic resources that may not match protocol expectations

---

## Run State Machine

### Protocol Run Status Enum

13 states covering full lifecycle:

```
┌────────────────────────────────────────────────────────────────┐
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
└────────────────────────────────────────────────────────────────┘
```

### Assessment: ✅ Comprehensive

---

## Browser Execution Flow

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
│  7. Update DB: protocolRuns.update(runId, { status })           │
└────────────────────────────────────────────────────────────────┘
```

### Output Message Types

| Type | Handler |
|------|---------|
| `stdout` | Logged to UI |
| `stderr` | Logged as error, sets hasError flag |
| `well_state_update` | Updates run wellState for visualization |
| `function_call_log` | Records function call for timeline |

### Assessment: ✅ Full lifecycle handling + 46 E2E specs
