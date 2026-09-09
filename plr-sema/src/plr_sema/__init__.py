"""plr-sema: Semantic analysis of PyLabRobot programs: execution-graph IR, well-formedness, and per-operation SAFE / WILL_FAIL / UNKNOWN verdicts.

Round-4 remediation (M6): the package used to export nothing
(`__all__ = []`), so `import plr_sema; plr_sema.check_graph(...)` failed even
though `plr_sema.check.check_graph` worked fine -- AC-1.1's "import plr_sema
exits 0" only ever exercised bare importability, never that the package's
round-1 entry point and record types are actually reachable from the
top-level package name. `check/` is stdlib-only (no libcst/pylabrobot/
pydantic -- see `plr_sema.check`'s module docstring) and `verdict.py` is
stdlib-only too, so re-exporting both here does not widen the import
boundary `tests/test_import_boundary.py` enforces.
"""

from plr_sema.check import check_graph
from plr_sema.verdict import AnalysisReport, Verdict

__all__ = ["check_graph", "AnalysisReport", "Verdict"]
