# Installation

This guide covers installing Praxis for **Production Mode**, which is suitable for shared lab infrastructure, scheduled runs, and multi-user environments.

## Prerequisites

- **Python 3.11+** (3.13 recommended)
- **Node.js 20+** (for frontend)
- **PostgreSQL 15+** (for production database)
- **Redis 7+** (for task queue and state)
- **Docker** (optional, for containerized setup)

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

## Production Deployment

For production deployments, see the [Configuration](../reference/configuration.md) guide for:

- TLS/SSL setup
- Database connection pooling
- Redis clustering
- Keycloak authentication
- Load balancing
