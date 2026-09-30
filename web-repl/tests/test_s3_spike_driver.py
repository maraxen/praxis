"""No-browser plumbing checks for the S3 spike driver (epic 260929_notebook-display-design, A3).

``scripts/spikes/260929_s3_ipython_hooks.py`` is the pre-registered S3 probe. Nothing here
launches Playwright or Chromium and nothing here measures S3: it proves the DRIVER, UNIT,
STAMP, RESUME, COMPLETENESS and OUTCOME-GATING plumbing (D17) against a stub probe, and it
proves the PROBE LOGIC against a fake IPython kernel, so that when the real run happens a
plumbing or reader bug cannot be mistaken for a finding.

Three layers, none of which touches a browser:

* Plumbing (real subprocesses). Every unit runs as a REAL subprocess
  (``scripts/unit_runner.run_unit``, real ``Watchdog``, real stamps) started through a tiny
  stub launcher that loads the driver by path and swaps in a stub probe / session / input
  environment. Timeouts are shrunk through the ``main(..., unit_timeout_s=, driver_extra_s=)``
  parameters (never a CLI flag: the real budget is fixed at 10 min and pre-registered).
* Probe logic against a FAKE KERNEL (in-process). The real kernel cell sources (the ones the
  spike seeds into its notebook) are executed against a small fake of IPython's shell, modelled
  on IPython 9.12.0 ``core/interactiveshell.py`` and ``core/formatters.py`` and on
  ``pyodide_kernel-0.8.2``'s ``Interpreter`` (custom-exception return value discarded; the
  post-run events only in the sync ``run_cell``; ``status`` derived from ``_last_traceback``).
  Each variant of the fake (everything works; formatter metadata dropped; handler return
  ignored; instance ``showtraceback`` not honoured; ...) must land on the pre-registered
  branch, and each CONTROL must be able to say no: a fake whose handler swallows the
  unregistered class makes the negative control fail (``invalid``), a Run All that never stops
  makes the control read False, an unmeasured cell reads None, never a branch.
* The in-page JS (run under ``bun`` when present) against a fake notebook model.
"""

from __future__ import annotations

import ast
import asyncio
import dataclasses
import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
import types
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "spikes" / "260929_s3_ipython_hooks.py"
SIDECAR_PATH = DRIVER_PATH.with_suffix(".bth.toml")
UNIT = "ipython_hooks"

pytestmark = pytest.mark.timeout(180)


