---
title: 'Zero-action first-run setup for the PyLabRobot REPL (debt #1396)'
description: Spec for bootstrapping PyLabRobot automatically on every Pyodide kernel start, fail-closed and visible, with no user-typed setup
status: draft
task_id: 260914_first-run-setup
date: '260914'
backlog_ids: ''
adversarial_review: 'round1 REVISE->revised; round2 REVISE (1 MAJOR)->revised 260914 (challenge_r1, defense_r1, adjudication_r1, challenge_r2)'
---
# Zero-action first-run setup for the PyLabRobot REPL (debt #1396)

## Overview

Every Pyodide kernel in the lab should run the Praxis bootstrap on its own when it
starts. The user's first cell waits for it to finish. If setup fails, that cell (and
every later cell) shows the error instead of running on a half-configured kernel. The
user never types setup code. The whole design depends on the S0 spike (section 5).

## 1. Problem

A fresh kernel has no `pylabrobot` (`praxis_boot.py:10-15`). Today the user has to run
`import praxis_boot; await praxis_boot.setup()`, or welcome.ipynb cell 3, once per
kernel session and again after every reload or restart (welcome.ipynb cell 1:
"re-run the bootstrap cell below after each reload or kernel restart"). If they forget,
the first `import pylabrobot` fails with `ModuleNotFoundError` and nothing explains why.

## 2. Non-goals

- The Angular playground (`praxis/web-client`). It has its own JupyterLite config
  (`praxis/web-client/src/assets/jupyterlite/jupyter-lite.gh-pages.json`) and its own
  bootstrap snippet (`playground-jupyterlite.service.ts:278-292`). Nothing here
  changes it. The `praxis_main` guard in T2 only makes it safer if the two ever share
  a build.
- Opening a device automatically. Web Serial/WebUSB still need a user gesture
  (welcome.ipynb cell 7).
- Making setup faster, or caching the environment across kernel sessions.
- The REPL app's `?code=&execute=1` path. It uses the same kernel, so it gets
  auto-setup for free, but it is not a design target.
- A federated JupyterLab labextension (constraint 5). It is only reconsidered under
  fallback G (section 6.3), and that needs a human decision.

## 3. Acceptance criteria

Each criterion is proved by the gate named in section 8.

- **AC-1 (zero action).** In a fresh lab kernel, a first cell containing only
  `import builtins, pylabrobot; from pylabrobot.io.serial import Serial; print(Serial is builtins.WebSerial)`
  prints `True` and has execute status `ok`. No setup code is typed or run by the
  harness or by any notebook cell. The same fresh kernel also resolves the bare
  playground names the legacy bootstrap cell provided, WITHOUT an import:
  `LiquidHandler.__name__ == "LiquidHandler"` and `STAR` is defined (section 6.2
  `_run_setup` step 6, T3b), asserted in `--fresh-boot-check`.
- **AC-2 (first cell waits).** A first cell sent the moment the kernel reports idle
  (before setup could have finished) still meets AC-1, and `praxis_boot.gate_waited is True`,
  where `gate_waited` is set only when the gate saw `state == "running"` on entry for
  that cell (section 6.2). Asserted in `--fresh-boot-check` (section 8.3), which always
  delays the async pylabrobot wheel fetch so the wait is deterministic, not timing luck.
- **AC-3 (fail-closed and visible).** If any bootstrap stage fails, the user's first
  cell gets execute status `error`. Its visible output contains `PraxisAutoSetupError`
  plus the failing stage's reason, and none of the cell's own code runs (a side-effect
  sentinel in the cell is not set). Every later cell behaves the same way until
  recovery (AC-5).
- **AC-4 (post-condition kept).** Auto-setup only reports `ready` after `_verify()`
  passes: `pylabrobot` is importable and `pylabrobot.io.serial.Serial is builtins.WebSerial`.
  If `praxis_main` returns without raising but `_verify()` fails, that counts as a
  failure under AC-3.
- **AC-5 (manual path still works).** In a ready kernel, `await praxis_boot.setup()`
  prints `already bootstrapped` and does not run the loader a second time. In a failed
  kernel, a cell calling `await praxis_boot.setup()` is let through the gate; when it
  succeeds, later cells run normally.
- **AC-6 (no double-run).** At most one COMPLETED `praxis_main` stage sequence runs per kernel
  (a retry after a failed sequence is allowed, AC-5),
  however auto-setup, `praxis_boot.setup()` and a direct legacy
  `exec(...); await praxis_main(root)` cell are mixed. `setup(force=True)` is the only
  deliberate exception.
- **AC-7 (restart).** After a kernel restart, AC-1 holds again, and `praxis_boot.kernel_nonce`
  differs from the value before the restart (proving it is a new interpreter).
- **AC-8 (sha pin kept).** Loader verification against `_LOADER_MODULE_SHA256` is
  unchanged. No new path fetches and executes code. The existing
  `test_praxis_bootstrap_loader.py` sha tests still pass unmodified, and the
  fault-injection gate (AC-3) is also run with a tampered `bootstrap/stages.py`.
  *Trust root (unchanged from today):* `bootstrap/praxis_bootstrap.py` is fetched
  same-origin with an HTTP status check and no sha pin (`praxis_boot.py:143-159`); the
  sha pin covers `stages.py`/`transport.py` only.
- **AC-9 (drift detected at build time).** The build fails if (a) the runtime
  `dist/jupyter-lite.json` does not carry
  `loadPyodideOptions.env.PYTHONSTARTUP == "/drive/praxis_startup.py"`, (b) that file
  is not staged and indexed, or (c) the vendored pyodide-kernel wheel no longer
  contains the awaited-transform internals the gate relies on, including the
  cleanup-before-line transform loop order (section 7 row 10, T5).
  A pyodide-kernel or IPython change that drops env passthrough or PYTHONSTARTUP
  handling is NOT detectable at build time; it is detected at runtime by
  `--fresh-boot-check` only.
- **AC-10 (docs match behaviour).** welcome.ipynb and the `praxis_boot.py` docstring
  no longer tell users to run setup. No **code cell** of any notebook shipped under
  `web-repl/files/` contains any of the shared forbidden list `praxis_main(`,
  `praxis_boot.setup(`, `HOST_ROOT =` (checked by a unit test, section 8.1, and by the
  notebook-check and fresh-boot static checks, section 8.3; all three use the same list
  and scan code cells only). The list deliberately does not contain a bare `setup(`, so
  PyLabRobot's normal `await lh.setup()` stays allowed in shipped device notebooks.
  Markdown cells may mention `praxis_boot.setup()`.
- **AC-11 (existing gates).** Every current repl.yml step passes on the new build,
  with the premise changes from section 8.

## 4. Design alternatives

