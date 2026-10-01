"""Browserless tests for ``praxis/display/errors.py`` (task B6, backlog #5642): the error panel and the
exception handler. Closes AC-16 and AC-13's error-panel case.

Spec: ``260929_notebook-display-epic.md`` D8 ("Handler", "Panel drawing: committed volume, not pending",
"What PLR's message omits", "Tracking"), D2 (the bundle and the error stamp by owner), D4 (the capped,
escaped traceback), D9 (``ledger.step_for``), section 3.3 (the error-panel templates), AC-16 (the panel),
AC-17 (handler semantics; the fake shell here is B6's half of it, B8 owns ``install.py``), AC-28 (no
glossary literal outside ``glossary.py``), and the sprint notes (S3: ``set_custom_exc`` is NOT the carrier,
the S3-C fallback is: wrap the shell INSTANCE's ``showtraceback``).

**Real PLR at the 1.0.0b1 pin.** Every panel is built from the REAL error raised by the real
``LiquidHandler`` (non-shim home ``pylabrobot.legacy.liquid_handling``) and the chatterbox backend on the
fixture's ``assemble()`` deck, with B5's setups (E1, E2, E3, E4, E5, E6, E7, E9, E10, E11, E12, E13, E15,
E16 and the negatives; the 96-head setups E96-* since #5659). The venv's editable PLR can be the old 0.2.2, so the first fixture asserts
the version; run with ``PYTHONPATH=<PLR 1.0.0b1 source>`` prepended. ``test_every_scenario_raises_the_class_it_claims``
checks the setups WITHOUT the module under test, so a setup that stops raising fails on its own and never
lets a panel test pass vacuously.

**The wrapper is tested against a FAKE shell** (IPython is not in the project venv). ``FakeShell`` models
what S3 MEASURED in the Pyodide kernel (run a3458bf2, outcome s3_combined; IPython 9.12.0 and
``pyodide_kernel-0.8.2``, as ``test_s3_spike_driver.py`` modelled them):

* ``run_code`` catches the cell's exception and calls ``self.showtraceback(running_compiled_code=True)``,
  looked up on the INSTANCE (so an instance attribute wins), in a plain cell and in a top-level-``await`` cell;
* the default ``showtraceback`` ends in ``self._showtraceback(etype, evalue, stb)``, which sets
  ``_last_traceback``, and the kernel derives the cell's status from ``_last_traceback``: a cell with it
  set gets an ``error`` output and Run All stops;
* ``set_custom_exc`` is recorded and never used by the handler (its handler runs but its return value
  does not become the error output: S3-C).

**Controls (nothing here passes vacuously).** The checks are plain functions of the module under test. A
handler that swallows the error output (never reaches ``_showtraceback``), one that always shows the
generic panel, one that draws PENDING volume, and one that does not cap the traceback are each run through
the check built to catch them and must FAIL it, while the good module passes. Positive controls: the
backend spy sees a real aspirate and a real dispense (so "no call on E1" is not a dead spy); the traceback
of an ordinary error is not capped.

**Import discipline** (ADR 260817 Sec 2.4). ``praxis/display`` is loaded by path under the synthetic package
``_praxis_display_under_test``; ``web-repl/overlay/assets/python`` is never put on ``sys.path``.
``errors.py`` must import in plain CPython with NO PLR, IPython or ``js`` at import time.
"""

from __future__ import annotations

import ast
import asyncio
import dataclasses
import importlib
import importlib.util
import inspect
import json
import os
import re
import subprocess
import sys
import traceback
import types
from html.parser import HTMLParser
from pathlib import Path

import pylabrobot
import pytest
from pylabrobot.legacy.liquid_handling import LiquidHandler
from pylabrobot.legacy.tip_tracker import tip_spot_tracker
from pylabrobot.resources import (
    Container,
    Coordinate,
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
    hamilton_plate_carrier_L5_ac,
)

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL = _TESTS_DIR.parent
_DISPLAY_DIR = _WEB_REPL / "overlay" / "assets" / "python" / "praxis" / "display"
_ERRORS_PATH = _DISPLAY_DIR / "errors.py"
_FIXTURE_PATH = _WEB_REPL / "design" / "notebook-display" / "make_fixture.py"
_PKG = "_praxis_display_under_test"

CAP = 65_536
TB_CAP = 16_384
SESSION, EXEC = "S1-test", 7

ALLOWED_PLR_MODULES = {
    "pylabrobot.legacy.liquid_handling",
    "pylabrobot.legacy.tip_tracker",
    "pylabrobot.resources",
    "pylabrobot.resources.errors",
    "pylabrobot.resources.volume_tracker",
}

HOSTILE = [
    '<b>&"\'x',
    "</svg><script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "</details></div><script>alert(1)</script><style>*{display:none}</style>",
    "&amp;&lt;b&gt;",
]


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
def _restore_state():
    """Tracking is a PLR global and ``configure`` / ``_ERROR_STEPS`` are module state: no test may
    leak into the next (the suite runs in random order)."""
    tip, vol = does_tip_tracking(), does_volume_tracking()
    yield
    set_tip_tracking(tip)
    set_volume_tracking(vol)
    module = sys.modules.get(f"{_PKG}.ledger")
    if module is not None:
        module.configure()
        module._ERROR_STEPS.clear()


@pytest.fixture(scope="module")
def errors():
    """praxis/display/errors.py. A missing module is the RED reason."""
    if not _ERRORS_PATH.is_file():
        pytest.fail(f"praxis/display/errors.py does not exist yet: {_ERRORS_PATH}")
    _package()
    return importlib.import_module(f"{_PKG}.errors")


def _sibling(name):
    _package()
    return importlib.import_module(f"{_PKG}.{name}")


@pytest.fixture(scope="module")
def gl():
    return _sibling("glossary")


@pytest.fixture(scope="module")
def lw():
    return _sibling("labware")


@pytest.fixture(scope="module")
def led():
    return _sibling("ledger")


@pytest.fixture(scope="module")
def svg():
    return _sibling("svg")


@pytest.fixture(scope="module")
def bud():
    return _sibling("budget")


@pytest.fixture(scope="module")
def ctxmod():
    return _sibling("context")


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


# --------------------------------------------------------------------------- scenarios (B5's setups)


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


def _spy_backend(lh):
    """Record every backend ``aspirate`` / ``dispense`` call on the chatterbox backend (D8 "Panel
    drawing": the tracker refusal is raised before the backend is reached)."""
    calls: list[str] = []
    for op in ("aspirate", "dispense", "aspirate96", "dispense96"):
        original = getattr(lh.backend, op)

        def spy(*args, _op=op, _original=original, **kwargs):
            calls.append(_op)
            return _original(*args, **kwargs)

        setattr(lh.backend, op, spy)
    lh.backend_calls = calls


async def _world():
    """The fixture's deck (tips_300 on the tip carrier, source and assay plates), tracking on, with
    the backend spied."""
    deck, lh = await _fx().assemble()
    _spy_backend(lh)
    return deck, lh, deck.get_resource("tips_300"), deck.get_resource("source"), deck.get_resource("assay")


def _add_trough(deck, name="trough"):
    carrier = Trough_CAR_5R60_A00(name=f"{name}_carrier")
    carrier[0] = trough = hamilton_1_trough_60mL_Vb(name=name)
    deck.assign_child_resource(carrier, track=16)
    return trough


async def _catch(coro, lh=None):
    """Await ``coro``, which must raise; when ``lh`` is given remember the backend calls made
    before and after it (``lh.calls_at_failure = (before, after)``)."""
    before = len(lh.backend_calls) if lh is not None else None
    try:
        await coro
    except Exception as e:
        if lh is not None:
            lh.calls_at_failure = (before, len(lh.backend_calls))
        return e
    raise AssertionError("the op was expected to raise and did not")


async def _e1_setup():
    """The fixture's error cell setup: assay A1:H1 committed at 50 uL (via a real aspirate and a real
    dispense, which the backend spy records)."""
    deck, lh, tips, source, assay = await _world()
    await lh.pick_up_tips(tips["A1:H1"])
    await lh.aspirate(source["A1:H1"], vols=[50.0] * 8)
    await lh.dispense(assay["A1:H1"], vols=[50.0] * 8)
    wells = assay["A1:H1"]
    assert [w.tracker.volume for w in wells] == [50.0] * 8
    assert lh.backend_calls == ["aspirate", "dispense"]  # positive control: the spy is live
    return deck, lh, tips, source, assay, wells


@scenario("E1", TooLittleLiquidError)
async def _e1():
    """The fixture's error cell: 80 uL from assay A1:H1, which holds 50."""
    deck, lh, tips, source, assay, wells = await _e1_setup()
    exc = await _catch(lh.aspirate(wells, vols=[80.0] * 8), lh)
    return Raised(exc, deck=deck, lh=lh, wells=wells, assay=assay, tips=tips)


@scenario("E1_h12", TooLittleLiquidError)
async def _e1_h12():
    """E1 with residue on H12, a well of the owner plate OUTSIDE the op (AC-16, C11-2): committed 100,
    pending 60 by direct tracker use. The op's own rollback cannot erase it."""
    deck, lh, tips, source, assay, wells = await _e1_setup()
    h12 = assay.get_item("H12")
    h12.tracker.set_volume(100)
    h12.tracker.remove_liquid(40)  # direct, NOT committed
    exc = await _catch(lh.aspirate(wells, vols=[80.0] * 8), lh)
    return Raised(exc, deck=deck, lh=lh, wells=wells, assay=assay, h12=h12)


@scenario("E1_ledger", TooLittleLiquidError)
async def _e1_ledger():
    """E1 inside a real ``RunLedger`` (show off here; the flow tests below show it on)."""
    led = _sibling("ledger")
    deck, lh, tips, source, assay = await _world()
    try:
        with led.RunLedger(lh, show=False) as run:
            await lh.pick_up_tips(tips["A1:H1"])
            await lh.aspirate(source["A1:H1"], vols=[50.0] * 8)
            await lh.dispense(assay["A1:H1"], vols=[50.0] * 8)
            await lh.aspirate(assay["A1:H1"], vols=[80.0] * 8)
    except TooLittleLiquidError as exc:
        return Raised(exc, deck=deck, lh=lh, run=run)
    raise AssertionError("expected TLL")


@scenario("E2", TooLittleVolumeError)
async def _e2():
    """A tip holding 400 uL (preset), dispensed into a 360 uL well: TLV, owner the well."""
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips([tips.get_item("A1")])
    lh.head[0].get_tip().tracker.set_volume(400)  # set_volume does not validate max_volume
    well = assay.get_item("A2")
    assert well.max_volume == 360 and well.tracker.volume == 0
    exc = await _catch(lh.dispense([well], vols=[400.0], use_channels=[0]), lh)
    return Raised(exc, deck=deck, lh=lh, well=well, assay=assay)


@scenario("E2_summed", TooLittleVolumeError)
async def _e2_summed():
    """Two channels dispense 200 uL each into ONE trough whose tracker holds at most 300."""
    deck, lh, tips, _source, _assay = await _world()
    trough = _add_trough(deck)
    trough.tracker.max_volume = 300.0
    await lh.pick_up_tips(tips["A1:B1"])
    for c in (0, 1):
        lh.head[c].get_tip().tracker.set_volume(200)
    exc = await _catch(lh.dispense([trough, trough], vols=[200.0, 200.0], use_channels=[0, 1]), lh)
    return Raised(exc, deck=deck, lh=lh, trough=trough)


@scenario("E3", TooLittleVolumeError)
async def _e3():
    """400 uL into a tip whose max_volume is 360, from a well preset to 500."""
    deck, lh, tips, source, _assay = await _world()
    src = source.get_item("A1")
    src.tracker.set_volume(500)
    await lh.pick_up_tips([tips.get_item("A1")])
    tip = lh.head[0].get_tip()
    assert tip.tracker.max_volume == 360
    exc = await _catch(lh.aspirate([src], vols=[400.0], use_channels=[0]), lh)
    return Raised(exc, deck=deck, lh=lh, tip=tip, src=src)


@scenario("E4", HasTipError)
async def _e4():
    """Pick up with tips already on: the loop local ``channel`` (rule (e), no tracker frame)."""
    deck, lh, tips, _source, _assay = await _world()
    await lh.pick_up_tips(tips["A1:H1"])
    exc = await _catch(lh.pick_up_tips(tips["A2:H2"]))
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
    """Aspirate with no tip mounted."""
    deck, lh, _tips, source, _assay = await _world()
    exc = await _catch(lh.aspirate([source.get_item("A1")], vols=[50.0], use_channels=[0]), lh)
    return Raised(exc, deck=deck, lh=lh)


@scenario("E7", NoTipError)
async def _e7():
    """Pick up from a spot whose tip is already on channel 0."""
    deck, lh, tips, _source, _assay = await _world()
    spot = tips.get_item("A1")
    await lh.pick_up_tips([spot])
    exc = await _catch(lh.pick_up_tips([spot], use_channels=[1]))
    return Raised(exc, deck=deck, lh=lh, tips=tips, spot=spot)


@scenario("E8", TooLittleLiquidError)
async def _e8():
    """A tracker used directly, outside any LH: rule (d) resolves the well, but there is no op."""
    deck, lh, tips, source, assay = await _world()
    well = assay.get_item("A1")
    try:
        well.tracker.remove_liquid(999)
    except TooLittleLiquidError as exc:
        return Raised(exc, deck=deck, lh=lh, well=well)
    raise AssertionError("remove_liquid(999) was expected to raise")


@scenario("E9", TooLittleLiquidError)
async def _e9():
    """Eight channels, 30 uL each, from ONE trough holding 100 committed: 240 > 100."""
    deck, lh, tips, _source, _assay = await _world()
    trough = _add_trough(deck)
    trough.tracker.set_volume(100)
    await lh.pick_up_tips(tips["A1:H1"])
    exc = await _catch(lh.aspirate([trough] * 8, vols=[30.0] * 8, use_channels=list(range(8))), lh)
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
    exc = await _catch(lh.aspirate(wells, vols=[80.0] * 8), lh)
    return Raised(exc, deck=deck, lh=lh, wells=wells, assay=assay)


