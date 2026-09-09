"""Execution-verify wiring: P2.2 harness (``verify/``) -> P2.3 floor_gen rows.

Only ``ambiguity_class == "none"`` rows carry a COMPLETE, fully-grounded call.
The other three classes are intentionally NOT executable ground truth (D7):

* ``out-of-surface``     -- no call at all (NL clarification only).
* ``missing-slot``       -- a required param is deliberately OMITTED; the
  vendored dispatcher's own ``require()`` would reject it every time.
* ``ambiguous-referent`` -- the ambiguous param carries a deliberately VAGUE
  string (e.g. "the same well") instead of a groundable ref; grounding it
  would fail every time.

Running real execution-verify against either of the latter two would reject
100% of those rows for reasons that have nothing to do with teacher/synth
quality -- the model's CORRECT behavior for these classes is a clarifying
response or a partial tool_call, never a dispatchable PLR call. So this
module only ever RUNS verify() for "none"-class rows; every other class is
reported as ``skipped`` (never rejected).

Even a "none"-class call needs realistic PLR PRECONDITIONS that floor_gen's
one-call-per-cell design doesn't carry on its own: a tip must already be
mounted before aspirate/dispense/drop_tips/discard_tips, and a well/tip must
already hold liquid before it can be aspirated/dispensed from. ``_precondition_plan``
builds the minimal synthetic prefix call(s) + ``DeckLayout`` needed to satisfy
those preconditions, entirely at verify()-call time -- none of this scaffolding
is written into the committed row; only the row's own real call is graded.

(260828, execution-verify wiring task 260828_wire_execution_verify.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pylabrobot.utils.positions import expand_string_range

from coxswain.plr.param_namespace import ParamKind, params_of
from verify import run_verify_sync
from verify.deck import DeckLayout
from verify.dispatcher import SUPPORTED_TOOLS
from verify.failure_taxonomy import classify_check_failure, classify_exception

from floor_gen.synth import SynthExample

__all__ = ["ExecutionVerifyResult", "execution_verify_example"]

#: Synthetic setup scaffolding -- never written into the committed row.
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

#: Human-readable skip reasons, keyed by ambiguity class (D7 rationale above).
_CLASS_SKIP_REASONS: dict[str, str] = {
    "out-of-surface": "out-of-surface rows carry no call sequence (D7 clarify-only example)",
    "missing-slot": "missing-slot calls are intentionally incomplete (D7 required param "
                    "omitted); not executable ground truth, not a synth defect",
    "ambiguous-referent": "ambiguous-referent calls carry a deliberately vague/ungroundable "
                          "ref on the ambiguous param (D7); not executable ground truth, "
                          "not a synth defect",
}


@dataclass(frozen=True)
class ExecutionVerifyResult:
    """Outcome of attempting execution-verify on one synthesized example."""

    #: True iff verify() was actually invoked (only for eligible "none" calls).
    ran: bool
    #: True iff execution-verify was intentionally not attempted (D7 classes,
    #: LH_BACKENDS-unsupported receiver, or a documented harness limitation).
    #: A skip is NEVER a rejection: the row is kept either way.
    skipped: bool
    skip_reason: str | None
    #: Accept/reject signal for the CALLER: False only when verify() actually
    #: ran and returned passed=False (or the harness itself raised) -- never
    #: False for a skip.
    passed: bool
    #: Bounded summary to attach to the committed row on an executed pass;
    #: None when skipped (nothing ran) or rejected (row is dropped, not kept).
    summary: dict[str, Any] | None


def _resource_type_holders(call: dict[str, Any]) -> list[str]:
    """Names of this call's RESOURCE_TYPE_RESOURCE-typed symbolic refs.

    infer_layout() defaults every unrecognized ref name to a bare Plate;
    PLR's move_resource/move_plate/move_lid reject a Plate destination for a
    "resource" (ResourceStack/ResourceHolder) target. DeckLayout.holders is
    the harness's OWN documented mechanism for exactly this ("move/plate
    parking destinations" -- verify/deck.py). Deduped: the same name can
    legitimately appear twice (e.g. move_resource.resource == .destination
    would otherwise register two holders under one name and crash).
    """
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
    """Decide whether ``call`` is verifiable, and if so, what synthetic setup
    it needs. Returns ``(skip_reason, prefix_calls, extra_resources, seed_volumes)``.

    ``skip_reason`` non-None means: do not call verify() at all, treat as
    skipped (not rejected). Otherwise ``prefix_calls`` are prepended to the
    real call for verify()'s call_sequence (and included verbatim in the
    verify-only intent record so the slot-agreement length check is
    trivially satisfied); ``extra_resources``/``seed_volumes`` merge into
    the DeckLayout passed to verify().
    """
    name = call["name"]
    params = call["params"]

    if name not in SUPPORTED_TOOLS:
        # plate_reader (read_absorbance/fluorescence/luminescence) today;
        # LH_BACKENDS/dispatcher.SUPPORTED_TOOLS is liquid-handler-only (no
        # plate-reader chatterbox tip/volume tracker story -- verifier.py's
        # own module docstring, "AC-2.2.2").
        return (
            f"{name!r} has no LiquidHandler-chatterbox execution path (non-liquid-handler "
            "receiver; the P2.2 harness's LH_BACKENDS covers liquid handling only)",
            [], {}, {},
        )

    if name == "transfer" and params.get("volume_ul") is None:
        # checks.py's own _expected_volume_deltas comment: "transfer without
        # volume_ul cannot be post-conditioned deterministically (recorded
        # deviation)". volume_ul is schema-Optional (a real bench transfer
        # can say "transfer to X" with an implicit ratio/ALL semantics), but
        # the vendored dispatcher only supports the explicit target_vols
        # path -- PLR itself raises before any check would even run.
        return (
            "transfer without volume_ul cannot be deterministically post-conditioned by "
            "the P2.2 harness (documented checks.py limitation, not a synth defect)",
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

    # pick_up_tips / stamp / move_resource / move_plate / move_lid: no
    # mounted-tip precondition (empirically confirmed 260828 -- stamp uses a
    # separate PLR mechanism, move_* doesn't pipette).
    return None, [], {}, {}


def execution_verify_example(
    example: SynthExample,
    *,
    record_id: str,
) -> ExecutionVerifyResult:
    """Attempt real execution-verify on ``example``'s ground-truth call.

    Never raises: a harness-level exception that escapes ``verify()`` itself
    (rather than being reported inside its own ``passed=False`` result) is
    caught and reported as a REJECTION, not a generation-run crash.

    Deliberately does NOT pass ``row["intent"]["expected_effects"]``
    (``corpus.py``'s ``_expected_effects()``) through to verify()'s
    ``effects_match`` axis (AC-2.2.3-adjacent). Empirically (260828, full
    committed-matrix run) that axis produces FALSE negatives unrelated to
    real row correctness for two independent, pre-existing reasons this
    module does not attempt to fix (out of scope -- see task report):
    (1) ``_expected_effects()`` derives ``target_ref`` from the call's FIRST
    D11-derived slot regardless of which effect it's attached to (e.g. a
    transfer's "transfers" effect gets target_ref=SOURCE, not destination);
    (2) ``checks.py``'s well-lookup for the "transfers" effect only reads
    the ``targets`` (plural) touched-key, which stamp's dispatcher never
    populates (stamp uses singular ``target``), and discard_tips's "at" is
    dispatch-inert (never touched at all) so "drops_tips" can never be
    evidenced for it. The tracker-based post-condition axis (AC-2.2.2:
    execution_ok/volume_delta/tips_delta/move_location) -- where a
    hallucinated tip/volume call actually gets caught -- is unaffected and
    still fully exercised.
    """
    cls = example.cell.ambiguity_class
    if cls != "none":
        reason = _CLASS_SKIP_REASONS.get(cls, f"ambiguity_class {cls!r} is not executable ground truth")
        return ExecutionVerifyResult(ran=False, skipped=True, skip_reason=reason, passed=True, summary=None)

    (call,) = example.schema_calls  # exactly one call for a "none"-class cell
    real_call = {"name": call["name"], "params": dict(call["params"])}

    skip_reason, prefix, extra_resources, seed_volumes = _precondition_plan(real_call)
    if skip_reason is not None:
        return ExecutionVerifyResult(ran=False, skipped=True, skip_reason=skip_reason, passed=True, summary=None)

    call_sequence = [*prefix, real_call]
    verify_intent = {
        "record_id": record_id,
        "utterance": "",
        "source": "synthetic",
        # Deliberately == call_sequence: this module verifies the row's OWN
        # ground truth actually executes correctly, not a separate
        # prediction-vs-intent deviation (there is no separate "predicted"
        # call here). slot_agreement/intent_agreement_parse_layer are
        # therefore vacuous by construction; execution_ok/volume_delta/
        # tips_delta/move_location are the checks that matter.
        "calls": [{"name": c["name"], "params": c["params"]} for c in call_sequence],
        # expected_effects intentionally omitted -- see docstring above.
        "expected_effects": [],
    }
    layout = DeckLayout(
        resources=dict(extra_resources),
        seed_volumes=dict(seed_volumes),
        holders=_resource_type_holders(real_call),
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
        # Named checks only (pass/fail/detail) -- deliberately NOT the raw
        # state_before/state_after snapshots (full deck serialization),
        # which would bloat every committed row for no auditing benefit
        # beyond what the per-check details already give.
        "checks": [{"name": c["name"], "passed": c["passed"], "detail": c["detail"]} for c in result["checks"]],
    }
    return ExecutionVerifyResult(
        ran=True, skipped=False, skip_reason=None, passed=result["passed"], summary=summary
    )
