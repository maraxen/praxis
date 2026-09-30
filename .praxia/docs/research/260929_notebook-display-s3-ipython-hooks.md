---
title: 'Spike S3 (notebook display epic): IPython hooks in the Pyodide kernel'
description: Result of pre-registered spike S3, bathos run a3458bf2, outcome s3_combined (S3-A carrier holds; S3-C set_custom_exc yields no error output so the showtraceback wrapper is needed; S3-D post_run_cell does not fire for top-level-await cells). Run against the local 260828 dist.
status: final
task_id: 260929_notebook-display-design
date: '260929'
confidence: ''
sources: ''
---
# Spike S3 (notebook display epic): IPython hooks in the Pyodide kernel


# Spike S3: IPython hooks in the Pyodide kernel

**Outcome: `s3_combined`** (D1 branches **S3-A** carrier, **S3-C** exceptions, **S3-D** events; two
deviations, neither a STOP). Pre-registered bathos run `a3458bf2-9b0a-4925-866e-2422ef5585a3`, verified
by its record (`runs` table: status `completed`, outcome `s3_combined`, exit code 0, after
`bth compact`). Task A3 of the notebook display epic (backlog #5625); spec
`.praxia/docs/specs/260929_notebook-display-epic.md`, D1 S3, D2, D7, D8, D17.

## Provenance and pre-registration order
- Probe `scripts/spikes/260929_s3_ipython_hooks.py` and sidecar `.bth.toml` were committed on
  `feat/notebook-display-sprint-a` as `09217390` (17:57 on 260929) **before any run**; neither file
  changed afterwards. Bathos lock (committed as `95be08a8`): `sidecar_sha256 =
  5eb9f731a94224f246eb292b8b0e10ca953144dd56622696c5fac76752329b23`, `script_sha256 =
  548ac2bcf8aa4748872e83e855755f774377a7c21ecc5234910d1f3c1188a1b7`, `git_sha =
  d8923c736238f14969935da9600e3b980b15037b`; the orchestrator verified that the committed sidecar and
  script hash to exactly these values. This was the first and only execution. The sidecar recorded a
  non-criterion source-reading prior (S3-C plus S3-D); the run agreed with it, but the prior was not
  a criterion and was not applied.
- Run by the user, unsandboxed, full Chromium: `cd /tmp/praxis-nd-a && bth run --project-slug praxis
  --output-paths outputs/spikes/260929_s3 -- uv run --no-sync python3
  scripts/spikes/260929_s3_ipython_hooks.py --out-dir outputs/spikes/260929_s3 --dist
  /home/marielle/projects/praxis/web-repl/dist`. Browser: Google Chrome for Testing 153.0.8010.12.
- **DEVIATION: dist.** The served dist is the **local `web-repl/dist` built 260828** (PLR 0.2.2 build),
  not a fresh build off `origin/main` a176bac7 (PLR 1.0.0b1). S3 measures IPython 9.12.0 and
  `pyodide_kernel` in the kernel, which the PLR 1.0 bump did not change (Pyodide 314.0.1 and IPython
  9.12.0 were verified untouched by the recon), but this is a measurement of that dist.

## Unit: `ipython_hooks` RECOMPUTED (none reused); no error findings; no timeout
`all_units_complete = true`, `reused = []`, `timed_out = []`, `error_findings = {}`, `sub_errors = {}`,
`measurement_valid = true`, all 17 `validity_checks` true. Duration 28 s of a 600 s budget; kernel
idle after 14.2 s; warm-up 0.25 s. artifact sha256: `ac0757afc7588618d4279f79a694ec275acb51744abec8a30c0e078f32a421c7`.

Hashed inputs (prefixes; full values are in the stamp): `script` `548ac2bc`, `runner` `814fc870`,
`harness` `cc3c4ed0` (repl_smoke.py), `dist` `49e655b2`, `fixture` `699d9789` (the notebook built inside
the script), `chrome` `5275952f`, `driver` `99b2d23e`, `args` `7654f322`.

## Findings (AC-3 record)
Read from the notebook model (`notebook.content.model.cells`); kernel-side observations were returned
as raw `application/json` display bundles, never printed text. The kernel is
`pyodide_kernel.interpreter.Interpreter` on IPython 9.12.0 (Python 3.14.2).
- **(a)** `get_ipython()` is non-None; `display_formatter`, `events`, `set_custom_exc` and the
  mimebundle and `text/html` formatters are all present.
- **(b) `mimebundle_formatter.for_type(cls, fn)` with `(data, metadata)`: holds.** In a plain cell and in a
  top-level-`await` cell our HTML is in the output and the stamp is at top-level `metadata["praxis"]`.
  Negative control: an unstamped object reads no stamp.
- **(b') `formatters['text/html'].for_type(cls, fn)` returning `(html, {"praxis": stamp})`: holds.**
  Both modes; the stamp is at `metadata["text/html"]["praxis"]`. So the carrier branch is **S3-A**
  and the S3-B fallback is not needed; `stampOf` reads either location (D2) regardless.
- **(c) `set_custom_exc` handler: FAILS as a design carrier (S3-C).** The handler **is invoked** for
  an exception in a plain and in an `await` cell (`self` is the shell), and `display()` inside it **does
  emit**, but the returned structured traceback is **not** turned into the cell's `error` output
  (`error_output_present = false` in both modes), and **Run All does not stop** (`runall.custom`: all
  three cells ran, `stops = false`; the control block with a default error stops after two cells, so the
  premise holds).
- **(c') instance `showtraceback` wrapper (the S3-C fallback): HOLDS.** Wrapping the shell instance's
  `showtraceback` handled the registered classes and delegated everything else to `_showtraceback`
  (`delegated: _showtraceback`), produced an **error output** in both modes, and **Run All stopped**
  (`runall.wrap`: `ran = [true, true, false]`). Path evidence: the kernel derives run status from
  `Interpreter._last_traceback`, set in `Interpreter._showtraceback` (recorded in `path_evidence`).
  So B6 does **not** stop; it uses the wrapper.
- **(d) `events.register('post_run_cell', cb)`: FIRES for plain cells, does NOT fire for top-level-`await`
  cells (S3-D).** `pre_run_cell` fires for both modes; `post_run_cell` fired for the plain marker cell and
  not for the `await` cell (`fired_plain = true`, `fired_await = false`); unregistering stops it
  (`fired_after_unregister = false`).
- **D17 negative control:** an exception class not registered with the handler or the wrapper reached the
  **default traceback** (`negative_control_failed_as_required = true`).

## Consequences for the spec
- **D1 S3-C is in force:** B6 wraps the kernel shell **instance's** `showtraceback` (instance attribute;
  PLR and IPython classes untouched) for the four error classes, delegating everything else. Do not use
  `set_custom_exc` as the carrier: its handler's `display()` works but the cell gets no error output and
  Run All continues, which would violate the spec's "Run All stops on error" behaviour.
- **D1 S3-D is in force:** B7's kernel announcer must not rely on `post_run_cell`; announce from PLR
  state-update callbacks, debounced with `loop.call_later(0.1, ...)`, and settle the drawn-state digest
  inside that debounced announcer (the C11-7 fix), since `post_run_cell` also does not fire after an
  `await` cell.
- **D2:** either carrier location works; keep one reader, `stampOf`.
- No spec text needs to change for S3. Reproduce: `bth sql "SELECT id, status, outcome, exit_code FROM runs
  WHERE id LIKE 'a3458bf2%'"` after `bth compact` (the shared catalog lock is contended at times; retry);
  artifacts under `outputs/spikes/260929_s3/` in the sprint worktree (gitignored; hashes above).

