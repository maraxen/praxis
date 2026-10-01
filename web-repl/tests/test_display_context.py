"""Browserless tests for ``praxis/display/context.py`` (task B5, backlog #5640): error context
resolution, ``context.resolve(exc, tb) -> ErrorContext | None``. Closes AC-15.

Spec: ``260929_notebook-display-epic.md`` D8 (steps 1-5: the tracker frame, the op frames filtered on
``glossary.ACTIONS``, the ``*96`` short-circuit, owner rules (a)-(e) by identity, the COMMITTED and
per-resource SUMMED offending set with the per-channel rule for a tip owner, the pending-residue
rule "owner outside the committed offending set -> None", "What PLR's message omits", "Panel
drawing", "Tracking"), section 3.3 (the templates only as far as the context feeds them; B6 builds
the panel), the B5 task text and AC-15 (E1-E16, E4-off, E6-off and the four negatives). The 96-head
ops (``E96-*``) resolve on their own path since #5659: ``261001_nd-next-5659-96head-errors.md``
(N5659-1..4, AC-96-1..5, ``-k "dispatch96 or map96 or offend96 or discrim96 or none96"``).

**Real PLR at the 1.0.0b1 pin.** Every case raises the REAL error, through the real
``LiquidHandler`` (non-shim home ``pylabrobot.legacy.liquid_handling``) and the chatterbox backend,
on the fixture's ``assemble()`` deck. The venv's editable PLR can be the old 0.2.2, which would make
every case meaningless, so the first fixture asserts the version; run with
``PYTHONPATH=<PLR 1.0.0b1 source>`` prepended when the venv is not on the pin. Each case is built by
a scenario coroutine and cached; ``test_every_scenario_raises_the_class_it_claims`` checks the
scenarios themselves, WITHOUT the module under test, so a setup that stops raising fails on its own
and never lets a resolver test pass vacuously.

**Import discipline** (ADR 260817 Sec 2.4). ``praxis/display`` is loaded by path under the synthetic
package ``_praxis_display_under_test``; ``web-repl/overlay/assets/python`` is never put on
``sys.path``. ``context.py`` must import in plain CPython with NO PLR import at import time (it
resolves PLR classes inside functions), and its lazy imports must be quiet under warnings-as-errors
and name only the pin's non-shim homes (and be in ``plr_contract.CONTRACT``).

**Controls (nothing here passes vacuously).**

* the case checks are plain functions of a resolver; a resolver that always returns ``None``, one
  that always names the first op resource, and one that resolves by NAME (an impostor with the same
  name is accepted) must each FAIL the checks built to catch them;
* the "committed, not pending" and "committed tip, not ``has_tip``" checks are run against mutants
  of the module (its committed readers patched to read pending state / ``has_tip``; its offending set
  skipped): each must fail the cases built for it (the direct-residue cases, E14, E13/E15) while E1
  and E4 still pass, which shows the checks bite where they claim to. (E13's own op rolls its
  resource back, so at resolve time pending equals committed there; the direct-residue cases have no
  op to roll back and are what catch a pending reader.)
* the frame filter is run against a ``glossary.ACTIONS`` that also lists PLR's ``wrapper`` frames;
* the mixed-stack rule (N5659-1 (ii)) is checked on a real non-96 failure under a ``*96`` frame
  (``E1_via_96``) and on a real ``*96`` failure under a non-96 op frame (``E96-under-1ch``); an
  innermost-frame-only dispatcher and the old any-96 short-circuit are run as mutants of the
  dispatch seam (``_path``) and must fail the cases built for them;
* the 96 path's committed offending set is run against mutants of its seams (first failure only,
  a mask that ignores which channels hold a tip, a ``has_tip`` reader, PLR's own demand, no NoTip
  clause, no container-mode guard): each must fail the cases built for it;
* the AST scan (no ``has_tip``, no ``TipSpot.get_tip``, no ``spot.tracker``) is run against
  synthetic sources first, and a runtime tripwire on ``TipSpot`` proves the same at run time.

**Re-anchored at the pin** (PLR 1.0.0b1, ``pylabrobot/legacy/...``; D8 "Tracking" asks B5 to
re-anchor the head-side NoTip sites here). Head-side ``NoTipError`` comes only from
``TipTracker.get_tip`` (``tip_tracker.py:118``, ``"{thing} does not have a tip."``) and
``TipTracker.remove_tip`` (``:166``), with ``thing`` = ``"Channel N"`` (LH:418), reached at
``liquid_handler.py`` :880 (``drop_tips``, and so ``return_tips`` and ``discard_tips``), :1200
(``aspirate``), :1405 (``dispense``) and :909 (``drop_tips``, ``remove_tip``); the commit loops at
:1288 and :1489 call ``get_tip`` again after a failure. Head-side ``HasTipError`` is LH:758
(``"Channel has tip"``, pick-up loop, no tracker frame) and ``tip_tracker.py:153``. Spot-side:
``TipSpot.get_tip`` raises at LH:727 (before the queue loop), ``add_tip`` at :761 and the drop
queue at :901-911. ``test_pin_anchors_still_read_as_documented`` re-checks the ones the resolver
depends on, by content and not by line number.
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import dataclasses
import importlib
import importlib.util
import inspect
import re
import subprocess
import sys
import textwrap
import types
from pathlib import Path

import pylabrobot
import pytest
from pylabrobot.legacy.liquid_handling import LiquidHandler
from pylabrobot.legacy.tip_tracker import TipTracker, tip_spot_tracker
from pylabrobot.resources import (
    Container,
    Coordinate,
    TipSpot,
    does_tip_tracking,
    does_volume_tracking,
    set_tip_tracking,
    set_volume_tracking,
)
from pylabrobot.resources.agenbio import agenbio_1_troughplate_100mL_Fl
from pylabrobot.resources.corning import cor_96_wellplate_360uL_Fb
from pylabrobot.resources.errors import (
    HasTipError,
    NoTipError,
    TooLittleLiquidError,
    TooLittleVolumeError,
)
from pylabrobot.resources.hamilton import (
    Trough_CAR_5R60_A00,
    hamilton_1_trough_60mL_Vb,
    hamilton_96_tiprack_300uL_filter,
)
from pylabrobot.resources.revvity import Revvity_384_wellplate_28ul_Ub
from pylabrobot.resources.volume_tracker import VolumeTracker

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL = _TESTS_DIR.parent
_DISPLAY_DIR = _WEB_REPL / "overlay" / "assets" / "python" / "praxis" / "display"
_CONTEXT_PATH = _DISPLAY_DIR / "context.py"
_FIXTURE_PATH = _WEB_REPL / "design" / "notebook-display" / "make_fixture.py"
_PKG = "_praxis_display_under_test"

CONTAINER, TIP_SPOT, CHANNEL, TIP = "container", "tip_spot", "channel", "tip"

# The non-shim homes the module may import PLR from (D8 "Classes the code checks", sprint B
# "Import contract"); ``pylabrobot.resources`` for the resource classes.
ALLOWED_PLR_MODULES = {
    "pylabrobot.legacy.liquid_handling",
    "pylabrobot.legacy.tip_tracker",
    "pylabrobot.resources",
    "pylabrobot.resources.errors",
    "pylabrobot.resources.volume_tracker",
}


# --------------------------------------------------------------------------- loading


def _package():
    if _PKG not in sys.modules:
        module = types.ModuleType(_PKG)
        module.__path__ = [str(_DISPLAY_DIR)]
        module.__package__ = _PKG
        sys.modules[_PKG] = module
    return sys.modules[_PKG]


@pytest.fixture(scope="module", autouse=True)
def _plr_is_the_pin():
    """A wrong PLR must fail loudly, never pass silently (the venv may carry 0.2.2)."""
    version = str(getattr(pylabrobot, "__version__", ""))
    assert version.startswith("1.0.0b1"), (
        f"PyLabRobot {version!r} at {pylabrobot.__file__} is not the 1.0.0b1 pin; "
        "run with PYTHONPATH=<PLR 1.0.0b1 source> prepended"
    )
    assert Path(pylabrobot.__file__).is_file()


@pytest.fixture(autouse=True)
def _restore_tracking_flags():
    """Tracking is a PLR global; a case that turns it off must not leak into the next test."""
    tip, vol = does_tip_tracking(), does_volume_tracking()
    yield
    set_tip_tracking(tip)
    set_volume_tracking(vol)


@pytest.fixture(scope="module")
def cx():
    """praxis/display/context.py. A missing module is the RED reason."""
    if not _CONTEXT_PATH.is_file():
        pytest.fail(f"praxis/display/context.py does not exist yet: {_CONTEXT_PATH}")
    _package()
    return importlib.import_module(f"{_PKG}.context")


@pytest.fixture(scope="module")
def gl():
    _package()
    return importlib.import_module(f"{_PKG}.glossary")


_FX = None


def _fx():
    """The ported design fixture module (its ``assemble`` builds the deck every case runs on)."""
    global _FX
    if _FX is None:
        spec = importlib.util.spec_from_file_location("_praxis_make_fixture_under_test", _FIXTURE_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules["_praxis_make_fixture_under_test"] = module
        spec.loader.exec_module(module)
        _FX = module
    return _FX


# --------------------------------------------------------------------------- scenarios


class Raised:
    """What a scenario hands back: the exception plus the live objects the expectations name."""

    def __init__(self, exc, **objects):
        self.exc = exc
        self.tb = exc.__traceback__
        self.__dict__.update(objects)


SCENARIOS: dict = {}
EXPECTED_CLASS: dict = {}
_CASES: dict = {}


def scenario(name, exc_class):
    def register(fn):
        SCENARIOS[name] = fn
        EXPECTED_CLASS[name] = exc_class
        return fn

    return register


def case(name) -> Raised:
    """Run a scenario once (fresh deck, real PLR) and cache what it raised."""
    if name not in _CASES:
        _CASES[name] = asyncio.run(SCENARIOS[name]())
    return _CASES[name]


async def _world(tip_tracking=True):
    """The fixture's deck (tips_300 on the tip carrier, source and assay plates), tracking on."""
    deck, lh = await _fx().assemble()
    if not tip_tracking:
        set_tip_tracking(False)
    return deck, lh, deck.get_resource("tips_300"), deck.get_resource("source"), deck.get_resource("assay")


def _add_trough(deck, name="trough"):
    carrier = Trough_CAR_5R60_A00(name=f"{name}_carrier")
    carrier[0] = trough = hamilton_1_trough_60mL_Vb(name=name)
    deck.assign_child_resource(carrier, track=16)
    return trough


async def _catch(coro):
    try:
        await coro
    except Exception as e:
        return e
    raise AssertionError("the op was expected to raise and did not")


def _committed_volumes(wells):
    return [w.tracker.volume for w in wells]


@scenario("E1", TooLittleLiquidError)
async def _e1():
    """The fixture's error cell: 80 uL from assay A1:H1, which holds 50."""
    deck, lh, tips, source, assay = await _world()
    await lh.pick_up_tips(tips["A1:H1"])
    await lh.aspirate(source["A1:H1"], vols=[50.0] * 8)
    await lh.dispense(assay["A1:H1"], vols=[50.0] * 8)
    wells = assay["A1:H1"]
    assert _committed_volumes(wells) == [50.0] * 8
    exc = await _catch(lh.aspirate(wells, vols=[80.0] * 8))
    return Raised(exc, deck=deck, lh=lh, wells=wells, assay=assay)


@scenario("E1_via_96", TooLittleLiquidError)
async def _e1_via_96():
    """E1 again, but the failing aspirate is called from a ``*96`` frame (a subclass method with
    a ``*96`` name): a real non-96 failure with a ``*96`` op on the stack.
    """
    deck, lh, tips, source, assay = await _world()
    await lh.pick_up_tips(tips["A1:H1"])
    await lh.aspirate(source["A1:H1"], vols=[50.0] * 8)
    await lh.dispense(assay["A1:H1"], vols=[50.0] * 8)

    class LH96(LiquidHandler):
        async def aspirate96(self, resources, vols):
            return await self.aspirate(resources, vols=vols)

    lh.__class__ = LH96
    wells = assay["A1:H1"]
    exc = await _catch(lh.aspirate96(wells, [80.0] * 8))
    return Raised(exc, deck=deck, lh=lh, wells=wells)


@scenario("E2", TooLittleVolumeError)
async def _e2():
    """A tip holding 400 uL (preset), dispensed into a 360 uL well: TLV, owner the well."""
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips([tips.get_item("A1")])
    lh.head[0].get_tip().tracker.set_volume(400)  # set_volume does not validate max_volume
    well = assay.get_item("A2")
    assert well.max_volume == 360 and well.tracker.volume == 0
    exc = await _catch(lh.dispense([well], vols=[400.0], use_channels=[0]))
    return Raised(exc, deck=deck, lh=lh, well=well)


@scenario("E2_summed", TooLittleVolumeError)
async def _e2_summed():
    """Two channels dispense 200 uL each into ONE trough whose tracker holds at most 300: each
    request fits, the sum does not. (A plate well is too small to space two channels over.)
    """
    deck, lh, tips, _source, _assay = await _world()
    trough = _add_trough(deck)
    trough.tracker.max_volume = 300.0  # a public attribute of the tracker; committed room is 300
    await lh.pick_up_tips(tips["A1:B1"])
    for c in (0, 1):
        lh.head[c].get_tip().tracker.set_volume(200)
    exc = await _catch(lh.dispense([trough, trough], vols=[200.0, 200.0], use_channels=[0, 1]))
    return Raised(exc, deck=deck, lh=lh, trough=trough)


@scenario("E3", TooLittleVolumeError)
async def _e3():
    """400 uL into a tip whose max_volume is 360 (not the 300 nominal), from a well preset to 500."""
    deck, lh, tips, source, _assay = await _world()
    src = source.get_item("A1")
    src.tracker.set_volume(500)
    await lh.pick_up_tips([tips.get_item("A1")])
    tip = lh.head[0].get_tip()
    assert tip.tracker.max_volume == 360
    exc = await _catch(lh.aspirate([src], vols=[400.0], use_channels=[0]))
    return Raised(exc, deck=deck, lh=lh, tip=tip, src=src)


@scenario("E3_per_channel", TooLittleVolumeError)
async def _e3_per_channel():
    """Channels 0 and 1 aspirate 300 and 400 uL: only channel 1 overflows its tip."""
    deck, lh, tips, source, _assay = await _world()
    for well in source["A1:B1"]:
        well.tracker.set_volume(500)
    await lh.pick_up_tips(tips["A1:B1"])
    tip0, tip1 = lh.head[0].get_tip(), lh.head[1].get_tip()
    exc = await _catch(lh.aspirate(source["A1:B1"], vols=[300.0, 400.0]))
    return Raised(exc, deck=deck, lh=lh, tip0=tip0, tip1=tip1)


