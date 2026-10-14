import asyncio

from pylabrobot.legacy.liquid_handling import LiquidHandler
from pylabrobot.legacy.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.resources import set_tip_tracking, set_volume_tracking
from pylabrobot.resources.corning import cor_96_wellplate_360uL_Fb
from pylabrobot.resources.hamilton import (
  STARLetDeck, hamilton_96_tiprack_300uL_filter, hamilton_plate_carrier_L5_ac, hamilton_tip_carrier_L5,
)


async def main():
  set_tip_tracking(True)
  set_volume_tracking(True)
  deck = STARLetDeck()
  lh = LiquidHandler(backend=LiquidHandlerChatterboxBackend(num_channels=8), deck=deck)
  await lh.setup()
  tip_car = hamilton_tip_carrier_L5(name="tip_carrier")
  tip_car[0] = tips = hamilton_96_tiprack_300uL_filter(name="tips")
  deck.assign_child_resource(tip_car, track=3)
  plate_car = hamilton_plate_carrier_L5_ac(name="plate_carrier")
  plate_car[0] = plate = cor_96_wellplate_360uL_Fb(name="plate")
  deck.assign_child_resource(plate_car, track=9)

  wells = plate.get_all_items()
  for w in wells:
    w.tracker.set_volume(100)
  wells[10].tracker.set_volume(0)  # one empty well: the tracker refuses aspirate96 at well index 10
  await lh.pick_up_tips96(tips)
  tip0 = lh.head96[0].get_tip().tracker

  try:
    await lh.aspirate96(plate, volume=50)
  except Exception as e:
    print("aspirate96 refused:", type(e).__name__)
  print("after refusal:  well 0 pending/committed =", wells[0].tracker.pending_volume, wells[0].tracker.volume,
        "| tip 0 pending/committed =", tip0.pending_volume, tip0.volume)

  wells[10].tracker.set_volume(100)
  await lh.aspirate96(plate, volume=10)  # succeeds; physically only these 10 uL move
  print("after success:  well 0 =", wells[0].tracker.volume, "(expected 90) | tip 0 =", tip0.volume, "(expected 10)")
  return wells[0].tracker.volume, tip0.volume


if __name__ == "__main__":
  well0, tip0_volume = asyncio.run(main())
  # --- not part of the issue snippet: record the result for bathos ---
  import json, os, subprocess, pylabrobot
  from pathlib import Path
  root = Path(pylabrobot.__file__).resolve().parent.parent
  sha = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
  dirty = bool(subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
                              capture_output=True, text=True).stdout.strip()) or sha == "unknown"
  if os.environ.get("BTH_RESULTS_PATH"):
    Path(os.environ["BTH_RESULTS_PATH"]).write_text(json.dumps(
      {"plr_git_sha": sha, "plr_git_dirty": dirty, "well0_after_success": well0, "tip0_after_success": tip0_volume}) + "\n")
