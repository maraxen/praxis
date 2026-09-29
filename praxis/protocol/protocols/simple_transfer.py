"""Simple Transfer Protocol.

A basic demo protocol that transfers liquid between wells in a plate.
This protocol demonstrates the use of PLR type hints for resources.
"""

from typing import Any

from pylabrobot.legacy.liquid_handling import LiquidHandler
from pylabrobot.resources import Plate, TipRack

from praxis.backend.core.decorators import protocol_function


@protocol_function(
  name="simple_transfer",
  version="1.0.0",
  description="Transfer liquid from source well(s) to destination well(s)",
  category="liquid_handling",
  tags=["demo", "transfer", "basic"],
  is_top_level=True,
  param_metadata={
    "liquid_handler": {
      "description": "The liquid handling robot to use for transfers",
      "plr_type": "LiquidHandler",
    },
    "source_plate": {
      "description": "Source plate containing liquid to transfer",
      "plr_type": "Plate",
    },
    "dest_plate": {
      "description": "Destination plate to receive the liquid",
      "plr_type": "Plate",
    },
    "tip_rack": {
      "description": "Tip rack for liquid handling",
      "plr_type": "TipRack",
    },
    "source_wells": {
      "description": "Source well positions (e.g., 'A1,A2,A3')",
    },
    "dest_wells": {
      "description": "Destination well positions (e.g., 'B1,B2,B3')",
    },
    "volume_ul": {
      "description": "Volume to transfer in microliters",
    },
  },
)
async def simple_transfer(
  state: dict[str, Any],
  liquid_handler: LiquidHandler,
  source_plate: Plate,
  dest_plate: Plate,
  tip_rack: TipRack,
  source_wells: str = "A1",
  dest_wells: str = "B1",
  volume_ul: float = 100.0,
) -> dict[str, Any]:
  """Transfer liquid from source wells to destination wells.

  This protocol performs a simple liquid transfer operation:
  1. Pick up tips from the tip rack
  2. Aspirate liquid from source wells
  3. Dispense liquid to destination wells
  4. Drop tips

  Args:
      state: Protocol state dictionary
      liquid_handler: Liquid handler
      source_plate: Plate containing the source liquid
      dest_plate: Plate to receive the liquid
      tip_rack: Tip rack for the transfer
      source_wells: Comma-separated source well positions
      dest_wells: Comma-separated destination well positions
      volume_ul: Volume to transfer in microliters

  Returns:
      Updated state dictionary with transfer results

  """
  # Parse well positions
  source_well_list = [w.strip() for w in source_wells.split(",")]
  dest_well_list = [w.strip() for w in dest_wells.split(",")]

  # Validate matching well counts
  if len(source_well_list) != len(dest_well_list):
    msg = (
      f"Source wells ({len(source_well_list)}) and destination wells "
      f"({len(dest_well_list)}) must have the same count"
    )
    raise ValueError(msg)

  transfers = []
  
  # Execute transfers
  for i in range(len(source_well_list)):
    src = source_well_list[i]
    dst = dest_well_list[i]
    
    # Simple tip management: 1 tip per transfer
    # In a real protocol, you might reuse tips or batch transfers
    await liquid_handler.pick_up_tips(tip_rack[f"A{i+1}"])
    
    await liquid_handler.aspirate(source_plate[src], vols=[volume_ul])
    await liquid_handler.dispense(dest_plate[dst], vols=[volume_ul])
    
    await liquid_handler.return_tips()

    transfer_record = {
      "source_plate": source_plate.name,
      "source_well": src,
      "dest_plate": dest_plate.name,
      "dest_well": dst,
      "volume_ul": volume_ul,
      "status": "completed",
    }
    transfers.append(transfer_record)

  # Update state
  state["transfers"] = transfers
  state["transfer_count"] = len(transfers)
  state["total_volume_ul"] = volume_ul * len(transfers)
  state["status"] = "completed"

  return state
