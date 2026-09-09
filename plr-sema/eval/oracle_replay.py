"""Oracle replay tier 1 (T16b): corpus evaluation with measurement fixes (#4879).

Run the PLR chatterbox simulator (ground truth) and plr-sema's static analyzer
in parallel against rows from corpus_p25.jsonl + golden_pairs.jsonl, with proper
measurement of: rows_total, rows_no_call (clarifications), rows_skipped
(unfixable via preconditions), rows_executed (actually ran), operations_executed.

Per-row output: {record_id, source_file, line, utterance, calls[], skip_reason,
no_call_reason, runtime {outcome, error, exc_class}, static verdicts, compare[],
intent_check_failures[], totality_ok, check_graph_raised}.

Summary: unsound count, agreement matrix (runtime × static), per-method unknown%,
exception ranking split by PLR vs harness category, precondition_state ranking,
crosscheck content-join results.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BOOTSTRAP_FLAG = "PLR_SEMA_ORACLE_BOOTSTRAPPED"


def _bootstrap_into_training_env() -> None:
    """Bathos 0.13.0a4's ``bth run`` executes ``[sys.executable, script, *args]``
    with bathos's OWN interpreter, which lacks ``verify``/``training``/
    ``coxswain``/``overlay_gen`` (row_to_verifier_inputs's lazy imports then
    fail per-row as spurious "parse_error" outcomes, not a script crash --
    see #4879 T16d run 260902, 393/900 rows misclassified this way under a
    bare ``bth run --script-path`` invocation). Same fix as
    scripts/experiments/p26_finetune.py (ebd6b76d): re-exec under the
    workspace venv, falling back to ``uv run --offline --no-sync``.
    ``os.execve`` preserves the environment so BTH_RESULTS_PATH/BTH_OUTPUT_DIR
    plumbing survives the hop.
    """
    if os.environ.get(_BOOTSTRAP_FLAG):
        sys.stderr.write(
            "oracle_replay: 'verify' still not importable after re-exec; "
            "run `uv sync` in the repo first\n"
        )
        raise SystemExit(3)
    env = dict(os.environ, **{_BOOTSTRAP_FLAG: "1"})
    venv_python = _REPO_ROOT / ".venv" / "bin" / "python"
    script_args = sys.argv[1:]
    if venv_python.is_file():
        argv = [str(venv_python), str(Path(__file__).resolve()), *script_args]
        os.execve(str(venv_python), argv, env)
    uv = shutil.which("uv")
    if uv is None:
        sys.stderr.write("oracle_replay: neither .venv/bin/python nor uv found\n")
        raise SystemExit(3)
    argv = [uv, "run", "--offline", "--no-sync", "python",
            str(Path(__file__).resolve()), *script_args]
    os.chdir(_REPO_ROOT)
    os.execve(uv, argv, env)


if importlib.util.find_spec("verify") is None:
    _bootstrap_into_training_env()

import argparse
import collections
import dataclasses
import json
import logging
import time
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))

import oracle_common as oc  # noqa: E402 -- module handle, needed to install/restore FINDINGS_SINK (#4979, T32)
from oracle_common import (
    DEFAULT_CONTRACTS,
    RuntimeOutcome,
    compare,
    content_digest,
    extract_first_call,
    param_names_from_contracts,
    row_to_verifier_inputs,
    run_runtime,
    run_static_calls,
)

log = logging.getLogger(__name__)

REPO_ROOT = _REPO_ROOT


def _classify_exception(exc_class: str | None) -> str:
    """Classify an exception into PLR vs harness category.

    PLR exceptions: NoTipError, HasTipError, TooLittleLiquidError,
    TooLittleVolumeError, BlowOutVolumeError, ValueError (from PLR).

    Harness/dispatcher exceptions: GroundingError, DispatchError, TypeError,
    AttributeError, etc.
    """
    if not exc_class:
        return "none"
    # PLR precondition-state exceptions
    if exc_class in ("NoTipError", "HasTipError", "TooLittleLiquidError",
                     "TooLittleVolumeError", "BlowOutVolumeError"):
        return "precondition_state"
    # Dispatcher grounding errors
    if exc_class == "GroundingError":
        return "ungroundable_reference"
    if exc_class == "DispatchError":
        return "unsupported_tool"
    # Other harness errors
    return "harness_error"


def _extract_utterance_and_call(row: dict[str, Any]) -> tuple[str, str]:
    """Extract utterance and first call name from a row.

    Handles corpus format (messages) and crosscheck formats (floor: utterance,
    overlay: instruction).
    """
    utterance = ""
    call_name = ""

    # Corpus format (messages)
    for msg in row.get("messages", []):
        if msg.get("role") == "user":
            utterance = msg.get("content", "")
        elif msg.get("role") == "assistant":
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                call_name = tool_calls[0].get("function", {}).get("name", "")
                break

    # Floor format (utterance + structured_calls)
    if not utterance and "structured_calls" in row:
        utterance = row.get("utterance", "")
        calls = row.get("structured_calls", [])
        if calls:
            call_name = calls[0].get("name", "")

    # Overlay format (instruction + call)
    if not utterance and "instruction" in row:
        utterance = row.get("instruction", "")
        call_info = row.get("call", {})
        if isinstance(call_info, dict):
            call_name = call_info.get("name", "")
        elif isinstance(call_info, str):
            call_name = call_info

    return utterance, call_name


def _site_key(plr_site: Any) -> str:
    """``"file:line:qualname"`` for a :class:`plr_sema.verdict.PlrSite`, or
    the literal string ``"<none>"`` for a Finding with no site -- same
    format as ``unknown_ledger.py``'s own ``_site_key`` (#4979, T32), kept
    as an independent copy rather than an import so this module's own
    report format never depends on that script's internals.
    """
    if plr_site is None:
        return "<none>"
    return f"{plr_site.file}:{plr_site.lineno}:{plr_site.qualname}"


@dataclasses.dataclass
class RowResult:
    """Result for one row."""

    record_id: str
    corpus_file: str
    row_index: int
    utterance: str
    call_names: list[str]  # names of all calls in call_sequence
    scaffold_prefix_count: int  # number of prefix calls added
    no_call_reason: str | None
    skip_reason: str | None
    n_operations_executed: int
    runtime_outcome: str  # "no_call", "skipped:<reason>", "ran_ok", "raised:<Class>", "not_reached", "setup_error"
    runtime_error: str | None
    runtime_exc_class: str | None
    static_verdicts: dict[str, str]  # op_i -> verdict string (only executed ops)
    n_findings: int  # total across all executed ops
    compare_rows: list[dict[str, Any]]  # only executed ops
    check_graph_raised: bool
    check_graph_exception: str | None
    intent_check_failures: list[dict[str, Any]]
    totality_ok: bool
    unsound_count: int
    plr_kwargs: dict[int, dict[str, Any]]  # PLR-named arguments by call index
    tool_params: dict[str, dict[str, Any]]  # tool parameter names by op_id
    #: 260902 (spec §11.10): call_sequence indices that were never planned
    #: (no PlanResult, hence no CALL lowered) -- adapt_graph's old
    #: tool-named fallback has no successor; these rows are counted here
    #: rather than silently getting a tool-named CALL.
    not_planned_indices: list[int] = dataclasses.field(default_factory=list)
    #: §12.4.3 (#4939): original ref strings row_to_verifier_inputs's
    #: loader-only well-ref normalisation rewrote for this row (e.g.
    #: ["tip_rack_3_F7"]); empty when nothing normalised. A row counts
    #: toward rows_normalised regardless of its no_call/skip/executed
    #: bucket -- the rewrite can happen before a LATER precondition-plan
    #: skip.
    normalized_refs: list[str] = dataclasses.field(default_factory=list)
    #: #4982 D1 (increment 4 §13.12.1's criterion (a) for #4923): elapsed
    #: seconds for the static-check path only (``run_static_calls``), and
    #: separately for the runtime simulator path (``run_runtime``). Zero on
    #: rows that never reach the corresponding call (no_call/skip/parse
    #: error/setup error). Additive fields -- no other RowResult field's
    #: meaning changes.
    check_elapsed_s: float = 0.0
    runtime_elapsed_s: float = 0.0
    #: #4979 (T32, spec 260904 §15.10): tier-(iii) guard sites
    #: (``guard.is_dynamic_raise``) visited anywhere in THIS row's lowered
    #: graph, threaded from ``run_static_calls``'s new ``excludes_sites``
    #: collector (one list per ROW, never per operation -- see that
    #: function's own docstring). Empty for every row before this field
    #: existed and for every row with zero tier-(iii) guards. Published as
    #: a pure annotation (``rows_excused_by_scope`` in the report) with NO
    #: gate effect: it never changes ``compare()``'s ``unsound`` computation,
    #: which stays exactly `oracle_common.py`'s unmodified predicate.
    excludes_sites: list[str] = dataclasses.field(default_factory=list)


def run_row(
    row: dict[str, Any],
    corpus_file: str,
    row_index: int,
    contracts_json: str,
    *,
    ambiguity_class: str | None = None,
    sidecar_record_id: str | None = None,
    provenance: str | None = None,
    observe_element_types: bool = False,
) -> RowResult:
    """Process one corpus row: runtime + static + compare.

    Catch exceptions and record them, don't crash the harness.

    ``observe_element_types`` (spec 260904 §15.4, O1, T30b): pass-through
    to :func:`oracle_common.run_static_calls`'s own default-off switch.
    ``False`` (the default) reproduces every pre-T30b caller's exact
    behaviour -- this row's ``rt.resource_types``/``rt.element_types`` are
    computed either way (``run_runtime`` always collects them, O1's cost
    there is unconditional) but are only ever THREADED into the static
    path when this flag is set.
    """
    # Parse row into verifier inputs
    try:
        call_sequence, intent_record, deck_layout, skip_reason, no_call_reason = row_to_verifier_inputs(
            row,
            source_file=Path(corpus_file).stem,
            line=row_index,
            ambiguity_class=ambiguity_class,
            sidecar_record_id=sidecar_record_id,
            provenance=provenance,
        )
    except Exception as e:
        log.warning("Failed to parse row %s:%d: %s", corpus_file, row_index, e)
        # #4939 follow-up (260903): content-digest record_id, best-effort
        # (row_to_verifier_inputs itself raised, so we can't reuse its
        # extraction; re-extract independently -- extract_first_call
        # tolerates a malformed row by returning ("", None)).
        _utt, _call = extract_first_call(row)
        return RowResult(
            record_id=f"{Path(corpus_file).stem}:{content_digest(_utt, _call)}",
            corpus_file=corpus_file,
            row_index=row_index,
            utterance="",
            call_names=[],
            scaffold_prefix_count=0,
            no_call_reason="parse_error",
            skip_reason=None,
            n_operations_executed=0,
            runtime_outcome="setup_error",
            runtime_error=f"parse:{e}",
            runtime_exc_class="ParseError",
            static_verdicts={},
            n_findings=0,
            compare_rows=[],
            check_graph_raised=False,
            check_graph_exception="parse error",
            intent_check_failures=[],
            totality_ok=True,
            unsound_count=0,
            plr_kwargs={},
            tool_params={},
        )

    record_id = intent_record.get("record_id", f"{corpus_file}:{row_index}")
    utterance = intent_record.get("utterance", "")
    call_names = [c["name"] for c in call_sequence]

    # If no_call_reason, skip execution
    if no_call_reason:
        return RowResult(
            record_id=record_id,
            corpus_file=corpus_file,
            row_index=row_index,
            utterance=utterance,
            call_names=call_names,
            scaffold_prefix_count=0,
            no_call_reason=no_call_reason,
            skip_reason=None,
            n_operations_executed=0,
            runtime_outcome="no_call",
            runtime_error=None,
            runtime_exc_class=None,
            static_verdicts={},
            n_findings=0,
            compare_rows=[],
            check_graph_raised=False,
            check_graph_exception=None,
            intent_check_failures=[],
            totality_ok=True,
            unsound_count=0,
            plr_kwargs={},
            tool_params={},
        )

    # If skipped, return skipped outcome
    if skip_reason:
        return RowResult(
            record_id=record_id,
            corpus_file=corpus_file,
            row_index=row_index,
            utterance=utterance,
            call_names=call_names,
            scaffold_prefix_count=0,
            no_call_reason=None,
            skip_reason=skip_reason,
            n_operations_executed=0,
            runtime_outcome=f"skipped:{skip_reason.split()[0]}",  # first word of reason
            runtime_error=None,
            runtime_exc_class=None,
            static_verdicts={},
            n_findings=0,
            compare_rows=[],
            check_graph_raised=False,
            check_graph_exception=None,
            intent_check_failures=[],
            totality_ok=True,
            unsound_count=0,
            plr_kwargs={},
            tool_params={},
            normalized_refs=intent_record.get("normalized_refs", []),
        )

    # Reconstruct example dict for spike functions
    example = {
        "call_sequence": call_sequence,
        "intent_record": intent_record,
        "deck_layout": deck_layout,
    }

    # Runtime
    _rt_start = time.perf_counter()
    try:
        rt = run_runtime(example)
    except Exception as e:
        log.warning("Runtime failed for %s: %s", record_id, e)
        rt = RuntimeOutcome(
            error=f"runtime_harness:{e}",
            exc_class="RuntimeError",
            failing_index=None,
            planned_indices=[],
            passed=False,
        )
    runtime_elapsed_s = time.perf_counter() - _rt_start

    # Map runtime outcome to string
    if rt.error is None:
        runtime_outcome = "ran_ok"
    elif rt.failing_index is None:
        runtime_outcome = "not_reached(setup_error)"
    else:
        runtime_outcome = f"raised:{rt.exc_class}"

    # Static (260902, spec §11: lower_calls + check_ir, not adapt_graph +
    # check_graph -- see oracle_common.py's module docstring).
    check_graph_raised = False
    check_graph_exception = None
    static_verdicts = {}
    n_findings = 0
    tool_params_dict = {}
    not_planned_indices: list[int] = []
    check_elapsed_s = 0.0
    #: #4979 (T32, spec 260904 §15.10): one collector per row, threaded to
    #: `run_static_calls`'s new `excludes_sites` kwarg. Populated with raw
    #: `PlrSite` objects during the call below; reduced to `_site_key`
    #: strings for `RowResult` right after, so this function's own return
    #: value stays JSON-friendly like every other field.
    row_excludes_sites: list[Any] = []
    _check_start = time.perf_counter()
    try:
        param_names = param_names_from_contracts(contracts_json)
        st, not_planned_indices = run_static_calls(
            example,
            rt.plr_kwargs,
            contracts_json,
            param_names=param_names,
            observe_element_types=observe_element_types,
            resource_types=rt.resource_types,
            element_types=rt.element_types,
            excludes_sites=row_excludes_sites,
        )
        static_verdicts = {oid: sdata["verdict"] for oid, sdata in st.items()}
        n_findings = sum(sdata["n_findings"] for sdata in st.values())
        # Capture PLR-named kwargs (IR value JSON) for per-row record --
        # §11.10: a not-planned index has no successor to adapt_graph's old
        # tool-named fallback, so it carries no entry here at all.
        for i, kwargs in rt.plr_kwargs.items():
            tool_params_dict[f"op_{i}"] = kwargs
    except Exception as e:
        log.warning("Static analysis failed for %s: %s", record_id, e)
        check_graph_raised = True
        check_graph_exception = f"{type(e).__name__}: {e}"
    finally:
        check_elapsed_s = time.perf_counter() - _check_start

    # Compare (only if both runtime and static succeeded)
    compare_rows = []
    unsound_count = 0
    if static_verdicts:
        try:
            compare_rows = compare(example, rt, st)
            unsound_count = sum(r["unsound"] for r in compare_rows)
        except Exception as e:
            log.warning("Compare failed for %s: %s", record_id, e)

    # Totality check
    totality_ok = len(call_sequence) == 0 or n_findings >= len(call_sequence)

    return RowResult(
        record_id=record_id,
        corpus_file=corpus_file,
        row_index=row_index,
        utterance=utterance,
        call_names=call_names,
        scaffold_prefix_count=len(call_sequence) - 1 if len(call_sequence) > 0 else 0,
        no_call_reason=None,
        skip_reason=None,
        n_operations_executed=len(call_sequence),
        runtime_outcome=runtime_outcome,
        runtime_error=rt.error,
        runtime_exc_class=rt.exc_class,
        static_verdicts=static_verdicts,
        n_findings=n_findings,
        compare_rows=compare_rows,
        check_graph_raised=check_graph_raised,
        check_graph_exception=check_graph_exception,
        intent_check_failures=[],
        totality_ok=totality_ok,
        unsound_count=unsound_count,
        plr_kwargs=rt.plr_kwargs,
        tool_params=tool_params_dict,
        not_planned_indices=not_planned_indices,
        normalized_refs=intent_record.get("normalized_refs", []),
        check_elapsed_s=check_elapsed_s,
        runtime_elapsed_s=runtime_elapsed_s,
        excludes_sites=sorted({_site_key(s) for s in row_excludes_sites}),
    )


def main(argv: list[str] | None = None) -> int:
    _wall_start = time.perf_counter()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", type=str, action="append", required=True,
                    help="corpus JSONL file (repeatable)")
    ap.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS,
                    help="contract table JSON")
    ap.add_argument("--crosscheck", type=str, action="append", default=[],
                    help="floor/overlay file for comparison (repeatable)")
    ap.add_argument("--sidecar", type=str, default=None,
                    help="assemble sidecar JSONL (record_id, ambiguity_class, provenance, "
                         "lineage); line-paired with the FIRST --corpus file whose line "
                         "count matches it exactly, else joined by content (utterance) "
                         "as a labelled fallback")
    ap.add_argument("--report", type=Path, required=True,
                    help="JSON report output")
    ap.add_argument("--limit", type=int, default=None,
                    help="smoke-test limit (rows to process)")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    # Load contracts
    contracts_json = args.contracts.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # T16d (#4879) + #4939 follow-up (260903): sidecar join. Primary path
    # is still LINE POSITION when corpus and sidecar are line-count-matched
    # (``exact_eligible``) -- corpus_p25.jsonl/corpus_p25_sidecar.jsonl are
    # written as COMPANION files by the same assembler pass, so line i of
    # one is always line i of the other REGARDLESS of what content either
    # side carries; this is not the same kind of "line number" fragility a
    # hardcoded line constant in a test fixture has (that constant assumes
    # a corpus LAYOUT that can silently shift out from under it on a later
    # regen -- verified 260903: 260902's 900-row corpus regrew to 1427 rows
    # via mid-file insertion, invalidating TestT16dSidecarGating's hardcoded
    # line numbers, see below -- while THIS join recomputes both sides
    # fresh, every run, so it was never stale). Content-digest join
    # (utterance + first tool call, :func:`content_digest`) is the fallback
    # for files that are NOT line-paired (golden_pairs.jsonl is a reordered
    # near-duplicate of corpus_p25's own golden slice) -- an upgrade over
    # the prior utterance-ONLY fallback, which could conflate two rows that
    # share an utterance but differ in tool call/params. Note: a pure
    # content-digest join over the WHOLE file (ignoring position) is
    # deliberately NOT used even when eligible -- 58/1427 corpus_p25.jsonl
    # rows (260903) share a content digest with >=1 other row, and a
    # position-blind digest-to-digest join would silently misassign one of
    # those duplicates' sidecar metadata (ambiguity_class, provenance) to
    # the WRONG row of the group; the line-paired join has no such failure
    # mode for files it actually applies to.
    # ------------------------------------------------------------------
    sidecar_rows: list[dict[str, Any]] = []
    sidecar_by_digest: dict[str, dict[str, Any]] = {}
    if args.sidecar:
        with open(args.sidecar) as f:
            for line in f:
                if not line.strip():
                    continue
                srow = json.loads(line)
                sidecar_rows.append(srow)
                utt = srow.get("utterance", "")
                raw_calls = srow.get("calls") or []
                call = (
                    {"name": raw_calls[0].get("name", ""), "params": raw_calls[0].get("params", {})}
                    if raw_calls
                    else None
                )
                digest = content_digest(utt, call)
                if digest not in sidecar_by_digest:
                    sidecar_by_digest[digest] = srow
        log.info("Loaded %d sidecar rows from %s", len(sidecar_rows), args.sidecar)

    def _sidecar_for(corpus_file: str, line_no: int, row: dict[str, Any], exact_eligible: bool) -> tuple[dict[str, Any] | None, str]:
        """(sidecar_row, join_method) for this corpus row, or (None, 'none')."""
        if not sidecar_rows:
            return None, "none"
        if exact_eligible and 1 <= line_no <= len(sidecar_rows):
            return sidecar_rows[line_no - 1], "line_exact"
        utterance, call = extract_first_call(row)
        srow = sidecar_by_digest.get(content_digest(utterance, call))
        if srow is not None:
            return srow, "content_fallback"
        return None, "unmatched"

    # Load crosscheck: exact join by record_id (floor.record_id / overlay.id)
    # is primary; (utterance, call_name) content join is kept ONLY as a
    # labelled fallback for rows with no sidecar join.
    floor_by_record_id: dict[str, dict[str, Any]] = {}
    overlay_by_id: dict[str, dict[str, Any]] = {}
    crosscheck_by_content: dict[tuple[str, str], dict[str, Any]] = {}
    for cc_file in args.crosscheck:
        try:
            with open(cc_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if "record_id" in row and "structured_calls" in row:
                        # floor format
                        floor_by_record_id.setdefault(row["record_id"], row)
                    elif "id" in row and "call" in row:
                        # overlay format
                        overlay_by_id.setdefault(row["id"], row)
                    utterance, call_name = _extract_utterance_and_call(row)
                    if utterance and call_name:
                        key = (utterance, call_name)
                        # Prefer earlier rows if duplicates exist
                        if key not in crosscheck_by_content:
                            crosscheck_by_content[key] = row
        except Exception as e:
            log.warning("Failed to load crosscheck file %s: %s", cc_file, e)
    log.info(
        "Loaded crosscheck: %d floor (by record_id), %d overlay (by id), %d by (utterance, call_name) fallback",
        len(floor_by_record_id), len(overlay_by_id), len(crosscheck_by_content),
    )

    # Process corpus files
    results: list[RowResult] = []
    n_rows_total = 0
    n_rows_no_call = 0
    n_rows_parse_error = 0
    n_rows_skipped = 0
    n_rows_executed = 0
    #: §12.4.3 (#4939): rows with >=1 well-ref rewritten by
    #: row_to_verifier_inputs's loader-only normalisation, counted
    #: regardless of which no_call/skip/executed bucket the row lands in
    #: (a rewritten row can still be skipped by a LATER precondition check).
    n_rows_normalised = 0
    sidecar_join_counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    # #4939 follow-up (260903): a row's OWN record_id is now a content
    # digest (stable across corpus reordering), decoupled from the
    # sidecar's own id scheme ("cov-...", "ovl-..."). The crosscheck EXACT
    # join below still needs THAT id (it's the floor/overlay join key), so
    # thread it through this side dict rather than overloading record_id.
    record_id_to_sidecar_id: dict[str, str] = {}

    _collected_findings: list[tuple[str, tuple[Any, ...]]] = []
    _prior_findings_sink = oc.FINDINGS_SINK

    def _t32_findings_sink(row_id: str, findings: tuple[Any, ...]) -> None:
        """#4979 (T32, spec 260904 §15.10): chain-compose with whatever
        FINDINGS_SINK was already installed (e.g. unknown_ledger.py's own,
        which calls THIS module's main() with its own sink active) rather
        than clobbering it -- a caller that wraps oracle_replay.main() in
        its own sink must keep seeing every row, unmodified."""
        _collected_findings.append((row_id, findings))
        if _prior_findings_sink is not None:
            _prior_findings_sink(row_id, findings)

    oc.FINDINGS_SINK = _t32_findings_sink
    try:
        for corpus_file in args.corpus:
            try:
                with open(corpus_file) as f:
                    corpus_file_lines = f.readlines()
                exact_eligible = len(sidecar_rows) > 0 and len(corpus_file_lines) == len(sidecar_rows)
                for line_no, line in enumerate(corpus_file_lines, 1):
                        if args.limit and n_rows_total >= args.limit:
                            break
                        if not line.strip():
                            continue
                        try:
                            row = json.loads(line)
                        except Exception as e:
                            log.warning("Failed to parse JSON at %s:%d: %s", corpus_file, line_no, e)
                            continue
                        srow, join_method = _sidecar_for(corpus_file, line_no, row, exact_eligible)
                        ambiguity_class = srow.get("ambiguity_class") if srow else None
                        sidecar_record_id = srow.get("record_id") if srow else None
                        provenance = srow.get("provenance") if srow else None
                        sidecar_join_counts[provenance or "no_sidecar"][join_method] += 1
                        result = run_row(
                            row, corpus_file, line_no, contracts_json,
                            ambiguity_class=ambiguity_class,
                            sidecar_record_id=sidecar_record_id,
                            provenance=provenance,
                            # #4979 (T32, spec 260904 §15.4/O1): oracle_common.
                            # run_static_calls's own docstring names THIS
                            # module as "the first REPLAY caller expected to"
                            # turn O1 on -- run_row's own default stays False
                            # for every other caller (tips_dirty_cost.py,
                            # tier2_extractor.py, test_t30_measure.py), so
                            # this is set explicitly here rather than by
                            # flipping run_row's own default.
                            observe_element_types=True,
                        )
                        results.append(result)
                        if sidecar_record_id:
                            record_id_to_sidecar_id[result.record_id] = sidecar_record_id
                        n_rows_total += 1
                        if result.normalized_refs:
                            n_rows_normalised += 1
                        if result.no_call_reason == "parse_error":
                            n_rows_parse_error += 1
                        elif result.no_call_reason:
                            n_rows_no_call += 1
                        elif result.skip_reason:
                            n_rows_skipped += 1
                        else:
                            n_rows_executed += 1
                        if n_rows_total % 100 == 0:
                            log.info("Processed %d rows (no_call=%d, parse_error=%d, skipped=%d, executed=%d)...",
                                     n_rows_total, n_rows_no_call, n_rows_parse_error, n_rows_skipped, n_rows_executed)
            except Exception as e:
                log.warning("Failed to process corpus file %s: %s", corpus_file, e)
    finally:
        oc.FINDINGS_SINK = _prior_findings_sink

    log.info("Sidecar join counts by provenance: %s", {k: dict(v) for k, v in sidecar_join_counts.items()})

    # parse_error rows: report what failed to parse (T16d step 2)
    parse_error_rows = [
        {"record_id": r.record_id, "source_file": r.corpus_file, "line": r.row_index, "error": r.runtime_error}
        for r in results if r.no_call_reason == "parse_error"
    ]
    if parse_error_rows:
        log.info("parse_error rows (%d): %s", len(parse_error_rows), parse_error_rows[:5])

    # Compute summary statistics (only on executed rows)
    executed_results = [r for r in results if not r.no_call_reason and not r.skip_reason]

    # #4939 follow-up (260903): a row whose runtime failed BEFORE op 0 was
    # ever planned -- every index in call_sequence is in not_planned_indices,
    # so plr_kwargs is {} and static analysis has literally nothing to
    # analyze (every op gets a contentless "unknown"/0-findings entry,
    # §11.10) -- is a SETUP failure, not an analyzable execution: it
    # contributes no real signal to totality/unsound/unknown_rate and
    # inflates all three if left in. Bucketed separately as
    # ``rows_setup_error``; excluded from every "analyzable" aggregate
    # below (totality, unsound, check_graph_exceptions, operations_executed,
    # unknown_rate, agreement_matrix, exception_ranking,
    # precondition_state_ranking). Crosscheck (ground-truth PASS/FAIL
    # agreement) is NOT static-analysis-derived, so setup_error rows stay
    # in it -- "did we and P2.5 agree this row fails" is still meaningful
    # signal even with zero static findings.
    def _is_setup_error(r: RowResult) -> bool:
        return bool(r.not_planned_indices) and len(r.not_planned_indices) == r.n_operations_executed

    setup_error_results = [r for r in executed_results if _is_setup_error(r)]
    analyzable_results = [r for r in executed_results if not _is_setup_error(r)]
    n_rows_setup_error = len(setup_error_results)
    n_rows_executed = len(analyzable_results)

    setup_error_error_counts: dict[str, int] = collections.Counter(
        r.runtime_error for r in setup_error_results if r.runtime_error
    )
    setup_error_top = [
        {"error": err, "count": count} for err, count in setup_error_error_counts.most_common(10)
    ]

    n_unsound = sum(r.unsound_count for r in analyzable_results)
    n_totality_violations = sum(1 for r in analyzable_results if not r.totality_ok)
    n_check_graph_exceptions = sum(1 for r in analyzable_results if r.check_graph_raised)
    n_operations_executed = sum(r.n_operations_executed for r in analyzable_results)

    # Agreement matrix: runtime outcome × static verdict (analyzable rows only)
    agreement_matrix = collections.defaultdict(lambda: collections.Counter())
    for r in analyzable_results:
        if not r.compare_rows:
            continue
        for comp in r.compare_rows:
            outcome = comp["runtime"]
            verdict = comp["static"]
            agreement_matrix[outcome][verdict] += 1

    # Unknown rate by method
    method_unknown_rate: dict[str, float] = {}
    method_counts: dict[str, int] = collections.defaultdict(int)
    method_unknown: dict[str, int] = collections.defaultdict(int)
    for r in analyzable_results:
        for comp in r.compare_rows:
            method = comp["method"]
            method_counts[method] += 1
            if comp["static"] == "unknown":
                method_unknown[method] += 1
    for method in method_counts:
        method_unknown_rate[method] = method_unknown[method] / method_counts[method] if method_counts[method] > 0 else 0.0

    # Exception ranking by category
    exc_counter: dict[str, int] = collections.Counter()
    exc_category_counter: dict[str, int] = collections.Counter()
    exc_methods: dict[str, set[str]] = collections.defaultdict(set)
    precondition_exceptions: dict[str, int] = collections.Counter()
    for r in analyzable_results:
        if r.runtime_exc_class:
            exc_counter[r.runtime_exc_class] += 1
            category = _classify_exception(r.runtime_exc_class)
            exc_category_counter[category] += 1
            for call_name in r.call_names:
                exc_methods[r.runtime_exc_class].add(call_name)
            if category == "precondition_state":
                precondition_exceptions[r.runtime_exc_class] += 1

    exception_ranking = [
        {"class": exc, "count": count, "raised_on_methods": sorted(exc_methods[exc])}
        for exc, count in exc_counter.most_common()
    ]
    precondition_ranking = [
        {"class": exc, "count": count}
        for exc, count in precondition_exceptions.most_common()
    ]

    # Category breakdown
    category_breakdown = dict(exc_category_counter)

    # Crosscheck: exact join by record_id (floor.record_id / overlay.id) is
    # primary; (utterance, first_call_name) content join is a LABELLED
    # fallback for rows with no sidecar-derived record_id (T16d, #4879).
    # #4939 follow-up (260903): the corpus row's OWN record_id is now a
    # content digest, decoupled from the sidecar's "cov-.../ovl-..." id
    # scheme (see record_id_to_sidecar_id above, populated from the SAME
    # content-digest sidecar join _sidecar_for now uses) -- floor/overlay's
    # id space is the sidecar's, not the corpus's, so this join goes
    # through that side table rather than r.record_id directly. Crosscheck
    # intentionally still iterates the FULL executed_results (including
    # setup_error rows, not just analyzable_results): ground-truth
    # pass/fail agreement is meaningful even when static analysis had
    # nothing to say about a row.
    crosscheck_result = {
        "joined": 0, "agree": 0, "disagree": 0,
        "joined_exact": 0, "joined_content_fallback": 0,
        "examples": [],
    }
    for r in executed_results:
        first_call = r.call_names[0] if r.call_names else ""
        if not first_call:
            continue
        cc_row = None
        join_method = None
        sidecar_id = record_id_to_sidecar_id.get(r.record_id)
        if sidecar_id:
            cc_row = floor_by_record_id.get(sidecar_id) or overlay_by_id.get(sidecar_id)
            if cc_row is not None:
                join_method = "exact"
        if cc_row is None:
            key = (r.utterance, first_call)
            cc_row = crosscheck_by_content.get(key)
            if cc_row is not None:
                join_method = "content_fallback"
        if cc_row is None:
            continue
        crosscheck_result["joined"] += 1
        crosscheck_result["joined_exact" if join_method == "exact" else "joined_content_fallback"] += 1
        cc_passed = cc_row.get("execution_verify", {}).get("passed")
        our_passed = r.runtime_outcome == "ran_ok"
        if cc_passed == our_passed:
            crosscheck_result["agree"] += 1
        else:
            crosscheck_result["disagree"] += 1
            if len(crosscheck_result["examples"]) < 10:
                cc_error = cc_row.get("execution_verify", {}).get("error")
                crosscheck_result["examples"].append({
                    "record_id": r.record_id,
                    "join_method": join_method,
                    "utterance": r.utterance[:60],
                    "call": first_call,
                    "our_outcome": r.runtime_outcome,
                    "our_error": r.runtime_error,
                    "recorded_outcome": "passed" if cc_passed else "failed",
                    "recorded_error": cc_error[:100] if cc_error else None,
                    "is_plate_tracker_error": "'Plate' object has no attribute 'tracker'" in (r.runtime_error or ""),
                })

    # Compute global unknown_rate
    total_unknown_ops = sum(
        sum(1 for comp in r.compare_rows if comp["static"] == "unknown")
        for r in analyzable_results
    )
    global_unknown_rate = total_unknown_ops / n_operations_executed if n_operations_executed > 0 else 0.0

    # #4979 (T32, spec 260904 §15.10): n_findings_decided (SAFE/WILL_FAIL
    # findings) and n_findings_by_reason (UNKNOWN findings' own reason),
    # computed over every Finding this run's FINDINGS_SINK saw -- the same
    # population unknown_ledger.py's own sink sees when IT wraps this
    # module's main() (every row that reaches run_row's Static section; a
    # rows_setup_error row reaches that section too but its plr_kwargs is
    # {} so it contributes no real per-op Finding there either, per
    # unknown_ledger.py's own note on this exact point -- see its
    # "rows_executed (positionally correlated...)" note).
    n_findings_decided_total = 0
    n_findings_decided_by_site: collections.Counter = collections.Counter()
    n_findings_by_reason: collections.Counter = collections.Counter()
    for _row_id, _findings in _collected_findings:
        for f in _findings:
            if f.verdict.value in ("safe", "will_fail"):
                n_findings_decided_total += 1
                n_findings_decided_by_site[_site_key(f.plr_site)] += 1
            elif f.verdict.value == "unknown" and f.reason:
                n_findings_by_reason[f.reason] += 1

    # #4979 (T32, spec 260904 §15.9 block (4)/AC-15.5(iii)): whether the
    # evaluator's own per-guard result type exposes a shortcircuit flag at
    # all. `plr_sema.check.predicate.GuardResult` has exactly three fields
    # -- `verdict`, `reason`, `tier_iii` (re-verified this pass) -- and no
    # `decided_via_shortcircuit`, so this is published `null` rather than
    # guessed at 0, per the deliverable's own instruction for exactly this
    # case. Computing the real count would require an analyzer change
    # (a fourth `GuardResult` field), which is out of scope for a
    # measurement-only task.
    n_decided_via_env_ref_shortcircuit = None

    # #4979 (T32, spec 260904 §15.10): rows_excused_by_scope, a PURE
    # ANNOTATION with NO gate effect -- never read by `compare()`'s own
    # unsound computation, which stays byte-identical to
    # `oracle_common.compare` (unmodified predicate, no `exc_class`
    # reference anywhere in this comparison path). A row counts iff (a) the
    # runtime raised at some op i, (b) the static verdict AT op i is
    # "safe" (i.e. `compare()` would score this row unsound), and (c) the
    # ROW's own `excludes_sites` (>=1 tier-(iii) guard visited ANYWHERE in
    # this row's call sequence -- `excludes_sites` is a one-list-per-row
    # fact, never per-operation, exactly like `AnalysisReport.scope`,
    # `oracle_common.run_static_calls`'s own docstring) is non-empty.
    rows_excused_by_scope_examples: list[dict[str, Any]] = []
    n_rows_excused_by_scope = 0
    for r in analyzable_results:
        if not r.excludes_sites:
            continue
        raised_comp = next((c for c in r.compare_rows if c["runtime"].startswith("raised:")), None)
        if raised_comp is not None and raised_comp["static"] == "safe":
            n_rows_excused_by_scope += 1
            if len(rows_excused_by_scope_examples) < 20:
                rows_excused_by_scope_examples.append({
                    "record_id": r.record_id,
                    "op_index": raised_comp["index"],
                    "method": raised_comp["method"],
                    "runtime": raised_comp["runtime"],
                    "excludes_sites": r.excludes_sites,
                })

    # #4979 (T32, spec 260904 §15.9 block (4)): per-method residual reason
    # sets, in the SAME "decidable+reason1+reason2" string-key shape
    # `plr-sema/eval/t30_measure.py`'s own `block4_per_op_with_o1.by_method`
    # publishes -- so a reader (or a follow-up script) can diff the two
    # JSON files directly without reshaping either one. "decidable" is
    # t30_measure's own pseudo-member (not a REASON_VOCABULARY member,
    # never a real `Finding.reason`): prepended here under the identical
    # rule -- >=1 finding on the op has verdict SAFE or WILL_FAIL -- so the
    # two files' keys compare like-for-like. Built from the SAME
    # `_collected_findings` positional correlation `unknown_ledger.py`
    # itself relies on (one FINDINGS_SINK call per row that reaches the
    # Static section, in `executed_results` order), restricted to
    # `analyzable_results` (excludes rows_setup_error, matching every other
    # per-op aggregate in this report).
    _analyzable_ids = {id(r) for r in analyzable_results}
    residual_reason_sets_by_method: dict[str, dict[str, Any]] = {}
    if len(executed_results) == len(_collected_findings):
        for _row, (_sink_row_id, _row_findings) in zip(executed_results, _collected_findings):
            if id(_row) not in _analyzable_ids:
                continue
            _by_op: dict[str, list[Any]] = collections.defaultdict(list)
            for f in _row_findings:
                _by_op[f.operation_id].append(f)
            for _op_id, _flist in _by_op.items():
                try:
                    _idx = int(_op_id.split("_", 1)[1])
                except (IndexError, ValueError):
                    continue
                _method = _row.call_names[_idx] if 0 <= _idx < len(_row.call_names) else "<unknown>"
                _decided = any(f.verdict.value in ("safe", "will_fail") for f in _flist)
                _unknown_reasons = sorted({f.reason for f in _flist if f.verdict.value == "unknown" and f.reason})
                _key_parts = (["decidable"] if _decided else []) + _unknown_reasons
                _key = "+".join(_key_parts) if _key_parts else "<none>"
                _entry = residual_reason_sets_by_method.setdefault(
                    _method, {"n_ops": 0, "residual_reason_sets": collections.Counter()}
                )
                _entry["n_ops"] += 1
                _entry["residual_reason_sets"][_key] += 1
    else:
        log.warning(
            "residual_reason_sets_by_method SKIPPED: positional correlation invariant broken "
            "(%d executed_results vs %d FINDINGS_SINK calls) -- do not trust a diff against "
            "t30_measure.py's block4 without investigating",
            len(executed_results), len(_collected_findings),
        )
    for _m, _e in residual_reason_sets_by_method.items():
        _e["residual_reason_sets"] = dict(
            sorted(_e["residual_reason_sets"].items(), key=lambda kv: (-kv[1], kv[0]))
        )

    # Crosscheck agreement rate
    cc_joined = crosscheck_result["joined"]
    cc_agreement_rate = (
        crosscheck_result["agree"] / cc_joined if cc_joined > 0 else 0.0
    )

    # #4982 D1 (increment 4 §13.12.1's criterion (a) for #4923): timing.
    # check_only_elapsed_s sums RowResult.check_elapsed_s over ALL rows in
    # `results` -- only rows that reached the static-check branch of
    # run_row (no_call_reason and skip_reason both None, i.e. the union of
    # analyzable_results and setup_error_results) carry a nonzero value, so
    # this is exactly the check-only cost actually spent, whether or not
    # the row was later excluded from the analyzable aggregates above.
    # runtime_elapsed_s is the same sum for the simulator path.
    # wall_elapsed_s is main()'s own elapsed time (arg parsing through the
    # point the report is assembled, i.e. everything except writing it).
    check_only_elapsed_s = sum(r.check_elapsed_s for r in results)
    runtime_elapsed_s_total = sum(r.runtime_elapsed_s for r in results)
    wall_elapsed_s = time.perf_counter() - _wall_start

    # Flat summary for bathos/BTH_RESULTS_PATH (key names match the
    # validated sidecar's result_schema; do not rename rows_total/
    # operations_executed -- oracle_replay.bth.toml's summary_flat mapping
    # is already validated against these exact names, see #4879 header).
    summary_flat = {
        "rows_total": n_rows_total,
        "rows_no_call": n_rows_no_call,
        "rows_parse_error": n_rows_parse_error,
        "rows_normalised": n_rows_normalised,
        "rows_skipped": n_rows_skipped,
        "rows_setup_error": n_rows_setup_error,
        "rows_executed": n_rows_executed,
        "operations_executed": n_operations_executed,
        "unsound": n_unsound,
        "check_graph_exceptions": n_check_graph_exceptions,
        "totality_violations": n_totality_violations,
        "unknown_rate": global_unknown_rate,
        "crosscheck_joined": cc_joined,
        "crosscheck_joined_exact": crosscheck_result["joined_exact"],
        "crosscheck_joined_content_fallback": crosscheck_result["joined_content_fallback"],
        "crosscheck_agreement": cc_agreement_rate,
        "check_only_elapsed_s": check_only_elapsed_s,
        "n_findings_decided": n_findings_decided_total,
        "rows_excused_by_scope": n_rows_excused_by_scope,
    }

    # Build report
    report = {
        "summary_flat": summary_flat,
        "check_only_elapsed_s": check_only_elapsed_s,
        "runtime_elapsed_s": runtime_elapsed_s_total,
        "wall_elapsed_s": wall_elapsed_s,
        "denominators": {
            "rows_total": n_rows_total,
            "rows_no_call": n_rows_no_call,
            "rows_parse_error": n_rows_parse_error,
            "rows_normalised": n_rows_normalised,
            "rows_skipped": n_rows_skipped,
            "rows_setup_error": n_rows_setup_error,
            "rows_executed": n_rows_executed,
            "operations_executed": n_operations_executed,
        },
        "summary": {
            "rows_processed": n_rows_total,
            "rows_no_call": n_rows_no_call,
            "rows_parse_error": n_rows_parse_error,
            "rows_skipped": n_rows_skipped,
            "rows_setup_error": n_rows_setup_error,
            "rows_executed": n_rows_executed,
            "total_operations_executed": n_operations_executed,
            "unsound_count": n_unsound,
            "totality_violations": n_totality_violations,
            "check_graph_exceptions": n_check_graph_exceptions,
        },
        "sidecar_join_counts": {k: dict(v) for k, v in sidecar_join_counts.items()},
        "setup_error_top": setup_error_top,
        "parse_error_rows": parse_error_rows,
        "agreement_matrix": {
            outcome: dict(verdicts)
            for outcome, verdicts in agreement_matrix.items()
        },
        "unknown_rate_by_method": method_unknown_rate,
        "exception_category_breakdown": category_breakdown,
        "exception_ranking": exception_ranking,
        "precondition_state_ranking": precondition_ranking,
        "crosscheck": crosscheck_result,
        # #4979 (T32, spec 260904 §15.10/§15.11 AC-15.8): findings whose
        # emitted verdict is SAFE or WILL_FAIL, per PLR site -- the gated
        # number (floor >= 223, AC-15.8), broken down by site rather than
        # published as a bare total only.
        "n_findings_decided": n_findings_decided_total,
        "n_findings_decided_by_site": dict(
            sorted(n_findings_decided_by_site.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        # #4979 (T32, spec 260904 §15.9 block (1)/AC-15.8): UNKNOWN
        # findings' own reason, published separately from
        # n_findings_decided and explicitly excluded from "converted"
        # (guard_env_dependent/guard_operand_unknown counts included here
        # for completeness, not folded into n_findings_decided).
        "n_findings_by_reason": dict(
            sorted(n_findings_by_reason.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
        # #4979 (T32, spec 260904 §15.9 block (4)): null -- GuardResult
        # exposes no `decided_via_shortcircuit` field this increment; see
        # this variable's own assignment above for the full explanation.
        "n_decided_via_env_ref_shortcircuit": n_decided_via_env_ref_shortcircuit,
        # #4979 (T32, spec 260904 §15.10): pure annotation, no gate effect
        # -- see this block's own assignment above.
        "rows_excused_by_scope": {
            "count": n_rows_excused_by_scope,
            "examples": rows_excused_by_scope_examples,
        },
        # #4979 (T32, spec 260904 §15.9 block (4)/static-vs-evaluator
        # agreement): same shape as t30_measure.py's own
        # block4_per_op_with_o1.by_method, for direct comparison.
        "residual_reason_sets_by_method": residual_reason_sets_by_method,
        "rows": [
            {
                "record_id": r.record_id,
                "source_file": r.corpus_file,
                "line": r.row_index,
                "utterance": r.utterance,
                "calls": r.call_names,
                "scaffold_prefix_count": r.scaffold_prefix_count,
                "no_call_reason": r.no_call_reason,
                "skip_reason": r.skip_reason,
                "normalized_refs": r.normalized_refs,
                "runtime": {
                    "outcome": r.runtime_outcome,
                    "error": r.runtime_error,
                    "exc_class": r.runtime_exc_class,
                },
                "static": r.static_verdicts,
                "tool_params": r.tool_params,
                "plr_kwargs": r.plr_kwargs,
                "not_planned_indices": r.not_planned_indices,
                "compare": r.compare_rows,
                "intent_check_failures": r.intent_check_failures,
                "totality_ok": r.totality_ok,
                "check_graph_raised": r.check_graph_raised,
                "check_graph_exception": r.check_graph_exception,
                "unsound": r.unsound_count,
                "excludes_sites": r.excludes_sites,
            }
            for r in results
        ],
    }

    # Write report
    args.report.write_text(json.dumps(report, indent=2))
    log.info("Report written to %s", args.report)

    # Write BTH_RESULTS_PATH if set
    bth_path = os.environ.get("BTH_RESULTS_PATH")
    if bth_path:
        Path(bth_path).write_text(json.dumps(summary_flat))
        log.info("Bathos results written to %s", bth_path)

    # Log summary
    log.info(
        "summary: rows_total=%d no_call=%d parse_error=%d normalised=%d skipped=%d setup_error=%d executed=%d ops=%d unsound=%d check_graph_exc=%d totality_vio=%d unknown_rate=%.3f crosscheck_joined=%d (exact=%d fallback=%d) agree=%.3f check_only_elapsed_s=%.3f runtime_elapsed_s=%.3f wall_elapsed_s=%.3f n_findings_decided=%d rows_excused_by_scope=%d",
        n_rows_total,
        n_rows_no_call,
        n_rows_parse_error,
        n_rows_normalised,
        n_rows_skipped,
        n_rows_setup_error,
        n_rows_executed,
        n_operations_executed,
        n_unsound,
        n_check_graph_exceptions,
        n_totality_violations,
        global_unknown_rate,
        cc_joined,
        crosscheck_result["joined_exact"],
        crosscheck_result["joined_content_fallback"],
        cc_agreement_rate,
        check_only_elapsed_s,
        runtime_elapsed_s_total,
        wall_elapsed_s,
        n_findings_decided_total,
        n_rows_excused_by_scope,
    )

    return 1 if n_unsound > 0 or n_check_graph_exceptions > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
