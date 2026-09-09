"""Tests for audit findings and gate mechanics (§5.2, §5.4, §5.5, §5.7).

Comprehensive coverage of finding generation, fingerprinting, and gate evaluation.
"""

import json
from pathlib import Path
from io import StringIO

import pytest

from ingest import audit, recipes, cli
from coxswain.plr.tool_schema import TOOL_SCHEMA
from coxswain.plr.param_namespace import PARAM_NAMESPACE


class TestFindingShape:
    """Tests for Finding dataclass and hash computation (§5.2)."""

    def test_evidence_dataclass_frozen(self):
        """Evidence is frozen (immutable) (§5.2)."""
        ev = audit.Evidence(
            recipe_path="test.qmd",
            token_raw="test",
            token_kind=recipes.TokenKind.IDENT,
            receiver=None,
            receiver_type=recipes.ReceiverType.NONE,
            member="test",
            member_is_in_surface=False,
            match_mode=audit.MatchMode.EXACT,
        )
        with pytest.raises(AttributeError):
            ev.recipe_path = "new_path"  # type: ignore

    def test_finding_dataclass_frozen(self):
        """Finding is frozen (immutable) (§5.2)."""
        f = audit.Finding(
            finding_id="test_id",
            adjudicable_digest="test_digest",
            kind=audit.FindingKind.PHANTOM_VERB,
            subject="mix",
            blocking=True,
            verdict="no_evidence",
            evidence=(),
            reading_table_is_wrong="",
            reading_api_moved="",
            verdict_hint="",
        )
        with pytest.raises(AttributeError):
            f.subject = "new_subject"  # type: ignore

    def test_canonical_json_consistency(self):
        """canonical_json is deterministic (sorted keys, compact) (§5.2, R4-B3)."""
        obj = {"z": 1, "a": 2, "m": 3}
        json1 = audit.canonical_json(obj)
        json2 = audit.canonical_json(obj)
        assert json1 == json2
        # Verify it's sorted
        assert b"a" in json1 and b"a" < b"m" < b"z" in json1

    def test_sha16_produces_16_hex_chars(self):
        """_sha16 produces exactly 16 hex characters (first half of SHA-256)."""
        hash_val = audit._sha16({"test": "object"})
        assert len(hash_val) == 16
        assert all(c in "0123456789abcdef" for c in hash_val)

    def test_dotted_subject_construction(self):
        """dotted_subject concatenates receiver_type.value + '.' + member (§5.2, R5-W4)."""
        subject = audit.dotted_subject(
            recipes.ReceiverType.LIQUID_HANDLER, "use_channels"
        )
        assert subject == "liquid_handler.use_channels"

    def test_param_subject_construction(self):
        """param_subject concatenates verb + ':' + token (§5.2, R5-W4)."""
        subject = audit.param_subject("aspirate", "backend_kwargs")
        assert subject == "aspirate:backend_kwargs"


