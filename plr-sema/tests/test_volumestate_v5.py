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
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from plr_sema.check import ir, volumestate
from plr_sema.verdict import Finding, Verdict

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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
