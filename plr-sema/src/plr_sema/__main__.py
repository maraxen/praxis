"""`python -m plr_sema check <file.py>...` (spec 261002 §6).

Exit codes: 0 analyzed with no WILL_FAIL (UNKNOWN allowed); 1 at least one
WILL_FAIL; 2 not analyzed, unreadable input, or usage error. Several files:
the worst code wins. A not-analyzed file is never reported as safe.
"""

from __future__ import annotations

import argparse
import dataclasses
import enum
import json
import sys
from pathlib import Path

from plr_sema.analysis import Analyzed, NotAnalyzed, NotAnalyzedReason, analyze
from plr_sema.contracts import ContractsError, contracts_source, load_contracts
from plr_sema.verdict import Verdict

EXIT_OK, EXIT_WILL_FAIL, EXIT_NOT_ANALYZED = 0, 1, 2


def _jsonable(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        items = [_jsonable(v) for v in obj]
        return sorted(items, key=json.dumps) if isinstance(obj, (set, frozenset)) else items
    return obj


def _check_one(path: Path, function: str | None, contracts) -> tuple[int, dict, list[str]]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        detail = f"cannot read {path}: {exc}"
        return EXIT_NOT_ANALYZED, {"file": str(path), "function": function, "outcome": "not_analyzed",
                                   "reason": "unreadable_input", "detail": detail}, [f"{path}: unreadable_input {detail}"]
    out = analyze(source, function, contracts=contracts)
    if isinstance(out, NotAnalyzed):
        rec = {"file": str(path), "function": out.function_name, "outcome": "not_analyzed",
               "reason": out.reason.value, "detail": out.detail}
        return EXIT_NOT_ANALYZED, rec, [f"{path}: not analyzed: {out.reason.value}: {out.detail}"]
    assert isinstance(out, Analyzed)
    lines = []
    for f in out.report.findings:
        line = out.op_lines.get(f.operation_id, 0)
        why = f.category if f.verdict is Verdict.WILL_FAIL else f.reason
        lines.append(f"{path}:{line} {f.operation_id} {f.verdict.value} {why}")
    lines.append(f"{path}::{out.function_name} -> {out.report.verdict.value} ({len(out.report.findings)} findings)")
    rec = {"file": str(path), "function": out.function_name, "outcome": "analyzed",
           "verdict": out.report.verdict.value, "key": out.key.as_str(),
           "findings": _jsonable(list(out.report.findings))}
    code = EXIT_WILL_FAIL if out.report.verdict is Verdict.WILL_FAIL else EXIT_OK
    return code, rec, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m plr_sema")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="statically check PLR protocol files")
    check.add_argument("files", nargs="+", type=Path)
    check.add_argument("--function", help="function to analyze (default: the only top-level def)")
    check.add_argument("--json", action="store_true", help="machine-readable output")
    check.add_argument("--contracts", help="contract table (.json or .json.gz)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse exits 2 on usage errors already; normalize anything else
        return EXIT_NOT_ANALYZED if exc.code else EXIT_OK

    contracts = None
    contracts_error = None
    try:
        where = contracts_source(args.contracts)
        if where.path is None:
            contracts_error = f"no contract table configured (layer: {where.layer})"
        else:
            contracts = load_contracts(where.path)
    except ContractsError as exc:
        contracts_error = str(exc)

    worst, records, text = EXIT_OK, [], []
    for path in args.files:
        if contracts is None:
            code = EXIT_NOT_ANALYZED
            rec = {"file": str(path), "function": args.function, "outcome": "not_analyzed",
                   "reason": NotAnalyzedReason.CONTRACTS_UNAVAILABLE.value, "detail": contracts_error}
            lines = [f"{path}: not analyzed: {NotAnalyzedReason.CONTRACTS_UNAVAILABLE.value}: {contracts_error}"]
        else:
            try:
                code, rec, lines = _check_one(path, args.function, contracts)
            except Exception as exc:  # noqa: BLE001 -- exit 1 means WILL_FAIL; a crash must never share it
                print(f"{path}: internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
                code = EXIT_NOT_ANALYZED
                rec = {"file": str(path), "function": args.function, "outcome": "not_analyzed",
                       "reason": "internal_error", "detail": f"{type(exc).__name__}: {exc}"}
                lines = [f"{path}: not analyzed: internal_error: {type(exc).__name__}: {exc}"]
        worst = max(worst, code)
        records.append(rec)
        text.extend(lines)

    if args.json:
        print(json.dumps({"results": records, "exit_code": worst}, sort_keys=True))
    else:
        print("\n".join(text))
    return worst


if __name__ == "__main__":
    sys.exit(main())
