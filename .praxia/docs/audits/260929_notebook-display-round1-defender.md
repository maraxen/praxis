---
title: Notebook display epic, round 1 defender
description: Defender rulings on the 29 round 1 findings. Verdict REVISE with 25 CONCEDE, 3 PARTIAL and 1 REBUT, consolidated into amendments A-1..A-20 for Revision 1.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 1 defender

Reviewer: praxia:spec-defender (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-defense_r1`. Challenge:
`260929_notebook-display-round1-challenger.md`.

Verdict: **REVISE**. Both blockers are real and can be fixed in the spec text. No finding
needed recon. Rejected fixes: the C1-9 nonce. Better fixes than the challenger's: C1-4(c), C1-10,
C1-20.

**Orchestrator rulings (260929):**
- C1-9 threat model verified. `origin/main:web-repl/bootstrap/praxis_bootstrap.py:214-218`
  executes `code` from any `praxis:execute` message on `praxis_repl`, so a same-origin page
  already has kernel code execution and a viz3d nonce raises no bar.
- "Needs the user" S1-L: take the defender's default (accept and state the deviation). It is
  consistent with the user's 260929 ruling "split initially. we can figure out a more
  ergonomic layout later."
- C1-15: closed by the user's 260929 ruling (volume only).

## Rulings

- **C1-1 CONCEDE.** For the STARLet `s_n = 880/1005 ≈ 0.876`, so labels at `s_min = 0.6` render
  at 8.6 px. Fix: deck `s_min = max(0.88·s_n, 0.6)`. Cost: the fixture deck's min-width is about
  775 px and scrolls by about 65 px at a 710 px notebook, which D5 allows. Sizing labels at
  `11/s_min` was rejected (labels grow to 16–27 px).
- **C1-2 CONCEDE.** The fixed iframe URL means the page never learns the viewer id, and the
  page transport gives up after 60 s (`static/transport.js:26,73`), so an early iframe is dead.
  Fix:
  - a `query` kind;
  - the shell sets the iframe `src` with `&viewer=<id>` on every announce;
  - the shim posts nothing without `viewer` and fires `onclose` after 3 s;
  - `dock()` keeps a module-level current viewer and awaits its `stop()` (a module function,
    not an override);
  - new AC keys: second-dock, no-viewer shim, `redock_reloads`, `late_iframe`.
- **C1-3 PARTIAL.** Extend the contract; don't exclude the directory. Add
  `("pylabrobot.resources.resource", "Resource")` in C2, plus a per-task contract entry for any
  new `pylabrobot.*` import in B2/B4–B7. Put the test in the C2 and B gates. Append an ADR §2
  addendum.
- **C1-4 CONCEDE.**
  - (a) Owner rule (e): no tracker frame plus `HasTipError` in an LH frame with a `channel`
    local means the owner is that channel.
  - (b), (c) `offending` and all body numbers use committed state only, with demand summed per
    resource:
    - TLL: summed demand > `tracker.volume`.
    - TLV: summed addition > `max_volume − tracker.volume`.
    - Tip-owner TLV: the tip on channel c.
    - HasTip/NoTip: conflicting committed tip state.
    - The resolved owner is always included; `{avail}` is committed, `{req}` is summed.
    - PLR's number appears only in the verbatim "PyLabRobot raised" line.
  - New AC-15 cases: E9 (a trough across 8 channels), E10 (mixed wells).
- **C1-5 CONCEDE.**
  - Any wrapped op called while another is in flight becomes its child row. Steps, tip cycles
    and µL moved count top-level rows only.
  - On exception the wrapper marks the row `error`, stores `(exc, step)` in
    `ledger._ERROR_STEPS[id(exc)]` and re-raises. `errors.handler` reads it with
    `ledger.step_for(exc)` and removes it.
  - `__exit__` with an exception still shows the ledger (unless `show=False`) before the error
    panel.
  - AC cases: discard gives one row with one Drop child; the step number appears in the panel.
- **C1-6 CONCEDE.** The harness init script sets
  `localStorage["praxis-repl-persistence-ack"] = "browser-only"` when `main` carries the ladder.
  New key `persistence_gate_never_open` on AC-23/24.
- **C1-7 PARTIAL.** S2 also records the trust state and mimetype of a notebook executed, saved
  and reopened in the same browser.
  - New branch **S2-T**: reopened trusted, which renders as live.
  - AC-2 gains a column; AC-24 matches that path's branch, with S2-T keys `svg_in_dom` plus
    `liquid_fill_computed`.
  - Upload/download is already the crafted case, so no third probe is needed.
- **C1-8 PARTIAL.** Replace `setRelativeSizes` with the main DockPanel's `saveLayout()`, then
  edit the split area's `sizes`, then `restoreLayout()`. S1 records
  `dock_layout_sizing_reachable`.
  - New branch **S1-L**: when neither CSS limits nor layout sizing work, the initial width is
    set once and the drag is unclamped. The drag-clamp keys become recorded-only, as a stated
    deviation.
  - ≥1600 target: `panel_width = max(420, main_area_width − 960 − nb_h_padding)` ±8 px at
    1600×900 and 1920×1080, with the file browser closed.
  - AC-39 negative case: a stock 50/50 split fails.
  - Update the Risks row.
- **C1-9 PARTIAL.**
  - The citation is misread (a delivery note), and the nonce is rejected: same-origin already
    has `praxis:execute`, and a nonce on a broadcast bus is visible to all listeners.
  - Upstream's token and Host/Origin checks defend a cross-origin localhost websocket, which
    does not exist here. The `window.parent` access is our own vendored code on our own origin.
  - Replace the rationale with the origin threat model. Cap virtual clients at 4; drop unknown
    `kind`s and non-JSON.
  - AC-31: client 5 gets no `accept`; an unknown kind is ignored with no exception.
- **C1-10 CONCEDE.**
  - `svg.py` owns `esc_text`/`esc_attr` (`html.escape(quote=True)`) for every interpolated
    string. `data-praxis-grid` is `esc_attr(json.dumps(...))`.
  - The traceback is `traceback.format_exception(...)` (no ANSI), escaped.
  - Shell modules match by `el.dataset.praxisRes === name`, never by building a selector.
  - AC-9: a plate named `<b>&"'x` appears escaped, with zero raw `<b>`. AC-19: `focus()` gets
    the exact name.
- **C1-11 CONCEDE.**
  - `install()` posts `{type:"praxis:display-session", json:"{\"session\":...}"}` through
    `stale.py`'s poster.
  - The current session is the last one seen. There are no session marks until one is known.
  - AC-18: exactly one post. AC-19: no marks before a session. AC-23:
    `earlier_session_marked` after a restart.
- **C1-12 CONCEDE.**
  - `stale.js` keeps marks in memory and re-applies them idempotently on each cell's
    `outputs.changed`, on `inViewportChanged` (or the equivalent S1 records), and on
    `activeCellChanged`.
  - S1 records `windowingMode` and the re-attach signal.
  - AC-23: `mark_survives_scroll`.
- **C1-13 CONCEDE.**
  - `cellState(model, {running, snapshot})`, where the snapshot is the source captured when an
    execution is observed, or at first observation for loaded cells.
  - Precedence: running > stale > error > ran > not-run.
  - After a reload, cells show ran/error from their saved outputs, and stale only after an edit
    in this page.
  - Extend AC-5 with these cases.
- **C1-14 CONCEDE.**
  - `dock()` awaits `viewer.wait_for_browser(timeout=15)` (the TimeoutError is caught and
    stated), so the first hello prints in the `dock()` cell. Later reconnect hellos land in the
    current cell, which is accepted and stated.
  - AC-34 reads `viewer.clients_seen[-1]["backend"]` by evaluating a cell.
- **C1-15 PARTIAL.** Moot. D15 records the user's decision, OQ-2 closes, and the Non-goals line
  cites the user decision of 260929.
- **C1-16 CONCEDE.** A6 depends on A5. Sprint A order: A1, A2, A3 in parallel; then A4 and A5
  (after A1); then A6 (after A5); then A7.
- **C1-17 CONCEDE.** From sprint C, the R21 grep also covers `visualizer3d/`,
  `visualizer3d-augmentations/` and `shell/display/dock.js`, with `test -d` and exit 1 exactly.
- **C1-18 CONCEDE.** The stamp becomes `{v, kind, resource, rev, session, exec}`, with
  `exec = get_ipython().execution_count`. The term is "display session id": random, minted once
  per kernel process by `install()`. Update AC-9's keys.
- **C1-19 CONCEDE.** Spot-side and volume errors need tracking on (off by default). Head-side
  HasTip/NoTip fire regardless (`liquid_handler.py:534, 655, 974`). AC-15: E4-off and E6-off.
- **C1-20 CONCEDE.** The innermost frame whose `self` is a LiquidHandler and whose `co_name` is
  in `glossary.ACTIONS` supplies the locals, which skips `<listcomp>`/`<genexpr>`. The outermost
  such frame supplies `action` (the user's call), so `return_tips` reads "Return tips". AC-15
  adds a case for `return_tips` onto an occupied spot.
- **C1-21 CONCEDE.** `dock.js` holds the preset (initially `top`) and always calls
  `focus(name, preset)`. AC-35: `follow_keeps_preset`, with
  `normalize(from − at)·VIEWS.top > 0.99`.
- **C1-22 PARTIAL.**
  - `start` does not pre-warm `_models_on_disk`; its first call is the inherited scene build
    (`server.py:417`).
  - Meshes are unsupported (0 `.glb` vendored, 0 `reference_glb` in PLR 0.2.2), so every model
    is drawn as a box.
  - S4 times the first `_models_on_disk(PACKAGE_ROOT)`. AC-31: no `mesh` in the fixture scene.
- **C1-23 PARTIAL.**
  - A revised target needs the orchestrator's approval, recorded in the sprint PR; the fixer
    doesn't edit targets.
  - Ladder level 1 drops `data-praxis-grid` for blocked labware.
  - The traceback is capped at 16 KiB with the tail kept and "… N earlier lines omitted".
    Everything counts toward the 64 KiB cap, and the drawing degrades first.
  - AC-13: a 200-frame traceback stays ≤ 65,536 bytes.
- **C1-24 CONCEDE.** MVP figures: `Plate`, `TipRack`, `Deck`, `Well`. Other `Container`
  subclasses get the name line and sentence only (`kind="container"`, no drawing). Infinite
  `max_volume` reads "{name} holds {v} µL." AC-10: a Trough with no `<svg`.
- **C1-25 CONCEDE.**
  - At 1024–1279 the first announce opens the drawer.
  - A close button or Escape hides it; `praxis:toggle-deck-panel` reopens it.
  - Crossing to ≥1280 re-homes an open drawer into the split (one iframe reload) and leaves a
    closed one closed. Crossing below 1280 does the reverse.
  - AC-36: `drawer_dismiss_reopen`, `tier_up_rehomes`.
- **C1-26 CONCEDE.** `stop`: `super().stop()`, then end every VirtualConnection (a queue
  sentinel), await its handler task, and post `close`. AC-31: no `_handler` task pending.
- **C1-27 REBUT.** C1 already depends on nothing and can run during sprint A, and sprints A and
  B don't depend on S4 (§7). This is scheduling, not spec content.
- **C1-28 CONCEDE.** AC-30: the socket.js tag is the first `<script` element, immediately followed
  by the original `:319` gif.js tag.
- **C1-29 CONCEDE.** AC-7 adds scenario D1-dark in the default JupyterLab Dark: the five
  `rail_state_*` keys, `prompts_take_no_space`, and `rail_colors_match_dark` (rail grey is the
  computed `--jp-border-color1`).

## Amendment list (apply in this order)
1. A-1 (D5, AC-12): C1-1.
2. A-2 (D11 protocol and Kernel, D12, §3.6, AC-31/32/38): C1-2.
3. A-3 (D11 threat model, AC-31): C1-9.
4. A-4 (D11 Kernel start/stop, S4, AC-31, AC-34): C1-14, C1-22, C1-26.
5. A-5 (AC-30): C1-28.
6. A-6 (C2, B2/B4–B8 gates, ADR addendum): C1-3.
7. A-7 (D8 steps 2–4, tracking note, AC-15/16): C1-4, C1-19, C1-20.
8. A-8 (D9, AC-14/16/17): C1-5.
9. A-9 (D2, §3.2, D14, AC-9/10/19): C1-10, C1-18, C1-24.
10. A-10 (D4, AC-13): C1-23.
11. A-11 (D7, AC-18/19/23): C1-11, C1-12.
12. A-12 (§4 chrome.js, AC-5): C1-13.
13. A-13 (D1 S1, D6, Risks, AC-36, AC-39): C1-8, C1-25; S1-L is accepted as a stated deviation.
14. A-14 (D12, AC-35): C1-21.
15. A-15 (D1 S2, §4 A2, AC-2, AC-24): C1-7.
16. A-16 (D16, AC-23/24): C1-6.
17. A-17 (AC-7): C1-29.
18. A-18 (AC-18, AC-31): C1-17.
19. A-19 (A6, the §6 table and order): C1-16.
20. A-20 (D15, §2, §8 OQ-2): C1-15.
