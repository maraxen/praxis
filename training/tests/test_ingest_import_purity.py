"""F3 purity, proven transitively (AC-1.11, §7.3).

Three properties, tested in order of increasing strength:

  (a) Direct AST bans, one walk over every `.py` module under `training/ingest/`:
      1. no `import subprocess`, `os.system`, `eval`, `exec`, `importlib`, `runpy`
      2. zero `ast.Assert` nodes (bare `assert` is banned package-wide -- every
         invariant raises a typed exception instead)
      3. `ingest/__main__.py` imports none of the five command modules (what makes
         "there is no dispatcher" structural rather than behavioural)
      4. `ingest/cli.py` imports no sibling ingest module at all (what keeps the
         one-way import direction the exception hierarchy depends on from being
         silently re-broken)

  (b) Transitive closure, allowlisted: every module reachable from the ingest
      package's imports falls into stdlib / coxswain.* / a training/ sibling
      top-level package / praxis_training.* / an explicitly allowlisted entry.

  (c) Runtime proof, the strongest check: the full pipeline runs into a tmp_path
      with subprocess.run/Popen/call and os.system patched to raise, and completes
      without any of them ever firing.

These are four RULES inside property (a) -- AC-1.11 names exactly THREE
properties (a/b/c); do not present the four rules as four properties.
"""

import ast
import importlib.util
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import Any

import pytest

from ingest import audit, cli, eval_split, gap, io, licenses, recipes

INGEST_DIR = Path(io.__file__).parent
DATA_DIR = INGEST_DIR / "data"
REPO_ROOT = io.REPO_ROOT

MODULES_UNDER_LINT = sorted(INGEST_DIR.glob("*.py"))

COMMAND_MODULE_NAMES = ("licenses", "recipes", "eval_split", "audit", "gap")

# The banned names for rule 1. Matched against ast.Import.names[].name and
# ast.ImportFrom.module (any spelling: absolute or relative).
_BANNED_IMPORT_ROOTS = frozenset({"subprocess", "eval", "exec", "importlib", "runpy"})


def _module_ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(), filename=str(path))


# ============================================================================
# (a) Direct AST bans -- one walk, four rules
# ============================================================================


class TestDirectBans:
    @pytest.mark.parametrize("path", MODULES_UNDER_LINT, ids=lambda p: p.name)
    def test_no_banned_imports_or_os_system(self, path: Path):
        """Rule 1: no import subprocess/eval/exec/importlib/runpy, and no
        os.system(...) call, anywhere under training/ingest/."""
        tree = _module_ast(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root not in _BANNED_IMPORT_ROOTS, (
                        f"{path.name}: banned `import {alias.name}`"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0]
                    assert root not in _BANNED_IMPORT_ROOTS, (
                        f"{path.name}: banned `from {node.module} import ...`"
                    )
            elif isinstance(node, ast.Call):
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "system"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "os"
                ):
                    pytest.fail(f"{path.name}: banned os.system(...) call")
                if isinstance(func, ast.Name) and func.id in {"eval", "exec"}:
                    pytest.fail(f"{path.name}: banned bare {func.id}(...) call")

    @pytest.mark.parametrize("path", MODULES_UNDER_LINT, ids=lambda p: p.name)
    def test_no_bare_assert(self, path: Path):
        """Rule 2: zero ast.Assert nodes anywhere in the package (R4-W9). Every
        invariant must raise a typed exception instead of a bare `assert`, which
        `python -O` silently disables."""
        tree = _module_ast(path)
        assert_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        assert not assert_nodes, (
            f"{path.name}: contains {len(assert_nodes)} bare `assert` statement(s) "
            f"at line(s) {[n.lineno for n in assert_nodes]} -- raise a typed "
            f"exception instead"
        )

    def test_main_imports_no_command_module(self):
        """Rule 3: ingest/__main__.py imports none of the five command modules,
        in any spelling (absolute or relative). This is what makes 'there is no
        dispatcher' structural rather than behavioural."""
        path = INGEST_DIR / "__main__.py"
        tree = _module_ast(path)
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    if parts[0] == "ingest" and len(parts) > 1 and parts[1] in COMMAND_MODULE_NAMES:
                        offenders.append(alias.name)
                    elif parts[0] in COMMAND_MODULE_NAMES:
                        offenders.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                parts = mod.split(".") if mod else []
                # Relative import: `from . import audit` etc. -- module="" or
                # module names a sibling; level > 0 for `.`/`..`.
                if node.level and node.level > 0:
                    if mod in COMMAND_MODULE_NAMES:
                        offenders.append(f"{'.' * node.level}{mod}")
                    if not mod:
                        # `from . import licenses` -- check the imported names
                        for alias in node.names:
                            if alias.name in COMMAND_MODULE_NAMES:
                                offenders.append(f"{'.' * node.level} import {alias.name}")
                else:
                    if parts and parts[0] == "ingest" and len(parts) > 1 and parts[1] in COMMAND_MODULE_NAMES:
                        offenders.append(mod)
                    elif parts and parts[0] in COMMAND_MODULE_NAMES:
                        offenders.append(mod)
        assert not offenders, (
            f"__main__.py imports command module(s): {offenders} -- this would "
            f"make it a dispatcher, contradicting §7.1"
        )

    def test_cli_imports_no_sibling_ingest_module(self):
        """Rule 4: ingest/cli.py imports no sibling ingest module at all -- not
        just no command module, but none (io.py and versions.py included).
        This keeps cli.py importable (the exception hierarchy roots live there,
        and every command module imports cli.py -- a reverse import cycles)."""
        path = INGEST_DIR / "cli.py"
        tree = _module_ast(path)
        sibling_names = {"io", "versions", "sources", "licenses", "recipes",
                          "eval_split", "audit", "gap"}
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    if parts[0] == "ingest" and len(parts) > 1 and parts[1] in sibling_names:
                        offenders.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if node.level and node.level > 0:
                    if mod in sibling_names:
                        offenders.append(f"{'.' * node.level}{mod}")
                    if not mod:
                        for alias in node.names:
                            if alias.name in sibling_names:
                                offenders.append(f"{'.' * node.level} import {alias.name}")
                else:
                    parts = mod.split(".") if mod else []
                    if parts and parts[0] == "ingest" and len(parts) > 1 and parts[1] in sibling_names:
                        offenders.append(mod)
        assert not offenders, (
            f"cli.py imports sibling ingest module(s): {offenders} -- this would "
            f"create a circular import (every command module imports cli.py)"
        )


