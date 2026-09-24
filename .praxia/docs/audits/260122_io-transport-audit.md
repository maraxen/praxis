---
title: 'Recon Report: pylabrobot.io Transport Audit for Browser Mode'
---

# Recon Report: pylabrobot.io Transport Audit for Browser Mode

**Target:** pylabrobot.io transport abstraction layer
**Priority:** P1
**Auditor:** antigravity (recon persona)
**Date:** 2026-01-22

---

## 1. IO Transport Types Discovery

The `pylabrobot.io` module provides several transport abstractions for hardware communication. Below is a list of all identified types and their current support status in the browser (Pyodide) environment.

| Transport Type | Python Module | Native Library Dependency | Status |
| :--- | :--- | :--- | :--- |
| **Serial** | `pylabrobot.io.serial` | `pyserial` | ✅ Shimmed |
| **USB** | `pylabrobot.io.usb` | `pyusb` (libusb) | ✅ Shimmed |
| **FTDI** | `pylabrobot.io.ftdi` | `pylibftdi` (libftdi) | ✅ Shimmed |
| **HID** | `pylabrobot.io.hid` | `hid` (hidapi) | ❌ **NOT SHIMMED** |
| **Socket** | `pylabrobot.io.socket` | `asyncio` streams (raw TCP) | ❌ **NOT SHIMMED** |
| **HTTP** | `pylabrobot...backends.http` | `requests` | ❌ **NOT SHIMMED*** |

*\*Note: `HTTP` is partially functional via environment-level patches like `pyodide-http`, but lacks a formal `pylabrobot.io` implementation.*

---

## 2. Browser Shim Inventory

### ✅ Existing Shims (`praxis/web-client/src/assets/shims/`)

1. **`web_serial_shim.py`**: Implements `WebSerial` using the browser's WebSerial API. Supports both dynamic `requestPort` and `SerialProxy` for main-thread delegation.
2. **`web_usb_shim.py`**: Implements `WebUSB` using the browser's WebUSB API.
3. **`web_ftdi_shim.py`**: Implements `WebFTDI`. Critical for CLARIOstar support.

### ❌ Missing Shims

1. **HID Shim**: Required for **Inheco** heating/shaking devices.
2. **Socket Shim**: Required for **PreciseFlex** robot arms and **Inheco SiLA** interfaces.

---

## 3. Risk Assessment & Recommendations

### 🔴 High Risk: HID Devices (Inheco)

- **Impact**: Inheco temperature controllers are industry standard. Currently, they cannot be controlled in browser mode.
- **Recommendation**: Develop a `WebHID` shim. The WebHID API is compatible with the `hidapi` model used by PyLabRobot.

### 🔴 High Risk: Socket/TCP Limitations

- **Impact**: PreciseFlex arms and other ethernet-enabled devices are hard-blocked by browser security models which prevent raw TCP connections.
- **Recommendation**: This is a structural limitation. Short-term fix is to use a WebSocket-to-TCP proxy server (e.g., `websockify`) if local hardware access is required, or accept that these backends require a "bridged" execution mode.

### 🟠 Moderate Risk: Direct Imports Bypass

- **Finding**: Several backends (`BioShake`, `MasterFlex`, `Cytomat`) bypass `pylabrobot.io` and perform `import serial` directly.
- **Impact**: These backends will fail to load in Pyodide even if `pylabrobot.io.Serial` is patched.
- **Recommendation**: The `pyodide_io_patch.py` should be expanded to shim `sys.modules['serial']`, `sys.modules['usb']`, and `sys.modules['hid']` entirely, rather than just patching the `pylabrobot.io` namespace.

### 🟡 Low Risk: Missing Constants

- **Finding**: Some backends rely on constants from the `serial` module (e.g., `serial.EIGHTBITS`). Existing shims do not provide these.
- **Recommendation**: Ensure shims include standard `pyserial` and `pyusb` constant definitions to avoid `AttributeError`.

---

## 4. Proposed Action Plan

1. **Phase 1 (Immediate)**: Update `pyodide_io_patch.py` to inject shims into `sys.modules` to catch direct imports.
2. **Phase 2**: Implement `web_hid_shim.py` to enable Inheco device support.
3. **Phase 3**: Evaluate a WebSocket-to-TCP bridge for `Socket` transport support.
