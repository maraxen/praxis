"""Tier-2a source renderer (spec 260903 `260903_plr-sema-real-programs-
increment.md` §12.4.1, backlog #4880): render one executed corpus row's
call sequence to a minimal Python protocol source, faithful enough that
praxis's extractor -> ``lower_graph`` produces the SAME bytecode
``lower_calls`` produces for the same row -- the bytecode differential
``plr-sema/eval/tier2_extractor.py`` runs.

**Resources become typed parameters** of the rendered function, because
``_initialize_resources_from_params``
(``praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:278-298``)
is what turns a parameter's type hint into a ``ResourceNode`` -- an
untyped/unparameterized resource is invisible to the extractor. The type
used for each parameter is the REAL PLR class the runtime actually bound
(:func:`oracle_common.resource_type_of`, threaded through
:attr:`oracle_common.RuntimeOutcome.resource_types`), not a guess from
``deck_layout`` -- most referenced resources (the mined utterance's own
plate/tip rack) are never IN ``deck_layout.resources``, which carries only
the scaffolding's OWN additions (e.g. ``prime_plate``); see
:func:`oracle_common.resource_types_from_kwargs`'s own docstring for why.

Each call renders as ``await lh.<method>(<plr_param>=<value>, ...)`` --
PLR method parameter names taken from the bound ``PlanResult.kwargs``, the
SAME dict ``lower_calls`` reads (``oracle_common.calls_from_plr_kwargs``)
-- so the renderer never invents a name and the tool-name barrier
(§11.2.3) is respected by construction, and ALWAYS as a keyword argument
(never positional), which is what lets the extractor's own
``_extract_arguments`` (``arg.keyword.value``) recover the exact PLR param
name rather than falling back to its positional-index heuristic
(``common_arg_names``). The scaffolding reset (§12.1.6) renders as the
literal line ``await lh.setup()``.

A kwarg value the renderer cannot express as Python source (anything
outside ``{lit, ref, seq-of-{lit,ref}}``, or a ``ref`` naming a resource
whose runtime type this module never captured) is DROPPED from the
rendered call and recorded as a :class:`Residual` -- the "renderer"
divergence cause (§12.4.1's table) -- never invented, never silently
coerced to something else.

**Non-identifier resource names (backlog #4949, 260903 tier2a followup):**
a resource whose real runtime NAME is not a valid Python identifier (e.g.
``"plate_carrier-1"``, the dominant residual class found in the 260903
full-corpus run -- 122/122 renderer residuals, all of this one shape) is
no longer dropped. It gets a sanitised, collision-safe PARAMETER name
(:func:`_make_param_names` -- ``"plate_carrier-1"`` -> ``"plate_carrier_1"``)
and is declared and referenced under that name; :attr:`RenderedProtocol.
name_map` (``{original_name: sanitised_name}``) is returned alongside the
source so a caller comparing tier-1 (which only ever sees the ORIGINAL
name) against tier-2 (extracted from source that only ever sees the
SANITISED name) can translate back -- see
``tier2_extractor.compare_bytecode``'s ``resource_name_map`` parameter.
A non-identifier WELL/CELL subscript (the ``cell`` half of a ``ref``, e.g.
``res["A-1"]``) needed no such fix: it was never rendered as an
identifier in the first place -- ``_render_value`` already emits it as a
``repr``'d string literal inside the extractor's own subscript grammar
(``res[<literal>]``), which is valid Python for ANY string.

This module imports nothing from ``praxis`` and nothing from
``plr_sema.check`` -- it consumes and produces plain Python/JSON, matching
the rest of ``plr-sema/eval/``'s import-boundary discipline (AC-12.16).
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Mapping
from typing import Any

__all__ = [
    "Residual",
    "RenderedProtocol",
    "render_protocol",
    "classify_residual_reason",
    "RESIDUAL_UNKNOWN_RESOURCE",
    "RESIDUAL_UNRENDERABLE_VALUE_KIND",
    "RESIDUAL_OTHER",
]

_RECEIVER_NAME = "lh"
_RECEIVER_TYPE = "LiquidHandler"

#: :func:`classify_residual_reason`'s controlled vocabulary (backlog #4949,
#: 260903 tier2a followup) -- published as ``renderer_residual_by_class`` in
#: the tier2a report. ``RESIDUAL_UNKNOWN_RESOURCE``: a ``ref`` names a
#: resource this module never captured a runtime PLR type for (so it was
#: never declared a function parameter, identifier-validity aside).
#: ``RESIDUAL_UNRENDERABLE_VALUE_KIND``: a kwarg value's ``k`` is outside
#: ``{lit, ref, seq}`` -- no Python literal form exists for it at all.
#: ``RESIDUAL_OTHER``: defensive catch-all; not expected to fire for any
#: reason string this module itself produces (both classes above are
#: exhaustive over :func:`_render_value`'s own failure branches), kept so a
#: future new failure mode is counted rather than silently misclassified.
RESIDUAL_UNKNOWN_RESOURCE = "unknown_resource"
RESIDUAL_UNRENDERABLE_VALUE_KIND = "unrenderable_value_kind"
RESIDUAL_OTHER = "other"

_UNKNOWN_RESOURCE_MARKER = "has no captured runtime PLR type"
_UNRENDERABLE_KIND_MARKER = "unrenderable value kind"

_NON_IDENTIFIER_CHARS = re.compile(r"[^0-9a-zA-Z_]")


def classify_residual_reason(reason: str) -> str:
    """One of :data:`RESIDUAL_UNKNOWN_RESOURCE` /
    :data:`RESIDUAL_UNRENDERABLE_VALUE_KIND` / :data:`RESIDUAL_OTHER`, from
    a :attr:`Residual.reason` string. A substring match, not a structured
    field on :class:`Residual`, because both marker strings are produced
    exclusively by THIS module (:func:`_render_value` / :func:`render_protocol`
    below) -- there is exactly one place either could drift out of sync
    with this function, and it is in this same file.
    """
    if _UNKNOWN_RESOURCE_MARKER in reason:
        return RESIDUAL_UNKNOWN_RESOURCE
    if _UNRENDERABLE_KIND_MARKER in reason:
        return RESIDUAL_UNRENDERABLE_VALUE_KIND
    return RESIDUAL_OTHER


def _sanitize_identifier(name: str) -> str:
    """Best-effort valid Python identifier from an arbitrary resource NAME
    string: every character outside ``[0-9a-zA-Z_]`` becomes ``_`` (so
    ``"tip-rack-1"`` -> ``"tip_rack_1"``, the spec's own worked example),
    and a result that would not be a valid identifier standing alone
    (empty, or starting with a digit) is prefixed with ``_``.
    Collision-safety across the whole resource set is
    :func:`_make_param_names`'s job, not this function's -- this is a pure
    per-name transform.
    """
    s = _NON_IDENTIFIER_CHARS.sub("_", name)
    if not s or s[0].isdigit():
        s = f"_{s}"
    return s


def _make_param_names(resource_types: Mapping[str, str]) -> dict[str, str]:
    """``{original_resource_name: sanitised_python_identifier}`` for every
    entry in ``resource_types`` (the receiver ``lh`` excluded -- it is
    never itself a resource-typed parameter). Collision-safe: if two
    distinct original names sanitise to the same identifier, or a
    sanitised name collides with an already-valid resource name (or with
    ``lh``), later entries get a numeric suffix (``foo``, ``foo_2``,
    ``foo_3``, ...). Iterates ``resource_types`` in its own (insertion,
    i.e. first-planned-kwarg) order, so the mapping is deterministic for a
    given row.
    """
    used: set[str] = {_RECEIVER_NAME}
    out: dict[str, str] = {}
    for name in resource_types:
        if name == _RECEIVER_NAME:
            continue
        base = name if name.isidentifier() else _sanitize_identifier(name)
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        used.add(candidate)
        out[name] = candidate
    return out


@dataclasses.dataclass(frozen=True, slots=True)
class Residual:
    """One kwarg the renderer could not express as Python source."""

    call_index: int
    method: str
    kwarg: str
    reason: str


@dataclasses.dataclass(frozen=True, slots=True)
class RenderedProtocol:
    source: str
    function_name: str
    residuals: tuple[Residual, ...]
    #: call_index (position in the ``calls`` list this was rendered from,
    #: ``0`` == the prepended setup) -> 1-based source line of that call's
    #: ``await lh.<method>(...)`` line, for divergence reports (AC-12.15's
    #: "source line" requirement).
    call_lines: Mapping[int, int]
    #: ``{original_resource_name: sanitised_python_identifier}``
    #: (:func:`_make_param_names`) -- identity (``{n: n}``) for every
    #: already-identifier name, a real rewrite for the rest. A caller
    #: comparing tier-1 (original names) against tier-2 (extracted from
    #: source that only ever saw the sanitised names) needs this to
    #: translate back; see ``tier2_extractor.compare_bytecode``'s
    #: ``resource_name_map`` parameter.
    name_map: Mapping[str, str]


def _render_lit(v: Any) -> str:
    """A JSON scalar (``None``/``bool``/``int``/``float``/``str``) as a
    Python literal. ``repr`` round-trips all five through ``ast.literal_eval``
    (what ``lower_graph``'s ``_lower_ast_node`` uses on a non-resource,
    non-subscript, non-list/tuple node).
    """
    return repr(v)


def _render_value(
    value: Mapping[str, Any], *, path: str, reasons: list[str], name_map: Mapping[str, str],
) -> str | None:
    """``name_map`` is ``{original_resource_name: sanitised_python_identifier}``
    (:func:`_make_param_names`) -- a ``ref`` renders under the SANITISED
    name (the identifier actually declared as a function parameter), never
    the raw runtime name, so a non-identifier name like
    ``"plate_carrier-1"`` no longer needs an identifier check here at all:
    membership in ``name_map`` (== "this module captured a runtime PLR
    type for it and declared it a parameter",
    :func:`render_protocol`'s own param-declaration loop) is the only
    renderability test, for BOTH top-level and nested (inside a ``seq``)
    refs alike.
    """
    k = value.get("k") if isinstance(value, Mapping) else None
    if k == "lit":
        return _render_lit(value.get("v"))
    if k == "ref":
        name = value.get("name")
        if not isinstance(name, str) or name not in name_map:
            reasons.append(
                f"{path}: ref name {name!r} {_UNKNOWN_RESOURCE_MARKER} "
                "(oracle_common.resource_types_from_kwargs)"
            )
            return None
        cell = value.get("cell")
        param_name = name_map[name]
        return f"{param_name}[{cell!r}]" if cell is not None else param_name
    if k == "seq":
        items = value.get("items") or []
        rendered_items: list[str] = []
        for i, item in enumerate(items):
            rendered = _render_value(item, path=f"{path}[{i}]", reasons=reasons, name_map=name_map)
            if rendered is None:
                return None
            rendered_items.append(rendered)
        return f"[{', '.join(rendered_items)}]"
    reasons.append(f"{path}: {_UNRENDERABLE_KIND_MARKER} {k!r} (not lit/ref/seq)")
    return None


def render_protocol(
    calls: list[dict[str, Any]],
    resource_types: Mapping[str, str],
    *,
    function_name: str = "protocol",
) -> RenderedProtocol:
    """Render ``calls`` (:func:`oracle_common.calls_from_plr_kwargs`'s own
    output -- ``calls[0]`` is always the prepended scaffolding ``setup()``,
    §12.1.6) plus ``resource_types``
    (:attr:`oracle_common.RuntimeOutcome.resource_types`) to a minimal
    Python protocol source.

    A resource name referenced by a kwarg ``ref`` but absent from
    ``resource_types`` is treated exactly like any other unrenderable
    value (a residual on that kwarg, not a crash and not a fabricated
    type) -- it simply never becomes a function parameter, so the
    extractor cannot see it as a resource either, which is the correct,
    conservative behaviour: better an honest residual than a guessed type
    that could itself be the source of a spurious divergence.

    A resource whose real runtime NAME is not a valid Python identifier
    (e.g. ``"plate_carrier-1"``, backlog #4949's dominant residual class --
    122/122 in the 260903 full-corpus run) is no longer skipped: it gets a
    sanitised, collision-safe parameter name
    (:func:`_make_param_names`/:attr:`RenderedProtocol.name_map`) and is
    declared and referenced under THAT name -- declaring the raw name
    would produce a SyntaxError that kills libcst's parse of the whole
    rendered protocol (found live, 260903 full-corpus run: 95/235 executed
    rows, before this fix).
    """
    name_map = _make_param_names(resource_types)
    render_name_map = dict(name_map)
    render_name_map[_RECEIVER_NAME] = _RECEIVER_NAME

    params = [f"{_RECEIVER_NAME}: {_RECEIVER_TYPE}"]
    for name, cls in resource_types.items():
        if name == _RECEIVER_NAME:
            continue
        params.append(f"{name_map[name]}: {cls}")

    lines = [f"async def {function_name}({', '.join(params)}):"]
    residuals: list[Residual] = []
    call_lines: dict[int, int] = {}

    for i, call in enumerate(calls):
        method = call.get("method", "")
        if method == "setup":
            call_lines[i] = len(lines) + 1
            lines.append(f"    await {_RECEIVER_NAME}.setup()")
            continue
        kwargs = call.get("kwargs") or {}
        parts: list[str] = []
        for k, v in kwargs.items():
            reasons: list[str] = []
            name = v.get("name") if isinstance(v, Mapping) and v.get("k") == "ref" else None
            if name is not None and name not in resource_types and name != _RECEIVER_NAME:
                residuals.append(
                    Residual(
                        call_index=i, method=method, kwarg=k,
                        reason=f"call[{i}].{method}.{k}: resource {name!r} "
                                f"{_UNKNOWN_RESOURCE_MARKER} "
                                "(oracle_common.resource_types_from_kwargs)",
                    )
                )
                continue
            rendered = _render_value(v, path=f"call[{i}].{method}.{k}", reasons=reasons, name_map=render_name_map)
            if rendered is None:
                residuals.append(
                    Residual(
                        call_index=i, method=method, kwarg=k,
                        reason=reasons[-1] if reasons else "unrenderable",
                    )
                )
                continue
            parts.append(f"{k}={rendered}")
        call_lines[i] = len(lines) + 1
        lines.append(f"    await {_RECEIVER_NAME}.{method}({', '.join(parts)})")

    if len(lines) == 1:
        lines.append("    pass")

    source = "\n".join(lines) + "\n"
    return RenderedProtocol(
        source=source, function_name=function_name,
        residuals=tuple(residuals), call_lines=call_lines, name_map=name_map,
    )
