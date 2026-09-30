"""``install()``: turn the display layer on in the kernel (task B8; spec D2, D7, D8, D9, D13, AC-17).

One call (the bootstrap's non-fatal stage, D13, makes it) that wires every piece B1-B7 built:

1. **The display session id** (D2): a random id minted ONCE per kernel process (``stale.new_session_id``)
   and shared by every stamp this layer makes (drawings, the ledger, error panels) and by the
   announcements, so the shell can tell this kernel's outputs from an earlier session's.
2. **The formatters** (D2). ``Plate``, ``TipRack``, ``Deck`` and ``Container`` are registered by CLASS with
   the shell's display formatter, so IPython resolves subclasses by MRO: an ``EmbeddedTipRack`` (the pin's
   ``tips_300``) is a ``TipRack``, a ``Well`` is a ``Container``. No code here dispatches on a type-name
   string. Before every render the session is asked for ``render_kwargs(obj)``, which settles the drawn
   state and gives the ``rev`` the stamp must carry (B7: settling is automatic). ``RunLedger`` needs no
   registration on the primary carrier: IPython finds its ``_repr_mimebundle_``.
3. **The error handler** (D8): ``errors.install`` wraps the shell INSTANCE's ``showtraceback`` for the four
   PLR errors (the S3-C fallback, in force: ``set_custom_exc`` runs its handler but its traceback does not
   become the cell's error output, and Run All would not stop). ``set_custom_exc`` is never called.
4. **The ledger seam** (D9): ``ledger.configure(session=..., exec_count=...)``, because a bare
   ``RunLedger(lh)`` stamps session ``"unset"`` until it is told.
5. **The announcer** (D7): a ``stale.DisplaySession`` posts ``praxis:resource-changed`` on the
   shell channel (through ``stale.make_repl_poster``, the only ``import js``). ``post_run_cell``
   is registered as an OPTIMISATION only: spike S3-D measured that it does not fire for top-level-``await``
   cells, so the debounced ``loop.call_later`` timer inside ``DisplaySession`` is the real path.

**Carriers.** The primary carrier (S3-A, measured to hold) is
``display_formatter.mimebundle_formatter.for_type(cls, fn)`` with ``fn(obj) -> (data, metadata)``: the stamp
rides at ``metadata["praxis"]``. The S3-B fallback is selected when the shell lacks that API or a
registration raises (whatever was registered is taken back first): ``text/html`` and ``text/plain`` are
registered SEPARATELY through ``display_formatter.formatters[...].for_type``; the html function returns
``(html, {"praxis": stamp})`` so the stamp rides at ``metadata["text/html"]["praxis"]``, which the shell
reads through the same ``stampOf`` accessor. The plain function returns the summary sentence and, because
IPython's plain-text formatter calls a registered printer as ``func(obj, p, cycle)``, also writes it to
``p`` when one is given. Under the fallback ``RunLedger`` is registered too (its own
``_repr_mimebundle_`` cannot be assumed to carry metadata when the mimebundle carrier does not).

**A formatter never breaks a display.** A render that raises is logged and the formatter returns ``None``,
so IPython falls back to the object's default repr.

**Idempotent and reversible.** A second ``install`` on the same shell returns the same handle and registers
nothing. ``Installed.uninstall()`` restores the shell (formatters, ``showtraceback``, the event hook, the
ledger seam) and silences the announcer; it is idempotent. If a step fails, what was done is undone and
the exception propagates (the bootstrap turns it into ``praxis:display-error``).

**Imports.** Plain CPython, IPython-free and ``js``-free at import time: the standard library and the
sibling modules only. The four PyLabRobot classes are resolved inside ``display_classes`` from
``pylabrobot.resources``; ``get_ipython`` is imported only when no shell is passed; ``import js`` lives in
``stale.make_repl_poster``.
"""

from __future__ import annotations

import logging

from . import deck, errors, labware, ledger, stale

__all__ = [
    "CARRIER_FORMATTERS",
    "CARRIER_MIMEBUNDLE",
    "Installed",
    "display_classes",
    "install",
    "render",
]

log = logging.getLogger("praxis.display")

#: D2's carrier, measured to hold by spike S3 (S3-A): one mimebundle per object, stamp at ``metadata.praxis``.
CARRIER_MIMEBUNDLE = "mimebundle"
#: The S3-B fallback: ``text/html`` and ``text/plain`` registered separately, stamp at ``metadata["text/html"]``.
CARRIER_FORMATTERS = "formatters"

#: shell id -> its live handle. A handle removes itself on ``uninstall``.
_INSTALLED: dict[int, Installed] = {}
#: The display session id of this kernel process, minted on first use (D2: once per process).
_SESSION: str | None = None


def _process_session() -> str:
    global _SESSION
    if _SESSION is None:
        _SESSION = stale.new_session_id()
    return _SESSION


