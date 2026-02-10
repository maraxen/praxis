# Configuration

Praxis is configured through environment variables and configuration files.

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `PRAXIS_DB_DSN` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing key | Random 32+ character string |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `PRAXIS_ENV` | `development` | Environment: development, staging, production |
| `LOG_LEVEL` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:4200` | Allowed CORS origins (comma-separated) |
| `API_PREFIX` | `/api/v1` | API route prefix |

### Authentication

| Variable | Description |
|----------|-------------|
| `KEYCLOAK_URL` | Keycloak server URL |
| `KEYCLOAK_REALM` | Keycloak realm name |
| `KEYCLOAK_CLIENT_ID` | OAuth client ID |
| `KEYCLOAK_CLIENT_SECRET` | OAuth client secret (if confidential client) |

### Celery

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `REDIS_URL` | Celery message broker |
| `CELERY_RESULT_BACKEND` | `REDIS_URL` | Task result storage |
| `CELERY_TASK_TIMEOUT` | `3600` | Default task timeout (seconds) |

### Protocol Discovery

| Variable | Default | Description |
|----------|---------|-------------|
| `PROTOCOL_DIRS` | `./protocols` | Protocol search directories (comma-separated) |
| `PROTOCOL_PATTERNS` | `*.py` | File patterns to scan |

## praxis.ini

The primary configuration file for backend settings. Located at the project root.

```ini
[output_directories]
protocol_output = "./protocol_output"

[protocol_directories]
default_directory = ./praxis/protocol/protocols
additional_directories = ["./test_protocols"]

[database]
host = localhost
port = 5433
praxis_dsn = postgresql://praxis:praxis@localhost:5433/praxis_db
keycloak_dsn = postgresql://keycloak:keycloak@localhost:5432/keycloak

[redis]
host = localhost
port = 6379
db = 0

[celery]
broker = redis://localhost:6379/0
backend = redis://localhost:6379/0

[logging]
level = INFO
logfile = logs/praxis.log

[baseline_decks]
liquid_handler_1 = "/path/to/baseline/deck_1.json"
liquid_handler_2 = "/path/to/baseline/deck_2.json"

[admin]
username = admin
password = admin  ; Change this to a strong password

[app]
url = http://localhost:5137

[keycloak]
server_url = http://localhost:8080
realm_name = praxis
client_id = praxis-client
client_secret = <your-client-secret>
```

## Configuration Files

### pyproject.toml

Project metadata and tool configuration:

```toml
[project]
name = "praxis"
version = "0.1.0"

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = ["--cov=praxis"]

[tool.ruff]
line-length = 120
```

### angular.json

Frontend build configuration:

```json
{
  "projects": {
    "web-client": {
      "architect": {
        "build": {
          "configurations": {
            "production": {
              "fileReplacements": [{
                "replace": "src/environments/environment.ts",
                "with": "src/environments/environment.prod.ts"
              }]
            },
            "demo": {
              "fileReplacements": [{
                "replace": "src/environments/environment.ts",
                "with": "src/environments/environment.browser.ts"
              }]
            }
          }
        }
      }
    }
  }
}
```

### Environment Files (Frontend)

```typescript
// environment.ts (development)
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1',
  wsUrl: 'ws://localhost:8000',
  demoMode: false
};

// environment.prod.ts
export const environment = {
  production: true,
  apiUrl: '/api/v1',
  wsUrl: '',  // Relative WebSocket
  demoMode: false
};

// environment.browser.ts
export const environment = {
  production: false,
  apiUrl: '/api/v1',
  wsUrl: '',
  demoMode: true
};
```

## Docker Configuration

### docker-compose.yml

```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: praxis
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: praxis
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: .
    environment:
      - PRAXIS_DB_DSN=postgresql+asyncpg://praxis:${DB_PASSWORD}@db:5432/praxis
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis

  celery:
    build: .
    command: celery -A praxis.backend.celery worker --loglevel=info
    environment:
      - PRAXIS_DB_DSN=postgresql+asyncpg://praxis:${DB_PASSWORD}@db:5432/praxis
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

### .env.example

```bash
# Database
DB_PASSWORD=secure_password_here
PRAXIS_DB_DSN=postgresql+asyncpg://praxis:${DB_PASSWORD}@localhost:5432/praxis

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=generate_a_secure_random_key_here

# Optional: Keycloak
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=praxis
KEYCLOAK_CLIENT_ID=praxis-web

# Optional: Logging
LOG_LEVEL=INFO
```

## Database Configuration

### Alembic (Migrations)

```ini
# alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]
hooks = ruff
ruff.type = exec
ruff.executable = ruff
ruff.options = format REVISION_SCRIPT_FILENAME
```

### Connection Pool

```python
# praxis/backend/db/config.py
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    settings.db_dsn,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)
```

## Logging Configuration

```python
# praxis/backend/utils/logging.py
import logging
from logging.config import dictConfig

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "DEBUG"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/praxis.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json"
        }
    },
    "loggers": {
        "praxis": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"]
        }
    }
}

dictConfig(LOGGING_CONFIG)
```

## Feature Flags

```python
# praxis/backend/config/features.py
from pydantic_settings import BaseSettings

class FeatureFlags(BaseSettings):
    enable_scheduling: bool = True
    enable_hardware_discovery: bool = True
    enable_demo_data: bool = False

    class Config:
        env_prefix = "FEATURE_"

features = FeatureFlags()
```

Usage:

```python
from praxis.backend.config.features import features

if features.enable_scheduling:
    # Enable scheduling endpoints
    app.include_router(scheduling_router)
```

## Production Considerations

### Security

```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set secure headers
export CORS_ORIGINS="https://your-domain.com"
```

### Performance

```bash
# Increase worker count for production
uvicorn main:app --workers 4

# Or use Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Monitoring

```bash
# Enable Prometheus metrics
export ENABLE_METRICS=true

# Configure Sentry
export SENTRY_DSN=https://...@sentry.io/...
```
