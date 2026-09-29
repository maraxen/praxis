"""Browserless tests for ``praxis/viz`` (P6.5).

No Pyodide, no Chromium, no kernel: ``BrowserVisualizer`` takes its transport by
injection, so a ``RecordingTransport`` substitutes for the BroadcastChannel and
the whole PLR callback chain runs under plain CPython.

Per ADR ``260817_repl-layout-and-delivery-mechanism.md`` Sec 2.4 this file must
NOT append ``web-repl/overlay/assets/python`` to ``sys.path`` -- that subtree
contains a ``praxis/`` package which would shadow the repo's real top-level
``praxis``. The modules are therefore loaded by path under a synthetic package
name, which keeps ``sys.path`` untouched and leaves ``import praxis`` meaning
what it always meant. ``test_rid_invariant.py`` asserts that shadowing has not
happened; this file must not be the thing that breaks it.

Assertions are on the ORDERED EVENT SEQUENCE, never byte-exact payloads: payload
size for the same operation differs across PLR pins (S-D measured 485 KB / 164 KB
/ 137 KB across the three candidates), so byte comparison would fail on a pin bump
that changed nothing behavioural.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from pylabrobot.resources import Coordinate, Resource

_VIZ_DIR = (
    Path(__file__).resolve().parents[1]
    / "overlay" / "assets" / "python" / "praxis" / "viz"
)
_PKG = "_praxis_viz_under_test"


def _load_viz_package():
    """Load praxis/viz under a synthetic name, without touching sys.path."""
    if _PKG not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            _PKG,
            _VIZ_DIR / "__init__.py",
            submodule_search_locations=[str(_VIZ_DIR)],
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[_PKG] = module
        spec.loader.exec_module(module)
    return sys.modules[_PKG]


_load_viz_package()
transport_mod = importlib.import_module(f"{_PKG}.transport")
browser_mod = importlib.import_module(f"{_PKG}.browser")

BrowserVisualizer = browser_mod.BrowserVisualizer
RecordingTransport = transport_mod.RecordingTransport


def _root() -> Resource:
    return Resource(name="root", size_x=100, size_y=100, size_z=10)


def _child(name: str = "child") -> Resource:
    return Resource(name=name, size_x=10, size_y=10, size_z=5)


def _make(resource=None, **kwargs):
    resource = resource if resource is not None else _root()
    tr = RecordingTransport()
    kwargs.setdefault("show_machine_tools_at_start", False)
    viz = BrowserVisualizer(resource, transport=tr, **kwargs)
    return viz, tr, resource


async def _settle() -> None:
    """Let callback-scheduled sends run.

    The inherited callbacks schedule via ``run_coroutine_threadsafe`` /
    ``call_soon`` / ``ensure_future`` rather than awaiting inline, so the events
    are not visible on the transport until the loop turns.
    """
    for _ in range(5):
        await asyncio.sleep(0)


# --------------------------------------------------------------------------
# The ordering assertion GATE G6 turns on.
# --------------------------------------------------------------------------
def test_setup_emits_root_resource_before_any_state() -> None:
    async def scenario():
        viz, tr, _ = _make()
        await viz.setup()
        await _settle()
        return list(tr.events)

    events = asyncio.run(scenario())
    assert events[0] == "set_root_resource", (
        f"the initial deck paint must lead with set_root_resource, got {events}"
    )
    assert "set_state" in events, f"no state was ever pushed: {events}"
    assert events.index("set_root_resource") < events.index("set_state"), (
        "set_state arrived before set_root_resource; the renderer would be asked "
        f"to update resources it has never been told about. sequence={events}"
    )


def test_stats_sent_is_at_least_two_after_setup() -> None:
    """GATE G6 asserts ``stats()['sent'] >= 2``; exactly 1 is the FAILURE signature."""
    async def scenario():
        viz, _tr, _ = _make()
        await viz.setup()
        await _settle()
        return viz.stats()

    stats = asyncio.run(scenario())
    assert stats["sent"] >= 2, (
        f"only {stats['sent']} message(s) sent. Exactly 1 is the documented failure "
        "signature: set_root_resource went out but the state push never followed."
    )


def test_show_machine_tools_is_emitted_only_when_requested() -> None:
    async def scenario(flag):
        viz, tr, _ = _make(show_machine_tools_at_start=flag)
        await viz.setup()
        await _settle()
        return list(tr.events)

    assert "show_machine_tools" in asyncio.run(scenario(True))
    assert "show_machine_tools" not in asyncio.run(scenario(False))


def test_assign_then_unassign_emit_in_that_order() -> None:
    async def scenario():
        viz, tr, root = _make()
        await viz.setup()
        await _settle()
        tr.clear()

        kid = _child()
        root.assign_child_resource(kid, location=Coordinate(0, 0, 0))
        await _settle()
        root.unassign_child_resource(kid)
        await _settle()
        return list(tr.events)

    events = asyncio.run(scenario())
    assert "resource_assigned" in events, f"assign produced no event: {events}"
    assert "resource_unassigned" in events, f"unassign produced no event: {events}"
    assert events.index("resource_assigned") < events.index("resource_unassigned")


def test_stop_emits_stop_and_marks_disconnected() -> None:
    async def scenario():
        viz, tr, _ = _make()
        await viz.setup()
        await _settle()
        tr.clear()
        await viz.stop()
        return list(tr.events), viz.has_connection(), viz.setup_finished

    events, connected, finished = asyncio.run(scenario())
    assert events == ["stop"], f"expected exactly a stop event, got {events}"
    assert connected is False
    assert finished is False


def test_double_setup_raises() -> None:
    async def scenario():
        viz, _tr, _ = _make()
        await viz.setup()
        with pytest.raises(RuntimeError, match="already been started"):
            await viz.setup()

    asyncio.run(scenario())


def test_send_command_before_setup_raises() -> None:
    async def scenario():
        viz, _tr, _ = _make()
        with pytest.raises(RuntimeError, match="no transport connection"):
            await viz.send_command("set_state", {}, wait_for_response=False)

    asyncio.run(scenario())


def test_wait_for_response_fails_loudly_instead_of_hanging() -> None:
    """An ack channel does not exist; awaiting one would block forever.

    Blocking forever is the exact failure shape this project has repeatedly been
    burned by (a silent no-op that looks like a slow boot), so the unsupported
    path must raise rather than await.
    """
    async def scenario():
        viz, _tr, _ = _make()
        await viz.setup()
        with pytest.raises(NotImplementedError, match="wait_for_response"):
            await viz.send_command("ping", {}, wait_for_response=True)

    asyncio.run(scenario())


# --------------------------------------------------------------------------
# S-D regression: non-finite floats must never reach the browser raw.
# --------------------------------------------------------------------------
def test_non_finite_floats_are_sanitized_not_emitted_raw() -> None:
    """``trash``/``trash_core96`` carry ``max_volume = float('inf')``.

    A bare ``json.dumps`` emits a literal ``Infinity`` token, which browser
    ``JSON.parse`` rejects -- S-D measured a 65,516-byte initial paint failing with
    ``SyntaxError: Unexpected token 'I'`` while every later delta parsed fine. The
    fix lives in PLR's ``_assemble_command``; this test exists so that routing
    around that method (serializing in the transport instead) fails visibly.
    """
    async def scenario():
        viz, tr, _ = _make()
        await viz.setup()
        await _settle()
        tr.clear()
        await viz.send_command(
            "set_state",
            {"trash": {"max_volume": float("inf"), "nan_field": float("nan")}},
            wait_for_response=False,
        )
        return tr.messages[0]

    raw = asyncio.run(scenario())
    assert "Infinity" in raw, "sanity: the test payload should mention Infinity"
    # Parse with BROWSER strictness. Python's json.loads accepts bare `Infinity`
    # and `NaN` as a non-standard extension, so a plain json.loads(raw) would
    # happily swallow exactly the payload the browser rejects -- it looks like a
    # guard and is not one. parse_constant fires only on those bare tokens, which
    # makes this line do the work its comment claims.
    def _reject(token: str):
        raise AssertionError(
            f"bare {token!r} token reached the transport. Browser JSON.parse "
            "rejects this; the payload would fail to render. Cause: something "
            "serialized without going through PLR's _assemble_command."
        )

    parsed = json.loads(raw, parse_constant=_reject)
    assert parsed["data"]["trash"]["max_volume"] == "Infinity"
    assert parsed["data"]["trash"]["nan_field"] == "NaN"


# --------------------------------------------------------------------------
# GATE X, made mechanical.
# --------------------------------------------------------------------------
def test_exactly_four_visualizer_members_are_overridden() -> None:
    """GATE X: a FIFTH override means stop and escalate to V4.

    The plan states override-count growth is a design regression, not a
    maintenance chore -- it means PLR's socket assumptions have spread far enough
    that a transport hook belongs upstream. Enforced here rather than left to
    review, because nobody notices a quiet fifth override in a diff.
    """
    from pylabrobot.visualizer.visualizer import Visualizer

    overridden = {
        name
        for name, attr in vars(BrowserVisualizer).items()
        if not name.startswith("__")
        and hasattr(Visualizer, name)
        and getattr(Visualizer, name) is not attr
    }
    assert overridden == {"setup", "stop", "has_connection", "send_command"}, (
        f"BrowserVisualizer overrides {sorted(overridden)}. GATE X: if a fifth "
        "vis.js/Visualizer member needs overriding, STOP and escalate to V4 "
        "(upstream a transport hook into PLR) rather than growing this set."
    )


def test_transport_module_does_not_import_js() -> None:
    """ADR Sec 2.1: ``transport.py`` must stay importable outside Pyodide."""
    import ast

    tree = ast.parse((_VIZ_DIR / "transport.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "js" not in imported, (
        "transport.py imports `js`, which makes it unimportable under CPython and "
        "kills every browserless test in this file."
    )


# --------------------------------------------------------------------------
# GATE G6's decisive arm, browserless.
# --------------------------------------------------------------------------
def test_pick_up_tips_emits_set_state_after_set_root_resource() -> None:
    """The check the execution plan calls decisive, run against a real LiquidHandler.

    G6: "in a real kernel, pick_up_tips produces set_state AFTER set_root_resource;
    viz.stats()['sent'] >= 2 -- a result of exactly 1 is the documented FAILURE
    signature." This is the browserless half; repl_smoke.py --probe runs the
    in-kernel half.

    NOTE THE PRECONDITION THE GATE TEXT OMITS: ``does_tip_tracking()`` defaults to
    FALSE. With tracking off, pick_up_tips mutates no resource state, so no
    state-update callback fires and NO set_state is emitted -- the gate fails for
    a reason that has nothing to do with the transport. Measured 2026-08-20:
    without set_tip_tracking(True) the post-pickup event slice is empty; with it,
    a single batched set_state naming exactly the four picked tipspots.
    """
    from pylabrobot.legacy.liquid_handling import LiquidHandler
    from pylabrobot.legacy.liquid_handling.backends import LiquidHandlerChatterboxBackend
    from pylabrobot.resources import STARLetDeck, does_tip_tracking, set_tip_tracking
    from pylabrobot.resources.hamilton import (
        hamilton_96_tiprack_1000uL_filter as TipRack1000,
    )

    async def scenario():
        deck = STARLetDeck()
        lh = LiquidHandler(
            backend=LiquidHandlerChatterboxBackend(num_channels=8), deck=deck
        )
        tr = RecordingTransport()
        viz = BrowserVisualizer(deck, transport=tr, show_machine_tools_at_start=False)
        await lh.setup()
        await viz.setup()
        await _settle()

        rack = TipRack1000(name="tips_01")
        deck.assign_child_resource(rack, rails=3)
        await _settle()

        before = len(tr.events)
        await lh.pick_up_tips(rack["A1:D1"])
        # A real await, not sleep(0): the update hops call_soon_threadsafe ->
        # call_soon -> ensure_future before it reaches the transport.
        await asyncio.sleep(0.2)
        return list(tr.events), before, viz.stats(), tr.decoded(len(tr.messages) - 1)

    previous = does_tip_tracking()
    set_tip_tracking(True)
    try:
        events, before, stats, last = asyncio.run(scenario())
    finally:
        set_tip_tracking(previous)  # global; do not leak into other tests

    assert events[0] == "set_root_resource"
    assert "set_state" in events[before:], (
        "pick_up_tips emitted no set_state. If tip tracking is on, the state-update "
        f"callback chain is not wired. sequence={events}"
    )
    assert stats["sent"] >= 2, f"exactly-1 is the documented failure signature: {stats}"
    assert last["event"] == "set_state"
    picked = set(last["data"])
    assert picked == {f"tips_01_tipspot_{w}1" for w in "ABCD"}, (
        f"set_state should name exactly the four picked tipspots, got {sorted(picked)}"
    )


def test_pick_up_tips_without_tip_tracking_emits_nothing() -> None:
    """Pins the precondition above, so it cannot silently become untrue.

    This is the failure mode that made the gate look broken: chatterbox prints a
    full pickup, so the operation plainly ran, yet the transport sees nothing.
    Anyone hitting an empty slice should reach for set_tip_tracking before
    suspecting BrowserVisualizer.
    """
    from pylabrobot.legacy.liquid_handling import LiquidHandler
    from pylabrobot.legacy.liquid_handling.backends import LiquidHandlerChatterboxBackend
    from pylabrobot.resources import STARLetDeck, does_tip_tracking, set_tip_tracking
    from pylabrobot.resources.hamilton import (
        hamilton_96_tiprack_1000uL_filter as TipRack1000,
    )

    async def scenario():
        deck = STARLetDeck()
        lh = LiquidHandler(
            backend=LiquidHandlerChatterboxBackend(num_channels=8), deck=deck
        )
        tr = RecordingTransport()
        viz = BrowserVisualizer(deck, transport=tr, show_machine_tools_at_start=False)
        await lh.setup()
        await viz.setup()
        await _settle()
        rack = TipRack1000(name="tips_02")
        deck.assign_child_resource(rack, rails=3)
        await _settle()
        before = len(tr.events)
        await lh.pick_up_tips(rack["A1:D1"])
        await asyncio.sleep(0.2)
        return list(tr.events)[before:]

    previous = does_tip_tracking()
    set_tip_tracking(False)
    try:
        after = asyncio.run(scenario())
    finally:
        set_tip_tracking(previous)

    assert after == [], (
        "tip tracking is off, so pick_up_tips should mutate no state and emit "
        f"nothing -- got {after}. If this now emits, the precondition documented "
        "in the sibling test no longer holds and GATE G6's text should be updated."
    )
