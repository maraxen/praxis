"""Post-condition + agreement checks for the P2.2 verify harness.

Two independent axes (spec rev2 §7 AC-2.2.x):

AC-2.2.2 POST-CONDITIONS -- computed from the EXECUTED calls' own claims and
confirmed against measured tracker state:
* mounted-tip deltas (pick_up_tips => present; drop/discard => absent),
  simulated sequentially through the sequence then compared to the live head;
* per-well used-volume deltas measured via ``VolumeTracker.get_free_volume()``
  snapshot diffs, cross-checked against the independent ``serialize_state``
  (pending_volume) channel;
* move verbs have NO tracker deltas (C-M-lizard convention, see package
  docstring): their post-condition is a target-location assertion via deck
  serialization topology.

AC-2.2.3 SLOT AGREEMENT -- every grounded arg of the executed call must match
the intent record's expected binding for that call index; plus the parse-layer
``check_intent_agreement`` from the P2.0 contract as a consistency axis.

A wrong-slot call passes the first axis and fails the second BY DESIGN.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from coxswain.plr.intent_record import (
    IntentRecord,
    PredictedCall,
    check_intent_agreement,
)
from coxswain.plr.param_namespace import ParamKind, params_of

__all__ = ["Check", "ExecutedCall", "run_all_checks"]

#: tool -> method_contracts.EffectType vocabulary join (by-string, per P2.0).
_TOOL_EFFECTS = {
    "pick_up_tips": "loads_tips",
    "drop_tips": "drops_tips",
    "discard_tips": "drops_tips",
    "aspirate": "aspirates",
    "dispense": "dispenses",
    "transfer": "transfers",
    "stamp": "transfers",
}

#: plr_arg carrying the wells a liquid effect lands on / takes from.
_WELL_ARGS = {"aspirates": "resources", "dispenses": "resources",
              "transfers": "targets"}


@dataclass
class Check:
    """One named boolean check with human-readable evidence."""

    name: str
    passed: bool
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass
class ExecutedCall:
    """What actually ran: tool + grounded kwargs + bindings + touched objects."""

    index: int
    tool: str
    kwargs: Mapping[str, Any]
    plan_result: Any = None  # dispatcher.PlanResult

    @property
    def bindings(self) -> list:
        return list(self.plan_result.bindings)

    def touched(self, plr_arg: str) -> list[Any]:
        return self.plan_result.touched.get(plr_arg, [])

    def ref_of(self, plr_arg: str) -> str | None:
        for b in self.plan_result.bindings:
            if b.plr_arg == plr_arg:
                return b.ref
        return None


def _obj_name(obj: Any) -> str:
    return getattr(obj, "name", None) or f"<{type(obj).__name__}>"


# ---------------------------------------------------------------------------
# AC-2.2.2 volume axis
# ---------------------------------------------------------------------------

def _expected_volume_deltas(executed: list[ExecutedCall]) -> tuple[dict[str, float], list[Check]]:
    """Accumulate expected USED-volume deltas per well NAME across the whole
    sequence (handles repeated touches and multi-well ranges)."""
    deltas: dict[str, float] = {}
    problems: list[Check] = []
    for call in executed:
        if call.tool == "aspirate":
            vols = call.kwargs.get("vols", [])
            for well, v in zip(call.touched("resources"), vols):
                deltas[_obj_name(well)] = deltas.get(_obj_name(well), 0.0) - float(v)
        elif call.tool == "dispense":
            vols = call.kwargs.get("vols", [])
            for well, v in zip(call.touched("resources"), vols):
                deltas[_obj_name(well)] = deltas.get(_obj_name(well), 0.0) + float(v)
        elif call.tool == "transfer":
            tvs = call.kwargs.get("target_vols") or []
            src = call.touched("source")
            tgts = call.touched("targets")
            if not tvs:
                # vendored transfer distributes source_vol equally; without an
                # explicit volume there is no deterministic post-condition.
                problems.append(Check(
                    "volume_delta", False,
                    f"call {call.index}: transfer without volume_ul cannot be "
                    f"post-conditioned deterministically (recorded deviation)",
                ))
                continue
            if len(src) == 1:
                deltas[_obj_name(src[0])] = (
                    deltas.get(_obj_name(src[0]), 0.0) - sum(float(v) for v in tvs)
                )
            for well, v in zip(tgts, tvs):
                deltas[_obj_name(well)] = deltas.get(_obj_name(well), 0.0) + float(v)
    return deltas, problems


def _measured_used_delta(name: str, before, after) -> tuple[float | None, float | None]:
    """Used-volume change via get_free_volume() snapshot diffs. Returns
    (delta, pending_volume_delta_from_serialize_state)."""
    fb = before["free_volume"].get(name)
    fa = after["free_volume"].get(name)
    if fb is None or fa is None:
        return None, None
    delta = -(fa - fb)
    pb = before["resources"].get(name, {}).get("pending_volume")
    pa = after["resources"].get(name, {}).get("pending_volume")
    # pending_volume tracks USED volume directly (unlike free_volume, which is
    # max-relative -- hence the negation above).
    snap_delta = None if (pb is None or pa is None) else float(pa) - float(pb)
    return delta, snap_delta


def _check_volumes(executed: list[ExecutedCall], before, after,
                   tolerance_ul: float) -> list[Check]:
    expected, problems = _expected_volume_deltas(executed)
    checks: list[Check] = list(problems)
    for name, want in sorted(expected.items()):
        got, snap = _measured_used_delta(name, before, after)
        if got is None:
            checks.append(Check(f"volume_delta:{name}", False,
                                "well missing from a state snapshot"))
            continue
        ok = abs(got - want) <= tolerance_ul
        cross = "" 
        if snap is not None:
            cross_ok = abs(snap - got) <= tolerance_ul
            ok = ok and cross_ok
            cross = "; serialize_state cross-check " + ("ok" if cross_ok else f"MISMATCH ({snap:+.6f})")
        checks.append(Check(
            f"volume_delta:{name}", ok,
            f"expected {want:+.6f} uL used-delta, measured {got:+.6f}{cross}",
        ))
    if not expected and not problems:
        checks.append(Check("volume_delta", True, "no liquid ops executed"))
    return checks


# ---------------------------------------------------------------------------
# AC-2.2.2 tip axis
# ---------------------------------------------------------------------------

def _check_tips(executed: list[ExecutedCall], before, after) -> Check:
    virtual_mounted = 0
    spot_expect: dict[str, bool] = {}
    details: list[str] = []
    ok = True

    for call in executed:
        if call.tool == "pick_up_tips":
            spots = call.touched("tip_spots")
            virtual_mounted += len(spots)
            for s in spots:
                spot_expect[_obj_name(s)] = False   # rack spot EMPTIED
            details.append(f"call {call.index}: pick_up_tips x{len(spots)}")
        elif call.tool == "drop_tips":
            spots = call.touched("tip_spots")
            if virtual_mounted < len(spots):
                ok = False
                details.append(f"call {call.index}: dropping {len(spots)} tips "
                               f"with only {virtual_mounted} mounted")
            virtual_mounted = max(0, virtual_mounted - len(spots))
            for s in spots:
                spot_expect[_obj_name(s)] = True    # spot FILLED
        elif call.tool == "discard_tips":
            details.append(f"call {call.index}: discard_tips dropped "
                           f"{virtual_mounted} mounted")
            virtual_mounted = 0

    measured = after["mounted_tips"]
    if measured != virtual_mounted:
        ok = False
        details.append(f"mounted tips: measured {measured} != expected {virtual_mounted}")
    else:
        details.append(f"mounted tips {measured} == expected {virtual_mounted}")

    return Check("tips_delta", ok, "; ".join(details) or "no tip ops")


def _spot_occupancy(executed: list[ExecutedCall]) -> dict[str, tuple[int, object, bool]]:
    """name -> (call_index, spot, expected FINAL occupancy), sequential:"""
    final: dict[str, tuple[int, object, bool]] = {}
    order: dict[str, int] = {}
    for call in executed:
        if call.tool == "pick_up_tips":
            spots = call.touched("tip_spots")
            expect = False
        elif call.tool == "drop_tips":
            spots = call.touched("tip_spots")
            expect = True
        else:
            continue
        for s in spots:
            name = _obj_name(s)
            final[name] = (call.index, s, expect)
            order[name] = call.index
    return final


# ---------------------------------------------------------------------------
# Move verbs: C-M-lizard convention -- location assertion via serialization
# ---------------------------------------------------------------------------

def _find_in_topology(topology: Mapping[str, Any], name: str) -> Mapping[str, Any] | None:
    def walk(children):
        for c in children or []:
            if c.get("name") == name:
                return c
            found = walk(c.get("children"))
            if found is not None:
                return found
        return None
    return walk(topology.get("children"))


def _check_moves(executed: list[ExecutedCall], after, before) -> list[Check]:
    checks: list[Check] = []
    obj_arg = {"move_resource": "resource", "move_plate": "plate", "move_lid": "lid"}
    for call in executed:
        if call.tool not in obj_arg:
            continue
        moved = call.kwargs.get(obj_arg[call.tool])
        moved_name = _obj_name(moved)
        node = _find_in_topology(after["topology"], moved_name)
        dest = call.kwargs.get("to")
        expected_parent = getattr(dest, "name", None)
        if node is None:
            checks.append(Check(f"move_location:{moved_name}", False,
                                "moved object missing from post-run topology"))
            continue
        parent = node.get("parent_name")
        if expected_parent is not None:
            ok = parent == expected_parent
            detail = f"{moved_name} re-parented to {parent!r} (expected {expected_parent!r})"
        else:
            # Coordinate destination: assert the serialized LOCATION changed
            # vs before rather than the parent chain.
            loc = node.get("location")
            before_node = _find_in_topology(before["topology"], moved_name)
            before_loc = (before_node or {}).get("location")
            ok = loc is not None and loc != before_loc
            detail = f"{moved_name} location {before_loc!r} -> {loc!r}"
        checks.append(Check(f"move_location:{moved_name}", ok, detail))
    return checks


# ---------------------------------------------------------------------------
# Intent effects table (P2.0 join-by-string vocabulary)
# ---------------------------------------------------------------------------

def _effect_evidence(effect: str, target_ref: str, executed: list[ExecutedCall],
                     before, after, tolerance_ul: float) -> tuple[bool, str]:
    def touches(call: ExecutedCall) -> bool:
        # binding refs may be comma-joined lists; match on individual tokens
        return any(
            tok.strip() == target_ref
            for b in call.plan_result.bindings
            for tok in b.ref.split(",")
        )

    if effect == "moves_resource":
        # C-M-lizard convention: no tracker deltas exist; evidence is the
        # serialized target-location assertion.
        movers = [c for c in executed if c.tool.startswith("move_") and touches(c)]
        if not movers:
            return False, f"no executed {effect} reaches {target_ref!r}"
        from verify.checks import _find_in_topology  # local import: same module
        for c in movers:
            moved = c.kwargs.get(next(
                (a for a in ("resource", "plate", "lid") if a in c.kwargs), ""))
            node = _find_in_topology(after["topology"], _obj_name(moved))
            dest = c.kwargs.get("to")
            expected_parent = getattr(dest, "name", None)
            if expected_parent is not None:
                ok = node is not None and node.get("parent_name") == expected_parent
                if ok:
                    return True, f"{_obj_name(moved)} re-parented to {expected_parent!r}"
                return False, (f"{target_ref!r}: parent "
                               f"{(node or {}).get('parent_name')!r} after run")
        return False, f"no {effect} evidence at {target_ref!r}"

    supporting = [
        c for c in executed
        if _TOOL_EFFECTS.get(c.tool) == effect and touches(c)
    ]
    if not supporting:
        return False, f"no executed {effect} touches {target_ref!r}"

    if effect in _WELL_ARGS:
        total = 0.0
        for call in supporting:
            arg = _WELL_ARGS[effect]
            objs = call.touched(arg)
            if effect == "transfers" and call.tool == "transfer":
                objs = call.touched("targets")
            for o in objs:
                d, _ = _measured_used_delta(_obj_name(o), before, after)
                if d is not None:
                    total += d
        if effect == "aspirates":
            total = -total
        if abs(total) <= tolerance_ul:
            return False, f"declared {effect}@{target_ref} but zero measured delta"
        return True, f"measured {total:+.3f} uL at {target_ref}"

    if effect == "loads_tips":
        return _tip_transition_evidence(effect, target_ref, executed,
                                        before, after, want_after=False)
    if effect == "drops_tips":
        return _tip_transition_evidence(effect, target_ref, executed,
                                        before, after, want_after=True)
    return False, f"unsupported effect string {effect!r}"


def _check_effects(intent: IntentRecord, executed: list[ExecutedCall],
                   before, after, tolerance_ul: float) -> Check:
    effects = intent.get("expected_effects") or []
    if not effects:
        return Check("effects_match", True, "no expected_effects declared")
    bad: list[str] = []
    for eff in effects:
        ok, why = _effect_evidence(eff.get("effect", ""), eff.get("target_ref", ""),
                                   executed, before, after, tolerance_ul)
        if not ok:
            bad.append(f"{eff.get('effect')}@{eff.get('target_ref')}: {why}")
    return Check("effects_match", not bad,
                 "all declared effects evidenced" if not bad else "; ".join(bad))


# ---------------------------------------------------------------------------
# AC-2.2.3 slot agreement (execution layer + parse layer)
# ---------------------------------------------------------------------------

def _ref_tokens(binding) -> list[str]:
    return [t.strip() for t in binding.ref.split(",")]


def _tip_transition_evidence(effect: str, target_ref: str,
                             executed: list[ExecutedCall],
                             before, after, *, want_after: bool) -> tuple[bool, str]:
    """loads/drops evidence at SPOT granularity: an executed op of the right
    family touches the named spot AND the spot's FINAL serialized tip
    occupancy matches the declared net effect (empty for loads_tips,
    occupied for drops_tips).

    AUTHORING CONVENTION: expected_effects describe NET observable outcomes.
    A pick-then-return-to-the-same-spot cycle inside one run nets to no
    occupancy change, so such sequences declare drops_tips only (or none);
    the intra-run mechanics are post-conditioned by tips_delta instead."""
    for call in executed:
        if _TOOL_EFFECTS.get(call.tool) != effect:
            continue
        bindings = [b for b in call.plan_result.bindings if b.plr_arg == "tip_spots"]
        spots = call.touched("tip_spots")
        for b in bindings:
            tokens = _ref_tokens(b)
            if len(tokens) != len(spots):
                continue
            for tok, spot in zip(tokens, spots):
                if tok != target_ref:
                    continue
                name = _obj_name(spot)
                occ_before = before["resources"].get(name, {}).get("tip") is not None
                occ_after = after["resources"].get(name, {}).get("tip") is not None
                if occ_after is want_after:
                    return True, f"{name} final occupancy {occ_before}->{occ_after}"
                return False, (f"{name} final occupancy {occ_after}, "
                               f"expected {'occupied' if want_after else 'empty'}")
    return False, f"no executed {effect} touches {target_ref!r}"

def _norm_refs(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_norm_refs(v) for v in value)
    if isinstance(value, str):
        return " ".join(value.split())
    return str(value)


def _check_slot_agreement(call_sequence, intent: IntentRecord) -> list[Check]:
    checks: list[Check] = []
    intended_calls = intent.get("calls", [])
    reasons: list[str] = []

    seq_ok = len(call_sequence) == len(intended_calls)
    if not seq_ok:
        reasons.append(f"sequence length {len(call_sequence)} != intended "
                       f"{len(intended_calls)}")

    for i, call in enumerate(call_sequence):
        if not seq_ok:
            break
        want = intended_calls[i]
        if call.get("name") != want.get("name"):
            reasons.append(f"{i}: executed {call.get('name')!r} != intended "
                           f"{want.get('name')!r}")
            continue
        rows = {s.name: s for s in params_of(call["name"])}
        for arg, spec in rows.items():
            got = call.get("params", {}).get(arg)
            exp = want.get("params", {}).get(arg)
            if got is None and exp is None:
                continue
            if spec.kind is ParamKind.LITERAL:
                if got != exp:
                    reasons.append(f"{i}.{arg}: literal {got!r} != intended {exp!r}")
            elif _norm_refs(got) != _norm_refs(exp):
                reasons.append(
                    f"{i}.{arg}: grounded {_norm_refs(got)!r} != intended binding "
                    f"{_norm_refs(exp)!r}"
                )
    checks.append(Check(
        "slot_agreement", not reasons,
        "every grounded argument matches the intent-record binding"
        if not reasons else "BINDING MISMATCH: " + "; ".join(reasons),
    ))

    # Parse-layer consistency via the P2.0 shared contract (D11).  Harness
    # fixtures carry UNGROUNDED ref strings, so the deterministic derivation
    # reports every symbolic arg as an unresolved slot; the intent side is
    # therefore NORMALIZED through the same derive_call_gaps before the
    # comparison -- both sides re-derived, nothing hand-authored.
    from coxswain.plr.intent_record import DerivedSlot
    from coxswain.plr.slot_derivation import derive_call_gaps

    def gap_view(call: Mapping[str, Any]) -> dict[str, Any]:
        derived = derive_call_gaps(call.get("name"), call.get("params") or {})
        return {
            "name": call.get("name"),
            "params": dict(call.get("params") or {}),
            "missing_required": list(derived.missing_required),
            "unresolved_slots": [
                {"arg_name": s.arg_name, "reference": s.reference,
                 "resource_type": s.resource_type}
                for s in derived.unresolved_slots
            ],
        }

    normalized_intent = {
        "record_id": intent.get("record_id"),
        "utterance": intent.get("utterance", ""),
        "source": "golden",
        "calls": [gap_view(c) for c in intended_calls],
        "expected_effects": [],
    }
    agreement = check_intent_agreement(
        [PredictedCall(name=c.get("name"), params=c.get("params") or {})
         for c in call_sequence],
        normalized_intent,  # type: ignore[arg-type]
    )
    checks.append(Check(
        "intent_agreement_parse_layer", agreement.overall,
        "names/params/gaps re-derived clean (D11)" if agreement.overall
        else "; ".join(agreement.reasons),
    ))
    return checks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_all_checks(call_sequence, intent: IntentRecord,
                   executed: list[ExecutedCall],
                   before, after, tolerance_ul: float,
                   execution_error: str | None) -> list[Check]:
    """Run every axis; returns the ordered checks list for the result dict."""
    checks: list[Check] = []
    checks.append(Check(
        "execution_ok", execution_error is None,
        "execution completed without error" if execution_error is None
        else f"execution failed: {execution_error}",
    ))
    checks.extend(_check_volumes(executed, before, after, tolerance_ul))
    checks.append(_check_tips(executed, before, after))

    # Spot occupancy evidence (pick => empty, drop => filled), folded into one
    # check so the tip axis stays a single boolean like the others.
    occupancy_bad: list[str] = []
    for name, (idx, spot, expect_occupied) in _spot_occupancy(executed).items():
        has_tip = bool(getattr(spot.tracker, "has_tip", None))
        if has_tip != expect_occupied:
            occupancy_bad.append(f"call {idx}: {name} occupied={has_tip}, "
                                 f"expected {expect_occupied}")
    if occupancy_bad:
        base = next((c for c in checks if c.name == "tips_delta"), None)
        if base is not None:
            base.passed = False
            base.detail += "; " + "; ".join(occupancy_bad)

    checks.extend(_check_moves(executed, after, before))
    checks.append(_check_effects(intent, executed, before, after, tolerance_ul))
    checks.extend(_check_slot_agreement(call_sequence, intent))
    return checks
