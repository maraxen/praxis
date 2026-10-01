---
title: 'Notebook display, next: several notebooks and viewers at once (kernel identity on praxis_viz3d)'
description: Spec-increment DRAFT for backlog #5660. Grounds the two known MVP limits (frozen deck after a kernel restart with several live-kernel notebooks; evict-oldest rotation) plus three more failure modes found while reproducing them; shows what identity the Pyodide kernel can and cannot give; compares seven options; recommends an optional `origin` field on `announce` (the Jupyter client session id of the request that called dock()), shell-side owner resolution through `kernel.clientId`, and tiered viewer arbitration. Design only; no product code.
status: draft
task_id: 260929_notebook-display-design
date: '261001'
backlog_id: 5660
---
# Several notebooks / viewers at once (backlog #5660)

Base: `feat/notebook-display-sprint-c-stacked` @ `60d053f2` (draft PR #198). Epic:
`260929_notebook-display-epic.md` (D11, T1-T27, I1-I6, AC-31/32/38/39). This draft edits
nothing; section 10 lists what the epic would need if the user accepts it.

## 1. Problem and current behaviour (verified, file:line)

### 1.1 The wire protocol today

BroadcastChannel `praxis_viz3d` (`viewer3d.py:62`), every message a JSON string. One channel
for the whole origin: every tab's shell, every tab's kernels and every viewer iframe hears
every message.

| kind | from -> to | fields | sent by | limits |
|---|---|---|---|---|
| `query` | shell -> kernels | none | `dock.js:924-931` (mount T1, reopen T4 only: I3) | none |
| `announce` | kernel -> all | `viewer, deck, session` | `viewer3d.py:323-330`: at `start()` (`:287`) and on every `query` (`:366-368`) | `deck`,`session` cut to 200 (`MAX_LABEL :79`); shell drops any message over 4096 chars unparsed and any id over 200 (`dock.js:98-99, 1169, 214-216`) |
| `open` | iframe page -> kernel | `viewer, client` | `socket.js:234` | `client` 1..200 (`viewer3d.py:76, 227`) |
| `accept` | kernel -> page | `viewer, client` | `:400` | page ignores one that arrives after 3 s (`socket.js:182-186`) |
| `msg` | both | `viewer, client, data` | `VirtualConnection.send` `:166-169`; `socket.js:213` | `data` must be a string; no size cap kernel-side |
| `bye` | page -> kernel | `viewer, client` | `socket.js:154-158` (close, pagehide, accept timeout) | once per socket |
| `evict` | kernel -> page | `viewer, client` | `:396` at the cap | the cap is PER VIEWER: `_virtual` lives on one `DockedViewer3D` (`:262, 392-397`), `MAX_CLIENTS = 4` (`:74`) |
| `close` | kernel -> all | `viewer, reason` | `stop()` `:313` | a restarted kernel posts nothing |

The shell acts on `announce` and `close` only (`dock.js:1179-1187`). The iframe shim acts on
`accept/msg/evict/close` and drops everything else, `announce` included (`socket.js:57-72`).
Nothing on the channel names a kernel, a notebook or a tab. `session` is the display session
id (`install.py:77-80`, `stale.new_session_id`): one per kernel PROCESS, and it is the stamp
session of drawn outputs, but it says nothing about which panel runs that process.

### 1.2 How dock.js decides which viewer belongs to which notebook

- One shell per browser tab, one panel per shell, one `current` viewer id (`dock.js:243-246`).
  Kernels live in the tab that started them: `PyodideKernel.initWorker` does `new Worker(...)`
  in the page (`pyodide-kernel-extension/static/327.fb6afea1c03ce19e.js`, class `f`). Other
  tabs hold their own kernels, but all tabs share the channel. So a tab's panel can show
  another tab's viewer, and does.
- `onAnnounce` (`dock.js:996-1014`): any announce, whoever sent it and whoever asked, goes
  through T2/T3/T6/T11/T18. In `open-connected` an announce for another id RETARGETS the
  iframe (T11, `:1012`). "Most recent announce wins" is the only arbitration.
- `recordViewerPanel` (`:984-994`): on EVERY announce (query answers included) it maps
  `viewerPanel[id]` to the one notebook panel with a running code cell, if exactly one.
- `ownsViewer` (`:1088-1100`): the viewer's kernel is `viewerPanel[current]`; with no entry,
  the only panel with a kernel; else unknown, and restarts never fire.
- `onActiveCellChanged` (`:682-687`) and `focus` (`:656-672`) act on the iframe in the panel
  whatever panel the cell belongs to.

### 1.3 Failure modes (reproduced where cheap)

Reproduced by a throwaway bun test against the real `dock.js` and `__tests__/fakes.js`
(2 notebooks, fake kernels). Command: `cd /tmp/claude-1000/spike && OMP_NUM_THREADS=2 bun
test spike_multi.test.js` (not committed: it is a spike, its assertions are re-stated as AC-44
to AC-46 below, tests-first).

| id | failure | reproduced? | evidence |
|---|---|---|---|
| FM1 | The item's limit 1. Viewer learned from a `query` answer (nothing executing), 2 live-kernel notebooks: restart of the owner's kernel leaves `open-connected` (frozen deck). | **yes** | `FM1` passes asserting `open-connected`; the existing test `dock.test.js` "with no viewerPanel entry and two panels with kernels, a restart changes nothing (the stated gap)" pins it as intended. |
| FM1b | NEW, worse. A query answer re-maps a known viewer to whichever panel happens to be running a cell. nb1 docks v1 (mapped nb1); the panel is closed; nb2 starts a long cell; reopen -> v1 answers -> `viewerPanel[v1] = nb2`. | **yes** | restart of nb2 (not v1's kernel): state `open-waiting` (a live deck wrongly dropped); restart of nb1 (v1's kernel): `open-connected` (frozen). |
| FM2 | NEW. Two live viewers: `announce(v1), announce(v2)` ends on v2, swapped order ends on v1. Any tab's `query` makes every OTHER tab's open panel hop to whichever viewer answered last (T11 is unconditional). | **yes** | srcs `[v1, v2]`, final `v2`; swapped final `v1`. |
| FM3 | NEW. Follow (and click-to-focus) from notebook 2 drives notebook 1's deck: a cell of nb2 activated while the panel shows v1 calls `focus(name)` in v1's page. | **yes** | `focus` calls into the v1 iframe: `[["focus","assay","top"]]`. |
| FM4 | The item's limit 2. >4 live pages on ONE viewer: evict-oldest rotates. Mechanism read, not run: an evicted page gets `onclose`; `transport.js:72-73` retries after `RECONNECT_MS = 1500`; `onopen` resets `lostAt` (`:66`), so the page never gives up; each retry evicts the next-oldest and costs a full scene+state resend. | **no** (needs concurrent real pages; K1b `many_reloads` is sequential) | Per VIEWER, not per origin (`:262`); reached today because every tab's panel converges on the last-announced viewer (FM2). |

### 1.4 What identity is reachable from inside the kernel

All read from the vendored bundles in `/tmp/praxis-nd-b/web-repl/dist` (the worktree has no
`dist`); nothing installed.

| identity | where it lives | reachable from Python? |
|---|---|---|
| kernel id | `initRemoteOptions` passes `kernelId: this.id` to the worker (`327.fb6a...js`); `initKernel` then only runs `await piplite.install(...)` and `import pyodide_kernel` (`PyodideRemoteKernel.initKernel`) | **No.** JS-side `this._options` only. |
| notebook path | `location: PathExt.dirname(path)` (`build/3102.28da48d.js`, Sessions) -> worker option -> used only for `os.chdir` when `mountDrive` | **No** as an identity: it is the DIRECTORY; two notebooks in one folder share it; `mountDrive` needs a service worker or cross-origin isolation. |
| `browsingContextId` | worker option, DriveFS only | No. |
| client session id | JupyterLab sets `session: this._clientId` on every request (`requestExecute`, `jlab_core.c0153ee.js`) and opens the socket with `channels?session_id=<clientId>`. JupyterLite deserializes the message unchanged, keeps `this._parent = e` (`BaseKernel.handleMessage`, `3102`), and routes replies by `e.header.session` (`d = e => ... this._clients.get(t)`). `PyodideRemoteKernel.setup` then does `this._kernel._parent_header = toPy(parent)`, and that `_kernel` is `pyodide_kernel.kernel_instance`, i.e. `get_ipython().kernel` (`__init__.py`; `praxis_boot.py:230` already uses `shell.kernel`). | **Yes, by reading:** `get_ipython().kernel._parent_header["header"]["session"]`. The Pyodide-side type after `toPy` is **unverified** (assumption A4). |
| display session | `announce.session` = `_process_session()` = the stamp session of drawn outputs | Yes, already shipped. Page side: `stale.js:576 panelSession(panel)`, set only after a stamped output is observed after the panel's kernel start. |
| page-side, no kernel help | `panel.sessionContext.session.kernel.id`, `.clientId` (public getter, `jlab_core ... get clientId()`), `isRunning(cell.model)`, `kernel.anyMessage` | n/a |

Consequence: the epic's "a kernel identity is not reachable from the worker" (D7, line 404;
revision note on C7-6) is true of the KERNEL ID and false of the thing that matters here: the
request's client session id is in every request the kernel sees, and it equals a value the
page can read off each notebook's kernel connection. The one gap is that it identifies a
CONNECTION, not a kernel (assumption A7).

