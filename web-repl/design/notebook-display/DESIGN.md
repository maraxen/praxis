# Notebook display: design plan

task_id `260929_notebook-display-design`. Prototype: `index.html` in this directory
(open it directly, or with `?viewer=<Visualizer3D url>` to dock the live 3D viewer).
Fixture: `make_fixture.py` -> `fixture.js`, a real PLR 0.2.2 STARlet deck after three
simulated column transfers. Nothing here is staged by `build_repl.py`, which copies only
`overlay/assets/` and `files/`.

## Brief

**Subject.** The Praxis web REPL: a JupyterLite notebook where people write PyLabRobot
code, run it against a simulated or real liquid handler, and see what happened on the deck.

**Audience.** Lab scientists and automation engineers. They know plates, rails and tips
better than Jupyter. They read a notebook to answer one question, over and over: *what
is on the deck now, and did the last step do what I meant?*

**Primary job.** Close the gap between a line of code and the physical state it changed.
Vanilla JupyterLite prints `Plate(name=source, size_x=127.76, ...)` and a wall of
chatterbox text. The deck itself is only visible in a separate window.

Three surfaces, one system:

1. **Rich cell outputs.** PLR objects render as what they are: a plate as a to-scale
   footprint with liquid in the wells, a tip rack as tips, a deck as a plan with rails,
   a run as a ledger of liquid moves, and a PLR error as a plain statement of what went
   wrong and where.
2. **Notebook chrome.** Quieter and more legible than vanilla: cell state shown on a
   status rail, no `[ ]:` prompts, outputs visibly owned by their cell.
3. **Deck dock.** PLR's new `Visualizer3D` (BioCam / Camillo Moschner, PyLabRobot #1378,
   merged 2026-09-27) docked beside the notebook in a compact embed mode, following the
   cell you are working in. Stefan Golas's `viz3d-motion` fork (motion playback decoded
   from firmware commands) plugs into the same dock as a scrub bar when it lands.

## Tokens

Kept inside the Praxis identity that `overlay/assets/theme/praxis-theme.css` already
ships: rose and moonstone, Roboto Flex and JetBrains Mono. This design doesn't rebrand.
It gives the brand colors *jobs*.

### Color

| Name | Hex | Job |
|---|---|---|
| Deck steel | `#EEF1F4` | Page ground. Cool, like a STAR's stainless deck. Not cream. |
| Sheet | `#FFFFFF` | Cell surface. |
| Ink | `#1D2935` | Text, outlines of labware. 14.8:1 on sheet. |
| Ink soft | `#56636F` | Secondary text, rail numbers. 6.2:1 on sheet. |
| Rail | `#C9D2DA` | Hairlines: rails, carrier outlines, cell edges. Structure only, never text. |
| Moonstone | `#73A9C2` | **Liquid.** Fills wells by volume. Never used for text or chrome. |
| Moonstone ink | `#2F6882` | Links and "done" state. 6.1:1. |
| Rose | `#ED7A9B` | **Attention.** Running cell, focused resource, selection. Marks only. |
| Rose ink | `#B8436A` | Rose text where rose must be read. 5.2:1. |
| Brick | `#B3402A` | Errors. 5.7:1. Kept far from rose so an error never reads as a selection. |

The rule that carries the system: **moonstone means liquid and rose means "look here".**
Blue in a well always means volume. Pink anywhere, in the notebook or the 3D dock, is
the thing you're working on.

Syntax (retints the Material palette the 260828 handoff deferred; all ≥ 5:1 on sheet):
keyword `#2F6882`, string `#A63D61`, number `#8A5A00`, call `#7B4FA0`,
comment `#56636F` italic.

### Type

- **Roboto Flex** for everything that isn't code. Its width axis is the one active
  typographic device: resource names in outputs are set condensed (`wdth` 25, weight 600)
  like the stamped labels on a carrier. Prose and UI stay at normal width.
  Data uses `tabular-nums` in Roboto Flex, not a monospace face.
- **JetBrains Mono** for code cells and tracebacks only.
- Scale on a 15 px body, 1.5 line-height, ratio about 1.2:
  12.5 (figure labels) / 15 (body, code 13.5) / 18 (output headings) / 22 / 28
  (notebook title). Code is capped at 88 ch and prose at 72 ch.

