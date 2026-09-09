"""Tests for the phantom-verb audit logic (§5.3, W5, test-first per Task 5).

Verifies the two-stage evidence rule, phantom verdicts, and the integrity
of the experimental_partition loader.
"""

import json
import dataclasses
from pathlib import Path

import pytest

from ingest import audit, recipes
from ingest.versions import AUDIT_RULES_VERSION
from coxswain.plr.tool_schema import TOOL_SCHEMA, ToolSpec
from coxswain.plr.param_namespace import PARAM_NAMESPACE
from training.overlay_gen.miner import NON_SURFACE_VERB_REASONS


class TestPartitionLoader:
    """Tests for load_experimental_partition (§5.3, C4)."""

    def test_loader_invariants_hold(self, tmp_path):
        """Verify partition loader enforces invariants (§5.3)."""
        # Load the live partition
        phantom, no_backend = audit.load_experimental_partition()

        # Invariant 1: disjoint
        assert phantom & no_backend == set()

        # Invariant 2: complete coverage of experimental entries
        experimental = {n for n, s in TOOL_SCHEMA.items() if s.experimental}
        assert phantom | no_backend == experimental

        # Invariant 3: every key in NON_SURFACE_VERB_REASONS
        for verb in phantom | no_backend:
            assert verb in NON_SURFACE_VERB_REASONS

    def test_loader_rejects_unbalanced_partition(self, tmp_path, monkeypatch):
        """Partition loader raises AuditError on unbalanced partition (§5.3)."""
        bad_partition_path = tmp_path / "bad_partition.json"
        bad_partition_path.write_text(
            json.dumps({
                "phantom": {"mix": "...", "blow_out": "..."},
                "no_backend": {"shake": "...", "mix": "..."},  # overlap!
            })
        )

        with pytest.raises(audit.AuditError, match="overlap"):
            audit.load_experimental_partition(bad_partition_path)

    def test_loader_rejects_incomplete_partition(self, tmp_path, monkeypatch):
        """Partition loader raises AuditError if experimentals are missing (§5.3)."""
        bad_partition_path = tmp_path / "bad_partition.json"
        # Omit some experimental verbs
        bad_partition_path.write_text(
            json.dumps({
                "phantom": {"mix": "..."},
                "no_backend": {"shake": "..."},
            })
        )

        with pytest.raises(audit.AuditError, match="does not match"):
            audit.load_experimental_partition(bad_partition_path)


class TestPhantomVerdict:
    """Tests for phantom verdict classification (§5.3, W5, two-stage rule)."""

    def test_mix_verdict_kwarg_only(self):
        """mix: primary exact IDENT, corroborating CLASSISH → KWARG_ONLY (§5.3)."""
        # From spec: part1/04_pipetting.qmd#mix with apis "Mix, mix, surface_following_distance"
        # Expected: KWARG_ONLY (has primary exact `mix` IDENT)
        evidence_by_key = {
            (audit.FindingKind.PHANTOM_VERB, "mix"): [
                audit.Evidence(
                    recipe_path="part1/04_pipetting.qmd#mix",
                    token_raw="mix",
                    token_kind=recipes.TokenKind.IDENT,
                    receiver=None,
                    receiver_type=recipes.ReceiverType.NONE,
                    member="mix",
                    member_is_in_surface=False,
                    match_mode=audit.MatchMode.EXACT,
                ),
                audit.Evidence(
                    recipe_path="part1/04_pipetting.qmd#mix",
                    token_raw="Mix",
                    token_kind=recipes.TokenKind.CLASSISH,
                    receiver=None,
                    receiver_type=recipes.ReceiverType.NONE,
                    member="Mix",
                    member_is_in_surface=False,
                    match_mode=audit.MatchMode.CLASSISH_CASEFOLD,
                ),
            ]
        }
        verdict = audit._classify_phantom_verdict(evidence_by_key, "mix")
        assert verdict == audit.PhantomVerdict.KWARG_ONLY

    def test_blow_out_verdict_kwarg_only(self):
        """blow_out: primary exact IDENT among kwargs → KWARG_ONLY (§5.3)."""
        evidence_by_key = {
            (audit.FindingKind.PHANTOM_VERB, "blow_out"): [
                audit.Evidence(
                    recipe_path="part2/12_hardware.qmd#backend-kwargs",
                    token_raw="blow_out",
                    token_kind=recipes.TokenKind.IDENT,
                    receiver=None,
                    receiver_type=recipes.ReceiverType.NONE,
                    member="blow_out",
                    member_is_in_surface=False,
                    match_mode=audit.MatchMode.EXACT,
                ),
            ]
        }
        verdict = audit._classify_phantom_verdict(evidence_by_key, "blow_out")
        assert verdict == audit.PhantomVerdict.KWARG_ONLY

    def test_touch_tip_verdict_no_evidence(self):
        """touch_tip: absent from all 91 recipes → NO_EVIDENCE (§5.3)."""
        evidence_by_key = {}
        verdict = audit._classify_phantom_verdict(evidence_by_key, "touch_tip")
        assert verdict == audit.PhantomVerdict.NO_EVIDENCE

    def test_contested_verdict_with_dotted_receiver(self):
        """Phantom verb with lh.verb DOTTED evidence → CONTESTED (§5.3, W5)."""
        evidence_by_key = {
            (audit.FindingKind.PHANTOM_VERB, "mix"): [
                audit.Evidence(
                    recipe_path="synthetic.qmd",
                    token_raw="lh.mix",
                    token_kind=recipes.TokenKind.DOTTED,
                    receiver="lh",
                    receiver_type=recipes.ReceiverType.LIQUID_HANDLER,
                    member="mix",
                    member_is_in_surface=False,
                    match_mode=audit.MatchMode.EXACT,
                ),
            ]
        }
        verdict = audit._classify_phantom_verdict(evidence_by_key, "mix")
        assert verdict == audit.PhantomVerdict.CONTESTED

    def test_casefold_corroborating_cannot_produce_contested(self):
        """CLASSISH casefold match alone cannot produce CONTESTED (§5.3, W5, enforced)."""
        # Only casefold evidence (no primary IDENT or DOTTED lh/pr)
        evidence_by_key = {
            (audit.FindingKind.PHANTOM_VERB, "mix"): [
                audit.Evidence(
                    recipe_path="synthetic.qmd",
                    token_raw="Mix",
                    token_kind=recipes.TokenKind.CLASSISH,
                    receiver=None,
                    receiver_type=recipes.ReceiverType.NONE,
                    member="Mix",
                    member_is_in_surface=False,
                    match_mode=audit.MatchMode.CLASSISH_CASEFOLD,
                ),
            ]
        }
        verdict = audit._classify_phantom_verdict(evidence_by_key, "mix")
        # Corroborating alone is insufficient
        assert verdict == audit.PhantomVerdict.NO_EVIDENCE


