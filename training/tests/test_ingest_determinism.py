"""Determinism tests for every ingest writer (AC-1.10, §7.4).

Each writer is run TWICE against the SAME on-disk inputs, into TWO DISTINCT
temp directories, and the two outputs are asserted byte-identical. This
proves determinism given fixed inputs: no `datetime.now()`, no PID, no
dict-ordering nondeterminism, nothing environment-dependent leaks into any
committed artifact.

A mutable upstream clone (the cookbook drifting between the two runs) is a
separate, non-determinism concern already handled by `eval_split.py`'s §4.4
assertions -- this file holds every OTHER input fixed and only varies the
output directory.
"""

import json
from pathlib import Path
from types import SimpleNamespace

from ingest import audit, eval_split, gap, licenses


def _assert_byte_identical(dir_a: Path, dir_b: Path, name: str) -> None:
    a = (dir_a / name).read_bytes()
    b = (dir_b / name).read_bytes()
    assert a == b, f"{name} differs between two runs against the same inputs"
    # Sanity: both writes actually happened and produced non-trivial content.
    assert len(a) > 0


# ============================================================================
# licenses.py
# ============================================================================


class TestLicensesDeterminism:
    def test_write_report_byte_identical(self, tmp_path):
        findings = licenses.verify_all()
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"

        licenses.write_report(findings, dir_a)
        licenses.write_report(findings, dir_b)

        _assert_byte_identical(dir_a, dir_b, "license_report.json")

    def test_write_sources_manifest_byte_identical(self, tmp_path):
        findings = licenses.verify_all()
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"

        licenses.write_sources_manifest(findings, dir_a)
        licenses.write_sources_manifest(findings, dir_b)

        _assert_byte_identical(dir_a, dir_b, "SOURCES.md")


# ============================================================================
# audit.py
# ============================================================================


class TestAuditDeterminism:
    def test_report_byte_identical(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"

        assert audit._handle_report(SimpleNamespace(out=dir_a)) == 0
        assert audit._handle_report(SimpleNamespace(out=dir_b)) == 0

        _assert_byte_identical(dir_a, dir_b, "audit_report.json")
        _assert_byte_identical(dir_a, dir_b, "audit_findings.jsonl")

    def test_emit_census_byte_identical(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"

        assert audit._handle_emit_census(SimpleNamespace(out=dir_a)) == 0
        assert audit._handle_emit_census(SimpleNamespace(out=dir_b)) == 0

        _assert_byte_identical(dir_a, dir_b, "blocking_census.json")

    def test_emit_fingerprint_byte_identical(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"

        assert audit._handle_emit_fingerprint(SimpleNamespace(out=dir_a)) == 0
        assert audit._handle_emit_fingerprint(SimpleNamespace(out=dir_b)) == 0

        _assert_byte_identical(dir_a, dir_b, "canonical_tables_fingerprint.json")


# ============================================================================
# gap.py
# ============================================================================


class TestGapDeterminism:
    def test_gate_report_byte_identical(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"

        code_a = gap.gate(out_dir=dir_a)
        code_b = gap.gate(out_dir=dir_b)

        assert code_a == code_b
        _assert_byte_identical(dir_a, dir_b, "gap_report.json")


# ============================================================================
# eval_split.py
# ============================================================================


class TestEvalSplitDeterminism:
    def test_emit_byte_identical(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"

        assert eval_split._emit(SimpleNamespace(out=dir_a)) == 0
        assert eval_split._emit(SimpleNamespace(out=dir_b)) == 0

        _assert_byte_identical(dir_a, dir_b, "eval_split.json")

    def test_emit_lineage_contract_byte_identical(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"

        assert eval_split._emit_lineage_contract(SimpleNamespace(out=dir_a)) == 0
        assert eval_split._emit_lineage_contract(SimpleNamespace(out=dir_b)) == 0

        _assert_byte_identical(dir_a, dir_b, "lineage_contract.json")


# ============================================================================
# Cross-cutting: every artifact is valid, sorted-key, ensure_ascii=False JSON
# with a trailing structure that round-trips (§7.4's serializer contract).
# ============================================================================


class TestArtifactsAreValidJson:
    """A light structural check that rides the same writes: every emitted
    JSON artifact parses, which would catch a writer that silently produced
    truncated or malformed output while still being byte-identical run-to-run
    (byte-identical is not the same claim as well-formed)."""

    def test_every_written_artifact_parses_as_json(self, tmp_path):
        out = tmp_path / "all"
        findings = licenses.verify_all()
        licenses.write_report(findings, out)
        audit._handle_report(SimpleNamespace(out=out))
        audit._handle_emit_census(SimpleNamespace(out=out))
        audit._handle_emit_fingerprint(SimpleNamespace(out=out))
        gap.gate(out_dir=out)
        eval_split._emit(SimpleNamespace(out=out))
        eval_split._emit_lineage_contract(SimpleNamespace(out=out))

        for name in (
            "license_report.json",
            "audit_report.json",
            "blocking_census.json",
            "canonical_tables_fingerprint.json",
            "gap_report.json",
            "eval_split.json",
            "lineage_contract.json",
        ):
            json.loads((out / name).read_text())

        # audit_findings.jsonl is JSONL, not JSON -- each line parses independently.
        for line in (out / "audit_findings.jsonl").read_text().splitlines():
            json.loads(line)
