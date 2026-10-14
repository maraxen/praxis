---
title: 'DRAFT (not filed): PyLabRobot legacy 96-head ops leave pending tracker changes after a refusal'
description: Draft upstream issue for PyLabRobot. The four legacy 96-head operations queue volume and tip tracker changes before the try block whose except rolls back, so a refused operation leaves pending state that the next successful operation commits. Includes a verified standalone reproduction (bathos run 55627ffd) and the exact source references at the Praxis pin. Written for the user to file or not; nothing has been filed.
status: draft
task_id: 260929_notebook-display-design
date: '261001'
backlog_id: 5659
---

# DRAFT, NOT FILED. For the user to review, verify against upstream `main`, and file (or not).

Target: `PyLabRobot/pylabrobot` (issue). Everything below was checked against the version Praxis pins:
**PyLabRobot 1.0.0b1, commit `786ac2c4e` ("Release 1.0.0b1 with complete package assets")**, `pylabrobot.legacy` namespace,
file `pylabrobot/legacy/liquid_handling/liquid_handler.py`. **Before filing, re-check the same lines on upstream `main`**:
the structure may already have changed there (this draft cannot know).

---

## Suggested title

`LiquidHandler 96-head ops (pick_up_tips96 / drop_tips96 / aspirate96 / dispense96) queue tracker changes outside the try: a refused op leaves pending state that a later successful op commits`

## Summary

When a volume or tip tracker refuses a 96-head operation partway through (for example `TooLittleLiquidError` on the 11th well),
the wells and tips already visited keep their **pending** changes and nothing rolls them back. The next 96-head operation that
succeeds calls `commit()` on the same trackers, which makes those leftovers permanent. The tracked state then disagrees with
what the robot physically did.

The 1-channel `aspirate` already handles this correctly, and says so in a comment (`liquid_handler.py:1265-1266`):
"The trackers are queued inside the try, so a tracker that refuses an operation rolls every channel back below, just like a
backend error." The 96-head operations were not given the same treatment.

## Where (at the pin)

| Operation | Tracker queue loop (outside the `try`) | The `try` / rollback |
|---|---|---|
| `pick_up_tips96` | lines 1715-1727 (`head96[i].add_tip(..., commit=False)`, `tip_spot.tracker.remove_tip()`) | `try` at 1730; rollback in the `except` at 1732-1737 |
| `drop_tips96` | lines 1796-1808 (includes a `RuntimeError` at 1803 that can fire mid-loop) | `try` at 1811; rollback at 1813-1820 |
| `aspirate96` | lines 2010-2017 (single container) and 2039-2046 (96 containers): `remove_liquid` / `add_liquid` | `try` at 2059; rollback at 2061-2068 |
| `dispense96` | lines 2158-2165 (tip `remove_liquid`) and the container loops that follow | `try` at 2213; rollback at 2215-2222 |
| **control: 1-channel `aspirate`** | lines 1269-1273, **inside** the `try` | `try` at 1268; commit/rollback at 1284-1289 |

Why a refusal inside those loops leaves state behind: `VolumeTracker.remove_liquid` validates against the **pending** volume and
mutates `pending_volume` (`resources/volume_tracker.py` ~101-109); only `rollback()` (~156-160) restores it, and `commit()`
(~147-151) does `self.volume = self.pending_volume`.

## Minimal reproduction (verified)

Attached file: `261001_plr_96head_pending_residue_repro.py` (PyLabRobot only, no other dependency; chatterbox backend; volume and tip
tracking on; 195 lines including its docstring, in the Praxis repo at `scripts/spikes/`). Scenario:

1. **Control (1-channel).** 8 channels hold tips, wells `A1..G1` hold 100 uL, `H1` holds 0. `aspirate(plate["A1:H1"], [50]*8)` is refused
   (`TooLittleLiquidError`). Afterwards no well and no tip has `pending_volume != volume`.
2. **96-head.** 96 tips held; all 96 wells hold 100 uL except well index 10, which holds 0. `aspirate96(plate, 50)` is refused with
   `TooLittleLiquidError` at well 10, after wells 0..9 and tips 0..9 were already queued.
3. Refill well 10 to 100 uL and call `aspirate96(plate, 10)`. It **succeeds**.

Physical truth after steps 2 and 3: only the 10 uL of the second call moved, so well 0 holds 90 uL and tip 0 holds 10 uL.

