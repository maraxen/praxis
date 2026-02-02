# CLI Commands

Common commands for development and operations.

## Development

### Start Services

```bash
# Start test database
make db-test

# Or with Docker Compose
docker compose up -d db redis
```

### Run Backend

```bash
# With auto-reload
export PRAXIS_DB_DSN="postgresql+asyncpg://postgres:postgres@localhost:5432/praxis"
uv run uvicorn praxis.backend.main:app --reload --port 8000

# Production mode
uv run uvicorn praxis.backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Run Frontend

```bash
cd praxis/web-client

# Development
bun start

# Demo mode
bun run start:browser

# Production build
bun run build
```

### Run Celery Worker

```bash
# Start worker
uv run celery -A praxis.backend.celery worker --loglevel=info

# With concurrency
uv run celery -A praxis.backend.celery worker --concurrency=4

# Flower monitoring
uv run celery -A praxis.backend.celery flower
```

## Testing

### Backend Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=praxis --cov-report=html

# Specific markers
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m "not slow"

# Specific test
uv run pytest tests/services/test_protocol_service.py::test_create
```

### Frontend Tests

```bash
cd praxis/web-client

# All tests
bun test

# Watch mode
bun test -- --watch

# Coverage
bun test -- --code-coverage
```

## Linting & Formatting

### Python

```bash
# Check
uv run ruff check .

# Fix
uv run ruff check --fix .

# Format
uv run ruff format .

# Type check
uv run ty check praxis/
```

### TypeScript

```bash
cd praxis/web-client

# Lint
bun run lint

# Fix
bun run lint -- --fix
```

## Database

### Migrations

```bash
# Create migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one
uv run alembic downgrade -1

# Show history
uv run alembic history
```

### Reset Database

```bash
# Drop and recreate
uv run alembic downgrade base
uv run alembic upgrade head
```

## Protocol Discovery

### Sync Protocols

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/discovery/sync-all

# Sync specific
curl -X POST http://localhost:8000/api/v1/discovery/sync-protocols
curl -X POST http://localhost:8000/api/v1/discovery/sync-machines
curl -X POST http://localhost:8000/api/v1/discovery/sync-resources
```

## Documentation

### Build Docs

```bash
# Install MkDocs
pip install mkdocs-material

# Serve locally
mkdocs serve

# Build static site
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy
```

## Docker

### Build

```bash
# Build backend image
docker build -t praxis-backend .

# Build frontend image
docker build -t praxis-frontend -f praxis/web-client/Dockerfile praxis/web-client
```

### Run

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f backend

# Stop
docker compose down

# Stop and remove volumes
docker compose down -v
```

## Debugging

### Backend

```bash
# Run with debugger
python -m debugpy --listen 5678 -m uvicorn praxis.backend.main:app --reload

# Or with VS Code launch.json
```

### Database Queries

```bash
# Connect to database
docker exec -it praxis_db psql -U postgres -d praxis

# Common queries
SELECT * FROM protocols LIMIT 10;
SELECT * FROM machines WHERE status = 'IDLE';
```

### Redis

```bash
# Connect to Redis CLI
docker exec -it praxis_redis redis-cli

# Common commands
KEYS praxis:*
GET praxis:run:xyz:status
```

## Makefile Targets

Common targets in `Makefile`:

```makefile
.PHONY: dev test lint build

dev:
	docker compose up -d db redis
	uv run uvicorn praxis.backend.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check .
	cd praxis/web-client && bun run lint

build:
	cd praxis/web-client && bun run build

db-test:
	docker run -d --name praxis_test_db \
		-e POSTGRES_PASSWORD=postgres \
		-p 5432:5432 postgres:15

clean:
	docker compose down -v
	rm -rf .pytest_cache htmlcov
	cd praxis/web-client && rm -rf dist node_modules
```

## Environment Shortcuts

Add to your shell profile (`.bashrc` or `.zshrc`):

```bash
# Praxis aliases
alias praxis-backend='cd ~/projects/praxis && PRAXIS_DB_DSN="postgresql+asyncpg://postgres:postgres@localhost:5432/praxis" uv run uvicorn praxis.backend.main:app --reload'
alias praxis-frontend='cd ~/projects/praxis/praxis/web-client && bun start'
alias praxis-test='cd ~/projects/praxis && uv run pytest'
alias praxis-sync='curl -X POST http://localhost:8000/api/v1/discovery/sync-all'
```
