"""Browserless tests for ``praxis/display/install.py`` and ``praxis/display/__init__.py`` (task B8, backlog
#5644; spec ``260929_notebook-display-epic.md`` D2 (registration), D7 (session and announcer wiring), D8
and D9 (error handler and ledger wiring), D13, AC-17, AC-20's install half, and the sprint notes "For B8").

**What ``install()`` is.** One call, in the kernel, that (1) mints the display session id once per kernel
process, (2) registers the D2 formatters for ``Plate``, ``TipRack``, ``Deck`` and ``Container`` (a
``Well`` is a ``Container``; an ``EmbeddedTipRack`` is a ``TipRack``, resolved by the shell's MRO, never by
a type-name string), (3) wraps the shell INSTANCE's ``showtraceback`` for the four PLR errors (S3-C; B6's
``errors.install``), (4) configures the ledger's session and exec-count seam, and (5) hooks the D7
announcer (``post_run_cell`` as an optimisation; the debounced ``loop.call_later`` timer is the real path,
S3-D). It is idempotent, returns a handle whose ``uninstall()`` restores the shell, and rolls back what it
did if a step fails.

**Carrier.** The spike (S3, run a3458bf2) measured S3-A: ``mimebundle_formatter.for_type(cls, fn)`` returning
``(data, metadata)`` puts the stamp at ``metadata["praxis"]``. The S3-B fallback (separate ``text/html`` and
``text/plain`` registration, the html function returning ``(html, {"praxis": stamp})``) is selected when the
shell lacks the primary API or the primary registration raises, and is tested here against fakes that lack
it. Both carriers are read through one accessor (``stamp_of``, the Python twin of the shell's ``stampOf``).

**Fakes, not IPython** (it is not in the project venv). ``FakeShell`` models what S3 MEASURED (IPython 9.12.0
and ``pyodide_kernel-0.8.2``): ``DisplayFormatter.format`` reads the mimebundle formatter, then the per-mime
formatters (a registered one wins, and a ``(data, metadata)`` return is unpacked to ``metadata[mime]``);
``run_code`` calls ``self.showtraceback(...)`` looked up on the INSTANCE, in a plain cell and in a
top-level-``await`` cell; the default ``showtraceback`` ends in ``self._showtraceback``, which is what makes
the cell an error output; ``set_custom_exc`` is recorded and never used.

**Real PLR at the 1.0.0b1 pin** for every drawing and every error (the venv's editable PLR can be the old
0.2.2, so the first fixture asserts the version; run with ``PYTHONPATH=<PLR 1.0.0b1 source>``). Scenarios E1,
E13 and E15 are B5/B6's setups.

**Import discipline** (ADR 260817 Sec 2.4): ``praxis/display`` is loaded by path under the synthetic package
``_praxis_display_under_test`` and ``web-repl/overlay/assets/python`` is never put on ``sys.path``. ``install``
and ``__init__`` must import in plain CPython, under ``-I -W error``, with no PLR, IPython or ``js``.
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
import types
from pathlib import Path

import pylabrobot
import pytest
from pylabrobot.legacy.liquid_handling import LiquidHandler
from pylabrobot.resources import (
    Container,
    Deck,
    Plate,
    TipRack,
    Well,
    does_tip_tracking,
    does_volume_tracking,
    set_tip_tracking,
    set_volume_tracking,
)
from pylabrobot.resources.errors import TooLittleLiquidError, TooLittleVolumeError
from pylabrobot.resources.hamilton import (
    Trough_CAR_5R60_A00,
    hamilton_1_trough_60mL_Vb,
)

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL = _TESTS_DIR.parent
_DISPLAY_DIR = _WEB_REPL / "overlay" / "assets" / "python" / "praxis" / "display"
_INSTALL_PATH = _DISPLAY_DIR / "install.py"
_INIT_PATH = _DISPLAY_DIR / "__init__.py"
_FIXTURE_PATH = _WEB_REPL / "design" / "notebook-display" / "make_fixture.py"
_PKG = "_praxis_display_under_test"

CAP = 65_536

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


def _sibling(name):
    _package()
    return importlib.import_module(f"{_PKG}.{name}")


@pytest.fixture(scope="module", autouse=True)
def _plr_is_the_pin():
    """A wrong PLR must fail loudly, never pass silently (the venv may carry 0.2.2)."""
    version = str(getattr(pylabrobot, "__version__", ""))
    assert version.startswith("1.0.0b1"), (
        f"PyLabRobot {version!r} at {pylabrobot.__file__} is not the 1.0.0b1 pin; "
        "run with PYTHONPATH=<PLR 1.0.0b1 source> prepended"
    )


@pytest.fixture(scope="module")
def inst():
    """praxis/display/install.py. A missing module is the RED reason."""
    if not _INSTALL_PATH.is_file():
        pytest.fail(f"praxis/display/install.py does not exist yet: {_INSTALL_PATH}")
    _package()
    return importlib.import_module(f"{_PKG}.install")


@pytest.fixture(scope="module")
def lw():
    return _sibling("labware")


@pytest.fixture(scope="module")
def dk():
    return _sibling("deck")


@pytest.fixture(scope="module")
def led():
    return _sibling("ledger")


@pytest.fixture(scope="module")
def stale():
    return _sibling("stale")


@pytest.fixture(scope="module")
def svg():
    return _sibling("svg")


@pytest.fixture(autouse=True)
def _restore_state():
    """PLR tracking is a global; ``install`` keeps module state (the installed handles, the process
    session id); the ledger has a module-level configure seam. No test may leak into the next."""
    tip, vol = does_tip_tracking(), does_volume_tracking()
    yield
    set_tip_tracking(tip)
    set_volume_tracking(vol)
    module = sys.modules.get(f"{_PKG}.install")
    if module is not None:
        for handle in list(getattr(module, "_INSTALLED", {}).values()):
            handle.uninstall()
    ledger = sys.modules.get(f"{_PKG}.ledger")
    if ledger is not None:
        ledger.configure()
        ledger._ERROR_STEPS.clear()


# --------------------------------------------------------------------------- the fake shell


_MISSING = object()


class FakeFormatter:
    """IPython's ``BaseFormatter`` reduced to what registration uses: ``for_type`` (returns the old
    function), ``pop``, and an MRO ``lookup``."""

    def __init__(self):
        self.type_printers: dict = {}
        self.for_type_calls = 0

    def for_type(self, typ, func=None):
        self.for_type_calls += 1
        old = self.type_printers.get(typ)
        if func is not None:
            self.type_printers[typ] = func
        return old

    def pop(self, typ, default=_MISSING):
        try:
            return self.type_printers.pop(typ)
        except KeyError:
            if default is _MISSING:
                raise
            return default

    def lookup(self, obj):
        for t in type(obj).__mro__:
            if t in self.type_printers:
                return self.type_printers[t]
        raise KeyError(type(obj))


class RaisingFormatter(FakeFormatter):
    """A mimebundle formatter whose ``for_type`` fails: the primary carrier is unusable."""

    def for_type(self, typ, func=None):
        raise RuntimeError("for_type is not supported on this formatter")


class FlakyFormatter(FakeFormatter):
    """A mimebundle formatter whose third ``for_type`` raises: a primary registration that fails half way."""

    def for_type(self, typ, func=None):
        if self.for_type_calls >= 2:
            raise RuntimeError("the third registration fails")
        return super().for_type(typ, func)


class _Printer:
    def __init__(self):
        self.buf: list[str] = []

    def text(self, s):
        self.buf.append(s)


class FakeDisplayFormatter:
    """IPython ``DisplayFormatter.format`` (core/formatters.py), as the S3 spike's fake models it."""

    def __init__(self, mimebundle):
        if mimebundle is not None:  # a shell without the primary API has no such attribute at all
            self.mimebundle_formatter = mimebundle
        self.formatters = {"text/plain": FakeFormatter(), "text/html": FakeFormatter()}

    def format(self, obj):
        data: dict = {}
        md: dict = {}
        bundle_fn = None
        mimebundle = getattr(self, "mimebundle_formatter", None)
        if mimebundle is not None:
            try:
                bundle_fn = mimebundle.lookup(obj)
            except KeyError:
                bundle_fn = None
        if bundle_fn is not None:
            result = bundle_fn(obj)
        else:
            method = getattr(obj, "_repr_mimebundle_", None)
            result = method(include=None, exclude=None) if method else None
        if result is not None:
            data, md = result if isinstance(result, tuple) else (result, {})
            data, md = dict(data), dict(md)
        for mime, formatter in self.formatters.items():
            try:
                registered = formatter.lookup(obj)
            except KeyError:
                registered = None
            if mime in data and registered is None:
                continue
            one_md = None
            if registered is not None:
                if mime == "text/plain":
                    printer = _Printer()
                    registered(obj, printer, False)  # IPython's pretty-printer signature
                    value = "".join(printer.buf)
                else:
                    value = registered(obj)
                    if isinstance(value, tuple) and len(value) == 2:
                        value, one_md = value
            elif mime == "text/plain":
                value = repr(obj)
            else:
                method = getattr(obj, "_repr_html_", None)
                value = method() if method else None
            if value is not None:
                data[mime] = value
            if one_md is not None:
                md[mime] = one_md
        return data, md


