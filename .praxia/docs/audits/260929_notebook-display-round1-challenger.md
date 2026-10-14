---
title: Notebook display epic, round 1 challenger
description: Adversarial challenge of the notebook display epic spec draft (51bebdc5). Verdict REVISE, with 2 blockers, 13 majors and 14 minors.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 1 challenger

Spec: `.praxia/docs/specs/260929_notebook-display-epic.md` @ 51bebdc5. Reviewer:
praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r1`.

Verdict: **REVISE**

Orchestrator checks (260929): C1-1's premise holds (`hamilton_decks.py:22`
`STARLET_SIZE_X = 1005`). C1-3's premise holds: `origin/main:web-repl/tests/plr_contract.py`
lists `pylabrobot.resources.coordinate` (line 78) and no `pylabrobot.resources.resource`.

## Findings

### C1-1 [BLOCKER] The deck detail floor contradicts itself, and AC-12 fails on the fixture deck
- Where: D5 "Scale terms" / "For the deck, `s_min = 0.6`", the D5 worked check, AC-12.
- Claim:
  - Labels are drawn at `12.5 / s_n` user units, so at `s_min` they render at
    `12.5·s_min/s_n` px. For the fixture STARLet (1005 mm), `s_n ≈ 0.876`, so labels come out
    at about 8.6 px. That is below the 11 px invariant, and AC-12's own check fails.
  - The worked check confuses `s_n` with `s_min`.
- Required change:
  - Use `s_min = max(0.88·s_n, 0.6)` for the deck too, and re-derive the full-detail rule.
  - Fix the worked check.
  - Add a deck narrower than 880 mm to AC-12.

### C1-2 [BLOCKER] The `praxis_viz3d` protocol cannot be implemented: the page never learns the `viewer` id
- Where: D11 protocol table, D12, §3.6 iframe URL, C3/C4, AC-32.
- Claim:
  - `open` needs `{viewer, client}`, but the iframe URL is fixed and `announce` may come
    before the iframe loads.
  - Nothing supplies the id on first load, reload or drawer move.
  - Re-running `dock()` leaks the previous viewer's subscriptions.
- Required change:
  - The shell sets `?viewer=<id>` (plus a nonce, C1-9) in the iframe `src` and reloads on each
    `announce`, or add a discovery message.
  - `dock()` stops any previous viewer.
  - Add AC cases for a re-run `dock()` and for an iframe loaded after the announce.

### C1-3 [MAJOR] The vendored Python breaks `test_contract_covers_imports.py`, and no task handles it
- Where: D11 "Python", C2, AC-33, section 4.
- Claim:
  - The vendored `server.py:31`, `scene.py:17`, `grids.py:11` and `facility.py:8` import
    `pylabrobot.resources.resource`, which is absent from `plr_contract.CONTRACT`.
  - The files are byte-identical, so the imports cannot be rerouted, and CI goes red at C2.
  - The `praxis/display/*` modules likely import other absent submodules.
  - Shipping loose PLR-main code beside the 0.2.2 wheel deviates from ADR §2.
- Evidence: `web-repl/tests/test_contract_covers_imports.py:176-180`; `plr_contract.py:58-102`.
- Required change:
  - Add tasks that extend the contract with a justification (or exclude `plr_visualizer3d/`
    for a stated reason).
  - Put the test in the gates for C2 and B8.
  - File an ADR amendment.

### C1-4 [MAJOR] Error context resolution has no path for `HasTipError("Channel has tip")`, and the set of offending wells is undefined
- Claim:
  - (a) `liquid_handler.py:533-535` raises with no tracker frame, so E4 resolves to `None`.
  - (b) PLR raises on the first failing op only (`:1031-1035`). The spec never defines the set
    of offending wells.
  - (c) The panel mixes pending (`available` parsed from the message) and committed volume.
    With a resource repeated across channels this reads "holds 0 µL" beside a full well.
- Required change:
  - Add owner rule (e) for `HasTipError`.
  - Define `offending` with a single volume basis.
  - Add AC cases for a repeated resource and for mixed wells.

### C1-5 [MAJOR] `RunLedger` double-records `discard_tips`/`return_tips`, so AC-14's row count is ill-defined
- Claim:
  - `discard_tips`/`return_tips` call `self.drop_tips` (`liquid_handler.py:775, 833, 1646, 1678`),
    so the ledger records twice.
  - The error handler has no mechanism to get the step number.
- Required change:
  - Treat an op called while another is in flight as its child.
  - Define how the step reaches the handler, with an AC.
  - Say whether the ledger is displayed on the error path.

### C1-6 [MAJOR] The persistence ladder on `main` intercepts saves in the display harness
- Claim: The first-save modal `dialog#praxis-persistence-first-save` blocks the save steps in
  AC-23/AC-24 when run in a fresh context.
- Required change:
  - D16 pre-sets the ack key (`praxis-repl-persistence-ack`) or dismisses the modal through
    its real control.
  - Add a key asserting the modal did not block.

### C1-7 [MAJOR] S2 assumes a reopened notebook is untrusted, and no branch covers "reopened as trusted"
- Required change:
  - A2 probes the crafted, the executed-saved-reopened and the download/upload paths.
  - Add branch S2-T.
  - AC-24 asserts the branch recorded for the executed-saved-reopened path.

### C1-8 [MAJOR] The size-clamp fallback targets an API a DockPanel split doesn't have, and the ≥1600 tier has no mechanism
- Claim:
  - `setRelativeSizes` is a `SplitPanel` method; a main-area `split-right` lives in a
    `DockLayout`.
  - A stock 50/50 split passes AC-36 at ≥1600.
- Required change:
  - Add an S1 branch (DockLayout `saveLayout`/`restoreLayout` sizing, or escalate).
  - Give the ≥1600 target a number: ±8 px.
  - Add a negative case: a stock 50/50 split must fail.

### C1-9 [MAJOR] Dropping the viewer's token rests on a misread citation, and inbound traffic is unbounded
- Claim:
  - `transport.py:16-18` is a delivery note, not a security acceptance.
  - `praxis_viz3d` is bidirectional, and a `*.github.io` origin is shared with the account's
    other project pages.
  - Upstream has a token plus Host/Origin checks (`server.py:170-173, 329-349`).
  - The same-origin, unsandboxed iframe gets `window.parent`.
- Required change:
  - Add a threat model.
  - Use a per-viewer nonce in the shell-set iframe URL, required on `open`.
  - Cap the virtual clients and drop unknown `kind`s.
  - Add AC cases for a wrong nonce and for client N+1.

### C1-10 [MAJOR] No HTML-escaping requirement for user-controlled strings in trusted outputs
- Required change:
  - `html.escape(quote=True)` for text and attributes.
  - JSON-in-attribute escaping.
  - ANSI stripping for the traceback.
  - `CSS.escape`/attribute comparison in the shell scripts.
  - Hostile-name AC cases.

### C1-11 [MAJOR] The shell cannot tell which session is current
- Required change:
  - `install()` posts `praxis:display-session`.
  - No marks before a session is known.
  - Add an AC key after a kernel restart.

### C1-12 [MAJOR] Marks written only to the DOM are lost when JupyterLab re-renders or virtualises cells
- Required change:
  - Re-apply marks on cell attach and output re-render, naming the signal.
  - S1 records the windowing mode.
  - Add an AC for scrolling out of view and back.

### C1-13 [MAJOR] `cellState(model, kernelStatus)` cannot compute "stale", and state precedence is undefined
- Required change:
  - Take a per-cell execution snapshot.
  - Define precedence and the post-reload state.
  - Extend AC-5.

### C1-14 [MAJOR] The viewer's hello `print` lands in whichever cell is executing, and AC-34 depends on it
- Evidence: `server.py:577-585`.
- Required change:
  - State where the output goes.
  - Read `hello_backend` from `viewer.clients_seen[-1]`.

### C1-15 [MAJOR] A binding user decision is unmet but filed as non-blocking
- Claim: "identity on hover" can't be built at the pin (`volume_tracker.py:122-138`), and OQ-2
  is marked non-blocking.
- **Orchestrator note:** the user already answered this on 260929: "keep blue as volume, we can
  make things more complicated later." Volume only is accepted. OQ-2 closes as decided.

### C1-16 [MINOR] A6 has a hidden dependency on A5
- A6 makes assert_dist_complete require shell/display/{index,chrome}.js and AC-6 runs a build plus test -f, neither of which can pass before A5. Required change: make A6 depend on A5, or have A6 create stubs.
### C1-17 [MINOR] The R21 grep is not extended to the new visualizer paths
- Required change: add web-repl/overlay/assets/visualizer3d/, visualizer3d-augmentations/ and web-repl/shell/display/dock.js to the R21 grep, with test -d and exit 1 exactly (as AC-41 does for R19).
### C1-18 [MINOR] The stamp omits "the cell that drew it"; `session` is named two ways
- Required change: add exec (the execution count) and/or a cell id to metadata.praxis, or state that rev/session replace it and why; use one term for session (D2 calls it a kernel session id, D7 says install() mints it).
### C1-19 [MINOR] "The four errors fire only with tracking enabled" is false for head-side errors (`liquid_handler.py:534-535, 655, 684, 974`)
- Required change: correct the statement, and add an AC-15 case with tracking off (E4 and E6 still resolve).
### C1-20 [MINOR] `action = f_code.co_name` can be a comprehension frame or the wrong glossary action (`:504, :974`)
- Required change: take the innermost frame whose co_name is in glossary.ACTIONS, and state whether the user-level caller (discard) or the inner op (drop) names the action.
### C1-21 [MINOR] Follow reframes from the iso direction (`app.js:180`) and overrides the user's preset
- Required change: dock.js passes the current preset as viewName; add an AC-35 key that after Top then Follow the camera direction is still Top.
### C1-22 [MINOR] Mesh and `_models_on_disk` behaviour are unexamined after the rename and without a file server (`server.py:98, 224, 280, 791`)
- PACKAGE_ROOT becomes the parent of plr_visualizer3d; any mesh gets the URL mesh/<id>, which only the removed file server serves; stock start also runs _models_on_disk in a thread. Required change: state that meshes are unsupported (drawn as boxes); S4 records the _models_on_disk walk and its cost; AC-31 asserts no mesh.url for the fixture.
### C1-23 [MINOR] The byte budget can be moved by the implementer, and the grid JSON and traceback are unbudgeted
- D4 says 'any miss is revised with a recorded reason', which lets the fixer move the gate. Required change: say who approves a revised target, whether level 1 of the ladder drops the grid descriptor, and a traceback truncation rule.
### C1-24 [MINOR] Registering `Container` pulls in Next-list labware (Trough, Tube, PetriDish, Trash)
- Required change: list which Container subclasses get a figure in the MVP, and what the rest show (sentence only).
### C1-25 [MINOR] Drawer-tier behaviour (auto-open, dismissal, resize back up) is underspecified
- Required change: state whether the first announce at 1024-1279 auto-opens the drawer over the notebook, how it is dismissed and reopened, and what happens on a resize back above 1280.
### C1-26 [MINOR] `VirtualConnection`s are not ended on `stop()`
- super().stop() clears _clients but the tasks running _handler keep awaiting their queues. Required change: stop() ends every VirtualConnection; AC-31 asserts no _handler task is pending after stop().
### C1-27 [MINOR] Spike S4, the one that can stop the viewer, runs last; move it to sprint A
- Required change: run C1/S4 in sprint A alongside S1-S3, so an S4-C stop is known before sprint B.
### C1-28 [MINOR] AC-30's tag-position check is weaker than D11's rule (`index.html:319`)
- AC-30 checks 'before the first <script type="module"', D11 says immediately before the first <script (index.html:319, the classic gif.js). Required change: AC-30 asserts the D11 position.
### C1-29 [MINOR] The default Dark theme's chrome is never gated in a browser
- Required change: run scenario D1 in JupyterLab Dark as well, asserting rail states and colours.

## Summary
BLOCKER 2, MAJOR 13, MINOR 14. Top: C1-1, C1-2, C1-3; then C1-4 and C1-6.