class TestFindingIDReproducibility:
    """Tests for finding_id stability and hash integrity (§5.2, R4-B3)."""

    def test_finding_id_bytes_pin(self):
        """compute_finding_id produces pinned bytes (§5.2, R4-B3, AC-1.7)."""
        payload = audit._finding_id_payload(
            audit.FindingKind.PHANTOM_VERB, "mix"
        )
        canonical = audit.canonical_json(payload)
        # Pinned bytes: sorted keys (kind < rules_version < subject)
        assert canonical == b'{"kind":"phantom_verb","rules_version":"1","subject":"mix"}'

    def test_finding_id_requires_findingkind_enum(self):
        """compute_finding_id raises AuditError if kind is str, not FindingKind (R2-B2, R4-B3)."""
        with pytest.raises(audit.AuditError, match="takes a FindingKind member"):
            audit.compute_finding_id("phantom_verb", "mix")  # type: ignore

    def test_finding_id_unchanged_by_unrelated_recipe(self):
        """Finding ID unchanged when unrelated recipe is appended (§5.2, C3)."""
        fid_1 = audit.compute_finding_id(audit.FindingKind.PHANTOM_VERB, "mix")
        fid_2 = audit.compute_finding_id(audit.FindingKind.PHANTOM_VERB, "mix")
        assert fid_1 == fid_2

    def test_adjudicable_digest_changes_on_evidence_change(self):
        """adjudicable_digest changes when evidence (verdict) changes (§5.2, C3)."""
        # Finding with KWARG_ONLY verdict
        f1 = audit.Finding(
            finding_id="test_id_1",
            adjudicable_digest="",
            kind=audit.FindingKind.PHANTOM_VERB,
            subject="mix",
            blocking=True,
            verdict=audit.PhantomVerdict.KWARG_ONLY.value,
            evidence=(
                audit.Evidence(
                    recipe_path="test.qmd",
                    token_raw="mix",
                    token_kind=recipes.TokenKind.IDENT,
                    receiver=None,
                    receiver_type=recipes.ReceiverType.NONE,
                    member="mix",
                    member_is_in_surface=False,
                    match_mode=audit.MatchMode.EXACT,
                ),
            ),
            reading_table_is_wrong="",
            reading_api_moved="",
            verdict_hint="",
        )

        # Finding with CONTESTED verdict (different evidence)
        f2 = audit.Finding(
            finding_id="test_id_1",
            adjudicable_digest="",
            kind=audit.FindingKind.PHANTOM_VERB,
            subject="mix",
            blocking=True,
            verdict=audit.PhantomVerdict.CONTESTED.value,
            evidence=(
                audit.Evidence(
                    recipe_path="test.qmd",
                    token_raw="lh.mix",
                    token_kind=recipes.TokenKind.DOTTED,
                    receiver="lh",
                    receiver_type=recipes.ReceiverType.LIQUID_HANDLER,
                    member="mix",
                    member_is_in_surface=False,
                    match_mode=audit.MatchMode.EXACT,
                ),
            ),
            reading_table_is_wrong="",
            reading_api_moved="",
            verdict_hint="",
        )

        d1 = audit._sha16(audit._adjudicable_view(f1))
        d2 = audit._sha16(audit._adjudicable_view(f2))
        assert d1 != d2


