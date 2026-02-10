# Contributing to Praxis

Thank you for your interest in contributing to Praxis! This document will help you get started.

## Getting Started

See the installation instructions [here](docs/getting-started/installation.md). For contributing, you should install Praxis from source.

It's highly appreciated by the developers if you communicate what you want to work on, to minimize any duplicate work.

## Development Tips

It is recommend that you use VSCode, as we provide a workspace config in `/.vscode/settings.json`, but you can use any editor you like, of course.

Some VSCode Extensions I'd recommend:

- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [Pylint](https://github.com/microsoft/vscode-pylint)
- [Code Spell Checker](https://marketplace.visualstudio.com/items?itemName=streetsidesoftware.code-spell-checker)
- [pylance/pyright](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance)

## Agentic Development Workflow

This project uses the `.agent/` directory for AI-assisted development:

- **DEVELOPMENT_MATRIX.md**: Central priority/status tracking
- **backlog/**: Detailed work item specifications
- **prompts/**: Agent dispatch prompts organized by date
- **codestyles/**: Language-specific conventions

See `.agent/README.md` for full documentation.

## Running Tests

Praxis uses `pytest` to run unit tests. Please make sure tests pass when you submit a PR. You can run tests as follows.

```bash
uv run pytest # run test on the latest version
```

`pylint` is used to enforce code style. The rc file is `/.pylintrc`. As mentioned above, it is very helpful to have an editor do style checking as you're writing code.

```bash
uv run ruff check
```

`ty` (pyright-based) is used to enforce type checking.

```bash
uv run ty check
```

## Writing documentation

It is important that you write documentation for your code. As a rule of thumb, all functions and classes, whether public or private, are required to have a docstring. Praxis uses [Google Style Python Docstrings](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html). In addition, Praxis uses [type hints](https://docs.python.org/3/library/typing.html) to document the types of variables.

To build the documentation, run `uv run mkdocs serve` in the root directory. The documentation will be available at `http://127.0.0.1:8000`. To build static output, run `uv run mkdocs build` and open `site/index.html`.

## Data Models

### SQLModel Unified Architecture

Praxis uses **SQLModel** for unified data modeling, combining ORM and Pydantic functionality:

**Location:** `praxis/backend/models/domain/`

SQLModel provides:

- **ORM Models**: Database tables with SQLAlchemy relationships
- **API Schemas**: Pydantic validation (Create/Read/Update variants)
- **Polymorphic Inheritance**: Handled via SQLAlchemy's single-table inheritance

**Example Structure:**

```python
# Domain model (both ORM + Pydantic)
class Machine(Asset, table=True):
    __tablename__ = "machines"
    # ORM fields
    status: MachineStatusEnum = Field(default=MachineStatusEnum.OFFLINE)

# API schemas
class MachineCreate(SQLModel):
    name: str
    status: MachineStatusEnum | None = None

class MachineRead(SQLModel):
    accession_id: UUID
    name: str
    status: MachineStatusEnum
```

### Legacy Aliases (Temporary)

The `praxis/backend/models/orm/` directory contains **backward-compatibility aliases** only:

```python
# orm/__init__.py provides aliases for gradual migration
from praxis.backend.models.domain.machine import Machine as MachineOrm
```

**Do not use these in new code.** Use the domain models directly.

### Migration Toolkit

If you encounter `XOrm` references in code, use the migration script:

```bash
# Dry run to preview changes
uv run python scripts/fix_orm_references.py --dry-run

# Apply fixes to backend code
uv run python scripts/fix_orm_references.py --path praxis/backend

# Apply fixes to test code
uv run python scripts/fix_orm_references.py --path tests
```

The script automatically:

- Replaces `XOrm` → `X` (e.g., `MachineOrm` → `Machine`)
- Updates imports: `from praxis.backend.models.orm` → `from praxis.backend.models.domain`

### When Adding New Models

1. **Define in `models/domain/`** with SQLModel
2. **Use single-table inheritance** for polymorphic models
3. **Create schema variants**: `Create`, `Read`, `Update`
4. **Export in `domain/__init__.py`**
5. **Never add to `orm/`** - that's legacy only

## Common Tasks

### Fixing a bug

Bug fixes are an easy way to get started contributing.

Make sure you write a test that fails before your fix and passes after your fix. This ensures that this bug will never occur again. Tests are written in `<filename>_tests.py` files. See [Python's unittest module](https://docs.python.org/3/library/unittest.html) and existing tests for more information. In most cases, adding a few additional lines to an existing test should be sufficient.

## Support

If you have any questions, feel free to reach out using the [Praxis forum](https://forums.PyLabRobot.org).