def display_classes() -> tuple:
    """The four classes the display registers, by class (``Plate``, ``TipRack``, ``Deck``, ``Container``).
    Resolved when first needed (never at import); raises ``ImportError`` if PLR is not importable."""
    from pylabrobot.resources import Container, Deck, Plate, TipRack  # noqa: PLC0415 -- lazy by design

    return (Plate, TipRack, Deck, Container)


def _current_shell():
    try:
        from IPython import get_ipython  # noqa: PLC0415 -- only when no shell is passed
    except ImportError as exc:
        raise ImportError(
            "praxis.display.install() needs IPython's shell; pass shell= explicitly outside a kernel"
        ) from exc
    shell = get_ipython()
    if shell is None:
        raise RuntimeError("praxis.display.install(): get_ipython() returned None, there is no shell to install into")
    return shell


def _bundle_of(obj, kwargs):
    """``(data, metadata)`` for one displayable object, stamped with ``kwargs`` (see ``render_kwargs``)."""
    if isinstance(obj, ledger.RunLedger):
        return obj.bundle()  # its stamp reads the seam ``ledger.configure`` set
    if deck.is_deck(obj):
        return deck.render(obj, **kwargs)
    return labware.render(obj, **kwargs)


def _sentence_of(obj) -> str:
    """The ``text/plain`` of ``obj`` (the summary sentence): what ``render(obj)`` puts there, without
    drawing, stamping or subscribing anything."""
    if isinstance(obj, ledger.RunLedger):
        return obj.text()
    if deck.is_deck(obj):
        return deck.sentence(obj)
    return labware.sentence(obj)


class Installed:
    """What ``install`` returns.

    ``shell`` is the shell it is installed on; ``session`` the ``stale.DisplaySession``; ``session_id`` the
    display session id every stamp carries; ``carrier`` is ``CARRIER_MIMEBUNDLE`` or ``CARRIER_FORMATTERS``;
    ``errors`` the ``errors.Installed`` handle; ``active`` is false after ``uninstall``.
    """

    def __init__(self, shell, session_id: str):
        self.shell = shell
        self.session_id = session_id
        self.session: stale.DisplaySession | None = None
        self.carrier: str | None = None
        self.errors: errors.Installed | None = None
        self.active = True
        self._post = None
        self._registered: list[tuple] = []  # (formatter, cls, previous registration or None)
        self._hook = None
        self._ledger_configured = False

    # -- what the shell reads ---------------------------------------------------------

    def exec_count(self):
        """The execution count of the cell running now (``get_ipython().execution_count``)."""
        return getattr(self.shell, "execution_count", None)

    def render(self, obj):
        """``(data, metadata)`` for ``obj``, stamped with the settled rev, this session and this cell."""
        if isinstance(obj, ledger.RunLedger):
            return _bundle_of(obj, None)
        return _bundle_of(obj, self.session.render_kwargs(obj))

    def _announce(self, payload: str) -> None:
        """The session's poster, silenced once uninstalled (PLR callbacks cannot be unsubscribed)."""
        if self.active and self._post is not None:
            self._post(payload)

    # -- formatter functions ------------------------------------------------------------

    def _safe(self, obj):
        try:
            return self.render(obj)
        except Exception:  # noqa: BLE001 -- IPython then shows the default repr
            log.warning("praxis.display: could not draw %s", type(obj).__name__, exc_info=True)
            return None

    def _mimebundle_fn(self, obj):
        return self._safe(obj)

    def _html_fn(self, obj):
        bundle = self._safe(obj)
        if bundle is None:
            return None
        data, metadata = bundle
        return data["text/html"], {"praxis": metadata["praxis"]}

    def _plain_fn(self, obj, printer=None, cycle=False):
        try:
            text = _sentence_of(obj)
        except Exception:  # noqa: BLE001
            log.warning("praxis.display: no summary for %s", type(obj).__name__, exc_info=True)
            if printer is not None:
                printer.text(repr(obj))
            return None
        if printer is not None:
            printer.text(text)  # IPython's plain-text formatter calls func(obj, p, cycle)
        return text

    # -- registration -----------------------------------------------------------------------

    def _register(self, formatter, cls, fn) -> None:
        previous = formatter.for_type(cls, fn)
        self._registered.append((formatter, cls, previous))

    def _unregister_formatters(self) -> None:
        while self._registered:
            formatter, cls, previous = self._registered.pop()
            try:
                if previous is not None:
                    formatter.for_type(cls, previous)
                else:
                    formatter.pop(cls, None)
            except Exception:  # noqa: BLE001
                log.warning("praxis.display: could not unregister %s", getattr(cls, "__name__", cls), exc_info=True)

    def _register_formatters(self) -> None:
        classes = display_classes()
        display_formatter = getattr(self.shell, "display_formatter", None)
        if display_formatter is None:
            raise RuntimeError("praxis.display.install(): the shell has no display_formatter")
        mimebundle = getattr(display_formatter, "mimebundle_formatter", None)
        if mimebundle is not None and callable(getattr(mimebundle, "for_type", None)):
            try:
                for cls in classes:
                    self._register(mimebundle, cls, self._mimebundle_fn)
                self.carrier = CARRIER_MIMEBUNDLE
                return
            except Exception:  # noqa: BLE001 -- S3-B: take back what was registered, use the fallback
                log.warning("praxis.display: mimebundle registration failed, using the S3-B fallback", exc_info=True)
                self._unregister_formatters()
        html, plain = display_formatter.formatters["text/html"], display_formatter.formatters["text/plain"]
        for cls in (*classes, ledger.RunLedger):
            self._register(html, cls, self._html_fn)
            self._register(plain, cls, self._plain_fn)
        self.carrier = CARRIER_FORMATTERS

    def _hook_events(self) -> None:
        """``post_run_cell`` flushes the announcer at once. An optimisation only (S3-D): a shell with no
        event manager, or one that never fires it, still announces through the debounced timer."""
        register = getattr(getattr(self.shell, "events", None), "register", None)
        if not callable(register):
            log.info("praxis.display: the shell has no event manager; announcements use the debounced timer")
            return
        hook = self.session.post_run_cell
        register("post_run_cell", hook)
        self._hook = hook

    # -- reversal ----------------------------------------------------------------------------

    def uninstall(self) -> None:
        """Restore the shell and silence the announcer. Idempotent."""
        if not self.active:
            return
        self.active = False
        steps = [
            self._unhook_events,
            self._unregister_formatters,
            self._uninstall_errors,
            self._cancel_timer,
        ]
        for step in steps:
            try:
                step()
            except Exception:  # noqa: BLE001 -- keep undoing the rest
                log.warning("praxis.display: uninstall step %s failed", step.__name__, exc_info=True)
        if _INSTALLED.get(id(self.shell)) is self:
            del _INSTALLED[id(self.shell)]
        if self._ledger_configured:
            self._ledger_configured = False
            other = _active_handle()
            if other is None:
                ledger.configure()
            else:
                other._configure_ledger()

    def _unhook_events(self) -> None:
        hook, self._hook = self._hook, None
        if hook is not None:
            self.shell.events.unregister("post_run_cell", hook)

    def _uninstall_errors(self) -> None:
        handle, self.errors = self.errors, None
        if handle is not None:
            handle.uninstall()

    def _cancel_timer(self) -> None:
        if self.session is not None:
            self.session._cancel_timer()  # no public cancel: the poster is gated anyway

    def _configure_ledger(self) -> None:
        ledger.configure(session=self.session_id, exec_count=self.exec_count)
        self._ledger_configured = True


