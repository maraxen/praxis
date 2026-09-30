"""Browserless tests for ``praxis/display/floor.py`` (task B1, backlog #5632): the pure math
of the D5 detail floor. Closes the pure half of AC-12; B3's ``test_display_deck.py`` adds the
real PLR definitions and the rendered-text checks.

Spec: ``260929_notebook-display-epic.md`` D5. Invariants: rendered text is never below 11 px
and rendered wells never below 4 px across, laid out against a design content width of 880 px.
Labels are drawn at ``12.5 / s_n`` user units, so a text floor of 11 px needs
``s_min >= 0.88 * s_n`` for EVERY figure.

Geometry below uses STAND-IN numbers named in each case (a Cor 96 well is 6.86 mm, a 384-well
pitch is 4.5 mm, ...): B1 has no PLR import by spec, so nothing here is read from a resource.

The module is loaded by path under a synthetic name; ``web-repl/overlay/assets/python`` is never
put on ``sys.path`` (ADR 260817 Sec 2.4; ``test_rid_invariant.py``).

Controls: every property check is also run against a deliberately broken ``s_min`` (a 0.85 text
factor; a missing well term) and must fail there, so a check that can only pass is caught.
"""

from __future__ import annotations

import ast
import importlib.util
import itertools
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_FLOOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "overlay" / "assets" / "python" / "praxis" / "display" / "floor.py"
)
_PKG = "_praxis_display_floor_under_test"

EPS = 1e-9

# Stand-in geometry (mm). NOT read from PLR; see the module docstring.
COR96_WELL_D = 6.86        # design fixture plate well diameter (D5 worked check)
COR96_PITCH = 9.0
COR96_WIDTH = 127.76
PLATE384_WELL_D = 3.6      # "about 3.6 mm" (D5 worked check)
PLATE384_PITCH = 4.5
PLATE1536_WELL_D = 1.7     # stand-in for a 1536 well; pitch is the SBS 2.25 mm
PLATE1536_PITCH = 2.25
TIP_D = 7.2                # tips_300 at the pin (D5 worked check)
STARLET_WIDTH = 1005.0     # STARLetDeck size_x (D5 worked check)


@pytest.fixture(scope="module")
def floor():
    if _PKG in sys.modules:
        return sys.modules[_PKG]
    if not _FLOOR_PATH.is_file():
        pytest.fail(f"praxis/display/floor.py does not exist yet: {_FLOOR_PATH}")
    spec = importlib.util.spec_from_file_location(_PKG, _FLOOR_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[_PKG] = module
    spec.loader.exec_module(module)
    return module


def _imports_of(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0] if node.level == 0 else "<relative>")
    return names


def test_module_imports_only_the_standard_library(floor):
    imports = _imports_of(_FLOOR_PATH.read_text())
    assert imports <= set(sys.stdlib_module_names) | {"__future__"}, imports
    assert not (imports & {"js", "pyodide", "IPython", "pylabrobot", "praxis", "<relative>"})


# --------------------------------------------------------------------------- constants


def test_design_constants_are_the_spec_numbers(floor):
    assert floor.DESIGN_WIDTH_PX == 880
    assert floor.LABEL_PX == 12.5
    assert floor.TEXT_FLOOR_PX == 11
    assert floor.WELL_FLOOR_PX == 4
    assert floor.LABEL_MIN_PITCH_PX == 24
    assert floor.LABWARE_NOMINAL_SCALE == 3
    assert floor.DECK_MIN_SCALE == 0.6
    assert tuple(floor.LABEL_STEPS) == (1, 2, 4, 8)
    assert floor.SQUARE_CELL_MIN_WELLS == 384
    assert floor.TEXT_FLOOR_RATIO == pytest.approx(0.88, abs=EPS)
    assert floor.WRAPPER_STYLE == "overflow-x:auto"
    assert floor.DETAIL_FULL != floor.DETAIL_BLOCK


# --------------------------------------------------------------------------- nominal scale


def test_labware_nominal_scale_is_3_and_ignores_width(floor):
    assert floor.nominal_scale("labware") == 3
    assert floor.nominal_scale("labware", 127.76) == 3
    assert floor.nominal_scale("labware", 100000) == 3


