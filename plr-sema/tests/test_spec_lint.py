"""Tests for the two round-6 mechanical checkers (``scripts/check_spec_citations.py``,
``scripts/check_spec_crossrefs.py``) and the enforcement that the live spec
passes both.

Two layers, deliberately:

* **Synthetic fixtures** prove every violation kind still *fires*. A lint that
  goes quiet after its heuristics are tuned is indistinguishable from a lint
  that passes -- so each kind gets a fixture that must trip it.
* **The live spec** must produce zero failing violations. This is the
  round-6 recommendation made enforceable: stale line citations and AC/HM
  bookkeeping drift fail the suite instead of waiting for a review round.

The checkers are loaded by path (``importlib``), not imported: ``scripts/``
is not a package, and pulling it under ``src/`` would put document-lint
code inside the analyzer's import boundary for no reason.
"""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PKG_ROOT.parent
SCRIPTS = PKG_ROOT / "scripts"
SPEC = REPO_ROOT / ".praxia" / "docs" / "specs" / "260901_plr-sema-pre-corpus-spec.md"
SPEC_INCREMENT_1 = REPO_ROOT / ".praxia" / "docs" / "specs" / "260902_plr-sema-tip-typestate-increment.md"
SPEC_INCREMENT_2 = REPO_ROOT / ".praxia" / "docs" / "specs" / "260902_plr-sema-ir-bytecode-increment.md"
SPEC_INCREMENT_3 = REPO_ROOT / ".praxia" / "docs" / "specs" / "260903_plr-sema-real-programs-increment.md"
SPEC_INCREMENT_4 = REPO_ROOT / ".praxia" / "docs" / "specs" / "260903_plr-sema-families-cache-increment.md"
SPEC_INCREMENT_5 = REPO_ROOT / ".praxia" / "docs" / "specs" / "260903_plr-sema-volume-increment.md"
SPEC_INCREMENT_6 = REPO_ROOT / ".praxia" / "docs" / "specs" / "260904_plr-sema-predicate-increment.md"
SPEC_INCREMENT_7 = REPO_ROOT / ".praxia" / "docs" / "specs" / "260909_plr-sema-observation-increment.md"
SPEC_INCREMENT_8 = REPO_ROOT / ".praxia" / "docs" / "specs" / "260909_plr-sema-move-family-increment.md"
REGISTRY = PKG_ROOT / "src" / "plr_sema" / "_hand_maintained.py"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod  # dataclasses resolve string annotations via sys.modules
    spec.loader.exec_module(mod)
    return mod


citations = _load("check_spec_citations")
crossrefs = _load("check_spec_crossrefs")


# --------------------------------------------------------------------------
# citation-anchor validator
# --------------------------------------------------------------------------


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text(
        "\n".join(["# 1", "# 2", "# 3", "# 4", "def foo():", "    return 1", "", "def bar():", "    return 2"] + ["# pad"] * 11) + "\n"
    )
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "dup.py").write_text("x = 1\n")
    (tmp_path / "b" / "dup.py").write_text("x = 2\n")
    return tmp_path


def _cit_kinds(root: Path, text: str) -> dict[str, list[str]]:
    spec = root / "spec.md"
    spec.write_text(textwrap.dedent(text))
    out: dict[str, list[str]] = {}
    for v in citations.check(spec, root):
        out.setdefault(v.kind, []).append(v.citation)
    return out


def test_clean_citation_passes_bounds_and_symbol(fake_repo: Path) -> None:
    kinds = _cit_kinds(fake_repo, "The helper `foo` (`pkg/mod.py:5-6`) returns one.\n")
    assert kinds == {}


def test_out_of_range_fires(fake_repo: Path) -> None:
    kinds = _cit_kinds(fake_repo, "see `pkg/mod.py:99`\n")
    assert list(kinds) == ["out_of_range"]


def test_symbol_not_in_range_fires(fake_repo: Path) -> None:
    # `foo` is at line 5; citing lines 8-9 (bar) with `foo` co-named must trip
    kinds = _cit_kinds(fake_repo, "The helper `foo` (`pkg/mod.py:8-9`) returns one.\n")
    assert list(kinds) == ["symbol_not_in_range"]


