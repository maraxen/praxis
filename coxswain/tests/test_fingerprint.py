"""FR-6 / N3 staleness fingerprint tests (spec §2.4, §4.4, AC-9).

The compared field set is EXACTLY {concurrency_active, precondition_digest};
every other field on ``StalenessFingerprint`` is provenance/audit-only and is
excluded from comparison. ``compare()`` is the ONLY place that set is
enumerated, there is no benign-drift classification anywhere in this file, and
adding a field to the dataclass must not silently widen the comparison.
"""

from dataclasses import dataclass

from coxswain.fft import fingerprint as fp
from coxswain.records import StalenessFingerprint


def _fp(
    *,
    fingerprint_id: str = "cx-1-abc123:0:fp",
    turn_id: str = "cx-1-abc123",
    gate_seq: int = 0,
    card_revision: int = 0,
    taken_at: float = 1000.0,
    concurrency_active: bool = False,
    precondition_digest: str = "deadbeef",
) -> StalenessFingerprint:
    return StalenessFingerprint(
        fingerprint_id=fingerprint_id,
        turn_id=turn_id,
        gate_seq=gate_seq,
        card_revision=card_revision,
        taken_at=taken_at,
        concurrency_active=concurrency_active,
        precondition_digest=precondition_digest,
    )


# --- AC-9 assertion 1: the realistic no-drift case compares EQUAL -------------


def test_compare_equal_when_only_provenance_differs() -> None:
    """Propose-time vs confirm-time records necessarily differ in
    fingerprint_id/gate_seq/card_revision/taken_at; that must NOT abort."""
    propose_time = _fp(gate_seq=0, card_revision=0, taken_at=1000.0)
    confirm_time = _fp(
        fingerprint_id="cx-1-abc123:4:fp", gate_seq=4, card_revision=2, taken_at=1042.5
    )
    assert fp.compare(propose_time, confirm_time) is True


def test_compare_is_symmetric_on_provenance_noise() -> None:
    assert fp.compare(
        _fp(taken_at=1.0),
        _fp(fingerprint_id="x:9:fp", turn_id="other-turn", gate_seq=9, card_revision=9, taken_at=9.0),
    ) is True


# --- AC-9 assertion 2: any compared-field difference is drift -----------------


def test_compare_unequal_on_concurrency_active_difference() -> None:
    assert fp.compare(_fp(concurrency_active=False), _fp(concurrency_active=True)) is False


def test_compare_unequal_on_precondition_digest_difference() -> None:
    assert fp.compare(_fp(precondition_digest="a"), _fp(precondition_digest="b")) is False


# --- AC-9 assertion 3 / §2.4: the compared set is CLOSED ----------------------


@dataclass(frozen=True)
class _StalenessFingerprintWithNewField(StalenessFingerprint):
    """Simulates a future contributor adding a field to the record shape.

    If compare() ever widened to whole-record equality (or to a stale field
    list), two records differing only in ``future_field`` would start
    comparing unequal and every execution would abort -- AC-9's third
    assertion exists to catch exactly that regression."""

    future_field: str = "unset"


def _sub(*, concurrency_active: bool = False, future_field: str = "unset") -> _StalenessFingerprintWithNewField:
    return _StalenessFingerprintWithNewField(
        fingerprint_id="cx-1-abc123:0:fp",
        turn_id="cx-1-abc123",
        gate_seq=0,
        card_revision=0,
        taken_at=1000.0,
        concurrency_active=concurrency_active,
        precondition_digest="deadbeef",
        future_field=future_field,
    )


def test_new_dataclass_field_does_not_join_the_comparison() -> None:
    a = _sub(concurrency_active=False, future_field="left")
    b = _sub(concurrency_active=False, future_field="right")
    assert a.future_field != b.future_field
    assert fp.compare(a, b) is True  # type: ignore[arg-type]


def test_compared_fields_still_drive_comparison_for_subclasses() -> None:
    a = _sub(concurrency_active=False)
    b = _sub(concurrency_active=True)
    assert fp.compare(a, b) is False  # type: ignore[arg-type]


# --- capture ------------------------------------------------------------------


def test_capture_mints_normative_fingerprint_id_and_stamps_time() -> None:
    rec = fp.capture(
        turn_id="cx-1700000000000-k3x9qz",
        gate_seq=2,
        card_revision=1,
        concurrency_active=True,
        precondition_digest="cafe",
        taken_at=1712.5,
    )
    assert isinstance(rec, StalenessFingerprint)
    assert rec.fingerprint_id == "cx-1700000000000-k3x9qz:2:fp"
    assert rec.turn_id == "cx-1700000000000-k3x9qz"
    assert rec.gate_seq == 2
    assert rec.card_revision == 1
    assert rec.taken_at == 1712.5
    assert rec.concurrency_active is True
    assert rec.precondition_digest == "cafe"


# --- no benign-drift classification anywhere ----------------------------------


def test_no_benign_drift_classification_exists() -> None:
    """FR-6: no drift is classified as benign; compare() yields a plain bool
    and the disposition vocabulary carries no benign tier for drift."""
    from coxswain.records import DISPOSITIONS

    public = {name for name in dir(fp) if "benign" in name.lower()}
    assert public == set()
    assert not any("benign" in d for d in DISPOSITIONS)


def test_compare_enumerates_exactly_the_two_field_names() -> None:
    """The enumeration lives in compare() alone: its body may name only
    {concurrency_active, precondition_digest} as record attributes."""
    import ast

    tree = ast.parse(open(fp.__file__, encoding="utf-8").read(), mode="exec")
    compare_node = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "compare"
    )
    named = {
        node.attr
        for node in ast.walk(compare_node)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    }
    record_attrs = named & {
        "fingerprint_id",
        "turn_id",
        "gate_seq",
        "card_revision",
        "taken_at",
        "concurrency_active",
        "precondition_digest",
    }
    assert record_attrs == {"concurrency_active", "precondition_digest"}
