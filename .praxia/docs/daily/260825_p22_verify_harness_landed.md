# Daily record: 260825_p22_verify_harness_landed

**daily_id:** 260825_p22_verify_harness_landed
**item:** Coxswain P2.2 execution-verify harness (backlog 4477)
**spec:** `.praxia/docs/specs/260825_coxswain-phase-2-functiongemma-copilot-p.md` rev2 §7 AC-2.2.x
**branch:** repl-fresh-boot (local only; NO push per constraints)

## Landed

`training/verify/` package (P2.2 deliverables 1-4) + tests + examples:

| File | LOC | Role |
|------|-----|------|
| `verify/__init__.py` | ~66 | public API; C-M-lizard convention docstring |
| `verify/deck.py` | ~230 | DeckFactory wrapper: DeckLayout, tiny-deck inference, seeding, snapshots |
| `verify/grounding.py` | ~105 | ref grammar (`name`, `name.well`, end-exclusive slices), Binding evidence rows |
| `verify/dispatcher.py` | ~195 | canonical->vendored kwarg mapping via PARAM_NAMESPACE; STRICT anomaly gate; PlanResult |
| `verify/checks.py` | ~500 | AC-2.2.2 tracker post-conditions; move location assertions; AC-2.2.3 slot agreement; effects table |
| `verify/verifier.py` | ~190 | async `verify(call_sequence, intent_record, backend=...) -> {passed, error?, state_before, state_after, checks}` |
| `verify/cli.py` | ~160 | batch CLI: dir mode, summary, exit codes, `--bench N` AC-2.2.4 gate |
| examples/*.json | 4 files | clean_transfer, aspirate_dispense_drop, move_plate, wrong_slot_known_failure (by design fails) |
| tests/test_verify_*.py | 5 files, 17 tests | post-conditions, strict anomalies, wrong-slot axis, moves, CLI+gate |

## Measured performance (AC-2.2.4)

- **100 verifications in 6.5s single-process (15.3/s, 65 ms each)** vs the <5 min budget.
- Gate verdict printed by `uv run --package training verify-cli training/examples --bench 100`.
- Full-scale lane in tests is opt-in (`P22_FULL_BENCH=1`) after a contention incident (below);
  default test lane measures a 12-run sample and asserts the projected rate.

## Test evidence

- `cd training && uv run --package training python -m pytest tests/ -q`
  -> **145 passed**, 1 failed -- the failure is P2.1's
  `test_golden_consistency.py::test_committed_artifacts_regenerate_byte_for_byte`
  (not this item's; owner notified).
- All 17 `test_verify_*` tests pass; suite wall time ~3s.

## Conventions recorded (juror finding C-M-lizard)

1. `move_resource/move_plate/move_lid` produce no tracker deltas -> intent check is a
   TARGET-LOCATION assertion via deck serialization topology (parent_name / location).
2. Post-condition volume checks key off the EXECUTED calls' own refs;
   slot-agreement + expected_effects tie execution to the INTENT. A wrong-slot call
   therefore passes post-conditions and fails agreement BY DESIGN
   (`examples/wrong_slot_known_failure.json` pins it).
3. PLR `_check_args` STRICT enforcement is inert for `**backend_kwargs` backends
   (all chatterbox ones), so the harness mirrors the semantics itself: under
   STRICT, params outside the canonical namespace raise TypeError before dispatch;
   under WARN they ride the backend_kwargs channel. Global set_strictness(STRICT)
   is still applied around every run and restored after (test proves restoration).
4. `expected_effects` are NET outcomes; pick-and-return-same-spot cycles within one
   run are post-conditioned by tips_delta instead of declaring loads_tips.

## Coordination notes

- training/pyproject.toml is SHARED between four parallel sub-pipelines. My first
  write clobbered skunk's file mid-flight (raced); recovered from journal and
  re-merged by skunk. Rule adopted: extend include lists / deps, never replace.
  My contribution to it: `[project.scripts] verify-cli` entry only.
- Root pyproject.toml members edit landed by skunk; I did not touch root.
- Incident: perf-gate test appeared to "spin forever" when three agents ran test
  suites concurrently on this box (~7 min at 104% CPU); with contention it exceeds
  any small per-test timeout. Mitigated by the sample-rate default lane +
  opt-in full bench; full-scale number recorded above via the CLI.

## Deviations

- read_* plate-reader verbs are rejected as unsupported in the LH harness
  (different receiver; phase-2 receiver plan keeps them out of scope here).
- transfer/aspirate/dispense require volume_ul for deterministic
  post-conditions; transfer without volume records an explanatory failed check.
