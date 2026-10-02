"""Browserless tests for ``praxis/display/deck.py`` (task B3, backlog #5637): the deck plan with its
rail ruler, carriers and labware footprints, level-of-detail, the deck sentence and the D2 mimebundle.
Closes AC-11, and the deck halves of AC-12 (the detail floor on REAL PyLabRobot definitions, replacing
B1's stand-in numbers) and AC-13 (the D4 byte cap and its ladder on a deck).

Spec: ``260929_notebook-display-epic.md`` D2 (bundle, stamp, escaping), D3 (inline light palette), D4
(64 KiB cap, 48 KiB fixture-deck target, ladder), D5 (deck ``s_n = 880 / W`` clamped to >= 0.6,
``s_min = max(0.88 s_n, 0.6)``, labware drawn in full only if ``d_min * s_min >= 4``), sections 3.2
(deck sentence, rail ruler) and 3.4 (attributes), AC-11, AC-12, AC-13 and the sprint notes (B1 notes:
"B3 must redo AC-12 with real PLR definitions").

**PyLabRobot.** Every PLR object is the REAL 1.0.0b1 pin, built with the constructors of the ported
design fixture (``web-repl/design/notebook-display/make_fixture.py``, ``assemble()``); the extra decks
(narrower than 880 mm, oversize) are real ``HamiltonSTARDeck`` / ``STARDeck`` instances. The venv's
editable PLR can be the old 0.2.2, which would make every test meaningless, so the first test asserts
the version. Run with ``PYTHONPATH=<PLR 1.0.0b1 source>`` prepended when the venv is not on the pin.

Definitions used by name: ``STARLetDeck`` (1005 mm, 30 tracks), ``STARDeck`` (1545 mm, 54 tracks),
``HamiltonSTARDeck(num_tracks=14, size_x=440)`` and ``(num_tracks=20, size_x=600)``,
``hamilton_tip_carrier_L5``, ``hamilton_plate_carrier_L5_ac``, ``hamilton_96_tiprack_300uL_filter``
(an ``EmbeddedTipRack``, 7.2 mm tip spots), ``cor_96_wellplate_360uL_Fb`` (6.86 mm wells),
``Greiner_384_wellplate_28ul_Fb`` (3.3 mm) and ``Hibase_Greiner_1536_Well`` (2.3 mm).

**Import discipline** (ADR 260817 Sec 2.4). ``praxis/display`` is loaded by path under the synthetic
package ``_praxis_display_under_test``; ``web-repl/overlay/assets/python`` is never put on
``sys.path`` (its ``praxis/`` would shadow the repo's real package; ``test_rid_invariant.py``).

**Controls.** Every check that could pass vacuously has a control that must FAIL: the floor checker
against a shrunken font, a shrunken ``min-width`` and a shrunken well; the escape checker against naive
markup; the balance checker against broken markup; the AST lints against snippets that break each
rule; the dispatch check against a class that only borrows the name ``TipRack``; the detail-level
oracle is exercised on decks where labware goes BOTH ways (block at 1005 mm, full at 440 mm).
"""

from __future__ import annotations

import ast
import asyncio
import html as html_mod
import importlib
import importlib.util
import json
import math
import re
import subprocess
import sys
import types
import warnings
from html.parser import HTMLParser
from pathlib import Path

import pytest

import pylabrobot

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL = _TESTS_DIR.parent
_DISPLAY_DIR = _WEB_REPL / "overlay" / "assets" / "python" / "praxis" / "display"
_DECK_PATH = _DISPLAY_DIR / "deck.py"
_FIXTURE_PATH = _WEB_REPL / "design" / "notebook-display" / "make_fixture.py"
_PKG = "_praxis_display_under_test"

CAP = 65_536
DECK_TARGET = 49_152  # AC-11: the fixture deck's text/html; D4's 48 KiB

# D3 palette.
SHEET, INK, INK_SOFT, RAIL = "#FFFFFF", "#1D2935", "#56636F", "#C9D2DA"
MOONSTONE = "#73A9C2"

SPEC_SENTENCE = "Tip carrier on rail 3, plate carrier on rail 9. 3 pieces of labware: tips_300, source, assay."

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
def dk():
    """praxis/display/deck.py. A missing module is the RED reason."""
    if not _DECK_PATH.is_file():
        pytest.fail(f"praxis/display/deck.py does not exist yet: {_DECK_PATH}")
    _package()
    return importlib.import_module(f"{_PKG}.deck")


@pytest.fixture(scope="module")
def svg(dk):
    return importlib.import_module(f"{_PKG}.svg")


@pytest.fixture(scope="module")
def budget(dk):
    return importlib.import_module(f"{_PKG}.budget")


@pytest.fixture(scope="module")
def floor(dk):
    return importlib.import_module(f"{_PKG}.floor")


@pytest.fixture(scope="module")
def lw(dk):
    return importlib.import_module(f"{_PKG}.labware")


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
def deck_html(dk, deck):
    return dk.render_html(deck)


# --------------------------------------------------------------------------- deck builders (real PLR)


def _star(num_tracks: int, size_x: float, name: str = "deck"):
    from pylabrobot.resources.hamilton import HamiltonSTARDeck

    return HamiltonSTARDeck(
        name=name, num_tracks=num_tracks, size_x=size_x, size_y=653.5, size_z=334.7,
        with_waste_block=False, with_trash=False, with_trash96=False, with_teaching_needle_rack=False,
        core_grippers=None,
    )


def _mixed(fx, deck):
    """Tips on track 3; on track 9 a Cor 96 (some liquid), a 384 and a 1536 plate. The same layout
    on every deck, so only the deck's width changes what is drawn in full."""
    from pylabrobot.resources.greiner import Greiner_384_wellplate_28ul_Fb
    from pylabrobot.resources.tecan.plates import Hibase_Greiner_1536_Well

    tip_car = fx.hamilton_tip_carrier_L5(name="tip_carrier")
    tip_car[0] = fx.hamilton_96_tiprack_300uL_filter(name="tips_300")
    deck.assign_child_resource(tip_car, track=3)
    plate_car = fx.hamilton_plate_carrier_L5_ac(name="plate_carrier")
    cor = fx.cor_96_wellplate_360uL_Fb(name="cor96")
    for w in cor.get_all_items()[:24]:
        w.tracker.set_volume(120.0)
    plate_car[0] = cor
    plate_car[1] = Greiner_384_wellplate_28ul_Fb(name="p384")
    plate_car[2] = Hibase_Greiner_1536_Well(name="p1536")
    deck.assign_child_resource(plate_car, track=9)
    return deck


@pytest.fixture(scope="module")
def decks(fx, deck):
    from pylabrobot.resources.hamilton import STARDeck

    return {
        "fixture1005": deck,
        "mid600": _mixed(fx, _star(20, 600.0, "mid")),
        "narrow440": _mixed(fx, _star(14, 440.0, "narrow")),
        "oversize1545": _mixed(fx, STARDeck(name="big")),
    }


