---
title: 'Notebook display next: a more ergonomic deck-panel layout (backlog #5656)'
description: Revision 2. Grounds the MVP split-right deck panel in the recorded K2 geometry (a fixed 5+5 px dock inset; 0 px dead space at 1280 open, 73.5 px at 1440 open, 220 px after any drag past 480 at both widths), names the root cause (Lumino's split allocation honours the deck's min-width but not its max-width; the capped deck is centred in an oversized half), and specifies a medium-tier re-clamp through the existing layout path that keeps the deck's current width and hands the slack to the notebook, triggered on open, tier entry, the end of a drag and main-area resizes, gated by a measured-mode unit fake and a new real-browser unit K3 that leaves K2 unchanged; the sidebar, per-notebook docking and a labextension stay on paper
status: accepted-r2
revision: 2
task_id: 260929_notebook-display-design
date: '261001'
backlog_id: 5656
---
# Notebook display next: deck-panel layout (backlog #5656), revision 2

> **Draft spec increment. Design only, no product code.** It amends the epic
> `.praxia/docs/specs/260929_notebook-display-epic.md` (D1 S1 row, D6, D11 line 804, D16, AC-36, AC-39,
> sections 2 and 3.6) *by reference*; section 10 lists exactly what would change. The epic and
> `web-repl/design/notebook-display/DESIGN.md` are not edited here. Base:
> `feat/notebook-display-sprint-c-stacked` @ `98a233ed` (PR #198, unmerged). Every file:line below is in
> the worktree `/tmp/praxis-nd-b` at that commit unless it says otherwise.
> Tags: **verified** = read at file:line, or arithmetic on a recorded snapshot; **estimate** = arithmetic
> under an assumption that has not been measured (the assumption is named); **unverified** = needs a real
> browser (the orchestrator runs those) or a user answer.
> Decisions only the user can take are in `/tmp/claude-1000/specs/v2/5656_decisions.md` (Q1-Q8). This
> document is written for the recommended defaults and says, at each fork, what changes if the answer differs.

The MVP deck panel is a JupyterLab main-area split. The user's decided text (DESIGN.md:219-220) reads:
"**The deck panel is a JupyterLab main-area split** (`split-right`) beside the notebook, not a sidebar. A
more ergonomic layout comes later." The MVP is done and green on the recorded run (K1a 14/14, K1b 9/9, K2
20/20 required keys; dist `ba43b338`). This increment asks what "more ergonomic" should mean, using what
the real runs recorded, before anything is built.

---

## R2. Revision 2: what changed and why

Round 1: challenger REVISE (20 findings), defender 16 conceded / 4 partial / 0 rebutted. Every finding is
resolved as the defender adjudicated. Where challenger and defender differ (C9, C10, C16, C19) this
revision follows the evidence the defender verified, and re-checked it (noted per row).

