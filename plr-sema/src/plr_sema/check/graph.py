"""plr_sema.check.graph: stdlib-dataclass mirror of the extracted protocol
computation graph (spec 260901 §5.3 "Fork C", §6.2; superseded 260902 by
§11 -- ``260902_plr-sema-ir-bytecode-increment.md``).

**Why a mirror, not the real model.** ``OperationNode``/``ResourceNode``/
``ProtocolComputationGraph`` (``praxis/backend/utils/plr_static_analysis/
models.py:524-662``) are pydantic ``BaseModel``s under ``praxis.*`` --
forbidden under ``check/`` by §1.3 (no ``praxis`` import under
``src/plr_sema/``) and unmovable per §1.1 (round 1 moves nothing out of
``praxis/``), independent of any Pyodide/pydantic question. The wire format
between ``extract/`` (server-side, round 2) and ``check/`` (browser-side,
this module) is already JSON (§6.2), so this mirror is populated by
``json.loads`` + explicit field extraction below -- NEVER by a pydantic
``model_validate``. No third model hierarchy is introduced: this triple of
stdlib mirrors is the only model hierarchy ``check/`` ever sees.

**260902: total, not derived-from-consumers (§11.1.4/§11.4.2's normative
supersession).** Through spec_version 9 the field set here was
"derived-from-consumers, normative, not exemplary" (D1) -- a field was
mirrored iff a §3.3 reason or the §7.3 contract-table lookup key consumed
it, and the old module docstring said, verbatim, "do not add to it, do not
trim it". SEMA-IR (§11) supersedes that rule with the **no-drop invariant**:
every field of every upstream model gets exactly one disposition -- an
instruction field (I), a widen trigger (W), sideband (S, carried but never
hashed and never read by ``check_ir``), or excluded-with-a-written-reason
(X) -- and the full table lives in ``plr_sema.check.ir.DISPOSITIONS``, not
here. This module's job changed accordingly: it is no longer the checker's
own input (``check_graph`` now calls ``plr_sema.check.ir.lower_graph``
directly on the raw JSON payload, never through these dataclasses -- see
``plr_sema.check``'s module docstring), it is the LOWERING's documented
input schema, grown from 7/1/3 fields (the old derived-from-consumers
subset) to the full 15/9/10 upstream field set (260902), now 16/9/10
(spec §12.2/#4932's ``trip`` field, §12.2.3). ``tests/
test_check_graph_mirror_drift.py`` (Fork C) is correspondingly strengthened
from a subset check to an EXHAUSTIVENESS check: ``{f.name for f in
dataclasses.fields(Mirror)} == set(UpstreamModel.model_fields)``, both
directions, for all three models -- a field added upstream now turns it
red (previously it would pass silently, since the old check was subset-only
and one-directional), and so does a mirrored field that no longer exists
upstream.

**``parse_graph``/``_operation_from_dict``/``_resource_from_dict`` are kept
for API continuity and as the (still-exercised) reference deserializer,
but ``check_graph``'s own runtime pipeline no longer calls them** -- see
``plr_sema.check.ir.lower_graph``, which reads the raw JSON payload dict
directly (a lowering that needs ``ast.parse`` on the ``arguments`` values
and first-appearance slot assignment has no use for an intermediate frozen
dataclass). ``is_grounded`` is likewise kept but has no current caller in
this package; see its own docstring.

**SPEC GAP, carried forward from round 4, now resolved by the no-drop
invariant itself.** §5.3/§6.2 used to describe the mirrored ``ResourceNode``
field as "``id``, and whatever identifies the resource variable it
corresponds to" -- but the live
``praxis.backend.utils.plr_static_analysis.models.ResourceNode`` (:562-587)
has NO ``id`` field; ``ProtocolComputationGraph.resources`` is
``dict[str, ResourceNode]``, keyed by variable name, and ``ResourceNode``
itself separately carries that same name as ``variable_name`` (:564). The
no-drop invariant makes this moot: every real field is mirrored now
(including ``variable_name``), so there is no "which field identifies it"
judgement left to flag -- ``variable_name`` is simply one of the nine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "OperationNode",
    "ResourceNode",
    "ProtocolComputationGraph",
    "parse_graph",
    "is_grounded",
]


@dataclass(frozen=True, slots=True)
class OperationNode:
    """Total stdlib mirror of
    ``praxis.backend.utils.plr_static_analysis.models.OperationNode``
    (16 fields, spec §12.2/#4932 -- ``trip`` added for a REGION loop
    header's proved trip count, §12.2.3) -- see ``plr_sema.check.ir.
    DISPOSITIONS["OperationNode"]`` for the per-field disposition
    (§11.1.4).
    """

    id: str
    line_number: int
    method_name: str
    receiver_variable: str
    receiver_type: str | None
    arguments: dict[str, str]
    node_type: str
    preconditions: tuple[str, ...]
    creates_state: tuple[str, ...]
    depends_on_params: tuple[str, ...]
    foreach_source: str | None
    foreach_body: tuple[str, ...]
    trip: int | None
    condition_expr: str | None
    true_branch: tuple[str, ...]
    false_branch: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResourceNode:
    """Total stdlib mirror of
    ``praxis.backend.utils.plr_static_analysis.models.ResourceNode``
    (:562-587, 9 fields) -- see ``plr_sema.check.ir.DISPOSITIONS
    ["ResourceNode"]`` for the per-field disposition (§11.1.4).
    """

    variable_name: str
    declared_type: str
    element_type: str | None
    is_container: bool
    is_parameter: bool
    parental_chain: tuple[str, ...]
    source_expression: str | None
    items_x: int | None
    items_y: int | None


@dataclass(frozen=True, slots=True)
class ProtocolComputationGraph:
    """Total stdlib mirror of
    ``praxis.backend.utils.plr_static_analysis.models.ProtocolComputationGraph``
    (:613-634, 10 fields, methods excluded -- see ``plr_sema.check.ir.
    DISPOSITIONS["ProtocolComputationGraph"]`` for the per-field
    disposition, §11.1.4).
    """

    protocol_fqn: str
    protocol_name: str
    operations: tuple[OperationNode, ...]
    resources: dict[str, ResourceNode]
    preconditions: tuple[Any, ...]
    execution_order: tuple[str, ...]
    machine_types: tuple[str, ...]
    resource_types: tuple[str, ...]
    has_loops: bool
    has_conditionals: bool


def _operation_from_dict(d: dict[str, Any]) -> OperationNode:
    return OperationNode(
        id=d["id"],
        line_number=d.get("line_number", 0),
        method_name=d["method_name"],
        receiver_variable=d["receiver_variable"],
        receiver_type=d.get("receiver_type"),
        arguments=dict(d.get("arguments") or {}),
        node_type=d.get("node_type", "static"),
        preconditions=tuple(d.get("preconditions", ())),
        creates_state=tuple(d.get("creates_state", ())),
        depends_on_params=tuple(d.get("depends_on_params", ())),
        foreach_source=d.get("foreach_source"),
        foreach_body=tuple(d.get("foreach_body", ())),
        trip=d.get("trip"),
        condition_expr=d.get("condition_expr"),
        true_branch=tuple(d.get("true_branch", ())),
        false_branch=tuple(d.get("false_branch", ())),
    )


def _resource_from_dict(d: dict[str, Any]) -> ResourceNode:
    return ResourceNode(
        variable_name=d["variable_name"],
        declared_type=d.get("declared_type", ""),
        element_type=d.get("element_type"),
        is_container=bool(d.get("is_container", False)),
        is_parameter=bool(d.get("is_parameter", True)),
        parental_chain=tuple(d.get("parental_chain", ())),
        source_expression=d.get("source_expression"),
        items_x=d.get("items_x"),
        items_y=d.get("items_y"),
    )


def parse_graph(payload: dict[str, Any]) -> ProtocolComputationGraph:
    """Deserialize one graph JSON payload (§6.2's wire format -- the raw
    ``.model_dump(mode="json")`` output of the real, out-of-process
    ``ProtocolComputationGraph``) into this module's stdlib mirror.
    ``json.loads`` + explicit field extraction only -- never a pydantic
    ``model_validate`` (see module docstring). Kept for API continuity;
    ``check_graph``'s own runtime pipeline lowers the raw payload directly
    through ``plr_sema.check.ir.lower_graph`` instead (see module
    docstring).
    """
    operations = tuple(_operation_from_dict(o) for o in payload.get("operations", ()))
    resources = {
        name: _resource_from_dict(r) for name, r in payload.get("resources", {}).items()
    }
    return ProtocolComputationGraph(
        protocol_fqn=payload["protocol_fqn"],
        protocol_name=payload.get("protocol_name", ""),
        operations=operations,
        resources=resources,
        preconditions=tuple(payload.get("preconditions", ())),
        execution_order=tuple(payload.get("execution_order", ())),
        machine_types=tuple(payload.get("machine_types", ())),
        resource_types=tuple(payload.get("resource_types", ())),
        has_loops=bool(payload.get("has_loops", False)),
        has_conditionals=bool(payload.get("has_conditionals", False)),
    )


def is_grounded(op: OperationNode, graph: ProtocolComputationGraph) -> bool:
    """Graph-membership test: does ``op.receiver_variable`` correspond to a
    ``ResourceNode`` present in ``graph.resources``? No current caller in
    this package (kept for API continuity, spec §5.3's forward-looking
    note) -- SEMA-IR's own equivalent is the ``grounded`` fact
    ``plr_sema.check.ir.lower_graph`` tracks per slot while assigning
    ``Ref``s (§11.3.1).
    """
    return op.receiver_variable in graph.resources
