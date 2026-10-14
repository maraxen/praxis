---
title: Notebook display epic, round 12 challenger (Revision 11)
description: Round 12 targeted check of Revision 11 (8aa1aa01). All C11-1..C11-15 CLOSED and re-derived from source. No BLOCKER or MAJOR; 5 MINOR and 2 suggestions carried as sprint notes. Verdict CONVERGED.
status: final
task_id: 260929_notebook-display-design
date: '260929'
verdict: ''
base_sha: ''
---
# Notebook display epic, round 12 challenger (Revision 11)


# Round 12 challenger

Reviewer: praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r12`. Target: spec at `8aa1aa01` (Revision 11).
Verdict: **CONVERGED**. 0 BLOCKER, 0 MAJOR, 5 MINOR, 2 suggestions. Read/Grep/Glob only; every C11
fix was re-derived from the PLR 1.0.0b1 wheel copy, the merged runner and the sprint branch.

## Closure of C11-1..C11-15
All 15 CLOSED, each fix re-derived (not taken from the R11 log):
- **C11-1:** the ERE `(^|[^_])_repr_[a-z]+_` matches `def _repr_html_` (a space satisfies `[^_]`) and not
  `__repr__`; 0 hits over the wheel copy.
- **C11-2:** AC-16 on assay H12 can pass and can fail. `set_volume(100)` sets both volumes (VT:69-72),
  a direct `remove_liquid(40)` changes only pending (VT:106-109) giving 100 / 60; E1's failure rolls back
  only the op's resources (LH:1284-1289), so H12 keeps 100 / 60 at render time; a panel that draws
  pending would draw `sqrt(60/max)` and the "differs from" assert catches it.
- **C11-3:** the four use sites are right (`repl_smoke.py` :1656 `list(...)`, :1666 iteration, :1680
  `list(...)`, :4451 `len(...)`); a function returning the same tuple keeps all four behaviours; a missing
  `version.txt` now raises inside `run_notebook_check`, which `main` catches (:4410-4417, exit 1 as before).
  `test_repl_smoke_import.py` as designed exercises both cases. Every remaining `repl_smoke_units`
  mention is marked dropped or historical.
- **C11-4:** the AC-31 snapshot detects the named patch (`_mark_scene_dirty` exists, `server.py:506`) and
  is robust to PLR's own mutations (`_models_on_disk` stays the same `lru_cache` object; runtime fields
  are instance attributes, `server.py:738-779`; no `global`/`setattr`/`Viewer3D.` writes in `server.py`).
- **C11-5:** E14 stepped through against LH:727-761 and `legacy/tip_tracker.py`; "committed =
  `TipTracker.get_tip()`" is correct; `TipSpot.get_tip()` adds a tip when tracking is off
  (`tip_rack.py:213-216`).
- **C11-6..C11-15:** closed. C11-8 is correct in logic (invocation is C12-1); C11-9 matches
  `unit_runner.py` (`kill_tree` :395-405, `run_unit` :455-462, `ensure_token` :509, `Watchdog` :569-583,
  `write_result` :604-610, `commit` :612-622, `_wait` :350-354, `driver_input` :696-698); C11-11's
  `repl.yml:17-37` still names the single S1 script, so A1 has that work left; C11-12 missed one anchor
  (C12-4); C11-13 is consistent with AC-31's seeding order; C11-14 and C11-15: rules (a), (c), (d) cannot
  collide (a mounted legacy tip is outside the deck tree, held in the head tracker's `_carried`).

## Findings (all MINOR; carried as sprint notes in the spec's Convergence section)
| ID | Finding | Required change |
|---|---|---|
| C12-1 | D7 :424-431 says "exactly this bash"; AC-18, AC-31 and C7 run the R21 gate in [PY] tests or CI. Pasted into a `bash -e {0}` CI step it exits on the pipeline's status 1 (the passing case) before PIPESTATUS is read; via `subprocess.run(cmd, shell=True)` dash rejects `s=(`. Both fail loudly, never falsely pass. | State the invocation: `subprocess.run(["bash","-c",GATE])` with no `-e`/`pipefail`, or the Python form; CI wraps with `set +e`. |
| C12-2 | D11 :1005-1007 promises "only deviation from stock PLR state is the `PACKAGE_ROOT` rebind"; AC-31 snapshots only `vars(Viewer3D)` and `vars(server)`, so e.g. `server.Resource.x = ...` or a patch in `pylabrobot.visualizer3D.scene` passes. | Extend the snapshot to every module dict under `pylabrobot.visualizer3D.*` and the class dicts they expose, or narrow D11's wording. |
| C12-3 | AC-1 "Units" (:1986-1989; governs AC-1/2/3/29) omits `harness` from the hashed inputs; D17 :1540-1543 requires it. | Add `harness` (`scripts/repl_smoke.py`). |
| C12-4 | D16 :1489-1490 "`repl.yml:45` on the sprint A branch" is `:47`. | Fix the anchor. |
| C12-5 | The A1 import test's temporary tree holds only `repl_smoke.py` and `pyproject.toml`; if A7 makes `repl_smoke.py` load `scripts/unit_runner.py` at import, it breaks. Fails loudly. | Copy `unit_runner.py` into the temporary tree, or keep the load lazy. |
| S1 | D16 :1154 says `notebook_expected()` is called "once per run", A1 calls it at four sites. The S1 probe's `_dry_run` comment (:1750) goes stale. | Say "at each use site" or bind once at the top of `run_notebook_check`; update the comment in the amendment commit. |
| S2 | AC-31's positive control should name how to run a scene build without the rebind. | A stock `Viewer3D(deck, open_browser=False)` over the seeded root. |

## Not verifiable by the challenger
The E14 probe outcome and E13 message text as observed at run time (consistent with source); whether
fixture source A1 holds 150 uL and the assay plate's `max_volume` at the pin (the design fixture is not in
the worktree); which Python CI's `uv run` resolves (3.12 vs 3.14) and whether 3.14's lazy `__annotate__`
could change `vars(Viewer3D)` keys (AC-31's stop-and-report rule covers it); the Chromium token open risk
(C10-1); the `origin/main a176bac7` anchors themselves (the challenger read only the sprint branch).
