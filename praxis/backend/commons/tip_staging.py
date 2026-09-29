from praxis.utils.sanitation import parse_well_name
from pylabrobot.legacy.liquid_handling import LiquidHandler
from pylabrobot.resources import Plate, TipRack, Well


async def wash_tips96(
  liquid_handler: LiquidHandler,
  tip_racks: list[TipRack],
  water_stations: list[Plate],
  bleach_station: Plate,
  volume: float = 500,
):
  for tips in tip_racks:
    await liquid_handler.pick_up_tips96(tips)
    await liquid_handler.aspirate96(bleach_station, volume=volume)
    await liquid_handler.dispense96(bleach_station, volume=volume)
    for water_station in water_stations:
      await liquid_handler.aspirate96(water_station, volume=volume)
      await liquid_handler.dispense96(water_station, volume=volume)
    await liquid_handler.drop_tips96(tips)


async def split_tips_along_columns(wells: list[Well]) -> list[list[Well]]:
  if not all(isinstance(well, Well) for well in wells):
    msg = "Invalid well type."
    raise ValueError(msg)
  columns = [(await parse_well_name(well))[0] for well in wells]
  return [
    [well for column, well in zip(columns, wells, strict=False) if column == i]
    for i in range(max(columns) + 1)
  ]
