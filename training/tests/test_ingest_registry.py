"""Tests for the ingest registry loader (sources.py).

Covers all ten load-time invariants (I1–I10), admission state census,
the live-deadline branch (AC-1.12), and the exception hierarchy.

§2.1–2.4 defines the invariants. §7.1's hierarchy table is the normative
specification of error classes. Rev 7 (C1): RegistryError subclasses cli.IngestError,
checked here at the task that introduces it.
"""

import json
import pytest
import tempfile
from datetime import datetime, date as dateclass, timedelta
from pathlib import Path

from ingest import sources, cli


def make_test_registry(bad_row_index: int = -1, **overrides) -> dict:
    """Create a 21-row test registry with unique source_ids.

    Args:
        bad_row_index: Index of the row to apply overrides to (-1 = none).
        **overrides: Fields to override in the specified row.
    """
    sources_list = []
    for i in range(21):
        row = {
            "source_id": f"test{i:02d}__repo",
            "repo_url": f"https://github.com/test{i}/repo",
            "clone_path": f"~/projects/repos/test{i}",
            "pinned_sha": "0" * 40,
            "genre": "unclear",
            "extractor_kind": "python",
            "admission_state": "pending_recon",
            "admission_argument": "",
            "rejection_reason": "testing",
            "tier_ceiling": 2,
            "tier_ceiling_reason": "",
        }

        if i == bad_row_index:
            row.update(overrides)

        sources_list.append(row)

    return {"registry_version": "2", "sources": sources_list}


class TestRegistryLoading:
    """Test successful registry loading."""

    def test_load_registry_succeeds(self) -> None:
        """Test that the committed sources.json loads without errors."""
        registry = sources.load_registry()
        assert len(registry) == 21, "Registry must have exactly 21 rows (I1)"

    def test_registry_has_correct_census(self) -> None:
        """Test the 1/18/2 admission_state census (§2.3)."""
        registry = sources.load_registry()

        admitted = [r for r in registry if r.admission_state == sources.AdmissionState.ADMITTED]
        pending = [r for r in registry if r.admission_state == sources.AdmissionState.PENDING_RECON]
        rejected = [r for r in registry if r.admission_state == sources.AdmissionState.REJECTED_PERMANENT]

        assert len(admitted) == 1, "Exactly 1 row should be ADMITTED"
        assert len(pending) == 18, "Exactly 18 rows should be PENDING_RECON"
        assert len(rejected) == 2, "Exactly 2 rows should be REJECTED_PERMANENT"

        # Verify the cookbook is admitted
        cookbook = admitted[0]
        assert cookbook.source_id == "chory-lab__plr-cookbook"

        # Verify the two rejected rows
        rejected_ids = {r.source_id for r in rejected}
        assert rejected_ids == {"GreenTilden__oolitic-plr", "vanallenlab__agentic-ai-codebase"}

    def test_cookbook_admission_argument(self) -> None:
        """Test that the cookbook has the required admission argument."""
        registry = sources.load_registry()
        cookbook = next(r for r in registry if r.source_id == "chory-lab__plr-cookbook")
        assert cookbook.admission_argument
        assert "H1" in cookbook.admission_argument

    def test_cheshire_drivers_ceiling(self) -> None:
        """Test that cheshire-drivers has tier_ceiling: 2 (not capped by license)."""
        registry = sources.load_registry()
        row = next(r for r in registry if r.source_id == "Cheshire-Labs__cheshire-drivers")
        assert row.tier_ceiling == 2, "cheshire-drivers must have tier_ceiling: 2 (C16)"

    def test_by_id_lookup(self) -> None:
        """Test the by_id() helper function."""
        row = sources.by_id("chory-lab__plr-cookbook")
        assert row.source_id == "chory-lab__plr-cookbook"

        with pytest.raises(sources.RegistryError):
            sources.by_id("nonexistent__repo")


