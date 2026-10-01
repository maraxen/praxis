---
title: 'Notebook display: structured error context for 96-head ops (backlog #5659)'
description: Revision 2 of the D8 step 2 follow-up. Replace the *96 short-circuit with a head96-aware error context (locals mapping with a container-mode guard, committed offending set, the 96 panel rows, committed rack drawing, ledger after-state on committed volumes) as the CORE, and a separable RESIDUE layer (detect and name the pending changes PLR 1.0.0b1 leaves after a refused 96 op). Drops the unenforceable 32 KiB claim. Design only, no product code.
status: accepted-r2
revision: 2
task_id: 260929_notebook-display-design
date: '261001'
backlog_id: 5659
---
# Increment: structured error context for 96-head ops (backlog #5659, umbrella #5648)

> **Status: DRAFT r2 for the user's decision** (decision sheet: `5659_decisions.md`, next to this file).
> It amends `260929_notebook-display-epic.md` by reference and does not edit it; section 10 lists every
> touched place. Base: `feat/notebook-display-sprint-c-stacked @ 98a233ed` (PR #198). PLR pin: 1.0.0b1,
> `786ac2c4e`, read at `/tmp/praxis-nd-b/external/pylabrobot`. Every PLR path below is under
> `external/pylabrobot/pylabrobot/`; `LH` = `legacy/liquid_handling/liquid_handler.py`; tip trackers are
> `legacy/tip_tracker.py` (not the 32-line `resources/tip_tracker.py` shim).
>
> **Provenance of numbers.** Numbers tagged *(v1 obs.)* are the round-1 drafting agent's spike output: run
> on 261001 in a scratch dir, never committed, never registered. They are **unregistered observations**.
> Numbers tagged *(S<n>)* come from this revision's pre-registered spikes (`spike-run` records under
> `/tmp/praxis-nd-b/.praxia/spikes/261001_nd-next-5659-96head-errors/`). Neither kind is a finding; the gates
> in section 6 re-derive every number a decision depends on. Cite the test, not this text. S1-S3 crashed
> on an import cycle (`pylabrobot.legacy.tip_tracker` imported before `pylabrobot.legacy.liquid_handling`)
> before reaching their question; they answer nothing and are not cited. S7-S9 re-ran them under new ids
> with only the import order changed. All cited spikes (S4-S9) matched their pre-registered
> `expect_if_true`.

## Revision 2: what changed and why

Round 1: challenger REVISE (18 findings), defender 10 conceded / 7 partial / 1 rebutted. Where they differ,
this revision follows the evidence the defender checked against the source, and says so.

