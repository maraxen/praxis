"""plr_sema.telemetry: emission surface for analyzer events (spec 260901 §4).

**FAILURE_CATEGORIES is promoted verbatim from
``training/verify/failure_taxonomy.py:71-78``.** That module's own docstring
(``:17-34``) records why each category exists for the *dynamic* execution
harness it was coined for; reproduced here because it is the justification
for freezing the set rather than re-deriving it:

* a REAL bug in our own harness/synth code (``shape_mismatch``) -- should
  trend toward zero; any nonzero count here after a bug-fixing pass is a
  strong signal something in OUR code is still wrong.
* a mined/generated call referencing something that doesn't exist on the
  deck at all (``ungroundable_reference``) -- usually a miner/synth
  reference-construction bug, occasionally a genuinely bad teacher value.
* a call that is well-formed and correctly grounded, but the harness's
  SYNTHESIZED, single-call (or short-prefix) setup didn't establish the
  physical/deck STATE the real call sequence assumes (``precondition_state``,
  e.g. ``NoTipError`` on a call that needs more channels than the synthetic
  prefix armed) -- tells us about a structural limitation of ISOLATED-call
  verification, not a defect in the mined/generated call itself.
* a call that ran to completion without raising, but our own post-condition
  checks (tip/volume-delta) caught a real semantic mismatch between what the
  call claims and what actually happened (``postcondition_mismatch``) --
  the highest-value category for catching real generation defects.
* a tool with no LiquidHandler-chatterbox execution path at all
  (``unsupported_tool``) -- a scope boundary, not a defect signal.
* anything else (``harness_internal``) -- a bug in the verify/exec_verify
  plumbing itself, not signal about the generated or mined data.

**Static re-interpretation (spec §4.1).** The 6-set was validated at corpus
scale for a *dynamic* harness. plr-sema is a *static* analyzer, so four of
the six categories mean something different here, and one is presently
unreachable:

| category                | dynamic meaning (verify/)          | static meaning (plr-sema)                                          |
|--------------------------|-------------------------------------|---------------------------------------------------------------------|
| ``precondition_state``   | a PLR exception escaped at runtime  | a derived guard is statically established to fire                   |
| ``postcondition_mismatch``| ran clean, but effect checks disagreed | **unreachable in v1** -- no effects are simulated. Reserved.     |
| ``shape_mismatch``       | ``DispatchError`` -- bad call shape | arity/keyword mismatch against the derived signature                |
| ``ungroundable_reference``| ``GroundingError`` -- no such deck object | a resource variable with no ``ResourceNode`` in the graph      |
| ``unsupported_tool``     | method outside ``SUPPORTED_TOOLS``  | method not resolvable to any entry in the whole-survey derived contract table (260901 T11 -- no longer ``SUPPORTED_TOOLS``, which is now the DYNAMIC harness's own boundary only; see ``plr_sema.check`` module docstring) |
| ``harness_internal``     | analyzer/plumbing bug               | same; always paired with ``reason="internal_error"``                 |

``postcondition_mismatch`` being unreachable in v1 is recorded here so a
zero count in the gap ledger (spec §7.4) reads as "correctly unreachable",
not "suspiciously clean" -- the tripwire for a real taxonomy gap is a
nonzero-and-growing ``harness_internal`` rate (spec §4.3), not this one.

**Emission surface -- zero new dependencies.** No opentelemetry, structlog,
logfire, or cisternal: adding one now would prejudge both the Pyodide
question (spec §6) and an org-wide observability choice out of scope here.
``TelemetrySink`` is a minimal Protocol; ``set_sink``/the default sink are a
process-global with a no-op default; ``JsonlSink`` is the only concrete
sink shipped in-package (stdlib ``json``, append mode).

**Never raises.** ``emit`` swallows every sink failure, matching
``capture_git_state``'s discipline (spec §4.1): telemetry that can crash the
analyzer is worse than no telemetry.

**Never shells out.** ``emit`` only serializes the ``SurveyStamp`` it is
handed; callers are expected to pass ``plr_sema._provenance.survey_stamp()``,
which is itself process-memoized (see ``_provenance/stamp.py``'s docstring)
so that "every event carries the full stamp" (spec §4.1) doesn't multiply
into per-event subprocess calls.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

from plr_sema._provenance import SurveyStamp
from plr_sema.verdict import REASON_VOCABULARY, Finding, PlrSite, Verdict

SCHEMA_VERSION = 1

#: Closed set of failure categories, promoted verbatim from
#: training/verify/failure_taxonomy.py:71-78 (see module docstring). Frozen:
#: extending this set is a deliberate, reviewable design conversation, not a
#: silent commit (spec §4.3).
FAILURE_CATEGORIES: frozenset[str] = frozenset(
    {
        "unsupported_tool",
        "ungroundable_reference",
        "shape_mismatch",
        "precondition_state",
        "harness_internal",
        "postcondition_mismatch",
    }
)

#: The three event kinds an emitter may report (spec §4.1's event schema).
EVENT_KINDS: frozenset[str] = frozenset({"finding", "internal_error", "derivation_gap"})


class TelemetrySink(Protocol):
    """Minimal emission surface. Concrete sinks (JsonlSink, or a downstream
    adapter to a real backend) implement exactly this one method."""

    def emit(self, event: Mapping[str, Any]) -> None: ...


class _NullSink:
    """Process-default sink: telemetry is strictly optional (spec AC-4.4).
    Never raises, never does anything."""

    def emit(self, event: Mapping[str, Any]) -> None:
        return None


_NULL_SINK = _NullSink()
_sink: TelemetrySink | None = None


def set_sink(sink: TelemetrySink | None) -> None:
    """Set the process-global telemetry sink. ``None`` (the default)
    restores the no-op sink."""
    global _sink
    _sink = sink


def _current_sink() -> TelemetrySink:
    return _sink if _sink is not None else _NULL_SINK


class JsonlSink:
    """Append-only JSONL sink: one ``json.dumps`` event per line, stdlib
    ``json`` only. Opened in append mode on every ``emit`` call rather than
    held open, so a sink instance is safe to construct once and reuse for
    the life of a process without worrying about file-handle lifecycle."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def emit(self, event: Mapping[str, Any]) -> None:
        line = json.dumps(event)
        with open(self._path, mode="a", encoding="utf-8") as fh:
            fh.write(line)
            fh.write("\n")


