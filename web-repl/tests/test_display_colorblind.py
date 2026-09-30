"""Colour-vision check for the notebook display's palette (task B8, backlog #5644; spec
``260929_notebook-display-epic.md`` AC-27 colour half, D3 "Errors are never shown by colour alone",
DESIGN.md "Color" and its quality floor: "rose (selection) and brick (error) stay distinct").

**What is checked.** The design's palette pairs that a reader must tell apart, under normal vision and
under protanopia, deuteranopia and tritanopia (Machado, Oliveira and Fernandes 2009, severity 1.0):

* AC-27 itself: CIEDE2000(rose ``#ED7A9B``, brick ``#B3402A``) >= 10 under all four visions, by colour
  alone (no cue may stand in for it: an error must never read as a selection).
* The design's text colours on the sheet keep WCAG contrast >= 4.5 after simulation (ink, ink soft,
  moonstone ink, rose ink, brick).
* The marks of a figure: moonstone (volume) against rose (attention) against brick (error), and each
  against the sheet and the well outline. A pair that collapses under some simulation (CIEDE2000 < 10)
  passes only if a NON-COLOUR cue separates it AND that cue is present in a real render of a plate (a
  filled disk against an unfilled ring; a fault's cross path). "Errors are never shown by colour alone" is
  therefore enforced from the emitted SVG, not from a comment.
* Deck steel against sheet (a deliberately quiet 3.x apart): the cell edge is a rail hairline, so the
  rail must stand clear of BOTH surfaces (CIEDE2000 >= 5) under every vision. That the edge is a rail
  hairline lives in the theme CSS (``test_display_css.py``).

**The instrument is verified first** (``rules/BATHOS.md``: verify the measurement pipeline on ground
truth). CIEDE2000 is checked against eight published Sharma, Wu and Dalal (2005) pairs; the Machado
matrices against their own invariants (each row sums to 1, so white and every grey are fixed points, and
a saturated red really moves under protanopia). Controls that can only pass prove nothing, so each one has
a partner that MUST fail: the near-identical pair AC-27 names (``#ED7A9B`` against ``#E8789A``), a
luminance-matched red/green that is distinct to normal vision and collapses under protan and deutan, a
blue-green pair that collapses under tritan, a cue that the render does not carry, and a mutated palette
(brick swapped for a rose-like colour; the fault cross stripped) run through the same evaluator.

The test asserts and reports no findings. If a number is cited in a doc it goes through bathos first.

**No new dependencies.** The colour math is inline standard-library code; the matrices are inline
constants with their source cited. The palette is read from DESIGN.md and from the SVG the shipped
``labware.py`` emits (real PLR at the 1.0.0b1 pin, for the render-derived cues only).
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import math
import re
import sys
import types
from html.parser import HTMLParser
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL = _TESTS_DIR.parent
_DISPLAY_DIR = _WEB_REPL / "overlay" / "assets" / "python" / "praxis" / "display"
_DESIGN = _WEB_REPL / "design" / "notebook-display" / "DESIGN.md"
_PKG = "_praxis_display_under_test"

VISIONS = ("normal", "protan", "deutan", "tritan")

#: AC-27's number: two marks the reader must tell apart are "distinct" at CIEDE2000 >= 10.
DISTINCT_DE = 10.0
#: A hairline (a rail, a well outline) against the surface it is drawn on: "clear at a glance", not a
#: full mark. Chosen here, before any measurement of the shipped palette (committed red first).
HAIRLINE_DE = 5.0
#: WCAG AA for text.
TEXT_CONTRAST = 4.5

# --------------------------------------------------------------------------- the instrument

# Machado, Oliveira and Fernandes, "A Physiologically-based Model for Simulation of Color Vision
# Deficiency", IEEE Transactions on Visualization and Computer Graphics 15(6), 2009 (the model's
# severity 1.0 matrices, as tabulated by the authors and reproduced by colorspace and DaltonLens). They act
# on LINEAR sRGB, rows summing to 1 so white (and every grey) is a fixed point.
_MACHADO = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritan": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}

# D65 white point, and the sRGB -> XYZ matrix (IEC 61966-2-1, D65).
_WHITE = (0.95047, 1.0, 1.08883)
_SRGB_TO_XYZ = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)

_HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def _rgb(hex_color: str) -> tuple[float, float, float]:
    if not _HEX.fullmatch(hex_color):
        raise ValueError(f"not a #RRGGBB colour: {hex_color!r}")
    return tuple(int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def simulate(hex_color: str, vision: str) -> tuple[float, float, float]:
    """The colour as LINEAR sRGB under ``vision`` (clipped to the gamut, as the model prescribes)."""
    lin = [_linear(c) for c in _rgb(hex_color)]
    if vision == "normal":
        return tuple(lin)
    m = _MACHADO[vision]
    return tuple(min(1.0, max(0.0, sum(m[i][j] * lin[j] for j in range(3)))) for i in range(3))


def _lab(lin: tuple[float, float, float]) -> tuple[float, float, float]:
    xyz = [sum(_SRGB_TO_XYZ[i][j] * lin[j] for j in range(3)) for i in range(3)]

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116

    fx, fy, fz = (f(xyz[i] / _WHITE[i]) for i in range(3))
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def ciede2000(lab1, lab2) -> float:
    """CIEDE2000 (Sharma, Wu and Dalal 2005, "The CIEDE2000 color-difference formula: implementation
    notes, supplementary test data, and mathematical observations"), kL = kC = kH = 1."""
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt(c_bar**7 / (c_bar**7 + 25**7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if c1p else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if c2p else 0.0
    d_l, d_c = l2 - l1, c2p - c1p
    if c1p * c2p == 0:
        d_h = 0.0
    else:
        d_h = h2p - h1p
        if d_h > 180:
            d_h -= 360
        elif d_h < -180:
            d_h += 360
    big_d_h = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(d_h / 2))
    l_bar, c_bar_p = (l1 + l2) / 2, (c1p + c2p) / 2
    if c1p * c2p == 0:
        h_bar = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        h_bar = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        h_bar = (h1p + h2p + 360) / 2
    else:
        h_bar = (h1p + h2p - 360) / 2
    t = (
        1
        - 0.17 * math.cos(math.radians(h_bar - 30))
        + 0.24 * math.cos(math.radians(2 * h_bar))
        + 0.32 * math.cos(math.radians(3 * h_bar + 6))
        - 0.20 * math.cos(math.radians(4 * h_bar - 63))
    )
    d_theta = 30 * math.exp(-(((h_bar - 275) / 25) ** 2))
    r_c = 2 * math.sqrt(c_bar_p**7 / (c_bar_p**7 + 25**7))
    s_l = 1 + 0.015 * (l_bar - 50) ** 2 / math.sqrt(20 + (l_bar - 50) ** 2)
    s_c = 1 + 0.045 * c_bar_p
    s_h = 1 + 0.015 * c_bar_p * t
    r_t = -math.sin(math.radians(2 * d_theta)) * r_c
    return math.sqrt(
        (d_l / s_l) ** 2 + (d_c / s_c) ** 2 + (big_d_h / s_h) ** 2 + r_t * (d_c / s_c) * (big_d_h / s_h)
    )


def delta_e(a: str, b: str, vision: str = "normal") -> float:
    """CIEDE2000 between two ``#RRGGBB`` colours as seen under ``vision``."""
    return ciede2000(_lab(simulate(a, vision)), _lab(simulate(b, vision)))


def min_delta_e(a: str, b: str) -> float:
    """The smallest CIEDE2000 across normal vision and the three simulations."""
    return min(delta_e(a, b, v) for v in VISIONS)


def _luminance(hex_color: str, vision: str) -> float:
    r, g, b = simulate(hex_color, vision)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str, vision: str = "normal") -> float:
    """WCAG contrast ratio of two colours as seen under ``vision``."""
    la, lb = _luminance(a, vision), _luminance(b, vision)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def min_contrast(a: str, b: str) -> float:
    return min(contrast(a, b, v) for v in VISIONS)


# --------------------------------------------------------------------------- the pair evaluator


@dataclasses.dataclass(frozen=True)
class Pair:
    """Two colours a reader must tell apart.

    ``kind``: ``text`` (WCAG contrast >= 4.5), ``mark`` (CIEDE2000 >= 10, or a verified cue) or
    ``hairline`` (CIEDE2000 >= 5). ``cues`` names the non-colour cues (keys of the render evidence) that
    may stand in for colour on a ``mark`` pair; an empty tuple means colour alone must do it.
    """

    name: str
    a: str
    b: str
    kind: str = "mark"
    cues: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class Verdict:
    ok: bool
    by: str  # "colour", "cue" or "" (failed)
    worst: float  # the smallest measure across the four visions (a ratio for text, a delta E otherwise)


def evaluate(pair: Pair, cues: dict[str, bool]) -> Verdict:
    """Does ``pair`` pass under every vision? ``cues`` is what a render shows (cue name -> present)."""
    if pair.kind == "text":
        worst = min_contrast(pair.a, pair.b)
        return Verdict(worst >= TEXT_CONTRAST, "colour" if worst >= TEXT_CONTRAST else "", worst)
    threshold = HAIRLINE_DE if pair.kind == "hairline" else DISTINCT_DE
    worst = min_delta_e(pair.a, pair.b)
    if worst >= threshold:
        return Verdict(True, "colour", worst)
    if pair.cues and all(cues.get(c, False) for c in pair.cues):
        return Verdict(True, "cue", worst)
    return Verdict(False, "", worst)


def failing(pairs, cues: dict[str, bool]) -> list[str]:
    return [p.name for p in pairs if not evaluate(p, cues).ok]


# --------------------------------------------------------------------------- the design's palette


def design_palette() -> dict[str, str]:
    """``{"Rose": "#ED7A9B", ...}`` parsed from DESIGN.md's Color table (the source of truth)."""
    out = {}
    for line in _DESIGN.read_text().splitlines():
        m = re.match(r"\|\s*([A-Za-z][A-Za-z ]*?)\s*\|\s*`(#[0-9A-Fa-f]{6})`", line)
        if m:
            out[m.group(1)] = m.group(2).upper()
    return out


def _package():
    if _PKG not in sys.modules:
        module = types.ModuleType(_PKG)
        module.__path__ = [str(_DISPLAY_DIR)]
        module.__package__ = _PKG
        sys.modules[_PKG] = module
    return sys.modules[_PKG]


@pytest.fixture(scope="module")
def palette():
    p = design_palette()
    for name in ("Deck steel", "Sheet", "Ink", "Ink soft", "Rail", "Moonstone", "Moonstone ink", "Rose",
                 "Rose ink", "Brick"):
        assert name in p, f"DESIGN.md's Color table has no {name!r}: {sorted(p)}"
    return p


@pytest.fixture(scope="module")
def labware():
    _package()
    return importlib.import_module(f"{_PKG}.labware")


# --------------------------------------------------------------------------- the render evidence


class _Paths(HTMLParser):
    """Every ``<path>`` of a document as its attribute dict."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paths: list[dict[str, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "path":
            self.paths.append({k: (v or "") for k, v in attrs})


def _by_class(html: str) -> dict[str, dict[str, str]]:
    parser = _Paths()
    parser.feed(html)
    return {p.get("class", ""): p for p in parser.paths}


def _same(a: str, b: str) -> bool:
    return a.upper() == b.upper()


def render_evidence(labware_module):
    """A real 96-well plate render with liquid, a changed well and a faulted well, at the pin.

    Returns ``(colours, cues)``: the colours the figure actually uses, read from its SVG, and the
    non-colour cues it carries.
    """
    import pylabrobot
    from pylabrobot.resources.corning import cor_96_wellplate_360uL_Fb

    version = str(getattr(pylabrobot, "__version__", ""))
    assert version.startswith("1.0.0b1"), (
        f"PyLabRobot {version!r} at {pylabrobot.__file__} is not the 1.0.0b1 pin; "
        "run with PYTHONPATH=<PLR 1.0.0b1 source> prepended"
    )
    plate = cor_96_wellplate_360uL_Fb(name="cv_plate")
    html = labware_module.render_figure(
        plate,
        volume_of=lambda well: 150.0 if well.get_identifier() in ("A1", "A2", "B1") else 0.0,
        changed={"B2"},
        fault={"C3"},
    )
    paths = _by_class(html)
    for cls in ("sv-well", "sv-liquid", "sv-changed", "sv-fault", "sv-fault-x"):
        assert cls in paths, f"the render has no {cls!r} path: {sorted(paths)}"
    well, liquid = paths["sv-well"], paths["sv-liquid"]
    changed, fault, cross = paths["sv-changed"], paths["sv-fault"], paths["sv-fault-x"]
    colours = {
        "well_fill": well["fill"],
        "well_stroke": well["stroke"],
        "liquid_fill": liquid["fill"],
        "changed_stroke": changed["stroke"],
        "fault_stroke": fault["stroke"],
        "cross_stroke": cross["stroke"],
    }
    cues = {
        # a wet well is a FILLED disk inside its outline; a mark is an UNFILLED ring
        "liquid_is_filled_disk": liquid["fill"].startswith("#") and liquid.get("stroke", "none") in ("", "none"),
        "changed_is_unfilled_ring": changed["fill"] == "none" and changed["stroke"].startswith("#"),
        "fault_is_unfilled_ring": fault["fill"] == "none" and fault["stroke"].startswith("#"),
        # D3: every brick well mark also carries a cross glyph (a second path); a changed mark has none
        "fault_has_cross": bool(cross.get("d")) and cross["fill"] == "none",
        "changed_has_no_cross": "sv-changed-x" not in paths,
    }
    return colours, cues


def design_pairs(palette: dict[str, str], colours: dict[str, str]) -> list[Pair]:
    """The pairs the design juxtaposes. Mark colours come from what the render used."""
    sheet, rail = palette["Sheet"], palette["Rail"]
    pairs = [
        # text on the sheet: the design's stated contrast ratios, kept under every simulation
        Pair("ink on sheet", palette["Ink"], sheet, "text"),
        Pair("ink soft on sheet", palette["Ink soft"], sheet, "text"),
        Pair("moonstone ink on sheet", palette["Moonstone ink"], sheet, "text"),
        Pair("rose ink on sheet", palette["Rose ink"], sheet, "text"),
        Pair("brick on sheet", palette["Brick"], sheet, "text"),
        # surfaces: steel and sheet are quiet by design; the rail hairline must clear BOTH
        Pair("rail on sheet", rail, sheet, "hairline"),
        Pair("rail on deck steel", rail, palette["Deck steel"], "hairline"),
        Pair("well outline on well", colours["well_stroke"], colours["well_fill"], "hairline"),
        # marks: AC-27 (colour alone), then volume against attention against error
        Pair("rose (attention) vs brick (error)", colours["changed_stroke"], colours["fault_stroke"]),
        Pair("moonstone (volume) vs rose (attention)", colours["liquid_fill"], colours["changed_stroke"],
             cues=("liquid_is_filled_disk", "changed_is_unfilled_ring")),
        Pair("moonstone (volume) vs brick (error)", colours["liquid_fill"], colours["fault_stroke"],
             cues=("liquid_is_filled_disk", "fault_is_unfilled_ring", "fault_has_cross")),
        Pair("liquid vs empty well", colours["liquid_fill"], colours["well_fill"]),
        Pair("changed mark on sheet", colours["changed_stroke"], sheet),
        Pair("fault mark on sheet", colours["fault_stroke"], sheet),
        Pair("fault cross vs liquid", colours["cross_stroke"], colours["liquid_fill"],
             cues=("fault_has_cross",)),
    ]
    return pairs


@pytest.fixture(scope="module")
def evidence(labware):
    return render_evidence(labware)


# --------------------------------------------------------------------------- the instrument is verified first

# Sharma, Wu and Dalal (2005), supplementary test data: (Lab1, Lab2, expected dE00), pairs 1-4, 17, 22-24.
_SHARMA = [
    ((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
    ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
    ((50.0, 2.8361, -74.0200), (50.0, 0.0, -82.7485), 3.4412),
    ((50.0, -1.3802, -84.2814), (50.0, 0.0, -82.7485), 1.0000),
    ((50.0, 2.5, 0.0), (50.0, 0.0, -2.5), 4.3065),
    ((50.0, 2.5, 0.0), (73.0, 25.0, -18.0), 27.1492),
    ((50.0, 2.5, 0.0), (61.0, -5.0, 29.0), 22.8977),
    ((50.0, 2.5, 0.0), (56.0, -27.0, -3.0), 31.9030),
]


@pytest.mark.parametrize("lab1,lab2,expected", _SHARMA)
def test_ciede2000_matches_the_published_sharma_pairs(lab1, lab2, expected):
    assert ciede2000(lab1, lab2) == pytest.approx(expected, abs=5e-4)
    assert ciede2000(lab2, lab1) == pytest.approx(expected, abs=5e-4)  # symmetric


@pytest.mark.parametrize("vision", sorted(_MACHADO))
def test_machado_rows_sum_to_one_so_every_grey_is_a_fixed_point(vision):
    for row in _MACHADO[vision]:
        assert sum(row) == pytest.approx(1.0, abs=1e-5)
    for grey in ("#000000", "#404040", "#808080", "#FFFFFF"):
        assert simulate(grey, vision) == pytest.approx(simulate(grey, "normal"), abs=1e-5)


def test_the_simulation_is_not_the_identity():
    """A pipeline that changes nothing would pass every collapse check for the wrong reason: saturated red
    under protanopia must move a long way (positive control for the negatives below)."""
    for vision in ("protan", "deutan"):
        assert delta_e("#FF0000", "#FF0000", vision) == 0
        moved = ciede2000(_lab(simulate("#FF0000", "normal")), _lab(simulate("#FF0000", vision)))
        assert moved > 30, (vision, moved)
    blue = ciede2000(_lab(simulate("#0000FF", "normal")), _lab(simulate("#0000FF", "tritan")))
    assert blue > 20, blue


def test_identity_and_symmetry():
    for v in VISIONS:
        assert delta_e("#73A9C2", "#73A9C2", v) == 0
        assert delta_e("#73A9C2", "#ED7A9B", v) == pytest.approx(delta_e("#ED7A9B", "#73A9C2", v), abs=1e-9)


def test_wcag_contrast_agrees_with_the_designs_stated_ratios(palette):
    """DESIGN.md states 14.8:1 (ink), 6.2:1 (ink soft), 6.1:1 (moonstone ink), 5.2:1 (rose ink) and 5.7:1
    (brick) on the sheet: the contrast function reproduces them, so it measures what the design measured."""
    expect = {"Ink": 14.8, "Ink soft": 6.2, "Moonstone ink": 6.1, "Rose ink": 5.2, "Brick": 5.7}
    for name, ratio in expect.items():
        assert contrast(palette[name], palette["Sheet"]) == pytest.approx(ratio, abs=0.06), name


def test_the_colour_math_uses_only_the_standard_library():
    tree = ast.parse(Path(__file__).read_text())
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    # pytest is the runner; pylabrobot is imported inside render_evidence only, for the real render
    assert roots - stdlib <= {"pytest", "pylabrobot"}, roots - stdlib


# --------------------------------------------------------------------------- AC-27, verbatim


def test_ac27_rose_and_brick_are_distinct_under_every_vision(palette):
    rose, brick = palette["Rose"], palette["Brick"]
    assert (rose, brick) == ("#ED7A9B", "#B3402A")
    for vision in VISIONS:
        assert delta_e(rose, brick, vision) >= DISTINCT_DE, vision


def test_ac27_negative_control_near_identical_rose_fails():
    """``#ED7A9B`` against ``#E8789A`` must FAIL the same check, under every vision."""
    for vision in VISIONS:
        assert delta_e("#ED7A9B", "#E8789A", vision) < DISTINCT_DE, vision
    v = evaluate(Pair("rose vs near-rose", "#ED7A9B", "#E8789A"), {})
    assert not v.ok and v.by == ""


def test_ac27_positive_control_black_against_white_passes():
    for vision in VISIONS:
        assert delta_e("#000000", "#FFFFFF", vision) >= DISTINCT_DE, vision
    assert evaluate(Pair("black vs white", "#000000", "#FFFFFF"), {}).by == "colour"


# --------------------------------------------------------------------------- collapse controls (must FAIL)

# distinct to normal vision, collapsing under protan and deutan (a red and a green of matched luminance)
_RED_GREEN = ("#87281E", "#3C4B1E")
# distinct to normal vision, collapsing under tritan (a blue-green and a green)
_BLUE_GREEN = ("#28F0E1", "#28FF8C")


def test_control_a_red_green_pair_collapses_under_protan_and_deutan_and_fails_the_evaluator():
    a, b = _RED_GREEN
    assert delta_e(a, b, "normal") >= DISTINCT_DE  # distinct to a normal eye: the trap
    assert delta_e(a, b, "protan") < DISTINCT_DE
    assert delta_e(a, b, "deutan") < DISTINCT_DE
    assert not evaluate(Pair("red vs green", a, b), {}).ok


def test_control_a_blue_green_pair_collapses_under_tritan_and_fails_the_evaluator():
    a, b = _BLUE_GREEN
    assert delta_e(a, b, "normal") >= DISTINCT_DE
    assert delta_e(a, b, "tritan") < DISTINCT_DE
    assert not evaluate(Pair("blue-green vs green", a, b), {}).ok


def test_control_the_cue_channel_can_say_yes_and_can_say_no():
    a, b = _RED_GREEN
    pair = Pair("red vs green with a cross", a, b, cues=("has_cross",))
    yes = evaluate(pair, {"has_cross": True})
    assert yes.ok and yes.by == "cue"  # a real cue rescues a collapsing pair, and is reported as a cue
    assert not evaluate(pair, {"has_cross": False}).ok  # a cue the render does not carry rescues nothing
    assert not evaluate(pair, {}).ok
    partial = Pair("needs two cues", a, b, cues=("has_cross", "is_ring"))
    assert not evaluate(partial, {"has_cross": True, "is_ring": False}).ok


def test_control_a_text_colour_that_collapses_under_simulation_fails():
    """Contrast is checked AFTER simulation: a light red on a light green is fine in luminance to no one."""
    assert not evaluate(Pair("light on light", "#E8A0A0", "#FFFFFF", "text"), {}).ok
    assert evaluate(Pair("ink on sheet", "#1D2935", "#FFFFFF", "text"), {}).ok


# --------------------------------------------------------------------------- the shipped palette


def test_labware_colours_are_the_designs(labware, palette):
    c = labware.COLORS
    assert c["sheet"].upper() == palette["Sheet"]
    assert c["ink"].upper() == palette["Ink"]
    assert c["ink_soft"].upper() == palette["Ink soft"]
    assert c["rail"].upper() == palette["Rail"]
    assert c["moonstone"].upper() == palette["Moonstone"]
    assert c["rose"].upper() == palette["Rose"]
    assert c["brick"].upper() == palette["Brick"]


def test_the_rendered_marks_use_the_designs_colours(evidence, palette):
    colours, _cues = evidence
    assert _same(colours["liquid_fill"], palette["Moonstone"])
    assert _same(colours["changed_stroke"], palette["Rose"])
    assert _same(colours["fault_stroke"], palette["Brick"])
    assert _same(colours["cross_stroke"], palette["Brick"])
    assert _same(colours["well_stroke"], palette["Rail"])


def test_the_render_carries_the_non_colour_cues(evidence):
    _colours, cues = evidence
    assert cues == {
        "liquid_is_filled_disk": True,
        "changed_is_unfilled_ring": True,
        "fault_is_unfilled_ring": True,
        "fault_has_cross": True,
        "changed_has_no_cross": True,
    }


def test_every_design_pair_survives_every_vision(palette, evidence):
    colours, cues = evidence
    pairs = design_pairs(palette, colours)
    assert failing(pairs, cues) == []


def test_rose_and_brick_pass_by_colour_alone_never_by_a_cue(palette, evidence):
    colours, cues = evidence
    (pair,) = [p for p in design_pairs(palette, colours) if p.name.startswith("rose (attention) vs brick")]
    assert pair.cues == ()
    verdict = evaluate(pair, cues)
    assert verdict.ok and verdict.by == "colour" and verdict.worst >= DISTINCT_DE


def test_the_hairlines_clear_both_surfaces_so_steel_and_sheet_may_stay_quiet(palette, evidence):
    colours, cues = evidence
    quiet = min_delta_e(palette["Deck steel"], palette["Sheet"])
    assert quiet < HAIRLINE_DE, "steel and sheet are quiet by design; if they are far apart this note is stale"
    for name in ("rail on sheet", "rail on deck steel"):
        (pair,) = [p for p in design_pairs(palette, colours) if p.name == name]
        assert evaluate(pair, cues).ok, name


# --------------------------------------------------------------------------- mutants must be caught


def test_mutant_brick_swapped_for_a_rose_like_colour_is_caught(palette, evidence):
    colours, cues = evidence
    mutated = {**colours, "fault_stroke": "#E8789A", "cross_stroke": "#E8789A"}
    bad = failing(design_pairs(palette, mutated), cues)
    assert "rose (attention) vs brick (error)" in bad, bad
    assert failing(design_pairs(palette, colours), cues) == []  # the unmutated palette is clean


def test_mutant_the_fault_cross_removed_leaves_a_collapsing_error_mark_unsupported(palette, evidence):
    """If the error mark ever loses its cross AND its colour collapses onto the liquid's under some
    vision, the evaluator must fail: colour alone is then all that separates error from volume."""
    colours, cues = evidence
    # an error drawn in (nearly) the liquid's blue: the pair collapses under every vision
    blue_like_moonstone = "#73A9C3"
    mutated_colours = {**colours, "fault_stroke": blue_like_moonstone}
    no_cross = {**cues, "fault_has_cross": False}
    assert min_delta_e(colours["liquid_fill"], blue_like_moonstone) < DISTINCT_DE
    assert "moonstone (volume) vs brick (error)" in failing(design_pairs(palette, mutated_colours), no_cross)
    # with the cross (and both ring cues) present the same colours are rescued by a cue
    ok = evaluate(
        [p for p in design_pairs(palette, mutated_colours) if p.name.startswith("moonstone (volume) vs brick")][0],
        cues,
    )
    assert ok.ok and ok.by == "cue"


def test_mutant_a_volume_colour_that_collapses_onto_rose_needs_its_cue(palette, evidence):
    """Volume against attention: with the liquid recoloured to (nearly) rose the pair collapses under every
    vision, so only the cue (a filled disk against an unfilled ring) can carry it, and without the filled
    disk the evaluator must fail."""
    colours, cues = evidence
    mutated = {**colours, "liquid_fill": "#EC7A9A"}
    (pair,) = [p for p in design_pairs(palette, mutated) if p.name.startswith("moonstone (volume) vs rose")]
    assert min_delta_e(pair.a, pair.b) < DISTINCT_DE
    assert not evaluate(pair, {**cues, "liquid_is_filled_disk": False}).ok
    assert not evaluate(pair, {**cues, "changed_is_unfilled_ring": False}).ok
    assert evaluate(pair, cues).by == "cue"
