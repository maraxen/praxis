"""Browserless tests for ``praxis/display/labware.py`` (task B2, backlog #5636): the Plate,
TipRack and Well figures, the summary sentences, well-range compression, the ``data-praxis-grid``
descriptor and the D2 mimebundle with its stamp. Closes AC-9 and AC-10, and the labware half of
AC-12 (REAL PyLabRobot geometry, replacing the stand-in numbers in ``test_display_floor.py``) and of
AC-13 (the D4 targets for a 96-well plate and a tip rack; the cap and the ladder for one output).

Spec: ``260929_notebook-display-epic.md`` D2 (bundle, stamp, escaping, no script/style/svg mime),
D3 (inline light palette), D4 (one path per state, 64 KiB cap, ladder), D5 (scale, ``s_min``,
labels, wells >= 4 px, text >= 11 px), D14, section 3.2 (sentences, well-range compression) and
3.4 (grid descriptor), plus the S2 note: on an untrusted reopen only ``class`` survives, so the
name line and the sentence must be meaningful on their own.

**PyLabRobot.** Every PLR object here is the REAL 1.0.0b1 pin, built with the constructors of the
ported design fixture (``web-repl/design/notebook-display/make_fixture.py``). The venv's editable
PLR can be the old 0.2.2, which would make every test meaningless, so the first test asserts the
version. Run with ``PYTHONPATH=<PLR 1.0.0b1 source>`` prepended when the venv is not on the pin.

**Import discipline** (ADR 260817 Sec 2.4). ``praxis/display`` is loaded by path under the
synthetic package ``_praxis_display_under_test``; ``web-repl/overlay/assets/python`` is never put
on ``sys.path`` (its ``praxis/`` would shadow the repo's real package; ``test_rid_invariant.py``
guards it).

**Controls.** Every check that could pass vacuously has a control that must FAIL: the ``_repr_``
gate regex is run against a synthetic hook and a ``__repr__``; the floor checker against a
shrunken font and a shrunken ``min-width``; the escape checker against naive markup; the radius
check against a linear-radius oracle; the dispatch check against a class that only borrows the
name ``TipRack``; the AST lints against snippets that break each rule.
"""

from __future__ import annotations

import ast
import asyncio
import html as html_mod
import importlib
import importlib.util
import json
import math
import random
import re
import subprocess
import sys
import types
import warnings
from decimal import ROUND_HALF_UP, Decimal
from html.parser import HTMLParser
from pathlib import Path

import pytest

import pylabrobot

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL = _TESTS_DIR.parent
_DISPLAY_DIR = _WEB_REPL / "overlay" / "assets" / "python" / "praxis" / "display"
_LABWARE_PATH = _DISPLAY_DIR / "labware.py"
_FIXTURE_PATH = _WEB_REPL / "design" / "notebook-display" / "make_fixture.py"
_FIXTURE_JS = _WEB_REPL / "design" / "notebook-display" / "fixture.js"
_PKG = "_praxis_display_under_test"

CAP = 65_536
BUDGET_TARGETS = {"plate96": 16 * 1024, "tiprack": 12 * 1024}

# D3 palette (design tokens; the theme maps the structural four by attribute value).
SHEET, INK, INK_SOFT, RAIL = "#FFFFFF", "#1D2935", "#56636F", "#C9D2DA"
MOONSTONE, ROSE, BRICK = "#73A9C2", "#ED7A9B", "#B3402A"

HOSTILE_NAMES = [
    '<b>&"\'x',
    "</svg><script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "' onmouseover='alert(1)",
    '" onfocus="alert(1)" x="',
    "&amp;&lt;b&gt;",
    "<style>*{display:none}</style>",
    "µL \U0001f9ea 日本語",
]


# --------------------------------------------------------------------------- loading


def _package():
    """The synthetic package for praxis/display (no __init__ is run, sys.path is untouched)."""
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
def lw():
    """praxis/display/labware.py. A missing module is the RED reason."""
    if not _LABWARE_PATH.is_file():
        pytest.fail(f"praxis/display/labware.py does not exist yet: {_LABWARE_PATH}")
    _package()
    return importlib.import_module(f"{_PKG}.labware")


@pytest.fixture(scope="module")
def svg(lw):
    return importlib.import_module(f"{_PKG}.svg")


@pytest.fixture(scope="module")
def budget(lw):
    return importlib.import_module(f"{_PKG}.budget")


@pytest.fixture(scope="module")
def floor(lw):
    return importlib.import_module(f"{_PKG}.floor")