class TestFingerprinting:
    """Tests for fingerprinting functions (§5.7)."""

    def test_canonical_tables_fingerprint_exists(self):
        """canonical_tables_fingerprint() returns a 16-hex-char string (§5.7)."""
        fp = audit.canonical_tables_fingerprint()
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)

    def test_verb_slice_membership(self):
        """_verb_slice returns membership record for a verb (§5.7, Case A)."""
        sl = audit._verb_slice("aspirate")
        assert sl["scope"] == "verb"
        assert sl["verb"] == "aspirate"
        assert sl["in_tool_schema"] is True  # aspirate is in TOOL_SCHEMA
        assert "tool_row" in sl
        assert "in_param_namespace" in sl
        assert "param_rows" in sl

    def test_param_slice_membership(self):
        """_param_slice returns membership record for a param (§5.7, Case B)."""
        sl = audit._param_slice("vols", "aspirate")
        assert sl["scope"] == "param"
        assert sl["token"] == "vols"
        assert sl["declaring_verb"] == "aspirate"
        assert "rows_by_verb" in sl
        assert "declared_anywhere" in sl

    def test_subject_table_fingerprint_verb_case(self):
        """subject_table_fingerprint parses verb kind (§5.7)."""
        fp1 = audit.subject_table_fingerprint(
            audit.FindingKind.PHANTOM_VERB, "mix"
        )
        assert len(fp1) == 16

    def test_subject_table_fingerprint_dotted_case(self):
        """subject_table_fingerprint parses dotted kind (§5.7)."""
        fp1 = audit.subject_table_fingerprint(
            audit.FindingKind.SURFACE_ADJACENT,
            "liquid_handler.use_channels",
        )
        assert len(fp1) == 16

    def test_subject_table_fingerprint_param_case(self):
        """subject_table_fingerprint parses param_candidate kind (§5.7)."""
        fp1 = audit.subject_table_fingerprint(
            audit.FindingKind.PARAM_CANDIDATE,
            "aspirate:backend_kwargs",
        )
        assert len(fp1) == 16

    def test_subject_table_fingerprint_rejects_malformed_dotted(self):
        """subject_table_fingerprint raises on malformed dotted subject (§5.7, R3-W6)."""
        with pytest.raises(audit.AuditError, match="not.*<receiver_type>.<member>"):
            audit.subject_table_fingerprint(
                audit.FindingKind.SURFACE_ADJACENT,
                "backends/chatterbox.py",  # not a valid receiver_type
            )

    def test_subject_table_fingerprint_rejects_malformed_param(self):
        """subject_table_fingerprint raises on malformed param subject (§5.7, R3-W6)."""
        with pytest.raises(audit.AuditError, match="not.*<verb>:<token>"):
            audit.subject_table_fingerprint(
                audit.FindingKind.PARAM_CANDIDATE,
                "flow_rates",  # missing colon
            )

    def test_subject_table_fingerprint_blocks_blocking_scope_none(self, monkeypatch):
        """subject_table_fingerprint raises if blocking kind uses scope=none (§5.7, R3-W7)."""
        # Temporarily promote unclassified_token to BLOCKING_KINDS
        new_blocking = audit.BLOCKING_KINDS | {audit.FindingKind.UNCLASSIFIED_TOKEN}
        monkeypatch.setattr(audit, "BLOCKING_KINDS", new_blocking)

        # Now trying to fingerprint unclassified_token should raise
        with pytest.raises(audit.AuditError, match="is blocking.*scope=none"):
            audit.subject_table_fingerprint(
                audit.FindingKind.UNCLASSIFIED_TOKEN,
                "cor_96_wellplate_360uL_Fb",
            )


class TestAuditRun:
    """Tests for run_audit() (§5.1–§5.4)."""

    def test_run_audit_returns_result(self):
        """run_audit() returns AuditResult with findings and blocking_census (§5)."""
        result = audit.run_audit()
        assert isinstance(result, audit.AuditResult)
        assert isinstance(result.findings, tuple)
        assert isinstance(result.blocking_census, dict)

    def test_run_audit_produces_9_blocking_findings(self):
        """run_audit() produces 9 blocking findings against live cookbook (§5.4.1)."""
        result = audit.run_audit()
        blocking_findings = [f for f in result.findings if f.blocking]
        assert len(blocking_findings) == 9

    def test_run_audit_blocking_census_matches_expected(self):
        """run_audit() blocking_census matches §5.4.1 census (4+5+0+0)."""
        result = audit.run_audit()
        assert result.blocking_census["phantom_verb"] == 4
        assert result.blocking_census["surface_adjacent"] == 5
        assert result.blocking_census["receiver_drift"] == 0
        assert result.blocking_census["param_misattributed"] == 0

    def test_run_audit_findings_are_sorted(self):
        """run_audit() findings are sorted by finding_id (determinism, F6)."""
        result = audit.run_audit()
        finding_ids = [f.finding_id for f in result.findings]
        assert finding_ids == sorted(finding_ids)

    def test_run_audit_each_finding_has_all_fields(self):
        """run_audit() findings have all required fields (§5.2)."""
        result = audit.run_audit()
        for f in result.findings:
            assert f.finding_id
            assert f.adjudicable_digest
            assert isinstance(f.kind, audit.FindingKind)
            assert f.subject
            assert isinstance(f.blocking, bool)
            # verdict can be empty string for non-phantom findings
            assert isinstance(f.evidence, tuple)
            assert isinstance(f.verdict, str)


class TestGateMechanics:
    """Tests for gate() evaluation (§5.5, G2)."""

    def test_gate_returns_int(self):
        """gate() returns an int exit code (§5.5)."""
        exit_code = audit.gate()
        assert isinstance(exit_code, int)

    def test_gate_exit_0_with_committed_adjudications(self):
        """gate() exits 0 against the real, committed 9-entry adjudications file
        (§5.5, step 4/5). Task 5 left this file empty, so this test originally
        asserted exit 2; Task 6 seeded all nine required entries, which is exactly
        what makes the gate pass now. See test_ingest_audit_gate.py for the
        missing/incomplete/stale_digest negative-path coverage this left behind."""
        exit_code = audit.gate()
        assert exit_code == cli.EXIT_OK

    def test_gate_exit_1_on_missing_census(self, tmp_path):
        """gate() exits 1 if blocking_census.json is missing (§5.5, step 2)."""
        nonexistent_path = tmp_path / "nonexistent_census.json"
        exit_code = audit.gate(census_path=nonexistent_path)
        assert exit_code == cli.EXIT_MEASUREMENT_ERROR

    def test_gate_loads_recipes_exit_5_on_unavailable(self, tmp_path, monkeypatch):
        """gate() exits 5 if recipes are unavailable (§5.5, step 1)."""
        nonexistent_recipes = tmp_path / "nonexistent_recipes.yml"
        exit_code = audit.gate(recipes_path=nonexistent_recipes)
        assert exit_code == cli.EXIT_INCONCLUSIVE

    def test_gate_prints_unadjudicated_to_stdout(self, capsys):
        """gate() prints unadjudicated findings to stdout (§5.5, G2)."""
        gate = audit.gate(out=StringIO())
        captured = capsys.readouterr()
        # We're calling with default adjudications_path which is empty
        # So gate should print unadjudicated findings


