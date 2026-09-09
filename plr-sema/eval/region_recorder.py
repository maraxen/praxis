"""The tier-2b executed-ground-truth recorder (spec 260903
`260903_plr-sema-real-programs-increment.md` §12.4.2, backlog #4880/T21,
AC-12.17).

**Not `plan_call`** (round-1 O1). A region fixture is a real coroutine
containing a real Python ``for``/``while``/``if`` -- it is executed
directly (``await protocol(lh, ...)``), never replayed as a
``call_sequence`` list, so ``training/verify/dispatcher.py``'s
``plan_call`` -- reached only from ``verifier.py``'s own
``for i, call in enumerate(call_sequence)`` loop -- structurally cannot
observe anything inside a real loop body. This module wraps the tool
methods on the receiver **instance** ``build_setup`` returns instead.

**Instance-level, not class-level.** :meth:`RegionRecorder.install` sets a
bound-method-shaped attribute directly on the receiver *object*
(``setup.machine``), never on ``type(setup.machine)`` -- so nothing global
is patched and no other test (or concurrent fixture run) can observe the
wrap. :meth:`RegionRecorder.uninstall` removes the instance attribute,
which reveals the class's own method again (Python attribute lookup falls
through instance -> class when the instance ``__dict__`` entry is
deleted) -- the class object itself is never touched.

**The call-site key is the CALLER's source line**, read via
``sys._getframe(1).f_lineno`` from inside the wrapper -- frame 0 is the
wrapper's own body, frame 1 is whichever fixture statement is doing the
``await lh.pick_up_tips(...)``. A monotonic per-key visit counter turns
repeat visits of the same source line (a loop body revisited on each
iteration) into an ordered ``visit_index`` sequence -- 1, 2, 3, ... --
which is what lets :mod:`region_oracle` line an executed visit up against
the static side's unrolled ``iteration N`` findings (spec §12.3.4 point 2).
"""

from __future__ import annotations

import dataclasses
import functools
import sys
from collections.abc import Callable, Sequence
from typing import Any

__all__ = [
    "VisitRecord",
    "RegionRecorder",
    "DuplicateCallSiteError",
]


class DuplicateCallSiteError(RuntimeError):
    """Two operations in one extracted graph share a ``(method_name,
    lineno)`` key -- spec §12.4.2's fixture-design constraint ("each
    fixture body therefore contains at most one call site per PLR method
    per region body") is genuinely violated (two call sites of the same
    method on the SAME source line, e.g. inside the same straight-line
    body). Raised loudly rather than silently overwriting -- the join is a
    LOOKUP, not a heuristic (§12.4.2).
    """


@dataclasses.dataclass(frozen=True, slots=True)
class VisitRecord:
    """One executed call, in the shape §12.4.2 specifies:
    ``(method_name, lineno, visit_index, outcome)``. ``outcome`` is
    ``"ran_ok"`` or ``"raised:<ExcClass>"`` -- never the exception object
    itself (this record must be diffable/JSON-able for the report).
    """

    method: str
    lineno: int
    visit_index: int
    outcome: str


