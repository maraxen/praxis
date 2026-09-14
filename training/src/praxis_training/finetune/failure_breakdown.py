"""Classify the exact-match failures in ``baseline_eval`` reports into
measurement artifacts versus genuine model errors.

Diagnostic ONLY. It never re-scores a report and never touches a promotion
verdict -- the P2.6 prereg (§3) fixes the scorer before training, so any
scoring change is a proposal for the user, not something this module applies::

    python -m praxis_training.finetune.failure_breakdown \
        --report baseline=training/eval/reports/260901_baseline_real_v2.json \
        --report A=training/eval/reports/260901_p26_arm_A.json ... \
        --out-json training/eval/reports/260901_p26_failure_breakdown.json

Categories (one per failed row; first match wins, top to bottom):

``no_call``            emitted zero calls where >=1 was intended (abstain/clarify)
``spurious_call``      emitted a call on an out-of-surface (zero-call) row
``unknown_verb``       every emitted call named an unknown/excluded tool
``name_mismatch``      wrong tool name
``list_escape_format`` params differ ONLY because a list-valued argument came
                       back as the FunctionGemma template's serialization
                       ``[<escape>a<escape>,<escape>b<escape>]``; the parser
                       (``fgml_parser``) has no nested-list decoding, so the
                       value is compared as one string.  MEASUREMENT ARTIFACT.
``slot_order_only``    params equal; the only disagreement is the ORDER of the
                       derived ``unresolved_slots`` tuple.  The template's
                       ``dictsort`` makes the model emit keys alphabetically,
                       ``check_intent_agreement`` compares tuples positionally.
                       MEASUREMENT ARTIFACT.
``gold_slot_annotation`` params equal, yet the gold record's own
                       ``unresolved_slots`` annotation disagrees with what
                       ``derive_call_gaps`` yields from those same params. No
                       model can ever pass such a row.  GOLD-SET DEFECT.
``gold_missing_required`` params equal, yet the gold record's
                       ``missing_required`` annotation disagrees with the
                       derivation (the assembler dropped golden gap fields,
                       260902 finding).  GOLD-SET DEFECT.
``param_content``      params genuinely differ in content
``other``              anything else (kept verbose in the JSON)

``ARTIFACT_CATEGORIES`` are the categories a scorer/gold fix can flip to a
hit without the model changing; ``breakdown_report`` lists their record_ids
so a re-score prediction can be registered row-by-row (``rescore_check``).
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from praxis_training.baseline_eval.metrics import _normalize

__all__ = ["ARTIFACT_CATEGORIES", "classify_reasons", "breakdown_report", "render_markdown", "main"]

ARTIFACT_CATEGORIES = ("list_escape_format", "slot_order_only", "gold_slot_annotation", "gold_missing_required")
ESC = "<escape>"

_PARAMS_RE = re.compile(r"^params mismatch: \d+: predicted (\{.*?\}) != intended (\{.*\})$")
_SLOT_RE = re.compile(r"^\d+: unresolved_slots derived \((.*)\) != intended \((.*)\)$")
_MISSING_RE = re.compile(r"^\d+: missing_required derived \((.*)\) != intended \((.*)\)$")
_DERIVED_SLOT_RE = re.compile(r"DerivedSlot\([^)]*\)")
_LIST_RE = re.compile(r"^\[(.*)\]$", re.DOTALL)


def _decode_escaped_list(value: Any) -> Any:
    """``'[<escape>a<escape>,<escape>b<escape>]'`` -> ``['a', 'b']``; other values unchanged."""
    if not isinstance(value, str):
        return value
    m = _LIST_RE.match(value.strip())
    if not m:
        return value
    inner = m.group(1)
    if not inner.strip():
        return []
    items: list[Any] = []
    for raw in _split_outside_escapes(inner):
        text = raw.strip()
        if text.startswith(ESC) and text.endswith(ESC) and len(text) >= 2 * len(ESC):
            text = text[len(ESC):-len(ESC)]
        items.append(text)
    return items


def _split_outside_escapes(text: str) -> list[str]:
    """Split on commas that are not inside an ``<escape>...<escape>`` span
    (the template lets a string value contain a literal comma)."""
    parts: list[str] = []
    buf: list[str] = []
    inside = False
    i = 0
    while i < len(text):
        if text.startswith(ESC, i):
            inside = not inside
            buf.append(ESC)
            i += len(ESC)
            continue
        ch = text[i]
        if ch == "," and not inside:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def _params_from_reason(reason: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    m = _PARAMS_RE.match(reason)
    if not m:
        return None
    try:
        return ast.literal_eval(m.group(1)), ast.literal_eval(m.group(2))
    except (ValueError, SyntaxError):
        return None


def classify_reasons(reasons: Sequence[str]) -> str:
    """Map one failed row's ``reasons`` tuple to a category (see module doc)."""
    rs = [str(r) for r in reasons]
    joined = "\n".join(rs)
    if any(r.startswith("sequence length 0 != intended") for r in rs):
        return "no_call"
    if any(re.match(r"^sequence length [1-9]\d* != intended 0$", r) for r in rs):
        return "spurious_call"
    if "emitted call(s) but all to unknown/excluded verbs" in joined:
        return "unknown_verb"
    if any(r.startswith("name mismatch") for r in rs):
        return "name_mismatch"
    params_lines = [p for p in (_params_from_reason(r) for r in rs) if p is not None]
    if params_lines:
        all_list_escape = True
        for predicted, intended in params_lines:
            decoded = {k: _decode_escaped_list(v) for k, v in predicted.items()}
            changed = any(decoded[k] != predicted[k] for k in predicted)
            if not changed or _normalize(decoded) != _normalize(intended):
                all_list_escape = False
                break
        return "list_escape_format" if all_list_escape else "param_content"
    slot_lines = [m for m in (_SLOT_RE.match(r) for r in rs) if m is not None]
    missing_lines = [m for m in (_MISSING_RE.match(r) for r in rs) if m is not None]
    if rs and len(slot_lines) + len(missing_lines) == len(rs):
        # No params-mismatch line => params equal => derived gaps come from the
        # SAME params the gold record carries. Any disagreement is therefore
        # positional (scorer) or an inconsistent gold annotation, never the model.
        if missing_lines:
            return "gold_missing_required"
        if all(
            Counter(_DERIVED_SLOT_RE.findall(m.group(1))) == Counter(_DERIVED_SLOT_RE.findall(m.group(2)))
            for m in slot_lines
        ):
            return "slot_order_only"
        return "gold_slot_annotation"
    return "other"


