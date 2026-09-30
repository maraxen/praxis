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
E16, E-96 and the negatives). The venv's editable PLR can be the old 0.2.2, so the first fixture asserts
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
from pylabrobot.resources import (
    does_tip_tracking,
    does_volume_tracking,
    set_tip_tracking,
    set_volume_tracking,
)
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
    for op in ("aspirate", "dispense"):
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


@scenario("E-96", TooLittleLiquidError)
async def _e96():
    """A real 96-head failure: pick up the whole rack, aspirate 50 uL from an empty assay plate."""
    deck, lh, tips, _source, assay = await _world()
    await lh.pick_up_tips96(tips)
    exc = await _catch(lh.aspirate96(assay, volume=50.0))
    return Raised(exc, deck=deck, lh=lh)


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


def _details_text(root):
    return _one(root, "praxis-details-body", "pre").text()


def _without_plr_and_traceback(root):
    """The text of the panel with the verbatim PLR line and the traceback removed."""
    parts = []
    for cls in ("praxis-error__step", "praxis-error__title", "praxis-error__body", "praxis-error__fix"):
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
    assert _text_of(root, "praxis-error__body") == body
    assert _text_of(root, "praxis-error__fix") == fix
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
    assert "Each well holds 50 µL; the aspirate asked for 80 µL." in _text_of(root, "praxis-error__body")
    assert "Nothing was aspirated." in _text_of(root, "praxis-error__body")


def test_the_fault_wells_carry_a_brick_ring_and_a_cross(errors):
    """AC-16 / D3: a fault is never colour alone (a ring path AND a cross path, one subpath per well)."""
    _data, _meta, root = _render(errors, "E1")
    p = _paths(root)
    assert len(p["sv-fault"]) == 1 and len(_subpaths(p["sv-fault"][0])) == 8
    assert len(p["sv-fault-x"]) == 1 and len(_subpaths(p["sv-fault-x"][0])) == 8
    for cls in ("sv-fault", "sv-fault-x"):
        (node,) = [n for n in root.find_all("path", cls)]
        assert node.attrs["stroke"] == "#B3402A"  # brick


def test_e10_marks_exactly_the_offending_wells(errors):
    _d, _m, root = _render(errors, "E10")
    assert _fault_ids(root) == {"A1", "B1", "C1", "D1"}
    assert len(_subpaths(_paths(root)["sv-fault"][0])) == 4


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
    assert _text_of(root, "praxis-error__body").startswith("Each well holds 50 µL; the aspirate asked for 80 µL.")
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


@pytest.mark.parametrize("name", ["E1", "E2", "E3", "E12", "E6", "E9", "E10"])
def test_nothing_was_aspirated_or_dispensed_the_backend_was_not_reached(errors, name):
    """A tracker refusal is raised before the backend is called (LH:1269-1274, :1470-1475): the spy
    records no aspirate or dispense call during the failing op (a confirmatory assert of the ordering,
    D8), and the panel says so."""
    r = case(name)
    before, after = r.lh.calls_at_failure
    assert after == before, (name, r.lh.backend_calls)
    _d, _m, root = _render(errors, name)
    body = _text_of(root, "praxis-error__body")
    assert ("Nothing was aspirated." in body) or ("Nothing was dispensed." in body)


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


GENERIC_CASES = ["E13", "E15", "E-96", "E8", "E2_summed"]


@pytest.mark.parametrize("name", GENERIC_CASES)
def test_a_context_that_is_none_gets_the_generic_panel(errors, ctxmod, svg, name):
    r = case(name)
    if name in ("E13", "E15", "E-96"):
        assert ctxmod.resolve(r.exc, r.tb) is None  # the AC-15 premise
    data, meta, root = _render(errors, name)
    sentence = f"PyLabRobot raised {type(r.exc).__name__}: {r.exc}"
    assert _text_of(root, "praxis-error__title") == sentence  # the heading IS PLR's sentence
    assert data["text/plain"].startswith(sentence)
    assert not root.find_all(None, "praxis-error__body")
    assert not root.find_all(None, "praxis-error__fix")
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
        assert not root.find_all(None, "praxis-error__body") and not root.find_all("svg")


# --------------------------------------------------------------------------- the step line (D9)


def test_the_step_line_names_the_step_when_one_is_given(errors):
    _d, _m, root = _render(errors, "E1", step=4)
    assert _text_of(root, "praxis-error__step") == "Step 4 of the run."


def test_no_step_line_without_a_step(errors):
    _d, _m, root = _render(errors, "E1")
    assert not root.find_all(None, "praxis-error__step")


def test_the_step_line_comes_first_in_the_text_and_in_the_panel(errors):
    data, _m, root = _render(errors, "E1", step=2)
    assert data["text/plain"].startswith("Step 2 of the run.")
    order = [n.attrs["class"] for n in root.walk()
             if n.attrs.get("class") in ("praxis-error__step", "praxis-error__title")]
    assert order == ["praxis-error__step", "praxis-error__title"]


def test_the_generic_panel_also_names_the_step(errors):
    _d, _m, root = _render(errors, "E13", step=3)
    assert _text_of(root, "praxis-error__step") == "Step 3 of the run."


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
        assert _text_of(root, "praxis-error__plr") == f"PyLabRobot raised {type(exc).__name__}: {payload}"
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
    first, tail = body.split("\n", 1)
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
    monkeypatch.setattr(errors, "_finish", lambda *a, **k: None)  # never reaches _showtraceback
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
    assert _text_of(root, "praxis-error__step") == "Step 4 of the run."
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
        body = _text_of(root, "praxis-error__body")
        assert gl.action_name(op) in body, (name, body)
    _d, _m, root = _render(errors, "E16")
    assert gl.verb_form("discard_tips") in _text_of(root, "praxis-error__fix")
    assert gl.action_name("pick_up_tips") in _text_of(root, "praxis-error__fix")
