"""The D5 detail floor as pure math (task B1; spec D5, AC-12).

Pure standard library: no PyLabRobot, no IPython, no ``js``, no other Praxis module.

Invariants: rendered text is never below **11 px** and rendered wells never below **4 px**
across. Python cannot measure the browser, so every figure is laid out against a design content
width of **880 px**:

* ``s_n`` is the nominal scale in px/mm: 3 for a single labware figure; for the deck, fit to
  880 px and clamped to >= 0.6.
* Labels are drawn at ``12.5 / s_n`` user units (mm), i.e. 12.5 px at ``s_n``. At ``s_min`` a
  label renders at ``12.5 * s_min / s_n`` px, so the text floor needs ``s_min >= 0.88 * s_n``
  for EVERY figure.
* ``s_min`` is the smallest scale the figure may be rendered at (below it the figure scrolls
  horizontally instead of shrinking): for single labware ``max(0.88 * s_n, 4 / d_min)``, for the
  deck ``max(0.88 * s_n, 0.6)``.

``label_font_units`` and ``min_width_px`` round UP to two decimals, so rounding can never take a
figure below the floor it was computed for.
"""

from __future__ import annotations

import math
from decimal import ROUND_CEILING, Decimal, localcontext

__all__ = [
    "DESIGN_WIDTH_PX", "LABEL_PX", "TEXT_FLOOR_PX", "WELL_FLOOR_PX", "LABEL_MIN_PITCH_PX",
    "LABWARE_NOMINAL_SCALE", "DECK_MIN_SCALE", "TEXT_FLOOR_RATIO", "LABEL_STEPS",
    "SQUARE_CELL_MIN_WELLS", "WRAPPER_STYLE", "DETAIL_FULL", "DETAIL_BLOCK",
    "nominal_scale", "s_min_labware", "s_min_deck", "s_min", "label_font_units", "rendered_px",
    "label_step_k", "uses_square_cells", "detail_level", "min_width_px", "svg_style",
    "scrolls_at_design_width",
]

DESIGN_WIDTH_PX = 880.0            # DESIGN.md: content max 880 px
LABEL_PX = 12.5                    # labels render at this size at s_n
TEXT_FLOOR_PX = 11.0               # rendered text never below this
WELL_FLOOR_PX = 4.0                # rendered wells never below this across
LABEL_MIN_PITCH_PX = 24.0          # labelled columns/rows at least this far apart
LABWARE_NOMINAL_SCALE = 3.0        # px/mm for a single labware figure
DECK_MIN_SCALE = 0.6               # px/mm floor for the deck
TEXT_FLOOR_RATIO = TEXT_FLOOR_PX / LABEL_PX   # 0.88
LABEL_STEPS = (1, 2, 4, 8)
SQUARE_CELL_MIN_WELLS = 384        # plates of this many wells or more are square cells
WRAPPER_STYLE = "overflow-x:auto"  # inline style of the wrapper around the svg (D5 Emission)

DETAIL_FULL = "full"
DETAIL_BLOCK = "block"

_EPS = 1e-9


def _pos(name: str, v) -> float:
    if isinstance(v, bool):
        raise TypeError(f"{name} must be a number, not bool")
    f = float(v)  # str/None raise ValueError/TypeError here
    if not math.isfinite(f) or f <= 0:
        raise ValueError(f"{name} must be a positive finite number, got {v!r}")
    return f


def _ceil2(x: float) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 60
        return Decimal(repr(float(x))).quantize(Decimal("0.01"), rounding=ROUND_CEILING)


def _plain(d: Decimal) -> str:
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def nominal_scale(kind: str, width_mm=None) -> float:
    """``s_n`` in px/mm. ``"labware"``: 3 (width ignored). ``"deck"``: ``880 / width_mm``
    clamped to >= 0.6 (a deck narrower than 880 mm therefore has ``s_n > 1``)."""
    if kind == "labware":
        return LABWARE_NOMINAL_SCALE
    if kind == "deck":
        return max(DESIGN_WIDTH_PX / _pos("width_mm", width_mm), DECK_MIN_SCALE)
    raise ValueError(f"kind must be 'labware' or 'deck', got {kind!r}")