| # | Sev. | Resolution | One-line reason | Now handled in |
|---|---|---|---|---|
| C1 | BLOCKER | accepted | 19,746 B figure + 16,384 B traceback > 32,768 B before any text; nothing enforces 32 KiB. The claim is dropped; 64 KiB is the only enforced bound; the worst case is now a formula (one measured instance: 38,616 B, S5) | N5659-7, AC-96-7, Q3 |
| C2 | MAJOR | accepted (defender: partial) | D4 has no "unfaulted" qualifier; the miss is now a D4:198 target revision with per-figure numbers, for the user | N5659-7, AC-96-7(b), Q3 |
| C3 | MAJOR | accepted | residue now includes mounted tips' VolumeTrackers; the sentence names the hazard; the drawing clause only where there is a drawing; epic :636 listed | N5659-11, AC-96-R1/R2, s.10 |
| C4 | MAJOR | accepted | a one-item Plate is single-container mode (LH:1993); rows dispatch on the recorded container mode, not `_in_plate` | N5659-2, N5659-6, AC-96-2, AC-96-6 |
| C5 | MAJOR | accepted | the r1 pending mutant could not fail on F3/H; replaced by a scenario that tells the readings apart (needs a second rack) | AC-96-4(a) |
| C6 | MAJOR | accepted | dispense96's tip loop precedes its count/plate/fit checks; container-mode guard returns `None` | N5659-2, AC-96-2 |
| C7 | MAJOR | partially | committed demand kept, now argued (physical state; PLR's set is a subset) and gated; it is a user decision. Correction to the defender: its scenario ("wells 0-4 short") raises nothing in PLR, so r2 adds a short well PLR does reach | N5659-4, AC-96-4(b), Q5 |
| C8 | MAJOR | partially | s.4's "byte-identical" was wrong; the 1-channel rack change is stated, tested positively, `vals` + sentence pinned. Sub-point rejected (defender): a committed reader in `errors.py` has precedent (`errors._drawn_volume`, errors.py:181-184) | N5659-8, AC-96-11, Q6 |
| C9 | MAJOR | partially | epic :637-639 listed; "identical for successful ops" corrected; the ledger stays committed (core), labware outputs stay pending; user question | N5659-10, AC-96-8, Q7 |
| C10 | MAJOR | accepted | innermost `*96` under an outer non-96 op frame gives `None`; `stamp` reads as aspirate96/dispense96 and its source-TLV is unreachable | N5659-1, AC-96-1 |
| C11 | MAJOR | partially | facts right, premise wrong (defender): `create_browser_backend` has no caller (S6); users build their own handler from playground names. A17 is replaced by a coverage statement | s.1.8, A17-A23, Q2 |
| C12 | MINOR | accepted | NoTip via `TipSpot.get_tip` after drop residue added to `NONE_CASES` | A9, AC-96-5 |
| C13 | MINOR | partially | no contradiction (today's layering, errors.py:257-258); N and the one-well-Plate TLV join `GENERIC_CASES`, not `NONE_CASES` | AC-96-6 |
| C14 | MINOR | rejected | rule (d)'s "Channel N" parse already applies to head96 trackers and the panel stays generic without `ctx.op` (errors.py:311); `head96` stays `False` on rule (d), documented | N5659-3 |
| C15 | MINOR | accepted | every epic/code/test-docstring place listed; five test files, not four | s.10, AC-96-12 |
| C16 | MINOR | accepted | base 98a233ed; legacy tip tracker; ":1246" was the ladder test (:1241-1254), the traceback-cap control is :1214; the 96 canary asserts tracker < `try` < backend and no rollback before `try` | header, AC-96-9 |
| C17 | MINOR | partially | "have" for several spots; "on every channel" only when no well is shared; strings provisional until Q9; `compress_wells` is bounded (at most 96 ids) | N5659-6 |
| C18 | MINOR | accepted | new `ErrorContext` fields get defaults and go at the end | N5659-2 |

Other changes: (1) the design is split into a **core** (build now) and a **residue layer** (separable,
can be deferred); (2) the residue reader lives in a new module `residue.py`, because `context.py`'s AST scan
forbids `has_tip` (test_display_context.py:1541-1546) and must not be loosened; (3) the physical-state
argument now states where it stops: once a later success commits residue (B2), committed state is no
longer physical either; (4) the vacuous r1 negatives (`E96-runtime`, `E96-tooSmall` at resolver level) are
kept as scenario premises but no longer counted as controls; (5) the assumptions table is now the
Assumption Ledger, with nine spike records (S1-S3 crashed on an import cycle and are not cited; S4-S9 are).

## 1. Problem and current behaviour

### 1.1 What the 96 ops are (at the pin)

| Op | Lines | Binds | Tracker raise sites | Queue outside the `try`? |
|---|---|---|---|---|
| `pick_up_tips96` | 1674-1743 | `tip_rack`; loop `tips`, `i`, `tip_spot` | `head96[i].add_tip` :1722 (`HasTipError`); `tip_spot.get_tip()` :1722 (`NoTipError` via `TipSpot.get_tip`, tip_rack.py:209-218) | **yes** (:1715-1727; `try` :1730) |
| `drop_tips96` | 1745-1827 | `resource`; loop `i`, `tip`, `tip_spot` | `head96[i].get_tip()` :1800 (`NoTipError`); spot `add_tip` :1807 (`HasTipError`); `RuntimeError` :1803 | **yes** (:1796-1808; `try` :1811) |
| `return_tips96` / `discard_tips96` | 1850-1881 / 1883-1912 | call `drop_tips96` (:1876, :1908) | `RuntimeError` :1875 | n/a |
| `aspirate96` | 1925-2075 | `resource`, scalar `volume` (:1985), `containers` (:1990-2002), `tips` (:1981) | well/container `remove_liquid` :2016 / :2045; tip `add_liquid` :2017 / :2046 | **yes** (:2010-2046; `try` :2059) |
| `dispense96` | 2077-2229 | same (:2131, :2135, :2140-2152) | tip `remove_liquid` :2163 (first, every tip); container `add_liquid` :2173; well :2200 | **yes** (:2158-2200; `try` :2213) |

`aspirate96` runs its fit, same-plate and 96-count checks **before** its loops (:2007, :2031-2037).
`dispense96` runs its tip loop **before** them (:2158-2165 vs :2169, :2187-2193), so a tip error can arrive
with 48 or 384 containers, wells of several plates, or a container too small for the head (A26, C6).
1-channel `aspirate`/`dispense` queue inside the `try` and roll back; the 96 ops do not (A10).

### 1.2 What the 96 ops can raise

| Exception | Raised by | Display class? |
|---|---|---|
| `TooLittleLiquidError` | `aspirate96` container/well (:2016, :2045); `dispense96` tip (:2163) | yes |
| `TooLittleVolumeError` | `aspirate96` tip (:2017, :2046); `dispense96` container (:2173), well (:2200) | yes |
| `HasTipError` | `pick_up_tips96` head channel (:1722, thing `"Channel N"`, LH:421); `drop_tips96` rack spot (:1807) | yes |
| `NoTipError` | **only through pending residue**: head `get_tip()` at :1800 / :1981 / :2131, and `TipSpot.get_tip()` at :1722 after drop residue on the same rack (C12) | yes |
| `RuntimeError`, `ValueError`, `TypeError`, `KeyError` | non-zero tip volume :1803; none picked up :1875; counts/fit/lid; `KeyError` at `head96[i]` on a backend with no 96 head (A19) | no (plain traceback) |

Not errors: 96 ops with no tips mounted (`tips` all `None`); a partial rack (`pick_up_tips96` picks what is
there); tracking off (A15).

### 1.3 How D8 resolves a 1-channel op today

`context.resolve` (context.py:443-514): op frames are `LiquidHandler` frames whose `co_name` is in
`glossary.ACTIONS`; **any `*96` op frame returns `None`** (:462-463); innermost op frame supplies
`resources`/`tip_spots`, `use_channels`, `vols` (:491-495); owner by identity (:258-338); committed
offending set (`_volume_offenders` :344-390, `_tip_offenders` :398-430); owner outside the set gives
`None` (:504-506). `errors._panel_for` (:308-316) picks a row; `None` gives the generic panel.

### 1.4 What a 96 op shows now

Today's E-96 scenario (test_display_context.py:642-647): `pick_up_tips96(tips)` then `aspirate96(assay,
50)` raises `TooLittleLiquidError: Not enough liquid in container: 50.0uL > 0uL.`; `resolve` returns
`None` (:462); the generic panel names no plate, no well and no count.

### 1.5 Offending wells for a 96 head

PLR raises at the first failing position and validates against pending state. The set must be recomputed
from committed state, as D8 step 4 does, with the head's committed mounted set as the channel list
*(v1 obs.: empty plate 96; row D short 12; partial head 92; three-room-short 3; single container
2,880 vs 2,000)*.

### 1.6 Residue (the finding that shapes the design)

All four 96 ops queue tracker changes outside the `try`, and `rollback()` runs only when the backend
raises (A10). A tracker refusal therefore leaves pending state behind (A38), and the next success commits
it (`commit()` sets `volume = pending_volume`, volume_tracker.py:151; A11). *(v1 obs. B2: A1 at 20 µL where
70 is physical; tip 0 at 60 where 10 is physical.)* The residue covers wells, containers, **the mounted
tips' own volume trackers** (aspirate96 :2017/:2046, dispense96 :2163; C3), head channels and rack spots.
The error panel's rack drawing, grid `vals` and rack sentence read the resource tree, which is pending
(A12); the same hole exists for 1-channel pick-up/drop residue (E14), including a rack drawn for a
1-channel spot owner (A31).

**Where the physical-state argument stops.** Every 96 refusal precedes the backend (A10), so at the moment
of the refusal committed state is what the robot physically did. That stays true only until a later
success commits the residue (B2): from then on neither PLR's committed nor its pending state is physical,
and nothing in Praxis can recover the truth. This is the hazard the residue sentence names.

### 1.7 Ledger side

The ledger records a failed 96 row like any other and `step_for` finds it. Its after-state reads pending
(ledger.py:589, :600, :603, :691; A13), so after a refused `dispense96` it outlines wells nothing was
dispensed into *(v1 obs.: 10 wells)*. Ledger counts for a partial head (96 channels, `96 x volume`) are out
of scope (follow-up; `test_display_ledger.py:1260-1261` pin `[96] * 4` and 4,800).

### 1.8 Who sees these panels (replaces r1 A17)

A 96 panel appears only when **all** hold: (1) tracking is on: PLR's tip and volume tracking are off by
default (resources/tip_tracking.py:5, volume_tracker.py:14; epic :643), and with them off no 96 tracker
error fires (A15); (2) `await lh.setup()` has run (`head96` is `{}` until then, LH:384, :420-424); (3) the
backend reports a 96 head: `LiquidHandlerChatterboxBackend` (chatterbox.py:47, the documented simulation
backend, make_fixture.py:53), `SerializingBackend` (serializing_backend.py:34), `STARBackend` when the
machine reports a CoRe 96 head (STAR_backend.py:816-818). **Not covered:** `WebBridgeBackend` (never sets
a 96 head, backend.py:49, web_bridge.py:1377) and the OT-2, Vantage and EVO backends (base default); there
`pick_up_tips96` raises `KeyError` at `head96[i]` (:1722), not a display class. How REPL users get a
handler: `praxis_boot._inject_playground_names` (praxis_boot.py:144-165) calls
`web_bridge.bootstrap_playground(shell.user_ns)`, which injects `LiquidHandler` and every `*Backend` class
of `pylabrobot.legacy.liquid_handling.backends` (web_bridge.py:1487, :1501-1503); `create_browser_backend`
has no caller in the tracked tree (A20, S6). Only a running kernel can confirm the injection at runtime
(A23, deferred).

## Assumption Ledger (section 2)

| ID | Assumption | If false | Status | Evidence |
|----|------------|----------|--------|----------|
| A1 | The display tests run against the PLR 1.0.0b1 submodule pin and fail loudly on another PLR | every AC would test a different PLR | VERIFIED | read: web-repl/tests/test_display_context.py:126-134 |
| A2 | aspirate96 from the empty assay plate after pick_up_tips96 raises TooLittleLiquidError on the fixture, and a scenario-premise test pins the class | E96-empty would not exist | VERIFIED | read: web-repl/tests/test_display_context.py:642-647; read: web-repl/tests/test_display_context.py:744-751 |
| A3 | In aspirate96 and dispense96 the locals containers and volume are bound before any tracker call | Option A mapping reads absent locals; fall back to Option B | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1985-2002; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2135-2152 |
| A4 | The tips local is built from has_tip, which includes pending state, so it is not the committed mounted set | the mounted set could be read from tips | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1981; read: external/pylabrobot/pylabrobot/legacy/tip_tracker.py:105-119 |
| A5 | Head channel c pairs with item c of the op's labware: zip of containers and tips, enumerate of the rack, get_item(i) on drop | channel pairing and position naming are wrong | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2039; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1716; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1805 |
| A6 | PLR skips a channel whose tips entry is None, so that channel's well is not demanded | rule O2 would demand tipless channels | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2040-2041; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2159-2160 |
| A7 | With no pending residue on the op's trackers pending equals committed, so PLR's first failing target lies inside the committed recompute over the committed-mounted channels | the owner-in-set test would reject real failures | VERIFIED | read: external/pylabrobot/pylabrobot/resources/volume_tracker.py:99-104; read: external/pylabrobot/pylabrobot/resources/volume_tracker.py:69-72; read: external/pylabrobot/pylabrobot/legacy/tip_tracker.py:63-68 |
| A8 | HasTip on pick_up_tips96 comes from head96[i].add_tip when the channel holds a pending tip, and HasTip on drop_tips96 into a TipRack from the spot tracker's add_tip | the HasTip rules in N5659-4 are wrong | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1721-1722; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1804-1807; read: external/pylabrobot/pylabrobot/legacy/tip_tracker.py:152-153 |
| A9 | NoTipError in a 96 op arises only where a pending has_tip check passes and a committed get_tip fails: head96 get_tip in drop_tips96 and in both tips comprehensions, and TipSpot.get_tip in pick_up_tips96 | NoTip-always-None would hide a committed-explainable fault | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1798-1800; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1981; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2131; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1721-1722; read: external/pylabrobot/pylabrobot/resources/tip_rack.py:209-218 |
| A10 | In all four 96 ops the tracker queue loop runs before the try, the backend call is inside it, and rollback runs only in the except of the backend call | the "Nothing was aspirated" sentence and the residue premise both fail | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2010-2068; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2158-2222; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1715-1737; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1796-1820 |
| A11 | A later successful 96 op commits residue left by an earlier refusal, because commit sets volume to pending_volume | the residue hazard would be cosmetic | VERIFIED | read: external/pylabrobot/pylabrobot/resources/volume_tracker.py:147-151; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2069-2075 |
| A12 | The error panel's tip-rack drawing, its grid vals and the rack sentence read the resource tree (spot.tip), which includes pending state | the committed tip hook is unneeded | VERIFIED | read: web-repl/overlay/assets/python/praxis/display/labware.py:630-631; read: web-repl/overlay/assets/python/praxis/display/labware.py:657; read: web-repl/overlay/assets/python/praxis/display/labware.py:278-280; read: external/pylabrobot/pylabrobot/legacy/tip_tracker.py:55-61 |
| A13 | The ledger after-state reads pending volume at touch time, at compute time and in the volume fallback | N5659-10 is unneeded | VERIFIED | read: web-repl/overlay/assets/python/praxis/display/ledger.py:589; read: web-repl/overlay/assets/python/praxis/display/ledger.py:600; read: web-repl/overlay/assets/python/praxis/display/ledger.py:603; read: web-repl/overlay/assets/python/praxis/display/ledger.py:691 |
| A14 | On the fixture a 96-fault plate figure and a 96-fault rack figure are each above their D4 targets of 16,384 and 12,288 bytes and each at most 20,480 bytes | Q3 changes: no miss to approve, or the proposed 20 KiB target is too low | VERIFIED | spike: S5 |
| A15 | With tip tracking off no 96 tip error fires, and with volume tracking off no 96 volume error fires | the coverage statement changes | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1717-1718; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1806; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2014; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2162-2165 |
| A16 | The 96 tracker code runs before the backend call, so any backend with a 96 head raises the same errors at the same sites | the STAR coverage claim is wrong | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2059-2060; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2213-2214 |
| A17 | (r1, retired) The Pyodide kernel's PLR is the pin and lh.head96 exists on a chatterbox-like backend | none | UNVERIFIED | deferred: retired in r2 and split into A19-A23; its runtime half needs a live Pyodide kernel and is A23 |
| A18 | labware.render_figure marks all fault ids with one ring path and one cross path, no new class and no circle element | the D5 and size ACs change | VERIFIED | read: web-repl/overlay/assets/python/praxis/display/labware.py:478-497 |
| A19 | WebBridgeBackend reports no 96 head, so lh.head96 is empty after setup and pick_up_tips96 raises KeyError at head96[i] | the coverage statement changes | VERIFIED | read: web-repl/overlay/assets/python/web_bridge.py:1377; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/backends/backend.py:49; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:420-424; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1721-1722 |
| A20 | create_browser_backend has no caller in the tracked tree; its only tracked occurrence is its definition | WebBridgeBackend users would be a real audience that gets KeyError tracebacks | VERIFIED | spike: S6 |
| A21 | The REPL bootstrap injects LiquidHandler and every Backend-suffixed class of pylabrobot.legacy.liquid_handling.backends, the chatterbox included, into the user namespace | the coverage statement changes | VERIFIED | read: web-repl/files/praxis_boot.py:144-165; read: web-repl/overlay/assets/python/web_bridge.py:1487; read: web-repl/overlay/assets/python/web_bridge.py:1501-1503; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/backends/__init__.py:2 |
| A22 | LiquidHandlerChatterboxBackend and SerializingBackend report a 96 head, STARBackend reports what the machine reports, and lh.head96 is empty until setup | the coverage statement changes | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/backends/chatterbox.py:47; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/backends/serializing_backend.py:34; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/backends/hamilton/STAR_backend.py:816-818; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:384 |
| A23 | In the running Pyodide kernel bootstrap_playground really leaves those names in user_ns | none | UNVERIFIED | deferred: needs the built site in Chromium (repl_smoke); if false users import the backend themselves, and no design element changes |
| A24 | A one-item Plate becomes single-container mode with its Well, whose parent is the Plate, so errors._in_plate is true for that owner | the C4 fix is unnecessary | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1993; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2143; read: web-repl/overlay/assets/python/praxis/display/errors.py:194-196; read: web-repl/overlay/assets/python/praxis/display/errors.py:236 |
| A25 | A PLR one-well troughplate exists whose well passes the 96-head fit check, and aspirate96 on it runs in single-container mode with a Well whose parent is the Plate | the E96-onewell-plate fixture must build a custom Plate | VERIFIED | spike: S4 |
| A26 | dispense96's tip loop runs before its fit, same-plate and 96-count checks, so a tip error can arrive with len(containers) not in (1, 96), wells of several plates, or a container too small for the head | the container-mode guard is unneeded | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2158-2170; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2185-2193 |
| A27 | aspirate96 runs its fit, same-plate and 96-count checks before its tracker loops | none | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2005-2008; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2030-2037 |
| A28 | The channels PLR iterates without raising are a subset of the committed-mounted set, because a pending-present channel with no committed tip raises NoTipError in the tips comprehension | committed demand could understate PLR's demand | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1981; read: external/pylabrobot/pylabrobot/legacy/tip_tracker.py:110-119 |
| A29 | After H's residue, pick_up_tips96 from a second full 96 rack raises HasTipError at channel 5; the committed reading gives 96 offending channels and a has_tip (pending) reading gives 91 | AC-96-4(a) needs another discriminating scenario | VERIFIED | spike: S7 |
| A30 | After H's residue, aspirate96 of 50 uL from a plate whose wells 0-4 and 10 hold 10 uL and the rest 200 raises TooLittleLiquidError from well 10 (C2); committed demand gives 6 offending wells and the PLR-iterated channel set gives 1 | AC-96-4(b) and Q5 need another scenario | VERIFIED | spike: S8 |
| A31 | After E14, a 1-channel drop_tips of channel 3 onto tips_300 A1 raises HasTipError, today's resolver gives a spot-owner context, and today's panel draws 92 tips present while 95 spots hold a committed tip | the 1-channel rack change has no positive test | VERIFIED | spike: S9 |
| A32 | ErrorContext declares no field defaults and a test constructs it by keyword without any new field | C18 is moot | VERIFIED | read: web-repl/overlay/assets/python/praxis/display/context.py:105-117; read: web-repl/tests/test_display_context.py:1415-1419 |
| A33 | stamp is not a glossary action and its dispense96 goes into source, which it has just aspirated from, so a stamp TooLittleVolumeError on source is unreachable and stamp errors come from aspirate96 | a stamp row is needed | VERIFIED | read: web-repl/overlay/assets/python/praxis/display/glossary.py:59-67; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2265-2266 |
| A34 | PLR's own nested 96 calls are return_tips96 and discard_tips96 calling drop_tips96, and stamp calling aspirate96 and dispense96; any other mixed stack comes from user code | the None rule for mixed stacks would hide PLR's own calls | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1876; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1908; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2265-2266 |
| A35 | context.py's AST scan forbids has_tip anywhere and .tracker outside two helpers, so a pending reader cannot live in context.py without changing that scan | the residue reader could live in context.py | VERIFIED | read: web-repl/tests/test_display_context.py:1541-1546 |
| A36 | An aspirate96 error panel with the 96-fault plate figure and a traceback of 300 distinct frames is larger than 32,768 bytes and at most 65,536 bytes | the 32 KiB drop is unnecessary | VERIFIED | spike: S5 |
| A37 | The test fixture holds one tip rack, so the second-rack scenario must add one on tip carrier position 1 | AC-96-4(a) could use the fixture as is | VERIFIED | read: web-repl/design/notebook-display/make_fixture.py:56-58 |
| A38 | A pick_up_tips96 refusal leaves pending tips on head channels and pending removals on rack spots, and a drop_tips96 refusal leaves the reverse | the residue layer would cover volumes only | VERIFIED | read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1721-1727; read: external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:1804-1808 |
| A39 | Other labware outputs draw get_used_volume, which includes pending | the ledger/display disagreement (Q7) does not exist | VERIFIED | read: web-repl/overlay/assets/python/praxis/display/labware.py:218-219 |

**Recipes** (each after `world()` = `test_display_context._world()`, i.e. `make_fixture.assemble()`, and
`await lh.pick_up_tips96(tips)` unless noted). **B** assay wells 80 µL except row D at 10, `aspirate96(assay,
50)`. **C3** wells' `max_volume` 5000, `set_volume(1000)`, `aspirate96(source, 200)` twice. **D**
`aspirate96(source, 30)` then `dispense96(assay, 50)`; **D2** `aspirate96(source, 30)`, then the tips on channels
7 and 9 set to 20 µL (`tip.tracker.set_volume(20)`), then `dispense96(assay, 25)` (fails at tip 7 after tips
0-6 are queued: 7 tips of residue). **E** assay
room 30 µL at indices 10, 11, 40, 200 elsewhere, tips hold 100, `dispense96(assay, 100)`. **F3** `head96[3]`,
`head96[50]` hold committed tips, `pick_up_tips96(tips)`. **G2** committed tips removed from spots 0, 1, 2, 50
first, empty plate. **H** committed tips put back in spots 5 and 77, `drop_tips96(tips)`. **J2** bare
`Container` 120x80x40, max 20,000, holding 2,000, `aspirate96(c, 30)`. **L** F3 then `drop_tips96(tips)` /
`aspirate96(assay, 10)`. **N** `Container` (max 3,000) holding 1,000, tips hold 30, `dispense96(c, 30)`. **R2**
(new, A29) H, then a second rack `tips_b` on `tip_carrier[1]`, `pick_up_tips96(tips_b)`. **K** (new, A30) H,
assay wells 0-4 and 10 at 10 µL, the rest 200, `aspirate96(assay, 50)`. **Q** (new, C12) H, then
`pick_up_tips96(tips)`. **P1** (new, A31) E14 (`pick_up_tips(tips["D1:D1"], use_channels=[3])`,
`pick_up_tips(tips["A2:H2"])`), then `drop_tips(tips["A1:A1"], use_channels=[3])`.

## 3. Options

### 3.1 Locals mapping

- **A. Normalise to the 1-channel shape (recommended).** Read `containers`, `volume` and the tip ops'
  `tip_rack`/`resource`; take the channel list from committed `lh.head96`; fill `resources`, `channels`,
  `volumes`; reuse `_volume_offenders`/`_tip_offenders` with the head dict passed in. Depends on the
  PLR-internal local `containers` (A3), pin-guarded.
- **B. Arguments only** (re-derive `containers` from `resource`). Re-implements :1990-2002. Fallback only.
- **C. Loop locals only.** Understates; rejected.

### 3.2 Offending rule

- **O1 first failure only.** Rejected (understates).
- **O2 committed recompute over the committed-mounted channels (recommended).** See N5659-4.
- **O2' PLR's demand** (the channels PLR iterated: pending `has_tip` and committed `get_tip`). Equals O2 when
  no head residue exists; differs after head residue (A30). Offered as Q5's alternative.
- **O3 whole head.** Rejected (overstates).

### 3.3 The drawing when many positions fault

- **F1 per-position ring + cross, as today (recommended).** Faulted figures exceed D4's targets (A14):
  a D4:198 target revision for the user (N5659-7).
- **F2 compaction when every position faults.** **Not adopted:** a fault costs ~110 B *(v1 obs.:
  (19,746 - 9,164) / 96)*, so 95 faults cost almost as much as 96; F2 bounds only the all-faulted case
  unless it also marks the complement, which is a new mark concept (~60-80 lines in `labware.py`, unmeasured).
- **F2' a second ladder threshold at 32 KiB.** **Not adopted:** `budget.enforce` hard-codes the 64 KiB cap,
  and degrading a drawing below a cap D4 never set has no D4 reason (D4 justifies the cap by notebook JSON
  size, epic :188-190).
- **F3 block level above N faults.** Use the existing ladder level 1 (blocks, *(v1 obs.)* 5,540 B) when
  more than N positions fault. ~10 lines; loses per-position marks for large sets. Offered in Q3.

### 3.4 Residue

- **R1 read-only notice (recommended, separable).** `residue.py` detects pending != committed on the op's
  trackers; the 96 panel adds one hazard sentence. No state change.
- **R2 repair** (`rollback()` from the display hook). Rejected: D8 "changes no state".
- **R3 nothing.** The core still ships; B2 drift stays silent. This is "defer the residue layer" in Q4.

## 4. Recommendation

Build the **core** now: dispatch (N5659-1), mapping with a container-mode guard (N5659-2), owners (N5659-3),
committed offending set (N5659-4), rows (N5659-5, -6), size as a target revision (N5659-7), committed rack
drawing in error panels (N5659-8), glossary (N5659-9), ledger after-state on committed volumes (N5659-10),
premise canaries (N5659-12). Build the **residue layer** (N5659-11) as a separate task the user may defer.
The core changes one shipped 1-channel behaviour: an error panel's rack drawing, grid `vals` and rack
sentence show committed tips, which differs from today only when a rack carries tip residue (P1, A31).
Every other 1-channel output is unchanged (AC-96-12). Everything committed state cannot explain still
gives `None` ("never guesses" holds).

## 5. Proposed decisions

**N5659-1. Dispatch on the innermost op frame.** Let `ops` be the op frames (unchanged definition). (i) If
every frame in `ops` is a `*96` op, resolve on the 96 path with `head = lh.head96`. (ii) If any is `*96` and
any is not (an innermost `*96` under an outer non-96 op frame, e.g. a subclass `aspirate` calling
`aspirate96`; or an innermost non-96 op under a `*96` frame, `E1_via_96`), return `None`. (iii) No `*96`
frame: today's path, unchanged. `stamp` is not in `glossary.ACTIONS` (A33), so a `stamp` error resolves as
`aspirate96`/`dispense96` (`action == op`) and reads "Aspirate (96 head)"; its TooLittleVolume on `source`
is unreachable (A33), so no stamp row exists. PLR's own nested calls (A34) are all-96 and resolve.

**N5659-2. Locals mapping with a container-mode guard.** Read from the innermost op frame; absent -> `None`.

| Op | Source | `ErrorContext` field |
|---|---|---|
| `aspirate96`, `dispense96` | `containers` | **guard**: `container_mode = "per_channel"` iff `len(containers) == 96` and all share one parent; `"single"` iff `len(containers) == 1` and `lh._check_96_head_fits_in_container(containers[0])`; otherwise return `None` (48, 384, mixed plates, too-small container: C6) |
| same | committed `lh.head96[c].get_tip()` succeeding | `channels` = those c, ascending (NOT the `tips` local, A4) |
| same | `containers` | `resources` = `containers[c]` (per_channel) or `containers[0]` (single), one per channel in `channels` |
| same | `volume` | `volumes` = `(volume,) * len(channels)` |
| `pick_up_tips96` | `tip_rack` | `channels` = c whose spot `tip_rack.get_item(c)` has a committed tip; `resources` = those spots |
| `drop_tips96` (and via `return_tips96`/`discard_tips96`) into a `TipRack` | `resource` | `channels` = committed-mounted c; `resources` = `resource.get_item(c)` |
| all | | `head96 = True` |

New `ErrorContext` fields, appended after `available` with defaults (C18): `head96: bool = False`,
`container_mode: str | None = None` (core); `residue: tuple = ()` (residue layer). Tip-owner rows never
index `containers`. `lh.head96` empty or missing gives `None`.

**N5659-3. Owners on the 96 path.** (a) unchanged; (b) `lh.head96[c] is tracker` -> `OWNER_CHANNEL`,
`channel = c`; (c) a committed tip on `head96` whose tracker is the tracker -> `OWNER_TIP`; (d) unchanged
(no op frame; `head96` stays `False`, documented: a head96 tracker's "Channel N" parses as an 8-channel
head channel and the panel stays generic, errors.py:311; C14 rejected); (e) unused. `lh.head` is never read
on the 96 path.

**N5659-4. Committed offending set (O2), with its semantics stated.** Demand per distinct container =
`volume x (channels mapped to it)` (single mode: `n x volume`; shared wells in per_channel mode sum); a
container offends if demand exceeds committed volume (TLL) or committed room (TLV). Tip owners per channel
against committed tip volume / room. HasTip on pick-up: channels with a committed head tip whose spot c has
a committed tip. HasTip on drop: spots with a committed tip whose channel has a committed tip. Disabled
trackers not demanded. **NoTip on the 96 path always returns `None`** (A9). Owner outside the set -> `None`.
*Semantics:* "the channels the op uses" means the channels that physically hold a tip, i.e. the
committed-mounted set. PLR's iterated set is a subset of it (A28), so O2 can only add positions PLR did not
reach (after head residue: wells under channels PLR skipped, A30), never omit one PLR reached; and PLR's
failing owner is inside O2 unless the owner itself carries residue, which gives `None` as today.

**N5659-5. Position naming.** Head channels are named by the identifier of item c of the op's labware;
tip-owner and head-channel rows state counts and the value span, no position list, no drawing.

**N5659-6. Panel rows (strings PROVISIONAL until Q9; pinned by tests once answered).** `{W}` =
`compress_wells` (at most 96 ids; a checkerboard gives 48 comma items, bounded). `{k ...}` =
`glossary.plural`. Fix strings name the 96 parameter `volume`, not `vols`. Row choice: by `container_mode`
and owner kind, **never** by `_in_plate` (C4).

| Case (op, owner, mode) | Heading | Body | Fix | Drawing |
|---|---|---|---|---|
| TLL aspirate96, container, per_channel | "Not enough liquid in {plate} {W}." | no shared well: "Each well holds {avail} µL; the aspirate asked for {volume} µL on every channel." / "{W} hold {min}-{max} µL; ..." ; shared wells: "...; the aspirate asked for {req} µL per well, summed over the channels that share it." + "Nothing was aspirated." | "Lower `volume` to {min} µL or less, or aspirate from wells that hold more." | plate, offenders marked |
| TLL aspirate96, container, single | "Not enough liquid in {name}." ({name} = the Plate's name when the container is its only well, else the container's) | "It holds {avail} µL; the aspirate asked for {req} µL across {n channel}. Nothing was aspirated." | "Lower `volume`, or aspirate from a container that holds more." | none |
| TLL dispense96, tip | "Not enough liquid in {k tip} on the 96 head." | "Each holds {span} µL; the dispense asked for {volume} µL on every channel. Nothing was dispensed." | "Dispense {min} µL or less, or aspirate more first." | none |
| TLV dispense96, container, per_channel | "Not enough room in {plate} {W}." | as TLL with "has room for" | "Lower `volume`, or dispense into emptier wells." | plate |
| TLV aspirate96, tip | "Not enough room in {k tip} on the 96 head." | "Each has room for {span} µL; the aspirate asked for {volume} µL on every channel. Nothing was aspirated." | "Aspirate less, or use larger tips." | none |
| HasTip pick_up_tips96, channel | "The 96 head already holds a tip on {k channel}." | "{Action} asked those channels for another." | "Drop or discard the tips first." | none |
| HasTip drop/return/discard 96, spot | "{rack} {W} already has a tip." / "{rack} {W} already have tips." (more than one spot) | "{Action} asked to put tips there." | "Drop the tips into empty positions." | rack (committed tips, N5659-8) |
| NoTip (any 96) | generic | | | |
| TLV dispense96, single (incl. a one-well Plate) | generic (context computed, no row: today's gap, errors.py:257-258) | | | |

Stamps: well/spot rows `resource` = the drawn labware; single-container row = `{name}`; tip and channel
rows `null` (D2).

**N5659-7. Size: the 64 KiB cap is the only enforced whole-panel bound.** The r1 "<= 32 KiB" claim is
withdrawn (C1). Worst case, as a formula: `html ~= F + T_esc + X`, where `F` = the faulted figure (plate
~19.7 KB, rack ~19.4 KB *(v1 obs.; S5)*), `T_esc` = the escaped, capped traceback (<= 16,384 B raw;
escaping expands up to 6x for `"`, and `_fit` then shrinks the cap down `_TB_LIMITS`, errors.py:71, :373-383,
until the whole is <= 65,536), `X` ~ 1.5 KB of heading/body/fix/PLR line and markup (estimate). For a plain
16 KiB traceback the round-1 defender estimated **~38 KB (unmeasured)**. One instance is now measured
*(S5)*: the 96-fault plate panel with a 300-distinct-frame traceback (25,688 B raw, tail-capped) is
**38,616 B**: above the withdrawn 32,768, well under 65,536. It is one synthetic traceback, not a bound.
**D4 target revision (needs the user's approval under D4:198):** faulted figures miss D4's per-figure
targets: plate 19,746 / 16,384 (+21%), rack 19,437 / 12,288 (+58%) *(S5; identical to v1 obs.; unfaulted
9,164 / 9,639)*. Proposed: new targets
`<= 20,480 B` for a 96-fault plate figure and a 96-fault rack figure, checked by a test on the fixture, the
unfaulted targets unchanged. D5 unchanged (same `width`, `min-width`, `viewBox`, `s_n`, `s_min`; no `<circle>`).

**N5659-8. Committed rack tips in error panels (core).** `labware.render_figure` (and `_tiprack_figure`,
`tiprack_sentence`, `_block`) gain an optional keyword `tip_of(spot) -> Tip | None`, default `lambda s:
s.tip` (today's reading, so every non-error output is byte-identical). `errors` passes `_drawn_tip(spot)`
= the committed tip of `tip_spot_tracker(spot)` (`None` on `NoTipError`), defined next to
`errors._drawn_volume` (precedent, errors.py:181-184). The hook feeds the rings/dots/dashes
(labware.py:630-631), grid `vals` (:657) and the rack sentence (:278-280), so hover text, keyboard text and
drawing agree. Applied to **every** error panel that draws a rack, 1-channel included (Q6; if the user says
no, the hook is passed only when `ctx.head96`).

**N5659-9. Glossary.** `glossary.HEAD96_NOUN = "96 head"`, outside `NOUNS`; `SUFFIX_96 = f"
({HEAD96_NOUN})"`; `ACTIONS`/`VERBS` unchanged. Section 3.5's "ledger only" becomes "ledger and 96-head
error panels". The AC-28 scan covers the new constant.

**N5659-10. Ledger after-state reads committed volumes (core).** `_touch`, `_compute_after` and the
`volume_of` fallback (ledger.py:589, :600, :603, :691) read `tracker.volume`. Rows, names, counts and
`step_for` unchanged. *Corrected claim (C9):* identical to today whenever no touched well carries pending
residue when it is read; it differs (a) after a refused 96 op (the case it fixes) and (b) when residue
predates the op (direct tracker use, E13/E15, or an earlier refused 96 op on the same wells), where the
before-value is now committed. After a B2-style commit both readings are wrong (s.1.6); committed at least
shows the jump. Labware outputs (`display(plate)`, `labware._default_volume`, :218-219) **stay pending in
this increment** (Q7); epic :637-639 is amended to say so.

**N5659-11. Residue layer (separable; Q4).** New module `praxis/display/residue.py`, the only display
module that reads pending state: `_pending_volume(tracker)` (`pending_volume`) and `_pending_tip(tracker)`
(`has_tip`), plus `of(lh, ctx) -> tuple`. `context.resolve` calls it on the 96 path and stores the result in
`ErrorContext.residue`; `context.py` itself reads no pending state, so its AST scan (A35) is unchanged.
Residue = the op's containers whose `pending_volume != volume`; **the mounted tips** (committed tip of each
`head96` channel) whose tracker's `pending_volume != volume`; `head96` channels whose pending tip presence
differs from committed; the op rack's spots likewise. Residue from any earlier op counts (it is the state at
resolve time). When non-empty, every 96 row (not the generic panel) appends, after the fix, in
`praxis-summary` and in `text/plain`:
"PyLabRobot still records moves that did not happen on {X}; the next step that succeeds will save them, and
the tracked state will be wrong from then on." plus, **only when the panel has a drawing**, " The drawing
shows what was actually done." `{X}` joins "{plate} {W}", container names, "{k tip} on the 96 head",
"{k channel} of the 96 head", "{rack} {W}". Strings provisional (Q4). Read-only.

