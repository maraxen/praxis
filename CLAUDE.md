# CLAUDE.md

Harness file for the **praxis** repository. Every claim here was checked against
`origin/main` on 2026-09-14; where a rule has a non-obvious reason, the reason is given,
because a rule whose cost is invisible gets "optimised" away by the next agent.

`AGENTS.md` (447 lines) predates the REPL refocus and is **partly stale** — see
[What in AGENTS.md no longer holds](#what-in-agentsmd-no-longer-holds). Where the two
disagree, this file wins.

---

## What this repo is

Praxis is a browser-hosted lab-automation environment built on PyLabRobot. Three surfaces
matter day to day:

| Path | What it is |
|---|---|
| `web-repl/` | The shipped product surface: a JupyterLite/Pyodide REPL, its build scripts, wheel pipeline, and browser gates |
| `coxswain/` | The natural-language → protocol-call copilot (FunctionGemma pipeline) |
| `praxis/` | The Angular web client and the server-side app |
| `external/pylabrobot` | Submodule. **Required** — the REPL gate's first step is `test -f external/pylabrobot/pyproject.toml` |

There is **no `repl/` directory**; the tree is `web-repl/`. Anything referring to `repl/`
is stale.

---

## Stack rules

- **Python: `uv run python`. Never bare `python`.** The repo is a uv workspace; a bare
  interpreter resolves the wrong environment or none at all.
- **JS/TS: `bun`.** The coxswain harness runs `bun test web-repl/shell/coxswain`.
- Long output → redirect to a log file, then grep for signal. Don't page it into context.

## Testing

**Run pytest one file at a time.** This is not a style preference — CI does it too, and
`.github/workflows/repl.yml` states why in its own comment:

> One process per file, deliberately. These tests manipulate `sys.path`, cache modules
> under synthetic names, and toggle PyLabRobot globals (`set_tip_tracking`); sharing one
> interpreter invites order-dependent failures that would be far harder to read.

**Never run a whole JAX/pytest suite on a local dev box.** It exhausts swap and kills the
machine; this has happened. Local runs are for a single file or a `-k` selector. Heavy
suites belong on a remote host.

⚠️ `.pre-commit-config.yaml` contains a `pytest` hook that is a bare `pytest -v` with
`always_run: true` and `pass_filenames: false` — i.e. the **whole suite**, ignoring which
files you touched. That contradicts the per-file discipline above and is exactly the shape
that kills a local box. Know it is there before you run `pre-commit run --all-files`.

The one place a whole directory is correct is coxswain, which CI runs as
`uv sync --all-packages` then `uv run --no-sync pytest coxswain/tests -q`. The
`--all-packages` / `--no-sync` pair is load-bearing: without it the workspace member is
not installed (`ModuleNotFoundError`), and without `--no-sync` pytest syncs it back out.

## The gates that actually run

`.github/workflows/repl.yml` ("REPL") is the gate with teeth. `ci.yml` is
**`disabled_manually`** and runs nothing. The REPL workflow has two jobs:

**Build + browser gates** — vendor Pyodide → build wheels → install Chromium → build the
site → then, in order:

```bash
uv run python web-repl/scripts/build_repl.py --base-path /praxis/
uv run python web-repl/scripts/check_wheel_coherence.py --check-untracked
uv run python web-repl/scripts/check_wheel_contract.py
uv run python scripts/repl_smoke.py --probe            --base-path /praxis/
uv run python scripts/repl_smoke.py --probe --offline  --base-path /praxis/
uv run python scripts/repl_smoke.py --notebook-check   --base-path /praxis/
uv run python scripts/repl_smoke.py --fresh-boot-check --base-path /praxis/
uv run python scripts/repl_smoke.py --completion-check --require-jedi ...
uv run python scripts/repl_smoke.py --typeahead-check  --base-path /praxis/
uv run python scripts/repl_smoke.py --viz-check        # no base path, by design
# then web-repl/tests/*.py, one pytest process per file
```

**Coxswain pytest + JS harness** — the coxswain suite plus `bun test`.

Reproduce a gate failure with the exact command above; do not approximate it.

### The wheel-coherence seam

`check_wheel_coherence.py` guards the boundary between built wheels and what is tracked in
git. Its manifest scan is **deliberately scoped** to the wheel directories
(`_WHEEL_MANIFEST_PARENTS`), because `_git_ls_files("*manifest.json")` is a git pathspec
**suffix** match, not a basename match — unscoped, it swept up
`training/**/train_manifest.json` and failed the gate on files that have nothing to do with
wheels. Keep the manifest arm scoped; the `.whl` arm is intentionally repo-wide.

## Landing a change

- Branch, then open a PR. **Never push to `main`, force-push, or merge someone else's work.**
- `main` is governed by a **ruleset** (`main-CI`), not classic branch protection — so
  `gh api repos/maraxen/praxis/branches/main/protection` returns a misleading
  `404 Branch not protected`. Read `gh api repos/maraxen/praxis/rules/branches/main`.
- That ruleset requires one approving review plus status checks `test (3.10|3.11|3.12)`,
  which come from the **disabled** `ci.yml` and therefore can never turn green. Every merge
  to `main` is consequently an owner `--admin` bypass. **An agent must not perform it** —
  let the REPL gate finish, then hand the merge to a human.
- A `pull_request` run builds the *merge result*. Re-running an old red run rebuilds the
  **old** merge commit and proves nothing; to pick up a fix that landed on `main`, use
  `gh pr update-branch <n>`, or merge `main` in and push when the branch has conflicts.

## Documentation

Internal docs live at `.praxia/docs/<category>/YYMMDD_slug.md` — categories `daily`,
`plans`, `handoffs`, `specs`, `audits`, `research`, `decisions`, `reference`, `roadmaps`,
`archive`, `misc`. Prefer the praxia docs tool's `add` action over hand-authoring; it
resolves the path and stamps frontmatter.

**`.praxia/docs/INDEX.md` is generated. Never hand-edit it.** Regenerate with the docs
tool's `index` action. On a merge conflict in `INDEX.md`, take either side and regenerate —
it is deterministic, so there is nothing to resolve by hand. Always pass an absolute
`workspace` to docs/backlog/debt calls; the MCP server binds its workspace once per process
and will otherwise write against the wrong checkout.

Public docs (`README.md`, `docs/`, `CONTRIBUTING.md`, this file, `AGENTS.md`) are out of
scope for that convention.

## Conventions worth not relearning

- **`py2dmol` / `py2Dmol` is a real package** (sokrypton/py2Dmol) and is **never** a typo
  for `py3Dmol`. Do not "correct" it.
- CI must never invoke `just`. The `justfile` is for humans.
- Don't stage another session's dirty or untracked files. This repo is worked by
  concurrent sessions and worktrees; `git add -A` will sweep up someone else's work.
- The git stash stack is shared across worktrees. Never use bare `git stash` / `git stash
  pop` — prefer a WIP commit, or `git stash push -u -m "<unique-tag>"` plus
  `git stash apply <sha>`.

---

## What in AGENTS.md no longer holds

`AGENTS.md` remains useful for Angular signal patterns, Playwright wait strategies, and its
TDD / systematic-debugging / verification-before-completion sections. These parts are stale:

- **"Current State (2026-01-31)"** — over seven months old; the pass/fail lists there are
  not evidence about the tree today.
- **`npx playwright test` as the E2E entry point** — there is no npm `e2e` script. The
  browser gate is Python/Playwright-driven through `scripts/repl_smoke.py`, orchestrated by
  `repl.yml`.
- **`.agent/staging/e2e_autonomous_handoff.md`** — `.agent/` exists in three places
  (`.agent/`, `praxis/.agent/`, `praxis/web-client/.agent/`) and is slated for migration
  into `.praxia/docs/`. Don't add to it.
- **Bun-for-everything** — correct for the JS harness and the web client, but the REPL
  surface and every gate above are Python via `uv`.
