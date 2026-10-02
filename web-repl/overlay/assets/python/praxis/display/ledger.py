"""``RunLedger``: a run of liquid-handling ops as a table (task B4; spec D9, D2, D4, sections 3.3, 3.5).

``with RunLedger(lh) as run:`` shadows the LiquidHandler ops on ONE INSTANCE for the length of the
block. Each wrapper records a row (``in-flight``, then ``ok`` or ``error``) and awaits the original
bound method, so a ``transfer`` that calls ``self.aspirate`` / ``self.dispense`` hits the wrappers and
owns those rows as children (``return_tips`` and ``discard_tips`` own the one ``drop_tips`` row they
cause, the ``*96`` pair likewise). Steps, tip cycles and uL moved count TOP-LEVEL rows only. On exit
the instance attributes are removed and, unless ``show=False``, the ledger is displayed, on the error
path too and without suppressing the exception (the ledger therefore appears before the error panel).

**Nothing else changes.** PLR modules and classes are never mutated (the wrappers are instance
attributes); an op's arguments, return value and exception pass through untouched (the same objects,
the same exception instance); a wrapper never raises and never alters what it wraps. Everything the
ledger derives from the arguments (where, volumes, channels) is computed defensively, so an argument
it cannot read costs a blank cell, never the op. PLR's logger and its ``pylabrobot.events`` bus are
not used (D9): the bus does not wrap ``return_tips``, ``discard_tips`` or ``transfer``, so it cannot
give nested rows.

**Failures.** An op that raises marks its row ``error`` with the exception class and message, stores
``(exc, step)`` in ``_ERROR_STEPS[id(exc)]`` (the step of the TOP-LEVEL row it belongs to; the dict is
bounded, oldest first) and re-raises the same exception. The D8 error handler reads it back with
``step_for(exc)``, which returns the step and removes the entry.

**Nesting** follows the calling context (a ``ContextVar``), not a global stack: ops started by
``asyncio.gather`` inside an op are its children, two tasks that each run one op are siblings, and a
task that outlives its parent op files its rows at the top level.

**Where things are decided.** Action names, verb forms and roles come from ``glossary`` (AC-28: no
action string is spelled here). The table, the name line and the text are built with ``svg`` helpers
only, every interpolated string through their escaping (D2), class-only elements outside the SVG
(S2). The after-state figures are labware's own (``labware.render_figure``): the plates this run
dispensed into, frozen when the ledger detaches, with the wells that changed outlined in rose.

**Byte cap (D4).** ``bundle`` runs ``budget.enforce``: level 0 the table and the figures, level 1 the
figures as blocks, level 2 the table alone plus the omission sentence and no bars. If even that is
over the cap the LAST fallback is fewer table rows, with a line saying how many are not shown; the
header counts stay true. (The spec's ladder stops at level 2; a run of thousands of rows has no other
way to stay under the cap, which is never exceeded, AC-13.)

**Session and execution count.** The stamp needs the display session id and ``get_ipython()``'s
execution count, which ``install()`` (B8) owns. ``configure(session=..., exec_count=...)`` is the seam:
each is a value or a zero-argument callable, read at render time; ``configure()`` resets.

Plain CPython: this module imports only the standard library and its siblings ``budget``,
``glossary``, ``labware`` (which resolves PLR lazily, inside functions) and ``svg``. No PLR import,
no IPython, no ``js`` at import time; ``IPython.display.display`` is resolved when a ledger exits with
no ``display`` injected.
"""

from __future__ import annotations

import contextvars
import dataclasses
import inspect
import logging
import math

from . import budget, glossary, labware, svg

__all__ = [
    "IN_FLIGHT", "OK", "ERROR", "Row", "RunLedger", "configure", "step_for",
]

log = logging.getLogger("praxis.display")

IN_FLIGHT = "in-flight"
OK = "ok"
ERROR = "error"

# Error cooperation with D8: id(exc) -> (exc, step). The value holds the exception itself, so an id
# cannot be recycled while its entry lives, and it is bounded because nothing forces a reader.
_ERROR_STEPS: dict = {}
_ERROR_STEPS_MAX = 64

# The row of the op running in this context (see "Nesting" above).
_CURRENT = contextvars.ContextVar("praxis_display_ledger_row", default=None)

