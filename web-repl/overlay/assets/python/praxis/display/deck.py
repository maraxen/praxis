"""Deck repr for ``praxis.display`` (task B3; spec D2, D4, D5, sections 3.2 and 3.4).

The deck plan: a to-scale top view (front edge at the bottom) with a rail ruler along the front
edge, carriers in rail outline with condensed name labels, and labware at its level of detail; the
summary sentence ("Tip carrier on rail 3, plate carrier on rail 9. 3 pieces of labware: tips_300,
source, assay."); and the D2 mimebundle (``text/html`` + ``text/plain`` + the
``{v, kind, resource, rev, session, exec}`` stamp, ``kind == "deck"``).

**Imports.** Plain CPython and Pyodide: only the standard library and the siblings ``svg``,
``floor``, ``budget`` and ``labware`` at import time. PyLabRobot's ``Deck``, ``Carrier``, ``Plate``
and ``TipRack`` are resolved INSIDE functions (``_plr``) from ``pylabrobot.resources``. Dispatch is
by CLASS (``isinstance``), never by a type-name string, so an ``EmbeddedTipRack`` is a tip rack.

**Emission (D2, D3, D14).** Every element goes through ``svg.el`` / ``svg.path_el`` /
``svg.text_el`` / ``svg.text_line`` and every interpolated string through their escaping; nothing
here writes markup by hand. The figure is wrapped by ``labware`` (the ``overflow-x:auto`` wrapper,
the ``<svg>`` with its D5 inline ``style`` and ``data-praxis-minw``). Element classes and colours
are B2's (``sv-plate``, ``sv-well``, ``sv-liquid``, ``sv-tip-ring``, ``sv-tip``, ``sv-tip-gone``,
``sv-block``), plus ``sv-carrier``, ``sv-fixture``, ``sv-rail``, ``sv-ruler``, ``sv-label`` and
``sv-grid`` (the ruler's numbers).

**Scale (D5).** ``W_mm`` is the deck's own width (``get_size_x()``, 1005 for the STARLet).
``s_n = max(880 / W_mm, 0.6)`` and ``s_min = max(0.88 * s_n, 0.6)`` (``floor``); labels are
``12.5 / s_n`` user units, so they render at 11 px or more at ``s_min``. The SVG is emitted at
``W_mm * s_n`` px with ``min-width = W_mm * s_min``: a deck fitted below 0.6 px/mm is emitted at
0.6 and scrolls. A resource that hangs off the left of the deck (the STARLet's 96-head trash) is
clipped by the viewBox rather than widening the figure.

**Detail (D5).** A Plate or TipRack is drawn in full if its smallest well or tip spot,
``d_min * s_min >= 4`` px, otherwise as a filled block (its summary is in the deck sentence). Any
other labware is a block. Full labware carries ``data-praxis-res`` and a ``data-praxis-grid`` in the
FIGURE's user units (so a hit-test needs no per-labware transform); a block carries no grid.

**Byte cap (D4).** ``render`` runs the ladder through ``budget.enforce``: level 0 the plan, level 1
every labware a block with no grid, level 2 the name line, the sentence and
``budget.OMISSION_SENTENCE``. Names are shortened where DISPLAYED; the stamp and
``data-praxis-res`` keep the full name.

**Rails.** At the pin PLR calls rails tracks: the ruler's count is ``deck.num_tracks`` and a
carrier's rail is the track whose ``track_to_location`` x is nearest its own; the deprecated
``num_rails`` is never read. A deck with no tracks (a plain ``Deck``) has no ruler and its carriers
are placed by ``x`` in mm in the sentence.

Public API: ``is_deck``, ``deck_scale``, ``rail_labels``, ``detail_of``, ``sentence``,
``name_line``, ``render_figure``, ``render_html``, ``stamp`` and ``render``.
"""

from __future__ import annotations

import math
import re

from . import budget, floor, labware, svg

__all__ = [
    "is_deck", "deck_scale", "rail_labels", "detail_of", "sentence", "name_line",
    "render_figure", "render_html", "stamp", "render",
]

_COLORS = labware.COLORS
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

