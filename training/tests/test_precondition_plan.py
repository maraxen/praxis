"""Direct unit coverage for ``_precondition_plan``'s tip-arming logic.

Both floor_gen and overlay_gen's exec_verify modules previously armed
EXACTLY ONE tip (``_DUMMY_TIP_SPOT``) before every aspirate/dispense call,
regardless of how many resources the call actually addressed. PLR's real
``LiquidHandler.aspirate``/``dispense`` take list-cardinality
``resources``/``vols`` and require one distinct tip per list entry
(``use_channels`` defaults to ``range(len(resources))``; picking up a
second tip on an already-occupied channel raises ``HasTipError`` --
confirmed via ``training/verify/data/plr_preconditions.json`` and PLR's own
source, 260828). These tests exist so a regression here is caught directly,
not only by re-running a full ``agy``-backed pipeline pass and eyeballing
rejection categories (how the prior grounding bug in this same area was
actually caught -- see ``verify/failure_taxonomy.py``'s module docstring).

``transfer`` is deliberately NOT touched by the fix: PLR's real
``transfer()`` does one ``aspirate(resources=[source])`` then loops
``dispense(..., use_channels=[0])`` serially over every target, reusing a
single tip regardless of target count -- so its single-tip pickup was
already correct.
"""

from __future__ import annotations

import floor_gen.exec_verify as floor_pp
import overlay_gen.exec_verify as overlay_pp


def _floor_plan(name: str, params: dict):
    return floor_pp._precondition_plan({"name": name, "params": params})


def _overlay_plan(name: str, params: dict):
    return overlay_pp._precondition_plan(name, params)


# Run every case against both modules (identical fix, different call shape).
_PLANNERS = {"floor_gen": _floor_plan, "overlay_gen": _overlay_plan}


def _tips_armed(prefix_calls: list[dict]) -> list[str]:
    """Every tip spot from every pick_up_tips call in a prefix-call list."""
    spots: list[str] = []
    for call in prefix_calls:
        if call["name"] == "pick_up_tips":
            spots.extend(call["params"]["at"])
    return spots


def test_single_source_aspirate_arms_exactly_one_tip():
    for plan in _PLANNERS.values():
        skip_reason, prefix, extra_resources, seeds = plan(
            "aspirate", {"source": "plate.A1", "volume_ul": [50.0]}
        )
        assert skip_reason is None
        tips = _tips_armed(prefix)
        assert len(tips) == 1
        assert len(set(tips)) == 1
        assert seeds == {"plate.A1": 50.0}


def test_multi_source_aspirate_arms_n_distinct_tips_and_seeds_each_source():
    for plan in _PLANNERS.values():
        sources = ["plate.A1", "plate.B1", "plate.C1"]
        vols = [10.0, 20.0, 30.0]
        skip_reason, prefix, extra_resources, seeds = plan(
            "aspirate", {"source": sources, "volume_ul": vols}
        )
        assert skip_reason is None
        tips = _tips_armed(prefix)
        assert len(tips) == 3
        assert len(set(tips)) == 3  # distinct physical spots -- no HasTipError
        assert seeds == dict(zip(sources, vols))


def test_single_destination_dispense_arms_exactly_one_tip():
    for plan in _PLANNERS.values():
        skip_reason, prefix, extra_resources, seeds = plan(
            "dispense", {"destination": "plate.A1", "volume_ul": [40.0]}
        )
        assert skip_reason is None
        tips = _tips_armed(prefix)
        assert len(tips) == 1
        assert sum(seeds.values()) == 40.0


def test_multi_destination_dispense_arms_n_distinct_tips_and_primes_n_wells():
    for plan in _PLANNERS.values():
        destinations = ["plate.A1", "plate.B1", "plate.C1"]
        vols = [15.0, 25.0, 35.0]
        skip_reason, prefix, extra_resources, seeds = plan(
            "dispense", {"destination": destinations, "volume_ul": vols}
        )
        assert skip_reason is None
        tips = _tips_armed(prefix)
        assert len(tips) == 3
        assert len(set(tips)) == 3
        # exactly one synthetic aspirate priming all N wells at once
        aspirate_prefixes = [c for c in prefix if c["name"] == "aspirate"]
        assert len(aspirate_prefixes) == 1
        assert len(seeds) == 3
        assert sorted(seeds.values()) == sorted(vols)


def test_colon_range_scalar_source_arms_one_tip_per_expanded_well():
    """The real failure mode this fix was actually missing until caught by
    re-running overlay_gen: a mined ``plate["D1:F1"]`` subscript normalizes
    to a SCALAR string "plate.D1:F1" (not a Python list), even though it
    addresses 3 wells via PLR's INCLUSIVE colon-range semantics. A naive
    `isinstance(source, list)` check treats this as 1 channel and arms only
    1 tip, producing "NoTipError: Channel 1 does not have a tip.\""""
    for plan in _PLANNERS.values():
        skip_reason, prefix, extra_resources, seeds = plan(
            "aspirate", {"source": "plate.D1:F1", "volume_ul": [100.0, 50.0, 200.0]}
        )
        assert skip_reason is None
        tips = _tips_armed(prefix)
        assert len(tips) == 3
        assert len(set(tips)) == 3
        assert seeds == {"plate.D1": 100.0, "plate.E1": 50.0, "plate.F1": 200.0}


def test_colon_range_scalar_destination_dispense_arms_one_tip_per_expanded_well():
    for plan in _PLANNERS.values():
        skip_reason, prefix, extra_resources, seeds = plan(
            "dispense", {"destination": "plate.A1:C1", "volume_ul": [10.0, 20.0, 30.0]}
        )
        assert skip_reason is None
        tips = _tips_armed(prefix)
        assert len(tips) == 3
        assert len(set(tips)) == 3
        assert len(seeds) == 3
        assert sorted(seeds.values()) == [10.0, 20.0, 30.0]


def test_transfer_with_multiple_targets_still_arms_exactly_one_tip():
    """transfer's real PLR semantics reuse a single tip serially across every
    target -- multi-target transfer must NOT trigger N-tip arming."""
    for plan in _PLANNERS.values():
        skip_reason, prefix, extra_resources, seeds = plan(
            "transfer",
            {
                "source": "plate.A1",
                "destination": ["plate.B1", "plate.C1", "plate.D1"],
                "volume_ul": [10.0, 10.0, 10.0],
            },
        )
        assert skip_reason is None
        tips = _tips_armed(prefix)
        assert len(tips) == 1
