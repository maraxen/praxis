"""Unit tests for User model."""
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.user import (
    User,
    UserBase,
    UserCreate,
    UserUpdate,
)
from praxis.backend.models.domain.user import (
    UserRead as UserResponse,
)


@pytest.mark.asyncio
async def test_user_orm_creation_minimal(db_session: AsyncSession) -> None:
    """Test creating User with minimal required fields."""
    from praxis.backend.utils.uuid import uuid7

    user_id = uuid7()
    user = User(
        accession_id=user_id,
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password_123",
    )
    db_session.add(user)
    await db_session.flush()

    # Verify creation
    assert user.accession_id == user_id
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.hashed_password == "hashed_password_123"
    assert user.is_active is True  # Default
    assert user.full_name is None
    assert user.phone_number is None
    assert user.phone_carrier is None


@pytest.mark.asyncio
async def test_user_orm_creation_with_all_fields(db_session: AsyncSession) -> None:
    """Test creating User with all fields populated."""
    from praxis.backend.utils.uuid import uuid7

    user_id = uuid7()
    user = User(
        accession_id=user_id,
        username="fulluser",
        email="full@example.com",
        hashed_password="hashed_password_456",
        full_name="John Doe",
        is_active=True,
        phone_number="555-1234",
        phone_carrier="verizon",
    )
    db_session.add(user)
    await db_session.flush()

    # Verify all fields
    assert user.accession_id == user_id
    assert user.username == "fulluser"
    assert user.email == "full@example.com"
    assert user.hashed_password == "hashed_password_456"
    assert user.full_name == "John Doe"
    assert user.is_active is True
    assert user.phone_number == "555-1234"
    assert user.phone_carrier == "verizon"


