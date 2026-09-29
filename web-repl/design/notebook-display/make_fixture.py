"""Build the design prototype's fixture from a real PyLabRobot deck.

The prototype renders PLR geometry (sizes, locations, well grids) rather than
invented shapes, so this script assembles a small STARlet layout, runs a few
simulated liquid-handling steps on the chatterbox backend, and writes what the
notebook display layer would receive: the serialized deck plus per-well volume
and tip-presence state, and a log of the operations.

Design fixture only -- it produces no finding.

  uv run --no-sync python web-repl/design/notebook-display/make_fixture.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import traceback
from pathlib import Path

import pylabrobot
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.resources import set_tip_tracking, set_volume_tracking
from pylabrobot.resources.corning.plates import Cor_96_wellplate_360ul_Fb
from pylabrobot.resources.hamilton import (
  PLT_CAR_L5AC_A00,
  STARLetDeck,
  TIP_CAR_480_A00,
  hamilton_96_tiprack_300uL_filter,
)

log = logging.getLogger("make_fixture")
HERE = Path(__file__).resolve().parent


async def assemble() -> tuple[STARLetDeck, LiquidHandler]:
  """The layout: tips on rail 3, a source and an assay plate on rail 9."""
  set_tip_tracking(True)
  set_volume_tracking(True)

  deck = STARLetDeck()
  lh = LiquidHandler(backend=LiquidHandlerChatterboxBackend(num_channels=8), deck=deck)
  await lh.setup()

  tip_car = TIP_CAR_480_A00(name="tip_carrier")
  tip_car[0] = hamilton_96_tiprack_300uL_filter(name="tips_300")
  deck.assign_child_resource(tip_car, rails=3)

  plate_car = PLT_CAR_L5AC_A00(name="plate_carrier")
  plate_car[0] = source = Cor_96_wellplate_360ul_Fb(name="source")
  plate_car[1] = Cor_96_wellplate_360ul_Fb(name="assay")
  deck.assign_child_resource(plate_car, rails=9)

  for well in source.get_all_items():
    well.tracker.set_volume(200.0)
  return deck, lh


async def run_transfers(lh: LiquidHandler, deck: STARLetDeck) -> list[dict]:
  """Column-wise transfers source -> assay at 50, 100 and 150 uL, fresh tips each."""
  source, dest, tips = deck.get_resource("source"), deck.get_resource("assay"), deck.get_resource("tips_300")
  ops: list[dict] = []
  for col, vol in ((1, 50.0), (2, 100.0), (3, 150.0)):
    await lh.pick_up_tips(tips[f"A{col}:H{col}"])
    ops.append({"op": "pick_up_tips", "target": f"tips_300 col {col}", "channels": 8})
    await lh.aspirate(source[f"A{col}:H{col}"], vols=[vol] * 8)
    ops.append({"op": "aspirate", "target": f"source col {col}", "volume_ul": vol, "channels": 8})
    await lh.dispense(dest[f"A{col}:H{col}"], vols=[vol] * 8)
    ops.append({"op": "dispense", "target": f"assay col {col}", "volume_ul": vol, "channels": 8})
    await lh.discard_tips()
    ops.append({"op": "discard_tips", "target": "trash", "channels": 8})
  return ops


async def build() -> dict:
  deck, lh = await assemble()
  ops = await run_transfers(lh, deck)
  source, dest, tips = deck.get_resource("source"), deck.get_resource("assay"), deck.get_resource("tips_300")

  def state_of(plate) -> dict:
    return {w.get_identifier(): round(w.tracker.get_used_volume(), 3) for w in plate.get_all_items()}

  data = {
    "generator": "web-repl/design/notebook-display/make_fixture.py",
    "deck": deck.serialize(),
    "volumes": {"source": state_of(source), "assay": state_of(dest)},
    "max_volume_ul": source.get_item("A1").max_volume,
    "tips": {s.get_identifier(): s.has_tip() for s in tips.get_all_items()},
    "ops": ops,
  }

  # The error cell: over-aspirate from a column that holds 50 uL. State above is taken
  # first, so this does not leak into it.
  await lh.pick_up_tips(tips["A4:H4"])
  try:
    await lh.aspirate(dest["A1:H1"], vols=[80.0] * 8)
  except Exception as e:  # noqa: BLE001 -- recording whatever PLR raises is the point
    data["error"] = {
      "type": type(e).__name__,
      "module": type(e).__module__,
      "message": str(e),
      "traceback": _as_in_kernel(traceback.format_exc(limit=-4)),
    }
  return data


def _as_in_kernel(tb: str) -> str:
  """Rewrite local paths to what a Pyodide kernel shows, so no home path is committed."""
  plr_root = str(Path(pylabrobot.__file__).resolve().parent.parent) + "/"
  return tb.replace(plr_root, "/lib/python3.12/site-packages/").replace(str(Path(__file__).resolve()), "<cell 6>")


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", type=Path, default=HERE / "fixture.js")
  args = ap.parse_args()
  logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
  data = asyncio.run(build())
  args.out.write_text("window.PRAXIS_FIXTURE = " + json.dumps(data, separators=(",", ":")) + ";\n")
  log.info("wrote %s (%d bytes, %d ops)", args.out, args.out.stat().st_size, len(data["ops"]))


if __name__ == "__main__":
  main()
