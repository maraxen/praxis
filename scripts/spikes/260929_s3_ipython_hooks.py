#!/usr/bin/env python3
"""Spike S3 (notebook display epic, task A3): IPython display/exception/event hooks in the
JupyterLite Pyodide kernel.

Pre-registered by ``scripts/spikes/260929_s3_ipython_hooks.bth.toml`` (committed BEFORE the
first run). Design: ``.praxia/docs/specs/260929_notebook-display-epic.md`` D1 (row S3), D2
(registration, the ``metadata["text/html"]["praxis"]`` carrier), D8 (``set_custom_exc``), D16
(shared unit runner, bounded teardown) and D17 (one declared bounded unit ``ipython_hooks``,
10 min, resume, completeness). Run it as::

    bth run --project-slug praxis --output-paths outputs/spikes/260929_s3 -- \
        uv run --no-sync python3 scripts/spikes/260929_s3_ipython_hooks.py \
        --out-dir outputs/spikes/260929_s3 --dist <dist> [--resume]

(``bth run`` has no ``--out`` option; the result reaches bathos through ``$BTH_RESULTS_PATH``.)

Two modes, one file, the same shape as the S1 driver (``260929_s1_lumino_widget.py``, which
is left untouched: its script hash is recorded in a committed bathos lock; the shared
plumbing below is DUPLICATED from it on purpose, so that S2 and S3 stay independent):

* **Driver** (no ``--unit``): runs the one D17 S3 unit as its own subprocess
  ``<script> --unit ipython_hooks --out-dir <dir> ...`` through ``unit_runner.run_unit``
  (timeout = 10 min + 60 s), applies the ``--resume`` rule, and evaluates the sidecar's
  ``[outcomes]`` inputs ONLY when the unit is complete. An incomplete run writes no
  ``$BTH_RESULTS_PATH`` and exits 3, so bathos records no outcome.
* **Unit** (``--unit ipython_hooks``): ``ensure_token`` -> arm the ``Watchdog`` (10 min) ->
  clear own stamp/artifact/timeout marker -> probe -> write ``<out>/units/ipython_hooks.json``
  under the watchdog lock -> bounded teardown (browser and Playwright closed, ``kill_tree``,
  flush) -> commit ``<out>/units/ipython_hooks.stamp.json`` through ``Watchdog.commit`` ->
  ``os._exit(stamp.exit)``.

What the unit does. It seeds a notebook (built in this file; its canonical JSON is the
``fixture`` input), opens it in the served lab with FULL Chromium, waits for the Pyodide
kernel (which boots PLR through PYTHONSTARTUP and gates every cell on that boot; the wait for
idle and the warm-up cell may use most of the budget) and then runs the probe cells in that
ONE kernel: (a) ``get_ipython()``, (b) ``mimebundle_formatter.for_type``, (b') the per-type
``formatters['text/html'].for_type`` carrier at ``metadata["text/html"]["praxis"]``, (c)
``set_custom_exc`` (plus (c') the instance ``showtraceback`` wrapper that S3-C would use),
(d) ``events.register('post_run_cell')``, each in a plain cell AND a top-level-``await`` cell,
Run All behaviour, and the D17 negative control (an exception class not registered with
``set_custom_exc`` must reach the default traceback).

Measurement discipline (``~/.claude/rules/BATHOS.md``): every result is read from the
NOTEBOOK MODEL (``notebook.content.model.cells``: each cell's ``outputs`` and
``execution_count`` as JSON), never from the DOM, the console or printed text. Kernel-side
observations that have no output of their own (whether a handler ran, which events fired) are
sent back as structured ``display_data`` bundles (``application/json``, raw) and read from the
same model. A verdict that could be a probe bug is only reported next to a control that
proves the instrument can say the opposite (see the sidecar); anything uncontrolled or
unmeasured is ``None``, and any ``None`` in a validity check makes the run ``invalid``, never
a branch claim. A probe that raises is an ``error`` finding, never a negative result.

PLR dependence: nothing here imports or touches PyLabRobot. The only dependence is that the
served dist's kernel boots PLR at start-up and gates the first cell on it; if the boot does
not reach idle, or the first (warm-up) cell raises, the artifact records that and the run is
``invalid``.

``--dry-run`` prints the unit, the pre-registered fields, the kernel cells and the resolved
inputs' sources without launching a browser or hashing the dist.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import importlib.util
import json
import logging
import os
import subprocess
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

LOG = logging.getLogger("s3_spike")

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "unit_runner.py"
REPL_SMOKE_PATH = REPO_ROOT / "scripts" / "repl_smoke.py"
DEFAULT_DIST = REPO_ROOT / "web-repl" / "dist"

UNIT_NAME = "ipython_hooks"
#: D17 S3 row: ONE bounded unit, 10 min. The driver kills at this + 60 s (D16/D17). The
#: estimate is the spec's, not a measurement; not changed here.
UNIT_TIMEOUT_S = 10 * 60.0
DRIVER_EXTRA_S = 60.0
#: The probe stops STARTING work at this fraction of the unit budget (540 s of 600 s), so an
#: artifact reporting how far it got is written before the watchdog can fire.
DEADLINE_FRACTION = 0.9

VIEWPORT = {"width": 1440, "height": 900}
NB_PATH = "s3_ipython_hooks.ipynb"
NAV_TIMEOUT_MS = 90_000
#: Internal step caps (seconds). Each is further clipped to the time left before the deadline.
IDLE_TIMEOUT_S = 240.0
WARMUP_TIMEOUT_S = 180.0
CELL_TIMEOUT_S = 45.0
BLOCK_TIMEOUT_S = 90.0

#: The stamps the probe's formatters return. ``exec`` is added kernel-side (an int).
B_STAMP = {"v": 1, "kind": "plate", "resource": "s3-plate", "rev": 7, "session": "s3-session-b"}
H_STAMP = {"v": 1, "kind": "plate", "resource": "s3-plate", "rev": 7, "session": "s3-session-h"}

MODES = ("plain", "await")
D_MARKERS = {
    "plain": "s3-d-plain-marker",
    "await": "s3-d-await-marker",
    "after": "s3-d-after-marker",
}
RUNALL_BLOCKS = {
    "control": ("n1", "n2", "n3"),
    "custom": ("r1", "r2", "r3"),
    "wrap": ("w1", "w2", "w3"),
}
RUNALL_METHOD = (
    "notebook:run-cell over a multi-cell selection (the Notebook actions runCells path that "
    "Run All also uses; the run-all-cells command itself is not used because it would "
    "re-execute the earlier probe cells)"
)


# --------------------------------------------------------------------------- #
# The unit table (D17 S3 row) and its pre-registered artifact fields
# --------------------------------------------------------------------------- #


@dataclasses.dataclass(frozen=True)
class UnitSpec:
    name: str
    required: tuple[str, ...]


UNITS: tuple[UnitSpec, ...] = (
    UnitSpec(
        UNIT_NAME,
        (
            "kernel_ready", "boot", "prelude", "cells", "sub_errors", "get_ipython_present",
            "ipython_version", "path_evidence", "a", "b", "b_prime", "c", "c_prime", "d",
            "runall", "negative_control", "all_cells_done", "deadline_hit", "aborted",
        ),
    ),
)
UNIT_NAMES = tuple(u.name for u in UNITS)
UNIT_BY_NAME = {u.name: u for u in UNITS}


# --------------------------------------------------------------------------- #
# The kernel cells (the seeded notebook). Kernel-side code has never met the real dist:
# every observation is echoed as a structured bundle and read back from the model.
# --------------------------------------------------------------------------- #

SETUP_SRC = r"""
import asyncio, inspect, json, sys
import IPython
from IPython.display import display

_S3 = {"handler_calls": [], "wrap_seen": [], "events": [], "post_execute": 0}


def _s3_emit(tag, **payload):
    payload["tag"] = tag
    clean = json.loads(json.dumps(payload, default=str))
    display({"application/json": clean, "text/plain": json.dumps(clean)}, raw=True, metadata={"s3": tag})


class S3CustomError(Exception):
    pass


class S3WrapError(Exception):
    pass


class S3PlainError(Exception):
    pass


class S3B:
    def __init__(self, mode):
        self.mode = mode


class S3H:
    def __init__(self, mode):
        self.mode = mode


class S3Repr:
    def _repr_html_(self):
        return "<i>s3-repr</i>"


def _s3_a():
    ip = get_ipython()
    out = {"is_none": ip is None}
    if ip is None:
        return out
    t = type(ip)
    fm = getattr(ip, "display_formatter", None)
    out.update(
        ip_type=t.__module__ + "." + t.__qualname__,
        mro=[c.__module__ + "." + c.__qualname__ for c in t.__mro__][:6],
        ipython_version=IPython.__version__,
        has_display_formatter=fm is not None,
        has_mimebundle_formatter=hasattr(fm, "mimebundle_formatter"),
        has_html_formatter="text/html" in getattr(fm, "formatters", {}),
        has_events=hasattr(ip, "events"),
        has_set_custom_exc=hasattr(ip, "set_custom_exc"),
        execution_count=ip.execution_count,
        autoawait=getattr(ip, "autoawait", None),
    )
    return out


