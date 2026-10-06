#!/usr/bin/env python3
"""Shim <-> pylabrobot IO contract probe: does each browser shim accept every
call the SHIPPED pylabrobot wheel makes of the class it replaces?

``web-repl/bootstrap/stages.apply()`` replaces ``pylabrobot.io.{serial.Serial,
usb.USB, hid.HID, ftdi.FTDI}`` wholesale with independent shim classes
(``web-repl/overlay/assets/shims/web_*_shim.py``). Nothing ties the shims to
pylabrobot's signatures, so a pin bump that adds a constructor argument breaks
every backend that passes it -- in the browser only, at connect time, with the
robot on the bench. That is exactly how this file came to exist:

    hamilton/base.py:  self.io = USB(human_readable_device_name="Hamilton ...", ...)
    TypeError: WebUSB.__init__() got an unexpected keyword argument
               'human_readable_device_name'

``plr_contract.CONTRACT`` only proves the four classes *exist* in the wheel; it
says nothing about whether a shim can stand in for them. This probe checks three
things, all against the wheel actually installed in the interpreter running it:

1. **Member surface.** Every public member of the pylabrobot class (plus
   ``__init__``) exists on the shim with the same kind (property / coroutine /
   plain function / classmethod / staticmethod / context manager) and a
   compatible signature: identical positional order, every keyword accepted,
   no extra required parameters, and identical defaults where both sides
   have one. Members a shim deliberately cannot provide are listed in
   ``WAIVERS`` with a reason, and a waiver never excuses a member that a
   backend actually uses (check 3).
2. **Constructor call sites.** Every ``USB(...)`` / ``Serial(...)`` /
   ``HID(...)`` / ``FTDI(...)`` call in the wheel's own source is bound with
   ``inspect.Signature.bind`` against the shim's constructor. A call that also
   fails to bind against pylabrobot's own constructor is reported as a scanner
   bug rather than a shim bug.
3. **Instance usage.** For every class that stores one of those objects on
   ``self.<attr>``, every ``self.<attr>.<member>`` the class touches must exist
   on the shim (as a class member or an attribute set in a shim method), and
   every call ``self.<attr>.<member>(...)`` must bind against the shim method.

It also rejects imports that would bypass ``stages.apply()`` (anything other
than ``from <target module> import <Class>``, which is the binding the patch
rewrites).

Runs as a subprocess inside ``check_shim_contract.py``'s throwaway venv (the
editable-install trap is documented there), and is imported directly by
``web-repl/tests/test_shim_contract.py`` for the synthetic-class unit tests.
Stdlib only, CPython >= 3.10, because the throwaway venv has nothing else.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import json
import sys
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# (pylabrobot module, class name, shim module, shim class). The class/builtins
# names mirror ``stages.IO_TARGETS``; test_shim_contract.py asserts they stay
# in sync so a fifth patched class cannot land without a contract entry.
TARGETS: tuple[tuple[str, str, str, str], ...] = (
    ("pylabrobot.io.serial", "Serial", "web_serial_shim", "WebSerial"),
    ("pylabrobot.io.usb", "USB", "web_usb_shim", "WebUSB"),
    ("pylabrobot.io.hid", "HID", "web_hid_shim", "WebHID"),
    ("pylabrobot.io.ftdi", "FTDI", "web_ftdi_shim", "WebFTDI"),
)

# (pylabrobot class name, member) -> why the shim does not provide it. A waived
# member that a backend in the wheel actually touches is still a violation.
WAIVERS: dict[tuple[str, str], str] = {
    ("USB", "read_executor"): (
        "a ThreadPoolExecutor for blocking pyusb reads; WebUSB transfers are "
        "already awaitable on the event loop, so there is no executor to expose"
    ),
    ("FTDI", "dev"): (
        "returns the underlying pylibftdi.Device; the browser has no libftdi, "
        "only a WebUSB device, which is not that type"
    ),
}

_KIND_PROPERTY = "property"
_KIND_CLASSMETHOD = "classmethod"
_KIND_STATICMETHOD = "staticmethod"
_KIND_CONTEXTMANAGER = "contextmanager"
_KIND_COROUTINE = "coroutine function"
_KIND_FUNCTION = "function"
_KIND_DATA = "data attribute"


@dataclass
class Violation:
    target: str  # e.g. "USB -> WebUSB"
    check: str  # "member" | "call-site" | "usage" | "import" | "scanner"
    where: str  # "WebUSB.__init__" or "pylabrobot/.../base.py:73"
    detail: str

    def __str__(self) -> str:
        return f"[{self.check}] {self.target} @ {self.where}: {self.detail}"


@dataclass
class Report:
    violations: list[Violation] = field(default_factory=list)
    # pylabrobot class name -> number of constructor call sites found and bound.
    call_sites: dict[str, int] = field(default_factory=dict)
    # pylabrobot class name -> number of distinct self.<attr>.<member> uses.
    usages: dict[str, int] = field(default_factory=dict)
    waived_unused: list[str] = field(default_factory=list)
    plr_file: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "violations": [asdict(v) for v in self.violations],
                "call_sites": self.call_sites,
                "usages": self.usages,
                "waived_unused": self.waived_unused,
                "plr_file": self.plr_file,
            },
            indent=2,
        )


# --- 1. member surface --------------------------------------------------------


def member_kind(cls: type, name: str) -> str | None:
    """Kind of ``cls.name`` as declared (no descriptor invocation), or None."""
    try:
        raw = inspect.getattr_static(cls, name)
    except AttributeError:
        return None
    if isinstance(raw, property):
        return _KIND_PROPERTY
    if isinstance(raw, classmethod):
        return _KIND_CLASSMETHOD
    if isinstance(raw, staticmethod):
        return _KIND_STATICMETHOD
    if inspect.isfunction(raw):
        if inspect.isgeneratorfunction(inspect.unwrap(raw)) and hasattr(raw, "__wrapped__"):
            return _KIND_CONTEXTMANAGER
        if inspect.iscoroutinefunction(inspect.unwrap(raw)):
            return _KIND_COROUTINE
        return _KIND_FUNCTION
    return _KIND_DATA


def _callable_for(cls: type, name: str) -> Callable[..., Any] | None:
    raw = inspect.getattr_static(cls, name)
    if isinstance(raw, (classmethod, staticmethod)):
        return raw.__func__
    if inspect.isfunction(raw):
        return raw
    return None


def _signature(fn: Callable[..., Any], *, drop_first: bool) -> inspect.Signature:
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    if drop_first and params and params[0].kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        params = params[1:]
    return sig.replace(parameters=params)


_POSITIONAL = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
_KEYWORD = (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)


def compare_signatures(plr: inspect.Signature, shim: inspect.Signature) -> list[str]:
    """Ways in which ``shim`` cannot accept every call that ``plr`` accepts."""
    problems: list[str] = []
    plr_params = list(plr.parameters.values())
    shim_params = list(shim.parameters.values())
    shim_by_name = {p.name: p for p in shim_params}
    shim_var_kw = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in shim_params)
    shim_var_pos = any(p.kind is inspect.Parameter.VAR_POSITIONAL for p in shim_params)

    plr_pos = [p for p in plr_params if p.kind in _POSITIONAL]
    shim_pos = [p for p in shim_params if p.kind in _POSITIONAL]
    for index, p in enumerate(plr_pos):
        if index < len(shim_pos):
            if shim_pos[index].name != p.name:
                problems.append(
                    f"positional parameter #{index} is {shim_pos[index].name!r}, "
                    f"pylabrobot has {p.name!r} (a positional call would misbind)"
                )
        elif not shim_var_pos:
            problems.append(f"does not accept {p.name!r} positionally (pylabrobot slot #{index})")
    if any(p.kind is inspect.Parameter.VAR_POSITIONAL for p in plr_params) and not shim_var_pos:
        problems.append("pylabrobot accepts *args, shim does not")

    for p in plr_params:
        if p.kind not in _KEYWORD or p.kind is inspect.Parameter.POSITIONAL_ONLY:
            continue
        mine = shim_by_name.get(p.name)
        if mine is None or mine.kind not in _KEYWORD:
            if not shim_var_kw:
                problems.append(f"does not accept keyword {p.name!r}")
            continue
        if (
            p.default is not inspect.Parameter.empty
            and mine.default is not inspect.Parameter.empty
            and p.default != mine.default
        ):
            problems.append(
                f"default for {p.name!r} is {mine.default!r}, pylabrobot's is {p.default!r}"
            )
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in plr_params) and not shim_var_kw:
        problems.append("pylabrobot accepts **kwargs, shim does not")

    plr_required = {
        p.name
        for p in plr_params
        if p.default is inspect.Parameter.empty
        and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    }
    for p in shim_params:
        if (
            p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            and p.name not in plr_required
        ):
            problems.append(f"requires {p.name!r}, which pylabrobot does not require")
    return problems


# Members whose defining class lives in one of these modules are not part of
# pylabrobot's contract. At 1.0.0b1 ``pylabrobot/io/serial.py`` and
# ``pylabrobot/io/ftdi.py`` do ``from io import IOBase`` -- the STDLIB file
# ABC, not ``pylabrobot.io.io.IOBase`` -- so ``Serial``/``FTDI`` inherit
# ``close``/``fileno``/``seekable``/... from ``_io._IOBase``. Nothing in
# pylabrobot calls those on a transport; requiring shims to grow them would be
# enforcing an upstream accident.
_NON_CONTRACT_MODULES = frozenset({"builtins", "io", "_io", "abc"})


def _defining_class(cls: type, name: str) -> type | None:
    for klass in cls.__mro__:
        if name in vars(klass):
            return klass
    return None


def public_members(cls: type) -> list[str]:
    names = {"__init__"}
    for name in dir(cls):
        if name.startswith("_"):
            continue
        owner = _defining_class(cls, name)
        if owner is None or owner.__module__ in _NON_CONTRACT_MODULES:
            continue
        names.add(name)
    return sorted(names)


def check_members(
    plr_cls: type,
    shim_cls: type,
    *,
    waivers: dict[tuple[str, str], str] = WAIVERS,
) -> list[Violation]:
    target = f"{plr_cls.__name__} -> {shim_cls.__name__}"
    out: list[Violation] = []
    for name in public_members(plr_cls):
        where = f"{shim_cls.__name__}.{name}"
        plr_kind = member_kind(plr_cls, name)
        shim_kind = member_kind(shim_cls, name)
        if shim_kind is None:
            if (plr_cls.__name__, name) in waivers:
                continue
            out.append(Violation(target, "member", where, f"missing (pylabrobot: {plr_kind})"))
            continue
        if plr_kind != shim_kind:
            out.append(
                Violation(target, "member", where, f"is a {shim_kind}, pylabrobot's is a {plr_kind}")
            )
            continue
        plr_fn = _callable_for(plr_cls, name)
        shim_fn = _callable_for(shim_cls, name)
        if plr_fn is None or shim_fn is None:
            continue
        drop = plr_kind != _KIND_STATICMETHOD
        for problem in compare_signatures(
            _signature(plr_fn, drop_first=drop), _signature(shim_fn, drop_first=drop)
        ):
            out.append(Violation(target, "member", where, problem))
    return out


# --- 2/3. source scan: call sites, instance usage, import routing ---------------


def instance_attributes(cls: type) -> set[str]:
    """Names ``cls`` assigns on ``self`` anywhere in its own (and its bases') source."""
    names: set[str] = set()
    for klass in cls.__mro__:
        if klass is object:
            continue
        try:
            source = inspect.getsource(klass)
        except (OSError, TypeError):
            continue
        tree = ast.parse(_dedent(source))
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            for t in targets:
                if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                    names.add(t.attr)
    return names


def _dedent(source: str) -> str:
    import textwrap

    return textwrap.dedent(source)


def _module_name_for(path: Path, package_root: Path) -> str:
    rel = path.relative_to(package_root.parent).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_from(module: str, level: int, current: str, is_package: bool) -> str:
    if level == 0:
        return module or ""
    base = current.split(".")
    if not is_package:
        base = base[:-1]
    if level > 1:
        base = base[: len(base) - (level - 1)]
    return ".".join([*base, module] if module else base)


def _is_test_path(path: Path) -> bool:
    return (
        "tests" in path.parts
        or path.name.startswith("test_")
        or path.name.endswith("_tests.py")
        or path.name.endswith("_test.py")
    )


class _Placeholder:
    """Stand-in argument value for ``Signature.bind``; never inspected."""


def _bind(sig: inspect.Signature, call: ast.Call) -> str | None:
    """Bind a call's argument *shape* to ``sig``. None on success, else the error.

    Starred / double-starred arguments cannot be bound statically; when present,
    only what is known is checked (explicit keywords must be accepted).
    """
    has_star = any(isinstance(a, ast.Starred) for a in call.args)
    has_dstar = any(k.arg is None for k in call.keywords)
    kwargs = {k.arg: _Placeholder() for k in call.keywords if k.arg is not None}
    if has_star or has_dstar:
        params = sig.parameters
        var_kw = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
        for name in kwargs:
            p = params.get(name)
            if (p is None or p.kind not in _KEYWORD) and not var_kw:
                return f"got an unexpected keyword argument {name!r}"
        return None
    args = [_Placeholder() for _ in call.args]
    try:
        sig.bind(*args, **kwargs)
    except TypeError as exc:
        return str(exc)
    return None


def _call_text(call: ast.Call) -> str:
    text = ast.unparse(call)
    return text if len(text) <= 160 else text[:157] + "..."


def scan_package(
    package_root: Path,
    pairs: Iterable[tuple[str, str, type, type]],
    report: Report,
    *,
    waivers: dict[tuple[str, str], str] = WAIVERS,
) -> None:
    """Scan ``package_root`` (the installed ``pylabrobot/`` dir) for checks 2 and 3.

    ``pairs`` is ``(plr_module, plr_class_name, plr_cls, shim_cls)``.
    """
    pairs = list(pairs)
    # Everything is keyed by the contract NAME from ``pairs`` (e.g. "USB"), never
    # by ``name`` -- the two only coincide by convention.
    by_origin = {(mod, name): (name, plr_cls, shim_cls) for mod, name, plr_cls, shim_cls in pairs}
    origin_modules = {mod for mod, _name, _p, _s in pairs}
    names = {name for _mod, name, _p, _s in pairs}
    for _mod, name, _p, _s in pairs:
        report.call_sites.setdefault(name, 0)
        report.usages.setdefault(name, 0)
    used_members: set[tuple[str, str]] = set()
    shim_attrs = {name: instance_attributes(shim) for _m, name, _p, shim in pairs}
    plr_attrs = {name: instance_attributes(plr) for _m, name, plr, _s in pairs}

    for path in sorted(package_root.rglob("*.py")):
        if _is_test_path(path.relative_to(package_root)):
            continue
        current = _module_name_for(path, package_root)
        if current in origin_modules:
            continue  # the class's own module (Validator subclasses etc.)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        rel = path.relative_to(package_root.parent).as_posix()
        is_pkg = path.name == "__init__.py"

        # local name -> (contract name, plr_cls, shim_cls); local module alias -> module path
        local: dict[str, tuple[str, type, type]] = {}
        mod_alias: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                source = _resolve_from(node.module or "", node.level, current, is_pkg)
                for alias in node.names:
                    if (source, alias.name) in by_origin:
                        local[alias.asname or alias.name] = by_origin[(source, alias.name)]
                    elif alias.name in names and source.startswith("pylabrobot.io"):
                        report.violations.append(
                            Violation(
                                alias.name,
                                "import",
                                f"{rel}:{node.lineno}",
                                f"`from {source} import {alias.name}` is not the binding "
                                "stages.apply() patches -- this backend would get the "
                                "native class in the browser",
                            )
                        )
                    elif source in origin_modules:
                        mod_alias.setdefault(alias.asname or alias.name, f"{source}.{alias.name}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in origin_modules and alias.asname:
                        mod_alias[alias.asname] = alias.name

        def resolve(func: ast.expr) -> tuple[str, type, type] | None:
            if isinstance(func, ast.Name):
                return local.get(func.id)
            if isinstance(func, ast.Attribute):
                dotted = _dotted(func.value)
                if dotted is None:
                    return None
                head, _, rest = dotted.partition(".")
                module = mod_alias.get(head, head) + (f".{rest}" if rest else "")
                return by_origin.get((module, func.attr))
            return None

        if not local and not mod_alias and "pylabrobot.io" not in path.read_text(encoding="utf-8"):
            continue

        # 2. constructor call sites, anywhere in the file
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                hit = resolve(node.func)
                if hit is None:
                    continue
                name, plr_cls, shim_cls = hit
                target = f"{name} -> {shim_cls.__name__}"
                where = f"{rel}:{node.lineno}"
                report.call_sites[name] += 1
                own = _bind(_signature(plr_cls.__init__, drop_first=True), node)
                if own is not None:
                    report.violations.append(
                        Violation(
                            target,
                            "scanner",
                            where,
                            f"call does not even bind against pylabrobot's own "
                            f"{name}: {own} -- {_call_text(node)}",
                        )
                    )
                    continue
                err = _bind(_signature(shim_cls.__init__, drop_first=True), node)
                if err is not None:
                    report.violations.append(
                        Violation(target, "call-site", where, f"{err} -- {_call_text(node)}")
                    )

        # 3. instance usage, per class that stores one of the targets on self
        for cls_node in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            holders: dict[str, tuple[str, type, type]] = {}
            for node in ast.walk(cls_node):
                if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                    found = [resolve(c.func) for c in ast.walk(node.value) if isinstance(c, ast.Call)]
                    found = [f for f in found if f is not None]
                    if not found:
                        continue
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for t in targets:
                        if (
                            isinstance(t, ast.Attribute)
                            and isinstance(t.value, ast.Name)
                            and t.value.id == "self"
                        ):
                            holders[t.attr] = found[0]
            if not holders:
                continue
            calls_by_func = {
                id(n.func): n for n in ast.walk(cls_node) if isinstance(n, ast.Call)
            }
            for node in ast.walk(cls_node):
                if not (
                    isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Attribute)
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id == "self"
                    and node.value.attr in holders
                ):
                    continue
                name, plr_cls, shim_cls = holders[node.value.attr]
                member = node.attr
                target = f"{name} -> {shim_cls.__name__}"
                where = f"{rel}:{node.lineno} ({cls_node.name}.{node.value.attr}.{member})"
                key = (name, member)
                if key not in used_members:
                    used_members.add(key)
                    report.usages[name] += 1
                plr_has = member_kind(plr_cls, member) is not None or member in plr_attrs[name]
                shim_has = member_kind(shim_cls, member) is not None or member in shim_attrs[name]
                if not shim_has:
                    why = " (waived as unused, but it IS used)" if key in waivers else ""
                    report.violations.append(
                        Violation(target, "usage", where, f"shim has no {member!r}{why}")
                    )
                    continue
                if not plr_has:
                    continue  # duck-typed access pylabrobot itself doesn't define
                call = calls_by_func.get(id(node))
                shim_fn = _callable_for(shim_cls, member) if member_kind(shim_cls, member) else None
                plr_fn = _callable_for(plr_cls, member) if member_kind(plr_cls, member) else None
                if call is None or shim_fn is None or plr_fn is None:
                    continue
                drop = member_kind(plr_cls, member) != _KIND_STATICMETHOD
                if _bind(_signature(plr_fn, drop_first=drop), call) is not None:
                    continue  # pylabrobot's own call is off-contract; not the shim's problem
                err = _bind(_signature(shim_fn, drop_first=drop), call)
                if err is not None:
                    report.violations.append(
                        Violation(target, "usage", where, f"{err} -- {_call_text(call)}")
                    )

    for (cls_name, member) in waivers:
        if cls_name in names and (cls_name, member) not in used_members:
            report.waived_unused.append(f"{cls_name}.{member}")


def _dotted(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = _dotted(node.value)
        return f"{head}.{node.attr}" if head else None
    return None


# --- driver ---------------------------------------------------------------------


def run(shims_dir: Path, *, min_call_sites: int = 1) -> Report:
    if str(shims_dir) not in sys.path:
        sys.path.insert(0, str(shims_dir))
    import pylabrobot

    report = Report(plr_file=pylabrobot.__file__)
    pairs = []
    for plr_mod, plr_name, shim_mod, shim_name in TARGETS:
        plr_cls = getattr(importlib.import_module(plr_mod), plr_name)
        shim_cls = getattr(importlib.import_module(shim_mod), shim_name)
        report.violations.extend(check_members(plr_cls, shim_cls))
        pairs.append((plr_mod, plr_name, plr_cls, shim_cls))
    scan_package(Path(pylabrobot.__file__).parent, pairs, report)
    # Non-vacuousness: a scanner that silently matches nothing passes everything.
    for name, count in report.call_sites.items():
        if count < min_call_sites:
            report.violations.append(
                Violation(
                    name,
                    "scanner",
                    "pylabrobot/",
                    f"found {count} constructor call sites (< {min_call_sites}); the "
                    "scanner is not seeing this class's users",
                )
            )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--shims-dir", type=Path, required=True)
    parser.add_argument("--json", type=Path, help="Also write the full report here.")
    args = parser.parse_args(argv)
    report = run(args.shims_dir.resolve())
    if args.json:
        args.json.write_text(report.to_json(), encoding="utf-8")
    print("PYLABROBOT_FILE=" + report.plr_file)
    print("CALL_SITES " + json.dumps(report.call_sites, sort_keys=True))
    print("USAGES " + json.dumps(report.usages, sort_keys=True))
    if report.waived_unused:
        print("WAIVED_UNUSED " + ", ".join(report.waived_unused))
    if report.violations:
        for v in report.violations:
            print("SHIM-CONTRACT-FAIL " + str(v), file=sys.stderr)
        print(f"SHIM-CONTRACT-FAIL {len(report.violations)} violation(s)", file=sys.stderr)
        return 1
    print("SHIM-CONTRACT-OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
