"""Kernel-side staleness for ``praxis.display`` (task B7; spec D7, D2, section 4, AC-18).

Every resource output is stamped with a per-resource ``rev`` that ``stale.py`` holds, the display
session id and the execution count (D2). When something a drawn output shows changes, the kernel
tells the shell with ONE typed message on the existing ``praxis_repl`` BroadcastChannel; the shell
marks the older outputs in the DOM (``stale.js``, B9). Nothing here touches a notebook model.

**What counts as a change (D7, Revision 10).** At the pin a PLR callback does not always mean a
change: ``VolumeTracker.rollback()`` fires callbacks, so a failed aspirate or dispense fires them on
every op resource although the committed state is unchanged, and a tip pick-up fires ``did_unassign``
once per tip on the rack and on the deck. So a callback only marks every drawn ancestor **dirty**;
a dirty resource is **settled** by recomputing its ``state_digest`` (the sha256 of exactly what an
ordinary output draws), and ``rev`` increments only when the digest differs from the stored one.
Settling is lazy: the intermediate pending states of a failing op (70, 40, 10, then back to 100) are
never digested.

* ``state_digest(resource)``: per container in the subtree ``(name, tracker.get_used_volume())``
  (pending included, as the figure draws it); per tip spot ``(name, spot.tip is not None)`` (the
  tree, never the docstring-deprecated ``spot.tracker`` / ``spot.has_tip()``); and the structure of
  the subtree (each child's name, parent and location).
* ``DisplaySession.draw(resource)``: subscribe (idempotently), settle, return the rev to stamp. It
  settles even if no callback marked the resource dirty, so a stamp always matches what its output
  draws even if a state change made no callback.
* Announcements: PLR callbacks schedule ``loop.call_later(0.1, ...)`` (a debounce: each callback
  restarts it). The timer, and ``post_run_cell`` when IPython fires it, both run ``flush()``, which
  settles every dirty resource FIRST and then builds the message from the revs that changed. Under
  S3-D ``post_run_cell`` does not fire for top-level-``await`` cells, so the timer alone must work.

**Message** (D7): ``{type: "praxis:resource-changed", json: "<string>"}``, built flat with
``js.Object.fromEntries`` as ``praxis_bootstrap._post`` does (:func:`make_repl_poster`). ``json``
encodes ``{"session", "exec", "revs": {"<name>": <rev>}}`` and is capped at 4 KiB; past the cap the
``revs`` map is replaced by ``"all": true`` (:func:`announcement_json`). ``exec`` is the execution
count read when the first change of the batch was seen (the cell that made it), so a debounced
announcement that runs after the next cell has started still names the right cell.

**Imports.** Plain CPython and Pyodide: the standard library only at import time. The PyLabRobot
classes are resolved INSIDE :func:`state_digest`; ``import js`` appears inside
:func:`make_repl_poster` and nowhere else. The channel name is spelled in this module only.

**A callback never breaks a liquid-handling call.** PLR runs these callbacks inside its tracker
operations, so every callback body is guarded and logs instead of raising; a poster that raises is
logged and the announcement is retried at the next flush.
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import logging
import secrets
import weakref
from collections.abc import Callable
from typing import Any

__all__ = [
    "CHANNEL",
    "MESSAGE_TYPE",
    "JSON_CAP",
    "DEBOUNCE_SECONDS",
    "new_session_id",
    "state_digest",
    "announcement_json",
    "make_repl_poster",
    "DisplaySession",
]

#: The existing device-authorization channel (D7). Spelled here and nowhere else in praxis/display.
CHANNEL = "praxis_repl"
#: The one message type this module posts (no session message, D7).
MESSAGE_TYPE = "praxis:resource-changed"
#: Cap on the ``json`` field, in bytes (D7).
JSON_CAP = 4096
#: The announcer's debounce, in seconds (S3-D).
DEBOUNCE_SECONDS = 0.1

log = logging.getLogger(__name__)


def new_session_id() -> str:
    """A random display session id (D2): minted once per kernel process by ``install()``."""
    return secrets.token_hex(8)


# --------------------------------------------------------------------------- the digest


def _plr():
    """The PLR classes the digest dispatches on, resolved when first needed, never at import."""
    from pylabrobot.resources import Container, TipSpot

    return Container, TipSpot


def _num(value) -> float:
    """A float rounded below anything a figure can draw; ``+ 0.0`` turns ``-0.0`` into ``0.0``."""
    return round(float(value), 6) + 0.0


def _location(node):
    loc = node.location
    return None if loc is None else [_num(loc.x), _num(loc.y), _num(loc.z)]


def state_digest(resource) -> str:
    """The sha256 (hex) of a canonical serialisation of what an ordinary output of ``resource`` draws.

    For each container in the subtree (the resource included) ``(name, get_used_volume())``, pending
    operations included because the figure draws them; for each tip spot ``(name, spot.tip is not
    None)``; and the subtree's structure, each descendant's ``(name, parent name, location)``. The tip
    a spot holds is the spot's state, so it is not listed again as structure.
    """
    container_cls, spot_cls = _plr()
    nodes = [resource, *resource.get_all_children()]
    entries: list[list[Any]] = []
    for node in nodes:
        if isinstance(node, container_cls):
            entries.append(["c", node.name, _num(node.tracker.get_used_volume())])
        elif isinstance(node, spot_cls):
            entries.append(["t", node.name, node.tip is not None])
    for node in nodes[1:]:
        parent = node.parent
        if isinstance(parent, spot_cls):
            continue
        entries.append(["s", node.name, None if parent is None else parent.name, _location(node)])
    entries.sort(key=lambda e: (e[0], e[1], json.dumps(e[2:])))
    canonical = json.dumps(entries, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


# --------------------------------------------------------------------------- the message


def announcement_json(session: str, exec_count: int | None, revs: dict[str, int]) -> str:
    """The ``json`` field of the announcement, at most :data:`JSON_CAP` bytes.

    ``{"session", "exec", "revs"}``; past the cap the ``revs`` map is replaced by ``"all": true``.
    """
    full = json.dumps({"session": session, "exec": exec_count, "revs": revs}, separators=(",", ":"))
    if len(full.encode("utf-8")) <= JSON_CAP:
        return full
    return json.dumps({"session": session, "exec": exec_count, "all": True}, separators=(",", ":"))


def make_repl_poster(channel_name: str = CHANNEL) -> Callable[[str], None]:
    """Build a ``post(json_str)`` bound to a real BroadcastChannel. Kernel-only.

    ``import js`` lives here and nowhere else in this module, as in ``viz/browser.py``. The message is
    ``{type: "praxis:resource-changed", json: <the string>}``, built flat with ``js.Object.fromEntries``
    as ``praxis_bootstrap._post`` does (both constructor forms, as there).
    """
    import js  # noqa: PLC0415 - deliberately local; see docstring

    try:
        channel = js.BroadcastChannel.new(channel_name)
    except Exception:
        channel = js.BroadcastChannel(channel_name)

    def post(payload: str) -> None:
        channel.postMessage(js.Object.fromEntries([("type", MESSAGE_TYPE), ("json", payload)]))

    return post


# --------------------------------------------------------------------------- the session


class _Record:
    """One drawn resource: the object, its rev, the digest that rev was taken at, and dirtiness."""

    __slots__ = ("digest", "dirty", "obj", "rev")

    def __init__(self, obj, digest: str):
        self.obj = obj
        self.rev = 0
        self.digest = digest
        self.dirty = False


class DisplaySession:
    """Revs, subscriptions and the debounced announcer for one kernel's display session.

    ``post`` is an injected ``post(str)`` (see :func:`make_repl_poster`). ``loop`` is anything with
    ``call_later(delay, cb) -> handle`` and ``handle.cancel()``; ``None`` resolves the running asyncio
    loop when a callback fires, and with no loop at all only ``flush`` / ``post_run_cell`` announce.
    ``exec_count`` is an injected ``() -> int | None`` (``get_ipython().execution_count`` in the
    kernel).
    """

    def __init__(
        self,
        post: Callable[[str], None],
        *,
        loop=None,
        exec_count: Callable[[], int | None] | None = None,
        session_id: str | None = None,
        debounce: float = DEBOUNCE_SECONDS,
    ):
        self._post = post
        self._loop = loop
        self._exec_count = exec_count
        self._debounce = debounce
        self.session_id: str = session_id or new_session_id()
        self._records: dict[str, _Record] = {}
        #: ids of every resource with a state callback registered (idempotency; PLR appends).
        self._subscribed: set[int] = set()
        #: ids of every drawn root with structure callbacks registered.
        self._structural: set[int] = set()
        self._changed: set[str] = set()
        self._batch_open = False
        self._batch_exec: int | None = None
        self._timer = None

    # -- drawing --------------------------------------------------------------

    def draw(self, resource) -> int:
        """Register ``resource`` as drawn and return the rev its output must carry.

        Subscribes to it and every descendant and to its structural changes (once each), and settles
        it (recomputes the digest, bumping ``rev`` if what it draws changed) BEFORE the caller
        renders, so the stamp always matches the figure.
        """
        name = resource.name
        record = self._records.get(name)
        if record is None:
            self._subscribe(resource)
            self._watch_structure(resource)
            record = self._records[name] = _Record(resource, state_digest(resource))
            return record.rev
        if record.obj is not resource:
            # A different object under a drawn name: the rev keeps counting, never restarts.
            self._subscribe(resource)
            self._watch_structure(resource)
            record.obj = resource
        self._settle(name, record)
        return record.rev

    def note_output(self, stamp: dict[str, Any], resource=None) -> int | None:
        """Register a drawn output by its stamp. A stamp with ``resource`` or ``rev`` null (a ledger
        or error stamp, D2) subscribes nothing and never enters an announcement: returns ``None``.
        """
        if stamp.get("resource") is None or stamp.get("rev") is None:
            return None
        if resource is None:
            raise ValueError(f"stamp names {stamp['resource']!r} but no resource was given to subscribe to")
        return self.draw(resource)

    def render_kwargs(self, resource) -> dict[str, Any]:
        """``rev``, ``session`` and ``exec_count`` for ``labware.render`` (D2). Settles first."""
        return {"rev": self.draw(resource), "session": self.session_id, "exec_count": self._current_exec()}

    def rev_of(self, name: str) -> int | None:
        """The stored rev of a drawn resource (no settling), or ``None`` if it was never drawn."""
        record = self._records.get(name)
        return None if record is None else record.rev

    # -- announcing -----------------------------------------------------------

    def post_run_cell(self, *_args) -> str | None:
        """The IPython ``post_run_cell`` hook: flush now (cancelling the pending timer)."""
        return self.flush()

    def flush(self) -> str | None:
        """Settle every dirty resource, then post the changed revs (one message), if any.

        Returns the ``json`` string posted, or ``None`` when nothing changed or the post failed (a
        failed post is logged and retried at the next flush).
        """
        self._cancel_timer()
        for name in sorted(n for n, r in self._records.items() if r.dirty):
            self._settle(name, self._records[name])
        if not self._changed:
            self._end_batch()
            return None
        exec_count = self._batch_exec if self._batch_open else self._current_exec()
        revs = {n: self._records[n].rev for n in sorted(self._changed)}
        payload = announcement_json(self.session_id, exec_count, revs)
        try:
            self._post(payload)
        except Exception as exc:
            log.warning("display staleness announcement failed (retried at the next flush): %s", exc)
            return None
        self._changed.clear()
        self._end_batch()
        return payload

    # -- internals ------------------------------------------------------------

    def _current_exec(self) -> int | None:
        if self._exec_count is None:
            return None
        try:
            return self._exec_count()
        except Exception as exc:
            log.warning("display exec_count failed: %s", exc)
            return None

    def _end_batch(self) -> None:
        self._batch_open = False
        self._batch_exec = None

    def _settle(self, name: str, record: _Record) -> bool:
        """Recompute the digest; bump ``rev`` only if it differs. Also picks up new descendants."""
        self._subscribe(record.obj)
        digest = state_digest(record.obj)
        record.dirty = False
        if digest == record.digest:
            return False
        record.digest = digest
        record.rev += 1
        self._changed.add(name)
        return True

    def _subscribe(self, resource) -> None:
        """State callbacks on ``resource`` and every descendant, once each (via ``_subscribed``)."""
        _container, spot_cls = _plr()
        for node in (resource, *resource.get_all_children()):
            if id(node) in self._subscribed or isinstance(node.parent, spot_cls):
                continue  # a tip resting in a spot is the spot's state, not a resource to watch
            self._subscribed.add(id(node))
            weakref.finalize(node, self._subscribed.discard, id(node))
            node.register_state_update_callback(functools.partial(self._on_change, weakref.ref(node)))

    def _watch_structure(self, resource) -> None:
        """Assign / unassign callbacks on a drawn root (they propagate up from every descendant)."""
        if id(resource) in self._structural:
            return
        self._structural.add(id(resource))
        weakref.finalize(resource, self._structural.discard, id(resource))
        callback = functools.partial(self._on_change, weakref.ref(resource))
        resource.register_did_assign_resource_callback(callback)
        resource.register_did_unassign_resource_callback(callback)

    def _on_change(self, ref, *_args) -> None:
        """A PLR callback: mark every drawn ancestor dirty and schedule the announcer. Never raises."""
        try:
            node = ref()
            marked = False
            while node is not None:
                record = self._records.get(node.name)
                if record is not None and record.obj is node:
                    record.dirty = marked = True
                node = node.parent
            if not marked:
                return
            if not self._batch_open:
                self._batch_open = True
                self._batch_exec = self._current_exec()
            self._schedule()
        except Exception:
            log.exception("display staleness callback failed")

    def _resolve_loop(self):
        if self._loop is not None:
            return self._loop
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None

    def _schedule(self) -> None:
        loop = self._resolve_loop()
        if loop is None:
            return
        self._cancel_timer()
        try:
            self._timer = loop.call_later(self._debounce, self._on_timer)
        except Exception as exc:
            self._timer = None
            log.warning("display staleness announcer could not be scheduled: %s", exc)

    def _cancel_timer(self) -> None:
        timer, self._timer = self._timer, None
        if timer is not None:
            timer.cancel()

    def _on_timer(self) -> None:
        self._timer = None
        try:
            self.flush()
        except Exception:
            log.exception("display staleness announcer failed")