class RegionRecorder:
    """Wraps a fixed set of async tool methods on one receiver INSTANCE.

    ``methods`` is the candidate method-name set to wrap (typically
    ``plr_sema.check._supported_tools.SUPPORTED_TOOLS`` -- the DYNAMIC
    execution harness's own capability boundary, §12.4.2's "the method set
    to wrap is the receiver class's own methods that appear as contract
    keys -- derived, not typed"); a name absent from ``type(receiver)`` is
    silently skipped (not every fixture calls every tool method), never an
    error.
    """

    def __init__(self, receiver: Any, methods: Sequence[str]) -> None:
        self._receiver = receiver
        self._methods = tuple(methods)
        self._originals: dict[str, Callable[..., Any]] = {}
        self._visit_counts: dict[tuple[str, int], int] = {}
        self.records: list[VisitRecord] = []
        self._installed = False

    def install(self) -> None:
        if self._installed:
            raise RuntimeError("RegionRecorder.install() called twice on one recorder")
        for name in self._methods:
            if not hasattr(type(self._receiver), name):
                continue
            bound_original = getattr(self._receiver, name)
            self._originals[name] = bound_original
            setattr(self._receiver, name, self._make_wrapper(name, bound_original))
        self._installed = True

    def uninstall(self) -> None:
        """Remove every instance-level shim, restoring plain attribute
        lookup through to the class's own method (AC-12.17(iv): "the
        wrapper is removed on teardown and the class object is
        unmodified, tested by asserting the unbound method is the
        original after the run").
        """
        if not self._installed:
            return
        instance_dict = self._receiver.__dict__
        for name in self._originals:
            if name in instance_dict:
                del instance_dict[name]
        self._originals.clear()
        self._installed = False

    def _make_wrapper(self, name: str, original: Callable[..., Any]) -> Callable[..., Any]:
        recorder = self

        @functools.wraps(original)
        async def _shim(*args: Any, **kwargs: Any) -> Any:
            # frame 0 is this shim; frame 1 is the fixture statement that
            # awaited `lh.<name>(...)` -- the call-site identity §12.4.2
            # specifies, independent of how many times this exact line is
            # revisited by a loop.
            caller_lineno = sys._getframe(1).f_lineno
            key = (name, caller_lineno)
            visit_index = recorder._visit_counts.get(key, 0) + 1
            recorder._visit_counts[key] = visit_index
            try:
                result = await original(*args, **kwargs)
            except Exception as exc:
                recorder.records.append(
                    VisitRecord(name, caller_lineno, visit_index, f"raised:{type(exc).__name__}")
                )
                raise
            recorder.records.append(VisitRecord(name, caller_lineno, visit_index, "ran_ok"))
            return result

        return _shim

    def by_key(self) -> dict[tuple[str, int], list[VisitRecord]]:
        """``{(method, lineno): [VisitRecord, ...]}`` in visit order --
        the executed side's own join key, mirroring the static side's
        ``(method_name, line_number)`` grouping.
        """
        out: dict[tuple[str, int], list[VisitRecord]] = {}
        for record in self.records:
            out.setdefault((record.method, record.lineno), []).append(record)
        return out

    @property
    def raised(self) -> VisitRecord | None:
        """The single record whose outcome starts with ``"raised:"``, or
        ``None`` -- at most one can exist per run (an exception propagates
        out of ``protocol(...)`` and stops the harness's own execution;
        see :mod:`region_oracle`'s ``run_fixture``).
        """
        for record in self.records:
            if record.outcome.startswith("raised:"):
                return record
        return None


def build_static_join_map(
    call_sites: Sequence[tuple[str, int, str]],
) -> dict[tuple[str, int], str]:
    """``(method_name, lineno) -> operation_id`` from an iterable of
    ``(method_name, lineno, operation_id)`` triples (one per non-``REGION``
    ``CALL`` operation in an extracted graph). Raises
    :class:`DuplicateCallSiteError` -- loudly, not a silent
    last-write-wins overwrite -- the moment two triples share their
    ``(method_name, lineno)`` prefix (spec §12.4.2's fixture-design
    constraint / AC-12.17(iii)'s "registering a duplicate ... raises
    rather than overwriting").
    """
    out: dict[tuple[str, int], str] = {}
    for method_name, lineno, operation_id in call_sites:
        key = (method_name, lineno)
        if key in out:
            raise DuplicateCallSiteError(
                f"duplicate call site (method={method_name!r}, lineno={lineno}): "
                f"operation {out[key]!r} already registered this key, "
                f"cannot also register {operation_id!r} -- §12.4.2 requires at most "
                f"one call site per method per fixture body"
            )
        out[key] = operation_id
    return out
