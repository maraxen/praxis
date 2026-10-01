"""Error context resolution for ``praxis.display`` (task B5; spec D8 steps 1-5, section 3.3, AC-15).

``resolve(exc, tb) -> ErrorContext | None`` reads the traceback frames of one of the four PLR errors
(``TooLittleLiquidError``, ``TooLittleVolumeError``, ``HasTipError``, ``NoTipError``) and says WHICH
resource, channel or tip the fault is about, and by how much, so B6's panel can name it. PLR's own
message omits all of that. It never patches PLR and it changes no state: it only reads. **It never
guesses:** every path that cannot be established from the frames and the committed state gives
``None``, and the handler then shows the generic panel.

1. **Tracker.** The innermost frame (below the innermost op frame, when there is one) whose ``self``
   is a ``VolumeTracker`` or a ``TipTracker``.
2. **Op frames.** Frames whose ``self`` is a ``LiquidHandler`` AND whose ``co_name`` is a key of
   ``glossary.ACTIONS`` (read at call time). That excludes PLR 1.0's ``wrapper`` frames and any
   comprehension frame. If EVERY op frame is a ``*96`` op the 96 path below resolves it (#5659,
   N5659-1); if some are and some are not (a subclass ``aspirate`` calling ``aspirate96``, or an
   ordinary op under a ``*96`` frame) the result is ``None``; with no ``*96`` frame it is the
   1-channel path. The INNERMOST op frame supplies the locals (``resources`` or ``tip_spots``,
   ``use_channels``, ``vols``, and for the pick-up loop ``channel``); the OUTERMOST supplies
   ``action``, the user's call. A missing local is read as absent, never guessed.
3. **Owner, by identity** (rules (a)-(e), D8): (a) a container of ``lh.deck``'s subtree whose tracker
   IS the tracker, or a tip spot whose ``tip_spot_tracker(spot)`` IS the tracker; (b) ``lh.head[c]``;
   (c) a mounted tip whose own tracker IS the tracker; (d) with NO op frame, parse ``tracker.thing``
   (``"Channel N"``, ``"<name>_volume_tracker"``, or a tip spot's own name) and look the name up on
   the decks the frames reach; (e) no tracker frame, a ``HasTipError`` and a ``channel`` local. A
   name that matches a ``Tip`` gives no owner. Rule (d) also requires the found resource's tracker to
   be the tracker that raised (a same-named impostor does not resolve).
4. **Offending set: committed state only.** PLR validates against PENDING state and raises on the
   first failing channel only, so every number is recomputed from COMMITTED state: volume errors
   sum demand per resource over the op's channels (per channel for a tip owner); tip errors use
   ``TipTracker.get_tip()`` succeeding (never ``has_tip``, never ``TipSpot.get_tip()``, never a
   spot's own ``.tracker``). An owner outside that set (pending residue) gives ``None``.

**The 96 path** (#5659; ``261001_nd-next-5659-96head-errors.md`` N5659-1..4). The 96 ops bind
``containers`` / ``volume`` (aspirate96, dispense96), ``tip_rack`` (pick_up_tips96) or ``resource``
(drop_tips96) instead of the 1-channel ``resources`` / ``use_channels`` / ``vols``, so ``_op96_inputs``
normalises them to the same shape: the channels are those of ``lh.head96`` that PHYSICALLY hold a tip
(a committed tip, never the ``tips`` local, which is built from ``has_tip`` and so includes pending
state), one resource per channel. A container list that is neither 96 wells of one plate nor one
container the head fits in gives ``None`` (dispense96 runs its tip loop before its count and fit
checks). Owners are matched against ``lh.head96`` and never ``lh.head``; a NoTip error on the 96 path
always gives ``None`` (it arises only where a pending check passes and a committed read fails, which
committed state cannot explain). ``ErrorContext.head96`` and ``container_mode`` carry the path.

**Residue** (#5659 task 8; N5659-11). PLR's 96 ops queue tracker changes before their ``try``, so a refused
op leaves PENDING changes behind. On the 96 path ``ErrorContext.residue`` carries them, found by
``residue.of`` -- the only display module that reads pending state. This module reads none: the
``residue`` import is the whole of its involvement, which is why the scan below stays as it was.

**Deck source for rule (d).** With no op frame there is no ``lh.deck``. The roots searched are those
the frames reach (a local that is a ``LiquidHandler`` gives its deck, a local that is a resource gives
its root: in a notebook the cell's frame IS the user's namespace) plus any passed in ``decks``. A name
found on more than one distinct resource is ambiguous, so it gives no owner.

The result is an immutable ``ErrorContext``; see its docstring for what each field means to B6.

Plain CPython: no PLR, IPython or ``js`` import at import time. PLR classes are resolved inside
functions, from the pin's non-shim homes only (``pylabrobot.legacy.liquid_handling``,
``pylabrobot.legacy.tip_tracker``, ``pylabrobot.resources``, ``pylabrobot.resources.errors``,
``pylabrobot.resources.volume_tracker``).
"""

