---
title: 'Notebook display epic: spec premises vs PLR 1.0.0b1 (recon for Revision 10)'
description: 'Exploratory recon, not pre-registered: which 260929 spec claims survive main''s PLR 0.2.2 to 1.0.0b1 pin bump. Two AC cases (E13, E15) no longer raise; pending-residue premise false for aspirate/dispense; C2 vendoring redundant. Orchestrator re-ran the E13/E15 probe independently.'
status: final
task_id: 260929_notebook-display-design
date: '260929'
confidence: ''
sources: ''
---
# Notebook display epic: spec premises vs PLR 1.0.0b1 (recon for Revision 10)


# Notebook display epic: spec premises vs PLR 1.0.0b1

**Status of this evidence.** Exploratory recon by a subagent (Sonnet), run 260929 against the
built PLR wheel copy `1.0.0b1+g786ac2c4` (`_praxis_build_info.PLR_SOURCE_SHA` =
`786ac2c4e4f7afe37885af2d98ff5b0afe274c67`), Python 3.14.6, chatterbox backend. Commit
`786ac2c4e` is in no local git object DB. It is **not** pre-registered: cite no number from it
until the AC-15/16 test files re-run it under a sidecar. Probe scripts: `/tmp/claude-1000/probe/`
(`probe_errors.py`, `probe_callbacks.py`, ...; ephemeral). The orchestrator independently
re-ran `probe_errors.py` against the same wheel and confirmed the two BLOCKER results below
(E9 leaves trough vol 100 / pend 100 and every tip 0/0; the E13 retry and the E15 second
aspirate do not raise). Control: the same probe on 0.2.2 reproduces the spec's verified values.

