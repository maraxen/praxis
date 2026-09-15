"""PYTHONSTARTUP shim for the Praxis Pyodide kernel (debt #1396, T4).

IPython runs this file via ``safe_execfile`` in the *user* namespace during
kernel init (every kernel, including restarts), so anything left in
``globals()`` here would leak into the user's first cell. Nothing in this
file may raise past its own top level either -- an exception escaping this
file is swallowed invisibly by the startup machinery, which would silently
leave the kernel bare with no explanation (failure mode 4 in the spec).

The happy path just hands off to ``praxis_boot._autostart()``, which installs
the real cell gate and kicks off the bootstrap task; see
``web-repl/files/praxis_boot.py`` for that state machine.

The ``except BaseException`` branch below covers the two things
``_autostart`` itself cannot: ``import praxis_boot`` failing (a shadowed or
deleted copy in the user's drive, failure mode 11) and a protocol mismatch
(this startup file shipping against an incompatible ``praxis_boot.py``). It
installs its OWN inline gate -- with no ``praxis_boot`` import of its own --
into ``get_ipython().kernel.lite_transform_manager.cleanup_transforms``, so
every cell still gets a clear, fail-closed error instead of a confusing
``ModuleNotFoundError`` on the user's own code.

Per the S0 E4 normative rule (spec section 6.2): a transform that raises out
of ``transform_cell`` leaves the kernel stuck ``busy`` with JS pageerrors
instead of a normal traceback, so the inline gate must never raise, and
every step that builds its error message is separately guarded so a broken
exception ``__repr__``/``__str__`` still results in a working gate.
"""

try:
    import praxis_boot as _praxis_boot

    if getattr(_praxis_boot, "AUTOSETUP_PROTOCOL", None) != 1:
        raise RuntimeError(
            "praxis_boot.py in your drive is not the shipped version "
            "(AUTOSETUP_PROTOCOL mismatch)"
        )
    _praxis_boot._autostart(origin="PYTHONSTARTUP")
except BaseException as _praxis_exc:
    # Inline catch-and-rewrite gate. Needs no praxis_boot import.
    # Guarded formatting (R2-5): the exception's own __repr__ may raise.
    try:
        _praxis_detail = repr(_praxis_exc)
    except BaseException:
        _praxis_detail = "<unprintable exception>"
    try:
        _praxis_msg = (
            "PraxisAutoSetupError: praxis auto-setup could not start: " + _praxis_detail
            + ". Your cell was NOT run. "
            "A copy of praxis_boot.py or praxis_startup.py saved in this browser shadows "
            "the shipped one: delete or restore it in the file browser, then restart the kernel."
        )
    except BaseException:
        _praxis_msg = "PraxisAutoSetupError: praxis auto-setup could not start. Your cell was NOT run."
    try:
        async def _praxis_inline_gate(lines, _m=_praxis_msg):
            try:
                return ["raise RuntimeError(" + repr(_m) + ")\n"]
            except BaseException:
                return ["raise RuntimeError('PraxisAutoSetupError: praxis auto-setup could not start')\n"]

        get_ipython().kernel.lite_transform_manager.cleanup_transforms.insert(0, _praxis_inline_gate)
    except BaseException:
        pass  # kernel internals missing: T5 build contract + --fresh-boot-check
finally:
    for _praxis_n in ("_praxis_boot", "_praxis_detail", "_praxis_msg", "_praxis_inline_gate"):
        globals().pop(_praxis_n, None)
    globals().pop("_praxis_n", None)
