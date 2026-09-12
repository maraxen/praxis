---
title: 'REPL gate unblock: scoping R6''s manifest scan to the wheel seam (sprint 136, #5110)'
description: 'Sprint 136 plan and record: the repl.yml GATE G7 false positive that skipped all ten browser gates on the 4-PR stack, its two-defect root cause, the surface-dispatch fixer run, and the differential verification.'
status: completed
task_id: 260912_repl-gate-manifest-scope
date: '260912'
sprint: '136'
backlog_ids: '5110'
---
# REPL gate unblock: scoping R6's manifest scan to the wheel seam (sprint 136, #5110)

L5 autonomous loop, 260912. Rubric: `category=bug` -> no BRAINSTORM, adversarial TIER1,
template `bugfix_simple`. The fixer step ran on Cursor over ACP via praxia
`surface_dispatch`, per the standing instruction to use surface dispatch.

## 0. Selection

TRIAGE found no `quick`/`standard` item on the open board. What it *did* find was that
the three P1 REPL-refocus items were the only P1s, and that their premises were stale --
so the staleness pass (S1) ran first, and the sprint item came out of it rather than out
of the backlog as it stood.

While checking whether the REPL work was healthy, listing the `repl.yml` workflow runs
showed **8 consecutive failures since 260904**, every one on `coxswain-p2-pipeline` --
PR #156, the base that #157 -> #158 -> #159 all stack on. That is a P1 bug blocking four
PRs, and it was on no list anywhere. Filed as **#5110** and selected.

## 1. TRIAGE staleness pass (the loop's known gap, praxia idea-351)

TRIAGE scores items by MoSCoW/WSJF without verifying their premise still matches
reality. Last cycle six Coxswain items turned out fully shipped but open. Before scoring
the five REPL-refocus items, a Sonnet audit checked every stated claim against
`origin/main` (`c1e75d57`) -- **not** against this worktree, which is a stacked feature
branch three deep off an older base and lacks unrelated work. Three of the audit's
load-bearing findings were then spot-checked independently by the orchestrator.

| item | verdict | disposition |
|---|---|---|
| #4293 P2 spike battery | PARTIALLY SHIPPED | rescoped -> **S-E only** |
| #4294 P3 wheel pipeline | **SHIPPED** | closed |
| #4296 P5 static site | PARTIALLY SHIPPED | rescoped -> **persistence only** |
| #4297 P6 visualizer vendor | **SHIPPED** | closed |
| #4298 P7 CI gate + docs | PARTIALLY SHIPPED | rescoped -> **CLAUDE.md + debt-1293** |

Detail worth keeping:

- **#4294 closed.** `web-repl/scripts/build_wheels.py` (561 lines) is the real recipe:
  an archive-based export of the pinned submodule commit, a `+g<sha8>` stamp, and
  `manifest.json` as the single filename seam. The submodule pin is **0.2.2 /
  `dd79c4c89`**, not the 0.1.6 the item assumed -- Phase 4's pin bump already shipped.
  Independently corroborated twice: plr-sema's frozen benchmark is *named*
  `tier1-sidecar-gated-dd79c4c89`, and this sprint's own local wheel build stamped
  `0.2.2+gdd79c4c8`.
- **#4297 closed.** The visualizer is vendored at
  `web-repl/overlay/assets/visualizer/` (index.html, lib.js, vis.js, main.css, gif.js,
  gif.worker.js, img/, konva.min.js, VENDOR_MANIFEST.json), with
  `window.receiveFromPython` at `vis.js:255`. GATE G6 records 4 anchors matched exactly
  once and 5 CDN substitutions, verified idempotent.
- **#4296's two motivating claims are both false.** `web-repl/jupyter-lite.json:3` sets
  `"appUrl": "./lab"` -- the full lab surface, not a bare CodeConsole -- and lines 6-8
  pin all three storage names to fixed literals. The release-blocker data-loss seam is
  already closed. Only the P5.8 persistence ladder remains (`storage.persist()` has zero
  hits repo-wide; no File System Access path exists).
- **#4298's headline claim is false**: `.github/workflows/repl.yml` exists, 214 lines,
  citing GATE G7's rationale verbatim, running the full browser battery. What survives is
  the root `CLAUDE.md` (never authored) and debt-1293 (115 files still in
  `.praxia/docs/misc/`, `.agent/` still present in three locations).
- **#4293 is the one item that genuinely cannot be run autonomously.** Six of seven
  spikes are closed with adjudicated verdicts in
  `.praxia/docs/research/260817_g2-spike-battery-verdict.md` (overall PARTIAL-GO). S-E is
  recorded UNMET -- never reached its human pause point across four headless self-check
  attempts. It needs a human at a machine with real USB/HID/serial hardware and a
  non-headless Chromium, because `requestDevice()` needs genuine user activation, which a
  synthetic click cannot supply.

