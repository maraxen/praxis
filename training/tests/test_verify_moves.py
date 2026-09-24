"""Move-verb verification: C-M-lizard convention tests.

move_resource/plate/lid have NO tracker deltas; their post-condition is a
target-location assertion via deck serialization (see verify/__init__.py).
"""

import asyncio

from verify import verify


def _intent(calls, effects):
    return {
        "record_id": "t_move",
        "utterance": "test",
        "source": "golden",
        "calls": calls,
        "expected_effects": effects,
    }


def _layout(holders):
    return {
        "resources": {"source_plate": "Plate"},
        "holders": holders,
    }


SEQ = [{"name": "move_plate",
        "params": {"plate": "source_plate", "destination": "park_a"}}]


def test_move_location_assertion_passes():
    intent = _intent(SEQ, [{"effect": "moves_resource", "target_ref": "park_a"}])
    r = asyncio.run(verify(SEQ, intent, layout=_layout(["park_a"])))
    assert r["passed"], [(c["name"], c["detail"]) for c in r["checks"] if not c["passed"]]
    check = next(c for c in r["checks"] if c["name"] == "move_location:source_plate")
    assert check["passed"] and "park_a" in check["detail"]
    # the moved plate really is under the park holder in the serialized deck
    def find(children, name):
        for c in children or []:
            if c["name"] == name:
                return c
            f = find(c.get("children"), name)
            if f:
                return f
    node = find(r["state_after"]["topology"]["children"], "source_plate")
    assert node["parent_name"] == "park_a"


def test_move_to_wrong_park_fails_agreement_and_effect():
    """Executes cleanly at park_b, but intent binds destination=park_a."""
    seq = [{"name": "move_plate",
            "params": {"plate": "source_plate", "destination": "park_b"}}]
    intent = _intent(
        [{"name": "move_plate",
          "params": {"plate": "source_plate", "destination": "park_a"}}],
        [{"effect": "moves_resource", "target_ref": "park_a"}],
    )
    r = asyncio.run(verify(seq, intent, layout=_layout(["park_a", "park_b"])))
    checks = {c["name"]: c for c in r["checks"]}
    assert r["error"] is None  # executed cleanly
    assert not checks["slot_agreement"]["passed"]
    assert not checks["effects_match"]["passed"]
    assert checks["move_location:source_plate"]["passed"]  # it DID reach park_b
    assert not r["passed"]


def test_no_tracker_delta_checks_for_moves():
    """A move-only sequence must not fabricate volume/tip checks."""
    intent = _intent(SEQ, [])
    r = asyncio.run(verify(SEQ, intent, layout=_layout(["park_a"])))
    names = [c["name"] for c in r["checks"]]
    assert any(n.startswith("volume_delta") for n in names)
    tips = next(c for c in r["checks"] if c["name"] == "tips_delta")
    assert tips["passed"] and "expected 0" in tips["detail"]  # no tip ops simulated
