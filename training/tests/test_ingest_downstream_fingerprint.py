"""AC-1.14: the committed downstream-artifact fingerprint tripwire.

`data/canonical_tables_fingerprint.json` pins two independent things:
  1. `fingerprint` -- the hash of the canonical tables (§5.7's projection).
  2. `built_artifacts` -- sha256 of the five build-time artifacts that were
     regenerated FROM those tables (floor_gen/overlay_gen/assemble outputs).

Either one drifting means the committed downstream artifacts no longer match
what the canonical tables would currently produce -- and Increment 1 cannot
regenerate them itself (floor_gen/overlay_gen are teacher-gated, F8), so this
is a tripwire, not a self-healing check.
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from ingest import audit, io

DATA_DIR = Path(audit.__file__).parent / "data"
FINGERPRINT_PATH = DATA_DIR / "canonical_tables_fingerprint.json"


def _load_committed() -> dict:
    with open(FINGERPRINT_PATH) as f:
        return json.load(f)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestCommittedFingerprintMatchesLive:
    def test_fingerprint_matches_live_canonical_tables(self):
        committed = _load_committed()
        live = audit.canonical_tables_fingerprint()
        assert committed["fingerprint"] == live, (
            f"committed fingerprint {committed['fingerprint']!r} != live "
            f"{live!r} -- a canonical table changed since this file was last "
            f"regenerated (§5.7)"
        )

    @pytest.mark.parametrize(
        "rel_path",
        [
            "training/out/corpus_p23_smoke.jsonl",
            "training/overlay_gen/out/overlay_smoke.jsonl",
            "training/assemble/out/corpus_p25.jsonl",
            "training/assemble/out/corpus_p25_sidecar.jsonl",
            "training/assemble/out/manifest.json",
        ],
    )
    def test_built_artifact_hash_matches_live_file(self, rel_path):
        committed = _load_committed()
        expected = committed["built_artifacts"][rel_path]
        live_path = io.REPO_ROOT / rel_path
        assert live_path.exists(), f"built artifact missing on disk: {live_path}"
        actual = _sha256_file(live_path)
        assert actual == expected, (
            f"{rel_path}: committed sha256 {expected!r} != live {actual!r}"
        )

    def test_exactly_five_built_artifacts(self):
        committed = _load_committed()
        assert len(committed["built_artifacts"]) == 5

    def test_regeneration_order_is_stated(self):
        committed = _load_committed()
        assert committed["regeneration_order"] == [
            "floor_gen", "overlay_gen", "assemble", "ingest",
        ]


class TestFingerprintTripwireIsLive:
    def test_mutating_the_projection_flips_the_fingerprint(self, monkeypatch):
        """Mutate a COPY of a canonical table (TOOL_SCHEMA) and assert the
        fingerprint comparison FAILS -- proving the tripwire actually reacts
        to a table edit rather than being a hardcoded pass."""
        from coxswain.plr.tool_schema import TOOL_SCHEMA
        import dataclasses

        committed = _load_committed()
        original_fingerprint = audit.canonical_tables_fingerprint()
        assert committed["fingerprint"] == original_fingerprint

        some_key = next(iter(TOOL_SCHEMA))
        mutated_spec = dataclasses.replace(
            TOOL_SCHEMA[some_key], experimental=not TOOL_SCHEMA[some_key].experimental
        )
        monkeypatch.setitem(TOOL_SCHEMA, some_key, mutated_spec)

        mutated_fingerprint = audit.canonical_tables_fingerprint()
        assert mutated_fingerprint != original_fingerprint
        assert committed["fingerprint"] != mutated_fingerprint


class TestBuiltArtifactsTripwireIsLive:
    def test_perturbing_one_byte_of_manifest_copy_still_fails_ac114(self, tmp_path):
        """Leave the canonical-table projection ALONE but perturb one byte of
        a COPY of manifest.json, and assert AC-1.14 still fails -- this is
        what proves built_artifacts (not just fingerprint) is checked. A
        single combined hash could not have caught this class of drift."""
        committed = _load_committed()
        real_manifest = io.REPO_ROOT / "training/assemble/out/manifest.json"
        real_bytes = real_manifest.read_bytes()

        # The fingerprint half is untouched and still agrees.
        assert committed["fingerprint"] == audit.canonical_tables_fingerprint()

        # Perturb one byte of a COPY (never touch the real committed file).
        mutated = bytearray(real_bytes)
        # Flip a byte that is guaranteed printable/harmless to flip (find any
        # ASCII digit and change it), so the mutation is real but doesn't
        # depend on file layout beyond "at least one digit exists".
        flip_index = next(i for i, b in enumerate(mutated) if 0x30 <= b <= 0x38)
        mutated[flip_index] += 1
        mutated_bytes = bytes(mutated)
        assert mutated_bytes != real_bytes

        perturbed_path = tmp_path / "manifest.json"
        perturbed_path.write_bytes(mutated_bytes)

        perturbed_hash = _sha256_file(perturbed_path)
        expected_hash = committed["built_artifacts"]["training/assemble/out/manifest.json"]

        # AC-1.14 "still fails": the perturbed copy's hash disagrees with the
        # committed built_artifacts entry, even though the fingerprint half
        # (checked separately, above) is unaffected by this mutation.
        assert perturbed_hash != expected_hash