def _s3_path():
    ip = get_ipython()
    if ip is None:
        return {"no_ip": True}
    t = type(ip)
    out = {}

    def guard(key, fn):
        try:
            out[key] = fn()
        except BaseException as e:
            out[key] = "error: " + repr(e)

    def run_code_src():
        src = inspect.getsource(t.run_code)
        i = src.find("except self.custom_exceptions")
        j = src.find("except:", i) if i >= 0 else -1
        branch = src[i:j] if (i >= 0 and j > i) else (src[i:i + 400] if i >= 0 else "")
        return {
            "has_custom_branch": i >= 0,
            "custom_branch_calls_customtb": "CustomTB(" in branch,
            "custom_branch_uses_return_value": ("= self.CustomTB(" in branch) or ("return self.CustomTB(" in branch),
            "custom_branch_calls_showtraceback": "showtraceback" in branch,
            "custom_branch": branch.strip()[:400],
        }

    guard("run_code", run_code_src)
    guard("showtraceback_owner", lambda: t.showtraceback.__module__ + "." + t.showtraceback.__qualname__)
    guard("_showtraceback_owner", lambda: t._showtraceback.__module__ + "." + t._showtraceback.__qualname__)
    guard("_showtraceback_source", lambda: inspect.getsource(t._showtraceback)[:600])
    guard("kernel_type", lambda: type(ip.kernel).__module__ + "." + type(ip.kernel).__qualname__)
    guard("kernel_run_status_from_last_traceback", lambda: "_last_traceback is None" in inspect.getsource(type(ip.kernel).run))
    guard("run_cell_triggers_post_run_cell", lambda: "post_run_cell" in inspect.getsource(t.run_cell))
    guard("run_cell_async_triggers_post_run_cell", lambda: "post_run_cell" in inspect.getsource(t.run_cell_async))
    guard("custom_exceptions_initial", lambda: [c.__name__ for c in ip.custom_exceptions])
    guard("autoawait", lambda: ip.autoawait)
    guard("should_run_async_for_await_cell", lambda: bool(ip.should_run_async("await asyncio.sleep(0)")))
    return out


_s3_emit(
    "setup",
    ipython_version=IPython.__version__,
    python_version=sys.version.split()[0],
    get_ipython_present=get_ipython() is not None,
)
"""

B_REG_SRC = r"""
ip = get_ipython()
_S3_B_STAMP = @@B_STAMP@@


def _s3_b_fn(obj):
    stamp = dict(_S3_B_STAMP, exec=get_ipython().execution_count)
    return ({"text/html": "<b>s3-b-" + obj.mode + "</b>", "text/plain": "s3-b-" + obj.mode}, {"praxis": stamp})


_err = None
try:
    ip.display_formatter.mimebundle_formatter.for_type(S3B, _s3_b_fn)
except BaseException as e:
    _err = repr(e)
_s3_emit("b_reg", error=_err)
"""

BP_REG_SRC = r"""
ip = get_ipython()
_S3_H_STAMP = @@H_STAMP@@


def _s3_h_html(obj):
    stamp = dict(_S3_H_STAMP, exec=get_ipython().execution_count)
    return ("<b>s3-h-" + obj.mode + "</b>", {"praxis": stamp})


def _s3_h_plain(obj, p, cycle):
    p.text("s3-h-" + obj.mode)


_html_err = None
_plain_err = None
try:
    ip.display_formatter.formatters["text/html"].for_type(S3H, _s3_h_html)
except BaseException as e:
    _html_err = repr(e)
try:
    ip.display_formatter.formatters["text/plain"].for_type(S3H, _s3_h_plain)
except BaseException as e:
    _plain_err = repr(e)
_s3_emit("bp_reg", html_error=_html_err, plain_error=_plain_err)
"""

D_REG_SRC = r"""
ip = get_ipython()


def _s3_post_run_cell(*args):
    r = args[0] if args else None
    info = getattr(r, "info", None)
    _S3["events"].append({
        "kind": "post_run_cell",
        "raw": (getattr(info, "raw_cell", None) or "")[:80],
        "n_args": len(args),
        "success": getattr(r, "success", None),
        "execution_count": getattr(r, "execution_count", None),
    })


def _s3_pre_run_cell(*args):
    info = args[0] if args else None
    _S3["events"].append({"kind": "pre_run_cell", "raw": (getattr(info, "raw_cell", None) or "")[:80]})


def _s3_post_execute():
    _S3["post_execute"] += 1


_err = None
try:
    ip.events.register("post_run_cell", _s3_post_run_cell)
    ip.events.register("pre_run_cell", _s3_pre_run_cell)
    ip.events.register("post_execute", _s3_post_execute)
except BaseException as e:
    _err = repr(e)
_s3_emit("d_reg", error=_err)
"""

D_UNREG_SRC = r"""
ip = get_ipython()
_err = None
try:
    ip.events.unregister("post_run_cell", _s3_post_run_cell)
except BaseException as e:
    _err = repr(e)
_s3_emit("d_unreg", error=_err)
"""

C_REG_SRC = r"""
ip = get_ipython()


def _s3_c_handler(self, etype, value, tb, tb_offset=None):
    rec = {"etype": etype.__name__, "value": str(value), "self_is_shell": self is ip, "tb_offset": tb_offset}
    _S3["handler_calls"].append(rec)
    try:
        display(
            {"application/json": {"tag": "c_handler_display", "value": str(value)}, "text/plain": "s3-c-handler-display"},
            raw=True,
            metadata={"s3": "c_handler_display"},
        )
    except BaseException as e:
        rec["display_raised"] = repr(e)
    return ["S3CustomError: " + str(value)]


_err = None
try:
    ip.set_custom_exc((S3CustomError,), _s3_c_handler)
except BaseException as e:
    _err = repr(e)
_s3_emit("c_reg", error=_err, custom_exceptions=[c.__name__ for c in getattr(ip, "custom_exceptions", ())])
"""

W_INSTALL_SRC = r"""
ip = get_ipython()
_s3_orig_show = ip.showtraceback


def _s3_wrap_show(*args, **kwargs):
    exc = kwargs.get("exc_tuple") or (args[0] if args and args[0] else None) or sys.exc_info()
    et, ev, tb = exc
    rec = {"etype": et.__name__ if et is not None else None, "value": str(ev), "handled": isinstance(ev, S3WrapError)}
    _S3["wrap_seen"].append(rec)
    if isinstance(ev, S3WrapError):
        try:
            display(
                {"application/json": {"tag": "w_handler_display", "value": str(ev)}, "text/plain": "s3-w-handler-display"},
                raw=True,
                metadata={"s3": "w_handler_display"},
            )
        except BaseException as e:
            rec["display_raised"] = repr(e)
        try:
            ip._showtraceback(et, ev, ["S3WrapError: " + str(ev)])
            rec["delegated"] = "_showtraceback"
        except BaseException as e:
            rec["delegate_raised"] = repr(e)
        return None
    return _s3_orig_show(*args, **kwargs)


_err = None
try:
    ip.showtraceback = _s3_wrap_show
except BaseException as e:
    _err = repr(e)
