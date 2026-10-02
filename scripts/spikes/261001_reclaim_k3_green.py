#!/usr/bin/env python3
"""K3, GREEN phase (backlog #5656, AC-N5): the pre-registered run on the build WITH the fix.

Pre-registered by ``scripts/spikes/261001_reclaim_k3_green.bth.toml`` (committed BEFORE either run). ``bth run`` ties a sidecar to the
script it runs by name, so this one-line launcher exists beside it; the runner is ``scripts/spikes/261001_reclaim_k3.py``.

    bth run --project-slug praxis --output-paths outputs/reclaim_k3/green -- \\
        uv run --no-sync python3 scripts/spikes/261001_reclaim_k3_green.py --dist web-repl/dist --out-dir outputs/reclaim_k3/green [--resume]
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

RUNNER_PATH = Path(__file__).resolve().with_name("261001_reclaim_k3.py")
PHASE = "green"


def main(argv: list[str] | None = None, **kwargs) -> int:
    spec = importlib.util.spec_from_file_location("reclaim_k3_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load the K3 runner from {RUNNER_PATH}")
    runner = importlib.util.module_from_spec(spec)
    sys.modules["reclaim_k3_runner"] = runner
    spec.loader.exec_module(runner)
    return runner.main(argv, phase=PHASE, **kwargs)


if __name__ == "__main__":
    sys.exit(main())
