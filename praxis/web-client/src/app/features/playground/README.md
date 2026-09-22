# REPL Hardware Drivers

This directory contains the JupyterLite REPL component and hardware communication drivers for browser-based lab automation.

## WebUSB/WebSerial Architecture

### Overview

Browser mode supports hardware communication via WebUSB and WebSerial APIs. These APIs allow direct communication with laboratory instruments from the browser without requiring backend server connectivity.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser                                   │
│  ┌──────────────────┐    ┌──────────────────────────────────┐  │
│  │  Angular UI      │    │  Pyodide Worker                   │  │
│  │  (Main Thread)   │    │  (Python Runtime)                 │  │
│  │                  │    │                                    │  │
│  │  - ISerialDriver │───►│  - web_serial_shim.py             │  │
│  │  - DriverRegistry│    │  - web_usb_shim.py                │  │
│  └────────┬─────────┘    └─────────────┬────────────────────┘  │
│           │                            │                        │
│           ▼                            ▼                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  WebUSB / WebSerial APIs                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────┘
                                     │ USB
                                     ▼
                        ┌────────────────────────┐
                        │   Laboratory Hardware   │
                        │   (Hamilton, BMG, etc)  │
                        └────────────────────────┘
```

### Supported Devices

| Device | Chip/Protocol | Driver | Status |
|--------|---------------|--------|--------|
| CLARIOstar | FTDI USB-Serial | `FtdiSerialDriver` | ✅ Working |
| Hamilton STAR/Starlet | CDC-ACM | WebSerial native | ✅ Working |
| Opentrons OT-2 | HTTP API | REST (backend) | N/A |
| Tecan EVO/Fluent | Proprietary | Backend only | N/A |

### Driver Architecture

The driver system consists of several layers:

1. **Interfaces** (`serial-interface.ts`)
   - `ISerial`: Core serial port operations (open, close, read, write)
   - `ISerialDriver`: Device detection and connection factory

2. **Implementations**
   - `FtdiSerial`/`FtdiSerialDriver`: FTDI USB-to-Serial chips via WebUSB
   - `MockSerial`/`MockSerialDriver`: Testing without hardware

3. **Registry** (`driver-registry.ts`)
   - Maps USB VID/PID to appropriate driver
   - Supports runtime driver registration
   - Test mode for mock injection

## Driver Registration

Drivers are registered automatically when the registry is first accessed:

```typescript
import { findDriverForDevice, registerDriver } from './drivers';

// Find driver for a known device
const driver = findDriverForDevice(0x0403, 0x6001); // FTDI FT232R

// Register a custom driver
registerDriver(myCustomDriver);
```

### Pyodide Integration

The Python shims (`web_serial_shim.py`, `web_usb_shim.py`) are loaded into Pyodide and patched into PyLabRobot's I/O layer:

```python
import pylabrobot.io.serial as _ser
import pylabrobot.io.usb as _usb

_ser.Serial = WebSerial
_usb.USB = WebUSB
```

## Adding New Drivers

To add support for a new serial device:

### 1. Create Driver Class

```typescript
// my-device-driver.ts
import { ISerial, ISerialDriver, DeviceFilter } from './serial-interface';

export class MyDeviceSerial implements ISerial {
  private _isOpen = false;

  get isOpen(): boolean { return this._isOpen; }

  async open(options?: { baudRate?: number }): Promise<void> {
    // Device-specific open logic
    this._isOpen = true;
  }

  async close(): Promise<void> {
    // Device-specific close logic
    this._isOpen = false;
  }

  async read(length: number): Promise<Uint8Array> {
    // Device-specific read logic
  }

  async write(data: Uint8Array): Promise<void> {
    // Device-specific write logic
  }
}

export class MyDeviceDriver implements ISerialDriver {
  readonly driverName = 'MyDevice';
  readonly supportedDevices: DeviceFilter[] = [
    { vendorId: 0x1234, productId: 0x5678 },
  ];

  async connect(device: USBDevice): Promise<ISerial> {
    return new MyDeviceSerial(device);
  }
}
```

### 2. Register the Driver

Option A: Add to `driver-registry.ts` initialization:

```typescript
import { MyDeviceDriver } from './my-device-driver';

// In initializeRegistry()
drivers.push(new MyDeviceDriver());
```

Option B: Register at runtime:

```typescript
import { registerDriver } from './drivers';
import { MyDeviceDriver } from './my-device-driver';

registerDriver(new MyDeviceDriver());
```

### 3. Update Python Shim (if needed)

If the device requires special handling in Python, update `web_serial_shim.py` or create a new shim file.

## Testing

### Running Tests

```bash
cd praxis/web-client
npm test -- --include='**/serial*'
```

### Using Mock Driver

```typescript
import { enableTestMode, findDriverForDevice } from './drivers';

// Enable test mode
enableTestMode();

// Now mock driver is available
const mockDriver = findDriverForDevice(0xFFFF, 0xFFFF);
```

### Writing Tests

```typescript
import { MockSerial } from './drivers';

it('should handle device response', async () => {
  const serial = new MockSerial();
  serial.queueResponse(new Uint8Array([0x01, 0x02]));

  await serial.open();
  const response = await serial.read(10);

  expect(response).toEqual(new Uint8Array([0x01, 0x02]));
});
```

## Future Work

### Phase B: Main Thread Driver Migration

Currently, the FTDI driver runs in the Python/Pyodide worker. Phase B will:

1. Move USB I/O to TypeScript in the main browser thread
2. Create message-passing protocol between main thread and Pyodide worker
3. Convert Python-side shim to a thin proxy

## Related Files

- `jupyterlite-repl.component.ts` - REPL UI component
- `../../../assets/shims/web_serial_shim.py` - Python WebSerial shim
- `../../../assets/shims/web_usb_shim.py` - Python WebUSB shim
- `../../core/services/hardware-discovery.service.ts` - Device discovery UI