from __future__ import annotations

import dataclasses
import functools
import types
from typing import Any

from . import glossary, residue

__all__ = [
    "OWNER_CONTAINER", "OWNER_TIP_SPOT", "OWNER_CHANNEL", "OWNER_TIP",
    "Offender", "ErrorContext", "resolve", "PATH_1CH", "PATH_96",
]

#: The owner is a container (a well or a trough); ``ErrorContext.owner`` is that resource.
OWNER_CONTAINER = "container"
#: The owner is a tip spot; ``ErrorContext.owner`` is that ``TipSpot``.
OWNER_TIP_SPOT = "tip_spot"
#: The owner is a channel (no tip involved); ``ErrorContext.channel`` is its index, ``owner`` is ``None``.
OWNER_CHANNEL = "channel"
#: The owner is the tip mounted on a channel; ``owner`` is the ``Tip``, ``channel`` its channel.
OWNER_TIP = "tip"

_EPS = 1e-6  # PLR's own tolerance (volume_tracker.py:101, :116)
_VOLUME_TRACKER_SUFFIX = "_volume_tracker"  # container.py:87
_CHANNEL_PREFIX = "Channel "  # legacy/liquid_handling/liquid_handler.py:418


@dataclasses.dataclass(frozen=True, eq=False)
class Offender:
    """One member of the committed offending set.

    ``target`` is a resource (a container or a tip spot) or, for a channel or a tip owner, the channel
    index. ``requested`` and ``available`` are the committed numbers for a volume error (``requested``
    summed per resource, per channel for a tip; ``available`` the committed volume for a TLL and the
    committed room for a TLV) and ``None`` for a tip error.
    """

    target: Any
    requested: float | None
    available: float | None


@dataclasses.dataclass(frozen=True, eq=False)
class ErrorContext:
    """What B6 needs to name a fault. Identity-compared (resources compare by value in PLR).

    - ``error``: the exception class name.
    - ``action``: the OUTERMOST op frame's method name (a ``glossary.ACTIONS`` key), the user's call;
      ``None`` with no op frame (rule (d)). ``op``: the INNERMOST op frame's name, the one whose locals
      were used (differs from ``action`` for ``return_tips``/``discard_tips`` -> ``drop_tips``).
    - ``rule``: which owner rule fired, ``"a"`` to ``"e"``.
    - ``owner_kind`` / ``owner`` / ``channel``: see the ``OWNER_*`` constants.
    - ``resources`` / ``channels`` / ``volumes``: the op's ``resources`` (or ``tip_spots``),
      ``use_channels`` and ``vols`` as bound in the innermost op frame; ``()`` when absent.
    - ``offending``: the committed offending set, in op order, as ``Offender`` records; ``targets``
      is just their targets.
    - ``requested`` / ``available``: the OWNER's committed numbers (``None`` for tip errors); a tip
      owner's are per channel.
    - ``head96``: ``True`` when the error was resolved on the 96 path (``channels`` are then the
      ``lh.head96`` channels that hold a committed tip; ``resources`` one entry per such channel).
    - ``container_mode``: on the 96 path of ``aspirate96`` / ``dispense96``, ``"per_channel"`` (96
      wells of one plate, channel c pairs with well c) or ``"single"`` (one container for the whole
      head, which may be the only well of a Plate); ``None`` otherwise.
    - ``residue``: on the 96 path, the ``residue.Residue`` records for the changes PLR queued on the op's
      trackers and never confirmed (containers, mounted tips, head channels, rack spots); ``()`` when there
      are none and always on the 1-channel path.
    """

    error: str
    action: str | None
    op: str | None
    rule: str
    owner_kind: str
    owner: Any
    channel: int | None
    resources: tuple
    channels: tuple
    volumes: tuple
    offending: tuple
    requested: float | None
    available: float | None
    head96: bool = False
    container_mode: str | None = None
    residue: tuple = ()

    @property
    def targets(self) -> tuple:
        return tuple(o.target for o in self.offending)