## 2. The bug (#5110)

Run **34367219312** (headSha `6f45eecb`): steps 1-11 pass -- submodule assert, deps,
vendor Pyodide, build wheels, install Chromium, build site -- then step 12 **"Wheel
coherence and contract"** fails, and steps 13-21 are all **skipped**:

> probe the kernel / offline gate / execute welcome.ipynb / fresh-notebook two-line
> bootstrap / completion (kernel) / completion (as-you-type) / visualizer render +
> praxis_viz channel / branding + vendored font integrity / the 11 pytest files

So the browser battery has never run on this stack. That is precisely the failure
`repl.yml` exists to prevent, in its own words: *"this repo shipped an unservable build
precisely because no CI gate looked at the browser."* The gate looked, went red on
something unrelated, and stopped looking.

```
COHERENCE FAIL: 9 tracked manifest.json file(s) found (R6 forbids this too, repo-wide):
['training/assemble/out/manifest.json', 'training/golden/manifest.json',
 'training/out/manifest.json', 'training/out/p26/A/train_manifest.json',
 'training/out/p26/B/train_manifest.json', 'training/out/p26/C/train_manifest.json',
 'training/out/p26b/A/train_manifest.json', 'training/out/p26c/A/train_manifest.json',
 'training/out/p26d/A/train_manifest.json']
```

**Two defects**, in `check_untracked()`:

1. **Suffix, not basename.** `_git_ls_files("*manifest.json")`. A pathspec `*` matches
   across a slash *and* matches a partial basename, so the pattern matches any path
   ending in that literal. Measured in-repo: the old pattern returns **9** paths, an
   exact-basename pattern returns **3**. The six-path difference is
   `train_manifest.json` files, which are not named `manifest.json` at all.
   `_git_ls_files`' own docstring is correct that the leading `*` is needed for any-depth
   matching (a bare literal only matches root level) but does not account for the
   partial-basename consequence.
2. **Scope.** The three genuine hits are Coxswain *training* artifacts. R6's intent is
   that `manifest.json` is the only filename seam for the browser **wheel loader** -- a
   stale tracked copy under a wheels directory would shadow the built one. A
   training-output manifest cannot shadow anything. The rule's "repo-wide, no per-name
   exception" wording predates a sibling subproject in this monorepo shipping files with
   that generic basename. The `.whl` arm's repo-wide scope *is* defensible and was left
   alone.

Note the checker gating CI had **no test file at all**, while its siblings
(`build_manifest`, `fetch_vendored_wheels`, `praxis_bootstrap_loader`) all do.

## 3. Fix

`e995de31`, two files.

- `web-repl/scripts/check_wheel_coherence.py` -- filter candidates by exact basename
  (`Path(p).name == "manifest.json"`), then scope to a new `_WHEEL_MANIFEST_PARENTS`
  covering **both** wheels directories (`web-repl/overlay/assets/wheels` and the
  stale-spec sibling `praxis/web-client/src/assets/wheels`). Module docstring updated in
  both places it states the rule, plus the argparse help and the failure message, so code
  and stated contract agree. `.whl` arm untouched.
- `web-repl/tests/test_check_wheel_coherence.py` -- NEW, four scratch-repo tests driving
  `check_untracked(repo_root=...)`, which had been made exercisable that way
  deliberately.

## 4. Gates

**Differential, run by the orchestrator against the unfixed script** (a test that passes
both ways proves nothing):

| test | vs base | vs fix |
|---|---|---|
| 1. training manifests are not a problem | **FAIL** | pass |
| 2. tracked wheels manifest still IS a problem | pass | pass |
| 3. nested tracked `.whl` still reported | pass | pass |
| 4. root-level `manifest.json` not a problem | **FAIL** | pass |

Tests 2 and 3 passing in both directions is correct and intended -- they are the
regression guards proving the narrowing disabled neither R6 nor the `.whl` arm.