**N5659-12. Premise canaries.** Plain assertions named `test_plr_premise_*`: residue after a refused 96 op;
no-tip 96 ops raise nothing; partial head allowed; tracking off raises nothing; and the source-order canary
(AC-96-9). A pin bump that moves the loops into the `try` fails them and tells the maintainer the residue
layer can go.

## 6. Acceptance criteria

Run: from `/tmp/praxis-nd-b` (or a checkout), `PYTHONPATH=external/pylabrobot OMP_NUM_THREADS=2 uv run
--no-sync python -m pytest web-repl/tests/<ONE file> -k <sel> -q`, one file per process, never the whole
suite. Every positive names a negative control that **must FAIL**: a mutant (monkeypatched module function)
or a scenario, each run under `pytest.raises(AssertionError)` next to the real module passing. A check no
plausible mutant can fail is labelled a premise, not a control. Scenario-premise tests
(`test_every_scenario_raises_the_class_it_claims`, test_display_context.py:744) cover every new scenario.

**Core**

- **AC-96-1 Dispatch** (`test_display_context.py -k dispatch96`). `E96-empty` resolves on the 96 path;
  `E1_via_96` and new `E96-under-1ch` (a subclass `aspirate` that calls `aspirate96` on an empty plate)
  give `None`; `E96-return` has `action == "return_tips96"`, `op == "drop_tips96"`. **Controls:** an
  innermost-frame-only dispatcher resolves `E96-under-1ch` (fails); today's any-96 short-circuit fails
  every positive.
