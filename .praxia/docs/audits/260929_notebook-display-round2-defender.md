---
title: Notebook display epic, round 2 defender
description: Defender rulings on C2-1..C2-12 (10 CONCEDE, 2 PARTIAL), consolidated into amendments B-1..B-12 for Revision 2. Verdict REVISE.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 2 defender

Reviewer: praxia:spec-defender (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-defense_r2`. Verdict: **REVISE**. No standing ruling is
reopened.

**Orchestrator rulings (260929):**
- C2-7 is verified. IPython `core/formatters.py:243-250` (9.13.0 in the uv cache) unpacks a
  `(data, metadata)` tuple returned by a per-type formatter into `md_dict[format_type]`.
- B-9's scope cut is confirmed: `*96` errors are out of the MVP and get the generic panel. MVP
  item 3 names four error classes and says nothing of heads.

## Rulings

- **C2-1 CONCEDE.**
  - Evidence: `transport.js:56-75` only reconnects, and `server.py:357-361` evicts only when a
    send raises, which a BroadcastChannel post never does.
  - At the cap, evict the oldest client: post `evict` to it and end its VirtualConnection with a
    sentinel. The new client gets `accept`.
  - The shim posts `bye` on `pagehide` and on its accept timeout, and ignores a late `accept`.
    It fires `onclose` on its own `evict`, so the page's reconnect loop recovers.
  - Eviction is the backstop, since a `pagehide` post is best-effort.
- **C2-2 CONCEDE.**
  - D6 gets a four-case table (below). S1 records `css_limits_refit`, and AC-36 is keyed by case.
  - Delete "set once at open".
  - `dock.js` calls `parent.fit()` after every tier change inside the split.
- **C2-3 CONCEDE.**
  - `viewer3d.py` rebinds `plr_visualizer3d.server.PACKAGE_ROOT` to `tempfile.mkdtemp()` once,
    before the first viewer. `_register_meshes` reads the global at call time, and
    `_models_on_disk` is cached per root (`:104`).
  - It's a module global, not a class attribute: GATE X holds and no vendored bytes change. D11
    states it as the one deliberate runtime rebinding.
  - S4 records the resolved root and the walk time. AC-31 asserts the rebind, and that a `.glb`
    under the old root yields no `mesh`.
- **C2-4 PARTIAL.**
  - Conceded: PLR checks pending state (`volume_tracker.py:91,114-116`,
    `tip_tracker.py:91,104`).
  - New rule: if the resolved owner is not in the committed offending set, `resolve` returns
    `None` and the generic panel is shown.
  - AC-15: E13 (a retry after E9) and E14 (a pick-up after a failed pick-up) both return `None`.
    AC-17: E13 shows the generic panel.
  - Rebutted: pending-only callbacks correctly bump `rev`, because ordinary outputs draw
    `get_used_volume()`, which includes pending. D7 says this in one sentence.
- **C2-5 CONCEDE.**
  - (a) A new §3.3 row "TLL, owner is a tip (dispense)":
    - Heading: "The tip on channel {c} holds only {avail} µL."
    - Body: "The dispense asked for {req} µL. Nothing was dispensed."
    - Fix: "Dispense {avail} µL or less, or aspirate more first."
    - Step 4 compares per channel for a tip owner. E12: dispense 100 µL from an empty tip.
  - (b) `*96` errors are out of scope. Step 2 short-circuits to `None` when any ACTIONS frame is
    a `*96` op, and `head96` is removed from owner rule (b).
    - E-96 negative case: a real `aspirate96` TLL returns `None`.
    - The `*96` glossary names and ledger wrappers stay, for the ledger only.
- **C2-6 CONCEDE.**
  - Stamp types: `rev: <int|null>`, `resource: <name|null>`.
  - Ledger: `resource: null`, `rev: null`.
  - Error: `resource` = the drawn labware (plate, container or tip rack), or `null` for a
    channel owner or the generic panel; `rev: null`.
  - Outputs with `rev: null` are never marked "Changed since" (they're historical). Session
    marks apply to every kind.
  - Follow targets the first output with a non-null `resource`. Clicking figures inside a
    ledger or panel is unchanged.
  - AC-18/19 cases.
- **C2-7 PARTIAL.**
  - S3(b′) tests `formatters['text/html'].for_type` returning `(html, {"praxis": stamp})`, so
    the S3-B carrier is `metadata["text/html"]["praxis"]`. If that also fails, stop B7/B9 and
    escalate.
  - One reader, `stampOf(output) = output.metadata?.praxis ??
    output.metadata?.["text/html"]?.praxis`, is used by `stale.js`, `dock.js` and the harness,
    so AC-21 holds unconditionally.
  - The DOM-attribute option is rejected, since S2 may strip `data-*`.
- **C2-8 CONCEDE.**
  - Current session is per notebook panel and derived from outputs. Delete the
    `praxis:display-session` message.
  - `panelSession[P]` is the stamp session of the newest stamped output of a cell whose
    execution `chrome.js` observed in this page, after P's kernel last started (seen via
    `sessionContext`).
  - Earlier-session marks apply only where `stamp.session ≠ panelSession[P]`, and none are
    written until it is known.
  - The "add a kernel identity" option is rejected (not reachable from the worker).
- **C2-9 CONCEDE.**
  - A closed panel (tab closed or drawer hidden) holds no iframe, and announces are ignored
    while it's closed, except that the first announce auto-opens it.
  - On reopen, `dock.js` creates the iframe with no `src` and posts `query`; `src` comes only
    from the answering announce.
  - AC-38 `late_iframe` asserts, through a harness BroadcastChannel listener, that `query` was
    posted after reopen and that `src` was first set after the answering announce.
  - New AC-39(e): with `query` dropped, `late_iframe` must fail.
- **C2-10 CONCEDE.** Drop the comprehension case from AC-15 and B5. The step 2 wording keeps the
  `co_name` filter as defence.
- **C2-11 CONCEDE.** `stale` requires a non-null execution count and a snapshot. AC-5: an edited,
  never-run cell is `not-run`.
- **C2-12 CONCEDE.** Kinds:
  - page → kernel `bye {viewer, client}`
  - kernel → one page `evict {viewer, client}`
  - kernel → all `close {viewer, reason}`; the shell acts only on this one
  - AC-32 changes to "posts `bye` exactly once".

### D6 sizing cases (B-3)
| CSS limits | Layout sizing | 1280–1599 | ≥ 1600 |
|---|---|---|---|
| honoured | reachable | CSS | layout |
| ignored | reachable | layout | layout |
| honoured | unreachable | CSS | inline px min/max width + `parent.fit()`, asserted only if `css_limits_refit`, otherwise recorded-only |
| ignored | unreachable (S1-L) | every width key recorded-only | every width key recorded-only |

In every case the drawer and height keys stay asserted. AC-39(d) is skipped wherever the ≥1600 key
is recorded-only.

## Amendment list (one pass, in order)
- **B-1 (C2-12, C2-1)** Protocol kinds `bye`/`evict`/`close`; the eviction cap.
  - Touches: D11 table, inbound bounds and Kernel; §4 `viewer3d.py`/`socket.js`; C3, C4; §7
    threat row.
  - AC-31: a fifth `open` gets `accept`, the oldest gets `evict`, its `_handler` ends,
    `_clients` stays at 4, and `bye` ends a connection.
  - AC-32: `bye` on `close()`/`pagehide`/timeout; a late `accept` is ignored; `onclose` on
    `evict`.
  - AC-38: `many_reloads` (6 reloads).
- **B-2 (C2-9)** Closed panel semantics.
  - Touches: D11, §3.6, D12, §4 `dock.js`, C5, C7.
  - AC-38 `late_iframe` ordering; new AC-39(e).
- **B-3 (C2-2)** The D6 four-case table.
  - Touches: D1 S1 and §4 S1 (`css_limits_refit`), A1, AC-1; AC-36 keyed by case; AC-39(d)
    skip rule; §7 sizing row.
  - Delete "set once at open"; `parent.fit()` on tier change.
- **B-4 (C2-3)** `PACKAGE_ROOT` rebind.
  - Touches: D11 Python; D1 S4; §4 S4 and `viewer3d.py`; C1, C3.
  - AC-29: records root and time. AC-31: rebind and `.glb`-no-mesh.
- **B-5 (C2-7)** S3(b′) and the `metadata["text/html"]["praxis"]` carrier; escalate on failure.
  - Touches: D2 registration; `stampOf` in §4 `install.py`/`stale.js`/`dock.js`; B8, B9.
  - AC-3 (b′); AC-17 fallback case; AC-21 via `stampOf`.
- **B-6 (C2-6)** Stamps by kind.
  - Touches: D2 types and values; D7 (null rev is never rev-marked); D12 Follow skips null.
  - AC-18/19 cases.
- **B-7 (C2-8)** Per-panel session; the `display-session` message is deleted.
  - Touches: D7; §4 `stale.py`/`stale.js`; B7, B9; §7 `praxis_repl` row.
  - AC-18: remove the session-message bullets. AC-19: per-panel rules plus a two-panel case.
    AC-23 `earlier_session_marked`: add "re-running a drawing cell".
- **B-8 (C2-4)** Pending residue → `None`.
  - Touches: D8 steps 4 and 5 ("otherwise step 5"); D7 one sentence; §7 pending row; B5.
  - AC-15 E13 and E14; AC-17 E13 shows the generic panel.
- **B-9 (C2-5)** Tip-owner TLL row and E12; the `*96` short-circuit and E-96.
  - Touches: `head96` removed from rule (b); §3.3; §3.5 note; B5, B6.
  - AC-16 E12.
- **B-10 (C2-10)** Delete the comprehension case; step 2 wording.
- **B-11 (C2-11)** Stale requires a run: §3.1, §4 `chrome.js`, AC-5.
- **B-12** Revision 2 log section and frontmatter.

## Convergence (defender)
No BLOCKER is expected after B-1..B-12, though a MAJOR is possible in the residual risks. A targeted
round 3 re-check of B-1, B-3, B-7 and B-8 is recommended instead of a full round.

Residual risks:
- Whether Lumino re-reads size limits after `fit()` (left to S1).
- Delivery of `bye` at `pagehide` (eviction backstops it).
- Per-panel session timing: a restored, never-executed panel writes no marks, which is the safe
  default.
- Eviction thrash with more than 4 live pages (the multi-viewer non-goal).