@scenario("E11", HasTipError)
async def _e11():
    """``return_tips`` onto an occupied spot."""
    deck, lh, tips, _source, _assay = await _world()
    a1 = tips.get_item("A1")
    await lh.pick_up_tips([a1])
    await lh.pick_up_tips([tips.get_item("A2")], use_channels=[1])
    await lh.drop_tips([a1], use_channels=[1])
    assert lh.head[0].get_tip_origin() is a1 and a1.tip is not None
    exc = await _catch(lh.return_tips(use_channels=[0]))
    return Raised(exc, deck=deck, lh=lh, spot=a1, tips=tips)


@scenario("E12", TooLittleLiquidError)
async def _e12():
    """Dispense 100 uL from an empty tip: TLL, owner the tip on channel 0."""
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips([tips.get_item("A1")])
    assert lh.head[0].get_tip().tracker.volume == 0
    exc = await _catch(lh.dispense([assay.get_item("A1")], vols=[100.0], use_channels=[0]), lh)
    return Raised(exc, deck=deck, lh=lh)


@scenario("E13", TooLittleLiquidError)
async def _e13():
    """Residue from direct tracker use (committed 100, pending 90): 95 <= 100 yet PLR raises."""
    deck, lh, tips, _source, _assay = await _world()
    trough = _add_trough(deck)
    await lh.pick_up_tips([tips.get_item("A1")])
    trough.tracker.set_volume(100)
    trough.tracker.remove_liquid(10.0)  # direct, NOT committed
    assert (trough.tracker.volume, trough.tracker.pending_volume) == (100, 90)
    exc = await _catch(lh.aspirate([trough], vols=[95.0], use_channels=[0]), lh)
    assert str(exc) == "Not enough liquid in container: 95.0uL > 90.0uL."
    assert trough.tracker.volume >= 95.0
    return Raised(exc, deck=deck, lh=lh, trough=trough)


@scenario("E96-empty", TooLittleLiquidError)
async def _e96_empty():
    """A real 96-head failure: pick up the whole rack, aspirate 50 uL from an empty assay plate.
    (This was ``E-96``; #5659 gives the 96 head its own panel rows.)"""
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96(assay, volume=50.0), lh)
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


# ---- #5659: the 96-head scenarios behind AC-96-6/-7/-9/-11 (recipes as in test_display_context.py)


def _bare_container(deck, name, *, max_volume=20000.0):
    container = Container(name=name, size_x=120.0, size_y=80.0, size_z=40.0, max_volume=max_volume)
    deck.assign_child_resource(container, location=Coordinate(500.0, 100.0, 0))
    return container


def _one_well_plate(deck, name="trough_plate"):
    plate = agenbio_1_troughplate_100mL_Fl(name=name)
    deck.get_resource("plate_carrier")[2] = plate
    return plate


def _set_tip_volumes(lh, volume):
    for tracker in lh.head96.values():
        tracker.get_tip().tracker.set_volume(volume)


def _give_spot_a_committed_tip(tips, i):
    spot = tips.get_item(i)
    tip_spot_tracker(spot).add_tip(spot.make_tip())  # commit=True
    return spot


@scenario("E96-single", TooLittleLiquidError)
async def _e96_single():
    deck, lh, tips, _source, _assay = await _world()
    container = _bare_container(deck, "big")
    container.tracker.set_volume(2000)
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96(container, volume=30.0), lh)
    return Raised(exc, deck=deck, lh=lh, container=container)


@scenario("E96-onewell-plate", TooLittleLiquidError)
async def _e96_onewell_plate():
    deck, lh, tips, _source, _assay = await _world()
    plate = _one_well_plate(deck)
    plate.get_item(0).tracker.set_volume(1000)
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96(plate, volume=30.0), lh)
    return Raised(exc, deck=deck, lh=lh, plate=plate)


@scenario("E96-rowD", TooLittleLiquidError)
async def _e96_rowd():
    """B: assay wells 80 uL except row D at 10. Wells A1-C1 carry queued (pending 30) residue when D1 raises."""
    deck, lh, tips, _source, assay = await _world()
    for well in assay.get_all_items():
        well.tracker.set_volume(80)
    for well in assay["D1:D12"]:
        well.tracker.set_volume(10)
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96(assay, volume=50.0), lh)
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-partial", TooLittleLiquidError)
async def _e96_partial():
    deck, lh, tips, _source, assay = await _world()
    for i in (0, 1, 2, 50):
        tip_spot_tracker(tips.get_item(i)).remove_tip(commit=True)
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96(assay, volume=50.0), lh)
    return Raised(exc, deck=deck, lh=lh, tips=tips, assay=assay)


@scenario("E96-shared", TooLittleLiquidError)
async def _e96_shared():
    """A list of 96 wells in which A1 appears twice (channels 0 and 1) and B1 not at all: A1 holds
    60 uL and is asked for 2 x 50, so the demand is summed per well."""
    deck, lh, tips, _source, assay = await _world()
    wells = assay.get_all_items()
    for well in wells:
        well.tracker.set_volume(80)
    wells[0].tracker.set_volume(60)
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96([wells[0], wells[0], *wells[2:]], volume=50.0), lh)
    return Raised(exc, deck=deck, lh=lh, assay=assay)


@scenario("E96-tipTLV", TooLittleVolumeError)
async def _e96_tip_tlv():
    deck, lh, tips, source, _assay = await _world()
    for well in source.get_all_items():
        well.tracker.max_volume = 5000
        well.tracker.set_volume(1000)
    await lh.pick_up_tips96(tips)
    await lh.aspirate96(source, volume=200.0)
    exc = await _catch(lh.aspirate96(source, volume=200.0), lh)
    return Raised(exc, deck=deck, lh=lh)


@scenario("E96-tipTLL", TooLittleLiquidError)
async def _e96_tip_tll():
    deck, lh, tips, source, assay = await _world()
    await lh.pick_up_tips96(tips)
    await lh.aspirate96(source, volume=30.0)
    exc = await _catch(lh.dispense96(assay, volume=50.0), lh)
    return Raised(exc, deck=deck, lh=lh)


@scenario("E96-tipTLL-D2", TooLittleLiquidError)
async def _e96_tip_tll_d2():
    deck, lh, tips, source, assay = await _world()
    await lh.pick_up_tips96(tips)
    await lh.aspirate96(source, volume=30.0)
    for c in (7, 9):
        lh.head96[c].get_tip().tracker.set_volume(20)
    exc = await _catch(lh.dispense96(assay, volume=25.0), lh)
    return Raised(exc, deck=deck, lh=lh)


@scenario("E96-dispTLV", TooLittleVolumeError)
async def _e96_disp_tlv():
    deck, lh, tips, _source, assay = await _world()
    for i, well in enumerate(assay.get_all_items()):
        well.tracker.set_volume(330 if i in (10, 11, 40) else 160)
    await lh.pick_up_tips96(tips)
    _set_tip_volumes(lh, 100)
    exc = await _catch(lh.dispense96(assay, volume=100.0), lh)
    return Raised(exc, deck=deck, lh=lh, assay=assay)


@scenario("E96-hasTip-pickup", HasTipError)
async def _e96_has_tip_pickup():
    deck, lh, tips, _source, _assay = await _world()
    for c in (3, 50):
        lh.head96[c].add_tip(tips.get_item(c).make_tip())  # committed
    exc = await _catch(lh.pick_up_tips96(tips))
    return Raised(exc, deck=deck, lh=lh, tips=tips)


async def _h():
    """H: the whole rack picked up, committed tips put back in spots 5 (F1) and 77 (F10)."""
    deck, lh, tips, source, assay = await _world()
    await lh.pick_up_tips96(tips)
    for i in (5, 77):
        _give_spot_a_committed_tip(tips, i)
    return deck, lh, tips, source, assay


@scenario("E96-hasTip-drop", HasTipError)
async def _e96_has_tip_drop():
    """Channels 0-4 are queued (pending tips on spots 0-4) before spot 5 raises: 7 pending, 2 committed."""
    deck, lh, tips, _source, _assay = await _h()
    exc = await _catch(lh.drop_tips96(tips))
    return Raised(exc, deck=deck, lh=lh, tips=tips)


@scenario("E96-return", HasTipError)
async def _e96_return():
    deck, lh, tips, _source, _assay = await _world()
    await lh.pick_up_tips96(tips)
    _give_spot_a_committed_tip(tips, 5)
    exc = await _catch(lh.return_tips96())
    return Raised(exc, deck=deck, lh=lh, tips=tips)


@scenario("E96-noTip-residue", NoTipError)
async def _e96_notip_residue():
    deck, lh, tips, _source, _assay = await _world()
    for c in (3, 50):
        lh.head96[c].add_tip(tips.get_item(c).make_tip())
    assert isinstance(await _catch(lh.pick_up_tips96(tips)), HasTipError)
    exc = await _catch(lh.drop_tips96(tips))
    return Raised(exc, deck=deck, lh=lh, tips=tips)


@scenario("E96-residue-TLL", TooLittleLiquidError)
async def _e96_residue_tll():
    deck, lh, tips, _source, assay = await _world()
    for well in assay.get_all_items():
        well.tracker.set_volume(80)
    for well in assay["D1:D12"]:
        well.tracker.set_volume(10)
    await lh.pick_up_tips96(tips)
    assert isinstance(await _catch(lh.aspirate96(assay, volume=50.0)), TooLittleLiquidError)
    for well in assay["D1:D12"]:
        well.tracker.set_volume(80)
    exc = await _catch(lh.aspirate96(assay, volume=50.0), lh)
    return Raised(exc, deck=deck, lh=lh, assay=assay)


@scenario("E96-N", TooLittleVolumeError)
async def _e96_n():
    deck, lh, tips, _source, _assay = await _world()
    container = _bare_container(deck, "tub", max_volume=3000.0)
    container.tracker.set_volume(1000)
    await lh.pick_up_tips96(tips)
    _set_tip_volumes(lh, 30)
    exc = await _catch(lh.dispense96(container, volume=30.0), lh)
    return Raised(exc, deck=deck, lh=lh, container=container)


@scenario("E96-onewell-TLV", TooLittleVolumeError)
async def _e96_onewell_tlv():
    deck, lh, tips, _source, _assay = await _world()
    plate = _one_well_plate(deck)
    plate.get_item(0).tracker.set_volume(98000)
    await lh.pick_up_tips96(tips)
    _set_tip_volumes(lh, 30)
    exc = await _catch(lh.dispense96(plate, volume=30.0), lh)
    return Raised(exc, deck=deck, lh=lh, plate=plate)


@scenario("E96_ledger", TooLittleLiquidError)
async def _e96_ledger():
    """The 96 failure inside a real ``RunLedger``: step 2 (pick up, then the failing aspirate)."""
    led = _sibling("ledger")
    deck, lh, tips, _source, assay = await _world()
    try:
        with led.RunLedger(lh, show=False) as run:
            await lh.pick_up_tips96(tips)
            await lh.aspirate96(assay, volume=50.0)
    except TooLittleLiquidError as exc:
        return Raised(exc, deck=deck, lh=lh, run=run)
    raise AssertionError("expected TLL")


@scenario("P1", HasTipError)
async def _p1():
    """A31: after E14's residue, a 1-channel drop of channel 3 onto the occupied tips_300 A1. The
    rack's PENDING view holds 92 tips, its committed view 95."""
    deck, lh, tips, _source, _assay = await _world()
    await lh.pick_up_tips(tips["D1:D1"], use_channels=[3])
    assert isinstance(await _catch(lh.pick_up_tips(tips["A2:H2"])), HasTipError)  # channels 0-2 queue first
    exc = await _catch(lh.drop_tips(tips["A1:A1"], use_channels=[3]))
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
    exc = await _catch(lh.aspirate([well], vols=[200.0], use_channels=[0]), lh)
    return Raised(exc, deck=deck, lh=lh, tip=tip, well=well)


@scenario("E16", NoTipError)
async def _e16():
    """``discard_tips(use_channels=[0])`` with no tip mounted."""
    deck, lh, _tips, _source, _assay = await _world()
    exc = await _catch(lh.discard_tips(use_channels=[0]))
    assert str(exc) == "Channel 0 does not have a tip."
    return Raised(exc, deck=deck, lh=lh)


@scenario("hostile_plate", TooLittleLiquidError)
async def _hostile_plate():
    """A plate whose NAME is hostile markup (a name is fixed at creation), aspirated from while empty."""
    deck, lh, tips, _source, _assay = await _world()
    carrier = hamilton_plate_carrier_L5_ac(name="hostile_carrier")
    carrier[0] = plate = cor_96_wellplate_360uL_Fb(name=HOSTILE[1])
    deck.assign_child_resource(carrier, track=16)
    await lh.pick_up_tips(tips["A1:H1"])
    exc = await _catch(lh.aspirate(plate["A1:H1"], vols=[80.0] * 8), lh)
    return Raised(exc, deck=deck, lh=lh, plate=plate)


@scenario("neg_value_error", ValueError)
async def _neg_value_error():
    deck, lh, tips, source, _assay = await _world()
    await lh.pick_up_tips([tips.get_item("A1")])
    exc = await _catch(lh.aspirate([source.get_item("A1")], vols=[50.0, 60.0], use_channels=[0]))
    return Raised(exc, deck=deck, lh=lh)


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
    """The setups themselves, without the module under test (AC-15 preamble)."""
    r = case(name)
    assert type(r.exc) is EXPECTED_CLASS[name], (name, type(r.exc), str(r.exc))
    assert r.exc.__traceback__ is not None


# --------------------------------------------------------------------------- HTML helpers


