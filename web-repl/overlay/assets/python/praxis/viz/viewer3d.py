"""``DockedViewer3D`` -- PyLabRobot's 3D ``Viewer3D`` talking to the docked deck panel (task C3; spec D11).

The 1.0.0b1 pin ships ``pylabrobot.visualizer3D`` and the REPL's PLR wheel already contains it, so
this module imports it and subclasses ``server.Viewer3D``. No PLR Python is copied and none is edited.
What Pyodide cannot do is what the stock class does in ``start``: bind a websocket server and an HTTP
file server, start threads and open a browser. The page it would serve is vendored statically instead
(``assets/visualizer3d/``), and its one ``new WebSocket(...)`` is replaced in that iframe by the
socket shim (``assets/visualizer3d-augmentations/socket.js``), a WebSocket-shaped class over the
BroadcastChannel ``praxis_viz3d``. This module is the kernel end of that channel.

GATE X (the same discipline as ``browser.py``): ``DockedViewer3D`` overrides exactly ``__init__``,
``start`` and ``stop`` of ``Viewer3D``. ``_handler``, ``_broadcast``, ``_flush``, ``_enqueue``, the
scene debounce, ``_on_client_message`` (hello) and every subscription path are inherited unchanged: a
``VirtualConnection`` per page client stands in for the websocket the inherited ``_handler`` expects.
A fourth override is a design regression -- stop and upstream a transport hook to PLR instead. The one
deliberate deviation from stock PLR state is the ``PACKAGE_ROOT`` rebind (``_ensure_package_root``).

Protocol on the channel (every message is a JSON string; field names match ``socket.js`` and
``shell/display/dock.js``):

=======  =================  =====================================================================
kind     direction          fields
=======  =================  =====================================================================
query    shell -> kernel    none. Answered with ``announce`` by a live viewer.
announce kernel -> all      ``viewer``, ``deck``, ``session``
open     page -> kernel     ``viewer``, ``client``
accept   kernel -> page     ``viewer``, ``client``; then ``scene`` and ``state`` arrive as ``msg``
msg      both               ``viewer``, ``client``, ``data`` (the exact string a websocket carries)
bye      page -> kernel     ``viewer``, ``client``: that client is gone
evict    kernel -> page     ``viewer``, ``client``: the kernel dropped this client at the cap
close    kernel -> all      ``viewer``, ``reason``: the viewer stopped
=======  =================  =====================================================================

Threat model: the origin is the boundary (spec D11), so there is no nonce. Inbound bounds instead:
at most ``MAX_CLIENTS`` virtual clients, and at the cap a new ``open`` evicts the OLDEST one (orphans
from routine reloads would otherwise fill the cap, because a BroadcastChannel post never fails, so the
stock evict-on-send-failure path never fires). A message that is not a JSON object, or whose ``kind``
is unknown or whose ids are malformed, is dropped without an exception (logged at debug level).

``import js`` appears only inside ``make_viz3d_channel()``, as in ``browser.py``, so everything else
here runs under plain CPython with an injected channel.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import logging
import secrets
import shutil
import sys
import tempfile
from typing import Any, Callable, Dict, Optional, Protocol, Set

import pylabrobot.visualizer3D.server as _plr_server

logger = logging.getLogger(__name__)

#: The 3D viewer's BroadcastChannel. Not ``praxis_viz`` (whose receiver would misread these envelopes)
#: and not ``praxis_repl`` (R21).
VIZ3D_CHANNEL = "praxis_viz3d"

KIND_QUERY = "query"
KIND_ANNOUNCE = "announce"
KIND_OPEN = "open"
KIND_ACCEPT = "accept"
KIND_MSG = "msg"
KIND_BYE = "bye"
KIND_EVICT = "evict"
KIND_CLOSE = "close"

#: Virtual clients kept at once; a fifth ``open`` evicts the oldest (D11 "Inbound bounds").
MAX_CLIENTS = 4
#: Longest viewer / client id accepted, matching ``dock.js`` (MAX_ID).
MAX_ID = 200
#: Longest deck name / session id put in an ``announce``, so it stays far under ``dock.js``'s
#: 4096-character message cap whatever the deck is called.
MAX_LABEL = 200
#: ``dock()`` waits this long (seconds) for the page's first hello.
BROWSER_WAIT_S = 15
#: ``stop()`` waits this long (seconds) for the handler tasks to end before cancelling them.
STOP_TIMEOUT_S = 5.0
CLOSE_REASON = "stopped"
#: The display session id used when ``praxis.display`` is not installed (``display/errors.py`` default).
UNSET_SESSION = "unset"

#: Ends a ``VirtualConnection``'s async iteration. Never a string, so no client message can be it.
_END = object()


class ChannelTransport(Protocol):
    """What ``DockedViewer3D`` requires of its channel (injected; ``make_viz3d_channel`` is the real one).

    ``post`` takes the already-serialized JSON string, like ``transport.py``'s posters. A listener gets
    whatever the channel delivered (the message's ``data``); the viewer ignores anything but a string.
    """

    def post(self, message: str) -> None: ...

    def add_listener(self, listener: Callable[[Any], None]) -> None: ...

    def remove_listener(self, listener: Callable[[Any], None]) -> None: ...

    def close(self) -> None: ...


class _JsChannel:
    """A real ``BroadcastChannel`` (kernel only). Constructed by ``make_viz3d_channel``."""

    def __init__(self, channel: Any, create_proxy: Callable[[Any], Any]) -> None:
        self._channel = channel
        self._create_proxy = create_proxy
        self._proxies: Dict[Any, Any] = {}

    def post(self, message: str) -> None:
        self._channel.postMessage(message)

    def add_listener(self, listener: Callable[[Any], None]) -> None:
        def on_message(event: Any) -> None:
            listener(event.data)

        proxy = self._create_proxy(on_message)
        self._proxies[listener] = proxy
        self._channel.addEventListener("message", proxy)

    def remove_listener(self, listener: Callable[[Any], None]) -> None:
        proxy = self._proxies.pop(listener, None)
        if proxy is not None:
            self._channel.removeEventListener("message", proxy)
            proxy.destroy()

    def close(self) -> None:
        for listener in list(self._proxies):
            self.remove_listener(listener)
        self._channel.close()


def make_viz3d_channel(name: str = VIZ3D_CHANNEL) -> ChannelTransport:
    """Open a real BroadcastChannel. Kernel-only: ``import js`` lives here and nowhere else."""
    import js  # noqa: PLC0415 - deliberately local; see the module docstring
    from pyodide.ffi import create_proxy  # noqa: PLC0415

    return _JsChannel(js.BroadcastChannel.new(name), create_proxy)


class VirtualConnection:
    """The websocket the inherited ``Viewer3D._handler`` expects, for one page client.

    ``send`` posts a ``msg`` envelope; async iteration yields the strings the page sent (fed by the
    viewer's channel listener) and ends when ``end()`` queues the sentinel (``bye``, eviction, stop).
    After ``end()`` a ``send`` is a no-op: nothing is posted to a client that has left.
    """

    def __init__(self, viewer: str, client: str, post: Callable[[Dict[str, Any]], None]) -> None:
        self.viewer = viewer
        self.client = client
        self._post = post
        self._queue: "asyncio.Queue[Any]" = asyncio.Queue()
        self._ended = False

    @property
    def ended(self) -> bool:
        return self._ended

    async def send(self, message: str) -> None:
        if self._ended:
            return
        self._post({"kind": KIND_MSG, "viewer": self.viewer, "client": self.client, "data": message})

    def feed(self, message: str) -> None:
        if not self._ended:
            self._queue.put_nowait(message)

    def end(self) -> None:
        if not self._ended:
            self._ended = True
            self._queue.put_nowait(_END)

    def __aiter__(self) -> "VirtualConnection":
        return self

    async def __anext__(self) -> str:
        item = await self._queue.get()
        if item is _END:
            raise StopAsyncIteration
        return item


_package_root_rebound = False


def _ensure_package_root() -> None:
    """Rebind ``server.PACKAGE_ROOT`` to an empty directory this module owns, once.

    The stock root is the installed PLR package, which at the pin holds 63 ``.glb`` files;
    ``_models_on_disk(PACKAGE_ROOT)`` would find them, and any whose name matches a scene model would
    become a ``mesh`` whose ``mesh/<id>`` URL nothing serves. Meshes are unsupported here, so every
    model stays a box. This is the ONE deliberate runtime rebinding of PLR state (a module global, not
    an override, so GATE X holds). Guarded and idempotent: the first call sets the global and the flag,
    every later call returns at once. Called first in ``DockedViewer3D.__init__``, never at import.
    """
    global _package_root_rebound
    if _package_root_rebound:
        return
    owned = tempfile.mkdtemp(prefix="praxis-viz3d-")
    atexit.register(shutil.rmtree, owned, ignore_errors=True)
    _plr_server.PACKAGE_ROOT = owned
    _package_root_rebound = True


def _display_session() -> str:
    """The display session id if ``praxis.display`` is installed in this process, else ``"unset"``.

    Looked up in ``sys.modules`` and never imported: this must not pull the display layer (or, under
    CPython, some other ``praxis`` package) in as a side effect.
    """
    install = sys.modules.get("praxis.display.install")
    process_session = getattr(install, "_process_session", None)
    try:
        session = process_session() if callable(process_session) else None
    except Exception:  # noqa: BLE001 - a label, never worth failing a dock() for
        session = None
    return session if isinstance(session, str) and session else UNSET_SESSION


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= MAX_ID


class DockedViewer3D(_plr_server.Viewer3D):
    """``Viewer3D`` over ``praxis_viz3d``. Overrides exactly ``__init__``, ``start`` and ``stop``.

    Args:
      root: the resource that is the world, as for ``Viewer3D``.
      channel_factory: returns the channel (``ChannelTransport``); default ``make_viz3d_channel``.
        Called by ``start``, so a viewer that was never started holds no channel.
      session: the display session id put in ``announce``; default the process's, or ``"unset"``.
      **kwargs: forwarded to ``Viewer3D.__init__`` (``open_browser`` is forced off: there is no server).

    ``viewer_id`` is the id minted for this viewer; the page learns it from ``announce``.
    """

    def __init__(
        self,
        root: Any,
        *,
        channel_factory: Optional[Callable[[], ChannelTransport]] = None,
        session: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        _ensure_package_root()
        kwargs["open_browser"] = False
        super().__init__(root, **kwargs)
        self.viewer_id = "v-" + secrets.token_hex(8)
        self.session = session if session else _display_session()
        self._channel_factory = channel_factory if channel_factory is not None else make_viz3d_channel
        self._channel: Optional[ChannelTransport] = None
        # Insertion-ordered (client id -> connection): ``_clients`` is a set, so the oldest client is
        # found here. Removal from ``_clients`` on eviction and ``bye`` is synchronous, before the new
        # client's ``_handler`` has run a step.
        self._virtual: Dict[str, VirtualConnection] = {}
        self._handler_tasks: Set["asyncio.Task[None]"] = set()
        self._started = False
        self._stopped = False

    # --- override 1 of 3 (__init__ above) --------------------------------------------------------

    # --- override 2 of 3 -------------------------------------------------------------------------
    async def start(self) -> None:
        """Copy of stock ``start`` without servers, threads, pre-warm and browser; then subscribe.

        ``legacy_size`` runs synchronously (Pyodide has no threads, and ``asyncio.to_thread`` needs
        them). ``_models_on_disk`` is not pre-warmed: its first call is the inherited scene build.
        """
        if self._stopped:
            raise RuntimeError("a stopped DockedViewer3D cannot be started again; make a new one")
        if self._started:
            return
        self._loop = asyncio.get_running_loop()
        self._browser_drawing = asyncio.Event()
        self._legacy_bytes = _plr_server.legacy_size(self.root)
        channel = self._channel_factory()
        channel.add_listener(self._on_channel_message)
        self._channel = channel
        self._started = True
        self.announce()

    # --- override 3 of 3 -------------------------------------------------------------------------
    async def stop(self) -> None:
        """Stop listening to the tree, end every connection, post ``close``, leave the channel.

        Idempotent: a second call (or a concurrent one) returns at once and posts nothing. A stopped
        viewer answers no ``query`` and accepts no ``open``.
        """
        if self._stopped:
            return
        self._stopped = True
        channel = self._channel
        try:
            await super().stop()  # skips the servers it does not have (they are None)
            for connection in list(self._virtual.values()):
                connection.end()
            self._virtual.clear()
            tasks = list(self._handler_tasks)
            if tasks:
                _, pending = await asyncio.wait(tasks, timeout=STOP_TIMEOUT_S)
                for task in pending:
                    task.cancel()
                if pending:
                    await asyncio.wait(pending, timeout=1.0)
            if self._started:
                self._post({"kind": KIND_CLOSE, "viewer": self.viewer_id, "reason": CLOSE_REASON})
        finally:
            self._channel = None
            if channel is not None:
                try:
                    channel.remove_listener(self._on_channel_message)
                finally:
                    channel.close()

    # --- not overrides: channel side -------------------------------------------------------------
    def announce(self) -> None:
        """Tell the shell this viewer exists (`announce {viewer, deck, session}`)."""
        self._post({
            "kind": KIND_ANNOUNCE,
            "viewer": self.viewer_id,
            "deck": str(self.root.name)[:MAX_LABEL],
            "session": str(self.session)[:MAX_LABEL],
        })

    def _post(self, message: Dict[str, Any]) -> None:
        """Post one envelope; a failing post is logged, never raised (the lifecycle must go on)."""
        try:
            self._post_strict(message)
        except Exception:  # noqa: BLE001
            logger.warning("praxis_viz3d: a %r post failed", message.get("kind"), exc_info=True)

    def _post_strict(self, message: Dict[str, Any]) -> None:
        channel = self._channel
        if channel is not None:
            channel.post(json.dumps(message))

    def _on_channel_message(self, raw: Any) -> None:
        """The channel listener. Never raises into the channel: junk is dropped and logged at debug."""
        if self._stopped or self._channel is None:
            return
        try:
            self._dispatch(raw)
        except Exception:  # noqa: BLE001
            logger.warning("praxis_viz3d: handling a message failed", exc_info=True)

    def _dispatch(self, raw: Any) -> None:
        if not isinstance(raw, str):
            logger.debug("praxis_viz3d: dropped a non-string message (%s)", type(raw).__name__)
            return
        try:
            message = json.loads(raw)
        except ValueError:
            logger.debug("praxis_viz3d: dropped a message that is not JSON")
            return
        if not isinstance(message, dict):
            logger.debug("praxis_viz3d: dropped a message that is not a JSON object")
            return
        kind = message.get("kind")
        if kind == KIND_QUERY:
            self.announce()
            return
        if kind not in (KIND_OPEN, KIND_BYE, KIND_MSG):
            logger.debug("praxis_viz3d: dropped a message of unknown kind %r", kind if isinstance(kind, str) else None)
            return
        client = message.get("client")
        if message.get("viewer") != self.viewer_id or not _valid_id(client):
            logger.debug("praxis_viz3d: dropped a %s for another viewer or with a bad client id", kind)
            return
        if kind == KIND_OPEN:
            self._open_client(client)
        elif kind == KIND_BYE:
            self._drop_client(client)
        else:
            connection = self._virtual.get(client)
            data = message.get("data")
            if connection is not None and isinstance(data, str):
                connection.feed(data)
            else:
                logger.debug("praxis_viz3d: dropped a msg for an unknown client or with non-string data")

    def _open_client(self, client: str) -> None:
        if client in self._virtual:
            logger.debug("praxis_viz3d: ignored a second open for a live client")
            return
        while len(self._virtual) >= MAX_CLIENTS:
            oldest = next(iter(self._virtual))
            evicted = self._virtual.pop(oldest)
            self._clients.discard(evicted)  # synchronously: before the new handler can add itself
            self._post({"kind": KIND_EVICT, "viewer": self.viewer_id, "client": oldest})
            evicted.end()
        connection = VirtualConnection(self.viewer_id, client, self._post_strict)
        self._virtual[client] = connection
        self._post({"kind": KIND_ACCEPT, "viewer": self.viewer_id, "client": client})
        assert self._loop is not None  # set by start(); a stopped viewer never gets here
        task = self._loop.create_task(self._handler(connection))
        self._handler_tasks.add(task)
        task.add_done_callback(lambda t, c=client, conn=connection: self._handler_done(t, c, conn))

    def _drop_client(self, client: str) -> None:
        connection = self._virtual.pop(client, None)
        if connection is not None:
            self._clients.discard(connection)
            connection.end()

    def _handler_done(self, task: "asyncio.Task[None]", client: str, connection: VirtualConnection) -> None:
        self._handler_tasks.discard(task)
        self._clients.discard(connection)
        if self._virtual.get(client) is connection:
            del self._virtual[client]
        if not task.cancelled() and task.exception() is not None:
            logger.debug("praxis_viz3d: a client handler ended with %r", task.exception())


#: The viewer ``dock()`` made last, stopped first by the next ``dock()``.
_current_viewer: Optional[DockedViewer3D] = None


async def dock(deck: Any, **kw: Any) -> DockedViewer3D:
    """Start a ``DockedViewer3D`` on ``deck`` for the deck panel; return it.

    If an earlier ``dock()`` left a viewer, it is stopped first (so re-running the cell leaks no
    subscriptions, and the shell sees the old viewer's ``close`` before the new viewer's ``announce``).
    Then it waits up to ``BROWSER_WAIT_S`` seconds for the page's first hello; a timeout is stated in
    one printed line and the viewer is returned anyway. Reconnect hellos later print in whichever cell
    is executing, or nowhere; gates read ``viewer.clients_seen`` instead.
    """
    global _current_viewer
    previous, _current_viewer = _current_viewer, None
    if previous is not None:
        await previous.stop()
    viewer = DockedViewer3D(deck, **kw)
    _current_viewer = viewer
    try:
        await viewer.start()
    except Exception:
        if _current_viewer is viewer:
            _current_viewer = None
        await viewer.stop()
        raise
    try:
        await viewer.wait_for_browser(timeout=BROWSER_WAIT_S)
    except asyncio.TimeoutError:
        print(f"viewer: no deck view connected within {BROWSER_WAIT_S} s; it will attach when the deck panel opens.")
    return viewer