@scenario("E4", HasTipError)
async def _e4():
    """Pick up with tips already on: the loop local ``channel`` (rule (e), no tracker frame)."""
    deck, lh, tips, _source, _assay = await _world()
    await lh.pick_up_tips(tips["A1:H1"])
    exc = await _catch(lh.pick_up_tips(tips["A2:H2"]))
    return Raised(exc, deck=deck, lh=lh, tips=tips)


@scenario("E4-off", HasTipError)
async def _e4_off():
    deck, lh, tips, _source, _assay = await _world(tip_tracking=False)
    try:
        assert not does_tip_tracking()
        await lh.pick_up_tips(tips["A1:H1"])
        exc = await _catch(lh.pick_up_tips(tips["A2:H2"]))
    finally:
        set_tip_tracking(True)
    return Raised(exc, deck=deck, lh=lh, tips=tips)


@scenario("E5", HasTipError)
async def _e5():
    """Drop onto an occupied spot (A2 still holds its tip)."""
    deck, lh, tips, _source, _assay = await _world()
    await lh.pick_up_tips([tips.get_item("A1")])
    spot = tips.get_item("A2")
    assert spot.tip is not None
    exc = await _catch(lh.drop_tips([spot], use_channels=[0]))
    return Raised(exc, deck=deck, lh=lh, tips=tips, spot=spot)


@scenario("E6", NoTipError)
async def _e6():
    """Aspirate with no tip mounted: ``"Channel 0 does not have a tip."`` (thing = ``Channel N``)."""
    deck, lh, _tips, source, _assay = await _world()
    exc = await _catch(lh.aspirate([source.get_item("A1")], vols=[50.0], use_channels=[0]))
    return Raised(exc, deck=deck, lh=lh)


@scenario("E6-off", NoTipError)
async def _e6_off():
    deck, lh, _tips, source, _assay = await _world(tip_tracking=False)
    try:
        assert not does_tip_tracking()
        exc = await _catch(lh.aspirate([source.get_item("A1")], vols=[50.0], use_channels=[0]))
    finally:
        set_tip_tracking(True)
    return Raised(exc, deck=deck, lh=lh)


@scenario("E7", NoTipError)
async def _e7():
    """Pick up from a spot whose tip is already on channel 0 (raised before the queue loop)."""
    deck, lh, tips, _source, _assay = await _world()
    spot = tips.get_item("A1")
    await lh.pick_up_tips([spot])
    exc = await _catch(lh.pick_up_tips([spot], use_channels=[1]))
    return Raised(exc, deck=deck, lh=lh, tips=tips, spot=spot)


@scenario("E8", TooLittleLiquidError)
async def _e8():
    """A tracker used directly, outside any LH: owner from ``thing`` = ``<name>_volume_tracker``.
    ``deck``, ``lh`` and ``well`` are locals of THIS frame on purpose: it is the "cell".
    """
    deck, lh, tips, source, assay = await _world()
    well = assay.get_item("A1")
    try:
        well.tracker.remove_liquid(999)
    except TooLittleLiquidError as exc:
        return Raised(exc, deck=deck, lh=lh, well=well)
    raise AssertionError("remove_liquid(999) was expected to raise")


@scenario("E8_spot", NoTipError)
async def _e8_spot():
    """No LH: an empty tip spot's own tracker (``thing`` = the spot's name at the pin)."""
    deck, lh, tips, source, assay = await _world()
    spot = tips.get_item("A1")
    await lh.pick_up_tips([spot])
    try:
        tip_spot_tracker(spot).get_tip()
    except NoTipError as exc:
        return Raised(exc, deck=deck, lh=lh, spot=spot)
    raise AssertionError("get_tip on a taken spot was expected to raise")


@scenario("E8_channel", NoTipError)
async def _e8_channel():
    """No LH frame: a head tracker used directly (``thing`` = ``Channel 3``)."""
    deck, lh, tips, source, assay = await _world()
    try:
        lh.head[3].get_tip()
    except NoTipError as exc:
        return Raised(exc, deck=deck, lh=lh)
    raise AssertionError("get_tip on an empty channel was expected to raise")


@scenario("E9", TooLittleLiquidError)
async def _e9():
    """Eight channels, 30 uL each, from ONE trough holding 100 committed: 240 > 100."""
    deck, lh, tips, _source, _assay = await _world()
    trough = _add_trough(deck)
    trough.tracker.set_volume(100)
    await lh.pick_up_tips(tips["A1:H1"])
    exc = await _catch(lh.aspirate([trough] * 8, vols=[30.0] * 8, use_channels=list(range(8))))
    # a failed aspirate rolls every op resource back: no residue at the pin
    assert (trough.tracker.volume, trough.tracker.pending_volume) == (100, 100)
    return Raised(exc, deck=deck, lh=lh, trough=trough)


@scenario("E10", TooLittleLiquidError)
async def _e10():
    """A1:D1 hold 50 and E1:H1 hold 200; 80 uL from each: exactly A1:D1 offend."""
    deck, lh, tips, _source, assay = await _world()
    wells = assay["A1:H1"]
    for well in wells[:4]:
        well.tracker.set_volume(50)
    for well in wells[4:]:
        well.tracker.set_volume(200)
    await lh.pick_up_tips(tips["A1:H1"])
    exc = await _catch(lh.aspirate(wells, vols=[80.0] * 8))
    return Raised(exc, deck=deck, lh=lh, wells=wells)


@scenario("E11", HasTipError)
async def _e11():
    """``return_tips`` onto an occupied spot: channel 1 drops its tip into A1 (which channel 0's
    tip came from), then channel 0 is asked to return to A1.
    """
    deck, lh, tips, _source, _assay = await _world()
    a1 = tips.get_item("A1")
    await lh.pick_up_tips([a1])  # channel 0
    await lh.pick_up_tips([tips.get_item("A2")], use_channels=[1])
    await lh.drop_tips([a1], use_channels=[1])  # A1 is occupied again
    assert lh.head[0].get_tip_origin() is a1 and a1.tip is not None
    exc = await _catch(lh.return_tips(use_channels=[0]))
    return Raised(exc, deck=deck, lh=lh, spot=a1)


@scenario("E12", TooLittleLiquidError)
async def _e12():
    """Dispense 100 uL from an empty tip: TLL, owner the tip on channel 0."""
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips([tips.get_item("A1")])
    tip = lh.head[0].get_tip()
    assert tip.tracker.volume == 0
    exc = await _catch(lh.dispense([assay.get_item("A1")], vols=[100.0], use_channels=[0]))
    return Raised(exc, deck=deck, lh=lh, tip=tip)


@scenario("E12_per_channel", TooLittleLiquidError)
async def _e12_per_channel():
    """Tips hold 50 and 10 uL, each asked for 30: only channel 1 lacks the liquid."""
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips(tips["A1:B1"])
    tip0, tip1 = lh.head[0].get_tip(), lh.head[1].get_tip()
    tip0.tracker.set_volume(50)
    tip1.tracker.set_volume(10)
    exc = await _catch(lh.dispense(assay["A1:B1"], vols=[30.0, 30.0], use_channels=[0, 1]))
    return Raised(exc, deck=deck, lh=lh, tip0=tip0, tip1=tip1)


@scenario("E13", TooLittleLiquidError)
async def _e13():
    """Residue from direct tracker use (committed 100, pending 90): 95 <= 100 yet PLR raises."""
    deck, lh, tips, _source, _assay = await _world()
    trough = _add_trough(deck)
    await lh.pick_up_tips([tips.get_item("A1")])
    trough.tracker.set_volume(100)
    trough.tracker.remove_liquid(10.0)  # direct, NOT committed
    assert (trough.tracker.volume, trough.tracker.pending_volume) == (100, 90)
    exc = await _catch(lh.aspirate([trough], vols=[95.0], use_channels=[0]))
    assert str(exc) == "Not enough liquid in container: 95.0uL > 90.0uL."
    assert trough.tracker.volume >= 95.0
    # the failed op's rollback: pending is back to committed
    assert (trough.tracker.volume, trough.tracker.pending_volume) == (100, 100)
    return Raised(exc, deck=deck, lh=lh, trough=trough)


@scenario("residue_direct_tll", TooLittleLiquidError)
async def _residue_direct_tll():
    """No LH frame, so no rollback erases the residue: committed 100, pending 90, and a direct
    ``remove_liquid(95)`` raises although 95 fits the committed volume. ``deck`` is a local."""
    deck, lh, tips, source, assay = await _world()
    well = assay.get_item("A1")
    well.tracker.set_volume(100)
    well.tracker.remove_liquid(10.0)
    assert (well.tracker.volume, well.tracker.pending_volume) == (100, 90)
    try:
        well.tracker.remove_liquid(95.0)
    except TooLittleLiquidError as exc:
        assert (well.tracker.volume, well.tracker.pending_volume) == (100, 90)  # residue survives
        return Raised(exc, deck=deck, lh=lh, well=well)
    raise AssertionError("expected TLL")


@scenario("residue_direct_tlv", TooLittleVolumeError)
async def _residue_direct_tlv():
    """The TLV twin: committed 300 (room 60), pending 350 (room 10), a direct ``add_liquid(20)``."""
    deck, lh, tips, source, assay = await _world()
    well = assay.get_item("A1")
    well.tracker.set_volume(300)
    well.tracker.add_liquid(50.0)
    assert (well.tracker.volume, well.tracker.pending_volume) == (300, 350)
    try:
        well.tracker.add_liquid(20.0)
    except TooLittleVolumeError as exc:
        return Raised(exc, deck=deck, lh=lh, well=well)
    raise AssertionError("expected TLV")


@scenario("over_committed_direct", TooLittleLiquidError)
async def _over_committed_direct():
    """The residue twin that committed state DOES explain: 105 exceeds the committed 100 too."""
    deck, lh, tips, source, assay = await _world()
    well = assay.get_item("A1")
    well.tracker.set_volume(100)
    well.tracker.remove_liquid(10.0)
    try:
        well.tracker.remove_liquid(105.0)
    except TooLittleLiquidError as exc:
        return Raised(exc, deck=deck, lh=lh, well=well)
    raise AssertionError("expected TLL")


@scenario("E4_channel1", HasTipError)
async def _e4_channel1():
    """Pick up on channels 0 and 1 while channel 1 holds a tip: the failing channel is 1, so the
    ``channel`` loop local is what names it (channel 0 has none and only queues)."""
    deck, lh, tips, _source, _assay = await _world()
    await lh.pick_up_tips([tips.get_item("A1")], use_channels=[1])
    exc = await _catch(lh.pick_up_tips(tips["A2:B2"], use_channels=[0, 1]))
    return Raised(exc, deck=deck, lh=lh, tips=tips)


@scenario("impostor_in_op", TooLittleLiquidError)
async def _impostor_in_op():
    """The impostor first, the deck's real (empty) A1 and B1 after it, in ONE op: the raising tracker is the
    impostor's, but its name belongs to a well that IS in the op and IS short of liquid, so only
    identity keeps the real well from being named."""
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips(tips["A1:C1"])
    impostor = cor_96_wellplate_360uL_Fb(name="assay").get_item("A1")
    real, other = assay.get_item("A1"), assay.get_item("B1")
    assert impostor.name == real.name and impostor is not real and real.tracker.volume == 0
    # (PLR compares and hashes resources by value: [impostor, real] alone would be ONE resource)
    exc = await _catch(lh.aspirate([impostor, real, other], vols=[50.0] * 3, use_channels=[0, 1, 2]))
    return Raised(exc, deck=deck, lh=lh, impostor=impostor, real=real)


@scenario("impostor_direct", TooLittleLiquidError)
async def _impostor_direct():
    """No LH frame: a standalone tracker named exactly like the deck well's. Rule (d) finds the
    well by name, but the well's tracker is not this one."""
    deck, lh, tips, source, assay = await _world()
    real = assay.get_item("A1")
    impostor = VolumeTracker(thing=real.tracker.thing, max_volume=real.max_volume)
    assert impostor is not real.tracker
    try:
        impostor.remove_liquid(999.0)
    except TooLittleLiquidError as exc:
        return Raised(exc, deck=deck, lh=lh, real=real)
    raise AssertionError("expected TLL")


@scenario("nested_trackers", TooLittleLiquidError)
async def _nested_trackers():
    """Two DIFFERENT trackers on the stack: a callback on well A1's tracker removes 999 uL from well
    B1. The one that raised is the INNERMOST tracker frame (B1's); A1's own request (1 uL) fits."""
    deck, lh, tips, source, assay = await _world()
    a1, b1 = assay.get_item("A1"), assay.get_item("B1")
    a1.tracker.set_volume(100)
    b1.tracker.set_volume(100)
    a1.tracker.register_callback(lambda: b1.tracker.remove_liquid(999.0))
    try:
        a1.tracker.remove_liquid(1.0)
    except TooLittleLiquidError as exc:
        return Raised(exc, deck=deck, lh=lh, a1=a1, b1=b1)
    raise AssertionError("expected TLL")


@scenario("E14", HasTipError)
async def _e14():
    """Pending tip residue from a failed pick-up, then a second pick-up on those channels."""
    deck, lh, tips, _source, _assay = await _world()
    await lh.pick_up_tips(tips["D1:D1"], use_channels=[3])
    first = await _catch(lh.pick_up_tips(tips["A2:H2"]))  # channels 0-2 queue, channel 3 raises
    assert isinstance(first, HasTipError)
    for i in (0, 1, 2):
        assert lh.head[i].has_tip is True  # pending included
        with pytest.raises(NoTipError):
            lh.head[i].get_tip()  # nothing committed
    exc = await _catch(lh.pick_up_tips(tips["A3:C3"], use_channels=[0, 1, 2]))
    return Raised(exc, deck=deck, lh=lh, tips=tips)


@scenario("E15", TooLittleVolumeError)
async def _e15():
    """Tip-side residue from direct tracker use: committed room 360 but pending room 160."""
    deck, lh, tips, source, _assay = await _world()
    await lh.pick_up_tips([tips.get_item("A1")])
    tip = lh.head[0].get_tip()
    tip.tracker.add_liquid(200)  # direct, NOT committed
    assert (tip.tracker.volume, tip.tracker.pending_volume) == (0, 200)
    well = source.get_item("A1")
    well.tracker.set_volume(300)
    exc = await _catch(lh.aspirate([well], vols=[200.0], use_channels=[0]))
    return Raised(exc, deck=deck, lh=lh, tip=tip, well=well)


@scenario("E16", NoTipError)
async def _e16():
    """``discard_tips(use_channels=[0])`` with no tip mounted."""
    deck, lh, _tips, _source, _assay = await _world()
    exc = await _catch(lh.discard_tips(use_channels=[0]))
    assert str(exc) == "Channel 0 does not have a tip."
    return Raised(exc, deck=deck, lh=lh)