class _Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.children: list = []

    def walk(self):
        yield self
        for c in self.children:
            if isinstance(c, _Node):
                yield from c.walk()

    def find_all(self, tag=None, cls=None):
        out = []
        for n in self.walk():
            if tag is not None and n.tag != tag:
                continue
            if cls is not None and cls not in (n.attrs.get("class") or "").split():
                continue
            out.append(n)
        return out

    def text(self) -> str:
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = _Node(tag, dict(attrs), self.cur)
        self.cur.children.append(n)
        self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(_Node(tag, dict(attrs), self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def _parse(doc: str) -> _Node:
    b = _TreeBuilder()
    b.feed(doc)
    b.close()
    return b.root


def _one(root, cls, tag=None):
    hits = root.find_all(tag, cls)
    assert len(hits) == 1, f"expected exactly one .{cls}, found {len(hits)}"
    return hits[0]


def _text_of(root, cls):
    return _one(root, cls).text()


def _render(errors, name_or_r, **kw):
    r = case(name_or_r) if isinstance(name_or_r, str) else name_or_r
    kw.setdefault("session", SESSION)
    kw.setdefault("exec_count", EXEC)
    data, meta = errors.render(r.exc, r.tb, **kw)
    return data, meta, _parse(data["text/html"])


def _paths(root):
    out: dict[str, list[str]] = {}
    for p in root.find_all("path"):
        out.setdefault(p.attrs.get("class", ""), []).append(p.attrs["d"])
    return out


def _subpaths(d):
    return [s for s in re.split(r"(?=M)", d) if s]


def _grid(root):
    groups = [n for n in root.walk() if n.tag == "g" and "data-praxis-grid" in n.attrs]
    assert len(groups) == 1
    return json.loads(groups[0].attrs["data-praxis-grid"])


def _fault_ids(root):
    g = _grid(root)
    return {i for i, f in zip(g["ids"].split(), g["flags"], strict=True) if int(f) & 2}


_NUM = r"-?(?:\d+\.?\d*|\.\d+)"


def _circle_radius(sp):
    m = re.match(rf"M({_NUM})[ ,]?({_NUM})a({_NUM})[ ,]?({_NUM}) 0 1 0", sp)
    assert m, sp
    return float(m.group(3))


def _summaries(root):
    """The body and fix sentences: ``p.praxis-summary`` in document order (A4's theme has no rule for
    dedicated ``praxis-error__body`` / ``__fix`` classes, and the CSS gate refuses classes with no rule)."""
    return [n for n in root.find_all("p", "praxis-summary")]


def _part(root, which):
    """``body`` or ``fix`` text; ``step`` is the ``p.praxis-omitted`` that starts "Step "."""
    if which == "step":
        hits = [n.text() for n in root.find_all("p", "praxis-omitted") if n.text().startswith("Step ")]
        assert len(hits) == 1, hits
        return hits[0]
    ps = _summaries(root)
    assert len(ps) == 2, f"expected a body and a fix, found {len(ps)}"
    return ps[{"body": 0, "fix": 1}[which]].text()


def _has_step(root):
    return any(n.text().startswith("Step ") for n in root.find_all("p", "praxis-omitted"))


def _details_text(root):
    return _one(root, "praxis-details-body", "pre").text()


def _without_plr_and_traceback(root):
    """The text of the panel with the verbatim PLR line and the traceback removed."""
    parts = []
    for cls in ("praxis-omitted", "praxis-error__title", "praxis-summary"):
        parts += [n.text() for n in root.find_all(None, cls)]
    return "\n".join(parts)


# --------------------------------------------------------------------------- AC-16: the templates (section 3.3)

# (case, heading, body, fix, resource in the stamp, drawn?, fault ids)
# Transcribed from section 3.3 independently of the module (the oracle).
TEMPLATES = [
    (
        "E1",
        "Not enough liquid in assay A1:H1.",
        "Each well holds 50 µL; the aspirate asked for 80 µL. Nothing was aspirated.",
        "Lower `vols` to 50 µL or less, or aspirate from wells that hold more.",
        "assay", True, {f"{r}1" for r in "ABCDEFGH"},
    ),
    (
        "E2",
        "Not enough room in assay A2.",
        "Each well has room for 360 µL; the dispense asked for 400 µL. Nothing was dispensed.",
        "Lower `vols`, or dispense into emptier wells.",
        "assay", True, {"A2"},
    ),
    (
        "E3",
        "The tip on channel 0 can't hold 400 µL.",
        "It has room for 360 µL. Nothing was aspirated.",
        "Aspirate less, or use larger tips.",
        None, False, set(),
    ),
    (
        "E4",
        "Channel 0 already holds a tip.",
        "Pick up asked channel 0 for another.",
        "Drop or discard the tip first.",
        None, False, set(),
    ),
    (
        "E5",
        "tips_300 A2 already has a tip.",
        "Drop tips asked to put a tip there.",
        "Drop the tip into an empty position.",
        "tips_300", True, {"A2"},
    ),
    (
        "E6",
        "Channel 0 has no tip.",
        "Aspirate needs a tip on every channel it uses.",
        "Pick up tips before you aspirate.",
        None, False, set(),
    ),
    (
        "E7",
        "tips_300 A1 has no tip.",
        "Pick up asked for a tip that has already been taken.",
        "Pick up from a position that still has a tip.",
        "tips_300", True, {"A1"},
    ),
    (
        "E9",
        "Not enough liquid in trough.",
        "It holds 100 µL; the aspirate asked for 240 µL across 8 channels. Nothing was aspirated.",
        "Lower `vols`, or aspirate from a container that holds more.",
        "trough", False, set(),
    ),
    (
        "E10",
        "Not enough liquid in assay A1:D1.",
        "Each well holds 50 µL; the aspirate asked for 80 µL. Nothing was aspirated.",
        "Lower `vols` to 50 µL or less, or aspirate from wells that hold more.",
        "assay", True, {f"{r}1" for r in "ABCD"},
    ),
    (
        "E11",
        "tips_300 A1 already has a tip.",
        "Return tips asked to put a tip there.",
        "Drop the tip into an empty position.",
        "tips_300", True, {"A1"},
    ),
    (
        "E12",
        "The tip on channel 0 holds only 0 µL.",
        "The dispense asked for 100 µL. Nothing was dispensed.",
        "Dispense 0 µL or less, or aspirate more first.",
        None, False, set(),
    ),
    (
        "E16",
        "Channel 0 has no tip.",
        "Discard tips needs a tip on every channel it uses.",
        "Pick up tips before you discard tips.",
        None, False, set(),
    ),
]


@pytest.mark.parametrize("row", TEMPLATES, ids=[t[0] for t in TEMPLATES])
def test_each_template_row(errors, svg, row):
    name, heading, body, fix, resource, drawn, fault = row
    data, meta, root = _render(errors, name)
    assert _text_of(root, "praxis-error__title") == heading
    assert _part(root, "body") == body
    assert _part(root, "fix") == fix
    # the stamp by owner (D2): the drawn labware, else null; rev is always null
    assert meta == {"praxis": {"v": 1, "kind": "error", "resource": resource, "rev": None,
                               "session": SESSION, "exec": EXEC}}
    svg.check_bundle(data, meta)
    # a drawing only for a Well or tip-spot owner; a channel, a tip or a non-Well container gets none
    assert bool(root.find_all("svg")) is drawn
    if drawn:
        assert _fault_ids(root) == fault
    # text/plain carries the heading and the body (and PLR's line)
    plain = data["text/plain"]
    assert heading in plain and body in plain
    assert f"PyLabRobot raised {type(case(name).exc).__name__}: {case(name).exc}" in plain


def test_e1_states_the_fixtures_error_cell_in_the_spec_words(errors):
    """Section 3.3's closing paragraph: 80 uL from assay A1:H1, which holds 50."""
    data, _meta, root = _render(errors, "E1")
    assert _text_of(root, "praxis-error__title") == "Not enough liquid in assay A1:H1."
    assert "Each well holds 50 µL; the aspirate asked for 80 µL." in _part(root, "body")
    assert "Nothing was aspirated." in _part(root, "body")


def test_the_fault_wells_carry_a_brick_ring_and_a_cross(errors):
    """AC-16 / D3: a fault is never colour alone (a ring path AND a cross path, one subpath per well)."""
    _data, _meta, root = _render(errors, "E1")
    p = _paths(root)
    assert len(p["sv-fault"]) == 1 and len(_subpaths(p["sv-fault"][0])) == 8
    assert len(p["sv-fault-x"]) == 1 and len(_subpaths(p["sv-fault-x"][0])) == 16  # two strokes per well
    for cls in ("sv-fault", "sv-fault-x"):
        (node,) = [n for n in root.find_all("path", cls)]
        assert node.attrs["stroke"] == "#B3402A"  # brick


def test_e10_marks_exactly_the_offending_wells(errors):
    _d, _m, root = _render(errors, "E10")
    assert _fault_ids(root) == {"A1", "B1", "C1", "D1"}
    assert len(_subpaths(_paths(root)["sv-fault"][0])) == 4
    assert len(_subpaths(_paths(root)["sv-fault-x"][0])) == 8


def test_a_tip_owner_and_a_channel_owner_have_a_null_resource_and_no_drawing(errors):
    for name in ("E3", "E4", "E6", "E12", "E16"):
        _data, meta, root = _render(errors, name)
        assert meta["praxis"]["resource"] is None, name
        assert not root.find_all("svg"), name


def test_a_tip_rack_owner_is_stamped_with_the_racks_name(errors):
    for name in ("E5", "E7", "E11"):
        _data, meta, _root = _render(errors, name)
        assert meta["praxis"]["resource"] == "tips_300", name


def test_a_well_owner_is_stamped_with_the_plate_and_a_trough_with_its_own_name(errors):
    assert _render(errors, "E1")[1]["praxis"]["resource"] == "assay"
    assert _render(errors, "E9")[1]["praxis"]["resource"] == "trough"


def test_the_panel_has_a_rail_a_heading_and_a_traceback_inside_details(errors):
    _d, _m, root = _render(errors, "E1")
    outer = root.find_all("div", "praxis-error")
    assert len(outer) == 1 and "praxis-out" in outer[0].attrs["class"].split()
    details = root.find_all("details")
    assert len(details) == 1
    assert _one(details[0], "praxis-details-summary", "summary").text() == "Show traceback"
    assert details[0].find_all("pre")


def test_body_numbers_are_committed_and_summed_no_plr_number_outside_its_line(errors):
    """E9: PLR's message mixes in pending state ("30.0uL > 10.0uL"); the body says 100 and 240."""
    r = case("E9")
    plr_numbers = set(re.findall(r"\d+(?:\.\d+)?", str(r.exc)))
    body_numbers = set(re.findall(r"\d+", "It holds 100 µL; the aspirate asked for 240 µL across 8 channels."))
    foreign = {n for n in plr_numbers if n.split(".")[0] not in body_numbers}
    assert foreign, f"the control needs a PLR number the body does not use: {plr_numbers}"
    _d, _m, root = _render(errors, "E9")
    outside = _without_plr_and_traceback(root)
    for n in foreign:
        assert re.search(rf"(?<![\d.]){re.escape(n)}(?![\d.])", outside) is None, (n, outside)
    plr_line = _text_of(root, "praxis-error__plr")
    assert plr_line == f"PyLabRobot raised TooLittleLiquidError: {r.exc}"


def test_the_plr_line_is_verbatim_str_of_the_exception(errors):
    for name in ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E10", "E11", "E12", "E16"):
        r = case(name)
        _d, _m, root = _render(errors, name)
        assert _text_of(root, "praxis-error__plr") == f"PyLabRobot raised {type(r.exc).__name__}: {r.exc}", name


def test_the_traceback_is_format_exception_inside_details(errors):
    r = case("E1")
    _d, _m, root = _render(errors, "E1")
    assert _details_text(root) == "".join(traceback.format_exception(type(r.exc), r.exc, r.tb))


# --------------------------------------------------------------------------- AC-16: committed volume on H12


def _check_h12_committed(errors):
    """The AC-16 drawing check as a function of a module (so the pending-volume mutant can be run
    through it). Returns nothing; raises AssertionError."""
    r = case("E1_h12")
    h12 = r.h12
    # precondition, at render time (after the failed op, before the panel is built)
    assert h12.tracker.volume == 100
    assert h12.tracker.get_used_volume() == 60
    data, _meta = errors.render(r.exc, r.tb, session=SESSION, exec_count=EXEC)
    root = _parse(data["text/html"])
    radius_well = h12.get_size_x() / 2
    liquid = _subpaths(_paths(root)["sv-liquid"][0])
    assert len(liquid) == 9  # A1:H1 at 50 and H12 at 100
    drawn = _circle_radius(liquid[-1])  # H12 is last in column-major order
    committed = radius_well * (100 / h12.max_volume) ** 0.5
    pending = radius_well * (60 / h12.max_volume) ** 0.5
    assert abs(drawn - committed) <= 1e-3, (drawn, committed)
    assert abs(drawn - pending) > 0.1, (drawn, pending)
    grid = _grid(root)
    assert grid["vals"][grid["ids"].split().index("H12")] == 100


def test_ac16_the_drawing_uses_committed_volume_on_a_well_outside_the_op(errors):
    _check_h12_committed(errors)


def test_the_h12_case_keeps_e1s_exact_heading_and_body(errors):
    """H12 is outside the op and outside the offending set, so E1's strings are unchanged."""
    _d, _m, root = _render(errors, "E1_h12")
    assert _text_of(root, "praxis-error__title") == "Not enough liquid in assay A1:H1."
    assert _part(root, "body").startswith("Each well holds 50 µL; the aspirate asked for 80 µL.")
    assert _fault_ids(root) == {f"{r}1" for r in "ABCDEFGH"}


def test_rendering_a_panel_changes_no_tracker_state(errors):
    r = case("E1_h12")
    before = (r.h12.tracker.volume, r.h12.tracker.pending_volume,
              [(w.tracker.volume, w.tracker.pending_volume) for w in r.wells])
    _render(errors, r)
    after = (r.h12.tracker.volume, r.h12.tracker.pending_volume,
             [(w.tracker.volume, w.tracker.pending_volume) for w in r.wells])
    assert before == after == (100, 60, [(50.0, 50.0)] * 8)


def test_control_a_panel_that_draws_pending_volume_fails_the_h12_check(errors, monkeypatch):
    _check_h12_committed(errors)  # the good module passes
    monkeypatch.setattr(errors, "_drawn_volume", lambda container: container.tracker.get_used_volume())
    with pytest.raises(AssertionError):
        _check_h12_committed(errors)


# --------------------------------------------------------------------------- D8 "Panel drawing": the backend spy


@pytest.mark.parametrize("name", ["E1", "E2", "E3", "E12", "E9", "E10"])
def test_nothing_was_aspirated_or_dispensed_the_backend_was_not_reached(errors, name):
    """A tracker refusal is raised before the backend is called (LH:1269-1274, :1470-1475): the spy
    records no aspirate or dispense call during the failing op (a confirmatory assert of the ordering,
    D8), and the panel says so."""
    r = case(name)
    before, after = r.lh.calls_at_failure
    assert after == before, (name, r.lh.backend_calls)
    _d, _m, root = _render(errors, name)
    body = _part(root, "body")
    assert ("Nothing was aspirated." in body) or ("Nothing was dispensed." in body)


def test_a_no_tip_aspirate_never_reaches_the_backend_either():
    """E6 (NoTip on aspirate): the head tracker refuses before the backend too, but its template makes no
    "Nothing was aspirated" claim (section 3.3), so only the spy is asserted."""
    r = case("E6")
    before, after = r.lh.calls_at_failure
    assert after == before


def test_the_spy_is_live_e1_setup_made_one_real_aspirate_and_one_real_dispense():
    """Positive control for the spy: a spy that never records would make the assert above vacuous."""
    r = case("E1")
    assert r.lh.backend_calls == ["aspirate", "dispense"]
    assert r.lh.calls_at_failure == (2, 2)


def test_the_source_order_behind_the_claim_tracker_queue_before_the_backend_call():
    """Read from the pin's source, by content: in both ops the tracker loop runs inside the ``try``
    and before ``self.backend.aspirate`` / ``self.backend.dispense``."""
    src = inspect.getsource(sys.modules[LiquidHandler.__module__])
    for op, tracker_call in (("aspirate", "remove_liquid"), ("dispense", "add_liquid")):
        body = src[src.index(f"  async def {op}(") :]
        body = body[: body.index("\n  async def ", 10)]
        try_at = body.index("try:")
        tracker_at = body.index(tracker_call, try_at)
        backend_at = body.index(f"await self.backend.{op}(", try_at)
        assert try_at < tracker_at < backend_at, op


# --------------------------------------------------------------------------- the generic panel


GENERIC_CASES = ["E13", "E15", "E8", "E2_summed", "E96-noTip-residue", "E96-residue-TLL", "E96-N", "E96-onewell-TLV"]


@pytest.mark.parametrize("name", GENERIC_CASES)
def test_a_context_that_is_none_gets_the_generic_panel(errors, ctxmod, svg, name):
    r = case(name)
    if name in ("E13", "E15", "E96-noTip-residue", "E96-residue-TLL"):
        assert ctxmod.resolve(r.exc, r.tb) is None  # the AC-15 premise
    if name in ("E96-N", "E96-onewell-TLV"):  # a context, but no template row (errors.py: TLV on a single container)
        ctx = ctxmod.resolve(r.exc, r.tb)
        assert ctx is not None and ctx.head96 and ctx.container_mode == "single"
    data, meta, root = _render(errors, name)
    sentence = f"PyLabRobot raised {type(r.exc).__name__}: {r.exc}"
    assert _text_of(root, "praxis-error__title") == sentence  # the heading IS PLR's sentence
    assert data["text/plain"].startswith(sentence)
    assert not _summaries(root)  # no body, no fix
    assert not root.find_all("svg")
    assert _details_text(root) == "".join(traceback.format_exception(type(r.exc), r.exc, r.tb))
    assert meta["praxis"] == {"v": 1, "kind": "error", "resource": None, "rev": None,
                              "session": SESSION, "exec": EXEC}
    svg.check_bundle(data, meta)


def test_a_resolver_that_raises_degrades_to_the_generic_panel_and_never_raises(errors, svg):
    def boom(exc, tb=None, **kw):
        raise RuntimeError("resolver blew up")

    r = case("E1")
    data, meta = errors.render(r.exc, r.tb, session=SESSION, exec_count=EXEC, resolver=boom)
    root = _parse(data["text/html"])
    assert _text_of(root, "praxis-error__title") == f"PyLabRobot raised TooLittleLiquidError: {r.exc}"
    assert meta["praxis"]["resource"] is None
    svg.check_bundle(data, meta)


def test_a_context_no_template_can_build_degrades_to_the_generic_panel(errors, ctxmod):
    """A real ``ErrorContext`` whose offending set names no well of the plate: the template raises, the panel is generic."""
    import dataclasses

    r = case("E1")
    good = ctxmod.resolve(r.exc, r.tb)
    assert good is not None
    broken = dataclasses.replace(good, offending=(object(),))  # min() of no wells raises
    data, meta = errors.render(r.exc, r.tb, session=SESSION, exec_count=EXEC, resolver=lambda *a, **k: broken)
    assert data["text/plain"].startswith("PyLabRobot raised TooLittleLiquidError")
    assert meta["praxis"]["resource"] is None


def test_a_missing_session_is_stamped_unset_not_refused(errors):
    r = case("E1")
    _d, meta = errors.render(r.exc, r.tb)
    assert meta["praxis"]["session"] == "unset" and meta["praxis"]["exec"] is None
    _d, meta = errors.render(r.exc, r.tb, session=lambda: 1 / 0, exec_count=lambda: -3)
    assert meta["praxis"]["session"] == "unset" and meta["praxis"]["exec"] is None


def test_a_resolver_that_returns_garbage_degrades_to_the_generic_panel(errors):
    r = case("E1")
    data, meta = errors.render(r.exc, r.tb, session=SESSION, exec_count=EXEC, resolver=lambda *a, **k: object())
    assert meta["praxis"]["resource"] is None
    assert data["text/plain"].startswith("PyLabRobot raised TooLittleLiquidError")


def test_control_a_handler_that_always_shows_the_generic_panel_fails_the_template_check(errors, ctxmod, monkeypatch):
    def check_e1(errors):
        _d, _m, root = _render(errors, "E1")
        assert _text_of(root, "praxis-error__title") == "Not enough liquid in assay A1:H1."

    check_e1(errors)  # the good module passes
    monkeypatch.setattr(ctxmod, "resolve", lambda *a, **k: None)
    with pytest.raises(AssertionError):
        check_e1(errors)


def test_the_generic_panel_of_e13_and_e15_carries_no_committed_number(errors):
    """The residue cases must not invent numbers: no body, no fix, no drawing (D8 step 4)."""
    for name in ("E13", "E15"):
        _d, _m, root = _render(errors, name)
        assert not _summaries(root) and not root.find_all("svg")


# --------------------------------------------------------------------------- the step line (D9)


def test_the_step_line_names_the_step_when_one_is_given(errors):
    _d, _m, root = _render(errors, "E1", step=4)
    assert _part(root, "step") == "Step 4 of the run."


def test_no_step_line_without_a_step(errors):
    _d, _m, root = _render(errors, "E1")
    assert not _has_step(root)


def test_the_step_line_comes_first_in_the_text_and_in_the_panel(errors):
    data, _m, root = _render(errors, "E1", step=2)
    assert data["text/plain"].startswith("Step 2 of the run.")
    order = [n.attrs["class"] for n in root.walk()
             if n.attrs.get("class") == "praxis-error__title"
             or (n.attrs.get("class") == "praxis-omitted" and n.text().startswith("Step "))]
    assert order == ["praxis-omitted", "praxis-error__title"]


def test_the_generic_panel_also_names_the_step(errors):
    _d, _m, root = _render(errors, "E13", step=3)
    assert _part(root, "step") == "Step 3 of the run."


def test_handle_reads_the_step_from_the_ledger_once_and_the_entry_is_gone(errors, led):
    r = asyncio.run(SCENARIOS["E1_ledger"]())  # fresh: the autouse fixture clears _ERROR_STEPS per test
    step = r.run.rows[-1].step
    assert step == 4  # pick up, aspirate, dispense, the failing aspirate
    assert led._ERROR_STEPS[id(r.exc)] == (r.exc, 4)
    shown = []
    stb = errors.handle(r.exc, r.tb, session=SESSION, exec_count=EXEC,
                        display=lambda *a, **k: shown.append((a, k)))
    assert stb == [f"TooLittleLiquidError: {r.exc}"]
    assert id(r.exc) not in led._ERROR_STEPS
    (args, kwargs), = shown
    assert "Step 4 of the run." in args[0]["text/plain"]
    assert kwargs.get("raw") is True and kwargs["metadata"]["praxis"]["kind"] == "error"


# --------------------------------------------------------------------------- escaping and the cap (D2, D4)


def _hostile_exc(cls, message, cell_name="cell"):
    try:
        raise cls(message)
    except cls as e:
        return e


@pytest.mark.parametrize("payload", HOSTILE)
def test_hostile_exception_messages_are_escaped_everywhere(errors, svg, payload):
    for exc in (_hostile_exc(TooLittleLiquidError, payload), _hostile_exc(HasTipError, payload)):
        data, meta = errors.render(exc, exc.__traceback__, session=SESSION, exec_count=EXEC)
        svg.check_bundle(data, meta)  # no <script>/<style>/handlers/links
        doc = data["text/html"]
        for needle in ("<script", "<style", "<img", "<b>"):
            assert needle not in doc, (payload, needle)
        assert "&lt;" in doc or "&amp;" in doc or "&quot;" in doc or "&#x27;" in doc
        root = _parse(doc)
        # a resolver-less exception is the generic panel: PLR's sentence is its heading
        assert _text_of(root, "praxis-error__title") == f"PyLabRobot raised {type(exc).__name__}: {payload}"
        assert payload in _details_text(root)  # the text survives, only as text


def test_a_frame_containing_markup_appears_escaped_in_the_traceback(errors):
    """AC-16: a frame containing ``<b>`` appears as ``&lt;b&gt;``."""
    try:
        raise HasTipError("<b>frame</b>")  # this source line is part of the traceback text
    except HasTipError as exc:
        data, _meta = errors.render(exc, exc.__traceback__, session=SESSION, exec_count=EXEC)
    doc = data["text/html"]
    assert "&lt;b&gt;" in doc and "<b>" not in doc
    assert "raise HasTipError(&quot;&lt;b&gt;frame&lt;/b&gt;&quot;)" in doc


def test_a_hostile_resource_name_is_escaped_in_the_heading_and_the_drawing(errors, svg):
    r = case("hostile_plate")
    data, meta, root = _render(errors, "hostile_plate")
    doc = data["text/html"]
    svg.check_bundle(data, meta)
    assert "<script" not in doc and "</svg><script" not in doc
    assert _text_of(root, "praxis-error__title") == f"Not enough liquid in {HOSTILE[1]} A1:H1."
    assert meta["praxis"]["resource"] == HOSTILE[1]  # the stamp is JSON, unescaped
    assert r.plate.name == HOSTILE[1]


def test_the_traceback_has_no_ansi_escape(errors):
    exc = _hostile_exc(TooLittleLiquidError, "\x1b[31mred\x1b[0m and \x1b]0;title\x07 done")
    data, _m = errors.render(exc, exc.__traceback__, session=SESSION, exec_count=EXEC)
    assert "\x1b" not in data["text/html"] and "\x1b" not in data["text/plain"]
    assert "red" in _details_text(_parse(data["text/html"]))


def _long_exc(n_lines):
    message = "\n".join(f"detail line {i:05d} " + "x" * 40 for i in range(n_lines))
    return _hostile_exc(HasTipError, message)


def _check_traceback_cap(errors, bud):
    exc = _long_exc(4000)  # ~240 KB of traceback text
    full = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    assert len(full.encode()) > 10 * TB_CAP
    data, _meta = errors.render(exc, exc.__traceback__, session=SESSION, exec_count=EXEC)
    body = _details_text(_parse(data["text/html"]))
    assert len(body.encode()) <= TB_CAP
    first, newline, tail = body.partition("\n")
    assert newline and tail, "a capped traceback keeps its tail under the marker line"
    match = re.fullmatch(r"… (\d+) earlier lines omitted", first)
    assert match, first
    assert full.endswith(tail)  # the TAIL is kept, whole lines
    assert "detail line 03999" in body and "detail line 00000" not in body
    dropped = len(full[:-1].split("\n")) - len(tail[:-1].split("\n"))
    assert int(match.group(1)) == dropped
    assert len(data["text/html"].encode()) <= CAP


def test_a_huge_traceback_is_tail_capped_with_the_marker(errors, bud):
    _check_traceback_cap(errors, bud)


def test_the_cap_marker_matches_the_budget_modules_wording(errors, bud):
    exc = _long_exc(4000)
    data, _m = errors.render(exc, exc.__traceback__, session=SESSION, exec_count=EXEC)
    first = _details_text(_parse(data["text/html"])).split("\n")[0]
    n = int(re.fullmatch(r"… (\d+) earlier lines omitted", first).group(1))
    assert first == bud.TAIL_MARKER_FORMAT.format(n=n)


def test_an_ordinary_traceback_is_not_capped(errors):
    """Control for the cap: a short traceback is shown whole, with no marker."""
    r = case("E1")
    _d, _m, root = _render(errors, "E1")
    assert "earlier lines omitted" not in _details_text(root)
    assert _details_text(root).endswith(f"TooLittleLiquidError: {r.exc}\n")


def test_control_a_handler_that_does_not_cap_the_traceback_fails_the_cap_check(errors, bud, monkeypatch):
    _check_traceback_cap(errors, bud)  # the good module passes
    monkeypatch.setattr(bud, "cap_tail", lambda text, *a, **k: text)
    with pytest.raises(AssertionError):
        _check_traceback_cap(errors, bud)


@pytest.mark.parametrize("quote", ['"', "<", "&", "'"])
def test_the_whole_panel_stays_under_64_kib_whatever_the_escaping_expands_to(errors, svg, quote):
    """AC-13's error-panel case: 16 KiB of characters that each escape to 4-6 bytes would be 96 KiB
    if the traceback were capped before escaping only. The cap is never exceeded."""
    exc = _hostile_exc(HasTipError, "\n".join(quote * 100 for _ in range(400)))
    data, meta = errors.render(exc, exc.__traceback__, session=SESSION, exec_count=EXEC)
    assert len(data["text/html"].encode("utf-8")) <= CAP
    svg.check_bundle(data, meta)
    assert "Show traceback" in data["text/html"]  # text is never dropped to save a drawing
    body = _details_text(_parse(data["text/html"]))
    assert body.count(quote) > 1000  # the traceback SHRANK to fit; it was not dropped


def test_a_long_resource_name_and_message_still_fit_the_cap(errors, svg):
    exc = _hostile_exc(TooLittleLiquidError, "y" * 500_000)
    data, meta = errors.render(exc, exc.__traceback__, session=SESSION, exec_count=EXEC)
    assert len(data["text/html"].encode("utf-8")) <= CAP
    svg.check_bundle(data, meta)


def test_the_drawing_degrades_before_the_text_when_the_panel_is_over_the_cap(errors, bud, monkeypatch):
    """D4 ladder: level 1 blocks, then level 2 omits the drawing with the sentence; the text stays."""
    seen = []
    def fat(resource, *, level=0, **kw):
        seen.append(level)
        return "<div>" + "z" * (CAP if level < 2 else 0) + "</div>"

    monkeypatch.setattr(errors.labware, "render_figure", fat)
    data, meta = errors.render(case("E1").exc, case("E1").tb, session=SESSION, exec_count=EXEC)
    assert seen[:2] == [0, 1]  # the drawing degrades level by level
    assert len(data["text/html"].encode()) <= CAP
    assert bud.OMISSION_SENTENCE in data["text/html"]
    root = _parse(data["text/html"])
    assert _text_of(root, "praxis-error__title") == "Not enough liquid in assay A1:H1."


# --------------------------------------------------------------------------- the wrapper (S3-C fallback)


class FakeShell:
    """The parts of IPython 9.12's ``InteractiveShell`` and pyodide-kernel's ``Interpreter`` the S3
    probe MEASURED (see the module docstring). ``default_calls`` are the exceptions that reached the
    ORIGINAL ``showtraceback`` body."""

    def __init__(self):
        self.execution_count = 1
        self.custom_exc_calls: list = []
        self.default_calls: list = []
        self.displayed: list = []
        self._last_traceback = None
        self.showtraceback_calls = 0

    def set_custom_exc(self, exc_tuple, handler):
        self.custom_exc_calls.append((exc_tuple, handler))

    def showtraceback(self, exc_tuple=None, filename=None, tb_offset=None, exception_only=False,
                      running_compiled_code=False):
        etype, value, _tb = exc_tuple or sys.exc_info()
        self.default_calls.append(value)
        if etype is None:  # IPython: "No traceback available to show."
            return
        stb = [f"---- Traceback (most recent call last) ----\n{etype.__name__}: {value}"]
        self._showtraceback(etype, value, stb)

    def _showtraceback(self, etype, evalue, stb):
        # pyodide_kernel.interpreter.Interpreter._showtraceback
        self._last_traceback = {"ename": etype.__name__, "evalue": str(evalue), "traceback": stb}

    # --- what run_code does (IPython 9.12 core/interactiveshell.py run_code) ---------------------
    def _run_plain(self, cell):
        self._last_traceback = None
        try:
            cell()
        except BaseException:
            self.showtraceback(running_compiled_code=True)  # looked up on the instance
        return self._finish_cell()

    async def _run_await(self, cell):
        self._last_traceback = None
        try:
            await cell()
        except BaseException:
            self.showtraceback(running_compiled_code=True)
        return self._finish_cell()

    def _finish_cell(self):
        # the kernel derives the run status from _last_traceback: an error output, and Run All stops
        out = {"panels": list(self.displayed), "error": self._last_traceback}
        self.displayed.clear()
        self.execution_count += 1
        return out

    def run(self, cell, mode):
        if mode == "plain":
            return self._run_plain(cell)
        return asyncio.run(self._run_await(cell))

    def run_all(self, cells, mode="await"):
        """Run cells in order, stopping at the first that leaves an error output (Run All)."""
        ran = []
        for cell in cells:
            out = self.run(cell, mode)
            ran.append(out)
            if out["error"] is not None:
                break
        return ran


class Recorder:
    """A ``display`` that records its calls into the shell, in order."""

    def __init__(self, shell=None):
        self.calls: list = []
        self.shell = shell

    def __call__(self, obj, *args, raw=False, metadata=None, **kwargs):
        entry = {"obj": obj, "raw": raw, "metadata": metadata}
        self.calls.append(entry)
        if self.shell is not None:
            self.shell.displayed.append(entry)


def _raiser(exc, mode):
    if mode == "plain":
        def cell():
            raise exc
    else:
        async def cell():
            await asyncio.sleep(0)
            raise exc
    return cell


def _ok_cell(mode):
    if mode == "plain":
        return lambda: None

    async def cell():
        await asyncio.sleep(0)

    return cell


def _installed(errors, **kw):
    shell = FakeShell()
    rec = Recorder(shell)
    handle = errors.install(shell, session=SESSION, exec_count=lambda: shell.execution_count,
                            display=rec, **kw)
    return shell, rec, handle


MODES = ["plain", "await"]


def _check_wrapper_semantics(errors):
    """The handled classes emit the panel AND still yield an error output that stops Run All; other
    exceptions delegate untouched. A plain function of a module (the swallowing mutant runs through it)."""
    for mode in MODES:
        shell, rec, _h = _installed(errors)
        r = case("E1")
        first, second, third = _raiser(r.exc, mode), _ok_cell(mode), _ok_cell(mode)
        ran = shell.run_all([_ok_cell(mode), first, second, third], mode)
        assert len(rec.calls) == 1, (mode, len(rec.calls))
        assert len(ran) == 2, (mode, "Run All must stop at the failing cell")
        err = ran[1]["error"]
        assert err is not None, (mode, "the cell must still end in an error output")
        assert err["ename"] == "TooLittleLiquidError"
        assert err["traceback"] == [f"TooLittleLiquidError: {r.exc}"]
        assert shell.default_calls == []


def test_handled_classes_emit_the_panel_and_still_stop_run_all(errors):
    _check_wrapper_semantics(errors)


def test_control_a_handler_that_swallows_the_error_output_fails_the_wrapper_check(errors, monkeypatch):
    _check_wrapper_semantics(errors)  # the good module passes
    monkeypatch.setattr(errors, "_finish", lambda *a, **k: True)  # claims done, never reaches _showtraceback
    with pytest.raises(AssertionError):
        _check_wrapper_semantics(errors)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name,klass", [("E1", TooLittleLiquidError), ("E2", TooLittleVolumeError),
                                        ("E4", HasTipError), ("E6", NoTipError)])
