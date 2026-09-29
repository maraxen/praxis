from typing import Literal

from praxis.utils.errors import ExperimentError
from praxis.utils.sanitation import (
  check_list_length,
  coerce_to_list,
  liquid_handler_setup_check,
  parse_well_name,
  tip_mapping,
)
from pylabrobot.legacy.liquid_handling import LiquidHandler
from pylabrobot.resources import Plate, TipRack, Well


async def dilution_checks(
  n_dilutions: int,
  source_plate: Plate,
  target_plate: Plate,
  dilution_factor: float,
  source_wells: list[int],
  target_wells: list[int],
  mix_cycles: int,
  tip_rack: TipRack,
  source_volumes: float | list[float] | None = None,
  dilution_axis: Literal["row", "column", "x", "y", 0, 1, "optimal"] | None = "optimal",
):
  """Checks for errors in the dilution series functions.

  Args:
    liquid_handler: LiquidHandler object
    source_plate: Plate with the source wells
    target_plate: Plate with the target wells
    dilution_factor: Factor by which to dilute each time
    source_wells: Wells in the source plate to dilute
    target_wells: Wells in the target plate to dilute
    mix_cycles: Number of mixing cycles to perform
    tip_rack: TipRack object
    source_volumes: Volume in the source wells. If None, will transfer the total well volume \
      divided by the dilution factor.
    dilution_axis: Axis along which to dilute. Options are "row", "column", "x", "y", 0, 1.

  Raises:
    ExperimentError: If there are errors in the input parameters.

  """
  if len(source_wells) != len(target_wells):
    msg = "Number of source wells does not match number of target wells"
    raise ValueError(msg)
  if not source_plate:
    msg = "No source plate specified"
    raise ValueError(msg)
  if not target_plate:
    msg = "No target plate specified"
    raise ValueError(msg)
  if not isinstance(dilution_factor, float):
    msg = "Dilution factor must be a float"
    raise ValueError(msg)
  if not isinstance(source_wells, list) or not isinstance(target_wells, list):
    msg = "Source and target wells must be lists"
    raise ValueError(msg)
  if not isinstance(mix_cycles, int):
    msg = "Mix cycles must be an integer"
    raise ValueError(msg)
  if not isinstance(tip_rack, TipRack):
    msg = "Tip rack must be a TipRack object"
    raise ValueError(msg)
  if source_volumes:
    if not isinstance(source_volumes, (float, list)):
      msg = "Source volumes must be a float or list of floats"
      raise ValueError(msg)
    if isinstance(source_volumes, list) and len(source_volumes) != len(source_wells):
      msg = "Number of source volumes does not match number of source wells"
      raise ValueError(msg)
  if dilution_axis not in ["row", "column", "x", "y", 0, 1, "optimal"]:
    msg = "Invalid dilution axis"
    raise ValueError(msg)