def test_qualname_passes_when_def_encloses_cited_line(fake_repo: Path) -> None:
    # line 6 is `return 1` inside foo(); citing it by the qualname must pass
    kinds = _cit_kinds(fake_repo, "the raise in `Mod.foo` (`pkg/mod.py:6`) fires\n")
    assert kinds == {}
    # ...but a def that does NOT enclose the line still trips
    kinds = _cit_kinds(fake_repo, "the raise in `Mod.foo` (`pkg/mod.py:9`) fires\n")
    assert list(kinds) == ["symbol_not_in_range"]


def test_symbol_from_following_clause_is_not_charged(fake_repo: Path) -> None:
    # `bar` appears AFTER the citation, in the next clause: not a co-name
    kinds = _cit_kinds(fake_repo, "`foo` lives at `pkg/mod.py:5`, and `bar` elsewhere.\n")
    assert kinds == {}


def test_filename_tokens_are_not_identifiers(fake_repo: Path) -> None:
    kinds = _cit_kinds(fake_repo, "`mod.py` is short (`pkg/mod.py:1-2`).\n")
    assert kinds == {}


def test_multi_range_citation_searches_every_range(fake_repo: Path) -> None:
    kinds = _cit_kinds(fake_repo, "`bar` is defined (`pkg/mod.py:1-2,8-9`).\n")
    assert kinds == {}


def test_unresolved_and_ambiguous_fire(fake_repo: Path) -> None:
    kinds = _cit_kinds(fake_repo, "see `nope.py:1` and `dup.py:1`\n")
    assert set(kinds) == {"unresolved", "ambiguous"}


def test_bare_basename_resolves_when_unique(fake_repo: Path) -> None:
    kinds = _cit_kinds(fake_repo, "`foo` (`mod.py:5`)\n")
    assert kinds == {}


def test_unanchored_is_informational_only(fake_repo: Path) -> None:
    spec = fake_repo / "spec.md"
    spec.write_text("earlier file, then `:12`\n")
    vs = citations.check(spec, fake_repo)
    assert [v.kind for v in vs] == ["unanchored"] and all(v.informational for v in vs)


# --------------------------------------------------------------------------
# AC / HM cross-reference lint
# --------------------------------------------------------------------------

_REGISTRY_SRC = '''
BUDGET_CAP = 4
ROWS = [
    HandMaintainedSurface(id="HM-1", what="w", metric="m", declared=3, status="CAPPED", why_not_derived="x", breaks_when="y"),
    HandMaintainedSurface(id="HM-2", what="w", metric="m", declared=1, status="FROZEN", why_not_derived="x", breaks_when="y"),
]
'''

_SPEC_SRC = """
- **AC-1.1** first
- **AC-1.2** second
- **AC-1.3** third, gated nowhere
- **AC-2.1 (qualified)** fourth

| task | scope | files | gate | ~LOC | depends on |
|---|---|---|---|---|---|
| **T1** | s | f | `uv run pytest x` + AC-1.1–1.2 + AC-9.9 | ~1 | — |
| **T2** | s | f | AC-1.2 | ~1 | — |
| **T3** | s | f | AC-2.1 | ~1 | — |

### 9.2 Inventory (baseline)

| id | surface | metric | baseline | status | trigger |
|---|---|---|---|---|---|
| HM-1 | a | m | **2** | CAPPED (3) | none |
| HM-2 | b | m | **2** | FROZEN | none |
| HM-3 | c | m | **1** | FROZEN | none |

### 9.3 next

### 9.4 Budget

**Total budget: 5 registry rows** (HM-1 and HM-2).
"""