### 1.5 Constraints that bound any change

- GATE X: `DockedViewer3D` overrides exactly `__init__`, `start`, `stop` (`viewer3d.py:11-16`;
  AC-31). New methods, new instance attributes and module functions are not overrides.
  `Viewer3D` defines no `announce`/`origin` (checked against `server.py` `def` list), so no
  collision.
- Existing tests pin the announce shape exactly: `test_viewer3d_docked.py:627-628, 755-756`,
  and "exactly one post" sequences (`:1036`, `:1114-1115`, `:1327-1329`). A new MESSAGE kind
  would break the sequence tests; a new announce field that is OMITTED when unknown breaks
  none (those tests run under CPython with no IPython).
- Already-open tabs keep their old dock.js and old kernel for their whole life (kernel and
  shell come from one dist), so mixed pairs only arise across tabs through the shared channel.
- The 4-client cap and evict-oldest are D11 decisions; this increment must not change them.

## 2. Assumptions

| # | assumption the plan leans on | tag | evidence / spike |
|---|---|---|---|
| A1 | Kernels are per tab (a worker owned by the tab that started the session) | verified | `327...js` `initWorker`; `3102` `Y.startNew` keeps `_kernels` in the page |
| A2 | The page can read a kernel connection's `clientId` | verified | `jlab_core` `get clientId(){return this._clientId}` |
| A3 | The `header.session` the kernel sees equals that `clientId` | verified (3 places) | `requestExecute` `session:this._clientId`; ws URL `session_id=`; reply routing by `e.header.session` |
| A4 | Under Pyodide, `get_ipython().kernel._parent_header` is a dict with `["header"]["session"]` a str | **unverified** | `setup()` does `toPy(parent)`; cannot run Pyodide here (no node, no browser). Spike S5 (section 7) before T2 |
| A5 | `_parent_header` is stable for the whole request that calls `dock()` | verified | every `handleMessage` runs under `i.runExclusive` (`3102`); `input_reply` bypasses it but sets no parent header |
| A6 | A kernel restart keeps the notebook's connection (same `clientId`) | unverified | the design does not depend on it: owned records are dropped on the restart signal |
| A7 | Closing and reopening a notebook tab gives a NEW `clientId` for the same live kernel | unverified (reasoned: `connectToKernel({...clientId: this._clientId})` mints per session connection) | design tolerates either: rebind by `kernel.id`, else the viewer becomes "unowned" and falls back |
| A8 | An old dock ignores extra announce fields | verified | `dock.js:1177-1182` reads `viewer` and `deck` only |
| A9 | The socket shim ignores `announce` | verified | `socket.js:57-72` returns null for any kind but accept/msg/evict/close |
| A10 | `recordViewerPanel` can be made first-sighting-only without breaking T1-T27 | **spiked** | patched copy of `web-repl/shell/display` in `/tmp/claude-1000/spike2/display`: `bun test dock.test.js` = 232 pass, 0 fail, both for `if (viewerPanel.has(id)) return` and for a `sightedViewers` Set (the second also covers a viewer first seen without a mapping). Baseline unpatched copy: 232 pass |
| A11 | The one-line fix removes FM1b | **spiked** | same spike file against the patched copy: non-owner restart `open-connected`, owner restart `open-waiting` |
| A12 | CPython tests run without IPython, so `origin` is None and old shapes hold | verified by reading the four exact-shape tests; `/tmp/praxis-nd-b/.venv/bin/python -m pytest web-repl/tests/test_viewer3d_docked.py -k "exact_shape or query_yields_one_announce"` = 2 passed | the worktree itself has no pytest env (a `uv run --no-sync` created an untracked, ignored `.venv`; removal was denied by the sandbox classifier) |
| A13 | `repl_smoke.py` can open a second notebook and restart a chosen one | **unverified** | helpers `_open_blank_notebook :1842`, `_open_existing_notebook :2566` exist, but `DisplayDriver`/`DockDriver` address one notebook by cell index; K3 needs new driver methods |
| A15 | A cell can start `dock()` as a background task so its announce lands after the cell finished | **unverified** | needed only to build K3's no-executing-cell case; fallback `loop.call_later` or a second cell awaiting a sleep |
| A14 | Python can capture `origin` before the first `await` in `dock()` | verified | `dock()` `:425-451` awaits `previous.stop()` BEFORE constructing; the capture must move above that await |

