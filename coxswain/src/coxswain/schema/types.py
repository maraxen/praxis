"""Structural safety types per spec §3.3: risk tiers, cue identifiers, the
closed disposition enum, the per-cue exit payload types, and
``OVERRIDABLE_CUES``.

Design constraint (§3.3, binding): widening override scope must require a
source change to ``OVERRIDABLE_CUES`` plus a new spec decision. It must never
be achievable by configuration, environment variable, build flag, feature
toggle, URL parameter, or support ticket. The exit payload types for cues 0,
1 and 2 do not carry override affordance fields at all, so an over-eager UI
cannot render an override control for them even by mistake.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Final

from coxswain.ids import override_id_for
from coxswain.records import SCHEMA_VERSION, OverrideRecord

#: §3.3 — the entire override scope, as a compile-time constant.
OVERRIDABLE_CUES: Final[frozenset[int]] = frozenset({3})


class RiskTier(str, Enum):
    """N1 tiering (AC-8/AC-14). Exactly one tier per PLR call, independent of
    parameters."""

    READ_ONLY = "read_only"
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"


class CueId(int, Enum):
    """The four FFT cues (F4-locked semantics). Values are normative ints; the
    gate logs ``cue`` as a plain int on every record."""

    CONCURRENCY = 0
    COMPLETENESS = 1
    GROUNDING = 2
    PRECONDITION = 3


class Disposition(str, Enum):
    """The closed disposition vocabulary of §2.4 as an enum. The canonical
    string set lives in ``coxswain.records.DISPOSITIONS``; this enum is the
    typed surface over it and must not grow independently."""

    CONTINUE = "continue"
    PASS = "pass"
    BLOCKED_CONCURRENT = "blocked:concurrent"
    BLOCKED_STALE_CARD = "blocked:stale_card"
    BLOCKED_AUDIT_UNAVAILABLE = "blocked:audit_unavailable"
    CLARIFY_INCOMPLETE = "clarify:incomplete"
    CLARIFY_NOT_FOUND = "clarify:not_found"
    CLARIFY_DISAMBIGUATE = "clarify:disambiguate"
    CLARIFY_PRECONDITION = "clarify:precondition"
    OVERRIDE_PRECONDITION = "override:precondition"
    ABORTED_DRIFT = "aborted:drift"


# --- Per-cue exit payload types ----------------------------------------------
# Cues 0/1/2 structurally lack the override affordance fields (AC-6). Only
# cue 3's payload carries them, and eligibility itself is decided only in the
# gate (W2), shipped to the UI as the `overridable` boolean.


@dataclass(frozen=True)
class ConcurrencyExitPayload:
    """Cue 0. ``None`` means the probe could not determine the signal, which
    maps to blocked:concurrent (NFR-5 fail-closed)."""

    concurrency_active: bool | None


@dataclass(frozen=True)
class CompletenessExitPayload:
    """Cue 1 -- missing required fields (clarify:incomplete)."""

    missing_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class GroundingExitPayload:
    """Cue 2 -- symbolic resolution of an ambiguous reference.

    ``candidates`` entries are KernelInstance objects (name/resource_type/
    position, from plr.grounding / fft.context); the JS candidate picker
    renders their labels and positions. Typed Any to keep this module
    import-cycle-free of the grounding layer."""

    slot: str = ""
    candidates: tuple[Any, ...] = ()
    message: str = ""


@dataclass(frozen=True)
class PreconditionExitPayload:
    """Cue 3 -- precondition enumeration. The only payload with the override
    affordance fields."""

    overridable: bool
    override_prompt: str
    unmet_preconditions: tuple[str, ...] = ()
    justification: str = ""


class OverrideNotAllowedError(ValueError):
    """Raised when an override is requested for a cue outside
    OVERRIDABLE_CUES."""


def request_override(
    *,
    turn_id: str,
    gate_seq: int,
    cue: int,
    justification: str,
    ts: float,
) -> OverrideRecord:
    """Eligibility check + immutable record construction for FR-10.

    The full override flow (typed justification capture in the card, gate-side
    emission ordering) lands in W2; this is the kernel-side eligibility
    primitive AC-6 tests against. Raises OverrideNotAllowedError for any cue
    not in OVERRIDABLE_CUES."""
    if cue not in OVERRIDABLE_CUES:
        raise OverrideNotAllowedError(
            f"cue {cue} is not overridable: overrides are scoped to "
            f"OVERRIDABLE_CUES={sorted(OVERRIDABLE_CUES)} by a source-level "
            "constant, not configuration"
        )
    return OverrideRecord(
        schema_version=SCHEMA_VERSION,
        override_id=override_id_for(turn_id, gate_seq),
        turn_id=turn_id,
        gate_seq=gate_seq,
        cue=cue,
        justification=justification,
        ts=ts,
    )
