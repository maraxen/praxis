# JupyterLite Bootstrap Audit

## 2-Phase BroadcastChannel Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    JupyterLite Bootstrap Flow                   │
├─────────────────────────────────────────────────────────────────┤
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
│  │ 4. Send "praxis:ready" → Angular                          │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Shim Loading Order

```
1. web_serial_shim.py → builtins.WebSerial
2. web_usb_shim.py → builtins.WebUSB
3. web_ftdi_shim.py → builtins.WebFTDI
4. web_bridge.py → written to virtual FS
5. Patch pylabrobot.io.serial.Serial = WebSerial
6. Patch pylabrobot.io.usb.USB = WebUSB
7. Patch pylabrobot.io.ftdi.FTDI = WebFTDI
```

## Key Code Locations

| Component | Lines |
|-----------|-------|
| Minimal Bootstrap | [95-120](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/playground/services/playground-jupyterlite.service.ts#L95-120) |
| Ready Listener | [51-70](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/playground/services/playground-jupyterlite.service.ts#L51-70) |
| Full Bootstrap | [173-351](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/playground/services/playground-jupyterlite.service.ts#L173-351) |

## Assessment: ✅ Sound but Complex

**Strengths:**
- 2-phase approach avoids URL length limits
- BroadcastChannel works across iframe boundary
- 30-second timeout with fallback

**Concerns:**
- Complex error paths if BroadcastChannel fails
- No retry mechanism for failed shim loads