## 3. Options

| # | option | fixes | protocol change | GATE X | browser-gate cost |
|---|---|---|---|---|---|
| O1 | Heuristic repair only: record `viewerPanel` on the FIRST sighting of a viewer id | FM1b | none | untouched | none new; K1b unchanged |
| O2 | **Kernel origin**: optional `origin` on `announce` = the request's client session id, captured at construction; shell resolves owner by `kernel.clientId`, rebinds by `kernel.id` | FM1, FM1b, FM2 (with O-arbitration), FM3, most of FM4 | one optional field | untouched (kwarg on `__init__`, a module helper, an extra attribute) | new unit K3 (two notebooks, ~20 min), one new harness flag, one probe (S5) |
| O3 | Page-side only: match `announce.session` to `stale.panelSession(panel)` | partial FM1 (needs a stamped output observed in this page), FM3 | none | untouched | K3-like unit needed anyway |
| O4 | Jupyter comm: Python opens a comm to a target the shell registers on each panel's kernel connection; iopub reaches only that kernel's clients | FM1, FM1b, survives notebook reopen | a second transport (comm) beside the channel | untouched | K3 plus comm wiring; `registerCommTarget` per connection, re-register on kernel change; comm packages in Pyodide unverified |
| O5 | Handshake token: `query{nonce}` -> `announce{reply_to}` | FM2 for the querying tab only (addressing), not ownership | `query` gains a field, announce another | untouched | new K1b-level key; does not identify a kernel |
| O6 | Shell injects identity: `kernel.requestExecute({silent: true})` into each panel's kernel | strongest binding | none on the channel | untouched | runs shell-chosen code in the user's kernel: busy flicker, queues behind long cells, collides with D14 ("no eval") and chrome.js's execution observation |
| O7 | Liveness probe: re-`query` the current viewer, drop the panel if no answer in N s | FM1 incl. foreign viewers (other tab's restart) | none | untouched | breaks I3 (query only in T1/T4); a kernel busy in a long synchronous cell is indistinguishable from dead (the page's own 60 s give-up has the same false positive); slow against the T25 "within 5 s" |

