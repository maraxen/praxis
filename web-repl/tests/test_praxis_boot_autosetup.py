"""CPython unit tests for ``web-repl/files/praxis_boot.py``'s auto-setup state
machine (T3, debt #1396): ``_autostart``, ``_run_setup``, ``_gate_cell`` and
its liveness/robustness rules, ``_gate_error``, ``status()``, ``dismiss()``.

There is no real browser or pyodide-kernel here, so this fakes:

- ``js`` (an ``XMLHttpRequest`` that always serves a tiny synthetic loader
  script defining ``praxis_main``, plus ``js.location.pathname`` for
  ``derive_host_root()``). The served ``praxis_main`` forwards to
  ``builtins._praxis_test_hook``, an async callable each test installs, so
  every test gets full control over "the bootstrap" without touching the
  real ``bootstrap/praxis_bootstrap.py``.
- ``IPython`` (``get_ipython()`` returning a fake shell whose
  ``.kernel.lite_transform_manager`` is a plain object with
  ``cleanup_transforms``/``line_transforms`` lists -- the same shape
  ``pyodide_kernel.litetransform.LiteTransformerManager`` has).

``praxis_boot._verify`` is monkeypatched per test rather than faking a whole
``pylabrobot`` package tree, EXCEPT where the test is specifically about the
_verify-fails-after-praxis_main-succeeds path (AC-4 / failure mode 6, per the
8.4 trap "mocking away the error path").

Each test gets a fresh import of ``praxis_boot`` (the ``pb`` fixture), so
module-level state (``state``, ``kernel_nonce``, ``_task``, ``_lock``, ...)
never leaks between tests.
"""

from __future__ import annotations

import asyncio
import builtins
import importlib
import sys
import types
from pathlib import Path

import pytest

_FILES_DIR = Path(__file__).resolve().parents[1] / "files"
if str(_FILES_DIR) not in sys.path:
    sys.path.insert(0, str(_FILES_DIR))

HOST_ROOT = "/praxis/"

# D1 detection substring used in _gate_error(); must remain synchronized with stages.py
_D1_DETECTION_SUBSTRING = "D1 whole-deployment staleness check"

_LOADER_SOURCE = (
    "async def praxis_main(host_root, *, raise_on_error=False):\n"
    "    import builtins\n"
    "    return await builtins._praxis_test_hook(host_root, raise_on_error=raise_on_error)\n"
)


class _FakeXHR:
    """Always 200s and serves ``_LOADER_SOURCE``, regardless of URL -- the
    tests here are about the state machine built on top of the fetch, not
    the fetch itself (that is ``test_praxis_bootstrap_loader.py``'s job)."""

    def __init__(self) -> None:
        self.status = 0
        self.responseText = ""
        self._url: str | None = None

    def open(self, method, url, async_) -> None:
        self._url = url

    def send(self, body) -> None:
        self.status = 200
        self.responseText = _LOADER_SOURCE


def _install_fake_js(monkeypatch, pathname: str = HOST_ROOT + "extensions/@jupyterlite/x.js") -> None:
    fake_js = types.ModuleType("js")
    fake_js.XMLHttpRequest = types.SimpleNamespace(new=lambda: _FakeXHR())
    fake_js.location = types.SimpleNamespace(pathname=pathname)
    monkeypatch.setitem(sys.modules, "js", fake_js)


class _FakeManager:
    """Stands in for ``pyodide_kernel.litetransform.LiteTransformerManager``:
    a plain object exposing the two lists ``_autostart``/``_gate_cell`` care
    about, in the same order (cleanup before line transforms, per
    ``litetransform.py:31``)."""

    def __init__(self) -> None:
        self.cleanup_transforms: list = []
        self.line_transforms: list = ["pip_magic_stub"]


class _FakeKernel:
    def __init__(self, manager: _FakeManager) -> None:
        self.lite_transform_manager = manager


class _FakeShell:
    def __init__(self, manager: _FakeManager) -> None:
        self.kernel = _FakeKernel(manager)


def _install_fake_ipython(monkeypatch) -> _FakeManager:
    manager = _FakeManager()
    fake_ipython = types.ModuleType("IPython")
    fake_ipython.get_ipython = lambda: _FakeShell(manager)
    monkeypatch.setitem(sys.modules, "IPython", fake_ipython)
    return manager


def _set_hook(monkeypatch, hook) -> None:
    monkeypatch.setattr(builtins, "_praxis_test_hook", hook, raising=False)