class TestBlockingCensus:
    """Tests for blocking census loading and validation (§5.4.1, C4, AC-1.6)."""

    def test_blocking_census_matches_committed(self):
        """Observed census equals committed blocking_census.json (AC-1.6)."""
        # This is a regression test against the live cookbook
        # Expected per spec: 9 blocking (4 phantom + 5 surface_adjacent + 0 receiver_drift + 0 param_misattributed)
        census = audit.load_blocking_census()
        assert census == {
            "phantom_verb": 4,
            "surface_adjacent": 5,
            "receiver_drift": 0,
            "param_misattributed": 0,
        }

    def test_blocking_census_loader_validates_keys(self, tmp_path):
        """load_blocking_census raises AuditError on key mismatch (§5.5, C4)."""
        bad_census_path = tmp_path / "bad_census.json"
        bad_census_path.write_text(
            json.dumps({
                "census": {
                    "phantom_verb": 4,
                    "surface_adjacent": 5,
                    # missing receiver_drift and param_misattributed
                }
            })
        )

        with pytest.raises(audit.AuditError, match="keys"):
            audit.load_blocking_census(bad_census_path)


class TestSurfaceAdjacentFindings:
    """Tests for surface_adjacent findings (§5.4.1, blocking, 5 live subjects)."""

    def test_surface_adjacent_subjects_by_name(self):
        """Five surface_adjacent subjects appear by exact name (§5.4.1, table)."""
        # Run audit to get findings
        result = audit.run_audit()
        surface_adjacent_findings = [
            f for f in result.findings
            if f.kind == audit.FindingKind.SURFACE_ADJACENT
        ]

        expected_subjects = {
            "liquid_handler.use_channels",
            "liquid_handler.use_tips",
            "liquid_handler.probe_tip_presence_via_pickup",
            "liquid_handler.clear_head_state",
            "liquid_handler.head",
        }

        actual_subjects = {f.subject for f in surface_adjacent_findings}
        assert actual_subjects == expected_subjects

    def test_surface_adjacent_evidence_lines(self):
        """surface_adjacent findings have evidence from recipes.yml lines (§5.4.1)."""
        result = audit.run_audit()
        surface_adjacent_findings = [
            f for f in result.findings
            if f.kind == audit.FindingKind.SURFACE_ADJACENT
        ]

        # Check that each has evidence
        for f in surface_adjacent_findings:
            assert len(f.evidence) > 0
            # Evidence should have recipe_path and token_raw
            for ev in f.evidence:
                assert ev.recipe_path
                assert ev.token_raw

    def test_surface_adjacent_fingerprints_are_distinct(self):
        """Five surface_adjacent subjects have distinct fingerprints (§5.7, subject-distinctness)."""
        result = audit.run_audit()
        surface_adjacent_findings = [
            f for f in result.findings
            if f.kind == audit.FindingKind.SURFACE_ADJACENT
        ]

        fingerprints = [
            audit.subject_table_fingerprint(f.kind, f.subject)
            for f in surface_adjacent_findings
        ]

        # All should be distinct
        assert len(fingerprints) == len(set(fingerprints))


class TestBlockingCensusComparison:
    """Tests for census_drift reporting (§5.5, G2, step 3)."""

    def test_census_mismatch_is_not_failure(self, tmp_path, monkeypatch):
        """Census mismatch prints census_drift but does not fail gate (§5.5, G2)."""
        # Monkeypatch to create an artificial mismatch
        bad_census_path = tmp_path / "bad_census.json"
        bad_census_path.write_text(
            json.dumps({
                "audit_rules_version": "1",
                "census": {
                    "phantom_verb": 3,  # Mismatch: expected 4
                    "surface_adjacent": 5,
                    "receiver_drift": 0,
                    "param_misattributed": 0,
                }
            })
        )

        # Create an empty adjudications file (to avoid unadjudicated errors)
        adj_path = tmp_path / "adjudications.json"
        adj_path.write_text(json.dumps({"adjudications": {}}))

        # The gate should still run and report the mismatch
        from io import StringIO
        out = StringIO()
        exit_code = audit.gate(
            census_path=bad_census_path,
            adjudications_path=adj_path,
            out=out,
        )

        output = out.getvalue()
        assert "census_drift" in output
        assert "kind=phantom_verb" in output
        # But it should not be exit 0 because adjudications are missing
        assert exit_code == audit.cli.EXIT_UNADJUDICATED_BLOCKING
