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
SPEC_INCREMENT_9 = REPO_ROOT / ".praxia" / "docs" / "specs" / "260929_plr-sema-plr1-tip-effect-increment.md"
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
# version pins (260930): a citation resolves against the commit it was written at
# --------------------------------------------------------------------------


def _git(root: Path, *args: str) -> str:
    import subprocess

    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def pinned_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """A git repo whose `pkg/mod.py` defines `foo` at line 2 in commit `v1` and,
    after two lines are inserted above it, at line 4 in commit `v2`."""
    _git(tmp_path, "init", "-q")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("# header\ndef foo():\n    return 1\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "v1")
    v1 = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "pkg" / "mod.py").write_text("# header\n# new 1\n# new 2\ndef foo():\n    return 1\n")
    _git(tmp_path, "commit", "-q", "-am", "v2")
    v2 = _git(tmp_path, "rev-parse", "HEAD")
    return tmp_path, v1, v2


def _failing(root: Path, text: str) -> list:
    spec = root / "spec.md"
    spec.write_text(textwrap.dedent(text))
    return [v for v in citations.check(spec, root) if not v.informational]


def test_pin_frontmatter_resolves_at_the_pinned_commit(pinned_repo) -> None:
    root, v1, _v2 = pinned_repo
    line = "The helper `foo` (`pkg/mod.py:2-3`) returns one.\n"
    assert _failing(root, line), "control: unpinned, the drifted citation must fail against today's tree"
    assert _failing(root, f"---\ncitations_at: {v1}\n---\n{line}") == []


def test_pin_marker_repins_following_lines_only(pinned_repo) -> None:
    root, v1, v2 = pinned_repo
    doc = (
        f"---\ncitations_at: {v1}\n---\n"
        "Old text: `foo` (`pkg/mod.py:2-3`).\n"
        f"<!-- citations-at: {v2} -->\n"
        "Amendment: `foo` (`pkg/mod.py:4-5`).\n"
    )
    assert _failing(root, doc) == []
    # the old citation placed AFTER the marker is resolved at v2 and must fail there
    wrong = doc + "Misplaced old text: `foo` (`pkg/mod.py:2-3`).\n"
    failing = _failing(root, wrong)
    assert [(v.kind, v.rev) for v in failing] == [("symbol_not_in_range", v2)], failing


def test_pin_live_marker_returns_to_todays_tree(pinned_repo) -> None:
    root, v1, _v2 = pinned_repo
    doc = f"---\ncitations_at: {v1}\n---\n<!-- citations-at: live -->\nNow: `foo` (`pkg/mod.py:4-5`).\n"
    assert _failing(root, doc) == []


def test_pin_list_resolves_each_file_at_the_first_rev_that_has_it(pinned_repo) -> None:
    """An ordered pin `<v1> <v2>`: `pkg/mod.py` exists at both, so it is checked
    at v1 (the old citation passes, the new one fails); `report.json`, added only
    in a later commit, resolves at that commit."""
    root, v1, _v2 = pinned_repo
    (root / "out").mkdir()
    (root / "out" / "report.json").write_text('{\n  "n_ops": 548\n}\n')
    _git(root, "add", "out/report.json")
    _git(root, "commit", "-q", "-m", "artifact")
    v3 = _git(root, "rev-parse", "HEAD")
    (root / "out" / "report.json").unlink()  # gone from the working tree, like an untracked report
    ok = f"---\ncitations_at: {v1} {v3}\n---\n`foo` (`pkg/mod.py:2-3`) and `n_ops` (`out/report.json:2`).\n"
    assert _failing(root, ok) == []
    order = f"---\ncitations_at: {v1} {v3}\n---\n`foo` (`pkg/mod.py:4-5`).\n"
    assert [v.rev for v in _failing(root, order)] == [v1], "a file at both revs is checked at the FIRST"


def test_pin_to_an_unknown_rev_is_an_error_not_a_pass(pinned_repo) -> None:
    import subprocess

    root, _v1, _v2 = pinned_repo
    with pytest.raises(subprocess.CalledProcessError):
        _failing(root, "---\ncitations_at: 0123456789abcdef0123456789abcdef01234567\n---\n`foo` (`pkg/mod.py:2`)\n")