@scenario("E96-empty", TooLittleLiquidError)
async def _e96_empty():
    """A real 96-head failure: pick up the whole rack, aspirate 50 uL from an empty assay plate.
    (This was ``E-96``; #5659 renames it and gives it a real resolution to check.)"""
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96(assay, volume=50.0))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


# ---- #5659: the 96-head scenarios. Recipes are the spec's (section 2, "Recipes"); letters in the
# ---- docstrings are the spec's.


def _bare_container(deck, name, *, x=120.0, y=80.0, z=40.0, max_volume=20000.0, at=(500.0, 100.0)):
    """A bare ``Container`` assigned straight to the deck (rule (a) walks ``lh.deck``'s subtree)."""
    container = Container(name=name, size_x=x, size_y=y, size_z=z, max_volume=max_volume)
    deck.assign_child_resource(container, location=Coordinate(at[0], at[1], 0))
    return container


def _one_well_plate(deck, name="trough_plate"):
    """A PLR one-well troughplate on a free plate-carrier site (A25, S4); its well fits the head."""
    plate = agenbio_1_troughplate_100mL_Fl(name=name)
    deck.get_resource("plate_carrier")[2] = plate
    assert plate.num_items == 1
    return plate


def _set_tip_volumes(lh, volume):
    for tracker in lh.head96.values():
        tracker.get_tip().tracker.set_volume(volume)


def _give_spot_a_committed_tip(tips, i):
    spot = tips.get_item(i)
    tip_spot_tracker(spot).add_tip(spot.make_tip())  # commit=True
    return spot


def _take_committed_tip_from_spot(tips, i):
    tip_spot_tracker(tips.get_item(i)).remove_tip(commit=True)


@scenario("E96-single", TooLittleLiquidError)
async def _e96_single():
    """J2: a bare 120x80x40 Container (max 20,000) holding 2,000; 96 channels x 30 uL = 2,880."""
    deck, lh, tips, _source, _assay = await _world()
    container = _bare_container(deck, "big")
    container.tracker.set_volume(2000)
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96(container, volume=30.0))
    return Raised(exc, deck=deck, lh=lh, container=container)


@scenario("E96-onewell-plate", TooLittleLiquidError)
async def _e96_onewell_plate():
    """A one-item Plate is single-container mode (LH:1993) and its Well's parent is the Plate, so
    a dispatch on ``_in_plate`` would call it a per-channel plate (C4)."""
    deck, lh, tips, _source, _assay = await _world()
    plate = _one_well_plate(deck)
    well = plate.get_item(0)
    well.tracker.set_volume(1000)
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96(plate, volume=30.0))
    return Raised(exc, deck=deck, lh=lh, plate=plate, well=well)


@scenario("E96-rowD", TooLittleLiquidError)
async def _e96_rowd():
    """B: assay wells 80 uL except row D at 10; 50 uL on every channel. Wells A1-C1 and tips 0-2
    are queued (residue) before D1 raises."""
    deck, lh, tips, _source, assay = await _world()
    for well in assay.get_all_items():
        well.tracker.set_volume(80)
    for well in assay["D1:D12"]:
        well.tracker.set_volume(10)
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96(assay, volume=50.0))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-partial", TooLittleLiquidError)
async def _e96_partial():
    """G2: committed tips removed from spots 0, 1, 2 and 50 first (A1, B1, C1, C7), so the head
    mounts 92 tips; the plate is empty."""
    deck, lh, tips, _source, assay = await _world()
    for i in (0, 1, 2, 50):
        _take_committed_tip_from_spot(tips, i)
    await lh.pick_up_tips96(tips)
    assert sum(1 for t in lh.head96.values() if t.has_tip) == 92
    exc = await _catch(lh.aspirate96(assay, volume=50.0))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-tipTLV", TooLittleVolumeError)
async def _e96_tip_tlv():
    """C3: the wells can supply 400 uL per channel; the second 200 uL does not fit a 360 uL tip."""
    deck, lh, tips, source, _assay = await _world()
    for well in source.get_all_items():
        well.tracker.max_volume = 5000
        well.tracker.set_volume(1000)
    await lh.pick_up_tips96(tips)
    await lh.aspirate96(source, volume=200.0)
    exc = await _catch(lh.aspirate96(source, volume=200.0))
    return Raised(exc, deck=deck, lh=lh, tips=tips, source=source)


@scenario("E96-tipTLL", TooLittleLiquidError)
async def _e96_tip_tll():
    """D: every tip holds 30 uL and is asked to dispense 50."""
    deck, lh, tips, source, assay = await _world()
    await lh.pick_up_tips96(tips)
    await lh.aspirate96(source, volume=30.0)
    exc = await _catch(lh.dispense96(assay, volume=50.0))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-tipTLL-D2", TooLittleLiquidError)
async def _e96_tip_tll_d2():
    """D2: tips on channels 7 and 9 hold 20 uL, the rest 30; 25 uL is asked. Tip 7 fails after tips
    0-6 are queued (7 tips of residue)."""
    deck, lh, tips, source, assay = await _world()
    await lh.pick_up_tips96(tips)
    await lh.aspirate96(source, volume=30.0)
    for c in (7, 9):
        lh.head96[c].get_tip().tracker.set_volume(20)
    exc = await _catch(lh.dispense96(assay, volume=25.0))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-dispTLV", TooLittleVolumeError)
async def _e96_disp_tlv():
    """E: assay room is 30 uL at indices 10, 11 and 40 (C2, D2, A6) and 200 elsewhere; the tips hold
    100 and dispense 100. Wells 0-9 are queued (residue) before C2 raises."""
    deck, lh, tips, _source, assay = await _world()
    for i, well in enumerate(assay.get_all_items()):
        well.tracker.set_volume(330 if i in (10, 11, 40) else 160)
    await lh.pick_up_tips96(tips)
    _set_tip_volumes(lh, 100)
    exc = await _catch(lh.dispense96(assay, volume=100.0))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


async def _f3(tips_spot_3_emptied=False):
    deck, lh, tips, _source, assay = await _world()
    if tips_spot_3_emptied:
        _take_committed_tip_from_spot(tips, 3)
    for c in (3, 50):
        lh.head96[c].add_tip(tips.get_item(c).make_tip())  # committed
    return deck, lh, tips, assay


@scenario("E96-hasTip-pickup", HasTipError)
async def _e96_has_tip_pickup():
    """F3: head channels 3 and 50 hold committed tips, then a full rack is picked up. Channels
    0-2 are queued (pending tips, pending removals on spots 0-2) before channel 3 raises."""
    deck, lh, tips, assay = await _f3()
    exc = await _catch(lh.pick_up_tips96(tips))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-hasTip-pickup-s3", HasTipError)
async def _e96_has_tip_pickup_s3():
    """F3 with the committed tip removed from spot 3 first: channel 3 is skipped (no tip to pick
    up) and channel 50 raises. Spot 3's channel is NOT offending although its head holds a tip."""
    deck, lh, tips, assay = await _f3(tips_spot_3_emptied=True)
    exc = await _catch(lh.pick_up_tips96(tips))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


async def _h(channels_without_a_tip=()):
    """H: the whole rack picked up, committed tips put back in spots 5 (F1) and 77."""
    deck, lh, tips, source, assay = await _world()
    await lh.pick_up_tips96(tips)
    for c in channels_without_a_tip:
        lh.head96[c].remove_tip(commit=True)
    for i in (5, 77):
        _give_spot_a_committed_tip(tips, i)
    return deck, lh, tips, source, assay


@scenario("E96-hasTip-drop", HasTipError)
async def _e96_has_tip_drop():
    """H, then ``drop_tips96(tips)``: channels 0-4 are queued (spots 0-4 pending tips, head 0-4
    pending removals) before spot 5 raises."""
    deck, lh, tips, _source, assay = await _h()
    exc = await _catch(lh.drop_tips96(tips))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-hasTip-drop-m8", HasTipError)
async def _e96_has_tip_drop_m8():
    """H with channels 0-7 tipless: spot 5 is not touched (its channel holds nothing), spot 77 raises."""
    deck, lh, tips, _source, assay = await _h(channels_without_a_tip=range(8))
    exc = await _catch(lh.drop_tips96(tips))
    return Raised(exc, deck=deck, lh=lh, tips=tips)


@scenario("E96-return", HasTipError)
async def _e96_return():
    """A spot refilled after the pick-up, then ``return_tips96()``: PLR's own nested 96 call."""
    deck, lh, tips, _source, _assay = await _world()
    await lh.pick_up_tips96(tips)
    _give_spot_a_committed_tip(tips, 5)
    exc = await _catch(lh.return_tips96())
    return Raised(exc, deck=deck, lh=lh, tips=tips)


def _add_second_rack(deck):
    tip_carrier = deck.get_resource("tip_carrier")
    tip_carrier[1] = tips_b = hamilton_96_tiprack_300uL_filter(name="tips_b")
    return tips_b


@scenario("E96-R2", HasTipError)
async def _e96_r2():
    """R2: after H's residue, ``pick_up_tips96`` from a second full rack raises at channel 5. Committed
    reading: 96 channels hold a tip. A ``has_tip`` (pending) reading: 91 (channels 0-4 look empty)."""
    deck, lh, tips, _source, _assay = await _h()
    assert isinstance(await _catch(lh.drop_tips96(tips)), HasTipError)
    tips_b = _add_second_rack(deck)
    exc = await _catch(lh.pick_up_tips96(tips_b))
    return Raised(exc, deck=deck, lh=lh, tips=tips, tips_b=tips_b)


@scenario("E96-K", TooLittleLiquidError)
async def _e96_k():
    """K: after H's residue the assay wells 0-4 and 10 hold 10 uL and the rest 200; 50 uL aspirated.
    PLR skips channels 0-4 (pending removal) and names C2 only; the head physically holds all 96."""
    deck, lh, tips, _source, assay = await _h()
    assert isinstance(await _catch(lh.drop_tips96(tips)), HasTipError)
    for i, well in enumerate(assay.get_all_items()):
        well.tracker.set_volume(10 if i in (0, 1, 2, 3, 4, 10) else 200)
    exc = await _catch(lh.aspirate96(assay, volume=50.0))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-noTip-residue", NoTipError)
async def _e96_notip_residue():
    """L: F3, then ``drop_tips96``: channel 0 holds a PENDING tip from the refused pick-up and no
    committed one, so ``get_tip()`` raises NoTip."""
    deck, lh, tips, assay = await _f3()
    assert isinstance(await _catch(lh.pick_up_tips96(tips)), HasTipError)
    exc = await _catch(lh.drop_tips96(tips))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-noTip-residue-asp", NoTipError)
async def _e96_notip_residue_asp():
    """L, second op: ``aspirate96`` builds its ``tips`` list from ``get_tip()`` of every pending tip."""
    deck, lh, tips, assay = await _f3()
    assert isinstance(await _catch(lh.pick_up_tips96(tips)), HasTipError)
    exc = await _catch(lh.aspirate96(assay, volume=10.0))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-noTip-spot", NoTipError)
async def _e96_notip_spot():
    """Q: after H's residue, ``pick_up_tips96(tips)``: spot 0 holds a pending tip and no committed
    one, so ``TipSpot.get_tip()`` (committed) raises NoTip at the head's add_tip call."""
    deck, lh, tips, _source, _assay = await _h()
    assert isinstance(await _catch(lh.drop_tips96(tips)), HasTipError)
    exc = await _catch(lh.pick_up_tips96(tips))
    return Raised(exc, deck=deck, lh=lh, tips=tips)


@scenario("E96-residue-TLL", TooLittleLiquidError)
async def _e96_residue_tll():
    """B, then row D is fixed with set_volume(80) and the aspirate retried: A1-C1 still carry the first
    refusal's queued removals (pending 30), so PLR raises at A1 again while every committed
    volume (80) covers the 50 uL."""
    deck, lh, tips, _source, assay = await _world()
    for well in assay.get_all_items():
        well.tracker.set_volume(80)
    for well in assay["D1:D12"]:
        well.tracker.set_volume(10)
    await lh.pick_up_tips96(tips)
    assert isinstance(await _catch(lh.aspirate96(assay, volume=50.0)), TooLittleLiquidError)
    for well in assay["D1:D12"]:
        well.tracker.set_volume(80)
    exc = await _catch(lh.aspirate96(assay, volume=50.0))
    assert (assay.get_item("A1").tracker.volume, assay.get_item("A1").tracker.pending_volume) == (80, 30)
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-N", TooLittleVolumeError)
async def _e96_n():
    """N: a Container (max 3,000) holding 1,000; the tips hold 30 and dispense 30 each: 2,880 > 2,000.
    Single-container TLV: a context, no panel row (today's gap, errors.py:257-258)."""
    deck, lh, tips, _source, _assay = await _world()
    container = _bare_container(deck, "tub", max_volume=3000.0)
    container.tracker.set_volume(1000)
    await lh.pick_up_tips96(tips)
    _set_tip_volumes(lh, 30)
    exc = await _catch(lh.dispense96(container, volume=30.0))
    return Raised(exc, deck=deck, lh=lh, container=container)


@scenario("E96-onewell-TLV", TooLittleVolumeError)
async def _e96_onewell_tlv():
    """N on a one-well Plate: the well is the owner, its parent is the Plate."""
    deck, lh, tips, _source, _assay = await _world()
    plate = _one_well_plate(deck)
    well = plate.get_item(0)
    well.tracker.set_volume(98000)
    await lh.pick_up_tips96(tips)
    _set_tip_volumes(lh, 30)
    exc = await _catch(lh.dispense96(plate, volume=30.0))
    return Raised(exc, deck=deck, lh=lh, plate=plate, well=well)


@scenario("E96-disp48", TooLittleLiquidError)
async def _e96_disp48():
    """dispense96's tip loop runs BEFORE its count check (C6): empty tips, 48 wells, a tip error."""
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.dispense96(assay["A1:H6"], volume=50.0))
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-disp384", TooLittleLiquidError)
async def _e96_disp384():
    deck, lh, tips, _source, _assay = await _world()
    plate = Revvity_384_wellplate_28ul_Ub(name="plate384")
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.dispense96(plate, volume=50.0))
    return Raised(exc, deck=deck, lh=lh, plate=plate)


@scenario("E96-disp-small", TooLittleLiquidError)
async def _e96_disp_small():
    """The container fails the head's fit check, which runs after the tip loop."""
    deck, lh, tips, _source, _assay = await _world()
    small = _bare_container(deck, "small", x=50.0, y=50.0, z=20.0, max_volume=1000.0)
    assert not lh._check_96_head_fits_in_container(small)
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.dispense96(small, volume=50.0))
    return Raised(exc, deck=deck, lh=lh, small=small)


