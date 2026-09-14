"""AC-2.2.2 post-condition tests: tracker deltas on tiny decks."""

import asyncio
import json
from pathlib import Path

from verify import verify

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _load(name):
    data = json.loads((EXAMPLES / name).read_text())
    return data["call_sequence"], data["intent_record"], data.get("deck_layout")


def _run(seq, intent, layout=None, **kw):
    return asyncio.run(verify(seq, intent, layout=layout, **kw))


def test_clean_transfer_volume_deltas_and_snapshots():
    seq, intent, layout = _load("clean_transfer.json")
    r = _run(seq, intent, layout)
    assert r["passed"], [(c["name"], c["detail"]) for c in r["checks"] if not c["passed"]]
    names = {c["name"] for c in r["checks"]}
    assert "volume_delta:source_plate_well_A1" in names
    assert "volume_delta:dest_plate_well_B1" in names
    by_name = {c["name"]: c for c in r["checks"]}
    assert "+50.000000" in by_name["volume_delta:dest_plate_well_B1"]["detail"]
    # state snapshots present and independent channels agree
    assert r["state_before"]["mounted_tips"] == 0
    assert r["state_after"]["mounted_tips"] == 0  # picked 2 then discarded both
    src_before = r["state_before"]["resources"]["source_plate_well_A1"]
    src_after = r["state_after"]["resources"]["source_plate_well_A1"]
    assert src_after["pending_volume"] < src_before["pending_volume"]


def test_pickup_then_discard_tips_delta():
    seq, intent, layout = _load("clean_transfer.json")
    r = _run(seq, intent, layout)
    tips = next(c for c in r["checks"] if c["name"] == "tips_delta")
    assert tips["passed"]
    # pick 2 -> mounted 2 -> discard -> 0
    assert "expected 0" in tips["detail"]


def test_drop_tips_back_into_spots():
    """Pick C1,D1 then drop them back: final occupancy True, mounted 0."""
    seq, intent, layout = _load("aspirate_dispense_drop.json")
    r = _run(seq, intent, layout)
    assert r["passed"], [(c["name"], c["detail"]) for c in r["checks"] if not c["passed"]]
    tips = next(c for c in r["checks"] if c["name"] == "tips_delta")
    assert "occupied" not in tips["detail"] or "expected False" not in tips["detail"]


def test_execution_failure_fails_verification():
    """Aspirating more than seeded raises TooLittleLiquidError mid-run:
    verification must fail with the error recorded, not raise."""
    seq, intent, layout = _load("clean_transfer.json")
    bad = [
        {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1", "tip_rack.B1"]}},
        {"name": "transfer", "params": {
            "source": "source_plate.A1",
            "destination": "dest_plate.B1",
            "volume_ul": 500,  # seeded only 100 uL
        }},
    ]
    intent["calls"][1]["params"]["volume_ul"] = 500
    r = _run(bad, intent, layout)
    assert not r["passed"]
    assert r["error"] and "TooLittleLiquid" in r["error"]
    exec_ok = next(c for c in r["checks"] if c["name"] == "execution_ok")
    assert not exec_ok["passed"]


def test_global_flags_restored_after_run():
    from pylabrobot.liquid_handling.strictness import Strictness, get_strictness
    from pylabrobot.resources.volume_tracker import does_volume_tracking
    from pylabrobot.resources.tip_tracker import does_tip_tracking

    seq, intent, layout = _load("clean_transfer.json")
    _run(seq, intent, layout)
    assert get_strictness() is Strictness.WARN  # PLR default restored
    assert does_volume_tracking() is False
    assert does_tip_tracking() is False
