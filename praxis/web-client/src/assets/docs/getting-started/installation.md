# Installation

This guide covers installing Praxis for development or production use.

## Prerequisites

- **Python 3.11+** (3.13 recommended)
- **Node.js 20+** (for frontend)
- **PostgreSQL 15+** (for production)
- **Redis 7+** (for task queue and state)
- **Docker** (optional, for containerized setup)

## Application Modes Selection

Choosing the right mode depends on your use case:

| Mode | Use Case | Installation Effort |
|------|----------|---------------------|
| **Browser Mode** | Direct hardware control from laptop, single-user research, portability. | **Minimal** (Browser only) |
| **Production Mode** | Shared lab infrastructure, scheduled runs, multi-user environments. | **Full** (Python + Postgres + Redis) |
| **Browser Mode** | Software evaluation, UI testing, presentations. | **None** (Online Demo) |

## Browser Mode (Recommended for Local Use)

Browser mode allows you to run Praxis entirely within your web browser. It uses Pyodide to run the Python logic and WebSerial/WebUSB to talk to your hardware. No backend installation is required beyond hosting the frontend.

### To run locally

1. Ensure you have Node.js 20+ installed.
2. Clone the repo and install frontend dependencies:

   ```bash
   git clone https://github.com/maraxen/praxis.git
   cd praxis/praxis/web-client
   bun install
   ```

3. Start the dev server in browser configuration:

   ```bash
   bun run start:browser
   ```

4. Open <http://localhost:4200>. You are now running in **Browser Mode**.

## Production Mode Installation (Full Stack)

### 1. Clone the Repository

```bash
git clone https://github.com/maraxen/praxis.git
cd praxis
```

### 2. Install Python Dependencies

Praxis uses [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### 3. Install Frontend Dependencies

```bash
cd praxis/web-client
bun install
```

### 4. Configure Environment

Create a `.env` file in the project root:

```bash
# Database
PRAXIS_DB_DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/praxis

# Redis
REDIS_URL=redis://localhost:6379/0

# Security (generate a secure key)
SECRET_KEY=your-secret-key-here

# Optional: Keycloak authentication
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=praxis
KEYCLOAK_CLIENT_ID=praxis-web
```

### 5. Start Services

=== "Docker Compose"

    ```bash
    # Start PostgreSQL and Redis
    docker compose up -d db redis

    # Run migrations
    uv run alembic upgrade head

    # Start backend
    uv run uvicorn praxis.backend.main:app --reload --port 8000

    # In another terminal, start frontend
    cd praxis/web-client && bun start
    ```

=== "Make Commands"

    ```bash
    # Start test database
    make db-test

    # Start backend (set DB DSN first)
    export PRAXIS_DB_DSN="postgresql+asyncpg://postgres:postgres@localhost:5432/praxis_test"
    uv run uvicorn praxis.backend.main:app --reload --port 8000

    # Start frontend
    cd praxis/web-client && bun start
    ```

## Verify Installation

1. Open <http://localhost:4200> in your browser
2. You should see the Praxis dashboard
3. Check the backend health: `curl http://localhost:8000/health`

## Browser Mode (No Backend Required)

For quick demonstrations without setting up the backend:

```bash
cd praxis/web-client
bun run start:browser
```

This runs the frontend with mock data - perfect for demos or UI development.

## Production Deployment

For production deployments, see the [Configuration](../reference/configuration.md) guide for:

- TLS/SSL setup
- Database connection pooling
- Redis clustering
- Keycloak authentication
- Load balancing

## Troubleshooting

### Common Issues

**Database connection failed**
: Ensure PostgreSQL is running and the DSN is correct. Check firewall rules.

**Redis connection refused**
: Verify Redis is running: `redis-cli ping` should return `PONG`.

**Frontend build errors**
: Clear node_modules and reinstall: `rm -rf node_modules && bun install`

**Import errors for PyLabRobot**
: Ensure you're running commands with `uv run` to use the correct virtualenv.

See [Troubleshooting](../reference/troubleshooting.md) for more solutions.