@scenario("E96-under-1ch", TooLittleLiquidError)
async def _e96_under_1ch():
    """A ``*96`` op called from a non-96 op frame (a subclass ``aspirate`` calling ``aspirate96``):
    a mixed stack, the INNERMOST frame is a 96 op."""
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips96(tips)

    class LH1(LiquidHandler):
        async def aspirate(self, resources, vols, **kwargs):
            return await self.aspirate96(resources, volume=vols)

    lh.__class__ = LH1
    exc = await _catch(lh.aspirate(assay, 50.0))
    return Raised(exc, deck=deck, lh=lh, assay=assay)


@scenario("E96-runtime", RuntimeError)
async def _e96_runtime():
    """A non-display class from a 96 op (drop with liquid in the tips): a premise, not a control."""
    deck, lh, tips, source, _assay = await _world()
    await lh.pick_up_tips96(tips)
    await lh.aspirate96(source, volume=30.0)
    exc = await _catch(lh.drop_tips96(tips))
    return Raised(exc, deck=deck, lh=lh)


@scenario("E96-tooSmall", ValueError)
async def _e96_too_small():
    """aspirate96 checks the fit BEFORE its loops, so this is a ValueError, not a tracker error."""
    deck, lh, tips, _source, _assay = await _world()
    small = _bare_container(deck, "small", x=50.0, y=50.0, z=20.0, max_volume=1000.0)
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96(small, volume=50.0))
    return Raised(exc, deck=deck, lh=lh)


@scenario("impostor", TooLittleLiquidError)
async def _impostor():
    """A well that is NOT on the deck but carries the deck well's exact name (and so tracker
    ``thing``), aspirated from through the real LH.
    """
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips([tips.get_item("A1")])
    fake_plate = cor_96_wellplate_360uL_Fb(name="assay")
    impostor = fake_plate.get_item("A1")
    real = assay.get_item("A1")
    assert impostor.name == real.name and impostor is not real
    assert impostor.tracker.thing == real.tracker.thing
    exc = await _catch(lh.aspirate([impostor], vols=[50.0], use_channels=[0]))
    return Raised(exc, deck=deck, lh=lh, impostor=impostor, real=real, fake_plate=fake_plate)


@scenario("neg_value_error", ValueError)
async def _neg_value_error():
    deck, lh, tips, source, _assay = await _world()
    await lh.pick_up_tips([tips.get_item("A1")])
    exc = await _catch(lh.aspirate([source.get_item("A1")], vols=[50.0, 60.0], use_channels=[0]))
    return Raised(exc, deck=deck, lh=lh)


@scenario("neg_ghost_volume", TooLittleLiquidError)
async def _neg_ghost_volume():
    """A tracker whose ``thing`` names nothing on any deck, no LH frame. ``deck`` is reachable from
    this frame's locals, so a lookup that finds nothing is the reason for ``None``.
    """
    deck, lh, tips, source, assay = await _world()
    ghost = VolumeTracker(thing="ghost_well_volume_tracker", max_volume=100.0)
    try:
        ghost.remove_liquid(5.0)
    except TooLittleLiquidError as exc:
        return Raised(exc, deck=deck, lh=lh)
    raise AssertionError("the ghost tracker was expected to raise")


@scenario("neg_ghost_spot", NoTipError)
async def _neg_ghost_spot():
    deck, lh, tips, source, assay = await _world()
    ghost = TipTracker(thing="nowhere_tipspot_A1")
    try:
        ghost.get_tip()
    except NoTipError as exc:
        return Raised(exc, deck=deck, lh=lh)
    raise AssertionError("the ghost tip tracker was expected to raise")


@scenario("neg_tip_name_volume", TooLittleLiquidError)
async def _neg_tip_name_volume():
    """A resting tip's own VolumeTracker (``thing`` = the tip's name, which IS on the deck)."""
    deck, lh, tips, source, assay = await _world()
    tip = tips.get_item("A1").tip
    assert tip is not None and deck.get_resource(tip.name) is tip
    assert tip.tracker.thing == tip.name
    try:
        tip.tracker.remove_liquid(5.0)
    except TooLittleLiquidError as exc:
        return Raised(exc, deck=deck, lh=lh, tip=tip)
    raise AssertionError("an empty tip was expected to raise on remove_liquid")


@scenario("neg_tip_name_tracker", NoTipError)
async def _neg_tip_name_tracker():
    """A TipTracker whose ``thing`` matches a ``Tip`` on the deck (round 11, C11-15)."""
    deck, lh, tips, source, assay = await _world()
    tip = tips.get_item("A1").tip
    assert tip is not None and deck.get_resource(tip.name) is tip
    tracker = TipTracker(thing=tip.name)
    try:
        tracker.get_tip()
    except NoTipError as exc:
        return Raised(exc, deck=deck, lh=lh, tip=tip)
    raise AssertionError("an empty tracker was expected to raise")


@scenario("neg_bare_discard", RuntimeError)
async def _neg_bare_discard():
    deck, lh, _tips, _source, _assay = await _world()
    exc = await _catch(lh.discard_tips())
    assert str(exc) == "No tips have been picked up and no channels were specified."
    return Raised(exc, deck=deck, lh=lh)


@scenario("neg_bare_return", RuntimeError)
async def _neg_bare_return():
    deck, lh, _tips, _source, _assay = await _world()
    exc = await _catch(lh.return_tips())
    assert str(exc) == "No tips have been picked up."
    return Raised(exc, deck=deck, lh=lh)


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_every_scenario_raises_the_class_it_claims(name):
    """The setups themselves, without the module under test: a case that stops raising at a pin
    bump fails here instead of letting its resolver test pass vacuously (AC-15 preamble).
    """
    r = case(name)
    assert type(r.exc) is EXPECTED_CLASS[name], (name, type(r.exc), str(r.exc))
    assert r.exc.__traceback__ is not None


def test_e14_first_failure_is_the_channel_3_has_tip_error():
    """E14 step 2 leaves pending tips on channels 0-2 (rebuilt, so it does not depend on the cache)."""

    async def go():
        deck, lh, tips, _s, _a = await _world()
        await lh.pick_up_tips(tips["D1:D1"], use_channels=[3])
        exc = await _catch(lh.pick_up_tips(tips["A2:H2"]))
        return lh, exc

    lh, exc = asyncio.run(go())
    assert isinstance(exc, HasTipError) and str(exc) == "Channel has tip"
    assert [lh.head[i].has_tip for i in range(4)] == [True, True, True, True]
    committed = []
    for i in range(4):
        try:
            lh.head[i].get_tip()
            committed.append(True)
        except NoTipError:
            committed.append(False)
    assert committed == [False, False, False, True]


# --------------------------------------------------------------------------- helpers over a context


def _ids(objs):
    return [id(o) for o in objs]


def _same(objs, expected):
    assert _ids(objs) == _ids(expected), ([getattr(o, "name", o) for o in objs],
                                          [getattr(o, "name", o) for o in expected])


def _resolve(resolve, r, **kw):
    return resolve(r.exc, r.exc.__traceback__, **kw)


def _offenders(ctx):
    return [(o.target if isinstance(o.target, int) else id(o.target), o.requested, o.available)
            for o in ctx.offending]


# --------------------------------------------------------------------------- the case checks
#
# Each check is a function of a RESOLVER, so the controls can be run through the same code that
# judges the real module.


def check_e1(resolve):
    r = case("E1")
    ctx = _resolve(resolve, r)
    assert ctx is not None
    assert ctx.error == "TooLittleLiquidError"
    assert ctx.owner_kind == CONTAINER and ctx.owner is r.wells[0] and ctx.rule == "a"
    assert ctx.channel is None
    assert ctx.action == "aspirate" and ctx.op == "aspirate"
    _same(ctx.resources, r.wells)
    assert tuple(ctx.channels) == tuple(range(8)) and tuple(ctx.volumes) == (80.0,) * 8
    _same(ctx.targets, r.wells)  # offending A1:H1
    assert ctx.requested == 80.0 and ctx.available == 50.0  # committed
    assert [(o.requested, o.available) for o in ctx.offending] == [(80.0, 50.0)] * 8
    assert ctx.head96 is False and ctx.container_mode is None  # the 1-channel path says so (#5659)


def check_e2(resolve):
    r = case("E2")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleVolumeError"
    assert ctx.owner_kind == CONTAINER and ctx.owner is r.well
    assert ctx.action == "dispense"
    _same(ctx.targets, [r.well])
    assert (ctx.requested, ctx.available) == (400.0, 360.0)  # committed room = max - volume


def check_e2_summed(resolve):
    r = case("E2_summed")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleVolumeError"
    assert ctx.owner is r.trough and ctx.owner_kind == CONTAINER
    _same(ctx.targets, [r.trough])  # one resource, the demand of two channels
    assert (ctx.requested, ctx.available) == (400.0, 300.0)


def check_e3(resolve):
    r = case("E3")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleVolumeError"
    assert ctx.owner_kind == TIP and ctx.owner is r.tip and ctx.channel == 0 and ctx.rule == "c"
    assert ctx.action == "aspirate"
    assert ctx.targets == (0,)
    assert (ctx.requested, ctx.available) == (400.0, 360.0)


def check_e3_per_channel(resolve):
    r = case("E3_per_channel")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner_kind == TIP
    assert ctx.owner is r.tip1 and ctx.channel == 1
    assert ctx.targets == (1,)  # per channel, not summed: 300 fits, 400 does not
    assert (ctx.requested, ctx.available) == (400.0, 360.0)


def check_e4(resolve):
    r = case("E4")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "HasTipError"
    assert ctx.owner_kind == CHANNEL and ctx.channel == 0 and ctx.owner is None and ctx.rule == "e"
    assert ctx.action == "pick_up_tips"
    assert ctx.targets == tuple(range(8))  # every channel that already holds a committed tip
    assert ctx.requested is None and ctx.available is None


def check_e4_off(resolve):
    r = case("E4-off")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner_kind == CHANNEL and ctx.channel == 0 and ctx.rule == "e"
    assert ctx.targets == tuple(range(8))


def check_e5(resolve):
    r = case("E5")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "HasTipError"
    assert ctx.owner_kind == TIP_SPOT and ctx.owner is r.spot and ctx.rule == "a"
    assert ctx.channel is None and ctx.action == "drop_tips"
    _same(ctx.targets, [r.spot])


def check_e6(resolve):
    r = case("E6")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "NoTipError"
    assert ctx.owner_kind == CHANNEL and ctx.channel == 0 and ctx.owner is None and ctx.rule == "b"
    assert ctx.action == "aspirate" and ctx.targets == (0,)


def check_e6_off(resolve):
    r = case("E6-off")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner_kind == CHANNEL and ctx.channel == 0 and ctx.rule == "b"


def check_e7(resolve):
    r = case("E7")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "NoTipError"
    assert ctx.owner_kind == TIP_SPOT and ctx.owner is r.spot and ctx.rule == "a"
    assert ctx.action == "pick_up_tips"
    _same(ctx.targets, [r.spot])
    # the frame raised before its queue loop: only tip_spots and use_channels are bound
    assert tuple(ctx.channels) == (1,)
    _same(ctx.resources, [r.spot])


def check_e8(resolve):
    r = case("E8")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleLiquidError"
    assert ctx.owner_kind == CONTAINER and ctx.owner is r.well and ctx.rule == "d"
    assert ctx.action is None and ctx.op is None
    assert tuple(ctx.resources) == () and tuple(ctx.channels) == ()
    _same(ctx.targets, [r.well])
    assert (ctx.requested, ctx.available) == (999.0, 0.0)


def check_e8_spot(resolve):
    r = case("E8_spot")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "NoTipError"
    assert ctx.owner_kind == TIP_SPOT and ctx.owner is r.spot and ctx.rule == "d"
    assert ctx.action is None


def check_e8_channel(resolve):
    r = case("E8_channel")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner_kind == CHANNEL and ctx.channel == 3
    assert ctx.owner is None and ctx.rule == "d" and ctx.action is None


def check_e9(resolve):
    r = case("E9")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleLiquidError"
    assert ctx.owner_kind == CONTAINER and ctx.owner is r.trough
    _same(ctx.targets, [r.trough])
    assert ctx.requested == 240.0  # summed over 8 channels, not PLR's 30 and not per channel
    assert ctx.available == 100.0  # committed, not PLR's 10.0
    assert ctx.available != 10.0  # PLR's message counts the pending 30 x 3 already removed
    assert len(ctx.channels) == 8


def check_e10(resolve):
    r = case("E10")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner is r.wells[0]
    _same(ctx.targets, r.wells[:4])  # exactly A1:D1
    assert [o.available for o in ctx.offending] == [50.0] * 4
    assert ctx.requested == 80.0 and ctx.available == 50.0


def check_e11(resolve):
    r = case("E11")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "HasTipError"
    assert ctx.owner_kind == TIP_SPOT and ctx.owner is r.spot
    assert ctx.action == "return_tips"  # the OUTERMOST ACTIONS frame, not drop_tips
    assert ctx.op == "drop_tips"  # the innermost supplies the locals
    _same(ctx.targets, [r.spot])
    assert tuple(ctx.channels) == (0,)


def check_e12(resolve):
    r = case("E12")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleLiquidError"
    assert ctx.owner_kind == TIP and ctx.owner is r.tip and ctx.channel == 0 and ctx.rule == "c"
    assert ctx.action == "dispense" and ctx.targets == (0,)
    assert (ctx.requested, ctx.available) == (100.0, 0.0)


def check_e12_per_channel(resolve):
    r = case("E12_per_channel")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner_kind == TIP
    assert ctx.owner is r.tip1 and ctx.channel == 1
    assert ctx.targets == (1,)  # per channel: the tip holding 50 has enough for its own 30
    assert (ctx.requested, ctx.available) == (30.0, 10.0)


def check_e13(resolve):
    r = case("E13")
    assert _resolve(resolve, r) is None


def check_residue_direct_tll(resolve):
    assert _resolve(resolve, case("residue_direct_tll")) is None


def check_residue_direct_tlv(resolve):
    assert _resolve(resolve, case("residue_direct_tlv")) is None


def check_over_committed_direct(resolve):
    r = case("over_committed_direct")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner is r.well and ctx.rule == "d"
    assert (ctx.requested, ctx.available) == (105.0, 100.0)  # committed, not the pending 90


def check_e4_channel1(resolve):
    r = case("E4_channel1")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner_kind == CHANNEL and ctx.rule == "e"
    assert ctx.channel == 1  # the loop local, not the first channel of the op
    assert ctx.targets == (1,)  # committed: only channel 1 holds a tip
    assert tuple(ctx.channels) == (0, 1)


def check_impostor_in_op(resolve):
    assert _resolve(resolve, case("impostor_in_op")) is None


