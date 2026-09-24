#!/usr/bin/env python3
"""Survey every exception class in vendored PyLabRobot: hierarchy, a proposed
failure-mode category, and every call site that raises it.

Feeds training/verify/failure_taxonomy.py, whose "precondition_state"
category currently lumps EVERY real pylabrobot.* exception into one bucket
(see that module's docstring, 260828). This script exists to make that
bucket legible: which specific PLR exceptions can fire, roughly why
(grouped into finer failure modes), and where in PLR's own source they're
actually raised -- so a precondition-synthesis fix (e.g. the open
multi-channel tip-precondition gap in overlay_gen/exec_verify.py's
_precondition_plan) can be built from real trigger conditions instead of
guesswork.

AST, not tree-sitter: the survey target (vendored PyLabRobot) is pure
Python source, so ast.parse gives exact, dependency-free cross-file
inheritance resolution and raise-site line numbers. Tree-sitter earns its
keep on multi-language or incremental-parse targets; neither applies here.

Shares scripts/plr_survey_common.py with survey_plr_preconditions.py and
survey_plr_deprecations.py (file discovery, version stamping, the
class-collection + exception-closure passes) -- see that module's
docstring for why version-stamping specifically matters: it's what makes
re-running these surveys across PLR upgrades ("does this taxonomy still
hold after bumping the pin") a diff against a known baseline rather than a
guess.

Usage:
    uv run python scripts/survey_plr_exceptions.py
    uv run python scripts/survey_plr_exceptions.py --plr-root external/pylabrobot/pylabrobot \
        --out training/verify/data/plr_exception_taxonomy.json

Output: a JSON report (see --out) plus a human-readable summary table on
stdout: category -> exception classes -> trigger-site counts.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from plr_survey_common import (
    DEFAULT_PLR_ROOT,
    PROJECT_ROOT,
    ClassInfo,
    collect_all_classes,
    exception_name_closure,
    iter_source_files,
    parse_files,
    plr_version_stamp,
    resolved_call_name,
)

DEFAULT_OUT = PROJECT_ROOT / "training" / "verify" / "data" / "plr_exception_taxonomy.json"

#: (category, keyword) pairs checked in order, first match on the class NAME
#: wins. This is a proposed taxonomy for human review, not a load-bearing
#: runtime classifier -- verify/failure_taxonomy.py still buckets all of
#: these under "precondition_state" for execution-verify purposes; this is
#: the finer-grained breakdown WITHIN that bucket.
_NAME_KEYWORD_CATEGORIES: list[tuple[str, str]] = [
    ("tip_state", "Tip"),
    ("volume_state", "Volume"),
    ("volume_state", "Liquid"),
    ("channel_state", "Channel"),
    ("contamination_state", "Contamination"),
    ("location_state", "Location"),
    ("resource_definition", "DefinitionIncomplete"),
    ("occupancy_state", "NoPlate"),
    ("occupancy_state", "HasPlate"),
    ("occupancy_state", "NoFreeSite"),
    ("occupancy_state", "NotAtBucket"),
    ("calibration_state", "Calibrated"),
    ("resource_state", "Resource"),
]

#: Fallback by defining-module path substring, checked if no name keyword hit.
_MODULE_SUBSTRING_CATEGORIES: list[tuple[str, str]] = [
    ("pump_state", "pumps"),
    ("centrifuge_state", "centrifuge"),
    ("plate_reader_state", "plate_reading"),
    ("storage_state", "storage"),
    ("channel_state", "liquid_handling"),
    ("resource_state", "resources"),
]


@dataclass
class ExceptionClass:
    name: str
    module: str
    file: str
    lineno: int
    bases: list[str]
    docstring: str | None
    category: str = "uncategorized"
    trigger_sites: list["TriggerSite"] = field(default_factory=list)


@dataclass
class TriggerSite:
    file: str
    lineno: int
    enclosing_function: str | None
    enclosing_condition: str | None
    #: "raise" (a literal `raise ClassName(...)`) or "dispatch_table" (the
    #: class appears as a dict-literal VALUE -- PLR's own pattern for
    #: firmware error-code -> exception-class lookup, e.g. STAR_backend.py's
    #: `{8: HamiltonNoTipError, ...}` then `raise error_class_map[code](...)`
    #: elsewhere; a literal raise-site scan structurally cannot see this).
    kind: str = "raise"


class _RaiseCollector(ast.NodeVisitor):
    """Every `raise` call and dispatch-table reference, matched against the
    exception-class closure computed across ALL files."""

    def __init__(self, file: str, exception_names: frozenset[str]):
        self.file = file
        self.exception_names = exception_names
        self._func_stack: list[str] = []
        self._condition_stack: list[str] = []
        self.sites: list[tuple[str, TriggerSite]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._func_stack.append(node.name)
        self.generic_visit(node)
        self._func_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_If(self, node: ast.If) -> None:
        try:
            cond = ast.unparse(node.test)
        except Exception:  # noqa: BLE001 - best-effort context only
            cond = None
        self._condition_stack.append(cond or "<unparseable>")
        for child in node.body:
            self.visit(child)
        self._condition_stack.pop()
        for child in node.orelse:
            self.visit(child)

    def visit_Raise(self, node: ast.Raise) -> None:
        if node.exc is None:
            return  # bare `raise` (re-raise) -- no new exception identity
        name = resolved_call_name(node.exc)
        if name is None or name not in self.exception_names:
            return
        self.sites.append((
            name,
            TriggerSite(
                file=self.file,
                lineno=node.lineno,
                enclosing_function=self._func_stack[-1] if self._func_stack else None,
                enclosing_condition=self._condition_stack[-1] if self._condition_stack else None,
                kind="raise",
            ),
        ))

    def visit_Dict(self, node: ast.Dict) -> None:
        for value in node.values:
            if isinstance(value, ast.Name) and value.id in self.exception_names:
                self.sites.append((
                    value.id,
                    TriggerSite(
                        file=self.file,
                        lineno=value.lineno,
                        enclosing_function=self._func_stack[-1] if self._func_stack else None,
                        enclosing_condition=None,
                        kind="dispatch_table",
                    ),
                ))
        self.generic_visit(node)


def _categorize(info: ClassInfo) -> str:
    for category, keyword in _NAME_KEYWORD_CATEGORIES:
        if keyword in info.name:
            return category
    for category, keyword in _MODULE_SUBSTRING_CATEGORIES:
        if keyword in info.module:
            return category
    return "uncategorized"


def survey(plr_root: Path) -> list[ExceptionClass]:
    files = iter_source_files(plr_root)
    print(f"scanning {len(files)} files under {plr_root}")
    parsed = parse_files(files)

    all_classes = collect_all_classes(parsed, plr_root)
    exception_names = exception_name_closure(all_classes)
    print(f"found {len(exception_names & set(all_classes))} exception classes "
          f"(of {len(all_classes)} total classes)")

    exception_classes: dict[str, ExceptionClass] = {
        name: ExceptionClass(
            name=info.name, module=info.module, file=info.file, lineno=info.lineno,
            bases=info.bases, docstring=info.docstring, category=_categorize(info),
        )
        for name, info in all_classes.items() if name in exception_names
    }

    for file, tree in parsed.items():
        rel = str(Path(file).relative_to(PROJECT_ROOT))
        raiser = _RaiseCollector(rel, exception_names)
        raiser.visit(tree)
        for name, site in raiser.sites:
            if name in exception_classes:
                exception_classes[name].trigger_sites.append(site)

    return sorted(exception_classes.values(), key=lambda e: (e.category, e.name))


def print_summary(classes: list[ExceptionClass]) -> None:
    by_category: dict[str, list[ExceptionClass]] = defaultdict(list)
    for exc in classes:
        by_category[exc.category].append(exc)

    for category in sorted(by_category):
        members = by_category[category]
        print(f"\n=== {category} ({len(members)} classes) ===")
        for exc in members:
            raises = [s for s in exc.trigger_sites if s.kind == "raise"]
            dispatch = [s for s in exc.trigger_sites if s.kind == "dispatch_table"]
            funcs = sorted({s.enclosing_function for s in raises if s.enclosing_function})
            if raises:
                where = f"raised in: {', '.join(funcs)}"
            elif dispatch:
                where = f"NO literal raise site -- only in {len(dispatch)} error-code dispatch table(s)"
            else:
                where = "no trigger evidence found (declared, unreferenced, or unresolvable)"
            print(f"  {exc.name:<32} {len(raises):>3} raise site(s)  {where}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plr-root", type=Path, default=DEFAULT_PLR_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    classes = survey(args.plr_root)
    print_summary(classes)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "plr_root": str(args.plr_root.relative_to(PROJECT_ROOT)),
        "version": plr_version_stamp(),
        "total_exception_classes": len(classes),
        "classes": [asdict(exc) for exc in classes],
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"\nwrote {args.out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
