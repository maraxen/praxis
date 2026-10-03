"""plr_sema.extract: source -> ProtocolComputationGraph (libcst).

Since spec 261002 Slice 1 this is the one extractor: it was moved here from
``praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py``,
which is now a re-export shim. Requires the ``extract`` extra. Import the
functions from ``plr_sema.extract.computation_graph_extractor``; this package
``__init__`` stays import-free so ``import plr_sema.extract`` does not load libcst.
"""

from __future__ import annotations

__all__: list[str] = []