### Shape

Radius encodes physical versus software. Software surfaces (cells, the dock) are 8 px,
the brand control radius. Labware is drawn at its true corner radius (plate ≈ 2 mm,
scaled). Wells are circles when PLR says `cross_section_type: circle`. No drop shadows.
Depth comes from ground versus sheet only.

## Layout

```
┌─ mark  standard-curve.ipynb ─────────────── Simulated STARlet ── Kernel ready ─┐
│                                                  │                              │
│  ▌ 2  lh = LiquidHandler(...)                    │  Deck            Follow ●    │
│  ▌    deck.assign_child_resource(...)            │ ┌──────────────────────────┐ │
│  ▌  ┌ output ───────────────────────────────┐   │ │                          │ │
│  ▌  │ deck  HamiltonSTARDeck, 32 rails      │   │ │   Visualizer3D (embed)   │ │
│  ▌  │ [plan view, rails 1..32 ruler]        │   │ │   rose = selection       │ │
│  ▌  └───────────────────────────────────────┘   │ │                          │ │
│                                                  │ └──────────────────────────┘ │
│  ▌ 3  source                                     │  assay  A1:H3  3 columns    │
│  ▌  [plate footprint, wells filled by volume]    │  Iso  Top  Front            │
│                                                  │  ─ motion scrub (viz3d) ─   │
└──────────────────────────────────────────────────┴──────────────────────────────┘
```

- Two columns above 1100 px: the notebook (fluid, content max 880 px, left-aligned) and
  the dock (sticky, 420–560 px, resizable). Below that, the dock collapses to a bottom
  sheet with the deck plan as its peek state.
- The **status rail** replaces `In [n]:`: a 3 px bar on each cell's left edge. Rail grey
  means not run, moonstone ink means ran, rose means running, brick means error. A dashed
  bar means stale, edited since it ran. The execution count sits at the rail's top in
  12.5 px ink-soft.
- Outputs are inset under their code, on the same sheet, divided by one rail hairline.
  They aren't separate cards.

## Output grammar

Every PLR output has the same three rows, so a reader learns them once:

1. **Name line.** The resource name (condensed), then its PLR type and model in ink-soft.
   `source  Plate  cor_96_wellplate_360uL_Fb`
2. **The drawing.** To scale, at 3 px/mm, front edge at the bottom as you stand at the
   machine. Row letters and column numbers appear on well grids because they are the
   real addresses (A–H, 1–12).
3. **Summary sentence.** State in words, not a stats strip:
   "24 of 96 wells hold liquid, 50–150 µL. 2,400 µL in the plate."

Hovering a well or tip shows its address and value. Clicking any resource in any output
focuses it in the dock (rose outline in both places).

- **Plate:** well outline in rail. Liquid is a moonstone disk whose *area* is proportional
  to volume over `max_volume`, so a half-full well looks half-full.
- **Tip rack:** present tips are filled ink rings, taken tips are empty dashed rings.
  "72 of 96 tips left. Columns 1–3 used."
- **Deck:** plan of the deck with a rail ruler along the front edge (numbers every 5
  rails), carriers in rail outline, labware in ink, liquid and tips as above at small
  scale. Name labels on carriers, condensed.
- **Run ledger** (the output of a cell that moved liquid): one row per operation, grouped
  by tip cycle. Columns: step, action, where, volume, channels. Aspirate and dispense
  rows carry a small moonstone bar sized by volume. The ledger ends with the deck state
  after the run: the changed plate, with changed wells marked in rose.
- **PLR error:** brick status rail. A heading states the fault in the domain's terms,
  names the resource and wells PLR's own message omits, and gives the fix. The drawing
  shows the offending wells in brick. The traceback is folded under "Show traceback".

  PLR says: `TooLittleLiquidError: Not enough liquid in container: 80.0uL > 50.0uL.`
  The output says: **"Not enough liquid in assay A1:H1."** "Each well holds 50 µL; the
  aspirate asked for 80 µL. Lower `vols` to 50 µL or less, or aspirate from the source
  plate."

## Deck dock