@pytest.fixture(scope="module")
def fx():
    """The ported design fixture module (its constructors are the ones the tests build with)."""
    spec = importlib.util.spec_from_file_location("_praxis_make_fixture_under_test", _FIXTURE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_praxis_make_fixture_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def state(fx):
    """The fixture state after its three column transfers: (deck, lh, ops)."""

    async def build():
        deck, lh = await fx.assemble()
        ops = await fx.run_transfers(lh, deck)
        return deck, lh, ops

    return asyncio.run(build())


@pytest.fixture(scope="module")
def deck(state):
    return state[0]


@pytest.fixture(scope="module")
def source(deck):
    return deck.get_resource("source")


@pytest.fixture(scope="module")
def assay(deck):
    return deck.get_resource("assay")


@pytest.fixture(scope="module")
def tips(deck):
    return deck.get_resource("tips_300")


# --------------------------------------------------------------------------- html helpers


class _Node:
    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
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


def _figure_group(root: _Node) -> _Node:
    groups = [n for n in root.walk() if n.tag == "g" and "data-praxis-res" in n.attrs]
    assert len(groups) == 1, f"expected one resource group, found {len(groups)}"
    return groups[0]


def _svg_root(root: _Node) -> _Node:
    svgs = root.find_all("svg")
    assert len(svgs) == 1, f"expected one <svg>, found {len(svgs)}"
    return svgs[0]


def _grid_of(root: _Node) -> dict:
    """The grid descriptor as the shell reads it: attribute -> html.unescape -> json.loads."""
    raw = _figure_group(root).attrs["data-praxis-grid"]
    return json.loads(raw)


def _paths(root: _Node) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in root.find_all("path"):
        out.setdefault(p.attrs.get("class", ""), []).append(p.attrs["d"])
    return out


_NUM = r"-?(?:\d+\.?\d*|\.\d+)"


def _subpaths(d: str) -> list[str]:
    return [s for s in re.split(r"(?=M)", d) if s]


def _circle(sp: str):
    m = re.match(rf"M({_NUM})[ ,]?({_NUM})a({_NUM})[ ,]?({_NUM}) 0 1 0", sp)
    if not m:
        return None
    x, y, rx, ry = (float(v) for v in m.groups())
    assert abs(rx - ry) < 1e-9, sp
    return x + rx, y, rx  # centre x, centre y, radius


def _rect(sp: str):
    """(x, y, w, h) of a rect subpath ``M x y H x2 V y2 H x z`` (no corner radius)."""
    m = re.match(rf"M({_NUM})[ ,]?({_NUM})H({_NUM})V({_NUM})H({_NUM})z$", sp)
    if not m:
        return None
    x, y, x2, y2, x3 = (float(v) for v in m.groups())
    assert abs(x - x3) < 1e-9, sp
    return x, y, x2 - x, y2 - y


def _texts(root: _Node) -> list[tuple[str, float]]:
    return [(t.text(), float(t.attrs["font-size"])) for t in root.find_all("text")]


# --------------------------------------------------------------------------- oracles (from the spec)


def _fmt(x) -> str:
    """Section 3.2 number formatting: thousands separator, at most one decimal, half up."""
    d = Decimal(repr(float(x))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    s = format(d, ",f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def _plate_sentence_oracle(volumes: list[float], max_volume: float) -> str:
    held = [v for v in volumes if v > 1e-6]
    if not held:
        return f"All {len(volumes)} wells are empty. Each holds up to {_fmt(max_volume)} µL."
    lo, hi, total = min(held), max(held), sum(held)
    rng = f"{_fmt(lo)} µL each" if _fmt(lo) == _fmt(hi) else f"{_fmt(lo)}–{_fmt(hi)} µL"
    count = (
        f"All {len(volumes)} wells hold liquid"
        if len(held) == len(volumes)
        else f"{len(held)} of {len(volumes)} wells hold liquid"
    )
    return f"{count}, {rng}. {_fmt(total)} µL in the plate."


def _ids_of(plate) -> list[str]:
    return [plate.get_child_identifier(w) for w in plate.get_all_items()]


def _volumes_of(plate) -> list[float]:
    return [w.tracker.get_used_volume() for w in plate.get_all_items()]


def _row_index(label: str) -> int:
    if len(label) == 1:
        return ord(label) - 65
    return (ord(label[0]) - 64) * 26 + (ord(label[1]) - 65)


def _expand(spec: str) -> set[str]:
    """Independent expander for the compressed form: ``A1``, ``A1:H3`` (a block) and comma lists."""

    def cell(tok):
        m = re.fullmatch(r"([A-Z]+)(\d+)", tok)
        assert m, tok
        return _row_index(m.group(1)), int(m.group(2))

    def name(r, c):
        label = chr(65 + r) if r < 26 else chr(64 + r // 26) + chr(65 + r % 26)
        return f"{label}{c}"

    out: set[str] = set()
    for part in spec.split(", "):
        if ":" in part:
            a, b = part.split(":")
            (r0, c0), (r1, c1) = cell(a), cell(b)
            assert r0 <= r1 and c0 <= c1, part
            out |= {name(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}
        else:
            r, c = cell(part)
            out.add(name(r, c))
    return out


def _all_ids(rows: int, cols: int) -> list[str]:
    return [f"{chr(65 + r)}{c}" for c in range(1, cols + 1) for r in range(rows)]


# --------------------------------------------------------------------------- 0. the premises


def test_repr_gate_no_ipython_display_hook_at_the_pin():
    """Spec D2 / B2 gate: ``grep -rnE '(^|[^_])_repr_[a-z]+_' <plr> --include='*.py'`` exits 1."""
    pattern = re.compile(r"(^|[^_])_repr_[a-z]+_")
    root = Path(pylabrobot.__file__).resolve().parent
    files = sorted(root.rglob("*.py"))
    assert len(files) > 500, f"the scan visited only {len(files)} files under {root}"
    hits = []
    for f in files:
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{f.relative_to(root)}:{n}: {line.strip()}")
    assert not hits, "PLR defines an IPython display hook; a registered formatter would shadow it:\n" + "\n".join(hits[:10])


def test_repr_gate_regex_controls():
    """Positive and negative control: the gate's regex fires on a hook and not on __repr__."""
    pattern = re.compile(r"(^|[^_])_repr_[a-z]+_")
    assert pattern.search("  def _repr_html_(self):")
    assert pattern.search("x._repr_mimebundle_()")
    assert pattern.search("def _repr_svg_(self):")
    assert not pattern.search("  def __repr__(self):")
    assert not pattern.search("return f'{self.__repr__()}'")
    # The Revision 10 BRE `_repr_[a-z]*_` matched every __repr__; the ERE must not.
    assert re.search(r"_repr_[a-z]*_", "def __repr__(self):")


def test_fixture_source_is_ported_to_the_pin():
    src = _FIXTURE_PATH.read_text(encoding="utf-8")
    problems = _fixture_source_problems(src)
    assert not problems, problems


def _fixture_source_problems(src: str) -> list[str]:
    """What a fixture port to the 1.0.0b1 pin must not contain (deprecated names, shims, 3.12)."""
    problems = []
    for bad in ("TIP_CAR_480_A00", "PLT_CAR_L5AC_A00", "Cor_96_wellplate_360ul_Fb", "rails=", "num_rails", "python3.12"):
        if bad in src:
            problems.append(f"deprecated or stale name still present: {bad}")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module in ("pylabrobot.liquid_handling", "pylabrobot.liquid_handling.backends") or node.module.startswith(
                "pylabrobot.resources.tip_tracker"
            ):
                problems.append(f"shim import: {node.module}")
    for good in ("hamilton_tip_carrier_L5", "hamilton_plate_carrier_L5_ac", "cor_96_wellplate_360uL_Fb", "track=3", "python3.14"):
        if good not in src:
            problems.append(f"missing: {good}")
    return problems


def test_fixture_port_checker_flags_the_old_source():
    """Negative control: the checker rejects the un-ported (0.2.2) idioms."""
    old = (
        "from pylabrobot.liquid_handling import LiquidHandler\n"
        "from pylabrobot.resources.corning.plates import Cor_96_wellplate_360ul_Fb\n"
        "deck.assign_child_resource(tip_car, rails=3)\n"
        "n = deck.num_rails\n"
        "p = '/lib/python3.12/site-packages/'\n"
    )
    problems = _fixture_source_problems(old)
    assert len(problems) >= 4, problems


def test_fixture_runs_clean_under_warnings_as_errors_and_matches_the_committed_fixture(tmp_path):
    """Run the ported script under ``-W error`` and compare it with the committed ``fixture.js``.

    The traceback text is compared only structurally: its caret markers differ between the CPython
    that generated the file and the one running this test.
    """
    out = tmp_path / "fixture.js"
    proc = subprocess.run(
        [sys.executable, "-W", "error", str(_FIXTURE_PATH), "--out", str(out)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    fresh = _load_fixture_js(out)
    committed = _load_fixture_js(_FIXTURE_JS)
    for key in ("generator", "deck", "volumes", "max_volume_ul", "tips", "ops"):
        assert fresh[key] == committed[key], f"fixture.js is stale against make_fixture.py: {key}"
    assert fresh["error"]["type"] == committed["error"]["type"] == "TooLittleLiquidError"
    assert fresh["error"]["message"] == committed["error"]["message"]
    assert fresh["error"]["module"] == committed["error"]["module"]
    for tb in (fresh["error"]["traceback"], committed["error"]["traceback"]):
        assert "/lib/python3.14/site-packages/pylabrobot/" in tb
        assert "/home/" not in tb and "/tmp/" not in tb and "python3.12" not in tb
    deck_data = committed["deck"]
    assert deck_data["num_tracks"] == 30 and "num_rails" not in deck_data
    assert "rotation" not in deck_data and "barcode" not in deck_data
    text = _FIXTURE_JS.read_text(encoding="utf-8")
    assert "/home/" not in text and "python3.12" not in text


def _load_fixture_js(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    prefix = "window.PRAXIS_FIXTURE = "
    assert text.startswith(prefix) and text.rstrip().endswith(";")
    return json.loads(text[len(prefix) :].rstrip()[:-1])


def test_fixture_state_is_what_the_spec_says(state, source, assay, tips):
    """AC-9/AC-10 premises, read from PLR itself: the numbers the sentences are derived from."""
    assert type(tips).__name__ == "EmbeddedTipRack" and type(tips).__name__ != "TipRack"
    assert source.model == "cor_96_wellplate_360uL_Fb"
    def vol(plate, ids):
        return [plate.get_item(i).tracker.get_used_volume() for i in ids]

    cols = {c: _all_ids(8, 12)[(c - 1) * 8 : c * 8] for c in range(1, 13)}
    assert [vol(assay, cols[c]) for c in (1, 2, 3)] == [[50.0] * 8, [100.0] * 8, [150.0] * 8]
    assert {v for c in range(4, 13) for v in vol(assay, cols[c])} == {0.0}
    assert sum(_volumes_of(assay)) == 2400.0 and sum(1 for v in _volumes_of(assay) if v > 0) == 24
    assert [vol(source, cols[c]) for c in (1, 2, 3)] == [[150.0] * 8, [100.0] * 8, [50.0] * 8]
    assert {v for c in range(4, 13) for v in vol(source, cols[c])} == {200.0}
    assert sum(_volumes_of(source)) == 8 * (150 + 100 + 50) + 9 * 8 * 200 == 16800.0
    assert sum(1 for s in tips.get_all_items() if s.tip is not None) == 72


# --------------------------------------------------------------------------- 1. sentences


def test_assay_sentence_is_exactly_the_spec_string(lw, assay):
    assert lw.plate_sentence(assay) == "24 of 96 wells hold liquid, 50–150 µL. 2,400 µL in the plate."


def test_source_sentence_is_exactly_the_spec_string(lw, source):
    # Columns 1-3 hold 150, 100 and 50 uL (the fixture drew 50 + 100 + 150 out of 200 each) and
    # columns 4-12 hold 200 uL: 8 * (150 + 100 + 50) + 8 * 9 * 200 = 16,800.
    assert lw.plate_sentence(source) == "All 96 wells hold liquid, 50–200 µL. 16,800 µL in the plate."


def test_plate_sentences_equal_the_oracle_derived_from_tracker_state(lw, assay, source):
    for plate in (assay, source):
        expected = _plate_sentence_oracle(_volumes_of(plate), plate.get_item("A1").max_volume)
        assert lw.plate_sentence(plate) == expected


def _plate_with(fx, name, volumes: dict[str, float]):
    plate = fx.cor_96_wellplate_360uL_Fb(name=name)
    for ident, v in volumes.items():
        plate.get_item(ident).tracker.set_volume(v)
    return plate


@pytest.mark.parametrize(
    "volumes, expected",
    [
        ({}, "All 96 wells are empty. Each holds up to 360 µL."),
        ({i: 200.0 for i in _all_ids(8, 12)}, "All 96 wells hold liquid, 200 µL each. 19,200 µL in the plate."),
        ({"A1": 12.34}, "1 of 96 wells hold liquid, 12.3 µL each. 12.3 µL in the plate."),
        ({"A1": 0.25, "B1": 1234.56}, "2 of 96 wells hold liquid, 0.3–1,234.6 µL. 1,234.8 µL in the plate."),
        ({"A1": 50.0, "H12": 50.0}, "2 of 96 wells hold liquid, 50 µL each. 100 µL in the plate."),
    ],
)
def test_plate_sentence_rules(lw, fx, volumes, expected):
    """The section 3.2 rules, each on its own: empty, all-equal, one decimal, thousands, en dash."""
    plate = _plate_with(fx, "p", volumes)
    assert lw.plate_sentence(plate) == expected
    # The expectation is itself checked against the independent oracle, so a wrong literal in the
    # table above cannot hide an implementation bug.
    assert expected == _plate_sentence_oracle(_volumes_of(plate), 360.0)


def test_sentence_oracle_control_distinguishes_a_wrong_string():
    """The oracle is not a rubber stamp: it disagrees with an off-by-one count and a hyphen."""
    good = _plate_sentence_oracle([50.0] * 24 + [0.0] * 72, 360.0)
    assert good == "24 of 96 wells hold liquid, 50 µL each. 1,200 µL in the plate."
    assert good != "23 of 96 wells hold liquid, 50 µL each. 1,200 µL in the plate."
    assert _plate_sentence_oracle([50.0, 150.0] + [0.0] * 94, 360.0).count("–") == 1


def test_tiprack_sentence_is_exactly_the_spec_string(lw, tips):
    assert lw.tiprack_sentence(tips) == "72 of 96 tips left. Columns 1–3 used."


def _rack_with_used(fx, name, used_ids):
    rack = fx.hamilton_96_tiprack_300uL_filter(name=name)
    for ident in used_ids:
        spot = rack.get_item(ident)
        spot.unassign_tip()
        assert spot.tip is None
    return rack


@pytest.mark.parametrize(
    "used, expected",
    [
        ([], "96 of 96 tips left."),
        (["A4"], "95 of 96 tips left. Column 4 used."),
        (_all_ids(8, 3), "72 of 96 tips left. Columns 1–3 used."),
        (["A1", "B1", "A2"], "93 of 96 tips left. Columns 1–2 used."),
        (["A1", "H3"], "94 of 96 tips left. Columns 1, 3 used."),
        (["C1", "A2", "A3", "A4", "H9", "A12"], "90 of 96 tips left. Columns 1–4, 9, 12 used."),
        (_all_ids(8, 12), "0 of 96 tips left. Columns 1–12 used."),
    ],
)
def test_tiprack_sentence_rules(lw, fx, used, expected):
    rack = _rack_with_used(fx, "r", used)
    assert lw.tiprack_sentence(rack) == expected


def test_well_sentence_is_exactly_the_spec_string(lw, assay):
    well = assay.get_item("A1")
    assert well.max_volume == 360
    assert well.tracker.get_used_volume() == 50.0
    assert lw.container_sentence(well) == "assay A1 holds 50 µL of 360 µL."


def test_well_sentence_uses_the_fixtures_max_volume_value_formatted(lw, fx):
    plate = fx.cor_96_wellplate_360uL_Fb(name="big")
    well = plate.get_item("B2")
    well.max_volume = 1234.5
    well.tracker.set_volume(99.95)
    assert lw.container_sentence(well) == f"big B2 holds {_fmt(99.95)} µL of 1,234.5 µL."


def test_containers_other_than_wells_get_the_same_sentence_or_the_infinite_form(lw):
    from pylabrobot.resources import Trough, Tube

    t = Trough(name="reservoir", size_x=100, size_y=20, size_z=30, max_volume=1000)
    t.tracker.set_volume(250.5)
    assert lw.container_sentence(t) == "reservoir holds 250.5 µL of 1,000 µL."
    inf = Trough(name="waste", size_x=100, size_y=20, size_z=30, max_volume=math.inf)
    inf.tracker.set_volume(1234.0)
    assert lw.container_sentence(inf) == "waste holds 1,234 µL."
    tube = Tube(name="t1", size_x=10, size_y=10, size_z=50, max_volume=1500)
    assert lw.container_sentence(tube) == "t1 holds 0 µL of 1,500 µL."


def test_a_well_outside_any_plate_is_named_by_its_own_name(lw):
    from pylabrobot.resources import Well

    w = Well(name="lonely", size_x=6, size_y=6, size_z=10, max_volume=200)
    w.tracker.set_volume(20)
    assert lw.container_sentence(w) == "lonely holds 20 µL of 200 µL."


# --------------------------------------------------------------------------- 2. well-range compression


@pytest.mark.parametrize(
    "ids, expected",
    [
        (_all_ids(8, 1), "A1:H1"),  # a full column
        (["A1", "B1", "C1", "D1"], "A1:D1"),  # part of a column
        (["E1", "F1", "G1", "H1"], "E1:H1"),
        (_all_ids(8, 3), "A1:H3"),  # a block: a full-height block
        ([f"{r}{c}" for r in "BCD" for c in (2, 3, 4)], "B2:D4"),  # a block in the middle
        (["A1"], "A1"),
        (["A1", "C3", "H12"], "A1, C3, H12"),  # scattered
        (["A1", "B1", "D1"], "A1:B1, D1"),  # two runs in one column
        (["A1", "B1", "A2"], "A1:B1, A2"),  # an L shape is not a block
        (["A1", "B1", "C1", "D1", "A2", "B2", "C2", "D2"], "A1:D2"),
        (["A1", "B1", "F1", "G1", "A2", "B2", "F2", "G2"], "A1:B2, F1:G2"),  # equal runs merge
        (["A1", "B1", "A3", "B3"], "A1:B1, A3:B3"),  # equal runs in non-adjacent columns do not
        (["H12", "A1", "C3"], "A1, C3, H12"),  # input order is irrelevant
        (["AA1", "AB1", "AC1"], "AA1:AC1"),  # two-letter rows (1536-well plates)
        (["A1", "A1", "B1"], "A1:B1"),  # duplicates collapse
    ],
)
def test_compress_wells_cases(lw, ids, expected):
    assert lw.compress_wells(ids) == expected
    assert _expand(lw.compress_wells(ids)) == set(ids)


def test_compress_wells_agrees_with_plr_on_real_plates(lw, source):
    """PLR's own ``get_items`` is the oracle for the range form: a block and a column."""
    for spec in ("A1:H1", "A1:H3", "B2:D4", "A1:D1"):
        wells = source.get_items(spec)
        ids = [source.get_child_identifier(w) for w in wells]
        assert lw.compress_wells(ids) == spec
        assert source.get_items(lw.compress_wells(ids)) == wells


def test_compress_wells_round_trips_random_sets(lw):
    """Property check: the output always expands back to exactly the input, on random subsets."""
    rng = random.Random(260929)
    universe = _all_ids(8, 12) + [f"A{r}{c}" for r in "ABCDEF" for c in (1, 2)]
    for _ in range(300):
        ids = rng.sample(universe, rng.randint(1, 40))
        out = lw.compress_wells(ids)
        assert _expand(out) == set(ids), (ids, out)
        assert lw.compress_wells(list(reversed(ids))) == out  # order-insensitive


def test_compress_wells_expander_control_detects_a_wrong_string():
    """The round-trip oracle must fail on a wrong answer."""
    assert _expand("A1:H3") != set(_all_ids(8, 2))
    assert _expand("A1:H2") != set(_all_ids(8, 3))
    assert _expand("A1, C3") != {"A1", "C3", "B2"}


@pytest.mark.parametrize("bad", [[], ["1A"], [""], ["a1"], ["A"], ["A0"], ["A1 "], ["A1:B2"], [None], [1]])
def test_compress_wells_rejects_what_is_not_a_well_id(lw, bad):
    with pytest.raises((ValueError, TypeError)):
        lw.compress_wells(bad)


def test_where_label_says_column_for_exactly_one_whole_column(lw):
    assert lw.where_label("source", _all_ids(8, 1), n_rows=8) == "source, column 1"
    assert lw.where_label("source", _all_ids(8, 12)[-8:], n_rows=8) == "source, column 12"
    assert lw.where_label("assay", _all_ids(8, 3), n_rows=8) == "assay A1:H3"
    assert lw.where_label("assay", ["A1", "B1"], n_rows=8) == "assay A1:B1"
    assert lw.where_label("assay", ["A1", "C3"], n_rows=8) == "assay A1, C3"
    # a whole column of a 4-row plate is a column; the same ids on an 8-row plate are not
    assert lw.where_label("q", _all_ids(4, 2)[:4], n_rows=4) == "q, column 1"
    assert lw.where_label("q", _all_ids(4, 2)[:4], n_rows=8) == "q A1:D1"


# --------------------------------------------------------------------------- 3. the plate figure


@pytest.fixture(scope="module")
def assay_html(lw, assay):
    return lw.render_html(assay)


@pytest.fixture(scope="module")
def source_html(lw, source):
    return lw.render_html(source)


def test_plate_html_has_no_circle_script_style_and_at_most_eight_paths(assay_html, source_html):
    for doc in (assay_html, source_html):
        assert doc.count("<circle") == 0
        assert doc.count("<script") == 0
        assert doc.count("<style") == 0
        assert doc.count("<path") <= 8
        assert doc.count("<g") == 1  # no per-well group


def test_well_outline_path_has_96_subpaths_and_liquid_has_24_for_assay(assay_html, source_html):
    a, s = _paths(_parse(assay_html)), _paths(_parse(source_html))
    assert len(a["sv-well"]) == 1 and len(_subpaths(a["sv-well"][0])) == 96
    assert len(a["sv-liquid"]) == 1 and len(_subpaths(a["sv-liquid"][0])) == 24
    assert len(_subpaths(s["sv-liquid"][0])) == 96
    assert a["sv-well"][0].count("M") == 96 and a["sv-liquid"][0].count("M") == 24


def test_every_liquid_radius_is_r_times_sqrt_v_over_max_within_1e_3(lw, assay, source, assay_html, source_html):
    for plate, doc in ((assay, assay_html), (source, source_html)):
        p = _paths(_parse(doc))
        held = [(i, w) for i, w in zip(_ids_of(plate), plate.get_all_items()) if w.tracker.get_used_volume() > 0]
        liquid = _subpaths(p["sv-liquid"][0])
        assert len(liquid) == len(held)
        for sp, (ident, w) in zip(liquid, held):
            cx, cy, r = _circle(sp)
            r_well = w.get_size_x() / 2
            expected = r_well * math.sqrt(w.tracker.get_used_volume() / w.max_volume)
            assert abs(r - expected) <= 1e-3, (ident, r, expected)


def test_liquid_radius_control_a_linear_radius_would_fail(assay, assay_html):
    """Negative control: a linear (v / max) radius differs from the sqrt rule by far more than 1e-3."""
    w = assay.get_item("A1")
    r_well = w.get_size_x() / 2
    sqrt_r = r_well * math.sqrt(w.tracker.get_used_volume() / w.max_volume)
    linear_r = r_well * w.tracker.get_used_volume() / w.max_volume
    assert abs(sqrt_r - linear_r) > 0.5
    first = _circle(_subpaths(_paths(_parse(assay_html))["sv-liquid"][0])[0])
    assert abs(first[2] - linear_r) > 0.5


def test_liquid_disks_are_concentric_with_their_wells_and_moonstone(assay_html):
    root = _parse(assay_html)
    p = _paths(root)
    outlines = [_circle(s) for s in _subpaths(p["sv-well"][0])]
    liquid = [_circle(s) for s in _subpaths(p["sv-liquid"][0])]
    # assay's liquid is in columns 1-3: the first 24 wells in PLR's column-major order
    assert len(liquid) == 24
    for o, l in zip(outlines[:24], liquid):
        assert abs(o[0] - l[0]) < 0.02 and abs(o[1] - l[1]) < 0.02 and l[2] < o[2]
    assert f'fill="{MOONSTONE}"' in assay_html


def test_plate_palette_is_inline_and_uppercase_for_the_theme_selectors(assay_html):
    """D3: the structural colours are presentation attributes the theme maps by attribute value."""
    root = _parse(assay_html)
    fills = {n.attrs.get("fill") for n in root.walk() if "fill" in n.attrs}
    strokes = {n.attrs.get("stroke") for n in root.walk() if "stroke" in n.attrs}
    assert {SHEET, MOONSTONE} <= fills
    assert {INK, RAIL} <= strokes
    assert _one(root, "sv-well").attrs["fill"] == SHEET and _one(root, "sv-well").attrs["stroke"] == RAIL
    assert _one(root, "sv-liquid").attrs["fill"] == MOONSTONE
    rect = root.find_all("rect")
    assert len(rect) == 1 and rect[0].attrs["stroke"] == INK and rect[0].attrs["fill"] == SHEET


def _one(root: _Node, cls: str) -> _Node:
    found = [n for n in root.walk() if cls in (n.attrs.get("class") or "").split()]
    assert len(found) == 1, f"class {cls}: {len(found)} elements"
    return found[0]


def test_plate_outline_is_a_two_mm_rounded_rect_of_the_plates_size(assay, assay_html):
    rect = _parse(assay_html).find_all("rect")[0]
    assert float(rect.attrs["rx"]) == 2.0
    assert abs(float(rect.attrs["width"]) - assay.get_size_x()) < 0.01
    assert abs(float(rect.attrs["height"]) - assay.get_size_y()) < 0.01


def test_plate_geometry_is_to_scale_with_the_front_edge_at_the_bottom(assay, assay_html):
    """A1 is at the back-left in PLR (largest y); drawn top-left. Pitch is PLR's 9 mm."""
    root = _parse(assay_html)
    rect = root.find_all("rect")[0]
    circles = [_circle(s) for s in _subpaths(_paths(root)["sv-well"][0])]
    ids = _ids_of(assay)
    pos = dict(zip(ids, circles))
    assert pos["A1"][1] < pos["H1"][1], "row A must be above row H (front edge at the bottom)"
    assert pos["A1"][0] < pos["A12"][0]
    assert abs((pos["A2"][0] - pos["A1"][0]) - 9.0) < 0.02
    assert abs((pos["B1"][1] - pos["A1"][1]) - 9.0) < 0.02
    ox, oy = float(rect.attrs["x"]), float(rect.attrs["y"])
    for ident, w in zip(ids, assay.get_all_items()):
        # drawn position relative to the plate outline = PLR's position, with y flipped
        want_x = ox + w.location.x + w.get_size_x() / 2
        want_y = oy + assay.get_size_y() - (w.location.y + w.get_size_y() / 2)
        assert abs(pos[ident][0] - want_x) < 0.02, ident
        assert abs(pos[ident][1] - want_y) < 0.02, ident
        assert abs(pos[ident][2] - w.get_size_x() / 2) < 0.011, ident


def test_plate_has_row_letters_and_column_numbers(assay_html):
    labels = [t for t, _ in _texts(_parse(assay_html))]
    assert sorted(t for t in labels if t.isalpha()) == list("ABCDEFGH")
    assert sorted((int(t) for t in labels if t.isdigit())) == list(range(1, 13))
    assert len(labels) == 20


def test_svg_is_emitted_at_three_px_per_mm_with_the_d5_min_width_and_scroll_wrapper(lw, floor, assay, assay_html):
    root = _parse(assay_html)
    svg_el = _svg_root(root)
    vb = [float(v) for v in svg_el.attrs["viewbox"].split()]
    w_mm, h_mm = vb[2], vb[3]
    assert abs(float(svg_el.attrs["width"]) - w_mm * 3) < 0.02
    assert abs(float(svg_el.attrs["height"]) - h_mm * 3) < 0.02
    d_min = min(min(w.get_size_x(), w.get_size_y()) for w in assay.get_all_items())
    s_min = max(0.88 * 3, 4 / d_min)
    assert svg_el.attrs["style"] == floor.svg_style(w_mm, s_min)
    assert svg_el.attrs["style"].startswith("max-width:100%;min-width:") and svg_el.attrs["style"].endswith("px;height:auto")
    assert float(svg_el.attrs["data-praxis-minw"]) == pytest.approx(floor.min_width_px(w_mm, s_min), abs=0.006)
    wrapper = svg_el.parent
    assert wrapper.attrs["style"] == "overflow-x:auto"
    # The worked check in D5: a Cor 96 plate at 3 px/mm has a min-width of about 390 px.
    assert 385 <= float(svg_el.attrs["data-praxis-minw"]) <= 395


def test_name_line_sentence_and_aria_label(lw, assay, assay_html):
    root = _parse(assay_html)
    name = root.find_all(cls="praxis-name")[0]
    assert name.text() == f"assay  Plate  {assay.model}"
    assert [c.attrs["class"] for c in name.children if isinstance(c, _Node)] == [
        "praxis-name__title", "praxis-name__type", "praxis-name__model",
    ]
    summary = root.find_all(cls="praxis-summary")[0]
    sentence = lw.plate_sentence(assay)
    assert summary.text() == sentence
    g = _figure_group(root)
    assert g.attrs["role"] == "img" and g.attrs["tabindex"] == "0"
    assert g.attrs["aria-label"] == sentence
    assert g.attrs["data-praxis-res"] == "assay"
    outer = root.children[0]
    assert "praxis-out" in outer.attrs["class"].split()


class _Balance(HTMLParser):
    """Every non-void start tag is closed by its own end tag, in order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"</{tag}> closes {self.stack[-1:]}")
        else:
            self.stack.pop()


def _is_balanced(doc: str) -> bool:
    b = _Balance()
    b.feed(doc)
    b.close()
    return not b.errors and not b.stack


def test_every_html_form_is_well_balanced(lw, assay, source, tips, real_plates):
    from pylabrobot.resources import Trough

    docs = [
        lw.render_html(assay), lw.render_html(source), lw.render_html(tips),
        lw.render_html(assay.get_item("A1")), lw.render_html(_rect_well()),
        lw.render_html(real_plates["greiner384"]),
        lw.render_html(Trough(name="t", size_x=1, size_y=1, size_z=1, max_volume=5)),
    ]
    for level in (1, 2):
        docs += [lw.render_html(assay, level=level), lw.render_html(tips, level=level)]
    assert all(_is_balanced(d) for d in docs)


def test_balance_checker_control_rejects_broken_markup():
    assert _is_balanced("<div><p>x</p><svg><path d='M0 0'/></svg></div>")
    assert not _is_balanced("<div><p>x</div>")
    assert not _is_balanced("<div><p>x</p>")


# --------------------------------------------------------------------------- 4. marks


def test_changed_and_fault_marks_are_their_own_paths_and_fault_carries_a_cross(lw, assay):
    changed = set(_ids_of(assay)[:24])  # columns 1-3
    fault = {f"{r}1" for r in "ABCDEFGH"}
    doc = lw.render_html(assay, changed=changed, fault=fault)
    root = _parse(doc)
    p = _paths(root)
    assert len(_subpaths(p["sv-changed"][0])) == 24 and _one(root, "sv-changed").attrs["stroke"] == ROSE
    ring = _one(root, "sv-fault")
    cross = _one(root, "sv-fault-x")
    assert len(_subpaths(ring.attrs["d"])) == 8 and ring.attrs["stroke"] == BRICK
    assert cross.attrs["d"].count("M") == 16 and cross.attrs["stroke"] == BRICK  # two strokes each
    assert f'stroke="{ROSE}"' in doc
    assert doc.count("<circle") == 0 and doc.count("<path") <= 8
    grid = _grid_of(root)
    flags = grid["flags"]
    ids = grid["ids"].split()
    assert len(flags) == len(ids) == 96
    for ident, flag in zip(ids, flags):
        want = (1 if ident in changed else 0) + (2 if ident in fault else 0)
        assert int(flag) == want, ident


def test_no_marks_means_no_mark_paths(assay_html):
    p = _paths(_parse(assay_html))
    assert not {"sv-changed", "sv-fault", "sv-fault-x"} & set(p)
    assert set(_grid_of(_parse(assay_html))["flags"]) == {"0"}


def test_an_unknown_mark_id_is_refused(lw, assay):
    with pytest.raises(ValueError):
        lw.render_html(assay, changed={"Z99"})
    with pytest.raises(ValueError):
        lw.render_html(assay, fault={"A1", "nope"})


def test_volume_override_draws_committed_volume_not_pending(lw, fx):
    """B6's contract: ``volume_of`` swaps the volume the figure draws (committed vs pending)."""
    plate = fx.cor_96_wellplate_360uL_Fb(name="res")
    h12 = plate.get_item("H12")
    h12.tracker.set_volume(100)
    h12.tracker.remove_liquid(40)  # uncommitted: committed 100, pending 60
    assert h12.tracker.volume == 100 and h12.tracker.get_used_volume() == 60
    r_well = h12.get_size_x() / 2

    def radius(doc):
        return _circle(_subpaths(_paths(_parse(doc))["sv-liquid"][0])[-1])[2]

    pending = radius(lw.render_html(plate))
    committed = radius(lw.render_html(plate, volume_of=lambda c: c.tracker.volume))
    assert abs(pending - r_well * math.sqrt(60 / 360)) <= 1e-3
    assert abs(committed - r_well * math.sqrt(100 / 360)) <= 1e-3
    assert abs(committed - pending) > 0.1
    assert lw.plate_sentence(plate, volume_of=lambda c: c.tracker.volume).startswith("1 of 96 wells hold liquid, 100 µL each")
    assert lw.plate_sentence(plate).startswith("1 of 96 wells hold liquid, 60 µL each")


# --------------------------------------------------------------------------- 5. the grid descriptor


def test_grid_descriptor_matches_plr_geometry_and_state(lw, assay):
    root = _parse(lw.render_html(assay))
    grid = _grid_of(root)
    assert set(grid) == {"v", "kind", "res", "x0", "y0", "dx", "dy", "rows", "cols", "ids", "vals", "flags"}
    assert grid["v"] == 1 and grid["kind"] == "volume" and grid["res"] == "assay"
    assert grid["rows"] == 8 and grid["cols"] == 12
    ids = grid["ids"].split()
    assert ids == _ids_of(assay)
    assert grid["vals"] == [round(v, 1) if v % 1 else int(v) for v in _volumes_of(assay)]
    assert len(grid["vals"]) == len(ids) == len(grid["flags"])
    assert grid["dx"] == pytest.approx(assay.item_dx, abs=0.011)
    assert grid["dy"] == pytest.approx(abs(assay.item_dy), abs=0.011)
    # every id's grid position is the centre of the circle that is drawn for it
    circles = [_circle(s) for s in _subpaths(_paths(root)["sv-well"][0])]
    for ident, (cx, cy, _r) in zip(ids, circles):
        m = re.fullmatch(r"([A-Z]+)(\d+)", ident)
        row, col = _row_index(m.group(1)), int(m.group(2)) - 1
        assert abs(grid["x0"] + col * grid["dx"] - cx) < 0.02, ident
        assert abs(grid["y0"] + row * grid["dy"] - cy) < 0.02, ident


def _grid_problems(grid: dict, plate) -> list[str]:
    """Independent verifier of a plate descriptor, used both ways (must pass and must fail)."""
    problems = []
    if grid["ids"].split() != _ids_of(plate):
        problems.append("ids")
    want = [round(v, 1) if v % 1 else int(v) for v in _volumes_of(plate)]
    if grid["vals"] != want:
        problems.append("vals")
    if grid["rows"] != 8 or grid["cols"] != 12:
        problems.append("shape")
    return problems


def test_grid_verifier_control_rejects_tampered_descriptors(lw, assay):
    grid = _grid_of(_parse(lw.render_html(assay)))
    assert _grid_problems(grid, assay) == []
    bad = json.loads(json.dumps(grid))
    bad["vals"][0] += 1
    assert "vals" in _grid_problems(bad, assay)
    bad = json.loads(json.dumps(grid))
    bad["ids"] = " ".join(reversed(grid["ids"].split()))
    assert "ids" in _grid_problems(bad, assay)
    bad = json.loads(json.dumps(grid))
    bad["cols"] = 11
    assert "shape" in _grid_problems(bad, assay)


def test_tiprack_grid_and_well_grid(lw, tips, assay):
    g = _grid_of(_parse(lw.render_html(tips)))
    assert g["kind"] == "tip" and g["res"] == "tips_300" and g["rows"] == 8 and g["cols"] == 12
    ids = g["ids"].split()
    assert ids == _ids_of(tips)
    assert g["vals"] == [1 if tips.get_item(i).tip is not None else 0 for i in ids]
    assert g["vals"].count(0) == 24 and g["vals"].count(1) == 72
    well = assay.get_item("A1")
    gw = _grid_of(_parse(lw.render_html(well)))
    assert gw["kind"] == "volume" and gw["ids"] == "A1" and gw["vals"] == [50] and gw["rows"] == 1 and gw["cols"] == 1
    assert gw["res"] == well.name


# --------------------------------------------------------------------------- 6. the tip rack figure


@pytest.fixture(scope="module")
def tips_html(lw, tips):
    return lw.render_html(tips)


def test_tiprack_paths_are_one_per_state_and_no_circles(tips_html):
    root = _parse(tips_html)
    assert tips_html.count("<circle") == 0 and tips_html.count("<script") == 0 and tips_html.count("<style") == 0
    for cls, n in (("sv-tip-ring", 72), ("sv-tip", 72), ("sv-tip-gone", 24)):
        found = [p for p in root.find_all("path") if p.attrs.get("class") == cls]
        assert len(found) == 1, f"{cls}: {len(found)} <path> elements (must be exactly one)"
        assert len(_subpaths(found[0].attrs["d"])) == n, cls
    assert len(root.find_all("path")) == 3


def test_tiprack_palette_and_dashed_taken_rings(tips_html):
    root = _parse(tips_html)
    ring, core, gone = _one(root, "sv-tip-ring"), _one(root, "sv-tip"), _one(root, "sv-tip-gone")
    assert (ring.attrs["fill"], ring.attrs["stroke"]) == (SHEET, INK)
    # the core is an ink dot: a zero-length subpath under a round cap (it keeps the rack in budget)
    assert core.attrs["stroke"] == INK and core.attrs["fill"] == "none" and core.attrs["stroke-linecap"] == "round"
    assert gone.attrs["fill"] == "none" and gone.attrs["stroke"] == RAIL and "stroke-dasharray" in gone.attrs


def test_tiprack_ring_size_comes_from_plr_and_cores_sit_inside(tips, tips_html):
    root = _parse(tips_html)
    spot = tips.get_item("A1")
    assert spot.get_size_x() == 7.2  # the pin's tip spot (9.0 at 0.2.2)
    ring_path, core_path = _one(root, "sv-tip-ring"), _one(root, "sv-tip")
    rings = [_circle(s) for s in _subpaths(ring_path.attrs["d"])]
    cores = [_dot(s) for s in _subpaths(core_path.attrs["d"])]
    assert len(rings) == len(cores) == 72
    for c in rings:
        assert abs(c[2] - 3.6) < 0.011
    for ring, core in zip(rings, cores):
        assert abs(ring[0] - core[0]) < 0.02 and abs(ring[1] - core[1]) < 0.02
    # the dot's diameter is the stroke width: 0.45 of the ring's, and it fits inside the ring
    assert float(core_path.attrs["stroke-width"]) == pytest.approx(2 * 3.6 * 0.45, abs=0.006)
    assert float(core_path.attrs["stroke-width"]) < 2 * 3.6


def _dot(sp: str):
    m = re.fullmatch(rf"M({_NUM})[ ,]?({_NUM})h0", sp)
    assert m, sp
    return float(m.group(1)), float(m.group(2))


def test_tiprack_present_and_taken_rings_cover_every_spot_exactly_once(tips, tips_html):
    root = _parse(tips_html)
    ids = _ids_of(tips)
    present_ids = [i for i in ids if tips.get_item(i).tip is not None]
    taken_ids = [i for i in ids if tips.get_item(i).tip is None]
    rings = [_circle(s) for s in _subpaths(_one(root, "sv-tip-ring").attrs["d"])]
    gone = [_circle(s) for s in _subpaths(_one(root, "sv-tip-gone").attrs["d"])]
    grid = _grid_of(root)
    for ids_, circles in ((present_ids, rings), (taken_ids, gone)):
        assert len(ids_) == len(circles)
        for ident, (cx, cy, _r) in zip(ids_, circles):
            m = re.fullmatch(r"([A-Z]+)(\d+)", ident)
            row, col = _row_index(m.group(1)), int(m.group(2)) - 1
            assert abs(grid["x0"] + col * grid["dx"] - cx) < 0.02
            assert abs(grid["y0"] + row * grid["dy"] - cy) < 0.02


def test_full_rack_has_no_taken_path_and_empty_rack_has_no_tip_paths(lw, fx):
    full = _parse(lw.render_html(fx.hamilton_96_tiprack_300uL_filter(name="full")))
    assert {p.attrs["class"] for p in full.find_all("path")} == {"sv-tip-ring", "sv-tip"}
    empty = _parse(lw.render_html(_rack_with_used(fx, "empty", _all_ids(8, 12))))
    assert {p.attrs["class"] for p in empty.find_all("path")} == {"sv-tip-gone"}


def test_tiprack_name_line_and_sentence(lw, tips, tips_html):
    root = _parse(tips_html)
    assert root.find_all(cls="praxis-name")[0].text() == f"tips_300  EmbeddedTipRack  {tips.model}"
    assert root.find_all(cls="praxis-summary")[0].text() == "72 of 96 tips left. Columns 1–3 used."
    assert _figure_group(root).attrs["aria-label"] == "72 of 96 tips left. Columns 1–3 used."


# --------------------------------------------------------------------------- 7. the well figure


def test_well_figure_is_a_circle_subpath_with_a_sqrt_liquid_disk(lw, assay):
    well = assay.get_item("A1")
    doc = lw.render_html(well)
    root = _parse(doc)
    assert doc.count("<circle") == 0 and doc.count("<script") == 0
    outline = _subpaths(_one(root, "sv-well").attrs["d"])
    liquid = _subpaths(_one(root, "sv-liquid").attrs["d"])
    assert len(outline) == 1 and len(liquid) == 1
    r = well.get_size_x() / 2
    assert abs(_circle(outline[0])[2] - r) < 0.011
    assert abs(_circle(liquid[0])[2] - r * math.sqrt(50 / 360)) <= 1e-3
    assert _figure_group(root).attrs["aria-label"] == "assay A1 holds 50 µL of 360 µL."
    assert root.find_all(cls="praxis-summary")[0].text() == "assay A1 holds 50 µL of 360 µL."
    expected_name = f"{well.name}  Well" + (f"  {well.model}" if well.model else "")
    assert root.find_all(cls="praxis-name")[0].text() == expected_name


def test_empty_well_has_no_liquid_path(lw, assay):
    root = _parse(lw.render_html(assay.get_item("H12")))
    assert "sv-liquid" not in _paths(root)


def _rect_well(name="rw", sx=8.0, sy=6.0, volume=50.0, max_volume=200.0):
    from pylabrobot.resources import CrossSectionType, Well

    w = Well(
        name=name, size_x=sx, size_y=sy, size_z=10, max_volume=max_volume,
        cross_section_type=CrossSectionType.RECTANGLE,
    )
    w.tracker.set_volume(volume)
    return w


def test_a_rectangular_well_renders_as_a_rect_subpath(lw):
    w = _rect_well()
    root = _parse(lw.render_html(w))
    outline = _subpaths(_one(root, "sv-well").attrs["d"])
    liquid = _subpaths(_one(root, "sv-liquid").attrs["d"])
    assert len(outline) == 1 and _circle(outline[0]) is None
    ox, oy, ow, oh = _rect(outline[0])
    assert (round(ow, 2), round(oh, 2)) == (8.0, 6.0)
    lx, ly, lw_, lh = _rect(liquid[0])
    f = math.sqrt(50 / 200)
    assert abs(lw_ - 8.0 * f) < 0.011 and abs(lh - 6.0 * f) < 0.011  # area is proportional to volume
    assert abs((lx + lw_ / 2) - (ox + ow / 2)) < 0.011 and abs((ly + lh / 2) - (oy + oh / 2)) < 0.011


def test_a_plate_of_rectangular_wells_uses_rect_subpaths_and_the_smaller_side_as_d_min(lw):
    from pylabrobot.resources import Coordinate, CrossSectionType, Plate, Well

    wells = {}
    for c in range(2):
        for r in range(2):
            ident = f"{'AB'[r]}{c + 1}"
            w = Well(
                name=f"rp_{ident}", size_x=8, size_y=1.2, size_z=10, max_volume=100,
                cross_section_type=CrossSectionType.RECTANGLE,
            )
            w.location = Coordinate(4 + c * 10, 20 - r * 8, 1)
            wells[ident] = w
    plate = Plate(name="rp", size_x=30, size_y=30, size_z=10, ordered_items=wells)
    root = _parse(lw.render_html(plate))
    outline = _subpaths(_one(root, "sv-well").attrs["d"])
    assert len(outline) == 4 and all(_circle(s) is None and _rect(s) for s in outline)
    svg_el = _svg_root(root)
    w_mm = float(svg_el.attrs["viewbox"].split()[2])
    s_min = float(svg_el.attrs["data-praxis-minw"]) / w_mm
    # d_min is the SMALLER side (1.2 mm): 4 / 1.2 = 3.33 beats the 0.88 * 3 text floor. Using the
    # longer side (8 mm) would have given 2.64.
    assert s_min == pytest.approx(4 / 1.2, abs=0.005)
    assert _floor_problems(lw.render_html(plate)) == []


# --------------------------------------------------------------------------- 8. AC-12 on real geometry


def _real_plates():
    from pylabrobot.resources.greiner import Greiner_384_wellplate_28ul_Fb
    from pylabrobot.resources.tecan.plates import Hibase_Greiner_1536_Well

    return {
        "greiner384": Greiner_384_wellplate_28ul_Fb(name="p384"),
        "tecan1536": Hibase_Greiner_1536_Well(name="p1536"),
    }


@pytest.fixture(scope="module")
def real_plates():
    return _real_plates()


def _floor_problems(doc: str, expected_s_min: float | None = None) -> list[str]:
    """AC-12 checker: text >= 11 px, wells >= 4 px, at the s_min the figure declares."""
    root = _parse(doc)
    svg_el = _svg_root(root)
    w_mm = float(svg_el.attrs["viewbox"].split()[2])
    m = re.search(r"min-width:([\d.]+)px", svg_el.attrs["style"])
    s_min = float(m.group(1)) / w_mm
    problems = []
    for text, size in _texts(root):
        if size * s_min < 11 - 1e-9:
            problems.append(f"text {text!r}: {size * s_min:.3f} px")
    for cls in ("sv-well", "sv-tip-ring"):
        for n in root.find_all("path", cls=cls):
            for sp in _subpaths(n.attrs["d"]):
                c = _circle(sp)
                d = 2 * c[2] if c else min(_rect(sp)[2:])
                if d * s_min < 4 - 1e-9:
                    problems.append(f"{cls}: {d * s_min:.3f} px")
    if expected_s_min is not None and abs(s_min - expected_s_min) > 0.002:
        problems.append(f"s_min {s_min:.4f} != {expected_s_min:.4f}")
    return problems


def _d_min(res) -> float:
    return min(min(c.get_size_x(), c.get_size_y()) for c in res.get_all_items())


@pytest.mark.parametrize("which", ["fixture96", "tiprack", "greiner384", "tecan1536"])
def test_ac12_text_and_wells_meet_the_floor_on_real_plr_geometry(lw, source, tips, real_plates, which):
    res = {"fixture96": source, "tiprack": tips, **real_plates}[which]
    doc = lw.render_html(res)  # level 0, before the byte ladder (the 1536 plate is over the cap)
    expected = max(0.88 * 3, 4 / _d_min(res))
    assert _floor_problems(doc, expected) == []
    root = _parse(doc)
    assert _texts(root), "a figure with no labels cannot have checked the text floor"


def test_ac12_checker_controls_fail_on_a_shrunken_font_min_width_and_well(lw, source):
    doc = lw.render_html(source)
    assert _floor_problems(doc) == []
    small_font = re.sub(r'font-size="[\d.]+"', 'font-size="3.5"', doc)
    assert any("text" in p for p in _floor_problems(small_font))
    small_min = re.sub(r"min-width:[\d.]+px", "min-width:100px", doc)
    assert _floor_problems(small_min)
    # wells shrunk below 4 px at the declared s_min
    shrunk = re.sub(r"a3\.43 3\.43", "a0.5 0.5", doc)  # d = 1 mm -> 2.64 px at s_min
    assert any("sv-well" in p for p in _floor_problems(shrunk))


def test_real_geometry_replaces_the_floor_tests_stand_ins(source, tips, real_plates):
    """The stand-ins in test_display_floor.py (6.86, 3.6, 1.7, 7.2) against what PLR really has."""
    assert min(source.get_item("A1").get_size_x(), source.get_item("A1").get_size_y()) == 6.86
    assert tips.get_item("A1").get_size_x() == 7.2
    assert real_plates["greiner384"].get_item("A1").get_size_x() == 3.3  # stand-in said 3.6
    assert real_plates["tecan1536"].get_item("A1").get_size_x() == 2.3  # stand-in said 1.7


@pytest.mark.parametrize("which", ["greiner384", "tecan1536"])
def test_plates_of_384_wells_or_more_are_square_cells_with_every_kth_label(lw, floor, real_plates, which):
    plate = real_plates[which]
    doc = lw.render_html(plate)
    root = _parse(doc)
    outline = _subpaths(_one(root, "sv-well").attrs["d"])
    assert len(outline) == plate.num_items
    assert all(_circle(s) is None for s in outline), "384+ wells must be square cells"
    d = _d_min(plate)
    for sp in outline[:5] + outline[-5:]:
        _x, _y, w, h = _rect(sp)
        assert abs(w - d) < 0.011 and abs(h - d) < 0.011
    svg_el = _svg_root(root)
    w_mm = float(svg_el.attrs["viewbox"].split()[2])
    s_min = float(svg_el.attrs["data-praxis-minw"]) / w_mm
    pitch = plate.item_dx
    k = next((k for k in (1, 2, 4, 8) if k * pitch * s_min >= 24 - 1e-9), 8)
    assert k == floor.label_step_k(pitch, s_min) and k > 1
    labels = [t for t, _ in _texts(root)]
    cols = sorted(int(t) for t in labels if t.isdigit())
    n_cols = plate.num_items_x
    assert cols == list(range(1, n_cols + 1, k))
    rows = [t for t in labels if t.isalpha()]
    n_rows = plate.num_items_y
    assert len(rows) == len(range(0, n_rows, k))


def test_a_96_well_plate_keeps_a_label_on_every_row_and_column(assay_html):
    labels = [t for t, _ in _texts(_parse(assay_html))]
    assert len(labels) == 20  # k applies only from 384 wells (D5)


# --------------------------------------------------------------------------- 9. the bundle and its stamp


def test_bundle_shape_and_stamp_for_a_plate(lw, svg, assay):
    data, meta = lw.render(assay, rev=7, session="sess-abc", exec_count=12)
    assert set(data) == {"text/html", "text/plain"}
    assert data["text/plain"] == lw.plate_sentence(assay)
    assert meta == {"praxis": {"v": 1, "kind": "plate", "resource": "assay", "rev": 7, "session": "sess-abc", "exec": 12}}
    assert set(meta["praxis"]) == {"v", "kind", "resource", "rev", "session", "exec"}
    svg.check_bundle(data, meta)
    assert "image/svg+xml" not in data
    html = data["text/html"]
    assert "<script" not in html and "<style" not in html


def test_stamp_values_by_kind_and_injected_fields(lw, svg, tips, assay):
    well = assay.get_item("B3")
    for res, kind in ((tips, "tiprack"), (well, "container"), (assay, "plate")):
        data, meta = lw.render(res, rev=0, session="s", exec_count=None)
        assert meta["praxis"]["kind"] == kind
        assert meta["praxis"]["resource"] == res.name
        assert meta["praxis"]["rev"] == 0 and meta["praxis"]["exec"] is None
        svg.check_bundle(data, meta)
    _d, meta = lw.render(assay, rev=None, session="s", exec_count=3)
    assert meta["praxis"]["rev"] is None and meta["praxis"]["exec"] == 3
    assert lw.render(assay, rev=1, session="x", exec_count=1)[1] != lw.render(assay, rev=2, session="x", exec_count=1)[1]


def test_bundle_is_refused_when_the_session_is_missing(lw, svg, assay):
    """The stamp is validated by svg.check_bundle: an empty session id is a caller bug, not a bundle."""
    with pytest.raises(svg.UnsafeHtmlError):
        lw.render(assay, rev=1, session="", exec_count=1)


def test_render_is_deterministic_and_does_not_touch_plr_state(lw, assay, tips):
    def snapshot():
        return (
            tuple(_volumes_of(assay)),
            tuple(s.tip is not None for s in tips.get_all_items()),
            tuple(w.tracker.volume for w in assay.get_all_items()),
        )

    before = snapshot()
    a = lw.render(assay, rev=1, session="s", exec_count=1)
    b = lw.render(assay, rev=1, session="s", exec_count=1)
    lw.render(tips, rev=1, session="s", exec_count=1)
    assert a == b
    assert snapshot() == before


def test_an_unsupported_resource_is_a_type_error(lw):
    from pylabrobot.resources import Resource

    with pytest.raises(TypeError):
        lw.render(Resource(name="x", size_x=1, size_y=1, size_z=1), rev=1, session="s", exec_count=1)


# --------------------------------------------------------------------------- 10. sentence-only containers


def test_trough_is_a_container_bundle_with_no_drawing(lw, svg):
    from pylabrobot.resources import Trough

    t = Trough(name="reservoir", size_x=100, size_y=20, size_z=30, max_volume=1000, model="agenbio_1_troughplate_100mL_Fl")
    t.tracker.set_volume(250.5)
    data, meta = lw.render(t, rev=2, session="s", exec_count=5)
    assert meta["praxis"]["kind"] == "container" and meta["praxis"]["resource"] == "reservoir"
    assert "<svg" not in data["text/html"] and "<path" not in data["text/html"]
    assert data["text/plain"] == "reservoir holds 250.5 µL of 1,000 µL."
    root = _parse(data["text/html"])
    assert root.find_all(cls="praxis-name")[0].text() == "reservoir  Trough  agenbio_1_troughplate_100mL_Fl"
    assert root.find_all(cls="praxis-summary")[0].text() == data["text/plain"]
    svg.check_bundle(data, meta)


def test_container_with_infinite_max_volume_reads_holds_v_only(lw):
    from pylabrobot.resources import Trough

    t = Trough(name="waste", size_x=100, size_y=20, size_z=30, max_volume=math.inf)
    t.tracker.set_volume(80)
    data, _meta = lw.render(t, rev=1, session="s", exec_count=1)
    assert data["text/plain"] == "waste holds 80 µL."
    assert "<svg" not in data["text/html"]


def test_render_figure_is_empty_for_sentence_only_containers(lw):
    from pylabrobot.resources import Trough

    t = Trough(name="t", size_x=1, size_y=1, size_z=1, max_volume=10)
    assert lw.render_figure(t) == ""
    assert lw.render_figure(_rect_well()) != ""


# --------------------------------------------------------------------------- 11. dispatch is by class


def test_an_embedded_tip_rack_is_a_tip_rack_by_class(lw, tips):
    from pylabrobot.resources import EmbeddedTipRack, TipRack

    assert isinstance(tips, TipRack) and type(tips) is EmbeddedTipRack and type(tips) is not TipRack
    assert lw.kind_of(tips) == "tiprack"


def test_a_renamed_subclass_still_resolves_and_a_borrowed_name_does_not(lw, fx):
    from pylabrobot.resources import EmbeddedTipRack, Resource

    rack = fx.hamilton_96_tiprack_300uL_filter(name="odd")
    rack.__class__ = type("CompletelyDifferentName", (EmbeddedTipRack,), {})
    assert lw.kind_of(rack) == "tiprack"
    assert "72" not in lw.tiprack_sentence(rack) and lw.tiprack_sentence(rack).startswith("96 of 96 tips left")

    class TipRack(Resource):  # borrows the name only; it is not a PLR TipRack
        pass

    impostor = TipRack(name="impostor", size_x=1, size_y=1, size_z=1)
    assert type(impostor).__name__ == "TipRack"
    with pytest.raises(TypeError):
        lw.kind_of(impostor)
    with pytest.raises(TypeError):
        lw.render(impostor, rev=1, session="s", exec_count=1)


def _compares_type_names(src: str) -> list[int]:
    """Line numbers of comparisons against a ``__name__`` (dispatch by type-name string)."""
    hits = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Compare):
            for side in [node.left, *node.comparators]:
                if isinstance(side, ast.Attribute) and side.attr == "__name__":
                    hits.append(node.lineno)
    return hits


def test_no_dispatch_on_a_type_name_string_in_labware_source(lw):
    assert _compares_type_names(_LABWARE_PATH.read_text(encoding="utf-8")) == []


def test_type_name_lint_control_flags_a_dispatch_on_the_name():
    assert _compares_type_names("if type(x).__name__ == 'TipRack':\n    pass\n") == [1]
    assert _compares_type_names("name = type(x).__name__\n") == []


# --------------------------------------------------------------------------- 12. escaping


def _hostile_problems(doc: str, name: str, attr_values: dict[str, str] | None = None) -> list[str]:
    """Independent escape checker: no element or attribute the renderer did not intend, and the
    hostile string comes back byte-identical through a browser-style parse."""
    problems = []
    if re.search(r"<\s*(script|style|img|iframe|object)\b", doc, re.I):
        problems.append("raw script/style/img element")
    allowed = {"div", "p", "span", "svg", "g", "rect", "path", "text", "#root"}
    root = _parse(doc)
    for n in root.walk():
        if n.tag not in allowed:
            problems.append(f"unexpected element <{n.tag}>")
        for k in n.attrs:
            if k.startswith("on") or k in ("href", "src", "srcdoc") or (k.startswith("data-") and k not in ("data-praxis-res", "data-praxis-grid", "data-praxis-minw")):
                problems.append(f"unexpected attribute {k}")
    if name in doc and name != html_mod.escape(name, quote=True):
        problems.append("the raw hostile string appears in the html")
    g = [n for n in root.walk() if n.tag == "g" and "data-praxis-res" in n.attrs]
    if g and g[0].attrs["data-praxis-res"] != name:
        problems.append("data-praxis-res does not round-trip")
    for key, want in (attr_values or {}).items():
        if g and g[0].attrs.get(key) != want:
            problems.append(f"{key} does not round-trip")
    return problems


@pytest.mark.parametrize("name", HOSTILE_NAMES)
def test_hostile_plate_name_is_escaped_everywhere(lw, svg, fx, name):
    plate = fx.cor_96_wellplate_360uL_Fb(name=name)
    plate.get_item("A1").tracker.set_volume(50)
    plate.model = f"<i>{name}</i>"
    data, meta = lw.render(plate, rev=1, session="s", exec_count=1)
    doc = data["text/html"]
    assert _hostile_problems(doc, name) == []
    root = _parse(doc)
    assert _grid_of(root)["res"] == name  # data-praxis-grid round-trips through unescape + json
    assert root.find_all(cls="praxis-name__title")[0].text() == name
    assert root.find_all(cls="praxis-name__model")[0].text() == f"<i>{name}</i>"
    assert meta["praxis"]["resource"] == name
    svg.check_output_html(doc)


def test_hostile_name_html_has_zero_raw_b_tag(lw, fx):
    name = '<b>&"\'x'
    plate = fx.cor_96_wellplate_360uL_Fb(name=name)
    doc = lw.render(plate, rev=1, session="s", exec_count=1)[0]["text/html"]
    assert "<b>" not in doc
    assert "&lt;b&gt;&amp;&quot;&#x27;x" in doc


@pytest.mark.parametrize("name", HOSTILE_NAMES)
def test_hostile_well_container_and_rack_names_are_escaped_in_aria_label_and_text(lw, fx, name):
    plate = fx.cor_96_wellplate_360uL_Fb(name=name)
    well = plate.get_item("A1")
    well.tracker.set_volume(50)
    doc = lw.render(well, rev=1, session="s", exec_count=1)[0]["text/html"]
    sentence = f"{name} A1 holds 50 µL of 360 µL."
    assert _hostile_problems(doc, well.name, {"aria-label": sentence}) == []
    assert _parse(doc).find_all(cls="praxis-summary")[0].text() == sentence
    rack = fx.hamilton_96_tiprack_300uL_filter(name=name)
    rdoc = lw.render(rack, rev=1, session="s", exec_count=1)[0]["text/html"]
    assert _hostile_problems(rdoc, name) == []
    from pylabrobot.resources import Trough

    t = Trough(name=name, size_x=1, size_y=1, size_z=1, max_volume=10)
    tdoc, tmeta = lw.render(t, rev=1, session="s", exec_count=1)
    assert _hostile_problems(tdoc["text/html"], name) == []
    assert tdoc["text/plain"] == f"{name} holds 0 µL of 10 µL."


def test_escape_checker_control_flags_naive_markup():
    """Negative control: markup built with a bare f-string fails the very checker the renderer passes."""
    name = '"><script>alert(1)</script>'
    naive = f'<div class="praxis-out"><svg><g data-praxis-res="{name}"></g></svg><p>{name}</p></div>'
    assert _hostile_problems(naive, name)
    name2 = "<b>x"
    assert _hostile_problems(f'<div><p class="praxis-name">{name2}</p></div>', name2)


def test_a_huge_hostile_name_never_breaks_the_cap_and_the_text_is_kept(lw, svg, budget, fx):
    name = "<" * 100_000
    plate = fx.cor_96_wellplate_360uL_Fb(name=name)
    plate.get_item("A1").tracker.set_volume(50)
    data, meta = lw.render(plate, rev=1, session="s", exec_count=1)
    doc = data["text/html"]
    assert budget.html_bytes(doc) <= CAP
    assert budget.OMISSION_SENTENCE in doc  # the drawing degraded to level 2
    assert data["text/plain"].startswith("1 of 96 wells hold liquid")
    assert meta["praxis"]["resource"] == name  # the stamp is JSON, not html: it keeps the full name
    svg.check_bundle(data, meta)


def test_long_names_are_shortened_for_display_only(lw, svg, fx):
    """A 250-character name reads shortened in the text, but the shell's exact match on
    ``data-praxis-res`` and the stamp keep the FULL name (D2: never a selector from a name)."""
    name = "n" * 249 + "Z"
    plate = fx.cor_96_wellplate_360uL_Fb(name=name)
    plate.get_item("B2").tracker.set_volume(30)
    data, meta = lw.render(plate, rev=1, session="s", exec_count=1)
    root = _parse(data["text/html"])
    assert _figure_group(root).attrs["data-praxis-res"] == name
    assert _grid_of(root)["res"] == name
    assert meta["praxis"]["resource"] == name
    shown = root.find_all(cls="praxis-name__title")[0].text()
    assert len(shown) == 200 and shown.endswith("…") and name.startswith(shown[:-1])
    well = plate.get_item("B2")
    sentence = lw.container_sentence(well)
    assert sentence.startswith(shown + " B2 holds 30 µL of 360 µL")


def test_labware_source_never_builds_markup_by_hand_or_escapes_on_its_own(lw):
    problems = _markup_lint(_LABWARE_PATH.read_text(encoding="utf-8"))
    assert problems == []


def _markup_lint(src: str) -> list[str]:
    """Hand-built markup or a private escaper in the module body (docstrings excluded)."""
    tree = ast.parse(src)
    doc_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant):
                doc_ids.add(id(first.value))
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_ids:
            if re.search(r"<[A-Za-z/!]", node.value):
                problems.append(f"line {node.lineno}: markup literal {node.value[:30]!r}")
        if isinstance(node, ast.Import):
            problems += [f"line {node.lineno}: import {a.name}" for a in node.names if a.name in ("html", "cgi", "xml.sax.saxutils")]
        if isinstance(node, ast.ImportFrom) and node.module in ("html", "cgi", "xml.sax.saxutils"):
            problems.append(f"line {node.lineno}: from {node.module} import")
    return problems


def test_markup_lint_controls():
    assert _markup_lint("x = f'<p>{y}</p>'\n")
    assert _markup_lint("import html\n")
    assert _markup_lint("from html import escape\n")
    assert _markup_lint('"""doc <b>"""\nx = 1\n') == []


# --------------------------------------------------------------------------- 13. S2: what survives


def _s2_text(doc: str) -> str:
    """What an untrusted reopen shows (S2-B): the SVG subtree is gone, and so is every attribute
    but ``class`` (which carries no text)."""

    def text(node):
        if node.tag == "svg":
            return ""
        return "".join(c if isinstance(c, str) else text(c) for c in node.children)

    return text(_parse(doc))


def test_name_line_and_sentence_are_meaningful_without_the_svg_or_any_attribute(lw, assay, tips):
    for res, sentence in ((assay, lw.plate_sentence(assay)), (tips, lw.tiprack_sentence(tips))):
        shown = _s2_text(lw.render_html(res))
        name_line = f"{res.name}  {type(res).__name__}  {res.model}"
        assert name_line in shown and sentence in shown
        # nothing else survives: the row letters and column numbers lived only in the SVG
        assert shown.replace(name_line, "").replace(sentence, "") == ""


def test_s2_simulation_control_loses_text_that_lives_only_in_the_svg(lw, assay):
    doc = lw.render_html(assay)
    labels = [t for t, _ in _texts(_parse(doc))]
    assert len(labels) == 20  # there IS svg-only text (row letters, column numbers) to lose ...
    name_line = f"assay  Plate  {assay.model}"
    # ... and the simulation loses all of it: only the name line and the sentence remain
    assert _s2_text(doc).replace(name_line, "").replace(lw.plate_sentence(assay), "") == ""
    assert _s2_text("<div><svg><text>only-in-svg</text></svg><p>kept</p></div>") == "kept"


def test_every_s2_probe_attribute_is_emitted_by_some_figure(lw, assay, tips):
    """The S2 branch only changes what survives on reopen; the figures emit every attribute."""
    fault = {"A1", "B1"}
    docs = [lw.render_html(assay, changed={"A1"}, fault=fault), lw.render_html(tips)]
    emitted: set[str] = set()
    for doc in docs:
        for n in _parse(doc).walk():
            emitted |= set(n.attrs)
    wanted = {
        "fill", "stroke", "stroke-width", "stroke-dasharray", "class", "style", "role", "aria-label",
        "tabindex", "data-praxis-res", "data-praxis-grid", "data-praxis-minw", "viewbox",
    }
    assert wanted <= emitted, sorted(wanted - emitted)
    tags = {n.tag for doc in docs for n in _parse(doc).walk()}
    assert {"svg", "g", "path", "rect", "text"} <= tags


# --------------------------------------------------------------------------- 14. budget (one output)


def test_96_well_plate_and_tip_rack_meet_their_d4_targets(lw, budget, source, tips, record_property):
    plate = budget.html_bytes(lw.render(source, rev=1, session="s", exec_count=1)[0]["text/html"])
    rack = budget.html_bytes(lw.render(tips, rev=1, session="s", exec_count=1)[0]["text/html"])
    record_property("bytes_plate96_full", plate)
    record_property("bytes_tiprack", rack)
    assert plate <= BUDGET_TARGETS["plate96"], f"96-well plate is {plate} bytes"
    assert rack <= BUDGET_TARGETS["tiprack"], f"tip rack is {rack} bytes"


def test_the_ladder_levels_shrink_and_meet_the_documented_shapes(lw, budget, svg, source):
    full = lw.render_html(source, level=budget.LEVEL_FULL)
    block = lw.render_html(source, level=budget.LEVEL_BLOCKS)
    omit = lw.render_html(source, level=budget.LEVEL_OMITTED)
    sizes = [budget.html_bytes(d) for d in (full, block, omit)]
    assert sizes[0] > sizes[1] > sizes[2]
    # level 1: a filled block, no grid, no wells, but still a resource with a text alternative
    root = _parse(block)
    g = _figure_group(root)
    assert "data-praxis-grid" not in g.attrs and g.attrs["aria-label"] == lw.plate_sentence(source)
    assert "sv-well" not in _paths(root) and "sv-liquid" not in _paths(root)
    assert len(root.find_all("rect")) == 1 and root.find_all("rect")[0].attrs["fill"] == RAIL
    assert not root.find_all("text")
    # level 2: name line + sentence + the omission sentence, and no drawing
    assert "<svg" not in omit and budget.OMISSION_SENTENCE in omit and lw.plate_sentence(source) in omit
    assert budget.OMISSION_SENTENCE not in full and budget.OMISSION_SENTENCE not in block
    for d in (full, block, omit):
        svg.check_output_html(d)


def test_a_1536_well_plate_degrades_to_a_block_within_the_cap(lw, budget, svg, real_plates):
    plate = real_plates["tecan1536"]
    for w in plate.get_all_items()[:200]:
        w.tracker.set_volume(10)
    assert budget.html_bytes(lw.render_html(plate)) > CAP, "the control needs a plate that is over the cap at level 0"
    data, meta = lw.render(plate, rev=1, session="s", exec_count=1)
    doc = data["text/html"]
    assert budget.html_bytes(doc) <= CAP
    root = _parse(doc)
    assert "sv-well" not in _paths(root) and "data-praxis-grid" not in _figure_group(root).attrs
    assert data["text/plain"] == lw.plate_sentence(plate)
    assert "hold liquid" in data["text/plain"]
    svg.check_bundle(data, meta)


def test_a_384_well_plate_full_of_liquid_stays_within_the_cap(lw, budget, real_plates, record_property):
    plate = real_plates["greiner384"]
    for w in plate.get_all_items():
        w.tracker.set_volume(w.max_volume / 2)
    n = budget.html_bytes(lw.render(plate, rev=1, session="s", exec_count=1)[0]["text/html"])
    record_property("bytes_plate384_full", n)
    assert n <= CAP


# --------------------------------------------------------------------------- 15. import discipline


def _module_level_imports(src: str) -> list[str]:
    tree = ast.parse(src)
    out = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            out += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            out.append(("." * node.level) + (node.module or ""))
    return out


def _all_pylabrobot_imports(src: str) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            found |= {a.name for a in node.names if a.name.split(".")[0] == "pylabrobot"}
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "pylabrobot":
            found.add(node.module)
    return found


def test_labware_imports_no_pylabrobot_at_module_level_and_only_contract_modules_anywhere(lw):
    src = _LABWARE_PATH.read_text(encoding="utf-8")
    top = _module_level_imports(src)
    assert not [m for m in top if m.split(".")[0] in ("pylabrobot", "js", "IPython", "pyodide")], top
    import plr_contract

    contract = {path for path, _symbol in plr_contract.CONTRACT}
    used = _all_pylabrobot_imports(src)
    assert used, "labware.py must resolve PLR classes (Plate, TipRack, ...) through the contract"
    assert used <= contract, f"imports outside the contract: {sorted(used - contract)}"
    assert not [m for m in used if m in ("pylabrobot.resources.tip_tracker", "pylabrobot.liquid_handling")]


def test_import_lint_control_flags_a_module_level_plr_import():
    assert _module_level_imports("import pylabrobot\nfrom .svg import x\n") == ["pylabrobot", ".svg"]
    assert _module_level_imports("def f():\n    import pylabrobot\n") == []
    assert _all_pylabrobot_imports("def f():\n    from pylabrobot.resources import Plate\n") == {"pylabrobot.resources"}


def test_labware_imports_in_plain_cpython_without_touching_pylabrobot_or_the_browser(tmp_path):
    """A fresh interpreter, no PLR on the path, warnings as errors: the module must still import."""
    code = (
        "import sys, types, importlib\n"
        f"m = types.ModuleType({_PKG!r}); m.__path__ = [{str(_DISPLAY_DIR)!r}]; sys.modules[{_PKG!r}] = m\n"
        f"lw = importlib.import_module({_PKG + '.labware'!r})\n"
        "bad = [k for k in sys.modules if k.split('.')[0] in ('pylabrobot', 'js', 'IPython', 'pyodide')]\n"
        "assert not bad, bad\n"
        "print('ok')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-W", "error", "-I", "-c", code], capture_output=True, text=True, timeout=60
    )
    assert proc.returncode == 0 and proc.stdout.strip() == "ok", proc.stderr[-1500:]


def test_rendering_real_labware_raises_no_warning(lw, source, tips, assay):
    """Deprecated PLR names (``spot.has_tip()``, ``get_liquids``, ...) must not be used."""
    from pylabrobot.resources import Trough

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for res in (source, tips, assay, assay.get_item("A1"), Trough(name="t", size_x=1, size_y=1, size_z=1, max_volume=5)):
            lw.render(res, rev=1, session="s", exec_count=1)


def test_labware_module_docstring_is_present_and_names_its_spec(lw):
    assert lw.__doc__ and "D2" in lw.__doc__


# --------------------------------------------------------------------------- 15. committed tips and faulted figures (#5659)
#
# Spec: ``261001_nd-next-5659-96head-errors.md`` N5659-8 (the optional ``tip_of`` hook), AC-96-7 (b)(c)
# (faulted-figure size and D5) and AC-96-11 (the default hook reads today's ``spot.tip``).

# sha256 of today's outputs, taken at base 98a233ed BEFORE the hook existed: the default reading must
# stay byte-identical for every non-error output (N5659-8). A change here is a change to a shipped
# output, never a test fix.
_PRE_HOOK_GOLDEN = {
    "tips.html": "61240cea2459b38de49586383c0e94a487d84139ef6405577b3a6d1e5206ff3b",
    "tips.html.l1": "749716a04aafd0664ab5aca00774bd8aee727a0764db190d00ffae6c4035fe39",
    "tips.html.l2": "3cf46734c9db023e16d8f82e394fc325608c1a5dc217c191f2c714e56f9b6abc",
    "tips.sentence": "8783800c7acbb5db79bf07a2d45fd838dbde8c65490bbc249cc8d174ae21dcf1",
    "tips.figure_marked": "cf9054828d4922bc15e15f03058ebb6a8b1f2514c2860eae8a6bf0dc3eee1e13",
    "tips.bundle": "90873572d2da7f4273be8719bee6f6fb9d2640f7cb12215acbc4ac47b2814f0e",
    "full.html": "77b2cdde29e91274e44ca90b7cc0a81987161a86adf52943a695805f4a6b0977",
    "full.html.l1": "1302bf82ec780ee3b20db5ac1d2feae1ef9deda1066970414a9eea96e1f8682a",
    "full.html.l2": "7f5f19f1e70799f8690ab19e0e902a9819e6576046a4d0c855ae4b7f2fa38897",
    "full.sentence": "75e5c81982e4259e2b6bb95a5dbdbb96707884fda3f4a9d32fb43419265a23d3",
    "full.figure_marked": "5d529e59a278c32ef96d5ce0cb292dee559410bb68f662950b0367c07cc8a483",
    "full.bundle": "0697d71e1182e5d35e4448f590990be47b4baea9611c94b546fb42fbd13aa78e",
    "empty.html": "cc1c0b93d1cbfefe61ad0093e679fa96f02104d47cd07173df2f25c63a9c3f00",
    "empty.html.l1": "9007a32a770757b33403b960ee90ba987fed774dc472536988f94934d527a164",
    "empty.html.l2": "4741d81862593ba6345b20eabac8a90d8237a7b105fc677c04d35ebd2841f450",
    "empty.sentence": "63a961acfd9432b963ab049f535082d1361f3605fe48b119d45ddf0fbae3482f",
    "empty.figure_marked": "75c9745c9e321e6dd64bd3b38452d6abe2e85e447cc5afad4cad8bfac8e2207c",
    "empty.bundle": "80efb7e2f0b4ad7de4f09a65826e0ee93882f9d51ea1b398c8bc3f086729c109",
}


def _sha(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()


def _golden_outputs(lw, name, rack, **kw) -> dict:
    out = {
        f"{name}.html": _sha(lw.render_html(rack, **kw)),
        f"{name}.html.l1": _sha(lw.render_html(rack, level=1, **kw)),
        f"{name}.html.l2": _sha(lw.render_html(rack, level=2, **kw)),
        f"{name}.sentence": _sha(lw.sentence(rack, **kw)),
        f"{name}.figure_marked": _sha(lw.render_figure(rack, fault={"A1", "H12"}, changed={"B2"}, **kw)),
    }
    data, _meta = lw.render(rack, rev=1, session="s", exec_count=3, **kw)
    out[f"{name}.bundle"] = _sha(data["text/html"] + "|" + data["text/plain"])
    return out


def _golden_racks(fx, tips):
    full = fx.hamilton_96_tiprack_300uL_filter(name="full")
    empty = _rack_with_used(fx, "empty", _all_ids(8, 12))
    return {"tips": tips, "full": full, "empty": empty}


def test_tip_of_default_reading_is_byte_equal_to_the_outputs_before_the_hook(lw, fx, tips):
    """No hook: every rack output (levels 0, 1, 2, the sentence, a marked figure, the bundle) is
    byte-identical to what the base commit produced. The goldens were taken before the change."""
    got = {}
    for name, rack in _golden_racks(fx, tips).items():
        got.update(_golden_outputs(lw, name, rack))
    assert got == _PRE_HOOK_GOLDEN


def test_tip_of_the_explicit_default_hook_equals_no_hook(lw, fx, tips):
    got = {}
    for name, rack in _golden_racks(fx, tips).items():
        got.update(_golden_outputs(lw, name, rack, tip_of=lambda spot: spot.tip))
    assert got == _PRE_HOOK_GOLDEN


def test_tip_of_golden_control_a_changed_output_is_seen(lw, fx, tips):
    """Control for the goldens: a rack with one tip fewer must NOT hash the same."""
    rack = _rack_with_used(fx, "full", ["A1"])
    assert _golden_outputs(lw, "full", rack)["full.html"] != _PRE_HOOK_GOLDEN["full.html"]


def _committed(spot):
    from pylabrobot.legacy.tip_tracker import tip_spot_tracker
    from pylabrobot.resources.errors import NoTipError

    try:
        return tip_spot_tracker(spot).get_tip()
    except NoTipError:
        return None


def _rack_with_pending_removals(fx, ids):
    """A full rack whose spots in *ids* have a PENDING removal (committed tip kept)."""
    from pylabrobot.legacy.tip_tracker import tip_spot_tracker

    rack = fx.hamilton_96_tiprack_300uL_filter(name="pend_rm")
    for ident in ids:
        tip_spot_tracker(rack.get_item(ident)).remove_tip()  # commit=False
        assert rack.get_item(ident).tip is None and _committed(rack.get_item(ident)) is not None
    return rack


def _rack_with_a_pending_add(fx, ident):
    """A rack whose spot *ident* has no committed tip but a pending one."""
    from pylabrobot.legacy.tip_tracker import tip_spot_tracker

    rack = fx.hamilton_96_tiprack_300uL_filter(name="pend_add")
    spot = rack.get_item(ident)
    tip_spot_tracker(spot).remove_tip(commit=True)
    tip_spot_tracker(spot).add_tip(spot.make_tip(), commit=False)
    assert spot.tip is not None and _committed(spot) is None
    return rack


def _tip_surfaces(doc: str):
    """What a reader sees of the tips: drawn rings, the grid's hover values, the aria-label."""
    root = _parse(doc)
    paths = _paths(root)
    rings = len(_subpaths(paths["sv-tip-ring"][0])) if "sv-tip-ring" in paths else 0
    return rings, sum(_grid_of(root)["vals"]), _figure_group(root).attrs["aria-label"]


_PENDING_RM = ("A1", "B1", "C1", "D1", "E1")


def _check_committed_surfaces(doc, present, sentence):
    rings, vals, aria = _tip_surfaces(doc)
    assert (rings, vals, aria) == (present, present, sentence)


def test_tip_of_hook_feeds_the_drawing_the_hover_values_and_the_sentence(lw, fx):
    rack = _rack_with_pending_removals(fx, _PENDING_RM)
    full = "96 of 96 tips left."
    _check_committed_surfaces(lw.render_figure(rack, tip_of=_committed), 96, full)
    # the pending reading (today's) sees 91 on all three surfaces
    _check_committed_surfaces(lw.render_figure(rack), 91, "91 of 96 tips left. Column 1 used.")
    assert lw.tiprack_sentence(rack, tip_of=_committed) == full
    assert lw.sentence(rack, tip_of=_committed) == full
    assert lw.tiprack_sentence(rack) == "91 of 96 tips left. Column 1 used."


def test_tip_of_hook_reaches_every_ladder_level_and_the_bundle(lw, fx):
    rack = _rack_with_pending_removals(fx, _PENDING_RM)
    full = "96 of 96 tips left."
    block = lw.render_figure(rack, level=1, tip_of=_committed)
    assert _figure_group(_parse(block)).attrs["aria-label"] == full
    omitted = lw.render_html(rack, level=2, tip_of=_committed)
    assert full in omitted and "91 of 96" not in omitted
    html = lw.render_html(rack, tip_of=_committed)
    assert full in html and "91 of 96" not in html
    data, _meta = lw.render(rack, rev=1, session="s", exec_count=1, tip_of=_committed)
    assert data["text/plain"] == full and full in data["text/html"]


def test_tip_of_a_pending_add_is_not_drawn_by_the_committed_reading(lw, fx):
    rack = _rack_with_a_pending_add(fx, "H12")
    _check_committed_surfaces(lw.render_figure(rack, tip_of=_committed), 95, "95 of 96 tips left. Column 12 used.")
    _check_committed_surfaces(lw.render_figure(rack), 96, "96 of 96 tips left.")


def test_tip_of_a_hook_returning_none_draws_the_spot_as_taken(lw, fx):
    rack = fx.hamilton_96_tiprack_300uL_filter(name="all_there")
    doc = lw.render_figure(rack, tip_of=lambda spot: None)
    assert _tip_surfaces(doc) == (0, 0, "0 of 96 tips left. Columns 1–12 used.")
    assert len(_subpaths(_paths(_parse(doc))["sv-tip-gone"][0])) == 96


def test_tip_of_control_the_default_hook_fails_the_committed_check(lw, fx):
    rack = _rack_with_pending_removals(fx, _PENDING_RM)
    with pytest.raises(AssertionError):
        _check_committed_surfaces(lw.render_figure(rack), 96, "96 of 96 tips left.")


def test_tip_of_control_a_sentence_that_ignores_the_hook_disagrees_with_the_drawing(lw, fx, monkeypatch):
    rack = _rack_with_pending_removals(fx, _PENDING_RM)
    real = lw.tiprack_sentence
    monkeypatch.setattr(lw, "tiprack_sentence", lambda r, tip_of=None: real(r))
    with pytest.raises(AssertionError):
        _check_committed_surfaces(lw.render_figure(rack, tip_of=_committed), 96, "96 of 96 tips left.")


def test_tip_of_control_hover_values_that_ignore_the_hook_disagree_with_the_drawing(lw, fx, monkeypatch):
    rack = _rack_with_pending_removals(fx, _PENDING_RM)
    real = lw._grid_descriptor

    def pending_vals(kind, res_name, items, values, flags, offset, dx, dy):
        values = [1 if i.child.tip is not None else 0 for i in items] if kind == "tip" else values
        return real(kind, res_name, items, values, flags, offset, dx, dy)

    monkeypatch.setattr(lw, "_grid_descriptor", pending_vals)
    with pytest.raises(AssertionError):
        _check_committed_surfaces(lw.render_figure(rack, tip_of=_committed), 96, "96 of 96 tips left.")


# ---- AC-96-7 (b)(c): faulted figures


def _all_ids_of(res):
    return {i.get_identifier() for i in res.get_all_items()}


# D4:198 target revision for an ALL-FAULTED 96-position figure (plate or rack): 28 KiB. History: spec r2 proposed 20 KiB from a
# measurement on an EMPTY plate (19,746 B plate, 19,437 B rack); the user approved it on 2026-10-01; verifying the build then found a
# plate holding liquid is 26,370 B once all 96 wells are faulted (the fill adds ~6.6 KB), so the user approved the measured 28 KiB
# (option (a), 2026-10-01): 26,370 B + ~8.7 % margin. The normal (unfaulted) D4 targets, 16 KiB plate and 12 KiB rack, are unchanged.
FAULTED_TARGET = 28 * 1024


def test_faulted_96_plate_and_rack_figures_meet_the_approved_28_kib_target(lw, budget, fx, record_property):
    plate = fx.cor_96_wellplate_360uL_Fb(name="empty_assay")  # the fixture's assay plate as assembled
    rack = fx.hamilton_96_tiprack_300uL_filter(name="full_rack")
    sizes = {
        "plate": budget.html_bytes(lw.render_figure(plate, fault=_all_ids_of(plate))),
        "rack": budget.html_bytes(lw.render_figure(rack, fault=_all_ids_of(rack))),
    }
    record_property("bytes_plate96_all_faulted", sizes["plate"])
    record_property("bytes_tiprack_all_faulted", sizes["rack"])
    for which, size in sizes.items():
        assert size <= FAULTED_TARGET, f"the all-faulted {which} figure is {size} bytes"


def test_faulted_96_plate_holding_liquid_meets_the_faulted_target(lw, budget, fx, record_property):
    """The first target (20 KiB) was measured on an EMPTY plate. A plate whose wells hold liquid draws a volume fill per well on
    top of the fault marks, so its all-faulted figure is bigger: a dispense into a full plate is exactly the case (TooMuchLiquid)
    where all 96 wells can be faulted AND full. Measured on the fixture's 200 uL source plate."""
    plate = fx.cor_96_wellplate_360uL_Fb(name="full_source")
    for well in plate.get_all_items():
        well.tracker.set_volume(200.0)
    size = budget.html_bytes(lw.render_figure(plate, fault=_all_ids_of(plate)))
    record_property("bytes_plate96_200uL_all_faulted", size)
    assert size <= FAULTED_TARGET, f"the all-faulted plate holding 200 uL per well is {size} bytes"


def test_faulted_figure_control_one_path_per_fault_exceeds_the_target(lw, budget, fx, monkeypatch):
    plate = fx.cor_96_wellplate_360uL_Fb(name="empty_assay")
    real_svg = importlib.import_module(f"{_PKG}.svg")

    def path_per_fault(items, changed, fault, *, circle_of, s_n, ox, oy):
        parts = []
        for i in items:
            if i.ident in fault:
                parts.append(real_svg.path_el(
                    lw._shape_path(i, circle=circle_of(i), grow=lw._FAULT_GROW_MM, ox=ox, oy=oy),
                    cls="sv-fault", fill="none", stroke=lw.COLORS["brick"], stroke_width=1.0,
                ))
                parts.append(real_svg.path_el(
                    real_svg.cross_path(i.cx + ox, i.cy + oy, lw._CROSS_RATIO * i.d / 2),
                    cls="sv-fault-x", fill="none", stroke=lw.COLORS["brick"], stroke_width=1.0,
                ))
        return parts

    assert budget.html_bytes(lw.render_figure(plate, fault=_all_ids_of(plate))) <= FAULTED_TARGET
    monkeypatch.setattr(lw, "_mark_paths", path_per_fault)
    assert budget.html_bytes(lw.render_figure(plate, fault=_all_ids_of(plate))) > FAULTED_TARGET


def _d5_numbers(doc):
    root = _parse(doc)
    s = _svg_root(root)
    # the test HTML parser lower-cases attribute names: viewBox is read as "viewbox"
    return {k: s.attrs.get(k) for k in ("width", "viewbox", "style", "data-praxis-minw")}


def _check_faulted_d5(lw, res):
    plain, faulted = lw.render_figure(res), lw.render_figure(res, fault=_all_ids_of(res))
    assert _d5_numbers(plain) == _d5_numbers(faulted)
    assert all(v is not None for v in _d5_numbers(faulted).values())
    assert faulted.count("<circle") == 0


def test_faulted_figures_keep_the_d5_numbers_and_draw_no_circle_element(lw, fx):
    _check_faulted_d5(lw, fx.cor_96_wellplate_360uL_Fb(name="p"))
    _check_faulted_d5(lw, fx.hamilton_96_tiprack_300uL_filter(name="r"))


def test_faulted_figure_control_a_circle_per_fault_is_refused(lw, fx, monkeypatch):
    real_svg = importlib.import_module(f"{_PKG}.svg")
    real = lw._mark_paths

    def circles(items, changed, fault, *, circle_of, s_n, ox, oy):
        return real(items, changed, fault, circle_of=circle_of, s_n=s_n, ox=ox, oy=oy) + [
            real_svg.el("circle", "", cx=i.cx + ox, cy=i.cy + oy, r=i.d / 2) for i in items if i.ident in fault
        ]

    plate = fx.cor_96_wellplate_360uL_Fb(name="p")
    _check_faulted_d5(lw, plate)
    monkeypatch.setattr(lw, "_mark_paths", circles)
    with pytest.raises(AssertionError):
        _check_faulted_d5(lw, plate)


def test_faulted_figure_control_a_d5_number_that_moves_with_the_faults_is_seen(lw, fx, monkeypatch):
    plate = fx.cor_96_wellplate_360uL_Fb(name="p")
    real = lw._svg_figure

    def wider_when_faulted(inner, width_mm, height_mm, s_n, s_min_value):
        return real(inner, width_mm + (1.0 if "sv-fault" in inner else 0.0), height_mm, s_n, s_min_value)

    monkeypatch.setattr(lw, "_svg_figure", wider_when_faulted)
    with pytest.raises(AssertionError):
        _check_faulted_d5(lw, plate)
