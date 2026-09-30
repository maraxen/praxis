"""Browserless tests for ``praxis/display/ledger.py`` (task B4, backlog #5638): ``RunLedger``, the
per-instance op wrappers, nesting, the run table, ``_ERROR_STEPS`` / ``step_for`` and the ledger
bundle. Closes AC-14 and the ledger half of AC-28 (with ``test_display_glossary.py``).

Spec: ``260929_notebook-display-epic.md`` D9 (``RunLedger`` is a context manager that shadows ONE
instance's methods; each wrapper records a row ``in-flight`` then ``ok`` or ``error`` and awaits
the original bound method; a wrapped op called while another is in flight becomes its child; steps,
tip cycles and uL moved count top-level rows only; ``__exit__`` deletes the instance attributes and,
unless ``show=False``, displays the ledger, on the error path too, without suppressing the
exception; a failed op stores ``(exc, step)`` in ``_ERROR_STEPS[id(exc)]`` and re-raises the SAME
exception; PLR's logger and event bus are not used), D2 (the bundle and its stamp: a ledger has
``resource: null`` and ``rev: null``), D4 (64 KiB cap, fixture ledger <= 32 KiB), section 3.3 (the
name line, the table, the after-state plate), section 3.5 (the glossary names) and AC-14.

**PyLabRobot.** AC-14 replays ``make_fixture.run_transfers`` on the REAL 1.0.0b1 pin, chatterbox
backend, through ``LiquidHandler`` from its non-shim home. The venv's editable PLR can be the old
0.2.2, which would make every replay meaningless, so the first test asserts the version. Run with
``PYTHONPATH=<PLR 1.0.0b1 source>`` prepended when the venv is not on the pin. Cases that do not
need PLR's own behaviour use ``FakeLH``, a duck-typed handler with PLR's op names and signatures
(and REAL PLR resources as arguments), so the ledger is also checked against exact call logs.

**Import discipline** (ADR 260817 Sec 2.4). ``praxis/display`` is loaded by path under the
synthetic package ``_praxis_display_under_test``; ``web-repl/overlay/assets/python`` is never put on
``sys.path``. The module under test must import in plain CPython with no PLR import at all.

**Controls.** Every property that could pass vacuously has a control that must FAIL:

* the transparency checker (return value, argument identity, exception identity, call log) is run
  against ledgers whose wrapper swallows an exception, drops a return, alters a return, wraps the
  exception, drops keyword arguments, copies arguments, or calls the op twice;
* the nesting checker against a ledger that records everything flat;
* the cleanliness checker against a ledger whose ``detach`` leaves its wrappers on the instance;
* the error-step checker against a ledger that never records the step;
* the class-only checker and the hostile-name checker against naive markup.
"""

from __future__ import annotations

import ast
import asyncio
import copy
import html as html_mod
import importlib
import importlib.util
import json
import re
import subprocess
import sys
import types
from html.parser import HTMLParser
from pathlib import Path

import pytest

import pylabrobot
from pylabrobot.legacy.liquid_handling import LiquidHandler

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL = _TESTS_DIR.parent
_DISPLAY_DIR = _WEB_REPL / "overlay" / "assets" / "python" / "praxis" / "display"
_LEDGER_PATH = _DISPLAY_DIR / "ledger.py"
_FIXTURE_PATH = _WEB_REPL / "design" / "notebook-display" / "make_fixture.py"
_PKG = "_praxis_display_under_test"

CAP = 65_536
FIXTURE_LEDGER_TARGET = 32 * 1024  # D4: "fixture ledger <= 32 KiB"

# The thirteen op names (section 3.5), spelled here on purpose: this is the oracle, and it is
# captured BEFORE the module under test is loaded.
OPS = [
    "pick_up_tips", "drop_tips", "return_tips", "discard_tips", "aspirate", "dispense", "transfer",
    "pick_up_tips96", "drop_tips96", "return_tips96", "discard_tips96", "aspirate96", "dispense96",
]
ORIGINALS = {name: LiquidHandler.__dict__[name] for name in OPS}

MOONSTONE, ROSE = "#73A9C2", "#ED7A9B"

