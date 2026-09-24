"""AC-1 / Spec 260901 §1 import boundary: nothing under plr_sema/src may import
praxis.*, verify, or training. The package is corpus-independent and must remain
independent of the analyzer's training/verification harness.

T8 addition (spec §1.3/AC-6.2): `src/plr_sema/check/` additionally may not
import `pylabrobot` or `libcst` (§6's packaging fact -- `check/` is
browser-side and must run under Pyodide, where neither native extension nor
a PLR install is available). `test_no_pylabrobot_import_under_check` walks
that one subtree with the same `ast.walk` machinery `_iter_imports` already
provides.

Round-4 remediation (M6): AC-1.1 used to be satisfied by "`import plr_sema`
exits 0" alone -- true even when `plr_sema/__init__.py` exported nothing
(`__all__ = []`), which was the actual pre-round-4 state:
`plr_sema.check_graph` was unreachable from the top-level package despite
being the package's round-1 entry point. `test_plain_cpython_import_of_public_surface`
(named in spec §1.3, previously absent from this file -- a spec/test drift
this fix also closes) strengthens AC-1.1 to assert the three names the
package now re-exports are actually importable, in a fresh subprocess.
"""

import ast
import subprocess
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "plr_sema"
CHECK_ROOT = SRC_ROOT / "check"
PLR_SEMA_ROOT = SRC_ROOT.parent.parent


def _iter_imports(tree: ast.AST):
    """Yield (node, top_level_module) for every absolute import."""
    if isinstance(tree, ast.Import):
        for alias in tree.names:
            yield tree, alias.name.split(".")[0]
    elif isinstance(tree, ast.ImportFrom):
        if tree.level == 0 and tree.module:
            yield tree, tree.module.split(".")[0]


def test_no_praxis_imports_under_src() -> None:
    """Spec 260901 §1.3 AC-1.2: no import whose top-level module is praxis."""
    offenders: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            for import_node, top in _iter_imports(node):
                if top == "praxis":
                    offenders.append(f"{path}: {ast.unparse(import_node)}")
    assert offenders == [], f"Spec violation: {offenders}"


def test_no_verify_or_training_imports_under_src() -> None:
    """Spec 260901 §1.3: no import of verify or training modules.
    The package must not reach into the training harness."""
    offenders: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            for import_node, top in _iter_imports(node):
                if top in ("verify", "training"):
                    offenders.append(f"{path}: {ast.unparse(import_node)}")
    assert offenders == [], f"Spec violation: {offenders}"


def test_no_pylabrobot_import_under_check() -> None:
    """Spec §1.3/AC-6.2: `src/plr_sema/check/` may import neither `pylabrobot`
    nor `libcst` -- §6's packaging fact (native-extension `libcst` and a PLR
    install are both unavailable under Pyodide; importing PLR to check a
    protocol would also defeat the point of a pre-environment static
    analyzer). Restricted to the `check/` subtree only -- `derive/` and
    `extract/` (round 2) are not constrained by this test."""
    offenders: list[str] = []
    for path in sorted(CHECK_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            for import_node, top in _iter_imports(node):
                if top in ("pylabrobot", "libcst"):
                    offenders.append(f"{path}: {ast.unparse(import_node)}")
    assert offenders == [], f"Spec violation: {offenders}"


def test_plain_cpython_import_of_public_surface() -> None:
    """Spec §1.3/AC-1.1 (round-4 remediation, M6): a fresh subprocess
    `import plr_sema` must expose `check_graph`, `AnalysisReport`, and
    `Verdict` as top-level attributes, not merely exit 0. A bare "exits 0"
    assertion is satisfiable by an empty `__all__` -- exactly the pre-round-4
    state, in which `plr_sema.check_graph` was unreachable despite being the
    package's round-1 entry point (spec §6.2)."""
    src_path = str(PLR_SEMA_ROOT / "src")
    preamble = (
        "import plr_sema; "
        "assert callable(plr_sema.check_graph); "
        "assert plr_sema.AnalysisReport is not None; "
        "assert plr_sema.Verdict is not None"
    )
    result = subprocess.run(
        [sys.executable, "-c", preamble],
        cwd=str(PLR_SEMA_ROOT),
        env={"PYTHONPATH": src_path, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"import plr_sema (public surface) failed:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
