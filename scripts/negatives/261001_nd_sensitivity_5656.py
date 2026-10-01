#!/usr/bin/env python3
"""AC-N6 / N-g (backlog #5656): is the re-clamp's predicate SENSITIVE to the empty strip beside the deck?

Pre-registered by ``scripts/spikes/261001_nd_sensitivity_5656.bth.toml`` (committed BEFORE the run). This module is the N-g driver of
the deck-layout increment (spec ``.praxia/docs/specs/261001_nd-next-5656-deck-layout.md`` AC-N6, task T7). It adds ONE negative to the
shared AC-39 driver ``scripts/negatives/260929_nd_sensitivity.py`` WITHOUT editing that file: the shared driver is a hashed input of the
locked sprint A, B and C sensitivity runs (A31), so it is loaded by path and the negative ``g`` is registered in the LOADED module's table.

* ``g``: ONLY the negative-only unit ``N-g`` (``repl_smoke.py --dock-check --scenario N-g``): at 1440x900 the harness adds a STOCK
  split-right widget that carries the deck's CSS limits (min 420 / max 480 px, no dock.js sizing), measures the layout Lumino leaves, then
  sizes that SAME widget so its half is 480 / A (the path the fix uses) and measures again. K3's predicate ``reclaim_ok(.., 480)`` must
  report FAILURE on the first (the unit exits nonzero naming ``reclaim_ok_stock_capped_1440``) and SUCCESS on the second.

``g_detected`` iff the measurement is valid and the predicate failed on the stock arrangement; ``g_not_detected`` iff it is valid and the
predicate passed there (which would contradict the recorded run: a finding about Lumino, not a pass). Validity comes from INPUTS, never
from the dead-space output: every rect present, the stock node's computed min / max = 420px / 480px, the layout config's sizes 0.5 / 0.5
+- 0.01, and the control passing ``reclaim_ok``. A measurement that fails any of them raises inside the harness unit (an error finding) and
the run is ``invalid``.

The negative gets its own dist copy under ``/tmp/claude-1000/nd-neg/g/dist/`` and its own harness ``--out-dir`` under
``/tmp/claude-1000/nd-neg/g/out/`` (C8-5). Nothing about the stock arrangement depends on dock.js (the dock is closed, so the re-clamp
never runs): the run does not need the fixed build, and it can be re-run on any later build. Run it (unsandboxed, from a checkout whose
``web-repl/dist`` is a FRESH build)::

    bth run --project-slug praxis --output-paths outputs/nd_sensitivity/sprint_5656 -- \\
        uv run --no-sync python3 scripts/spikes/261001_nd_sensitivity_5656.py \\
        --out-dir outputs/nd_sensitivity/sprint_5656 --dist web-repl/dist [--resume]

``bth``, never ``uv run bth`` (which silently skips sidecar enforcement). Verify the run by its RECORD: ``bth compact`` then
``bth sql "SELECT id, status, outcome, exit_code, command FROM runs WHERE id LIKE '<prefix>%'"``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

DRIVER_PATH = Path(__file__).resolve()
SHARED_PATH = DRIVER_PATH.parent / "260929_nd_sensitivity.py"
SPRINT = "5656"
NEGATIVES = ("g",)
HARNESS_UNIT = "N-g"
EXPECTED_KEY = "reclaim_ok_stock_capped_1440"

_SHARED = None


def negative_g(shared):
    """The ``Negative`` record of ``g`` in the shared driver's own dataclass."""
    return shared.Negative(
        id="g",
        harness_flag="--dock-check",
        harness_unit=HARNESS_UNIT,
        expected_key=EXPECTED_KEY,
        delete=None,
        mutation=(
            "none to the dist copy: at 1440x900 the harness adds a STOCK split-right widget that carries the deck's CSS limits "
            "(min 420 / max 480 px, no dock.js sizing), measures the layout Lumino leaves and applies K3's predicate "
            "reclaim_ok(.., 480) to it, which must report failure; the same widget sized by the harness itself must pass it"
        ),
        result_checks=(("control_sized_passes", "true"),),
    )


def load_shared():
    """The shared driver, loaded by path ONCE, with negative ``g`` registered in the loaded module's table (the file is not edited)."""
    global _SHARED
    if _SHARED is not None:
        return _SHARED
    spec = importlib.util.spec_from_file_location("nd_sensitivity_shared_5656", SHARED_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load the shared sensitivity driver from {SHARED_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nd_sensitivity_shared_5656"] = module
    spec.loader.exec_module(module)
    module.NEGATIVES["g"] = negative_g(module)
    _SHARED = module
    return module


def main(argv: list[str] | None = None, **kwargs) -> int:
    shared = load_shared()
    return shared.main(argv, sprint=SPRINT, negatives=NEGATIVES, entry_path=DRIVER_PATH, **kwargs)


if __name__ == "__main__":
    sys.exit(main())
