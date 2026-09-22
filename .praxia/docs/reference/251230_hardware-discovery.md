# Hardware Discovery

Praxis can automatically detect laboratory devices connected via USB or serial ports using browser APIs.

## Overview

Hardware discovery uses:

- **WebSerial API**: For serial port devices (RS-232, USB-serial adapters)
- **WebUSB API**: For direct USB devices

!!! note "Browser Support"
    WebSerial and WebUSB are supported in Chromium-based browsers (Chrome, Edge, Brave). Firefox and Safari do not currently support these APIs.

## Using Hardware Discovery

### Opening the Dialog

**From Assets page:**

1. Navigate to **Assets** → **Machines** tab
2. Click **Discover Hardware**

**From Command Palette:**

1. Press <kbd>Cmd</kbd>+<kbd>K</kbd> (or <kbd>Ctrl</kbd>+<kbd>K</kbd>)
2. Type "discover hardware"
3. Select the action

**Keyboard shortcut:**

- <kbd>Alt</kbd>+<kbd>D</kbd> opens hardware discovery directly

### Scanning for Devices

#### Scan All

Click **Scan All** to detect all connected devices:

1. Browser prompts for permission
2. Discovered devices are listed
3. PLR-compatible devices show inferred type

#### Add Serial Device

For serial port devices specifically:

1. Click **Add Serial Device**
2. Select the port from browser dialog
3. Device appears in list with serial info

#### Add USB Device

For direct USB devices:

1. Click **Add USB Device**
2. Select the device from browser dialog
3. Device appears with USB vendor/product info

### Understanding Results

Each discovered device shows:

| Field | Description |
|-------|-------------|
| **Type** | Serial or USB |
| **Status** | Connected, Disconnected, Unknown |
| **PLR Type** | Inferred PyLabRobot type (if recognized) |
| **Vendor ID** | USB vendor identifier |
| **Product ID** | USB product identifier |

### Device Recognition

Praxis recognizes common lab devices by their USB identifiers:

| Vendor | Products |
|--------|----------|
| **Opentrons** | OT-2, Flex, modules |
| **Hamilton** | STAR, Microlab |
| **FTDI** | Serial adapters (many devices) |
| **Tecan** | EVO, Fluent |

Unrecognized devices show "Unknown" but can still be registered manually.

### Configuring Devices

Some devices require configuration before use:

1. Expand the device panel
2. Fill in required fields (baud rate, protocol, etc.)
3. Click **Save Configuration**

Common configuration options:

| Option | Description | Typical Values |
|--------|-------------|----------------|
| **Baud Rate** | Serial communication speed | 9600, 115200 |
| **Data Bits** | Bits per character | 7, 8 |
| **Stop Bits** | End of character marker | 1, 2 |
| **Parity** | Error checking | None, Even, Odd |

### Registering as Machine

Once configured, register the device:

1. Click **Register as Machine**
2. Enter a name
3. Select the PLR type (or confirm inferred type)
4. Review connection settings
5. Click **Save**

The device appears in your Machines list.

## Troubleshooting

### No Devices Found

**Check physical connections:**

- Ensure cables are securely connected
- Try a different USB port
- Check power to the device

**Check browser permissions:**

- Clear site permissions and try again
- Some browsers require HTTPS for WebSerial/WebUSB

**Try manual selection:**

- Use **Add Serial Device** or **Add USB Device**
- Browser shows a picker even if auto-scan fails

### Device Not Recognized

If a device isn't recognized as PLR-compatible:

1. Check if the device is supported by PyLabRobot
2. Register manually and specify the correct FQN
3. Configure connection parameters as needed

### Permission Denied

WebSerial/WebUSB require user gesture:

1. Click the scan button (not keyboard shortcut)
2. Browser shows permission dialog
3. Select the device and click "Connect"

### Device Disconnects

If devices disconnect unexpectedly:

- Check USB power (try powered hub)
- Check cable quality
- Some devices require driver installation

## API Integration

### Backend Endpoints

```
GET  /api/v1/hardware/discover/serial   # List serial devices
GET  /api/v1/hardware/discover/usb      # List USB devices
POST /api/v1/hardware/register          # Register a device
```

### Request Example

```bash
# Discover and register a device
curl -X POST http://localhost:8000/api/v1/hardware/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Flex Lab A",
    "device_type": "serial",
    "port": "/dev/ttyUSB0",
    "fqn": "pylabrobot.liquid_handling.backends.opentrons.OpentronsBackend",
    "connection_info": {
      "host": "192.168.1.50",
      "port": 31950
    }
  }'
```

## Security Considerations

!!! warning "USB Device Security"
    WebUSB and WebSerial provide direct hardware access. Only grant permissions to trusted sites.

Best practices:

1. Only use hardware discovery over HTTPS in production
2. Regularly audit connected devices
3. Revoke browser permissions when not needed
4. Use device authentication where available

## Browser Mode Behavior

In browser mode, hardware discovery returns mock devices:

- Simulated serial and USB devices
- Pre-configured PLR types
- No actual hardware access

This allows testing the UI flow without real hardware.