@pytest.fixture(scope="module")
def s3():
    spec = importlib.util.spec_from_file_location("s3_driver_under_test", DRIVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["s3_driver_under_test"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# A fake IPython kernel (modelled on IPython 9.12.0 + pyodide_kernel 0.8.2)
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class Knobs:
    bundle_metadata: bool = True  # the mimebundle formatter's metadata reaches the output
    html_tuple: bool = True  # a per-type text/html function's (html, md) tuple is unpacked
    custom_tb_return_used: bool = False  # IPython discards CustomTB's return: False (real)
    post_run_cell_on_async: bool = False  # IPython triggers post_run_cell only in run_cell: False (real)
    wrapper_honoured: bool = True  # run_code calls the INSTANCE's showtraceback
    handle_all: bool = False  # a broken hook that also swallows unregistered classes
    no_ip: bool = False  # get_ipython() is None
    stop_on_error: bool = True  # the kernel aborts the rest of a Run block after an error reply
    idle: bool = True
    warm_raises: bool = False
    hang_cell: str | None = None  # this cell's run never settles
    raise_on: tuple[str, ...] = ()  # the driver itself raises for these cells


ALL_YES = Knobs(custom_tb_return_used=True, post_run_cell_on_async=True)
REAL_LIKE = Knobs()  # what reading the IPython / pyodide-kernel source predicts


class FakeEvents:
    def __init__(self) -> None:
        self.cbs: dict[str, list[Any]] = {}

    def register(self, name: str, fn: Any) -> None:
        self.cbs.setdefault(name, []).append(fn)

    def unregister(self, name: str, fn: Any) -> None:
        self.cbs[name].remove(fn)

    def trigger(self, name: str, *args: Any) -> None:
        for fn in list(self.cbs.get(name, [])):
            fn(*args)


class FakeFormatter:
    def __init__(self) -> None:
        self.reg: dict[type, Any] = {}

    def for_type(self, typ: type, func: Any = None) -> None:
        self.reg[typ] = func

    def lookup(self, obj: Any) -> Any:
        for t in type(obj).__mro__:
            if t in self.reg:
                return self.reg[t]
        raise KeyError(type(obj))


class FakePrinter:
    def __init__(self) -> None:
        self.buf: list[str] = []

    def text(self, s: str) -> None:
        self.buf.append(s)


class FakeDisplayFormatter:
    """IPython ``DisplayFormatter.format`` (formatters.py:196-256), reduced."""

    def __init__(self, knobs: Knobs) -> None:
        self.k = knobs
        self.mimebundle_formatter = FakeFormatter()
        self.formatters = {"text/plain": FakeFormatter(), "text/html": FakeFormatter()}

    def format(self, obj: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        fd: dict[str, Any] = {}
        md: dict[str, Any] = {}
        try:
            bundle = self.mimebundle_formatter.lookup(obj)
        except KeyError:
            bundle = None
        if bundle is not None:
            r = bundle(obj)
            fd, md = r if isinstance(r, tuple) else (r, {})
            fd, md = dict(fd), dict(md)
            if not self.k.bundle_metadata:
                md = {}
        for fmt, f in self.formatters.items():
            try:
                registered = f.lookup(obj)
            except KeyError:
                registered = None
            if fmt in fd and registered is None:
                continue
            data: Any = None
            one_md: Any = None
            if registered is not None:
                if fmt == "text/plain":
                    p = FakePrinter()
                    registered(obj, p, False)
                    data = "".join(p.buf)
                else:
                    r = registered(obj)
                    if isinstance(r, tuple) and len(r) == 2 and self.k.html_tuple:
                        data, one_md = r
                    else:
                        data = r
            elif fmt == "text/html":
                method = getattr(obj, "_repr_html_", None)
                data = method() if method else None
            else:
                data = repr(obj)
            if data is not None:
                fd[fmt] = data
            if one_md is not None:
                md[fmt] = one_md
        return fd, md


class _Info:
    def __init__(self, raw: str) -> None:
        self.raw_cell = raw


class _Result:
    def __init__(self, info: _Info, success: bool, count: int) -> None:
        self.info, self.success, self.execution_count = info, success, count


CURRENT: dict[str, Any] = {}


def _fake_display(*objs: Any, raw: bool = False, metadata: dict | None = None, **_kw: Any) -> None:
    shell = CURRENT["shell"]
    for obj in objs:
        if raw:
            data, md = dict(obj), dict(metadata or {})
        else:
            data, md = shell.display_formatter.format(obj)
            md.update(metadata or {})
        shell.outputs.append({"output_type": "display_data", "data": data, "metadata": md})


class FakeKernelObj:
    def __init__(self, shell: FakeShell) -> None:
        self.shell = shell

    def run(self, code: str) -> dict[str, Any]:
        sh = self.shell
        sh._last_traceback = None
        if sh.should_run_async(code):
            asyncio.run(sh.run_cell_async(code))
        else:
            sh.run_cell(code)
        if sh._last_traceback is None:
            return {"status": "ok"}
        return {"status": "error", **sh._last_traceback}


class FakeShell:
    def __init__(self, knobs: Knobs) -> None:
        self.k = knobs
        self.execution_count = 1
        self.events = FakeEvents()
        self.display_formatter = FakeDisplayFormatter(knobs)
        self._custom_exceptions: tuple = ()
        self.CustomTB = None
        self.autoawait = True
        self.kernel = FakeKernelObj(self)
        self._last_traceback: dict[str, Any] | None = None
        self._custom_stb: list[str] = []
        self.outputs: list[dict[str, Any]] = []
        self.user_ns: dict[str, Any] = {}
        self.set_custom_exc((), None)

    @property
    def custom_exceptions(self) -> tuple:
        if self.k.handle_all and self._custom_exceptions:
            return (BaseException,)
        return self._custom_exceptions

    def set_custom_exc(self, exc_tuple: tuple, handler: Any) -> None:
        if not isinstance(exc_tuple, tuple):
            raise TypeError("The custom exceptions must be given as a tuple.")

        def wrapped(etype, value, tb, tb_offset=None):
            stb = handler(self, etype, value, tb, tb_offset=tb_offset) if handler else []
            if stb is None:
                stb = []
            assert isinstance(stb, list) and all(isinstance(x, str) for x in stb)
            self._custom_stb = stb
            return stb

        self.CustomTB = wrapped
        self._custom_exceptions = exc_tuple

    def should_run_async(self, code: str, *a: Any, **k: Any) -> bool:
        return "await " in code

    def showtraceback(self, exc_tuple=None, filename=None, tb_offset=None, exception_only=False,
                      running_compiled_code=False):
        etype, value, _tb = exc_tuple or sys.exc_info()
        stb = [
            "-" * 30 + "\n" + f"{etype.__name__}{' ' * 20}Traceback (most recent call last)\n"
            f"Cell In[{self.execution_count}]\n{etype.__name__}: {value}"
        ]
        self._showtraceback(etype, value, stb)

    def _showtraceback(self, etype, evalue, stb):
        self._last_traceback = {"ename": str(etype), "evalue": str(evalue), "traceback": stb}

    def run_cell(self, source: str):
        result = None
        try:
            result = asyncio.run(self.run_cell_async(source))
        finally:
            self.events.trigger("post_execute")
            self.events.trigger("post_run_cell", result)
        return result

    async def run_cell_async(self, source: str):
        info = _Info(source)
        self.events.trigger("pre_execute")
        self.events.trigger("pre_run_cell", info)
        tree = ast.parse(source)
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last = tree.body[-1]
            tree.body[-1] = ast.copy_location(
                ast.Assign(targets=[ast.Name("__s3_last__", ast.Store())], value=last.value), last
            )
        ast.fix_missing_locations(tree)
        code_obj = compile(tree, "<cell>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        await self.run_code(code_obj)
        value = self.user_ns.pop("__s3_last__", None)
        if value is not None:
            data, md = self.display_formatter.format(value)
            self.outputs.append(
                {"output_type": "execute_result", "data": data, "metadata": md,
                 "execution_count": self.execution_count}
            )
        count = self.execution_count
        self.execution_count += 1
        self._async_epilogue(info, count)
        return _Result(info, self._last_traceback is None, count)

    def _async_epilogue(self, info, count):
        # the variant where the async path also triggers the post events (NOT what IPython 9.12 does)
        if self.k.post_run_cell_on_async:
            self.events.trigger("post_run_cell", _Result(info, True, count))

    async def run_code(self, code_obj):
        try:
            r = eval(code_obj, self.user_ns)
            if inspect.iscoroutine(r):
                await r
        except SystemExit:
            pass
        except self.custom_exceptions:
            etype, value, tb = sys.exc_info()
            self.CustomTB(etype, value, tb)
            if self.k.custom_tb_return_used:
                self._showtraceback(etype, value, self._custom_stb)
        except:  # noqa: E722 (mirrors IPython's run_code)
            if self.k.wrapper_honoured:
                self.showtraceback(running_compiled_code=True)
            else:
                type(self).showtraceback(self, running_compiled_code=True)


class FakeKernelDriver:
    """The ``PageKernelDriver`` interface over the fake kernel, executing the REAL cell sources."""

    pageerrors: list[str] = []

    def __init__(self, s3: Any, knobs: Knobs) -> None:
        self.s3, self.k = s3, knobs
        self.shell = FakeShell(knobs)
        self.shell.user_ns.update(
            {"__name__": "__main__", "get_ipython": (lambda: None) if knobs.no_ip else (lambda: self.shell)}
        )
        CURRENT["shell"] = self.shell
        self.sources = dict(s3.CELL_SOURCES)
        self.ran: list[str] = []

    def open(self) -> None:
        pass

    def wait_idle(self, timeout_s: float) -> bool:
        return self.k.idle

    def _exec(self, name: str) -> dict[str, Any]:
        if name in self.k.raise_on:
            raise RuntimeError(f"driver blew up on {name}")
        base = {"name": name, "index": self.s3.CELL_INDEX[name], "error": None, "execution_state": "idle",
                "seconds": 0.0}
        if name == self.k.hang_cell:
            return {**base, "state": "pending", "execution_count": None, "outputs": []}
        if name == "warm" and self.k.warm_raises:
            err = {"output_type": "error", "ename": "RuntimeError", "evalue": "praxis boot failed",
                   "traceback": ["RuntimeError: praxis boot failed"]}
            return {**base, "state": "rejected", "execution_count": 1, "outputs": [self.s3.trim_output(err)]}
        sh = self.shell
        sh.outputs = []
        count = sh.execution_count
        status = sh.kernel.run(self.sources[name])
        outs = list(sh.outputs)
        if status["status"] == "error":
            outs.append({"output_type": "error", "ename": status["ename"], "evalue": status["evalue"],
                         "traceback": status["traceback"]})
        outs = json.loads(json.dumps(outs, default=str))
        self.ran.append(name)
        return {**base, "state": "rejected" if status["status"] == "error" else "resolved",
                "execution_count": count, "outputs": [self.s3.trim_output(o) for o in outs]}

    def run_cell(self, name: str, timeout_s: float) -> dict[str, Any]:
        return self._exec(name)

    def run_block(self, names: tuple[str, ...], key: str, timeout_s: float) -> dict[str, Any]:
        recs = []
        aborted = False
        any_error = False
        for name in names:
            if aborted:
                recs.append({"name": name, "index": self.s3.CELL_INDEX[name], "error": None,
                             "execution_state": "idle", "seconds": 0.0, "state": "resolved",
                             "execution_count": None, "outputs": []})
                continue
            rec = self._exec(name)
            recs.append(rec)
            if any(o.get("output_type") == "error" for o in rec["outputs"]):
                any_error = True
                aborted = self.k.stop_on_error
        for rec in recs:
            rec["state"] = "rejected" if any_error else "resolved"
        return {"run": {"state": "rejected" if any_error else "resolved", "error": None, "seconds": 0.0},
                "cells": recs}


@pytest.fixture
def fake_ipython_modules(monkeypatch):
    ipy = types.ModuleType("IPython")
    ipy.__version__ = "9.12.0"
    disp = types.ModuleType("IPython.display")
    disp.display = _fake_display
    ipy.display = disp
    monkeypatch.setitem(sys.modules, "IPython", ipy)
    monkeypatch.setitem(sys.modules, "IPython.display", disp)


def run_fake(s3: Any, knobs: Knobs, *, deadline_s: float = 600.0) -> dict[str, Any]:
    kd = FakeKernelDriver(s3, knobs)
    return s3.run_hooks_probe(kd, time.monotonic() + deadline_s)


def derived(s3: Any, art: dict[str, Any]) -> dict[str, Any]:
    art = json.loads(json.dumps(art, default=str))  # what the unit writes and the driver reads
    return s3.derive_outcome_fields(art)


@pytest.fixture(scope="module")
def happy_fields(s3):
    """A complete probe artifact from the ALL_YES fake kernel (used by the plumbing tests)."""
    saved = {k: sys.modules.get(k) for k in ("IPython", "IPython.display")}
    ipy = types.ModuleType("IPython")
    ipy.__version__ = "9.12.0"
    disp = types.ModuleType("IPython.display")
    disp.display = _fake_display
    ipy.display = disp
    sys.modules["IPython"], sys.modules["IPython.display"] = ipy, disp
    try:
        return json.loads(json.dumps(run_fake(s3, ALL_YES), default=str))
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


# --------------------------------------------------------------------------- #
# The kernel cells themselves
# --------------------------------------------------------------------------- #


def test_kernel_cells_parse_with_top_level_await_and_await_cells_await(s3):
    names = [n for n, _ in s3.CELL_SOURCES]
    assert len(names) == len(set(names)) and names[0] == "warm"
    for name, source in s3.CELL_SOURCES:
        ast.parse(source)  # valid Python (top-level await parses; only compile needs the flag)
        compile(source, name, "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    for name, source in s3.CELL_SOURCES:
        if name.endswith("_await"):
            assert "await asyncio.sleep(0)" in source, name
        if name.endswith("_plain"):
            assert "await" not in source, name
    for names_ in s3.RUNALL_BLOCKS.values():
        assert all(n in s3.CELL_INDEX for n in names_)


def test_event_markers_appear_only_in_their_own_marker_cells(s3):
    for key, marker in s3.D_MARKERS.items():
        holders = [n for n, src in s3.CELL_SOURCES if marker in src]
        assert holders == [f"d_{key}"], (marker, holders)


def test_fixture_is_an_unexecuted_notebook_built_from_the_cells(s3):
    nb = s3.build_fixture()
    assert [c["id"] for c in nb["cells"]] == ["s3-" + n for n in s3.CELL_NAMES]
    assert all(c["execution_count"] is None and c["outputs"] == [] for c in nb["cells"])
    assert "".join(nb["cells"][1]["source"]) == dict(s3.CELL_SOURCES)["setup"]
    assert s3.sha256_bytes(s3.fixture_bytes()) == s3.sha256_bytes(s3.fixture_bytes())


def test_fixture_hash_changes_when_a_kernel_cell_changes(s3, monkeypatch):
    before = s3.sha256_bytes(s3.fixture_bytes())
    edited = tuple((n, src + "# edited\n") if n == "c_plain" else (n, src) for n, src in s3.CELL_SOURCES)
    monkeypatch.setattr(s3, "CELL_SOURCES", edited)
    assert s3.sha256_bytes(s3.fixture_bytes()) != before


# --------------------------------------------------------------------------- #
# The probe against a fake kernel: every branch, every control
# --------------------------------------------------------------------------- #


def test_all_yes_kernel_is_s3_a_and_valid(s3, fake_ipython_modules):
    art = run_fake(s3, ALL_YES)
    assert art["aborted"] is None and art["sub_errors"] == {}
    d = derived(s3, art)
    flat = d["flat"]
    assert flat["measurement_valid"] is True, d["details"]["validity_checks"]
    assert (flat["b_holds"], flat["b_prime_holds"], flat["c_holds"], flat["d_holds"]) == (True, True, True, True)
    assert flat["d1_branch"] == "S3-A" and flat["n_deviations"] == 0
    assert flat["get_ipython_present"] is True and flat["ipython_version"] == "9.12.0"
    assert flat["negative_control_failed_as_required"] is True
    assert flat["runall_control_stops"] is True and flat["runall_custom_stops"] is True
    assert art["get_ipython_present"] is True and art["all_cells_done"] is True and art["deadline_hit"] is False


def test_real_like_kernel_lands_on_s3_c_and_s3_d(s3, fake_ipython_modules):
    """What reading the IPython 9.12 / pyodide-kernel 0.8.2 source predicts: a custom-exception
    handler's return is discarded so no error output and Run All does not stop (S3-C, and the
    instance ``showtraceback`` wrapper holds); ``post_run_cell`` fires for a plain cell but not
    for a top-level-await cell (S3-D). The carrier hooks work. NOT a measurement of the dist.
    """
    art = run_fake(s3, REAL_LIKE)
    d = derived(s3, art)
    flat, checks = d["flat"], d["details"]["validity_checks"]
    assert flat["measurement_valid"] is True, checks
    assert flat["b_holds"] is True and flat["b_prime_holds"] is True and flat["carrier_branch"] == "S3-A"
    assert flat["c_holds"] is False and flat["c_fallback_holds"] is True and flat["exc_branch"] == "S3-C"
    assert flat["d_holds"] is False and flat["events_branch"] == "S3-D"
    assert flat["d1_branch"] == "S3-C+S3-D" and flat["n_deviations"] == 2
    assert flat["runall_custom_stops"] is False and flat["runall_wrap_stops"] is True
    assert flat["runall_control_stops"] is True
    c_plain = art["c"]["modes"]["plain"]
    assert c_plain["invoked"] is True and c_plain["display_emitted"] is True
    assert c_plain["error_output_present"] is False and c_plain["ok"] is False
    d_art = art["d"]
    assert d_art["fired_plain"] is True and d_art["fired_await"] is False
    assert d_art["fired_after_unregister"] is False
    assert d_art["pre_run_cell_await"] is True  # pre_run_cell does fire for await cells
    ev = art["path_evidence"]
    assert ev["run_code"]["has_custom_branch"] is True
    assert ev["kernel_run_status_from_last_traceback"] is True
    assert ev["run_cell_triggers_post_run_cell"] is True and ev["run_cell_async_triggers_post_run_cell"] is False


def test_bundle_metadata_dropped_but_html_carrier_holds_is_s3_b(s3, fake_ipython_modules):
    art = run_fake(s3, dataclasses.replace(ALL_YES, bundle_metadata=False))
    flat = derived(s3, art)["flat"]
    assert flat["measurement_valid"] is True
    assert flat["b_holds"] is False and flat["b_prime_holds"] is True
    assert flat["carrier_branch"] == "S3-B" and flat["d1_branch"] == "S3-B" and flat["n_deviations"] == 1
    # the stamp DID arrive nested for (b') and NOT at the top level for (b)
    assert art["b_prime"]["modes"]["plain"]["stamp_nested_ok"] is True
    assert art["b"]["modes"]["plain"]["stamp_top"] is None and art["b"]["modes"]["plain"]["html_ok"] is True


def test_both_carriers_failing_is_the_b7_b9_stop(s3, fake_ipython_modules):
    art = run_fake(s3, dataclasses.replace(ALL_YES, bundle_metadata=False, html_tuple=False))
    flat = derived(s3, art)["flat"]
    assert flat["measurement_valid"] is True
    assert flat["b_holds"] is False and flat["b_prime_holds"] is False
    assert flat["carrier_branch"] == "STOP" and flat["d1_branch"] == "STOP-B7B9"


def test_custom_exc_and_wrapper_both_failing_is_the_b6_stop(s3, fake_ipython_modules):
    art = run_fake(s3, dataclasses.replace(REAL_LIKE, wrapper_honoured=False))
    flat = derived(s3, art)["flat"]
    assert flat["measurement_valid"] is True
    assert flat["c_holds"] is False and flat["c_fallback_holds"] is False
    assert flat["exc_branch"] == "STOP" and "STOP-B6" in flat["d1_branch"]


def test_a_kernel_where_run_all_never_stops_reports_the_premise_failure(s3, fake_ipython_modules):
    """The control (a DEFAULT error) does not stop Run All either: the instrument said "does not
    stop" (so it is valid), the run-all clause is waived from (c)/(c'), and the premise failure
    is reported separately.
    """
    art = run_fake(s3, dataclasses.replace(ALL_YES, stop_on_error=False))
    d = derived(s3, art)
    flat = d["flat"]
    assert flat["runall_control_stops"] is False and flat["measurement_valid"] is True, d["details"]
    assert flat["c_holds"] is True  # clause waived; the other clauses hold
    assert flat["runall_custom_stops"] is False


def test_negative_control_fails_when_a_broken_hook_swallows_the_unregistered_class(s3, fake_ipython_modules):
    """A hook that handles EVERY exception fails the D17 negative control: the run is invalid
    and no branch may be cited from it.
    """
    art = run_fake(s3, dataclasses.replace(ALL_YES, handle_all=True))
    d = derived(s3, art)
    flat = d["flat"]
    assert flat["negative_control_failed_as_required"] is False
    assert flat["measurement_valid"] is False
    assert d["details"]["validity_checks"]["negative_control_failed_as_required"] is False
    neg = art["negative_control"]["cases"]["custom_plain"]
    assert neg["handled_by_hook"] is True and neg["failed_as_required"] is False


def test_negative_control_reaches_the_default_traceback_when_the_hooks_are_scoped(s3, fake_ipython_modules):
    art = run_fake(s3, REAL_LIKE)
    cases = art["negative_control"]["cases"]
    assert set(cases) == {"custom_plain", "custom_await", "wrap_plain", "wrap_await"}
    for name, case in cases.items():
        assert case["failed_as_required"] is True, name
        assert case["default_traceback_reached"] is True and case["handler_display_present"] is False
    assert cases["wrap_plain"]["seen_by_hook"] is True and cases["wrap_plain"]["handled_by_hook"] is False
    assert cases["custom_plain"]["seen_by_hook"] is False
    assert art["negative_control"]["failed_as_required"] is True


def test_negative_control_that_errors_has_not_failed_as_required(s3, fake_ipython_modules):
    """The driver raising while reading the control's kernel-side call list is a sub-probe
    ``error`` finding: the control is unmeasured (None), NOT failed-as-required, and invalid.
    """
    art = run_fake(s3, dataclasses.replace(ALL_YES, raise_on=("c_calls",)))
    assert list(art["sub_errors"]) == ["c"] and art["sub_errors"]["c"]["type"] == "RuntimeError"
    assert art["negative_control"]["failed_as_required"] is None
    d = derived(s3, art)
    assert d["flat"]["negative_control_failed_as_required"] is None
    assert d["flat"]["measurement_valid"] is False
    assert d["flat"]["n_error_units"] == 0  # the unit-level lift happens in run_unit_mode (below)
    assert art["b_prime"] is not None, "later sub-probes still ran and kept their evidence"


def test_no_get_ipython_makes_every_hook_verdict_false_and_is_its_own_outcome_input(s3, fake_ipython_modules):
    art = run_fake(s3, dataclasses.replace(ALL_YES, no_ip=True))
    d = derived(s3, art)
    flat = d["flat"]
    assert flat["get_ipython_present"] is False
    assert (flat["b_holds"], flat["b_prime_holds"], flat["c_holds"], flat["d_holds"]) == (False,) * 4
    assert flat["measurement_valid"] is True, d["details"]["validity_checks"]


def test_kernel_that_never_idles_aborts_and_is_invalid_with_nulls(s3, fake_ipython_modules):
    art = run_fake(s3, dataclasses.replace(ALL_YES, idle=False))
    assert art["kernel_ready"] is False and art["aborted"] == "kernel_not_idle"
    assert art["cells"] == {} and art["a"] is None and art["c"] is None
    flat = derived(s3, art)["flat"]
    assert flat["measurement_valid"] is False
    assert flat["b_holds"] is None and flat["c_holds"] is None and flat["d1_branch"] is None


def test_a_warmup_error_aborts_and_is_invalid(s3, fake_ipython_modules):
    art = run_fake(s3, dataclasses.replace(ALL_YES, warm_raises=True))
    assert art["boot"]["warmup_error"]["evalue"] == "praxis boot failed"
    assert art["aborted"] == "warmup_failed" and art["prelude"]["ok"] is False
    assert derived(s3, art)["flat"]["measurement_valid"] is False
    assert art["cells"]["setup"]["state"] == "skipped"


def test_a_cell_that_never_settles_aborts_the_rest(s3, fake_ipython_modules):
    art = run_fake(s3, dataclasses.replace(ALL_YES, hang_cell="b_plain"))
    assert art["aborted"] == "cell_timeout:b_plain"
    assert art["cells"]["b_await"]["state"] == "skipped"
    flat = derived(s3, art)["flat"]
    assert flat["measurement_valid"] is False and flat["b_holds"] is None and art["all_cells_done"] is False


def test_a_hit_deadline_records_it_and_is_invalid(s3, fake_ipython_modules):
    art = run_fake(s3, ALL_YES, deadline_s=-5.0)
    assert art["deadline_hit"] is True and art["aborted"] is not None
    assert derived(s3, art)["flat"]["measurement_valid"] is False


def test_every_preregistered_field_is_returned_even_when_unmeasured(s3, fake_ipython_modules):
    for knobs in (ALL_YES, dataclasses.replace(ALL_YES, idle=False), dataclasses.replace(ALL_YES, warm_raises=True)):
        art = run_fake(s3, knobs)
        assert set(s3.UNIT_BY_NAME[UNIT].required) <= set(art)


def test_collect_sub_probes_catches_a_raise_and_keeps_the_others(s3):
    def boom(_r):
        raise ValueError("kaboom")

    results, errs = s3.collect_sub_probes({"x": lambda r: 1, "y": boom, "z": lambda r: r["x"] + 1})
    assert results == {"x": 1, "y": None, "z": 2}
    assert list(errs) == ["y"] and errs["y"]["type"] == "ValueError" and errs["y"]["message"] == "kaboom"
    assert 0 < len(errs["y"]["traceback_tail"].encode()) <= 4096


# --------------------------------------------------------------------------- #
# Pure readers: each can say no
# --------------------------------------------------------------------------- #


def _rec(outputs, count=3, state="resolved"):
    return {"state": state, "execution_count": count, "outputs": outputs}


def _bundle_out(prefix, mode, *, top=None, nested=None, html=True, kind="display_data"):
    md = {}
    if top is not None:
        md["praxis"] = top
    if nested is not None:
        md["text/html"] = {"praxis": nested}
    data = {"text/plain": "x"}
    if html:
        data["text/html"] = f"<b>{prefix}{mode}</b>"
    return {"output_type": kind, "data": data, "metadata": md}


def test_judge_carrier_reads_top_level_nested_and_absent_stamps(s3):
    stamp = {**s3.B_STAMP, "exec": 3}
    top = s3.judge_carrier(_rec([_bundle_out("s3-b-", "plain", top=stamp)]), prefix="s3-b-", mode="plain", static=s3.B_STAMP, carrier="top")
    assert top["measured"] and top["html_ok"] and top["carrier_ok"] and top["exec_matches_cell"] is True
    nested = s3.judge_carrier(_rec([_bundle_out("s3-b-", "plain", nested=stamp)]), prefix="s3-b-", mode="plain", static=s3.B_STAMP, carrier="top")
    assert nested["stamp_nested_ok"] is True and nested["carrier_ok"] is False  # right stamp, wrong place
    none = s3.judge_carrier(_rec([_bundle_out("s3-b-", "plain")]), prefix="s3-b-", mode="plain", static=s3.B_STAMP, carrier="top")
    assert none["measured"] and none["carrier_ok"] is False and none["stamp_top"] is None
    assert s3.judge_carrier(_rec([_bundle_out("s3-b-", "plain", top=stamp)]), prefix="s3-b-", mode="plain", static=s3.B_STAMP, carrier="html")["carrier_ok"] is False
    nothing = s3.judge_carrier(_rec([]), prefix="s3-b-", mode="plain", static=s3.B_STAMP, carrier="top")
    assert nothing["measured"] is False  # no output to inspect: never a claim


@pytest.mark.parametrize(
    "stamp",
    [
        {"v": 1, "kind": "plate", "resource": "s3-plate", "rev": 7, "session": "WRONG", "exec": 3},
        {"v": 1, "kind": "plate", "resource": "s3-plate", "rev": 7, "session": "s3-session-b", "exec": True},
        {"v": 1, "kind": "plate", "resource": "s3-plate", "rev": 7, "session": "s3-session-b", "exec": "3"},
        {"v": 1, "kind": "plate", "resource": "s3-plate", "rev": 7, "session": "s3-session-b"},
    ],
)
def test_a_wrong_or_partial_stamp_is_not_a_carrier(s3, stamp):
    j = s3.judge_carrier(_rec([_bundle_out("s3-b-", "plain", top=stamp)]), prefix="s3-b-", mode="plain", static=s3.B_STAMP, carrier="top")
    assert j["measured"] is True and j["carrier_ok"] is False


def test_judge_carrier_without_our_html_inspects_the_first_display_and_says_html_not_ok(s3):
    stamp = {**s3.B_STAMP, "exec": 3}
    j = s3.judge_carrier(_rec([_bundle_out("s3-b-", "plain", top=stamp, html=False)]), prefix="s3-b-", mode="plain", static=s3.B_STAMP, carrier="top")
    assert j["measured"] is True and j["html_ok"] is False
    assert s3.combine_carrier({"error": None}, {"plain": j, "await": j}, ("error",)) is False


def test_unstamped_control_can_say_absent_and_can_catch_a_reader_that_invents_a_stamp(s3):
    plain = {"output_type": "display_data", "data": {"text/html": "<i>s3-repr</i>"}, "metadata": {}}
    assert s3.judge_unstamped_control(_rec([plain]))["reads_none"] is True
    stamped = {**plain, "metadata": {"praxis": {"v": 1}}}
    assert s3.judge_unstamped_control(_rec([stamped]))["reads_none"] is False
    nested = {**plain, "metadata": {"text/html": {"praxis": {"v": 1}}}}
    assert s3.judge_unstamped_control(_rec([nested]))["reads_none"] is False
    assert s3.judge_unstamped_control(_rec([]))["measured"] is False


def test_emit_payload_prefers_json_falls_back_to_text_and_ignores_other_tags(s3):
    as_json = {"output_type": "display_data", "data": {"application/json": {"tag": "a", "x": 1}}, "metadata": {"s3": "a"}}
    as_text = {"output_type": "display_data", "data": {"text/plain": '{"tag": "b", "y": 2}'}, "metadata": {"s3": "b"}}
    other = {"output_type": "display_data", "data": {"application/json": {"tag": "c"}}, "metadata": {"s3": "c"}}
    assert s3.emit_payload([as_json, as_text, other], "a") == ({"tag": "a", "x": 1}, "application/json")
    assert s3.emit_payload([as_json, as_text, other], "b") == ({"tag": "b", "y": 2}, "text/plain")
    assert s3.emit_payload([as_json, as_text, other], "zzz") == (None, None)
    junk = {"output_type": "display_data", "data": {"text/plain": "not json"}, "metadata": {"s3": "j"}}
    assert s3.emit_payload([junk], "j") == (None, None)
    stream = {"output_type": "stream", "name": "stdout", "text": '{"tag": "a"}'}
    assert s3.emit_payload([stream], "a") == (None, None), "printed text is never a measurement"


def test_trim_output_never_truncates_the_probes_own_bundles_but_bounds_foreign_ones(s3):
    big = {"tag": "d_events", "events": ["x" * 100] * 200}
    own = {"output_type": "display_data", "data": {"application/json": big}, "metadata": {"s3": "d_events"}}
    foreign = {"output_type": "display_data", "data": {"application/json": big}, "metadata": {}}
    assert s3.trim_output(own)["data"]["application/json"] == big
    assert "_truncated" in s3.trim_output(foreign)["data"]["application/json"]
    err = {"output_type": "error", "ename": "E", "evalue": "v", "traceback": ["l" * 5000] * 40}
    t = s3.trim_output(err)
    assert len(t["traceback"]) == 24 and all(len(x) < 2200 for x in t["traceback"])


def _exc_rec(outputs, count=4):
    return _rec(outputs, count=count)


def _err(ename, tb):
    return {"output_type": "error", "ename": ename, "evalue": "v", "traceback": tb}


def _shown(tag, value):
    return {"output_type": "display_data", "data": {"application/json": {"tag": tag, "value": value}}, "metadata": {"s3": tag}}


def test_judge_exc_requires_invocation_display_and_the_returned_traceback(s3):
    line = "S3CustomError: s3-c-plain"
    good = _exc_rec([_shown("c_handler_display", "s3-c-plain"), _err("<class 'S3CustomError'>", [line])])
    calls = [{"value": "s3-c-plain"}]
    kw = dict(message="s3-c-plain", expected_line=line, display_tag="c_handler_display")
    assert s3.judge_exc(good, calls, **kw)["ok"] is True
    default_tb = _exc_rec([_shown("c_handler_display", "s3-c-plain"), _err("E", ["Traceback\nS3CustomError: s3-c-plain"])])
    j = s3.judge_exc(default_tb, calls, **kw)
    assert j["error_output_present"] is True and j["traceback_is_returned_stb"] is False and j["ok"] is False
    assert s3.judge_exc(_exc_rec([_err("E", [line])]), calls, **kw)["ok"] is False  # display did not emit
    assert s3.judge_exc(good, [], **kw)["ok"] is False  # handler was not invoked
    assert s3.judge_exc(_exc_rec([_shown("c_handler_display", "s3-c-plain")]), calls, **kw)["ok"] is False
    assert s3.judge_exc(good, None, **kw)["ok"] is None  # call list unreadable: unmeasured
    assert s3.judge_exc(_rec(good["outputs"], state="pending"), calls, **kw)["ok"] is None


def test_judge_default_control_rejects_a_handled_or_a_missing_default_traceback(s3):
    tb = ["----\nS3PlainError    Traceback (most recent call last)\nCell In[5]\nS3PlainError: m"]
    ok = _exc_rec([_err("<class 'S3PlainError'>", tb)])
    kw = dict(message="m", cls_name="S3PlainError", display_tag="c_handler_display")
    assert s3.judge_default(ok, [], **kw)["failed_as_required"] is True
    assert s3.judge_default(ok, [{"value": "m"}], **kw)["failed_as_required"] is False  # handler saw and handled it
    assert s3.judge_default(ok, [{"value": "m", "handled": False}], **kw)["failed_as_required"] is True  # wrapper passed it on
    shown = _exc_rec([_shown("c_handler_display", "m"), _err("E", tb)])
    assert s3.judge_default(shown, [], **kw)["failed_as_required"] is False
    one_line = _exc_rec([_err("E", ["S3PlainError: m"])])  # no default traceback header
    assert s3.judge_default(one_line, [], **kw)["failed_as_required"] is False
    assert s3.judge_default(_exc_rec([]), [], **kw)["failed_as_required"] is False  # no error output at all
    assert s3.judge_default(ok, None, **kw)["failed_as_required"] is None  # unmeasured


def _blk(s3, ran, counts, raiser_error=True, state="resolved"):
    names = ("n1", "n2", "n3")
    mk = lambda n, on: [{"output_type": "display_data", "data": {"application/json": {"name": n}}, "metadata": {"s3": "ra"}}] if on else []
    cells = [
        {"execution_count": counts[0], "outputs": mk("n1", ran[0])},
        {"execution_count": counts[1], "outputs": [_err("E", ["x"])] if raiser_error else []},
        {"execution_count": counts[2], "outputs": mk("n3", ran[2])},
    ]
    return s3.judge_block(cells, {"state": state}, names)


def test_judge_block_stops_only_when_controlled(s3):
    assert _blk(s3, (True, True, False), (1, 2, None))["stops"] is True
    assert _blk(s3, (True, True, True), (1, 2, 3))["stops"] is False
    assert _blk(s3, (False, True, False), (None, 2, None))["stops"] is None  # first marker never ran
    assert _blk(s3, (True, True, False), (1, 2, 3))["stops"] is None  # count says it ran, no marker: inconsistent
    assert _blk(s3, (True, True, False), (1, 2, None), state="pending")["stops"] is None  # never settled
    assert _blk(s3, (True, True, False), (1, None, None), raiser_error=False)["stops"] is None  # raiser never ran


def test_judge_events_control_must_be_able_to_say_did_not_fire(s3):
    m = s3.D_MARKERS
    ev = lambda kind, key: {"kind": kind, "raw": "# " + m[key] + "\npass"}
    payload = {"events": [ev("post_run_cell", "plain"), ev("pre_run_cell", "await")], "post_execute": 4}
    d = s3.judge_events({"error": None}, payload)
    assert d["fired_plain"] is True and d["fired_await"] is False and d["fired_after_unregister"] is False
    assert d["pre_run_cell_await"] is True
    assert s3.combine_events(d) is False
    both = {"events": [ev("post_run_cell", "plain"), ev("post_run_cell", "await")]}
    assert s3.combine_events(s3.judge_events({"error": None}, both)) is True
    leaked = {"events": [ev("post_run_cell", k) for k in ("plain", "await", "after")]}
    assert s3.combine_events(s3.judge_events({"error": None}, leaked)) is None  # control fired: not trustworthy
    assert s3.combine_events(s3.judge_events({"error": None}, None)) is None  # unreadable
    assert s3.combine_events(s3.judge_events(None, both)) is None  # registration unread
    assert s3.combine_events(s3.judge_events({"error": "AttributeError()"}, both)) is False


def test_get_ipython_present_needs_both_modes_to_agree(s3):
    f = s3.get_ipython_present_from
    assert f({"plain": {"is_none": False}, "await": {"is_none": False}}) is True
    assert f({"plain": {"is_none": True}, "await": {"is_none": True}}) is False
    assert f({"plain": {"is_none": False}, "await": {"is_none": True}}) is None
    assert f({"plain": {"is_none": False}, "await": None}) is None and f(None) is None


def test_branch_tables(s3):
    assert (s3.carrier_branch(True, None), s3.carrier_branch(False, True), s3.carrier_branch(False, False)) == ("S3-A", "S3-B", "STOP")
    assert s3.carrier_branch(False, None) is None and s3.carrier_branch(None, True) is None
    assert (s3.exc_branch(True, False), s3.exc_branch(False, True), s3.exc_branch(False, False)) == ("S3-A", "S3-C", "STOP")
    assert s3.exc_branch(None, True) is None
    assert (s3.events_branch(True), s3.events_branch(False), s3.events_branch(None)) == ("S3-A", "S3-D", None)
    assert s3.runall_component(False, False) is True and s3.runall_component(False, True) is False
    assert s3.runall_component(None, True) is None


BATHOS_PY = Path.home() / ".local" / "share" / "uv" / "tools" / "bathos" / "bin" / "python"

OUTCOME_CASES = {
    "all_yes": (ALL_YES, "s3_a"),
    "real_like": (REAL_LIKE, "s3_combined"),  # S3-C + S3-D
    "carrier_b": (dataclasses.replace(ALL_YES, bundle_metadata=False), "s3_b"),
    "carriers_fail": (dataclasses.replace(ALL_YES, bundle_metadata=False, html_tuple=False), "stop_b7_b9"),
    "exc_only": (dataclasses.replace(ALL_YES, custom_tb_return_used=False), "s3_c"),
    "events_only": (dataclasses.replace(ALL_YES, post_run_cell_on_async=False), "s3_d"),
    "exc_stop": (dataclasses.replace(REAL_LIKE, wrapper_honoured=False, post_run_cell_on_async=True), "stop_b6"),
    "no_run_all_stop": (dataclasses.replace(ALL_YES, stop_on_error=False), "runall_premise_fails"),
    "control_fails": (dataclasses.replace(ALL_YES, handle_all=True), "invalid"),
    "no_ip": (dataclasses.replace(ALL_YES, no_ip=True), "s3_no_ipython"),
    "not_idle": (dataclasses.replace(ALL_YES, idle=False), "invalid"),
    "warm_error": (dataclasses.replace(ALL_YES, warm_raises=True), "invalid"),
}


@pytest.mark.skipif(not BATHOS_PY.exists(), reason="needs the bathos uv-tool interpreter (not in CI)")
def test_sidecar_outcomes_select_the_expected_branch_for_every_fake_variant(s3, fake_ipython_modules, tmp_path):
    """The sidecar's outcome conditions, evaluated by bathos's own ``evaluate_outcome`` (DuckDB,
    first match in file order) over the flat fields each fake variant produces, select exactly
    the pre-registered branch. This proves the conditions parse and are exhaustive/exclusive
    over the cases; it says nothing about the real kernel.
    """
    flats = {}
    for name, (knobs, _label) in OUTCOME_CASES.items():
        flats[name] = derived(s3, run_fake(s3, knobs))["flat"]
    script = tmp_path / "eval_outcomes.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "from bathos.sidecar import parse_sidecar, evaluate_outcome\n"
        "sc = parse_sidecar(Path(sys.argv[1]))\n"
        "flats = json.loads(Path(sys.argv[2]).read_text())\n"
        "print(json.dumps({k: evaluate_outcome(sc, v) for k, v in flats.items()}))\n"
    )
    flats_path = tmp_path / "flats.json"
    flats_path.write_text(json.dumps(flats))
    proc = subprocess.run(
        [str(BATHOS_PY), str(script), str(SIDECAR_PATH), str(flats_path)],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    labels = json.loads(proc.stdout.strip().splitlines()[-1])
    assert labels == {name: label for name, (_k, label) in OUTCOME_CASES.items()}, labels


# --------------------------------------------------------------------------- #
# Stub launcher: the real driver code, stub probe/session/env
# --------------------------------------------------------------------------- #

STUB_SCRIPT = textwrap.dedent(
    """
    import importlib.util, json, os, sys, time
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("s3_driver", os.environ["S3_DRIVER"])
    m = importlib.util.module_from_spec(spec)
    sys.modules["s3_driver"] = m
    spec.loader.exec_module(m)
    PLAN = json.loads(os.environ["S3_STUB_PLAN"])
    FAKE = json.loads(os.environ["S3_STUB_ENV"])
    m.build_env = lambda args: m.InputEnv(**FAKE)


    class Sess:
        pageerrors = ["stub pageerror"]

        def __init__(self, unit, out_dir):
            self.unit, self.out = unit, Path(out_dir)

        def close(self):
            paths = m.unit_paths(self.out, self.unit)
            (self.out / f"closed.{self.unit}.json").write_text(json.dumps({
                "saw_artifact": paths["artifact"].exists(),
                "saw_stamp": paths["stamp"].exists(),
                "t": time.time(),
            }))
            if PLAN.get("close_hang"):
                time.sleep(600)


    m.SESSION_FACTORY = lambda unit, args, env: Sess(unit, args.out_dir)


    def _raise(msg):
        raise ValueError(msg)


    def probe(sess, ctx):
        out = Path(ctx.args.out_dir)
        with open(out / "count", "a") as fh:
            fh.write("x\\n")
        if PLAN.get("hang"):
            time.sleep(600)
        if PLAN.get("raise"):
            raise ValueError(PLAN["raise"])
        fields = dict(PLAN["fields"])
        if PLAN.get("sub_raise"):
            results, errs = m.collect_sub_probes({
                "b_prime": lambda r: fields["b_prime"],
                "c": lambda r: _raise(PLAN["sub_raise"]),
                "d": lambda r: fields["d"],
            })
            fields.update(results)
            fields["sub_errors"] = errs
            fields["negative_control"] = m.judge_negative_control(results.get("c"), fields.get("c_prime"))
        if PLAN.get("drop_field"):
            fields.pop(PLAN["drop_field"], None)
        return fields


    m.PROBES = {m.UNIT_NAME: probe}
    sys.exit(m.main(
        sys.argv[1:],
        unit_argv_prefix=[sys.executable, os.path.abspath(__file__)],
        unit_timeout_s=float(os.environ.get("S3_STUB_TIMEOUT", "600")),
        driver_extra_s=float(os.environ.get("S3_STUB_EXTRA", "60")),
    ))
    """
)

FAKE_ENV = {
    "script": "s" * 64, "runner": "r" * 64, "harness": "h" * 64, "dist": "d" * 64, "fixture": "f" * 64,
    "chrome": "c" * 64, "driver": "v" * 64, "base_path": "/", "chrome_path": "", "chrome_version": "stub",
}


class Harness:
    def __init__(self, s3: Any, tmp_path: Path, fields: dict[str, Any]) -> None:
        self.m = s3
        self.tmp = tmp_path
        self.out = tmp_path / "out"
        self.stub = tmp_path / "stub_launcher.py"
        self.stub.write_text(STUB_SCRIPT)
        self.results = tmp_path / "bth_results.json"
        self.plan: dict[str, Any] = {"fields": fields}
        self.fake_env = dict(FAKE_ENV)
        self.timeout = "600"
        self.extra = "60"

    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k != "PRAXIS_UNIT_TOKEN"}
        env.update(
            S3_DRIVER=str(DRIVER_PATH), S3_STUB_PLAN=json.dumps(self.plan),
            S3_STUB_ENV=json.dumps(self.fake_env), S3_STUB_TIMEOUT=self.timeout,
            S3_STUB_EXTRA=self.extra, BTH_RESULTS_PATH=str(self.results),
        )
        return env

    def cmd(self, *extra: str) -> list[str]:
        return [sys.executable, str(self.stub), "--out-dir", str(self.out), "--dist", str(self.tmp), *extra]

    def driver(self, *extra: str) -> tuple[int, dict[str, Any]]:
        proc = subprocess.run(self.cmd(*extra), env=self.env(), capture_output=True, text=True, timeout=170)
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip().startswith("{")]
        assert lines, f"no aggregate JSON on stdout.\nstdout={proc.stdout!r}\nstderr={proc.stderr[-3000:]}"
        return proc.returncode, json.loads(lines[-1])

    def unit(self) -> int:
        return subprocess.run(
            self.cmd("--unit", UNIT), env=self.env(), capture_output=True, text=True, timeout=120
        ).returncode

    def count(self) -> int:
        p = self.out / "count"
        return len(p.read_text().split()) if p.exists() else 0

    def artifact(self) -> dict[str, Any]:
        return json.loads(self.m.unit_paths(self.out, UNIT)["artifact"].read_text())

    def stamp(self) -> dict[str, Any]:
        return json.loads(self.m.unit_paths(self.out, UNIT)["stamp"].read_text())


@pytest.fixture
def h(s3, tmp_path, happy_fields):
    return Harness(s3, tmp_path, happy_fields)


# --------------------------------------------------------------------------- #
# The unit table is the D17 S3 row
# --------------------------------------------------------------------------- #


def test_unit_table_is_the_d17_s3_row(s3):
    assert s3.UNIT_NAMES == ("ipython_hooks",)
    assert s3.UNIT_TIMEOUT_S == 600.0 and s3.DRIVER_EXTRA_S == 60.0
    assert s3.UNIT_TIMEOUT_S * s3.DEADLINE_FRACTION == 540.0
    assert s3.UNIT_BY_NAME[UNIT].required[0] == "kernel_ready"


def test_sidecar_preregisters_the_unit_the_fields_and_the_d17_design(s3):
    text = SIDECAR_PATH.read_text()
    assert f"[design.units.{UNIT}]" in text
    for field in s3.UNIT_BY_NAME[UNIT].required:
        assert f'"{field}"' in text, field
    lowered = text.lower()
    for needle in ("os._exit", "driver", "harness", "600", "660", "unit_runner.watchdog", "unit_runner.run_unit",
                   "--resume", "error finding", "full unit set", "negative control", "unregistered",
                   "set_custom_exc", 'metadata["text/html"]["praxis"]', "[outcomes.invalid]",
                   "is_residual = true", "notebook model"):
        assert needle in lowered, needle
    flat_fields = derived_field_names(s3)
    for name in flat_fields:
        assert f"\n{name} = " in text, f"result_schema lacks {name}"


def derived_field_names(s3: Any) -> list[str]:
    fields = dict.fromkeys(s3.UNIT_BY_NAME[UNIT].required)
    art = {**fields, "cells": {}, "sub_errors": {}}
    return list(s3.derive_outcome_fields(art)["flat"])


def test_dry_run_prints_the_plan_and_launches_nothing():
    proc = subprocess.run(
        [sys.executable, str(DRIVER_PATH), "--dry-run", "--out-dir", "unused"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    plan = json.loads(proc.stdout)
    assert [u["name"] for u in plan["units"]] == [UNIT]
    assert plan["unit_timeout_s"] == 600.0 and plan["driver_timeout_s"] == 660.0 and plan["probe_deadline_s"] == 540.0
    assert plan["kernel_cells"][0] == "warm" and len(plan["fixture_sha256"]) == 64


# --------------------------------------------------------------------------- #
# Driver / unit / stamp / completeness / outcome gating (real subprocesses)
# --------------------------------------------------------------------------- #


def test_full_run_completes_stamps_and_evaluates_outcome_fields(h):
    code, agg = h.driver()
    assert code == 0
    assert agg["all_units_complete"] and agg["outcome_evaluated"] and agg["spike"] == "S3"
    assert agg["recomputed"] == [UNIT] and agg["reused"] == []
    art, stamp = h.artifact(), h.stamp()
    raw = h.m.unit_paths(h.out, UNIT)["artifact"].read_bytes()
    assert stamp["artifact_sha256"] == h.m.sha256_bytes(raw)
    assert stamp["exit"] == 0 and stamp["unit"] == UNIT and stamp["timeout_s"] == 600.0
    assert art["error"] is None and art["pageerrors"] == ["stub pageerror"] and art["missing_fields"] == []
    assert set(stamp["inputs"]) == {"script", "runner", "harness", "dist", "fixture", "chrome", "driver", "args"}
    flat = json.loads(h.results.read_text())
    assert flat["measurement_valid"] is True and flat["d1_branch"] == "S3-A" and flat["n_deviations"] == 0
    assert flat["negative_control_failed_as_required"] is True and flat["all_units_complete"] is True
    assert flat == agg["outcome_fields"]


def test_teardown_order_artifact_then_close_then_stamp(h):
    h.driver()
    closed = json.loads((h.out / f"closed.{UNIT}.json").read_text())
    assert closed["saw_artifact"] is True, "artifact must exist before teardown"
    assert closed["saw_stamp"] is False, "stamp must be committed AFTER teardown"
    assert h.stamp()["finished"] >= closed["t"]


def test_resume_reuses_a_verified_unit_and_records_source_and_hashes(h):
    h.driver()
    code, agg = h.driver("--resume")
    assert code == 0 and agg["recomputed"] == [] and len(agg["reused"]) == 1
    rec = agg["reused"][0]
    assert rec["source"].endswith(f"units/{UNIT}.json")
    assert rec["artifact_sha256"] == h.stamp()["artifact_sha256"]
    assert set(rec["inputs"]) >= {"script", "runner", "harness", "dist", "fixture", "chrome", "driver"}
    assert h.count() == 1, "a reused unit must not run again"
    # outcomes are still evaluated over the FULL unit set when everything was reused
    assert agg["outcome_evaluated"] and json.loads(h.results.read_text())["measurement_valid"] is True


def test_without_resume_everything_is_recomputed(h):
    h.driver()
    _, agg = h.driver()
    assert agg["recomputed"] == [UNIT] and h.count() == 2


@pytest.mark.parametrize("changed", ["chrome", "driver", "dist", "fixture", "runner", "script", "harness"])
def test_input_mismatch_forces_recompute(h, changed):
    h.driver()
    h.fake_env[changed] = "0" * 64
    _, agg = h.driver("--resume")
    assert agg["reused"] == [] and agg["recomputed"] == [UNIT] and h.count() == 2
    assert all(changed in rec["mismatched"] for rec in agg["stale"])


def test_base_path_is_an_input_too(h):
    h.driver()
    h.fake_env["base_path"] = "/other/"
    _, agg = h.driver("--resume")
    assert agg["recomputed"] == [UNIT] and "args" in agg["stale"][0]["mismatched"]


def test_build_env_hashes_repl_smoke_as_the_harness_input_and_the_fixture_from_the_cells(s3, tmp_path, monkeypatch):
    """D17 / AC-3: the driver loads ``repl_smoke.py`` (``ServedDir``, ``chromium_launch_args``,
    ``resolve_chrome_path``), so its sha256 is the ``harness`` input, in driver mode and
    ``--unit`` mode alike (both call ``build_env``); the ``fixture`` input is the hash of the
    seeded notebook built from the kernel cells.
    """
    import argparse

    smoke = tmp_path / "repl_smoke_stub.py"
    smoke.write_text("# harness v1\n")
    chrome = tmp_path / "chrome"
    chrome.write_text("#!/bin/sh\necho stub-chrome 1\n")
    chrome.chmod(0o755)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "a.txt").write_text("a")
    monkeypatch.setattr(s3, "REPL_SMOKE_PATH", smoke)
    # ``uv.lock`` is gitignored (absent in a fresh worktree); this test is about ``harness``
    monkeypatch.setattr(s3.unit_runner, "driver_input", lambda **kw: "v" * 64)
    monkeypatch.setattr(
        s3, "repl_smoke", lambda: types.SimpleNamespace(resolve_chrome_path=lambda explicit: chrome)
    )
    args = argparse.Namespace(chrome_path=None, dist=str(dist), base_path="/")
    env1 = s3.build_env(args)
    assert env1.harness == s3.sha256_file(smoke)
    assert env1.harness != env1.runner and env1.harness != env1.script
    assert env1.fixture == s3.sha256_bytes(s3.fixture_bytes())
    smoke.write_text("# harness v2\n")
    env2 = s3.build_env(args)
    assert env2.harness != env1.harness
    assert env2.runner == env1.runner and env2.script == env1.script and env2.fixture == env1.fixture
    inputs = s3.compute_inputs(UNIT, env2)
    assert inputs["harness"] == env2.harness
    assert set(inputs) == {"script", "runner", "harness", "dist", "fixture", "chrome", "driver", "args"}


def test_a_headless_shell_is_refused(s3, tmp_path, monkeypatch):
    import argparse

    shell = tmp_path / "chrome-headless-shell"
    shell.write_text("#!/bin/sh\n")
    shell.chmod(0o755)
    monkeypatch.setattr(s3, "repl_smoke", lambda: types.SimpleNamespace(resolve_chrome_path=lambda e: shell))
    with pytest.raises(RuntimeError, match="FULL Chromium"):
        s3.build_env(argparse.Namespace(chrome_path=None, dist=str(tmp_path), base_path="/"))


def test_a_tampered_artifact_is_not_reused(h):
    h.driver()
    path = h.m.unit_paths(h.out, UNIT)["artifact"]
    path.write_text(path.read_text().replace('"ipython_version": "9.12.0"', '"ipython_version": "0.0.0"'))
    _, agg = h.driver("--resume")
    assert agg["recomputed"] == [UNIT] and h.count() == 2
    assert "artifact_sha256 does not match" in " ".join(agg["stale"][0]["reasons"])


def test_error_finding_is_complete_counts_against_outcomes_and_is_never_reused(h):
    h.plan["raise"] = "probe blew up"
    code, agg = h.driver()
    assert code == 0 and agg["outcome_evaluated"], "a raised probe is a COMPLETE unit"
    err = h.artifact()["error"]
    assert err["type"] == "ValueError" and err["message"] == "probe blew up"
    assert 0 < len(err["traceback_tail"].encode()) <= 4096
    assert h.stamp()["exit"] == 1
    assert agg["error_findings"][UNIT]["type"] == "ValueError"
    flat = json.loads(h.results.read_text())
    assert flat["measurement_valid"] is False and flat["n_error_units"] == 1
    assert agg["validity_checks"]["no_error_findings"] is False
    assert flat["b_holds"] is None and flat["d1_branch"] is None  # nothing measured, no branch claimed
    # resume: the errored unit is recomputed
    h.plan.pop("raise")
    _, agg2 = h.driver("--resume")
    assert agg2["recomputed"] == [UNIT] and h.count() == 2
    assert json.loads(h.results.read_text())["measurement_valid"] is True


def test_a_raised_sub_probe_becomes_the_units_error_finding_and_is_never_reused(h):
    h.plan["sub_raise"] = "sub blew up"
    code, agg = h.driver()
    assert code == 0 and agg["outcome_evaluated"]
    art = h.artifact()
    assert art["error"]["sub_probe"] == "c" and art["error"]["type"] == "ValueError"
    assert art["error"]["message"] == "sub blew up" and list(art["sub_errors"]) == ["c"]
    assert art["c"] is None and art["b_prime"] is not None and art["d"] is not None, "later sub-probes kept"
    assert h.stamp()["exit"] == 1
    flat = json.loads(h.results.read_text())
    assert flat["measurement_valid"] is False and flat["n_error_units"] == 1
    assert flat["negative_control_failed_as_required"] is None, "an errored control has NOT failed as required"
    assert agg["validity_checks"]["no_error_findings"] is False
    h.plan.pop("sub_raise")
    _, agg2 = h.driver("--resume")
    assert agg2["recomputed"] == [UNIT] and agg2["reused"] == []


def test_missing_preregistered_field_is_exit_1_and_not_reusable(h):
    h.plan["drop_field"] = "runall"
    h.driver()
    assert h.stamp()["exit"] == 1 and h.artifact()["missing_fields"] == ["runall"]
    h.plan.pop("drop_field")
    _, agg2 = h.driver("--resume")
    assert agg2["recomputed"] == [UNIT]


def test_timeout_leaves_no_stamp_no_artifact_and_blocks_outcome_evaluation(h):
    h.plan["hang"] = True
    h.timeout, h.extra = "6", "20"
    code, agg = h.driver()
    assert code == 3
    assert agg["all_units_complete"] is False and agg["outcome_evaluated"] is False
    assert agg["timed_out"] == [UNIT] and agg["incomplete"] == [UNIT]
    paths = h.m.unit_paths(h.out, UNIT)
    assert not paths["stamp"].exists() and not paths["artifact"].exists()
    marker = json.loads(paths["timeout"].read_text())
    assert marker["unit"] == UNIT and marker["budget_s"] == 6.0
    assert agg["units"][UNIT]["exit"] == 124
    assert not h.results.exists(), "no outcome may be written for an incomplete run"
    assert "outcome_fields" not in agg
    # a resume run is a new run: the unit is recomputed, and now the outcome is evaluated
    h.plan.pop("hang")
    code2, agg2 = h.driver("--resume")
    assert code2 == 0 and agg2["recomputed"] == [UNIT] and h.results.exists()


def test_hang_in_teardown_is_a_timeout_not_a_stamp(h):
    h.plan["close_hang"] = True
    h.timeout, h.extra = "6", "20"
    code, agg = h.driver()
    assert code == 3 and agg["timed_out"] == [UNIT]
    paths = h.m.unit_paths(h.out, UNIT)
    assert not paths["stamp"].exists() and not paths["artifact"].exists(), "teardown hangs are bounded BEFORE the stamp"


def test_run_unit_timeout_over_a_valid_stamp_defers_to_the_stamp(s3, h, monkeypatch, caplog):
    import argparse

    class Wrapper:
        """The real runner, but it reports a timeout even though the unit stamped."""

        def run_unit(self, argv, timeout_s, **kw):
            real = s3.unit_runner.run_unit(argv, timeout_s, **kw)
            return real._replace(timed_out=True, killed=True)

    for k, v in h.env().items():
        monkeypatch.setenv(k, v)
    args = argparse.Namespace(out_dir=str(h.out), resume=False, dist=str(h.tmp), base_path="/", chrome_path=None)
    with caplog.at_level("WARNING"):
        code = s3.run_driver(
            args, unit_argv_prefix=[sys.executable, str(h.stub)], runner=Wrapper(),
            env=s3.InputEnv(**FAKE_ENV), unit_timeout_s=600.0, driver_extra_s=60.0,
        )
    assert code == 0
    agg = json.loads((h.out / "result.json").read_text())
    assert agg["timed_out"] == [] and agg["recomputed"] == [UNIT]
    assert "the stamp governs" in caplog.text


def test_missing_plr_submodule_only_affects_real_browser_mode(s3, tmp_path, monkeypatch, caplog):
    """The driver loads ``repl_smoke.py`` lazily, only in real browser mode: the stub runs above
    never load it. If it fails to load for ANY reason (a stand-in that raises at import here)
    ``--dry-run`` degrades to a ``chrome_error`` note and a real driver run exits 2 with nothing
    started.
    """
    import argparse

    broken = tmp_path / "repl_smoke_broken.py"
    broken.write_text("class VizCheckError(RuntimeError): pass\nraise VizCheckError('no submodule')\n")
    monkeypatch.setattr(s3, "REPL_SMOKE_PATH", broken)
    monkeypatch.setattr(s3, "_REPL_SMOKE", None)
    args = argparse.Namespace(out_dir=str(tmp_path / "out"), resume=False, dist=str(tmp_path),
                              base_path="/", chrome_path=None, dry_run=True)
    assert s3._dry_run(args) == 0
    monkeypatch.setattr(s3, "_REPL_SMOKE", None)
    args.dry_run = False
    with caplog.at_level("ERROR"):
        assert s3.run_driver(args) == 2
    assert "cannot build the input set" in caplog.text
    assert not list((tmp_path / "out" / "units").glob("*")), "no unit may be started"


# --------------------------------------------------------------------------- #
# The in-page JS under a JS engine (fake notebook model): positive AND negative controls
# --------------------------------------------------------------------------- #

JS_ENGINE = shutil.which("node") or shutil.which("bun")
needs_js = pytest.mark.skipif(JS_ENGINE is None, reason="needs node or bun")


def _run_js(s3: Any, body: str, tmp_path: Path) -> Any:
    script = tmp_path / "probe_lib_test.js"
    script.write_text(
        "globalThis.window = globalThis;\n"
        "globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);\n"
        + s3.S3_JS
        + ";\nconst S = window.__s3;\n"
        + "const sleep = (ms) => new Promise((r) => setTimeout(r, ms));\n"
        + "(async () => {\n"
        + textwrap.dedent(body)
        + "\n})().catch((e) => { console.error(e); process.exit(1); });\n"
    )
    cmd = [JS_ENGINE, "run", str(script)] if Path(JS_ENGINE).name == "bun" else [JS_ENGINE, str(script)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


FAKE_NB = """
const executed = [];
const cellsJson = [
  {execution_count: null, outputs: []},
  {execution_count: 5, outputs: [{output_type: 'stream', text: 'hi'}]},
  {execution_count: null, outputs: []},
];
const cells = {get: (i) => (cellsJson[i] ? {toJSON: () => cellsJson[i], executionState: 'idle'} : undefined)};
const selected = new Set();
let active = -1;
const widgets = [{id: 0}, {id: 1}, {id: 2}];
const nb = {
  node: {classList: {contains: (c) => c === 'jp-NotebookPanel'}},
  content: {
    model: {cells}, widgets,
    deselectAll() { selected.clear(); },
    select(w) { selected.add(w.id); },
    set activeCellIndex(i) { active = i; },
    get activeCellIndex() { return active; },
  },
  sessionContext: {session: {kernel: {status: 'idle'}}},
};
let pending = null;
window.jupyterapp = {
  shell: {widgets() { return [nb][Symbol.iterator](); }},
  commands: {execute(id) {
    executed.push({id, active, selected: [...selected].sort()});
    return new Promise((res, rej) => { pending = {res, rej}; });
  }},
};
"""


@needs_js
def test_js_run_block_selects_the_cells_and_state_follows_the_command_promise(s3, tmp_path):
    out = _run_js(
        s3,
        FAKE_NB
        + """
        S.runBlock([0, 1, 2], 'block:x');
        const before = S.runState('block:x');
        pending.res(true);
        await sleep(10);
        S.runCell(1, 'cell:y');
        const single = executed[1];
        pending.rej(new Error('kernel error'));
        await sleep(10);
        console.log(JSON.stringify({executed: executed[0], single, before, after: S.runInfo('block:x'),
                                    rejected: S.runInfo('cell:y'), unknown: S.runState('nope'), status: S.kernelStatus()}));
        """,
        tmp_path,
    )
    assert out["executed"] == {"id": "notebook:run-cell", "active": 0, "selected": [0, 1, 2]}
    assert out["single"]["active"] == 1 and out["single"]["selected"] == []
    assert out["before"] == "pending" and out["after"]["state"] == "resolved" and out["after"]["value"] is True
    assert out["rejected"]["state"] == "rejected" and "kernel error" in out["rejected"]["error"]
    assert out["unknown"] is None and out["status"] == "idle"  # an unknown key is "unknown", never settled


@needs_js
def test_js_cell_read_returns_model_outputs_and_null_for_a_missing_cell(s3, tmp_path):
    out = _run_js(
        s3,
        FAKE_NB
        + """
        console.log(JSON.stringify({one: S.cellRead(1), zero: S.cellRead(0), missing: S.cellRead(9)}));
        """,
        tmp_path,
    )
    assert out["one"]["execution_count"] == 5 and out["one"]["outputs"][0]["text"] == "hi"
    assert out["zero"]["execution_count"] is None and out["zero"]["outputs"] == []
    assert out["missing"] is None


@needs_js
def test_js_command_that_throws_synchronously_is_a_rejected_run(s3, tmp_path):
    out = _run_js(
        s3,
        FAKE_NB
        + """
        window.jupyterapp.commands.execute = () => { throw new Error('no such command'); };
        S.runCell(0, 'cell:z');
        console.log(JSON.stringify(S.runInfo('cell:z')));
        """,
        tmp_path,
    )
    assert out["state"] == "rejected" and "no such command" in out["error"]
