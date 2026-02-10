"""Selective Transfer Protocol.

A protocol that demonstrates complex well selection UI scenarios.
This shows how to use well selector parameters to enable grid-based
well selection in the protocol configuration UI.
"""

from typing import Any

from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.resources import Plate, TipRack

from praxis.backend.core.decorators import protocol_function


@protocol_function(
  name="selective_transfer",
  version="1.0.0",
  description="Transfer liquid between selected wells with rich well selection UI",
  category="liquid_handling",
  tags=["demo", "transfer", "well-selection", "advanced"],
  is_top_level=True,
  param_metadata={
    "liquid_handler": {
      "description": "The liquid handling robot to use",
      "plr_type": "LiquidHandler",
    },
    "source_plate": {
      "description": "Source plate containing samples",
      "plr_type": "Plate",
    },
    "dest_plate": {
      "description": "Destination plate for transfers",
      "plr_type": "Plate",
    },
    "tip_rack": {
      "description": "Tip rack for liquid handling",
      "plr_type": "TipRack",
    },
    "indices": {
      "description": "Well positions to transfer (e.g. A1, B2)",
      "ui_hint": "well_selector",
      "plate_ref": "source_plate",
    },
    "transfer_volume_ul": {
      "description": "Volume to transfer per well in microliters",
      "min": 1.0,
      "max": 1000.0,
    },
  },
)
async def selective_transfer(
  state: dict[str, Any],
  liquid_handler: LiquidHandler,
  source_plate: Plate,
  dest_plate: Plate,
  tip_rack: TipRack,
  indices: str = "A1:A4",
  transfer_volume_ul: float = 50.0,
) -> dict[str, Any]:
  """Transfer liquid between selected wells with various patterns.

  Args:
      state: Protocol state dictionary
      liquid_handler: Liquid handler for transfers
      source_plate: Source plate with samples
      dest_plate: Destination plate
      tip_rack: Tips for transfer
      indices: Well selection for transfers (applied to both plates)
      transfer_volume_ul: Volume per transfer

  Returns:
      Updated state with transfer records

  """
  # Parse well selections
  well_names = _parse_wells(indices)
  src_well_names = well_names
  dst_well_names = well_names

  transfers = []

  # Perform transfers using 1:1 mapping
  if len(src_well_names) != len(dst_well_names):
    msg = (
      f"Protocol requires equal well counts: "
      f"{len(src_well_names)} sources vs {len(dst_well_names)} destinations"
    )
    raise ValueError(msg)

  for i in range(len(src_well_names)):
    src = src_well_names[i]
    dst = dst_well_names[i]

    # Perform transfer
    await _perform_transfer(
      liquid_handler, source_plate, src, dest_plate, dst, transfer_volume_ul, tip_rack, i
    )

    transfers.append(
      {
        "source_plate": source_plate.name,
        "source_well": src,
        "dest_plate": dest_plate.name,
        "dest_well": dst,
        "volume_ul": transfer_volume_ul,
        "pattern": "1:1",
      }
    )

  # Update state
  state["transfers"] = transfers
  state["transfer_count"] = len(transfers)
  state["total_volume_ul"] = transfer_volume_ul * len(transfers)
  state["status"] = "completed"

  return state


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
  # Use column-major addressing to cycle through tip positions
  # Standard 96-tip rack: rows A-H (8), columns 1-12 (12)
  row_idx = tip_idx % 8
  col_idx = (tip_idx // 8) % 12
  row_letter = chr(ord('A') + row_idx)
  tip_id = f"{row_letter}{col_idx + 1}"

  await lh.pick_up_tips(tip_rack[tip_id])
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