- **AC-96-2 Mapping and guard** (`-k map96`). `E96-empty`: `channels == tuple(range(96))`,
  `volumes == (50.0,)*96`, `container_mode == "per_channel"`, `head96 is True`. `E96-single` (J2):
  `"single"`, requested 2,880, available 2,000. `E96-onewell-plate` (`agenbio_1_troughplate_100mL_Fl`, which
  fits the head per S4, assigned into `lh.deck`'s subtree (a free plate-carrier site, or the deck directly if no site
  accepts it: unverified which); its well at 1,000 µL; `aspirate96(plate, 30)`):
  `"single"`, owner the well, requested 2,880, available 1,000. `None` for `E96-disp48` (`dispense96(assay["A1:H6"],
  50)` with tips holding 0), `E96-disp384` (a 384-well plate), `E96-disp-small` (a container failing the fit
  check). **Controls:** a guard-less mutant raises `IndexError` on `E96-disp48` and returns a context on
  `E96-disp384` (fails both).
- **AC-96-3 Offending sets** (`-k offend96`). `E96-empty` 96 wells, available 0; `E96-rowD` exactly D1-D12,
  available 10; `E96-partial` (G2) 92, A1/B1/C1/C7 absent; `E96-tipTLV` (C3) `OWNER_TIP` rule c, 96,
  requested 200, available 160; `E96-tipTLL` (D: 96, available 30; D2: channels 7 and 9, available 20);
  `E96-dispTLV` (E) C2, D2, A6, available 30; `E96-hasTip-pickup` (F3) owner channel 3 rule b, `[3, 50]`, spot
  3 emptied `[50]`; `E96-hasTip-drop` (H) owner spot F1, `[5, 77]`, channels 0-7 tipless `[77]`.
  **Controls:** first-failure-only mutant fails `E96-rowD`, `E96-empty`; mask-blind mutant (all 96 channels)
  fails `E96-partial`; `always_none` and `first_op_resource` (test_display_context.py:1431-1450) fail the new
  positives; read-only snapshot (volume, pending, committed tip, pending tip of every tracker) equal before
  and after `resolve`.
