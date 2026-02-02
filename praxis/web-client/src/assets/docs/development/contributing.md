# Contributing

Thank you for your interest in contributing to Praxis! This guide covers how to set up your development environment and submit contributions.

## Development Setup

### Prerequisites

- Python 3.11+ (3.13 recommended)
- Node.js 20+
- Docker (for PostgreSQL and Redis)
- Git

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/maraxen/praxis.git
cd praxis

# Install Python dependencies
uv sync

# Install frontend dependencies
cd praxis/web-client
bun install
```

### Start Services

```bash
# Start database and Redis
docker compose up -d db redis

# Or use make
make db-test
```

### Run the Application

```bash
# Terminal 1: Backend
export PRAXIS_DB_DSN="postgresql+asyncpg://postgres:postgres@localhost:5432/praxis_test"
uv run uvicorn praxis.backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd praxis/web-client
bun start
```

## Code Standards

### Python

We use:
- **ruff** for linting and formatting
- **pyright/ty** for type checking
- **pytest** for testing

```bash
# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run ty check praxis/

# Test
uv run pytest
```

### TypeScript

We use:
- **ESLint** for linting
- **Prettier** for formatting (via ESLint)
- **Karma/Jasmine** for testing

```bash
cd praxis/web-client

# Lint
bun run lint

# Test
bun test

# Build
bun run build
```

## Git Workflow

### Branch Naming

```
feature/short-description
fix/issue-number-description
docs/what-is-documented
refactor/what-is-refactored
```

### Commit Messages

Use conventional commits:

```
type(scope): short description

Longer explanation if needed.

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Ensure tests pass
4. Submit a PR with clear description
5. Address review feedback
6. Squash and merge when approved

## Testing

### Backend Tests

```bash
# All tests
uv run pytest

# Specific file
uv run pytest tests/services/test_protocol_service.py

# With coverage
uv run pytest --cov=praxis --cov-report=html

# Only unit tests
uv run pytest -m unit
```

### Frontend Tests

```bash
cd praxis/web-client

# All tests
bun test

# Watch mode
bun test -- --watch

# Single run with coverage
bun test -- --code-coverage
```

### Test Categories

| Marker | Description |
|--------|-------------|
| `unit` | Fast, isolated tests |
| `integration` | Tests with database |
| `e2e` | End-to-end tests |
| `slow` | Tests taking >1s |

## Project Structure

```
praxis/
├── praxis/
│   ├── backend/
│   │   ├── api/           # FastAPI routes
│   │   ├── core/          # Execution engine
│   │   ├── services/      # Business logic
│   │   ├── models/        # ORM & Pydantic
│   │   └── utils/         # Utilities
│   └── web-client/
│       └── src/
│           ├── app/
│           │   ├── core/      # Services, guards
│           │   ├── features/  # Feature modules
│           │   └── shared/    # Shared components
│           └── assets/
├── tests/                 # Python tests
├── docs/                  # Documentation
└── external/             # External dependencies (PLR)
```

## Adding Features

### Backend Feature

1. **Model**: Add ORM model in `models/orm/`
2. **Schema**: Add Pydantic model in `models/pydantic/`
3. **Service**: Add service in `services/`
4. **Route**: Add API route in `api/routes/`
5. **Tests**: Add tests in `tests/`

### Frontend Feature

1. **Component**: Create in `features/{feature}/components/`
2. **Service**: Create in `features/{feature}/services/` or `core/services/`
3. **Route**: Add to `app.routes.ts`
4. **Tests**: Add `.spec.ts` alongside component

## Documentation

### Building Docs

```bash
# Install MkDocs
pip install mkdocs-material

# Serve locally
mkdocs serve

# Build
mkdocs build
```

### Adding Pages

1. Create markdown file in `docs/`
2. Add to `nav` in `mkdocs.yml`
3. Link from related pages

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release PR
4. Tag release after merge
5. GitHub Actions handles deployment

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/maraxen/praxis/issues)
- **Discussions**: [GitHub Discussions](https://github.com/maraxen/praxis/discussions)
- **Documentation**: [This site](https://maraxen.github.io/praxis/)

## Code of Conduct

Be respectful and constructive. We're all working toward the same goal of improving lab automation.
