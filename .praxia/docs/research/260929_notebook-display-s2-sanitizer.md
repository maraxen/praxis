---
title: 'Spike S2 (notebook display epic): sanitizer survivorship and reopen trust'
description: 'Result of pre-registered spike S2, bathos run bf83a4e6, outcome s2_b_exec_t: a crafted (untrusted) notebook reopens as text/html with the SVG stripped (S2-B); a notebook executed, saved and reopened in the same browser reopens trusted with the full SVG intact (S2-T). Run against the local 260828 dist.'
status: final
task_id: 260929_notebook-display-design
date: '260929'
confidence: ''
sources: ''
---
# Spike S2 (notebook display epic): sanitizer survivorship and reopen trust


# Spike S2: sanitizer survivorship and reopen trust

**Outcome: `s2_b_exec_t`.** D1 branches: the **crafted** (never executed, untrusted) path is **S2-B**;
the **executed, saved and reopened in the same browser** path is **S2-T**. Pre-registered bathos run
`bf83a4e6-b026-4cd4-a75c-362d7b1c91d8`, verified by its record (`runs` table: status `completed`,
outcome `s2_b_exec_t`, exit code 0, after `bth compact`). Task A2 of the notebook display epic
(backlog #5624); spec `.praxia/docs/specs/260929_notebook-display-epic.md`, D1 S2, D2, D3, D17.

## Provenance and pre-registration order
- Probe `scripts/spikes/260929_s2_sanitizer.py` and sidecar `.bth.toml` were committed on
  `feat/notebook-display-sprint-a` as `84841ff0` (17:53 on 260929) **before any run**; neither file
  changed afterwards. Bathos lock (committed as `d8923c73`): `sidecar_sha256 =
  fd6b02b71ca111bc393039fdb9c4aadca0c6bb3b5bd5628612259cff4008b4de`, `script_sha256 =
  b3bd8be00a27df2692c9fd0a3bbc288a3f36fab115ea090619d2946cc6ade027`, `git_sha =
  0271c6f4da9e7db9a32fa15fd70114c17652f199`; the orchestrator verified that the committed sidecar and
  script hash to exactly these values. This was the first and only execution.
- Run by the user, unsandboxed, full Chromium: `cd /tmp/praxis-nd-a && bth run --project-slug praxis
  --output-paths outputs/spikes/260929_s2 -- uv run --no-sync python3 scripts/spikes/260929_s2_sanitizer.py
  --out-dir outputs/spikes/260929_s2 --dist /home/marielle/projects/praxis/web-repl/dist`
  (`UV_PROJECT_ENVIRONMENT` = the main checkout's `.venv`). Browser: Google Chrome for Testing
  153.0.8010.12 (`chromium-1243`, CI's bundled build).
- **DEVIATION: dist.** The served dist is the **local `web-repl/dist` built 260828** (PLR 0.2.2 build),
  not a fresh build off `origin/main` a176bac7 (PLR 1.0.0b1): commit `786ac2c4e` is in no local git
  object DB and `git clone` is blocked by the sandbox proxy. JupyterLite core/pins did not change after
  260828, and S2 measures the JupyterLab sanitizer and trust model, not PLR, but this is a
  measurement of that dist. A7's CI `--display-check` runs on a fresh build and is authoritative for the
  chrome; a re-check of S2 on the fresh dist is cheap (`--resume` does not reuse across a dist change).

## Units: every unit RECOMPUTED (none reused); no error findings; no timeouts
`all_units_complete = true`, `reused = []`, `timed_out = []`, `error_findings = {}`,
`measurement_valid = true`, all 16 `validity_checks` true (including `trust_corroborated_all`,
`live_positive_control_ok`, `negative_control_failed_as_required`, `reopen_paths_agree`).

| Unit | Recomputed / reused | Duration | artifact sha256 |
|---|---|---|---|
| `live` | recomputed | 20 s | `1b3a63b124a77b22287e5672e9c6f67b98f02fc7cea40f261f08ce26e7c3d9e8` |
| `crafted` | recomputed | 15 s | `5049e91cc35daf6e537f4c7bb7963dfad5ad9e1752b0fb44651613a4f08c23ff` |
| `executed_saved_reopened` | recomputed | 45 s | `bb67d12ed37a9049fe06c804863ef3c4a7203821a1a61bf2d58557822dca9c75` |
| `neg_script_onclick` | recomputed | 16 s | `51d18f699d63f0999e97d8c943ea3e1b2cffee0b3cff5efb47ce97d70eaf1500` |

Hashed inputs (from the `live` stamp; `args` differs per unit, the rest is shared):

- `args`: `38cb0d981a1005b1e5e0b7e4d157f1795f3975194d786af4bdc21973b0e739be`
- `chrome`: `5275952feb3c569d43faaf9551eb35c93a9b18f38c7408656e0a2d85a09d2596`
- `dist`: `49e655b28e4a65c2b25e165948c57eceedc0d6c928ccb6038197fe5820ae0138`
- `driver`: `99b2d23e49a0904adfffd19634312ea89414d770210867114969b07da6917b33`
- `fixture`: `3ceee277188c760ea03aa1982b12b032ef86b2420438d4d8496f777b5f61c98d`
- `harness`: `cc3c4ed0bf081a6f9b7cc995522f15529efffcc7f3b1978b6a89afb90ee1f330`
- `runner`: `814fc870d3f049c1ad4f0a20b33c5717292ba9c37e5d70aa790bdeae70713506`
- `script`: `b3bd8be00a27df2692c9fd0a3bbc288a3f36fab115ea090619d2946cc6ade027`

## Findings (AC-2 record)
**Crafted notebook, reopened untrusted (S2-B).** JupyterLab chose **`text/html`** from
`{text/html, text/plain}`, and its sanitizer **stripped the whole SVG**: `svg`, `g`, `path`, `rect`,
`text` and `title` are all absent. `table`, `details` and `summary` survive, but with **only `class`**;
`style`, `aria-label`, `role`, `tabindex`, `data-praxis-res` and `data-praxis-grid` are all stripped.
Trust state: `false`, corroborated three ways (output model, cell model, and the sentinel `onclick`
being stripped).

**Executed, saved and reopened in the same browser (S2-T).** The output reopens **trusted** and
renders **live**: `text/html`, all elements present, every listed attribute intact (`class`, `style`,
`role`, `aria-label`, `tabindex`, `data-*`, `viewBox`, `fill`, `stroke`, `stroke-width`,
`stroke-dasharray`, geometry). The close-and-reopen read and the reload-and-reopen read agreed
(`reopen_agree = true`), and the file on disk was verified saved before reopening.

**Controls.** `live` (trusted, kernel-displayed) is the positive control: every element and attribute
intact, and a second bundle containing a `<script>` and an `onclick` was observably live
(`live_positive_control_ok = true`). `neg_script_onclick` (its own crafted notebook): rendered as
`text/html` with both marker elements present in the file, trust corroborated untrusted, and the
`<script>` and every `onclick` were **stripped** (`negative_control_failed_as_required = true`), which
proves the sanitizer ran; the crafted and negative-control notebooks agree.

## Consequences for the spec
- **D1:** the S2-B downstream design applies to the crafted / untrusted-reopen path ("reopened
  outputs show name line, sentence, ledger table and error text, with no drawings until re-run;
  accepted"). S2-T applies to the executed-saved-reopened path: reopening a notebook the user ran in
  this browser keeps the live design. Interaction on untrusted reopened outputs (hover, keyboard,
  click to focus) is **not available** (`data-*` and `tabindex` are stripped) and returns when the cell
  is re-run, as D1 already states.
- **B2/B3 (reprs):** the text part of every output (name line, summary sentence, ledger `table`, error
  `details`/`summary`) must be meaningful on its own with only `class` surviving, since that is all an
  untrusted reopen keeps. No inline `style` or `data-*` may carry information the text does not.
- **A4/B9:** styling that must survive an untrusted reopen has to be keyed on `class` (the theme CSS
  already maps `.praxis-out`, `.praxis-error`, `.praxis-stale` by class); inline `style` colours are
  lost on untrusted reopen and only applied live.
- No spec text needs to change for S2. Reproduce: `bth sql "SELECT id, status, outcome, exit_code
  FROM runs WHERE id LIKE 'bf83a4e6%'"` after `bth compact`; artifacts under
  `outputs/spikes/260929_s2/` in the sprint worktree (gitignored; hashes above).