@pytest.mark.parametrize("width, expected", [
    (STARLET_WIDTH, 880 / 1005),     # D5 worked check: about 0.876
    (880, 1.0),
    (440, 2.0),                       # narrower than 880 mm: s_n > 1
    (500, 1.76),
    (1466, 880 / 1466),               # just above the clamp boundary
    (880 / 0.6, 0.6),                 # boundary: fitted scale is exactly 0.6
    (2000, 0.6),                      # fitted 0.44 -> clamped
    (10_000, 0.6),
])
def test_deck_nominal_scale_fits_880_px_and_clamps_at_0_6(floor, width, expected):
    assert floor.nominal_scale("deck", width) == pytest.approx(expected, rel=1e-12)


def test_deck_nominal_scale_worked_value_for_starlet(floor):
    assert floor.nominal_scale("deck", STARLET_WIDTH) == pytest.approx(0.876, abs=5e-4)


@pytest.mark.parametrize("bad", [None, 0, -1, float("nan"), float("inf"), "wide"])
def test_deck_nominal_scale_requires_a_positive_finite_width(floor, bad):
    with pytest.raises((ValueError, TypeError)):
        floor.nominal_scale("deck", bad)


def test_nominal_scale_rejects_an_unknown_kind(floor):
    for kind in ("plate", "", None, "DECK"):
        with pytest.raises(ValueError):
            floor.nominal_scale(kind, 1005)


# --------------------------------------------------------------------------- s_min


@pytest.mark.parametrize("d_min, expected", [
    (COR96_WELL_D, 2.64),                # 0.88 * 3 dominates: 4 / 6.86 = 0.58
    (TIP_D, 2.64),
    (PLATE384_WELL_D, 2.64),             # 4 / 3.6 = 1.11
    (PLATE1536_WELL_D, 2.64),            # 4 / 1.7 = 2.35
    (1.5, 4 / 1.5),                      # boundary region: 4/1.5 = 2.667 > 2.64
    (1.0, 4.0),                          # the well term wins, s_min > s_n
    (4 / 2.64, 2.64),                    # exactly at the crossover
])
def test_labware_s_min_is_the_larger_of_the_text_and_well_terms(floor, d_min, expected):
    assert floor.s_min_labware(3, d_min) == pytest.approx(expected, rel=1e-12)


def test_labware_s_min_for_the_fixture_plate_gives_the_worked_min_width(floor):
    s_min = floor.s_min_labware(3, COR96_WELL_D)
    assert s_min == pytest.approx(2.64)
    assert COR96_WIDTH * s_min == pytest.approx(337.29, abs=0.01)


@pytest.mark.parametrize("width, expected", [
    (STARLET_WIDTH, 0.7705),   # D5: about 0.771, not 0.6
    (880, 0.88),
    (500, 0.88 * 1.76),        # narrower deck, s_n > 1 (AC-12)
    (2000, 0.6),               # clamped: s_n = 0.6, s_min = max(0.528, 0.6)
    (1466, 0.6),               # s_n = 0.6002; 0.88 * s_n = 0.528 < 0.6
])
def test_deck_s_min_is_max_of_text_term_and_0_6(floor, width, expected):
    s_n = floor.nominal_scale("deck", width)
    assert floor.s_min_deck(s_n) == pytest.approx(expected, abs=1e-4)


def test_deck_s_min_for_starlet_is_0_771_not_0_6(floor):
    s_n = floor.nominal_scale("deck", STARLET_WIDTH)
    assert floor.s_min_deck(s_n) == pytest.approx(0.771, abs=1e-3)
    assert floor.s_min_deck(s_n) > 0.7


def test_s_min_dispatch_matches_the_two_forms(floor):
    assert floor.s_min("labware", 3, COR96_WELL_D) == floor.s_min_labware(3, COR96_WELL_D)
    assert floor.s_min("deck", 0.876) == floor.s_min_deck(0.876)
    with pytest.raises(ValueError):
        floor.s_min("labware", 3)          # the labware form needs a diameter
    with pytest.raises(ValueError):
        floor.s_min("plate", 3, 6.86)