**Why it matters.** `origin/main` (a176bac7, PR #184 "plr-1.0-bump") moved the pin from 0.2.2
(`dd79c4c89`) to 1.0.0b1 (`786ac2c4e`) after the spec converged. The pin is the same commit
the spec fetched as "PLR main" for Visualizer3D.

## Ranked amendments for Revision 10

**BLOCKER**
1. **AC-15 E13 and E15 no longer raise at 1.0.** `aspirate`/`dispense` now queue tracker changes
   inside the `try` and a tracker refusal rolls every channel back (source comment at
   `legacy/liquid_handling/liquid_handler.py` ~1265, ~1466). Replace both cases; keep E14 (a
   real residue path); optionally add a synthetic residue case that queues an uncommitted
   `tracker.remove_liquid` directly. Fix the AC-17 E13/E15 generic-panel cases and the B5/B6/B8
   mentions.
2. **D8 step 4 "Pending residue" and "Panel drawing: committed, not pending"** (C2-4, C3-1
   premises) are false for aspirate and dispense at 1.0. Residue survives only for
   `pick_up_tips`/`drop_tips` (queue loops still outside the `try`, ~755-761, 901-911; E14
   confirmed). AC-16's "forcing pending != committed well" must force it by direct tracker use.
   Rewrite the D8 "Panel drawing" section, the section 7 rows and OQ-6.
3. **AC-18 / R21 grep** (`grep -rn praxis_repl .../praxis/viz/ .../visualizer/
   .../visualizer-augmentations/` expected exit 1) exits 0 (3 comment hits in
   `web-repl/overlay/assets/python/praxis/viz/transport.py:10,11,26`). Pre-existing (same at
   `e74ad0fa` and on the design branch), not caused by PR #184. AC-31's extended form fails the
   same way. Exempt those comment lines or change the grep.

**MAJOR**
1. D8 "What PLR's message omits": tip-spot messages now name the spot
   (`'tips_300_tipspot_A2 already has a tip.'`, `'tips_300_tipspot_A1 does not have a tip.'`;
   `TipTracker(thing=spot.name)`). The "Tip spot" / `tip_rack.py:52` text is false. Well trackers
   now yield deck names (`assay_well_A1_volume_tracker`; 0.2.2 gave `well_0_0_volume_tracker`),
   so owner rule (d) now parses wells too.
2. **C2 / D11 vendoring.** The pin ships `pylabrobot/visualizer3D`, and the REPL's PLR wheel
   already contains it; `websockets` 17.0.1 is a vendored wheel. The five vendored `.py` files
   under a renamed `plr_visualizer3d`, the ADR addendum and the extra contract entry are
   redundant, and the stated rationale ("never collides with a future pin that ships it") is
   inverted. Import `pylabrobot.visualizer3D` and rebind its `PACKAGE_ROOT`; keep vendoring
   only `static/` (pages must be HTTP-served). This is a design decision (orchestrator ruling
   needed, see the ruling below). OQ-7 is resolved: the pin is that commit.
3. "Zero `.glb` vendored, every model a box" is false at the pin: it ships 63 `.glb` files
   (byonoy, hamilton `resource_model`, ...); the wheel grew 1.26 to 10.2 MB. The `PACKAGE_ROOT`
   rebind to an empty dir is now load-bearing (unrebound root is site-packages).
4. D7: `VolumeTracker.rollback()` now fires callbacks, so a failed op bumps `rev` of the source
   plate and the tip's origin spot though nothing changed (0.2.2: no bump). `register_callback`
   now appends where it replaced. Pick-up fires `did_unassign` x8 on the rack and the deck
   (tips are tree children). Document the spurious "Changed since" after a failed op, or
   filter it.
5. OQ-6 and the section 7 risk rows: reword for tip ops only.
6. Design fixture: use non-deprecated names (`hamilton_tip_carrier_L5`,
   `hamilton_plate_carrier_L5_ac`, `cor_96_wellplate_360uL_Fb`,
   `assign_child_resource(..., track=3)` = same x as `rails=3`); `deck.num_rails` (deprecated,
   32) becomes `num_tracks` (30), ruler labels 1, 5 ... 30 are the same; regenerate
   `fixture.js` (`tips_300` is now `EmbeddedTipRack`, a `TipRack` subclass; tip spots 7.2 mm,
   was 9.0; D5 thresholds hold: 7.2 x 0.771 = 5.55 >= 4; do not dispatch on the type-name
   string; `deck.serialize()` shape changed: `num_tracks`, no `rotation`/`barcode`).
7. `scripts/repl_smoke.py` now derives the expected PLR version from the submodule's
   `version.txt` at import (`NOTEBOOK_EXPECTED`, :1449 via :1426-1441): importing it without an
   initialised submodule raises `VizCheckError`. Spike drivers that import `ServedDir` /
   `chromium_launch_args` cannot run in an uninitialised worktree; the main checkout's 0.2.2
   submodule would expect "0.2.2+g". Affects A1-A3 driver design and local runnability (CI is
   authoritative, D16).
8. `TipTracker` is legacy-only: `pylabrobot.legacy.tip_tracker.TipTracker` (the
   `resources.tip_tracker` path is a DeprecationWarning shim). `LiquidHandler` is at
   `pylabrobot.legacy.liquid_handling`; `VolumeTracker` stays at `pylabrobot.resources.
   volume_tracker`. `web-repl/tests/plr_contract.py` now has a "CONTRACT names no shim" test and
   a probe that escalates warnings to errors, so new B-task imports must use non-shim homes.
9. E2/E3 setups are underspecified: a 400 uL dispense needs `tip.tracker.set_volume(400)`; E3
   needs the source well preset to 500. Both are TRUE once set up so.
10. E7's site moved: the taken-spot NoTip is raised before the queue loop (LH:727 via
    `TipSpot.get_tip`) with only `tip_spots` and `use_channels` bound.

