# PyLabPraxis Frontend Development Setup

This guide helps you get the Angular frontend running with the Python backend API.

## Prerequisites

- **Node.js**: 20.x or higher
- **npm**: 11.x or higher
- **Python**: 3.10 or higher (for backend)
- **Docker**: Required for backend database (optional for frontend-only dev)

## Quick Start (Full Stack)

### 1. Start the Backend

From the project root:

```bash
# Start test database
make db-test

# Install Python dependencies
uv sync --extra test

# Run database migrations (if needed)
uv run alembic upgrade head

# Start backend API server
uv run uvicorn main:app --reload
```

The backend API will be available at `http://localhost:8000`

### 2. Start the Frontend

From the `praxis/web-client` directory:

```bash
# Install dependencies (first time only)
bun install

# Start development server
bun start
```

The frontend will be available at `http://localhost:4200`

## Development Features

### Proxy Configuration

The Angular dev server is configured with a proxy (`proxy.conf.json`) that routes:
- `/api/*` → `http://localhost:8000/api/*` (HTTP requests)
- `/ws/*` → `ws://localhost:8000/ws/*` (WebSocket connections)

This means you can use relative URLs in your Angular code:
```typescript
// This works because of the proxy
this.http.get('/api/v1/protocols')
```

### Environment Configuration

Environment files control API URLs for different deployment targets:

- **Development** (`src/environments/environment.ts`)
  - Uses relative URLs with proxy
  - WebSocket: `ws://localhost:8000/api/v1/ws`

- **Production** (`src/environments/environment.prod.ts`)
  - Uses relative URLs (assumes same-origin deployment)
  - WebSocket: Dynamically constructed from current host

## Authentication Flow

The app uses JWT-based authentication:

1. **Login**: User enters credentials on `/login`
2. **Backend**: Validates credentials, returns JWT token
3. **Storage**: Token stored in `localStorage`
4. **Injection**: `AuthInterceptor` automatically adds `Bearer ${token}` header to all requests
5. **Logout**: Calls backend `/api/v1/auth/logout`, clears localStorage

**Default Test User** (if backend has seed data):
- Username: `admin` or `test_user`
- Password: Check backend configuration

## Available Scripts

```bash
# Development server (with proxy)
bun start

# Build for production
bun run build

# Run unit tests
bun test

# Run e2e tests
bun run e2e

# Lint code
bun run lint
```

## Project Structure

```
praxis/web-client/
├── src/
│   ├── app/
│   │   ├── core/                   # Singletons (guards, interceptors, store)
│   │   │   ├── store/app.store.ts  # NgRx Signals state
│   │   │   ├── guards/             # Route guards
│   │   │   └── http/               # HTTP interceptors
│   │   ├── features/               # Feature modules
│   │   │   ├── auth/               # Login, auth service
│   │   │   ├── assets/             # Asset management
│   │   │   ├── protocols/          # Protocol library
│   │   │   ├── run-protocol/       # Protocol execution
│   │   │   └── ...
│   │   ├── layout/                 # App shell (sidebar, toolbar)
│   │   └── shared/                 # Shared components, pipes, directives
│   ├── environments/               # Environment configurations
│   └── styles.scss                 # Global styles
├── proxy.conf.json                 # Dev server proxy config
└── angular.json                    # Angular CLI config
```

## Common Issues

### Cannot connect to backend

**Problem**: Frontend shows network errors or 404s

**Solution**:
1. Verify backend is running: `curl http://localhost:8000/api/v1/protocols`
2. Check proxy.conf.json is correct
3. Restart Angular dev server: `bun start`

### Authentication not working

**Problem**: Login fails or token not sent

**Solution**:
1. Check backend logs for authentication errors
2. Verify `auth.interceptor.ts` is registered in `app.config.ts`
3. Clear localStorage: `localStorage.clear()` in browser console
4. Check backend user exists and password is correct

### WebSocket connection fails

**Problem**: Live dashboard not updating

**Solution**:
1. Verify WebSocket URL in environment files
2. Check backend WebSocket handler is running
3. Verify proxy.conf.json includes WebSocket config (`"ws": true`)

## API Endpoints Reference

### Authentication
- `POST /api/v1/auth/login` - Login with username/password
- `POST /api/v1/auth/logout` - Logout (clears session)
- `GET /api/v1/auth/me` - Get current user info

### Assets
- `GET /api/v1/machines` - List machines
- `POST /api/v1/machines` - Create machine
- `DELETE /api/v1/machines/{id}` - Delete machine
- `GET /api/v1/resources` - List resources
- `POST /api/v1/resources` - Create resource
- `DELETE /api/v1/resources/{id}` - Delete resource

### Protocols
- `GET /api/v1/protocols` - List protocols
- `POST /api/v1/protocols/upload` - Upload protocol file

### Protocol Execution
- `POST /api/v1/runs` - Start protocol run
- `POST /api/v1/runs/{id}/stop` - Stop protocol run
- `WS /api/v1/ws/execution/{run_id}` - Live execution updates

## Testing

### Unit Tests (Vitest)
```bash
bun test
```

### E2E Tests (Playwright)
```bash
# Run e2e tests
bun run e2e

# Run e2e tests in UI mode
npx playwright test --ui
```

## Production Build

```bash
# Build for production
bun run build

# Output will be in dist/web-client/browser/
```

Serve with any static file server or integrate with backend static file serving.

## Need Help?

- **Frontend Issues**: Check `.agent/FRONTEND_STATUS.md`
- **Backend Issues**: Check `.agent/BACKEND_STATUS.md`
- **Architecture**: Check `.agent/ANGULAR_FRONTEND_ROADMAP.md`