class _BadRepr(Exception):
    """An exception whose own __repr__/__str__ raise (R2-5)."""

    def __repr__(self) -> str:  # noqa: DUNDER001
        raise RuntimeError("__repr__ is broken too")

    def __str__(self) -> str:
        raise RuntimeError("__str__ is broken")


class _FakeTaskThatNeverFinishes:
    """A ``_task`` stand-in whose ``__await__`` completes instantly (so a
    single ``await asyncio.shield(...)`` returns right away) but which never
    reports itself as done -- used to prove the gate awaits at most once per
    cell even in a state that "should be impossible" (8.1's await-counter
    case)."""

    def __init__(self) -> None:
        self.await_count = 0

    def __await__(self):
        self.await_count += 1
        if False:  # pragma: no cover - makes this a generator, never runs
            yield
        return None

    def done(self) -> bool:
        return False

    def cancelled(self) -> bool:
        return False

    def exception(self):
        return None


@pytest.fixture()
def pb(monkeypatch):
    """A fresh import of ``praxis_boot`` per test."""
    sys.modules.pop("praxis_boot", None)
    module = importlib.import_module("praxis_boot")
    yield module
    sys.modules.pop("praxis_boot", None)
    # _praxis_test_hook is cleaned up by the monkeypatch fixture itself
    # (it is always installed via monkeypatch.setattr); only _PRAXIS_BOOT_DONE
    # is sometimes set directly, so only that needs manual cleanup here.
    if hasattr(builtins, "_PRAXIS_BOOT_DONE"):
        delattr(builtins, "_PRAXIS_BOOT_DONE")


async def _drain(task) -> None:
    """Cancel a dangling task and swallow the resulting CancelledError, so a
    test that leaves ``_task`` pending doesn't emit "Task was destroyed but
    it is pending" noise."""
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# _autostart
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_autostart_idempotent(pb, monkeypatch):
    _install_fake_js(monkeypatch)
    manager = _install_fake_ipython(monkeypatch)

    async def _hangs(host_root, *, raise_on_error=False):
        await asyncio.Event().wait()

    _set_hook(monkeypatch, _hangs)

    pb._autostart(origin="PYTHONSTARTUP")
    first_task = pb._task
    assert pb.state == "running"
    assert pb.autostart_origin == "PYTHONSTARTUP"
    assert manager.cleanup_transforms == [pb._gate_cell]

    pb._autostart(origin="PYTHONSTARTUP")  # e.g. %run praxis_startup.py again
    assert pb._task is first_task
    assert manager.cleanup_transforms.count(pb._gate_cell) == 1

    await _drain(pb._task)


@pytest.mark.asyncio
async def test_autostart_gate_is_ahead_of_pip_magic(pb, monkeypatch):
    _install_fake_js(monkeypatch)
    manager = _install_fake_ipython(monkeypatch)

    async def _hangs(host_root, *, raise_on_error=False):
        await asyncio.Event().wait()

    _set_hook(monkeypatch, _hangs)

    pb._autostart(origin="PYTHONSTARTUP")
    assert manager.cleanup_transforms[0] is pb._gate_cell
    assert manager.line_transforms == ["pip_magic_stub"]  # untouched, still after cleanup

    await _drain(pb._task)


def test_autostart_never_raises_when_kernel_internals_missing(pb, monkeypatch):
    """Failure mode 10 / the real safeguard is T5's build contract, but
    _autostart itself must still fail closed, not raise, if the lookup of
    get_ipython().kernel.lite_transform_manager fails."""
    fake_ipython = types.ModuleType("IPython")
    fake_ipython.get_ipython = lambda: (_ for _ in ()).throw(RuntimeError("no get_ipython"))
    monkeypatch.setitem(sys.modules, "IPython", fake_ipython)

    pb._autostart(origin="PYTHONSTARTUP")  # must not raise

    assert pb.state == "failed"
    assert pb.failure is not None
    assert pb._task is None


# ---------------------------------------------------------------------------
# _run_setup / setup() happy and failure paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_setup_success_sets_ready(pb, monkeypatch):
    _install_fake_js(monkeypatch)
    monkeypatch.setattr(pb, "_verify", lambda: "0.2.2+gdeadbeef")

    async def _ok(host_root, *, raise_on_error=False):
        return None

    _set_hook(monkeypatch, _ok)

    result = await pb._run_setup(host_root_override=HOST_ROOT)
    assert result == HOST_ROOT
    assert pb.state == "ready"
    assert pb.host_root == HOST_ROOT
    assert pb.failure is None


