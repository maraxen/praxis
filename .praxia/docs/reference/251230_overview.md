# Architecture Overview

Source: praxis/backend/core/protocols/orchestrator.py

Praxis is designed as a modular, service-oriented system for laboratory automation. This document provides a comprehensive overview of the architecture, components, and data flow.

## System Diagram

### Production Mode

```mermaid
graph TD
    %% Styling for Subgraph Titles
    classDef sectionTitle font-size:22px,font-weight:bold,fill:none,stroke:none;

    subgraph Frontend ["Frontend (Angular)"]
        UI[Web UI]
        Store[NgRx Store]
        Services[Frontend Services]
    end
    style Frontend fill:transparent,stroke:var(--mat-sys-primary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph API ["API Layer"]
        Server[FastAPI Server]
        WS[WebSocket Handler]
    end
    style API fill:transparent,stroke:var(--mat-sys-secondary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph Core ["Core Engine"]
        Orch[Orchestrator]
        Sched[Scheduler]
        Proto[Protocol Engine]
        Asset[Asset Manager]
    end
    style Core fill:transparent,stroke:var(--mat-sys-primary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph Runtime ["Runtime"]
        WCR[WorkcellRuntime]
        PLR[PyLabRobot]
        Sim[Simulators]
    end
    style Runtime fill:transparent,stroke:var(--mat-sys-secondary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph Workers ["Workers"]
        Celery[Celery Workers]
    end
    style Workers fill:transparent,stroke:var(--mat-sys-primary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph Data ["Data Layer"]
        PG[(PostgreSQL)]
        Redis[(Redis)]
    end
    style Data fill:transparent,stroke:var(--mat-sys-secondary),stroke-width:2px,color:var(--mat-sys-on-surface)

    UI --> Server
    UI --> WS
    Store --> Services
    Services --> Server

    Server --> Orch
    Server --> Asset
    WS --> Orch

    Orch --> Proto
    Orch --> Sched
    Sched --> Celery
    Celery --> Orch

    Orch --> WCR
    Asset --> WCR
    WCR --> PLR
    WCR --> Sim

    Server --> PG
    Orch --> Redis
    Celery --> Redis
    WCR --> PG
```

### Lite Mode

```mermaid
graph TD
    subgraph Frontend_Lite ["Frontend (Angular)"]
        UI_L[Web UI]
        Store_L[NgRx Store]
    end
    style Frontend_Lite fill:transparent,stroke:var(--mat-sys-primary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph API_Lite ["Local API"]
        Server_L[FastAPI Process]
    end
    style API_Lite fill:transparent,stroke:var(--mat-sys-secondary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph Core_Lite ["Core Engine"]
        Orch_L[Orchestrator]
        Asset_L[Asset Manager]
    end
    style Core_Lite fill:transparent,stroke:var(--mat-sys-primary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph Runtime_Lite ["Runtime"]
        WCR_L[WorkcellRuntime]
        PLR_L[PyLabRobot]
    end
    style Runtime_Lite fill:transparent,stroke:var(--mat-sys-secondary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph Data_Lite ["Data Layer"]
        SQLite[(SQLite)]
    end
    style Data_Lite fill:transparent,stroke:var(--mat-sys-secondary),stroke-width:2px,color:var(--mat-sys-on-surface)

    UI_L --> Server_L
    Store_L --> Server_L
    Server_L --> Orch_L
    Server_L --> Asset_L
    Orch_L --> WCR_L
    Asset_L --> WCR_L
    WCR_L --> PLR_L
    Server_L --> SQLite
    WCR_L --> SQLite
```

### Browser Mode (Pyodide)