| # | Finding (short) | Resolution | Where now |
|---|---|---|---|
| C1 | 10 px at 1280 is a fixed inset, not dead space; all figures off by 10 | **accepted.** Dead space is now `slack - 2 x (notebook_panel.left - dock_panel.left)`, read per snapshot. 1280 open = 0 (flush), 1440 open = 73.5. Every figure re-derived from the K2 snapshots | 1.2 table, A3-A6, AC-N1 |
| C2 | Dead space returns after any drag past 480, a file-browser toggle, an in-tier resize | **accepted, and it is now the design's centre.** Root cause read in Lumino's code: a tab area's `fit()` reports `maxWidth` Infinity, so the split hands out the min but not the max; the capped deck is centred in its half. Fix = re-clamp on every event that can grow the deck's half | 1.1, 1.2, O1, N5656-3, AC-N3, AC-N5 |
| C3 | The unit fake hands the slack to the notebook, so it can never show dead space | **accepted.** Opt-in measured mode in `fakes.js`; a calibration test must reproduce 73.5 and 220 from a stock split before any dead-space assertion counts | N5656-10, AC-N2, T2 |
| C4 | Opening at 480 makes the notebook narrower at the quality-target width; that was a silent user decision | **accepted.** Open width is user question Q1; default 420 (notebook 527 / 687 at 1280 / 1440) | 1.2, Q1, N5656-3 |
| C5 | `layoutSize()` takes no argument; `clamp(480,420,x)` undefined; mutant (ii) equivalent | **accepted.** A new function `reclaimMedium()` with an explicit formula against the *available* width; `layoutSize()` and the wide path are untouched; mutant (ii) dropped, replaced by M5 (wrong denominator), which fails by 6.4 px | 3 O1, N5656-3, AC-N3 |
| C6 | Open-time sizing happens before an iframe exists; reload counting over open is undefined | **accepted, and it changes.** The re-clamp now runs on the *next* `layoutModified`, after `connectTo` has already appended the iframe (`dock.js:962`), so an open-time `restoreLayout` *does* meet a live iframe. Expected loads over an open step are defined as exactly 1. Reloads are counted over the tier change and every re-clamp step | AC-N5 keys `open_loads_once_1440`, `iframe_reloads_during_reclaim`; risk R2 |
| C7 | RED tests or new K2 keys pushed before the fix turn CI red | **accepted.** RED commits stay local; the branch is pushed only with a GREEN head (precedent: `2c6eb1b9` RED then `1c313e00` GREEN). If a design decision is "no", the RED block is deleted | 7 push policy |
| C8 | New test files must be listed in `repl.yml` | **accepted.** One new pytest file (`test_nd_sensitivity_5656_driver.py`); the new bun file is covered by the directory step | AC-N8, T8 |
| C9 | N-g's outcome logic is circular; T6 edited a locked input | **partially accepted (defender's split).** Validity now comes from a positive control and from inputs (the arrangement is read from the layout config, not from the dead-space output). N-g is kept as a re-runnable negative (the RED K3 run is a one-off on a dist that will not exist after the fix). New driver file; the locked one is not touched | AC-N6, T7 |
| C10 | User ruled "not a sidebar"; S5 should not run by default | **partially accepted (defender's split).** Ruling quoted; S5 is not scheduled and runs only if the user reopens the question (Q5, default no); O2 stays a paper option | intro, 3 O2, N5656-6 |
| C11 | "About 710 px" is a user requirement, not a typo | **accepted.** The gap is recorded as a finding; whether 710 is binding is Q3; DESIGN.md and the D6 text are not edited | 1.2 item 2, Q3, 10 |
| C12 | K1a/K1b at 1440 would run `restoreLayout` at open for the first time | **accepted.** Risk R1 plus the K3 key `reclaim_keeps_current_1440` (shell's current widget and active cell unchanged by re-clamps) | 8, AC-N5 |
| C13 | Wrong dist hash; key counts 20/14/9, not 25/22 | **accepted.** Dist `ba43b338` (stamp :8). Hashing the worktree's `web-repl/dist` with the harness's own `dist_hash` gives `ba43b338`, so the bundle reads in this revision are of the gated build. v1's `b67e0782` has no source. v1 read the main checkout's dist, which hashes `49e655b2` | 1.2, A20 |
| C14 | K2 took ~117 s of 900 s | **accepted.** Budget risk restated; the unbudgeted item was S5 (now unscheduled) | 8 |
| C15 | New keys need a sizing-case family; `geo_before` is evidence-only | **accepted.** New keys live in a new unit K3 with its own `reclaim_status(record)` (asserted iff CSS honoured and layout reachable). Stated: a diagnostic snapshot reader becomes gate input (`real_dead_space`) | AC-N1, AC-N5 |
| C16 | After the fix the deck is flush with the handle at 1440 too | **partially accepted.** N5656-5 still holds (guard code unchanged). Stated: the 1440 drags now depend on the guard. K3's drag keys carry a movement precondition, so a drag the iframe swallowed fails them | N5656-5, AC-N5 |
| C17 | Sidebar width and "by construction" overclaimed | **accepted.** Downgraded to unverified estimates | 1.3, 3 O2 |
| C18 | O1b figures wrong; order matters | **accepted.** Collapse first, then size; re-derived 779/939 (420) and 719/879 (480) as estimates | 3 O1b, Q4 |
| C19 | Zero-match `-k`/`-t` gates can pass | **partially accepted.** Spiked here: bun 1.3.11 `-t` with zero matches exits 1; pytest exits 5 (defender). Gates still name their tests and state a minimum pass count. The splitter is mouse-only (keyboard resize is a stated limit) | 6 preamble, 2 non-goals |
| C20 | Epic line 804 says announce carries `viewer` only | **accepted.** Section 10 amends epic :804, the fakes.js header and dock.js's SIZING comment (`dock.js:43-51`) | 10 |

Beyond round 1 (found while verifying):
- **The drag guard cannot host the re-clamp.** Existing tests pin it: `dock.test.js:2705-2717` (no timer
  is set by a press or release), `:2719-2731` (a press and release change no size, limit or fit) and
  `:2733-2745` (no timer API in the guard's source section). The defender's "drag guard pointerup" hook
  would edit or break them. Separately, a synchronous `saveLayout()` at the guard's mount-time capture
  `pointerup` runs *before* Lumino's own press-time `pointerup` handler. `saveLayout()` calls
  `holdAllSizes()` (`sizeHint = size`), and `size` lags the last move until Lumino's posted update runs
  (`moveHandle` -> `parent.update()`), so the last move could be dropped. That is inferred from code,
  unverified at runtime. The hook chosen is `shell.layoutModified` (verified to fire after a handle
  release; A11).
- **Two K2 keys stop being able to catch a swallowed drag.** If the deck opens at 420,
  `drag_clamp_low_1440/1280` start at the clamp they test: a drag that did nothing still passes. The
  drag-high keys still catch it. K2 is left unchanged (Q7), and K3's mid-drag keys restore a
  non-vacuous low-clamp check.
- **Any new K2 key edits pinned constants.** `test_repl_smoke_resume.py:3472` (the six families),
  `:3683` / `:3687` (K2 key set), `:5139` (the drag sequence `[300, 700, 300, 700, 300]`). A new unit K3
  instead edits two pinned numbers (`test_repl_workflow_scenarios.py:276-278`). Q7.

---

## 1. Problem and current behaviour (verified)

### 1.1 How the split is mounted and sized today, and why dead space appears

- **Mount.** `findRootConstructor` (`dock.js:166`) walks a shell widget's prototype chain to the root
  Lumino `Widget`, `attach` (`dock.js:847-891`) calls
  `app.shell.add(widget, "main", {mode: "split-right", activate: false, ref})` (`:860-862`). One global
  widget.
- **Sizing today (`SIZING` `dock.js:84-90`, `applySizing` `:772-783`).** 1280-1599 px: inline CSS
  `min-width: 420px; max-width: 480px` (`setLimits` `:720-723`) plus `parent.fit()`, then **return**
  (`:774-777`); no layout call, and the ResizeObserver callback only re-evaluates the tier
  (`onDockResized` `:804-808`). >= 1600 px: `layoutSize()` (`:742-768`), target
  `min(0.9 x main, max(420, main - 960 - pad))` as a fraction of the *whole* dock width `main` (`:751-752`).
  1024-1279 px: fixed drawer.
- **Why the dead space (read in the gated bundle, `web-repl/dist/build/jlab_core.c0153ee.js`, dist
  `ba43b338`).**
  - A tab area's `fit()` returns `{minWidth: max(tabBar, widget min), ..., maxWidth: Infinity}`
    (`:437`, `maxWidth:o` with `o=1/0`). The split's `fit()` copies each child's `minWidth` into its
    sizer's `minSize` and sets no `maxSize` (`:437`). So the split never gives the deck's half less than
    420, and it gives it any amount more.
  - Inside the half, `LayoutItem.update` clamps the widget's width to its max-width and, with the default
    alignment, centres it: `e+=(n-o)/2` (`:437`). The surplus sits on both sides of the deck and nobody
    gets it.
  - `#jp-main-dock-panel {padding: var(--jp-private-dock-panel-padding, 5px)}` (`:602`). That is the
    fixed 5 + 5 px inset in every snapshot.
- **Events that grow the deck's half while the deck is capped.**
  - opening (Lumino's `split-right` starts at `[0.5, 0.5]`);
  - a splitter drag past 480;
  - a file-browser collapse (the main area widens);
  - an in-tier window resize upward.
  
  None of them triggers anything at medium today.
- **Drag guard** (`installDragGuard` `dock.js:584-589`): document-capture `pointerdown` on a
  `lm-DockPanel-handle` / `lm-SplitPanel-handle` (`:534`) sets `pointer-events: none` on the deck
  iframes until `pointerup` / `pointercancel` / blur. Its tests forbid timers and sizing in it
  (R2 "beyond round 1").
- **Lifecycle** is the D11 table (T1-T27, I1-I6), single-instance closure state (`dock.js:241-262`).
  `announce` carries `{viewer, deck, session}` (`viewer3d.py:323-330`), but `handleMessage` passes only
  `id` and `deck` (`dock.js:1181`).
- **Baseline.** `OMP_NUM_THREADS=2 bun test web-repl/shell/display/dock.test.js`: 232 pass, 0 fail
  (run here at `98a233ed`, 0.97 s).

### 1.2 What the recorded run shows

Source: `outputs/repl_smoke/dock-check/result.K2.json` (untracked artifact; `result_sha256 e0176c97...`,
stamp `result.K2.stamp.json` with `inputs.dist = ba43b338...` at `:8`; `failing_keys: []` at `:10763`;
`sizing_case: honoured_reachable` at `:10778`; started `1790878978.96` / finished `1790879095.62`, 116.7 s).
Rectangles are `evidence.*.geo_*.rects` (re-read here by a throwaway inspection of the JSON).
**Real dead space** = `summary.slack - 2 x (notebook_panel.left - dock_panel.left)`. The left inset is
measured as 5.0 in every snapshot, and the right inset is assumed to equal it: the padding rule is
symmetric (`jlab_core.c0153ee.js:602`), and the wide snapshots check it (deck right 1561.98 against dock
right 1567). Available width for notebook + deck: `A = dock - 10 - 5`. These numbers are exploratory (no
sidecar). AC-N5 re-measures them under a pre-registered run.

| Fact (file browser open) | 1280x800 | 1440x900 | Source (JSON line of `slack`) |
|---|---|---|---|
| Dock / available `A` | 962 / 947 | 1122 / 1107 | `geo_before.rects.dock_panel` |
| Open: deck / notebook | 473.5 / 473.5 | 480 / 553.5 | `:7396` / `:10694` |
| Open: real dead space | **0** (deck left 768.5 = handle right) | **73.5** (36.75 + 36.75) | same |
| After drag to 700: deck / notebook / real dead | 480 / 247 / **220** (110 + 110) | 480 / 407 / **220** | `:6652` / `:10322` |
| After drag to 300: deck / notebook / real dead | 420 / 527 / 0 | 420 / 687 / 0 | `:6838` / `:10508` |
| After a 30 px drag right (evidence-only step) | 480 / 277 / 190 | n/a | `:7210` |
| Tier change 1600 -> 1440 (`fit_medium`) | n/a | 420 / 687 / 0 | `:267` |
| Wide path lands short of its target | n/a | 1600 open: 415.08 for target 420 (= 420 x 1267/1282) | `:453` |

Derived (arithmetic on `A`, verified inputs):

| Notebook width if the deck sits at | 1280 | 1440 |
|---|---|---|
| 420 | 527 (measured) | 687 (measured) |
| 450 | 497 | 657 |
| 480 | 467 | 627 |
| 420 with the file browser collapsed first (O1b) | 779 (estimate: `A` = 1214 - 15) | 939 (estimate: 1374 - 15) |
| 480 with the file browser collapsed first | 719 (estimate) | 879 (estimate) |

1. **Dead space at open exists at 1440 only, and it is 73.5 px.** At 1280 the 50/50 half (473.5) is
   below the cap, so the deck fills it. The "134 px for nothing" of v1 was 73.5 px of dead space plus
   60 px of deck shrink (480 to 420).
2. **The notebook gets 473.5 (1280) / 553.5 (1440) at open, against DESIGN.md's "about 710 px".**
   DESIGN.md:246-247: "With the file browser open the notebook gets about 710 px". With the file browser
   open and the deck at its 420 floor, the most the notebook can get is 527 (1280) / 687 (1440). 710 is
   reachable only with the file browser collapsed. This is a finding against a user requirement, not a
   number to correct (Q3).
3. **The worst case is after a drag.** Any drag past 480 leaves 220 px empty at both widths, and the
   notebook drops to 247 px at 1280. AC-36's `drag_clamp_high_*` pass anyway, because `clamp_high_ok`
   (`scripts/repl_smoke.py:6956-6958`) checks only the deck width. That is a gate gap; the epic should
   record it (section 10).
4. **The file-browser toggle and an in-tier resize upward also leave dead space (estimate, unmeasured).**
   Both grow `A` while the deck stays capped.
   - Toggle at 1440 from the open state: half ~679.5, dead ~199.5. This assumes Lumino keeps relative
     sizes on resize; for a 50/50 split, distributing the extra width equally gives the same figure.
   - Resize 1280 -> 1440 with the deck at 420: dead ~11 px (proportional) to ~20 px (equal extra per
     child).
   
   AC-N5 measures both.
5. **The iframe next to the handle took the splitter drags at 1280** (first K2 run). The drag guard
   (`ba97d432`) fixed it. After this increment the deck is flush with the handle at 1440 as well
   (C16).
6. **S1-L did not happen**, and the D6 row is right *for the deck node*. `SIZING.case` is
   `honoured_reachable` (S1 run `1e0cab6d`, run at viewport `1440x900`,
   `scripts/spikes/260929_s1_lumino_widget.bth.toml:137`). S1's `css_limits` unit checked only the deck
   width under a drag (`:178`), never whether the notebook got the space back. So "CSS honoured" holds
   for the node, not for the allocation. That is the defect this increment fixes.

### 1.3 What a right-sidebar panel would change (paper only)

Unchanged in substance from v1. Read in the gated bundle (`jlab_core.c0153ee.js`, dist `ba43b338`):
`shell.add(w, "right", {rank})` -> `SideBarHandler.addWidget`, right stack `min-width:
var(--jp-sidebar-min-width)` (250 px), no maximum, `expandRight()` / `collapseRight()` public. Downgraded
per C17:
- the open width of a sidebar deck is **unverified**. The left stack measures 250 px at 1440 and 1600
  (`fit_medium`, `fit_wide`), which does not fit a `[1, 2.5, 1]` relative split, so the side areas
  probably sit at their minimum;
- whether a 420-480 clamp propagates through `#jp-right-stack` is **unverified**;
- "no dead space by construction" is **unverified**.

The user's ruling excludes it ("not a sidebar", DESIGN.md:219-220).

### 1.4 Per-notebook docking (paper only)

Unchanged from v1. `announce.session` exists (`viewer3d.py:329`). `stale.js:576` `panelSession(panel)`.
Retargeting on `currentChanged` would write `src` on a notebook switch and break I2. Deferred to #5660.

### 1.5 Labextension buildability (paper only)

Unchanged from v1 (spikes C1/C2 of v1 were throwaway and are not cited as numbers). No evidence of need.

---

## 2. Assumption Ledger

Workspace for paths: `/tmp/praxis-nd-b` @ `98a233ed`. **No spike records exist for this revision.** The
spike runner the process names (`scripts/loop/adversarial_metrics.py spike-run`) is absent from this
workspace and from the main checkout, so every VERIFIED row rests on a read citation. Browser-runtime
facts are `deferred` to the pre-registered K3 runs (AC-N5), which are their spikes. Bundle citations are
to the minified single-line file, so the line number locates the module, not the statement; the quoted
token is given.

| ID | Assumption | If false | Status | Evidence |
|----|------------|----------|--------|----------|
| A1 | The deck is one global widget added with `app.shell.add(w, "main", {mode: "split-right", activate: false, ref})` | re-home design changes | VERIFIED | read: web-repl/shell/display/dock.js:860-862 |
| A2 | At 1280-1599 `applySizing` sets the CSS limits, calls `parent.fit()` and returns without any layout call | no defect to fix at medium | VERIFIED | read: web-repl/shell/display/dock.js:774-777 |
| A3 | In medium, `onDockResized` only re-evaluates the tier; no sizing follows a main-area resize | toggle/resize dead space would not occur | VERIFIED | read: web-repl/shell/display/dock.js:804-808 |
| A4 | The dock has a fixed 5 px inset each side, from `#jp-main-dock-panel` padding | dead-space formula wrong | VERIFIED | read: web-repl/dist/build/jlab_core.c0153ee.js:602 (`padding: var(--jp-private-dock-panel-padding, 5px)`); read: outputs/repl_smoke/dock-check/result.K2.json:7396 (r1 C1, notebook_panel.left - dock_panel.left = 5 in every snapshot) |
| A5 | Recorded real dead space: 0 at 1280 open, 73.5 at 1440 open, 220 after the drag to 700 at both widths, 0 after the drag to 300 | the design's motivation and every predicted number change | VERIFIED | read: outputs/repl_smoke/dock-check/result.K2.json:7396; read: outputs/repl_smoke/dock-check/result.K2.json:10694; read: outputs/repl_smoke/dock-check/result.K2.json:6652; read: outputs/repl_smoke/dock-check/result.K2.json:10322 |
| A6 | Available width `A = dock - 15` and the notebook is `A - deck` when the deck fills its half (527 / 687 at a 420 deck) | open-width table wrong | VERIFIED | read: outputs/repl_smoke/dock-check/result.K2.json:6838; read: outputs/repl_smoke/dock-check/result.K2.json:10508 |
| A7 | Lumino's split honours a child's min-width in the allocation but not its max-width (tab-area `fit()` returns `maxWidth` Infinity) | root cause misnamed; another fix would be needed | VERIFIED | read: web-repl/dist/build/jlab_core.c0153ee.js:437 (TabLayoutNode `fit` `...maxWidth:o` with `o=1/0`; split `fit` sets only `sizers[i].minSize`) |
| A8 | A capped widget is centred inside its half (default alignment) | dead-space split before/after would differ (total unchanged) | VERIFIED | read: web-repl/dist/build/jlab_core.c0153ee.js:437 (`LayoutItem.update`: `case"center":e+=(n-o)/2`); read: outputs/repl_smoke/dock-check/result.K2.json:10694 (36.75 + 36.75) |
| A9 | `restoreLayout()` re-applies the config `sizes` as fractions of the available width, so the sibling ends at `A x f` | the re-clamp formula would not land | VERIFIED | read: outputs/repl_smoke/dock-check/result.K2.json:453 (wide open: 415.08 = 420 x 1267/1282, i.e. fraction 420/1282 of available 1267); read: web-repl/dist/build/jlab_core.c0153ee.js:437 (`normalizeSizes`) |
| A10 | `restoreLayout()` does not re-append a widget node that is already attached, so the deck iframe is not reloaded | every re-clamp would reload the viewer | VERIFIED | read: web-repl/dist/build/jlab_core.c0153ee.js:437 (DockLayout `attachWidget(e){this.parent.node!==e.node.parentNode&&(...appendChild...)}`); read: scripts/spikes/260929_s1_lumino_widget.bth.toml:137 (S1 at 1440x900 recorded `restore_layout_keeps_iframe`) |
| A11 | A splitter-handle release fires DockPanel `layoutModified`, which LabShell relays to `shell.layoutModified` through a 0 ms debouncer (asynchronously, after the release) | drag trigger needs another hook | VERIFIED | read: web-repl/dist/build/jlab_core.c0153ee.js:437 (DockPanel `_evtPointerUp`: `this._releaseMouse(),M.MessageLoop.postMessage(this,v.LayoutModified)`); read: web-repl/dist/build/jlab_core.c0153ee.js:3 (`this._dockPanel.layoutModified.connect(this._onLayoutModified`, `_layoutDebouncer=new _.Debouncer(()=>{this._layoutModified.emit(void 0)},0)`) |
| A12 | `restoreLayout()` and `addWidget()` also post `LayoutModified`, so the shell's `layoutModified` follows open and every re-clamp (async: the re-entry guard must be convergence, not the `sizing` flag alone) | open trigger missing; or a sync loop | VERIFIED | read: web-repl/dist/build/jlab_core.c0153ee.js:437 (DockPanel `restoreLayout(e){...M.MessageLoop.postMessage(this,v.LayoutModified)}`, `addWidget(e,t={}){...M.MessageLoop.postMessage(this,v.LayoutModified)}`) |
| A13 | `shell.collapseLeft()` / `expandLeft()` fire the shell's `layoutModified` | toggle relies on the ResizeObserver only (still covered) | VERIFIED | read: web-repl/dist/build/jlab_core.c0153ee.js:3 (`collapseLeft(){this._leftHandler.collapse(),this._onLayoutModified()}`, `expandLeft(){...this._onLayoutModified()}`) |
| A14 | dock.js already listens to `shell.layoutModified` (`onLayoutModified`) | a new connection needed | VERIFIED | read: web-repl/shell/display/dock.js:1222 |
| A15 | JupyterLab already calls `shell.saveLayout()` on every `layoutModified`, so a `saveLayout()` in our handler adds no new side-effect class (`holdAllSizes`) | evaluation must avoid `saveLayout` | VERIFIED | read: web-repl/dist/build/jlab_core.c0153ee.js:3 (`n.layoutModified.connect(()=>{g.save(n.saveLayout())})`) |
| A16 | `saveLayout()` config tab areas carry the real widget objects and `currentIndex`, and split areas carry normalised `sizes` from the current sizer sizes | sibling measurement impossible from config | VERIFIED | read: web-repl/dist/build/jlab_core.c0153ee.js:437 (`createConfig(){return{type:"tab-area",widgets:this.tabBar.titles.map(e=>e.owner),currentIndex:...}}`, `createNormalizedSizes` uses `e.size`) |
| A17 | The drag-guard tests forbid a timer or a size change in the guard and grep its source section for timer APIs | the guard could host the re-clamp | VERIFIED | read: web-repl/shell/display/dock.test.js:2705-2745 |
| A18 | Lumino's handle width is the DockPanel `spacing` (default 4), so `A` could be computed as `dock - padding - spacing` | formula silently 1 px off (recorded handle is 5) | REFUTED | read: web-repl/dist/build/jlab_core.c0153ee.js:437 (`this._spacing=4`); read: outputs/repl_smoke/dock-check/result.K2.json:10694 (`handles_width: 5.0`); changed: `A` is measured from a sibling, `A = width(sibling node) / f_sibling`, never from `spacing` or padding |
| A19 | In the legacy fake every node rect is `{width: 0}` except the dock's, so a re-clamp that needs a measured sibling width does nothing there, and the 232 existing tests keep their meaning as the "cannot measure, do nothing" path | `:1640` / `:1774` would turn red and need edits | VERIFIED | read: web-repl/shell/display/__tests__/fakes.js:440; read: web-repl/shell/display/__tests__/fakes.js:889 |
| A20 | The bundle read here is the gated build | Lumino facts could differ from what K2 ran | VERIFIED | read: outputs/repl_smoke/dock-check/result.K2.stamp.json:8 (`ba43b338`); read: scripts/unit_runner.py:681-693 (`dist_hash`, applied here to `web-repl/dist`: `ba43b338`) |
| A21 | Required key counts: K2 20, K1a 14, K1b 9 | AC-N7 wording | VERIFIED | read: scripts/repl_smoke.py:6995-7016; read: scripts/repl_smoke.py:7037-7055; read: scripts/repl_smoke.py:7057-7067 |
| A22 | Existing tests pin the six width families, the K2 key set, the nine K2 steps and the K2 drag sequence | extending K2 would be free | VERIFIED | read: web-repl/tests/test_repl_smoke_resume.py:3471-3472; read: web-repl/tests/test_repl_smoke_resume.py:3681-3689; read: web-repl/tests/test_repl_smoke_resume.py:5139 |
| A23 | A new dock unit needs a `repl.yml` step and changes the pinned D16 backstop numbers (`dock == 45`, `137`) | K3 wiring is cheaper than stated | VERIFIED | read: web-repl/tests/test_repl_workflow_scenarios.py:269-278 |
| A24 | `clamp_high_ok` checks only the deck width (the 220 px state passes AC-36) | gate gap claim wrong | VERIFIED | read: scripts/repl_smoke.py:6956-6958 |
| A25 | The harness has `collapseLeft` but no `expandLeft` | K3 can reuse a driver call | VERIFIED | read: scripts/repl_smoke.py:8645-8648; read: scripts/repl_smoke.py:9080-9083 |
| A26 | bun 1.3.11 `-t` with zero matches exits non-zero | a zero-match gate passes | VERIFIED | read: /tmp/claude-1000/bun_zero.log (`regex "zz-no-such-test-zz" matched 0 tests`, exit 1; throwaway probe, no finding) |
| A27 | A `restoreLayout()` at medium (open, drag end, toggle, resize) keeps `shell.currentWidget` and the notebook's active cell (no activation) | K1a Follow keys could go red | UNVERIFIED | deferred: needs a real browser; K3 key `reclaim_keeps_current_1440` and the unchanged K1a run are the probe (AC-N5, AC-N7) |
| A28 | A `restoreLayout()` meeting an iframe that is still loading (the open re-clamp runs after `connectTo` appends it) causes no second load | `open_loads_once_1440` fails; open re-clamp must wait for the load | UNVERIFIED | deferred: needs a real browser; K3 key `open_loads_once_1440` (A10 makes it likely) |
| A29 | After a main-area resize Lumino keeps relative sizes (proportional), not equal extra per child | only the toggle/resize *estimates* change; the design re-measures every time | UNVERIFIED | deferred: needs a real browser; the unit tests run both rules (AC-N3 j) so the design does not depend on it |
| A30 | The window `resize` event can reach `evaluateTier` before Lumino has laid out the new width, so one evaluation may use the old `A` | a transient wrong fraction | UNVERIFIED | deferred: runtime ordering; the design self-corrects on the following ResizeObserver callback (`A` changed -> recompute), covered by AC-N3 (g) and K3 `reclaim_after_tier_entry` |
| A31 | The S1 lock and the sprint-C sensitivity lock name `scripts/negatives/260929_nd_sensitivity.py` as a committed input, so it must not change | locked run unreproducible | VERIFIED | read: scripts/spikes/260929_nd_sensitivity_sprint_c.bth.toml:10-11 |

Non-goals stated so a reviewer need not ask: keyboard resizing of the splitter (Lumino handles are
mouse-only; a known limit); the wide path's ~5 px undershoot (`layoutSize` divides by `main`, not the
available width; the wide key passes at +-8; recorded, not fixed here).

---

## 3. Options

### O0. Keep the split exactly as built
- **Gains.** Zero change.
- **Costs.** 73.5 px empty at 1440 open; 220 px empty after any drag past 480 (notebook 247 at 1280);
  estimated ~200 px after a file-browser collapse at 1440; AC-36 keeps passing through all of it.

### O1. Keep the split, re-clamp the allocation through the layout path (recommended)

- **O1a. `reclaimMedium()`.** At the medium tier only, whenever the deck's half has grown past the width
  the deck should have, set the split so the half equals that width and give the rest to the siblings,
  through the same `saveLayout()` -> edit `sizes` -> `restoreLayout()` path the wide tier uses (A9, A10).
  The width "the deck should have" is:
  - the **open width** right after an attach or a tier entry (Q1; default 420);
  - **the width it already had** after a main-area change (file-browser toggle, window resize): the
    user's last width is kept;
  - **its own current width** after a drag (the user's choice, already clamped to 420-480 by the node's
    CSS).
  Triggers: `shell.layoutModified` (open, drag release, toggle, its own restore: A11-A13) and the existing
  ResizeObserver (A3). Re-entry guard: convergence (a no-op when the half is within 1 px of the target),
  plus a streak cap of 3 consecutive restores (a backstop for a layout that refuses the sizes), plus the
  existing `sizing` flag. Wide path, drawer, D11, drag guard: unchanged.
  - *Gate cost.* A measured-mode fake (C3), a new bun test file, a new real-browser unit K3 (K2
    unchanged), a re-runnable sensitivity N-g. Edits to existing tests are limited to Q6 (comments only)
    and Q7 (two pinned CI numbers).
  - *Fork Q2 = "open only".* Drop the drag/toggle/resize triggers (only attach / tier entry evaluate);
    K3 keeps `reclaim_open_*` and `reclaim_after_tier_entry`, and the drag/toggle/resize keys become
    recorded-only evidence. The 220 px state is then a stated, accepted limitation.
- **O1b. Yield the left area (opt-in, Q4).** On open at medium, `collapseLeft()` **first**, then the
  re-clamp sizes the split; on close, `expandLeft()` only if we collapsed it and it is still collapsed.
  Notebook 779 / 939 at a 420 deck (estimate, A6 + collapse). Default **off**.

### O2. A right-sidebar panel (paper only)
Excluded by the user ("not a sidebar", DESIGN.md:219-220). Read-only evidence: 1.3. Every width claim is
**unverified** (C17). Not probed unless the user reopens the question (Q5). If they do, the S5 probe of
v1 (pre-registered, product-free) is the next step; its test file would need a `repl.yml` line.

### O3. Per-notebook docking (paper only)
Unchanged from v1: breaks I2/I3, deferred to #5660.

### O4. A labextension (paper only)
Unchanged from v1: no evidence of need; buildable without npm (v1 spike C2, throwaway).

### Comparison

| | O0 | O1a (420) | O1a (480) | O1a open-only (Q2) | O1a + O1b (420) |
|---|---|---|---|---|---|
| Notebook at open, 1280 / 1440 | 473.5 / 553.5 | 527 / 687 | 467 / 627 | as O1a | 779 / 939 (estimate) |
| Dead space at open, 1440 | 73.5 | 0 | 0 | 0 | 0 |
| Dead space after a drag past 480 | 220 | 0 | 0 | 220 | 0 |
| Dead space after a file-browser collapse at 1440 | ~200 (estimate) | 0 | 0 | ~36-66 (estimate) | n/a |
| D11 table changed | no | no | no | no | no |
| Existing assertions edited | none | Q6 comments, Q7 two CI numbers | same | same | same + new keys |

---

## 4. Recommendation

1. **Build O1a with the open width 420 and all four triggers** (Q1, Q2 defaults). It removes every
   recorded dead-space state inside the user's "split" ruling, with no lifecycle change, through a
   mechanism the wide tier already runs in production.
2. **Do not yield the left area** (Q4 default no); report the 779 / 939 figures to the user.
3. **Leave K2 byte-identical and add K3** (Q7). K2 stays the regression check for AC-36. K3 carries the
   new outcome keys, each with a movement or change precondition so it cannot pass on a no-op.
4. **Keep the sidebar, per-notebook docking and the labextension on paper**; S5 is not run (Q5 default no).
5. **Close the S1-L labextension question in the epic** and add the allocation note to D6 (section 10).

---

## 5. Proposed decisions

- **N5656-1. The deck stays a main-area split at >= 1280 px and a drawer below.** Reason: the user's
  ruling, quoted above; O2 has read-only, unverified evidence.
- **N5656-2. S1-L / labextension question closed; D6 gains an allocation note.** `SIZING.case` remains
  `honoured_reachable` (deck node: limits honoured; layout: reachable). D6's "CSS honoured" is qualified:
  "the deck node is clamped; Lumino's allocation honours the minimum only (A7), so the 1280-1599 row
  re-clamps the allocation through layout (N5656-3)". `SIZING` (the exported object) is unchanged
  (`dock.test.js` pins it); only the header comment `dock.js:43-51` changes.
- **N5656-3. Medium-tier re-clamp (`reclaimMedium`).** Precisely:
  - **State.** `settledDeck` (px, or `null`) and `settledAvail` (px, or `null`) are reset to `null`
    on attach to the split and on a tier change into medium; `reclaimStreak` (int) is reset to 0 on
    detach. New exported constants: `OPEN_WIDTH_MEDIUM = 420` (Q1), `RECLAIM_EPS_PX = 1`,
    `RECLAIM_STREAK_MAX = 3`.
  - **Runs** only when `!disposed && state !== "closed" && home === "split" && tier === "medium" &&
    widget && !attaching && !sizing`.
  - **Measure.**
    1. `dock = mainDock()`, `config = dock.saveLayout()`, `split = findSplit(config.main, widget)`. If
       any is missing, return (degrade quietly, like `layoutSize`).
    2. Among the split's *other* children, pick a tab area whose current widget `w` (from
       `widgets[currentIndex]`) has a node rect width `> 4` and a computed `max-width` of `none`
       (when `getComputedStyle` is available). Take the one with the largest size fraction `f_s`
       (`sizes` normalised by their total).
    3. `A = width(w.node) / f_s`. No such child, or `A` not finite: return. Reading the sibling,
       never the deck node, keeps the result right when the deck's limits changed but Lumino has
       not refit yet (A30).
  - **Target.**
    1. `half = f_d x A` (the deck's fraction).
    2. `target` is `OPEN_WIDTH_MEDIUM` if `settledDeck === null`. Otherwise it is `settledDeck` if
       `|A - settledAvail| > RECLAIM_EPS_PX` (the main area changed), else
       `clamp(half, 420, 480)` (a drag or an unrelated layout change: adopt what the user has).
    3. Clamp `target` to [420, 480]. If `A - target < 2`, return.
    4. Set `settledDeck = target`, `settledAvail = A`.
  - **Act.**
    1. If `|half - target| <= RECLAIM_EPS_PX`, set `reclaimStreak = 0` and return (converged).
    2. If `reclaimStreak >= RECLAIM_STREAK_MAX`, `note()` once per attach and return.
    3. Otherwise increment `reclaimStreak` and set the deck's fraction to `target / A`. The other
       children share `1 - target/A` in proportion to their current sizes (the same redistribution as
       `layoutSize`, `dock.js:756-761`, written out again; `layoutSize` itself is not changed).
    4. Set `sizing = true`, call `dock.restoreLayout(config)`, and clear `sizing` in `finally`.
  - **Triggers.**
    - `onLayoutModified` (after its existing close check) calls `reclaimMedium()`.
    - `onDockResized` calls it after `evaluateTier()` when `tier === "medium"`.
    - `evaluateTier`, on a change into medium inside the split, calls it after `applySizing("tier")`.
    - No other call site. The drag guard is not touched (A17).
  - **Never** at >= 1600 or in the drawer. Never writes `src`. Never touches the CSS limits. Every call
    site runs under the existing `guarded(...)` wrappers, so a throw is reported and leaves state as it
    was. Reason: A5, A7; the machinery (A9, A10) exists.
- **N5656-4. The shell never collapses or expands the left area on its own** unless Q4 is "yes" (then
  only O1b, collapse-then-size, restore-only-what-it-changed).
- **N5656-5. No change to the D11 table, T1-T27, I1-I6, the `praxis_viz3d` protocol, the drag-guard code
  or the drawer.** Consequence stated (C16): after the fix the deck iframe is flush with the handle at
  1440 as well as 1280, so the 1440 drags depend on the guard. K3's drag keys require movement, so a
  swallowed drag fails them.
- **N5656-6. The sidebar is not probed** unless the user reopens it (Q5). Reason: user ruling.
- **N5656-7. Per-notebook docking stays with #5660**; the epic's D11 line 804 is corrected to say
  `announce` carries `viewer`, `deck` and `session` (C20).
- **N5656-8. Control discipline for every new key.**
  - A pure derive function with a positive and a negative synthetic control in pytest.
  - A precondition that fails the key when its action did nothing (movement >= 20 px, or a main-area
    change >= 150 px).
  - A real-browser negative: the pre-registered RED K3 run on the pre-fix build, or N-g.
  - Keys that pass on the pre-fix build by design are named as guard keys, and their negatives are
    stated (AC-N5).
- **N5656-9. New real-browser unit K3; K2 unchanged.** Reason: A22 / A23 (Q7).
- **N5656-10. Measured-mode fake, opt-in.** `createFakeDockPanel(..., {mode: "measured"})`. The default
  remains `"legacy"`, so none of the 232 existing assertions changes meaning beyond A19.

---

## 6. Acceptance criteria

`AC-N<n>`, local to this increment. Pytest and bun run one file per process, with `OMP_NUM_THREADS=2`.
- pytest exits 5 on zero selected tests. bun 1.3.11 exits 1 on a zero-match `-t` (A26). Bun gates
  still run whole files and require a stated minimum pass count.
- Real-browser gates run under the orchestrator.
- Tolerances: `RECLAIM_EPS_PX = 1` (product), `CLAMP_TOL_PX = 2` (harness, existing `:6876`).
- No existing key, tolerance or gate is loosened. Nothing replaces an existing mechanism assertion with
  an outcome assertion: the outcome assertions are *added* in a new file, and the old lines stay (Q6:
  comments only).

**AC-N1 (pure dead-space measure).** `real_dead_space(snapshot) -> float | None` in
`scripts/repl_smoke.py`:
- Value: `layout_summary(snapshot)["slack"] - 2 x (rects.notebook_panel.left - rects.dock_panel.left)`.
- `None` when a rect is missing or non-numeric, or the measured left inset is outside [0, 20].
- Predicates `reclaim_ok(snap, want_deck)` (real dead <= 2 and |deck - want| <= 2) and
  `moved(before, after, min_px)` (|after - before| >= min_px).
- Gate: `uv run --no-sync python -m pytest web-repl/tests/test_repl_smoke_resume.py -k "real_dead_space or reclaim_ok or moved_px" -q`, at least 12 tests.
- Positive controls: literal copies of the recorded rects (comment cites `result.K2.json` and
  `result_sha256 e0176c97...`): 1280 open -> 0.0 (+-0.01); `fit_medium` -> 0.0; `wide_1920` -> 0.0156.
- Negative controls:
  - 1440 open -> 73.5, and `reclaim_ok(..., 480)` false;
  - 1280 after the drag to 700 -> 220, `reclaim_ok` false;
  - missing `notebook_panel` -> `None` -> `reclaim_ok` false;
  - inset 30 -> `None`;
  - `moved(420, 420, 20)` false.

**AC-N2 (measured fake reproduces the recorded run).** New file
`web-repl/shell/display/dock_reclaim.test.js`, block "measured fake calibration". It drives
`createFakeDockPanel(lumino, doc, {width, mode: "measured"})` directly (no dock.js): seed a notebook
(inline `min-width: 2px`), `addWidget(deck, {mode: "split-right", ref})` with 420 / 480 inline limits,
then `drag`.
- Required, within 0.01 px:

  | dock | step | deck | notebook | real dead (fake's reader = AC-N1 formula on node rects) |
  |---|---|---|---|---|
  | 962 | open | 473.5 | 473.5 | 0 |
  | 1122 | open | 480 | 553.5 | 73.5, split 36.75 / 36.75 |
  | 962, 1122 | drag 300 | 420 | 527 / 687 | 0 |
  | 962, 1122 | drag 700 | 480 | 247 / 407 | 220 |
  | 1122 | 50/50 with the limits cleared (wide-like) | 553.5 | 553.5 | 0 |

- Also required: the legacy mode on the same inputs still reports the legacy numbers (e.g. 1440 legacy
  open: deck 480, notebook 960). This pins that the opt-in did not change the default.
- Gate: `OMP_NUM_THREADS=2 bun test web-repl/shell/display/dock_reclaim.test.js -t "measured fake calibration"`, at least 9 pass.
- Negative control: the 73.5 and 220 rows *are* the negative of "the fake cannot show dead space".
  A fake that hands the slack to the notebook (the legacy `_assign` rule) fails them, which the legacy
  comparison row shows.

**AC-N3 (re-clamp behaviour, unit).** Same file, block "medium re-clamp (N5656-3)", with a local `env`
built from `fakes.js` helpers in measured mode. Window width minus a 318 px sidebar gives dock 962 /
1122, as recorded. `shell.layoutModified` is queued, not emitted synchronously, and `env.settle()`
delivers the queue then fires the ResizeObserver if the dock width changed. More than 10 rounds throws
"layout did not settle". Assertions at 1280 and 1440:
- (a) **Open.** After settle: deck = `OPEN_WIDTH_MEDIUM` +-0.5, real dead <= 0.5, notebook =
  `A - OPEN_WIDTH_MEDIUM` +-0.5, `restoreCalls >= 1`, one iframe inserted, the only `src` write is T2's,
  the D11 snapshot is `open-connected`.
- (b) **Drag to 460.** Deck 460 +-0.5, and `restoreCalls` unchanged (nothing to fix, nothing done).
- (c) **Drag to 700.** Deck 480 +-0.5, dead <= 0.5, notebook `A - 480` +-0.5, exactly one restore for
  that release.
- (d) **Drag to 300.** Deck 420, dead 0.
- (e) **Toggle.** After (c), `setSidebar(0)` then settle: deck 480 +-0.5, dead <= 0.5. Then
  `setSidebar(318)`: the same.
- (f) **Resize.** With the deck at 420, 1280 -> 1440: deck 420 +-0.5, dead <= 0.5. With the deck at 480,
  1440 -> 1280: deck 480, notebook 467 +-0.5.
- (g) **Tier entry.** 1600 -> 1440: deck `OPEN_WIDTH_MEDIUM` +-0.5, dead <= 0.5. At 1600 itself, only
  `layoutSize` restores occur (the re-clamp never runs at wide).
- (h) **Convergence.** Every trigger settles within 3 rounds.
- (i) **Refusing layout.** A fake whose `restoreLayout` ignores `sizes`: at most `RECLAIM_STREAK_MAX`
  restores per trigger, and one `note`.
- (j) **Resize rule.** (e) and (f) also pass with `resizeRule: "equalExcess"`.
- (k) **No re-clamp.** Closed, drawer, a deck the user moved out of a horizontal split, and a sibling
  with a max-width: no restore, no error.

Gate: `OMP_NUM_THREADS=2 bun test web-repl/shell/display/dock_reclaim.test.js`, at least 40 pass, 0 fail.

Negative controls: each mutant below is loaded through a patch loader copied from `dock.test.js:2374-2387`
(anchor must match exactly once). Each has an identity-patch positive control, and each must FAIL its
probe. The failure is argued against the code:

| Mutant | Patch | Probe | Why it fails |
|---|---|---|---|
| M1 no re-clamp | first line of `reclaimMedium` -> `return;` | (a) at 1440 | measured fake leaves 73.5 (AC-N2) |
| M2 no layout trigger | the `reclaimMedium()` call in `onLayoutModified` removed | (c) at 1440 | a drag does not resize the dock, so the ResizeObserver never fires; 220 remains |
| M3 no resize trigger | the call in `onDockResized` removed | (f) 1280 -> 1440 | the fake models a window resize as ResizeObserver only (no `layoutModified`); dead 11-20 > 0.5 |
| M4 width not kept | `target` always `OPEN_WIDTH_MEDIUM` | (b) | deck snaps to 420, probe wants 460 |
| M5 wrong denominator | `target / A` -> `target / (A + 15)` | (c) at 1440 | deck half 473.6, probe wants 480 +-0.5 |
| M6 no convergence | the `<= RECLAIM_EPS_PX` early return removed | (h) | a restore on every round until the streak cap; "exactly one restore per release" fails |
| M7 no streak cap | the cap check removed | (i) | refusing layout never converges; `settle()` throws after 10 rounds |
| M8 runs at wide | the `tier === "medium"` condition removed | (g) at 1600 with the file browser closed (dock 1600, `A` 1585) | `layoutSize` lands the deck at 624 x 1585/1600 = 618.2 (probe: +-1, and only `layoutSize` restores); the mutant then re-clamps to `OPEN_WIDTH_MEDIUM` (settled is null), 420 |

**AC-N4 (existing unit tests unchanged).** `OMP_NUM_THREADS=2 bun test web-repl/shell/display/dock.test.js`:
232 pass, 0 fail, and the file is byte-identical except the comment-only edits Q6 allows.
- `:1640` and `:1774` keep `restoreCalls` 0. After the change this is true because the legacy fake has
  no node geometry, so the re-clamp cannot measure and does nothing (A19). The Q6 edit says so in their
  comments.
- The drag-guard block (`:2454-2745`) passes untouched; the re-clamp code lies outside the guard
  section markers.
- Negative control: the existing mutant blocks (`:2311-2452`, `:2747-...`) still FAIL their probes
  (unchanged).

**AC-N5 (real browser, new unit K3).** `--dock-check --scenario K3`: one page, one kernel, one `dock()`,
file browser open. Budget 10 min (estimate: ~150 s, unmeasured; K2's nine steps took 116.7 s).
- Each step ends with `settle_layout()`: poll `D.layout()` every 250 ms until two consecutive summaries
  agree within 0.5 px, cap 5 s. A timeout fails the step's key and records "did not settle".
- Keys, all `True`, family status from `reclaim_status(record)`: asserted iff `css_limits_honoured and
  layout_sizing_reachable`, else recorded-only. That is a new function; `width_key_status` and
  `WIDTH_CATEGORIES` are not touched.

| Key | Step | Predicate | Non-vacuous precondition | Expected on the pre-fix build |
|---|---|---|---|---|
| `open_loads_once_1440` | 1440x900, `dock()` cell, settle | deck iframe loads during the step == 1 | loads counter readable | true (guard key; negative: K1b's reload keys exercise the counter) |
| `reclaim_open_1440` | same | `reclaim_ok(snap, OPEN)` | split home, deck present | **false** (73.5; deck 480) |
| `reclaim_keeps_mid_1440` | drag to 460 | deck 460 +-2 and dead <= 2 | `moved(open, after, 20)` | true (guard key: catches M4-like over-eager re-clamp; negative: unit M4) |
| `reclaim_low_moves_1440` | drag to 300 | deck 420 +-2, dead <= 2 | `moved(460, after, 20)` | true (guard key: catches a swallowed drag) |
| `reclaim_after_high_1440` | drag to 700 | `reclaim_ok(snap, 480)` and notebook `A - 480` +-2 | `moved(420, deck, 20)` | **false** (220) |
| `reclaim_after_toggle_1440` | `collapse_left`, settle; `expand_left`, settle | both snapshots `reclaim_ok(snap, 480)` | dock width +>= 200 at collapse, back within 2 at expand | **false** (~200 estimate) |
| `reclaim_keeps_current_1440` | around the toggle | `shell.currentWidget.id` and the notebook's active cell index equal before collapse and after expand; current widget is not the deck | both reads present | true (guard key for A27; negative: synthetic only, stated) |
| `reclaim_after_resize_down` | viewport 1280x800 | `reclaim_ok(snap, 480)` | dock width change 160 +-2 | **false** (deck half ~700 x 947/1107 = ~599, dead ~119 estimate) |
| `reclaim_after_resize_up` | drag to 300 at 1280, then viewport 1440x900 | `reclaim_ok(snap, 420)` | `moved` on the drag; dock change 160 +-2 | **false** (11-20 estimate) |
| `reclaim_after_tier_entry` | 1600x900, settle, 1440x900, settle | `reclaim_ok(snap, OPEN)` | the 1600 snapshot has no deck max-width | true at OPEN 420 (today's 420/687), **false** at 480 |
| `iframe_reloads_during_reclaim` | loads counted from the 460 drag through the tier entry | == 0 | counter readable | true (guard key; a reload here would be the A10/A28 failure) |
| `reclaim_open_1280` | 1280x800, close + reopen (T4 -> T6), settle | `reclaim_ok(snap, OPEN)` | the state went `closed` then `open-connected` (a fresh attach, read from `D.view()`) | **false** (473.5, more than 2 px from 420 or 480) |
| `pageerrors` | whole run | `[]` after the existing narrow toleration | | true |

- **RED run (the real-browser negative).** Pre-registered, by the orchestrator.
  - Sidecar `scripts/spikes/261001_reclaim_k3_red.bth.toml` committed before the run; build = HEAD with
    T5 (harness) and *without* T4 (product).
  - Outcome `red_detected` iff every key marked **false** above is false *and* every guard key is true;
    `invalid` iff any precondition fails or a step did not settle.
  - Run: `bth run --project-slug praxis -- uv run --no-sync python3 scripts/spikes/261001_reclaim_k3.py --phase red`.
- **GREEN run.** Sidecar `scripts/spikes/261001_reclaim_k3_green.bth.toml`, committed with the red one,
  before either run. Outcome `green` iff all 13 keys true. Verified by record
  (`bth sql "SELECT id, status, outcome, exit_code FROM runs WHERE id LIKE '<prefix>%'"`, after
  `bth compact`).
- Resume/chunking: K3 is one unit with its own watchdog (like K2). A timeout loses only K3.

**AC-N6 (sensitivity N-g, re-runnable).** New negative-only unit `N-g` (no CI step, not in the aggregate,
like `N-d`).
- Harness `D.stockSplitCapped(a)` (additive) adds a stock split-right widget with 420 / 480 inline limits
  and no dock.js sizing at 1440x900. It measures (`stock`), then sizes that same stock widget itself
  (save -> sizes so the half is 480 / A -> restore) and measures again (`sized_control`).
- `ng_measurement_problem(raw)`. Validity comes from inputs, never from the dead-space output:
  - all rects present;
  - computed min / max of the stock node = 420px / 480px;
  - the `stock` layout config sizes are 0.5 / 0.5 +-0.01;
  - `sized_control` passes `reclaim_ok(..., 480)`.

  Any failure -> `invalid`.
- Outcomes: `g_detected` iff valid and `reclaim_ok(stock, 480)` is false; `g_not_detected` iff valid and
  it is true (which would contradict A5: a finding about Lumino, not a pass).
- Files: new `scripts/negatives/261001_nd_sensitivity_5656.py` (the locked
  `scripts/negatives/260929_nd_sensitivity.py` is not edited, A31), sidecar
  `scripts/spikes/261001_nd_sensitivity_5656.bth.toml` (committed first), tests
  `web-repl/tests/test_nd_sensitivity_5656_driver.py`: `derive_ng_keys` true on the recorded 1440 stock
  arrangement (`geo_before` rects), false on a sized one, `invalid` on missing rects and on a 0.3 / 0.7
  config.

**AC-N7 (no regression).** On the fixed build, unchanged harness lines:
- K1a 14/14, K1b 9/9, K2 20/20 (with `iframe_reloads_during_resize` 0), `--dock-check --aggregate-only`
  green including K3;
- `bun test web-repl/shell/display` (the CI step) green;
- every pytest file green, one process each.

K2's `drag_clamp_low_*` will pass from a 420 open even on a swallowed drag. This is stated, not hidden:
K3's `reclaim_low_moves_1440` is the non-vacuous check (Q7). The random-sequence model test passes
unchanged.

**AC-N8 (CI wiring; orchestrator edits `.github/`).**
- In `.github/workflows/repl.yml`:
  - add step "Dock check K3 (medium re-clamp)", `timeout-minutes: 12`, `if: ${{ !cancelled() }}`,
    `uv run python scripts/repl_smoke.py --dock-check --scenario K3 --base-path /praxis/`, after K2 and
    before the dock aggregate;
  - change the job `timeout-minutes` from 137 to 149;
  - add `uv run python -m pytest web-repl/tests/test_nd_sensitivity_5656_driver.py -q` to the Tests step,
    alphabetical.
- In `web-repl/tests/test_repl_workflow_scenarios.py:276-278`: `dock == 45` becomes `57` (12 + 16 + 17 +
  12) and `137` becomes `149`. That is the only edit to an existing assertion's value in this increment,
  and it extends a sum; it loosens nothing (Q7).
- Gates: `uv run --no-sync python -m pytest web-repl/tests/test_repl_workflow_covers_tests.py -q` and
  `.../test_repl_workflow_scenarios.py -q` pass.
- Negative control: the covers test fails on a branch that adds the new pytest file without the `repl.yml`
  line (its own assertion, `:48-55`), which is exactly what `98a233ed` fixed for PR #198.

**AC-N9 (conditional on Q4 = yes, O1b).**
- K3 gains `left_yielded_1280` and `left_restored_1280`. A user-collapsed left area stays collapsed after
  close: the negative is a build that always expands on close, which must fail `left_restored_1280`.
- Bun mutants, and an order test: collapse happens before the re-clamp, so the deck ends at OPEN, not
  capped in a grown half.

**AC-N10 (docs).** Section 10 edits by the orchestrator in a separate commit; `docs check` passes. Not a
code gate.

---

## 7. Task decomposition (tests first)

LOC are rough (tests + code). **RB** = real-browser run by the orchestrator. **Push policy (C7):** RED
commits stay local. The branch is pushed only when its head passes every CI gate, including K3 with the
fixed dock.js (CI builds the dist from source). CI runs the head only, so RED commits followed by GREEN
commits in one push are fine; this repo's history already does it (`2c6eb1b9` -> `1c313e00`). If Q1/Q2 are
answered so that a RED block no longer applies, the block is deleted, not skipped.

| Task | What | Files | ~LOC | Depends | RB |
|---|---|---|---|---|---|
| **T1** | Pure: `real_dead_space`, `reclaim_ok`, `moved`, `reclaim_status`, `derive_k3_keys` + tests (AC-N1); green on its own (no product dependency) | `scripts/repl_smoke.py` (additive), `web-repl/tests/test_repl_smoke_resume.py` (tests appended only) | 90 + 160 | none | no |
| **T2** | Measured-mode fake: `mode`, `inset`, `handle`, `resizeRule` options; node rects; queued `layoutModified` from `addWidget` / `restoreLayout` / drag release / `setSidebar`; calibration block (AC-N2), green on its own; fakes.js header describes both modes | `web-repl/shell/display/__tests__/fakes.js` (additive; legacy path unchanged), `web-repl/shell/display/dock_reclaim.test.js` (create) | 140 + 120 | none | no |
| **T3** | RED: "medium re-clamp" block (a)-(k) and mutants M1-M8 (AC-N3); local commit only | `dock_reclaim.test.js` | 320 | T2, Q1, Q2 | no |
| **T4** | GREEN: `reclaimMedium` + the three call sites + constants + header comment (`dock.js:43-51`) | `web-repl/shell/display/dock.js` | 70 | T3 | no |
| **T5** | K3 harness: `D.expandLeft`, `D.currentInfo` (current widget id, active cell index), `settle_layout`, `run_k3`, `HarnessUnit("K3", DOCK_CHECK, 10*60, ...)`, fake-driver tests (pytest, appended) | `scripts/repl_smoke.py` (additive), `web-repl/tests/test_repl_smoke_resume.py` | 180 + 220 | T1 | no |
| **T6** | Sidecars for RED and GREEN K3 (committed before either run) + their thin runner; RED run on HEAD = T1+T2+T3+T5 (no T4); GREEN run after T4 | `scripts/spikes/261001_reclaim_k3.py`, `261001_reclaim_k3_red.bth.toml`, `261001_reclaim_k3_green.bth.toml` | 60 + 80 | T5 (RED), T4 (GREEN) | RB x2 |
| **T7** | N-g: `D.stockSplitCapped`, `ng_measurement_problem`, `derive_ng_keys`, unit row, new driver + sidecar + tests (AC-N6) | `scripts/repl_smoke.py`, `scripts/negatives/261001_nd_sensitivity_5656.py`, `scripts/spikes/261001_nd_sensitivity_5656.bth.toml`, `web-repl/tests/test_nd_sensitivity_5656_driver.py` | 70 + 90 + 50 + 140 | T1 | RB |
| **T8** | CI wiring (AC-N8): the pinned-number edit in `test_repl_workflow_scenarios.py` (fixer), `repl.yml` (orchestrator), same push | as AC-N8 | 10 | T5, T7, Q7 | no |
| **T9** | Q6 comment-only edits: `dock.test.js:6-7` header, the comments at `:1640` / `:1774` (and their titles if Q6 allows) | `dock.test.js` | 6 | T4, Q6 | no |
| **T10** | Only if Q4 = yes: O1b (AC-N9) | `dock.js`, `dock_reclaim.test.js`, `repl_smoke.py` | 30 + 90 + 40 | T4 | RB |
| **T11** | Epic edits (section 10), orchestrator | epic spec | doc | T6, T7 outcomes | no |

Order: T1 and T2 in parallel, then T3, then T5, then T6 (RED run), then T4, then T6 (GREEN run), then T7,
T8 and T9, then one push; local K1a / K1b / K2 / K3 by the orchestrator before the push. T10 and anything
O2/O3/O4 are not scheduled. Each of T1-T9 fits one fixer session; T5 is the largest (harness), and its
fake-driver tests make it checkable without a browser.

---

## 8. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | `restoreLayout()` at medium now runs under K1a and K1b at 1440 (open, reopen, re-home), where it never ran; it could change activation or `shell.currentWidget`, the class of K1a Follow failure seen before | `reclaim_keeps_current_1440` (K3); K1a/K1b run locally before the push; restoring the config keeps `currentIndex` (A16); rollback = revert T4 (one function and three call lines) |
| R2 | The open re-clamp runs after `connectTo` has appended the iframe (`dock.js:962`), so a `restoreLayout()` meets a loading iframe (A28); a second load would break K1b's reload counts and K1a timing | `open_loads_once_1440`; A10 makes a reload unlikely (no re-append); if it fails, defer the open re-clamp until the frame's first `load` (a D11-neutral change), measured again |
| R3 | A re-clamp loop (async `layoutModified` after our own restore) | convergence at 1 px (A12), streak cap 3, the `sizing` flag; unit M6/M7; K3 settles within 5 s or fails |
| R4 | Wrong `A` from a stale or min-clamped sibling, or a sibling that is not the notebook | sibling must be uncapped and > 4 px; picks the largest fraction; self-corrects on the next trigger (A30); unit (k) |
| R5 | The user's own drag is undone | width preserved by rule (drag -> adopt current; resize -> keep settled); unit (b), K3 `reclaim_keeps_mid_1440`, M4 |
| R6 | CI red from RED tests or K3 before the fix | push policy (section 7); K3 lands in the same push as T4 |
| R7 | K2's `drag_clamp_low_*` stop discriminating a swallowed drag (open at 420) | stated (AC-N7); K3 drag keys with movement preconditions; Q7 offers to tighten K2 instead |
| R8 | K3 adds CI time | ~150 s estimate inside a 10-min budget; job backstop 137 -> 149 (AC-N8); K2 measured 116.7 s of 900 s |
| R9 | `saveLayout()` on every `layoutModified` has a side effect (`holdAllSizes`) | JupyterLab already does it on every `layoutModified` (A15); the evaluation exits on tier/state first |
| R10 | The measured fake encodes a wrong Lumino model | it is calibrated against five recorded snapshots (AC-N2); resize semantics run under both rules (A29); K3 is the authority |
| R11 | Exploratory numbers (section 1.2) quoted as findings | the RED K3 run re-measures them under a sidecar; no external doc quotes 73.5 / 220 before it |
| R12 | Workspace persistence: JupyterLab saves the layout (with our sizes) on every change | the deck widget is not restorer-tracked (D14), so a reload does not restore it; sizes of a missing widget are dropped by `normalizeAreaConfig` (read, `jlab_core.c0153ee.js:437`, `restoreLayout`) |

Rollback for the whole increment: revert T4 (product) and the K3 step. T1, T2, T5 and T7 are additive and
harmless alone.

---

## 9. Open questions for the user

All are in `/tmp/claude-1000/specs/v2/5656_decisions.md`, in plain language with numbers. Summary
(default in brackets; the spec is written for the defaults):

- Q1 open width at 1280-1599 [420]
- Q2 when to reclaim the space [open, tier entry, after a drag, after a toggle or resize]
- Q3 is "about 710 px" binding [no; a target, gap recorded]
- Q4 yield the file browser [no]
- Q5 sidebar back on the table / run the S5 probe [no]
- Q6 may `dock.test.js:1640` / `:1774` change [comments only; the assertions stay]
- Q7 a new unit K3 with two pinned CI numbers changed, rather than editing K2's pinned lists [yes]
- Q8 may DESIGN.md be edited [no]

---

## 10. What this changes in the epic spec (orchestrator, not here)

- **D1, S1 row.** Closing note after S1-L: "Not in force: S1 recorded S1-A, `honoured_reachable` (run
  `1e0cab6d`); the labextension question for sizing is closed by #5656 N5656-2."
- **D6.** Under the sizing-case table: "CSS limits are honoured by the deck node; Lumino's allocation
  honours only the minimum (its tab-area `fit()` reports no maximum), so at 1280-1599 the deck's half is
  re-clamped through layout to the deck's width on open, tier entry, the end of a drag and main-area
  resizes (#5656 N5656-3)." The medium row's mechanism cell gains "plus layout re-clamp". The user's
  "about 710 px" text is **not** edited. A finding note is added: "measured: 527 (1280) / 687 (1440) at
  most with the file browser open; see #5656 Q3."
- **D11, line 804.** "`announce` carries `viewer`, `deck` and `session`; `close` carries `viewer`."
  T1-T27 / I1-I6 unchanged (stated).
- **AC-36.** Record the gate gap: `drag_clamp_high_*` pass with 220 px of dead space. The fix's keys live
  in K3 (new AC-36b, or a new AC; orchestrator's choice of numbering).
- **AC-39.** New (f): N-g.
- **D16 unit table.** K3 (10 min, 1440x900 / 1280x800 / 1600x900, one page) and N-g (negative-only, no CI
  step); the D16 backstop line 137 -> 149.
- **Section 4 / fakes.js row.** The measured mode, its calibration and the header correction ("legacy mode
  hands the clamped difference to siblings, which K2 contradicts").
- **dock.js SIZING header** (`dock.js:43-51`): the code comment changes in T4; the epic's quote of it, if
  any, follows.
- **Section 2 non-goals.** Unchanged. The several-notebooks non-goal gets a pointer to #5660 and section
  1.4 here.
- **Section 3.6 / G1.** No change.
- **Revision note.** "Revision 12 (261001): #5656, N5656-1..10."
- **DESIGN.md.** Not edited (Q8). If the user says yes, the only candidate is a "Next" pointer; the 710
  text stays theirs.

---

## Rulings (user, 2026-10-01) -- appended by the orchestrator; no other text changed

The user answered the decision sheet (`5656_decisions.md`) with: "go with your recommendations they seem
sensible". Recorded answers:

| Q | Ruling |
|---|---|
| Q1 open width at 1280-1599 | **420** |
| Q2 when to reclaim empty space | **(b)**: on open / tier entry AND after every splitter drag, file-browser toggle and in-tier window resize; the deck's current width is kept |
| Q3 "about 710 px" | a **target, not binding**; recorded as a finding; the user's text is not edited |
| Q4 close the file browser on open | **no** (T10 / O1b not scheduled) |
| Q5 sidebar back on the table | **no**; O2 stays on paper; no S5 probe |
| Q6 touching `dock.test.js:1640` / `:1774` | **(b)**: comments and titles only; the checked values stay |
| Q7 new real-browser checks | **new unit K3**; K2 stays byte-identical |
| Q8 edit `DESIGN.md` | **no**; only the epic, by the orchestrator |

Build order and push policy as in section 7. Browser runs (RED and GREEN K3, N-g) are done by the
orchestrator. `status` is now `accepted-r2`.
