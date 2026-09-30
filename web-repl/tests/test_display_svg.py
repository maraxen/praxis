"""Browserless tests for ``praxis/display/svg.py`` (task B1, backlog #5632).

Spec: ``260929_notebook-display-epic.md`` D2 (escaping; one mimebundle, no
``<script>``/``<style>``/``image/svg+xml``), D3 (inline colour attributes), D4 (one path per
state), D14 (``data-*`` names), and the S2 spike result (an untrusted reopen keeps only
``class`` on ``table``/``details``/``summary`` and strips the whole SVG, ``style``, ``aria-label``
and every ``data-*``).

Import discipline, as in ``test_browser_visualizer.py`` and per ADR
``260817_repl-layout-and-delivery-mechanism.md`` Sec 2.4: the module is loaded BY PATH under a
synthetic name. This file must never put ``web-repl/overlay/assets/python`` on ``sys.path``
(its ``praxis/`` would shadow the repo's real ``praxis``; ``test_rid_invariant.py`` guards it).

Every check that could pass vacuously has a control that must FAIL: the escape round-trip
checker is run against an escaper that escapes nothing and against one that leaves quotes
raw; the output scanner is run against a hand-built hostile document; the S2 sanitizer
simulation is run against a text that lives only in SVG.
"""

from __future__ import annotations

import ast
import html
import importlib.util
import json
import math
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

_DISPLAY_DIR = (
    Path(__file__).resolve().parents[1]
    / "overlay" / "assets" / "python" / "praxis" / "display"
)
_SVG_PATH = _DISPLAY_DIR / "svg.py"
_PKG = "_praxis_display_svg_under_test"

# The allowed ``data-*`` names in an OUTPUT (D14; D5 S2-A' branch names ``data-praxis-minw``).
# ``data-praxis-cell-state`` / ``data-praxis-exec`` are written by the shell onto cell
# DOM nodes, never emitted inside an output.
ALLOWED_DATA = {"data-praxis-res", "data-praxis-grid", "data-praxis-minw"}

# Strings chosen to break an escaper that handles only the obvious cases.
ADVERSARIAL = [
    "<script>alert(1)</script>",
    "</svg><script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "' onmouseover='alert(1)",
    '" onfocus="alert(1)" x="',
    "&",
    "&amp;",
    "&lt;script&gt;",
    "&#60;script&#62;",
    "a&b<c>d\"e'f",
    "<b>&\"'x",
    "<!-- comment -->",
    "]]>",
    "javascript:alert(1)",
    "<style>*{display:none}</style>",
    "plain name",
    "µL wells",
    "日本語のプレート",
    "\U0001f9ea tube",
    "‮evil‬",
    "tab\tnew\nline",
    "\x00nul",
    "x" * 100_000,
    "<" * 5_000,
    "\"'&<>" * 4_000,
]


# --------------------------------------------------------------------------- loading


