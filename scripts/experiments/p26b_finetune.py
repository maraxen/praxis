"""P2.6b: retrain the arm-A recipe on the assembly-0.1.4 corpus (repaired floor
rows + natural-phrasing lane) and score it on the FROZEN 228-row eval split
(task 260902_p26b_surface_data, backlog 4890, prereg
.praxia/docs/preregistration/260902_p26b-floor-surface-prereg.md).

Thin ``bth run`` entry point: everything after ``--`` goes to
``praxis_training.finetune.train.main`` (the P2.6 trainer, recipe 0.1.0
unchanged) which also writes the sidecar result dict to ``$BTH_RESULTS_PATH``.
The pre-registered prediction fields (surface6_recovered,
verb_category_migrated, flips_hit_to_miss, probe_*) are filled by the
trainer's ``--compare-report`` / ``--probe-pairs`` options (P2.6b plumbing).

Bootstrap: if ``praxis_training`` is not importable under the interpreter
``bth run`` picked, re-exec under the repo venv, falling back to
``uv run --offline --no-sync --package training``. ``os.execv`` keeps the
environment, so ``BTH_RESULTS_PATH`` / ``BTH_OUTPUT_DIR`` plumbing survives.

Cluster invocation (first word = scripts/slurm/bth_run.sh, see lesson 469)::

    bth submit --remote engaging --preset gpu --name p26b-arm-A --no-push-first -- \
        scripts/slurm/bth_run.sh \
        env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
            PRAXIS_GIT_SHA=$(git rev-parse HEAD) PRAXIS_GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD) \
        bth run --script-path scripts/experiments/p26b_finetune.py \
            --output-paths outputs/p26b/A/result.json --tags arm:A2 -- \
            --arm A --seed 0 --eval-after --out-dir outputs/p26b/A \
            --compare-report training/eval/reports/260902_p26_rescore_A.json \
            --probe-pairs training/assemble/out/corpus_p25_probe.jsonl \
            --probe-sidecar training/assemble/out/corpus_p25_probe_sidecar.jsonl
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BOOTSTRAP_FLAG = "PRAXIS_P26B_BOOTSTRAPPED"


def _bootstrap_into_training_env() -> None:
    """Re-exec under an interpreter that has the training extra installed."""
    if os.environ.get(_BOOTSTRAP_FLAG):
        sys.stderr.write(
            "p26b_finetune: praxis_training still not importable after re-exec; "
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
        sys.stderr.write("p26b_finetune: neither .venv/bin/python nor uv found\n")
        raise SystemExit(3)
    argv = [uv, "run", "--offline", "--no-sync", "--package", "training", "python",
            str(Path(__file__).resolve()), *script_args]
    os.chdir(_REPO_ROOT)
    os.execve(uv, argv, env)


try:
    from praxis_training.finetune.train import main
except ModuleNotFoundError as exc:  # pragma: no cover - exercised on the cluster
    if exc.name and exc.name.split(".")[0] in {"praxis_training", "torch", "trl", "transformers", "datasets"}:
        _bootstrap_into_training_env()
    raise

if __name__ == "__main__":
    raise SystemExit(main())
