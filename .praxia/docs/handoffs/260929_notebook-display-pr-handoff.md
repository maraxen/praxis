---
title: 'Notebook display epic: sprint A/B/C branches, evidence and PR handoff (overnight 260929)'
description: 'State of epic #5648 after the first execution pass: three stacked local branches (A, B, C), the test evidence per layer, what only CI or a browser can settle, the decisions waiting on the user, and how to open the PRs. Nothing is pushed.'
status: active
task_id: 260929_notebook-display-design
date: '260929'
---
# Notebook display epic: sprint A/B/C branches, evidence and PR handoff (overnight 260929)


# Notebook display epic: branches, evidence and PR handoff

Epic #5648 (spec `.praxia/docs/specs/260929_notebook-display-epic.md`, converged after 12 challenger
rounds and Revisions 1-11). **Nothing is pushed.** Merge is yours.

## The stack (all local; worktrees under `/tmp/`, branches survive them)

| Layer | Branch | Head | Commits | Based on |
|---|---|---|---|---|
| A: spikes S1-S3, chrome, staging, harness | `feat/notebook-display-sprint-a` | `95be08a8` | 25 | `origin/main` a176bac7 |
| B: `praxis.display` (reprs, ledger, errors, staleness, install), shell stale/interact, theme rules | `feat/notebook-display-sprint-b` | `7fec6b08` | +30 | A |
| C: vendored Visualizer3D `static/`, socket shim, S4 probe (deck panel to follow) | `feat/notebook-display-sprint-c-stacked` | `85f28f58` | +7 | B |
| (superseded) | `feat/notebook-display-sprint-c` | `47ff92f6` | 7 | A |

Merge order A, B, C. C is stacked on B because C5 needs B9's `stale.js`. `origin/main` is now f78c4bf2, two
documentation commits past the a176bac7 base (a plr-sema spec and the PLR phase 2 plan), so each branch needs a
rebase first. The spec, round records, research notes and the design prototype live on the local branch
`design/notebook-display` (unpushed); the prototype was also cherry-picked into A/B (`web-repl/design/notebook-display/`
in B), so push/merge the design branch for docs only, or expect duplicate-content rebases.

Suggested way to open them (yours to run, each is a new branch so no force is needed):
`git fetch origin`, then rebase A onto `origin/main`, B onto A, C onto B, `git push -u origin <branch>` for each,
open PR A against `main`, PR B against A's branch, PR C against B's branch (retarget to `main` as each merges).
CI (`.github/workflows/repl.yml`) is the authority for everything listed under "Only CI or a browser can settle".

## Evidence per layer (verified by the orchestrator by re-running, not from agent reports)

- **A.** Runner 45 passed / 3 skipped (real-Chromium case is CI-only); S1 55, S2 101, S3 64 driver tests; import 5;
  theme CSS 67 (+1 skipped); staging 8; resume 93; workflow scenarios 19; sprint A sensitivity driver 55;
  `bun test web-repl/shell/display` 72. Sidecars validate. **Three spikes RAN under bathos** (each verified by its
  record after `bth compact`, each pre-registration matched by the run's lock file, all recomputed, no error findings):
  S1 run `1e0cab6d` outcome `s1_a`, S2 run `bf83a4e6` outcome `s2_b_exec_t`, S3 run `a3458bf2` outcome `s3_combined`.
  Notes: `.praxia/docs/research/260929_notebook-display-s{1-lumino-widget,2-sanitizer,3-ipython-hooks}.md`.
  All ran against the local **260828 dist (PLR 0.2.2)**, a recorded deviation.
- **B.** svg 259, floor 109, budget 53, labware 141, deck 86, glossary 100, ledger 126, stale 59, context 126,
  errors 136, install 58, colour-vision 31, bootstrap loader 28, theme CSS 125 (+1 skipped, +1 strict xfail for the
  missing width axis), staging 13, resume 270, workflow scenarios 24, fixture 19, sprint B sensitivity driver 62;
  bun 215. All PLR-touching tests run against PLR 1.0.0b1 via `PYTHONPATH=/tmp/claude-1000/plr10` (the venv's own
  PLR is the old 0.2.2; each test asserts the tree is 1.0.0b1).
- **C.** Vendoring 61 (+2 need the submodule), S4 driver 99 (with `PRAXIS_PLR_PIN_TREE`), bun 280 (socket shim 65).
  The vendored `static/` tree is byte-identical to upstream at the pin (checked by git blob sha through the GitHub
  API), except one transformed `index.html` as D11/AC-30 require.

Not done and not claimed: A2/A3/A7/B10/C1 are **in progress** in the backlog (probes/harness authored and tested,
real runs pending); C3, C5 (running), C6, C7 not finished.

## Only CI or a browser can settle (nobody has seen these run)

From the spec's sprint notes: the real-Chromium runner case; D1/D1-dark (chrome), D2/D3/D4 (reprs, staleness, errors,
interaction, S2 reopen, high contrast) and the AC-39(a) sensitivity runs; the S4 spike (needs a dist built at the PLR
1.0 pin: `pylabrobot.visualizer3D` is absent from the local 0.2.2 dist, and the probe records `invalid` there); real
IPython behaviour of B6's `showtraceback` wrapper and B8's formatter registration (only fakes exist); B2's zero-length
round-cap tip cores rendering as dots; B9's mark survival, index drift and capture-phase key handling against Lumino;
kernel-restart status vocabulary; the banner's look; wall times against the D16 budgets (D2 is the tightest).

## Decisions and actions waiting on you

1. **A PLR 1.0 dist.** Either push A so CI builds it and runs A7b/B10b, or build one locally. Gates A7b, S4, B10b and
   all of C after C5. (Local builds need network; the sandbox proxy at `localhost:3128` refuses connections here, so an
   agent cannot fetch anything except through `gh api`.)
2. **#5671 font re-vendor** (Roboto Flex has no width axis, so condensed names do not render): needs network to Google Fonts.
3. **Confirm or overrule** the recorded interpretation calls: AC-25's ArrowRight text (spec says 50 µL, fixture gives
   100 µL), the extra pre-registered `s2_crafted_trusted` S2 outcome, the moonstone-vs-rose colour pair passing on shape only.
4. Whether to keep the entry scripts for the sensitivity runs under `scripts/spikes/` (as built) or move them to
   `scripts/negatives/` (as the spec's file plan says): a `git mv` plus a few path strings.

## Environment notes

- The unsandboxed runs need the user (`! bth run ...`): the auto-mode classifier denied the orchestrator launching
  full Chromium; the working form is in the memory file `notebook_display_epic.md` (no `--out` flag on `bth run`).
- `uv.lock` is gitignored and required by `unit_runner.driver_input()`; copy it into a fresh worktree.
- `bth compact` is slow and the shared catalog lock is contended at times; retry.
- The repo's ruff config has `fix = true`: running `ruff check` on a file rewrites it. Lint only your own new files.
- `test_plr_contract.py` has 4 tests that error locally with "wheels not built" (environment, identical on the base
  branch); CI builds the wheels.
- Six `.git/worktrees/praxis-nd-a*` entries are stuck `prunable` (bind-mount quirk); harmless.
- Entering a worktree seeds it with untracked dotfiles (`.bashrc`, `.claude/*`, `.mcp.json`, telemetry logs): never
  `git add -A` there.
