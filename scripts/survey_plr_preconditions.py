#!/usr/bin/env python3
"""Survey every function/method in vendored PyLabRobot for the STATE
PRECONDITIONS it asserts before doing its real work: guard clauses
(`if <cond>: raise X(...)`), bare `assert`s, and same-scope calls to
validation-looking helpers.

Why (260828, direct follow-up to the open multi-channel tip-precondition
gap in training/overlay_gen/exec_verify.py's _precondition_plan): that gap
was found by trial and error (a real execution rejection, traced back by
hand). This survey exists so the NEXT precondition gap is found by reading
what PLR's own source actually requires, not by another live failure.
Concretely, aspirate()'s own body answers the tip-count question directly:
`use_channels = use_channels or self._default_use_channels or
list(range(len(resources)))` then `tips = [self.head[channel].get_tip()
for channel in use_channels]` -- i.e. exactly one tip per RESOURCE unless
use_channels is given explicitly, which is precisely the fact
_precondition_plan needs to synthesize the right number of tips.

Scope: the ENGINE scans every function/method across the whole vendored
surface (not just LiquidHandler) -- `--target-class` only filters the
REPORT, so this survey is reusable for other tool families without
re-architecting it. Only reused across surveys, never scan-scoped, for
exactly the reason the exception survey turned out to matter beyond its
original 2-module trial: fixing a gap you didn't know to look for needs
the whole surface, not just the part you started with.

Not full-program dataflow analysis -- this is a single-pass, per-function
syntactic scan (matches the exception survey's approach: cheap, precise,
zero extra dependency, deliberately not aiming to resolve everything).
Concretely NOT resolved:
* cross-class delegate calls (e.g. `self.head[channel].get_tip()` --
  `get_tip` lives on a different class than the caller). Only SAME-CLASS
  (`self.<name>(...)`) and MODULE-LEVEL (`bare_name(...)`) delegate calls
  are resolved, since those don't need type inference to attribute
  correctly. A cross-class call whose receiver is a bare `self.<name>`
  Attribute or a bare Name is recorded as an UNRESOLVED_CALL note so a
  human knows to look; every OTHER receiver shape (`self.head[channel].
  get_tip()`, `tip_spot.get_tip()`, ...) used to vanish with no trace at
  all (round-4/round-5 finding F1) and is now recorded, receiver-qualified,
  in `dropped_calls` instead of silently disappearing.
* which precondition applies under which caller-supplied argument VALUES
  (this is a static syntactic survey, not a symbolic executor) -- the
  `mentions_params` field says WHICH parameters a guard's condition
  references, not what values make it fire.

Usage:
    uv run python scripts/survey_plr_preconditions.py --target-class LiquidHandler
    uv run python scripts/survey_plr_preconditions.py \
        --out training/verify/data/plr_preconditions.json
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from plr_survey_common import (
    DEFAULT_PLR_ROOT,
    DEFAULT_PLR_SUBMODULE,
    PROJECT_ROOT,
    iter_source_files,
    module_name,
    parse_files,
    plr_version_stamp,
    relative_to_project_or_absolute,
    resolved_call_name,
)

DEFAULT_OUT = PROJECT_ROOT / "training" / "verify" / "data" / "plr_preconditions.json"


@dataclass
class DroppedCall:
    """One receiver-qualified call expression dropped by `visit_Call`'s
    `name is None` fallthrough (see `FunctionPreconditions.dropped_calls`),
    recorded WHERE it was seen: its own line number and the nearest-first
    `scope_trail` live at the moment of the visit (260903, spec
    260903_plr-sema-volume-increment.md §14.0.2, T25). Same shape and same
    trail convention `PreconditionFinding` already uses -- `_record` builds
    the identical three facts for findings; this is the same recording,
    applied to a dropped call instead of a finding. Multiplicity is
    preserved: two call sites with the identical `expr` under different
    scopes are two separate `DroppedCall` records, not one deduplicated
    entry (AC-14.3(iii))."""

    expr: str
    lineno: int
    scope_trail: list[str]


@dataclass
class PreconditionFinding:
    kind: str  # "raise_guard" | "assert"
    #: The nearest enclosing branch condition's source text, or None if the
    #: raise/assert is unconditional in its immediate scope (still real
    #: evidence -- e.g. an unconditional raise reachable only via an outer
    #: guard already captured in scope_trail).
    condition: str | None
    raises: str | None  # exception class name; None only for a bare assert
    #: Nearest-first list of enclosing if/for/while readable context, e.g.
    #: ["for channel in use_channels", "if not skip_head"].
    scope_trail: list[str]
    mentions_params: list[str]
    lineno: int


@dataclass
class FunctionPreconditions:
    qualname: str  # "LiquidHandler.aspirate" or bare "func_name" at module level
    class_name: str | None
    module: str
    file: str
    lineno: int
    params: list[str]
    findings: list[PreconditionFinding] = field(default_factory=list)
    #: Same-class or module-level helper calls found in the body that LOOK
    #: like validation (name starts with _check/_assert/_validate/validate,
    #: or is itself a function this survey found has its own findings) --
    #: the reader should also check that function's own entry.
    delegates_to: list[str] = field(default_factory=list)
    #: Calls this survey could not attribute to a same-class or
    #: module-level function (see module docstring's scope note) -- named
    #: so a human can decide whether to chase it by hand.
    unresolved_calls: list[str] = field(default_factory=list)
    #: (round-5 T0, F1) Every call whose receiver is an ast.Attribute but is
    #: NOT the literal `self.<name>(...)` shape (e.g. `self.head[channel].
    #: get_tip()`, `tip_spot.get_tip()`) -- previously left NO trace at all,
    #: not even an unresolved_calls entry, because `visit_Call` only ever
    #: set `name` for a bare `self.<name>` Attribute or a bare Name. Recorded
    #: as the full receiver-qualified call expression (`ast.unparse` of the
    #: whole `Call.func` node), not a bare attribute name, so
    #: `self.head[channel].get_tip` is distinguishable from `tip_spot.get_tip`.
    #: Strictly additive: does not alter `name`/`delegates_to`/
    #: `unresolved_calls` for any existing call shape.
    #: (260903, T25) Each entry is now a `DroppedCall` record -- `expr` plus
    #: the call's own `lineno` and nearest-first `scope_trail` -- rather than
    #: a bare `expr` string. Multiplicity preserved (this is a `list`, built
    #: from `_BodyScanner.dropped`, itself now a `list` and not a `set`): a
    #: dotted call expression appearing twice under two different scopes
    #: yields two distinct records here (spec §14.0.2's normative schema-
    #: change box, AC-14.3(iii)).
    dropped_calls: list[DroppedCall] = field(default_factory=list)


def _is_validation_looking(name: str) -> bool:
    lname = name.lower()
    return any(lname.startswith(p) for p in ("_check", "check_", "_assert", "assert_", "_validate", "validate"))


class _BodyScanner(ast.NodeVisitor):
    """Walks ONE function/method body for precondition evidence."""

    def __init__(self, param_names: set[str], class_method_names: set[str], module_func_names: set[str]):
        self.param_names = param_names
        self.class_method_names = class_method_names
        self.module_func_names = module_func_names
        self._scope_trail: list[str] = []
        self.findings: list[PreconditionFinding] = []
        self.delegates: set[str] = set()
        self.unresolved: set[str] = set()
        #: (round-5 T0, F1) receiver-qualified call expressions dropped by
        #: the `name is None` fallthrough below -- see PreconditionFinding's
        #: dropped_calls docstring. (260903, T25) A `list`, not a `set`:
        #: multiplicity is preserved, since each entry now also carries its
        #: own `lineno`/`scope_trail`, which distinguishes two otherwise-
        #: identical `expr`s recorded at two different call sites.
        self.dropped: list[DroppedCall] = []

    def _mentions(self, node: ast.expr) -> list[str]:
        names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        return sorted(names & self.param_names)

    def _record(self, kind: str, condition: ast.expr | None, raises: str | None, lineno: int) -> None:
        cond_src = None
        mentions: list[str] = []
        if condition is not None:
            try:
                cond_src = ast.unparse(condition)
            except Exception:
                cond_src = None
            mentions = self._mentions(condition)
        self.findings.append(PreconditionFinding(
            kind=kind, condition=cond_src, raises=raises,
            scope_trail=list(self._scope_trail), mentions_params=mentions, lineno=lineno,
        ))

    def visit_If(self, node: ast.If) -> None:
        try:
            test_src = ast.unparse(node.test)
        except Exception:
            test_src = "<unparseable>"
        self._scope_trail.insert(0, f"if {test_src}")
        for child in node.body:
            self.visit(child)
        self._scope_trail.pop(0)
        if node.orelse:
            # A trailing `else:` block is STILL conditionally guarded -- by
            # the negation of `test` -- not unconditional. An `elif` chain
            # self-nests as a single ast.If in orelse, which pushes its OWN
            # "if <elif_test>" trail entry on top of this one when visited,
            # correctly compounding both conditions.
            self._scope_trail.insert(0, f"else of: if {test_src}")
            for child in node.orelse:
                self.visit(child)
            self._scope_trail.pop(0)

    def visit_For(self, node: ast.For) -> None:
        try:
            trail_entry = f"for {ast.unparse(node.target)} in {ast.unparse(node.iter)}"
        except Exception:
            trail_entry = "for <unparseable>"
        self._scope_trail.insert(0, trail_entry)
        self.generic_visit(node)
        self._scope_trail.pop(0)

    visit_AsyncFor = visit_For  # type: ignore[assignment]

    def visit_While(self, node: ast.While) -> None:
        try:
            trail_entry = f"while {ast.unparse(node.test)}"
        except Exception:
            trail_entry = "while <unparseable>"
        self._scope_trail.insert(0, trail_entry)
        self.generic_visit(node)
        self._scope_trail.pop(0)

    def visit_Raise(self, node: ast.Raise) -> None:
        if node.exc is None:
            return  # bare re-raise -- not a new precondition
        if isinstance(node.exc, ast.Name):
            # `raise error` -- a local variable holding a previously-caught
            # or previously-constructed exception (PLR's own "defer the
            # raise until per-item cleanup finishes" idiom), NOT a literal
            # class reference. The variable's NAME is not an exception
            # class name and must not be reported as one.
            name = f"<dynamic:{node.exc.id}>"
        else:
            name = resolved_call_name(node.exc)
        # The nearest enclosing `if` (if any) IS the guard condition for a
        # raise sitting directly in that if's body -- record it as such
        # rather than duplicating the whole scope_trail into `condition`.
        nearest_if_condition = None
        if self._scope_trail and self._scope_trail[0].startswith("if "):
            nearest_if_condition = self._scope_trail[0][3:]
        self.findings.append(PreconditionFinding(
            kind="raise_guard", condition=nearest_if_condition, raises=name,
            scope_trail=list(self._scope_trail),
            mentions_params=sorted(self.param_names & {n.id for n in ast.walk(node.exc) if isinstance(n, ast.Name)}),
            lineno=node.lineno,
        ))

    def visit_Assert(self, node: ast.Assert) -> None:
        self._record("assert", node.test, None, node.lineno)

    def visit_Call(self, node: ast.Call) -> None:
        target = node.func
        name: str | None = None
        is_self_call = False
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
            name = target.attr
            is_self_call = True
        elif isinstance(target, ast.Name):
            name = target.id
        elif isinstance(target, ast.Attribute):
            # (round-5 T0, F1) Every OTHER receiver shape -- a multi-level
            # attribute chain (`self.head[channel].get_tip`), or a non-self
            # bare-Name receiver (`tip_spot.get_tip`) -- previously left no
            # trace at all: `name` stayed None and the recording block below
            # never ran. Record the full receiver-qualified call expression
            # (the whole `Call.func` node, not just `target.attr`) so it can
            # be told apart from a same-named call on a different receiver.
            # Purely additive: `name`/`is_self_call` are untouched, so the
            # existing delegates/unresolved recording below is unaffected.
            try:
                expr = ast.unparse(target)
            except Exception:
                expr = f"<unparseable>.{target.attr}"
            # (260903, T25) Record WHERE this dropped call sits, not just
            # what it looks like -- `node.lineno` is the Call node's own
            # line (the call, not the receiver expression), and
            # `self._scope_trail` is the SAME nearest-first, polarity-aware
            # trail `_record` captures for findings, read at the identical
            # point in the walk (§14.0.2's normative schema-change box).
            self.dropped.append(DroppedCall(expr=expr, lineno=node.lineno, scope_trail=list(self._scope_trail)))

        if name is not None:
            if (is_self_call and name in self.class_method_names) or (not is_self_call and name in self.module_func_names):
                self.delegates.add(name)
            elif is_self_call or (not is_self_call and _is_validation_looking(name)):
                # Looks like a validation call but isn't resolvable to a
                # same-class/module function this survey collected (e.g. a
                # cross-class call, or a builtin/imported one) -- name it,
                # don't drop it.
                if _is_validation_looking(name) or is_self_call:
                    self.unresolved.add(name)
        self.generic_visit(node)


def _function_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = node.args
    names = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    if args.vararg:
        names.append(args.vararg.arg)
    if args.kwarg:
        names.append(args.kwarg.arg)
    return names


def survey(plr_root: Path) -> list[FunctionPreconditions]:
    files = iter_source_files(plr_root)
    print(f"scanning {len(files)} files under {plr_root}")
    parsed = parse_files(files)

    results: list[FunctionPreconditions] = []

    for file, tree in parsed.items():
        module = module_name(Path(file), plr_root)
        rel_file = relative_to_project_or_absolute(Path(file))

        module_func_names = {
            n.name for n in ast.iter_child_nodes(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        def _survey_function(node, class_name: str | None, class_method_names: set[str]):
            params = _function_params(node)
            scanner = _BodyScanner(set(params), class_method_names, module_func_names)
            for stmt in node.body:
                scanner.visit(stmt)
            qualname = f"{class_name}.{node.name}" if class_name else node.name
            results.append(FunctionPreconditions(
                qualname=qualname, class_name=class_name, module=module, file=rel_file,
                lineno=node.lineno, params=params, findings=scanner.findings,
                delegates_to=sorted(scanner.delegates), unresolved_calls=sorted(scanner.unresolved),
                # (260903, T25) NOT sorted -- `scanner.dropped` is already a
                # deterministic list in AST-visitation order, and multiplicity
                # (two records sharing an `expr` from two different scopes)
                # must be preserved verbatim, not collapsed or reordered by a
                # `sorted()` over records that carry no total order.
                dropped_calls=list(scanner.dropped),
            ))

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _survey_function(node, None, set())
            elif isinstance(node, ast.ClassDef):
                method_names = {
                    n.name for n in ast.iter_child_nodes(node)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                for member in ast.iter_child_nodes(node):
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        _survey_function(member, node.name, method_names)

    return results


def print_summary(results: list[FunctionPreconditions], target_class: str | None) -> None:
    scoped = [r for r in results if target_class is None or r.class_name == target_class]
    with_findings = [r for r in scoped if r.findings]
    print(f"\n{len(with_findings)} of {len(scoped)} scoped function(s) have precondition evidence"
          f"{f' (class={target_class})' if target_class else ' (whole surface)'}")
    for r in with_findings:
        print(f"\n=== {r.qualname} ({r.file}:{r.lineno}) params={r.params} ===")
        for f_ in r.findings:
            scope = " <- ".join(f_.scope_trail) if f_.scope_trail else "(unconditional in body)"
            target = f_.raises or "AssertionError"
            cond = f_.condition or "(see scope_trail)"
            print(f"  [{f_.kind}] raises {target} if NOT ({cond})   scope: {scope}"
                  f"{'  mentions: ' + ','.join(f_.mentions_params) if f_.mentions_params else ''}")
        if r.delegates_to:
            print(f"  delegates to (check their own entries): {', '.join(r.delegates_to)}")
        if r.unresolved_calls:
            print(f"  unresolved validation-looking calls (chase by hand): {', '.join(r.unresolved_calls)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plr-root", type=Path, default=DEFAULT_PLR_ROOT)
    parser.add_argument("--target-class", default=None,
                         help="Filter the printed/written report to one class (e.g. LiquidHandler). "
                              "The scan itself always covers the whole surface.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--submodule-root", type=Path, default=None,
        help="Git root to stamp this survey's 'version' field against (260901 T13). "
             "Defaults to the vendored external/pylabrobot submodule -- pass this "
             "explicitly when --plr-root points at a DIFFERENT tree (e.g. an "
             "out-of-repo upstream extraction) so 'version' describes what was "
             "actually scanned instead of silently reporting the default submodule's "
             "git state. A non-git tree (e.g. a `git archive | tar -x` extraction with "
             "no .git dir) degrades to {git_sha: None, git_dirty: None} here -- "
             "record its real pin out of band (see plr_sema._provenance.Surface).",
    )
    args = parser.parse_args()

    results = survey(args.plr_root)
    print_summary(results, args.target_class)

    scoped = [r for r in results if args.target_class is None or r.class_name == args.target_class]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    submodule_root = args.submodule_root if args.submodule_root is not None else DEFAULT_PLR_SUBMODULE
    payload: dict[str, Any] = {
        "plr_root": relative_to_project_or_absolute(args.plr_root),
        "version": plr_version_stamp(submodule_root),
        "target_class_filter": args.target_class,
        "total_functions_scanned": len(results),
        "total_functions_in_report": len(scoped),
        "functions": [asdict(r) for r in scoped],
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {relative_to_project_or_absolute(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
