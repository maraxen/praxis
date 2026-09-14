"""plr_sema.check._supported_tools: the DYNAMIC EXECUTION HARNESS's
capability boundary (spec 260901 §6.2's D1 note, "adjacent fix, same
location"; redefined 260901 T11 -- see below).

**No longer the analyzed-surface boundary (260901 T11).** Through spec_version
6, this set doubled as both (a) ``training.verify.dispatcher``'s own
10-method dynamic-execution capability limit, and (b) ``plr_sema``'s entire
analyzed surface -- because derivation and checking were both hand-gated on
it, the two boundaries were accidentally identical and nothing distinguished
them. T11 decouples derivation from this set: ``plr_sema.derive`` now derives
a contract for every method the survey indexed (the whole PLR surface, 4,770
methods at the current pin), and ``plr_sema.check``'s ``unsupported_tool``
reason now means "key absent from that whole-survey contract table", not
"not in this frozenset" (see ``plr_sema.check``'s module docstring). This set
ITSELF is unchanged and still real: it is what
``training.verify.dispatcher`` can actually DISPATCH at runtime (the dynamic
execution harness's own scope boundary), which is a genuinely different fact
from what this STATIC analyzer can derive a contract for. Kept for the one
live drift test below and for ``plr_sema.derive.build_gap_ledger``'s
``supported_tools``-scoped reporting subset (informational only -- it no
longer gates which methods get a contract).

**Single in-package definition (consolidated).** T6 originally placed a
mirror of this set at ``plr_sema.derive`` (module-level, next to the
transitive-closure machinery it feeds). T8 needed the SAME set inside
``check/`` too (§3.3) -- and ``check/`` is stdlib-only, forbidden from
importing ``praxis``/``verify`` (§1.3), so it cannot reach
``training.verify.dispatcher.SUPPORTED_TOOLS`` directly. Rather than typing
a THIRD copy (upstream + derive + check), this module is the single
in-package source of truth: ``plr_sema.derive`` imports and re-exports it
from here (``from plr_sema.check._supported_tools import SUPPORTED_TOOLS``)
so ``from plr_sema.derive import SUPPORTED_TOOLS`` keeps resolving to the
exact same object, and exactly ONE live cross-package drift test
(``tests/test_check_graph.py::test_supported_tools_match_upstream``) checks
it against ``training.verify.dispatcher.SUPPORTED_TOOLS`` -- not two.

Mirrors ``training/verify/dispatcher.py:37-41``'s ``SUPPORTED_TOOLS``
verbatim (10-tool frozenset). Copied, not imported -- same pattern §4.1 uses
for ``FAILURE_CATEGORIES`` (promoted from ``training/verify/failure_taxonomy.
py`` rather than imported), for the same reason: the import-boundary test
(§1.3) forbids ``src/plr_sema/`` from reaching into ``training``/``verify`` at
all, poisoned-import or not.
"""

from __future__ import annotations

#: Mirrors training/verify/dispatcher.py:37-41's SUPPORTED_TOOLS verbatim.
#: Kept honest by test_check_graph.py::test_supported_tools_match_upstream,
#: a live cross-package drift test (same pattern as
#: telemetry.FAILURE_CATEGORIES's test_categories_match_upstream, §4.2).
SUPPORTED_TOOLS: frozenset[str] = frozenset(
    {
        "pick_up_tips",
        "drop_tips",
        "discard_tips",
        "aspirate",
        "dispense",
        "transfer",
        "stamp",
        "move_resource",
        "move_plate",
        "move_lid",
    }
)

__all__ = ["SUPPORTED_TOOLS"]
