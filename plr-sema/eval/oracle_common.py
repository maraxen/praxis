"""Shared oracle infrastructure: runtime/static/compare pipeline.

Factored from plr-sema/scripts/oracle_spike.py (260902 spike). This module is
imported by both the oracle_spike.py worked example and the tier-1 corpus-replay
harness (oracle_replay.py). Module-level imports avoid plr_sema.src.* (a
circular-dependency hazard at IMPORT TIME, not a boundary the import-boundary
test enforces here -- that test is scoped to src/plr_sema/, and eval/ is
explicitly permitted to import pylabrobot/training.verify/plr_sema, spec
§11.2.2's "Where it lives"); every plr_sema import below is therefore done
LAZILY, inside a function body, after inserting plr-sema/src onto sys.path
-- the same pattern this module already used for check_graph before 260902.

260902 (spec §11, SEMA-IR): ``adapt_graph`` is DELETED. The corpus path now
lowers through :func:`plr_sema.check.ir.lower_calls` over PLR-named,
already-grounded kwargs (:func:`ir_value_of`, harvested by
:func:`run_runtime`'s ``recording_plan_call`` wrapper) instead of adapting a
call sequence into a §6.2 graph payload keyed by tool-named/guessed
argument names. ``run_static`` (the graph-payload path, still used by a
future tier-2 source-render harness) is UNCHANGED; :func:`run_static_calls`
is its new sibling for the ``lower_calls`` path.
"""

from __future__ import annotations

import asyncio
import collections
import contextlib
import dataclasses
import functools
import hashlib
import io
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)

#: (#4976, band B0, UNKNOWN ledger): an optional observer over
#: :func:`run_static_calls`'s own per-row findings, installed by
#: ``plr-sema/eval/unknown_ledger.py``. When set, ``run_static_calls`` calls
#: ``FINDINGS_SINK(row_id, findings)`` once per invocation -- ``findings`` is
#: the SAME relabelled, setup-pc-excluded tuple of real ``Finding`` objects
#: (:class:`plr_sema.verdict.Finding`) that call collapses into its returned
#: ``per_op`` summary immediately afterward, keyed by the row's own
#: ``intent_record["record_id"]`` (the content-digest id every corpus row
#: already carries, :func:`content_digest`) or ``""`` when ``example`` has
#: no ``intent_record`` (a caller/test that builds a bare ``example`` dict,
#: e.g. this module's own doctests and ``tests/test_oracle_replay.py``'s
#: synthetic fixtures). Default is ``None`` (no observer): every existing
#: caller of ``run_static_calls`` (``oracle_replay.py``, ``tip_mutants.py``,
#: ``scripts/oracle_spike.py``, and this repo's own tests) is therefore
#: byte-identical in behaviour and return value whether or not this module
#: has ever been imported by the ledger -- this is purely an ADDITIVE
#: observation seam, never a control-flow change, and it does not
#: monkeypatch ``check_ir`` or anything else. See ``run_static_calls``'s own
#: docstring for the exact point in its pipeline this fires.
FindingsSink = Callable[[str, "tuple[Any, ...]"], None]
FINDINGS_SINK: FindingsSink | None = None

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACTS = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json"


# --------------------------------------------------------------------------
# content-digest identity (#4939 follow-up, 260903): the 260902->260903
# corpus regrew 900->1427 rows via MID-FILE insertion (natural-phrasing
# lane, assembly 0.1.4/0.1.5), which silently invalidated every
# line-number-keyed record_id ("{source_stem}:{line}") and every test
# fixture that hardcoded a line number to reach a specific row -- the row
# formerly at that line moved. A content digest over (utterance, first
# tool call) is stable across insertion/reordering; ``line`` is kept
# alongside it purely as a display field, not an identity key.
# --------------------------------------------------------------------------


