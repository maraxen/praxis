"""Labware reprs for ``praxis.display`` (task B2; spec D2, D3, D4, D5, D14, sections 3.2 and 3.4).

Plate, tip rack and single-well figures with their name line and summary sentence, well-range
compression, the ``data-praxis-grid`` descriptor, and the D2 mimebundle (``text/html`` +
``text/plain`` + the ``{v, kind, resource, rev, session, exec}`` stamp). Every other ``Container``
(trough, tube, ...) gets the name line and the sentence only, with no drawing (D2).

**Imports.** Plain CPython, and Pyodide: this module imports only the standard library and its
siblings ``svg``, ``floor`` and ``budget`` at import time. The PyLabRobot classes are resolved
INSIDE functions (``_plr``), from ``pylabrobot.resources``, so the module imports with no PLR on
the path and nothing at import time can fail in the browser.

**Dispatch is by CLASS** (D2): ``isinstance`` against ``Plate``, ``TipRack`` and ``Container``, so
an ``EmbeddedTipRack`` (the pin's ``tips_300``) is a tip rack, and no code compares a type-name
string. ``Well`` is checked first among containers because a well is drawn and other containers
are not.

**Emission (D2, D3, D14).** Every element goes through ``svg.el`` / ``svg.path_el`` /
``svg.text_el`` / ``svg.text_line`` and every interpolated string through their escaping
(``svg.esc_text`` / ``svg.esc_attr``); nothing here writes markup by hand and nothing escapes on
its own. Colours are inline presentation attributes in the design's light palette (``COLORS``),
in the upper-case form the theme's attribute selectors match. The resource group carries
``data-praxis-res``, ``data-praxis-grid``, ``role="img"``, ``aria-label`` (= the sentence) and
``tabindex="0"``; the SVG carries ``viewBox``, the D5 inline ``style`` and ``data-praxis-minw``;
a wrapper carries ``overflow-x:auto``. The name line and the sentence are class-only elements, so
they stay meaningful after an untrusted reopen strips the SVG and every other attribute (S2).

**One path per state (D4).** Well outlines, liquid disks, changed marks, fault rings and fault
crosses are one ``<path>`` each (one subpath per well); tips get one path each for present
rings, present cores (an ink dot: a zero-length subpath under a round cap) and taken rings.
There is no ``<circle>`` and no per-well ``<g>``. Liquid area is proportional to volume: ``r_liquid = r * sqrt(clamp(v / max, 0, 1))``. The
liquid subpaths are written with three decimals (``svg.circle_path`` keeps two), because AC-9
requires every liquid radius within 1e-3 mm of that rule.

**Scale (D5).** Single labware is drawn at 3 px/mm; ``s_min = max(0.88 * s_n, 4 / d_min)`` with
``d_min`` the smallest drawn well or tip diameter, from ``floor``. Plates of 384 wells or more
are drawn as square cells and carry column and row labels every ``k``-th (``floor.label_step_k``).
Labels are ``floor.label_font_units(s_n)`` user units.

**Byte cap (D4).** ``render`` runs the ladder through ``budget.enforce``: level 0 the full
figure, level 1 a filled block with no ``data-praxis-grid``, level 2 the name line, the sentence
and ``budget.OMISSION_SENTENCE``. Names are shortened to ``NAME_DISPLAY_MAX`` characters wherever
they are DISPLAYED, so the text of level 2 is always small enough to fit; the stamp keeps the
full name.

Public API: ``kind_of``, ``compress_wells``, ``where_label``, ``plate_sentence``,
``tiprack_sentence``, ``container_sentence``, ``sentence``, ``name_line``, ``render_figure``,
``render_html``, ``stamp`` and ``render``. ``volume_of(container) -> float`` (default
``container.tracker.get_used_volume()``, which includes pending state) lets a caller draw
another volume, for example the committed ``tracker.volume`` an error panel draws (D8). In the
same way ``tip_of(spot) -> Tip | None`` (default ``spot.tip``, the resource tree, which includes
pending operations) lets a caller say which tip a rack spot HOLDS: an error panel passes the
committed tip (#5659, N5659-8). The one hook feeds the drawn rings, the grid's hover values and the
sentence, so the three always agree.
"""

from __future__ import annotations

import json
import math
import re
from decimal import ROUND_HALF_UP, Decimal, localcontext

from . import budget, floor, svg

__all__ = [
    "COLORS", "NAME_DISPLAY_MAX",
    "kind_of", "compress_wells", "where_label",
    "plate_sentence", "tiprack_sentence", "container_sentence", "sentence",
    "name_line", "render_figure", "render_html", "stamp", "render",
]

