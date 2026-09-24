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


# ---------------------------------------------------------------------------
# T40 (spec 260909 §16.2, observation increment, backlog #5023): the
# `plr_observation` additive result key -- AC-16.1.
# ---------------------------------------------------------------------------

#: §16.2.1's CLOSED field list, extended by §17.3 (move-family increment,
#: T51) with `arm_slots` -- a field absent from this table is not observed.
#: Mirrors `plr-sema/eval/oracle_common.OBSERVATION_KEYS`.
_OBSERVATION_KEYS = {
    "backend_class", "num_channels", "head_channels", "deck_resource_names",
    "arm_slots",
}


def test_plr_observation_present_on_success():
    seq, intent, layout = _load("clean_transfer.json")
    r = _run(seq, intent, layout)
    assert r["passed"], [(c["name"], c["detail"]) for c in r["checks"] if not c["passed"]]
    obs = r["plr_observation"]
    assert obs is not None
    # §16.2.1's CLOSED record: exactly these five keys, no others -- fails
    # if `plr_observation` ever grows a sixth key.
    assert set(obs) == _OBSERVATION_KEYS
    assert obs["backend_class"] == "LiquidHandlerChatterboxBackend"
    assert obs["num_channels"] == 8
    assert obs["head_channels"] == sorted(obs["head_channels"])
    assert len(obs["head_channels"]) == obs["num_channels"]
    # deck_resource_names: the deck's own name plus every descendant,
    # extracted recursively -- clean_transfer.json declares source_plate/
    # dest_plate/tip_rack among its resources.
    assert "source_plate" in obs["deck_resource_names"]
    assert "dest_plate" in obs["deck_resource_names"]
    assert "tip_rack" in obs["deck_resource_names"]
    # §17.3's placement half (AC-17.2): `arm_slots` is the sorted key set
    # of `self._resource_pickups`, non-empty for a real chatterbox backend
    # (num_arms >= 1) once `setup.machine.setup()` has run.
    assert obs["arm_slots"] == sorted(obs["arm_slots"])
    assert len(obs["arm_slots"]) > 0


def test_capture_observation_arm_slots_empty_before_setup_nonempty_after():
    """AC-17.2's placement half (spec 260909_plr-sema-move-family-increment
    .md §17.3, T51): `arm_slots` is the SORTED key set of
    `machine._resource_pickups` -- EMPTY before `await
    setup.machine.setup()` runs (the dict is initialised empty at
    construction,
    `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:176`)
    and non-empty after (`setup` rebuilds it wholesale, `:212`) -- the
    identical placement argument §16.2.1 already makes for `head_channels`.
    """
    from verify.deck import DeckLayout, build_setup, capture_observation

    setup = build_setup("LiquidHandlerChatterboxBackend", DeckLayout())
    before = capture_observation(setup)
    assert before["arm_slots"] == []

    asyncio.run(setup.machine.setup())
    after = capture_observation(setup)
    assert after["arm_slots"] != []
    assert after["arm_slots"] == sorted(after["arm_slots"])


def test_arm_slots_stability_across_pickup_and_drop(monkeypatch):
    """AC-17.2's stability assertion (spec 260909_plr-sema-move-family
    -increment.md §17.3, round 1's C16): an operation sequence containing a
    pickup and a drop leaves `sorted(self._resource_pickups)` unchanged --
    what licenses calling the observed `Seq` complete at a LATER instant
    than the capture point. `move_plate` calls `pick_up_resource` then
    `drop_resource` internally."""
    import verify.verifier as verifier_mod

    captured: dict[str, object] = {}
    orig_capture = verifier_mod.capture_observation

    def _spy(setup):
        record = orig_capture(setup)
        captured["machine"] = setup.machine
        return record

    monkeypatch.setattr(verifier_mod, "capture_observation", _spy)

    seq, intent, layout = _load("move_plate.json")
    r = _run(seq, intent, layout)
    assert r["passed"], [(c["name"], c["detail"]) for c in r["checks"] if not c["passed"]]

    before = r["plr_observation"]["arm_slots"]
    after = sorted(captured["machine"]._resource_pickups)
    assert after == before