class FakeEvents:
    def __init__(self):
        self.callbacks: dict[str, list] = {}
        self.register_calls = 0

    def register(self, name, fn):
        self.register_calls += 1
        self.callbacks.setdefault(name, []).append(fn)

    def unregister(self, name, fn):
        self.callbacks[name].remove(fn)

    def trigger(self, name, *args):
        for fn in list(self.callbacks.get(name, [])):
            fn(*args)


class FakeShell:
    """The parts of IPython 9.12's ``InteractiveShell`` and pyodide-kernel's ``Interpreter`` S3 MEASURED.

    ``carrier``: ``"mimebundle"`` (the primary API works), ``"absent"`` (no ``mimebundle_formatter`` at
    all), ``"raises"`` (its ``for_type`` raises) or ``"flaky"`` (it raises on the third registration). ``events=False`` models a shell with no event manager.
    """

    def __init__(self, carrier="mimebundle", events=True):
        mimebundle = {"mimebundle": FakeFormatter, "absent": lambda: None, "raises": RaisingFormatter,
                       "flaky": FlakyFormatter}[carrier]()
        self.display_formatter = FakeDisplayFormatter(mimebundle)
        if events:
            self.events = FakeEvents()
        self.execution_count = 1
        self.custom_exc_calls: list = []
        self.default_calls: list = []
        self.outputs: list[dict] = []
        self._last_traceback = None

    # -- the API install() touches ------------------------------------------------
    def set_custom_exc(self, exc_tuple, handler):
        self.custom_exc_calls.append((exc_tuple, handler))

    def showtraceback(self, exc_tuple=None, filename=None, tb_offset=None, exception_only=False,
                      running_compiled_code=False):
        etype, value, _tb = exc_tuple or sys.exc_info()
        self.default_calls.append(value)
        if etype is None:
            return
        self._showtraceback(etype, value, [f"---- Traceback ----\n{etype.__name__}: {value}"])

    def _showtraceback(self, etype, evalue, stb):
        self._last_traceback = {"ename": etype.__name__, "evalue": str(evalue), "traceback": stb}

    # -- display() ------------------------------------------------------------------
    def display(self, obj, *args, raw=False, metadata=None, **kwargs):
        if raw:
            data, md = dict(obj), dict(metadata or {})
        else:
            data, md = self.display_formatter.format(obj)
            md.update(metadata or {})
        self.outputs.append({"output_type": "display_data", "data": data, "metadata": md})

    # -- what run_code does -----------------------------------------------------------
    def _run_plain(self, cell):
        self._last_traceback = None
        try:
            cell()
        except BaseException:
            self.showtraceback(running_compiled_code=True)
        return self._finish_cell()

    async def _run_await(self, cell):
        self._last_traceback = None
        try:
            await cell()
        except BaseException:
            self.showtraceback(running_compiled_code=True)
        return self._finish_cell()

    def _finish_cell(self):
        out = {"outputs": list(self.outputs), "error": self._last_traceback}
        self.outputs.clear()
        self.execution_count += 1
        return out

    def run(self, cell, mode):
        if mode == "plain":
            return self._run_plain(cell)
        return asyncio.run(self._run_await(cell))


