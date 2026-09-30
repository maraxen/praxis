"""Unit-level pins for the §14.5 V5 tip-cell lifecycle and its 260929 amendment.

Spec: `260903_plr-sema-volume-increment.md` §14.5 V5. The 260929 amendment
(PLR 1.0 bump): a tip movement with no modelled effect -- or a modelled
departure whose channels are unresolved -- resets EVERY recorded tip cell to
`TOP`, in addition to setting `tips_dirty`.

Why a unit-level file. At PLR 1.0 the rewritten `TipTracker` leaves
`pick_up_tips`/`drop_tips` with NO derived `channel_effect`, so the committed
`derived_contracts.json` can no longer exercise V5's *modelled* bullets, and
the graph-level retip fixture (`test_check_graph.py::
test_ac_14_5_e_retip_dirty_tip_never_safe`) now travels the *unmodelled*
bullet. These tests drive `volumestate.evaluate_call` directly with the REAL
`LiquidHandler.aspirate`/`dispense` contract entries and receiver state, and
SYNTHETIC pick_up/drop contract entries (`{}` = no derived effect, exactly
the 1.0 shape; `{"channel_effect": "HAS_TIP"/"NO_TIP"}` = the shape the old
pin derived), so both shapes stay pinned regardless of what the derivation
produces.

The sequence under test is the round-1 O4 counterexample:
pick_up / aspirate 50 / drop / pick_up / dispense 50.

**Negative control.** `test_negative_control_*` re-runs the retip sequences
with `VolumeWalk.reset_tip_cells` patched to a no-op (the pre-amendment
behaviour) and asserts they then report `SAFE` -- the false verdict the
amendment removes. If a control ever stops observing `SAFE`, its sequence has
stopped discriminating and the pins above it are vacuous.

**Modelled path (T62, spec `260929_plr-sema-plr1-tip-effect-increment.md`
section 18.6 / AC-18.5).** The 260929 tip-effect increment makes the committed
`derived_contracts.json` carry `channel_effect` for `pick_up_tips`
(`HAS_TIP`) and `drop_tips` (`NO_TIP`) again, and for `load_state` /
`update_head_state` (`widen`, with no resolvable channel set). The last section
of this file drives V5 through THOSE REAL entries, not the synthetic ones
above, so the modelled path is pinned against what the analyzer really ships.
Its negative controls remove V5's modelled tip lifecycle (`pickup`/`drop`) or the
channel-set reset and must observe the false `SAFE`.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from plr_sema.check import check_graph, ir, volumestate
from plr_sema.verdict import Finding, PlrSite, Verdict

PLR_SEMA_ROOT = Path(__file__).resolve().parents[1]
_DERIVED = json.loads((PLR_SEMA_ROOT / "data" / "derived_contracts.json").read_text(encoding="utf-8"))
_CONTRACTS: dict[str, Any] = _DERIVED["contracts"]
_LH_STATE: dict[str, Any] = _DERIVED["receiver_state"]["LiquidHandler"]

_ENV = frozenset({"does_volume_tracking"})

_LH = 0
_WELL = 1
_RACK = 2

_ASPIRATE = _CONTRACTS["LiquidHandler.aspirate"]
_DISPENSE = _CONTRACTS["LiquidHandler.dispense"]
_SET_VOLUME = {"is_volume_setter": True}

#: pick_up_tips / drop_tips as PLR 1.0 leaves them: no derived tip effect.
_UNMODELLED: dict[str, Any] = {}
#: ... and as the old pin derived them.
_PICKUP_MODELLED: dict[str, Any] = {"channel_effect": "HAS_TIP"}
_DROP_MODELLED: dict[str, Any] = {"channel_effect": "NO_TIP"}

_TIP_SIDE_QUALNAME = "VolumeTracker.validate_remove_liquid"

_Step = tuple[ir.Call, dict[str, Any]]


def _lit(x: Any) -> ir.Lit:
    return ir.Lit(x)


def _seq(*items: ir.Value) -> ir.Seq:
    return ir.Seq(tuple(items))


def _seed(volume: float) -> _Step:
    call = ir.Call(receiver=_WELL, receiver_type="VolumeTracker", method="set_volume", kwargs={"volume": _lit(volume)})
    return call, _SET_VOLUME


def _pickup(contract: dict[str, Any]) -> _Step:
    kwargs = {"tip_spots": _seq(ir.Ref(_RACK, "A1")), "use_channels": _seq(_lit(0))}
    return ir.Call(receiver=_LH, receiver_type="LiquidHandler", method="pick_up_tips", kwargs=kwargs), contract


def _drop(contract: dict[str, Any], *, channels_top: bool = False) -> _Step:
    if channels_top:
        # Unresolvable channels AND unresolvable default-param operand:
        # `tipstate.channels_for_call` -> None (rule 4). A rack Ref is still
        # mentioned so the unmodelled arm, where taken, still sees a resource.
        kwargs = {"tip_spots": ir.Top(), "use_channels": ir.Top(), "waste": ir.Ref(_RACK, "A1")}
    else:
        kwargs = {
            "tip_spots": _seq(ir.Ref(_RACK, "A1")),
            "use_channels": _seq(_lit(0)),
            "allow_nonzero_volume": _lit(True),
        }
    return ir.Call(receiver=_LH, receiver_type="LiquidHandler", method="drop_tips", kwargs=kwargs), contract


def _aspirate(vol: float) -> _Step:
    kwargs = {"resources": _seq(ir.Ref(_WELL)), "vols": _seq(_lit(vol)), "use_channels": _seq(_lit(0))}
    return ir.Call(receiver=_LH, receiver_type="LiquidHandler", method="aspirate", kwargs=kwargs), _ASPIRATE


def _dispense(vol: float) -> _Step:
    kwargs = {"resources": _seq(ir.Ref(_WELL)), "vols": _seq(_lit(vol)), "use_channels": _seq(_lit(0))}
    return ir.Call(receiver=_LH, receiver_type="LiquidHandler", method="dispense", kwargs=kwargs), _DISPENSE


def _run(steps: list[_Step]) -> tuple[volumestate.VolumeWalk, list[list[Finding]]]:
    """Thread `volumestate.evaluate_call` over `steps`.

    Returns the final walk and, per step, that step's findings.
    """
    walk = volumestate.VolumeWalk()
    out: list[list[Finding]] = []
    for i, (call, contract) in enumerate(steps):
        state = _LH_STATE if call.receiver_type == "LiquidHandler" else None
        findings = volumestate.evaluate_call(f"op_{i}", call, contract, state, walk, env=_ENV, poisoned=False)
        out.append(list(findings))
    return walk, out


def _tip_side(findings: list[Finding]) -> Finding:
    tip = [f for f in findings if f.plr_site is not None and f.plr_site.qualname == _TIP_SIDE_QUALNAME]
    assert len(tip) == 1, f"expected exactly one tip-side finding, got {findings!r}"
    return tip[0]


def _retip(pickup: dict[str, Any], drop: dict[str, Any]) -> list[_Step]:
    """Build pick_up / aspirate 50 / drop / pick_up / dispense 50 (the O4 shape)."""
    return [_seed(100.0), _pickup(pickup), _aspirate(50.0), _drop(drop), _pickup(pickup), _dispense(50.0)]


def _unresolved_channels_retip() -> list[_Step]:
    """Modelled drop with unresolved channels, then an UNMODELLED pickup."""
    return [
        _seed(100.0),
        _pickup(_PICKUP_MODELLED),
        _aspirate(50.0),
        _drop(_DROP_MODELLED, channels_top=True),
        _pickup(_UNMODELLED),
        _dispense(50.0),
    ]


# ---------------------------------------------------------------------------
# The soundness fix: an unmodelled tip movement forgets every tip volume.
# ---------------------------------------------------------------------------


def test_unmodelled_retip_dirty_tip_is_never_safe() -> None:
    """PLR-1.0 shape (no derived tip effect): the O4 sequence is never SAFE.

    Before the amendment the tip cell recorded by `aspirate(50)`
    (`[50, +inf]`) survived the unmodelled drop, so the second tip's
    `dispense(50)` was reported SAFE -- but the second tip is a fresh object
    with used volume 0, and PLR raises.
    """
    _, per_step = _run(_retip(_UNMODELLED, _UNMODELLED))
    final = _tip_side(per_step[-1])
    assert final.verdict is Verdict.UNKNOWN
    assert final.reason == "volume_state_unknown"
    assert final.verdict is not Verdict.SAFE


def test_unmodelled_drop_resets_recorded_tip_cell_to_top() -> None:
    """The mechanism, one step earlier: the recorded tip cell is `TOP` after the drop.

    `tips_dirty` is set, and the container cell (the well) is untouched.
    """
    steps = _retip(_UNMODELLED, _UNMODELLED)[:4]  # seed, pickup, aspirate, drop
    walk_before, _ = _run(steps[:3])
    assert walk_before.get(("tip", 0)) == volumestate.Interval(50.0, float("inf"))
    assert walk_before.tips_dirty is True  # the unmodelled pickup already set it

    walk_after, _ = _run(steps)
    assert walk_after.get(("tip", 0)) == volumestate.TOP
    assert walk_after.tips_dirty is True
    assert walk_after.get(("container", _WELL, None)) == walk_before.get(("container", _WELL, None))
    assert walk_after.get(("container", _WELL, None)) != volumestate.TOP


def test_modelled_drop_with_unresolved_channels_never_safe() -> None:
    """A modelled drop whose channels are unresolvable must forget the recorded cell.

    Which cell departed is unknown, so the recorded cell is forgotten, not
    merely flagged: with the pickup then unmodelled (no rescue by
    `VolumeWalk.pickup`) a stale `[50, +inf]` would give SAFE.
    """
    _, per_step = _run(_unresolved_channels_retip())
    final = _tip_side(per_step[-1])
    assert final.verdict is Verdict.UNKNOWN
    assert final.reason == "volume_state_unknown"


def test_reset_touches_only_tip_cells_and_not_the_dirty_flag() -> None:
    """`reset_tip_cells` leaves container cells and `tips_dirty` alone."""
    walk = volumestate.VolumeWalk()
    walk.set(("tip", 0), volumestate.Interval(50.0, 50.0))
    walk.set(("tip", 3), volumestate.Interval(0.0, 0.0))
    walk.set(("container", 1, None), volumestate.Interval(10.0, 10.0))
    assert walk.tips_dirty is False
    walk.reset_tip_cells()
    assert walk.get(("tip", 0)) == volumestate.TOP
    assert walk.get(("tip", 3)) == volumestate.TOP
    assert walk.get(("container", 1, None)) == volumestate.Interval(10.0, 10.0)
    assert walk.tips_dirty is False  # setting the flag is the caller's job


def test_reset_survives_snapshot_restore_and_join() -> None:
    """The reset is ordinary walk state: snapshots restore it and joins do not undo it."""
    walk = volumestate.VolumeWalk()
    walk.set(("tip", 0), volumestate.Interval(50.0, 50.0))
    arm_a = walk.snapshot()
    walk.reset_tip_cells()
    arm_b = walk.snapshot()
    joined = volumestate.join_walk_states(arm_a, arm_b)
    # One arm reset, the other kept [50, 50]: the join must not resurrect precision.
    assert joined.cells[("tip", 0)].hi == float("inf")
    walk.restore(arm_a)
    assert walk.get(("tip", 0)) == volumestate.Interval(50.0, 50.0)


# ---------------------------------------------------------------------------
# No needless degradation where a tip effect IS derived.
# ---------------------------------------------------------------------------


def test_modelled_provably_empty_retip_keeps_precision() -> None:
    """Derived tip effects (synthetic, old-pin shape): a provably-empty drop stays precise.

    pick_up / aspirate 50 / dispense 50 / drop (provably empty, so
    `tips_dirty` stays false) / pick_up (`[0, 0]`) / aspirate 30 /
    dispense 20 -> the final dispense is still SAFE. The reset applies only
    to unmodelled movement, so it must not degrade this.
    """
    steps = [
        _seed(100.0),
        _pickup(_PICKUP_MODELLED),
        _aspirate(50.0),
        _dispense(50.0),
        _drop(_DROP_MODELLED),
        _pickup(_PICKUP_MODELLED),
        _aspirate(30.0),
        _dispense(20.0),
    ]
    walk, per_step = _run(steps)
    assert walk.tips_dirty is False
    assert _tip_side(per_step[-1]).verdict is Verdict.SAFE


def test_modelled_dirty_retip_still_unknown_not_worse() -> None:
    """Modelled shapes, drop of a NON-empty tip: still UNKNOWN, unchanged by the amendment."""
    _, per_step = _run(_retip(_PICKUP_MODELLED, _DROP_MODELLED))
    final = _tip_side(per_step[-1])
    assert final.verdict is Verdict.UNKNOWN
    assert final.reason == "volume_state_unknown"


def _empty_drop_then_overdraw(pickup: dict[str, Any], drop: dict[str, Any]) -> Verdict:
    """Run pick_up / aspirate 50 / dispense 50 / drop / pick_up / dispense 10.

    The second tip is fresh (used volume 0), so dispensing 10 really raises.
    Returns the final tip-side verdict.
    """
    steps = [
        _seed(100.0),
        _pickup(pickup),
        _aspirate(50.0),
        _dispense(50.0),
        _drop(drop),
        _pickup(pickup),
        _dispense(10.0),
    ]
    _, per_step = _run(steps)
    return _tip_side(per_step[-1]).verdict


def test_modelled_provably_empty_retip_keeps_definite_will_fail() -> None:
    """Precision the amendment must NOT cost where a tip effect is derived.

    After a provably-empty drop the next pickup is `[0, 0]`, so the overdraw
    is a definite WILL_FAIL.
    """
    assert _empty_drop_then_overdraw(_PICKUP_MODELLED, _DROP_MODELLED) is Verdict.WILL_FAIL


def test_unmodelled_twin_of_the_same_sequence_is_unknown_never_definite() -> None:
    """The 1.0 shape of the same sequence has no derived effect, so it is UNKNOWN.

    Nothing proves the drop empty nor the fresh pickup `[0, 0]`. This
    precision was already absent before the amendment (an unmodelled pickup
    never seeded `[0, 0]`); pinned so a future 'improvement' that credits an
    unmodelled movement with `[0, 0]` must be a conscious spec change.
    """
    assert _empty_drop_then_overdraw(_UNMODELLED, _UNMODELLED) is Verdict.UNKNOWN


# ---------------------------------------------------------------------------
# Negative controls: with the pre-amendment behaviour the pins above are wrong.
# ---------------------------------------------------------------------------


def test_negative_control_without_reset_unmodelled_retip_is_unsound_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pre-amendment behaviour (`reset_tip_cells` a no-op): the O4 sequence reports SAFE."""
    monkeypatch.setattr(volumestate.VolumeWalk, "reset_tip_cells", lambda self: None)
    _, per_step = _run(_retip(_UNMODELLED, _UNMODELLED))
    assert _tip_side(per_step[-1]).verdict is Verdict.SAFE