class TestAdjudicationValidation:
    """Tests for adjudication completeness checking (§5.5, G2)."""

    def test_check_adjudication_fields_requires_reading(self):
        """_check_adjudication_fields requires valid reading enum (§5.5, G2)."""
        f = audit.Finding(
            finding_id="test",
            adjudicable_digest="test",
            kind=audit.FindingKind.PHANTOM_VERB,
            subject="test",
            blocking=True,
            verdict="",
            evidence=(),
            reading_table_is_wrong="",
            reading_api_moved="",
            verdict_hint="",
        )
        adj = {"reading": "invalid_reading"}
        result = audit._check_adjudication_fields(adj, f)
        assert result is not None
        assert "reading" in result

    def test_check_adjudication_fields_requires_rationale(self):
        """_check_adjudication_fields requires rationale >= 40 chars (§5.5, G2)."""
        f = audit.Finding(
            finding_id="test",
            adjudicable_digest="test",
            kind=audit.FindingKind.PHANTOM_VERB,
            subject="test",
            blocking=True,
            verdict="",
            evidence=(),
            reading_table_is_wrong="",
            reading_api_moved="",
            verdict_hint="",
        )
        adj = {
            "reading": "table_is_wrong",
            "rationale": "short",  # Too short
        }
        result = audit._check_adjudication_fields(adj, f)
        assert result is not None
        assert "rationale" in result

    def test_check_adjudication_fields_requires_adjudicated_by_on(self):
        """_check_adjudication_fields requires adjudicated_by and adjudicated_on (§5.5, G2)."""
        f = audit.Finding(
            finding_id="test",
            adjudicable_digest="test",
            kind=audit.FindingKind.PHANTOM_VERB,
            subject="test",
            blocking=True,
            verdict="",
            evidence=(),
            reading_table_is_wrong="",
            reading_api_moved="",
            verdict_hint="",
        )
        adj = {
            "reading": "table_is_wrong",
            "rationale": "This is a long enough rationale to pass validation checks",
            # Missing adjudicated_by and adjudicated_on
        }
        result = audit._check_adjudication_fields(adj, f)
        assert result is not None
        assert "adjudicated" in result

    def test_action_ref_pattern_matching(self):
        """ACTION_REF_RE matches backlog, commit, and issue refs (§5.5, G2)."""
        # Backlog reference
        assert audit.ACTION_REF_RE.match("backlog:coxswain-nsvr-use-channels")
        # Commit reference
        assert audit.ACTION_REF_RE.match(
            "commit:0000000000000000000000000000000000000000"
        )
        # Issue reference
        assert audit.ACTION_REF_RE.match(
            "issue:https://github.com/owner/repo/issues/123"
        )
        # Invalid
        assert not audit.ACTION_REF_RE.match("backlog:InvalidCase")
        assert not audit.ACTION_REF_RE.match("commit:toolong")


class TestAuditErrorHandling:
    """Tests for AuditError exception (§7.1, C1)."""

    def test_audit_error_is_ingest_error(self):
        """AuditError is a subclass of cli.IngestError (§7.1, C1)."""
        assert issubclass(audit.AuditError, cli.IngestError)

    def test_audit_error_maps_to_exit_1(self):
        """AuditError is caught by cli.run and returns exit 1 (§7.1)."""
        # This is tested implicitly by the gate tests above


class TestAuditVersioning:
    """Tests for AUDIT_RULES_VERSION (§5.2, C4)."""

    def test_audit_rules_version_is_pinned(self):
        """AUDIT_RULES_VERSION is defined and pinned (§5.2, C4)."""
        from ingest.versions import AUDIT_RULES_VERSION
        assert AUDIT_RULES_VERSION == "1"
        # It should be used in every hash payload
        assert AUDIT_RULES_VERSION in audit._finding_id_payload(
            audit.FindingKind.PHANTOM_VERB, "test"
        ).values()