_s3_emit("w_reg", error=_err, installed=ip.showtraceback is _s3_wrap_show)
"""

CELL_SOURCES: tuple[tuple[str, str], ...] = (
    ("warm", "s3_warm = 1\n"),
    ("setup", SETUP_SRC),
    ("a_plain", '_s3_emit("a", mode="plain", **_s3_a())\n'),
    ("a_await", 'await asyncio.sleep(0)\n_s3_emit("a", mode="await", **_s3_a())\n'),
    ("path", '_s3_emit("path", **_s3_path())\n'),
    ("b_reg", B_REG_SRC.replace("@@B_STAMP@@", repr(B_STAMP))),
    ("b_plain", 'display(S3B("plain"))\nS3B("plain_result")\n'),
    ("b_await", 'await asyncio.sleep(0)\ndisplay(S3B("await"))\nS3B("await_result")\n'),
    ("b_control", "display(S3Repr())\n"),
    ("bp_reg", BP_REG_SRC.replace("@@H_STAMP@@", repr(H_STAMP))),
    ("bp_plain", 'display(S3H("plain"))\nS3H("plain_result")\n'),
    ("bp_await", 'await asyncio.sleep(0)\ndisplay(S3H("await"))\nS3H("await_result")\n'),
    ("d_reg", D_REG_SRC),
    ("d_plain", "# " + D_MARKERS["plain"] + "\npass\n"),
    ("d_await", "# " + D_MARKERS["await"] + "\nawait asyncio.sleep(0)\n"),
    ("d_unreg", D_UNREG_SRC),
    ("d_after", "# " + D_MARKERS["after"] + "\npass\n"),
    (
        "d_emit",
        '_s3_emit("d_events", events=list(_S3["events"]), post_execute=_S3["post_execute"])\n',
    ),
    ("c_reg", C_REG_SRC),
    ("c_plain", 'raise S3CustomError("s3-c-plain")\n'),
    ("c_await", 'await asyncio.sleep(0)\nraise S3CustomError("s3-c-await")\n'),
    ("c_neg_plain", 'raise S3PlainError("s3-c-neg-plain")\n'),
    ("c_neg_await", 'await asyncio.sleep(0)\nraise S3PlainError("s3-c-neg-await")\n'),
    ("c_calls", '_s3_emit("c_calls", calls=list(_S3["handler_calls"]))\n'),
    ("w_install", W_INSTALL_SRC),
    ("w_plain", 'raise S3WrapError("s3-w-plain")\n'),
    ("w_await", 'await asyncio.sleep(0)\nraise S3WrapError("s3-w-await")\n'),
    ("w_neg_plain", 'raise S3PlainError("s3-w-neg-plain")\n'),
    ("w_neg_await", 'await asyncio.sleep(0)\nraise S3PlainError("s3-w-neg-await")\n'),
    ("w_calls", '_s3_emit("w_calls", calls=list(_S3["wrap_seen"]))\n'),
    ("n1", '_s3_emit("ra", name="n1")\n'),
    ("n2", 'raise S3PlainError("s3-ra-n2")\n'),
    ("n3", '_s3_emit("ra", name="n3")\n'),
    ("r1", '_s3_emit("ra", name="r1")\n'),
    ("r2", 'raise S3CustomError("s3-ra-r2")\n'),
    ("r3", '_s3_emit("ra", name="r3")\n'),
    ("w1", '_s3_emit("ra", name="w1")\n'),
    ("w2", 'raise S3WrapError("s3-ra-w2")\n'),
    ("w3", '_s3_emit("ra", name="w3")\n'),
)
CELL_NAMES = tuple(name for name, _ in CELL_SOURCES)
CELL_INDEX = {name: i for i, name in enumerate(CELL_NAMES)}


def build_fixture() -> dict[str, Any]:
    """The seeded notebook (nbformat 4.5, one code cell per probe cell, nothing executed)."""
    cells = [
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "s3-" + name,
            "metadata": {},
            "outputs": [],
            "source": source.splitlines(keepends=True),
        }
        for name, source in CELL_SOURCES
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python (Pyodide)", "language": "python", "name": "python"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def fixture_bytes() -> bytes:
    return json.dumps(build_fixture(), sort_keys=True, indent=1).encode()


# --------------------------------------------------------------------------- #
# Loading the shared modules BY PATH (nothing edits sys.path)
# --------------------------------------------------------------------------- #


def _load_by_path(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


unit_runner = _load_by_path("unit_runner", RUNNER_PATH)
_REPL_SMOKE: Any = None


def repl_smoke() -> Any:
    """``scripts/repl_smoke.py`` loaded by path, once (ServedDir, chromium_launch_args, ...)."""
    global _REPL_SMOKE
    if _REPL_SMOKE is None:
        _REPL_SMOKE = _load_by_path("repl_smoke", REPL_SMOKE_PATH)
    return _REPL_SMOKE


# --------------------------------------------------------------------------- #
# Hashing and the unit's input set (D17 "Inputs hashed")
# --------------------------------------------------------------------------- #


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    return unit_runner._sha256_file(Path(path))


@dataclasses.dataclass
class InputEnv:
    """Everything the input set is built from, already hashed (so tests can fake it)."""

    script: str
    runner: str
    harness: str  # sha256 of scripts/repl_smoke.py (loaded by path; D17 "harness" input)
    dist: str
    fixture: str  # sha256 of the canonical JSON of the seeded notebook (built in this file)
    chrome: str
    driver: str
    base_path: str = "/"
    chrome_path: str = ""
    chrome_version: str = ""


def chrome_version_of(chrome_path: str) -> str:
    try:
        proc = subprocess.run(
            [chrome_path, "--version"], capture_output=True, text=True, timeout=30, check=False
        )
        return (proc.stdout or proc.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unavailable: {type(exc).__name__}"


def build_env(args: argparse.Namespace) -> InputEnv:
    """Resolve and hash the real inputs. Raises FileNotFoundError on a missing dist/chrome."""
    chrome_path = str(repl_smoke().resolve_chrome_path(args.chrome_path))
    if "headless_shell" in chrome_path or "headless-shell" in chrome_path:
        raise RuntimeError(
            f"{chrome_path} is a headless shell; S3 needs FULL Chromium (D16). Pass --chrome-path."
        )
    version = chrome_version_of(chrome_path)
    return InputEnv(
        script=sha256_file(SCRIPT_PATH),
        runner=sha256_file(RUNNER_PATH),
        harness=sha256_file(REPL_SMOKE_PATH),
        dist=unit_runner.dist_hash(args.dist),
        fixture=sha256_bytes(fixture_bytes()),
        chrome=sha256_bytes(f"{chrome_path}\n{version}".encode()),
        driver=unit_runner.driver_input(),
        base_path=args.base_path,
        chrome_path=chrome_path,
        chrome_version=version,
    )


def compute_inputs(unit: str, env: InputEnv) -> dict[str, str]:
    """The stamp's ``inputs``: script, runner, harness, dist, fixture, chrome, driver, args.
    S3 has one unit and no upstream unit, so there is no ``upstream:*`` input.
    """
    return {
        "script": env.script,
        "runner": env.runner,
        "harness": env.harness,
        "dist": env.dist,
        "fixture": env.fixture,
        "chrome": env.chrome,
        "driver": env.driver,
        "args": sha256_bytes(
            json.dumps(
                {"unit": unit, "viewport": VIEWPORT, "base_path": env.base_path}, sort_keys=True
            ).encode()
        ),
    }


# --------------------------------------------------------------------------- #
# Unit files, completeness and the resume rule (D17)
# --------------------------------------------------------------------------- #


def unit_paths(out_dir: Path, name: str) -> dict[str, Path]:
    units = out_dir / "units"
    return {
        "artifact": units / f"{name}.json",
        "stamp": units / f"{name}.stamp.json",
        "timeout": units / f"{name}.timeout.json",
    }


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _rm(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def inspect_unit(out_dir: Path, spec: UnitSpec, current_inputs: dict[str, str]) -> dict[str, Any]:
    """Classify the unit's files against the CURRENT inputs.

    * ``complete``: artifact and a matching stamp exist (the stamp's ``artifact_sha256``
      equals the artifact on disk and its ``inputs`` equal the current inputs). A raised
      probe is complete (its ``error`` finding is in the artifact). Only a timeout or a
      stampless crash is incomplete.
    * ``reusable`` (the ``--resume`` rule): complete AND ``stamp.exit == 0`` AND no
      ``error`` finding AND every pre-registered field present.
    * ``mismatched``: the input names whose hash differs from the stamp's.
    """
    paths = unit_paths(out_dir, spec.name)
    artifact_bytes: bytes | None
    try:
        artifact_bytes = paths["artifact"].read_bytes()
    except OSError:
        artifact_bytes = None
    stamp = _read_json(paths["stamp"])
    artifact = None
    if artifact_bytes is not None:
        try:
            artifact = json.loads(artifact_bytes)
        except ValueError:
            artifact = None
    state: dict[str, Any] = {
        "unit": spec.name,
        "artifact": artifact,
        "stamp": stamp if isinstance(stamp, dict) else None,
        "artifact_path": str(paths["artifact"]),
        "complete": False,
        "reusable": False,
        "mismatched": [],
        "reasons": [],
    }
    if artifact is None or not isinstance(artifact, dict):
        state["reasons"].append("no artifact")
        return state
    if state["stamp"] is None:
        state["reasons"].append("no stamp")
        return state
    stamp = state["stamp"]
    if stamp.get("artifact_sha256") != sha256_bytes(artifact_bytes or b""):
        state["reasons"].append("artifact_sha256 does not match the artifact on disk")
        return state
    recorded = stamp.get("inputs") or {}
    mismatched = sorted(
        name
        for name in set(recorded) | set(current_inputs)
        if recorded.get(name) != current_inputs.get(name)
    )
    state["mismatched"] = mismatched
    if mismatched:
        state["reasons"].append("stamp inputs differ from current inputs")
        return state
    state["complete"] = True
    if stamp.get("exit") != 0:
        state["reasons"].append(f"stamp.exit == {stamp.get('exit')}")
    if artifact.get("error") is not None:
        state["reasons"].append("artifact carries an error finding")
    missing = [f for f in spec.required if f not in artifact] + list(
        artifact.get("missing_fields") or []
    )
    if missing:
        state["reasons"].append(f"pre-registered fields missing: {sorted(set(missing))}")
    state["reusable"] = not state["reasons"]
    return state


# --------------------------------------------------------------------------- #
# Reading the notebook model (pure; unit-tested without a browser)
# --------------------------------------------------------------------------- #

_CAP = 4096
_OWN_CAP = 256 * 1024


def _mime_text(value: Any) -> str | None:
    """A mime value as text: nbformat stores multiline text as a list of strings."""
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        return "".join(value)
    return value if isinstance(value, str) else None


def _shrink(value: Any, cap: int = _CAP) -> Any:
    """Keep a JSON value if it is small; otherwise a marked head of its JSON text."""
    if isinstance(value, str):
        return value if len(value) <= cap else value[:cap] + f"...[+{len(value) - cap} chars]"
    text = json.dumps(value, default=str, sort_keys=True)
    if len(text) <= cap:
        return value
    return {"_truncated": len(text), "head": text[:cap]}


def trim_output(output: dict[str, Any]) -> dict[str, Any]:
    """A bounded copy of one nbformat output (the artifact keeps the model's evidence)."""
    kind = output.get("output_type")
    out: dict[str, Any] = {"output_type": kind}
    if kind in ("display_data", "execute_result"):
        # the probe's own tagged bundles (metadata.s3) carry its measurements: never truncate them
        own = isinstance((output.get("metadata") or {}).get("s3"), str)
        cap = _OWN_CAP if own else _CAP
        out["data"] = {
            mime: _shrink(_mime_text(v) if isinstance(v, list) else v, cap)
            for mime, v in (output.get("data") or {}).items()
        }
        out["metadata"] = _shrink(output.get("metadata") or {})
        if "execution_count" in output:
            out["execution_count"] = output["execution_count"]
    elif kind == "error":
        out["ename"] = _shrink(output.get("ename"))
        out["evalue"] = _shrink(output.get("evalue"))
        out["traceback"] = [_shrink(line, 2048) for line in (output.get("traceback") or [])[:24]]
    elif kind == "stream":
        out["name"] = output.get("name")
        out["text"] = _shrink(_mime_text(output.get("text")) or "")
    return out


def is_done(rec: dict[str, Any] | None) -> bool:
    """The cell's run settled (its command promise resolved or rejected): it was executed."""
    return bool(rec) and rec.get("state") in ("resolved", "rejected")


def emit_payload(outputs: list[dict[str, Any]] | None, tag: str) -> tuple[dict[str, Any] | None, str | None]:
    """The payload of the ``display_data`` output that kernel-side ``_s3_emit(tag)`` produced,
    and the channel it was read from (``application/json``, else the ``text/plain`` JSON).
    """
    for output in outputs or []:
        if output.get("output_type") != "display_data":
            continue
        if (output.get("metadata") or {}).get("s3") != tag:
            continue
        data = output.get("data") or {}
        as_json = data.get("application/json")
        if isinstance(as_json, dict):
            return as_json, "application/json"
        text = _mime_text(data.get("text/plain"))
        if text is not None:
            try:
                parsed = json.loads(text)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                return parsed, "text/plain"
    return None, None


def error_output(outputs: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    return next((o for o in outputs or [] if o.get("output_type") == "error"), None)


def summarize_error(outputs: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    err = error_output(outputs)
    if err is None:
        return None
    return {
        "ename": err.get("ename"),
        "evalue": err.get("evalue"),
        "traceback_tail": _shrink("\n".join(str(x) for x in (err.get("traceback") or []))[-2048:], 2048),
    }


def _stamp_ok(stamp: Any, static: dict[str, Any]) -> bool:
    if not isinstance(stamp, dict):
        return False
    rest = {k: v for k, v in stamp.items() if k != "exec"}
    exec_count = stamp.get("exec")
    return rest == static and isinstance(exec_count, int) and not isinstance(exec_count, bool)


def judge_carrier(
    rec: dict[str, Any], *, prefix: str, mode: str, static: dict[str, Any], carrier: str
) -> dict[str, Any]:
    """Where did the stamp land on the output the registered formatter produced?

    ``carrier`` is ``"top"`` (``metadata["praxis"]``, the (b) mimebundle carrier) or
    ``"html"`` (``metadata["text/html"]["praxis"]``, the (b') per-type carrier). The output is
    the ``display_data`` whose ``text/html`` is exactly the formatter's HTML; if the formatter
    did not run, the first ``display_data`` is inspected instead (``html_ok`` is then False).
    ``measured`` is False when there is nothing to inspect (never a branch claim).
    """
    outs = rec.get("outputs") or []
    disp = [o for o in outs if o.get("output_type") == "display_data"]
    want = f"<b>{prefix}{mode}</b>"
    ours = next((o for o in disp if _mime_text((o.get("data") or {}).get("text/html")) == want), None)
    target = ours if ours is not None else (disp[0] if disp else None)
    md = (target or {}).get("metadata")
    md = md if isinstance(md, dict) else {}
    top = md.get("praxis") if isinstance(md.get("praxis"), dict) else None
    root = md.get("text/html")
    nested = root.get("praxis") if isinstance(root, dict) and isinstance(root.get("praxis"), dict) else None
    top_ok, nested_ok = _stamp_ok(top, static), _stamp_ok(nested, static)
    result = next(
        (
            o
            for o in outs
            if o.get("output_type") == "execute_result"
            and _mime_text((o.get("data") or {}).get("text/html")) == f"<b>{prefix}{mode}_result</b>"
        ),
        None,
    )
    rmd = (result or {}).get("metadata")
    rmd = rmd if isinstance(rmd, dict) else {}
    rroot = rmd.get("text/html")
    rstamp = (
        rmd.get("praxis")
        if carrier == "top"
        else (rroot.get("praxis") if isinstance(rroot, dict) else None)
    )
    exec_seen = (top if carrier == "top" else nested) or {}
    return {
        "measured": is_done(rec) and target is not None,
        "state": rec.get("state"),
        "html_ok": ours is not None,
        "display_count": len(disp),
        "stamp_top": top,
        "stamp_nested": nested,
        "stamp_top_ok": top_ok,
        "stamp_nested_ok": nested_ok,
        "carrier_ok": top_ok if carrier == "top" else nested_ok,
        "exec_matches_cell": (exec_seen.get("exec") == rec.get("execution_count")) if exec_seen else None,
        "result_output_present": result is not None,
        "result_carrier_ok": _stamp_ok(rstamp, static) if result is not None else None,
        "error": summarize_error(outs),
    }


def judge_unstamped_control(rec: dict[str, Any]) -> dict[str, Any]:
    """Instrument control for (b)/(b'): a plain ``_repr_html_`` object carries NO stamp; the
    reader must say so (it must be able to answer "absent").
    """
    outs = rec.get("outputs") or []
    disp = next(
        (
            o
            for o in outs
            if o.get("output_type") == "display_data"
            and _mime_text((o.get("data") or {}).get("text/html")) == "<i>s3-repr</i>"
        ),
        None,
    )
    md = (disp or {}).get("metadata")
    md = md if isinstance(md, dict) else {}
    root = md.get("text/html")
    nested = isinstance(root, dict) and "praxis" in root
    return {
        "measured": is_done(rec) and disp is not None,
        "reads_none": None if disp is None else ("praxis" not in md and not nested),
        "metadata": md,
    }


def judge_exc(
    rec: dict[str, Any],
    calls: list[dict[str, Any]] | None,
    *,
    message: str,
    expected_line: str,
    display_tag: str,
) -> dict[str, Any]:
    """One raise of a REGISTERED class: was the handler invoked, did ``display()`` inside it
    emit, and did the handler's returned structured traceback become the cell's ``error``
    output (exactly ``[expected_line]``)?
    """
    outs = rec.get("outputs") or []
    err = error_output(outs)
    tb = err.get("traceback") if err else None
    shown, _ = emit_payload(outs, display_tag)
    measured = is_done(rec) and calls is not None
    invoked = None if calls is None else any(c.get("value") == message for c in calls)
    display_emitted = isinstance(shown, dict) and shown.get("value") == message
    returned = err is not None and tb == [expected_line]
    ok = None
    if measured:
        ok = bool(invoked and display_emitted and err is not None and returned)
    return {
        "measured": measured,
        "state": rec.get("state"),
        "execution_count": rec.get("execution_count"),
        "invoked": invoked,
        "display_emitted": display_emitted,
        "error_output_present": err is not None,
        "error_ename": (err or {}).get("ename"),
        "error_evalue": (err or {}).get("evalue"),
        "error_traceback": tb,
        "traceback_is_returned_stb": returned,
        "ok": ok,
    }


def judge_default(
    rec: dict[str, Any],
    calls: list[dict[str, Any]] | None,
    *,
    message: str,
    cls_name: str,
    display_tag: str,
) -> dict[str, Any]:
    """The D17 negative control for one raise of an UNREGISTERED class: the handler must not
    have handled it, no handler display may exist, and the default traceback (a multi-line
    IPython traceback naming the class) must be the cell's ``error`` output.
    ``failed_as_required`` is None (never True) unless the cell settled and the kernel-side
    call list was read: a control that errored has NOT failed as required.
    """
    outs = rec.get("outputs") or []
    err = error_output(outs)
    tb_lines = [str(x) for x in ((err or {}).get("traceback") or [])]
    tb_text = "\n".join(tb_lines)
    shown, _ = emit_payload(outs, display_tag)
    measured = is_done(rec) and calls is not None
    matching = [c for c in (calls or []) if c.get("value") == message]
    handled = any(c.get("handled", True) is not False for c in matching)
    default_reached = (
        err is not None
        and cls_name in (str(err.get("ename")) + "\n" + tb_text)
        and "Traceback" in tb_text
        and len(tb_lines) >= 1
    )
    verdict = None
    if measured:
        verdict = bool((not handled) and shown is None and default_reached)
    return {
        "measured": measured,
        "state": rec.get("state"),
        "handled_by_hook": handled if measured else None,
        "seen_by_hook": bool(matching) if measured else None,
        "handler_display_present": shown is not None,
        "default_traceback_reached": default_reached,
        "error_ename": (err or {}).get("ename"),
        "error_traceback_head": tb_lines[:2],
        "failed_as_required": verdict,
    }


def marker_ran(rec: dict[str, Any], name: str) -> bool:
    payload, _ = emit_payload(rec.get("outputs"), "ra")
    return isinstance(payload, dict) and payload.get("name") == name


def judge_block(cells: list[dict[str, Any]], run: dict[str, Any], names: tuple[str, str, str]) -> dict[str, Any]:
    """A three-cell Run block (marker, raiser, marker). ``stops`` is True when the third cell
    never ran, and None (never a claim) unless the block settled, the first marker and the
    raiser ran, and the third cell's ``execution_count`` agrees with its marker.
    """
    first, raiser, third = cells
    r1 = marker_ran(first, names[0])
    r3 = marker_ran(third, names[2])
    r2 = raiser.get("execution_count") is not None or bool(raiser.get("outputs"))
    consistent = r3 == (third.get("execution_count") is not None)
    settled = run.get("state") in ("resolved", "rejected")
    stops = (not r3) if (settled and r1 and r2 and consistent) else None
    return {
        "names": list(names),
        "run_state": run.get("state"),
        "run_error": run.get("error"),
        "ran": [r1, r2, r3],
        "execution_counts": [c.get("execution_count") for c in cells],
        "raiser_error_output": error_output(raiser.get("outputs")) is not None,
        "consistent": consistent,
        "stops": stops,
    }


def judge_events(reg: dict[str, Any] | None, payload: dict[str, Any] | None) -> dict[str, Any]:
    """(d): did ``post_run_cell`` fire for each marker cell, and NOT for the marker cell run
    after ``unregister`` (the control: the reader must be able to answer "did not fire")?
    """
    events = (payload or {}).get("events")
    readable = isinstance(events, list)

    def fired(kind: str, marker: str) -> bool | None:
        if not readable:
            return None
        return any(e.get("kind") == kind and marker in (e.get("raw") or "") for e in events)

    return {
        "reg_read": isinstance(reg, dict),
        "reg_error": reg.get("error") if isinstance(reg, dict) else None,
        "events_readable": readable,
        "fired_plain": fired("post_run_cell", D_MARKERS["plain"]),
        "fired_await": fired("post_run_cell", D_MARKERS["await"]),
        "fired_after_unregister": fired("post_run_cell", D_MARKERS["after"]),
        "pre_run_cell_plain": fired("pre_run_cell", D_MARKERS["plain"]),
        "pre_run_cell_await": fired("pre_run_cell", D_MARKERS["await"]),
        "post_execute_count": (payload or {}).get("post_execute"),
        "n_events": len(events) if readable else None,
        "events": events[:40] if readable else None,
    }


def judge_negative_control(c: dict[str, Any] | None, cp: dict[str, Any] | None) -> dict[str, Any]:
    """D17: an exception class NOT registered must reach the default traceback, under BOTH the
    ``set_custom_exc`` handler and the instance ``showtraceback`` wrapper, plain and await.
    """
    cases: dict[str, Any] = {}
    for label, src in (("custom", c), ("wrap", cp)):
        for mode in MODES:
            cases[f"{label}_{mode}"] = ((src or {}).get("neg") or {}).get(mode)
    verdicts = [(j or {}).get("failed_as_required") for j in cases.values()]
    return {
        "cases": cases,
        "failed_as_required": None if any(v is None for v in verdicts) else all(verdicts),
    }


# --------------------------------------------------------------------------- #
# Derivations (pure): the sub-probe judgments -> the flat fields the sidecar reads
# --------------------------------------------------------------------------- #


def get_ipython_present_from(a: dict[str, Any] | None) -> bool | None:
    if not isinstance(a, dict):
        return None
    plain, awaited = a.get("plain"), a.get("await")
    if not isinstance(plain, dict) or not isinstance(awaited, dict):
        return None
    flags = (plain.get("is_none"), awaited.get("is_none"))
    if flags == (False, False):
        return True
    if flags == (True, True):
        return False
    return None


def combine_carrier(reg: dict[str, Any] | None, modes: dict[str, Any] | None, err_keys: tuple[str, ...]) -> bool | None:
    """(b) / (b') holds iff registration raised nothing and, in BOTH the plain and the await
    cell, the formatter's HTML was emitted with the stamp at the carrier.
    """
    if not isinstance(reg, dict):
        return None
    if any(reg.get(k) is not None for k in err_keys):
        return False
    judged = [modes.get(m) if isinstance(modes, dict) else None for m in MODES]
    if any(not isinstance(j, dict) or j.get("measured") is not True for j in judged):
        return None
    return all(bool(j["html_ok"] and j["carrier_ok"]) for j in judged)


def runall_component(block_stops: bool | None, control_stops: bool | None) -> bool | None:
    """The "Run All stops" clause of (c)/(c'). Waived (True) when the CONTROL (a default,
    unregistered error) does not stop Run All either: the premise then fails for every
    exception path and is reported separately (``runall_control_stops``).
    """
    if control_stops is False:
        return True
    return block_stops


def combine_exc(reg: dict[str, Any] | None, modes: dict[str, Any] | None, runall_ok: bool | None) -> bool | None:
    """(c) / (c') holds iff registration raised nothing, the hook was invoked, its
    ``display()`` emitted and its returned traceback became the ``error`` output in BOTH modes,
    and Run All stops (or the clause is waived).
    """
    if not isinstance(reg, dict):
        return None
    if reg.get("error") is not None:
        return False
    judged = [modes.get(m) if isinstance(modes, dict) else None for m in MODES]
    if any(not isinstance(j, dict) or j.get("measured") is not True for j in judged):
        return None
    if any(j.get("ok") is False for j in judged):
        return False
    return runall_ok


def combine_events(d: dict[str, Any] | None) -> bool | None:
    """(d) holds iff ``post_run_cell`` fired for the plain AND the await marker cell, and the
    control (marker after ``unregister``) did not fire.
    """
    if not isinstance(d, dict) or d.get("reg_read") is not True:
        return None
    if d.get("reg_error") is not None:
        return False
    if d.get("events_readable") is not True or d.get("fired_after_unregister") is not False:
        return None
    return bool(d.get("fired_plain") and d.get("fired_await"))


def _block(art: dict[str, Any], key: str) -> dict[str, Any]:
    return ((art.get("runall") or {}).get("blocks") or {}).get(key) or {}


def carrier_branch(b: bool | None, bp: bool | None) -> str | None:
    if b is True:
        return "S3-A"
    if b is False and bp is True:
        return "S3-B"
    if b is False and bp is False:
        return "STOP"
    return None


def exc_branch(c: bool | None, cp: bool | None) -> str | None:
    if c is True:
        return "S3-A"
    if c is False and cp is True:
        return "S3-C"
    if c is False and cp is False:
        return "STOP"
    return None


def events_branch(d: bool | None) -> str | None:
    return None if d is None else ("S3-A" if d else "S3-D")


def evaluate_validity(art: dict[str, Any], flags: dict[str, Any]) -> dict[str, bool]:
    """Named checks whose conjunction is ``measurement_valid``. Any ``error`` finding, a
    control that did not behave as required, an unmeasured (``None``) hook verdict, a cell
    that never settled, or a hit deadline makes the run ``invalid`` (the residual outcome): it
    never satisfies a positive outcome. When ``get_ipython()`` is None the hook verdicts are
    False by construction (nothing can be registered) and the hook checks are waived.
    """
    ip = flags["get_ipython_present"]
    boot = art.get("boot") or {}
    checks: dict[str, bool] = {
        "no_error_findings": art.get("error") is None and not art.get("sub_errors"),
        "kernel_ready": art.get("kernel_ready") is True,
        "boot_ok": boot.get("warmup_done") is True and boot.get("warmup_error") is None,
        "prelude_ok": (art.get("prelude") or {}).get("ok") is True,
        "all_cells_done": art.get("all_cells_done") is True,
        "deadline_not_hit": art.get("deadline_hit") is False,
        "not_aborted": art.get("aborted") is None,
        "a_measured": ip is not None,
    }
    if ip is not False:
        control = _block(art, "control")
        checks.update(
            {
                "b_measured": flags["b_holds"] is not None,
                "b_prime_measured": flags["b_prime_holds"] is not None,
                "c_measured": flags["c_holds"] is not None,
                "c_prime_measured_if_needed": flags["c_holds"] is not False
                or flags["c_fallback_holds"] is not None,
                "d_measured": flags["d_holds"] is not None,
                "b_control_reads_none": all(
                    ((art.get(k) or {}).get("control_unstamped") or {}).get("reads_none") is True
                    for k in ("b", "b_prime")
                ),
                "d_control_did_not_fire": (art.get("d") or {}).get("fired_after_unregister") is False,
                "negative_control_failed_as_required": flags["negative_control_failed_as_required"] is True,
                "runall_control_measured": control.get("stops") is not None
                and control.get("raiser_error_output") is True,
            }
        )
    return checks


def derive_outcome_fields(art: dict[str, Any]) -> dict[str, Any]:
    """The flat scalar fields the sidecar's ``[outcomes]`` conditions read, plus the
    ``details`` (validity checks, per-hook verdicts).
    """
    ip = get_ipython_present_from(art.get("a"))
    b_reg, bp_reg = (art.get("b") or {}).get("reg"), (art.get("b_prime") or {}).get("reg")
    b_holds = combine_carrier(b_reg, (art.get("b") or {}).get("modes"), ("error",))
    bp_holds = combine_carrier(bp_reg, (art.get("b_prime") or {}).get("modes"), ("html_error",))
    control_stops = _block(art, "control").get("stops")
    c, cp = art.get("c") or {}, art.get("c_prime") or {}
    c_holds = combine_exc(c.get("reg"), c.get("modes"), runall_component(_block(art, "custom").get("stops"), control_stops))
    cp_holds = combine_exc(cp.get("reg"), cp.get("modes"), runall_component(_block(art, "wrap").get("stops"), control_stops))
    d_holds = combine_events(art.get("d"))
    if ip is False:  # no shell: no hook can be registered (deterministic, not a measurement gap)
        b_holds = bp_holds = c_holds = cp_holds = d_holds = False
    neg = (art.get("negative_control") or {}).get("failed_as_required")
    flags = {
        "get_ipython_present": ip,
        "b_holds": b_holds,
        "b_prime_holds": bp_holds,
        "c_holds": c_holds,
        "c_fallback_holds": cp_holds,
        "d_holds": d_holds,
        "negative_control_failed_as_required": neg,
    }
    validity = evaluate_validity(art, flags)
    carrier = carrier_branch(b_holds, bp_holds)
    exc = exc_branch(c_holds, cp_holds)
    events = events_branch(d_holds)
    branches = (carrier, exc, events)
    tokens = [
        {"S3-B": "S3-B", "STOP": "STOP-B7B9"}.get(carrier or ""),
        {"S3-C": "S3-C", "STOP": "STOP-B6"}.get(exc or ""),
        {"S3-D": "S3-D"}.get(events or ""),
    ]
    tokens = [t for t in tokens if t]
    known = all(x is not None for x in branches)
    flat = {
        "all_units_complete": True,
        "n_units": len(UNITS),
        "n_error_units": 1 if (art.get("error") is not None) else 0,
        "measurement_valid": all(validity.values()),
        "kernel_ready": art.get("kernel_ready"),
        "aborted": art.get("aborted") or "none",
        "get_ipython_present": ip,
        "ipython_version": art.get("ipython_version"),
        "b_holds": b_holds,
        "b_prime_holds": bp_holds,
        "c_holds": c_holds,
        "c_fallback_holds": cp_holds,
        "d_holds": d_holds,
        "carrier_branch": carrier,
        "exc_branch": exc,
        "events_branch": events,
        "n_deviations": (sum(1 for x in branches if x != "S3-A") if known else None),
        "d1_branch": (("+".join(tokens) if tokens else "S3-A") if known else None),
        "runall_control_stops": control_stops,
        "runall_custom_stops": _block(art, "custom").get("stops"),
        "runall_wrap_stops": _block(art, "wrap").get("stops"),
        "negative_control_failed_as_required": neg,
    }
    details = {"validity_checks": validity, "branches": {"carrier": carrier, "exc": exc, "events": events}}
    return {"flat": flat, "details": details}


# --------------------------------------------------------------------------- #
# The in-page probe library (installed as window.__s3; read via page.evaluate)
# --------------------------------------------------------------------------- #

S3_JS = r"""
(() => {
  if (window.__s3) return true;
  const S = {};
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const raf2 = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  S.settle = async (ms) => { await raf2(); await sleep(ms === undefined ? 350 : ms); await raf2(); return true; };
  S.shell = () => window.jupyterapp.shell;
  S.nbPanel = () => {
    for (const w of S.shell().widgets('main')) {
      if (w.node && w.node.classList.contains('jp-NotebookPanel') && w.content) return w;
    }
    return null;
  };
  S.cellCount = () => { const nb = S.nbPanel(); return nb ? nb.content.widgets.length : null; };
  S.kernelStatus = () => {
    const nb = S.nbPanel();
    return nb && nb.sessionContext && nb.sessionContext.session && nb.sessionContext.session.kernel
      ? nb.sessionContext.session.kernel.status : null;
  };
  S.runs = {};
  S._dispatch = (key) => {
    S.runs[key] = {state: 'pending', error: null, value: null};
    let pr;
    try { pr = window.jupyterapp.commands.execute('notebook:run-cell'); }
    catch (e) { S.runs[key] = {state: 'rejected', error: String(e), value: null}; return true; }
    Promise.resolve(pr).then(
      (v) => { S.runs[key] = {state: 'resolved', error: null, value: v === undefined ? null : v}; },
      (e) => { S.runs[key] = {state: 'rejected', error: String(e), value: null}; });
    return true;
  };
  S.runCell = (i, key) => {
    const nb = S.nbPanel().content;
    nb.deselectAll(); nb.activeCellIndex = i;
    return S._dispatch(key);
  };
  S.runBlock = (idxs, key) => {
    const nb = S.nbPanel().content;
    nb.deselectAll(); nb.activeCellIndex = idxs[0];
    for (const i of idxs) nb.select(nb.widgets[i]);
    return S._dispatch(key);
  };
  S.runState = (key) => (S.runs[key] ? S.runs[key].state : null);
  S.runInfo = (key) => S.runs[key] || null;
  S.cellRead = (i) => {
    const nb = S.nbPanel();
    const cells = nb && nb.content && nb.content.model && nb.content.model.cells;
    if (!cells) return null;
    const cell = cells.get ? cells.get(i) : cells[i];
    if (!cell) return null;
    const j = typeof cell.toJSON === 'function' ? cell.toJSON() : {};
    return {
      index: i,
      execution_count: j.execution_count === undefined ? null : j.execution_count,
      execution_state: cell.executionState === undefined ? null : cell.executionState,
      outputs: j.outputs || [],
    };
  };
  window.__s3 = S;
  return true;
})()
"""

SAVE_JS = """async (a) => {
    try {
        await window.jupyterapp.serviceManager.contents.save(a.path, {
            type: "notebook", format: "json", content: a.content});
        return {ok: true};
    } catch (e) { return {ok: false, error: String(e)}; }
}"""


# --------------------------------------------------------------------------- #
# Browser session (real), the page-backed kernel driver, and the probe context
# --------------------------------------------------------------------------- #


class BrowserSession:
    """Served dist + Playwright + one full-Chromium page. ``close()`` is the teardown's
    step 2: browser closed, Playwright stopped, server shut down; every failure is logged
    with ``logging.error`` and never changes the artifact's keys.
    """

    def __init__(self, args: argparse.Namespace, env: InputEnv) -> None:
        from playwright.sync_api import sync_playwright

        rs = repl_smoke()
        self.pageerrors: list[str] = []
        self.prefix = rs._normalize_base_path(args.base_path)
        self._stack = contextlib.ExitStack()
        self._pw: Any = None
        self._browser: Any = None
        try:
            served = self._stack.enter_context(
                rs.ServedDir(Path(args.dist), args.base_path, coi=False)
            )
            self.port = served.port
            self.origin = f"http://127.0.0.1:{served.port}"
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                executable_path=env.chrome_path,
                headless=True,
                args=rs.chromium_launch_args(offline=False),
            )
            context = self._browser.new_context(viewport=dict(VIEWPORT))
            # D16 persistence gate: the first-save modal must not block the harness.
            context.add_init_script(
                'window.localStorage.setItem("praxis-repl-persistence-ack", "browser-only");'
            )
            self.page = context.new_page()
            self.page.on("pageerror", lambda exc: self.pageerrors.append(str(exc)))
        except BaseException:
            self.close()
            raise

    @property
    def lab_url(self) -> str:
        return f"{self.origin}{self.prefix}lab/index.html"

    def close(self) -> None:
        for label, fn in (
            ("browser.close", lambda: self._browser and self._browser.close()),
            ("playwright.stop", lambda: self._pw and self._pw.stop()),
            ("served dir", self._stack.close),
        ):
            try:
                fn()
            except Exception:
                LOG.exception("teardown step failed: %s", label)


@dataclasses.dataclass
class ProbeCtx:
    unit: str
    args: argparse.Namespace
    env: InputEnv
    fixture: dict[str, Any]
    deadline: float  # time.monotonic() value after which no new work is started


class PageKernelDriver:
    """The kernel seam, backed by the real page. ``run_hooks_probe`` only ever talks to this
    interface (``open``, ``wait_idle``, ``run_cell``, ``run_block``), so the tests can put a
    fake kernel behind it. Results are read from the notebook model (``window.__s3.cellRead``).
    """

    def __init__(self, sess: Any, ctx: ProbeCtx) -> None:
        self.sess = sess
        self.ctx = ctx
        self.page = sess.page

    @property
    def pageerrors(self) -> list[str]:
        return list(getattr(self.sess, "pageerrors", []) or [])

    def _ev(self, expr: str, arg: Any = None) -> Any:
        return self.page.evaluate(f"async (a) => window.__s3.{expr}", arg)

    def open(self) -> None:
        page = self.page
        page.goto(self.sess.lab_url, wait_until="load", timeout=NAV_TIMEOUT_MS)
        page.wait_for_function(
            "() => !!window.jupyterapp && !!window.jupyterapp.shell", timeout=NAV_TIMEOUT_MS
        )
        page.evaluate(S3_JS)
        saved = page.evaluate(SAVE_JS, {"path": NB_PATH, "content": self.ctx.fixture})
        if not saved.get("ok"):
            raise RuntimeError(f"could not seed the S3 notebook: {saved.get('error')!r}")
        repl_smoke()._open_existing_notebook(page, NB_PATH, timeout_ms=NAV_TIMEOUT_MS)
        page.wait_for_function(
            "(n) => { const w = window.__s3.nbPanel(); return !!w && w.content.widgets.length >= n; }",
            arg=len(CELL_NAMES),
            timeout=NAV_TIMEOUT_MS,
        )
        self._ev("settle(800)")

    def wait_idle(self, timeout_s: float) -> bool:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        try:
            self.page.wait_for_function(
                "() => window.__s3.kernelStatus() === 'idle'", timeout=timeout_s * 1000
            )
            return True
        except PlaywrightTimeoutError:
            return False

    def _wait_settled(self, key: str, timeout_s: float) -> bool:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        try:
            self.page.wait_for_function(
                "(k) => { const s = window.__s3.runState(k); return s !== null && s !== 'pending'; }",
                arg=key,
                timeout=timeout_s * 1000,
            )
            return True
        except PlaywrightTimeoutError:
            return False

    def _record(self, name: str, key: str, started: float) -> dict[str, Any]:
        info = self._ev("runInfo(a)", key) or {"state": "pending", "error": None}
        read = self._ev("cellRead(a)", CELL_INDEX[name]) or {}
        return {
            "name": name,
            "index": CELL_INDEX[name],
            "state": info.get("state"),
            "error": info.get("error"),
            "execution_count": read.get("execution_count"),
            "execution_state": read.get("execution_state"),
            "outputs": [trim_output(o) for o in (read.get("outputs") or [])],
            "seconds": round(time.monotonic() - started, 3),
        }

    def run_cell(self, name: str, timeout_s: float) -> dict[str, Any]:
        started = time.monotonic()
        key = f"cell:{name}"
        self._ev("runCell(a.i, a.k)", {"i": CELL_INDEX[name], "k": key})
        self._wait_settled(key, timeout_s)
        self._ev("settle(150)")
        return self._record(name, key, started)

    def run_block(self, names: tuple[str, ...], key: str, timeout_s: float) -> dict[str, Any]:
        started = time.monotonic()
        rkey = f"block:{key}"
        self._ev("runBlock(a.idx, a.k)", {"idx": [CELL_INDEX[n] for n in names], "k": rkey})
        self._wait_settled(rkey, timeout_s)
        self._ev("settle(150)")
        run = self._ev("runInfo(a)", rkey) or {"state": "pending", "error": None}
        return {
            "run": {"state": run.get("state"), "error": run.get("error"), "seconds": round(time.monotonic() - started, 3)},
            "cells": [self._record(n, rkey, started) for n in names],
        }


#: Replaceable seams (the plumbing tests substitute stubs; nothing in production does).
def open_session(unit: str, args: argparse.Namespace, env: InputEnv) -> Any:
    return BrowserSession(args, env)


SESSION_FACTORY: Callable[[str, argparse.Namespace, InputEnv], Any] = open_session
KERNEL_DRIVER_FACTORY: Callable[[Any, ProbeCtx], Any] = PageKernelDriver


# --------------------------------------------------------------------------- #
# The probe: orchestration over the kernel seam
# --------------------------------------------------------------------------- #


def _tail(text: str, limit: int = 4096) -> str:
    raw = text.encode("utf-8", "replace")
    return raw[-limit:].decode("utf-8", "replace")


def collect_sub_probes(
    registry: dict[str, Callable[[dict[str, Any]], Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Run each sub-probe in order, each seeing the earlier results. A sub-probe that RAISES
    is caught: its result is None and its ``{type, message, traceback_tail}`` goes into
    ``sub_errors`` (the unit lifts the first into the artifact's ``error`` finding, so the
    unit still completes and the finding counts toward ``[outcomes]``). Later sub-probes still
    run: their evidence is kept, but the run is ``invalid``.
    """
    results: dict[str, Any] = {}
    errors: dict[str, dict[str, Any]] = {}
    for name, fn in registry.items():
        try:
            results[name] = fn(results)
        except Exception as exc:
            LOG.exception("sub-probe %s raised", name)
            results[name] = None
            errors[name] = {
                "type": type(exc).__name__,
                "message": str(exc)[:2000],
                "traceback_tail": _tail(traceback.format_exc()),
            }
    return results, errors


class HooksRun:
    """One pass over the probe cells in the ONE kernel, recording every cell."""

    def __init__(self, kd: Any, deadline: float) -> None:
        self.kd = kd
        self.deadline = deadline
        self.cells: dict[str, dict[str, Any]] = {}
        self.aborted: str | None = None
        self.deadline_hit = False

    def _budget(self, cap_s: float) -> float:
        return min(cap_s, self.deadline - time.monotonic())

    def _skipped(self, name: str, reason: str) -> dict[str, Any]:
        return {
            "name": name, "index": CELL_INDEX.get(name), "state": "skipped", "error": reason,
            "execution_count": None, "execution_state": None, "outputs": [], "seconds": 0.0,
        }

    def _admit(self, cap_s: float) -> float | None:
        """Seconds allowed for the next step, or None if nothing may start."""
        if self.aborted is not None:
            return None
        left = self._budget(cap_s)
        if left <= 1.0:
            self.deadline_hit = True
            self.aborted = self.aborted or "deadline"
            return None
        return left

    def cell(self, name: str, cap_s: float = CELL_TIMEOUT_S) -> dict[str, Any]:
        left = self._admit(cap_s)
        if left is None:
            rec = self._skipped(name, self.aborted or "aborted")
        else:
            rec = self.kd.run_cell(name, left)
            if not is_done(rec):
                self.aborted = f"cell_timeout:{name}"
        self.cells[name] = rec
        return rec

    def block(self, key: str, names: tuple[str, str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        left = self._admit(BLOCK_TIMEOUT_S)
        if left is None:
            recs = [self._skipped(n, self.aborted or "aborted") for n in names]
            run = {"state": "skipped", "error": self.aborted, "seconds": 0.0}
        else:
            out = self.kd.run_block(names, key, left)
            recs, run = out["cells"], out["run"]
            if run.get("state") not in ("resolved", "rejected"):
                self.aborted = f"block_timeout:{key}"
        for rec in recs:
            self.cells[rec["name"]] = rec
        return recs, run

    def payload(self, name: str, tag: str) -> dict[str, Any] | None:
        return emit_payload(self.cells[name].get("outputs"), tag)[0]

    # ---- sub-probes -------------------------------------------------------- #

    def sub_a(self, _r: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for mode in MODES:
            self.cell(f"a_{mode}")
            out[mode] = self.payload(f"a_{mode}", "a")
        return out

    def sub_path(self, _r: dict[str, Any]) -> dict[str, Any] | None:
        self.cell("path")
        return self.payload("path", "path")

    def sub_b(self, _r: dict[str, Any]) -> dict[str, Any]:
        self.cell("b_reg")
        reg = self.payload("b_reg", "b_reg")
        modes = {}
        for mode in MODES:
            modes[mode] = judge_carrier(self.cell(f"b_{mode}"), prefix="s3-b-", mode=mode, static=B_STAMP, carrier="top")
        return {"reg": reg, "modes": modes, "control_unstamped": judge_unstamped_control(self.cell("b_control"))}

    def sub_b_prime(self, _r: dict[str, Any]) -> dict[str, Any]:
        self.cell("bp_reg")
        reg = self.payload("bp_reg", "bp_reg")
        modes = {}
        for mode in MODES:
            modes[mode] = judge_carrier(self.cell(f"bp_{mode}"), prefix="s3-h-", mode=mode, static=H_STAMP, carrier="html")
        return {"reg": reg, "modes": modes, "control_unstamped": judge_unstamped_control(self.cells.get("b_control") or self._skipped("b_control", "not run"))}

    def sub_d(self, _r: dict[str, Any]) -> dict[str, Any]:
        self.cell("d_reg")
        reg = self.payload("d_reg", "d_reg")
        for name in ("d_plain", "d_await", "d_unreg", "d_after", "d_emit"):
            self.cell(name)
        return judge_events(reg, self.payload("d_emit", "d_events"))

    def _exc_group(self, prefix: str, reg_cell: str, reg_tag: str, calls_cell: str, calls_tag: str,
                   cls: str, display_tag: str) -> dict[str, Any]:
        self.cell(reg_cell)
        reg = self.payload(reg_cell, reg_tag)
        raised = {mode: self.cell(f"{prefix}_{mode}") for mode in MODES}
        negs = {mode: self.cell(f"{prefix}_neg_{mode}") for mode in MODES}
        self.cell(calls_cell)
        payload = self.payload(calls_cell, calls_tag)
        calls = payload.get("calls") if isinstance(payload, dict) and isinstance(payload.get("calls"), list) else None
        modes = {
            m: judge_exc(raised[m], calls, message=f"s3-{prefix}-{m}", expected_line=f"{cls}: s3-{prefix}-{m}",
                         display_tag=display_tag)
            for m in MODES
        }
        neg = {
            m: judge_default(negs[m], calls, message=f"s3-{prefix}-neg-{m}", cls_name="S3PlainError",
                             display_tag=display_tag)
            for m in MODES
        }
        return {"reg": reg, "modes": modes, "neg": neg, "calls": calls}

    def sub_c(self, _r: dict[str, Any]) -> dict[str, Any]:
        return self._exc_group("c", "c_reg", "c_reg", "c_calls", "c_calls", "S3CustomError", "c_handler_display")

    def sub_c_prime(self, _r: dict[str, Any]) -> dict[str, Any]:
        return self._exc_group("w", "w_install", "w_reg", "w_calls", "w_calls", "S3WrapError", "w_handler_display")

    def sub_runall(self, _r: dict[str, Any]) -> dict[str, Any]:
        blocks: dict[str, Any] = {}
        for key, names in RUNALL_BLOCKS.items():
            recs, run = self.block(key, names)
            blocks[key] = judge_block(recs, run, names)
        return {"method": RUNALL_METHOD, "blocks": blocks}

    def sub_negative(self, results: dict[str, Any]) -> dict[str, Any]:
        return judge_negative_control(results.get("c"), results.get("c_prime"))


def _ipython_version(a: dict[str, Any] | None, setup_payload: dict[str, Any] | None) -> str | None:
    for source in [(a or {}).get(m) for m in MODES] + [setup_payload]:
        version = source.get("ipython_version") if isinstance(source, dict) else None
        if isinstance(version, str):
            return version
    return None


def run_hooks_probe(kd: Any, deadline: float) -> dict[str, Any]:
    """The whole probe over a kernel driver. Every pre-registered field is returned (None
    where unmeasured); ``aborted`` names why the probe stopped early, if it did.
    """
    run = HooksRun(kd, deadline)
    fields: dict[str, Any] = dict.fromkeys(UNIT_BY_NAME[UNIT_NAME].required)
    fields.update(cells=run.cells, sub_errors={}, aborted=None, deadline_hit=False, all_cells_done=False)
    t0 = time.monotonic()
    kd.open()
    ready = kd.wait_idle(max(1.0, min(IDLE_TIMEOUT_S, deadline - time.monotonic())))
    idle_s = round(time.monotonic() - t0, 3)
    fields["kernel_ready"] = ready
    boot: dict[str, Any] = {"kernel_idle_seconds": idle_s, "warmup_done": False, "warmup_error": None, "warmup_seconds": None}
    fields["boot"] = boot
    fields["prelude"] = {"ok": False, "payload": None, "channel": None}
    if not ready:
        fields["aborted"] = "kernel_not_idle"
        return fields
    warm = run.cell("warm", WARMUP_TIMEOUT_S)
    boot.update(warmup_done=is_done(warm), warmup_error=summarize_error(warm.get("outputs")), warmup_seconds=warm.get("seconds"))
    if not is_done(warm) or boot["warmup_error"] is not None:
        run.aborted = run.aborted or "warmup_failed"
    setup = run.cell("setup")
    payload, channel = emit_payload(setup.get("outputs"), "setup")
    fields["prelude"] = {
        "ok": is_done(setup) and payload is not None and error_output(setup.get("outputs")) is None,
        "payload": payload, "channel": channel,
    }
    if not fields["prelude"]["ok"]:
        run.aborted = run.aborted or "prelude_failed"
    registry = {
        "a": run.sub_a, "path_evidence": run.sub_path, "b": run.sub_b, "b_prime": run.sub_b_prime,
        "d": run.sub_d, "c": run.sub_c, "c_prime": run.sub_c_prime, "runall": run.sub_runall,
        "negative_control": run.sub_negative,
    }
    results, sub_errors = collect_sub_probes(registry)
    fields.update(results)
    fields["sub_errors"] = sub_errors
    fields["get_ipython_present"] = get_ipython_present_from(fields.get("a"))
    fields["ipython_version"] = _ipython_version(fields.get("a"), fields["prelude"].get("payload"))
    fields["aborted"] = run.aborted
    fields["deadline_hit"] = run.deadline_hit
    fields["all_cells_done"] = bool(run.cells) and all(is_done(r) for r in run.cells.values())
    return fields


def probe_ipython_hooks(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    return run_hooks_probe(KERNEL_DRIVER_FACTORY(sess, ctx), ctx.deadline)


PROBES: dict[str, Callable[[Any, ProbeCtx], dict[str, Any]]] = {UNIT_NAME: probe_ipython_hooks}


# --------------------------------------------------------------------------- #
# Unit mode: the D17 per-unit sequence
# --------------------------------------------------------------------------- #


def _flush_all() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (OSError, ValueError):
            pass
    for handler in logging.getLogger().handlers:
        try:
            handler.flush()
        except Exception:  # pragma: no cover
            pass


def _sleep_forever_until_killed() -> None:  # pragma: no cover - the watchdog exits the process
    while True:
        time.sleep(1)


def run_unit_mode(args: argparse.Namespace, *, unit_timeout_s: float = UNIT_TIMEOUT_S) -> None:
    """Never returns: ends in ``os._exit`` (stamp.exit, or 124 from the watchdog)."""
    spec = UNIT_BY_NAME[args.unit]
    token = unit_runner.ensure_token()  # may re-exec; a no-op under run_unit
    out_dir = Path(args.out_dir)
    paths = unit_paths(out_dir, spec.name)
    paths["artifact"].parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    deadline = time.monotonic() + unit_timeout_s * DEADLINE_FRACTION

    def on_expire() -> None:
        _rm(paths["artifact"])
        marker = {
            "unit": spec.name, "budget_s": unit_timeout_s, "started": started, "expired": time.time(),
        }
        try:
            unit_runner.write_atomic(paths["timeout"], json.dumps(marker).encode())
        except OSError:
            pass
        unit_runner.emit_line(json.dumps({"unit": spec.name, "status": "timeout", "budget_s": unit_timeout_s}))

    watchdog = unit_runner.Watchdog(unit_timeout_s, on_expire)  # first act after ensure_token
    for key in ("stamp", "artifact", "timeout"):  # stamp first: never a stamp without its artifact
        _rm(paths[key])

    error: dict[str, Any] | None = None
    fields: dict[str, Any] = {}
    session: Any = None
    env: InputEnv | None = None
    try:
        env = build_env(args)
        ctx = ProbeCtx(spec.name, args, env, build_fixture(), deadline)
        session = SESSION_FACTORY(spec.name, args, env)
        fields = PROBES[spec.name](session, ctx)
    except Exception as exc:  # a raised probe is an `error` finding, and the unit still completes
        LOG.exception("probe %s raised", spec.name)
        error = {
            "type": type(exc).__name__, "message": str(exc)[:2000],
            "traceback_tail": _tail(traceback.format_exc()),
        }
    if error is None and fields.get("sub_errors"):
        # a raised SUB-probe is an `error` finding in the one artifact (D17): the first one
        first = next(iter(fields["sub_errors"]))
        error = {"sub_probe": first, **fields["sub_errors"][first]}
    if env is None:  # build_env itself failed; the stamp still needs inputs (best effort)
        env = InputEnv("", "", "", "", "", "", "", getattr(args, "base_path", "/"))

    missing = [f for f in spec.required if f not in fields]
    artifact: dict[str, Any] = {"unit": spec.name, "error": error}
    for name in spec.required:
        artifact[name] = fields.get(name)
    for name, value in fields.items():
        artifact.setdefault(name, value)
    artifact.update(
        {
            "missing_fields": missing if error is None else [],
            "pageerrors": list(getattr(session, "pageerrors", []) or []),
            "chrome_path": env.chrome_path, "chrome_version": env.chrome_version,
            "viewport": dict(VIEWPORT), "started": started, "finished": time.time(),
        }
    )
    data = json.dumps(artifact, indent=1, sort_keys=True, default=str).encode()
    if not watchdog.write_result(lambda: unit_runner.write_atomic(paths["artifact"], data)):
        _sleep_forever_until_killed()

    # Bounded teardown (D16, C9-1): close browser + Playwright, kill any residual descendant.
    if session is not None:
        try:
            session.close()
        except Exception:
            LOG.exception("session close raised")
    try:
        survivors = unit_runner.kill_tree(os.getpid(), token)
        if survivors:
            LOG.error("descendants survived kill_tree: %s", survivors)
    except Exception:
        LOG.exception("kill_tree raised during teardown")
    _flush_all()

    exit_code = 0 if (error is None and not missing) else 1
    stamp = {
        "unit": spec.name,
        "inputs": compute_inputs(spec.name, env),
        "artifact_sha256": sha256_bytes(data),
        "started": started, "finished": time.time(), "exit": exit_code, "timeout_s": unit_timeout_s,
    }
    stamp_bytes = json.dumps(stamp, indent=1, sort_keys=True).encode()
    if not watchdog.commit(lambda: unit_runner.write_atomic(paths["stamp"], stamp_bytes)):
        _sleep_forever_until_killed()
    os._exit(exit_code)  # nothing runs after the stamp: no atexit, no threads, no shutdown


# --------------------------------------------------------------------------- #
# Driver mode
# --------------------------------------------------------------------------- #


def _dry_run(args: argparse.Namespace) -> int:
    plan = {
        "script": str(SCRIPT_PATH), "dist": str(args.dist), "dist_exists": Path(args.dist).is_dir(),
        "unit_timeout_s": UNIT_TIMEOUT_S, "driver_timeout_s": UNIT_TIMEOUT_S + DRIVER_EXTRA_S,
        "probe_deadline_s": UNIT_TIMEOUT_S * DEADLINE_FRACTION, "viewport": VIEWPORT,
        "units": [{"name": u.name, "required_fields": list(u.required)} for u in UNITS],
        "kernel_cells": list(CELL_NAMES), "fixture_sha256": sha256_bytes(fixture_bytes()),
        "runall_blocks": {k: list(v) for k, v in RUNALL_BLOCKS.items()},
    }
    try:
        plan["chrome_path"] = str(repl_smoke().resolve_chrome_path(args.chrome_path))
    except Exception as exc:  # any failure to load repl_smoke or to find Chromium
        plan["chrome_path"] = None
        plan["chrome_error"] = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
    print(json.dumps(plan, indent=1))
    return 0


def run_driver(
    args: argparse.Namespace,
    *,
    unit_argv_prefix: list[str] | None = None,
    unit_timeout_s: float = UNIT_TIMEOUT_S,
    driver_extra_s: float = DRIVER_EXTRA_S,
    runner: Any = None,
    env: InputEnv | None = None,
) -> int:
    """Run the unit (resuming if asked), then evaluate outcomes iff it is complete.

    Exit 0: the unit is complete and the outcome fields were written (the sidecar's
    ``[outcomes]`` then evaluate them; an ``invalid`` outcome is still exit 0). Exit 3: the
    unit is incomplete; no outcome is written. Exit 2: the environment is unusable (no
    dist, no chrome).
    """
    runner = runner or unit_runner
    out_dir = Path(args.out_dir)
    (out_dir / "units").mkdir(parents=True, exist_ok=True)
    if env is None:
        try:
            env = build_env(args)
        except (FileNotFoundError, RuntimeError) as exc:
            LOG.error("cannot build the input set: %s", exc)
            return 2
    prefix = unit_argv_prefix if unit_argv_prefix is not None else [sys.executable, str(SCRIPT_PATH)]

    states: dict[str, dict[str, Any]] = {}
    status: dict[str, dict[str, Any]] = {}
    reused: list[dict[str, Any]] = []
    recomputed: list[str] = []
    timed_out: list[str] = []
    stale: list[dict[str, Any]] = []

    for spec in UNITS:
        inputs = compute_inputs(spec.name, env)
        current = inspect_unit(out_dir, spec, inputs)
        if args.resume and current["reusable"]:
            LOG.info("unit %s reused (stamp valid, exit 0, no error, fields present)", spec.name)
            states[spec.name] = current
            reused.append(
                {
                    "unit": spec.name, "source": current["artifact_path"],
                    "inputs": current["stamp"]["inputs"],
                    "artifact_sha256": current["stamp"]["artifact_sha256"],
                }
            )
            status[spec.name] = {"status": "reused"}
            continue
        if args.resume and current["stamp"] is not None:
            stale.append(
                {"unit": spec.name, "mismatched": current["mismatched"], "reasons": current["reasons"]}
            )
        paths = unit_paths(out_dir, spec.name)
        for key in ("stamp", "artifact", "timeout"):
            _rm(paths[key])
        argv = prefix + [
            "--unit", spec.name, "--out-dir", str(out_dir), "--dist", str(args.dist),
            "--base-path", args.base_path,
        ]
        if env.chrome_path:
            argv += ["--chrome-path", env.chrome_path]
        LOG.info("starting unit %s (timeout %.0f s)", spec.name, unit_timeout_s + driver_extra_s)
        outcome = runner.run_unit(argv, unit_timeout_s + driver_extra_s, cwd=str(REPO_ROOT))
        after = inspect_unit(out_dir, spec, inputs)
        states[spec.name] = after
        if after["complete"]:
            if outcome.timed_out:
                LOG.warning("unit %s: run_unit timed out over a VALID stamp; the stamp governs", spec.name)
            recomputed.append(spec.name)
            status[spec.name] = {
                "status": "recomputed", "exit": after["stamp"]["exit"],
                "error": after["artifact"].get("error"),
                "artifact_path": after["artifact_path"],
                "artifact_sha256": after["stamp"]["artifact_sha256"],
                "inputs": after["stamp"]["inputs"],
            }
        else:
            marker = paths["timeout"].exists()
            if outcome.timed_out or marker or outcome.exit == 124:
                timed_out.append(spec.name)
                status[spec.name] = {"status": "timeout", "exit": outcome.exit}
            else:
                status[spec.name] = {"status": "crashed", "exit": outcome.exit, "reasons": after["reasons"]}
            LOG.error("unit %s is INCOMPLETE: %s", spec.name, status[spec.name])

    all_complete = all(states[u.name].get("complete") for u in UNITS)
    aggregate: dict[str, Any] = {
        "spike": "S3", "all_units_complete": all_complete, "outcome_evaluated": False,
        "units": status, "reused": reused, "recomputed": recomputed, "timed_out": timed_out,
        "blocked": [], "stale": stale,
        "incomplete": [u.name for u in UNITS if not states[u.name].get("complete")],
        "error_findings": {
            u.name: states[u.name]["artifact"]["error"]
            for u in UNITS
            if states[u.name].get("complete") and states[u.name]["artifact"].get("error") is not None
        },
        "chrome_path": env.chrome_path, "chrome_version": env.chrome_version,
        "inputs_hashed": {"script": env.script, "runner": env.runner, "harness": env.harness,
                          "dist": env.dist, "fixture": env.fixture, "chrome": env.chrome, "driver": env.driver},
    }
    exit_code = 3
    if all_complete:
        derived = derive_outcome_fields(states[UNIT_NAME]["artifact"])
        aggregate.update(derived["details"])
        aggregate["outcome_fields"] = derived["flat"]
        aggregate["outcome_evaluated"] = True
        results_path = os.environ.get("BTH_RESULTS_PATH")
        if results_path:
            unit_runner.write_atomic(results_path, json.dumps(derived["flat"], sort_keys=True).encode())
        exit_code = 0
    else:
        LOG.error("NOT evaluating outcomes: incomplete units %s", aggregate["incomplete"])
    unit_runner.write_atomic(
        out_dir / "result.json", json.dumps(aggregate, indent=1, sort_keys=True, default=str).encode()
    )
    print(json.dumps(aggregate, sort_keys=True, default=str))
    return exit_code


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out-dir", required=True, help="Output dir (units/<name>.json + stamp + result.json).")
    p.add_argument("--resume", action="store_true", help="Skip a verified-complete unit (D17 rule).")
    p.add_argument("--unit", choices=UNIT_NAMES, default=None, help="Unit mode: run exactly one unit.")
    p.add_argument("--dist", default=str(DEFAULT_DIST), help="Built dist to serve (lab/ entry).")
    p.add_argument("--chrome-path", default=None, help="Full Chromium executable (not headless_shell).")
    p.add_argument("--base-path", default="/", help="URL prefix the dist is served under.")
    p.add_argument("--dry-run", action="store_true", help="Print the plan; launch nothing, hash nothing.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(
    argv: list[str] | None = None,
    *,
    unit_argv_prefix: list[str] | None = None,
    unit_timeout_s: float = UNIT_TIMEOUT_S,
    driver_extra_s: float = DRIVER_EXTRA_S,
) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.dry_run:
        return _dry_run(args)
    if args.unit:
        run_unit_mode(args, unit_timeout_s=unit_timeout_s)  # never returns
        return 1  # pragma: no cover
    return run_driver(
        args, unit_argv_prefix=unit_argv_prefix, unit_timeout_s=unit_timeout_s,
        driver_extra_s=driver_extra_s,
    )


if __name__ == "__main__":
    sys.exit(main())