| # | Design | Verdict | Why |
|---|---|---|---|
| A | **Startup file + per-cell async gate.** `loadPyodideOptions.env.PYTHONSTARTUP` points at a `/drive` file. That file schedules setup and registers an async cell transform that waits for it | **Chosen (S0 passed, 260914)** | IPython runs PYTHONSTARTUP during kernel init, on every kernel including restarts (F1). `/drive` is already mounted by then (F2). The env var can be set from jupyter-lite.json (F3). The transform is async and runs before every cell (F6), which fixes both the race (F5) and the invisible startup output (F4): the error is raised inside the cell itself. Needs no JS and no labextension |
| B | **JS shell auto-executes the bootstrap.** praxis-shell.js detects a new kernel and dispatches code | Rejected | There is no clean "fresh kernel ready" signal (F7, jupyterlab#11620). Lab command dispatch can silently do nothing behind a Select Kernel dialog, and run-all promises can hang (F7). Output from `requestExecute` is not tied to a cell, so failures are invisible (F7). Fails constraint 1 |
| C | **One-click shell button/banner** | Rejected as primary | Not zero-action. Clicking still has to execute code in the kernel, so it hits the same dispatch problems as B (F7). Only justified if A is proven unsafe, and A's one hazard (the race, F5) is closed by the gate |
| D | **Startup file only, no gate** | Rejected | The user's first cell races setup (F5), and failures are invisible (F4). Fails AC-2 and AC-3 |
| E | **A + shell status banner** fed by `praxis:ready` / `praxis:error` | Deferred (T9, optional) | Banner would add page-level visibility. It is not needed for AC-1..11. `praxis:error` is broadcast to every kernel in the origin, so the banner could not tell which kernel failed without new correlation fields. Kept as the out-of-band detector in fallback F |
| F | IPYTHONDIR profile startup dir instead of PYTHONSTARTUP | Fallback B1 only | Same machinery (F1), but it needs a directory tree in the contents drive. Dot-directories may not be indexed. Only used if PYTHONSTARTUP specifically is not honoured |
| G | Federated labextension | Rejected (constraint 5) | Section 6.3 is the only path back to it |

**Zero-action is feasible.** S0 confirmed F3 and F6 in a real browser (section 5), so
no one-click design is proposed as the primary.

## 5. S0 spike gate

The primary design (sections 6.1-6.2) goes ahead only if the parallel browser spike
observes all of the following in a built site with pinned jupyterlite-core 0.8.1,
pyodide-kernel 0.8.2 and pyodide 314.0.1, served under `/praxis/`. Evidence must come
from cell outputs or execute_reply content, never from console text alone.

| ID | Must observe | Required for |
|---|---|---|
| S0-1 | With `litePluginSettings["@jupyterlite/pyodide-kernel-extension:kernel"].loadPyodideOptions.env.PYTHONSTARTUP` set, a file at that `/drive` path runs during kernel init. It sets `builtins.__praxis_s0`, which a later cell can read | A |
| S0-2 | Setting `env` does not break Pyodide's default environment: in a cell, `os.environ["HOME"]` is what it was without the key, and `os.getcwd() == "/drive"` | A |
| S0-3 | `import praxis_boot` works from inside the startup file | A |
| S0-4 | A coroutine started with `asyncio.ensure_future` in the startup file runs to completion (including a `micropip`/`pyodide.http` await) without any cell being executed | A |
| S0-5 | An async callable inserted at `get_ipython().kernel.lite_transform_manager.cleanup_transforms[0]` is awaited before the first cell runs. Test: the scheduled task sleeps 5 s, and a cell sent at kernel-idle sees it done | A (AC-2) |
| S0-6 | If the transform returns `["raise RuntimeError('S0-probe')\n"]`, the notebook cell shows the traceback and execute status `error`, and a side-effect sentinel in the original cell is not set | A (AC-3) |
| S0-7 | After a kernel restart (kernel API `restart()`), S0-1 and S0-5 hold again with a new nonce | A (AC-7) |
| S0-8 | `print()` inside the transform shows up in the executing cell's output | "waiting…" line only. If this fails, drop the line; A still proceeds |
| S0-9 | Informational: what an exception raised inside the transform looks like in the UI. The design must not depend on it | — |
| S0-10 | Informational: whether completions answer while setup is still running (typeahead gate interplay) | risk R6 |

**Decision rule**
- S0-1..S0-7 all pass: build sections 6.1-6.2 (primary).
- S0-1 fails but env is honoured (for example, a test var shows up in `os.environ`): fallback **B1**. Same design, but set
  `IPYTHONDIR=/drive/praxis_ipython` and ship `files/praxis_ipython/profile_default/startup/00-praxis.py`
  instead of PYTHONSTARTUP. S0 is re-run for that variant, and that re-run also records
  which directories/files IPython creates under `/drive/praxis_ipython` (they become
  visible IndexedDB entries in the file browser).
- S0-1..S0-4 pass but S0-5 or S0-6 fails: fallback **F** (section 6.3).
- `env` is not honoured at all (S0-1 and B1 both fail): fallback **G** (section 6.3). Stop and escalate.

### 5.1 Observed results (spike, 260914) — DECISION: primary design proceeds

Setup: a copy of `web-repl/dist` served locally, driven through `lab/index.html` with
Playwright/Chromium. Raw evidence: `/tmp/claude-1000/spike1396/result.json`
(re-verified by the orchestrator). Spike experiment ids E1-E6 map onto the S0 rows as
follows. Evidence is from cell output models and DOM tracebacks, not console text.

| Spike | S0 row(s) | Result | Observed |
|---|---|---|---|
| E1 | S0-1 (S0-3 partial) | PASS | PYTHONSTARTUP set ONLY in the ROOT `jupyter-lite.json` `litePluginSettings["@jupyterlite/pyodide-kernel-extension:kernel"].loadPyodideOptions.env` is honoured by the lab app. The app-level `lab/` and `repl/` `jupyter-lite.json` carry no `litePluginSettings` and inherit it. The startup file set a builtins flag read by cell 1 (`E1_STARTUP_RAN True`), and `get_ipython()` works inside the startup file (`E1_IP_SOURCE get_ipython`). `import praxis_boot` from the startup file was not separately exercised; `--fresh-boot-check` (`autostart_origin == "PYTHONSTARTUP"`) covers it at runtime |
| E2 | S0-5, S0-4 (partial) | PASS | An async `cleanup_transforms` gate blocked the first cell: 20 s fake setup → `gate_delay_s` 16.11 after `boot_to_notebook_ready_s` 9.79; cell 1 printed `E2_SETUP_DONE True`. The scheduled coroutine ran to completion. A `micropip`/`pyodide.http` await inside it was not exercised (covered at runtime by `--fresh-boot-check`). **Caveat:** a 1-3 s setup is fully absorbed by the ~9.8 s kernel boot (`gate_delay_s` ~0.05-0.1), so a gate test only proves waiting when setup outlasts boot (drives the `gate_waited` design in section 8.3) |
| E3 | — | PASS | Later cells run normally; a user `1/0` renders a normal `Cell In[3], line 1` traceback |
| E4 (caught) | S0-6 | PASS | The gate caught the task exception and REWROTE the cell to `raise RuntimeError('praxis setup failed: ...')`: a clean `Cell In[1], line 1` traceback in the output model and DOM, none of the original cell's prints appeared, kernel `idle`, no pageerrors |
| E4 (uncaught variant) | S0-9 | Informational, NEGATIVE | A transform that RAISES produces a visible internal traceback (`kernel.py:104` → `litetransform.py:32`) BUT also JS pageerrors `['PythonError', "Cannot set properties of undefined (setting 'execution_count')"]` and kernel `busy` at snapshot. **Normative rule derived from this:** the gate, and any inline startup-file gate, MUST catch every exception and rewrite the cell; nothing may raise out of `transform_cell` (section 6.2, failure mode 16) |
| E5 | S0-7 | PASS | `notebook:restart-run-all` re-ran the startup file on the new kernel (23.8 s; cell 1 again `E1_STARTUP_RAN True` / `E2_SETUP_DONE True`). No per-kernel nonce was checked, so the nonce-based `--restart-check` stays |
| E6 | — | PASS (note) | `%pip list` coexists with the gate. It produced 0 captured outputs; unexplained and unrelated to the gate. Note only |
| — | S0-2 | Not measured | `HOME`/`cwd` under a set `env` were not probed. The kernel booted normally and `/drive` was mounted. Non-blocking; a regression would surface in `--fresh-boot-check` / `--notebook-check` |
| — | S0-8 | Not measured | The "waiting…" print is therefore omitted from the gate (section 6.2) |
| — | S0-10 | Not measured | Stays risk R6, covered by `--typeahead-check` |

Further observations:
- `notebook:run-all-cells` halts at the first raising cell. So a gated setup failure
  stops a run-all at cell 1, which makes `--notebook-check` fail loudly rather than
  run later cells on a bare kernel.
- The spike's claim that `repl/index.html` lacks the injected shell is FALSE: all six
  app `index.html` files carry it (`inject_shell.py` `discover_targets`, lines 295-312).
  It has no bearing on this design.

**Decision.** S0-1, S0-5, S0-6 and S0-7 were observed passing; the unmeasured parts of
S0-2..S0-4 are covered by runtime CI gates. The primary design (sections 6.1-6.2)
proceeds. Fallbacks B1, F and G (section 6.3) are NOT taken and stay documented only.

## 6. Chosen design

### 6.1 Components and files

| File | Change |
|---|---|
| `web-repl/jupyter-lite.json` | Add `"loadPyodideOptions": {"env": {"PYTHONSTARTUP": "/drive/praxis_startup.py"}}` next to `disablePyPIFallback` (lines 19-21). Lands in T7, together with the `repl_smoke.py` premise change, never before it |
| `web-repl/files/praxis_startup.py` (new) | Startup shim, about 30 lines. No setup logic of its own; only the inline fallback gate (6.2) |
| `web-repl/files/praxis_boot.py` | Gains the state machine, in-flight lock, `_autostart()`, `_gate_cell()`, `PraxisAutoSetupError`, `status()`. `setup()` stays compatible |
| `web-repl/bootstrap/praxis_bootstrap.py` | Two additive changes to `praxis_main`: keyword `raise_on_error: bool = False`, and a kernel-wide once-guard. The `_LOADER_MODULE_SHA256` marker line and `_bootstrap_loader_modules` do not change |
| `web-repl/files/welcome.ipynb` | Remove the bootstrap cell, rewrite the docs cells (6.5) |
| `web-repl/scripts/build_repl.py` | Retire the `HOST_ROOT` rewrite, add assertions for startup env, startup file and kernel-internals contract |
| `scripts/repl_smoke.py` | Premise changes and new modes (section 8) |
| `.github/workflows/repl.yml` | New steps and test files |

`web-repl/bootstrap/stages.py` and `transport.py` do not change, so the stamped shas
move only when their bytes do (AC-8).

### 6.2 Runtime behaviour

**Startup file** (`/drive/praxis_startup.py`). IPython runs it with `safe_execfile` in
the user namespace (F1), so it must not leave names behind:

```python
try:
    import praxis_boot as _praxis_boot
    if getattr(_praxis_boot, "AUTOSETUP_PROTOCOL", None) != 1:
        raise RuntimeError("praxis_boot.py in your drive is not the shipped version "
                           "(AUTOSETUP_PROTOCOL mismatch)")
    _praxis_boot._autostart(origin="PYTHONSTARTUP")
except BaseException as _praxis_exc:
    # Inline catch-and-rewrite gate. Needs no praxis_boot import.
    # Guarded formatting (R2-5): the exception's own __repr__ may raise.
    try:
        _praxis_detail = repr(_praxis_exc)
    except BaseException:
        _praxis_detail = "<unprintable exception>"
    try:
        _praxis_msg = (
            "PraxisAutoSetupError: praxis auto-setup could not start: " + _praxis_detail
            + ". Your cell was NOT run. "
            "A copy of praxis_boot.py or praxis_startup.py saved in this browser shadows "
            "the shipped one: delete or restore it in the file browser, then restart the kernel."
        )
    except BaseException:
        _praxis_msg = "PraxisAutoSetupError: praxis auto-setup could not start. Your cell was NOT run."
    try:
        async def _praxis_inline_gate(lines, _m=_praxis_msg):
            try:
                return ["raise RuntimeError(" + repr(_m) + ")\n"]
            except BaseException:
                return ["raise RuntimeError('PraxisAutoSetupError: praxis auto-setup could not start')\n"]
        get_ipython().kernel.lite_transform_manager.cleanup_transforms.insert(0, _praxis_inline_gate)
    except BaseException:
        pass  # kernel internals missing: T5 build contract + --fresh-boot-check
finally:
    for _praxis_n in ("_praxis_boot", "_praxis_detail", "_praxis_msg", "_praxis_inline_gate"):
        globals().pop(_praxis_n, None)
    globals().pop("_praxis_n", None)
```

Any exception escaping this file would be swallowed invisibly (F4), so nothing may
escape it. `_autostart` does all of its own error handling and records failures in
state, so the `praxis_boot` gate can show them. The `except BaseException` branch covers
the two cases `_autostart` cannot: `import praxis_boot` itself failing, and a protocol
mismatch (section 7 row 11). The inline gate blocks every cell with an error naming the
cause, and like every gate it only ever returns a rewrite, never raises (S0 E4 rule).
Every message built on this path goes through a guarded formatter with a static
fallback string that still contains the literal `PraxisAutoSetupError`, so an exception
whose `__repr__`/`__str__` raises still installs the inline gate (R2-5).
A user-deleted or user-edited `/drive/praxis_startup.py` (IndexedDB-shadowed) is not
covered by this branch; see R3.

**`praxis_boot` state** (module-level; the module stays a singleton in `sys.modules`):
- `state: Literal["idle", "running", "ready", "failed", "dismissed"] = "idle"`
- `host_root: str | None` (existing, still set only on success)
- `failure: BaseException | None`
- `gate_waited: bool` (default `False`; set `True` only when `_gate_cell` enters with `state == "running"`)
- `kernel_nonce: str` (`secrets.token_hex(8)`, set at import)
- `autostart_origin: str | None`
- `_task: asyncio.Future | None`
- `_lock: asyncio.Lock` (created lazily inside a coroutine, not at import time)
- `AUTOSETUP_PROTOCOL = 1`

**`_autostart(origin)`** (synchronous, must never raise):
1. If `_task is not None`, return (idempotent).
2. Set `autostart_origin = origin`.
3. `shell = IPython.get_ipython()`, then `manager = shell.kernel.lite_transform_manager`.
   If that lookup fails, set `state = "failed"`, set `failure = RuntimeError("pyodide-kernel internals changed: …")`,
   and return. (The build contract in T5 is the real safeguard for this case.)
4. `manager.cleanup_transforms.insert(0, _gate_cell)`, unless it is already there.
   `cleanup_transforms` runs before `line_transforms`, which hold `pip_magic`
   (litetransform.py:22-31). That means a first cell of `%pip install x` also waits.
5. `state = "running"`, then `_task = asyncio.ensure_future(_run_setup(auto=True))`.

**`_run_setup(host_root_override=None, *, force=False, auto=False)`** is the old
`setup()` body, with these changes:
1. `async with _lock`, so there is only ever one run at a time.
2. If `state == "ready"` and not `force`, return `host_root` (and print `already bootstrapped …` when not `auto`).
3. Derive the root, sync-XHR `bootstrap/praxis_bootstrap.py`, and exec it into a
   private namespace (unchanged, `praxis_boot.py:138-166`).
4. `await praxis_main(root, raise_on_error=True)`. The real exception propagates,
   with the stage's reason and traceback, after `praxis:error` has been posted.
5. `version = _verify()`. This is the AC-4 post-condition and is unchanged.
6. On success: set `host_root`, `state = "ready"`, `failure = None`. Print the ready
   line only when not `auto`.
   **Playground names (T3b, gap found in execution 260914, audit
   `260914_first-run-setup_gap_playground_ns`).** Before setting `state = "ready"`,
   call `web_bridge.bootstrap_playground(<IPython user_ns>)` so the user namespace
   gets the same names the legacy welcome bootstrap cell provided: `LiquidHandler`,
   `LiquidHandlerBackend`, every `*Backend` class and `STAR` (web_bridge.py:1385-1440).
   Why: that cell exec'd the loader into the NOTEBOOK globals, so `praxis_main`'s
   `bootstrap_playground(globals())` (praxis_bootstrap.py:392) reached the user;
   `_run_setup` execs it into a private dict, and `_import_resources`
   (praxis_bootstrap.py:181-191) only puts `pylabrobot.resources` names on `builtins`.
   Without this, a notebook writing `LiquidHandler(backend=STAR(), deck=...)` without
   imports gets `NameError` once T6 removes the welcome cell. Get the namespace via
   `IPython.get_ipython().user_ns`; if there is no shell (CPython tests) skip. Guarded:
   any exception here is swallowed and does NOT fail setup (the post-condition is
   `_verify`, not ergonomics). Safe to call again: its builtins shim re-injection was
   deleted (web_bridge.py:1441-1455) and its stdout redirect is skipped because
   `builtins._PRAXIS_JUPYTERLITE` is already True. The loader and the sha-pinned
   `stages.py`/`transport.py` do not change.
7. On any `BaseException` (except `CancelledError`, which is re-raised): set
   `state = "failed"` and `failure = exc`. Re-raise when not `auto`. When `auto`,
   swallow it, because the gate is what surfaces it.

**`setup(host_root_override=None, *, force=False)`** is the public API; signature and
return value do not change. If a `_task` is still pending, it awaits
`asyncio.shield(_task)` first. Then it returns `await _run_setup(host_root_override, force=force)`.
In a ready kernel this prints `already bootstrapped` (AC-5). In a failed kernel it
retries.

**`_gate_cell(lines: list[str]) -> list[str]`** (async; its whole body sits in
`try/except BaseException`). **Normative (S0 E4):** the gate must catch every
exception and rewrite the cell; it must never raise out of `transform_cell`. A raising
transform leaves the kernel `busy` and throws JS pageerrors
(`Cannot set properties of undefined (setting 'execution_count')`). The body is a
dispatch on `state`:
1. If `state in ("ready", "dismissed")`, return `lines` unchanged. This is the
   steady-state cost: one comparison per cell.
2. If `state == "running"`: set `gate_waited = True`, then `await asyncio.shield(_task)`
   **exactly once for this cell** (catching any exception the task ended with), then
   **re-dispatch once through steps 1, 3 and 4, re-reading `state`; never back into
   step 2**. A task that ended `failed` therefore reaches step 3, and one that ended
   `ready` returns the original lines. No "waiting…" print (S0-8 not measured).
   Liveness rules (R2-4):
   - **Task done but state still `running`** (for example the task was cancelled:
     `_run_setup` re-raises `CancelledError` without recording state): set
     `state = "failed"` and `failure = RuntimeError("praxis auto-setup task ended without a result")`,
     with `__cause__` set to the task's exception (or the `CancelledError`) when one is
     available. Then continue to step 3.
   - **The wait itself is interrupted** (`KeyboardInterrupt` or `CancelledError` raised
     into the gate while awaiting): do not re-await and do not re-raise. Return
     `["raise __import__('praxis_boot').PraxisAutoSetupError('praxis auto-setup was interrupted while this cell waited for it. Your cell was NOT run; re-run it, or run await praxis_boot.setup().')\n"]`
     (a static string). The shielded task keeps running, so the next cell waits for
     it again, at most once. There is no unbounded re-dispatch loop.
   - Any other state still `running` after the single wait (task not done, wait not
     interrupted; should be impossible) goes to step 4.
3. If `state == "failed"`: when the joined source contains `praxis_boot`, return
   `lines` unchanged (this is the recovery path, AC-5). Otherwise return
   `["raise __import__('praxis_boot')._gate_error()\n"]`.
4. If the gate itself hits an internal error (including any other `state` value),
   return `["raise RuntimeError(" + repr("PraxisAutoSetupError: praxis auto-setup gate error: " + _safe_repr(exc)) + ")\n"]`.
   The whole step-4 build sits in its own `try`; if it fails, return the static line
   `["raise RuntimeError('PraxisAutoSetupError: praxis auto-setup gate error')\n"]`.

**`_safe_repr(obj, fallback="<unprintable exception>") -> str`** (R2-5): returns
`repr(obj)`, or `fallback` if `repr` raises anything (`BaseException`). Every error
message built in `praxis_boot` (gate step 4, `_gate_error`, `status()`) formats
exceptions only through `_safe_repr` / an equivalent guarded `str`.

The replacement never adds lines in front of user code; it either returns the lines
untouched or replaces them all. That keeps `%%cell` magics and traceback line numbers
intact on the success path.

**`_gate_error()`** returns `PraxisAutoSetupError(msg)` with `__cause__ = failure`.
The message says: PyLabRobot setup failed in this kernel, then `failure`'s type and
message, then the site root if it was derived, then: "Your cell was NOT run. Retry with
`await praxis_boot.setup()` in a cell, restart the kernel, or run
`praxis_boot.dismiss()` to use this kernel without PyLabRobot." The message is built
with guarded formatting (R2-5): the whole construction sits in `try/except BaseException`,
and on any failure `_gate_error()` still returns `PraxisAutoSetupError` with the static
message "PyLabRobot setup failed in this kernel (details unavailable). Your cell was NOT
run. Retry with `await praxis_boot.setup()`, or restart the kernel." (and `__cause__`
still set to `failure` when that assignment itself succeeds). Because the exception
is raised inside the cell's own execution, it becomes a normal traceback with status
`error` (S0-6). Two failures get different recovery text:
- **`_verify()` failed after `praxis_main` completed** (failure mode 6): the once-guard
  flag is already set, so a `setup()` retry skips the stages and fails `_verify` again.
  The message says: "setup completed but the result is broken; `praxis_boot.setup()`
  cannot fix this — restart the kernel."
