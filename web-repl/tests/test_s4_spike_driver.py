"""No-browser plumbing checks for the S4 spike driver (epic 260929_notebook-display-design, C1).

``scripts/spikes/260929_s4_viewer3d_pyodide.py`` is the pre-registered S4 probe. Nothing here
launches Playwright or Chromium, builds a dist or runs ``bth run``, and nothing here measures
S4: it proves the DRIVER, UNIT, STAMP, RESUME, COMPLETENESS and OUTCOME-GATING plumbing (D17)
against a stub probe, and it proves the PROBE LOGIC (judges, branch derivation, controls), so
that when the real run happens a plumbing or reader bug cannot be mistaken for a finding.

Layers, none of which touches a browser:

* Plumbing (real subprocesses). Every unit runs as a REAL subprocess
  (``scripts/unit_runner.run_unit``, real ``Watchdog``, real stamps) started through a tiny stub
  launcher that loads the driver by path and swaps in a stub probe / session / input environment.
  Timeouts are shrunk through the ``main(..., unit_timeout_s=, driver_extra_s=)`` parameters
  (never a CLI flag: the real budget is fixed at 10 min and pre-registered).
* Judges and branch derivation over synthetic artifacts: every D1 S4 branch (S4-A, S4-B, S4-C),
  the two unnamed stops (UNMAPPED, MESH) and each validity check that must land on ``invalid``;
  the sidecar's ``[outcomes]`` evaluated by bathos's own ``evaluate_outcome`` over those flats.
* The kernel cell sources run IN CPYTHON (a fake notebook kernel that executes each cell,
  top-level await included, and records ``display`` bundles as outputs) against PLR's own
  ``pylabrobot.visualizer3D`` when importable. This is a STAND-IN for the Pyodide kernel, not S4
  evidence: CPython has real threads, a selector loop and no boot stubs. It proves that the
  cells run, that the reader parses their bundles, and that every control can say the opposite:
  a negative control that imports fails the run; an absent ``visualizer3D`` (or a dist that is
  not the pin) is ``invalid`` with the PLR version recorded; a loop that lacks ``call_later``
  is S4-C; a start that uses a thread is UNMAPPED; a viewer step that raises is null and
  ``invalid``. Locally, point ``PRAXIS_PLR_PIN_TREE`` at an installed-form copy of PLR 1.0.0b1
  (its parent directory goes first on ``sys.path``); CI uses the root environment's PLR.
* The in-page JS (run under ``node`` or ``bun`` when present) against a fake notebook model.
"""

from __future__ import annotations

import ast
import asyncio
import copy
import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
import traceback
import types
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "spikes" / "260929_s4_viewer3d_pyodide.py"
SIDECAR_PATH = DRIVER_PATH.with_suffix(".bth.toml")
UNIT = "viewer3d_pyodide"

pytestmark = pytest.mark.timeout(180)


