# Quick Start

Get up and running with Praxis in 5 minutes.

## Prerequisites

Complete the [Installation](installation.md) guide first. You can choose between [Browser Mode](installation-browser.md), [Production Mode](installation-production.md), or [Lite Mode](installation-lite.md).

## Modes: Pick Your Flow

Praxis can be run in two main ways.

> **ℹ️ Recommendation:** We currently recommend **Browser Mode** for most users. It is the most **stable, rigorously tested, and actively developed** version of Praxis. Use Production Mode only if you require persistent database storage or specialized backend integration.

### Option A: Browser Mode (Recommended)

This mode runs entirely in your browser using Pyodide (WASM). No Python/Docker backend required.

1. Clone the repo: `git clone https://github.com/maraxen/praxis.git`
2. Install & Start:

   ```bash
   cd praxis/web-client
   bun install && bun run start:browser
   ```

3. Open <http://localhost:4200>. You're ready to go!

### Option B: Production / Full Stack Mode

This runs the full architecture with FastAPI, PostgreSQL, and Redis. Verification steps:

1. Follow the [Production Installation Guide](installation-production.md) to set up Docker and Python.
2. Start the Services:

   ```bash
   # Terminal 1: Backend
   export PRAXIS_DB_DSN="postgresql+asyncpg://postgres:postgres@localhost:5432/praxis_test"
   uv run uvicorn praxis.backend.main:app --reload --port 8000

   # Terminal 2: Frontend
   cd praxis/web-client && bun start
   ```

### 2. Sync Protocol Definitions

Praxis discovers protocols from Python files using AST parsing. Sync the built-in examples:

```bash
curl -X POST http://localhost:8000/api/v1/discovery/sync-all
```

Or use the UI: Navigate to **Protocols** and click **Sync**.

### 3. Run a Protocol

1. Open <http://localhost:4200>
2. Navigate to **Protocols** in the sidebar
3. Select a protocol (e.g., "Simple Transfer")
4. Click **Run Protocol**
5. Follow the 4-step wizard:
   - **Parameters**: Configure protocol inputs
   - **Resources**: Select plates, tips, reagents
   - **Machines**: Assign liquid handlers
   - **Review**: Confirm and execute

### 4. Monitor Execution

During execution:

- **Live logs** stream via WebSocket
- **Progress indicator** shows current step
- **Deck visualizer** shows labware positions
- **Control buttons** allow pause/resume/cancel

## Working with Assets

### Add a Machine

1. Navigate to **Assets** → **Machines** tab
2. Click **Add Machine**
3. Select a PLR definition (e.g., `opentrons.Flex`)
4. Configure connection info
5. Save

### Add Resources

1. Navigate to **Assets** → **Resources** tab
2. Click **Add Resource**
3. Select a type (Plate, TipRack, Reservoir)
4. Configure properties (consumable, quantity)
5. Save

### Hardware Discovery

Connect USB/serial devices automatically:

1. Navigate to **Assets** → **Machines** tab
2. Click **Discover Hardware**
3. Grant browser permissions for WebSerial/WebUSB
4. Select detected devices
5. Register as machines

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| <kbd>Cmd</kbd>+<kbd>K</kbd> | Command palette |
| <kbd>Alt</kbd>+<kbd>H</kbd> | Go to Home |
| <kbd>Alt</kbd>+<kbd>P</kbd> | Go to Protocols |
| <kbd>Alt</kbd>+<kbd>M</kbd> | Go to Machines |
| <kbd>Alt</kbd>+<kbd>R</kbd> | Go to Resources |
| <kbd>Alt</kbd>+<kbd>D</kbd> | Discover Hardware |

## Next Steps

- [Architecture Overview](../architecture/overview.md) - Understand the system design
- [User Guide: Protocols](../user-guide/protocols.md) - Deep dive into protocol management
- [API Reference](../api/rest-api.md) - Integrate with the REST API
