"""Shape validation of mined calls and overlay rows against the P2.0 tables.

Every candidate row must be a namespace-legal call before it may enter the
overlay: tool name inside PHASE2_TOOL_NAMES, receiver type matching
TOOL_SCHEMA, params drawn from PARAM_NAMESPACE only, required params present,
cardinality and literal/symbolic kinds respected. Validation failures are
counted, never silently dropped -- an off-shape row that reaches P2.5 assembly
teaches the model a vocabulary that does not exist.
"""

from __future__ import annotations

from typing import Any

from coxswain.plr.param_namespace import (
    PARAM_NAMESPACE,
    ParamKind,
    params_of,
    required_params,
)
from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES, TOOL_SCHEMA

__all__ = ["validate_call", "validate_row"]

_ROW_REQUIRED_FIELDS: tuple[str, ...] = ("id", "instruction", "call", "provenance")
_PROVENANCE_REQUIRED_FIELDS: tuple[str, ...] = (
    "provenance",
    "source_notebook_or_protocol",
    "generator",
    "prompt_version",
    "teacher_model_version",
)


def validate_call(call: dict[str, Any]) -> list[str]:
    """Return the list of shape violations for one normalized call (empty ==
    legal). ``call`` is ``{"name", "receiver_type", "params"}``."""
    errors: list[str] = []
    name = call.get("name")
    if not isinstance(name, str) or name not in PHASE2_TOOL_NAMES:
        return [f"name {name!r} is not in the phase-2 surface"]

    spec = TOOL_SCHEMA[name]
    if call.get("receiver_type") != spec.receiver_type:
        errors.append(
            f"receiver_type {call.get('receiver_type')!r} != schema "
            f"{spec.receiver_type!r} for {name}"
        )

    params = call.get("params")
    if not isinstance(params, dict):
        errors.append(f"params must be a dict, got {type(params).__name__}")
        return errors

    known = {ps.name for ps in params_of(name)}
    unknown = sorted(set(params) - known)
    if unknown:
        errors.append(f"params outside namespace for {name}: {unknown}")

    missing = [p for p in required_params(name) if p not in params]
    if missing:
        errors.append(f"missing required params for {name}: {missing}")

    for ps in params_of(name):
        if ps.name not in params:
            continue
        value = params[ps.name]
        is_list = isinstance(value, list)
        if ps.cardinality == "list" and not is_list:
            errors.append(f"{name}.{ps.name}: cardinality list but value is scalar")
        if ps.cardinality == "scalar" and is_list:
            errors.append(f"{name}.{ps.name}: cardinality scalar but value is list")
        values = value if is_list else [value]
        for v in values:
            if not isinstance(v, (str, int, float, bool)):
                errors.append(
                    f"{name}.{ps.name}: unsupported value type {type(v).__name__}"
                )
                break
        if ps.kind is ParamKind.SYMBOLIC_RESOURCE_REF and not all(
            isinstance(v, str) for v in values
        ):
            errors.append(f"{name}.{ps.name}: symbolic ref must be string-valued")
    return errors


def validate_row(row: dict[str, Any]) -> list[str]:
    """Validate one candidate overlay row: envelope fields + provenance tags +
    the embedded call shape."""
    errors: list[str] = []
    for field in _ROW_REQUIRED_FIELDS:
        if field not in row:
            errors.append(f"row missing required field {field!r}")
    instruction = row.get("instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        errors.append("instruction must be a non-empty string")
    prov = row.get("provenance")
    if not isinstance(prov, dict):
        errors.append("provenance must be a dict")
    else:
        for field in _PROVENANCE_REQUIRED_FIELDS:
            if field not in prov or not str(prov.get(field, "")).strip():
                errors.append(f"provenance missing/blank {field!r}")
        if prov.get("provenance") not in (None, "naturalness"):
            # None tolerated only because the blank-check above already fires.
            errors.append(
                f"provenance.provenance must be 'naturalness', got {prov.get('provenance')!r}"
            )
    call = row.get("call")
    if isinstance(call, dict):
        errors.extend(validate_call(call))
    else:
        errors.append("call must be a dict")
    return errors


def namespace_summary() -> dict[str, int]:
    """Tiny introspection helper used by smoke reports."""
    return {
        "phase2_tools": len(PHASE2_TOOL_NAMES),
        "namespace_tools": len(PARAM_NAMESPACE),
    }
