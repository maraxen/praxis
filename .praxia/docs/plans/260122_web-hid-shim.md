---
title: 'WebHID Shim Implementation Plan'
---

# WebHID Shim Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable browser-mode Inheco device support via WebHID API shim.

**Architecture:**
The solution involves creating a Python-side shim (`web_hid_shim.py`) that strictly mirrors the `pylabrobot.io.hid.HID` interface but communicates with the browser's WebHID API (via `navigator.hid`) through Pyodide's JavaScript bridge. This shim will be injected at runtime into the `pylabrobot` module hierarchy, effectively replacing the native `hid` library dependency with a browser-native implementation.

**Tech Stack:** Python (Pyodide), JavaScript (WebHID API), Asyncio

---

### Task 1: Create web_hid_shim.py

**Files:**

- Create: `praxis/web-client/src/assets/shims/web_hid_shim.py`

**Step 1: Boilerplate & Imports**

- Setup logging and Pyodide JS bridge imports (`js`, `pyodide.ffi`).
- Define `WebHID` class structure matching `pylabrobot.io.hid.HID` constructor signature (`vid`, `pid`, `serial_number`).

**Step 2: Implement Setup (Request Device)**

- Implement `async def setup(self)`.
- Use `navigator.hid.requestDevice` with VID/PID filters.
- **Constraint:** Requires user interaction. This connects with the standard PLR flow where `setup()` is called.
- Select the first returned device.
- Call `device.open()` via JS bridge.
- Initialize an `asyncio.Queue` for buffering input reports.
- Register `oninputreport` listener to push data to the queue.

**Step 3: Implement Read (Async Queue)**

- Implement `async def read(self, size: int, timeout: int) -> bytes`.
- Pull from the `asyncio.Queue` with `asyncio.wait_for(timeout)`.
- **Logic:** Handle data reconstruction. WebHID separates `reportId` and `data`.
  - If `reportId` == 0, return `data`.
  - If `reportId` != 0, return `bytes([reportId]) + data`.
  - *Note:* This heuristic aligns with how `hidapi` typically marshals data based on device configuration.

**Step 4: Implement Write**

- Implement `async def write(self, data: bytes, report_id: bytes = b"\x00")`.
- Parse `report_id` (byte) and `data` (bytes).
- Call `device.sendReport(reportId, data)` via JS bridge.

**Step 5: Implement Stop**

- Close device and clear listeners.

### Task 2: Update pyodide_io_patch.py

**Files:**

- Modify: `praxis/web-client/src/assets/shims/pyodide_io_patch.py`

**Step 1: Import WebHID**

- Add import for `web_hid_shim`.

**Step 2: Patch HID Module**

- In `patch_pylabrobot_io()`:
  - Target `pylabrobot.io.hid`.
  - Set `pylabrobot.io.hid.HID = WebHID`.
  - Force `pylabrobot.io.hid.USE_HID = True` (override default import failure).
  - Log success.

**Step 3: Update Status Reporting**

- Update `get_io_status()` to include `hid_patched` status.

### Task 3: Verification Script

**Files:**

- Create: `praxis/web-client/src/assets/shims/test_hid.py` (Temporary)

**Step 1: Create Test Script**

- Simple script to import `HID`, instantiate, and check type (should be `WebHID`).
