---
title: 'PyLabRobot Hardware Communication Matrix'
---

# PyLabRobot Hardware Communication Matrix

**Last Updated**: 2026-01-07
**Purpose**: Reference documentation for PLR machine driver communication protocols and browser support.

---

## Communication Protocol Overview

| Protocol | Browser Support | Driver Location | Notes |
|----------|-----------------|-----------------|-------|
| **CDC-ACM Serial** | ✅ WebSerial API | Native browser | Standard USB serial, best browser support |
| **FTDI USB-Serial** | ✅ WebUSB API | `web_serial_shim.py` | Requires custom driver for status bytes |
| **Proprietary USB** | ⚠️ WebUSB API | Backend only | Device-specific protocols |
| **TCP/IP** | ✅ Fetch API | Backend proxy | CORS restrictions apply |
| **HTTP REST** | ✅ Fetch API | Direct or proxy | Native browser support |

---

## Machine Backend Matrix

### Liquid Handlers

| Machine | Vendor | FQN | Comm Protocol | Browser Driver | Status |
|---------|--------|-----|---------------|----------------|--------|
| STAR | Hamilton | `pylabrobot.liquid_handling.backends.hamilton.STAR` | CDC-ACM Serial | WebSerial native | ✅ Working |
| Starlet | Hamilton | `pylabrobot.liquid_handling.backends.hamilton.Starlet` | CDC-ACM Serial | WebSerial native | ✅ Working |
| Vantage | Hamilton | `pylabrobot.liquid_handling.backends.hamilton.Vantage` | CDC-ACM Serial | WebSerial native | ⏳ Untested |
| OT-2 | Opentrons | `pylabrobot.liquid_handling.backends.opentrons.OT2` | HTTP REST | Backend only | N/A (cloud API) |
| Flex | Opentrons | `pylabrobot.liquid_handling.backends.opentrons.Flex` | HTTP REST | Backend only | N/A (cloud API) |
| EVO | Tecan | `pylabrobot.liquid_handling.backends.tecan.EVO` | Proprietary | Backend only | N/A |
| Fluent | Tecan | `pylabrobot.liquid_handling.backends.tecan.Fluent` | Proprietary | Backend only | N/A |

### Plate Readers

| Machine | Vendor | FQN | Comm Protocol | Browser Driver | Status |
|---------|--------|-----|---------------|----------------|--------|
| CLARIOstar | BMG Labtech | `pylabrobot.plate_reading.clario_star_backend.CLARIOstarBackend` | FTDI USB-Serial | `FtdiSerialDriver` | ✅ Working |
| SPECTROstar | BMG Labtech | `pylabrobot.plate_reading.backends.bmg.SPECTROstar` | FTDI USB-Serial | `FtdiSerialDriver` | ⏳ Untested |

### Heating/Shaking

| Machine | Vendor | FQN | Comm Protocol | Browser Driver | Status |
|---------|--------|-----|---------------|----------------|--------|
| Hamilton Heater Shaker | Hamilton | `pylabrobot.heating_shaking.backends.hamilton.HamiltonHeaterShaker` | Serial | ⏳ TBD | ⏳ Untested |
| Inheco TEC | Inheco | `pylabrobot.heating_shaking.backends.inheco.InhecoTEC` | Serial | ⏳ TBD | ⏳ Untested |

### Simulation

| Machine | Vendor | FQN | Comm Protocol | Browser Driver | Status |
|---------|--------|-----|---------------|----------------|--------|
| SimulatorBackend | PyLabRobot | `pylabrobot.liquid_handling.backends.simulation.SimulatorBackend` | None (virtual) | N/A | ✅ Working |

---

## USB VID/PID Registry

Known device identifiers for automatic driver selection:

| VID | PID | Manufacturer | Model | Driver |
|-----|-----|--------------|-------|--------|
| `0x08BB` | `0x0106` | Hamilton | STAR | WebSerial CDC-ACM |
| `0x08BB` | `0x0107` | Hamilton | Starlet | WebSerial CDC-ACM |
| `0x0856` | `0xAC11` | B&B Electronics | USB-Serial (Hamilton adapter) | WebSerial CDC-ACM |
| `0x08AF` | `0x8000` | MCT | USB-Serial (Hamilton adapter) | WebSerial CDC-ACM |
| `0x0403` | `0x6001` | FTDI | FT232R | `FtdiSerialDriver` |
| `0x0403` | `0x6010` | FTDI | FT2232 | `FtdiSerialDriver` |
| `0x0403` | `0x6014` | FTDI | FT232H | `FtdiSerialDriver` |
| `0x0403` | `0xBB68` | FTDI | CLARIOstar | `FtdiSerialDriver` |

---

## Future Work

1. **Automated VID/PID Discovery**: Extract VID/PID from PLR backend source code during definition sync
2. **Driver Auto-Loading**: Dynamically load drivers based on discovered device types
3. **Hamilton E2E Validation**: Final validation with physical Starlet hardware
4. **Shaker/Heater Support**: Investigate communication protocols for auxiliary devices

---

## Related Documents

- [hardware_connectivity.md](../backlog/hardware_connectivity.md) - Active work items
- `praxis/web-client/src/app/features/repl/README.md` - Driver implementation guide
