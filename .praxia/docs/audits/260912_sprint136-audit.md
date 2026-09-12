---
title: 'Sprint 136 review gate: R6 manifest scope narrowing (#5110) - PASS'
description: 'Sonnet praxia:reviewer report for commit e995de31, persisted verbatim: soundness answer, six-dimension scores, and the two non-blocking staleness suggestions with their resolution.'
status: completed
task_id: 260912_repl-gate-manifest-scope
date: '260912'
---
# Sprint 136 review gate: R6 manifest scope narrowing (#5110) - PASS

Gate of record for sprint 136. Agent: `praxia:reviewer` (Sonnet), no Bash, reading the
diff and the surrounding code directly. Scope: commit `e995de31` on
`repl-gate-manifest-scope` over `main` `c1e75d57`.

`code_review_diff` was **not** used: praxia debt #1793 (filed this cycle) records that its
`run_verification` `fmt` step reformats the workspace it reviews.

**Verdict: PASS**, confidence high. `required_fixes: []`. Next action: approve / merge
as-is.

| dimension | score |
|---|---|
| functional_correctness | 5 |
| security | 5 |
| code_quality | 4 |
| test_coverage | 4 |
| error_handling | 4 |
| documentation | 4 |

## The soundness question

> Can this change cause a REAL R6 violation to go undetected -- is there a tracked file
> that would genuinely shadow the browser wheel loader's manifest seam, which the old
> code caught and the new code does not?

**No.** `_WHEEL_MANIFEST_PARENTS` (`check_wheel_coherence.py:243-246`) contains exactly
the two paths anything in this codebase treats as a manifest-loader seam:

- `web-repl/overlay/assets/wheels` -- matches `_load_manifest`'s read path
  (`check_wheel_coherence.py:132`), `build_manifest.py`'s write path
  (`build_manifest.py:234,374`), `build_wheels.py`'s `OUTPUT_DIR`
  (`build_wheels.py:49`), and -- the decisive cross-check -- the browser loader's own
  `MANIFEST_REL_PATH = "assets/wheels/manifest.json"` (`web-repl/bootstrap/transport.py:67`).
- `praxis/web-client/src/assets/wheels` -- the pre-ADR stale location, matching
  `_TRACKED_OLD_WHEELS` (`check_wheel_coherence.py:229-232`).

A third *physical* manifest write exists at `build_repl.py:809`
(`out_dir / "assets" / "wheels" / "manifest.json"`), but `out_dir` is the staged `dist/`
tree and `dist/` is wholly gitignored (`web-repl/.gitignore:2`) -- a copy of the same
file, never independently tracked. Correctly out of R6's scope, not a missed location.

On the exact-parent match (`Path(p).parent in _WHEEL_MANIFEST_PARENTS`,
`check_wheel_coherence.py:281`), which means
`web-repl/overlay/assets/wheels/sub/manifest.json` is not flagged: **correctly out of
scope, not a gap** -- the loader fetches a fixed literal path (`transport.py:67`) and
never scans a subtree, so a nested manifest cannot shadow it.

## Checks the review ran on the tests

- `_manifest_problems()`'s substring filter (`test_check_wheel_coherence.py:60`) is not
  contaminated: the `.whl` message (`check_wheel_coherence.py:267-270`) and the
  gitignore-negation message (`:294-304`) were both read and neither contains the
  `manifest.json` substring.
- The tests pass a nonexistent `scratch / ".gitignore"`; `_find_gitignore_negation`
  (`:256-257`) explicitly guards `if not gitignore_path.is_file(): return []`, so they
  pass by design rather than by accident.
- All seven `repo-wide` occurrences in the file were re-checked; none now describes the
  manifest arm (`:59,61-64,242,269,320`).
- No other caller of `check_untracked` or `_git_ls_files` exists in the repo -- no ripple.
- The `#5110` citations (`check_wheel_coherence.py:37,236`;
  `test_check_wheel_coherence.py:8`) accurately describe the bug.

## The two suggestions, and their resolution

Both concern **pre-existing** staleness in adjacent code, not regressions from this diff.
The reviewer flagged them as uncertain because it could not read the git index without
Bash. The orchestrator resolved that afterwards:

```
git ls-files 'praxis/web-client/src/assets/wheels/*'   -> nothing tracked
grep 'src/assets/wheels' .gitignore                     -> negation absent
```

So **P3.11 has already landed**, and the reviewer's suspicion was right:
`_TRACKED_OLD_WHEELS`, the `_GITIGNORE_NEGATION` arm, the docstring text describing those
wheels as "currently tracked", and the second `_WHEEL_MANIFEST_PARENTS` entry are all now
dead. None is a correctness risk -- each can only ever produce a false positive, never a
false negative -- which is why none became a required fix.

Filed as **praxis debt #1795**. The second `_WHEEL_MANIFEST_PARENTS` entry is deliberately
retained as defensive scope until that cleanup runs, so a manifest reappearing at the old
location would still be caught. #1795 also carries the reviewer's second suggestion: a
direct unit test for `_find_gitignore_negation`, which is load-bearing for
`check_untracked`'s third arm and currently only covered incidentally.

## Note on the evidence the review relied on

Per its brief the reviewer did not re-run the tests; it assessed whether the
orchestrator's evidence was sufficient. That evidence was produced independently of the
dispatched fixer (whose ACP surface returns `claim_verified: null`, praxia debt #1773):
all 4 tests pass against the fix; run against the *unfixed* script, tests 1 and 4 fail
while 2 and 3 pass, confirming the first two are differential and the latter two are
regression guards; and CI step 12 was reproduced locally end to end with both commands
exiting 0.
