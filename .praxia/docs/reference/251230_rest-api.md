# REST API Reference

The Praxis backend provides a RESTful API built with FastAPI. All endpoints are prefixed with `/api/v1`.

## Base URL

```
http://localhost:8000/api/v1
```

## Interactive Documentation

FastAPI auto-generates interactive docs:

```
GET /docs      # Swagger UI
GET /redoc     # ReDoc
```

## Authentication

```
POST /api/v1/auth/login       # Get JWT token
POST /api/v1/auth/logout      # Invalidate session
GET  /api/v1/auth/me          # Current user info
```

Most endpoints require a JWT bearer token:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/...
```

## Protocols

### Definitions (CRUD)

```
GET    /api/v1/protocols/definitions            # List protocol definitions
GET    /api/v1/protocols/definitions/{id}        # Get protocol definition
POST   /api/v1/protocols/definitions             # Create protocol definition
PUT    /api/v1/protocols/definitions/{id}        # Update protocol definition
DELETE /api/v1/protocols/definitions/{id}        # Delete protocol definition
```

### Runs

```
GET    /api/v1/protocols/runs                    # List protocol runs
GET    /api/v1/protocols/runs/{id}               # Get run details
POST   /api/v1/protocols/runs/actions/start       # Start a protocol run
```

### Execution Control

```
POST   /api/v1/protocols/runs/{run_id}/pause     # Pause a running protocol
POST   /api/v1/protocols/runs/{run_id}/resume    # Resume a paused protocol
```

## Machines

```
GET    /api/v1/machines/definitions              # List machine definitions (CRUD)
GET    /api/v1/machines/definitions/{id}         # Get machine definition
POST   /api/v1/machines/definitions              # Create machine
PUT    /api/v1/machines/definitions/{id}         # Update machine
DELETE /api/v1/machines/definitions/{id}         # Delete machine
PATCH  /api/v1/machines/{id}/status              # Update machine status
```

### Machine Frontends & Backends

```
GET    /api/v1/machine-frontends/                # List frontend definitions
GET    /api/v1/machine-frontends/{id}            # Get frontend
GET    /api/v1/machine-frontends/{id}/backends   # List backends for frontend
POST   /api/v1/machine-frontends/                # Create frontend
PUT    /api/v1/machine-frontends/{id}            # Update frontend
DELETE /api/v1/machine-frontends/{id}            # Delete frontend

GET    /api/v1/machine-backends/                 # List backend definitions
POST   /api/v1/machine-backends/                 # Create backend
```

## Resources (Labware)

```
GET    /api/v1/resources/definitions             # List resource definitions (CRUD)
GET    /api/v1/resources/definitions/{id}        # Get resource definition
POST   /api/v1/resources/definitions             # Create resource
PUT    /api/v1/resources/definitions/{id}        # Update resource
DELETE /api/v1/resources/definitions/{id}        # Delete resource
GET    /api/v1/resources/{id}                    # Get individual resource instance
```

## Decks

```
GET    /api/v1/decks/                            # List decks (CRUD)
GET    /api/v1/decks/{id}                        # Get deck
POST   /api/v1/decks/                            # Create deck
PUT    /api/v1/decks/{id}                        # Update deck
DELETE /api/v1/decks/{id}                        # Delete deck
GET    /api/v1/decks/types                       # List deck type definitions
```

## Workcell

> **Note:** This prefix is singular (`/workcell`), not plural.

```
GET    /api/v1/workcell/                         # List workcells (CRUD)
GET    /api/v1/workcell/{id}                     # Get workcell
POST   /api/v1/workcell/                         # Create workcell
PUT    /api/v1/workcell/{id}                     # Update workcell
DELETE /api/v1/workcell/{id}                     # Delete workcell
```

## Discovery

```
POST   /api/v1/discovery/sync-all                # Trigger protocol/hardware discovery
```

## Hardware

```
GET    /api/v1/hardware/discover/serial          # Discover serial devices
GET    /api/v1/hardware/discover/usb             # Discover USB devices
POST   /api/v1/hardware/register                 # Register a hardware device
GET    /api/v1/hardware/status                   # Hardware status overview
```

## Scheduler

```
GET    /api/v1/scheduler/entries                 # List scheduled entries (CRUD)
GET    /api/v1/scheduler/entries/{id}            # Get entry
POST   /api/v1/scheduler/entries                 # Create entry
PUT    /api/v1/scheduler/entries/{id}            # Update entry
DELETE /api/v1/scheduler/entries/{id}            # Delete entry
POST   /api/v1/scheduler/entries/{id}/execute    # Execute entry now
```

## Data Outputs

```
GET    /api/v1/data-outputs/outputs              # List run outputs
GET    /api/v1/data-outputs/outputs/{id}         # Get output
GET    /api/v1/data-outputs/outputs/{id}/export  # Export (format=csv|json)
```

## WebSockets

```
WS     /api/v1/ws/execution/{run_id}             # Real-time execution updates
```

## REPL

```
WS     /api/v1/repl/session                      # Interactive Python REPL
POST   /api/v1/repl/save_session                 # Save REPL session
```

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Human-readable error description"
}
```

| Code | Meaning |
|------|---------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists or is in use |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error |

## OpenAPI Schema

```
GET /api/v1/openapi.json
```
