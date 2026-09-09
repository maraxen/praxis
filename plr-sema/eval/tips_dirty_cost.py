"""#4982 D2 (sprint 127 band D, `.praxia/docs/plans/260904_plr-sema-sprint127-
predicates.md` row D item 2): the `tips_dirty` precision cost.

**The question.** Increment 5's volume family (`.praxia/docs/specs/
260903_plr-sema-volume-increment.md` §14.5 V5) widens a tip cell's interval
to `TOP` at `pick_up_tips` whenever the walk-level `tips_dirty` flag is set
(`plr_sema.check.volumestate.VolumeWalk.pickup`, ~:182-186) -- a fail-closed
rule because tip movement outside the tip/volume families' own modelled
effects (`_is_unmodelled_tip_movement`, ~:489-523) is genuinely unmodelled,
not because the walk observed a dirty tip. **How much DEFINITE information
does that rule cost**, on the frozen tier-1 corpus replay and on the tier-2b
executed region fixtures, versus the alternative explanation that a cell
is `UNKNOWN` simply because it was never seeded (`TOP` at entry, §14.3)?

**Method.** Every population is run through `plr_sema.check.check_ir`
TWICE: (a) as shipped, and (b) with a **measurement-only** monkeypatch
(`_no_tips_dirty`, below) that replaces `volumestate.VolumeWalk` with a
subclass whose `pickup` ignores `tips_dirty` entirely -- a freshly-picked-
up tip is always `[0, 0]`, exactly as if V5's flag never existed. The
patch is scoped to one `check_ir` call (context manager, restored in a
``finally``) and never touches the shipped `VolumeWalk` class or its
`pickup` method -- (a) and (b) are bit-for-bit identical on-disk before
and after this script exists. **This is a measurement, not a proposal to
ship (b)**: the rule exists because unmodelled tip movement is a genuine
soundness gap, and turning it off would make some `WILL_FAIL`/`SAFE`
verdicts unsound on programs this script does not check.

Disabling `tips_dirty` never changes which `CALL`s are lowered, how many
`volume_guards` pair against them (`_v0_pairs` depends only on the call's
literal kwargs and the guard's cell/amount params, never on interval
state), or how many findings a row/fixture produces -- only the VERDICT a
`volume_state_unknown`-shipped finding gets in variant (b) can differ. So
raw findings from the two variants are compared pairwise, in order, per
op; every `volume_state_unknown` finding in (a) is bucketed as either
TURNED DEFINITE (its paired (b) finding is `safe`/`will_fail`) or STILL
UNKNOWN (identical or still-unknown in (b) -- the cell was never a tip
cell `tips_dirty` gates, or the pairing/tolerance itself is what leaves it
`UNKNOWN`, i.e. genuinely unseeded `TOP` or an unresolved amount/cell).

**Populations.**

* **Tier 1** -- the SAME sidecar-gated tier-1 population `oracle_replay.py`
  scores (343 executed rows / 548 ops at the frozen pin): this script
  reuses `oracle_replay.run_row` for the identical no_call/skip/setup_error
  gating (so the population is byte-identical to the frozen benchmark),
  then re-derives `call_sequence`/`intent_record`/`deck_layout` via a
  second, deterministic `row_to_verifier_inputs` call (same arguments
  `run_row` used) and re-lowers with `oracle_common.lower_row_calls` +
  `plr_sema.check.check_ir` directly -- the same path
  `oracle_common.run_static_calls` uses internally, but returning the RAW
  `Finding` tuple instead of the joined per-op summary (§11.10's shape),
  which is what a per-finding tips_dirty cost needs and
  `run_static_calls`'s joined `{"verdict", "n_findings", "reasons"}` shape
  cannot express. `env=frozenset()` throughout, matching
  `oracle_replay.run_row`'s own (unparametrised) call to
  `run_static_calls` exactly.
* **Tier 2b** -- the 16 executed region fixtures under
  `plr-sema/eval/fixtures/regions/*.py`, via `region_oracle.py`'s own
  static path (`region_oracle._static_report`, reused unmodified): extract
  -> inject synthetic `setup` -> `lower_graph` -> `check_ir` -> relabel.
  `env=frozenset({"does_volume_tracking"})` (the name read off the
  callable's own `__name__`, never typed) -- `region_oracle._run_fixture_
  execution` always leaves both trackers on before observing, so every
  fixture's real run observes `True`; this script skips the (expensive,
  irrelevant-to-a-purely-static-diff) async execution step and asserts
  the same constant env directly rather than re-deriving it 16 times.

Usage::

    uv run python plr-sema/eval/tips_dirty_cost.py \\
        --corpus training/assemble/out/corpus_p25.jsonl \\
        --sidecar training/assemble/out/corpus_p25_sidecar.jsonl \\
        --contracts plr-sema/data/derived_contracts.json \\
        --fixtures plr-sema/eval/fixtures/regions \\
        --report outputs/plr-sema/tips_dirty_cost_260904.json \\
        --limit 50
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "eval"))
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))

import oracle_common as oc  # noqa: E402
import region_oracle  # noqa: E402
from oracle_replay import RowResult, run_row  # noqa: E402

log = logging.getLogger("tips_dirty_cost")

DEFAULT_CONTRACTS = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json"
DEFAULT_FIXTURES_DIR = REPO_ROOT / "plr-sema" / "eval" / "fixtures" / "regions"

#: The one reason this whole script exists to move.
_TARGET_REASON = "volume_state_unknown"


# ---------------------------------------------------------------------------
# The measurement-only switch (#4982 D2). See module docstring.
# ---------------------------------------------------------------------------


def _no_tips_dirty_walk_cls(volumestate_mod):
    """Builds the measurement-only ``VolumeWalk`` subclass against the
    CALLER-SUPPLIED ``volumestate`` module object (never imports it itself)
    so this stays a pure function of an already-imported module -- no
    second import path, no risk of subclassing a stale copy.
    """

    class _NoTipsDirtyVolumeWalk(volumestate_mod.VolumeWalk):
        """Measurement-only override (#4982 D2): ``pickup`` no longer reads
        ``tips_dirty`` -- a freshly-picked-up tip is always treated as
        provably empty (``[0, 0]``), exactly as if V5's whole-walk
        ``tips_dirty`` flag never existed. NOT a proposed change to shipped
        behaviour: tip movement outside the tip/volume families' modelled
        effects genuinely is unmodelled (volumestate.py's own module
        docstring), and the fail-closed rule exists for that reason. This
        class is injected ONLY by this script (see ``_no_tips_dirty``
        below), scoped to one ``check_ir`` call; the shipped ``VolumeWalk``
        class is untouched.
        """

        def pickup(self, cell: Any) -> None:
            self._cells[cell] = volumestate_mod.Interval(0.0, 0.0)

    return _NoTipsDirtyVolumeWalk


@contextlib.contextmanager
def _no_tips_dirty():
    """Monkeypatches ``plr_sema.check.volumestate.VolumeWalk`` for the
    duration of the ``with`` block, restoring the original class in a
    ``finally`` regardless of how the block exits. ``check/__init__.py``
    imports the module with ``from plr_sema.check import ... volumestate``
    (binding the name to the SAME module object this function patches), and
    constructs ``vwalk = volumestate.VolumeWalk()`` by late-bound attribute
    lookup at call time -- so patching the attribute here is visible to
    every ``check_ir`` call made inside the ``with`` block, and the patch
    is gone the instant the block exits.
    """
    from plr_sema.check import volumestate as volumestate_mod

    original = volumestate_mod.VolumeWalk
    volumestate_mod.VolumeWalk = _no_tips_dirty_walk_cls(volumestate_mod)
    try:
        yield
    finally:
        volumestate_mod.VolumeWalk = original


# ---------------------------------------------------------------------------
# Accumulator
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class MethodBucket:
    n_volume_state_unknown_shipped: int = 0
    n_turned_definite_without_rule: int = 0
    n_still_unknown_unseeded: int = 0


@dataclasses.dataclass
class TierAccumulator:
    n_ops: int = 0
    n_volume_state_unknown_shipped: int = 0
    n_turned_definite_without_rule: int = 0
    n_still_unknown_unseeded: int = 0
    by_method: dict[str, MethodBucket] = dataclasses.field(default_factory=dict)
    #: rows/fixtures where the two variants' raw finding COUNTS diverged --
    #: should never happen (see module docstring's invariant argument);
    #: recorded, not silently ignored, if it ever does.
    length_mismatches: list[str] = dataclasses.field(default_factory=list)

    def _bucket(self, method: str) -> MethodBucket:
        return self.by_method.setdefault(method, MethodBucket())

    def record_pair(self, method: str, shipped_finding: Any, nodirty_finding: Any) -> None:
        if shipped_finding.reason != _TARGET_REASON:
            return
        self.n_volume_state_unknown_shipped += 1
        bucket = self._bucket(method)
        bucket.n_volume_state_unknown_shipped += 1
        if nodirty_finding.verdict.value in ("safe", "will_fail"):
            self.n_turned_definite_without_rule += 1
            bucket.n_turned_definite_without_rule += 1
        else:
            self.n_still_unknown_unseeded += 1
            bucket.n_still_unknown_unseeded += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_ops": self.n_ops,
            "n_volume_state_unknown_shipped": self.n_volume_state_unknown_shipped,
            "n_turned_definite_without_rule": self.n_turned_definite_without_rule,
            "n_still_unknown_unseeded": self.n_still_unknown_unseeded,
            "by_method": {
                method: dataclasses.asdict(bucket)
                for method, bucket in sorted(self.by_method.items())
            },
            "length_mismatches": self.length_mismatches,
        }


def _op_id_to_method(instructions: tuple[Any, ...], origin: dict[int, str]) -> dict[str, str]:
    """``op_id -> PLR method name``, read off the lowered IR's own ``Call``
    instructions (``ir.Call.method``) via the SAME ``pc -> op_id`` map
    ``relabel_findings`` uses -- never a second, hand-maintained name list.
    """
    from plr_sema.check import ir as _ir

    out: dict[str, str] = {}
    for pc, op_id in origin.items():
        if 0 <= pc < len(instructions) and isinstance(instructions[pc], _ir.Call):
            out[op_id] = instructions[pc].method
    return out


def _diff_findings(
    acc: TierAccumulator,
    *,
    row_or_fixture_id: str,
    shipped: tuple[Any, ...],
    nodirty: tuple[Any, ...],
    op_id_to_method: dict[str, str],
) -> None:
    if len(shipped) != len(nodirty):
        log.warning(
            "%s: raw finding count diverged between variants (%d shipped vs %d no-tips-dirty) "
            "-- skipping pairwise diff for this row/fixture (see module docstring's invariant)",
            row_or_fixture_id, len(shipped), len(nodirty),
        )
        acc.length_mismatches.append(row_or_fixture_id)
        return
    for f_shipped, f_nodirty in zip(shipped, nodirty):
        method = op_id_to_method.get(f_shipped.operation_id, "<unknown>")
        acc.record_pair(method, f_shipped, f_nodirty)


# ---------------------------------------------------------------------------
# Tier 1 -- the frozen sidecar-gated corpus replay population.
# ---------------------------------------------------------------------------


def _tier1_raw_findings(
    row: dict[str, Any],
    corpus_file: str,
    row_index: int,
    contracts_json: str,
    contracts: dict[str, Any],
    receiver_states: dict[str, Any],
    param_names: dict[str, tuple[str, ...]],
    *,
    ambiguity_class: str | None,
    sidecar_record_id: str | None,
    provenance: str | None,
    result: RowResult,
) -> tuple[tuple[Any, ...], tuple[Any, ...], dict[str, str]] | None:
    """Raw findings for ONE already-classified executed, non-setup_error
    tier-1 row -- ``(shipped, nodirty, op_id_to_method)``, or ``None`` if
    the row's own lowering diverges from what produced ``result`` (should
    not happen; ``row_to_verifier_inputs`` is a pure function of its
    arguments, and ``result`` was built from the identical arguments).
    """
    from plr_sema.check import check_ir
    from plr_sema.check import ir as _ir

    call_sequence, intent_record, deck_layout, skip_reason, no_call_reason = oc.row_to_verifier_inputs(
        row, source_file=Path(corpus_file).stem, line=row_index,
        ambiguity_class=ambiguity_class, sidecar_record_id=sidecar_record_id, provenance=provenance,
    )
    if no_call_reason or skip_reason:
        return None  # defensive; caller already filtered on `result`.
    example = {"call_sequence": call_sequence, "intent_record": intent_record, "deck_layout": deck_layout}
    resources = oc.resources_from_example(example)
    bc, not_planned = oc.lower_row_calls(example, result.plr_kwargs, resources=resources, param_names=param_names)
    if sorted(not_planned) != sorted(result.not_planned_indices):
        log.warning(
            "%s: re-derived not_planned_indices %s != RowResult's %s -- lowering is not "
            "reproducing run_row's own call, skipping", result.record_id, not_planned, result.not_planned_indices,
        )
        return None

    # Same origin rewrite oracle_common.run_static_calls does internally
    # (mirrored here, once, rather than re-derived per finding/per method).
    planned_indices = [i for i in range(len(call_sequence)) if i not in set(not_planned)]
    origin = bc.sideband.get("origin", {})
    setup_pcs = {pc for pc, local_idx in origin.items() if local_idx == "setup"}
    real_origin = {
        pc: f"op_{planned_indices[int(local_idx)]}" for pc, local_idx in origin.items() if local_idx != "setup"
    }
    op_id_to_method = _op_id_to_method(bc.instructions, real_origin)

    def _relabel(raw: tuple[Any, ...]) -> tuple[Any, ...]:
        raw = tuple(f for f in raw if int(f.operation_id) not in setup_pcs)
        return _ir.relabel_findings(raw, real_origin)

    shipped_raw = check_ir(bc, contracts, receiver_states, env=frozenset())
    shipped = _relabel(shipped_raw)
    with _no_tips_dirty():
        nodirty_raw = check_ir(bc, contracts, receiver_states, env=frozenset())
    nodirty = _relabel(nodirty_raw)
    return shipped, nodirty, op_id_to_method


def _run_tier1(
    acc: TierAccumulator,
    *,
    corpus_files: list[str],
    sidecar_path: str | None,
    contracts_json: str,
    limit: int | None,
) -> None:
    contracts_payload = json.loads(contracts_json)
    contracts = contracts_payload.get("contracts", {})
    receiver_states = contracts_payload.get("receiver_state", {})
    param_names = oc.param_names_from_contracts(contracts_json)

    sidecar_rows: list[dict[str, Any]] = []
    sidecar_by_digest: dict[str, dict[str, Any]] = {}
    if sidecar_path:
        with open(sidecar_path) as f:
            for line in f:
                if not line.strip():
                    continue
                srow = json.loads(line)
                sidecar_rows.append(srow)
                utt = srow.get("utterance", "")
                raw_calls = srow.get("calls") or []
                call = (
                    {"name": raw_calls[0].get("name", ""), "params": raw_calls[0].get("params", {})}
                    if raw_calls else None
                )
                digest = oc.content_digest(utt, call)
                sidecar_by_digest.setdefault(digest, srow)
        log.info("Loaded %d sidecar rows from %s", len(sidecar_rows), sidecar_path)

    def _sidecar_for(line_no: int, row: dict[str, Any], exact_eligible: bool):
        if not sidecar_rows:
            return None, "none"
        if exact_eligible and 1 <= line_no <= len(sidecar_rows):
            return sidecar_rows[line_no - 1], "line_exact"
        utterance, call = oc.extract_first_call(row)
        srow = sidecar_by_digest.get(oc.content_digest(utterance, call))
        return (srow, "content_fallback") if srow is not None else (None, "unmatched")

    n_rows_total = 0
    n_rows_considered = 0  # matches n_rows_executed in oracle_replay.py (setup_error excluded)
    n_rows_setup_error = 0

    def _is_setup_error(r: RowResult) -> bool:
        return bool(r.not_planned_indices) and len(r.not_planned_indices) == r.n_operations_executed

    for corpus_file in corpus_files:
        with open(corpus_file) as f:
            corpus_lines = f.readlines()
        exact_eligible = len(sidecar_rows) > 0 and len(corpus_lines) == len(sidecar_rows)
        for line_no, line in enumerate(corpus_lines, 1):
            if limit and n_rows_total >= limit:
                break
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception as e:
                log.warning("Failed to parse JSON at %s:%d: %s", corpus_file, line_no, e)
                continue
            n_rows_total += 1
            srow, _join_method = _sidecar_for(line_no, row, exact_eligible)
            ambiguity_class = srow.get("ambiguity_class") if srow else None
            sidecar_record_id = srow.get("record_id") if srow else None
            provenance = srow.get("provenance") if srow else None

            result = run_row(
                row, corpus_file, line_no, contracts_json,
                ambiguity_class=ambiguity_class, sidecar_record_id=sidecar_record_id, provenance=provenance,
            )
            if result.no_call_reason or result.skip_reason:
                continue
            if _is_setup_error(result):
                n_rows_setup_error += 1
                continue
            n_rows_considered += 1

            found = _tier1_raw_findings(
                row, corpus_file, line_no, contracts_json, contracts, receiver_states, param_names,
                ambiguity_class=ambiguity_class, sidecar_record_id=sidecar_record_id, provenance=provenance,
                result=result,
            )
            if found is None:
                continue
            shipped, nodirty, op_id_to_method = found
            acc.n_ops += result.n_operations_executed
            _diff_findings(
                acc, row_or_fixture_id=result.record_id, shipped=shipped, nodirty=nodirty,
                op_id_to_method=op_id_to_method,
            )
            if n_rows_considered % 100 == 0:
                log.info("tier1: considered %d rows (setup_error=%d)...", n_rows_considered, n_rows_setup_error)

    log.info(
        "tier1: rows_total=%d rows_considered=%d rows_setup_error=%d ops=%d",
        n_rows_total, n_rows_considered, n_rows_setup_error, acc.n_ops,
    )


# ---------------------------------------------------------------------------
# Tier 2b -- the 16 executed region fixtures.
# ---------------------------------------------------------------------------


def _run_tier2b(acc: TierAccumulator, *, fixtures_dir: Path, contracts_json: str, limit: int | None) -> None:
    from pylabrobot.resources.volume_tracker import does_volume_tracking

    ir_mod = region_oracle._lazy_ir()
    check_mod, _supported_tools, _verdict_cls, _join_fn = region_oracle._lazy_check()
    contracts_payload = json.loads(contracts_json)
    param_names = oc.param_names_from_contracts(contracts_json)
    # 260903 (spec §14.6/§14.11): the name comes from the callable's own
    # __name__, never a typed string -- `region_oracle._run_fixture_
    # execution` always sets both trackers True before observing, so every
    # fixture's real (unmeasured) run observes True; this script asserts
    # the constant directly rather than paying for 16 async executions
    # whose runtime outcome this purely-static diff does not use.
    env = frozenset({does_volume_tracking.__name__})

    cache_dir = Path(tempfile.gettempdir()) / "plr_sema_tips_dirty_cost_extract"
    cache_dir.mkdir(parents=True, exist_ok=True)

    fixture_paths = sorted(fixtures_dir.glob("*.py"))
    if limit:
        fixture_paths = fixture_paths[:limit]
    if not fixture_paths:
        log.error("no fixtures found under %s", fixtures_dir)
        return

    for path in fixture_paths:
        name = path.stem
        try:
            payload = region_oracle._extract_graph_payload(
                path, cache_dir=cache_dir, runner_python=sys.executable,
            )
        except Exception as e:
            log.warning("%s: extract failed, skipping: %s", name, e)
            continue

        try:
            bytecode, shipped, _join_map, _static, _proved = region_oracle._static_report(
                payload, contracts_payload, param_names, ir_mod, check_mod, env=env,
            )
            with _no_tips_dirty():
                _bc2, nodirty, _jm2, _st2, _pt2 = region_oracle._static_report(
                    payload, contracts_payload, param_names, ir_mod, check_mod, env=env,
                )
        except Exception as e:
            log.warning("%s: static check failed, skipping: %s", name, e)
            continue

        origin = bytecode.sideband.get("origin", {})
        op_id_to_method = _op_id_to_method(bytecode.instructions, origin)
        n_ops = sum(1 for instr in bytecode.instructions if isinstance(instr, ir_mod.Call))
        acc.n_ops += n_ops
        _diff_findings(
            acc, row_or_fixture_id=name, shipped=tuple(shipped), nodirty=tuple(nodirty),
            op_id_to_method=op_id_to_method,
        )
        log.info("tier2b: %-32s n_ops=%d n_findings=%d", name, n_ops, len(shipped))

    log.info("tier2b: fixtures=%d ops=%d", len(fixture_paths), acc.n_ops)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", type=str, action="append", required=True, help="corpus JSONL file (repeatable)")
    ap.add_argument("--sidecar", type=str, default=None, help="assemble sidecar JSONL (same join as oracle_replay.py)")
    ap.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS, help="contract table JSON")
    ap.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES_DIR, help="directory of *.py region fixtures")
    ap.add_argument("--report", type=Path, required=True, help="JSON report output")
    ap.add_argument("--limit", type=int, default=None, help="smoke-test limit (rows AND fixtures)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    contracts_json = args.contracts.read_text(encoding="utf-8")

    tier1 = TierAccumulator()
    _run_tier1(tier1, corpus_files=args.corpus, sidecar_path=args.sidecar, contracts_json=contracts_json, limit=args.limit)

    tier2b = TierAccumulator()
    _run_tier2b(tier2b, fixtures_dir=args.fixtures, contracts_json=contracts_json, limit=args.limit)

    summary_flat = {
        "tier1_n_ops": tier1.n_ops,
        "tier1_n_volume_state_unknown_shipped": tier1.n_volume_state_unknown_shipped,
        "tier1_n_turned_definite_without_rule": tier1.n_turned_definite_without_rule,
        "tier1_n_still_unknown_unseeded": tier1.n_still_unknown_unseeded,
        "tier1_length_mismatches": len(tier1.length_mismatches),
        "tier2b_n_ops": tier2b.n_ops,
        "tier2b_n_volume_state_unknown_shipped": tier2b.n_volume_state_unknown_shipped,
        "tier2b_n_turned_definite_without_rule": tier2b.n_turned_definite_without_rule,
        "tier2b_n_still_unknown_unseeded": tier2b.n_still_unknown_unseeded,
        "tier2b_length_mismatches": len(tier2b.length_mismatches),
    }

    report = {
        "summary_flat": summary_flat,
        "tier1": tier1.to_dict(),
        "tier2b": tier2b.to_dict(),
        "notes": [
            "Expected on tier 1: the frozen corpus never seeds a well or disables a tracker "
            "(increment 5 sprint 123 close, 0 of 1523 sidecar rows mention "
            "set_volume/set_liquids/disable_volume_trackers), so every CONTAINER cell is "
            "unseeded TOP at entry regardless of tips_dirty. The tips_dirty rule only "
            "changes a TIP cell's entry interval at pick_up_tips, and only a volume guard "
            "whose cell_param resolves to a tip (the local/tip V0 pairing clause) ever pairs "
            "against one -- so the a-priori expectation is that tips_dirty costs zero (or "
            "very few) definite verdicts on tier 1, dominated instead by container cells that "
            "were never going to be definite regardless (n_still_unknown_unseeded >> "
            "n_turned_definite_without_rule).",
            f"Actual tier 1: n_volume_state_unknown_shipped={tier1.n_volume_state_unknown_shipped}, "
            f"n_turned_definite_without_rule={tier1.n_turned_definite_without_rule}, "
            f"n_still_unknown_unseeded={tier1.n_still_unknown_unseeded}.",
            f"Actual tier 2b: n_volume_state_unknown_shipped={tier2b.n_volume_state_unknown_shipped}, "
            f"n_turned_definite_without_rule={tier2b.n_turned_definite_without_rule}, "
            f"n_still_unknown_unseeded={tier2b.n_still_unknown_unseeded}.",
            "Soundness caveat: the no-tips-dirty variant (b) is a MEASUREMENT, not a proposal to "
            "ship. The tips_dirty rule exists because tip movement outside the tip/volume "
            "families' own modelled effects (move_resource/move_plate over a tip rack, stamp, "
            "any 96-head operation, or an unresolved-channel departure) is genuinely unmodelled "
            "-- turning the rule off would make some SAFE/WILL_FAIL verdicts unsound on programs "
            "this script does not check. No shipped file changed to produce this report.",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2))
    log.info("Report written to %s", args.report)

    bth_path = os.environ.get("BTH_RESULTS_PATH")
    if bth_path:
        Path(bth_path).write_text(json.dumps(summary_flat))
        log.info("Bathos results written to %s", bth_path)

    log.info(
        "summary: tier1 ops=%d unknown_shipped=%d turned_definite=%d still_unknown=%d | "
        "tier2b ops=%d unknown_shipped=%d turned_definite=%d still_unknown=%d",
        tier1.n_ops, tier1.n_volume_state_unknown_shipped, tier1.n_turned_definite_without_rule,
        tier1.n_still_unknown_unseeded,
        tier2b.n_ops, tier2b.n_volume_state_unknown_shipped, tier2b.n_turned_definite_without_rule,
        tier2b.n_still_unknown_unseeded,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