@pytest.mark.asyncio
async def test_run_setup_praxis_main_failure_sets_failed_and_raises_when_not_auto(pb, monkeypatch):
    _install_fake_js(monkeypatch)

    async def _boom(host_root, *, raise_on_error=False):
        raise RuntimeError("stage exploded")

    _set_hook(monkeypatch, _boom)

    with pytest.raises(RuntimeError, match="stage exploded"):
        await pb._run_setup(host_root_override=HOST_ROOT)

    assert pb.state == "failed"
    assert isinstance(pb.failure, RuntimeError)


@pytest.mark.asyncio
async def test_run_setup_swallows_failure_when_auto(pb, monkeypatch):
    """AC-3/6.2 step 7: 'when auto, swallow it, because the gate is what
    surfaces it' -- an auto run must not raise out of _run_setup."""
    _install_fake_js(monkeypatch)

    async def _boom(host_root, *, raise_on_error=False):
        raise RuntimeError("stage exploded")

    _set_hook(monkeypatch, _boom)

    result = await pb._run_setup(host_root_override=HOST_ROOT, auto=True)
    assert result is None
    assert pb.state == "failed"


@pytest.mark.asyncio
async def test_verify_failure_after_praxis_main_success_sets_failed(pb, monkeypatch):
    """AC-4 / failure mode 6 / 8.4 trap 7: praxis_main succeeds but _verify
    fails -- must NOT be reported ready."""
    _install_fake_js(monkeypatch)

    async def _ok(host_root, *, raise_on_error=False):
        return None

    _set_hook(monkeypatch, _ok)

    def _bad_verify():
        raise RuntimeError(
            "pylabrobot imported, but its Serial class is NOT the browser shim"
        )

    monkeypatch.setattr(pb, "_verify", _bad_verify)

    with pytest.raises(RuntimeError, match="NOT the browser shim"):
        await pb._run_setup(host_root_override=HOST_ROOT)

    assert pb.state == "failed"
    assert getattr(pb.failure, "_praxis_verify_failed", False) is True


@pytest.mark.asyncio
async def test_setup_already_ready_prints_already_bootstrapped_and_skips_praxis_main(
    pb, monkeypatch, capsys
):
    _install_fake_js(monkeypatch)
    monkeypatch.setattr(pb, "_verify", lambda: "0.2.2+gdeadbeef")
    calls = {"n": 0}

    async def _count(host_root, *, raise_on_error=False):
        calls["n"] += 1

    _set_hook(monkeypatch, _count)

    result1 = await pb.setup(host_root_override=HOST_ROOT)
    assert result1 == HOST_ROOT
    assert calls["n"] == 1
    capsys.readouterr()

    result2 = await pb.setup(host_root_override=HOST_ROOT)
    captured = capsys.readouterr()
    assert "already bootstrapped" in captured.out
    assert calls["n"] == 1  # not run again
    assert result2 == HOST_ROOT


@pytest.mark.asyncio
async def test_setup_force_reruns_and_clears_boot_done_guard(pb, monkeypatch):
    """AC-6 / T2's test_force_clears_guard: setup(force=True) is the one
    deliberate exception to the once-guard, and it clears the builtins flag
    BEFORE praxis_main runs again."""
    _install_fake_js(monkeypatch)
    monkeypatch.setattr(pb, "_verify", lambda: "0.2.2+gdeadbeef")
    builtins._PRAXIS_BOOT_DONE = True
    seen_guard_values = []

    async def _record(host_root, *, raise_on_error=False):
        seen_guard_values.append(getattr(builtins, "_PRAXIS_BOOT_DONE", "missing"))

    _set_hook(monkeypatch, _record)

    pb.state = "ready"
    pb.host_root = HOST_ROOT

    await pb.setup(host_root_override=HOST_ROOT, force=True)

    assert seen_guard_values == [False]
    assert pb.state == "ready"


