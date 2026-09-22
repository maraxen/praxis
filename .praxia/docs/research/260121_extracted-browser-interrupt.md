# Browser Interrupt Logic Extraction (TD-801)

## Overview

This report documents the extraction of browser-side Python interruption logic from the `angular_refactor` branch diffs. The implementation enables graceful and immediate interruption of Python code executing via Pyodide in a Web Worker.

## Core Components

### 1. Python Worker (`python.worker.ts`)

- **Pyodide Initialization**: Uses `loadPyodide` from the `pyodide` package.
- **Interrupt Mechanism**:
  - Uses a `SharedArrayBuffer` to communicate interrupts from the main thread.
  - `const interruptBuffer = new Uint8Array(new SharedArrayBuffer(1));`
  - `loadedPyodide.setInterruptBuffer(interruptBuffer);`
  - Setting `interruptBuffer[0] = 2` triggers a `KeyboardInterrupt` in the Python runtime.
- **Lifecycle**: Initializes Pyodide on load and handles `run` and `interrupt` message types.

### 2. Python Runtime Service (`python-runtime.service.ts`)

- **Worker Encapsulation**: Manages the `Worker` instance lifecycle (`new Worker(...)`, `terminate()`).
- **Communication**:
  - Exposes a `messages$` observable (via `Subject`) for the main thread to consume worker updates.
  - `runCode(code)`: Sends a `{ type: 'run', payload: { code } }` message.
  - `interrupt()`: Sends a `{ type: 'interrupt' }` message.
- **Error Handling**: Captures `worker.onerror` and emits it through the message stream.

### 3. Execution Service (`execution.service.ts`)

- **Dual-Mode Execution**:
  - Dispatches to either the backend API or the `PythonRuntimeService` based on the environment/mode.
  - **Run ID**: Browser runs are prefixed with `browser-` (e.g., `browser-170123...`).
- **Status Mapping**:
  - Maps Pyodide-specific statuses to the application's `ExecutionStatus`:
    - `loading-pyodide` -> `PREPARING`
    - `pyodide-ready` -> `PENDING`
    - `executing-python` -> `RUNNING`
    - `python-execution-complete` -> `COMPLETED`
    - `python-execution-interrupted` -> `CANCELLED`
- **Interrupt Logic**:
  - In `stopRun()`, it checks `runId.startsWith('browser-')`.
  - If true, calls `this.pythonRuntimeService.interrupt()`.

## Interrupt Handling Patterns

1. **Shared Buffer Pre-emption**: The `SharedArrayBuffer` allows the main thread to flip a bit that the Pyodide runtime checks between bytecodes, ensuring the worker doesn't need to be terminated (preserving state).
2. **Reactive Message Loop**: The `ExecutionService` acts as a bridge, subscribing to worker messages and updating its internal `_currentRun` signal.
3. **Graceful Cleanup**: The `clearRun()` method triggers an `ngUnsubscribe` subject to clean up observables and calls `disconnect()`.

## Extracted Code Locations

- Service: `praxis/web-client/src/app/features/run-protocol/services/execution.service.ts`
- Runtime Model: `praxis/web-client/src/app/features/run-protocol/services/python-runtime.service.ts`
- Web Worker: `praxis/web-client/src/app/features/run-protocol/services/python.worker.ts`
- Tests: `*.spec.ts` in the same directory.