@pytest.mark.parametrize("args", [(0, 6.86), (-1, 6.86), (3, 0), (3, -1), (float("nan"), 6.86),
                                  (3, float("nan")), (3, float("inf"))])
def test_labware_s_min_rejects_degenerate_input(floor, args):
    with pytest.raises(ValueError):
        floor.s_min_labware(*args)


@pytest.mark.parametrize("s_n", [0, -0.5, float("nan"), float("inf")])
def test_deck_s_min_rejects_degenerate_input(floor, s_n):
    with pytest.raises(ValueError):
        floor.s_min_deck(s_n)


# --------------------------------------------------------------------------- the invariants (AC-12 math)

_S_N = [0.6, 0.65, 0.7, 0.876, 1.0, 1.76, 2.0, 3.0]
_D_MIN = [0.9, 1.0, 1.5, 1.7, 3.6, 6.86, 7.2, 12.0]


def _text_px(font_units: float, scale: float) -> float:
    return font_units * scale


def _all_figures(floor):
    """(label, s_n, s_min, d_min) over labware and deck cases; the decks reuse tip/well sizes."""
    for d in _D_MIN:
        s_n = floor.nominal_scale("labware")
        yield f"labware d={d}", s_n, floor.s_min_labware(s_n, d), d
    for width in (300, 500, 880, STARLET_WIDTH, 1466, 2000, 5000):
        s_n = floor.nominal_scale("deck", width)
        for d in _D_MIN:
            yield f"deck w={width} d={d}", s_n, floor.s_min_deck(s_n), d


def test_text_never_renders_below_11_px_at_s_min_for_every_figure(floor):
    n = 0
    for label, s_n, s_min, _ in _all_figures(floor):
        units = floor.label_font_units(s_n)
        assert _text_px(units, s_min) >= 11 - EPS, label
        assert _text_px(units, s_n) >= 12.5 - EPS, label   # and >= 12.5 px at nominal
        n += 1
    assert n > 40


def test_s_min_is_never_above_s_n_times_anything_absurd_and_never_below_the_text_term(floor):
    for label, s_n, s_min, _ in _all_figures(floor):
        assert s_min >= 0.88 * s_n - EPS, label


def test_wells_drawn_in_full_are_at_least_4_px_at_s_min(floor):
    full = block = 0
    for label, s_n, s_min, d in _all_figures(floor):
        level = floor.detail_level(d, s_min)
        if level == floor.DETAIL_FULL:
            assert d * s_min >= 4 - EPS, label
            full += 1
        else:
            assert level == floor.DETAIL_BLOCK
            assert d * s_min < 4, label
            block += 1
    assert full and block  # both branches exercised


def test_single_labware_is_always_drawn_in_full(floor):
    """s_min_labware includes the 4 / d_min term, so detail_level can never say block for it."""
    for d in _D_MIN:
        s_min = floor.s_min_labware(3, d)
        assert d * s_min >= 4 - EPS
        assert floor.detail_level(d, s_min) == floor.DETAIL_FULL


def test_invariant_checks_are_not_vacuous_a_broken_s_min_is_caught(floor):
    """Controls: rerun the text and well checks against wrong s_min forms; they must fail."""
    def text_ok(s_min_fn):
        return all(
            _text_px(floor.label_font_units(s_n), s_min_fn(s_n, d)) >= 11 - EPS
            for s_n, d in itertools.product(_S_N, _D_MIN)
        )

    def well_ok(s_min_fn):
        return all(d * s_min_fn(s_n, d) >= 4 - EPS for s_n, d in itertools.product(_S_N, _D_MIN))

    good = lambda s_n, d: max(0.88 * s_n, 4 / d)                 # noqa: E731
    text_factor_085 = lambda s_n, d: max(0.85 * s_n, 4 / d)      # noqa: E731
    no_well_term = lambda s_n, d: 0.88 * s_n                     # noqa: E731
    assert text_ok(good) and well_ok(good)                        # positive control
    assert not text_ok(text_factor_085)                           # negative controls
    assert not well_ok(no_well_term)


def test_module_s_min_matches_the_reference_formula(floor):
    for s_n, d in itertools.product(_S_N, _D_MIN):
        assert floor.s_min_labware(s_n, d) == pytest.approx(max(0.88 * s_n, 4 / d), rel=1e-12)
        assert floor.s_min_deck(s_n) == pytest.approx(max(0.88 * s_n, 0.6), rel=1e-12)