_CARRIER_RX_MM = 3.0             # carrier corner radius (the prototype)
_FIXTURE_RX_MM = 2.0
_FIXTURE_MIN_WIDTH_MM = 6.0      # a zero-width fixture (the STARLet's `trash`) still gets a footprint
_FIXTURE_LABEL_MIN_MM = 80.0     # only fixtures at least this deep carry a name label (the prototype)
_LABEL_CHAR_EM = 0.6             # estimated glyph width / font size, for keeping labels inside the figure
# Lengths below are CSS px at the nominal scale, converted to user units (mm) by ``/ s_n``.
_STROKE_PX = {"carrier": 1.0, "fixture": 1.0, "rail": 0.6, "rail_major": 0.8, "ruler": 0.8}
_RULER_GAP_PX = 3.0              # front edge -> ruler baseline
_TICK_PX = (4.0, 8.0)            # minor and major tick lengths
_LABEL_ABOVE_PX = 3.0            # carrier label baseline above the carrier's back edge
_LABWARE_LABEL_ABOVE_PX = 1.5
_LABEL_ROOM_PX = 16.0            # headroom above the topmost resource for its label
_FONT_WEIGHT = "600"
_HALO_PX = 2.0                   # a sheet-coloured halo keeps a label legible over a rail or a neighbour's edge


# --------------------------------------------------------------------------- PLR (lazy)


def _plr():
    """The PLR classes this module dispatches on, resolved when first needed, never at import."""
    from pylabrobot.resources import Carrier, Deck, Plate, TipRack

    return Carrier, Deck, Plate, TipRack


def is_deck(resource) -> bool:
    return isinstance(resource, _plr()[1])


def _require_deck(resource):
    if not is_deck(resource):
        raise TypeError(f"deck.py renders a Deck, not {type(resource).__name__}")
    return resource


# --------------------------------------------------------------------------- what is on the deck


def _loc(deck, res):
    return res.get_location_wrt(deck)


def _carriers(deck) -> list:
    carrier_cls = _plr()[0]
    found = [c for c in deck.children if isinstance(c, carrier_cls)]
    return sorted(found, key=lambda c: (_loc(deck, c).x, c.name))


def _labware(deck) -> list:
    """Every piece of labware, in the order the sentence names it: what sits on each carrier's sites
    (carriers by rail, sites in their own order), then Plates and TipRacks assigned to the deck."""
    _carrier, _deck, plate_cls, tiprack_cls = _plr()
    found = []
    for carrier in _carriers(deck):
        for holder in carrier.children:
            found.extend(holder.children)
    direct = [c for c in deck.children if isinstance(c, (plate_cls, tiprack_cls))]
    found.extend(sorted(direct, key=lambda c: (_loc(deck, c).x, _loc(deck, c).y, c.name)))
    return found


def _fixtures(deck) -> list:
    carrier_cls, _deck, plate_cls, tiprack_cls = _plr()
    return [c for c in deck.children if not isinstance(c, (carrier_cls, plate_cls, tiprack_cls))]


def _track_count(deck):
    n = getattr(deck, "num_tracks", None)
    if isinstance(n, int) and not isinstance(n, bool) and n > 0 and callable(getattr(deck, "track_to_location", None)):
        return n
    return None


def _track_x(deck, track: int) -> float:
    return float(deck.track_to_location(track).x)


def _rail_of(deck, x: float):
    """The track a carrier at *x* sits on (the nearest track start), or ``None`` without tracks or
    when *x* is more than half a track from every one."""
    n = _track_count(deck)
    if n is None:
        return None
    best = min(range(1, n + 1), key=lambda t: abs(_track_x(deck, t) - x))
    pitch = abs(_track_x(deck, 2) - _track_x(deck, 1)) if n > 1 else 22.5
    return best if abs(_track_x(deck, best) - x) <= pitch / 2 else None


def rail_labels(num_tracks: int) -> list[int]:
    """The ruler's numbers: rail 1 and every 5th rail (section 3.2)."""
    if isinstance(num_tracks, bool) or not isinstance(num_tracks, int) or num_tracks < 0:
        raise ValueError(f"num_tracks must be a non-negative int, got {num_tracks!r}")
    return [r for r in range(1, num_tracks + 1) if r == 1 or r % 5 == 0]