def _stamp_to_dict(stamp: SurveyStamp) -> dict[str, Any]:
    def _git_state_to_dict(state: Any) -> dict[str, Any]:
        return {
            "hash": state.hash,
            "branch": state.branch,
            "dirty": state.dirty,
            "dirty_content_id": state.dirty_content_id,
            "provenance_source": state.provenance_source,
            "toplevel": state.toplevel,
        }

    return {
        "plr": _git_state_to_dict(stamp.plr),
        "praxis": _git_state_to_dict(stamp.praxis),
        "pylabrobot_version": stamp.pylabrobot_version,
        "stamped_at": stamp.stamped_at,
        "schema_version": stamp.schema_version,
        # T13 (260901, backlog #4859): which named Surface this stamp was
        # computed against -- additive fields, see SurveyStamp's docstring.
        "surface": stamp.surface,
        "surface_pin": stamp.surface_pin,
    }


def build_event(
    *,
    event: str,
    protocol_fqn: str,
    operation_id: str,
    verdict: Verdict,
    stamp: SurveyStamp,
    category: str | None = None,
    reason: str | None = None,
    plr_site: PlrSite | None = None,
) -> dict[str, Any]:
    """Build one event dict matching spec §4.1's schema exactly. Does not
    emit -- callers pass the result to :func:`emit`.

    ``category``/``reason`` are nullable but, when present, are validated
    against ``FAILURE_CATEGORIES``/``REASON_VOCABULARY`` respectively -- a
    telemetry event carrying a category or reason string that isn't in
    either closed vocabulary would itself be a silent taxonomy drift, which
    is exactly what this module exists to make visible, not perpetuate.
    """
    if event not in EVENT_KINDS:
        raise ValueError(f"event={event!r} is not one of {sorted(EVENT_KINDS)}")
    if category is not None and category not in FAILURE_CATEGORIES:
        raise ValueError(f"category={category!r} is not a member of FAILURE_CATEGORIES")
    if reason is not None and reason not in REASON_VOCABULARY:
        raise ValueError(f"reason={reason!r} is not a member of REASON_VOCABULARY")

    return {
        "schema_version": SCHEMA_VERSION,
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
        "protocol_fqn": protocol_fqn,
        "operation_id": operation_id,
        "verdict": verdict.value,
        "category": category,
        "reason": reason,
        "plr_site": (
            {"file": plr_site.file, "lineno": plr_site.lineno, "qualname": plr_site.qualname}
            if plr_site is not None
            else None
        ),
        "stamp": _stamp_to_dict(stamp),
    }


def emit_finding(
    finding: Finding,
    *,
    protocol_fqn: str,
    stamp: SurveyStamp,
) -> None:
    """Build and emit a ``"finding"`` event from a :class:`Finding`. Never
    raises: a sink failure is swallowed, matching
    ``capture_git_state``'s discipline (spec §4.1)."""
    event = build_event(
        event="finding",
        protocol_fqn=protocol_fqn,
        operation_id=finding.operation_id,
        verdict=finding.verdict,
        stamp=stamp,
        category=finding.category or None,
        reason=finding.reason or None,
        plr_site=finding.plr_site,
    )
    emit(event)


def emit(event: Mapping[str, Any]) -> None:
    """Hand ``event`` to the current sink. Never raises, never shells out --
    the caller is responsible for having already built ``event`` (e.g. via
    :func:`build_event`/:func:`emit_finding`) and stamped it with an
    already-computed :class:`SurveyStamp`."""
    try:
        _current_sink().emit(event)
    except Exception:
        # Telemetry that can crash the analyzer is worse than no telemetry
        # (spec §4.1). Swallow unconditionally, matching
        # capture_git_state's never-raises discipline.
        return None
