"""plr_sema.extract: the server-side extractor (spec 260901 §6.2).

**Round 2, not round 1.** ``src/plr_sema/extract/`` is where ``libcst`` and
``pylabrobot`` imports are permitted (§6.1/§6.2) -- source-in,
``ProtocolComputationGraph``-JSON-out, feeding ``plr_sema.check`` over the
wire. It does not exist as a working implementation in round 1: building it
now would be circular (§6.2/C5) -- round 1's ``check_graph`` fixture is
produced out-of-process, by subprocessing into the EXISTING
``praxis.backend.utils.plr_static_analysis`` extractor
(``visitors/computation_graph_extractor.py``), not by this package. This
module is a placeholder marking the packaging seam (§1.1's layout) so
``extract/`` exists as an importable, empty namespace; the ``@jit``/
``check(fn)`` capability (source->graph, server-side) is round 2's work.
"""

from __future__ import annotations

__all__: list[str] = []
