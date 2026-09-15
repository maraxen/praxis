"""CPython unit tests for ``web-repl/files/praxis_startup.py`` (T4, debt
#1396): the PYTHONSTARTUP shim and its inline catch-and-rewrite gate.

IPython runs this file via ``safe_execfile`` -- compile + exec of the file's
*source* into a namespace dict (the user namespace) -- so these tests do the
same, rather than ``import``ing it as a module, to match the real execution
model exactly (section 6.2, and the T4 dispatch brief).

Fakes used:

- ``praxis_boot``: installed into ``sys.modules`` per test, either as a
  working stub (records ``_autostart`` calls) or as an import that raises
  (via a monkeypatched ``builtins.__import__``, since the startup file does
  a bare ``import praxis_boot as _praxis_boot`` -- there is no module object
  to substitute when the point of the test is that the *import itself*
  fails).
- ``get_ipython``: not a real name anywhere in CPython; IPython injects it
  into the user namespace at runtime. Tests that need the inline gate to be
  installable put a callable under that key in the exec namespace directly;
  tests for failure mode 10 (kernel internals missing) simply omit it.

Each test execs into a *fresh* namespace dict, so there is nothing to reset
between tests (unlike ``praxis_boot`` itself, which is a singleton module).
"""

from __future__ import annotations

import asyncio
import builtins
import sys
import types
from pathlib import Path

import pytest

_STARTUP_PATH = Path(__file__).resolve().parents[1] / "files" / "praxis_startup.py"
_SOURCE = _STARTUP_PATH.read_text()

# The private names praxis_startup.py must not leave behind in the exec
# namespace, in either the success or the failure path (module docstring;
# spec section 6.2's `finally` block plus Python's implicit `except ... as
# name: ... ; del name`).
_PRIVATE_NAMES = (
    "_praxis_boot",
    "_praxis_exc",
    "_praxis_detail",
    "_praxis_msg",
    "_praxis_inline_gate",
    "_praxis_n",
)


def _run_startup(namespace: dict) -> None:
    """Exec praxis_startup.py's source into *namespace*, the way IPython's
    ``safe_execfile(..., raise_exceptions=True)`` does for PYTHONSTARTUP."""
    exec(compile(_SOURCE, str(_STARTUP_PATH), "exec"), namespace)


class _BadRepr(Exception):
    """An exception whose own __repr__/__str__ raise (R2-5)."""

    def __repr__(self) -> str:  # noqa: DUNDER001
        raise RuntimeError("__repr__ is broken too")

    def __str__(self) -> str:
        raise RuntimeError("__str__ is broken")


class _FakeManager:
    """Same shape as ``pyodide_kernel.litetransform.LiteTransformerManager``
    exposes: plain lists, cleanup before line transforms."""

    def __init__(self) -> None:
        self.cleanup_transforms: list = []
        self.line_transforms: list = ["pip_magic_stub"]


class _FakeKernel:
    def __init__(self, manager: _FakeManager) -> None:
        self.lite_transform_manager = manager


class _FakeShell:
    def __init__(self, manager: _FakeManager) -> None:
        self.kernel = _FakeKernel(manager)


def _install_fake_get_ipython(namespace: dict) -> _FakeManager:
    """Puts a ``get_ipython`` name directly into the exec namespace, the way
    IPython injects it into the real user namespace (it is not importable)."""
    manager = _FakeManager()
    namespace["get_ipython"] = lambda: _FakeShell(manager)
    return manager


def _install_working_praxis_boot(monkeypatch, *, protocol: int = 1) -> list:
    """A ``praxis_boot`` stub whose import succeeds. Returns the list of
    origins ``_autostart`` was called with (should end up length <= 1)."""
    module = types.ModuleType("praxis_boot")
    module.AUTOSETUP_PROTOCOL = protocol
    calls: list = []

    def _autostart(origin: str) -> None:
        calls.append(origin)

    module._autostart = _autostart
    monkeypatch.setitem(sys.modules, "praxis_boot", module)
    return calls