- Hosts the vendored Visualizer3D page in an iframe, in an **embed mode** added by an
  augmentation script, the same pattern as today's `overlay/assets/visualizer-augmentations/`.
  The mode hides the navbar, the left tool rail and the stats footer, collapses the
  Facility Tree behind a toggle, and sets the page ground to deck steel.
- Transport: `Viewer3D`'s socket surface is `_broadcast` (server.py:353), `_handler`
  (server.py:590) and `start` (the HTTP and websocket servers, :780–811). The page's socket
  is one line in `static/transport.js:63`. Same shape as `praxis/viz/browser.py`: subclass
  and route over the existing BroadcastChannel. **Measured 260929:** main's Visualizer3D
  served over this fixture deck runs against our pinned PLR 0.2.2 unchanged, and draws in
  headless Chromium on WebGL2/SwiftShader.
- Dock header: deck name, **Follow** toggle (focus the resource the current cell's output
  shows), view presets Iso / Top / Front (the page's own `?view=` values).
- Footer: the current selection in words ("assay A1:H3, 3 columns").
- **Motion (viz3d-motion):** when a run cell executes, the dock shows a scrub bar over its
  decoded commands, labeled with the ledger's step numbers, so a ledger row and a moment
  in the animation are the same thing. Golas's branch is STAR-only, v1-driver-only and
  unmerged (54 ahead, 76 behind main as of 260929), so this is a slot and not a dependency.

## Motion

None by default, as in the shipped theme. Three things respond to actions: a running
cell's rail turns rose, a focused resource gets a rose outline in both panes, and the
dock's motion playback plays when the user presses it. `prefers-reduced-motion` has
nothing to disable.

## Review against the generic defaults

| First instinct | Why it was generic | Revised to |
|---|---|---|
| Brand 135° gradient as the running-cell indicator | The gradient is decoration, and gradient washes are the SaaS tell | Solid rose rail. The gradient stays in the logo mark only |
| Each output a rounded card with a shadow | SaaS card kit | Outputs inset on the cell's own sheet, one hairline |
| "VOLUME / TIPS / WELLS" stat tiles above the plate | Big-number tiles plus all-caps labels | One summary sentence under the drawing |
| Monospace for coordinates and volumes | Monospace-for-small-data tell | Roboto Flex `tabular-nums`. Mono is code only |
| Dark IDE theme to feel "technical" | Near-black plus one accent | Light first, a cool steel ground from the machine itself. Dark is a token swap later |
| Meta line `Plate · 96 wells · 360 µL` | Middle-dot meta string | Name line is name, type, model, spaced. Counts go in the sentence |

The one bold choice is the **to-scale drawing**. Every other part of the design stays
quiet so it can carry the page.

## Implementation path (not built here)

1. `praxis.display`: `_repr_html_` for `Plate`, `TipRack`, `Deck`, `Container`, and a
   `RunLedger` context manager that records ops. It emits self-contained HTML + inline SVG,
   because JupyterLite custom MIME renderers need a labextension build that web-repl
   deliberately doesn't have. Registered at boot through
   `get_ipython().display_formatter.formatters['text/html'].for_type(...)`, so PLR stays
   unpatched.
2. The error display: `get_ipython().set_custom_exc((PLR errors...), handler)` renders
   the error panel, with the wells taken from the ledger's last op.
3. Chrome: extend `praxis-theme.css` (status rail, prompt removal, syntax palette),
   keeping its `body[data-jp-theme-name]` scoping rule.
4. Dock: vendor `pylabrobot/visualizer3D/static` and add `praxis/viz/viewer3d.py` (Viewer3D
   subclass over BroadcastChannel) plus the embed augmentation. The shell mounts the dock
   beside the notebook.

## Screenshots (260929, headless Chromium, SwiftShader)

- `shots/desktop-full.png`: the whole notebook with the plan-view dock fallback.
- `shots/error-output.png`: the PLR error output and the dock.
- `shots/dock-visualizer3d.png`: `?viewer=` with main's Visualizer3D serving this fixture
  deck, cropped as a stand-in for embed mode. The page's stats footer colliding with its
  scale bar is why embed mode has to hide chrome from inside the page, not crop it.
- `shots/visualizer3d-standalone.png`: the same viewer as PLR ships it, for comparison.
