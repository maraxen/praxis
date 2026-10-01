#!/usr/bin/env python3
"""Standalone reproduction for an UPSTREAM PyLabRobot report (draft only, nothing is filed from here).

Claim under test: in the legacy ``LiquidHandler``, the 96-head operations queue their tracker changes OUTSIDE the
``try`` whose ``except`` rolls back, so when a tracker refuses the operation partway through (``TooLittleLiquidError``
on the 11th well), the wells/tips already visited keep PENDING changes that nothing rolls back, and the next operation
that SUCCEEDS commits them: the tracked volumes then disagree with what the robot physically did.

The 1-channel ``aspirate`` is the control: it queues inside its ``try`` (liquid_handler.py, with a comment saying a
tracker that refuses rolls every channel back "just like a backend error"), so the same refusal leaves no residue.

Only PyLabRobot is imported (no Praxis code), so the maintainers can run this file as is on a checkout:

    python 261001_plr_96head_pending_residue_repro.py            # prints a JSON summary

Under ``bth run`` the flat fields are also written to $BTH_RESULTS_PATH (see the sidecar next to this file).

Scenario (all volumes in uL, 96-well plate "source", chatterbox backend, volume + tip tracking ON):
  control (1-channel): 8 channels hold tips; wells A1..G1 = 100, H1 = 0; aspirate 50 uL from A1:H1 -> refused at H1.
  96-head: 96 tips held; wells 0..95 = 100 except well 10 = 0; aspirate96(plate, 50) -> refused at well 10 after wells 0..9
  and tips 0..9 were already queued. Then well 10 is refilled to 100 and aspirate96(plate, 10) is called and SUCCEEDS.
  Physical truth after the two calls: only the 10 uL of the second call moved: well 0 = 90, tip 0 holds 10.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pylabrobot
from pylabrobot.legacy.liquid_handling import LiquidHandler
from pylabrobot.legacy.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.resources import set_tip_tracking, set_volume_tracking
from pylabrobot.resources.corning import cor_96_wellplate_360uL_Fb
from pylabrobot.resources.hamilton import (
  STARLetDeck,
  hamilton_96_tiprack_300uL_filter,
  hamilton_plate_carrier_L5_ac,
  hamilton_tip_carrier_L5,
)

log = logging.getLogger("plr_96head_residue_repro")

REFUSED_WELL_INDEX = 10  # the 96-head loop visits wells in order; it is refused at this one
FIRST_VOLUME = 50.0  # the refused call
SECOND_VOLUME = 10.0  # the call that succeeds afterwards
WELL_START = 100.0


async def fresh() -> tuple[Any, Any, Any]:
  """A new chatterbox STARLet with one tip rack and one 96-well plate; tracking on."""
  set_tip_tracking(True)
  set_volume_tracking(True)
  deck = STARLetDeck()
  lh = LiquidHandler(backend=LiquidHandlerChatterboxBackend(num_channels=8), deck=deck)
  await lh.setup()
  tip_car = hamilton_tip_carrier_L5(name="tip_carrier")
  tip_car[0] = tips = hamilton_96_tiprack_300uL_filter(name="tips")
  deck.assign_child_resource(tip_car, track=3)
  plate_car = hamilton_plate_carrier_L5_ac(name="plate_carrier")
  plate_car[0] = plate = cor_96_wellplate_360uL_Fb(name="source")
  deck.assign_child_resource(plate_car, track=9)
  return lh, tips, plate


def residue(trackers: list[Any]) -> list[int]:
  """Indexes of trackers whose pending state differs from their committed state."""
  return [i for i, t in enumerate(trackers) if t.pending_volume != t.volume]


async def control_one_channel() -> dict[str, Any]:
  lh, tips, plate = await fresh()
  wells = [plate.get_item(f"{r}1") for r in "ABCDEFGH"]
  for w in wells:
    w.tracker.set_volume(WELL_START)
  wells[7].tracker.set_volume(0.0)  # H1 is empty: the 8-channel aspirate is refused at channel 7
  await lh.pick_up_tips(tips["A1:H1"])
  raised = None
  try:
    await lh.aspirate(plate["A1:H1"], vols=[FIRST_VOLUME] * 8)
  except Exception as e:  # noqa: BLE001 -- recording whatever PLR raises is the point
    raised = e
  tip_trackers = [lh.head[c].get_tip().tracker for c in range(8)]
  return {
    "control_refused": raised is not None,
    "control_exception": type(raised).__name__ if raised else None,
    "control_residue_wells": residue([w.tracker for w in wells]),
    "control_residue_tips": residue(tip_trackers),
  }


async def residue_96() -> dict[str, Any]:
  lh, tips, plate = await fresh()
  wells = plate.get_all_items()
  for w in wells:
    w.tracker.set_volume(WELL_START)
  wells[REFUSED_WELL_INDEX].tracker.set_volume(0.0)
  await lh.pick_up_tips96(tips)
  tip_trackers = [lh.head96[c].get_tip().tracker for c in range(96)]

  first_exc = None
  try:
    await lh.aspirate96(plate, volume=FIRST_VOLUME)
  except Exception as e:  # noqa: BLE001
    first_exc = e
  after_refusal = {
    "wells": residue([w.tracker for w in wells]),
    "tips": residue(tip_trackers),
    "well0_pending": wells[0].tracker.pending_volume,
    "well0_committed": wells[0].tracker.volume,
    "tip0_pending": tip_trackers[0].pending_volume,
    "tip0_committed": tip_trackers[0].volume,
  }

  wells[REFUSED_WELL_INDEX].tracker.set_volume(WELL_START)  # refill the empty well, then retry with a smaller volume
  second_exc = None
  try:
    await lh.aspirate96(plate, volume=SECOND_VOLUME)
  except Exception as e:  # noqa: BLE001
    second_exc = e
  return {
    "refused_96": first_exc is not None,
    "refused_exception": type(first_exc).__name__ if first_exc else None,
    "refused_message": str(first_exc) if first_exc else None,
    "second_call_succeeded": second_exc is None,
    "residue_after_refusal_wells": after_refusal["wells"],
    "residue_after_refusal_tips": after_refusal["tips"],
    "well0_pending_after_refusal": after_refusal["well0_pending"],
    "well0_committed_after_refusal": after_refusal["well0_committed"],
    "tip0_pending_after_refusal": after_refusal["tip0_pending"],
    "tip0_committed_after_refusal": after_refusal["tip0_committed"],
    "well0_committed_after_success": wells[0].tracker.volume,
    "well0_physical_truth": WELL_START - SECOND_VOLUME,
    "tip0_committed_after_success": tip_trackers[0].volume,
    "tip0_physical_truth": SECOND_VOLUME,
  }


def flatten(control: dict[str, Any], run96: dict[str, Any]) -> dict[str, Any]:
  """Flat, SQL-friendly fields for the sidecar's outcomes (bools, ints, floats and strings only)."""
  wells_res = run96["residue_after_refusal_wells"]
  tips_res = run96["residue_after_refusal_tips"]
  return {
    "plr_version": getattr(pylabrobot, "__version__", "unknown"),
    "control_refused": control["control_refused"],
    "control_rolled_back": not control["control_residue_wells"] and not control["control_residue_tips"],
    "control_exception": control["control_exception"] or "",
    "refused_96": run96["refused_96"],
    "refused_exception": run96["refused_exception"] or "",
    "second_call_succeeded": run96["second_call_succeeded"],
    "n_residue_wells_after_refusal": len(wells_res),
    "n_residue_tips_after_refusal": len(tips_res),
    "residue_after_refusal": bool(wells_res or tips_res),
    "well0_pending_after_refusal": run96["well0_pending_after_refusal"],
    "well0_committed_after_refusal": run96["well0_committed_after_refusal"],
    "tip0_pending_after_refusal": run96["tip0_pending_after_refusal"],
    "tip0_committed_after_refusal": run96["tip0_committed_after_refusal"],
    "well0_committed_after_success": run96["well0_committed_after_success"],
    "well0_physical_truth": run96["well0_physical_truth"],
    "tip0_committed_after_success": run96["tip0_committed_after_success"],
    "tip0_physical_truth": run96["tip0_physical_truth"],
    "phantom_well": run96["well0_committed_after_success"] != run96["well0_physical_truth"],
    "phantom_tip": run96["tip0_committed_after_success"] != run96["tip0_physical_truth"],
  }


async def run() -> dict[str, Any]:
  control = await control_one_channel()
  run96 = await residue_96()
  return flatten(control, run96)


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("-v", "--verbose", action="store_true")
  args = parser.parse_args(argv)
  logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
  fields = asyncio.run(run())
  text = json.dumps(fields, indent=2, sort_keys=True)
  print(text)
  out = os.environ.get("BTH_RESULTS_PATH")
  if out:
    Path(out).write_text(text + "\n", encoding="utf-8")
    log.info("wrote %s", out)
  return 0


if __name__ == "__main__":
  sys.exit(main())