class FakeHandle:
    def __init__(self, delay, cb):
        self.delay, self.cb, self.cancelled = delay, cb, False

    def cancel(self):
        self.cancelled = True


class FakeLoop:
    """Anything with ``call_later(delay, cb) -> handle``: the debounced announcer's seam."""

    def __init__(self):
        self.timers: list[FakeHandle] = []

    def call_later(self, delay, cb):
        handle = FakeHandle(delay, cb)
        self.timers.append(handle)
        return handle

    def live(self):
        return [t for t in self.timers if not t.cancelled]

    def fire(self):
        """Fire every live timer once (what ``loop.call_later`` does after the debounce)."""
        due = self.live()
        for t in due:
            t.cancelled = True
            t.cb()
        return len(due)


class Recorder:
    """A ``display`` for install(): records its calls and forwards them to the fake shell."""

    def __init__(self, shell):
        self.shell = shell
        self.calls: list[dict] = []

    def __call__(self, obj, *args, raw=False, metadata=None, **kwargs):
        self.calls.append({"obj": obj, "raw": raw, "metadata": metadata})
        self.shell.display(obj, raw=raw, metadata=metadata)


def stamp_of(output):
    """The Python twin of the shell's ``stampOf`` (D2): ``metadata.praxis`` else
    ``metadata["text/html"].praxis``; ``None`` when neither carries one."""
    md = output["metadata"]
    if md.get("praxis") is not None:
        return md["praxis"]
    carrier = md.get("text/html")
    return carrier.get("praxis") if isinstance(carrier, dict) else None


def make(inst_module, *, carrier="mimebundle", events=True, loop=True, **kw):
    """A fake shell, a poster list and (optionally) a fake loop, with ``install`` already run."""
    shell = FakeShell(carrier=carrier, events=events)
    posted: list[str] = []
    fake_loop = FakeLoop() if loop else None
    rec = Recorder(shell)
    handle = inst_module.install(shell, post=posted.append, loop=fake_loop, display=rec, **kw)
    return shell, handle, posted, fake_loop, rec


# --------------------------------------------------------------------------- PLR worlds

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


async def _world():
    deck, lh = await _fx().assemble()
    return deck, lh, deck.get_resource("tips_300"), deck.get_resource("source"), deck.get_resource("assay")


def world():
    return asyncio.run(_world())


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


async def _e1():
    """80 uL from assay A1:H1, which holds 50 (TooLittleLiquid; the fixture's error cell)."""
    deck, lh, tips, source, assay = await _world()
    await lh.pick_up_tips(tips["A1:H1"])
    await lh.aspirate(source["A1:H1"], vols=[50.0] * 8)
    await lh.dispense(assay["A1:H1"], vols=[50.0] * 8)
    return await _catch(lh.aspirate(assay["A1:H1"], vols=[80.0] * 8))


async def _e13():
    """Residue from direct tracker use (committed 100, pending 90): 95 <= 100 yet PLR raises (B5's E13)."""
    deck, lh, tips, _source, _assay = await _world()
    trough = _add_trough(deck)
    await lh.pick_up_tips([tips.get_item("A1")])
    trough.tracker.set_volume(100)
    trough.tracker.remove_liquid(10.0)  # direct, NOT committed
    exc = await _catch(lh.aspirate([trough], vols=[95.0], use_channels=[0]))
    assert str(exc) == "Not enough liquid in container: 95.0uL > 90.0uL."
    return exc


async def _e15():
    """Tip-side residue from direct tracker use: committed room 360, pending room 160 (B5's E15)."""
    deck, lh, tips, source, _assay = await _world()
    await lh.pick_up_tips([tips.get_item("A1")])
    tip = lh.head[0].get_tip()
    tip.tracker.add_liquid(200)  # direct, NOT committed
    well = source.get_item("A1")
    well.tracker.set_volume(300)
    return await _catch(lh.aspirate([well], vols=[200.0], use_channels=[0]))


_CASES: dict = {}


def case(name):
    if name not in _CASES:
        _CASES[name] = asyncio.run({"E1": _e1, "E13": _e13, "E15": _e15}[name]())
    return _CASES[name]


def _raiser(exc, mode):
    if mode == "plain":
        def cell():
            raise exc
    else:
        async def cell():
            await asyncio.sleep(0)
            raise exc
    return cell


MODES = ["plain", "await"]


# --------------------------------------------------------------------------- the public API


def test_the_public_api(inst):
    assert set(inst.__all__) >= {"install", "render", "Installed"}
    for name in ("install", "render"):
        assert callable(getattr(inst, name))
    params = inspect.signature(inst.install).parameters
    assert list(params)[0] == "shell" and params["shell"].default is None
    for name in ("post", "loop", "session_id", "display", "resolver"):
        assert params[name].kind is inspect.Parameter.KEYWORD_ONLY and params[name].default is None, name


def test_the_four_display_classes(inst):
    assert set(inst.display_classes()) == {Plate, TipRack, Deck, Container}


def test_install_returns_a_handle(inst):
    shell, handle, _posted, _loop, _rec = make(inst)
    assert isinstance(handle, inst.Installed)
    assert handle.shell is shell and handle.active is True
    assert handle.carrier == inst.CARRIER_MIMEBUNDLE
    assert re.fullmatch(r"[0-9a-f]{16}", handle.session_id)
    assert handle.session.session_id == handle.session_id


