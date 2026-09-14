"""Kernel-resident reentrancy tracking (§4.5, RISK-7).

Two in-process concurrency sources, both living in the same interpreter as
the FFT gate so reading them is a local attribute read with no round trip:

- ``ExecutionFlag`` -- a module-level reentrancy counter that ``execute.py``
  (W3) increments before dispatching any PLR call and decrements in a
  ``finally``. Covers every Coxswain-initiated execution.
- ``DispatchWatch`` -- a counter kept by a thin wrapper installed over the
  resident ``LiquidHandler``'s dispatch entrypoint at Coxswain init. Covers
  PLR calls a user issues directly from a notebook cell, which the kernel,
  though single-threaded, can interleave with a gate pass across an ``await``
  window.

NFR-1: pure Python, no ``import js``, CPython-importable.
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Final

__all__ = ["EXECUTION_FLAG", "DispatchWatch", "ExecutionFlag"]


class ExecutionFlag:
    """Reentrancy depth counter for Coxswain-initiated PLR execution."""

    def __init__(self) -> None:
        self._depth: int = 0

    @property
    def depth(self) -> int:
        return self._depth

    def increment(self) -> None:
        self._depth += 1

    def decrement(self) -> None:
        if self._depth <= 0:
            raise RuntimeError("ExecutionFlag.decrement below zero: unbalanced release")
        self._depth -= 1

    def active(self) -> _execution_flag_active:
        """Context manager: increment on entry, always decrement on exit."""
        return _execution_flag_active(self)


class _execution_flag_active:
    """Bound-context helper (kept module-level so ExecutionFlag stays picklable
    by value-free state and introspectable)."""

    def __init__(self, flag: ExecutionFlag) -> None:
        self._flag = flag

    def __enter__(self) -> ExecutionFlag:
        self._flag.increment()
        return self._flag

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._flag.decrement()


#: §4.5 source 1. execute.py uses this shared instance.
EXECUTION_FLAG: Final[ExecutionFlag] = ExecutionFlag()


class DispatchWatch:
    """Counter + wrapper installer over an arbitrary object's dispatch
    entrypoint. The wrapped method raises the depth for the duration of the
    underlying call (sync or async) and always restores it in a ``finally``."""

    def __init__(self) -> None:
        self._depth: int = 0
        self._installed: bool = False
        self._owner: Any = None
        self._name: str | None = None
        self._original: Any = None

    @property
    def depth(self) -> int:
        return self._depth

    @property
    def installed(self) -> bool:
        return self._installed

    def install(self, owner: Any, entrypoint: str = "dispatch") -> bool:
        """Wrap ``owner.<entrypoint>`` with the counter. Returns False (and
        leaves the probe-facing state at not-installed) when the attribute is
        missing or not callable -- an installation failure must surface as
        ``None`` upstream, never as a silent 'not active'."""
        target = getattr(owner, entrypoint, None)
        if not callable(target):
            return False
        watch = self

        if inspect.iscoroutinefunction(target):

            @functools.wraps(target)
            async def async_wrapper(*args: Any, **kwargs: Any):
                watch._depth += 1
                try:
                    return await target(*args, **kwargs)
                finally:
                    watch._depth -= 1

            wrapper = async_wrapper
        else:

            @functools.wraps(target)
            def sync_wrapper(*args: Any, **kwargs: Any):
                watch._depth += 1
                try:
                    return target(*args, **kwargs)
                finally:
                    watch._depth -= 1

            wrapper = sync_wrapper

        setattr(owner, entrypoint, wrapper)
        self._owner = owner
        self._name = entrypoint
        self._original = target
        self._installed = True
        return True

    def uninstall(self) -> None:
        if self._installed and self._owner is not None and self._name is not None:
            setattr(self._owner, self._name, self._original)
        self._owner = None
        self._name = None
        self._original = None
        self._installed = False
