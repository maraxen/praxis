---
title: 'plr-sema sprint 135 audit (#5043): PASS -- the volume wire cannot mint a SAFE, and the null re-measure is correctly explained'
description: 'praxia:reviewer (Sonnet) source-level audit of 12003b06..b857b301 (T57 fix + differential test, T58 re-measure + tracked scripts). Verdict PASS, high confidence, no required fixes. Confirms env is consumed only on volumestate._pair_finding''s fires branch (WILL_FAIL vs volume_tracking_unasserted), the safe branch is env-independent, the T58 null result (194 / 2916 / 0 / 0 / 216, identical to inc8) is confirmed against the JSON and explained by volume_tracking_unasserted 0 before and after, and the test is non-vacuous. Two cosmetic suggestions.'
status: completed
task_id: 260911_sema-volume-wiring
date: '260911'
---
# plr-sema sprint 135 audit (#5043)

Reviewer: `praxia:reviewer` (Sonnet, `claude-sonnet-5`), Read/Grep/Glob only. Range `12003b06..b857b301`
on `plr-sema-volume-observation-wiring`. Persisted verbatim by the orchestrator (the agent has no Write).

## Verdict

**PASS**, confidence high.

> The T57 fix threads `RuntimeOutcome.volume_tracking_observed` into both corpus-replay call sites of
> `run_static_calls`, exactly mirroring the already-correct `predicate_mutants.py` sibling; source-level
> trace confirms `env` is consumed only inside `volumestate._pair_finding`'s `fires` branch (choosing
> WILL_FAIL vs. UNKNOWN/`volume_tracking_unasserted`) and never touches the `safe` branch, so no new SAFE
> verdict is reachable. The T58 re-measurement's null result (194/2916/0/0/216, byte-identical to the
> inc8 baseline) is independently confirmed against the actual JSON artifacts, and is correctly explained
> by `volume_tracking_unasserted` being 0 both before and after (no benchmark row has a firing volume
> guard). The differential test is non-vacuous and correctly scoped; citations resolve to real spec
> sections.

**The one-line soundness answer:** No -- `env`'s only consumer (`volumestate._pair_finding`, via
`volume_guard_is_unconditional`) is read exclusively on the `fires` branch to choose `WILL_FAIL` vs.
`UNKNOWN` (`volume_tracking_unasserted`); the `safe` branch (`_safe`, and the per-op join's monotonic
combination) is computed independent of `env`, so this change cannot produce a SAFE verdict that
pre-change code would not have produced.

## Scores

| dimension | score |
|---|---|
| functional_correctness | 5 |
| security | 5 |
| code_quality | 4 |
| test_coverage | 4 |
| error_handling | 5 |
| documentation | 5 |

Verification: tests/lint/types not re-run by the reviewer (read-only role); the orchestrator's own runs
stand (per-file suite 75 passed in the dispatch worktree and again after applying here).

## Required fixes

None.

## Suggestions (cosmetic, both addressed or dispositioned at close)

1. `plr-sema/scripts/probe_volume_observation.py` and `compare_unknown_ledgers.py` use 2-space
   indentation while sibling scripts use 4-space. **Disposition:** the 2-space form is what
   `uv run ruff format` produces under `plr-sema/pyproject.toml`'s own ruff configuration; the siblings
   predate it and fail `ruff format --check`. Left as the formatter emits it, recorded here.
2. `plr-sema/scripts/oracle_spike.py:84`'s comment was terser than `oracle_replay.py`'s parallel one.
   **Addressed** in the close commit: expanded to the same citation depth plus the soundness note.

## What was checked, in the reviewer's words

- Both edits pass the row's own `rt.volume_tracking_observed` (not a process-wide re-read).
- `run_static_calls` builds `env = {does_volume_tracking.__name__}` iff the flag is True; `env` reaches
  `check_ir`; the only consumer is `_pair_finding`'s `fires` branch.
- `TestT57VolumeObservationThreading` fails against the unfixed call site on its first assertion and
  cannot pass vacuously (the `recorded_kwargs` guard precedes the membership assertion); monkeypatch
  targets are the names as bound in the `oracle_replay` module namespace.
- The T58 numbers were re-read from the committed artifacts, not from the commit message.
- Spec sections §14.6 / §14.11 cited in the T57 comments exist in
  `.praxia/docs/specs/260903_plr-sema-volume-increment.md`.