def test_each_of_the_four_classes_is_handled_in_both_modes(errors, mode, name, klass):
    shell, rec, _h = _installed(errors)
    r = case(name)
    assert type(r.exc) is klass
    out = shell.run(_raiser(r.exc, mode), mode)
    assert [c["raw"] for c in rec.calls] == [True]
    data, meta = rec.calls[0]["obj"], rec.calls[0]["metadata"]
    assert set(data) == {"text/html", "text/plain"}
    assert meta["praxis"]["kind"] == "error"
    assert out["error"]["traceback"] == [f"{klass.__name__}: {r.exc}"]
    assert shell.default_calls == []


def test_plain_and_await_cells_behave_identically(errors):
    outs = {}
    for mode in MODES:
        shell, rec, _h = _installed(errors)
        r = case("E1")
        out = shell.run(_raiser(r.exc, mode), mode)
        outs[mode] = (
            [c["obj"]["text/plain"] for c in rec.calls],
            [c["metadata"]["praxis"] for c in rec.calls],
            out["error"],
        )
    plain, awaited = outs["plain"], outs["await"]
    assert plain[0] == awaited[0]
    assert {k: v for k, v in plain[1][0].items() if k != "exec"} == {k: v for k, v in awaited[1][0].items() if k != "exec"}
    assert plain[2] == awaited[2]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", ["neg_value_error", "neg_bare_discard", "neg_bare_return"])
