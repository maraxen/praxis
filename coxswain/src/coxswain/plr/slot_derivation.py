"""D11 deterministic derivation of ``missing_required`` / ``unresolved_slots``
(P2.0 deliverable 3).

D11 (spec rev2): the model predicts ONLY ``{name, params}``. Whether a call is
incomplete and which arguments are symbolic references are DERIVED
deterministically, post-parse, from the canonical namespace tables -- never
from model output, never from value heuristics.

Classification rule (the whole rule):

1. Look up the tool's table rows. Unknown or excluded-from-phase-2 tool names
   raise KeyError (loud; generation cannot reach them anyway).
2. A required row whose param is absent from the input mapping OR bound to
   None adds its schema-side name to ``missing_required`` (table declaration
   order). Presence-based: an empty list counts as present.
3. For each PRESENT known param with kind SYMBOLIC_RESOURCE_REF:
   string values become one ``DerivedSlot`` each; list/tuple values contribute
   one slot per string element, in given order (FR-3 as-given); non-string
   structured payloads (e.g. a Coordinate mapping) count as grounded literals.
4. Params with kind LITERAL are never slots, even when string-valued -- the
   TABLE decides kind, not stringiness.
5. Unknown extra params land in ``unknown_params`` (advisory): worker output
   is advisory-only under C-M1, so the gate stays total; the kernel-side
   validation mandated by F1-rev2 still exits ``clarify:*`` before propose.

NFR-1/NFR-2: pure function, stdlib only, no ``js``, no ``praxis.*``, input
mapping never mutated. Field names deliberately mirror
``coxswain.fft.context.UnresolvedSlot`` (arg_name/reference/resource_type);
fft imports plr, never the reverse, so downstream conversion is a plain copy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from coxswain.plr.param_namespace import ParamKind, params_of

__all__ = ["CallGaps", "DerivedSlot", "derive_call_gaps"]


@dataclass(frozen=True)
class DerivedSlot:
    """One symbolic reference awaiting grounding (mirrors fft UnresolvedSlot)."""

    arg_name: str
    reference: str
    resource_type: str


@dataclass(frozen=True)
class CallGaps:
    """The deterministic gap report for one parsed call."""

    #: Required schema params absent (or None), in table declaration order.
    missing_required: tuple[str, ...] = ()
    #: Symbolic references needing grounding, in params-as-given order.
    unresolved_slots: tuple[DerivedSlot, ...] = ()
    #: Params outside the canonical namespace (advisory; C-M1 advisory rule).
    unknown_params: tuple[str, ...] = ()


def _slots_for(value: Any, spec_name: str, resource_type: str) -> list[DerivedSlot]:
    if isinstance(value, str):
        return [DerivedSlot(spec_name, value, resource_type)]
    if isinstance(value, (list, tuple)):
        return [
            DerivedSlot(spec_name, element, resource_type)
            for element in value
            if isinstance(element, str)
        ]
    return []  # structured payloads (Coordinate mappings, numbers) are grounded


def derive_call_gaps(tool_name: str, params: Mapping[str, Any]) -> CallGaps:
    """Classify one call's args and derive its gap fields deterministically."""
    rows = params_of(tool_name)  # KeyError on unknown/excluded tool: loud
    known = {spec.name: spec for spec in rows}

    missing = tuple(
        spec.name for spec in rows if spec.required and params.get(spec.name) is None
    )
    slots: list[DerivedSlot] = []
    for key in params:
        spec = known.get(key)
        if spec is None or spec.kind is not ParamKind.SYMBOLIC_RESOURCE_REF:
            continue
        slots.extend(_slots_for(params[key], key, spec.resource_type or ""))
    unknown = tuple(key for key in params if key not in known)

    return CallGaps(missing_required=missing, unresolved_slots=tuple(slots), unknown_params=unknown)