def test_crossref_lint_fires_every_kind(tmp_path: Path) -> None:
    reg = tmp_path / "reg.py"
    reg.write_text(_REGISTRY_SRC)
    spec = tmp_path / "spec.md"
    spec.write_text(_SPEC_SRC)
    vs = crossrefs.check(spec, reg)
    by_kind = {}
    for v in vs:
        by_kind.setdefault(v.kind, set()).add(v.subject)
    assert by_kind["ac_ungated"] == {"AC-1.3"}
    assert by_kind["ac_multiply_gated"] == {"AC-1.2"}
    assert by_kind["ac_undefined"] == {"AC-9.9"}
    assert by_kind["hm_not_in_registry"] == {"HM-3"}
    assert by_kind["hm_ceiling_mismatch"] == {"HM-2"}  # HM-1's CAPPED (3) matches declared=3
    assert by_kind["budget_cap_mismatch"] == {"BUDGET_CAP"}
    assert "hm_missing_from_inventory" not in by_kind
    assert "hm_status_mismatch" not in by_kind


def test_crossref_lint_reports_registry_row_missing_from_inventory(tmp_path: Path) -> None:
    reg = tmp_path / "reg.py"
    reg.write_text(_REGISTRY_SRC)
    spec = tmp_path / "spec.md"
    spec.write_text("### 9.2 Inventory\n\n| HM-1 | a | m | **3** | CAPPED (3) | n |\n\n### 9.3\n")
    kinds = {v.kind: v.subject for v in crossrefs.check(spec, reg)}
    assert kinds == {"hm_missing_from_inventory": "HM-2"}


# --------------------------------------------------------------------------
# the live spec must pass both
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "spec_path",
    [
        pytest.param(SPEC, id="main"),
        pytest.param(SPEC_INCREMENT_1, id="increment-1-tip-typestate"),
        pytest.param(SPEC_INCREMENT_2, id="increment-2-ir-bytecode"),
        pytest.param(SPEC_INCREMENT_3, id="increment-3-real-programs"),
        pytest.param(SPEC_INCREMENT_4, id="increment-4-families-cache"),
        pytest.param(SPEC_INCREMENT_5, id="increment-5-volume"),
        pytest.param(SPEC_INCREMENT_6, id="increment-6-predicates"),
        pytest.param(SPEC_INCREMENT_7, id="increment-7-observation"),
        pytest.param(SPEC_INCREMENT_8, id="increment-8-move-family"),
    ],
)
def test_live_spec_has_no_failing_citations(spec_path: Path) -> None:
    if not spec_path.is_file():
        pytest.skip(f"spec not present: {spec_path}")
    failing = [v for v in citations.check(spec_path, REPO_ROOT) if not v.informational]
    assert failing == [], "\n".join(f"{v.kind} L{v.spec_line} {v.citation} -- {v.detail}" for v in failing)


@pytest.mark.skipif(not SPEC.is_file(), reason="spec not present in this checkout")
def test_live_spec_ac_hm_crossrefs_reconcile() -> None:
    vs = crossrefs.check(SPEC, REGISTRY)
    assert vs == [], "\n".join(f"{v.kind} L{v.spec_line} {v.subject} -- {v.detail}" for v in vs)


@pytest.mark.parametrize(
    "spec_path",
    [
        pytest.param(SPEC_INCREMENT_1, id="increment-1-tip-typestate"),
        pytest.param(SPEC_INCREMENT_2, id="increment-2-ir-bytecode"),
        pytest.param(SPEC_INCREMENT_3, id="increment-3-real-programs"),
        pytest.param(SPEC_INCREMENT_4, id="increment-4-families-cache"),
        pytest.param(SPEC_INCREMENT_5, id="increment-5-volume"),
        pytest.param(SPEC_INCREMENT_6, id="increment-6-predicates"),
        pytest.param(SPEC_INCREMENT_7, id="increment-7-observation"),
        pytest.param(SPEC_INCREMENT_8, id="increment-8-move-family"),
    ],
)
def test_increment_specs_ac_gating_violations(spec_path: Path) -> None:
    """Increments have no §9.2 inventory table, but must not have AC gating violations."""
    if not spec_path.is_file():
        pytest.skip(f"spec not present: {spec_path}")
    all_vs = crossrefs.check(spec_path, REGISTRY)
    # Filter to only gating-related violations (not HM-related ones)
    gating_violations = [v for v in all_vs if v.kind in {"ac_ungated", "ac_undefined", "ac_multiply_gated"}]
    assert gating_violations == [], "\n".join(
        f"{v.kind} L{v.spec_line} {v.subject} -- {v.detail}" for v in gating_violations
    )
