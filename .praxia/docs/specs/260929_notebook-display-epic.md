---
title: 'Notebook display epic: rich PLR outputs, quieter chrome, Visualizer3D deck panel (web-repl)'
description: Epic spec for the web-REPL notebook display. Three sprints (A spikes + chrome, B praxis.display reprs/ledger/errors/staleness, C Visualizer3D deck panel). Four spikes (S1-S4) run first, and every downstream decision states its behaviour under each spike outcome.
status: draft
task_id: 260929_notebook-display-design
date: '260929'
adversarial_review: 'none yet'
---
# Notebook display epic (web-repl)

## Overview

The Praxis web REPL (JupyterLite `lab/` entry, Pyodide kernel) shows PyLabRobot objects as
`Plate(name=source, size_x=127.76, ...)`, and the deck is visible only in a separate window.
This epic makes three surfaces work as one system:

- **Rich cell outputs.** Plates, tip racks, containers and decks render as to-scale drawings
  with a name line and one summary sentence. A `RunLedger` renders a run as a table of liquid
  moves. Four PLR errors render as a plain statement of what went wrong and where.
- **Notebook chrome.** A status rail replaces the `[ ]:` prompts, outputs belong visibly to
  their cell, and the Light theme gets the design's steel/sheet palette.
- **Deck panel.** PLR main's `Visualizer3D` (PyLabRobot #1378, BioCam / Camillo Moschner,
  merged 2026-09-27) runs in a JupyterLab main-area split beside the notebook, in an embed
  mode, and follows the cell you are working in.

Inputs, all read for this spec:

- Design and binding user decisions: `web-repl/design/notebook-display/DESIGN.md`, final
  section "Decisions and scope (user, 260929)". Its **MVP** list is the scope of this epic.
  Its **Next** list is named here (section 2 and the follow-on backlog) but not specified.
- Reference renderer: `web-repl/design/notebook-display/display.js`, with `display.css`,
  `index.html`, `make_fixture.py`, the generated `fixture.js` and `shots/*.png`. The shipped
  renderer emits equivalent HTML and SVG from Python.
- Existing conventions: the ADR `.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md`,
  `web-repl/README.md`, `web-repl/scripts/build_repl.py`, `web-repl/shell/praxis-shell.js`,
  `web-repl/overlay/assets/theme/praxis-theme.css`, `web-repl/overlay/assets/python/praxis/viz/{browser,transport}.py`,
  `web-repl/overlay/assets/visualizer-augmentations/index.js`, `scripts/repl_smoke.py`, and
  the visualizer transport spec `.praxia/docs/specs/260817_spec-visualizer-transport-shim.md`
  (R19, R21).
- PLR main's `pylabrobot/visualizer3D/`, fetched to `/tmp/claude-1000/plr-main/pylabrobot/visualizer3D/`.
- The pinned PLR 0.2.2 (`external/pylabrobot`, `dd79c4c89`) for error sites and tracker behaviour.

**Base.** File references below are to branch `design/notebook-display` at `fd987728`. That
branch predates the persistence ladder (`.praxia/docs/specs/260922_repl-persistence-ladder.md`),
which also appends an IIFE to `praxis-shell.js`, extends `stage_shell`, adds
`test_repl_workflow_covers_tests.py` and adds a `--persistence-check` gate. Every sprint branches
from `origin/main`, not from the design branch. Where this spec says "append", it means after
whatever IIFEs `main` already carries.

---

## 1. Decisions (read first)

### D1. Four spikes run first. The downstream design is correct under every outcome.

Four facts that the design depends on cannot be read from source in this repo. Each becomes a
pre-registered spike (D17). Each sprint that depends on a spike names the branch it builds.

| Spike | Question | Branches and what the downstream design does |
|---|---|---|
| **S1** (sprint A) | Can a plain script, with no labextension build, construct a Lumino `Widget` and add it with `app.shell.add(w, 'main', {mode: 'split-right', ref})`? Does Lumino honour CSS `min-width`/`max-width` on the widget node? Which DOM hooks or model signals give each cell's state (not run, ran, running, error, edited since run)? | **S1-A**: walk the prototype chain of an existing shell widget to the root class. Identify it structurally: its prototype owns `processMessage` and `onAfterAttach`, and its own prototype is `Object.prototype`. `new Ctor({node})` then gives the deck panel as a real widget. **S1-B**: A fails, but a stock command (candidate `help:open`) creates a main-area iframe widget, its iframe allows scripts and same-origin, and it can be re-added with `split-right`. The deck panel then re-homes that widget and replaces its content. **S1-C**: both fail. **Stop** sprint C task C5 and escalate: the user's decision (a real JupyterLab widget) cannot be met without a labextension. The degraded option offered to the user is a shell-owned fixed panel with `#main` narrowed by CSS. Size limits: if CSS limits are honoured, use them. Otherwise the shell clamps through the parent split panel's `setRelativeSizes` (S1 records whether that is reachable). Cell state: each state uses a CSS hook where one exists. Otherwise `chrome.js` computes it from model signals and writes `data-praxis-cell-state` on the cell node. |
| **S2** (sprint A) | For a notebook reopened untrusted in our JupyterLite build, which mimetype does JupyterLab choose from `{text/html, text/plain}`? What does its sanitizer keep of our HTML and SVG? The spike tests elements `svg g path rect text title details summary table`; attributes `fill stroke stroke-width stroke-dasharray class style role aria-label tabindex data-*`; and `viewBox`. | **S2-A**: `text/html` is chosen and SVG survives with `class`. Full design, with token-mapped CSS (D3) applied to reopened outputs. **S2-A'**: SVG survives, but `class` and/or `style` are stripped. Reopened outputs keep their inline light palette (D3) and scale freely without the D5 `min-width` until re-run. Accepted and stated. **S2-B**: SVG is stripped, but `text/html` is still chosen. Reopened outputs show name line, sentence, ledger table and error text, with no drawings until re-run. Accepted: "survives trust loss" is met by the text. **S2-C**: `text/plain` is chosen. Reopened outputs show the summary sentence. Accepted; OQ-9 asks whether a labextension is wanted later. **In every branch the live output format is identical (D2).** Interaction on reopened outputs (hover, keyboard, click to focus) works only if `data-*` and `tabindex` survive. If they are stripped, it returns when the cell is re-run. |
| **S3** (sprint A) | In the JupyterLite Pyodide kernel (`pyodide_kernel-0.8.2`; IPython 9.12.0 per the cached `pyodide-lock.json`), four things: (a) Is `get_ipython()` non-None? (b) Does `display_formatter.mimebundle_formatter.for_type(cls, fn)` work, with `fn` returning `(data, metadata)`? (c) Is a `set_custom_exc` handler invoked for an exception raised in a plain cell **and** in a top-level-`await` cell? Does `display()` inside the handler emit, does the returned structured traceback become the cell's `error` output, and does Run All stop? (d) Does `events.register('post_run_cell', cb)` fire? | **S3-A**: all yes. Design as written. **S3-B**: (b) fails. Register `text/html` and `text/plain` separately via `formatters[...].for_type`. The D7 stamp then lives only in DOM `data-praxis-*` attributes, which live (trusted) outputs keep. **S3-C**: (c) fails. Wrap the kernel shell **instance's** `showtraceback`: an instance attribute that handles the four classes and delegates everything else. PLR and IPython classes are not modified. If that is also not honoured, stop B6 and escalate (MVP item 3 cannot be met). **S3-D**: (d) fails. The kernel announces from PLR state-update callbacks, debounced with `loop.call_later(0.1, ...)`. |
| **S4** (sprint C) | Does the vendored `plr_visualizer3d` package import in the Pyodide kernel? Check `http.server`, `webbrowser`, `socket.gethostname()`, `websockets.asyncio.server` and `websockets.http11`. Does `DockedViewer3D(deck)` construct and `start()` without threads? Does WebLoop support `call_later` and `call_soon_threadsafe` as the viewer uses them? How many bytes is the fixture deck's first `scene` message? | **S4-A**: all yes. Design as written. **S4-B**: a stdlib import or `gethostname` fails. `praxis/viz/viewer3d.py` installs minimal named stubs into `sys.modules` **before** importing `plr_visualizer3d`, the same mechanism `stages.install_native_stubs` uses. Each stub is listed and tested. Vendored files stay byte-identical. **S4-C**: WebLoop lacks `call_later`. Making it work would need a fourth override (`_mark_scene_dirty`), which trips GATE X (D11). **Stop** and escalate. The recommended path is to upstream a transport hook to PLR. |

S1, S2 and S3 are sprint A tasks A1–A3. S4 is sprint C task C1. No task downstream of a spike
starts until that spike's record exists (AC-1..AC-3, AC-29).

### D2. One mimebundle per resource. No `<script>`, no `<style>`, no `image/svg+xml`.

Each rendered PLR object produces one bundle:

- `text/html`: self-contained HTML with inline SVG. There is no `<script>` and no `<style>`
  element. All interaction comes from the shell script (D14).
- `text/plain`: the summary sentence (section 3.2). This is what any viewer that drops HTML
  shows.
- `metadata["praxis"]`: `{"v": 1, "kind": "plate|tiprack|container|deck|ledger|error",
  "resource": "<name>", "rev": <int>, "session": "<kernel session id>"}`. This stamp is JSON,
  not HTML, so no sanitizer can strip it (D7).

Registration uses `get_ipython().display_formatter.mimebundle_formatter.for_type(cls, fn)`,
where `fn` returns `(data, metadata)` (S3-B has the fallback). The registered classes are
`Plate`, `TipRack`, `Deck` and `Container`, with IPython resolving subclasses by MRO. PLR at
the pin defines no `_repr_html_` or `_repr_*_` anywhere under `external/pylabrobot/pylabrobot`
(grep: 0 hits), so nothing is shadowed. PLR is never patched.

`image/svg+xml` is **not** emitted:

- JupyterLab ranks `text/html` above it for trusted outputs.
- For untrusted outputs the SVG renderer is not the safe one.
- It would double the bytes for the benefit of other viewers only.

GitHub and VS Code rendering is a human check (H2).

### D3. Colour is layered: inline light palette, overridden by token-mapped Praxis CSS.

