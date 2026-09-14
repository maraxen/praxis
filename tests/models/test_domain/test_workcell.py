"""Unit tests for Workcell model."""
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from praxis.backend.models.domain.workcell import (
    Workcell,
    WorkcellBase,
    WorkcellCreate,
    WorkcellUpdate,
)
from praxis.backend.models.domain.workcell import (
    WorkcellRead as WorkcellResponse,
)
from praxis.backend.models.enums.workcell import WorkcellStatusEnum


@pytest.mark.asyncio
async def test_workcell_orm_creation_with_defaults(db_session: AsyncSession) -> None:
    """Test creating a Workcell with default values."""
    from praxis.backend.utils.uuid import uuid7

    # Create a workcell with only required fields
    workcell_id = uuid7()
    workcell = Workcell(
        accession_id=workcell_id,
        name="test_workcell",
    )

    # Verify defaults are set
    assert workcell.accession_id == workcell_id
    assert workcell.name == "test_workcell"
    assert workcell.status == WorkcellStatusEnum.AVAILABLE.value
    assert workcell.description is None
    assert workcell.physical_location is None
    assert workcell.latest_state_json is None


@pytest.mark.asyncio
async def test_workcell_orm_persist_to_database(db_session: AsyncSession) -> None:
    """Test that a Workcell can be persisted to the database."""
    from praxis.backend.utils.uuid import uuid7

    workcell_id = uuid7()
    workcell = Workcell(
        accession_id=workcell_id,
        name="test_persistence",
        description="A test workcell",
        physical_location="Lab 1",
    )

    # Add to session and flush
    db_session.add(workcell)
    await db_session.flush()

    # Query back from database
    result = await db_session.execute(
        select(Workcell).where(Workcell.accession_id == workcell_id),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == workcell_id
    assert retrieved.name == "test_persistence"
    assert retrieved.description == "A test workcell"
    assert retrieved.physical_location == "Lab 1"


@pytest.mark.asyncio
async def test_workcell_orm_unique_name_constraint(db_session: AsyncSession) -> None:
    """Test that workcell names must be unique."""
    from sqlalchemy.exc import IntegrityError

    from praxis.backend.utils.uuid import uuid7

    # Create first workcell
    workcell1 = Workcell(
        accession_id=uuid7(),
        name="unique_workcell",
    )
    db_session.add(workcell1)
    await db_session.flush()

    # Try to create another with same name
    workcell2 = Workcell(
        accession_id=uuid7(),
        name="unique_workcell",  # Duplicate name
    )
    db_session.add(workcell2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_workcell_orm_relationships_empty_by_default(db_session: AsyncSession) -> None:
    """Test that relationship collections are empty by default."""
    from praxis.backend.utils.uuid import uuid7

    workcell = Workcell(
        accession_id=uuid7(),
        name="test_relationships",
    )

    # Relationships should be empty lists
    assert workcell.machines == []
    assert workcell.decks == []
    assert workcell.resources == []


@pytest.mark.asyncio
async def test_workcell_orm_with_custom_status(db_session: AsyncSession) -> None:
    """Test creating a workcell with a custom status."""
    from praxis.backend.utils.uuid import uuid7

    workcell = Workcell(
        accession_id=uuid7(),
        name="test_status",
        status=WorkcellStatusEnum.MAINTENANCE.value,
    )

    db_session.add(workcell)
    await db_session.flush()

    # Verify status was set
    assert workcell.status == WorkcellStatusEnum.MAINTENANCE.value


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestWorkcellSchemas:
    """Tests for Workcell Pydantic schemas."""

    def test_workcell_base_minimal(self) -> None:
        """Test creating a WorkcellBase with minimal required fields."""
        workcell = WorkcellBase(name="test_workcell")

        assert workcell.name == "test_workcell"
        assert workcell.fqn is None
        assert workcell.status == WorkcellStatusEnum.AVAILABLE
        assert workcell.description is None

    def test_workcell_base_with_all_fields(self) -> None:
        """Test creating a WorkcellBase with all fields populated."""
        now = datetime.now(timezone.utc)
        state = {"foo": "bar", "count": 42}

        workcell = WorkcellBase(
            name="full_workcell",
            fqn="test.full.workcell",
            description="A fully populated workcell",
            physical_location="Lab 1, Room 101",
            status=WorkcellStatusEnum.IN_USE,
            latest_state_json=state,
            last_state_update_time=now,
        )

        assert workcell.name == "full_workcell"
        assert workcell.fqn == "test.full.workcell"
        assert workcell.description == "A fully populated workcell"
        assert workcell.physical_location == "Lab 1, Room 101"
        assert workcell.status == WorkcellStatusEnum.IN_USE.value
        assert workcell.latest_state_json == state
        assert workcell.last_state_update_time == now

    def test_workcell_create_inherits_from_base(self) -> None:
        """Test that WorkcellCreate inherits all properties from WorkcellBase."""
        workcell = WorkcellCreate(
            name="create_test",
            description="Testing create model",
        )

        assert workcell.name == "create_test"
        assert workcell.description == "Testing create model"
        assert workcell.status == WorkcellStatusEnum.AVAILABLE

    def test_workcell_update_all_fields_optional(self) -> None:
        """Test that WorkcellUpdate allows all fields to be optional."""
        update = WorkcellUpdate()
        assert update.name is None
        assert update.description is None
        assert update.status is None

        update_partial = WorkcellUpdate(name="new_name")
        assert update_partial.name == "new_name"
        assert update_partial.description is None

    def test_workcell_response_serialization_to_dict(self) -> None:
        """Test that WorkcellResponse can be serialized to a dictionary."""
        workcell = WorkcellResponse(
            name="serialize_test",
            fqn="test.serialize",
            description="Testing serialization",
            status=WorkcellStatusEnum.MAINTENANCE,
        )

        data = workcell.model_dump()

        assert isinstance(data, dict)
        assert data["name"] == "serialize_test"
        assert data["status"] == "maintenance"
        assert data["machines"] == []
        assert data["resources"] == []
        assert data["decks"] == []

    def test_workcell_response_serialization_to_json(self) -> None:
        """Test that WorkcellResponse can be serialized to JSON."""
        now = datetime.now(timezone.utc)
        workcell = WorkcellResponse(
            name="json_test",
            status=WorkcellStatusEnum.ERROR,
            last_state_update_time=now,
        )

        json_str = workcell.model_dump_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["name"] == "json_test"
        assert data["status"] == "error"

    def test_workcell_response_deserialization_from_dict(self) -> None:
        """Test that WorkcellResponse can be deserialized from a dictionary."""
        data = {
            "name": "deserialize_test",
            "fqn": "test.deserialize",
            "description": "From dict",
            "status": "inactive",
            "latest_state_json": {"key": "value"},
            "machines": [],
            "resources": [],
            "decks": [],
        }

        workcell = WorkcellResponse.model_validate(data)

        assert workcell.name == "deserialize_test"
        assert workcell.status == "inactive"
        assert workcell.latest_state_json == {"key": "value"}

    def test_workcell_response_enum_validation(self) -> None:
        """Test that WorkcellResponse properly validates enum values."""
        workcell1 = WorkcellResponse(
            name="enum_test_1",
            status="active",
        )
        assert workcell1.status == "active"

        workcell2 = WorkcellResponse(
            name="enum_test_2",
            status=WorkcellStatusEnum.RESERVED,
        )
        assert workcell2.status == "reserved"

        with pytest.raises(ValueError):
            WorkcellResponse(
                name="enum_test_3",
                status="invalid_status",
            )

    def test_workcell_response_roundtrip_serialization(self) -> None:
        """Test that WorkcellResponse can be serialized and deserialized without data loss."""
        original = WorkcellResponse(
            name="roundtrip_test",
            fqn="test.roundtrip",
            description="Testing roundtrip",
            status=WorkcellStatusEnum.MAINTENANCE,
            latest_state_json={"test": "data"},
        )

        data = original.model_dump()
        restored = WorkcellResponse.model_validate(data)

        assert restored.name == original.name
        assert restored.status == original.status
        assert restored.latest_state_json == original.latest_state_json

    @pytest.mark.asyncio
    async def test_workcell_response_from_model(self, db_session: AsyncSession) -> None:
        """Test converting a Workcell instance to WorkcellResponse."""
        from praxis.backend.utils.uuid import uuid7
        workcell_id = uuid7()
        model_workcell = Workcell(
            accession_id=workcell_id,
            name="model_test_workcell",
            description="Testing ORM to Pydantic conversion",
            status=WorkcellStatusEnum.ACTIVE.value,
            latest_state_json={"key": "value"},
        )

        db_session.add(model_workcell)
        await db_session.flush()

        # Re-query with eager loading to simulate a proper DB fetch
        stmt = (
            select(Workcell)
            .options(
                selectinload(Workcell.machines),
                selectinload(Workcell.decks),
                selectinload(Workcell.resources),
            )
            .where(Workcell.accession_id == workcell_id)
        )
        result = await db_session.execute(stmt)
        loaded_workcell = result.scalars().one()

        response = WorkcellResponse.model_validate(loaded_workcell)

        assert response.accession_id == workcell_id
        assert response.name == "model_test_workcell"
        assert response.status == "active"
        assert response.latest_state_json == {"key": "value"}