# --------------------------------------------------------------------------- PLR, resolved lazily


@functools.cache
def _plr():
    """The PLR classes the resolver dispatches on, resolved when first needed, never at import."""
    from pylabrobot.legacy.liquid_handling import LiquidHandler
    from pylabrobot.legacy.tip_tracker import TipTracker, tip_spot_tracker
    from pylabrobot.resources import Container, Resource, ResourceNotFoundError, TipRack, TipSpot
    from pylabrobot.resources.errors import (
        HasTipError,
        NoTipError,
        TooLittleLiquidError,
        TooLittleVolumeError,
    )
    from pylabrobot.resources.volume_tracker import VolumeTracker

    return types.SimpleNamespace(
        LiquidHandler=LiquidHandler, TipTracker=TipTracker, tip_spot_tracker=tip_spot_tracker,
        Container=Container, Resource=Resource, ResourceNotFoundError=ResourceNotFoundError,
        TipRack=TipRack, TipSpot=TipSpot, HasTipError=HasTipError, NoTipError=NoTipError,
        TooLittleLiquidError=TooLittleLiquidError, TooLittleVolumeError=TooLittleVolumeError,
        VolumeTracker=VolumeTracker,
        FOUR=(TooLittleLiquidError, TooLittleVolumeError, HasTipError, NoTipError),
    )


# --------------------------------------------------------------------------- committed readers
#
# The ONLY places that read tracker state or a spot's or container's tracker. Everything else goes
# through them, so "committed, never pending" and "never has_tip / TipSpot.get_tip / spot.tracker" are
# each a one-function fact (the tests scan for it, and mutate these to prove the checks bite).


def _committed_volume(tracker):
    """The committed volume: ``VolumeTracker.volume`` (never ``pending_volume``)."""
    return tracker.volume


def _committed_room(tracker):
    """The committed room: ``max_volume`` less the committed volume (PLR's free volume reads pending)."""
    return tracker.max_volume - _committed_volume(tracker)


def _committed_tip(tracker):
    """The committed tip of a ``TipTracker`` (raises ``NoTipError`` without one). Never ``has_tip``,
    which includes pending operations."""
    return tracker.get_tip()


def _container_tracker(container):
    """A container's own volume tracker (``Container.tracker``)."""
    return container.tracker


def _tip_tracker(tip):
    """A tip's own volume tracker (``Tip.tracker``)."""
    return tip.tracker


def _has_committed_tip(tracker):
    try:
        _committed_tip(tracker)
    except _plr().NoTipError:
        return False
    return True


def _mounted_tip(head_tracker):
    """The committed tip on a channel's head tracker, or ``None``."""
    if head_tracker is None:
        return None
    try:
        return _committed_tip(head_tracker)
    except _plr().NoTipError:
        return None


def _positions_with_committed_tip(pairs):
    """The indices of ``(index, tip tracker)`` pairs whose tracker holds a COMMITTED tip, in order.
    The one definition of "the channels (or spots) that physically hold a tip" on the 96 path."""
    return [index for index, tracker in pairs if _has_committed_tip(tracker)]


def _committed_channels(head):
    """The channels of a head dict that hold a committed tip, ascending."""
    return _positions_with_committed_tip(sorted(head.items(), key=lambda item: item[0]))


def _tip_error_explainable_on_96(exc):
    """On the 96 path only a ``HasTipError`` can be explained by committed state: a ``NoTipError``
    there arises where a pending check passes and a committed read fails (head ``get_tip`` after a
    refused pick-up, ``TipSpot.get_tip`` after a refused drop), which committed state cannot show."""
    return isinstance(exc, _plr().HasTipError)


def _shortfall(tracker, requested, too_little_liquid):
    """The committed ``available`` when ``requested`` does not fit it, else ``None``. A TLL is short
    when the request exceeds the committed volume, a TLV when it exceeds the committed room."""
    available = _committed_volume(tracker) if too_little_liquid else _committed_room(tracker)
    return available if requested - available > _EPS else None


