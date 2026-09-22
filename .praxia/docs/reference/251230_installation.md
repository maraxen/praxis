# Installation Overview

Praxis can be deployed in several ways depending on your needs. Choose the mode that best fits your environment.

<div class="grid cards" markdown>

- :material-application-braces:{ .lg .middle } **Browser Mode**

    ---

    Zero setup. Runs entirely in your browser using Pyodide and WebSerial/WebUSB. Perfect for portability and quick research.

    [:octicons-arrow-right-24: Browser Installation](installation-browser.md)

- :material-server:{ .lg .middle } **Production Mode**

    ---

    Full stack with PostgreSQL, Redis, and Celery. Best for shared lab infrastructure and scheduled protocols.

    [:octicons-arrow-right-24: Production Installation](installation-production.md)

- :material-lightning-bolt:{ .lg .middle } **Lite Mode**

    ---

    Local development mode using SQLite and in-memory stores. No Docker required. Ideal for rapid development and testing.

    [:octicons-arrow-right-24: Lite Installation](installation-lite.md)

</div>

## Comparison

| Feature | Browser Mode | Production Mode | Lite Mode |
|---------|--------------|-----------------|-----------|
| **Setup Effort** | Minimal | High | Medium |
| **Backend** | None (Pyodide) | FastAPI | FastAPI |
| **Database** | SQLite (In-Memory) | PostgreSQL | SQLite (File) |
| **Task Queue** | In-Memory | Redis + Celery | In-Memory |
| **Persistence** | Session-only | Full | Full (File) |
| **Hardware Access** | WebSerial/WebUSB | OS-Level Drivers | OS-Level Drivers |
| **Docker Required** | No | Recommended | No |