async def find_optimal_dilution_strategy(
  n_variables: int,  # TODO: implement replicate handling
  n_dilutions: int,
  dilution_factors: float | list[float] | list[list[float]],
  source_plate: Plate,
  target_plate: Plate,
  variables_volumes: float | list[float],
  undiluted_source: bool = True,
  variable_accession_ids: list[str] | None = None,
) -> dict[str, dict]:
  """Finds the optimal dilution strategy for a dilution series and prints the details for what wells
  to use for each variable undiluted or initial dilution source.

  Args:
    n_variables: Number of variables to dilute
    n_dilutions: Number of dilutions to perform
    dilution_factors: Factor by which to dilute each time
    source_plate: Plate with the source wells
    target_plate: Plate with the target wells
    variables_volumes: Volume in the source wells. If None, will transfer the total well volume \
      divided by the dilution factor.
    variable_accession_ids: Names of the variables to dilute

  Returns:
    variable_details: Dictionary with the details of the dilution strategy for each variable

  """
  if n_dilutions * n_variables > target_plate.num_items:
    msg = "Number of dilutions exceeds number of wells in plate"
    raise ValueError(msg)
  dilution_factors, variables_volumes = await coerce_to_list(
    [dilution_factors, variables_volumes],
  )
  assert isinstance(dilution_factors, list)
  assert isinstance(variables_volumes, list)
  dilution_factors, variables_volumes = await check_list_length(
    items=[dilution_factors, variables_volumes],
    coerce_length=True,
    target_length=n_variables,
  )
  for dilution_factor in dilution_factors:
    if isinstance(dilution_factor, list):
      if len(dilution_factor) == 1:
        dilution_factor = dilution_factor * n_dilutions
      if len(dilution_factor) != n_dilutions:
        msg = "Number of dilutions does not match with dilution factors"
        raise ValueError(msg)
    else:
      dilution_factor = [dilution_factor] * n_dilutions
  if (
    n_variables <= target_plate.num_items_y and n_dilutions <= target_plate.num_items_x
  ):
    strategy = "all_row"
  else:
    strategy = "split_row"
  if variable_accession_ids is None:
    variable_accession_ids = [str(i) for i in range(n_variables)]
  variable_details: dict[str, dict] = {
    var: {"id": var} for var in variable_accession_ids
  }
  if strategy == "all_row":
    for i, var in enumerate(variable_accession_ids):
      variable_details[var]["initial_well"] = target_plate[i][0]
      variable_details[var]["initial_well_index"] = i
      variable_details[var]["dilution_strategy"] = "row"
  elif strategy == "split_row":
    for i, var in enumerate(variable_accession_ids):
      if i < target_plate.num_items_y:
        variable_details[var]["initial_well"] = target_plate[i][0]
        variable_details[var]["initial_well_index"] = i
        if n_dilutions > target_plate.num_items_x:
          variable_details[var]["dilution_strategy"] = "snake"
        variable_details[var]["dilution_strategy"] = "row"
      else:
        variable_details[var]["initial_well"] = target_plate[
          (i - target_plate.num_items_y) + (n_dilutions * target_plate.num_items_y)
        ][0]
        variable_details[var]["initial_well_index"] = (i - target_plate.num_items_y) + (
          n_dilutions * target_plate.num_items_y
        )
        variable_details[var]["dilution_strategy"] = "snake"
    for var in variable_details:
      _column, _row = await parse_well_name(variable_details[var]["initial_well"])
  return variable_details


async def optimal_dilution_transfer(
  liquid_handler: LiquidHandler,
  source_plate: Plate,
  target_plate: Plate,
  dilution_factor: float,
  source_wells: list[int],
  target_wells: list[int],
  dilution_tip_rack: TipRack,
  mix_cycles: int = 10,
  source_volumes: float | list[float] | None = None,
):
  pass


