"""Shared utilities for scripts/survey_plr_*.py.

Every PLR survey needs the same three things, factored out here so they
don't drift into three slightly-different copies:

1. Which files count as real PLR source (PLR's own test-file naming has no
   single convention -- STARtests.py, backend_tests.py, test_foo.py all
   coexist; a first version of the exception survey missed this and let
   pytest-only mock classes pollute a real hierarchy).
2. A version stamp for whatever's actually being scanned (git SHA of the
   vendored submodule + pylabrobot.__version__ if importable) -- so a
   survey's JSON output records EXACTLY what it ran against. This is the
   load-bearing piece for running surveys across library versions: diff two
   stamped snapshots and the version stamp is what tells you what changed
   between them, not just that something did.
3. The class-collection pass (name/module/file/lineno/bases/docstring) and
   the exception-hierarchy fixpoint closure, needed by any survey that
   cares whether a given class IS an exception (not just named like one).
"""

from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLR_ROOT = PROJECT_ROOT / "external" / "pylabrobot" / "pylabrobot"
DEFAULT_PLR_SUBMODULE = PROJECT_ROOT / "external" / "pylabrobot"

_ROOT_EXCEPTION_NAMES = {"Exception", "BaseException"}


def is_source_file(path: Path) -> bool:
    """False for PLR's own test files. Matched on filename STEM SUFFIX, not
    a single fixed pattern -- PLR mixes STARtests.py, backend_tests.py, and
    test_foo.py with no one convention.
    """
    stem = path.stem
    return not (stem.endswith("test") or stem.endswith("tests") or stem.startswith("test_"))


def iter_source_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if is_source_file(p))


def module_name(file: Path, root: Path) -> str:
    rel = file.relative_to(root.parent)
    return ".".join(rel.with_suffix("").parts)


def relative_to_project_or_absolute(path: Path) -> str:
    """``path`` relative to ``PROJECT_ROOT`` when possible, else absolute.

    260901 T13 (backlog #4859): a survey can target a PLR tree materialized
    OUTSIDE this repo -- e.g. an upstream snapshot extracted to a tmpdir via
    ``git archive <sha> | tar -x`` for the surface-parameterization work --
    and a caller can likewise point ``--out`` anywhere. ``Path.relative_to``
    raises ``ValueError`` for any path that is not actually inside
    ``PROJECT_ROOT``; every prior call site assumed both ``--plr-root`` and
    ``--out`` were always repo-relative and called ``.relative_to(
    PROJECT_ROOT)`` unconditionally, which crashed for either argument
    (measured 260901: ``--out`` outside the repo raised this ValueError
    *after* the file had already been written -- the write itself has no
    such assumption, only the human-readable path formatting after it did).
    """
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def plr_version_stamp(submodule_root: Path = DEFAULT_PLR_SUBMODULE) -> dict[str, str | bool | None]:
    """Git SHA + dirty flag of the vendored submodule, and pylabrobot's own
    __version__ if the installed package is importable (may differ from the
    submodule checkout if the venv has a different pin -- both are recorded
    rather than assumed to agree).
    """
    stamp: dict[str, str | bool | None] = {"git_sha": None, "git_dirty": None, "pylabrobot_version": None}
    try:
        sha = subprocess.run(
            ["git", "-C", str(submodule_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
        stamp["git_sha"] = sha
        dirty = subprocess.run(
            ["git", "-C", str(submodule_root), "status", "--porcelain"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
        stamp["git_dirty"] = bool(dirty)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    try:
        import pylabrobot
        stamp["pylabrobot_version"] = getattr(pylabrobot, "__version__", None)
    except ImportError:
        pass
    return stamp


@dataclass
class ClassInfo:
    name: str
    module: str
    file: str
    lineno: int
    bases: list[str]
    docstring: str | None


def parse_files(files: list[Path]) -> dict[str, ast.Module]:
    """Parse once; callers needing raw nodes for deeper per-method work
    (precondition guards, deprecation markers, ...) walk this same dict
    themselves rather than re-parsing from disk a second time.
    """
    parsed: dict[str, ast.Module] = {}
    for f in files:
        try:
            source = f.read_text(encoding="utf-8")
            parsed[str(f)] = ast.parse(source, filename=str(f))
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"skip {f}: {e}")
    return parsed


class _ClassCollector(ast.NodeVisitor):
    def __init__(self, module: str, rel_file: str):
        self.module = module
        self.rel_file = rel_file
        self.classes: dict[str, ClassInfo] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = [ast.unparse(b) for b in node.bases]
        doc = ast.get_docstring(node)
        self.classes[node.name] = ClassInfo(
            name=node.name, module=self.module, file=self.rel_file, lineno=node.lineno,
            bases=bases, docstring=(doc.strip().splitlines()[0] if doc else None),
        )
        self.generic_visit(node)


def collect_all_classes(parsed: dict[str, ast.Module], plr_root: Path) -> dict[str, ClassInfo]:
    all_classes: dict[str, ClassInfo] = {}
    for file, tree in parsed.items():
        module = module_name(Path(file), plr_root)
        rel_file = str(Path(file).relative_to(PROJECT_ROOT))
        collector = _ClassCollector(module, rel_file)
        collector.visit(tree)
        for name, info in collector.classes.items():
            if name in all_classes:
                print(f"duplicate class name {name!r} in {all_classes[name].file} and {info.file} -- keeping first")
                continue
            all_classes[name] = info
    return all_classes


def exception_name_closure(classes: dict[str, ClassInfo]) -> frozenset[str]:
    """Fixpoint over the bases graph: a class is an exception if any base is
    a root sentinel or an already-known exception -- handles cross-file
    inheritance chains regardless of file processing order.
    """
    names = set(_ROOT_EXCEPTION_NAMES)
    changed = True
    while changed:
        changed = False
        for name, info in classes.items():
            if name in names:
                continue
            if any(base in names for base in info.bases):
                names.add(name)
                changed = True
    return frozenset(names)


def resolved_call_name(exc_node: ast.expr) -> str | None:
    """The class/function name a Call or bare Name expression resolves to,
    stripped of any module/attribute prefix (last segment only).
    """
    target = exc_node.func if isinstance(exc_node, ast.Call) else exc_node
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None
