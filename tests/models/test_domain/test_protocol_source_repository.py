"""Unit tests for ProtocolSourceRepositorymodel."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.protocol_source import ProtocolSourceRepository
from praxis.backend.models.enums import ProtocolSourceStatusEnum


@pytest.mark.asyncio
async def test_protocol_source_repository_orm_creation_minimal(
    db_session: AsyncSession,
) -> None:
    """Test creating ProtocolSourceRepositorywith minimal required fields."""
    repo = ProtocolSourceRepository(
        name="test_repo",
    )
    db_session.add(repo)
    await db_session.flush()

    # Verify creation
    assert repo.accession_id is not None
    assert repo.name == "test_repo"
    assert repo.git_url == ""  # Default
    assert repo.default_ref == "main"  # Default
    assert repo.local_checkout_path is None
    assert repo.last_synced_commit is None
    assert repo.status == ProtocolSourceStatusEnum.ACTIVE.value  # Default
    assert repo.auto_sync_enabled is True  # Default


@pytest.mark.asyncio
async def test_protocol_source_repository_orm_creation_with_all_fields(
    db_session: AsyncSession,
) -> None:
    """Test creating ProtocolSourceRepositorywith all fields populated."""
    repo = ProtocolSourceRepository(
        name="full_repo",
        git_url="https://github.com/example/protocols.git",
        default_ref="develop",
        local_checkout_path="/opt/protocols/example",
        last_synced_commit="abc123def456",
        status=ProtocolSourceStatusEnum.SYNCING,
        auto_sync_enabled=False,
    )
    db_session.add(repo)
    await db_session.flush()

    # Verify all fields
    assert repo.accession_id is not None
    assert repo.name == "full_repo"
    assert repo.git_url == "https://github.com/example/protocols.git"
    assert repo.default_ref == "develop"
    assert repo.local_checkout_path == "/opt/protocols/example"
    assert repo.last_synced_commit == "abc123def456"
    assert repo.status == ProtocolSourceStatusEnum.SYNCING.value
    assert repo.auto_sync_enabled is False


@pytest.mark.asyncio
async def test_protocol_source_repository_orm_persist_to_database(
    db_session: AsyncSession,
) -> None:
    """Test full persistence cycle for ProtocolSourceRepository."""
    repo = ProtocolSourceRepository(
        name="persistence_test_repo",
        git_url="https://github.com/test/persistence.git",
        default_ref="main",
        auto_sync_enabled=True,
    )
    db_session.add(repo)
    await db_session.flush()

    # Query back
    result = await db_session.execute(
        select(ProtocolSourceRepository).where(
            ProtocolSourceRepository.accession_id == repo.accession_id,
        ),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == repo.accession_id
    assert retrieved.name == "persistence_test_repo"
    assert retrieved.git_url == "https://github.com/test/persistence.git"
    assert retrieved.default_ref == "main"
    assert retrieved.auto_sync_enabled is True


@pytest.mark.asyncio
async def test_protocol_source_repository_orm_unique_name_constraint(
    db_session: AsyncSession,
) -> None:
    """Test that name must be unique."""
    from sqlalchemy.exc import IntegrityError

    # Create first repository
    repo1 = ProtocolSourceRepository(
        name="unique_repo_name",
        git_url="https://github.com/example/repo1.git",
    )
    db_session.add(repo1)
    await db_session.flush()

    # Try to create another with same name
    repo2 = ProtocolSourceRepository(
        name="unique_repo_name",  # Duplicate name
        git_url="https://github.com/example/repo2.git",
    )
    db_session.add(repo2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_protocol_source_repository_orm_status_transitions(
    db_session: AsyncSession,
) -> None:
    """Test different status values for protocol source repository."""
    statuses = [
        (ProtocolSourceStatusEnum.ACTIVE, "active_repo"),
        (ProtocolSourceStatusEnum.SYNCING, "syncing_repo"),
        (ProtocolSourceStatusEnum.SYNC_ERROR, "error_repo"),
        (ProtocolSourceStatusEnum.INACTIVE, "inactive_repo"),
    ]

    for status, name in statuses:
        repo = ProtocolSourceRepository(
            name=name,
            git_url=f"https://github.com/example/{name}.git",
            status=status,
        )
        db_session.add(repo)
        await db_session.flush()

        # Verify status
        assert repo.status == status.value


@pytest.mark.asyncio
async def test_protocol_source_repository_orm_auto_sync_flag(
    db_session: AsyncSession,
) -> None:
    """Test auto_sync_enabled flag."""
    # Repository with auto-sync enabled (default)
    repo_enabled = ProtocolSourceRepository(
        name="auto_sync_enabled_repo",
        git_url="https://github.com/example/enabled.git",
        auto_sync_enabled=True,
    )
    db_session.add(repo_enabled)
    await db_session.flush()
    assert repo_enabled.auto_sync_enabled is True

    # Repository with auto-sync disabled
    repo_disabled = ProtocolSourceRepository(
        name="auto_sync_disabled_repo",
        git_url="https://github.com/example/disabled.git",
        auto_sync_enabled=False,
    )
    db_session.add(repo_disabled)
    await db_session.flush()
    assert repo_disabled.auto_sync_enabled is False


@pytest.mark.asyncio
async def test_protocol_source_repository_orm_query_by_name(
    db_session: AsyncSession,
) -> None:
    """Test querying repositories by name."""
    repo = ProtocolSourceRepository(
        name="queryable_repo",
        git_url="https://github.com/example/queryable.git",
    )
    db_session.add(repo)
    await db_session.flush()

    # Query by name
    result = await db_session.execute(
        select(ProtocolSourceRepository).where(
            ProtocolSourceRepository.name == "queryable_repo",
        ),
    )
    retrieved = result.scalars().first()

    assert retrieved is not None
    assert retrieved.name == "queryable_repo"
    assert retrieved.git_url == "https://github.com/example/queryable.git"


@pytest.mark.asyncio
async def test_protocol_source_repository_orm_update_commit_hash(
    db_session: AsyncSession,
) -> None:
    """Test updating last_synced_commit field."""
    repo = ProtocolSourceRepository(
        name="sync_test_repo",
        git_url="https://github.com/example/sync.git",
        last_synced_commit=None,
    )
    db_session.add(repo)
    await db_session.flush()

    # Initially no commit hash
    assert repo.last_synced_commit is None

    # Update commit hash
    repo.last_synced_commit = "new_commit_abc123"
    await db_session.flush()

    # Query back and verify update
    result = await db_session.execute(
        select(ProtocolSourceRepository).where(
            ProtocolSourceRepository.accession_id == repo.accession_id,
        ),
    )
    retrieved = result.scalars().first()
    assert retrieved.last_synced_commit == "new_commit_abc123"


@pytest.mark.asyncio
async def test_protocol_source_repository_orm_repr(db_session: AsyncSession) -> None:
    """Test string representation of ProtocolSourceRepository."""
    repo = ProtocolSourceRepository(
        name="repr_repo",
        git_url="https://github.com/example/repr.git",
    )

    repr_str = repr(repo)
    assert "ProtocolSourceRepository" in repr_str
    assert str(repo.accession_id) in repr_str
    assert "repr_repo" in repr_str
    assert "https://github.com/example/repr.git" in repr_str