# The design's light palette (DESIGN.md "Color"). Upper case on purpose: praxis-theme.css maps the
# structural four (sheet, ink, ink soft, rail) by attribute value, case-insensitively.
COLORS = {
    "sheet": "#FFFFFF",
    "ink": "#1D2935",
    "ink_soft": "#56636F",
    "rail": "#C9D2DA",
    "moonstone": "#73A9C2",
    "rose": "#ED7A9B",
    "brick": "#B3402A",
}

NAME_DISPLAY_MAX = 200

_EPS_UL = 1e-6                # a well "holds liquid" above this (PLR's own volume tolerance)
_PLATE_CORNER_MM = 2.0        # the plate outline's corner radius (section 3.2)
_PAD_LABELLED_MM = {"l": 16.0, "t": 14.0, "r": 4.0, "b": 4.0}   # room for row / column labels
_PAD_PLAIN_MM = 2.0           # around a single well and around a block
_CORE_RATIO = 0.45            # present tip: core radius / ring radius (the prototype's 1.5 / 3.3)
_CHANGED_GROW_MM = 0.9        # the changed ring sits this far outside the well (the prototype)
_FAULT_GROW_MM = 1.0
_CROSS_RATIO = 0.55           # fault cross half-size / well radius
_STROKE_PX = {"plate": 1.2, "well": 1.0, "tip_ring": 1.2, "taken": 1.0, "changed": 1.6, "fault": 2.0}
_DASH_PX = 2.0
_FONT_FAMILY = "Roboto Flex, system-ui, sans-serif"

_ID = re.compile(r"([A-Z]{1,2})([0-9]+)")


# --------------------------------------------------------------------------- PLR (lazy)


def _plr():
    """The PLR classes this module dispatches on, resolved when first needed, never at import."""
    from pylabrobot.resources import Container, CrossSectionType, Plate, TipRack, Well

    return Container, CrossSectionType, Plate, TipRack, Well


def kind_of(resource) -> str:
    """The stamp kind of a drawable or describable resource: ``plate``, ``tiprack`` or
    ``container``. Resolved through the PLR classes (an ``EmbeddedTipRack`` is a ``TipRack``);
    ``TypeError`` for anything else."""
    container, _cross, plate, tiprack, _well = _plr()
    if isinstance(resource, plate):
        return "plate"
    if isinstance(resource, tiprack):
        return "tiprack"
    if isinstance(resource, container):
        return "container"
    raise TypeError(f"labware.py renders Plate, TipRack and Container, not {type(resource).__name__}")


def _is_well(resource) -> bool:
    return isinstance(resource, _plr()[4])


def _is_drawable(resource) -> bool:
    return kind_of(resource) in ("plate", "tiprack") or _is_well(resource)


# --------------------------------------------------------------------------- identifiers and ranges


def _split_id(ident) -> tuple[int, int]:
    """``"B12"`` -> (row index 1, column number 12). Row labels are PLR's: A..Z, then AA, AB, ..."""
    if not isinstance(ident, str):
        raise TypeError(f"a well id must be str, got {type(ident).__name__}")
    m = _ID.fullmatch(ident)
    if not m or int(m.group(2)) < 1:
        raise ValueError(f"not a well id: {ident!r}")
    label = m.group(1)
    row = ord(label) - 65 if len(label) == 1 else (ord(label[0]) - 64) * 26 + (ord(label[1]) - 65)
    return row, int(m.group(2))


