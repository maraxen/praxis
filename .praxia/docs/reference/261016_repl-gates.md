---
title: 'REPL CI gates and the wheel-coherence seam'
description: The ordered REPL gate commands, the two CI jobs, and why the wheel-coherence manifest scan is scoped; moved verbatim out of the always-on harness file.
status: active
task_id: 261016_harness-fleet-audit
date: '261016'
---

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
