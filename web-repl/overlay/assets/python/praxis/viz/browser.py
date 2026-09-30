"""``BrowserVisualizer`` -- PyLabRobot's Visualizer with the servers removed (P6.4).

Stock ``Visualizer`` owns two servers: a websocket server for commands and an
HTTP file server for the renderer. Neither can exist in a Pyodide kernel, which
has no sockets and no threads. This subclass keeps **all** of PLR's serialization,
callback registration, and state batching, and replaces only the four members that
touch the socket:

  ``setup`` / ``stop`` / ``has_connection`` / ``send_command``

That set is not a guess. GATE G2 criterion 2 measured it, and also established
that the **+30-line callback-override fallback is NOT required**: every loop path
the inherited callbacks use -- ``asyncio.run_coroutine_threadsafe``,
``loop.call_soon_threadsafe``, ``loop.call_soon``, and ``asyncio.ensure_future``
-- works unshimmed on Pyodide's WebLoop
(``.praxia/docs/research/260817_g2-spike-battery-verdict.md`` Sec 5, Sec 8).

GATE X: if a fifth member ever needs overriding, STOP and escalate to V4
(upstream a transport hook into PLR). Override-count growth is a design
regression, not a maintenance chore.

Constructor note: ``Visualizer.__init__`` raises when ``HAS_WEBSOCKETS`` is False
(``visualizer.py:168`` at pin ``786ac2c4`` / 1.0.0b1; was ``:144`` at ``dd79c4c8``) -- the guard is in the constructor, not
in ``setup()``, so subclassing cannot dodge it. ``websockets-17.0.1`` is vendored
into ``overlay/assets/wheels/`` for exactly this reason; measured true in-kernel
under ``--offline`` (``repl_smoke.py --probe --offline`` step 2b:
``plr_has_websockets = true``). ``websockets`` is imported but never *used* here:
nothing in this class calls ``serve(...)``.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from pylabrobot.visualizer.visualizer import Visualizer

from .transport import VIZ_CHANNEL, BroadcastChannelTransport, VizTransport

# Serialized ``type`` -> how many more rails than tracks the deck counted under PLR 0.2.2's
# ``num_rails``. Mirrors PLR 1.0's own deprecated ``HamiltonDeck.num_rails`` property, which
# returns ``num_tracks + _rails_beyond_tracks`` (``hamilton_decks.py:231-242``); the class
# attribute is 0 on ``HamiltonDeck`` and 2 on ``HamiltonSTARDeck`` (``star_decks.py:26``).
# Cross-checked against the old pin: STARLet was ``STARLET_NUM_RAILS = 32`` and STAR
# ``STAR_NUM_RAILS = 56`` at ``dd79c4c89`` (``hamilton_decks.py:21,26``); at 1.0 they are
# ``num_tracks`` 30 and 54 (``hamilton_decks.py:20-21``).
_RAILS_BEYOND_TRACKS: Dict[str, int] = {"HamiltonSTARDeck": 2}

# Events whose ``data["resource"]`` is a serialized resource tree headed for ``lib.js``.
_RESOURCE_TREE_EVENTS = frozenset({"set_root_resource", "resource_assigned"})


def add_legacy_num_rails(node: Any) -> Any:
    """Return a copy of a serialized resource tree with ``num_rails`` derived from ``num_tracks``.

    The vendored renderer (``overlay/assets/visualizer/lib.js``) reads ``num_rails`` to draw the
    deck's rail grid (``lib.js:928, 1362-1363, 1417, 1453``). PLR 1.0 serializes ``num_tracks``
    instead (``HamiltonDeck.serialize``, ``hamilton_decks.py:464``), so at 1.0 the grid silently
    vanishes (``HamiltonSTARDeck.num_rails`` is undefined and the draw loop runs zero times).
    ``lib.js`` must stay byte-identical to upstream (R2: the renderer is never forked), so the
    data is fixed on the way to it instead.

    A node gains ``num_rails = num_tracks + offset`` only when it carries ``num_tracks`` and has
    no ``num_rails``; an existing value is never overwritten. ``offset`` is 2 for
    ``HamiltonSTARDeck`` and 0 for any other type (see ``_RAILS_BEYOND_TRACKS``). Nodes without
    ``num_tracks`` (OT-2, Tecan, carriers, wells) pass through unchanged. The input is never
    mutated.
    """
    if not isinstance(node, dict):
        return node
    out = dict(node)
    tracks = out.get("num_tracks")
    if "num_rails" not in out and isinstance(tracks, int) and not isinstance(tracks, bool):
        out["num_rails"] = tracks + _RAILS_BEYOND_TRACKS.get(out.get("type"), 0)
    children = out.get("children")
    if isinstance(children, list):
        out["children"] = [add_legacy_num_rails(child) for child in children]
    return out


class _PyodideLoopShim:
    """Supplies the event loop ``Visualizer.loop`` requires.

    Stock ``Visualizer`` starts a background thread, creates a loop in it, and
    assigns ``self._loop``; its ``loop`` property raises ``RuntimeError`` while
    that attribute is None. Overriding ``setup()`` removes the thread, so the
    attribute must be populated some other way or every inherited callback raises
    on its first ``self.loop`` access.

    Pyodide already runs a WebLoop, so the correct loop is simply the running one.
    This is a *resolver*, not a reimplementation: G2 measured the WebLoop handling
    all four scheduling calls the callbacks make. Do not grow it into a custom
    loop -- that is the road to reimplementing asyncio inside a browser.
    """

    @staticmethod
    def resolve() -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            # Not inside a running loop (e.g. a CPython test constructing the
            # visualizer synchronously). get_event_loop() still yields a usable
            # loop object for attribute purposes.
            return asyncio.get_event_loop()


class BrowserVisualizer(Visualizer):
    """A ``Visualizer`` that emits over a transport instead of a websocket.

    Args:
      resource: the root resource, as for ``Visualizer``.
      transport: any object satisfying :class:`~praxis.viz.transport.VizTransport`.
        Injected rather than constructed internally so browserless tests can pass
        a ``RecordingTransport``.
      **kwargs: forwarded to ``Visualizer.__init__``.
    """

    def __init__(
        self,
        resource: Any,
        transport: VizTransport,
        **kwargs: Any,
    ) -> None:
        # open_browser has no meaning without a file server, and leaving it True
        # makes stock PLR try to launch a browser from inside a browser.
        kwargs.setdefault("open_browser", False)
        super().__init__(resource, **kwargs)
        self._transport = transport
        self._connected = False

    # --- override 1 of 4 -------------------------------------------------
    async def setup(self) -> None:
        """Mark the transport live and paint the initial deck.

        No websocket server, no file server, no thread. Stock ``setup()`` defers
        the first paint until the browser posts a "ready" event over the socket;
        with a BroadcastChannel there is no such handshake, so the paint is issued
        here directly. That ordering is what GATE G6 asserts: ``set_root_resource``
        must precede any ``set_state``.
        """
        if self.setup_finished:
            raise RuntimeError("The visualizer has already been started.")
        self._loop = _PyodideLoopShim.resolve()
        self._connected = True
        self.setup_finished = True
        await self._send_resources_and_state()

    # --- override 2 of 4 -------------------------------------------------
    async def stop(self) -> None:
        """Tear down without touching sockets or threads.

        Mirrors stock ``stop()``'s observable behaviour -- emit ``stop``, then mark
        the visualizer down -- minus the server shutdown it cannot perform.
        """
        if not self.setup_finished:
            return
        await self.send_command("stop", wait_for_response=False)
        self._connected = False
        self.setup_finished = False

    # --- override 3 of 4 -------------------------------------------------
    def has_connection(self) -> bool:
        """Stock checks ``self._websocket is not None``; there is no socket here."""
        return self._connected

    # --- override 4 of 4 -------------------------------------------------
    async def send_command(
        self,
        event: str,
        data: Optional[Dict[str, Any]] = None,
        wait_for_response: bool = True,
    ) -> Optional[dict]:
        """Serialize via PLR, then hand the string to the transport.

        ``_assemble_command`` is called deliberately rather than serializing here:
        it is where ``_sanitize_floats`` runs. ``trash``/``trash_core96`` carry
        ``max_volume = float('inf')``, and a bare ``json.dumps`` emits a literal
        ``Infinity`` token that browser ``JSON.parse`` rejects -- S-D measured
        exactly this, a 65,516-byte initial paint failing with
        ``SyntaxError: Unexpected token 'I'`` while every later delta parsed fine.
        Bypassing ``_assemble_command`` would silently reintroduce it.
        """
        if data is None:
            data = {}

        if wait_for_response:
            # Every internal PLR call site passes wait_for_response=False (checked
            # at this pin: visualizer.py lines 628, 648, 670, 673, 697, 706, 729),
            # so no paint path reaches here. A user calling it directly would
            # otherwise block forever on an ack channel that does not exist --
            # fail loudly instead of hanging.
            raise NotImplementedError(
                "BrowserVisualizer.send_command(wait_for_response=True) is not "
                "supported: the praxis_viz BroadcastChannel is one-way as wired "
                "today, so no response can arrive and the await would never "
                "return. Pass wait_for_response=False."
            )

        if not self.has_connection():
            raise RuntimeError(
                "BrowserVisualizer has no transport connection; call setup() first."
            )

        if event in _RESOURCE_TREE_EVENTS and isinstance(data.get("resource"), dict):
            # PLR 1.0 decks serialize ``num_tracks``; the vendored lib.js draws the rail
            # grid from ``num_rails``. Adapt the data, never the renderer (R2).
            data = {**data, "resource": add_legacy_num_rails(data["resource"])}

        serialized, _id = self._assemble_command(event=event, data=data)
        self._transport.send(serialized)
        return None

    # --- not an override: the G6 assertion surface -----------------------
    def stats(self) -> Dict[str, int]:
        """Transport counters. GATE G6 asserts ``stats()['sent'] >= 2``.

        Exactly 1 is the documented FAILURE signature: it means the initial
        ``set_root_resource`` went out but the operation's ``set_state`` never
        followed, i.e. the state-update callback chain is not wired.
        """
        return self._transport.stats()


def make_broadcast_poster(channel_name: str = VIZ_CHANNEL):
    """Build a poster bound to a real BroadcastChannel. Kernel-only.

    ``import js`` lives here and nowhere else in this package, so ``transport.py``
    and the rest of this module stay importable under CPython for tests.
    """
    import js  # noqa: PLC0415 - deliberately local; see docstring

    channel = js.BroadcastChannel.new(channel_name)

    def post(serialized: str) -> None:
        channel.postMessage(serialized)

    return post


def make_browser_visualizer(resource: Any, **kwargs: Any) -> BrowserVisualizer:
    """Convenience constructor wiring a real BroadcastChannel transport."""
    transport = BroadcastChannelTransport(make_broadcast_poster())
    return BrowserVisualizer(resource, transport=transport, **kwargs)