class TestInvariantI1:
    """Test invariant I1: exactly 21 rows; source_id unique."""

    def test_i1_wrong_count(self) -> None:
        """Test that I1 rejects row counts != 21."""
        data = {
            "registry_version": "2",
            "sources": [
                {
                    "source_id": "test__repo",
                    "repo_url": "https://github.com/test/repo",
                    "clone_path": "~/projects/repos/test",
                    "pinned_sha": "0" * 40,
                    "genre": "unclear",
                    "extractor_kind": "python",
                    "admission_state": "pending_recon",
                    "admission_argument": "",
                    "rejection_reason": "testing",
                    "tier_ceiling": 2,
                    "tier_ceiling_reason": "",
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="exactly 21 rows"):
                sources.load_registry(path)
        finally:
            path.unlink()

    def test_i1_duplicate_source_id(self) -> None:
        """Test that I1 rejects duplicate source_id."""
        base_row = {
            "source_id": "duplicate__repo",
            "repo_url": "https://github.com/test/repo",
            "clone_path": "~/projects/repos/test",
            "pinned_sha": "0" * 40,
            "genre": "unclear",
            "extractor_kind": "python",
            "admission_state": "pending_recon",
            "admission_argument": "",
            "rejection_reason": "testing",
            "tier_ceiling": 2,
            "tier_ceiling_reason": "",
        }

        data = {
            "registry_version": "2",
            "sources": [base_row.copy() for _ in range(21)]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="duplicate source_id"):
                sources.load_registry(path)
        finally:
            path.unlink()


class TestInvariantI2:
    """Test invariant I2: pinned_sha matches ^[0-9a-f]{40}$."""

    def test_i2_invalid_sha_short(self) -> None:
        """Test that I2 rejects short SHA."""
        data = make_test_registry(bad_row_index=0, pinned_sha="abc123")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I2 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()

    def test_i2_invalid_sha_uppercase(self) -> None:
        """Test that I2 rejects uppercase hex."""
        data = make_test_registry(bad_row_index=0, pinned_sha="0" * 39 + "A")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I2 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()


class TestInvariantI3:
    """Test invariant I3: clone_path validation."""

    def test_i3_path_not_in_repos(self) -> None:
        """Test that I3 rejects paths not starting with ~/projects/repos/."""
        data = make_test_registry(bad_row_index=0, clone_path="~/other/path")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I3 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()


class TestInvariantI4:
    """Test invariant I4: admission_state ⟺ admission_argument and rejection_reason."""

    def test_i4_admitted_missing_argument(self) -> None:
        """Test that I4 rejects ADMITTED without admission_argument."""
        data = make_test_registry(
            bad_row_index=0,
            genre="cookbook",
            extractor_kind="recipes_yml",
            admission_state="admitted",
            admission_argument="",  # Missing
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I4 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()

    def test_i4_pending_with_argument(self) -> None:
        """Test that I4 rejects PENDING_RECON with admission_argument."""
        data = make_test_registry(
            bad_row_index=0,
            admission_argument="should be empty",  # Wrong
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I4 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()

    def test_i4_pending_missing_reason(self) -> None:
        """Test that I4 rejects PENDING_RECON without rejection_reason."""
        data = make_test_registry(
            bad_row_index=0,
            rejection_reason="",  # Missing
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I4 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()


class TestInvariantI5:
    """Test invariant I5: ADMITTED ⇒ extractor_kind != NONE."""

    def test_i5_admitted_with_none_extractor(self) -> None:
        """Test that I5 rejects ADMITTED with extractor_kind NONE."""
        data = make_test_registry(
            bad_row_index=0,
            genre="cookbook",
            extractor_kind="none",  # Not allowed for admitted
            admission_state="admitted",
            admission_argument="testing",
            rejection_reason="",  # Required for ADMITTED
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I5 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()


class TestInvariantI6:
    """Test invariant I6: tier_ceiling and tier_ceiling_reason validation."""

    def test_i6_invalid_ceiling_value(self) -> None:
        """Test that I6 rejects invalid tier_ceiling values."""
        data = make_test_registry(bad_row_index=0, tier_ceiling=3)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I6 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()

    def test_i6_missing_prefix(self) -> None:
        """Test that I6 requires valid prefix for ceilings < 2."""
        data = make_test_registry(
            bad_row_index=0,
            tier_ceiling=0,
            tier_ceiling_reason="invalid reason",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I6 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()

    def test_i6_license_keyword_in_reason(self) -> None:
        """Test that I6 rejects 'licen' substring in ceiling_reason."""
        data = make_test_registry(
            bad_row_index=0,
            tier_ceiling=0,
            tier_ceiling_reason="contamination: license issue",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I6 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()

    def test_i6_gpl_keyword_in_reason(self) -> None:
        """Test that I6 rejects GPL keyword in ceiling_reason."""
        data = make_test_registry(
            bad_row_index=0,
            tier_ceiling=0,
            tier_ceiling_reason="contamination: AGPL license detected",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I6 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()


class TestInvariantI7:
    """Test invariant I7: last_push date format validation."""

    def test_i7_invalid_date_format(self) -> None:
        """Test that I7 rejects invalid date formats."""
        data = make_test_registry(bad_row_index=0, last_push="2024/06/01")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I7 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()


class TestInvariantI8:
    """Test invariant I8: AC-1.12 live-deadline rule for the cookbook."""

    def test_i8_future_deadline(self) -> None:
        """Test that a future deadline passes (AC-1.12)."""
        future_date = (dateclass.today() + timedelta(days=5)).strftime("%Y-%m-%d")

        # Create 21 unique rows, with the cookbook at index 0 having a future deadline
        sources_list = []
        for i in range(21):
            if i == 0:
                row = {
                    "source_id": "chory-lab__plr-cookbook",
                    "repo_url": "https://github.com/chory-lab/plr-cookbook",
                    "clone_path": "~/projects/repos/plr-cookbook",
                    "pinned_sha": "0" * 40,
                    "genre": "cookbook",
                    "extractor_kind": "recipes_yml",
                    "admission_state": "admitted",
                    "admission_argument": "test",
                    "rejection_reason": "",
                    "tier_ceiling": 2,
                    "tier_ceiling_reason": "",
                    "license_scan_dirs": ["cookbook"],
                    "license_request_due": future_date,
                }
            else:
                row = {
                    "source_id": f"test{i:02d}__repo",
                    "repo_url": f"https://github.com/test{i}/repo",
                    "clone_path": f"~/projects/repos/test{i}",
                    "pinned_sha": "0" * 40,
                    "genre": "unclear",
                    "extractor_kind": "python",
                    "admission_state": "pending_recon",
                    "admission_argument": "",
                    "rejection_reason": "testing",
                    "tier_ceiling": 2,
                    "tier_ceiling_reason": "",
                }
            sources_list.append(row)

        data = {"registry_version": "2", "sources": sources_list}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            # Should succeed
            registry = sources.load_registry(path)
            assert len(registry) == 21
        finally:
            path.unlink()

    def test_i8_past_deadline(self) -> None:
        """Test that a past deadline fails (AC-1.12)."""
        past_date = (dateclass.today() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Create 21 unique rows, with the cookbook at index 0 having a past deadline
        sources_list = []
        for i in range(21):
            if i == 0:
                row = {
                    "source_id": "chory-lab__plr-cookbook",
                    "repo_url": "https://github.com/chory-lab/plr-cookbook",
                    "clone_path": "~/projects/repos/plr-cookbook",
                    "pinned_sha": "0" * 40,
                    "genre": "cookbook",
                    "extractor_kind": "recipes_yml",
                    "admission_state": "admitted",
                    "admission_argument": "test",
                    "rejection_reason": "",
                    "tier_ceiling": 2,
                    "tier_ceiling_reason": "",
                    "license_scan_dirs": ["cookbook"],
                    "license_request_due": past_date,
                }
            else:
                row = {
                    "source_id": f"test{i:02d}__repo",
                    "repo_url": f"https://github.com/test{i}/repo",
                    "clone_path": f"~/projects/repos/test{i}",
                    "pinned_sha": "0" * 40,
                    "genre": "unclear",
                    "extractor_kind": "python",
                    "admission_state": "pending_recon",
                    "admission_argument": "",
                    "rejection_reason": "testing",
                    "tier_ceiling": 2,
                    "tier_ceiling_reason": "",
                }
            sources_list.append(row)

        data = {"registry_version": "2", "sources": sources_list}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I8 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()

    def test_i8_missing_deadline(self) -> None:
        """Test that the cookbook requires a deadline."""
        # Create 21 unique rows, with the cookbook at index 0 having no deadline
        sources_list = []
        for i in range(21):
            if i == 0:
                row = {
                    "source_id": "chory-lab__plr-cookbook",
                    "repo_url": "https://github.com/chory-lab/plr-cookbook",
                    "clone_path": "~/projects/repos/plr-cookbook",
                    "pinned_sha": "0" * 40,
                    "genre": "cookbook",
                    "extractor_kind": "recipes_yml",
                    "admission_state": "admitted",
                    "admission_argument": "test",
                    "rejection_reason": "",
                    "tier_ceiling": 2,
                    "tier_ceiling_reason": "",
                    "license_scan_dirs": ["cookbook"],
                    "license_request_due": "",  # Missing
                }
            else:
                row = {
                    "source_id": f"test{i:02d}__repo",
                    "repo_url": f"https://github.com/test{i}/repo",
                    "clone_path": f"~/projects/repos/test{i}",
                    "pinned_sha": "0" * 40,
                    "genre": "unclear",
                    "extractor_kind": "python",
                    "admission_state": "pending_recon",
                    "admission_argument": "",
                    "rejection_reason": "testing",
                    "tier_ceiling": 2,
                    "tier_ceiling_reason": "",
                }
            sources_list.append(row)

        data = {"registry_version": "2", "sources": sources_list}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I8 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()


class TestInvariantI9:
    """Test invariant I9: license_scan_dirs path validation."""

    def test_i9_absolute_path(self) -> None:
        """Test that I9 rejects absolute paths."""
        data = make_test_registry(
            bad_row_index=0,
            license_scan_dirs=["/absolute/path"],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I9 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()

    def test_i9_parent_traversal(self) -> None:
        """Test that I9 rejects paths with .."""
        data = make_test_registry(
            bad_row_index=0,
            license_scan_dirs=["../other"],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I9 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()


class TestInvariantI10:
    """Test invariant I10: license_request_due_extensions validation."""

    def test_i10_missing_fields(self) -> None:
        """Test that I10 requires from/to/reason in each extension."""
        data = make_test_registry(
            bad_row_index=0,
            license_request_due_extensions=[
                {"from": "2026-09-01", "to": "2026-10-01"}  # Missing reason
            ],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I10 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()

    def test_i10_inverted_dates(self) -> None:
        """Test that I10 requires to > from."""
        data = make_test_registry(
            bad_row_index=0,
            license_request_due_extensions=[
                {"from": "2026-10-01", "to": "2026-09-01", "reason": "test"}  # Reversed
            ],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I10 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()

    def test_i10_too_long_extension(self) -> None:
        """Test that I10 requires delta ≤ 30 days."""
        data = make_test_registry(
            bad_row_index=0,
            license_request_due_extensions=[
                {"from": "2026-09-01", "to": "2026-10-31", "reason": "test"}  # 60 days
            ],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(sources.RegistryError, match="I10 violation"):
                sources.load_registry(path)
        finally:
            path.unlink()


class TestExceptionHierarchy:
    """Test the exception hierarchy (rev 7, C1)."""

    def test_registry_error_is_ingest_error(self) -> None:
        """Test that RegistryError subclasses cli.IngestError."""
        assert issubclass(sources.RegistryError, cli.IngestError)

    def test_cli_run_maps_registry_error_to_exit_1(self) -> None:
        """Test that cli.run maps RegistryError to exit 1."""

        def handler(args: object) -> int:
            raise sources.RegistryError("test error")

        parser = cli.IngestArgumentParser(prog="test")
        result = cli.run(handler, parser, argv=[])

        assert result == cli.EXIT_MEASUREMENT_ERROR  # Exit code 1
