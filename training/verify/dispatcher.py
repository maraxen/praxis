"""Call dispatch: canonical intent-record calls -> vendored PLR invocations.

Mapping is driven by coxswain.plr.param_namespace.PARAM_NAMESPACE (THE
canonical table): schema param name -> vendored kwarg + cardinality.  The
dispatcher never invents argument names.

STRICT-mode anomalies: PLR's own _check_args STRICT enforcement is inert for
backends whose methods accept ``**backend_kwargs`` (all chatterbox backends
do) -- extra kwargs would be silently swallowed.  The harness therefore
mirrors _check_args semantics itself: while global strictness is STRICT,
ANY param not present in the tool's canonical namespace raises TypeError
before dispatch ("Extra arguments ..."); under WARN it is forwarded into the
vendored **backend_kwargs channel and ignored by the chatterbox.  This is
the anomaly class AC-2.2.1's "STRICT anomalies fail" keys off; the global
set_strictness(STRICT) is still applied around every run and restored after.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from coxswain.plr.param_namespace import ParamKind, params_of

from verify.grounding import Binding, GroundingError, ground_param

__all__ = [
    "DispatchError",
    "PlanResult",
    "UnsupportedCallError",
    "plan_call",
]

#: LiquidHandler-receiver tools this harness can execute on a chatterbox LH.
#: read_* verbs are plate-reader-receiver calls (different machine); the
#: phase-2 receiver verification plan keeps them out of the LH harness.
SUPPORTED_TOOLS = frozenset({
    "pick_up_tips", "drop_tips", "discard_tips",
    "aspirate", "dispense", "transfer", "stamp",
    "move_resource", "move_plate", "move_lid",
})

_MOVE_OBJ_ARG = {"move_resource": "resource", "move_plate": "plate", "move_lid": "lid"}


class DispatchError(RuntimeError):
    """A call could not be mapped onto the vendored API."""


class UnsupportedCallError(DispatchError):
    """Tool exists in the schema but has no LH-chatterbox execution path."""


@dataclass
class PlanResult:
    """A grounded, mapped call ready to await."""

    index: int
    tool: str
    method: Any                 # bound LiquidHandler method
    kwargs: dict[str, Any] = field(default_factory=dict)
    bindings: list[Binding] = field(default_factory=list)
    #: plr_arg -> grounded PLR objects (evidence for post-condition math)
    touched: dict[str, list[Any]] = field(default_factory=dict)


def _rows(tool: str):
    try:
        return params_of(tool)
    except KeyError as e:
        raise UnsupportedCallError(
            f"tool {tool!r} is not in the phase-2 canonical namespace"
        ) from e


def _wrap_vols(count: int, vols: Any) -> list[float]:
    """Broadcast a scalar volume across channels; pass lists through."""
    if isinstance(vols, list):
        out = [float(v) for v in vols]
        if len(out) != count:
            raise DispatchError(f"volume list len {len(out)} != {count} targets")
        return out
    return [float(vols)] * count


def _single(objs: list[Any], label: str) -> Any:
    if len(objs) != 1:
        raise DispatchError(f"{label} grounds to exactly one object, got {len(objs)}")
    return objs[0]


def plan_call(call: Mapping[str, Any], index: int, setup, *, strict: bool) -> PlanResult:
    """Ground + map one call WITHOUT executing it."""
    tool = call.get("name")
    if not isinstance(tool, str):
        raise DispatchError(f"call #{index}: missing 'name'")
    if tool not in SUPPORTED_TOOLS:
        raise UnsupportedCallError(
            f"call #{index}: {tool!r} has no LiquidHandler-chatterbox "
            f"execution path (read_* verbs are plate-reader-receiver)"
        )
    rows = _rows(tool)
    known = {spec.name: spec for spec in rows}

    params = call.get("params") or {}
    unknown = [k for k in params if k not in known]
    if unknown and strict:
        # Mirrors PLR _check_args STRICT wording for backends without **kwargs;
        # under WARN these ride the backend_kwargs channel (chatterbox ignores).
        raise TypeError(f"Extra arguments to {tool}: {sorted(unknown)}")

    result = PlanResult(index=index, tool=tool,
                        method=getattr(setup.machine, tool))
    kwargs = result.kwargs
    touched = result.touched

    def bind(arg: str) -> None:
        spec = known[arg]
        kind = ("symbolic" if spec.kind is ParamKind.SYMBOLIC_RESOURCE_REF
                else "literal")
        value, binding = ground_param(
            index, tool, arg, spec.plr_arg, params.get(arg), kind, setup,
        )
        if spec.plr_arg is not None:
            if isinstance(value, list):
                kwargs[spec.plr_arg] = value
                touched[spec.plr_arg] = list(value)
            else:
                kwargs[spec.plr_arg] = value
                touched[spec.plr_arg] = [value]
        else:
            # dispatch-inert symbolic param (e.g. discard_tips.at): grounded
            # for slot-agreement evidence only, never handed to PLR.
            touched[f"inert:{arg}"] = value if isinstance(value, list) else [value]
        result.bindings.append(binding)

    def require(*args: str) -> None:
        missing = [a for a in args if a not in params]
        if missing:
            raise DispatchError(f"{tool}: missing required param(s) {missing}")

    if tool in ("aspirate", "dispense"):
        res_arg = "source" if tool == "aspirate" else "destination"
        require(res_arg, "volume_ul")
        bind(res_arg)
        bind("volume_ul")
        kwargs["vols"] = _wrap_vols(len(kwargs["resources"]), params["volume_ul"])

    elif tool == "transfer":
        require("source", "destination")
        bind("source")
        bind("destination")
        kwargs["source"] = _single(kwargs["source"], "transfer.source")
        if params.get("volume_ul") is not None:
            kwargs["target_vols"] = _wrap_vols(
                len(kwargs["targets"]), params["volume_ul"]
            )

    elif tool == "pick_up_tips":
        require("at")
        bind("at")

    elif tool == "drop_tips":
        require("destination")
        bind("destination")

    elif tool == "discard_tips":
        for inert in ("what", "at"):
            if inert in params:
                bind(inert)

    elif tool == "stamp":
        require("source", "destination", "volume_ul")
        bind("source")
        bind("destination")
        bind("volume_ul")  # plr_arg="volume" -> already lands in kwargs["volume"]
        # source/destination are scalar-cardinality symbolic refs, but
        # ground_param always returns a grounded LIST (one entry); vendored
        # stamp() wants bare Plates for both, mirroring the transfer.source
        # unwrap below.
        kwargs["source"] = _single(kwargs["source"], "stamp.source")
        kwargs["target"] = _single(kwargs["target"], "stamp.destination")
        kwargs["volume"] = float(_wrap_vols(1, params["volume_ul"])[0])

    elif tool in _MOVE_OBJ_ARG:
        obj_arg = _MOVE_OBJ_ARG[tool]
        require(obj_arg, "destination")
        bind(obj_arg)
        bind("destination")
        kwargs[obj_arg] = _single(kwargs[obj_arg], f"{tool}.{obj_arg}")
        if isinstance(kwargs["to"], list):
            kwargs["to"] = _single(kwargs["to"], f"{tool}.destination")
        # destination stays as-is otherwise: resource/holder object or Coordinate

    for k in unknown:
        kwargs.setdefault(k, params[k])

    return result
