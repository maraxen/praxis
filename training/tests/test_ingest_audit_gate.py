"""Tests for the G2 gate — `audit.gate()`'s exit-code contract (§5.5, Task 6).

Drives `audit.gate(...)` in-process via its `recipes_path` / `adjudications_path` /
`census_path` keyword overrides. Per §5.5, the injection is Python-level ONLY — the
CLI exposes no path flags for these, so every fixture here calls the function
directly rather than going through argv (a path flag on a blocking gate would be a
bypass with a different name).

Evaluation order under test (§5.5):
  1. load_recipes() -> run_audit()          CookbookUnavailable -> exit 5
  2. load_blocking_census()                 AuditError          -> exit 1
  3. census comparison                      drift is NOT a failure (stdout only)
  4. adjudication completeness              any failure         -> exit 2
  5. all four passed                        -> exit 0
"""

import json
from io import StringIO
from pathlib import Path

import pytest

from ingest import audit, cli, recipes

DATA_DIR = Path(audit.__file__).parent / "data"
REAL_ADJUDICATIONS_PATH = DATA_DIR / "audit_adjudications.json"
REAL_CENSUS_PATH = DATA_DIR / "blocking_census.json"


# ============================================================================
# Fixture helpers
# ============================================================================


def _load_real_adjudications() -> dict:
    with open(REAL_ADJUDICATIONS_PATH) as f:
        return json.load(f)


def _write_adjudications(tmp_path: Path, data: dict, name: str = "adjudications.json") -> Path:
    out = tmp_path / name
    out.write_text(json.dumps(data, indent=1))
    return out


def _flip_hex_digit(digest: str) -> str:
    """Flip the first hex character of a digest to produce a correct-shaped,
    but wrong, digest (a 'stale_digest', not a malformed one)."""
    first = digest[0]
    replacement = "0" if first != "0" else "1"
    return replacement + digest[1:]


def _first_file_backlog_item_id(data: dict) -> str:
    return next(
        fid
        for fid, adj in data["adjudications"].items()
        if adj.get("action") == "file_backlog_item"
    )


def _recipes_yml_without_use_channels_record(tmp_path: Path) -> Path:
    """A copy of the REAL recipes.yml with the sole `lh.use_channels` record
    (recipes.yml:152, the "Set default channels" recipe) deleted.

    That record is the ONLY place in the cookbook where `use_channels` appears
    as a DOTTED `lh.use_channels` token (the other three occurrences are bare
    IDENT tokens inside `apis:` lists, which never contribute surface_adjacent
    evidence). Deleting it drops the observed `surface_adjacent` census from 5
    to 4 while leaving all eight other blocking findings' evidence, and hence
    their adjudicable_digest, untouched (§ Task 6, R3-W3/R4-B1).
    """
    real_path = recipes.default_recipes_path()
    lines = real_path.read_text().splitlines(keepends=True)

    anchor = None
    for i, line in enumerate(lines):
        if line.strip() == 'apis: "lh.use_channels"':
            anchor = i
            break
    assert anchor is not None, (
        "fixture anchor not found: expected a bare `apis: \"lh.use_channels\"` "
        "line in the live recipes.yml (recipes.yml:152 at spec-authoring time). "
        "If the cookbook has changed, this fixture needs a new anchor."
    )

    start = anchor
    while not lines[start].strip().startswith("- title:"):
        start -= 1
        assert start >= 0, "walked off the start of the file looking for the record start"

    new_lines = lines[:start] + lines[anchor + 1:]
    out = tmp_path / "recipes_drift_down.yml"
    out.write_text("".join(new_lines))
    return out


# ============================================================================
# Sanity: the real, committed inputs
# ============================================================================


class TestGateSanity:
    def test_gate_exits_0_with_real_seeded_nine_entry_file(self):
        """--gate exits 0 against the real 9-entry audit_adjudications.json and
        the real blocking_census.json, with no path overrides at all."""
        assert audit.gate() == cli.EXIT_OK


# ============================================================================
# Completeness failures -> exit 2, each with its own labelled reason
# ============================================================================


