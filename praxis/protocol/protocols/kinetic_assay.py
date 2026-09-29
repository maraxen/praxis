"""Kinetic Plate Reader Assay Protocol.

A time-course plate reader protocol that demonstrates complex no-deck workflows
with multiple readings over time. Useful for enzyme kinetics, cell growth, or
any temporal assay.

This shows a more advanced `requires_deck=False` protocol with data views.
"""

from typing import Any

from pylabrobot.legacy.plate_reading import PlateReader
from pylabrobot.resources import Plate

from praxis.backend.core.decorators import protocol_function


@protocol_function(
  name="kinetic_assay",
  version="1.0.0",
  description="Time-course plate reader assay with multiple readings (no liquid handler)",
  category="plate_reading",
  tags=["demo", "assay", "kinetic", "no-deck", "time-course"],
  is_top_level=True,
  requires_deck=False,
  data_views=[
    {
      "name": "kinetic_curve",
      "description": "Average OD over time (line chart)",
      "source_type": "function_output",
    },
    {
      "name": "well_heatmap",
      "description": "Final reading values by well position (heatmap)",
      "source_type": "function_output",
    },
  ],
  param_metadata={
    "plate_reader": {
      "description": "The plate reader instrument",
      "plr_type": "PlateReader",
    },
    "plate": {
      "description": "The plate to read",
      "plr_type": "Plate",
    },
    "wavelength_nm": {
      "description": "Absorbance wavelength in nanometers",
      "min": 200,
      "max": 1000,
    },
    "wells_to_read": {
      "description": "Wells to monitor (use grid selector for visual selection)",
      "ui_hint": "well_selector",
    },
    "interval_seconds": {
      "description": "Time between readings in seconds",
      "min": 10,
      "max": 3600,
    },
    "duration_minutes": {
      "description": "Total assay duration in minutes",
      "min": 1,
      "max": 1440,
    },
    "temperature_c": {
      "description": "Incubation temperature (if supported)",
      "min": 20.0,
      "max": 45.0,
    },
    "shake_before_read": {
      "description": "Shake plate before each reading",
    },
  },
)
async def kinetic_assay(
  state: dict[str, Any],
  plate_reader: PlateReader,
  plate: Plate,
  wavelength_nm: int = 600,
  wells_to_read: str = "A1:H12",
  interval_seconds: int = 60,
  duration_minutes: int = 60,
  temperature_c: float = 37.0,
  shake_before_read: bool = True,
) -> dict[str, Any]:
  """Perform a kinetic plate reader assay over time.

  This protocol demonstrates a time-course measurement workflow:
  1. Configure the plate reader with temperature and wavelength
  2. Parse the well selection
  3. Take readings at specified intervals
  4. Calculate growth rates and other metrics
  5. Return data suitable for visualization

  Args:
      state: Protocol state dictionary
      plate_reader: Plate reader instrument
      plate: Plate to read
      wavelength_nm: Absorbance wavelength
      wells_to_read: Well selection string
      interval_seconds: Time between readings
      duration_minutes: Total duration
      temperature_c: Incubation temperature
      shake_before_read: Whether to shake before reading

  Returns:
      Updated state with kinetic data

  """
  # Parse wells
  wells = _parse_well_selection(wells_to_read)

  # Calculate number of readings
  total_seconds = duration_minutes * 60
  num_readings = total_seconds // interval_seconds

  # Store configuration
  state["config"] = {
    "wavelength_nm": wavelength_nm,
    "wells": wells,
    "plate_name": plate.name,
    "interval_seconds": interval_seconds,
    "duration_minutes": duration_minutes,
    "temperature_c": temperature_c,
    "shake_before_read": shake_before_read,
    "num_readings": num_readings,
  }

  # Simulate time-course readings
  time_points = []
  readings_by_well = {well: [] for well in wells}

  for reading_idx in range(num_readings):
    time_minutes = (reading_idx * interval_seconds) / 60.0
    time_points.append(time_minutes)

    # Simulate exponential growth for each well
    for well in wells:
      # Base OD with exponential increase
      base_od = 0.05 + (hash(well) % 50) / 1000.0
      growth_rate = 0.01 + (hash(well + "rate") % 30) / 1000.0
      od = base_od * (1 + growth_rate * time_minutes) ** 1.5
      readings_by_well[well].append(round(od, 4))

  # Calculate average OD at each time point for line chart
  avg_ods = []
  for idx in range(num_readings):
    avg = sum(readings_by_well[w][idx] for w in wells) / len(wells)
    avg_ods.append(round(avg, 4))

  # Final readings for heatmap
  final_readings = {well: readings_by_well[well][-1] for well in wells}

  # Calculate growth metrics
  growth_metrics = {}
  for well in wells:
    initial = readings_by_well[well][0]
    final = readings_by_well[well][-1]
    fold_change = final / initial if initial > 0 else 0
    growth_metrics[well] = {
      "initial_od": initial,
      "final_od": final,
      "fold_change": round(fold_change, 2),
    }

  # Structure data for visualization
  state["time_points"] = time_points
  state["readings_by_well"] = readings_by_well
  state["avg_ods"] = avg_ods
  state["final_readings"] = final_readings
  state["growth_metrics"] = growth_metrics

  # Data for data_views
  state["kinetic_curve_data"] = [
    {"time_minutes": t, "avg_od": od} for t, od in zip(time_points, avg_ods, strict=False)
  ]
  state["well_heatmap_data"] = final_readings

  state["status"] = "completed"
  state["well_count"] = len(wells)
  state["reading_count"] = num_readings

  return state


def _parse_well_selection(selection: str) -> list[str]:
  """Parse a well selection string into a list of well positions."""
  wells = []

  if ":" in selection and "," not in selection:
    start, end = selection.split(":")
    start_row, start_col = start[0].upper(), int(start[1:])
    end_row, end_col = end[0].upper(), int(end[1:])

    for row_ord in range(ord(start_row), ord(end_row) + 1):
      for col in range(start_col, end_col + 1):
        wells.append(f"{chr(row_ord)}{col}")
  elif "," in selection:
    wells = [w.strip().upper() for w in selection.split(",")]
  else:
    wells = [selection.strip().upper()]

  return wells
