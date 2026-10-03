"""plr-sema: Semantic analysis of PyLabRobot programs: execution-graph IR, well-formedness, and per-operation SAFE / WILL_FAIL / UNKNOWN verdicts.

Round-4 remediation (M6): the package used to export nothing
(`__all__ = []`), so `import plr_sema; plr_sema.check_graph(...)` failed even
though `plr_sema.check.check_graph` worked fine -- AC-1.1's "import plr_sema
exits 0" only ever exercised bare importability, never that the package's
round-1 entry point and record types are actually reachable from the
top-level package name. `check/` is stdlib-only (no libcst/pylabrobot/
pydantic -- see `plr_sema.check`'s module docstring) and `verdict.py` is
stdlib-only too, so re-exporting both here does not widen the import
boundary `tests/test_import_boundary.py` enforces. Since spec 261002 Slice 1
it also exposes ``analyze`` and its outcome types lazily (see ``__getattr__``).
"""

from plr_sema.check import check_graph
from plr_sema.verdict import AnalysisReport, Verdict

_LAZY = {
    "analyze": "plr_sema.analysis",
    "Analyzed": "plr_sema.analysis",
    "NotAnalyzed": "plr_sema.analysis",
    "NotAnalyzedReason": "plr_sema.analysis",
    "VerdictKey": "plr_sema.analysis",
}

__all__ = ["check_graph", "AnalysisReport", "Verdict", *_LAZY]


def __getattr__(name: str):
    # spec 261002 §4: lazy so `import plr_sema` never loads plr_sema.analysis's
    # contracts/tomllib machinery at import time; analysis itself defers libcst.
    if name in _LAZY:
        import importlib

        value = getattr(importlib.import_module(_LAZY[name]), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'plr_sema' has no attribute {name!r}")