def breakdown_report(report: Mapping[str, Any]) -> dict[str, Any]:
    n = int(report["n_examples"])
    successes = int(report["exact_match_accuracy"]["successes"])
    failures = report.get("exact_match_failures", [])
    by_cat: Counter[str] = Counter()
    by_class_cat: dict[str, Counter[str]] = defaultdict(Counter)
    other_rows: list[dict[str, Any]] = []
    for row in failures:
        cat = classify_reasons(row.get("reasons", ()))
        by_cat[cat] += 1
        by_class_cat[row.get("class", "unlabeled")][cat] += 1
        if cat == "other":
            other_rows.append({"record_id": row.get("record_id"), "reasons": list(row.get("reasons", ()))})
    artifact_rows = sum(by_cat[c] for c in ARTIFACT_CATEGORIES)
    artifact_ids: dict[str, list[str]] = {c: [] for c in ARTIFACT_CATEGORIES}
    for row in failures:
        cat = classify_reasons(row.get("reasons", ()))
        if cat in artifact_ids:
            artifact_ids[cat].append(str(row.get("record_id")))
    return {
        "n_examples": n,
        "exact_match_successes": successes,
        "n_failures": len(failures),
        "by_category": dict(sorted(by_cat.items())),
        "by_class_and_category": {k: dict(sorted(v.items())) for k, v in sorted(by_class_cat.items())},
        "artifact_rows": artifact_rows,
        # Diagnostic ceiling if the two scorer artifacts were absent: every
        # artifact row is counted as a hit. NOT a re-score -- an upper bound.
        "artifact_adjusted_accuracy_ceiling": (successes + artifact_rows) / n if n else None,
        "artifact_record_ids": {c: sorted(v) for c, v in artifact_ids.items()},
        "other_rows": other_rows,
    }


def render_markdown(results: Mapping[str, Mapping[str, Any]]) -> str:
    cats = ["no_call", "spurious_call", "unknown_verb", "name_mismatch", "list_escape_format",
            "slot_order_only", "gold_slot_annotation", "gold_missing_required", "param_content", "other"]
    lines = ["| report | exact | " + " | ".join(cats) + " | artifact rows | ceiling if fixed |",
             "|---|---|" + "---|" * len(cats) + "---|---|"]
    for name, r in results.items():
        cells = [str(r["by_category"].get(c, 0)) for c in cats]
        lines.append(
            f"| {name} | {r['exact_match_successes']}/{r['n_examples']} | " + " | ".join(cells)
            + f" | {r['artifact_rows']} | {r['artifact_adjusted_accuracy_ceiling']:.3f} |"
        )
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m praxis_training.finetune.failure_breakdown")
    p.add_argument("--report", action="append", required=True, metavar="NAME=REPORT.json")
    p.add_argument("--out-json", type=Path, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    results: dict[str, Any] = {}
    for spec in args.report:
        name, _, path = spec.partition("=")
        if not path:
            raise SystemExit(f"--report expects NAME=path, got {spec!r}")
        results[name] = breakdown_report(json.loads(Path(path).read_text(encoding="utf-8")))
        results[name]["source"] = path
    md = render_markdown(results)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps({"artifact_categories": list(ARTIFACT_CATEGORIES),
                                             "reports": results}, indent=2) + "\n", encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