- **AC-96-4 Committed vs pending discriminators** (`-k discrim96`; adds `tips_b` on `tip_carrier[1]`, A37).
  (a) `E96-R2` (A29): owner channel 5, `len(offending) == 96`. **Control:** a has_tip (pending) reader
  mutant of the head/spot readers gives 91 (fails). (b) `E96-K` (A30): owner C2, offending A1-E1 and C2
  (6). **Control:** a PLR-demand mutant (channels = pending `has_tip` and committed `get_tip`) gives 1 (fails).
  If the user picks O2' (Q5), (b) flips to 1 and the control becomes the committed mutant.
- **AC-96-5 None cases** (`NONE_CASES` extended). `E96-noTip-residue` (L, both ops), `E96-noTip-spot` (Q),
  `E96-residue-TLL` (B, row D fixed with `set_volume(80)`, retry). **Controls:** a pending-volume reader
  (`_committed_volume -> pending_volume`) resolves `E96-residue-TLL` (fails); a mutant that drops the
  NoTip clause **and** uses all 96 channels resolves both NoTip cases (fails). `E96-runtime` and
  `E96-tooSmall` are premises only (non-display classes; no plausible mutant resolves them).
- **AC-96-6 Panels** (`test_display_errors.py -k panel96`). Each AC-96-3 positive renders its N5659-6 row:
  heading/body/fix, `text/plain`, "PyLabRobot raised ..." equals `str(exc)`, ring and cross counts equal the
  offender count, tip/channel/single rows have no `<svg>`, stamps per N5659-6, "Step n of the run." from a
  real `RunLedger`. `E96-onewell-plate` renders the single row ("across 96 channels"), never "on every
  channel". `E96-single` never shows "30.0uL > 20.0uL" outside the PLR line. Plural spots say "have".
  `GENERIC_CASES` drops `"E-96"`, gains `E96-noTip-residue`, `E96-residue-TLL` (both inside the `resolve is
  None` branch) and `E96-N`, `E96-onewell-TLV` (non-`None` context, no row; outside that branch).
  **Controls:** always-generic handler fails every row; an `_in_plate`-dispatch mutant renders the well row
  for `E96-onewell-plate` (fails); first-failure heading fails `E96-rowD`; `_drawn_volume ->
  get_used_volume` fails `E96-rowD`+residue (A1 drawn 30, committed 80, read from grid `vals`); a mutant
  that removes the no-row guard (errors.py:257-258) renders a row for `E96-N` (fails).