# --------------------------------------------------------------------------- scale and detail


def deck_scale(deck) -> tuple[float, float]:
    """``(s_n, s_min)`` in px/mm for *deck* (D5): ``s_n = max(880 / W, 0.6)``, ``s_min = max(0.88 s_n, 0.6)``."""
    s_n = floor.nominal_scale("deck", _require_deck(deck).get_size_x())
    return s_n, floor.s_min_deck(s_n)


def _d_min(res):
    items = labware._items(res)
    return min((i.d for i in items), default=None)


def detail_of(deck, res) -> str:
    """``floor.DETAIL_FULL`` or ``floor.DETAIL_BLOCK`` for one piece of labware on *deck*: full only
    for a Plate or TipRack whose smallest well or tip spot is at least 4 px at the deck's ``s_min``."""
    _c, _d, plate_cls, tiprack_cls = _plr()
    if not isinstance(res, (plate_cls, tiprack_cls)):
        return floor.DETAIL_BLOCK
    d_min = _d_min(res)
    if not d_min:
        return floor.DETAIL_BLOCK
    return floor.detail_level(d_min, deck_scale(deck)[1])


# --------------------------------------------------------------------------- sentence and name line


def _phrase(carrier) -> str:
    """A carrier's kind, from its PLR class: ``TipCarrier`` -> ``tip carrier``."""
    return _CAMEL.sub(" ", type(carrier).__name__).lower()


def _carrier_clause(deck) -> str:
    parts = []
    for i, carrier in enumerate(_carriers(deck)):
        x = _loc(deck, carrier).x
        rail = _rail_of(deck, x)
        where = f"on rail {rail}" if rail is not None else f"at {svg.fmt_amount(x)} mm"
        phrase = _phrase(carrier)
        parts.append(f"{phrase[:1].upper() + phrase[1:] if i == 0 else phrase} {where}")
    return ", ".join(parts) + "." if parts else "No carriers."


def _labware_clause(deck) -> str:
    pieces = _labware(deck)
    if not pieces:
        return "No labware."
    noun = "piece" if len(pieces) == 1 else "pieces"
    names = ", ".join(labware._disp(p.name) for p in pieces)
    return f"{svg.fmt_amount(len(pieces))} {noun} of labware: {names}."


def sentence(deck) -> str:
    """Section 3.2: "Tip carrier on rail 3, plate carrier on rail 9. 3 pieces of labware: tips_300,
    source, assay." Carriers in rail order, phrased from their PLR class; then the labware."""
    _require_deck(deck)
    return f"{_carrier_clause(deck)} {_labware_clause(deck)}"


def name_line(deck) -> str:
    """Section 3.2 item 1: the name, the PLR type and, for a deck with tracks, "N rails" (the
    prototype's; the pin's model string is a mesh name, not something to read)."""
    _require_deck(deck)
    parts = [
        svg.text_line("span", "praxis-name__title", labware._disp(deck.name)),
        svg.text_line("span", "praxis-name__type", type(deck).__name__),
    ]
    n = _track_count(deck)
    if n is not None:
        parts.append(svg.text_line("span", "praxis-name__model", f"{n} rails"))
    return svg.el("p", "  ".join(parts), cls="praxis-name")


# --------------------------------------------------------------------------- figure


class _Frame:
    """The figure's coordinate frame: x is the deck's x in mm; a deck-frame y (up from the front
    edge) maps to ``ytop - y``. ``px`` is one CSS px at the nominal scale, in mm."""

    def __init__(self, deck, s_n: float, ytop: float):
        self.deck, self.s_n, self.ytop, self.px = deck, s_n, ytop, 1.0 / s_n
        self.width = float(deck.get_size_x())
        self.fs = floor.label_font_units(s_n)

    def y(self, y_deck: float) -> float:
        return self.ytop - y_deck

    def rect_y(self, res) -> float:
        return self.ytop - (_loc(self.deck, res).y + res.get_size_y())

    def sw(self, key: str) -> float:
        return _STROKE_PX[key] * self.px


