"""Which PLR source files make up the analyzed surface (260929, task
260929_plr-1.0-migration, workstream C).

Before PyLabRobot 1.0 the whole ``pylabrobot`` package WAS the legacy,
machine-agnostic ``LiquidHandler`` API, so every consumer walked it with a
plain ``rglob("*.py")``. From 1.0.0b1 (submodule pin ``786ac2c4e``) the tree
holds two APIs side by side: the legacy one under ``pylabrobot/legacy/`` and
the new vendor/device API (``hamilton/``, ``agilent/``, ``opentrons/``, ...),
plus shim packages at the old import paths that only ``import *`` from
``legacy``. The new API re-defines names the legacy one also defines
(``pick_up_tips``/``aspirate`` on driver feature classes, 109 duplicate class
names tree-wide), and the contract table is keyed on bare qualnames -- a
whole-tree walk would disambiguate, and so silently unreach, keys that praxis
programs name.

**The rule (user decision "option A", 260929: keep analysing the legacy
LiquidHandler).** When ``<root>/legacy/__init__.py`` exists, the ``legacy``
surface is the STATIC IMPORT CLOSURE of every source file under ``legacy/``:
exactly the modules the legacy API can execute, which is what praxis programs
(repointed to ``pylabrobot.legacy.*`` in 4772f264) actually call. Shared
modules the legacy code imports (``resources/``, ``lib/``, ``events/``,
``io/``, the parts of ``hamilton/star/`` the legacy STAR backend delegates to)
are in; new-API modules nothing legacy imports are out. When there is no
``legacy/`` package (every pre-1.0 tree, including the ``dd79c4c89`` pin and
the ``upstream_nonlegacy`` snapshot of ``3a50a567f``) the surface is the whole
tree, byte-for-byte the pre-260929 behaviour.

The closure over-approximates on purpose (a superset of the runtime import
graph is the sound direction for an analyzer that must not miss code the
legacy API can reach): every ``import``/``from ... import`` anywhere in a
file counts (function-local, ``TYPE_CHECKING``-guarded, ``try``-guarded),
every parent package of an imported module counts, ``from pkg import name``
counts ``pkg.name`` when that is a module, and any string literal naming a
module in the tree counts (covers ``importlib.import_module("pylabrobot...")``
in ``legacy/liquid_handling/channel_positioning.py`` and
``pipette_batch_scheduling.py``).
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

#: The subpackage PyLabRobot 1.0 moved the machine-agnostic API into. A
#: single path segment naming the surface root, the same kind of literal as
#: ``derive._DEFAULT_PLR_PKG_ROOT``'s ``external/pylabrobot/pylabrobot``.
LEGACY_SUBPACKAGE = "legacy"

#: ``legacy`` -- the default: legacy import closure when ``legacy/`` exists,
#: else the whole tree. ``nonlegacy`` -- every source file NOT under
#: ``legacy/`` (the shape a future ``upstream_nonlegacy`` re-cut at >= 1.0
#: would take). ``all`` -- every source file, no selection.
SURFACE_FILE_MODES: tuple[str, ...] = ("legacy", "nonlegacy", "all")


def has_legacy_subpackage(plr_pkg_root: Path) -> bool:
    return (plr_pkg_root / LEGACY_SUBPACKAGE / "__init__.py").is_file()


def _is_under(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _module_names(files: list[Path], plr_pkg_root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for f in files:
        parts = f.relative_to(plr_pkg_root.parent).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        out[".".join(parts)] = f
    return out


def _file_imports(file: Path, own_module: str, is_package: bool, known: dict[str, Path]) -> set[Path]:
    tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
    package = own_module if is_package else own_module.rpartition(".")[0]
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - (node.level - 1)] if node.level > 1 else base
                mod = ".".join(base + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            names.append(mod)
            names.extend(f"{mod}.{alias.name}" for alias in node.names if alias.name != "*")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in known:
            names.append(node.value)
    deps: set[Path] = set()
    for name in names:
        parts = name.split(".")
        for i in range(1, len(parts) + 1):
            hit = known.get(".".join(parts[:i]))
            if hit is not None:
                deps.add(hit)
    return deps


@lru_cache(maxsize=8)
def _legacy_closure_cached(plr_pkg_root_str: str, files_key: tuple[str, ...]) -> tuple[str, ...]:
    plr_pkg_root = Path(plr_pkg_root_str)
    files = [Path(p) for p in files_key]
    known = _module_names(files, plr_pkg_root)
    module_of = {f: m for m, f in known.items()}
    legacy_dir = plr_pkg_root / LEGACY_SUBPACKAGE
    seed = [f for f in files if _is_under(f, legacy_dir)]
    seen = set(seed)
    stack = list(seed)
    while stack:
        f = stack.pop()
        for dep in _file_imports(f, module_of[f], f.name == "__init__.py", known):
            if dep not in seen:
                seen.add(dep)
                stack.append(dep)
    return tuple(sorted(str(f) for f in seen))


def legacy_import_closure(plr_pkg_root: Path, files: list[Path]) -> list[Path]:
    """The static import closure of ``files`` under ``<root>/legacy/``,
    restricted to ``files`` (so the caller's test-file filter still
    applies). Sorted, deterministic.
    """
    key = tuple(str(f) for f in sorted(files))
    return [Path(p) for p in _legacy_closure_cached(str(plr_pkg_root), key)]


def select_surface_files(
    plr_pkg_root: Path,
    is_source_file: Callable[[Path], bool],
    mode: str = "legacy",
) -> list[Path]:
    """The analyzed surface's source files under ``plr_pkg_root``, sorted.
    See the module docstring for the rule; ``is_source_file`` is the
    caller's own test-file filter (derive and the surveys each own one).
    """
    if mode not in SURFACE_FILE_MODES:
        raise ValueError(f"unknown surface file mode {mode!r}; expected one of {SURFACE_FILE_MODES}")
    every = sorted(p for p in plr_pkg_root.rglob("*.py") if is_source_file(p))
    if mode == "all":
        return every
    legacy_dir = plr_pkg_root / LEGACY_SUBPACKAGE
    if mode == "nonlegacy":
        return [p for p in every if not _is_under(p, legacy_dir)]
    if not has_legacy_subpackage(plr_pkg_root):
        return every
    return legacy_import_closure(plr_pkg_root, every)
