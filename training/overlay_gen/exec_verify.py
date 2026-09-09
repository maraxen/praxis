"""Execution-verify wiring: P2.2 harness (``verify/``) -> P2.4 overlay rows.

Mirrors ``floor_gen.exec_verify``'s precondition-planning approach (same PLR
call vocabulary, same chatterbox harness) but does NOT import it: this
package's convention is to keep floor_gen/overlay_gen siblings independent
(``pair_builder.py`` already duplicates ``floor_gen/corpus.py``'s
``_prewarm_cache_batched`` pattern rather than cross-importing it -- see that
function's docstring) rather than introduce a floor_gen<->overlay_gen coupling
for a small amount of shared logic. A follow-up could factor this out into a
shared module if a THIRD caller ever needs it.

overlay_gen's calls come from MINING REAL notebook/protocol source code
(``overlay_gen.miner``), not from a synthesized, schema-clean value pool.
``MinedCall.params`` therefore carries the VERBATIM SOURCE EXPRESSION for
each argument (miner.py's own docstring: "grounding happens downstream,
never in this generator") -- e.g. ``"plate['A1']"``, ``"plate[dst_well]"``
(a variable reference), or ``"sample_volume_ul * 0.8"`` (a computed
expression), not a resolved deck reference or a numeric literal. Only the
SIMPLE, literal-resolvable subset (bare name / ``name['A1']`` /
``name['A1:C1']`` well-refs; actual numeric-literal volumes) can be
translated into the P2.2 harness's ``<name>.<id>`` grounding grammar at all.

A rejection here therefore means something DIFFERENT from floor_gen's: this
is REAL code that was already running against some PLR version, so a
genuine execution-verify failure most likely indicates version skew against
the vendored PLR pinned here (``PLR_SUBMODULE_SHA``) or a mining-extraction
gap -- NOT that a teacher model hallucinated. A skip (computed/variable
value, non-liquid-handler receiver) is NEVER a rejection: the harness
simply cannot judge that call, one way or the other, from its source text
alone. (260828, execution-verify wiring task 260828_wire_execution_verify.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pylabrobot.utils.positions import expand_string_range

from coxswain.plr.param_namespace import ParamKind, params_of
from verify import run_verify_sync
from verify.deck import DeckLayout
from verify.dispatcher import SUPPORTED_TOOLS
from verify.failure_taxonomy import classify_check_failure, classify_exception

from overlay_gen.miner import MinedCall

__all__ = ["ExecutionVerifyResult", "execution_verify_call"]

_TIP_RACK = "tip_rack"
_DUMMY_TIP_SPOT = f"{_TIP_RACK}.A1"
_PRIME_PLATE = "prime_plate"
_PRIME_WELL = f"{_PRIME_PLATE}.A1"
#: Both the harness's tip_rack and generic "Plate" resources are real 96-well
#: (8x12) footprints (chatterbox_runner.py's hamilton_96_tiprack_1000uL_filter
#: / Cor_96_wellplate_360ul_Fb).
_PLATE_ROWS = "ABCDEFGH"


def _row_major_wells(resource: str, n: int) -> list[str]:
    """N distinct row-major wells on ``resource`` (A1, B1, ..., H1, A2, ...) --
    any realistic PLR channel count (<=96) has a distinct physical spot."""
    wells = [f"{resource}.{row}{col}" for col in range(1, 13) for row in _PLATE_ROWS]
    if n > len(wells):
        raise ValueError(f"{resource} (96 wells) cannot supply {n} distinct wells")
    return wells[:n]


def _expand_ref(ref: str) -> list[str]:
    """A single grounded dotted ref (``name.A1`` or ``name.A1:C1``) -> the
    individual well refs it addresses. Mirrors ``verify/grounding.py``'s
    ``ground_ref`` exactly (same ``expand_string_range`` PLR's own INCLUSIVE
    colon-range ``__getitem__`` branch uses) -- a SINGLE ref string can
    itself address multiple physical wells/channels. (260828 finding: a
    scalar colon-range ref like ``"plate.D1:F1"`` was silently treated as
    ONE channel, arming only 1 tip for a call that actually needs 3.)"""
    base, _, tail = ref.partition(".")
    if not tail or ":" not in tail:
        return [ref]
    return [f"{base}.{pos}" for pos in expand_string_range(tail)]


def _expand_channel_wells(refs: Any) -> list[str]:
    """The full flat list of individual wells ``refs`` (a single ref string
    or a list of ref strings) addresses, expanding any colon-range ref
    first. Matches position-for-position against the call's flat
    ``volume_ul`` list, same as the real dispatcher's own
    ``len(grounded) == len(vols)`` invariant (``verify/dispatcher.py``'s
    ``_wrap_vols``)."""
    ref_list = refs if isinstance(refs, list) else [refs]
    wells: list[str] = []
    for ref in ref_list:
        wells.extend(_expand_ref(ref))
    return wells

#: Well/slice token inside a source-text subscript, e.g. "A1" or "A1:H1".
_WELL_TOKEN = r"[A-Ha-h]\d{1,2}(?::[A-Ha-h]\d{1,2})?"
#: name['A1'] / name["A1:H1"] -- a literal, statically-groundable well ref.
_BRACKET_REF = re.compile(rf"^(\w+)\[(['\"])({_WELL_TOKEN})\2\]$")
#: bare whole-resource name (no subscript at all).
_BARE_NAME = re.compile(r"^\w+$")
_CANONICAL_TIP_RACK = "tip_rack"


@dataclass(frozen=True)
class ExecutionVerifyResult:
    """Outcome of attempting execution-verify on one mined call."""

    ran: bool
    skipped: bool
    skip_reason: str | None
    passed: bool
    summary: dict[str, Any] | None


def _normalize_ref(value: Any, resource_type: str | None) -> str | None:
    """A mined symbolic-ref VALUE -> the harness's dotted grammar, or None
    if it's not a literal, statically-groundable reference (a variable name,
    an index expression, a slice built from a loop variable, ...).

    ``resource_type`` gates which BARE (no-subscript) names are trusted:
    "plate"/"lid"/"resource" params legitimately address a WHOLE resource by
    bare name (matches the schema). A bare name for "container"/"tip_spot"
    is inherently ambiguous from source text alone -- real notebook code
    routinely binds a variable to an ALREADY-INDEXED single well/tip-spot
    object before calling the verb (e.g. ``tube = plate['A1']; dispense
    (tube, ...)``), which reads identically to "the whole container" in the
    mined text; treating it as "the whole Plate" would be a false-negative
    execution-verify rejection, not a real defect, so it's left ungroundable
    (skipped) instead of guessed at.
    """
    if not isinstance(value, str):
        return None
    m = _BRACKET_REF.match(value)
    if m:
        name, _quote, well = m.groups()
        # verify/deck.py's DeckFactory always builds exactly ONE tip rack,
        # named "tip_rack" -- a real notebook's own rack variable name
        # (e.g. "tiprack", "tr0", "tip_rack_20") never matches that literal
        # name, so ground it against the canonical rack regardless of what
        # the source called it (same reasoning as floor_gen.synth's fix).
        rack = _CANONICAL_TIP_RACK if resource_type == "tip_spot" else name
        return f"{rack}.{well.upper()}"
    if resource_type in ("container", "tip_spot"):
        return None
    if _BARE_NAME.match(value):
        return value
    return None


def _normalize_volume(value: Any) -> float | None:
    """A mined literal-float VALUE -> a real float, or None if it's source
    text for a variable/computed expression (e.g. "sample_volume_ul * 0.8",
    or a bare variable name like "volume_ul")."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _normalize_params(name: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """The full param dict -> a harness-groundable form, or None if ANY
    param is a variable/computed expression the harness cannot resolve."""
    try:
        rows = params_of(name)
    except KeyError:
        return None
    known = {spec.name: spec for spec in rows}
    normalized: dict[str, Any] = {}
    for key, value in params.items():
        spec = known.get(key)
        if spec is None:
            continue  # not a canonical param (shouldn't happen: miner.py's own namespace filter)
        is_list = isinstance(value, list)
        values = value if is_list else [value]

        if spec.kind is ParamKind.SYMBOLIC_RESOURCE_REF:
            refs = [_normalize_ref(v, spec.resource_type) for v in values]
            if any(r is None for r in refs):
                return None
            normalized[key] = refs if is_list else refs[0]
        elif spec.plr_type in ("float", "List[float]", "Optional[List[float]]"):
            nums = [_normalize_volume(v) for v in values]
            if any(n is None for n in nums):
                return None
            normalized[key] = nums if is_list else nums[0]
        else:
            # Literal str-ish params (what="tips", at=well positions for
            # read_*): kept as-is if already plain strings; those verbs are
            # unsupported by SUPPORTED_TOOLS anyway (see caller), so this
            # branch is effectively only "what" for discard_tips today.
            if all(isinstance(v, str) for v in values):
                normalized[key] = value
            else:
                return None
    return normalized


def _resource_type_holders(name: str, params: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for spec in params_of(name):
        if spec.kind is ParamKind.SYMBOLIC_RESOURCE_REF and spec.resource_type == "resource":
            value = params.get(spec.name)
            if isinstance(value, str):
                names.append(value)
            elif isinstance(value, list):
                names.extend(v for v in value if isinstance(v, str))
    return list(dict.fromkeys(names))


def _precondition_plan(
    name: str, params: dict[str, Any]
) -> tuple[str | None, list[dict[str, Any]], dict[str, str], dict[str, float]]:
    """Same PLR-precondition scaffolding as floor_gen.exec_verify's helper
    of the same name -- see that module's docstring for the full rationale
    (tip-mount / seeded-liquid preconditions a single mined call can't carry
    on its own)."""
    if name not in SUPPORTED_TOOLS:
        return (
            f"{name!r} has no LiquidHandler-chatterbox execution path (non-liquid-handler "
            "receiver; the P2.2 harness's LH_BACKENDS covers liquid handling only)",
            [], {}, {},
        )
    if name == "transfer" and params.get("volume_ul") is None:
        return (
            "transfer without volume_ul cannot be deterministically post-conditioned by "
            "the P2.2 harness (documented checks.py limitation)",
            [], {}, {},
        )

    # transfer/discard_tips always use exactly one PLR channel -- transfer
    # internally does ONE aspirate(resources=[source]) then loops
    # dispense(..., use_channels=[0]) serially over every target (PLR's real
    # liquid_handler.py), so it never needs N-tip arming regardless of how
    # many targets it has. Do not "fix" this branch by symmetry with
    # aspirate/dispense below.
    pickup = {"name": "pick_up_tips", "params": {"at": [_DUMMY_TIP_SPOT]}}

    if name == "transfer":
        total = sum(float(v) for v in params.get("volume_ul") or [])
        seeds = {params["source"]: total} if total > 0 else {}
        return None, [pickup], {}, seeds

    if name == "aspirate":
        # aspirate's own source/volume_ul are schema-declared list
        # cardinality: a single call can name N parallel resources (as a
        # Python list of refs, OR as ONE colon-range ref string spanning N
        # wells), and PLR requires one distinct tip per resource
        # (use_channels defaults to range(len(resources)); a second pickup
        # on an occupied channel raises HasTipError). Arm N tips, not
        # always 1.
        sources = _expand_channel_wells(params["source"])
        vols = params["volume_ul"] if isinstance(params["volume_ul"], list) else [params["volume_ul"]]
        pickup_n = {"name": "pick_up_tips", "params": {"at": _row_major_wells(_TIP_RACK, len(sources))}}
        return None, [pickup_n], {}, dict(zip(sources, vols))

    if name == "dispense":
        # Same N-tip requirement as aspirate. dispense pulls FROM each
        # mounted tip's own tracked volume; prime all N channels via ONE
        # synthetic aspirate addressing N distinct prime wells (aspirate's
        # own resources/vols are list-typed, so this is a single
        # well-formed prefix call, not N separate ones).
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

    return None, [], {}, {}


def execution_verify_call(call: MinedCall, *, record_id: str) -> ExecutionVerifyResult:
    """Attempt real execution-verify on one mined call. Never raises."""
    real_params = _normalize_params(call.name, call.params)
    if real_params is None:
        return ExecutionVerifyResult(
            ran=False, skipped=True,
            skip_reason=(
                "mined call references a variable/computed value (not a literal deck ref "
                "or numeric volume) that the P2.2 harness's static grounding can't resolve "
                "from source text alone; execution-verify skipped, not rejected"
            ),
            passed=True, summary=None,
        )

    real_call = {"name": call.name, "params": real_params}
    skip_reason, prefix, extra_resources, seed_volumes = _precondition_plan(call.name, real_params)
    if skip_reason is not None:
        return ExecutionVerifyResult(ran=False, skipped=True, skip_reason=skip_reason, passed=True, summary=None)

    call_sequence = [*prefix, real_call]
    verify_intent = {
        "record_id": record_id,
        "utterance": "",
        "source": "notebook",
        "calls": [{"name": c["name"], "params": c["params"]} for c in call_sequence],
        "expected_effects": [],  # see floor_gen.exec_verify's docstring for why
    }
    layout = DeckLayout(
        resources=dict(extra_resources),
        seed_volumes=dict(seed_volumes),
        holders=_resource_type_holders(call.name, real_params),
    )

    try:
        result = run_verify_sync(call_sequence=call_sequence, intent_record=verify_intent, layout=layout)
    except Exception as exc:  # noqa: BLE001 - harness-level failure; never crash the run
        summary = {
            "passed": False,
            "backend": None,
            "error": f"{type(exc).__name__}: {exc}",
            # See verify.failure_taxonomy module docstring for the category
            # set and why a flat rejection count isn't enough (260828).
            "category": classify_exception(exc),
            "checks": [],
        }
        return ExecutionVerifyResult(ran=True, skipped=False, skip_reason=None, passed=False, summary=summary)

    summary = {
        "passed": result["passed"],
        "backend": result["backend"],
        "error": result["error"],
        # None when passed=True. Otherwise: verifier.verify() absorbs any
        # dispatch/execution exception INTERNALLY and reports it via the
        # "execution_ok" named check rather than raising -- so a real
        # NoTipError etc. never reaches the except block above; classify
        # from the checks list, which distinguishes an absorbed-exception
        # failure from a genuine post-execution effect mismatch (260828
        # finding, see verify.failure_taxonomy module docstring shape #2).
        "category": None if result["passed"] else classify_check_failure(result["checks"]),
        "checks": [{"name": c["name"], "passed": c["passed"], "detail": c["detail"]} for c in result["checks"]],
    }
    return ExecutionVerifyResult(
        ran=True, skipped=False, skip_reason=None, passed=result["passed"], summary=summary
    )