@pytest.fixture(scope="module")
def s4():
    spec = importlib.util.spec_from_file_location("s4_driver_under_test", DRIVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["s4_driver_under_test"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# A synthetic artifact and its variants (what the unit writes, after a JSON round trip)
# --------------------------------------------------------------------------- #


def good_fields(s4: Any) -> dict[str, Any]:
    """A complete, valid S4-A artifact (synthetic: every judged structure by hand)."""
    return {
        "kernel_ready": True,
        "boot": {"kernel_idle_seconds": 3.0, "warmup_done": True, "warmup_error": None, "warmup_seconds": 0.2},
        "prelude": {"ok": True, "payload": {"tag": "setup"}, "channel": "application/json"},
        "cells": {}, "sub_errors": {}, "skipped": {},
        "plr": {"measured": True, "visualizer3d_present": True, "at_pin": True, "pin_evidence": "sha",
                "version": "1.0.0b1+g786ac2c4", "source_sha": s4.PIN_SHA, "build_id": "b",
                "perf_counter_resolution_s": 1e-4},
        "imports": {"measured": True, "stdlib_ok": True, "stdlib_failures": [], "websockets_ok": True,
                    "visualizer3d_ok": True, "positive_control_ok": True, "stub_detector_control_ok": True,
                    "records": {}},
        "hostname": {"measured": True, "ok": True, "value": "pyodide"},
        "negative_control": {"measured": True, "failed_as_required": True},
        "loop": {"measured": True, "call_later_supported": True, "call_soon_threadsafe_supported": True,
                 "timer_cancel_control_ok": True},
        "viewer": {"measured": True, "construct_ok": True, "start_ok": True, "start_without_threads": True,
                   "patch_control_ok": True},
        "roots": {"measured": True,
                  "stock": {"measured": True, "root": "/lib/python3/site-packages/pylabrobot",
                            "in_plr_package": True, "in_site_packages": True, "glb_count": 63},
                  "rebound": {"measured": True, "root": "/tmp/tmpabc", "empty": True,
                              "differs_from_stock": True, "idempotent": True}},
        "scene": {"measured": True, "first_scene_message_bytes": 44404, "mesh_models_rebound": 0,
                  "mesh_models_stock": 4, "flush_ok": True},
        "walk": {"measured": True, "stock": {"seconds": 0.05, "root": "s", "cache_miss": True},
                 "rebound": {"seconds": 0.0001, "root": "/tmp/tmpabc", "cache_miss": True,
                             "on_rebound_root": True}},
        "seeded_control": {"measured": True, "mesh_seen": True},
        "all_cells_done": True, "deadline_hit": False, "aborted": None, "error": None,
    }


def _set(d: dict[str, Any], path: str, value: Any) -> None:
    keys = path.split(".")
    for k in keys[:-1]:
        d = d[k]
    d[keys[-1]] = value


def variant(s4: Any, **mods: Any) -> dict[str, Any]:
    art = copy.deepcopy(good_fields(s4))
    for path, value in mods.items():
        _set(art, path.replace("__", "."), value)
    return art


def _waive_viewer(art: dict[str, Any]) -> dict[str, Any]:
    for k in ("viewer", "roots", "scene", "walk", "seeded_control"):
        art[k] = None
    return art


def derived(s4: Any, art: dict[str, Any]) -> dict[str, Any]:
    art = json.loads(json.dumps(art, default=str))  # what the unit writes and the driver reads
    return s4.derive_outcome_fields(art)


def s4_b_stdlib(s4: Any) -> dict[str, Any]:
    art = variant(s4, imports__stdlib_ok=False, imports__stdlib_failures=["http.server"],
                  imports__visualizer3d_ok=False)
    return _waive_viewer(art)


def s4_b_hostname(s4: Any) -> dict[str, Any]:
    return _waive_viewer(variant(s4, hostname__ok=False, imports__visualizer3d_ok=False))


def s4_c(s4: Any) -> dict[str, Any]:
    art = variant(s4, loop__call_later_supported=False, loop__timer_cancel_control_ok=None)
    return art  # the viewer path may or may not have been measured: both are valid under S4-C


def unmapped_ws(s4: Any) -> dict[str, Any]:
    return _waive_viewer(variant(s4, imports__websockets_ok=False, imports__visualizer3d_ok=False))


BRANCH_CASES = {
    "s4_a": (lambda s4: variant(s4), "S4-A", "none"),
    "s4_b_stdlib_import": (s4_b_stdlib, "S4-B", "http.server"),
    "s4_b_gethostname": (s4_b_hostname, "S4-B", "socket.gethostname"),
    "s4_c": (s4_c, "S4-C", "none"),
    "s4_c_dominates_s4_b": (
        lambda s4: _waive_viewer(variant(s4, loop__call_later_supported=False, loop__timer_cancel_control_ok=None,
                                         imports__stdlib_ok=False, imports__stdlib_failures=["webbrowser"],
                                         imports__visualizer3d_ok=False)),
        "S4-C", "webbrowser"),
    "mesh": (lambda s4: variant(s4, scene__mesh_models_rebound=3), "MESH", "none"),
    "unmapped_websockets": (unmapped_ws, "UNMAPPED", "none"),
    "unmapped_visualizer3d_import": (
        lambda s4: _waive_viewer(variant(s4, imports__visualizer3d_ok=False)), "UNMAPPED", "none"),
    "unmapped_thread_in_start": (lambda s4: variant(s4, viewer__start_without_threads=False), "UNMAPPED", "none"),
    "unmapped_start_failed": (lambda s4: variant(s4, viewer__start_ok=False), "UNMAPPED", "none"),
    "unmapped_flush_failed": (lambda s4: variant(s4, scene__flush_ok=False), "UNMAPPED", "none"),
    "unmapped_soon_threadsafe": (
        lambda s4: variant(s4, loop__call_soon_threadsafe_supported=False), "UNMAPPED", "none"),
}


@pytest.mark.parametrize("name", sorted(BRANCH_CASES))
def test_branch_derivation_from_valid_measurements(s4, name):
    build, branch, stubs = BRANCH_CASES[name]
    flat = derived(s4, build(s4))["flat"]
    assert flat["measurement_valid"] is True and flat["invalid_reason"] == "none", flat
    assert flat["d1_branch"] == branch
    assert flat["stubs_required"] == stubs


INVALID_CASES = {
    "error_finding": (dict(error={"type": "ValueError", "message": "x"}), "no_error_findings"),
    "sub_errors": (dict(sub_errors={"loop": {"type": "ValueError"}}), "no_error_findings"),
    "kernel_not_ready": (dict(kernel_ready=False), "kernel_ready"),
    "warmup_error": (dict(boot__warmup_error={"ename": "RuntimeError"}), "boot_ok"),
    "prelude": (dict(prelude__ok=False), "prelude_ok"),
    "visualizer3d_absent": (dict(plr__visualizer3d_present=False, aborted="visualizer3d_absent"),
                            "visualizer3d_present"),
    "visualizer3d_unmeasured": (dict(plr__visualizer3d_present=None), "visualizer3d_present"),
    "not_the_pin": (dict(plr__at_pin=False), "plr_at_pin"),
    "pin_unreadable": (dict(plr__at_pin=None), "plr_at_pin"),
    "aborted": (dict(aborted="cell_timeout:loop"), "not_aborted"),
    "cell_not_done": (dict(all_cells_done=False), "all_cells_done"),
    "deadline": (dict(deadline_hit=True), "deadline_not_hit"),
    "imports_unmeasured": (dict(imports__measured=False), "imports_measured"),
    "import_positive_control": (dict(imports__positive_control_ok=False), "import_positive_control"),
    "stub_detector": (dict(imports__stub_detector_control_ok=False), "stub_detector_control"),
    "hostname_unmeasured": (dict(hostname__ok=None), "hostname_measured"),
    "negative_control_false": (dict(negative_control__failed_as_required=False),
                               "negative_control_failed_as_required"),
    "negative_control_null": (dict(negative_control=None), "negative_control_failed_as_required"),
    "loop_unmeasured": (dict(loop__measured=False, loop__call_later_supported=None), "loop_measured"),
    "timer_control": (dict(loop__timer_cancel_control_ok=False), "timer_cancel_control"),
    "viewer_step_raised": (dict(viewer__measured=False, viewer__start_ok=None), "viewer_measured"),
    "patch_control": (dict(viewer__patch_control_ok=False, viewer__start_without_threads=None), "patch_control_ok"),
    "scene_unmeasured": (dict(scene__measured=False, scene__first_scene_message_bytes=None), "scene_measured"),
    "flush_unmeasured": (dict(scene__flush_ok=None), "flush_measured"),
    "roots_unmeasured": (dict(roots__measured=False), "roots_measured"),
    "walk_not_on_rebound": (dict(walk__rebound__on_rebound_root=False), "walk_measured"),
    "walk_not_a_first_call": (dict(walk__measured=False), "walk_measured"),
    "mesh_unmeasured": (dict(scene__mesh_models_rebound=None), "mesh_counts_measured"),
    "seeded_control_no_mesh": (dict(seeded_control__mesh_seen=False), "seeded_control_sees_mesh"),
    "rebind_not_empty": (dict(roots__rebound__empty=False), "rebind_effective"),
    "rebind_same_root": (dict(roots__rebound__differs_from_stock=False), "rebind_effective"),
}


@pytest.mark.parametrize("name", sorted(INVALID_CASES))
def test_each_uncontrolled_or_unmeasured_case_is_invalid_and_claims_no_branch(s4, name):
    mods, reason = INVALID_CASES[name]
    flat = derived(s4, variant(s4, **mods))["flat"]
    assert flat["measurement_valid"] is False
    assert flat["invalid_reason"] == reason
    assert flat["d1_branch"] is None


def test_a_negative_control_that_errored_has_not_failed_as_required(s4):
    """A sub-probe that raised leaves its result null, so the control reads None, not True."""
    results, errors = s4.collect_sub_probes(
        {"loop": lambda r: good_fields(s4)["loop"],
         "negative_control": lambda r: (_ for _ in ()).throw(RuntimeError("control blew up"))}
    )
    assert results["negative_control"] is None and list(errors) == ["negative_control"]
    assert errors["negative_control"]["type"] == "RuntimeError"
    art = variant(s4, negative_control=None, sub_errors=errors)
    flat = derived(s4, art)["flat"]
    assert flat["negative_control_failed_as_required"] is None
    assert flat["measurement_valid"] is False and flat["d1_branch"] is None


def test_derived_flat_fields_match_the_sidecar_result_schema(s4):
    flat = derived(s4, variant(s4))["flat"]
    text = SIDECAR_PATH.read_text()
    for name in flat:
        assert f"\n{name} = " in text, f"result_schema lacks {name}"
    schema = text.split("[result_schema]")[1].split("\n# ---")[0]
    declared = {ln.split(" = ")[0] for ln in schema.splitlines() if " = " in ln}
    assert declared == set(flat), sorted(declared ^ set(flat))


BATHOS_PY = Path.home() / ".local" / "share" / "uv" / "tools" / "bathos" / "bin" / "python"
OUTCOME_LABEL = {"S4-A": "s4_a", "S4-B": "s4_b", "S4-C": "s4_c", "MESH": "s4_mesh", "UNMAPPED": "s4_unmapped"}


@pytest.mark.skipif(not BATHOS_PY.exists(), reason="needs the bathos uv-tool interpreter (not in CI)")
def test_sidecar_outcomes_select_the_expected_outcome_for_every_case(s4, tmp_path):
    """The sidecar's outcome conditions, evaluated by bathos's own ``evaluate_outcome`` (DuckDB,
    first match in file order) over the flat fields each synthetic case produces, select exactly
    the pre-registered outcome. It says nothing about the real kernel.
    """
    flats: dict[str, Any] = {}
    expected: dict[str, str] = {}
    for name, (build, branch, _stubs) in BRANCH_CASES.items():
        flats[name] = derived(s4, build(s4))["flat"]
        expected[name] = OUTCOME_LABEL[branch]
    for name, (mods, _reason) in INVALID_CASES.items():
        flats["invalid_" + name] = derived(s4, variant(s4, **mods))["flat"]
        expected["invalid_" + name] = "invalid"
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
    assert labels == expected, {k: (labels.get(k), v) for k, v in expected.items() if labels.get(k) != v}


# --------------------------------------------------------------------------- #
# The pure judges
# --------------------------------------------------------------------------- #


def test_judge_plr_records_the_version_and_the_pin_evidence(s4):
    sha = s4.PIN_SHA
    base = {"find_spec": {"pylabrobot.visualizer3D": True}, "pylabrobot_version": "1.0.0b1+g786ac2c4"}
    assert s4.judge_plr({**base, "plr_source_sha": sha})["at_pin"] is True
    assert s4.judge_plr({**base, "plr_source_sha": sha})["pin_evidence"] == "sha"
    assert s4.judge_plr({**base, "plr_source_sha": "0" * 40})["at_pin"] is False  # version alone must not rescue
    assert s4.judge_plr({**base, "plr_source_sha": None})["at_pin"] is True
    assert s4.judge_plr({**base, "plr_source_sha": None})["pin_evidence"] == "version_only"
    old = {"find_spec": {"pylabrobot.visualizer3D": False}, "pylabrobot_version": "0.2.2+gdd79c4c8"}
    j = s4.judge_plr(old)
    assert j["visualizer3d_present"] is False and j["at_pin"] is False and j["version"] == "0.2.2+gdd79c4c8"
    assert s4.judge_plr({"find_spec": {"pylabrobot.visualizer3D": None}})["visualizer3d_present"] is None
    assert s4.judge_plr(None)["measured"] is False and s4.judge_plr(None)["at_pin"] is None


def _import_payload(s4: Any, **overrides: Any) -> dict[str, Any]:
    real = {"ok": True, "stub_like": False, "preloaded": False}
    records = {n: dict(real) for n in s4.ALL_IMPORTS}
    for name, rec in overrides.items():
        records[name.replace("__", ".")] = rec
    return {"records": records,
            "controls": {"positive_json": dict(real), "bare_module_reads_stub_like": True}}


def test_judge_imports_groups_and_never_counts_a_stub_as_a_real_import(s4):
    ok = s4.judge_imports(_import_payload(s4))
    assert ok["measured"] and ok["stdlib_ok"] and ok["websockets_ok"] and ok["visualizer3d_ok"]
    assert ok["positive_control_ok"] and ok["stub_detector_control_ok"]
    bad = s4.judge_imports(_import_payload(s4, http__server={"ok": False, "error": {"type": "ImportError"}}))
    assert bad["stdlib_ok"] is False and bad["stdlib_failures"] == ["http.server"]
    assert bad["websockets_ok"] is True
    stub = s4.judge_imports(_import_payload(s4, webbrowser={"ok": True, "stub_like": True}))
    assert stub["stdlib_ok"] is False and stub["stdlib_failures"] == ["webbrowser"], "a bare stub is not a success"
    ssl = s4.judge_imports(_import_payload(s4, ssl={"ok": True, "stub_like": True}))
    assert ssl["stdlib_ok"] is True, "ssl is boot-stubbed and recorded only"
    ws = s4.judge_imports(_import_payload(s4, websockets={"ok": False, "error": {"type": "ModuleNotFoundError"}}))
    assert ws["websockets_ok"] is False and ws["stdlib_ok"] is True
    unread = _import_payload(s4)
    del unread["records"]["websockets.http11"]
    assert s4.judge_imports(unread)["measured"] is False and s4.judge_imports(unread)["websockets_ok"] is None
    assert s4.judge_imports(None) == {"measured": False, "records": None}
    broken_control = _import_payload(s4)
    broken_control["controls"]["bare_module_reads_stub_like"] = False
    assert s4.judge_imports(broken_control)["stub_detector_control_ok"] is False


def test_judge_hostname_and_negative_import(s4):
    assert s4.judge_hostname({"ok": True, "value": "h"})["ok"] is True
    assert s4.judge_hostname({"ok": False, "error": {"type": "OSError"}})["ok"] is False
    assert s4.judge_hostname(None)["ok"] is None
    cands = ("tkinter", "curses")

    def rec(name: str, **kw: Any) -> dict[str, Any]:
        return {"ok": False, "error": {"type": "ModuleNotFoundError", "message": f"No module named '{name}'",
                                       "name": name}, **kw}

    good = {"candidates": {n: rec(n) for n in cands}}
    assert s4.judge_negative_import(good, cands)["failed_as_required"] is True
    imported = {"candidates": {"tkinter": {"ok": True}, "curses": rec("curses")}}
    j = s4.judge_negative_import(imported, cands)
    assert j["failed_as_required"] is False and j["unexpected_success"] == ["tkinter"]
    wrong_type = {"candidates": {"tkinter": {"ok": False, "error": {"type": "AttributeError", "message": "x"}},
                                 "curses": rec("curses")}}
    assert s4.judge_negative_import(wrong_type, cands)["failed_as_required"] is False
    wrong_module = {"candidates": {"tkinter": rec("something_else"), "curses": rec("curses")}}
    assert s4.judge_negative_import(wrong_module, cands)["failed_as_required"] is False
    assert s4.judge_negative_import({"candidates": {"tkinter": rec("tkinter")}}, cands)["failed_as_required"] is None
    assert s4.judge_negative_import(None, cands)["failed_as_required"] is None


def test_judge_loop_only_calls_a_missing_or_unimplemented_api_a_failure(s4):
    ok = {"has_call_later": True, "has_call_soon_threadsafe": True, "call_later_fired": True,
          "soon_threadsafe_fired": True, "cancelled_fired": False, "errors": {}}
    j = s4.judge_loop(ok)
    assert j["measured"] and j["call_later_supported"] is True and j["call_soon_threadsafe_supported"] is True
    assert j["timer_cancel_control_ok"] is True
    assert s4.judge_loop({**ok, "cancelled_fired": True})["timer_cancel_control_ok"] is False
    assert s4.judge_loop({**ok, "has_call_later": False})["call_later_supported"] is False
    nie = {**ok, "errors": {"call_later": {"type": "NotImplementedError"}}}
    assert s4.judge_loop(nie)["call_later_supported"] is False
    other = {**ok, "errors": {"call_later": {"type": "RuntimeError"}}}
    assert s4.judge_loop(other)["call_later_supported"] is None and s4.judge_loop(other)["measured"] is False
    never = {**ok, "call_later_fired": False}
    assert s4.judge_loop(never)["call_later_supported"] is None, "a timer that never fired is inconclusive"
    soon = {**ok, "errors": {"call_soon_threadsafe": {"type": "AttributeError"}}}
    assert s4.judge_loop(soon)["call_soon_threadsafe_supported"] is False
    assert s4.judge_loop(None)["call_later_supported"] is None


def test_judge_viewer_start_without_threads_needs_the_patch_control(s4):
    setup = {"ready": True, "overrides": ["__init__", "start", "stop"]}
    calls0 = {"thread_start": 0, "websockets_serve": 0, "webbrowser_open": 0}
    base = {"errors": {}, "construct_ok": True, "start_ok": True, "stop_ok": True,
            "patch_control_all_raise": True, "calls_during_start": calls0}
    j = s4.judge_viewer(setup, base)
    assert j["measured"] and j["start_without_threads"] is True and j["overrides"] == ["__init__", "start", "stop"]
    used = {**base, "calls_during_start": {**calls0, "thread_start": 1}}
    assert s4.judge_viewer(setup, used)["start_without_threads"] is False
    no_control = {**base, "patch_control_all_raise": False}
    assert s4.judge_viewer(setup, no_control)["start_without_threads"] is None
    raised = {**base, "start_ok": None, "errors": {"start": {"type": "RuntimeError"}}}
    j = s4.judge_viewer(setup, raised)
    assert j["start_ok"] is None and j["start_without_threads"] is None and j["measured"] is False
    assert s4.judge_viewer({"ready": False}, base)["measured"] is False
    assert s4.judge_viewer(setup, None)["construct_ok"] is None


def test_judge_scene_and_walk_and_seeded(s4):
    rebound = {"errors": {}, "events": ["scene", "state"], "first_message_bytes": 100, "n_mesh_models": 0,
               "flush": {"events": ["scene", "state"], "epoch_before": 1, "epoch_after": 2, "rebuilds": 1},
               "hello_seen": True, "wait_for_browser_ok": True, "root_after": "/tmp/r", "listing": [],
               "walk_log": [{"root": "/tmp/r", "seconds": 0.001, "cache_miss": True, "n_models": 0}],
               "walk_calls_in_start": 0, "differs_from_stock": True, "idempotent": True}
    stock = {"errors": {}, "root": "/site/pylabrobot", "n_mesh_models": 4, "scene_message_bytes": 200,
             "walk_log": [{"root": "/site/pylabrobot", "seconds": 0.05, "cache_miss": True, "n_models": 63}]}
    scene = s4.judge_scene(stock, rebound)
    assert scene["measured"] and scene["first_scene_message_bytes"] == 100 and scene["flush_ok"] is True
    assert scene["mesh_models_rebound"] == 0 and scene["mesh_models_stock"] == 4
    late = {**rebound, "flush": {**rebound["flush"], "events": ["scene"]}}
    assert s4.judge_scene(stock, late)["flush_ok"] is False
    epoch = {**rebound, "flush": {**rebound["flush"], "epoch_after": 1}}
    assert s4.judge_scene(stock, epoch)["flush_ok"] is False
    raised = {**rebound, "errors": {"flush": {"type": "ValueError"}}}
    assert s4.judge_scene(stock, raised)["flush_ok"] is None
    wrong_order = {**rebound, "events": ["state", "scene"]}
    assert s4.judge_scene(stock, wrong_order)["measured"] is False
    assert s4.judge_scene(stock, wrong_order)["first_scene_message_bytes"] is None
    roots = s4.judge_roots(stock, rebound)
    assert roots["measured"] and roots["rebound"]["empty"] is True and roots["rebound"]["root"] == "/tmp/r"
    walk = s4.judge_walk(stock, rebound, roots)
    assert walk["measured"] and walk["rebound"]["on_rebound_root"] is True and walk["stock"]["seconds"] == 0.05
    hit = {**rebound, "walk_log": [{"root": "/tmp/r", "seconds": 0.0, "cache_miss": False}]}
    assert s4.judge_walk(stock, hit, roots)["measured"] is False, "a cache hit is not a first walk"
    other_root = {**rebound, "walk_log": [{"root": "/somewhere/else", "seconds": 0.0, "cache_miss": True}]}
    w = s4.judge_walk(stock, other_root, roots)
    assert w["measured"] is False and w["rebound"]["on_rebound_root"] is False
    assert s4.judge_seeded({"errors": {}, "mesh_seen": True, "model": "m"})["mesh_seen"] is True
    assert s4.judge_seeded({"errors": {"seeded": {"type": "E"}}, "mesh_seen": True})["measured"] is False
    assert s4.judge_seeded(None)["mesh_seen"] is None


def test_the_spec_imports_are_all_probed_and_the_negative_candidates_are_absent_from_pyodide(s4):
    for name in ("socket", "http.server", "webbrowser", "websockets", "websockets.asyncio.server",
                 "websockets.http11", "pylabrobot.visualizer3D", "pylabrobot.visualizer3D.server"):
        assert name in s4.ALL_IMPORTS, name
    assert set(s4.NEG_ABSENT_MODULES) == {"tkinter", "curses"}
    assert s4.PIN_SHA == "786ac2c4e4f7afe37885af2d98ff5b0afe274c67" and s4.PIN_VERSION_PREFIX == "1.0.0b1"


# --------------------------------------------------------------------------- #
# The kernel cells, run in CPython (a stand-in, not S4 evidence)
# --------------------------------------------------------------------------- #

CURRENT: dict[str, Any] = {}


def _fake_display(obj: Any, raw: bool = False, metadata: dict | None = None, **_kw: Any) -> None:
    CURRENT["outs"].append({"output_type": "display_data", "data": dict(obj), "metadata": dict(metadata or {})})


class FakeKernelDriver:
    """The ``PageKernelDriver`` interface over CPython: each cell's REAL source is compiled with
    top-level await and evaluated in one shared namespace; ``display`` bundles and an exception
    become the cell's outputs.
    """

    pageerrors: list[str] = []

    def __init__(self, s4: Any, sources: tuple[tuple[str, str], ...], *, loop: Any = None,
                 idle: bool = True, hang_cell: str | None = None) -> None:
        self.s4 = s4
        self.sources = dict(sources)
        self.ns: dict[str, Any] = {"__name__": "__main__"}
        self.loop = loop or asyncio.new_event_loop()
        self.idle, self.hang_cell = idle, hang_cell
        self.count = 0
        self.ran: list[str] = []

    def open(self) -> None:
        pass

    def wait_idle(self, timeout_s: float) -> bool:
        return self.idle

    def run_cell(self, name: str, timeout_s: float) -> dict[str, Any]:
        base = {"name": name, "index": self.s4.CELL_INDEX[name], "error": None, "execution_state": "idle",
                "seconds": 0.0}
        if name == self.hang_cell:
            return {**base, "state": "pending", "execution_count": None, "outputs": []}
        CURRENT["outs"] = []
        self.count += 1
        state = "resolved"
        try:
            code = compile(self.sources[name], f"<{name}>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
            result = eval(code, self.ns)
            if inspect.iscoroutine(result):
                self.loop.run_until_complete(result)
        except BaseException as exc:  # a cell that raises is an error output, as in the kernel
            state = "rejected"
            CURRENT["outs"].append({"output_type": "error", "ename": type(exc).__name__, "evalue": str(exc),
                                    "traceback": traceback.format_exc().splitlines()})
        outs = json.loads(json.dumps(CURRENT["outs"], default=str))
        self.ran.append(name)
        return {**base, "state": state, "execution_count": self.count,
                "outputs": [self.s4.trim_output(o) for o in outs]}


@pytest.fixture
def fake_ipython_modules(monkeypatch):
    ipy = types.ModuleType("IPython")
    disp = types.ModuleType("IPython.display")
    disp.display = _fake_display
    ipy.display = disp
    monkeypatch.setitem(sys.modules, "IPython", ipy)
    monkeypatch.setitem(sys.modules, "IPython.display", disp)


@pytest.fixture(scope="module")
def real_plr():
    """PLR's own ``pylabrobot.visualizer3D`` in this interpreter, or a skip."""
    tree = os.environ.get("PRAXIS_PLR_PIN_TREE")
    if tree and "pylabrobot" not in sys.modules:
        sys.path.insert(0, tree)
    try:
        import websockets  # noqa: F401
        from pylabrobot.visualizer3D import server
    except Exception as exc:  # not importable here (for example PLR 0.2.2): the cells cannot run
        pytest.skip(f"pylabrobot.visualizer3D is not importable in this interpreter ({type(exc).__name__}: {exc})")
    saved_root, saved_models = server.PACKAGE_ROOT, server._models_on_disk
    yield server
    server.PACKAGE_ROOT, server._models_on_disk = saved_root, saved_models


@pytest.fixture
def real_plr_clean(real_plr):
    """The module of ``real_plr`` with its two probed globals restored, and the ``_models_on_disk``
    cache emptied, around each test (a probe rebinds ``PACKAGE_ROOT``, wraps ``_models_on_disk``
    and fills its per-root cache; a fresh kernel starts with none of that)."""
    saved = (real_plr.PACKAGE_ROOT, real_plr._models_on_disk)
    saved[1].cache_clear()  # the walk cache is per process: a fresh kernel starts with it empty
    yield real_plr
    real_plr.PACKAGE_ROOT, real_plr._models_on_disk = saved
    saved[1].cache_clear()


@pytest.fixture
def plr_env(s4, real_plr_clean, fake_ipython_modules, monkeypatch):
    """Real ``visualizer3D`` plus a pin that reads as whatever PLR this interpreter has, so that a
    valid-run assertion does not depend on which PLR the environment carries (the pin itself is
    checked separately, and only where the pin's tree is present)."""
    import pylabrobot

    monkeypatch.setattr(s4, "PIN_VERSION_PREFIX", str(pylabrobot.__version__))
    try:
        info = importlib.import_module("pylabrobot._praxis_build_info")
        sha = getattr(info, "PLR_SOURCE_SHA", None)
    except ImportError:
        sha = None
    if sha:
        monkeypatch.setattr(s4, "PIN_SHA", sha)
    return real_plr_clean


NEG_ABSENT_IN_CPYTHON = ("s4_no_such_module_xyz",)


def run_fake(s4: Any, *, sources: tuple[tuple[str, str], ...] | None = None,
             neg: tuple[str, ...] = NEG_ABSENT_IN_CPYTHON, deadline_s: float = 600.0,
             **kd_kw: Any) -> dict[str, Any]:
    srcs = sources if sources is not None else s4.build_cell_sources(neg)
    kd = FakeKernelDriver(s4, srcs, **kd_kw)
    try:
        art = s4.run_viewer_probe(kd, time.monotonic() + deadline_s, neg)
    finally:
        kd.loop.close()
    return json.loads(json.dumps(art, default=str))


def mutate(s4: Any, cell: str, old: str, new: str, neg: tuple[str, ...] = NEG_ABSENT_IN_CPYTHON):
    out = []
    hit = False
    for name, src in s4.build_cell_sources(neg):
        if name == cell:
            assert old in src, f"mutation anchor missing in {cell}: {old!r}"
            src, hit = src.replace(old, new), True
        out.append((name, src))
    assert hit
    return tuple(out)


def test_kernel_cells_compile_with_top_level_await_and_await_cells_await(s4):
    assert s4.CELL_NAMES == ("warm", "setup", "imports", "hostname", "neg_import", "loop", "viewer_setup",
                             "viewer", "roots_stock", "roots_rebound", "seeded", "restore")
    for name, src in s4.CELL_SOURCES:
        compile(src, name, "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        try:
            compile(src, name, "exec")
            top_level_await = False
        except SyntaxError:
            top_level_await = True
        assert top_level_await == (name in {"loop", "viewer", "roots_stock", "roots_rebound", "seeded"}), name
    assert "@@" not in "".join(src for _, src in s4.CELL_SOURCES), "an unfilled placeholder"


def test_fixture_is_an_unexecuted_notebook_and_its_hash_follows_the_kernel_code(s4):
    fixture = s4.build_fixture()
    assert [c["id"] for c in fixture["cells"]][:3] == ["s4-warm", "s4-setup", "s4-imports"]
    assert all(c["execution_count"] is None and c["outputs"] == [] for c in fixture["cells"])
    assert len(fixture["cells"]) == len(s4.CELL_NAMES)
    changed = s4.build_cell_sources()
    changed = tuple((n, s + ("# edited\n" if n == "hostname" else "")) for n, s in changed)
    other = json.dumps(s4.build_fixture(changed), sort_keys=True, indent=1).encode()
    assert s4.sha256_bytes(other) != s4.sha256_bytes(s4.fixture_bytes())


def test_every_bundle_tag_a_cell_emits_is_the_one_the_driver_reads(s4):
    import re

    emitted = set()
    for _name, src in s4.CELL_SOURCES:
        emitted |= set(re.findall(r'_s4_emit\("(\w+)"', src))
    assert emitted == {"setup", "imports", "hostname", "neg_import", "loop", "viewer_setup", "viewer",
                       "roots_stock", "roots_rebound", "seeded", "final"}
    driver_src = DRIVER_PATH.read_text()
    for tag in emitted - {"final"}:
        assert f'"{tag}", "{tag}"' in driver_src or f'"{tag}")' in driver_src, f"no reader for {tag}"


def test_full_probe_over_the_real_visualizer3d_lands_on_s4_a_with_every_control(s4, plr_env):
    art = run_fake(s4)
    assert art.get("error") is None and art["sub_errors"] == {} and art["skipped"] == {}
    d = s4.derive_outcome_fields(art)
    flat = d["flat"]
    assert flat["measurement_valid"] is True, d["details"]["validity_checks"]
    assert flat["d1_branch"] == "S4-A" and flat["stubs_required"] == "none"
    # instrument sanity, CPython stand-in only: the stock root yields the pin's meshes, the rebound none,
    # the seeded control yields exactly one model's mesh, and the timed walks ran on their own roots
    assert flat["mesh_models_stock"] > 0 and flat["mesh_models_rebound"] == 0
    assert art["seeded_control"]["mesh_seen"] is True and art["seeded_control"]["only_the_seeded_model"] is True
    assert flat["walk_on_rebound_root"] is True and flat["rebound_root"] != flat["stock_root"]
    assert flat["rebound_root_empty"] is True and flat["rebind_idempotent"] is True
    assert flat["stock_root_in_plr_package"] is True and flat["stock_glb_count"] >= 1
    assert flat["first_scene_message_bytes"] > 1000 and art["scene"]["event_order"][:2] == ["scene", "state"]
    assert art["scene"]["handler_matches_encode"] is True and art["scene"]["hello_seen"] is True
    assert art["viewer"]["overrides"] == ["__init__", "start", "stop"]
    assert art["viewer"]["walk_calls_in_start"] == 0 and art["viewer"]["subscribed_after_stop"] == 0
    assert art["walk"]["rebound"]["n_models"] == 0 and art["walk"]["stock"]["n_models"] >= 1
    assert flat["plr_at_pin"] is True and flat["visualizer3d_present"] is True and flat["plr_version"]
    final = next(o for o in art["cells"]["restore"]["outputs"] if (o.get("metadata") or {}).get("s4") == "final")
    assert final["data"]["application/json"]["models_on_disk_restored"] is True


def test_a_negative_control_module_that_imports_makes_the_run_invalid(s4, plr_env):
    art = run_fake(s4, neg=("json",))
    flat = s4.derive_outcome_fields(art)["flat"]
    assert art["negative_control"]["failed_as_required"] is False
    assert art["negative_control"]["unexpected_success"] == ["json"]
    assert flat["measurement_valid"] is False and flat["invalid_reason"] == "negative_control_failed_as_required"
    assert flat["d1_branch"] is None


def test_a_dist_without_visualizer3d_fails_fast_records_the_version_and_is_invalid(s4, monkeypatch, fake_ipython_modules):
    """PLR 0.2.2 (the local 260828 dist) has no visualizer3D: the probe aborts after ``setup``,
    skips every later cell, records the PLR version it saw, and claims no branch.
    """
    real_find_spec = importlib.util.find_spec

    def find_spec(name: str, *a: Any, **k: Any):
        return None if name == "pylabrobot.visualizer3D" else real_find_spec(name, *a, **k)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec)
    srcs = s4.build_cell_sources(NEG_ABSENT_IN_CPYTHON)
    kd = FakeKernelDriver(s4, srcs)
    try:
        art = json.loads(json.dumps(s4.run_viewer_probe(kd, time.monotonic() + 600, NEG_ABSENT_IN_CPYTHON), default=str))
    finally:
        kd.loop.close()
    assert art["aborted"] == "visualizer3d_absent"
    assert kd.ran == ["warm", "setup"], "nothing after setup may run"
    assert art["plr"]["visualizer3d_present"] is False and art["plr"]["measured"] is True
    assert isinstance(art["plr"]["version"], str) and art["plr"]["version"], "the PLR version it saw is recorded"
    assert art["imports"] == {"measured": False, "records": None} and art["viewer"]["measured"] is False
    flat = s4.derive_outcome_fields(art)["flat"]
    assert flat["measurement_valid"] is False and flat["invalid_reason"] == "visualizer3d_present"
    assert flat["visualizer3d_present"] is False and flat["d1_branch"] is None
    assert flat["aborted"] == "visualizer3d_absent" and flat["plr_version"] == art["plr"]["version"]


def test_a_dist_that_is_not_the_pin_is_invalid_even_with_visualizer3d(s4, plr_env, monkeypatch):
    monkeypatch.setattr(s4, "PIN_SHA", "0" * 40)
    monkeypatch.setattr(s4, "PIN_VERSION_PREFIX", "9.9.9")
    art = run_fake(s4)
    flat = s4.derive_outcome_fields(art)["flat"]
    assert flat["plr_at_pin"] is False and flat["visualizer3d_present"] is True
    assert flat["measurement_valid"] is False and flat["invalid_reason"] == "plr_at_pin"
    assert flat["d1_branch"] is None


def test_the_local_pin_tree_reads_as_the_pin(s4, real_plr_clean, fake_ipython_modules):
    """Only where the installed-form copy of the pin (with its build info) is what is imported."""
    try:
        info = importlib.import_module("pylabrobot._praxis_build_info")
    except ImportError:
        pytest.skip("this PLR carries no _praxis_build_info (a checkout, not a built wheel)")
    if getattr(info, "PLR_SOURCE_SHA", None) != s4.PIN_SHA:
        pytest.skip("this PLR is not the pin")
    art = run_fake(s4)
    assert art["plr"]["at_pin"] is True and art["plr"]["pin_evidence"] == "sha"
    assert s4.derive_outcome_fields(art)["flat"]["plr_at_pin"] is True


class _NoCallLaterLoop(asyncio.SelectorEventLoop):
    """A loop whose ``call_later`` is unimplemented for the probe's own list-append timers only
    (asyncio.sleep needs the real one), standing in for a WebLoop that lacks ``call_later``."""

    def __init__(self, exc: type[BaseException], api: str) -> None:
        super().__init__()
        self._exc, self._api = exc, api

    def _probe_cb(self, cb: Any) -> bool:
        return isinstance(getattr(cb, "__self__", None), list)

    def call_later(self, delay, callback, *args, **kw):
        if self._api == "call_later" and self._probe_cb(callback):
            raise self._exc("call_later")
        return super().call_later(delay, callback, *args, **kw)

    def call_soon_threadsafe(self, callback, *args, **kw):
        if self._api == "call_soon_threadsafe" and self._probe_cb(callback):
            raise self._exc("call_soon_threadsafe")
        return super().call_soon_threadsafe(callback, *args, **kw)


def test_a_loop_without_call_later_is_the_s4_c_stop(s4, plr_env):
    art = run_fake(s4, loop=_NoCallLaterLoop(NotImplementedError, "call_later"))
    flat = s4.derive_outcome_fields(art)["flat"]
    assert art["loop"]["call_later_supported"] is False
    assert flat["measurement_valid"] is True and flat["d1_branch"] == "S4-C"


def test_a_loop_without_call_soon_threadsafe_is_unmapped_not_s4_c(s4, plr_env):
    art = run_fake(s4, loop=_NoCallLaterLoop(AttributeError, "call_soon_threadsafe"))
    flat = s4.derive_outcome_fields(art)["flat"]
    assert art["loop"]["call_soon_threadsafe_supported"] is False and art["loop"]["call_later_supported"] is True
    assert flat["measurement_valid"] is True, {k: v for k, v in s4.derive_outcome_fields(art)["details"]["validity_checks"].items() if not v}
    assert flat["d1_branch"] == "UNMAPPED"


def test_a_start_that_uses_a_thread_is_unmapped_and_a_raising_step_is_invalid(s4, plr_env):
    threaded = mutate(
        s4, "viewer_setup",
        "            self._legacy_bytes = _s4_legacy_size(self.root)  # synchronous: no threads\n",
        "            self._legacy_bytes = _s4_legacy_size(self.root)\n"
        "            try:\n"
        "                threading.Thread(target=lambda: None).start()\n"
        "            except RuntimeError:\n"
        "                pass\n")
    art = run_fake(s4, sources=threaded)
    flat = s4.derive_outcome_fields(art)["flat"]
    assert art["viewer"]["calls_during_start"]["thread_start"] == 1 and art["viewer"]["patch_control_ok"] is True
    assert flat["start_ok"] is True and flat["start_without_threads"] is False
    assert flat["measurement_valid"] is True, {k: v for k, v in s4.derive_outcome_fields(art)["details"]["validity_checks"].items() if not v}
    assert flat["d1_branch"] == "UNMAPPED"
    boom = mutate(
        s4, "viewer_setup",
        "            self._legacy_bytes = _s4_legacy_size(self.root)  # synchronous: no threads\n",
        "            raise RuntimeError('start blew up')\n")
    art = run_fake(s4, sources=boom)
    flat = s4.derive_outcome_fields(art)["flat"]
    assert art["viewer"]["start_ok"] is None and flat["start_ok"] is None, "a raised step is null, not False"
    assert flat["measurement_valid"] is False and flat["invalid_reason"] == "viewer_measured"
    assert flat["d1_branch"] is None


def test_an_unstubbed_stdlib_module_is_reported_as_s4_b_with_the_viewer_path_waived(s4, plr_env, monkeypatch):
    """Make ``http.server`` unimportable, as a missing stdlib module would be: the imports cell
    records the failure, the viewer cells are skipped and named, and the run is S4-B with the
    stub list, not invalid."""
    real_import = importlib.import_module

    def import_module(name: str, package: str | None = None):
        if name == "http.server":
            raise ModuleNotFoundError("No module named 'http.server'", name="http.server")
        return real_import(name, package)

    monkeypatch.setattr(importlib, "import_module", import_module)
    art = run_fake(s4)
    flat = s4.derive_outcome_fields(art)["flat"]
    assert art["imports"]["stdlib_failures"] == ["http.server"]
    assert set(art["skipped"]) == set(s4.VIEWER_CELLS) and art["viewer"]["measured"] is False
    assert flat["measurement_valid"] is True, {k: v for k, v in s4.derive_outcome_fields(art)["details"]["validity_checks"].items() if not v}
    assert flat["d1_branch"] == "S4-B" and flat["stubs_required"] == "http.server"


def test_a_cell_that_never_settles_aborts_the_rest_and_is_invalid(s4, plr_env):
    art = run_fake(s4, hang_cell="loop")
    assert art["aborted"] == "cell_timeout:loop"
    flat = s4.derive_outcome_fields(art)["flat"]
    assert flat["measurement_valid"] is False and flat["d1_branch"] is None
    assert art["cells"]["viewer_setup"]["state"] == "skipped" and "viewer" in art["skipped"]


def test_a_kernel_that_never_idles_and_a_hit_deadline_are_invalid(s4, fake_ipython_modules):
    art = run_fake(s4, idle=False)
    assert art["kernel_ready"] is False and art["aborted"] == "kernel_not_idle"
    assert s4.derive_outcome_fields(art)["flat"]["measurement_valid"] is False
    art = run_fake(s4, deadline_s=0.5)
    assert art["deadline_hit"] is True and s4.derive_outcome_fields(art)["flat"]["measurement_valid"] is False


def test_every_preregistered_field_is_returned_even_when_unmeasured(s4, fake_ipython_modules):
    art = run_fake(s4, idle=False)
    for name in s4.UNIT_BY_NAME[UNIT].required:
        assert name in art, name


def test_collect_sub_probes_catches_a_raise_and_keeps_the_others(s4):
    def boom(_r):
        raise ValueError("boom")

    results, errors = s4.collect_sub_probes({"a": lambda r: 1, "b": boom, "c": lambda r: r.get("a", 0) + 1})
    assert results == {"a": 1, "b": None, "c": 2}
    assert list(errors) == ["b"] and errors["b"]["type"] == "ValueError" and errors["b"]["message"] == "boom"
    assert 0 < len(errors["b"]["traceback_tail"].encode()) <= 4096


# --------------------------------------------------------------------------- #
# Stub launcher: the real driver code, stub probe/session/env
# --------------------------------------------------------------------------- #

STUB_SCRIPT = textwrap.dedent(
    """
    import importlib.util, json, os, sys, time
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("s4_driver", os.environ["S4_DRIVER"])
    m = importlib.util.module_from_spec(spec)
    sys.modules["s4_driver"] = m
    spec.loader.exec_module(m)
    PLAN = json.loads(os.environ["S4_STUB_PLAN"])
    FAKE = json.loads(os.environ["S4_STUB_ENV"])
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
            target = PLAN["sub_raise"]
            names = ["plr", "imports", "hostname", "negative_control", "loop", "viewer", "roots", "scene",
                     "walk", "seeded_control"]
            results, errs = m.collect_sub_probes({
                n: (lambda r, n=n: _raise(target + " blew up") if n == target else fields[n]) for n in names
            })
            fields.update(results)
            fields["sub_errors"] = errs
        if PLAN.get("drop_field"):
            fields.pop(PLAN["drop_field"], None)
        return fields


    m.PROBES = {m.UNIT_NAME: probe}
    sys.exit(m.main(
        sys.argv[1:],
        unit_argv_prefix=[sys.executable, os.path.abspath(__file__)],
        unit_timeout_s=float(os.environ.get("S4_STUB_TIMEOUT", "600")),
        driver_extra_s=float(os.environ.get("S4_STUB_EXTRA", "60")),
    ))
    """
)

FAKE_ENV = {
    "script": "s" * 64, "runner": "r" * 64, "harness": "h" * 64, "dist": "d" * 64, "fixture": "f" * 64,
    "chrome": "c" * 64, "driver": "v" * 64, "base_path": "/", "chrome_path": "", "chrome_version": "stub",
}


class Harness:
    def __init__(self, s4: Any, tmp_path: Path, fields: dict[str, Any]) -> None:
        self.m = s4
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
            S4_DRIVER=str(DRIVER_PATH), S4_STUB_PLAN=json.dumps(self.plan),
            S4_STUB_ENV=json.dumps(self.fake_env), S4_STUB_TIMEOUT=self.timeout,
            S4_STUB_EXTRA=self.extra, BTH_RESULTS_PATH=str(self.results),
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
def h(s4, tmp_path):
    return Harness(s4, tmp_path, good_fields(s4))


# --------------------------------------------------------------------------- #
# The unit table is the D17 S4 row
# --------------------------------------------------------------------------- #


def test_unit_table_is_the_d17_s4_row(s4):
    assert s4.UNIT_NAMES == ("viewer3d_pyodide",)
    assert s4.UNIT_TIMEOUT_S == 600.0 and s4.DRIVER_EXTRA_S == 60.0
    assert s4.UNIT_TIMEOUT_S * s4.DEADLINE_FRACTION == 540.0
    assert s4.UNIT_BY_NAME[UNIT].required[0] == "kernel_ready"


def test_sidecar_preregisters_the_unit_the_fields_and_the_d17_design(s4):
    text = SIDECAR_PATH.read_text()
    assert f"[design.units.{UNIT}]" in text
    for field in s4.UNIT_BY_NAME[UNIT].required:
        assert f'"{field}"' in text, field
    lowered = text.lower()
    for needle in ("os._exit", "driver", "harness", "600", "660", "unit_runner.watchdog", "unit_runner.run_unit",
                   "--resume", "error finding", "full unit set", "negative control", "tkinter", "curses",
                   "package_root", "_ensure_package_root", "[outcomes.invalid]", "is_residual = true",
                   "notebook model", "1.0.0b1", "786ac2c4e4f7afe37885af2d98ff5b0afe274c67", "0.2.2",
                   "visualizer3d_absent", "dist_at_the_pin", "mesh_models_rebound", "walk_rebound_seconds",
                   "first_scene_message_bytes", "stubs_required", "[outcomes.s4_a]", "[outcomes.s4_b]",
                   "[outcomes.s4_c]", "call_later", "call_soon_threadsafe", "10 min"):
        assert needle in lowered, needle
    for stanza in ("[design.timeouts]", "[design.cells]", "[design.derivations]", "[design.controls]"):
        assert stanza in text
    for inp in ("script", "runner", "harness", "dist", "fixture", "chrome", "driver", "args"):
        assert inp in text.split("hashed_inputs")[1].split("resume_rule")[0], inp


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
    assert plan["plr_pin"]["sha"] == "786ac2c4e4f7afe37885af2d98ff5b0afe274c67"
    assert "pylabrobot.visualizer3D" in plan["imports"] and "PLR 0.2.2" in plan["dist_requirement"]


# --------------------------------------------------------------------------- #
# Driver / unit / stamp / completeness / outcome gating (real subprocesses)
# --------------------------------------------------------------------------- #


def test_full_run_completes_stamps_and_evaluates_outcome_fields(h):
    code, agg = h.driver()
    assert code == 0
    assert agg["all_units_complete"] and agg["outcome_evaluated"] and agg["spike"] == "S4"
    assert agg["recomputed"] == [UNIT] and agg["reused"] == []
    art, stamp = h.artifact(), h.stamp()
    raw = h.m.unit_paths(h.out, UNIT)["artifact"].read_bytes()
    assert stamp["artifact_sha256"] == h.m.sha256_bytes(raw)
    assert stamp["exit"] == 0 and stamp["unit"] == UNIT and stamp["timeout_s"] == 600.0
    assert art["error"] is None and art["pageerrors"] == ["stub pageerror"] and art["missing_fields"] == []
    assert set(stamp["inputs"]) == {"script", "runner", "harness", "dist", "fixture", "chrome", "driver", "args"}
    flat = json.loads(h.results.read_text())
    assert flat["measurement_valid"] is True and flat["d1_branch"] == "S4-A" and flat["stubs_required"] == "none"
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


def test_build_env_hashes_repl_smoke_as_the_harness_input_and_the_fixture_from_the_cells(s4, tmp_path, monkeypatch):
    """D17 / AC-29: the driver loads ``repl_smoke.py`` (``ServedDir``, ``chromium_launch_args``,
    ``resolve_chrome_path``), so its sha256 is the ``harness`` input, in driver mode and
    ``--unit`` mode alike (both call ``build_env``); the ``fixture`` input is the hash of the
    seeded notebook built from the kernel cells (the probe's kernel code).
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
    monkeypatch.setattr(s4, "REPL_SMOKE_PATH", smoke)
    # ``uv.lock`` is gitignored (absent in a fresh worktree); this test is about ``harness``
    monkeypatch.setattr(s4.unit_runner, "driver_input", lambda **kw: "v" * 64)
    monkeypatch.setattr(
        s4, "repl_smoke", lambda: types.SimpleNamespace(resolve_chrome_path=lambda explicit: chrome)
    )
    args = argparse.Namespace(chrome_path=None, dist=str(dist), base_path="/")
    env1 = s4.build_env(args)
    assert env1.harness == s4.sha256_file(smoke)
    assert env1.harness != env1.runner and env1.harness != env1.script
    assert env1.fixture == s4.sha256_bytes(s4.fixture_bytes())
    smoke.write_text("# harness v2\n")
    env2 = s4.build_env(args)
    assert env2.harness != env1.harness
    assert env2.runner == env1.runner and env2.script == env1.script and env2.fixture == env1.fixture
    inputs = s4.compute_inputs(UNIT, env2)
    assert inputs["harness"] == env2.harness
    assert set(inputs) == {"script", "runner", "harness", "dist", "fixture", "chrome", "driver", "args"}
    (dist / "a.txt").write_text("b")  # the dist hash covers the PLR wheel that carries visualizer3D
    assert s4.build_env(args).dist != env2.dist


def test_a_headless_shell_is_refused(s4, tmp_path, monkeypatch):
    import argparse

    shell = tmp_path / "chrome-headless-shell"
    shell.write_text("#!/bin/sh\n")
    shell.chmod(0o755)
    monkeypatch.setattr(s4, "repl_smoke", lambda: types.SimpleNamespace(resolve_chrome_path=lambda e: shell))
    with pytest.raises(RuntimeError, match="FULL Chromium"):
        s4.build_env(argparse.Namespace(chrome_path=None, dist=str(tmp_path), base_path="/"))


def test_a_tampered_artifact_is_not_reused(h):
    h.driver()
    path = h.m.unit_paths(h.out, UNIT)["artifact"]
    path.write_text(path.read_text().replace('"version": "1.0.0b1+g786ac2c4"', '"version": "0.0.0"'))
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
    assert flat["d1_branch"] is None and flat["invalid_reason"] == "no_error_findings"
    # resume: the errored unit is recomputed
    h.plan.pop("raise")
    _, agg2 = h.driver("--resume")
    assert agg2["recomputed"] == [UNIT] and h.count() == 2
    assert json.loads(h.results.read_text())["measurement_valid"] is True


def test_a_raised_sub_probe_becomes_the_units_error_finding_and_is_never_reused(h):
    h.plan["sub_raise"] = "loop"
    code, agg = h.driver()
    assert code == 0 and agg["outcome_evaluated"]
    art = h.artifact()
    assert art["error"]["sub_probe"] == "loop" and art["error"]["type"] == "ValueError"
    assert art["error"]["message"] == "loop blew up" and list(art["sub_errors"]) == ["loop"]
    assert art["loop"] is None and art["viewer"] is not None and art["scene"] is not None, "later sub-probes kept"
    assert h.stamp()["exit"] == 1
    flat = json.loads(h.results.read_text())
    assert flat["measurement_valid"] is False and flat["n_error_units"] == 1 and flat["d1_branch"] is None
    assert agg["validity_checks"]["no_error_findings"] is False
    h.plan.pop("sub_raise")
    _, agg2 = h.driver("--resume")
    assert agg2["recomputed"] == [UNIT] and agg2["reused"] == []


def test_a_negative_control_that_errors_through_the_driver_is_not_failed_as_required(h):
    h.plan["sub_raise"] = "negative_control"
    code, agg = h.driver()
    assert code == 0 and agg["outcome_evaluated"]
    art = h.artifact()
    assert art["negative_control"] is None and art["error"]["sub_probe"] == "negative_control"
    flat = json.loads(h.results.read_text())
    assert flat["negative_control_failed_as_required"] is None, "an errored control has NOT failed as required"
    assert flat["measurement_valid"] is False and flat["d1_branch"] is None
    assert h.stamp()["exit"] == 1


def test_plr_without_visualizer3d_maps_to_invalid_through_the_driver(h, s4):
    """The wrong-dist case end to end through driver, unit, stamp and outcome fields: no branch."""
    h.plan["fields"] = variant(
        s4, plr__visualizer3d_present=False, plr__at_pin=False, plr__version="0.2.2+gdd79c4c8",
        plr__source_sha=None, aborted="visualizer3d_absent")
    for k in ("imports", "hostname", "loop", "viewer", "roots", "scene", "walk", "seeded_control", "negative_control"):
        h.plan["fields"][k] = None
    code, agg = h.driver()
    assert code == 0 and agg["outcome_evaluated"]
    flat = json.loads(h.results.read_text())
    assert flat["measurement_valid"] is False and flat["d1_branch"] is None
    assert flat["invalid_reason"] == "visualizer3d_present" and flat["visualizer3d_present"] is False
    assert flat["plr_version"] == "0.2.2+gdd79c4c8" and flat["aborted"] == "visualizer3d_absent"
    assert h.stamp()["exit"] == 0, "an invalid measurement is still a complete, clean unit"


def test_missing_preregistered_field_is_exit_1_and_not_reusable(h):
    h.plan["drop_field"] = "walk"
    h.driver()
    assert h.stamp()["exit"] == 1 and h.artifact()["missing_fields"] == ["walk"]
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


def test_run_unit_timeout_over_a_valid_stamp_defers_to_the_stamp(s4, h, monkeypatch, caplog):
    import argparse

    class Wrapper:
        """The real runner, but it reports a timeout even though the unit stamped."""

        def run_unit(self, argv, timeout_s, **kw):
            real = s4.unit_runner.run_unit(argv, timeout_s, **kw)
            return real._replace(timed_out=True, killed=True)

    for k, v in h.env().items():
        monkeypatch.setenv(k, v)
    args = argparse.Namespace(out_dir=str(h.out), resume=False, dist=str(h.tmp), base_path="/", chrome_path=None)
    with caplog.at_level("WARNING"):
        code = s4.run_driver(
            args, unit_argv_prefix=[sys.executable, str(h.stub)], runner=Wrapper(),
            env=s4.InputEnv(**FAKE_ENV), unit_timeout_s=600.0, driver_extra_s=60.0,
        )
    assert code == 0
    agg = json.loads((h.out / "result.json").read_text())
    assert agg["timed_out"] == [] and agg["recomputed"] == [UNIT]
    assert "the stamp governs" in caplog.text


def test_missing_plr_submodule_only_affects_real_browser_mode(s4, tmp_path, monkeypatch, caplog):
    """The driver loads ``repl_smoke.py`` lazily, only in real browser mode: the stub runs above
    never load it. If it fails to load for ANY reason (a stand-in that raises at import here)
    ``--dry-run`` degrades to a ``chrome_error`` note and a real driver run exits 2 with nothing
    started.
    """
    import argparse

    broken = tmp_path / "repl_smoke_broken.py"
    broken.write_text("class VizCheckError(RuntimeError): pass\nraise VizCheckError('no submodule')\n")
    monkeypatch.setattr(s4, "REPL_SMOKE_PATH", broken)
    monkeypatch.setattr(s4, "_REPL_SMOKE", None)
    args = argparse.Namespace(out_dir=str(tmp_path / "out"), resume=False, dist=str(tmp_path),
                              base_path="/", chrome_path=None, dry_run=True)
    assert s4._dry_run(args) == 0
    monkeypatch.setattr(s4, "_REPL_SMOKE", None)
    args.dry_run = False
    with caplog.at_level("ERROR"):
        assert s4.run_driver(args) == 2
    assert "cannot build the input set" in caplog.text
    assert not list((tmp_path / "out" / "units").glob("*")), "no unit may be started"


# --------------------------------------------------------------------------- #
# The in-page JS under a JS engine (fake notebook model): positive AND negative controls
# --------------------------------------------------------------------------- #

JS_ENGINE = shutil.which("node") or shutil.which("bun")
needs_js = pytest.mark.skipif(JS_ENGINE is None, reason="needs node or bun")


def _run_js(s4: Any, body: str, tmp_path: Path) -> Any:
    script = tmp_path / "probe_lib_test.js"
    script.write_text(
        "globalThis.window = globalThis;\n"
        "globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);\n"
        + s4.S4_JS
        + ";\nconst S = window.__s4;\n"
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
def test_js_run_cell_selects_the_cell_and_state_follows_the_command_promise(s4, tmp_path):
    out = _run_js(
        s4,
        FAKE_NB
        + """
        S.runCell(2, 'cell:x');
        const before = S.runState('cell:x');
        pending.res(true);
        await sleep(10);
        S.runCell(1, 'cell:y');
        const single = executed[1];
        pending.rej(new Error('kernel error'));
        await sleep(10);
        console.log(JSON.stringify({executed: executed[0], single, before, after: S.runInfo('cell:x'),
                                    rejected: S.runInfo('cell:y'), unknown: S.runState('nope'), status: S.kernelStatus()}));
        """,
        tmp_path,
    )
    assert out["executed"] == {"id": "notebook:run-cell", "active": 2, "selected": []}
    assert out["single"]["active"] == 1 and out["single"]["selected"] == []
    assert out["before"] == "pending" and out["after"]["state"] == "resolved" and out["after"]["value"] is True
    assert out["rejected"]["state"] == "rejected" and "kernel error" in out["rejected"]["error"]
    assert out["unknown"] is None and out["status"] == "idle"  # an unknown key is "unknown", never settled


@needs_js
def test_js_cell_read_returns_model_outputs_and_null_for_a_missing_cell(s4, tmp_path):
    out = _run_js(
        s4,
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
def test_js_command_that_throws_synchronously_is_a_rejected_run(s4, tmp_path):
    out = _run_js(
        s4,
        FAKE_NB
        + """
        window.jupyterapp.commands.execute = () => { throw new Error('no such command'); };
        S.runCell(0, 'cell:z');
        console.log(JSON.stringify(S.runInfo('cell:z')));
        """,
        tmp_path,
    )
    assert out["state"] == "rejected" and "no such command" in out["error"]