_MISSING = object()
_UNSET = object()
_EPS_UL = 1e-6
_HEAD96_CHANNELS = 96

_WHERE_MAX = 300
_NAME_MAX = 200
_ERROR_MAX = 160
_BAR_MAX_PX = 56
_BAR_HEIGHT_PX = 6
_PLAIN_MAX_ROWS = 500
_NEST = "↳"
_DEFAULT_SESSION = "unset"

_COLUMNS = ("Step", "Action", "Where", "Volume", "Channels")


# --------------------------------------------------------------------------- the rows


@dataclasses.dataclass(eq=False)
class Row:
    """One op the ledger saw. ``step`` is the top-level step number (``None`` for a child row);
    ``vols`` is the volume PER CHANNEL in uL (``()`` when the op moves no liquid or it is unknown);
    ``channels`` is how many channels the op used (``None`` when unknown)."""

    id: int
    op: str
    action: str
    step: int | None
    parent: Row | None = dataclasses.field(repr=False)
    depth: int
    where: str = ""
    vols: tuple = ()
    channels: int | None = None
    status: str = IN_FLIGHT
    error_type: str | None = None
    error_message: str | None = None
    children: list = dataclasses.field(default_factory=list, repr=False)
    owner: object = dataclasses.field(default=None, repr=False)

    @property
    def volume(self) -> float:
        """Total uL: the sum over channels."""
        return float(sum(self.vols))

    def top(self) -> Row:
        """The top-level row this row belongs to (itself when it is one)."""
        row = self
        while row.parent is not None:
            row = row.parent
        return row

    def walk(self):
        """This row, then its children, depth first."""
        yield self
        for child in self.children:
            yield from child.walk()


# --------------------------------------------------------------------------- error cooperation


def _remember(exc, step) -> None:
    if step is None:
        return
    _ERROR_STEPS.pop(id(exc), None)  # re-insert: the newest entry lives longest
    _ERROR_STEPS[id(exc)] = (exc, step)
    while len(_ERROR_STEPS) > _ERROR_STEPS_MAX:
        _ERROR_STEPS.pop(next(iter(_ERROR_STEPS)))


def step_for(exc):
    """The step of the top-level row *exc* was raised in, once: the entry is removed. ``None`` for an
    exception no ledger saw, and for a second call."""
    entry = _ERROR_STEPS.get(id(exc))
    if entry is None or entry[0] is not exc:
        return None
    del _ERROR_STEPS[id(exc)]
    return entry[1]


# --------------------------------------------------------------------------- session and exec seam

_providers = {"session": None, "exec_count": None}


def configure(*, session=None, exec_count=None) -> None:
    """Set where the stamp's display session id and execution count come from (each a value or a
    zero-argument callable, read at render time). ``configure()`` restores the defaults."""
    _providers["session"] = session
    _providers["exec_count"] = exec_count


def _provided(key):
    provider = _providers[key]
    try:
        return provider() if callable(provider) else provider
    except Exception:  # noqa: BLE001 -- a broken provider must never break a display
        log.debug("ledger %s provider failed", key, exc_info=True)
        return None


def _session_id() -> str:
    value = _provided("session")
    return value if isinstance(value, str) and value else _DEFAULT_SESSION


def _exec_count():
    value = _provided("exec_count")
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


# --------------------------------------------------------------------------- reading the arguments


def _short(text, limit: int) -> str:
    s = str(text)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _labware_kind(x):
    """``plate``, ``tiprack`` or ``container`` for a PLR labware object, else ``None``."""
    if x is None:
        return None
    try:
        return labware.kind_of(x)
    except TypeError:
        return None


def _as_list(x) -> list:
    """A resource argument as a list: a list or tuple as is, anything else as one item."""
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _where(resources) -> str:
    """Where an op acted: ``"source, column 1"`` for a whole column, ``"assay A1:H3"`` for a block,
    a comma list otherwise, wells grouped by their plate or tip rack; any other resource by name."""
    order: list = []   # first-seen keys
    groups: dict = {}  # key -> (parent, [ids]) for wells and tip spots
    loose: dict = {}   # key -> name for everything else
    for res in resources:
        parent = getattr(res, "parent", None)
        if parent is not None and hasattr(res, "get_identifier") and _labware_kind(parent) in ("plate", "tiprack"):
            key = ("g", id(parent))
            if key not in groups:
                groups[key] = (parent, [])
                order.append(key)
            groups[key][1].append(res.get_identifier())
            continue
        name = getattr(res, "name", None)
        if isinstance(name, str):
            key = ("n", name)
            if key not in loose:
                loose[key] = _short(name, _NAME_MAX)
                order.append(key)
    parts = []
    for key in order:
        if key in groups:
            parent, ids = groups[key]
            parts.append(labware.where_label(parent.name, ids, n_rows=parent.num_items_y))
        else:
            parts.append(loose[key])
    return _short(", ".join(parts), _WHERE_MAX)


