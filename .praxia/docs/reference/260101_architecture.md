---
title: 'Application Architecture: Runtime Modes'
---

# Application Architecture: Runtime Modes

This document outlines the architectural differences between the various runtime modes of PyLabPraxis.

## Overview

PyLabPraxis is designed to run in multiple environments, ranging from a purely client-side browser experience to a full-scale production deployment. The `ModeService` in the frontend is the central authority for determining the current mode.

## Modes

### 1. Browser Mode (`browser`)

* **Description**: Pure client-side application running in the browser.
* **Backend**: None. No API calls to a Python backend.
* **Execution**:
  * **Simulation**: Supported via client-side logic or limited WASM implementation (future).
  * **Physical**: Not supported directly (unless via WebSerial shim, deemed experimental).
* **Storage**: `LocalStorage` / `IndexedDB` for converting and saving data locally.
* **Authentication**: Bypassed.
* **Key Restrictions**:
  * **Scheduling**: Disabled. The scheduler requires a persistent backend worker.
  * **Reservations**: Not supported.
  * **Database**: No persistent relational database.

### 2. Demo Mode (`demo`)

* **Description**: A variation of Browser Mode pre-loaded with fake assets, protocols, and data to demonstrate functionality.
* **Backend**: None.
* **Difference**: Uses `DemoInterceptor` to intercept HTTP requests and return mock data.
* **Key Restrictions**: Same as Browser Mode.

### 3. Lite Mode (`lite`)

* **Description**: A lightweight local deployment.
* **Backend**: Local Python FastAPI server.
* **Database**: SQLite.
* **Execution**: Supports local physical hardware control.
* **Authentication**: Simplified or bypassed (depending on config).
* **Key Restrictions**:
  * Designed for single-user or small lab usage.

### 4. Production Mode (`production`)

* **Description**: Full-scale deployment.
* **Backend**: Full FastAPI cluster.
* **Database**: PostgreSQL.
* **Infrastructure**: Redis (for caching/queues), Keycloak (for Auth).
* **Execution**: Full job queueing and scheduler support.

## Feature Matrix

| Feature | Browser | Demo | Lite | Production |
| :--- | :---: | :---: | :---: | :---: |
| **Authentication** | ❌ | ❌ | ✅ | ✅ |
| **Physical Execution** | ⚠️ (WebSerial) | ❌ | ✅ | ✅ |
| **Simulation** | ✅ | ✅ | ✅ | ✅ |
| **Scheduler** | ❌ | ❌ | ✅ | ✅ |
| **Asset Reservations** | ❌ | ❌ | ✅ | ✅ |
| **Persistent History** | ❌ (Local Only) | ❌ | ✅ | ✅ |

## Design Decisions

### Browser Mode Limitations

In Browser Mode, we explicitly disable features that require a persistent backend state or complex background workers.

* **Scheduler**: The scheduler relies on a background worker to trigger jobs at specific times. This cannot be reliably implemented in a pure browser environment due to tab suspension and lack of server persistence. UI elements for scheduling are disabled and explain this limitation.
* **Reservations**: Asset reservations require a centralized lock manager (Database/Redis) to prevent race conditions. Valid only in a multi-user or server-backed environment.
