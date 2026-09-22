---
title: 'RECON Report: Global Module Shimming Status'
---

# RECON Report: Global Module Shimming Status

## 1. Modules Injected into `sys.modules`

Based on the analysis of `praxis/web-client/src/assets/shims/pyodide_io_patch.py`, the following modules are injected into `sys.modules` to support direct imports in a Pyodide environment:

- **`serial`**: A shim module is injected, making `import serial` and `from serial import Serial` work.
- **`serial.tools`**: A placeholder module is injected.
- **`serial.tools.list_ports`**: A placeholder module with a `comports()` function that returns an empty list is injected.
- **`usb`**: A placeholder module is injected.
- **`usb.core`**: A placeholder module is injected to handle `import usb.core`.
- **`hid`**: A placeholder module is injected.

## 2. Constants and Classes Available

### `serial` Module Shim

- **Status:** PASS
- **Classes:**
    - `Serial`: Aliased to the `WebSerial` class from `web_serial_shim.py`.
    - `SerialException`: A simple alias for Python's built-in `Exception`.
- **Constants:**
    - **Bytesize:** `EIGHTBITS`, `SEVENBITS`, `FIVEBITS`, `SIXBITS`
    - **Parity:** `PARITY_NONE`, `PARITY_EVEN`, `PARITY_ODD`, `PARITY_MARK`, `PARITY_SPACE`
    - **Stopbits:** `STOPBITS_ONE`, `STOPBITS_TWO`, `STOPBITS_ONE_POINT_FIVE`

### `usb.core` Module Shim

- **Status:** FAIL (Partial Implementation)
- **Classes:**
    - `Device`: A phantom, empty class is defined to prevent `ImportError`. It has no functionality.
- **Functions:**
    - `find()`: A function that accepts any arguments but always returns `None`.

### `hid` Module Shim

- **Status:** FAIL (Partial Implementation)
- **Classes:** None
- **Functions:**
    - `device()`: Returns `None`.
    - `enumerate()`: Returns an empty list `[]`.

## 3. Direct Import Test Assessment

- **`import serial`**: **PASS**. The shim provides the `Serial` class and all required constants. Backends that use `import serial` should function correctly.
- **`import usb.core`**: **FAIL**. The shim prevents `ImportError`, but it does not provide a functional implementation. Any code that attempts to use the returned `Device` object or relies on `find()` to return a device will fail at runtime.
- **`import hid`**: **FAIL**. The shim prevents `ImportError`, but the `device()` and `enumerate()` functions are non-functional placeholders. Code relying on this module will fail at runtime.

## 4. Missing Items

- **`usb.core`**:
    - A functional `Device` class that wraps `WebUSB`.
    - A `find()` implementation that can discover and return authorized WebUSB devices.
    - Other `usb.core` constants or functions that might be required by specific backends.
- **`hid`**:
    - A functional `device` class or function that wraps a future `WebHID` implementation.
    - A functional `enumerate()` that can list authorized HID devices.
- **`pyserial` Constants**:
    - The current implementation covers the most common constants. A full review against the `pyserial` API documentation might reveal missing, less-common constants (e.g., related to flow control). However, what's implemented is likely sufficient for the known affected backends.

## 5. Recommendation

The global module shimming for `serial` is well-implemented and appears complete for the known use cases.

The shims for `usb` and `hid` are incomplete and serve only to prevent import errors. They are not functional replacements.

**Recommendation:**

1.  **Proceed with the `serial` shim as-is.** It is ready for use.
2.  **For `usb` and `hid`, a decision is required:**
    *   **Option A (Quick Fix):** If no backends currently rely on direct `import usb.core` or `import hid`, the existing placeholder shims are sufficient to prevent errors in the Pyodide environment. This can be considered a temporary solution.
    *   **Option B (Full Implementation):** If backends *do* require direct `usb.core` or `hid` access, a full implementation is necessary. This would involve creating wrapper classes that expose a `pyusb`- or `hidapi`-compatible API, backed by the `WebUSB` and a new `WebHID` shim. This is a more significant undertaking.

Given the context of the original prompt, which was primarily concerned with `serial` imports, the current state may be acceptable if no `usb` or `hid` backends are being used in the browser. An audit of backends that use `usb.core` and `hid` is recommended to determine the urgency of a full implementation.