def _plain_deck_of_plates(factory, n, *, size_x=440.0, size_y=653.5, cols=3, pitch=(130.0, 90.0), prefix="p"):
    """A plain ``Deck`` (no rails) with *n* plates assigned directly at real locations."""
    from pylabrobot.resources import Coordinate, Deck

    d = Deck(size_x=size_x, size_y=size_y, size_z=100.0, name="plain")
    for i in range(n):
        d.assign_child_resource(
            factory(name=f"{prefix}{i}"),
            location=Coordinate((i % cols) * pitch[0], 5.0 + (i // cols) * pitch[1], 0.0),
        )
    return d


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


def _svg_root(root: _Node) -> _Node:
    svgs = root.find_all("svg")
    assert len(svgs) == 1, f"expected one <svg>, found {len(svgs)}"
    return svgs[0]


def _outer(root: _Node) -> _Node:
    """The deck's own resource group (the one that carries role=img and the sentence)."""
    groups = [n for n in root.walk() if n.tag == "g" and n.attrs.get("role") == "img"]
    assert len(groups) == 1, f"expected one role=img group, found {len(groups)}"
    return groups[0]


def _items(root: _Node) -> dict[str, _Node]:
    """Resource groups inside the deck, by resource name."""
    out: dict[str, _Node] = {}
    for n in root.walk():
        if n.tag == "g" and "data-praxis-res" in n.attrs and n.attrs.get("role") != "img":
            name = n.attrs["data-praxis-res"]
            assert name not in out, f"two groups for {name!r}"
            out[name] = n
    return out


def _paths_in(node: _Node) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in node.find_all("path"):
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


def _vline(sp: str):
    """(x, y0, y1) of a vertical line subpath ``M x y0 V y1``."""
    m = re.fullmatch(rf"M({_NUM})[ ,]?({_NUM})V({_NUM})", sp)
    assert m, sp
    return tuple(float(v) for v in m.groups())


def _texts(root: _Node) -> list[tuple[str, float]]:
    return [(t.text(), float(t.attrs["font-size"])) for t in root.find_all("text")]


def _view(root: _Node) -> tuple[float, float]:
    """(width mm, height mm) of the viewBox."""
    vb = [float(v) for v in _svg_root(root).attrs["viewbox"].split()]
    assert vb[0] == 0 and vb[1] == 0, vb
    return vb[2], vb[3]


def _declared_s_min(root: _Node) -> float:
    svg_el = _svg_root(root)
    w_mm, _h = _view(root)
    m = re.search(r"min-width:([\d.]+)px", svg_el.attrs["style"])
    return float(m.group(1)) / w_mm


# --------------------------------------------------------------------------- oracles (from the spec)


def _s_n(width_mm: float) -> float:
    return max(880.0 / width_mm, 0.6)


def _s_min(width_mm: float) -> float:
    return max(0.88 * _s_n(width_mm), 0.6)


def _d_min(res) -> float:
    return min(min(c.get_size_x(), c.get_size_y()) for c in res.get_all_items())


def _labware_of(deck) -> list:
    """Every Plate / TipRack on the deck: on carrier sites, then directly on the deck."""
    from pylabrobot.resources import Carrier, Plate, TipRack

    found = []
    for c in sorted((c for c in deck.children if isinstance(c, Carrier)), key=lambda c: c.get_location_wrt(deck).x):
        for holder in c.children:
            found += list(holder.children)
    found += sorted(
        (c for c in deck.children if isinstance(c, (Plate, TipRack))),
        key=lambda c: (c.get_location_wrt(deck).x, c.get_location_wrt(deck).y),
    )
    return found


def _is_full(res, width_mm) -> bool:
    return _d_min(res) * _s_min(width_mm) >= 4 - 1e-9


# =========================================================================== 1. the pin and the fixture


def test_fixture_deck_is_the_real_starlet_at_the_pin(deck):
    """The numbers the spec's D5 worked check quotes, read from PLR rather than trusted."""
    from pylabrobot.resources.hamilton import HamiltonSTARDeck

    assert isinstance(deck, HamiltonSTARDeck)
    assert deck.get_size_x() == 1005.0
    assert deck.num_tracks == 30
    tips = deck.get_resource("tips_300")
    assert tips.get_item("A1").get_size_x() == 7.2  # 9.0 at 0.2.2
    src = deck.get_resource("source")
    assert min(src.get_item("A1").get_size_x(), src.get_item("A1").get_size_y()) == 6.86
    from pylabrobot.resources.greiner import Greiner_384_wellplate_28ul_Fb
    from pylabrobot.resources.tecan.plates import Hibase_Greiner_1536_Well

    assert Greiner_384_wellplate_28ul_Fb(name="a").get_item("A1").get_size_x() == 3.3  # stand-in said 3.6
    assert Hibase_Greiner_1536_Well(name="b").get_item("A1").get_size_x() == 2.3  # stand-in said 1.7


def test_deck_scale_matches_the_d5_worked_check(dk, floor, deck):
    s_n, s_min = dk.deck_scale(deck)
    assert s_n == pytest.approx(880 / 1005, rel=1e-12)
    assert s_min == pytest.approx(0.88 * 880 / 1005, rel=1e-12)
    assert s_min == pytest.approx(0.7706, abs=1e-4)  # "about 0.771"
    assert (s_n, s_min) == (floor.nominal_scale("deck", 1005.0), floor.s_min_deck(floor.nominal_scale("deck", 1005.0)))


# =========================================================================== 2. AC-11: sentence


def test_deck_sentence_is_exactly_the_spec_string(dk, deck):
    assert dk.sentence(deck) == SPEC_SENTENCE


def test_deck_text_plain_and_aria_label_are_the_sentence(dk, deck, deck_html):
    data, meta = dk.render(deck, rev=1, session="s1", exec_count=3)
    assert data["text/plain"] == SPEC_SENTENCE
    root = _parse(deck_html)
    assert _outer(root).attrs["aria-label"] == SPEC_SENTENCE
    assert root.find_all(cls="praxis-summary")[0].text() == SPEC_SENTENCE


def _phrase(carrier) -> str:
    words = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", type(carrier).__name__).lower()
    return words


def test_sentence_rules_independent_oracle(dk, fx):
    """Carriers in rail order, phrased from their PLR class, then the labware in that order."""
    deck = _star(20, 600.0)
    plate_car = fx.hamilton_plate_carrier_L5_ac(name="pc")
    plate_car[1] = fx.cor_96_wellplate_360uL_Fb(name="second")
    plate_car[0] = fx.cor_96_wellplate_360uL_Fb(name="first")
    deck.assign_child_resource(plate_car, track=3)
    tip_car = fx.hamilton_tip_carrier_L5(name="tc")
    tip_car[0] = fx.hamilton_96_tiprack_300uL_filter(name="rack")
    deck.assign_child_resource(tip_car, track=9)
    expected = (
        f"{_phrase(plate_car).capitalize()} on rail 3, {_phrase(tip_car)} on rail 9. "
        "3 pieces of labware: first, second, rack."
    )
    assert dk.sentence(deck) == expected
    assert expected.startswith("Plate carrier on rail 3, tip carrier on rail 9.")  # the ordering is by rail, not by insertion


def test_sentence_two_carriers_of_one_class_and_singular_labware(dk, fx):
    deck = _star(20, 600.0)
    for track, name in ((3, "a"), (9, "b")):
        c = fx.hamilton_plate_carrier_L5_ac(name=name)
        deck.assign_child_resource(c, track=track)
    c = deck.get_resource("a")
    c[0] = fx.cor_96_wellplate_360uL_Fb(name="only")
    assert dk.sentence(deck) == "Plate carrier on rail 3, plate carrier on rail 9. 1 piece of labware: only."


def test_sentence_of_an_empty_deck(dk):
    from pylabrobot.resources.hamilton import STARLetDeck

    assert dk.sentence(STARLetDeck(name="bare")) == "No carriers. No labware."


def test_sentence_on_a_deck_without_rails_gives_no_rail_number(dk, fx):
    deck = _plain_deck_of_plates(fx.cor_96_wellplate_360uL_Fb, 2, prefix="q")
    s = dk.sentence(deck)
    assert s == "No carriers. 2 pieces of labware: q0, q1."
    assert "rail" not in s


def test_sentence_number_formatting_uses_thousands_separators(dk, fx):
    deck = _plain_deck_of_plates(fx.cor_96_wellplate_360uL_Fb, 1200, size_x=20000.0, size_y=200000.0, cols=100, prefix="w")
    assert dk.sentence(deck).startswith("No carriers. 1,200 pieces of labware: w0, ")


def test_sentence_follows_the_tree_not_a_hardcoded_string(dk, fx, deck):
    """Control: the spec sentence is not a constant. Changing the layout changes it."""
    other = _star(30, 1005.0)
    tip_car = fx.hamilton_tip_carrier_L5(name="tc")
    tip_car[0] = fx.hamilton_96_tiprack_300uL_filter(name="racks")
    other.assign_child_resource(tip_car, track=5)
    s = dk.sentence(other)
    assert s == "Tip carrier on rail 5. 1 piece of labware: racks."
    assert s != SPEC_SENTENCE and dk.sentence(deck) == SPEC_SENTENCE


# =========================================================================== 3. AC-11: rail ruler


def _ruler(root: _Node):
    """(label, x) of the ruler's numbers (class sv-grid), and the tick subpaths (x, y0, y1)."""
    labels = [(t.text(), float(t.attrs["x"])) for t in root.find_all("text", cls="sv-grid")]
    ticks = []
    for p in root.find_all("path", cls="sv-ruler"):
        for sp in _subpaths(p.attrs["d"]):
            if "V" in sp:
                ticks.append(_vline(sp))
    return labels, ticks


def test_ruler_labels_are_exactly_rails_1_5_10_15_20_25_30(deck_html):
    labels, _ = _ruler(_parse(deck_html))
    assert [t for t, _x in labels] == ["1", "5", "10", "15", "20", "25", "30"]


def test_ruler_uses_num_tracks_and_never_reads_num_rails(dk, deck, monkeypatch):
    """The deprecated ``num_rails`` reads 32 here; reading it is a DeprecationWarning and a failure."""
    monkeypatch.setattr(type(deck), "num_rails", property(lambda self: pytest.fail("num_rails was read")))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        doc = dk.render_html(deck)
    labels, ticks = _ruler(_parse(doc))
    assert "30" in [t for t, _ in labels] and "32" not in [t for t, _ in labels]
    assert len(ticks) == 30


def test_ruler_ticks_and_numbers_sit_on_the_rails_x_positions(deck, deck_html):
    labels, ticks = _ruler(_parse(deck_html))
    want = {t: deck.track_to_location(t).x for t in range(1, 31)}
    assert sorted(round(x, 2) for x, _a, _b in ticks) == sorted(round(v, 2) for v in want.values())
    for text, x in labels:
        assert x == pytest.approx(want[int(text)], abs=0.011)
    # every fifth rail (and the first) has the longer tick
    lengths = {round(x, 2): abs(b - a) for x, a, b in ticks}
    major = {round(want[t], 2) for t in (1, 5, 10, 15, 20, 25, 30)}
    long_len = max(lengths.values())
    assert {x for x, ln in lengths.items() if ln == pytest.approx(long_len)} == major
    assert all(ln < long_len for x, ln in lengths.items() if x not in major)


def test_ruler_is_along_the_front_edge_below_everything_else(deck, deck_html):
    """Front edge at the bottom (section 3.2): the ruler's ticks are lower than every carrier."""
    root = _parse(deck_html)
    _labels, ticks = _ruler(root)
    tick_top = min(min(a, b) for _x, a, b in ticks)
    for r in root.find_all("rect", cls="sv-carrier"):
        assert float(r.attrs["y"]) + float(r.attrs["height"]) <= tick_top + 1e-6
    _w, h = _view(root)
    assert max(max(a, b) for _x, a, b in ticks) < h


def test_ruler_labels_of_a_54_track_deck_and_a_12_track_deck(dk, decks):
    assert [t for t, _ in _ruler(_parse(dk.render_html(decks["oversize1545"])))[0]] == [str(n) for n in [1, *range(5, 55, 5)]]
    assert [t for t, _ in _ruler(_parse(dk.render_html(decks["narrow440"])))[0]] == ["1", "5", "10"]
    assert dk.rail_labels(30) == [1, 5, 10, 15, 20, 25, 30]
    assert dk.rail_labels(1) == [1]


def test_rail_lines_one_path_each_for_minor_and_major(deck_html):
    root = _parse(deck_html)
    rails = [p for p in root.find_all("path") if "sv-rail" in p.attrs.get("class", "").split()]
    assert len(rails) == 2
    minor = [p for p in rails if "sv-rail--major" not in p.attrs["class"].split()][0]
    major = [p for p in rails if "sv-rail--major" in p.attrs["class"].split()][0]
    assert len(_subpaths(minor.attrs["d"])) == 23 and len(_subpaths(major.attrs["d"])) == 7
    assert major.attrs["stroke"] == INK_SOFT and minor.attrs["stroke"] == RAIL


def test_a_deck_without_rails_has_no_ruler(dk, fx):
    deck = _plain_deck_of_plates(fx.cor_96_wellplate_360uL_Fb, 2)
    root = _parse(dk.render_html(deck))
    assert _ruler(root) == ([], []) and not root.find_all("path", cls="sv-rail")


# =========================================================================== 4. AC-11: footprints, to scale


def test_carrier_labels_are_present(deck_html):
    labels = [t.text() for t in _parse(deck_html).find_all("text", cls="sv-label")]
    assert "tip_carrier" in labels and "plate_carrier" in labels


def _footprints(root: _Node):
    """name -> (x, y, w, h) of its footprint rect (carrier, fixture, plate outline or block)."""
    out = {}
    for name, g in _items(root).items():
        rects = [r for r in g.find_all("rect")]
        assert len(rects) == 1, f"{name}: {len(rects)} rects"
        r = rects[0]
        out[name] = tuple(float(r.attrs[k]) for k in ("x", "y", "width", "height"))
    return out


def test_carriers_and_labware_are_drawn_to_scale_in_mm(deck, deck_html):
    """x, width and height are PLR's, in mm; y is measured down from a common top edge K, so
    ``y_svg + height + y_deck`` is the same K for every resource (front edge at the bottom)."""
    root = _parse(deck_html)
    fp = _footprints(root)
    ks = []
    for name in ("tip_carrier", "plate_carrier", "tips_300", "source", "assay"):
        res = deck.get_resource(name)
        loc = res.get_location_wrt(deck)
        x, y, w, h = fp[name]
        assert x == pytest.approx(loc.x, abs=0.011)
        assert w == pytest.approx(res.get_size_x(), abs=0.011)
        assert h == pytest.approx(res.get_size_y(), abs=0.011)
        ks.append(y + h + loc.y)
    assert max(ks) - min(ks) < 0.03, ks
    # the two carriers are where their tracks are: track 3 and track 9
    assert fp["tip_carrier"][0] == pytest.approx(deck.track_to_location(3).x)
    assert fp["plate_carrier"][0] == pytest.approx(deck.track_to_location(9).x)
    # a plate sits inside its carrier's footprint
    cx, _cy, cw, _ch = fp["plate_carrier"]
    for n in ("source", "assay"):
        assert cx <= fp[n][0] and fp[n][0] + fp[n][2] <= cx + cw + 1e-6


def test_the_figure_is_as_wide_as_the_deck_and_covers_the_content(deck, deck_html):
    root = _parse(deck_html)
    w, h = _view(root)
    assert w == pytest.approx(deck.get_size_x())  # D5: W_mm is the deck's width
    fp = _footprints(root)
    assert all(y >= -1e-6 for (_x, y, _w, _h) in fp.values()), "nothing above the top edge"
    assert max(y + hh for (_x, y, _w, hh) in fp.values()) < h, "the ruler band lies below the resources"


def test_every_labware_footprint_is_positioned_by_its_location_in_the_deck(decks, dk):
    for key in ("mid600", "narrow440", "oversize1545"):
        deck = decks[key]
        root = _parse(dk.render_html(deck))
        fp = _footprints(root)
        ks = []
        for res in _labware_of(deck) + [c for c in deck.children if type(c).__name__.endswith("Carrier")]:
            loc = res.get_location_wrt(deck)
            x, y, w, h = fp[res.name]
            assert x == pytest.approx(loc.x, abs=0.011) and w == pytest.approx(res.get_size_x(), abs=0.011)
            ks.append(y + h + loc.y)
        assert max(ks) - min(ks) < 0.03, (key, ks)


def test_fixtures_are_drawn_dashed_and_named_by_groups(deck, deck_html):
    root = _parse(deck_html)
    items = _items(root)
    for name in ("trash_core96", "waste_block", "trash"):
        assert name in items, name
        assert items[name].find_all("rect", cls="sv-fixture")
    # a zero-width resource (the fixture's `trash`) still gets a visible footprint
    assert float(items["trash"].find_all("rect")[0].attrs["width"]) > 0
    # labels never sit outside the figure
    w, _h = _view(root)
    for t in root.find_all("text"):
        assert 0 <= float(t.attrs["x"]) <= w, (t.text(), t.attrs["x"])


def test_labware_groups_carry_the_attribute_contract(dk, deck, deck_html):
    """Full-detail labware: data-praxis-res + data-praxis-grid (in FIGURE units, section 3.4)."""
    root = _parse(deck_html)
    items = _items(root)
    for name in ("tips_300", "source", "assay"):
        g = items[name]
        grid = json.loads(g.attrs["data-praxis-grid"])
        res = deck.get_resource(name)
        assert grid["res"] == name and grid["cols"] == 12 and grid["rows"] == 8
        # the grid's origin lands on the labware's first well, in the deck figure's own coordinates
        x, y, w, h = _footprints(root)[name]
        first = res.get_all_items()[0]
        assert grid["x0"] == pytest.approx(x + first.location.x + first.get_size_x() / 2, abs=0.02)
        assert grid["y0"] == pytest.approx(y + (res.get_size_y() - first.location.y - first.get_size_y() / 2), abs=0.02)
        assert grid["ids"].split()[:2] == [res.get_child_identifier(c) for c in res.get_all_items()[:2]]
    src = json.loads(items["source"].attrs["data-praxis-grid"])
    assert src["kind"] == "volume" and src["vals"] and set(src["vals"]) <= {50, 100, 150, 200}
    assert json.loads(items["tips_300"].attrs["data-praxis-grid"])["kind"] == "tip"


def test_the_outer_group_is_the_decks_resource_group(deck, deck_html):
    g = _outer(_parse(deck_html))
    assert g.attrs["data-praxis-res"] == deck.name and g.attrs["tabindex"] == "0"
    assert "data-praxis-grid" not in g.attrs


def test_labware_is_drawn_in_full_on_the_fixture_deck(deck, deck_html):
    """D5 worked check: Cor 96 wells are 6.86 mm -> 5.3 px, tip spots 7.2 mm -> 5.55 px, both >= 4."""
    items = _items(_parse(deck_html))
    for name in ("tips_300", "source", "assay"):
        assert not items[name].find_all("rect", cls="sv-block"), name
    assert len(_subpaths(_paths_in(items["source"])["sv-well"][0])) == 96
    assert len(_subpaths(_paths_in(items["assay"])["sv-liquid"][0])) == 24
    assert len(_subpaths(_paths_in(items["source"])["sv-liquid"][0])) == 96
    tp = _paths_in(items["tips_300"])
    assert len(_subpaths(tp["sv-tip-ring"][0])) == 72 and len(_subpaths(tp["sv-tip-gone"][0])) == 24
    assert len(tp["sv-tip"]) == 1
    assert 6.86 * 0.7706 == pytest.approx(5.29, abs=0.01) and 7.2 * 0.7706 == pytest.approx(5.55, abs=0.01)


def test_liquid_radius_on_the_deck_is_r_sqrt_v_over_max(deck, deck_html):
    assay = deck.get_resource("assay")
    items = _items(_parse(deck_html))
    circles = [_circle(s) for s in _subpaths(_paths_in(items["assay"])["sv-liquid"][0])]
    wells = [w for w in assay.get_all_items() if w.tracker.get_used_volume() > 1e-6]
    assert len(circles) == len(wells) == 24
    got = sorted(c[2] for c in circles)
    want = sorted(w.get_size_x() / 2 * math.sqrt(w.tracker.get_used_volume() / w.max_volume) for w in wells)
    for g, w in zip(got, want, strict=True):
        assert abs(g - w) < 1e-3
    linear = sorted(w.get_size_x() / 2 * (w.tracker.get_used_volume() / w.max_volume) for w in wells)
    assert any(abs(g - w) > 1e-3 for g, w in zip(got, linear, strict=True)), "control: a linear radius would differ"
    assert f'fill="{MOONSTONE}"' in deck_html


def test_volume_of_override_is_honoured_on_the_deck(dk, deck):
    """The committed volume (an error panel's, D8) can be drawn instead of the pending one."""
    doc = dk.render_html(deck, volume_of=lambda c: 0.0)
    items = _items(_parse(doc))
    assert "sv-liquid" not in _paths_in(items["source"]) and "sv-liquid" not in _paths_in(items["assay"])
    assert dk.render_html(deck) != doc


def test_colours_are_inline_and_uppercase(deck_html):
    for hexv in (SHEET, INK, INK_SOFT, RAIL, MOONSTONE):
        assert f'"{hexv}"' in deck_html, hexv
    assert not re.search(r"#[0-9a-f]{6}\b", deck_html), "lower-case hex would dodge the theme's attribute selectors"


# =========================================================================== 5. level of detail


@pytest.mark.parametrize("key", ["fixture1005", "mid600", "narrow440", "oversize1545"])
def test_detail_level_of_every_labware_follows_d_min_times_s_min(dk, decks, key):
    deck = decks[key]
    width = deck.get_size_x()
    root = _parse(dk.render_html(deck))
    items = _items(root)
    for res in _labware_of(deck):
        g = items[res.name]
        block = bool(g.find_all("rect", cls="sv-block"))
        assert block == (not _is_full(res, width)), (key, res.name, _d_min(res), _s_min(width))
        assert ("data-praxis-grid" in g.attrs) == (not block), (key, res.name)
        assert dk.detail_of(deck, res) == ("block" if block else "full")


def test_detail_level_goes_both_ways_across_the_decks(dk, decks):
    """Control: a rule that always says 'full' or always 'block' fails one of these."""
    def blocks(key):
        deck = decks[key]
        items = _items(_parse(dk.render_html(deck)))
        return {n for n, g in items.items() if g.find_all("rect", cls="sv-block")}

    assert blocks("fixture1005") == set()
    assert blocks("mid600") == {"p1536"}
    assert blocks("narrow440") == set()
    assert blocks("oversize1545") == {"p384", "p1536"}


def test_384_and_1536_plates_on_the_fixture_deck_scale_are_blocks_with_the_sentence(dk, fx):
    """D5 worked check: a 384-well plate's wells are 3.3 mm -> 2.5 px at s_min 0.771, so a block."""
    from pylabrobot.resources.greiner import Greiner_384_wellplate_28ul_Fb
    from pylabrobot.resources.tecan.plates import Hibase_Greiner_1536_Well

    deck = _star(30, 1005.0)
    car = fx.hamilton_plate_carrier_L5_ac(name="pc")
    car[0] = Greiner_384_wellplate_28ul_Fb(name="p384")
    car[1] = Hibase_Greiner_1536_Well(name="p1536")
    car[2] = fx.cor_96_wellplate_360uL_Fb(name="p96")
    deck.assign_child_resource(car, track=9)
    items = _items(_parse(dk.render_html(deck)))
    assert items["p384"].find_all("rect", cls="sv-block") and items["p1536"].find_all("rect", cls="sv-block")
    assert not items["p96"].find_all("rect", cls="sv-block")
    assert "3 pieces of labware: p384, p1536, p96." in dk.sentence(deck)
    assert 3.3 * 0.7706 < 4 <= 6.86 * 0.7706


def test_block_footprint_equals_the_labware_footprint_and_is_filled(dk):
    from pylabrobot.resources.hamilton import hamilton_plate_carrier_L5_ac
    from pylabrobot.resources.tecan.plates import Hibase_Greiner_1536_Well

    d = _star(30, 1005.0)
    car = hamilton_plate_carrier_L5_ac(name="pc")
    p = Hibase_Greiner_1536_Well(name="p1536")
    car[0] = p
    d.assign_child_resource(car, track=9)
    root = _parse(dk.render_html(d))
    r = _items(root)["p1536"].find_all("rect", cls="sv-block")[0]
    loc = p.get_location_wrt(d)
    assert float(r.attrs["x"]) == pytest.approx(loc.x, abs=0.011)
    assert float(r.attrs["width"]) == pytest.approx(p.get_size_x(), abs=0.011)
    assert r.attrs["fill"] == RAIL and r.attrs["stroke"] == INK


def test_square_cells_for_384_and_1536_when_they_are_drawn_in_full(dk, decks):
    items = _items(_parse(dk.render_html(decks["narrow440"])))
    for name, want in (("p384", 384), ("p1536", 1536)):
        subs = _subpaths(_paths_in(items[name])["sv-well"][0])
        assert len(subs) == want
        assert all(_circle(s) is None and _rect(s) is not None for s in subs), "384+ wells are square cells"


def test_direct_deck_labware_is_drawn_too(dk, fx):
    deck = _plain_deck_of_plates(fx.cor_96_wellplate_360uL_Fb, 2, size_x=1005.0, prefix="d")
    items = _items(_parse(dk.render_html(deck)))
    assert set(items) == {"d0", "d1"} and all("data-praxis-grid" in g.attrs for g in items.values())


def test_other_labware_on_a_carrier_is_a_block_and_named_in_the_sentence(dk, fx):
    from pylabrobot.resources import Trough

    deck = _star(30, 1005.0)
    car = fx.hamilton_plate_carrier_L5_ac(name="pc")
    car[0] = Trough(name="reagents", size_x=120.0, size_y=80.0, size_z=20.0, max_volume=1000.0)
    deck.assign_child_resource(car, track=9)
    items = _items(_parse(dk.render_html(deck)))
    assert items["reagents"].find_all("rect", cls="sv-block") and "data-praxis-grid" not in items["reagents"].attrs
    assert "1 piece of labware: reagents." in dk.sentence(deck)


# =========================================================================== 6. dispatch by class


def test_an_embedded_tip_rack_is_drawn_as_a_tip_rack_by_class(deck, deck_html):
    from pylabrobot.resources import EmbeddedTipRack, TipRack

    tips = deck.get_resource("tips_300")
    assert isinstance(tips, TipRack) and type(tips) is EmbeddedTipRack and type(tips) is not TipRack
    assert "sv-tip-ring" in _paths_in(_items(_parse(deck_html))["tips_300"])


def test_a_renamed_subclass_resolves_and_a_borrowed_name_does_not(dk, fx):
    from pylabrobot.resources import EmbeddedTipRack, Resource

    deck = _star(30, 1005.0)
    car = fx.hamilton_tip_carrier_L5(name="tc")
    rack = fx.hamilton_96_tiprack_300uL_filter(name="odd")
    rack.__class__ = type("CompletelyDifferentName", (EmbeddedTipRack,), {})
    car[0] = rack
    deck.assign_child_resource(car, track=3)
    pcar = fx.hamilton_plate_carrier_L5_ac(name="pc")
    deck.assign_child_resource(pcar, track=9)

    class TipRack(Resource):  # borrows the name only; it is not a PLR TipRack
        pass

    impostor = TipRack(name="impostor", size_x=110.0, size_y=70.0, size_z=10.0)
    assert type(impostor).__name__ == "TipRack"
    pcar[0] = impostor
    items = _items(_parse(dk.render_html(deck)))
    assert "sv-tip-ring" in _paths_in(items["odd"])
    assert items["impostor"].find_all("rect", cls="sv-block") and not _paths_in(items["impostor"]).get("sv-tip-ring")


def _compares_type_names(src: str) -> list[int]:
    hits = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Compare):
            for side in [node.left, *node.comparators]:
                if isinstance(side, ast.Attribute) and side.attr == "__name__":
                    hits.append(node.lineno)
    return hits


def test_no_dispatch_on_a_type_name_string_in_deck_source(dk):
    assert _compares_type_names(_DECK_PATH.read_text(encoding="utf-8")) == []


def test_type_name_lint_control_flags_a_dispatch_on_the_name():
    assert _compares_type_names("if type(x).__name__ == 'TipRack':\n    pass\n") == [1]
    assert _compares_type_names("name = type(x).__name__\n") == []


def test_a_non_deck_is_a_type_error(dk, fx):
    with pytest.raises(TypeError):
        dk.render(fx.cor_96_wellplate_360uL_Fb(name="p"), rev=1, session="s", exec_count=1)
    with pytest.raises(TypeError):
        dk.sentence(object())


# =========================================================================== 7. the D2 bundle and its stamp


def test_bundle_shape_and_stamp_for_a_deck(dk, svg, deck):
    data, meta = dk.render(deck, rev=7, session="sess-1", exec_count=12)
    assert set(data) == {"text/html", "text/plain"}
    assert meta == {"praxis": {"v": 1, "kind": "deck", "resource": "deck", "rev": 7, "session": "sess-1", "exec": 12}}
    assert set(meta["praxis"]) == {"v", "kind", "resource", "rev", "session", "exec"}
    svg.check_bundle(data, meta)
    assert data["text/plain"] == dk.sentence(deck)
    doc = data["text/html"]
    for bad in ("<circle", "<script", "<style", "<img", "onclick", "href="):
        assert bad not in doc
    assert "image/svg+xml" not in data


def test_injected_fields_are_carried_and_exec_may_be_null(dk, deck):
    _data, meta = dk.render(deck, rev=0, session="x", exec_count=None)
    assert meta["praxis"]["exec"] is None and meta["praxis"]["rev"] == 0
    assert dk.stamp("deck", "d", 3, "s", 4) == {"v": 1, "kind": "deck", "resource": "d", "rev": 3, "session": "s", "exec": 4}


def test_bundle_is_refused_when_the_session_is_missing(dk, svg, deck):
    with pytest.raises(svg.UnsafeHtmlError):
        dk.render(deck, rev=1, session="", exec_count=1)


def test_name_line_and_wrapper(dk, deck, deck_html):
    root = _parse(deck_html)
    line = root.find_all(cls="praxis-name")[0]
    assert root.find_all(cls="praxis-name__title")[0].text() == "deck"
    assert root.find_all(cls="praxis-name__type")[0].text() == "HamiltonSTARDeck"
    assert root.find_all(cls="praxis-name__model")[0].text() == "30 rails"
    assert line.tag == "p"
    top = root.children[0]
    assert top.tag == "div" and set(top.attrs["class"].split()) == {"praxis-out", "praxis-deck"}


def test_name_line_and_sentence_survive_without_the_svg_or_any_attribute(deck_html):
    """S2: an untrusted reopen strips the SVG, style, aria-label and data-*; the text must still say it."""
    root = _parse(deck_html)
    without_svg = " ".join(
        n.text() for n in root.walk() if n.tag in ("p", "span") and n.attrs.get("class", "").startswith("praxis-")
    )
    assert "deck" in without_svg and "HamiltonSTARDeck" in without_svg and SPEC_SENTENCE in without_svg


def test_render_is_deterministic_and_does_not_touch_plr_state(dk, deck):
    def snapshot():
        return (
            [(w.name, w.tracker.get_used_volume()) for w in deck.get_resource("assay").get_all_items()],
            [(s.name, s.tip is None) for s in deck.get_resource("tips_300").get_all_items()],
            [(c.name, c.location) for c in deck.children],
        )

    before = snapshot()
    a = dk.render(deck, rev=1, session="s", exec_count=1)
    b = dk.render(deck, rev=1, session="s", exec_count=1)
    assert a == b and snapshot() == before


def test_rendering_a_real_deck_raises_no_warning(dk, decks):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for deck in decks.values():
            dk.render(deck, rev=1, session="s", exec_count=1)


class _Balance(HTMLParser):
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


def test_every_html_form_is_well_balanced(dk, decks):
    docs = []
    for deck in decks.values():
        docs += [dk.render_html(deck, level=lv) for lv in (0, 1, 2)]
    assert all(_is_balanced(d) for d in docs)


def test_balance_checker_control_rejects_broken_markup():
    assert _is_balanced("<div><p>x</p><svg><path d='M0 0'/></svg></div>")
    assert not _is_balanced("<div><p>x</div>")
    assert not _is_balanced("<div><p>x</p>")


# =========================================================================== 8. escaping


def _hostile_problems(doc: str, name: str, group_names: dict[str, str] | None = None) -> list[str]:
    """Independent escape checker: no element or attribute the renderer did not intend, and each
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
            if k.startswith("on") or k in ("href", "src", "srcdoc") or (
                k.startswith("data-") and k not in ("data-praxis-res", "data-praxis-grid", "data-praxis-minw")
            ):
                problems.append(f"unexpected attribute {k}")
    if name in doc and name != html_mod.escape(name, quote=True):
        problems.append("the raw hostile string appears in the html")
    res = {n.attrs["data-praxis-res"] for n in root.walk() if n.tag == "g" and "data-praxis-res" in n.attrs}
    for want in (group_names or {}).values():
        if want not in res:
            problems.append(f"data-praxis-res {want!r} does not round-trip")
    return problems


@pytest.mark.parametrize("name", HOSTILE_NAMES)
def test_hostile_deck_carrier_and_labware_names_are_escaped_everywhere(dk, svg, fx, name):
    deck = _star(20, 600.0, name=name)
    car = fx.hamilton_tip_carrier_L5(name=f"c{name}")
    rack = fx.hamilton_96_tiprack_300uL_filter(name=f"r{name}")
    car[0] = rack
    deck.assign_child_resource(car, track=3)
    pcar = fx.hamilton_plate_carrier_L5_ac(name=f"pc{name}")
    plate = fx.cor_96_wellplate_360uL_Fb(name=f"p{name}")
    plate.get_item("A1").tracker.set_volume(50)
    pcar[0] = plate
    deck.assign_child_resource(pcar, track=9)
    data, meta = dk.render(deck, rev=1, session="s", exec_count=1)
    doc = data["text/html"]
    names = {"deck": name, "car": car.name, "rack": rack.name, "pcar": pcar.name, "plate": plate.name}
    assert _hostile_problems(doc, name, names) == []
    root = _parse(doc)
    assert _outer(root).attrs["data-praxis-res"] == name
    assert _outer(root).attrs["aria-label"] == data["text/plain"]
    assert root.find_all(cls="praxis-name__title")[0].text() == name
    assert meta["praxis"]["resource"] == name
    grid = json.loads(_items(root)[plate.name].attrs["data-praxis-grid"])  # unescape + json.loads round trip
    assert grid["res"] == plate.name
    labels = [t.text() for t in root.find_all("text", cls="sv-label")]
    assert car.name in labels and plate.name in labels  # text, escaped in the source, exact after parsing
    assert plate.name in data["text/plain"] and rack.name in data["text/plain"]
    svg.check_output_html(doc)


def test_hostile_name_html_has_zero_raw_b_tag(dk, fx):
    name = '<b>&"\'x'
    deck = _star(20, 600.0, name=name)
    doc = dk.render(deck, rev=1, session="s", exec_count=1)[0]["text/html"]
    assert "<b>" not in doc
    assert "&lt;b&gt;&amp;&quot;&#x27;x" in doc


def test_escape_checker_control_flags_naive_markup():
    name = '"><script>alert(1)</script>'
    naive = f'<div class="praxis-out"><svg><g data-praxis-res="{name}"></g></svg><p>{name}</p></div>'
    assert _hostile_problems(naive, name)
    name2 = "<b>x"
    assert _hostile_problems(f'<div><p class="praxis-name">{name2}</p></div>', name2)


def test_a_huge_hostile_deck_name_never_breaks_the_cap_and_the_text_is_kept(dk, svg, budget, fx):
    name = "<" * 100_000
    deck = _star(30, 1005.0, name=name)
    car = fx.hamilton_plate_carrier_L5_ac(name="pc")
    car[0] = fx.cor_96_wellplate_360uL_Fb(name=name + "p")
    deck.assign_child_resource(car, track=9)
    data, meta = dk.render(deck, rev=1, session="s", exec_count=1)
    assert budget.html_bytes(data["text/html"]) <= CAP
    assert data["text/plain"].startswith("Plate carrier on rail 9. 1 piece of labware: ")
    assert meta["praxis"]["resource"] == name  # the stamp is JSON: it keeps the full name
    svg.check_bundle(data, meta)


def test_deck_source_never_builds_markup_by_hand_or_escapes_on_its_own(dk):
    assert _markup_lint(_DECK_PATH.read_text(encoding="utf-8")) == []


def _markup_lint(src: str) -> list[str]:
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


# =========================================================================== 9. AC-12: the detail floor, real definitions


def _floor_problems(doc: str, expected_s_min: float | None = None) -> list[str]:
    """AC-12 checker: text >= 11 px, wells and tips >= 4 px, at the s_min the figure declares."""
    root = _parse(doc)
    s_min = _declared_s_min(root)
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


@pytest.mark.parametrize("key", ["fixture1005", "mid600", "narrow440", "oversize1545"])
def test_ac12_text_wells_and_tips_meet_the_floor_on_real_decks(dk, decks, key):
    deck = decks[key]
    doc = dk.render_html(deck)  # level 0: before the byte ladder
    assert _floor_problems(doc, _s_min(deck.get_size_x())) == []
    root = _parse(doc)
    assert len(_texts(root)) >= 9, "a figure with no labels cannot have checked the text floor"
    drawn = sum(len(_subpaths(p.attrs["d"])) for cls in ("sv-well", "sv-tip-ring") for p in root.find_all("path", cls=cls))
    assert drawn >= 96, "a figure with no wells cannot have checked the well floor"


def test_ac12_the_fixture_deck_has_s_min_0_771_not_0_6(deck_html):
    root = _parse(deck_html)
    assert _declared_s_min(root) == pytest.approx(0.7706, abs=1e-3)
    assert float(_svg_root(root).attrs["data-praxis-minw"]) == pytest.approx(774.4, abs=0.02)  # 0.88 * 880: "about 775"
    assert "min-width:774.4" in _svg_root(root).attrs["style"]  # rounded UP to two decimals (774.41)


def test_ac12_every_text_element_is_at_least_11_px_at_s_min(deck_html):
    root = _parse(deck_html)
    s_min = _declared_s_min(root)
    sizes = {round(size * s_min, 3) for _t, size in _texts(root)}
    assert min(sizes) >= 11.0 - 1e-9
    assert min(sizes) < 11.05, "labels are drawn at 12.5 px at s_n, i.e. exactly the floor at s_min"


def test_ac12_a_deck_narrower_than_880_mm_meets_the_same_checks(decks, dk):
    deck = decks["narrow440"]
    root = _parse(dk.render_html(deck))
    s_n = 880 / 440
    assert s_n > 1
    assert _declared_s_min(root) == pytest.approx(max(0.88 * s_n, 0.6))
    svg_el = _svg_root(root)
    assert float(svg_el.attrs["width"]) == pytest.approx(440 * s_n)
    assert _floor_problems(dk.render_html(deck), max(0.88 * s_n, 0.6)) == []


def test_ac12_an_oversize_deck_is_emitted_at_0_6_with_horizontal_scroll(decks, dk):
    """STARDeck is 1545 mm: 880/1545 = 0.57 < 0.6, so s_n = s_min = 0.6 and it scrolls."""
    deck = decks["oversize1545"]
    assert deck.get_size_x() == 1545.0 and 880 / 1545 < 0.6
    root = _parse(dk.render_html(deck))
    svg_el = _svg_root(root)
    assert float(svg_el.attrs["width"]) == pytest.approx(1545 * 0.6)
    assert _declared_s_min(root) == pytest.approx(0.6)
    assert float(svg_el.attrs["data-praxis-minw"]) == pytest.approx(927.0, abs=0.02)
    assert float(svg_el.attrs["data-praxis-minw"]) > 880
    assert dk.deck_scale(deck) == (0.6, 0.6)
    wrapper = root.find_all("div", cls="praxis-fig")[0]
    assert "overflow-x:auto" in wrapper.attrs["style"]


def test_ac11_wrapper_carries_overflow_x_auto_and_the_svg_the_d5_min_width(deck_html):
    root = _parse(deck_html)
    wrappers = root.find_all("div", cls="praxis-fig")
    assert len(wrappers) == 1 and wrappers[0].attrs["style"] == "overflow-x:auto"
    assert _svg_root(root) in wrappers[0].children
    style = _svg_root(root).attrs["style"]
    assert re.fullmatch(r"max-width:100%;min-width:[\d.]+px;height:auto", style), style
    assert float(_svg_root(root).attrs["width"]) == pytest.approx(880, abs=0.01)  # width = W_mm * s_n = 880 px


def test_ac12_checker_controls_fail_on_a_shrunken_font_min_width_and_well(dk, deck):
    doc = dk.render_html(deck)
    assert _floor_problems(doc) == []
    small_font = re.sub(r'font-size="[\d.]+"', 'font-size="3.5"', doc)
    assert any("text" in p for p in _floor_problems(small_font))
    small_min = re.sub(r"min-width:[\d.]+px", "min-width:100px", doc)
    assert _floor_problems(small_min)
    shrunk = re.sub(r"a3\.43 3\.43", "a0.5 0.5", doc)  # a 1 mm well: 0.77 px at s_min
    assert any("sv-well" in p for p in _floor_problems(shrunk))
    tiny_tips = re.sub(r"a3\.6 3\.6", "a0.5 0.5", doc)
    assert any("sv-tip-ring" in p for p in _floor_problems(tiny_tips))
    assert _floor_problems(doc, 0.6), "control: the expected-s_min check rejects the wrong scale (0.6 for 0.771)"


def test_ac12_floor_control_the_naive_scale_would_break_the_text_floor():
    """0.6 px/mm with labels sized for 0.876 would render them at 8.6 px: the reason s_min is not 0.6."""
    assert 12.5 / 0.87562 * 0.6 < 11 <= 12.5 / 0.87562 * 0.7706 + 1e-6


# =========================================================================== 10. AC-13: the byte budget


def test_fixture_deck_meets_its_d4_target_and_the_cap(dk, budget, deck, record_property):
    n = budget.html_bytes(dk.render(deck, rev=1, session="s", exec_count=1)[0]["text/html"])
    record_property("bytes_fixture_deck_level0", n)
    assert n <= DECK_TARGET, f"the fixture deck is {n} bytes (D4 target {DECK_TARGET}; only the orchestrator may change it)"
    assert n <= CAP


def test_the_ladder_levels_shrink_and_meet_the_documented_shapes(dk, budget, svg, deck, record_property):
    full = dk.render_html(deck, level=budget.LEVEL_FULL)
    block = dk.render_html(deck, level=budget.LEVEL_BLOCKS)
    omit = dk.render_html(deck, level=budget.LEVEL_OMITTED)
    sizes = [budget.html_bytes(d) for d in (full, block, omit)]
    for level, n in zip((0, 1, 2), sizes, strict=True):
        record_property(f"bytes_fixture_deck_level{level}", n)
    assert sizes[0] > sizes[1] > sizes[2]
    # level 1: every labware a filled block with no grid; carriers, ruler and labels remain
    root = _parse(block)
    items = _items(root)
    assert "data-praxis-grid" not in block
    for res in _labware_of(deck):
        g = items[res.name]
        assert len(g.find_all("rect", cls="sv-block")) == 1 and not g.find_all("path")
    paths = _paths_in(root)
    assert not {"sv-well", "sv-liquid", "sv-tip-ring", "sv-tip", "sv-tip-gone"} & set(paths)
    assert [t for t, _x in _ruler(root)[0]] == ["1", "5", "10", "15", "20", "25", "30"]
    assert {"tip_carrier", "plate_carrier"} <= {t.text() for t in root.find_all("text", cls="sv-label")}
    assert _floor_problems(block) == []
    # level 2: name line + sentence + omission sentence, and no drawing
    assert "<svg" not in omit and budget.OMISSION_SENTENCE in omit and SPEC_SENTENCE in omit
    assert budget.OMISSION_SENTENCE not in full and budget.OMISSION_SENTENCE not in block
    for d in (full, block, omit):
        svg.check_output_html(d)


def test_render_picks_level_zero_for_the_fixture_deck(dk, budget, deck):
    doc, level = budget.enforce(lambda lv: dk.render_html(deck, level=lv), budget.LEVELS)
    assert level == budget.LEVEL_FULL
    assert dk.render(deck, rev=1, session="s", exec_count=1)[0]["text/html"] == doc


def test_twenty_1536_well_plates_degrade_to_blocks_within_the_cap(dk, budget, svg, record_property):
    from pylabrobot.resources.tecan.plates import Hibase_Greiner_1536_Well

    deck = _plain_deck_of_plates(Hibase_Greiner_1536_Well, 20, size_x=440.0)
    assert 880 / 440 * 0.88 * 2.3 >= 4, "control precondition: these plates are drawn in full at this scale"
    level0 = dk.render_html(deck)
    record_property("bytes_20x1536_level0", budget.html_bytes(level0))
    assert budget.html_bytes(level0) > CAP, "the control needs a deck that is over the cap at level 0"
    assert "data-praxis-grid" in level0 and level0.count("sv-well") == 20
    doc, level = budget.enforce(lambda lv: dk.render_html(deck, level=lv), budget.LEVELS)
    record_property("bytes_20x1536_level1", budget.html_bytes(doc))
    assert level == budget.LEVEL_BLOCKS and budget.html_bytes(doc) <= CAP
    assert "data-praxis-grid" not in doc, "level 1: blocked labware carries no data-praxis-grid"
    items = _items(_parse(doc))
    assert len(items) == 20 and all(g.find_all("rect", cls="sv-block") for g in items.values())
    data, meta = dk.render(deck, rev=1, session="s", exec_count=1)
    assert data["text/html"] == doc and budget.OMISSION_SENTENCE not in doc
    svg.check_bundle(data, meta)
    assert data["text/plain"].startswith("No carriers. 20 pieces of labware: p0, ")


def test_a_deck_too_crowded_for_blocks_degrades_to_summary_only(dk, budget, svg, fx, record_property):
    deck = _plain_deck_of_plates(fx.cor_96_wellplate_360uL_Fb, 400, size_x=2700.0, size_y=1800.0, cols=20, pitch=(130.0, 90.0), prefix="plate_")
    l1 = dk.render_html(deck, level=budget.LEVEL_BLOCKS)
    record_property("bytes_400_level1", budget.html_bytes(l1))
    assert budget.html_bytes(l1) > CAP, "the control needs a deck whose blocks alone are over the cap"
    data, meta = dk.render(deck, rev=1, session="s", exec_count=1)
    doc = data["text/html"]
    assert budget.html_bytes(doc) <= CAP
    assert "<svg" not in doc and budget.OMISSION_SENTENCE in doc
    assert data["text/plain"] in doc and "400 pieces of labware" in doc  # text is never dropped to save a drawing
    svg.check_bundle(data, meta)


def test_render_figure_is_empty_at_level_2_and_drawn_below_it(dk, budget, deck):
    assert dk.render_figure(deck, level=budget.LEVEL_OMITTED) == ""
    assert dk.render_figure(deck, level=budget.LEVEL_FULL).startswith("<div")
    assert dk.render_figure(deck, level=budget.LEVEL_BLOCKS).startswith("<div")


def test_ladder_levels_are_validated(dk, deck):
    for bad in (3, -1, True, "1"):
        with pytest.raises(ValueError):
            dk.render_html(deck, level=bad)


# =========================================================================== 11. import discipline


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


def test_deck_imports_no_pylabrobot_at_module_level_and_only_contract_modules_anywhere(dk):
    src = _DECK_PATH.read_text(encoding="utf-8")
    top = _module_level_imports(src)
    assert not [m for m in top if m.split(".")[0] in ("pylabrobot", "js", "IPython", "pyodide")], top
    import plr_contract

    contract = {path for path, _symbol in plr_contract.CONTRACT}
    used = _all_pylabrobot_imports(src)
    assert used, "deck.py must resolve PLR classes (Deck, Carrier, ...) through the contract"
    assert used <= contract, f"imports outside the contract: {sorted(used - contract)}"
    assert not [m for m in used if m in ("pylabrobot.resources.tip_tracker", "pylabrobot.liquid_handling")]


def test_import_lint_control_flags_a_module_level_plr_import():
    assert _module_level_imports("import pylabrobot\nfrom .svg import x\n") == ["pylabrobot", ".svg"]
    assert _module_level_imports("def f():\n    import pylabrobot\n") == []
    assert _all_pylabrobot_imports("def f():\n    from pylabrobot.resources import Deck\n") == {"pylabrobot.resources"}


def test_deck_imports_in_plain_cpython_without_touching_pylabrobot_or_the_browser():
    """A fresh interpreter, no PLR on the path, warnings as errors: the module must still import."""
    code = (
        "import sys, types, importlib\n"
        f"m = types.ModuleType({_PKG!r}); m.__path__ = [{str(_DISPLAY_DIR)!r}]; sys.modules[{_PKG!r}] = m\n"
        f"dk = importlib.import_module({_PKG + '.deck'!r})\n"
        "bad = [k for k in sys.modules if k.split('.')[0] in ('pylabrobot', 'js', 'IPython', 'pyodide')]\n"
        "assert not bad, bad\n"
        "print('ok')\n"
    )
    proc = subprocess.run([sys.executable, "-W", "error", "-I", "-c", code], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0 and proc.stdout.strip() == "ok", proc.stderr[-1500:]


def test_deck_module_docstring_is_present_and_names_its_spec(dk):
    assert dk.__doc__ and "D2" in dk.__doc__ and "D5" in dk.__doc__
