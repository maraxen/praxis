# plr-sema

> Renamed twice: `plr-jit` → `plr-preflight` → `plr-sema` (all 260901–02). "JIT" named a mechanism that
> never existed; "preflight" named only the pre-execution moment. What the package is, in
> compiler terms, is the semantic-analysis pass over PLR programs: it builds the execution-graph
> IR and checks it for well-formedness and state validity. Error recovery and optimization are
> later passes over the same IR. Historical task_ids keep whichever name was current.

Semantic analysis of PyLabRobot programs: execution-graph IR, well-formedness, and per-operation SAFE / WILL_FAIL / UNKNOWN verdicts.

Decomposes a protocol's arguments into PLR resources, static/invariant values,
and dynamic values; maps the execution graph; and validates — on the code side —
that PLR state will not produce an error.

**v1 is a sound static analyzer.** Every verdict is one of `SAFE` / `WILL_FAIL` /
`UNKNOWN`, never a boolean, and `UNKNOWN` is the default for anything derivation
cannot resolve. Error recovery and hardware/command-stream optimization are
later extensions on the same substrate, not v1 scope.

The package is self-contained: nothing under `src/plr_sema/` may import `praxis`,
`verify`, or `training`, enforced by `tests/test_import_boundary.py`.

Specification: `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md`