@liquid_handler_setup_check
async def antigen_dilution_series(
  liquid_handler: LiquidHandler,
  antigen_accession_ids: list[str],
  antigen_volumes: float | list[float],
  n_dilutions: int,
  mix_cycles: int,
  dilution_factors: float | list[float],
  buffer_total_volume: float,
  buffer_reservoir: Plate,
  dilution_plate: Plate,
  buffer_tips: TipRack,
  dilution_tips: TipRack,
  dilution_axis: Literal["row", "column", "x", "y", 0, 1, "optimal"] | None = "optimal",
  single_buffer: bool = True,
  use_96: bool = True,
):
  antigen_volumes, dilution_factors = await coerce_to_list(
    [antigen_volumes, dilution_factors],
  )
  assert isinstance(antigen_volumes, list) and isinstance(dilution_factors, list), (
    "Antigen volumes and dilution factors must be lists"
  )
  antigen_volumes, dilution_factors = await check_list_length(
    items=[antigen_volumes, dilution_factors],
    coerce_length=True,
    target_length=len(antigen_accession_ids),
  )
  if dilution_axis == "optimal":
    antigen_dilution_details = await find_optimal_dilution_strategy(
      n_variables=len(antigen_accession_ids),
      n_dilutions=n_dilutions,
      dilution_factors=dilution_factors,
      source_plate=dilution_plate,
      target_plate=dilution_plate,
      variables_volumes=antigen_volumes,
      variable_accession_ids=antigen_accession_ids,
      undiluted_source=True,
    )
  else:
    msg = "Only optimal dilution strategy implemented currently"
    raise NotImplementedError(msg)
  proceed = input("Proceed with dilution series? (y/n)")
  proceed = proceed.lower()

  async def check_input(proceed: str):
    if proceed not in ["y", "n", "yes", "no", ""]:
      proceed = input("Input invalid. Proceed with dilution series? (y/n)")
      proceed = proceed.lower()
      if proceed not in ["y", "n", "yes", "no", ""]:
        proceed = await check_input(proceed)
    return proceed

  proceed = await check_input(proceed)
  if proceed == "n":
    return antigen_dilution_details
    msg = "Dilution series aborted"
    raise RuntimeError(msg)
  buffer_transfer_volumes = [
    antigen_volumes[i] - antigen_volumes[i] / dilution_factors[i]
    for i in range(len(antigen_accession_ids))
  ]
  if len(set(buffer_transfer_volumes)) == 1:
    if use_96:
      if not single_buffer:
        msg = "Single buffer not specified but 96 transfer head specified"
        raise ValueError(msg)
      buffer_transfer_volume = buffer_transfer_volumes[0]
      await transfer_buffer96(
        liquid_handler=liquid_handler,
        tip_rack=buffer_tips,
        buffer_reservoir=buffer_reservoir,
        target_plate=dilution_plate,
        buffer_transfer_volume=buffer_transfer_volume,
        buffer_total_volume=buffer_total_volume,
        return_tips=True,
      )
    else:
      msg = "8-well transfer head not implemented"
      raise NotImplementedError(msg)
    await serial_dilution(
      liquid_handler=liquid_handler,
      tips=dilution_tips,
      plate=dilution_plate,
      variable_dict=antigen_dilution_details,
      n_dilutions=n_dilutions,
      dilution_factors=dilution_factors,
      source_volumes=antigen_volumes,
      mix_cycles=mix_cycles,
    )
  elif len(set(buffer_transfer_volumes)) != 1 and use_96:
    msg = (
      "Buffer transfer volumes not equal but 96 transfer head was specified \
      for buffer transfer"
    )
    raise ValueError(
      msg,
    )
  else:
    msg = "More complex dilution factors per variable not implemented"
    raise NotImplementedError(
      msg,
    )
  return None


@liquid_handler_setup_check
async def transfer_buffer96(
  liquid_handler: LiquidHandler,
  tip_rack: TipRack,
  buffer_reservoir: Plate,  # TODO: allow for reservoir
  target_plate: Plate,
  buffer_transfer_volume: float,
  buffer_total_volume: float,
  return_tips: bool = False,
):
  if buffer_transfer_volume * 96 > buffer_total_volume:
    msg = "Buffer volume insufficient"
    raise RuntimeError(msg)
  await liquid_handler.pick_up_tips96(tip_rack=tip_rack)
  await liquid_handler.aspirate96(
    resource=buffer_reservoir, volume=buffer_transfer_volume,
  )
  await liquid_handler.dispense96(resource=target_plate, volume=buffer_transfer_volume)
  if return_tips:
    await liquid_handler.drop_tips96(resource=tip_rack)


