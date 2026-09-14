"""AC-2 / NFR-2 import boundary: nothing under coxswain/src may import
praxis.* (the backend is reimplemented dependency-free here, per the ADR), and
no module has a module-level `import js` (NFR-1 CPython importability).
"""

import ast
import subprocess
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "coxswain"


def _iter_imports(tree: ast.AST):
    """Yield (node, top_level_module) for every absolute import."""
    if isinstance(tree, ast.Import):
        for alias in tree.names:
            yield tree, alias.name.split(".")[0]
    elif isinstance(tree, ast.ImportFrom):
        if tree.level == 0 and tree.module:
            yield tree, tree.module.split(".")[0]


def test_no_praxis_imports_under_src() -> None:
    offenders: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            for import_node, top in _iter_imports(node):
                if top == "praxis":
                    offenders.append(f"{path}: {ast.unparse(import_node)}")
    assert offenders == [], f"NFR-2 violated: {offenders}"


def test_no_module_level_js_import_under_src() -> None:
    """NFR-1: no module-level `import js`. Browser bindings are injected or
    lazily imported inside functions; only module-body statements are checked
    so a lazy import inside a function remains legal."""
    offenders: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for stmt in tree.body:  # module level only
            for node, top in _iter_imports(stmt):
                if top == "js":
                    offenders.append(f"{path}: {ast.unparse(stmt)}")
    assert offenders == [], f"NFR-1 violated by module-level js import: {offenders}"


def test_plain_cpython_import_of_w1_modules() -> None:
    """AC-1a: the modules W1 creates import cleanly in plain CPython."""
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import coxswain.records, coxswain.ids, coxswain.schema.types",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"stderr:\n{proc.stderr}"