HOSTILE_NAMES = [
    '<b>&"\'x',
    "</svg><script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "' onmouseover='alert(1)",
    "&amp;&lt;b&gt;",
    "<style>*{display:none}</style>",
    "µL \U0001f9ea 日本語",
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


@pytest.fixture(scope="module")
def led():
    """praxis/display/ledger.py. A missing module is the RED reason."""
    if not _LEDGER_PATH.is_file():
        pytest.fail(f"praxis/display/ledger.py does not exist yet: {_LEDGER_PATH}")
    _package()
    return importlib.import_module(f"{_PKG}.ledger")


@pytest.fixture(scope="module")
def gl(led):
    return importlib.import_module(f"{_PKG}.glossary")


@pytest.fixture(scope="module")
def svg(led):
    return importlib.import_module(f"{_PKG}.svg")


@pytest.fixture(scope="module")
def budget(led):
    return importlib.import_module(f"{_PKG}.budget")


@pytest.fixture(scope="module")
def fx():
    """The ported design fixture module (``assemble`` and ``run_transfers`` are what AC-14 replays)."""
    spec = importlib.util.spec_from_file_location("_praxis_make_fixture_under_test", _FIXTURE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_praxis_make_fixture_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _reset_module_state(request):
    """``configure`` and ``_ERROR_STEPS`` are module state; no test may leak into the next (the
    suite runs in random order)."""
    module = request.getfixturevalue("led") if "led" in request.fixturenames else None
    if module is not None:
        module.configure()
        module._ERROR_STEPS.clear()
    yield
    if module is not None:
        module.configure()
        module._ERROR_STEPS.clear()


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- a duck-typed handler


class FakeLH:
    """PLR's op names and signatures, recording every call. ``raises`` maps an op name to an
    exception INSTANCE to raise, ``hooks`` maps one to an async callable run inside the op body,
    ``returns`` holds one distinct sentinel per op (what the op returns)."""

    def __init__(self, tips_mounted: int = 8):
        self.head = {i: types.SimpleNamespace(has_tip=i < tips_mounted) for i in range(8)}
        self.calls: list[tuple[str, dict]] = []
        self.raises: dict[str, BaseException] = {}
        self.hooks: dict[str, object] = {}
        self.returns = {name: object() for name in OPS}
        self.origins: list = []

    async def _op(self, name, **arguments):
        self.calls.append((name, arguments))
        hook = self.hooks.get(name)
        if hook is not None:
            await hook()
        if name in self.raises:
            raise self.raises[name]
        return self.returns[name]

    async def pick_up_tips(self, tip_spots, use_channels=None, offsets=None, **backend_kwargs):
        self.origins = list(tip_spots) if isinstance(tip_spots, (list, tuple)) else []
        return await self._op("pick_up_tips", tip_spots=tip_spots, use_channels=use_channels, offsets=offsets, **backend_kwargs)

    async def drop_tips(self, tip_spots, use_channels=None, offsets=None, allow_nonzero_volume=False, **backend_kwargs):
        return await self._op(
            "drop_tips", tip_spots=tip_spots, use_channels=use_channels, offsets=offsets,
            allow_nonzero_volume=allow_nonzero_volume, **backend_kwargs,
        )

    async def return_tips(self, use_channels=None, allow_nonzero_volume=False, offsets=None, **backend_kwargs):
        await self._op("return_tips", use_channels=use_channels)
        return await self.drop_tips(tip_spots=self.origins, use_channels=use_channels)

    async def discard_tips(self, use_channels=None, allow_nonzero_volume=True, offsets=None, **backend_kwargs):
        await self._op("discard_tips", use_channels=use_channels)
        return await self.drop_tips(tip_spots=[self.trash] * 8, use_channels=use_channels)

    async def aspirate(
        self, resources, vols, use_channels=None, flow_rates=None, offsets=None, liquid_height=None,
        blow_out_air_volume=None, spread="wide", mix=None, **backend_kwargs,
    ):
        return await self._op("aspirate", resources=resources, vols=vols, use_channels=use_channels, **backend_kwargs)

    async def dispense(
        self, resources, vols, use_channels=None, flow_rates=None, offsets=None, liquid_height=None,
        blow_out_air_volume=None, spread="wide", mix=None, **backend_kwargs,
    ):
        result = await self._op("dispense", resources=resources, vols=vols, use_channels=use_channels, **backend_kwargs)
        # A dispense changes the wells' volume, so the ledger has a real "after" state to draw.
        wells = list(resources) if isinstance(resources, (list, tuple)) else [resources]
        amounts = list(vols) if isinstance(vols, (list, tuple)) else [vols] * len(wells)
        for well, v in zip(wells, amounts, strict=False):
            tracker = getattr(well, "tracker", None)
            if tracker is not None:
                tracker.set_volume(tracker.get_used_volume() + float(v))
        return result

    async def transfer(
        self, source, targets, source_vol=None, ratios=None, target_vols=None, aspiration_flow_rate=None,
        dispense_flow_rates=None, **backend_kwargs,
    ):
        await self._op("transfer", source=source, targets=targets, source_vol=source_vol)
        vols = target_vols or [source_vol / len(targets)] * len(targets)
        await self.aspirate(resources=[source], vols=[sum(vols)])
        for target, v in zip(targets, vols, strict=True):
            await self.dispense(resources=[target], vols=[v], use_channels=[0])
        return self.returns["transfer"]

    async def pick_up_tips96(self, tip_rack, offset=None, **backend_kwargs):
        return await self._op("pick_up_tips96", tip_rack=tip_rack, offset=offset)

    async def drop_tips96(self, resource, offset=None, allow_nonzero_volume=False, **backend_kwargs):
        return await self._op("drop_tips96", resource=resource, offset=offset)

    async def return_tips96(self, allow_nonzero_volume=False, offset=None, **backend_kwargs):
        await self._op("return_tips96")
        return await self.drop_tips96(self.rack96)

    async def discard_tips96(self, allow_nonzero_volume=True, **backend_kwargs):
        await self._op("discard_tips96")
        return await self.drop_tips96(self.trash)

    async def aspirate96(self, resource, volume, offset=None, flow_rate=None, liquid_height=None,
                         blow_out_air_volume=None, mix=None, **backend_kwargs):
        return await self._op("aspirate96", resource=resource, volume=volume)

    async def dispense96(self, resource, volume, offset=None, flow_rate=None, liquid_height=None,
                         blow_out_air_volume=None, mix=None, **backend_kwargs):
        return await self._op("dispense96", resource=resource, volume=volume)

    trash = types.SimpleNamespace(name="trash", parent=None)
    rack96 = None


class Boom(Exception):
    """A distinct exception class so a swallowed or re-wrapped exception cannot pass."""


class _Recorder:
    """A ``display`` that records what it was asked to show."""

    def __init__(self):
        self.shown: list = []
        self.vars_at_show: list[set] = []

    def __call__(self, obj):
        self.shown.append(obj)


# --------------------------------------------------------------------------- html helpers


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

    def inside(self, tag) -> bool:
        p = self.parent
        while p is not None:
            if p.tag == tag:
                return True
            p = p.parent
        return False


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


def _body_rows(root: _Node) -> list[_Node]:
    tables = root.find_all("table")
    assert len(tables) == 1, f"expected one table, found {len(tables)}"
    bodies = tables[0].find_all("tbody")
    assert len(bodies) == 1
    return [n for n in bodies[0].children if isinstance(n, _Node) and n.tag == "tr"]


def _cell(row: _Node, cls: str) -> _Node:
    cells = row.find_all("td", cls=cls)
    assert len(cells) == 1, f"row has {len(cells)} cells of class {cls}"
    return cells[0]


def _classes(node: _Node) -> set[str]:
    return set((node.attrs.get("class") or "").split())


def _changed_ids(root: _Node) -> set[str]:
    """Wells the figure marks: decoded from the shell's own descriptor (``ids`` + ``flags``)."""
    groups = [n for n in root.walk() if n.tag == "g" and "data-praxis-grid" in n.attrs]
    out: set[str] = set()
    for g in groups:
        grid = json.loads(g.attrs["data-praxis-grid"])
        ids = grid["ids"].split(" ")
        out |= {i for i, f in zip(ids, grid["flags"], strict=True) if int(f) & 1}
    return out


def _class_only_problems(root: _Node) -> list[str]:
    """S2: outside an SVG and outside labware's own figure block, every element the ledger emits
    carries at most ``class`` (an untrusted reopen strips the rest)."""
    problems = []
    for n in root.walk():
        if n.tag in ("#root", "svg") or n.inside("svg"):
            continue
        if any(c in ("praxis-ledger__after",) for c in _classes(n)) or _in_after(n):
            continue
        extra = set(n.attrs) - {"class"}
        if extra:
            problems.append(f"<{n.tag}> carries {sorted(extra)}")
    return problems


def _in_after(n: _Node) -> bool:
    p = n.parent
    while p is not None:
        if "praxis-ledger__after" in _classes(p):
            return True
        p = p.parent
    return False


def _hostile_problems(doc: str, name: str) -> list[str]:
    problems = []
    if html_mod.escape(name, quote=True) != name and name in doc:
        problems.append("the raw hostile string appears in the html")
    root = _parse(doc)
    for n in root.walk():
        if n.tag in ("script", "style", "img", "iframe", "object"):
            problems.append(f"element <{n.tag}>")
        for a in n.attrs:
            if a.lower().startswith("on"):
                problems.append(f"event-handler attribute {a}")
    return problems


# --------------------------------------------------------------------------- fixtures for PLR


def _fixture_run(fx, body, *, replay=True):
    """Fresh fixture deck and handler, the three column transfers optionally replayed OUTSIDE any
    ledger, then ``await body(deck, lh)``."""

    async def go():
        deck, lh = await fx.assemble()
        if replay:
            await fx.run_transfers(lh, deck)
        return await body(deck, lh)

    return _run(go())


def _state(deck) -> dict:
    out = {}
    for name in ("source", "assay"):
        plate = deck.get_resource(name)
        out[name] = {w.get_identifier(): round(w.tracker.get_used_volume(), 6) for w in plate.get_all_items()}
    tips = deck.get_resource("tips_300")
    out["tips"] = {s.get_identifier(): s.has_tip() for s in tips.get_all_items()}
    return out


# =========================================================================== import purity


def test_ledger_imports_no_pylabrobot_anywhere_in_its_source(led):
    tree = ast.parse(_LEDGER_PATH.read_text())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    assert not found & {"pylabrobot", "js", "pyodide", "ipykernel"}, found


def test_ledger_module_level_imports_are_stdlib_or_siblings(led):
    tree = ast.parse(_LEDGER_PATH.read_text())
    stdlib = set(sys.stdlib_module_names)
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert {a.name.split(".")[0] for a in node.names} <= stdlib
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 1 or (node.module or "").split(".")[0] in stdlib, ast.dump(node)[:80]


def test_ledger_imports_in_plain_cpython_with_pylabrobot_blocked(led):
    """The claim itself, not just the source: a fresh interpreter whose import system REFUSES
    ``pylabrobot`` (and IPython, and js) can import glossary and ledger, and never pulls PLR in."""
    code = f"""
import sys, types, importlib, importlib.abc

class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in ("pylabrobot", "IPython", "js", "pyodide"):
            raise ImportError("blocked: " + name)

sys.meta_path.insert(0, Block())
pkg = types.ModuleType("_p")
pkg.__path__ = [{str(_DISPLAY_DIR)!r}]
sys.modules["_p"] = pkg
importlib.import_module("_p.glossary")
m = importlib.import_module("_p.ledger")
assert not [k for k in sys.modules if k.split(".")[0] in ("pylabrobot", "IPython", "js")], "imported"
print("ok", m.RunLedger.__name__)
"""
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120, check=False)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip() == "ok RunLedger"


# =========================================================================== AC-14: the fixture replay


def _replay(fx, led, *, show=False, display=None):
    """The fixture's three column transfers inside ``RunLedger(lh, show=False)``."""

    async def body(deck, lh):
        with led.RunLedger(lh, show=show, display=display) as run:
            await fx.run_transfers(lh, deck)
        return run, deck, lh

    async def go():
        deck, lh = await fx.assemble()
        return await body(deck, lh)

    return _run(go())


@pytest.fixture(scope="module")
def replay(fx, led):
    return _replay(fx, led)


def test_replay_has_twelve_top_level_rows_in_three_tip_cycles(replay):
    run, _deck, _lh = replay
    assert len(run.rows) == 12
    assert run.steps == 12
    assert run.tip_cycles == 3


def test_replay_actions_in_order(replay):
    run, _deck, _lh = replay
    assert [r.action for r in run.rows] == ["Pick up tips", "Aspirate", "Dispense", "Discard tips"] * 3
    assert [r.op for r in run.rows] == ["pick_up_tips", "aspirate", "dispense", "discard_tips"] * 3


def test_replay_steps_are_numbered_one_to_twelve_and_children_carry_none(replay):
    run, _deck, _lh = replay
    assert [r.step for r in run.rows] == list(range(1, 13))
    for row in run.all_rows:
        if row.parent is not None:
            assert row.step is None


def test_replay_every_row_finished_ok(replay):
    run, _deck, _lh = replay
    assert {r.status for r in run.all_rows} == {"ok"}
    assert all(r.error_type is None and r.error_message is None for r in run.all_rows)


def test_each_discard_row_has_exactly_one_drop_tips_child(replay):
    run, _deck, _lh = replay
    discards = [r for r in run.rows if r.op == "discard_tips"]
    assert len(discards) == 3
    for row in discards:
        assert [c.op for c in row.children] == ["drop_tips"]
        child = row.children[0]
        assert child.action == "Drop tips"
        assert child.parent is row and child.depth == 1 and row.depth == 0
        assert child.status == "ok"
    others = [r for r in run.rows if r.op != "discard_tips"]
    assert all(r.children == [] for r in others)


def test_children_do_not_change_step_cycle_or_volume_counts(replay):
    run, _deck, _lh = replay
    assert len(run.all_rows) == 15  # 12 top-level + 3 drop_tips children
    assert run.steps == 12 and run.tip_cycles == 3 and run.moved == 2400.0


def test_replay_volumes_per_channel_are_50_100_150_and_channels_are_8(replay):
    run, _deck, _lh = replay
    liquid = [r for r in run.rows if r.op in ("aspirate", "dispense")]
    assert [r.vols for r in liquid] == [(50.0,) * 8] * 2 + [(100.0,) * 8] * 2 + [(150.0,) * 8] * 2
    assert [r.volume for r in liquid] == [400.0, 400.0, 800.0, 800.0, 1200.0, 1200.0]
    assert [r.channels for r in run.rows] == [8] * 12
    assert all(c.channels == 8 for r in run.rows for c in r.children)


def test_replay_where_reads_as_a_whole_column(replay):
    run, _deck, _lh = replay
    assert [r.where for r in run.rows[:4]] == ["tips_300, column 1", "source, column 1", "assay, column 1", "trash"]
    assert [r.where for r in run.rows[8:12]] == ["tips_300, column 3", "source, column 3", "assay, column 3", "trash"]
    assert run.rows[3].children[0].where == "trash"


def test_replay_summary_and_plain_text(replay):
    run, _deck, _lh = replay
    assert run.summary() == "run  12 steps, 3 tip cycles, 2,400 µL moved"
    data, _meta = run.bundle(session="s", exec_count=1)
    assert data["text/plain"].startswith("run  12 steps, 3 tip cycles, 2,400 µL moved")


def test_replay_after_state_figure_marks_the_24_changed_assay_wells_in_rose(replay):
    run, _deck, _lh = replay
    data, _meta = run.bundle(session="s", exec_count=1)
    doc = data["text/html"]
    root = _parse(doc)
    assert doc.count(f'stroke="{ROSE}"') == 1  # one changed path (D4: one path per state)
    changed_paths = [p for p in root.find_all("path") if p.attrs.get("class") == "sv-changed"]
    assert len(changed_paths) == 1
    assert changed_paths[0].attrs["stroke"] == ROSE
    assert len([s for s in re.split(r"(?=M)", changed_paths[0].attrs["d"]) if s]) == 24
    assert _changed_ids(root) == {f"{r}{c}" for r in "ABCDEFGH" for c in (1, 2, 3)}
    resources = [n.attrs["data-praxis-res"] for n in root.walk() if "data-praxis-res" in n.attrs]
    assert resources == ["assay"]  # only the plate this run dispensed into
    assert "The assay plate after the run. Wells this run changed are outlined." in root.text()


def test_replay_after_state_figure_draws_the_plate_after_the_run_not_later(fx, led):
    """The figure is frozen at exit: state changed AFTER the run must not leak into the ledger."""

    async def body(deck, lh):
        with led.RunLedger(lh, show=False) as run:
            await fx.run_transfers(lh, deck)
        first = run.bundle(session="s", exec_count=1)[0]["text/html"]
        deck.get_resource("assay").get_item("H12").tracker.set_volume(300.0)  # not touched by the run
        deck.get_resource("assay").get_item("A1").tracker.set_volume(0.0)  # touched by the run
        second = run.bundle(session="s", exec_count=1)[0]["text/html"]
        return first, second

    first, second = _fixture_run(fx, body, replay=False)
    assert first == second


def test_replay_after_exit_the_class_is_untouched_and_no_op_name_is_left_on_the_instance(replay):
    run, _deck, lh = replay
    assert LiquidHandler.aspirate is ORIGINALS["aspirate"]
    for name in OPS:
        assert LiquidHandler.__dict__[name] is ORIGINALS[name], name
        assert name not in vars(lh), name
    assert not run.attached


def test_replay_ledger_bundle_is_valid_and_stamped_kind_ledger_with_null_resource_and_rev(replay, svg):
    run, _deck, _lh = replay
    data, meta = run.bundle(session="sess-1", exec_count=7)
    svg.check_bundle(data, meta)
    assert meta == {
        "praxis": {"v": 1, "kind": "ledger", "resource": None, "rev": None, "session": "sess-1", "exec": 7}
    }
    assert set(data) == {"text/html", "text/plain"}


def test_replay_ledger_meets_the_d4_target_and_cap(replay, budget):
    run, _deck, _lh = replay
    doc = run.bundle(session="s", exec_count=1)[0]["text/html"]
    size = budget.html_bytes(doc)
    assert size <= FIXTURE_LEDGER_TARGET, f"fixture ledger is {size} bytes (target {FIXTURE_LEDGER_TARGET})"
    assert size <= CAP


def test_replay_leaves_the_same_state_as_the_same_run_without_a_ledger(fx, led):
    """The ledger changes no op's effect: every well volume and every tip is as after a bare run."""
    async def under_ledger(deck, lh):
        with led.RunLedger(lh, show=False):
            await fx.run_transfers(lh, deck)
        return _state(deck)

    async def bare_run(deck, lh):
        await fx.run_transfers(lh, deck)
        return _state(deck)

    with_ledger = _fixture_run(fx, under_ledger, replay=False)
    bare = _fixture_run(fx, bare_run, replay=False)
    assert with_ledger == bare
    assert sum(with_ledger["assay"].values()) == 2400.0 and sum(with_ledger["source"].values()) == 19200.0 - 2400.0


def test_replay_rows_come_from_real_calls_not_from_the_fixtures_own_op_log(fx, led):
    """The ledger records what PLR was asked, so a different run gives different rows."""

    async def body(deck, lh):
        tips = deck.get_resource("tips_300")
        source = deck.get_resource("source")
        with led.RunLedger(lh, show=False) as run:
            await lh.pick_up_tips(tips["A1:D1"])
            await lh.aspirate(source["A1:D1"], vols=[10.0, 20.0, 30.0, 40.0])
            await lh.discard_tips()
        return run

    run = _fixture_run(fx, body, replay=False)
    assert [r.action for r in run.rows] == ["Pick up tips", "Aspirate", "Discard tips"]
    assert run.rows[0].where == "tips_300 A1:D1" and run.rows[0].channels == 4
    assert run.rows[1].where == "source A1:D1" and run.rows[1].vols == (10.0, 20.0, 30.0, 40.0)
    assert run.rows[1].volume == 100.0 and run.rows[1].channels == 4
    assert run.rows[2].channels == 4  # the tips mounted when it was called
    assert run.moved == 0.0  # nothing was dispensed


# =========================================================================== nesting (real PLR)


def test_a_transfer_yields_one_row_owning_its_aspirate_and_dispense_rows(fx, led):
    async def body(deck, lh):
        tips, source, assay = (deck.get_resource(n) for n in ("tips_300", "source", "assay"))
        with led.RunLedger(lh, show=False) as run:
            await lh.pick_up_tips(tips["A1"])
            await lh.transfer(source.get_item("A1"), assay["A1:B1"], source_vol=20)
            await lh.discard_tips()
        return run

    run = _fixture_run(fx, body, replay=False)
    assert [r.action for r in run.rows] == ["Pick up tips", "Transfer", "Discard tips"]
    transfer = run.rows[1]
    assert [c.action for c in transfer.children] == ["Aspirate", "Dispense", "Dispense"]
    assert all(c.parent is transfer and c.step is None and c.depth == 1 for c in transfer.children)
    assert [c.vols for c in transfer.children] == [(20.0,), (10.0,), (10.0,)]
    assert transfer.volume == 20.0 and transfer.channels == 1
    assert transfer.where == "source A1 to assay A1:B1"
    assert run.steps == 3 and run.tip_cycles == 1
    assert run.moved == 20.0  # once: not 20 (transfer) + 20 (its dispenses)
    assert len(run.all_rows) == 7  # 3 top-level + 3 under the transfer + 1 under discard_tips


def test_return_tips_owns_one_drop_tips_row(fx, led):
    async def body(deck, lh):
        tips = deck.get_resource("tips_300")
        with led.RunLedger(lh, show=False) as run:
            await lh.pick_up_tips(tips["A1:H1"])
            await lh.return_tips()
        return run

    run = _fixture_run(fx, body, replay=False)
    assert [r.action for r in run.rows] == ["Pick up tips", "Return tips"]
    ret = run.rows[1]
    assert [c.op for c in ret.children] == ["drop_tips"]
    assert ret.children[0].action == "Drop tips" and ret.children[0].step is None
    assert ret.where == "tips_300, column 1"  # adopted from the drop it caused
    assert ret.channels == 8
    assert run.steps == 2


def test_a_bare_drop_tips_is_a_top_level_row(fx, led):
    async def body(deck, lh):
        tips = deck.get_resource("tips_300")
        with led.RunLedger(lh, show=False) as run:
            await lh.pick_up_tips(tips["A1:B1"])
            await lh.drop_tips(tips["A1:B1"])
        return run

    run = _fixture_run(fx, body, replay=False)
    assert [(r.action, r.step, r.children) for r in run.rows] == [("Pick up tips", 1, []), ("Drop tips", 2, [])]


def test_every_glossary_action_is_shadowed_and_removed(led, gl):
    lh = FakeLH()
    run = led.RunLedger(lh, show=False)
    with run:
        assert set(vars(lh)) >= set(gl.ACTIONS)  # all thirteen, the 96 variants too
        assert set(gl.ACTIONS) == set(OPS)
    assert not set(vars(lh)) & set(OPS)


# =========================================================================== failures (real PLR)


def test_an_op_that_raises_marks_its_row_error_and_reraises_the_same_exception(fx, led):
    """AC-14: 80 uL from a well holding 50 uL raises TooLittleLiquidError inside the context."""
    from pylabrobot.resources.errors import TooLittleLiquidError

    async def body(deck, lh):
        tips, assay = deck.get_resource("tips_300"), deck.get_resource("assay")
        caught = []
        try:
            with led.RunLedger(lh, show=False) as run:
                await lh.pick_up_tips(tips["A4:H4"])
                try:
                    await lh.aspirate(assay["A1:H1"], vols=[80.0] * 8)
                except TooLittleLiquidError as inner:
                    caught.append(inner)
                    raise
        except TooLittleLiquidError as outer:
            caught.append(outer)
        return run, caught, lh

    run, caught, lh = _fixture_run(fx, body, replay=True)
    assert len(caught) == 2 and caught[0] is caught[1]  # __exit__ did not replace or suppress it
    exc = caught[0]
    assert str(exc) == "Not enough liquid in container: 80.0uL > 50.0uL."
    failed = run.rows[1]
    assert failed.action == "Aspirate" and failed.status == "error" and failed.step == 2
    assert failed.error_type == "TooLittleLiquidError"
    assert failed.error_message == "Not enough liquid in container: 80.0uL > 50.0uL."
    assert failed.where == "assay, column 1" and failed.vols == (80.0,) * 8
    assert run.rows[0].status == "ok"
    assert run.steps == 2 and run.tip_cycles == 1 and run.moved == 0.0
    assert not run.attached and not set(vars(lh)) & set(OPS)


def test_step_for_returns_the_failing_rows_step_once(fx, led):
    from pylabrobot.resources.errors import TooLittleLiquidError

    async def body(deck, lh):
        tips, assay = deck.get_resource("tips_300"), deck.get_resource("assay")
        with pytest.raises(TooLittleLiquidError) as info, led.RunLedger(lh, show=False):
            await lh.pick_up_tips(tips["A4:H4"])
            await lh.aspirate(assay["A1:H1"], vols=[80.0] * 8)
        return info.value

    exc = _fixture_run(fx, body, replay=True)
    assert led._ERROR_STEPS[id(exc)] == (exc, 2)  # the spec's shape: (exc, step)
    assert led.step_for(exc) == 2
    assert id(exc) not in led._ERROR_STEPS
    assert led.step_for(exc) is None  # a second call: the entry was removed


def test_with_show_true_and_a_raising_op_the_ledger_is_displayed_and_the_exception_propagates(fx, led):
    from pylabrobot.resources.errors import TooLittleLiquidError

    display = _Recorder()

    async def body(deck, lh):
        tips, assay = deck.get_resource("tips_300"), deck.get_resource("assay")
        with pytest.raises(TooLittleLiquidError), led.RunLedger(lh, display=display) as run:
            await lh.pick_up_tips(tips["A4:H4"])
            await lh.aspirate(assay["A1:H1"], vols=[80.0] * 8)
        return run

    run = _fixture_run(fx, body, replay=True)
    assert display.shown == [run]  # once, and the ledger itself
    data, meta = run._repr_mimebundle_()
    doc = data["text/html"]
    assert meta["praxis"]["kind"] == "ledger"
    root = _parse(doc)
    error_rows = [r for r in _body_rows(root) if "praxis-ledger__row--error" in _classes(r)]
    assert len(error_rows) == 1
    assert "TooLittleLiquidError" in error_rows[0].text()
    assert "error" in _cell(error_rows[0], "praxis-ledger__act").text()  # not colour alone (D3)
    assert data["text/plain"].startswith("run  2 steps, 1 tip cycle, 0 µL moved")


def test_the_ledger_is_displayed_after_the_wrappers_are_removed(led):
    lh = FakeLH()
    seen = []

    def display(obj):
        seen.append(set(vars(lh)) & set(OPS))

    async def go():
        with led.RunLedger(lh, display=display):
            await lh.pick_up_tips([1])

    _run(go())
    assert seen == [set()]


def test_show_false_never_displays(led):
    display = _Recorder()

    async def go():
        with led.RunLedger(FakeLH(), show=False, display=display) as run:
            pass
        fake = FakeLH()
        fake.raises["aspirate"] = Boom()
        with pytest.raises(Boom), led.RunLedger(fake, show=False, display=display):
            await fake.aspirate([1], [1.0])
        return run

    _run(go())
    assert display.shown == []


def test_show_true_displays_on_a_clean_exit_too(led):
    display = _Recorder()

    async def go():
        with led.RunLedger(FakeLH(), display=display) as run:
            pass
        return run

    run = _run(go())
    assert display.shown == [run]


def test_default_display_is_ipythons_and_is_resolved_lazily(led, monkeypatch):
    """No display injected: ``IPython.display.display`` is imported when the context exits."""
    shown = []
    fake_ipython = types.ModuleType("IPython")
    fake_display = types.ModuleType("IPython.display")
    fake_display.display = shown.append
    fake_ipython.display = fake_display
    monkeypatch.setitem(sys.modules, "IPython", fake_ipython)
    monkeypatch.setitem(sys.modules, "IPython.display", fake_display)

    async def go():
        with led.RunLedger(FakeLH()) as run:
            pass
        return run

    run = _run(go())
    assert shown == [run]


def test_a_display_that_raises_never_replaces_the_ops_exception(led):
    def bad_display(obj):
        raise RuntimeError("display broke")

    async def go():
        fake = FakeLH()
        boom = Boom("the op failed")
        fake.raises["aspirate"] = boom
        with pytest.raises(Boom) as info, led.RunLedger(fake, display=bad_display):
            await fake.aspirate([1], [1.0])
        return info.value is boom

    assert _run(go()) is True


def test_a_display_that_raises_on_a_clean_exit_is_not_swallowed(led):
    """No other error is in flight, so a display failure is the only signal there is."""

    def bad_display(obj):
        raise RuntimeError("display broke")

    with pytest.raises(RuntimeError, match="display broke"), led.RunLedger(FakeLH(), display=bad_display):
        pass


# =========================================================================== failures (FakeLH)


def test_a_failing_child_marks_child_and_parent_and_records_the_top_level_step(led):
    async def go():
        fake = FakeLH()
        boom = Boom("aspirate broke")
        fake.raises["aspirate"] = boom
        with pytest.raises(Boom) as info, led.RunLedger(fake, show=False) as run:
            await fake.pick_up_tips(["s"])
            await fake.transfer("src", ["t1", "t2"], source_vol=20)
        return run, info.value, boom

    run, exc, boom = _run(go())
    assert exc is boom
    transfer = run.rows[1]
    assert transfer.status == "error" and transfer.step == 2
    assert [c.status for c in transfer.children] == ["error"]  # the dispenses never ran
    assert transfer.children[0].error_type == "Boom" and transfer.error_message == "aspirate broke"
    assert led.step_for(exc) == 2  # the top-level ancestor's step, not None
    assert led.step_for(exc) is None


def test_ops_after_a_failure_are_still_recorded(led):
    async def go():
        fake = FakeLH()
        fake.raises["aspirate"] = Boom("x")
        with led.RunLedger(fake, show=False) as run:
            with pytest.raises(Boom):
                await fake.aspirate([1], [1.0])
            del fake.raises["aspirate"]
            await fake.aspirate([1], [1.0])
            await fake.dispense([1], [1.0])
        return run

    run = _run(go())
    assert [(r.step, r.status) for r in run.rows] == [(1, "error"), (2, "ok"), (3, "ok")]


def test_a_cancelled_op_is_recorded_as_an_error_and_is_not_put_in_error_steps(led):
    async def go():
        fake = FakeLH()
        fake.raises["aspirate"] = asyncio.CancelledError()
        with led.RunLedger(fake, show=False) as run:
            with pytest.raises(asyncio.CancelledError):
                await fake.aspirate([1], [1.0])
        return run

    before = dict(led._ERROR_STEPS)
    run = _run(go())
    assert run.rows[0].status == "error" and run.rows[0].error_type == "CancelledError"
    assert dict(led._ERROR_STEPS) == before  # only Exceptions reach the D8 handler


def test_an_exception_whose_str_raises_is_recorded_and_still_reraised(led):
    class Nasty(Exception):
        def __str__(self):
            raise ValueError("no str for you")

    async def go():
        fake = FakeLH()
        nasty = Nasty()
        fake.raises["aspirate"] = nasty
        with led.RunLedger(fake, show=False) as run:
            with pytest.raises(Nasty) as info:
                await fake.aspirate([1], [1.0])
        return run, info.value is nasty

    run, same = _run(go())
    assert same
    assert run.rows[0].status == "error" and run.rows[0].error_type == "Nasty"
    assert isinstance(run.rows[0].error_message, str)
    run.bundle(session="s", exec_count=1)  # and the ledger still renders


def test_error_steps_is_bounded_so_unread_entries_cannot_pile_up(led):
    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False):
            for _ in range(led._ERROR_STEPS_MAX * 3):
                fake.raises["aspirate"] = Boom("x")
                with pytest.raises(Boom):
                    await fake.aspirate([1], [1.0])

    _run(go())
    assert 0 < len(led._ERROR_STEPS) <= led._ERROR_STEPS_MAX


