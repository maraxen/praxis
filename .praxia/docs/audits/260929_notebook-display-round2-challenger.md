---
title: Notebook display epic, round 2 challenger
description: Round 2 challenge of Revision 1 (b80848e9). All 29 round 1 findings CLOSED. 12 new findings (2 BLOCKER, 7 MAJOR, 3 MINOR). Verdict REVISE.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 2 challenger

Reviewer: praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r2`. Verdict: **REVISE**.

**Closure:** C1-1..C1-29 all CLOSED as ruled (C1-27's rebuttal accepted). Knock-on effects are
tracked below: C1-2 → C2-1 and C2-9, C1-4 → C2-4, C1-8 → C2-2, C1-11 → C2-8, C1-20 → C2-10,
C1-22 → C2-3.

**Orchestrator checks on `origin/main` (260929; the challenger had no shell):**
- `web-repl/bootstrap/transport.py:210,247`: `fetch_sources(..., dest_root=".")` writes loose
  sources relative to the kernel's working directory.
- `server.py:98`: `PACKAGE_ROOT = dirname(dirname(abspath(__file__)))`.
- `.github/workflows/repl.yml:64`: `python-version: "3.12"`.
- C2-3's premise stands.

## New findings

### C2-1 [BLOCKER] The 4-client cap has no way to drop dead clients, so the panel stops working after routine reloads
- **Where:** D11 inbound bounds, protocol, `socket.js` (C4), AC-31/32/38.
- **Claim:**
  - The iframe reloads on every announce, drawer move, manual reload and 60 s give-up.
  - A client ends only on a page `close`, and the page transport never closes
    (`static/transport.js:56-93`, reconnect only).
  - Nothing posts `close` on `pagehide` or on the shim's 3 s accept timeout.
  - Orphans stay in `_clients` forever, because a BroadcastChannel post never raises
    (`server.py:357-361`).
  - A long synchronous cell delays `accept` past 3 s, so the page retries and a second orphan
    appears.
  - The 5th connection gets no accept and the panel stays dead. No gate reloads more than about
    3 times, so this passes on a broken build.
- **Required change:**
  - At cap, evict the oldest client; don't refuse the newest.
  - The shim posts `close` on `pagehide` and on its accept timeout.
  - AC-31: the fifth evicts the oldest.
  - AC-38 `many_reloads`: 6 sequential reloads, each repopulating `resources()`.
  - AC-32: `pagehide` and accept timeout each post `close`.
  - The cap ruling stands; only the overflow policy changes.

### C2-2 [BLOCKER] Two S1 sizing branches have no mechanism for widths AC-36 still asserts
- **Where:** D1 S1, D6, AC-36, AC-39(d), C5.
- **Claim:** The four combinations of (CSS honoured, layout sizing reachable) aren't all covered.
  - CSS-only: nothing sets the ≥1600 width (D6 routes it only through layout sizing, and the CSS
    limits exist only in the 1280–1599 query), so a stock 50/50 split fails a correct build.
  - S1-L: "set once at open" has no mechanism (`app.shell.add` takes no size), yet AC-36 still
    asserts `[420,480]` and the ≥1600 formula. AC-39(d) is skipped while the check it proves
    sensitive stays asserted.
- **Required change:**
  - Give each of the four cases a mechanism or recorded-only status for every AC-36 width key.
  - CSS-only: name a CSS mechanism above 1600 (e.g. a `calc()` min/max width with the file
    browser closed), or make that key recorded-only.
  - S1-L: every width key recorded-only (drawer and height keys stay asserted); drop "set once
    at open" or name its mechanism.

### C2-3 [MAJOR] `PACKAGE_ROOT` is the kernel's `/drive`, so the model walk scans the user's files and the "meshes unsupported" premise fails
- **Where:** D11 Python, "Meshes are unsupported", S4, AC-29, AC-31.
- **Claim:**
  - Loose sources land relative to the kernel's working directory, the contents drive `/drive`
    (`build_repl.py:351-353`, `files/praxis_boot.py:17-19`).
  - So `_models_on_disk(PACKAGE_ROOT)` (`server.py:104-129`, first called at `:224` via `:417`)
    runs `os.walk` over the whole drive.
  - A user `.glb` named after a PLR model becomes a `mesh` whose URL nothing serves.
  - AC-31 checks the fixture in CPython only. S4 has no decision rule if the walk is slow.
- **Required change:**
  - `viewer3d.py` rebinds `plr_visualizer3d.server.PACKAGE_ROOT` to an empty directory it owns.
    That's a module global, not an override, and no vendored bytes change.
  - AC-31 asserts the rebind, plus a `.glb` under the old root that yields no `mesh`.
  - S4 records the resolved root.

### C2-4 [MAJOR] Committed-only numbers contradict the raise after an earlier failed op left pending state
- **Where:** D8 step 4, panel drawing, §3.3, AC-15/16.
- **Claim:**
  - PLR checks pending state: `volume_tracker.py:91` (`get_used_volume()` returns
    `pending_volume`) and `tip_tracker.py:55,91` (`_pending_tip`). Failures leave earlier
    channels pending (`liquid_handler.py:533-538`, `:1031-1035`).
  - Worked case: after E9 the trough is at 100 committed and 10 pending. A retry of 10 µL × 8
    raises TLL, yet nothing offends under step 4, and the panel reads "holds 100 µL; asked
    80 µL", which describes no fault.
  - The same happens for HasTip after a failed pick-up (`:538`, `commit=False`).
  - Pending `remove_liquid` also fires the callback (`volume_tracker.py:98-99`), so D7 marks
    outputs "Changed since" while committed state is unchanged.
- **Required change:**
  - Define the panel when committed shows no shortfall but pending differs, e.g. a "tracker
    still holds changes from an earlier failed step" template with both numbers labelled.
    Or fall back to the generic panel.
  - AC-15/16 cases: a retry after E9, and a pick-up after a failed pick-up.
  - State D7's behaviour for callbacks that change pending state only.

### C2-5 [MAJOR] Context resolution misses real raise sites at the pin
- **Where:** D8 steps 2–4, owner rule (c), §3.3, AC-15.
- **Claim:**
  - (a) Dispense raises TLL on the tip (`liquid_handler.py:1235`,
    `op.tip.tracker.remove_liquid`). This is the most common beginner error, and there is no
    tip-owner TLL template or case.
  - (b) `aspirate96`/`dispense96` bind `containers` and a scalar `volume` (`:1695-1698`,
    `:1775-1816`), with no `resources`/`tip_spots`/`vols`/`use_channels`, so step 2 and step 4
    are undefined for them.
- **Required change:**
  - Add the tip-owner TLL template and E12 (dispense from an empty tip).
  - Either define the 96-head locals mapping with a case, or declare `*96` errors out of scope
    (generic panel when the ACTIONS frame is a `*96` op) with a negative case.

### C2-6 [MAJOR] Ledger and error outputs have no defined `resource`/`rev`, so staleness and Follow on them are undefined
- **Where:** D2 metadata kinds, D7, D12 Follow.
- **Required change:**
  - State the stamp for each kind (e.g. ledger `resource` = null with no rev, error
    `resource` = the owner).
  - State whether they are ever marked stale (recommend never: they're historical).
  - State the Follow target.
  - Add AC-18/19 cases.

### C2-7 [MAJOR] Under S3-B the stamp has no named carrier, and AC-21 cannot pass
- **Where:** D1 S3-B, §3.4, D7, D12, AC-21, AC-24.
- **Claim:**
  - S3-B puts the stamp in unnamed DOM `data-praxis-*` attributes, while `stale.js` and Follow
    read stamps model-first.
  - AC-21 requires `metadata.praxis` unconditionally.
  - The premise is doubtful anyway: per-type formatters accept a `(data, metadata)` return.
- **Required change:** Either:
  - S3 also tests `formatters['text/html'].for_type` returning `(html, md)`, and the metadata
    is kept under S3-B;
  - or name the DOM stamp attributes, have `stale.js` and `dock.js` read them under S3-B, and
    make AC-21 and AC-9 conditional on the branch.

### C2-8 [MAJOR] One global "current session" marks a second notebook's live outputs as "Drawn in an earlier session"
- **Where:** D7 session announcement and marking, AC-19/23.
- **Claim:**
  - Two notebooks with two kernels are routine in one tab (`welcome.ipynb` beside the user's
    notebook), and BroadcastChannel reaches other tabs too.
  - Booting B marks all of A's live outputs as from an earlier session.
- **Required change:**
  - Scope "current session" per notebook panel, e.g. via `sessionContext`: the newest stamped
    session in that panel since its kernel last started. Or add a kernel identity to the
    message.
  - AC-19: two panels with two sessions, neither marked.

### C2-9 [MAJOR] `late_iframe` passes even when the `query` path is broken
- **Claim:**
  - The shell sets `src` on every announce, even while the panel is closed.
  - Reattaching loads the already-updated `src`, so reopening connects without
    `query` → `announce`.
- **Required change:**
  - Either don't update `src` while the panel is closed (`query` on reopen is then the only
    path), or have AC-38 assert that a `query` was posted and that its announce set the `src`.
  - Plus a negative run with `query` suppressed that must fail.

### C2-10 [MINOR] AC-15's comprehension-frame case cannot be built on Python 3.12 (PEP 709 inlines list comprehensions; no genexpr raise at the pin)
- Required change: make it a synthetic-frame unit case, or drop it and keep the filter as
  defence only.

### C2-11 [MINOR] "stale" outranks "not-run", so an edited, never-run cell shows dashed
- Required change: stale requires a non-null execution count and a snapshot. Add an AC-5 case.

### C2-12 [MINOR] Page→kernel `close {viewer, client}` and kernel→all `close {viewer, reason}` share a kind
- Required change: the shell acts only on a `close` that has `reason` and no `client`, or rename
  one of the two kinds.

## Summary
BLOCKER 2, MAJOR 7, MINOR 3. Every fix is local spec text plus AC cases, and none reopens a
ruling. The challenger judges the spec converged once these are applied as stated, and
suggests a targeted re-check of C2-1, C2-2 and C2-4 instead of a full round 3.
