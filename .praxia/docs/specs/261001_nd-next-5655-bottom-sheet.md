---
title: 'Notebook display, next: layouts below 1024 px (deck panel as a bottom sheet), increment draft'
description: 'Design for backlog #5655. Below 1024 px the deck panel becomes a full-width bottom sheet with a peek and an expanded height, as a third HOME of the existing widget (like the drawer), not a new D11 state. Grounded in dock.js, the K2 harness, the built JupyterLab bundle and the prototype CSS; options, decisions N5655-1..13, executable gates, tasks, risks and open questions.'
status: draft
task_id: 260929_notebook-display-design
date: '261001'
backlog_id: 5655
---
# Notebook display, next: the deck panel as a bottom sheet below 1024 px (backlog #5655)

> **Status: DRAFT, design only.** Base: branch `feat/notebook-display-sprint-c-stacked` @ `60d053f2`
> (PR #198, MVP done, not merged). No product code, test, CSS or workflow is touched by this
> document. It does **not** edit the epic spec (`260929_notebook-display-epic.md`); section 10
> lists what the orchestrator would amend if the user accepts it. Every claim carries a tag:
> **verified** (read at file:line, or probed), **spiked** (a throwaway run, command and result
> given), or **unverified** (a lead; the section 2 table says what would settle it). Browser
> facts are all **unverified** by this author (Chromium cannot start in this sandbox); section 7
> task SH-0 is the pre-registered browser spike set the orchestrator runs first.

---

## 1. Problem and current behaviour

**The item.** Backlog #5655: "Layouts below 1024 px (deck panel as a bottom sheet). MVP is desktop
>= 1280 px with a 1024-1279 drawer. Starting point: the prototype's bottom sheet with the deck plan
as its peek state. Must fit the D11 deck-panel state machine without new lifecycle states."
Epic text: D6 row "< 1024 px: Out of scope. The prototype's bottom sheet is the later starting
point" (epic line 285); Non-goals "Layouts below 1024 px" (line 1654); Next (line 1684); G6 names
">= 1024 px" (line 1635).

### 1.1 What happens below 1024 px today (verified)

| Fact | Evidence |
|---|---|
| `tierOf(w)` returns `"drawer"` for every `w < 1280`, 1023 included; `homeOf("drawer")` is `"drawer"`. | `dock.js:113-122`; pinned by `dock.test.js:277-284` (`tierOf(1023)` is `"drawer"`, comment "out of scope") |
| So below 1024 the panel is the same right-edge drawer: `position: fixed; right: 0; width: 480px; z-index: 900`, `top`/`bottom` read once at attach from `#jp-main-dock-panel`'s rect (fallback `0`/`0`). | `dock.js:810-842` (`drawerBox`, `applyDrawerStyle`) |
| **Spiked 261001:** a throwaway copy of `dock.test.js` with the drawer `describe` (13 tests) at width 800 and the random-sequence model (6 seeds x 400 events) crossing 1440 <-> 800 passes with today's code, and a direct probe at 400 / 800 / 1023 gives `{position: fixed, width: "480px", right: "0"}`, `home: "drawer"`. The lifecycle already works below 1024; only the geometry is wrong. At 400 px the 480 px drawer is 80 px wider than the window. Command: `OMP_NUM_THREADS=2 bun test web-repl/shell/display/dock.spike.test.js -t "drawer"` then `-t "random sequences"` then `-t SPIKE` (temp copy in the same directory with `width: 1152` -> 800; deleted afterwards, `git status` clean). | probe output above |
| `evaluateTier` returns at once when the tier string is unchanged, so 1100 -> 900 is not an event today, and would stay not one. A new boundary needs a new comparison. | `dock.js:1070-1080` |
| `rehome` is detach-then-attach for any home change: a DOM move, so a connected panel's iframe reloads once (T15). | `dock.js:1056-1068`, `892-910` |
| The body and the iframe both carry inline `min-height: 300px`; on a 500 px-high window a panel built on them cannot fit its box. | `dock.js:369, 495` |
| Escape hides the panel and the close button is shown only when `home === "drawer"`. A third home must extend both. | `dock.js:402, 440` |
| Every K2 viewport is >= 1152 px; no harness step, no unit test other than `tierOf(1023)` touches a width below 1024. The harness has no touch emulation (`has_touch`, `touchscreen`, `new_cdp_session` all absent). | `repl_smoke.py:6969-6977`; grep over `repl_smoke.py` and `dock.test.js` |
| The theme CSS may hold **exactly one** `@media` and **no** transition or animation. | `web-repl/tests/test_display_css.py:1554-1565` (one `@media (min-width: 1600px)`), NFR-6 test near `:1500` |
| `__tests__/fakes.js` has no `#jp-main-dock-panel`, no `setPointerCapture`, no `pointerType`. | grep of `fakes.js` |

### 1.2 What a sub-1024 viewport does to JupyterLab itself

Read from the built bundle at `~/projects/praxis/web-repl/dist` (main checkout, JupyterLite
app-lab 0.8.1, JupyterLab 4.6 packages, built 2026-08-28; **not** a build of this branch).

- **JupyterLab has no responsive shell** (verified in `build/jlab_core.*.js`). Its only narrow-width
  CSS is `@media (width <= 760px)` (cell toolbar hidden; `.jp-InputArea` becomes a column with the
  prompt above the editor; notebook footer margin; code-console input height) and a
  `max-width: 480px` rule. The shell is the desktop dock layout: menu bar, side bars, a main
  `DockPanel` inside a horizontal `RestorableSplitPanel`, inside a vertical one whose second child
  is the "down" area (`#jp-down-stack`). Narrow handling in code is limited to `ReactiveToolbar`
  (toolbar overflow popup; verified present). Whether the menu bar copes at 600 px is unverified.
- **The left area keeps `min-width: var(--jp-sidebar-min-width)`** whenever open (rule verified;
  the value, 250 px by JupyterLab's default, is unverified here), and the file browser is open at
  load (the harness has to collapse it for the >= 1600 steps: `repl_smoke.py:8645`, `leftCollapsed`).
  At 760 px that leaves the notebook roughly 480 px, below the D6 figure of 710 px for the
  file-browser-open 1280 case; D5's detail floor engages earlier. Unverified in a browser.
- **The Praxis chrome interacts with the 760 px rule.** The theme zeroes the prompt's width
  (`praxis-theme.css:544-556`); JupyterLab's `<= 760px` rule turns the input area into a column.
  Whether a zero-width prompt then costs a blank line above each cell is unverified. This is a
  notebook-chrome question, not a sheet question (risk R4).
- `lab/index.html` carries `<meta name="viewport" content="width=device-width, initial-scale=1">`
  (verified), so a tablet or phone reports its real CSS width.

**Does JupyterLab "support" it?** It runs; it is not designed for it. No official-support
statement was checked (no network). The honest scope is therefore "the sheet must be correct on
whatever JupyterLab lays out", and the supported, gated range is 760-1023 px (D-N5655-10).

### 1.3 What the viewer iframe and the drag guard imply for a sheet (verified unless tagged)

- The panel holds **one** iframe, only in `open-connected` (I1). A sheet that "minimises" by
  removing or hiding-by-removal the iframe would break I1 or add a state. A sheet that only changes
  the iframe's CSS box keeps both: the page observes its viewport with a `ResizeObserver` and
  re-sizes without reloading (`visualizer3d/renderer.js:268-291`).
- `OrbitControls` sets `touch-action: none` on the canvas (`vendor/OrbitControls.js:478`):
  one finger rotates, two dolly/pan. A one-finger drag **inside** the expanded iframe is the
  viewer's, so the sheet's own drag must live on a dedicated grip, never on the iframe.
- The drag guard (`dock.js:534-590`) freezes the iframe (`pointer-events: none`, previous inline
  value remembered and restored) from a `pointerdown` on `lm-DockPanel-handle` or
  `lm-SplitPanel-handle` until `pointerup`, `pointercancel`, window `blur` or teardown, because the
  iframe flush against a handle took the drag stream. **A sheet grip is not a Lumino handle, so it
  is not guarded today.** The same cross-document stealing applies to a drag that moves over the
  iframe. Two protections are available and both are specified (N5655-6): the grip's own pointer
  capture (unverified across a cross-document iframe) and adding the grip class to the guard (the
  verified mechanism).
- **Do not make the peek inert through the iframe's inline `pointer-events`.** The guard remembers
  "previous inline value" at the press and puts it back at the release. A press on the grip while
  the iframe is inline-inert (peek) records `none`; if the drag ends in the expanded mode, the
  release restores `none` and the expanded viewer is dead. Peek inertness is a transparent cover
  element over the body (N5655-5), which touches no iframe style.
- **Touch and Lumino.** Lumino's `SplitPanel` and `DockPanel` use `pointerdown` on the handle and
  `pointermove`/`pointerup` on `document`, and listen for no `pointercancel`; the only
  `touch-action` rule in the Lumino CSS is `.lm-TabBar-tab` (verified in the bundle). On a touch
  device the browser may therefore claim a vertical drag of a Lumino handle for scrolling and send
  `pointercancel`: unverified, and a pre-existing gap for tablets at >= 1024 (R8), not this item.
  A sheet built outside Lumino (a fixed node on `document.body`, like the drawer) does not depend
  on any of it.
- Pressing a Lumino handle (e.g. the left side-bar splitter) while the sheet is up still freezes
  the iframe through the existing guard; nothing changes there.

### 1.4 The prototype's bottom sheet: what is reusable

`web-repl/design/notebook-display/display.css:480-497`, `display.js:336-412`, `DESIGN.md` "Layout".

| Prototype | Reuse? |
|---|---|
| `@media (max-width: 1100px)`: `.dock` fixed, `left/right/bottom: 0`, `height: 340px`, `border-top: 1px solid var(--rail)`, top corners 12 px, `.scrub { display: none }` | **Idea only.** Full-width bottom anchoring, the hairline and hiding the scrub (here: the motion slot) carry over. The breakpoint is 1024 in the epic, not 1100; the rule cannot be a CSS `@media` in `praxis-theme.css` (`test_display_css.py:1554`); 12 px top corners differ from DESIGN.md "Shape" (software surfaces 8 px). |
| `.notebook { padding-bottom: 380px }` | **Idea carries over** as a computed inset (N5655-8): without it the last cell cannot scroll above the sheet. |
| One fixed 340 px height | **No.** There is no peek and no expanded state, no handle, no gesture and no touch handling in the prototype; "peek" exists only in `DESIGN.md` prose. |
| "Deck plan" in the dock = `deckFigure(...)` SVG, shown only when no `?viewer=` is given (`display.js:341-345`) | **No second renderer.** The shipped dock has no plan figure; the viewer's **Top** preset (orthographic, `VIEWS.top`, `renderer.js:117-121`) is the plan (N5655-5, OQ-A). |
| `.dock__frame` negative-offset crop | **No.** Superseded by `embed.css` (hides chrome from inside the page). |

---

## 2. Assumptions

| # | Assumption the design leans on | Tag | Evidence / spike |
|---|---|---|---|
| A1 | Below 1024 the panel is today's 480 px right drawer and the D11 lifecycle already holds there. | verified + spiked | section 1.1; bun spike (13 + 6 pass, probe at 400/800/1023) |
| A2 | `tierOf`/`homeOf` can stay as they are if the home decision moves to a new pure function; no existing assertion needs editing. `homeOf` has no direct test. | verified | `dock.test.js:277-284`; grep `homeOf` in tests finds nothing else |
| A3 | `snapshot()` consumers use `toMatchObject`, so a new `sheetMode` key breaks no test. | verified | `dock.test.js:474,486,505,529,614`; the K2 harness reads `snapshot()` through `window.__praxisDisplay` (`repl_smoke.py:8137`), no product switch needed |
| A4 | The theme CSS cannot gain a second `@media` or any transition; sheet layout therefore lives in dock.js inline styles, as the drawer's does. | verified | `test_display_css.py:1554`, NFR-6 test |
| A5 | JupyterLab is not responsive below 1024; 760 px is its only breakpoint. | verified (bundle of the main checkout's dist) | section 1.2 |
| A6 | The LabShell has a Lumino "down" area (`_addToDownArea`, `_showDownPanel`, `_vsplitPanel`) that a widget can be added to. | verified (read) | `jlab_core.*.js`; behaviour in a browser unverified |
| A7 | The page re-sizes on its viewport `ResizeObserver` with no reload and `OrbitControls` owns canvas touch. | verified (read) | `renderer.js:268-291`, `OrbitControls.js:469-478` |
| A8 | The Top view frames the whole deck legibly in a wide, short (about 768 x 112) strip, and re-sizing from tall to short keeps it complete. The orthographic frustum height is set from the distance, not re-fitted on resize (`sizeOrthographic`), so a shorter viewport shrinks the drawing; completeness depends on the strip's aspect against the deck's. | **unverified** | spike **S-sh-1** (screenshot of the strip; `canvas_nonblank`; `camera().distance` unchanged across peek <-> expanded) |
| A9 | A drag started on the grip keeps receiving moves over a cross-document iframe, via `setPointerCapture` (touch pointers are implicitly captured; a mouse needs the call). | **unverified** | spike **S-sh-2**; the guard-class route (verified mechanism) is specified regardless |
| A10 | Playwright/CDP touch (`Input.dispatchTouchEvent`) honours `touch-action`, i.e. a vertical touch drag on an element **without** `touch-action: none` produces `pointercancel`, and with it does not. If it does not, the touch-drag key is insensitive and must not be a gate. | **unverified** | spike **S-sh-2**, both arms, before any K3b code |
| A11 | After a pointer drag that ends over the capturing element a `click` is still dispatched to it, so a drag that snaps on `pointerup` also toggles on the `click` unless suppressed. | unverified (standard behaviour) | gate `drag_up_expands_once` plus its mutant; spike **S-sh-2** records it |
| A12 | Padding-bottom on `.jp-WindowedPanel-outer` (`overflow: auto; height: 100%`, class verified) extends the notebook's scroll range under the windowing logic. | **unverified** | spike **S-sh-3** (`last_cell_clears_sheet` with and without) |
| A13 | The harness can run a context with `has_touch=True` plus mouse and keyboard in the same unit. | unverified (Playwright API) | `DockSession` creates its context at `repl_smoke.py:5280`; SH-5 adds the option |
| A14 | The CI job has headroom for two more units: step timeouts today sum to 92 min of 137 (`repl.yml:55`). | verified for the sum; headroom unverified | `repl.yml:186-256` |
| A15 | z-index 900 clears the notebook and the dock; JupyterLab menus and dialogs sit above it (the drawer already uses 900). | unverified for the sheet | gate `sheet_geometry` does not cover it; R14 |

---

## 3. Options

| | Idea | Browser-gate cost | Verdict |
|---|---|---|---|
| **A. Fix only** | Keep the drawer for all < 1280, change `width` to `min(480px, 100%)`. | One K2 step at e.g. 800 x 600 (about 40 LOC harness, no new unit). | Does not deliver the item: no peek, the drawer still covers 60-100% of the window, right-anchored on a window that is wider than tall only by accident. Kept as the **fallback** if the user declines the sheet. |
| **B. Overlay sheet (recommended)** | A third home of the same widget node, `position: fixed` on `document.body` like the drawer, full width, bottom-anchored inside the dock box; two heights (peek, expanded) as a presentation mode; a grip button with tap/keyboard and optional drag. | **New units K3a and K3b** (Pyodide boot each; about 12 and 10 min budget), a `has_touch` context and CDP touch, 3 pre-registered spikes, about 6 sensitivity mutants (each re-runs only its own unit). | Matches the prototype and the item; no Lumino dependence; lifecycle untouched. |
| **B'. Same, geometry in theme CSS** | Same as B but laid out by a `@media (max-width: 1023px)` rule with `!important` over the drawer's inline styles. | Same units; plus a `test_display_css.py` change. | Rejected: a second `@media` breaks `test_display_css.py:1554` (would have to be loosened), and layout would live in two places (JS inline plus CSS `!important`). |
| **C. Lumino down area** | `app.shell.add(widget, "down")`: the panel lives in the bottom tab panel; size via the shell's private `_vsplitPanel.setRelativeSizes`. | Reuses K2's mouse-drag machinery; touch on a Lumino handle likely needs a `touch-action` rule (A10-like spike); sizing through a private API needs a recorded S1-style capability case; a split <-> down re-home is a DOM move (one reload). | Rejected as the default. It **reflows** the notebook (the bottom panel takes layout space from the whole main area, including under the file browser); it adds a second tab bar over our header; peek/expanded need private-API sizing; the down area is shared with user widgets. Verified to exist (A6), so it remains the answer if the user prefers a docked bottom panel to an overlay (OQ-K). |
| **D. Full-screen takeover** | Below 1024 the panel covers the whole dock box; close to return. | Tiny: one step, no drag, no touch. | Rejected: the notebook is gone, which defeats Follow ("the cell you are working in"); but it is the cheapest honest fallback after A. |

**Cost in gates, in words.** B adds two real-browser units (K3a about 10-12 min, K3b about 8-10 min;
step timeouts budget+2, `repl.yml` pattern), two AC-42 table rows, one CI step each, one harness
context option and a CDP touch driver. It adds no change to K1a, K1b or K2 (their viewports are
>= 1152 and the drawer code path is not edited). Sensitivity: mutants run through the tracked
sensitivity driver, each re-running only the one unit it targets (D16).

---

## 4. Recommendation

Build **Option B in two stages**.

- **Stage 1 (SH-1..SH-6): the sheet with tap, keyboard and computed geometry**, no drag. Everything
  load-bearing: the home, in-place overlay re-homing, the peek strip (live viewer, Top preset), the
  grip button, the cover, the notebook inset, the height rules, K3a. Touch works by tap.
- **Stage 2 (SH-7, SH-8): drag**, gated on spike S-sh-2 showing that the touch-drag key is
  sensitive (A10). If it is not, drag ships mouse-only with a human touch check in the epic's
  residual-checks list, not a gate that cannot fail.

The sheet is a **home**, exactly as the drawer is. No D11 state, row or invariant is added.

---

## 5. Proposed decisions

Each follows the epic's D-style: statement, reason, and mapping onto D11.

**N5655-1. The home is chosen by window width through a new pure function; `tierOf` and `homeOf`
are untouched.** `homeOfWidth(w)`: `w < 1024` -> `"sheet"`, `w < 1280` -> `"drawer"`, else
`"split"`. `tier` (wide/medium/drawer) stays the **sizing** tier for the split; the home decision
and the early-return in `evaluateTier` compare the home as well as the tier. *Reason:* the
existing assertion `tierOf(1023) === "drawer"` stays true and untouched (A2); one place decides
the home. *D11:* the "tier crossing" event is generalised from "crosses 1280" to "changes the
home" (crossing 1280 or 1024); T10, T15, T21 are its rows.

**N5655-2. The sheet is a third home of the same widget node, not a state; `peek | expanded` is a
held presentation value.** Same host as the drawer (`document.body`, fixed). `sheetMode` is
in-memory only (no storage key, D14), initial `peek`, written only by the grip, the cover and the
drag; no D11 transition reads or writes it, it never touches the iframe, `src`, `query` or `seen`.
It sits with `preset` and `follow` (both held presentation values with no lifecycle effect, D12).
`snapshot()` gains `sheetMode` (`null` outside the sheet) and `home` may be `"sheet"`; nothing
else on the controller changes. *Reason:* "without new lifecycle states" (the item). *Why no new
state is needed:* the only candidate was a minimised bar with the iframe dropped or hidden, which
breaks I1 or adds a state; there is no minimised height (close is the minimum, T17).

**N5655-3. Re-homing between overlays is an in-place restyle; any move to or from the split is a
DOM move.** drawer <-> sheet: rewrite inline styles on the same node, no `removeChild`, no
`app.shell.add`, no reload. sheet <-> split: `detachPanel` then `attach`, exactly the existing
T15 path (one reload, same `src`, no `query`). *Reason:* the same node is already on `body`;
avoiding the move is free and removes a reload. *D11:* T10, T15, T21 say "re-home the panel";
T15's parenthesis "one reload" describes a DOM move and is amended to "(a DOM move reloads once;
an in-place restyle does not)". I2 is untouched (no `src` write on any re-home).

**N5655-4. Geometry is inline and recomputed on every window resize while an overlay is up.**
Sheet: `position: fixed; left: 0; right: 0; top: auto`; `bottom` and the available height from
`drawerBox()` (the dock panel's rect, so the menu bar and status bar are never covered); `z-index:
900`; top border one rail hairline (`var(--jp-border-color1)`), top corners 8 px; no shadow
sideways. Clear every style key the previous home set (a stale `height` or `width` is the failure).
Peek strip `112 px` of body; header unchanged; footer shows the focus line only (motion slot
hidden in peek, "collapses first", D6). Expanded height `min(box - 56, 720)` px. The body's and
the frame's inline `min-height: 300px` are overridden to `0` while the home is the sheet and
restored on leaving. A window `resize` re-applies the geometry while `home` is an overlay (rotation
changes the height without changing the home). No `@media`, no transition (A4): the snap is
instant. *D11:* none; presentation.

**N5655-5. The peek shows the live viewer, Top preset by default, through a cover; there is no second
renderer.** The one iframe stays laid out at strip size (not `display: none`: a 0 x 0 page would
re-frame on expand, A8). In peek a transparent `<button class="praxis-deck-panel__peek-cover">`
(`tabindex="-1"`, `aria-hidden="true"`, pointer-only) sits over the body and expands on tap;
the iframe's own inline style is never written. *Reason:* the cover keeps the guard's restore
logic safe (section 1.3) and the iframe count at one. *D11:* I1 holds (the cover is not an
iframe), I5 holds (waiting/lost texts show in peek; the body scrolls if the strip is short).

**N5655-6. The grip is a real button first; drag is an enhancement with two snap points.**
`<button class="praxis-deck-panel__grip" aria-expanded aria-controls=<body id>>`, 28 px tall,
full width, accessible name "Expand the deck panel" / "Collapse the deck panel"; click, Enter and
Space toggle. Drag (Stage 2): `pointerdown` on the grip with `button 0` or any touch;
`setPointerCapture`; `touch-action: none` and `user-select: none` on the grip; `contextmenu`
stopped on the grip (so a long press does not open JupyterLab's menu); an 8 px threshold; while
dragging the sheet moves by `transform: translateY` only (no `height` or `bottom` writes, so the
iframe sees no resize storm); on release it snaps to the nearer of the two heights; `pointercancel`
or window `blur` reverts to the pre-drag mode; a `click` that follows a drag is swallowed (A11).
The grip's class joins `HANDLE_CLASSES` so the existing guard freezes the iframe for the press
(additive; the guard's tests are untouched). *D11:* none.

**N5655-7. Opening and closing follow D11 with the held mode.** T2 and T4 attach the sheet in the
held `sheetMode` (initially `peek`); close (T7, T17, T22) removes it and keeps the mode in
memory; the toggle command is unchanged. The close button shows in both overlays; **Escape with
focus inside** closes (T7, T17, T22) in both overlays, in both modes, as for the drawer (D6). *Why
peek on the first announce:* it is a side effect of the user running `dock()`, and the notebook
must stay usable. OQ-C asks whether the explicit toggle should open expanded.

**N5655-8. The notebook gets a bottom inset, never a width change.** While the sheet is the
home, dock.js sets `--praxis-sheet-inset` on `document.documentElement` to the peek height and
removes it on leaving the sheet or closing; one non-`@media` theme rule consumes it
(`.jp-NotebookPanel .jp-WindowedPanel-outer { padding-bottom: var(--praxis-sheet-inset, 0px) }`),
subject to A12/S-sh-3. The inset is the **peek** height in both modes, so expanding does not jump
the scroll position. `drawer_no_reflow`'s analogue holds: width unchanged.

**N5655-9. Heights.** The D6 height rule (viewer >= 300 px at 800 high; motion slot <= 36 px,
collapses first) stays a desktop-tier statement. For the sheet: peek strip 96-160 px; expanded
viewer >= 300 px at 768 x 1024; the sheet always lies inside the dock box. Heights < 500 px are
out of the gated range (no clip, no overflow outside the box is still asserted at 760 x 500).

**N5655-10. The supported, gated range is 760-1023 px wide, >= 500 px high.** 760 is JupyterLab's
own mobile breakpoint. Narrower, the sheet works (it is full width) but the notebook is
JupyterLab's mobile layout (R4) and nothing there is gated. Phone portrait is not a target (Pyodide
plus WebGL); the item's realistic users are a narrow desktop window and a portrait tablet.

**N5655-11. Width only.** The sheet is chosen by width, not by `pointer: coarse`: a touch tablet at
1024-1365 keeps the drawer or the split. (Touch-resizing the split handle there is R8.)

**N5655-12. The sheet spans the whole window width.** It covers the bottom of the side bars when
they are open; it does not collapse the user's file browser (OQ-H).

**N5655-13. No new product test switches.** Gates read `snapshot()` (now with `sheetMode`) and the
DOM through `window.__praxisDisplay` as K2 does; AC-39(c)'s grep is unchanged.

### 5.1 Mapping onto D11 (T1-T27, I1-I6): no new state, row or invariant

| Rows | Effect of the sheet |
|---|---|
| T1 mount | `syncTier` also computes the home. Nothing else. |
| T2, T4 (attach in "the current tier's home") | "home" now ranges over split, drawer, sheet. Attach reads `sheetMode`, does not write it. |
| T3, T5, T8, T9, T13, T20, T23, T24 (no action) | Unchanged. T5 also covers a 1024 crossing while closed. |
| T6, T11, T18, T27 (iframe create / retarget / same id) | Unchanged. They run inside whichever home. |
| T7, T17, T22 (close panel) | Sheet detaches like the drawer; inset removed; mode kept. |
| T10, T15, T21 (tier crossing) | Generalised event: "the window changes home" (1280, and 1024). overlay <-> overlay: in-place, zero reloads; to/from split: the existing DOM move. |
| T12, T14, T19, T25, T26 (kernel close, plr:gone, restart) | Unchanged; home-independent. |
| T16 (iframe reload) | Unchanged. |
| I1 | Holds: peek never removes or hides-by-removal the frame; the cover is not an iframe. |
| I2 | Holds: expand, collapse, drag, rotation and overlay <-> overlay write no `src`. |
| I3, I4, I6 | Untouched. |
| I5 | Holds: the two texts show in peek and expanded. |
| New "events" (expand, collapse, drag, resize in the sheet) | Presentation events with the same status as Follow and Iso/Top/Front clicks: no state change. They are not added to the event list. |

---

## 6. Acceptance criteria

IDs `AC-SH-n`. Local runs are narrow (one file, one `-k`); `OMP_NUM_THREADS=2`; Python
`uv run --no-sync`. Browser units run with the sandbox disabled, per the epic's local-runs note;
CI is authoritative.

### 6.1 bun, no browser (extend `web-repl/shell/display/dock.test.js` and `__tests__/fakes.js`)

Run: `OMP_NUM_THREADS=2 bun test web-repl/shell/display/dock.test.js -t "sheet"`; the existing
suites with `-t "drawer"`, `-t "drag guard"`, `-t "random sequences"`, and finally the whole file.

| AC | Claim | Positive control | Negative control (must fail) |
|---|---|---|---|
| AC-SH-1 | `homeOfWidth`: 1023 sheet, 1024 drawer, 1279 drawer, 1280 split; `tierOf` assertions at `:277-284` pass **unchanged**. | the four boundary pairs | mutants patched into a temp copy of dock.js (the file's existing pattern: each anchor matches once): `< 1024` -> `<= 1024`; `< 1280` -> `< 1279` |
| AC-SH-2 | Attach at 900: `position: fixed`, `left 0`, `right 0`, `bottom` from the dock rect, no `width: 480px`; leaving for the drawer clears `left`, `height`, `transform`, `min-height` overrides; leaving for the split clears all overlay keys; inline `min-height: 300px` restored. | geometry equals the fake dock rect | mutant that does not clear `height`: the drawer ends with a stale height |
| AC-SH-3 | Lifecycle independence: the existing random-sequence model (unchanged `step`) with crossings drawn from 1440 / 1152 / 900 plus `expand`, `collapse`, grip click, `resize` events: after every event `assertInvariants` (I1-I6), `srcWrites` equals the model's, `queries` equals the model's, and the home equals `homeOfWidth(width)`. Seeds 1-6 x 400. One test per row that names a home at 900: T2, T4, T6, T7, T10, T15, T17, T21, T22. | the model agrees | mutant whose `expand` writes `src` (I2 fails); mutant whose cover is an `iframe` (I1 fails) |
| AC-SH-4 | overlay <-> overlay is in place: iframe element identical, panel node never removed (counted `removeChild`/`appendChild`), `app.shell.addCalls` unchanged, `srcWrites` unchanged. sheet <-> split: iframe element identical, `addCalls` +1, `src` unchanged (T15). Closed stays closed across 1024 (T5). | both paths | mutant `rehome` that detaches for overlay -> overlay (identity holds but `removeChild` count rises) |
| AC-SH-5 | Grip and cover: grip is a `button`, `aria-expanded` mirrors `snapshot().sheetMode`, name flips; click and Enter/Space toggle; cover exists only in sheet + peek, is `aria-hidden` and `tabindex -1`, is not an iframe; the frame's inline `pointer-events` is `""` in peek; `sheetMode` survives close -> reopen and is `null` outside the sheet; Escape with focus inside closes in both modes; Escape elsewhere does not. | each assertion | mutant that sets the frame inert in peek, run with the scenario "press the grip in peek, release in expanded": the frame is left `none` and the test fails |
| AC-SH-6 | Drag (Stage 2): below 8 px = click only; past 8 px up from peek = expanded on release; the `click` after a drag is swallowed (net one change); `pointercancel` and `blur` revert; `setPointerCapture` called with the pointer id; zero `height`/`bottom` writes during moves; the iframe is inert during the press and restored (previous value kept, as the guard tests do) after `pointerup`, `pointercancel`, `blur` and teardown mid-press; no listener leak after `dispose()`. | each | mutants: no capture; no click swallow (double toggle); no cancel handler (stuck); grip class absent from the guard; per-move `height` write |
| AC-SH-7 | Inset: `--praxis-sheet-inset` set to the peek height in the sheet (both modes), removed on closing, on leaving for drawer/split, and on `dispose()`. | set / removed | mutant that never removes it |
| AC-SH-8 | Regression: the whole of `dock.test.js` passes with no existing test edited (the drag-guard probes `probeIgnoresNonHandles` etc. included). | green | n/a (this is the no-loosening gate; `git diff` on the file shows additions only) |

### 6.2 pytest, no browser

| AC | Claim | Command |
|---|---|---|
| AC-SH-9 | K3a and K3b are in the one unit table (id, check, budget, listed keys, viewports, `has_touch`); `derive_k3a_keys` and `derive_k3b_keys` are pure with a **positive and a negative raw evidence set for every key**; the keys are in the aggregate; the workflow has one step per unit with `timeout-minutes` budget+2 (AC-42). | `OMP_NUM_THREADS=2 uv run --no-sync pytest web-repl/tests/test_repl_smoke_resume.py -k "k3"`; then `web-repl/tests/test_repl_workflow_scenarios.py`; then `web-repl/tests/test_nd_sensitivity_driver.py -k sheet` (one file per process) |
| AC-SH-10 | Theme CSS: grip, cover and inset rules exist, use tokens, add no `@media` (the file still has exactly one), no transition/animation, no removed outline. A new test pins the inset rule's selector. | `uv run --no-sync pytest web-repl/tests/test_display_css.py` (whole file, **unchanged tests pass**) |

### 6.3 Real browser, `--dock-check` (orchestrator / CI). Each unit is atomic with its own stamp, budget and `--out-dir` (D16).

**K3a** (new, `AC-SH-11`, 12 min): one page, one kernel, one `dock()`; starts at 768 x 1024; every
viewport change is `set_viewport`; later opens by `praxis:toggle-deck-panel`. Mouse and keyboard only.

| Key | Claim | Positive control | Negative control |
|---|---|---|---|
| `sheet_geometry` | at 768 x 1024 after the first announce: home `sheet`, fixed, `left 0`, width = `innerWidth`, bottom edge = dock-panel bottom (+-1), top >= dock-panel top, one iframe, strip height in [96, 160], peek total <= 45% of the box | the real run | the **same predicate applied to the 1152 evidence** of `sheet_drawer_inplace` (a right-anchored 480 px drawer) must be false; plus pure raw sets |
| `peek_draws` | `resources()` non-empty; canvas non-blank in the strip (the AC-34 screenshot count, with its two synthetic controls: all-ground reads 0, 5%-marked reads above threshold); camera direction matches `VIEWS.top` (> 0.99) | AC-34's controls | the all-ground synthetic image |
| `sheet_no_reflow` | notebook content width unchanged by opening, +-0.5 px | real | pure raw with a 40 px change |
| `last_cell_clears_sheet` | after scrolling to the end, the last cell's bottom <= the sheet's top (+-1) | real | **dist mutant N-inset**: theme rule removed; the key must fail |
| `expand_collapse_click` | real click on the grip: expanded (height = expected, `aria-expanded` true, expanded viewer >= 300 at 768 x 1024); click again: peek; the **same iframe element**, zero iframe `load` events (harness `MutationObserver`, AC-36 `iframe_reloads_during_resize` style), `src` unchanged, `resources()` non-empty | real | pure raw with one extra load; **dist mutant N-reload**: expand replaces the frame |
| `sheet_drawer_inplace` | 768 -> 1152 -> 768 with the panel open: home drawer / sheet, same element, **0 loads**, same `src`, `resources()` non-empty | real | **dist mutant N-detach**: overlay -> overlay detaches; loads >= 1 |
| `sheet_split_rehomes` | 768 -> 1440: home split, `panel_is_split_right`, same `src`, `resources()` repopulates within 10 s (T15); back to 768: sheet; with the panel closed, 768 -> 1440 stays closed (T5) | real | pure raw: split without `src` kept |
| `sheet_dismiss_reopen` | close button (T17), toggle (T4 -> T6), Escape with focus on Follow (T17), toggle; `sheetMode` kept across | real | pure raw: iframe left after close |
| `sheet_text_visible` | after `viewer.stop()` (T12) the no-viewer text lies inside the strip, `scrollHeight <= clientHeight`, at 768 x 1024 | real | pure raw with a clipped text |
| `sheet_fits_small` | at 760 x 500 expanded: the sheet's rect is inside the dock box on all four sides | real | pure raw with a sheet taller than the box |
| `sheet_follows_resize` | 900 x 600 <-> 600 x 900 (both sheet): bottom edge stays at the dock bottom; height recomputed | real | **dist mutant N-stale**: no resize refresh; the key must fail |
| `pageerrors` | `[]` | AC-34's | n/a |

**K3b** (new, `AC-SH-12`, 10 min, Stage 2; context `has_touch=True`, mouse still works): touch is
Playwright `touchscreen.tap` and CDP `Input.dispatchTouchEvent` for drags (the harness gains a CDP
session; Chromium-only, as the harness already is).

| Key | Claim | Positive control | Negative control |
|---|---|---|---|
| `tap_expand_collapse` | a real tap on the grip toggles twice, iframe untouched | real | `tap_elsewhere_inert`: a tap on a notebook cell leaves `sheetMode` unchanged |
| `drag_up_expands_once` (mouse, then touch) | a 120 px upward drag from peek ends expanded and the final mode is stable 300 ms later (no second toggle from the trailing `click`) | real | **dist mutant N-click**: swallow removed; the final mode is `peek`; the key must fail |
| `drag_touch_not_cancelled` | the touch drag delivers >= 80% of its sent moves to the grip and no `pointercancel` | real | **dist mutant N-touch-action**: `touch-action: none` removed. **Valid only if S-sh-2 shows this mutant fails the key**; otherwise drop the key and list a human touch check |
| `drag_over_iframe_completes` | a drag that starts on the grip and moves over the iframe region still ends the drag (grip receives the release; mode snapped) | real | **dist mutant N-capture**: neither pointer capture nor the guard class; the iframe takes the stream and the key must fail |
| `drag_cancel_reverts` | a `pointercancel` mid-drag restores the pre-drag mode and a live iframe | real | pure raw: mode left half-way |
| `iframe_reloads_during_drag` | 0 `load` events over every drag | real | as `expand_collapse_click` |

**Every key above is also covered by a pure `derive_k3*_keys` test with a passing and a failing raw
set (AC-SH-9)**, so a key that cannot fail is caught without a browser. Dist mutants run through the
tracked sensitivity driver, each in its own `/tmp/claude-1000/nd-neg/<name>/{dist,out}`, one unit
each, pre-registered with a committed `.bth.toml` before the run (epic AC-39). **Regression gate
`AC-SH-13`:** K1a, K1b and K2 pass unchanged (the drawer path at 1152-1279 is not edited).

---

## 7. Task decomposition (tests first; every task commits RED then GREEN)

| ID | Task | Files | ~LOC | Depends | Browser? |
|---|---|---|---|---|---|
| SH-0 | Pre-registered browser spikes (sidecars committed first): **S-sh-1** peek strip: screenshot, `canvas_nonblank`, `camera().distance` across a tall -> short -> tall CSS resize of the iframe; **S-sh-2** pointer facts: (a) `touch-action` present/absent arms under CDP touch (A10), (b) pointer capture over the iframe (A9), (c) trailing click after a drag (A11), (d) Lumino split handle under CDP touch (R8, informational); **S-sh-3** `padding-bottom` on `.jp-WindowedPanel-outer` extends scroll range (A12). | `scripts/spikes/261001_nd_sheet_*.py` + `.bth.toml` (3 each) | 3 x ~110 | none | **yes** (orchestrator) |
| SH-1 | RED: AC-SH-1, 2, 4 (home, geometry, in-place vs move) + `fakes.js` additions (`#jp-main-dock-panel` rect, recorders for `removeChild`/`appendChild`). GREEN: `homeOfWidth`, `isOverlay`, `applySheetStyle`/`clearSheetStyle`, `rehome` and `evaluateTier` comparing the home, resize refresh, Escape and close-button conditions extended. | `dock.test.js`, `__tests__/fakes.js`, `dock.js` | tests ~260, fakes ~50, src ~120 | none | no |
| SH-2 | RED/GREEN: AC-SH-3 (extend the random model's crossings and events) and the T-row tests at 900. | `dock.test.js` | ~140 | SH-1 | no |
| SH-3 | RED/GREEN: AC-SH-5, 7 (grip, cover, `sheetMode`, snapshot key, inset variable, min-height overrides). | `dock.test.js`, `dock.js` | tests ~180, src ~90 | SH-1 | no |
| SH-4 | Theme CSS: grip look (tokens only), cover rule, inset rule; AC-SH-10 pins them. Gated on S-sh-3 for the inset selector. | `praxis-theme.css`, `test_display_css.py` (additions) | css ~45, test ~50 | SH-3, S-sh-3 | no (S-sh-3 yes) |
| SH-5 | Harness: K3a rows in the unit table, `derive_k3a_keys` + controls, `DockSession` option for `has_touch`, driver methods (`click_grip`, sheet facts), AC-42 workflow test rows. | `scripts/repl_smoke.py`, `web-repl/tests/test_repl_smoke_resume.py`, `test_repl_workflow_scenarios.py` | src ~260, tests ~260, 20 | SH-3 | scenario body real-browser |
| SH-6 | CI step for K3a; sensitivity: pre-register then run N-inset, N-reload, N-detach, N-stale. | `.github/workflows/repl.yml` (one step), `scripts/spikes/261001_nd_sensitivity_sheet.py` + `.bth.toml`, `test_nd_sensitivity_driver.py` | ~30, ~180, ~60 | SH-5 | **yes** (orchestrator runs; CI step) |
| SH-7 | Stage 2 RED/GREEN: AC-SH-6 (drag, pointer capture, threshold, click swallow, cancel, guard class). | `dock.test.js`, `dock.js` | tests ~200, src ~90 | SH-3, S-sh-2 | no |
| SH-8 | Stage 2 harness: K3b, CDP touch driver, derive + controls, CI step, mutants N-click, N-touch-action (only if S-sh-2 allows), N-capture. | `repl_smoke.py`, tests, `repl.yml`, sensitivity script | src ~200, tests ~200, ~40 | SH-5, SH-7, S-sh-2 | **yes** |
| SH-9 | Epic spec amendments (section 10), after the user answers section 9. Orchestrator. | epic spec | docs | all | no |

Estimated total: about 1.4k LOC of tests, 0.7k of product and harness code, 0.4k of spikes and
sensitivity; stage 1 (SH-0..SH-6) is about two thirds of it.

---

## 8. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | CDP touch does not honour `touch-action`, so the touch-drag key cannot fail. | S-sh-2 both arms **before** SH-8; if insensitive, drop the key and add a human touch check to the epic's residual checks. |
| R2 | The Top view in a 768 x 112 strip is illegible or cropped (A8). | S-sh-1; the strip height (112) is a constant to tune; gate asserts a range and `canvas_nonblank`, not pixels. Fallback: the strip hosts the focus line only until expanded (the iframe stays, in a taller box). |
| R3 | The inset does not extend scroll range under windowing (A12). | S-sh-3; alternative `margin-bottom` on `.jp-WindowedPanel-inner`; `last_cell_clears_sheet` with its mutant keeps either honest. |
| R4 | Below 760 px JupyterLab's mobile CSS plus the theme's zero-width prompt may add a blank line per cell, and the 250 px side bar leaves about 480 px for the notebook (D5 floors engage). Notebook chrome, not sheet. | Out of the gated range (N5655-10); list as a follow-up; the sheet itself is width-independent. |
| R5 | The sheet covers the side bar's lower part and a cell being edited near the bottom. | The inset; OQ-H. |
| R6 | Pointer capture across a cross-document iframe may not route (A9). | The guard class is the verified mechanism; capture is belt and braces; `drag_over_iframe_completes` + N-capture decide. |
| R7 | System gestures (edge swipes) cancel the pointer mid-drag. | `pointercancel` reverts (AC-SH-6, `drag_cancel_reverts`). |
| R8 | Lumino split handles are probably not touch-draggable at 1024-1365 (no `touch-action`, no `pointercancel` handling). Pre-existing, not this item. | S-sh-2(d) records it; backlog candidate: `.lm-SplitPanel-handle { touch-action: none }` in theme CSS. |
| R9 | The two theme-CSS tests (one `@media`, no transition) could be tripped by new CSS. | Decisions N5655-4/6 avoid both; AC-SH-10 runs the whole file unchanged. |
| R10 | On-screen keyboard: with a cell in edit the fixed sheet can sit under the keyboard or over the cursor line. | Inset covers the peek; behaviour with the keyboard is unverified; residual human check. |
| R11 | Two new Pyodide-booting units lengthen CI by about 26 min of step timeouts (92 -> about 118 of a 137 min job; headroom unverified, A14). | OQ-J; units are independent, resumable and bounded (D16). |
| R12 | `drawerBox()` is read once at attach, so the existing drawer's top/bottom go stale on a height change (pre-existing). | Not fixed here (no edit to the drawer path); the sheet recomputes on resize (N5655-4). Noted as a debt candidate. |
| R13 | A sheet that blocks the Follow-driven camera: Follow still focuses in a 112 px strip. | Legibility is S-sh-1's question; Follow logic untouched. |
| R14 | z-index 900 versus JupyterLab menus and dialogs (A15). | Unverified; a K3a step opening a menu over the sheet is cheap to add if S-sh-1 shows a clash. |
| R15 | `sheetMode` as a fourth held value invites someone to key behaviour on it. | The AC-SH-3 model has no `sheetMode`; any dependence of a T row on it fails the independence test. |

---

## 9. Open questions for the user (non-blocking unless marked; each has a default)

1. **OQ-A (blocking for peek content).** Is "the deck plan as its peek state" the **live viewer in
   its Top preset** (default; one iframe, no new content kind) or **praxis.display's SVG deck
   plan** (needs a kernel -> shell snapshot channel, a second renderer, and a body that is not in
   D11)? *Default: the live viewer, Top.*
2. **OQ-B.** Is 760-1023 px wide and >= 500 px high the right gated range, with narrower
   best-effort and ungated? *Default: yes.*
3. **OQ-C.** On open, should the sheet start in peek for both the first announce (T2) and the toggle
   command (T4), or should the explicit toggle open it expanded? *Default: held mode, initially
   peek, for both.*
4. **OQ-D.** `tierOf(1023)` stays `"drawer"` (a legacy sizing tier) while the panel's home at 1023
   is `"sheet"`, so `dock.test.js:278` is not edited. Prefer instead to change that assertion to
   `"sheet"` and fold the home into `tierOf`? *Default: leave the test, add `homeOfWidth`.*
5. **OQ-E.** Ship Stage 1 (tap and keyboard) first and Stage 2 (drag) after spike S-sh-2?
   *Default: yes.*
6. **OQ-F.** Notebook bottom inset by one non-`@media` theme rule on `.jp-WindowedPanel-outer`
   (default), or set inline from dock.js on each notebook panel's outer node? *Default: theme
   rule, subject to S-sh-3.*
7. **OQ-G.** If S-sh-2 shows synthetic touch cannot exercise `touch-action`, accept a human touch
   check on a real tablet as the residual check instead of a gate? *Default: yes.*
8. **OQ-H.** Full-width sheet over the open side bar (default), or bound it to the dock panel's
   horizontal extent (needs a resize observer on the dock because opening the side bar fires no
   window resize)? *Default: full width.*
9. **OQ-I.** Keep the sheet width-only, so a touch tablet at 1024-1365 keeps the drawer or the
   split? *Default: yes (N5655-11).*
10. **OQ-J.** Raise the REPL job's `timeout-minutes` (137) if the K3a/K3b steps leave too little
    headroom? *Default: measure on the first CI run, raise only with the orchestrator's approval
    (D16 budget rule).*
11. **OQ-K.** If you prefer a docked, reflowing bottom panel to an overlay, Option C (Lumino down
    area) is the alternative. *Default: overlay (Option B).*
12. **OQ-L.** Top corners 8 px per DESIGN.md "Shape" rather than the prototype's 12 px?
    *Default: 8 px.*

---

## 10. What this changes in the epic spec (not edited by this draft)

If accepted, the orchestrator would amend `260929_notebook-display-epic.md` as follows.

- **D6.** Table row `< 1024 px` becomes "Bottom sheet (N5655), gated 760-1023"; add the sheet to
  "Mechanism"; the drawer paragraph keeps its text (the drawer still owns 1024-1279).
- **D11.** "Events": **tier crossing** is generalised to "the window changes home (crosses 1280, or
  1024)". T2 and T4 name "split, drawer or sheet". T10, T15, T21: "re-home"; T15's "(one reload ...)"
  becomes "(a DOM move reloads once; an in-place restyle between the two overlays does not)". The
  list of values dock.js holds gains `sheetMode`, stated as presentation only. **T1-T27 and I1-I6
  keep their numbers and meaning; no row or invariant is added.**
- **D12.** One sentence: Iso / Top / Front, Follow and the peek/expanded mode all update held values
  only and never change D11 state.
- **D16.** Unit table: rows `K3a` (`--dock-check`, AC-SH-11, one page, 12 min) and `K3b` (AC-SH-12,
  `has_touch` context, 10 min); the harness gains a CDP touch driver and a context option.
- **Section 2.** G6 "Desktop rendering tiers >= 1024 px" gains "and the sub-1024 sheet"; the
  non-goal "Layouts below 1024 px" and the Next bullet are removed (or narrowed to "below 760 px").
- **Section 3.6.** Adds the sheet's home, peek and expanded descriptions and the Escape/close rule.
- **Section 4.** `dock.js`, `praxis-theme.css`, `__tests__/fakes.js`, `repl_smoke.py`, the two
  test files and `repl.yml` get rows.
- **Section 5.** AC-SH-1..13 become the sheet's ACs (AC-36 itself is not edited: the drawer keys
  and the 1152 viewport stay). AC-39 gains the mutants N-inset, N-reload, N-detach, N-stale,
  N-click, N-touch-action (conditional), N-capture. AC-42's unit table and workflow test gain K3a
  and K3b.
- **Section 6.** New fixer tasks SH-1..SH-8 (C-sprint style).
- **Section 7.** Risk rows R1-R3, R6, R8 and R10 above.
- **Section 8.** OQ-3 (human quality checks at sub-1280 widths) gains the touch-tablet check.
- **`web-repl/design/notebook-display/DESIGN.md`** is a design input and is not edited; its
  "Next" bullet and MVP item 4 "< 1024 px: out of scope" are what this supersedes.