- **AC-96-7 Size** (`test_display_errors.py -k size96`, `test_display_labware.py -k faulted`). (a) The
  hostile-quote test (test_display_errors.py:1221-1231) gains two parameters: the `E96-empty` plate panel
  and the `E96-hasTip-drop` rack panel, rendered with `resolver=` returning the real context and a hostile
  exception of the matching class: `<= 65,536`, `check_bundle`, "Show traceback" present, quote count > 1000.
  **Controls:** the traceback-cap control (:1214) extended to these panels fails; a `_fit` mutant that renders
  level 0 with the full 16 KiB cap and no ladder exceeds 65,536 for `"` (fails). (b) **Only if Q3 = approve:**
  `len(render_figure(assay, fault=all 96)) <= 20,480` and the same for the rack; **control:** a
  `_mark_paths` mutant emitting one `<path>` per fault exceeds it (fails). (c) D5: faulted
  `width`/`min-width`/`viewBox` equal unfaulted; zero `<circle>`; **control:** a circle-per-fault mutant
  fails. (d) The unfaulted targets test (test_display_labware.py:1601-1607) is unchanged.
- **AC-96-8 Ledger** (`test_display_ledger.py -k after96`). A real refused `dispense96` (E) inside
  `RunLedger(lh, show=False)`: row status error, `step_for(exc) == 1`, `_after_state()` shows no changed
  well. **Control:** a pending-reading `_compute_after` mutant sees changed wells (fails). (b) Pre-existing
  direct residue on a touched well (E13 pattern) followed by a successful dispense: the after-state's
  before-value is committed (pins the changed behaviour, C9). `:1260-1261` unchanged.