def test_error_steps_keeps_the_newest_entries(led):
    excs = []

    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False):
            for _ in range(led._ERROR_STEPS_MAX + 5):
                e = Boom("x")
                excs.append(e)
                fake.raises["aspirate"] = e
                with pytest.raises(Boom):
                    await fake.aspirate([1], [1.0])

    _run(go())
    assert led.step_for(excs[-1]) is not None
    assert led.step_for(excs[0]) is None  # the oldest was evicted


def test_step_for_is_none_for_anything_it_never_saw(led):
    assert led.step_for(Boom("never raised in a ledger")) is None
    assert led.step_for(None) is None
    assert led.step_for(object()) is None


def test_step_for_does_not_confuse_an_exception_with_a_recycled_id(led):
    """The entry holds the exception itself, so its ``id`` cannot be recycled while the entry lives,
    and a lookup with a different object under the same key is refused."""
    exc = Boom("x")
    imposter = Boom("y")
    led._ERROR_STEPS[id(imposter)] = (exc, 9)  # a corrupted entry: key and exception disagree
    assert led.step_for(imposter) is None


# =========================================================================== transparency (checker + controls)


ARGS = {
    "pick_up_tips": {"tip_spots": object(), "use_channels": object(), "offsets": object()},
    "drop_tips": {"tip_spots": object(), "use_channels": object(), "offsets": object(), "allow_nonzero_volume": object()},
    "aspirate": {"resources": object(), "vols": object(), "use_channels": object()},
    "dispense": {"resources": object(), "vols": object(), "use_channels": object()},
    "pick_up_tips96": {"tip_rack": object(), "offset": object()},
    "drop_tips96": {"resource": object(), "offset": object(), "allow_nonzero_volume": object()},
    "aspirate96": {"resource": object(), "volume": object()},
    "dispense96": {"resource": object(), "volume": object()},
}