def check_impostor_direct(resolve):
    assert _resolve(resolve, case("impostor_direct")) is None


def check_nested_trackers(resolve):
    r = case("nested_trackers")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner is r.b1 and ctx.rule == "d"
    assert (ctx.requested, ctx.available) == (999.0, 100.0)  # the innermost tracker frame's own volume


def check_e14(resolve):
    r = case("E14")
    assert _resolve(resolve, r) is None


def check_e15(resolve):
    r = case("E15")
    assert _resolve(resolve, r) is None


def check_e16(resolve):
    r = case("E16")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "NoTipError"
    assert ctx.owner_kind == CHANNEL and ctx.channel == 0 and ctx.owner is None and ctx.rule == "b"
    assert ctx.action == "discard_tips" and ctx.op == "drop_tips"
    assert ctx.targets == (0,)
    # the innermost frame (drop_tips) supplies the op resources: the trash, one per channel
    assert len(ctx.resources) == 1 and ctx.resources[0] is r.deck.get_trash_area()


def check_e1_via_96(resolve):
    r = case("E1_via_96")
    assert _resolve(resolve, r) is None


def check_impostor(resolve):
    r = case("impostor")
    assert _resolve(resolve, r) is None


def _check_none(name):
    def check(resolve):
        r = case(name)
        assert _resolve(resolve, r) is None

    check.__name__ = f"check_{name}"
    return check


check_neg_value_error = _check_none("neg_value_error")
check_neg_ghost_volume = _check_none("neg_ghost_volume")
check_neg_ghost_spot = _check_none("neg_ghost_spot")
check_neg_tip_name_volume = _check_none("neg_tip_name_volume")
check_neg_tip_name_tracker = _check_none("neg_tip_name_tracker")
check_neg_bare_discard = _check_none("neg_bare_discard")
check_neg_bare_return = _check_none("neg_bare_return")


def _ids_of(targets):
    return [t.get_identifier() for t in targets]


def check_e96_empty(resolve):
    r = case("E96-empty")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleLiquidError"
    assert ctx.owner_kind == CONTAINER and ctx.owner is r.assay.get_item(0) and ctx.rule == "a"
    assert ctx.channel is None
    assert ctx.action == "aspirate96" and ctx.op == "aspirate96"
    assert ctx.head96 is True and ctx.container_mode == "per_channel"
    assert tuple(ctx.channels) == tuple(range(96)) and tuple(ctx.volumes) == (50.0,) * 96
    _same(ctx.resources, r.assay.get_all_items())
    _same(ctx.targets, r.assay.get_all_items())  # every well offends: the plate is empty
    assert ctx.requested == 50.0 and ctx.available == 0.0
    assert [(o.requested, o.available) for o in ctx.offending] == [(50.0, 0.0)] * 96


def check_e96_single(resolve):
    r = case("E96-single")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleLiquidError"
    assert ctx.container_mode == "single" and ctx.head96 is True
    assert ctx.owner_kind == CONTAINER and ctx.owner is r.container and ctx.rule == "a"
    assert ctx.action == "aspirate96"
    assert tuple(ctx.channels) == tuple(range(96))
    _same(ctx.resources, [r.container] * 96)  # one container, one entry per channel
    _same(ctx.targets, [r.container])
    assert (ctx.requested, ctx.available) == (2880.0, 2000.0)  # 96 x 30 against the committed 2,000


def check_e96_onewell_plate(resolve):
    r = case("E96-onewell-plate")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.container_mode == "single" and ctx.head96 is True
    assert ctx.owner_kind == CONTAINER and ctx.owner is r.well and ctx.rule == "a"
    assert ctx.owner.parent is r.plate  # the well's parent is a Plate: `_in_plate` would say "plate"
    _same(ctx.resources, [r.well] * 96)
    _same(ctx.targets, [r.well])
    assert (ctx.requested, ctx.available) == (2880.0, 1000.0)


def check_e96_rowd(resolve):
    r = case("E96-rowD")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner is r.assay.get_item("D1") and ctx.rule == "a"
    assert ctx.container_mode == "per_channel" and tuple(ctx.channels) == tuple(range(96))
    _same(ctx.targets, r.assay["D1:D12"])  # exactly D1-D12, not the first failure only
    assert _ids_of(ctx.targets) == [f"D{i}" for i in range(1, 13)]
    assert [(o.requested, o.available) for o in ctx.offending] == [(50.0, 10.0)] * 12
    assert (ctx.requested, ctx.available) == (50.0, 10.0)  # committed 10, not PLR's pending state


def check_e96_partial(resolve):
    r = case("E96-partial")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner is r.assay.get_item("D1")
    wells = r.assay.get_all_items()
    absent = (0, 1, 2, 50)  # A1, B1, C1, C7: no tip on those channels, so no well is demanded
    assert tuple(ctx.channels) == tuple(c for c in range(96) if c not in absent)
    _same(ctx.targets, [w for i, w in enumerate(wells) if i not in absent])
    assert len(ctx.targets) == 92
    assert not {"A1", "B1", "C1", "C7"} & set(_ids_of(ctx.targets))
    _same(ctx.resources, [wells[c] for c in ctx.channels])
    assert tuple(ctx.volumes) == (50.0,) * 92


def check_e96_tip_tlv(resolve):
    r = case("E96-tipTLV")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleVolumeError"
    assert ctx.owner_kind == TIP and ctx.rule == "c" and ctx.channel == 0
    assert ctx.owner is r.lh.head96[0].get_tip()
    assert ctx.action == "aspirate96" and ctx.head96 is True
    assert ctx.targets == tuple(range(96))
    assert (ctx.requested, ctx.available) == (200.0, 160.0)  # the tip's committed room: 360 - 200


def check_e96_tip_tll(resolve):
    r = case("E96-tipTLL")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleLiquidError"
    assert ctx.owner_kind == TIP and ctx.rule == "c" and ctx.channel == 0
    assert ctx.action == "dispense96" and ctx.targets == tuple(range(96))
    assert (ctx.requested, ctx.available) == (50.0, 30.0)
    # the tip rows never index `containers`; the container mode is still the one the op used
    assert ctx.container_mode == "per_channel"


def check_e96_tip_tll_d2(resolve):
    r = case("E96-tipTLL-D2")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner_kind == TIP and ctx.channel == 7
    assert ctx.owner is r.lh.head96[7].get_tip()
    assert ctx.targets == (7, 9)  # per channel: the other 94 tips hold 30 >= 25
    assert (ctx.requested, ctx.available) == (25.0, 20.0)


def check_e96_disp_tlv(resolve):
    r = case("E96-dispTLV")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleVolumeError"
    assert ctx.owner is r.assay.get_item(10) and ctx.owner_kind == CONTAINER and ctx.rule == "a"
    assert ctx.action == "dispense96" and ctx.container_mode == "per_channel"
    assert _ids_of(ctx.targets) == ["C2", "D2", "A6"]
    _same(ctx.targets, [r.assay.get_item(i) for i in (10, 11, 40)])
    assert [(o.requested, o.available) for o in ctx.offending] == [(100.0, 30.0)] * 3
    assert tuple(ctx.volumes) == (100.0,) * 96


def check_e96_has_tip_pickup(resolve):
    r = case("E96-hasTip-pickup")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "HasTipError"
    assert ctx.owner_kind == CHANNEL and ctx.channel == 3 and ctx.owner is None and ctx.rule == "b"
    assert ctx.action == "pick_up_tips96" and ctx.op == "pick_up_tips96" and ctx.head96 is True
    assert ctx.container_mode is None
    assert ctx.targets == (3, 50)  # committed tips: not channels 0-2, which only hold a pending tip
    assert tuple(ctx.channels) == tuple(range(96))  # every spot of the rack holds a committed tip
    _same(ctx.resources, [r.tips.get_item(c) for c in range(96)])
    assert ctx.requested is None and ctx.available is None


def check_e96_has_tip_pickup_s3(resolve):
    r = case("E96-hasTip-pickup-s3")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner_kind == CHANNEL and ctx.channel == 50 and ctx.rule == "b"
    assert ctx.targets == (50,)  # channel 3 holds a tip, but spot 3 has none to pick up
    assert tuple(ctx.channels) == tuple(c for c in range(96) if c != 3)


def check_e96_has_tip_drop(resolve):
    r = case("E96-hasTip-drop")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "HasTipError"
    assert ctx.owner_kind == TIP_SPOT and ctx.owner is r.tips.get_item(5) and ctx.rule == "a"
    assert ctx.owner.get_identifier() == "F1" and ctx.channel is None
    assert ctx.action == "drop_tips96" and ctx.op == "drop_tips96" and ctx.head96 is True
    _same(ctx.targets, [r.tips.get_item(5), r.tips.get_item(77)])  # committed tips: not spots 0-4
    assert tuple(ctx.channels) == tuple(range(96))  # the head physically holds 96 tips
    _same(ctx.resources, [r.tips.get_item(c) for c in range(96)])


def check_e96_has_tip_drop_m8(resolve):
    r = case("E96-hasTip-drop-m8")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.owner is r.tips.get_item(77) and ctx.rule == "a"
    _same(ctx.targets, [r.tips.get_item(77)])  # spot 5 holds a tip, but channel 5 holds none
    assert tuple(ctx.channels) == tuple(range(8, 96))


def check_e96_return(resolve):
    r = case("E96-return")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "HasTipError"
    assert ctx.action == "return_tips96" and ctx.op == "drop_tips96"  # the user's call; the frame used
    assert ctx.owner_kind == TIP_SPOT and ctx.owner is r.tips.get_item(5)
    _same(ctx.targets, [r.tips.get_item(5)])
    assert ctx.head96 is True


def check_e96_r2(resolve):
    r = case("E96-R2")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "HasTipError"
    assert ctx.owner_kind == CHANNEL and ctx.channel == 5 and ctx.rule == "b"
    assert ctx.action == "pick_up_tips96"
    assert len(ctx.offending) == 96 and ctx.targets == tuple(range(96))
    _same(ctx.resources, [r.tips_b.get_item(c) for c in range(96)])


def check_e96_k(resolve):
    r = case("E96-K")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleLiquidError"
    assert ctx.owner is r.assay.get_item(10) and ctx.owner.get_identifier() == "C2"
    assert _ids_of(ctx.targets) == ["A1", "B1", "C1", "D1", "E1", "C2"]  # what the head physically holds
    assert [(o.requested, o.available) for o in ctx.offending] == [(50.0, 10.0)] * 6
    assert tuple(ctx.channels) == tuple(range(96))


def check_e96_n(resolve):
    r = case("E96-N")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.error == "TooLittleVolumeError"
    assert ctx.container_mode == "single" and ctx.owner is r.container and ctx.rule == "a"
    assert ctx.action == "dispense96"
    assert (ctx.requested, ctx.available) == (2880.0, 2000.0)  # committed room: 3,000 - 1,000


def check_e96_onewell_tlv(resolve):
    r = case("E96-onewell-TLV")
    ctx = _resolve(resolve, r)
    assert ctx is not None and ctx.container_mode == "single" and ctx.owner is r.well
    assert ctx.owner.parent is r.plate
    assert (ctx.requested, ctx.available) == (2880.0, 2000.0)


check_e96_noTip_residue = _check_none("E96-noTip-residue")
check_e96_noTip_residue_asp = _check_none("E96-noTip-residue-asp")
check_e96_noTip_spot = _check_none("E96-noTip-spot")
check_e96_residue_tll = _check_none("E96-residue-TLL")
check_e96_disp48 = _check_none("E96-disp48")
check_e96_disp384 = _check_none("E96-disp384")
check_e96_disp_small = _check_none("E96-disp-small")
check_e96_under_1ch = _check_none("E96-under-1ch")
check_e96_runtime = _check_none("E96-runtime")
check_e96_too_small = _check_none("E96-tooSmall")

#: the 96 scenarios that resolve to a context, and the ones that must give ``None`` (and why)
POSITIVE_96 = {
    "E96-empty": check_e96_empty, "E96-single": check_e96_single,
    "E96-onewell-plate": check_e96_onewell_plate, "E96-rowD": check_e96_rowd,
    "E96-partial": check_e96_partial, "E96-tipTLV": check_e96_tip_tlv,
    "E96-tipTLL": check_e96_tip_tll, "E96-tipTLL-D2": check_e96_tip_tll_d2,
    "E96-dispTLV": check_e96_disp_tlv, "E96-hasTip-pickup": check_e96_has_tip_pickup,
    "E96-hasTip-pickup-s3": check_e96_has_tip_pickup_s3, "E96-hasTip-drop": check_e96_has_tip_drop,
    "E96-hasTip-drop-m8": check_e96_has_tip_drop_m8, "E96-return": check_e96_return,
    "E96-R2": check_e96_r2, "E96-K": check_e96_k, "E96-N": check_e96_n,
    "E96-onewell-TLV": check_e96_onewell_tlv,
}
NONE_96 = {
    "E96-noTip-residue": check_e96_noTip_residue, "E96-noTip-residue-asp": check_e96_noTip_residue_asp,
    "E96-noTip-spot": check_e96_noTip_spot, "E96-residue-TLL": check_e96_residue_tll,
    "E96-disp48": check_e96_disp48, "E96-disp384": check_e96_disp384,
    "E96-disp-small": check_e96_disp_small, "E96-under-1ch": check_e96_under_1ch,
    "E96-runtime": check_e96_runtime, "E96-tooSmall": check_e96_too_small,
}

CHECKS = {
    "E1": check_e1, "E2": check_e2, "E2_summed": check_e2_summed, "E3": check_e3,
    "E3_per_channel": check_e3_per_channel, "E4": check_e4, "E4-off": check_e4_off,
    "E5": check_e5, "E6": check_e6, "E6-off": check_e6_off, "E7": check_e7, "E8": check_e8,
    "E8_spot": check_e8_spot, "E8_channel": check_e8_channel, "E9": check_e9, "E10": check_e10,
    "E11": check_e11, "E12": check_e12, "E12_per_channel": check_e12_per_channel,
    "residue_direct_tll": check_residue_direct_tll, "residue_direct_tlv": check_residue_direct_tlv,
    "over_committed_direct": check_over_committed_direct,
    "E4_channel1": check_e4_channel1, "impostor_in_op": check_impostor_in_op,
    "impostor_direct": check_impostor_direct, "nested_trackers": check_nested_trackers,
    "E13": check_e13, "E14": check_e14, "E15": check_e15, "E16": check_e16,
    "E1_via_96": check_e1_via_96, "impostor": check_impostor,
    "neg_value_error": check_neg_value_error, "neg_ghost_volume": check_neg_ghost_volume,
    "neg_ghost_spot": check_neg_ghost_spot, "neg_tip_name_volume": check_neg_tip_name_volume,
    "neg_tip_name_tracker": check_neg_tip_name_tracker, "neg_bare_discard": check_neg_bare_discard,
    "neg_bare_return": check_neg_bare_return,
    **POSITIVE_96, **NONE_96,
}