- **Inline.** Every essential colour is an SVG presentation attribute (`fill="#73A9C2"`,
  `stroke="#1D2935"`), and HTML text colour is an inline `style` on the few elements that
  need one. With no Praxis CSS (GitHub, VS Code, print, or S2-A'), an output is still legible
  in the design's light palette.
- **Enhancement.** Presentation attributes carry the lowest cascade priority, so any CSS rule
  wins. `praxis-theme.css` gains `.praxis-out`-scoped rules that map the structural colours to
  JupyterLab tokens:
  - sheet → `var(--jp-layout-color0)`
  - ink → `var(--jp-content-font-color0)`
  - ink soft → `var(--jp-content-font-color2)`
  - rail → `var(--jp-border-color1)`
  - error text → `var(--jp-error-color1)`

  Only moonstone (liquid), rose (attention) and brick (error marks) stay brand constants.
- **Consequence.** Outputs follow Dark (the default), Light **and** "JupyterLab Dark High
  Contrast" without the stylesheet naming any theme. `test_theme_staging.py::test_high_contrast_theme_is_left_alone`
  asserts that the string "JupyterLab Dark High Contrast" and `data-jp-theme-light` never
  appear in the rules. That test keeps passing, and the MVP's "outputs respect Dark High
  Contrast" is met by construction (AC-26).
- **Errors are never shown by colour alone.** Every brick well mark also carries a cross
  glyph (a second path). Every error has a heading sentence.

### D4. Size: one path per well state, and a 64 KiB cap per output.

DESIGN.md requires "one combined path per well state instead of one element per well, plus a
per-output byte cap" but gives no number. This spec sets the numbers:

- **Structure.** A plate figure has one `<path>` per state:
  - well outlines
  - liquid disks (one subpath per non-empty well)
  - changed marks
  - fault marks
  - fault crosses

  Tips get one path each for present rings, present cores and taken rings. There are **zero**
  `<circle>` elements and no per-well `<g>`. Hover and keyboard read a compact grid
  description (section 3.4), not per-well nodes.
- **Hard cap.** At most **65,536 bytes** of UTF-8 `text/html` per output. The reason: a
  30-cell notebook with ten drawings stays under about 1 MB of JSON, which bounds the IndexedDB
  and working-folder mirror writes (the persistence ladder writes whole files per save).
- **Targets**, checked by tests on the fixture:
  - 96-well plate ≤ 16 KiB
  - tip rack ≤ 12 KiB
  - fixture deck ≤ 48 KiB
  - fixture ledger ≤ 32 KiB

  These are estimates from the path grammar (about 35 bytes per circle subpath) and are
  **not measured**. The tests measure them, and any miss is revised with a recorded reason.
- **Degradation ladder** when a render would exceed the cap, in order:
  1. every labware drawn as a filled block
  2. the drawing omitted, with name line + sentence + "Drawing omitted: it would exceed
     64 KiB."

  The cap is never exceeded (AC-13).

### D5. Detail floor, not a fixed scale. The DESIGN.md numbers are kept.

**Invariants:**
- Rendered text is never below **11 px**.
- Rendered wells are never below **4 px** across.

Python cannot measure the browser, so each figure is laid out against a **design content
width of 880 px** (DESIGN.md: "content max 880 px").

**Scale terms:**
- `s_n` is the nominal scale in px/mm:
  - **3** for a single labware figure
  - for the deck: fit to 880 px, clamped to **≥ 0.6**
- Labels are drawn at `12.5 / s_n` user units (mm), which renders them at 12.5 px when the
  figure is at `s_n`.
- `s_min` is the smallest scale the figure may be rendered at:
  `max(0.88 · s_n, 4 / d_min)`, where 0.88 = 11/12.5 and `d_min` is the smallest drawn well
  or tip diameter in mm. For the deck, `s_min = 0.6`.

**Emission.** The SVG is written with `width = W_mm · s_n` and inline
`style="max-width:100%;min-width:<W_mm · s_min>px;height:auto"`, inside a wrapper with inline
`style="overflow-x:auto"`. Below its floor the figure scrolls horizontally and does not
shrink.

**When a scale would break an invariant, the figure shows less detail:**
- **Single labware** is drawn at 3 px/mm.
- **Plates of 384 wells or more** are drawn as square cells. They carry column labels every
  `k`-th column and row labels every `k`-th row. `k` is the smallest of {1, 2, 4, 8} for
  which `k · pitch_mm · s_min ≥ 24 px`, so labels never collide.
- **Deck plan.**
  - Each labware is drawn in full detail if `d_min · s_min ≥ 4`.
  - Otherwise it is drawn as a filled block, with its summary in the deck's sentence.
  - Labels never shrink below the floor.
  - If fitting the deck to 880 px gives a scale below 0.6 px/mm, it is drawn at 0.6 px/mm
    and scrolls horizontally.

**Worked check against the fixture:**
- A Cor 96 plate at `s_n = 3`: well 6.86 mm → 20.6 px.
- `s_min = 2.64`, so the figure's `min-width` is about 390 px, which fits the ~710 px
  notebook width seen with the file browser open.
- A 384-well plate on the deck at 0.6 px/mm: its wells are about 3.6 mm → 2.2 px, so it is
  drawn as a block.

**S2-A' branch.** If S2 finds inline `style` stripped on reopened outputs, the floor holds
only for live outputs. `interact.js` can re-apply `min-width` from `data-praxis-minw` when
`data-*` survives.

### D6. Layout tiers keep the user's numbers. 1280 px is the quality target.

DESIGN.md's "Decided" says the MVP targets desktop windows ≥ 1280 px. MVP item 4 also lists a
1024–1279 drawer. Both are built:

| Window width | Layout | Gate |
|---|---|---|
| ≥ 1600 px | Two panes. Notebook content capped at 960 px; the deck panel takes the rest (no maximum; OQ-4). | AC-36 at 1600×900 |
| 1280–1599 px | Two panes. Deck panel 420–480 px, resizable. With the file browser open the notebook gets about 710 px and outputs scale down to their floor (D5). | AC-36 at 1440×900 and 1280×800 |
| 1024–1279 px | Deck panel is a drawer **over** the notebook. Opening it does not reflow the notebook. | AC-36 at 1152×800 (functional only; human quality checks run at ≥ 1280, OQ-3) |
| < 1024 px | Out of scope. The prototype's bottom sheet is the later starting point. | none |

**Height:** on an 800 px-tall window, the viewer iframe keeps at least **300 px**. The motion
slot shows one row (≤ 36 px) and collapses first.

**Mechanism:**
- The deck panel's widget node carries CSS `min-width: 420px; max-width: 480px` inside
  `@media (min-width: 1280px) and (max-width: 1599px)`, and no max above 1600.
- The 960 px notebook cap is CSS on the notebook panel's content.
- If S1 shows Lumino ignores CSS limits, `dock.js` clamps on `ResizeObserver` callbacks
  through the parent split's `setRelativeSizes` (D1, S1).
- The drawer detaches the widget from the main area and re-attaches it as a fixed-position
  overlay. Moving an iframe in the DOM reloads it, and the socket shim reconnects (D11), so
  this costs one re-greeting.

### D7. Staleness: revision stamps in metadata, announcements on `praxis_repl`, marks in the DOM only.

**Stamps.** Every resource output is stamped (D2) with `resource`, `rev` and `session`:
- `session` is a random id minted once per kernel by `praxis.display.install()`.
- `rev` is a per-resource counter held in the kernel.

When a resource is drawn, `stale.py` subscribes idempotently to the drawn resource and every
descendant (`register_state_update_callback`, `resource.py:924`), and to structural changes
(`register_did_assign_resource_callback` / `unassign`, `resource.py:806-830`). Any callback
increments the `rev` of every drawn ancestor.

**Announcement.** At `post_run_cell` (S3-D has the fallback), if any rev changed during the
cell, the kernel posts exactly one message on the existing **`praxis_repl`** BroadcastChannel,
as the user decided:
- The message is `{type: "praxis:resource-changed", json: "<string>"}`, built flat with
  `js.Object.fromEntries`, as `praxis_bootstrap._post` does.
- `json` encodes `{"session": ..., "exec": <execution_count>, "revs": {"<name>": <rev>}}` and
  is capped at **4 KiB**. Past the cap the `revs` map is replaced by `"all": true`.

**Why `praxis_repl` does not break R21.** R21 (visualizer transport spec) forbids *visualizer*
traffic on `praxis_repl` and greps `praxis/viz/`, `visualizer/` and `visualizer-augmentations/`
for the name. That grep must still exit 1 exactly (AC-18). These announcements come from
`praxis/display/`, send at most one message per cell, carry a typed `type`, and are ignored by
every other listener:
- `praxis-shell.js:84-93` acts only on `praxis:shell-ping`.
- `praxis_bootstrap._setup_broadcast_listener` acts only on `praxis:execute` and
  `praxis:interaction_response` (`praxis_bootstrap.py:212-214`).

**Marking.** The shell (`stale.js`) keeps the latest rev per `(session, resource)`. An output
whose stamp is older gets a DOM notice, **"Changed since, see deck panel."**, inserted in its
output node. The notice is never written to the notebook model, so it is not saved. An output
from another session gets **"Drawn in an earlier session."** The shell maps model outputs to
DOM nodes through the notebook widget's output areas, following the model-first pattern of
`repl_smoke.py:1300-1381`.

### D8. Errors: four classes, context from the traceback, no PLR patch.

The display handles `TooLittleLiquidError`, `TooLittleVolumeError`, `HasTipError` and
`NoTipError` from `pylabrobot.resources.errors` (`errors.py:8-22`). Everything else gets the
normal IPython traceback, styled by Praxis CSS on the stderr/error output. Nothing is
intercepted.

**What PLR's message omits (read at the pin):**
- `TooLittleLiquidError`: "Not enough liquid in container: {volume}uL > {used}uL."
  (`volume_tracker.py:92-94`). No container name.
- `TooLittleVolumeError`: "Not enough space in container: ..." (`:105-107`). No container
  name, and the container may be a **tip** (the tip's tracker receives `add_liquid` during an
  aspirate, `liquid_handler.py:1035`).
- `HasTipError`: "Channel has tip" (`liquid_handler.py:535`), with no channel number, or
  "{thing} already has a tip." (`tip_tracker.py:92`).
- `NoTipError`: "{thing} does not have a tip." (`tip_tracker.py:65, 105`). Here `thing` is
  "Channel N" for head trackers (`liquid_handler.py:197`) but just "Tip spot" for every tip
  spot (`tip_rack.py:52`).

**Context resolution** is a pure function, `context.resolve(exc, tb) -> ErrorContext | None`,
over the traceback frames. It only reads them:

1. **Tracker.** The innermost frame whose `f_locals["self"]` is a `VolumeTracker` or
   `TipTracker` gives `tracker`, and for volume errors, `requested` = that frame's `volume`
   local.
2. **Op.** The innermost frame whose `self` is a `LiquidHandler` gives:
   - `lh`
   - `action = f_code.co_name`
   - `op_resources` (local `resources` or `tip_spots`)
   - `use_channels` and `vols`
   - for `HasTipError("Channel has tip")`, the loop locals `channel` and `op`
     (`liquid_handler.py:533-535`)
3. **Owner, by identity, in this order:**
   - (a) walk `lh.deck`'s subtree for a resource whose `.tracker is tracker` (container or tip
     spot)
   - (b) `lh.head[c] is tracker`, or `lh.head96[c]`, which gives the channel
   - (c) a mounted tip whose `.tracker is tracker`, which gives a tip overflow on channel `c`
   - (d) with no LH frame: parse `tracker.thing`. `"<name>_volume_tracker"`
     (`container.py:85`) gives the container name, and `"Channel N"` gives the channel.
4. **`available`** is parsed from the message (`> ([\d.]+)uL`). This is the value at raise
   time.
5. **Result.** If no owner resolves, the result is `None`, and the handler shows the generic
   panel ("PyLabRobot raised X: message" plus the traceback). **It never guesses.**

**Handler** (`errors.py`, registered by `set_custom_exc`; S3-C has the fallback):
- It calls `display()` on the panel bundle.
- It returns a one-line structured traceback, `["<ExcName>: <PLR message>"]`. The cell
  therefore still ends in an `error` output, the rail shows brick, and Run All stops.
- The full traceback sits inside the panel's `<details>`.

**Panel drawing: committed volume, not pending.** At the pin, the tracker queue loops
(`liquid_handler.py:1031-1035` aspirate, `:533-538` pick up, `:677-684` drop) are outside the
`try` that later commits or rolls back (`:1048-1064`). A tracker error on channel k therefore
leaves channels 0..k-1 with **uncommitted pending** changes, and the backend was never called.
Consequences:
- The panel draws each container's **committed** `tracker.volume` (a public attribute).
- The panel may state "Nothing was aspirated/dispensed" because the backend was not reached.
- The panel never describes the other channels' tracker state.
- Other outputs keep drawing PLR's own `get_used_volume()`, which includes pending, as the
  prototype fixture does. OQ-6 records the upstream question.

**Tracking must be on.** The four errors fire only with PLR tip/volume tracking enabled.
Tracking is off by default (`tip_tracker.py:14`, `volume_tracker.py`); the fixture enables it.

### D9. `RunLedger` is an explicit context manager that shadows one instance's methods.

`with praxis.display.RunLedger(lh) as run:` is the design's own implementation path
(DESIGN.md step 1). How it records:
- On enter, it sets **instance** attributes on that one `LiquidHandler` for these methods:
  - `pick_up_tips`, `drop_tips`, `return_tips`, `discard_tips`
  - `aspirate`, `dispense`, `transfer`
  - the `*96` variants
- Each wrapper records a row (`in-flight`, then `ok` or `error`) and awaits the original bound
  method.
- A `transfer` row owns the aspirate and dispense rows it causes as children. They are nested,
  not double-counted.
- On exit, it deletes the instance attributes and, unless `show=False`, calls `display(run)`.

**Nothing else changes.** PLR modules and classes are never mutated. AC-14 asserts that
`LiquidHandler.aspirate` is the original function and that no op name remains in
`lh.__dict__`.

**Error cooperation.** If an op raises inside the context, the error handler (D8) takes that
row's step number.

**Why not PLR's logger.** PLR logs every command through `_log_command` → `logger.debug` on
the package logger `"pylabrobot"` (`liquid_handler.py:82, 411-424`), with the arguments
flattened to strings. Capturing it would mean raising the user's `"pylabrobot"` logger to
DEBUG, which also fills PLR's own `FileHandler` (`pylabrobot/__init__.py:67-89`). Rejected.

An automatic ledger for every liquid-moving cell is Next (OQ-8).

### D10. The default theme stays Dark. Light gets the designed palette.

`web-repl/jupyter-lite.json:17-20` pins `"theme": "JupyterLab Dark"`. DESIGN.md is light-first,
but changing the first-run theme is a brand decision the MVP list does not make. This epic
therefore:

- Keeps Dark as the default. OQ-1 asks the user.
- Under `body[data-jp-theme-name='JupyterLab Light']`, replaces the cream layout colours with
  the design's page ground `#EEF1F4` and cell sheet `#FFFFFF`, and applies the syntax palette:
  keyword `#2F6882`, string `#A63D61`, number `#8A5A00`, call `#7B4FA0`, comment `#56636F`
  italic. The palette goes through JupyterLab's `--jp-mirror-editor-*` tokens; the exact
  token names are confirmed in task A4.
- Makes the status rail, prompt removal, output inset and error styling theme-neutral, using
  `--jp-*` tokens and brand constants. They apply in Dark and Light.
- Leaves "JupyterLab Dark High Contrast" untouched, as the header of `praxis-theme.css`
  requires. Outputs still follow it (D3).

Every rule obeys the file's load-bearing header: `--jp-*` overrides only under
`body[data-jp-theme-name=...]`, never `:root` or `data-jp-theme-light`, and no `transition`,
`animation` or `@keyframes`.

### D11. Visualizer3D delivery: vendored bytes, three overrides, a socket shim over `praxis_viz3d`.

**Static page.** `web-repl/scripts/vendor_visualizer3d.py` copies PLR main's
`pylabrobot/visualizer3D/static/` to `web-repl/overlay/assets/visualizer3d/`.
- Every file except `index.html` stays **byte-identical**. The script checks sha256 of source
  against output, and the manifest records it.
