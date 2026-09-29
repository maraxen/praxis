"""Plate Reader Assay Protocol.

A standalone plate reader protocol that demonstrates workflows without
a liquid handler or deck. This is useful for simple absorbance or
fluorescence readings where no liquid handling is needed.

This protocol uses `requires_deck=False` to skip deck setup in the UI.
"""

from typing import Any

from pylabrobot.legacy.plate_reading import PlateReader
from pylabrobot.resources import Plate

from praxis.backend.core.decorators import protocol_function


@protocol_function(
  name="plate_reader_assay",
  version="1.0.0",
  description="Measure absorbance or fluorescence on a plate (no liquid handler required)",
  category="plate_reading",
  tags=["demo", "assay", "no-deck", "absorbance", "fluorescence"],
  is_top_level=True,
  requires_deck=False,  # Key: Skip deck setup wizard
  param_metadata={
    "plate_reader": {
      "description": "The plate reader instrument",
      "plr_type": "PlateReader",
    },
    "plate": {
      "description": "The plate to read (must already be in the reader)",
      "plr_type": "Plate",
    },
    "measurement_type": {
      "description": "Type of measurement (absorbance or fluorescence)",
      "ui_hint": "select",
      "options": ["absorbance", "fluorescence"],
    },
    "wavelength_nm": {
      "description": "Measurement wavelength in nanometers",
    },
    "excitation_nm": {
      "description": "Excitation wavelength for fluorescence (ignored for absorbance)",
    },
    "wells_to_read": {
      "description": "Wells to read (e.g., 'A1:H12' for full plate, 'A1,B1,C1' for specific wells)",
      "ui_hint": "well_selector",
    },
  },
)
async def plate_reader_assay(
  state: dict[str, Any],
  plate_reader: PlateReader,
  plate: Plate,
  measurement_type: str = "absorbance",
  wavelength_nm: int = 450,
  excitation_nm: int = 485,
  wells_to_read: str = "A1:H12",
) -> dict[str, Any]:
  """Measure absorbance or fluorescence on a plate.

  This protocol performs plate reading without requiring a liquid handler:
  1. Parse the well selection string
  2. Configure the plate reader for the measurement type
  3. Read the specified wells
  4. Return the measurements in the state

  Args:
      state: Protocol state dictionary
      plate_reader: Plate reader instrument
      plate: Plate to read
      measurement_type: 'absorbance' or 'fluorescence'
      wavelength_nm: Emission/absorbance wavelength in nm
      excitation_nm: Excitation wavelength for fluorescence
      wells_to_read: Well selection string

  Returns:
      Updated state with reading results

  """
  # Parse well selection
  wells = _parse_well_selection(wells_to_read, plate)

  # Store measurement configuration
  state["measurement_config"] = {
    "type": measurement_type,
    "wavelength_nm": wavelength_nm,
    "excitation_nm": excitation_nm if measurement_type == "fluorescence" else None,
    "wells": wells,
    "plate_name": plate.name,
  }

  # Simulate readings (in actual execution, we'd call plate_reader methods)
  readings = {}
  for well in wells:
    # Simulated OD/fluorescence value
    readings[well] = 0.05 + (hash(well) % 100) / 1000.0

  state["readings"] = readings
  state["well_count"] = len(wells)
  state["status"] = "completed"

  return state


def _parse_well_selection(selection: str, plate: Plate) -> list[str]:
  """Parse a well selection string into a list of well positions.

  Supports formats:
  - Range: 'A1:H12' (rectangle selection)
  - List: 'A1,B2,C3' (specific wells)
  - Column: 'A1:A8' (single column)
  - Row: 'A1:H1' (single row)
  """
  wells = []

  if ":" in selection and "," not in selection:
    # Range selection
    start, end = selection.split(":")
    start_row, start_col = start[0], int(start[1:])
    end_row, end_col = end[0], int(end[1:])

    for row_ord in range(ord(start_row), ord(end_row) + 1):
      for col in range(start_col, end_col + 1):
        wells.append(f"{chr(row_ord)}{col}")
  elif "," in selection:
    # List selection
    wells = [w.strip() for w in selection.split(",")]
  else:
    # Single well
    wells = [selection.strip()]

  return wells
