
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.outputs import FunctionDataOutput
from praxis.backend.models.domain.protocol import (
    FunctionCallLog,
    FunctionProtocolDefinition,
    ProtocolRun,
)
from praxis.backend.models.enums import DataOutputTypeEnum, SpatialContextEnum
from praxis.backend.utils.uuid import uuid7


@pytest.mark.asyncio
async def test_debug_orm_relationships(db_session: AsyncSession):
    # 1. Create dependencies
    # Need FunctionProtocolDefinition for ProtocolRun?
    # ProtocolRun requires "top_level_protocol_definition_accession_id"?
    # Let's check definition.
    # Assuming minimal valid object.

    fpd = FunctionProtocolDefinition(
        name="test_fpd",
        fqn="test_fpd",
        accession_id=uuid7()
    )
    db_session.add(fpd)
    await db_session.flush()

    pr = ProtocolRun(
        name="test_pr",
        top_level_protocol_definition_accession_id=fpd.accession_id,
        accession_id=uuid7()
    )
    db_session.add(pr)
    await db_session.flush()

    fcl = FunctionCallLog(
        name="test_fcl",
        protocol_run_accession_id=pr.accession_id,
        function_protocol_definition_accession_id=fpd.accession_id,
        sequence_in_run=0,
        accession_id=uuid7()
    )
    db_session.add(fcl)
    await db_session.flush()

    # 2. Create FunctionDataOutput
    fdo = FunctionDataOutput(
        name="test_fdo",
        function_call_log_accession_id=fcl.accession_id,
        protocol_run_accession_id=pr.accession_id,
        data_type=DataOutputTypeEnum.GENERIC_MEASUREMENT,
        spatial_context=SpatialContextEnum.WELL_SPECIFIC,
        data_key="test_key",
        accession_id=uuid7()
    )
    db_session.add(fdo)
    await db_session.flush()

    assert fdo.accession_id is not None
