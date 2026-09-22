# Browser Mode Connection Persistence Tests

This document outlines the test plan for validating hardware connection persistence in Browser Mode.

## 1. Current Behavior

The `ExecutionService` manages the connection to the backend for protocol execution.

- **Communication**: The frontend communicates with the backend via a WebSocket connection for real-time updates on the execution status.
- **State Management**: The service uses Angular Signals to maintain the execution state in memory. This includes the run ID, status, logs, and progress.
- **Persistence**: The connection and execution state are **not** persisted across page refreshes. If the page is reloaded, the in-memory state is lost, and the WebSocket connection is terminated.
- **Reconnection**: The WebSocket connection has a basic retry mechanism (`retry({ delay: 3000, count: 3 })`) that attempts to reconnect if the connection is lost during a run. However, this does not cover page reloads.

## 2. Test Scenarios

### 2.1. Test Connection State Across Page Refresh

- **Objective**: Verify that the connection state is lost on page refresh.
- **Preconditions**:
    1. The application is running in Browser Mode.
    2. A protocol run has been started and is in the `RUNNING` state.
- **Steps**:
    1. Observe the UI and confirm that the execution status, logs, and progress are being updated.
    2. Refresh the browser page.
- **Expected Outcome**:
    - After the refresh, the UI should reset to its initial state.
    - The application should not automatically reconnect to the ongoing run.
    - The previous execution state (logs, progress) should be lost.

### 2.2. Test Reconnection After Device Disconnect

- **Objective**: Verify the WebSocket retry mechanism.
- **Preconditions**:
    1. The application is running in Browser Mode.
    2. A protocol run has been started and is in the `RUNNING` state.
- **Steps**:
    1. Disconnect the network on the client machine to simulate a connection loss.
    2. Observe the browser's developer console for WebSocket error messages.
    3. Reconnect the network within the retry window (approximately 9 seconds).
- **Expected Outcome**:
    - The WebSocket should attempt to reconnect.
    - Once the network is restored, the connection should be re-established, and the UI should resume receiving updates.

### 2.3. Test Recovery After USB Errors

- **Objective**: Document the application's behavior when the backend reports a hardware error.
- **Preconditions**:
    1. The application is running in Browser Mode.
- **Steps**:
    1. Manually send a WebSocket message of type `error` from the backend to the client.
- **Expected Outcome**:
    - The `ExecutionService` should handle the message and update the run state to `FAILED`.
    - The UI should display an error message in the logs.
    - The WebSocket connection should be terminated.

## 3. Identified Gaps and Potential Improvements

1.  **No State Persistence**: The most significant gap is the lack of state persistence across page reloads. This can lead to a poor user experience, as any page refresh will lose the context of the ongoing run.
    - **Suggestion**: Use `localStorage` to store the `runId` of the active run. On application load, check for an active `runId` and, if one exists, automatically reconnect to the WebSocket to resume monitoring.
2.  **No Manual Reconnect**: There is no UI mechanism to manually reconnect to a run.
    - **Suggestion**: Add a "Reconnect to last run" button if a `runId` is found in `localStorage` but the WebSocket connection fails.
3.  **Limited Error Recovery**: The frontend simply displays errors reported by the backend. There are no mechanisms for user-initiated recovery actions (e.g., "retry step," "ignore error").
    - **Suggestion**: This is a larger feature, but worth noting. A more robust implementation might include a more sophisticated error handling and recovery workflow.
