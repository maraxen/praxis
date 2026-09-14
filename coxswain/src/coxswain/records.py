"""The §2.4 record shapes: six frozen dataclasses plus the closed
vocabularies and NFR-7's kernel-side string caps.

Field names are normative (spec §2: "an implementer must not choose their own").
All persisted per-turn artifacts live on the ``CoxswainTurnRecord`` aggregate
keyed by ``turn_id`` (§2.3); ``OverrideRecord`` lives in a separate store and is
exempt from eviction.

NFR-1/NFR-2: this module imports nothing from praxis and has no browser
bindings; it imports cleanly in plain CPython.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

# --- Schema versioning (§2.5) ------------------------------------------------

#: Mirrored as the IndexedDB database version in audit_store.js (W5). Both
#: persisted aggregates carry it in the record body, so an exported L3 bundle
#: is self-describing independently of the database it came from.
SCHEMA_VERSION: Final[int] = 1

# --- Closed vocabularies ------------------------------------------------------

TURN_STATES: Final[frozenset[str]] = frozenset({"open", "closed", "abandoned"})

EXECUTION_STATUSES: Final[frozenset[str]] = frozenset(
    {"ok", "failed", "aborted_stale"}
)

DECISION_CATEGORIES: Final[frozenset[str]] = frozenset(
    {"initial", "re_entry", "confirm_recheck"}
)

#: The closed disposition vocabulary of §2.4. There is no open-ended "other".
DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {
        "continue",
        "pass",
        "blocked:concurrent",
        "blocked:stale_card",
        "blocked:audit_unavailable",
        "clarify:incomplete",
        "clarify:not_found",
        "clarify:disambiguate",
        "clarify:precondition",
        "override:precondition",
        "aborted:drift",
    }
)

# --- NFR-7 string caps, enforced kernel-side before persistence --------------

#: Maximum rendered length per string class. A string exceeding its cap is
#: truncated on a word boundary and suffixed with an ellipsis; it is never
#: rejected silently. The same caps are mirrored in the browser-side JS.
STRING_CAPS: Final[dict[str, int]] = {
    "nl_restatement": 400,
    "candidate_label": 120,
    "warning_badge_text": 64,
    "edited_field_value": 200,
    "override_justification": 500,
    "confirmation_phrase": 60,
}

_ELLIPSIS: Final[str] = "…"


def truncate_to_cap(value: str, cap: int) -> str:
    """Truncate ``value`` to at most ``cap`` characters on a word boundary,
    suffixed with ``…``. Strings within the cap pass through unchanged."""
    if len(value) <= cap:
        return value
    head = value[: max(cap - 1, 0)]
    cut = head.rfind(" ")
    if cut > 0:
        head = head[:cut]
    return head.rstrip() + _ELLIPSIS


def _require_in_vocabulary(field_name: str, value: str, vocabulary: frozenset[str]) -> None:
    if value not in vocabulary:
        raise ValueError(
            f"{field_name} {value!r} is outside the closed vocabulary "
            f"{sorted(vocabulary)}"
        )


# --- Record shapes (§2.4) -----------------------------------------------------


@dataclass(frozen=True)
class CoxswainTurnRecord:
    """The persisted aggregate of §2.3, keyed by ``turn_id``, one record per
    turn in the single L0 object store ``coxswain_turns``."""

    schema_version: int
    turn_id: str
    session_id: str
    state: str  # one of TURN_STATES
    opened_at: float
    closed_at: float | None
    transcript: tuple[Any, ...] = ()
    pending_intents: tuple[PendingIntent, ...] = ()  # type: ignore[name-defined]
    decisions: tuple[FftDecision, ...] = ()  # type: ignore[name-defined]
    fingerprints: tuple[StalenessFingerprint, ...] = ()  # type: ignore[name-defined]
    outcome: ExecutionOutcome | None = None  # type: ignore[name-defined]

    def __post_init__(self) -> None:
        _require_in_vocabulary("state", self.state, TURN_STATES)
        if self.state == "open":
            if self.closed_at is not None:
                raise ValueError("an open turn must not carry closed_at")
        elif self.closed_at is None:
            raise ValueError(f"a {self.state!r} turn must carry closed_at")


@dataclass(frozen=True)
class FftDecision:
    """One FFT gate pass. The N6 '3-field log' is category/cue/disposition;
    the remaining fields are the correlation and provenance keys of §2."""

    turn_id: str
    session_id: str
    gate_seq: int
    cue: int
    category: str  # one of DECISION_CATEGORIES
    disposition: str  # one of DISPOSITIONS
    payload_kind: str
    card_revision: int
    ts: float
    fingerprint_id: str | None
    override_id: str | None

    def __post_init__(self) -> None:
        _require_in_vocabulary("category", self.category, DECISION_CATEGORIES)
        _require_in_vocabulary("disposition", self.disposition, DISPOSITIONS)


@dataclass(frozen=True)
class StalenessFingerprint:
    """FR-6 staleness capture. Compared fields are exactly
    ``concurrency_active`` and ``precondition_digest``; every other field is
    provenance only and is excluded from comparison (the compared set is
    enumerated solely in fft/fingerprint.py from W2 onward)."""

    fingerprint_id: str
    turn_id: str
    gate_seq: int
    card_revision: int
    taken_at: float
    concurrency_active: bool
    precondition_digest: str


@dataclass(frozen=True)
class OverrideRecord:
    """An immutable scoped-override entry (FR-10). Persisted in the separate
    ``coxswain_overrides`` store, exempt from eviction (§2.3), retaining its
    turn_id so exports stay joinable even after the turn is evicted."""

    schema_version: int
    override_id: str
    turn_id: str
    gate_seq: int
    cue: int
    justification: str
    ts: float

    def __post_init__(self) -> None:
        # NFR-7 kernel-side enforcement: a record cannot carry an unbounded
        # justification that a later viewer renders.
        object.__setattr__(
            self,
            "justification",
            truncate_to_cap(self.justification, STRING_CAPS["override_justification"]),
        )


@dataclass(frozen=True)
class PendingIntent:
    """The parsed-but-not-yet-executed proposal. ``unresolved_slots`` is what
    FR-8's re-enter-the-same-cue rule tests for emptiness before advancing."""

    turn_id: str
    parsed_call: Any
    resolved_slots: tuple[Any, ...] = ()
    exited_cue: int = -1
    unresolved_slots: tuple[str, ...] = ()
    candidates: tuple[Any, ...] = ()
    card_revision: int = 0


@dataclass(frozen=True)
class ExecutionOutcome:
    """Terminal result for a turn. Writing one closes the turn (§2.3), any
    status included -- failed and aborted_stale alike."""

    turn_id: str
    gate_seq: int
    status: str  # one of EXECUTION_STATUSES
    detail: str | None
    ts: float

    def __post_init__(self) -> None:
        _require_in_vocabulary("status", self.status, EXECUTION_STATUSES)