def _label(frame: _Frame, cx: float, y: float, name, *, cls: str, fill: str) -> str:
    """A name label centred on *cx*, moved to stay inside the figure (anchored to a side otherwise), with
    a sheet-coloured halo (``paint-order: stroke``) so it stays legible where it crosses a rail."""
    shown = labware._disp(name)
    half = _LABEL_CHAR_EM * frame.fs * len(shown) / 2
    if cx - half < 0:
        x, anchor = frame.px, "start"
    elif cx + half > frame.width:
        x, anchor = frame.width - frame.px, "end"
    else:
        x, anchor = cx, "middle"
    return svg.text_el(
        x, y, shown, frame.fs, anchor=anchor, cls=cls, fill=fill, font_weight=_FONT_WEIGHT, font_stretch="condensed",
        stroke=_COLORS["sheet"], stroke_width=_HALO_PX * frame.px, stroke_linejoin="round", paint_order="stroke",
    )


def _item_group(name, inner: str, grid: dict | None = None) -> str:
    return svg.el(
        "g", inner, cls="praxis-item", data_praxis_res=str(name),
        data_praxis_grid=labware._grid_attr(grid) if grid is not None else None,
    )


def _rails_and_ruler(frame: _Frame, y_bottom: float, y_top: float) -> list[str]:
    deck = frame.deck
    n = _track_count(deck)
    if n is None:
        return []
    major = set(rail_labels(n))
    xs = {t: _track_x(deck, t) for t in range(1, n + 1)}
    px = frame.px

    def vline(x, ya, yb):
        return f"M{svg.num(x)} {svg.num(ya)}V{svg.num(yb)}"

    out = []
    for cls, stroke, key, pick in (
        ("sv-rail", _COLORS["rail"], "rail", lambda t: t not in major),
        ("sv-rail sv-rail--major", _COLORS["ink_soft"], "rail_major", lambda t: t in major),
    ):
        d = "".join(vline(xs[t], frame.y(y_top), frame.y(y_bottom)) for t in xs if pick(t))
        if d:
            out.append(svg.path_el(d, cls=cls, fill="none", stroke=stroke, stroke_width=frame.sw(key)))
    base = -_RULER_GAP_PX * px
    ticks = "".join(
        vline(xs[t], frame.y(base), frame.y(base - _TICK_PX[t in major] * px)) for t in xs
    )
    first, last = xs[1], xs[n]
    baseline = f"M{svg.num(first)} {svg.num(frame.y(base))}H{svg.num(last)}"
    out.append(svg.path_el(baseline + ticks, cls="sv-ruler", fill="none", stroke=_COLORS["ink_soft"], stroke_width=frame.sw("ruler")))
    label_y = frame.y(base - (_TICK_PX[1] + 2.0) * px - 0.75 * frame.fs)
    for t in sorted(major):
        out.append(svg.text_el(xs[t], label_y, t, frame.fs, anchor="middle", cls="sv-grid", fill=_COLORS["ink_soft"]))
    return out


def _carrier_group(frame: _Frame, carrier) -> str:
    loc = _loc(frame.deck, carrier)
    w, h = carrier.get_size_x(), carrier.get_size_y()
    rect = svg.el(
        "rect", "", cls="sv-carrier", x=loc.x, y=frame.rect_y(carrier), width=w, height=h, rx=_CARRIER_RX_MM,
        fill=_COLORS["sheet"], stroke=_COLORS["rail"], stroke_width=frame.sw("carrier"),
    )
    label = _label(frame, loc.x + w / 2, frame.rect_y(carrier) - _LABEL_ABOVE_PX * frame.px, carrier.name, cls="sv-label", fill=_COLORS["ink"])
    return _item_group(carrier.name, rect + label)


def _fixture_group(frame: _Frame, res) -> str:
    loc = _loc(frame.deck, res)
    w, h = max(res.get_size_x(), _FIXTURE_MIN_WIDTH_MM), res.get_size_y()
    dash = f"{svg.num(4 * frame.px)} {svg.num(3 * frame.px)}"
    inner = svg.el(
        "rect", "", cls="sv-fixture", x=loc.x, y=frame.rect_y(res), width=w, height=h, rx=_FIXTURE_RX_MM,
        fill="none", stroke=_COLORS["rail"], stroke_width=frame.sw("fixture"), stroke_dasharray=dash,
    )
    if res.get_size_y() > _FIXTURE_LABEL_MIN_MM:
        inner += _label(frame, loc.x + w / 2, frame.rect_y(res) - _LABEL_ABOVE_PX * frame.px, res.name, cls="sv-label sv-label--soft", fill=_COLORS["ink_soft"])
    return _item_group(res.name, inner)