def _row_label(index: int) -> str:
    if index < 26:
        return chr(65 + index)
    return chr(64 + index // 26) + chr(65 + index % 26)


def _cell_name(row: int, col: int) -> str:
    return f"{_row_label(row)}{col}"


def compress_wells(ids) -> str:
    """The compressed range of a set of well ids (section 3.3).

    A block is ``A1:H3``, a partial column ``A1:D1``, a single well ``A1``, and anything else a
    comma list of those (``"A1:B1, D1"``, ``"A1, C3"``). Column runs with the same rows on
    adjacent columns merge into one block. The result is order-insensitive and always expands
    back to exactly the input. ``ValueError`` for an empty set or an id that is not
    ``[A-Z]{1,2}[0-9]+``.
    """
    cells = {_split_id(i) for i in ids}
    if not cells:
        raise ValueError("cannot compress an empty set of wells")
    by_col: dict[int, list[int]] = {}
    for row, col in cells:
        by_col.setdefault(col, []).append(row)
    blocks: list[list[int]] = []          # [col0, col1, row0, row1]
    open_blocks: dict[tuple[int, int], list[int]] = {}
    for col in sorted(by_col):
        rows = sorted(by_col[col])
        runs: list[tuple[int, int]] = []
        start = prev = rows[0]
        for r in rows[1:]:
            if r != prev + 1:
                runs.append((start, prev))
                start = r
            prev = r
        runs.append((start, prev))
        still_open: dict[tuple[int, int], list[int]] = {}
        for run in runs:
            block = open_blocks.get(run)
            if block is not None and block[1] == col - 1:
                block[1] = col
            else:
                block = [col, col, run[0], run[1]]
                blocks.append(block)
            still_open[run] = block
        open_blocks = still_open
    parts = []
    for c0, c1, r0, r1 in sorted(blocks, key=lambda b: (b[0], b[2])):
        first = _cell_name(r0, c0)
        parts.append(first if (c0, r0) == (c1, r1) else f"{first}:{_cell_name(r1, c1)}")
    return ", ".join(parts)


def where_label(name, ids, *, n_rows: int) -> str:
    """Where a run touched: ``"source, column 1"`` for exactly one whole column of an
    ``n_rows``-row plate, otherwise ``"assay A1:H3"`` or a comma list (section 3.3)."""
    cells = {_split_id(i) for i in ids}
    cols = {c for _r, c in cells}
    if len(cols) == 1 and {r for r, _c in cells} == set(range(n_rows)):
        return f"{_disp(name)}, column {next(iter(cols))}"
    return f"{_disp(name)} {compress_wells(ids)}"


# --------------------------------------------------------------------------- sentences


def _disp(name) -> str:
    """A name as DISPLAYED: shortened so that level 2 of the ladder can always fit."""
    s = str(name)
    return s if len(s) <= NAME_DISPLAY_MAX else s[: NAME_DISPLAY_MAX - 1] + "…"


def _default_volume(container) -> float:
    return container.tracker.get_used_volume()


def _amount(x) -> str:
    return svg.fmt_amount(x)


def _finite_positive(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x) and x > 0


def _runs(numbers) -> str:
    """``[1, 2, 3, 5]`` -> ``"1–3, 5"``: runs of two or more with an en dash."""
    nums = sorted(set(numbers))
    out: list[str] = []
    i = 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else f"{nums[i]}–{nums[j]}")
        i = j + 1
    return ", ".join(out)


def plate_sentence(plate, volume_of=None) -> str:
    """Section 3.2: "24 of 96 wells hold liquid, 50–150 µL. 2,400 µL in the plate."; every well
    holding liquid reads "All 96 wells hold liquid, 200 µL each. ..."; an empty plate reads
    "All 96 wells are empty. Each holds up to 360 µL."."""
    volume_of = volume_of or _default_volume
    wells = plate.get_all_items()
    n = len(wells)
    if n == 0:
        return f"{_disp(plate.name)} has no wells."
    vols = [float(volume_of(w)) for w in wells]
    held = [v for v in vols if v > _EPS_UL]
    if not held:
        maxes = [w.max_volume for w in wells if _finite_positive(w.max_volume)]
        tail = ""
        if maxes:
            lo, hi = min(maxes), max(maxes)
            cap = _amount(lo) if _amount(lo) == _amount(hi) else f"{_amount(lo)}–{_amount(hi)}"
            tail = f" Each holds up to {cap} µL."
        return f"All {_amount(n)} wells are empty.{tail}"
    lo, hi = min(held), max(held)
    span = f"{_amount(lo)} µL each" if _amount(lo) == _amount(hi) else f"{_amount(lo)}–{_amount(hi)} µL"
    count = (
        f"All {_amount(n)} wells hold liquid"
        if len(held) == n
        else f"{_amount(len(held))} of {_amount(n)} wells hold liquid"
    )
    return f"{count}, {span}. {_amount(sum(held))} µL in the plate."


def _spot_tip(spot):
    """The default ``tip_of``: the tip the spot holds in the resource tree (D7), pending included."""
    return spot.tip


def tiprack_sentence(rack, tip_of=None) -> str:
    """Section 3.2: "72 of 96 tips left. Columns 1–3 used." A column is used when any of its
    spots has lost its tip; presence is ``tip_of(spot)`` (default: the tip the spot holds in the
    resource tree, D7)."""
    tip_of = tip_of or _spot_tip
    spots = rack.get_all_items()
    ids = _identifiers(rack)
    present = [tip_of(s) is not None for s in spots]
    left = sum(present)
    text = f"{_amount(left)} of {_amount(len(spots))} tips left."
    used = sorted({_split_id(i)[1] for i, here in zip(ids, present, strict=True) if not here})
    if used:
        word = "Column" if len(used) == 1 else "Columns"
        text += f" {word} {_runs(used)} used."
    return text


def _container_label(container) -> str:
    plate_cls = _plr()[2]
    if _is_well(container) and isinstance(container.parent, plate_cls):
        return f"{_disp(container.parent.name)} {container.get_identifier()}"
    return _disp(container.name)


