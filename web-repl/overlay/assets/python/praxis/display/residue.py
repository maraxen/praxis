"""Pending residue after a refused 96-head op (#5659, task 8; ``261001_nd-next-5659-96head-errors.md``
N5659-11, AC-96-R1..R4).

PyLabRobot 1.0.0b1 queues the tracker changes of its four 96-head ops (``pick_up_tips96``,
``drop_tips96``, ``aspirate96``, ``dispense96``) BEFORE the ``try`` that guards the backend call, and
``rollback()`` runs only when the backend raises (A10). A tracker that refuses the op therefore leaves the
changes it had already queued behind as PENDING state, and the next op that succeeds commits them
(``commit()`` sets ``volume = pending_volume``, A11): from then on the tracked state is wrong, and nothing
in Praxis can recover the truth. This module finds those queued changes so the error panel can say so while
the user can still avoid it. It never changes state (a repair is rejected, D8 "changes no state").

**This is the only display module that reads PENDING state.** Everywhere else in ``praxis/display`` the
rule is committed state only (``context.py``'s AST scan forbids ``has_tip``, and ``errors.py`` draws
``tracker.volume`` and ``get_tip()``), so the two pending readers, ``_pending_volume`` and ``_pending_tip``,
are the only functions that may touch ``pending_volume`` / ``has_tip``; ``test_display_context.py``
(``-k residue96``) scans for exactly that.

**What counts as residue** (a tracker whose pending state differs from its committed state), for the op's
own labware, the state at resolve time (residue from an EARLIER op counts too):

* ``container``: a container of the op whose volume tracker has ``pending_volume != volume`` (the ``containers``
  of ``aspirate96`` / ``dispense96``; the op commits every one of them on success);
* ``tip``: a mounted tip (the COMMITTED tip of a ``head96`` channel) whose own volume tracker differs (aspirate96
  :2017/:2046 and dispense96 :2163 queue on the tips, which round 1 missed);
* ``channel``: a ``head96`` channel whose pending tip presence differs from its committed one;
* ``spot``: a spot of the op's tip rack (``pick_up_tips96`` / ``drop_tips96``) likewise.

Disabled trackers are skipped (PLR neither queues nor commits on them). ``of`` never raises: a failure gives
no residue, never a broken error panel.

Plain CPython: no PLR, IPython or ``js`` import at import time. The two PLR names are resolved inside a
function from the pin's non-shim homes (``pylabrobot.legacy.tip_tracker``, ``pylabrobot.resources.errors``).
"""

from __future__ import annotations

import dataclasses
import functools
import logging
import types

__all__ = ["KIND_CONTAINER", "KIND_TIP", "KIND_CHANNEL", "KIND_SPOT", "Residue", "of"]

log = logging.getLogger("praxis.display")

#: ``Residue.target`` is a container (a well, a trough) of the op.
KIND_CONTAINER = "container"
#: ``Residue.target`` is a channel index: the tip mounted on it has a pending volume.
KIND_TIP = "tip"
#: ``Residue.target`` is a channel index: its tracker's pending tip presence differs from the committed one.
KIND_CHANNEL = "channel"
#: ``Residue.target`` is a ``TipSpot`` of the op's rack.
KIND_SPOT = "spot"

_EPS = 1e-6  # PLR's own tolerance (volume_tracker.py:101, :116)


@dataclasses.dataclass(frozen=True, eq=False)
class Residue:
    """One tracker with queued changes: ``kind`` is a ``KIND_*``, ``target`` the resource or channel index."""

    kind: str
    target: object


@functools.cache
def _plr():
    from pylabrobot.legacy.tip_tracker import tip_spot_tracker
    from pylabrobot.resources.errors import NoTipError

    return types.SimpleNamespace(tip_spot_tracker=tip_spot_tracker, NoTipError=NoTipError)


# --------------------------------------------------------------------------- the only pending readers


def _pending_volume(tracker):
    """The volume including queued operations (``VolumeTracker.pending_volume``)."""
    return tracker.pending_volume


def _pending_tip(tracker):
    """Whether the tracker holds a tip, queued operations included (``TipTracker.has_tip``)."""
    return tracker.has_tip


# --------------------------------------------------------------------------- committed readers


def _committed_volume(tracker):
    return tracker.volume


def _has_committed_tip(tracker):
    try:
        tracker.get_tip()
    except _plr().NoTipError:
        return False
    return True


# --------------------------------------------------------------------------- pending != committed


def _volume_differs(tracker) -> bool:
    if tracker.is_disabled:  # PLR queues and commits nothing on a disabled tracker
        return False
    return abs(_pending_volume(tracker) - _committed_volume(tracker)) > _EPS


def _tip_differs(tracker) -> bool:
    if tracker.is_disabled:
        return False
    return _pending_tip(tracker) != _has_committed_tip(tracker)


# --------------------------------------------------------------------------- the four kinds of residue


def _container_items(containers) -> tuple:
    """The op's containers (each once, in op order) whose volume tracker has queued changes."""
    seen, out = set(), []
    for container in containers:
        if id(container) in seen:
            continue
        seen.add(id(container))
        if _volume_differs(container.tracker):
            out.append(Residue(KIND_CONTAINER, container))
    return tuple(out)


def _mounted_tip_items(head) -> tuple:
    """The channels whose COMMITTED tip has a volume tracker with queued changes, ascending."""
    out = []
    for channel in sorted(head):
        try:
            tip = head[channel].get_tip()
        except _plr().NoTipError:
            continue
        if _volume_differs(tip.tracker):
            out.append(Residue(KIND_TIP, channel))
    return tuple(out)


def _channel_items(head) -> tuple:
    """The head channels whose tip presence has queued changes, ascending."""
    return tuple(Residue(KIND_CHANNEL, channel) for channel in sorted(head) if _tip_differs(head[channel]))


def _spot_items(rack) -> tuple:
    """The spots of the op's tip rack whose tip presence has queued changes, in rack order."""
    tracker_of = _plr().tip_spot_tracker
    return tuple(Residue(KIND_SPOT, spot) for spot in rack.get_all_items() if _tip_differs(tracker_of(spot)))


def of(lh, *, containers=(), rack=None) -> tuple:
    """The queued changes PLR left on the op's trackers: ``Residue`` records, containers (in op order), then
    mounted tips, head channels and rack spots (each ascending). ``containers`` are the ``containers`` of an
    ``aspirate96`` / ``dispense96``, ``rack`` the tip rack of a ``pick_up_tips96`` / ``drop_tips96``; the head
    is ``lh.head96``. Read-only. ``()`` when there is none, and on any failure (never raises)."""
    try:
        head = getattr(lh, "head96", None) or {}
        found = [*_container_items(containers), *_mounted_tip_items(head), *_channel_items(head)]
        if rack is not None:
            found += _spot_items(rack)
        return tuple(found)
    except Exception:  # noqa: BLE001 -- a broken detector must never break an error display
        log.debug("residue: detection failed", exc_info=True)
        return ()