def _finite(values) -> bool:
    return all(math.isfinite(v) for v in values)


def _per_channel(volumes, n):
    """uL per channel from a ``vols`` argument: a list as is, a scalar broadcast over *n* channels;
    ``()`` when it cannot be read as finite numbers."""
    if volumes is None:
        return ()
    if isinstance(volumes, (int, float)) and not isinstance(volumes, bool):
        vols = (float(volumes),) * max(int(n or 1), 1)
    else:
        vols = tuple(float(v) for v in volumes)
    return vols if _finite(vols) else ()


def _safe(fn, default):
    try:
        return fn()
    except Exception:  # noqa: BLE001 -- describing an op must never break the op
        log.debug("could not describe an op argument", exc_info=True)
        return default


@dataclasses.dataclass
class _Info:
    where: str = ""
    vols: tuple = ()
    channels: int | None = None
    targets: list = dataclasses.field(default_factory=list)  # containers a dispense acts on


def _mounted(lh) -> int:
    return sum(1 for t in lh.head.values() if getattr(t, "has_tip", False))


def _channel_count(bound, fallback):
    use = bound.get("use_channels")
    return len(use) if use else fallback


def _describe(lh, name, bound) -> _Info:
    """What a row shows for op *name* called with the bound arguments *bound*."""
    role = glossary.role_of(name)
    info = _Info()
    if glossary.is_96(name):
        info.channels = _HEAD96_CHANNELS
        res = bound.get("tip_rack") if bound.get("tip_rack") is not None else bound.get("resource")
        resources = _as_list(res)
        info.where = _safe(lambda: _where(resources), "")
        if role in (glossary.ASPIRATE, glossary.DISPENSE):
            info.vols = _safe(lambda: _per_channel(bound.get("volume"), _HEAD96_CHANNELS), ())
            if role == glossary.DISPENSE:
                info.targets = resources
        return info
    if role in (glossary.PICK_UP, glossary.DROP):
        spots = _as_list(bound.get("tip_spots"))
        info.where = _safe(lambda: _where(spots), "")
        if spots:
            info.channels = _safe(lambda: _channel_count(bound, len(spots)), None)
        elif role == glossary.DROP:  # a return or a discard: every channel that has a tip
            info.channels = _safe(lambda: _channel_count(bound, _mounted(lh)), None)
        return info
    if role in (glossary.ASPIRATE, glossary.DISPENSE):
        resources = _as_list(bound.get("resources"))
        info.where = _safe(lambda: _where(resources), "")
        info.channels = _safe(lambda: _channel_count(bound, len(resources)), None)
        info.vols = _safe(lambda: _per_channel(bound.get("vols"), info.channels or len(resources)), ())
        if role == glossary.DISPENSE:
            info.targets = resources
        return info
    if role == glossary.TRANSFER:
        source, targets = _as_list(bound.get("source")), _as_list(bound.get("targets"))
        src, dst = _safe(lambda: _where(source), ""), _safe(lambda: _where(targets), "")
        info.where = _short(f"{src} to {dst}" if src and dst else src or dst, _WHERE_MAX)
        info.channels = 1

        def total():
            each = bound.get("source_vol")
            if each is None:
                each = sum(bound.get("target_vols") or ())
            v = float(each)
            return (v,) if math.isfinite(v) else ()

        info.vols = _safe(total, ())
        info.targets = targets
    return info


# --------------------------------------------------------------------------- the ledger