def _install_raising_import(monkeypatch, exc_factory) -> None:
    """Makes ``import praxis_boot`` raise ``exc_factory()``, by intercepting
    the ``__import__`` builtin the exec'd code implicitly uses. There is no
    ``praxis_boot`` module object to monkeypatch when the point is that the
    import statement itself fails (a shadowed/deleted drive copy, failure
    mode 11)."""
    monkeypatch.delitem(sys.modules, "praxis_boot", raising=False)
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "praxis_boot":
            raise exc_factory()
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


async def _run_gate(gate, lines: list[str]) -> list[str]:
    return await gate(lines)


def _assert_no_private_names_leaked(namespace: dict) -> None:
    for name in _PRIVATE_NAMES:
        assert name not in namespace, f"{name!r} leaked into the exec namespace"


# --------------------------------------------------------------------------
# Success path
# --------------------------------------------------------------------------


def test_success_calls_autostart_once_and_leaves_no_names(monkeypatch) -> None:
    calls = _install_working_praxis_boot(monkeypatch)
    namespace: dict = {}

    _run_startup(namespace)

    assert calls == ["PYTHONSTARTUP"]
    _assert_no_private_names_leaked(namespace)


def test_success_installs_no_inline_gate(monkeypatch) -> None:
    """The happy path never touches the inline fallback gate at all."""
    _install_working_praxis_boot(monkeypatch)
    namespace: dict = {}
    manager = _install_fake_get_ipython(namespace)

    _run_startup(namespace)

    assert manager.cleanup_transforms == []


# --------------------------------------------------------------------------
# (a) import praxis_boot raising
# --------------------------------------------------------------------------


def test_import_failure_installs_inline_gate_at_index_zero(monkeypatch) -> None:
    _install_raising_import(
        monkeypatch, lambda: ModuleNotFoundError("No module named 'praxis_boot'")
    )
    namespace: dict = {}
    manager = _install_fake_get_ipython(namespace)

    _run_startup(namespace)

    assert len(manager.cleanup_transforms) == 1
    assert manager.cleanup_transforms[0] is manager.cleanup_transforms[0]  # sanity
    _assert_no_private_names_leaked(namespace)


def test_import_failure_gate_returns_raise_line_naming_the_import_error(monkeypatch) -> None:
    _install_raising_import(
        monkeypatch, lambda: ModuleNotFoundError("No module named 'praxis_boot'")
    )
    namespace: dict = {}
    manager = _install_fake_get_ipython(namespace)
    _run_startup(namespace)
    gate = manager.cleanup_transforms[0]

    rewritten = asyncio.run(_run_gate(gate, ["user_code()\n"]))

    assert isinstance(rewritten, list)
    assert len(rewritten) == 1
    assert "PraxisAutoSetupError" in rewritten[0]
    assert "No module named" in rewritten[0]
    assert "praxis_boot" in rewritten[0]

    with pytest.raises(RuntimeError) as excinfo:
        exec(compile(rewritten[0], "<gate-rewrite>", "exec"), {})
    assert "PraxisAutoSetupError" in str(excinfo.value)
    assert "No module named" in str(excinfo.value)


# --------------------------------------------------------------------------
# (b) AUTOSETUP_PROTOCOL mismatch
# --------------------------------------------------------------------------


def test_protocol_mismatch_installs_inline_gate_and_skips_autostart(monkeypatch) -> None:
    calls = _install_working_praxis_boot(monkeypatch, protocol=2)
    namespace: dict = {}
    manager = _install_fake_get_ipython(namespace)

    _run_startup(namespace)

    assert calls == []  # _autostart must never run after a protocol mismatch
    assert len(manager.cleanup_transforms) == 1
    _assert_no_private_names_leaked(namespace)


