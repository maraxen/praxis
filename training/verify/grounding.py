"""Reference-string grounding for the P2.2 verify harness.

Grammar (the harness-side twin of cue-2 grounding; deterministic):

* ``<name>``              whole deck resource (plate, holder, rack)
* ``<name>.<id>``         one well / tip spot, ALWAYS returned as a 1-list
                          (vendored ItemizedResource.__getitem__ returns lists
                          even for single identifiers)
* ``<name>.<id>:<id2>``   vendored colon-range STRING semantics -- INCLUSIVE
                          on both ends (verified against vendored
                          ``pylabrobot.utils.positions.expand_string_range``
                          and ``ItemizedResource.__getitem__``'s own
                          docstring example: ``"A1:E1"`` yields A1..E1, 5
                          items; cross-checked against the official PLR
                          user-guide notebook `hamilton-star/basic.ipynb`,
                          which pairs ``plate["A1:C1"]`` with a 3-element
                          volume list across "channels 1, 2, and 3").
                          260828 finding: a prior version of this module
                          constructed a Python SLICE OBJECT (``obj[a:b]``)
                          from the two endpoints, which is a genuinely
                          DIFFERENT, END-EXCLUSIVE code path in vendored PLR
                          (``__getitem__``'s ``isinstance(identifier, slice)``
                          branch, using index-position ``range(start, stop)``)
                          -- that path is for real Python slice syntax
                          (``obj["A1":"H1"]``, two separate string args), not
                          for the single colon-containing STRING every real
                          mined call actually uses. Rejected 12/99 real
                          mined overlay_gen calls with a fabricated
                          "volume list len N != N-1 targets" error before
                          this fix. Prefer explicit identifier lists in
                          fixtures for readability regardless.
* ``{"x":..,"y":..,"z":..}`` structured Coordinate payload -> grounded
                          literal (param_namespace note on move destinations).

Every grounding is recorded as a :class:`Binding` -- the evidence row used by
the slot-agreement check ("every grounded arg in the executed call").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

__all__ = ["Binding", "GroundingError", "canonical_ref", "ground_ref", "ground_param"]


class GroundingError(KeyError):
    """A reference could not be resolved against the live deck."""


@dataclass(frozen=True)
class Binding:
    """One grounded argument of one executed call."""

    call_index: int
    tool: str
    arg: str          # canonical schema-side param name
    plr_arg: str | None  # vendored kwarg it was dispatched under (None = inert)
    ref: str          # the reference/value as written in the call
    kind: str         # "symbolic" | "literal"
    resolved: str     # human-readable resolution evidence


def ground_ref(ref: str, setup) -> list[Any]:
    """Resolve a ref string to a LIST of PLR objects against a SetupHandle."""
    if not isinstance(ref, str) or not ref.strip():
        raise GroundingError(f"invalid ref {ref!r}")
    base, _, tail = ref.partition(".")
    if base not in setup.resources:
        raise GroundingError(
            f"resource {base!r} not on deck (have: {sorted(setup.resources)})"
        )
    obj = setup.resources[base]
    if not tail:
        return [obj]
    # Well/spot addressing: pass the STRING through unchanged (bare id or
    # colon-range) so vendored ItemizedResource.__getitem__ takes its
    # string branch (get_items/expand_string_range, INCLUSIVE) -- do NOT
    # split on ':' and re-index with obj[a:b], which builds a Python slice
    # object and silently hits the END-EXCLUSIVE index-range branch instead
    # (260828 finding, see module docstring).
    try:
        items = obj[tail.strip()]
    except Exception as e:  # PLR raises ValueError/KeyError variants
        raise GroundingError(f"cannot address {ref!r} on {base!r}: {e}") from e
    return list(items)


def canonical_ref(ref: str) -> str:
    """Normalized form used when comparing executed vs intended bindings."""
    return " ".join(ref.split())


def _coordinate(value: Mapping[str, Any]) -> Any:
    from pylabrobot.resources import Coordinate

    return Coordinate(float(value["x"]), float(value["y"]), float(value["z"]))


def ground_param(call_index: int, tool: str, arg: str, plr_arg: str | None,
                 value: Any, kind: str, setup) -> tuple[Any, Binding]:
    """Ground ONE parameter value; returns (objects_or_value, binding).

    Symbolic values are ref strings/lists-of-refs and ground into PLR objects.
    Literal values pass through untouched.  Structured Coordinate payloads on
    symbolic params count as grounded literals (recorded convention).
    """
    if kind == "literal":
        return value, Binding(call_index, tool, arg, plr_arg,
                              canonical_ref(str(value)), "literal",
                              f"literal value {value!r}")
    if isinstance(value, Mapping):
        if {"x", "y", "z"} <= set(value.keys()):
            return _coordinate(value), Binding(
                call_index, tool, arg, plr_arg, canonical_ref(str(sorted(value.items()))),
                "literal", f"Coordinate payload -> {_coordinate(value)!r}")
        raise GroundingError(f"{tool}.{arg}: unsupported mapping payload {value!r}")

    refs = value if isinstance(value, list) else [value]
    grounded: list[Any] = []
    seen: list[str] = []
    for r in refs:
        if not isinstance(r, str):
            raise GroundingError(f"{tool}.{arg}: symbolic value must be ref string(s), got {r!r}")
        grounded.extend(ground_ref(r, setup))
        seen.append(canonical_ref(r))
    binding = Binding(call_index, tool, arg, plr_arg, ", ".join(seen), "symbolic",
                      f"{len(grounded)} object(s): {[getattr(g, 'name', type(g).__name__) for g in grounded]}")
    return grounded, binding
