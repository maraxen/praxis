"""AC-21 / §2.5 schema-version check against the pure store: any record whose
schema_version differs from the running build's puts the whole store into
read-only degrade with a loud message naming both numbers. No migration, no
silent coercion."""

import pytest

from coxswain.persistence.store import (
    SCHEMA_VERSION,
    StoreMode,
    CoxswainAuditStore,
    ReadOnlyStoreError,
)
from coxswain.records import (
    CoxswainTurnRecord,
    ExecutionOutcome,
    OverrideRecord,
)

from test_retention import FakeBackend, ManualClock


def turn_with_version(tid: str, version: int) -> CoxswainTurnRecord:
    return CoxswainTurnRecord(
        schema_version=version,
        turn_id=tid,
        session_id="sess-1",
        state="closed",
        opened_at=1.0,
        closed_at=2.0,
    )


class TestMatchingVersion:
    def test_store_with_current_version_is_read_write(self) -> None:
        backend = FakeBackend()
        backend.save_turn(turn_with_version("t1", SCHEMA_VERSION))
        store = CoxswainAuditStore.open(backend, now=ManualClock())
        assert store.mode is StoreMode.READ_WRITE
        assert store.status_message is None


class TestNewerData:
    def test_older_build_opening_newer_store_degrades_read_only(self) -> None:
        future = SCHEMA_VERSION + 1
        backend = FakeBackend()
        backend.save_turn(turn_with_version("t1", future))
        store = CoxswainAuditStore.open(backend, now=ManualClock())

        assert store.mode is StoreMode.READ_ONLY
        # loud line names BOTH numbers (§2.5's phrasing contract)
        assert str(future) in store.status_message
        assert str(SCHEMA_VERSION) in store.status_message
        assert "newer" in store.status_message

    def test_existing_records_remain_readable_and_uncoerced(self) -> None:
        future = SCHEMA_VERSION + 4
        backend = FakeBackend()
        backend.save_turn(turn_with_version("t1", future))
        store = CoxswainAuditStore.open(backend, now=ManualClock())

        record = store.get_turn("t1")
        assert record is not None
        assert record.schema_version == future, "never silently coerce"

    def test_export_still_succeeds_while_read_only(self) -> None:
        future = SCHEMA_VERSION + 1
        backend = FakeBackend()
        backend.save_turn(turn_with_version("t1", future))
        backend.save_override(
            OverrideRecord(
                schema_version=future,
                override_id="t1:0:ovr",
                turn_id="t1",
                gate_seq=0,
                cue=3,
                justification="j",
                ts=1.0,
            )
        )
        store = CoxswainAuditStore.open(backend, now=ManualClock())
        bundle = store.export_bundle()
        assert bundle["turns"]["t1"]["schema_version"] == future
        assert bundle["overrides"][0]["override_id"] == "t1:0:ovr"
        assert bundle["exported_by_schema_version"] == SCHEMA_VERSION

    def test_no_write_is_accepted_and_no_new_turn_minted(self) -> None:
        future = SCHEMA_VERSION + 1
        backend = FakeBackend()
        backend.save_turn(turn_with_version("t1", future))
        store = CoxswainAuditStore.open(backend, now=ManualClock())

        with pytest.raises(ReadOnlyStoreError):
            store.begin_turn("fresh-turn", "sess-1")
        with pytest.raises(ReadOnlyStoreError):
            store.close_turn("t1")
        with pytest.raises(ReadOnlyStoreError):
            store.attach_outcome(
                "t1",
                ExecutionOutcome(
                    turn_id="t1", gate_seq=0, status="ok", detail=None, ts=3.0
                ),
            )
        with pytest.raises(ReadOnlyStoreError):
            store.add_override(
                OverrideRecord(
                    schema_version=SCHEMA_VERSION,
                    override_id="x:0:ovr",
                    turn_id="x",
                    gate_seq=0,
                    cue=3,
                    justification="j",
                    ts=1.0,
                )
            )

    def test_abandon_on_load_is_suppressed_in_read_only(self) -> None:
        """Abandoning writes; §2.5 says no write is accepted in read-only mode.
        The foreign build owns its records' lifecycle."""
        future = SCHEMA_VERSION + 1
        backend = FakeBackend()
        backend.save_turn(
            CoxswainTurnRecord(
                schema_version=future,
                turn_id="still-open-foreign",
                session_id="sess-1",
                state="open",
                opened_at=1.0,
                closed_at=None,
            )
        )
        saves_before_load = len(backend.saved_turns)
        store = CoxswainAuditStore.open(backend, now=ManualClock())

        assert store.mode is StoreMode.READ_ONLY
        assert len(backend.saved_turns) == saves_before_load
        assert store.get_turn("still-open-foreign").state == "open"

    def test_eviction_is_also_a_write_and_is_refused(self) -> None:
        future = SCHEMA_VERSION + 1
        backend = FakeBackend()
        backend.save_turn(turn_with_version("old-a", future))
        backend.save_turn(turn_with_version("old-b", future))
        saves_before_load = len(backend.saved_turns)
        store = CoxswainAuditStore.open(backend, now=ManualClock(), turn_cap=1)

        assert store.mode is StoreMode.READ_ONLY
        assert len(backend.saved_turns) == saves_before_load
        assert store.get_turn("old-a") is not None, "no silent eviction either"


class TestOlderData:
    def test_newer_build_opening_older_store_degrades_the_same_way(self) -> None:
        past = SCHEMA_VERSION - 1
        backend = FakeBackend()
        backend.save_turn(turn_with_version("t1", past))
        store = CoxswainAuditStore.open(backend, now=ManualClock())

        assert store.mode is StoreMode.READ_ONLY
        assert str(past) in store.status_message
        assert str(SCHEMA_VERSION) in store.status_message

    def test_mixed_store_reports_the_worst_direction(self) -> None:
        backend = FakeBackend()
        backend.save_turn(turn_with_version("older", SCHEMA_VERSION - 1))
        backend.save_turn(turn_with_version("newer", SCHEMA_VERSION + 1))
        store = CoxswainAuditStore.open(backend, now=ManualClock())

        assert store.mode is StoreMode.READ_ONLY
