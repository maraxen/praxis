#!/usr/bin/env python3
"""AC-39(b)-(e), sprint C: are the dock gates SENSITIVE to what they guard?

Pre-registered by ``scripts/spikes/260929_nd_sensitivity_sprint_c.bth.toml`` (committed BEFORE
the run). This is sprint C's thin entry script (D17, C7-8; task C7): it fixes the negative set to
``b``, ``c``, ``d`` and ``e`` and calls the shared driver ``scripts/negatives/260929_nd_sensitivity.py``,
loaded by path.

* ``b``: ``assets/visualizer3d-augmentations/socket.js`` removed from its own dist copy; ONLY the ``K1a``
  unit (``--dock-check --scenario K1a``) runs against it and must exit nonzero naming ``viewer_resources``.
* ``c``: a static scan, no browser: ``grep -rnE '__praxis_test|data-praxis-test'`` over ``web-repl/shell/display``
  and ``web-repl/overlay/assets/visualizer3d-augmentations`` (``*.js``, not ``__tests__``) must find nothing.
* ``d``: ONLY the negative-only ``N-d`` unit: at 1600x900 the harness puts the viewer page in a STOCK split-right
  widget of its own and the AC-36 >= 1600 width predicate must report failure (naming ``panel_width_wide_1600``);
  ``skipped`` passes only where the recorded D6 sizing case makes that key recorded-only.
* ``e``: ONLY ``K1b`` with the harness-only ``--neg drop-query``: ``late_iframe`` must fail, and the harness must
  show that queries were actually dropped.

Each harness negative gets its own dist copy under ``/tmp/claude-1000/nd-neg/<negative>/dist/`` and its own
harness ``--out-dir`` under ``/tmp/claude-1000/nd-neg/<negative>/out/`` (C8-5). Like sprints A and B, this entry
script sits beside the spike scripts (the spec's file plan names ``scripts/negatives/``; a ``git mv`` plus the
path strings in the sidecar and the tests would move all three).

Run it (unsandboxed, from a checkout whose ``web-repl/dist`` is a FRESH build at the pin)::

    bth run --project-slug praxis --output-paths outputs/nd_sensitivity/sprint_c -- \\
        uv run --no-sync python3 scripts/spikes/260929_nd_sensitivity_sprint_c.py \\
        --out-dir outputs/nd_sensitivity/sprint_c --dist web-repl/dist [--resume]

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
SPRINT = "c"
NEGATIVES = ("b", "c", "d", "e")


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