async def _check_transparent(ledger_cls):
    """The properties a wrapper must keep, as ONE checker so its controls can be run through it.

    For every op: the result is the handler's own object; the arguments arrive as the very objects
    passed (junk objects, so the ledger's row descriptors also cannot break the op); a raised
    exception is the same instance, with its args, cause and context untouched; and the handler sees
    the same calls in the same order as with no ledger at all.
    """
    # 1. return values and argument identity, every op that takes plain arguments
    plain = FakeLH()
    with ledger_cls(plain, show=False):
        for name, kwargs in ARGS.items():
            try:
                result = await getattr(plain, name)(**kwargs)
            except Exception as exc:  # noqa: BLE001 -- a wrapper that breaks the call is a finding too
                raise AssertionError(f"{name}: the call raised {exc!r}") from exc
            assert result is plain.returns[name], f"{name}: the return value changed"
            recorded = plain.calls[-1][1]
            for key, value in kwargs.items():
                assert recorded[key] is value, f"{name}: argument {key} was not passed through as the same object"
    # positional arguments are passed positionally
    pos = FakeLH()
    a, b = object(), object()
    with ledger_cls(pos, show=False):
        try:
            await pos.aspirate(a, b)
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"positional call raised {exc!r}") from exc
    assert pos.calls[-1][1]["resources"] is a and pos.calls[-1][1]["vols"] is b

    # 2. exceptions: the same instance, nothing chained on
    for name in ARGS:
        fake = FakeLH()
        boom = Boom(f"{name} failed", 7)
        fake.raises[name] = boom
        with ledger_cls(fake, show=False):
            try:
                await getattr(fake, name)(**ARGS[name])
            except BaseException as caught:  # noqa: BLE001 -- the point is to see what escapes
                assert caught is boom, f"{name}: a different exception escaped ({caught!r})"
                assert caught.args == (f"{name} failed", 7)
                assert caught.__cause__ is None and caught.__context__ is None
            else:
                raise AssertionError(f"{name}: the exception was swallowed")

    # 3. the handler sees the same calls in the same order, with and without a ledger
    async def script(fake):
        await fake.pick_up_tips(["s1", "s2"], use_channels=[0, 1])
        await fake.transfer("src", ["t1", "t2"], source_vol=20)
        await fake.aspirate(["w"], [5.0])
        await fake.return_tips()
        await fake.pick_up_tips(["s3"])
        await fake.discard_tips()

    bare, wrapped = FakeLH(), FakeLH()
    await script(bare)
    with ledger_cls(wrapped, show=False):
        await script(wrapped)
    shape = lambda calls: [(n, sorted(k)) for n, k in calls]  # noqa: E731
    assert shape(wrapped.calls) == shape(bare.calls), "the ledger changed which ops the handler saw"


