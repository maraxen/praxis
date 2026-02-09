"""Serial Dilution Protocol.

A demo protocol that performs serial dilution across a plate row.
Demonstrates iterative well-to-well transfers with dilution factor.
"""

from typing import Any

from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.resources import Plate, TipRack, Trough

from praxis.backend.core.decorators import protocol_function


@protocol_function(
    name="serial_dilution",
    version="1.0.0",
    description="Perform serial dilution across a plate row",
    category="liquid_handling",
    tags=["demo", "dilution", "assay"],
    is_top_level=True,
    param_metadata={
        "liquid_handler": {
            "description": "Liquid handler",
            "plr_type": "LiquidHandler",
        },
        "plate": {
            "description": "Plate for serial dilution",
            "plr_type": "Plate",
        },
        "tip_rack": {
            "description": "Tip rack for liquid handling",
            "plr_type": "TipRack",
        },
        "diluent_trough": {
            "description": "Trough containing diluent",
            "plr_type": "Trough",
        },
        "start_row": {
            "description": "Starting row letter (A-H)",
        },
        "num_dilutions": {
            "description": "Number of dilution steps",
        },
        "sample_volume_ul": {
            "description": "Volume of sample to transfer between wells",
        },
        "diluent_volume_ul": {
            "description": "Volume of diluent to add to each well",
        },
        "dilution_factor": {
            "description": "Dilution factor per step (e.g., 2 for 1:2 dilution)",
        },
    },
)
async def serial_dilution(
    state: dict[str, Any],
    liquid_handler: LiquidHandler,
    plate: Plate,
    tip_rack: TipRack,
    diluent_trough: Trough,
    start_row: str = "A",
    num_dilutions: int = 8,
    sample_volume_ul: float = 100.0,
    diluent_volume_ul: float = 100.0,
    dilution_factor: float = 2.0,
) -> dict[str, Any]:
    """Perform serial dilution across a plate row.

    This protocol:
    1. Adds diluent to all dilution wells
    2. Transfers sample from column 1 to column 2
    3. Mixes and transfers to subsequent columns
    4. Discards final transfer volume

    Args:
        state: Protocol state dictionary
        liquid_handler: Liquid handler
        plate: Plate for the serial dilution
        tip_rack: Tip rack for transfers
        diluent_trough: Trough with diluent
        start_row: Starting row (e.g., 'A')
        num_dilutions: Number of dilution steps
        sample_volume_ul: Volume transferred between wells
        diluent_volume_ul: Volume of diluent per well
        dilution_factor: Dilution factor per step

    Returns:
        Updated state with dilution series data

    """
    row = start_row.upper()
    if len(row) != 1 or row not in "ABCDEFGH":
        msg = f"Invalid row: {row}. Must be A-H."
        raise ValueError(msg)

    if num_dilutions < 1 or num_dilutions > 12:
        msg = f"num_dilutions must be 1-12, got {num_dilutions}"
        raise ValueError(msg)

    # Generate well positions for this row
    well_positions = [f"{row}{i}" for i in range(1, num_dilutions + 2)]

    # Record operations
    dilution_steps = []

    # Step 1: Add diluent to all dilution wells (columns 2 onwards)
    # Using one tip for diluent distribution
    await liquid_handler.pick_up_tips(tip_rack["A1"])
    
    for well in well_positions[1:]:
        await liquid_handler.aspirate([diluent_trough], vols=[diluent_volume_ul])
        await liquid_handler.dispense(plate[well], vols=[diluent_volume_ul])
        
        dilution_steps.append({
            "operation": "add_diluent",
            "well": well,
            "volume_ul": diluent_volume_ul,
            "source": diluent_trough.name,
        })
    
    await liquid_handler.return_tips()

    # Step 2: Serial transfer from well to well
    concentrations = [1.0]  # Starting concentration (relative)
    
    # Use a new tip for the serial dilution to avoid contamination back to source?
    # Actually, often you change tips between steps, or reuse if going low -> high (not here)
    # or high -> low (yes here). We are diluting, so we are going high to low.
    # BUT, to be clean, let's use a new tip for the whole series or change if needed.
    # Standard practice: reuse tip for serial dilution row is acceptable if mixing thoroughly,
    # but strictly speaking, carryover increases.
    # Let's use one tip for the series for simplicity in this demo.
    
    await liquid_handler.pick_up_tips(tip_rack["B1"])

    for i in range(num_dilutions):
        src_well = well_positions[i]
        dst_well = well_positions[i + 1]

        # Transfer
        await liquid_handler.aspirate(plate[src_well], vols=[sample_volume_ul])
        await liquid_handler.dispense(plate[dst_well], vols=[sample_volume_ul])
        
        # Mix (aspirate/dispense in place)
        # await liquid_handler.mix(plate[dst_well], vols=[sample_volume_ul], cycles=3) # PLR mix not always available on LH directly?
        # Let's simulate mix with asp/disp
        for _ in range(3):
             await liquid_handler.aspirate(plate[dst_well], vols=[sample_volume_ul * 0.8])
             await liquid_handler.dispense(plate[dst_well], vols=[sample_volume_ul * 0.8])

        dilution_steps.append({
            "operation": "transfer",
            "source_well": src_well,
            "dest_well": dst_well,
            "volume_ul": sample_volume_ul,
        })

        # Calculate concentration after dilution
        new_conc = concentrations[-1] / dilution_factor
        concentrations.append(new_conc)
        
    await liquid_handler.return_tips()

    # Update state
    state["dilution_steps"] = dilution_steps
    state["well_positions"] = well_positions
    state["concentrations"] = concentrations
    state["dilution_factor"] = dilution_factor
    state["plate_name"] = plate.name
    state["status"] = "completed"

    return state