@liquid_handler_setup_check
async def serial_dilution(
  liquid_handler: LiquidHandler,  # TODO: handle single row and snaked dilutions that are longer than a column
  tips: TipRack,
  plate: Plate,
  variable_dict: dict[str, dict],
  n_dilutions: int,
  dilution_factors: float | list[float],
  source_volumes: float | list[float] | None = None,
  mix_cycles: int = 10,
):
  """Completes a serial dilution. Function assumes you are diluting from the top row of the source plate
  and diluting down the columns of the target plate. If you do not specify a source volume, the
  function will assume the maximum well volume divided by the dilution factor.

  Args:
    liquid_handler: LiquidHandler object
    n_dilutions: Number of dilutions to perform
    dilution_factor: Factor by which to dilute each time
    source: Plate with the source wells
    n_replicates: Number of replicates to perform. Per replicate, the dilution series will be \
      per column.
    source_volumes: Volume in the top columns of the source plate. If None, will transfer the \
      total well volume divided by the dilution factor.
    target_plate: Plate to transfer to. If None, will transfer on the source plate.

  """
  if source_volumes is None:
    source_volumes = [plate[0][0].max_volume] * len(variable_dict)
  dilution_factors, source_volumes = await coerce_to_list(
    [dilution_factors, source_volumes],
  )
  assert isinstance(dilution_factors, list)
  assert isinstance(source_volumes, list)
  dilution_factors, source_volumes = await check_list_length(
    [dilution_factors, source_volumes], True, len(variable_dict),
  )
  initial_wells = [variable_dict[var]["initial_well"] for var in variable_dict]
  tip_spots = await tip_mapping(tips=tips, sources=initial_wells, source_plate=plate)
  single_row, snaked = [], []
  for i, var in enumerate(variable_dict):
    variable_dict[var]["tip_spot"] = tip_spots[i]
    variable_dict[var]["source_volume"] = source_volumes[i]
    variable_dict[var]["dilution_factor"] = dilution_factors[i]
    variable_dict[var]["dilution_volume"] = source_volumes[i] / dilution_factors[i]
    if variable_dict[var]["dilution_strategy"] == "row":
      single_row.append(var)
    elif variable_dict[var]["dilution_strategy"] == "snake":
      snaked.append(var)
    else:
      msg = "Invalid dilution strategy"
      raise ValueError(msg)
  await liquid_handler.pick_up_tips(
    tip_spots=[variable_dict[var]["tip_spot"] for var in single_row],
  )
  for i in range(n_dilutions - 1):
    column_from = i * plate.num_items_y
    column_to = (i + 1) * plate.num_items_y
    wells_from = [
      variable_dict[var]["initial_well_index"] + column_from for var in single_row
    ]
    wells_to = [
      variable_dict[var]["initial_well_index"] + column_to for var in single_row
    ]
    dilution_volumes = [variable_dict[var]["dilution_volume"] for var in single_row]
    mix_volume = [int(dilution_volumes[j] * 0.5 * 10) for j in range(len(single_row))]
    mix_speed = [1200] * len(single_row)
    if i == 0:
      for well, var in zip(plate[wells_from], single_row, strict=False):
        well.variable_accession_id = variable_dict[var]["id"]
        well.dilution_factor = variable_dict[var]["dilution_factor"] ** i
      await liquid_handler.aspirate(
        resources=plate[wells_from],
        vols=dilution_volumes,
        homogenization_cycles=[mix_cycles] * len(single_row),
        homogenization_volume=mix_volume,
        homogenization_speed=mix_speed,
      )
    else:
      await liquid_handler.aspirate(resources=plate[wells_from], vols=dilution_volumes)
    await liquid_handler.dispense(
      resources=plate[wells_to],
      vols=dilution_volumes,
      mix_cycles=[mix_cycles] * len(single_row),
      mix_volume=mix_volume,
      mix_speed=mix_speed,
    )
    for well, var in zip(plate[wells_to], single_row, strict=False):
      well.variable_accession_id = variable_dict[var]["id"]
      well.dilution_factor = variable_dict[var]["dilution_factor"] ** i
  await liquid_handler.drop_tips(
    tip_spots=[variable_dict[var]["tip_spot"] for var in single_row],
  )
  if len(snaked) == 0:
    return
  if len(snaked) > tips.num_items_y:
    msg = "More variables than tips in tip rack"
    raise NotImplementedError(msg)
  await liquid_handler.pick_up_tips(
    tip_spots=[variable_dict[var]["tip_spot"] for var in snaked],
  )
  backward, next_rows = False, False
  dilution_volumes = [variable_dict[var]["dilution_volume"] for var in snaked]
  wells_from = [variable_dict[var]["initial_well_index"] for var in snaked]
  mix_volume = [int(dilution_volumes[j] * 0.5 * 10) for j in range(len(snaked))]
  mix_speed = [1200] * len(snaked)
  for i in range(n_dilutions - 1):
    if any(
      well + ((-1 if backward else 1) * plate.num_items_y) > plate.num_items
      for well in wells_from
    ):
      next_rows = True
      backward = True
    elif backward and any(
      well + ((-1 if backward else 1) * plate.num_items_y)
      < variable_dict[snaked[j]]["initial_well_index"]
      for j, well in enumerate(wells_from)
    ):
      next_rows = True
      backward = False
    if backward and not next_rows:
      wells_to = [well - plate.num_items_y for well in wells_from]
    if not backward and not next_rows:
      wells_to = [well + plate.num_items_y for well in wells_from]
    if next_rows:
      wells_to = [well + len(snaked) for well in wells_from]
      next_rows = False
    if i == 0:
      for well, var in zip(plate[wells_from], snaked, strict=False):
        well.variable_accession_id = variable_dict[var]["id"]
        well.dilution_factor = variable_dict[var]["dilution_factor"] ** i
      await liquid_handler.aspirate(
        resources=plate[wells_from],
        use_channels=list(range(len(snaked))),
        vols=dilution_volumes,
        homogenization_cycles=[mix_cycles] * len(snaked),
        homogenization_volume=mix_volume,
      )
    else:
      await liquid_handler.aspirate(
        resources=plate[wells_from],
        use_channels=list(range(len(snaked))),
        vols=dilution_volumes,
      )
    await liquid_handler.dispense(
      resources=plate[wells_to],
      use_channels=list(range(len(snaked))),
      vols=dilution_volumes,
      mix_cycles=[mix_cycles] * len(snaked),
      mix_volume=mix_volume,
    )
    for well, var in zip(plate[wells_to], snaked, strict=False):
      well.variable_accession_id = variable_dict[var]["id"]
      well.dilution_factor = variable_dict[var]["dilution_factor"] ** i
    wells_from = wells_to
  await liquid_handler.drop_tips(
    tip_spots=[variable_dict[var]["tip_spot"] for var in snaked],
  )


