"""A-CALLBACK-NO-DELEGATE's pin check (backlog #5668; spec 260902 §10.6.3,
spec 260909 §17.5.1's 260930 amendment).

A call through a stored instance callable (`for cb in self._callbacks: cb()`)
is recorded by the survey as a `callback_calls` entry, which `plr_sema.derive`
turns into an `unresolved_delegate` gap but NOT into one of M3's fail-closed
conditions. That is sound only if a stored callback never calls the delegate
whose call-site set M3 folds, `LiquidHandler._check_args`. The half of that
checkable from PLR source is checked here: every callback PLR itself registers
(`<x>.register_<...>callback(<arg>)`, outside tests) resolves to a function
that, following same-class `self.<m>()` calls to a fixpoint, never calls
`_check_args`. User-registered callbacks remain an assumption.

The inventory size is pinned, so a PLR bump that adds a registration fails
here and gets a human look instead of silently widening the assumption.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLR_PKG = REPO_ROOT / "external" / "pylabrobot" / "pylabrobot"
#: The delegate M3 folds call-site sets for (spec 260909 §17.5.1).
FOLDED_DELEGATE = "_check_args"
#: PLR-internal `register_*callback*(...)` calls at the pin (786ac2c4e).
EXPECTED_REGISTRATIONS = 22


def _is_test_file(path: Path) -> bool:
    return path.name.endswith("_tests.py") or path.name.startswith("test_") or "tests" in path.parts


def _registrations() -> list[tuple[Path, ast.ClassDef | None, ast.AST, ast.expr]]:
    """(file, enclosing class, enclosing function, registered argument) per call."""
    found: list[tuple[Path, ast.ClassDef | None, ast.AST, ast.expr]] = []
    for path in sorted(PLR_PKG.rglob("*.py")):
        if _is_test_file(path.relative_to(PLR_PKG)):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))

        def visit(node: ast.AST, cls: ast.ClassDef | None, fn: ast.AST | None) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.ClassDef):
                    visit(child, child, None)
                    continue
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    visit(child, cls, child)
                    continue
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr.startswith("register_")
                    and "callback" in child.func.attr
                ):
                    # Positional or keyword: every argument is a candidate
                    # callable, so none escapes the inventory.
                    for arg in (*child.args, *(kw.value for kw in child.keywords)):
                        found.append((path, cls, fn, arg))
                visit(child, cls, fn)

        visit(tree, None, None)
    return found


_CLASS_INDEX: dict[str, list[ast.ClassDef]] | None = None


def _class_index() -> dict[str, list[ast.ClassDef]]:
    """Every class in the package by bare name. Names collide (legacy and
    non-legacy trees define same-named classes), so each name maps to ALL its
    definitions and lookups check every candidate -- over-approximating the
    MRO, which can only flag more, never less."""
    global _CLASS_INDEX
    if _CLASS_INDEX is None:
        index: dict[str, list[ast.ClassDef]] = {}
        for path in sorted(PLR_PKG.rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ClassDef):
                    index.setdefault(node.name, []).append(node)
        _CLASS_INDEX = index
    return _CLASS_INDEX


def _base_names(cls: ast.ClassDef) -> list[str]:
    names = []
    for base in cls.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
        elif isinstance(base, ast.Subscript) and isinstance(base.value, ast.Name):
            names.append(base.value.id)
    return names


def _lookup_methods(cls: ast.ClassDef | None, name: str, index: dict[str, list[ast.ClassDef]] | None = None) -> list[ast.AST]:
    """Every definition of method `name` on `cls` or any (candidate) ancestor."""
    if cls is None:
        return []
    index = _class_index() if index is None else index
    found: list[ast.AST] = []
    seen: set[int] = set()
    stack = [cls]
    while stack:
        c = stack.pop()
        if id(c) in seen:
            continue
        seen.add(id(c))
        own = [n for n in c.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
        if own:
            found.extend(own)
            continue
        for base in _base_names(c):
            stack.extend(index.get(base, []))
    return found


def _resolve(cls: ast.ClassDef | None, fn: ast.AST | None, arg: ast.expr, index=None) -> list[ast.AST]:
    """The function bodies a registered argument may denote, when statically
    local: `self.<m>` -> every definition of `m` on the class or an ancestor; a
    bare name -> a def nested in the enclosing function; a lambda -> itself.
    `[]` when the argument is none of these."""
    if isinstance(arg, ast.Lambda):
        return [arg]
    if isinstance(arg, ast.Attribute) and isinstance(arg.value, ast.Name) and arg.value.id == "self":
        return _lookup_methods(cls, arg.attr, index)
    if isinstance(arg, ast.Name) and fn is not None:
        return [
            node for node in ast.walk(fn)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == arg.id
        ]
    return []


def _reaches_folded_delegate(start: ast.AST, cls: ast.ClassDef | None, index=None) -> bool:
    """Following `self.<m>()` calls through `cls`'s (candidate) MRO to a
    fixpoint, does any reached body call `FOLDED_DELEGATE` by name?"""
    seen: set[int] = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        for call in (n for n in ast.walk(node) if isinstance(n, ast.Call)):
            func = call.func
            name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None
            if name == FOLDED_DELEGATE:
                return True
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "self":
                stack.extend(_lookup_methods(cls, func.attr, index))
    return False


#: The exact inventory at the pin, as sorted `(file, registered argument)`
#: pairs -- pinned as a LIST, not a count, so an added registration offset by
#: a removed one still fails.
EXPECTED_INVENTORY = [
    ("legacy/liquid_handling/liquid_handler.py", "self._state_updated"),
    ("legacy/liquid_handling/liquid_handler.py", "self._state_updated"),
    ("legacy/plate_reading/imager.py", "self._will_assign_resource"),
    ("legacy/tip_tracker.py", "self._callback"),
    ("legacy/tip_tracker.py", "state_updated"),
    ("resources/carrier.py", "self._deregister_resource_stack_callback"),
    ("resources/carrier.py", "self._update_resource_stack_location"),
    ("resources/container.py", "self._state_updated"),
    ("resources/hamilton/hamilton_decks.py", "self._check_safe_z_height"),
    ("resources/hamilton/prep_decks.py", "self._check_safe_deck_height"),
    ("resources/resource.py", "self._call_did_assign_resource_callbacks"),
    ("resources/resource.py", "self._call_did_unassign_resource_callbacks"),
    ("resources/resource.py", "self._call_will_assign_resource_callbacks"),
    ("resources/resource.py", "self._call_will_unassign_resource_callbacks"),
    ("resources/tip.py", "self._state_updated"),
    ("visualizer/visualizer.py", "lambda _: self._handle_state_update_callback(resource)"),
    ("visualizer/visualizer.py", "lambda _: self._handle_state_update_callback(resource)"),
    ("visualizer/visualizer.py", "self._handle_resource_assigned_callback"),
    ("visualizer/visualizer.py", "self._handle_resource_unassigned_callback"),
    ("visualizer3D/server.py", "on_update"),
    ("visualizer3D/server.py", "self._on_assign"),
    ("visualizer3D/server.py", "self._on_unassign"),
]


def test_inventory_of_plr_internal_registrations_is_pinned() -> None:
    inventory = sorted((str(p.relative_to(PLR_PKG)), ast.unparse(a)) for p, _c, _f, a in _registrations())
    assert len(inventory) == EXPECTED_REGISTRATIONS
    assert inventory == EXPECTED_INVENTORY, inventory


def _scan(source: str, *, class_methods: set[str] = frozenset(), inherited: frozenset[str] = frozenset(),
          module_funcs: set[str] = frozenset()):
    """Run the survey's OWN `_BodyScanner` over one synthetic method body --
    the same entry `scripts/survey_plr_preconditions.py`'s `_survey_function`
    uses, not a reimplementation."""
    import sys as _sys

    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in _sys.path:
        _sys.path.insert(0, scripts_dir)
    from survey_plr_preconditions import _BodyScanner  # noqa: PLC0415

    (func,) = [n for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    scanner = _BodyScanner({a.arg for a in func.args.args}, set(class_methods), set(module_funcs), inherited)
    for stmt in func.body:
        scanner.visit(stmt)
    return scanner


def test_scanner_records_for_loop_callback() -> None:
    s = _scan("def set_volume(self, v):\n  for callback in self._callbacks:\n    callback()\n")
    assert s.callback_calls == {"_callbacks"} and not s.unresolved and not s.delegates


def test_scanner_records_async_for_and_assign_callbacks() -> None:
    s = _scan(
        "async def f(self):\n"
        "  async for cb in self._stream:\n"
        "    cb()\n"
        "  fn = self._occupied_func\n"
        "  fn(1)\n"
    )
    assert s.callback_calls == {"_stream", "_occupied_func"}


def test_scanner_method_alias_is_a_delegate_not_a_callback() -> None:
    """Review finding 1: `fn = self.<method>; fn()` is an ordinary self-call
    (PLR's own `probing_fn = self.probe_tip_presence_via_pickup`), never a
    callback -- A-CALLBACK-NO-DELEGATE's exemption must not cover it."""
    own = _scan("def f(self):\n  fn = self.probe\n  fn()\n", class_methods={"probe"})
    assert own.delegates == {"probe"} and not own.callback_calls
    inherited = _scan("def f(self):\n  fn = self.base_m\n  fn()\n", inherited=frozenset({"base_m"}))
    assert inherited.delegates == {"base_m"} and inherited.inherited_delegates == {"base_m"}
    assert not inherited.callback_calls


def test_scanner_validation_looking_bound_name_keeps_its_unresolved_entry() -> None:
    """Review finding 2: before #5668 a validation-looking bare name was an
    `unresolved` entry (an M3 fail-closed trigger); it still is, so the
    callback bucket never removes one."""
    s = _scan("def f(self):\n  check_fn = self._checker\n  check_fn()\n")
    assert s.unresolved == {"check_fn"} and s.callback_calls == {"_checker"}


def test_scanner_module_function_shadowing_a_bound_name_stays_a_delegate() -> None:
    s = _scan("def f(self):\n  helper = self._h\n  helper()\n", module_funcs={"helper"})
    assert s.delegates == {"helper"} and not s.callback_calls


def test_scanner_unbound_bare_call_is_not_a_callback() -> None:
    s = _scan("def f(self, cb):\n  cb()\n  other = compute()\n  other()\n")
    assert not s.callback_calls


def test_no_plr_internal_callback_reaches_the_folded_delegate() -> None:
    offenders = []
    for path, cls, fn, arg in _registrations():
        if any(_reaches_folded_delegate(t, cls) for t in _resolve(cls, fn, arg)):
            offenders.append(f"{path.relative_to(PLR_PKG)}:{arg.lineno} {ast.unparse(arg)}")
    assert not offenders, offenders


def test_unresolvable_registrations_are_forwarders_only() -> None:
    """A registration whose argument does not resolve statically must be a pure
    forwarder of another stored callback (`self._callback`, a stored attribute,
    not a method) -- the only such shape PLR uses at the pin. Anything else
    would be an unchecked callback and must get a human look."""
    unresolved = [ast.unparse(arg) for _p, cls, fn, arg in _registrations() if not _resolve(cls, fn, arg)]
    assert unresolved and all(u == "self._callback" for u in unresolved), unresolved


def test_positive_control_detects_a_callback_that_calls_the_delegate() -> None:
    """The instrument must fire: a synthetic class registering a callback that
    reaches `_check_args` through one same-class hop is flagged."""
    src = (
        "class Base:\n"
        "  def _helper(self):\n"
        "    self._check_args(None, {}, default=set())\n"
        "class H(Base):\n"
        "  def setup(self):\n"
        "    self.r.register_state_update_callback(self._cb)\n"
        "  def _cb(self):\n"
        "    self._helper()\n"
    )
    base, cls = ast.parse(src).body
    assert isinstance(base, ast.ClassDef) and isinstance(cls, ast.ClassDef)
    index = {"Base": [base], "H": [cls]}
    targets = _resolve(cls, None, ast.parse("self._cb", mode="eval").body, index)
    assert targets and any(_reaches_folded_delegate(t, cls, index) for t in targets)
    lam = ast.parse("lambda _: self._cb()", mode="eval").body
    assert any(_reaches_folded_delegate(t, cls, index) for t in _resolve(cls, None, lam, index))


def test_negative_control_passes_a_pure_notifier() -> None:
    src = (
        "class R:\n"
        "  def _state_updated(self):\n"
        "    for cb in self._callbacks:\n"
        "      cb(self.serialize_state())\n"
        "class C(R):\n"
        "  pass\n"
    )
    base, cls = ast.parse(src).body
    assert isinstance(base, ast.ClassDef) and isinstance(cls, ast.ClassDef)
    index = {"R": [base], "C": [cls]}
    targets = _resolve(cls, None, ast.parse("self._state_updated", mode="eval").body, index)
    assert targets and not any(_reaches_folded_delegate(t, cls, index) for t in targets)