@pytest.fixture(scope="module")
def svg():
    """Load praxis/display/svg.py by path. A missing module is the RED reason."""
    if _PKG in sys.modules:
        return sys.modules[_PKG]
    if not _SVG_PATH.is_file():
        pytest.fail(f"praxis/display/svg.py does not exist yet: {_SVG_PATH}")
    spec = importlib.util.spec_from_file_location(_PKG, _SVG_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[_PKG] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- helpers


class _Collector(HTMLParser):
    """Records every start tag with its ORDERED attribute pairs, and all text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, list[tuple[str, str | None]]]] = []
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, list(attrs)))

    def handle_data(self, data):
        self.text.append(data)


def _parse(doc: str) -> _Collector:
    c = _Collector()
    c.feed(doc)
    c.close()
    return c


def _text_of(doc: str) -> str:
    return "".join(_parse(doc).text)


def _roundtrip_ok(esc_text, esc_attr, s: str) -> bool:
    """Embed *s* as an attribute value and as text; True iff nothing broke out.

    Breakout means: another tag or attribute appeared, or the value did not come back
    byte-identical after the browser's own decoding (``HTMLParser`` here).
    """
    doc = f'<div data-praxis-res="{esc_attr(s)}">{esc_text(s)}</div>'
    c = _parse(doc)
    if [t for t, _ in c.tags] != ["div"]:
        return False
    if c.tags[0][1] != [("data-praxis-res", s)]:
        return False
    return "".join(c.text) == s


def _independent_scan(doc: str) -> dict:
    """Scan written from the spec, not from the module under test."""
    parsed = _parse(doc)
    data_names = {
        name for _, attrs in parsed.tags for name, _ in attrs if name.startswith("data-")
    }
    on_attrs = {
        name for _, attrs in parsed.tags for name, _ in attrs if name.startswith("on")
    }
    tags = {t for t, _ in parsed.tags}
    return {
        "script": bool(re.search(r"<\s*script", doc, re.I)) or "script" in tags,
        "style_el": bool(re.search(r"<\s*style", doc, re.I)) or "style" in tags,
        "data_names": data_names,
        "on_attrs": on_attrs,
    }


def _path_tokens(d: str) -> list[tuple[str, list[float]]]:
    """Tiny SVG path tokenizer: [(command, [numbers])]. Enough for M m L l H h V v A a Z z."""
    out: list[tuple[str, list[float]]] = []
    for m in re.finditer(r"([MmLlHhVvAaZz])([^MmLlHhVvAaZz]*)", d):
        nums = [float(x) for x in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", m.group(2))]
        out.append((m.group(1), nums))
    return out


def _endpoints(d: str) -> list[tuple[float, float]]:
    """Absolute end points of every segment, following the SVG current-point rules."""
    pts: list[tuple[float, float]] = []
    x = y = 0.0
    for cmd, n in _path_tokens(d):
        if cmd == "M":
            x, y = n[0], n[1]
        elif cmd == "m":
            x, y = x + n[0], y + n[1]
        elif cmd == "L":
            x, y = n[0], n[1]
        elif cmd == "l":
            x, y = x + n[0], y + n[1]
        elif cmd == "H":
            x = n[0]
        elif cmd == "h":
            x += n[0]
        elif cmd == "V":
            y = n[0]
        elif cmd == "v":
            y += n[0]
        elif cmd == "A":
            x, y = n[5], n[6]
        elif cmd == "a":
            x, y = x + n[5], y + n[6]
        elif cmd in "Zz":
            continue
        pts.append((x, y))
    return pts


def _imports_of(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0] if node.level == 0 else "<relative>")
    return names


_FORBIDDEN_IMPORTS = {"js", "pyodide", "pyodide_js", "IPython", "ipykernel", "pylabrobot",
                      "web_bridge", "web_serial_shim", "web_usb_shim", "web_hid_shim",
                      "web_ftdi_shim", "praxis", "<relative>"}


# S2's untrusted-reopen sanitizer, simulated: keep only these elements, and only `class`.
_S2_KEEP = {"table", "thead", "tbody", "tr", "td", "th", "details", "summary", "div", "p",
            "span", "pre", "b", "i", "em", "strong", "code", "br"}


def _s2_untrusted_text(doc: str) -> str:
    """Text a viewer shows after S2's sanitizer: SVG subtree and all attributes but class gone."""
    class _P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.svg_depth = 0
            self.out: list[str] = []

        def handle_starttag(self, tag, attrs):
            if tag == "svg":
                self.svg_depth += 1

        def handle_endtag(self, tag):
            if tag == "svg" and self.svg_depth:
                self.svg_depth -= 1

        def handle_data(self, data):
            if not self.svg_depth:
                self.out.append(data)

    p = _P()
    p.feed(doc)
    p.close()
    return "".join(p.out)


def _s2_surviving_attrs(doc: str) -> dict[str, set[str]]:
    """Per-tag attribute names that a class-only sanitizer would NOT strip."""
    kept: dict[str, set[str]] = {}
    for tag, attrs in _parse(doc).tags:
        if tag in _S2_KEEP:
            kept.setdefault(tag, set()).update(n for n, _ in attrs if n != "class")
    return kept


# --------------------------------------------------------------------------- purity


def test_module_imports_only_the_standard_library(svg):
    imports = _imports_of(_SVG_PATH.read_text())
    assert not (imports & _FORBIDDEN_IMPORTS), imports & _FORBIDDEN_IMPORTS
    stdlib = set(sys.stdlib_module_names)
    assert imports <= stdlib | {"__future__"}, imports - stdlib


def test_import_scanner_control_flags_a_forbidden_import():
    """Negative control: the scanner must fire on `import js` and a PLR import."""
    src = "import js\nfrom pylabrobot.resources import Plate\nfrom . import x\nimport html\n"
    found = _imports_of(src)
    assert {"js", "pylabrobot", "<relative>", "html"} <= found
    assert found & _FORBIDDEN_IMPORTS == {"js", "pylabrobot", "<relative>"}


# --------------------------------------------------------------------------- escaping


def test_escapers_are_exactly_html_escape_with_quotes(svg):
    for s in ADVERSARIAL:
        assert svg.esc_text(s) == html.escape(s, quote=True)
        assert svg.esc_attr(s) == html.escape(s, quote=True)


@pytest.mark.parametrize("s", ADVERSARIAL, ids=lambda s: repr(s[:24]))
def test_escapers_neither_break_out_nor_lose_the_value(svg, s):
    assert _roundtrip_ok(svg.esc_text, svg.esc_attr, s)


@pytest.mark.parametrize("s", [x for x in ADVERSARIAL if "<" in x or '"' in x or "'" in x][:12],
                         ids=lambda s: repr(s[:24]))
def test_escaped_output_has_no_raw_metacharacters(svg, s):
    for esc in (svg.esc_text, svg.esc_attr):
        out = esc(s)
        assert not set('<>"\'') & set(out)
        # every ampersand introduces an entity
        assert not re.search(r"&(?![A-Za-z]+;|#\d+;|#x[0-9A-Fa-f]+;)", out)


def test_round_trip_checker_is_not_vacuous():
    """Negative controls: an escaper that escapes nothing, and one that leaves quotes raw."""
    identity = lambda s: s  # noqa: E731
    no_quotes = lambda s: html.escape(s, quote=False)  # noqa: E731
    # An escaper that escapes nothing must be caught on every string that can actually break
    # markup (a bare "<<<" is inert to an HTML parser, so it is not in this list).
    must_break = [
        "<script>alert(1)</script>", "</svg><script>alert(1)</script>",
        '"><img src=x onerror=alert(1)>',
        '" onfocus="alert(1)" x="', "&amp;", "&lt;script&gt;", "&#60;script&#62;",
        "a&b<c>d\"e'f", "<b>&\"'x", "<style>*{display:none}</style>", "<!-- comment -->",
    ]
    assert set(must_break) <= set(ADVERSARIAL)
    assert all(not _roundtrip_ok(identity, identity, s) for s in must_break)
    # An escaper that leaves quotes raw must be caught wherever a quote is present.
    quoted = [s for s in ADVERSARIAL if '"' in s and len(s) < 100]
    assert len(quoted) >= 4
    assert all(not _roundtrip_ok(html.escape, no_quotes, s) for s in quoted)
    # ...and the checker does accept a correct escaper, so it can pass at all.
    assert all(_roundtrip_ok(html.escape, html.escape, s) for s in ADVERSARIAL)


def test_escapers_coerce_non_strings_and_are_deterministic(svg):
    assert svg.esc_text(5) == "5"
    assert svg.esc_attr(2.5) == "2.5"
    s = ADVERSARIAL[9]
    assert svg.esc_text(s) == svg.esc_text(s) and svg.esc_attr(s) == svg.esc_attr(s)


def test_very_long_names_stay_linear_and_lossless(svg):
    s = "\"'&<>" * 40_000
    out = svg.esc_attr(s)
    assert len(out) < len(s) * 7
    assert html.unescape(out) == s


# --------------------------------------------------------------------------- attributes


def test_attrs_keeps_hostile_values_inside_one_attribute(svg):
    for s in ADVERSARIAL:
        doc = f"<div{svg.attrs(data_praxis_res=s)}></div>"
        c = _parse(doc)
        assert [t for t, _ in c.tags] == ["div"]
        assert c.tags[0][1] == [("data-praxis-res", s)]


def test_attrs_underscores_become_hyphens_and_order_is_preserved(svg):
    out = svg.attrs(stroke_width=1.5, fill="#73A9C2", stroke="#1D2935")
    assert out == ' stroke-width="1.5" fill="#73A9C2" stroke="#1D2935"'


def test_attrs_grid_descriptor_round_trips_through_unescape_and_json(svg):
    grid = {"o": [1.5, 2.5], "rows": 8, "cols": 12, "ids": ["A1", '"B"<2>'], "v": [50, None]}
    doc = f"<g{svg.attrs(data_praxis_grid=json.dumps(grid))}></g>"
    (_, attrs), = _parse(doc).tags
    assert json.loads(dict(attrs)["data-praxis-grid"]) == grid
    assert '"B"<2>' not in doc  # never raw in the markup


@pytest.mark.parametrize("name", [
    "data_praxis_evil", "data_x", "data-", "data_praxis_res_", "DATA_PRAXIS_RES",
    "data_praxis_cell_state", "data_praxis_exec", "data_praxis_test",
])
def test_attrs_rejects_data_names_outside_the_allowed_set(svg, name):
    with pytest.raises(ValueError):
        svg.attrs(**{name: "x"})


@pytest.mark.parametrize("name", ["data_praxis_res", "data_praxis_grid", "data_praxis_minw"])
def test_attrs_accepts_each_allowed_data_name(svg, name):
    assert svg.attrs(**{name: "x"}) == f' {name.replace("_", "-")}="x"'


def test_allowed_data_names_are_exactly_the_documented_set(svg):
    assert set(svg.ALLOWED_DATA_ATTRS) == ALLOWED_DATA


@pytest.mark.parametrize("name", [
    "onclick", "onload", "onerror", "onmouseover", "OnClick", "href", "src", "srcdoc",
    "xlink:href", "a b", 'a"b', "a=b", "a>b", "", "1a", "a<b", "a\nb", "a/b",
])
def test_attrs_rejects_unsafe_or_malformed_names(svg, name):
    with pytest.raises(ValueError):
        svg.attrs(**{name: "x"})


def test_attrs_rejects_names_that_collide_after_normalisation(svg):
    with pytest.raises(ValueError):
        svg.attrs(**{"stroke_width": 1, "stroke-width": 2})


def test_attrs_none_is_omitted_bool_is_rejected_numbers_are_compact(svg):
    assert svg.attrs(fill=None, stroke="#000") == ' stroke="#000"'
    with pytest.raises(TypeError):
        svg.attrs(hidden=True)
    assert svg.attrs(width=127.76, height=85) == ' width="127.76" height="85"'


def test_attrs_is_deterministic(svg):
    assert svg.attrs(a=1, b="<>") == svg.attrs(a=1, b="<>")


# --------------------------------------------------------------------------- elements


@pytest.mark.parametrize("tag", ["script", "SCRIPT", "Script", "style", "STYLE", "img onerror=x",
                                 "", "1div", "div>", "a b", "iframe", "object", "embed", "link",
                                 "meta", "base", "foreignObject"])
def test_el_rejects_dangerous_or_malformed_tags(svg, tag):
    with pytest.raises(ValueError):
        svg.el(tag, "x")


@pytest.mark.parametrize("tag", ["div", "span", "p", "pre", "table", "tr", "td", "th", "details",
                                 "summary", "svg", "g", "path", "rect", "text", "title"])
def test_el_accepts_the_tags_the_displays_use(svg, tag):
    assert svg.el(tag, "x", cls="c") == f'<{tag} class="c">x</{tag}>'


def test_el_interpolates_inner_verbatim_and_escapes_attributes(svg):
    doc = svg.el("div", svg.esc_text("<b>&"), data_praxis_res='"><x>')
    c = _parse(doc)
    assert [t for t, _ in c.tags] == ["div"]
    assert c.tags[0][1] == [("data-praxis-res", '"><x>')]
    assert "".join(c.text) == "<b>&"


def test_el_cls_alias_is_class_and_is_validated(svg):
    assert svg.el("div", "", cls="a-b c_d") == '<div class="a-b c_d"></div>'
    for bad in ('a"b', "a<b", "a=b", "", "a\nb"):
        with pytest.raises(ValueError):
            svg.el("div", "", cls=bad)


def test_text_line_is_class_only_and_escapes(svg):
    for s in ADVERSARIAL:
        doc = svg.text_line("p", "praxis-sentence", s)
        c = _parse(doc)
        assert c.tags == [("p", [("class", "praxis-sentence")])]
        assert "".join(c.text) == s


def test_text_el_font_size_is_in_user_units_and_never_rounded_down(svg):
    for size in (12.5 / 3, 12.5 / 0.8756, 12.5 / 2.5, 4.16, 14.27, 5.0, 100.0):
        doc = svg.text_el(1, 2, "A1", size)
        (_, attrs), = _parse(doc).tags
        d = dict(attrs)
        assert float(d["font-size"]) >= size - 1e-12, (size, d["font-size"])
        assert float(d["font-size"]) - size < 0.0101
        assert "px" not in d["font-size"]


def test_text_el_escapes_and_keeps_position(svg):
    for s in ADVERSARIAL:
        doc = svg.text_el(3.5, 4.25, s, 4.17, anchor="middle")
        c = _parse(doc)
        assert [t for t, _ in c.tags] == ["text"]
        d = dict(c.tags[0][1])
        assert (d["x"], d["y"], d["text-anchor"]) == ("3.5", "4.25", "middle")
        assert "".join(c.text) == s


def test_text_el_validates_size_and_anchor(svg):
    for bad in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            svg.text_el(0, 0, "x", bad)
    with pytest.raises(ValueError):
        svg.text_el(0, 0, "x", 4, anchor="left")
    with pytest.raises(ValueError):
        svg.text_el(0, 0, "x", 4, anchor='middle" onload="x')


def test_path_el_emits_one_path_with_escaped_attributes(svg):
    doc = svg.path_el("M0 0h1v1z", fill="#73A9C2", stroke_width=0.5)
    assert doc == '<path d="M0 0h1v1z" fill="#73A9C2" stroke-width="0.5"/>'
    hostile = svg.path_el('M0 0"><script>', fill='"><x>')
    c = _parse(hostile)
    assert [t for t, _ in c.tags] == ["path"]


# --------------------------------------------------------------------------- numbers


@pytest.mark.parametrize("x, expected", [
    (0, "0"), (0.0, "0"), (-0.0, "0"), (1, "1"), (1.0, "1"), (12.5, "12.5"), (3.14159, "3.14"),
    (-2.5, "-2.5"), (1.005, "1.01"), (0.004, "0"), (-0.004, "0"), (127.76, "127.76"),
    (100, "100"), (1e-9, "0"), (0.1 + 0.2, "0.3"),
])
def test_num_is_compact_two_decimals_half_up_and_never_negative_zero(svg, x, expected):
    assert svg.num(x) == expected


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_num_rejects_non_finite_values(svg, bad):
    with pytest.raises(ValueError):
        svg.num(bad)
    with pytest.raises(ValueError):
        svg.num_ceil(bad)


@pytest.mark.parametrize("x, expected", [
    (4.16, "4.16"), (12.5 / 3, "4.17"), (4.161, "4.17"), (0, "0"), (5, "5"), (12.5 / 2.5, "5"),
])
def test_num_ceil_never_rounds_down(svg, x, expected):
    assert svg.num_ceil(x) == expected
    assert float(svg.num_ceil(x)) >= x - 1e-12


@pytest.mark.parametrize("x, expected", [
    (0, "0"), (50, "50"), (2400, "2,400"), (19200, "19,200"), (12.34, "12.3"), (12.25, "12.3"),
    (0.25, "0.3"), (999.95, "1,000"), (1234567.891, "1,234,567.9"), (-0.04, "0"), (150.0, "150"),
    (16800, "16,800"), (200.5, "200.5"),
])
def test_fmt_amount_is_thousands_separated_at_most_one_decimal(svg, x, expected):
    assert svg.fmt_amount(x) == expected


def test_fmt_amount_rejects_non_finite(svg):
    with pytest.raises(ValueError):
        svg.fmt_amount(float("nan"))


# --------------------------------------------------------------------------- path builders


def test_circle_path_is_one_subpath_of_two_arcs_returning_to_start(svg):
    d = svg.circle_path(10, 20, 3.43)
    toks = _path_tokens(d)
    assert [c for c, _ in toks if c not in "Zz"] == ["M", "a", "a"]
    assert d.count("M") == 1
    assert toks[0][1] == [6.57, 20.0]
    arcs = [n for c, n in toks if c == "a"]
    assert all(a[0] == a[1] == 3.43 for a in arcs)
    # relative arcs: +2r then -2r along x, so the path closes on its start
    assert arcs[0][5] + arcs[1][5] == pytest.approx(0.0, abs=1e-9)
    assert abs(arcs[0][5]) == pytest.approx(6.86)
    assert arcs[0][6] == arcs[1][6] == 0.0


def test_circle_path_emits_no_circle_element_and_is_compact(svg):
    d = svg.circle_path(123.45, 67.89, 3.43)
    assert "<" not in d and "circle" not in d
    assert len(d) <= 64  # measured: 60 bytes for this circle (D4 estimated ~35, unmeasured)


def test_circle_path_is_deterministic(svg):
    assert svg.circle_path(1.234, 5.678, 0.9) == svg.circle_path(1.234, 5.678, 0.9)


@pytest.mark.parametrize("args", [(0, 0, 0), (0, 0, -1), (0, 0, float("nan")), (float("inf"), 0, 1),
                                  (0, float("nan"), 1)])
def test_circle_path_rejects_degenerate_input(svg, args):
    with pytest.raises(ValueError):
        svg.circle_path(*args)


def test_rect_path_plain_rect_visits_exactly_its_four_corners(svg):
    d = svg.rect_path(5, 6, 10, 4)
    assert d.count("M") == 1
    assert set(_endpoints(d)) == {(5, 6), (15, 6), (15, 10), (5, 10)}


def test_rect_path_rounded_rect_stays_inside_its_box_and_clamps_radius(svg):
    d = svg.rect_path(5, 6, 10, 4, rx=2)
    pts = _endpoints(d)
    assert min(p[0] for p in pts) == 5 and max(p[0] for p in pts) == 15
    assert min(p[1] for p in pts) == 6 and max(p[1] for p in pts) == 10
    assert sum(1 for c, _ in _path_tokens(d) if c in "Aa") == 4
    # an oversized radius clamps to half the short side; endpoints never leave the box
    big = _endpoints(svg.rect_path(5, 6, 10, 4, rx=99))
    assert all(5 <= x <= 15 and 6 <= y <= 10 for x, y in big)


@pytest.mark.parametrize("args", [(0, 0, 0, 1), (0, 0, 1, 0), (0, 0, -1, 1), (0, 0, float("nan"), 1)])
def test_rect_path_rejects_degenerate_input(svg, args):
    with pytest.raises(ValueError):
        svg.rect_path(*args)
    with pytest.raises(ValueError):
        svg.rect_path(0, 0, 1, 1, rx=-1)


def test_cross_path_is_two_diagonal_subpaths(svg):
    d = svg.cross_path(10, 20, 2)
    assert d.count("M") == 2
    assert set(_endpoints(d)) == {(8, 18), (12, 22), (8, 22), (12, 18)}
    for bad in (0, -1, float("nan")):
        with pytest.raises(ValueError):
            svg.cross_path(0, 0, bad)


def test_many_circles_join_into_one_path_with_one_m_each(svg):
    subs = [svg.circle_path(9 * (i % 12) + 14.38, 9 * (i // 12) + 11.24, 3.43) for i in range(96)]
    d = "".join(subs)
    assert d.count("M") == 96
    doc = svg.path_el(d, fill="#73A9C2")
    assert doc.count("<path") == 1 and "<circle" not in doc
    assert len(doc.encode()) < 8_000  # D4: one path per state stays small


# --------------------------------------------------------------------------- details / text fallbacks


def test_details_html_is_class_only_and_escapes_summary_and_body(svg):
    for s in ADVERSARIAL:
        doc = svg.details_html(s, s)
        c = _parse(doc)
        tags = [t for t, _ in c.tags]
        assert tags == ["details", "summary", "pre"], tags
        for _, attrs in c.tags:
            assert [n for n, _ in attrs] == ["class"]
        assert "".join(c.text) == s + s


def test_details_html_text_survives_a_class_only_sanitizer(svg):
    doc = svg.details_html("Show traceback", "Traceback (most recent call last):\n  KeyError: 'x'")
    assert _s2_surviving_attrs(doc) == {"details": set(), "summary": set(), "pre": set()}
    text = _s2_untrusted_text(doc)
    assert "Show traceback" in text and "KeyError: 'x'" in text


def test_sanitizer_simulation_control_loses_svg_only_text_and_flags_style_attrs(svg):
    """Negative control for the S2 simulation: text that lives only in SVG is lost."""
    doc = f'<div style="x:y">{svg.el("svg", svg.text_el(0, 0, "only in svg", 4.17), aria_label="only in label")}</div>'
    assert "only in svg" not in _s2_untrusted_text(doc)
    assert "only in label" not in _s2_untrusted_text(doc)
    assert _s2_surviving_attrs(doc) == {"div": {"style"}}


def test_details_html_rejects_a_bad_class(svg):
    with pytest.raises(ValueError):
        svg.details_html("s", "b", cls='x" onclick="y')


# --------------------------------------------------------------------------- whole-document safety


def _compose(svg, name: str) -> str:
    """A representative figure built only from svg.py primitives, around a hostile *name*."""
    inner = (
        svg.path_el(svg.circle_path(10, 10, 3.43), fill="none", stroke="#1D2935")
        + svg.path_el(svg.cross_path(10, 10, 2), stroke="#B5482F")
        + svg.text_el(1, 2, name, 4.17)
        + svg.el("title", svg.esc_text(name))
    )
    figure = svg.el(
        "svg", inner, viewBox="0 0 100 50", width=300, height=150,
        style="max-width:100%;min-width:264px;height:auto",
        role="img", aria_label=name, tabindex=0,
        data_praxis_res=name, data_praxis_grid=json.dumps({"n": name}),
    )
    return (
        svg.el("div", svg.text_line("p", "praxis-name", name) + figure
               + svg.details_html("Show traceback", name), style="overflow-x:auto")
    )


@pytest.mark.parametrize("name", ADVERSARIAL, ids=lambda s: repr(s[:24]))
def test_composed_figure_has_no_script_style_or_stray_data_names(svg, name):
    doc = _compose(svg, name)
    scan = _independent_scan(doc)
    assert not scan["script"] and not scan["style_el"]
    assert scan["data_names"] <= ALLOWED_DATA
    assert not scan["on_attrs"]
    assert "<script" not in doc.lower() and "<style" not in doc.lower()
    svg.check_output_html(doc)  # the module's own guard agrees


def test_independent_scan_control_flags_a_hostile_document():
    """Negative control: the scan really fires."""
    bad = '<div onclick="x"><script>1</script><style>a{}</style><b data-evil="1"></b></div>'
    scan = _independent_scan(bad)
    assert scan["script"] and scan["style_el"]
    assert scan["data_names"] == {"data-evil"} and scan["on_attrs"] == {"onclick"}


@pytest.mark.parametrize("bad", [
    "<script>1</script>", "<SCRIPT >1</SCRIPT>", "< script>", "<style>a{}</style>", "<STYLE>",
    '<div onclick="x">', '<svg onload="x">', '<a href="javascript:x">', '<img src="x">',
    '<div data-evil="1">', '<div data-praxis-cell-state="run">', "<iframe>", "<object>", "<embed>",
    "<foreignObject>", "<link rel=stylesheet>", "<meta>", "<base>",
])
def test_check_output_html_rejects_hostile_documents(svg, bad):
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_output_html(bad)


def test_unsafe_html_error_is_a_value_error(svg):
    assert issubclass(svg.UnsafeHtmlError, ValueError)


def test_check_output_html_accepts_allowed_data_names_and_inline_style(svg):
    svg.check_output_html(
        '<div style="overflow-x:auto" data-praxis-res="a" data-praxis-grid="{}" '
        'data-praxis-minw="390"><svg viewBox="0 0 1 1"><path d="M0 0" fill="#73A9C2"/></svg></div>'
    )


def test_check_output_html_is_not_fooled_by_escaped_user_text(svg):
    svg.check_output_html(svg.text_line("p", "n", "<script>alert(1)</script> & data-evil=1 onclick=x"))


# --------------------------------------------------------------------------- bundle guard (D2)


def _stamp(**over):
    s = {"v": 1, "kind": "plate", "resource": "assay", "rev": 3, "session": "abc123", "exec": 4}
    s.update(over)
    return s


def _bundle(html_doc="<p class=\"n\">hi</p>", plain="hi", stamp=None):
    return {"text/html": html_doc, "text/plain": plain}, {"praxis": stamp or _stamp()}


def test_check_bundle_accepts_a_well_formed_bundle_in_both_carrier_shapes(svg):
    data, meta = _bundle()
    svg.check_bundle(data, meta)
    svg.check_bundle(data, {"text/html": {"praxis": _stamp()}})  # S3-B carrier (D2, D1)


@pytest.mark.parametrize("kind, resource, rev", [
    ("plate", "assay", 0), ("tiprack", "tips", 12), ("container", "trough", 1), ("deck", "deck", 7),
    ("ledger", None, None), ("error", None, None), ("error", "assay", None),
])
def test_check_bundle_accepts_each_kind_with_its_null_pattern(svg, kind, resource, rev):
    data, _ = _bundle()
    svg.check_bundle(data, {"praxis": _stamp(kind=kind, resource=resource, rev=rev, exec=None)})


@pytest.mark.parametrize("extra_key", ["image/svg+xml", "application/javascript", "text/javascript",
                                       "application/json", "image/png", "text/markdown"])
def test_check_bundle_rejects_any_mime_beyond_html_and_plain(svg, extra_key):
    data, meta = _bundle()
    data[extra_key] = "<svg/>"
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_bundle(data, meta)


def test_check_bundle_rejects_missing_text_plain_or_empty_data(svg):
    data, meta = _bundle()
    del data["text/plain"]
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_bundle(data, meta)
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_bundle({}, meta)
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_bundle({"text/html": "<p/>", "text/plain": ""}, meta)


def test_check_bundle_runs_the_html_guard(svg):
    data, meta = _bundle(html_doc="<div><script>1</script></div>")
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_bundle(data, meta)


@pytest.mark.parametrize("bad", [
    {"v": 2}, {"kind": "PLATE"}, {"kind": "well"}, {"kind": None}, {"resource": 5}, {"rev": True},
    {"rev": "3"}, {"rev": -1}, {"session": ""}, {"session": None}, {"exec": True}, {"exec": 1.5},
    {"exec": -1}, {"v": True},
])
def test_check_bundle_rejects_malformed_stamp_values(svg, bad):
    data, _ = _bundle()
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_bundle(data, {"praxis": _stamp(**bad)})


def test_check_bundle_rejects_missing_or_extra_stamp_keys_or_no_stamp(svg):
    data, _ = _bundle()
    s = _stamp()
    del s["exec"]
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_bundle(data, {"praxis": s})
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_bundle(data, {"praxis": _stamp(extra=1)})
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_bundle(data, {})
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_bundle(data, {"text/html": {}})


@pytest.mark.parametrize("kind, over", [
    ("ledger", {"resource": "assay"}), ("ledger", {"rev": 3}), ("error", {"rev": 3}),
])
def test_check_bundle_enforces_the_null_values_D2_fixes_by_kind(svg, kind, over):
    data, _ = _bundle()
    stamp = _stamp(kind=kind, resource=None, rev=None, **over)
    with pytest.raises(svg.UnsafeHtmlError):
        svg.check_bundle(data, {"praxis": stamp})


def test_stamp_is_json_serialisable_and_roundtrips(svg):
    data, meta = _bundle()
    assert json.loads(json.dumps(meta)) == meta


# --------------------------------------------------------------------------- staging


def test_b1_modules_reach_dist_through_the_manifest_walk():
    """`build_manifest.collect_sources` walks overlay/assets/python recursively, so the three
    B1 modules stage with no build change; assert that rather than assume it."""
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    spec = importlib.util.spec_from_file_location("_bm_under_test_b1", scripts / "build_manifest.py")
    bm = importlib.util.module_from_spec(spec)
    sys.modules["_bm_under_test_b1"] = bm
    spec.loader.exec_module(bm)
    overlay = Path(__file__).resolve().parents[1] / "overlay"
    paths = {e["path"] for e in bm.collect_sources(overlay)}
    for name in ("svg", "floor", "budget"):
        assert f"assets/python/praxis/display/{name}.py" in paths, sorted(paths)
