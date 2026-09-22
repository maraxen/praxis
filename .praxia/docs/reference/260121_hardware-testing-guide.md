---
title: 'WebSerial Hardware-in-the-Loop (HITL) Testing Guide'
---

# WebSerial Hardware-in-the-Loop (HITL) Testing Guide

This document outlines the manual testing procedures for verifying WebSerial-based hardware discovery and communication in Praxis. Due to current CI limitations, this process is a critical step to ensure hardware compatibility before merging related changes.

## 1. Required Hardware

To perform these tests, you will need access to the following physical hardware:

- **Hamilton STARlet**: Liquid handler.
- **Hamilton STAR**: Liquid handler.
- **BMG CLARIOstar**: Plate reader.
- **Opentrons OT-2**: Liquid handler.
- A computer with a recent version of **Google Chrome** or **Microsoft Edge** (verifying WebSerial API support).
- Necessary USB cables to connect each instrument.

## 2. Browser Permission Setup

The WebSerial API requires explicit user permission to access serial devices. This is a critical security feature of the browser.

1.  **Initial Connection**: The first time you attempt to connect to a device from the Praxis UI, the browser will display a permission dialog in the top-left corner.
2.  **Device List**: The dialog will show a list of available serial devices detected by the operating system.
3.  **Granting Access**: Select the correct device from the list and click "Connect". This grants the Praxis web application access to that device for the current session.
4.  **Revoking Access**: Permissions can be managed or revoked by clicking the lock icon in the address bar and navigating to "Site settings".

**Note**: If the expected device does not appear in the list, it may be due to a driver issue, a faulty cable, or another application holding a lock on the serial port. See the Troubleshooting section for more details.

## 3. Step-by-Step Testing Procedure

Follow these steps for each piece of hardware listed above.

1.  **Physical Connection**:
    - Ensure the hardware is powered on.
    - Connect the device directly to your computer via a USB cable. Avoid using USB hubs if possible, as they can sometimes introduce instability.

2.  **Launch Praxis**:
    - Start the Praxis application stack.
    - Navigate to the "Hardware" -> "Discovery" page in the web client.

3.  **Initiate Scan**:
    - Click the "Scan for Devices" button.
    - The browser should prompt you for permission to access a serial device.

4.  **Select Device**:
    - In the browser's device selection dialog, find and select the target hardware (e.g., "Hamilton STARlet").
    - Click "Connect".

5.  **Verify Discovery**:
    - The UI should update to show that the device has been discovered.
    - A new card representing the hardware should appear on the screen, displaying its name and status.
    - Confirm that the displayed information (e.g., model name) is correct.

6.  **Test Communication (If Applicable)**:
    - For devices with interactive controls (like liquid handlers), attempt a simple action if the UI supports it (e.g., "Home axes").
    - This step verifies that the command-response loop is functional.

7.  **Disconnect and Repeat**:
    - Physically disconnect the device.
    - The device's status in the UI should update, perhaps to "Disconnected" or by being removed from the list.
    - Reconnect the device and ensure it can be discovered again.
    - Repeat this process for all required hardware.

## 4. Known VID/PID Mappings

This section provides the standard Vendor ID (VID) and Product ID (PID) pairs used by the application to identify supported hardware.

| Device             | Vendor ID (VID) | Product ID (PID) |
| ------------------ | --------------- | ---------------- |
| Hamilton STARlet   | `0x08BB`        | `0x0107`         |
| Hamilton STAR      | `0x08BB`        | `0x0106`         |
| BMG CLARIOstar     | `0x0403`        | `0xBB68`         |
| Opentrons OT-2     | `0x04D8`        | `0xE11A`         |

This mapping is crucial for the hardware discovery service to correctly filter and identify compatible devices.

## 5. Troubleshooting Common Issues

**Issue: Device not appearing in the browser's selection list.**

- **Driver Issues**: Ensure the necessary FTDI or serial port drivers are installed on your operating system. Windows usually handles this automatically, but macOS or Linux may require manual installation.
- **Cable Fault**: Try a different USB cable.
- **Port Lock**: Another application (e.g., a vendor-specific control software, a terminal emulator like PuTTY) might be holding the serial port open. Close all other applications that might be communicating with the device.
- **Permissions**: On Linux, you may need to add your user to the `dialout` group (`sudo usermod -a -G dialout $USER`) to have permission to access serial devices.

**Issue: Device is discovered but communication fails.**

- **Incorrect Baud Rate/Settings**: This is unlikely if using the official Praxis software but could be an issue in development. The application must connect with the correct serial port settings (baud rate, data bits, etc.).
- **Firmware Issues**: The device's firmware may be in a bad state. Try power cycling the instrument.

**Issue: Browser does not ask for permission.**

- **WebSerial Not Supported**: Ensure you are using a compatible browser (Chrome, Edge).
- **Insecure Context**: The WebSerial API is only available on secure contexts (`https://` or `localhost`). Ensure you are accessing the Praxis frontend accordingly.

## 6. Flight Checklist Template

Use this template for each manual testing session. Copy the markdown below and fill it out.

```markdown
# Hardware Test Flight Checklist

**Date**: YYYY-MM-DD
**Tester**: [Your Name]
**Praxis Version/Branch**: [Version or Git Branch]

---

### Hamilton STARlet (0x08BB:0x0107)

- [ ] Powered on and connected via USB.
- [ ] Device appears in browser permission dialog.
- [ ] Device successfully discovered in Praxis UI.
- [ ] Correct model name displayed.
- [ ] **Result**: PASS / FAIL
- **Notes**:

---

### Hamilton STAR (0x08BB:0x0106)

- [ ] Powered on and connected via USB.
- [ ] Device appears in browser permission dialog.
- [ ] Device successfully discovered in Praxis UI.
- [ ] Correct model name displayed.
- **Result**: PASS / FAIL
- **Notes**:

---

### BMG CLARIOstar (0x0403:0xBB68)

- [ ] Powered on and connected via USB.
- [ ] Device appears in browser permission dialog.
- [ ] Device successfully discovered in Praxis UI.
- [ ] Correct model name displayed.
- **Result**: PASS / FAIL
- **Notes**:

---

### Opentrons OT-2 (0x04D8:0xE11A)

- [ ] Powered on and connected via USB.
- [ ] Device appears in browser permission dialog.
- [ ] Device successfully discovered in Praxis UI.
- [ ] Correct model name displayed.
- **Result**: PASS / FAIL
- **Notes**:

---

### Summary

- **Overall Result**: ALL PASS / ISSUES FOUND
- **Blockers**: [List any issues preventing full validation]
```