def test_other_exceptions_delegate_untouched_and_reach_the_default_traceback(errors, mode, name):
    """Negative control: an unregistered class (a ValueError, and the RuntimeErrors of a bare
    discard_tips() / return_tips(), AC-15's negatives) gets no panel and the DEFAULT traceback."""
    shell, rec, _h = _installed(errors)
    r = case(name)
    out = shell.run(_raiser(r.exc, mode), mode)
    assert rec.calls == []
    assert shell.default_calls == [r.exc]
    assert out["error"]["traceback"][0].startswith("---- Traceback (most recent call last)")


def test_delegation_passes_every_argument_through_unchanged(errors):
    shell = FakeShell()
    captured = []
    shell.showtraceback = lambda *a, **k: captured.append((a, k))  # someone else's instance attribute
    rec = Recorder(shell)
    errors.install(shell, session=SESSION, exec_count=1, display=rec)
    err = ValueError("plain")
    shell.showtraceback((ValueError, err, None), "file.py", 3, True, running_compiled_code=True)
    assert captured == [(((ValueError, err, None), "file.py", 3, True), {"running_compiled_code": True})]
    assert rec.calls == []


def test_a_handled_class_passed_through_exc_tuple_is_handled(errors):
    """``showtraceback(exc_tuple=...)`` (as ``%tb`` and IPython's own callers pass it), not only the
    ``sys.exc_info()`` path of ``run_code``: the probe's ``exc_tuple`` handling."""
    shell, rec, _h = _installed(errors)
    r = case("E1")
    shell.showtraceback(exc_tuple=(type(r.exc), r.exc, r.tb))
    assert len(rec.calls) == 1 and shell.default_calls == []
    assert shell._last_traceback["traceback"] == [f"TooLittleLiquidError: {r.exc}"]
    shell2, rec2, _h2 = _installed(errors)
    shell2.showtraceback((type(r.exc), r.exc, r.tb))  # positional, too
    assert len(rec2.calls) == 1 and shell2.default_calls == []


def test_an_empty_exc_tuple_delegates(errors):
    """No exception to show (``(None, None, None)``): nothing to handle, the original decides."""
    shell, rec, _h = _installed(errors)
    shell.showtraceback((None, None, None))  # the fake's default body then reads value None
    assert rec.calls == [] and shell.default_calls == [None]


def test_the_default_display_is_ipython_display_resolved_lazily(errors, monkeypatch):
    shown = []
    ipy = types.ModuleType("IPython")
    disp = types.ModuleType("IPython.display")
    disp.display = lambda obj, **kw: shown.append((obj, kw))
    ipy.display = disp
    monkeypatch.setitem(sys.modules, "IPython", ipy)
    monkeypatch.setitem(sys.modules, "IPython.display", disp)
    shell = FakeShell()
    errors.install(shell, session=SESSION, exec_count=1)  # no display= given
    shell.run(_raiser(case("E1").exc, "await"), "await")
    assert len(shown) == 1
    obj, kw = shown[0]
    assert set(obj) == {"text/html", "text/plain"} and kw["raw"] is True and kw["metadata"]["praxis"]["kind"] == "error"


def test_the_wrapper_is_an_instance_attribute_and_the_classes_are_untouched(errors):
    before_shell_cls = FakeShell.__dict__["showtraceback"]
    before_lh = {n: LiquidHandler.__dict__[n] for n in ("aspirate", "dispense", "pick_up_tips")}
    shell, _rec, _h = _installed(errors)
    assert "showtraceback" in vars(shell)
    assert FakeShell.__dict__["showtraceback"] is before_shell_cls
    assert {n: LiquidHandler.__dict__[n] for n in before_lh} == before_lh


def test_set_custom_exc_is_never_used_as_the_carrier(errors):
    """S3-C: ``set_custom_exc`` runs its handler but the return value is not the error output."""
    shell, _rec, _h = _installed(errors)
    shell.run(_raiser(case("E1").exc, "await"), "await")
    assert shell.custom_exc_calls == []


def test_install_is_idempotent_and_shows_one_panel(errors):
    shell = FakeShell()
    rec = Recorder(shell)
    h1 = errors.install(shell, session=SESSION, exec_count=1, display=rec)
    wrapper = vars(shell)["showtraceback"]
    h2 = errors.install(shell, session=SESSION, exec_count=1, display=rec)
    assert vars(shell)["showtraceback"] is wrapper
    assert h2 is h1
    out = shell.run(_raiser(case("E1").exc, "await"), "await")
    assert len(rec.calls) == 1  # not two stacked wrappers
    assert out["error"] is not None


def test_uninstall_restores_the_original_and_is_safe_twice(errors):
    shell = FakeShell()
    rec = Recorder(shell)
    handle = errors.install(shell, session=SESSION, exec_count=1, display=rec)
    assert "showtraceback" in vars(shell)
    handle.uninstall()
    assert "showtraceback" not in vars(shell)  # the class method shows again
    handle.uninstall()  # idempotent
    out = shell.run(_raiser(case("E1").exc, "plain"), "plain")
    assert rec.calls == [] and shell.default_calls == [case("E1").exc]
    assert out["error"]["traceback"][0].startswith("---- Traceback")


def test_uninstall_restores_a_prior_instance_attribute(errors):
    shell = FakeShell()
    prior = lambda *a, **k: "prior"  # noqa: E731
    shell.showtraceback = prior
    handle = errors.install(shell, session=SESSION, exec_count=1, display=Recorder(shell))
    assert vars(shell)["showtraceback"] is not prior
    handle.uninstall()
    assert vars(shell)["showtraceback"] is prior


def test_a_wrapper_wrapped_again_by_someone_else_passes_through_after_uninstall(errors):
    shell = FakeShell()
    rec = Recorder(shell)
    handle = errors.install(shell, session=SESSION, exec_count=1, display=rec)
    ours = vars(shell)["showtraceback"]

    def theirs(*a, **k):
        return ours(*a, **k)

    shell.showtraceback = theirs
    handle.uninstall()  # cannot remove ours from under theirs: it must simply go inert
    assert vars(shell)["showtraceback"] is theirs
    shell.run(_raiser(case("E1").exc, "plain"), "plain")
    assert rec.calls == []


def test_a_shell_without_showtraceback_underscore_falls_back_to_the_original(errors):
    """The error must never be lost: with no ``_showtraceback`` to finish through, delegate."""
    shell = FakeShell()
    shell._showtraceback = None  # not callable

    def orig_show(*a, **k):
        shell.default_calls.append("orig")

    shell.showtraceback = orig_show
    rec = Recorder(shell)
    errors.install(shell, session=SESSION, exec_count=1, display=rec)
    shell.run(_raiser(case("E1").exc, "plain"), "plain")
    assert shell.default_calls  # reached the original


def test_install_refuses_no_shell(errors):
    with pytest.raises(ValueError):
        errors.install(None)