def test_protocol_mismatch_gate_returns_raise_line_naming_the_mismatch(monkeypatch) -> None:
    _install_working_praxis_boot(monkeypatch, protocol=2)
    namespace: dict = {}
    manager = _install_fake_get_ipython(namespace)
    _run_startup(namespace)
    gate = manager.cleanup_transforms[0]

    rewritten = asyncio.run(_run_gate(gate, ["user_code()\n"]))

    assert len(rewritten) == 1
    assert "PraxisAutoSetupError" in rewritten[0]
    assert "AUTOSETUP_PROTOCOL mismatch" in rewritten[0]

    with pytest.raises(RuntimeError) as excinfo:
        exec(compile(rewritten[0], "<gate-rewrite>", "exec"), {})
    assert "PraxisAutoSetupError" in str(excinfo.value)
    assert "AUTOSETUP_PROTOCOL mismatch" in str(excinfo.value)


# --------------------------------------------------------------------------
# (c) the inline gate never raises, regardless of the lines it is given
# --------------------------------------------------------------------------


def test_inline_gate_never_raises_regardless_of_input_lines(monkeypatch) -> None:
    _install_raising_import(
        monkeypatch, lambda: ModuleNotFoundError("No module named 'praxis_boot'")
    )
    namespace: dict = {}
    manager = _install_fake_get_ipython(namespace)
    _run_startup(namespace)
    gate = manager.cleanup_transforms[0]

    for lines in ([], ["\n"], ["a = '''; import os\n", "b = 2\n"], ["x = 1\\\n"]):
        rewritten = asyncio.run(_run_gate(gate, lines))
        assert isinstance(rewritten, list)
        assert len(rewritten) == 1
        assert "PraxisAutoSetupError" in rewritten[0]


# --------------------------------------------------------------------------
# (d) no get_ipython / kernel internals missing: the file itself still does
# not raise
# --------------------------------------------------------------------------


def test_missing_get_ipython_does_not_raise(monkeypatch) -> None:
    _install_raising_import(
        monkeypatch, lambda: ModuleNotFoundError("No module named 'praxis_boot'")
    )
    namespace: dict = {}  # deliberately no "get_ipython" key

    _run_startup(namespace)  # must not raise

    _assert_no_private_names_leaked(namespace)


def test_missing_kernel_attribute_does_not_raise(monkeypatch) -> None:
    """``get_ipython()`` exists but its shell has no ``.kernel`` -- same
    "kernel internals missing" failure mode 10, reached a different way."""
    _install_raising_import(
        monkeypatch, lambda: ModuleNotFoundError("No module named 'praxis_boot'")
    )
    namespace: dict = {}
    namespace["get_ipython"] = lambda: types.SimpleNamespace()  # no .kernel

    _run_startup(namespace)  # must not raise

    _assert_no_private_names_leaked(namespace)


# --------------------------------------------------------------------------
# (e) R2-5: an exception whose __repr__/__str__ themselves raise
# --------------------------------------------------------------------------


def test_bad_repr_exception_still_installs_inline_gate(monkeypatch) -> None:
    _install_raising_import(monkeypatch, _BadRepr)
    namespace: dict = {}
    manager = _install_fake_get_ipython(namespace)

    _run_startup(namespace)

    assert len(manager.cleanup_transforms) == 1
    _assert_no_private_names_leaked(namespace)


def test_bad_repr_exception_gate_raise_line_contains_marker_and_never_raises(monkeypatch) -> None:
    _install_raising_import(monkeypatch, _BadRepr)
    namespace: dict = {}
    manager = _install_fake_get_ipython(namespace)
    _run_startup(namespace)
    gate = manager.cleanup_transforms[0]

    rewritten = asyncio.run(_run_gate(gate, ["user_code()\n"]))

    assert len(rewritten) == 1
    assert "PraxisAutoSetupError" in rewritten[0]

    with pytest.raises(RuntimeError) as excinfo:
        exec(compile(rewritten[0], "<gate-rewrite>", "exec"), {})
    assert "PraxisAutoSetupError" in str(excinfo.value)