- **AC-96-9 Source-order canary** (`test_display_errors.py -k order96`). For `aspirate96` / `dispense96`
  (`remove_liquid` / `add_liquid`) and `pick_up_tips96` / `drop_tips96` (`add_tip` / `remove_tip`): in the
  op's source body, first tracker call < `try:` < `await self.backend.<op>(`, and every `rollback()` is after
  `try:`. **Control:** the same function on 1-channel `aspirate` fails (its tracker call is inside the `try`,
  LH:1268-1274). Plus a chatterbox spy: no `aspirate96`/`dispense96` call recorded at a refusal;
  **control:** the spy records one on a successful `aspirate96`.
- **AC-96-10 Glossary** (`test_display_glossary.py -k head96`). `HEAD96_NOUN`, `SUFFIX_96` derived, existing
  tests unchanged; scan covers the constant. **Control:** the scan flags a synthetic module that spells it.
- **AC-96-11 Committed rack tips** (`test_display_labware.py -k tip_of`, `test_display_errors.py -k
  rack_committed`). Default hook: byte-equal to today on every existing labware golden. `E96-hasTip-drop`:
  drawn present 2, `vals` sum 2, sentence "2 of 96 tips left." (pending: 7). `P1` (1-channel, A31): drawn
  present 95, `vals` sum 95, sentence equals `tiprack_sentence` over committed tips. **Control:** the
  default (pending) hook in errors fails both. If Q6 = no: `P1` asserts today's pending drawing instead.
- **AC-96-12 Regression.** Every existing test in `test_display_{context,errors,ledger,glossary,labware}.py`
  passes unmodified except the supersessions in section 10 (Q8).

**Residue layer (only if Q4 is not "defer")**

- **AC-96-R1 Contents** (`test_display_context.py -k residue96`). `E96-rowD`: wells A1-C1 and the tips on
  channels 0-2; `E96-dispTLV` (E): 10 wells and 96 tips; `E96-hasTip-drop`: spots A1-E1 and channels 0-4;
  `E96-empty`: `()`. **Controls:** a detector ignoring tip volume trackers fails E and rowD; a
  committed-only detector (always `()`) fails every positive.
- **AC-96-R2 Sentence** (`test_display_errors.py -k residue96`). Present iff residue; drawing clause iff a
  figure: `E96-rowD` (plate row) has it; `E96-tipTLL` D2 (tip row, tips 0-6 residue) has the sentence without
  the clause; `E96-empty` has none. **Controls:** unconditional-clause mutant fails D2; always-sentence
  mutant fails `E96-empty`.
- **AC-96-R3 Module boundary.** A new AST scan: `pending_volume` and `has_tip` only inside
  `residue._pending_volume`/`_pending_tip`; `context.py`'s scan (test_display_context.py:1522-1559) unchanged
  and green. **Control:** the new scan flags a synthetic source reading `has_tip` outside the readers.
- **AC-96-R4 Read-only.** Snapshots before/after equal with the residue layer on.

## 7. Fixer tasks (tests first; each RED commit confirmed RED for the right reason)

### Task 1: glossary RED + GREEN
`HEAD96_NOUN`, derivation, scan (AC-96-10); fix glossary.py:24-27 docstring.
**Files**: `web-repl/tests/test_display_glossary.py`, `web-repl/overlay/assets/python/praxis/display/glossary.py` (modify)
**Gate**: `... pytest web-repl/tests/test_display_glossary.py -q`
**Scope estimate**: ~35 LOC

### Task 2: context core RED
AC-96-1..5 scenarios, mutants, read-only snapshot; supersede the E-96 pins (s.10, Q8); second rack in the test only.
**Files**: `web-repl/tests/test_display_context.py` (modify)
**Gate**: `... pytest web-repl/tests/test_display_context.py -k "96" -q` fails only on the new cases
**Scope estimate**: ~480 LOC

### Task 3: context core GREEN
N5659-1..4: dispatch, `_op96_inputs` + guard, head passed into the offender functions, new fields with defaults.
**Files**: `web-repl/overlay/assets/python/praxis/display/context.py` (modify)
**Gate**: `... pytest web-repl/tests/test_display_context.py -q`
**Scope estimate**: ~150 LOC

### Task 4: labware hook RED + GREEN
`tip_of` through `render_figure`, `_tiprack_figure`, `tiprack_sentence`, `_block`; faulted-figure test (b) only after Q3.
**Files**: `web-repl/tests/test_display_labware.py`, `web-repl/overlay/assets/python/praxis/display/labware.py` (modify)
**Gate**: `... pytest web-repl/tests/test_display_labware.py -q`
**Scope estimate**: ~110 LOC

### Task 5: errors core RED
AC-96-6, -7, -9, -11 (errors part); `GENERIC_CASES`.
**Files**: `web-repl/tests/test_display_errors.py` (modify)
**Gate**: `... pytest web-repl/tests/test_display_errors.py -k "96 or rack_committed" -q` fails only on new cases
**Scope estimate**: ~450 LOC

### Task 6: errors core GREEN
96 rows, mode dispatch, `_drawn_tip` hook; errors.py:30 docstring.
**Files**: `web-repl/overlay/assets/python/praxis/display/errors.py` (modify)
**Gate**: `... pytest web-repl/tests/test_display_errors.py -q`
**Scope estimate**: ~160 LOC

