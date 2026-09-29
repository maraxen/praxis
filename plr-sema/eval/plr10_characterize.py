"""PLR 1.0 characterisation, two arms over the frozen tier-1 benchmark (#5622).

Measurement instrument for backlog #5622 (task 260929_plr-1.0-migration). It is a
thin wrapper around :func:`oracle_replay.main` -- the row pipeline, the oracle
(:func:`oracle_common.compare`) and every counter are oracle_replay's own; nothing
is reimplemented here. Pre-registration: ``plr10_characterize.bth.toml`` (sidecar,
committed before any run). This script implements that sidecar exactly.

Two arms over the SAME corpus/sidecar/crosschecks/contracts:

``real``
    Exactly the shipped :func:`oracle_replay.main` run.

``all_safe`` (NEGATIVE CONTROL)
    Identical run, except every operation's STATIC verdict is forced to
    ``"safe"`` before :func:`oracle_common.compare` sees it. Any operation that
    raised at runtime is then counted unsound by oracle_replay's OWN ``unsound``
    predicate (``verdict == "safe" and outcome.startswith("raised")``). If that
    counter does not fire here, ``unsound == 0`` on the real arm is not evidence.

The seam is ``oracle_replay.run_static_calls`` (the name :func:`oracle_replay.run_row`
resolves at call time): it is the sole producer of the per-operation static
verdict dict ``st`` that ``compare`` consumes. The wrapper calls the original
(so FINDINGS_SINK, ``excludes_sites`` collection and every finding are
unchanged), then overwrites ``st[oid]["verdict"]`` only. ``scoped_verdict``,
``n_findings`` and ``reasons`` are left untouched. The patch is a context manager
that restores the original attribute in ``finally``; no module source is edited.

Outputs (``--out-dir``): ``real.oracle_replay.json``, ``all_safe.oracle_replay.json``
and ``result.json`` (exactly the sidecar's ``[result_schema]`` keys), also printed
to stdout as a single JSON object. ``result.json`` is written only when both arms
ran. Exit code is 0 whenever the run completed; the outcome is judged by the
sidecar, not by the exit code. ``oracle_replay``'s own RuntimeError invariants
propagate.

Input paths are resolved relative to the current working directory (as in
oracle_replay). A missing input path is an error here, whereas oracle_replay
would only log a warning and produce an empty report.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import importlib.util
import json
import logging
import os
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

_EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_EVAL_DIR))

if importlib.util.find_spec("verify") is None:
    # oracle_replay would silently re-exec ITSELF (not this script) under the
    # workspace venv on import; refuse instead of running a different program.
    raise SystemExit(
        "plr10_characterize: 'verify' is not importable; run under the project venv "
        "(e.g. `uv run --no-sync python plr-sema/eval/plr10_characterize.py ...`)"
    )

import oracle_replay  # noqa: E402

log = logging.getLogger("plr10_characterize")

#: The sidecar's ``[result_schema]``, verbatim (test_plr10_characterize.py checks
#: this against the TOML file so the two cannot drift).
RESULT_SCHEMA: dict[str, type] = {
    "control_fires": bool,
    "real_rows_executed": int,
    "real_rows_setup_error": int,
    "real_operations_executed": int,
    "real_unsound": int,
    "real_unsound_scoped": int,
    "real_totality_violations": int,
    "real_check_graph_exceptions": int,
    "real_n_operations_scope_verdict_safe": int,
    "real_unknown_rate": float,
    "real_crosscheck_agreement": float,
    "all_safe_unsound": int,
    "all_safe_operations_executed": int,
    "runtime_raised_ops_all_safe_arm": int,
}

REAL_REPORT_NAME = "real.oracle_replay.json"
ALL_SAFE_REPORT_NAME = "all_safe.oracle_replay.json"
RESULT_NAME = "result.json"


@contextlib.contextmanager
def all_safe_static_verdicts() -> Iterator[None]:
    """Force every operation's static verdict to ``"safe"`` inside the block.

    Patches ``oracle_replay.run_static_calls`` (see module docstring) and
    restores the original object in ``finally``, including on exception.
    """
    original = oracle_replay.run_static_calls

    @functools.wraps(original)
    def _forced_safe(*args: Any, **kwargs: Any) -> Any:
        per_op, not_planned = original(*args, **kwargs)
        for entry in per_op.values():
            entry["verdict"] = "safe"
        return per_op, not_planned

    oracle_replay.run_static_calls = _forced_safe
    try:
        yield
    finally:
        oracle_replay.run_static_calls = original


@contextlib.contextmanager
def _without_bth_results_path() -> Iterator[None]:
    """oracle_replay.main writes its own ``summary_flat`` to BTH_RESULTS_PATH; two
    arms would clobber each other and the final result. Unset it while arms run."""
    saved = os.environ.pop("BTH_RESULTS_PATH", None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ["BTH_RESULTS_PATH"] = saved


def run_arm(
    *,
    corpus: list[str],
    sidecar: str | None,
    crosscheck: list[str],
    contracts: Path,
    limit: int | None,
    report_path: Path,
    patch: Callable[[], contextlib.AbstractContextManager[None]] | None = None,
) -> dict[str, Any]:
    """One :func:`oracle_replay.main` run, returns its parsed report."""
    argv: list[str] = []
    for c in corpus:
        argv += ["--corpus", c]
    if sidecar:
        argv += ["--sidecar", sidecar]
    for cc in crosscheck:
        argv += ["--crosscheck", cc]
    argv += ["--contracts", str(contracts)]
    if limit is not None:
        argv += ["--limit", str(limit)]
    argv += ["--report", str(report_path)]

    with contextlib.ExitStack() as stack:
        stack.enter_context(_without_bth_results_path())
        # oracle_replay/PLR may print to stdout; stdout is reserved for result.json.
        stack.enter_context(contextlib.redirect_stdout(sys.stderr))
        if patch is not None:
            stack.enter_context(patch())
        rc = oracle_replay.main(argv)
    log.info("oracle_replay.main returned rc=%s (report %s)", rc, report_path)
    return json.loads(report_path.read_text(encoding="utf-8"))


def runtime_raised_ops(report: dict[str, Any]) -> int:
    """Executed operations whose runtime outcome raised, from the report's own
    ``agreement_matrix`` (runtime outcome x static verdict, analyzable rows only --
    the same population ``summary_flat.unsound`` is summed over)."""
    return sum(
        sum(int(n) for n in verdicts.values())
        for outcome, verdicts in report["agreement_matrix"].items()
        if outcome.startswith("raised")
    )


def build_result(real: dict[str, Any], all_safe: dict[str, Any]) -> dict[str, Any]:
    """The sidecar's ``[result_schema]`` dict, read off the two reports."""
    rs, asf = real["summary_flat"], all_safe["summary_flat"]
    raised = runtime_raised_ops(all_safe)
    all_safe_unsound = int(asf["unsound"])
    result = {
        "control_fires": bool(all_safe_unsound >= 1 and all_safe_unsound >= raised),
        "real_rows_executed": int(rs["rows_executed"]),
        "real_rows_setup_error": int(rs["rows_setup_error"]),
        "real_operations_executed": int(rs["operations_executed"]),
        "real_unsound": int(rs["unsound"]),
        "real_unsound_scoped": int(rs["unsound_scoped"]),
        "real_totality_violations": int(rs["totality_violations"]),
        "real_check_graph_exceptions": int(rs["check_graph_exceptions"]),
        "real_n_operations_scope_verdict_safe": int(rs["n_operations_scope_verdict_safe"]),
        "real_unknown_rate": float(rs["unknown_rate"]),
        "real_crosscheck_agreement": float(rs["crosscheck_agreement"]),
        "all_safe_unsound": all_safe_unsound,
        "all_safe_operations_executed": int(asf["operations_executed"]),
        "runtime_raised_ops_all_safe_arm": int(raised),
    }
    assert list(result) == list(RESULT_SCHEMA)
    return result