Observed (pre-registered prediction, then run; Praxis bathos run `55627ffd-a15b-4e4f-a08d-11feb433f5e0`, outcome `residue_reproduced`):

```
control_refused                 true     (TooLittleLiquidError)
control_rolled_back             true     (no residue on the 1-channel control)
refused_96                      true     (TooLittleLiquidError)
n_residue_wells_after_refusal   10       wells 0..9: pending != committed
n_residue_tips_after_refusal    10       tips  0..9: pending != committed
well0   after refusal           pending 50, committed 100
tip0    after refusal           pending 50, committed 0
second_call_succeeded           true
well0_committed_after_success   40       (physical truth 90)
tip0_committed_after_success    60       (physical truth 10)
```

## Re-run on latest upstream `main` (261014)

The same scenario, re-run with a script that also records the PyLabRobot commit it imported
(`scripts/spikes/261014_plr_96head_residue_repro_latest.py`, sidecar committed before both runs in `9ae28351`).
`pylabrobot.__version__` reads `1.0.0b1` at both commits, so cite the SHAs, not the version.

| PyLabRobot commit | Bathos run | Outcome | Residue wells / tips | well 0 committed (truth) | tip 0 committed (truth) |
|---|---|---|---|---|---|
| `93aa7c402ae3bbd54e008175044b51b6b8d24ee7` (upstream `main`, 2026-10-12), clean clone | `46e29dbc` | `residue_reproduced` | 10 / 10 | 40 (90) | 60 (10) |
| `786ac2c4e4f7afe37885af2d98ff5b0afe274c67` (1.0.0b1 release, 2026-09-28), clean | `eae83bee` | `residue_reproduced` | 10 / 10 | 40 (90) | 60 (10) |

In both, the 1-channel control is refused (`TooLittleLiquidError`) and leaves no residue. `liquid_handler.py` last changed upstream
in `d5dc1f0b7` (2026-10-07); at `93aa7c402` the 96-head queue loops are still outside the `try` (`pick_up_tips96` 1714-1727 vs 1730,
`aspirate96` ~2016/~2045 vs 2059). The original run `55627ffd` recorded only `plr_version`; its commit, `786ac2c4e`, is inferred from
its worktree's editable install, and `eae83bee` re-measures that commit with the commit recorded.

## What was demonstrated and what was only read

- **Run:** `aspirate96` (steps above), and the 1-channel `aspirate` as control.
- **Read, not run:** the same structure in `pick_up_tips96`, `drop_tips96` and `dispense96` (table above). A refusal inside their
  queue loops would behave the same way by the same reasoning, but the reproduction does not exercise them. If you file this,
  either extend the script to those three or word the issue as "the same structure appears in ...".
- **Not tested:** a real Hamilton STAR backend (the tracker code runs before the backend call and is backend-independent, but this
  was not run on hardware), and any PyLabRobot version other than 1.0.0b1.

## Expected

A refused 96-head operation leaves every tracker exactly as it found it, as the 1-channel operations do.

## Suggested fix (for discussion)

Queue the tracker changes **inside** the `try`, as the 1-channel `aspirate` does, so the existing `except` rolls back every tracker
that was touched. For `drop_tips96`, the `RuntimeError` at line 1803 also needs to roll back the channels already processed.
A regression test could be this reproduction without the Praxis wrapper: refuse a 96-head op, then assert
`pending_volume == volume` on every well and tip.

## Why Praxis cares (context, optional to include)

Praxis's notebook error panels name the plate, wells and counts for 1-channel failures. For 96-head failures they currently show only
PyLabRobot's one-line message. Reading tracker state after a 96-head refusal is unreliable while the leftovers exist. Praxis is
building its panels from **committed** state and a separate, optional warning about the leftovers, and does not patch PyLabRobot.

## Provenance (for the user, not for the issue)

- Script `scripts/spikes/261001_plr_96head_pending_residue_repro.py`, sha256 `8a267ebd...5774`; sidecar
  `.../261001_plr_96head_pending_residue_repro.bth.toml` committed before the run (`61b02db9`).
- Run `55627ffd-a15b-4e4f-a08d-11feb433f5e0`: cool-tier record status `completed`, outcome `residue_reproduced`, exit 0, not residual;
  lock sha256 `d42a3ca5...22a3` equals the record's `manifest_sha256`.
- Nothing has been filed, posted or sent to anyone. Filing is the user's decision.