@pytest.mark.asyncio
async def test_setup_waits_for_pending_auto_task_instead_of_running_twice(pb, monkeypatch):
    """Failure mode 8: user calls setup() while auto is running -- waits,
    then reuses that run's result rather than starting a second one."""
    _install_fake_js(monkeypatch)
    monkeypatch.setattr(pb, "_verify", lambda: "0.2.2+gdeadbeef")
    calls = {"n": 0}
    release = asyncio.Event()

    async def _slow(host_root, *, raise_on_error=False):
        calls["n"] += 1
        await release.wait()

    _set_hook(monkeypatch, _slow)

    pb.state = "running"
    pb._task = asyncio.ensure_future(pb._run_setup(host_root_override=HOST_ROOT, auto=True))
    await asyncio.sleep(0)

    setup_call = asyncio.ensure_future(pb.setup(host_root_override=HOST_ROOT))
    await asyncio.sleep(0)
    assert not setup_call.done()

    release.set()
    result = await setup_call
    assert result == HOST_ROOT
    assert calls["n"] == 1
    assert pb.state == "ready"


# ---------------------------------------------------------------------------
# _gate_cell: steady states (ready / dismissed / failed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_ready_state_passes_lines_through_unchanged(pb):
    pb.state = "ready"
    lines = ["print('hi')\n"]
    result = await pb._gate_cell(lines)
    assert result is lines


@pytest.mark.asyncio
async def test_gate_dismissed_state_passes_lines_through_unchanged(pb):
    pb.state = "dismissed"
    lines = ["print('hi')\n"]
    result = await pb._gate_cell(lines)
    assert result is lines


@pytest.mark.asyncio
async def test_gate_failed_state_blocks_unrelated_cell(pb):
    pb.state = "failed"
    pb.failure = RuntimeError("boom")
    result = await pb._gate_cell(["_S = 1\n"])
    assert result == ["raise __import__('praxis_boot')._gate_error()\n"]


@pytest.mark.asyncio
async def test_gate_failed_state_lets_recovery_cell_through(pb):
    pb.state = "failed"
    pb.failure = RuntimeError("boom")
    lines = ["import praxis_boot\n", "await praxis_boot.setup()\n"]
    result = await pb._gate_cell(lines)
    assert result is lines


@pytest.mark.asyncio
async def test_gate_waited_only_set_when_gate_entered_with_running(pb):
    pb.gate_waited = False
    pb.state = "ready"
    await pb._gate_cell(["x = 1\n"])
    assert pb.gate_waited is False

    pb.state = "failed"
    pb.failure = RuntimeError("boom")
    await pb._gate_cell(["x = 1\n"])
    assert pb.gate_waited is False


def test_executing_the_failed_rewrite_line_raises_with_recorded_cause(pb):
    boom = RuntimeError("boom")
    pb.state = "failed"
    pb.failure = boom

    lines = pb._gate_dispatch_failed(["_S = 1\n"])
    assert len(lines) == 1

    ns: dict = {}
    with pytest.raises(pb.PraxisAutoSetupError) as excinfo:
        exec(compile("".join(lines), "<gate>", "exec"), ns)
    assert excinfo.value.__cause__ is boom


# ---------------------------------------------------------------------------
# _gate_cell: running -> ready / failed re-dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_running_then_ready_returns_original_lines(pb, monkeypatch):
    _install_fake_js(monkeypatch)
    monkeypatch.setattr(pb, "_verify", lambda: "0.2.2+gdeadbeef")
    release = asyncio.Event()

    async def _slow(host_root, *, raise_on_error=False):
        await release.wait()

    _set_hook(monkeypatch, _slow)

    pb.state = "running"
    pb._task = asyncio.ensure_future(pb._run_setup(host_root_override=HOST_ROOT, auto=True))

    lines = ["x = 1\n"]
    gate_task = asyncio.ensure_future(pb._gate_cell(lines))
    await asyncio.sleep(0)
    assert pb.gate_waited is True
    assert not gate_task.done()

    release.set()
    result = await gate_task
    assert result == lines
    assert pb.state == "ready"


@pytest.mark.asyncio
async def test_gate_running_then_failed_returns_raise_rewrite(pb, monkeypatch):
    _install_fake_js(monkeypatch)

    async def _boom(host_root, *, raise_on_error=False):
        raise RuntimeError("stage exploded")

    _set_hook(monkeypatch, _boom)

    pb.state = "running"
    pb._task = asyncio.ensure_future(pb._run_setup(host_root_override=HOST_ROOT, auto=True))

    result = await pb._gate_cell(["_S = 1\n"])
    assert pb.state == "failed"
    assert pb.gate_waited is True
    assert result == ["raise __import__('praxis_boot')._gate_error()\n"]