### Task 7: ledger RED + GREEN
AC-96-8; N5659-10.
**Files**: `web-repl/tests/test_display_ledger.py`, `web-repl/overlay/assets/python/praxis/display/ledger.py` (modify)
**Gate**: `... pytest web-repl/tests/test_display_ledger.py -q`
**Scope estimate**: ~70 LOC

### Task 8: residue layer RED + GREEN (separable; skip if Q4 = defer)
AC-96-R1..R4; `residue.py`; `ErrorContext.residue`; sentence.
**Files**: `web-repl/overlay/assets/python/praxis/display/residue.py` (create), `context.py`, `errors.py`, `test_display_context.py`, `test_display_errors.py` (modify)
**Gate**: `... pytest web-repl/tests/test_display_context.py -k residue96 -q` then `... test_display_errors.py -k residue96 -q`
**Scope estimate**: ~260 LOC

### Task 9: regression sweep
Each of the five files once, one process each (AC-96-12). Browser: none (only known classes are emitted; `test_display_css.py` scans them).
**Gate**: five single-file pytest runs green
**Scope estimate**: 0 LOC

Order: 1, 2, 3, 4, 5, 6, 7, then 8; 9 last. Epic edits (s.10) are doc work after the user's answers, not a fixer task.

## 8. Risks

| Risk | Mitigation |
|---|---|
| `containers`/`volume` are PLR-internal locals | A3; AC-96-2 on the real pin; Option B fallback |
| PLR moves the 96 loops into the `try` | canaries fail (N5659-12); the residue layer is then removable; the core is unaffected |
| Superseding the E-96 pins reads as loosening | strictly stronger positives, surviving negatives kept; needs the user's yes (Q8) |
| Faulted figures miss D4 targets | explicit D4:198 revision (Q3); 64 KiB enforced; F3 block level as fallback |
| Committed demand names wells PLR skipped (A30) | stated semantics; gated; user decision (Q5) |
| After a B2 commit committed state is not physical either | the residue sentence warns before the commit; nothing can repair after it; upstream report (Q1) |
| 1-channel rack drawing changes | positive test P1, `vals` + sentence pinned; Q6 can scope it to 96 panels |
| Ledger (committed) vs `display(plate)` (pending) disagree after a refused 96 op | listed (:637-639), Q7; follow-up decides labware |
| Tip/channel rows have no positions | deliberate (N5659-5) |
| Backends without a 96 head (WebBridgeBackend, OT-2) get KeyError tracebacks | out of scope, stated (s.1.8) |
| A new module `residue.py` in the wheel | no per-file manifest found in `web-repl/scripts`; Task 9 + the REPL gate confirm (unverified until CI) |

## 9. Open questions for the user

All in `5659_decisions.md` (Q1-Q9, plain language, defaults). Q1 build/upstream, Q2 coverage/worth,
Q3 faulted-figure targets, Q4 residue sentence, Q5 committed vs PLR demand, Q6 1-channel rack drawings,
Q7 ledger committed vs display pending, Q8 E-96 pins, Q9 wording ("96 head", provisional strings).
Partial-head ledger counts (r1 Q6) stay a follow-up.

## 10. What this changes (NOT edited here)

**Epic `260929_notebook-display-epic.md`:** D8 intro (:470-471, "out of MVP scope" removed); D8 step 2
(:513-517, short-circuit -> N5659-1); step 3 rule (b) (:538, head96 on the 96 path); step 4 (:555-593, 96
rules, NoTip clause; "Pending residue" :577-586 drops "a failed aspirate or dispense leaves none" for 96
ops); step 5 (**:591**, "or a `*96` op is on the stack" -> the mixed-stack rule); "Panel drawing"
(:604-641: first bullet scoped to 1-channel; a 96 bullet; **:636** "never describes the other channels'
tracker state" gains "except the 96 residue sentence"; **:637-639** "Other outputs keep drawing ...
get_used_volume()" gains "the ledger after-state reads committed (N5659-10); error-panel racks draw
committed tips (N5659-8)"); D4 (:191-200, faulted-figure targets if Q3 approves); D9 (:651-690, one sentence:
after-state reads committed); section 3.3 (:1772-1803 rows; :1799 drops "or a `*96` op"); goals/non-goals
(:1632-1633, :1664); section 3.5 (:1843-1846); file plan (:1925 context row; errors/labware/glossary rows;
new `residue.py` row); **:3208** (B5 task text, "the `*96` short-circuit"); **:3816** ("`*96` errors are
out of MVP scope"); AC-15 E-96 (:2218-2223) -> AC-96-1..5; AC-16 -> AC-96-6, -11; AC-13 -> AC-96-7; AC-14 ->
AC-96-8; AC-28 -> AC-96-10; risks (:3506, :3509) and OQ-6 (:3557) extended to the four 96 ops.

**Code docstrings:** `errors.py:30` ("a `*96` op" in the generic-panel list); `context.py:14` ("If any op
frame is a `*96` op the result is `None`"); `context.py:447` (resolve docstring "a `*96` op"); `glossary.py:24-27`.

**Tests (five files):** `test_display_context.py` docstring :9 and :38-40; `check_e96` (:1049-1051) and its
`CHECKS` entry (:1091); `NONE_CASES` (:1424-1428, drop "E-96", add the AC-96-5 cases);
`test_real_resolver_passes_what_the_controls_fail` (:1454, drop "E-96"); the test at :1230 renamed from
"applies_to_any_96_frame_on_the_stack" to "a_non_96_op_under_a_96_frame_resolves_to_none" (body
unchanged; still true under N5659-1); `test_e96_is_a_real_96_head_failure_with_a_96_frame` (:1220) kept.
`test_display_errors.py`: `GENERIC_CASES` (:997) and its branch (:1003); hostile-quote parametrisation
(:1221); traceback-cap control (:1214). `test_display_glossary.py:180-181` ("No error template uses a 96
verb" -> "96 panels use base verbs plus `HEAD96_NOUN`"). `test_display_labware.py` (new `tip_of` and
faulted tests). `test_display_ledger.py` (AC-96-8).

**Backlog:** #5659 umbrella; Tasks 1-9; a follow-up for partial-head ledger counts and for whether labware
outputs switch to committed.

---

## Rulings (user, 2026-10-01) -- appended by the orchestrator; no other text changed

The user answered the decision sheet (`5659_decisions.md`) with: "build now, draft the upstream report. yes,
for the covered backends. go with your recommendations they seem sensible. don't file reports, just draft
them". Recorded answers:

| Q | Ruling |
|---|---|
| Q1 build now or wait for PLR | **(a) build the core now.** The upstream report is **drafted by the orchestrator, NOT filed** (the user files, if at all) |
| Q2 worth building given who sees these panels | **(a) yes, for the covered backends** (chatterbox simulation, SerializingBackend, a STAR reporting a 96 head); WebBridgeBackend/OT-2/Vantage/EVO are not covered |
| Q3 size of faulted drawings | **(a) approve** measured 20,480-byte (20 KiB) targets for fully-faulted plate and rack drawings under D4:198; normal targets unchanged; no compaction, no second ceiling |
| Q4 residue sentence | **(a) keep, as a separate task after the core** (task 8) |
| Q5 offending set | **(a) committed** (what the head physically holds) |
| Q6 1-channel rack drawings | **(a) yes**, committed tips in every error panel; pinned by a new test |
| Q7 ledger | **(a)** the ledger reads committed; plate drawings in later cells stay pending for now |
| Q8 replace the E-96 pins | **(a) yes** (a legitimate spec change; the surviving negatives are kept) |
| Q9 wording | **accept as written** (the provisional strings get pinned by the tests) |

Core = tasks 1-7 then 9; task 8 (residue) runs after the core is verified. `status` is now `accepted-r2`.