**MINOR (anchors)** New anchors on `origin/main` a176bac7 (legacy path
`pylabrobot/legacy/liquid_handling/liquid_handler.py` = LH unless noted): TLL raise now
`volume_tracker.py:102` in `validate_remove_liquid` (called :108); TLV :117
`validate_add_liquid`; tip `add_liquid` LH:1273; HasTip LH:758; "already has a tip"
`legacy/tip_tracker.py:153`; NoTip :118/:166; container tracker `thing` `container.py:87`;
"Channel N" thing LH:418; `*96` range LH:1674-2229; `return_tips`->`drop_tips` LH:1000,
`discard_tips`->`drop_tips` :1058, `drop_tips96` :1876/:1908, logger :88, `_log_command`
:643-645, bare-call RuntimeErrors LH:1047 and :998; tracking-off defaults
`resources/tip_tracking.py:5` and `volume_tracker.py:14`; D7 callbacks `resource.py:1364`,
assign callbacks :1236-1251, pending bump VT:111-112; `STARLET_SIZE_X = 1005` at
`hamilton_decks.py:811` (`:22` is `STARPLUS_NUM_TRACKS = 76`); `repl_smoke.py`
`run_notebook_check` :1463 -> :1482, `RESULT` print :1769 -> :1788, model-first reads :1572 and
:1624; `praxis_bootstrap.py` ledger :289-398 -> :289-421, `stages.verify_identity()` :415,
`praxis:ready` :421, new `micropip.install("typing-extensions")` ~:384 (D13's insertion point
is still "after step 12"); `build_repl.py` `stage_shell` :1016 and `assert_dist_complete` :1193
(they live in `build_repl.py`, not `stages.py`); `repl.yml` `timeout-minutes` and python lines
are :45 and :66 on the sprint branch (:43/:64 on main); the fixture's `_as_in_kernel` rewrites to
`/lib/python3.12/...` but the kernel is CPython 3.14.

**TRUE and unchanged (no edit needed):** the four error classes (`resources/errors.py:8-22`
byte-identical), TLL/TLV message texts, E1/E2/E3/E4/E6/E8/E10/E11/E12/E14/E16 behaviour, D8
step 2 frame filter and locals (new `wrapper` frames from `events/bus.py:331` and
`legacy/machines/machine.py:58` are excluded by the `co_name` filter), outermost frame supplies
`action`, `*96` short-circuit and E-96 recipe, owner rules (a)-(e) by identity, no liquid
identity (D15, #5658), Visualizer3D anchors (`Viewer3D` server.py:155, `_broadcast` :353,
`_handler` :590, `PACKAGE_ROOT` :98, `_models_on_disk` :104-105, `_register_meshes` :216 with the
global read at :224, `transport.js:63`), Pyodide 314.0.1 and IPython 9.12.0
(`formatters.py:243-250` tuple return verified in the shipped wheel), `repl.yml` untouched by
the 14 commits, `transport.py:210,247`, `build_repl.py:351-353`, `praxis_boot.py:17-19`,
`praxis_bootstrap.py:212-218`. `overlay/assets/visualizer/` is the 2D Konva visualizer and does
not collide with C2's paths; `viz3d` appears nowhere else in the repo.

**Sprint A.** A1-A5 are PLR-independent, as is A7. A6 has line-anchor changes only. The one
PLR-related touch is item MAJOR-7 (import-time submodule dependency in `repl_smoke.py`).

**Easier:** C2 can shrink (pin ships visualizer3D, websockets vendored); volume-error residue
mostly gone; tip-spot messages carry the spot name. PLR now has `pylabrobot.events`
(`evented_operation` on pick-up, drop, aspirate, dispense; opt-in bus), a possible future
alternative to D9's method shadowing, but it does not wrap `return_tips`, `discard_tips` or
`transfer`. **Harder:** `TipTracker` legacy-only and tips are tree children; rollback fires
callbacks; deprecated names throughout; fixture must be regenerated; the 10.2 MB wheel may
matter for boot budgets and unit timeouts.

## Orchestrator note (not recon)
A1a implementer found a spec contradiction independent of PLR: D16 "Shared unit runner" sends
`SIGSTOP` at discovery and then `SIGTERM`, while the fixpoint case (AC-42) expects a `SIGTERM`
handler to fork during the grace window; a stopped process cannot run its handler. Implemented
as `SIGCONT` right after `SIGTERM` and a re-freeze before `SIGKILL`. Revision 10 should adopt
that wording. Also: `Watchdog(budget_s, on_expire)` vs the test cases' `Watchdog(1)` (make
`on_expire` optional), `dist_hash` line format (`"<rel>\t<sha>\n"`, posix-sorted, empty dir =
sha256 of nothing, missing dir raises), `driver_input` reads gitignored `uv.lock` (raises when
absent), `UnitOutcome.killed` undefined (= "kill_tree ran").
