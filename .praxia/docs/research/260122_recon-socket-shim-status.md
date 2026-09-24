---
title: 'RECON Report: Socket/TCP Transport Shim Status'
---

# RECON Report: Socket/TCP Transport Shim Status

## 1. Current Implementation Status

**There is currently no implementation of a Socket/TCP transport shim for browser mode.**

- The existing I/O patching in `praxis/web-client/src/assets/shims/pyodide_io_patch.py` handles Serial, USB, HID, and FTDI protocols by mapping them to their corresponding Web APIs (e.g., WebSerial, WebUSB).
- This file and its related shims contain no code for handling raw TCP sockets.
- The `.agent/TECHNICAL_DEBT.md` file explicitly lists "Socket/TCP Transport Shim" as a missing feature and a high-priority item.

This confirms that direct TCP socket communication from PyLabRobot backends is not supported when running in a browser environment.

## 2. Architecture Approach

No architecture is currently in place. However, the prior research documented in `.agent/prompts/260122_socket_shim_research.md` and `.agent/TECHNICAL_DEBT.md` strongly recommends a **WebSocket-to-TCP Bridge** architecture.

The proposed architecture would consist of:

1.  **A Shimmed Socket Class (`web_socket_shim.py`):** A Python class for the Pyodide environment that mimics the standard Python `socket` interface but uses the browser's WebSocket API to communicate.
2.  **A Bridge Server:** A small, separate server process (e.g., Python, Node.js) that runs on the user's local machine or network. This server listens for incoming WebSocket connections from the browser and translates them into raw TCP socket connections to the target hardware. `websockify` is a well-known example of such a bridge.
3.  **Patching Mechanism:** The `pyodide_io_patch.py` script would be updated to inject the `web_socket_shim` into `pylabrobot.io.socket` and potentially into `sys.modules` to handle direct `import socket` calls.

**Data Flow:**
`PyLabRobot Backend (in Browser)` -> `web_socket_shim.py (WebSocket)` -> `Bridge Server` -> `Hardware (TCP)`

## 3. Blocked Hardware List

The absence of a TCP shim directly blocks hardware that relies on ethernet for command and control. Based on the technical debt log and prior research, the following hardware is confirmed to be blocked in browser mode:

-   **PreciseFlex Arms:** These robotic arms use raw TCP sockets for communication.
-   **Inheco SiLA Devices:** These devices use the SiLA (Standards in Lab Automation) protocol, which operates over TCP.
-   **Other ethernet-controlled hardware:** Any other device that requires a direct TCP/IP connection will not function in the browser.

## 4. Proposed Solution Path

The recommended path forward is to implement the **WebSocket-to-TCP Bridge** as described in the architecture section.

The implementation steps would be:

1.  **Develop the Bridge Server:** Create a simple, well-documented server application. A Python implementation using libraries like `websockets` would be a good choice to keep the technology stack consistent.
2.  **Implement the WebSocket Shim:** Create `web_socket_shim.py`. This shim will need to handle the connection lifecycle, data framing, and translation between Python's stream-based I/O and WebSocket messages.
3.  **Update `pyodide_io_patch.py`:** Integrate the new shim to patch the `socket` module at runtime in the Pyodide environment.
4.  **Documentation:** Update developer and user documentation to explain how to run the bridge server when using browser mode with affected hardware.
5.  **Testing:** Create tests to validate the end-to-end communication flow.

**Alternatives Considered (from prior research):**
-   **WebTransport API:** A newer browser API that uses QUIC. While promising, its browser support is less mature, and it may not be compatible with older lab hardware.
-   **Native Shell (Electron/Tauri):** This would involve wrapping the web client in a native application, which adds significant complexity and moves away from a pure browser-based solution.

The WebSocket bridge is the most mature, pragmatic, and widely-used solution for this problem.

## 5. Recommendation for Shipping

**This is a high-priority feature required for shipping browser-mode support for a critical class of hardware (robotic arms and SiLA devices).**

It is recommended to:
1.  **Proceed with the WebSocket-to-TCP Bridge implementation.**
2.  Prioritize this work, as it is a direct blocker for specific hardware integrations.
3.  Allocate resources to develop and test both the shim and the bridge server.

Without this feature, the browser-mode execution will remain incompatible with a significant portion of the automated lab hardware ecosystem.
