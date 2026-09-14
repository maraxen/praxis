"""Unit tests for UserService.

Tests cover all CRUD operations, authentication, and user-specific functionality.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.filters import SearchFilters
from praxis.backend.models.domain.user import (
    User,
    UserCreate,
    UserUpdate,
)
from praxis.backend.services.user import UserService, user_service


@pytest.mark.asyncio
async def test_user_service_create_user(db_session: AsyncSession) -> None:
    """Test creating a new user with password hashing."""
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="secure_password_123",
        full_name="Test User",
    )

    user = await user_service.create(db_session, obj_in=user_data)

    # Verify user was created
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.is_active is True

    # Verify password was hashed (not stored as plain text)
    assert user.hashed_password != "secure_password_123"
    assert user.hashed_password.startswith("$2b$")  # bcrypt hash prefix

    # Verify password can be verified
    assert user_service.verify_password("secure_password_123", user.hashed_password)
    assert not user_service.verify_password("wrong_password", user.hashed_password)


@pytest.mark.asyncio
async def test_user_service_create_user_minimal(db_session: AsyncSession) -> None:
    """Test creating user with only required fields."""
    user_data = UserCreate(
        username="minimaluser",
        email="minimal@example.com",
        password="password123",
    )

    user = await user_service.create(db_session, obj_in=user_data)

    assert user.username == "minimaluser"
    assert user.email == "minimal@example.com"
    assert user.full_name is None
    assert user.is_active is True  # Default


@pytest.mark.asyncio
async def test_user_service_create_duplicate_username(db_session: AsyncSession) -> None:
    """Test that creating user with duplicate username fails.

    The @handle_db_transaction decorator converts IntegrityError to ValueError.
    """
    user_data1 = UserCreate(
        username="duplicate",
        email="first@example.com",
        password="password123",
    )
    await user_service.create(db_session, obj_in=user_data1)

    # Try to create another user with same username
    user_data2 = UserCreate(
        username="duplicate",  # Same username
        email="second@example.com",
        password="password456",
    )

    # The decorator wraps IntegrityError in ValueError
    with pytest.raises(ValueError, match="integrity error"):
        await user_service.create(db_session, obj_in=user_data2)


@pytest.mark.asyncio
async def test_user_service_create_duplicate_email(db_session: AsyncSession) -> None:
    """Test that creating user with duplicate email fails.

    The @handle_db_transaction decorator converts IntegrityError to ValueError.
    """
    user_data1 = UserCreate(
        username="user1",
        email="duplicate@example.com",
        password="password123",
    )
    await user_service.create(db_session, obj_in=user_data1)

    # Try to create another user with same email
    user_data2 = UserCreate(
        username="user2",
        email="duplicate@example.com",  # Same email
        password="password456",
    )

    # The decorator wraps IntegrityError in ValueError
    with pytest.raises(ValueError, match="integrity error"):
        await user_service.create(db_session, obj_in=user_data2)


@pytest.mark.asyncio
async def test_user_service_get_by_id(db_session: AsyncSession) -> None:
    """Test retrieving user by ID."""
    user_data = UserCreate(
        username="getbyid",
        email="getbyid@example.com",
        password="password123",
    )
    created_user = await user_service.create(db_session, obj_in=user_data)

    # Retrieve by ID
    retrieved_user = await user_service.get(db_session, created_user.accession_id)

    assert retrieved_user is not None
    assert retrieved_user.accession_id == created_user.accession_id
    assert retrieved_user.username == "getbyid"


@pytest.mark.asyncio
async def test_user_service_get_by_id_not_found(db_session: AsyncSession) -> None:
    """Test retrieving non-existent user returns None."""
    from praxis.backend.utils.uuid import uuid7

    non_existent_id = uuid7()
    user = await user_service.get(db_session, non_existent_id)

    assert user is None


@pytest.mark.asyncio
async def test_user_service_get_by_username(db_session: AsyncSession) -> None:
    """Test retrieving user by username."""
    user_data = UserCreate(
        username="findme",
        email="findme@example.com",
        password="password123",
    )
    await user_service.create(db_session, obj_in=user_data)

    # Retrieve by username
    user = await user_service.get_by_username(db_session, "findme")

    assert user is not None
    assert user.username == "findme"
    assert user.email == "findme@example.com"


@pytest.mark.asyncio
async def test_user_service_get_by_username_not_found(db_session: AsyncSession) -> None:
    """Test retrieving user by non-existent username returns None."""
    user = await user_service.get_by_username(db_session, "nonexistent")
    assert user is None


@pytest.mark.asyncio
async def test_user_service_get_by_email(db_session: AsyncSession) -> None:
    """Test retrieving user by email."""
    user_data = UserCreate(
        username="emailuser",
        email="findemail@example.com",
        password="password123",
    )
    await user_service.create(db_session, obj_in=user_data)

    # Retrieve by email
    user = await user_service.get_by_email(db_session, "findemail@example.com")

    assert user is not None
    assert user.username == "emailuser"
    assert user.email == "findemail@example.com"


@pytest.mark.asyncio
async def test_user_service_get_by_email_not_found(db_session: AsyncSession) -> None:
    """Test retrieving user by non-existent email returns None."""
    user = await user_service.get_by_email(db_session, "nonexistent@example.com")
    assert user is None


@pytest.mark.asyncio
async def test_user_service_get_multi(db_session: AsyncSession) -> None:
    """Test listing multiple users with pagination."""
    # Create multiple users
    for i in range(5):
        user_data = UserCreate(
            username=f"user{i}",
            email=f"user{i}@example.com",
            password="password123",
        )
        await user_service.create(db_session, obj_in=user_data)

    # Get all users
    filters = SearchFilters(offset=0, limit=10)
    users = await user_service.get_multi(db_session, filters=filters)

    # Should find at least our 5 users
    assert len(users) >= 5
    usernames = [u.username for u in users]
    assert "user0" in usernames
    assert "user4" in usernames


@pytest.mark.asyncio
async def test_user_service_get_multi_pagination(db_session: AsyncSession) -> None:
    """Test pagination in get_multi."""
    # Create users
    for i in range(5):
        user_data = UserCreate(
            username=f"page_user{i}",
            email=f"page_user{i}@example.com",
            password="password123",
        )
        await user_service.create(db_session, obj_in=user_data)

    # Get first page (2 users)
    filters = SearchFilters(offset=0, limit=2)
    page1 = await user_service.get_multi(db_session, filters=filters)
    assert len(page1) == 2

    # Get second page (2 users)
    filters = SearchFilters(offset=2, limit=2)
    page2 = await user_service.get_multi(db_session, filters=filters)
    assert len(page2) == 2

    # Pages should have different users
    page1_ids = {u.accession_id for u in page1}
    page2_ids = {u.accession_id for u in page2}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.asyncio
async def test_user_service_update_user(db_session: AsyncSession) -> None:
    """Test updating user information."""
    user_data = UserCreate(
        username="updateuser",
        email="update@example.com",
        password="password123",
        full_name="Original Name",
    )
    user = await user_service.create(db_session, obj_in=user_data)

    # Update user
    update_data = UserUpdate(
        full_name="Updated Name",
        email="newemail@example.com",
    )
    updated_user = await user_service.update(
        db_session,
        db_obj=user,
        obj_in=update_data,
    )

    # Verify updates
    assert updated_user.full_name == "Updated Name"
    assert updated_user.email == "newemail@example.com"
    assert updated_user.username == "updateuser"  # Unchanged


@pytest.mark.asyncio
async def test_user_service_update_password(db_session: AsyncSession) -> None:
    """Test updating user password."""
    user_data = UserCreate(
        username="pwduser",
        email="pwd@example.com",
        password="old_password",
    )
    user = await user_service.create(db_session, obj_in=user_data)
    old_hash = user.hashed_password

    # Update password
    update_data = UserUpdate(password="new_password")
    updated_user = await user_service.update(
        db_session,
        db_obj=user,
        obj_in=update_data,
    )

    # Verify password was hashed and changed
    assert updated_user.hashed_password != old_hash
    assert user_service.verify_password("new_password", updated_user.hashed_password)
    assert not user_service.verify_password("old_password", updated_user.hashed_password)


@pytest.mark.asyncio
async def test_user_service_update_partial(db_session: AsyncSession) -> None:
    """Test partial update (only some fields)."""
    user_data = UserCreate(
        username="partial",
        email="partial@example.com",
        password="password123",
        full_name="Original Name",
    )
    user = await user_service.create(db_session, obj_in=user_data)

    # Update only full_name
    update_data = UserUpdate(full_name="New Name")
    updated_user = await user_service.update(
        db_session,
        db_obj=user,
        obj_in=update_data,
    )

    # Only full_name should change
    assert updated_user.full_name == "New Name"
    assert updated_user.username == "partial"
    assert updated_user.email == "partial@example.com"


@pytest.mark.asyncio
async def test_user_service_remove_user(db_session: AsyncSession) -> None:
    """Test deleting a user."""
    user_data = UserCreate(
        username="deleteuser",
        email="delete@example.com",
        password="password123",
    )
    user = await user_service.create(db_session, obj_in=user_data)
    user_id = user.accession_id

    # Delete user
    deleted_user = await user_service.remove(db_session, accession_id=user_id)

    assert deleted_user is not None
    assert deleted_user.username == "deleteuser"

    # Verify user no longer exists
    retrieved = await user_service.get(db_session, user_id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_user_service_remove_nonexistent(db_session: AsyncSession) -> None:
    """Test deleting non-existent user returns None."""
    from praxis.backend.utils.uuid import uuid7

    non_existent_id = uuid7()
    deleted = await user_service.remove(db_session, accession_id=non_existent_id)

    assert deleted is None


@pytest.mark.asyncio
async def test_user_service_authenticate_success(db_session: AsyncSession) -> None:
    """Test successful user authentication."""
    user_data = UserCreate(
        username="authuser",
        email="auth@example.com",
        password="correct_password",
    )
    await user_service.create(db_session, obj_in=user_data)

    # Authenticate
    authenticated_user = await user_service.authenticate(
        db_session,
        username="authuser",
        password="correct_password",
    )

    assert authenticated_user is not None
    assert authenticated_user.username == "authuser"


@pytest.mark.asyncio
async def test_user_service_authenticate_wrong_password(db_session: AsyncSession) -> None:
    """Test authentication fails with wrong password."""
    user_data = UserCreate(
        username="authfail",
        email="authfail@example.com",
        password="correct_password",
    )
    await user_service.create(db_session, obj_in=user_data)

    # Try to authenticate with wrong password
    authenticated_user = await user_service.authenticate(
        db_session,
        username="authfail",
        password="wrong_password",
    )

    assert authenticated_user is None


@pytest.mark.asyncio
async def test_user_service_authenticate_nonexistent_user(db_session: AsyncSession) -> None:
    """Test authentication fails for non-existent user."""
    authenticated_user = await user_service.authenticate(
        db_session,
        username="nonexistent",
        password="password",
    )

    assert authenticated_user is None


@pytest.mark.asyncio
async def test_user_service_authenticate_inactive_user(db_session: AsyncSession) -> None:
    """Test authentication fails for inactive user."""
    user_data = UserCreate(
        username="inactive",
        email="inactive@example.com",
        password="password123",
        is_active=False,
    )
    await user_service.create(db_session, obj_in=user_data)

    # Try to authenticate inactive user
    authenticated_user = await user_service.authenticate(
        db_session,
        username="inactive",
        password="password123",
    )

    assert authenticated_user is None


@pytest.mark.asyncio
async def test_user_service_set_active(db_session: AsyncSession) -> None:
    """Test activating/deactivating a user."""
    user_data = UserCreate(
        username="activeuser",
        email="active@example.com",
        password="password123",
    )
    user = await user_service.create(db_session, obj_in=user_data)

    # User should start active
    assert user.is_active is True

    # Deactivate user
    deactivated = await user_service.set_active(
        db_session,
        user=user,
        is_active=False,
    )
    assert deactivated.is_active is False

    # Reactivate user
    reactivated = await user_service.set_active(
        db_session,
        user=deactivated,
        is_active=True,
    )
    assert reactivated.is_active is True


@pytest.mark.asyncio
async def test_user_service_password_hashing_is_secure(db_session: AsyncSession) -> None:
    """Test that password hashing is secure (uses bcrypt)."""
    user_data = UserCreate(
        username="secureuser",
        email="secure@example.com",
        password="test_password_123",
    )
    user = await user_service.create(db_session, obj_in=user_data)

    # Verify bcrypt was used (hash starts with $2b$)
    assert user.hashed_password.startswith("$2b$")

    # Verify different users with same password get different hashes (salt)
    user_data2 = UserCreate(
        username="secureuser2",
        email="secure2@example.com",
        password="test_password_123",  # Same password
    )
    user2 = await user_service.create(db_session, obj_in=user_data2)

    # Hashes should be different due to salting
    assert user.hashed_password != user2.hashed_password


@pytest.mark.asyncio
async def test_user_service_singleton_instance(db_session: AsyncSession) -> None:
    """Test that user_service is a singleton instance."""
    # The imported user_service should be an instance of UserService
    assert isinstance(user_service, UserService)
    assert user_service.model == User