- **D1 shell-sha mismatch** (failure mode 12): the message says: "another Praxis tab
  from an older deploy on this site answered first. Close other Praxis tabs from an
  older deploy, then restart the kernel."

**`dismiss()`** sets `state = "dismissed"`, but only while `state == "failed"`. The
call passes the gate because its source contains `praxis_boot`. Open question OQ-2.

**`status()`** prints exactly one line, `praxis auto-setup state: <state>` (for example
`praxis auto-setup state: ready`), with no other prefix or suffix, then returns a dict:
`state`, `host_root`, pylabrobot version, `autostart_origin`, `kernel_nonce`, `failure`
(via `_safe_repr`, `None` when there is no failure). `--notebook-check` matches the
literal `praxis auto-setup state: ready` (sections 6.5, 8.3).

**`praxis_main` changes** (praxis_bootstrap.py:289):
- Signature becomes `async def praxis_main(host_root: str, *, raise_on_error: bool = False)`.
  Positional callers (Angular snippet, legacy notebook cells) behave exactly as before.
- Once-guard. At entry, if `getattr(builtins, "_PRAXIS_BOOT_DONE", False)` is true,
  log `[Bootstrap] already bootstrapped in this kernel; skipping`, post `praxis:ready`,
  and return. (Re-posting ready keeps playground-style listeners working; see OQ-3.)
  The flag is set immediately before the final `praxis:ready` post (line 391), i.e.
  only after all stages pass; a stage failure leaves it unset, so a retry re-runs the
  stages. `_verify()` runs later, in `_run_setup`, so a `_verify` failure after full
  success leaves the flag set; the recovery is a kernel restart (failure mode 6).
  `builtins` is used rather than a module global because every caller exec's a fresh
  copy of this file. This is what makes an old saved notebook's legacy bootstrap cell
  harmless under auto-setup (AC-6). `setup(force=True)` clears the flag before its run.
