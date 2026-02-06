diff --git a/.agent/audits/python_runtime.md b/.agent/audits/python_runtime.md
new file mode 100644
index 0000000..46310e7
--- /dev/null
+++ b/.agent/audits/python_runtime.md
@@ -0,0 +1,78 @@
+# Audit: python_runtime
+
+## Summary
+The Pyodide-based Python runtime in Praxis consists of a Web Worker (`python.worker.ts`) and an Angular service (`python-runtime.service.ts`). The worker manages a full Python environment including PyLabRobot, Jedi, and custom shims for WebSerial/USB/FTDI/HID. The service acts as a bridge, handling lazy initialization, message routing for hardware I/O, user interactions, and a snapshot-based fast-start mechanism. While the system is feature-rich and supports complex hardware interactions, it exhibits some technical debt in the form of redundant promise wrappers, extensive use of `any` types, and a slight mismatch between implementation and unit tests.
+
+## Logic Explanation
+- **python.worker.ts**:
+  - Initializes Pyodide from local assets or CDN.
+  - Installs core Python packages (`micropip`, `jedi`, `pylabrobot`, `cloudpickle`).
+  - Sets up hardware shims (`web_serial_shim.py`, etc.) to intercept Python I/O and route it to JS via `postMessage`.
+  - Uses `PyodideConsole` for interactive execution, supporting multi-line input and completions.
+  - Supports snapshotting: can dump its state to a buffer or restore from one, significantly reducing startup time on subsequent loads.
+  - Handles `EXECUTE_BLOB` for running serialized protocol functions via `cloudpickle`.
+- **python-runtime.service.ts**:
+  - Lazily initializes the worker only when needed.
+  - Manages worker restoration from snapshots via `PyodideSnapshotService`.
+  - Routes `RAW_IO` messages from the worker to the `HardwareDiscoveryService`.
+  - Routes `USER_INTERACTION` messages to the `InteractionService` for UI dialogs.
+  - Provides a REPL-like interface with `execute`, `getCompletions`, and `getSignatures`.
+
+## Documentation Gaps
+- **Snapshot Protocol (severity: medium)**: The lifecycle of snapshot creation and restoration is not documented, making it unclear when snapshots are invalidated.
+- **RAW_IO Schema (severity: medium)**: The command set (OPEN, CLOSE, WRITE, READ, READLINE) used between Python and JS lacks formal documentation or a shared schema.
+- **EXECUTE_BLOB Preconditions (severity: low)**: Requirements for `machine_config` and `deck_setup_script` are not documented.
+
+## Quality Signals
+| File:Line | Signal Type | Severity | Issue |
+|-----------|-------------|----------|-------|
+| python.worker.ts:310 | long_function | Medium | `initializePyodide` is >200 lines |
+| python.worker.ts:618 | panic_prone | High | `(pyodide as any).loadSnapshot` - using `any` on critical API |
+| python.worker.ts:668 | panic_prone | High | `(pyodide as any).dumpSnapshot` - using `any` on critical API |
+| python-runtime.service.ts:228 | hacky_pattern | High | Redundant `return new Promise` wrapper in `getCompletions` |
+| python-runtime.service.ts:256 | hacky_pattern | High | Redundant `return new Promise` wrapper in `getSignatures` |
+| python-runtime.service.ts:310 | magic_value | Low | `payload: any` in `sendMessage` |
+| python.worker.ts:8 | magic_value | Low | `machine_config: any` type |
+| python.worker.ts:559 | error_swallowing | Medium | catch block in `executePush` might swallow context if traceback fails |
+
+## Brittleness Assessment
+Overall: robust
+Rationale: The system handles many failure modes, such as falling back to fresh initialization if a snapshot fails to load. It uses `Promise.all` for parallel loading of assets, which is efficient but could be brittle if one of many optional stubs fails to fetch. The use of `as any` for Pyodide snapshot APIs is a sign of mismatched type definitions but doesn't necessarily mean it will fail at runtime if the version of Pyodide is consistent.
+
+### Locations
+- python.worker.ts:633 - robust: Fallback to fresh init if snapshot restore fails.
+- python-runtime.service.ts:228 - fragile: Redundant promise nesting is confusing and prone to bugs during refactoring.
+- python.worker.ts:526 - fragile: splitting code by lines in `executePush` might interfere with multi-line statements if not handled perfectly by `PyodideConsole`.
+
+## Test Coverage
+- Covered: `should initialize worker`, `should handle execution` (mostly).
+- Missing (critical):
+  - Snapshot integration tests (current tests mark it as "to be implemented" or "baseline").
+  - `RAW_IO` routing to `HardwareDiscoveryService`.
+  - `USER_INTERACTION` routing to `InteractionService`.
+  - Error handling during `micropip` installation or shim loading.
+- Score: 2/5
+
+## Hacky Patterns
+- python-runtime.service.ts:228 - Double promise wrapper.
+- python.worker.ts:365 - Parallel fetch of stubs for cloudpickle hardcodes many paths in the worker.
+- python.worker.ts:474 - Verification call with hardcoded strings for scope check.
+
+## Recommendations (Priority Order)
+1. [P1] Refactor `getCompletions` and `getSignatures` in `python-runtime.service.ts` to remove redundant promise wrappers.
+2. [P1] Update unit tests to reflect the current implementation of snapshotting and message routing.
+3. [P2] Define proper TypeScript interfaces for message payloads instead of using `any`.
+4. [P2] Break down the large `initializePyodide` function into smaller, more manageable sub-functions.
+5. [P3] Formalize the `RAW_IO` protocol in a shared documentation or schema file.
+
+## Tech Debt Items
+- [high/robustness] Redundant promise nesting in REPL methods.
+- [medium/testing] Outdated unit tests for snapshotting features.
+- [low/refactoring] Massive `initializePyodide` function needs decomposition.
+- [medium/types] High usage of `any` in worker messages.
+
+## Metrics
+- LOC: 1167
+- Functions: 25
+- Complexity: high
+- Quality Score: 6/10