def _plate_layers(items, frame, ox, oy, volume_of) -> tuple[list[str], list]:
    cross_section = labware._plr()[1]
    square = floor.uses_square_cells(len(items))

    def circle_of(i):
        return (not square) and i.child.cross_section_type == cross_section.CIRCLE

    vols = [float(volume_of(i.child)) for i in items]
    layers = [svg.path_el(
        "".join(labware._shape_path(i, circle=circle_of(i), ox=ox, oy=oy) for i in items),
        cls="sv-well", fill=_COLORS["sheet"], stroke=_COLORS["rail"], stroke_width=labware._sw("well", frame.s_n),
    )]
    liquid = []
    for i, v in zip(items, vols, strict=True):
        f = labware._fraction(v, i.child.max_volume)
        if f <= 0:
            continue
        if circle_of(i):
            liquid.append(labware._liquid_circle(i.cx + ox, i.cy + oy, i.d / 2 * math.sqrt(f)))
        else:
            liquid.append(labware._shape_path(i, circle=False, scale=math.sqrt(f), ox=ox, oy=oy))
    if liquid:
        layers.append(svg.path_el("".join(liquid), cls="sv-liquid", fill=_COLORS["moonstone"]))
    return layers, [labware._num_json(v) for v in vols]


def _tip_layers(items, frame, ox, oy) -> tuple[list[str], list]:
    s_n = frame.s_n
    present = [i for i in items if i.child.tip is not None]
    taken = [i for i in items if i.child.tip is None]
    layers = []
    if present:
        layers.append(svg.path_el(
            "".join(labware._shape_path(i, circle=True, ox=ox, oy=oy) for i in present),
            cls="sv-tip-ring", fill=_COLORS["sheet"], stroke=_COLORS["ink"], stroke_width=labware._sw("tip_ring", s_n),
        ))
        layers.append(svg.path_el(
            "".join(labware._dot_path(i.cx + ox, i.cy + oy) for i in present),
            cls="sv-tip", fill="none", stroke=_COLORS["ink"], stroke_width=labware._CORE_RATIO * min(i.d for i in present),
            stroke_linecap="round",
        ))
    if taken:
        dash = svg.num(labware._DASH_PX / s_n)
        layers.append(svg.path_el(
            "".join(labware._shape_path(i, circle=True, ox=ox, oy=oy) for i in taken),
            cls="sv-tip-gone", fill="none", stroke=_COLORS["rail"], stroke_width=labware._sw("taken", s_n),
            stroke_dasharray=f"{dash} {dash}",
        ))
    return layers, [1 if i.child.tip is not None else 0 for i in items]


def _labware_group(frame: _Frame, res, full: bool, volume_of) -> str:
    loc = _loc(frame.deck, res)
    w, h = res.get_size_x(), res.get_size_y()
    ox, oy = loc.x, frame.rect_y(res)
    name = labware._disp(res.name)
    label = _label(frame, ox + w / 2, oy - _LABWARE_LABEL_ABOVE_PX * frame.px, name, cls="sv-label", fill=_COLORS["ink"])
    plate_cls = _plr()[2]
    if not full:
        rect = svg.el(
            "rect", "", cls="sv-block", x=ox, y=oy, width=w, height=h, rx=labware._PLATE_CORNER_MM,
            fill=_COLORS["rail"], stroke=_COLORS["ink"], stroke_width=labware._sw("plate", frame.s_n),
        )
        return _item_group(res.name, rect + label)
    items = labware._items(res)
    outline = svg.el(
        "rect", "", cls="sv-plate", x=ox, y=oy, width=w, height=h, rx=labware._PLATE_CORNER_MM,
        fill=_COLORS["sheet"], stroke=_COLORS["ink"], stroke_width=labware._sw("plate", frame.s_n),
    )
    if isinstance(res, plate_cls):
        layers, values = _plate_layers(items, frame, ox, oy, volume_of)
        kind = "volume"
    else:
        layers, values = _tip_layers(items, frame, ox, oy)
        kind = "tip"
    dx, dy = labware._pitches(items)
    grid = labware._grid_descriptor(kind, res.name, items, values, labware._flags(items, set(), set()), (ox, oy), dx, dy)
    return _item_group(res.name, outline + "".join(layers) + label, grid)


