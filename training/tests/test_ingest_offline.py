"""AC-1.16: §7.5's clone-absent behaviour table, parametrized row-for-row.

19 cases over 15 rows: 13 command rows contribute one case each; the exit-64
row (six emitter commands with --out omitted) expands to six cases, one per
command; the `pytest -k ingest` "all pass, clone-dependent tests skip" row is
a suite-level assertion, not a parametrized case, and is not counted.

Two independent clone-absence axes are simulated:
  - `recipes.default_recipes_path()` is monkeypatched to a nonexistent path
    -- this is what makes the cookbook clone "absent" for recipes.py,
    audit.py, gap.py and eval_split.py's --emit (all of which resolve
    recipes.yml through this one function).
  - `licenses.py` does NOT consult `default_recipes_path()` at all -- it
    operates on the full 21-row registry's own `clone_path` fields via
    `sources.load_registry()`. To simulate "clones absent" for its two
    clone-dependent commands (--check-descend, --verify-clones), the
    registry itself is monkeypatched (via `licenses.load_registry`) to a
    copy of the real 21 rows with every `clone_path` redirected to a
    guaranteed-nonexistent location. `--report` is clone-independent in
    BOTH columns (NOT_CLONED is data, not an error) and is tested without
    forcing registry absence, matching what the live rows already exercise.
"""

import dataclasses
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import pytest

from ingest import audit, cli, eval_split, gap, io, licenses, recipes, sources

REAL_SIDECAR_PATH = io.REPO_ROOT / "training/assemble/out/corpus_p25_sidecar.jsonl"


def _nonexistent_recipes_path(tmp_path: Path) -> Path:
    return tmp_path / "no_such_clone" / "cookbook" / "recipes.yml"


def _all_clones_absent_registry() -> tuple:
    """A copy of the REAL 21-row registry with every clone_path redirected to
    a location guaranteed not to exist, simulating a checkout with no
    ~/projects/repos/ at all -- the scenario §7.5's 'cookbook clone absent'
    column describes for licenses.py's two registry-driven commands."""
    real_rows = sources.load_registry()
    return tuple(
        dataclasses.replace(
            row, clone_path=f"~/projects/repos/__does_not_exist__/{row.source_id}"
        )
        for row in real_rows
    )


def _patch_cookbook_absent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(recipes, "default_recipes_path", lambda: _nonexistent_recipes_path(tmp_path))


def _patch_registry_all_absent(monkeypatch) -> None:
    fake_registry = _all_clones_absent_registry()
    monkeypatch.setattr(licenses, "load_registry", lambda: fake_registry)


def _run_licenses_cli(monkeypatch, argv: list[str]) -> int:
    monkeypatch.setattr("sys.argv", ["python -m ingest.licenses", *argv])
    return licenses.main()


def _run_via_cli_run(handler, parser, argv: list[str]) -> int:
    return cli.run(handler, parser, argv)


# ============================================================================
# The 19 cases
# ============================================================================


@dataclasses.dataclass(frozen=True)
class Case:
    id: str
    expected: int
    run: Callable[[object, Path], int]


def _case_licenses_report(monkeypatch, tmp_path: Path) -> int:
    out = tmp_path / "out"
    return _run_licenses_cli(monkeypatch, ["--report", "--out", str(out)])


def _case_licenses_check_descend(monkeypatch, tmp_path: Path) -> int:
    _patch_registry_all_absent(monkeypatch)
    return _run_licenses_cli(monkeypatch, ["--check-descend"])


def _case_licenses_verify_clones(monkeypatch, tmp_path: Path) -> int:
    _patch_registry_all_absent(monkeypatch)
    return _run_licenses_cli(monkeypatch, ["--verify-clones"])