Notes. O1 is independent and cheap, so it is a prerequisite of O2, not an alternative. O3
rejects itself on the FM1 scenario: a never-executed or just-reloaded panel has no
`panelSession`. O4 is the most robust identity (kernel-keyed, survives reopen and consoles)
but is a second transport with its own lifecycle for a problem one string already solves;
keep it as the escape hatch if S5 shows `header.session` is unreadable. O5 and O7 do not
supply identity; they are backstops (section 9, Q5).

## 4. Recommendation

**O1 now, O2 for the identity, plus shell-side tiered arbitration; defer O3-O7.**

- O2 is the smallest thing that supplies the missing fact: one optional string, no new kind
  (so every existing sequence test holds), no change to the cap or the three overrides.
- The shell consumes it with a strict precedence: a resolved owner decides; a viewer whose
  announce carries an `origin` that matches no panel is FOREIGN (another tab, a console) and
  never goes through the executing-cell heuristic (that heuristic is the source of FM1b);
  only an announce with NO `origin` (an old kernel) takes the legacy path unchanged, so T1-T27
  and the 232 existing dock tests keep their meaning byte for byte.
- It does not add a second panel, a viewer picker or automatic switching on tab change. The
  panel still shows one viewer; what changes is that the choice is deterministic and
  the restart/Follow logic is attached to the right notebook. Automatic switching is Q1.
- Residual, stated: a restart of a FOREIGN viewer's kernel (another tab) is unobservable; a
  notebook reopened onto a live kernel is rebound by `kernel.id` only if the viewer was bound
  while the old panel was open.

## 5. Proposed decisions

**N5660-1. `announce` gains an optional `origin`.** Shape: `{kind, viewer, deck, session[,
origin]}`. `origin` is a non-empty string of at most 200 characters (`MAX_LABEL`), the
Jupyter client session id of the request that constructed the viewer. It is omitted, not
null, when unknown. Reason: omission keeps every existing exact-shape and one-post test true
without edits, and old shells read only `viewer` and `deck` (A8). The module docstring table
and D11's protocol table gain the field. No new `kind`.

**N5660-2. No protocol version field, no negotiation.** Compatibility is by tolerance in both
directions (table). Reason: a `proto` field would be present on every announce and break the
exact-shape tests for no behaviour the receivers do not already get from `origin` being
present or absent. Revisit only if a field ever changes meaning.