def test_negative_control_without_reset_unresolved_channels_is_unsound_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pre-amendment behaviour: the unresolved-channels departure also reports SAFE."""
    monkeypatch.setattr(volumestate.VolumeWalk, "reset_tip_cells", lambda self: None)
    _, per_step = _run(_unresolved_channels_retip())
    assert _tip_side(per_step[-1]).verdict is Verdict.SAFE


# ---------------------------------------------------------------------------
# T62 / AC-18.5: V5 through the REAL, now-modelled contract entries.
# ---------------------------------------------------------------------------

_PICKUP_REAL: dict[str, Any] = _CONTRACTS["LiquidHandler.pick_up_tips"]
_DROP_REAL: dict[str, Any] = _CONTRACTS["LiquidHandler.drop_tips"]
_LOAD_STATE_REAL: dict[str, Any] = _CONTRACTS["LiquidHandler.load_state"]
_UPDATE_HEAD_STATE_REAL: dict[str, Any] = _CONTRACTS["LiquidHandler.update_head_state"]

_DOES_VOLUME_TRACKING_ENV = frozenset({"does_volume_tracking"})
_REMOVE_LIQUID_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/resources/volume_tracker.py",
    lineno=102,
    qualname="VolumeTracker.validate_remove_liquid",
)


def test_real_contracts_carry_the_modelled_tip_effects() -> None:
    """Precondition of the whole section: the shipped table is on the modelled path.

    If this fails the tests below silently exercise the unmodelled arm again
    (the PLR 1.0 shape) and no longer pin what T62 says they pin.
    """
    assert _PICKUP_REAL.get("channel_effect") == "HAS_TIP"
    assert _DROP_REAL.get("channel_effect") == "NO_TIP"
    assert _LOAD_STATE_REAL.get("channel_effect") == "widen"
    assert _UPDATE_HEAD_STATE_REAL.get("channel_effect") == "widen"


def test_real_contracts_retip_never_safe_and_dirty_flag_is_the_gate() -> None:
    """pick_up / aspirate 50 / drop / pick_up / dispense 50 on the MODELLED path.

    The drop departs a tip whose interval `[50, +inf]` is not provably empty,
    so `tips_dirty` is set by `VolumeWalk.drop` itself (NOT by the amendment's
    `reset_tip_cells`, which only the unmodelled arm calls), the second
    pickup records `TOP`, and the final dispense is `UNKNOWN`, never `SAFE`.
    """
    walk, per_step = _run(_retip(_PICKUP_REAL, _DROP_REAL))
    assert walk.tips_dirty is True
    assert walk.get(("tip", 0)) != volumestate.Interval(0.0, 0.0)
    final = _tip_side(per_step[-1])
    assert final.verdict is Verdict.UNKNOWN
    assert final.reason == "volume_state_unknown"
    assert final.verdict is not Verdict.SAFE


def test_real_contracts_retip_control_without_modelled_lifecycle_is_unsound_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative control for the test above: remove V5's modelled tip lifecycle.

    With `VolumeWalk.pickup` and `VolumeWalk.drop` no-ops the recorded tip
    cell `[50, +inf]` survives the drop and the pickup, and the dispense is
    reported `SAFE`, the false verdict the modelled lifecycle prevents. If this
    stops observing `SAFE`, the sequence above has stopped discriminating.
    """
    monkeypatch.setattr(volumestate.VolumeWalk, "pickup", lambda self, cell: None)
    monkeypatch.setattr(volumestate.VolumeWalk, "drop", lambda self, cell: None)
    _, per_step = _run(_retip(_PICKUP_REAL, _DROP_REAL))
    assert _tip_side(per_step[-1]).verdict is Verdict.SAFE


