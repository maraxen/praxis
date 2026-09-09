"""Spec 260901 §5.3 "Fork C" / §5.6 AC-5.5 / D8, STRENGTHENED 260902 by §11
(``260902_plr-sema-ir-bytecode-increment.md``, §11.4.2/§11.7 AC-11.1) from a
SUBSET check into an EXHAUSTIVENESS check.

Lives under `tests/`, which spec §1.3's boundary walk does NOT cover (that
walk is scoped to `src/plr_sema/`) -- so, unlike anything under `src/`, this
file MAY import `praxis.backend.utils.plr_static_analysis.models`. Compares
`plr_sema.check.graph`'s mirror dataclasses' field names against the live
pydantic models' `model_fields` keys, in BOTH directions, for all THREE
models (`OperationNode`, `ResourceNode`, and -- new in this file --
`ProtocolComputationGraph`).

**Why exhaustiveness, not subset (260902 supersession).** Through
spec_version 9, `check/graph.py`'s field set was "derived-from-consumers,
normative" (D1): a field was mirrored iff a consumer needed it, and this
test only checked `mirror_fields <= upstream_fields` -- it could not see
OVER-inclusion relative to a §6.2 table (a second test,
`test_mirror_field_set_matches_spec_table`, covered that by comparing
against a hand-transcribed literal list). SEMA-IR's no-drop invariant
(§11.1.4) replaces "which fields does a consumer need" with "every field
gets exactly one disposition", and the mirror grows from a hand-chosen
subset to the FULL upstream field set -- so the correct comparison is now
equality, and a single test suffices: `mirror_fields == upstream_fields`,
both directions. A field added upstream now turns THIS test red (previously
it would pass silently, since subset-only cannot detect a missing field);
a mirrored field that no longer exists upstream still turns it red, as it
always did.

Fails CLOSED (an assertion, not a skip) whenever `praxis` is importable in
the running test environment (spec §5.5's Fork C failure-mode note) --
converting a silent runtime gap (a mirrored field that no longer exists
upstream, producing a silent None/KeyError at `json.loads` time rather than
an import-time error, since the mirror never imports the pydantic model to
fail against) into a red test at review time. Only skips, with an explicit
reason, when `praxis` genuinely is not importable in this environment.

**Relationship to `tests/test_ir.py`'s AC-11.1.** That test checks
`plr_sema.check.ir.DISPOSITIONS` -- the disposition table itself -- against
field names read by AST/regex directly off `models.py` (no pydantic
import, environment-independent). This file checks a DIFFERENT thing: that
`check/graph.py`'s dataclass mirror (the lowering's documented input
schema, §11.4.2) has not drifted from the LIVE pydantic model. The two
together give environment-independent AND live-import coverage; neither
substitutes for the other.
"""

from __future__ import annotations

import dataclasses

import pytest
from plr_sema.check.graph import OperationNode, ProtocolComputationGraph, ResourceNode

try:
    from praxis.backend.utils.plr_static_analysis.models import (
        OperationNode as UpstreamOperationNode,
    )
    from praxis.backend.utils.plr_static_analysis.models import (
        ProtocolComputationGraph as UpstreamProtocolComputationGraph,
    )
    from praxis.backend.utils.plr_static_analysis.models import (
        ResourceNode as UpstreamResourceNode,
    )
except ImportError as exc:  # pragma: no cover - environment-dependent
    UpstreamOperationNode = None
    UpstreamResourceNode = None
    UpstreamProtocolComputationGraph = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


_MIRROR_TARGETS = [
    (OperationNode, "OperationNode", UpstreamOperationNode),
    (ResourceNode, "ResourceNode", UpstreamResourceNode),
    (ProtocolComputationGraph, "ProtocolComputationGraph", UpstreamProtocolComputationGraph),
]


@pytest.mark.parametrize(
    "mirror_cls, mirror_name, upstream_cls",
    _MIRROR_TARGETS,
    ids=["OperationNode", "ResourceNode", "ProtocolComputationGraph"],
)
def test_mirror_is_exhaustive_against_upstream(mirror_cls, mirror_name, upstream_cls) -> None:
    """§11.4.2/AC-11.1: `{f.name for f in dataclasses.fields(mirror_cls)}
    == set(upstream_cls.model_fields)`, both directions. Fails closed -- if
    `praxis` is not importable here, this is a genuine environment gap, not
    a pass, and is reported via `pytest.skip` with the import error named,
    never a silent pass.
    """
    if _IMPORT_ERROR is not None:
        pytest.skip(
            f"praxis not importable in this test environment ({_IMPORT_ERROR!r}) -- "
            f"Fork C's mirror-drift check cannot run; this is an environment gap, "
            f"not evidence the mirror is correct"
        )

    upstream_fields = set(upstream_cls.model_fields.keys())
    mirror_fields = {f.name for f in dataclasses.fields(mirror_cls)}

    extra = mirror_fields - upstream_fields
    missing = upstream_fields - mirror_fields
    assert not extra and not missing, (
        f"plr_sema.check.graph.{mirror_name}'s field set {sorted(mirror_fields)} != "
        f"the live praxis {mirror_name}.model_fields set {sorted(upstream_fields)} "
        f"(SEMA-IR's no-drop invariant, §11.1.4, requires exact equality) -- "
        f"extra (mirrored but not upstream): {sorted(extra)}, "
        f"missing (upstream but not mirrored): {sorted(missing)}"
    )


@pytest.mark.parametrize(
    "mirror_cls, expected_count",
    # OperationNode 15 -> 16 (spec §12.2/#4932: `trip` added for a REGION
    # loop header's proved trip count, §12.2.3).
    [
        (OperationNode, 16),
        (ResourceNode, 9),
        (ProtocolComputationGraph, 10),
    ],
    ids=["OperationNode", "ResourceNode", "ProtocolComputationGraph"],
)
def test_mirror_field_counts_match_spec(mirror_cls, expected_count) -> None:
    """§11.7 AC-11.1's second half: the three measured counts are pinned at
    (16, 9, 10) for the current upstream model -- the number that must be
    RE-READ, not re-guessed, the day it changes. Does not require `praxis`
    to be importable (a pure count of this module's own dataclass fields).
    """
    actual = len(dataclasses.fields(mirror_cls))
    assert actual == expected_count, (
        f"{mirror_cls.__name__} has {actual} mirrored fields, expected "
        f"{expected_count} (spec §11.7 AC-11.1's pinned upstream field count -- "
        f"re-read this number from models.py if it legitimately changed, "
        f"do not just bump the constant)"
    )