# --------------------------------------------------------------------------- registration: the primary carrier (S3-A)


def test_exactly_the_four_classes_are_registered_on_the_mimebundle_formatter(inst):
    shell, _h, _p, _l, _r = make(inst)
    mb = shell.display_formatter.mimebundle_formatter
    assert set(mb.type_printers) == {Plate, TipRack, Deck, Container}
    assert shell.display_formatter.formatters["text/html"].type_printers == {}
    assert shell.display_formatter.formatters["text/plain"].type_printers == {}
    assert shell.custom_exc_calls == [], "set_custom_exc is never the carrier (S3-C)"


def test_a_plate_is_displayed_with_the_stamp_at_metadata_praxis(inst, lw):
    shell, handle, _p, _l, _r = make(inst)
    _deck, _lh, _tips, _source, assay = world()
    shell.display(assay)
    (out,) = shell.outputs
    assert set(out["data"]) == {"text/html", "text/plain"}
    assert "<svg" in out["data"]["text/html"] and len(out["data"]["text/html"].encode()) <= CAP
    assert out["metadata"]["praxis"] is stamp_of(out)
    assert "text/html" not in out["metadata"], "the primary carrier puts the stamp at the top level only"
    assert stamp_of(out) == {"v": 1, "kind": "plate", "resource": "assay", "rev": 0,
                             "session": handle.session_id, "exec": shell.execution_count}
    assert out["data"]["text/plain"] == lw.sentence(assay)


def test_a_tip_rack_and_an_embedded_tip_rack_resolve_to_the_tip_rack_formatter(inst):
    shell, handle, _p, _l, _r = make(inst)
    _deck, _lh, tips, _source, _assay = world()
    assert type(tips).__name__ == "EmbeddedTipRack" and type(tips) is not TipRack and isinstance(tips, TipRack)
    shell.display(tips)
    (out,) = shell.outputs
    assert stamp_of(out)["kind"] == "tiprack" and stamp_of(out)["resource"] == "tips_300"
    assert "<svg" in out["data"]["text/html"]
    # resolved by class through the MRO: the registration is for TipRack, not for the subclass
    assert TipRack in shell.display_formatter.mimebundle_formatter.type_printers
    assert type(tips) not in shell.display_formatter.mimebundle_formatter.type_printers


def test_a_deck_is_displayed_as_a_deck(inst):
    shell, handle, _p, _l, _r = make(inst)
    deck, _lh, _tips, _source, _assay = world()
    shell.display(deck)
    (out,) = shell.outputs
    assert stamp_of(out)["kind"] == "deck" and stamp_of(out)["resource"] == deck.name
    assert stamp_of(out)["session"] == handle.session_id
    assert "<svg" in out["data"]["text/html"] and len(out["data"]["text/html"].encode()) <= CAP


def test_a_well_and_other_containers_go_through_the_container_formatter(inst, lw):
    shell, _h, _p, _l, _r = make(inst)
    deck, _lh, _tips, _source, assay = world()
    well, trough = assay.get_item("A1"), _add_trough(deck)
    shell.display(well)
    shell.display(trough)
    well_out, trough_out = shell.outputs
    for out, res in ((well_out, well), (trough_out, trough)):
        assert stamp_of(out)["kind"] == "container" and stamp_of(out)["resource"] == res.name
        assert out["data"]["text/plain"] == lw.sentence(res)
    assert "<svg" not in trough_out["data"]["text/html"], "a container that is not a Well is sentence-only (D2)"


def test_an_unregistered_object_is_left_alone(inst):
    shell, _h, _p, _l, _r = make(inst)
    _deck, lh, _tips, _source, _assay = world()
    shell.display(lh)
    (out,) = shell.outputs
    assert stamp_of(out) is None and out["data"]["text/plain"] == repr(lh)


def test_a_subclass_of_a_registered_class_resolves_by_the_mro(inst):
    shell, _h, _p, _l, _r = make(inst)

    class MyPlate(Plate):
        pass

    _deck, _lh, _tips, _source, assay = world()
    assert shell.display_formatter.mimebundle_formatter.lookup(MyPlate.__new__(MyPlate)) is not None
    shell.display(assay)
    assert stamp_of(shell.outputs[0])["kind"] == "plate"


