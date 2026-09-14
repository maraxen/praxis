"""§4.5: the ConcurrencyProbe protocol, its None -> blocked mapping rule,
and the MVP KernelExecutionProbe reading the two named in-process sources.

The signal is kernel-resident and read at call time: ``ExecutionFlag`` (the
Coxswain executor's reentrancy counter) OR'd with ``DispatchWatch`` (a wrapper
over the resident LiquidHandler's dispatch entrypoint, covering notebook-cell
PLR calls). ``None`` -- the probe cannot determine the signal, e.g. the
DispatchWatch failed to install at init -- must map to ``blocked:concurrent``
at the cue, never to continue (NFR-5 fail-closed).

Named residual gap (recorded in spec §4.5, not discovered later): a PLR call
reaching hardware by a path that bypasses both sources is invisible to an
in-process probe. That is why cue 3 and FR-6's confirm-time re-check exist.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from coxswain.runtime.execution_flag import (
    EXECUTION_FLAG,
    DispatchWatch,
    ExecutionFlag,
)

__all__ = ["ConcurrencyProbe", "KernelExecutionProbe"]


@runtime_checkable
class ConcurrencyProbe(Protocol):
    """Cue 0's signal source. ``None`` == cannot determine -> blocked."""

    def is_active(self) -> bool | None: ...


class KernelExecutionProbe:
    """MVP probe: OR of the two in-process §4.5 sources.

    - ExecutionFlag depth > 0  -> True
    - DispatchWatch depth > 0  -> True
    - watch not installed      -> None (unknown; blocks upstream)
    - both zero                -> False
    """

    def __init__(
        self,
        *,
        execution_flag: ExecutionFlag | None = None,
        dispatch_watch: DispatchWatch | None = None,
    ) -> None:
        # Defaults are the shared kernel instances: production wiring needs no
        # arguments; tests inject isolated counters.
        self._flag = execution_flag if execution_flag is not None else EXECUTION_FLAG
        self._watch = dispatch_watch if dispatch_watch is not None else DispatchWatch()

    def is_active(self) -> bool | None:
        if self._flag.depth > 0:
            return True
        if not self._watch.installed:
            return None
        return self._watch.depth > 0
