"""FR-6 / N3 staleness fingerprint capture and comparison.

``compare()`` is the ONLY place in the codebase where FR-6's compared field
set -- ``{concurrency_active, precondition_digest}`` -- is enumerated. Every
other ``StalenessFingerprint`` field (``fingerprint_id``, ``turn_id``,
``gate_seq``, ``card_revision``, ``taken_at``) is provenance/audit-only and
MUST NOT join the comparison: those fields necessarily differ between any two
passes, so comparing them would abort every execution that ever reached
confirm time (spec §2.4).

There is deliberately no benign-drift classification here: any difference in
either compared field maps, at the gate, to ``aborted:drift`` and a fresh
clarify/re-propose cycle. Nothing is auto-corrected.
"""

from __future__ import annotations

from coxswain.ids import fingerprint_id_for
from coxswain.records import StalenessFingerprint

__all__ = ["capture", "compare", "COMPARED_FIELDS"]

#: The closed compared-field set of FR-6. Named once, consumed by compare()
#: below; adding a field to StalenessFingerprint must not add it here.
COMPARED_FIELDS: tuple[str, str] = ("concurrency_active", "precondition_digest")


def capture(
    *,
    turn_id: str,
    gate_seq: int,
    card_revision: int,
    concurrency_active: bool,
    precondition_digest: str,
    taken_at: float,
) -> StalenessFingerprint:
    """Stamp one StalenessFingerprint for the current gate pass."""
    return StalenessFingerprint(
        fingerprint_id=fingerprint_id_for(turn_id, gate_seq),
        turn_id=turn_id,
        gate_seq=gate_seq,
        card_revision=card_revision,
        taken_at=taken_at,
        concurrency_active=concurrency_active,
        precondition_digest=precondition_digest,
    )


def compare(a: StalenessFingerprint, b: StalenessFingerprint) -> bool:
    """True iff the two fingerprints agree on exactly FR-6's compared fields.

    Provenance fields are excluded here and nowhere else; a field added to
    ``StalenessFingerprint`` does not silently join this comparison
    (AC-9 assertion 3)."""
    return (
        a.concurrency_active == b.concurrency_active
        and a.precondition_digest == b.precondition_digest
    )