def test_the_real_ledger_is_transparent(led):
    _run(_check_transparent(led.RunLedger))


def _mutant(led, kind):
    """A ledger whose wrapper breaks exactly one transparency property."""

    class Mutant(led.RunLedger):
        def _wrap(self, name, orig):
            async def swallow(*a, **k):
                try:
                    return await orig(*a, **k)
                except Exception:  # noqa: BLE001
                    return None

            async def drop_return(*a, **k):
                await orig(*a, **k)

            async def alter_return(*a, **k):
                return [await orig(*a, **k)]

            async def wrap_exception(*a, **k):
                try:
                    return await orig(*a, **k)
                except Boom as exc:
                    raise Boom(*exc.args) from exc

            async def drop_kwargs(*a, **k):
                return await orig(*a)

            async def copy_args(*a, **k):
                return await orig(*[copy.copy(x) for x in a], **{key: copy.copy(v) for key, v in k.items()})

            async def call_twice(*a, **k):
                await orig(*a, **k)
                return await orig(*a, **k)

            return {
                "swallow": swallow, "drop_return": drop_return, "alter_return": alter_return,
                "wrap_exception": wrap_exception, "drop_kwargs": drop_kwargs, "copy_args": copy_args,
                "call_twice": call_twice,
            }[kind]

    return Mutant


@pytest.mark.parametrize(
    "kind",
    ["swallow", "drop_return", "alter_return", "wrap_exception", "drop_kwargs", "copy_args", "call_twice"],
)
def test_control_a_wrapper_that_changes_behaviour_fails_the_transparency_check(led, kind):
    with pytest.raises(AssertionError):
        _run(_check_transparent(_mutant(led, kind)))


def test_the_wrap_seam_is_what_attach_installs(led):
    """Control for the controls: the mutants only mean something if ``_wrap`` is what ``attach``
    puts on the instance."""
    marker = []

    class Spy(led.RunLedger):
        def _wrap(self, name, orig):
            marker.append(name)
            return super()._wrap(name, orig)

    lh = FakeLH()
    with Spy(lh, show=False):
        pass
    assert set(marker) == set(OPS)


def test_wrapped_methods_keep_their_names_and_signature(led):
    import inspect

    lh = FakeLH()
    with led.RunLedger(lh, show=False):
        assert lh.aspirate.__name__ == "aspirate"
        assert list(inspect.signature(lh.aspirate).parameters)[:3] == ["resources", "vols", "use_channels"]


# =========================================================================== nesting checker + control


async def _check_nesting(ledger_cls):
    fake = FakeLH()
    fake.rack96 = object()
    run = ledger_cls(fake, show=False)
    with run:
        await fake.pick_up_tips(["s"])
        await fake.transfer("src", ["t1", "t2"], source_vol=20)
        await fake.discard_tips()
        await fake.pick_up_tips(["s"])
        await fake.return_tips()
        await fake.return_tips96()
        await fake.discard_tips96()
    assert [r.op for r in run.rows] == [
        "pick_up_tips", "transfer", "discard_tips", "pick_up_tips", "return_tips", "return_tips96", "discard_tips96",
    ], "nested ops were recorded as top-level rows"
    assert [c.op for c in run.rows[1].children] == ["aspirate", "dispense", "dispense"]
    assert [c.op for c in run.rows[2].children] == ["drop_tips"]
    assert [c.op for c in run.rows[4].children] == ["drop_tips"]
    assert [c.op for c in run.rows[5].children] == ["drop_tips96"]
    assert [c.op for c in run.rows[6].children] == ["drop_tips96"]
    assert run.steps == 7


def test_nesting_of_every_wrapper_pair_including_the_96_head(led):
    _run(_check_nesting(led.RunLedger))


def test_control_a_flat_recorder_fails_the_nesting_check(led):
    class Flat(led.RunLedger):
        def _wrap(self, name, orig):
            async def wrapper(*a, **k):
                row = self._begin(name, a, k)  # never publishes the row as the current parent
                try:
                    result = await orig(*a, **k)
                except BaseException as exc:
                    self._fail(row, exc)
                    raise
                self._finish(row)
                return result

            return wrapper

    with pytest.raises(AssertionError):
        _run(_check_nesting(Flat))


def test_control_a_recorder_that_records_nothing_fails_the_nesting_check(led):
    class Blind(led.RunLedger):
        def _wrap(self, name, orig):
            return orig

    with pytest.raises(AssertionError):
        _run(_check_nesting(Blind))


def test_96_ops_are_recorded_with_the_96_head_names(led):
    async def go():
        from pylabrobot.resources import Trough  # noqa: F401 -- only to prove PLR resources work here

        fake = FakeLH()
        with led.RunLedger(fake, show=False) as run:
            await fake.pick_up_tips96(_plate("rack"))
            await fake.aspirate96(_plate("src"), volume=50)
            await fake.dispense96(_plate("dst"), volume=50)
            await fake.drop_tips96(_plate("trash"))
        return run

    run = _run(go())
    assert [r.action for r in run.rows] == [
        "Pick up tips (96 head)", "Aspirate (96 head)", "Dispense (96 head)", "Drop tips (96 head)",
    ]
    assert [r.channels for r in run.rows] == [96] * 4
    assert run.rows[1].vols == (50.0,) * 96 and run.rows[1].volume == 4800.0
    assert [r.where for r in run.rows] == ["rack", "src", "dst", "trash"]
    assert run.tip_cycles == 1 and run.moved == 4800.0 and run.steps == 4


def _plate(name):
    """A stand-in resource with PLR's shape for a whole labware (a name and no parent well)."""
    return types.SimpleNamespace(name=name, parent=None)


# =========================================================================== concurrency


def test_concurrent_top_level_ops_are_not_nested_into_each_other(led):
    """Two tasks each run one op; while one is in flight the other starts. They are siblings."""

    async def go():
        fake = FakeLH()
        gate = asyncio.Event()

        async def hold():
            await gate.wait()

        fake.hooks["aspirate"] = hold
        with led.RunLedger(fake, show=False) as run:
            first = asyncio.create_task(fake.aspirate([1], [1.0]))
            await asyncio.sleep(0)
            second = asyncio.create_task(fake.dispense([1], [1.0]))
            await asyncio.sleep(0)
            gate.set()
            await asyncio.gather(first, second)
        return run

    run = _run(go())
    assert [r.op for r in run.rows] == ["aspirate", "dispense"]
    assert all(r.parent is None and r.children == [] for r in run.rows)
    assert [r.step for r in run.rows] == [1, 2]


def test_ops_started_by_gather_inside_an_op_are_its_children(led):
    async def go():
        fake = FakeLH()

        async def fan_out():
            await asyncio.gather(fake.aspirate([1], [1.0]), fake.dispense([1], [2.0]))

        fake.hooks["transfer"] = fan_out
        with led.RunLedger(fake, show=False) as run:
            await fake.transfer("s", ["t"], source_vol=1)
        return run

    run = _run(go())
    assert [r.op for r in run.rows] == ["transfer"]
    kids = run.rows[0].children
    assert sorted(c.op for c in kids) == ["aspirate", "aspirate", "dispense", "dispense"]  # the two from
    assert all(c.parent is run.rows[0] and c.depth == 1 for c in kids)  # gather, and transfer's own two


def test_a_task_that_outlives_its_parent_op_records_top_level(led):
    """A task spawned inside an op inherits the op as its context; once that op is over the new
    row must not be filed under a finished parent."""

    async def go():
        fake = FakeLH()
        spawned = []

        async def spawn():
            async def late():
                await asyncio.sleep(0.01)
                await fake.dispense([1], [1.0])

            spawned.append(asyncio.create_task(late()))

        fake.hooks["aspirate"] = spawn
        with led.RunLedger(fake, show=False) as run:
            await fake.aspirate([1], [1.0])
            await asyncio.gather(*spawned)
        return run

    run = _run(go())
    assert [(r.op, r.parent) for r in run.rows] == [("aspirate", None), ("dispense", None)]


# =========================================================================== attach / detach


def test_attach_and_detach_are_idempotent(led):
    lh = FakeLH()
    run = led.RunLedger(lh, show=False)
    assert run.attached is False
    run.attach()
    first = {n: vars(lh)[n] for n in OPS}
    run.attach()  # a second attach must not wrap the wrappers
    assert {n: vars(lh)[n] for n in OPS} == first
    assert run.attached is True

    async def one():
        await lh.aspirate([1], [1.0])

    _run(one())
    assert len(run.rows) == 1  # recorded once, not twice
    run.detach()
    run.detach()  # a second detach is a no-op, not an error
    assert not set(vars(lh)) & set(OPS) and run.attached is False


def test_enter_and_exit_are_attach_and_detach(led):
    lh = FakeLH()
    run = led.RunLedger(lh, show=False)
    assert run.__enter__() is run
    assert run.attached and set(OPS) <= set(vars(lh))
    assert run.__exit__(None, None, None) is False  # never suppresses
    assert not run.attached and not set(vars(lh)) & set(OPS)


def test_exit_returns_false_for_an_exception_too(led):
    run = led.RunLedger(FakeLH(), show=False)
    run.__enter__()
    assert run.__exit__(Boom, Boom("x"), None) is False


def test_a_ledger_can_be_entered_again_after_it_exited(led):
    lh = FakeLH()
    run = led.RunLedger(lh, show=False)

    async def one(name):
        await getattr(lh, name)([1], [1.0])

    with run:
        _run(one("aspirate"))
    with run:
        _run(one("dispense"))
    assert [r.op for r in run.rows] == ["aspirate", "dispense"]
    assert [r.step for r in run.rows] == [1, 2]
    assert not set(vars(lh)) & set(OPS)


def test_a_second_ledger_on_the_same_instance_is_refused_and_leaves_the_first_intact(led):
    lh = FakeLH()
    first = led.RunLedger(lh, show=False)
    second = led.RunLedger(lh, show=False)
    with first:
        before = {n: vars(lh)[n] for n in OPS}
        with pytest.raises(RuntimeError, match="already"):
            second.attach()
        assert {n: vars(lh)[n] for n in OPS} == before
        assert first.attached and not second.attached
    assert not set(vars(lh)) & set(OPS)
    with second:  # and once the first is gone the second can attach
        assert second.attached


