# Testing Guide

Comprehensive guide to testing in Praxis.

## Overview

Praxis uses a layered testing strategy:

| Layer | Framework | Purpose |
|-------|-----------|---------|
| Unit | pytest / Jasmine | Isolated component tests |
| Integration | pytest | Database and service tests |
| E2E | Playwright (planned) | Full stack tests |

## Backend Testing

### Setup

Tests require a test database:

```bash
# Start test database
make db-test

# Or manually
docker run -d \
  --name praxis_test_db \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15
```

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=praxis --cov-report=html

# Specific tests
uv run pytest tests/services/test_protocol_service.py
uv run pytest tests/api/test_machines.py::test_create_machine

# By marker
uv run pytest -m unit           # Only unit tests
uv run pytest -m "not slow"     # Skip slow tests
uv run pytest -m integration    # Only integration tests
```

### Test Structure

```python
# tests/services/test_protocol_service.py

import pytest
from praxis.backend.services import protocol_service
from praxis.backend.models.pydantic import ProtocolCreate

@pytest.fixture
async def sample_protocol(db_session):
    """Create a sample protocol for testing."""
    return await protocol_service.create(
        db_session,
        ProtocolCreate(
            name="Test Protocol",
            source_path="/test/path.py"
        )
    )

class TestProtocolService:
    @pytest.mark.asyncio
    async def test_create_protocol(self, db_session):
        """Test creating a new protocol."""
        protocol = await protocol_service.create(
            db_session,
            ProtocolCreate(
                name="New Protocol",
                source_path="/protocols/new.py"
            )
        )

        assert protocol.id is not None
        assert protocol.name == "New Protocol"

    @pytest.mark.asyncio
    async def test_get_protocol(self, db_session, sample_protocol):
        """Test retrieving a protocol by ID."""
        protocol = await protocol_service.get(db_session, sample_protocol.id)

        assert protocol.name == sample_protocol.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_protocol(self, db_session):
        """Test that getting a nonexistent protocol raises an error."""
        with pytest.raises(EntityNotFoundError):
            await protocol_service.get(db_session, "nonexistent-id")
```

### Fixtures

Common fixtures in `conftest.py`:

```python
# tests/conftest.py

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