class RunLedger:
    """Records the LiquidHandler ops called on ONE handler while it is attached.

    ``RunLedger(lh, *, show=True, display=None)``: ``show`` displays the ledger when the ``with``
    block exits (on error too); ``display`` is the function that does it (default
    ``IPython.display.display``, resolved then). Public: ``rows`` (top-level rows), ``all_rows``,
    ``steps``, ``tip_cycles``, ``moved``, ``attached``, ``summary()``, ``attach()`` / ``detach()``
    (both idempotent), ``render_html(level)``, ``text()`` and ``bundle(session=, exec_count=)``.
    """

    def __init__(self, lh, *, show: bool = True, display=None):
        self._lh = lh
        self._show = bool(show)
        self._display = display
        self._rows: list[Row] = []
        self._counter = 0
        self._attached = False
        self._gen = 0
        self._saved: dict = {}
        self._installed: dict = {}
        self._origs: dict = {}
        self._sigs: dict = {}
        self._touched: dict = {}
        self._after = None

    # -- state ------------------------------------------------------------------

    @property
    def attached(self) -> bool:
        return self._attached

    @property
    def rows(self) -> list:
        """The top-level rows, in step order (a copy)."""
        return list(self._rows)

    @property
    def all_rows(self) -> list:
        """Every row, depth first: each top-level row followed by its children."""
        return [r for top in self._rows for r in top.walk()]

    @property
    def steps(self) -> int:
        return len(self._rows)

    @property
    def tip_cycles(self) -> int:
        """Top-level pick-ups that did not fail: a cycle starts at each pick-up."""
        return sum(1 for r in self._rows if glossary.role_of(r.op) == glossary.PICK_UP and r.status != ERROR)

    @property
    def moved(self) -> float:
        """uL moved: top-level dispenses and transfers that finished ok (children are not added)."""
        return float(sum(
            r.volume for r in self._rows
            if r.status == OK and glossary.role_of(r.op) in (glossary.DISPENSE, glossary.TRANSFER)
        ))

    def summary(self) -> str:
        """``run  12 steps, 3 tip cycles, 2,400 µL moved``: the name line's text."""
        return f"run  {self._counts()}"

    def _counts(self) -> str:
        return ", ".join((
            glossary.plural(self.steps, "step"),
            glossary.plural(self.tip_cycles, "tip cycle"),
            f"{svg.fmt_amount(self.moved)} µL moved",
        ))

    def __repr__(self) -> str:
        return f"<RunLedger {self.steps} steps{', attached' if self._attached else ''}>"

    # -- attach and detach ------------------------------------------------------

    def _wrap(self, name, orig):
        """The wrapper that goes on the instance in place of *orig* (a bound method). The one seam
        the tests replace to prove the transparency checks can fail."""
        ledger, gen = self, self._gen

        async def wrapper(*args, **kwargs):
            if not (ledger._attached and ledger._gen == gen):  # detached: forward, record nothing
                result = orig(*args, **kwargs)
                return await result if inspect.isawaitable(result) else result
            row = ledger._begin(name, args, kwargs)
            token = _CURRENT.set(row)
            try:
                result = orig(*args, **kwargs)
                if inspect.isawaitable(result):
                    result = await result
            except BaseException as exc:
                ledger._fail(row, exc)
                raise
            else:
                ledger._finish(row)
                return result
            finally:
                try:
                    _CURRENT.reset(token)
                except ValueError:  # reset from another context (a generator finalised elsewhere)
                    pass

        wrapper.__name__ = name
        wrapper.__qualname__ = f"RunLedger.{name}"
        wrapper.__doc__ = getattr(orig, "__doc__", None)
        wrapper.__wrapped__ = orig
        return wrapper

    def attach(self) -> RunLedger:
        """Shadow the handler's ops with recording wrappers. Idempotent. ``TypeError`` for an object
        that cannot take instance attributes or has none of the ops; ``RuntimeError`` when another
        ledger is attached to the same handler. All or nothing."""
        if self._attached:
            return self
        lh = self._lh
        try:
            ns = vars(lh)
        except TypeError as exc:
            raise TypeError(f"RunLedger needs a LiquidHandler, not {type(lh).__name__}") from exc
        if any(getattr(ns.get(n), "_praxis_ledger", None) is not None for n in glossary.ACTIONS):
            raise RuntimeError("a RunLedger is already attached to this LiquidHandler")
        found = {n: getattr(lh, n) for n in glossary.ACTIONS if callable(getattr(lh, n, None))}
        if not found:
            raise TypeError(f"{type(lh).__name__} has none of the LiquidHandler operations")
        self._gen += 1
        for name, orig in found.items():
            try:
                self._sigs[name] = inspect.signature(orig)
            except (TypeError, ValueError):
                self._sigs[name] = None
        wrappers = {n: self._wrap(n, o) for n, o in found.items()}
        for w in wrappers.values():
            try:
                w._praxis_ledger = self
            except AttributeError:  # a seam that returns a builtin method: nothing to mark
                pass
        saved = {n: ns.get(n, _MISSING) for n in found}
        done: list = []
        try:
            for n, w in wrappers.items():
                ns[n] = w
                done.append(n)
        except Exception:
            for n in done:
                if saved[n] is _MISSING:
                    ns.pop(n, None)
                else:
                    ns[n] = saved[n]
            raise
        self._origs, self._saved, self._installed = found, saved, wrappers
        self._attached = True
        return self

    def detach(self) -> RunLedger:
        """Remove the wrappers and freeze the after-state. Idempotent. An op attribute that was on the
        instance before is put back; one somebody else installed over ours is left alone."""
        if not self._attached:
            return self
        self._attached = False  # first, so a wrapper someone still holds is already inert
        ns = vars(self._lh)
        for n, w in self._installed.items():
            if ns.get(n) is w:
                if self._saved[n] is _MISSING:
                    del ns[n]
                else:
                    ns[n] = self._saved[n]
        self._installed, self._saved, self._origs = {}, {}, {}
        self._after = _safe(self._compute_after, [])
        return self

    def __enter__(self) -> RunLedger:
        return self.attach()

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.detach()
        if self._show:
            try:
                display = self._display
                if display is None:
                    from IPython.display import display  # noqa: PLC0415 -- resolved only when shown
                display(self)
            except Exception:
                if exc_type is None:
                    raise
                log.warning("could not display the run ledger", exc_info=True)  # the op's error wins
        return False

    # -- recording --------------------------------------------------------------

    def _bound(self, name, args, kwargs) -> dict:
        sig = self._sigs.get(name)
        try:
            if sig is not None:
                return dict(sig.bind_partial(*args, **kwargs).arguments)
        except TypeError:
            pass
        return dict(kwargs)

    def _begin(self, name, args, kwargs) -> Row:
        parent = _CURRENT.get()
        if parent is not None and (parent.owner is not self or parent.status != IN_FLIGHT):
            parent = None
        info = _safe(lambda: _describe(self._lh, name, self._bound(name, args, kwargs)), _Info())
        row = Row(
            id=self._counter, op=name, action=glossary.action_name(name),
            step=None if parent is not None else len(self._rows) + 1,
            parent=parent, depth=0 if parent is None else parent.depth + 1,
            where=info.where, vols=info.vols, channels=info.channels, owner=self,
        )
        self._counter += 1
        (self._rows if parent is None else parent.children).append(row)
        _safe(lambda: self._touch(info.targets), None)
        return row

    def _close(self, row: Row) -> None:
        if row.children:  # a return or a discard says where the drop it caused went
            if not row.where:
                row.where = row.children[0].where
            if row.channels is None:
                row.channels = row.children[0].channels

    def _finish(self, row: Row) -> None:
        row.status = OK
        self._close(row)

    def _fail(self, row: Row, exc: BaseException) -> None:
        row.status = ERROR
        row.error_type = type(exc).__name__
        try:
            row.error_message = str(exc)
        except Exception:  # noqa: BLE001 -- a hostile __str__ must not replace the op's error
            row.error_message = f"<{row.error_type} could not be printed>"
        self._close(row)
        if isinstance(exc, Exception):
            _remember(exc, row.top().step)

    # -- the after-state --------------------------------------------------------

    def _touch(self, targets) -> None:
        """Remember the COMMITTED volume of every container a dispense is about to change (first touch).
        Committed (``tracker.volume``), not pending (``get_used_volume``): PLR's 96 ops queue their tracker
        changes outside their ``try``, so a refused 96 op leaves pending volume on wells nothing was
        dispensed into, and the after-state must not show those as changed (#5659, N5659-10)."""
        for res in targets:
            if _labware_kind(res) == "plate":
                wells = res.get_all_items()
            elif getattr(res, "tracker", None) is not None:
                wells = [res]
            else:
                continue
            for well in wells:
                if id(well) not in self._touched:
                    self._touched[id(well)] = (well, well.tracker.volume)

    def _compute_after(self) -> list:
        """``[(plate, changed_ids, {id(well): uL})]`` for each plate this run dispensed into, in order
        of first touch, keeping only plates with a well whose volume changed."""
        plates: dict = {}
        for well, before in self._touched.values():
            plate = well.parent
            if plate is None or _labware_kind(plate) != "plate":
                continue
            changed = plates.setdefault(id(plate), (plate, set()))[1]
            if abs(well.tracker.volume - before) > _EPS_UL:
                changed.add(well.get_identifier())
        return [
            (plate, ids, {id(w): w.tracker.volume for w in plate.get_all_items()})
            for plate, ids in plates.values() if ids
        ]

    def _after_state(self) -> list:
        return self._after if self._after is not None else _safe(self._compute_after, [])

    # -- rendering --------------------------------------------------------------

    @staticmethod
    def _volume_text(row: Row) -> str:
        if not row.vols:
            return ""
        lo, hi = min(row.vols), max(row.vols)
        a, b = svg.fmt_amount(lo), svg.fmt_amount(hi)
        if a != b:
            return f"{a}–{b} µL"
        return f"{a} µL each" if len(row.vols) > 1 else f"{a} µL"

    @staticmethod
    def _plain_line(row: Row) -> str:
        step = f"{row.step:>3}" if row.step is not None else "   "
        lead = f"{step}  " + "  " * row.depth + (f"{_NEST} " if row.depth else "")
        parts = [row.action, row.where, RunLedger._volume_text(row)]
        if row.channels is not None:
            parts.append(glossary.plural(row.channels, "channel"))
        line = lead + "  ".join(p for p in parts if p)
        if row.status == IN_FLIGHT:
            line += f"  [{IN_FLIGHT}]"
        elif row.status == ERROR:
            line += f"  [{ERROR}: {_short(f'{row.error_type}: {row.error_message}', _ERROR_MAX)}]"
        return line

    def text(self, *, max_rows: int = _PLAIN_MAX_ROWS) -> str:
        """``text/plain``: the summary line, then one line per row (children indented)."""
        rows = self.all_rows
        lines = [self.summary()] + [self._plain_line(r) for r in rows[:max_rows]]
        if len(rows) > max_rows:
            lines.append(self._more_text(len(rows) - max_rows))
        return "\n".join(lines)

    @staticmethod
    def _more_text(n: int) -> str:
        return f"… {svg.fmt_amount(n)} more {'row' if n == 1 else 'rows'} not shown."

    def _row_html(self, row: Row, level: int, widest: float) -> str:
        role = glossary.role_of(row.op)
        classes = ["praxis-ledger__row", f"praxis-ledger__row--{row.status}"]
        if row.parent is not None:
            classes.append("praxis-ledger__row--child")
        if row.parent is None and role == glossary.PICK_UP:
            classes.append("praxis-ledger__row--cycle")  # a new tip cycle: a hairline above it
        act = ""
        if row.parent is not None:
            act += svg.text_line("span", "praxis-ledger__nest", _NEST) + " "
        act += svg.esc_text(row.action)
        if row.status == IN_FLIGHT:
            act += " " + svg.text_line("span", "praxis-ledger__status", IN_FLIGHT)
        elif row.status == ERROR:
            message = _short(f"{ERROR}: {row.error_type}: {row.error_message}", _ERROR_MAX)
            act += " " + svg.text_line("span", "praxis-ledger__err", message)
        vol = svg.esc_text(self._volume_text(row))
        if level < budget.LEVEL_OMITTED and role in (glossary.ASPIRATE, glossary.DISPENSE) and row.vols and widest > 0:
            width = max(2, round(_BAR_MAX_PX * max(row.vols) / widest))
            rect = svg.el("rect", "", x=0, y=0, width=width, height=_BAR_HEIGHT_PX, rx=_BAR_HEIGHT_PX / 2,
                          fill=labware.COLORS["moonstone"])
            vol = svg.el(
                "svg", rect, cls="praxis-ledger__bar", width=width, height=_BAR_HEIGHT_PX,
                viewBox=f"0 0 {width} {_BAR_HEIGHT_PX}", aria_hidden="true",
            ) + vol
        cells = (
            svg.el("td", svg.esc_text("" if row.step is None else row.step), cls="praxis-ledger__step")
            + svg.el("td", act, cls="praxis-ledger__act")
            + svg.el("td", svg.esc_text(row.where), cls="praxis-ledger__where")
            + svg.el("td", vol, cls="praxis-ledger__vol")
            + svg.el("td", svg.esc_text("" if row.channels is None else row.channels), cls="praxis-ledger__ch")
        )
        return svg.el("tr", cells, cls=" ".join(classes))

    def _after_html(self, level: int) -> str:
        afters = self._after_state()
        if not afters:
            return ""
        if level >= budget.LEVEL_OMITTED:
            return svg.text_line("p", "praxis-omitted", budget.OMISSION_SENTENCE)
        blocks = []
        for plate, changed, volumes in afters:
            def volume_of(well, volumes=volumes):
                return volumes.get(id(well), well.tracker.volume)

            label = f"The {_short(plate.name, _NAME_MAX)} plate after the run. Wells this run changed are outlined."
            blocks.append(
                svg.text_line("p", "praxis-ledger__after-label", label)
                + labware.render_figure(plate, level=level, volume_of=volume_of, changed=changed)
                + svg.text_line("p", "praxis-summary", labware.sentence(plate, volume_of))
            )
        return svg.el("div", "".join(blocks), cls="praxis-ledger__after")

    def render_html(self, level: int = budget.LEVEL_FULL, *, max_rows: int | None = None) -> str:
        """The whole ``text/html`` at one ladder level (see the module docstring). ``max_rows`` shows
        only the first rows of the table and says how many are not shown."""
        if isinstance(level, bool) or level not in budget.LEVELS:
            raise ValueError(f"level must be one of {budget.LEVELS}, got {level!r}")
        rows = self.all_rows
        shown = rows if max_rows is None else rows[:max_rows]
        widest = max(
            (max(r.vols) for r in shown if r.vols and glossary.role_of(r.op) in (glossary.ASPIRATE, glossary.DISPENSE)),
            default=0.0,
        )
        head = svg.el("p", "  ".join((
            svg.text_line("span", "praxis-name__title", "run"),
            svg.text_line("span", "praxis-name__type", self._counts()),
        )), cls="praxis-name")
        thead = svg.el("thead", svg.el("tr", "".join(
            svg.el("th", svg.esc_text(c), cls="praxis-ledger__th") for c in _COLUMNS
        ), cls="praxis-ledger__head"))
        tbody = svg.el("tbody", "".join(self._row_html(r, level, widest) for r in shown))
        parts = [head, svg.el("table", thead + tbody, cls="praxis-ledger__table")]
        if len(shown) < len(rows):
            parts.append(svg.text_line("p", "praxis-ledger__more", self._more_text(len(rows) - len(shown))))
        parts.append(self._after_html(level))
        return svg.el("div", "".join(parts), cls="praxis-out praxis-ledger")

    def _render_capped(self, level: int) -> str:
        doc = self.render_html(level)
        if level < budget.LEVEL_OMITTED:
            return doc
        n = len(self.all_rows)
        while budget.html_bytes(doc) > budget.MAX_HTML_BYTES and n > 0:
            n //= 2
            doc = self.render_html(level, max_rows=n)
        return doc

    def bundle(self, *, session=_UNSET, exec_count=_UNSET):
        """One mimebundle ``(data, metadata)`` (D2): ``text/html`` under the 64 KiB cap,
        ``text/plain`` starting with the summary, and the stamp ``kind: "ledger"`` with
        ``resource: null`` and ``rev: null``. Validated with ``svg.check_bundle``."""
        session = _session_id() if session is _UNSET else session
        exec_count = _exec_count() if exec_count is _UNSET else exec_count
        doc, _level = budget.enforce(self._render_capped)
        data = {"text/html": doc, "text/plain": self.text()}
        metadata = {"praxis": labware.stamp("ledger", None, None, session, exec_count)}
        svg.check_bundle(data, metadata)
        return data, metadata

    def _repr_mimebundle_(self, include=None, exclude=None):
        """What IPython's ``display(run)`` asks for."""
        return self.bundle()