def render_figure(deck, *, level=budget.LEVEL_FULL, volume_of=None) -> str:
    """The plan inside its ``overflow-x:auto`` wrapper; ``""`` at ladder level 2 (drawing omitted).

    Level 0 draws each Plate and TipRack in full when ``detail_of`` says so; level 1 draws every
    piece of labware as a block with no ``data-praxis-grid``.
    """
    _require_deck(deck)
    labware._check_level(level)
    if level >= budget.LEVEL_OMITTED:
        return ""
    volume_of = volume_of or labware._default_volume
    s_n, s_min = deck_scale(deck)
    carriers, pieces, fixtures = _carriers(deck), _labware(deck), _fixtures(deck)
    drawn = carriers + pieces + fixtures
    px = 1.0 / s_n
    top = max((_loc(deck, r).y + r.get_size_y() for r in drawn), default=0.0)
    frame = _Frame(deck, s_n, top + _LABEL_ROOM_PX * px)
    bottom = -(_RULER_GAP_PX + _TICK_PX[1] + 2.0) * px - 1.05 * frame.fs - 2.0 * px
    height = frame.ytop - bottom
    y_rail0 = min((_loc(deck, c).y for c in carriers), default=0.0)

    parts = _rails_and_ruler(frame, y_rail0, top)
    parts += [_fixture_group(frame, r) for r in fixtures]
    parts += [_carrier_group(frame, c) for c in carriers]
    for res in pieces:
        full = level == budget.LEVEL_FULL and detail_of(deck, res) == floor.DETAIL_FULL
        parts.append(_labware_group(frame, res, full, volume_of))
    outer = labware._resource_group(deck.name, sentence(deck), "".join(parts), None)
    return labware._svg_figure(outer, frame.width, height, s_n, s_min)


def render_html(deck, *, level=budget.LEVEL_FULL, volume_of=None) -> str:
    """The whole ``text/html`` of one output at one ladder level: name line, plan (levels 0 and 1),
    the sentence, and at level 2 the omission sentence."""
    _require_deck(deck)
    labware._check_level(level)
    text = sentence(deck)
    parts = [name_line(deck)]
    if level < budget.LEVEL_OMITTED:
        parts.append(render_figure(deck, level=level, volume_of=volume_of))
        parts.append(svg.text_line("p", "praxis-summary", text))
    else:
        parts.append(svg.text_line("p", "praxis-summary", text))
        parts.append(svg.text_line("p", "praxis-omitted", budget.OMISSION_SENTENCE))
    return svg.el("div", "".join(parts), cls="praxis-out praxis-deck")


def stamp(kind: str, resource_name, rev, session, exec_count) -> dict:
    """The D2 stamp: ``{v, kind, resource, rev, session, exec}``. JSON, so no sanitizer strips it."""
    return labware.stamp(kind, resource_name, rev, session, exec_count)


def render(deck, *, rev, session, exec_count, volume_of=None):
    """One mimebundle ``(data, metadata)`` for a Deck (D2).

    ``rev``, ``session`` and ``exec_count`` are injected (as for ``labware.render``). ``data`` holds
    exactly ``text/html`` and ``text/plain`` (the sentence); ``metadata`` is ``{"praxis": stamp}``
    with ``kind == "deck"``. The HTML is held to the 64 KiB cap by the degradation ladder and the
    bundle is validated with ``svg.check_bundle``.
    """
    _require_deck(deck)
    doc, _level = budget.enforce(lambda lv: render_html(deck, level=lv, volume_of=volume_of), budget.LEVELS)
    data = {"text/html": doc, "text/plain": sentence(deck)}
    metadata = {"praxis": stamp("deck", deck.name, rev, session, exec_count)}
    svg.check_bundle(data, metadata)
    return data, metadata