- In the `except` (line 393), after posting `praxis:error`: `if raise_on_error: raise`.

**Restart (AC-7).** A restart ends the worker (constraint 4). The new kernel runs
PYTHONSTARTUP again, and `praxis_boot` and `builtins` start clean. Nothing needs
handling beyond F1.

**Interaction with shells.** praxis-shell.js needs no change: the bootstrap's D1
`shell-ping` still gets its pong. Behaviour change, accepted: every kernel that
completes setup now installs the `praxis:execute` broadcast listener
(`praxis_bootstrap.py:379`), where before only kernels whose user ran setup did; the
only senders are the out-of-scope Angular playground. coxswain-shell.js uses its own
`praxis_coxswain` channel (coxswain-shell.js:12-13) and is unaffected. T9 (optional)
adds a banner.

### 6.3 Fallbacks

- **B1** (PYTHONSTARTUP not honoured, env honoured): identical, except the startup
  file moves to `web-repl/files/praxis_ipython/profile_default/startup/00-praxis.py`
  with env `IPYTHONDIR=/drive/praxis_ipython`. T5's build assertion checks that path
  is staged and indexed instead.
- **F** (startup works, gate does not): the startup file still auto-runs setup. With
  no gate, correctness moves elsewhere: (1) T9's shell banner becomes required. It
  shows "Setting up PyLabRobot…", then ready, or a red error with the reason, fed by
  a new `praxis:autosetup` message `{type, state, reason, kernel_nonce}` that
  `praxis_boot` posts. (2) `praxis_boot` puts a lazy import hook (`sys.meta_path` finder) on
  `pylabrobot`. If setup is running, the hook raises
  `PraxisAutoSetupError("setup still running, re-run this cell in a few seconds")`;
  if it failed, it raises the recorded failure. This is fail-closed only for code
  that imports pylabrobot. It is not truly zero-action when a user runs a cell too
  early. AC-2 is downgraded to "a first cell run too early gets a visible, actionable
  error". *(Not taken: S0 passed, section 5.1; OQ-1 is moot.)*
- **G** (no env channel at all): stop. Keep the manual two lines, add T9's banner as a
  reminder, and reopen the design with the human: either a labextension (constraint 5
  proof = S0 evidence) or an upstream request for a startup hook in pyodide-kernel.

### 6.4 Idempotency matrix

| Sequence | Result |
|---|---|
| auto running → user cell `await praxis_boot.setup()` | Gate waits for the auto task. `setup()` sees `ready`, prints `already bootstrapped` |
| auto ready → legacy cell `exec(loader); await praxis_main(root)` | Once-guard: no stages re-run, `praxis:ready` re-posted |
| auto failed → `await praxis_boot.setup()` | Gate lets it through. `_lock` means one run. On success, `ready` |
| auto failed → legacy `praxis_main(root)` cell | Blocked by the gate (source lacks `praxis_boot`). Message points to `praxis_boot.setup()` |
| `setup(force=True)` in a ready kernel | Deliberate re-run, as today. Risk R4 |
| `%run praxis_startup.py` again | `_autostart` sees `_task`, does nothing |

### 6.5 Documentation changes

- **welcome.ipynb.** Delete cell 3 (the fetch-and-exec bootstrap). Cell 1's last
  bullet becomes: "The Python environment does not persist, but you don't have to do
  anything: every kernel sets PyLabRobot up by itself when it starts, including after
  a reload or restart." Cell 2 becomes "1. Setup is automatic": what happens, that
  the first cell may take a few seconds, what a `PraxisAutoSetupError` means, and the
  three ways to recover. Cell 4 becomes "Checking or retrying setup":
  `praxis_boot.status()`, `await praxis_boot.setup()` (mentioned in markdown only). Add
  a short code cell `import praxis_boot; praxis_boot.status()` before cell 6; its output
  line is exactly `praxis auto-setup state: ready` in a healthy kernel (section 6.2
  `status()`). Cell 6 stays as it is.
- **praxis_boot.py module docstring.** Lead with "You normally never import this: every
  kernel runs it automatically at start (via `praxis_startup.py`)". Then document
  `status()`, `setup()` (retry, idempotent), `dismiss()`, and the gate. Replace
  "Every kernel session needs it once" with an explanation of the automatic path. The
  `setup()` docstring says "safe to call any time; returns immediately if this kernel
  is already set up".
- **repl.yml comments** at lines 115-119 and 151-156 are updated to match the new
  premises.

## 7. Failure modes

