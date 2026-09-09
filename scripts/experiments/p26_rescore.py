"""P2.6 re-score: apply the CURRENT scorer to a saved generations dump and
check the pre-registered row-level prediction (task 260902_p26_rescore,
backlog 4861, amendment .praxia/docs/preregistration/260902_p26-rescore-amendment.md).

No inference happens here. The dump (``praxis-recorded-model-outputs``,
written by ``baseline_eval --dump-outputs``) fixes the model's strings; the
only thing that varies between the OLD report and the NEW one is the scorer
(parser list decoding, order-insensitive slot comparison) and the gold
sidecar's re-derived gap fields. ``rescore_check.check_prediction`` then
verifies: no hit->miss flip, every miss->hit flip inside the breakdown's
artifact set, clarify metrics identical, n unchanged.

Tracked run (per model; CPU, seconds)::

    bth run --script-path scripts/experiments/p26_rescore.py \
        --output-paths training/eval/reports/260902_p26_rescore_A.json --tags model:A -- \
        --model A --dump training/eval/outputs/260902_p26_dump_A.json \
        --old-report training/eval/reports/260902_p26_dumpscore_old_A.json \
        --prediction training/eval/reports/260902_p26_rescore_prediction.json \
        --out training/eval/reports/260902_p26_rescore_A.json

Writes the new report to ``--out``, the check to ``<out stem>.check.json``,
and the flat result dict (sidecar ``result_schema``) to ``--results-out``
and ``$BTH_RESULTS_PATH``.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BOOTSTRAP_FLAG = "PRAXIS_P26_BOOTSTRAPPED"


def _bootstrap_into_training_env() -> None:
    """Re-exec under an interpreter that has the training package installed."""
    if os.environ.get(_BOOTSTRAP_FLAG):
        sys.stderr.write(
            "p26_rescore: praxis_training still not importable after re-exec; "
            "run `uv sync --package training --extra train` in the repo first\n"
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
        sys.stderr.write("p26_rescore: neither .venv/bin/python nor uv found\n")
        raise SystemExit(3)
    argv = [uv, "run", "--offline", "--no-sync", "--package", "training", "python",
            str(Path(__file__).resolve()), *script_args]
    os.chdir(_REPO_ROOT)
    os.execve(uv, argv, env)


try:
    import praxis_training  # noqa: F401
except ModuleNotFoundError:
    _bootstrap_into_training_env()

import argparse
import json

from praxis_training.baseline_eval.runner import load_pair_set, run_recorded
from praxis_training.finetune.rescore_check import check_prediction
from praxis_training.finetune.versions import CORPUS_REL, SIDECAR_REL


def _abs(p: Path) -> Path:
    return p if p.is_absolute() else _REPO_ROOT / p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="p26_rescore.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", required=True, help="key into the prediction JSON's 'models' (baseline/A/B/C)")
    ap.add_argument("--dump", type=Path, required=True, help="recorded-outputs artifact from --dump-outputs")
    ap.add_argument("--old-report", type=Path, required=True, help="OLD-scorer report over the same dump")
    ap.add_argument("--prediction", type=Path, required=True, help="pre-registered prediction JSON")
    ap.add_argument("--out", type=Path, required=True, help="NEW-scorer report path")
    ap.add_argument("--pairs", type=Path, default=Path(CORPUS_REL))
    ap.add_argument("--sidecar", type=Path, default=Path(SIDECAR_REL))
    ap.add_argument("--split", default="eval")
    ap.add_argument("--results-out", type=Path, default=None, help="flat result dict (default <out stem>.result.json)")
    args = ap.parse_args(argv)

    pair_set = load_pair_set(_abs(args.pairs), _abs(args.sidecar))
    report = run_recorded(pair_set, _abs(args.dump), split=args.split)
    out = _abs(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    old = json.loads(_abs(args.old_report).read_text(encoding="utf-8"))
    prediction = json.loads(_abs(args.prediction).read_text(encoding="utf-8"))["models"][args.model]
    check = check_prediction(old, report, prediction)
    check_path = out.with_name(out.stem + ".check.json")
    check_path.write_text(json.dumps(check | {"model": args.model, "dump": str(args.dump),
                                              "old_report": str(args.old_report),
                                              "prediction": str(args.prediction)}, indent=2) + "\n",
                          encoding="utf-8")

    result = {
        "model": args.model,
        "n_eval": int(check["n_examples"]),
        "prediction_holds": int(bool(check["prediction_holds"])),
        "clarify_identical": int(bool(check["clarify_identical"])),
        "tripwire_ok": int(bool(check["tripwire_ok"])),
        "successes_old": int(check["successes_old"]),
        "successes_new": int(check["successes_new"]),
        "accuracy_old": float(check["accuracy_old"]),
        "accuracy_new": float(check["accuracy_new"]),
        "artifact_rows_predicted": int(check["artifact_rows_predicted"]),
        "flips_miss_to_hit": int(check["flips_miss_to_hit"]),
        "flips_hit_to_miss": len(check["flips_hit_to_miss"]),
        "flips_miss_to_hit_unpredicted": len(check["flips_miss_to_hit_unpredicted"]),
        "predicted_but_still_missed": len(check["predicted_but_still_missed"]),
        "tripwire_new": int(check["tripwire_new"]) if check["tripwire_new"] is not None else -1,
    }
    results_out = _abs(args.results_out) if args.results_out else out.with_name(out.stem + ".result.json")
    results_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    bth_path = os.environ.get("BTH_RESULTS_PATH")
    if bth_path:
        Path(bth_path).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2))
    print(f"report: {out}\ncheck: {check_path}")
    return 0 if check["prediction_holds"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