**Direct proof against the tree that actually carries the nine files.** This matters
because of a branch fact worth stating plainly: **`main` has no `training/` directory at
all.** The nine manifests exist only on `coxswain-p2-pipeline` (#156) and the branches
stacked on it. So the fix branch, cut from `main`, *cannot* reproduce the false positive,
and neither could the dispatch worktree. The scratch-repo tests above are branch-independent
and do prove it -- they synthesize the real paths -- but the conclusive check is running
the fixed function against the primary checkout, which sits on `coxswain-p2-pipeline`:

```
candidates from the OLD leaky pattern:  all 9 paths, unchanged
check_untracked with the FIX applied:   NONE
```

**CI step 12 also reproduced locally, end to end** -- both commands, the second of which
has never executed in CI (the step's shell aborts at the first failure). After the wheel
build produced the wheels:

```
check_wheel_coherence.py --check-untracked  -> exit 0   "coherence OK (untracked)"
check_wheel_contract.py                     -> exit 0   "CONTRACT-OK 29"
```

Read that second block for what it is: run from a `main`-based tree, it demonstrates **no
regression** and that `check_wheel_contract.py` passes -- not that the false positive is
gone. The differential tests and the direct run above are what establish the fix.

(Before the wheels existed, `check_wheel_contract.py` fails with
`.../overlay/assets/wheels does not exist -- run build_wheels.py first` -- an environment
artifact, not a gate failure; CI satisfies it at step 9.)

**Consequence for the stack:** CI on the fix's own PR will pass with or without the fix,
since `main` has nothing to trip on. #156 picks the fix up only once #160 merges to
`main` **and** #156 gets a fresh merge-result build -- a push to its branch or a re-run.
Re-running the existing red run is not enough; it would rebuild the old merge commit.

## 5. Surface-dispatch record (dispatch `3d9768bd`)

Second production use. **One launch, one completion** -- a clean run, unlike sprint 135's
three launches.

What worked: the agent followed the dense brief exactly -- step 0 environment (submodule
init, then a full workspace sync), test first and observed red, fix, green, both gate
commands with exit codes, removal of its own `.serena/` cache, no commit. The terminal
record's unscoped status listed exactly the two intended files. It also went slightly
beyond the brief in the right direction, finding the *second* wheels directory from
`_TRACKED_OLD_WHEELS` and covering it.

Praxia-side findings, both already filed:

- **debt #1792** reproduced: `envelope.json` still appears in `git_status_unscoped` on a
  *completed* record -- the MCP-written file is outside the materialization allowlist.
- **debt #1773** reproduced: `claim_verified: null`, `files_changed_claimed: []`,
  `tests: []`. The ACP surface returns no structured self-report, so admission can verify
  nothing and the orchestrator must verify by hand. Everything in S4 was therefore run by
  the orchestrator, not taken from the agent's report.
- `containment: "none"`, `transport_used: "acp"`, no fallback -- as expected for Cursor
  over ACP (the vendored v1 ACP schema exposes no sandbox-mode surface to read).

Envelope shape correction for the record: `brief` is a **struct**
(`{goal, acceptance_criteria[], out_of_scope[]}`), not a string, and `context`
(`ContextPack`: `budget_bytes`, `rules_slice`, `prior_outputs`, `lessons`, `recon_refs`,
`files_to_read`) and `created_at` are required. Source of truth:
`praxia/crates/praxia-dispatch/src/envelope.rs`.

## 6. Outcome

| | |
|---|---|
| commit | `e995de31` on `repl-gate-manifest-scope`, cut from `main` `c1e75d57` |
| why off main | so the fix reaches PR #156's merge-result run, unblocking the stack |
| tests | 4 new, differential red-then-green verified independently |
| CI step 12 | both commands exit 0 locally |
| audit | see S7 |

## 7. Audit

**PASS**, high confidence, `required_fixes: []`, scores 5/5/4/4/4/4. Full report:
`.praxia/docs/audits/260912_sprint136-audit.md`. `code_review_diff` was not used --
praxia debt #1793 (filed this cycle) records that its `fmt` step reformats the workspace
it reviews -- so a Sonnet `praxia:reviewer` was the gate of record.

Soundness answer: **no**, the narrowing cannot hide a real R6 violation. The review
cross-checked `_WHEEL_MANIFEST_PARENTS` against every place in the codebase that reads or
writes that manifest, the decisive one being the browser loader's own
`MANIFEST_REL_PATH = "assets/wheels/manifest.json"` (`web-repl/bootstrap/transport.py:67`).
It also found a third physical manifest write at `build_repl.py:809` and correctly ruled
it out of scope (it targets the wholly-gitignored `dist/` tree). And it justified the
exact-parent match better than the brief did: a nested
`.../wheels/sub/manifest.json` cannot shadow anything because the loader fetches a fixed
literal path and never scans a subtree.

Two non-blocking suggestions, both about **pre-existing** staleness the reviewer could not
settle without Bash. The orchestrator settled it afterwards -- `git ls-files` on the old
wheels path returns nothing and the `!**/src/assets/wheels/` negation is absent from
`.gitignore`, so **P3.11 has already landed** and `_TRACKED_OLD_WHEELS`, the
gitignore-negation arm, and the second `_WHEEL_MANIFEST_PARENTS` entry are dead. Each can
only ever false-positive, never false-negative, so none blocks the merge. Filed as praxis
debt **#1795**; the second parents entry is deliberately kept as defensive scope until
that cleanup runs.
