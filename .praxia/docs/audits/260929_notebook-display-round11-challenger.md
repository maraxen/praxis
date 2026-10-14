---
title: Notebook display epic, round 11 challenger (Revision 10)
description: Round 11 check of Revision 10 (474c9b36). 1 BLOCKER (B2 _repr_ grep can never pass), 3 MAJOR (AC-16 forcing vacuous, repl_smoke lazy-load vs committed S1 probe, GATE X part 2 unenforced), 11 MINOR. Verdict REVISE; fixed as Revision 11.
status: final
task_id: 260929_notebook-display-design
date: '260929'
verdict: ''
base_sha: ''
---
# Notebook display epic, round 11 challenger (Revision 10)


# Round 11 challenger

Reviewer: praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r11`. Target: spec at `474c9b36` (Revision 10).
Verdict: **REVISE**. 1 BLOCKER, 3 MAJOR, 11 MINOR. The challenger had Read/Grep/Glob only and read
the PLR 1.0.0b1 wheel copy, the recon probe outputs, and the sprint worktree `/tmp/praxis-nd-a`.

## Closure of R10-1..R10-13
CLOSED: R10-1 (E13 matches source VT:99-112, 156-163, LH:1265-1292), R10-3, R10-4, R10-5 (applied
coherently; C3 no longer depending on C2 is right), R10-6 (ruling confirmed on the merits), R10-9,
R10-10, R10-11, R10-12, R10-13. OPEN: R10-2 (C11-2), R10-7 (C11-1), R10-8 (C11-3).

## Findings
| ID | Sev | Finding | Required change |
|---|---|---|---|
| C11-1 | BLOCKER | B2 gate `grep -rn '_repr_html_\|_repr_[a-z]*_'`: BRE `[a-z]*` may be empty, so `__repr__` matches. 15 hits at the pin (`resources/resource.py:273`, `plate.py:109`, `tip_rack.py:349,541`, `itemized_resource.py:372`, `legacy/tip_tracker.py:217`, ...). No real IPython `_repr_*_` hook exists at the pin. B2 could never reach 0 hits. | `grep -rnE '(^\|[^_])_repr_[a-z]+_' ... --include='*.py'` expecting exit 1; fix D2's "0.2.2: 0 hits" sentence. **Orchestrator verified 260929:** the spec regex gives 15 hits, the ERE gives 0, and 0 real hooks. |
| C11-2 | MAJOR | AC-16 forces a pending != committed well "before the failing op", but a failed aspirate/dispense rolls back every op resource (LH:1284-1289; VT:160 `pending_volume = self.volume`), erasing that residue. | Put the residue on a well of the owner plate outside the op (assay H12 with op A1:H1); assert pending != committed there when the panel renders; assert the drawn radius comes from committed `tracker.volume`. (Consistent with the orchestrator's own probe: pending reset to committed after the failed op.) |
| C11-3 | MAJOR | D16/D17/A1/section 4 say spike drivers never load `repl_smoke.py` and S1 hashes it, but the driver needs `resolve_chrome_path` (`repl_smoke.py:105`) and the committed A1b-1 probe loads it (`260929_s1_lumino_widget.py:265-267`, `run_driver` :1777); its sidecar `hashed_inputs` (`.bth.toml:109`) omit `repl_smoke.py`. | Pick one. (a) make `NOTEBOOK_EXPECTED` (`repl_smoke.py:1450-1454`) a function called at :1656/:1666/:1680/:4451 (about 6 lines), removing the import-time dependency; (b) move chrome helpers into `repl_smoke_units.py` created in A1. Either way reconcile S1's hashed inputs with D17 by an explicit sidecar amendment before the run. Add `test_s1_spike_driver.py` and `s1_cell_states.ipynb` to section 4. |
| C11-4 | MAJOR | GATE X part 2 ("only deviation from stock PLR state is the `PACKAGE_ROOT` rebind") has no check behind it (AC-31 checks the AST import set and a grep; part 1 inspects `vars(DockedViewer3D)` only). A `server.Viewer3D._mark_scene_dirty = ...` assignment (the S4-C fourth-override case) passes parts 1-3. | AC-31: snapshot `dict(vars(Viewer3D))` and the `pylabrobot.visualizer3D.server` module dict by identity before loading `viewer3d.py`; after load, construct, start, stop, every entry identical except `PACKAGE_ROOT`. |
| C11-5 | MINOR | E14 setup unwritten; "committed tip state" accessor unnamed (`has_tip` includes pending, `tip_tracker.py:105-108`; `TipSpot.get_tip()` creates a tip when tracking is off, `tip_rack.py:209-218`). | Write the verified recipe: `pick_up_tips(tips["D1:D1"], use_channels=[3])`; `pick_up_tips(tips["A2:H2"])` raises HasTip; `head[0..2].has_tip` True and `head[i].get_tip()` raises NoTip; then `pick_up_tips(tips["A3:C3"], use_channels=[0,1,2])` raises `HasTipError("Channel has tip")` with no tracker frame and resolve returns `None`. Committed = `TipTracker.get_tip()` succeeding, never `has_tip`, never `TipSpot.get_tip()`. |
| C11-6 | MINOR | E15 confirmed by source (`validate_add_liquid` uses pending free volume VT:114-119; queue inside the `try` LH:1268-1273; raises `TooLittleVolumeError: Not enough space in container: 200.0uL > 160.0uL.`); tracker loop precedes `backend.aspirate` (LH:1269-1274, 1470-1475). E2's parenthetical (:2053) is false (dispense calls `resource.add_liquid` before `tip.remove_liquid`, LH:1472-1474). | Turn both "verify, else stop" branches into confirmatory asserts; correct E2's note. |
| C11-7 | MINOR | D7 :355-356 "a failed aspirate bumps nothing" is false when the op's containers carried earlier residue; settling not stated for the S3-D debounced path; AC-18's "set_volume bumps" needs a different value; "tip present as drawn" names no accessor. | Qualify; settle inside the S3-D announcer; AC-18 sets A1 to a value other than 150; name `spot.tip is not None`. |
| C11-8 | MINOR | R21 check: pipeline exit is the last grep's; a first-grep exit 2 reads as a pass. | Check `PIPESTATUS[0]` in {0,1}, or run the grep in Python and filter there. |
| C11-9 | MINOR | D16 vs `unit_runner.py`: `ensure_token` :1221 shows `sys.argv` (code uses `sys.orig_argv`, :509, C10-4); `Watchdog` raises without a token (:579-583), keyword-only `token`/`grace_s`/`exit_fn`/`kill_fn` and `write_result` (C10-2) absent from D16; `_wait` ends early when every member is gone (:350-354). | Update D16 and AC-42 (set the token or pass `token=`). |
| C11-10 | MINOR | AC-42's "string check" that `test_repl_smoke_resume.py` never loads `repl_smoke.py` matches its own literal; the C8-5 "exits 2"/`--aggregate-only` cases are CLI behaviour. | AST check plus a runtime check (no `sys.modules` entry with `__file__` = `scripts/repl_smoke.py`); test pure functions. |
| C11-11 | MINOR | `repl.yml` `paths:` filters lack `scripts/repl_smoke_units.py`, `scripts/spikes/**`, `scripts/negatives/**`. | Add in A1/A7. |
| C11-12 | MINOR | Anchor slips: `STARLET_SIZE_X` at `hamilton_decks.py:811` is the `_OLD_CONSTANTS` dict; live value `star_decks.py:225`, `STARLetDeck` :209. `repl.yml` `timeout-minutes` :47, python :68 on the sprint branch; `NOTEBOOK_EXPECTED` :1450 there; `praxis:interaction_response` at `praxis_bootstrap.py:266`. | Re-anchor. |
| C11-13 | MINOR | The `PACKAGE_ROOT` rebind trigger is ambiguous ("module code before the first construction" vs AC-31 seeding a root before construction). | State the trigger (guarded first-construction helper, or import; if import, the test seeds before loading `viewer3d.py`). |
| C11-14 | MINOR | `TipSpot.tracker`/`get_tip`/`has_tip` are docstring-deprecated ("TODO: Remove in v1", `tip_rack.py:200-226`); rule (a) calls `.tracker` on every spot, which creates trackers (`tip_tracker.py:233-258`). | Prefer `pylabrobot.legacy.tip_tracker.tip_spot_tracker` and `spot.tip`; add a section 7 row for v1 removal. |
| C11-15 | MINOR | Rule (d): a tip's VolumeTracker `thing` is the tip name (`tip.py:52`, e.g. `tips_300_tipspot_A1#0`); a lookup by name resolves to a `Tip` (a `HeadTool`), neither container nor spot. | A `Tip` match means no owner, or map to its spot via `tip_origin` (`tip_rack.py:286`). |

## Rulings checked
- D7 drawn-state digest filter: **confirmed** (rollback settles lazily so intermediate states are invisible; pending-only change bumps, agreeing with AC-18 and Revision 2 B-8; a pick-up gives one bump per settle, not eight; AC-23 `unchanged_not_marked` holds).
- R21 pipeline: exits 1 on the 3 real hits, not vacuous (the `test -d` guard). Error masking is C11-8.
- `repl_smoke_units.py`: **not the smallest fix** (C11-3, C11-10).
- C2/D11 binding ruling: applied coherently; C3 -> C2 edge correctly dropped; GATE X part 2 unenforced (C11-4); rebind trigger ambiguous (C11-13).
- `kill_tree` steps 4-5 match the code (`unit_runner.py:356-375`); remaining drift is C11-9.
- Round-10 notes C10-1..C10-4: intact and implemented.

## Not verifiable by the challenger (no execution)
The (a)-(c) run results (consistent with source), the E-96 recipe at the pin, the `did_unassign` x8 count,
the 63 `.glb` count and wheel size, Chromium keeping the token in `/proc/<pid>/environ` (open until
C10-1 runs in CI), `websockets` in CI's root env (`pyproject.toml:57-61` optional extra; C3 has a
stop-and-report rule), the Pyodide 3.14 site-packages path, and the Revision 10 anchors on
origin/main a176bac7 itself (the challenger had only the sprint branch, where they are shifted).

## Orchestrator dispositions (260929)
- C11-1: verified by running the grep against the wheel copy (15 / 0 / 0); adopt.
- C11-2: adopt (consistent with the orchestrator's E9 probe, where pending reset to committed).
- **C11-3: ruling (a).** Make `NOTEBOOK_EXPECTED` lazy in `repl_smoke.py` (about 6 lines, with a
  regression test that importing the module succeeds with no submodule). Drop `repl_smoke_units.py`
  and every task/AC mention of it; everything may load `repl_smoke.py` again. The change lands in
  A1 (S1 needs it). The committed S1 sidecar's `hashed_inputs` gains `repl_smoke.py` by an explicit
  amendment committed before the first run (no run has happened; the amendment is recorded in the
  spec and in the S1 research note). Add `web-repl/tests/test_s1_spike_driver.py` and
  `s1_cell_states.ipynb` to section 4.
- C11-4, C11-5..C11-15: adopt as stated. C11-13: rebind in a guarded, idempotent first-construction
  helper (tests seed the temporary root after import, before the first construction).
- Fixed as Revision 11 through the spec writer; a targeted round 12 follows.