class TestGateCompletenessFailures:
    def test_missing_adjudication_exits_2(self, tmp_path):
        """Removing any one adjudication entry from a temp copy -> exit 2, reason 'missing'."""
        data = _load_real_adjudications()
        removed_id = next(iter(data["adjudications"]))
        del data["adjudications"][removed_id]
        path = _write_adjudications(tmp_path, data)

        out = StringIO()
        code = audit.gate(adjudications_path=path, out=out)

        assert code == cli.EXIT_UNADJUDICATED_BLOCKING
        printed = out.getvalue()
        assert removed_id in printed
        assert "missing" in printed

    def test_short_rationale_exits_2_incomplete(self, tmp_path):
        """Shortening `rationale` below 40 chars -> exit 2, reason 'incomplete'."""
        data = _load_real_adjudications()
        target_id = next(iter(data["adjudications"]))
        data["adjudications"][target_id]["rationale"] = "too short"
        assert len(data["adjudications"][target_id]["rationale"]) < 40
        path = _write_adjudications(tmp_path, data)

        out = StringIO()
        code = audit.gate(adjudications_path=path, out=out)

        assert code == cli.EXIT_UNADJUDICATED_BLOCKING
        printed = out.getvalue()
        assert target_id in printed
        assert "incomplete" in printed

    def test_malformed_action_ref_exits_2_incomplete(self, tmp_path):
        """`action_ref: "x"` on a file_backlog_item adjudication fails ACTION_REF_RE
        -> exit 2, reason 'incomplete' (R3-W8's grammar, not a non-empty-string check)."""
        data = _load_real_adjudications()
        target_id = _first_file_backlog_item_id(data)
        data["adjudications"][target_id]["action_ref"] = "x"
        path = _write_adjudications(tmp_path, data)

        out = StringIO()
        code = audit.gate(adjudications_path=path, out=out)

        assert code == cli.EXIT_UNADJUDICATED_BLOCKING
        printed = out.getvalue()
        assert target_id in printed
        assert "incomplete" in printed

    def test_well_formed_action_ref_exits_0(self, tmp_path):
        """The positive case for the same finding: a real backlog:<id> ref
        (`backlog:coxswain-nsvr-use-channels`, per Task 6's own example)
        satisfies ACTION_REF_RE and the gate passes -- proves the regex
        actually ACCEPTS a well-formed ref, not just rejects a malformed one."""
        data = _load_real_adjudications()
        target_id = _first_file_backlog_item_id(data)
        data["adjudications"][target_id]["action_ref"] = "backlog:coxswain-nsvr-use-channels"
        path = _write_adjudications(tmp_path, data)

        code = audit.gate(adjudications_path=path)

        assert code == cli.EXIT_OK

    def test_stale_digest_exits_2(self, tmp_path):
        """A correct-but-stale `adjudicated_digest` (one hex digit flipped)
        -> exit 2, reason 'stale_digest'."""
        data = _load_real_adjudications()
        target_id = next(iter(data["adjudications"]))
        original_digest = data["adjudications"][target_id]["adjudicated_digest"]
        flipped = _flip_hex_digit(original_digest)
        assert flipped != original_digest
        data["adjudications"][target_id]["adjudicated_digest"] = flipped
        path = _write_adjudications(tmp_path, data)

        out = StringIO()
        code = audit.gate(adjudications_path=path, out=out)

        assert code == cli.EXIT_UNADJUDICATED_BLOCKING
        printed = out.getvalue()
        assert target_id in printed
        assert "stale_digest" in printed

    def test_every_exit_2_failure_names_every_failing_finding_id(self, tmp_path):
        """When TWO independent failures are injected at once (one missing, one
        incomplete), both finding_ids and both reasons are printed -- not just
        the first one found (§5.5: 'printing every failing finding_id with its
        reason')."""
        data = _load_real_adjudications()
        ids = list(data["adjudications"])
        missing_id = ids[0]
        incomplete_id = ids[1]
        del data["adjudications"][missing_id]
        data["adjudications"][incomplete_id]["rationale"] = "short"
        path = _write_adjudications(tmp_path, data)

        out = StringIO()
        code = audit.gate(adjudications_path=path, out=out)

        assert code == cli.EXIT_UNADJUDICATED_BLOCKING
        printed = out.getvalue()
        assert missing_id in printed and "missing" in printed
        assert incomplete_id in printed and "incomplete" in printed


# ============================================================================
# Census-absent -> exit 1 (never 0, never 2), three ways it can be broken
# ============================================================================


