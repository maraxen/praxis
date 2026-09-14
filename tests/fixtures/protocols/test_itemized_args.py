from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.resources import Well


async def test_itemized_args(
  lh: LiquidHandler,
  source_wells: list[Well],
):
  """Test protocol for itemized arguments.

  This protocol takes a list of wells and iterates over them.
  It is used to verify that the tracer handles itemized arguments correctly.
  """
  await lh.pick_up_tips(source_wells[0])

  for well in source_wells:
    await lh.aspirate(well, vol=10)
    await lh.dispense(well, vol=10)

  await lh.drop_tips()
