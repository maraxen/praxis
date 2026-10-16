---
title: 'Upstream PyLabRobot issue body (ready to file): tracker state desync when a refusal is raised before the rollback block'
description: Final issue text for PyLabRobot/pylabrobot. The user wrote the title and TL;DR; Claude composed the report below the disclosure line. Every number in it comes from pre-registered bathos runs (ee04302a for the inline snippet; 59c963d1/ace4dd8c for the table; 46e29dbc/eae83bee for aspirate96). Filed 2026-10-14 as https://github.com/PyLabRobot/pylabrobot/issues/1483.
status: final
task_id: 260929_notebook-display-design
date: '261014'
backlog_id: 5659
---

<!-- Everything between the two rules below is the issue as it would be filed. -->

---

**Title:** State desync: tracker changes are queued before the rollback block, so an error partway through leaves state half-updated (at least for 96-head ops)

**TL;DR (written by me):** `pick_up_tips96`, `drop_tips96`, `aspirate96` and `dispense96`, and also the single-channel `pick_up_tips` and `drop_tips`, update the trackers in a loop before the `try` whose `except` rolls them back. When a tracker check fails partway through that loop, the channels already visited keep their changes, even though no command has been sent to the backend, so nothing can have physically happened. Consequently, the tracked state disagrees with the deck, and the next successful operation saves those changes along with its own, so the trackers record events that never happened. Single-channel `aspirate` and `dispense` already do this correctly, by queuing inside the `try`. I think we should make that standard across these methods, and any future/other method that updates trackers before calling the backend.

*Claude-composed full report is disclosed below and should have all details.*

---

### Summary

In `pylabrobot/legacy/liquid_handling/liquid_handler.py`, six operations queue their tracker changes (`commit=False`, pending volumes) in a loop that runs **before** the `try` whose `except` calls `rollback()`. If a tracker check raises inside that loop, the `except` never runs: the channels, tip spots, wells and tips already visited keep their pending changes. The backend has not been called, so nothing moved. The next operation that succeeds calls `commit()` on the same trackers and makes those changes permanent.

With tip tracking on, the tip operations' leftovers are visible immediately, before any commit, because a tip is a child of its spot in the resource tree.

Single-channel `aspirate` and `dispense` queue inside the `try` and say why ([L1265-L1266](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L1265-L1266)):

```python
# actually aspirate the liquid. The trackers are queued inside the try, so a tracker that
# refuses an operation rolls every channel back below, just like a backend error.
```

### Reproduction (`aspirate96`)

Chatterbox backend, tip and volume tracking on. One empty well makes the volume tracker refuse `aspirate96` at well index 10, after wells 0–9 and tips 0–9 were queued:

```python
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


asyncio.run(main())
```