class TestGateCensusAbsentExitsOne:
    def test_census_file_missing_entirely_exits_1(self, tmp_path):
        nonexistent = tmp_path / "no_such_census.json"
        out = StringIO()

        code = audit.gate(census_path=nonexistent, out=out)

        assert code == cli.EXIT_MEASUREMENT_ERROR
        printed = out.getvalue()
        assert str(nonexistent) in printed
        assert "audit" in printed and "emit-census" in printed and "--out" in printed

    def test_census_file_present_but_invalid_json_exits_1(self, tmp_path):
        bad = tmp_path / "invalid_census.json"
        bad.write_text("{this is not valid json")
        out = StringIO()

        code = audit.gate(census_path=bad, out=out)

        assert code == cli.EXIT_MEASUREMENT_ERROR
        printed = out.getvalue()
        assert str(bad) in printed
        assert "audit" in printed and "emit-census" in printed and "--out" in printed

    def test_census_file_present_with_wrong_key_set_exits_1(self, tmp_path):
        bad = tmp_path / "wrong_keys_census.json"
        # Missing receiver_drift and param_misattributed keys -- fails the
        # loader's set(census) == {k.value for k in BLOCKING_KINDS} invariant.
        bad.write_text(json.dumps({
            "blocking_census_version": "1",
            "audit_rules_version": "1",
            "census": {"phantom_verb": 4, "surface_adjacent": 5},
        }))
        out = StringIO()

        code = audit.gate(census_path=bad, out=out)

        assert code == cli.EXIT_MEASUREMENT_ERROR
        printed = out.getvalue()
        assert str(bad) in printed
        assert "audit" in printed and "emit-census" in printed and "--out" in printed


# ============================================================================
# Ordering: clone-absent (exit 5) wins over census-absent (exit 1)
# ============================================================================


class TestGateOrdering:
    def test_clone_absent_and_census_absent_exits_5_not_1(self, tmp_path, monkeypatch):
        """With BOTH the clone absent and the census file missing, the gate
        exits 5, not 1 -- the clone check (step 1) runs before the census check
        (step 2), so a machine with no clone is never told to run a census-emit
        command it cannot service either (§5.5, R4-W10's ordering fixture)."""
        monkeypatch.setattr(
            recipes, "default_recipes_path",
            lambda: tmp_path / "no_such_clone" / "cookbook" / "recipes.yml",
        )
        nonexistent_census = tmp_path / "no_such_census.json"

        code = audit.gate(census_path=nonexistent_census)

        assert code == cli.EXIT_INCONCLUSIVE

    def test_clone_absent_alone_exits_5(self, tmp_path):
        """Exit 5, not 0 or 2, when the cookbook clone is absent generally
        (§7.5) -- before any adjudication or census logic runs at all."""
        nonexistent_recipes = tmp_path / "no_such_clone" / "cookbook" / "recipes.yml"

        code = audit.gate(recipes_path=nonexistent_recipes)

        assert code == cli.EXIT_INCONCLUSIVE


# ============================================================================
# census_drift: drift DOWN is exit 0 (not a failure), drift UP would be exit 2
# ============================================================================


class TestCensusDrift:
    def test_drift_down_exits_0_with_census_drift_line(self, tmp_path):
        """A temp recipes.yml with the lh.use_channels recipe removed drops the
        observed surface_adjacent census from 5 to 4. The other eight blocking
        findings stay adjudicated and digest-stable, so completeness still
        passes; the drift is reported, not failed on (§5.5 step 3, R3-W3/R4-B1).
        This is the ONLY fixture in this file that exercises the real (patched)
        recipes.yml content rather than a synthetic one, and is the only
        detector this package has for a cookbook-side surface_adjacent
        disappearance (a surface_adjacent adjudication can never go
        stale_digest, per §5.7/R3-B1)."""
        drifted_recipes = _recipes_yml_without_use_channels_record(tmp_path)
        out = StringIO()

        code = audit.gate(recipes_path=drifted_recipes, out=out)

        assert code == cli.EXIT_OK
        printed = out.getvalue()
        assert "census_drift kind=surface_adjacent pinned=5 observed=4" in printed

    def test_drift_down_leaves_the_other_eight_findings_untouched(self, tmp_path):
        """Sanity check on the fixture itself: exactly one blocking finding
        (liquid_handler.use_channels) disappears; nothing else about the
        cookbook's blocking census shifts as a side effect."""
        drifted_recipes = _recipes_yml_without_use_channels_record(tmp_path)

        result = audit.run_audit(drifted_recipes)

        assert result.blocking_census["surface_adjacent"] == 4
        assert result.blocking_census["phantom_verb"] == 4
        assert result.blocking_census["receiver_drift"] == 0
        assert result.blocking_census["param_misattributed"] == 0
        blocking_ids = {f.finding_id for f in result.findings if f.blocking}
        assert len(blocking_ids) == 8
