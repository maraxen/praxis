# Production Mode Installation

Production Mode is designed for shared lab environments, multi-user access, and long-running scheduled protocols. It uses a full stack with a dedicated API server and persistent databases.

## Prerequisites

- **Python 3.11+** (3.12 recommended)
- **Node.js 20+**
- **Docker & Docker Compose**
- **PostgreSQL 15+**
- **Redis 7+**

## Quick Start (Docker Compose)

The easiest way to run the full stack is using Docker Compose:

1. **Clone the Repository**

   ```bash
   git clone https://github.com/maraxen/praxis.git
   cd praxis
   ```

2. **Start Infrastructure**

   ```bash
   docker compose up -d db redis
   ```

3. **Setup Python Environment**

   ```bash
   uv sync
   uv run alembic upgrade head
   ```

4. **Start Backend**

   ```bash
   uv run uvicorn main:app --reload --port 8000
   ```

5. **Start Frontend**

   ```bash
   cd praxis/web-client
   bun install
   bun start
   ```

6. **Access Praxis**
   Open [http://localhost:4200](http://localhost:4200).

## Environment Configuration

Create a `.env` file in the root directory to customize your setup:

```properties
# Database
PRAXIS_DB_DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/praxis

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secure-secret-key
```

## When to use Production Mode

- **Persistence**: All protocol runs and states are stored in PostgreSQL.
- **Concurrency**: Multiple users can interact with the system simultaneously.
- **Scheduling**: Support for Celery-based task scheduling for background runs.
- **Shared Access**: Run Praxis as a central hub for your laboratory.