def test_real_contracts_provably_empty_retip_second_pickup_cell_is_zero_zero() -> None:
    """AC-18.5 precision half.

    pickup / aspirate 50 / dispense 50 / drop / pickup / aspirate 50 /
    dispense 50. The drop departs a provably-empty tip, so `tips_dirty` stays
    false, the second pickup's cell is exactly `[0, 0]`, and the second dispense
    DECIDES (`SAFE`). The amendment must not be what made the retip tests pass:
    here the reset must not fire at all.
    """
    steps = [
        _seed(100.0),
        _pickup(_PICKUP_REAL),
        _aspirate(50.0),
        _dispense(50.0),
        _drop(_DROP_REAL),
        _pickup(_PICKUP_REAL),
    ]
    walk, _ = _run(steps)
    assert walk.tips_dirty is False
    assert walk.get(("tip", 0)) == volumestate.Interval(0.0, 0.0)

    steps += [_aspirate(50.0), _dispense(50.0)]
    walk, per_step = _run(steps)
    assert walk.tips_dirty is False
    assert _tip_side(per_step[-1]).verdict is Verdict.SAFE


def _empty_retip_then_overdraw() -> tuple[Verdict, volumestate.VolumeWalk]:
    """pickup / aspirate 50 / dispense 50 / drop / pickup / dispense 10 (real contracts).

    The second tip is fresh, so dispensing 10 really raises. Returns the final
    tip-side verdict and the walk.
    """
    steps = [
        _seed(100.0),
        _pickup(_PICKUP_REAL),
        _aspirate(50.0),
        _dispense(50.0),
        _drop(_DROP_REAL),
        _pickup(_PICKUP_REAL),
        _dispense(10.0),
    ]
    walk, per_step = _run(steps)
    return _tip_side(per_step[-1]).verdict, walk


