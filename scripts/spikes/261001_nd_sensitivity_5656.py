#!/usr/bin/env python3
"""N-g (backlog #5656, AC-N6): the bathos-visible entry of the deck-layout sensitivity run.

Pre-registered by ``scripts/spikes/261001_nd_sensitivity_5656.bth.toml`` (committed BEFORE the run). ``bth run`` ties a sidecar to the
script it runs by name, so this one-line launcher sits beside the sidecar; the driver (the negative ``g``, its harness unit ``N-g``
and the shared AC-39 machinery it loads by path) is ``scripts/negatives/261001_nd_sensitivity_5656.py``, which also is the entry its unit
subprocesses start and the file whose sha256 is the run's ``entry`` input.

    bth run --project-slug praxis --output-paths outputs/nd_sensitivity/sprint_5656 -- \\
        uv run --no-sync python3 scripts/spikes/261001_nd_sensitivity_5656.py \\
        --out-dir outputs/nd_sensitivity/sprint_5656 --dist web-repl/dist [--resume]
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

DRIVER_PATH = Path(__file__).resolve().parents[1] / "negatives" / "261001_nd_sensitivity_5656.py"


def main(argv: list[str] | None = None, **kwargs) -> int:
    spec = importlib.util.spec_from_file_location("nd_sensitivity_5656_driver", DRIVER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load the N-g driver from {DRIVER_PATH}")
    driver = importlib.util.module_from_spec(spec)
    sys.modules["nd_sensitivity_5656_driver"] = driver
    spec.loader.exec_module(driver)
    return driver.main(argv, **kwargs)


if __name__ == "__main__":
    sys.exit(main())