def test_a_display_that_raises_never_costs_the_error_output(errors):
    shell = FakeShell()

    def bad_display(*a, **k):
        raise RuntimeError("display broke")

    errors.install(shell, session=SESSION, exec_count=1, display=bad_display)
    out = shell.run(_raiser(case("E1").exc, "await"), "await")
    assert out["error"]["traceback"] == [f"TooLittleLiquidError: {case('E1').exc}"]


def test_a_resolver_that_raises_inside_the_wrapper_still_shows_the_generic_panel_and_the_error(errors):
    def boom(exc, tb=None, **kw):
        raise RuntimeError("resolver blew up")

    shell, rec, _h = _installed(errors, resolver=boom)
    r = case("E1")
    out = shell.run(_raiser(r.exc, "await"), "await")
    assert len(rec.calls) == 1
    assert rec.calls[0]["obj"]["text/plain"].startswith("PyLabRobot raised TooLittleLiquidError")
    assert out["error"] is not None


def test_the_generic_panel_of_e13_and_e15_through_the_wrapper_has_a_null_resource(errors):
    for name in ("E13", "E15"):
        shell, rec, _h = _installed(errors)
        r = case(name)
        out = shell.run(_raiser(r.exc, "await"), "await")
        assert len(rec.calls) == 1
        assert rec.calls[0]["metadata"]["praxis"]["resource"] is None
        assert rec.calls[0]["obj"]["text/plain"] == f"PyLabRobot raised {type(r.exc).__name__}: {r.exc}"
        assert out["error"]["traceback"] == [f"{type(r.exc).__name__}: {r.exc}"]


def test_session_and_exec_are_read_at_render_time_from_callables(errors):
    shell = FakeShell()
    rec = Recorder(shell)
    box = {"s": "first"}
    errors.install(shell, session=lambda: box["s"], exec_count=lambda: shell.execution_count, display=rec)
    shell.run(_raiser(case("E1").exc, "plain"), "plain")
    box["s"] = "second"
    shell.run(_raiser(case("E1").exc, "plain"), "plain")
    stamps = [c["metadata"]["praxis"] for c in rec.calls]
    assert [s["session"] for s in stamps] == ["first", "second"]
    assert [s["exec"] for s in stamps] == [1, 2]


def test_the_ledger_is_displayed_before_the_panel_and_the_step_is_named(errors, led):
    """AC-17's order check with a real ``RunLedger`` (show on) around a failing op: the recorded
    ``display`` calls are the ledger, then the panel; the panel names the step; the entry is gone."""
    shell = FakeShell()
    rec = Recorder(shell)
    errors.install(shell, session=SESSION, exec_count=1, display=rec)
    exc_box = {}

    async def cell():
        deck, lh, tips, source, assay = await _world()
        with led.RunLedger(lh, display=rec):
            await lh.pick_up_tips(tips["A1:H1"])
            await lh.aspirate(source["A1:H1"], vols=[50.0] * 8)
            await lh.dispense(assay["A1:H1"], vols=[50.0] * 8)
            try:
                await lh.aspirate(assay["A1:H1"], vols=[80.0] * 8)
            except TooLittleLiquidError as e:
                exc_box["exc"] = e
                raise

    out = shell.run(cell, "await")
    assert len(rec.calls) == 2
    assert isinstance(rec.calls[0]["obj"], led.RunLedger) and rec.calls[0]["raw"] is False
    assert rec.calls[1]["raw"] is True
    panel = rec.calls[1]["obj"]
    root = _parse(panel["text/html"])
    assert _part(root, "step") == "Step 4 of the run."
    assert _text_of(root, "praxis-error__title") == "Not enough liquid in assay A1:H1."
    assert id(exc_box["exc"]) not in led._ERROR_STEPS
    assert out["error"] is not None


# --------------------------------------------------------------------------- the API and imports


def test_the_public_api(errors):
    assert set(errors.__all__) >= {"handled_classes", "render", "handle", "install"}
    for name in ("render", "handle", "install", "handled_classes"):
        assert callable(getattr(errors, name))


def test_handled_classes_are_exactly_the_four(errors):
    assert set(errors.handled_classes()) == {TooLittleLiquidError, TooLittleVolumeError, HasTipError, NoTipError}


_ENV_PIN = {"PYTHONPATH": str(Path(pylabrobot.__file__).resolve().parent.parent)}

_LOAD = f"""
import sys, types, importlib
pkg = types.ModuleType({_PKG!r}); pkg.__path__ = [{str(_DISPLAY_DIR)!r}]; pkg.__package__ = {_PKG!r}
sys.modules[{_PKG!r}] = pkg
"""


def _run_py(code):
    env = {**os.environ, **_ENV_PIN}
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=180,
                          check=False, env=env)


def test_errors_imports_in_plain_cpython_with_no_plr_ipython_or_js_at_import_time():
    if not _ERRORS_PATH.is_file():
        pytest.fail(f"praxis/display/errors.py does not exist yet: {_ERRORS_PATH}")
    code = _LOAD + f"""
m = importlib.import_module({_PKG!r} + '.errors')
bad = [k for k in sys.modules if k.split('.')[0] in ('pylabrobot', 'IPython', 'js')]
assert not bad, bad
print('ok', m.install.__name__)
"""
    proc = _run_py(code)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip() == "ok install"


def test_errors_lazy_plr_imports_are_quiet_under_warnings_as_errors_and_use_only_the_pins_homes():
    if not _ERRORS_PATH.is_file():
        pytest.fail(f"praxis/display/errors.py does not exist yet: {_ERRORS_PATH}")
    code = _LOAD + f"""
import warnings
warnings.simplefilter('error', DeprecationWarning)
m = importlib.import_module({_PKG!r} + '.errors')
assert len(m.handled_classes()) == 4
for shim in ('pylabrobot.liquid_handling', 'pylabrobot.resources.tip_tracker'):
    assert shim not in sys.modules, shim
print('ok')
"""
    proc = _run_py(code)
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert proc.stdout.strip() == "ok"


def _plr_imports(source: str) -> set[str]:
    mods = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("pylabrobot"):
            mods.add(node.module)
        elif isinstance(node, ast.Import):
            mods |= {a.name for a in node.names if a.name.startswith("pylabrobot")}
    return mods


def test_errors_names_only_the_pins_non_shim_homes(errors):
    mods = _plr_imports(_ERRORS_PATH.read_text())
    assert mods <= ALLOWED_PLR_MODULES, mods - ALLOWED_PLR_MODULES
    assert "pylabrobot.resources.errors" in mods  # the four classes come from their home


def test_errors_has_no_module_level_ipython_js_or_plr_import(errors):
    tree = ast.parse(_ERRORS_PATH.read_text())
    top = {
        alias.name.split(".")[0]
        for node in tree.body if isinstance(node, ast.Import) for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in tree.body if isinstance(node, ast.ImportFrom) and node.level == 0
    }
    assert not top & {"pylabrobot", "IPython", "js"}, top


# --------------------------------------------------------------------------- AC-28: no glossary literal here


def _docstring_nodes(tree):
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                out.add(id(body[0].value))
    return out


def literals_from_the_table(source, table):
    """The AC-28 scan (as ``test_display_glossary.py`` has it): string literals, docstrings skipped,
    comments not in the AST, equal to a string of the glossary table."""
    tree = ast.parse(source)
    skip = _docstring_nodes(tree)
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip and n.value in table]


def _table(gl):
    return set(gl.ACTIONS) | set(gl.ACTIONS.values()) | set(gl.VERBS.values())


def test_the_scan_control_flags_a_spelled_action_and_ignores_docstrings_and_comments(gl):
    table = _table(gl)
    for src in ('x = "Aspirate"\n', 'y = ("pick_up_tips", 1)\n', 'z = {"k": "discard tips"}\n'):
        assert literals_from_the_table(src, table), src
    for src in ('"""Aspirate."""\nx = 1\n', '# "Aspirate"\nx = 1\n', 'x = "the aspirate asked"\n'):
        assert literals_from_the_table(src, table) == [], src


def test_errors_spells_no_glossary_literal(errors, gl):
    """AC-28, second bullet, for errors.py: names come from ``glossary.action_name`` / ``verb_form``."""
    hits = literals_from_the_table(_ERRORS_PATH.read_text(), _table(gl))
    assert hits == [], f"action strings outside glossary.py: {sorted(set(hits))}"


def test_errors_asks_the_glossary_for_action_names(errors):
    src = _ERRORS_PATH.read_text()
    assert "glossary.action_name" in src and "glossary.verb_form" in src


def test_every_action_string_in_a_panel_equals_a_glossary_value(errors, gl):
    """AC-28, first bullet, for the error half: the {Action} in each body is ``glossary.action_name``."""
    for name, op in (("E5", "drop_tips"), ("E11", "return_tips"), ("E16", "discard_tips"), ("E6", "aspirate")):
        _d, _m, root = _render(errors, name)
        body = _part(root, "body")
        assert gl.action_name(op) in body, (name, body)
    _d, _m, root = _render(errors, "E16")
    assert gl.verb_form("discard_tips") in _part(root, "fix")
    assert gl.action_name("pick_up_tips") in _part(root, "fix")


# --------------------------------------------------------------------------- the 96-head panels (#5659)
#
# Spec: ``261001_nd-next-5659-96head-errors.md`` N5659-6 (the rows), N5659-7 (size), N5659-8 (committed
# rack tips), AC-96-6, -7, -9 and -11. ``-k "panel96 or size96 or order96 or rack_committed"``.

_ALL_IDS = [f"{r}{c}" for c in range(1, 13) for r in "ABCDEFGH"]
_PARTIAL_IDS = [i for i in _ALL_IDS if i not in ("A1", "B1", "C1", "C7")]
_ROW_D = [f"D{c}" for c in range(1, 13)]


def _compress(ids):
    return _sibling("labware").compress_wells(ids)


# (case, heading, body, fix, resource in the stamp, fault ids or None when there is no drawing)
# Transcribed from N5659-6 independently of the module (the oracle). {W} comes from labware.compress_wells.
ROWS96 = [
    (
        "E96-empty",
        "Not enough liquid in assay A1:H12.",
        "Each well holds 0 µL; the aspirate asked for 50 µL on every channel. Nothing was aspirated.",
        "Lower `volume` to 0 µL or less, or aspirate from wells that hold more.",
        "assay", set(_ALL_IDS),
    ),
    (
        "E96-rowD",
        "Not enough liquid in assay D1:D12.",
        "Each well holds 10 µL; the aspirate asked for 50 µL on every channel. Nothing was aspirated.",
        "Lower `volume` to 10 µL or less, or aspirate from wells that hold more.",
        "assay", set(_ROW_D),
    ),
    (
        "E96-partial",
        f"Not enough liquid in assay {_compress(_PARTIAL_IDS)}.",
        "Each well holds 0 µL; the aspirate asked for 50 µL on every channel. Nothing was aspirated.",
        "Lower `volume` to 0 µL or less, or aspirate from wells that hold more.",
        "assay", set(_PARTIAL_IDS),
    ),
    (
        "E96-shared",
        "Not enough liquid in assay A1.",
        "Each well holds 60 µL; the aspirate asked for 100 µL per well, summed over the channels that "
        "share it. Nothing was aspirated.",
        "Lower `volume` to 60 µL or less, or aspirate from wells that hold more.",
        "assay", {"A1"},
    ),
    (
        "E96-single",
        "Not enough liquid in big.",
        "It holds 2,000 µL; the aspirate asked for 2,880 µL across 96 channels. Nothing was aspirated.",
        "Lower `volume`, or aspirate from a container that holds more.",
        "big", None,
    ),
    (
        "E96-onewell-plate",
        "Not enough liquid in trough_plate.",
        "It holds 1,000 µL; the aspirate asked for 2,880 µL across 96 channels. Nothing was aspirated.",
        "Lower `volume`, or aspirate from a container that holds more.",
        "trough_plate", None,
    ),
    (
        "E96-tipTLL",
        "Not enough liquid in 96 tips on the 96 head.",
        "Each holds 30 µL; the dispense asked for 50 µL on every channel. Nothing was dispensed.",
        "Dispense 30 µL or less, or aspirate more first.",
        None, None,
    ),
    (
        "E96-tipTLL-D2",
        "Not enough liquid in 2 tips on the 96 head.",
        "Each holds 20 µL; the dispense asked for 25 µL on every channel. Nothing was dispensed.",
        "Dispense 20 µL or less, or aspirate more first.",
        None, None,
    ),
    (
        "E96-tipTLV",
        "Not enough room in 96 tips on the 96 head.",
        "Each has room for 160 µL; the aspirate asked for 200 µL on every channel. Nothing was aspirated.",
        "Aspirate less, or use larger tips.",
        None, None,
    ),
    (
        "E96-dispTLV",
        "Not enough room in assay C2:D2, A6.",
        "Each well has room for 30 µL; the dispense asked for 100 µL on every channel. Nothing was dispensed.",
        "Lower `volume`, or dispense into emptier wells.",
        "assay", {"C2", "D2", "A6"},
    ),
    (
        "E96-hasTip-pickup",
        "The 96 head already holds a tip on 2 channels.",
        "Pick up tips (96 head) asked those channels for another.",
        "Drop or discard the tips first.",
        None, None,
    ),
    (
        "E96-hasTip-drop",
        "tips_300 F1, F10 already have tips.",
        "Drop tips (96 head) asked to put tips there.",
        "Drop the tips into empty positions.",
        "tips_300", {"F1", "F10"},
    ),
    (
        "E96-return",
        "tips_300 F1 already has a tip.",
        "Return tips (96 head) asked to put tips there.",
        "Drop the tips into empty positions.",
        "tips_300", {"F1"},
    ),
]


def _check_row96(errors, svg, row):
    name, heading, body, fix, resource, fault = row
    r = case(name)
    data, meta, root = _render(errors, name)
    assert _text_of(root, "praxis-error__title") == heading
    assert _part(root, "body") == body
    assert _part(root, "fix") == fix
    assert meta == {"praxis": {"v": 1, "kind": "error", "resource": resource, "rev": None,
                               "session": SESSION, "exec": EXEC}}
    svg.check_bundle(data, meta)
    assert _text_of(root, "praxis-error__plr") == f"PyLabRobot raised {type(r.exc).__name__}: {r.exc}"
    plain = data["text/plain"]
    assert heading in plain and body in plain and fix in plain
    assert f"PyLabRobot raised {type(r.exc).__name__}: {r.exc}" in plain
    assert bool(root.find_all("svg")) is (fault is not None)  # tip, channel and single rows draw nothing
    if fault is not None:
        assert _fault_ids(root) == fault
        # a ring path AND a cross path, one ring per offender and two strokes per cross (D3)
        p = _paths(root)
        assert len(_subpaths(p["sv-fault"][0])) == len(fault)
        assert len(_subpaths(p["sv-fault-x"][0])) == 2 * len(fault)