def test_an_instance_attribute_that_was_already_there_is_restored_not_deleted(led):
    """A user's own instance-level wrapper must survive the ledger (a risk row in the spec)."""
    lh = FakeLH()
    seen = []
    orig = lh.aspirate

    async def mine(*a, **k):
        seen.append("mine")
        return await orig(*a, **k)

    lh.aspirate = mine

    async def go():
        with led.RunLedger(lh, show=False) as run:
            await lh.aspirate([1], [1.0])
        return run

    run = _run(go())
    assert seen == ["mine"] and len(run.rows) == 1  # the ledger wrapped THEIR wrapper
    assert vars(lh)["aspirate"] is mine  # and put it back
    assert not set(vars(lh)) & (set(OPS) - {"aspirate"})


def test_a_wrapper_left_over_after_detach_is_inert(led):
    lh = FakeLH()
    run = led.RunLedger(lh, show=False)
    with run:
        stray = lh.aspirate  # someone kept a reference

    async def go():
        return await stray([1], [1.0])

    assert _run(go()) is lh.returns["aspirate"]  # still forwards, unchanged
    assert len(run.rows) == 0  # detached: it forwards and records nothing


def test_a_replacement_installed_over_the_wrapper_is_not_clobbered_on_detach(led):
    lh = FakeLH()
    run = led.RunLedger(lh, show=False)
    run.attach()
    lh.__dict__["dispense"] = theirs = object()  # something else replaced our wrapper
    run.detach()
    assert vars(lh)["dispense"] is theirs
    assert not set(vars(lh)) & (set(OPS) - {"dispense"})


def test_attach_is_all_or_nothing(led):
    """An instance that cannot take attributes gets a clear TypeError and nothing half-installed."""

    class Slotted:
        __slots__ = ()

        async def aspirate(self, resources, vols):
            return 1

    with pytest.raises(TypeError):
        led.RunLedger(Slotted(), show=False).attach()

    class Plain:
        async def aspirate(self, resources, vols):
            return 1

    plain = Plain()
    with led.RunLedger(plain, show=False):
        assert "aspirate" in vars(plain)
    assert vars(plain) == {}


def test_a_handler_with_only_some_ops_is_wrapped_for_those_ops(led):
    class Partial:
        async def aspirate(self, resources, vols, use_channels=None):
            return "a"

        async def dispense(self, resources, vols, use_channels=None):
            return "d"

    lh = Partial()

    async def go():
        with led.RunLedger(lh, show=False) as run:
            assert (await lh.aspirate([1], [1.0]), await lh.dispense([1], [1.0])) == ("a", "d")
            assert set(vars(lh)) == {"aspirate", "dispense"}
        return run

    run = _run(go())
    assert [r.op for r in run.rows] == ["aspirate", "dispense"] and vars(lh) == {}


@pytest.mark.parametrize("thing", [None, object(), 3, "lh", types.SimpleNamespace()])
def test_a_ledger_over_something_that_is_not_a_handler_is_a_type_error(led, thing):
    with pytest.raises(TypeError):
        led.RunLedger(thing, show=False).attach()


def test_control_a_ledger_that_leaves_its_wrappers_behind_fails_the_cleanliness_check(led):
    def check(cls):
        lh = FakeLH()
        with cls(lh, show=False):
            pass
        leftover = set(vars(lh)) & set(OPS)
        assert not leftover, f"instance attributes left behind: {sorted(leftover)}"

    check(led.RunLedger)

    class Leaky(led.RunLedger):
        def detach(self):
            self._attached = False  # forgets to delete the instance attributes
            return self

    with pytest.raises(AssertionError):
        check(Leaky)


# =========================================================================== per-instance isolation


def test_ops_on_another_handler_are_not_recorded_and_its_class_is_untouched(led):
    async def go():
        a, b = FakeLH(), FakeLH()
        with led.RunLedger(a, show=False) as run:
            await b.aspirate([1], [1.0])
            await a.dispense([1], [1.0])
            assert vars(b) == {k: v for k, v in vars(b).items() if k not in OPS}
        return run, a, b

    run, a, b = _run(go())
    assert [r.op for r in run.rows] == ["dispense"]
    assert [n for n, _ in b.calls] == ["aspirate"]


def test_two_handlers_with_their_own_ledgers_record_only_their_own_ops(led):
    async def go():
        a, b = FakeLH(), FakeLH()
        with led.RunLedger(a, show=False) as ra, led.RunLedger(b, show=False) as rb:
            await a.aspirate([1], [1.0])
            await b.dispense([1], [1.0])
            await a.transfer("s", ["t"], source_vol=1)
            await b.pick_up_tips(["s"])
        return ra, rb

    ra, rb = _run(go())
    assert [r.op for r in ra.rows] == ["aspirate", "transfer"]
    assert [r.op for r in rb.rows] == ["dispense", "pick_up_tips"]
    assert [c.op for c in ra.rows[1].children] == ["aspirate", "dispense"]
    assert rb.rows[0].children == []


def test_an_op_of_one_ledger_calling_another_ledgers_handler_is_not_its_child(led):
    async def go():
        a, b = FakeLH(), FakeLH()

        async def call_b():
            await b.aspirate([1], [1.0])

        a.hooks["transfer"] = call_b
        with led.RunLedger(a, show=False) as ra, led.RunLedger(b, show=False) as rb:
            await a.transfer("s", ["t"], source_vol=1)
        return ra, rb

    ra, rb = _run(go())
    assert [c.op for c in ra.rows[0].children] == ["aspirate", "dispense"]  # its own transfer's
    assert len(rb.rows) == 1 and rb.rows[0].parent is None and rb.rows[0].step == 1


def test_two_real_handlers_are_isolated_and_the_class_is_never_mutated(fx, led):
    async def go():
        deck_a, lh_a = await fx.assemble()
        deck_b, lh_b = await fx.assemble()
        tips_a, tips_b = deck_a.get_resource("tips_300"), deck_b.get_resource("tips_300")
        with led.RunLedger(lh_a, show=False) as run:
            for name in OPS:
                assert getattr(LiquidHandler, name) is ORIGINALS[name]
                assert LiquidHandler.__dict__[name] is ORIGINALS[name]
            await lh_b.pick_up_tips(tips_b["A1"])  # NOT recorded
            await lh_a.pick_up_tips(tips_a["A1"])
            assert not set(vars(lh_b)) & set(OPS)
        return run

    run = _run(go())
    assert [(r.action, r.where) for r in run.rows] == [("Pick up tips", "tips_300 A1")]


# =========================================================================== descriptors (FakeLH)


def test_scalar_and_mixed_volumes_and_explicit_channels(led, fx):
    plate = fx.cor_96_wellplate_360uL_Fb(name="p")
    wells = plate["A1:B1"]

    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False) as run:
            await fake.aspirate(wells, vols=50)  # a scalar broadcasts over the channels
            await fake.aspirate(wells, vols=[10, 80])
            await fake.dispense(wells[:1], vols=[5.5], use_channels=[3])
        return run

    run = _run(go())
    assert run.rows[0].vols == (50.0, 50.0) and run.rows[0].channels == 2
    assert run.rows[1].vols == (10.0, 80.0) and run.rows[1].volume == 90.0
    assert run.rows[2].vols == (5.5,) and run.rows[2].channels == 1
    doc = run.render_html()
    text = _parse(doc).text()
    assert "50 µL each" in text and "10–80 µL" in text and "5.5 µL" in text


def test_where_groups_wells_by_plate_and_falls_back_to_names_for_other_containers(led, fx):
    from pylabrobot.resources import Trough

    src = fx.cor_96_wellplate_360uL_Fb(name="src")
    dst = fx.cor_96_wellplate_360uL_Fb(name="dst")
    trough = Trough(name="reservoir", size_x=10, size_y=10, size_z=10, max_volume=1000)

    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False) as run:
            await fake.aspirate([src.get_item("A1"), dst.get_item("A1")], vols=[1, 1])
            await fake.aspirate([trough], vols=[100])
            await fake.aspirate(src["A1:H3"], vols=[1] * 24)
            await fake.aspirate(src["A1"] + src["C3"], vols=[1, 1])
        return run

    run = _run(go())
    assert run.rows[0].where == "src A1, dst A1"
    assert run.rows[1].where == "reservoir"
    assert run.rows[2].where == "src A1:H3"
    assert run.rows[3].where == "src A1, C3"


def test_discard_tips_channels_is_the_number_of_tips_mounted(led):
    async def go():
        fake = FakeLH(tips_mounted=3)
        with led.RunLedger(fake, show=False) as run:
            await fake.discard_tips()
            await fake.discard_tips(use_channels=[0, 1])
        return run

    run = _run(go())
    assert [r.channels for r in run.rows] == [3, 2]


def test_a_descriptor_that_cannot_read_its_arguments_never_breaks_the_op(led):
    """Junk arguments: the ledger records blanks, the op runs and returns exactly as it would."""
    hostile = types.SimpleNamespace()

    class Exploding:
        @property
        def name(self):
            raise RuntimeError("no name")

        @property
        def parent(self):
            raise RuntimeError("no parent")

        def __len__(self):
            raise RuntimeError("no len")

        def __iter__(self):
            raise RuntimeError("no iter")

    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False) as run:
            r1 = await fake.aspirate(Exploding(), "vols?")
            r2 = await fake.aspirate(hostile, [object(), "x"], use_channels=Exploding())
            r3 = await fake.pick_up_tips(None)
            r4 = await fake.transfer(Exploding(), ["t"], source_vol="lots", target_vols=[1.0])
        return run, (r1, r2, r3, r4), fake

    run, results, fake = _run(go())
    assert results == (fake.returns["aspirate"], fake.returns["aspirate"], fake.returns["pick_up_tips"], fake.returns["transfer"])
    assert [r.status for r in run.rows] == ["ok"] * 4
    run.bundle(session="s", exec_count=1)  # and the ledger still renders


# =========================================================================== counts: what "moved" means