def test_every_scenario_has_a_check():
    assert set(CHECKS) == set(SCENARIOS)


@pytest.mark.parametrize("name", sorted(CHECKS))
def test_case(cx, name):
    """AC-15: each case raises the real error and resolves as the spec says."""
    CHECKS[name](cx.resolve)


# --------------------------------------------------------------------------- the API and its types


def test_owner_kind_constants_and_module_shape(cx):
    assert (cx.OWNER_CONTAINER, cx.OWNER_TIP_SPOT, cx.OWNER_CHANNEL, cx.OWNER_TIP) == (
        CONTAINER, TIP_SPOT, CHANNEL, TIP)
    assert callable(cx.resolve)
    assert dataclasses.is_dataclass(cx.ErrorContext) and dataclasses.is_dataclass(cx.Offender)
    params = inspect.signature(cx.resolve).parameters
    assert list(params)[:2] == ["exc", "tb"]
    assert params["tb"].default is None


def test_tb_defaults_to_the_exception_traceback(cx):
    r = case("E1")
    assert cx.resolve(r.exc).owner is r.wells[0]


def test_context_is_immutable(cx):
    ctx = cx.resolve(case("E1").exc)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.requested = 1.0


def test_resolve_is_read_only(cx):
    """Resolving reads committed and pending state and changes neither, on the cases that walk
    every tracker (E14: pending tips; E13: pending volume).
    """

    def snapshot(r):
        lh = r.lh
        heads = []
        for c, t in lh.head.items():
            try:
                t.get_tip()
                committed = True
            except NoTipError:
                committed = False
            heads.append((c, t.has_tip, committed))
        vols = []
        for res in [r.deck, *r.deck.get_all_children()]:
            tr = getattr(res, "tracker", None)
            if isinstance(tr, VolumeTracker):
                vols.append((res.name, tr.volume, tr.pending_volume))
        spots = [(s.name, s.tip is not None) for s in r.deck.get_all_children() if isinstance(s, TipSpot)]
        return heads, vols, spots

    for name in ("E13", "E14", "E4", "E7"):
        r = case(name)
        before = snapshot(r)
        cx.resolve(r.exc, r.exc.__traceback__)
        assert snapshot(r) == before, name


# --------------------------------------------------------------------------- the frame filter


def test_e1_stack_has_wrapper_frames_that_the_filter_must_exclude(cx, gl):
    """PLR 1.0 wraps LH methods in ``wrapper`` frames whose ``self`` IS the handler
    (``legacy/machines/machine.py:58``; ``events/bus.py:331`` has none). They are not actions.
    """
    r = case("E1")
    frames = []
    tb = r.tb
    while tb is not None:
        frames.append(tb.tb_frame)
        tb = tb.tb_next
    wrappers = [f for f in frames if f.f_code.co_name == "wrapper" and isinstance(f.f_locals.get("self"), LiquidHandler)]
    assert wrappers, "the stack no longer has a wrapper frame with an LH self: the filter is untested"
    assert "wrapper" not in gl.ACTIONS
    ctx = cx.resolve(r.exc)
    assert ctx.action == "aspirate" and ctx.op == "aspirate"


def test_a_filter_that_admits_wrapper_frames_fails_e1(cx, gl, monkeypatch):
    """Control: with ``wrapper`` added to ``glossary.ACTIONS`` the OUTERMOST action becomes
    ``wrapper`` and E1's check must fail. It also proves the module reads ``glossary.ACTIONS`` at
    call time (the filter is the glossary's table, not a copy).
    """
    check_e1(cx.resolve)
    monkeypatch.setattr(gl, "ACTIONS", {**gl.ACTIONS, "wrapper": "Wrapper"})
    with pytest.raises(AssertionError):
        check_e1(cx.resolve)


def test_a_frame_named_like_an_action_on_a_non_handler_is_not_an_op_frame(cx):
    """The filter needs BOTH an LH ``self`` and an ACTIONS ``co_name``. A frame named ``aspirate``
    whose ``self`` is not a LiquidHandler (a fake, the ledger's wrappers) is not an op frame: the
    tracker still resolves by rule (d) and there is no action.
    """
    deck, lh, tips, source, assay = asyncio.run(_world())  # locals: the roots rule (d) can reach
    well = assay.get_item("A1")

    class Fake:
        def aspirate(self, w):
            w.tracker.remove_liquid(999)

    try:
        Fake().aspirate(well)
    except TooLittleLiquidError as exc:
        ctx = cx.resolve(exc)
    else:
        raise AssertionError("expected TLL")
    assert ctx is not None and ctx.owner is well and ctx.rule == "d"
    assert ctx.action is None and ctx.op is None


# --------------------------------------------------------------------------- the *96 short-circuit


def test_e96_is_a_real_96_head_failure_with_a_96_frame():
    r = case("E96-empty")
    names = []
    tb = r.tb
    while tb is not None:
        names.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next
    assert "aspirate96" in names


# --------------------------------------------------------------------------- the 96 path (#5659)
#
# Spec: ``261001_nd-next-5659-96head-errors.md`` N5659-1..4 and AC-96-1..5. The 96 ops resolve on
# their own path: dispatch on the op frames, a locals mapping with a container-mode guard, owners
# against ``lh.head96``, and the committed offending set over the channels that physically hold a tip.


def test_a_96_frame_is_a_real_frame_in_every_96_scenario():
    """Premise: every 96 positive really raised through a ``*96`` op frame (so the dispatch tests
    are about a 96 stack, not a 1-channel one)."""
    for name in POSITIVE_96:
        names = []
        tb = case(name).tb
        while tb is not None:
            names.append(tb.tb_frame.f_code.co_name)
            tb = tb.tb_next
        assert any(n.endswith("96") for n in names), name


def test_a_non_96_op_under_a_96_frame_resolves_to_none(cx):
    """E1's failing op is an ordinary aspirate; a ``*96`` frame ABOVE it still gives ``None`` (N5659-1
    (ii): a mixed stack), while E1 without it resolves. Body unchanged since the D8 short-circuit."""
    r = case("E1_via_96")
    names = []
    tb = r.tb
    while tb is not None:
        names.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next
    assert "aspirate96" in names and "aspirate" in names
    assert cx.resolve(r.exc) is None
    assert cx.resolve(case("E1").exc) is not None  # the same failure without the 96 frame resolves


def test_dispatch96_all_96_frames_resolve_on_the_96_path(cx):
    check_e96_empty(cx.resolve)
    ctx = cx.resolve(case("E96-return").exc)
    assert (ctx.action, ctx.op) == ("return_tips96", "drop_tips96")  # PLR's own nested call (A34)
    assert ctx.head96 is True
    assert cx.resolve(case("E1").exc).head96 is False  # the 1-channel path is unchanged


def test_dispatch96_a_mixed_stack_gives_none_in_both_directions(cx):
    """Innermost 96 under an outer non-96 op frame, and innermost non-96 under a 96 frame (C10)."""
    for name in ("E96-under-1ch", "E1_via_96"):
        names = []
        tb = case(name).tb
        while tb is not None:
            names.append(tb.tb_frame.f_code.co_name)
            tb = tb.tb_next
        assert "aspirate96" in names and "aspirate" in names, name
        assert cx.resolve(case(name).exc) is None, name
    # the order of the two frames differs between them, which is what makes both directions covered
    under, via = _frame_names("E96-under-1ch"), _frame_names("E1_via_96")
    assert under.index("aspirate") < under.index("aspirate96")  # outer non-96, inner 96
    assert via.index("aspirate96") < via.index("aspirate")  # outer 96, inner non-96


def _frame_names(name):
    out, tb = [], case(name).tb
    while tb is not None:
        out.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next
    return out


def test_dispatch96_control_an_innermost_frame_only_dispatcher_resolves_the_mixed_stack(cx, monkeypatch):
    """The innermost-only dispatcher (N5659-1's rejected reading) sends E96-under-1ch down the 96 path:
    the check built to catch that must fail, while the real E96-empty still passes."""
    assert cx._path([_Frame("aspirate"), _Frame("aspirate96")]) is None  # the real dispatcher: mixed

    def innermost_only(op_frames):
        if not op_frames:
            return "1ch"
        return "96" if op_frames[-1].f_code.co_name.endswith("96") else "1ch"

    _mutant(monkeypatch, cx, _path=innermost_only)
    check_e96_empty(cx.resolve)
    with pytest.raises(AssertionError):
        check_e96_under_1ch(cx.resolve)


class _Frame:
    """The two things the dispatcher reads from a frame."""

    def __init__(self, co_name):
        self.f_code = types.SimpleNamespace(co_name=co_name)


def test_dispatch96_control_the_old_any_96_short_circuit_fails_every_96_positive(cx, monkeypatch):
    def short_circuit(op_frames):
        return None if any(f.f_code.co_name.endswith("96") for f in op_frames) else "1ch"

    check_e1(cx.resolve)
    _mutant(monkeypatch, cx, _path=short_circuit)
    check_e1(cx.resolve)
    for name, check in POSITIVE_96.items():
        with pytest.raises(AssertionError):
            check(cx.resolve)


@pytest.mark.parametrize("name", sorted(POSITIVE_96))
def test_dispatch96_each_positive_names_the_96_op_it_failed_in(cx, name):
    ctx = cx.resolve(case(name).exc)
    assert ctx is not None and ctx.head96 is True
    assert ctx.op is not None and ctx.op.endswith("96") and ctx.action.endswith("96")


def test_error_context_new_fields_are_defaulted_and_last(cx):
    """C18: ``head96`` and ``container_mode`` follow ``available``, with defaults, so every existing
    keyword construction (the first-op-resource control below) keeps working."""
    fields = dataclasses.fields(cx.ErrorContext)
    names = [f.name for f in fields]
    assert names[names.index("available") + 1:][:2] == ["head96", "container_mode"]
    for f in fields[names.index("head96"):]:
        assert f.default is not dataclasses.MISSING, f.name
    assert next(f for f in fields if f.name == "head96").default is False
    assert next(f for f in fields if f.name == "container_mode").default is None
    ctx = cx.ErrorContext(
        error="x", action=None, op=None, rule="a", owner_kind=CONTAINER, owner=None, channel=None,
        resources=(), channels=(), volumes=(), offending=(), requested=None, available=None)
    assert ctx.head96 is False and ctx.container_mode is None


# ---- AC-96-2: mapping and guard


def test_map96_the_locals_map_to_one_entry_per_channel(cx):
    for name in ("E96-empty", "E96-single", "E96-onewell-plate"):
        POSITIVE_96[name](cx.resolve)


def test_map96_a_container_that_is_not_per_channel_or_single_gives_none(cx):
    """dispense96's tip loop precedes its count / plate / fit checks (C6), so a tip error can arrive
    with 48 or 384 containers or a container too small for the head: the guard returns ``None``."""
    for name in ("E96-disp48", "E96-disp384", "E96-disp-small"):
        assert type(case(name).exc) is TooLittleLiquidError  # a display class, so the guard is what says None
        NONE_96[name](cx.resolve)


def test_map96_control_a_guard_less_mapping_breaks_on_the_unguarded_cases(cx, monkeypatch):
    """Without the guard the 48-container case indexes past its list and the 384-container case
    returns a context built from the first 96 wells."""
    _mutant(monkeypatch, cx, _container_mode=lambda lh, containers: "per_channel")
    check_e96_empty(cx.resolve)
    with pytest.raises(IndexError):
        check_e96_disp48(cx.resolve)
    with pytest.raises(AssertionError):
        check_e96_disp384(cx.resolve)


def test_map96_the_single_container_mode_needs_the_head_to_fit(cx):
    """A one-container list is single mode only when ``_check_96_head_fits_in_container`` says so."""
    r = case("E96-disp-small")
    assert not r.lh._check_96_head_fits_in_container(r.small)
    assert cx._container_mode(r.lh, [r.small]) is None
    big = case("E96-single")
    assert cx._container_mode(big.lh, [big.container]) == "single"
    assay = case("E96-empty")
    assert cx._container_mode(assay.lh, assay.assay.get_all_items()) == "per_channel"
    assert cx._container_mode(assay.lh, assay.assay.get_all_items()[:48]) is None
    assert cx._container_mode(assay.lh, []) is None


def test_map96_a_per_channel_list_needs_one_parent(cx):
    r = case("E96-empty")
    wells = list(r.assay.get_all_items())
    other = case("E96-rowD").assay.get_all_items()[0]  # a well of a different plate object
    assert cx._container_mode(r.lh, [*wells[:95], other]) is None


# ---- AC-96-3: offending sets


@pytest.mark.parametrize("name", sorted(POSITIVE_96))
def test_offend96_each_positive_matches_its_expected_context(cx, name):
    POSITIVE_96[name](cx.resolve)


def test_offend96_a_first_failure_only_dispenser_fails_the_set_checks(cx, monkeypatch):
    """O1 (rejected): only PLR's first failure. It understates E96-rowD (12 wells) and E96-empty (96),
    and the tip-side twin understates the HasTip sets."""
    real_volume, real_tip = cx._volume_offenders, cx._tip_offenders

    def first_volume(*args, **kwargs):
        found = real_volume(*args, **kwargs)
        return found[:1] if found else found

    def first_tip(*args, **kwargs):
        found = real_tip(*args, **kwargs)
        return found[:1] if found else found

    for name in ("E96-rowD", "E96-empty", "E96-hasTip-pickup", "E96-hasTip-drop"):
        POSITIVE_96[name](cx.resolve)
    _mutant(monkeypatch, cx, _volume_offenders=first_volume, _tip_offenders=first_tip)
    for name in ("E96-rowD", "E96-empty", "E96-hasTip-pickup", "E96-hasTip-drop"):
        with pytest.raises(AssertionError):
            POSITIVE_96[name](cx.resolve)


def test_offend96_a_mask_blind_dispenser_names_channels_that_hold_no_tip(cx, monkeypatch):
    """Control for "the channels the op uses are the ones that physically hold a tip": a reading that
    takes all 96 channels names wells under the four tipless channels of E96-partial."""
    POSITIVE_96["E96-partial"](cx.resolve)
    _mutant(monkeypatch, cx, _positions_with_committed_tip=lambda pairs: [i for i, _ in pairs])
    with pytest.raises(AssertionError):
        POSITIVE_96["E96-partial"](cx.resolve)
    with pytest.raises(AssertionError):
        POSITIVE_96["E96-hasTip-drop-m8"](cx.resolve)
    with pytest.raises(AssertionError):
        POSITIVE_96["E96-hasTip-pickup-s3"](cx.resolve)


