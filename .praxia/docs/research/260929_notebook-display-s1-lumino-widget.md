---
title: 'Spike S1 (notebook display epic): Lumino widget, split-right, size limits, cell-state hooks'
description: 'Result of pre-registered spike S1, bathos run 1e0cab6d, outcome s1_a: real Lumino widget constructible by prototype-chain walk, split-right works, CSS size limits honoured (D6 case honoured_reachable, all width keys asserted), restoreLayout keeps the iframe. Run against the local 260828 dist.'
status: final
task_id: 260929_notebook-display-design
date: '260929'
confidence: ''
sources: ''
---
# Spike S1 (notebook display epic): Lumino widget, split-right, size limits, cell-state hooks


# Spike S1: Lumino widget, split-right, size limits, cell-state hooks

**Outcome: `s1_a`** (D1 branch **S1-A**, D6 sizing case **`honoured_reachable`**). Pre-registered
bathos run `1e0cab6d-0765-4c16-802f-84c571637a3e`, verified by its record (status `completed`,
outcome `s1_a`, exit code 0 in the `runs` table; `bth compact` first). Task A1 of the notebook
display epic (backlog #5623); spec `.praxia/docs/specs/260929_notebook-display-epic.md`, D1 S1, D6,
D17.

## Provenance and pre-registration order
- Probe `scripts/spikes/260929_s1_lumino_widget.py` and sidecar `.bth.toml` were committed on
  `feat/notebook-display-sprint-a` as `60e892fe` **before any run**. The sidecar and driver were
  then **amended once, before the first run**, to add `repl_smoke.py` as the hashed input
  `harness` (`29c1ad97`; reason: round 11 C11-3 / round 12 C12-3, the driver loads `repl_smoke.py`
  and D17 requires it as an input; units, timeouts, outcomes, hypothesis, negative control and
  resume rule are unchanged).
- Bathos lock `scripts/spikes/260929_s1_lumino_widget.bth.1e0cab6d-....bth.lock.toml` (committed as
  `cde98c38`): `sidecar_sha256 = 04ffa644207b0971b99f3dd715ac4dda41ead93bab33b384ac40c62f272913dc`,
  `script_sha256 = 7702944e7b696b6b8eefaceb0f008930e9282eabdcd0029f869b7ef1f3af7a6a`,
  `git_sha = b44c196cfd8679778debf7efa6e85e1cd3abc8ec`. The orchestrator verified that the committed
  sidecar and script at `b44c196c` hash to exactly these values.
- **No earlier run.** A first launch attempt failed at `bth run` argument parsing (`--out` is not a
  `bth run` option; exit 2) before any script started, so it produced no record, no units and no
  output. The run cited here is the first and only execution of the probe.
- Command (unsandboxed, full Chromium): `cd /tmp/praxis-nd-a && bth run --project-slug praxis
  --output-paths outputs/spikes/260929_s1 -- uv run --no-sync python3
  scripts/spikes/260929_s1_lumino_widget.py --out-dir outputs/spikes/260929_s1 --dist
  /home/marielle/projects/praxis/web-repl/dist`, with `UV_PROJECT_ENVIRONMENT` set to the main checkout's
  `.venv`. `uv.lock` was copied into the worktree (gitignored).
- Browser: Google Chrome for Testing 153.0.8010.12 (`chromium-1243`, the build CI bundles), viewport
  1440 x 900.

## DEVIATION: dist
The dist served is the **local `web-repl/dist` built 260828** (PLR 0.2.2 build), not a fresh build off
`origin/main` a176bac7 (PLR 1.0.0b1): the pin commit `786ac2c4e` is in no local git object DB and the
sandbox proxy blocks the clone. No commit touched `web-repl/pyproject.toml`, `uv.lock` or
`jupyter-lite.json` after 260828 (JupyterLite `appVersion` 0.8.1 in the dist), and S1 measures only
JupyterLab shell behaviour (Lumino, split-right, size limits, cell hooks), so the result is expected to
carry over, but it is a measurement of that dist, not of current main. The dist manifest hash is in
the stamps' `inputs.dist` below. Sprint A's `--display-check` harness (A7) reruns the chrome
scenarios on CI against the freshly built dist and is the authoritative check.

## Units: every unit RECOMPUTED (none reused); no error findings; no timeouts
`result.json`: `all_units_complete = true`, `reused = []`, `timed_out = []`, `blocked = []`,
`error_findings = {}`, `measurement_valid = true`, all 13 `validity_checks` true. Each unit ran in
its own subprocess and browser context (budget 240 s, driver kill 300 s); every unit finished in
15 to 31 s, so the estimated budgets have wide headroom (recorded for D16's first-CI-run rule; not a
budget revision).

| Unit | Recomputed / reused | Duration | artifact sha256 |
|---|---|---|---|
| `widget_a` | recomputed | 17 s | `e85f66a24166241eeeeaf333b88ba896a8ac83d00db26351be197fbcefbed116` |
| `widget_b` | recomputed | 31 s | `1abae6838d9352dab0246e88fd066818d54ca5fbedc6e5f81881bb5a96947452` |
| `split_right` | recomputed | 15 s | `8fa8fa148e99bb57008fcd712d5ff0ea1e2dce6a7937f7916ebd79e02eb0aa7a` |
| `css_limits` | recomputed | 19 s | `2b7e65fb913782b872e42a7795d262167b9f2c55493c7c972aca43c8be6ff723` |
| `dock_layout_sizing` | recomputed | 17 s | `3baad0a86e8e7c7605feb172e39655a15516ab07d51b117d58ffde61f4bf585e` |
| `css_limits_refit` | recomputed | 18 s | `05b510956653dd37d07e783b03a1e456f74fa7b7b1919865cad16feafd81e600` |
| `restore_layout_keeps_iframe` | recomputed | 21 s | `bf740087472fd319b3bd25fa7e262a19141b79e77db7c024de12afc72aa12a7c` |
| `cell_hooks` | recomputed | 18 s | `0086162e11ffa88029143bc45f22fd1642edb2c1711d44b0ef78b8e852e4dcad` |
| `windowing` | recomputed | 20 s | `e7b37ddbfaf86de7b57aa3fc0988e3624db690bb35f91974fd8598a2dbe2a8bf` |
| `neg_wrong_ctor` | recomputed | 16 s | `45ac34f40cc676de9641559f976412228e173e25c95105411266114256e401d9` |

Hashed inputs (stamp `inputs`, identical across units except upstream artifact hashes):

- `args`: `e18af12957c03607e2a3e2c71f7b4e58a94e34423c0b14a9a40da808469cec12`
- `chrome`: `5275952feb3c569d43faaf9551eb35c93a9b18f38c7408656e0a2d85a09d2596`
- `dist`: `49e655b28e4a65c2b25e165948c57eceedc0d6c928ccb6038197fe5820ae0138`
- `driver`: `99b2d23e49a0904adfffd19634312ea89414d770210867114969b07da6917b33`
- `fixture`: `7ae8593749a8922bb30f6eababee0f42b3fd88d73fd315f4aabf7826e03bfdbc`
- `harness`: `53309b94d4b8e9e2c4d2a4ed4aab7913f322349f7dfee53846d18aa9a6cabe5f`
- `runner`: `814fc870d3f049c1ad4f0a20b33c5717292ba9c37e5d70aa790bdeae70713506`
- `script`: `7702944e7b696b6b8eefaceb0f008930e9282eabdcd0029f869b7ef1f3af7a6a`

## Findings (AC-1 record)
- **S1-A holds.** The root Lumino `Widget` class is reachable by walking the prototype chain of an
  existing shell widget and identified structurally (prototype owns `processMessage` and
  `onAfterAttach`, own prototype is `Object.prototype`): found at chain index **3** (minified name
  `z`); `new Ctor({node})` constructs an instance that passes `instanceof` the root, attaches, and
  `shell.add(w, 'main', {mode: 'split-right', ref})` places it beside the open notebook: notebook
  1112 -> 553.5 px, widget 553.5 px at left 848.5 (`split_right`: `side_by_side = true`,
  `orientation = horizontal`). Negative control: `Object`, `Array`, the notebook panel's leaf class
  and a subclass of the real root all fail the structural check while the real root passes
  (`neg_wrong_ctor`: `negative_control_failed_as_required = true`,
  `positive_control_structural_pass = true`).
- **S1-B is not usable, and does not need to be.** The stock `help:open` widget's iframe gets
  `sandbox="allow-scripts allow-forms"` (no `allow-same-origin`; `localStorage` throws inside it), so it
  fails the D1 S1-B criteria. This says nothing about the deck panel: C5 creates its own iframe and
  sets its own `sandbox` attribute.
- **Sizing: `css_limits_honoured = true`.** Inline CSS `min-width: 420px; max-width: 480px` on the
  widget node held after a splitter drag (limited widths 420 / 480 vs unconstrained control widths
  300 / 700; `drag_control_ok = true`, tolerance 3 px).
  **`css_limits_refit = true`:** setting the limits then `widget.parent.fit()` moves the widget from
  553.5 to 420 px (the parent is the `DockPanel`, `parent_is_dock_panel = true`).
  **`dock_layout_sizing_reachable = true`** too: `saveLayout` -> edit split-area `sizes` ->
  `restoreLayout` moved 0.5 / 0.5 to measured 0.296 / 0.691 for requested 0.3 / 0.7 (accessor
  `_dockPanel`, tolerance 0.05). D6 case is therefore **`honoured_reachable`**: every AC-36 width key
  is **asserted** (`width_key_status`: `open_width_1280_1599`, `open_width_ge_1600`,
  `drag_clamp_1280_1599`, `resize_within_wide`, `fit_after_tier_change` both tiers,
  `ac39d_ge1600_negative`). No S1-L deviation is needed.
- **`restore_layout_keeps_iframe = true`.** `restoreLayout()` re-parents nothing: the iframe node is
  the same node, its `load` event count did not change (delta 0) and the page token set before the
  call survived; the deliberate re-insertion control produced a load event and lost the token
  (`reload_control_detected = true`). So a clamp via layout sizing causes no iframe reload.
- **Cell-state hooks (five states, all reached by model ground truth; `all_states_derivable = true`):**
  - `not_run`: model (no execution count and no outputs); the prompt text is `[ ]:`.
  - `running`: model (`exec_state: running`); the prompt text is `[*]:`.
  - `ran`: a combination of model features (execution count set, not dirty, no error output).
  - `error`: a **CSS hook**, recorded by the probe as the single feature
    `mime:application/vnd.jupyter.stderr` (the exact selector or attribute is in
    `units/cell_hooks.json`; A5 reads it from there), with model `out_types: error`.
  - `stale` (edited since run): a **CSS hook**, the class **`jp-mod-dirty`** on the cell (model
    `dirty: true`).
  - `n_states_with_css_hook = 2`; the other three come from the model, so chrome.js (A5) should read
    the notebook model for `not_run`/`ran`/`running` and may use the two CSS features for `error`
    and `stale`.
- **Windowing.** `windowing_mode = contentVisibility` (read from `notebookConfig`); the 65-cell fixture
  scrolled with no DOM detach observed (`detach_observed = false`, `windowing_exercised = false`), so
  there is **no re-attach signal** (`reattach_signal = null`) and none is needed in this mode.
  Caveat for chrome.js (A5) and B9: this holds for `contentVisibility`. If `windowingMode` is ever
  `full` (JupyterLab's default in other builds, or a user setting) cells detach and the per-cell
  hooks must re-run on re-attach; A5 should read the mode at start and either assert
  `contentVisibility` or subscribe to `inViewportChanged` when it is not.
- **Console:** `widget_b` recorded one page error (the sandboxed `localStorage` access above); every
  other unit had `pageerrors = []`.

## Consequences for the spec
- D1: branch **S1-A** taken; sprint C task C5 proceeds on a real Lumino widget. D6 row: `css limits
  honoured / layout sizing reachable`: CSS at 1280-1599, layout at >= 1600; nothing recorded-only.
- No spec text needs to change for S1. Two implementer notes for A5/C5: (1) read `windowingMode`
  (above); (2) `widget.parent` is the `DockPanel` (`_dockPanel` accessor works in this build, with
  the probe's capability-scan fallback), so `dock.js` can call `parent.fit()` after tier changes.
- Reproduce: `bth sql "SELECT id, status, outcome, exit_code, command FROM runs WHERE id LIKE
  '1e0cab6d%'"` after `bth compact`; artifacts under `outputs/spikes/260929_s1/` in the sprint worktree
  (gitignored; hashes above).