| # | Failure | What the user sees | How it is covered |
|---|---|---|---|
| 1 | `bootstrap/praxis_bootstrap.py` returns 404 (wrong root) | First cell: `PraxisAutoSetupError` caused by `RuntimeError: fetching the loader … HTTP 404` | Existing `_run_setup` check. Gate: `--autosetup-fault-check --fault 404:bootstrap/praxis_bootstrap.py` |
| 2 | `stages.py`/`transport.py` returns 404 | Error caused by `RuntimeError: failed to fetch loader module` (re-raised by `raise_on_error`) | Same gate, `404:bootstrap/stages.py` |
| 3 | Loader sha mismatch | Error caused by `loader module sha256 mismatch` | Same gate, `tamper:bootstrap/stages.py` (served bytes changed). Unit tests unchanged |
| 4 | manifest 404, D1 sha mismatch, source drift, wheel drift | Typed `PraxisBootError` subclass as the cause | Existing loader unit tests, plus a new `raise_on_error` unit test |
| 5 | `micropip.install` fails | Cause is the micropip exception | `raise_on_error` path. Gate `404:assets/wheels/<pylabrobot wheel>` |
| 6 | `praxis_main` returns but `_verify()` fails | Cause is `RuntimeError: … Serial class is NOT the browser shim`; the message says `setup()` cannot fix it and to **restart the kernel** (the once-guard flag is already set, so a retry skips the stages). Recovery: kernel restart | CPython unit test with `praxis_main` stubbed to a no-op; unit test that the error text names restart |
| 7 | Kernel restarted mid-setup | Worker is killed; the new kernel starts over | AC-7 gate restarts after setup completes. Restarting mid-setup is covered by the worker teardown (F2) and not gated separately (R7) |
| 8 | User calls `setup()` while auto is running | Waits, then `already bootstrapped` | `_lock` + shield. Unit test T3 |
| 9 | First cell is `%pip install …` | Waits (cleanup_transforms runs before pip_magic) | Unit test orders transforms. Browser gate cell 1 variant |
| 10 | pyodide-kernel bump drops PYTHONSTARTUP handling, renames `lite_transform_manager`/`cleanup_transforms`, or stops awaiting transforms | Before T5: silently back to a bare kernel | **Transform internals detected at build time** by T5's `assert_kernel_autosetup_contract`. It reads the vendored wheel at `dist/extensions/@jupyterlite/pyodide-kernel-extension/static/pypi/pyodide_kernel-*.whl` (observed: `pyodide_kernel-0.8.2-py3-none-any.whl`), asserts exactly one match with version `0.8.2`, and asserts the wheel sources still contain the literal `code = await self.lite_transform_manager.transform_cell(code)` (`kernel.py:104`), the literal loop header `for transform in self.cleanup_transforms + self.line_transforms:` (`litetransform.py:31`; catches a rename of `cleanup_transforms` or a reorder that would put `pip_magic` ahead of the gate) and the literal awaited loop body `lines = await transform(lines)` (`litetransform.py:32`; lines 104 and 32 appear in the S0 E4 traceback). **Dropped PYTHONSTARTUP handling or env passthrough is runtime-only**: it lives in IPython (`shellapp.py:422`) and the worker JS, not in this wheel, so it is detected only by `--fresh-boot-check` in CI (AC-1 fails with `ModuleNotFoundError`, `praxis_boot.state` is not `ready`). **Detected by users**: only with T9 banner |
| 11 | `import praxis_boot` fails in the startup file (user shadowed/edited `praxis_boot.py` in IndexedDB, or deleted it) | Every cell raises `RuntimeError("PraxisAutoSetupError: praxis auto-setup could not start: …")` naming the import error or the protocol mismatch (or a static fallback if the exception cannot be formatted), and how to recover | `praxis_startup.py`'s `except BaseException` branch (6.2) installs an inline catch-and-rewrite gate into `get_ipython().kernel.lite_transform_manager.cleanup_transforms`, with no `praxis_boot` import. It covers both `import praxis_boot` failing and `AUTOSETUP_PROTOCOL != 1`. Unit test in `test_praxis_startup.py`. A deleted/edited `praxis_startup.py` itself stays uncovered; R3 |
| 12 | A shell tab from an older deploy on the same origin answers D1 first (also: two kernels booting at once) | `shell_ping` resolves on the FIRST pong regardless of sha (`transport.py:283-289`), so a stale tab's pong fails D1. The first cell gets `PraxisAutoSetupError` whose text says to close other Praxis tabs from an older deploy and restart the kernel | Pre-existing, but now reached on every kernel start. `transport.py` is sha-pinned and NOT changed (AC-8). Follow-up debt in section 11. R5 |
| 13 | Offline | Same as today; all assets local | `--probe --offline` still in repl.yml |
| 14 | User wants plain Python after a failure | Cells blocked | `praxis_boot.dismiss()`. OQ-2 |
| 15 | Old saved notebook still has the legacy bootstrap cell | Runs as a no-op via the once-guard, prints `bootstrap complete` | Unit test T2 |
| 16 | An exception escapes a gate (`_gate_cell` or the inline startup gate) out of `transform_cell` | Internal traceback, JS pageerrors (`Cannot set properties of undefined (setting 'execution_count')`), kernel stuck `busy` (S0 E4 uncaught variant) | Prevented by the normative rule in 6.2: every gate catches everything and returns a rewrite. Unit tests: internal gate error returns a raise line and never raises (both gates) |
| 17 | Setup task cancelled, or the first cell's wait interrupted (`KeyboardInterrupt`/`CancelledError`), or an exception whose `__repr__`/`__str__` raises reaches a message build | Cancelled task: the cell gets `PraxisAutoSetupError` ("task ended without a result"), state `failed`. Interrupted wait: the cell raises `PraxisAutoSetupError('praxis auto-setup was interrupted …')`; the next cell waits again, at most once. Unformattable exception: the static fallback message, still containing `PraxisAutoSetupError` | Gate liveness rules and `_safe_repr` (6.2, R2-4/R2-5). Unit tests in `test_praxis_boot_autosetup.py` and `test_praxis_startup.py` (section 8.1) |

## 8. Test and gate plan

### 8.1 CPython unit tests (one pytest process per file; each new file's repl.yml line is added in the task that creates it)

| File | New/changed | Covers |
|---|---|---|
| `web-repl/tests/test_praxis_bootstrap_loader.py` | Changed: add `test_raise_on_error_reraises_after_posting_error`, `test_positional_call_still_swallows`, `test_once_guard_skips_stages_and_reposts_ready`, `test_force_clears_guard` (the last one is in the praxis_boot test) | AC-6, failure modes 2-4 and 15 |
| `web-repl/tests/test_praxis_boot_autosetup.py` | **New.** Fakes a `js` module (XHR returning a loader stub) and a fake shell exposing `.kernel.lite_transform_manager` built from a copy of `LiteTransformerManager` semantics (a plain object with `cleanup_transforms`/`line_transforms` lists). Tests: `_autostart` idempotent; gate waits while running; gate re-dispatches after the wait: running → failed returns the raise-rewrite lines, running → ready returns the original lines; `gate_waited` is set only when the gate entered with `running`; `_verify`-failure error text names kernel restart; D1-mismatch error text says to close other Praxis tabs from an older deploy and restart; ready passes lines through byte-identical; failed replaces lines with a single raise line and executing it raises `PraxisAutoSetupError` whose `__cause__` is the recorded failure; failed + `praxis_boot` in source passes through; `_verify` failure → failed; concurrent `setup()` during auto runs `praxis_main` exactly once (call counter); `setup()` in ready prints `already bootstrapped`; internal gate error returns a raise line and never raises; `dismiss` only from failed; gate is `cleanup_transforms[0]`, ahead of `pip_magic`. Liveness (R2-4): a cancelled task leaves state `running` → the gate sets `failed` with a cause and returns the raise-rewrite line; the gate awaits `_task` at most once per cell (await counter == 1 even when state is still `running` afterwards); `KeyboardInterrupt` and `CancelledError` raised into the wait each return the static 'setup was interrupted' raise line, do not raise, and do not loop; a following cell with the task still pending waits once more. Robustness (R2-5), each with an exception class whose `__repr__` and `__str__` raise: (i) as `failure`, `_gate_error()` returns a `PraxisAutoSetupError` with the static fallback message; (ii) as a forced internal gate error, step 4 returns a single raise line containing `PraxisAutoSetupError` and never raises; (iii) `status()` still prints its line and returns. `status()` prints exactly `praxis auto-setup state: ready` in a ready kernel (captured stdout). Playground names (T3b): with a fake `IPython.get_ipython()` whose `user_ns` is a dict and a fake `web_bridge` module, a successful `_run_setup` calls `bootstrap_playground` exactly once with that exact `user_ns` object (identity) before `state` becomes `ready`; with `get_ipython()` returning None it is skipped and setup still reaches `ready`; if `bootstrap_playground` raises, setup still reaches `ready` and nothing propagates; a failed setup (praxis_main or `_verify` raising) never calls it | AC-1 (playground names), AC-2..6 logic, failure modes 6, 8, 9, 17 |
| `web-repl/tests/test_praxis_startup.py` | **New.** Runs `praxis_startup.py` with a stub `praxis_boot` in `sys.modules`: calls `_autostart(origin="PYTHONSTARTUP")` once and leaves no names in its exec namespace (success and failure paths). With a fake `get_ipython()` exposing `.kernel.lite_transform_manager.cleanup_transforms`: (a) `praxis_boot` import raising → inline gate inserted at index 0, and awaiting it returns a single raise line whose message names the import error; (b) `AUTOSETUP_PROTOCOL` differing → same, message names the protocol mismatch; (c) the inline gate never raises; (d) with no `get_ipython`/manager, the file itself still does not raise; (e) (R2-5) `praxis_boot` import raising an exception whose `__repr__` and `__str__` raise → the inline gate is still inserted at index 0, and its single raise line contains `PraxisAutoSetupError`; in (a) and (b) the raise line also contains `PraxisAutoSetupError` | Failure modes 11, 16, 17 |
| `web-repl/tests/test_autosetup_build_assertions.py` | **New.** `assert_autosetup_env` (missing key / wrong path / key misfiled at top level → `BuildAssertionError`), `assert_praxis_startup_shipped` (staged-but-unindexed, indexed-but-missing), `assert_kernel_autosetup_contract` against synthetic wheels placed at `extensions/@jupyterlite/pyodide-kernel-extension/static/pypi/` (a good one passes; no wheel, two wheels, wrong version, a `litetransform.py` with `lines = transform(lines)` lacking `await`, a `litetransform.py` whose loop is `for transform in self.line_transforms + self.cleanup_transforms:` (reordered) or iterates a renamed list, or a missing `transform_cell` await each fail) | AC-9, failure mode 10 |
| `web-repl/tests/test_base_path.py` | Changed: replace needle tests with `assert_no_hardcoded_bootstrap_in_notebooks`. Any `files/**/*.ipynb` whose **code cells** contain any of the shared forbidden list `praxis_main(`, `praxis_boot.setup(`, `HOST_ROOT =` fails the build; markdown cells are not scanned (they may mention `praxis_boot.setup()`). Synthetic tests include a notebook with `await praxis_boot.setup()` in markdown only (passes), in a code cell (fails), and `await lh.setup()` in a code cell (passes). `test_real_source_notebook_carries_the_needle` becomes `test_real_source_notebooks_carry_no_bootstrap`, the only test in the file that reads the real `web-repl/files/` tree; it passes only after T6 (see T5/T6 ordering, section 9) | AC-10, and removes the vacuous-green trap |