```mermaid
graph TD
    subgraph Frontend_Browser ["Frontend (Browser Only)"]
        UI_B[Web UI]
        Store_B[NgRx Store]
        IO_Shim[IO Shim Service]
    end
    style Frontend_Browser fill:transparent,stroke:var(--mat-sys-primary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph WebWorker ["Web Worker (Pyodide)"]
        PyBridge[Python Bridge]
        Core_B[Core Engine]
        PLR_B[PyLabRobot]
    end
    style WebWorker fill:transparent,stroke:var(--mat-sys-secondary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph BrowserData ["Browser Storage"]
        IDB[(IndexedDB)]
        LocalStorage[(LocalStorage)]
    end
    style BrowserData fill:transparent,stroke:var(--mat-sys-primary),stroke-width:2px,color:var(--mat-sys-on-surface)

    subgraph Hardware ["Physical Hardware"]
        USB[WebSerial / USB]
        Bluetooth[WebBluetooth]
    end
    style Hardware fill:transparent,stroke:var(--mat-sys-secondary),stroke-width:2px,color:var(--mat-sys-on-surface)

    UI_B --> Store_B
    Store_B --> PyBridge
    PyBridge --> Core_B
    Core_B --> PLR_B
    
    PLR_B --> IO_Shim
    IO_Shim --> USB
    IO_Shim --> Bluetooth
    
    Store_B --> IDB
    Store_B --> LocalStorage
```

## Layer Responsibilities

### Frontend Layer

| Component | Responsibility |
|-----------|----------------|
| **Web UI** | Angular 19+ application with Material Design components |
| **NgRx Store** | Centralized state management with signal-based reactivity |
| **Frontend Services** | HTTP clients, WebSocket handlers, local storage |

### API Layer

| Component | Responsibility |
|-----------|----------------|
| **FastAPI Server** | RESTful endpoints for all resources and operations |
| **WebSocket Handler** | Real-time updates during protocol execution |
| **Middleware** | Authentication, CORS, request logging, error handling |

### Core Engine

| Component | Responsibility |
|-----------|----------------|
| **Orchestrator** | Step-by-step protocol execution control |
| **Scheduler** | Celery-based task queuing and scheduling |
| **Protocol Engine** | Python protocol loading and execution |
| **Asset Manager** | Hardware allocation and lifecycle management |

### Runtime Layer

| Component | Responsibility |
|-----------|----------------|
| **WorkcellRuntime** | Live PyLabRobot object management |
| **PyLabRobot** | Hardware driver abstraction |
| **Simulators** | Mock hardware for testing |

### Data Layer

| Component | Responsibility |
|-----------|----------------|
| **PostgreSQL** | Persistent storage for configurations, history, and logs |
| **Redis** | Distributed state, task queue, and caching |

## Key Design Principles

### 1. Separation of Concerns

Each layer has clear responsibilities:

- **API routes** handle HTTP concerns only
- **Services** implement business logic
- **Core components** manage execution flow
- **Runtime** handles hardware interaction

### 2. Async-First

The entire backend is built on async Python:

```python
async def execute_protocol(protocol_id: str, params: dict) -> ProtocolRun:
    async with get_db_session() as session:
        protocol = await protocol_service.get(session, protocol_id)
        run = await orchestrator.execute(protocol, params)
        return run
```

### 3. Type Safety

Comprehensive type hints throughout:

- **Pydantic models** for API validation
- **SQLAlchemy ORM** with typed models
- **TypeScript** with strict mode in frontend

### 4. State Isolation

Different state layers for different needs:

| State Type | Storage | Lifetime | Use Case |
|------------|---------|----------|----------|
| **Persistent** | PostgreSQL | Forever | Configurations, history |
| **Run State** | Redis | Per-run | Execution progress, shared data |
| **Live State** | Memory | Per-worker | Hardware objects, connections |

## Component Deep Dives

For detailed documentation on each component:

- [Backend Components](backend.md) - Orchestrator, Services, Models
- [Frontend Components](frontend.md) - Angular architecture, Store, Services
- [State Management](state-management.md) - How state flows through the system
- [Execution Flow](execution-flow.md) - Protocol execution lifecycle

## Technology Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Core language |
| FastAPI | 0.100+ | Web framework |
| SQLAlchemy | 2.0+ | ORM (async) |
| Celery | 5.3+ | Task queue |
| Redis | 7+ | Cache & state |
| PostgreSQL | 15+ | Database |
| PyLabRobot | Latest | Hardware control |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| Angular | 19+ | Framework |
| Material | 19+ | UI components |
| TypeScript | 5.4+ | Language |
| RxJS | 7+ | Reactive streams |
| Plotly | 2+ | Data visualization |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| GitHub Actions | CI/CD |
| MkDocs | Documentation |
