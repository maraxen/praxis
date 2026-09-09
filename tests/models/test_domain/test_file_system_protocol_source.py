"""Unit tests for FileSystemProtocolSourcemodel."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.protocol_source import FileSystemProtocolSource
from praxis.backend.models.enums import ProtocolSourceStatusEnum


@pytest.mark.asyncio
async def test_file_system_protocol_source_orm_creation_minimal(
    db_session: AsyncSession,
) -> None:
    """Test creating FileSystemProtocolSourcewith minimal required fields."""
    source = FileSystemProtocolSource(
        name="test_fs_source",
    )
    db_session.add(source)
    await db_session.flush()

    # Verify creation
    assert source.accession_id is not None
    assert source.name == "test_fs_source"
    assert source.base_path == ""  # Default
    assert source.is_recursive is True  # Default
    assert source.status == ProtocolSourceStatusEnum.ACTIVE  # Default


@pytest.mark.asyncio
async def test_file_system_protocol_source_orm_creation_with_all_fields(
    db_session: AsyncSession,
) -> None:
    """Test creating FileSystemProtocolSourcewith all fields populated."""
    source = FileSystemProtocolSource(
        name="full_fs_source",
        base_path="/opt/protocols/library",
        is_recursive=False,
        status=ProtocolSourceStatusEnum.INACTIVE,
    )
    db_session.add(source)
    await db_session.flush()

    # Verify all fields
    assert source.accession_id is not None
    assert source.name == "full_fs_source"
    assert source.base_path == "/opt/protocols/library"
    assert source.is_recursive is False
    assert source.status == ProtocolSourceStatusEnum.INACTIVE


@pytest.mark.asyncio
async def test_file_system_protocol_source_orm_persist_to_database(
    db_session: AsyncSession,
) -> None:
    """Test full persistence cycle for FileSystemProtocolSource."""
    source = FileSystemProtocolSource(
        name="persistence_test_fs",
        base_path="/var/protocols/test",
        is_recursive=True,
    )
    db_session.add(source)
    await db_session.flush()

    # Query back
    result = await db_session.execute(
        select(FileSystemProtocolSource).where(
            FileSystemProtocolSource.accession_id == source.accession_id,
        ),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == source.accession_id
    assert retrieved.name == "persistence_test_fs"
    assert retrieved.base_path == "/var/protocols/test"
    assert retrieved.is_recursive is True


@pytest.mark.asyncio
async def test_file_system_protocol_source_orm_unique_name_constraint(
    db_session: AsyncSession,
) -> None:
    """Test that name must be unique."""
    from sqlalchemy.exc import IntegrityError

    # Create first source
    source1 = FileSystemProtocolSource(
        name="unique_fs_name",
        base_path="/opt/protocols/source1",
    )
    db_session.add(source1)
    await db_session.flush()

    # Try to create another with same name
    source2 = FileSystemProtocolSource(
        name="unique_fs_name",  # Duplicate name
        base_path="/opt/protocols/source2",
    )
    db_session.add(source2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_file_system_protocol_source_orm_status_transitions(
    db_session: AsyncSession,
) -> None:
    """Test different status values for file system protocol source."""
    statuses = [
        (ProtocolSourceStatusEnum.ACTIVE, "active_fs"),
        (ProtocolSourceStatusEnum.SYNCING, "syncing_fs"),
        (ProtocolSourceStatusEnum.SYNC_ERROR, "error_fs"),
        (ProtocolSourceStatusEnum.INACTIVE, "inactive_fs"),
    ]

    for status, name in statuses:
        source = FileSystemProtocolSource(
            name=name,
            base_path=f"/opt/protocols/{name}",
            status=status,
        )
        db_session.add(source)
        await db_session.flush()

        # Verify status
        assert source.status == status


@pytest.mark.asyncio
async def test_file_system_protocol_source_orm_is_recursive_flag(
    db_session: AsyncSession,
) -> None:
    """Test is_recursive flag for scanning subdirectories."""
    # Source with recursive scanning (default)
    recursive_source = FileSystemProtocolSource(
        name="recursive_fs",
        base_path="/opt/protocols/recursive",
        is_recursive=True,
    )
    db_session.add(recursive_source)
    await db_session.flush()
    assert recursive_source.is_recursive is True

    # Source without recursive scanning
    non_recursive_source = FileSystemProtocolSource(
        name="non_recursive_fs",
        base_path="/opt/protocols/non_recursive",
        is_recursive=False,
    )
    db_session.add(non_recursive_source)
    await db_session.flush()
    assert non_recursive_source.is_recursive is False


@pytest.mark.asyncio
async def test_file_system_protocol_source_orm_query_by_name(
    db_session: AsyncSession,
) -> None:
    """Test querying sources by name."""
    source = FileSystemProtocolSource(
        name="queryable_fs",
        base_path="/opt/protocols/queryable",
    )
    db_session.add(source)
    await db_session.flush()

    # Query by name
    result = await db_session.execute(
        select(FileSystemProtocolSource).where(
            FileSystemProtocolSource.name == "queryable_fs",
        ),
    )
    retrieved = result.scalars().first()

    assert retrieved is not None
    assert retrieved.name == "queryable_fs"
    assert retrieved.base_path == "/opt/protocols/queryable"


@pytest.mark.asyncio
async def test_file_system_protocol_source_orm_update_base_path(
    db_session: AsyncSession,
) -> None:
    """Test updating base_path field."""
    source = FileSystemProtocolSource(
        name="path_update_fs",
        base_path="/opt/protocols/old_path",
    )
    db_session.add(source)
    await db_session.flush()

    # Initially old path
    assert source.base_path == "/opt/protocols/old_path"

    # Update base path
    source.base_path = "/opt/protocols/new_path"
    await db_session.flush()

    # Query back and verify update
    result = await db_session.execute(
        select(FileSystemProtocolSource).where(
            FileSystemProtocolSource.accession_id == source.accession_id,
        ),
    )
    retrieved = result.scalars().first()
    assert retrieved.base_path == "/opt/protocols/new_path"


@pytest.mark.asyncio
async def test_file_system_protocol_source_orm_repr(db_session: AsyncSession) -> None:
    """Test string representation of FileSystemProtocolSource."""
    source = FileSystemProtocolSource(
        name="repr_fs",
        base_path="/opt/protocols/repr",
    )

    repr_str = repr(source)
    assert "FileSystemProtocolSource" in repr_str
    assert str(source.accession_id) in repr_str
    assert "repr_fs" in repr_str
    assert "/opt/protocols/repr" in repr_str


@pytest.mark.asyncio
async def test_file_system_protocol_source_orm_query_by_status(
    db_session: AsyncSession,
) -> None:
    """Test querying sources by status."""
    # Create sources with different statuses
    active_source = FileSystemProtocolSource(
        name="active_status_fs",
        base_path="/opt/protocols/active",
        status=ProtocolSourceStatusEnum.ACTIVE,
    )
    inactive_source = FileSystemProtocolSource(
        name="inactive_status_fs",
        base_path="/opt/protocols/inactive",
        status=ProtocolSourceStatusEnum.INACTIVE,
    )
    db_session.add(active_source)
    db_session.add(inactive_source)
    await db_session.flush()

    # Query for active sources
    result = await db_session.execute(
        select(FileSystemProtocolSource).where(
            FileSystemProtocolSource.status == ProtocolSourceStatusEnum.ACTIVE,
        ),
    )
    active_sources = result.scalars().all()

    # Should find at least our active source
    assert len(active_sources) >= 1
    assert any(s.name == "active_status_fs" for s in active_sources)