def test_line_pins_default_live_and_marker_order() -> None:
    doc = "---\ntitle: x\n---\na\n<!-- citations-at: abc123 -->\nb\n<!-- citations-at: live -->\nc\n"
    pins = citations.line_pins(doc)
    lines = doc.splitlines()
    assert pins[lines.index("a")] == "live"
    assert pins[lines.index("b")] == "abc123"
    assert pins[lines.index("c")] == "live"


def test_inline_pin_applies_to_its_own_line_only() -> None:
    doc = "---\ncitations_at: base1\n---\n| row a |\n| row b | <!-- citations-at: def456 -->\n| row c |\n"
    pins = citations.line_pins(doc)
    lines = doc.splitlines()
    assert pins[lines.index("| row a |")] == "base1"
    assert pins[lines.index("| row b | <!-- citations-at: def456 -->")] == "def456"
    assert pins[lines.index("| row c |")] == "base1"


def test_inline_pin_resolves_the_line_at_its_rev(pinned_repo) -> None:
    root, v1, v2 = pinned_repo
    doc = (
        f"---\ncitations_at: {v1}\n---\n"
        "| old | `foo` (`pkg/mod.py:2-3`) |\n"
        f"| edited | `foo` (`pkg/mod.py:4-5`) | <!-- citations-at: {v2} -->\n"
        "| old again | `foo` (`pkg/mod.py:2-3`) |\n"
    )
    assert _failing(root, doc) == []


#: A commit on main whose recorded `external/pylabrobot` gitlink is the OLD pin
#: (dd79c4c89, PyLabRobot 0.2.2): the parent of the 1.0.0b1 bump.
PRE_BUMP_REV = "6b1e5121^"


def test_pinned_tree_reads_the_submodule_at_the_recorded_gitlink() -> None:
    """At a pre-bump commit, `liquid_handling/liquid_handler.py` exists (PLR 0.2.2
    layout) and `legacy/liquid_handling/liquid_handler.py` does not; today it is
    the other way round. This is what makes one sha pin both trees."""
    import subprocess

    try:
        tree = citations.GitTree(REPO_ROOT, PRE_BUMP_REV)
    except subprocess.CalledProcessError as e:  # shallow clone / uninitialised submodule
        pytest.skip(f"history not available here: {e.stderr}")
    old = "external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py"
    new = "external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py"
    paths = set(tree.paths())
    assert old in paths and new not in paths
    assert "def pick_up_tips" in tree.read(old)
    live = set(citations.LiveTree(REPO_ROOT).paths())
    assert new in live and old not in live


#: Specs whose citations are pinned: everything written against an older tree.
#: A spec still being written may stay `live` (increment 9, today).
PINNED_SPECS = [
    SPEC, SPEC_INCREMENT_1, SPEC_INCREMENT_2, SPEC_INCREMENT_3, SPEC_INCREMENT_4,
    SPEC_INCREMENT_5, SPEC_INCREMENT_6, SPEC_INCREMENT_7, SPEC_INCREMENT_8,
]


@pytest.mark.parametrize("spec_path", [pytest.param(p, id=p.stem) for p in PINNED_SPECS])
def test_historical_specs_declare_valid_pins(spec_path: Path) -> None:
    """Version pinning is TRACKED, not optional: every historical spec declares a
    frontmatter pin, and every pin it uses is a real commit that is an ancestor
    of HEAD (a pin to a commit that never landed would check nothing real)."""
    import subprocess

    if not spec_path.is_file():
        pytest.skip(f"spec not present: {spec_path}")
    pins = citations.declared_pins(spec_path)
    assert pins and pins[0] != citations.LIVE, f"{spec_path.name}: no frontmatter `citations_at`"
    for rev in citations.declared_revs(spec_path):
        if rev == citations.LIVE:
            continue
        sha = _git(REPO_ROOT, "rev-parse", "--verify", f"{rev}^{{commit}}")
        ancestor = subprocess.run(["git", "-C", str(REPO_ROOT), "merge-base", "--is-ancestor", sha, "HEAD"])
        assert ancestor.returncode == 0, f"{spec_path.name}: pin {rev} is not an ancestor of HEAD"


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
        pytest.param(SPEC_INCREMENT_9, id="increment-9-plr1-tip-effects"),
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
        pytest.param(SPEC_INCREMENT_9, id="increment-9-plr1-tip-effects"),
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
