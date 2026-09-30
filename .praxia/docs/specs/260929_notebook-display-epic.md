---
title: 'Notebook display epic: rich PLR outputs, quieter chrome, Visualizer3D deck panel (web-repl)'
description: Epic spec for the web-REPL notebook display. Three sprints (A spikes + chrome, B praxis.display reprs/ledger/errors/staleness, C Visualizer3D deck panel). Four spikes (S1-S4) run first, and every downstream decision states its behaviour under each spike outcome.
status: active
task_id: 260929_notebook-display-design
date: '260929'
adversarial_review: 'round1 challenger REVISE (2 BLOCKER / 13 MAJOR / 14 MINOR) / defender REVISE (A-1..A-20) -> revised 260929 (Revision 1); round2 challenger REVISE (2 BLOCKER / 7 MAJOR / 3 MINOR; all round1 CLOSED) / defender REVISE (B-1..B-12) -> revised 260929 (Revision 2); round3 challenger REVISE (2 MAJOR / 2 MINOR; all round2 CLOSED; both MAJORs verified against PLR 0.2.2) -> revised 260929 (Revision 3); round4 challenger REVISE (2 MAJOR / 2 MINOR; all round3 CLOSED) -> revised 260929 (Revision 4, orchestrator); round5 challenger REVISE (1 MAJOR / 3 MINOR; C4-1, C4-3 CLOSED, C4-2 partial) -> revised 260929 (Revision 5, orchestrator); round6 challenger REVISE (1 MAJOR / 1 MINOR) -> revised 260929 (Revision 6: deck panel state machine); round7 challenger REVISE (2 MAJOR vs user preemption rule / 6 MINOR / 1 SUGGESTION; state machine sound) -> revised 260929 (Revision 7); round8 challenger REVISE (2 MAJOR / 5 MINOR; resume design otherwise sound) -> revised 260929 (Revision 8); round9 challenger REVISE (1 MAJOR / 5 MINOR) -> revised 260929 (Revision 9); round10 challenger ACCEPT (0 BLOCKER / 0 MAJOR; 4 MINOR for the sprint) -> CONVERGED 260929; Revision 10 (PLR 1.0 pin + runner corrections) 260929; round11 challenger REVISE (1 BLOCKER / 3 MAJOR / 11 MINOR) -> Revision 11 (round 11 fixes) 260929, challenger round 12 pending; round12 challenger CONVERGED 260929 (0 BLOCKER / 0 MAJOR / 5 MINOR, sprint notes)'
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
- **Deck panel.** PLR's `Visualizer3D` (PyLabRobot #1378, BioCam / Camillo Moschner,
  merged 2026-09-27; shipped in the 1.0.0b1 pin as `pylabrobot.visualizer3D`) runs in a
  JupyterLab main-area split beside the notebook, in an embed mode, and follows the cell you
  are working in.

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
- The pinned PLR **1.0.0b1** (`external/pylabrobot`, `786ac2c4e4f7afe37885af2d98ff5b0afe274c67`,
  pinned on `origin/main` by `a176bac7`, PR #184 "plr-1.0-bump") for error sites, tracker
  behaviour and `pylabrobot/visualizer3D/`. That commit is the same one the spec first fetched
  as "PLR main" to `/tmp/claude-1000/plr-main/pylabrobot/visualizer3D/` (OQ-7, resolved). The
  spec was first written against the earlier pin 0.2.2 (`dd79c4c89`); Revision 10 re-checked
  every PLR-dependent claim against 1.0.0b1
  (`.praxia/docs/research/260929_notebook-display-plr10-premises.md`, "the PLR 1.0 recon"
  below; exploratory, not pre-registered: the AC-15/16 test files re-verify it).
- **PLR line anchors.** Unless a reference says otherwise, a PLR anchor is at the 1.0.0b1 pin,
  and `LH` means `pylabrobot/legacy/liquid_handling/liquid_handler.py`. An anchor marked
  "(0.2.2)" is historical and was not re-checked by the recon.

**Base.** File references below are to branch `design/notebook-display` at `fd987728`. That
branch predates the persistence ladder (`.praxia/docs/specs/260922_repl-persistence-ladder.md`),
which also appends an IIFE to `praxis-shell.js`, extends `stage_shell`, adds
`test_repl_workflow_covers_tests.py` and adds a `--persistence-check` gate. Every sprint branches
from `origin/main`, not from the design branch. Where this spec says "append", it means after
whatever IIFEs `main` already carries. Where a reference says "on origin/main a176bac7", the
line number was read at that commit (the PLR 1.0 recon).

---

## 1. Decisions (read first)

### D1. Four spikes run first. The downstream design is correct under every outcome.

Four facts that the design depends on cannot be read from source in this repo. Each becomes a
pre-registered spike (D17). Each sprint that depends on a spike names the branch it builds.

| Spike | Question | Branches and what the downstream design does |
|---|---|---|
| **S1** (sprint A) | Can a plain script, with no labextension build, construct a Lumino `Widget` and add it with `app.shell.add(w, 'main', {mode: 'split-right', ref})`? Does Lumino honour CSS `min-width`/`max-width` on the widget node? Which DOM hooks or model signals give each cell's state (not run, ran, running, error, edited since run)? | **S1-A**: walk the prototype chain of an existing shell widget to the root class. Identify it structurally: its prototype owns `processMessage` and `onAfterAttach`, and its own prototype is `Object.prototype`. `new Ctor({node})` then gives the deck panel as a real widget. **S1-B**: A fails, but a stock command (candidate `help:open`) creates a main-area iframe widget, its iframe allows scripts and same-origin, and it can be re-added with `split-right`. The deck panel then re-homes that widget and replaces its content. **S1-C**: both fail. **Stop** sprint C task C5 and escalate: the user's decision (a real JupyterLab widget) cannot be met without a labextension. The degraded option offered to the user is a shell-owned fixed panel with `#main` narrowed by CSS. Size limits (a second, independent axis): if CSS limits are honoured, use them. Otherwise the shell sizes through the main DockPanel's layout: `saveLayout()`, edit the split area's `sizes`, then `restoreLayout()` (a main-area `split-right` lives in a `DockLayout`, which has no `setRelativeSizes`). S1 records `css_limits_honoured`, `dock_layout_sizing_reachable` and `css_limits_refit` (whether Lumino re-reads a widget's CSS `min-width`/`max-width` after `parent.fit()`). S1 also records `restore_layout_keeps_iframe`: whether `restoreLayout()` keeps an iframe in the widget loaded, so that a layout-sizing clamp causes no reload. If it is `false`, layout sizing is used only at open and on tier changes (one reload each, like a drawer move), never for `ResizeObserver` or drag clamps; for those the row is read as if layout sizing were unreachable (CSS or inline px where honoured, otherwise recorded-only). *(Round 4, C4-2.)* The combination selects one row of the D6 sizing-case table, which fixes, per AC-36 width key, the mechanism or the recorded-only status. **S1-L**: neither CSS limits nor layout sizing works. The split opens at Lumino's own size, the drag is unclamped, and **every** AC-36 width key is recorded-only (the drawer and height keys stay asserted). This is a stated deviation, accepted per the user's 260929 ruling "split initially. we can figure out a more ergonomic layout later." Cell state: each state uses a CSS hook where one exists. Otherwise `chrome.js` computes it from model signals and writes `data-praxis-cell-state` on the cell node. S1 also records the notebook's `windowingMode` and the signal that fires when a virtualised cell's DOM is re-attached (used by D7 marking). |
| **S2** (sprint A) | For a notebook reopened untrusted in our JupyterLite build, which mimetype does JupyterLab choose from `{text/html, text/plain}`? What does its sanitizer keep of our HTML and SVG? The spike tests elements `svg g path rect text title details summary table`; attributes `fill stroke stroke-width stroke-dasharray class style role aria-label tabindex data-*`; and `viewBox`. S2 probes two reopen paths and records the trust state and chosen mimetype of each: a **crafted** notebook written to the drive (never executed, so untrusted; this also stands for download/upload), and a notebook **executed, saved and reopened** in the same browser. | **S2-T**: the executed-saved-reopened notebook reopens **trusted**. It renders as live, and the branches below then apply only to the crafted path. **S2-A**: `text/html` is chosen and SVG survives with `class`. Full design, with token-mapped CSS (D3) applied to reopened outputs. **S2-A'**: SVG survives, but `class` and/or `style` are stripped. Reopened outputs keep their inline light palette (D3) and scale freely without the D5 `min-width` until re-run. Accepted and stated. **S2-B**: SVG is stripped, but `text/html` is still chosen. Reopened outputs show name line, sentence, ledger table and error text, with no drawings until re-run. Accepted: "survives trust loss" is met by the text. **S2-C**: `text/plain` is chosen. Reopened outputs show the summary sentence. Accepted; OQ-9 asks whether a labextension is wanted later. **In every branch the live output format is identical (D2).** Interaction on reopened outputs (hover, keyboard, click to focus) works only if `data-*` and `tabindex` survive. If they are stripped, it returns when the cell is re-run. |
| **S3** (sprint A) | In the JupyterLite Pyodide kernel (`pyodide_kernel-0.8.2`; IPython 9.12.0 per the cached `pyodide-lock.json`), four things, (b) with a variant (b′): (a) Is `get_ipython()` non-None? (b) Does `display_formatter.mimebundle_formatter.for_type(cls, fn)` work, with `fn` returning `(data, metadata)`? (b′) Does `display_formatter.formatters['text/html'].for_type(cls, fn)`, with `fn` returning `(html, {"praxis": stamp})`, put the stamp at the output's `metadata["text/html"]["praxis"]`? (IPython `core/formatters.py:243-250` unpacks a per-type `(data, metadata)` return into `md_dict[format_type]`; verified by the orchestrator on 9.13.0, 260929.) (c) Is a `set_custom_exc` handler invoked for an exception raised in a plain cell **and** in a top-level-`await` cell? Does `display()` inside the handler emit, does the returned structured traceback become the cell's `error` output, and does Run All stop? (d) Does `events.register('post_run_cell', cb)` fire? | **S3-A**: all yes. Design as written. **S3-B**: (b) fails and (b′) holds. Register `text/html` and `text/plain` separately via `formatters[...].for_type`; the `text/html` function returns `(html, {"praxis": stamp})`, so the D7 stamp is carried at `metadata["text/html"]["praxis"]`. Every reader goes through one accessor, `stampOf` (D2), so staleness, Follow and AC-21 behave identically under S3-A and S3-B. A DOM-attribute carrier is rejected: S2 may strip `data-*`. If (b′) also fails, **stop** B7 and B9 and escalate. **S3-C**: (c) fails. Wrap the kernel shell **instance's** `showtraceback`: an instance attribute that handles the four classes and delegates everything else. PLR and IPython classes are not modified. If that is also not honoured, stop B6 and escalate (MVP item 3 cannot be met). **S3-D**: (d) fails. The kernel announces from PLR state-update callbacks, debounced with `loop.call_later(0.1, ...)`. |
| **S4** (sprint C) | Does the pin's `pylabrobot.visualizer3D` package, which the REPL's PLR wheel already contains, import in the Pyodide kernel, with `websockets` (17.0.1) from its vendored wheel (Revision 10; the PLR 1.0 recon)? Check `http.server`, `webbrowser`, `socket.gethostname()`, `websockets.asyncio.server` and `websockets.http11`. Does `DockedViewer3D(deck)` construct and `start()` without threads? Does WebLoop support `call_later` and `call_soon_threadsafe` as the viewer uses them? How many bytes is the fixture deck's first `scene` message? What does the stock `pylabrobot.visualizer3D.server.PACKAGE_ROOT` resolve to in the kernel (expected: inside the installed PLR package in site-packages, which at the pin ships 63 `.glb` model files; the PLR 1.0 recon), and what is it after `viewer3d.py`'s rebind (D11)? How long does the first `_models_on_disk(PACKAGE_ROOT)` walk take over the rebound root (it is no longer pre-warmed by `start`; its first call is the inherited scene build, `server.py:417`)? | **S4-A**: all yes. Design as written. **S4-B**: a stdlib import or `gethostname` fails. `praxis/viz/viewer3d.py` installs minimal named stubs into `sys.modules` **before** importing `pylabrobot.visualizer3D`, the same mechanism `stages.install_native_stubs` uses. Each stub is listed and tested. No PLR file is modified. **S4-C**: WebLoop lacks `call_later`. Making it work would need a fourth override (`_mark_scene_dirty`), which trips GATE X (D11). **Stop** and escalate. The recommended path is to upstream a transport hook to PLR. |

S1, S2 and S3 are sprint A tasks A1–A3. S4 is sprint C task C1. No task downstream of a spike
starts until that spike's record exists (AC-1..AC-3, AC-29).

### D2. One mimebundle per resource. No `<script>`, no `<style>`, no `image/svg+xml`.

Each rendered PLR object produces one bundle:

- `text/html`: self-contained HTML with inline SVG. There is no `<script>` and no `<style>`
  element. All interaction comes from the shell script (D14).
- `text/plain`: the summary sentence (section 3.2). This is what any viewer that drops HTML
  shows.
- `metadata["praxis"]`: `{"v": 1, "kind": "plate|tiprack|container|deck|ledger|error",
  "resource": <name|null>, "rev": <int|null>, "session": "<display session id>", "exec": <int|null>}`.
  This stamp is JSON, not HTML, so no sanitizer can strip it (D7).
  - The **display session id** is random, minted once per kernel process by
    `praxis.display.install()`. This spec uses that one term everywhere.
  - `exec` is `get_ipython().execution_count` at render time: the cell that drew the output.
  - **Values by kind** (Revision 2):
    - `plate`, `tiprack`, `container`, `deck`: `resource` is the drawn resource's name and
      `rev` its current rev (D7).
    - `ledger`: `resource: null`, `rev: null`.
    - `error`: `resource` is the labware the panel is about (plate, container or tip rack),
      or `null` when the owner is a channel (including a tip on a channel) or the panel is the
      generic one; `rev: null`.
  - Outputs with `rev: null` are historical and are never marked "Changed since" (D7). Follow
    skips outputs with `resource: null` (D12).

Registration uses `get_ipython().display_formatter.mimebundle_formatter.for_type(cls, fn)`,
where `fn` returns `(data, metadata)`. Under S3-B, `text/html` and `text/plain` are registered
separately and the stamp rides at `metadata["text/html"]["praxis"]` (D1, S3(b′)).

**One stamp reader.** Every consumer reads the stamp through one accessor,
`stampOf(output) = output.metadata?.praxis ?? output.metadata?.["text/html"]?.praxis`. It is
exported from `shell/display/stale.js`, imported by `dock.js`, and the `--display-check` and
`--dock-check` harnesses evaluate the same expression. No other code reads
`metadata.praxis` directly. The registered classes are
`Plate`, `TipRack`, `Deck` and `Container`, with IPython resolving subclasses by MRO (at the
pin `tips_300` is an `EmbeddedTipRack`, a `TipRack` subclass, so it resolves to the `TipRack`
formatter; no code dispatches on a type-name string). PLR defines no IPython display hook
(`_repr_html_` or any other `_repr_<name>_`), so a registered formatter shadows nothing. At
0.2.2 that was recorded as "0 hits" by an earlier recon whose pattern is not preserved here;
it was **not** the BRE `'_repr_html_\|_repr_[a-z]*_'` that Revision 10 put in B2's gate,
because that pattern's `[a-z]*` may match empty, so it matches every `__repr__` and gives 15
hits at the 1.0.0b1 pin (for example `resources/resource.py:273`, `legacy/tip_tracker.py:217`;
round 11, C11-1). The gate is the ERE
`grep -rnE '(^|[^_])_repr_[a-z]+_' external/pylabrobot/pylabrobot --include='*.py'`, which
must exit **1** (no match): the `(^|[^_])` prefix excludes `__repr__`, and `[a-z]+` needs at
least one letter. The orchestrator ran it on the 1.0.0b1 wheel copy (260929): 0 hits, and 0
real `_repr_*_` hooks. B2 runs it at the pin as part of its gate (any other exit, B2 stops and
reports). PLR is never patched.

**MVP figures** are `Plate`, `TipRack`, `Deck` and `Well`. Every other `Container` subclass
(Trough, Tube, PetriDish, Trash, ...) gets the name line and the sentence only, with
`kind="container"` and no drawing (section 3.2). Their figures are Next ("More labware").

**Escaping.** Resource names and every other interpolated string are user-controlled, and live
outputs are trusted HTML.
- `svg.py` owns `esc_text` and `esc_attr` (both `html.escape(s, quote=True)`). Every
  interpolated string in text or an attribute goes through one of them.
- `data-praxis-grid` is `esc_attr(json.dumps(...))`.
- The traceback is `traceback.format_exception(...)` (plain text, no ANSI), then escaped.
- The shell never builds a CSS selector from a name. It matches with
  `el.dataset.praxisRes === name` (D14).

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
  **not measured**. The tests measure them. A missed target is revised only with the
  orchestrator's approval, recorded with its reason in the sprint PR. The fixer does not edit
  targets.
- **Everything counts.** The 64 KiB cap covers the whole `text/html`: the SVG, the
  `data-praxis-grid` descriptors, the ledger table and an error panel's traceback.
- **Traceback cap.** An error panel's traceback is capped at **16 KiB**. The tail is kept and
  the head is replaced by one line, "… N earlier lines omitted".
- **Degradation ladder** when a render would exceed the cap, in order (the drawing always
  degrades first; text is never dropped to save a drawing):
  1. every labware drawn as a filled block, and `data-praxis-grid` dropped for blocked
     labware
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
- `s_min` is the smallest scale the figure may be rendered at. At `s_min` a label renders at
  `12.5 · s_min / s_n` px, so the text floor needs `s_min ≥ 0.88 · s_n` (0.88 = 11/12.5) for
  **every** figure, the deck included:
  - single labware: `s_min = max(0.88 · s_n, 4 / d_min)`, where `d_min` is the smallest drawn
    well or tip diameter in mm
  - deck: `s_min = max(0.88 · s_n, 0.6)`

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
  - Each labware is drawn in full detail if `d_min · s_min ≥ 4`, with the deck's `s_min`
    above.
  - Otherwise it is drawn as a filled block, with its summary in the deck's sentence.
  - Labels never shrink below the floor.
  - If fitting the deck to 880 px gives a scale below 0.6 px/mm, it is drawn at 0.6 px/mm
    (`s_n = s_min = 0.6`) and scrolls horizontally.

**Worked check against the fixture:**
- A Cor 96 plate at `s_n = 3`: well 6.86 mm → 20.6 px.
- `s_min = 2.64`, so the figure's `min-width` is about 390 px, which fits the ~710 px
  notebook width seen with the file browser open.
- The STARLet deck (width 1005 mm: `size_x=1005.0` in `STARLetDeck`,
  `resources/hamilton/star_decks.py:225`, the function at `:209`, at the pin;
  `hamilton_decks.py:811` is only the `_OLD_CONSTANTS` compatibility dict entry
  `"STARLET_SIZE_X": 1005`; round 11, C11-12): `s_n = 880/1005 ≈ 0.876`, so
  `s_min = max(0.771, 0.6) ≈ 0.771`. Labels render at ≥ 11 px. The deck's
  `min-width` is about 775 px, so at the ~710 px notebook width it scrolls by about 65 px,
  which this decision allows.
- A 384-well plate on that deck: its wells are about 3.6 mm → 2.8 px at `s_min`, so it is
  drawn as a block. The Cor 96 plate on the deck: 6.86 mm → 5.3 px, so it is drawn in full.
- The fixture's `tips_300` on that deck: its tip spots are 7.2 mm at the pin (9.0 mm at
  0.2.2; the PLR 1.0 recon) → 7.2 × 0.771 ≈ 5.55 px ≥ 4, so it is drawn in full. No D5
  threshold or number changes at the pin.

**S2-A' branch.** If S2 finds inline `style` stripped on reopened outputs, the floor holds
only for live outputs. `interact.js` can re-apply `min-width` from `data-praxis-minw` when
`data-*` survives.

### D6. Layout tiers keep the user's numbers. 1280 px is the quality target.

DESIGN.md's "Decided" says the MVP targets desktop windows ≥ 1280 px. MVP item 4 also lists a
1024–1279 drawer. Both are built:

| Window width | Layout | Gate |
|---|---|---|
| ≥ 1600 px | Two panes. Notebook content capped at 960 px; the deck panel takes the rest (no maximum; OQ-4): `panel_width = max(420, main_area_width − 960 − nb_h_padding)`, where `nb_h_padding` is the notebook panel's computed horizontal padding. | AC-36 at 1600×900 and 1920×1080, file browser closed, ±8 px |
| 1280–1599 px | Two panes. Deck panel 420–480 px, resizable. With the file browser open the notebook gets about 710 px and outputs scale down to their floor (D5). | AC-36 at 1440×900 and 1280×800 |
| 1024–1279 px | Deck panel is a drawer **over** the notebook. Opening it does not reflow the notebook. | AC-36 at 1152×800 (functional only; human quality checks run at ≥ 1280, OQ-3) |
| < 1024 px | Out of scope. The prototype's bottom sheet is the later starting point. | none |

**Height:** on an 800 px-tall window, the viewer iframe keeps at least **300 px**. The motion
slot shows one row (≤ 36 px) and collapses first.

**Mechanism:**
- The deck panel's widget node carries CSS `min-width: 420px; max-width: 480px` inside
  `@media (min-width: 1280px) and (max-width: 1599px)`, and no max above 1600.
- The 960 px notebook cap is CSS on the notebook panel's content.
- **Layout sizing** ("reachable" below): `dock.js` sets the width and clamps on
  `ResizeObserver` callbacks through the main DockPanel's `saveLayout()` / edit the split
  area's `sizes` / `restoreLayout()` (D1, S1).
- `dock.js` calls `parent.fit()` on the panel's parent after every tier change inside the
  split (crossing 1600 px either way), so Lumino re-reads the size limits.
- Which mechanism applies is fixed by S1's recorded case (Revision 2, B-3):

  | CSS limits | Layout sizing | 1280–1599 | ≥ 1600 |
  |---|---|---|---|
  | honoured | reachable | CSS | layout |
  | ignored | reachable | layout | layout |
  | honoured | unreachable | CSS | inline px `min-width`/`max-width` (both equal to the D6 formula) on the widget node + `parent.fit()`; asserted only if `css_limits_refit`, otherwise recorded-only. The inline values are cleared, and `parent.fit()` called, when the window drops below 1600 px. They are recomputed on every `ResizeObserver` callback (a window resize within ≥ 1600 px, and a file-browser toggle), not only on tier crossings. |
  | ignored | unreachable (**S1-L**) | every width key recorded-only | every width key recorded-only |

  If S1 records `restore_layout_keeps_iframe = false`, every `layout` cell above means
  "layout at open and on tier changes only"; `ResizeObserver` and drag clamps then follow the
  `unreachable` row for the same CSS column, so a clamp never reloads the deck iframe. The
  resulting per-key status is recorded in AC-1 with the sizing case. AC-36 records
  `iframe_reloads_during_resize` (the count of deck iframe loads during the resize and drag
  steps), and asserts it is 0 in every case. *(Round 4, C4-2.)*

  In every case the drawer keys and the height keys stay asserted. AC-39(d) is skipped, and
  recorded as skipped, wherever the ≥ 1600 key is recorded-only. Under S1-L the split opens
  at Lumino's own size and the drag is unclamped: a stated deviation (D1).
- The drawer detaches the widget from the main area and re-attaches it as a fixed-position
  overlay. Moving an iframe in the DOM reloads it: the old client posts `bye` on `pagehide`
  and the socket shim reconnects (D11; the `viewer` id stays in its `src`), so this costs one
  re-greeting (D11 deck-panel state table, T15).

**Drawer behaviour (1024–1279 px).** The drawer is the deck panel in this tier; its lifecycle
is the D11 deck-panel state table, with no drawer-specific rules:
- The first `announce` of a page opens it over the notebook (T2).
- A close button in its header, or Escape while focus is in it, hides it; hiding is the
  table's "close panel" event (T7, T17, T22), so a hidden drawer holds no iframe.
  `praxis:toggle-deck-panel` reopens it (T4).
- Crossing 1280 px either way is the table's "tier crossing" event: an open panel is
  re-homed between drawer and split, keeping its state and any iframe `src` (T10, T15, T21);
  a closed one stays closed (T5).

### D7. Staleness: revision stamps in metadata, announcements on `praxis_repl`, marks in the DOM only.

**Stamps.** Every resource output is stamped (D2) with `resource`, `rev`, `session` and `exec`:
- `session` is the display session id (D2): random, minted once per kernel process by
  `praxis.display.install()`.
- `rev` is a per-resource counter held in the kernel.
- `exec` names the cell execution that drew the output.

When a resource is drawn, `stale.py` subscribes idempotently to the drawn resource and every
descendant (`register_state_update_callback`, `resource.py:1364` at the pin), and to structural
changes (`register_did_assign_resource_callback` / `unassign`, `resource.py:1236-1251`).
Idempotency comes from `stale.py`'s own `_subscribed` set: at the pin PLR's callback
registration **appends** where 0.2.2 replaced (the PLR 1.0 recon, MAJOR-4), so a second
registration would fire twice.

**Rev bumps are filtered on the drawn state** (Revision 10). At the pin a callback does not
always mean a change: `VolumeTracker.rollback()` now fires callbacks, so a failed op fires
them on the source plate and on the tip's origin spot although nothing changed (0.2.2 fired
none), and a pick-up fires `did_unassign` eight times on the rack and on the deck (tips are
tree children). An unconditional bump would therefore mark an output "Changed since" after
every failed op. So:
- For each drawn resource, `stale.py` keeps `(rev, digest)`. The **digest** is the sha256 of a
  canonical serialisation of exactly what an ordinary output of that resource draws: for each
  container in its subtree, `(name, get_used_volume())`; for each tip spot, `(name,
  spot.tip is not None)` (the tip the spot holds in the resource tree, which is what the
  figure draws and includes pending operations, `tip_rack.py:125-131`; never the
  docstring-deprecated `spot.tracker` / `spot.has_tip()`, `tip_rack.py:200-222`; round 11,
  C11-7, C11-14); and the subtree's structure (each child's name, parent and location).
- A callback only marks every drawn ancestor **dirty**. A dirty resource is **settled** by
  recomputing its digest: if the digest differs from the stored one, `rev` increments and the
  digest is stored; otherwise nothing changes.
- Settling happens at `post_run_cell` (before the announcement is built) and **before any
  render of that resource**, so a stamp always carries the rev that matches what its output
  draws (a cell that aspirates and then draws the plate stamps the settled rev and is not
  marked by its own announcement). Under S3-D (no `post_run_cell`), the debounced
  `loop.call_later(0.1, ...)` announcer settles every dirty resource first, then builds its
  announcement, the same order (round 11, C11-7).
- Consequences: a failed aspirate or dispense, whose rollback restores every op resource's
  tracker at the pin, bumps nothing and posts nothing **when the op's resources carried no
  pending residue before the op**. If one did (for example an uncommitted direct
  `tracker.remove_liquid`, AC-15 E13), the rollback sets its pending volume back to the
  committed one (`volume_tracker.py:156-163`), which changes what an ordinary output draws, so
  that resource's `rev` bumps, correctly (round 11, C11-7). A change that alters only pending tracker state
  (residue of a failed `pick_up_tips`/`drop_tips`, or a user's own uncommitted tracker call;
  pending bump at `volume_tracker.py:111-112`) still bumps `rev`, correctly: ordinary outputs
  draw `get_used_volume()`, which includes pending (D8 "Panel drawing").
- *Why not filter on committed state* (the literal form of the Revision 10 brief): that would
  suppress the pending-only bump that D7 has required since Revision 2 (B-8; AC-18), leaving
  a drawing of pending volume unmarked after it changed. For the rollback case both filters
  agree; the drawn-state filter is the one that never hides a change an output drew.

Ledger and error outputs carry `rev: null` (D2), subscribe nothing and never enter an
announcement.

**Announcement.** At `post_run_cell` (S3-D has the fallback), if any rev changed during the
cell, the kernel posts exactly one message on the existing **`praxis_repl`** BroadcastChannel,
as the user decided:
- The message is `{type: "praxis:resource-changed", json: "<string>"}`, built flat with
  `js.Object.fromEntries`, as `praxis_bootstrap._post` does.
- `json` encodes `{"session": ..., "exec": <execution_count>, "revs": {"<name>": <rev>}}` and
  is capped at **4 KiB**. Past the cap the `revs` map is replaced by `"all": true`.

**Current session, per notebook panel** (Revision 2, B-7; there is no session message). The
shell derives each notebook panel's current session from that panel's own outputs:
- `panelSession[P]` is the stamp session (`stampOf`, D2) of the newest stamped output of a
  cell whose execution `chrome.js` observed in this page, after P's kernel last started (seen
  through P's `sessionContext` kernel-changed / status signals).
- Until `panelSession[P]` is known, no "earlier session" mark is written in P. A restored,
  never-executed panel therefore writes none, which is the safe default.
- Two panels with two kernels (for example `welcome.ipynb` beside the user's notebook) each
  have their own current session and never mark each other's outputs.
- Adding a kernel identity to the stamp is rejected: it is not reachable from the worker.

**Why `praxis_repl` does not break R21.** R21 (visualizer transport spec) forbids *visualizer*
traffic on `praxis_repl` and greps `praxis/viz/`, `visualizer/` and `visualizer-augmentations/`
for the name. That check must pass (the "R21 check" below: its final `grep` exits 1 and its
first exits 0 or 1; AC-18), and from sprint C it also covers
the new visualizer paths (AC-31). **The plain grep already exits 0 on `main`** (Revision 10;
the PLR 1.0 recon, BLOCKER-3; pre-existing, the same at `e74ad0fa` and on the design branch):
`web-repl/overlay/assets/python/praxis/viz/transport.py:10,11` (module docstring) and `:26`
(a `#` comment) mention the name as the RST inline literal ` ``praxis_repl`` `, to say the
visualizer does **not** use it. The gate therefore strips that documentation form before
matching (the "R21 check" below). Exempting only `#` comment lines would not suffice: `:10`
and `:11` are docstring lines. These announcements come from `praxis/display/`, send at
most one message per cell, carry a typed `type`, and are ignored
by every other listener:
- `praxis-shell.js:84-93` acts only on `praxis:shell-ping`.
- `praxis_bootstrap._setup_broadcast_listener` acts only on `praxis:execute` and
  `praxis:interaction_response` (`praxis_bootstrap.py:214` and `:266` on the sprint A branch;
  round 11, C11-12).

**R21 check** (Revision 10; exit handling fixed in Revision 11, C11-8). Every R21 gate in this
spec (AC-18, AC-31, B7, C3, C7) runs, after `test -d`/`test -f` on each path, exactly this bash
over its path list `<paths>`:

```
grep -rn "praxis_repl" <paths> | sed 's/``praxis_repl``//g' | grep "praxis_repl"; s=("${PIPESTATUS[@]}")
[ "${s[0]}" -le 1 ] && [ "${s[1]}" -eq 0 ] && [ "${s[2]}" -eq 1 ]
```

The second line is the gate's exit, and it passes only if: the first `grep` exited 0 or 1
(hits, or none at all; **2**, an error such as an unreadable path, fails); `sed` exited 0; and
the final `grep` exited **1** (no line names the channel outside the RST documentation form).
A plain pipeline's exit is only the last command's, so without `PIPESTATUS` a first-`grep`
error would read as a pass (round 11, C11-8). A Python implementation of the gate is equally
valid if it applies the same rule (run the first `grep` with `subprocess`, require its return
code in {0, 1}, strip the form in Python, require no residual line). On `main` today the first
`grep` exits 0 on the three `transport.py:10,11,26` documentation mentions and the final
`grep` exits 1, so the gate passes and is not vacuous (confirmed by the round 11 challenger).
It still catches every code use: a Python or JS string literal (`"praxis_repl"`,
`'praxis_repl'`, a JS template literal), a bare identifier, and a mention on the same line as
a documentation mention (the `sed` removes only the double-backtick form, never the whole
line).

**Marking.** The shell (`stale.js`) keeps the latest rev per `(session, resource)`. An output
whose stamp has a non-null `rev` older than that gets a DOM notice, **"Changed since, see deck
panel."**, inserted in its output node. Outputs with `rev: null` (ledger, error) are never
marked "Changed since". The notice is never written to the notebook model, so it is not
saved. Once `panelSession[P]` is known, an output in P of any kind whose
`stamp.session ≠ panelSession[P]` gets **"Drawn in an earlier session."** The shell maps model outputs to DOM nodes through the notebook widget's output
areas, following the model-first pattern of `repl_smoke.py` (`:1300-1381` at the base
`fd987728`; the model-first reads are at `:1572` and `:1624` on origin/main a176bac7).

**Marks survive re-rendering.** JupyterLab re-renders outputs and, with windowing, detaches
off-screen cells. `stale.js` therefore keeps its marks in memory and re-applies them
idempotently on each cell's `outputs.changed`, on `inViewportChanged` (or the re-attach
signal S1 records for the observed `windowingMode`), and on `activeCellChanged`.

### D8. Errors: four classes, context from the traceback, no PLR patch.

The display handles `TooLittleLiquidError`, `TooLittleVolumeError`, `HasTipError` and
`NoTipError` from `pylabrobot.resources.errors` (`errors.py:8-22`, byte-identical at the
1.0.0b1 pin; the PLR 1.0 recon). Everything else gets the
normal IPython traceback, styled by Praxis CSS on the stderr/error output. Nothing is
intercepted. This includes the `RuntimeError`s that bare `discard_tips()` ("No tips have been
picked up and no channels were specified.") and bare `return_tips()` ("No tips have been
picked up.") raise with no tip mounted: they are not one of the four classes and get the plain
styled traceback (AC-15 negatives). Errors raised inside a `*96` (96-head) op are out of MVP scope: they get the
generic panel (step 2; orchestrator ruling 260929, MVP item 3 names four classes and no heads).

**Classes the code checks, by non-shim home** (Revision 10; the PLR 1.0 recon, MAJOR-8):
`LiquidHandler` from `pylabrobot.legacy.liquid_handling`, `TipTracker` from
`pylabrobot.legacy.tip_tracker` (the `pylabrobot.resources.tip_tracker` path is a
`DeprecationWarning` shim at the pin), and `VolumeTracker` from
`pylabrobot.resources.volume_tracker`. No `praxis/display/` module imports a shim home:
`web-repl/tests/plr_contract.py` has a "CONTRACT names no shim" test and a probe that escalates
warnings to errors (sprint B "Import contract").

**What PLR's message omits (read at the 1.0.0b1 pin; the PLR 1.0 recon):**
- `TooLittleLiquidError`: "Not enough liquid in container: {volume}uL > {used}uL."
  (`volume_tracker.py:102`, in `validate_remove_liquid`, called at `:108`). No container name.
- `TooLittleVolumeError`: "Not enough space in container: ..." (`:117`,
  `validate_add_liquid`). No container name, and the container may be a **tip** (the tip's
  tracker receives `add_liquid` during an aspirate, LH:1273).
- `HasTipError`: "Channel has tip" (LH:758), with no channel number, or
  "{thing} already has a tip." (`legacy/tip_tracker.py:153`).
- `NoTipError`: "{thing} does not have a tip." (`legacy/tip_tracker.py:118, 166`). Here `thing`
  is "Channel N" for head trackers (LH:418). For a tip spot it is, at the pin, the spot's own
  name (`TipTracker(thing=spot.name)`): `'tips_300_tipspot_A2 already has a tip.'`,
  `'tips_300_tipspot_A1 does not have a tip.'`. At 0.2.2 it was just "Tip spot". The panel's
  heading still names the rack and spot in Praxis words (§3.3); PLR's text appears only in the
  verbatim "PyLabRobot raised" line, which no AC asserts beyond equalling `str(exc)`.
- A container's volume tracker's `thing` is `"<name>_volume_tracker"` (`container.py:87`). At
  the pin a well's name is its deck name (`assay_well_A1_volume_tracker`; 0.2.2 gave
  `well_0_0_volume_tracker`), so owner rule (d) below resolves wells too.

**Context resolution** is a pure function, `context.resolve(exc, tb) -> ErrorContext | None`,
over the traceback frames. It only reads them:

1. **Tracker.** The innermost frame whose `f_locals["self"]` is a `VolumeTracker` or
   `TipTracker` gives `tracker`, and for volume errors, `requested` = that frame's `volume`
   local.
2. **Op.** Only frames whose `self` is a `LiquidHandler` **and** whose `f_code.co_name` is a
   key of `glossary.ACTIONS` count. The `co_name` filter also excludes any `<listcomp>` or
   `<genexpr>` frame; this is defence only, with no test case (on Python 3.12 and later,
   including CI's CPython 3.12 for the tests, `repl.yml:68` on the sprint A branch, and the
   kernel's CPython 3.14, PEP 709 inlines list comprehensions, and no generator
   expression raises at the pin). At the pin it also excludes the `wrapper` frames that
   `pylabrobot/events/bus.py:331` and `legacy/machines/machine.py:58` add around LH methods
   (the PLR 1.0 recon).
   - **`*96` short-circuit.** If any such frame is a `*96` op (`pick_up_tips96`,
     `drop_tips96`, `return_tips96`, `discard_tips96`, `aspirate96`, `dispense96`;
     LH:1674-2229), `resolve` returns `None` at once and the
     generic panel is shown. The `*96` glossary names and ledger wrappers exist for the
     ledger only (D9, section 3.5).
   - The **innermost** such frame supplies the locals:
     - `lh`
     - `op_resources` (local `resources` or `tip_spots`)
     - `use_channels` and `vols`
     - for `HasTipError("Channel has tip")`, the loop locals `channel` and `op`
       (the pick-up queue loop, LH:755-761; raised at LH:758)
     - a frame that raised before its queue loop binds fewer locals: the taken-spot `NoTipError`
       of a pick-up is raised at LH:727 (through `TipSpot.get_tip`) with only `tip_spots` and
       `use_channels` bound (E7). Missing locals are read as absent, never guessed.
   - The **outermost** such frame supplies `action`: the user's call. So `return_tips`
     onto an occupied spot reads "Return tips", not the inner `drop_tips`.
3. **Owner, by identity, in this order:**
   - (a) walk `lh.deck`'s subtree for a container whose `.tracker is tracker`, or a tip spot
     whose `tip_spot_tracker(spot) is tracker` (`pylabrobot.legacy.tip_tracker.tip_spot_tracker`,
     `legacy/tip_tracker.py:233-258`). The docstring-deprecated `TipSpot.tracker` is never
     read (`tip_rack.py:200-207`, "TODO: Remove in v1"; round 11, C11-14). `tip_spot_tracker`
     creates and caches a tracker for a spot that has none yet (`:242-257`); that is the same
     object PLR itself uses for the spot on every later lookup, held weakly, so the side
     effect changes no tip state and is accepted. A resting `Tip` in the subtree (its own
     `VolumeTracker`, `tip.py:52`) is not an owner under this rule (see rule (d)).
   - (b) `lh.head[c] is tracker`, which gives the channel
   - (c) a mounted tip whose `.tracker is tracker`, which gives the tip on channel `c` (a TLV
     overflow on aspirate, LH:1273, or a TLL on dispense)
   - (d) with no LH frame: parse `tracker.thing`, in this order. `"Channel N"` gives the
     channel. `"<name>_volume_tracker"` (`container.py:87`) gives the container name, wells
     included (deck names at the pin). Any other value is, at the pin, a tip spot's own name
     (`TipTracker(thing=spot.name)`) and is looked up as a resource name. A name that matches
     nothing gives no owner (`None`, AC-15 negative). **A name that matches a `Tip`** (a tip's
     `VolumeTracker` has `thing` = the tip's own name, `tip.py:52`, for example
     `tips_300_tipspot_A1#0`; a `Tip` is a `HeadTool`, neither container nor spot) **gives no
     owner** either (`None`, generic panel; round 11, C11-15). Chosen over mapping it to its
     spot with `tip_origin` (`tip_rack.py:286-303`): the tip-owner templates need a channel
     (`The tip on channel {c} ...`, §3.3), which only an LH frame gives (rule (c)), and a
     volume error described on a tip spot would name a fault a spot cannot have (a spot holds
     no liquid; its templates are HasTip/NoTip).
   - (e) no tracker frame, a `HasTipError`, and an LH frame with a `channel` local
     (LH:758 raises before any tracker is touched): the owner is that channel.
4. **Offending set and numbers: committed state only.** PLR raises on the first failing
   channel only, and its message mixes in pending state ("Panel drawing" below). Every number
   and every mark in the panel is therefore computed from **committed** state, with demand
   **summed per resource** over the op's channels:
   - TLL, container owner: a resource offends if its summed requested volume >
     `tracker.volume`.
   - TLL, tip owner (dispense): compared **per channel**, not summed. The tip on channel c
     offends if its committed `tracker.volume` < channel c's requested volume.
   - TLV, container owner: a resource offends if its summed addition >
     `max_volume − tracker.volume`.
   - TLV, tip owner: the tip on channel c offends if channel c's requested volume >
     its `max_volume − tracker.volume` (committed); `{avail}` is that committed room.
   - HasTip / NoTip: the channels or tip spots whose committed tip state conflicts with the
     op (a channel that already holds a tip for Pick up, an empty spot for Pick up, an
     occupied spot for Drop/Return, a channel with no committed tip, for any op that uses a
     mounted tip (Aspirate, Dispense, Transfer, Drop tips, Return tips, Discard tips)).
     **Committed tip state** means `TipTracker.get_tip()` succeeding
     (`legacy/tip_tracker.py:110-119`, which returns the committed tip and raises `NoTipError`
     without one): `lh.head[c].get_tip()` for a channel, `tip_spot_tracker(spot).get_tip()`
     for a tip spot. It is **never** `has_tip`, which includes pending operations
     (`:105-108`), and **never** `TipSpot.get_tip()`, which is docstring-deprecated and adds a
     new tip to the spot when tracking is off (`tip_rack.py:209-218`) (round 11, C11-5).
   - **Pending residue.** PLR validates against pending state (`validate_remove_liquid`,
     `volume_tracker.py:99-104`, verified at the pin by the E13 setup; `validate_add_liquid`,
     `:114-119`, whose `get_free_volume()` is `max_volume − get_used_volume()` and so reads
     pending, `:91-97`, confirmed from source by round 11, C11-6; the tip trackers,
     `legacy/tip_tracker.py:118, 153, 166`), so uncommitted changes can cause a raise that
     committed state does not explain. At the pin such residue comes only from a failed
     `pick_up_tips`/`drop_tips` (E14) or from direct tracker use (E13, E15); a failed
     aspirate or dispense leaves none ("Panel drawing" below). If the resolved owner is
     **not** in the committed offending set, `resolve` returns `None`. Otherwise step 5
     applies.
   - `{avail}` is the committed value and `{req}` is the summed request (per channel for a
     tip owner).
   - PLR's own number appears only in the verbatim "PyLabRobot raised" line.
5. **Result.** If no owner resolves, or the owner is not in the committed offending set
   (step 4), or a `*96` op is on the stack (step 2), the result is `None`, and the handler
   shows the generic panel ("PyLabRobot raised X: message" plus the traceback). Otherwise the
   result is the `ErrorContext`. **It never guesses.**

**Handler** (`errors.py`, registered by `set_custom_exc`; S3-C has the fallback):
- It calls `display()` on the panel bundle.
- It returns a one-line structured traceback, `["<ExcName>: <PLR message>"]`. The cell
  therefore still ends in an `error` output, the rail shows brick, and Run All stops.
- The full traceback sits inside the panel's `<details>`: `traceback.format_exception(...)`
  (no ANSI), escaped (D2), capped at 16 KiB with the tail kept (D4).
- If the exception was raised inside a `RunLedger`, it reads the step with
  `ledger.step_for(exc)` (D9), which also removes the entry, and the panel names the step.

**Panel drawing: committed volume, not pending** (rewritten in Revision 10; the PLR 1.0
recon, BLOCKER-1/2). What a failed op leaves behind differs by op at the 1.0.0b1 pin:
- **`aspirate` and `dispense` leave no residue.** They queue their tracker changes **inside**
  the `try`, and a tracker refusal rolls every channel back (LH ~1265 aspirate, ~1466
  dispense). Verified independently by the orchestrator on the 1.0.0b1 wheel: after E9 the
  trough reads committed 100 / pending 100 and every tip 0 / 0, and a retry of the same op
  raises nothing from residue. (At 0.2.2 these loops sat outside the `try` and left channels
  0..k-1 pending; that premise is false at the pin.)
- **`pick_up_tips` and `drop_tips` still leave residue.** Their queue loops are still outside
  the `try` (LH ~755-761 pick up, ~901-911 drop): a tracker error on channel k leaves
  channels 0..k-1 with **uncommitted pending** tip changes (E14 confirmed at the pin).
- **Direct tracker use leaves residue.** A user's own `tracker.remove_liquid(v)` or
  `add_liquid(v)` with no commit changes pending state only (E13, E15). A later failed
  aspirate or dispense that includes that resource rolls it back too (the commit/rollback
  loop covers every op resource and every op tip, LH:1284-1289 and :1485-1490;
  `rollback()` sets `pending_volume = self.volume`, `volume_tracker.py:160`), so after a
  failed op such residue survives only on resources **outside** the op (round 11, C11-2; the
  orchestrator's E9 probe likewise showed pending reset to committed on the op's resources).

Consequences:
- The panel draws each container's **committed** `tracker.volume` (a public attribute), and
  its numbers and marks use committed state (step 4). For aspirate and dispense at the pin,
  committed equals pending on every op resource after the failed op, so on those resources
  this changes nothing visible; it does on the other wells of the drawn plate that carry
  residue, and it is a **defence** for the pick-up/drop residue, for direct tracker use, and
  for a future pin that moves a queue loop again. AC-16 checks it on a well outside the op.
- The panel may state "Nothing was aspirated/dispensed": a tracker refusal is raised before
  the backend is called, so the backend was not reached. This is read from source at the pin:
  the tracker loop runs before `backend.aspirate` / `backend.dispense` inside the same `try`
  (LH:1269-1274 and :1470-1475; round 11, C11-6). B6's chatterbox backend spy (no aspirate or
  dispense call recorded on E1) is a **confirmatory assert** of that ordering, not a
  verify-else-stop branch.
- The panel never describes the other channels' tracker state.
- Other outputs keep drawing PLR's own `get_used_volume()`, which includes pending, as the
  prototype fixture does; at the pin this differs from committed only after a failed
  pick-up/drop or direct tracker use. OQ-6 records the upstream question, now for the tip ops.
- A later raise caused only by residue resolves to `None` and gets the generic panel (step 4,
  "Pending residue"; AC-15 E13, E14, E15).

**Tracking.** PLR tip/volume tracking is off by default (`resources/tip_tracking.py:5`,
`volume_tracker.py:14` at the pin); the fixture enables it.
- Spot-side HasTip/NoTip and both volume errors fire only with tracking on.
- Head-side `HasTipError`/`NoTipError` fire regardless (HasTip at LH:758; the 0.2.2 sites
  were `liquid_handler.py:534, 655, 974`, and the head-side NoTip sites at the pin are to be
  re-anchored by B5), and resolve by rules (b), (d) and (e) with tracking off (AC-15 E4-off,
  E6-off).

### D9. `RunLedger` is an explicit context manager that shadows one instance's methods.

`with praxis.display.RunLedger(lh) as run:` is the design's own implementation path
(DESIGN.md step 1). How it records:
- On enter, it sets **instance** attributes on that one `LiquidHandler` for these methods:
  - `pick_up_tips`, `drop_tips`, `return_tips`, `discard_tips`
  - `aspirate`, `dispense`, `transfer`
  - the `*96` variants
- Each wrapper records a row (`in-flight`, then `ok` or `error`) and awaits the original bound
  method.
- **Nesting.** Any wrapped op called while another wrapped op is in flight becomes a child row
  of it. So a `transfer` owns the aspirate and dispense rows it causes, and `discard_tips` /
  `return_tips` each own the one `drop_tips` row they cause (`return_tips` → `drop_tips`
  LH:1000, `discard_tips` → `drop_tips` LH:1058; the `*96` pair LH:1876, :1908). Steps, tip
  cycles and µL moved count **top-level rows only**.
- On exit, it deletes the instance attributes and, unless `show=False`, calls `display(run)`.
  This holds on the error path too: `__exit__` with an exception still displays the ledger,
  which therefore appears before the error panel, and does not suppress the exception.

**Nothing else changes.** PLR modules and classes are never mutated. AC-14 asserts that
`LiquidHandler.aspirate` is the original function and that no op name remains in
`lh.__dict__`.

**Error cooperation.** If an op raises inside the context, its wrapper marks the row `error`,
stores `(exc, step)` in the module dict `ledger._ERROR_STEPS[id(exc)]`, and re-raises the same
exception unchanged. The error handler (D8) reads it with `ledger.step_for(exc)`, which
returns the step and removes the entry.

**Why not PLR's logger.** PLR logs every command through `_log_command` → `logger.debug` on
the package logger `"pylabrobot"` (LH:88 and LH:643-645), with the arguments
flattened to strings. Capturing it would mean raising the user's `"pylabrobot"` logger to
DEBUG, which also fills PLR's own `FileHandler` (`pylabrobot/__init__.py:67-89`, 0.2.2).
Rejected.

**Why not PLR's event bus** (Revision 10). The pin adds an opt-in `pylabrobot.events` bus
(`evented_operation` on pick-up, drop, aspirate and dispense; the PLR 1.0 recon). It does not
wrap `return_tips`, `discard_tips` or `transfer`, so it cannot give the nested rows D9 needs.
Method shadowing stays; the bus is a possible later alternative, not specified here.

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

### D11. Visualizer3D delivery: the pin's `pylabrobot.visualizer3D`, a vendored static page, three overrides, a socket shim over `praxis_viz3d`.

*Revision 10 (orchestrator ruling, binding).* The 1.0.0b1 pin ships `pylabrobot/visualizer3D`,
the REPL's PLR wheel already contains it, and `websockets` (17.0.1) is a vendored wheel (the
PLR 1.0 recon, MAJOR-2). The Revision 1-9 design (five vendored `.py` files renamed to
`plr_visualizer3d`, an ADR §2 addendum and an extra contract entry) is therefore dropped: its
stated reason, "never collides with a future pin that ships it", is inverted now that the pin
ships it. No PLR Python is copied into the overlay. Only `static/` is vendored, because the
page must be HTTP-served from the dist and the wheel's copy lives inside the kernel's
site-packages, which nothing serves.

**Static page.** `web-repl/scripts/vendor_visualizer3d.py` copies the pin's
`pylabrobot/visualizer3D/static/` to `web-repl/overlay/assets/visualizer3d/`. Its source is
`--src`, default `external/pylabrobot` (the submodule at the pin, the same tree the REPL's PLR
wheel is built from).
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
- `VENDOR_MANIFEST.json` records the PLR source commit (read from the source checkout's
  `HEAD`; at the pin `786ac2c4e4f7afe37885af2d98ff5b0afe274c67`) and per-file sha256.
- `--check` fails, with the differing paths, if any committed file differs from the source,
  or if the recorded commit differs from the source's `HEAD`. A pin bump that touches
  `static/`, or any pin bump at all, therefore fails `--check` until the static tree is
  explicitly re-vendored. CI runs `--check` against the submodule the REPL job already
  initialises (evidence: the job checks out with `submodules: recursive` and then asserts
  `test -f external/pylabrobot/pyproject.toml`, `repl.yml:56-61` on the sprint A branch.
  Revision 10 cited `repl_smoke.py`'s import-time `version.txt` read instead; A1 makes that
  read lazy, so it is no longer evidence; round 11, C11-3).
- The pin also ships 63 `.glb` model files elsewhere in the package (byonoy, hamilton
  `resource_model`, ...; the wheel grew from 1.26 to 10.2 MB; the PLR 1.0 recon, MAJOR-3).
  None is vendored.

**Python: import the pin's package.** `praxis/viz/viewer3d.py` imports
`pylabrobot.visualizer3D` from the kernel's installed PLR wheel and subclasses its
`server.Viewer3D`. It edits no PLR file and copies none.
- **Import contract.** `viewer3d.py` imports `pylabrobot.visualizer3D.server`, which lives
  under `assets/python/` and is therefore scanned by `test_contract_covers_imports.py`. C3
  adds `("pylabrobot.visualizer3D.server", "Viewer3D")` to `plr_contract.CONTRACT` with a
  justification comment, by the same per-task rule every sprint B task follows (sprint B
  "Import contract"). This is the ordinary entry for the task's own import, not the dropped
  Revision 1-9 entry for uneditable vendored files. `pylabrobot.visualizer3D` is not a shim
  home; that it imports with warnings escalated to errors is to be verified by C3 (the
  contract probe is C3's gate).
- **`PACKAGE_ROOT` is rebound** (Revision 2, B-4; load-bearing at the pin, Revision 10). The
  stock `PACKAGE_ROOT = dirname(dirname(abspath(__file__)))` (`server.py:98`) resolves inside
  the installed PLR package in site-packages, which at the pin holds 63 `.glb` files.
  `_models_on_disk(PACKAGE_ROOT)` (`server.py:104-105`) would find them, and any whose name
  matches a fixture model would become a `mesh` whose `mesh/<id>` URL nothing serves (there is
  no file server). So `viewer3d.py` rebinds `pylabrobot.visualizer3D.server.PACKAGE_ROOT` to
  `tempfile.mkdtemp()` (an empty directory it owns) **once, before the first viewer is
  constructed**. **Trigger** (round 11, C11-13): a guarded, idempotent module helper,
  `_ensure_package_root()`, called as the first statement of `DockedViewer3D.__init__`
  (before `super().__init__`). On its first call it sets the global and a module flag; every
  later call returns at once and changes nothing. Importing `viewer3d.py` changes no PLR
  state; the rebind happens at the first construction. So a test can seed its own temporary
  root **after** importing `viewer3d.py` and **before** the first construction (AC-31).
  `_register_meshes` (`server.py:216`) reads the global at call time (`:224`),
  and `_models_on_disk` is cached per root (`:104`), so the rebind takes effect for every
  call. It is a module global, not a class attribute, so the override set stays at three
  (GATE X). This is the **one deliberate runtime rebinding** of PLR state. Rebinding a module
  global of the installed package changes it for the whole kernel process; nothing else in
  the REPL reads it (`viz3d` appears nowhere else in the repo; the PLR 1.0 recon).
- **Meshes are unsupported.** Zero `.glb` files are vendored or served, and the rebound root
  is empty, so every model is drawn as a box and no `mesh/<id>` URL is ever emitted. That the
  rebind alone removes every `mesh` from the fixture scene at the pin (no other code path
  emits one, for example from a resource's own model reference) is to be verified by C1 (S4
  records the scene) and asserted by AC-31, which also shows the rebind is what removes it.

**Transport.** No file vendored from PLR is edited. The page's only socket is
`new WebSocket(window.WS_URL)` (`static/transport.js:63`). `socket.js` replaces
`window.WebSocket`, **in that iframe page only**, with `PraxisSocket`: a WebSocket-shaped class
over `BroadcastChannel("praxis_viz3d")`.
- It has the same `CONNECTING/OPEN/CLOSING/CLOSED` statics, `readyState`, `send`, `close`,
  `onopen`, `onclose` and `onmessage`.
- The page's `transport.js` compares against `WebSocket.OPEN` and `WebSocket.CONNECTING` and
  reconnects every 1.5 s for 60 s (`transport.js:23-27, 56-75`). It keeps working unchanged.

**Protocol on `praxis_viz3d`.** Every message is a JSON string. `open`, `accept`, `msg`, `bye`
and `evict` carry `viewer` (the id minted per `DockedViewer3D`) and `client` (the id minted per
`PraxisSocket`); `announce` and `close` carry `viewer` only; `query` carries neither.

**How the page learns the viewer id.** The iframe's `src` is
`assets/visualizer3d/index.html?embed=1&view=top&viewer=<id>`, and `dock.js` writes it only
when handling an `announce`, as the deck-panel state table below fixes (T2, T6, T11, T18).
Writing it (re)loads the page. `socket.js` reads `viewer` from `location.search`. With no
`viewer` parameter the shim posts nothing (not even `bye`) and fires `onclose` after 3 s. The
page's own transport gives up after 60 s (`static/transport.js:26, 73`), so a page loaded
without an id is never created: no iframe exists without a `src` (invariant I1).

**Deck-panel state machine** (Revision 6, R6-1; the single source of truth for the deck
panel's lifecycle, superseding the Revision 2 "Closed panel" paragraph). Every other section
(D6 drawer, D12 embed mode, §3.6, §4 `dock.js`, C5, C7, AC-36, AC-38, §7) refers to this
table and restates none of it. `dock.js` holds three values besides the state: `seen` (whether
this page has received any `announce` since mount), `current` (the viewer id of the last
`announce` the panel acted on, or none), and the view preset (D12). It also keeps
`viewerPanel`, a map from viewer id to notebook panel, used only by the kernel-restart event
(Revision 7, C7-6):
- On every `announce`, in any state (including an ignored one, T3), if `chrome.js` reports
  exactly one notebook panel P with a cell executing, `viewerPanel[id] = P`. (`dock()` posts
  its viewer's first `announce` from inside the executing `dock()` cell.)
- The **viewer's kernel** is the kernel of `viewerPanel[current]`. If `current` has no entry
  (the page loaded after `dock()` ran, and the `announce` answered a `query`), it is the
  kernel of the only open notebook panel with a live kernel, if there is exactly one.
  Otherwise the viewer's kernel is unknown, and the kernel-restart event never fires for it:
  the panel then shows a frozen view (the dead kernel posts no `close`, and the page's socket
  stays open, so no `plr:gone` arrives either) until the user closes and reopens the panel
  (T17, then T4, whose `query` no dead viewer answers). This is accepted, and is stated
  under the multi-notebook non-goal (§2).

States:

| State | Panel | Iframe in the panel DOM | Body text |
|---|---|---|---|
| `closed` | not attached (split tab closed, or drawer hidden) | none | none |
| `open-waiting` | attached | none | "No deck viewer is running. Run `viewer = await praxis.viz.viewer3d.dock(deck)` in a cell." (§3.6) |
| `open-connected` | attached | exactly one, `src` carrying `viewer=<current>` | none (the page) |
| `open-lost` | attached | none | "The deck view lost its connection. Close and reopen the deck panel, or run `dock(deck)` again." (§3.6) |

Events: **mount** (`dock.js` mounts on page load); **announce** (kernel `announce {viewer}`;
"first" means `seen` was false); **reopen** (`praxis:toggle-deck-panel` while closed);
**close panel** (the split tab closed, the drawer's close button or Escape, or
`praxis:toggle-deck-panel` while open); **kernel close** (kernel `close {viewer}`, "current"
when its `viewer` equals `current`); **plr:gone** (forwarded by `embed.js` as a
`praxis:dock-status` event, D12); **tier crossing** (the window crosses 1280 px, which moves an
open panel between split and drawer, D6; a 1600 px crossing only re-sizes the split with
`parent.fit()`, moves no iframe, and is not a lifecycle event);
**iframe reload** (the page in the panel's iframe unloads and loads again with the same `src`,
while the panel stays in its tier: a harness `iframe.src = iframe.src`, or a user reload. The
reload caused by a tier crossing's DOM move belongs to the tier-crossing event (T10, T15, T21)
and is **not** an iframe reload, so one crossing never fires both T15 and T16; Revision 7,
C7-9); **kernel restart** (the viewer's kernel, as defined above, restarts or shuts down,
observed on that notebook panel's `sessionContext`: `statusChanged` to `restarting`,
`autorestarting` or `dead`, or `kernelChanged`, including a change to no kernel. The dead
kernel posts no `close`, so without this event the panel would keep a frozen deck that looks
live. A restart of any other panel's kernel is not this event. Revision 7, C7-6).

| # | State | Event | Next state | Actions |
|---|---|---|---|---|
| T1 | (none) | mount | `closed` | `seen = false`, `current` = none; post `query` |
| T2 | `closed` | announce, first | `open-connected` | `seen = true`; attach the panel in the current tier's home (split or drawer); create one iframe; set its `src` with `viewer=<id>`; `current = id` |
| T3 | `closed` | announce, not first | `closed` | none (ignored; no iframe is created) |
| T4 | `closed` | reopen | `open-waiting` | attach the panel, with **no** iframe, in the current tier's home (split or drawer); show the no-viewer text; post `query` |
| T5 | `closed` | kernel close (any), plr:gone, tier crossing, close panel | `closed` | none |
| T23 | `closed` | kernel restart | `closed` | none |
| T6 | `open-waiting` | announce (first or not; including the answer to a `query`) | `open-connected` | `seen = true`; hide the text; **create** one new iframe (a removed element is never reused); set its `src` with `viewer=<id>`; `current = id` |
| T7 | `open-waiting` | close panel | `closed` | detach the panel; `current` = none |
| T8 | `open-waiting` | kernel close (any) | `open-waiting` | none |
| T24 | `open-waiting` | kernel restart | `open-waiting` | none |
| T9 | `open-waiting` | plr:gone | `open-waiting` | none (ignored; C5-2) |
| T10 | `open-waiting` | tier crossing | `open-waiting` | re-home the panel (split ↔ drawer, D6); no `query` is re-sent (an outstanding answer still lands through T6) |
| T11 | `open-connected` | announce, id ≠ `current` | `open-connected` | set the `src` of the iframe in the panel to `viewer=<id>` (the page reloads); `current = id` |
| T27 | `open-connected` | announce, id = `current` | `open-connected` | none (no `src` write, no reload: the page is already on that viewer; for example another page's `query` answered by the same viewer; Revision 7, C7-9) |
| T12 | `open-connected` | kernel close, current | `open-waiting` | remove the iframe; show the no-viewer text (within 5 s); `current` = none |
| T25 | `open-connected` | kernel restart | `open-waiting` | as T12: remove the iframe; show the no-viewer text (within 5 s); `current` = none |
| T13 | `open-connected` | kernel close, not current | `open-connected` | none |
| T14 | `open-connected` | plr:gone | `open-lost` | remove the iframe; show the lost-connection text; keep `current` |
| T15 | `open-connected` | tier crossing | `open-connected` | re-home the panel with its iframe (one reload, same `src`; C3-3); no `src` write, no `query` |
| T16 | `open-connected` | iframe reload | `open-connected` | no lifecycle action (the page reconnects from the `viewer` in its `src`; the old client's `bye` and eviction clean up, D11; D12 re-applies the preset on the load) |
| T17 | `open-connected` | close panel | `closed` | remove the iframe; detach the panel; `current` = none |
| T18 | `open-lost` | announce | `open-connected` | hide the text; create one new iframe; set its `src` with `viewer=<id>`; `current = id` |
| T19 | `open-lost` | kernel close, current | `open-waiting` | show the no-viewer text instead of the lost-connection text; `current` = none |
| T26 | `open-lost` | kernel restart | `open-waiting` | as T19: show the no-viewer text instead of the lost-connection text; `current` = none |
| T20 | `open-lost` | kernel close, not current; plr:gone | `open-lost` | none |
| T21 | `open-lost` | tier crossing | `open-lost` | re-home the panel |
| T22 | `open-lost` | close panel | `closed` | detach the panel; `current` = none |

Every announce also sets `seen = true`, in any state. "iframe reload" has no row for
`closed`, `open-waiting` or `open-lost`, because those states hold no iframe (I1). Rows T23 to
T27 were added by Revision 7 and sit beside the rows for their state; T1 to T22 keep their
numbers and meaning, except that T11 now covers only a new id (T27 covers the same id) and T4
names the tier's home.

Invariants (C5 checks each after every transition):
- **I1.** The panel DOM holds an iframe if and only if the state is `open-connected`, and then
  exactly one, whose `src` carries `viewer=<current>`.
- **I2.** An iframe `src` is written only in T2, T6, T11 and T18, i.e. only from an
  `announce` whose id differs from the one the panel shows. Reopen, tier crossing, iframe
  reload, kernel restart and a same-id `announce` (T27) never write it.
- **I3.** `query` is posted only in T1 and T4.
- **I4.** `plr:gone` changes state only in `open-connected` (T14). So after a kernel `close`
  or a kernel restart (T12, T25) it is ignored until an `announce` returns the panel to
  `open-connected`, and from then on it is honoured again (C5-2, C6-1).
- **I5.** The no-viewer text is shown if and only if the state is `open-waiting`, and the
  lost-connection text if and only if it is `open-lost` (C4-1).
- **I6.** A kernel `close` for the current viewer, or a kernel restart, never shows the
  lost-connection text.

Re-docking (re-running a `dock()` cell with an open panel) is T12 followed by T6: `dock()`
awaits the old viewer's `stop()`, whose `close` removes the iframe and shows the no-viewer
text, and the new viewer's `announce` then creates a fresh iframe with the new id. The
no-viewer text is visible between the two; this is accepted and stated (C6-1). A stopped
viewer has left `praxis_viz3d` (Kernel, `stop`), so a later `query` is answered only by the
live viewer, never by a dead one (Revision 7, C7-3).

| Direction | `kind` | Meaning |
|---|---|---|
| kernel → all | `announce` | `{viewer, deck, session}` (`session` is the display session id): a viewer exists. The shell handles it per the deck-panel state table (T2, T3, T6, T11, T18). |
| shell → kernel | `query` | `{}`: sent on mount (T1) and on reopen (T4). A live `DockedViewer3D` answers with `announce`. |
| page → kernel | `open` | `{viewer, client}` |
| kernel → page | `accept` | Then the page receives, in order, the `scene` and `state` messages that `Viewer3D._handler` sends (`server.py:590-593`), as `msg`. |
| both | `msg` | `{client, data}`: `data` is the exact string the websocket would carry. |
| page → kernel | `bye` | `{viewer, client}`: the client is gone. Posted on `close()`, on `pagehide`, and on the shim's accept timeout. Ends that client's `VirtualConnection`. |
| kernel → one page | `evict` | `{viewer, client}`: the kernel dropped this client at the client cap. The shim fires `onclose`, so the page's own reconnect loop recovers. |
| kernel → all | `close` | `{viewer, reason}`: the viewer stopped. The shell acts only on this kind and `announce`, per the deck-panel state table (T12, T19; ignored elsewhere). A kernel that restarts or shuts down posts nothing; the shell observes that on the notebook's `sessionContext` instead (the kernel-restart event, T25, T26). |

- Without an `accept` within **3 s**, the shim posts `bye`, fires `onclose`, and ignores any
  later `accept` for that client; the page's own reconnect loop retries with a new client.
- `bye` at `pagehide` is best-effort (a page being torn down may not deliver it). Eviction at
  the cap is the backstop.
- A synchronous cell that blocks the kernel for more than about 60 s makes the page's
  transport give up (`static/transport.js:26, 72-74`); the panel then enters `open-lost`
  (state table T14) even though the viewer is still live, and closing and reopening the deck
  panel recovers through `query` (T22, T4, T6). This is accepted and stated.
- Traffic uses a **new channel**, not `praxis_viz`: that channel's receiver
  (`visualizer-augmentations/index.js`) would misread these envelopes. It is also not
  `praxis_repl`, per R21.

**Threat model: the origin is the boundary.** BroadcastChannel delivers only within one
origin. On GitHub Pages that origin (`<account>.github.io`) is shared with the account's other
project pages, so "same origin" means "any page the account serves".
- Any same-origin page can already run kernel code: it can post `praxis:execute` on
  `praxis_repl`, and `praxis_bootstrap.py:214-218` (on `main`) executes its `code`. The
  `praxis_viz3d` channel gives such a page nothing it does not already have.
- A per-viewer nonce is therefore **not** added. It would raise no bar, and a nonce sent over
  a broadcast bus is visible to every listener on it.
- Upstream `Viewer3D`'s token and Host/Origin checks (`server.py:170-173, 329-349`) defend a
  localhost websocket against **cross-origin** pages. No websocket exists here, so
  `_check_websocket` is never reached. The iframe's `window.parent` access is our own
  vendored code on our own origin.
- **Inbound bounds.** `DockedViewer3D` caps virtual clients at **4**. At the cap, a new
  `open` **evicts the oldest** client: the kernel posts `evict` to it and ends its
  `VirtualConnection` with a sentinel, then gives the new client `accept`. `_clients` never
  exceeds 4. `_clients` is a set (`server.py:187`), so `DockedViewer3D` keeps its own
  insertion-ordered map of clients to find the oldest, and the evict path removes the old
  connection from `_clients` synchronously, before the new client's `_handler` runs. (A BroadcastChannel post never raises, so the stock evict-on-send-failure path,
  `server.py:357-361`, never fires; without eviction, orphans from routine reloads would
  fill the cap.) Messages that are not JSON, or whose `kind` is unknown, are dropped without
  an exception (logged at debug level).

**Kernel.** `praxis/viz/viewer3d.py` defines `DockedViewer3D(Viewer3D)`, which overrides
exactly **`__init__`, `start` and `stop`**:
- `__init__` first calls `_ensure_package_root()` (the guarded, idempotent `PACKAGE_ROOT`
  rebind, above; a module function, so it adds no override), then forces
  `open_browser=False` and takes an injected channel factory.
- `start` copies the stock body (`server.py:785-811`) with four differences: `legacy_size`
  runs synchronously (Pyodide has no threads, and `asyncio.to_thread` needs them); there is no
  `websockets.serve`; there is no file server; and `_models_on_disk` is not pre-warmed in a
  thread (its first call is the inherited scene build, `server.py:417`; S4 times it).
  It subscribes to the channel instead. On each `open` (evicting the oldest client at the
  4-client cap) it builds a `VirtualConnection`, which has an `async send`, async iteration
  over an `asyncio.Queue`, and ends on `bye` or eviction (a queue sentinel). It then runs the **inherited, unmodified** `_handler(conn)` as a task.
  `_broadcast`, `_flush`, `_enqueue`, the scene debounce, `_on_client_message` (hello) and
  every subscription path are inherited unchanged. `start` answers `query` with `announce`.
- `stop` calls `super().stop()`, which already skips `_ws_server` and `_httpd` when they are
  `None` (`server.py:841-850`). It then ends every `VirtualConnection` (a queue sentinel),
  awaits each `_handler` task, posts `close`, and then **unsubscribes from `praxis_viz3d`**
  (removes its listener and closes its channel). A stopped viewer therefore answers no
  `query` and accepts no `open`: otherwise `late_iframe`'s reopen could receive two
  `announce`s, from a dead viewer and a live one, and end on the dead one (Revision 7, C7-3).
  `stop` is idempotent: a second call on a
  stopped viewer returns at once, raises nothing and posts nothing (so a `dock()` after a
  user's own `await viewer.stop()` posts no second `close`; Revision 6).

**`dock(deck, **kw)`** is a module function, not an override, so GATE X is unaffected.
- It keeps a module-level current viewer. If one exists, it awaits that viewer's `stop()`
  before constructing the next, so re-running a `dock()` cell leaks no subscriptions. The
  shell sees the old viewer's `close` before the new viewer's `announce` (re-docking, state
  table T12 then T6).
- After `start()` it awaits `viewer.wait_for_browser(timeout=15)`. A `TimeoutError` is caught
  and stated in one printed line. So the page's first hello prints in the `dock()` cell.
  Later reconnect hellos (iframe reload, drawer move) print in whichever cell is executing,
  or nowhere if none is. This is accepted and stated. Gates read the hello from
  `viewer.clients_seen`, never from printed output.

**GATE X** (the same discipline as `praxis/viz/browser.py:18-20`; re-derived in Revision 10
for a design with no vendored Python bytes at all). It asserts three things:
1. **Overrides.** The override set of `DockedViewer3D` over the pin's
   `pylabrobot.visualizer3D.server.Viewer3D` is exactly `{__init__, start, stop}` (AC-31,
   against the real pin in CI). A fourth override is a design regression. Stop, and upstream
   a transport hook to PLR.
2. **No PLR Python in the overlay, none modified.** No `plr_visualizer3d` package or other
   copy of PLR Python exists under `web-repl/`, and `viewer3d.py`'s only deviation from stock
   PLR state is the `PACKAGE_ROOT` rebind. Enforced by AC-31's **state snapshot** (round 11,
   C11-4): every entry of `vars(Viewer3D)` and of the `pylabrobot.visualizer3D.server` module
   dict is the identical object before `viewer3d.py` is loaded and after a viewer is
   constructed, started and stopped, except `PACKAGE_ROOT`. A patch such as
   `server.Viewer3D._mark_scene_dirty = ...` (the S4-C fourth-override case done by
   assignment) passes parts 1 and 3 but fails this.
3. **Static bytes.** Every file under `web-repl/overlay/assets/visualizer3d/` other than the
   transformed `index.html` is byte-identical to the pin's `static/`, each hashed in
   `VENDOR_MANIFEST.json`, and `vendor_visualizer3d.py --check` against the submodule exits 0
   (AC-30).

`praxis_viz3d` and `DockedViewer3D` live under `praxis/viz/`, so the R21 check (D7: no
`praxis_repl` under `praxis/viz/` outside the RST documentation form) continues to pass.
From sprint C it also covers `web-repl/overlay/assets/visualizer3d/`,
`web-repl/overlay/assets/visualizer3d-augmentations/` and `web-repl/shell/display/dock.js`,
each checked with `test -e` first (AC-31).

### D12. Deck panel behaviour uses the page's own public API. Selection colour is the page's.

PLR's page exposes `window.plrViewer` (`static/app.js:172-223`):
- `focus(name, viewName)` selects and frames a resource.
- `view(name)` sets `top`/`iso`/`front`.
- `resources()`, `stateOf(name)`, `camera()` and `stats()` answer questions without redrawing.

**The shell drives the panel through it**, calling across the frame: the iframe is
same-origin with no `sandbox`. Every call goes to the iframe currently in the panel, read
from the DOM at call time, and only in the D11 state `open-connected` (the only state with an
iframe, I1). In any other state Follow and Click do nothing, and Iso / Top / Front only
update the held preset. After every load of the panel's iframe (T2, T6, T11, T15, T16, T18),
`dock.js` re-applies the held preset with `plrViewer.view(preset)` once the page's
`plrViewer` exists **and `plrViewer.resources()` is non-empty**, i.e. after the first `scene`
has arrived (polled every 250 ms, given up after 10 s), since the `src` always carries
`view=top` (Revision 6). A `view()` issued before the first `scene` could be overridden when
the page frames the arriving scene (Revision 7, C7-7; AC-38 `preset_survives_reload`).
- **Preset.** `dock.js` holds the current view preset, initially `top`. Every focus call is
  `plrViewer.focus(name, preset)`, never `focus(name)`, whose default reframes from the iso
  direction (`app.js:180`) and would override the user's preset.
- **Follow** (on by default): when the active cell changes, focus the resource stamped on its
  first Praxis output whose stamp has a non-null `resource` (`stampOf`, D2). Ledger outputs,
  channel-owner error panels and generic panels are skipped; a cell with no such output
  leaves the camera unchanged.
- **Click** on any resource inside an output (a `data-praxis-res` hit) focuses it. This
  includes figures inside a ledger or an error panel, unchanged by the Follow rule.
- **Iso / Top / Front** set the preset and call `plrViewer.view`.
- The footer states the focused resource, and for a ledger row, its wells ("assay A1:H3,
  3 columns").

**Deviation from DESIGN.md**, which asks for "a rose outline in both places". The page's
selection box is its own colour (`SELECT = 0x1a4b8c`, `constants.js:118`) and fades after
`SELECTION_SHOWN_MS = 2000` (`:121`). Changing that means editing vendored code, which D11
forbids. So:
- The rose outline is persistent in the notebook output.
- In the deck panel, the page's transient selection plus camera framing stand in.
- A persistent 3D highlight is Next, and needs an upstream PLR API (OQ-5).

**Embed mode.** `embed.js` runs only when `location.search` has `embed=1`. The same query
string carries `viewer=<id>`, written by the shell only from an `announce` (D11 deck-panel
state table, I2) and read only by `socket.js`.
- It hides, from inside the page, the navbar (`.navbar`), the left tool rail
  (`#toolbar-left`), the stats footer (`#stats-panel`), the tree (`#sidepanel`) and its
  toggle strip (`#toolbar`). This goes through an injected stylesheet, `embed.css`, and does
  not crop the page.
- It sets the page ground to `#EEF1F4`.
- It forwards the page's `plr:status` and `plr:gone` events (`transport.js:35, 74`) to the
  parent window as `praxis:dock-status` CustomEvents. The navbar that normally shows the
  status is hidden. What `dock.js` does with a forwarded `plr:gone` is the state table's
  plr:gone event (D11: T14; ignored in every other state).

MVP hides the tree. DESIGN.md's "collapse behind a toggle" is Next.

**Motion slot.** The footer carries one reserved row, "Motion playback is not available for
this backend.", disabled, ≤ 36 px. It is always visible, so the height rule (D6) can be tested
with no test-only switch in product code. `viz3d-motion` is unmerged: STAR v1 driver only,
54 commits ahead and 76 behind main.

### D13. The display installs as a non-fatal bootstrap stage.

`praxis_bootstrap.praxis_main` is a fail-closed ledger (`praxis_bootstrap.py:289-421` on
origin/main a176bac7; `:289-398` at the base). A new step runs after step 12
(`stages.verify_identity()`, `:415`) and before `praxis:ready` (`:421`). The PLR 1.0 bump
added a `micropip.install("typing-extensions")` earlier in the ledger (~`:384`); the insertion
point is unchanged:

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
- **No selectors built from names.** Resource names are user-controlled. Modules find nodes
  by comparing `el.dataset.praxisRes === name` over candidate elements, never by
  interpolating a name into a `querySelector` string (D2).

### D15. At the pin, the liquid's identity is not available. Blue shows volume only.

The user decided: "Blue is volume, always ... The liquid's identity appears on hover and in the
text." The tracker no longer records liquids (read at 0.2.2; unchanged at the 1.0.0b1 pin,
the PLR 1.0 recon; the anchors below are 0.2.2's):
- `get_liquids` is deprecated, with the docstring "The volume tracker no longer tracks
  individual liquids." (`volume_tracker.py:122-138`, 0.2.2).
- `set_liquids` collapses to a volume (`:74-86`, 0.2.2).

Hover and text therefore show volume only. The colour rule is unaffected. **Decided by the
user, 260929:** "keep blue as volume, we can make things more complicated later." Volume only
is the MVP; identity returns when PLR tracks it. OQ-2 is closed.

### D16. New browser gates live in `repl_smoke.py`. CI is authoritative.

The harness is `scripts/repl_smoke.py` at the **repo root** (not under `web-repl/scripts/`).
Two new flags follow the shape of `run_notebook_check` (`repl_smoke.py:1226-1430` at the base
`fd987728`; on origin/main a176bac7 it starts at `:1482`): `ServedDir`, `chromium_launch_args`,
model-first output reads, and a `result` dict whose keys are the ACs. They do **not** copy its
run shape: `run_notebook_check` builds one `RESULT` and prints it once at the end
(`:1788` on origin/main a176bac7), and CI bounds it only by the job-level
`timeout-minutes: 45` (`.github/workflows/repl.yml:43` on origin/main a176bac7, `:47` on the
sprint A branch). The new checks are split into units, persisted per unit,
and resumable ("Preemption-safe harness design" below; Revision 7, C7-1).

**Import-time submodule dependency, removed in A1** (Revision 10 found it, the PLR 1.0 recon,
MAJOR-7; Revision 11 removes it, orchestrator ruling (a) on round 11 C11-3). `repl_smoke.py`
derives the expected PLR version from the submodule's `version.txt` **at import**: the
module-level tuple `NOTEBOOK_EXPECTED` (`:1450-1454` on the sprint A branch; `:1449` on
origin/main a176bac7) calls `expected_plr_version_prefix()` (`:1426-1441`), which raises
`VizCheckError` when `version.txt` is missing, so importing or loading the module by path
without an initialised submodule fails. A1 makes it lazy (about 6 lines): `NOTEBOOK_EXPECTED`
becomes a function, `notebook_expected() -> tuple[str, ...]`, returning the same three
strings, and its four use sites (`:1656`, `:1666`, `:1680` and `:4451` on the sprint A branch)
call it (once per `--notebook-check` run; the version is still read from `version.txt`, only
later). A regression test (A1, `web-repl/tests/test_repl_smoke_import.py`) proves both halves.
Consequences:
- **Everything may load `repl_smoke.py`.** The harness's pure functions (the unit table with
  listed keys, input hashing, stamp validation, the skip rule, the aggregate, and
  `run_scenario`'s ordering with injected browser, runner and watchdog seams) live in
  `repl_smoke.py` itself, each testable without a browser or the submodule;
  `test_repl_smoke_resume.py`, `test_unit_runner.py` (its CI-only real-Chromium case uses
  `resolve_chrome_path`) and the spike and sensitivity drivers load it by path, at collection
  or at module import as they need. No separate plumbing module exists (the Revision 10
  `scripts/repl_smoke_units.py` is dropped from the design; round 11, C11-3).
- **Spike drivers load it for the harness helpers.** A spike script (D17) loads
  `repl_smoke.py` by path for `ServedDir`, `chromium_launch_args` and `resolve_chrome_path`,
  in its driver (the S1 driver's input set resolves the Chromium path through it) and in its
  `--unit` branch, and hashes it into every unit's inputs (D17, the `harness` input).
- **Browser runs still need a dist built at the pin.** `--notebook-check` compares against
  the version derived from the submodule, and every browser unit serves a dist whose PLR wheel
  was built from the submodule, so local browser runs happen in a checkout branched from
  origin/main with `git submodule update --init external/pylabrobot` at the pin (not the main
  checkout while its submodule is at 0.2.2). Loading the module, `--resume` stamp evaluation,
  `--aggregate-only` and every pure-function test need no submodule. CI initialises the
  submodule and is authoritative ("Local runs" below).

- **`--display-check`** (sprint A adds its chrome scenarios; sprint B adds the rest). It seeds
  the drive with `web-repl/tests/fixtures/notebooks/display_check.ipynb` through
  `serviceManager.contents.save`, then executes cells **one at a time**. It never runs Run All
  on the error cells, except in the one scenario that proves Run All stops.
- **Persistence gate.** When `main` carries the persistence ladder, its first-save modal
  (`dialog#praxis-persistence-first-save`) would block the harness's saves in a fresh
  context. Both harnesses therefore add a context init script that sets
  `localStorage["praxis-repl-persistence-ack"] = "browser-only"` (an existing key; this epic
  adds none), and AC-23/AC-24 assert `persistence_gate_never_open`.
- **`--dock-check`** (sprint C). It launches a **full** Chromium, the
  `chromium-*/chrome-linux*/chrome` that `resolve_chrome_path` already selects, never
  `headless_shell`, with extra args `--use-angle=swiftshader --enable-unsafe-swiftshader`.
  - Measured 260929 by the orchestrator: the headless shell had neither WebGPU nor WebGL2;
    full Chromium drew the fixture deck on WebGL2/SwiftShader.
  - The result records `chrome_path` and the page's hello (`backend`, `renderer`), read by
    evaluating `viewer.clients_seen[-1]` in a cell (D11), not from printed output.

**Local runs.** Narrow only: one `--scenario <id>` at a time, or the driver resuming over
stamps. A direct `--scenario` run is bounded by its own watchdog at the unit's budget
("Preemption-safe harness design" below; Revision 8, C8-2). Browser and Playwright teardown
run inside that bounded region, before the stamp, and only `os._exit` follows the stamp
(Revision 9, C9-1). The process therefore ends within the budget plus `kill_tree`'s grace, and
the local form needs no outer `timeout`. `unit_runner.py --reap` refuses to run locally
without `--force` (C9-2). The real-Chromium case in `test_unit_runner.py` runs in CI only,
never locally (C9-5). Local runs need `dangerouslyDisableSandbox: true`, and per project
memory they should run with no `--chrome-path` before a local result is called green: local
chromium-1234 differs from CI's bundled build. Every local browser run (`repl_smoke.py`
scenario or spike `--unit`) serves a dist built with the submodule initialised at the pin
(above; after A1 this is a dist requirement, not an import requirement; Revision 11). pytest
runs one file at a time; there are no whole-suite runs (local compute limits).

#### Preemption-safe harness design (Revision 7, C7-1)

This applies the user's rule of 260929: any run longer than a few minutes persists each unit
of work as it completes, resumes by skipping verified-complete units, and bounds every
timeout to one chunk. Every browser scenario boots Pyodide, so each check runs for many
minutes and is covered by the rule.

**The unit is the scenario.** Each unit is independent: it gets a fresh browser context,
seeds the drive itself, boots its own kernel, and reads nothing from another unit. Budgets
are the per-subprocess timeout; the CI step timeout is the budget + 2 min. The budgets below
are estimates, not measurements. The first CI run of each scenario (A7, B10, C7) records its
wall time in the aggregate. A budget is revised only with the orchestrator's approval,
recorded in the sprint PR with the measured times, the same rule as D4's byte targets. A
revised budget must stay at least 1.5× the measured time and must never be turned into a
single whole-run timeout. *(Orchestrator, Revision 7.)*

| Unit | Check | ACs | Page(s) | Budget |
|---|---|---|---|---|
| `D1` | `--display-check` | AC-7 (Light) | one | 6 min |
| `D1-dark` | `--display-check` | AC-7 `d1_dark` | one | 5 min |
| `D2` | `--display-check` | AC-21, AC-22, AC-23, AC-25 (includes one kernel restart and one Run All) | one | 12 min |
| `D3` | `--display-check` | AC-24 (execute, save, reload, reopen) | one page, reloaded | 8 min |
| `D4` | `--display-check` | AC-26 | two contexts (one with `praxis-theme.css` blocked) | 6 min |
| `K1a` | `--dock-check` | AC-34, AC-35, AC-37 | one, 1440×900 | 10 min |
| `K1b` | `--dock-check` | AC-38 (lifecycle; **atomic**, keys in the fixed AC-38 order) | one, 1440×900 | 14 min |
| `K2` | `--dock-check` | AC-36 (tiers; atomic, fixed order stated in AC-36) | one, starting at 1152×800 | 15 min |
| `N-d` | `--dock-check` | AC-39(d) negative only; never part of the aggregate | one, 1600×900 | 6 min |

- **K1 is split** into K1a and K1b so that no unit has an unbounded budget and a lifecycle
  failure does not discard the drawing, Follow and live-state keys. "K1" in older text means
  both. K1b and K2 are atomic: their keys depend on each other's page state, so a unit is
  never resumed mid-way; a timeout or preemption recomputes the whole unit.
- **One subprocess per unit.** `--display-check --scenario <id>` and
  `--dock-check --scenario <id>` run exactly one unit in one process, with one browser. The
  driver starts each unit as its own subprocess through `unit_runner.run_unit` (below) with
  timeout = the unit's budget + 60 s, and forwards every hashed argument plus `--out-dir`,
  `--serve-dir` and `--chrome-path` to it. There is no whole-run timeout.
- **Shared unit runner** (Revision 8, C8-1). Playwright launches Chromium with
  `detached: true` on Linux (`playwright-core/lib/server/utils/processLauncher.js:108-111`),
  so Chromium leads its **own** process group: killing the unit's process group leaves a hung
  Chromium alive, and so does a CI step timeout. Every unit kind (these harness units, the
  D17 spike units and the D17 AC-39 negative units) therefore starts and kills units through
  one module, `scripts/unit_runner.py`, so the three cannot diverge. Its public functions:
  - `kill_tree(root_pid, token, grace_s=5)` (Revision 9, C9-2, C9-3):
    1. **Collect to a fixpoint.** Repeat two passes until neither finds a new pid:
       - walk `/proc/<pid>/task/*/children` recursively from `root_pid` **and** from every
         pid collected so far;
       - sweep every `/proc/<pid>/environ` for the exact NUL-delimited entry
         `PRAXIS_UNIT_TOKEN=<token>`. This catches a `setsid` grandchild whose parent already
         exited and which was re-parented out of the tree, and anything such an orphan
         forked since.
       Each newly found pid gets `SIGSTOP` as soon as it is found, so nothing forks or
       re-parents away mid-kill. The sweep matches the whole entry, never a prefix, suffix or
       substring. It **skips** a pid whose environ read raises `PermissionError`,
       `ProcessLookupError` or `FileNotFoundError`, or returns empty (a kernel thread or a
       zombie).
    2. **Guard against pid reuse (C9-3).** At discovery each pid is recorded with its
       `/proc/<pid>/stat` starttime (field 22). Where `os.pidfd_open` is available, a pidfd
       is also opened, and every later signal to that pid goes through
       `signal.pidfd_send_signal`. Otherwise the starttime is re-read immediately before
       each signal, and the pid is skipped if it is gone or its starttime differs. A pid
       that passes the check is a **verified** member.
    3. Collect the process group id of every verified pid. A group signal (`os.killpg`) is
       sent only while at least one verified member of that group is still alive.
    4. `SIGTERM` each of those process groups and each verified pid, then **immediately
       `SIGCONT`** each of them (Revision 10). A stopped process cannot run a signal handler,
       so without the `SIGCONT` a `SIGTERM` handler could never run, or fork, during the grace
       window, contradicting the fixpoint case (AC-42); the Revision 8-9 text had this
       contradiction, found by the A1a implementation.
    5. After `grace_s`, or as soon as every collected member is gone if that is sooner (the
       wait polls and ends early, `unit_runner.py:350-354`; round 11, C11-9),
       **re-freeze** (`SIGSTOP`) every verified pid still alive, repeat the
       step 1 fixpoint (which stops each new find, for example a child forked during the
       grace window by a `SIGTERM` handler), then `SIGKILL` each verified pid still alive, and
       each process group with a verified live member.
    Steps 1 to 5 run inside a `try` whose `finally` sends `SIGCONT` to every pid it stopped
    and that is still alive (C9-2). An exception or a Ctrl-C mid-walk therefore never leaves a
    process stopped. Only
    a `SIGKILL` of the caller can skip the `finally`. The stopped processes still carry the
    token, so `--reap` removes them: in CI its `if: always()` step does this, and locally
    `--reap --force` does. `kill_tree` never signals the caller, the caller's ancestors or
    the caller's own process group. It logs any survivor with `logging.error` (none is
    expected).
  - `run_unit(argv, timeout_s, *, env, cwd, grace_s=5) -> UnitOutcome(exit, timed_out,
    killed)`: mints a fresh `PRAXIS_UNIT_TOKEN` (uuid4) into the child's environment **at
    exec**, so it is visible in the child's `/proc/<pid>/environ`. Playwright passes the
    environment on to its driver and to Chromium. `run_unit` starts the child with
    `start_new_session=True`, and on expiry calls `kill_tree` with that token and `grace_s`.
    `UnitOutcome.killed` means "`kill_tree` ran" (Revision 10): true only on a timeout or
    when the caller raised while waiting. A unit that exits normally and leaves an orphan is
    **not** swept by `run_unit`; its own bounded teardown (below) and CI's `--reap` step cover
    that case.
  - `ensure_token()` (Revision 9, C9-4): if `PRAXIS_UNIT_TOKEN` is absent from the
    environment, mint one, flush stdout and stderr, and re-exec the current process with it
    set: `os.execve(sys.executable, sys.orig_argv, env)`, falling back to
    `[sys.executable, *sys.argv]` only where `sys.orig_argv` is absent, so interpreter flags
    (`-O`, `-X ...`) survive (`unit_runner.py:496-516`, `:509`; C10-4; round 11, C11-9). A
    token assigned to `os.environ` after exec is invisible in `/proc/self/environ`, so the
    sweep could not see it; the re-exec fixes that. It is a no-op when the token is already
    set, as it is under `run_unit`.
  - `Watchdog(budget_s, on_expire=None, *, token=None, grace_s=5, exit_fn=None,
    kill_fn=None)` (`unit_runner.py:549-638`; round 11, C11-9): a daemon timer, armed on
    construction. `on_expire` is optional (Revision 10). `token` defaults to
    `$PRAXIS_UNIT_TOKEN`, and construction **raises `RuntimeError`** when neither is set
    (`:579-583`), so `ensure_token()` (or an explicit `token=`) must come first. `exit_fn` and
    `kill_fn` default to `os._exit` and `kill_tree`; they are injectable so the lock semantics
    can be tested in-process. A unit's entry point arms it as its **first act** after
    `ensure_token()`, before it deletes any file or launches anything (C9-4). It owns the
    stamp lock:
    - `write_result(write)` runs the result or artifact writer under the lock and returns
      `True`; once the watchdog has fired, or a stamp is committed, it returns `False` and
      does not call the writer (`:604-610`; C10-2). A unit writes its result through it, so
      "no result after a timeout" holds even when the write races the expiry.
    - `commit(write_stamp)` runs the stamp rename under the lock, then disarms the watchdog.
      If the watchdog has already fired, it refuses and returns `False`. A second call to
      `commit` raises (Revision 10; `:612-622`).
    - `disarm()` stops the timer without committing (Revision 10).
    - On expiry, under the same lock, it does nothing if a stamp was already committed or it
      was disarmed.
      Otherwise it marks itself fired, calls `on_expire` if given (which deletes the unit's
      result file if present, writes the timeout marker and prints the timeout line; C9-6),
      then releases the lock, runs `kill_tree(os.getpid(), token)` over its own descendants
      and calls `os._exit(124)`. An `on_expire` that raises is logged with `logging.error`,
      and the kill and the exit still happen (Revision 10).
  - **Bounded teardown** (Revision 9, C9-1). Every unit, harness or spike, ends in this order,
    all inside the watchdog-bounded region:
    1. write the result or artifact through `Watchdog.write_result` (Revision 11, C11-9);
    2. close the browser (`browser.close()`) and leave `sync_playwright()`, which stops the
       node driver; an exception here is logged with `logging.error` and does not change the
       keys;
    3. run `kill_tree(os.getpid(), token)` over any descendant still alive (a no-op, with no
       grace wait, when the close succeeded and nothing is collected; a survivor is logged);
    4. flush stdout, stderr and the logging handlers;
    5. `Watchdog.commit` the stamp.
    After a successful commit the unit calls only `os._exit(stamp.exit)`. That call skips
    `atexit` handlers, non-daemon threads and the interpreter's own shutdown, so nothing can
    hang after the stamp. A hang in steps 1 to 4 is a timeout (exit 124, no stamp, no
    result).
  - `write_atomic(path, bytes)` (temporary file, fsync, rename), `dist_hash(dir)` (the
    `dist` input below) and `driver_input()` (the `driver` input below, C8-6). Exact
    contracts (Revision 10, as implemented in A1a):
    - `dist_hash(dir)`: one line `"<rel>\t<sha256>\n"` per file, where `<rel>` is the file's
      path relative to `dir` in posix form, lines sorted by `<rel>`; the result is the sha256
      of the concatenated lines. An empty directory hashes to the sha256 of nothing. A
      missing directory **raises** (a missing dist is never hashed as empty).
    - `driver_input()` reads `uv.lock`, which is gitignored (CI creates it); a missing
      `uv.lock` **raises**.
  - Public helpers `emit_line`, `read_proc_stat` and `reap()` (the function behind `--reap`).
    Their contracts are the merged module's docstrings and its tests; the spec does not
    restate them (Revision 10).
  - **Injectable seams.** The fault cases of AC-42 (environ reader, `/proc` reader, walk,
    pidfd availability, Playwright version, `uv.lock` bytes) are injected through
    keyword-only parameters, never through module globals the tests patch (Revision 10).
  - A CLI, `uv run python scripts/unit_runner.py --reap` (Revision 9, C9-2). It collects
    every distinct `PRAXIS_UNIT_TOKEN` value found by the environ sweep and runs `kill_tree`
    once per token (with no root, the sweep and the fixpoint only), excluding itself and its
    ancestors. `--token <t>` (repeatable) restricts the reap to those tokens (Revision 10).
    It **refuses** (exit 2, signalling nothing) unless the `CI` environment
    variable is set (GitHub Actions sets `CI=true`) or `--force` is given, so a stray local
    invocation cannot kill another session's units. It serves CI's `if: always()` reap step.
    Written with argparse and logging.
  - **Open risk: Chromium and the token** (Revision 10). The environ sweep assumes Chromium's
    processes keep `PRAXIS_UNIT_TOKEN=<token>` readable in `/proc/<pid>/environ`. Chromium
    may rewrite its process-title area, which on Linux can overwrite the environ region. The
    C10-1 positive control in the CI-only real-Chromium case settles it (a live Chromium
    process must be seen carrying the token before the kill is asserted). If that control
    fails, it is a **finding**, not a test bug: it is reported to the orchestrator, and the
    fallback is to match by process group and session recorded from the runner's own start,
    with the token sweep kept as the belt. Caveat on the fallback: Playwright launches
    Chromium with `detached: true` (`processLauncher.js:108-111`), which in Node makes the
    child a new process-group **and session** leader, so a session match alone would not
    reach it; the descendant walk (which reaches Chromium while its driver parent lives)
    remains the primary net. Which combination works is to be verified by the C10-1 control.
  Consumers load it by path (`importlib.util.spec_from_file_location` on
  `Path(__file__).resolve()` up to `scripts/unit_runner.py`), as the tests load
  `repl_smoke.py`; nothing edits `sys.path`.
- **`--scenario` is self-bounded** (Revision 8, C8-2). A direct `--scenario <id>` run (the
  local gate form in A7, B10 and C7, and every CI scenario step) first calls
  `unit_runner.ensure_token()`, which re-execs with `PRAXIS_UNIT_TOKEN` set if the driver did
  not set it (Revision 9, C9-4). Its first act after that is to arm a `unit_runner.Watchdog`
  at the unit's D16 table budget, before it deletes its files or launches the browser. On
  expiry the watchdog, under the stamp lock:
  - deletes `result.<id>.json` if present (C9-6);
  - writes `<out>/result.<id>.timeout.json` (`{unit, budget_s, started, expired}`,
    informational and never a completion marker);
  - prints one JSON line `{"unit": <id>, "status": "timeout", "budget_s": ...}`;
  - kills its descendant tree and exits **124** without writing a stamp.
  The stamp is committed through `Watchdog.commit`. Once the watchdog has fired, the stamp
  rename is refused. Once the stamp is renamed, the watchdog is disarmed. The browser and
  Playwright close before the commit ("Bounded teardown" above; C9-1), so a disarmed
  watchdog never leaves teardown unbounded. The three bounds are fixed in this order, so each
  outer bound is only a backstop:
  1. the watchdog at the budget;
  2. the driver's `run_unit` kill at budget + 60 s;
  3. the CI step timeout at budget + 2 min.
  If the driver's `run_unit` times out over a **valid** stamp, the stamp governs (C9-1). A
  valid stamp is one that exists, whose `inputs` equal the current inputs and whose
  `result_sha256` matches the result on disk. The unit is then judged from its result like
  any recomputed unit, is not listed in `timed_out`, and the driver logs the timeout with
  `logging.warning`.
- **Per-unit output.** Right after arming its watchdog (C9-4), and before any other work, a
  unit deletes its own `result.<id>.json`, stamp and timeout marker (Revision 8, C8-3), so an
  interrupted or timed-out re-run can never leave an earlier run's stamp standing. It then
  writes `<out>/result.<id>.json` (its keys, `pageerrors`, `chrome_path`, and its failing
  keys), runs the bounded teardown (C9-1), and, last, commits `<out>/result.<id>.stamp.json`
  through `Watchdog.commit`. Both files are written with `unit_runner.write_atomic`, the
  result inside `Watchdog.write_result` (Revision 11, C11-9). The unit
  then exits with `os._exit(stamp.exit)`. The stamp is the completion marker:
  `{unit, inputs: {name: sha256}, result_sha256, started, finished, exit, budget_s}`, where
  `exit` is the code the unit exits with (0 only if every listed key is present and holds).
  `<out>` is `--out-dir`, default `outputs/repl_smoke/<check>/`, gitignored. A run with a
  non-default `--serve-dir` or any `--neg` flag must also pass an explicit `--out-dir`; the
  harness exits 2 otherwise, so a negative or a copied dist can never overwrite the default
  results (Revision 8, C8-5).
- **Inputs hashed** (sha256), per unit:
  - `dist`: `unit_runner.dist_hash` of the served dist (`--serve-dir`, or the default build
    dir): the sha256 of the sorted `<rel>\t<sha256>\n` lines of every file under it;
  - `notebook`: `web-repl/tests/fixtures/notebooks/display_check.ipynb`;
  - `harness`: the sha256 of `scripts/repl_smoke.py` (Revision 11: the only harness file,
    `repl_smoke_units.py` being dropped, C11-3);
  - `runner` (Revision 9, C9-6): `scripts/unit_runner.py`, so a change to the kill, watchdog
    or write logic recomputes every unit, as it already does for spike and nd units (D17);
  - `chrome`: the string `<resolved chrome path>\n<chrome --version output>`;
  - `args`: the unit id, `--base-path`, the viewport list, and any harness-only negative flag
    (for example AC-39(e)'s `--neg drop-query`);
  - `driver` (Revision 8, C8-6): `unit_runner.driver_input()`, the sha256 of
    `<installed playwright version>\n<sha256 of uv.lock>`, the version read with
    `importlib.metadata.version("playwright")` (no subprocess). A Playwright upgrade or any
    lockfile change therefore recomputes every unit.
- **Listed keys.** The driver's unit table carries, per unit, its id, check, budget and the
  list of result keys its ACs name (the "listed keys"); AC-42 checks the table against this
  section and the AC headers.
- **Resume.** The driver (`--display-check` or `--dock-check` with no `--scenario`) runs its
  units in the table order (D1, D1-dark, D2, D3, D4; then K1a, K1b, K2). It **skips** a unit
  only if all of these hold (Revision 8, C8-3): its stamp exists; `stamp.exit == 0`;
  `stamp.inputs` equals the current inputs; `result_sha256` equals the sha256 of the result
  file on disk; and **every** listed key of the unit is present in that result and holds.
  Otherwise it recomputes the unit (the unit clears its own files first, above; the driver
  also clears them before launching it). A unit whose result has a failing or missing key is
  recorded and never reused, so a flaky failure is always retried. A timed-out unit leaves no
  stamp and no result, and counts as failed with `timeout` named. A `run_unit` timeout over a
  valid stamp is not a timed-out unit: the stamp governs and the timeout is logged
  ("`--scenario` is self-bounded" above; Revision 9, C9-1). `--fresh` ignores all stamps.
- **Aggregate.** The driver writes `<out>/result.json` and prints it:
  `{scenarios: {id: result}, reused: [{id, source, inputs, result_sha256}], recomputed: [id],
  timed_out: [id], missing: [id], stale: [{id, mismatched: [input name]}]}`, where `source`
  is the reused result's path, `timed_out` lists units with a timeout marker and no stamp (or,
  in the driver, whose `run_unit` call timed out and left no valid stamp; C9-1), and `stale` lists units whose stamp exists but does not meet the skip rule, naming each
  input whose hash differs. It exits 0 only if every listed key of every unit in its check
  holds. **The pass rule is unchanged** from the single-process design: resume changes how
  the work is scheduled, never which keys must hold.
- **`--aggregate-only`** (Revision 8, C8-4) recomputes nothing, starts no unit subprocess
  (the `chrome --version` probe for the `chrome` input is the only process it runs) and
  **never deletes** anything: a missing, timed-out or stale unit counts as failed and stays
  on disk for diagnosis. It computes the current inputs from its own arguments, so it must be
  given the same hashed arguments as the scenario runs (`--base-path`, and `--serve-dir` and
  `--out-dir` when non-default). CI's final step uses it.
- **AC-39 negatives run only their own unit** (a: `D1`; b: `K1a`; d: `N-d`; e: `K1b` with
  `--neg drop-query`), each against its own mutated copy of the dist and with its own
  `--out-dir` (D17; Revision 8, C8-5). The mutated dist has a different `dist` hash, so no
  negative can reuse, or be reused by, a real run, and its own out dir means it never
  overwrites one.
- **CI policy: no reuse across workflow runs.** Each workflow run is a fresh runner, and it
  recomputes every unit. CI never downloads an earlier run's artifacts, even when hashes
  would match, so a green gate is always evidence produced on this run's head. The only reuse
  in CI is inside one job: the final `--aggregate-only` step reads the stamps that the
  scenario steps of the same job just wrote. The layout, in the existing REPL job:
  - one step per unit, `uv run python scripts/repl_smoke.py --display-check --scenario <id>
    --base-path /praxis/` (and likewise `--dock-check`), each with step-level
    `timeout-minutes` = the unit's budget + 2, and `if: ${{ !cancelled() }}`, so one failing
    unit does not hide the others;
  - one aggregate step per check, `uv run python scripts/repl_smoke.py --display-check
    --aggregate-only --base-path /praxis/` (and likewise `--dock-check`), with
    `if: ${{ !cancelled() }}`; this is the step whose exit gates the PR. Its hashed arguments
    must equal the scenario steps' (Revision 8, C8-4: without `--base-path /praxis/` every
    stamp's `args` hash mismatches and the gate is permanently red);
  - one reap step with `if: always()`, `uv run python scripts/unit_runner.py --reap`, step
    `timeout-minutes: 1`, which kills any unit process a step timeout left behind (C8-1). It
    runs without `--force`, because GitHub Actions sets `CI=true` (C9-2);
  - one `actions/upload-artifact` step with `if: always()` that uploads every
    `result.<id>.json`, stamp, timeout marker and `result.json`, for diagnosis only;
  - the job-level `timeout-minutes` (`repl.yml:43` on origin/main a176bac7, `:45` on the
    sprint A branch) stays only as a backstop, raised to at
    least 45 plus the sum of the job's scenario step timeouts (60 after sprint A, 92 after
    sprint B, 137 after sprint C), so it is never the limit that ends a unit. The reap step's
    1 minute sits inside the 45-minute allowance and is not added to the sum.

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
- Runs use `bth run --project-slug praxis -- uv run --no-sync python3 scripts/spikes/<name>.py --out-dir <dir> [--resume] ...`.
  Use `bth`, never `uv run bth`, which silently skips enforcement.
- A run is verified by its **record**:
  `bth sql "SELECT id, status, outcome, exit_code, command FROM runs WHERE id LIKE '<prefix>%'"`.
  Run `bth compact` first if the run is not yet visible.
- Each spike's research note, `.praxia/docs/research/260929_notebook-display-s<N>-<slug>.md`
  (filed with `docs add`), cites the run id and names the D1 branch taken.

**Units, resume and chunking** (Revision 7, C7-2; the user's preemption rule of 260929). Each
spike is a driver over named units, not one process that writes its outcome at the end.

| Spike | Units (each its own browser context in its own subprocess) | Timeout per unit |
|---|---|---|
| S1 | `widget_a` (S1-A constructor walk), `widget_b` (S1-B stock-command widget), `split_right`, `css_limits`, `dock_layout_sizing`, `css_limits_refit`, `restore_layout_keeps_iframe`, `cell_hooks` (the five states), `windowing` (`windowingMode` and the re-attach signal), `neg_wrong_ctor` (negative control) | 4 min each |
| S2 | `live` (trusted live), `crafted` (untrusted reopened), `executed_saved_reopened`, `neg_script_onclick` (negative control, its own crafted notebook) | 5 min each |
| S3 | one declared bounded unit, `ipython_hooks`: (a), (b), (b′), (c) plain and top-level `await`, (d) and the negative control share one kernel, so they are one unit | 10 min |
| S4 | one declared bounded unit, `viewer3d_pyodide`: the imports (the pin's `pylabrobot.visualizer3D` from the dist's PLR wheel), construction, `start`, the loop checks, the scene bytes (and whether it carries any `mesh`), both `PACKAGE_ROOT`s, the walk time and the negative control share one kernel | 10 min |

- **Per-unit output.** A unit first calls `unit_runner.ensure_token()`, then arms its
  `unit_runner.Watchdog` (Revision 9, C9-4). Only then does it delete its own artifact,
  stamp and timeout marker (Revision 8, C8-3). It then writes `<out>/units/<name>.json`, runs
  the D16 bounded teardown (browser and Playwright closed, residual descendants killed,
  output flushed; C9-1), and commits `<out>/units/<name>.stamp.json` last through
  `Watchdog.commit`. Both files are written with `unit_runner.write_atomic` (the artifact
  inside `Watchdog.write_result`, Revision 11), and after the
  stamp the unit calls only `os._exit(stamp.exit)`. The stamp:
  `{unit, inputs: {name: sha256}, artifact_sha256, started, finished, exit, timeout_s}`.
  Inputs hashed: the spike script, `scripts/unit_runner.py`, the dist manifest (the same
  `dist` hash as D16, from `unit_runner.dist_hash`), the fixture (the seeded notebook or
  crafted notebook JSON, and for S4 the probe's kernel code; the PLR wheel that carries
  `pylabrobot.visualizer3D` is covered by the `dist` hash, Revision 10), `harness` =
  `scripts/repl_smoke.py` (which the driver and each `--unit` load by path for the harness
  helpers, D16 "Import-time submodule dependency, removed in A1"; the committed S1 probe and
  sidecar at A1b-1 omit it and are amended before the first run, A1), the chrome path and
  version, `driver` (the Playwright version and `uv.lock` sha256, `unit_runner.driver_input`,
  as in D16; Revision 8, C8-6), and, for a unit that builds on another unit's result, that
  unit's `artifact_sha256`. The S1 sizing, refit, restore and split units take the widget
  from `widget_a` or `widget_b`, so a recomputed widget unit invalidates them.
- **Chunked timeouts** (Revision 8, C8-1, C8-2). The driver starts each unit as its own
  subprocess (`<script> --unit <name> --out-dir <dir>`) through `unit_runner.run_unit`, with
  timeout = the table's timeout + 60 s. The unit itself arms a `unit_runner.Watchdog` at the
  table's timeout. On expiry the watchdog, under the stamp lock, deletes the unit's artifact
  if present (C9-6), writes `units/<name>.timeout.json`, kills its descendant tree (Chromium
  included, D16 "Shared unit runner") and exits 124 with no stamp. A timed-out unit is
  recorded as `timeout`. If the driver's `run_unit` times out over a valid stamp (inputs and
  `artifact_sha256` match), the stamp governs and the driver logs the timeout (D16; Revision
  9, C9-1). There is no whole-run timeout.
- **Completeness** (Revision 8, C8-7). A unit is **complete** when its artifact and a
  matching stamp exist. A probe that raises inside a unit is caught by the unit, recorded in
  the artifact as an `error` finding (`{type, message, traceback_tail}`, the tail capped at
  4 KiB), and the unit still writes its artifact and stamp: it is complete, the `error`
  finding counts toward `[outcomes]` exactly as the sidecar pre-registers (an `error` never
  satisfies a positive outcome, and a negative control that errors has not "failed as
  required"), and it is **never reused**. Only a timeout, or a crash that leaves no stamp,
  makes a unit **incomplete**.
- **`--resume`** skips a unit only if its stamp exists, `stamp.exit == 0`, its inputs equal
  the current inputs, its `artifact_sha256` equals the sha256 of the artifact on disk, the
  artifact has no `error` finding, and every field the sidecar pre-registers for that unit is
  present in it (C8-3, C8-7). Anything else is recomputed.
- **Outcomes over the full unit set.** The driver evaluates the sidecar's `[outcomes]` only
  when every unit is complete (by the definition above), reused or recomputed, over the full
  unit set. Reuse changes how the work is scheduled, never the `[outcomes]` criteria. A run
  with an incomplete unit, or preempted before that point, writes no outcome, and the next
  `bth run ... --resume` is a new run record.
- **Each sidecar pre-registers this design**: the unit list, the per-unit timeouts, the input
  set hashed for each unit (including `driver`), the resume rule (with `exit == 0`, no
  `error` finding and every pre-registered field present), the fields each unit's artifact
  must carry, the completeness definition above (artifact plus stamp is complete; a raised
  probe is a complete unit with an `error` finding that counts toward `[outcomes]` and is
  never reused; only a timeout or a stampless crash is incomplete), and the statement that
  `[outcomes]` are evaluated over the full unit set regardless of reuse. It is committed
  before the first run, as the hypothesis and outcomes are.
- **The research note records reuse**: for every unit, `recomputed` or `reused`, and for a
  reused unit, its source path, input sha256s and artifact sha256; plus the ids of any earlier
  partial runs. The run id it cites is the run whose outcome was evaluated.

**AC-39 sensitivity runs are pre-registered too** (Revision 7, C7-8). Their exit codes are
pass/fail findings cited in PRs, so they run through a tracked driver,
`scripts/negatives/260929_nd_sensitivity.py`, one bathos run per sprint, each with a sidecar
committed before its run: sprint A (A7: negative a), sprint B (B10: negative a) and sprint C
(C7: negatives b, c, d, e). So that each run has exactly one sidecar, named after its script
as the spikes' sidecars are, each sprint's run uses its own thin entry script,
`scripts/negatives/260929_nd_sensitivity_sprint_{a,b,c}.py`, which calls the shared driver
with a fixed negative set; each has its own `.bth.toml`. The driver follows the unit design
above: one unit per negative, each copying the pristine dist into its own directory
`/tmp/claude-1000/nd-neg/<negative>/dist/`, applying its one mutation, and running **only**
its own harness unit (D16) as a subprocess through `unit_runner.run_unit` (timeout = that
unit's budget + 60 s; the harness's own `--scenario` watchdog fires at the budget), with
`--serve-dir /tmp/claude-1000/nd-neg/<negative>/dist/` and its own
`--out-dir /tmp/claude-1000/nd-neg/<negative>/out/` (Revision 8, C8-5), so no negative writes
into the default `outputs/repl_smoke/<check>/` or into its own served dist (which would change
its `dist` hash). Its own records go to its `--out-dir`, default
`outputs/nd_sensitivity/sprint_<a|b|c>/`: `units/<negative>.json` plus a stamp, written after
clearing its own earlier files (C8-3) (inputs: the driver and entry script, `repl_smoke.py`,
`unit_runner.py`, the pristine and the mutated dist hashes, the chrome path and version, and
`driver`, C8-6). It supports `--resume`, which skips a negative only if its stamp exists with
`exit == 0`, its inputs and artifact sha256 match, its artifact carries every pre-registered
field (`harness_exit`, `failing_keys`, `outcome`), and its recorded outcome passed; a missed
negative is always rerun. A negative's `harness_exit` is the exit recorded in the harness
unit's stamp. If the driver's `run_unit` call times out over a valid harness stamp, the stamp
governs and the timeout is logged. A harness unit with no stamp is a timeout (D16; Revision
9, C9-1). Each sidecar has **one outcome per negative**: exit nonzero **and** the expected
key among the failing keys (a: `rail_state_after_run`; b: `viewer_resources`; d: the ≥ 1600
`panel_width` key; e: `late_iframe`), and for (c) zero grep matches. (d) may instead record
`skipped`, and the sidecar pre-registers that `skipped` passes only when the AC-1 sizing case
makes the ≥ 1600 key recorded-only (D6). A harness timeout (exit 124, no stamp, and no result file,
because the watchdog deletes it under the lock; C9-6) is nonzero but names no key, so it never passes a negative's outcome (Revision 8, consistency).
The completeness definition above applies: a negative unit whose driver code raised records
an `error` finding, counts as a failed outcome and is never reused.

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
  `HasTipError` and `NoTipError` from channel ops (not `*96` ops). Anything else keeps the plain
  traceback in Praxis styling; unresolvable, pending-residue and `*96` cases get the generic
  panel (D8).
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
- Distinct colours for multiple liquids in one well; liquid identity at all (D15; the user's
  decision of 260929, "keep blue as volume").
- Figures for `Container` subclasses other than `Well` (Trough, Tube, PetriDish, Trash): they
  get the name line and sentence only (D2).
- Layouts below 1024 px (the bottom sheet).
- A designed Dark variant (Dark gets token-mapped legibility only, D10). Changing the default
  theme (OQ-1).
- Several live viewers or notebooks at once. The most recent `announce` wins; the protocol
  carries ids, so this can be added later. With more than 4 live pages on one viewer, the
  client cap evicts in rotation (D11); accepted. When several notebooks have live kernels and
  the page learned the viewer only from a `query` answer, the viewer's kernel is unknown, so
  a restart of it leaves a frozen deck until the panel is closed and reopened (D11
  `viewerPanel`); accepted.
- An automatic ledger for cells run outside `RunLedger` (OQ-8).
- Structured error panels for `*96` (96-head) ops. They get the generic panel (D8 step 2).
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
  - Precedence when several apply: running > stale (dashed) > error > ran > not run.
  - "Edited since it ran" compares the source with a snapshot taken when an execution is
    observed in this page. After a reload, cells show ran or error from their saved outputs,
    and become stale only after an edit in this page.
  - Stale requires a run: a cell is stale only if it has a non-null execution count **and** a
    snapshot. An edited cell that never ran stays "not run".
- **Prompts.** The input and output prompts take no space. Outputs are inset under their code
  on the same sheet, divided by one rail-coloured hairline.
- **Light theme.** The page ground is `#EEF1F4`, the cell sheet `#FFFFFF`, and the syntax
  palette from D10 applies.
- **Tracebacks.** Non-PLR tracebacks keep JupyterLab's error output, restyled with brick
  accents and JetBrains Mono.

### 3.2 Output grammar (every resource output)

1. **Name line.** The resource name (Roboto Flex, `font-stretch` condensed, weight 600), then
   its PLR type and model in ink-soft: `source  Plate  Cor_96_wellplate_360ul_Fb`. The model
   string is PLR's `model` attribute, verbatim (the example is the design fixture's at 0.2.2;
   after B2's port to `cor_96_wellplate_360uL_Fb` it is whatever that attribute holds at the
   pin, and tests read it from the resource rather than hardcoding it).
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
   - Well: "assay A1 holds 50 µL of 360 µL."
   - Any other container (trough, tube, ...): the same sentence, with **no drawing** (D2).
     With an infinite `max_volume`: "{name} holds {v} µL."
   - Deck: "Tip carrier on rail 3, plate carrier on rail 9. 3 pieces of labware: tips_300,
     source, assay."
   - Number formatting: thousands separator, an en dash for ranges, `µL` preceded by a space,
     at most one decimal place.

**Deck** figures add a rail ruler along the front edge, numbered at rail 1 and every 5th rail.
Carriers are drawn in rail outline with condensed name labels, and labware in ink. The deck
tiers follow D5. *(Revision 10.)* At the pin PLR calls rails **tracks**: the ruler's count is
`deck.num_tracks` (30 for the STARLet; the deprecated `deck.num_rails` reads 32), and a
carrier's rail number is its track (`assign_child_resource(..., track=3)` places at the same x
as the deprecated `rails=3`; the PLR 1.0 recon). The labels 1, 5, ..., 30 are unchanged. The
user-facing word stays "rail", as DESIGN.md has it.

### 3.3 Run ledger and error panel

**Run ledger** (`with RunLedger(lh) as run:` → shown on exit):
- The name line reads "run  12 steps, 3 tip cycles, 2,400 µL moved". Steps, cycles and µL
  count top-level rows only (D9).
- A table has one row per top-level op, with columns **step, action, where, volume,
  channels**. Child rows (an op called inside another, D9) are indented under their parent
  and carry no step number.
- If the run ended in an error, the ledger is shown first (its failing row marked `error`),
  and the error panel follows it.
  - A new tip cycle, which starts at each pick-up, gets a hairline above it.
  - Aspirate and dispense rows carry a moonstone bar sized by volume.
  - Action names come from the glossary (section 3.5).
  - "Where" reads "source, column 1" for a whole column. Otherwise it is the compressed range
    "assay A1:H3", or a comma list.
- The table ends with the changed plates after the run, with the changed wells outlined in
  rose, under "The assay plate after the run. Wells this run changed are outlined."

**Error panel** (the four classes):
- A brick status rail.
- Inside a `RunLedger`, a first line "Step {n} of the run." (D9).
- A heading that states the fault and names the resource and wells.
- One body sentence with the numbers: committed `{avail}` and summed `{req}` (D8 step 4).
- A fix sentence.
- A drawing of the labware at committed volume, with the offending wells (D8 step 4) marked
  with a brick ring **and** a cross. A non-`Well` container owner gets no drawing (D2).
- "PyLabRobot raised `<Name>: <message>`", verbatim. This is the only place PLR's own number
  appears.
- `<details><summary>Show traceback</summary>`, capped per D4.

Templates. `{wells}` uses the compressed range of the offending set, and `µL` values are
formatted as in 3.2:

| Case | Heading | Body | Fix |
|---|---|---|---|
| TLL, owner is a well (aspirate) | "Not enough liquid in {plate} {wells}." | "Each well holds {avail} µL; the aspirate asked for {req} µL." Or, when the wells differ: "{wells} hold {min}–{max} µL; ...". Then: "Nothing was aspirated." | "Lower `vols` to {min} µL or less, or aspirate from wells that hold more." |
| TLL, owner is another container (aspirate) | "Not enough liquid in {container}." | "It holds {avail} µL; the aspirate asked for {req} µL across {n} channels. Nothing was aspirated." | "Lower `vols`, or aspirate from a container that holds more." |
| TLL, owner is a tip (dispense) | "The tip on channel {c} holds only {avail} µL." | "The dispense asked for {req} µL. Nothing was dispensed." | "Dispense {avail} µL or less, or aspirate more first." |
| TLV, owner is a well (dispense) | "Not enough room in {plate} {wells}." | "Each well has room for {avail} µL; the dispense asked for {req} µL. Nothing was dispensed." | "Lower `vols`, or dispense into emptier wells." |
| TLV, owner is a tip (aspirate) | "The tip on channel {c} can't hold {req} µL." | "It has room for {avail} µL. Nothing was aspirated." | "Aspirate less, or use larger tips." |
| HasTip, channel (pick up) | "Channel {c} already holds a tip." | "Pick up asked channel {c} for another." | "Drop or discard the tip first." |
| HasTip, tip spot (drop/return) | "{rack} {spot} already has a tip." | "{Action} asked to put a tip there." (`{Action}` is the outermost op, D8 step 2: "Drop tips", "Return tips" or "Discard tips".) | "Drop the tip into an empty position." |
| NoTip, channel | "Channel {c} has no tip." | "{Action} needs a tip on every channel it uses." | "Pick up tips before you {action}." |
| NoTip, tip spot (pick up) | "{rack} {spot} has no tip." | "Pick up asked for a tip that has already been taken." | "Pick up from a position that still has a tip." |

For the stamp, a tip owner counts as a channel owner: `resource: null` (D2). A raise that `resolve` returns `None` for (no owner, residue of uncommitted tracker state, or a `*96` op;
D8 steps 2, 4, 5) gets the generic panel: "PyLabRobot raised X: message" plus the traceback,
with no heading template. A raise outside the four classes, including the `RuntimeError` of a
bare `discard_tips()` or `return_tips()` with no tip mounted, gets no panel at all: the plain
IPython traceback, styled by Praxis CSS (D8).

With the fixture's error cell (`make_fixture.py:97-99` before B2's port to the pin: 80 µL
from assay A1:H1, which holds 50 µL), the panel reads "Not enough liquid in assay A1:H1." / "Each well holds 50 µL; the
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

**Click** on any resource focuses it in the deck panel with the current preset (D12). The
notebook output gets a persistent rose outline (the `is-focus` class, drawn by Praxis CSS).
The shell passes the exact `data-praxis-res` string through and matches nodes by
`dataset.praxisRes` (D14).

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

The `*96` names are used by the ledger only. Errors inside a `*96` op get the generic panel
(D8 step 2), so no error template uses them.

Nouns: **channel** (never "pip" or "pipette"), **well**, **tip**, **tip rack**, and
**deck panel** in every UI string. "Dock" is an internal name only.

### 3.6 Deck panel

It opens automatically, in the current tier's home (split right of the current notebook at
≥ 1280 px, the drawer at 1024–1279 px, D6), on the first `announce` a page
receives, i.e. after `viewer = await praxis.viz.viewer3d.dock(deck)` (D11 deck-panel state
table, T2). Its whole lifecycle (when it holds an iframe, when the `src` is written, when
`query` is sent, which text the body shows) is that table; this section only describes what
each state looks like. The layout:

- **Header:** the deck name, a Follow toggle (on), and Iso / Top / Front (Top is the page's
  default view, `renderer.js:263`).
- **Body:** in `open-connected`, the one iframe
  `assets/visualizer3d/index.html?embed=1&view=top&viewer=<id>`; in `open-waiting` and
  `open-lost`, one of the two texts below and no iframe (D11, I1, I5).
- **Footer:** the focused resource in words, then the one-row motion slot.

**States** (the texts for the D11 table's states; `closed` shows nothing):
- `open-waiting`: "No deck viewer is running.
  Run `viewer = await praxis.viz.viewer3d.dock(deck)` in a cell." Shown with no viewer
  known: after a reopen until the answering `announce` (or indefinitely with no answer),
  after a kernel `close` for the current viewer (within 5 s; for example after
  `await viewer.stop()`), after the viewer's kernel restarts or shuts down (within 5 s;
  T25, T26), and briefly while re-docking (T12 then T6).
- `open-lost`: "The deck view lost its connection. Close and reopen the deck panel, or run
  `dock(deck)` again." Shown only after `plr:gone` from the page in the panel (the page gave
  up after 60 s, possibly while the viewer is still live, see D11). It never claims the
  viewer is gone, because the shell cannot tell a stopped viewer from a busy kernel.
  *(Orchestrator, Revision 3.)* A kernel `close` never shows it (I6; *Round 4, C4-1*), and
  `plr:gone` is ignored outside `open-connected` (I4; *Round 5, C5-2*).

**Commands and tiers.** The registered command `praxis:toggle-deck-panel` is the table's
reopen event when the panel is closed (T4) and its close-panel event when it is open (T7,
T17, T22); closing the split tab, or hiding the drawer with its close button or Escape, is
also close panel. The tiers follow D6; crossing 1280 px is the table's tier-crossing event
(T5, T10, T15, T21).

---

## 4. Module and file plan

| Path | Action | Contents |
|---|---|---|
| `scripts/unit_runner.py` | create (A1); used by A2, A3, A7, B10, C1, C7 | The one shared unit runner (D16 "Shared unit runner"; Revision 8, C8-1; Revision 9, C9-1..C9-4): `kill_tree` (descendant walk over `/proc/<pid>/task/*/children` and the exact NUL-delimited `PRAXIS_UNIT_TOKEN=<token>` environ sweep, iterated to a fixpoint with `SIGSTOP` on each find, skipping unreadable or empty environs; pid-reuse guard by pidfd where available, else a `/proc/<pid>/stat` starttime check; group signals only with a verified live member; `SIGTERM` then an immediate `SIGCONT` so handlers run during the grace (Revision 10), then a re-freeze, a second fixpoint and `SIGKILL`; `SIGCONT` to every stopped live pid in a `finally`), `run_unit` (fresh token at exec, `start_new_session=True`, `kill_tree` on expiry, `grace_s=5`, `killed` = "`kill_tree` ran"), `ensure_token` (re-exec from `sys.orig_argv` with the token set), `Watchdog(budget_s, on_expire=None, *, token=None, grace_s=5, exit_fn=None, kill_fn=None)` (raises without a token; armed first; owns the stamp lock through `write_result`, which refuses once fired or committed, and `commit`, which raises on a second call; `disarm()`; on expiry deletes the result, writes the marker, kills the tree, exits 124, even if `on_expire` raises; Revision 11, C11-9), the bounded-teardown order (browser and Playwright closed before the stamp, only `os._exit(stamp.exit)` after it), `write_atomic`, `dist_hash` (`<rel>\t<sha256>\n` lines, posix, sorted; empty dir = sha256 of nothing; missing dir raises), `driver_input` (missing `uv.lock` raises), the public helpers `emit_line`, `read_proc_stat` and `reap()`, keyword-only injectable seams for the fault cases, and the `--reap` CLI (`kill_tree` per token found, `--token` repeatable to restrict; refuses without `CI` or `--force`). Merged on the sprint branch by A1a (Revision 10 makes this row say what that code does). Loaded by path by `repl_smoke.py`, the spike scripts and the sensitivity driver; no other module kills unit processes. argparse and logging. |
| `web-repl/tests/test_unit_runner.py` | create (A1) | AC-42 runner cases. All but one use real short-lived processes and no browser: a `setsid` grandchild does not survive `run_unit`'s timeout; a `setsid` grandchild whose parent has already exited is killed by the token sweep; a `Watchdog` child exits 124 at its budget with its `setsid` grandchild gone; a child that hangs after its stamp (a blocking `atexit` handler and a non-daemon thread) still exits with `stamp.exit` within budget + grace; the fixpoint catches a child forked during the grace by a sweep-found orphan; an unreadable or empty environ is skipped, and only the exact token entry matches; `SIGCONT` in the `finally` leaves no stopped process after an interrupted walk; `ensure_token` re-execs so `/proc/self/environ` carries the token; the pid-reuse guard; `kill_tree` never signals the caller's process group; `--reap` refuses without `CI` or `--force`, and with either it kills a token-carrying orphan; `driver_input` changes when the Playwright version or `uv.lock` changes (both injected); plus the Revision 10 contract cases (a `SIGTERM` handler runs because of the `SIGCONT`; `Watchdog(1)` with no `on_expire` (in a child that has the token, or with `token=` passed, since construction raises without one); a second `commit` raises; a raising `on_expire` still kills and exits 124; `dist_hash` line format, empty and missing dir; `driver_input` with no `uv.lock` raises; `--reap --token` restricts; `killed` false for a normal exit). The exception is one real-Chromium case (C9-5), which runs in CI only, never locally: after the C10-1 positive control, headless Chromium under `run_unit` leaves no process carrying the token (it resolves Chromium through `repl_smoke.py`'s `resolve_chrome_path`, which A1 makes import-safe without the submodule; Revision 11). Wired into `repl.yml` in A1, in the REPL job, which has Playwright's Chromium. |
| `scripts/spikes/260929_s{1,2,3,4}_*.py` (all four rows below) | create (A1–A3, C1) | Each is a unit driver per D17 "Units, resume and chunking": the units listed there, each started as `--unit <name>` through `unit_runner.run_unit` in its own subprocess and browser context (`repl_smoke.py` loaded by path, by the driver and the `--unit` branch alike, and hashed as the `harness` input; D16 "Import-time submodule dependency, removed in A1", Revision 11), self-bounded by a `unit_runner.Watchdog` at its timeout (armed first, after `ensure_token`); the unit clears its own files next; browser and Playwright teardown run before the stamp is committed, and only `os._exit(stamp.exit)` follows it (C9-1); `units/<name>.json` plus a stamp with input (including `driver`) and artifact sha256; a raised probe recorded as an `error` finding (complete, never reused); `--out-dir` and `--resume`; `[outcomes]` evaluated over the full unit set. The sidecar pre-registers the units, timeouts, hashed inputs, artifact fields, resume rule and completeness definition. |
| `scripts/negatives/260929_nd_sensitivity.py`, `260929_nd_sensitivity_sprint_{a,b,c}.py` + `.bth.toml` each | create (A7), used (B10, C7) | The AC-39 sensitivity driver and its per-sprint entry scripts and sidecars (D17, C7-8): one unit per negative, each on its own mutated dist copy (`/tmp/claude-1000/nd-neg/<negative>/dist/`) with its own `--out-dir` (`.../<negative>/out/`, C8-5), running only its own harness unit through `unit_runner.run_unit`; `driver` hashed; one outcome per negative. |
| `scripts/spikes/260929_s1_lumino_widget.py` + `.bth.toml` | create (A1) | Playwright probe over a built dist, `lab/` entry. It tries S1-A, then S1-B. It records `split_right_ok`, `css_limits_honoured`, `dock_layout_sizing_reachable` (the DockPanel `saveLayout`/`restoreLayout` path), `css_limits_refit` (inline px `min-width`/`max-width` then `parent.fit()`: does the widget take the new width?), `restore_layout_keeps_iframe` (does a `restoreLayout()` clamp reload an iframe in the widget?), the resulting D6 sizing case, the per-state cell hooks, the notebook's `windowingMode` and the cell re-attach signal, with the negative control from D17. Written with argparse and logging. Committed at A1b-1 (`60e892fe`, branch `feat/notebook-display-sprint-a`) with `harness` missing from its input set (`compute_inputs`, `260929_s1_lumino_widget.py:286-297`) and from the sidecar's `hashed_inputs` (`.bth.toml:109`), although its driver loads `repl_smoke.py` (`build_env`, `:267`); amended before the first run (A1; Revision 11, C11-3). |
| `web-repl/tests/test_s1_spike_driver.py` | create (A1; committed at A1b-1) | No-browser plumbing checks for the S1 driver: driver, unit, stamp, resume, completeness and outcome gating against stub probes, run as real `unit_runner.run_unit` subprocesses, plus the pure derivations (sizing case, AC-36 width-key status, cell-hook uniqueness, re-attach priority, validity) and the in-page JS checks under a JS engine. Its fake input environments gain the `harness` field with the A1 amendment. Already wired in `repl.yml` (`:264` on the sprint A branch). (Added to this table by Revision 11, C11-3.) |
| `web-repl/tests/fixtures/notebooks/s1_cell_states.ipynb` | create (A1; committed at A1b-1) | The S1 fixture notebook (the five state cells and the padding cell `cell_hooks` runs); hashed as the S1 `fixture` input (`.bth.toml:109`). (Added by Revision 11, C11-3.) |
| `web-repl/tests/test_repl_smoke_import.py` | create (A1) | The lazy-`NOTEBOOK_EXPECTED` regression test (D16; Revision 11, C11-3). It copies `scripts/repl_smoke.py` into a temporary tree holding only a `pyproject.toml` (so `find_repo_root`, `repl_smoke.py:315-328`, resolves there and no `external/pylabrobot/pylabrobot/version.txt` exists), loads the copy by path under a synthetic name, and asserts: the load succeeds; `notebook_expected()` then raises `VizCheckError`; after writing `version.txt` = `9.9.9` into the tree, `notebook_expected()` contains `"PyLabRobot 9.9.9+g"` (the prefix is still derived from `version.txt`); and no module-level name `NOTEBOOK_EXPECTED` remains. Written first and seen failing (the load raises before the change). Wired into `repl.yml` in A1. |
| `scripts/spikes/260929_s2_sanitizer.py` + `.bth.toml` | create (A2) | It writes a notebook JSON with crafted outputs to the drive, which is untrusted because it was never executed, reopens it, and records the chosen mimetype and survivorship per element and attribute. It repeats the check for the same bundle displayed live (trusted), and for a notebook executed, saved and reopened in the same browser, recording that path's trust state and mimetype (S2-T or not). Negative control from D17. |
| `scripts/spikes/260929_s3_ipython_hooks.py` + `.bth.toml` | create (A3) | It runs S3's (a), (b), (b′), (c) and (d) in the kernel; for (b′) it reads the output model's `metadata["text/html"]["praxis"]` through a seeded notebook, and records the IPython version, `run_code` path evidence and outputs by model. Negative control from D17. |
| `scripts/spikes/260929_s4_viewer3d_pyodide.py` + `.bth.toml` | create (C1) | It imports the pin's `pylabrobot.visualizer3D` from the dist's PLR wheel in the kernel (nothing staged; Revision 10), constructs and starts a throwaway `DockedViewer3D` prototype on the fixture deck, and records the stubs needed, the `scene` bytes and whether any model carries `mesh`, the stock and the rebound `PACKAGE_ROOT` (D11), and the time of the first `_models_on_disk(PACKAGE_ROOT)` walk over the rebound root. Negative control from D17. |
| `web-repl/overlay/assets/theme/praxis-theme.css` | modify (A4) | Appends sections for the status rail, prompt removal, output inset, the Light steel/sheet ground and syntax palette (Light only), `.praxis-out` token mapping (D3), the stale notice, the error panel, traceback accents, the hover readout, the focus ring, and the deck panel header and footer. It follows the header rules; no animation. |
| `web-repl/tests/test_display_css.py` | create (A4) | Text invariants on the new rules: no HC name, no `data-jp-theme-light`, no bare-`:root` `--jp-*`, no animation. Every colour in a `.praxis-*` rule is `var(--jp-*)`, `var(--praxis-*)` or one of the DESIGN hexes for moonstone, rose, rose ink or brick. The Light block carries `#EEF1F4`. |
| `web-repl/shell/display/index.js` | create (A5) | `mount(window)`: waits for `jupyterapp` and `restored`, then mounts `chrome`, and from sprint B `stale` and `interact`, and from sprint C `dock`. |
| `web-repl/shell/display/chrome.js` | create (A5) | Cell-state derivation from the model: a pure `cellState(model, {running, snapshot})`, where `snapshot` is the cell source captured when an execution is observed (or at first observation for a loaded cell), with precedence running > stale > error > ran > not-run (section 3.1); `stale` only with a non-null execution count and a snapshot. Plus the snapshot bookkeeping, an observed-execution event (cell, panel) that `stale.js` uses for `panelSession` (D7), and the DOM writer for `data-praxis-cell-state` and `data-praxis-exec`, per the S1 result. |
| `web-repl/shell/display/__tests__/fakes.js`, `chrome.test.js` | create (A5) | Fakes for cells, notebook, app, BroadcastChannel and the DOM, following `web-repl/shell/coxswain/__tests__/dom_stub.js`. |
| `web-repl/shell/praxis-shell.js` | modify, append only (A5) | One loader IIFE for `display/index.js`, gated to `/lab/`. Existing IIFEs untouched, including the persistence IIFE on `main`. |
| `web-repl/scripts/build_repl.py` | modify (A6, B9, C6) | A6: `stage_shell` (`build_repl.py:1016` on origin/main a176bac7) removes and then copies `shell/display/`, skipping `__tests__`, and `assert_dist_complete` (`:1193`) requires `shell/display/{index,chrome}.js`. B9: adds `stale.js` and `interact.js` to the required list. C6: adds `dock.js`, `assets/visualizer3d/index.html`, `assets/visualizer3d/vendor/three.webgpu.min.js`, `assets/visualizer3d-augmentations/{socket,embed}.js` and `embed.css`, `assets/python/praxis/viz/viewer3d.py`, and `assets/python/praxis/display/__init__.py`, the last from B8. (No `plr_visualizer3d` path: Revision 10.) |
| `web-repl/tests/test_display_staging.py` | create (A6), extend (B9, C6) | Stages to `tmp`: no `__tests__`, a stale file is removed, and `assert_dist_complete` raises on a missing required file. |
| `web-repl/design/notebook-display/make_fixture.py`, `fixture.js` | modify, regenerate (B2) | Port the design fixture to the 1.0.0b1 pin (Revision 10; the PLR 1.0 recon, MAJOR-6): non-deprecated names `hamilton_tip_carrier_L5`, `hamilton_plate_carrier_L5_ac`, `cor_96_wellplate_360uL_Fb`; `assign_child_resource(..., track=3)` (same x as `rails=3`); `deck.num_tracks` (30) instead of `num_rails`; imports from non-shim homes (D8). `tips_300` is now an `EmbeddedTipRack` (a `TipRack` subclass) with 7.2 mm tip spots; no code dispatches on the type-name string. `deck.serialize()` changed shape (`num_tracks`, no `rotation`/`barcode`), so `fixture.js` is regenerated from the port, never hand-edited, and `display.js` is checked against the new shape. `_as_in_kernel` rewrites paths to `/lib/python3.12/...`, but the kernel is CPython 3.14: it is corrected to the kernel's version or made version-independent. The volumes, wells and error cell keep their values, so AC-9's strings are unchanged. |
| `web-repl/tests/fixtures/notebooks/display_check.ipynb` | create (A7), extend (B10, C7) | The gate notebook. Boot cell, the fixture deck from `make_fixture.py`'s `assemble()` (as ported by B2; A7 adds only the D1 cells, and the fixture cells arrive with B10) with tracking on, cells that draw the deck, a plate and a tip rack, a `RunLedger` cell, one cell per error case, a sleep cell (running state), and a marker cell after an error (Run All stops). Not shipped in dist; the harness seeds it. |
| `scripts/repl_smoke.py` (repo root) | modify (A1, A7, B10, C7) | A1 (Revision 11, C11-3): the module-level `NOTEBOOK_EXPECTED` tuple (`:1450-1454` on the sprint A branch) becomes the function `notebook_expected()`, called at its four use sites (`:1656`, `:1666`, `:1680`, `:4451`), so importing the module no longer reads the submodule's `version.txt` (D16). A7 onward: adds `--display-check` and `run_display_check`, and later `--dock-check` and `run_dock_check`. Each is added to the "nothing to do" list and gets a `main()` branch. Both follow D16 "Preemption-safe harness design": `--scenario <id>` runs one unit in one process: `ensure_token`, then arming a `unit_runner.Watchdog` at its table budget as its first act (exit 124, timeout marker, result deleted, no stamp), then clearing its own files, and closing the browser and Playwright before the stamp commit, after which only `os._exit(stamp.exit)` runs (C9-1, C9-4, C9-6); with no `--scenario` the flag is the driver (one subprocess per unit through `unit_runner.run_unit` with budget + 60 s as timeout, stamp-matched resume requiring `exit == 0` and every listed key present and holding, aggregate `result.json` recording reused, timed-out, missing and stale units; a `run_unit` timeout over a valid stamp defers to the stamp and is logged); `--out-dir` (required with a non-default `--serve-dir` or any `--neg`), `--fresh`, `--aggregate-only` (never deletes), and the harness-only `--neg drop-query` (AC-39(e)). Hashed inputs include `driver` (C8-6) and `runner` (C9-6). The unit table (with listed keys), stamp writer, input hashing, reuse rule, `--out-dir` validation, `--aggregate-only` and the aggregate are pure functions in `repl_smoke.py` itself, each testable without a browser or the submodule (Revision 11: the Revision 10 `repl_smoke_units.py` split is dropped, C11-3); the CLI flags and the real-browser scenario bodies call them. Process start, kill and atomic writes come from `scripts/unit_runner.py` only. A7 adds the driver and D1/D1-dark, B10 adds D2–D4, C7 adds K1a, K1b, K2 and N-d. |
| `web-repl/tests/test_repl_smoke_resume.py` | create (A7), extend (B10, C7) | AC-42: loads `scripts/repl_smoke.py` by path at collection (import-safe without the submodule since A1; Revision 11, C11-3) and calls its pure functions directly with fake unit runners and injected seams (the `--out-dir` exit-2 rule and `--aggregate-only`'s no-delete, no-unit-subprocess behaviour are tested as functions returning their exit code, not through the CLI; C11-10); the `--scenario` watchdog case runs `run_scenario` in a short-lived child process with a hanging fake runner. Revision 9 adds: `run_scenario(<id>)` arms the `Watchdog` with that unit's table budget before anything else (C9-4); a hanging fake teardown exits 124 within budget + grace; a `run_unit` timeout over a valid stamp defers to the stamp (C9-1); a `runner` hash change forces a recompute (C9-6). |
| `web-repl/tests/test_repl_workflow_scenarios.py` | create (A7), extend (B10, C7) | AC-42: parses `repl.yml` and checks one step per unit with its step-level `timeout-minutes`, the `--aggregate-only` steps and that their hashed arguments equal the scenario steps', the `if: always()` reap step and upload, and the job-level backstop. |
| `web-repl/overlay/assets/python/praxis/display/__init__.py` | create (B8) | Exports `install`, `RunLedger` and `render`. `render(obj)` returns the bundle, for tests and explicit use. |
| `.../praxis/display/svg.py` | create (B1) | Path builders (circle as two arcs, rounded rect, cross), a text element with a font size in user units, number formatting, and `esc_text` / `esc_attr` (D2 escaping; the only escape helpers). No PLR import. |
| `.../praxis/display/floor.py` | create (B1) | D5 math: `nominal_scale`, `s_min` (labware and deck forms), `label_step_k`, `detail_level(labware, s_min)`. |
| `.../praxis/display/budget.py` | create (B1) | D4 cap and degradation ladder: `enforce(render_fn, levels) -> (html, level)`, and `cap_tail(text, 16384)` for tracebacks ("… N earlier lines omitted"). |
| `.../praxis/display/labware.py` | create (B2) | Plate, tip rack and well figures and sentences; sentence-only bundles for other containers (D2); well-range compression; the grid descriptor. |
| `.../praxis/display/deck.py` | create (B3) | Deck plan, rail ruler, carriers, labware at their detail level, the deck sentence. |
| `.../praxis/display/glossary.py` | create (B4) | `ACTIONS` and nouns (section 3.5). The only home of action strings. |
| `.../praxis/display/ledger.py` | create (B4) | `RunLedger` (D9): rows, in-flight nesting, top-level counts, tip cycles, the after-state figures, the bundle (stamp `resource: null`, `rev: null`, D2); `_ERROR_STEPS` and `step_for(exc)`. |
| `.../praxis/display/context.py` | create (B5) | `resolve(exc, tb) -> ErrorContext | None` (D8), with the frame filter on `glossary.ACTIONS`, the `*96` short-circuit, owner rules (a)–(e) (rule (d) parsing `"Channel N"`, `"<name>_volume_tracker"` and bare tip-spot names), `isinstance` checks against the non-shim `LiquidHandler`, `TipTracker` and `VolumeTracker` homes (D8), the committed offending set (per channel for a tip owner) and the pending-residue rule (owner outside the offending set → `None`). |
| `.../praxis/display/errors.py` | create (B6) | Panel rendering (section 3.3, including the tip-owner TLL row and the generic panel, with the step line from `ledger.step_for`; stamp per D2: the labware name or `null`, `rev: null`) and `handler(shell, etype, value, tb, tb_offset=None)`. |
| `.../praxis/display/stale.py` | create (B7) | Display session id, revs (none for `rev: null` stamps), subscriptions (idempotent through its own `_subscribed` set), the drawn-state digest filter (callbacks mark dirty; settling at `post_run_cell` and before each render bumps `rev` only when the digest changed; D7, Revision 10), the `post_run_cell` announcer. It posts nothing else (no session message; D7). It takes an injected `post(str)`. `import js` appears only inside `make_repl_poster()`, as in `browser.py:179-192`. |
| `.../praxis/display/install.py` | create (B8) | `install(shell=None)`: registers the D2 formatters (with the S3-B fallback: separate `text/html` / `text/plain` registration, the `text/html` function returning `(html, {"praxis": stamp})`), the D8 handler (with the S3-C fallback), the D7 hooks (with the S3-D fallback), and mints the display session id. It is idempotent. |
| `web-repl/bootstrap/praxis_bootstrap.py` | modify (B8) | Adds the D13 non-fatal stage between step 12 and `praxis:ready`. |
| `web-repl/shell/display/stale.js`, `interact.js` + tests | create (B9) | `stampOf` (D2, exported; the only stamp reader). D7 marking: `panelSession[P]` per notebook panel (from `chrome.js`'s observed executions and P's `sessionContext`), no "Changed since" on `rev: null` stamps, in-memory marks re-applied on `outputs.changed`, the S1 re-attach signal and `activeCellChanged`. D14 hover, keyboard, click and the live region; matching by `dataset.praxisRes`; the grid hit-test (pure). |
| `web-repl/tests/plr_contract.py` | modify (C3; B2–B8 as needed) | C3 adds `("pylabrobot.visualizer3D.server", "Viewer3D")` with a justification comment, for `viewer3d.py`'s own import (D11; Revision 10 dropped the Revision 1-9 `("pylabrobot.resources.resource", "Resource")` entry for vendored files). Each sprint B task adds an entry for any new `pylabrobot.*` submodule it imports, always from a non-shim home (the contract's "names no shim" test). |
| `web-repl/tests/test_display_{labware,deck,floor,budget,ledger,context,errors,stale,install,glossary,colorblind}.py` | create (B1–B8) | CPython tests. They load `praxis/display` by path under the synthetic package `_praxis_display_under_test` and never touch `sys.path` (README rule 2; the `test_browser_visualizer.py:33-51` pattern). They use real PLR resources at the 1.0.0b1 pin, `LiquidHandler` from `pylabrobot.legacy.liquid_handling`, and the chatterbox backend, imported from non-shim homes (D8; the backend's non-shim home is to be verified by B2 against `plr_contract.py`). |
| `web-repl/scripts/vendor_visualizer3d.py` | create (C2) | D11 vendoring of `static/` only (Revision 10), with `--src` defaulting to `external/pylabrobot` (the submodule at the pin) and `--check`, which verifies the committed tree's bytes and recorded commit against the source. Written with argparse and logging, and fails loud. |
| `web-repl/overlay/assets/visualizer3d/**` | generated, committed (C2) | The vendored static tree, `VENDOR_MANIFEST.json`, and the transformed `index.html`. |
| `web-repl/tests/test_vendor_visualizer3d.py` | create (C2) | AC-30. |
| `web-repl/overlay/assets/python/praxis/viz/viewer3d.py` | create (C3) | Imports the pin's `pylabrobot.visualizer3D` and subclasses its `server.Viewer3D` (Revision 10). The one-time `pylabrobot.visualizer3D.server.PACKAGE_ROOT` rebind to `tempfile.mkdtemp()` in the guarded, idempotent helper `_ensure_package_root()`, called first in `DockedViewer3D.__init__` (D11 "Trigger"; Revision 11, C11-13). `DockedViewer3D` (the 4-client cap with oldest-client eviction via `evict`, `bye` ending a connection, `query` answer, drop of non-JSON and unknown kinds, `stop` ending every connection, posting `close` and then unsubscribing from `praxis_viz3d`), `VirtualConnection`, `ChannelTransport` (injected), `make_viz3d_channel()` (the only `import js`), and `async def dock(deck, **kw)` (module-level current viewer stopped first; awaits `wait_for_browser(timeout=15)`). |
| `web-repl/tests/test_viewer3d_docked.py` | create (C3) | AC-31. Imports the pin's `pylabrobot.visualizer3D` from the root environment's PLR, and loads `praxis/viz` under a synthetic name. |
| `web-repl/overlay/assets/visualizer3d-augmentations/socket.js` | create (C4) | A classic script. The factory `makePraxisSocketClass(BroadcastChannelCtor, {acceptTimeoutMs})` is attached to the global, and the script assigns `window.WebSocket` when `document` exists. The viewer id comes from `location.search` (`viewer`); without it the socket posts nothing and closes after the accept timeout. With it, the socket posts `bye` on `close()`, on `pagehide` and on its accept timeout, ignores a late `accept`, and fires `onclose` on its own `evict` (D11). |
| `web-repl/overlay/assets/visualizer3d-augmentations/embed.js`, `embed.css` | create (C4) | D12 embed mode and status forwarding. |
| `web-repl/shell/display/__tests__/viz3d_socket.test.js` | create (C4) | Evaluates `socket.js` text against a fake global. Kept here so that no `__tests__` directory lives under `overlay/assets/`, which is staged wholesale (`build_repl.py:551-578`). |
| `web-repl/shell/display/dock.js` + tests | create (C5) | The deck panel widget per S1, the header, the footer, tiers and sizing per the D6 sizing-case table (CSS, DockPanel layout, inline px + `parent.fit()`, or S1-L), `parent.fit()` after every tier change inside the split, the drawer with its close button, Escape and tier crossing, Follow (skipping `resource: null` stamps, read through `stampOf`), the held preset (re-applied after each iframe load once `resources()` is non-empty, D12), layout sizing only at open and on tier changes when `restore_layout_keeps_iframe` is `false`, and the deck-panel lifecycle implemented exactly as the D11 deck-panel state table (four states, transitions T1–T27, invariants I1–I6; the §3.6 texts per state), acting on `praxis_viz3d` only for `announce` and the kernel `close`, and on the viewer's kernel's `sessionContext` for the kernel-restart event (`viewerPanel`, D11); `praxis:toggle-deck-panel`. |
| `.github/workflows/repl.yml` | modify (A1, A7, B10, C7) | Each sprint adds its pytest lines in the task that creates each test file (the per-file guard `test_repl_workflow_covers_tests.py` on `main` fails on an unwired file; A1 wires `test_unit_runner.py`, `test_repl_smoke_import.py` and `test_s1_spike_driver.py`, the last already wired at A1b-1), the `on.push.paths` and `on.pull_request.paths` filters (both lists, `repl.yml:17-37` on the sprint A branch, which today name only `scripts/repl_smoke.py`, `scripts/unit_runner.py` and the single S1 script under `scripts/`): A1 replaces `scripts/spikes/260929_s1_lumino_widget.py` with `scripts/spikes/**`, and A7 adds `scripts/negatives/**`, so a change to any spike or sensitivity script triggers the workflow (Revision 11, C11-11; every other new file is under the existing `web-repl/**`), its `bun test web-repl/shell/display` line in the coxswain job (A5), and its scenario steps per D16 "Preemption-safe harness design" (A7: `--display-check --scenario` D1 and D1-dark, plus the `--display-check --aggregate-only --base-path /praxis/` step, the `if: always()` `unit_runner.py --reap` step (no `--force`; Actions sets `CI=true`, C9-2) and the `if: always()` upload; B10: D2, D3, D4; C7: `--dock-check --scenario` K1a, K1b, K2, plus its `--dock-check --aggregate-only --base-path /praxis/` step), each scenario step with step-level `timeout-minutes` = budget + 2, and the job-level backstop raised to 60 / 92 / 137. No step downloads an earlier run's artifacts. |

**Files that must not change:**
- `web-repl/jupyter-lite.json` (D10; OQ-1 could change that later)
- `web-repl/scripts/inject_shell.py`
- the existing IIFEs in `praxis-shell.js`
- `web-repl/overlay/assets/visualizer/**` and `visualizer-augmentations/**`
- every byte vendored from PLR other than the transformed `index.html`
- no PLR Python is copied into the overlay at all (Revision 10; GATE X, D11)

---

## 5. Acceptance criteria

Gate shorthands:
- **[PY:file]** means `uv run python -m pytest web-repl/tests/<file> -q`, one file per
  process, as in `repl.yml`.
- **[BUN]** means `bun test web-repl/shell/display`.
- **[DISPLAY]** means the JSON keys of the aggregate `result.json` of
  `uv run python scripts/repl_smoke.py --display-check --base-path /praxis/` (the harness at
  the repo root), which runs each display unit as its own subprocess with its own timeout,
  resumes over stamp-matched units, and exits 0 only if every listed key of every unit holds
  (D16 "Preemption-safe harness design"). **[DISPLAY, scenario X]** names the unit whose
  `result.X.json` carries the keys; `--display-check --scenario X` runs that unit alone.
- **[DOCK]** means the same for `--dock-check` (units K1a, K1b, K2).
- Browser gates are authoritative in CI. Local runs follow D16.

### Sprint A: spikes and chrome

- **AC-1 (S1 recorded)**:
  - `bth sql` shows the S1 run with `status` completed and `outcome` not null. The run
    evaluated the pre-registered outcomes.
  - The sidecar's commit precedes the run (`git log` order).
  - The S1 research note names the widget branch (S1-A, S1-B or S1-C) and the sizing branch
    (CSS limits, DockPanel layout sizing, or S1-L), records `dock_layout_sizing_reachable`,
    the `windowingMode` and the cell re-attach signal, and records the negative control's
    failure.
  - The note also records `css_limits_honoured`, `css_limits_refit`, and the D6 sizing case
    (the table row) that AC-36 is keyed by.
  - The note records `restore_layout_keeps_iframe`: whether `restoreLayout()` keeps the
    widget's iframe loaded (no reload on a clamp).
  - The note lists every AC-36 width key with its resulting status (`asserted` or
    `recorded-only`), derived from the sizing case and `restore_layout_keeps_iframe`
    (D6 note, AC-36). *(Round 5, C5-1.)*
  - **Units** (Revision 7, C7-2; applies to AC-1, AC-2, AC-3 and AC-29): the sidecar lists
    the spike's D17 units, each unit's timeout, the hashed inputs (including `driver` and
    `unit_runner.py`), each unit's required artifact fields, the resume rule and the D17
    completeness definition (Revision 8, C8-7), and states that `[outcomes]` are evaluated
    over the full unit set regardless of reuse. The out dir holds `units/<name>.json` and a
    matching stamp for every unit, and each stamp's `artifact_sha256` equals the sha256 of its
    artifact. The note lists every unit as `recomputed` or `reused` (with source path, input
    sha256s and artifact sha256), lists every unit whose artifact carries an `error` finding
    (with its type and message), and names any earlier partial or timed-out run ids; the cited
    run is the one whose outcome was evaluated.
- **AC-2 (S2 recorded)**:
  - Same record and unit checks as AC-1 (units: `live`, `crafted`,
    `executed_saved_reopened`, `neg_script_onclick`).
  - The note contains the survivorship table: element and attribute × {trusted live,
    untrusted reopened (crafted), executed-saved-reopened}.
  - The note records the mimetype chosen for untrusted `{text/html, text/plain}`, the trust
    state and mimetype of the executed-saved-reopened path, and names the D1 branch for each
    path (S2-T, or one of S2-A, S2-A', S2-B, S2-C).
- **AC-3 (S3 recorded)**:
  - Same record and unit checks as AC-1 (one declared bounded unit, `ipython_hooks`,
    10 min).
  - The note records the IPython version seen in the kernel and the (a)–(d) results, and
    names the branch.
  - The note records the (b′) result: whether a `formatters['text/html'].for_type` function
    returning `(html, {"praxis": stamp})` yields the stamp at the output model's
    `metadata["text/html"]["praxis"]`. If (b) and (b′) both fail, the note says B7/B9 are
    stopped and escalated (D1).
- **AC-4 (theme invariants)** [PY:test_display_css.py] and [PY:test_theme_staging.py]:
  - Both pass. `test_high_contrast_theme_is_left_alone` and
    `test_jp_tokens_are_not_defined_on_bare_root` are unchanged and green.
- **AC-5 (cell-state logic)** [BUN]:
  - `cellState(model, {running, snapshot})` returns:
    - `not-run` for a cell with no execution count
    - `ran` after a successful execution
    - `running` while executing
    - `error` when an output has `output_type == "error"`
    - `stale` when the cell has a non-null execution count and a snapshot, and the source
      differs from the snapshot
  - Precedence: running > stale > error > ran > not-run. Cases: a running cell whose source
    was edited is `running`; an edited cell whose last output is an error is `stale`.
  - An edited cell that never ran (null execution count, no snapshot) is `not-run`.
  - After a reload (a loaded cell with saved outputs, snapshot taken at first observation):
    `ran` or `error` from its saved outputs, and `stale` only after an edit in this page.
  - The DOM writer sets `data-praxis-cell-state` and `data-praxis-exec`, and is idempotent.
- **AC-6 (staging)** [PY:test_display_staging.py]:
  - The test passes, including the stale-file and missing-file cases.
  - After `uv run python web-repl/scripts/build_repl.py --base-path /praxis/`, these both
    succeed: `test -f web-repl/dist/shell/display/index.js` and
    `! test -e web-repl/dist/shell/display/__tests__`.
- **AC-7 (chrome in the browser)** [DISPLAY, scenario D1: its own unit and subprocess, 6 min
  budget (D16); fresh context; Light theme set via `apputils:change-theme`]:
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
  - **Scenario D1-dark** (its own unit and subprocess, 5 min budget; fresh context, default
    JupyterLab Dark, no theme change), reported in `result.D1-dark.json` and in the aggregate
    under a `d1_dark` sub-object so the key names do not collide: the five `rail_state_*`
    keys above, `prompts_take_no_space`, and `rail_colors_match_dark` (rail
    grey equals the computed `--jp-border-color1`; the other states equal their section 3.1
    values).
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
  - `metadata["praxis"]` has keys `{v, kind, resource, rev, session, exec}`, with `exec`
    equal to the injected execution count.
  - **Hostile name**: a plate named `<b>&"'x` renders with its name escaped in text and in
    every attribute (`data-praxis-res`, `aria-label`, `data-praxis-grid`), and the
    `text/html` contains zero raw `<b>`. The grid attribute round-trips through
    `html.unescape` + `json.loads`.
- **AC-10 (tip rack and container)** [PY:test_display_labware.py]:
  - Tip rack `text/plain` == "72 of 96 tips left. Columns 1–3 used.".
  - The present-tip, core and taken-ring paths are each a single `<path>`.
  - For a single well: `text/plain` == "assay A1 holds 50 µL of 360 µL.". The text uses the
    fixture's `max_volume` value, formatted.
  - A rectangular well renders as a rect subpath.
  - A `Trough` gets `kind == "container"`, the name line and sentence, and **no** `<svg` in
    its `text/html`. A container with infinite `max_volume` reads "{name} holds {v} µL.".
- **AC-11 (deck repr)** [PY:test_display_deck.py]:
  - Ruler labels are exactly rails 1, 5, 10, 15, 20, 25, 30 for the STARLet deck
    (`deck.num_tracks` = 30 at the pin; the deprecated `num_rails` is not read; §3.2,
    Revision 10).
  - The carrier labels "tip_carrier" and "plate_carrier" are present.
  - The fixture deck's `text/html` is ≤ 49,152 bytes.
  - The deck sentence equals the section 3.2 example.
  - The wrapper carries `overflow-x:auto`, and the SVG carries the D5 `min-width`.
- **AC-12 (detail floor)** [PY:test_display_floor.py], parametrized over the fixture plate,
  the tip rack, the deck, a 384-well plate and a 1536-well plate. PLR resource definitions are
  available at the pin; the test names the exact definitions it uses.
  - For every figure and every text element: `font_size_user_units × s_min ≥ 11`. For the
    fixture STARLet deck this means `s_min ≈ 0.771` (D5 worked check), not 0.6.
  - A synthetic deck narrower than 880 mm (fitted `s_n > 1`) meets the same text and well
    checks, with `s_min = max(0.88 · s_n, 0.6)`.
  - For every drawn well or tip: `diameter_mm × s_min ≥ 4`; otherwise the labware is drawn as
    a block.
  - The 384- and 1536-well plates use square cells, with label steps equal to the D5 `k`.
  - A deck whose fitted scale is below 0.6 is emitted at 0.6 with horizontal scroll.
- **AC-13 (byte cap)** [PY:test_display_budget.py]:
  - Every fixture bundle has `text/html` ≤ 65,536 bytes and meets its D4 target. A missed
    target fails with the measured size; changing a target needs the orchestrator's approval
    in the sprint PR (D4).
  - A synthetic deck carrying 20 plates of 1536 wells degrades first to blocks and then, if
    still over, to summary-only. Its `text/html` is ≤ 65,536 bytes at every level, and the
    omission sentence is present when the drawing is dropped. At level 1, blocked labware
    carries no `data-praxis-grid`.
  - `cap_tail` on a synthetic 200-frame traceback keeps the tail, stays ≤ 16,384 bytes, and
    starts with "… N earlier lines omitted" with the right N.
  - [PY:test_display_errors.py]: an error panel over a real error with a 200-frame traceback
    has `text/html` ≤ 65,536 bytes.
- **AC-14 (ledger)** [PY:test_display_ledger.py], replaying `make_fixture.run_transfers`
  inside `RunLedger(lh, show=False)`:
  - 12 top-level rows in 3 tip cycles.
  - Actions in order: Pick up tips, Aspirate, Dispense, Discard tips, three times.
  - Each Discard tips row has exactly one child row, Drop tips, and the children do not
    change the step count, cycle count or µL moved.
  - Volumes 50, 100, 150 µL; channels 8.
  - `text/plain` starts "run  12 steps, 3 tip cycles, 2,400 µL moved".
  - The after-state assay figure marks 24 wells in rose (`stroke="#ED7A9B"`).
  - After exit: `LiquidHandler.aspirate is <the function captured before import>`, and no op
    name is in `vars(lh)`.
  - A `transfer` inside the context yields one Transfer row with nested children, not
    duplicate rows.
  - An op that raises inside the context marks its row `error` and re-raises the same
    exception object. `ledger.step_for(exc)` then returns that row's step, and a second call
    returns `None` (the entry is removed).
  - With `show=True` and an op that raises, `__exit__` displays the ledger bundle (a
    recording `display`) and the exception still propagates.
  - The ledger bundle's stamp has `kind == "ledger"`, `resource` null and `rev` null (D2).
- **AC-15 (error context)** [PY:test_display_context.py]. Real PLR at the 1.0.0b1 pin,
  chatterbox backend, tracking on unless the case says off. Each case raises the real error and
  asserts `resolve(exc, exc.__traceback__)`. No case asserts PLR's message text beyond what it
  states (tip-spot messages name the spot at the pin, D8). *(Revision 10: every case was
  re-checked against the pin by the PLR 1.0 recon; E13 and E15 were replaced because their
  0.2.2 setups no longer raise.)*
  - **E1** (fixture): aspirate 80 µL from assay A1:H1, which holds 50 → owner assay A1,
    op wells A1:H1, offending A1:H1, requested 80, available 50 (committed), action
    `aspirate`.
  - **E2**: setup: a tip on channel 0 preset with `lh.head[0].get_tip().tracker.set_volume(400)`
    (`set_volume` does not validate against `max_volume`, `volume_tracker.py:69-75`); then
    dispense 400 µL into a 360 µL well → TLV, owner a well. *(Revision 11, C11-6: Revision
    10's note that "a bare 400 µL dispense raises TLL on the tip first" was false. At the pin
    dispense queues the well's `add_liquid` before the tip's `remove_liquid`
    (LH:1472-1474), so the well's TLV is raised first with or without the preset; the preset
    is kept only so that a tip holding the dispensed volume is the realistic setup, and the
    case does not depend on it.)*
  - **E3**: aspirate more than the tip's `max_volume` (360 µL for the fixture's
    `hamilton_96_tiprack_300uL_filter`, not its 300 µL nominal; for example 400 µL) from a
    source well preset with `well.tracker.set_volume(500)`, so the well's removal cannot raise
    TLL first → TLV, owner the tip on channel 0. *(Round 4, C4-3; preset value fixed in
    Revision 10, MAJOR-9.)*
  - **E4**: `pick_up_tips` with tips already on → HasTip, owner the channel from the loop
    local, by rule (e) (no tracker frame).
  - **E5**: `drop_tips` onto an occupied spot → HasTip, owner the tip spot (PLR's message
    names the spot at the pin, e.g. `'tips_300_tipspot_A2 already has a tip.'`; not
    asserted).
  - **E6**: aspirate with no tips → NoTip, channel from `"Channel N"`.
  - **E7**: pick up from a taken spot → NoTip, owner the tip spot, by identity. At the pin it
    is raised before the queue loop (LH:727 through `TipSpot.get_tip`) with only `tip_spots`
    and `use_channels` bound in the LH frame; it leaves no pending residue.
  - **E8**: `well.tracker.remove_liquid(999)` outside any LH → owner from
    `thing` = `"<name>_volume_tracker"` (the well's deck name at the pin).
  - **E9** (repeated resource): aspirate 30 µL on 8 channels from one trough holding 100 µL
    committed → TLL, owner the trough, requested 240 (summed), available 100 (committed),
    offending = {trough}. The resolved numbers do not come from PLR's message.
  - **E10** (mixed wells): aspirate 80 µL from A1:H1 where A1:D1 hold 50 and E1:H1 hold 200
    → offending exactly A1:D1.
  - **E11**: `return_tips` onto an occupied spot → HasTip, owner the tip spot, `action ==
    "return_tips"` (the outermost ACTIONS frame), not `drop_tips`.
  - **E4-off**, **E6-off**: E4 and E6 with tracking off still raise and resolve to the same
    channel.
  - **E12**: dispense 100 µL from an empty tip → TLL, owner the tip on channel 0 (rule (c)),
    requested 100, available 0 (committed, per channel), action `dispense`.
  - **E13** (residue from direct tracker use; replaced in Revision 10, because at the pin
    E9's rollback leaves no residue and the old retry does not raise; setup verified by the
    orchestrator on the 1.0.0b1 wheel, 260929), step by step:
    1. `pick_up_tips` of one 300 µL filter tip (`max_volume` 360) on channel 0;
    2. `trough.tracker.set_volume(100)`, so the trough reads committed 100;
    3. `trough.tracker.remove_liquid(10)` called directly and **not** committed (committed
       100, pending 90);
    4. `lh.aspirate([trough], vols=[95.0], use_channels=[0])` raises
       `TooLittleLiquidError: Not enough liquid in container: 95.0uL > 90.0uL.`, although
       95 ≤ committed 100.
    → `None`: the owner (the trough) is not in the committed offending set (95 ≤ 100). The
    test also asserts the failed op's rollback: afterwards the trough's pending volume is
    back to 100.
  - **E14** (pending residue; confirmed at the pin): a `pick_up_tips` on several channels that
    fails inside its queue loop (LH:755-761; not the pre-loop taken-spot check of E7, which
    leaves no residue) leaves earlier channels with pending tips; a second pick-up on those
    channels raises `HasTipError` from that pending state, with no tracker frame and no
    committed conflict → `None`. Setup, step by step (round 11, C11-5, read against
    LH:755-761 and `legacy/tip_tracker.py:105-119`):
    1. `lh.pick_up_tips(tips["D1:D1"], use_channels=[3])` (channel 3 holds a committed tip);
    2. `lh.pick_up_tips(tips["A2:H2"])` (channels 0..7) raises `HasTipError`: channels 0, 1
       and 2 queue their pick-ups (`add_tip(..., commit=False)`, LH:761), then channel 3's
       `has_tip` check raises `"Channel has tip"` (LH:757-758) outside the `try`, so nothing
       commits or rolls back;
    3. precondition asserts: for `i` in 0, 1, 2, `lh.head[i].has_tip` is `True` (pending
       included, `:105-108`) and `lh.head[i].get_tip()` raises `NoTipError` (no committed tip,
       `:110-119`);
    4. `lh.pick_up_tips(tips["A3:C3"], use_channels=[0, 1, 2])` raises
       `HasTipError("Channel has tip")` at LH:758 on channel 0, with no tracker frame on the
       stack → rule (e) gives channel 0, which has no committed tip, so it is not in the
       committed offending set → `None`.
    "Committed" is `TipTracker.get_tip()` succeeding, never `has_tip` and never
    `TipSpot.get_tip()` (D8 step 4).
  - **E-96** (negative, `*96` out of scope): a real `aspirate96` that raises TLL → `None`
    (step 2 short-circuit). *Buildable (orchestrator, 260929, at 0.2.2; the recipe holds at
    the 1.0.0b1 pin, the PLR 1.0 recon):* on the fixture layout with the chatterbox backend,
    `pick_up_tips96(tips_300)` then `aspirate96(assay, volume=50)` raises
    `TooLittleLiquidError` (at 0.2.2: "Not enough liquid in container: 50.0uL > 0uL."; the
    message text is not asserted).
  - **E15** (TLV, tip owner, committed room; replaced in Revision 10, because at the pin the
    0.2.2 setup's first aspirate rolls back and the second does not raise). Synthetic
    tip-side residue, the E13 pattern on the tip's tracker:
    1. `pick_up_tips` of one 300 µL filter tip (`max_volume` 360) on channel 0;
    2. `lh.head[0].get_tip().tracker.add_liquid(200)` called directly and **not** committed
       (committed 0, pending 200);
    3. a source well preset with `well.tracker.set_volume(300)`; then
       `lh.aspirate([well], vols=[200.0], use_channels=[0])` raises
       `TooLittleVolumeError: Not enough space in container: 200.0uL > 160.0uL.` (room 160
       pending). The test **asserts** the class (a confirmatory assert, not a
       verify-else-stop branch; round 11, C11-6).
    → `None`: the committed room is 360 ≥ 200, so the tip owner is not in the committed
    offending set. Read from source at the pin (round 11 challenger): the aspirate queue runs
    inside the `try` (LH:1268-1273), the well's `remove_liquid(200)` succeeds (300 → pending
    100), and the tip's `add_liquid(200)` calls `validate_add_liquid`, whose free volume is
    `max_volume − get_used_volume()`, i.e. pending (`volume_tracker.py:91-97, 114-119`):
    360 − 200 = 160 < 200.
  - **E16** (NoTip, channel, drop-family op; verified 260929): `discard_tips(use_channels=[0])`
    with no tip mounted raises `NoTipError: Channel 0 does not have a tip.` → owner channel 0,
    action `discard_tips` (the outermost ACTIONS frame).
  - Negative: a `ValueError` → `None`.
  - Negative: a TLL raised by a tracker whose `thing` names nothing on any deck, with no LH
    frame → `None`.
  - Negative (verified 260929): bare `discard_tips()` with no tip mounted raises
    `RuntimeError: No tips have been picked up and no channels were specified.` → `None`
    (not one of the four classes; plain styled traceback, D8).
  - Negative (verified 260929): bare `return_tips()` with no tip mounted raises
    `RuntimeError: No tips have been picked up.` → `None` (as above).
- **AC-16 (error panel)** [PY:test_display_errors.py]:
  - For E1, the heading is exactly "Not enough liquid in assay A1:H1."
  - The body contains "Each well holds 50 µL; the aspirate asked for 80 µL." and
    "Nothing was aspirated."
  - The fix is the section 3.3 text.
  - Fault wells carry both a brick ring path and a cross path.
  - The drawing uses committed `tracker.volume`, checked on a well of the owner plate
    **outside** the failing op (Revision 11, C11-2): on the E1 setup, before the failing
    aspirate of assay A1:H1, `assay H12` gets `h12.tracker.set_volume(100)` and then a direct
    `h12.tracker.remove_liquid(40)` left uncommitted (committed 100, pending 60). A residue
    on a well **inside** the op would be erased by the failed op itself: its rollback covers
    every op resource (LH:1284-1289; `rollback()` sets `pending_volume = self.volume`,
    `volume_tracker.py:160`), and the orchestrator's E9 probe showed pending reset to
    committed on the failed op's resources, so the Revision 10 check would have passed
    vacuously. **Precondition assert** at render time (after the failed op, before the panel
    is built): `h12.tracker.volume == 100` and `h12.tracker.get_used_volume() == 60`. Then
    H12's drawn liquid radius equals `r · sqrt(100 / max_volume)` within 1e-3 mm (derived
    from committed `tracker.volume`) and differs from `r · sqrt(60 / max_volume)`. This is
    its own case built on the E1 setup, so E1's exact heading and body strings are unchanged
    (H12 is outside the op and outside the offending set).
  - The traceback is inside `<details>`, has no ANSI escape, and is HTML-escaped (a frame
    containing `<b>` appears as `&lt;b&gt;`).
  - `text/plain` contains the heading and the body.
  - E2–E7, E9, E10 and E11 each match their template row. E9 uses the "another container"
    row with requested 240 and available 100, and has no drawing. E10 marks exactly the
    offending wells. E11's body names "Return tips".
  - Body numbers are committed and summed: no number from PLR's message appears outside the
    "PyLabRobot raised" line (checked on E9, where they differ).
  - An error raised inside a `RunLedger` gets "Step {n} of the run." with the step from
    `ledger.step_for`.
  - **E12** matches the "TLL, owner is a tip (dispense)" row: heading "The tip on channel 0
    holds only 0 µL.", body "The dispense asked for 100 µL. Nothing was dispensed."
  - **E16** matches the "NoTip, channel" row: heading "Channel 0 has no tip.", and the body
    names "Discard tips" (the outermost op).
  - Stamps (D2): every panel has `kind == "error"` and `rev` null; E1's `resource ==
    "assay"`, E5's is the tip rack's name, and E4's and E12's (channel and tip owners) are
    null.
- **AC-17 (handler semantics)** [PY:test_display_install.py], with a fake shell recording
  `set_custom_exc`, `display` and formatter registrations:
  - Exactly the four classes are registered.
  - The handler returns a list of one string, `"<Name>: <message>"`.
  - The handler displays exactly one bundle.
  - An unresolvable context displays the generic panel. **E13** (AC-15, residue from direct
    tracker use; the Revision 10 setup) displays the generic panel, whose stamp has `resource`
    null. **E15** (AC-15, tip owner with committed room; the Revision 10 setup, whose raise
    AC-15 asserts, Revision 11) displays the generic panel likewise.
  - For an exception with a `ledger._ERROR_STEPS` entry, the handler's displayed bundle names
    that step, and the entry is gone afterwards. Order check with a real `RunLedger(lh)`
    (show on) around a failing op: the recorded `display` calls are the ledger bundle, then
    the panel.
  - `install()` is idempotent: a second call registers nothing new.
  - The S3-B and S3-C fallbacks each have a case that is selected when the fake lacks the
    primary API.
  - The S3-B case: the registered `text/html` function returns a tuple
    `(html, {"praxis": stamp})` whose stamp equals the one `render(obj)` puts at
    `metadata["praxis"]`, and the `text/plain` function returns the summary sentence.
- **AC-18 (staleness, kernel)** [PY:test_display_stale.py]:
  - Drawing `source` stamps `rev` r.
  - `source A1`'s tracker `set_volume(v)`, with `v` different from the 150 µL A1 holds in
    the fixture (for example 120; `set_volume(150)` changes nothing drawn, so the D7
    drawn-state filter correctly bumps nothing; round 11, C11-7), bumps `source` to r+1, and
    also the deck's rev if the deck was drawn.
  - One simulated `post_run_cell` posts exactly one message, carrying only the changed revs.
  - A cell with no change posts nothing.
  - The `json` field is ≤ 4096 bytes, and it switches to `"all": true` past the cap.
  - `stale.py` posts only `praxis:resource-changed` (no session message, D7): install plus a
    cell with no change posts nothing at all.
  - Registering a drawn output whose stamp has `resource` null or `rev` null (a ledger or
    error stamp, built by hand in the test) subscribes nothing (`_subscribed` unchanged) and
    adds nothing to any later announcement.
  - A pending-only change (a tracker `remove_liquid` queued and not committed; pending bump
    at `volume_tracker.py:111-112`) bumps the drawn resource's rev (D7).
  - **Rollback does not bump** (Revision 10, D7 drawn-state filter): with the trough drawn, a
    failed aspirate (the AC-15 E9 setup, whose rollback fires tracker callbacks at the pin)
    leaves the trough's rev and every other drawn rev unchanged, and the simulated
    `post_run_cell` posts nothing. A recording callback confirms the callbacks did fire, so the case is not
    passing vacuously.
  - **Settle before render** (Revision 10): a cell that sets a well's volume and then renders
    its plate stamps the settled rev, and that cell's own announcement carries the same rev
    (the fresh output is not older than the announcement).
  - The channel name `praxis_repl` appears in `praxis/display/stale.py` only.
  - `test -d` on the three paths, then the D7 "R21 check" over
    `web-repl/overlay/assets/python/praxis/viz/ web-repl/overlay/assets/visualizer/ web-repl/overlay/assets/visualizer-augmentations/`
    passes (R21: first `grep` 0 or 1, final `grep` exactly 1, by `PIPESTATUS`; Revision 11,
    C11-8). The plain `grep -rn "praxis_repl"` over these paths exits 0 on
    `main` because of three RST documentation mentions in `praxis/viz/transport.py:10,11,26`
    (Revision 10; the PLR 1.0 recon, BLOCKER-3); the check strips only that form. From
    sprint C the extended form in AC-31 replaces this one.
- **AC-19 (shell stale and interaction)** [BUN]:
  - `stale.js`, given stamps and announcements, marks only outputs with an older rev in the
    same session, marks other-session outputs "Drawn in an earlier session.", is idempotent,
    and never calls any model setter (the fake model throws on write).
  - Stamps are read only through `stampOf`: an output carrying its stamp at
    `metadata["text/html"]["praxis"]` (the S3-B carrier) is marked exactly like one carrying
    it at `metadata.praxis`.
  - `rev: null`: a ledger output and an error output stamped `resource: "assay"`, followed
    by an announcement raising `assay`'s rev, get no "Changed since" notice; both still get
    "Drawn in an earlier session." when their session differs from the panel's.
  - Per-panel session (D7): before panel P has an observed execution of a stamped cell after
    its kernel last started, no session mark is written in P; after one, `panelSession[P]`
    is that output's session. A fake kernel restart (P's `sessionContext` signal) followed by
    a re-run drawing cell makes the new session current and marks P's older outputs.
  - **Two panels**: panels P and Q with sessions sA and sB, each with an observed executed
    drawing cell; neither panel's outputs are marked "Drawn in an earlier session."
  - After the fake output node is replaced (`outputs.changed`) or detached and re-attached
    (the S1 re-attach signal), the mark is back exactly once.
  - `interact.js`:
    - The hit-test maps points to well ids for a 96 grid and a 384 grid, including edges.
    - ArrowRight from A1 gives A2, and ArrowDown from A1 gives B1, clamped at the edges.
    - The live-region text equals the hover text.
    - A click on `data-praxis-res` emits `focus(name)` to the injected dock API, with `name`
      exactly the resource name, including for AC-9's hostile name `<b>&"'x` (no selector is
      built; the fake `querySelector` throws if called with the name).
- **AC-20 (install and bootstrap)** [PY:test_praxis_bootstrap_loader.py] plus
  [PY:test_display_install.py]:
  - The stage order places the display install after `verify_identity` and before the
    `praxis:ready` post.
  - With an install that raises, `praxis:ready` is still posted, and one
    `praxis:display-error` message precedes it.
- **AC-21 (reprs live)** [DISPLAY, scenario D2: one unit and subprocess, 12 min budget, which
  also carries AC-22, AC-23 and AC-25 (D16)]:
  - `repr_cells_ok`: the deck, plate and tip-rack cells each have a model output with
    `text/html`, `text/plain` and a stamp read through `stampOf` (D2; `metadata.praxis`
    under S3-A, `metadata["text/html"].praxis` under S3-B).
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
  - `mark_survives_scroll`: the marked `source` output, scrolled out of view far enough to
    detach under the recorded `windowingMode` and back, still carries the notice exactly
    once.
  - `earlier_session_marked`: after `kernelmenu:restart`, re-running the boot cell and
    re-running a drawing cell (which sets the panel's current session, D7), a pre-restart
    output reads "Drawn in an earlier session."
  - `rerun_not_marked` (negative control for `earlier_session_marked`): in the same scenario,
    the re-run drawing cell's own new output does not contain "Drawn in an earlier session."
  - `persistence_gate_never_open`: `dialog#praxis-persistence-first-save` was never open
    during the scenario (D16); trivially true when `main` lacks the ladder.
- **AC-24 (trust loss)** [DISPLAY, scenario D3: its own unit and subprocess, 8 min budget; it
  executes its own drawing cells, then saves, reloads and reopens the notebook]:
  - `no_script_in_bundles`: the saved JSON has zero `<script` in any output.
  - `reopened_branch` equals the S2 branch recorded in AC-2 for the executed-saved-reopened
    path (this scenario is that path).
  - `persistence_gate_never_open`, as in AC-23.
  - Branch-conditional keys:
    - **S2-T**: `svg_in_dom` and `liquid_fill_computed` (moonstone), as for live outputs.
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
- **AC-26 (High Contrast)** [DISPLAY, scenario D4: its own unit and subprocess, 6 min budget;
  theme set to "JupyterLab Dark High Contrast"]:
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
  - Same record and unit checks as AC-1 (one declared bounded unit, `viewer3d_pyodide`,
    10 min).
  - The note lists the stubs required (possibly none), `call_later` support, the fixture
    `scene` bytes and the time of the first `_models_on_disk(PACKAGE_ROOT)` walk, and names
    the branch.
  - The note records the stock `PACKAGE_ROOT` resolved in the kernel (expected inside the
    installed PLR package in site-packages; Revision 10), the rebound root (D11), and states
    that the timed walk ran over the rebound root.
  - The note records that the pin's `pylabrobot.visualizer3D` was imported from the dist's
    PLR wheel with nothing staged, and whether the fixture's first `scene` carries any `mesh`
    under the rebound root (Revision 10).
- **AC-30 (vendoring; GATE X part 3)** [PY:test_vendor_visualizer3d.py], plus
  `uv run python web-repl/scripts/vendor_visualizer3d.py --check`, which reads the submodule
  `external/pylabrobot` at the pin by default and exits 0 locally (with the submodule
  initialised) and in CI (Revision 10: no separate PLR checkout step):
  - Every static file other than `index.html` has a sha256 equal to its source in the pin's
    `pylabrobot/visualizer3D/static/`.
  - `index.html` has 0 `{{`, exactly one `socket.js` tag, which is the **first** `<script`
    element in the document and is immediately followed by the original `index.html:319`
    `<script` tag (the classic gif.js tag), and exactly one `embed.js` tag before `</body>`.
  - 0 `https://` in `index.html`, and 0 `cdn.jsdelivr.net` in the whole vendored tree.
  - `VENDOR_MANIFEST.json` records the source commit (the pin,
    `786ac2c4e4f7afe37885af2d98ff5b0afe274c67`) and every file with its sha256.
  - `--check` exits nonzero, naming the path, on a synthetic source whose one static file
    differs, and on a synthetic source whose `HEAD` differs from the recorded commit.
  - Running the vendor script twice gives identical manifests.
  - `! test -e web-repl/overlay/assets/python/plr_visualizer3d` (no PLR Python is vendored;
    GATE X part 2).
- **AC-31 (DockedViewer3D)** [PY:test_viewer3d_docked.py], CPython, with a recording channel,
  against the pin's `pylabrobot.visualizer3D` from the root environment's PLR:
  - GATE X part 1: `{n for n in vars(DockedViewer3D) if callable(getattr(Viewer3D, n, None))} == {"__init__", "start", "stop"}`,
    where `Viewer3D` is `pylabrobot.visualizer3D.server.Viewer3D` and
    `DockedViewer3D.__mro__[1] is Viewer3D`.
  - GATE X part 2 (Revision 10): `viewer3d.py`'s `pylabrobot` imports (by AST) are
    `pylabrobot.visualizer3D` modules plus any contract-listed resource modules, and
    `grep -rn plr_visualizer3d web-repl/overlay/ web-repl/scripts/` exits 1 (the tests
    directory is not searched, so this test's own literal cannot match).
    [PY:test_contract_covers_imports.py] passes with
    `("pylabrobot.visualizer3D.server", "Viewer3D")` in `plr_contract.CONTRACT`.
  - **GATE X part 2, state snapshot** (Revision 11, C11-4). In a test whose process has not
    yet loaded `viewer3d.py`: import `pylabrobot.visualizer3D.server` and take
    `before_cls = dict(vars(Viewer3D))` and `before_mod = dict(vars(server))`. Then load
    `viewer3d.py` (synthetic name), construct a `DockedViewer3D` on the fixture deck with the
    recording channel, `await start()`, `await stop()`, and take `after_cls` and `after_mod`
    the same way. Assert: the key sets are equal, and for every key other than
    `PACKAGE_ROOT`, `after[k] is before[k]` (identity, not equality), in both dicts;
    `PACKAGE_ROOT` differs (the rebind). Negative control: the same comparison function, run
    after the test itself assigns `server.Viewer3D._mark_scene_dirty = lambda self: None`
    (undone afterwards), reports that key, so the snapshot is not vacuous. The test restores the stock `PACKAGE_ROOT` afterwards. If stock PLR code itself
    rebinds a `server` global or a `Viewer3D` attribute during construct/start/stop (so the
    check fails with no Praxis patch), C3 stops and reports; the orchestrator rules on an
    allowlist (to be verified by C3).
  - With `websockets.serve`, `threading.Thread` and `webbrowser.open` monkeypatched to raise,
    `start()` succeeds.
  - An `open` from client X yields `accept`, then a `msg` whose `data` decodes to event
    `scene`, then `state`, all addressed to X only.
  - A `msg` hello (the shape from `transport.js:39-53`) appends to `clients_seen`.
  - `set_volume` on a well yields a `state` message after the loop turns.
  - `assign_child_resource` yields `scene` or `moves` after `SCENE_DEBOUNCE_S`.
  - The fixture's first `scene` message contains no `mesh` key on any model.
  - `stop()` posts `close`, deregisters every callback (`_subscribed` empty), and afterwards
    no `_handler` task is pending (every `VirtualConnection` got its sentinel).
  - A second `stop()` on the same viewer raises nothing and posts nothing; a `dock()` after
    a user's own `stop()` posts no second `close` for the old id (D11, Revision 6).
  - **Stopped viewer leaves the channel** (Revision 7, C7-3): after `stop()`, the recording
    channel shows the viewer's listener removed and its channel closed; a `query` then gets
    no `announce` from it, and an `open` addressed to its id gets no `accept`. After a second
    `await dock(deck)`, a `query` yields exactly one `announce`, carrying the new viewer's id.
  - **Second dock**: a second `await dock(deck)` in the same process stops the first viewer
    (its `_subscribed` empty, a `close` with the first viewer's id posted) before the second
    `announce`.
  - `query` yields one `announce` for the current viewer.
  - **Client cap** (eviction): with 4 open clients, a fifth `open` gets `accept`; the
    oldest client gets `evict` (addressed to it only), its `_handler` task ends, and
    `_clients` stays at 4.
  - `bye` from a client ends its `VirtualConnection`: its `_handler` task ends and it leaves
    `_clients`.
  - **`PACKAGE_ROOT` rebind**: loading `viewer3d.py` leaves `PACKAGE_ROOT` unchanged (the
    rebind is not at import; D11 "Trigger", Revision 11, C11-13). After the first viewer is
    constructed, `pylabrobot.visualizer3D.server.PACKAGE_ROOT` is an existing, empty directory
    different from the value it held before that construction, and a second viewer does not
    rebind it again (calling `_ensure_package_root()` again leaves it unchanged). Each such
    test loads `viewer3d.py` fresh under a synthetic name, so the guard starts unset, and
    restores the stock value afterwards. Load-bearing check
    (Revision 10; the stock root is the installed PLR package, which the test never writes
    into): **after** loading `viewer3d.py` and **before** the first construction, the test sets `PACKAGE_ROOT` to a temporary
    directory holding a `.glb` named after a fixture model (standing in for the stock root's
    63 models) and clears the `_models_on_disk` cache for it. Positive control: the inherited
    scene build over that directory, with no rebind, puts a `mesh` key on that model. Then,
    after the first viewer's rebind, the first `scene` message has no `mesh` key on any model.
    If the positive control finds no `mesh`, C3 stops and reports (the check would be
    vacuous).
  - A non-JSON message and a message with an unknown `kind` are ignored: no exception, no
    post.
  - `dock()` with a fake viewer whose `wait_for_browser` raises `TimeoutError` returns the
    viewer and prints one line stating the timeout.
  - `grep -c praxis_viz3d web-repl/overlay/assets/python/praxis/viz/viewer3d.py` ≥ 1.
  - R21, extended from sprint C: `test -d` on the five directories
    (`web-repl/overlay/assets/python/praxis/viz/`, `visualizer/`, `visualizer-augmentations/`,
    `visualizer3d/`, `visualizer3d-augmentations/`, the last four under
    `web-repl/overlay/assets/`) and `test -f web-repl/shell/display/dock.js`, then the D7
    "R21 check" over all six paths passes (its `PIPESTATUS` rule; the plain grep exits 0 on the
    `transport.py:10,11,26` documentation mentions; Revision 10).
- **AC-32 (socket shim)** [BUN]:
  - `readyState` goes `CONNECTING` → `OPEN` on `accept`.
  - `send` while `CONNECTING` throws a `DOMException`-named `InvalidStateError`.
  - `onclose` fires on kernel `close` and on no `accept` within 3 s (fake clock).
  - The statics equal `{0, 1, 2, 3}`.
  - Messages for another `client` or `viewer` are ignored.
  - `close()` posts `bye` exactly once (a second `close()` posts nothing).
  - A `pagehide` event posts `bye` exactly once; the accept timeout posts `bye` exactly once.
  - A late `accept` (after the timeout) is ignored: `readyState` stays `CLOSED` and
    `onopen` does not fire.
  - `evict` addressed to this client fires `onclose`; an `evict` for another client is
    ignored.
  - The page-side shim never posts a message of kind `close`.
  - **No viewer**: loaded with no `viewer` parameter, the shim posts nothing at all and fires
    `onclose` after 3 s (fake clock). With `?viewer=v1`, `open` carries `viewer: "v1"`.
- **AC-33 (staging and offline)**:
  - [PY:test_display_staging.py] passes with the C6 paths.
  - After a build, `jq '.sources[].path' web-repl/dist/assets/wheels/manifest.json` lists
    `assets/python/praxis/viz/viewer3d.py` and no path under `assets/python/plr_visualizer3d/`
    (Revision 10: the viewer imports the pin's `pylabrobot.visualizer3D` from the PLR wheel).
  - [PY:test_contract_covers_imports.py] passes.
  - CI's `--probe --offline` gate stays green.
- **AC-34 (viewer draws in the deck panel)** [DOCK, scenario K1a: its own unit and subprocess,
  10 min budget (D16); 1440×900, Light theme; it boots, draws and runs `dock()` itself]:
  - `panel_is_split_right`: per the S1 branch, the panel is a main-area widget whose left edge
    is at or right of the notebook's right edge.
  - `viewer_resources`: `plrViewer.resources()` includes the fixture's `assay`, `source` and
    `tips_300`.
  - `hello_backend in {"WebGL2", "WebGPU"}`, read by evaluating
    `viewer.clients_seen[-1]["backend"]` in a cell (D11), not from printed output.
  - `canvas_nonblank`: > 1% of the iframe viewport's screenshot pixels differ from `#EEF1F4`.
  - `embed_hidden`: `.navbar`, `#toolbar-left`, `#stats-panel`, `#sidepanel` and `#toolbar`
    are all `display: none` inside the iframe.
  - `pageerrors == []`, in both the parent and the iframe.
- **AC-35 (Follow and presets)** [DOCK, K1a continued]:
  - `click_focuses`: a real click on `source` in the deck output changes
    `plrViewer.camera().at`, and the footer reads "source".
  - `follow_focuses`: with Follow on, activating the assay output's cell focuses `assay`.
  - `follow_off_holds`: with Follow off, activating another cell leaves the camera unchanged.
  - `follow_skips_null`: with Follow on, activating the `RunLedger` cell (whose only Praxis
    output is the ledger, `resource` null) leaves `plrViewer.camera()` unchanged (D12). The
    unit half (C5) covers a cell whose outputs are [ledger, plate] (focuses the plate)
    and a cell whose only output is a ledger (camera unchanged).
  - `preset_directions`: after Top, Front and Iso,
    `normalize(camera.from - camera.at) · normalize(VIEWS[name]) > 0.99`. The VIEWS vectors
    are copied from `renderer.js:117-121` into the harness.
  - `follow_keeps_preset`: after Top, then a Follow-driven focus on another resource,
    `normalize(camera.from - camera.at) · normalize(VIEWS.top) > 0.99`.
- **AC-36 (tiers)** [DOCK, scenario K2 across viewports: its own unit and subprocess, 15 min
  budget, atomic (D16)]:
  - **Execution order and page count** (Revision 7, C7-5). K2 uses **one page, one kernel and
    one `dock()`**; every viewport change is a `page.setViewportSize` on that page, and every
    later open is through `praxis:toggle-deck-panel`. Steps, in this order:
    1. A fresh page at 1152×800. Boot, draw, and measure the notebook content width; run
       `dock()`, whose first `announce` opens the drawer (T2). Keys `drawer_overlays`,
       `drawer_no_reflow` (the width before `dock()` against the width with the drawer open).
    2. `drawer_dismiss_reopen` (close button T17, toggle T4 → T6, Escape T17), then toggle to
       reopen (T4 → T6).
    3. `tier_up_rehomes`: resize to 1440×900 with the drawer open (T15); then resize back to
       1152×800 (T15), close with the close button (T17), resize to 1440×900 and assert it
       stays closed (T5); toggle to reopen at 1440×900 (T4 → T6).
    4. At 1440×900: the 1280–1599 open-time width key, then the splitter drags to 300 and
       700 px, with `iframe_reloads_during_resize` counting over the drags.
    5. `fit_after_tier_change`: resize 1440 → 1600 → 1440 wide.
    6. Resize to 1280×800; toggle close and reopen; the 1280–1599 keys (open-time width and
       both drags, counted as in step 4), then `viewer_height` and `motion_slot_height`.
    7. Close the file browser; resize to 1600×900; toggle close and reopen;
       `nb_content_width` and the ≥ 1600 `panel_width` key.
    8. `resize_within_wide`: resize 1600 → 1920 wide with the panel open, with
       `iframe_reloads_during_resize` counting over this step too.
    9. Resize to 1920×1080; toggle close and reopen; `nb_content_width` and the ≥ 1600
       `panel_width` key at open.
  - **Keyed by the D6 sizing case** recorded in AC-1. The result names the case and lists
    each width key below as `asserted` or `recorded-only`, per the D6 table: case
    honoured/reachable and case ignored/reachable assert every width key; case
    honoured/unreachable asserts the 1280–1599 keys and asserts the ≥ 1600 keys only if
    `css_limits_refit` (otherwise recorded-only); case S1-L records every width key.
  - If AC-1 records `restore_layout_keeps_iframe = false`, the open-time width keys and
    `fit_after_tier_change` keep their case status, while the drag-clamp keys and
    `resize_within_wide` take the status of the `unreachable` row for the same CSS column:
    CSS ignored → recorded-only; CSS honoured → CSS for the 1280–1599 drag, and inline px
    for `resize_within_wide`, asserted only if `css_limits_refit`. AC-39(d) is unaffected
    (it measures at open). *(Round 5, C5-1.)*
  - At 1600×900 and at 1920×1080, file browser closed: `nb_content_width ≤ 960` (always
    asserted; it is CSS on the notebook), and `panel_width` equals
    `max(420, main_area_width − 960 − nb_h_padding)` within ±8 px (D6) (≥ 1600 width key).
  - At 1440×900 and at 1280×800: `panel_width ∈ [420, 480]` after opening. After a real
    splitter drag to 300 px it is clamped to 420, and after a drag to 700 px, to 480. (These
    are the 1280–1599 width keys.)
  - `fit_after_tier_change`: resizing an open split panel from 1440 to 1600 wide and back
    re-satisfies each tier's width key (asserted or recorded per case).
  - `resize_within_wide`: resizing one page with an open split panel from 1600 to 1920 wide
    (no tier crossing) re-satisfies the ≥ 1600 width formula at 1920 (a ≥ 1600 width key,
    asserted or recorded per case; in case honoured/unreachable it checks that the inline
    widths were recomputed on `ResizeObserver`, D6).
  - `iframe_reloads_during_resize`: the number of deck iframe `load` events during the
    `resize_within_wide` step and the 1280–1599 splitter drag is 0, in every sizing case
    (D6 note on `restore_layout_keeps_iframe`). Asserted, not recorded-only: a build that
    clamps through a reloading `restoreLayout()` fails it. *(Round 4, C4-2.)* Counted in
    harness code only (AC-39(c)): a `MutationObserver` on the panel records every deck
    iframe inserted during the step, and a `load` listener on each counts loads, so a build
    that replaces the element is caught too. *(Round 5, C5-3.)*
  - At 1280×800: `viewer_height ≥ 300`, and `motion_slot_height ≤ 36`.
  - At 1152×800: `drawer_no_reflow`, meaning the notebook content width changes by 0 px when
    the drawer opens, and `drawer_overlays`, meaning the panel is `position: fixed`.
  - `drawer_dismiss_reopen`: at 1152×800 the first announce opens the drawer (D11 state
    table T2); its close button hides it, and no iframe remains in the DOM (T17);
    `praxis:toggle-deck-panel` reopens it (T4, then T6 on the answering `announce`); Escape
    hides it again (T17).
  - The drawer keys and the height keys are asserted in every sizing case.
  - `tier_up_rehomes`: resizing an open drawer from 1152 to 1440 wide re-homes it into the
    split (T15: `panel_is_split_right` holds, the iframe then in the panel keeps its `src`,
    `resources()` repopulates within 10 s); a closed drawer resized the same way stays closed
    (T5).
- **AC-37 (live state)** [DOCK, K1a continued]:
  - `state_updates`: after an aspirate cell,
    `plrViewer.stateOf(source.get_well("A1").name)` differs from its value before, within 5 s.
    The well name is read from the kernel, not hardcoded.
  - `stale_and_panel`: AC-23's notice text names the deck panel, and the panel is open.
- **AC-38 (reconnect and stop)** [DOCK, scenario K1b: its own unit and subprocess, 14 min
  budget, **atomic** (a timeout or preemption recomputes all of K1b; it is never resumed
  mid-way, D16); a fresh page at 1440×900, Light theme, which boots, draws and runs `dock()`
  itself]:
  - **Execution order** (Revision 6, C6-2; extended by Revision 7). The keys run in exactly
    the order listed below:
    `reconnect_after_reload`, `preset_survives_reload`, `drawer_reconnect`, `redock_live`,
    `stop_placeholder`, `redock_reloads`, `late_iframe`, `many_reloads`,
    `restart_placeholder`. `drawer_reconnect` and `redock_live` need a live viewer, so they
    precede `stop_placeholder`; `stop_placeholder` runs immediately before `redock_reloads`,
    so that re-dock's `announce` arrives in an open panel with no iframe after the user's own
    `stop()` (T6). `redock_live` re-docks a **live** viewer, so the old viewer's `close`
    exercises T12 → T6 (the C6-1 path) in the browser. `restart_placeholder` destroys the
    kernel, so it runs last.
  - **DOM reads** (Revision 6, C6-1). Every key reads the deck iframe by querying the panel's
    DOM at the moment of each read or write (for example `panel.querySelectorAll('iframe')`),
    never through an element reference held from an earlier step or key. Wherever a key
    names "the iframe", exactly one iframe must be in the panel DOM (D11, I1).
  - `reconnect_after_reload` (T16): after the iframe reloads (the harness sets
    `iframe.src = iframe.src`), `resources()` repopulates within 10 s.
  - `preset_survives_reload` (T16, D12; Revision 7, C7-7): the harness presses Front, then
    reloads the iframe (`iframe.src = iframe.src`); within 10 s `resources()` repopulates and
    `normalize(camera.from - camera.at) · normalize(VIEWS.front) > 0.99`, read from the
    iframe then in the panel (VIEWS as in AC-35).
  - `drawer_reconnect` (T15): after resizing to 1152×800 (the panel becomes a drawer and the
    iframe moves), `resources()` repopulates within 10 s; the harness then resizes back to
    1440×900 (the drawer is re-homed into the split, T15 again) and `resources()` repopulates
    within 10 s, so the later keys run in the split tier that `late_iframe`'s tab close needs.
  - `redock_live` (T12 → T6; Revision 7, C7-9): with the panel `open-connected` on a live
    viewer v1, re-running the `dock()` cell yields, observed through a harness
    `BroadcastChannel("praxis_viz3d")` listener and a `MutationObserver` on the panel subtree:
    a `close` for v1 before the `announce` for the new id v2 (read from the kernel); the v1
    iframe removed; exactly one iframe inserted after that `announce`, with its `src`'s
    `viewer` parameter equal to v2 at insertion; and `resources()` in it repopulating within
    10 s.
  - `stop_placeholder` (T12): after `await viewer.stop()`, within 5 s the body contains the
    exact string "No deck viewer is running.", does not contain "lost its connection", and
    the panel DOM holds no iframe.
  - `redock_reloads` (T6): re-running the `dock()` cell yields exactly one iframe in the
    panel DOM, whose `src`'s `viewer` parameter equals the new viewer's id (read from the
    kernel), and `resources()` in that iframe repopulates within 10 s.
  - `late_iframe` (T17, T3, T4, T6): the harness closes the deck panel's tab, re-runs
    `dock()` (only the first `announce` of a page auto-opens the panel, so it stays closed),
    then reopens it with `praxis:toggle-deck-panel` after `dock()` has returned; `resources()`
    populates within 10 s (`query` → `announce` → iframe with `src`). Ordering, observed
    through a harness `BroadcastChannel("praxis_viz3d")` listener and a `MutationObserver`
    on the panel subtree (`childList` and the `src` attribute): while closed, no iframe was
    in the DOM; a `query` was posted after the reopen; between the reopen and the answering
    `announce` the panel held no iframe; and the first iframe inserted into the panel
    appeared after that `announce`, with its `src` already carrying the viewer id.
  - `many_reloads` (T16): 6 sequential iframe reloads (`iframe.src = iframe.src`), each
    followed by `resources()` repopulating within 10 s. (With the cap at 4, this fails unless
    dead clients leave through `bye` or eviction, D11.)
  - `restart_placeholder` (T25; Revision 7, C7-6): with the panel `open-connected`, the
    harness runs `kernelmenu:restart` on the notebook that ran `dock()`; within 5 s the body
    contains the exact string "No deck viewer is running.", does not contain "lost its
    connection", and the panel DOM holds no iframe. (The harness `BroadcastChannel` listener
    also records that no `close` was posted: the restart, not a `close`, drove the change.)
- **AC-39 (sensitivity and hygiene)**:
  - **Pre-registered and unit-scoped** (Revision 7, C7-1, C7-8). Every negative below runs
    through the tracked sensitivity driver (D17, "AC-39 sensitivity runs are pre-registered
    too"), whose per-sprint sidecar, with one outcome per negative, is committed before the
    run. Each negative copies the built dist to its own `/tmp/claude-1000/nd-neg/<negative>/dist/`
    and runs **only** its own harness unit (D16), as a subprocess through
    `unit_runner.run_unit` with that unit's budget, and with its own
    `--out-dir /tmp/claude-1000/nd-neg/<negative>/out/` (Revision 8, C8-5; the harness refuses
    a non-default `--serve-dir` or any `--neg` without an explicit `--out-dir`). No negative
    writes into `outputs/repl_smoke/<check>/`. The run is verified by its bathos record
    (`outcome` evaluated), not by exit code alone; a harness timeout (exit 124) never passes.
  - (a) Remove `shell/display/index.js`, then run
    `--display-check --scenario D1 --serve-dir /tmp/claude-1000/nd-neg/a/dist --out-dir /tmp/claude-1000/nd-neg/a/out`:
    it exits nonzero and names `rail_state_after_run`.
  - (b) On its own copy, remove `assets/visualizer3d-augmentations/socket.js`, then run
    `--dock-check --scenario K1a --serve-dir /tmp/claude-1000/nd-neg/b/dist --out-dir /tmp/claude-1000/nd-neg/b/out`:
    it exits nonzero and names `viewer_resources`.
  - (c) `! grep -rnE '__praxis_test|data-praxis-test' web-repl/shell/display web-repl/overlay/assets/visualizer3d-augmentations --include='*.js' --exclude-dir=__tests__`
    finds nothing.
  - (d) Unit `N-d` (`--dock-check --scenario N-d --serve-dir /tmp/claude-1000/nd-neg/d/dist
    --out-dir /tmp/claude-1000/nd-neg/d/out`, 6 min): the AC-36 ≥ 1600 width predicate
    is sensitive: at 1600×900 the harness adds the
    viewer iframe in a stock `split-right` widget of its own (harness code, no `dock.js`
    sizing), measures it (a 50/50 split), and the predicate reports failure. Skipped, and
    recorded as such, wherever the ≥ 1600 key is recorded-only (D6 table: S1-L, and case
    honoured/unreachable without `css_limits_refit`).
  - (e) `late_iframe` is sensitive to the `query` path: with a harness context init script
    that wraps `BroadcastChannel.prototype.postMessage` in the parent page to drop messages
    of kind `query` (harness code, enabled by the harness-only flag `--neg drop-query`; no
    product switch), `--dock-check --scenario K1b --neg drop-query --serve-dir
    /tmp/claude-1000/nd-neg/e/dist --out-dir /tmp/claude-1000/nd-neg/e/out` exits nonzero and
    names `late_iframe`.
  - The observed exit codes, and the bathos run id whose outcome was evaluated, go in the
    sprint C PR description. (a) is run first in sprint A's PR (A7), and again in sprint B's
    (B10), each under its own sprint sidecar.
- **AC-40 (CI wiring)**:
  - `uv run python -m pytest web-repl/tests/test_repl_workflow_covers_tests.py -q` passes on
    each sprint's head.
  - `grep -c -- '--display-check' .github/workflows/repl.yml` ≥ 1 (sprint A).
  - `grep -c -- '--dock-check' .github/workflows/repl.yml` ≥ 1 (sprint C).
  - `grep -c 'bun test web-repl/shell/display' .github/workflows/repl.yml` ≥ 1 (sprint A).
  - The scenario-step layout of D16 is checked by AC-42's workflow test.
- **AC-41 (no regressions, sprints B and C)**:
  - AC-8's list is green on each sprint's head.
  - [PY:test_contract_covers_imports.py] passes on each sprint's head. Every `pylabrobot.*`
    submodule imported under `praxis/display/` or by `praxis/viz/viewer3d.py` has a
    `plr_contract.CONTRACT` entry with a justification comment, from a non-shim home (D8,
    D11; Revision 10).
  - R19: `test -d web-repl/overlay/assets/visualizer-augmentations`, then
    `grep -rnE 'requestDevice|requestPort' web-repl/overlay/assets/visualizer-augmentations/ web-repl/overlay/assets/visualizer3d-augmentations/ web-repl/shell/display/`
    exits **1 exactly**.
- **AC-42 (preemption-safe harness)** (Revision 7, C7-1; Revision 8, C8-1..C8-6; Revision 9,
  C9-1..C9-6) [PY:test_unit_runner.py], [PY:test_repl_smoke_resume.py] and
  [PY:test_repl_workflow_scenarios.py]. `test_unit_runner.py` is created in A1 (the runner
  cases); the other two are created in A7 for the display units and extended in B10 and C7
  for theirs:
  - **Runner** (`test_unit_runner.py`, real short-lived processes, no browser except the one
    CI-only case below; C8-1):
    - a child that starts a `setsid` grandchild (its own session and process group, as
      Playwright's detached Chromium) and then hangs: after `run_unit`'s timeout the
      grandchild is no longer running within the grace period (`/proc/<pid>` absent, or
      state `Z` in `/proc/<pid>/stat`);
    - the same with the intermediate parent exiting before the timeout, so the grandchild is
      re-parented out of the tree: the `PRAXIS_UNIT_TOKEN` sweep kills it;
    - a child arming `Watchdog(1)` with a `setsid` grandchild exits 124 within the budget
      plus grace, and the grandchild is gone;
    - **Hang after the stamp** (Revision 9, C9-1): a child arming `Watchdog(1)` commits a
      stamp with `exit` 3 while it holds an `atexit` handler that sleeps forever and a
      non-daemon thread that blocks forever. It exits with code 3 within the budget plus
      grace, because only `os._exit(stamp.exit)` follows the commit;
    - **Fixpoint** (C9-2): a sweep-found `setsid` orphan whose `SIGTERM` handler forks a
      child that ignores `SIGTERM` (the child inherits the token) during the grace window:
      after `kill_tree` returns, neither survives;
    - **Unreadable environ** (C9-2): with an injected environ reader that raises
      `PermissionError` for one pid, `ProcessLookupError` for another and returns empty for
      a third, `kill_tree` completes without raising and still kills the token-carrying
      grandchild. A process whose environ holds `PRAXIS_UNIT_TOKEN=<token>x` or
      `X_PRAXIS_UNIT_TOKEN=<token>` is not signalled;
    - **`SIGCONT` in `finally`** (C9-2): with an injected walk that raises
      `KeyboardInterrupt` after the first `SIGSTOP`, `kill_tree` re-raises, and afterwards
      no process of the test tree is in state `T` in `/proc/<pid>/stat`;
    - **`ensure_token`** (C9-4): a child started without `PRAXIS_UNIT_TOKEN` that calls
      `ensure_token()` finds the token in its own `/proc/self/environ` afterwards;
    - **Pid-reuse guard** (C9-3): with pidfd disabled and an injected `/proc` reader that
      reports a changed starttime for a collected pid, `kill_tree` sends that pid no
      signal, and sends no group signal to its pgid when the group has no other verified
      live member. Where `os.pidfd_open` exists, a spy shows every per-pid signal going
      through `signal.pidfd_send_signal`;
    - `kill_tree` never signals the caller or the caller's process group;
    - `--reap` (C9-2): with `CI` unset and no `--force` it exits 2 and a token-carrying
      orphan is still alive. With `CI=1`, and separately with `--force`, it kills the orphan
      and nothing without a token;
    - `driver_input()` changes when the injected Playwright version changes and when the
      injected `uv.lock` bytes change;
    - **Revision 10 contract cases** (the A1a implementation's behaviour; A1 adds any the
      merged suite lacks): in the fixpoint case the orphan's `SIGTERM` handler actually runs
      (it writes a marker file) because `kill_tree` sends `SIGCONT` right after `SIGTERM`,
      and its child forked in the grace window is re-frozen, collected by the second
      fixpoint and killed; `Watchdog(1)` with no `on_expire` fires, kills and exits 124 (the
      child carries the token, from `run_unit` or `ensure_token()`, or the case passes
      `token=`: construction raises `RuntimeError` without one, `unit_runner.py:579-583`;
      Revision 11, C11-9); a second `Watchdog.commit` raises; `disarm()` prevents the expiry; an `on_expire` that
      raises is logged and the child still exits 124 with its `setsid` grandchild gone;
      `dist_hash` equals the sha256 of the sorted `"<rel>\t<sha256>\n"` lines of a small
      tree, equals the sha256 of nothing for an empty directory, and raises for a missing
      one; `driver_input()` raises when `uv.lock` is missing; `--reap --token <t>` kills only
      the orphan carrying `t` and leaves another token's orphan alive; `UnitOutcome.killed` is
      false for a child that exits normally before its timeout and true after a timeout;
    - **Revision 11 contract cases** (round 11, C11-9; the merged module's behaviour, A1 adds
      any the merged suite lacks, to be verified by A1 against the suite): `Watchdog` with no
      token in the environment and no `token=` raises `RuntimeError`; with injected
      `exit_fn`/`kill_fn`, `write_result` after expiry returns `False` without calling its
      writer, and after a commit returns `False` likewise; `ensure_token()` in a child started
      with an interpreter flag (for example `python -X utf8`) re-execs with that flag kept
      (`sys.orig_argv`); `kill_tree`'s grace wait returns early once every collected member
      has exited (a child that exits on `SIGTERM` makes `kill_tree` return well before
      `grace_s`);

    - **Real Chromium** (Revision 9, C9-5; **CI only, never run locally**, per the local
      compute rule): marked `skipif` unless `CI` is set. In CI it fails, and never skips, if
      Chromium cannot be resolved. A child launches headless Chromium through Playwright and
      then hangs. Positive control first (C10-1): before the timeout, a live Chromium process
      (by `comm`/`exe`) carries the token and sits in a pgid different from the child's.
      After `run_unit`'s timeout, no process whose environ carries that unit's token survives
      the grace period. If the positive control fails (Chromium does not keep the token
      readable), that is a **finding** reported to the orchestrator, not a test bug to patch
      around (D16 "Open risk: Chromium and the token"; Revision 10). A1's local gate runs the
      file with this case skipped; the CI run is authoritative for it.
  - The driver's unit table equals D16's (ids, check, budget, listed keys); `--scenario <id>`
    runs exactly that unit.
  - `test_repl_smoke_resume.py` loads `scripts/repl_smoke.py` by path and tests its **pure
    functions** directly (Revision 11, C11-3, C11-10: the Revision 10 "never loads
    `repl_smoke.py`" check, and the AST/string check it needed, are dropped with
    `repl_smoke_units.py`). The CLI-behaviour cases below (the exit-2 `--out-dir` rule,
    `--aggregate-only`) call the functions behind the flags and assert their return code and
    effects, with an injected runner spy; only the `--scenario` watchdog cases run a child
    process. Import safety without the submodule is `test_repl_smoke_import.py`'s (A1).
  - With fake unit runners: every unit is started as its own `run_unit` call with its own
    budget + 60 s as timeout; no call carries a whole-run timeout.
  - A unit writes `result.<id>.json` before `result.<id>.stamp.json`; a runner killed between
    the two leaves no stamp, and the next resume recomputes that unit.
  - **`--scenario` watchdog** (C8-2; Revision 9, C9-6): `run_scenario` for a unit, run in a
    short-lived child process with a fake runner that writes its result and then hangs and a
    1 s budget, exits 124 at its budget, prints the `"status": "timeout"` line, writes the
    timeout marker and leaves **no** stamp. The result the fake wrote no longer exists,
    because the watchdog deleted it under the lock.
  - **Watchdog armed with the table budget** (C9-4): for every unit id in the table,
    `run_scenario(<id>)` with an injected `Watchdog` spy arms it exactly once, with that
    unit's D16 budget, before the first file deletion and before the fake browser launch.
  - **Hang in teardown** (C9-1): with a fake whose `browser.close()` hangs, and separately a
    fake whose `sync_playwright()` exit hangs, `run_scenario` exits 124 within budget +
    grace and leaves no stamp and no result.
  - **Driver timeout over a valid stamp** (C9-1): a fake `run_unit` that reports
    `timed_out` after the unit committed a valid stamp over a passing result: the unit is
    judged from its result (listed under `recomputed`, not `timed_out`), the aggregate
    passes, and a `logging.warning` naming the unit is emitted. The same fake with no stamp
    lists the unit under `timed_out`.
  - **Timed-out re-run clears the prior stamp** (C8-3): after a passing fake run of a unit
    leaves a stamp, a second `--scenario` run of it with a hanging fake runner times out;
    afterwards neither the old result nor the old stamp exists, and the next resume
    recomputes the unit (it is not under `reused`).
  - **Skip rule** (C8-3): resume skips a unit only when its stamp has `exit == 0`, its inputs
    and `result_sha256` match, and every listed key is present and holds; it records it under
    `reused` with its source path, input sha256s and `result_sha256`. Each of these
    recomputes it: a changed input (one case each for `dist`, `notebook`, `harness`,
    `runner` (C9-6), `chrome`, `args`, and `driver` with the Playwright version changed and with the
    `uv.lock` sha256 changed, C8-6), a tampered result file, a result with a failing key, a
    result with a listed key missing, a stamp with `exit != 0` over an otherwise passing
    result, and `--fresh`.
  - A timed-out unit is listed in `timed_out`, has no stamp and no result, and fails the
    aggregate.
  - The aggregate verdict over a fixed set of unit results is identical whether each unit was
    reused or recomputed (the pass rule is unchanged).
  - `--aggregate-only` starts no unit subprocess, counts a missing unit as failed, and
    **never deletes** (C8-4): with a stale stamp (one mismatched input) it exits nonzero,
    lists the unit under `stale` naming the mismatched input, and the result and stamp files
    are byte-identical afterwards. With the same `--base-path` as the scenario runs it
    reuses their stamps; with a different `--base-path` every unit is `stale` on `args`.
  - A non-default `--serve-dir`, or any `--neg`, without an explicit `--out-dir` exits 2
    before launching anything (C8-5).
  - The workflow test parses `repl.yml`: one step per unit of the current sprints, each
    running `--scenario <id>` with step-level `timeout-minutes` equal to the D16 budget + 2
    and `if: ${{ !cancelled() }}`; one `--aggregate-only` step per check whose hashed
    arguments (`--base-path`, and `--serve-dir`/`--out-dir` when present) equal those of
    every scenario step of that check (C8-4); an `if: always()` step running
    `scripts/unit_runner.py --reap` without `--force` (C8-1, C9-2); an `actions/upload-artifact` step with
    `if: always()` covering the out dirs; no `actions/download-artifact` step that fetches
    that artifact (CI never reuses across workflow runs); a job-level `timeout-minutes`
    of at least 45 plus the sum of the scenario step timeouts; and both `paths:` filters
    (`push` and `pull_request`) list `scripts/repl_smoke.py`, `scripts/unit_runner.py`,
    `scripts/spikes/**` and `scripts/negatives/**` (Revision 11, C11-11).

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
  CSS limits, measures the widget after a splitter drag, tries DockPanel layout sizing
  (`saveLayout` → edit `sizes` → `restoreLayout`), tests `css_limits_refit` (set inline px
  `min-width`/`max-width` on the widget node, call `parent.fit()`, measure), records the D6
  sizing case, records `restore_layout_keeps_iframe` (whether `restoreLayout()` keeps an
  iframe in the widget loaded, i.e. a clamp causes no reload), enumerates cell-state hooks for the five
  states, and records the notebook's `windowingMode` and the signal that fires when a
  scrolled-away cell's DOM is re-attached.
- **First, the shared unit runner** (Revision 8, C8-1; Revision 9, C9-1..C9-5), tests
  first: write `web-repl/tests/test_unit_runner.py` (the AC-42 runner cases, including the
  Revision 9 cases: hang after the stamp, fixpoint, unreadable environ, `SIGCONT` in
  `finally`, `ensure_token`, pid-reuse guard, `--reap` refusal, and the CI-only
  real-Chromium case) and see it fail, then `scripts/unit_runner.py` (D16 "Shared unit
  runner": `kill_tree` with the fixpoint, pidfd or starttime guard and `finally` `SIGCONT`;
  `run_unit`; `ensure_token`; `Watchdog` with `commit` and result deletion; the bounded
  teardown order; `write_atomic`, `dist_hash`, `driver_input`; `--reap` with its `CI` /
  `--force` guard), and wire the test into `repl.yml` in the REPL job that has Playwright's
  Chromium. The real-Chromium case is never run locally (local compute rule); A1's local
  gate runs the file with it skipped, and the PR's CI run is authoritative for it.
  Commit these to the sprint branch before the probe work, so A2 and A3 can start on them.
  A1 is the first sprint A task to need a unit runner (A1–A3 start before A7), so it owns
  the module; every later unit kind uses it and none reimplements process killing.
  *(Revision 10.)* This part is already merged on the sprint branch as A1a
  (`scripts/unit_runner.py`, 39 passing cases). D16 now states what that code does (the
  `SIGCONT` after `SIGTERM` and the re-freeze before `SIGKILL`, the optional `on_expire`,
  `disarm`, `commit` raising on a second call, `dist_hash`'s line format, `driver_input`'s
  `uv.lock` read, `killed`, `emit_line`/`read_proc_stat`/`reap()`, `--reap --token`,
  `grace_s`, the keyword-only seams). The remaining A1 work adds any AC-42 Revision 10 or
  Revision 11 contract case the merged suite lacks (Revision 11 adds the `Watchdog` token
  requirement, `write_result`, `ensure_token`'s `sys.orig_argv` and the early-ending grace
  wait, C11-9) and the C10-1 positive control, then proceeds to the probe.
- The probe is a unit driver (D17 "Units, resume and chunking"): the S1 units, each started
  as `--unit <name>` through `unit_runner.run_unit` in its own subprocess and browser
  context, 4 min each and self-bounded by a `unit_runner.Watchdog` armed as its first act,
  clearing its own files next, closing the browser and Playwright before the stamp commit
  (only `os._exit(stamp.exit)` after it, C9-1), `units/<name>.json` plus a stamp (inputs including `driver`), a raised probe
  recorded as an `error` finding, `--resume`; the sidecar pre-registers the units, timeouts,
  hashed inputs, artifact fields, resume rule and completeness definition (D17, C8-7), and
  evaluates `[outcomes]` over the full unit set.
- **Lazy `NOTEBOOK_EXPECTED`, before the probe runs** (Revision 11; orchestrator ruling (a)
  on round 11 C11-3; D16 "Import-time submodule dependency, removed in A1"). Tests first:
  write `web-repl/tests/test_repl_smoke_import.py` (§4 row) and see it fail, then turn
  `NOTEBOOK_EXPECTED` (`scripts/repl_smoke.py:1450-1454` on the sprint A branch) into
  `notebook_expected()` and call it at `:1656`, `:1666`, `:1680` and `:4451` (about 6
  lines). Wire the test into `repl.yml`. `--notebook-check` behaviour is unchanged (the same
  three strings, read at run time); the PR's CI "Execute welcome.ipynb" step confirms it
  (AC-8). S1's driver
  needs this: it loads `repl_smoke.py` for `ServedDir`, `chromium_launch_args` and
  `resolve_chrome_path` in its driver (`build_env`,
  `scripts/spikes/260929_s1_lumino_widget.py:265-283`, called from `run_driver` `:1777`),
  not only in `--unit`, so the Revision 10 rule "the driver never loads it" did not hold for
  the committed probe; after the change, loading it anywhere is safe.
- **Amend the committed S1 probe and sidecar before the first run** (Revision 11, C11-3). The
  probe committed at A1b-1 (`60e892fe`, branch `feat/notebook-display-sprint-a`) hashes no
  `repl_smoke.py` input (`InputEnv` and `compute_inputs`, `:240-297`), and its sidecar's
  `[design].hashed_inputs` (`.bth.toml:109`) omits it. In **one commit before the first
  `bth run`**: add a `harness` field (the sha256 of `scripts/repl_smoke.py`) to `InputEnv`,
  `build_env` and `compute_inputs`; add
  `"harness (scripts/repl_smoke.py, loaded by path for ServedDir, chromium_launch_args and resolve_chrome_path)"`
  to the sidecar's `hashed_inputs`; add the field to `test_s1_spike_driver.py`'s fake
  environments; and state in a comment beside `hashed_inputs` that the list was amended
  before any run, and why. No run has happened (orchestrator, 260929), so the amendment is
  still a pre-registration; the S1 research note records the amendment, its commit and its
  reason (round 11 C11-3: the driver loads `repl_smoke.py`, so a harness change must
  recompute every unit). The `[outcomes]` criteria are not touched.
- **Paths filter.** In both `repl.yml` `paths:` lists (`:17-37` on the sprint A branch),
  replace `scripts/spikes/260929_s1_lumino_widget.py` with `scripts/spikes/**` (C11-11), so
  A2's, A3's and C1's probes trigger the workflow too.
- The `bth run` itself happens in a checkout whose submodule is initialised at the pin
  (CI-equivalent: the dist's PLR wheel must be the pin's; D16).
- Run it with `bth run`, verify by record, and file the research note, which records each
  unit as recomputed or reused and lists any `error` findings.
- Depends on: none (a built dist).
- Closes: AC-1, and AC-42's runner cases.
- Gate: [PY:test_unit_runner.py] (locally with the real-Chromium case skipped; that case is
  closed by the PR's CI run), [PY:test_repl_smoke_import.py], [PY:test_s1_spike_driver.py],
  [PY:test_repl_workflow_covers_tests.py]; `git log` shows the S1 amendment commit before the
  run; AC-1 record query.
- Size: ~500 LOC (raised in Revision 8 for `unit_runner.py` and its test, in Revision 9
  for the fixpoint, pid-reuse guard, `ensure_token`, bounded teardown, seven new runner cases
  and the tightened `--reap` case, and in Revision 11 by ~50 for the lazy
  `notebook_expected()`, its regression test, the S1 `harness` input amendment and the
  Revision 11 runner cases).

**A2: Spike S2 (sanitizer and untrusted mimetype).** Same discipline as A1, over
`260929_s2_sanitizer.py`. The crafted outputs cover every element and attribute in D1's S2
row. Include a bundle with both `text/html` and `text/plain`, and the D17 negative control.
Probe both reopen paths from D1's S2 row: the crafted notebook, and a notebook executed,
saved and reopened in the same browser (record its trust state; S2-T if trusted). Each trust
path and the negative control is its own D17 unit (`live`, `crafted`,
`executed_saved_reopened`, `neg_script_onclick`), in its own subprocess and browser context,
5 min each, started and bounded through `scripts/unit_runner.py` (A1), with stamps (inputs
including `driver` and `harness`), the D17 completeness rule and `--resume`. As in A1,
`repl_smoke.py` is loaded by path where the probe needs it (import-safe after A1's lazy
`notebook_expected()`) and hashed as the `harness` input, and the run happens with the
submodule initialised at the pin (Revision 11, C11-3).
- Depends on: A1's `scripts/unit_runner.py` and A1's lazy `notebook_expected()` change only
  (Revision 8, C8-1; Revision 11; not A1's spike run).
- Closes: AC-2.
- Gate: AC-2 record query.
- Size: ~220 LOC.

**A3: Spike S3 (IPython hooks in the Pyodide kernel).** Same discipline, over
`260929_s3_ipython_hooks.py`. Test (a), (b), (b′), (c) and (d), each in a plain cell and a
top-level-`await` cell, reading results from the notebook model (for (b′), the output's
`metadata["text/html"]["praxis"]`). S3 declares itself one bounded D17 unit,
`ipython_hooks`, with a 10 min timeout (a `unit_runner.Watchdog` in the unit, `run_unit` at
10 min + 60 s in the driver), a stamp (inputs including `driver`), the D17 completeness rule
(a raised sub-probe is an `error` finding in the one artifact) and `--resume`; the sidecar
says so. As in A1, `repl_smoke.py` is loaded by path where the probe needs it and hashed as
the `harness` input, and the run happens with the submodule initialised at the pin
(Revision 11, C11-3).
- Depends on: A1's `scripts/unit_runner.py` and A1's lazy `notebook_expected()` change only
  (Revision 8, C8-1; Revision 11).
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
- Depends on: A5 (`assert_dist_complete` requires `shell/display/{index,chrome}.js`, and
  AC-6 builds and checks for them).
- Closes: AC-6.
- Gate: AC-6 commands, plus [PY:test_repl_workflow_covers_tests.py].
- Size: ~80 LOC.

**A7: `--display-check` harness and chrome scenario D1, plus CI wiring.** Add `--display-check`
and `run_display_check` to `repl_smoke.py`:
- seed the drive with `display_check.ipynb` (initially only the D1 cells)
- execute cells one at a time through the command registry
- read state from the model and computed styles
- add scenario D1 (Light) and scenario D1-dark (default Dark), per AC-7
- add the context init script that pre-sets the persistence ack key (D16)
- build the D16 "Preemption-safe harness design" machinery, tests first
  (`test_repl_smoke_resume.py`, which loads `repl_smoke.py` by path and tests its pure
  functions directly; Revision 11: no separate `repl_smoke_units.py`, since A1 made
  `repl_smoke.py` import-safe, C11-3, C11-10): the unit table with listed keys, `--scenario <id>` (one
  unit per process: `unit_runner.ensure_token`, then a `unit_runner.Watchdog` armed at its
  table budget as the first act (exit 124, timeout marker, result deleted, no stamp), then
  clearing its own files; browser and Playwright closed before the stamp commit, only
  `os._exit(stamp.exit)` after it; C9-1, C9-4, C9-6), the driver (one `unit_runner.run_unit`
  subprocess per unit with budget + 60 s as timeout, deferring to a valid stamp over its own
  timeout and logging it; no process killing outside `unit_runner.py`), the per-unit result
  and stamp writers (`unit_runner.write_atomic`, result through `Watchdog.write_result`,
  stamp through `Watchdog.commit`), input
  hashing including `driver` and `runner`, the skip rule (`exit == 0`, every listed key present and
  holding), the aggregate with `reused`/`recomputed`/`timed_out`/`missing`/`stale`, and
  `--out-dir` (required with a non-default `--serve-dir` or any `--neg`), `--fresh`,
  `--aggregate-only` (never deletes)

Then add the CI steps after "Execute welcome.ipynb", per D16: one step per unit
(`uv run python scripts/repl_smoke.py --display-check --scenario D1 --base-path /praxis/`,
and `D1-dark`) with step-level `timeout-minutes` 8 and 7 and `if: ${{ !cancelled() }}`, the
`--display-check --aggregate-only --base-path /praxis/` step, the `if: always()`
`uv run python scripts/unit_runner.py --reap` step (no `--force`: Actions sets `CI=true`),
the `if: always()` upload, and the
job-level backstop raised to 60; add `scripts/negatives/**` to both `paths:` filters (C11-11);
write `test_repl_workflow_scenarios.py` first and wire both
new test files. Write the sensitivity driver (units through `unit_runner.run_unit`, each
negative on `/tmp/claude-1000/nd-neg/<negative>/dist/` with its own `--out-dir .../out/`,
`driver` hashed; D17), `260929_nd_sensitivity_sprint_a.py` and its sidecar, commit them, then
run AC-39(a) through `bth run` (D17).
- Depends on: A1 (`scripts/unit_runner.py`), A4, A5, A6.
- Closes: AC-7, AC-8, AC-40 for its sprint A keys, and AC-42 for the display units D1 and
  D1-dark.
- Gate: interim, a local unsandboxed run of each unit (`--scenario D1`, `--scenario
  D1-dark`) on a fresh build per D16, in a checkout with the submodule initialised at the pin,
  then the driver resuming over their stamps (both listed under `reused`); [PY:test_repl_smoke_resume.py], [PY:test_repl_workflow_scenarios.py],
  [PY:test_repl_workflow_covers_tests.py]. Final: a green REPL workflow on the PR head.
- Size: ~410 LOC (raised in Revision 7 for the driver, stamps and the two tests; lowered by
  ~10 in Revision 11, since there is no second module to load and no import-isolation check).

Sprint A order: A1 starts with `scripts/unit_runner.py` and its test, then the lazy
`notebook_expected()` change and its test; once those are committed, A2 and A3 run in
parallel with the rest of A1; then A4 and A5 (after A1); then A6 (after A5); then A7.
*(Revision 8, C8-1: A2 and A3 previously had no dependency. Revision 11: A2 and A3 also wait
for the lazy change, which their drivers need to load `repl_smoke.py` in any checkout.)*

### Sprint B: praxis.display (merges alone; needs AC-2 and AC-3 records)

**Import contract (every task B2–B8).** A task that adds an import of a `pylabrobot.*`
submodule not already in `web-repl/tests/plr_contract.py`'s `CONTRACT` adds the entry, with a
justification comment, in the same task, and its gate includes
[PY:test_contract_covers_imports.py] (D11, AC-41). *(Revision 10.)* Every import uses the
pin's non-shim home: `pylabrobot.legacy.liquid_handling` for `LiquidHandler`,
`pylabrobot.legacy.tip_tracker` for `TipTracker`, `pylabrobot.resources.volume_tracker` for
`VolumeTracker`, `pylabrobot.resources.errors` for the four classes. A shim home (for example
`pylabrobot.resources.tip_tracker`) fails the contract's "names no shim" test and its
warnings-as-errors probe (D8; the PLR 1.0 recon, MAJOR-8).

**B1: Primitives, floor and budget.** Create `svg.py` (including `esc_text` / `esc_attr`),
`floor.py` (both `s_min` forms, D5) and `budget.py` (including `cap_tail`), with
`test_display_floor.py` (the pure math cases) and `test_display_budget.py` (the ladder with a
fake renderer, level 1 dropping the grid, and `cap_tail`), tests first. Add both `repl.yml`
lines.
- Depends on: none.
- Closes: the pure halves of AC-12 and AC-13.
- Gate: the two [PY] files.
- Size: ~260 LOC.

**B2: Labware reprs.** First port the design fixture to the pin (section 4
`make_fixture.py`/`fixture.js` row; Revision 10): non-deprecated constructors, `track=`
instead of `rails=`, `num_tracks`, non-shim imports, the `_as_in_kernel` path fix, and a
regenerated `fixture.js`; confirm that
`grep -rnE '(^|[^_])_repr_[a-z]+_' external/pylabrobot/pylabrobot --include='*.py'` exits 1
(no IPython display hook at the pin; D2), or stop and report. (Revision 11, C11-1: the
Revision 10 BRE `'_repr_html_\|_repr_[a-z]*_'` matched every `__repr__`, 15 hits at the pin,
so this gate could never pass.) Then create `labware.py`, and
`test_display_labware.py` first:
- sentences
- well-range compression, with cases for a full column, a block, and scattered wells
- the grid descriptor
- the D2 bundle and stamp, with `rev`, `session` and `exec` injected
- figures for `Plate`, `TipRack` and `Well`; sentence-only bundles for other containers (D2)
- escaping of every interpolated string through `svg.py`, with the hostile-name case
- the S2 branch's attribute set: emit every attribute; the branch only changes what survives
  on reopen
- tip racks resolved through the `TipRack` class (an `EmbeddedTipRack` is one), never by the
  type-name string

Add the test's `repl.yml` line.
- Depends on: B1.
- Closes: AC-9, AC-10.
- Gate: [PY:test_display_labware.py], [PY:test_contract_covers_imports.py], the `_repr_`
  ERE grep above (exit 1), and `fixture.js` regenerated from the ported `make_fixture.py` and
  committed with it.
- Size: ~370 LOC (raised in Revision 10 for the fixture port).

**B3: Deck repr.** Create `deck.py`, and `test_display_deck.py` first, including the 384-,
1536-, narrower-than-880-mm and oversize cases for AC-12 and AC-13. Add its `repl.yml` line.
- Depends on: B2.
- Closes: AC-11, and AC-12 and AC-13 in full except AC-13's error-panel case (B6).
- Gate: [PY:test_display_deck.py], [PY:test_display_floor.py], [PY:test_display_budget.py],
  [PY:test_contract_covers_imports.py].
- Size: ~300 LOC.

**B4: Glossary and RunLedger.** Create `glossary.py` and `ledger.py`, with
`test_display_ledger.py` and `test_display_glossary.py` first: in-flight nesting and
top-level counts, `_ERROR_STEPS` / `step_for`, the ledger shown on the error path (D9), and
the ledger stamp (`resource` null, `rev` null, D2). Add their `repl.yml` lines.
- Depends on: B2.
- Closes: AC-14, AC-28.
- Gate: the two [PY] files, [PY:test_contract_covers_imports.py].
- Size: ~320 LOC.

**B5: Error context.** Create `context.py`, and `test_display_context.py` first: cases
E1–E16, E4-off, E6-off, E-96 and the four negatives (including the two bare-call
`RuntimeError`s), using real PLR at the pin. Implement D8
steps 1–5: the `glossary.ACTIONS` frame filter (defence against comprehension frames, no
case), the `*96` short-circuit, owner rules (a)–(e) (no `head96` in rule (b); rule (d) with
the pin's `thing` forms), the committed, summed offending set (per channel for a tip owner),
and the pending-residue rule (owner outside the committed offending set → `None`). E13 and
E15 use the Revision 10 synthetic-residue setups; E15's raise is a confirmatory assert of the
class (read from source at the pin, AC-15; Revision 11, C11-6). E14 uses AC-15's step-by-step
recipe, with its precondition asserts (Revision 11, C11-5). Committed tip state is
`TipTracker.get_tip()` succeeding (`lh.head[c].get_tip()`, `tip_spot_tracker(spot).get_tip()`),
never `has_tip` and never `TipSpot.get_tip()`; owner rule (a) reads tip spots through
`tip_spot_tracker`, never `spot.tracker` (C11-14); a `Tip` matched by rule (d) gives no owner
(C11-15). Re-anchor the head-side
NoTip sites at the pin in the test's comments (D8 "Tracking"). Add its `repl.yml` line.
- Depends on: B4 (`glossary.ACTIONS`).
- Closes: AC-15.
- Gate: [PY:test_display_context.py], [PY:test_contract_covers_imports.py].
- Size: ~300 LOC.

**B6: Error panel and handler.** Create `errors.py`, and `test_display_errors.py` first.
Implement the handler per D8, using S3-A or the S3-C fallback as recorded in AC-3, with the
escaped, capped traceback (D2, D4) and the step line from `ledger.step_for` (D9). Include the
tip-owner TLL row (E12), the "NoTip, channel" row naming "Discard tips" (E16), the generic
panel for every `None` result (including E13 and E15, in their Revision 10 setups), the
committed-volume drawing checked on assay H12, a residue well outside the failing op, with its
render-time precondition assert (AC-16; Revision 11, C11-2), the "Nothing was
aspirated/dispensed" ordering as a confirmatory assert (D8 "Panel drawing": a backend spy
records no call on E1; the ordering is read from source, LH:1269-1274 and :1470-1475;
Revision 11, C11-6), and the error stamp by owner (D2). Add its `repl.yml` line.
- Depends on: B2, B4 (glossary, ledger), B5.
- Closes: AC-16, and AC-13's error-panel case.
- Gate: [PY:test_display_errors.py], [PY:test_contract_covers_imports.py].
- Size: ~280 LOC.

**B7: Staleness, kernel side.** Create `stale.py`, and `test_display_stale.py` first (D7:
revs, the announcer, no subscription or rev for `rev: null` stamps, the pending-only bump;
no session message; Revision 10: idempotent subscription through `_subscribed`, the
drawn-state digest filter with its rollback and settle-before-render cases; Revision 11,
C11-7: tip spots enter the digest as `spot.tip is not None`, the S3-D debounced announcer
settles before it builds its message, and AC-18's `set_volume` case uses a value other than
A1's 150 µL). Use an injected poster, with `import js` only in `make_repl_poster()`.
Add its `repl.yml` line. If AC-3 recorded (b) and (b′) both failing, do not start; escalate
(D1, S3-B).
- Depends on: B2.
- Closes: AC-18.
- Gate: [PY:test_display_stale.py], plus the D7 R21 check, [PY:test_contract_covers_imports.py].
- Size: ~260 LOC (raised in Revision 10 for the digest filter).

**B8: Install and bootstrap stage.** Create `install.py` and `praxis/display/__init__.py`, and
`test_display_install.py` first. It covers the fake shell and the S3-B (the
`(html, {"praxis": stamp})` carrier), S3-C and S3-D fallbacks, and the generic panel for
E13 and E15 (their Revision 10 setups). Add the D13 stage to `praxis_bootstrap.py`, and extend
`test_praxis_bootstrap_loader.py` for its order and its non-fatal failure. Add the `repl.yml`
line. Extend `assert_dist_complete` with `assets/python/praxis/display/__init__.py`.
- Depends on: B2, B3, B4, B6, B7.
- Closes: AC-17, AC-20, and the colour half of AC-27. The colour-vision test file is created
  here, test first, with its line added.
- Gate: [PY:test_display_install.py], [PY:test_praxis_bootstrap_loader.py],
  [PY:test_display_colorblind.py], [PY:test_contract_covers_imports.py].
- Size: ~220 LOC.

**B9: Shell stale and interaction.** Create `shell/display/stale.js` and `interact.js`, with
their bun tests first: `stampOf` (D2, exported), `panelSession` per notebook panel from
`chrome.js`'s observed executions and the panel's `sessionContext`, no session marks before
it is known, the two-panel case, no "Changed since" on `rev: null` stamps (D7), marks
re-applied on `outputs.changed`, the S1 re-attach signal and `activeCellChanged`, and
matching by `dataset.praxisRes` (D14). Mount them from `index.js`. Extend staging
(`build_repl.py` required list, `test_display_staging.py`). If AC-3 recorded (b) and (b′)
both failing, do not start; escalate (D1, S3-B).
- Depends on: A5 (observed executions), B7 (the `praxis:resource-changed` schema).
- Closes: AC-19.
- Gate: [BUN], [PY:test_display_staging.py].
- Size: ~360 LOC.

**B10: `--display-check` scenarios D2–D4.** Extend the fixture notebook and
`run_display_check` for AC-21 to AC-26, including AC-23's `mark_survives_scroll`,
`earlier_session_marked` (kernel restart, boot cell, then a re-run drawing cell) with its
negative control `rerun_not_marked` (the re-run output itself is not marked), and
`persistence_gate_never_open`; the harness reads stamps with the `stampOf` expression (D2). D3 asserts the
S2 branch that AC-2 recorded for the executed-saved-reopened path. D2, D3 and D4 are D16
units with budgets 12, 8 and 6 min; add them to the unit table, the two AC-42 tests and
`repl.yml` (one step each, step timeouts 14, 10 and 8; job backstop 92), each unit
self-bounded by the `--scenario` watchdog and started by the driver through
`unit_runner.run_unit` (D16); the existing aggregate step keeps `--base-path /praxis/`.
Commit `260929_nd_sensitivity_sprint_b.py` and its sidecar, then run AC-39(a) through
`bth run`, with its own `--out-dir` (D17, C8-5).
- Depends on: B8, B9.
- Closes: AC-21 to AC-26 (CI), AC-41 for sprint B, and AC-42 for D2–D4.
- Gate: interim, a local unsandboxed run of each new unit alone (D16). Final: a green REPL
  workflow on the PR head.
- Size: ~340 LOC.

Sprint B order: B1; B2; then B3, B4 and B7 in parallel; B5 (after B4); B6; B8; B9, which
can start after B7; then B10.

### Sprint C: Visualizer3D deck panel (merges alone; needs the AC-1 branch to be S1-A or S1-B)

**C1: Spike S4 (Viewer3D in Pyodide).** Discipline as in A1 (including loading
`repl_smoke.py` by path and hashing it as the `harness` input; Revision 11). The probe imports the pin's `pylabrobot.visualizer3D` from the dist's PLR
wheel and stages nothing (Revision 10; it previously staged a throwaway copy of five vendored
files). It does not wait for C2. It records D1's S4 questions, the scene bytes and whether
any model carries `mesh`, the stock `PACKAGE_ROOT` as resolved in the kernel, and the first
`_models_on_disk(PACKAGE_ROOT)` time after rebinding the root to an empty temporary
directory, as `viewer3d.py` will (D11). S4 declares itself one bounded D17 unit,
`viewer3d_pyodide`, with a 10 min timeout (a `unit_runner.Watchdog` in the unit, `run_unit`
at 10 min + 60 s in the driver, both from `scripts/unit_runner.py`), a stamp (inputs
including `driver`), the D17 completeness rule and `--resume`; the sidecar says so.
- Depends on: A1's `scripts/unit_runner.py` (merged with sprint A, so already on `main`).
- Closes: AC-29.
- Gate: AC-29 record query.
- Size: ~160 LOC (lowered in Revision 10: nothing is staged).

**C2: Vendoring script and the static tree** (Revision 10: `static/` only). First write
`test_vendor_visualizer3d.py` over a tiny synthetic source tree (anchors, placeholders, tag
positions, sha identity, a mismatching file and a mismatching recorded commit that must each
fail with context). Then write `vendor_visualizer3d.py`, run it against the submodule
`external/pylabrobot` at the pin (`786ac2c4e`, recorded in the manifest; OQ-7), and commit the
generated `web-repl/overlay/assets/visualizer3d/` tree. No Python is vendored, no ADR addendum
is written and no contract entry is added here (D11; the contract entry for `viewer3d.py`'s
own import is C3's). Add the `repl.yml` line. The CI `--check` step lands in C7.
- Depends on: none.
- Closes: AC-30 (local).
- Gate: [PY:test_vendor_visualizer3d.py], and `vendor_visualizer3d.py --check` exits 0
  locally with the submodule initialised at the pin.
- Size: ~200 LOC, plus the generated tree (lowered in Revision 10 from ~300).

**C3: DockedViewer3D.** Write `test_viewer3d_docked.py` first, then `viewer3d.py`:
- `import pylabrobot.visualizer3D` (the pin's package) and subclass its `server.Viewer3D`;
  add `("pylabrobot.visualizer3D.server", "Viewer3D")` to `plr_contract.CONTRACT` with a
  justification comment (D11; Revision 10)
- the three overrides, `VirtualConnection`, the injected channel, and `dock()`
- the one-time `pylabrobot.visualizer3D.server.PACKAGE_ROOT` rebind to `tempfile.mkdtemp()`
  in the guarded, idempotent module helper `_ensure_package_root()`, called first in
  `DockedViewer3D.__init__` (not at import, not an override; D11 "Trigger"; Revision 11,
  C11-13), with AC-31's load-bearing check (temporary root seeded after import, before the
  first construction) and its positive control
- AC-31's GATE X part 2 state snapshot of `vars(Viewer3D)` and the `server` module dict, with
  its negative control (Revision 11, C11-4)
- `start`: no `_models_on_disk` pre-warm, the 4-client cap with oldest-client eviction
  (`evict` plus a sentinel; an own insertion-ordered client map, since `_clients` is a set,
  and synchronous removal from `_clients` before the new `_handler` runs), `bye` ending a connection, `query` → `announce`, dropping
  non-JSON and unknown kinds (D11 threat model)
- `stop`: end every connection with a sentinel and await its `_handler` task, then `close`,
  then unsubscribe from `praxis_viz3d` (so a stopped viewer answers no `query` and accepts
  no `open`, C7-3); idempotent (a second call posts nothing)
- `dock()`: the module-level current viewer stopped first, and
  `wait_for_browser(timeout=15)` with the timeout stated
- any S4-B stubs, installed before the `pylabrobot.visualizer3D` import, each named in a
  module constant and asserted by the test

Add the test's `repl.yml` line. If the tests need `websockets.asyncio.server` in the root env
and it is missing, stop and report; do not vendor it.
- Depends on: C1 (the branch). C2 is no longer a dependency (Revision 10: `viewer3d.py` needs
  only the pin's package, not the static tree).
- Closes: AC-31, except its extended R21 check, which needs C4's and C5's paths and is closed
  by C7.
- Gate: [PY:test_viewer3d_docked.py], [PY:test_contract_covers_imports.py], plus the AC-18
  R21 check.
- Size: ~290 LOC.

**C4: Socket shim and embed mode.** Write `viz3d_socket.test.js` first, then `socket.js`
(viewer id from `location.search`; nothing posted without it; `bye` on `close()`, `pagehide`
and the accept timeout; a late `accept` ignored; `onclose` on its own `evict`), `embed.js`
and `embed.css` (D11, D12).
- Depends on: C2 (tag positions).
- Closes: AC-32.
- Gate: [BUN].
- Size: ~250 LOC.

**C5: Deck panel widget.** Create `shell/display/dock.js` and its bun tests (a fake app shell
and signals), tests first:
- the widget per the S1 branch, and sizing per the D6 sizing-case table recorded in AC-1
  (CSS limits, DockPanel `saveLayout`/`restoreLayout`, inline px `min-width`/`max-width` +
  `parent.fit()`, or S1-L), including the ≥ 1600 width formula and `parent.fit()` after
  every tier change inside the split (D6), and, in case honoured/unreachable, the inline
  widths recomputed on every `ResizeObserver` callback within ≥ 1600 px (window resize and
  file-browser toggle)
- the header, footer, motion slot, tiers, and the drawer: auto-open on first announce,
  close button, Escape, tier crossing both ways (D6)
- Follow (first output with a non-null `resource`, read through `stampOf` from `stale.js`),
  click-to-focus wiring from `interact.js`, and the held preset passed to every
  `focus(name, preset)` (D12)
- when `restore_layout_keeps_iframe` is `false`, layout sizing only at open and on tier
  changes (unit test: no `ResizeObserver` or drag clamp calls `restoreLayout()`)
- the deck-panel lifecycle as the D11 deck-panel state table, listening on `praxis_viz3d`
  and acting only on `announce` and the kernel `close` (`{viewer, reason}`), plus
  `praxis:toggle-deck-panel`, the drawer's close button and Escape, tier crossings and
  forwarded `plr:gone`, and the kernel-restart event from the viewer's kernel's
  `sessionContext` (the `viewerPanel` map, D11). Tests: **one bun test per table row, T1–T27** (a row that lists
  several events gets one case per event), each asserting the next state, the actions (iframe
  created / `src` written / iframe removed / `query` posted / text shown) and invariants
  I1–I6 read from the fake DOM (never from an element the test held). Sequence tests on top
  of the rows:
  - **C6-1 re-dock:** `open-connected` with `v1`, then kernel `close(v1)`, then
    `announce(v2)` → exactly one iframe in the panel, a newly created element (not the removed
    one), with `viewer=v2`; a later `plr:gone` from it is honoured again (→ `open-lost`).
  - **C5-2:** kernel `close(current)`, then `plr:gone` → the no-viewer text stays.
  - **Reopen:** `closed` → reopen → no iframe and one `query` posted; the answering
    `announce` then creates the only iframe, already carrying the `src`.
  - **C7-6 kernel restart:** `announce(v1)` while fake panel P has a cell executing (so
    `viewerPanel[v1] = P`), then P's `sessionContext` reports `restarting` → `open-waiting`,
    no iframe, the no-viewer text, no `query` posted; the same with `dead` and with
    `kernelChanged` to no kernel. A restart of another panel Q leaves `open-connected`
    unchanged. From `open-lost`, P's restart → `open-waiting` with the no-viewer text (T26).
    With no `viewerPanel` entry and two panels with kernels, a restart changes nothing (the
    stated gap); with exactly one panel with a kernel, it fires.
  - **C7-9 same id:** in `open-connected` on v1, `announce(v1)` writes no `src` and creates
    no iframe (T27); `announce(v2)` then writes `viewer=v2` (T11). A tier crossing's DOM move
    fires T15 only, never T16.
  - **C7-7 preset:** with a fake `plrViewer` whose `resources()` is empty, a load with the
    preset `front` calls no `view()`; once `resources()` is non-empty, exactly one
    `view("front")` follows.

Mount it from `index.js`.
- Depends on: A5, B9, C4, and AC-1 branch S1-A or S1-B. On S1-C, stop and escalate (D1).
- Closes: the unit half of AC-35 and AC-36, and the unit half of AC-38 (the D11 state
  table rows).
- Gate: [BUN].
- Size: ~480 LOC (raised in Revision 6 for the 22 row tests, and in Revision 7 for T23–T27,
  `viewerPanel` and the preset wait).

**C6: Staging and offline.** Add the C6 paths to `assert_dist_complete` and to
`test_display_staging.py`. Confirm that manifest collection picks up `viewer3d.py` and that
no `plr_visualizer3d` path is staged (AC-33; Revision 10: there is no vendored Python).
- Depends on: C2, C3, C4, C5.
- Closes: AC-33 (local parts).
- Gate: [PY:test_display_staging.py], [PY:test_contract_covers_imports.py], and a build.
- Size: ~60 LOC.

**C7: `--dock-check` gate and CI wiring.** Add `run_dock_check` with the D16 units K1a
(AC-34, AC-35, AC-37), K1b (AC-38) and K2 (AC-36), and the negative-only unit N-d
(AC-39(d)), each a `--scenario` in its own subprocess with its D16 budget (10, 14, 15 and
6 min), using the full-Chromium launch and SwiftShader args (D16), the
persistence-ack init script (D16), AC-36 keyed by the recorded D6 sizing case and run in its
stated one-page execution order (including
the 1600→1920 `resize_within_wide` case and `iframe_reloads_during_resize`), AC-38 in its
stated execution order (including `preset_survives_reload`, `redock_live` and
`restart_placeholder`) with every iframe read taken from the panel DOM (never a held
element), AC-38's `late_iframe` ordering listener and `many_reloads`, and the harness-only
`--neg drop-query` init script for AC-39(e). Extend the two AC-42 tests for the dock units.
Run the extended R21 check (AC-31). Add to CI:
- a `vendor_visualizer3d.py --check` step against the submodule the REPL job already
  initialises (Revision 10: no separate PLR checkout step, since the pin is the source)
- one `--dock-check --scenario <id>` step per unit K1a, K1b, K2 (step timeouts 12, 16, 17,
  `if: ${{ !cancelled() }}`), each self-bounded by the `--scenario` watchdog, the
  `--dock-check --aggregate-only --base-path /praxis/` step (hashed arguments equal to the
  scenario steps', C8-4), the dock out dir in the `if: always()` upload (the existing reap
  step also covers dock units), and the job-level backstop raised to 137

Commit `260929_nd_sensitivity_sprint_c.py` and its sidecar (one outcome each for (b), (c),
(d), (e)), then run them through `bth run` (D17), each negative with its own `--serve-dir`
and `--out-dir` under `/tmp/claude-1000/nd-neg/<negative>/` (C8-5).
- Depends on: C6.
- Closes: AC-30 (CI), AC-31's extended R21 check, AC-33 (CI), AC-34 to AC-39, AC-40 for its
  sprint C key, AC-41 for sprint C, and AC-42 for the dock units.
- Gate: interim, a local unsandboxed run of each unit alone (D16). Final: a green REPL
  workflow on the PR head.
- Size: ~450 LOC (raised in Revision 7 for the unit split, the three new AC-38 keys and the
  sensitivity driver's sprint C entry).

Sprint C order: C1 and C2 in parallel; C3 and C4; C5; C6; C7.

| Task | Sprint | Scope | Depends on | Closes |
|---|---|---|---|---|
| A1 | A | `scripts/unit_runner.py` + test, lazy `notebook_expected()` in `repl_smoke.py` + import test, S1 probe/sidecar `harness` amendment, then S1 spike | none | AC-1, AC-42 (runner cases) |
| A2 | A | S2 spike | A1 (`unit_runner.py` and the lazy `notebook_expected()` only) | AC-2 |
| A3 | A | S3 spike | A1 (`unit_runner.py` and the lazy `notebook_expected()` only) | AC-3 |
| A4 | A | theme CSS + CSS test | A1 | AC-4 |
| A5 | A | shell display skeleton, chrome.js, loader | A1 | AC-5 |
| A6 | A | staging | A5 | AC-6 |
| A7 | A | `--display-check` driver, units D1, D1-dark + CI + AC-39(a) sidecar | A1, A4, A5, A6 | AC-7, AC-8, AC-40 (A), AC-42 (D1, D1-dark) |
| B1 | B | svg, floor, budget | none | AC-12/13 (pure) |
| B2 | B | fixture port to the pin + labware reprs | B1 | AC-9, AC-10 |
| B3 | B | deck repr | B2 | AC-11, AC-12, AC-13 (except error-panel case) |
| B4 | B | glossary + RunLedger | B2 | AC-14, AC-28 |
| B5 | B | error context | B4 | AC-15 |
| B6 | B | error panel + handler | B2, B4, B5 | AC-16, AC-13 (error-panel case) |
| B7 | B | staleness (kernel) | B2 | AC-18 |
| B8 | B | install + bootstrap stage + colour test | B2, B3, B4, B6, B7 | AC-17, AC-20, AC-27 |
| B9 | B | shell stale + interaction | A5, B7 | AC-19 |
| B10 | B | `--display-check` units D2–D4 | B8, B9 | AC-21 to AC-26, AC-41 (B), AC-42 (D2–D4) |
| C1 | C | S4 spike | A1 (`unit_runner.py`, on `main` since sprint A) | AC-29 |
| C2 | C | vendoring `static/` + tree | none | AC-30 (local) |
| C3 | C | DockedViewer3D over the pin's `pylabrobot.visualizer3D` | C1 | AC-31 (except extended R21 check) |
| C4 | C | socket shim + embed | C2 | AC-32 |
| C5 | C | deck panel widget | A5, B9, C4, S1-A/B | AC-35/36 (unit) |
| C6 | C | staging + offline | C2–C5 | AC-33 (local) |
| C7 | C | `--dock-check` units K1a, K1b, K2, N-d + CI + AC-39 sidecar | C6 | AC-30, AC-31 (extended R21 check), AC-33 to AC-40 (C), AC-41 (C), AC-42 (dock units) |

---

## 7. Risks

| Risk | Mitigation / rollback |
|---|---|
| S1-C: no widget constructor is reachable without a labextension | D1 stops C5 and escalates to the user, who decided "a real widget". Sprints A and B do not depend on the widget and still merge. |
| The sanitizer strips SVG, `class` or `style` on reopened notebooks | Resolved by design (D1, S2 branches; S2-T covers a notebook that reopens trusted). Live outputs are unaffected, and reopened ones degrade to stated states. AC-24 asserts the recorded branch, so the degradation cannot be silent. |
| The Pyodide kernel's execution path ignores `set_custom_exc` | S3-C falls back to an instance-level `showtraceback` wrapper. If that also fails, B6 stops and MVP item 3 is escalated. |
| `mimebundle_formatter` does not accept `(data, metadata)` in the kernel (S3-B), so the stamp has no carrier | S3(b′) tests the per-type `text/html` formatter's `(html, {"praxis": stamp})` return (verified in IPython `core/formatters.py:243-250`); the stamp then rides at `metadata["text/html"]["praxis"]`, and one reader, `stampOf`, serves `stale.js`, `dock.js` and both harnesses, so AC-21 holds unconditionally. If (b′) also fails, B7 and B9 stop and escalate. |
| Frame-local names in PLR (`op`, `channel`, `resources`) change on a pin bump | Owner resolution is by **identity** first and `thing` second. Frame locals are used only for the loop channel (including owner rule (e)), the op wells and `vols`, and only from frames whose `co_name` is in `glossary.ACTIONS`. AC-15 runs against the real pin, so a bump that breaks it fails CI. |
| The panel's numbers differ from PLR's message (PLR's include pending state) | By design (D8 step 4): the body uses committed state summed per resource, and PLR's message is shown verbatim in the "PyLabRobot raised" line. AC-15 E9 and AC-16 check the two never mix. |
| Uncommitted tracker state (residue) makes drawings or error numbers mislead | Revised in Revision 10 for the 1.0.0b1 pin: a failed `aspirate`/`dispense` rolls every channel back and leaves **no** residue; only a failed `pick_up_tips`/`drop_tips` (queue loops still outside the `try`) and direct tracker use leave pending state (D8 "Panel drawing"; the PLR 1.0 recon). The error panel draws committed volume and uses committed numbers, a defence for exactly those paths (AC-16 forces it by direct tracker use on a well **outside** the failing op, since the op's own rollback erases residue on its resources; Revision 11, C11-2). Other outputs follow PLR's own `get_used_volume()`, and a pending-only change bumps `rev` for them (D7). A raise caused only by residue, where the resolved owner is not in the committed offending set, resolves to `None` and gets the generic panel rather than numbers that describe no fault (D8 step 4; AC-15 E13, E14, E15, AC-17 E13, E15). OQ-6 raises the tip-op case upstream. |
| A pin bump silently changes what an AC case exercises (0.2.2's E13 and E15 stopped raising at 1.0.0b1) | Every AC-15 case raises the real error at the pin in CI, so a case that stops raising fails its test rather than passing vacuously; E15's raise and E14's pending state are confirmatory asserts inside their cases (Revision 11, C11-5, C11-6). The Revision 10 recon re-checked every PLR-dependent claim; the next pin bump repeats that check. |
| PLR 1.0 rollback fires tracker callbacks, so a failed op would mark outputs "Changed since" although nothing changed | D7 drawn-state digest filter: callbacks only mark dirty; `rev` bumps only when what the output draws changed; settled before each render and at `post_run_cell`. AC-18 "Rollback does not bump" (with a recording callback proving the callbacks fired) and "Settle before render". PLR's registration now appends, so `stale.py` enforces idempotency with its own `_subscribed` set. |
| Errors inside `*96` ops bind different locals (`containers`, a scalar `volume`) | Out of MVP scope (orchestrator ruling 260929): D8 step 2 short-circuits to `None` and the generic panel; AC-15 E-96 checks it. The `*96` glossary names and ledger wrappers remain, for the ledger only. |
| `RunLedger` instance shadowing breaks a user's own wrapper on `lh` | It shadows only inside the `with` block, restores on exit even on error (AC-14), and is only used when the user writes it. |
| Staleness announcements on `praxis_repl` disturb device authorization | At most one small typed message per cell (4 KiB cap); there is no session message (the current session is derived per notebook panel from its outputs, D7). Both existing listeners ignore unknown types (`praxis-shell.js:84-88`, `praxis_bootstrap.py:214, 266` on the sprint A branch). The D7 R21 check still guards `praxis/viz/` (the plain grep exits 0 on three documentation mentions on `main`; the check strips only that form, Revision 10). Rollback: move `stale.py` to its own channel; the shell change is one constant. |
| Viewer3D stream messages are structured-cloned to every `praxis_viz3d` listener, including the shell | The shell acts only on `announce` and the kernel `close` (`{viewer, reason}`). The clone cost of a scene message is unmeasured; S4 records the scene bytes. If it matters, the announcements move to a separate small channel. |
| Two notebooks each start a viewer | Non-goal. The ids in the protocol keep messages unambiguous, and the most recent `announce` wins. Within one kernel, re-running `dock()` stops the previous viewer first (D11, AC-31). Two notebooks with two kernels never mark each other's outputs "Drawn in an earlier session": the current session is per panel (D7, AC-19). |
| Dead page clients (reloads, drawer moves, 60 s give-ups, a long synchronous cell delaying `accept`) fill the 4-client cap | The shim posts `bye` on `close()`, `pagehide` and its accept timeout, and ignores a late `accept`; at the cap the kernel evicts the oldest client (`evict`), so a new page always gets `accept` (D11). AC-31 (eviction), AC-32 (`bye`, `evict`) and AC-38 `many_reloads` (6 reloads) test it. With more than 4 live pages, eviction rotates: accepted under the multi-viewer non-goal. |
| The stock `PACKAGE_ROOT` resolves inside the installed PLR package, which at the pin ships 63 `.glb` files, so fixture models could become `mesh` entries whose URLs nothing serves | `viewer3d.py` rebinds `pylabrobot.visualizer3D.server.PACKAGE_ROOT` to an empty `tempfile.mkdtemp()` once, in a guarded idempotent helper at the first construction (Revision 11, C11-13): a module global, so the override set stays at three and no PLR file changes (D11, GATE X; AC-31's state snapshot proves it is the only change, C11-4). Load-bearing at the pin (Revision 10). S4 records both roots, the walk time and whether the scene carries `mesh` (AC-29); AC-31 asserts the rebind, with a positive control showing a seeded `.glb` yields a `mesh` without it and none with it. |
| A same-origin page (another project page on the shared `*.github.io` origin) drives `praxis_viz3d` | D11 threat model: such a page already has kernel code execution through `praxis:execute` on `praxis_repl`, so no nonce is added. Inbound traffic is bounded: 4 virtual clients (the oldest evicted at the cap), non-JSON and unknown kinds dropped (AC-31). |
| Vendored three.js tree (~2 MB) grows dist and the offline gate | AC-30 asserts zero CDN URLs, and AC-33 keeps `--probe --offline` green. The build logs the size. |
| The PLR wheel grew from 1.26 to 10.2 MB at the pin (the PLR 1.0 recon), which may lengthen boots and push units past their budgets | Budgets are estimates; the first CI run of each unit records its wall time, and a budget is revised only with the orchestrator's approval, at ≥ 1.5× the measured time, never as a whole-run timeout (D16). A timeout names its unit, so the cost is visible per unit. |
| A pin bump changes the vendored `static/` or the pin's `Viewer3D` | `vendor_visualizer3d.py --check` in CI against the submodule fails on any byte difference and on a recorded commit that differs from the pin (C7, AC-30); updating is an explicit re-vendor. GATE X part 1 runs against the real pin in CI (AC-31), so a bump that needs a fourth override fails there. |
| `repl_smoke.py` raises at import without the submodule initialised at the pin (`NOTEBOOK_EXPECTED`, `:1449` on origin/main a176bac7, `:1450-1454` on the sprint A branch), breaking local spike drivers and tests | Revision 11 (orchestrator ruling (a), C11-3): A1 makes it lazy (`notebook_expected()`, about 6 lines), so every consumer may load the module in any checkout; `test_repl_smoke_import.py` proves the import succeeds without `version.txt` and that the prefix is still derived from it when present. Browser runs still need a dist built at the pin; CI is authoritative. Rollback: revert the 6-line change and its test together. (Supersedes Revision 10's `repl_smoke_units.py` split, which the committed S1 probe already contradicted by loading `repl_smoke.py` in its driver.) |
| A committed pre-registration's input set misses a file the probe actually depends on (the S1 sidecar omits `repl_smoke.py`), so a changed harness could be reused under an old stamp | A1 amends the S1 probe's input set and the sidecar's `hashed_inputs` with `harness` in one commit **before the first run**, with the reason in the sidecar and the S1 research note; no run has happened, so this is still a pre-registration and `[outcomes]` are unchanged (Revision 11, C11-3). |
| PLR v1 removes the docstring-deprecated `TipSpot` legacy API (`tracker`, `get_tip`, `has_tip`, `empty`; "TODO: Remove in v1", `tip_rack.py:200-226`) | No Praxis code reads it: owner rule (a) uses `pylabrobot.legacy.tip_tracker.tip_spot_tracker(spot)`, committed tip state uses `TipTracker.get_tip()`, and drawings use `spot.tip` (D7, D8; Revision 11, C11-14). The deprecation is docstring-only (no warning is raised), so the contract's warnings-as-errors probe cannot see a use of it; the guard is that AC-15, AC-16 and AC-18 run against the real pin in CI, so once a pin drops the API any use fails with `AttributeError`. Remaining exposure: `tip_spot_tracker` is itself in `pylabrobot.legacy`, so a later removal of the legacy tracker needs a new committed-tip accessor; the next pin bump's recon checks it. |
| The CI Chromium lacks WebGL2 | D16's full Chromium with SwiftShader args. AC-34 records `hello_backend`, and the canvas check fails loudly rather than passing on a blank frame. |
| Moving the iframe for the drawer tier reloads it | D11 state table T15: the `viewer` id stays in its `src`, the old client posts `bye`, the shim reconnects, and AC-38 `drawer_reconnect` and AC-36 `tier_up_rehomes` test it. |
| A closed deck panel reconnects without exercising `query`, hiding a broken `query` path | D11 state table T3, T4, T6: a closed panel ignores every announce but a page's first; reopen attaches an iframe-less panel and posts `query`, so the only iframe is created by the answering `announce`. AC-38 `late_iframe` asserts the ordering, and AC-39(e) proves it fails with `query` dropped. |
| Piecemeal edits to the deck panel's lifecycle contradict each other (Revisions 4 and 5 each left a neighbouring gap; round 6 found "panel open, no iframe" uncovered after every re-dock) | One authoritative table in D11 (four states, T1–T27, invariants I1–I6); every other section references it. C5 has one test per row plus the C6-1 re-dock sequence; AC-38 runs in a stated order and reads the iframe from the DOM. A future lifecycle change edits the table and its row tests together. |
| A preempted, crashed or hung browser run loses every finished scenario, and one whole-run timeout hides which scenario hung | D16 "Preemption-safe harness design": one unit per scenario, one subprocess per unit with its own budget, a per-unit result and stamp written as each unit completes, resume over stamp-matched units, and one CI step per unit with a step-level timeout (the job timeout is only a backstop). A direct `--scenario` run bounds itself with a watchdog, armed as its first act at the unit's table budget (Revision 8, C8-2; Revision 9, C9-4). Browser and Playwright teardown run inside that bounded region before the stamp, and only `os._exit(stamp.exit)` follows the stamp, so a hang in teardown is a timeout and nothing can hang after the stamp (C9-1). A driver timeout over a valid stamp defers to the stamp and is logged. Spikes and AC-39 runs follow the same design (D17). AC-42 tests it, including a hang after the stamp and a hang in teardown. |
| A hung Chromium survives a unit timeout, because Playwright launches it detached as its own process-group leader (`processLauncher.js:108-111`), so a process-group kill or a CI step timeout orphans it and it holds CPU, memory or ports into the next unit | One shared `scripts/unit_runner.py` (D16, C8-1) used by every unit kind: `kill_tree` stops and walks every descendant and sweeps the per-unit `PRAXIS_UNIT_TOKEN` (exact entry; unreadable environs skipped) for re-parented orphans, repeating both to a fixpoint before the kill and again (after a re-freeze) after the grace; `SIGTERM` is followed at once by `SIGCONT`, so a handler can run and fork during the grace and the second fixpoint catches the fork (Revision 10). It guards against pid reuse with a pidfd, or with a starttime check where pidfd is unavailable, and sends group signals only while a verified member lives. It sends `SIGCONT` in a `finally`, and terminates every collected pid and process group (Revision 9, C9-2, C9-3). Open (Revision 10): whether Chromium keeps the token readable in `/proc/<pid>/environ`; the C10-1 positive control in CI settles it, a failure is a finding, and the fallback is a process-group/session match from the runner's start with the token sweep as the belt (D16). A direct run re-execs so the token is visible in `/proc/self/environ` (C9-4). CI adds an `if: always()` `--reap` step, which refuses to run outside CI without `--force`. AC-42's runner cases prove that a `setsid` grandchild dies, with and without its parent, and that a grace-window fork dies. A CI-only case proves that no real headless Chromium survives (C9-5). Rollback: revert the module and its callers together (no caller kills processes itself). |
| Resume reuses a stale or tampered result and a gate passes on old evidence | A unit is reused only when every input sha256 (dist, notebook, harness, runner, chrome, args, driver; `runner` added in Revision 9, C9-6) and its result sha256 match, its stamp has `exit == 0`, and every listed key is present and holds. A unit clears its own result and stamp before running, and its watchdog deletes any result it wrote before timing out, so a timed-out re-run leaves nothing to reuse (C8-3, C9-6). The aggregate lists every reused unit with its source and hashes; `--aggregate-only` never deletes, so a mismatch stays diagnosable (C8-4). CI never reuses across workflow runs. The pass rule is unchanged by reuse (AC-42). |
| A negative run overwrites real results, or a spike unit whose probe raised is silently treated as absent or reused | Each AC-39 negative has its own `--serve-dir` and `--out-dir` under `/tmp/claude-1000/nd-neg/<negative>/`, and the harness refuses a non-default dist or `--neg` without `--out-dir` (C8-5). A raised spike probe is a complete unit with an `error` finding that counts toward `[outcomes]` and is never reused; only a timeout or a stampless crash is incomplete, as each sidecar pre-registers (D17, C8-7). |
| A kernel restart leaves a frozen deck that looks live (the dead kernel posts no `close`) | D11 kernel-restart event on the viewer's kernel's `sessionContext` (T25, T26), treated like a kernel `close` for the current viewer; C5 unit cases and AC-38 `restart_placeholder`. The residual case (viewer's kernel unknown with several live kernels) is stated under the multi-notebook non-goal. |
| A new import names a shim home or a module the import contract lacks | Revised in Revision 10: no PLR Python is vendored. `viewer3d.py`'s own `pylabrobot.visualizer3D.server` import gets its contract entry in C3, and every sprint B import uses the pin's non-shim homes (D8); `test_contract_covers_imports.py` and the contract's no-shim test and warnings-as-errors probe gate C3 and sprint B (AC-31, AC-41). |
| A Lumino split ignores CSS min/max, or layout sizing is unreachable | S1 records `css_limits_honoured`, `dock_layout_sizing_reachable` and `css_limits_refit`, which select a row of the D6 sizing-case table; every AC-36 width key then has a mechanism or a recorded-only status (AC-36 is keyed by case). Layout sizing goes through the main DockPanel's `saveLayout()` / `sizes` / `restoreLayout()` (a `DockLayout` has no `setRelativeSizes`); CSS-only reaches ≥ 1600 with inline px limits plus `parent.fit()`, asserted only if `css_limits_refit`. `dock.js` calls `parent.fit()` after every tier change inside the split. AC-36 drags the splitter for real, and AC-39(d) proves the ≥ 1600 check fails on a stock 50/50 split wherever that key is asserted. Under S1-L every width key is recorded only and the drag is unclamped (drawer and height keys stay asserted): a stated deviation, consistent with the user's 260929 "split initially" ruling. Whether Lumino re-reads limits after `fit()` is exactly what S1 measures. If `restoreLayout()` reloads the widget's iframe (`restore_layout_keeps_iframe = false`), layout sizing is limited to open and tier changes, and AC-36 `iframe_reloads_during_resize` = 0 catches any clamp that reloads. |
| A user-controlled resource name injects markup into a trusted output | D2 escaping (`esc_text` / `esc_attr`, escaped traceback) and D14 matching by `dataset.praxisRes`. AC-9, AC-16 and AC-19 carry hostile-name cases. |
| The detail-floor math is wrong in the browser because CSS scales SVGs | D5 puts an explicit `min-width` on each SVG, and AC-12 checks the math. Rendered sizes are a human check (H1). If S2-A' strips `style`, the floor holds only for live outputs (stated). |
| The display layer throws at boot | D13 makes it non-fatal and loud (`praxis:display-error`). AC-20 tests both paths. |
| The notebook-check gate trips on the new error rendering | `welcome.ipynb` raises no PLR error. The error cases live only in `display_check.ipynb`. |
| Merge conflicts in `praxis-shell.js` with other appenders (persistence, P5.6) | One appended IIFE. Rollback reverts the IIFE, and the rest is inert. |
| Rollback overall | Each sprint adds files and migrates no data. There are no new storage keys. Reverting a sprint's PR removes its behaviour, and saved notebooks keep valid `text/plain` outputs. |

---

## 8. Open questions (user; non-blocking unless marked)

- **OQ-1.** Should the REPL's default theme change from JupyterLab Dark (`jupyter-lite.json:18`)
  to Light, where the design is complete? The default is no (D10).
- **OQ-2. Closed (user, 260929).** At PLR 0.2.2 no liquid identity is tracked, nor at the
  1.0.0b1 pin (D15). The user
  decided: "keep blue as volume, we can make things more complicated later." Volume only is
  the MVP; identity returns when PLR records it.
- **OQ-3.** The 1024–1279 drawer is built and gated functionally. Are human quality checks at
  ≥ 1280 only acceptable, as "MVP targets ≥ 1280" suggests?
- **OQ-4.** At ≥ 1600 px the deck panel takes "the rest", which is unbounded. Is a maximum
  wanted, for example 720 px?
- **OQ-5.** The 3D selection keeps the page's own blue, transient box (D12). Should a request
  go to PLR upstream for a persistent, colourable highlight API?
- **OQ-6.** At the 1.0.0b1 pin, a tracker error inside a `pick_up_tips` or `drop_tips`
  queue loop leaves earlier channels with uncommitted pending tip state (LH ~755-761,
  ~901-911), because those loops are still outside the `try`. `aspirate` and `dispense` no
  longer do: they queue inside the `try` and roll every channel back (LH ~1265, ~1466), so
  they leave no residue (Revision 10; the PLR 1.0 recon). Should the tip-op case be reported
  upstream?
- **OQ-7. Resolved (Revision 10).** The question was which PLR main commit to vendor. The
  1.0.0b1 pin (`origin/main` a176bac7) is `786ac2c4e4f7afe37885af2d98ff5b0afe274c67`, the
  commit whose 56-file `pylabrobot/visualizer3D/` tree was fetched and measured (matched blob
  for blob by the orchestrator, 260929; the 260929 WebGL2 measurement used it). C2 vendors
  `static/` from the submodule at the pin and records that commit; a pin bump re-vendors.
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
  - `build_repl.py:830-895` (shell staging), `:979-1047` (`assert_dist_complete`) at the
    base; on origin/main a176bac7 `stage_shell` is at `:1016` and `assert_dist_complete` at
    `:1193`
  - `praxis_bootstrap.py:289-398` (stage ledger) at the base; `:289-421` on origin/main
    a176bac7 (`verify_identity` `:415`, `praxis:ready` `:421`)
  - `praxis-shell.js:54-105` (channel listener)
  - `scripts/repl_smoke.py` (repo root): `:101-184` (Chromium resolution, launch args),
    `:1226-1430` (`run_notebook_check`) at the base `fd987728`; on origin/main a176bac7
    `run_notebook_check` starts at `:1482`, prints its single `RESULT` at `:1788`, reads
    outputs model-first at `:1572` and `:1624`, and derives `NOTEBOOK_EXPECTED` at import
    (`:1449`, via `:1426-1441`). On the sprint A branch: `resolve_chrome_path` `:105`,
    `find_repo_root` `:315-328`, `NOTEBOOK_EXPECTED` `:1450-1454` with use sites `:1656`,
    `:1666`, `:1680`, `:4451` (made lazy by A1, Revision 11)
  - `.github/workflows/repl.yml:146-226`; `:43` (the single job-level `timeout-minutes: 45`,
    origin/main a176bac7; `:47` on the sprint A branch). Sprint A branch also: `paths:`
    filters `:17-37`, `submodules: recursive` and the submodule assertion `:56-61`, CI
    Python `3.12` at `:68`, `test_s1_spike_driver.py` wired at `:264`
  - `scripts/unit_runner.py` on the sprint A branch (Revision 11, C11-9): `_wait` `:350-354`,
    `kill_tree` `:395-441`, `run_unit` `:455-485`, `ensure_token` `:496-516` (`sys.orig_argv`
    `:509`), `Watchdog` `:549-638` (token check `:579-583`, `write_result` `:604-610`,
    `commit` `:612-622`)
  - S1 probe at A1b-1 (`60e892fe`, branch `feat/notebook-display-sprint-a`):
    `scripts/spikes/260929_s1_lumino_widget.py` (`REPL_SMOKE_PATH` `:65`, `repl_smoke()`
    `:219-225`, `InputEnv` `:240-252`, `build_env` `:265-283`, `compute_inputs` `:286`,
    `run_driver` `:1757`) and `.bth.toml` (`hashed_inputs` `:109`)
  - `web-repl/overlay/assets/python/praxis/viz/transport.py:10,11,26` (the three RST
    documentation mentions of `praxis_repl` the D7 R21 check strips)
- PLR Visualizer3D at the 1.0.0b1 pin (`external/pylabrobot/pylabrobot/visualizer3D/`; the same
  tree as the earlier fetch to `/tmp/claude-1000/plr-main/pylabrobot/visualizer3D/`):
  - `server.py:98` (`PACKAGE_ROOT`), `:104-105` (`_models_on_disk`), `:155` (class),
    `:216`/`:224` (`_register_meshes` and its global read), `:353` (`_broadcast`),
    `:559-603` (hello and `_handler`, `:590`), `:711-783` (`__init__`), `:785-811` (`start`),
    `:829-850` (`stop`)
  - `static/transport.js:56-93`, `static/index.html:319-339`, `static/app.js:172-223`
    (`window.plrViewer`), `static/renderer.js:117-121, 261-264`, `static/constants.js:118-121`
- PLR 1.0.0b1 pin (`external/pylabrobot`, `786ac2c4e`; `LH` =
  `pylabrobot/legacy/liquid_handling/liquid_handler.py`), per the PLR 1.0 recon:
  - `resources/errors.py:8-22`
  - `resources/volume_tracker.py:14` (tracking default), `:102`/`:108`
    (`validate_remove_liquid`), `:111-112` (pending bump), `:117` (`validate_add_liquid`)
  - `legacy/tip_tracker.py:118, 153, 166`; `resources/tip_tracking.py:5`
  - `resources/container.py:87`, `resources/resource.py:1236-1251, 1364`
  - LH `:88`, `:418`, `:643-645`, `:727`, `:755-761` (`:758`), `~901-911`, `:998`, `:1000`,
    `:1047`, `:1058`, `~1265`, `:1273`, `~1466`, `:1674-2229`, `:1876`, `:1908`
  - `resources/hamilton/star_decks.py:209` (`STARLetDeck`), `:225` (`size_x=1005.0`);
    `hamilton_decks.py:811` is only the `_OLD_CONSTANTS` entry (Revision 11, C11-12)
  - `resources/tip_rack.py:125-131` (`TipSpot.tip`), `:200-226` (the legacy API, "TODO:
    Remove in v1"), `:286-303` (`tip_origin`); `resources/tip.py:52` (a tip's
    `VolumeTracker(thing=name)`); `legacy/tip_tracker.py:105-119` (`has_tip`, `get_tip`),
    `:233-258` (`tip_spot_tracker`); `resources/volume_tracker.py:69-75` (`set_volume`),
    `:91-97`, `:114-119`, `:156-163`; LH `:1268-1292`, `:1470-1490` (Revision 11)
- PLR 0.2.2 (`external/pylabrobot`, `dd79c4c89`; historical, the pin before a176bac7):
  - `resources/volume_tracker.py:74-86, 122-138` (D15)
  - `resources/well.py:19-28`
  - `pylabrobot/__init__.py:67-118`
- Upstream: PyLabRobot #1378 (Visualizer3D, merged 2026-09-27); PLR #1308 (Petri dishes, Next);
  `stefangolas/pylabrobot@viz3d-motion` (unmerged, slot only).
- Round 1 review: `.praxia/docs/audits/260929_notebook-display-round1-challenger.md`,
  `.praxia/docs/audits/260929_notebook-display-round1-defender.md`.
- Round 2 review: `.praxia/docs/audits/260929_notebook-display-round2-challenger.md`,
  `.praxia/docs/audits/260929_notebook-display-round2-defender.md`.
- Rounds 3 to 9: `.praxia/docs/audits/260929_notebook-display-round{3,4,5,6,7,8,9}-challenger.md`.
- Round 10: `.praxia/docs/audits/260929_notebook-display-round10-challenger.md`.
- Round 11 (Revision 11's work order, with the binding orchestrator dispositions):
  `.praxia/docs/audits/260929_notebook-display-round11-challenger.md` (audit
  `260929_notebook-display-design_spec-challenge_r11`).
- The PLR 1.0 recon (Revision 10's evidence):
  `.praxia/docs/research/260929_notebook-display-plr10-premises.md`.
- Playwright's detached Chromium launch:
  `praxis/web-client/node_modules/playwright-core/lib/server/utils/processLauncher.js:108-111`
  (`detached: process.platform !== "win32"`; verified by the orchestrator, 260929, round 8).
- The user's preemption rule (global instructions, 260929): intensive calculations are
  preemption-safe and recoverable by design (per-unit output and completion stamp, sha256-
  verified resume, per-chunk timeouts, design in the spec and the sidecar).
- IPython `core/formatters.py:243-250` (per-type `(data, metadata)` unpacking; S3(b′)).

## Revision 1 (260929)

Round-1 adversarial review: challenger REVISE (2 BLOCKER / 13 MAJOR / 14 MINOR), defender
REVISE (audits `260929_notebook-display-design_spec-challenge_r1` / `_spec-defense_r1`). The
defender's ordered amendment list A-1..A-20 was applied as ruled, with the orchestrator's
rulings: the C1-9 threat model is verified and no nonce is added; S1-L is accepted as a
stated deviation; OQ-2 is closed by the user's volume-only decision. C1-27 (move S4 to sprint
A) was REBUT and changed nothing. No AC or task was added or renumbered: every change appends
keys or cases to existing ACs. Each entry gives the amendment, the finding(s) it closes, and
where it landed.

- **A-1 (C1-1, BLOCKER): deck detail floor.** Deck `s_min = max(0.88·s_n, 0.6)`; the text
  floor is derived for every figure; worked check redone for the STARLet (`s_min ≈ 0.771`,
  min-width ≈ 775 px, scrolls ≈ 65 px at 710 px). Landed: D5; AC-12 (STARLet value, deck
  narrower than 880 mm).
- **A-2 (C1-2, BLOCKER): viewer id delivery.** New `query` kind (shell → kernel); iframe `src`
  set with `&viewer=<id>` on every announce; shim posts nothing without `viewer` and closes
  after 3 s; `dock()` keeps a module-level current viewer and awaits its `stop()`. Landed: D11
  protocol and `dock()`; D12 embed mode; §3.6; §4 viewer3d/socket/dock rows; AC-31 (second
  dock, `query`); AC-32 (no viewer); AC-38 (`redock_reloads`, `late_iframe`); C3, C4, C5.
  *(Superseded in part by Revision 2 B-2: `src` is set on every announce only while the panel
  is open; a closed panel holds no iframe, and reopen gets `src` only via `query`.)*
- **A-3 (C1-9): threat model.** Token rationale replaced by the origin threat model (existing
  `praxis:execute` path, broadcast-visible nonce rejected, upstream checks defend a
  cross-origin websocket that does not exist); 4-client cap; non-JSON and unknown kinds
  dropped. Landed: D11 "Threat model"; AC-31 (client 5, unknown kind, non-JSON); §7 new row.
  *(Superseded in part by Revision 2 B-1: at the cap the oldest client is evicted and the fifth
  `open` gets `accept`; the page→kernel `close` kind is renamed `bye`.)*
- **A-4 (C1-14, C1-22, C1-26): kernel start/stop.** `dock()` awaits
  `wait_for_browser(timeout=15)`, reconnect hellos stated; no `_models_on_disk` pre-warm, S4
  times it; meshes unsupported; `stop` ends every connection and awaits its handler task.
  Landed: D11 Python and Kernel; D1 S4 row; D16; §4 S4 and viewer3d rows; AC-29; AC-31 (no
  `mesh`, no pending `_handler`, timeout line); AC-34 (`clients_seen[-1]["backend"]`); C1, C3.
  *(Extended by Revision 2 B-4: the stock `PACKAGE_ROOT` is the contents drive, so
  `viewer3d.py` rebinds it to an empty temporary directory; S4 times the walk over that root.)*
- **A-5 (C1-28): socket.js tag position.** AC-30 asserts the first `<script`, immediately
  followed by the original `:319` gif.js tag.
- **A-6 (C1-3): import contract.** C2 adds `("pylabrobot.resources.resource", "Resource")`
  and an ADR §2 addendum; each sprint B task adds entries for its new `pylabrobot.*`
  imports; the contract test gates C2 and B2–B8. Landed: D11 Python; §4 (`plr_contract.py`,
  ADR rows); AC-30; AC-41; sprint B preamble; B2–B8 gates; C2; §7 new row. *(Superseded in
  part by Revision 10: no PLR Python is vendored, so the `pylabrobot.resources.resource`
  entry and the ADR addendum are dropped; C3 adds the entry for `viewer3d.py`'s own
  `pylabrobot.visualizer3D.server` import. The sprint B rule stands.)*
- **A-7 (C1-4, C1-19, C1-20): error context.** Frame filter on `glossary.ACTIONS` (innermost
  supplies locals, outermost supplies `action`); owner rule (e); offending set and body
  numbers from committed state with demand summed per resource; tracking note corrected.
  Landed: D8 steps 2–4 and "Tracking"; §3.3; AC-15 (E4 via rule (e), E9, E10, E11, E4-off,
  E6-off, comprehension frame); AC-16; B5; §7 rows. *(Superseded in part by Revision 2:
  B-10 removed the comprehension-frame case (the filter stays as defence); B-8 replaced "the
  resolved owner is always in the offending set" with the pending-residue rule; B-9 removed
  `head96` from owner rule (b) and added the `*96` short-circuit.)*
- **A-8 (C1-5): RunLedger nesting and step hand-off.** In-flight ops become children;
  counts use top-level rows; `_ERROR_STEPS` / `step_for`; ledger shown on the error path
  before the panel. Landed: D9; D8 handler; §3.3; AC-14; AC-16; AC-17; B4, B6.
- **A-9 (C1-10, C1-18, C1-24): escaping, stamp, MVP figures.** `esc_text`/`esc_attr`,
  escaped grid JSON and traceback, `dataset.praxisRes` matching; stamp gains `exec`, one term
  "display session id"; figures for Plate/TipRack/Deck/Well only, other containers
  sentence-only. Landed: D2; D7 stamps; D14; §2 non-goals; §3.2; §3.4; §4 svg/labware rows;
  AC-9 (keys, hostile name); AC-10 (Trough, infinite volume); AC-16 (escaped traceback);
  AC-19 (exact name); B1, B2. *(Extended by Revision 2: B-6 makes `resource`/`rev` nullable
  by kind; B-5 adds the S3-B carrier `metadata["text/html"]["praxis"]` and the `stampOf`
  reader.)*
- **A-10 (C1-23): byte budget.** Target revisions need orchestrator approval in the sprint
  PR; ladder level 1 drops `data-praxis-grid`; traceback capped at 16 KiB, tail kept;
  everything counts toward 64 KiB. Landed: D4; §4 budget row (`cap_tail`); AC-13; B1, B6.
- **A-11 (C1-11, C1-12): session and mark survival.** `install()` posts
  `praxis:display-session`; last session wins; no session marks before one; marks kept in
  memory and re-applied on `outputs.changed`, the re-attach signal and `activeCellChanged`.
  Landed: D7; D1 S1 row; §4 stale.py/stale.js rows; AC-18; AC-19; AC-23
  (`mark_survives_scroll`, `earlier_session_marked`); B7, B9, B10. *(Superseded in part by
  Revision 2 B-7: the `praxis:display-session` message and "last session wins" are deleted;
  the current session is derived per notebook panel from its outputs. Mark survival is
  unchanged.)*
- **A-12 (C1-13): cell state.** `cellState(model, {running, snapshot})`, precedence,
  post-reload behaviour. Landed: §3.1; §4 chrome.js row; AC-5. *(Amended by Revision 2
  B-11: `stale` requires a non-null execution count and a snapshot.)*
- **A-13 (C1-8, C1-25): sizing and drawer.** DockPanel `saveLayout`/`sizes`/`restoreLayout`
  replaces `setRelativeSizes`; S1 records `dock_layout_sizing_reachable`; branch S1-L
  (accepted deviation); ≥ 1600 formula ±8 px at 1600×900 and 1920×1080; drawer auto-open,
  dismiss, reopen and tier crossing. Landed: D1 S1 row; D6; §3.6; §4 S1 and dock rows; AC-1;
  AC-36 (formula, S1-L recording, `drawer_dismiss_reopen`, `tier_up_rehomes`); AC-39(d);
  A1, C5, C7; §7 row. *(Superseded in part by Revision 2 B-3: S1-L no longer sets a width
  "once at open"; every width key is keyed by the D6 sizing-case table, and under S1-L every
  width key is recorded-only.)*
- **A-14 (C1-21): preset held.** `dock.js` holds the preset (initially `top`) and always
  calls `focus(name, preset)`. Landed: D12; §3.4; AC-35 (`follow_keeps_preset`); C5.
- **A-15 (C1-7): reopened trusted.** S2 probes the executed-saved-reopened path; branch
  S2-T. Landed: D1 S2 row; §4 S2 row; A2; AC-2 (column, per-path branch); AC-24
  (path, S2-T keys); B10; §7 row.
- **A-16 (C1-6): persistence gate.** Harness init script pre-sets
  `praxis-repl-persistence-ack`. Landed: D16; AC-23 and AC-24 (`persistence_gate_never_open`);
  A7, B10, C7.
- **A-17 (C1-29): Dark chrome gated.** Scenario D1-dark (`d1_dark` sub-object). Landed:
  AC-7; A7.
- **A-18 (C1-17): R21 grep extended.** From sprint C it also covers `visualizer3d/`,
  `visualizer3d-augmentations/` and `shell/display/dock.js`. Landed: D7; D11; AC-18 (pointer);
  AC-31; C7.
- **A-19 (C1-16): A6 after A5.** Landed: A6; sprint A order; §6 table.
- **A-20 (C1-15): volume only decided.** Landed: D15; §2 non-goals; §8 OQ-2 closed.

**Consistency fixes made while applying** (not in the amendment list, required by it):
- B5 now depends on B4, because context resolution filters frames on `glossary.ACTIONS`
  (A-7). Sprint B order and the §6 table changed accordingly (B5 no longer parallel with B1).
- B3 also gates on the contract test (deck.py imports PLR); the defender listed B2/B4–B8.
- AC-13's new error-panel case is closed by B6, which owns `errors.py`; B3's and B6's
  Closes lines and the table say so. `cap_tail` lives in `budget.py` (B1).
- AC-31's extended R21 grep needs `visualizer3d-augmentations/` (C4) and `dock.js` (C5),
  which do not exist at C3. C3 runs the AC-18 grep; C7 closes the extended grep. `dock.js`
  is a file, so it is checked with `test -f`, not `test -d`.
- §3.3 gained a template row for a TLL whose owner is a non-`Well` container (needed by E9;
  such owners get no drawing per A-9), and the HasTip tip-spot body uses `{Action}` so that
  E11 reads "Return tips" (A-7).
- §3.3 names the ledger-before-panel order and the step line (A-8), and child rows carry no
  step number.
- `late_iframe` is defined against a closed panel plus `query`, since only a page's first
  announce auto-opens the panel (A-2, A-13).
- D1-dark keys sit in a `d1_dark` sub-object so they do not collide with D1's key names.
- AC-39(d) and the drag-clamp keys are recorded, not asserted, under S1-L. *(Superseded by
  Revision 2 B-3: under S1-L every width key is recorded-only, and AC-39(d) is skipped
  wherever the ≥ 1600 key is recorded-only.)*
- D11 `start` now lists four differences from the stock body (the `_models_on_disk`
  pre-warm is the fourth); the override set, and GATE X, stay at three.
- §7 gained rows for the committed-vs-PLR number difference, the same-origin threat model,
  hostile names and the import contract; the `praxis_repl`, sanitizer, sizing, drawer-reload
  and frame-locals rows were updated.
- B4, B5, B6 and B7 size estimates were raised by 20–40 LOC for the added cases.

## Revision 2 (260929)

Round-2 adversarial review: challenger REVISE (2 BLOCKER / 7 MAJOR / 3 MINOR; all round-1
findings C1-1..C1-29 CLOSED), defender REVISE (audits
`260929_notebook-display-design_spec-challenge_r2` / `_spec-defense_r2`; 10 CONCEDE, 2
PARTIAL). The defender's ordered amendment list B-1..B-12 was applied as ruled, with the
orchestrator's rulings: C2-7 is verified (IPython `core/formatters.py:243-250` unpacks a
per-type `(data, metadata)` return); `*96` errors are out of MVP scope and get the generic
panel. No AC or task was added or renumbered: every change appends keys or cases to existing
ACs (AC-39 gains sub-item (e)). Deletions ruled by the defender (the `praxis:display-session`
message, the comprehension-frame case, "set once at open", `head96` in owner rule (b), "the
resolved owner is always in the offending set") were removed everywhere; the Revision 1 log
above is annotated rather than rewritten. Each entry gives the amendment, the finding it
closes, and where it landed.

- **B-1 (C2-12, C2-1 BLOCKER): protocol kinds and eviction.** Page→kernel `bye
  {viewer, client}`, kernel→one page `evict {viewer, client}`, kernel→all `close
  {viewer, reason}` (the only `close`; the shell acts on it and `announce`). At the 4-client
  cap the oldest client is evicted; the shim posts `bye` on `close()`/`pagehide`/accept
  timeout, ignores a late `accept`, fires `onclose` on `evict`. Landed: D11 protocol preamble,
  table, timeout bullets, inbound bounds and Kernel `start`; D6 drawer-move note; §2
  non-goals (eviction rotation); §4 `viewer3d.py`/`socket.js` rows; AC-31 (eviction, `bye`);
  AC-32 (`bye` ×3 paths, late `accept`, `evict`, no page `close`); AC-38 `many_reloads`; C3,
  C4, C7; §7 threat, stream-clone and drawer rows, new dead-clients row.
- **B-2 (C2-9): closed panel.** No iframe while closed; announces ignored except the first
  (auto-open); reopen creates the iframe with no `src` and posts `query`. Landed: D11 "How
  the page learns the viewer id" and new "Closed panel"; D11 table `announce` row; D6 drawer
  behaviour; D12 embed mode; §3.6 body, states, commands; §4 `dock.js` row; AC-36
  `drawer_dismiss_reopen` (no iframe); AC-38 `late_iframe` ordering; AC-39(e); C5, C7; §7 new
  row. *(Superseded by the Revision 6 state table: the "Closed panel" paragraph is replaced by
  D11's deck-panel state machine, and reopen now attaches an iframe-less panel (T4); the
  iframe is created by the answering `announce` (T6).)*
- **B-3 (C2-2 BLOCKER): D6 sizing cases.** Four-case table; S1 records `css_limits_refit`;
  `parent.fit()` after every tier change inside the split; "set once at open" deleted.
  Landed: D1 S1 row; D6 mechanism (table); §4 S1 row; A1; AC-1; AC-36 (keyed by case,
  `fit_after_tier_change`, drawer/height always asserted); AC-39(d) skip rule; C5, C7; §7
  sizing row.
- **B-4 (C2-3): `PACKAGE_ROOT` rebind.** Rebound once to `tempfile.mkdtemp()` before the
  first viewer; module global, GATE X holds, the one deliberate runtime rebinding. Landed:
  D11 Python (new bullet, meshes bullet) and Kernel `__init__` note; D1 S4 row; §4 S4 and
  `viewer3d.py` rows; AC-29 (both roots, walk over rebound root); AC-31 (rebind,
  `.glb`-no-mesh); C1, C3; §7 new row. *(Kept and made load-bearing by Revision 10: the
  rebound global is now `pylabrobot.visualizer3D.server.PACKAGE_ROOT`, whose stock value is
  inside the installed PLR package with 63 `.glb` files.)*
- **B-5 (C2-7): S3(b′) carrier.** `formatters['text/html'].for_type` returning
  `(html, {"praxis": stamp})`, carrier `metadata["text/html"]["praxis"]`; one reader
  `stampOf`; escalate if (b′) fails. Landed: D1 S3 row (question and S3-B branch); D2
  registration and "One stamp reader"; §4 S3 spike, `install.py`, `stale.js`, `dock.js` rows;
  A3, B7, B8, B9, B10, C5; AC-3 (b′); AC-17 S3-B case; AC-19 (`stampOf` carrier case); AC-21
  `repr_cells_ok` via `stampOf`; §7 new row.
- **B-6 (C2-6): stamps by kind.** `resource: <name|null>`, `rev: <int|null>`; ledger null/null;
  error labware-or-null, rev null; null rev never marked "Changed since"; session marks on
  every kind; Follow skips null. Landed: D2 stamp and "Values by kind"; D7 stamps and
  marking; D12 Follow and click; §3.3 note; §4 `ledger.py`/`errors.py`/`stale.py`/`stale.js`/
  `dock.js` rows; AC-18 (null stamps subscribe nothing); AC-19 (`rev: null` case); B4, B6,
  C5.
- **B-7 (C2-8): per-panel session.** `praxis:display-session` deleted; `panelSession[P]`
  from outputs of executions `chrome.js` observed after P's kernel last started. Landed: D7
  (new "Current session, per notebook panel", R21 paragraph, marking); §4 `chrome.js`,
  `stale.py`, `install.py`, `stale.js` rows; AC-18 (session bullet removed; posts only
  `praxis:resource-changed`); AC-19 (per-panel rules, two-panel case); AC-23
  `earlier_session_marked` (re-run a drawing cell); B7, B9, B10; §7 `praxis_repl` and
  two-notebooks rows.
- **B-8 (C2-4): pending residue → `None`.** Owner outside the committed offending set →
  `None`, generic panel; pending-only callbacks bump `rev`. Landed: D8 steps 4 and 5, panel
  drawing; D7 (one sentence); §2 G5; §3.3 note; §4 `context.py` row; AC-15 E13, E14; AC-17
  E13; AC-18 (pending-only bump); B5, B6, B8; §7 pending row. *(Amended by Revision 10: at
  the 1.0.0b1 pin a failed aspirate/dispense leaves no residue, so E13 became a
  direct-tracker-use case; the rule stands for pick-up/drop residue and direct tracker use.)*
- **B-9 (C2-5): tip-owner TLL and `*96`.** New §3.3 row "TLL, owner is a tip (dispense)";
  step 4 compares per channel for a tip owner; step 2 `*96` short-circuit; `head96` removed
  from rule (b); rule (c) names TLL on dispense. Landed: D8 intro, steps 2–5, rule (b), rule
  (c); §2 G5 and non-goals; §3.3 row and note; §3.5 note; §4 `context.py`/`errors.py` rows;
  AC-15 E12, E-96; AC-16 E12; B5, B6; §7 new `*96` row.
- **B-10 (C2-10): comprehension case deleted.** Step 2 keeps the `co_name` filter as
  defence only (PEP 709). Landed: D8 step 2; AC-15; B5.
- **B-11 (C2-11): stale requires a run.** Landed: §3.1; §4 `chrome.js` row; AC-5 (definition
  and never-run case).
- **B-12: this log and the frontmatter** `adversarial_review` entry.

**Consistency fixes made while applying** (not in the amendment list, required by it):
- D11's protocol preamble listed every kind but `query` as carrying `client`; `announce` and
  `close` carry `viewer` only. Fixed with the new kinds.
- D6 case honoured/unreachable: the ≥ 1600 inline px limits would override the 1280–1599
  media-query CSS, so `dock.js` clears them (with `parent.fit()`) below 1600 px.
- AC-14 (ledger stamp) and AC-16 (error stamps for E1, E5, E4, E12) carry B-6's per-kind
  values, because the ledger and error bundles are built in B4 and B6, not in `stale.py`
  (B7 depends only on B2). AC-18 checks the kernel-side consequence with hand-built stamps.
- AC-35 gains `follow_skips_null` (DOCK key, with a C5 unit half), since Follow lives in
  `dock.js`, which AC-19 does not cover.
- B9's dependency note no longer cites the session message; it depends on A5 for
  `chrome.js`'s observed executions, which the §4 `chrome.js` row now names.
- §3.3 states the generic panel for every `None` result and that a tip owner's stamp is
  `resource: null`; §3.5 notes the `*96` names are ledger-only.
- §2 G5 and non-goals name the `*96` scope cut and eviction rotation; §7 gained rows for the
  S3 carrier, `*96`, dead clients, `PACKAGE_ROOT` and the closed-panel `query` path.
- B7 and B9 carry the S3(b′) stop condition; C7 lists its new harness pieces and runs
  AC-39(e).
- Size estimates raised: B5 ~300, B9 ~360, C3 ~290, C4 ~250, C5 ~380, C7 ~350 LOC.
- References list the round 2 audits and the IPython formatter lines.

## Revision 3 (260929)

Round-3 adversarial review: challenger REVISE (2 MAJOR / 2 MINOR; all round-2 findings
C2-1..C2-12 CLOSED; B-1, B-3 and B-7 judged sound). The orchestrator verified both MAJORs by
running real PLR 0.2.2 on the fixture (`web-repl/design/notebook-display/make_fixture.py`,
chatterbox backend) on 260929, and corrected the challenger's proposed E16 setup (a bare
`discard_tips()` raises `RuntimeError`, not `NoTipError`). No AC or task was added or
renumbered: every change appends cases or keys to existing ACs or edits existing text.

- **R3-1 (C3-1, MAJOR): TLV tip owner uses committed room.** The tip on channel c offends
  only if channel c's request > `max_volume − tracker.volume` (committed); `{avail}` is that
  room. Landed: D8 step 4; AC-15 E15 (→ `None`); AC-17 (E15 generic panel); B5, B6, B8.
  *(Amended by Revision 10: the 0.2.2 E15 setup does not raise at the 1.0.0b1 pin; E15 is now
  a synthetic tip-side residue case, to be verified by B5. The rule stands.)*
- **R3-2 (C3-2, MAJOR): NoTip channel for every tip-using op.** "A channel with no committed
  tip, for any op that uses a mounted tip (Aspirate, Dispense, Transfer, Drop tips, Return
  tips, Discard tips)". Bare `discard_tips()` / `return_tips()` `RuntimeError`s get the plain
  styled traceback. Landed: D8 step 4 and intro; §3.3 generic-panel paragraph; AC-15 E16 and
  two `RuntimeError` negatives; AC-16 E16 ("NoTip, channel", body names "Discard tips"); B5,
  B6.
- **R3-3 (C3-3, MINOR): tier re-homing is not a reopen.** Moving keeps the iframe's `src`
  (D6 drawer note and §7 drawer row unchanged). Landed: D11 "Closed panel" reopen list.
  *(Superseded by the Revision 6 state table: that text had been lost from "Closed panel" by
  Revision 5; the rule now lives in D11 T10, T15 and T21.)*
- **R3-4 (C3-4, MINOR): E10 and AC-39 wording.** Landed: AC-15 E10 (parenthetical deleted);
  AC-39 last bullet ((a) runs first in sprint A's PR, A7, again in B10) and the AC-40 heading
  restored to its own line.
- **R3-5 (implementer notes).**
  - (a) `_clients` is a set; own insertion-ordered map; synchronous removal on evict.
    Landed: D11 inbound bounds; C3 `start` bullet.
  - (b) A cell blocking > ~60 s makes the page give up; placeholder while the viewer lives;
    close/reopen recovers via `query`; accepted. Landed: D11 timeout bullets.
  - (c) Inline ≥ 1600 widths recomputed on `ResizeObserver`. Landed: D6 sizing table
    (honoured/unreachable row); AC-36 `resize_within_wide` (1600→1920); C5 (unit), C7.
  - (d) S1 records `restore_layout_keeps_iframe`. Landed: D1 S1 row; AC-1; A1.
  - (e) Negative control `rerun_not_marked`. Landed: AC-23; B10.
- **R3-6: this log and the frontmatter** `adversarial_review` entry.

**Consistency fixes made while applying:**
- B5's case list now reads E1–E16 and "the four negatives"; B6 names E16 and E15; B8 names
  E15; AC-39's last bullet agrees with A7 and B10, which both run AC-39(a).

## Revision 4 (260929)

Round 4 (`.praxia/docs/audits/260929_notebook-display-round4-challenger.md`) closed C3-1..C3-4
and four of the five R3-5 notes. It raised 2 MAJOR and 2 MINOR findings, applied here directly
by the orchestrator.

| Amendment | Finding | Landed |
|---|---|---|
| R4-1 | C4-1 (MAJOR): after the `plr:gone` edit, "the same placeholder" after `viewer.stop()` pointed at the lost-connection text | §3.6 States (a kernel `close` shows "No deck viewer is running."; only `plr:gone` shows the lost-connection text); D11 "Closed panel" and §3.6 Commands name the no-viewer text; §4 `dock.js` row names both placeholders; AC-38 `stop_placeholder` asserts the exact string, and the absence of "lost its connection". *(Superseded by the Revision 6 state table: the texts are D11 I5/I6 and §3.6 States; "Closed panel" and the §3.6 Commands wording are replaced by references to it.)* |
| R4-2 | C4-2 (MAJOR): `restore_layout_keeps_iframe` was recorded but no branch used it | D1 S1 row (`false` means layout sizing only at open and on tier changes); D6 table note (clamps follow the `unreachable` row); §4 S1 spike row records the key; AC-36 `iframe_reloads_during_resize` = 0, asserted in every case; C7 names it; §7 sizing row |
| R4-3 | C4-3 (MINOR): E3's threshold was ambiguous | AC-15 E3: more than `max_volume` (360 µL), with a source well that holds enough |
| R4-4 | C4-4 (MINOR, parser note) | No content change. ACs are `- **AC-n …**` bullets at line start (41 of them), the same form as the persistence spec |

## Revision 5 (260929)

Round 5 (`.praxia/docs/audits/260929_notebook-display-round5-challenger.md`) closed C4-1 and C4-3.
It found that C4-2 had not reached AC-36, and applied directly:

| Amendment | Finding | Landed |
|---|---|---|
| R5-1 | C5-1 (MAJOR): AC-36 asserted clamp keys in the `reachable` cases even when `restore_layout_keeps_iframe = false` | AC-36 `false`-branch clause; AC-1 lists every width key's resulting status |
| R5-2 | C5-2 (MINOR): no mechanism kept `plr:gone` from showing after a `close` | §3.6 (a `close` removes the iframe, and `plr:gone` is ignored until the next `announce`); C5 unit case; §4 `dock.js` row. *(Superseded by the Revision 6 state table: T12, I4; the Revision 5 text left "panel open, no iframe" without a rule for the next `announce`, round 6 C6-1.)* |
| R5-3 | C5-3 (MINOR): `iframe_reloads_during_resize` counting was unstated | AC-36 (MutationObserver plus a `load` listener per iframe, in the harness only) |
| R5-4 | C5-4 (MINOR): task text lagged | C5 names both placeholders and the `false` rule with a unit test; §4 `dock.js` row mirrors it. *(Placeholder wording superseded by the Revision 6 state table: C5 and the §4 row now reference D11 T1–T22 and I1–I6; the `false` rule is unchanged.)* |

## Revision 6 (260929)

Round 6 (`.praxia/docs/audits/260929_notebook-display-round6-challenger.md`) found 1 MAJOR and
1 MINOR, both in the deck panel's lifecycle. Revisions 4 and 5 had each patched one
symptom in lifecycle prose spread over seven sections, and each left a neighbouring gap. The
cause is fixed: one authoritative state machine in D11, referenced everywhere else. No AC or
task was added or renumbered; AC-38's bullets are reordered to match their stated execution
order.

| Amendment | Finding | Landed |
|---|---|---|
| R6-1 | C6-1 (MAJOR): `dock()` awaits the old viewer's `stop()`, whose `close` removes the iframe (Revision 5), so every re-dock passes through "panel open, no iframe", which no rule covered; a literal build showed "No deck viewer is running." after every re-dock | D11 "Deck-panel state machine": four states (`closed`, `open-waiting`, `open-connected`, `open-lost`), 22 transitions T1–T22, invariants I1–I6; an announce into an open panel with no iframe **creates** it, then sets `src` (T6, T18); re-docking stated as T12 → T6. Replaces D11 "Closed panel", the D11 `announce`/`query`/`close` rows and the long-cell bullet, D6 drawer behaviour, D12 embed mode, §3.6 (intro, Body, States, Commands and tiers), §4 `dock.js` row, C5, C7 and the §7 drawer and closed-panel rows with references |
| R6-2 | C6-1: §3.6's "its announce reloads the iframe with the new id" described a removed element; AC-38 `redock_reloads` was ambiguous (held element vs current one) | §3.6 re-dock text removed (now D11 re-docking, T12 → T6); AC-38 DOM-read rule (every iframe read is a fresh query of the panel DOM); `redock_reloads` asserts exactly one iframe carrying the new id; `stop_placeholder` asserts no iframe in the panel DOM |
| R6-3 | C6-1: tests | C5: one bun test per table row, invariants checked after each, plus sequences: re-dock (`close(v1)` then `announce(v2)` → one new iframe with `viewer=v2`, and a later `plr:gone` honoured again), C5-2, and reopen |
| R6-4 | C6-2 (MINOR): AC-38 key order unstated; `stop_placeholder` preceded keys that need a live viewer | AC-38 execution order: `reconnect_after_reload`, `drawer_reconnect`, `stop_placeholder`, `redock_reloads`, `late_iframe`, `many_reloads`; bullets reordered to match; C7 names the order |
| R6-5 | this log and the frontmatter `adversarial_review` entry | frontmatter; Revision 2 B-2, Revision 3 R3-3, Revision 4 R4-1 and Revision 5 R5-2/R5-4 annotated as superseded |

**Consistency fixes made while applying** (whole-spec check of every panel, iframe,
`announce`, `close`, `plr:gone` and `query` reference):
- **Reopen no longer creates an iframe.** Revision 2 had reopen create an iframe with no
  `src`; the table (T4, I1) attaches an iframe-less panel, which is what the task's "src only
  from the answering announce" needs and removes the only `src`-less iframe from the design.
  AC-38 `late_iframe` now observes the panel subtree: no iframe between the reopen and the
  answering `announce`, and the first inserted iframe already carries the `src`. AC-39(e)
  stays sensitive (with `query` dropped no iframe ever appears).
- **Tier crossing keeps the `src` (C3-3) was missing.** R3-3 had landed it in "Closed panel",
  and Revision 5's text no longer said it. Now T10, T15, T21, with a 1600 px crossing defined
  as sizing only (not a lifecycle event).
- **`open-lost` removes the iframe** (T14). The page had already given up, so this changes no
  recovery path (close/reopen, or `dock()` again), makes I1 hold in every state, and means no
  stale `plr:gone` can arrive from an element the panel no longer shows.
- **`praxis:toggle-deck-panel` while open** had no defined meaning; it is now close panel
  (T7, T17, T22), matching its name.
- **`stop()` is idempotent** (D11 Kernel; C3; new AC-31 bullet). Under the stated AC-38 order
  `redock_reloads` runs a `dock()` after the user's own `stop()`; a second `stop()` now posts
  no second `close` and raises nothing.
- **AC-38 `drawer_reconnect` returns to 1440×900.** It previously left K1 in the 1152 drawer
  tier, where `late_iframe`'s "closes the deck panel's tab" has no tab to close.
- **D12 calls only in `open-connected`.** Follow, Click and presets had no rule for a panel
  without an iframe; they now act only on the iframe in the panel DOM in `open-connected`,
  and the held preset is re-applied after every iframe load, since the `src` always carries
  `view=top` (a reload otherwise silently reset the user's preset).
- AC-36 `drawer_dismiss_reopen` and `tier_up_rehomes` name their table rows; §7 gains a row
  for the piecemeal-edit risk; C5's size estimate is raised to ~420 LOC and it also closes the
  unit half of AC-38.
- References list the round 3 to round 6 audits.

## Revision 7 (260929)

Round 7 (`.praxia/docs/audits/260929_notebook-display-round7-challenger.md`, audit
`260929_notebook-display-design_spec-challenge_r7`) closed C6-1 and C6-2 and found the
deck-panel state machine sound. It raised 2 MAJOR findings against the user's new preemption
rule (260929), 6 MINOR and 1 SUGGESTION. All were applied as the orchestrator ruled. Existing
AC, task, state-table row and invariant numbers are unchanged; Revision 7 appends AC-42 and
rows T23–T27, and splits scenario K1 into units K1a and K1b.

| Amendment | Finding | Landed |
|---|---|---|
| R7-1 | C7-1 (MAJOR): `--display-check` and `--dock-check` ran as one process that wrote results only at the end, under one 45 min job timeout | D16 path fix (the harness is `scripts/repl_smoke.py` at the repo root; `origin/main` line refs) and new D16 subsection "Preemption-safe harness design" (the unit table D1, D1-dark, D2, D3, D4, K1a, K1b, K2, N-d with budgets; `--scenario` one unit per subprocess; `result.<id>.json` plus a stamp with input and result sha256; driver resume; aggregate with `reused`; unchanged pass rule; CI policy: no reuse across workflow runs, one step per unit with step-level timeout, `--aggregate-only`, `if: always()` upload, job timeout as backstop); gate shorthand [DISPLAY]/[DOCK]; AC-7, AC-21, AC-24, AC-26, AC-34, AC-35, AC-36, AC-37, AC-38 unit headers; AC-39 (a), (b), (d), (e) each running only its unit; AC-40 pointer; new AC-42; §4 `repl_smoke.py` and `repl.yml` rows, two new test-file rows; A7, B10, C7 and the §6 table; §7 two new rows |
| R7-2 | C7-2 (MAJOR): spikes S1–S4 had no unit, resume or chunk design | D17 "Units, resume and chunking" (unit table per spike; S3 and S4 declared single bounded units at 10 min; `units/<name>.json` plus stamp; per-unit subprocess and timeout; `--resume`; outcomes over the full unit set; sidecar pre-registers the design; the note records reuse); §4 spike row; AC-1 "Units" bullet, referenced by AC-2, AC-3, AC-29; A1, A2, A3, C1 |
| R7-3 | C7-3 (MINOR): a stopped viewer stayed subscribed | D11 Kernel `stop` (unsubscribes after `close`), re-docking note; §4 `viewer3d.py` row; C3; AC-31 "Stopped viewer leaves the channel" |
| R7-4 | C7-4 (MINOR): T4 and §3.6 assumed the split | T4 ("in the current tier's home"); §3.6 opening sentence |
| R7-5 | C7-5 (MINOR): K2 had no order or page count | AC-36 "Execution order and page count" (one page, one kernel, one `dock()`, nine steps) |
| R7-6 | C7-6 (MINOR): a kernel restart left a frozen deck | D11: `viewerPanel` and "the viewer's kernel", the kernel-restart event (`sessionContext`), rows T23–T26, I2, I4, I6, the protocol `close` row; §3.6 States; §2 non-goal (unknown-kernel gap); §4 `dock.js` row; C5 sequence case; AC-38 `restart_placeholder`; §7 row |
| R7-7 | C7-7 (MINOR): preset re-apply untested and possibly before the first `scene` | D12 (re-apply once `resources()` is non-empty, 10 s bound); §4 `dock.js` row; C5 case; AC-38 `preset_survives_reload` |
| R7-8 | C7-8 (MINOR): AC-39 exit codes were unregistered findings | D17 "AC-39 sensitivity runs are pre-registered too" (driver, per-sprint entry scripts and sidecars, one outcome per negative, unit design); §4 row; AC-39 preamble; A7, B10, C7 |
| R7-9 | C7-9 (SUGGESTION): all three | D11 event definitions (a tier crossing's DOM move is not an iframe reload); T11 narrowed to a new id plus T27 (same id: no-op); I2; C5 case; AC-38 `redock_live`, placed after `drawer_reconnect` and before `stop_placeholder` in the stated order |
| R7-10 | this log and the frontmatter `adversarial_review` entry | frontmatter; References (round 7 audit, the user's rule, `origin/main` line refs) |

**Consistency fixes made while applying:**
- AC-38's stated order is now `reconnect_after_reload`, `preset_survives_reload`,
  `drawer_reconnect`, `redock_live`, `stop_placeholder`, `redock_reloads`, `late_iframe`,
  `many_reloads`, `restart_placeholder`. `redock_live` needs a live viewer, so it precedes
  `stop_placeholder`, which still runs immediately before `redock_reloads`.
  `restart_placeholder` destroys the kernel, so it runs last; its viewer's kernel is known,
  because `late_iframe`'s `dock()` announced during an executing cell (`viewerPanel`).
- K1 is split because a single unit carrying AC-34, AC-35, AC-37 and AC-38 had no bounded
  budget. K1a and K1b each boot and `dock()` themselves. AC-24's D3 now executes its own
  drawing cells, rather than inheriting D2's page, so each display unit is independent.
- The kernel-restart event needs to know which kernel owns the viewer, and the protocol
  carries no kernel identity (D7 rejects adding one). `viewerPanel` derives it from the panel
  executing when the `announce` arrives, with a single-kernel fallback. The remaining
  unknown case is stated, not hidden.
- A failing unit is never reused, so a flaky failure is retried on resume. This is a
  scheduling rule and does not change the pass rule.
- The harness path was already correct everywhere (`scripts/repl_smoke.py`); only the line
  references were base-relative. D16 and References now give both the base and the
  `origin/main` lines.
- C5 tests T1–T27; §4 `dock.js` row and the §7 piecemeal row name T1–T27.
- Sizes raised: A7 ~420, B10 ~340, C5 ~480, C7 ~450 LOC. The ACs now number 42 (R4-4's
  parser note counted 41).

## Revision 8 (260929)

Round 8 (`.praxia/docs/audits/260929_notebook-display-round8-challenger.md`, audit
`260929_notebook-display-design_spec-challenge_r8`) closed C7-1 through C7-9, found the
T23–T27 rows and the AC-38 order sound, and found the resume design sound apart from 2 MAJOR
and 5 MINOR holes. The orchestrator verified C8-1's premise
(`processLauncher.js:108-111`, `detached: process.platform !== "win32"`) and ruled: apply
everything; for C8-2, a self-enforced watchdog inside `--scenario`. AC, task, state-table row
and invariant numbers are unchanged; Revision 8 adds no AC and no task. It adds one module,
`scripts/unit_runner.py`, and its test, `web-repl/tests/test_unit_runner.py`, both owned by
A1.

| Amendment | Finding | Landed |
|---|---|---|
| R8-1 | C8-1 (MAJOR): a process-group kill does not reach Playwright's detached Chromium, and a CI step timeout orphans it | D16 "Shared unit runner" (`scripts/unit_runner.py`: `kill_tree` descendant walk with `SIGSTOP`, `PRAXIS_UNIT_TOKEN` environ sweep, `SIGTERM`/`SIGKILL` per pid and process group; `run_unit`; `Watchdog`; `--reap`) and "One subprocess per unit"; D16 CI layout (`if: always()` reap step, backstop note); D17 "Chunked timeouts" and the nd driver; §4 new rows `unit_runner.py` and `test_unit_runner.py`, spike, nd, `repl_smoke.py` and `repl.yml` rows; AC-39 preamble; AC-42 "Runner" cases and reap-step workflow check; A1 (owns the module, tests first), A2, A3, A7, B10, C1, C7 and the §6 table (A2, A3, A7, C1 depend on A1); sprint A order; §7 new row; References |
| R8-2 | C8-2 (MAJOR): a direct `--scenario` run had no timeout | D16 "`--scenario` is self-bounded" (watchdog at the budget, timeout marker, exit 124, no stamp, stamp/watchdog lock; bound ordering budget < budget + 60 s < budget + 2 min) and "Local runs"; aggregate `timed_out` from the marker; §4 `repl_smoke.py` and resume-test rows; AC-42 `--scenario` watchdog case; A7, B10, C7; §7 row |
| R8-3 | C8-3 (MINOR): a timed-out re-run left the old stamp; skip checked neither `exit` nor key presence | D16 "Per-unit output" (a unit clears its own files first; stamp `exit` defined), "Listed keys", "Resume" (skip needs `exit == 0` and every listed key present and holding); D17 "Per-unit output" and "`--resume`"; nd driver resume; §4 rows; AC-42 skip-rule and cleared-stamp cases; A7; §7 row |
| R8-4 | C8-4 (MINOR): the CI aggregate omitted the hashed `--base-path`, and deleted on mismatch | D16 "Aggregate" (`missing`, `stale` with mismatched input names), new "`--aggregate-only`" bullet (never deletes; same hashed arguments; starts no unit subprocess), CI aggregate step with `--base-path /praxis/`; §4 `repl.yml` and workflow-test rows; AC-42 aggregate and workflow cases; A7, B10, C7; §7 row |
| R8-5 | C8-5 (MINOR): AC-39 negatives wrote into the default out dir | D16 "Per-unit output" (non-default `--serve-dir` or `--neg` requires `--out-dir`, else exit 2) and the negatives bullet; D17 nd driver (`.../<negative>/dist/` and `.../<negative>/out/`, driver records under `outputs/nd_sensitivity/sprint_<x>/`); §4 nd row; AC-39 preamble and (a), (b), (d), (e) commands; AC-42 exit-2 case; A7, B10, C7; §7 row |
| R8-6 | C8-6 (MINOR): Playwright version and `uv.lock` were not hashed | D16 `driver` input (`unit_runner.driver_input`); D17 spike and nd input sets; §4 rows; AC-1 Units bullet; AC-42 `driver` cases (Playwright version, `uv.lock`) in both test files; §7 row |
| R8-7 | C8-7 (MINOR): a spike unit whose probe raised had undefined completeness | D17 "Completeness" (artifact plus stamp is complete; a raised probe is an `error` finding that counts toward `[outcomes]` and is never reused; only a timeout or stampless crash is incomplete), "`--resume`", "Outcomes over the full unit set" and the sidecar pre-registration bullet; nd paragraph; §4 spike row; AC-1 Units bullet (sidecar states it, note lists `error` units); A1, A3, C1; §7 row |
| R8-8 | this log and the frontmatter `adversarial_review` entry | frontmatter; References (round 8 audit, `processLauncher.js`) |

**Consistency fixes made while applying:**
- The AC-39 mutated dists moved from `/tmp/claude-1000/nd-neg/<negative>/` to
  `.../<negative>/dist/`, with the out dir beside it at `.../<negative>/out/`. An out dir
  inside the served dist would have changed the negative's own `dist` hash as it wrote.
- AC-42's "`--aggregate-only` starts no subprocess" conflicted with the hashed `chrome` input,
  which needs `chrome --version`. It now reads "starts no unit subprocess"; the version probe
  is the only process it runs.
- The driver's timeout is budget + 60 s (was the budget), so the unit's own watchdog, not the
  driver's kill, ends a hung unit in the normal case and the timeout marker is written.
  AC-42's fake-runner case changed to match.
- The driver never deletes on a stamp mismatch any more; recomputing a unit clears its files
  (the unit does it itself, and the driver does it just before launching). Only
  `--aggregate-only` is guaranteed to delete nothing.
- A harness timeout (exit 124) is nonzero but names no key, so it never passes an AC-39
  negative's outcome; stated in D17 and the AC-39 preamble.
- `unit_runner.py` and the `driver` input are hashed into the spike and nd stamps, so a
  change to the kill or write logic recomputes their units.
- Sprint A order: A2 and A3 now start after A1 commits `unit_runner.py`, not in parallel from
  the start; A7 and C1 list A1 explicitly.
- `repl.yml` §4 row gains A1 (wiring `test_unit_runner.py`); the reap step's 1 minute sits
  inside the job backstop's 45-minute allowance, so 60 / 92 / 137 are unchanged.
- Sizes: A1 ~250 → ~370 LOC. The ACs still number 42; the tasks still number 24.

## Revision 9 (260929)

Round 9 (`.praxia/docs/audits/260929_notebook-display-round9-challenger.md`, audit
`260929_notebook-display-design_spec-challenge_r9`) closed C8-1 through C8-7 and found the
runner design structurally sound, with 1 MAJOR and 5 MINOR hardening findings. The
orchestrator ruled:
- C9-1: the browser and Playwright close inside the watchdog-bounded region before the stamp,
  and only `os._exit(stamp.exit)` follows it. A driver timeout over a valid stamp defers to
  the stamp, and the timeout is logged.
- C9-3: pidfd where available, with a starttime fallback.
- C9-5: the real-Chromium case runs in CI only, never locally.
- C9-6: reword to "no stamp" **and** delete the result under the lock.
- C9-2 and C9-4: as stated.

AC, task, state-table row and invariant numbers are unchanged. Revision 9 adds no AC, no
task and no file. It adds one runner function (`ensure_token`), one `Watchdog` method
(`commit`) and one hashed input (`runner`).

| Amendment | Finding | Landed |
|---|---|---|
| R9-1 | C9-1 (MAJOR): the watchdog disarmed at the stamp, leaving `browser.close()`, `sync_playwright().__exit__` and driver shutdown unbounded | D16 "Shared unit runner" (new "Bounded teardown" bullet: result, teardown, residual `kill_tree`, flush, `Watchdog.commit`, then only `os._exit(stamp.exit)`), "`--scenario` is self-bounded" (commit after teardown; a driver timeout over a valid stamp defers to the stamp and is logged), "Per-unit output", "Resume", "Aggregate" (`timed_out` excludes a timeout over a valid stamp), "Local runs"; D17 "Per-unit output" and "Chunked timeouts"; nd paragraph (`harness_exit` from the stamp; stamp governs over the timeout); §4 `unit_runner.py`, `test_unit_runner.py`, spike, `repl_smoke.py` and resume-test rows; AC-42 runner case "hang after the stamp" and resume cases "hang in teardown" and "driver timeout over a valid stamp"; A1, A7; §7 preemption row |
| R9-2 | C9-2 (MINOR): `kill_tree` and `--reap` hardening | D16 `kill_tree` (walk plus sweep to a fixpoint, freezing each find; exact NUL-delimited entry; `PermissionError`, `ProcessLookupError`, `FileNotFoundError` and empty environ skipped; a second fixpoint after the grace; `SIGCONT` in a `finally`), `--reap` (`kill_tree` per token; refuses without `CI` or `--force`), CI reap step (no `--force`), "Local runs"; §4 `unit_runner.py`, `test_unit_runner.py` and `repl.yml` rows; AC-42 fixpoint, unreadable-environ, `SIGCONT` and `--reap` refusal cases and the workflow check; A1, A7; §7 runner row |
| R9-3 | C9-3 (MINOR): pid reuse before `SIGKILL` | D16 `kill_tree` step 2 (pidfd via `os.pidfd_open` / `signal.pidfd_send_signal`, else a `/proc/<pid>/stat` starttime re-check; group signals only with a verified live member); §4 rows; AC-42 pid-reuse case; A1; §7 runner row |
| R9-4 | C9-4 (MINOR): a token set after exec is invisible in `/proc/self/environ`, the watchdog was not armed first, and the inner bound was untested | D16 `run_unit` (token at exec), new `ensure_token` (re-exec), `Watchdog` armed as the first act, "`--scenario` is self-bounded", "Per-unit output"; D17 "Per-unit output"; §4 `unit_runner.py`, spike, `repl_smoke.py` and resume-test rows; AC-42 `ensure_token` case and "Watchdog armed with the table budget" case; A1, A7; §7 preemption and runner rows |
| R9-5 | C9-5 (MINOR): no gate ran a real Chromium | §4 `test_unit_runner.py` row (one real-Chromium case, wired in the REPL job with Playwright's Chromium); AC-42 "Real Chromium" case (`skipif` unless `CI`; fails rather than skips in CI when Chromium is missing; never run locally); D16 "Local runs"; A1 (local gate skips it, CI closes it); §7 runner row |
| R9-6 | C9-6 (MINOR): `unit_runner.py` was not hashed into harness stamps, and "no result" was not guaranteed | D16 "Inputs hashed" (new `runner` input), `Watchdog` expiry and "`--scenario` is self-bounded" (result deleted under the lock), "Resume"; D17 "Chunked timeouts" (artifact deleted under the lock); nd paragraph (harness timeout: no stamp, no result); §4 `repl_smoke.py` and resume-test rows; AC-42 `--scenario` watchdog case (no stamp; the pre-written result deleted), skip-rule `runner` case, timed-out-unit case; A7; §7 resume row |
| R9-7 | this log and the frontmatter `adversarial_review` entry | frontmatter; References (round 9 audit) |

**Consistency fixes made while applying:**
- The watchdog now owns the stamp lock through `Watchdog.commit`, so the harness and the spike
  units share one lock implementation rather than each writing its own.
- A unit's order is stated once: `ensure_token`, arm the watchdog, clear its own files, work,
  write the result or artifact, teardown, flush, commit the stamp, `os._exit`. D16 "Per-unit
  output", D17 "Per-unit output", the §4 rows and A1/A7 previously said "first act is to
  delete its own files", which conflicted with arming the watchdog first. They now say the
  deletion comes right after arming.
- stdout, stderr and logging are flushed before the stamp commit, because `os._exit` does not
  flush and a flush can block on a full pipe; the flush therefore sits inside the bounded
  region.
- `kill_tree`'s pre-kill fixpoint alone missed a fork made in the grace window by a `SIGTERM`
  handler. Step 5 repeats the fixpoint before `SIGKILL`.
- A `SIGKILL` of the caller skips the `finally`. The spec now says so, and names `--reap` (in
  CI) and `--reap --force` (locally) as the recovery for processes left stopped.
- `timed_out` in the aggregate, the Resume rule and the AC-39 `harness_exit` all now read the
  stamp first, so a driver timeout over a valid stamp is judged the same way in the harness
  driver, the spike drivers and the nd driver.
- The AC-42 `--reap` case now sets `CI=1` or passes `--force`; without either, the Revision 8
  case would have hit the new refusal.
- A1 size ~370 → ~450 LOC. The ACs still number 42; the tasks still number 24.

## Revision 10 (260929)

After round 10 converged, `origin/main` a176bac7 (PR #184 "plr-1.0-bump") moved the PyLabRobot
pin from 0.2.2 (`dd79c4c89`) to 1.0.0b1 (`786ac2c4e`). A recon re-checked every PLR-dependent
claim against the built 1.0.0b1 wheel:
`.praxia/docs/research/260929_notebook-display-plr10-premises.md` (exploratory, not
pre-registered; the AC-15/16 test files re-verify it under their own gates). The orchestrator
independently re-verified the two BLOCKER facts (a failed aspirate rolls every channel back;
the E13 retry and E15's second aspirate do not raise) and the synthetic residue setup now used
by E13, and issued one binding ruling (C2/D11, below). Revision 10 also makes D16 say what the
merged A1a `scripts/unit_runner.py` does. AC, task, state-table row and invariant numbers are
unchanged; Revision 10 adds no AC and no task. It adds one file,
`scripts/repl_smoke_units.py` (A7; *dropped again by Revision 11, R11-3*), and removes the vendored Python package, the ADR addendum
and one contract entry.

| Amendment | Finding (the PLR 1.0 recon unless noted) | Landed |
|---|---|---|
| R10-1 | BLOCKER-1: E13 and E15 no longer raise at the pin | AC-15 E13 replaced by a synthetic residue case from direct tracker use (setup verified by the orchestrator), E15 by a synthetic tip-side residue case (to be verified by B5, with a stop-and-report rule); E14 kept and clarified (a failure inside the queue loop, not E7's pre-loop check); AC-17; B5, B6, B8; §7 new "pin bump changes an AC case" row; Revision 2 B-8 and Revision 3 R3-1 annotated |
| R10-2 | BLOCKER-2: the "pending residue" premise is false for aspirate/dispense | D8 step 4 "Pending residue" and "Panel drawing" rewritten (aspirate/dispense roll back; pick-up/drop and direct tracker use still leave residue; the committed-numbers rule is a defence for those paths; "Nothing was aspirated" ordering to be verified by B6); AC-16 forces pending ≠ committed by direct tracker use; §7 residue row; OQ-6 reworded for the tip ops; §2 G5 unchanged |
| R10-3 | BLOCKER-3: the R21 grep exits 0 on `main` (`transport.py:10,11,26`, pre-existing) | D7 new "R21 check" (strip the RST ` ``praxis_repl`` ` form, then grep; exit 1 exactly), used by AC-18, AC-31, B7, C3, C7 and the §7 `praxis_repl` row. Chosen over "exempt comment lines" because `:10` and `:11` are docstring lines, not `#` comments |
| R10-4 | MAJOR-1: tip-spot messages name the spot; well trackers carry deck names | D8 "What PLR's message omits" and owner rule (d) (wells resolve; bare tip-spot names looked up); AC-15 E5, E7, E8 notes; no message text asserted beyond `str(exc)` |
| R10-5 | MAJOR-2, MAJOR-3 and the orchestrator's binding ruling: the pin ships `pylabrobot/visualizer3D`, the REPL wheel contains it, `websockets` is a vendored wheel | D11 rewritten: import `pylabrobot.visualizer3D`, subclass its `Viewer3D`, rebind its `PACKAGE_ROOT` (load-bearing: the stock root holds 63 `.glb` files); only `static/` vendored, from the submodule at the pin; `--check` on bytes and recorded commit. GATE X re-derived (part 1 overrides, part 2 no PLR Python in the overlay, part 3 static bytes in the manifest). D1 S4 row; D17 S4 unit and inputs; §4 rows (vendor script, contract, `viewer3d.py`, S4 spike, `build_repl.py`, test rows; the `plr_visualizer3d/**` and ADR rows deleted); AC-29, AC-30, AC-31 (GATE X parts 1-2, load-bearing rebind with a positive control), AC-33, AC-41; C1 (~160), C2 (~200, static only), C3 (adds the `pylabrobot.visualizer3D.server` contract entry; no longer depends on C2), C6, C7 (no PLR checkout step); §6 table; §7 rows; OQ-7 resolved; Revision 1 A-6 and Revision 2 B-4 annotated |
| R10-6 | MAJOR-4: rollback fires callbacks; registration appends; pick-up fires `did_unassign` ×8 | D7 drawn-state digest filter (callbacks mark dirty; settle at `post_run_cell` and before each render; bump only on a changed digest) and idempotency via `_subscribed`; AC-18 "Rollback does not bump" and "Settle before render"; §4 `stale.py` row; B7 (~260); §7 new row. **Deviation from the brief, stated:** the brief asked to filter on committed state; that contradicts D7's pending-only bump (Revision 2 B-8, AC-18), so the filter keys on the drawn state, which agrees with the committed filter in the rollback case |
| R10-7 | MAJOR-6: deprecated fixture names; `num_rails`; `fixture.js`; `EmbeddedTipRack`; `serialize()` shape; `_as_in_kernel` | §4 new `make_fixture.py`/`fixture.js` row; B2 (fixture port first, `_repr_` grep, ~370 LOC); §3.2 rail/track note and model-string note; AC-11 `num_tracks`; D2 (`EmbeddedTipRack` resolves by MRO, no type-name dispatch); D5 worked check (7.2 mm tips, thresholds unchanged) |
| R10-8 | MAJOR-7: `repl_smoke.py` needs the submodule at import | D16 "Import-time submodule dependency" (pure plumbing in `repl_smoke_units.py`; spike drivers lazy-load in `--unit` only; the harness needs the submodule; CI authoritative), "Local runs", `harness` input covers both files; D17 inputs; §4 new `repl_smoke_units.py` row, `repl_smoke.py`, spike, resume-test and `test_unit_runner.py` rows; A1, A2, A3, A7 notes; AC-42 check that the resume test never loads `repl_smoke.py`; §7 new row. *(Superseded by Revision 11 R11-3: `NOTEBOOK_EXPECTED` is made lazy in A1 instead, `repl_smoke_units.py` and the never-load rules are dropped, and the heading is now "Import-time submodule dependency, removed in A1".)* |
| R10-9 | MAJOR-8: legacy/non-shim homes; the contract's no-shim test | D8 "Classes the code checks"; sprint B "Import contract"; §4 contract, `context.py` and test rows; AC-41 |
| R10-10 | MAJOR-9, MAJOR-10: E2/E3 setups; E7's site | AC-15 E2 (tip preset to 400), E3 (source preset to 500), E7 (LH:727, pre-loop, only `tip_spots`/`use_channels` bound; D8 step 2 note on missing locals) |
| R10-11 | MAJOR-5 and the MINOR anchors | Every PLR anchor re-anchored to the pin (inputs note: `LH` = the legacy path; D5, D7, D8, D9, D13, D16, §4, References); base-commit numbers cited "on origin/main a176bac7" (`repl_smoke.py`, `praxis_bootstrap.py`, `build_repl.py`, `repl.yml`); the wheel-size risk (1.26 → 10.2 MB) added to §7; D9 notes the pin's `pylabrobot.events` bus and why D9 keeps shadowing |
| R10-12 | A1a implementation (orchestrator note in the recon): `SIGSTOP` then `SIGTERM` could not let a handler fork in the grace window, contradicting AC-42's fixpoint case | D16 `kill_tree` steps 4-5 (`SIGCONT` right after `SIGTERM`; re-freeze, second fixpoint, then `SIGKILL`); `Watchdog(budget_s, on_expire=None)`, `disarm()`, `commit` raising on a second call, a raising `on_expire` still kills and exits; `run_unit(..., grace_s=5)` and `killed` = "`kill_tree` ran"; `dist_hash` and `driver_input` contracts; `emit_line`, `read_proc_stat`, `reap()`; `--reap --token`; keyword-only seams; the Chromium-token open risk and its fallback (with the `detached`/session caveat); §4 `unit_runner.py` and `test_unit_runner.py` rows; AC-42 Revision 10 contract cases and C10-1 positive control; A1 note; §7 runner row |
| R10-13 | this log, the frontmatter `adversarial_review` entry and the Convergence section | frontmatter; inputs; References (the recon, round 10) |

**Consistency fixes made while applying:**
- C3 no longer depends on C2: `viewer3d.py` imports the pin's package, and C2 now vendors only
  the static page, which C4 (tag positions) and C6 still need.
- The CI PLR checkout step (C7) is gone: `--check` reads the submodule, which every job that
  runs `repl_smoke.py` already has initialised (its import-time `version.txt` read).
  *(Evidence replaced by Revision 11: A1 makes that read lazy; the job's `submodules:
  recursive` checkout and its submodule assertion, `repl.yml:56-61`, are the evidence now.)*
- C1's probe no longer stages files; it constructs a throwaway `DockedViewer3D` prototype over
  the imported package, since C3 has not landed when C1 runs.
- AC-31's `.glb` check can no longer place a file under the stock root (the installed PLR
  package); it seeds `PACKAGE_ROOT` with a temporary directory and adds a positive control, so
  the check cannot pass vacuously.
- The AC-15 preamble states that no case asserts PLR's message text beyond what it names, and
  E-96's message text is no longer asserted (it was read at 0.2.2).
- Sizes: B2 ~320 → ~370, B7 ~220 → ~260, C1 ~180 → ~160, C2 ~300 → ~200 LOC. The ACs still
  number 42; the tasks still number 24.

## Revision 11 (260929)

Round 11 (`.praxia/docs/audits/260929_notebook-display-round11-challenger.md`, audit
`260929_notebook-display-design_spec-challenge_r11`) checked Revision 10 at `474c9b36`. It
closed R10-1, R10-3, R10-4, R10-5, R10-6, R10-9..R10-13, left R10-2, R10-7 and R10-8 open
(as C11-2, C11-1, C11-3), and raised 1 BLOCKER, 3 MAJOR and 11 MINOR findings. It confirmed
the D7 drawn-state digest filter, the R21 pipeline on the three real hits, the C2/D11 ruling
and `kill_tree` steps 4-5. The orchestrator verified C11-1 by running both greps on the
1.0.0b1 wheel copy (15 / 0 hits, 0 real hooks), confirmed C11-2 against its own E9 probe, and
ruled **(a)** on C11-3: make `NOTEBOOK_EXPECTED` lazy and drop `repl_smoke_units.py`
everywhere. Every other finding was adopted as stated, C11-13 as a guarded first-construction
helper. AC, task, state-table row and invariant numbers are unchanged; Revision 11 adds no AC
and no task. It adds one test file (`web-repl/tests/test_repl_smoke_import.py`, A1), lists
two committed A1b-1 files in section 4 (`test_s1_spike_driver.py`, `s1_cell_states.ipynb`),
and removes one planned file (`scripts/repl_smoke_units.py`). Every changed claim was re-read
at its anchor: the PLR 1.0.0b1 wheel copy, and `scripts/repl_smoke.py`,
`scripts/unit_runner.py`, the S1 probe and sidecar, `test_s1_spike_driver.py` and `repl.yml`
on the sprint A branch (`feat/notebook-display-sprint-a`).

| Amendment | Finding | Landed |
|---|---|---|
| R11-1 | C11-1 (BLOCKER): B2's `_repr_` gate, the BRE `'_repr_html_\|_repr_[a-z]*_'`, matches every `__repr__` (15 hits at the pin), so it could never pass | D2 (the ERE `grep -rnE '(^\|[^_])_repr_[a-z]+_' external/pylabrobot/pylabrobot --include='*.py'`, exit 1; the 0.2.2 "0 hits" sentence no longer attributes that record to the BRE); B2 text and gate |
| R11-2 | C11-2 (MAJOR): AC-16's forced residue sat on the failing op's own wells, which the op's rollback resets (LH:1284-1289, `volume_tracker.py:160`), so the committed-drawing check was vacuous | AC-16 (residue on assay H12, outside the A1:H1 op: `set_volume(100)` then uncommitted `remove_liquid(40)`; render-time precondition 100 / 60; radius from committed 100); D8 "Panel drawing" (direct-tracker residue survives a failed op only outside it; the committed rule is visible on those wells); B6; §7 residue row |
| R11-3 | C11-3 (MAJOR), ruling (a): the S1 driver loads `repl_smoke.py` in its driver (`build_env`, `:267`), contradicting "never in its driver", and its sidecar's `hashed_inputs` omit it | D16 "Import-time submodule dependency, removed in A1" (`notebook_expected()` at the four use sites; everything may load `repl_smoke.py`; browser runs still need a dist at the pin); D16 "Local runs", `harness` input, consumer-load note; D17 spike inputs and nd inputs; D11 `--check` evidence re-pointed to `repl.yml:56-61`; §4: `repl_smoke_units.py` row deleted, `repl_smoke.py` row (A1 change, pure functions in the module), resume-test, `test_unit_runner.py`, spike and S1 rows; new rows `test_s1_spike_driver.py`, `s1_cell_states.ipynb`, `test_repl_smoke_import.py`; A1 (lazy change tests-first; S1 probe and sidecar `harness` amendment in one commit before the first run, recorded in the sidecar and the S1 research note; gate and size), A2, A3 (text and dependency), A7 (no second module), C1; sprint A order; §6 table; §7 row rewritten and a new pre-registration-gap row; R10-8 and the Revision 10 intro annotated |
| R11-4 | C11-4 (MAJOR): GATE X part 2 had no check; a `server.Viewer3D._mark_scene_dirty = ...` assignment passed parts 1-3 | AC-31 "GATE X part 2, state snapshot" (`vars(Viewer3D)` and the `server` module dict by identity, before load and after construct/start/stop, only `PACKAGE_ROOT` differs; a negative control; stock-rebind stop rule, to be verified by C3); D11 GATE X part 2 cites it; C3; §7 `PACKAGE_ROOT` row |
| R11-5 | C11-5 (MINOR): E14's setup unwritten; "committed tip state" named no accessor | AC-15 E14 recipe (D1 on channel 3; A2:H2 raises at LH:758 leaving channels 0-2 pending; precondition `has_tip` True, `get_tip()` raises; A3:C3 on 0-2 raises `"Channel has tip"` with no tracker frame → `None`); D8 step 4 (committed = `TipTracker.get_tip()` succeeding, never `has_tip`, never `TipSpot.get_tip()`); B5 |
| R11-6 | C11-6 (MINOR): E15 and the "nothing aspirated" ordering were verify-else-stop, though source confirms both; E2's note was false | AC-15 E15 (confirmatory assert, with the source reading `volume_tracker.py:91-97, 114-119` and LH:1268-1273); D8 step 4 and "Panel drawing" (ordering read from LH:1269-1274, :1470-1475; B6's spy is confirmatory); AC-15 E2 note corrected (dispense queues the well's `add_liquid` before the tip's `remove_liquid`, LH:1472-1474); AC-17; B5, B6; §7 pin-bump row |
| R11-7 | C11-7 (MINOR): D7 overstated "a failed aspirate bumps nothing"; S3-D settling unstated; AC-18's `set_volume` value unstated; "tip present as drawn" named no accessor | D7 (qualified: a pre-op residue on an op resource is erased by the rollback and bumps, correctly; the S3-D announcer settles first; digest uses `spot.tip is not None`); AC-18 (`set_volume(v)`, `v` ≠ 150); B7 |
| R11-8 | C11-8 (MINOR): the R21 pipeline's exit was the last grep's, so a first-grep error read as a pass | D7 "R21 check" (`PIPESTATUS`: first 0 or 1, `sed` 0, last exactly 1; a Python form allowed under the same rule; the 3-hit behaviour on `main` kept); the "exit 1" wordings in D7, D11, AC-18 and AC-31 |
| R11-9 | C11-9 (MINOR): D16 drifted from `unit_runner.py` | D16 `ensure_token` (`sys.orig_argv`, `:509`), `Watchdog` signature (keyword-only `token`, `grace_s`, `exit_fn`, `kill_fn`; raises without a token, `:579-583`), `write_result` (C10-2, `:604-610`; bounded teardown step 1, D16 and D17 per-unit output), `kill_tree` step 5 (grace wait ends early, `:350-354`); §4 `unit_runner.py` and `test_unit_runner.py` rows; AC-42 (`Watchdog(1)` with a token; Revision 11 contract cases, to be verified by A1 against the merged suite); A1, A7 |
| R11-10 | C11-10 (MINOR): AC-42's "never loads" check matched its own literal; the exit-2 and `--aggregate-only` cases are CLI behaviour | AC-42 (the never-load check is dropped with `repl_smoke_units.py`; the resume test calls the pure functions behind the flags and asserts return codes and effects); §4 resume-test row; A7 |
| R11-11 | C11-11 (MINOR): `repl.yml` `paths:` lacked the spike and sensitivity scripts | §4 `repl.yml` row (A1: `scripts/spikes/**` replaces the single S1 path; A7: `scripts/negatives/**`; both lists); A1, A7; AC-42 workflow test checks both lists. `scripts/repl_smoke_units.py` needs no entry (dropped) |
| R11-12 | C11-12 (MINOR): anchor slips | D5 (`star_decks.py:225`, `STARLetDeck` `:209`; `hamilton_decks.py:811` is `_OLD_CONSTANTS`); D16 and References (`repl.yml` `:47`, `:68`; `NOTEBOOK_EXPECTED` `:1450` on the sprint A branch); D7 and §7 (`praxis_bootstrap.py:214, 266` on the sprint A branch); D8 step 2 (CI Python 3.12, `repl.yml:68`). "On origin/main a176bac7" numbers are kept distinct from sprint-branch numbers |
| R11-13 | C11-13 (MINOR): the `PACKAGE_ROOT` rebind trigger was ambiguous | D11 "Trigger" (`_ensure_package_root()`, guarded and idempotent, first statement of `DockedViewer3D.__init__`; import changes no PLR state) and Kernel `__init__`; AC-31 (import leaves the root unchanged; the test seeds after import, before the first construction; fresh load per test); C3; §7 row |
| R11-14 | C11-14 (MINOR): rule (a) read the docstring-deprecated `TipSpot.tracker` | D8 rule (a) (`tip_spot_tracker(spot)`; its create-and-cache side effect stated and accepted); D7 digest (`spot.tip`); §7 new v1-removal row; B5 |
| R11-15 | C11-15 (MINOR): rule (d) could resolve a tip's tracker name to a `Tip` | D8 rule (d) (a `Tip` match gives no owner; `tip_origin` mapping rejected, with the reason); rule (a) (a resting `Tip` is not an owner); B5 |
| R11-16 | this log, the frontmatter `adversarial_review` entry and the Convergence section | frontmatter; References (round 11 audit, sprint-branch anchors for `repl_smoke.py`, `unit_runner.py`, the S1 probe, `repl.yml`, and the pin's tip and tracker anchors) |

**Consistency fixes made while applying:**
- With `repl_smoke.py` import-safe, "`--display-check` needs the submodule" no longer holds
  for loading, `--resume` or `--aggregate-only`; D16 now says what does need it (a dist built
  at the pin, and `--notebook-check`'s expected version).
- A2, A3 and C1 load `repl_smoke.py` as S1 does, so they now also wait for A1's lazy change
  (A2 and A3 only; C1 runs after sprint A merged) and hash `harness`.
- The R21 gate's pass condition is the second line's exit, so every "exits 1 exactly"
  referring to the whole gate now reads "passes"; AC-41's R19 grep, a single command with no
  pipeline, still exits 1 exactly and is unchanged.
- Rule (a)'s `Tip` exclusion follows from R11-15: a resting tip's own `VolumeTracker` is in
  the deck subtree, and the same reasoning applies.
- Sizes: A1 ~450 → ~500, A7 ~420 → ~410 LOC. The ACs still number 42; the tasks still
  number 24.

## Convergence (260929; re-converged after Revision 11, round 12)

**Converged after 10 challenger rounds, re-opened by the PLR 1.0 pin bump, and converged again
after round 12.** Round 10 (`.praxia/docs/audits/260929_notebook-display-round10-challenger.md`)
found no BLOCKER and no MAJOR. The PLR 1.0 pin bump on `origin/main` (a176bac7) then invalidated
several PLR-dependent premises (`.praxia/docs/research/260929_notebook-display-plr10-premises.md`),
and Revision 10 applied them with the orchestrator's C2/D11 ruling and the A1a runner corrections.
Round 11 (`.praxia/docs/audits/260929_notebook-display-round11-challenger.md`) returned REVISE on
Revision 10, fixed as Revision 11 with the orchestrator's C11-3 ruling (a). Round 12
(`.praxia/docs/audits/260929_notebook-display-round12-challenger.md`, targeted) found no BLOCKER and
no MAJOR on Revision 11 (5 MINOR, 2 suggestions): **CONVERGED 260929**. The MINORs are sprint
notes below, not a Revision 12.

| Round | BLOCKER | MAJOR | MINOR | Fixed by |
|---|---|---|---|---|
| 1 | 2 | 13 | 14 | Revision 1 (A-1..A-20, after the defender) |
| 2 | 2 | 7 | 3 | Revision 2 (B-1..B-12, after the defender) |
| 3 | 0 | 2 | 2 | Revision 3 |
| 4 | 0 | 2 | 2 | Revision 4 |
| 5 | 0 | 1 | 3 | Revision 5 |
| 6 | 0 | 1 | 1 | Revision 6 (deck panel state machine) |
| 7 | 0 | 2 | 6 | Revision 7 (preemption-safe harness and spikes, per the user's new rule of 260929) |
| 8 | 0 | 2 | 5 | Revision 8 (shared unit runner) |
| 9 | 0 | 1 | 5 | Revision 9 (bounded teardown) |
| 10 | 0 | 0 | 4 | none: recorded below for the sprint |
| (pin bump) | 3 | 10 | anchors | Revision 10 (PLR 1.0 recon, not a challenger round) |
| 11 | 1 | 3 | 11 | Revision 11 (REVISE; round 11 fixes, C11-3 ruling (a)) |
| 12 | 0 | 0 | 5 | none: recorded below for the sprint (CONVERGED) |

**For the implementing sprint (non-blocking MINORs, round 10). Fold them into A1's tests-first work:**
- **C10-1:** the real-Chromium `test_unit_runner.py` case gets a positive control. Before the
  timeout, a live Chromium process (by `comm`/`exe`) carries the token and sits in a pgid different
  from the child's. Only then assert that none survive. *(Folded into AC-42 by Revision 10; a
  failing control is a finding, D16 "Open risk: Chromium and the token".)*
- **C10-2:** `Watchdog.write_result` does the result/artifact write under the lock, checking
  `fired`, so "no result" after a timeout is guaranteed. *(Implemented, `unit_runner.py:604-610`;
  stated in D16 by Revision 11, C11-9.)*
- **C10-3:** the watchdog's timeout line is written with a non-blocking `os.write(1, ...)`
  (ignoring `EAGAIN`), or after `kill_tree`, and the marker file is the authoritative record.
- **C10-4:** `ensure_token` re-execs with `sys.orig_argv`, so interpreter flags are kept.
  *(Implemented, `unit_runner.py:509`; stated in D16 by Revision 11, C11-9.)*

**For the implementing sprint (non-blocking MINORs, round 12).** Fold into the task named in each note:
- **C12-1 (A7, B7, C3):** state how the R21 gate is invoked. Run it as `subprocess.run(["bash", "-c", GATE])`
  with no `-e` or `pipefail` (or use the allowed Python form); a CI `run:` step (`bash -e {0}`) must wrap it
  with `set +e`, and `/bin/sh` (dash) rejects the `s=(` array form. Both misuses fail loudly, never falsely pass.
- **C12-2 (C3):** AC-31's state snapshot covers only `vars(Viewer3D)` and `vars(server)`. Either extend it to
  every module dict under `pylabrobot.visualizer3D.*` (and the class dicts they expose), or narrow D11's
  wording to "no rebinding in `server` or `Viewer3D`".
- **C12-3 (A1, A2, A3, C1):** add `harness` (`scripts/repl_smoke.py`) to AC-1's "Units" hashed-input list
  (it governs AC-1, AC-2, AC-3 and AC-29); D17 already requires it.
- **C12-4 (doc):** D16's "`repl.yml:45` on the sprint A branch" is `:47` (`timeout-minutes: 45`), as D16's
  other anchor and References say.
- **C12-5 (A1, A7):** A1's import test builds a temporary tree holding only `repl_smoke.py` and
  `pyproject.toml`. If A7 makes `repl_smoke.py` load `scripts/unit_runner.py` at module import, the test
  must also copy `unit_runner.py`, or the load must stay lazy.
- **S1 (A1):** D16 says `notebook_expected()` is called "once per `--notebook-check` run" but A1 calls it at
  four sites: say "at each use site", or bind it once at the top of `run_notebook_check` so a missing
  `version.txt` fails before the browser launches. Update the S1 probe's `_dry_run` comment ("repl_smoke
  reads the PLR submodule's version.txt at import") in the amendment commit.
- **S2 (C3):** AC-31's positive control should run a scene build without triggering the rebind: a stock
  `Viewer3D(deck, open_browser=False)` over the seeded root, since constructing `DockedViewer3D` rebinds.

## Sprint notes recorded during execution (260929, orchestrator)

These are implementer findings from merged tasks that later tasks must honour. They interpret the
spec where it was silent or self-inconsistent; none reopens a ruling. Source: each task's verified
report and the S1/S2/S3 research notes in `.praxia/docs/research/`.

- **Spike results in force.** S1 = `s1_a` (run `1e0cab6d`): real Lumino widget by prototype-chain walk,
  D6 case `honoured_reachable`, every AC-36 width key asserted, `restoreLayout()` keeps the iframe,
  `windowingMode = contentVisibility` (no re-attach signal; A5 warns and subscribes to
  `inViewportChanged` for any other mode). S2 = `s2_b_exec_t` (run `bf83a4e6`): an untrusted reopen keeps
  only `class` on table/details/summary and strips the SVG and `style`/`data-*`/`tabindex`/`aria-label`/
  `role`; an executed-saved-reopened notebook is trusted and live. S3 = `s3_combined` (run `a3458bf2`):
  carriers work (S3-A), `set_custom_exc` yields no error output so B6 wraps the shell instance's
  `showtraceback` (S3-C), `post_run_cell` does not fire for top-level-`await` cells so B7 announces from
  debounced PLR callbacks (S3-D). All three ran against the local 260828 dist (PLR 0.2.2), a recorded
  deviation; A7's CI `--display-check` on a fresh build is authoritative.
- **A4 (theme CSS).** Light sets `--jp-layout-color1` = ground `#EEF1F4` (painted by `.jp-Notebook`) and
  `--jp-layout-color0` = sheet `#FFFFFF` (painted by `.jp-CodeCell`); AC-7's `light_ground` and
  `light_sheet` read exactly those two elements. The rail is `.jp-CodeCell::before` keyed on
  `data-praxis-cell-state`; the execution count is `.jp-CodeCell::after` with
  `content: attr(data-praxis-exec)`. The error rail is keyed on the attribute only (the stderr mime also
  marks plain stderr streams, so it is not a reliable error signal). The class vocabulary B2-B6 must emit
  is in the CSS header (`.praxis-out`, `.praxis-error`, `.praxis-error__title`, `.praxis-error__plr`,
  `.praxis-stale`, `.praxis-readout`, `.praxis-focus-ring`, `.praxis-deck-panel__*`). Inline `style` text
  colours cannot be remapped for Dark without `!important`, so HTML text must use classes; SVG colours are
  mapped by attribute value.
- **A5 (chrome.js).** State precedence is running > stale > error > ran > not-run; stale needs a non-null
  execution count and a snapshot taken when an execution was observed in this page (the snapshot form,
  not `isDirty`); an error output with a null count is `error`; `data-praxis-exec` is `""` for a null
  count. `onExecution` events carry `phase: "started" | "finished"`, and B9 must filter on `phase`. The
  loader logs and records `window.__praxisDisplay` on failure and posts nothing on `praxis_repl`;
  `praxis:display-error` (D13) is B8's.
- **A7 (harness).** Entry script and sidecar for the sprint A negative-sensitivity run are under
  `scripts/spikes/`, the shared driver under `scripts/negatives/`; the spec's file plan puts entry
  scripts under `negatives/` (a `git mv` plus path strings if that is preferred). D1-dark's listed keys omit
  `pageerrors` (a pageerror in D1-dark is recorded, not failing).
- **B1 (primitives).** `praxis/display/` has no `__init__.py` until B8. `budget.enforce` raises
  `BudgetExceeded` when even level 2 is over the cap, so B2-B6 must keep names short enough for level 2 to
  fit. `check_bundle` requires both `text/html` and `text/plain` (B8 may need a variant for the S3-B
  fallback, which is not in force). Measured about 60 bytes per circle subpath and about 5.7 KB for 96 wells
  in one path (D4's "about 35 bytes" was unmeasured). B1's floor tests use stand-in geometry; B2 (labware) and
  B3 (deck) must redo AC-12 with real PLR definitions.
- **C2 (vendoring).** `visualizer3d/index.html` is the one transformed file (three anchored edits, per
  D11/AC-30); the other 42 files are byte-identical to upstream at `786ac2c4e` (checked by blob sha
  through the GitHub API). The manifest has no `pylabrobot_version` field. `stage_overlay` copies all of
  `overlay/assets/`, so a build carries `assets/visualizer3d/`.
- **C4 (socket shim), for C3, C5 and C7.**
  - `msg` in BOTH directions carries `viewer` and `client` as well as `data` (the D11 prose at "Protocol
    on `praxis_viz3d`" governs; the table row `msg | {client, data}` is short by `viewer`). C3 must put
    `viewer` on every kernel-to-page message, or the page drops every scene. `msg` is delivered only after
    `accept`.
  - The page posts only `open`, `msg` and `bye` (`bye` once, on `close()`, `pagehide` or the accept
    timeout, never after `evict` or a kernel `close`); it never posts `close`, `query`, `announce`,
    `accept` or `evict`. Malformed or unknown kinds are dropped silently.
  - `close()` goes to CLOSING and fires `onclose` on a 0 ms timer, like a WebSocket; `send()` with
    non-string data throws `TypeError`, and while CONNECTING throws `InvalidStateError`.
  - `embed.js` forwards the page's `plr:status` and `plr:gone` to `window.parent` as `praxis:dock-status`
    CustomEvents with `detail = {event: "plr:status", connected: boolean, viewer}` or
    `{event: "plr:gone", viewer}` (C5 reads this). A `plr:status` fired before `embed.js` registers is
    not replayed.
  - The vendored page's three.js scene background is `0xe8ecef` (`renderer.js:34-35`), drawn on the canvas;
    `embed.css` can only paint the DOM ground `#EEF1F4`. AC-34 `canvas_nonblank` (C7) must expect a slight
    offset or compare against `#E8ECEF`, unless C5 decides to change the canvas colour (no setter exists
    without a vendored edit).
  - `embed.css` adds `.content{height:100%}` (not in D12) so the hidden navbar leaves no 60 px gap.
