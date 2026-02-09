"""Plate Preparation Protocol.

A demo protocol that prepares a 96-well plate by filling wells with liquid.
Demonstrates plate-wide operations and well iteration.
"""

from typing import Any

from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.resources import Plate, TipRack, Trough

from praxis.backend.core.decorators import protocol_function


@protocol_function(
    name="plate_preparation",
    version="1.0.0",
    description="Prepare a 96-well plate by filling wells with liquid",
    category="plate_handling",
    tags=["demo", "preparation", "fill"],
    is_top_level=True,
    param_metadata={
        "liquid_handler": {
            "description": "Liquid handler",
            "plr_type": "LiquidHandler",
        },
        "plate": {
            "description": "Plate to prepare",
            "plr_type": "Plate",
        },
        "tip_rack": {
            "description": "Tip rack for liquid handling",
            "plr_type": "TipRack",
        },
        "reagent_trough": {
            "description": "Trough containing reagent",
            "plr_type": "Trough",
        },
        "fill_pattern": {
            "description": "Pattern to fill: 'all', 'columns', 'rows', 'checkerboard'",
        },
        "volume_ul": {
            "description": "Volume to dispense per well in microliters",
        },
        "columns_to_fill": {
            "description": "Columns to fill (1-12), comma-separated. Used with 'columns' pattern",
        },
        "rows_to_fill": {
            "description": "Rows to fill (A-H), comma-separated. Used with 'rows' pattern",
        },
    },
)
async def plate_preparation(
    state: dict[str, Any],
    liquid_handler: LiquidHandler,
    plate: Plate,
    tip_rack: TipRack,
    reagent_trough: Trough,
    fill_pattern: str = "all",
    volume_ul: float = 200.0,
    columns_to_fill: str = "1,2,3,4,5,6,7,8,9,10,11,12",
    rows_to_fill: str = "A,B,C,D,E,F,G,H",
) -> dict[str, Any]:
    """Prepare a plate by filling wells with reagent.

    This protocol fills wells in a plate based on the specified pattern:
    - 'all': Fill all 96 wells
    - 'columns': Fill specified columns only
    - 'rows': Fill specified rows only
    - 'checkerboard': Fill alternating wells

    Args:
        state: Protocol state dictionary
        liquid_handler: Liquid handler
        plate: Plate to prepare
        tip_rack: Tip rack for dispensing
        reagent_trough: Trough containing the reagent
        fill_pattern: Pattern for filling wells
        volume_ul: Volume per well
        columns_to_fill: Columns for 'columns' pattern
        rows_to_fill: Rows for 'rows' pattern

    Returns:
        Updated state with preparation results

    """
    # Validate pattern
    valid_patterns = ["all", "columns", "rows", "checkerboard"]
    if fill_pattern not in valid_patterns:
        msg = f"Invalid fill_pattern: {fill_pattern}. Must be one of {valid_patterns}"
        raise ValueError(
            msg
        )

    # Parse columns and rows
    cols = [int(c.strip()) for c in columns_to_fill.split(",")]
    rows = [r.strip().upper() for r in rows_to_fill.split(",")]

    # Validate ranges
    for c in cols:
        if c < 1 or c > 12:
            msg = f"Invalid column: {c}. Must be 1-12."
            raise ValueError(msg)
    for r in rows:
        if r not in "ABCDEFGH":
            msg = f"Invalid row: {r}. Must be A-H."
            raise ValueError(msg)

    # Generate wells to fill based on pattern
    wells_to_fill = []
    all_rows = list("ABCDEFGH")
    all_cols = list(range(1, 13))

    if fill_pattern == "all":
        for row in all_rows:
            for col in all_cols:
                wells_to_fill.append(f"{row}{col}")
    elif fill_pattern == "columns":
        for row in all_rows:
            for col in cols:
                wells_to_fill.append(f"{row}{col}")
    elif fill_pattern == "rows":
        for row in rows:
            for col in all_cols:
                wells_to_fill.append(f"{row}{col}")
    elif fill_pattern == "checkerboard":
        for i, row in enumerate(all_rows):
            for j, col in enumerate(all_cols):
                if (i + j) % 2 == 0:
                    wells_to_fill.append(f"{row}{col}")

    # Pick up tips once for the batch dispense
    await liquid_handler.pick_up_tips(tip_rack["A1"])

    # Record dispensing operations
    dispense_operations = []
    for well in wells_to_fill:
        # Aspirate new reagent if needed? 
        # For simplicity, assuming trough has infinite volume or we aspirate per dispense for single-channel
        # Real optimization would aspirate large vol then multi-dispense.
        # Here: simple asp/disp cycle per well.
        await liquid_handler.aspirate([reagent_trough], vols=[volume_ul])
        await liquid_handler.dispense(plate[well], vols=[volume_ul])

        dispense_operations.append({
            "well": well,
            "volume_ul": volume_ul,
            "source": reagent_trough.name,
        })
        
    await liquid_handler.return_tips()

    # Update state
    state["dispense_operations"] = dispense_operations
    state["wells_filled"] = wells_to_fill
    state["total_wells"] = len(wells_to_fill)
    state["total_volume_ul"] = volume_ul * len(wells_to_fill)
    state["fill_pattern"] = fill_pattern
    state["plate_name"] = plate.name
    state["status"] = "completed"

    return state