def extract_first_call(row: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    """First user utterance + first assistant tool call (name, params) from
    a corpus ``messages``-format row. A narrower, identity-only sibling of
    :func:`row_to_verifier_inputs`'s own message-parsing loop -- kept
    separate (not shared code) so callers that only need row IDENTITY
    (e.g. a ``--sidecar`` content-digest lookup, done BEFORE
    :func:`row_to_verifier_inputs` runs and without a contracts_json /
    ambiguity_class context) don't need the full parse. Mirrors that
    loop's own tool_calls[0] extraction exactly, so a digest computed here
    and one computed from :func:`row_to_verifier_inputs`'s own
    ``user_message_content``/``real_call`` locals agree for the same row.
    """
    utterance = ""
    call: dict[str, Any] | None = None
    for msg in row.get("messages", []):
        if msg.get("role") == "user":
            utterance = msg.get("content", "")
        elif msg.get("role") == "assistant" and call is None:
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                func = tool_calls[0].get("function", {})
                call = {"name": func.get("name", ""), "params": func.get("arguments", {})}
    return utterance, call


def content_digest(utterance: str, call: dict[str, Any] | None) -> str:
    """``sha256(utterance + "\\n" + canonical JSON of the tool call))[:16]``.

    ``call`` is a single ``{"name": ..., "params": ...}`` dict (or
    ``None`` for a no-call row) -- every row in this corpus pipeline
    carries exactly one ground-truth tool call (``row_to_verifier_inputs``'s
    own "corpus has 1 call per row" comment), so there is no list-of-calls
    ordering question to canonicalize. ``json.dumps(..., sort_keys=True)``
    recursively sorts nested dict keys too, so ``params`` key order never
    perturbs the digest. NOT collision-free: 58/1427 corpus_p25.jsonl rows
    (260903) share a digest with >=1 other row (template-generated
    utterances repeat); ``record_id`` is therefore a content key, not a
    guaranteed-unique primary key -- ``line`` remains the disambiguator
    when one is needed.
    """
    canon = json.dumps(call, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{utterance}\n{canon}".encode("utf-8")).hexdigest()[:16]


def _import_param_namespace():
    """``training/`` and its ``coxswain`` dependency install top-level."""
    from coxswain.plr.param_namespace import ParamKind, params_of

    return ParamKind, params_of


def _import_overlay_normalizers():
    """overlay_gen's own mined-call normalizers (T16d, #4879): naturalness-
    provenance corpus rows carry VERBATIM MINED SOURCE EXPRESSIONS in their
    tool-call params (e.g. ``plate["C1"]``, ``sample_volume_ul * 0.8``, a
    bare loop-variable slice) -- see overlay_gen/exec_verify.py's module
    docstring. Reused directly rather than duplicated (unlike floor_gen's
    _precondition_plan, which oracle_common intentionally re-implements):
    these are regex-driven and importing avoids drift on the grounding
    grammar. Prior to this fix, oracle_common fed these raw expressions
    straight into _precondition_plan/the dispatcher, producing spurious
    TypeErrors (float() on a variable-name string) and "'Plate' object has
    no attribute 'tracker'" (an un-normalized ``plate["C1"]`` ref treated as
    one opaque resource name instead of grounding to ``plate.C1``) on rows
    overlay_gen's own harness would have skipped as ungroundable-from-source.
    """
    from overlay_gen.exec_verify import _normalize_params

    return _normalize_params


def _import_verifier():
    """``training/`` installs its subpackages top-level (``verify``), but be
    tolerant of the namespace form too.
    """
    try:
        import verify.verifier as v  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        import training.verify.verifier as v  # type: ignore[import-not-found,no-redef]
    return v


# --------------------------------------------------------------------------
# runtime side
# --------------------------------------------------------------------------


def ir_value_of(obj: Any) -> dict[str, Any]:
    """§11.2.2: maps a bound PLR object (a ``PlanResult.kwargs`` value) to
    IR value JSON -- :func:`plr_sema.check.ir.lower_calls`'s pre-slot-
    resolution wire shape. A ``Resource`` with a parent -> ``{"k": "ref",
    "name": <parent's name>, "cell": <this object's own name>}``; a
    top-level ``Resource`` -> ``{"k": "ref", "name": <this object's name>,
    "cell": null}``; a ``list``/``tuple`` -> ``{"k": "seq", "items": [...]}``
    recursively; a JSON scalar (``None``/``bool``/``int``/``float``/``str``)
    -> ``{"k": "lit", "v": ...}``; anything else -> ``{"k": "top"}``.

    ``Ref`` is NAME-keyed here, not slot-keyed: at harvest time (inside
    :func:`run_runtime`, one call at a time) there is no cross-call slot
    registry to assign integers against yet -- slot assignment is
    ``lower_calls``'s own job (mirroring ``lower_graph``'s first-appearance
    ordering), the same resolved ambiguity :func:`plr_sema.check.ir.
    lower_calls`'s docstring records.

    Replaces the pre-260902 harvest's ``repr(v)`` (`oracle_common.py:87-93`,
    pre-increment): a ``repr`` of a list of ``TipSpot``s is a string like
    ``"[<TipSpot ...>, <TipSpot ...>]"``, which carries no recoverable
    arity without re-parsing angle-bracket reprs and which
    ``ast.literal_eval`` rejects outright (spec §11.2.2's "one correction
    to the existing harvest, and it is not cosmetic").
    """
    if isinstance(obj, (list, tuple)):
        return {"k": "seq", "items": [ir_value_of(o) for o in obj]}
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return {"k": "lit", "v": obj}
    try:
        from pylabrobot.resources import Resource as _PLRResource
    except ImportError:  # pragma: no cover - pylabrobot always installed in eval/'s env
        _PLRResource = ()
    if _PLRResource and isinstance(obj, _PLRResource):
        parent = getattr(obj, "parent", None)
        if parent is not None:
            return {"k": "ref", "name": getattr(parent, "name", str(parent)), "cell": getattr(obj, "name", None)}
        return {"k": "ref", "name": getattr(obj, "name", str(obj)), "cell": None}
    return {"k": "top"}


#: §12.4.1 (#4880): the SAME generic vocabulary praxis's extractor
#: recognizes via ``praxis.common.type_inspection.PLR_RESOURCE_TYPES``
#: (word-boundary regex match over a type-HINT string,
#: ``_initialize_resources_from_params`` -> ``extract_resource_types``) --
#: duplicated here, not imported, because ``plr-sema/eval/`` may not
#: import ``praxis`` outside ``extract_runner.py``'s own subprocess
#: (AC-12.16). A VENDOR SUBCLASS name (e.g. ``HamiltonSTARDeck``) never
#: appears as a whole word inside that regex's pattern space ("Deck" is
#: preceded by "R", a word character, so ``\\b`` never matches there) --
#: found live in the 260903 full-corpus run: every ``move_resource`` row
#: rendered ``deck: HamiltonSTARDeck`` (the exact runtime class), which the
#: extractor's own ``_initialize_resources_from_params`` silently never
#: registered as a resource at all, producing 62 Top-vs-Ref divergences
#: that LOOKED like ``lower_graph``'s value-grammar gap (§12.2.5's closed
#: ``self.<attr>`` case) but were actually this renderer choosing too
#: specific a type hint for a parameter the extractor's recognizer cannot
#: see. Kept intentionally small and copied verbatim from the source list
#: (not derived) -- see that module's own docstring for why derivation was
#: rejected there; the same caution applies to a second, independent copy.
_PLR_GENERIC_RESOURCE_NAMES: frozenset[str] = frozenset({
    "Well", "TipSpot", "Spot", "Tube", "Plate", "TipRack", "Trough", "TubeRack",
    "Container", "PlateCarrier", "TipCarrier", "TroughCarrier", "Carrier",
    "CarrierSite", "Deck", "Slot", "Resource", "Lid", "LiquidHandler",
    "PlateReader", "HeaterShaker", "Shaker", "TemperatureController",
    "Centrifuge", "Thermocycler", "Pump", "PumpArray", "Fan", "Sealer",
    "Peeler", "PowderDispenser", "Incubator", "SCARA", "Machine",
})


def _generic_plr_type_name(obj: Any) -> str:
    """The most-specific ancestor class of ``obj`` whose NAME is in
    :data:`_PLR_GENERIC_RESOURCE_NAMES`, walked via ``type(obj).__mro__``
    (most to least specific). Falls back to ``type(obj).__name__`` (the
    concrete class) when nothing in the MRO matches -- an honest "no
    generic name known for this", not a crash; the renderer still tries
    the concrete name (better than omitting the parameter outright), and
    any resulting divergence is exactly what this increment exists to
    surface.
    """
    for cls in type(obj).__mro__:
        if cls.__name__ in _PLR_GENERIC_RESOURCE_NAMES:
            return cls.__name__
    return type(obj).__name__


def resource_type_of(obj: Any) -> tuple[str, str] | None:
    """§12.4.1 (#4880): ``(name, plr_type_hint)`` for the RESOURCE a bound
    PLR object ultimately belongs to -- mirrors :func:`ir_value_of`'s own
    "parent wins" rule (a cell reference's resource identity is its
    PARENT's name), but returns a type-hint string the extractor's own
    ``_initialize_resources_from_params`` can actually recognize
    (:func:`_generic_plr_type_name`), which ``ir_value_of``'s IR-value JSON
    deliberately does not carry (the grounded VALUE representation has no
    use for it -- only tier 2's renderer, which needs a real Python
    type-hint string for the resource's function-parameter annotation,
    does). Returns ``None`` for a non-``Resource`` (e.g. a bare literal).
    """
    try:
        from pylabrobot.resources import Resource as _PLRResource
    except ImportError:  # pragma: no cover - pylabrobot always installed in eval/'s env
        return None
    if not isinstance(obj, _PLRResource):
        return None
    parent = getattr(obj, "parent", None)
    target = parent if parent is not None else obj
    name = getattr(target, "name", None)
    if name is None:
        return None
    return name, _generic_plr_type_name(target)


def element_types_from_kwargs(kwargs: Mapping[str, Any]) -> dict[str, set[str]]:
    """O1's new element walk (spec 260904 §15.4, T30b) -- run ALONGSIDE
    :func:`resource_types_from_kwargs`, never replacing it. Records, per
    PARENT resource name, the RAW set of ``_generic_plr_type_name`` of each
    contained ELEMENT'S OWN class -- the opposite of
    :func:`resource_type_of`'s parent-wins rule, which discards exactly
    this information. An object with NO parent contributes nothing here:
    it has no ambiguity for ``element_type`` to resolve, since
    :func:`resource_types_from_kwargs` already names its own concrete class
    directly under its own name.

    Returns the RAW per-parent sets (not yet reduced to a singleton-or-
    ``None`` decision) so a caller can inspect heterogeneity directly; see
    :func:`element_type_singletons` for the fail-closed reduction (§15.4's
    heterogeneous-parent rule, C11b).
    """
    out: dict[str, set[str]] = {}
    try:
        from pylabrobot.resources import Resource as _PLRResource
    except ImportError:  # pragma: no cover - pylabrobot always installed in eval/'s env
        return out

    def walk(v: Any) -> None:
        if isinstance(v, (list, tuple)):
            for item in v:
                walk(item)
            return
        if not isinstance(v, _PLRResource):
            return
        parent = getattr(v, "parent", None)
        if parent is None:
            return  # no parent -> no ambiguity for element_type to resolve.
        parent_name = getattr(parent, "name", None)
        if parent_name is None:
            return
        out.setdefault(parent_name, set()).add(_generic_plr_type_name(v))

    for v in kwargs.values():
        walk(v)
    return out


def element_type_singletons(element_sets: Mapping[str, set[str]]) -> dict[str, str | None]:
    """The heterogeneous-parent rule (§15.4, C11b): ``element_type`` is the
    SET's single member iff it is a singleton, ``None`` (fail-closed)
    otherwise -- including an EMPTY set, which cannot occur from
    :func:`element_types_from_kwargs`'s own construction (a key is only
    ever ``setdefault``'d alongside an element) but is handled the same way
    defensively.
    """
    return {name: (next(iter(s)) if len(s) == 1 else None) for name, s in element_sets.items()}


def resource_types_from_kwargs(kwargs: Mapping[str, Any]) -> dict[str, str]:
    """Walk one call's RAW (pre-:func:`ir_value_of`) ``PlanResult.kwargs``
    values -- scalars, ``Resource``s, and lists/tuples thereof -- and return
    ``{resource_name: plr_class_name}`` for every resource reachable from
    them.

    Used by ``plr-sema/eval/render_protocol.py`` (§12.4.1) to type the
    rendered protocol's parameters with the SAME class the runtime actually
    bound, rather than guessing from ``deck_layout`` (which only carries the
    scaffolding's OWN additions, e.g. ``prime_plate`` -- most referenced
    resources, e.g. the mined utterance's own plate/tip rack, are never in
    it: ``_precondition_plan`` never populates ``extra_resources`` for them,
    and ``training/verify``'s own ``infer_layout()`` silently defaults every
    other unrecognized name to a bare ``Plate`` at RUNTIME, a decision this
    function does not need to replicate because it reads the real bound
    object instead of guessing).
    """
    out: dict[str, str] = {}

    def walk(v: Any) -> None:
        if isinstance(v, (list, tuple)):
            for item in v:
                walk(item)
            return
        found = resource_type_of(v)
        if found is not None:
            name, cls = found
            out.setdefault(name, cls)

    for v in kwargs.values():
        walk(v)
    return out


@dataclasses.dataclass
class RuntimeOutcome:
    error: str | None
    exc_class: str | None
    failing_index: int | None  # index of the call being executed when it raised
    planned_indices: list[int]
    passed: bool
    #: index -> {plr_param: <IR value JSON>} (ir_value_of, §11.2.2) -- PLR-named
    #: by construction (PlanResult.kwargs is written by plan_call's bind
    #: closure under spec.plr_arg, training/verify/dispatcher.py:117-135).
    plr_kwargs: dict[int, dict[str, Any]] = dataclasses.field(default_factory=dict)
    #: §12.4.1 (#4880): {resource_name: plr_class_name}, merged across every
    #: planned call's RAW kwargs (:func:`resource_types_from_kwargs`) -- the
    #: renderer's only source of truth for what type to annotate a rendered
    #: protocol's resource parameters with.
    resource_types: dict[str, str] = dataclasses.field(default_factory=dict)
    #: 260904 (spec §15.4, O1, T30b): {parent_resource_name: element_type
    #: or None}, merged across every planned call's RAW kwargs
    #: (:func:`element_types_from_kwargs`, reduced per parent by
    #: :func:`element_type_singletons`) -- the "the SET is a singleton"
    #: fail-closed rule, C11b, applied ACROSS the whole row (a parent seen
    #: with a homogeneous element set on one call and a heterogeneous one
    #: on another degrades to `None`, never silently overwritten back to a
    #: single class -- see `run_runtime`'s own accumulation below).
    element_types: dict[str, str | None] = dataclasses.field(default_factory=dict)
    #: 260903 (spec §14.6, volume increment 5, round-1 O5, T27, backlog
    #: #4959): the volume family's hypothesis, read off `verify()`'s own
    #: additive result key -- observed from INSIDE the window that turned
    #: tracking on, never by a separate process-wide call after the fact.
    #: `False` when `run_runtime` never reached `verify()`'s success path
    #: (a harness-level exception -- `result` is never built in that case).
    volume_tracking_observed: bool = False


def run_runtime(example: dict[str, Any]) -> RuntimeOutcome:
    verifier = _import_verifier()
    planned: list[int] = []
    plr_kwargs: dict[int, dict[str, Any]] = {}
    resource_types: dict[str, str] = {}
    element_sets: dict[str, set[str]] = {}
    real_plan_call = verifier.plan_call

    def recording_plan_call(call, index, setup, *, strict):
        planned.append(index)
        plan_result = real_plan_call(call, index, setup, strict=strict)
        # Capture PLR-named kwargs from the plan_result, reduced to IR
        # value JSON (§11.2.2) rather than a repr string.
        if hasattr(plan_result, "kwargs"):
            plr_kwargs[index] = {k: ir_value_of(v) for k, v in plan_result.kwargs.items()}
            resource_types.update(resource_types_from_kwargs(plan_result.kwargs))
            for parent_name, classes in element_types_from_kwargs(plan_result.kwargs).items():
                element_sets.setdefault(parent_name, set()).update(classes)
        return plan_result

    verifier.plan_call = recording_plan_call
    sink = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink):
            result = asyncio.run(
                verifier.verify(
                    example["call_sequence"],
                    example["intent_record"],
                    layout=example.get("deck_layout"),
                    backend=example.get("backend", "LiquidHandlerChatterboxBackend"),
                )
            )
    finally:
        verifier.plan_call = real_plan_call
    error = result.get("error")
    exc_class = error.split(":", 1)[0].strip() if error else None
    failing = planned[-1] if (error and planned) else None
    return RuntimeOutcome(
        error, exc_class, failing, planned, bool(result.get("passed")), plr_kwargs, resource_types,
        element_type_singletons(element_sets),
        bool(result.get("volume_tracking_observed")),
    )


# --------------------------------------------------------------------------
# static side
# --------------------------------------------------------------------------

_LH_TYPE = "LiquidHandler"


@functools.lru_cache(maxsize=4)
def param_names_from_contracts(contracts_json: str) -> dict[str, tuple[str, ...]]:
    """§11.2.4's ``param_names`` for :func:`plr_sema.check.ir.lower_calls`
    (and, symmetrically, what ``check_graph`` builds internally for
    ``lower_graph``): every contract-table entry's additive ``params`` key,
    reduced to ``{contract_key: (plr_param, ...)}``. An entry with no
    ``params`` (a stale, pre-260902 table) is simply absent -- callers that
    ``.get()`` this dict degrade to "trust nothing" for that key, same as
    AC-11.12's fail-closed default.
    """
    contracts = json.loads(contracts_json).get("contracts", {})
    return {key: tuple(entry.get("params", ())) for key, entry in contracts.items() if entry.get("params")}


def resources_from_example(
    example: dict[str, Any],
    *,
    resource_types: Mapping[str, str] | None = None,
    element_types: Mapping[str, str | None] | None = None,
) -> dict[str, dict[str, Any]]:
    """§11.2.2's ``resources`` parameter for :func:`plr_sema.check.ir.
    lower_calls`: a per-name RESOURCE declaration dict, built from
    ``deck_layout`` the same way ``adapt_graph`` (pre-260902) built its
    graph-payload ``resources`` -- the receiver (``lh``) plus every named
    ``deck_layout.resources`` entry.

    ``resource_types``/``element_types`` (spec 260904 §15.4, O1, T30b):
    OPTIONAL, additive, and OFF unless a caller explicitly passes them --
    omitting both reproduces this function's exact pre-O1 output, byte for
    byte (the default-off half of the switch; :func:`run_static_calls`'s
    own ``observe_element_types`` flag is what decides whether a caller
    ever does). When ``resource_types`` (:attr:`RuntimeOutcome.
    resource_types`, the REAL runtime class observed from inside the
    executed window -- §15.4's own "the type half is already computed"
    box) is given, it OVERRIDES ``deck_layout``'s own (frequently wrong,
    ``infer_layout()``-defaulted-to-``Plate``) type for any name it names,
    and adds an entry for a name ``deck_layout`` never had at all. When
    ``element_types`` (:attr:`RuntimeOutcome.element_types`, already
    reduced to singleton-or-``None`` by :func:`element_type_singletons`)
    is given, it threads a per-name ``element_type`` key into the SAME
    declaration -- read straight through by ``plr_sema.check.ir.
    lower_calls`` (``decl.get("element_type")``), no ``ir.py`` change
    needed at all.
    """
    layout = example.get("deck_layout") or {}
    resources: dict[str, dict[str, Any]] = {
        "lh": {"type": _LH_TYPE, "is_container": False, "is_parameter": True, "parents": ()}
    }
    for name, typ in (layout.get("resources") or {}).items():
        resources[name] = {"type": typ, "is_container": False, "is_parameter": True, "parents": ("Deck",)}
    if resource_types:
        for name, cls in resource_types.items():
            entry = resources.setdefault(
                name, {"is_container": False, "is_parameter": True, "parents": ("Deck",)}
            )
            entry["type"] = cls
    if element_types:
        for name, cls in element_types.items():
            if name in resources:
                resources[name]["element_type"] = cls
    return resources


def calls_from_plr_kwargs(
    example: dict[str, Any], plr_kwargs: dict[int, dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[int]]:
    """§11.10's tier-1 rule, restated: a row whose call was never planned
    (``i not in plr_kwargs``) produces NO ``CALL`` at all -- there is no
    tool-named fallback successor to ``adapt_graph``'s old ``json.dumps``
    branch (§11.10, "the fallback branch ... has no successor"). Returns
    ``(calls, not_planned_indices)`` -- ``calls`` is ``lower_calls``'s
    input, in the SAME relative order as the planned subset of
    ``example["call_sequence"]``; ``not_planned_indices`` is the original
    ``call_sequence`` indices the caller should count/report separately.

    §12.1.6 (#4938 real-programs increment): ``calls[0]`` is UNCONDITIONALLY
    the scaffolding's real reset -- ``setup.machine.setup()``, awaited by the
    verifier before ``_execute`` on every row (``training/verify/verifier.py:
    117-126``) -- on the same receiver slot (``"lh"``/``LiquidHandler``) with
    empty ``kwargs``. It is a plain dict here, exactly like every other
    element; it is :func:`lower_row_calls`, not this function or
    ``lower_calls`` itself, that gives it the sentinel origin ``"setup"``.
    Prepending it unconditionally (even for a row where nothing was planned,
    i.e. every index lands in ``not_planned``) is harmless: such a row is
    the ``rows_setup_error`` bucket downstream (``oracle_replay.py``'s
    ``_is_setup_error``), which is keyed off ``not_planned_indices`` and
    ``n_operations_executed`` -- neither reads ``calls`` -- and is excluded
    from every metric that would otherwise see the phantom setup CALL.
    """
    calls: list[dict[str, Any]] = [
        {"method": "setup", "kwargs": {}, "receiver": "lh", "receiver_type": _LH_TYPE}
    ]
    not_planned: list[int] = []
    for i, call in enumerate(example["call_sequence"]):
        kwargs = plr_kwargs.get(i)
        if kwargs is None:
            not_planned.append(i)
            continue
        calls.append({"method": call["name"], "kwargs": kwargs, "receiver": "lh", "receiver_type": _LH_TYPE})
    return calls, not_planned


def lower_row_calls(
    example: dict[str, Any],
    plr_kwargs: dict[int, dict[str, Any]],
    *,
    resources: dict[str, dict[str, Any]],
    param_names: dict[str, tuple[str, ...]] | None = None,
):
    """§12.1.6: builds :func:`plr_sema.check.ir.lower_calls`'s input via
    :func:`calls_from_plr_kwargs` (which always prepends the scaffolding's
    ``setup()`` reset as ``calls[0]``), lowers it, and rewrites
    ``bytecode.sideband["origin"]`` so:

    * pc 0's CALL (always the prepended setup, since ``calls[0]`` always is)
      carries the sentinel origin ``"setup"`` instead of ``lower_calls``' own
      auto-numbered ``"0"``;
    * every other CALL's origin is shifted down by one, making it IDENTICAL
      to what ``lower_calls`` would have produced over ``calls[1:]`` alone --
      the unchanged-origin half of AC-12.3, and what keeps the exact
      ``record_id`` join to P2.5's recorded per-operation results from
      shifting by one.

    ``lower_calls`` itself is untouched: it auto-numbers every CALL 0..N-1 in
    order and has no notion that the first one is special, so it stays a
    pure function of its ``calls`` argument (§12.1.6's normative paragraph).
    This rewrite is caller-side sideband normalisation, which is why it
    lives here in ``plr-sema/eval/`` rather than in ``plr_sema.check.ir``.

    Returns ``(bytecode, not_planned_indices)``.
    """
    sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))
    from plr_sema.check import ir as _ir

    calls, not_planned = calls_from_plr_kwargs(example, plr_kwargs)
    bc = _ir.lower_calls(calls, resources=resources, param_names=param_names)
    origin = bc.sideband.get("origin", {})
    new_origin: dict[int, str] = {}
    for pc, local_idx in origin.items():
        if local_idx == "0":
            new_origin[pc] = "setup"
        else:
            new_origin[pc] = str(int(local_idx) - 1)
    new_sideband = dict(bc.sideband)
    new_sideband["origin"] = new_origin
    bc = dataclasses.replace(bc, sideband=new_sideband)
    return bc, not_planned