# --------------------------------------------------------------------------- labels


@pytest.mark.parametrize("s_n", [0.6, 0.876, 3.0, 12.5 / 4.16])
def test_label_font_units_is_12_5_over_s_n_rounded_up_to_two_decimals(floor, s_n):
    u = floor.label_font_units(s_n)
    assert 12.5 / s_n - EPS <= u < 12.5 / s_n + 0.0101
    assert round(u, 2) == pytest.approx(u, abs=1e-12)


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf")])
def test_label_font_units_rejects_degenerate_scale(floor, bad):
    with pytest.raises(ValueError):
        floor.label_font_units(bad)


def test_rendered_px_helper_is_units_times_scale(floor):
    assert floor.rendered_px(4.17, 2.64) == pytest.approx(4.17 * 2.64)


@pytest.mark.parametrize("pitch, s_min, k", [
    (PLATE384_PITCH, 2.64, 4),      # k=2 gives 23.76 < 24, k=4 gives 47.52
    (PLATE1536_PITCH, 2.64, 8),     # k=4 gives 23.76 < 24, k=8 gives 47.52
    (COR96_PITCH, 2.64, 2),         # pure math: 23.76 < 24. Callers apply k only for >= 384 wells.
    (8.0, 3.0, 1),                  # exactly 24.0 passes (>=)
    (7.99, 3.0, 2),                 # 23.97 fails, 47.94 passes
    (12.0, 2.0, 1),                 # exactly 24
    (PLATE384_PITCH, 5.0, 2),       # 22.5 fails, 45 passes
    (0.5, 2.64, 8),                 # saturates at the largest step
    (1.0, 100.0, 1),
])
def test_label_step_k_is_the_smallest_step_giving_24_px(floor, pitch, s_min, k):
    assert floor.label_step_k(pitch, s_min) == k


def test_label_step_k_is_always_a_listed_step_and_monotone_in_pitch(floor):
    prev = None
    for pitch in [0.5 + 0.25 * i for i in range(60)]:
        k = floor.label_step_k(pitch, 2.64)
        assert k in (1, 2, 4, 8)
        if prev is not None:
            assert k <= prev   # a wider pitch never needs a larger step
        prev = k


def test_label_step_k_labels_never_collide_unless_saturated(floor):
    for pitch, s_min in itertools.product([1.0, 2.25, 4.5, 9.0], [0.7, 2.64, 4.0]):
        k = floor.label_step_k(pitch, s_min)
        assert k * pitch * s_min >= 24 - EPS or k == 8
        smaller = [c for c in (1, 2, 4, 8) if c < k]
        assert all(c * pitch * s_min < 24 for c in smaller)   # smallest such k


@pytest.mark.parametrize("args", [(0, 2.64), (-1, 2.64), (4.5, 0), (4.5, float("nan")),
                                  (float("inf"), 2.64)])
def test_label_step_k_rejects_degenerate_input(floor, args):
    with pytest.raises(ValueError):
        floor.label_step_k(*args)


@pytest.mark.parametrize("n, expected", [(1, False), (96, False), (383, False), (384, True),
                                         (1536, True), (10_000, True)])
def test_plates_of_384_wells_or_more_use_square_cells(floor, n, expected):
    assert floor.uses_square_cells(n) is expected


# --------------------------------------------------------------------------- detail level


@pytest.mark.parametrize("d_min, s_min, expected", [
    (COR96_WELL_D, 0.7705, "full"),         # D5: 6.86 -> 5.3 px on the STARLet deck
    (TIP_D, 0.7705, "full"),                # 5.55 px
    (PLATE384_WELL_D, 0.7705, "block"),     # 2.8 px
    (PLATE1536_WELL_D, 0.7705, "block"),
    (4.0, 1.0, "full"),                     # exactly 4 px: full
    (3.999, 1.0, "block"),
    (5.0, 0.8, "full"),                     # 4.0
])
def test_detail_level_is_full_iff_the_smallest_well_is_4_px_across(floor, d_min, s_min, expected):
    level = floor.detail_level(d_min, s_min)
    assert level == (floor.DETAIL_FULL if expected == "full" else floor.DETAIL_BLOCK)


