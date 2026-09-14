"""Tests for plate visualization service."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.outputs import (
    FunctionDataOutput,
    PlateDataVisualization,
    WellDataOutput,
)
from praxis.backend.models.enums.outputs import DataOutputTypeEnum, SpatialContextEnum
from praxis.backend.services.plate_viz import read_plate_data_visualization
from praxis.backend.utils.uuid import uuid7


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.mark.asyncio
async def test_read_plate_data_visualization(mock_db_session: AsyncMock) -> None:
    """Test reading plate data visualization."""
    plate_id = uuid7()
    fdo_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Create mock ORM objects
    # Note: Using explicit args because MappedAsDataclass might require them or not depending on config
    # Checking models: FunctionDataOutput has defaults?
    # FunctionDataOutput: data_type, spatial_context are required args? Memory item says so.

    fdo = FunctionDataOutput(
        name="test_fdo",
        function_call_log_accession_id=uuid.uuid4(),
        protocol_run_accession_id=uuid.uuid4(),
        data_type=DataOutputTypeEnum.ABSORBANCE_READING,
        measurement_timestamp=now,
        spatial_context=SpatialContextEnum.PLATE_LEVEL,
    )
    # Since we can't easily instantiate ORM relationships in tests without full setup,
    # we'll mock the relationship attribute on WellDataOutput if needed.
    # But read_plate_data_visualization accesses well_data_list[0].function_data_output.measurement_timestamp

    well_data_1 = WellDataOutput(
        name="test_well_1",
        function_data_output_accession_id=fdo_id,
        plate_resource_accession_id=plate_id,
        well_name="A1",
        data_value=0.5,
    )
    well_data_1.function_data_output = fdo

    well_data_2 = WellDataOutput(
        name="test_well_2",
        function_data_output_accession_id=fdo_id,
        plate_resource_accession_id=plate_id,
        well_name="A2",
        data_value=1.0,
    )
    well_data_2.function_data_output = fdo

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [well_data_1, well_data_2]
    mock_db_session.execute.return_value = mock_result

    result = await read_plate_data_visualization(
        mock_db_session,
        plate_resource_accession_id=plate_id,
        data_type=DataOutputTypeEnum.ABSORBANCE_READING,
    )

    assert result is not None
    assert isinstance(result, PlateDataVisualization)
    assert result.plate_resource_accession_id == plate_id
    assert result.data_type == DataOutputTypeEnum.ABSORBANCE_READING.value
    assert result.measurement_timestamp == now
    assert result.data_range["min"] == 0.5
    assert result.data_range["max"] == 1.0


@pytest.mark.asyncio
async def test_read_plate_data_visualization_no_data(mock_db_session: AsyncMock) -> None:
    """Test reading plate data visualization with no data."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute.return_value = mock_result

    result = await read_plate_data_visualization(
        mock_db_session,
        plate_resource_accession_id=uuid.uuid4(),
        data_type=DataOutputTypeEnum.ABSORBANCE_READING,
    )

    assert result is None
