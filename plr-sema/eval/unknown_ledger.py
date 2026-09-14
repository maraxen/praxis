"""The UNKNOWN ledger (band B0, backlog #4976, sprint 127 `260904_sema-predicates`).

Clusters the raw ``UNKNOWN``-verdict :class:`plr_sema.verdict.Finding` objects
the frozen tier-1 sidecar-gated benchmark (:mod:`oracle_replay`) produces on
EXECUTED real operations, keyed by ``(reason, plr_site, detail)`` -- the
"absolute count of UNKNOWN root causes, clusters not raw findings, on a named
frozen benchmark at a fixed pin" shape the main spec's deferred row (f)
settled on (`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md`
§1 row B0). This is the INSTRUMENT the whole sprint is measured against; it
makes **no analyzer semantics change** -- it only observes
:mod:`oracle_common`'s own row pipeline through the additive
``FINDINGS_SINK`` seam (#4976) and re-derives its own populations from the
SAME ``rows`` / ``denominators`` :mod:`oracle_replay` already publishes, so
nothing here can disagree with tier 1's own ``unknown_rate`` about which rows
or ops are "executed".

Pipeline (does not reimplement oracle_replay's row pipeline):

1. Install :data:`oracle_common.FINDINGS_SINK` to collect ``(row_id,
   findings)`` for every :func:`oracle_common.run_static_calls` invocation,
   in call order.
2. Call :func:`oracle_replay.main` with the frozen benchmark's own
   ``--corpus``/``--sidecar``/``--crosscheck`` arguments (pass-through),
   writing oracle_replay's OWN report to ``--replay-report`` (default:
   alongside ``--report``). Uninstall the sink in a ``finally`` so this
   script never leaves global state behind for a later import in the same
   interpreter (matters for the test suite).
3. Correlate collected findings back to oracle_replay's own per-row records
   by POSITION, not by ``record_id`` string equality: oracle_replay's own
   docstring (``content_digest``) records that 58/1427 corpus rows share a
   digest with >=1 other row, so a record_id is not a safe join key. The
   sink fires exactly once per row that reaches oracle_replay's "Static"
   section (:func:`oracle_replay.run_row`'s control flow returns BEFORE that
   section for every ``no_call``/``skipped`` row and never reaches it), in
   the same relative order oracle_replay itself iterates the corpus -- so
   ``report["rows"]`` filtered to ``no_call_reason is None and skip_reason
   is None``, in file order, zips 1:1 against the sink's own call order.
   This script asserts that invariant rather than assuming it.
4. Group each row's findings by (real, relabelled) ``operation_id``, compute
   each operation's own :func:`plr_sema.verdict.join` verdict from exactly
   the findings that operation carries (the SAME join oracle_replay's own
   ``compare()``/``unknown_rate`` reads via ``run_static_calls``'s ``verdict``
   key -- this script does not special-case anything oracle_replay does not
   already special-case), and cluster the UNKNOWN-verdict operations' own
   UNKNOWN findings.

Usage::

    uv run python plr-sema/eval/unknown_ledger.py \\
        --corpus training/assemble/out/corpus_p25.jsonl \\
        --sidecar training/assemble/out/corpus_p25_sidecar.jsonl \\
        --crosscheck training/out/corpus_p23_floor.jsonl \\
        --crosscheck training/overlay_gen/out/overlay_full.jsonl \\
        --report outputs/plr-sema/unknown_ledger_260904_before.json
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import oracle_common as oc  # noqa: E402
import oracle_replay  # noqa: E402

log = logging.getLogger(__name__)

DEFAULT_CONTRACTS = oc.DEFAULT_CONTRACTS
BENCHMARK_NAME = "tier1-sidecar-gated-dd79c4c89"


def _git_head() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception as e:  # pragma: no cover - diagnostic path only
        return f"<unavailable: {e}>"


def _plr_pin() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT / "external" / "pylabrobot"), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception as e:  # pragma: no cover - diagnostic path only
        return f"<unavailable: {e}>"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _site_key(plr_site: Any) -> str:
    """``"file:line:qualname"`` for a :class:`plr_sema.verdict.PlrSite`, or
    the literal string ``"<none>"`` for a Finding with no site (§ item 3's
    cluster key component)."""
    if plr_site is None:
        return "<none>"
    return f"{plr_site.file}:{plr_site.lineno}:{plr_site.qualname}"


@dataclasses.dataclass
class ClusterAccumulator:
    reason: str
    site: str
    detail: str
    n_findings: int = 0
    ops_blocked: set[tuple[int, str]] = dataclasses.field(default_factory=set)
    sole_blocker_ops: set[tuple[int, str]] = dataclasses.field(default_factory=set)
    per_method: collections.Counter = dataclasses.field(default_factory=collections.Counter)
    example_ops: list[tuple[int, str, str]] = dataclasses.field(default_factory=list)

    def add(self, row_idx: int, row_id: str, op_id: str, method: str) -> None:
        """Key by the POSITIONAL ``(row_idx, op_id)`` pair, never by
        ``(row_id, op_id)``. ``row_id`` is a content digest
        (``oracle_common.content_digest``, module docstring point 3) that
        collides across a documented ~4% of corpus rows, so two DIFFERENT
        ops belonging to two DIFFERENT rows can carry the identical
        ``row_id`` -- deduping on that string silently merged such ops into
        one ``ops_blocked`` entry, undercounting ``n_ops_blocked`` /
        ``n_ops_sole_blocker`` by exactly the collision count (band B0 fix,
        backlog #4976, round-1 challenger C12). ``row_idx`` is assigned by
        ``enumerate`` over one ``build_ledger`` call's own ``row_findings``
        and is therefore unique per row by construction, so this key cannot
        collide the way ``row_id`` does. ``row_id`` is kept in
        ``example_ops`` purely for human-readable display.
        """
        key = (row_idx, op_id)
        is_new_op = key not in self.ops_blocked
        self.n_findings += 1
        self.ops_blocked.add(key)
        if is_new_op:
            self.per_method[method] += 1
            if len(self.example_ops) < 5:
                self.example_ops.append((row_idx, row_id, op_id))

    def mark_sole_blocker(self, row_idx: int, op_id: str) -> None:
        self.sole_blocker_ops.add((row_idx, op_id))

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "plr_site": self.site,
            "condition": self.detail,
            "n_findings": self.n_findings,
            "n_ops_blocked": len(self.ops_blocked),
            "n_ops_sole_blocker": len(self.sole_blocker_ops),
            "per_method": dict(sorted(self.per_method.items(), key=lambda kv: (-kv[1], kv[0]))),
            "example_ops": [
                {"row_idx": i, "row_id": r, "op_id": o} for i, r, o in self.example_ops
            ],
        }


def cluster_unknown_findings(
    row_findings: list[tuple[str, tuple[Any, ...]]],
    row_methods: list[list[str]],
) -> dict[str, Any]:
    """Pure clustering core (unit-tested directly in
    ``test_unknown_ledger.py`` on synthetic Findings, no oracle_replay
    invocation needed).

    ``row_findings``: one entry per executed row, ``(row_id, findings)`` --
    ``findings`` is exactly what :data:`oracle_common.FINDINGS_SINK`
    receives for that row (relabelled real ``op_<i>`` ids, setup already
    excluded).
    ``row_methods``: the SAME length, ``row_methods[k][i]`` is the call
    name for ``op_<i>`` of ``row_findings[k]`` (i.e. the row's own
    ``call_names``/``calls`` list) -- used only for the ``per_method``
    breakdown; a missing/short entry degrades to ``"<unknown>"`` rather
    than raising, so a caller that cannot supply methods (the pure unit
    tests) still gets correct clusters, just without method attribution.

    Returns a dict with ``clusters`` (list, deterministically sorted by
    ``n_ops_blocked`` desc then the cluster key), ``per_op_reason_set_histogram``
    (a list of ``{"reason_set": [...], "n_ops": n}`` sorted the same way),
    ``n_ops_executed`` (distinct ``(row_idx, op_id)`` pairs seen at all,
    regardless of verdict), ``n_ops_unknown``, ``n_findings_total`` (UNKNOWN
    findings on UNKNOWN-verdict ops only), ``n_findings_by_reason``,
    ``n_clusters``, ``n_row_id_collisions`` and ``collision_ops`` (band B0
    fix, #4976 round-1 C12 -- see :meth:`ClusterAccumulator.add`), and
    ``consistency`` (the invariant cross-checks from :func:`_compute_consistency`).
    """
    sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))
    from plr_sema.verdict import Verdict, join

    clusters: dict[tuple[str, str, str], ClusterAccumulator] = {}
    reason_set_histogram: collections.Counter = collections.Counter()
    n_findings_by_reason: collections.Counter = collections.Counter()
    n_ops_executed = 0
    n_ops_unknown = 0
    n_findings_total = 0
    all_op_keys: set[tuple[int, str]] = set()
    # Content-digest collision bookkeeping (diagnostic only -- NOT used as a
    # dedup key anywhere; see ClusterAccumulator.add's docstring). Keyed by
    # the LEGACY, pre-fix (row_id, op_id) pair so a genuine collision --
    # two different (row_idx, op_id) UNKNOWN ops sharing one row_id -- is
    # detected and published instead of silently merged.
    legacy_unknown_ops: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)

    for row_idx, (row_id, findings) in enumerate(row_findings):
        methods = row_methods[row_idx] if row_idx < len(row_methods) else []
        per_op: dict[str, list[Any]] = collections.defaultdict(list)
        for f in findings:
            per_op[f.operation_id].append(f)
        for op_id, flist in per_op.items():
            key = (row_idx, op_id)
            # row_idx is unique per iteration of the outer loop and op_id is
            # unique within one row's own per_op dict, so this positional
            # key cannot collide by construction; a hit here would mean the
            # row/op iteration itself is broken, not a content-digest
            # collision (those are tracked below via legacy_unknown_ops).
            assert key not in all_op_keys, f"positional (row_idx, op_id) key collided: {key!r}"
            all_op_keys.add(key)
            n_ops_executed += 1
            verdict = join(tuple(flist))
            if verdict is not Verdict.UNKNOWN:
                continue
            n_ops_unknown += 1
            try:
                idx = int(op_id.split("_", 1)[1])
            except (IndexError, ValueError):
                idx = -1
            method = methods[idx] if 0 <= idx < len(methods) else "<unknown>"
            unknown_findings = [f for f in flist if f.verdict is Verdict.UNKNOWN]
            op_cluster_keys = {(f.reason, _site_key(f.plr_site), f.detail) for f in unknown_findings}
            sole = len(op_cluster_keys) == 1

            legacy_key = (row_id, op_id)
            occurrences = legacy_unknown_ops[legacy_key]
            if occurrences:
                log.debug(
                    "row_id collision: legacy key %r already seen at row_idx=%s -- also "
                    "row_idx=%d now (content-digest collision on an UNKNOWN op; NOT "
                    "merged -- see n_row_id_collisions/collision_ops in the report)",
                    legacy_key, [o["row_idx"] for o in occurrences], row_idx,
                )
            occurrences.append({
                "row_idx": row_idx,
                "record_id": row_id,
                "op_id": op_id,
                "method": method,
                "reason_set": sorted({f.reason for f in unknown_findings}),
                "findings": [
                    {"reason": f.reason, "plr_site": _site_key(f.plr_site), "detail": f.detail}
                    for f in unknown_findings
                ],
                "verdict": verdict.value,
            })

            for f in unknown_findings:
                n_findings_total += 1
                n_findings_by_reason[f.reason] += 1
                ckey = (f.reason, _site_key(f.plr_site), f.detail)
                acc = clusters.get(ckey)
                if acc is None:
                    acc = ClusterAccumulator(reason=f.reason, site=ckey[1], detail=f.detail)
                    clusters[ckey] = acc
                acc.add(row_idx, row_id, op_id, method)
                if sole:
                    acc.mark_sole_blocker(row_idx, op_id)
            reason_set_histogram[tuple(sorted({f.reason for f in unknown_findings}))] += 1

    # Every occurrence past the first, for a legacy key shared by >1
    # row_idx, is one op that the pre-fix set-keyed ops_blocked would have
    # silently folded into an earlier, unrelated op -- i.e. exactly the
    # "12 duplicate (row_id, op_id) ... row_id likely collided" warnings
    # the unfixed ledger logged on the frozen benchmark (#4976 round-1 C12).
    collision_ops = [
        occ
        for occurrences in legacy_unknown_ops.values()
        if len(occurrences) > 1
        for occ in occurrences[1:]
    ]
    collision_ops.sort(key=lambda o: (o["row_idx"], o["op_id"]))
    n_row_id_collisions = len(collision_ops)
    if n_row_id_collisions:
        log.info(
            "n_row_id_collisions=%d UNKNOWN-verdict op(s) shared a content-digest row_id "
            "with another row's op at the same op_id this run; positional keying keeps "
            "every one of them a distinct ops_blocked entry (see collision_ops)",
            n_row_id_collisions,
        )

    cluster_list = [c.to_dict() for c in clusters.values()]
    cluster_list.sort(key=lambda c: (-c["n_ops_blocked"], c["reason"], c["plr_site"], c["condition"]))

    histogram_list = [
        {"reason_set": list(rs), "n_ops": n}
        for rs, n in sorted(reason_set_histogram.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    consistency = _compute_consistency(cluster_list, histogram_list, n_ops_unknown)
    if not consistency["ok"]:
        for v in consistency["violations"]:
            log.error("ledger consistency violation: %s", v)

    return {
        "clusters": cluster_list,
        "per_op_reason_set_histogram": histogram_list,
        "n_ops_executed": n_ops_executed,
        "n_ops_unknown": n_ops_unknown,
        "n_findings_total": n_findings_total,
        "n_findings_by_reason": dict(sorted(n_findings_by_reason.items(), key=lambda kv: (-kv[1], kv[0]))),
        "n_clusters": len(cluster_list),
        "n_row_id_collisions": n_row_id_collisions,
        "collision_ops": collision_ops,
        "consistency": consistency,
    }


def _compute_consistency(
    cluster_list: list[dict[str, Any]],
    histogram_list: list[dict[str, Any]],
    n_ops_unknown: int,
) -> dict[str, Any]:
    """Cross-checks that must hold given clusters/histogram are built from
    the SAME per-op UNKNOWN-verdict population (band B0, #4976 round-1
    challenger C12): a violation means the clustering arithmetic itself has
    drifted, not just one benchmark run's numbers.

    Three invariants, each independent of the other two:

    1. ``sum(histogram.n_ops) == n_ops_unknown`` -- the histogram counts one
       entry per UNKNOWN op (keyed by reason SET, incremented directly in
       the per-op loop, never through a row_id-keyed set) and must total
       exactly the same population ``n_ops_unknown`` counts.
    2. For every reason ``r``: no single ``(reason, site, detail)`` cluster
       can claim more blocked ops than the number of UNKNOWN ops whose
       reason set contains ``r`` at all (derived from the histogram) --
       a cluster is a strict refinement of "ops carrying this reason", so
       its ``n_ops_blocked`` can never exceed that coarser population.
    3. Per cluster, ``sum(per_method.values()) == n_ops_blocked`` -- every
       ``ops_blocked`` member is counted in exactly one ``per_method`` slot
       (:meth:`ClusterAccumulator.add` increments ``per_method`` iff the op
       is new to ``ops_blocked``).
    """
    violations: list[str] = []

    sum_histogram_n_ops = sum(h["n_ops"] for h in histogram_list)
    n_ops_executed_unknown = n_ops_unknown  # same population, named separately per spec
    if not (sum_histogram_n_ops == n_ops_unknown == n_ops_executed_unknown):
        violations.append(
            f"sum(per_op_reason_set_histogram.n_ops)={sum_histogram_n_ops} != "
            f"n_ops_unknown={n_ops_unknown} (!= n_ops_executed_unknown={n_ops_executed_unknown})"
        )

    n_ops_with_reason: collections.Counter = collections.Counter()
    for h in histogram_list:
        for r in h["reason_set"]:
            n_ops_with_reason[r] += h["n_ops"]

    max_cluster_n_ops_blocked: dict[str, int] = {}
    for c in cluster_list:
        r = c["reason"]
        max_cluster_n_ops_blocked[r] = max(max_cluster_n_ops_blocked.get(r, 0), c["n_ops_blocked"])

    per_reason: dict[str, dict[str, int]] = {}
    for r, max_blocked in sorted(max_cluster_n_ops_blocked.items()):
        n_with_reason = n_ops_with_reason.get(r, 0)
        per_reason[r] = {
            "max_cluster_n_ops_blocked": max_blocked,
            "n_ops_with_reason": n_with_reason,
        }
        if max_blocked > n_with_reason:
            violations.append(
                f"reason={r!r}: max cluster n_ops_blocked={max_blocked} > "
                f"n_ops_with_reason (from histogram)={n_with_reason}"
            )

    for c in cluster_list:
        per_method_sum = sum(c["per_method"].values())
        if per_method_sum != c["n_ops_blocked"]:
            violations.append(
                f"cluster reason={c['reason']!r} site={c['plr_site']!r} "
                f"condition={c['condition']!r}: sum(per_method)={per_method_sum} != "
                f"n_ops_blocked={c['n_ops_blocked']}"
            )

    return {
        "ok": not violations,
        "violations": violations,
        "sum_histogram_n_ops": sum_histogram_n_ops,
        "n_ops_unknown": n_ops_unknown,
        "n_ops_executed_unknown": n_ops_executed_unknown,
        "per_reason": per_reason,
    }


_SETUP_GUARD_NOTE = (
    "liquid_handler.py:191 (`LiquidHandler.setup`'s own `if self.setup_finished: raise "
    "RuntimeError(...)` guard) NEVER appears in this ledger's clusters, and cannot, by "
    "construction of the current pipeline -- not because no such Finding is ever produced. "
    "derived_contracts.json's ONLY guard entry at that site belongs to the "
    "`LiquidHandler.setup` contract itself (confirmed by direct query: no other contract's "
    "`guards`/`channel_guards` list carries this site). `oracle_common.calls_from_plr_kwargs` "
    "(oracle_common.py:391-427) unconditionally prepends a `{\"method\": \"setup\", ...}` CALL "
    "as calls[0] for every row (the scaffolding's real `setup.machine.setup()` reset, "
    "training/verify/verifier.py:117-126); `check_ir` visits that CALL and evaluates its own "
    "`setup_finished` guard, producing a real Finding at the SETUP call's own pc. But "
    "`run_static_calls` (oracle_common.py:566,570) computes `setup_pcs` from "
    "`bc.sideband['origin']` and FILTERS every finding whose pre-relabel `operation_id` is a "
    "setup pc OUT of `raw_findings` *before* `_ir.relabel_findings` ever runs -- so a setup-pc "
    "finding is dropped before it could be relabelled onto any real `op_<i>`, and this "
    "ledger's own seam (installed immediately after that relabel, oracle_common.py's "
    "`FINDINGS_SINK` call site) never receives it. The planning-time probe's ':191 d1 setup' "
    "row (sprint plan §0, count 38) was produced by a DIFFERENT, ephemeral script "
    "($TMPDIR/probe/unknown_reason_probe.py) that wrapped `check_ir` directly rather than "
    "going through `run_static_calls`'s setup-pc exclusion + relabel; whatever attribution "
    "logic that probe used evidently mapped the setup CALL's own pc onto a real op id without "
    "replicating oracle_common's origin-shift (`lower_row_calls`, oracle_common.py:430-474). "
    "This ledger reuses `run_static_calls` unmodified and therefore cannot reproduce that "
    "artifact: if 38 setup-guard occurrences existed against real op ids in the properly-"
    "seamed pipeline, this ledger's clusters would show a `guard_predicate_unparsed` entry "
    "at `liquid_handler.py:191` with `n_ops_blocked` > 0 -- check this ledger's own clusters "
    "list for that site to confirm the count is exactly 0."
)


def build_ledger(
    *,
    corpus: list[str],
    sidecar: str | None,
    crosscheck: list[str],
    contracts: Path,
    limit: int | None,
    replay_report_path: Path,
) -> dict[str, Any]:
    collected: list[tuple[str, tuple[Any, ...]]] = []

    def _sink(row_id: str, findings: tuple[Any, ...]) -> None:
        collected.append((row_id, findings))

    argv = []
    for c in corpus:
        argv += ["--corpus", c]
    if sidecar:
        argv += ["--sidecar", sidecar]
    for cc in crosscheck:
        argv += ["--crosscheck", cc]
    argv += ["--contracts", str(contracts)]
    if limit is not None:
        argv += ["--limit", str(limit)]
    argv += ["--report", str(replay_report_path)]

    prior_sink = oc.FINDINGS_SINK
    oc.FINDINGS_SINK = _sink
    try:
        rc = oracle_replay.main(argv)
    finally:
        oc.FINDINGS_SINK = prior_sink

    replay_report = json.loads(replay_report_path.read_text())

    static_eligible_rows = [
        r for r in replay_report["rows"]
        if r.get("no_call_reason") is None and r.get("skip_reason") is None
    ]
    if len(static_eligible_rows) != len(collected):
        raise RuntimeError(
            f"positional correlation invariant broken: {len(static_eligible_rows)} rows "
            f"reached oracle_replay's Static section but the FINDINGS_SINK fired "
            f"{len(collected)} times -- oracle_replay.py's own row-processing order must "
            "have changed under this script; do not trust the per-op method attribution "
            "below without investigating."
        )

    row_methods = [r.get("calls", []) for r in static_eligible_rows]
    row_ids_from_report = [r.get("record_id", "") for r in static_eligible_rows]
    # Sanity cross-check (not a hard assertion -- record_id collisions are a
    # documented, expected 4%-ish rate, oracle_common.content_digest's own
    # docstring): the sink's own row_id should usually agree with the
    # report's row_id at the same position.
    mismatches = sum(
        1 for (sink_id, _f), rep_id in zip(collected, row_ids_from_report) if sink_id != rep_id
    )

    clustered = cluster_unknown_findings(collected, row_methods)

    n_ops_executed_baseline = replay_report["denominators"]["operations_executed"]
    n_rows_executed_baseline = replay_report["denominators"]["rows_executed"]
    unknown_rate_baseline = replay_report["summary_flat"]["unknown_rate"]
    unsound_baseline = replay_report["summary_flat"]["unsound"]

    notes = [
        _SETUP_GUARD_NOTE,
        (
            f"n_ops_executed (this ledger, distinct (row_id, op_id) pairs with >=1 real "
            f"Finding seen through the FINDINGS_SINK seam) = {clustered['n_ops_executed']} vs "
            f"oracle_replay.py's own operations_executed = {n_ops_executed_baseline}. A gap "
            "would mean some ops in an executed row's call_sequence never got a real Finding "
            "at all (e.g. a not-planned index after an earlier raise, given a synthetic "
            "'unknown'/0-findings placeholder by run_static_calls's own per_op dict comprehension "
            "rather than by check_ir) -- such ops carry no reason to cluster and are outside "
            "this ledger's UNKNOWN-root-cause scope by construction, not an omission."
        ),
        (
            f"rows_executed (positionally correlated against oracle_replay's own "
            f"no_call/skip-filtered rows) = {len(static_eligible_rows)} vs "
            f"oracle_replay.py's own denominators.rows_executed = {n_rows_executed_baseline}. "
            f"({len(static_eligible_rows) - n_rows_executed_baseline} of these are "
            "rows_setup_error rows -- oracle_replay excludes THOSE from rows_executed/"
            "operations_executed/unknown_rate but this ledger's sink still fires for them "
            "(run_row reaches the Static section before the setup-error check); they "
            "contribute zero findings/clusters here because none of their real ops are ever "
            "lowered (calls_from_plr_kwargs only lowers PLANNED calls), so they cannot pollute "
            "the clusters -- this note exists purely so the two row counts' difference is "
            "explained rather than left as an unexplained gap.)"
        ),
        (
            f"record_id sink/report positional cross-check: {mismatches} mismatch(es) out of "
            f"{len(collected)} rows (0 expected; content_digest collisions, when they occur, "
            "affect only method attribution for the tiny number of ops on a colliding row, "
            "never cluster membership -- clustering keys off (reason, plr_site, detail), never "
            "row_id)."
        ),
        (
            f"oracle_replay's own oracle exit code was {rc} (0 == unsound==0 and "
            f"check_graph_exceptions==0); unsound={unsound_baseline}, "
            f"unknown_rate={unknown_rate_baseline}."
        ),
        (
            f"band B0 fix (backlog #4976, round-1 challenger C12, 260905): "
            f"ClusterAccumulator.ops_blocked/sole_blocker_ops are now keyed by the "
            f"POSITIONAL (row_idx, op_id) pair, never by (row_id, op_id) -- row_id is a "
            f"content digest (mismatches note above) that collides across a documented "
            f"~4% of corpus rows, and deduping ops_blocked on that string silently merged "
            f"two DIFFERENT ops from two DIFFERENT rows into one entry whenever they "
            f"shared both a colliding row_id and an op_id. This run found "
            f"n_row_id_collisions={clustered['n_row_id_collisions']} such UNKNOWN-verdict "
            f"ops (full per-op reason/site list in collision_ops); the pre-fix ledger "
            f"undercounted n_ops_blocked by exactly this many ops on every cluster any of "
            f"them belonged to (observed 260904: the `:375 LiquidHandler._check_args` "
            f"cluster read 532 instead of 544, and the sole `unresolved_delegate` cluster "
            f"read 81 instead of 93 -- both off by exactly n_row_id_collisions)."
        ),
    ]

    header = {
        "task_id": "260904_sema-predicates",
        "backlog_id": 4976,
        "benchmark_name": BENCHMARK_NAME,
        "pin": _plr_pin(),
        "git_head": _git_head(),
        "contracts_path": str(contracts),
        "contracts_sha256": _sha256_file(contracts),
        "corpus_paths": corpus,
        "sidecar_path": sidecar,
        "crosscheck_paths": crosscheck,
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "oracle_replay_report_path": str(replay_report_path),
    }

    report = {
        "header": header,
        "baseline_comparison": {
            "n_ops_executed_this_ledger": clustered["n_ops_executed"],
            "n_ops_executed_baseline": n_ops_executed_baseline,
            "n_rows_executed_this_ledger": len(static_eligible_rows),
            "n_rows_executed_baseline": n_rows_executed_baseline,
            "unknown_rate_baseline": unknown_rate_baseline,
            "unsound_baseline": unsound_baseline,
        },
        "n_ops_executed": clustered["n_ops_executed"],
        "n_ops_unknown": clustered["n_ops_unknown"],
        "n_findings_total": clustered["n_findings_total"],
        "n_findings_by_reason": clustered["n_findings_by_reason"],
        "n_clusters": clustered["n_clusters"],
        "clusters": clustered["clusters"],
        "per_op_reason_set_histogram": clustered["per_op_reason_set_histogram"],
        "n_row_id_collisions": clustered["n_row_id_collisions"],
        "collision_ops": clustered["collision_ops"],
        "consistency": clustered["consistency"],
        "notes": notes,
    }
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", type=str, action="append", required=True,
                     help="corpus JSONL file (repeatable); pass-through to oracle_replay")
    ap.add_argument("--sidecar", type=str, default=None,
                     help="assemble sidecar JSONL; pass-through to oracle_replay")
    ap.add_argument("--crosscheck", type=str, action="append", default=[],
                     help="floor/overlay crosscheck file (repeatable); pass-through to oracle_replay")
    ap.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS,
                     help="contract table JSON")
    ap.add_argument("--limit", type=int, default=None,
                     help="smoke-test limit (rows to process), forwarded to oracle_replay")
    ap.add_argument("--report", type=Path, required=True,
                     help="ledger JSON output path")
    ap.add_argument("--replay-report", type=Path, default=None,
                     help="where to write oracle_replay's OWN report (default: "
                          "<report>.oracle_replay.json, alongside --report)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    replay_report_path = args.replay_report or args.report.with_name(
        args.report.stem + ".oracle_replay.json"
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    replay_report_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_ledger(
        corpus=args.corpus,
        sidecar=args.sidecar,
        crosscheck=args.crosscheck,
        contracts=args.contracts,
        limit=args.limit,
        replay_report_path=replay_report_path,
    )

    args.report.write_text(json.dumps(report, indent=2))
    log.info("Ledger written to %s", args.report)

    summary_flat = {
        "n_ops_executed": report["n_ops_executed"],
        "n_ops_unknown": report["n_ops_unknown"],
        "n_clusters": report["n_clusters"],
        "n_findings_total": report["n_findings_total"],
        "top_cluster_n_ops_blocked": report["clusters"][0]["n_ops_blocked"] if report["clusters"] else 0,
    }
    bth_path = os.environ.get("BTH_RESULTS_PATH")
    if bth_path:
        Path(bth_path).write_text(json.dumps(summary_flat))
        log.info("Bathos results written to %s", bth_path)

    log.info(
        "summary: n_ops_executed=%d n_ops_unknown=%d n_clusters=%d n_findings_total=%d "
        "top_cluster_n_ops_blocked=%d",
        summary_flat["n_ops_executed"], summary_flat["n_ops_unknown"],
        summary_flat["n_clusters"], summary_flat["n_findings_total"],
        summary_flat["top_cluster_n_ops_blocked"],
    )
    for cl in report["clusters"][:15]:
        log.info(
            "cluster: reason=%s site=%s n_findings=%d n_ops_blocked=%d n_ops_sole_blocker=%d detail=%r",
            cl["reason"], cl["plr_site"], cl["n_findings"], cl["n_ops_blocked"],
            cl["n_ops_sole_blocker"], cl["condition"][:80],
        )

    if report["n_row_id_collisions"]:
        log.info(
            "n_row_id_collisions=%d (see collision_ops in %s)",
            report["n_row_id_collisions"], args.report,
        )

    consistency = report["consistency"]
    if not consistency["ok"]:
        for v in consistency["violations"]:
            log.error("CONSISTENCY VIOLATION: %s", v)
        log.error(
            "ledger consistency check FAILED -- %d violation(s); report was still written "
            "to %s for inspection, but this run's numbers are NOT trustworthy",
            len(consistency["violations"]), args.report,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