Local verification is always a single file, e.g. `uv run python -m pytest web-repl/tests/test_praxis_boot_autosetup.py -q`.

### 8.2 Build assertions (build_repl.py, run in the "Build the site" step)
- `assert_autosetup_env(out_dir)`: the runtime `dist/jupyter-lite.json` has
  `litePluginSettings[kernel].loadPyodideOptions.env.PYTHONSTARTUP == "/drive/praxis_startup.py"`,
  and `disablePyPIFallback` and `pyodideUrl` are still present. This also catches the
  doit-regeneration class of bug described at build_repl.py:227-247.
- `assert_praxis_startup_shipped(out_dir)`: same shape as `assert_praxis_boot_shipped`.
- `assert_kernel_autosetup_contract(out_dir)`: failure mode 10. Reads
  `out_dir/extensions/@jupyterlite/pyodide-kernel-extension/static/pypi/pyodide_kernel-*.whl`
  and asserts the literals `for transform in self.cleanup_transforms + self.line_transforms:`,
  `lines = await transform(lines)` and
  `code = await self.lite_transform_manager.transform_cell(code)`. It does not claim to
  detect dropped PYTHONSTARTUP/env passthrough (runtime-only, `--fresh-boot-check`).
- `assert_no_hardcoded_bootstrap_in_notebooks(out_dir)`: replaces `apply_base_path`'s
  rewrite and its "changed == 0 raises" rule (build_repl.py:634-679). `--base-path`
  is still accepted: `repl_smoke` and the served prefix still use it, and
  `derive_host_root` handles the root.

### 8.3 Browser gates (scripts/repl_smoke.py, steps in repl.yml)