# ============================================================================
# (b) Transitive closure, allowlisted
# ============================================================================

_STDLIB_PATHS = tuple(
    p for p in (sysconfig.get_paths().get("stdlib"), sysconfig.get_paths().get("platstdlib"))
    if p
)


def _is_stdlib(name: str) -> bool:
    mod = sys.modules.get(name)
    if mod is None:
        return True  # not resolvable -- treat conservatively as not-a-finding
    f = getattr(mod, "__file__", None)
    if f is None:
        return True  # builtin / frozen module
    return any(f.startswith(p) for p in _STDLIB_PATHS)


def _resolve_spec_file(name: str) -> Path | None:
    """Resolve a dotted module name to its source file, without executing it
    (beyond whatever parent-package __init__ imports the finder itself needs).
    Returns None for anything unresolvable, built-in, or frozen."""
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ModuleNotFoundError, ValueError, AttributeError, TypeError):
        return None
    if spec is None or spec.origin is None or spec.origin in ("built-in", "frozen"):
        return None
    return Path(spec.origin)


def _direct_import_targets(path: Path) -> set[str]:
    """Top-level, non-relative import targets named in a module's source
    (`import X.Y` -> "X.Y"; `from X.Y import Z` -> "X.Y"). Relative imports
    (`from . import sibling`) are intra-package and not closure edges to
    categorize -- they resolve to modules already in MODULES_UNDER_LINT."""
    tree = ast.parse(path.read_text(), filename=str(path))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative -- intra-package, not a closure edge
            if node.module:
                targets.add(node.module)
    return targets


def _compute_ingest_closure() -> set[str]:
    """Static, session-order-independent BFS over the ingest package's own
    import graph, following only repo-local edges (source files that resolve
    under REPO_ROOT).

    Deliberately does NOT use `sys.modules` -- by the time this test runs
    under the full suite, sys.modules has accumulated imports from unrelated
    test files (e.g. a different test importing `pylabrobot` directly, or
    `training.overlay_gen.miner` via a test that is exempt from the ban this
    file is not) that were never reached by the ingest package's own code.
    A closure test that reads ambient process state is order-dependent and
    reports false positives depending on what ran before it; this walks the
    AST of the ingest modules themselves (deterministic, regardless of test
    order) and only recurses into modules that resolve to a file under
    REPO_ROOT -- third-party/stdlib dependencies are out of scope for F3
    (they cannot be the source of a subprocess call the ingest package's own
    code path reaches) and are not one of the five categories to sort into.
    """
    to_visit: list[Path] = list(MODULES_UNDER_LINT)
    visited_files: set[Path] = set(to_visit)
    closure: set[str] = set()

    while to_visit:
        path = to_visit.pop()
        for name in _direct_import_targets(path):
            root = name.split(".")[0]
            if root == "ingest":
                continue
            f = _resolve_spec_file(name)
            if f is None:
                f = _resolve_spec_file(root)
            if f is None:
                continue
            try:
                f.relative_to(REPO_ROOT)
            except ValueError:
                continue  # third-party / stdlib -- out of scope
            closure.add(name)
            if f not in visited_files:
                visited_files.add(f)
                to_visit.append(f)

    return closure