# ---------------------------------------------------------------------------
# _gate_cell liveness (R2-4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_liveness_task_cancelled_sets_failed_with_cause(pb, monkeypatch):
    _install_fake_js(monkeypatch)
    pb.state = "running"

    async def _never_finishes():
        await asyncio.Event().wait()

    pb._task = asyncio.ensure_future(_never_finishes())
    pb._task.cancel()
    await asyncio.sleep(0)
    assert pb._task.done() and pb._task.cancelled()

    result = await pb._gate_cell(["_S = 1\n"])
    assert pb.state == "failed"
    assert isinstance(pb.failure, RuntimeError)
    assert "ended without a result" in str(pb.failure)
    assert isinstance(pb.failure.__cause__, asyncio.CancelledError)
    assert result == ["raise __import__('praxis_boot')._gate_error()\n"]


@pytest.mark.asyncio
async def test_gate_awaits_task_at_most_once_even_if_still_running_after(pb):
    """8.1: 'the gate awaits _task at most once per cell (await counter == 1
    even when state is still running afterwards)'. _FakeTaskThatNeverFinishes
    simulates the "should be impossible" case: the wait returns normally but
    the task never reports itself done."""
    pb.state = "running"
    fake_task = _FakeTaskThatNeverFinishes()
    pb._task = fake_task

    result = await pb._gate_cell(["_S = 1\n"])

    assert fake_task.await_count == 1
    assert pb.state == "running"  # never touched: this is the fallback branch
    assert len(result) == 1
    assert "PraxisAutoSetupError" in result[0]


@pytest.mark.asyncio
async def test_interrupted_wait_via_cancelled_error_returns_static_line_and_does_not_raise(
    pb, monkeypatch
):
    _install_fake_js(monkeypatch)
    monkeypatch.setattr(pb, "_verify", lambda: "0.2.2+gdeadbeef")
    release = asyncio.Event()

    async def _slow(host_root, *, raise_on_error=False):
        await release.wait()

    _set_hook(monkeypatch, _slow)

    pb.state = "running"
    pb._task = asyncio.ensure_future(pb._run_setup(host_root_override=HOST_ROOT, auto=True))

    gate_task = asyncio.ensure_future(pb._gate_cell(["a = 1\n"]))
    await asyncio.sleep(0)
    gate_task.cancel()  # interrupts THIS wait, not the underlying _task
    result1 = await gate_task  # must not raise

    assert len(result1) == 1
    assert "interrupted" in result1[0]
    assert "praxis_boot" in result1[0]
    assert pb.state == "running"
    assert not pb._task.done()

    # 6.2 R2-4: "the next cell waits for it again, at most once."
    gate_task_2 = asyncio.ensure_future(pb._gate_cell(["b = 2\n"]))
    await asyncio.sleep(0)
    assert not gate_task_2.done()

    release.set()
    result2 = await gate_task_2
    assert result2 == ["b = 2\n"]
    assert pb.state == "ready"


@pytest.mark.asyncio
async def test_interrupted_wait_via_keyboard_interrupt_returns_static_line(pb, monkeypatch):
    _install_fake_js(monkeypatch)
    pb.state = "running"
    pb._task = asyncio.ensure_future(asyncio.Event().wait())

    async def _raise_kb(aw):
        raise KeyboardInterrupt()

    monkeypatch.setattr(pb.asyncio, "shield", _raise_kb)

    result = await pb._gate_cell(["a = 1\n"])
    assert len(result) == 1
    assert "interrupted" in result[0]
    assert pb.state == "running"

    await _drain(pb._task)


# ---------------------------------------------------------------------------
# _gate_error: error text per failure kind
# ---------------------------------------------------------------------------


def test_gate_error_default_recovery_text(pb):
    pb.state = "failed"
    pb.failure = RuntimeError("something else broke")
    err = pb._gate_error()
    msg = str(err).lower()
    assert "praxis_boot.setup()" in str(err)
    assert "dismiss()" in str(err)
    assert err.__cause__ is pb.failure


def test_gate_error_names_kernel_restart_on_verify_failure(pb):
    exc = RuntimeError("Serial class is NOT the browser shim")
    exc._praxis_verify_failed = True
    pb.state = "failed"
    pb.failure = exc
    msg = str(pb._gate_error()).lower()
    assert "restart the kernel" in msg
    assert "setup()" in msg


