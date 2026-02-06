diff --git a/.agent/audits/hardware_discovery.md b/.agent/audits/hardware_discovery.md
new file mode 100644
index 0000000..1edc4b7
--- /dev/null
+++ b/.agent/audits/hardware_discovery.md
@@ -0,0 +1,72 @@
+# Audit: praxis/web-client/src/app/core/services/hardware-discovery.service.ts
+
+## Summary
+The `HardwareDiscoveryService` is a core Angular service responsible for managing the lifecycle of hardware device discovery and connection in the Praxis web client. It leverages WebSerial and WebUSB APIs for local browser-based discovery while also integrating with a backend API for broader hardware support and persistent registration. While the service provides comprehensive functionality, it suffers from critical data loss bugs in its low-level I/O methods, lacks unit tests, and relies heavily on type assertions and hardcoded device maps.
+
+## Logic Explanation
+The service acts as a bridge between physical hardware and the Praxis application:
+1.  **Discovery**: Combines local browser APIs (`navigator.serial`, `navigator.usb`) and backend API calls to populate a reactive list of `discoveredDevices`.
+2.  **Mapping**: Uses a hardcoded `KNOWN_DEVICES` table (VID:PID mapping) and external PLR definitions (`PLR_MACHINE_DEFINITIONS`) to infer the correct PyLabRobot backend for a device.
+3.  **Connection Management**: Handles opening and closing serial connections both locally (for immediate WebBridgeIO use) and via the backend (for persistent state).
+4.  **Low-Level I/O**: Provides methods like `readFromPort` and `writeToPort` which are used by `WebBridgeIO` to communicate with devices from a Python context (via Pyodide).
+5.  **State Management**: Uses Angular Signals (`discoveredDevices`, `isDiscovering`, etc.) to provide reactive state to the UI.
+
+## Documentation Gaps
+- **Data Loss in I/O Methods (Severity: High)**: The `readFromPort` and `readLineFromPort` methods do not buffer incoming data. If a stream chunk contains more data than requested or data beyond a newline, that extra data is discarded, leading to potential protocol desynchronization.
+- **Internal/Debug API Exposure (Severity: Medium)**: `discoverAllDebug` is marked "DEBUG ONLY" but is a public method that will be included in production builds without explicit guards.
+- **VID/PID Assumptions (Severity: Low)**: Implicitly assumes all serial devices will have `usbVendorId` and `usbProductId`, which might not be true for all virtual or legacy ports.
+
+## Quality Signals
+| File:Line | Signal Type | Severity | Issue |
+|-----------|-------------|----------|-------|
+| 477 | type_assertion | High | Unsafe cast of API response: `response.devices as Array<DiscoveredDeviceResponse>` |
+| 711 | type_assertion | Medium | Unsafe cast of API response: `connections as Array<ConnectionStateResponse>` |
+| 810-835 | robustness | High | `readFromPort` drops unread bytes from the current chunk. |
+| 840-864 | robustness | High | `readLineFromPort` drops bytes trailing the first newline in a chunk. |
+| 197-217 | hacky_pattern | Medium | Using `Date.now()` for IDs can lead to collisions in high-concurrency scenarios. |
+| 78-154 | maintainability | Medium | Large hardcoded `KNOWN_DEVICES` map makes the service difficult to extend without modification. |
+| Multiple | type_assertion | Low | Extensive use of `as DeviceStatus` (e.g., lines 489, 516, 567) indicating type mismatches between API and UI models. |
+
+## Brittleness Assessment
+Overall: **fragile**
+Rationale: The critical bug in data handling for serial ports makes any communication protocol that doesn't fit perfectly into chunk boundaries (most of them) liable to fail unexpectedly. Furthermore, the heavy reliance on hardcoded maps and unsafe type assertions against API responses makes the service prone to breaking when external definitions or API schemas change.
+
+### Locations
+- 810: fragile - `readFromPort` lacks a read buffer; data is lost if `value.length > size`.
+- 840: fragile - `readLineFromPort` lacks a read buffer; data following `\n` is lost.
+- 477: fragile - Casting backend response directly without validation.
+- 78: fragile - Hardcoded device mapping requires code changes for new hardware support.
+
+## Test Coverage
+- Covered: None (via unit tests).
+- Missing (critical):
+    - `readFromPort`/`readLineFromPort` (data integrity tests).
+    - `discoverAll` (merging and deduplication logic).
+    - `createDeviceFromSerialPort`/`createDeviceFromUSB` (mapping logic).
+    - `registerAsMachine` (error handling and payload construction).
+- Score: 0/5 (The service has NO dedicated unit tests; only mocked E2E integration tests exist in `web-bridge.spec.ts`).
+
+## Hacky Patterns
+- 78-154: Hardcoded device registry.
+- 197, 252: `Date.now()` used for device IDs.
+- 47-73: Redundant interface definitions (`BackendDevice`, `RegisterMachineRequest`, `RegisterMachineResponse`) that are not used by the implementation.
+- 160: Imports are scattered; some are after the `KNOWN_DEVICES` block.
+
+## Recommendations (Priority Order)
+1. [P0] **Implement a Read Buffer**: Refactor `readFromPort` and `readLineFromPort` to use a persistent buffer per port to prevent data loss.
+2. [P1] **Add Unit Tests**: Create `hardware-discovery.service.spec.ts` and cover core logic, especially the mapping and I/O methods.
+3. [P2] **Safe Type Casting**: Use Zod or a similar validation library (or at least better type guards) instead of `as` assertions for API responses.
+4. [P3] **Externalize Device Registry**: Move `KNOWN_DEVICES` to a separate configuration file or fetch it from the backend/assets.
+5. [P4] **Refactor ID Generation**: Use a more robust ID generation strategy (e.g., UUID or structured ID based on VID/PID/Serial).
+
+## Tech Debt Items
+- [high/robustness] Lack of serial data buffering leading to data loss.
+- [high/testing] Zero unit test coverage for a core hardware service.
+- [medium/maintainability] Hardcoded hardware mappings.
+- [medium/clean-code] Redundant unused interfaces and scattered imports.
+
+## Metrics
+- LOC: 899
+- Functions: 32
+- Complexity: Medium
+- Quality Score: 3/10