def run_static(graph: dict[str, Any], contracts_json: str) -> dict[str, dict[str, Any]]:
    """The GRAPH-payload path (§6.2 wire format in, per-op verdict summary
    out) -- unchanged by 260902, kept for a future tier-2 source-render
    harness (§11.10). ``check_graph`` internally lowers via
    :func:`plr_sema.check.ir.lower_graph` and relabels; this function's own
    signature and behavior are untouched.
    """
    sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))
    from plr_sema import check_graph
    from plr_sema.verdict import join

    report = check_graph(json.dumps(graph), contracts_json)
    per_op: dict[str, list] = {o["id"]: [] for o in graph["operations"]}
    for f in report.findings:
        per_op.setdefault(f.operation_id, []).append(f)
    return {
        oid: {
            "verdict": join(fs).value,
            "n_findings": len(fs),
            "reasons": sorted({getattr(f, "reason", None) or "" for f in fs} - {""}),
        }
        for oid, fs in per_op.items()
    }


def run_static_calls(
    example: dict[str, Any],
    plr_kwargs: dict[int, dict[str, Any]],
    contracts_json: str,
    *,
    param_names: dict[str, tuple[str, ...]] | None = None,
    volume_tracking_observed: bool = False,
    observe_element_types: bool = False,
    resource_types: Mapping[str, str] | None = None,
    element_types: Mapping[str, str | None] | None = None,
    excludes_sites: "list[Any] | None" = None,
) -> tuple[dict[str, dict[str, Any]], list[int]]:
    """The ``lower_calls`` path (§11.2.2/§11.10 tier 1) -- ``adapt_graph``'s
    replacement. Lowers ``example["call_sequence"]``'s PLANNED subset
    (``i in plr_kwargs``), plus the §12.1.6 scaffolding ``setup()`` reset
    :func:`lower_row_calls` always prepends, through
    :func:`plr_sema.check.ir.lower_calls`, runs
    :func:`plr_sema.check.check_ir`, and relabels back to the ``op_<i>``
    convention :func:`compare` expects -- but keyed by the REAL
    ``call_sequence`` index, not the position among only-planned calls
    (:func:`lower_row_calls`'s rewritten ``origin`` map is 0-based over the
    REAL calls only and skips not-planned indices, using the sentinel
    ``"setup"`` for the prepended reset; this function composes the numeric
    half with the planned-index list to restore the real index, and drops
    the setup CALL's own findings entirely -- it has no real
    ``call_sequence`` index to compare against, §12.1.6).

    Returns ``(per_op, not_planned_indices)`` -- ``per_op`` additionally
    carries a ``{"verdict": "unknown", "n_findings": 0, "reasons": []}``
    entry for every not-planned index (so :func:`compare`, which indexes
    ``st[f"op_{i}"]`` for every ``i`` in ``call_sequence``, never
    KeyErrors), and the caller is expected to report ``not_planned_indices``
    separately (§11.10: "counted as ``not_planned`` in the report").

    ``volume_tracking_observed`` (spec 260903 §14.6/§14.11, volume
    increment 5, round-1 O5, T27, backlog #4959): the caller's own in-window
    observation (:attr:`RuntimeOutcome.volume_tracking_observed`, itself
    read off ``verify()``'s additive result key) -- this function builds
    ``env`` from it and passes ``env`` to :func:`plr_sema.check.check_ir`.
    The NAME comes from the ``does_volume_tracking`` callable's own
    ``__name__``, never a typed string constant. Defaulting to `False`
    reproduces every pre-T27 caller's behaviour exactly (``env=frozenset()``
    is ``check_ir``'s own default).

    (#4976, band B0): immediately after ``findings`` is computed below --
    already relabelled to real ``op_<i>`` ids and already stripped of every
    finding whose PRE-relabel ``operation_id`` was a setup pc (the two lines
    above this docstring's caller-visible effect) -- this function calls
    :data:`FINDINGS_SINK` with ``(row_id, findings)`` iff a sink is
    installed, where ``row_id`` is ``example.get("intent_record",
    {}).get("record_id", "")``. This is why a setup-guard finding (e.g.
    ``LiquidHandler.setup``'s own ``self.setup_finished`` raise-guard,
    ``external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:191``)
    can never reach the sink under a REAL op id: its Finding is excluded by
    the ``setup_pcs`` filter below before ``findings`` even exists, not
    merely before this seam -- there is no code path in this function by
    which it could be relabelled onto a real call's ``op_<i>``.

    ``observe_element_types``/``resource_types``/``element_types`` (spec
    260904 §15.4, O1, T30b): the default-off switch. With
    ``observe_element_types=False`` (the default), ``resources_from_example``
    is called with neither optional argument and this function's behaviour
    is BYTE-IDENTICAL to every pre-T30b caller's -- ``resource_types``/
    ``element_types`` are accepted but ignored in that case, so a caller
    may pass them unconditionally and flip the switch with one boolean.
    With ``observe_element_types=True``, both are threaded into
    ``resources_from_example`` (typically :attr:`RuntimeOutcome.
    resource_types`/``.element_types`` from the SAME row's ``run_runtime``
    call). T30b's own measurement script is the only caller that turns
    this on; T32 is expected to be the first REPLAY caller that does.

    ``excludes_sites`` (#4979, T32, spec 260904 §15.10): an OPTIONAL mutable
    list, threaded verbatim to :func:`plr_sema.check.check_ir`'s own
    ``excludes_sites`` collector -- this function never reads or clears it,
    only forwards the reference. ``None`` (the default) reproduces every
    pre-T32 caller's behaviour byte-identical, since ``check_ir``'s own
    default is also ``None``. A caller that passes a list gets it back
    populated, after the call, with one ``PlrSite`` per tier-(iii)
    (``guard.is_dynamic_raise``) guard visited anywhere in THIS call's
    lowered graph -- i.e. one list per ``run_static_calls`` invocation
    (one per ROW in every caller today), never per individual ``CALL``/
    operation; ``AnalysisReport.scope`` is the same one-list-per-report
    shape (`plr_sema/src/plr_sema/verdict.py`'s ``SoundnessScope``
    docstring). ``oracle_replay.py`` is the first caller that passes one,
    to publish ``rows_excused_by_scope`` as a pure annotation (no gate
    effect, §15.10's own normative box).
    """
    sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))
    from plr_sema.check import check_ir
    from plr_sema.check import ir as _ir
    from plr_sema.verdict import join

    if observe_element_types:
        resources = resources_from_example(example, resource_types=resource_types, element_types=element_types)
    else:
        resources = resources_from_example(example)
    contracts_payload = json.loads(contracts_json)
    contracts = contracts_payload.get("contracts", {})
    # 260902 (spec §10, tip typestate increment): thread the additive
    # `receiver_state` block through so the tier-1 replay actually
    # exercises tip-state evaluation -- omitting this would silently keep
    # AC-10.11's n_exact_channel_sets at 0 regardless of what lower_calls
    # produces, for a reason that has nothing to do with argument naming.
    receiver_states = contracts_payload.get("receiver_state", {})

    from pylabrobot.resources.volume_tracker import does_volume_tracking

    env = frozenset({does_volume_tracking.__name__}) if volume_tracking_observed else frozenset()

    bc, not_planned = _lower_row_calls_notified(example, plr_kwargs, resources, param_names, resource_types, element_types)
    raw_findings = check_ir(bc, contracts, receiver_states, env=env, excludes_sites=excludes_sites)

    planned_indices = [i for i in range(len(example["call_sequence"])) if i not in set(not_planned)]
    origin = bc.sideband.get("origin", {})
    setup_pcs = {pc for pc, local_idx in origin.items() if local_idx == "setup"}
    real_origin = {
        pc: f"op_{planned_indices[int(local_idx)]}" for pc, local_idx in origin.items() if local_idx != "setup"
    }
    raw_findings = tuple(f for f in raw_findings if int(f.operation_id) not in setup_pcs)
    findings = _ir.relabel_findings(raw_findings, real_origin)

    if FINDINGS_SINK is not None:
        row_id = (example.get("intent_record") or {}).get("record_id", "") or ""
        FINDINGS_SINK(row_id, findings)

    per_op: dict[str, list] = {f"op_{i}": [] for i in not_planned}
    for f in findings:
        per_op.setdefault(f.operation_id, []).append(f)
    result = {
        oid: {
            "verdict": join(tuple(fs)).value,
            "n_findings": len(fs),
            "reasons": sorted({getattr(f, "reason", None) or "" for f in fs} - {""}),
        }
        for oid, fs in per_op.items()
    }
    return result, not_planned