def container_sentence(container, volume_of=None) -> str:
    """Section 3.2: "assay A1 holds 50 µL of 360 µL." for a well (the plate's name and the
    well's id), "{name} holds {v} µL of {max} µL." for any other container, and "{name} holds
    {v} µL." when ``max_volume`` is not finite."""
    volume_of = volume_of or _default_volume
    held = _amount(volume_of(container))
    label = _container_label(container)
    if _finite_positive(container.max_volume):
        return f"{label} holds {held} µL of {_amount(container.max_volume)} µL."
    return f"{label} holds {held} µL."


def sentence(resource, volume_of=None, tip_of=None) -> str:
    """The summary sentence of *resource*: its ``text/plain`` and its drawing's ``aria-label``."""
    kind = kind_of(resource)
    if kind == "plate":
        return plate_sentence(resource, volume_of)
    if kind == "tiprack":
        return tiprack_sentence(resource, tip_of)
    return container_sentence(resource, volume_of)


# --------------------------------------------------------------------------- geometry


def _identifiers(res) -> list[str]:
    """Item ids in PLR's order (column-major: A1, B1, ..., A2, ...), aligned with
    ``get_all_items()``."""
    ordering = getattr(res, "_ordering", None)
    if ordering is not None:
        return list(ordering)
    return [res.get_child_identifier(c) for c in res.get_all_items()]


class _Item:
    __slots__ = ("ident", "row", "col", "cx", "cy", "sx", "sy", "child")

    def __init__(self, ident, row, col, cx, cy, sx, sy, child):
        self.ident, self.row, self.col = ident, row, col
        self.cx, self.cy, self.sx, self.sy = cx, cy, sx, sy
        self.child = child

    @property
    def d(self) -> float:
        return min(self.sx, self.sy)


def _items(res) -> list[_Item]:
    """Wells or tip spots in the resource's local frame, centres with y measured DOWN from the
    back edge (PLR's y is up from the front edge, and the front edge is drawn at the bottom)."""
    height = res.get_size_y()
    out = []
    for ident, child in zip(_identifiers(res), res.get_all_items(), strict=True):
        loc = child.location
        if loc is None:
            raise ValueError(f"{child.name} has no location in {res.name}")
        sx, sy = child.get_size_x(), child.get_size_y()
        row, col = _split_id(ident)
        out.append(_Item(ident, row, col, loc.x + sx / 2, height - (loc.y + sy / 2), sx, sy, child))
    return out


def _pitches(items: list[_Item]) -> tuple[float, float]:
    """Column pitch dx and row pitch dy from the items themselves (PLR grids are uniform)."""
    dx = dy = None
    by_row: dict[int, list[_Item]] = {}
    by_col: dict[int, list[_Item]] = {}
    for it in items:
        by_row.setdefault(it.row, []).append(it)
        by_col.setdefault(it.col, []).append(it)
    for row_items in by_row.values():
        if len(row_items) > 1:
            a, b = min(row_items, key=lambda i: i.col), max(row_items, key=lambda i: i.col)
            dx = (b.cx - a.cx) / (b.col - a.col)
            break
    for col_items in by_col.values():
        if len(col_items) > 1:
            a, b = min(col_items, key=lambda i: i.row), max(col_items, key=lambda i: i.row)
            dy = (b.cy - a.cy) / (b.row - a.row)
            break
    first = items[0]
    return (dx if dx is not None else first.sx), (dy if dy is not None else first.sy)