@pytest.mark.asyncio
async def test_user_orm_persist_to_database(db_session: AsyncSession) -> None:
    """Test full persistence cycle for User."""
    from praxis.backend.utils.uuid import uuid7

    user_id = uuid7()
    user = User(
        accession_id=user_id,
        username="persistuser",
        email="persist@example.com",
        hashed_password="hashed_password_789",
        full_name="Jane Smith",
    )
    db_session.add(user)
    await db_session.flush()

    # Query back
    result = await db_session.execute(
        select(User).where(User.accession_id == user_id),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == user_id
    assert retrieved.username == "persistuser"
    assert retrieved.email == "persist@example.com"
    assert retrieved.hashed_password == "hashed_password_789"
    assert retrieved.full_name == "Jane Smith"
    assert retrieved.is_active is True


@pytest.mark.asyncio
async def test_user_orm_unique_username_constraint(db_session: AsyncSession) -> None:
    """Test that username must be unique."""
    from praxis.backend.utils.uuid import uuid7

    # Create first user
    user1 = User(
        accession_id=uuid7(),
        username="uniqueuser",
        email="user1@example.com",
        hashed_password="hash1",
    )
    db_session.add(user1)
    await db_session.flush()

    # Try to create another with same username
    user2 = User(
        accession_id=uuid7(),
        username="uniqueuser",  # Duplicate username
        email="user2@example.com",
        hashed_password="hash2",
    )
    db_session.add(user2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_user_orm_unique_email_constraint(db_session: AsyncSession) -> None:
    """Test that email must be unique."""
    from praxis.backend.utils.uuid import uuid7

    # Create first user
    user1 = User(
        accession_id=uuid7(),
        username="user1",
        email="unique@example.com",
        hashed_password="hash1",
    )
    db_session.add(user1)
    await db_session.flush()

    # Try to create another with same email
    user2 = User(
        accession_id=uuid7(),
        username="user2",
        email="unique@example.com",  # Duplicate email
        hashed_password="hash2",
    )
    db_session.add(user2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_user_orm_is_active_flag(db_session: AsyncSession) -> None:
    """Test is_active flag for user accounts."""
    from praxis.backend.utils.uuid import uuid7

    # Active user (default)
    active_user = User(
        accession_id=uuid7(),
        username="activeuser",
        email="active@example.com",
        hashed_password="hash_active",
    )
    db_session.add(active_user)
    await db_session.flush()
    assert active_user.is_active is True

    # Inactive user
    inactive_user = User(
        accession_id=uuid7(),
        username="inactiveuser",
        email="inactive@example.com",
        hashed_password="hash_inactive",
        is_active=False,
    )
    db_session.add(inactive_user)
    await db_session.flush()
    assert inactive_user.is_active is False


@pytest.mark.asyncio
async def test_user_orm_phone_fields(db_session: AsyncSession) -> None:
    """Test phone number and carrier fields."""
    from praxis.backend.utils.uuid import uuid7

    user = User(
        accession_id=uuid7(),
        username="phoneuser",
        email="phone@example.com",
        hashed_password="hash_phone",
        phone_number="555-0100",
        phone_carrier="att",
    )
    db_session.add(user)
    await db_session.flush()

    # Query back
    result = await db_session.execute(
        select(User).where(User.username == "phoneuser"),
    )
    retrieved = result.scalars().first()

    assert retrieved is not None
    assert retrieved.phone_number == "555-0100"
    assert retrieved.phone_carrier == "att"


@pytest.mark.asyncio
async def test_user_orm_repr(db_session: AsyncSession) -> None:
    """Test string representation of User."""
    from praxis.backend.utils.uuid import uuid7

    user_id = uuid7()
    user = User(
        accession_id=user_id,
        username="repruser",
        email="repr@example.com",
        hashed_password="hash_repr",
    )

    repr_str = repr(user)
    assert "User" in repr_str
    assert str(user_id) in repr_str
    assert "repruser" in repr_str
    assert "repr@example.com" in repr_str
    assert "is_active=True" in repr_str


@pytest.mark.asyncio
async def test_user_orm_query_by_username(db_session: AsyncSession) -> None:
    """Test querying users by username."""
    from praxis.backend.utils.uuid import uuid7

    user = User(
        accession_id=uuid7(),
        username="queryuser",
        email="query@example.com",
        hashed_password="hash_query",
    )
    db_session.add(user)
    await db_session.flush()

    # Query by username
    result = await db_session.execute(
        select(User).where(User.username == "queryuser"),
    )
    retrieved = result.scalars().first()

    assert retrieved is not None
    assert retrieved.username == "queryuser"
    assert retrieved.email == "query@example.com"


@pytest.mark.asyncio
async def test_user_orm_query_by_email(db_session: AsyncSession) -> None:
    """Test querying users by email."""
    from praxis.backend.utils.uuid import uuid7

    user = User(
        accession_id=uuid7(),
        username="emailquery",
        email="emailquery@example.com",
        hashed_password="hash_email",
    )
    db_session.add(user)
    await db_session.flush()

    # Query by email
    result = await db_session.execute(
        select(User).where(User.email == "emailquery@example.com"),
    )
    retrieved = result.scalars().first()

    assert retrieved is not None
    assert retrieved.username == "emailquery"
    assert retrieved.email == "emailquery@example.com"


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestUserSchemas:
    """Tests for User Pydantic schemas."""

    def test_user_base_minimal(self) -> None:
        """Test UserBase with minimal required fields."""
        user = UserBase(
            username="testuser",
            email="test@example.com",
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name is None
        assert user.is_active is True  # Default

    def test_user_base_with_all_fields(self) -> None:
        """Test UserBase with all fields populated."""
        user = UserBase(
            username="fulluser",
            email="full@example.com",
            full_name="John Doe",
            is_active=True,
        )

        assert user.username == "fulluser"
        assert user.email == "full@example.com"
        assert user.full_name == "John Doe"
        assert user.is_active is True

    def test_user_create_with_password(self) -> None:
        """Test UserCreate includes password field."""
        user = UserCreate(
            username="newuser",
            email="new@example.com",
            password="secure_password_123",
            full_name="Jane Smith",
        )

        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.password == "secure_password_123"
        assert user.full_name == "Jane Smith"
        assert user.is_active is True

    def test_user_create_password_required(self) -> None:
        """Test that UserCreate requires password field."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                # Missing password
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("password",) for error in errors)

    def test_user_update_all_fields_optional(self) -> None:
        """Test that UserUpdate allows all fields to be optional."""
        # Empty update is valid
        update = UserUpdate()

        assert update.username is None
        assert update.email is None
        assert update.full_name is None
        assert update.is_active is None
        assert update.password is None

        # Can update specific fields
        update_partial = UserUpdate(
            username="updated_user",
            is_active=False,
        )

        assert update_partial.username == "updated_user"
        assert update_partial.is_active is False
        assert update_partial.email is None

    def test_user_update_with_password(self) -> None:
        """Test UserUpdate can include password change."""
        update = UserUpdate(
            password="new_password_456",
        )

        assert update.password == "new_password_456"
        assert update.username is None

    def test_user_response_serialization_to_dict(self) -> None:
        """Test UserResponse serialization to dict."""
        from praxis.backend.utils.uuid import uuid7
        id_val = uuid7()
        response = UserResponse(
            accession_id=id_val,
            username="response_user",
            email="response@example.com",
            full_name="Response User",
            is_active=True,
        )

        user_dict = response.model_dump()

        assert user_dict["accession_id"] == id_val
        assert user_dict["username"] == "response_user"
        assert user_dict["email"] == "response@example.com"
        assert user_dict["full_name"] == "Response User"
        assert user_dict["is_active"] is True

    def test_user_response_serialization_to_json(self) -> None:
        """Test UserResponse serialization to JSON."""
        from praxis.backend.utils.uuid import uuid7
        response = UserResponse(
            accession_id=uuid7(),
            username="json_user",
            email="json@example.com",
            full_name="JSON User",
        )

        json_str = response.model_dump_json()

        assert isinstance(json_str, str)
        assert "json_user" in json_str
        assert "json@example.com" in json_str

    def test_user_response_deserialization_from_dict(self) -> None:
        """Test creating UserResponse from dict."""
        from praxis.backend.utils.uuid import uuid7
        id_val = uuid7()
        user_data = {
            "accession_id": id_val,
            "username": "deserialized_user",
            "email": "deserialized@example.com",
            "full_name": "Deserialized User",
            "is_active": True,
        }

        response = UserResponse(**user_data)

        assert response.accession_id == id_val
        assert response.username == "deserialized_user"
        assert response.email == "deserialized@example.com"
        assert response.full_name == "Deserialized User"
        assert response.is_active is True

    def test_user_response_roundtrip_serialization(self) -> None:
        """Test UserResponse survives serialization round-trip."""
        from praxis.backend.utils.uuid import uuid7
        original = UserResponse(
            accession_id=uuid7(),
            username="roundtrip_user",
            email="roundtrip@example.com",
            full_name="Roundtrip Test",
            is_active=False,
        )

        # Serialize to dict and back
        user_dict = original.model_dump()
        restored = UserResponse(**user_dict)

        assert restored.accession_id == original.accession_id
        assert restored.username == original.username
        assert restored.email == original.email
        assert restored.full_name == original.full_name
        assert restored.is_active == original.is_active

    @pytest.mark.asyncio
    async def test_user_response_from_model(self, db_session: AsyncSession) -> None:
        """Test converting User to UserResponse."""
        from praxis.backend.utils.uuid import uuid7

        # Create ORM instance
        user_id = uuid7()
        model_user = User(
            accession_id=user_id,
            username="model_test_user",
            email="orm@example.com",
            hashed_password="hashed_password_123",
            full_name="ORM Test User",
            is_active=True,
            phone_number="555-1234",
            phone_carrier="verizon",
        )

        db_session.add(model_user)
        await db_session.flush()

        # Convert to Pydantic
        response = UserResponse.model_validate(model_user)

        # Verify conversion (note: phone fields and hashed_password are not in Pydantic model)
        assert response.accession_id == user_id
        assert response.username == "model_test_user"
        assert response.email == "orm@example.com"
        assert response.full_name == "ORM Test User"
        assert response.is_active is True

    @pytest.mark.asyncio
    async def test_user_response_from_orm_minimal(self, db_session: AsyncSession) -> None:
        """Test ORM-to-Pydantic conversion with minimal fields."""
        from praxis.backend.utils.uuid import uuid7

        user_id = uuid7()
        model_user = User(
            accession_id=user_id,
            username="minimal_user",
            email="minimal@example.com",
            hashed_password="hashed_password_456",
        )

        db_session.add(model_user)
        await db_session.flush()

        # Convert to Pydantic
        response = UserResponse.model_validate(model_user)

        # Verify
        assert response.username == "minimal_user"
        assert response.email == "minimal@example.com"
        assert response.full_name is None
        assert response.is_active is True  # Default

    def test_user_base_inactive_user(self) -> None:
        """Test UserBase with inactive user."""
        user = UserBase(
            username="inactiveuser",
            email="inactive@example.com",
            is_active=False,
        )

        assert user.username == "inactiveuser"
        assert user.is_active is False

    def test_user_create_inactive_user(self) -> None:
        """Test creating an inactive user."""
        user = UserCreate(
            username="newinactive",
            email="newinactive@example.com",
            password="password123",
            is_active=False,
        )

        assert user.username == "newinactive"
        assert user.is_active is False

    def test_user_response_does_not_expose_password(self) -> None:
        """Test that UserResponse does not contain password field."""
        from praxis.backend.utils.uuid import uuid7
        response = UserResponse(
            accession_id=uuid7(),
            username="secure_user",
            email="secure@example.com",
        )

        # Verify password is not in the model
        assert not hasattr(response, "password")
        assert not hasattr(response, "hashed_password")

        # Verify it's not in serialized output
        user_dict = response.model_dump()
        assert "password" not in user_dict
        assert "hashed_password" not in user_dict