@pytest.fixture
async def db_session():
    """Provide a database session for testing."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def mock_workcell_runtime():
    """Mock WorkcellRuntime for testing."""
    runtime = Mock(spec=WorkcellRuntime)
    runtime.get_machine.return_value = MockMachine()
    return runtime
```

### Mocking

```python
from unittest.mock import Mock, patch, AsyncMock

@pytest.mark.asyncio
async def test_execute_protocol(db_session):
    """Test protocol execution with mocked hardware."""
    with patch('praxis.backend.core.workcell_runtime.WorkcellRuntime') as mock_runtime:
        mock_runtime.return_value.get_machine = AsyncMock(return_value=MockMachine())

        result = await orchestrator.execute(protocol, params)

        assert result.status == RunStatus.COMPLETED
        mock_runtime.return_value.get_machine.assert_called_once()
```

### API Testing

```python
# tests/api/test_protocols.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_protocols(client: AsyncClient, sample_protocols):
    """Test listing protocols via API."""
    response = await client.get("/api/v1/protocols")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == len(sample_protocols)

@pytest.mark.asyncio
async def test_create_protocol(client: AsyncClient):
    """Test creating a protocol via API."""
    response = await client.post(
        "/api/v1/protocols",
        json={
            "name": "API Test Protocol",
            "source_path": "/test/api.py"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API Test Protocol"
```

## Frontend Testing

### Setup

```bash
cd praxis/web-client
bun install
```

### Running Tests

```bash
# All tests
bun test

# Watch mode
bun test -- --watch

# Single run with coverage
bun test -- --code-coverage

# Specific file
bun test -- --include=**/machine-list.component.spec.ts
```

### Component Testing

```typescript
// machine-list.component.spec.ts

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MachineListComponent } from './machine-list.component';
import { AssetService } from '../../services/asset.service';
import { of } from 'rxjs';

describe('MachineListComponent', () => {
  let component: MachineListComponent;
  let fixture: ComponentFixture<MachineListComponent>;
  let mockAssetService: jasmine.SpyObj<AssetService>;

  const mockMachines = [
    { id: '1', name: 'Machine 1', status: 'IDLE' },
    { id: '2', name: 'Machine 2', status: 'RUNNING' }
  ];

  beforeEach(async () => {
    mockAssetService = jasmine.createSpyObj('AssetService', ['getMachines']);
    mockAssetService.getMachines.and.returnValue(of(mockMachines));

    await TestBed.configureTestingModule({
      imports: [MachineListComponent],
      providers: [
        { provide: AssetService, useValue: mockAssetService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(MachineListComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load machines on init', () => {
    fixture.detectChanges();
    expect(mockAssetService.getMachines).toHaveBeenCalled();
    expect(component.machines()).toEqual(mockMachines);
  });

  it('should display machine cards', () => {
    fixture.detectChanges();
    const cards = fixture.nativeElement.querySelectorAll('app-machine-card');
    expect(cards.length).toBe(2);
  });
});
```

### Service Testing

```typescript
// asset.service.spec.ts

import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { AssetService } from './asset.service';

describe('AssetService', () => {
  let service: AssetService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AssetService]
    });

    service = TestBed.inject(AssetService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should fetch machines', () => {
    const mockMachines = [{ id: '1', name: 'Test' }];

    service.getMachines().subscribe(machines => {
      expect(machines).toEqual(mockMachines);
    });

    const req = httpMock.expectOne('/api/v1/machines');
    expect(req.request.method).toBe('GET');
    req.flush({ items: mockMachines });
  });
});
```

## Test Patterns

### Arrange-Act-Assert

```python
@pytest.mark.asyncio
async def test_create_and_get_machine(db_session):
    # Arrange
    machine_data = MachineCreate(
        name="Test Machine",
        status=MachineStatus.IDLE
    )

    # Act
    created = await machine_service.create(db_session, machine_data)
    retrieved = await machine_service.get(db_session, created.id)

    # Assert
    assert retrieved.name == "Test Machine"
    assert retrieved.status == MachineStatus.IDLE
```

### Given-When-Then (BDD style)

```python
@pytest.mark.asyncio
async def test_protocol_execution_updates_resource_quantity(db_session):
    """
    Given a protocol that uses 8 tips
    When the protocol executes successfully
    Then the tip rack quantity should decrease by 8
    """
    # Given
    tip_rack = await create_tip_rack(db_session, quantity=96)
    protocol = await create_protocol(db_session, uses_tips=8)

    # When
    await orchestrator.execute(protocol, assets={"tip_rack": tip_rack.id})

    # Then
    updated = await resource_service.get(db_session, tip_rack.id)
    assert updated.quantity == 88
```

### Table-Driven Tests

```python
@pytest.mark.parametrize("status,expected_available", [
    (MachineStatus.IDLE, True),
    (MachineStatus.RUNNING, False),
    (MachineStatus.OFFLINE, False),
    (MachineStatus.MAINTENANCE, False),
])
async def test_machine_availability(db_session, status, expected_available):
    machine = await create_machine(db_session, status=status)
    assert machine.is_available == expected_available
```

## Coverage

### Backend Coverage

```bash
# Generate coverage report
uv run pytest --cov=praxis --cov-report=html

# View report
open htmlcov/index.html
```

Target: 80% coverage minimum

### Frontend Coverage

```bash
bun test -- --code-coverage

# View report
open coverage/praxis/index.html
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main

GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - run: uv run pytest --cov

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: bun install
        working-directory: praxis/web-client
      - run: bun test -- --no-watch --code-coverage
        working-directory: praxis/web-client
```
