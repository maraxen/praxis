# AGENTS.md

Harness file for the **praxis** repository. Every claim here was checked against
`origin/main` on 2026-09-14; where a rule has a non-obvious reason, the reason is given,
because a rule whose cost is invisible gets "optimised" away by the next agent.
The Bun, Praxis web client (Tech Stack, Commands, Codebase Structure) and Angular Patterns
sections were merged in from the former AGENTS.md on 2026-10-16 and were not part of that check.

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

### Bun

Default to using Bun instead of Node.js.

- Use `bun <file>` instead of `node <file>` or `ts-node <file>`
- Use `bun test` instead of `jest` or `vitest`
- Use `bun build <file.html|file.ts|file.css>` instead of `webpack` or `esbuild`
- Use `bun install` instead of `npm install` or `yarn install` or `pnpm install`
- Use `bun run <script>` instead of `npm run <script>` or `yarn run <script>` or `pnpm run <script>`
- Use `bunx <package> <command>` instead of `npx <package> <command>`
- Bun automatically loads .env, so don't use dotenv.

## Testing

**Run pytest one file at a time.** This is not a style preference — CI does it too, and
`.github/workflows/repl.yml` states why in its own comment:

> One process per file, deliberately. These tests manipulate `sys.path`, cache modules
> under synthetic names, and toggle PyLabRobot globals (`set_tip_tracking`); sharing one
> interpreter invites order-dependent failures that would be far harder to read.

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
**`disabled_manually`** and runs nothing.

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

The legacy `.agent/` directories (root, `praxis/`, `praxis/web-client/`) were **retired on
2026-09-22** (debt #1293). Don't recreate them. Old docs and prose still cite `.agent/...`
paths; the manifest at `.praxia/docs/archive/agent-dirs-retired.md` lists every removed file
and the commit to restore it from, and `.praxia/docs/migration-manifest.txt` maps the 211
files moved out earlier, on 2026-05-22.

## Conventions worth not relearning

- CI must never invoke `just`. The `justfile` is for humans.
- Don't stage another session's dirty or untracked files. This repo is worked by
  concurrent sessions and worktrees; `git add -A` will sweep up someone else's work.
- The git stash stack is shared across worktrees. Never use bare `git stash` / `git stash
  pop` — prefer a WIP commit, or `git stash push -u -m "<unique-tag>"` plus
  `git stash apply <sha>`.

---

## Project: Praxis

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Angular 21 (standalone, signals, zoneless) |
| **Language** | TypeScript (strict mode) |
| **Build** | Angular CLI / esbuild |
| **Unit Tests** | Vitest |
| **E2E Tests** | Playwright |
| **Persistence** | SQLite WASM + OPFS |
| **Python Runtime** | JupyterLite + Pyodide |

### Commands

| Action | Command |
|--------|---------|
| Dev Server | `cd praxis/web-client && bun start` |
| Build | `bun run build` |

### Codebase Structure

```text
praxis/web-client/
├── src/app/
│   ├── core/            # Services, workers, SQLite, Pyodide
│   ├── features/        # Feature modules (protocols, assets)
│   ├── shared/          # Shared components, pipes
│   └── layout/          # App shell, navigation
├── e2e/
│   ├── specs/           # Test files (*.spec.ts)
│   ├── page-objects/    # Page Object Model classes
│   ├── fixtures/        # worker-db.fixture for isolation
│   └── helpers/         # Wizard helpers
└── src/assets/browser-data/  # PLR definitions, seed data
```

## Angular Patterns (Praxis)

### Signals

```typescript
protocols = signal<Protocol[]>([]);
loading = signal(false);
filteredProtocols = computed(() => 
    this.protocols().filter(p => p.status === 'active')
);

// Template
@if (loading()) { <mat-spinner /> }
```

### Deferred Initialization

```typescript
// For heavy workers (Pyodide, Plotly) - don't init in constructor
private async ensureReady(): Promise<void> {
    if (!this.worker && this.status() === 'idle') {
        this.initWorker();
    }
}
```

---

## Pointers

- **A REPL CI gate is red and you need to reproduce it, or you are editing `check_wheel_coherence.py`** → `.praxia/docs/reference/261016_repl-gates.md`
- **Writing or running web-client Playwright specs, or running the pre-ship checklist** → `.praxia/docs/reference/261016_e2e-testing.md`
- **Searching code structurally with `ast-grep`** → `.praxia/docs/reference/261016_ast-grep.md`
- **Writing a test, fixing a bug, or about to claim work is done — on a surface without the superpowers skills** → `.praxia/docs/reference/261016_core-skill-context.md`
