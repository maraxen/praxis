"""FunctionGemma tool-declaration rendering FROM the namespace table.

Juror finding 6a ("missing declaration descriptions/type mappings"): training
rows need a ``tools[]`` block, so declarations are RENDERED here from
``coxswain.plr.param_namespace`` -- one declaration per phase-2-included tool,
descriptions authored once in this module, parameter schemas mapped
deterministically from the table's ``plr_type``/``kind``/``cardinality``
columns. Nothing is hand-duplicated: required lists come from
``required_params``; property names are the SCHEMA-side vocabulary the model
predicts (dispatch maps schema name -> vendored kwarg at execution time).
"""

from __future__ import annotations

from typing import Any, Final

from coxswain.plr.param_namespace import (
    PARAM_NAMESPACE,
    ParamKind,
    ParamSpec,
    params_of,
    required_params,
)
from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES

__all__ = ["render_declaration", "render_declarations"]

#: One-line description per included tool. Descriptions state units using the
#: pinned value-format vocabulary (uL, nanometers, A1-style positions).
_DESCRIPTIONS: Final[dict[str, str]] = {
    "aspirate": (
        "Aspirate liquid from source containers into the pipette channels. "
        "Volumes are in microliters (uL)."
    ),
    "dispense": (
        "Dispense liquid from the pipette channels into destination containers. "
        "Volumes are in microliters (uL)."
    ),
    "transfer": (
        "Transfer liquid from a source well to one or more destination wells in "
        "one motion. The volume is the dispense target per destination, in "
        "microliters (uL)."
    ),
    "stamp": (
        "Copy the full well map of a source plate onto a destination plate, "
        "transferring the given volume per well, in microliters (uL)."
    ),
    "pick_up_tips": "Pick up tips from the given tip-rack positions.",
    "drop_tips": "Drop the mounted tips into the given tip spots or trash.",
    "discard_tips": (
        "Discard the mounted tips to waste; an optional location may be named "
        "and is confirmed before execution."
    ),
    "move_resource": "Move a deck resource such as a reservoir or plate carrier to a new location.",
    "move_plate": "Move a plate to a new deck location.",
    "move_lid": "Move a plate lid to a new deck location.",
    "read_absorbance": (
        "Read the absorbance of the plate loaded in the reader at a wavelength "
        "in nanometers; optionally restrict to wells given as A1-style positions."
    ),
    "read_fluorescence": (
        "Read fluorescence of the loaded plate with excitation and emission "
        "wavelengths in nanometers and a focal height in millimeters; wells are "
        "optional A1-style positions."
    ),
    "read_luminescence": (
        "Read luminescence of the loaded plate at a focal height in millimeters; "
        "wells are optional A1-style positions."
    ),
}

#: Literal-param JSON-schema mapping keyed on the table's verbatim plr_type.
_LITERAL_JSON_TYPES: Final[dict[str, dict[str, Any]]] = {
    "float": {"type": "number"},
    "List[float]": {"type": "array", "items": {"type": "number"}},
    "Optional[List[float]]": {"type": "array", "items": {"type": "number"}},
    "Optional[list[str]]": {"type": "array", "items": {"type": "string"}},
    'Literal["tips"]': {"type": "string", "enum": ["tips"]},
    "str": {"type": "string"},
}


def _property_schema(spec: ParamSpec) -> dict[str, Any]:
    """Map one namespace row onto a FunctionGemma property schema."""
    if spec.kind is ParamKind.SYMBOLIC_RESOURCE_REF:
        # Symbolic refs arrive as user-facing strings grounded post-parse.
        if spec.cardinality == "list":
            return {"type": "array", "items": {"type": "string"}}
        return {"type": "string"}
    base = _LITERAL_JSON_TYPES.get(spec.plr_type)
    if base is None:
        raise KeyError(f"no JSON mapping for literal plr_type {spec.plr_type!r}")
    return dict(base)


def render_declaration(tool_name: str) -> dict[str, Any]:
    """Render ONE FunctionGemma tool declaration for an included tool.

    KeyError (loud) for unknown or excluded-from-phase-2 tools.
    """
    if tool_name not in PARAM_NAMESPACE:
        raise KeyError(f"{tool_name!r} is not in the canonical param namespace")
    properties = {
        spec.name: _property_schema(spec) for spec in params_of(tool_name)
    }
    return {
        "name": tool_name,
        "description": _DESCRIPTIONS[tool_name],
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": list(required_params(tool_name)),
        },
    }


def render_declarations(tool_names: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Render declarations for the given tools (default: the whole phase-2
    surface), in sorted-name order for determinism."""
    names = sorted(tool_names) if tool_names is not None else sorted(PHASE2_TOOL_NAMES)
    return [render_declaration(name) for name in names]
