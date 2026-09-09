"""The async verifier (P2.2 deliverable 1).

verify(call_sequence, intent_record, backend="LiquidHandlerChatterboxBackend")
-> {passed, error?, state_before, state_after, checks}

Run pattern mirrors chatterbox_runner.run_single (:539-588): DeckFactory
setup -> await lh.setup() -> execute -> await lh.stop() in finally.  During
the run the global PLR strictness is set to STRICT and both trackers (tips +
volume) are enabled; every global is restored afterwards.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import time
from typing import Any, Mapping, Sequence

from pylabrobot.liquid_handling.strictness import (
    Strictness,
    get_strictness,
    set_strictness,
)
from pylabrobot.resources import set_tip_tracking, set_volume_tracking

from verify.checks import Check, ExecutedCall, run_all_checks
from verify.deck import DeckLayout, SetupHandle, build_setup, infer_layout
from verify.dispatcher import plan_call

__all__ = ["LH_BACKENDS", "UnsupportedBackendError", "verify"]

#: Registry subset this harness supports (liquid handling only; the plate
#: reader chatterbox has no tip/volume tracker story for AC-2.2.2).
LH_BACKENDS = {
    "LiquidHandlerChatterboxBackend": {"num_channels": 8},
    "STARChatterboxBackend": {"num_channels": 8, "core96_head_installed": True},
}

DEFAULT_TOLERANCE_UL = 1e-6


class UnsupportedBackendError(ValueError):
    """backend= must name a liquid-handler chatterbox from CHATTERBOX_REGISTRY."""


async def _execute(setup: SetupHandle, call_sequence, *, strict: bool):
    """Plan + await each call; returns executed calls (possibly partial)."""
    executed: list[ExecutedCall] = []
    for i, call in enumerate(call_sequence):
        plan = plan_call(call, i, setup, strict=strict)
        await plan.method(**plan.kwargs)
        executed.append(ExecutedCall(index=i, tool=call.get("name"),
                                     kwargs=plan.kwargs, plan_result=plan))
    return executed


async def verify(
    call_sequence: Sequence[Mapping[str, Any]],
    intent_record: Mapping[str, Any],
    *,
    backend: str = "LiquidHandlerChatterboxBackend",
    layout: DeckLayout | Mapping[str, Any] | None = None,
    volume_tolerance_ul: float = DEFAULT_TOLERANCE_UL,
    strict: bool = True,
) -> dict[str, Any]:
    """Execute a call sequence on a chatterbox deck and grade it.

    Args:
        call_sequence: [{name, params}] with canonical param names and ref
            strings ("source_plate.A1"); may deviate from the intent record --
            deviations are what the agreement axis exists to catch.
        intent_record: coxswain.plr.intent_record.IntentRecord-shaped mapping.
        backend: key of LH_BACKENDS / CHATTERBOX_REGISTRY["LiquidHandler"].
        layout: optional explicit DeckLayout (or its dict form); inferred from
            the calls when omitted.
        volume_tolerance_ul: absolute tolerance for volume post-conditions.
        strict: set STRICT during the run (default per AC-2.2.1); anomalies
            (params outside the canonical namespace) fail the verification.

    Returns:
        {passed, error, state_before, state_after, checks, bindings,
         elapsed_ms, backend, record_id}
    """
    if backend not in LH_BACKENDS:
        raise UnsupportedBackendError(
            f"backend {backend!r}; supported: {sorted(LH_BACKENDS)}"
        )
    if layout is not None and not isinstance(layout, DeckLayout):
        layout = DeckLayout(**layout)
    explicit_names: set[str] = set()
    if layout is not None:
        explicit_names = set(layout.resources) | set(layout.holders)
    base_layout = infer_layout(call_sequence, exclude=explicit_names)
    effective_layout = base_layout.merged(layout)

    t0 = time.monotonic()
    error: str | None = None
    executed: list[ExecutedCall] = []
    setup: SetupHandle | None = None
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    # 260903 (spec §14.6, volume increment 5, round-1 O5, T27, backlog
    # #4959): the volume family's hypothesis (`env`'s "does_volume_tracking"
    # member) must be OBSERVED from inside the window that actually turns
    # tracking on -- never from outside it (a process-wide call after this
    # function returns races the `finally` restore below). Additive result
    # key, default False (unobserved: the deck_build failure path below
    # never reaches the `set_volume_tracking(True)` call).
    volume_tracking_observed = False

    old_strictness = get_strictness()
    old_volume_tracking = _current_volume_tracking()
    old_tip_tracking = _current_tip_tracking()

    try:
        setup = build_setup(backend, effective_layout)
        # Snapshot BEFORE any execution, after seeding.
        before = setup.snapshot()

        set_strictness(Strictness.STRICT if strict else Strictness.WARN)
        set_volume_tracking(True)
        set_tip_tracking(True)
        # Observed HERE, inside the window `set_volume_tracking(True)` just
        # opened and the `finally` below will close -- not after `verify`
        # returns, which is what a process-wide call from outside this
        # function would race (§14.6's normative box).
        volume_tracking_observed = _current_volume_tracking()

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            await setup.machine.setup()          # chatterbox prints; captured
            try:
                executed = await _execute(setup, call_sequence, strict=strict)
            except Exception as e:  # noqa: BLE001 - reported, not raised
                error = f"{type(e).__name__}: {e}"
            finally:
                with contextlib.suppress(Exception):
                    await setup.machine.stop()   # proper teardown, always
        del buf  # chatterbox chatter intentionally suppressed

        after = setup.snapshot()
    except Exception as e:  # noqa: BLE001 - harness/deck-level failure
        error = f"{type(e).__name__}: {e}"
        if setup is not None:
            if before is None:
                before = setup.snapshot()
            after = setup.snapshot()
        else:
            return {
                "passed": False,
                "error": error,
                "state_before": None,
                "state_after": None,
                "checks": [Check("deck_build", False, str(e)).as_dict()],
                "bindings": [],
                "elapsed_ms": (time.monotonic() - t0) * 1000,
                "backend": backend,
                "record_id": intent_record.get("record_id")
                if isinstance(intent_record, Mapping) else None,
                "volume_tracking_observed": volume_tracking_observed,
            }
    finally:
        set_strictness(old_strictness)
        set_volume_tracking(old_volume_tracking)
        set_tip_tracking(old_tip_tracking)

    checks = run_all_checks(
        list(call_sequence), intent_record, executed, before, after,
        volume_tolerance_ul, error,
    )

    bindings = [
        {
            "call_index": b.call_index, "tool": b.tool, "arg": b.arg,
            "plr_arg": b.plr_arg, "ref": b.ref, "kind": b.kind,
            "resolved": b.resolved,
        }
        for call in executed
        for b in call.plan_result.bindings
    ]

    passed = all(c.passed for c in checks)
    return {
        "passed": passed,
        "error": error,
        "state_before": before,
        "state_after": after,
        "checks": [c.as_dict() for c in checks],
        "bindings": bindings,
        "elapsed_ms": (time.monotonic() - t0) * 1000,
        "backend": backend,
        "record_id": intent_record.get("record_id") if isinstance(intent_record, Mapping) else None,
        # 260903 (spec §14.6, volume increment 5, round-1 O5, T27): the
        # `does_volume_tracking()` hypothesis, observed from INSIDE the
        # window `set_volume_tracking(True)` opened above -- the harness
        # reads this field to build `env`, never calling the tracking
        # callable itself from outside this function.
        "volume_tracking_observed": volume_tracking_observed,
    }


# --- tracking-flag readback helpers (module-level globals in PLR) ----------

def _current_volume_tracking() -> bool:
    from pylabrobot.resources.volume_tracker import does_volume_tracking
    return does_volume_tracking()


def _current_tip_tracking() -> bool:
    from pylabrobot.resources.tip_tracker import does_tip_tracking
    return does_tip_tracking()


def run_verify_sync(**kwargs) -> dict[str, Any]:
    """Convenience sync wrapper used by the CLI and tests."""
    return asyncio.run(verify(**kwargs))