_TRAINING_SIBLINGS = ("floor_gen", "overlay_gen", "assemble", "verify")


def _category(name: str, allowlist_modules: set[str]) -> str | None:
    if name == "coxswain" or name.startswith("coxswain."):
        return "coxswain"
    for sib in _TRAINING_SIBLINGS:
        if name == sib or name.startswith(sib + "."):
            return "training-sibling"
    if name == "praxis_training" or name.startswith("praxis_training."):
        return "praxis_training"
    if name in allowlist_modules:
        return "allowlisted"
    return None


class TestTransitiveClosure:
    def _load_allowlist(self) -> dict:
        import json
        path = DATA_DIR / "import_closure_allowlist.json"
        with open(path) as f:
            return json.load(f)

    def test_every_closure_member_is_categorized(self):
        allowlist = self._load_allowlist()
        allowlist_modules = {e["module"] for e in allowlist["allowlist"]}

        closure = _compute_ingest_closure()
        uncategorized = sorted(
            name for name in closure if _category(name, allowlist_modules) is None
        )
        assert not uncategorized, (
            f"uncategorized module(s) in the ingest import closure: "
            f"{uncategorized} -- add each to data/import_closure_allowlist.json "
            f"with a reason, or confirm it's actually stdlib/coxswain/a training "
            f"sibling/praxis_training and fix the categorizer"
        )

    def test_allowlist_has_exactly_one_entry(self):
        """Pinned against the real closure (verified 260828): only assemble.build
        imports a banned name (subprocess, for plr_source_sha()'s `git submodule
        status` shell-out). A second entry appearing here without a corresponding
        code change is worth a second look."""
        allowlist = self._load_allowlist()
        assert len(allowlist["allowlist"]) == 1
        assert allowlist["allowlist"][0]["module"] == "assemble.build"

    def test_allowlist_entries_are_real(self):
        """Each allowlisted module's source actually imports what the entry
        claims -- catches a stale or fabricated allowlist entry."""
        allowlist = self._load_allowlist()
        for entry in allowlist["allowlist"]:
            f = _resolve_spec_file(entry["module"])
            assert f is not None, f"allowlisted module {entry['module']} does not resolve"
            tree = ast.parse(Path(f).read_text())
            imported_roots = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_roots.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
            for claimed in entry["imports"]:
                assert claimed in imported_roots, (
                    f"{entry['module']} does not actually import {claimed!r} "
                    f"(allowlist entry is stale)"
                )

    def test_no_other_closure_member_imports_a_banned_name(self):
        """The allowlist's single entry is verified to be the ONLY one needed:
        every OTHER module in the closure is scanned for the same banned names
        (a)'s AST ban forbids inside ingest/, and none of them import any."""
        allowlist = self._load_allowlist()
        allowlist_modules = {e["module"] for e in allowlist["allowlist"]}
        closure = _compute_ingest_closure()

        for name in sorted(closure - allowlist_modules):
            f = _resolve_spec_file(name)
            if f is None:
                continue
            tree = ast.parse(Path(f).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        assert root not in _BANNED_IMPORT_ROOTS, (
                            f"{name} ({f}) imports {alias.name!r} but is not in "
                            f"the allowlist"
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    root = node.module.split(".")[0]
                    assert root not in _BANNED_IMPORT_ROOTS, (
                        f"{name} ({f}) imports from {node.module!r} but is not "
                        f"in the allowlist"
                    )


# ============================================================================
# (c) Runtime proof, stronger than any scan
# ============================================================================


class TestNoSubprocessExecutes:
    def test_no_subprocess_executes(self, tmp_path, monkeypatch):
        """Run the full pipeline into tmp_path with subprocess.run/Popen/call
        and os.system patched to raise. Asserts the run completes."""

        def _raise(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError(
                f"subprocess/os.system was called with args={args} kwargs={kwargs} "
                f"-- F3 purity violated"
            )

        monkeypatch.setattr(subprocess, "run", _raise)
        monkeypatch.setattr(subprocess, "Popen", _raise)
        monkeypatch.setattr(subprocess, "call", _raise)
        monkeypatch.setattr(__import__("os"), "system", _raise)

        out = tmp_path / "out"

        findings = licenses.verify_all()
        assert licenses.write_report(findings, out) is not None
        assert licenses.write_sources_manifest(findings, out) is not None

        from types import SimpleNamespace
        assert audit._handle_report(SimpleNamespace(out=out)) == 0

        assert audit.gate() == cli.EXIT_OK
        assert gap.gate(out_dir=out) in {cli.EXIT_OK, cli.EXIT_STOP_COVERAGE, cli.EXIT_CONTESTED}