def test_real_contracts_provably_empty_retip_overdraw_is_a_definite_will_fail() -> None:
    """The decision the `[0, 0]` cell buys, on the real contracts: a definite WILL_FAIL.

    After a provably-empty drop the second pickup is `[0, 0]`, so dispensing 10
    from it is decided. This is the discriminating half of AC-18.5's precision
    claim (an `aspirate 50` before the dispense would be decided even from
    `TOP`, since `[50, +inf]` already covers 50).
    """
    verdict, walk = _empty_retip_then_overdraw()
    assert walk.tips_dirty is False
    assert verdict is Verdict.WILL_FAIL


def test_real_contracts_precision_control_a_firing_reset_costs_the_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative control: if the pickup recorded `TOP` (a dirty walk), the same overdraw is UNKNOWN.

    So the `WILL_FAIL` above is carried by the modelled `[0, 0]`, not by
    something the amendment's reset could have produced.
    """
    monkeypatch.setattr(volumestate.VolumeWalk, "pickup", lambda self, cell: self.set(cell, volumestate.TOP))
    verdict, _ = _empty_retip_then_overdraw()
    assert verdict is Verdict.UNKNOWN


def _head_state_call(contract: dict[str, Any], method: str) -> _Step:
    """`update_head_state` / `load_state`: neither has a channel keyword nor a channel-default param."""
    kwargs = {"state": ir.Top()} if method == "update_head_state" else {"path": ir.Top()}
    return ir.Call(receiver=_LH, receiver_type="LiquidHandler", method=method, kwargs=kwargs), contract


@pytest.mark.parametrize(
    ("method", "contract"),
    [("update_head_state", _UPDATE_HEAD_STATE_REAL), ("load_state", _LOAD_STATE_REAL)],
)
def test_real_contracts_channel_set_reset_head_state_never_safe(method: str, contract: dict[str, Any]) -> None:
    """AC-18.5 (m9), unit level: a `widen` effect with no resolvable channel set resets.

    pickup / aspirate 50 / `<method>` / pickup / dispense 50. The head-state
    call resolves no channel set, so V5 sets `tips_dirty` and calls
    `reset_tip_cells`; the second pickup (`HAS_TIP`, dirty) records `TOP`, and
    the dispense is not `SAFE`.
    """
    steps = [
        _seed(100.0),
        _pickup(_PICKUP_REAL),
        _aspirate(50.0),
        _head_state_call(contract, method),
    ]
    walk, _ = _run(steps)
    assert walk.tips_dirty is True
    assert walk.get(("tip", 0)) == volumestate.TOP  # every recorded tip cell forgotten

    steps += [_pickup(_PICKUP_REAL), _dispense(50.0)]
    _, per_step = _run(steps)
    final = _tip_side(per_step[-1])
    assert final.verdict is Verdict.UNKNOWN
    assert final.verdict is not Verdict.SAFE


@pytest.mark.parametrize(
    ("method", "contract"),
    [("update_head_state", _UPDATE_HEAD_STATE_REAL), ("load_state", _LOAD_STATE_REAL)],
)
def test_real_contracts_channel_set_reset_control_without_reset_is_unsound_safe(
    monkeypatch: pytest.MonkeyPatch, method: str, contract: dict[str, Any]
) -> None:
    """Negative control: with the reset AND the pickup's dirty gate removed, the m9 sequence is SAFE.

    `pickup` is patched to a no-op (so a dirty walk cannot rescue the stale
    cell by recording `TOP`) and `reset_tip_cells` to a no-op. The stale
    `[50, +inf]` then decides the dispense `SAFE`: the exact false verdict the
    channel-set reset exists to prevent.
    """
    monkeypatch.setattr(volumestate.VolumeWalk, "reset_tip_cells", lambda self: None)
    monkeypatch.setattr(volumestate.VolumeWalk, "pickup", lambda self, cell: None)
    steps = [
        _seed(100.0),
        _pickup(_PICKUP_REAL),
        _aspirate(50.0),
        _head_state_call(contract, method),
        _pickup(_PICKUP_REAL),
        _dispense(50.0),
    ]
    _, per_step = _run(steps)
    assert _tip_side(per_step[-1]).verdict is Verdict.SAFE


def _retip_graph_with(*ops: dict[str, Any]) -> str:
    """The shipped `volume_retip` graph with its ops from `op_4` (aspirate) on replaced by `ops`.

    Keeps `op_1` (setup), `op_2` (set_volume), `op_3` (pick_up_tips); the
    replacements are numbered `op_4`, `op_5`, ... in order.
    """
    graph = json.loads((PLR_SEMA_ROOT / "tests" / "fixtures" / "volume_retip_graph.json").read_text(encoding="utf-8"))
    template = copy.deepcopy(graph["operations"][3])
    head = graph["operations"][:3]
    tail = []
    for i, spec in enumerate(ops, start=4):
        op = copy.deepcopy(template)
        op["id"] = f"op_{i}"
        op["method_name"] = spec["method_name"]
        op["arguments"] = spec["arguments"]
        tail.append(op)
    graph["operations"] = head + tail
    graph["execution_order"] = [o["id"] for o in graph["operations"]]
    return json.dumps(graph)


_ASPIRATE_50 = {"method_name": "aspirate", "arguments": {"resources": "[well]", "vols": "[50]", "use_channels": "[0]"}}
_DISPENSE_50 = {"method_name": "dispense", "arguments": {"resources": "[well]", "vols": "[50]", "use_channels": "[0]"}}
_PICKUP_SPEC = {"method_name": "pick_up_tips", "arguments": {"tip_spots": "[tips]", "use_channels": "[0]"}}


@pytest.mark.parametrize(
    ("method", "arguments"),
    [("update_head_state", {"state": "{0: None}"}), ("load_state", {"state": "{0: None}"})],
)
def test_check_graph_channel_set_reset_fixture(method: str, arguments: dict[str, str]) -> None:
    """AC-18.5 (m9), check level: pickup / aspirate 50 / `<method>` / pickup / dispense 50.

    Through `check_graph` with the shipped contracts: the head-state call
    resolves no channel set, so V5 resets the tip cells, and the tip-state family
    widens the receiver (the second `pick_up_tips` therefore has no
    `WILL_FAIL`, which it WOULD have at the own `has_tip` guard if the first
    tip were still known to be mounted). The final dispense is not `SAFE`.
    """
    contracts_json = (PLR_SEMA_ROOT / "data" / "derived_contracts.json").read_text(encoding="utf-8")
    graph = _retip_graph_with(
        _ASPIRATE_50,
        {"method_name": method, "arguments": arguments},
        _PICKUP_SPEC,
        _DISPENSE_50,
    )
    report = check_graph(graph, contracts_json, env=_DOES_VOLUME_TRACKING_ENV)

    second_pickup = [f for f in report.findings if f.operation_id == "op_6"]
    assert second_pickup, "the second pick_up_tips produced no findings; the fixture is not exercising it"
    assert not any(f.verdict is Verdict.WILL_FAIL for f in second_pickup), second_pickup

    final = [f for f in report.findings if f.plr_site == _REMOVE_LIQUID_SITE and f.operation_id == "op_7"]
    assert len(final) == 1
    assert final[0].verdict is Verdict.UNKNOWN
    assert final[0].verdict is not Verdict.SAFE

    # Control: WITHOUT the head-state call the first tip is still known mounted,
    # so the second pick_up_tips (op_5 here) IS a WILL_FAIL -- proving the
    # "no WILL_FAIL" assertion above is the widening's doing.
    control = _retip_graph_with(_ASPIRATE_50, _PICKUP_SPEC, _DISPENSE_50)
    control_report = check_graph(control, contracts_json, env=_DOES_VOLUME_TRACKING_ENV)
    assert any(f.verdict is Verdict.WILL_FAIL for f in control_report.findings if f.operation_id == "op_5")


def test_check_graph_retip_modelled_path_fixture_with_control() -> None:
    """T62's V5 fixture, check level: the O4 retip on the shipped, modelled contracts.

    pick_up / aspirate 50 / drop / pick_up / dispense 50 is never `SAFE`. The
    control is the graph without the drop/re-pickup, where the tip cell is
    `[50, +inf]` and dispensing 50 is decided: so the `UNKNOWN` above is the
    drop's doing and not a blanket loss of precision.
    """
    contracts_json = (PLR_SEMA_ROOT / "data" / "derived_contracts.json").read_text(encoding="utf-8")
    drop = {
        "method_name": "drop_tips",
        "arguments": {"tip_spots": "[tips]", "use_channels": "[0]", "allow_nonzero_volume": "True"},
    }
    graph = _retip_graph_with(_ASPIRATE_50, drop, _PICKUP_SPEC, _DISPENSE_50)
    report = check_graph(graph, contracts_json, env=_DOES_VOLUME_TRACKING_ENV)
    final = [f for f in report.findings if f.plr_site == _REMOVE_LIQUID_SITE and f.operation_id == "op_7"]
    assert len(final) == 1
    assert final[0].verdict is Verdict.UNKNOWN
    assert final[0].reason == "volume_state_unknown"

    control = _retip_graph_with(_ASPIRATE_50, _DISPENSE_50)
    control_report = check_graph(control, contracts_json, env=_DOES_VOLUME_TRACKING_ENV)
    decided = [f for f in control_report.findings if f.plr_site == _REMOVE_LIQUID_SITE and f.operation_id == "op_5"]
    assert len(decided) == 1
    assert decided[0].verdict is Verdict.SAFE, decided[0]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