def test_moved_counts_top_level_ok_dispenses_and_transfers_only(led, fx):
    plate = fx.cor_96_wellplate_360uL_Fb(name="p")
    wells = plate["A1:H1"]

    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False) as asp_only:
            await fake.aspirate(wells, vols=[10.0] * 8)
        fake2 = FakeLH()
        fake2.raises["dispense"] = Boom("x")
        with led.RunLedger(fake2, show=False) as failed:
            with pytest.raises(Boom):
                await fake2.dispense(wells, vols=[10.0] * 8)
        fake3 = FakeLH()
        with led.RunLedger(fake3, show=False) as mixed:
            await fake3.dispense(wells, vols=[10.0] * 8)
            await fake3.transfer(plate.get_item("A1"), [plate.get_item("B1")], source_vol=25)
        return asp_only, failed, mixed

    asp_only, failed, mixed = _run(go())
    assert asp_only.moved == 0.0
    assert failed.moved == 0.0
    assert mixed.moved == 80.0 + 25.0


def test_summary_pluralises_and_formats_amounts(led):
    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False) as empty:
            pass
        with led.RunLedger(fake, show=False) as one:
            await fake.pick_up_tips(["s"])
        with led.RunLedger(fake, show=False) as big:
            await fake.dispense([types.SimpleNamespace(name="x", parent=None)], vols=[1234.56])
        return empty, one, big

    empty, one, big = _run(go())
    assert empty.summary() == "run  0 steps, 0 tip cycles, 0 µL moved"
    assert one.summary() == "run  1 step, 1 tip cycle, 0 µL moved"
    assert big.summary() == "run  1 step, 0 tip cycles, 1,234.6 µL moved"


def test_a_failed_pick_up_does_not_start_a_tip_cycle_but_is_a_step(led):
    async def go():
        fake = FakeLH()
        fake.raises["pick_up_tips"] = Boom("x")
        with led.RunLedger(fake, show=False) as run:
            with pytest.raises(Boom):
                await fake.pick_up_tips(["s"])
        return run

    run = _run(go())
    assert run.steps == 1 and run.tip_cycles == 0


def test_mid_run_counts_include_the_row_in_flight(led):
    snapshots = []

    async def go():
        fake = FakeLH()
        run = led.RunLedger(fake, show=False)

        async def peek():
            snapshots.append((run.steps, [r.status for r in run.all_rows], run.summary(), run.render_html()))

        fake.hooks["aspirate"] = peek
        with run:
            await fake.pick_up_tips(["s"])
            await fake.aspirate([1], [1.0])
        return run

    run = _run(go())
    steps, statuses, summary, doc = snapshots[0]
    assert steps == 2 and statuses == ["ok", "in-flight"]
    assert summary.startswith("run  2 steps, 1 tip cycle")
    rows = _body_rows(_parse(doc))
    assert "praxis-ledger__row--in-flight" in _classes(rows[1])
    assert "in-flight" in _cell(rows[1], "praxis-ledger__act").text()
    assert run.rows[1].status == "ok"
    final = _body_rows(_parse(run.render_html()))
    assert "in-flight" not in "".join(r.text() for r in final)


# =========================================================================== the table


def test_table_header_and_rows(replay):
    run, _deck, _lh = replay
    root = _parse(run.render_html())
    headers = [th.text() for th in root.find_all("th")]
    assert headers == ["Step", "Action", "Where", "Volume", "Channels"]
    rows = _body_rows(root)
    assert len(rows) == 15  # one per row, children included
    steps = [_cell(r, "praxis-ledger__step").text() for r in rows]
    top = [r for r in rows if "praxis-ledger__row--child" not in _classes(r)]
    assert [_cell(r, "praxis-ledger__step").text() for r in top] == [str(i) for i in range(1, 13)]
    children = [r for r in rows if "praxis-ledger__row--child" in _classes(r)]
    assert len(children) == 3
    assert all(_cell(c, "praxis-ledger__step").text() == "" for c in children)
    assert steps.count("") == 3


def test_child_rows_sit_directly_under_their_parent_and_are_marked_as_nested(replay):
    run, _deck, _lh = replay
    rows = _body_rows(_parse(run.render_html()))
    for i, row in enumerate(rows):
        if "praxis-ledger__row--child" in _classes(row):
            assert "Discard tips" in _cell(rows[i - 1], "praxis-ledger__act").text()
            act = _cell(row, "praxis-ledger__act").text()
            assert act.startswith("↳") and "Drop tips" in act  # readable with no CSS at all


def test_action_cells_use_only_glossary_names(replay, gl):
    run, _deck, _lh = replay
    names = set(gl.ACTIONS.values())
    assert {r.action for r in run.all_rows} <= names
    rows = _body_rows(_parse(run.render_html()))
    for row in rows:
        text = _cell(row, "praxis-ledger__act").text().replace("↳", "").strip()
        assert text in names, text


def test_pick_up_rows_start_a_tip_cycle_hairline(replay):
    run, _deck, _lh = replay
    rows = _body_rows(_parse(run.render_html()))
    marked = [_cell(r, "praxis-ledger__act").text() for r in rows if "praxis-ledger__row--cycle" in _classes(r)]
    assert marked == ["Pick up tips"] * 3
    assert sum("praxis-ledger__row--cycle" in _classes(r) for r in rows) == 3


def test_aspirate_and_dispense_rows_carry_a_moonstone_bar_sized_by_volume(replay):
    run, _deck, _lh = replay
    rows = _body_rows(_parse(run.render_html()))
    widths = {}
    for row in rows:
        act = _cell(row, "praxis-ledger__act").text()
        bars = row.find_all("svg", cls="praxis-ledger__bar")
        if act in ("Aspirate", "Dispense"):
            assert len(bars) == 1, act
            rect = bars[0].find_all("rect")[0]
            assert rect.attrs["fill"] == MOONSTONE
            widths.setdefault(act, []).append(float(rect.attrs["width"]))
        else:
            assert bars == [], act
    for act in ("Aspirate", "Dispense"):
        w50, w100, w150 = widths[act]
        assert 0 < w50 < w100 < w150
        assert w50 / w150 == pytest.approx(50 / 150, abs=0.05)


def test_volume_cell_reads_each_for_a_multi_channel_row(replay):
    run, _deck, _lh = replay
    rows = _body_rows(_parse(run.render_html()))
    vols = [_cell(r, "praxis-ledger__vol").text() for r in rows]
    assert [v for v in vols if v] == ["50 µL each", "50 µL each", "100 µL each", "100 µL each", "150 µL each", "150 µL each"]
    chans = [_cell(r, "praxis-ledger__ch").text() for r in rows]
    assert set(chans) == {"8"}


def test_only_class_survives_on_the_table_markup(replay):
    """S2: on an untrusted reopen only ``class`` survives on table/details/summary, so the table's
    meaning (steps, actions, where, volume, channels) must live in text, not in attributes."""
    run, _deck, _lh = replay
    root = _parse(run.render_html())
    assert _class_only_problems(root) == []
    stripped = re.sub(r"<svg\b.*?</svg>", "", run.render_html(), flags=re.S)
    stripped = re.sub(r'\s(?!class=)[a-zA-Z-]+="[^"]*"', "", stripped)
    text = _parse(stripped).text()
    for needle in ("Pick up tips", "source, column 2", "150 µL each", "run  12 steps, 3 tip cycles, 2,400 µL moved"):
        assert needle in text


def test_control_the_class_only_checker_flags_other_attributes():
    root = _parse('<div class="a"><table class="t"><tr style="x:y"><td data-praxis-res="p">1</td></tr></table></div>')
    assert _class_only_problems(root) != []
    ok = _parse('<div class="a"><table class="t"><tr class="r"><td class="c">1</td></tr></table></div>')
    assert _class_only_problems(ok) == []


def test_name_line_is_run_then_the_counts_in_class_only_spans(replay):
    run, _deck, _lh = replay
    root = _parse(run.render_html())
    names = root.find_all("p", cls="praxis-name")
    assert len(names) == 1
    assert names[0].text() == "run  12 steps, 3 tip cycles, 2,400 µL moved"
    assert names[0].find_all("span", cls="praxis-name__title")[0].text() == "run"


def test_error_row_is_marked_by_text_and_class_not_colour_alone(led):
    async def go():
        fake = FakeLH()
        fake.raises["aspirate"] = Boom("the well is empty")
        with led.RunLedger(fake, show=False) as run:
            await fake.pick_up_tips(["s"])
            with pytest.raises(Boom):
                await fake.aspirate([1], [1.0])
        return run

    run = _run(go())
    rows = _body_rows(_parse(run.render_html()))
    assert "praxis-ledger__row--error" not in _classes(rows[0])
    assert "praxis-ledger__row--error" in _classes(rows[1])
    act = _cell(rows[1], "praxis-ledger__act").text()
    assert "error" in act and "Boom" in act and "the well is empty" in act


def test_after_state_only_for_plates_that_received_liquid(led, fx):
    src = fx.cor_96_wellplate_360uL_Fb(name="src")
    dst = fx.cor_96_wellplate_360uL_Fb(name="dst")
    other = fx.cor_96_wellplate_360uL_Fb(name="other")

    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False) as run:
            await fake.aspirate(src["A1:B1"], vols=[10, 10])
            await fake.dispense(dst["A1:B1"], vols=[10, 10])
            await fake.dispense(other["C3"], vols=[5])
            await fake.dispense(dst["A2"], vols=[0])  # a zero dispense changes nothing
        return run

    run = _run(go())
    root = _parse(run.render_html())
    figures = [n.attrs["data-praxis-res"] for n in root.walk() if "data-praxis-res" in n.attrs]
    assert figures == ["dst", "other"]  # in order of first dispense; the source is not shown
    labels = [n.text() for n in root.find_all("p", cls="praxis-ledger__after-label")]
    assert labels == [
        "The dst plate after the run. Wells this run changed are outlined.",
        "The other plate after the run. Wells this run changed are outlined.",
    ]
    assert _changed_ids(root) == {"A1", "B1", "C3"}


def test_no_after_state_block_when_nothing_was_dispensed(led):
    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False) as run:
            await fake.pick_up_tips(["s"])
        return run

    root = _parse(_run(go()).render_html())
    assert root.find_all(cls="praxis-ledger__after") == []
    assert [n for n in root.walk() if "data-praxis-res" in n.attrs] == []