def test_detail_level_accepts_an_object_carrying_d_min(floor):
    lw = SimpleNamespace(d_min=COR96_WELL_D)
    assert floor.detail_level(lw, 0.7705) == floor.DETAIL_FULL
    assert floor.detail_level(SimpleNamespace(d_min=PLATE384_WELL_D), 0.7705) == floor.DETAIL_BLOCK


@pytest.mark.parametrize("labware, s_min", [(0, 1), (-1, 1), (None, 1), (object(), 1), ("x", 1),
                                            (SimpleNamespace(), 1), (5, 0), (5, float("nan")),
                                            (float("nan"), 1)])
def test_detail_level_rejects_degenerate_input(floor, labware, s_min):
    with pytest.raises((ValueError, TypeError)):
        floor.detail_level(labware, s_min)


def test_the_d5_deck_worked_checks_hold_end_to_end(floor):
    s_min = floor.s_min_deck(floor.nominal_scale("deck", STARLET_WIDTH))
    assert floor.detail_level(PLATE384_WELL_D, s_min) == floor.DETAIL_BLOCK
    assert floor.detail_level(COR96_WELL_D, s_min) == floor.DETAIL_FULL
    assert floor.detail_level(TIP_D, s_min) == floor.DETAIL_FULL


# --------------------------------------------------------------------------- emission


def test_min_width_is_width_times_s_min_rounded_up(floor):
    assert floor.min_width_px(STARLET_WIDTH, 0.7705) == pytest.approx(774.4, abs=0.6)   # "about 775"
    assert floor.min_width_px(COR96_WIDTH, 2.64) >= COR96_WIDTH * 2.64 - EPS
    assert floor.min_width_px(COR96_WIDTH, 2.64) - COR96_WIDTH * 2.64 < 0.0101


def test_svg_style_is_the_exact_d5_string(floor):
    assert floor.svg_style(COR96_WIDTH, 2.64) == "max-width:100%;min-width:337.29px;height:auto"
    assert floor.svg_style(100, 0.6) == "max-width:100%;min-width:60px;height:auto"


def test_deck_scroll_flag_follows_min_width_against_the_880_design_width(floor):
    s_min = floor.s_min_deck(floor.nominal_scale("deck", STARLET_WIDTH))
    assert floor.scrolls_at_design_width(STARLET_WIDTH, s_min) is False   # 775 < 880
    # fitted scale below 0.6 (AC-12): emitted at 0.6 and scrolls
    assert floor.nominal_scale("deck", 2000) == 0.6
    assert floor.scrolls_at_design_width(2000, floor.s_min_deck(0.6)) is True   # 1200 > 880
    # a narrow deck fits and does not scroll
    assert floor.scrolls_at_design_width(500, floor.s_min_deck(1.76)) is False


@pytest.mark.parametrize("args", [(0, 1), (-1, 1), (100, 0), (100, float("nan"))])
def test_emission_helpers_reject_degenerate_input(floor, args):
    with pytest.raises(ValueError):
        floor.min_width_px(*args)
    with pytest.raises(ValueError):
        floor.svg_style(*args)
    with pytest.raises(ValueError):
        floor.scrolls_at_design_width(*args)


def test_results_are_deterministic(floor):
    a = [floor.s_min_deck(floor.nominal_scale("deck", w)) for w in (500, 1005, 2000)]
    b = [floor.s_min_deck(floor.nominal_scale("deck", w)) for w in (500, 1005, 2000)]
    assert a == b
    assert math.isfinite(sum(a))


# --------------------------------------------------------------------------- staging


def test_floor_module_reaches_the_dist_manifest_walk():
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    spec = importlib.util.spec_from_file_location("_bm_under_test_floor", scripts / "build_manifest.py")
    bm = importlib.util.module_from_spec(spec)
    sys.modules["_bm_under_test_floor"] = bm
    spec.loader.exec_module(bm)
    overlay = Path(__file__).resolve().parents[1] / "overlay"
    assert "assets/python/praxis/display/floor.py" in {e["path"] for e in bm.collect_sources(overlay)}