- `index.html` is transformed in exactly three ways:
  1. `{{ ... }}` placeholders are stripped by pattern: `{{ ws_port }}` at `index.html:338`,
     `{{ source_filename }}` at `:21`. This is the same approach as `vendor_visualizer.py`'s
     `_PLACEHOLDER_RE`.
  2. A classic `<script src="../visualizer3d-augmentations/socket.js"></script>` is inserted
     immediately before the first `<script` in the document (`index.html:319`), so it runs
     before any module.
  3. `<script type="module" src="../visualizer3d-augmentations/embed.js"></script>` is
     inserted before `</body>`.
- Each anchor must match exactly once, or vendoring fails with ±10 lines of context
  (`vendor_visualizer.py` pattern).
- After the transform, `index.html` has zero `https://` URLs, and the vendored tree has zero
  `cdn.jsdelivr.net` hits.
- `VENDOR_MANIFEST.json` records the PLR source commit and per-file sha256.

**Python.** The same script copies `{__init__,facility,grids,scene,server}.py` (excluding
`*_tests.py`, `demo.py` and `model_demo.py`) to
`web-repl/overlay/assets/python/plr_visualizer3d/`, byte-identical.
- The package is **renamed** so that it can never collide with a future PLR pin that ships
  `pylabrobot.visualizer3D`. Its imports still resolve: they are relative (`.scene`,
  `.grids`, ...) or absolute into `pylabrobot.resources.{coordinate,resource}`
  (`server.py:30-31`, `scene.py:16-17`, `grids.py:11`, `facility.py:7-8`), which exist at
  the pin.
- These are loose fetched files, covered by the D2 manifest. `build_manifest.collect_sources`
  already walks every `*.py` under `assets/python/`. This extends the ADR's "praxis's own
  browser Python ships as loose fetched files" (§2) to one vendored third-party package,
  recorded here as a deliberate extension.

**Transport.** No file vendored from PLR is edited. The page's only socket is
`new WebSocket(window.WS_URL)` (`static/transport.js:63`). `socket.js` replaces
`window.WebSocket`, **in that iframe page only**, with `PraxisSocket`: a WebSocket-shaped class
over `BroadcastChannel("praxis_viz3d")`.
- It has the same `CONNECTING/OPEN/CLOSING/CLOSED` statics, `readyState`, `send`, `close`,
  `onopen`, `onclose` and `onmessage`.
- The page's `transport.js` compares against `WebSocket.OPEN` and `WebSocket.CONNECTING` and
  reconnects every 1.5 s for 60 s (`transport.js:23-27, 56-75`). It keeps working unchanged.

**Protocol on `praxis_viz3d`.** Every message is a JSON string carrying `viewer` (the id
minted per `DockedViewer3D`) and `client` (the id minted per `PraxisSocket`):

| Direction | `kind` | Meaning |
|---|---|---|
| kernel → all | `announce` | `{viewer, deck, session}`: a viewer exists. The shell opens the deck panel on the first one. |
| page → kernel | `open` | `{viewer, client}` |
| kernel → page | `accept` | Then the page receives, in order, the `scene` and `state` messages that `Viewer3D._handler` sends (`server.py:590-593`), as `msg`. |
| both | `msg` | `{client, data}`: `data` is the exact string the websocket would carry. |
| page → kernel | `close` | The client closed. |
| kernel → all | `close` | `{viewer, reason}`: the viewer stopped. |

- Without an `accept` within **3 s**, the shim fires `onclose`, and the page's own reconnect
  loop retries.
- Traffic uses a **new channel**, not `praxis_viz`: that channel's receiver
  (`visualizer-augmentations/index.js`) would misread these envelopes. It is also not
  `praxis_repl`, per R21.
- There is no token. BroadcastChannel is origin-scoped (`transport.py:16-18`), which is the
  same exposure `praxis_viz` already accepts. `Viewer3D`'s `_check_websocket` token check is
  never reached, because no websocket server exists.

**Kernel.** `praxis/viz/viewer3d.py` defines `DockedViewer3D(Viewer3D)`, which overrides
exactly **`__init__`, `start` and `stop`**:
- `__init__` forces `open_browser=False` and takes an injected channel factory.
- `start` copies the stock body (`server.py:785-811`) with three differences: `legacy_size`
  runs synchronously (Pyodide has no threads, and `asyncio.to_thread` needs them); there is no
  `websockets.serve`; and there is no file server.
  It subscribes to the channel instead. On each `open` it builds a `VirtualConnection`, which
  has an `async send`, async iteration over an `asyncio.Queue`, and ends on `close`. It then
  runs the **inherited, unmodified** `_handler(conn)` as a task.
  `_broadcast`, `_flush`, `_enqueue`, the scene debounce, `_on_client_message` (hello) and
  every subscription path are inherited unchanged.
- `stop` calls `super().stop()`, which already skips `_ws_server` and `_httpd` when they are
  `None` (`server.py:841-850`), and then posts `close`.

**GATE X** (the same discipline as `praxis/viz/browser.py:18-20`): AC-31 asserts that the
override set is exactly these three. A fourth override is a design regression. Stop, and
upstream a transport hook to PLR.

`praxis_viz3d` and `DockedViewer3D` live under `praxis/viz/`, so the R21 grep (no `praxis_repl`
under `praxis/viz/`) continues to exit 1.

### D12. Deck panel behaviour uses the page's own public API. Selection colour is the page's.

PLR's page exposes `window.plrViewer` (`static/app.js:172-223`):
- `focus(name, viewName)` selects and frames a resource.
- `view(name)` sets `top`/`iso`/`front`.
- `resources()`, `stateOf(name)`, `camera()` and `stats()` answer questions without redrawing.

**The shell drives the panel through it**, calling across the frame: the iframe is
same-origin with no `sandbox`.
- **Follow** (on by default): when the active cell changes, focus the resource stamped on its
  first Praxis output.