# --------------------------------------------------------------------------
# comparison
# --------------------------------------------------------------------------


def compare(example: dict[str, Any], rt: RuntimeOutcome, st: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for i, call in enumerate(example["call_sequence"]):
        oid = f"op_{i}"
        if rt.failing_index is None:
            outcome = "ran_ok" if rt.error is None else "not_reached(setup_error)"
        elif i < rt.failing_index:
            outcome = "ran_ok"
        elif i == rt.failing_index:
            outcome = f"raised:{rt.exc_class}"
        else:
            outcome = "not_reached"
        verdict = st[oid]["verdict"]
        unsound = (verdict == "safe" and outcome.startswith("raised")) or (
            verdict == "will_fail" and outcome == "ran_ok"
        )
        rows.append({
            "index": i, "method": call["name"], "static": verdict,
            "static_findings": st[oid]["n_findings"], "runtime": outcome, "unsound": unsound,
        })
    return rows


# --------------------------------------------------------------------------
# row parsing for corpus + P2.5 scaffolding
# --------------------------------------------------------------------------

# Scaffolding constants (match floor_gen.exec_verify exactly)
_TIP_RACK = "tip_rack"
_DUMMY_TIP_SPOT = f"{_TIP_RACK}.A1"
_PRIME_PLATE = "prime_plate"
_PLATE_ROWS = "ABCDEFGH"

# T16d (#4879): floor_gen.exec_verify.execution_verify_example gates on
# ``example.cell.ambiguity_class != "none"`` and returns skipped=True BEFORE
# ever calling ``_precondition_plan`` -- see exec_verify.py:96-103
# (_CLASS_SKIP_REASONS) and :271-274. The corpus assembler's own sidecar
# (corpus_p25_sidecar.jsonl) records this same class per row using
# underscore-separated names ("clean_parse" == floor_gen's "none";
# "missing_slot"/"ambiguous_referent"/"out_of_surface" == floor_gen's
# "missing-slot"/"ambiguous-referent"/"out-of-surface"). Prior to this fix
# (T16b, 6c668aa6) oracle_common ran _precondition_plan on EVERY row with a
# tool call regardless of class, which (a) executed 118/123 ambiguous_referent
# and 95/175 missing_slot rows P2.5 never touched (execution_verify=None in
# corpus_p23_floor.jsonl for every one of them, verified 260902), producing
# spurious GroundingError/DispatchError/RuntimeError "disagreements" against
# a crosscheck P2.5 never ran, and (b) KeyError-crashed on 17 missing_slot
# rows whose required param (volume_ul) was deliberately omitted -- aspirate/
# dispense's own _precondition_plan branches index params["volume_ul"]
# unconditionally (a bug floor_gen's own function shares, but never hits
# because its cls-gate skips these rows first).
_CLASS_SKIP_REASONS: dict[str, str] = {
    "missing_slot": "missing_slot calls are intentionally incomplete (required param "
                     "omitted); not executable ground truth (floor_gen.exec_verify "
                     "_CLASS_SKIP_REASONS['missing-slot'])",
    "ambiguous_referent": "ambiguous_referent calls carry a deliberately vague/ungroundable "
                           "ref; not executable ground truth (floor_gen.exec_verify "
                           "_CLASS_SKIP_REASONS['ambiguous-referent'])",
    "out_of_surface": "out_of_surface rows carry no call sequence (D7 clarify-only example; "
                       "floor_gen.exec_verify _CLASS_SKIP_REASONS['out-of-surface'])",
}
_EXECUTABLE_AMBIGUITY_CLASS = "clean_parse"  # sidecar's name for floor_gen's cell.ambiguity_class == "none"


def _expand_ref(ref: str) -> list[str]:
    """A single grounded dotted ref (name.A1 or name.A1:C1) -> individual well refs.
    Mirrors verify/grounding.py's ground_ref exactly.
    """
    from pylabrobot.utils.positions import expand_string_range
    base, _, tail = ref.partition(".")
    if not tail or ":" not in tail:
        return [ref]
    return [f"{base}.{pos}" for pos in expand_string_range(tail)]


def _expand_channel_wells(refs: Any) -> list[str]:
    """Flat list of individual wells refs addresses, expanding any colon-range."""
    ref_list = refs if isinstance(refs, list) else [refs]
    wells: list[str] = []
    for ref in ref_list:
        wells.extend(_expand_ref(ref))
    return wells


def _row_major_wells(resource: str, n: int) -> list[str]:
    """N distinct row-major wells on resource (A1, B1, ..., H1, A2, ...)."""
    wells = [f"{resource}.{row}{col}" for col in range(1, 13) for row in _PLATE_ROWS]
    if n > len(wells):
        raise ValueError(f"{resource} (96 wells) cannot supply {n} distinct wells")
    return wells[:n]


def _resource_type_holders(call: dict[str, Any]) -> list[str]:
    """Names of this call's RESOURCE_TYPE_RESOURCE-typed symbolic refs.

    Replicates floor_gen.exec_verify._resource_type_holders exactly (T16d,
    #4879): infer_layout() defaults every unrecognized ref name to a bare
    Plate; PLR's move_resource/move_plate/move_lid reject a Plate
    destination for a "resource" (ResourceStack/ResourceHolder) target.
    DeckLayout.holders is the harness's own documented mechanism for
    exactly this. Prior to this fix, oracle_common never computed holders
    at all, so every move_resource/move_plate/move_lid call in the corpus
    hit "RuntimeError: Can only drop Lid resources onto Plate '<name>'"
    even on rows P2.5 recorded as passed (45/141 crosscheck-joined
    clean_parse disagreements, all in this one shape, verified 260902).
    Deduped: the same name can legitimately appear twice (e.g.
    move_resource.resource == .destination would otherwise register two
    holders under one name and crash).
    """
    ParamKind, params_of = _import_param_namespace()
    names: list[str] = []
    for spec in params_of(call["name"]):
        if spec.kind is ParamKind.SYMBOLIC_RESOURCE_REF and spec.resource_type == "resource":
            value = call["params"].get(spec.name)
            if isinstance(value, str):
                names.append(value)
            elif isinstance(value, list):
                names.extend(v for v in value if isinstance(v, str))
    return list(dict.fromkeys(names))


def _precondition_plan(
    call: dict[str, Any],
) -> tuple[str | None, list[dict[str, Any]], dict[str, str], dict[str, float]]:
    """Decide whether call is verifiable, and what synthetic setup it needs.

    Returns (skip_reason, prefix_calls, extra_resources, seed_volumes).
    Replicates floor_gen.exec_verify._precondition_plan exactly.
    """
    # Import SUPPORTED_TOOLS dynamically to avoid hard dep at module level
    try:
        from verify.dispatcher import SUPPORTED_TOOLS
    except ModuleNotFoundError:
        from training.verify.dispatcher import SUPPORTED_TOOLS  # type: ignore[import-not-found]

    name = call["name"]
    params = call["params"]

    if name not in SUPPORTED_TOOLS:
        return (
            f"{name!r} has no LiquidHandler-chatterbox execution path",
            [], {}, {},
        )

    if name == "transfer" and params.get("volume_ul") is None:
        return (
            "transfer without volume_ul cannot be deterministically post-conditioned",
            [], {}, {},
        )

    pickup = {"name": "pick_up_tips", "params": {"at": [_DUMMY_TIP_SPOT]}}

    if name == "transfer":
        if "source" not in params:
            return "transfer missing required 'source' param", [], {}, {}
        vol_param = params.get("volume_ul") or []
        # Handle both scalar and list volume_ul
        if isinstance(vol_param, (int, float)):
            total = float(vol_param)
        else:
            total = sum(float(v) for v in vol_param)
        seeds = {params["source"]: total} if total > 0 else {}
        return None, [pickup], {}, seeds

    if name == "aspirate":
        if "source" not in params:
            return "aspirate missing required 'source' param", [], {}, {}
        sources = _expand_channel_wells(params["source"])
        vols = params["volume_ul"] if isinstance(params["volume_ul"], list) else [params["volume_ul"]]
        pickup_n = {"name": "pick_up_tips", "params": {"at": _row_major_wells(_TIP_RACK, len(sources))}}
        return None, [pickup_n], {}, dict(zip(sources, vols))

    if name == "dispense":
        if "destination" not in params:
            return "dispense missing required 'destination' param", [], {}, {}
        destinations = _expand_channel_wells(params["destination"])
        vols = params["volume_ul"] if isinstance(params["volume_ul"], list) else [params["volume_ul"]]
        n = len(destinations)
        pickup_n = {"name": "pick_up_tips", "params": {"at": _row_major_wells(_TIP_RACK, n)}}
        prime_wells = _row_major_wells(_PRIME_PLATE, n)
        prime = {"name": "aspirate", "params": {"source": prime_wells, "volume_ul": list(vols)}}
        return None, [pickup_n, prime], {_PRIME_PLATE: "Plate"}, dict(zip(prime_wells, vols))

    if name == "drop_tips":
        destination = params.get("destination")
        spots = destination if isinstance(destination, list) else [destination]
        return None, [{"name": "pick_up_tips", "params": {"at": list(spots)}}], {}, {}

    if name == "discard_tips":
        return None, [pickup], {}, {}

    # pick_up_tips / stamp / move_resource / move_plate / move_lid: no precondition
    return None, [], {}, {}


# §12.4.3 (#4939): loader-only well-ref normalisation. ``<Row>`` a single
# A-H, ``<Col>`` 1-2 digits -- the same shape ``tip_mutants.py:124``'s
# dotted-ref regex (``_WELL_REF_RE``) targets, mirrored here for the
# underscore form a golden-provenance mined utterance actually produces
# (e.g. "tip rack 3 position F7" -> ``tip_rack_3_F7``).
_UNDERSCORE_WELL_REF_RE = re.compile(r"^(?P<base>.+)_(?P<row>[A-H])(?P<col>\d{1,2})$")


def _underscore_ref_base_counts(params: dict[str, Any]) -> collections.Counter:
    """How many times each ``<base>_<Row><Col>``-shaped ref's base occurs
    across ONE call's own params -- a base repeated 2+ times (e.g. a
    4-well ``pick_up_tips.at`` list all on ``filter_tip_box``) is
    self-consistent evidence it names one shared resource, not a
    name-pattern coincidence.
    """
    counts: collections.Counter = collections.Counter()
    for value in params.values():
        refs = value if isinstance(value, list) else [value]
        for ref in refs:
            if isinstance(ref, str):
                m = _UNDERSCORE_WELL_REF_RE.match(ref)
                if m:
                    counts[m.group("base")] += 1
    return counts


def _normalize_well_refs(call: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Rewrite ``<base>_<Row><Col>`` refs in ``call["params"]`` to
    ``<base>.<Row><Col>`` iff ``<base>`` is a DECLARED resource of this
    row's own layout -- the layout it has already computed, not a name
    pattern (AC-12.19). "Declared" means either:

    (a) a key of the scaffold resources ``_precondition_plan`` would add
        for this call -- consulted via a side-effect-free dry run
        (``_precondition_plan`` reads only ``call["name"]``/structural
        param presence, never ref VALUE shape, so this dry run cannot
        itself be influenced by the rewrite it is deciding); or
    (b) a base repeated 2+ times across this SAME call's own params
        (:func:`_underscore_ref_base_counts`).

    A base satisfying neither is left exactly as it is and keeps
    whatever skip/parse outcome it produces today (AC-12.19's ``foo_A1``
    / no ``foo`` declared case) -- this is the whole safety argument:
    without it, ``tip_rack_3_F7`` and a hypothetical resource genuinely
    NAMED ``tip_rack_3_F7`` are indistinguishable.

    Returns ``(call, [])`` unchanged when nothing normalises (including
    the identical ``call`` object, not a copy) so callers can cheaply
    check ``rewritten`` for the ``rows_normalised`` signal.
    """
    _, _, extra_resources, _ = _precondition_plan(call)
    declared = set(extra_resources.keys())
    declared |= {
        base for base, n in _underscore_ref_base_counts(call["params"]).items() if n >= 2
    }
    if not declared:
        return call, []

    rewritten: list[str] = []

    def _norm(value: Any) -> Any:
        if isinstance(value, list):
            return [_norm(v) for v in value]
        if isinstance(value, str):
            m = _UNDERSCORE_WELL_REF_RE.match(value)
            if m and m.group("base") in declared:
                rewritten.append(value)
                return f"{m.group('base')}.{m.group('row')}{m.group('col')}"
        return value

    new_params = {k: _norm(v) for k, v in call["params"].items()}
    if not rewritten:
        return call, []
    return {"name": call["name"], "params": new_params}, rewritten


def row_to_verifier_inputs(
    row: dict[str, Any],
    *,
    source_file: str,
    line: int,
    ambiguity_class: str | None = None,
    sidecar_record_id: str | None = None,
    provenance: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any] | None, str | None, str | None]:
    """Parse a chat-format corpus row into call_sequence, intent_record, layout.

    The row format (corpus_p25.jsonl) is:
        {
            "messages": [{role, content, tool_calls?}, ...],
            "tools": [...],
            "metadata": "train"|"test"|...,
        }

    The ground-truth call is extracted from the assistant message's
    tool_calls[*].function.{name, arguments}. The intent comes from the user
    message. Replicate P2.5 scaffolding (floor_gen.exec_verify): add prefix
    calls (pick_up_tips, etc.) to satisfy preconditions, populate seed_volumes,
    and return an intent_record with source="synthetic" and expected_effects=[].

    Args:
        row: a single row from corpus JSONL or chat-format JSON
        source_file: basename of the corpus file, for record_id
        line: line number (1-indexed) for record_id
        ambiguity_class: sidecar-provided class ("clean_parse", "missing_slot",
            "ambiguous_referent", "out_of_surface"); when given and not
            "clean_parse", the row is skipped before _precondition_plan runs
            (mirrors floor_gen.exec_verify's cls != "none" gate). None means
            no sidecar join was available for this row -- fall back to the
            pre-T16d behavior of attempting _precondition_plan unconditionally.
        sidecar_record_id: when given, overrides the synthetic
            "{source_file}:{line}" record_id with the sidecar's own
            record_id (exact join key against floor/overlay crosscheck files).
        provenance: sidecar's "coverage" | "golden" | "naturalness". When
            "naturalness", the row's params are VERBATIM MINED SOURCE
            EXPRESSIONS (overlay_gen provenance) and are run through
            overlay_gen's own _normalize_params before _precondition_plan;
            an unresolvable expression (variable/computed value) produces a
            skip_reason (matches overlay_gen.exec_verify.execution_verify_call),
            not an execution attempt.

    Returns:
        (call_sequence, intent_record, deck_layout, skip_reason, no_call_reason)
        - call_sequence: list of {name, params} dicts (may be empty)
        - intent_record: dict with record_id, utterance, source, calls,
          expected_effects, normalized_refs (§12.4.3, #4939: original ref
          strings the loader-only well-ref normalisation rewrote, e.g.
          ["tip_rack_3_F7"]; empty when nothing normalised)
        - deck_layout: dict with resources and seed_volumes, or None
        - skip_reason: None if executable; str reason if _precondition_plan rejected it
        - no_call_reason: "no_tool_calls" if assistant had no tool_calls; else None

    """
    # Find the assistant message with tool_calls
    real_call: dict[str, Any] | None = None
    user_message_content = ""
    no_call_reason = None
    for msg in row.get("messages", []):
        if msg.get("role") == "user":
            user_message_content = msg.get("content", "")
        elif msg.get("role") == "assistant":
            tool_calls = msg.get("tool_calls", [])
            if not tool_calls:
                no_call_reason = "no_tool_calls"
            elif tool_calls:
                # Take the first tool call (corpus has 1 call per row)
                func = tool_calls[0].get("function", {})
                real_call = {
                    "name": func.get("name", ""),
                    "params": func.get("arguments", {}),
                }

    # #4939 follow-up (260903): content-digest record_id, computed from the
    # RAW extraction above (before any naturalness-normalize_params /
    # _normalize_well_refs mutation below) -- stable across corpus
    # reordering, unlike the old "{source_file}:{line}" scheme.
    # ``sidecar_record_id`` is accepted for signature compatibility with
    # existing callers/tests but is intentionally no longer used for
    # identity: the sidecar's own id is joined via a separate content-digest
    # lookup on the CALLER's side (oracle_replay.py's ``_sidecar_for``), not
    # folded into this row's own record_id.
    del sidecar_record_id
    record_id = f"{source_file}:{content_digest(user_message_content, real_call)}"

    skip_reason = None
    call_sequence = []
    extra_resources = {}
    seed_volumes = {}
    normalized_refs: list[str] = []

    if no_call_reason:
        # Row has no tool_calls; this is a clarification turn
        pass
    elif not real_call:
        # Malformed row (should not happen if no_call_reason is set)
        no_call_reason = "malformed_row"
    elif ambiguity_class is not None and ambiguity_class != _EXECUTABLE_AMBIGUITY_CLASS:
        # T16d gate: P2.5 never ran execution_verify on this row (cls != "none");
        # do not call _precondition_plan at all.
        skip_reason = _CLASS_SKIP_REASONS.get(
            ambiguity_class,
            f"ambiguity_class {ambiguity_class!r} is not executable ground truth "
            "(unrecognized class, treated conservatively as non-executable)",
        )
    elif provenance == "naturalness":
        # T16d: mined-call source-expression normalization (overlay_gen's
        # own gate) before any precondition planning.
        normalize_params = _import_overlay_normalizers()
        normalized = normalize_params(real_call["name"], real_call["params"])
        if normalized is None:
            skip_reason = (
                "mined call references a variable/computed value (not a literal deck ref "
                "or numeric volume) that the P2.2 harness's static grounding can't resolve "
                "from source text alone; execution-verify skipped, not rejected "
                "(overlay_gen.exec_verify.execution_verify_call parity)"
            )
        else:
            real_call = {"name": real_call["name"], "params": normalized}
            real_call, normalized_refs = _normalize_well_refs(real_call)
            skip_reason, prefix, extra_resources, seed_volumes = _precondition_plan(real_call)
            if skip_reason is None:
                call_sequence = [*prefix, real_call]
    else:
        # §12.4.3 (#4939): loader-only well-ref normalisation, before
        # _precondition_plan so its derived prefix/seed_volumes see the
        # already-dotted ref (consistency, not a second pass over them).
        real_call, normalized_refs = _normalize_well_refs(real_call)
        # Apply P2.5 scaffolding via _precondition_plan
        skip_reason, prefix, extra_resources, seed_volumes = _precondition_plan(real_call)
        if skip_reason is None:
            call_sequence = [*prefix, real_call]

    # Build deck_layout from scaffold resources, seed volumes, and
    # resource-type holders (real_call only -- matches
    # floor_gen.exec_verify.execution_verify_example, which computes
    # holders from the real call, not the scaffold prefix).
    holders: list[str] = []
    if skip_reason is None and real_call is not None:
        holders = _resource_type_holders(real_call)
    deck_layout = None
    if extra_resources or seed_volumes or holders:
        deck_layout = {
            "resources": extra_resources,
            "seed_volumes": seed_volumes,
            "holders": holders,
        }

    # Replicate P2.5 scaffolding: intent matches the full call sequence
    intent_record = {
        "record_id": record_id,
        "utterance": user_message_content,
        "source": "synthetic",  # per P2.5 exec_verify
        "calls": [{"name": c["name"], "params": c["params"]} for c in call_sequence],
        "expected_effects": [],  # per P2.5 exec_verify
        # §12.4.3 (#4939): original ref strings rewritten by
        # _normalize_well_refs, e.g. ["tip_rack_3_F7"] -- empty when
        # nothing normalised. Threaded through the dict (not a new
        # positional return) so the function's 5-tuple arity, shared with
        # tip_mutants.py (out of #4939's scope), does not change.
        "normalized_refs": normalized_refs,
    }

    return call_sequence, intent_record, deck_layout, skip_reason, no_call_reason


# --------------------------------------------------------------------------
# LOWERED_SINK (#4978, T32 fix-up): a second additive observer, alongside
# FINDINGS_SINK above, over `run_static_calls`'s own per-row pipeline.
# APPENDED here, at the very end of the module, rather than beside
# FINDINGS_SINK or inline inside `run_static_calls` -- every increment spec
# (260901, 260902 x2, 260903 x3, 260904) cites exact `oracle_common.py:N-M`
# line ranges throughout this file, and inserting new lines anywhere in the
# MIDDLE would have shifted every citation below the insertion point. This
# hook therefore touches exactly ONE existing line elsewhere in the module
# (the `lower_row_calls(...)` call inside `run_static_calls`, rewritten to
# call `_lower_row_calls_notified` below -- a 1-line-for-1-line
# substitution, so no other line moves) plus this purely-appended block.
#
# Motivation (#4978): `plr-sema/eval/t30_measure.py`'s OWN row loop used to
# re-implement `row_to_verifier_inputs`/`run_runtime`/`lower_row_calls`
# directly, calling `row_to_verifier_inputs` WITHOUT the sidecar-derived
# `ambiguity_class`/`provenance` `oracle_replay.main()` computes per row --
# so every non-"clean_parse" row (missing_slot/ambiguous_referent/
# out_of_surface) that `run_row` skips was silently ADMITTED instead,
# inflating its measured population from the correct 544 executed real ops
# (223 `pick_up_tips`, matching `unknown_ledger.py`'s own FINDINGS_SINK-
# derived population) to 923 (361 `pick_up_tips`). Rather than have
# `t30_measure.py` re-derive that gating a second time (and risk drifting
# from it again), this hook lets it reuse `oracle_replay.main()` itself --
# unmodified, exactly like `unknown_ledger.py` already does via
# FINDINGS_SINK -- as its OWN source of "which rows/ops are executed",
# while still getting back the lowered `_ir.Call` instructions a per-call
# classifier needs (which `FINDINGS_SINK`'s `Finding` objects alone do not
# carry).
#
# Fired with ``(row_id, bc, bc_with_o1, not_planned, element_types)``
# immediately after `_lower_row_calls_notified`'s own (unmodified)
# `lower_row_calls` call returns, i.e. for every row that reaches
# `run_static_calls` at all (the SAME population `FINDINGS_SINK` is fired
# for, from the SAME call), regardless of what `check_ir` later decides:
#
# * ``bc`` is `lower_row_calls`'s own return value, lowered under exactly
#   the ``resources`` this `run_static_calls` invocation was actually
#   given -- i.e. WITH O1's element-type observation iff the caller's own
#   ``observe_element_types`` was ``True`` for this call (every existing
#   caller through `oracle_replay.py`'s `run_row` passes ``False``, so this
#   is the "without O1" view for every caller today).
# * ``bc_with_o1`` is a SECOND, independent `lower_row_calls` call over the
#   SAME ``example``/``plr_kwargs``/``param_names``, differing only in
#   using ``resources_from_example(example, resource_types=resource_types,
#   element_types=element_types)`` -- the WITH-O1 view -- built from the
#   ``resource_types``/``element_types`` parameters `run_static_calls`
#   already receives regardless of its own ``observe_element_types``
#   setting (`oracle_replay.run_row` always passes
#   `RuntimeOutcome.resource_types`/`.element_types` through). This gives a
#   sink observer BOTH views for every row unconditionally, rather than
#   only whichever one the caller's own flag happened to select -- exactly
#   what a block-4/5-style with/without-O1 comparison (T30b, spec 260904
#   §15.4) needs, without that comparison ever having to re-run
#   `row_to_verifier_inputs`/`run_runtime` itself.
# * ``not_planned`` is `calls_from_plr_kwargs`'s own not-planned index list
#   (identical for both lowerings -- it depends only on ``plr_kwargs``, not
#   on ``resources``, see `lower_row_calls`'s own body).
# * ``element_types`` is `run_static_calls`'s own ``element_types``
#   parameter, forwarded verbatim (as a defensive shallow copy) so a caller
#   can compute a heterogeneous-parent count (values that reduced to
#   ``None``, §15.4 C11b) without needing `RuntimeOutcome` itself.
#
# Default `None` (no observer): every existing caller of `run_static_calls`
# (`oracle_replay.py`, `tip_mutants.py`, `scripts/oracle_spike.py`, this
# module's own doctests, and every test in this repo) is therefore
# byte-identical in behaviour and return value whether or not this hook has
# ever been installed -- purely an additive observation seam, like
# FINDINGS_SINK, never a control-flow change; it does not monkeypatch
# `check_ir`, `lower_calls`, or anything else, and `lower_row_calls` itself
# stays untouched and still callable directly (as
# `plr-sema/eval/unknown_ledger.py` and every test that calls it directly
# still does).
LoweredSink = Callable[[str, Any, Any, "list[int]", "dict[str, str | None]"], None]
LOWERED_SINK: LoweredSink | None = None


def _lower_row_calls_notified(
    example: dict[str, Any],
    plr_kwargs: dict[int, dict[str, Any]],
    resources: dict[str, dict[str, Any]],
    param_names: dict[str, tuple[str, ...]] | None,
    resource_types: Mapping[str, str] | None,
    element_types: Mapping[str, str | None] | None,
):
    """`run_static_calls`'s own call site for `lower_row_calls`, wrapped
    only to additionally fire `LOWERED_SINK` (see this block's own header
    comment above) when one is installed. `lower_row_calls` is called here
    with EXACTLY the same arguments `run_static_calls` always passed it
    directly before this hook existed, so `(bc, not_planned)` -- this
    function's return value -- is byte-identical to the pre-hook call site
    in every case; the sink's own with-O1 lowering is a SEPARATE, additional
    `lower_row_calls` call that exists purely for the sink's benefit and
    whose result is never returned to `run_static_calls` itself.
    """
    bc, not_planned = lower_row_calls(example, plr_kwargs, resources=resources, param_names=param_names)
    if LOWERED_SINK is not None:
        row_id = (example.get("intent_record") or {}).get("record_id", "") or ""
        o1_resources = resources_from_example(example, resource_types=resource_types, element_types=element_types)
        bc_with_o1, _not_planned_o1 = lower_row_calls(
            example, plr_kwargs, resources=o1_resources, param_names=param_names
        )
        LOWERED_SINK(row_id, bc, bc_with_o1, not_planned, dict(element_types or {}))
    return bc, not_planned