| Mode | Change | Exact assertions |
|---|---|---|
| `--fresh-boot-check` | **Premise replaced.** `build_fresh_boot_probe_code` no longer imports or calls `praxis_boot.setup`. Its first statement reads `praxis_boot` state, then imports pylabrobot | `state == "ready"`; `autostart_origin == "PYTHONSTARTUP"`; `plr_version` startswith `0.2.2+g`; `serial_is_shim is True`; `derived_host_root == expected_root` (read from `praxis_boot.host_root`); `playground_names_ok is True`, where the probe cell evaluates `LiquidHandler.__name__ == "LiquidHandler" and "STAR" in globals()` with NO import of either name in the probe source (the harness asserts the probe source contains no `import LiquidHandler`/`from pylabrobot.liquid_handling` line before sending; T3b); `setup_called_by_probe is False` (a static check that the probe source contains none of the shared forbidden list `praxis_main(`, `praxis_boot.setup(`, `HOST_ROOT =`, asserted by the harness before sending); **`gate_waited is True`** (REQUIRED). The probe cell is dispatched at the first `idle`. **Deterministic wait (R2-1):** `--fresh-boot-check` ALWAYS runs with the harness fault `delay:assets/wheels/<pylabrobot wheel filename>:15`, where the filename is read from the served `assets/wheels/manifest.json` entry with `package == "pylabrobot"` (currently `pylabrobot-0.2.2+gdd79c4c8-py3-none-any.whl`), so the delayed request path is `<base-path>assets/wheels/pylabrobot-0.2.2+gdd79c4c8-py3-none-any.whl`. That fetch is made by `await micropip.install(wheel_url, deps=False)` in bootstrap stage 7 (`praxis_bootstrap.py:358-360`), an awaited coroutine: micropip 0.11.1 fetches URLs through Pyodide's async JS `fetch`, so the worker's event loop stays free while the server sleeps. The delay is NEVER put on a sync-XHR file (`bootstrap/praxis_bootstrap.py`, `bootstrap/stages.py`, `bootstrap/transport.py`, `assets/wheels/manifest.json`, the `assets/python`/`assets/shims` sources: `praxis_boot.py` and `praxis_bootstrap.py:102-103`, `transport.py:101` use `xhr.open("GET", url, False)`), because a sync XHR blocks the worker thread and would delay kernel-ready itself, so the cell would find setup already done. **Why 15 s:** S0 E2 measured kernel boot ~9.8 s, with setup starting ~3.9 s before the first cell could run; the wheel fetch comes after D1 and D2, so it begins at most ~6 s into boot. Holding it 15 s keeps setup `running` for at least ~9 s past first idle (and still covers a CI runner twice as slow), while staying well inside the cell timeout, which is raised by the delay (record the measured gate wait and adjust the timeout, never the assertion). Assertions: the delay fault's hit counter is > 0 (trap 5); `gate_waited is True`; the measured gate wait (harness wall time from sending the probe's execute request to its execute_reply) is recorded in the result JSON. Because `gate_waited` is set only when the gate entered with `state == "running"` for that cell, `True` proves setup completed after the cell's execute request reached the gate, so the assertion cannot pass vacuously. The old `plr_before == ModuleNotFoundError` premise moves to the negative control below |
| `--autosetup-fault-check` (**new**) | `ServedDir` gains `faults: dict[path_suffix, Fault]` with three kinds: `404`, `tamper`, and `delay:<path-suffix>:<seconds>` (sleep `<seconds>` in the handler thread, then serve the file normally; parse the seconds with `rsplit(":", 1)`). Faults are matched on the parsed URL path, `urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).endswith(suffix)` (C-17; `unquote`, not `unquote_plus`, so the wheel's literal `+` survives), applied in `Handler.do_GET` for the first N matching requests (`--fault-count`, default 1), and each fault keeps a hit counter. The server is `ThreadingHTTPServer` (`repl_smoke.py:274`), so a delay holds only that one request. Run once each for `404:bootstrap/stages.py` and `tamper:bootstrap/stages.py`. The page is served by the harness, so worker requests are intercepted (unlike `page.route`, repl.yml:137-140). **Notebook:** a harness-created blank notebook, not welcome.ipynb. The harness loads `<base-path>lab/index.html` (no `?path=`), waits for `window.jupyterapp`, creates the notebook with `window.jupyterapp.serviceManager.contents.newUntitled({type: "notebook", path: ""})`, opens the returned path with `window.jupyterapp.commands.execute("docmanager:open", {path, factory: "Notebook", kernel: {name: "python"}})`, then accepts a Select Kernel dialog if one appears (same handling as `repl_smoke.py:1286-1298`) and inserts the cells below into the model | Cell 1 = `_S = 'side' + 'effect'; import builtins; builtins.__praxis_cell_ran = True; print(_S)`: its output contains `PraxisAutoSetupError` and the fault's reason (`HTTP 404` / `sha256 mismatch`); the side-effect string is absent from outputs; execute status `error` (read from the notebook model, not the DOM, per repl_smoke.py:1342-1353). Cell 2 = the same, must also be blocked (every cell, not only the first). Cell 3 = `import praxis_boot; await praxis_boot.setup()` (fault count spent, so the retry succeeds): no error, prints `ready`. Cell 4 = AC-1 probe → `True`. `gate_waited` is RECORDED only, not asserted (a 404/sha fault fails within milliseconds). **This doubles as the negative control:** if auto-setup never ran, cell 1 would print the side effect and the gate fails |
| `--restart-check` (**new**) | After AC-1 passes, restart via the kernel API (`session.kernel.restart()`, no command dispatch and so no dialog, F7). Then run the AC-1 probe as a cell (lab notebook, same as notebook-check) | `kernel_nonce` after ≠ before; `state == "ready"`; `serial_is_shim is True` |
| `--race-check` (folded into `--fresh-boot-check`) | Cell sent as soon as `kernel.status == "idle"` is first seen | AC-1 passes; `gate_waited is True` (see `--fresh-boot-check`) |
| `--notebook-check` | `NOTEBOOK_EXPECTED` becomes (`"praxis auto-setup state: ready"`, `"PyLabRobot 0.2.2+g"`, `"Serial is the browser shim: True"`), and `"bootstrap complete"` is removed. The first literal is exactly the line `praxis_boot.status()` prints (section 6.2) from the welcome.ipynb status cell (section 6.5). Before running, the harness asserts the staged welcome.ipynb **code cells** contain none of the shared forbidden list `praxis_main(`, `praxis_boot.setup(`, `HOST_ROOT =` (markdown not scanned) | AC-10, AC-1 in the lab app |
| `--probe`, `--probe --offline`, `--completion-check` | Replace step 1 (fetch+exec+`praxis_main`, repl_smoke.py:318-330 and 629-640) with `import praxis_boot; await praxis_boot.setup()` and record `praxis_boot.state`. The gate plus once-guard make this a no-op check, not a second run. Check whether later probe steps rely on names the old `exec(..., globals())` put into the user namespace (e.g. `_praxis_channel`, `bootstrap_playground(globals())` injections); if so, import them from `builtins`/`web_bridge` explicitly | AC-6, AC-11 |
| `--typeahead-check` | Unchanged; its ready cell now waits for setup. The timeout may need to go up; record the measured delta | AC-11, R6 |

### 8.4 Test-design traps to avoid
1. **The notebook or probe still calls setup.** A gate passes because the harness or
   welcome.ipynb ran `setup()`/`praxis_main` itself. Guard: static source checks before
   sending (8.3), plus the AC-10 unit test.
2. **Reading source instead of output.** Cell source is in the DOM; the side-effect and
   error strings must be split literals and read from model outputs (repl_smoke.py:1342-1353).
3. **A "ready" signal that proves nothing.** `praxis:ready` or `state == "ready"` alone is
   not AC-1. Always pair it with the `_verify` identity check executed in the user's cell.
4. **Restart that isn't a restart.** Without the nonce comparison, a no-op restart passes.
5. **Faults that don't reach the worker.** Use harness-side `ServedDir` faults, not
   `page.route`. Self-test: fault-check asserts the handler actually served a faulted response (counter > 0), and fresh-boot-check asserts the same for its wheel delay fault.
8. **A delay that blocks the worker.** A delay on a sync-XHR asset stalls kernel-ready, so
   the cell never sees `running` (or it passes for the wrong reason). Delays go only on the
   async micropip wheel fetch (8.3).
6. **Unit fakes that drift from the pinned kernel.** The fake manager's ordering
   assumption (cleanup before line transforms) is backed by the build contract in T5,
   which reads the real wheel.
7. **Mocking away the error path.** Tests that stub `_verify` to always pass hide AC-4.
   Include a test where `praxis_main` succeeds and `_verify` fails.

### 8.5 AC → proof
AC-1 fresh-boot-check, notebook-check · AC-2 fresh-boot-check with the always-on `delay:assets/wheels/<pylabrobot wheel>:15` fault (delay hit counter > 0, `gate_waited is True`, measured gate wait recorded) + unit (running → ready/failed re-dispatch, single wait per cell, cancelled/interrupted wait) · AC-3 fault-check cells 1-2 on a harness-created blank notebook + unit (bad-repr exceptions still yield `PraxisAutoSetupError` text in gate step 4, `_gate_error` and the startup inline gate) · AC-4 unit (_verify fails), fault-check · AC-5 fault-check cell 3, unit · AC-6 unit (once-guard, lock counter), probe modes · AC-7 restart-check · AC-8 unchanged sha unit tests, fault-check tamper run, `git diff` shows stages.py/transport.py untouched · AC-9 build assertions + their unit test · AC-10 test_base_path + notebook-check static check · AC-11 full repl.yml run on the PR.

## 9. Fixer tasks

S0 passed; the primary design proceeds. Browser gates run in CI on the PR; local runs
are single files only.

**Delivery (C-1).** T2-T8 ship as ONE PR. Its CI gate is judged on the PR's final
commit only; intermediate commits are not required to be green (e.g. T5's build
assertions fail until T7 flips the env). Each task that creates a
`web-repl/tests/test_*.py` file adds that file's repl.yml Tests line in the same task.
The `web-repl/jupyter-lite.json` env flip lands in T7, together with (never before) the
`repl_smoke.py` premise change.

### T1: Record the S0 outcome — DONE (section 5.1, revision 260914)
**Files**: this spec (modify) · **Gate**: every S0-1..S0-7 row has an observed value
and the decision is stated · **Deps**: spike

### T2: `praxis_main` raise_on_error + once-guard
Section 6.2. Additive only; the marker line stays unchanged.
**Files**: `web-repl/bootstrap/praxis_bootstrap.py`, `web-repl/tests/test_praxis_bootstrap_loader.py` (modify)
**Gate**: `uv run python -m pytest web-repl/tests/test_praxis_bootstrap_loader.py -q` and `uv run python -m pytest web-repl/tests/test_stamp_loader_shas.py -q`
**Deps**: T1 · **~60 LOC**

### T3: praxis_boot state machine, gate, setup refactor
Section 6.2 in full (`_autostart`, `_run_setup`, `_gate_cell`, `_gate_error`,
`PraxisAutoSetupError`, `status`, `dismiss`, `_safe_repr`, the gate liveness rules, lock,
nonce, protocol constant).
**Files**: `web-repl/files/praxis_boot.py` (modify), `web-repl/tests/test_praxis_boot_autosetup.py` (create), `.github/workflows/repl.yml` (add that file's Tests line)
**Gate**: `uv run python -m pytest web-repl/tests/test_praxis_boot_autosetup.py -q`
**Deps**: T2 · **~250 LOC incl. tests**

### T4: Startup shim (incl. inline fallback gate)
The `jupyter-lite.json` env flip is NOT part of T4; it lands in T7 (C-1).
**Files**: `web-repl/files/praxis_startup.py` (create), `web-repl/tests/test_praxis_startup.py` (create), `.github/workflows/repl.yml` (add that file's Tests line)
**Gate**: `uv run python -m pytest web-repl/tests/test_praxis_startup.py -q`
**Deps**: T3 · **~110 LOC**

### T5: Build assertions + retire the HOST_ROOT rewrite
Add `assert_autosetup_env`, `assert_praxis_startup_shipped`, `assert_kernel_autosetup_contract`
and `assert_no_hardcoded_bootstrap_in_notebooks`, wired next to `assert_praxis_boot_shipped`
(build_repl.py:1275). Remove the `apply_base_path` rewrite and its zero-change failure.
The kernel contract reads `dist/extensions/@jupyterlite/pyodide-kernel-extension/static/pypi/pyodide_kernel-*.whl`
and asserts the literals `for transform in self.cleanup_transforms + self.line_transforms:`
(`litetransform.py:31`), `lines = await transform(lines)` and the `transform_cell` await (section 8.2).
The shared forbidden list is `praxis_main(`, `praxis_boot.setup(`, `HOST_ROOT =` (AC-10).
**Order (R2-3): T5 lands before T6.** T5 writes `test_real_source_notebooks_carry_no_bootstrap`,
but welcome.ipynb still carries its bootstrap cell until T6, so that one test is excluded
from T5's gate and enabled by T6's gate.
**Files**: `web-repl/scripts/build_repl.py`, `web-repl/tests/test_base_path.py` (modify), `web-repl/tests/test_autosetup_build_assertions.py` (create), `.github/workflows/repl.yml` (add the new file's Tests line)
**Gate** (synthetic cases only): `uv run python -m pytest web-repl/tests/test_autosetup_build_assertions.py -q`, then separately `uv run python -m pytest web-repl/tests/test_base_path.py -q -k "not test_real_source_notebooks_carry_no_bootstrap"`. The full build `uv run python web-repl/scripts/build_repl.py --base-path /praxis/ > /tmp/build.log 2>&1; grep -E "ASSERTION|autosetup|startup" /tmp/build.log` runs in CI on the PR's final commit only (it needs the vendored Pyodide, and fails until T6 and T7 land, C-1)
**Deps**: T4; same PR as T6 · **~200 LOC**

### T6: welcome.ipynb + docstrings
Section 6.5 (including the `praxis_boot.status()` code cell whose output is `praxis auto-setup state: ready`).
Runs after T5, whose rewritten `test_base_path.py` must already exist.
**Files**: `web-repl/files/welcome.ipynb`, `web-repl/files/praxis_boot.py` (docstrings only)
**Gate**: `uv run python -m pytest web-repl/tests/test_base_path.py -q` (the whole file, now including `test_real_source_notebooks_carry_no_bootstrap`: no code cell under `web-repl/files/` contains `praxis_main(`, `praxis_boot.setup(` or `HOST_ROOT =`), plus `uv run python -m pytest web-repl/tests/test_base_path.py -q -k test_real_source_notebooks_carry_no_bootstrap` to show that test ran (1 passed, not deselected)
**Deps**: T3, T5 · **~80 lines**

### T7: repl_smoke premises + new modes
Rewrite `build_fresh_boot_probe_code` and its assertions (repl_smoke.py:988-1060, 2083-2165).
Add `ServedDir` faults with three kinds, `404`, `tamper` and `delay:<path-suffix>:<seconds>`,
matched on the parsed, unquoted URL path (C-17) and each with a hit counter. Make
`--fresh-boot-check` always apply `delay:assets/wheels/<pylabrobot wheel from manifest.json>:15`,
assert its hit counter > 0 and `gate_waited is True`, and record the measured gate wait.
Never delay a sync-XHR asset (section 8.3). Add `--autosetup-fault-check` (on a
harness-created blank notebook), `--restart-check`, the notebook-check expected-string
(`praxis auto-setup state: ready`) and static-source changes (forbidden list
`praxis_main(`, `praxis_boot.setup(`, `HOST_ROOT =`), and the probe/completion step-1 swap
(section 8.3). In the same task (C-1), flip the env: add `loadPyodideOptions.env.PYTHONSTARTUP`
to `web-repl/jupyter-lite.json` (section 6.1).
**Files**: `scripts/repl_smoke.py`, `web-repl/jupyter-lite.json` (modify)
**Gate**: `uv run python scripts/repl_smoke.py --help | grep -E "autosetup-fault-check|restart-check|fault"`; `uv run python -c "import json;d=json.load(open('web-repl/jupyter-lite.json'));print(d['jupyter-config-data']['litePluginSettings']['@jupyterlite/pyodide-kernel-extension:kernel']['loadPyodideOptions'])"` shows the env; the browser run happens in CI (T8)
**Deps**: T3-T6 · **~350 LOC**

### T8: repl.yml wiring
Add steps: `--autosetup-fault-check --fault 404:bootstrap/stages.py`, the same with
`tamper:bootstrap/stages.py`, and `--restart-check`, all with `--base-path /praxis/`.
The new unit-test files' Tests lines were already added by T3, T4 and T5; T8 only
verifies all three are present. Update the comments at lines 115-119 and 151-156.
**Files**: `.github/workflows/repl.yml`
**Gate**: the REPL workflow is green on the PR's final commit (`gh pr checks <n>`). The
human merges (CLAUDE.md: agents do not merge)
**Deps**: T7 · **~40 lines**

### T9 (optional, required under fallback F): shell status banner
`praxis_boot` posts `{type: "praxis:autosetup", state, reason, kernel_nonce}` on
`praxis_repl` at each state change. praxis-shell.js renders a dismissible banner that
tracks the latest message per `kernel_nonce`.
**Files**: `web-repl/files/praxis_boot.py`, `web-repl/shell/praxis-shell.js`, `scripts/repl_smoke.py` (banner assertion in fault-check)
**Gate**: fault-check asserts a banner element with the reason text · **Deps**: T8 · **~120 LOC**

## 10. Risks

| # | Risk | Mitigation / rollback |
|---|---|---|
| R1 | F3/F6 rely on pyodide-kernel internals and break on a version bump | T5 contract fails the build for transform-internal changes (a missing await, or a renamed or reordered `cleanup_transforms` in the `litetransform.py:31` loop header); dropped PYTHONSTARTUP/env passthrough is caught only at runtime by `--fresh-boot-check`. Pins in pyproject.toml:33-34. Rollback: remove `loadPyodideOptions` from jupyter-lite.json and the kernel returns to manual setup, since `setup()` still works standalone |
| R2 | Replacing a cell's code in the gate surprises users (their cell "didn't run") | The message says so explicitly and gives three recovery paths. OQ-2 |
| R3 | A user's IndexedDB copy of `praxis_boot.py` (edited/renamed) shadows the shipped one, so auto-setup silently doesn't happen | A shadowed/broken `praxis_boot.py` (import failure or protocol mismatch) is made visible by the startup file's inline gate (failure mode 11). **Known limitation:** a user-deleted or user-edited `/drive/praxis_startup.py` (IndexedDB-shadowed) is NOT mitigated without T9 (banner); the kernel silently falls back to manual setup. Document "don't edit praxis_boot.py / praxis_startup.py" in their headers |
| R4 | `setup(force=True)` re-running stages in one kernel might break R-ID identity. **Unverified:** the `sys.modules` import cache used by `import_shim_class` (`stages.py:276-285`) suggests identity is preserved under force, but this is not proven; `test_praxis_bootstrap_loader.py:424-450` is a synthetic double exec, not a force re-run | Pre-existing behaviour. The once-guard stops accidental re-runs. Whether `force` should stay public is OQ-5 |
| R5 | Every kernel now boots the loader, so D1 runs on every kernel start. `shell_ping` resolves on the FIRST pong regardless of sha (`transport.py:283-289`), so a stale shell tab from an older deploy on the same origin can answer first and fail D1 | Pre-existing, now reached on every kernel start. `transport.py` is sha-pinned and not changed (AC-8). The gate's D1-mismatch text tells the user to close other Praxis tabs from an older deploy and restart the kernel. Follow-up debt in section 11. Extra cost is a few seconds per kernel (F9) |
| R6 | Setup work on the worker delays completions or typeahead during the setup window | `--typeahead-check` stays in CI. Record the timing and raise the timeout only with a measured number |
| R7 | Restart during setup leaves partial state | Worker termination discards all in-memory FS and module state. Not separately gated |
| R8 | Removing `apply_base_path` breaks a subpath deploy that relied on a notebook's HOST_ROOT | No shipped notebook keeps one after T6. `derive_host_root` is already the path for new notebooks (gated today). CI builds with `/praxis/` |
| R9 | Probe modes depended on names injected by `exec(loader, globals())` | T7 checks this explicitly; failing probes are caught in CI before merge |
| R10 | `web_bridge.bootstrap_playground(globals())` gets the private exec namespace under praxis_boot, not the user namespace | Already true for the manual path today. Confirm in T7 that no user-facing name disappears (compare `dir()` of a cell before and after) |

## 11. Open questions for the human

- **OQ-1. RESOLVED (moot).** S0 passed (section 5.1); the primary design proceeds and
  fallback F is not taken.
- **OQ-2.** After a failure, should every non-recovery cell stay blocked until
  `setup()` succeeds or `dismiss()` is called (the spec's default)? Or block only the
  first cell and then let a kernel without PyLabRobot run?
- **OQ-3.** Should the `praxis_main` once-guard re-post `praxis:ready` (keeps listeners
  like the Angular client happy), or post nothing?
- **OQ-4. RESOLVED.** T9's banner remains optional. The startup file's inline gate
  (C-6) makes import and protocol failures (failure mode 11) visible in-cell. Only a
  deleted/edited `praxis_startup.py` (R3) and dropped PYTHONSTARTUP/env passthrough
  (failure mode 10, caught by CI runtime) stay invisible to users without T9.
- **OQ-5.** Should `setup(force=True)` stay public given R4, or become
  `_force_rerun` for debugging only?
- **OQ-6.** `praxis_startup.py` shows up in the user's file browser next to
  `praxis_boot.py`. Is that acceptable, or should S0 also test a less visible
  location?

**Open items (not blocking):**
- Follow-up debt: in `shell_ping`, collect pongs over the window and accept any sha
  match, instead of resolving on the first pong (R5, failure mode 12). Out of scope
  here because `transport.py` is sha-pinned (AC-8).

## References
- Debt #1396 (user feedback 2026-08-24)
- `web-repl/files/praxis_boot.py`, `web-repl/bootstrap/praxis_bootstrap.py:289-398`, `web-repl/scripts/build_repl.py:346-388, 585-679`
- `scripts/repl_smoke.py:241-285, 296-330, 988-1060, 1209-1360, 2083-2165`
- `.github/workflows/repl.yml`
- pyodide_kernel 0.8.2: `__init__.py:26-33`, `interpreter.py:58-73`, `kernel.py:101-131`, `litetransform.py:19-35`
- IPython 9.12 `core/shellapp.py:346-443`, `paths.py:35`
- ADR `.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md`

