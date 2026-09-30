#!/usr/bin/env python3
"""AC-39(a), sprint A: is the D1 chrome scenario sensitive to the display module being absent?

Pre-registered by ``scripts/spikes/260929_nd_sensitivity_sprint_a.bth.toml`` (committed BEFORE
the run). This is sprint A's thin entry script (D17, C7-8): it fixes the negative set to ``a``
and calls the shared driver ``scripts/negatives/260929_nd_sensitivity.py``, loaded by path.
Negative ``a`` removes ``shell/display/index.js`` from its own dist copy and runs ONLY the
``D1`` harness unit against it (``--display-check --scenario D1``); the harness must exit
nonzero and name ``rail_state_after_run`` among its failing keys.

Run it (unsandboxed, from a checkout whose ``web-repl/dist`` is a FRESH build at the pin)::

    bth run --project-slug praxis --output-paths outputs/nd_sensitivity/sprint_a -- \\
        uv run --no-sync python3 scripts/spikes/260929_nd_sensitivity_sprint_a.py \\
        --out-dir outputs/nd_sensitivity/sprint_a --dist web-repl/dist [--resume]

``bth``, never ``uv run bth`` (which silently skips sidecar enforcement). Verify the run by its
RECORD: ``bth compact`` then
``bth sql "SELECT id, status, outcome, exit_code, command FROM runs WHERE id LIKE '<prefix>%'"``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ENTRY_PATH = Path(__file__).resolve()
SHARED_PATH = ENTRY_PATH.parents[1] / "negatives" / "260929_nd_sensitivity.py"
SPRINT = "a"
NEGATIVES = ("a",)


_SHARED = None


def _load_shared():
    """The shared driver, loaded by path ONCE (a fresh load per call would discard test patches)."""
    global _SHARED
    if _SHARED is not None:
        return _SHARED
    spec = importlib.util.spec_from_file_location("nd_sensitivity_shared", SHARED_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load the shared sensitivity driver from {SHARED_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nd_sensitivity_shared"] = module
    spec.loader.exec_module(module)
    _SHARED = module
    return module


def main(argv: list[str] | None = None, **kwargs) -> int:
    shared = _load_shared()
    return shared.main(argv, sprint=SPRINT, negatives=NEGATIVES, entry_path=ENTRY_PATH, **kwargs)


if __name__ == "__main__":
    sys.exit(main())
