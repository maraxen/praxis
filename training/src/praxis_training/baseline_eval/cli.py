"""CLI: ``python -m praxis_training.baseline_eval`` (P2.1 deliverable 2).

Examples::

    # Recorded-artifact mode (mechanics proof / checkpoint re-scoring):
    python -m praxis_training.baseline_eval \
        --pairs training/golden/golden_pairs.jsonl \
        --sidecar training/golden/golden_intent_sidecar.jsonl \
        --recorded training/eval/fixtures/recorded_fixture_mechanics_proof.json \
        --split eval --out training/eval/reports/report.json

    # Live local inference (REQUIRES gated-repo access: HF_TOKEN + terms):
    python -m praxis_training.baseline_eval --pairs ... --sidecar ... \
        --model google/functiongemma-270m-it --device cpu --split eval
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import load_pair_set, run_local, run_recorded

DEFAULT_PAIRS = "training/golden/golden_pairs.jsonl"
DEFAULT_SIDECAR = "training/golden/golden_intent_sidecar.jsonl"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m praxis_training.baseline_eval",
        description="FunctionGemma baseline eval: exact-match accuracy, clarify "
                    "recall/precision with Wilson 95% intervals.",
    )
    p.add_argument("--pairs", default=DEFAULT_PAIRS, help=f"native JSONL (default {DEFAULT_PAIRS})")
    p.add_argument("--sidecar", default=DEFAULT_SIDECAR, help=f"intent sidecar JSONL (default {DEFAULT_SIDECAR})")
    p.add_argument("--split", choices=["train", "eval"], default=None,
                   help="restrict scoring to one metadata split (default: all rows)")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--recorded", type=Path,
                      help="recorded-outputs JSON file (clearly labeled in the report)")
    p.add_argument("--allow-partial", action="store_true",
                   help="recorded mode: score only the recorded/scope intersection "
                        "(hand-made mechanics fixtures); report labeled PARTIAL")
    mode.add_argument("--model", help="HF model id for live local inference")
    p.add_argument("--revision", default="main", help="HF revision pin (default main; pin a SHA!)")
    p.add_argument("--device", default="cpu", help="torch device (default cpu; 270M is fine on CPU)")
    p.add_argument("--dtype", default=None, help="torch dtype name e.g. float32/bfloat16")
    p.add_argument("--out", type=Path, default=None, help="write JSON report here")
    p.add_argument("--label", default=None,
                   help="model_label recorded in the report (e.g. 'p26 arm B sha256:...'); "
                        "in --recorded mode overrides the label stored in the artifact")
    p.add_argument("--dump-outputs", type=Path, default=None,
                   help="live mode: also write every raw generation as a recorded-outputs "
                        "artifact (re-scorable later with --recorded, no inference)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[4]
    pairs_path = Path(args.pairs)
    sidecar_path = Path(args.sidecar)
    if not pairs_path.is_absolute():
        pairs_path = repo_root / pairs_path
    if not sidecar_path.is_absolute():
        sidecar_path = repo_root / sidecar_path

    pair_set = load_pair_set(pairs_path, sidecar_path)

    if args.recorded is not None:
        recorded_path = args.recorded
        if not recorded_path.is_absolute():
            recorded_path = repo_root / recorded_path
        report = run_recorded(pair_set, recorded_path, out_path=args.out,
                              split=args.split, allow_partial=args.allow_partial,
                              model_label=args.label)
    else:
        try:
            dump = args.dump_outputs
            if dump is not None and not dump.is_absolute():
                dump = repo_root / dump
            report = run_local(
                pair_set, args.model, revision=args.revision, device=args.device,
                dtype=args.dtype, out_path=args.out, split=args.split,
                model_label=args.label, dump_outputs=dump,
            )
        except RuntimeError as exc:
            print(f"BLOCKED: {exc}", file=sys.stderr)
            return 3  # distinct exit code: action-needed blocker

    text = json.dumps(report, indent=2)
    if args.out is not None:
        out = args.out if args.out.is_absolute() else repo_root / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")

    em, cr, cp = report["exact_match_accuracy"], report["clarify_recall"], report["clarify_precision"]

    def fmt(stat: dict) -> str:
        val = "n/a" if stat["value"] is None else f"{stat['value']:.3f}"
        lo_hi = "n/a" if stat["wilson95"] is None else f"[{stat['wilson95'][0]:.3f}, {stat['wilson95'][1]:.3f}]"
        return f"{val} {lo_hi} (k={stat['successes']}, n={stat['n']})"

    print(f"== baseline eval == mode={report['mode']} n={report['n_examples']}")
    print(f"labeled_as: {report['labeled_as']}")
    print(f"base_revision: {report['base_revision']}")
    print(f"exact_match_accuracy : {fmt(em)}")
    print(f"clarify_recall       : {fmt(cr)}")
    print(f"clarify_precision    : {fmt(cp)}")
    if args.out is not None:
        print(f"report written: {args.out}")
    if args.recorded is None and args.dump_outputs is not None:
        print(f"generations dumped: {args.dump_outputs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