@pytest.mark.parametrize("row", ROWS96, ids=[t[0] for t in ROWS96])
def test_panel96_each_row(errors, svg, row):
    _check_row96(errors, svg, row)


def test_panel96_the_one_well_plate_says_across_96_channels_never_on_every_channel(errors):
    """C4: a one-item Plate is single-container mode; its well's parent IS a Plate, so a dispatch on
    ``_in_plate`` would render the well row."""
    r = case("E96-onewell-plate")
    assert r.plate.get_item(0).parent is r.plate
    _d, _m, root = _render(errors, "E96-onewell-plate")
    body = _part(root, "body")
    assert "across 96 channels" in body and "on every channel" not in body
    assert _text_of(root, "praxis-error__title") == "Not enough liquid in trough_plate."


def test_panel96_a_single_container_never_shows_plrs_pending_numbers_outside_its_line(errors):
    r = case("E96-single")
    assert "30.0uL > 20.0uL" in str(r.exc)  # PLR's pending-state message (the premise)
    _d, _m, root = _render(errors, "E96-single")
    outside = _without_plr_and_traceback(root)
    assert "30.0uL" not in outside and "20.0uL" not in outside and "> 20" not in outside


def test_panel96_plural_spots_say_have_and_one_spot_says_has(errors):
    assert _text_of(_render(errors, "E96-hasTip-drop")[2], "praxis-error__title").endswith("already have tips.")
    assert _text_of(_render(errors, "E96-return")[2], "praxis-error__title").endswith("already has a tip.")


def test_panel96_names_the_step_from_a_real_run_ledger(errors, led):
    r = asyncio.run(SCENARIOS["E96_ledger"]())  # fresh: the autouse fixture clears _ERROR_STEPS per test
    assert r.run.rows[-1].step == 2  # pick up, then the failing aspirate
    shown = []
    errors.handle(r.exc, r.tb, session=SESSION, exec_count=EXEC, display=lambda *a, **k: shown.append((a, k)))
    (args, _kwargs), = shown
    root = _parse(args[0]["text/html"])
    assert _part(root, "step") == "Step 2 of the run."
    assert _text_of(root, "praxis-error__title") == "Not enough liquid in assay A1:H12."
    assert args[0]["text/plain"].startswith("Step 2 of the run.")


def test_panel96_the_96_rows_use_the_glossary_for_names_and_verbs(errors, gl):
    for name, expect in (("E96-hasTip-pickup", "pick_up_tips96"), ("E96-return", "return_tips96")):
        _d, _m, root = _render(errors, name)
        assert _part(root, "body").startswith(gl.action_name(expect))
    _d, _m, root = _render(errors, "E96-tipTLL")
    assert gl.HEAD96_NOUN in _text_of(root, "praxis-error__title")


# ---- the controls: each must FAIL the row check built for it


def test_panel96_control_a_handler_that_always_shows_the_generic_panel_fails_every_row(errors, svg, ctxmod, monkeypatch):
    for row in ROWS96:
        _check_row96(errors, svg, row)  # the good module passes them all
    monkeypatch.setattr(ctxmod, "resolve", lambda *a, **k: None)
    for row in ROWS96:
        with pytest.raises(AssertionError):
            _check_row96(errors, svg, row)


def test_panel96_control_an_in_plate_dispatch_renders_the_well_row_for_the_one_well_plate(errors, svg, monkeypatch):
    row = next(t for t in ROWS96 if t[0] == "E96-onewell-plate")
    _check_row96(errors, svg, row)
    monkeypatch.setattr(errors, "_row_kind", lambda ctx: "plate" if errors._in_plate(ctx.owner) else "single")
    with pytest.raises(AssertionError):
        _check_row96(errors, svg, row)
    # and it is specific: the bare container (no parent plate) and the real plate rows still pass
    for name in ("E96-single", "E96-rowD"):
        _check_row96(errors, svg, next(t for t in ROWS96 if t[0] == name))


def test_panel96_control_a_heading_from_the_first_failure_only_fails_row_d(errors, svg, ctxmod):
    import dataclasses

    row = next(t for t in ROWS96 if t[0] == "E96-rowD")
    _check_row96(errors, svg, row)

    def first_failure(exc, tb=None, **kw):
        ctx = ctxmod.resolve(exc, tb, **kw)
        return dataclasses.replace(ctx, offending=ctx.offending[:1])

    r = case("E96-rowD")
    data, _meta = errors.render(r.exc, r.tb, session=SESSION, exec_count=EXEC, resolver=first_failure)
    assert _text_of(_parse(data["text/html"]), "praxis-error__title") == "Not enough liquid in assay D1."
    assert _text_of(_parse(data["text/html"]), "praxis-error__title") != row[1]


def _check_96_plate_is_drawn_committed(errors):
    """E96-rowD leaves A1-C1 with pending 30 and committed 80: the drawing's hover values say 80."""
    r = case("E96-rowD")
    a1 = r.assay.get_item("A1")
    assert (a1.tracker.volume, a1.tracker.pending_volume) == (80, 30)  # the residue (precondition)
    data, _meta = errors.render(r.exc, r.tb, session=SESSION, exec_count=EXEC)
    grid = _grid(_parse(data["text/html"]))
    assert grid["vals"][grid["ids"].split().index("A1")] == 80


def test_panel96_the_plate_is_drawn_at_committed_volume_with_residue_on_the_op_wells(errors):
    _check_96_plate_is_drawn_committed(errors)


def test_panel96_control_a_pending_volume_drawing_fails_the_residue_check(errors, monkeypatch):
    _check_96_plate_is_drawn_committed(errors)
    monkeypatch.setattr(errors, "_drawn_volume", lambda container: container.tracker.get_used_volume())
    with pytest.raises(AssertionError):
        _check_96_plate_is_drawn_committed(errors)


# ---- GENERIC_CASES: the 96 cases that stay generic (see GENERIC_CASES above)


def test_panel96_control_a_mutant_without_the_no_row_guard_renders_a_row_for_a_single_container_overflow(errors, ctxmod, svg, monkeypatch):
    def generic(name):
        r = case(name)
        _d, _m, root = _render(errors, name)
        assert _text_of(root, "praxis-error__title") == f"PyLabRobot raised {type(r.exc).__name__}: {r.exc}"
        assert not _summaries(root)

    for name in ("E96-N", "E96-onewell-TLV"):
        ctx = ctxmod.resolve(case(name).exc)
        assert ctx is not None and ctx.head96 and ctx.container_mode == "single"  # a context, no row
        generic(name)
    monkeypatch.setattr(errors, "_single_container_has_row", lambda lack: True)
    for name in ("E96-N", "E96-onewell-TLV"):
        with pytest.raises(AssertionError):
            generic(name)


# --------------------------------------------------------------------------- N5659-7: size96


def _real_context_resolver(ctxmod, name):
    ctx = ctxmod.resolve(case(name).exc)
    assert ctx is not None, name
    return lambda *a, **k: ctx


SIZE96 = (("E96-empty", TooLittleLiquidError), ("E96-hasTip-drop", HasTipError))


@pytest.mark.parametrize("quote", ['"', "<", "&", "'"])
@pytest.mark.parametrize(("name", "cls"), SIZE96, ids=[n for n, _ in SIZE96])
def test_size96_the_whole_96_panel_stays_under_64_kib_whatever_the_escaping_expands_to(errors, svg, ctxmod, name, cls, quote):
    """The plate figure with all 96 wells faulted (~19.7 KB) and the rack figure (~19.4 KB) share the
    64 KiB cap with a 16 KiB traceback that escapes up to 6x: the ladder and the shrinking cap carry it."""
    exc = _hostile_exc(cls, "\n".join(quote * 100 for _ in range(400)))
    data, meta = errors.render(exc, exc.__traceback__, session=SESSION, exec_count=EXEC,
                               resolver=_real_context_resolver(ctxmod, name))
    assert len(data["text/html"].encode("utf-8")) <= CAP
    svg.check_bundle(data, meta)
    assert "Show traceback" in data["text/html"]
    root = _parse(data["text/html"])
    assert _text_of(root, "praxis-error__title").startswith(("Not enough liquid in assay", "tips_300"))  # a row, not generic
    assert _details_text(root).count(quote) > 1000  # the traceback SHRANK to fit; it was not dropped


def _check_traceback_cap96(errors, ctxmod, name, cls):
    exc = _long_exc(4000)
    exc = _hostile_exc(cls, str(exc))
    data, _meta = errors.render(exc, exc.__traceback__, session=SESSION, exec_count=EXEC,
                                resolver=_real_context_resolver(ctxmod, name))
    body = _details_text(_parse(data["text/html"]))
    assert len(body.encode()) <= TB_CAP
    assert re.match(r"… \d+ earlier lines omitted\n", body)
    assert len(data["text/html"].encode()) <= CAP


@pytest.mark.parametrize(("name", "cls"), SIZE96, ids=[n for n, _ in SIZE96])
def test_size96_a_huge_traceback_is_tail_capped_on_the_96_panels_too(errors, ctxmod, name, cls):
    _check_traceback_cap96(errors, ctxmod, name, cls)


@pytest.mark.parametrize(("name", "cls"), SIZE96, ids=[n for n, _ in SIZE96])
def test_size96_control_a_handler_that_does_not_cap_the_traceback_fails_on_the_96_panels(errors, bud, ctxmod, name, cls, monkeypatch):
    _check_traceback_cap96(errors, ctxmod, name, cls)
    monkeypatch.setattr(bud, "cap_tail", lambda text, *a, **k: text)
    with pytest.raises(AssertionError):
        _check_traceback_cap96(errors, ctxmod, name, cls)


@pytest.mark.parametrize(("name", "cls"), SIZE96, ids=[n for n, _ in SIZE96])
def test_size96_control_a_fit_without_the_ladder_exceeds_the_cap_for_quotes(errors, ctxmod, name, cls, monkeypatch):
    """A ``_fit`` that renders level 0 with the full 16 KiB traceback and no ladder is over 64 KiB for
    ``"`` (6 bytes each); the real ``_fit`` is not."""
    exc = _hostile_exc(cls, "\n".join('"' * 100 for _ in range(400)))
    resolver = _real_context_resolver(ctxmod, name)

    def size():
        data, _meta = errors.render(exc, exc.__traceback__, session=SESSION, exec_count=EXEC, resolver=resolver)
        return len(data["text/html"].encode("utf-8"))

    assert size() <= CAP
    monkeypatch.setattr(
        errors, "_fit",
        lambda exc, panel, step, tb_text: errors._html(exc, panel, step, tb_text, 0, errors._TB_LIMITS[0]),
    )
    assert size() > CAP


# --------------------------------------------------------------------------- AC-96-9: order96


def _pin_source():
    return inspect.getsource(sys.modules[LiquidHandler.__module__])


def _op_body(src, op):
    start = src.index(f"  async def {op}(")
    ends = [i for i in (src.find("\n  async def ", start + 10), src.find("\n  def ", start + 10)) if i != -1]
    return src[start : min(ends)]


def _check_queue_before_the_try(op, tracker_calls, backend_op=None):
    """In the op's source: the first tracker call < ``try:`` < ``await self.backend.<op>(``, and every
    ``rollback()`` comes after ``try:``. True of the 96 ops (their refusals leave pending state behind);
    false of the 1-channel ops, whose queue loop is inside the ``try`` and so rolls back."""
    body = _op_body(_pin_source(), op)
    try_at = body.index("try:")
    first_tracker = min(body.index(c) for c in tracker_calls if c in body)
    backend_at = body.index(f"await self.backend.{backend_op or op}(")
    rollbacks = [m.start() for m in re.finditer(r"\.rollback\(\)", body)]
    assert rollbacks, op
    assert first_tracker < try_at < backend_at, (op, first_tracker, try_at, backend_at)
    assert all(at > try_at for at in rollbacks), (op, rollbacks, try_at)


ORDER96 = [
    ("aspirate96", ("remove_liquid(",)), ("dispense96", ("add_liquid(",)),
    ("pick_up_tips96", ("add_tip(", "remove_tip(")), ("drop_tips96", ("add_tip(", "remove_tip(")),
]


@pytest.mark.parametrize(("op", "calls"), ORDER96, ids=[o for o, _ in ORDER96])
def test_order96_the_tracker_queue_precedes_the_try_and_the_backend_call(op, calls):
    _check_queue_before_the_try(op, calls)


@pytest.mark.parametrize(("op", "calls"), [("aspirate", ("remove_liquid(",)), ("dispense", ("add_liquid(",))])
def test_order96_control_the_one_channel_ops_queue_inside_the_try_and_fail_the_check(op, calls):
    with pytest.raises(AssertionError):
        _check_queue_before_the_try(op, calls)


def test_order96_no_backend_96_call_is_made_at_a_refusal():
    refusals = ("E96-empty", "E96-rowD", "E96-tipTLL", "E96-tipTLV", "E96-dispTLV", "E96-single", "E96-N")
    for name in refusals:
        r = case(name)
        before, after = r.lh.calls_at_failure
        assert after == before, (name, r.lh.backend_calls)


def test_order96_control_the_spy_records_a_successful_aspirate96():
    async def go():
        deck, lh, tips, source, _assay = await _world()
        await lh.pick_up_tips96(tips)
        await lh.aspirate96(source, volume=10.0)
        await lh.dispense96(source, volume=10.0)
        return lh.backend_calls

    assert asyncio.run(go()) == ["aspirate96", "dispense96"]
    # and the refusals above are about the TipSpot / pre-try work, not a dead spy: tipTLL did succeed once
    assert case("E96-tipTLL").lh.backend_calls == ["aspirate96"]


# --------------------------------------------------------------------------- AC-96-11: rack_committed


def _committed_tip(spot):
    from pylabrobot.resources.errors import NoTipError as _NoTip

    try:
        return tip_spot_tracker(spot).get_tip()
    except _NoTip:
        return None


