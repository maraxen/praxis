# Troubleshooting

Solutions to common issues in Praxis.

## Installation Issues

### Python dependency conflicts

**Symptom:** `uv sync` fails with version conflicts.

**Solution:**

```bash
# Clear cache and reinstall
rm -rf .venv
uv sync
```

### Node.js version mismatch

**Symptom:** bun install fails or Angular CLI errors.

**Solution:**

```bash
# Use Node 20+
nvm install 20
nvm use 20

# Clear and reinstall
rm -rf node_modules package-lock.json
bun install
```

### PyLabRobot import errors

**Symptom:** `ModuleNotFoundError: No module named 'pylabrobot'`

**Solution:**

```bash
# Ensure using uv environment
uv run python -c "import pylabrobot"

# If still failing, check external directory
ls external/pylabrobot
```

## Database Issues

### Connection refused

**Symptom:** `ConnectionRefusedError: [Errno 111] Connection refused`

**Cause:** PostgreSQL not running or wrong port.

**Solution:**

```bash
# Start database
docker compose up -d praxis-db

# Check it's running
docker ps | grep postgres

# Verify connection
psql -h localhost -U postgres -d praxis -c "SELECT 1"
```

### Migration errors

**Symptom:** `alembic.util.exc.CommandError: Can't locate revision`

**Solution:**

```bash
# Reset alembic
uv run alembic stamp head
uv run alembic upgrade head

# If still failing, recreate database
docker compose down -v
docker compose up -d praxis-db
uv run alembic upgrade head
```

### Database locked

**Symptom:** `OperationalError: database is locked` (SQLite only)

**Solution:** SQLite doesn't support concurrent writes. Use PostgreSQL for multi-user scenarios.

## Redis Issues

### Connection error

**Symptom:** `redis.exceptions.ConnectionError: Error connecting to redis://localhost:6379`

**Solution:**

```bash
# Start Redis
docker compose up -d redis

# Test connection
redis-cli ping  # Should return PONG
```

### Celery not receiving tasks

**Symptom:** Tasks queued but never executed.

**Solution:**

```bash
# Check worker is running
uv run celery -A praxis.backend.celery status

# Check broker connection
uv run celery -A praxis.backend.celery inspect ping

# Restart worker
pkill -f "celery worker"
uv run celery -A praxis.backend.celery worker --loglevel=debug
```

## Frontend Issues

### Blank page

**Symptom:** App loads but shows blank screen.

**Solution:**

1. Check browser console for errors (F12)
2. Verify API is running: `curl http://localhost:8000/health`
3. Check CORS settings if API errors

### API calls failing

**Symptom:** Network errors in browser console.

**Solution:**

```bash
# Check backend is running
curl http://localhost:8000/health

# Verify environment.ts has correct apiUrl
cat praxis/web-client/src/environments/environment.ts
```

### WebSocket not connecting

**Symptom:** Real-time updates not working, console shows WebSocket errors.

**Solution:**

1. Verify WebSocket URL in environment
2. Check for proxy issues (nginx, load balancer)
3. Ensure backend WebSocket route is enabled

### Build errors

**Symptom:** `bun run build` fails.

**Solution:**

```bash
# Clear caches
rm -rf node_modules/.cache
rm -rf dist

# Reinstall dependencies
bun install

# Rebuild
bun run build
```

## Hardware Discovery Issues

### No devices found

**Symptom:** Hardware discovery shows no devices.

**Cause:** Browser permissions, physical connection, or browser support.

**Solutions:**

1. Ensure using Chromium-based browser (Chrome, Edge)
2. Check physical USB/serial connections
3. Try different USB port or cable
4. Clear site permissions and retry

### Permission denied

**Symptom:** "Permission denied" when accessing device.

**Solution:**

```bash
# Linux: Add user to dialout group
sudo usermod -a -G dialout $USER
# Logout and login again

# macOS: Should work with standard permissions
```

### Device not recognized as PLR type

**Symptom:** Device appears but shows "Unknown" type.

**Solution:**

1. Check if device is supported by PyLabRobot
2. Manually select the correct FQN when registering
3. Check device USB VID/PID against known devices

## Protocol Execution Issues

### Protocol not found

**Symptom:** Protocol exists but execution fails with "not found."

**Solution:**

```bash
# Sync protocols
curl -X POST http://localhost:8000/api/v1/discovery/sync-protocols

# Check protocol is in database
curl http://localhost:8000/api/v1/protocols | jq
```

### Asset unavailable

**Symptom:** "AssetUnavailableError: Machine X is in use"

**Solutions:**

1. Check if another run is using the asset
2. Verify asset status: `curl http://localhost:8000/api/v1/machines/{id}`
3. Cancel stuck runs if any
4. Manually reset asset status if needed

### Timeout during execution

**Symptom:** Protocol hangs, eventually times out.

**Causes:**

- Hardware not responding
- Network issues
- Deadlock in protocol code

**Solutions:**

1. Check hardware connections
2. Enable simulation mode to test logic
3. Add logging to identify stuck point
4. Cancel run and investigate

## Performance Issues

### Slow API responses

**Symptom:** API calls take several seconds.

**Solutions:**

1. Check database query performance:

   ```sql
   EXPLAIN ANALYZE SELECT * FROM protocols;
   ```

2. Add missing indexes
3. Increase database connection pool size
4. Enable query caching

### High memory usage

**Symptom:** Backend using excessive memory.

**Solutions:**

1. Check for memory leaks in long-running processes
2. Reduce Celery worker concurrency
3. Enable garbage collection logging
4. Profile with `memory_profiler`

### Slow frontend

**Symptom:** UI is sluggish, especially with large lists.

**Solutions:**

1. Enable virtual scrolling for long lists
2. Use `trackBy` in `*ngFor` loops
3. Check for unnecessary re-renders
4. Profile with Chrome DevTools

## Logging and Debugging

### Enable debug logging

```bash
# Backend
export LOG_LEVEL=DEBUG
uv run uvicorn praxis.backend.main:app --reload

# Frontend
# Open Chrome DevTools > Console
# Enable "Verbose" log level
```

### View Celery task logs

```bash
# Worker logs
uv run celery -A praxis.backend.celery worker --loglevel=debug

# Specific task
uv run celery -A praxis.backend.celery call praxis.tasks.execute --args='["run-id"]'
```

### Database query logging

```python
# Add to backend config
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
```

## Getting Help

If you're still stuck:

1. **Check existing issues:** [GitHub Issues](https://github.com/maraxen/praxis/issues)
2. **Search discussions:** [GitHub Discussions](https://github.com/maraxen/praxis/discussions)
3. **Open new issue:** Include:
   - Error message (full traceback)
   - Steps to reproduce
   - Environment details (OS, Python version, etc.)
   - Relevant logs
