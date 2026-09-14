"""AC-16 / §4.5: the ConcurrencyProbe is backed by real reads of its two
named in-process sources -- ExecutionFlag and DispatchWatch.

A probe whose is_active() ignores its sources cannot pass: each test flips a
source and asserts the return value flips with it. None (source not
installed) maps to a blocked:concurrent exit, never continue (NFR-5).
"""

import asyncio

import pytest

from coxswain.fft import concurrency as conc
from coxswain.runtime import execution_flag as ef


class _FakeLiquidHandler:
    def __init__(self) -> None:
        self.dispatched: list[str] = []

    async def dispatch(self, call_name: str) -> str:
        self.dispatched.append(call_name)
        return f"ok:{call_name}"


# --- ExecutionFlag: module-level reentrancy counter ---------------------------


def test_execution_flag_counts_depth() -> None:
    flag = ef.ExecutionFlag()
    assert flag.depth == 0
    flag.increment()
    flag.increment()
    assert flag.depth == 2
    flag.decrement()
    flag.decrement()
    assert flag.depth == 0


def test_execution_flag_decrement_below_zero_is_refused() -> None:
    flag = ef.ExecutionFlag()
    flag.increment()
    flag.decrement()
    with pytest.raises(Exception):
        flag.decrement()


def test_execution_flag_context_manager_releases_on_exception() -> None:
    flag = ef.ExecutionFlag()
    with pytest.raises(RuntimeError):
        with flag.active():
            assert flag.depth == 1
            raise RuntimeError("boom")
    assert flag.depth == 0


def test_module_level_singleton_exists() -> None:
    """§4.5: execute.py increments THE module-level counter; it must exist
    without any construction step so every caller shares one instance."""
    assert isinstance(ef.EXECUTION_FLAG, ef.ExecutionFlag)


# --- DispatchWatch: wrapper installer over a dispatch entrypoint --------------


def test_dispatch_watch_wraps_and_counts_async_calls() -> None:
    lh = _FakeLiquidHandler()
    watch = ef.DispatchWatch()
    assert watch.install(lh, "dispatch") is True
    assert asyncio.run(lh.dispatch("aspirate")) == "ok:aspirate"
    assert lh.dispatched == ["aspirate"]
    assert watch.depth == 0  # released after the call completes


def test_dispatch_watch_uninstall_restores_original() -> None:
    lh = _FakeLiquidHandler()
    original = lh.dispatch
    watch = ef.DispatchWatch()
    watch.install(lh, "dispatch")
    watch.uninstall()
    assert lh.dispatch.__func__ is original.__func__  # noqa: B004 -- bound methods are fresh objects
    assert watch.installed is False


def test_dispatch_watch_install_failure_reports_not_installed() -> None:
    class _NoMethod:
        pass

    watch = ef.DispatchWatch()
    assert watch.install(_NoMethod(), "dispatch") is False
    assert watch.installed is False


def test_dispatch_watch_releases_on_async_exception() -> None:
    class _Boom:
        async def dispatch(self, name: str) -> str:
            raise RuntimeError("hw fault")

    obj = _Boom()
    watch = ef.DispatchWatch()
    watch.install(obj, "dispatch")
    with pytest.raises(RuntimeError):
        asyncio.run(obj.dispatch("x"))
    assert watch.depth == 0


# --- KernelExecutionProbe: OR of the two sources ------------------------------


def test_probe_false_when_all_sources_zero() -> None:
    """Both sources live, both at depth zero -> not active."""
    lh = _FakeLiquidHandler()
    watch = ef.DispatchWatch()
    assert watch.install(lh, "dispatch") is True
    probe = conc.KernelExecutionProbe(execution_flag=ef.ExecutionFlag(), dispatch_watch=watch)
    assert probe.is_active() is False


def test_probe_true_when_execution_flag_nonzero() -> None:
    """AC-16 assertion 1."""
    flag = ef.ExecutionFlag()
    lh = _FakeLiquidHandler()
    watch = ef.DispatchWatch()
    watch.install(lh, "dispatch")
    probe = conc.KernelExecutionProbe(execution_flag=flag, dispatch_watch=watch)
    flag.increment()
    assert probe.is_active() is True
    flag.decrement()
    assert probe.is_active() is False


def test_probe_true_when_only_dispatch_watch_nonzero() -> None:
    """AC-16 assertion 2: source 2 exists because notebook-cell PLR calls
    bypass Coxswain's own executor; the probe must see them even when
    ExecutionFlag is zero."""
    rec_values: list[bool | None] = []

    class _RecordingHandler:
        async def dispatch(self, name: str) -> str:
            rec_values.append(probe.is_active())
            return name

    flag = ef.ExecutionFlag()
    lh = _RecordingHandler()
    watch = ef.DispatchWatch()
    assert watch.install(lh, "dispatch") is True
    probe = conc.KernelExecutionProbe(execution_flag=flag, dispatch_watch=watch)

    assert probe.is_active() is False  # nothing running yet
    asyncio.run(lh.dispatch("transfer"))
    assert rec_values == [True], "probe must see the raised watch depth mid-call"


def test_probe_none_when_watch_failed_to_install() -> None:
    """§4.5: DispatchWatch failed to install at init is itself an unknown and
    must block -- None, not False."""
    watch = ef.DispatchWatch()  # never installed
    probe = conc.KernelExecutionProbe(execution_flag=ef.ExecutionFlag(), dispatch_watch=watch)
    assert probe.is_active() is None


def test_protocol_declares_is_active() -> None:
    assert hasattr(conc.ConcurrencyProbe, "is_active")