def s_min_labware(s_n, d_min_mm) -> float:
    """Single-labware ``s_min = max(0.88 * s_n, 4 / d_min)``; ``d_min_mm`` is the smallest
    drawn well or tip diameter in mm."""
    return max(TEXT_FLOOR_RATIO * _pos("s_n", s_n), WELL_FLOOR_PX / _pos("d_min_mm", d_min_mm))


def s_min_deck(s_n) -> float:
    """Deck ``s_min = max(0.88 * s_n, 0.6)``."""
    return max(TEXT_FLOOR_RATIO * _pos("s_n", s_n), DECK_MIN_SCALE)


def s_min(kind: str, s_n, d_min_mm=None) -> float:
    """Dispatch to the labware form (needs ``d_min_mm``) or the deck form."""
    if kind == "labware":
        if d_min_mm is None:
            raise ValueError("the labware form of s_min needs d_min_mm")
        return s_min_labware(s_n, d_min_mm)
    if kind == "deck":
        return s_min_deck(s_n)
    raise ValueError(f"kind must be 'labware' or 'deck', got {kind!r}")


def label_font_units(s_n) -> float:
    """Label font size in user units (mm): ``12.5 / s_n``, rounded UP to two decimals."""
    return float(_ceil2(LABEL_PX / _pos("s_n", s_n)))


def rendered_px(font_units, scale) -> float:
    """Rendered size in px of a length in user units at *scale* px/mm."""
    return _pos("font_units", font_units) * _pos("scale", scale)


def label_step_k(pitch_mm, s_min) -> int:
    """Smallest ``k`` in {1, 2, 4, 8} with ``k * pitch_mm * s_min >= 24`` px, so labels never
    collide; 8 if even that is not enough. Pure math: callers apply it only to plates of
    ``SQUARE_CELL_MIN_WELLS`` wells or more (D5)."""
    pitch, smin = _pos("pitch_mm", pitch_mm), _pos("s_min", s_min)
    for k in LABEL_STEPS:
        if k * pitch * smin >= LABEL_MIN_PITCH_PX - _EPS:
            return k
    return LABEL_STEPS[-1]


def uses_square_cells(n_wells: int) -> bool:
    """Plates of 384 wells or more are drawn as square cells."""
    return n_wells >= SQUARE_CELL_MIN_WELLS


def detail_level(labware, s_min) -> str:
    """``DETAIL_FULL`` if ``d_min * s_min >= 4`` px, else ``DETAIL_BLOCK`` (drawn as a filled
    block, with its summary in the deck's sentence).

    *labware* is the smallest drawn well or tip diameter in mm, either as a bare number or as
    any object with a ``d_min`` attribute.
    """
    d_min = labware.d_min if hasattr(labware, "d_min") else labware
    d, smin = _pos("d_min", d_min), _pos("s_min", s_min)
    return DETAIL_FULL if d * smin >= WELL_FLOOR_PX - _EPS else DETAIL_BLOCK


def min_width_px(width_mm, s_min) -> float:
    """The figure's ``min-width`` in px: ``W_mm * s_min``, rounded UP to two decimals."""
    return float(_ceil2(_pos("width_mm", width_mm) * _pos("s_min", s_min)))


def svg_style(width_mm, s_min) -> str:
    """The SVG's inline style (D5 Emission): ``max-width:100%;min-width:<W*s_min>px;height:auto``."""
    n = _ceil2(_pos("width_mm", width_mm) * _pos("s_min", s_min))
    return f"max-width:100%;min-width:{_plain(n)}px;height:auto"


def scrolls_at_design_width(width_mm, s_min) -> bool:
    """True if the figure's ``min-width`` exceeds the 880 px design content width, so it scrolls
    horizontally even there (a deck fitted below 0.6 px/mm; a narrower notebook scrolls more)."""
    return min_width_px(width_mm, s_min) > DESIGN_WIDTH_PX