def test_offend96_a_resolver_that_always_returns_none_fails_every_96_positive(cx):
    def always_none(exc, tb=None, **kw):
        return None

    for name, check in POSITIVE_96.items():
        with pytest.raises(AssertionError):
            check(always_none)
    for name, check in NONE_96.items():
        check(always_none)


def test_offend96_a_resolver_that_names_the_first_op_resource_fails_every_96_positive(cx):
    resolver = _first_op_resource_resolver(cx, include_96=True)
    for name, check in POSITIVE_96.items():
        with pytest.raises(AssertionError):
            check(resolver)


def _96_snapshot(r):
    lh = r.lh
    heads = []
    for c, t in lh.head96.items():
        try:
            tip = t.get_tip()
            committed, tip_state = True, (tip.tracker.volume, tip.tracker.pending_volume)
        except NoTipError:
            committed, tip_state = False, None
        heads.append((c, t.has_tip, committed, tip_state))
    vols = []
    for res in [r.deck, *r.deck.get_all_children()]:
        tr = getattr(res, "tracker", None)
        if isinstance(tr, VolumeTracker):
            vols.append((res.name, tr.volume, tr.pending_volume))
    spots = []
    for s in r.deck.get_all_children():
        if isinstance(s, TipSpot):
            try:
                tip_spot_tracker(s).get_tip()
                committed = True
            except NoTipError:
                committed = False
            spots.append((s.name, s.tip is not None, committed))
    return heads, vols, spots


def test_offend96_resolve_is_read_only_on_the_96_path(cx):
    """AC-96-3's snapshot: volume, pending volume, committed tip and pending tip of every tracker
    (head, mounted tips, wells, spots) are equal before and after ``resolve``."""
    for name in POSITIVE_96:
        r = case(name)
        before = _96_snapshot(r)
        assert cx.resolve(r.exc, r.exc.__traceback__) is not None
        assert _96_snapshot(r) == before, name


def test_offend96_the_snapshot_would_see_a_change(cx):
    """Control for the snapshot above: a state change between two snapshots is visible."""
    r = case("E96-rowD")
    before = _96_snapshot(r)
    well = r.assay.get_item("A1")
    original = well.tracker.pending_volume
    well.tracker.remove_liquid(1.0)  # pending only
    try:
        assert _96_snapshot(r) != before
    finally:
        well.tracker.pending_volume = original
    assert _96_snapshot(r) == before


# ---- AC-96-4: committed vs pending discriminators


def test_discrim96_r2_the_committed_reading_names_96_channels(cx, monkeypatch):
    check_e96_r2(cx.resolve)

    def has_tip_reader(tracker):
        if tracker.has_tip:
            return object()
        raise NoTipError(f"{tracker.thing} does not have a tip.")

    _mutant(monkeypatch, cx, _committed_tip=has_tip_reader)
    with pytest.raises(AssertionError):  # the pending reading gives 91: channels 0-4 look empty
        check_e96_r2(cx.resolve)
    ctx = cx.resolve(case("E96-R2").exc)
    assert ctx is not None and len(ctx.offending) == 91


def test_discrim96_k_the_committed_demand_names_the_wells_plr_skipped(cx, monkeypatch):
    check_e96_k(cx.resolve)
    def plr_demand(pairs):
        """The channels PLR iterated: a pending tip AND a committed one."""
        return [i for i, tracker in pairs if tracker.has_tip and _committed(tracker)]

    _mutant(monkeypatch, cx, _positions_with_committed_tip=plr_demand)
    with pytest.raises(AssertionError):
        check_e96_k(cx.resolve)
    ctx = cx.resolve(case("E96-K").exc)
    assert ctx is not None and _ids_of(ctx.targets) == ["C2"]  # PLR's own answer: one well


def _committed(tracker):
    try:
        tracker.get_tip()
    except NoTipError:
        return False
    return True


# ---- AC-96-5: None cases


def test_none96_the_new_none_cases_give_none(cx):
    for name, check in NONE_96.items():
        check(cx.resolve)


def test_none96_a_pending_volume_reader_resolves_the_residue_retry(cx, monkeypatch):
    """E96-residue-TLL: every committed volume covers the 50 uL, PLR raises at A1 on residue. A
    reader of pending volume would call A1 short."""
    check_e96_residue_tll(cx.resolve)
    _mutant(monkeypatch, cx, _committed_volume=lambda tracker: tracker.pending_volume)
    with pytest.raises(AssertionError):
        check_e96_residue_tll(cx.resolve)


def test_none96_a_mutant_without_the_notip_clause_and_the_mask_resolves_the_notip_cases(cx, monkeypatch):
    """NoTip on the 96 path always gives ``None`` (A9). Dropping that clause alone is not enough
    (the committed mask excludes the tipless channels); drop the mask too and the drop_tips96 case
    and the TipSpot.get_tip case resolve."""
    for name in ("E96-noTip-residue", "E96-noTip-residue-asp", "E96-noTip-spot"):
        NONE_96[name](cx.resolve)
    _mutant(
        monkeypatch, cx,
        _tip_error_explainable_on_96=lambda exc: True,
        _positions_with_committed_tip=lambda pairs: [i for i, _ in pairs],
    )
    for name in ("E96-noTip-residue", "E96-noTip-spot"):
        with pytest.raises(AssertionError):
            NONE_96[name](cx.resolve)


def test_none96_the_aspirate_notip_is_raised_before_the_locals_it_would_need_exist(cx, monkeypatch):
    """E96-noTip-residue-asp: aspirate96 builds ``tips`` (LH:1981) BEFORE it binds ``containers``
    (:1990-2002), so the frame the NoTip comes from has no ``containers`` to map. That, not only the
    NoTip clause, is why the case is ``None``: it stays ``None`` even with both guards mutated away.
    (Spec A3 says the locals are bound before any tracker call; that holds for the volume sites
    :2016/:2045 and :2163-:2200, not for the tips comprehension.)"""
    frame = next(f for f in _frames_of("E96-noTip-residue-asp") if f.f_code.co_name == "aspirate96")
    assert "volume" in frame.f_locals and "containers" not in frame.f_locals
    _mutant(
        monkeypatch, cx,
        _tip_error_explainable_on_96=lambda exc: True,
        _positions_with_committed_tip=lambda pairs: [i for i, _ in pairs],
    )
    NONE_96["E96-noTip-residue-asp"](cx.resolve)


def _frames_of(name):
    out, tb = [], case(name).tb
    while tb is not None:
        out.append(tb.tb_frame)
        tb = tb.tb_next
    return out


def test_none96_dropping_only_the_notip_clause_is_not_enough(cx, monkeypatch):
    """The mask alone already says None for the L cases: the two guards are independent, and the test
    above is the one that needs both removed."""
    _mutant(monkeypatch, cx, _tip_error_explainable_on_96=lambda exc: True)
    for name in ("E96-noTip-residue", "E96-noTip-residue-asp", "E96-noTip-spot"):
        NONE_96[name](cx.resolve)


def test_none96_runtime_and_toosmall_are_premises_not_controls(cx):
    """Non-display classes: nothing in the module could resolve them, so they prove nothing by passing.
    They are here to show the scenarios raise something else."""
    assert type(case("E96-runtime").exc) is RuntimeError
    assert type(case("E96-tooSmall").exc) is ValueError
    NONE_96["E96-runtime"](cx.resolve)
    NONE_96["E96-tooSmall"](cx.resolve)


# --------------------------------------------------------------------------- owners, by identity


def test_owner_rules_by_identity_a_same_named_impostor_does_not_resolve(cx):
    """Rules (a)-(c) compare objects. The impostor well has the deck well's name and tracker
    ``thing``; a NAME lookup would resolve it to the deck's assay A1.
    """
    r = case("impostor")
    assert r.impostor.name == r.real.name
    assert cx.resolve(r.exc) is None


def test_a_name_based_resolver_is_caught_by_the_impostor_check(cx):
    """Control for the check above: a resolver that resolves by NAME resolves the impostor, so the
    impostor check FAILS it (and it resolves E1 fine: the failure is specific).
    """
    real = cx.resolve

    def by_name(exc, tb=None, **kw):
        tb = tb if tb is not None else exc.__traceback__
        frames = []
        while tb is not None:
            frames.append(tb.tb_frame)
            tb = tb.tb_next
        for f in reversed(frames):
            s = f.f_locals.get("self")
            if isinstance(s, VolumeTracker):
                lh = next(g.f_locals["self"] for g in frames if isinstance(g.f_locals.get("self"), LiquidHandler))
                name = s.thing.removesuffix("_volume_tracker")
                well = lh.deck.get_resource(name)
                return dataclasses.replace(
                    real(case("E1").exc), owner=well) if well is not None else None
        return None

    with pytest.raises(AssertionError):
        check_impostor(by_name)
    check_e1(real)


def test_owner_rules_b_and_d_and_e_are_what_the_cases_exercise(cx):
    """Which rule fired, per case (a: container / spot by tree walk, b: head tracker, c: mounted
    tip, d: parsed ``thing`` with no LH frame, e: the ``channel`` local with no tracker frame).
    """
    got = {name: cx.resolve(case(name).exc).rule for name in (
        "E1", "E5", "E7", "E11", "E6", "E16", "E3", "E12", "E4", "E8", "E8_spot", "E8_channel")}
    assert got == {"E1": "a", "E5": "a", "E7": "a", "E11": "a", "E6": "b", "E16": "b", "E3": "c",
                   "E12": "c", "E4": "e", "E8": "d", "E8_spot": "d", "E8_channel": "d"}


def test_rule_d_needs_a_reachable_deck_and_accepts_an_explicit_one(cx):
    """With no LH frame there is no ``lh.deck``: the name is looked up on the roots that the
    traceback's frames reach, plus any passed in ``decks``. Cut the frame that holds them off and
    nothing resolves; hand the deck in and it does (a control that the lookup is the mechanism).
    """
    r = case("E8")
    assert cx.resolve(r.exc, r.exc.__traceback__.tb_next) is None  # only the tracker frames
    ctx = cx.resolve(r.exc, r.exc.__traceback__.tb_next, decks=[r.deck])
    assert ctx is not None and ctx.owner is r.well and ctx.rule == "d"


def test_rule_d_lookup_that_matches_a_tip_gives_no_owner(cx):
    """C11-15: a name that matches a ``Tip`` (neither container nor spot) gives no owner, whichever
    tracker type carries it; the preconditions are in the scenarios (the tip IS on the deck).
    """
    for name in ("neg_tip_name_volume", "neg_tip_name_tracker"):
        assert cx.resolve(case(name).exc) is None, name


def test_a_mounted_tip_is_an_owner_only_by_rule_c(cx):
    """A resting ``Tip`` in the deck subtree is not an owner under rule (a): its tracker matches no
    container and no spot, and with an LH frame there is no rule (d). E3 (mounted) resolves.
    """
    assert cx.resolve(case("E3").exc).owner_kind == TIP


# --------------------------------------------------------------------------- committed, not pending


def _mutant(monkeypatch, cx, **patches):
    for name, fn in patches.items():
        assert hasattr(cx, name), f"context.py has no {name}: the mutation seam moved"
        monkeypatch.setattr(cx, name, fn)


_DIRECT_RESIDUE = ("residue_direct_tll", "residue_direct_tlv", "over_committed_direct")


def test_a_resolver_that_reads_pending_state_fails_the_direct_residue_cases_but_not_e1(cx, monkeypatch):
    """Control for "committed, not pending". After a failed op PLR's rollback has already reset the
    op's own resources (pending == committed, E13's own assert), so a pending reader cannot be
    caught THERE. It can where no op rolls back: a direct tracker change with no LH frame. Patch the
    committed readers to read pending state: those cases must then FAIL, while E1 (nothing pending)
    still passes.
    """
    for name in (*_DIRECT_RESIDUE, "E1"):
        CHECKS[name](cx.resolve)
    _mutant(monkeypatch, cx, _committed_volume=lambda tracker: tracker.pending_volume)
    check_e1(cx.resolve)
    for name in _DIRECT_RESIDUE:
        with pytest.raises(AssertionError):
            CHECKS[name](cx.resolve)


def test_a_resolver_that_skips_the_committed_offending_set_fails_e13_e15_and_e14(cx, monkeypatch):
    """Control for the pending-residue rule ("owner outside the committed offending set -> None"): a
    resolver that treats every volume request as short, and every tip as conflicting, resolves
    E13, E15 and E14, so their checks FAIL. E1 and E4, which committed state does explain, still
    pass.
    """

    def always_short(tracker, requested, too_little_liquid):
        return cx._committed_volume(tracker) if too_little_liquid else cx._committed_room(tracker)

    _mutant(monkeypatch, cx, _shortfall=always_short, _tip_conflict=lambda exc, has_committed_tip: True)
    check_e1(cx.resolve)
    check_e4(cx.resolve)
    for name in ("E13", "E15", "E14", *_DIRECT_RESIDUE[:2]):
        with pytest.raises(AssertionError):
            CHECKS[name](cx.resolve)


def test_a_resolver_that_uses_has_tip_fails_e14_but_not_e4(cx, monkeypatch):
    """Committed tip state is ``TipTracker.get_tip()`` succeeding, never ``has_tip`` (pending
    included). With ``has_tip`` reading, E14's channel 0 (pending tip) is 'offending' and the case
    resolves, so its check FAILS; E4 (a committed tip) is unaffected.
    """

    def has_tip_reader(tracker):
        if tracker.has_tip:
            return object()
        raise NoTipError(f"{tracker.thing} does not have a tip.")

    _mutant(monkeypatch, cx, _committed_tip=has_tip_reader)
    check_e4(cx.resolve)
    with pytest.raises(AssertionError):
        check_e14(cx.resolve)


def test_the_committed_readers_read_committed_state(cx):
    """The seams themselves, on real trackers: volume is ``volume``, tip is ``get_tip()``."""
    tracker = VolumeTracker(thing="t_volume_tracker", max_volume=360.0)
    tracker.set_volume(100)
    tracker.remove_liquid(10)
    assert (tracker.volume, tracker.pending_volume) == (100, 90)
    assert cx._committed_volume(tracker) == 100
    tt = TipTracker(thing="Channel 0")
    with pytest.raises(NoTipError):
        cx._committed_tip(tt)


# --------------------------------------------------------------------------- controls for the checks