- **Click** on any resource inside an output (a `data-praxis-res` hit) focuses it.
- **Iso / Top / Front** call `plrViewer.view`.
- The footer states the focused resource, and for a ledger row, its wells ("assay A1:H3,
  3 columns").

**Deviation from DESIGN.md**, which asks for "a rose outline in both places". The page's
selection box is its own colour (`SELECT = 0x1a4b8c`, `constants.js:118`) and fades after
`SELECTION_SHOWN_MS = 2000` (`:121`). Changing that means editing vendored code, which D11
forbids. So:
- The rose outline is persistent in the notebook output.
- In the deck panel, the page's transient selection plus camera framing stand in.
- A persistent 3D highlight is Next, and needs an upstream PLR API (OQ-5).

**Embed mode.** `embed.js` runs only when `location.search` has `embed=1`.
- It hides, from inside the page, the navbar (`.navbar`), the left tool rail
  (`#toolbar-left`), the stats footer (`#stats-panel`), the tree (`#sidepanel`) and its
  toggle strip (`#toolbar`). This goes through an injected stylesheet, `embed.css`, and does
  not crop the page.
- It sets the page ground to `#EEF1F4`.
- It forwards the page's `plr:status` and `plr:gone` events (`transport.js:35, 74`) to the
  parent window as `praxis:dock-status` CustomEvents. The navbar that normally shows the
  status is hidden.

MVP hides the tree. DESIGN.md's "collapse behind a toggle" is Next.

**Motion slot.** The footer carries one reserved row, "Motion playback is not available for
this backend.", disabled, ≤ 36 px. It is always visible, so the height rule (D6) can be tested
with no test-only switch in product code. `viz3d-motion` is unmerged: STAR v1 driver only,
54 commits ahead and 76 behind main.

### D13. The display installs as a non-fatal bootstrap stage.

`praxis_bootstrap.praxis_main` is a fail-closed ledger (`praxis_bootstrap.py:289-398`). A new
step runs after step 12 (`stages.verify_identity()`) and before `praxis:ready`:

```
try: import praxis.display; praxis.display.install()
except Exception as exc: console.error(...); _post({"type": "praxis:display-error", "reason": str(exc)})
```

This is a **deliberate exception** to fail-closed. The ledger exists so that device I/O never
runs on the wrong class objects (ADR §2.2). A broken drawing layer must not take PyLabRobot
away from the user. The failure is loud: a console error plus a typed channel message, which
the shell shows as a one-line banner. It is never silent.

One stage covers both boot paths: `praxis_boot.setup()` and `welcome.ipynb`'s fetch-and-exec
cell both run `praxis_main`.

### D14. One shell script owns all interaction. Outputs work with none.

A new directory, `web-repl/shell/display/`, holds ES modules loaded by one IIFE appended to
`praxis-shell.js`. The IIFE captures `document.currentScript` synchronously, is gated to
`/lab/`, and runs `import(...).then(m => m.mount(window))`, as the persistence loader does.

**Module rules:**
- Modules take their browser dependencies by injection, so bun can test them.
- They wait for `window.jupyterapp` (present because `exposeAppInBrowser: "true"`,
  `jupyter-lite.json:9`) and `app.restored`.
- **No new storage keys.** Follow state and panel width are in memory only. The ADR's storage
  names and the persistence hygiene gate are unaffected.
- **No test-only switches in product code.** A grep guard enforces this (AC-39).

### D15. At the pin, the liquid's identity is not available. Blue shows volume only.

The user decided: "Blue is volume, always ... The liquid's identity appears on hover and in the
text." At PLR 0.2.2 the tracker no longer records liquids:
- `get_liquids` is deprecated, with the docstring "The volume tracker no longer tracks
  individual liquids." (`volume_tracker.py:122-138`).
- `set_liquids` collapses to a volume (`:74-86`).

Hover and text therefore show volume only. The colour rule is unaffected. OQ-2 asks the user to
confirm, and records that identity returns when PLR tracks it.

### D16. New browser gates live in `repl_smoke.py`. CI is authoritative.

Two new flags follow the shape of `run_notebook_check` (`repl_smoke.py:1226-1430`):
`ServedDir`, `chromium_launch_args`, model-first output reads, and a `result` dict whose keys
are the ACs.

- **`--display-check`** (sprint A adds its chrome scenarios; sprint B adds the rest). It seeds
  the drive with `web-repl/tests/fixtures/notebooks/display_check.ipynb` through
  `serviceManager.contents.save`, then executes cells **one at a time**. It never runs Run All
  on the error cells, except in the one scenario that proves Run All stops.
- **`--dock-check`** (sprint C). It launches a **full** Chromium, the
  `chromium-*/chrome-linux*/chrome` that `resolve_chrome_path` already selects, never
  `headless_shell`, with extra args `--use-angle=swiftshader --enable-unsafe-swiftshader`.
  - Measured 260929 by the orchestrator: the headless shell had neither WebGPU nor WebGL2;
    full Chromium drew the fixture deck on WebGL2/SwiftShader.
  - The result records `chrome_path` and the page's hello (`backend`, `renderer`).

**Local runs.** Narrow only. They need `dangerouslyDisableSandbox: true`, and per project
memory they should run with no `--chrome-path` before a local result is called green: local
chromium-1234 differs from CI's bundled build. pytest runs one file at a time; there are no
whole-suite runs (local compute limits).

### D17. Spikes are pre-registered bathos runs.

Each spike (S1–S4) is a tracked probe script under `scripts/spikes/` with a `.bth.toml`
sidecar. The sidecar states the hypothesis, the `[outcomes]` per branch of D1, and one
**negative control** that must fail. The script and sidecar are committed **before** the run.

**Negative controls:**
- **S1**: a deliberately wrong constructor candidate must fail the structural check.
- **S2**: a `<script>` element and an `onclick` attribute must be observed stripped. This
  proves the sanitizer ran; without it, "SVG survived" could mean nothing was sanitized.
- **S3**: an exception class not registered with `set_custom_exc` must reach the default
  traceback.
- **S4**: a stub-free import of a module known absent from Pyodide must fail.

**How the runs work:**
- Runs use `bth run --project-slug praxis -- uv run --no-sync python3 scripts/spikes/<name>.py ...`.
  Use `bth`, never `uv run bth`, which silently skips enforcement.
- A run is verified by its **record**:
  `bth sql "SELECT id, status, outcome, exit_code, command FROM runs WHERE id LIKE '<prefix>%'"`.
  Run `bth compact` first if the run is not yet visible.
- Each spike's research note, `.praxia/docs/research/260929_notebook-display-s<N>-<slug>.md`
  (filed with `docs add`), cites the run id and names the D1 branch taken.

---

## 2. Goals / Non-goals

**Goals (MVP, DESIGN.md "MVP" items 1–7)**
- G1: The deck panel is a real JupyterLab main-area split (S1-A or S1-B).
- G2: Outputs survive trust loss (D2, D3, S2). Colours are inline, Praxis CSS only enhances,
  no `<script>`, and every output has `text/plain`.
- G3: The size budget: one path per well state, and ≤ 64 KiB per output (D4).
- G4: Stale outputs are stamped, announced on `praxis_repl`, and marked
  "Changed since, see deck panel" (D7).
- G5: Structured error panels for `TooLittleLiquidError`, `TooLittleVolumeError`,
  `HasTipError` and `NoTipError`. Anything else keeps the plain traceback in Praxis styling
  (D8).
- G6: Desktop rendering tiers ≥ 1024 px and the 800 px height rule (D6).
- G7: The detail floor: text ≥ 11 px, wells ≥ 4 px (D5).
- G8: The quality floor:
  - rose and brick stay distinct under colour-vision deficiency, and errors are not shown by
    colour alone
  - keyboard navigation over wells, with the summary sentence as each drawing's text
    alternative
  - Dark High Contrast respected
  - one glossary name per action
- G9: The viewer: vendored static page, the `DockedViewer3D` transport, embed mode, Follow and
  view presets, and the motion slot as a UI slot only (D11, D12).

**Non-goals (this epic)**
- A JupyterLab labextension, custom MIME renderer, or npm or TypeScript build.
- Patching or forking PLR, IPython or any file vendored from PLR.
- Distinct colours for multiple liquids in one well; liquid identity at all (D15).
- Layouts below 1024 px (the bottom sheet).
- A designed Dark variant (Dark gets token-mapped legibility only, D10). Changing the default
  theme (OQ-1).
- Several live viewers or notebooks at once. The most recent `announce` wins; the protocol
  carries ids, so this can be added later.
- An automatic ledger for cells run outside `RunLedger` (OQ-8).
- A persistent 3D highlight in the deck panel (OQ-5). A collapsible tree in embed mode.
- A notebook top bar with the file name, a "Simulated STARlet" badge or the kernel state (shown
  in DESIGN.md's layout sketch, but not in the MVP list).

**Next (named; follow-on backlog, not specified here)**
- **Live hardware mode.** A Stop control that is always visible while a hardware backend is
  attached. Its semantics are a separate safety decision. The ledger streams during long runs,
  worded as "PyLabRobot's record", and STAR per-channel firmware errors are drawn on the
  labware.
- **Plate-reader results** on the plate outline, with their own sequential colour ramp (not
  moonstone).
- **More labware**: troughs, tube racks, lids, plate stacks, Petri dishes (PLR #1308),
  machine outputs.
- **Coxswain proposals** as ledger rows in a "proposed" state, with an approve control.
  `coxswain.css`'s `--cx-*` palette moves onto the Praxis tokens; another session owns
  coxswain.
- **Persistence UI tokens.** The persistence panel, chip and first-save modal (#4296) adopt
  the tokens.
- **Dark theme variant.**
- **Layouts below 1024 px** (the bottom sheet).
- **Motion playback** from `stefangolas/pylabrobot@viz3d-motion` in the reserved slot, once
  merged upstream.

---

## 3. User-visible behaviour

### 3.1 Chrome (all themes except High Contrast, which is untouched)

- **The status rail** replaces `In [n]:`. It is a 3 px bar on each code cell's left edge:
  - rail grey: not run
  - moonstone ink `#2F6882`: ran
  - rose `#ED7A9B`: running
  - brick `#B3402A`: error
  - dashed: edited since it ran

  The execution count sits at the rail's top, in 12.5 px ink-soft. The state comes from a CSS
  hook or from `data-praxis-cell-state`, per S1.
- **Prompts.** The input and output prompts take no space. Outputs are inset under their code
  on the same sheet, divided by one rail-coloured hairline.
- **Light theme.** The page ground is `#EEF1F4`, the cell sheet `#FFFFFF`, and the syntax
  palette from D10 applies.
- **Tracebacks.** Non-PLR tracebacks keep JupyterLab's error output, restyled with brick
  accents and JetBrains Mono.

### 3.2 Output grammar (every resource output)

1. **Name line.** The resource name (Roboto Flex, `font-stretch` condensed, weight 600), then
   its PLR type and model in ink-soft: `source  Plate  Cor_96_wellplate_360ul_Fb`. The model
   string is PLR's `model` attribute, verbatim.
2. **The drawing.**
   - It is to scale per D5, with the front edge at the bottom.
   - Well grids show row letters and column numbers.
   - Liquid is a moonstone disk whose **area** is proportional to
     `get_used_volume() / max_volume`, i.e. `r_liquid = r · sqrt(clamp(v / max, 0, 1))`.
     A container whose `max_volume` is infinite gets no fill.
   - Wells are circles when `cross_section_type == CIRCLE` (`well.py:19-28`) and rectangles
     otherwise.
   - Present tips are filled ink rings; taken tips are dashed rail rings.
   - The plate outline has a 2 mm corner radius.
3. **Summary sentence.** It is also the `text/plain` and the drawing's `aria-label`.
   - Plate: "24 of 96 wells hold liquid, 50–150 µL. 2,400 µL in the plate."
   - Every well holds liquid: "All 96 wells hold liquid, 200 µL each. 19,200 µL in the plate."
   - Empty plate: "All 96 wells are empty. Each holds up to 360 µL."
   - Tip rack: "72 of 96 tips left. Columns 1–3 used."
   - Container (single well or trough): "assay A1 holds 50 µL of 360 µL."
   - Deck: "Tip carrier on rail 3, plate carrier on rail 9. 3 pieces of labware: tips_300,
     source, assay."
   - Number formatting: thousands separator, an en dash for ranges, `µL` preceded by a space,
     at most one decimal place.

**Deck** figures add a rail ruler along the front edge, numbered at rail 1 and every 5th rail.
Carriers are drawn in rail outline with condensed name labels, and labware in ink. The deck
tiers follow D5.

### 3.3 Run ledger and error panel

**Run ledger** (`with RunLedger(lh) as run:` → shown on exit):
- The name line reads "run  12 steps, 3 tip cycles, 2,400 µL moved".
- A table has one row per op, with columns **step, action, where, volume, channels**.
  - A new tip cycle, which starts at each pick-up, gets a hairline above it.
  - Aspirate and dispense rows carry a moonstone bar sized by volume.
  - Action names come from the glossary (section 3.5).
  - "Where" reads "source, column 1" for a whole column. Otherwise it is the compressed range
    "assay A1:H3", or a comma list.
- The table ends with the changed plates after the run, with the changed wells outlined in
  rose, under "The assay plate after the run. Wells this run changed are outlined."

**Error panel** (the four classes):
- A brick status rail.
- A heading that states the fault and names the resource and wells.
- One body sentence with the numbers.
- A fix sentence.
- A drawing of the labware at committed volume, with the offending wells marked with a brick
  ring **and** a cross.
- "PyLabRobot raised `<Name>: <message>`".
- `<details><summary>Show traceback</summary>`.

Templates. `{wells}` uses the compressed range, and `µL` values are formatted as in 3.2:

| Case | Heading | Body | Fix |
|---|---|---|---|
| TLL, owner is a well (aspirate) | "Not enough liquid in {plate} {wells}." | "Each well holds {avail} µL; the aspirate asked for {req} µL." Or, when the wells differ: "{wells} hold {min}–{max} µL; ...". Then: "Nothing was aspirated." | "Lower `vols` to {min} µL or less, or aspirate from wells that hold more." |
| TLV, owner is a well (dispense) | "Not enough room in {plate} {wells}." | "Each well has room for {avail} µL; the dispense asked for {req} µL. Nothing was dispensed." | "Lower `vols`, or dispense into emptier wells." |
| TLV, owner is a tip (aspirate) | "The tip on channel {c} can't hold {req} µL." | "It has room for {avail} µL. Nothing was aspirated." | "Aspirate less, or use larger tips." |
| HasTip, channel (pick up) | "Channel {c} already holds a tip." | "Pick up asked channel {c} for another." | "Drop or discard the tip first." |
| HasTip, tip spot (drop/return) | "{rack} {spot} already has a tip." | "Drop asked to put a tip there." | "Drop the tip into an empty position." |
| NoTip, channel | "Channel {c} has no tip." | "{Action} needs a tip on every channel it uses." | "Pick up tips before you {action}." |
| NoTip, tip spot (pick up) | "{rack} {spot} has no tip." | "Pick up asked for a tip that has already been taken." | "Pick up from a position that still has a tip." |

With the fixture's error cell (`make_fixture.py:97-99`: 80 µL from assay A1:H1, which holds
50 µL), the panel reads "Not enough liquid in assay A1:H1." / "Each well holds 50 µL; the
aspirate asked for 80 µL. Nothing was aspirated."

### 3.4 Interaction (shell script; no `<script>` in outputs)

Each drawing carries:
- `data-praxis-res="<name>"` on the resource group.
- A grid descriptor, `data-praxis-grid`: compact JSON with origin, pitch, rows, cols, ids,
  per-well values, and each well's changed or fault flag.
- `tabindex="0"`, `role="img"`, and `aria-label` = the summary sentence.

**Hover** over a well or tip shows a small readout, positioned by the shell, with the address
and value: "assay B3: 100 µL", "tips_300 C2: tip", "tips_300 C2: taken".

**Keyboard.** Tab focuses a figure. Arrow keys move a focus ring across the grid, and one
shell-owned `aria-live="polite"` region announces the same text as the hover readout. Escape
leaves the grid.

**Click** on any resource focuses it in the deck panel. The notebook output gets a persistent
rose outline (the `is-focus` class, drawn by Praxis CSS).

If S2 shows that `data-*` or `tabindex` are stripped on reopened outputs, those outputs are
static until re-run.

### 3.5 Glossary (one name per action; `praxis/display/glossary.py`)

| PLR method | Name in every Praxis text | Verb form in fixes |
|---|---|---|
| `pick_up_tips` | Pick up tips | pick up tips |
| `drop_tips` | Drop tips | drop tips |
| `return_tips` | Return tips | return tips |
| `discard_tips` | Discard tips | discard tips |
| `aspirate` | Aspirate | aspirate |
| `dispense` | Dispense | dispense |
| `transfer` | Transfer | transfer |
| `*96` variants | the same name + " (96 head)" | the same |

Nouns: **channel** (never "pip" or "pipette"), **well**, **tip**, **tip rack**, and
**deck panel** in every UI string. "Dock" is an internal name only.

### 3.6 Deck panel

It opens automatically, split right of the current notebook, on the first `announce` from a
kernel, i.e. after `viewer = await praxis.viz.viewer3d.dock(deck)`. The layout:

- **Header:** the deck name, a Follow toggle (on), and Iso / Top / Front (Top is the page's
  default view, `renderer.js:263`).
- **Body:** the iframe `assets/visualizer3d/index.html?embed=1&view=top`.
- **Footer:** the focused resource in words, then the one-row motion slot.

**States:**
- With no viewer running, or after `plr:gone`, the body shows "No deck viewer is running.
  Run `viewer = await praxis.viz.viewer3d.dock(deck)` in a cell."
- `await viewer.stop()` gives the same placeholder within 5 s.

**Commands and tiers.** Closing the tab hides the panel. A registered command,
`praxis:toggle-deck-panel`, reopens it. The tiers follow D6.

---

## 4. Module and file plan

| Path | Action | Contents |
|---|---|---|
| `scripts/spikes/260929_s1_lumino_widget.py` + `.bth.toml` | create (A1) | Playwright probe over a built dist, `lab/` entry. It tries S1-A, then S1-B. It records `split_right_ok`, `css_limits_honoured`, `set_relative_sizes_reachable`, and the per-state cell hooks, with the negative control from D17. Written with argparse and logging. |
| `scripts/spikes/260929_s2_sanitizer.py` + `.bth.toml` | create (A2) | It writes a notebook JSON with crafted outputs to the drive, which is untrusted because it was never executed, reopens it, and records the chosen mimetype and survivorship per element and attribute. It repeats the check for the same bundle displayed live (trusted). Negative control from D17. |
| `scripts/spikes/260929_s3_ipython_hooks.py` + `.bth.toml` | create (A3) | It runs S3's (a)–(d) in the kernel through a seeded notebook, and records the IPython version, `run_code` path evidence and outputs by model. Negative control from D17. |
| `scripts/spikes/260929_s4_viewer3d_pyodide.py` + `.bth.toml` | create (C1) | It imports the staged `plr_visualizer3d` in the kernel, constructs and starts `DockedViewer3D` on the fixture deck, and records the stubs needed and the `scene` bytes. Negative control from D17. |
| `web-repl/overlay/assets/theme/praxis-theme.css` | modify (A4) | Appends sections for the status rail, prompt removal, output inset, the Light steel/sheet ground and syntax palette (Light only), `.praxis-out` token mapping (D3), the stale notice, the error panel, traceback accents, the hover readout, the focus ring, and the deck panel header and footer. It follows the header rules; no animation. |
| `web-repl/tests/test_display_css.py` | create (A4) | Text invariants on the new rules: no HC name, no `data-jp-theme-light`, no bare-`:root` `--jp-*`, no animation. Every colour in a `.praxis-*` rule is `var(--jp-*)`, `var(--praxis-*)` or one of the DESIGN hexes for moonstone, rose, rose ink or brick. The Light block carries `#EEF1F4`. |
| `web-repl/shell/display/index.js` | create (A5) | `mount(window)`: waits for `jupyterapp` and `restored`, then mounts `chrome`, and from sprint B `stale` and `interact`, and from sprint C `dock`. |
| `web-repl/shell/display/chrome.js` | create (A5) | Cell-state derivation from the model, a pure `cellState(model, kernelStatus)`, plus the DOM writer for `data-praxis-cell-state` and `data-praxis-exec`, per the S1 result. |
| `web-repl/shell/display/__tests__/fakes.js`, `chrome.test.js` | create (A5) | Fakes for cells, notebook, app, BroadcastChannel and the DOM, following `web-repl/shell/coxswain/__tests__/dom_stub.js`. |
| `web-repl/shell/praxis-shell.js` | modify, append only (A5) | One loader IIFE for `display/index.js`, gated to `/lab/`. Existing IIFEs untouched, including the persistence IIFE on `main`. |
| `web-repl/scripts/build_repl.py` | modify (A6, B9, C6) | A6: `stage_shell` removes and then copies `shell/display/`, skipping `__tests__`, and `assert_dist_complete` requires `shell/display/{index,chrome}.js`. B9: adds `stale.js` and `interact.js` to the required list. C6: adds `dock.js`, `assets/visualizer3d/index.html`, `assets/visualizer3d/vendor/three.webgpu.min.js`, `assets/visualizer3d-augmentations/{socket,embed}.js` and `embed.css`, `assets/python/plr_visualizer3d/server.py`, `assets/python/praxis/viz/viewer3d.py`, and `assets/python/praxis/display/__init__.py`, the last from B8. |
| `web-repl/tests/test_display_staging.py` | create (A6), extend (B9, C6) | Stages to `tmp`: no `__tests__`, a stale file is removed, and `assert_dist_complete` raises on a missing required file. |
| `web-repl/tests/fixtures/notebooks/display_check.ipynb` | create (A7), extend (B10, C7) | The gate notebook. Boot cell, the fixture deck from `make_fixture.py`'s `assemble()` with tracking on, cells that draw the deck, a plate and a tip rack, a `RunLedger` cell, one cell per error case, a sleep cell (running state), and a marker cell after an error (Run All stops). Not shipped in dist; the harness seeds it. |
| `scripts/repl_smoke.py` | modify (A7, B10, C7) | Adds `--display-check` and `run_display_check`, and later `--dock-check` and `run_dock_check`. Each is added to the "nothing to do" list and gets a `main()` branch. |
| `web-repl/overlay/assets/python/praxis/display/__init__.py` | create (B8) | Exports `install`, `RunLedger` and `render`. `render(obj)` returns the bundle, for tests and explicit use. |
| `.../praxis/display/svg.py` | create (B1) | Path builders (circle as two arcs, rounded rect, cross), a text element with a font size in user units, and number formatting. No PLR import. |
| `.../praxis/display/floor.py` | create (B1) | D5 math: `nominal_scale`, `s_min`, `label_step_k`, `detail_level(labware, s_min)`. |
| `.../praxis/display/budget.py` | create (B1) | D4 cap and degradation ladder: `enforce(render_fn, levels) -> (html, level)`. |
| `.../praxis/display/labware.py` | create (B2) | Plate, tip rack and container figures and sentences; well-range compression; the grid descriptor. |
| `.../praxis/display/deck.py` | create (B3) | Deck plan, rail ruler, carriers, labware at their detail level, the deck sentence. |
| `.../praxis/display/glossary.py` | create (B4) | `ACTIONS` and nouns (section 3.5). The only home of action strings. |
| `.../praxis/display/ledger.py` | create (B4) | `RunLedger` (D9): rows, tip cycles, the after-state figures, the bundle. |
| `.../praxis/display/context.py` | create (B5) | `resolve(exc, tb) -> ErrorContext | None` (D8). |
| `.../praxis/display/errors.py` | create (B6) | Panel rendering (section 3.3) and `handler(shell, etype, value, tb, tb_offset=None)`. |
| `.../praxis/display/stale.py` | create (B7) | Session id, revs, subscriptions, the `post_run_cell` announcer. It takes an injected `post(str)`. `import js` appears only inside `make_repl_poster()`, as in `browser.py:179-192`. |
| `.../praxis/display/install.py` | create (B8) | `install(shell=None)`: registers the D2 formatters (with the S3-B fallback), the D8 handler (with the S3-C fallback), the D7 hooks (with the S3-D fallback) and the session. It is idempotent. |
| `web-repl/bootstrap/praxis_bootstrap.py` | modify (B8) | Adds the D13 non-fatal stage between step 12 and `praxis:ready`. |
| `web-repl/shell/display/stale.js`, `interact.js` + tests | create (B9) | D7 marking; D14 hover, keyboard, click and the live region; the grid hit-test (pure). |
| `web-repl/tests/test_display_{labware,deck,floor,budget,ledger,context,errors,stale,install,glossary,colorblind}.py` | create (B1–B8) | CPython tests. They load `praxis/display` by path under the synthetic package `_praxis_display_under_test` and never touch `sys.path` (README rule 2; the `test_browser_visualizer.py:33-51` pattern). They use real PLR 0.2.2 resources and `LiquidHandlerChatterboxBackend`. |
| `web-repl/scripts/vendor_visualizer3d.py` | create (C2) | D11 vendoring: static and Python, with `--src` pointing at a PLR main checkout and `--check`, which verifies the committed trees against the source. Written with argparse and logging, and fails loud. |
| `web-repl/overlay/assets/visualizer3d/**` | generated, committed (C2) | The vendored static tree, `VENDOR_MANIFEST.json`, and the transformed `index.html`. |
| `web-repl/overlay/assets/python/plr_visualizer3d/**` | generated, committed (C2) | Five vendored `.py` files and `VENDOR_MANIFEST.json`. |
| `web-repl/tests/test_vendor_visualizer3d.py` | create (C2) | AC-30. |
| `web-repl/overlay/assets/python/praxis/viz/viewer3d.py` | create (C3) | `DockedViewer3D`, `VirtualConnection`, `ChannelTransport` (injected), `make_viz3d_channel()` (the only `import js`), and `async def dock(deck, **kw)`. |
| `web-repl/tests/test_viewer3d_docked.py` | create (C3) | AC-31. Loads `plr_visualizer3d` and `praxis/viz` under synthetic names. |
| `web-repl/overlay/assets/visualizer3d-augmentations/socket.js` | create (C4) | A classic script. The factory `makePraxisSocketClass(BroadcastChannelCtor, {acceptTimeoutMs})` is attached to the global, and the script assigns `window.WebSocket` when `document` exists. |
| `web-repl/overlay/assets/visualizer3d-augmentations/embed.js`, `embed.css` | create (C4) | D12 embed mode and status forwarding. |
| `web-repl/shell/display/__tests__/viz3d_socket.test.js` | create (C4) | Evaluates `socket.js` text against a fake global. Kept here so that no `__tests__` directory lives under `overlay/assets/`, which is staged wholesale (`build_repl.py:551-578`). |
| `web-repl/shell/display/dock.js` + tests | create (C5) | The deck panel widget per S1, the header, the footer, tiers, Follow, presets and placeholder; `praxis:toggle-deck-panel`. |
| `.github/workflows/repl.yml` | modify (A7, B10, C7) | Each sprint adds its pytest lines in the task that creates each test file (the per-file guard `test_repl_workflow_covers_tests.py` on `main` fails on an unwired file), its `bun test web-repl/shell/display` line in the coxswain job (A5), and its smoke step (A7: `--display-check`; C7: `--dock-check`). |

**Files that must not change:**
- `web-repl/jupyter-lite.json` (D10; OQ-1 could change that later)
- `web-repl/scripts/inject_shell.py`
- the existing IIFEs in `praxis-shell.js`
- `web-repl/overlay/assets/visualizer/**` and `visualizer-augmentations/**`
- every byte vendored from PLR other than the transformed `index.html`

---

## 5. Acceptance criteria

Gate shorthands:
- **[PY:file]** means `uv run python -m pytest web-repl/tests/<file> -q`, one file per
  process, as in `repl.yml`.
- **[BUN]** means `bun test web-repl/shell/display`.
- **[DISPLAY]** means the JSON keys of
  `uv run python scripts/repl_smoke.py --display-check --base-path /praxis/`, which exits 0
  only if every listed key holds.
- **[DOCK]** means the same for `--dock-check`.
- Browser gates are authoritative in CI. Local runs follow D16.

### Sprint A: spikes and chrome

- **AC-1 (S1 recorded)**:
  - `bth sql` shows the S1 run with `status` completed and `outcome` not null. The run
    evaluated the pre-registered outcomes.
  - The sidecar's commit precedes the run (`git log` order).
  - The S1 research note names the branch (S1-A, S1-B or S1-C), and the negative control's
    failure is recorded.
- **AC-2 (S2 recorded)**:
  - Same record checks as AC-1.
  - The note contains the survivorship table: element and attribute × {trusted live,
    untrusted reopened}.
  - The note records the mimetype chosen for untrusted `{text/html, text/plain}` and names the
    D1 branch.
- **AC-3 (S3 recorded)**:
  - Same record checks as AC-1.
  - The note records the IPython version seen in the kernel and the (a)–(d) results, and
    names the branch.
- **AC-4 (theme invariants)** [PY:test_display_css.py] and [PY:test_theme_staging.py]:
  - Both pass. `test_high_contrast_theme_is_left_alone` and
    `test_jp_tokens_are_not_defined_on_bare_root` are unchanged and green.
- **AC-5 (cell-state logic)** [BUN]:
  - `cellState` returns:
    - `not-run` for a cell with no execution count
    - `ran` after a successful execution
    - `running` while executing
    - `error` when an output has `output_type == "error"`
    - `stale` when the source changed after the last execution
  - The DOM writer sets `data-praxis-cell-state` and `data-praxis-exec`, and is idempotent.
- **AC-6 (staging)** [PY:test_display_staging.py]:
  - The test passes, including the stale-file and missing-file cases.
  - After `uv run python web-repl/scripts/build_repl.py --base-path /praxis/`, these both
    succeed: `test -f web-repl/dist/shell/display/index.js` and
    `! test -e web-repl/dist/shell/display/__tests__`.
- **AC-7 (chrome in the browser)** [DISPLAY, scenario D1: fresh context; Light theme set via
  `apputils:change-theme`]:
  - `rail_state_never_run == "not-run"`.
  - `rail_state_after_run == "ran"`.
  - `rail_state_while_sleep == "running"`, polled during `await asyncio.sleep(3)`.
  - `rail_state_after_raise == "error"`, from a `raise ValueError` cell.
  - `rail_state_after_edit == "stale"`, after typing into an executed cell.
  - `rail_colors_match`: each state's computed rail colour equals the section 3.1 value.
  - `prompts_take_no_space`: the input and output prompt widths are each ≤ 1 px.
  - `light_ground == "rgb(238, 241, 244)"` and `light_sheet == "rgb(255, 255, 255)"`.
  - `exec_count_on_rail`: the rail's count text equals the cell's execution count.
  - `pageerrors == []`.
- **AC-8 (no regressions, sprint A)**:
  - The REPL workflow is green on the PR head. That includes `--notebook-check`,
    `--fresh-boot-check`, `--completion-check`, `--typeahead-check`, `--viz-check`, the
    persistence gate if present on `main`, and
    `uv run python -m pytest web-repl/tests/test_inject_shell_coxswain.py -q`, including the
    inject block's byte-identity test.
  - `git diff origin/main -- web-repl/jupyter-lite.json web-repl/scripts/inject_shell.py` is
    empty.

### Sprint B: praxis.display

- **AC-9 (plate repr)** [PY:test_display_labware.py], on the fixture state rebuilt from
  `make_fixture.py`'s steps:
  - The assay bundle's `text/plain` is exactly
    "24 of 96 wells hold liquid, 50–150 µL. 2,400 µL in the plate.".
  - The source plate's `text/plain` is exactly
    "All 96 wells hold liquid, 50–200 µL. 16,800 µL in the plate.". This is recomputed from the
    fixture: columns 1–3 hold 150, 100 and 50 µL, and columns 4–12 hold 200 µL. The test
    derives the expected string from the tracker state and the section 3.2 rules, and asserts
    the rules separately.
  - `text/html` contains 0 `<circle`, 0 `<script`, 0 `<style`, and ≤ 8 `<path`.
  - The well-outline path has 96 subpaths (`M` count), and the liquid path has 24 for assay.
  - Every liquid radius equals `r · sqrt(v / max_volume)` within 1e-3 mm.
  - `fill="#73A9C2"` is present.
  - `metadata["praxis"]` has keys `{v, kind, resource, rev, session}`.
- **AC-10 (tip rack and container)** [PY:test_display_labware.py]:
  - Tip rack `text/plain` == "72 of 96 tips left. Columns 1–3 used.".
  - The present-tip, core and taken-ring paths are each a single `<path>`.
  - For a single well: `text/plain` == "assay A1 holds 50 µL of 360 µL.". The text uses the
    fixture's `max_volume` value, formatted.
  - A rectangular well renders as a rect subpath.
- **AC-11 (deck repr)** [PY:test_display_deck.py]:
  - Ruler labels are exactly rails 1, 5, 10, 15, 20, 25, 30 for the STARLet deck
    (`deck.num_rails`).
  - The carrier labels "tip_carrier" and "plate_carrier" are present.
  - The fixture deck's `text/html` is ≤ 49,152 bytes.
  - The deck sentence equals the section 3.2 example.
  - The wrapper carries `overflow-x:auto`, and the SVG carries the D5 `min-width`.
- **AC-12 (detail floor)** [PY:test_display_floor.py], parametrized over the fixture plate,
  the tip rack, the deck, a 384-well plate and a 1536-well plate. PLR resource definitions are
  available at the pin; the test names the exact definitions it uses.
  - For every figure and every text element: `font_size_user_units × s_min ≥ 11`.
  - For every drawn well or tip: `diameter_mm × s_min ≥ 4`; otherwise the labware is drawn as
    a block.
  - The 384- and 1536-well plates use square cells, with label steps equal to the D5 `k`.
  - A deck whose fitted scale is below 0.6 is emitted at 0.6 with horizontal scroll.
- **AC-13 (byte cap)** [PY:test_display_budget.py]:
  - Every fixture bundle has `text/html` ≤ 65,536 bytes and meets its D4 target. A missed
    target fails with the measured size.
  - A synthetic deck carrying 20 plates of 1536 wells degrades first to blocks and then, if
    still over, to summary-only. Its `text/html` is ≤ 65,536 bytes at every level, and the
    omission sentence is present when the drawing is dropped.
- **AC-14 (ledger)** [PY:test_display_ledger.py], replaying `make_fixture.run_transfers`
  inside `RunLedger(lh, show=False)`:
  - 12 rows in 3 tip cycles.
  - Actions in order: Pick up tips, Aspirate, Dispense, Discard tips, three times.
  - Volumes 50, 100, 150 µL; channels 8.
  - `text/plain` starts "run  12 steps, 3 tip cycles, 2,400 µL moved".
  - The after-state assay figure marks 24 wells in rose (`stroke="#ED7A9B"`).
  - After exit: `LiquidHandler.aspirate is <the function captured before import>`, and no op
    name is in `vars(lh)`.
  - A `transfer` inside the context yields one Transfer row with nested children, not
    duplicate rows.
  - An op that raises inside the context marks its row `error` and re-raises unchanged.
- **AC-15 (error context)** [PY:test_display_context.py]. Real PLR at the pin, chatterbox
  backend, tracking on. Each case raises the real error and asserts
  `resolve(exc, exc.__traceback__)`:
  - **E1** (fixture): aspirate 80 µL from assay A1:H1, which holds 50 → owner assay A1,
    op wells A1:H1, requested 80, available 50, action `aspirate`.
  - **E2**: dispense 400 µL into a 360 µL well → TLV, owner a well.
  - **E3**: aspirate more than the 300 µL tip holds → TLV, owner the tip on channel 0.
  - **E4**: `pick_up_tips` with tips already on → HasTip, channel from the loop local.
  - **E5**: `drop_tips` onto an occupied spot → HasTip, owner the tip spot.
  - **E6**: aspirate with no tips → NoTip, channel from `"Channel N"`.
  - **E7**: pick up from a taken spot → NoTip, owner the tip spot, by identity.
  - **E8**: `well.tracker.remove_liquid(999)` outside any LH → owner from
    `thing` = `"<name>_volume_tracker"`.
  - Negative: a `ValueError` → `None`.
  - Negative: a TLL raised by a tracker whose `thing` names nothing on any deck, with no LH
    frame → `None`.
- **AC-16 (error panel)** [PY:test_display_errors.py]:
  - For E1, the heading is exactly "Not enough liquid in assay A1:H1."
  - The body contains "Each well holds 50 µL; the aspirate asked for 80 µL." and
    "Nothing was aspirated."
  - The fix is the section 3.3 text.
  - Fault wells carry both a brick ring path and a cross path.
  - The drawing uses committed `tracker.volume`, checked by forcing a pending ≠ committed
    well.
  - The traceback is inside `<details>`.
  - `text/plain` contains the heading and the body.
  - E2–E7 each match their template row.
- **AC-17 (handler semantics)** [PY:test_display_install.py], with a fake shell recording
  `set_custom_exc`, `display` and formatter registrations:
  - Exactly the four classes are registered.
  - The handler returns a list of one string, `"<Name>: <message>"`.
  - The handler displays exactly one bundle.
  - An unresolvable context displays the generic panel.
  - `install()` is idempotent: a second call registers nothing new.
  - The S3-B and S3-C fallbacks each have a case that is selected when the fake lacks the
    primary API.
- **AC-18 (staleness, kernel)** [PY:test_display_stale.py]:
  - Drawing `source` stamps `rev` r.
  - `source A1`'s tracker `set_volume` bumps `source` to r+1, and also the deck's rev if the
    deck was drawn.
  - One simulated `post_run_cell` posts exactly one message, carrying only the changed revs.
  - A cell with no change posts nothing.
  - The `json` field is ≤ 4096 bytes, and it switches to `"all": true` past the cap.
  - The channel name `praxis_repl` appears in `praxis/display/stale.py` only.
  - `test -d` on the three paths, then
    `grep -rn "praxis_repl" web-repl/overlay/assets/python/praxis/viz/ web-repl/overlay/assets/visualizer/ web-repl/overlay/assets/visualizer-augmentations/`
    exits **1 exactly** (R21).
- **AC-19 (shell stale and interaction)** [BUN]:
  - `stale.js`, given stamps and announcements, marks only outputs with an older rev in the
    same session, marks other-session outputs "Drawn in an earlier session.", is idempotent,
    and never calls any model setter (the fake model throws on write).
  - `interact.js`:
    - The hit-test maps points to well ids for a 96 grid and a 384 grid, including edges.
    - ArrowRight from A1 gives A2, and ArrowDown from A1 gives B1, clamped at the edges.
    - The live-region text equals the hover text.
    - A click on `data-praxis-res` emits `focus(name)` to the injected dock API.
- **AC-20 (install and bootstrap)** [PY:test_praxis_bootstrap_loader.py] plus
  [PY:test_display_install.py]:
  - The stage order places the display install after `verify_identity` and before the
    `praxis:ready` post.
  - With an install that raises, `praxis:ready` is still posted, and one
    `praxis:display-error` message precedes it.
- **AC-21 (reprs live)** [DISPLAY, scenario D2]:
  - `repr_cells_ok`: the deck, plate and tip-rack cells each have a model output with
    `text/html`, `text/plain` and `metadata.praxis`.
  - `svg_in_dom`: each has an `svg` under its output node.
  - `html_bytes_max` ≤ 65,536.
  - `text_plain_matches`: the assay `text/plain` equals AC-9's string.
  - `pageerrors == []`.
- **AC-22 (error panels live)** [DISPLAY, D2 continued, cells run one at a time]:
  - `error_panels`: for E1, E2, E4 and E6, the heading text equals AC-16's.
  - `error_status`: each cell's last output has `output_type == "error"` and its rail state
    is `error`.
  - `runall_stops`: in a separate run-all of the "E1 then marker" pair, the marker cell's
    execution count stays null.
  - `other_errors_plain`: a `ValueError` cell shows the default traceback with no
    `.praxis-error` node.
- **AC-23 (staleness live)** [DISPLAY, D2 continued]:
  - `stale_marked`: after the aspirate cell runs, the earlier `source` output contains
    "Changed since, see deck panel." within 5 s.
  - `stale_not_persisted`: after `docmanager:save`, `contents.get` of the notebook contains
    no "Changed since".
  - `unchanged_not_marked`: the tip-rack output from before an aspirate-only cell is not
    marked.
- **AC-24 (trust loss)** [DISPLAY, scenario D3: save, reload, reopen the notebook]:
  - `no_script_in_bundles`: the saved JSON has zero `<script` in any output.
  - `reopened_branch` equals the S2 branch recorded in AC-2.
  - Branch-conditional keys:
    - **S2-A**: `liquid_fill_computed` is moonstone, or the theme's token for liquid (which
      is moonstone), on a reopened plate.
    - **S2-A'**: `liquid_fill_attr == "#73A9C2"`.
    - **S2-B**: `summary_text_visible` and no `svg`.
    - **S2-C**: `text_plain_visible`.
- **AC-25 (keyboard and text alternative)** [DISPLAY, D2]:
  - `svg_role_img` and `aria_label_equals_summary`.
  - `tab_focuses_figure`: Tab lands on the assay figure.
  - `arrow_moves`: ArrowRight changes the live region to "assay A2: 50 µL".
  - `escape_leaves`: Escape returns focus to the figure.
  - All keys are driven by `page.keyboard`.
- **AC-26 (High Contrast)** [DISPLAY, scenario D4: theme set to
  "JupyterLab Dark High Contrast"]:
  - `hc_text_color`: the summary text colour equals the computed `--jp-content-font-color0`.
  - `hc_sheet_fill`: the plate sheet fill equals the computed `--jp-layout-color0`.
  - `hc_palette_untouched`: the computed `--jp-layout-color0` equals the value measured before
    Praxis CSS loaded. The harness reads it from a context with `praxis-theme.css` blocked.
- **AC-27 (colour-vision check)** [PY:test_display_colorblind.py]:
  - CIEDE2000(rose `#ED7A9B`, brick `#B3402A`) ≥ 10 under normal vision and under Machado
    2009 protanopia, deuteranopia and tritanopia at severity 1.0. The Machado matrices are
    inline constants with their source cited, and there are no new dependencies.
  - **Negative control**: the same function reports failure for `#ED7A9B` against `#E8789A`.
  - **Positive control**: black against white passes.
  - The test reports no numbers as findings. If a number is cited in a doc, it goes through
    bathos first.
- **AC-28 (glossary)** [PY:test_display_glossary.py]:
  - Every ledger and error action string equals a `glossary.ACTIONS` value.
  - A scan of `praxis/display/*.py` other than `glossary.py`, with comments and docstrings
    stripped, finds no literal from the table.

### Sprint C: deck panel

- **AC-29 (S4 recorded)**:
  - Same record checks as AC-1.
  - The note lists the stubs required (possibly none), `call_later` support, and the fixture
    `scene` bytes, and names the branch.
- **AC-30 (vendoring)** [PY:test_vendor_visualizer3d.py], plus
  `uv run python web-repl/scripts/vendor_visualizer3d.py --check --src <plr-main>`, which exits
  0 in CI after the PLR main checkout step C7 adds:
  - Every static file other than `index.html` has a sha256 equal to its source.
  - `index.html` has 0 `{{`, exactly one `socket.js` tag, positioned before the first
    `<script type="module"`, and exactly one `embed.js` tag before `</body>`.
  - 0 `https://` in `index.html`, and 0 `cdn.jsdelivr.net` in the whole vendored tree.
  - Both manifests record the source commit and every file.
  - The five `.py` files are byte-identical, and there are no `*_tests.py`.
  - Running the vendor script twice gives identical manifests.
- **AC-31 (DockedViewer3D)** [PY:test_viewer3d_docked.py], CPython, with a recording channel:
  - GATE X: `{n for n in vars(DockedViewer3D) if callable(getattr(Viewer3D, n, None))} == {"__init__", "start", "stop"}`.
  - With `websockets.serve`, `threading.Thread` and `webbrowser.open` monkeypatched to raise,
    `start()` succeeds.
  - An `open` from client X yields `accept`, then a `msg` whose `data` decodes to event
    `scene`, then `state`, all addressed to X only.
  - A `msg` hello (the shape from `transport.js:39-53`) appends to `clients_seen`.
  - `set_volume` on a well yields a `state` message after the loop turns.
  - `assign_child_resource` yields `scene` or `moves` after `SCENE_DEBOUNCE_S`.
  - `stop()` posts `close` and deregisters every callback (`_subscribed` empty).
  - `grep -c praxis_viz3d web-repl/overlay/assets/python/praxis/viz/viewer3d.py` ≥ 1, and the
    AC-18 R21 grep still exits 1 exactly.
- **AC-32 (socket shim)** [BUN]:
  - `readyState` goes `CONNECTING` → `OPEN` on `accept`.
  - `send` while `CONNECTING` throws a `DOMException`-named `InvalidStateError`.
  - `onclose` fires on kernel `close` and on no `accept` within 3 s (fake clock).
  - The statics equal `{0, 1, 2, 3}`.
  - Messages for another `client` or `viewer` are ignored.
  - `close()` posts `close` exactly once.
- **AC-33 (staging and offline)**:
  - [PY:test_display_staging.py] passes with the C6 paths.
  - After a build, `jq '.sources[].path' web-repl/dist/assets/wheels/manifest.json` lists
    `assets/python/plr_visualizer3d/server.py` and `assets/python/praxis/viz/viewer3d.py`.
  - [PY:test_contract_covers_imports.py] passes.
  - CI's `--probe --offline` gate stays green.
- **AC-34 (viewer draws in the deck panel)** [DOCK, scenario K1: 1440×900, Light theme]:
  - `panel_is_split_right`: per the S1 branch, the panel is a main-area widget whose left edge
    is at or right of the notebook's right edge.
  - `viewer_resources`: `plrViewer.resources()` includes the fixture's `assay`, `source` and
    `tips_300`.
  - `hello_backend in {"WebGL2", "WebGPU"}`, from the kernel's printed hello line.
  - `canvas_nonblank`: > 1% of the iframe viewport's screenshot pixels differ from `#EEF1F4`.
  - `embed_hidden`: `.navbar`, `#toolbar-left`, `#stats-panel`, `#sidepanel` and `#toolbar`
    are all `display: none` inside the iframe.
  - `pageerrors == []`, in both the parent and the iframe.
- **AC-35 (Follow and presets)** [DOCK, K1 continued]:
  - `click_focuses`: a real click on `source` in the deck output changes
    `plrViewer.camera().at`, and the footer reads "source".
  - `follow_focuses`: with Follow on, activating the assay output's cell focuses `assay`.
  - `follow_off_holds`: with Follow off, activating another cell leaves the camera unchanged.
  - `preset_directions`: after Top, Front and Iso,
    `normalize(camera.from - camera.at) · normalize(VIEWS[name]) > 0.99`. The VIEWS vectors
    are copied from `renderer.js:117-121` into the harness.
- **AC-36 (tiers)** [DOCK, scenario K2 across viewports]:
  - At 1600×900: `nb_content_width ≤ 960`, and the panel fills the remainder.
  - At 1440×900 and at 1280×800: `panel_width ∈ [420, 480]` after opening. After a real
    splitter drag to 300 px it is clamped to 420, and after a drag to 700 px, to 480.
  - At 1280×800: `viewer_height ≥ 300`, and `motion_slot_height ≤ 36`.
  - At 1152×800: `drawer_no_reflow`, meaning the notebook content width changes by 0 px when
    the drawer opens, and `drawer_overlays`, meaning the panel is `position: fixed`.
- **AC-37 (live state)** [DOCK, K1 continued]:
  - `state_updates`: after an aspirate cell,
    `plrViewer.stateOf(source.get_well("A1").name)` differs from its value before, within 5 s.
    The well name is read from the kernel, not hardcoded.
  - `stale_and_panel`: AC-23's notice text names the deck panel, and the panel is open.
- **AC-38 (reconnect and stop)** [DOCK, K1 continued]:
  - `reconnect_after_reload`: after the iframe reloads (the harness sets
    `iframe.src = iframe.src`), `resources()` repopulates within 10 s.
  - `stop_placeholder`: after `await viewer.stop()`, the placeholder text from section 3.6 is
    visible within 5 s.
  - `drawer_reconnect`: after crossing into the 1152 tier (the iframe moves), `resources()`
    repopulates within 10 s.
- **AC-39 (sensitivity and hygiene)**:
  - Copy the built dist to `/tmp/claude-1000/nd-neg/`.
  - (a) Remove `shell/display/index.js`, then run
    `--display-check --serve-dir /tmp/claude-1000/nd-neg`: it exits nonzero and names
    `rail_state_after_run`.
  - (b) On a fresh copy, remove `assets/visualizer3d-augmentations/socket.js`, then run
    `--dock-check`: it exits nonzero and names `viewer_resources`.
  - (c) `! grep -rnE '__praxis_test|data-praxis-test' web-repl/shell/display web-repl/overlay/assets/visualizer3d-augmentations --include='*.js' --exclude-dir=__tests__`
    finds nothing.
  - The observed exit codes go in the sprint C PR description. (a) is run first in sprint B's
    PR.
- **AC-40 (CI wiring)**:
  - `uv run python -m pytest web-repl/tests/test_repl_workflow_covers_tests.py -q` passes on
    each sprint's head.
  - `grep -c -- '--display-check' .github/workflows/repl.yml` ≥ 1 (sprint A).
  - `grep -c -- '--dock-check' .github/workflows/repl.yml` ≥ 1 (sprint C).
  - `grep -c 'bun test web-repl/shell/display' .github/workflows/repl.yml` ≥ 1 (sprint A).
- **AC-41 (no regressions, sprints B and C)**:
  - AC-8's list is green on each sprint's head.
  - R19: `test -d web-repl/overlay/assets/visualizer-augmentations`, then
    `grep -rnE 'requestDevice|requestPort' web-repl/overlay/assets/visualizer-augmentations/ web-repl/overlay/assets/visualizer3d-augmentations/ web-repl/shell/display/`
    exits **1 exactly**.

---

## 6. Fixer tasks

Every task is one session. TDD applies: the task's tests are written and seen failing for the
right reason before its implementation. **Closes** names the ACs its gate proves. A fixer
does not commit the orchestrator's files and does not merge. Merges are the owner's `--admin`
action (project memory, "praxis main merge policy").

### Sprint A: spikes, then chrome (merges alone)

**A1: Spike S1 (Lumino widget, split-right, size limits, cell-state hooks).** Write
`scripts/spikes/260929_s1_lumino_widget.py` and its sidecar, and commit both **before** the run
(D17).
- The probe builds on `run_notebook_check`'s launch and ServedDir pattern.
- It tries S1-A, then S1-B, adds the widget with `split-right` next to an open notebook, sets
  CSS limits, measures the widget after a splitter drag, and enumerates cell-state hooks for
  the five states.
- Run it with `bth run`, verify by record, and file the research note.
- Depends on: none (a built dist).
- Closes: AC-1.
- Gate: AC-1 record query.
- Size: ~250 LOC.

**A2: Spike S2 (sanitizer and untrusted mimetype).** Same discipline as A1, over
`260929_s2_sanitizer.py`. The crafted outputs cover every element and attribute in D1's S2
row. Include a bundle with both `text/html` and `text/plain`, and the D17 negative control.
- Depends on: none.
- Closes: AC-2.
- Gate: AC-2 record query.
- Size: ~220 LOC.

**A3: Spike S3 (IPython hooks in the Pyodide kernel).** Same discipline, over
`260929_s3_ipython_hooks.py`. Test (a)–(d), each in a plain cell and a top-level-`await` cell,
reading results from the notebook model.
- Depends on: none.
- Closes: AC-3.
- Gate: AC-3 record query.
- Size: ~200 LOC.

**A4: Theme CSS for chrome and outputs.** First write `web-repl/tests/test_display_css.py`
and see it fail. Then append the section 4 rules to `praxis-theme.css`:
- the rail keyed on S1's hooks or `data-praxis-cell-state`
- zero-width prompts
- the Light ground, sheet and syntax palette, confirming the `--jp-mirror-editor-*` token names
  against the bundled CSS in `dist/build/themes/`
- `.praxis-out` token mapping (D3)
- styles for the stale notice, error panel, readout, focus ring, and deck panel header and
  footer

Add the test's pytest line to the "Tests" step of `repl.yml`.
- Depends on: A1, because the rail selectors depend on S1.
- Closes: AC-4.
- Gate: [PY:test_display_css.py], [PY:test_theme_staging.py], and
  [PY:test_repl_workflow_covers_tests.py].
- Size: ~220 LOC.

**A5: Shell display skeleton and chrome module.** Create `shell/display/{index,chrome}.js`,
`__tests__/fakes.js` and `chrome.test.js`, writing the tests first. Append the loader IIFE to
`praxis-shell.js`. Add the `bun test web-repl/shell/display` step to the coxswain job in
`repl.yml`.
- Depends on: A1.
- Closes: AC-5.
- Gate: [BUN], and [PY:test_inject_shell_coxswain.py] still passing.
- Size: ~260 LOC.

**A6: Staging.** Extend `stage_shell` and `assert_dist_complete` (section 4, A6 row). Create
`test_display_staging.py` first, and add its `repl.yml` line.
- Depends on: none.
- Closes: AC-6.
- Gate: AC-6 commands, plus [PY:test_repl_workflow_covers_tests.py].
- Size: ~80 LOC.

**A7: `--display-check` harness and chrome scenario D1, plus CI wiring.** Add `--display-check`
and `run_display_check` to `repl_smoke.py`:
- seed the drive with `display_check.ipynb` (initially only the D1 cells)
- execute cells one at a time through the command registry
- read state from the model and computed styles
- add scenario D1

Then add the CI step
`uv run python scripts/repl_smoke.py --display-check --base-path /praxis/` after "Execute
welcome.ipynb", and run AC-39(a) against a copied dist.
- Depends on: A4, A5, A6.
- Closes: AC-7, AC-8, and AC-40 for its sprint A keys.
- Gate: interim, a local unsandboxed run on a fresh build per D16. Final: a green REPL
  workflow on the PR head.
- Size: ~260 LOC.

Sprint A order: A1, A2, A3 and A6 in parallel; then A4 and A5 (after A1); then A7.

### Sprint B: praxis.display (merges alone; needs AC-2 and AC-3 records)

**B1: Primitives, floor and budget.** Create `svg.py`, `floor.py` and `budget.py`, with
`test_display_floor.py` (the pure math cases) and `test_display_budget.py` (the ladder with a
fake renderer), tests first. Add both `repl.yml` lines.
- Depends on: none.
- Closes: the pure halves of AC-12 and AC-13.
- Gate: the two [PY] files.
- Size: ~260 LOC.

**B2: Labware reprs.** Create `labware.py`, and `test_display_labware.py` first:
- sentences
- well-range compression, with cases for a full column, a block, and scattered wells
- the grid descriptor
- the D2 bundle and stamp, with `rev` and `session` injected
- the S2 branch's attribute set: emit every attribute; the branch only changes what survives
  on reopen

Add the test's `repl.yml` line.
- Depends on: B1.
- Closes: AC-9, AC-10.
- Gate: [PY:test_display_labware.py].
- Size: ~320 LOC.

**B3: Deck repr.** Create `deck.py`, and `test_display_deck.py` first, including the 384-,
1536- and oversize cases for AC-12 and AC-13. Add its `repl.yml` line.
- Depends on: B2.
- Closes: AC-11, and AC-12 and AC-13 in full.
- Gate: [PY:test_display_deck.py], [PY:test_display_floor.py], [PY:test_display_budget.py].
- Size: ~300 LOC.

**B4: Glossary and RunLedger.** Create `glossary.py` and `ledger.py`, with
`test_display_ledger.py` and `test_display_glossary.py` first. Add their `repl.yml` lines.
- Depends on: B2.
- Closes: AC-14, AC-28.
- Gate: the two [PY] files.
- Size: ~300 LOC.

**B5: Error context.** Create `context.py`, and `test_display_context.py` first: cases E1–E8
and both negatives, using real PLR at the pin. Add its `repl.yml` line.
- Depends on: none.
- Closes: AC-15.
- Gate: [PY:test_display_context.py].
- Size: ~220 LOC.

**B6: Error panel and handler.** Create `errors.py`, and `test_display_errors.py` first.
Implement the handler per D8, using S3-A or the S3-C fallback as recorded in AC-3. Add its
`repl.yml` line.
- Depends on: B2, B4 (glossary), B5.
- Closes: AC-16.
- Gate: [PY:test_display_errors.py].
- Size: ~260 LOC.

**B7: Staleness, kernel side.** Create `stale.py`, and `test_display_stale.py` first. Use an
injected poster, with `import js` only in `make_repl_poster()`. Add its `repl.yml` line.
- Depends on: B2.
- Closes: AC-18.
- Gate: [PY:test_display_stale.py], plus the R21 grep.
- Size: ~200 LOC.

**B8: Install and bootstrap stage.** Create `install.py` and `praxis/display/__init__.py`, and
`test_display_install.py` first. It covers the fake shell and the S3-B, S3-C and S3-D
fallbacks. Add the D13 stage to `praxis_bootstrap.py`, and extend
`test_praxis_bootstrap_loader.py` for its order and its non-fatal failure. Add the `repl.yml`
line. Extend `assert_dist_complete` with `assets/python/praxis/display/__init__.py`.
- Depends on: B2, B3, B4, B6, B7.
- Closes: AC-17, AC-20, and the colour half of AC-27. The colour-vision test file is created
  here, test first, with its line added.
- Gate: [PY:test_display_install.py], [PY:test_praxis_bootstrap_loader.py],
  [PY:test_display_colorblind.py].
- Size: ~220 LOC.

**B9: Shell stale and interaction.** Create `shell/display/stale.js` and `interact.js`, with
their bun tests first. Mount them from `index.js`. Extend staging (`build_repl.py` required
list, `test_display_staging.py`).
- Depends on: A5, B7 (message schema).
- Closes: AC-19.
- Gate: [BUN], [PY:test_display_staging.py].
- Size: ~320 LOC.

**B10: `--display-check` scenarios D2–D4.** Extend the fixture notebook and
`run_display_check` for AC-21 to AC-26. D3 asserts the S2 branch named in AC-2. Run AC-39(a).
- Depends on: B8, B9.
- Closes: AC-21 to AC-26 (CI), and AC-41 for sprint B.
- Gate: interim, a local unsandboxed run (D16). Final: a green REPL workflow on the PR head.
- Size: ~300 LOC.

Sprint B order: B1 and B5 in parallel; B2; then B3, B4 and B7 in parallel; B6; B8; B9, which
can start after B7; then B10.

### Sprint C: Visualizer3D deck panel (merges alone; needs the AC-1 branch to be S1-A or S1-B)

**C1: Spike S4 (Viewer3D in Pyodide).** Discipline as in A1. The probe stages a throwaway copy
of the five vendored files. It does not wait for C2. It records D1's S4 questions and the
scene bytes.
- Depends on: none.
- Closes: AC-29.
- Gate: AC-29 record query.
- Size: ~180 LOC.

**C2: Vendoring script and committed trees.** First write `test_vendor_visualizer3d.py` over a
tiny synthetic source tree (anchors, placeholders, tag positions, sha identity, and a
mismatch that must fail with context). Then write `vendor_visualizer3d.py`, run it against a
PLR main checkout **at a named commit** (the #1378 merge or later, recorded in both
manifests), and commit the two generated trees. Add the `repl.yml` line. The `--check` step
and the PLR main checkout step land in C7.
- Depends on: none.
- Closes: AC-30 (local).
- Gate: [PY:test_vendor_visualizer3d.py], and `vendor_visualizer3d.py --check` exits 0
  locally.
- Size: ~300 LOC, plus the generated trees.

**C3: DockedViewer3D.** Write `test_viewer3d_docked.py` first, then `viewer3d.py`:
- the three overrides, `VirtualConnection`, the injected channel, and `dock()`
- any S4-B stubs, installed before the vendored import, each named in a module constant and
  asserted by the test

Add the test's `repl.yml` line. If the tests need `websockets.asyncio.server` in the root env
and it is missing, stop and report; do not vendor it.
- Depends on: C1 (the branch), C2.
- Closes: AC-31.
- Gate: [PY:test_viewer3d_docked.py], plus the R21 grep.
- Size: ~260 LOC.

**C4: Socket shim and embed mode.** Write `viz3d_socket.test.js` first, then `socket.js`,
`embed.js` and `embed.css` (D11, D12).
- Depends on: C2 (tag positions).
- Closes: AC-32.
- Gate: [BUN].
- Size: ~220 LOC.

**C5: Deck panel widget.** Create `shell/display/dock.js` and its bun tests (a fake app shell
and signals), tests first:
- the widget per the S1 branch
- the header, footer, motion slot, tiers and drawer
- Follow, click-to-focus wiring from `interact.js`, presets, the placeholder, and
  `praxis:toggle-deck-panel`
- `announce` listening on `praxis_viz3d`

Mount it from `index.js`.
- Depends on: A5, B9, C4, and AC-1 branch S1-A or S1-B. On S1-C, stop and escalate (D1).
- Closes: the unit half of AC-35 and AC-36.
- Gate: [BUN].
- Size: ~340 LOC.

**C6: Staging and offline.** Add the C6 paths to `assert_dist_complete` and to
`test_display_staging.py`. Confirm that manifest collection picks up the vendored Python.
- Depends on: C2, C3, C4, C5.
- Closes: AC-33 (local parts).
- Gate: [PY:test_display_staging.py], [PY:test_contract_covers_imports.py], and a build.
- Size: ~60 LOC.

**C7: `--dock-check` gate and CI wiring.** Add `run_dock_check` with scenarios K1 and K2
(AC-34 to AC-38), using the full-Chromium launch and SwiftShader args (D16). Add to CI:
- a step that checks out PLR main at C2's recorded commit into a temporary directory, followed
  by `vendor_visualizer3d.py --check --src <dir>`
- the `--dock-check` step

Run AC-39(b) and (c).
- Depends on: C6.
- Closes: AC-30 (CI), AC-33 (CI), AC-34 to AC-39, AC-40 for its sprint C key, and AC-41 for
  sprint C.
- Gate: interim, a local unsandboxed run (D16). Final: a green REPL workflow on the PR head.
- Size: ~320 LOC.

Sprint C order: C1 and C2 in parallel; C3 and C4; C5; C6; C7.

| Task | Sprint | Scope | Depends on | Closes |
|---|---|---|---|---|
| A1 | A | S1 spike | none | AC-1 |
| A2 | A | S2 spike | none | AC-2 |
| A3 | A | S3 spike | none | AC-3 |
| A4 | A | theme CSS + CSS test | A1 | AC-4 |
| A5 | A | shell display skeleton, chrome.js, loader | A1 | AC-5 |
| A6 | A | staging | none | AC-6 |
| A7 | A | `--display-check` D1 + CI | A4, A5, A6 | AC-7, AC-8, AC-40 (A) |
| B1 | B | svg, floor, budget | none | AC-12/13 (pure) |
| B2 | B | labware reprs | B1 | AC-9, AC-10 |
| B3 | B | deck repr | B2 | AC-11, AC-12, AC-13 |
| B4 | B | glossary + RunLedger | B2 | AC-14, AC-28 |
| B5 | B | error context | none | AC-15 |
| B6 | B | error panel + handler | B2, B4, B5 | AC-16 |
| B7 | B | staleness (kernel) | B2 | AC-18 |
| B8 | B | install + bootstrap stage + colour test | B2, B3, B4, B6, B7 | AC-17, AC-20, AC-27 |
| B9 | B | shell stale + interaction | A5, B7 | AC-19 |
| B10 | B | `--display-check` D2–D4 | B8, B9 | AC-21 to AC-26, AC-41 (B) |
| C1 | C | S4 spike | none | AC-29 |
| C2 | C | vendoring + trees | none | AC-30 (local) |
| C3 | C | DockedViewer3D | C1, C2 | AC-31 |
| C4 | C | socket shim + embed | C2 | AC-32 |
| C5 | C | deck panel widget | A5, B9, C4, S1-A/B | AC-35/36 (unit) |
| C6 | C | staging + offline | C2–C5 | AC-33 (local) |
| C7 | C | `--dock-check` + CI | C6 | AC-30, AC-33 to AC-40 (C), AC-41 (C) |

---

## 7. Risks

| Risk | Mitigation / rollback |
|---|---|
| S1-C: no widget constructor is reachable without a labextension | D1 stops C5 and escalates to the user, who decided "a real widget". Sprints A and B do not depend on the widget and still merge. |
| The sanitizer strips SVG, `class` or `style` on reopened notebooks | Resolved by design (D1, S2 branches). Live outputs are unaffected, and reopened ones degrade to stated states. AC-24 asserts the recorded branch, so the degradation cannot be silent. |
| The Pyodide kernel's execution path ignores `set_custom_exc` | S3-C falls back to an instance-level `showtraceback` wrapper. If that also fails, B6 stops and MVP item 3 is escalated. |
| Frame-local names in PLR (`op`, `channel`, `resources`) change on a pin bump | Owner resolution is by **identity** first and `thing` second. Frame locals are used only for the loop channel and op wells. AC-15 runs against the real pin, so a bump that breaks it fails CI. |
| A PLR mid-loop tracker error leaves pending volumes on earlier channels, so drawings mislead | The error panel draws committed volume (D8), and AC-16 forces the case. Other outputs follow PLR's own `get_used_volume()`. OQ-6 raises it upstream. |
| `RunLedger` instance shadowing breaks a user's own wrapper on `lh` | It shadows only inside the `with` block, restores on exit even on error (AC-14), and is only used when the user writes it. |
| Staleness announcements on `praxis_repl` disturb device authorization | At most one small typed message per cell (4 KiB cap). Both existing listeners ignore unknown types (`praxis-shell.js:84-88`, `praxis_bootstrap.py:212-214`). R21's grep still guards `praxis/viz/`. Rollback: move `stale.py` to its own channel; the shell change is one constant. |
| Viewer3D stream messages are structured-cloned to every `praxis_viz3d` listener, including the shell | The shell listens only for `announce` and `close`. The clone cost of a scene message is unmeasured; S4 records the scene bytes. If it matters, the announcements move to a separate small channel. |
| Two notebooks each start a viewer | Non-goal. The ids in the protocol keep messages unambiguous, and the most recent `announce` wins. |
| Vendored three.js tree (~2 MB) grows dist and the offline gate | AC-30 asserts zero CDN URLs, and AC-33 keeps `--probe --offline` green. The build logs the size. |
| The PLR main source drifts from the vendored copy | `--check` in CI against the pinned commit (C7). Updating is an explicit re-vendor with a new commit in both manifests. |
| The CI Chromium lacks WebGL2 | D16's full Chromium with SwiftShader args. AC-34 records `hello_backend`, and the canvas check fails loudly rather than passing on a blank frame. |
| Moving the iframe for the drawer tier reloads it | The shim reconnects, and AC-38 `drawer_reconnect` tests it. |
| A Lumino split ignores CSS min/max | S1 records the fact, and `dock.js` clamps through `setRelativeSizes`. AC-36 drags the splitter for real. |
| The detail-floor math is wrong in the browser because CSS scales SVGs | D5 puts an explicit `min-width` on each SVG, and AC-12 checks the math. Rendered sizes are a human check (H1). If S2-A' strips `style`, the floor holds only for live outputs (stated). |
| The display layer throws at boot | D13 makes it non-fatal and loud (`praxis:display-error`). AC-20 tests both paths. |
| The notebook-check gate trips on the new error rendering | `welcome.ipynb` raises no PLR error. The error cases live only in `display_check.ipynb`. |
| Merge conflicts in `praxis-shell.js` with other appenders (persistence, P5.6) | One appended IIFE. Rollback reverts the IIFE, and the rest is inert. |
| Rollback overall | Each sprint adds files and migrates no data. There are no new storage keys. Reverting a sprint's PR removes its behaviour, and saved notebooks keep valid `text/plain` outputs. |

---

## 8. Open questions (user; non-blocking unless marked)

- **OQ-1.** Should the REPL's default theme change from JupyterLab Dark (`jupyter-lite.json:18`)
  to Light, where the design is complete? The default is no (D10).
- **OQ-2.** At PLR 0.2.2 no liquid identity is tracked (D15). Is "volume only" acceptable for
  the MVP? Identity would return when PLR records it.
- **OQ-3.** The 1024–1279 drawer is built and gated functionally. Are human quality checks at
  ≥ 1280 only acceptable, as "MVP targets ≥ 1280" suggests?
- **OQ-4.** At ≥ 1600 px the deck panel takes "the rest", which is unbounded. Is a maximum
  wanted, for example 720 px?
- **OQ-5.** The 3D selection keeps the page's own blue, transient box (D12). Should a request
  go to PLR upstream for a persistent, colourable highlight API?
- **OQ-6.** At the pin, a tracker error mid-loop leaves earlier channels with uncommitted
  pending state (`liquid_handler.py:1031-1035`, `:533-538`, `:677-684`). Should this be
  reported upstream?
- **OQ-7.** Is the PLR main commit to vendor the #1378 merge commit, or the newest main at C2
  time? The spec requires only a named commit recorded in both manifests. *Orchestrator,
  260929:* the 56-file `pylabrobot/visualizer3D/` tree that was fetched and measured matches
  PLR main `786ac2c4e4f7afe37885af2d98ff5b0afe274c67` blob for blob (the `git/trees`
  listing was compared by sha256). That is the commit the 260929 WebGL2 measurement used.
- **OQ-8.** Is an automatic ledger for every liquid-moving cell wanted after MVP? It would
  need a capture mechanism that D9 rejected for now.
- **OQ-9.** If S2 lands on S2-C (`text/plain` for untrusted), is a labextension later worth
  its build toolchain? The ADR and theme header currently reject one.

## 9. Residual human checks (not autonomous ACs)

- **H1.** Compare outputs against `shots/desktop-full.png` and `shots/error-output.png` at
  1280 and 1600 px in Light. Judge the rendered text and well sizes against the floor by eye.
- **H2.** Open a saved notebook on GitHub and in VS Code, and in print preview. Confirm that it
  is legible with no Praxis CSS.
- **H3.** On a real GPU browser (Chrome, Edge), run the deck panel on a full STAR deck: frame
  rate, and the time to the first scene.
- **H4.** Run a screen reader (NVDA or VoiceOver) over a plate figure: the summary sentence, and
  keyboard navigation announcements.
- **H5.** A colour-vision simulator or user check of rose against brick in context: the
  selection outline next to fault marks.
- **H6.** A lab scientist reads the error-panel and ledger wording against the glossary.

## References

- Design and user decisions: `web-repl/design/notebook-display/DESIGN.md` (MVP and Next
  lists); the reference renderer `display.js:53-86` (plate and tip drawing), `:125-198`
  (deck), `:209-230` (sentences), `:256-300` (ledger and error); the fixture generator
  `make_fixture.py:39-107`; screenshots `shots/*.png`.
- Format precedent: `.praxia/docs/specs/260922_repl-persistence-ladder.md` (copy at
  `/tmp/claude-1000/persist_spec.md`).
- ADR: `.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md` §2.1 (tree),
  §2.3 (D1/D2 manifest), §2.4 (namespace; no `sys.path` append), §5.5 (served paths and
  storage names).
- Visualizer transport spec R19/R21: `.praxia/docs/specs/260817_spec-visualizer-transport-shim.md:335-343`.
- Existing patterns:
  - `web-repl/overlay/assets/python/praxis/viz/browser.py:18-20` (GATE X), `:179-192`
    (sole `import js`)
  - `transport.py:10-18` (channel separation, origin scope)
  - `visualizer-augmentations/index.js` (augmentation, queueing)
  - `web-repl/scripts/vendor_visualizer.py` (anchors, placeholders, manifest)
  - `build_repl.py:830-895` (shell staging), `:979-1047` (`assert_dist_complete`)
  - `praxis_bootstrap.py:289-398` (stage ledger)
  - `praxis-shell.js:54-105` (channel listener)
  - `scripts/repl_smoke.py:101-184` (Chromium resolution, launch args), `:1226-1430`
    (`run_notebook_check`)
  - `.github/workflows/repl.yml:146-226`
- PLR main Visualizer3D (`/tmp/claude-1000/plr-main/pylabrobot/visualizer3D/`):
  - `server.py:155` (class), `:353` (`_broadcast`), `:559-603` (hello and `_handler`),
    `:711-783` (`__init__`), `:785-811` (`start`), `:829-850` (`stop`)
  - `static/transport.js:56-93`, `static/index.html:319-339`, `static/app.js:172-223`
    (`window.plrViewer`), `static/renderer.js:117-121, 261-264`, `static/constants.js:118-121`
- PLR 0.2.2 (`external/pylabrobot`, `dd79c4c89`):
  - `resources/errors.py:8-22`
  - `resources/volume_tracker.py:88-143`
  - `resources/tip_tracker.py:57-110`
  - `resources/container.py:85`, `resources/tip_rack.py:52`, `resources/well.py:19-28`
  - `resources/resource.py:806-934`
  - `liquid_handling/liquid_handler.py:197, 411-424, 489-576, 637-684, 878-1067`
  - `pylabrobot/__init__.py:67-118`
- Upstream: PyLabRobot #1378 (Visualizer3D, merged 2026-09-27); PLR #1308 (Petri dishes, Next);
  `stefangolas/pylabrobot@viz3d-motion` (unmerged, slot only).