| shell | kernel | result |
|---|---|---|
| old | new | extra field ignored (`dock.js:1177-1182`); behaviour as today |
| new | old | no `origin`: legacy path (`viewerPanel` heuristic, T0'), as today |
| new | new, `dock()` outside a request (a timer, startup) | no `origin`: legacy path |
| new | new, request context | owner resolved or FOREIGN; new rules |
| iframe shim | any | announce dropped (A9) |

**N5660-3. The kernel captures `origin` once, at construction, before any `await`.**
`_kernel_origin()` is a module function: it looks `IPython` up in `sys.modules` (never
imports it, like `_display_session`), reads `get_ipython().kernel._parent_header["header"]
["session"]` (mapping access, then attribute access for a proxy), and returns None on any
absence, non-string, empty value or exception; over 200 characters it is cut. `DockedViewer3D
.__init__` takes `origin: Optional[str] = None` beside `session` and stores
`self.origin`; `announce()` adds the field when it is set; `dock()` calls `_kernel_origin()`
FIRST, before `await previous.stop()` (A14), and passes it unless the caller gave one.
Reason: a `query` is answered whenever it arrives, in whatever request context the kernel is
then in (a completion request from a console, say); reading live would stamp the wrong
connection. GATE X holds: still `{__init__, start, stop}`; the AC-31 state snapshot is
unchanged (an instance attribute and a module function are not entries of `vars(Viewer3D)`).

**N5660-4. The shell keeps a viewer table and resolves owners lazily.** `viewers: Map<id,
{deck, origin, kernelId}>`, bounded at 64 entries (oldest dropped, never `current`). On an
announce with a valid `origin` (a string, 1..200): owner = the tracked panel whose
`sessionContext.session.kernel.clientId === origin`; on a match, remember that panel's
`kernel.id` as `kernelId`. If no panel matches, try a panel whose `kernel.id === kernelId`
(a reopened notebook, A7). Else the owner is null (FOREIGN). Entries die on `close`, and on
the restart signals of their owner. A disposed owner panel nulls the owner but keeps
`kernelId`. Resolution runs again on `scanPanels` so a panel opened after the announce can
claim it.

**N5660-5 (= O1, "T0"). The legacy heuristic records a viewer id once.** `recordViewerPanel`
returns at once for an id it has seen (a `sightedViewers` Set, bounded like N5660-4). It is
also the only mapping used when an announce has no `origin`. Reason: FM1b; spiked (A10, A11).
It is a pure shell change with no protocol effect and ships first.

**N5660-6. Restart rule with owners.** For a panel P's restart/dead/`kernelChanged`: every
table record owned by P is dropped; if `current` was one of them, T25/T26 (the existing
`toWaiting`). A restart of any other panel does nothing. A foreign `current` is never
touched by a restart signal. If the announce carried no `origin`, `ownsViewer` is the legacy
function, unchanged. Reason: FM1, FM1b become exact instead of heuristic; the "frozen deck
until reopened" case remains only for foreign viewers.

**N5660-7. Arbitration is tiered; same tier never flaps.** Tier of a viewer at the instant of
an announce: **A** owner is the active notebook panel (N5660-8) or has a running code cell;
**B** owner is another tracked panel; **C** no owner (foreign, console, no `origin`). In
`open-connected`, an announce for id != `current` retargets (T11) iff its tier is strictly
better than `current`'s tier re-evaluated now, or both are C (legacy last-wins, exactly
today's T11). In `closed`-first, `open-waiting` and `open-lost` the first announce is taken as
today (T2, T6, T18) and any better-tier announce after it retargets. So after a `query`
answered by several viewers the panel ends on the active notebook's viewer in every arrival
order, with at most one extra `src` write; and a foreign `query` answer never moves an
`open-connected` panel that shows an owned viewer. `query` posting (I3) and the `src`-write
sites (I2: still T2/T6/T11/T18) are unchanged.

**N5660-8. "Active notebook panel"** = the most recent `shell.currentWidget` that is a
notebook panel (updated on `shell.currentChanged`), so clicking into the deck panel itself
does not make the notebook inactive.

**N5660-9. Follow and click-to-focus are scoped to the owner.** `onActiveCellChanged(panel,
cell)` acts only if the owner of `current` is `panel`, or the owner of `current` is unknown
(today's behaviour, for old kernels and foreign viewers). `interact.js` passes the clicked
notebook's panel node to `dock.focus(name, {node})` (optional second argument, so the
existing one-argument calls and tests are untouched); the same rule applies (Q3).

**N5660-10. No automatic switch on tab change in this increment.** The panel does not
retarget when the user switches notebooks. The user gets notebook B's deck by running
`dock()` in B, or by closing and reopening the panel with B active (N5660-7 picks B's
viewer). Reason: each retarget reloads the iframe (T11), losing camera and re-sending the
scene; and it needs a user-visible control (CSS is out of scope here). Q1.

**N5660-11. The cap is unchanged: 4 clients per viewer, evict-oldest, no new kind.** With
N5660-7 a tab shows its own notebook's viewer, so one viewer has about one panel client per
tab that shows it; rotation needs five panels on the same viewer. Documented as accepted
(D11); not mitigated, because the only available mitigation is to edit the vendored page's
reconnect loop (forbidden by GATE X part 3) or to make the shim give up after `evict`, which
would break the orphan-recovery D11 relies on.

**N5660-12. `snapshot()` gains `owners`** (viewer id -> panel id or null, read-only). It is a
controller field, not a test switch (AC-39(c) greps only `__praxis_test|data-praxis-test`).
Existing `snapshot()` assertions use `toMatchObject` or single fields.

**N5660-13. Harness.** A new unit K3 in `--dock-check`; a harness-only negative flag
`--neg strip-origin`; probe S5 before any product code. K1a/K1b/K2 keep their keys and order.

## 6. Acceptance criteria

Numbering continues the epic (AC-43...) and is provisional. Every key has a positive control
(the key passes on the shipping code) and a negative control (a deliberately broken variant
the key must reject). "Mutant" = the existing dock.test.js pattern: patch `dock.js` source,
each anchor must match exactly once, and the probe scenario must FAIL.

- **AC-43 (kernel origin)** [PY: `web-repl/tests/test_viewer3d_docked.py`, new class
  `TestOrigin`; run `/tmp/praxis-nd-b/.venv/bin/python -m pytest <file> -q -k Origin`]
  - (a) `DockedViewer3D(deck, origin="C-1", session="s")`: the announce equals
    `{"kind","viewer","deck","session","origin":"C-1"}` exactly. Without `origin` the shape is
    the old four keys (the four existing exact-shape tests, unedited, are the positive control
    of omission).
  - (b) A query answered after the provider changed still carries the constructor-time value.
    Negative: a mutant that reads the provider at announce time fails (b).
  - (c) `_kernel_origin()` table with a faked `IPython` in `sys.modules`: dict parent ->
    string; None parent, missing `header`, missing/empty/non-str `session`,
    `get_ipython() -> None`, `get_ipython` raising -> None; 201 chars -> 200; an attribute-style
    proxy parent works; `IPython` absent from `sys.modules` -> None and `IPython` is NOT
    imported by the call.
  - (d) `dock()` captures before it awaits `previous.stop()` (the fake previous viewer's
    `stop()` swaps the faked parent header).
  - (e) An announce with `origin`, a 200-char deck and a 200-char session stays under 4096.
  - (f) GATE X: the AC-31 override-set and state-snapshot tests pass unedited;
    `MAX_CLIENTS == 4`; the cap/evict tests (`:847-925`) pass unedited.
- **AC-44 (owner resolution and restart)** [BUN: new `web-repl/shell/display/dock_owner.test.js`,
  `bun test web-repl/shell/display/dock_owner.test.js`; fakes get `kernel.clientId` set by the
  test, `fakes.js` unedited]
  - (a) Two notebooks, announce `origin` = nb2's `clientId`, no cell running: restart of nb2
    -> `open-waiting` (FM1 inverted); restart of nb1 -> unchanged; and the mirror image.
  - (b) FM1b inverted: v1 owned by nb1, panel closed, nb2 runs a cell, reopen, v1 answers:
    restart of nb2 leaves the deck; restart of nb1 drops it.
  - (c) Rebind: owner panel disposed, a new panel object with the same `kernel.id` and a new
    `clientId` appears; restart of it drops the deck.
  - (d) `kernelChanged` to another kernel on the owner drops it; a dead non-owner does not.
  - (e) `origin` of wrong type, empty, 201 chars, array: treated as absent (legacy path).
  - (f) `origin` present but unmatched with one notebook running a cell: the viewer is FOREIGN,
    the running notebook is NOT recorded as its owner.
  - (g) Legacy: no `origin` -> every existing behaviour (the full existing `dock.test.js`,
    232 tests, unedited and green; `git diff 60d053f2 -- web-repl/shell/display/dock.test.js`
    empty).
  - (h) N5660-5: a viewer seen once with no mapping is not mapped by a later query answer.
  - Mutants that must fail: `ignore-origin` (always legacy) fails a, b, c; `first-panel-owns`
    fails a, b; `no-drop-on-restart` fails a, d; `record-every-announce` (T0' reverted) fails
    h and b-legacy.
- **AC-45 (arbitration)** [BUN, same file]
  - (a) Permutation: viewers v1 (nb1), v2 (nb2), foreign v3; from `open-waiting`, every
    arrival order of {v1, v2, v3} ends on the active notebook's viewer (active nb1 -> v1,
    active nb2 -> v2); with active = a notebook that owns none, ends on a B-tier viewer.
    `src` writes <= 2; no `query` posted (I3); exactly one iframe (I1).
  - (b) An `open-connected` panel on an owned viewer ignores a foreign announce (the cross-tab
    `query` answer) and a same-tier other-owner announce; it retargets to a better tier; it
    retargets to a viewer whose owner is running a cell.
  - (c) Both-C announces behave as T11 today (covered by the existing T11/T27 tests).
  - Mutant `last-wins` (T11 unconditional) fails a, b (this is FM2).
- **AC-46 (scoped Follow and click)** [BUN, same file]
  - (a) Panel on v1 (owner nb1): an activated stamped cell in nb2 -> zero `focus` calls
    (FM3 inverted); in nb1 -> one. Owner unknown -> as today. (b) Click on a resource in
    nb2's output with the panel on nb1's viewer -> `focus` returns false, no call; the same
    click in nb1's output -> true (if Q3 is yes). Mutant `follow-ungated` fails a.
- **AC-47 (compatibility)** [BUN + PY]
  - (a) `dock_owner.test.js`: an announce carrying unknown extra fields plus a valid `origin`
    is accepted through T2, T6 and T11 with the same DOM effects as one without. (b) The
    socket shim test file passes unedited (A9). (c) Section 5's matrix rows "old shell" and
    "no origin" are the PY AC-43(a) omission control and the AC-44(g) unedited legacy suite.
- **AC-48 (real browser, unit K3)** [DOCK `--dock-check --scenario K3`, run by the
  orchestrator; Chromium cannot start in the author's sandbox]. Two notebooks in one page
  (`dock_check.ipynb` and a second fixture notebook), each starts docking as a
  background task (`task = asyncio.ensure_future(dock(deck))`, read back in a later cell) so the
  announce lands with NO executing cell (the case the legacy heuristic cannot map; unverified
  harness assumption A15). Keys, in execution order:

  | key | statement | positive evidence | negative control |
  |---|---|---|---|
  | `origin_matches_client` | each notebook's announce `origin` (read from the harness channel log) equals that panel's `kernel.clientId`, and the two differ | equality x2 and inequality | `--neg strip-origin` (parent-page script removes `origin` from announces before the shell hears them): key false |
  | `query_prefers_active` | with both viewers live: close the panel, activate nb1, toggle -> v1; again with nb2 -> v2 | final iframe `viewer=` equals the active notebook's | dist mutant `last-wins`: key false |
  | `follow_scoped` | panel on v2 (nb2): activating a stamped cell in nb1 leaves the camera; in nb2 moves it | camera delta 0 / > eps | dist mutant `follow-ungated` |
  | `query_not_misowned` | reopen the panel while nb1 runs `await asyncio.sleep(...)`; v2 (nb2's) answers; restart nb1 -> panel still `open-connected` on v2 | iframe present, `resources()` non-empty | dist mutant `owner-by-running-cell` (owner = the panel with a running cell, for every announce) |
  | `restart_other_keeps_deck` | restart nb1 while the panel shows v2 | panel keeps v2 | dist mutant `any-restart-fires` |
  | `restart_owner_drops_deck` | restart nb2 -> within 5 s the no-viewer text, no iframe, no `close` posted | as K1b `restart_placeholder` | `--neg strip-origin`: frozen deck, key false |

  Budget proposal 20 min (two kernel boots plus two restarts). Dist mutants are string
  replacements on a copy of the built dist (each anchor must match once), run only through the
  pre-registered sensitivity driver (D17), unit-scoped, exit codes and bathos run ids go in
  the PR description, as AC-39. The unit's pre-registration sidecar is committed before the
  first real run.
- **AC-49 (probe S5, gates T2)** [DOCK, tracked script + `.bth.toml`, committed before the
  run]: in a real page with two notebooks, `get_ipython().kernel._parent_header["header"]
  ["session"]` is a str in each, equals that notebook's `sessionContext.session.kernel
  .clientId`, and the two differ. Outcomes: `pass`; `header_unreadable` (A4 false: try the
  attribute path, else O4); `mismatch` (A3 false in this build: O3 or O4). The design is
  correct under each: the shell's no-`origin` path is today's.
- **AC-50 (no regressions)** `dock.test.js` 232 pass unedited; `viz3d_socket.test.js`,
  `interact.test.js`, `index.test.js` unedited and green; K1a/K1b keys unchanged; R19/R21
  greps and `test_contract_covers_imports.py` as AC-41; the AC-31 state snapshot unchanged.

## 7. Task decomposition (tests first)

Each task is RED -> GREEN; a "RED" commit proves the new tests fail on the base.

| task | files | ~LOC | depends | gate |
|---|---|---|---|---|
| **T0** O1 | `web-repl/shell/display/dock_owner.test.js` (new, AC-44 h + FM1b legacy case); `dock.js` (`sightedViewers`, +5) | test 60, code 5 | none | bun only (not browser-gated; K1b unchanged) |
| **S5** probe | `scripts/spikes/261001_nd_5660_origin_probe.py` + `.bth.toml` (pre-registered); reuses the `DisplayDriver` machinery | 150 | none | **real browser** (orchestrator); gates T2 |
| **T1** RED | `test_viewer3d_docked.py` `TestOrigin` (AC-43) | 170 | none | pytest |
| **T2** GREEN | `viewer3d.py` (`_kernel_origin`, `origin` kwarg, `announce`, `dock()` order, docstring table) | 45 | T1, S5 pass | pytest |
| **T3** RED | `dock_owner.test.js` (AC-44, AC-45, AC-46, AC-47a, mutants) | 380 | T0 | bun |
| **T4** GREEN | `dock.js` (table, owner resolution, tiers, restart rule, active-panel tracking, Follow scope, `snapshot().owners`) | 140 | T3 | bun; `dock.test.js` unedited |
| **T5** | `interact.js` (+8: pass `{node}`), `interact.test.js` addition or a case in `dock_owner.test.js` | 40 | T4, Q3 | bun |
| **T6** harness | `repl_smoke.py`: `DOCK_UNITS` K3 + `K3_ORDER`, a two-notebook driver (open second notebook, cell/restart by notebook), `--neg strip-origin` (choices extended), pure key functions; `test_repl_smoke_resume.py` cases (positive/negative control per key function on synthetic evidence); `test_repl_workflow_scenarios.py` + `.github/workflows/repl.yml` K3 step (touches `.github/`, so a separate reviewed commit) | 450 | T2, T4 | pytest locally; **real browser** for the unit |
| **T7** sensitivity | `scripts/spikes/261001_nd_sensitivity_5660.py` + sidecar (D17): dist mutants and the `strip-origin` run | 120 | T6 | **real browser**, orchestrator |
| **T8** docs | epic spec revision note (section 10); `viewer3d.py` module docstring; no INDEX.md edit | doc | all | `praxia docs check` |

Parallelisable: T0, S5, T1. T2 waits for S5. Real-browser gated: S5, T6 (the unit), T7.

## 8. Risks

| risk | likelihood / impact | mitigation |
|---|---|---|
| A4 false: `_parent_header` is not a plain dict under Pyodide | medium / blocks O2 | S5 first; helper tries mapping then attribute; fallback O4 (comm) or O3 |
| A7 true: a reopened notebook has a new `clientId`, rebind by `kernel.id` only works if the viewer was bound while the old panel was open | medium / a dock opened before a tab close+reopen stays unowned | falls back to FOREIGN (no regression vs today); user re-runs `dock()`; stated in the user docs |
| A viewer started from a console attached to a notebook's kernel has the console's `clientId` | low / unowned | falls back to FOREIGN (stated in the user docs) |
| Foreign viewer's kernel restarts (other tab): frozen deck | medium / cosmetic | accepted gap, as today; O7 as later backstop (Q5) |
| Tier rules surprise a user who runs `dock()` in a background notebook | low | a running cell is tier A, so an explicit `dock()` always wins |
| The `origin` string is visible to every listener | none new | origin is the boundary (D11); the value is a random per-connection uuid, usable only to claim ownership in a shell it already shares the origin with |
| Real-browser K3 flakiness and cost (second kernel boot) | medium / CI minutes | unit-scoped, own timeout and stamp (AC-42 resume), budget stated; mutants run on demand, not in CI |
| `dock()` reordering breaks `test_dock_awaits_the_old_viewers_stop_before_constructing_the_next` (`:1193`) | low | only the `_kernel_origin()` read moves above the await; construction stays after it; `TestDock` (`:1088-1276`) is run before and after |
| Epic text says "no kernel identity" in three places | low | section 10 lists them; a revision note, not a silent edit |

## 9. Open questions for the user

1. **Q1 (auto-switch).** Should the deck panel switch to the owner's viewer when you switch
   notebook tabs? Costs one iframe reload per switch and needs a visible control. *Default:
   no* (N5660-10); you get the right deck by running `dock()` or reopening the panel.
2. **Q2 (foreign viewers).** Should a tab show a viewer whose kernel lives in ANOTHER tab? It
   works today. *Default: yes, lowest priority* (tier C), never displacing an owned one.
3. **Q3 (click scoping).** May `interact.js` pass the clicked notebook to `dock.focus` so a
   click in notebook 2 does not drive notebook 1's deck? *Default: yes*, optional second
   argument, tiny.
4. **Q4 (CI cost).** Run K3 (about 20 min, two kernel boots) in the REPL workflow as its own
   step, or only locally/on demand? *Default: in CI*, own `timeout-minutes`, own stamp.
5. **Q5 (liveness backstop).** Add a re-`query` liveness probe for foreign viewers
   (breaks I3, slow, false-positive on long synchronous cells)? *Default: no.*
6. **Q6 (cap).** Accept the evict-oldest rotation at five-plus panels on one viewer as a
   documented limit, rather than touching the shim? *Default: yes* (N5660-11).
7. **Q7 (O4).** If S5 fails, may the increment switch to the comm-based identity (a second
   transport) rather than stop? *Default: stop and ask*, because it is a larger design.
8. **Q8 (epic edit).** May the epic's D11 / section 2 / section 7 text be amended by a
   revision note once this is accepted, including the D7 line "a kernel identity is not
   reachable from the worker"? *Default: yes, as a revision note.*

## 10. What this changes in the epic spec (not edited by this draft)

| epic location | change |
|---|---|
| D11 protocol table, `announce` row (`:921`) and the "Protocol on praxis_viz3d" paragraph | add optional `origin` and its omission rule (N5660-1); `viewer3d.py` module docstring table likewise |
| D11 "How the page learns" / `viewerPanel` paragraph (`:806-833`) | the viewer's kernel is resolved by `origin` first; the executing-panel heuristic remains for announces without `origin`, first sighting only (N5660-5, -4) |
| D11 state table: T11 (`:875`) guard by tier; T13, T25, T26 "the viewer's kernel" definition; T3 keeps recording (now sightings); invariants I2 and I3 unchanged in letter | N5660-6, -7 |
| D11 Kernel paragraph | `__init__` kwarg `origin`, `dock()` captures first; GATE X text unchanged (still three overrides) |
| D7 line 404 and Revision 7 C7-6 note (`:4057`) | "not reachable from the worker" is true of the kernel id only; the client session id is reachable (section 1.4) |
| Section 2 non-goal "Several live viewers or notebooks at once" (`:1657-1664`) | narrowed: still one panel and one viewer shown; the restart gap and cap rotation text amended; owner-aware restart, arbitration and scoped Follow become goals |
| Section 7 risks rows (`:3514`, `:3531`) | the "unknown kernel" residual narrows to foreign viewers |
| Section 4 file table | `viewer3d.py`, `dock.js`, `interact.js`, `repl_smoke.py`, new `dock_owner.test.js`, new S5/N-5660 scripts |
| AC-31 (announce shape), AC-38 (unchanged), AC-39 (new negatives via the 5660 sensitivity run), AC-41 (greps), new AC-43..AC-50, Sprint C task list | additions only; no existing AC loosened |
| Open questions section 8 | Q1-Q8 above |