def _rack_surfaces(root):
    paths = _paths(root)
    rings = len(_subpaths(paths["sv-tip-ring"][0])) if "sv-tip-ring" in paths else 0
    groups = [n for n in root.walk() if n.tag == "g" and "data-praxis-grid" in n.attrs]
    assert len(groups) == 1
    return rings, sum(_grid(root)["vals"]), groups[0].attrs["aria-label"]


def _check_rack_committed(errors, lw, name, present):
    r = case(name)
    _d, _m, root = _render(errors, name)
    expected = lw.tiprack_sentence(r.tips, tip_of=_committed_tip)
    assert expected.startswith(f"{present} of 96 tips left.")
    assert _rack_surfaces(root) == (present, present, expected)


def test_rack_committed_the_96_drop_panel_draws_the_committed_tips(errors, lw):
    _check_rack_committed(errors, lw, "E96-hasTip-drop", 2)
    r = case("E96-hasTip-drop")
    assert sum(1 for s in r.tips.get_all_items() if s.tip is not None) == 7  # the pending view: 7, not 2


def test_rack_committed_the_one_channel_panel_draws_the_committed_tips_after_residue(errors, lw):
    """P1: today's panel draws 92 tips while 95 spots hold a committed tip (Q6 = yes, every error panel)."""
    _check_rack_committed(errors, lw, "P1", 95)
    r = case("P1")
    assert sum(1 for s in r.tips.get_all_items() if s.tip is not None) == 92  # the pending view


@pytest.mark.parametrize(("name", "present"), [("E96-hasTip-drop", 2), ("P1", 95)])
def test_rack_committed_control_the_default_pending_hook_fails_the_check(errors, lw, monkeypatch, name, present):
    _check_rack_committed(errors, lw, name, present)
    monkeypatch.setattr(errors, "_drawn_tip", lambda spot: spot.tip)
    with pytest.raises(AssertionError):
        _check_rack_committed(errors, lw, name, present)


def test_rack_committed_the_p1_panel_keeps_the_one_channel_texts(errors):
    _d, _m, root = _render(errors, "P1")
    assert _text_of(root, "praxis-error__title") == "tips_300 A1 already has a tip."
    assert _part(root, "body") == "Drop tips asked to put a tip there."
    assert _fault_ids(root) == {"A1"}


# --------------------------------------------------------------------------- the residue sentence (#5659 task 8)
#
# Spec: ``261001_nd-next-5659-96head-errors.md`` N5659-11 and the decision sheet's Q4 (the wording is the
# user's, accepted 261001), AC-96-R2. ``-k residue96``. The sentence follows the fix on every 96 ROW (never
# the generic panel), in ``text/plain`` too; its drawing clause only where the panel has a drawing. It is a
# ``div.praxis-summary`` and not a third ``p.praxis-summary``: ``_part`` (above, unchanged) counts exactly
# two ``p.praxis-summary`` elements, the body and the fix.

RESIDUE_SENTENCE = (
    "PyLabRobot still records moves that did not happen on {x}; the next step that succeeds will save "
    "them, and the tracked state will be wrong from then on."
)
RESIDUE_CLAUSE = " The drawing shows what was actually done."
_RESIDUE_WELLS_0_9 = [f"{row}1" for row in "ABCDEFGH"] + ["A2", "B2"]

# (case, the {x} of the sentence, does the panel have a drawing?). Transcribed from the decision sheet's
# Q4 and N5659-11's list of what {x} joins (plate wells, container names, tips, channels, rack spots).
RESIDUE_NOTES = [
    ("E96-rowD", "assay A1:C1 and 3 tips on the 96 head", True),
    ("E96-shared", "assay A1 and 1 tip on the 96 head", True),
    ("E96-dispTLV", f"assay {_compress(_RESIDUE_WELLS_0_9)} and 96 tips on the 96 head", True),
    ("E96-tipTLL-D2", "7 tips on the 96 head", False),
    ("E96-tipTLV", "source A1", False),
    ("E96-single", "big and 66 tips on the 96 head", False),
    ("E96-onewell-plate", "trough_plate and 33 tips on the 96 head", False),
    ("E96-hasTip-pickup", "3 channels of the 96 head and tips_300 A1:C1", False),
    ("E96-hasTip-drop", "5 channels of the 96 head and tips_300 A1:E1", True),
    ("E96-return", "5 channels of the 96 head and tips_300 A1:E1", True),
]
#: no residue (a first-position failure), a refusal to guess (None), a context with no row (generic), 1-channel
NO_RESIDUE_NOTE = [
    "E96-empty", "E96-partial", "E96-tipTLL", "E96-residue-TLL", "E96-noTip-residue", "E96-N", "E96-onewell-TLV",
    "P1", "E1",
]


def _notes(root):
    return root.find_all("div", "praxis-summary")


def _check_residue_note(errors, row):
    name, x, drawn = row
    data, _meta, root = _render(errors, name)
    expected = RESIDUE_SENTENCE.format(x=x) + (RESIDUE_CLAUSE if drawn else "")
    assert [n.text() for n in _notes(root)] == [expected], name
    assert len(_summaries(root)) == 2, name  # the body and the fix are still the only p.praxis-summary
    # text/plain: the heading, body and fix, then the sentence on its own line, then PLR's line
    lines = data["text/plain"].split("\n")
    assert expected in lines, name
    fix = _part(root, "fix")
    assert lines.index(fix) + 1 == lines.index(expected) == len(lines) - 2, name
    assert lines[-1].startswith("PyLabRobot raised "), name
    # html: fix, then the sentence, then the drawing (when there is one), then PLR's line
    html = data["text/html"]
    at = {"fix": html.index(fix), "note": html.index("PyLabRobot still records"), "plr": html.index("praxis-error__plr")}
    assert at["fix"] < at["note"] < at["plr"], name
    if drawn:
        assert at["note"] < html.index("<svg") < at["plr"], name
    else:
        assert "<svg" not in html, name
    assert bool(root.find_all("svg")) is drawn, name


def _check_no_residue_note(errors, name):
    data, _meta, root = _render(errors, name)
    assert "still records" not in data["text/html"], name
    assert "still records" not in data["text/plain"], name
    assert _notes(root) == [], name


def _fails_errors(check, *args):
    try:
        check(*args)
    except AssertionError:
        return True
    return False


@pytest.mark.parametrize("row", RESIDUE_NOTES, ids=[r[0] for r in RESIDUE_NOTES])
def test_residue96_the_sentence_follows_the_fix_on_every_96_row(errors, row):
    _check_residue_note(errors, row)


@pytest.mark.parametrize("name", NO_RESIDUE_NOTE)
def test_residue96_no_sentence_without_residue_and_none_on_the_generic_panel(errors, name):
    _check_no_residue_note(errors, name)


def test_residue96_premise_the_generic_96_panels_are_generic_although_residue_exists(errors, ctxmod):
    """E96-N and E96-onewell-TLV resolve to a context WITH residue (96 queued tips) and have no template
    row: the generic panel carries no sentence. E96-residue-TLL and E96-noTip-residue resolve to ``None``
    while the world holds residue. Neither is 'no residue', so the checks above test the rule, not an absence."""
    for name in ("E96-N", "E96-onewell-TLV"):
        ctx = ctxmod.resolve(case(name).exc)
        assert ctx is not None and ctx.head96 is True and len(ctx.residue) == 96, name
        assert errors._panel_for(case(name).exc, ctx) is None, name
    for name in ("E96-residue-TLL", "E96-noTip-residue"):
        assert ctxmod.resolve(case(name).exc) is None, name
    for name in ("E96-empty", "E96-partial", "E96-tipTLL"):
        ctx = ctxmod.resolve(case(name).exc)
        assert ctx is not None and ctx.residue == (), name


def test_residue96_the_sentence_is_computed_from_the_contexts_residue(errors, ctxmod):
    rs = _sibling("residue")
    r = case("E96-rowD")
    ctx = ctxmod.resolve(r.exc)

    def render_with(residue):
        resolver = lambda *a, **k: dataclasses.replace(ctx, residue=residue)  # noqa: E731
        _data, _meta, root = _render(errors, r, resolver=resolver)
        return [n.text() for n in _notes(root)]

    assert render_with(()) == []
    only_b1 = (rs.Residue(rs.KIND_CONTAINER, r.assay.get_item("B1")),)
    assert render_with(only_b1) == [RESIDUE_SENTENCE.format(x="assay B1") + RESIDUE_CLAUSE]
    mixed = (
        rs.Residue(rs.KIND_CONTAINER, r.assay.get_item("A1")), rs.Residue(rs.KIND_CONTAINER, r.assay.get_item("H1")),
        rs.Residue(rs.KIND_TIP, 4), rs.Residue(rs.KIND_CHANNEL, 2), rs.Residue(rs.KIND_CHANNEL, 3),
    )
    assert render_with(mixed) == [
        RESIDUE_SENTENCE.format(x="assay A1, H1, 1 tip on the 96 head and 2 channels of the 96 head") + RESIDUE_CLAUSE
    ]


def test_residue96_a_hostile_container_name_is_escaped_in_the_sentence(errors, ctxmod):
    rs = _sibling("residue")
    r = case("E96-rowD")
    ctx = ctxmod.resolve(r.exc)
    evil = Container(name='<script>alert("x")</script>', size_x=10.0, size_y=10.0, size_z=10.0, max_volume=100.0)
    resolver = lambda *a, **k: dataclasses.replace(ctx, residue=(rs.Residue(rs.KIND_CONTAINER, evil),))  # noqa: E731
    data, _meta, root = _render(errors, r, resolver=resolver)
    assert "<script>" not in data["text/html"]
    (note,) = _notes(root)
    assert '<script>alert("x")</script>' in note.text()  # escaped on the way out, the text round-trips


# ---- AC-96-R2 controls: each broken variant must FAIL the check built for it


def test_residue96_control_an_unconditional_drawing_clause_fails_the_rows_without_a_drawing(errors, monkeypatch):
    for row in RESIDUE_NOTES:
        _check_residue_note(errors, row)  # the real module passes them all
    monkeypatch.setattr(errors, "_drawing_clause", lambda drawn: RESIDUE_CLAUSE)
    failing = sorted(r[0] for r in RESIDUE_NOTES if _fails_errors(_check_residue_note, errors, r))
    assert failing == sorted(r[0] for r in RESIDUE_NOTES if not r[2])  # exactly the tip, channel and single rows
    assert "E96-tipTLL-D2" in failing  # the spec's case


def test_residue96_control_a_never_present_clause_fails_the_rows_with_a_drawing(errors, monkeypatch):
    monkeypatch.setattr(errors, "_drawing_clause", lambda drawn: "")
    failing = sorted(r[0] for r in RESIDUE_NOTES if _fails_errors(_check_residue_note, errors, r))
    assert failing == sorted(r[0] for r in RESIDUE_NOTES if r[2])


def test_residue96_control_an_always_sentence_handler_fails_the_row_without_residue(errors, monkeypatch):
    for name in NO_RESIDUE_NOTE:
        _check_no_residue_note(errors, name)
    monkeypatch.setattr(errors, "_residue_text", lambda ctx: RESIDUE_SENTENCE.format(x="the head"))
    failing = sorted(n for n in NO_RESIDUE_NOTE if _fails_errors(_check_no_residue_note, errors, n))
    # every no-residue 96 row; the generic panels have nowhere to put it, and the 1-channel rows are not its
    assert failing == ["E96-empty", "E96-partial", "E96-tipTLL"]
    assert "E96-empty" in failing  # the spec's case


def test_residue96_control_a_handler_that_ignores_the_residue_fails_every_note_row(errors, monkeypatch):
    monkeypatch.setattr(errors, "_residue_text", lambda ctx: "")
    assert [r[0] for r in RESIDUE_NOTES if not _fails_errors(_check_residue_note, errors, r)] == []


def test_residue96_control_a_third_p_praxis_summary_would_break_the_body_and_fix_helpers(errors):
    """Why the sentence is a div: the existing helper asserts exactly two ``p.praxis-summary`` (the body and
    the fix). The real panel keeps that; a panel with the sentence as a third ``p`` would not."""
    data, _meta, root = _render(errors, "E96-rowD")
    assert len(_summaries(root)) == 2 and len(_notes(root)) == 1
    three = _parse(data["text/html"].replace('<div class="praxis-summary">PyLabRobot still', '<p class="praxis-summary">PyLabRobot still'))
    assert len(_summaries(three)) == 3
    with pytest.raises(AssertionError):
        _part(three, "body")


def test_residue96_the_clause_needs_a_drawing_that_is_actually_there(errors, ctxmod, bud):
    """At the omitted level the figure is replaced by the omission sentence: "The drawing shows ..." would
    point at nothing. At the full level it is there."""
    name = "E96-rowD"
    r = case(name)
    ctx = ctxmod.resolve(r.exc)
    panel = errors._panel_for(r.exc, ctx)
    assert panel is not None and panel.figure is not None and panel.residue
    tb_text = errors._traceback_text(r.exc, r.tb)
    full = errors._html(r.exc, panel, None, tb_text, bud.LEVEL_FULL, 2048)
    omitted = errors._html(r.exc, panel, None, tb_text, bud.LEVEL_OMITTED, 2048)
    assert "The drawing shows what was actually done." in full and "<svg" in full
    assert "PyLabRobot still records" in omitted  # the hazard stays
    assert "The drawing shows" not in omitted and "<svg" not in omitted and bud.OMISSION_SENTENCE in omitted


def test_residue96_the_whole_panel_with_the_sentence_stays_under_the_cap_for_the_worst_residue(errors, svg, ctxmod):
    """The plate row with the longest sentence in this file (96 tips and 10 wells, drawn) and a 40 KB hostile
    traceback that escapes 6x still fits the 64 KiB cap, and keeps the sentence."""
    exc = _hostile_exc(TooLittleVolumeError, "\n".join('"' * 100 for _ in range(400)))
    ctx = ctxmod.resolve(case("E96-dispTLV").exc)
    data, meta = errors.render(exc, session=SESSION, exec_count=EXEC, resolver=lambda *a, **k: ctx)
    assert len(data["text/html"].encode("utf-8")) <= CAP
    svg.check_bundle(data, meta)
    assert "PyLabRobot still records" in data["text/html"]