def test_plr_observation_none_on_deck_build_failure(monkeypatch):
    """§16.2.1: `plr_observation` is `None` on the deck-build early return
    (`setup is None`, no field is obtainable) -- the same path
    `volume_tracking_observed` returns its own default on.
    """
    import verify.verifier as verifier_mod

    def _raising_build_setup(*args, **kwargs):
        raise RuntimeError("synthetic deck-build failure")

    monkeypatch.setattr(verifier_mod, "build_setup", _raising_build_setup)

    seq, intent, layout = _load("clean_transfer.json")
    r = _run(seq, intent, layout)
    assert not r["passed"]
    assert r["plr_observation"] is None
    assert r["state_before"] is None and r["state_after"] is None


def test_plr_observation_none_on_raising_capture(monkeypatch):
    """§16.2.1: the ONE capture point is fail-closed -- a raising read
    yields `plr_observation = None` rather than propagating, and the rest
    of the run (execution, checks) proceeds unaffected.
    """
    import verify.verifier as verifier_mod

    def _raising_capture(setup):
        raise RuntimeError("synthetic observation-window failure")

    monkeypatch.setattr(verifier_mod, "capture_observation", _raising_capture)

    seq, intent, layout = _load("clean_transfer.json")
    r = _run(seq, intent, layout)
    assert r["passed"], [(c["name"], c["detail"]) for c in r["checks"] if not c["passed"]]
    assert r["plr_observation"] is None


# ---------------------------------------------------------------------------
# T45 (spec 260909 §16.7, fence increment, backlog #5025): the additive
# `error_frames` result key -- AC-16.8.
# ---------------------------------------------------------------------------


def test_error_frames_none_on_success():
    seq, intent, layout = _load("clean_transfer.json")
    r = _run(seq, intent, layout)
    assert r["passed"], [(c["name"], c["detail"]) for c in r["checks"] if not c["passed"]]
    assert r["error"] is None
    assert r["error_frames"] is None


def test_error_frames_present_on_execution_failure():
    """§16.7 F1: `error_frames` is the WHOLE `traceback.extract_tb` frame
    list, outermost first, one dict per frame with `file`/`lineno`/
    `qualname` -- set at the inner `except` (an operation failure)."""
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
    frames = r["error_frames"]
    assert frames  # non-empty list, never a bare truthy sentinel
    assert isinstance(frames, list)
    for f in frames:
        assert set(f) == {"file", "lineno", "qualname"}
        assert isinstance(f["lineno"], int)


def test_error_frames_none_on_deck_build_failure(monkeypatch):
    """§16.2.1's `plr_observation` reasoning does NOT apply here:
    `error_frames` is set at the OUTER (harness/deck-level) `except`
    handler itself, so a deck-build failure -- unlike the capture-window
    failure below -- still yields a real, non-`None` frame list."""
    import verify.verifier as verifier_mod

    def _raising_build_setup(*args, **kwargs):
        raise RuntimeError("synthetic deck-build failure")

    monkeypatch.setattr(verifier_mod, "build_setup", _raising_build_setup)

    seq, intent, layout = _load("clean_transfer.json")
    r = _run(seq, intent, layout)
    assert not r["passed"]
    assert r["plr_observation"] is None
    assert r["error_frames"]
    assert any(f["qualname"].endswith("_raising_build_setup") for f in r["error_frames"])


def test_error_frames_outermost_first_on_reraise(monkeypatch):
    """§16.7's own C5 case: an exception raised inside the backend, caught,
    then re-raised at `liquid_handler.py:575-576` -- the re-raise frame
    must appear BEFORE the backend's own original raise frame, not after
    (`traceback.extract_tb` is outermost-first)."""
    from pylabrobot.liquid_handling.backends.chatterbox import LiquidHandlerChatterboxBackend

    async def _raising(self, *a, **kw):
        raise RuntimeError("synthetic backend failure")

    monkeypatch.setattr(LiquidHandlerChatterboxBackend, "pick_up_tips", _raising)

    seq, intent, layout = _load("clean_transfer.json")
    r = _run(seq[:1], intent, layout)  # just the pick_up_tips call
    assert not r["passed"]
    assert r["error"] and "synthetic backend failure" in r["error"]
    frames = r["error_frames"]
    assert frames
    reraise_idx = next(
        i for i, f in enumerate(frames)
        if f["lineno"] == 576 and f["file"].endswith("liquid_handler.py")
    )
    backend_idx = next(i for i, f in enumerate(frames) if f["qualname"].endswith("_raising"))
    assert reraise_idx < backend_idx  # outermost (re-raise) before innermost (backend)