def _n3(x) -> str:
    """Three-decimal coordinate for the liquid subpaths (AC-9: radius within 1e-3 mm)."""
    f = float(x)
    if not math.isfinite(f):
        raise ValueError(f"not a finite number: {x!r}")
    with localcontext() as ctx:
        ctx.prec = 60
        d = Decimal(repr(f)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _n3s(*vals) -> str:
    return " ".join(_n3(v) for v in vals).replace(" -", "-")


def _liquid_circle(cx, cy, r) -> str:
    """One circle subpath, same grammar as ``svg.circle_path``, at three decimals."""
    return f"M{_n3s(cx - r, cy)}a{_n3s(r, r, 0, 1, 0, 2 * r, 0)}a{_n3s(r, r, 0, 1, 0, -2 * r, 0)}z"


def _dot_path(cx, cy) -> str:
    """A zero-length subpath: with a round cap and a stroke width it draws a dot."""
    return f"M{svg.num(cx)} {svg.num(cy)}".replace(" -", "-") + "h0"


def _fraction(volume, max_volume) -> float:
    if volume <= _EPS_UL or not _finite_positive(max_volume):
        return 0.0
    return min(1.0, volume / max_volume)


def _validated_marks(ids: list[str], marks, what: str) -> set[str]:
    marks = set(marks)
    unknown = sorted(marks - set(ids))
    if unknown:
        raise ValueError(f"{what} names wells this resource does not have: {unknown[:5]}")
    return marks


def _num_json(v: float):
    v = round(float(v), 1)
    return int(v) if v == int(v) else v


# --------------------------------------------------------------------------- figure pieces


def _sw(kind: str, s_n: float) -> float:
    """A stroke of the design's px width, in user units at the nominal scale."""
    return _STROKE_PX[kind] / s_n


def _grid_attr(desc: dict) -> str:
    return json.dumps(desc, separators=(",", ":"))


def _resource_group(resource_name, sentence_text, inner: str, grid: dict | None) -> str:
    """The resource group: ``data-praxis-res``, the grid descriptor (when drawn in full),
    ``role="img"``, ``aria-label`` (the sentence) and ``tabindex="0"`` (section 3.4)."""
    return svg.el(
        "g",
        inner,
        cls="praxis-res",
        data_praxis_res=str(resource_name),
        data_praxis_grid=_grid_attr(grid) if grid is not None else None,
        role="img",
        aria_label=sentence_text,
        tabindex="0",
    )


def _svg_figure(inner: str, width_mm: float, height_mm: float, s_n: float, s_min_value: float) -> str:
    """The ``<svg>`` (D5 Emission: width at ``s_n``, ``max-width:100%;min-width:W*s_min;height:auto``)
    inside the ``overflow-x:auto`` wrapper."""
    doc = svg.el(
        "svg",
        inner,
        viewBox=f"0 0 {svg.num(width_mm)} {svg.num(height_mm)}",
        width=width_mm * s_n,
        height=height_mm * s_n,
        style=floor.svg_style(width_mm, s_min_value),
        data_praxis_minw=floor.min_width_px(width_mm, s_min_value),
        font_family=_FONT_FAMILY,
    )
    return svg.el("div", doc, cls="praxis-fig", style=floor.WRAPPER_STYLE)


def _shape_path(item: _Item, *, circle: bool, grow: float = 0.0, scale: float = 1.0, ox=0.0, oy=0.0) -> str:
    """One well-shaped subpath for *item* (circle or rect), grown by *grow* mm or scaled by
    *scale* about its centre, in figure coordinates (offset by ox, oy)."""
    cx, cy = item.cx + ox, item.cy + oy
    if circle:
        return svg.circle_path(cx, cy, item.d / 2 * scale + grow)
    w, h = item.sx * scale + 2 * grow, item.sy * scale + 2 * grow
    return svg.rect_path(cx - w / 2, cy - h / 2, w, h)


def _mark_paths(items, changed: set[str], fault: set[str], *, circle_of, s_n, ox, oy) -> list[str]:
    """Changed rings (rose), fault rings and fault crosses (brick): one path each (D4). A fault is
    a ring AND a cross, so it never relies on colour alone (D3)."""
    parts: list[str] = []
    rose = [_shape_path(i, circle=circle_of(i), grow=_CHANGED_GROW_MM, ox=ox, oy=oy) for i in items if i.ident in changed]
    if rose:
        parts.append(svg.path_el(
            "".join(rose), cls="sv-changed", fill="none", stroke=COLORS["rose"], stroke_width=_sw("changed", s_n)
        ))
    hit = [i for i in items if i.ident in fault]
    if hit:
        parts.append(svg.path_el(
            "".join(_shape_path(i, circle=circle_of(i), grow=_FAULT_GROW_MM, ox=ox, oy=oy) for i in hit),
            cls="sv-fault", fill="none", stroke=COLORS["brick"], stroke_width=_sw("fault", s_n),
        ))
        parts.append(svg.path_el(
            "".join(svg.cross_path(i.cx + ox, i.cy + oy, _CROSS_RATIO * i.d / 2) for i in hit),
            cls="sv-fault-x", fill="none", stroke=COLORS["brick"], stroke_width=_sw("fault", s_n),
        ))
    return parts


def _labels(items, pad, s_n, k: int) -> list[str]:
    """Column numbers above and row letters left of the grid, every k-th (k = 1 below 384)."""
    fs = floor.label_font_units(s_n)
    col_x: dict[int, float] = {}
    row_y: dict[int, float] = {}
    for it in items:
        col_x.setdefault(it.col, it.cx)
        row_y.setdefault(it.row, it.cy)
    out = []
    for col in sorted(col_x)[::k]:
        out.append(svg.text_el(pad["l"] + col_x[col], pad["t"] - 4, col, fs, anchor="middle", cls="sv-grid", fill=COLORS["ink_soft"]))
    for row in sorted(row_y)[::k]:
        out.append(svg.text_el(pad["l"] - 5, pad["t"] + row_y[row] + 0.35 * fs, _row_label(row), fs, anchor="end", cls="sv-grid", fill=COLORS["ink_soft"]))
    return out


def _grid_descriptor(kind, res_name, items, values, flags, offset, dx, dy) -> dict:
    """Section 3.4: origin, pitch, rows, cols, ids, per-well values and per-well flags. Positions
    are in the figure's user units; (row r, column c) is at ``x0 + (c - 1) * dx``,
    ``y0 + r * dy`` with r counted from A = 0."""
    first = items[0]
    return {
        "v": 1,
        "kind": kind,
        "res": str(res_name),
        "x0": round(first.cx + offset[0] - (first.col - 1) * dx, 2),
        "y0": round(first.cy + offset[1] - first.row * dy, 2),
        "dx": round(dx, 2),
        "dy": round(dy, 2),
        "rows": max(i.row for i in items) + 1,
        "cols": max(i.col for i in items),
        "ids": " ".join(i.ident for i in items),
        "vals": values,
        "flags": "".join(str(f) for f in flags),
    }


def _flags(items, changed: set[str], fault: set[str]) -> list[int]:
    return [(1 if i.ident in changed else 0) + (2 if i.ident in fault else 0) for i in items]


def _block(res, sentence_text, s_n) -> str:
    """Ladder level 1: the labware as one filled block. No wells, no labels, no grid; still a
    resource with its name, sentence, ``aria-label`` and focus target."""
    w, h = res.get_size_x(), res.get_size_y()
    pad = _PAD_PLAIN_MM
    rect = svg.el(
        "rect", "", cls="sv-block", x=pad, y=pad, width=w, height=h, rx=_PLATE_CORNER_MM,
        fill=COLORS["rail"], stroke=COLORS["ink"], stroke_width=_sw("plate", s_n),
    )
    group = _resource_group(res.name, sentence_text, rect, None)
    return _svg_figure(group, w + 2 * pad, h + 2 * pad, s_n, floor.TEXT_FLOOR_RATIO * s_n)


def _labelled_figure(res, items, layers: list[str], grid_desc, sentence_text, s_n, s_min_value, k) -> str:
    pad = _PAD_LABELLED_MM
    w = res.get_size_x() + pad["l"] + pad["r"]
    h = res.get_size_y() + pad["t"] + pad["b"]
    outline = svg.el(
        "rect", "", cls="sv-plate", x=pad["l"], y=pad["t"], width=res.get_size_x(), height=res.get_size_y(),
        rx=_PLATE_CORNER_MM, fill=COLORS["sheet"], stroke=COLORS["ink"], stroke_width=_sw("plate", s_n),
    )
    inner = outline + "".join(layers) + "".join(_labels(items, pad, s_n, k))
    return _svg_figure(_resource_group(res.name, sentence_text, inner, grid_desc), w, h, s_n, s_min_value)


def _label_step(items, n: int, s_min_value: float) -> int:
    if not floor.uses_square_cells(n) or len(items) < 2:
        return 1
    dx, dy = _pitches(items)
    return floor.label_step_k(min(abs(dx), abs(dy)), s_min_value)


def _plate_figure(plate, level, volume_of, changed, fault) -> str:
    _c, cross_section, _p, _t, _w = _plr()
    volume_of = volume_of or _default_volume
    s_n = floor.nominal_scale("labware")
    text = plate_sentence(plate, volume_of)
    if level >= budget.LEVEL_BLOCKS:
        return _block(plate, text, s_n)
    items = _items(plate)
    ids = [i.ident for i in items]
    changed, fault = _validated_marks(ids, changed, "changed"), _validated_marks(ids, fault, "fault")
    pad = _PAD_LABELLED_MM
    ox, oy = pad["l"], pad["t"]
    square = floor.uses_square_cells(len(items))

    def circle_of(i):
        return (not square) and i.child.cross_section_type == cross_section.CIRCLE

    d_min = min((i.d for i in items), default=None)
    s_min_value = floor.s_min_labware(s_n, d_min) if d_min else floor.TEXT_FLOOR_RATIO * s_n
    vols = [float(volume_of(i.child)) for i in items]
    layers: list[str] = []
    if items:
        layers.append(svg.path_el(
            "".join(_shape_path(i, circle=circle_of(i), ox=ox, oy=oy) for i in items),
            cls="sv-well", fill=COLORS["sheet"], stroke=COLORS["rail"], stroke_width=_sw("well", s_n),
        ))
    liquid = []
    for i, v in zip(items, vols, strict=True):
        f = _fraction(v, i.child.max_volume)
        if f <= 0:
            continue
        if circle_of(i):
            liquid.append(_liquid_circle(i.cx + ox, i.cy + oy, i.d / 2 * math.sqrt(f)))
        else:
            liquid.append(_shape_path(i, circle=False, scale=math.sqrt(f), ox=ox, oy=oy))
    if liquid:
        layers.append(svg.path_el("".join(liquid), cls="sv-liquid", fill=COLORS["moonstone"]))
    layers += _mark_paths(items, changed, fault, circle_of=circle_of, s_n=s_n, ox=ox, oy=oy)
    grid = None
    if items:
        dx, dy = _pitches(items)
        grid = _grid_descriptor("volume", plate.name, items, [_num_json(v) for v in vols], _flags(items, changed, fault), (ox, oy), dx, dy)
    return _labelled_figure(plate, items, layers, grid, text, s_n, s_min_value, _label_step(items, len(items), s_min_value))


def _tiprack_figure(rack, level, changed, fault, tip_of=None) -> str:
    tip_of = tip_of or _spot_tip
    s_n = floor.nominal_scale("labware")
    text = tiprack_sentence(rack, tip_of)
    if level >= budget.LEVEL_BLOCKS:
        return _block(rack, text, s_n)
    items = _items(rack)
    ids = [i.ident for i in items]
    changed, fault = _validated_marks(ids, changed, "changed"), _validated_marks(ids, fault, "fault")
    pad = _PAD_LABELLED_MM
    ox, oy = pad["l"], pad["t"]
    d_min = min((i.d for i in items), default=None)
    s_min_value = floor.s_min_labware(s_n, d_min) if d_min else floor.TEXT_FLOOR_RATIO * s_n
    held = [tip_of(i.child) is not None for i in items]
    present = [i for i, here in zip(items, held, strict=True) if here]
    taken = [i for i, here in zip(items, held, strict=True) if not here]
    layers: list[str] = []
    if present:
        layers.append(svg.path_el(
            "".join(_shape_path(i, circle=True, ox=ox, oy=oy) for i in present),
            cls="sv-tip-ring", fill=COLORS["sheet"], stroke=COLORS["ink"], stroke_width=_sw("tip_ring", s_n),
        ))
        # The core is an ink dot: a zero-length subpath under a round cap whose stroke width is the
        # core's diameter. A circle subpath is ~58 bytes, this is ~14, and it is what keeps a
        # 96-tip rack inside its D4 target (12 KiB; drawn as circles it is 13,051 bytes).
        core_width = _CORE_RATIO * min(i.d for i in present)
        layers.append(svg.path_el(
            "".join(_dot_path(i.cx + ox, i.cy + oy) for i in present),
            cls="sv-tip", fill="none", stroke=COLORS["ink"], stroke_width=core_width, stroke_linecap="round",
        ))
    if taken:
        dash = svg.num(_DASH_PX / s_n)
        layers.append(svg.path_el(
            "".join(_shape_path(i, circle=True, ox=ox, oy=oy) for i in taken),
            cls="sv-tip-gone", fill="none", stroke=COLORS["rail"], stroke_width=_sw("taken", s_n),
            stroke_dasharray=f"{dash} {dash}",
        ))
    layers += _mark_paths(items, changed, fault, circle_of=lambda _i: True, s_n=s_n, ox=ox, oy=oy)
    grid = None
    if items:
        dx, dy = _pitches(items)
        vals = [1 if here else 0 for here in held]
        grid = _grid_descriptor("tip", rack.name, items, vals, _flags(items, changed, fault), (ox, oy), dx, dy)
    return _labelled_figure(rack, items, layers, grid, text, s_n, s_min_value, _label_step(items, len(items), s_min_value))


def _well_figure(well, volume_of, changed, fault) -> str:
    """One well, top view, at 3 px/mm with no labels. A well is small, so ladder levels 0 and 1
    draw the same figure (it can never be what puts an output over the cap)."""
    _c, cross_section, plate_cls, _t, _w = _plr()
    volume_of = volume_of or _default_volume
    s_n = floor.nominal_scale("labware")
    text = container_sentence(well, volume_of)
    sx, sy = well.get_size_x(), well.get_size_y()
    ident = well.get_identifier() if isinstance(well.parent, plate_cls) else "A1"
    pad = _PAD_PLAIN_MM
    item = _Item(ident, 0, 1, sx / 2, sy / 2, sx, sy, well)
    changed, fault = _validated_marks([ident], changed, "changed"), _validated_marks([ident], fault, "fault")
    circle = well.cross_section_type == cross_section.CIRCLE
    v = float(volume_of(well))
    layers = [svg.path_el(
        _shape_path(item, circle=circle, ox=pad, oy=pad),
        cls="sv-well", fill=COLORS["sheet"], stroke=COLORS["ink"], stroke_width=_sw("well", s_n),
    )]
    f = _fraction(v, well.max_volume)
    if f > 0:
        d = (
            _liquid_circle(item.cx + pad, item.cy + pad, item.d / 2 * math.sqrt(f))
            if circle
            else _shape_path(item, circle=False, scale=math.sqrt(f), ox=pad, oy=pad)
        )
        layers.append(svg.path_el(d, cls="sv-liquid", fill=COLORS["moonstone"]))
    layers += _mark_paths([item], changed, fault, circle_of=lambda _i: circle, s_n=s_n, ox=pad, oy=pad)
    grid = _grid_descriptor("volume", well.name, [item], [_num_json(v)], _flags([item], changed, fault), (pad, pad), sx, sy)
    s_min_value = floor.s_min_labware(s_n, item.d)
    return _svg_figure(_resource_group(well.name, text, "".join(layers), grid), sx + 2 * pad, sy + 2 * pad, s_n, s_min_value)


# --------------------------------------------------------------------------- public rendering


def _check_level(level) -> int:
    if isinstance(level, bool) or level not in budget.LEVELS:
        raise ValueError(f"level must be one of {budget.LEVELS}, got {level!r}")
    return level


def render_figure(resource, *, level=budget.LEVEL_FULL, volume_of=None, changed=(), fault=(), tip_of=None) -> str:
    """The drawing of *resource* inside its ``overflow-x:auto`` wrapper; ``""`` for a container
    that is not a ``Well`` (those get no drawing, D2), and at ladder level 2 (drawing omitted).

    ``changed`` and ``fault`` are well (or tip spot) ids to mark in rose and in brick with a
    cross; an id the resource does not have is a ``ValueError``. ``tip_of(spot)`` says which tip a
    tip-rack spot holds (default ``spot.tip``); a plate ignores it.
    """
    _check_level(level)
    kind = kind_of(resource)
    if level >= budget.LEVEL_OMITTED:
        return ""
    if kind == "plate":
        return _plate_figure(resource, level, volume_of, changed, fault)
    if kind == "tiprack":
        return _tiprack_figure(resource, level, changed, fault, tip_of)
    if _is_well(resource):
        return _well_figure(resource, volume_of, changed, fault)
    return ""


def name_line(resource) -> str:
    """Section 3.2 item 1: the name, the PLR type and the model, each in its own class-only span
    (two spaces between, so the text reads the same with no CSS at all)."""
    parts = [
        svg.text_line("span", "praxis-name__title", _disp(resource.name)),
        svg.text_line("span", "praxis-name__type", type(resource).__name__),
    ]
    if resource.model:
        parts.append(svg.text_line("span", "praxis-name__model", _disp(resource.model)))
    return svg.el("p", "  ".join(parts), cls="praxis-name")


def render_html(resource, *, level=budget.LEVEL_FULL, volume_of=None, changed=(), fault=(), tip_of=None) -> str:
    """The whole ``text/html`` of one output at one ladder level: name line, drawing (levels 0
    and 1), the sentence, and at level 2 the omission sentence."""
    _check_level(level)
    kind = kind_of(resource)
    text = sentence(resource, volume_of, tip_of)
    drawn = _is_drawable(resource)
    parts = [name_line(resource)]
    if drawn and level < budget.LEVEL_OMITTED:
        parts.append(render_figure(
            resource, level=level, volume_of=volume_of, changed=changed, fault=fault, tip_of=tip_of
        ))
        parts.append(svg.text_line("p", "praxis-summary", text))
    else:
        parts.append(svg.text_line("p", "praxis-summary", text))
        if drawn:
            parts.append(svg.text_line("p", "praxis-omitted", budget.OMISSION_SENTENCE))
    return svg.el("div", "".join(parts), cls=f"praxis-out praxis-{kind}")


def stamp(kind: str, resource_name, rev, session, exec_count) -> dict:
    """The D2 stamp: ``{v, kind, resource, rev, session, exec}``. JSON, so no sanitizer strips it."""
    return {
        "v": 1,
        "kind": kind,
        "resource": None if resource_name is None else str(resource_name),
        "rev": rev,
        "session": session,
        "exec": exec_count,
    }


def render(resource, *, rev, session, exec_count, volume_of=None, changed=(), fault=(), tip_of=None):
    """One mimebundle ``(data, metadata)`` for a Plate, TipRack or Container (D2).

    ``rev``, ``session`` and ``exec_count`` are injected (the display session id and the revision
    come from ``stale.py``, the execution count from the shell). ``data`` holds exactly
    ``text/html`` and ``text/plain`` (the sentence); ``metadata`` is ``{"praxis": stamp}``. The
    HTML is held to the 64 KiB cap by the degradation ladder, and the bundle is validated with
    ``svg.check_bundle`` (an empty session id, for example, raises ``svg.UnsafeHtmlError``).
    """
    kind = kind_of(resource)
    levels = budget.LEVELS if _is_drawable(resource) else (budget.LEVEL_FULL,)
    doc, _level = budget.enforce(
        lambda lv: render_html(
            resource, level=lv, volume_of=volume_of, changed=changed, fault=fault, tip_of=tip_of
        ), levels
    )
    data = {"text/html": doc, "text/plain": sentence(resource, volume_of, tip_of)}
    metadata = {"praxis": stamp(kind, resource.name, rev, session, exec_count)}
    svg.check_bundle(data, metadata)
    return data, metadata