def _check_inputs(args: argparse.Namespace) -> None:
    paths = [*args.corpus, *args.crosscheck, str(args.contracts)]
    if args.sidecar:
        paths.append(args.sidecar)
    missing = [p for p in paths if not Path(p).is_file()]
    if missing:
        raise FileNotFoundError(
            f"input file(s) not found (paths are relative to cwd={Path.cwd()}): {missing}"
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", type=str, action="append", required=True,
                    help="corpus JSONL file (repeatable); pass-through to oracle_replay")
    ap.add_argument("--sidecar", type=str, default=None,
                    help="assemble sidecar JSONL; pass-through to oracle_replay")
    ap.add_argument("--crosscheck", type=str, action="append", default=[],
                    help="floor/overlay crosscheck file (repeatable); pass-through to oracle_replay")
    ap.add_argument("--contracts", type=Path, default=oracle_replay.DEFAULT_CONTRACTS,
                    help="contract table JSON (default: oracle_replay's own default)")
    ap.add_argument("--limit", type=int, default=None,
                    help="smoke-test row limit, forwarded to oracle_replay")
    ap.add_argument("--out-dir", type=Path, required=True,
                    help="directory for the per-arm reports and result.json")
    ap.add_argument("--arm", choices=("both", "real", "all_safe"), default="both",
                    help="which arm(s) to run (result.json needs both)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _check_inputs(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    common: dict[str, Any] = {
        "corpus": args.corpus,
        "sidecar": args.sidecar,
        "crosscheck": args.crosscheck,
        "contracts": args.contracts,
        "limit": args.limit,
    }
    real: dict[str, Any] | None = None
    all_safe: dict[str, Any] | None = None
    if args.arm in ("both", "real"):
        log.info("arm real: shipped oracle_replay run")
        real = run_arm(**common, report_path=args.out_dir / REAL_REPORT_NAME)
    if args.arm in ("both", "all_safe"):
        log.info("arm all_safe: negative control, every static verdict forced to safe")
        all_safe = run_arm(
            **common,
            report_path=args.out_dir / ALL_SAFE_REPORT_NAME,
            patch=all_safe_static_verdicts,
        )

    if real is None or all_safe is None:
        log.warning("single-arm run (--arm %s): no %s written", args.arm, RESULT_NAME)
        print(json.dumps({"arm": args.arm, "out_dir": str(args.out_dir)}))
        return 0

    # Same runtime on both arms: only the static verdict differs.
    for key in ("rows_executed", "rows_setup_error", "operations_executed"):
        if real["summary_flat"][key] != all_safe["summary_flat"][key]:
            log.warning("arms disagree on %s: real=%s all_safe=%s (runtime nondeterminism?)",
                        key, real["summary_flat"][key], all_safe["summary_flat"][key])

    result = build_result(real, all_safe)
    text = json.dumps(result)
    (args.out_dir / RESULT_NAME).write_text(json.dumps(result, indent=2), encoding="utf-8")
    log.info("result written to %s", args.out_dir / RESULT_NAME)
    bth_path = os.environ.get("BTH_RESULTS_PATH")
    if bth_path:
        Path(bth_path).write_text(text, encoding="utf-8")
        log.info("Bathos results written to %s", bth_path)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
