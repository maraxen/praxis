#!/usr/bin/env python3
"""Survey every deprecation marker in vendored PyLabRobot: which
functions/methods warn, what they say to use instead, and any inline
removal-target comment (e.g. `# remove v1b1`) on the def line.

Why: we already hit two of these incidentally in test output this session
(`Cor_96_wellplate_360ul_Fb`, `hamilton_1_trough_200ml_Vb`) -- discovered
one at a time as warnings scrolled by, not as a known, complete list. PLR
has no decorator-based deprecation convention (checked: zero `@deprecated`
usages anywhere in the vendored tree) -- every one of its 188
`warnings.warn(...)` call sites is the bare stdlib idiom, so that's the
only shape this survey needs to recognize.

Same AST-first, version-stamped approach as the other two surveys in this
family (survey_plr_exceptions.py, survey_plr_preconditions.py) --
comments aren't part of the AST, so the removal-target hint is pulled by
re-reading the raw source line at the def's lineno, not by parsing.

Usage:
    uv run python scripts/survey_plr_deprecations.py
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from plr_survey_common import (
    DEFAULT_PLR_ROOT,
    PROJECT_ROOT,
    iter_source_files,
    module_name,
    parse_files,
    plr_version_stamp,
)

DEFAULT_OUT = PROJECT_ROOT / "training" / "verify" / "data" / "plr_deprecations.json"

_DEPRECATION_CATEGORIES = {"DeprecationWarning", "PendingDeprecationWarning", "FutureWarning"}
#: e.g. "# remove v1b1", "# TODO remove in v2.0", "# deprecated, remove after 2026-07"
_REMOVAL_COMMENT_RE = re.compile(r"#.*?\b(remove[d]?|deprecat\w*)\b.*", re.IGNORECASE)


@dataclass
class DeprecationFinding:
    qualname: str
    class_name: str | None
    module: str
    file: str
    lineno: int
    category: str  # "DeprecationWarning" | "PendingDeprecationWarning" | "FutureWarning"
    message: str | None  # unparsed source of the warning message arg, best-effort
    #: The def line's trailing comment, if it mentions removal/deprecation
    #: (e.g. "# remove v1b1") -- None if there is none or it's unrelated.
    removal_comment: str | None
    docstring_mentions_deprecated: bool


def _literal_or_source(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    try:
        return ast.unparse(node)  # f-string or computed message -- best-effort source
    except Exception:  # noqa: BLE001
        return None


def _warn_category(node: ast.Call) -> str | None:
    # warnings.warn(msg, DeprecationWarning) -- positional
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Name) and node.args[1].id in _DEPRECATION_CATEGORIES:
        return node.args[1].id
    # warnings.warn(msg, category=DeprecationWarning) -- keyword
    for kw in node.keywords:
        if kw.arg == "category" and isinstance(kw.value, ast.Name) and kw.value.id in _DEPRECATION_CATEGORIES:
            return kw.value.id
    return None


class _WarnCollector(ast.NodeVisitor):
    def __init__(self):
        self.findings: list[tuple[str | None, str, str]] = []  # (category, message, ...)
        self._hit = False

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        is_warnings_warn = (
            (isinstance(func, ast.Attribute) and func.attr == "warn"
             and isinstance(func.value, ast.Name) and func.value.id == "warnings")
            or (isinstance(func, ast.Name) and func.id == "warn")
        )
        if is_warnings_warn:
            category = _warn_category(node)
            if category is not None:
                message = _literal_or_source(node.args[0]) if node.args else None
                self.findings.append((category, message))
        self.generic_visit(node)


def _def_line_comment(source_lines: list[str], lineno: int) -> str | None:
    """The trailing comment on the `def ...:` line itself (PLR's own
    convention for a removal-target hint, e.g. `def Foo():  # remove v1b1`).
    Scans forward a few lines for a multi-line signature's closing `:` --
    comments on intermediate parameter lines are deliberately not chased,
    since that's not PLR's observed convention (single trailing comment on
    whichever line closes the signature)."""
    for offset in range(0, 6):
        idx = lineno - 1 + offset
        if idx >= len(source_lines):
            break
        line = source_lines[idx]
        if ":" in line.split("#")[0]:  # signature closes on this line
            match = _REMOVAL_COMMENT_RE.search(line)
            return match.group(0).strip() if match else None
    return None


def survey(plr_root: Path) -> list[DeprecationFinding]:
    files = iter_source_files(plr_root)
    print(f"scanning {len(files)} files under {plr_root}")
    parsed = parse_files(files)

    results: list[DeprecationFinding] = []

    for file, tree in parsed.items():
        module = module_name(Path(file), plr_root)
        rel_file = str(Path(file).relative_to(PROJECT_ROOT))
        source_lines = Path(file).read_text(encoding="utf-8").splitlines()

        def _survey_function(node, class_name: str | None):
            collector = _WarnCollector()
            for stmt in node.body:
                collector.visit(stmt)
            if not collector.findings:
                return
            doc = ast.get_docstring(node) or ""
            qualname = f"{class_name}.{node.name}" if class_name else node.name
            removal_comment = _def_line_comment(source_lines, node.lineno)
            for category, message in collector.findings:
                results.append(DeprecationFinding(
                    qualname=qualname, class_name=class_name, module=module, file=rel_file,
                    lineno=node.lineno, category=category, message=message,
                    removal_comment=removal_comment,
                    docstring_mentions_deprecated="deprecat" in doc.lower(),
                ))

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _survey_function(node, None)
            elif isinstance(node, ast.ClassDef):
                for member in ast.iter_child_nodes(node):
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        _survey_function(member, node.name)

    return results


def print_summary(results: list[DeprecationFinding]) -> None:
    print(f"\n{len(results)} deprecation warning site(s) found\n")
    for r in sorted(results, key=lambda x: (x.module, x.qualname)):
        removal = f"  [{r.removal_comment}]" if r.removal_comment else ""
        msg = f": {r.message}" if r.message else ""
        print(f"  {r.qualname:<40} {r.category}{removal}  ({r.file}:{r.lineno}){msg}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plr-root", type=Path, default=DEFAULT_PLR_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    results = survey(args.plr_root)
    print_summary(results)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "plr_root": str(args.plr_root.relative_to(PROJECT_ROOT)),
        "version": plr_version_stamp(),
        "total_deprecation_sites": len(results),
        "deprecations": [asdict(r) for r in results],
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {args.out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
