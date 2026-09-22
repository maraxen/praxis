# Hardware Discovery Audit

## Architecture Overview

[hardware-discovery.service.ts](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/services/hardware-discovery.service.ts)

```
┌─────────────────────────────────────────────────────────────────┐
│                  Hardware Discovery Flow                        │
├─────────────────────────────────────────────────────────────────┤
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
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Connection Lifecycle:                                          │
│  available → connecting → connected → busy → disconnected       │
└─────────────────────────────────────────────────────────────────┘
```

## VID/PID Coverage Gap

| Metric | Count |
|--------|-------|
| `KNOWN_DEVICES` entries | **9** |
| `PLR_BACKEND_DEFINITIONS` entries | **33** |
| Coverage gap | **~73%** of backends have no VID/PID mapping |

### KNOWN_DEVICES Table

| VID:PID | Device | Has PLR Backend |
|---------|--------|-----------------|
| `0x08BB:0x0106` | Hamilton STAR | ✅ |
| `0x08BB:0x0107` | Hamilton Starlet | ✅ |
| `0x04D8:0xE11A` | Opentrons OT-2 | ✅ |
| `0x0856:0xAC11` | Hamilton via B&B | ✅ |
| `0x0403:0xBB68` | BMG CLARIOstar | ✅ |
| `0x08AF:0x8000` | Hamilton via MCT | ✅ |
| `0x1A86:0x7523` | Generic CH340 | ❌ |
| `0x0403:0x6001` | FTDI FT232 | ❌ |
| `0x067B:0x2303` | Prolific PL2303 | ❌ |

## Assessment: ⚠️ Significant Gap

Missing backends include Tecan, Inheco, Agilent, and many plate readers.

**Recommendation**: Auto-discovery from PLR package or backend API fallback.