def test_plain_text_lists_every_row_and_indents_children(replay):
    run, _deck, _lh = replay
    lines = run.bundle(session="s", exec_count=1)[0]["text/plain"].splitlines()
    assert lines[0] == "run  12 steps, 3 tip cycles, 2,400 µL moved"
    body = lines[1:]
    assert len(body) == 15
    assert body[0].lstrip().startswith("1") and "Pick up tips" in body[0]
    drop = [ln for ln in body if "Drop tips" in ln]
    assert len(drop) == 3 and all(ln.startswith("  ") and ln.lstrip() != ln for ln in drop)


# =========================================================================== bundle, stamp, providers


def test_repl_mimebundle_returns_a_valid_bundle_with_the_default_providers(led, svg):
    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False) as run:
            await fake.pick_up_tips(["s"])
        return run

    data, meta = _run(go())._repr_mimebundle_()
    svg.check_bundle(data, meta)
    stamp = meta["praxis"]
    assert (stamp["kind"], stamp["resource"], stamp["rev"], stamp["v"]) == ("ledger", None, None, 1)
    assert isinstance(stamp["session"], str) and stamp["session"]
    assert stamp["exec"] is None


def test_repl_mimebundle_accepts_ipythons_include_and_exclude(led):
    run = led.RunLedger(FakeLH(), show=False)
    assert run._repr_mimebundle_(include=None, exclude=None) == run._repr_mimebundle_()
    assert run._repr_mimebundle_(include={"text/html"}, exclude=set())[0].keys() >= {"text/html"}


def test_configure_sets_the_session_and_execution_providers(led):
    run = led.RunLedger(FakeLH(), show=False)
    counter = iter(range(41, 100))
    led.configure(session=lambda: "kernel-abc", exec_count=lambda: next(counter))
    assert run._repr_mimebundle_()[1]["praxis"]["session"] == "kernel-abc"
    assert run._repr_mimebundle_()[1]["praxis"]["exec"] == 42  # read at render time, each time
    led.configure()  # resets
    assert run._repr_mimebundle_()[1]["praxis"]["session"] != "kernel-abc"


def test_a_raising_provider_falls_back_and_never_breaks_the_display(led):
    def broken():
        raise RuntimeError("no kernel")

    led.configure(session=broken, exec_count=broken)
    data, meta = led.RunLedger(FakeLH(), show=False)._repr_mimebundle_()
    assert meta["praxis"]["session"] and meta["praxis"]["exec"] is None


def test_an_empty_session_is_refused_by_the_bundle_check(led, svg):
    run = led.RunLedger(FakeLH(), show=False)
    with pytest.raises(svg.UnsafeHtmlError):
        run.bundle(session="", exec_count=1)


def test_bundle_arguments_override_the_providers(led):
    led.configure(session=lambda: "from-provider", exec_count=lambda: 5)
    meta = led.RunLedger(FakeLH(), show=False).bundle(session="explicit", exec_count=9)[1]
    assert meta["praxis"]["session"] == "explicit" and meta["praxis"]["exec"] == 9


def test_the_glossary_is_the_only_source_of_the_ledgers_action_strings(gl, led):
    """AC-28, first bullet: what the ledger says is what ``glossary.ACTIONS`` says."""
    lh = FakeLH()
    lh.rack96 = _plate("rack")

    async def go():
        with led.RunLedger(lh, show=False) as run:
            await lh.pick_up_tips(["s"])
            await lh.transfer("a", ["b"], source_vol=1)
            await lh.return_tips()
            await lh.pick_up_tips96(_plate("r"))
            await lh.aspirate96(_plate("r"), volume=1)
            await lh.dispense96(_plate("r"), volume=1)
            await lh.return_tips96()
            await lh.discard_tips96()
            await lh.pick_up_tips(["s"])
            await lh.discard_tips()
        return run

    run = _run(go())
    assert {r.action for r in run.all_rows} <= set(gl.ACTIONS.values())
    for r in run.all_rows:
        assert r.action == gl.ACTIONS[r.op]


# =========================================================================== escaping


@pytest.mark.parametrize("name", HOSTILE_NAMES)
def test_hostile_plate_names_are_escaped_in_the_table_and_the_after_figure(led, svg, fx, name):
    plate = fx.cor_96_wellplate_360uL_Fb(name=name)

    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False) as run:
            await fake.aspirate(plate["A1:H1"], vols=[1.0] * 8)
            await fake.dispense(plate["A1:H1"], vols=[10.0] * 8)
        return run

    run = _run(go())
    data, meta = run.bundle(session="s", exec_count=1)
    doc = data["text/html"]
    assert _hostile_problems(doc, name) == []
    svg.check_bundle(data, meta)
    root = _parse(doc)
    assert _cell(_body_rows(root)[0], "praxis-ledger__where").text() == f"{name}, column 1"
    figure = [n for n in root.walk() if "data-praxis-res" in n.attrs]
    assert [n.attrs["data-praxis-res"] for n in figure] == [name]
    assert f"The {name} plate after the run." in root.text()


@pytest.mark.parametrize("message", HOSTILE_NAMES)
def test_hostile_exception_text_is_escaped_in_the_error_row(led, svg, message):
    async def go():
        fake = FakeLH()
        fake.raises["aspirate"] = Boom(message)
        with led.RunLedger(fake, show=False) as run:
            with pytest.raises(Boom):
                await fake.aspirate([1], [1.0])
        return run

    run = _run(go())
    data, meta = run.bundle(session="s", exec_count=1)
    doc = data["text/html"]
    assert _hostile_problems(doc, message) == []
    svg.check_bundle(data, meta)
    row = _body_rows(_parse(doc))[0]
    assert message in _cell(row, "praxis-ledger__act").text()


def test_control_the_hostile_checker_flags_naive_markup():
    name = '"><script>alert(1)</script>'
    assert _hostile_problems(f'<table><tr><td class="x">{name}</td></tr></table>', name)
    assert _hostile_problems('<td onclick="x()">a</td>', "a")
    assert _hostile_problems("<td>fine</td>", "fine") == []


# =========================================================================== the byte cap and the ladder


def _many_rows(led, n, *, fake=None):
    async def go():
        lh = fake or FakeLH()
        with led.RunLedger(lh, show=False) as run:
            for i in range(n):
                await lh.aspirate([_plate(f"well-{i}")], vols=[1.0 + i % 7])
        return run

    return _run(go())


def test_the_ladder_drops_the_drawing_first_then_text_never_before(led, budget, fx, monkeypatch):
    plate = fx.cor_96_wellplate_360uL_Fb(name="dst")

    async def go():
        fake = FakeLH()
        with led.RunLedger(fake, show=False) as run:
            await fake.aspirate([_plate("s")], vols=[10.0])
            await fake.dispense(plate["A1:H12"], vols=[5.0] * 96)
        return run

    run = _run(go())
    full, blocks, omitted = (run.render_html(level=lv) for lv in (0, 1, 2))
    assert "sv-well" in full and "data-praxis-grid" in full
    assert "sv-block" in blocks and "data-praxis-grid" not in blocks and "sv-well" not in blocks
    assert budget.OMISSION_SENTENCE in omitted
    assert "<svg" not in omitted and "sv-" not in omitted and "data-praxis-grid" not in omitted  # bars go too
    for doc in (full, blocks, omitted):
        assert "run  2 steps" in doc and "Aspirate" in doc and "Dispense" in doc  # the text stays

    sizes = [budget.html_bytes(d) for d in (full, blocks, omitted)]
    assert sizes[0] > sizes[1] > sizes[2]
    # With a cap just under each level the bundle takes the next one down.
    monkeypatch.setattr(budget, "MAX_HTML_BYTES", sizes[0] - 1)
    assert run.bundle(session="s", exec_count=1)[0]["text/html"] == blocks
    monkeypatch.setattr(budget, "MAX_HTML_BYTES", sizes[1] - 1)
    assert run.bundle(session="s", exec_count=1)[0]["text/html"] == omitted


def test_a_run_of_thousands_of_rows_stays_under_the_cap_and_says_what_it_left_out(led, budget, svg):
    run = _many_rows(led, 3000)
    data, meta = run.bundle(session="s", exec_count=1)
    doc = data["text/html"]
    assert budget.html_bytes(doc) <= CAP
    svg.check_bundle(data, meta)
    assert "run  3,000 steps" in doc  # the header stays true whatever is shown
    assert data["text/plain"].startswith("run  3,000 steps, 0 tip cycles, 0 µL moved")
    text = _parse(doc).text()
    m = re.search(r"… ([\d,]+) more rows? not shown", text)
    assert m, "the table does not say it was cut"
    shown = len(_body_rows(_parse(doc)))
    assert shown + int(m.group(1).replace(",", "")) == 3000
    assert run.steps == 3000 and len(run.rows) == 3000  # nothing was dropped from the record


def test_plain_text_is_bounded_for_a_long_run(led):
    data, _meta = _many_rows(led, 3000).bundle(session="s", exec_count=1)
    lines = data["text/plain"].splitlines()
    assert len(lines) < 3000
    assert any("not shown" in ln for ln in lines)


def test_a_run_just_under_the_cap_is_not_cut(led, budget):
    run = _many_rows(led, 40)
    doc = run.bundle(session="s", exec_count=1)[0]["text/html"]
    assert budget.html_bytes(doc) <= CAP
    assert len(_body_rows(_parse(doc))) == 40 and "not shown" not in doc


def test_huge_hostile_names_never_break_the_cap(led, budget, svg, fx):
    name = "<" * 100_000
    plate = fx.cor_96_wellplate_360uL_Fb(name=name)

    async def go():
        fake = FakeLH()
        fake.raises["aspirate"] = Boom("<" * 100_000)
        with led.RunLedger(fake, show=False) as run:
            await fake.dispense(plate["A1:H12"], vols=[1.0] * 96)
            with pytest.raises(Boom):
                await fake.aspirate(plate["A1:H12"], vols=[1.0] * 96)
        return run

    run = _run(go())
    data, meta = run.bundle(session="s", exec_count=1)
    assert budget.html_bytes(data["text/html"]) <= CAP
    svg.check_bundle(data, meta)
    assert data["text/plain"].startswith("run  2 steps")
