"""Re-export shim: moved to ``plr_sema.extract.computation_graph_extractor`` (spec 261002 Slice 1)."""

from plr_sema.extract.computation_graph_extractor import *  # noqa: F401,F403
from plr_sema.extract.computation_graph_extractor import _walk_cst_node  # noqa: F401  tests/utils/test_computation_graph.py
