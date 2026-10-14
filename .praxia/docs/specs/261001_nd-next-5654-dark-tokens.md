---
title: 'Notebook display, next: a Dark token set for outputs and the deck panel (backlog #5654)'
description: Spec-increment draft. Grounds what the shipped Dark theme does to the display's outputs and deck panel, tabulates computed candidate palettes (contrast and colour-vision), weighs three options, and recommends four Dark token overrides plus a framed light viewer, with gates, tasks, risks and open questions. Design only; no product code.
status: draft
task_id: 260929_notebook-display-design
date: '261001'
backlog_id: 5654
---

# Notebook display, next: a Dark token set (backlog #5654)

Increment to `260929_notebook-display-epic.md` (the epic is NOT edited here; section 10 lists what it would change).
Base: `feat/notebook-display-sprint-c-stacked @ 60d053f2` (PR #198). Branch of this draft: `nd/next-5654-dark-tokens`.

**Evidence base.** Every number below comes from two pre-registered bathos runs on this branch, not from conversation:

| Run | Script and sidecar | Outcome |
|---|---|---|
| `07edfb7f-eb0e-4fc7-abc7-81b9a77d35f5` | `scripts/spikes/261001_nd_dark_tokens_contrast.{py,bth.toml}` | `baseline_gaps_p2_feasible` |
| `54fdb517-7f09-4de5-8d88-d613df145c6c` | `scripts/spikes/261001_nd_dark_tokens_hybrid.{py,bth.toml}` | `hybrid_meets_all` |

The first reads the palette from `praxis-theme.css` and the vendored viewer's JS (nothing typed in); the second types four fixed hexes (disclosed below). Both use the B8 colour instrument
(`web-repl/tests/test_display_colorblind.py`, loaded by path), and carry their own positive and negative controls.
**Disclosure:** before the first sidecar existed I ran four throwaway inline explorations to choose candidates; they are
not cited, and the sidecars say so. The second run's hexes were chosen after reading the first run's table (also disclosed
in its sidecar). Contrast figures are "worst case": the minimum over the three Dark surfaces
(`--jp-layout-color0/1/2` = `#12121E`, `#1A1A2E`, `#1E1E2D`) and normal vision plus Machado 2009 protan, deutan, tritan.
Normal-vision-on-`#12121E` figures are marked "(ground)". The warm bathos index was write-locked by another process
during this task (`bth compact` failed: "Conflicting lock ... PID 0"), so the records were read straight from the cool-tier
parquet (`outcome`, `exit_code`, `sidecar_sha256` all present and matching the committed sidecars); run `bth compact`
before querying them with `bth sql`.

---

## 1. Problem and current behaviour (verified)

### 1.1 The theme

- `web-repl/jupyter-lite.json:17-20` pins `"theme": "JupyterLab Dark"`. Dark is the default, so it is what almost every user
  sees. D10 of the epic kept it so (`260929_notebook-display-epic.md:692`).
- The Dark palette is `praxis-theme.css:149-221` (ground `--jp-layout-color0: #12121e` at :157). In Dark the notebook ground
  and the cell "sheet" are the same colour: JupyterLab's core CSS has `.jp-Notebook { background: var(--jp-layout-color0) }`
  and `.jp-Cell { background: transparent }` (read from `jlab_core.c0153ee.js` in the main checkout's `web-repl/dist/`), and
  `test_display_css.py::test_dark_theme_has_no_cell_background` pins "no cell background rule reaches Dark".
- The design's depth device (steel ground, white sheet) therefore exists only in Light (`praxis-theme.css:401-462`).

### 1.2 What already adapts in Dark (no work needed)

| Surface | Mechanism | Evidence |
|---|---|---|
| SVG structure: sheet, ink, ink soft, rail | `.praxis-out [fill='#FFFFFF' i]` etc. map the inline light palette to `--jp-layout-color0`, `--jp-content-font-color0/2`, `--jp-border-color1`; no theme named | `praxis-theme.css:580-610`; pinned by `test_praxis_out_maps_structural_colours_to_tokens` and `test_praxis_out_is_not_theme_scoped` |
| HTML text in outputs (summary, name line, ledger, details) | `color: var(--jp-content-font-color0/2)`; no inline colour is emitted at all (`svg.py` strips `style`; the only hex literals in `praxis/display/` are `labware.py:72-78`) | `praxis-theme.css:863-1132`; `grep -n '#[0-9a-f]{6}'` over the display modules |
| Moonstone (liquid), rose (focus, running), both light-palette brand constants | already clear every mark bar on Dark (below) | run `07edfb7f` |
| Deck panel chrome: header, title, sub, Follow, Iso/Top/Front, footer, text fallbacks | all `var(--jp-*)`; `dock.js` colours are tokens too (`dock.js:377`) | `praxis-theme.css:707-805`; `dock.js` grep |
| Error title and ledger error text | `var(--jp-error-color1)` = `#cf6679` in Dark | `praxis-theme.css:676-678, 1113-1115` |

### 1.3 What is light-first and fails (run `07edfb7f`, candidate P0 = the shipped set)

Bars: text >= 4.5:1 (WCAG 1.4.3), non-text marks >= 3.0:1 (WCAG 1.4.11), colour pairs CIEDE2000 >= 10 under every vision (AC-27's number).

| Token (use-site, verified) | Shipped value | Worst-case | (ground) | Verdict |
|---|---|---|---|---|
| brick (error rail `:510`, error border `:576, :667`, `.sv-fault` `:989-993`, ledger error bar `:1098, :1106`) | `#B3402A` | 2.24 | 3.26 | mark bar missed |
| moonstone ink (rail `ran` `:502`, stale dashes `:516`) | `#2F6882` | 2.55 | 3.03 | mark bar missed |
| rose ink (deck item hover outline `:899` only) | `#B8436A` | 2.54 | 3.58 | mark bar missed |
| error title and ledger error text (`--jp-error-color1`) | `#CF6679` | 3.81 | 5.15 | **text bar missed** (it is 18 px / 600, below WCAG "large") |
| ink, ink soft, link, moonstone, rose | structural / constants | 14.72, 8.26, 6.15, 6.15, 5.17 | | pass |
| rose vs brick, moonstone vs brick, rail pairs | | 21.9, 42.2, >= 18.1 | | pass |

So the Dark gaps are exactly four tokens, none of them structural. Brick has **no text use-site** (it is only ever a
rail, border, stroke or bar, and every one of those has words beside it: D3 "errors are never shown by colour alone"), moonstone
ink has none either, rose ink is a hover stroke. The one coloured text in outputs is the error title.

**The deck panel's body is the largest light-first element and no token reaches it.** The panel body is an iframe of the
vendored Visualizer3D page. `embed.css` hard-codes its ground `#EEF1F4`; the scene paints its own `BACKGROUND = 0xe8ecef`
(`visualizer3d/renderer.js:34-35`), set once, never read from a theme. In Dark that is a 15.63:1 bright rectangle in a
`#12121E` panel. The page's drawing constants are dark-ink-on-light by design (`constants.js:72-76, 118`):

| Vendored constant | Hex | On its own light ground | On a Dark ground (`#12121E`) |
|---|---|---|---|
| `FLAT_EDGE` (every resource outline) | `#1F2529` | 13.05 | **1.20** |
| `SELECT` (selection box) | `#1A4B8C` | 7.28 | **2.15** |
| `STRUCTURE_DARK` (inner outlines) | `#49555E` | 6.44 | **2.43** |
| tip | `#333333` | 10.63 | **1.47** |

So darkening only the scene background would make the deck unreadable. Editing these is forbidden (D11: no vendored edits;
`VENDOR_MANIFEST.json` carries sha256 per file).

### 1.4 Which gate runs in which theme (read from `repl_smoke.py`)

| Unit | Theme | Why it matters here |
|---|---|---|
| D1 (rail, ground, sheet) | Light, via `set_theme` (`:5355`) | |
| D1-dark | default Dark | `rail_colors_match_dark` compares against the **shared** `RAIL_RGB` (`:4900`: `ran` `rgb(47,104,130)`, `error` `rgb(179,64,42)`), so changing Dark's rail colours changes this gate |
| D2 (reprs, errors, stale, keyboard), D3 (trust loss) | default Dark (neither calls `set_theme`) | D3 pins `liquid_fill_computed == rgb(115,169,194)` = moonstone (`:4221, :4354`): moonstone must not change in Dark |
| D4 (High Contrast) | HC, twin context with the CSS blocked | proves HC is untouched by comparing `--jp-layout-color0` |
| K1a, K1b, K2 (deck panel) | **Light only** (`DOCK_THEME = THEME_NAMES[True]`, `:8022, :9155`) | **the Dark deck panel has no browser gate at all today** |

### 1.5 The fence: existing tests that shape any design (read, not assumed)

1. **Pre-cap pin.** `test_display_css.py:1534-1535, 1641-1650` pins the first 39 224 bytes of `praxis-theme.css` by sha256 and
   requires what follows to be exactly one `@media` rule (the 1600 px cap). *Any* new CSS, before or after the cap, breaks
   `test_cap_is_a_pure_addition_after_the_a4_and_b_css_rules` unless the pin is moved; the file's own comment calls that
   the sanctioned procedure ("a legitimate later edit of an earlier rule has to move this pin deliberately"; moved once before).
2. **Outputs name no theme** (`test_praxis_out_is_not_theme_scoped`, :856); **HC and `data-jp-theme-light` are never named**
   (`:249`, `test_theme_staging.py::test_high_contrast_theme_is_left_alone`); every `--jp-*` override sits under a
   `body[data-jp-theme-name=...]` selector (`:255`); `:root` holds the brand constants at their light values (`:291`).
3. **Blue is volume** (`test_blue_means_volume_only`, :974) greps rules whose selector contains `.praxis-` or `.sv-` for the
   string "moonstone"; a body-level token redefinition has neither, so it is not policed there.
4. **`design_palette()` overwrites by row name** (`test_display_colorblind.py:253-260`: `out[m.group(1)] = ...`). A second
   Colour table in `DESIGN.md` reusing "Ink", "Brick", ... would silently replace the light values the whole B8 suite reads.
5. **`dock.js` builds the iframe `src` and pins it** (`dock.test.js:307-308`, `viewerSrc` returns
   `...index.html?embed=1&view=top&viewer=<id>`), sets inline `border: 0; width: 100%` on the iframe (`dock.js:495`), and
   `test_no_important_anywhere_in_the_file` forbids `!important`.

---

## 2. Assumptions

Tags: **V** verified (read at file:line or a registered run), **S** spiked (computed, no browser), **U** unverified (needs a real browser).

| # | Assumption the design leans on | Tag | Evidence |
|---|---|---|---|
| A1 | Dark gaps are exactly the four tokens in 1.3 | V/S | run `07edfb7f`, `p0_failing = text:error_title=3.81;mark:brick=2.24;mark:moonstone_ink=2.55;mark:rose_ink=2.54` |
| A2 | Brick, moonstone ink and rose ink have no text use-site | V | `grep -n 'praxis-brick\|praxis-moonstone-ink\|praxis-rose-ink' praxis-theme.css`: uses are `background`, `border-left`, `stroke`, `fill`, `box-shadow` only |
| A3 | A single 4.5:1 bar for brick is infeasible: brick lightened to 4.5 (P3 `#DB7865`) is 4.6 dE from rose under the worst vision | S | run `07edfb7f`, `p3_rose_vs_brick_ok = False` (the designed negative for "one bar for every token") |
| A4 | The hybrid `#4393B8 / #C05277 / #D1523A / #D47687` meets text 4.5, mark 3.0, pairs >= 10, hover-vs-focus >= 10 (13.1), hairline >= 5 on all three surfaces (8.5-8.6), rose-vs-brick >= 12 (13.8) | S | run `54fdb517`; four mutants each failed the check they target |
| A5 | A `--praxis-*` redefinition on `body[data-jp-theme-name='JupyterLab Dark']` reaches every `var(--praxis-*)` consumer under `body` and does not touch High Contrast | V (spec) / **U** (browser) | custom properties inherit; the HC name differs by string equality; the key `dark_brand_tokens_computed` below turns it into a measurement |
| A6 | Moonstone and rose can stay unchanged in Dark | V/S | worst-case 6.15 and 5.17; D3 pins moonstone's computed fill in Dark |
| A7 | Every gate that must change is enumerable from the unit table | V | 1.4; `test_repl_smoke_resume.py:1171, 1366, 1440` hold the old rail rgbs |
| A8 | Dark `.jp-Notebook` ground is `--jp-layout-color0` in the real app | V (CSS text) / **U** (render) | `jlab_core.c0153ee.js`; D1-dark records no ground |
| A9 | `filter: invert(1) hue-rotate(180deg)` on the viewer iframe gives a dark deck: filtered scene ground `#101417` (1.0:1 against the panel `#12121E`, seamless), edge `#D6DCE0` 13.37:1, selection `#8FC0FF` 9.83:1, tip `#CCCCCC` 11.53:1 | S (spec matrix, modelled) / **U** (browser: GPU iframe compositing, WebGL canvas, hues of models) | run `07edfb7f` `viewer` block |
| A10 | The scene's own ground `#E8ECEF` is within the K1a canvas tolerance (6) of the CSS ground `#EEF1F4` | V | max channel delta 6 (run `07edfb7f`, `k1a_canvas_tolerance_check`); this is why `CANVAS_CHANNEL_TOL = 6` |
| A11 | An `outline`/margin/radius on the iframe can frame it without `!important` and without editing `dock.js` | **U** | inline style sets only `flex`, `width`, `min-height`, `border` (`dock.js:495`); `margin` + `max-width` are free for CSS, but whether a negative-offset outline paints over an iframe is browser behaviour |
| A12 | Chromium is unavailable here, so nothing in this draft was rendered | V | task brief; every browser-dependent claim is tagged U |

---

## 3. Options

Two axes. **Output and chrome tokens** (A, B, C), then **the deck panel body** (O1 to O4), which is independent of them.

### 3.1 Output and chrome tokens

**Option A. Four Dark token overrides (recommended).**
One new block, inserted before the cap, under `body[data-jp-theme-name='JupyterLab Dark'], body:not([data-jp-theme-name])`
(the same first-paint selector the Dark block uses), redefining `--praxis-moonstone-ink`, `--praxis-rose-ink`,
`--praxis-brick` and `--jp-error-color1`. No rule changes, so every selector, mapping and "rule text" test is untouched; the
rules already read the tokens. High Contrast is not named, so it keeps the `:root` light constants exactly as today.
- Costs in tests: one pin move (`_PRE_CAP_BYTES`, `_PRE_CAP_SHA256`); a new `test_display_dark_tokens.py`.
- Costs in browser gates: D1-dark's expected rail colours (`ran`, `error`) change and get their own dark constants; D2 gains two
  keys (fault stroke, error title); D4 gains one (HC token unchanged); one new dock unit for the Dark panel.
- Tradeoff: Dark keeps ground == sheet (no depth), which is today's behaviour.

**Option B. A designed Dark scheme.** A, plus a raised output sheet (outputs on `--jp-layout-color1`, so ground-versus-sheet
depth exists in Dark as in Light) and the inverted viewer (O2).
- Costs in tests: reverses `test_dark_theme_has_no_cell_background` and the mapping `sheet -> var(--jp-layout-color0)`
  pinned in `test_praxis_out_maps_structural_colours_to_tokens`; `.praxis-out` rules cannot name a theme, so the raised sheet
  needs a new indirection token and edits to those pinned rules and their mutants. D1-dark gains ground/sheet keys like
  `light_ground`/`light_sheet`.
- Costs in browser gates: everything in A, plus the above keys and a screenshot review.
- Tradeoff: closest to "dark as designed as Light", but edits pinned assertions (as designs, not loosenings) and has no
  rendering evidence behind it. Not recommended before a real-browser look.

**Option C. Light reading surface.** Outputs keep the light palette on a white card inside Dark (no new colours; the B8
suite already covers it).
- Costs: reverses D3 ("outputs follow Dark ... without the stylesheet naming any theme") and AC-26's "by construction"
  for HC, which would then need a theme-scoped exception (forbidden by the "no theme named" tests). 15+ tests change.
- Tradeoff: zero contrast risk, but a white slab in a dark app, the same glare problem as the viewer, everywhere.
  Rejected.

### 3.2 The deck panel body (the vendored viewer)

| | What | Cost | Risk |
|---|---|---|---|
| **O1** (recommended default) | Keep the viewer light. Frame it as an inset (margin, radius, hairline) so a bright window reads as a deliberate view of the machine, not a defect; no vendored or `embed.js` change | CSS only, in the Dark block or a sibling rule; no `src` change (A11 U) | glare in a dark UI |
| **O2** | `filter: invert(1) hue-rotate(180deg)` on `iframe.praxis-deck-panel__frame` under the Dark name. Modelled result: ground `#101417`, edges `#D6DCE0`, selection `#8FC0FF` | one CSS rule; no `embed.js`, no `src`, no vendored edit; HC unnamed so untouched | hues of the models (carriers, tips, liquid orange) rotate approximately; GPU compositing cost; **needs a human look** (A9 U). K1a's `canvas_nonblank` counts against `#EEF1F4` but runs in Light, unaffected; a Dark unit needs its own expected ground |
| **O3** | Dark scene via a dynamic `import()` of `renderer.js` from `embed.js` and `view.background = ...` | `embed.js` change + theme plumbing (read the parent's `body[data-jp-theme-name]`, same origin) | **rejected on the numbers above**: with the ground dark the outlines are 1.2:1 and the selection 2.15:1 |
| **O4** | An upstream PLR theme API for the viewer (ties OQ-5) | none now | not buildable; named so it is not rediscovered |

---

## 4. Recommendation

**Option A with O1 now; O2 as a gated spike whose only deliverable is a screenshot pair for the user (open question 1).**
- It closes every measured gap (1.3) with four values and zero rule changes; the existing fence tests keep passing
  unchanged except one deliberate pin move.
- It adds the first browser gate on the Dark deck panel, which has none today (1.4).
- It does not claim the viewer is "dark" while its drawing constants cannot be: O3 is measurably unworkable, O2 is unproven.
- The proposed values are the **hybrid** (run `54fdb517`), assembled from run `07edfb7f`'s candidates by use:

| Token | Shipped | Proposed (Dark) | Worst-case | (ground) | Why this one |
|---|---|---|---|---|---|
| `--praxis-brick` | `#B3402A` (2.24) | `#D1523A` | 3.00 | 4.40 | P1's: keeps 13.8 dE from rose; P2's `#D5614B` sits exactly on 10.0 |
| `--praxis-moonstone-ink` | `#2F6882` (2.55) | `#4393B8` | 4.50 | 5.40 | P2's: the rail is a 3 px mark but the token is defined as readable (DESIGN: "links and done"), so it meets 4.5 |
| `--praxis-rose-ink` | `#B8436A` (2.54) | `#C05277` | 3.03 | 4.17 | P1's: a hover outline must stay 13.1 dE from the focus ring; P2's `#CE7794` is 3.3 dE from rose and would read as focus |
| `--jp-error-color1` | `#CF6679` (3.81) | `#D47687` | 4.54 | 5.96 | the one coloured text; P1 = P2 |

Unchanged in Dark: moonstone `#73A9C2`, rose `#ED7A9B`, running rail, ink, ink soft, rail (hairline 8.5-8.6 dE from each surface).

---

## 5. Proposed decisions

- **N5654-1. Dark gets four token overrides and no rule changes.** Reason: every use-site already reads a token (1.2, 1.3), so
  overriding the tokens at the Dark body repaints rails, fault marks, error borders, ledger bars and hover with no selector, no
  mapping and no "rule text" test touched. Rules stay theme-neutral (D3, D10).
- **N5654-2. The override block is scoped to `body[data-jp-theme-name='JupyterLab Dark'], body:not([data-jp-theme-name])`,
  never `:root`, never High Contrast.** Reason: the file header's cascade rule (a `--jp-*` override on `:root` loses to JupyterLab's
  runtime theme CSS, so `--jp-error-color1` needs the `body[...]` specificity; the `--praxis-*` names are JupyterLab-free, and
  declaring them on `body` makes them win over the `:root` constants for every descendant by inheritance), and "leaves HC
  untouched" (item #5654, epic D10). The block must come AFTER the Dark palette block (equal specificity, later wins), which
  placing it just before the cap guarantees. The `:not([data-jp-theme-name])` half keeps the first paint from flashing the light brick.
- **N5654-3. Text and marks are held to different bars by use-site, not by token name.** Text roles (ink, ink soft, link, error
  title) >= 4.5:1; mark roles (rails, outlines, strokes, bars, hover) >= 3.0:1; colour pairs >= 10 dE; hairlines >= 5 dE; all
  worst-case over three Dark surfaces and four visions. Reason: A3. A red hue cannot be both 4.5:1 on a dark ground and 10 dE from
  rose under tritanopia (P3: 4.6); forcing it would push brick toward tan or neon (P2g's `#FF4F0F`, 13.9 dE, is neon).
  Brick is therefore a **mark only**, and a test forbids brick as a `color` (N5654-9).
- **N5654-4. The error title is the one coloured text, so it is the one text token that moves.** Reason: `#CF6679` fails the
  bar under simulation (3.81 worst-case). It is lightened through `--jp-error-color1` in Dark (the token the rules already
  read, pinned by `test_praxis_out_error_text_uses_the_error_token`), which also retints Dark's other error text by ~5 RGB
  steps. Alternative in open question 4.
- **N5654-5. Moonstone and rose do not change in Dark.** Reason: they pass (6.15, 5.17 worst-case); D3's
  `liquid_fill_computed == rgb(115,169,194)` is a Dark-run pin; "blue is volume, rose is look here" stays a constant meaning
  across themes (DESIGN, D15).
- **N5654-6. The override block is inserted immediately before the `@media` cap and the pre-cap pin moves once, in the same
  commit, with the reason in the pin's comment.** Reason: 1.5 (1). The alternative (a second stylesheet) adds a staged
  file, an injector change and a staging test for four declarations. Pin moved, not loosened: the new prefix is pinned
  just as hard. Needs user approval (open question 2).
- **N5654-7. Dark values are documented in `DESIGN.md` under a separate "Color (Dark)" table whose row names never repeat a
  light row name** (for example "Brick on dark"). Reason: 1.5 (4): `design_palette()` overwrites by name. A regression test
  asserts the light table is still what `design_palette()` returns.
- **N5654-8. The viewer is framed, not themed (O1), until the user has seen O2.** Reason: 1.3 (the constants) and A9 (U). No
  vendored edit (D11), no `embed.js` change, no `src` change (1.5 (5)).
- **N5654-9. A new test file owns the Dark tokens: `web-repl/tests/test_display_dark_tokens.py`.** It loads the B8 instrument by
  path (no copy of CIEDE2000 or the matrices), reads the Dark block from the CSS, and holds the bars of N5654-3. Reason: the
  existing suite cannot read Dark colours (it maps nothing in Dark), and a copy of the instrument would drift.
- **N5654-10. The Dark deck panel gets its own dock unit, `K3`.** Reason: 1.4 (the panel is gated in Light only). It is
  chrome contrast, the frame, the viewer drawing against the Dark expected ground, and the HC non-effect.
- **N5654-11. Out of scope, recorded:** Dark code syntax (D10 gives the syntax palette to Light only, and
  `test_light_jp_overrides_carry_the_light_name_only` enforces it); the default theme (OQ-1); the Follow switch's off-state track
  (`border-color0` over the panel is 1.84:1 in Dark, 1.96:1 in Light: a pre-existing parity gap, colour is its only state cue
  besides `aria-checked`); a Dark raised sheet (Option B).

---

## 6. Acceptance criteria

Every browser key has a positive control (the value in the right theme) and a negative control (the wrong theme, or a mutated
input, must fail), per the harness rule. Browser units are run by the orchestrator; I could not run any.

- **AC-D1 (token values and bars)** [PY: new `web-repl/tests/test_display_dark_tokens.py`].
  - The Dark override block exists, is a single rule whose selector list is exactly the Dark name plus the first-paint
    `:not(...)`, declares exactly the four properties, with exactly the N5654 values, and is not `:root`/HC.
  - Bars of N5654-3 hold for those values over `--jp-layout-color0/1/2` and four visions, plus: rose-vs-brick >= 12 dE,
    rose-ink-vs-rose >= 10 dE, Dark hairline >= 5 dE on each surface.
  - **Positive control:** the shipped light-palette check still passes on the light table. **Negative controls (each must fail
    the named bar):** brick = shipped `#B3402A` (mark bar); brick = `#DB7865` (rose pair); rose ink = `#CE7794` (hover);
    error title = `#CF6679` (text bar); a block that adds the HC name; a block placed in `:root`. These are the
    mutants run `54fdb517` already proved the checker can see.
- **AC-D2 (the fence still holds)** [PY: `test_display_css.py`, `test_theme_staging.py`].
  - Every existing test passes unmodified **except** the two pin constants. `_PRE_CAP_BYTES`/`_PRE_CAP_SHA256` move to the new
    prefix (block included); `test_cap_is_a_pure_addition...` and `test_tail_check_fails_on_a_stray_rule_after_the_cap` stay
    as written. Named as must-stay-green and unedited: `test_praxis_out_is_not_theme_scoped`,
    `test_high_contrast_and_light_flag_are_not_named`, `test_high_contrast_theme_is_left_alone`,
    `test_every_jp_override_is_scoped_to_a_theme_name`, `test_rail_colours_match_section_3_1`,
    `test_blue_means_volume_only`, `test_brand_constants_exist_on_root`, `test_dark_theme_has_no_cell_background`,
    `test_praxis_out_error_text_uses_the_error_token`, the B8 file in full.
  - Negative control for the pin: the existing `test_prefix_check_fails_on_a_changed_or_truncated_earlier_rule` (a flipped byte
    in the new prefix must fail it).
- **AC-D3 (DESIGN.md hazard)** [PY: `test_display_dark_tokens.py`]. `design_palette()` returns the same ten light rows as before;
  a synthetic DESIGN with a repeated row name is shown to change it (negative control: this is the hazard being real).
- **AC-D4 (Dark rail in the browser)** [DISPLAY, unit `D1-dark`, AC-7 amended]. `rail_colors_match_dark` compares against new
  `RAIL_RGB_DARK` (`ran` `rgb(67,147,184)`, `running` unchanged, `error` `rgb(209,82,58)`; the stale needle uses the dark `ran`).
  New key `dark_brand_tokens_computed`: `getComputedStyle(document.body).getPropertyValue('--praxis-brick' / '--praxis-moonstone-ink' / '--praxis-rose-ink')`
  equal the three Dark values. **Positive:** the same read in D1 (Light) returns the `:root` values (`#B3402A`, ...), not Dark's;
  **negative:** pure `derive_chrome_keys` tests feed Light's values to the Dark derivation and must get `False`, and the
  existing `test_repl_smoke_resume.py` positive/negative pairs for rail colours are re-pointed (expected values change, the
  structure of each control does not).
- **AC-D5 (High Contrast untouched)** [DISPLAY, unit `D4`, AC-26 amended]. New key `hc_brand_tokens_unchanged`: in the measured
  HC context the same three properties equal the `:root` light constants. **Negative control (sensitivity, AC-39(f)):** on a
  dist copy whose Dark block selector also names HC, `--display-check --scenario D4` exits nonzero naming that key.
- **AC-D6 (outputs repaint in Dark)** [DISPLAY, unit `D2`, which already runs in Dark]. New keys `dark_fault_stroke` (computed
  `stroke` of the E1 error figure's `.sv-fault` equals the Dark brick) and `dark_error_title_color` (computed `color` of
  `.praxis-error__title` equals the computed `--jp-error-color1` and `rgb(212,118,135)`). **Negative:** the pure derivation
  fed the Light value `rgb(179,64,42)` returns `False`. D3's `liquid_fill_computed` is unchanged and must still hold.
- **AC-D7 (Dark deck panel)** [DOCK, new unit `K3`, 4 min budget, default Dark, viewer connected via the K1a setup].
  Keys: `panel_text_contrast_dark` (computed foreground vs resolved background of title, sub, Follow, Iso/Top/Front, footer, each
  >= 4.5, computed in-page from computed styles); `viewer_framed_dark` (O1: the frame's computed margin/radius are non-zero);
  `viewer_nonblank_dark` (the K1a pixel counter against the **O1 ground `#E8ECEF`**, > 1 % of pixels differ).
  **Controls:** the in-page contrast helper runs on two synthetic pairs (white on black passes,
  grey on grey fails) before the real read; `viewer_nonblank_dark` reuses K1a's all-ground and 5 %-marked synthetic images.
  Under O2 the expected ground becomes the filtered `#101417` and `viewer_nonblank_dark` counts against it.
- **AC-D8 (gate coverage of unchanged units)** [DISPLAY]. K1a, K1b, K2, D1, D2's other keys, D3 pass unchanged; the aggregate
  of each check still evaluates over its real units only.
- **AC-D9 (workflow wiring)** [PY: `test_repl_workflow_covers_tests.py`, `test_repl_workflow_scenarios.py`]. The new test file
  and the K3 step are wired in `repl.yml` (the per-file guard fails on an unwired file). K3's step uses the D16 layout
  (step timeout = budget + 2).
- **AC-D10 (sensitivity, AC-39(f))** [DISPLAY via the sensitivity driver, pre-registered]. Negative (f): on a dist copy whose
  `--praxis-brick` Dark override is removed, `--display-check --scenario D1-dark` exits nonzero naming
  `rail_colors_match_dark`. Sidecar committed before the run; positive control = the unmutated D1-dark passing.

---

## 7. Task decomposition (tests first)

| # | Task | Files | ~LOC | Depends | Browser |
|---|---|---|---|---|---|
| T0 | Done in this draft: the two registered runs, scripts, sidecars, locks | `scripts/spikes/261001_nd_dark_tokens_*` | 0 more | | no |
| T1 | RED: `test_display_dark_tokens.py` (values, bars, six mutants, DESIGN hazard); loads B8 instrument by path | `web-repl/tests/test_display_dark_tokens.py` | ~170 | | no |
| T2 | GREEN: insert the Dark block before the cap; move the pin (value and comment); add "Color (Dark)" to `DESIGN.md`; wire the test file in `repl.yml` | `praxis-theme.css`, `test_display_css.py` (2 constants + comment), `DESIGN.md`, `.github/workflows/repl.yml` (**orchestrator only**: the brief forbids touching `.github/`) | ~30 CSS, ~25 doc, 3 | T1 | no |
| T3 | RED then GREEN: dark rail constants and the `light` parameter through `rail_color_ok`/`derive_chrome_keys`; re-point the existing control pairs; `dark_brand_tokens_computed` derivation | `scripts/repl_smoke.py`, `web-repl/tests/test_repl_smoke_resume.py` | ~70 | T2 | derivation no; key is **yes** |
| T4 | RED then GREEN: D4 `hc_brand_tokens_unchanged` and D2 `dark_fault_stroke`, `dark_error_title_color`: derivations with controls, unit-table keys, in-page reads | `scripts/repl_smoke.py`, `test_repl_smoke_resume.py` | ~110 | T2 | derivations no; keys **yes** (D2, D4) |
| T5 | K3: unit table entry, `run_k3` (reuse `DockDriver`, `_setup_dock_world(theme=False)`), in-page contrast helper with controls, frame and ground keys | `scripts/repl_smoke.py`, `test_repl_smoke_resume.py`, `repl.yml` step | ~150 | T2 | **yes** |
| T6 | O1 frame CSS (`.praxis-deck-panel__frame` margin, `max-width`, radius, hairline under the Dark name), no `!important` | `praxis-theme.css` (inside the T2 block), `test_display_dark_tokens.py` rule check | ~10 | T2, A11 spike | **yes** (looks) |
| T7 | AC-39(f)/AC-D10 sensitivity negative: driver entry, sidecar committed first, `test_nd_sensitivity_driver.py` plumbing cases | `scripts/negatives/`, `scripts/spikes/`, tests | ~100 | T3 | **yes** |
| T8 | S-O2 spike: add the filter rule on a dist copy, take Dark panel screenshots for the user (not shipped) | none shipped | ~15 | T6 | **yes**, human review |
| T9 | Orchestrator: epic spec update (section 10) and the browser runs (D1-dark, D2, D4, K3, sensitivity) on a fresh build | epic spec | | all | **yes** |

T1 is the only test that exists before T2; T3-T5 each land their derivation tests RED before the harness code.

---

## 8. Risks

| Risk | Likelihood / impact | Mitigation |
|---|---|---|
| The body-level token override does not reach some consumer (a portal outside `body`, an iframe) | low / a stale light brick in Dark | AC-D4 reads the computed token on `body` and AC-D6 reads the computed stroke of a real fault mark; none of the consumers is in the iframe |
| `--jp-error-color1` also retints every other Dark error text app-wide | certain / minor (~5 RGB steps) | stated in N5654-4; open question 4 offers the ink-title alternative |
| Moonstone ink `#4393B8` is 7.3 dE from the liquid `#73A9C2`: the "done" rail and the volume blue are close cousins | medium / "blue is volume" muddied | they never share a surface (rail vs output body); the same family relation exists in Light (`#2F6882` vs `#73A9C2`); flagged for the human review H-dark |
| Error title `#D47687` is 4.7 dE from rose (a pink error headline next to a rose focus ring) | medium / an error could read as selection | the shipped `#CF6679` is 7.9 dE: already close. Mitigations: the brick rail beside it, the sentence itself, the cross glyph on the marks (D3); open question 4's ink-title alternative removes the colour entirely |
| The pin move is read as loosening a test | medium / process | N5654-6 names it, keeps the pin as strict, and asks first; precedent in the pin's own comment |
| `test_display_dark_tokens.py` and B8 drift (two readers of "the palette") | low | the new test loads B8's instrument; the Dark table is a separate section; AC-D3 guards the overwrite |
| Light viewer inset looks wrong in Dark | medium / taste | O1 is the cheapest to change; T8 produces the O2 pair for a decision |
| O2 would be gated nowhere before shipping | n/a unless chosen | AC-D7's ground key switches to the filtered ground in the same task; K3 is the only gate that could see it |
| Real-browser behaviour of A5, A9, A11 differs from the model | medium | all tagged U; each has a browser key or a screenshot task before it ships |
| The Dark deck panel is ungated today, so unknown defects may surface when K3 first runs | medium / schedule | K3 first-run wall time per the D16 first-run rule; the budget is an estimate |

---

## 9. Open questions (for the user; each with my default)

1. **The deck viewer in Dark: ship the light viewer as a framed inset (default), or try the inverted-viewer filter (`invert(1) hue-rotate(180deg)`, modelled to give a seamless dark ground and 9.8-13.4:1 outlines) and decide from screenshots I cannot take?** Default: ship the framed inset, produce the filtered screenshots in T8 for your decision.
2. **May the pre-cap pin in `test_display_css.py` (`_PRE_CAP_BYTES`, `_PRE_CAP_SHA256`) be moved once for the Dark block (the procedure its own comment describes), instead of putting four declarations in a second stylesheet that needs an injector change and a staging test?** Default: move the pin.
3. **May the D1-dark rail colours (`ran` and `error`, Dark only), two new D2 keys, one new D4 key and a new 4-minute dock unit `K3` be added to the D16 unit table?** (Each changes a pinned expectation or the key list, so I am not assuming it.) Default: yes.
4. **Error title in Dark: lighten the red token app-wide (`--jp-error-color1` `#CF6679` to `#D47687`, 4.54:1 worst-case, still pink next to rose), or render the title in ink (colour-independent, 14.7:1) and let the brick rail and the sentence carry the error?** Default: the lightened token; it keeps `test_praxis_out_error_text_uses_the_error_token` as written.
5. **Dark code syntax: leave stock (D10 gives the designed syntax palette to Light only) or add a Dark syntax palette as a follow-up?** Default: leave it, file separately.
6. **A raised Dark output sheet (ground versus sheet depth as in Light, Option B): wanted?** Default: no; it reverses `test_dark_theme_has_no_cell_background` and four mapping tests.
7. **The Follow switch's off-state track is 1.84:1 in Dark (1.96:1 in Light; colour plus `aria-checked` are its only state cues): fix here or separately?** Default: separately.

---

## 10. What this changes in the epic spec (not edited here)

| Epic section | Change |
|---|---|
| Section 2, Non-goals: "A designed Dark variant (Dark gets token-mapped legibility only, D10)" | narrowed: Dark gets four token overrides and a framed viewer; a raised sheet and a themed viewer stay out |
| Section 2, "Next: Dark theme variant" | moved to done for the token half; syntax and viewer-theming remain |
| D3, "Consequence" and "Only moonstone, rose and brick stay brand constants" | brick (and the two ink tokens) become theme-overridable tokens; moonstone and rose stay constants; the inline light palette is unchanged |
| D10 | add the Dark block (N5654-1, -2, -6); "Makes the status rail ... theme-neutral" gains "with Dark token values" |
| D12, "Embed mode" | unchanged under O1; under O2, one sentence about the iframe filter |
| D16 unit table | D1-dark keys (`dark_brand_tokens_computed`, expected rail colours), D2 +2 keys, D4 +1 key, new unit `K3`; budgets from the D16 estimates, first-run rule applies |
| 3.1 Chrome | the rail colour list gains "in Dark: `ran` `#4393B8`, `error` `#D1523A`" |
| AC-4, AC-7, AC-26, AC-27, AC-39 | AC-4: new pin; AC-7: the Dark colour clause; AC-26: new key; AC-27: add the Dark set (pairs, hover, hairline) under B8's instrument; AC-39: negative (f) |
| AC-34 to AC-38 | note that they run in Light and K3 covers Dark |
| OQ-1 | unchanged (default stays Dark); the new open questions 1-7 above are added |
| Section 9 residual human checks | add H-dark: the Dark notebook and deck panel against `shots/` by a human, the moonstone-ink versus liquid reading, and the O2 pair if chosen |
| `DESIGN.md` | "Dark theme variant" removed from "Next"; a "Color (Dark)" table with non-colliding row names |
| Revision notes | a Revision recording the two registered runs, the role split (N5654-3) and the pin move |

---

## Appendix: the numbers (runs `07edfb7f`, `54fdb517`)

Worst case over three Dark surfaces and four visions. "dE" is CIEDE2000, worst vision.

| Set | brick | moonstone ink | rose ink | error title | rose-brick | hover (rose ink vs rose) | Verdict |
|---|---|---|---|---|---|---|---|
| P0 shipped | `#B3402A` 2.24 | `#2F6882` 2.55 | `#B8436A` 2.54 | `#CF6679` 3.81 | 21.9 | 17.0 | text and 3 marks fail |
| P1 marks at 3.0 | `#D1523A` 3.00 | `#347491` 3.01 | `#C05277` 3.03 | `#D47687` 4.54 | 13.8 | 13.1 | passes |
| P2 inks at 4.5, brick 3.5 | `#D5614B` 3.52 | `#4393B8` 4.50 | `#CE7794` 4.59 | `#D47687` 4.54 | **10.0** | **3.3** | passes the first run's bars; hover collapses |
| P2g searched brick | `#FF4F0F` 3.51 | `#4393B8` | `#CE7794` | `#D47687` | 13.9 | 3.3 | neon brick |
| P3 all at 4.5 | `#DB7865` 4.52 | `#4393B8` | `#CE7794` | `#D47687` | **4.6** | 3.3 | **fails** rose-brick |
| **Hybrid** | `#D1523A` 3.00 | `#4393B8` 4.50 | `#C05277` 3.03 | `#D47687` 4.54 | 13.8 | 13.1 | **passes all, incl. hairline 8.5-8.6 on each surface** |

Other pairs, hybrid: moonstone-brick 38.9, ran rail vs error rail 39.4, vs running rail 10.3, vs not-run rail 33.4; unchanged
pair moonstone-rose 9.5 (protan), which B8 already rescues with the filled-disk-versus-ring cue; moonstone ink vs moonstone 7.3.
In the same order, normal vision on `#12121E`: brick 4.40, moonstone ink 5.40, rose ink 4.17, error title 5.96.

Viewer (run `07edfb7f`, `viewer`): raw light ground against the Dark panel 15.63:1; filtered ground `#101417` against it 1.0:1.
Filtered contrast against the filtered ground: edge 13.37, selection 9.83, inner outline 8.18, tip 11.53, outer shell 2.08
(1.71 unfiltered, so no worse). Modelled with the Filter Effects hue-rotate matrix on sRGB values; not measured in a browser.