def _first_op_resource_resolver(cx, include_96=False):
    """Always names the first op resource as a container owner, offending everything in the op.
    With ``include_96`` it also reads the 96 ops' ``containers`` / ``tip_rack`` / ``resource``."""
    ops = ("aspirate", "dispense", "pick_up_tips", "drop_tips")
    if include_96:
        ops += tuple(f"{op}96" for op in ops)

    def resolver(exc, tb=None, **kw):
        tb = tb if tb is not None else exc.__traceback__
        last = None
        while tb is not None:
            local = tb.tb_frame.f_locals
            if isinstance(local.get("self"), LiquidHandler) and tb.tb_frame.f_code.co_name in ops:
                last = local
            tb = tb.tb_next
        if last is None:
            return None
        res = list(last.get("resources") or last.get("tip_spots") or [])
        if include_96 and not res:
            res = list(last.get("containers") or [])
            for key in ("tip_rack", "resource"):
                rack = last.get(key)
                if not res and hasattr(rack, "get_all_items"):
                    res = list(rack.get_all_items())
        if not res:
            return None
        return cx.ErrorContext(
            error=type(exc).__name__, action=None, op=None, rule="a", owner_kind=CONTAINER,
            owner=res[0], channel=None, resources=tuple(res), channels=(), volumes=(),
            offending=tuple(cx.Offender(target=x, requested=1.0, available=1.0) for x in res),
            requested=1.0, available=1.0)

    return resolver


NONE_CASES = (
    "E13", "E14", "E15", "E1_via_96", "impostor", "impostor_in_op", "impostor_direct",
    "residue_direct_tll", "residue_direct_tlv", "neg_value_error", "neg_ghost_volume", "neg_ghost_spot", "neg_tip_name_volume",
    "neg_tip_name_tracker", "neg_bare_discard", "neg_bare_return",
    # #5659: the 96 cases that stay None (AC-96-5, AC-96-2's guard, mixed stacks, non-display classes)
    *NONE_96,
)


def test_a_resolver_that_always_returns_none_fails_the_positive_cases(cx):
    def always_none(exc, tb=None, **kw):
        return None

    positives = [n for n in CHECKS if n not in NONE_CASES]
    assert len(positives) >= 20
    for name in positives:
        with pytest.raises(AssertionError):
            CHECKS[name](always_none)
    # ... and it passes exactly the None cases: the checks are not one-sided
    for name in NONE_CASES:
        CHECKS[name](always_none)


def test_a_resolver_that_always_names_the_first_op_resource_fails_the_discriminating_cases(cx):
    resolver = _first_op_resource_resolver(cx)
    for name in ("E10", "E12", "E6", "E4", "E13", "E14", "E15", "E3", "E9", "E16"):
        with pytest.raises(AssertionError):
            CHECKS[name](resolver)


def test_real_resolver_passes_what_the_controls_fail(cx):
    """The other half of the controls: the real module passes every check the mutants fail."""
    for name in ("E10", "E12", "E6", "E4", "E13", "E14", "E15", "E96-empty", "E3", "E9", "E16", "impostor"):
        CHECKS[name](cx.resolve)


# --------------------------------------------------------------------------- summed vs per channel


def test_summed_demand_per_resource_a_per_channel_reading_would_miss_e9_and_e2(cx):
    """E9 (8 x 30 = 240 > 100) and E2_summed (2 x 200 = 400 > 300): each channel's own request
    fits, only the SUM does not. The requested numbers are the sums.
    """
    r9, r2 = case("E9"), case("E2_summed")
    assert cx.resolve(r9.exc).requested == 240.0
    assert cx.resolve(r2.exc).requested == 400.0 and cx.resolve(r2.exc).available == 300.0


def test_a_tip_owner_is_per_channel_not_summed(cx):
    """E3_per_channel and E12_per_channel: the sum over channels would flag every channel; only the
    channel whose own committed tip cannot serve its own request offends.
    """
    assert cx.resolve(case("E3_per_channel").exc).targets == (1,)
    assert cx.resolve(case("E12_per_channel").exc).targets == (1,)


# --------------------------------------------------------------------------- residue, defence


def test_owner_outside_the_committed_offending_set_is_none_for_every_residue_case(cx):
    for name in ("E13", "E14", "E15"):
        assert cx.resolve(case(name).exc) is None, name


def test_no_lh_frame_the_trackers_own_committed_state_decides(cx):
    """With no op frame the tracker that raised is checked against its own committed state:
    residue that a request fits gives ``None``, a request over the committed volume too resolves."""
    for name in _DIRECT_RESIDUE:
        CHECKS[name](cx.resolve)


# --------------------------------------------------------------------------- through a RunLedger


def test_an_error_raised_inside_a_run_ledger_resolves_the_same(cx):
    """B6 resolves errors raised inside ``RunLedger``: the ledger's wrapper frames (instance
    attributes, ``self`` is not a LiquidHandler) must not disturb the op frames.
    """
    ledger = importlib.import_module(f"{_PKG}.ledger")

    async def go():
        deck, lh, tips, source, assay = await _world()
        await lh.pick_up_tips(tips["A1:H1"])
        wells = assay["A1:H1"]
        with ledger.RunLedger(lh, show=False):
            exc = await _catch(lh.aspirate(wells, vols=[80.0] * 8))
        return Raised(exc, deck=deck, lh=lh, wells=wells)

    r = asyncio.run(go())
    ctx = cx.resolve(r.exc)
    assert ctx is not None and ctx.owner is r.wells[0] and ctx.action == "aspirate"
    _same(ctx.targets, r.wells)
    assert (ctx.requested, ctx.available) == (80.0, 0.0)


# --------------------------------------------------------------------------- what context.py may use

_SPOT_HELPERS = {"_container_tracker", "_tip_tracker"}


def scan_forbidden(source: str) -> list[str]:
    """Violations of D8's committed-state and legacy-API rules, found by AST:

    * no ``has_tip`` and no ``empty`` attribute anywhere (``has_tip`` includes pending operations;
      ``TipSpot.has_tip()`` / ``empty()`` are docstring-deprecated);
    * ``.get_tip`` only inside ``_committed_tip`` (a ``TipTracker`` method; ``TipSpot.get_tip`` adds a
      tip when tracking is off);
    * ``.tracker`` only inside ``_container_tracker`` and ``_tip_tracker`` (a container's and a
      tip's own tracker); a tip spot's ``.tracker`` is docstring-deprecated and never read;
    * ``pylabrobot`` imported only inside functions (no PLR import at import time) and only from
      the non-shim homes.
    """
    tree = ast.parse(source)
    problems: list[str] = []

    def visit(node, function):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function = node.name
        if isinstance(node, ast.Attribute):
            if node.attr in ("has_tip", "empty"):
                problems.append(f"line {node.lineno}: .{node.attr}")
            if node.attr == "get_tip" and function != "_committed_tip":
                problems.append(f"line {node.lineno}: .get_tip outside _committed_tip")
            if node.attr == "tracker" and function not in _SPOT_HELPERS:
                problems.append(f"line {node.lineno}: .tracker outside {sorted(_SPOT_HELPERS)}")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for mod in names:
                if mod == "pylabrobot" or mod.startswith("pylabrobot."):
                    if function is None:
                        problems.append(f"line {node.lineno}: module-level import of {mod}")
                    if mod not in ALLOWED_PLR_MODULES:
                        problems.append(f"line {node.lineno}: import of {mod} (not an allowed non-shim home)")
        for child in ast.iter_child_nodes(node):
            visit(child, function)

    visit(tree, None)
    return problems


_CLEAN = textwrap.dedent("""
    def _committed_tip(tracker):
        return tracker.get_tip()

    def _container_tracker(container):
        return container.tracker

    def f():
        from pylabrobot.legacy.tip_tracker import TipTracker
        return TipTracker
""")


def test_scan_control_a_clean_source_is_clean():
    assert scan_forbidden(_CLEAN) == []


@pytest.mark.parametrize(("bad", "needle"), [
    ("def f(spot):\n    return spot.tracker\n", ".tracker"),
    ("def f(spot):\n    return spot.has_tip\n", ".has_tip"),
    ("def f(spot):\n    return spot.has_tip()\n", ".has_tip"),
    ("def f(spot):\n    return spot.get_tip()\n", ".get_tip"),
    ("def f(spot):\n    spot.empty()\n", ".empty"),
    ("import pylabrobot\n", "module-level"),
    ("from pylabrobot.resources import Well\n", "module-level"),
    ("def f():\n    from pylabrobot.resources.tip_tracker import TipTracker\n", "not an allowed"),
    ("def f():\n    from pylabrobot.liquid_handling import LiquidHandler\n", "not an allowed"),
])
def test_scan_control_each_forbidden_form_is_flagged(bad, needle):
    problems = scan_forbidden(bad)
    assert problems and any(needle in p for p in problems), (bad, problems)


def test_context_py_uses_only_committed_readers_and_non_shim_homes():
    if not _CONTEXT_PATH.is_file():
        pytest.fail(f"praxis/display/context.py does not exist yet: {_CONTEXT_PATH}")
    assert scan_forbidden(_CONTEXT_PATH.read_text(encoding="utf-8")) == []


def test_context_py_reads_the_action_table_from_the_glossary_and_does_not_copy_it(cx, gl):
    tree = ast.parse(_CONTEXT_PATH.read_text(encoding="utf-8"))
    imported = {(n.module, a.name) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert ("glossary", "ACTIONS") not in imported  # `from .glossary import ACTIONS` would freeze it
    src = _CONTEXT_PATH.read_text(encoding="utf-8")
    assert "glossary.ACTIONS" in src


class _Tripwire:
    """Record (and pass through) any call of TipSpot's docstring-deprecated legacy API."""

    def __init__(self):
        self.hits: list[str] = []


@contextlib.contextmanager
def _tipspot_tripwire(monkeypatch):
    trip = _Tripwire()
    for attr in ("get_tip", "has_tip", "empty"):
        original = getattr(TipSpot, attr)

        def wrapped(self, *a, _orig=original, _attr=attr, **k):
            trip.hits.append(_attr)
            return _orig(self, *a, **k)

        monkeypatch.setattr(TipSpot, attr, wrapped)
    original_prop = TipSpot.__dict__["tracker"]

    def tracker(self):
        trip.hits.append("tracker")
        return original_prop.fget(self)

    monkeypatch.setattr(TipSpot, "tracker", property(tracker))
    yield trip


def test_the_tripwire_itself_fires(monkeypatch):
    """Control: each legacy accessor, used by a resolver, is recorded."""
    r = case("E5")
    with _tipspot_tripwire(monkeypatch) as trip:
        _ = r.spot.tracker
        r.spot.has_tip()
        r.spot.get_tip()
    assert trip.hits == ["tracker", "has_tip", "get_tip"]


def test_resolve_never_touches_tipspot_legacy_api_at_run_time(cx, monkeypatch):
    names = ("E4", "E4-off", "E5", "E6", "E7", "E11", "E14", "E16", "E8_spot", "E1", "E3")
    cases = [case(n) for n in names]  # built (and PLR's own use of the API done) BEFORE the wire
    with _tipspot_tripwire(monkeypatch) as trip:
        for r in cases:
            r.exc.__traceback__  # noqa: B018
            cx.resolve(r.exc)
    assert trip.hits == []


# --------------------------------------------------------------------------- import behaviour

_ENV_PIN = {"PYTHONPATH": str(Path(pylabrobot.__file__).resolve().parent.parent)}


def _run_py(code):
    import os

    env = {**os.environ, **_ENV_PIN}
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=180,
                          check=False, env=env)


_LOAD = f"""
import sys, types, importlib
pkg = types.ModuleType({_PKG!r}); pkg.__path__ = [{str(_DISPLAY_DIR)!r}]; pkg.__package__ = {_PKG!r}
sys.modules[{_PKG!r}] = pkg
"""


def test_context_imports_in_plain_cpython_with_no_plr_at_import_time():
    if not _CONTEXT_PATH.is_file():
        pytest.fail(f"praxis/display/context.py does not exist yet: {_CONTEXT_PATH}")
    code = _LOAD + f"""
m = importlib.import_module({_PKG!r} + '.context')
bad = [k for k in sys.modules if k.split('.')[0] in ('pylabrobot', 'IPython', 'js')]
assert not bad, bad
print('ok', m.resolve.__name__)
"""
    proc = _run_py(code)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip() == "ok resolve"


def test_resolving_is_quiet_under_warnings_as_errors_and_uses_only_the_pins_homes():
    """The lazy PLR imports run with DeprecationWarning escalated to an error (a shim home
    raises one), and the shim modules are never imported by ``resolve``.
    """
    if not _CONTEXT_PATH.is_file():
        pytest.fail(f"praxis/display/context.py does not exist yet: {_CONTEXT_PATH}")
    code = _LOAD + f"""
import warnings
warnings.simplefilter('error', DeprecationWarning)
m = importlib.import_module({_PKG!r} + '.context')
assert m.resolve(ValueError('x')) is None
for needed in ('pylabrobot.legacy.tip_tracker', 'pylabrobot.resources.volume_tracker',
               'pylabrobot.resources.errors', 'pylabrobot.legacy.liquid_handling'):
    assert needed in sys.modules, needed
for shim in ('pylabrobot.liquid_handling', 'pylabrobot.resources.tip_tracker'):
    assert shim not in sys.modules, shim
print('ok')
"""
    proc = _run_py(code)
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert proc.stdout.strip() == "ok"


# --------------------------------------------------------------------------- the pin's anchors


def _lh_source() -> str:
    return inspect.getsource(sys.modules[LiquidHandler.__module__])


def test_pin_anchors_still_read_as_documented():
    """The PLR sites the resolver depends on, checked by content (line numbers drift): a pin bump
    that moves or rewrites one fails here, next to the comment block that names them.
    """
    lh_src = _lh_source()
    tt_src = inspect.getsource(sys.modules[TipTracker.__module__])
    # LH:758 raises before any tracker is touched: no tracker frame, the loop local `channel`
    assert re.search(r"for channel, op in zip\(use_channels, pickups\):\s+if self\.head\[channel\]\.has_tip:\s+"
                     r'raise HasTipError\("Channel has tip"\)', lh_src)
    # LH:727: the taken-spot NoTip comes from the deprecated TipSpot.get_tip, before the queue loop
    assert "tips = [tip_spot.get_tip() for tip_spot in tip_spots]" in lh_src
    # head-side NoTip sites (LH:880, :1200, :1405) and the head tracker `thing` (LH:418)
    assert lh_src.count("self.head[channel].get_tip()") >= 3
    assert 'TipTracker(thing=f"Channel {c}")' in lh_src
    # tip_tracker.py:118/:166 and :153
    assert tt_src.count('raise NoTipError(f"{self.thing} does not have a tip.")') == 2
    assert 'raise HasTipError(f"{self.thing} already has a tip.")' in tt_src
    # the aspirate/dispense queue loops are INSIDE the try (no residue after a failed op)
    for op in ("aspirate", "dispense"):
        body = lh_src[lh_src.index(f"  async def {op}(") :]
        body = body[: body.index("\n  async def ", 10)]
        assert re.search(r"error: Optional\[Exception\] = None\s+try:\s+for op in ", body), op