# --------------------------------------------------------------------------- frames


def _frames(tb):
    out = []
    while tb is not None:
        out.append(tb.tb_frame)
        tb = tb.tb_next
    return out


def _local(frame, name):
    return frame.f_locals.get(name) if frame is not None else None


def _isinstance(value, cls):
    try:
        return isinstance(value, cls)
    except Exception:  # an object with a hostile ``__class__`` is simply not one
        return False


def _seq(value):
    return tuple(value) if isinstance(value, (list, tuple)) else None


def _number(value):
    return None if isinstance(value, bool) or not isinstance(value, (int, float)) else float(value)


def _channel_index(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _subtree(root):
    return [root, *root.get_all_children()]


#: ``_path`` results: the 1-channel path (also the path with no op frame at all) and the 96 path.
PATH_1CH, PATH_96 = "1ch", "96"


def _path(op_frames):
    """Which resolution path the op frames call for (N5659-1): ``PATH_96`` when every op frame is a
    ``*96`` op, ``PATH_1CH`` when none is (or there is no op frame), ``None`` for a mixed stack."""
    kinds = {glossary.is_96(frame.f_code.co_name) for frame in op_frames}
    if kinds == {True}:
        return PATH_96
    return PATH_1CH if kinds <= {False} else None


# --------------------------------------------------------------------------- the 96 locals


def _container_mode(lh, containers):
    """``"per_channel"`` for 96 containers of one parent, ``"single"`` for one container the 96 head
    fits in, else ``None`` (48 or 384 containers, wells of several plates, a container that is too
    small). dispense96 runs its tip loop BEFORE these checks, so a tip error can arrive with any."""
    p = _plr()
    containers = _seq(containers)
    if not containers or not all(_isinstance(c, p.Container) for c in containers):
        return None
    if len(containers) == 96:
        parent = containers[0].parent
        return "per_channel" if parent is not None and all(c.parent is parent for c in containers) else None
    if len(containers) == 1:
        try:
            fits = lh._check_96_head_fits_in_container(containers[0])
        except Exception:  # a hostile handler: not established, so not guessed
            return None
        return "single" if fits else None
    return None


def _op96_inputs(inner, lh, head):
    """The innermost 96 op frame's locals in the 1-channel shape: ``(resources, channels, volumes,
    container_mode)``, one resource per channel, or ``None`` when a local is absent or the container
    list is not one the op's own checks would accept. ``channels`` are those of ``head`` that hold a
    committed tip (aspirate96 / dispense96 / drop_tips96) or whose rack spot does (pick_up_tips96)."""
    p = _plr()
    role = glossary.role_of(inner.f_code.co_name)  # roles, not names: the glossary owns the action strings
    if role in (glossary.ASPIRATE, glossary.DISPENSE):
        containers, volume = _seq(_local(inner, "containers")), _number(_local(inner, "volume"))
        if containers is None or volume is None:
            return None
        mode = _container_mode(lh, containers)
        if mode is None:
            return None
        channels = _committed_channels(head)
        resources = tuple(containers[c] if mode == "per_channel" else containers[0] for c in channels)
        return resources, tuple(channels), (volume,) * len(channels), mode
    if role not in (glossary.PICK_UP, glossary.DROP):
        return None
    rack = _local(inner, "tip_rack" if role == glossary.PICK_UP else "resource")
    if not _isinstance(rack, p.TipRack) or rack.num_items != len(head):
        return None  # the trash (or anything else) has no positions to name
    if role == glossary.PICK_UP:
        pairs = [(c, p.tip_spot_tracker(rack.get_item(c))) for c in sorted(head)]
        channels = _positions_with_committed_tip(pairs)
    else:
        channels = _committed_channels(head)
    return tuple(rack.get_item(c) for c in channels), tuple(channels), (), None


def _op96_labware(inner):
    """The labware the innermost 96 op frame would commit on success, for the residue layer: ``(containers,
    rack)``. ``containers`` is the ``containers`` local of ``aspirate96`` / ``dispense96`` WHOLE (the op
    commits every one of them, not only those under a mounted tip); ``rack`` is the ``tip_rack`` /
    ``resource`` of a pick-up / drop. The other is ``()`` / ``None``. Locals are only named here; their
    state is read by ``residue.of``."""
    role = glossary.role_of(inner.f_code.co_name)
    if role in (glossary.ASPIRATE, glossary.DISPENSE):
        return _seq(_local(inner, "containers")) or (), None
    rack = _local(inner, "tip_rack" if role == glossary.PICK_UP else "resource")
    return (), rack if _isinstance(rack, _plr().TipRack) else None


# --------------------------------------------------------------------------- owners


@dataclasses.dataclass(frozen=True, eq=False)
class _Owner:
    kind: str
    obj: Any
    channel: int | None
    rule: str


def _owner_via_handler(lh, tracker, head):
    """Rules (a), (b), (c): by identity, with an op frame's handler in hand. ``head`` is the channel
    dict of the path: ``lh.head``, or ``lh.head96`` on the 96 path (``lh.head`` is never read there)."""
    p = _plr()
    deck = getattr(lh, "deck", None)
    if _isinstance(tracker, p.VolumeTracker):
        if deck is not None:
            for node in _subtree(deck):
                if isinstance(node, p.Container) and _container_tracker(node) is tracker:
                    return _Owner(OWNER_CONTAINER, node, None, "a")
        for channel, head_tracker in head.items():  # (c): a mounted tip's own tracker
            tip = _mounted_tip(head_tracker)
            if tip is not None and _tip_tracker(tip) is tracker:
                return _Owner(OWNER_TIP, tip, channel, "c")
        return None
    if deck is not None:
        for node in _subtree(deck):
            if isinstance(node, p.TipSpot) and p.tip_spot_tracker(node) is tracker:
                return _Owner(OWNER_TIP_SPOT, node, None, "a")
    for channel, head_tracker in head.items():  # (b)
        if head_tracker is tracker:
            return _Owner(OWNER_CHANNEL, None, channel, "b")
    return None


def _roots(frames, decks):
    """The resource trees the frames reach (a handler's deck, a resource's root), plus ``decks``."""
    p = _plr()
    roots, seen = [], set()

    def add(resource):
        if resource is None:
            return
        root = resource.get_root() if isinstance(resource, p.Resource) else None
        if root is not None and id(root) not in seen:
            seen.add(id(root))
            roots.append(root)

    for deck in decks or ():
        add(getattr(deck, "deck", deck) if _isinstance(deck, p.LiquidHandler) else deck)
    for frame in frames:
        for value in list(frame.f_locals.values()):
            if _isinstance(value, p.LiquidHandler):
                add(getattr(value, "deck", None))
            elif _isinstance(value, p.Resource):
                add(value)
    return roots


def _lookup(name, roots):
    """The one resource called ``name`` on the roots, else ``None`` (none, or ambiguous)."""
    p = _plr()
    found = []
    for root in roots:
        try:
            resource = root.get_resource(name)
        except p.ResourceNotFoundError:
            continue
        if all(resource is not other for other in found):
            found.append(resource)
    return found[0] if len(found) == 1 else None


def _owner_by_name(tracker, roots):
    """Rule (d): with no op frame, parse ``tracker.thing`` (a ``Tip`` match gives no owner)."""
    p = _plr()
    thing = getattr(tracker, "thing", None)
    if not isinstance(thing, str):
        return None
    if _isinstance(tracker, p.TipTracker):
        if thing.startswith(_CHANNEL_PREFIX) and thing[len(_CHANNEL_PREFIX):].isdigit():
            return _Owner(OWNER_CHANNEL, None, int(thing[len(_CHANNEL_PREFIX):]), "d")
        spot = _lookup(thing, roots)
        if isinstance(spot, p.TipSpot) and p.tip_spot_tracker(spot) is tracker:
            return _Owner(OWNER_TIP_SPOT, spot, None, "d")
        return None
    if thing.endswith(_VOLUME_TRACKER_SUFFIX):
        container = _lookup(thing[: -len(_VOLUME_TRACKER_SUFFIX)], roots)
        if isinstance(container, p.Container) and _container_tracker(container) is tracker:
            return _Owner(OWNER_CONTAINER, container, None, "d")
    return None


# --------------------------------------------------------------------------- the committed offending set


def _volume_offenders(exc, owner, lh, tracker, requested_local, resources, channels, volumes, head):
    """Volume errors: containers by summed demand per resource, a tip owner per channel. ``None``
    when a needed local is absent (nothing is guessed)."""
    p = _plr()
    too_little_liquid = isinstance(exc, p.TooLittleLiquidError)
    if lh is None:  # rule (d): the tracker that raised, against its own committed state
        if requested_local is None:
            return None
        available = _shortfall(tracker, requested_local, too_little_liquid)
        return [] if available is None else [Offender(owner.obj, requested_local, available)]
    if owner.kind == OWNER_CONTAINER:
        if resources is None or volumes is None or len(resources) != len(volumes):
            return None
        demand, order = {}, []
        for resource, raw in zip(resources, volumes, strict=True):
            volume = _number(raw)
            if volume is None:
                return None
            if isinstance(resource, p.Container):
                if id(resource) not in demand:
                    demand[id(resource)] = [resource, 0.0]
                    order.append(id(resource))
                demand[id(resource)][1] += volume
        offenders = []
        for key in order:
            resource, requested = demand[key]
            resource_tracker = _container_tracker(resource)
            if resource_tracker.is_disabled:  # PLR does not validate a disabled tracker
                continue
            available = _shortfall(resource_tracker, requested, too_little_liquid)
            if available is not None:
                offenders.append(Offender(resource, requested, available))
        return offenders
    if owner.kind == OWNER_TIP:
        if channels is None or volumes is None or len(channels) != len(volumes):
            return None
        offenders = []
        for channel, raw in zip(channels, volumes, strict=True):
            volume, tip = _number(raw), _mounted_tip(head.get(channel))
            if volume is None or tip is None:
                continue
            available = _shortfall(_tip_tracker(tip), volume, too_little_liquid)
            if available is not None:
                offenders.append(Offender(channel, volume, available))
        return offenders
    return None


def _tip_conflict(exc, has_committed_tip):
    """A ``HasTipError`` needs a committed tip to explain it, a ``NoTipError`` the lack of one."""
    return has_committed_tip if isinstance(exc, _plr().HasTipError) else not has_committed_tip


def _tip_offenders(exc, owner, lh, tracker, inner_name, resources, channels, head, is96=False):
    """HasTip / NoTip: the channels or tip spots whose COMMITTED tip state conflicts with the op."""
    p = _plr()
    has_tip_error = isinstance(exc, p.HasTipError)
    if is96 and not _tip_error_explainable_on_96(exc):
        return None
    if lh is None:  # rule (d): the tracker that raised, against its own committed state
        if not _tip_conflict(exc, _has_committed_tip(tracker)):
            return []
        target = owner.channel if owner.kind == OWNER_CHANNEL else owner.obj
        return [Offender(target, None, None)]
    role = glossary.role_of(inner_name)
    if owner.kind == OWNER_CHANNEL:
        # HasTip on a channel is a pick-up; NoTip on a channel is any op that uses a mounted tip
        if (role != glossary.PICK_UP) if has_tip_error else (role is None or role == glossary.PICK_UP):
            return None
        if channels is None:
            return None
        return [
            Offender(channel, None, None) for channel in channels
            if head.get(channel) is not None and _tip_conflict(exc, _has_committed_tip(head[channel]))
        ]
    if owner.kind == OWNER_TIP_SPOT:
        # HasTip on a spot is a drop-family op; NoTip on a spot is a pick-up
        if role != (glossary.DROP if has_tip_error else glossary.PICK_UP) or resources is None:
            return None
        offenders, seen = [], set()
        for spot in resources:
            if isinstance(spot, p.TipSpot) and id(spot) not in seen:
                seen.add(id(spot))
                if _tip_conflict(exc, _has_committed_tip(p.tip_spot_tracker(spot))):
                    offenders.append(Offender(spot, None, None))
        return offenders
    return None


def _in_set(owner, offenders):
    """Is the owner one of the offenders? Resources by identity, channels (and tips) by index."""
    if owner.kind in (OWNER_CONTAINER, OWNER_TIP_SPOT):
        return next((o for o in offenders if o.target is owner.obj), None)
    return next((o for o in offenders if isinstance(o.target, int) and o.target == owner.channel), None)


# --------------------------------------------------------------------------- resolve


def resolve(exc, tb=None, *, decks=()):
    """The ``ErrorContext`` of a PLR ``TooLittleLiquidError`` / ``TooLittleVolumeError`` /
    ``HasTipError`` / ``NoTipError`` raised with traceback ``tb`` (default ``exc.__traceback__``),
    or ``None`` when no owner can be established from the frames and committed state (any other
    exception, a mixed 1-channel / ``*96`` stack, no owner, or an owner that committed state does not
    explain).

    ``decks`` are extra resources whose trees rule (d) may search when no op frame is on the stack.
    Read-only: no tracker, tip or resource is changed.
    """
    p = _plr()
    if not isinstance(exc, p.FOUR):
        return None
    frames = _frames(tb if tb is not None else getattr(exc, "__traceback__", None))

    # step 2: op frames (an LH ``self`` and a glossary action name); the path they call for (N5659-1)
    actions = glossary.ACTIONS
    op_frames = [
        f for f in frames if f.f_code.co_name in actions and _isinstance(_local(f, "self"), p.LiquidHandler)
    ]
    path = _path(op_frames)
    if path is None:  # a mixed stack: a *96 op and an ordinary op, in either order
        return None
    is96 = path == PATH_96
    inner = op_frames[-1] if op_frames else None
    outer = op_frames[0] if op_frames else None
    lh = _local(inner, "self")
    head = (getattr(lh, "head96" if is96 else "head", None) or {}) if lh is not None else {}
    if is96 and not head:  # no 96 head (never set up, or a backend without one)
        return None
    inner_name = inner.f_code.co_name if inner is not None else None
    action = outer.f_code.co_name if outer is not None else None

    # step 1: the innermost tracker frame below the innermost op frame
    below = frames[frames.index(inner) + 1:] if inner is not None else frames
    tracker_frame = next(
        (f for f in reversed(below) if _isinstance(_local(f, "self"), (p.VolumeTracker, p.TipTracker))), None
    )
    tracker = _local(tracker_frame, "self")
    volume_error = isinstance(exc, (p.TooLittleLiquidError, p.TooLittleVolumeError))
    if tracker is not None and volume_error != isinstance(tracker, p.VolumeTracker):
        return None  # the tracker on the stack is not the kind that raises this error

    # step 3: the owner
    if tracker is not None:
        owner = (
            _owner_via_handler(lh, tracker, head) if lh is not None
            else _owner_by_name(tracker, _roots(frames, decks))
        )
    elif isinstance(exc, p.HasTipError) and lh is not None and not is96:
        channel = _channel_index(_local(inner, "channel"))  # LH:758 raises before any tracker is touched
        owner = None if channel is None else _Owner(OWNER_CHANNEL, None, channel, "e")
    else:
        owner = None
    if owner is None:
        return None

    # step 4: the committed offending set, from the innermost op frame's locals
    container_mode = None
    if is96:
        inputs = _op96_inputs(inner, lh, head)
        if inputs is None:
            return None
        resources, channels, volumes, container_mode = inputs
    else:
        resources = _seq(_local(inner, "resources"))
        if resources is None:
            resources = _seq(_local(inner, "tip_spots"))
        channels, volumes = _seq(_local(inner, "use_channels")), _seq(_local(inner, "vols"))
    if volume_error:
        offenders = _volume_offenders(
            exc, owner, lh, tracker, _number(_local(tracker_frame, "volume")), resources, channels, volumes, head
        )
    else:
        offenders = _tip_offenders(exc, owner, lh, tracker, inner_name, resources, channels, head, is96)
    if offenders is None:
        return None
    own = _in_set(owner, offenders)
    if own is None:  # pending residue (or nothing committed explains the raise): never guess
        return None

    # the residue of the 96 path (N5659-11): read by residue.py, the only module that reads pending state
    queued = ()
    if is96:
        containers, rack = _op96_labware(inner)
        queued = residue.of(lh, containers=containers, rack=rack)

    # step 5
    return ErrorContext(
        error=type(exc).__name__, action=action, op=inner_name, rule=owner.rule,
        owner_kind=owner.kind, owner=owner.obj, channel=owner.channel,
        resources=resources or (), channels=channels or (), volumes=volumes or (),
        offending=tuple(offenders), requested=own.requested, available=own.available,
        head96=is96, container_mode=container_mode, residue=queued,
    )