def _active_handle() -> Installed | None:
    """The most recently installed live handle, or ``None``."""
    return next(reversed(_INSTALLED.values()), None)


def install(shell=None, *, post=None, loop=None, session_id=None, display=None, resolver=None) -> Installed:
    """Wire the display into ``shell`` (default ``get_ipython()``) and return the handle.

    ``post`` is the announcer's ``post(json_str)`` (default ``stale.make_repl_poster()``); ``loop`` anything
    with ``call_later(delay, cb) -> handle`` (default: the running asyncio loop when a callback fires);
    ``session_id`` overrides the process's session id; ``display`` and ``resolver`` are passed to
    ``errors.install`` (tests). Idempotent per shell. If a step fails, what was done is undone and the
    exception propagates.
    """
    if shell is None:
        shell = _current_shell()
    existing = _INSTALLED.get(id(shell))
    if existing is not None and existing.active:
        return existing
    poster = post if post is not None else stale.make_repl_poster()  # may raise: nothing is done yet
    handle = Installed(shell, session_id or _process_session())
    handle._post = poster
    handle.session = stale.DisplaySession(
        handle._announce, loop=loop, exec_count=handle.exec_count, session_id=handle.session_id
    )
    _INSTALLED[id(shell)] = handle
    try:
        handle._register_formatters()
        handle._configure_ledger()
        handle.errors = errors.install(
            shell, session=handle.session_id, exec_count=handle.exec_count, display=display, resolver=resolver
        )
        handle._hook_events()
    except BaseException:
        handle.uninstall()
        raise
    return handle


def render(obj):
    """``(data, metadata)`` for ``obj``, for tests and explicit use (``praxis.display.render(plate)``).

    With the display installed it is exactly what the registered formatter produces (same session, the
    settled rev, the current execution count). Without it the stamp carries rev 0, this process's session
    id and no execution count, and nothing is subscribed, so it is never announced. ``TypeError`` for an
    object that is not a ``Plate``, ``TipRack``, ``Deck`` or ``Container``.
    """
    handle = _active_handle()
    if handle is not None:
        return handle.render(obj)
    if isinstance(obj, ledger.RunLedger):
        return obj.bundle()
    return _bundle_of(obj, {"rev": 0, "session": _process_session(), "exec_count": None})
