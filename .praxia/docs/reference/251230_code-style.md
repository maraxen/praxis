# Code Style Guide

Coding conventions and style guidelines for Praxis.

## Python

### Formatting

We use **ruff** for formatting:

```bash
uv run ruff format .
```

Configuration in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Linting

```bash
uv run ruff check .
uv run ruff check --fix .  # Auto-fix
```

### Type Hints

All code should be fully typed:

```python
# Good
async def get_machine(session: AsyncSession, machine_id: str) -> Machine:
    ...

# Bad
async def get_machine(session, machine_id):
    ...
```

Use `ty` for type checking:

```bash
uv run ty check praxis/
```

### Imports

Organize imports in groups:
1. Standard library
2. Third-party
3. Local

```python
import asyncio
from datetime import datetime
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models import MachineOrm
from praxis.backend.services import machine_service
```

### Docstrings

Use Google-style docstrings:

```python
async def execute_protocol(
    protocol_id: str,
    params: dict[str, Any],
    simulation: bool = False
) -> ProtocolRun:
    """Execute a protocol with the given parameters.

    Args:
        protocol_id: The unique identifier of the protocol to execute.
        params: Parameter values for the protocol.
        simulation: If True, run in simulation mode without hardware.

    Returns:
        The completed protocol run record.

    Raises:
        ProtocolNotFoundError: If the protocol doesn't exist.
        AssetUnavailableError: If required assets are not available.
    """
    ...
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Variables | snake_case | `machine_id` |
| Functions | snake_case | `get_machine()` |
| Classes | PascalCase | `MachineService` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Private | _prefix | `_internal_method()` |
| Modules | snake_case | `protocol_service.py` |

### Async/Await

Always use `async`/`await` for I/O operations:

```python
# Good
async def fetch_data():
    result = await db.execute(query)
    return result.scalars().all()

# Bad - blocking I/O in async context
async def fetch_data():
    result = db.execute(query)  # Missing await!
    return result.scalars().all()
```

## TypeScript

### Formatting

ESLint with Prettier rules handles formatting:

```bash
cd praxis/web-client
bun run lint
bun run lint -- --fix  # Auto-fix
```

### Type Safety

Use strict TypeScript:

```typescript
// Good
function getMachine(id: string): Machine | undefined {
  return this.machines().find(m => m.id === id);
}

// Bad - any types
function getMachine(id: any): any {
  return this.machines().find((m: any) => m.id === id);
}
```

### Angular Conventions

**Components:**

```typescript
@Component({
  selector: 'app-machine-card',  // Prefix with 'app-'
  standalone: true,
  imports: [...],
  template: `...`,
  styles: [`...`]
})
export class MachineCardComponent {
  // Inputs first
  @Input({ required: true }) machine!: Machine;

  // Outputs next
  @Output() select = new EventEmitter<Machine>();

  // Injected services
  private readonly assetService = inject(AssetService);

  // Signals
  readonly isHovered = signal(false);

  // Computed
  readonly statusColor = computed(() => ...);

  // Methods
  onSelect(): void {
    this.select.emit(this.machine);
  }
}
```

**Services:**

```typescript
@Injectable({ providedIn: 'root' })
export class AssetService {
  private readonly http = inject(HttpClient);

  // Public methods for external use
  getMachines(): Observable<Machine[]> {
    return this.http.get<{ items: Machine[] }>('/api/v1/machines')
      .pipe(map(response => response.items));
  }

  // Private methods for internal logic
  private transformResponse(data: ApiResponse): Machine[] {
    ...
  }
}
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Variables | camelCase | `machineId` |
| Functions | camelCase | `getMachine()` |
| Classes | PascalCase | `MachineService` |
| Interfaces | PascalCase | `Machine` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Files | kebab-case | `machine-list.component.ts` |

### RxJS

Prefer signals for simple state, RxJS for complex streams:

```typescript
// Signals for component state
readonly searchQuery = signal('');
readonly loading = signal(false);

// RxJS for HTTP and complex operations
getMachines(): Observable<Machine[]> {
  return this.http.get<Machine[]>('/api/v1/machines').pipe(
    retry(3),
    catchError(this.handleError)
  );
}
```

## CSS/SCSS

### Naming

Use BEM-like naming:

```scss
.machine-card {
  &__header { ... }
  &__body { ... }
  &__footer { ... }

  &--selected { ... }
  &--disabled { ... }
}
```

### Variables

Use CSS custom properties for theming:

```scss
:root {
  --color-primary: #3f51b5;
  --color-success: #4caf50;
  --spacing-unit: 8px;
}

.button {
  background: var(--color-primary);
  padding: calc(var(--spacing-unit) * 2);
}
```

### Responsive Design

Use Material breakpoints:

```scss
@use '@angular/material' as mat;

.container {
  padding: 16px;

  @include mat.breakpoints.up('md') {
    padding: 24px;
  }

  @include mat.breakpoints.up('lg') {
    padding: 32px;
  }
}
```

## Git

### Commit Messages

```
type(scope): short description

Longer explanation if needed.

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code change (no new feature or fix)
- `test`: Adding tests
- `chore`: Maintenance

### Branch Names

```
feature/add-hardware-discovery
fix/123-machine-connection-error
docs/update-api-reference
refactor/simplify-asset-service
```

## File Organization

### Python Modules

```python
# mymodule.py

"""Module docstring explaining purpose."""

# Imports
from typing import Any

# Constants
DEFAULT_TIMEOUT = 30

# Exceptions
class MyError(Exception):
    """Custom exception."""

# Classes
class MyClass:
    """Class docstring."""

# Functions
def my_function():
    """Function docstring."""
```

### TypeScript Modules

```typescript
// my-component.component.ts

// Angular imports
import { Component, inject } from '@angular/core';

// Third-party imports
import { Observable } from 'rxjs';

// Local imports
import { Machine } from '../../models/machine.model';

// Types/Interfaces
interface ComponentState {
  loading: boolean;
}

// Component
@Component({...})
export class MyComponent {
  ...
}
```