async def handle_dilution(
  liquid_handler: LiquidHandler,
  antigen_accession_ids: list[str],
  antigen_volumes: float | list[float],
  n_replicates: int,
  n_dilutions: int,
  mix_cycles: int,
  dilution_factors: float | list[float],
  buffer_total_volume: float,
  buffer_reservoir: Plate,
  dilution_plate: Plate,
  buffer_tips: TipRack,
  dilution_tips: TipRack,
  constant_dilution: bool = True,
) -> None:
  """Handles the dilution series for antigens."""
  if not isinstance(antigen_volumes, list) or not isinstance(dilution_factors, list):
    constant_dilution = True
  for i, _antigen_accession_id in enumerate(antigen_accession_ids):
    if constant_dilution:
      buffer_transfer_volumes = [
        antigen_volumes[i] - antigen_volumes[i] / dilution_factors[i],
      ] * n_dilutions
    else:
      msg = "More complex dilution factors per variable not implemented"
      raise NotImplementedError(
        msg,
      )
    column_index = i * dilution_plate.num_items_y
    dilution_wells = [j + (column_index) for j in range(n_dilutions)]
    await liquid_handler.pick_up_tips(
      tip_spots=buffer_tips[column_index : column_index + n_dilutions],
    )
    await transfer_buffer(
      liquid_handler=liquid_handler,
      buffer_reservoir=buffer_reservoir,
      target_wells=dilution_wells,
      target_plate=dilution_plate,
      buffer_volumes=buffer_transfer_volumes,
      buffer_total_volume=buffer_total_volume,
    )
    await liquid_handler.drop_tips(
      tip_spots=buffer_tips[column_index : column_index + n_dilutions],
    )
  await dilution_series(
    liquid_handler=liquid_handler,
    tips=dilution_tips,
    n_dilutions=n_dilutions,
    dilution_factors=dilution_factors,
    source_plate=dilution_plate,
    n_replicates=n_replicates,
    mix_cycles=mix_cycles,
    source_volumes=antigen_volumes,
    target_plate=dilution_plate,
  )


async def transfer_buffer(
  liquid_handler: LiquidHandler,
  buffer_reservoir: Plate,  # TODO: allow for reservoir
  target_plate: Plate,
  target_wells: int | str | list[int] | list[str] | list[Well],
  buffer_transfer_volumes: float | list[float],
  buffer_total_volume: float | list[float],
  buffer_wells: int | str | list[int] | list[str] | list[Well],
  mix_cycles: int = 0,
  mix_proportion: float = 0.5,
  mix_volumes: float | list[float] | None = None,
  single_buffer: bool = True,
):
  if single_buffer:
    if isinstance(buffer_total_volume, list) and len(buffer_total_volume) > 1:
      msg = "Total buffer volume variable list, but single buffer specified"
      raise ValueError(
        msg,
      )
    if sum(buffer_transfer_volumes) > buffer_total_volume:
      msg = "Buffer volume insufficient"
      raise Value(msg)
  await liquid_handler.aspirate(
    resources=buffer_reservoir[buffer_wells], vols=buffer_volumes,
  )
  await liquid_handler.dispense(target_plate[target_wells], vols=buffer_volumes)