def _case_recipes_emit_histogram(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    out = tmp_path / "out"
    return _run_via_cli_run(recipes._dispatch_handler, recipes._make_parser(),
                             ["--emit-histogram", "--out", str(out)])


def _case_recipes_emit_receiver_alias_keys(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    out = tmp_path / "out"
    return _run_via_cli_run(recipes._dispatch_handler, recipes._make_parser(),
                             ["--emit-receiver-alias-keys", "--out", str(out)])


def _case_audit_report(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    out = tmp_path / "out"
    return _run_via_cli_run(audit._dispatch_handler, audit._make_parser(),
                             ["--report", "--out", str(out)])


def _case_audit_gate(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    return _run_via_cli_run(audit._dispatch_handler, audit._make_parser(), ["--gate"])


def _case_audit_emit_census(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    out = tmp_path / "out"
    return _run_via_cli_run(audit._dispatch_handler, audit._make_parser(),
                             ["--emit-census", "--out", str(out)])


def _case_audit_emit_fingerprint(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    out = tmp_path / "out"
    return _run_via_cli_run(audit._dispatch_handler, audit._make_parser(),
                             ["--emit-fingerprint", "--out", str(out)])


def _case_gap_gate(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    return gap.gate(out_dir=tmp_path / "out")


def _case_eval_split_check_leak(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    return _run_via_cli_run(eval_split._dispatch_handler, eval_split._make_parser(),
                             ["--check-leak", str(REAL_SIDECAR_PATH)])


def _case_eval_split_emit(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    out = tmp_path / "out"
    return _run_via_cli_run(eval_split._dispatch_handler, eval_split._make_parser(),
                             ["--emit", "--out", str(out)])


def _case_eval_split_emit_lineage_contract(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    out = tmp_path / "out"
    return _run_via_cli_run(eval_split._dispatch_handler, eval_split._make_parser(),
                             ["--emit-lineage-contract", "--out", str(out)])


# --- The six --out-omitted cases (64 in both columns; clone check never runs) ---


def _case_recipes_emit_histogram_no_out(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    return _run_via_cli_run(recipes._dispatch_handler, recipes._make_parser(),
                             ["--emit-histogram"])


def _case_recipes_emit_receiver_alias_keys_no_out(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    return _run_via_cli_run(recipes._dispatch_handler, recipes._make_parser(),
                             ["--emit-receiver-alias-keys"])


def _case_audit_emit_census_no_out(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    return _run_via_cli_run(audit._dispatch_handler, audit._make_parser(),
                             ["--emit-census"])


def _case_audit_emit_fingerprint_no_out(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    return _run_via_cli_run(audit._dispatch_handler, audit._make_parser(),
                             ["--emit-fingerprint"])


def _case_eval_split_emit_no_out(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    return _run_via_cli_run(eval_split._dispatch_handler, eval_split._make_parser(),
                             ["--emit"])


def _case_eval_split_emit_lineage_contract_no_out(monkeypatch, tmp_path: Path) -> int:
    _patch_cookbook_absent(monkeypatch, tmp_path)
    return _run_via_cli_run(eval_split._dispatch_handler, eval_split._make_parser(),
                             ["--emit-lineage-contract"])


CASES = [
    Case("licenses --report --out <dir>", cli.EXIT_OK, _case_licenses_report),
    Case("licenses --check-descend", cli.EXIT_INCONCLUSIVE, _case_licenses_check_descend),
    Case("licenses --verify-clones", cli.EXIT_INCONCLUSIVE, _case_licenses_verify_clones),
    Case("recipes --emit-histogram --out <dir>", cli.EXIT_INCONCLUSIVE, _case_recipes_emit_histogram),
    Case("recipes --emit-receiver-alias-keys --out <dir>", cli.EXIT_INCONCLUSIVE, _case_recipes_emit_receiver_alias_keys),
    Case("audit --report --out <dir>", cli.EXIT_INCONCLUSIVE, _case_audit_report),
    Case("audit --gate", cli.EXIT_INCONCLUSIVE, _case_audit_gate),
    Case("audit --emit-census --out <dir>", cli.EXIT_INCONCLUSIVE, _case_audit_emit_census),
    Case("audit --emit-fingerprint --out <dir>", cli.EXIT_OK, _case_audit_emit_fingerprint),
    Case("gap --gate", cli.EXIT_INCONCLUSIVE, _case_gap_gate),
    Case("eval_split --check-leak <committed sidecar>", cli.EXIT_OK, _case_eval_split_check_leak),
    Case("eval_split --emit --out <dir>", cli.EXIT_INCONCLUSIVE, _case_eval_split_emit),
    Case("eval_split --emit-lineage-contract --out <dir>", cli.EXIT_OK, _case_eval_split_emit_lineage_contract),
    Case("recipes --emit-histogram [no --out]", cli.EXIT_USAGE, _case_recipes_emit_histogram_no_out),
    Case("recipes --emit-receiver-alias-keys [no --out]", cli.EXIT_USAGE, _case_recipes_emit_receiver_alias_keys_no_out),
    Case("audit --emit-census [no --out]", cli.EXIT_USAGE, _case_audit_emit_census_no_out),
    Case("audit --emit-fingerprint [no --out]", cli.EXIT_USAGE, _case_audit_emit_fingerprint_no_out),
    Case("eval_split --emit [no --out]", cli.EXIT_USAGE, _case_eval_split_emit_no_out),
    Case("eval_split --emit-lineage-contract [no --out]", cli.EXIT_USAGE, _case_eval_split_emit_lineage_contract_no_out),
]


def test_exactly_19_cases():
    """13 command rows x 1 + 6 --out-omitted cases = 19. A row added to §7.5
    without a corresponding case fails loudly (rev 8, C4)."""
    assert len(CASES) == 19


class TestOfflineBehaviourTable:
    @pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
    def test_case_exits_expected_code(self, case: Case, monkeypatch, tmp_path):
        actual = case.run(monkeypatch, tmp_path)
        assert actual == case.expected, (
            f"{case.id}: expected exit {case.expected}, got {actual}"
        )