Output on `main` ([`93aa7c402`](https://github.com/PyLabRobot/pylabrobot/commit/93aa7c402ae3bbd54e008175044b51b6b8d24ee7)):

```
aspirate96 refused: TooLittleLiquidError
after refusal:  well 0 pending/committed = 50.0 100 | tip 0 pending/committed = 50.0 0
after success:  well 0 = 40.0 (expected 90) | tip 0 = 60.0 (expected 10)
```

The same happens on the 1.0.0b1 release (`786ac2c4e`). Note that `pylabrobot.__version__` reads `1.0.0b1` at both commits.

### All affected operations

Each row forces one refusal from inside the operation's queue loop and counts the trackers left with pending ≠ committed. Same deck as above; identical results on `93aa7c402` and `786ac2c4e`.

| Operation | Queue loop / `try` at `93aa7c402` | Refusal forced by | Raised | Left pending | Tracked state afterwards (nothing moved) |
|---|---|---|---|---|---|
| `pick_up_tips96` | [L1714-L1727](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L1714-L1727) / [L1730](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L1730) | channel 10 already holds a tip | `HasTipError` | 10 channels, 10 tip spots | spot 0 reads empty, channel 0 reads holding a tip |
| `drop_tips96` | [L1795-L1808](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L1795-L1808) / [L1811](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L1811) | tip 10 holds liquid | `RuntimeError` (nonzero volume, raised inside the loop) | 10 channels, 10 tip spots | channel 0 reads empty, spot 0 reads holding a tip |
| `aspirate96` | [L2010-L2017](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L2010-L2017), [L2039-L2046](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L2039-L2046) / [L2059](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L2059) | well 10 is empty | `TooLittleLiquidError` | 10 wells, 10 tips | after a later successful `aspirate96`: well 0 = 40 µL (truth 90), tip 0 = 60 µL (truth 10) |
| `dispense96` | [L2158-L2165](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L2158-L2165), [L2195-L2200](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L2195-L2200) / [L2213](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L2213) | tip 10 holds 5 µL, 20 µL dispensed | `TooLittleLiquidError` | 10 tips | after a later successful 5 µL `dispense96`: tip 0 = 25 µL (truth 45) |
| `pick_up_tips` | [L755-L761](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L755-L761) / [L775](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L775) | channel 1 already holds a tip (`use_channels=[0, 1]`) | `HasTipError` | channel 0, spot A1 | |
| `drop_tips` | [L901-L909](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L901-L909) / [L923](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L923) | destination C1 already holds a tip | `HasTipError` | channel 0, spot A1 | |
| *control:* `dispense` | queued inside the `try` at [L1469](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L1466-L1469) | tip on channel 1 too short | `TooLittleLiquidError` | **nothing** | |

The script behind the table is below (PyLabRobot only). It counts residue as `tracker._pending_tip is not tracker._tip` for tip trackers and `pending_volume != volume` for volume trackers.

<details>
<summary>tip_dispense_residue_repro.py (all six operations + the control)</summary>

```python
#!/usr/bin/env python3
"""Standalone reproductions for an UPSTREAM PyLabRobot report: tracker changes queued ahead of the rollback block.

Companion to ``261001_plr_96head_pending_residue_repro.py`` / ``261014_plr_96head_residue_repro_latest.py`` (which cover
``aspirate96``). This file covers the other operations whose tracker queue loop sits OUTSIDE the ``try`` whose ``except``
rolls back, in ``pylabrobot/legacy/liquid_handling/liquid_handler.py``:

  pick_up_tips96  refused by HasTipError at channel 10 (a stray tip on head96[10]) after channels 0..9 were queued
  drop_tips96     refused by the nonzero-volume RuntimeError at channel 10 (tip 10 holds liquid) after 0..9 were queued
  dispense96      refused by TooLittleLiquidError at tip 10 (tip 10 holds less than the dispense volume) after 0..9;
                  then a smaller dispense96 SUCCEEDS and commits the leftovers (tip 0's committed volume vs physical truth)
  pick_up_tips    (1 channel) refused by HasTipError at channel 1 (stray tip) after channel 0 / spot A1 were queued
  drop_tips       (1 channel) refused by HasTipError at channel 1 (destination spot C1 is occupied) after channel 0 / A1

NEGATIVE control: the 1-channel ``dispense``, which queues inside its ``try`` (PLR comment: "a tracker that refuses an
operation rolls every channel back"), refused the same way as dispense96 (tip on channel 1 too short): it must leave no
residue, which shows the residue check does not report residue by construction.

A tracker has residue when its pending state differs from its committed state: for a tip tracker the pending tip is not
the committed tip (``_pending_tip is not _tip``), for a volume tracker ``pending_volume != volume``.

Only PyLabRobot is imported, so maintainers can run it as is on a checkout. Prints a JSON summary; under ``bth run`` the
flat fields are also written to $BTH_RESULTS_PATH. Volumes in uL; chatterbox backend; tip and volume tracking ON.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
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

log = logging.getLogger("plr_tip_dispense_residue_repro")

REFUSED = 10  # the 96-head loops visit channels in order; each 96-head scenario is refused at this one
WELL_START = 100.0
ASPIRATED = 50.0  # what every tip holds before the dispense scenarios
SHORT_TIP = 5.0  # what the short tip holds
FIRST_DISPENSE = 20.0  # refused: more than SHORT_TIP
SECOND_DISPENSE = 5.0  # succeeds afterwards


def plr_git() -> tuple[str, bool]:
  """(commit, dirty) of the PyLabRobot checkout that was imported; ("unknown", True) if it is not a git checkout."""
  root = Path(pylabrobot.__file__).resolve().parent.parent
  try:
    sha = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
                                capture_output=True, text=True, check=True).stdout.strip())
  except (OSError, subprocess.CalledProcessError):
    return "unknown", True
  return sha, dirty


async def fresh() -> tuple[Any, Any, Any, Any]:
  """A new chatterbox STARLet: one 300 uL tip rack, a source and a destination 96-well plate; tracking on."""
  set_tip_tracking(True)
  set_volume_tracking(True)
  deck = STARLetDeck()
  lh = LiquidHandler(backend=LiquidHandlerChatterboxBackend(num_channels=8), deck=deck)
  await lh.setup()
  tip_car = hamilton_tip_carrier_L5(name="tip_carrier")
  tip_car[0] = tips = hamilton_96_tiprack_300uL_filter(name="tips")
  deck.assign_child_resource(tip_car, track=3)
  plate_car = hamilton_plate_carrier_L5_ac(name="plate_carrier")
  plate_car[0] = source = cor_96_wellplate_360uL_Fb(name="source")
  plate_car[1] = dest = cor_96_wellplate_360uL_Fb(name="dest")
  deck.assign_child_resource(plate_car, track=9)
  for w in source.get_all_items():
    w.tracker.set_volume(WELL_START)
  return lh, tips, source, dest


def spare_tip() -> Any:
  """A tip that is not on the deck, to put a stray tip on a channel."""
  return hamilton_96_tiprack_300uL_filter(name="spare").get_item(0).get_tip()


def tip_residue(trackers: list[Any]) -> list[int]:
  return [i for i, t in enumerate(trackers) if t._pending_tip is not t._tip]


def volume_residue(trackers: list[Any]) -> list[int]:
  return [i for i, t in enumerate(trackers) if t.pending_volume != t.volume]


async def attempt(coro: Any) -> BaseException | None:
  try:
    await coro
  except Exception as e:  # noqa: BLE001 -- recording whatever PLR raises is the point
    return e
  return None


def exc_name(e: BaseException | None) -> str:
  return type(e).__name__ if e is not None else ""


async def pick_up_tips96_case() -> dict[str, Any]:
  lh, tips, _, _ = await fresh()
  lh.head96[REFUSED].add_tip(spare_tip(), commit=True)
  e = await attempt(lh.pick_up_tips96(tips))
  heads = tip_residue([lh.head96[c] for c in range(96)])
  spots = tip_residue([s.tracker for s in tips.get_all_items()])
  return {
    "p96_refused": e is not None, "p96_exception": exc_name(e),
    "p96_residue_channels": len([c for c in heads if c != REFUSED]), "p96_residue_spots": len(spots),
    "p96_spot0_has_tip_in_tree": tips.get_item(0).has_tip(),  # physically the tip is still in the rack
    "p96_channel0_has_tip": lh.head96[0].has_tip,  # physically channel 0 holds nothing
  }


async def drop_tips96_case() -> dict[str, Any]:
  lh, tips, _, _ = await fresh()
  await lh.pick_up_tips96(tips)
  t10 = lh.head96[REFUSED].get_tip().tracker
  t10.add_liquid(volume=SHORT_TIP)
  t10.commit()
  e = await attempt(lh.drop_tips96(tips))
  heads = tip_residue([lh.head96[c] for c in range(96)])
  spots = tip_residue([s.tracker for s in tips.get_all_items()])
  return {
    "d96_refused": e is not None, "d96_exception": exc_name(e),
    "d96_residue_channels": len(heads), "d96_residue_spots": len(spots),
    "d96_channel0_has_tip": lh.head96[0].has_tip,  # physically channel 0 still holds its tip
    "d96_spot0_has_tip_in_tree": tips.get_item(0).has_tip(),  # physically spot 0 is empty
  }


async def dispense96_case() -> dict[str, Any]:
  lh, tips, source, dest = await fresh()
  await lh.pick_up_tips96(tips)
  await lh.aspirate96(source, volume=ASPIRATED)
  tip_trackers = [lh.head96[c].get_tip().tracker for c in range(96)]
  tip_trackers[REFUSED].remove_liquid(ASPIRATED - SHORT_TIP)
  tip_trackers[REFUSED].commit()
  e = await attempt(lh.dispense96(dest, volume=FIRST_DISPENSE))
  tips_res = volume_residue(tip_trackers)
  wells_res = volume_residue([w.tracker for w in dest.get_all_items()])
  tip0_pending, tip0_committed = tip_trackers[0].pending_volume, tip_trackers[0].volume
  e2 = await attempt(lh.dispense96(dest, volume=SECOND_DISPENSE))
  truth = ASPIRATED - SECOND_DISPENSE  # only the second dispense moved liquid
  return {
    "s96_refused": e is not None, "s96_exception": exc_name(e),
    "s96_residue_tips": len(tips_res), "s96_residue_wells": len(wells_res),
    "s96_tip0_pending_after_refusal": tip0_pending, "s96_tip0_committed_after_refusal": tip0_committed,
    "s96_second_call_succeeded": e2 is None,
    "s96_tip0_committed_after_success": tip_trackers[0].volume, "s96_tip0_physical_truth": truth,
    "s96_phantom_tip": tip_trackers[0].volume != truth,
  }


async def pick_up_tips1_case() -> dict[str, Any]:
  lh, tips, _, _ = await fresh()
  lh.head[1].add_tip(spare_tip(), commit=True)
  e = await attempt(lh.pick_up_tips(tips["A1:B1"], use_channels=[0, 1]))
  return {
    "p1_refused": e is not None, "p1_exception": exc_name(e),
    "p1_residue_channels": len([c for c in tip_residue([lh.head[0], lh.head[1]]) if c != 1]),
    "p1_residue_spots": len(tip_residue([s.tracker for s in tips["A1:B1"]])),
  }


async def drop_tips1_case() -> dict[str, Any]:
  lh, tips, _, _ = await fresh()
  await lh.pick_up_tips(tips["A1:B1"], use_channels=[0, 1])
  e = await attempt(lh.drop_tips([tips.get_item("A1"), tips.get_item("C1")], use_channels=[0, 1]))
  return {
    "d1_refused": e is not None, "d1_exception": exc_name(e),
    "d1_residue_channels": len(tip_residue([lh.head[0], lh.head[1]])),
    "d1_residue_spots": len(tip_residue([tips.get_item("A1").tracker, tips.get_item("C1").tracker])),
  }


async def dispense1_control() -> dict[str, Any]:
  lh, tips, source, dest = await fresh()
  await lh.pick_up_tips(tips["A1:B1"], use_channels=[0, 1])
  await lh.aspirate(source["A1:B1"], vols=[ASPIRATED] * 2, use_channels=[0, 1])
  tip_trackers = [lh.head[c].get_tip().tracker for c in (0, 1)]
  tip_trackers[1].remove_liquid(ASPIRATED - SHORT_TIP)
  tip_trackers[1].commit()
  e = await attempt(lh.dispense(dest["A1:B1"], vols=[FIRST_DISPENSE] * 2, use_channels=[0, 1]))
  res = volume_residue(tip_trackers) + volume_residue([w.tracker for w in dest["A1:B1"]])
  return {"control_refused": e is not None, "control_exception": exc_name(e), "control_rolled_back": not res}


async def run() -> dict[str, Any]:
  out: dict[str, Any] = {}
  for case in (dispense1_control, pick_up_tips96_case, drop_tips96_case, dispense96_case, pick_up_tips1_case, drop_tips1_case):
    out.update(await case())
  out["residue_p96"] = out["p96_residue_channels"] > 0 or out["p96_residue_spots"] > 0
  out["residue_d96"] = out["d96_residue_channels"] > 0 or out["d96_residue_spots"] > 0
  out["residue_s96"] = out["s96_residue_tips"] > 0
  out["residue_p1"] = out["p1_residue_channels"] > 0 or out["p1_residue_spots"] > 0
  out["residue_d1"] = out["d1_residue_channels"] > 0 or out["d1_residue_spots"] > 0
  return out


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("-v", "--verbose", action="store_true")
  args = parser.parse_args(argv)
  logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
  sha, dirty = plr_git()
  fields = {"plr_version": getattr(pylabrobot, "__version__", "unknown"), "plr_git_sha": sha, "plr_git_dirty": dirty,
            "plr_source": str(Path(pylabrobot.__file__).resolve().parent)}
  fields.update(asyncio.run(run()))
  text = json.dumps(fields, indent=2, sort_keys=True)
  print(text)
  out = os.environ.get("BTH_RESULTS_PATH")
  if out:
    Path(out).write_text(text + "\n", encoding="utf-8")
    log.info("wrote %s", out)
  return 0


if __name__ == "__main__":
  sys.exit(main())
```

</details>

### What was run and what was not

- Run: everything in the table, on the chatterbox backend, at the two commits above.
- Not run: real hardware. The queue loops execute before any backend call, so the backend should not matter, but this was not tested on a STAR.
- Not covered: backend failures partway through a move. Those already reach the `except`. Whether a rollback is right there is a separate, harder question, because the physical state is genuinely uncertain.

### Suggested fix

Move each queue loop inside its `try`, as in single-channel `aspirate`/`dispense`, so that a tracker refusal reaches the same `rollback()` as a backend error. In `drop_tips96`, the nonzero-volume check could also move ahead of the loop, as single-channel `drop_tips` already does at [L878-L883](https://github.com/PyLabRobot/pylabrobot/blob/93aa7c402ae3bbd54e008175044b51b6b8d24ee7/pylabrobot/legacy/liquid_handling/liquid_handler.py#L878-L883). A regression test per operation: force a refusal inside the loop, then assert that every tracker's pending state equals its committed state.

---