def test_a_formatter_that_fails_degrades_to_the_default_repr_never_raises(inst, monkeypatch):
    shell, _h, _p, _l, _r = make(inst)
    _deck, _lh, _tips, _source, assay = world()
    monkeypatch.setattr(inst.labware, "render", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    fn = shell.display_formatter.mimebundle_formatter.lookup(assay)
    assert fn(assay) is None  # IPython then falls back to the default repr


def test_render_returns_the_bundle_for_explicit_use(inst, lw):
    _deck, _lh, _tips, _source, assay = world()
    data, metadata = inst.render(assay)
    assert set(data) == {"text/html", "text/plain"}
    assert metadata["praxis"]["kind"] == "plate" and metadata["praxis"]["resource"] == "assay"
    assert re.fullmatch(r"[0-9a-f]{16}", metadata["praxis"]["session"])
    with pytest.raises(TypeError):
        inst.render(object())


def test_render_agrees_with_the_installed_formatter(inst):
    shell, _h, _p, _l, _r = make(inst)
    _deck, _lh, _tips, _source, assay = world()
    shell.display(assay)
    installed = shell.outputs[0]
    data, metadata = inst.render(assay)
    assert data == installed["data"] and metadata["praxis"] == stamp_of(installed)


# --------------------------------------------------------------------------- the ledger


def test_the_ledger_stamp_carries_the_shared_session_and_exec(inst, led):
    shell, handle, _p, _l, _r = make(inst)
    shell.execution_count = 7
    _deck, lh, _tips, _source, _assay = world()
    run = led.RunLedger(lh, show=False)
    shell.display(run)  # through the formatter: RunLedger's own _repr_mimebundle_
    (out,) = shell.outputs
    assert stamp_of(out) == {"v": 1, "kind": "ledger", "resource": None, "rev": None,
                             "session": handle.session_id, "exec": 7}


def test_without_install_a_bare_ledger_says_unset_and_after_uninstall_it_is_unset_again(inst, led):
    _deck, lh, _tips, _source, _assay = world()
    assert led.RunLedger(lh, show=False).bundle()[1]["praxis"]["session"] == "unset"
    shell, handle, _p, _l, _r = make(inst)
    assert led.RunLedger(lh, show=False).bundle()[1]["praxis"]["session"] == handle.session_id
    handle.uninstall()
    assert led.RunLedger(lh, show=False).bundle()[1]["praxis"]["session"] == "unset"


# --------------------------------------------------------------------------- the S3-B fallback carrier


@pytest.mark.parametrize("carrier", ["absent", "raises", "flaky"])
def test_the_fallback_is_selected_when_the_primary_api_is_missing_or_unusable(inst, carrier):
    shell, handle, _p, _l, _r = make(inst, carrier=carrier)
    assert handle.carrier == inst.CARRIER_FORMATTERS
    html, plain = (shell.display_formatter.formatters[m] for m in ("text/html", "text/plain"))
    assert {Plate, TipRack, Deck, Container} <= set(html.type_printers)
    assert set(html.type_printers) == set(plain.type_printers)
    mb = getattr(shell.display_formatter, "mimebundle_formatter", None)
    assert mb is None or mb.type_printers == {}, "nothing half-registered is left on the primary formatter"


def test_the_fallback_html_function_returns_a_tuple_with_the_same_stamp_as_render(inst, lw):
    shell, handle, _p, _l, _r = make(inst, carrier="absent")
    _deck, _lh, _tips, _source, assay = world()
    html_fn = shell.display_formatter.formatters["text/html"].lookup(assay)
    plain_fn = shell.display_formatter.formatters["text/plain"].lookup(assay)
    result = html_fn(assay)
    assert isinstance(result, tuple) and len(result) == 2
    html, md = result
    data, metadata = inst.render(assay)
    assert set(md) == {"praxis"} and md["praxis"] == metadata["praxis"]
    assert html == data["text/html"]
    assert plain_fn(assay) == lw.sentence(assay) == data["text/plain"]  # returns the summary sentence


def test_the_fallback_plain_function_also_speaks_ipythons_pretty_printer_signature(inst, lw):
    shell, _h, _p, _l, _r = make(inst, carrier="absent")
    _deck, _lh, _tips, _source, assay = world()
    plain_fn = shell.display_formatter.formatters["text/plain"].lookup(assay)
    printer = _Printer()
    plain_fn(assay, printer, False)
    assert "".join(printer.buf) == lw.sentence(assay)


def test_under_the_fallback_the_stamp_rides_at_metadata_text_html_praxis(inst, svg):
    shell, handle, _p, _l, _r = make(inst, carrier="absent")
    _deck, _lh, tips, _source, assay = world()
    shell.display(assay)
    shell.display(tips)
    for out, kind in zip(shell.outputs, ("plate", "tiprack"), strict=True):
        assert "praxis" not in out["metadata"], "the S3-B carrier is per-mime, not top-level"
        assert out["metadata"]["text/html"]["praxis"] is stamp_of(out)
        assert stamp_of(out)["kind"] == kind and stamp_of(out)["session"] == handle.session_id
        svg.check_bundle(out["data"], out["metadata"])  # the validator reads either carrier
        assert set(out["data"]) == {"text/html", "text/plain"}


def test_the_fallback_covers_the_deck_the_embedded_tip_rack_and_the_ledger(inst, led):
    shell, handle, _p, _l, _r = make(inst, carrier="raises")
    deck, lh, tips, _source, _assay = world()
    for obj in (deck, tips, led.RunLedger(lh, show=False)):
        shell.display(obj)
    kinds = [stamp_of(o)["kind"] for o in shell.outputs]
    assert kinds == ["deck", "tiprack", "ledger"]
    assert {stamp_of(o)["session"] for o in shell.outputs} == {handle.session_id}


def test_the_carrier_tests_are_not_the_same_path(inst):
    """Negative control: the two carriers produce the stamp at different places, so a reader that only
    knew one location would fail the other."""
    primary, _h1, _p1, _l1, _r1 = make(inst)
    fallback, _h2, _p2, _l2, _r2 = make(inst, carrier="absent")
    _deck, _lh, _tips, _source, assay = world()
    primary.display(assay)
    fallback.display(assay)
    assert "praxis" in primary.outputs[0]["metadata"] and "text/html" not in primary.outputs[0]["metadata"]
    assert "praxis" not in fallback.outputs[0]["metadata"] and "text/html" in fallback.outputs[0]["metadata"]
    assert stamp_of(primary.outputs[0])["kind"] == stamp_of(fallback.outputs[0])["kind"]


# --------------------------------------------------------------------------- one session id, everywhere


def test_one_session_id_is_shared_by_every_stamp_and_the_announcement(inst, led):
    shell, handle, posted, loop, _rec = make(inst)
    shell.execution_count = 3
    _deck, lh, _tips, source, assay = world()
    shell.display(assay)  # a plate stamp
    shell.display(led.RunLedger(lh, show=False))  # a ledger stamp
    shell.display(source)  # a second plate, which is then changed
    out = shell.run(_raiser(case("E1"), "plain"), "plain")  # an error stamp, through the wrapped showtraceback
    stamps = [stamp_of(o) for o in out["outputs"]]
    assert [s["kind"] for s in stamps] == ["plate", "ledger", "plate", "error"]
    assert {s["session"] for s in stamps} == {handle.session_id}
    assert handle.session.session_id == handle.session_id
    source.get_item("A1").tracker.set_volume(120)
    assert loop.fire() == 1
    (message,) = posted
    assert json.loads(message)["session"] == handle.session_id


def test_the_session_id_is_minted_once_per_process_and_survives_uninstall(inst):
    _s1, h1, _p1, _l1, _r1 = make(inst)
    first = h1.session_id
    h1.uninstall()
    _s2, h2, _p2, _l2, _r2 = make(inst)
    _s3, h3, _p3, _l3, _r3 = make(inst)  # a second shell object at the same time
    assert h2.session_id == first == h3.session_id


def test_an_explicit_session_id_wins(inst):
    _shell, handle, _p, _l, _r = make(inst, session_id="fixed-session")
    assert handle.session_id == "fixed-session" and handle.session.session_id == "fixed-session"


def test_exec_is_the_shells_execution_count_read_at_render_time(inst):
    shell, _h, _p, _l, _r = make(inst)
    _deck, _lh, _tips, _source, assay = world()
    for n in (1, 5):
        shell.execution_count = n
        shell.display(assay)
    assert [stamp_of(o)["exec"] for o in shell.outputs] == [1, 5]


# --------------------------------------------------------------------------- staleness wiring (D7)


def test_a_drawn_plate_that_changes_is_announced_once_after_the_debounce(inst):
    shell, handle, posted, loop, _r = make(inst)
    _deck, _lh, _tips, source, _assay = world()
    shell.display(source)
    assert stamp_of(shell.outputs[0])["rev"] == 0
    source.get_item("A1").tracker.set_volume(120)  # 200 -> 120: changes what is drawn
    live = loop.live()
    assert len(live) == 1 and live[0].delay == pytest.approx(0.1), "the debounced timer is scheduled (S3-D)"
    assert posted == []
    assert loop.fire() == 1
    (message,) = posted
    body = json.loads(message)
    assert body == {"session": handle.session_id, "exec": shell.execution_count, "revs": {"source": 1}}
    shell.display(source)
    assert stamp_of(shell.outputs[1])["rev"] == 1


def test_a_change_to_something_never_drawn_announces_nothing(inst):
    shell, _h, posted, loop, _r = make(inst)
    _deck, _lh, _tips, source, assay = world()
    shell.display(source)
    assay.get_item("A1").tracker.set_volume(33)
    assert loop.live() == [] and posted == []


def test_post_run_cell_is_registered_once_as_an_optimisation_and_flushes_at_once(inst):
    shell, handle, posted, loop, _r = make(inst)
    assert len(shell.events.callbacks["post_run_cell"]) == 1
    _deck, _lh, _tips, source, _assay = world()
    shell.display(source)
    source.get_item("A1").tracker.set_volume(120)
    shell.events.trigger("post_run_cell", object())
    assert len(posted) == 1 and json.loads(posted[0])["revs"] == {"source": 1}
    assert loop.fire() == 0, "the pending timer was cancelled by the flush"
    assert len(posted) == 1


def test_the_debounced_timer_alone_announces_when_post_run_cell_never_fires(inst):
    """S3-D: ``post_run_cell`` does not fire for top-level-await cells. Nothing triggers it here."""
    shell, _h, posted, loop, _r = make(inst)
    _deck, _lh, _tips, source, _assay = world()
    shell.display(source)
    source.get_item("A2").tracker.set_volume(11)
    assert loop.fire() == 1 and len(posted) == 1


def test_a_shell_with_no_event_manager_still_installs_and_announces(inst):
    shell, handle, posted, loop, _r = make(inst, events=False)
    assert handle.active and not hasattr(shell, "events")
    _deck, _lh, _tips, source, _assay = world()
    shell.display(source)
    source.get_item("A2").tracker.set_volume(11)
    assert loop.fire() == 1 and len(posted) == 1


def test_the_default_loop_announces_from_a_real_running_loop(inst):
    """No ``loop=`` injected: the announcer resolves the running asyncio loop when a callback fires."""

    async def go():
        shell = FakeShell()
        posted: list[str] = []
        handle = inst.install(shell, post=posted.append, display=Recorder(shell))
        _deck, _lh, _tips, source, _assay = await _world()
        shell.display(source)
        source.get_item("A1").tracker.set_volume(120)
        assert posted == []
        await asyncio.sleep(0.4)
        return handle, posted

    handle, posted = asyncio.run(go())
    assert len(posted) == 1 and json.loads(posted[0])["revs"] == {"source": 1}


def test_the_default_poster_builds_the_praxis_repl_message(inst, monkeypatch):
    """With no ``post=``, the real poster (``stale.make_repl_poster``) is used: a flat ``{type, json}``
    message on the ``praxis_repl`` channel, built with ``js.Object.fromEntries``."""
    channels: list = []

    class Chan:
        def __init__(self, name):
            self.name, self.posted = name, []

        def postMessage(self, obj):
            self.posted.append(obj)

    fake_js = types.ModuleType("js")
    fake_js.BroadcastChannel = types.SimpleNamespace(new=lambda name: channels.append(Chan(name)) or channels[-1])
    fake_js.Object = types.SimpleNamespace(fromEntries=lambda pairs: dict(pairs))
    monkeypatch.setitem(sys.modules, "js", fake_js)
    shell = FakeShell()
    loop = FakeLoop()
    inst.install(shell, loop=loop, display=Recorder(shell))
    _deck, _lh, _tips, source, _assay = world()
    shell.display(source)
    source.get_item("A1").tracker.set_volume(120)
    loop.fire()
    (chan,) = channels
    assert chan.name == "praxis_repl"
    (message,) = chan.posted
    assert set(message) == {"type", "json"} and message["type"] == "praxis:resource-changed"
    assert json.loads(message["json"])["revs"] == {"source": 1}


def test_after_uninstall_nothing_is_announced(inst):
    shell, handle, posted, loop, _r = make(inst)
    _deck, _lh, _tips, source, _assay = world()
    shell.display(source)
    source.get_item("A1").tracker.set_volume(120)
    handle.uninstall()
    loop.fire()
    shell.events.trigger("post_run_cell", object())
    assert posted == []


# --------------------------------------------------------------------------- the error handler through install (AC-17)


@pytest.mark.parametrize("mode", MODES)
def test_e1_through_the_installed_handler_shows_the_panel_and_still_ends_in_an_error(inst, mode):
    shell, handle, _p, _l, rec = make(inst)
    exc = case("E1")
    out = shell.run(_raiser(exc, mode), mode)
    assert len(rec.calls) == 1 and rec.calls[0]["raw"] is True
    (panel,) = out["outputs"]
    stamp = stamp_of(panel)
    assert stamp["kind"] == "error" and stamp["rev"] is None and stamp["resource"] == "assay"
    assert stamp["session"] == handle.session_id and stamp["exec"] == 1
    assert out["error"] is not None
    assert out["error"]["traceback"] == [f"TooLittleLiquidError: {exc}"]  # a list of one string
    assert shell.default_calls == [] and shell.custom_exc_calls == []


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name,klass", [("E13", TooLittleLiquidError), ("E15", TooLittleVolumeError)])
def test_the_generic_panel_appears_for_e13_and_e15_through_the_installed_handler(inst, mode, name, klass):
    """AC-17: residue from direct tracker use is not the raise's cause in committed state, so the owner
    resolves to ``None`` and the panel is the generic one, whose stamp has ``resource`` null."""
    shell, handle, _p, _l, rec = make(inst)
    exc = case(name)
    assert type(exc) is klass
    out = shell.run(_raiser(exc, mode), mode)
    assert len(rec.calls) == 1
    (panel,) = out["outputs"]
    assert stamp_of(panel)["kind"] == "error" and stamp_of(panel)["resource"] is None
    assert stamp_of(panel)["session"] == handle.session_id
    assert panel["data"]["text/plain"] == f"PyLabRobot raised {klass.__name__}: {exc}"
    assert "praxis-error__title" in panel["data"]["text/html"]
    assert out["error"]["traceback"] == [f"{klass.__name__}: {exc}"]


def test_other_exceptions_are_delegated_untouched(inst):
    shell, _h, _p, _l, rec = make(inst)
    err = ValueError("plain")
    out = shell.run(_raiser(err, "plain"), "plain")
    assert rec.calls == [] and shell.default_calls == [err] and out["outputs"] == []
    assert out["error"] is not None


def test_a_run_ledger_shows_before_the_panel_and_the_panel_names_the_step(inst, led):
    """AC-17's order check with a real ``RunLedger`` (show on) around a failing op: the shell's outputs
    are the ledger bundle, then the panel; the panel names the step; the ``_ERROR_STEPS`` entry is gone."""
    shell, handle, _p, _l, rec = make(inst)
    box = {}

    async def cell():
        deck, lh, tips, source, assay = await _world()
        with led.RunLedger(lh, display=rec):
            await lh.pick_up_tips(tips["A1:H1"])
            await lh.aspirate(source["A1:H1"], vols=[50.0] * 8)
            await lh.dispense(assay["A1:H1"], vols=[50.0] * 8)
            try:
                await lh.aspirate(assay["A1:H1"], vols=[80.0] * 8)
            except TooLittleLiquidError as e:
                box["exc"] = e
                raise

    out = shell.run(cell, "await")
    assert [stamp_of(o)["kind"] for o in out["outputs"]] == ["ledger", "error"]
    assert {stamp_of(o)["session"] for o in out["outputs"]} == {handle.session_id}
    assert "Step 4 of the run." in out["outputs"][1]["data"]["text/html"]
    assert id(box["exc"]) not in led._ERROR_STEPS
    assert out["error"] is not None


# --------------------------------------------------------------------------- idempotency and uninstall


def test_a_second_install_returns_the_same_handle_and_registers_nothing_new(inst):
    shell, handle, _p, loop, rec = make(inst)
    calls_before = shell.display_formatter.mimebundle_formatter.for_type_calls
    events_before = shell.events.register_calls
    wrapper_before = shell.__dict__["showtraceback"]
    again = inst.install(shell, post=lambda s: None, loop=FakeLoop(), display=rec)
    assert again is handle
    assert shell.display_formatter.mimebundle_formatter.for_type_calls == calls_before
    assert shell.events.register_calls == events_before
    assert shell.__dict__["showtraceback"] is wrapper_before
    assert len(shell.events.callbacks["post_run_cell"]) == 1


def test_uninstall_restores_the_shell(inst, led):
    shell = FakeShell()
    original_showtraceback = shell.showtraceback  # the bound method a class provides
    posted: list = []
    handle = inst.install(shell, post=posted.append, loop=FakeLoop(), display=Recorder(shell))
    assert "showtraceback" in shell.__dict__
    handle.uninstall()
    assert handle.active is False
    assert shell.display_formatter.mimebundle_formatter.type_printers == {}
    assert shell.events.callbacks["post_run_cell"] == []
    assert "showtraceback" not in shell.__dict__ and shell.showtraceback == original_showtraceback
    handle.uninstall()  # idempotent


def test_uninstall_restores_a_formatter_that_was_already_registered(inst):
    shell = FakeShell()
    previous = lambda obj: ({"text/plain": "mine"}, {})  # noqa: E731 - someone else's registration
    shell.display_formatter.mimebundle_formatter.for_type(Plate, previous)
    handle = inst.install(shell, post=lambda s: None, loop=FakeLoop(), display=Recorder(shell))
    assert shell.display_formatter.mimebundle_formatter.type_printers[Plate] is not previous
    handle.uninstall()
    assert shell.display_formatter.mimebundle_formatter.type_printers == {Plate: previous}


def test_install_again_after_uninstall_works_and_keeps_the_session(inst):
    shell = FakeShell()
    rec = Recorder(shell)
    h1 = inst.install(shell, post=lambda s: None, loop=FakeLoop(), display=rec)
    h1.uninstall()
    h2 = inst.install(shell, post=lambda s: None, loop=FakeLoop(), display=rec)
    assert h2 is not h1 and h2.active and h2.session_id == h1.session_id
    assert len(shell.events.callbacks["post_run_cell"]) == 1
    assert set(shell.display_formatter.mimebundle_formatter.type_printers) == {Plate, TipRack, Deck, Container}


def test_install_with_no_shell_and_no_ipython_fails_loudly(inst, monkeypatch):
    monkeypatch.setitem(sys.modules, "IPython", None)  # `import IPython` -> ImportError
    with pytest.raises((ImportError, RuntimeError)):
        inst.install()


def test_a_failing_step_rolls_back_what_was_done_and_re_raises(inst, monkeypatch):
    shell = FakeShell()

    def boom(*a, **k):
        raise RuntimeError("errors.install exploded")

    monkeypatch.setattr(inst.errors, "install", boom)
    with pytest.raises(RuntimeError, match="errors.install exploded"):
        inst.install(shell, post=lambda s: None, loop=FakeLoop(), display=Recorder(shell))
    assert shell.display_formatter.mimebundle_formatter.type_printers == {}
    assert shell.events.callbacks.get("post_run_cell", []) == []
    assert "showtraceback" not in shell.__dict__
    led = _sibling("ledger")  # the ledger seam was reset: a bare ledger has no session
    _deck, lh, _tips, _source, _assay = world()
    assert led.RunLedger(lh, show=False).bundle()[1]["praxis"]["session"] == "unset"
    assert getattr(inst, "_INSTALLED", {}) == {}


def test_no_poster_in_plain_cpython_fails_loudly_and_leaves_the_shell_untouched(inst, monkeypatch):
    monkeypatch.setitem(sys.modules, "js", None)  # `import js` -> ImportError
    shell = FakeShell()
    with pytest.raises(ImportError):
        inst.install(shell, loop=FakeLoop(), display=Recorder(shell))
    assert shell.display_formatter.mimebundle_formatter.type_printers == {}
    assert "showtraceback" not in shell.__dict__


# --------------------------------------------------------------------------- imports and hygiene

_ENV_PIN = {"PYTHONPATH": str(Path(pylabrobot.__file__).resolve().parent.parent)}

_LOAD = f"""
import sys, types, importlib
pkg = types.ModuleType({_PKG!r}); pkg.__path__ = [{str(_DISPLAY_DIR)!r}]; pkg.__package__ = {_PKG!r}
sys.modules[{_PKG!r}] = pkg
"""


def _run_py(code, *flags):
    """A child CPython. ``-I`` ignores PYTHONPATH, so the PLR pin is deliberately NOT importable there:
    a module that imported PLR at import time would fail, not pass by luck."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run([sys.executable, *flags, "-c", code], capture_output=True, text=True, timeout=180,
                          check=False, env=env)


def test_install_imports_in_plain_cpython_under_isolated_warnings_as_errors():
    if not _INSTALL_PATH.is_file():
        pytest.fail(f"praxis/display/install.py does not exist yet: {_INSTALL_PATH}")
    code = _LOAD + f"""
m = importlib.import_module({_PKG!r} + '.install')
bad = [k for k in sys.modules if k.split('.')[0] in ('pylabrobot', 'IPython', 'js')]
assert not bad, bad
print('ok', m.install.__name__)
"""
    proc = _run_py(code, "-I", "-W", "error")
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip() == "ok install"


def test_the_package_init_exports_install_ledger_and_render_and_imports_in_plain_cpython():
    if not _INIT_PATH.is_file():
        pytest.fail(f"praxis/display/__init__.py does not exist yet: {_INIT_PATH}")
    code = f"""
import sys, importlib.util
name = '_praxis_display_pkg_under_test'
spec = importlib.util.spec_from_file_location(name, {str(_INIT_PATH)!r}, submodule_search_locations=[{str(_DISPLAY_DIR)!r}])
pkg = importlib.util.module_from_spec(spec)
sys.modules[name] = pkg
spec.loader.exec_module(pkg)
bad = [k for k in sys.modules if k.split('.')[0] in ('pylabrobot', 'IPython', 'js')]
assert not bad, bad
assert set(pkg.__all__) >= {{'install', 'RunLedger', 'render'}}, pkg.__all__
assert callable(pkg.install) and callable(pkg.render)
led = sys.modules[name + '.ledger']
ins = sys.modules[name + '.install']
assert pkg.RunLedger is led.RunLedger
assert pkg.install is ins.install and pkg.render is ins.render
print('ok')
"""
    proc = _run_py(code, "-I", "-W", "error")
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


def test_install_names_only_the_pins_non_shim_homes(inst):
    mods = _plr_imports(_INSTALL_PATH.read_text())
    assert mods <= ALLOWED_PLR_MODULES, mods - ALLOWED_PLR_MODULES
    assert "pylabrobot.resources" in mods


def _module_level_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    return {
        alias.name.split(".")[0] for node in tree.body if isinstance(node, ast.Import) for alias in node.names
    } | {
        (node.module or "").split(".")[0] for node in tree.body if isinstance(node, ast.ImportFrom) and node.level == 0
    }


@pytest.mark.parametrize("path", [_INSTALL_PATH, _INIT_PATH], ids=["install.py", "__init__.py"])
def test_no_module_level_plr_ipython_or_js_import(inst, path):
    assert not _module_level_roots(path) & {"pylabrobot", "IPython", "js"}


def test_the_channel_name_is_spelled_in_stale_py_only(inst):
    for path in (_INSTALL_PATH, _INIT_PATH):
        assert "praxis_repl" not in path.read_text(), path.name


def test_install_never_uses_set_custom_exc_as_the_carrier(inst):
    """S3-C: ``set_custom_exc``'s handler runs but its traceback does not become the error output."""
    calls = [
        n for n in ast.walk(ast.parse(_INSTALL_PATH.read_text()))
        if isinstance(n, ast.Attribute) and n.attr == "set_custom_exc"
    ]
    assert calls == []
