"""Tests for the well_outputs service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.filters import SearchFilters
from praxis.backend.models.domain.outputs import (
    WellDataOutput,
    WellDataOutputCreate,
    WellDataOutputUpdate,
)
from praxis.backend.services.well_outputs import (
    WellDataOutputCRUDService,
    create_well_data_outputs,
    create_well_data_outputs_from_flat_array,
)
from tests.factories import (
    FunctionCallLogFactory,
    FunctionDataOutputFactory,
    ProtocolRunFactory,
    ResourceFactory,
    WellDataOutputFactory,
)


@pytest.fixture
def well_data_output_service():
    """Return a WellDataOutputCRUDService."""
    return WellDataOutputCRUDService(WellDataOutput)


@pytest.mark.asyncio
async def test_create_well_data_output(
    db_session: AsyncSession,
    well_data_output_service: WellDataOutputCRUDService,
):
    """Test creating a well data output."""
    # Explicitly build hierarchy to ensure async flushing
    protocol_run = ProtocolRunFactory()
    assert protocol_run.accession_id is not None, "ProtocolRun accession_id is None!"
    await db_session.flush()

    function_call_log = FunctionCallLogFactory(protocol_run_obj=protocol_run)
    await db_session.flush()

    from praxis.backend.models.enums import DataOutputTypeEnum, SpatialContextEnum

    function_data_output = FunctionDataOutputFactory(
        _function_call_log=function_call_log,
        data_type=DataOutputTypeEnum.GENERIC_MEASUREMENT,
        spatial_context=SpatialContextEnum.WELL_SPECIFIC,
        data_key="test_key"
    )
    db_session.add(function_data_output)
    await db_session.flush()

    plate_resource = ResourceFactory.create()
    await db_session.flush()

    well_data_output_in = WellDataOutputCreate(
        function_data_output_accession_id=function_data_output.accession_id,
        plate_resource_accession_id=plate_resource.accession_id,
        well_name="A1",
        well_row=0,
        well_column=0,
        data_value=1.23,
    )
    created_well_data_output = await well_data_output_service.create(
        db_session, obj_in=well_data_output_in
    )
    assert created_well_data_output.well_name == "A1"
    assert created_well_data_output.data_value == 1.23
    assert created_well_data_output.function_data_output_accession_id == function_data_output.accession_id
    assert created_well_data_output.plate_resource_accession_id == plate_resource.accession_id


@pytest.mark.asyncio
async def test_create_well_data_output_invalid_well_name(
    db_session: AsyncSession,
    well_data_output_service: WellDataOutputCRUDService,
):
    """Test creating a well data output with an invalid well name."""
    function_data_output = FunctionDataOutputFactory.create()
    plate_resource = ResourceFactory.create()
    well_data_output_in = WellDataOutputCreate(
        function_data_output_accession_id=function_data_output.accession_id,
        plate_resource_accession_id=plate_resource.accession_id,
        well_name="!!",  # Invalid well name format
        data_value=1.23,
    )
    with pytest.raises(ValueError, match="Invalid well name format"):
        await well_data_output_service.create(
            db_session, obj_in=well_data_output_in
        )


@pytest.mark.asyncio
async def test_get_well_data_output(
    db_session: AsyncSession,
    well_data_output_service: WellDataOutputCRUDService,
):
    """Test getting a well data output."""
    well_data_output = WellDataOutputFactory.create()
    retrieved_well_data_output = await well_data_output_service.get(
        db_session, accession_id=well_data_output.accession_id
    )
    assert retrieved_well_data_output
    assert retrieved_well_data_output.accession_id == well_data_output.accession_id


@pytest.mark.asyncio
async def test_get_multi_well_data_output(
    db_session: AsyncSession,
    well_data_output_service: WellDataOutputCRUDService,
):
    """Test getting multiple well data outputs."""
    WellDataOutputFactory.create_batch(3)
    retrieved_well_data_outputs = await well_data_output_service.get_multi(
        db_session, filters=SearchFilters()
    )
    assert len(retrieved_well_data_outputs) == 3


@pytest.mark.asyncio
async def test_update_well_data_output(
    db_session: AsyncSession,
    well_data_output_service: WellDataOutputCRUDService,
):
    """Test updating a well data output."""
    well_data_output = WellDataOutputFactory.create(data_value=1.23)
    well_data_output_update = WellDataOutputUpdate(data_value=4.56)
    updated_well_data_output = await well_data_output_service.update(
        db_session, db_obj=well_data_output, obj_in=well_data_output_update
    )
    assert updated_well_data_output.data_value == 4.56


@pytest.mark.asyncio
async def test_remove_well_data_output(
    db_session: AsyncSession,
    well_data_output_service: WellDataOutputCRUDService,
):
    """Test removing a well data output."""
    well_data_output = WellDataOutputFactory.create()
    removed_well_data_output = await well_data_output_service.remove(
        db_session, accession_id=well_data_output.accession_id
    )
    assert removed_well_data_output
    assert removed_well_data_output.accession_id == well_data_output.accession_id
    retrieved_well_data_output = await well_data_output_service.get(
        db_session, accession_id=well_data_output.accession_id
    )
    assert not retrieved_well_data_output


@pytest.mark.asyncio
async def test_create_well_data_outputs(db_session: AsyncSession):
    """Test creating multiple well data outputs from a dictionary."""
    function_data_output = FunctionDataOutputFactory.create()
    plate_resource = ResourceFactory.create()
    well_data = {"A1": 1.1, "B2": 2.2, "C3": 3.3}

    well_outputs = await create_well_data_outputs(
        db_session,
        function_data_output_accession_id=function_data_output.accession_id,
        plate_resource_accession_id=plate_resource.accession_id,
        well_data=well_data,
    )

    assert len(well_outputs) == 3
    for well_output in well_outputs:
        assert well_output.well_name in well_data
        assert well_output.data_value == well_data[well_output.well_name]


@pytest.mark.asyncio
async def test_create_well_data_outputs_from_flat_array(db_session: AsyncSession):
    """Test creating multiple well data outputs from a flat array."""
    function_data_output = FunctionDataOutputFactory.create()
    plate_resource = ResourceFactory.create()
    await db_session.flush()
    data_array = [1.1, 2.2, 3.3]

    well_outputs = await create_well_data_outputs_from_flat_array(
        db_session,
        function_data_output_accession_id=function_data_output.accession_id,
        plate_resource_accession_id=plate_resource.accession_id,
        data_array=data_array,
    )

    assert len(well_outputs) == 3
    for i, well_output in enumerate(well_outputs):
        assert well_output.data_value == data_array[i]


@pytest.mark.asyncio
async def test_create_well_data_outputs_from_flat_array_invalid_length(
    db_session: AsyncSession,
):
    """Test creating multiple well data outputs from a flat array with an invalid length."""
    function_data_output = FunctionDataOutputFactory.create()
    # Explicitly clear dimensions to trigger the expected ValueError
    plate_resource = ResourceFactory.create(res_def__plr_definition_details_json=None)
    data_array = [1.1, 2.2, 3.3]
    with pytest.raises(ValueError, match="Could not determine plate dimensions for resource"):
        await create_well_data_outputs_from_flat_array(
            db_session,
            function_data_output_accession_id=function_data_output.accession_id,
            plate_resource_accession_id=plate_resource.accession_id,
            data_array=data_array,
        )