@liquid_handler_setup_check
async def transfer_top_row(
  liquid_handler: LiquidHandler,
  tips: TipRack,
  source_plate: Plate,  # TODO: allow for reservoir
  target_plate: Plate,
):
  n_columns = source_plate.num_items_x
  if source_plate.num_items_x < n_columns or target_plate.num_items_x < n_columns:
    msg = (
      f"{'Source' if source_plate.num_items_x < n_columns else 'Target'} \
      plate does not have enough columns"
    )
    raise ExperimentError(
      msg,
    )
  for i in range(n_columns):
    liquid_handler.pick_up_tips(tip_spots=tips[i * n_columns])
    await liquid_handler.transfer(
      source_plate=source_plate,
      source_well=i,
      target_plate=target_plate,
      target_well=i,
      volume=source_plate.well_volume(i),
    )
    liquid_handler.drop_tips(tip_spots=tips[i * n_columns])


async def dilution_series(
  liquid_handler: LiquidHandler,
  tips: TipRack,
  n_dilutions: int,
  dilution_factors: float | list[float],
  source_plate: Plate,  # TODO: allow for reservoir
  mix_cycles: int = 10,
  source_volumes: int | list[int] | None = None,
  target_plate: Plate | None = None,
):
  """Completes a dilution series. If using replicates, these are treated as separate dilution series.
  Function assumes you are diluting from the top row of the source plate and diluting down the
  columns of the target plate.

  Args:
    liquid_handler: LiquidHandler object
    n_dilutions: Number of dilutions to perform
    dilution_factor: Factor by which to dilute each time
    source: Plate with the source wells
    n_replicates: Number of replicates to perform. Per replicate, the dilution series will be \
      per column.
    source_volumes: Volume in the top columns of the source plate. If None, will transfer the \
      total well volume divided by the dilution factor.
    target_plate: Plate to transfer to. If None, will transfer on the source plate.

  """
  if isinstance(dilution_factors, list) and len(dilution_factors) != n_replicates:
    msg = "Number of dilutions does not match with dilution factors."
    raise ExperimentError(msg)
  if isinstance(source_volumes, int):
    source_volumes = [source_volumes] * n_replicates
  if isinstance(source_volumes, list) and len(source_volumes) != n_replicates:
    msg = "Number of dilutions does not match with source volumes."
    raise ExperimentError(msg)
  if not liquid_handler.setup_finished:
    msg = "Liquid handler not set up."
    raise ExperimentError(msg)
  if n_dilutions > source_plate.num_items_y + 1:
    msg = "Number of dilutions exceeds number of wells per column in plate."
    raise ExperimentError(
      msg,
    )
  if n_replicates > source_plate.num_items_x:
    msg = "Number of replicates exceeds number of wells per row in plate."
    raise ExperimentError(
      msg,
    )
  if not target_plate or target_plate == source_plate:
    target_plate = source_plate
  else:
    await transfer_top_row(
      liquid_handler=liquid_handler,
      tips=tips,
      source_plate=source_plate,
      target_plate=target_plate,
    )
  for i in range(n_replicates):
    well_number = i * target_plate.num_items_y
    if source_volumes:
      source_volume = source_volumes[i]
    else:
      source_volume = source_plate.well_volume(i * source_plate.num_items_y)
    await liquid_handler.pick_up_tips(tips[well_number])
    for j in range(n_dilutions):
      well_number = well_number + j
      transfer_volume = source_volume / dilution_factors[i]
      await liquid_handler.aspirate(
        target_plate[well_number],
        vols=[transfer_volume],
        mix_volume=[transfer_volume * 10],
        mix_cycles=[mix_cycles],
      )
      if j != len(range(n_dilutions)):
        await liquid_handler.dispense(
          target_plate[well_number + 1], vols=[transfer_volume],
        )
    await liquid_handler.dispense(
      target_plate[well_number + 1],
      vols=[0],
      mix_volume=[transfer_volume * 10],
      mix_cycles=[mix_cycles],
    )
    await liquid_handler.drop_tips(tips[well_number - j])