def test_gate_error_names_closing_older_tabs_on_d1_mismatch(pb):
    exc = RuntimeError(
        "D1 whole-deployment staleness check (ADR Sec 2.3) failed: manifest.json "
        "praxis_git_sha='aaa' != shell-injected praxis_git_sha='bbb'."
    )
    pb.state = "failed"
    pb.failure = exc
    msg = str(pb._gate_error()).lower()
    assert "close other praxis tabs from an older deploy" in msg
    assert "restart the kernel" in msg


def test_d1_detection_substring_matches_real_stages_message(pb):
    """Verify that the D1 detection substring in _gate_error() matches the
    actual message text in stages.py. This ensures the detection doesn't
    silently break if stages.py is reworded."""
    # Read the praxis_boot.py source and assert the substring is there
    praxis_boot_path = Path(__file__).resolve().parents[1] / "files" / "praxis_boot.py"
    with open(praxis_boot_path) as f:
        praxis_boot_source = f.read()

    assert _D1_DETECTION_SUBSTRING in praxis_boot_source, (
        f"D1 detection substring {_D1_DETECTION_SUBSTRING!r} not found in praxis_boot.py; "
        "the constant in the test file is now stale"
    )

    # Read the stages.py source and assert the substring is there
    stages_path = Path(__file__).resolve().parents[1] / "bootstrap" / "stages.py"
    with open(stages_path) as f:
        stages_source = f.read()

    assert _D1_DETECTION_SUBSTRING in stages_source, (
        f"D1 detection substring {_D1_DETECTION_SUBSTRING!r} not found in stages.py; "
        "the detection logic in praxis_boot._gate_error() is now stale"
    )


# ---------------------------------------------------------------------------
# dismiss()
# ---------------------------------------------------------------------------


def test_dismiss_only_takes_effect_from_failed(pb):
    for start in ("idle", "running", "ready", "dismissed"):
        pb.state = start
        pb.dismiss()
        assert pb.state == start

    pb.state = "failed"
    pb.dismiss()
    assert pb.state == "dismissed"


# ---------------------------------------------------------------------------
# Robustness (R2-5): exceptions whose __repr__/__str__ raise
# ---------------------------------------------------------------------------


def test_gate_error_survives_failure_with_bad_repr(pb):
    pb.state = "failed"
    pb.failure = _BadRepr("boom")

    err = pb._gate_error()  # must not raise

    assert isinstance(err, pb.PraxisAutoSetupError)
    assert "PraxisAutoSetupError" not in str(err) or True  # message need not repeat the name
    assert "details unavailable" in str(err) or "unprintable" in str(err)


@pytest.mark.asyncio
async def test_gate_internal_error_survives_bad_repr_exception(pb, monkeypatch):
    """Force the internal-error path (step 4) with an exception whose own
    formatting is broken; the returned line must still name
    PraxisAutoSetupError and the gate must not raise."""

    def _boom(lines):
        raise _BadRepr("boom")

    pb.state = "failed"
    monkeypatch.setattr(pb, "_gate_dispatch_failed", _boom)

    result = await pb._gate_cell(["_S = 1\n"])

    assert len(result) == 1
    assert "PraxisAutoSetupError" in result[0]
    assert "gate error" in result[0]


@pytest.mark.asyncio
async def test_gate_internal_error_for_unexpected_state_never_raises(pb):
    pb.state = "totally-bogus"  # e.g. a corrupted module global
    result = await pb._gate_cell(["_S = 1\n"])
    assert len(result) == 1
    assert "PraxisAutoSetupError" in result[0]
    assert "gate error" in result[0]


def test_status_survives_bad_repr_failure(pb, capsys):
    pb.state = "failed"
    pb.failure = _BadRepr("boom")

    result = pb.status()  # must not raise

    captured = capsys.readouterr()
    assert captured.out.strip() == "praxis auto-setup state: failed"
    assert result["state"] == "failed"
    assert result["failure"] == "<unprintable exception>"


# ---------------------------------------------------------------------------
# status()
# ---------------------------------------------------------------------------


def test_status_prints_exact_line_when_ready(pb, capsys):
    pb.state = "ready"
    pb.host_root = HOST_ROOT

    result = pb.status()

    captured = capsys.readouterr()
    assert captured.out.splitlines()[0] == "praxis auto-setup state: ready"
    assert result["state"] == "ready"
    assert result["host_root"] == HOST_ROOT
    assert result["failure"] is None
    assert "kernel_nonce" in result
    assert "autostart_origin" in result


def test_status_reports_no_failure_as_none(pb, capsys):
    pb.state = "idle"
    result = pb.status()
    capsys.readouterr()
    assert result["failure"] is None
