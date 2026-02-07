"""Browser stub for praxis.protocol.protocols.selective_transfer module.

This includes ALL functions from the backend that cloudpickle may reference
during protocol deserialization and execution.
"""

from typing import Any
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.resources import Plate, TipRack
from praxis.backend.core.decorators import protocol_function

@protocol_function(
    name="selective_transfer",
    version="1.0.0",
)
def selective_transfer(*args, **kwargs):
    """Stub - actual function comes from pickle."""
    pass


async def _perform_transfer(
    lh: LiquidHandler,
    src_plate: Plate,
    src_well: str,
    dst_plate: Plate,
    dst_well: str,
    vol: float,
    tip_rack: TipRack,
    tip_idx: int,
) -> None:
    """Execute a single transfer operation with tip handling."""
    # Simple tip tracking: Wrap around tip rack if needed
    num_tips = 96  # Assumed standard 96 tip rack for simplicity
    tip_spot = tip_rack.get_item(tip_idx % num_tips)

    if tip_spot:
        await lh.pick_up_tips(tip_spot)
        await lh.aspirate(src_plate[src_well], vols=[vol])
        await lh.dispense(dst_plate[dst_well], vols=[vol])
        await lh.return_tips()


def _parse_wells(selection: str) -> list[str]:
    """Parse a well selection string into a list of well positions."""
    wells = []

    if ":" in selection and "," not in selection:
        # Range or rectangle selection
        start, end = selection.split(":")
        start_row, start_col = start[0].upper(), int(start[1:])
        end_row, end_col = end[0].upper(), int(end[1:])

        for row_ord in range(ord(start_row), ord(end_row) + 1):
            for col in range(start_col, end_col + 1):
                wells.append(f"{chr(row_ord)}{col}")
    elif "," in selection:
        # List of specific wells
        wells = [w.strip().upper() for w in selection.split(",")]
    else:
        # Single well
        wells = [selection.strip().upper()]

    return wells
