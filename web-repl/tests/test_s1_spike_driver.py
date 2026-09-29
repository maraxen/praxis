"""No-browser plumbing checks for the S1 spike driver (epic 260929_notebook-display-design, A1b-1).

``scripts/spikes/260929_s1_lumino_widget.py`` is the pre-registered S1 probe. Nothing here
launches Playwright or Chromium and nothing here measures S1: it proves the DRIVER, UNIT,
STAMP, RESUME, COMPLETENESS and OUTCOME-GATING plumbing (D17) against a stub probe registry,
so that when the real run happens a plumbing bug cannot be mistaken for a finding.

Every unit runs as a REAL subprocess (``scripts/unit_runner.run_unit``, real ``Watchdog``,
real stamps), started through a tiny stub launcher that loads the driver by path and swaps
in the stub probes / session / input environment. Timeouts are shrunk through the
``main(..., unit_timeout_s=, driver_extra_s=)`` parameters (never a CLI flag: the real
budget is fixed at 4 min and pre-registered).

The pure derivations (sizing case, AC-36 width-key statuses, cell-hook uniqueness, re-attach
signal priority, validity) are tested directly. The in-page JS (structural constructor
check, negative control, layout-sizing edit) is exercised under ``node``/``bun`` against a
fake Lumino class hierarchy, with the positive control (a real root class passes) AND the
negative controls (wrong candidates fail; a shell whose root lacks the methods makes the
negative control NOT count as failed-as-required); those cases skip when no JS engine exists.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "spikes" / "260929_s1_lumino_widget.py"
SIDECAR_PATH = DRIVER_PATH.with_suffix(".bth.toml")

pytestmark = pytest.mark.timeout(180)


@pytest.fixture(scope="module")
def s1():
    spec = importlib.util.spec_from_file_location("s1_driver_under_test", DRIVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["s1_driver_under_test"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# Stub launcher: the real driver code, stub probes/session/env
# --------------------------------------------------------------------------- #

STUB_SCRIPT = textwrap.dedent(
    '''
    import importlib.util, json, os, sys, time
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("s1_driver", os.environ["S1_DRIVER"])
    m = importlib.util.module_from_spec(spec)
    sys.modules["s1_driver"] = m
    spec.loader.exec_module(m)
    PLAN = json.loads(os.environ["S1_STUB_PLAN"])
    FAKE = json.loads(os.environ["S1_STUB_ENV"])
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
            if self.unit in PLAN.get("close_hang", []):
                time.sleep(600)


    m.SESSION_FACTORY = lambda unit, args, env: Sess(unit, args.out_dir)


    def make_probe(unit):
        def probe(sess, ctx):
            out = Path(ctx.args.out_dir)
            with open(out / f"count.{unit}", "a") as fh:
                fh.write("x\\n")
            if unit in PLAN.get("hang", []):
                time.sleep(600)
            if unit in PLAN.get("raise", {}):
                raise ValueError(PLAN["raise"][unit])
            return dict(PLAN["fields"][unit])
        return probe


    m.PROBES = {u: make_probe(u) for u in m.UNIT_NAMES}
    sys.exit(m.main(
        sys.argv[1:],
        unit_argv_prefix=[sys.executable, os.path.abspath(__file__)],
        unit_timeout_s=float(os.environ.get("S1_STUB_TIMEOUT", "240")),
        driver_extra_s=float(os.environ.get("S1_STUB_EXTRA", "60")),
    ))
    '''
)

FAKE_ENV = {
    "script": "s" * 64, "runner": "r" * 64, "harness": "h" * 64, "dist": "d" * 64, "fixture": "f" * 64,
    "chrome": "c" * 64, "driver": "v" * 64, "base_path": "/", "chrome_path": "", "chrome_version": "stub",
}


def _fill(m: Any, unit: str, **over: Any) -> dict[str, Any]:
    fields = {name: None for name in m.UNIT_BY_NAME[unit].required}
    fields.update(over)
    return fields


def happy_fields(m: Any) -> dict[str, dict[str, Any]]:
    """A complete, internally consistent S1-A / css honoured / layout reachable run."""
    states = {s: True for s in m.STATES}
    hooks = {s: {"css": [], "dom_text": [], "model": ["x"], "mechanism": "model", "via": None} for s in m.STATES}
    src = {"widget_source": "S1-A"}
    return {
        "widget_a": _fill(m, "widget_a", usable=True, structural_found=True, chain=[], root_index=3,
                          root_ctor_name="Widget", constructed_ok=True, is_widget_instance=True,
                          attached_ok=True, split_right_ok=True, recipe={}, reason=None),
        "widget_b": _fill(m, "widget_b", usable=False, command_registered=False, widget_created=False,
                          iframe_found=False, split_right_ok=False, recipe={}, reason="stub"),
        "split_right": _fill(m, "split_right", split_right_ok=True, side_by_side=True, orientation="horizontal", **src),
        "css_limits": _fill(m, "css_limits", css_limits_honoured=True, drag_control_ok=True, **src),
        "dock_layout_sizing": _fill(m, "dock_layout_sizing", dock_layout_sizing_reachable=True, **src),
        "css_limits_refit": _fill(m, "css_limits_refit", css_limits_refit=True, **src),
        "restore_layout_keeps_iframe": _fill(m, "restore_layout_keeps_iframe", restore_layout_keeps_iframe=True,
                                             reload_control_detected=True, **src),
        "cell_hooks": _fill(m, "cell_hooks", kernel_ready=True, states_reached=states, all_states_reached=True,
                            snapshots={}, hooks=hooks, all_states_derivable=True, n_states_with_css_hook=0),
        "windowing": _fill(m, "windowing", windowing_mode="full", windowing_mode_reads={}, windowing_exercised=True,
                           detach_observed=True, reattach_raw={}, reattach_signal="inViewportChanged", cell_count=65),
        "neg_wrong_ctor": _fill(m, "neg_wrong_ctor", positive_control_structural_pass=True, wrong_candidates=[],
                                negative_control_failed_as_required=True),
    }


class Harness:
    def __init__(self, s1: Any, tmp_path: Path) -> None:
        self.m = s1
        self.tmp = tmp_path
        self.out = tmp_path / "out"
        self.stub = tmp_path / "stub_launcher.py"
        self.stub.write_text(STUB_SCRIPT)
        self.results = tmp_path / "bth_results.json"
        self.plan: dict[str, Any] = {"fields": happy_fields(s1)}
        self.fake_env = dict(FAKE_ENV)
        self.timeout = "240"
        self.extra = "60"

    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k != "PRAXIS_UNIT_TOKEN"}
        env.update(
            S1_DRIVER=str(DRIVER_PATH), S1_STUB_PLAN=json.dumps(self.plan),
            S1_STUB_ENV=json.dumps(self.fake_env), S1_STUB_TIMEOUT=self.timeout,
            S1_STUB_EXTRA=self.extra, BTH_RESULTS_PATH=str(self.results),
        )
        return env

    def cmd(self, *extra: str) -> list[str]:
        return [sys.executable, str(self.stub), "--out-dir", str(self.out), "--dist", str(self.tmp), *extra]

    def driver(self, *extra: str) -> tuple[int, dict[str, Any]]:
        proc = subprocess.run(self.cmd(*extra), env=self.env(), capture_output=True, text=True, timeout=170)
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip().startswith("{")]
        assert lines, f"no aggregate JSON on stdout.\nstdout={proc.stdout!r}\nstderr={proc.stderr[-3000:]}"
        return proc.returncode, json.loads(lines[-1])

    def unit(self, name: str) -> int:
        return subprocess.run(
            self.cmd("--unit", name), env=self.env(), capture_output=True, text=True, timeout=120
        ).returncode

    def count(self, unit: str) -> int:
        p = self.out / f"count.{unit}"
        return len(p.read_text().split()) if p.exists() else 0

    def artifact(self, unit: str) -> dict[str, Any]:
        return json.loads(self.m.unit_paths(self.out, unit)["artifact"].read_text())

    def stamp(self, unit: str) -> dict[str, Any]:
        return json.loads(self.m.unit_paths(self.out, unit)["stamp"].read_text())


@pytest.fixture()
def h(s1, tmp_path):
    return Harness(s1, tmp_path)


# --------------------------------------------------------------------------- #
# The unit table is the D17 S1 row
# --------------------------------------------------------------------------- #


def test_unit_table_is_the_d17_s1_row(s1):
    assert s1.UNIT_NAMES == (
        "widget_a", "widget_b", "split_right", "css_limits", "dock_layout_sizing",
        "css_limits_refit", "restore_layout_keeps_iframe", "cell_hooks", "windowing", "neg_wrong_ctor",
    )
    assert s1.UNIT_TIMEOUT_S == 240.0 and s1.DRIVER_EXTRA_S == 60.0
    for name in ("split_right", "css_limits", "dock_layout_sizing", "css_limits_refit", "restore_layout_keeps_iframe"):
        assert s1.UNIT_BY_NAME[name].upstream == ("widget_a", "widget_b"), name
    for name in ("widget_a", "widget_b", "cell_hooks", "windowing", "neg_wrong_ctor"):
        assert s1.UNIT_BY_NAME[name].upstream == (), name


def test_sidecar_preregisters_every_unit_and_required_field(s1):
    text = SIDECAR_PATH.read_text()
    for unit in s1.UNITS:
        assert f"[design.units.{unit.name}]" in text, unit.name
        for field in unit.required:
            assert f'"{field}"' in text, (unit.name, field)
    assert "neg_wrong_ctor" in text and "os._exit" in text


def test_dry_run_prints_the_plan_and_launches_nothing():
    proc = subprocess.run(
        [sys.executable, str(DRIVER_PATH), "--dry-run", "--out-dir", "unused"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    plan = json.loads(proc.stdout)
    assert [u["name"] for u in plan["units"]][0] == "widget_a" and len(plan["units"]) == 10
    assert plan["unit_timeout_s"] == 240.0 and plan["driver_timeout_s"] == 300.0


# --------------------------------------------------------------------------- #
# Driver / unit / stamp / completeness / outcome gating (real subprocesses)
# --------------------------------------------------------------------------- #


def test_full_run_completes_stamps_and_evaluates_outcome_fields(h):
    code, agg = h.driver()
    assert code == 0
    assert agg["all_units_complete"] and agg["outcome_evaluated"]
    assert agg["recomputed"] == list(h.m.UNIT_NAMES) and agg["reused"] == []
    for unit in h.m.UNIT_NAMES:
        art, stamp = h.artifact(unit), h.stamp(unit)
        raw = h.m.unit_paths(h.out, unit)["artifact"].read_bytes()
        assert stamp["artifact_sha256"] == h.m.sha256_bytes(raw)
        assert stamp["exit"] == 0 and stamp["unit"] == unit and stamp["timeout_s"] == 240.0
        assert art["error"] is None and art["pageerrors"] == ["stub pageerror"]
        assert set(stamp["inputs"]) >= {"script", "runner", "harness", "dist", "fixture", "chrome", "driver", "args"}
    # downstream stamps carry the upstream artifact hashes; independent units do not
    up = h.stamp("css_limits")["inputs"]
    assert up["upstream:widget_a"] == h.stamp("widget_a")["artifact_sha256"]
    assert up["upstream:widget_b"] == h.stamp("widget_b")["artifact_sha256"]
    assert not any(k.startswith("upstream:") for k in h.stamp("neg_wrong_ctor")["inputs"])
    flat = json.loads(h.results.read_text())
    assert flat["measurement_valid"] is True
    assert flat["widget_branch"] == "S1-A" and flat["d1_branch"] == "S1-A"
    assert flat["sizing_case"] == "honoured_reachable" and flat["sizing_branch"] == "css_limits"
    assert flat["negative_control_failed_as_required"] is True
    assert agg["width_key_status"]["case"] == "honoured_reachable"


def test_teardown_order_artifact_then_close_then_stamp(h):
    h.driver()
    for unit in h.m.UNIT_NAMES:
        closed = json.loads((h.out / f"closed.{unit}.json").read_text())
        assert closed["saw_artifact"] is True, f"{unit}: artifact must exist before teardown"
        assert closed["saw_stamp"] is False, f"{unit}: stamp must be committed AFTER teardown"
        assert h.stamp(unit)["finished"] >= closed["t"]


def test_resume_reuses_verified_units_and_records_source_and_hashes(h):
    h.driver()
    code, agg = h.driver("--resume")
    assert code == 0 and agg["recomputed"] == [] and len(agg["reused"]) == 10
    for rec in agg["reused"]:
        assert rec["source"].endswith(f"units/{rec['unit']}.json")
        assert rec["artifact_sha256"] == h.stamp(rec["unit"])["artifact_sha256"]
        assert set(rec["inputs"]) >= {"script", "runner", "harness", "dist", "fixture", "chrome", "driver"}
    assert all(h.count(u) == 1 for u in h.m.UNIT_NAMES), "a reused unit must not run again"
    # outcomes are still evaluated over the FULL unit set when everything was reused
    assert agg["outcome_evaluated"] and json.loads(h.results.read_text())["measurement_valid"] is True


def test_without_resume_everything_is_recomputed(h):
    h.driver()
    _, agg = h.driver()
    assert len(agg["recomputed"]) == 10 and all(h.count(u) == 2 for u in h.m.UNIT_NAMES)


@pytest.mark.parametrize("changed", ["chrome", "driver", "dist", "fixture", "runner", "script", "harness"])
def test_input_mismatch_forces_recompute(h, changed):
    h.driver()
    h.fake_env[changed] = "0" * 64
    _, agg = h.driver("--resume")
    assert agg["reused"] == [] and len(agg["recomputed"]) == 10
    assert all(h.count(u) == 2 for u in h.m.UNIT_NAMES)
    assert all(changed in rec["mismatched"] for rec in agg["stale"])


def test_build_env_hashes_repl_smoke_as_the_harness_input(s1, tmp_path, monkeypatch):
    """D17 / AC-1 "Units": the driver loads ``repl_smoke.py`` (``ServedDir``,
    ``chromium_launch_args``, ``resolve_chrome_path``), so its sha256 is the ``harness``
    input, in driver mode and ``--unit`` mode alike (both call ``build_env``). Amended
    before the first S1 run (round 11 C11-3 / round 12 C12-3)."""
    import argparse
    import types

    smoke = tmp_path / "repl_smoke_stub.py"
    smoke.write_text("# harness v1\n")
    chrome = tmp_path / "chrome"
    chrome.write_text("#!/bin/sh\necho stub-chrome 1\n")
    chrome.chmod(0o755)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "a.txt").write_text("a")
    monkeypatch.setattr(s1, "REPL_SMOKE_PATH", smoke)
    # ``uv.lock`` is gitignored (absent in a fresh worktree); this test is about ``harness``
    monkeypatch.setattr(s1.unit_runner, "driver_input", lambda **kw: "v" * 64)
    monkeypatch.setattr(
        s1, "repl_smoke", lambda: types.SimpleNamespace(resolve_chrome_path=lambda explicit: chrome)
    )
    args = argparse.Namespace(chrome_path=None, dist=str(dist), base_path="/")
    env1 = s1.build_env(args)
    assert env1.harness == s1.sha256_file(smoke)
    assert env1.harness != env1.runner and env1.harness != env1.script
    smoke.write_text("# harness v2\n")
    env2 = s1.build_env(args)
    assert env2.harness != env1.harness
    assert env2.runner == env1.runner and env2.script == env1.script
    # and it reaches the stamp inputs for every unit, with the other inputs unchanged
    inputs = s1.compute_inputs("widget_a", env2, {})
    assert inputs["harness"] == env2.harness
    assert {"script", "runner", "harness", "dist", "fixture", "chrome", "driver", "args"} <= set(inputs)


def test_a_tampered_artifact_is_not_reused(h):
    h.driver()
    path = h.m.unit_paths(h.out, "windowing")["artifact"]
    path.write_text(path.read_text().replace('"full"', '"none"'))
    _, agg = h.driver("--resume")
    assert agg["recomputed"] == ["windowing"] and len(agg["reused"]) == 9
    assert h.count("windowing") == 2


def test_recomputed_widget_unit_invalidates_the_units_that_build_on_it(h):
    h.driver()
    h.plan["fields"]["widget_a"]["reason"] = "changed on the second computation"
    assert h.unit("widget_a") == 0  # recomputed directly: new artifact hash, own stamp valid
    _, agg = h.driver("--resume")
    downstream = {"split_right", "css_limits", "dock_layout_sizing", "css_limits_refit", "restore_layout_keeps_iframe"}
    assert set(agg["recomputed"]) == downstream
    assert {r["unit"] for r in agg["reused"]} == set(h.m.UNIT_NAMES) - downstream
    assert all("upstream:widget_a" in rec["mismatched"] for rec in agg["stale"])


def test_error_finding_is_complete_counts_against_outcomes_and_is_never_reused(h):
    h.plan["raise"] = {"css_limits": "probe blew up"}
    code, agg = h.driver()
    assert code == 0 and agg["outcome_evaluated"], "a raised probe is a COMPLETE unit"
    err = h.artifact("css_limits")["error"]
    assert err["type"] == "ValueError" and err["message"] == "probe blew up"
    assert 0 < len(err["traceback_tail"].encode()) <= 4096
    assert h.stamp("css_limits")["exit"] == 1
    assert agg["error_findings"]["css_limits"]["type"] == "ValueError"
    flat = json.loads(h.results.read_text())
    assert flat["measurement_valid"] is False and flat["n_error_units"] == 1
    assert agg["validity_checks"]["no_error_findings"] is False
    # resume: the errored unit is recomputed, everything else reused
    h.plan.pop("raise")
    _, agg2 = h.driver("--resume")
    assert agg2["recomputed"] == ["css_limits"] and len(agg2["reused"]) == 9
    assert h.count("css_limits") == 2 and json.loads(h.results.read_text())["measurement_valid"] is True


def test_negative_control_that_errors_has_not_failed_as_required(h):
    h.plan["raise"] = {"neg_wrong_ctor": "boom"}
    _, agg = h.driver()
    flat = json.loads(h.results.read_text())
    assert flat["measurement_valid"] is False
    assert flat["negative_control_failed_as_required"] is None
    assert agg["validity_checks"]["negative_control_failed_as_required"] is False


def test_missing_preregistered_field_is_exit_1_and_not_reusable(h):
    del h.plan["fields"]["windowing"]["cell_count"]
    _, agg = h.driver()
    assert h.stamp("windowing")["exit"] == 1 and h.artifact("windowing")["missing_fields"] == ["cell_count"]
    h.plan["fields"]["windowing"]["cell_count"] = 65
    _, agg2 = h.driver("--resume")
    assert agg2["recomputed"] == ["windowing"]


def test_timeout_leaves_no_stamp_no_artifact_and_blocks_outcome_evaluation(h):
    h.plan["hang"] = ["neg_wrong_ctor"]
    h.timeout, h.extra = "6", "20"
    code, agg = h.driver()
    assert code == 3
    assert agg["all_units_complete"] is False and agg["outcome_evaluated"] is False
    assert agg["timed_out"] == ["neg_wrong_ctor"] and agg["incomplete"] == ["neg_wrong_ctor"]
    paths = h.m.unit_paths(h.out, "neg_wrong_ctor")
    assert not paths["stamp"].exists() and not paths["artifact"].exists()
    marker = json.loads(paths["timeout"].read_text())
    assert marker["unit"] == "neg_wrong_ctor" and marker["budget_s"] == 6.0
    assert agg["units"]["neg_wrong_ctor"]["exit"] == 124
    assert not h.results.exists(), "no outcome may be written for an incomplete run"
    assert "outcome_fields" not in agg
    # the other nine units are complete and reusable by the next run
    h.plan.pop("hang")
    code2, agg2 = h.driver("--resume")
    assert code2 == 0 and agg2["recomputed"] == ["neg_wrong_ctor"] and len(agg2["reused"]) == 9
    assert h.results.exists()


def test_hang_in_teardown_is_a_timeout_not_a_stamp(h):
    h.plan["close_hang"] = ["windowing"]
    h.timeout, h.extra = "6", "20"
    code, agg = h.driver()
    assert code == 3 and agg["timed_out"] == ["windowing"]
    paths = h.m.unit_paths(h.out, "windowing")
    assert not paths["stamp"].exists() and not paths["artifact"].exists(), "teardown hangs are bounded BEFORE the stamp"


def test_upstream_timeout_blocks_dependents_which_are_never_started(h):
    h.plan["hang"] = ["widget_a"]
    h.timeout, h.extra = "6", "20"
    code, agg = h.driver()
    assert code == 3 and agg["timed_out"] == ["widget_a"]
    dependents = ["split_right", "css_limits", "dock_layout_sizing", "css_limits_refit", "restore_layout_keeps_iframe"]
    assert agg["blocked"] == dependents
    assert all(h.count(u) == 0 for u in dependents)
    assert not h.results.exists()


def test_unit_with_incomplete_upstream_exits_3_without_a_stamp(h):
    assert h.unit("css_limits") == 3
    assert not h.m.unit_paths(h.out, "css_limits")["stamp"].exists()


def test_run_unit_timeout_over_a_valid_stamp_defers_to_the_stamp(s1, h, monkeypatch, caplog):
    import argparse

    class Wrapper:
        """The real runner, but it reports a timeout even though the unit stamped."""
        def run_unit(self, argv, timeout_s, **kw):
            real = s1.unit_runner.run_unit(argv, timeout_s, **kw)
            return real._replace(timed_out=True, killed=True)

    for k, v in h.env().items():
        monkeypatch.setenv(k, v)
    args = argparse.Namespace(out_dir=str(h.out), resume=False, dist=str(h.tmp), base_path="/", chrome_path=None)
    with caplog.at_level("WARNING"):
        code = s1.run_driver(
            args, unit_argv_prefix=[sys.executable, str(h.stub)], runner=Wrapper(),
            env=s1.InputEnv(**FAKE_ENV), unit_timeout_s=240.0, driver_extra_s=60.0,
        )
    assert code == 0
    agg = json.loads((h.out / "result.json").read_text())
    assert agg["timed_out"] == [] and agg["recomputed"] == list(s1.UNIT_NAMES)
    assert "the stamp governs" in caplog.text


def test_missing_plr_submodule_only_affects_real_browser_mode(s1, tmp_path, monkeypatch, caplog):
    """The driver loads ``repl_smoke.py`` lazily, only in real browser mode: the stub-registry
    runs above never load it. ``repl_smoke.py`` itself no longer reads the PLR submodule at
    import (A1c, ``test_repl_smoke_import.py``), but if it fails to load for ANY reason (a
    stand-in that raises at import here) ``--dry-run`` degrades to a ``chrome_error`` note and
    a real driver run exits 2 with nothing started."""
    import argparse

    broken = tmp_path / "repl_smoke_broken.py"
    broken.write_text("class VizCheckError(RuntimeError): pass\nraise VizCheckError('no submodule')\n")
    monkeypatch.setattr(s1, "REPL_SMOKE_PATH", broken)
    monkeypatch.setattr(s1, "_REPL_SMOKE", None)
    args = argparse.Namespace(out_dir=str(tmp_path / "out"), resume=False, dist=str(tmp_path),
                              base_path="/", chrome_path=None, dry_run=True)
    assert s1._dry_run(args) == 0
    monkeypatch.setattr(s1, "_REPL_SMOKE", None)
    args.dry_run = False
    with caplog.at_level("ERROR"):
        assert s1.run_driver(args) == 2
    assert "cannot build the input set" in caplog.text
    assert not list((tmp_path / "out" / "units").glob("*")), "no unit may be started"


# --------------------------------------------------------------------------- #
# Pure derivations
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("css", "layout", "case", "branch"),
    [
        (True, True, "honoured_reachable", "css_limits"),
        (False, True, "ignored_reachable", "dock_layout"),
        (True, False, "honoured_unreachable", "css_limits"),
        (False, False, "S1-L", "S1-L"),
        (None, True, None, None),
        (True, None, None, None),
    ],
)
def test_sizing_case_is_the_d6_table(s1, css, layout, case, branch):
    assert s1.sizing_case(css, layout) == case
    assert s1.sizing_branch(css, layout) == branch


def test_width_key_status_follows_d6_and_ac36(s1):
    f = s1.width_key_status
    ass, rec = "asserted", "recorded-only"
    s1l = f(False, False, True, True)
    assert s1l["case"] == "S1-L" and s1l["ac39d_ge1600_negative"] == "skipped"
    assert all(v == rec for k, v in s1l.items() if k not in ("case", "fit_after_tier_change", "ac39d_ge1600_negative"))
    row1 = f(True, True, False, True)  # honoured / reachable, restore keeps the iframe
    assert row1["open_width_ge_1600"] == ass and row1["resize_within_wide"] == ass and row1["ac39d_ge1600_negative"] == ass
    row1_reload = f(True, True, False, False)  # layout only at open/tier change; clamps follow CSS-unreachable
    assert row1_reload["open_width_ge_1600"] == ass and row1_reload["drag_clamp_1280_1599"] == ass
    assert row1_reload["resize_within_wide"] == rec  # inline px, but css_limits_refit is False
    assert f(True, True, True, False)["resize_within_wide"] == ass
    row2 = f(False, True, False, True)  # ignored / reachable
    assert row2["drag_clamp_1280_1599"] == ass and row2["resize_within_wide"] == ass
    row2_reload = f(False, True, True, False)
    assert row2_reload["drag_clamp_1280_1599"] == rec and row2_reload["resize_within_wide"] == rec
    assert row2_reload["open_width_ge_1600"] == ass
    row3 = f(True, False, False, True)  # honoured / unreachable, no refit
    assert row3["open_width_1280_1599"] == ass and row3["open_width_ge_1600"] == rec
    assert row3["ac39d_ge1600_negative"] == "skipped"
    assert f(True, False, True, True)["open_width_ge_1600"] == ass
    assert f(None, True, True, True) is None and f(True, True, True, None) is None


def test_pick_source_prefers_a_then_b_and_ignores_errored_units(s1):
    ok, bad = {"usable": True, "error": None}, {"usable": False, "error": None}
    assert s1.pick_source(ok, ok) == "S1-A"
    assert s1.pick_source(bad, ok) == "S1-B"
    assert s1.pick_source(bad, bad) is None
    assert s1.pick_source({"usable": True, "error": {"type": "X"}}, bad) is None


def _snap(**kw):
    base = {"classes": ["jp-Cell"], "data_attrs": [], "prompt_text": "[ ]:", "mimes": [], "execution_count": None,
            "execution_state": None, "is_dirty": None, "output_types": [], "source": "x"}
    base.update(kw)
    return base


def test_derive_hooks_credits_only_features_unique_to_a_state(s1):
    snaps = {
        "not_run": _snap(),
        "ran": _snap(prompt_text="[3]:", execution_count=3, output_types=["stream"]),
        "running": _snap(prompt_text="[*]:", execution_state="running", classes=["jp-Cell", "jp-mod-running"]),
        "error": _snap(prompt_text="[4]:", execution_count=4, output_types=["error"], mimes=["application/vnd.jupyter.stderr"]),
        "stale": _snap(prompt_text="[5]:", execution_count=5, output_types=["stream"]),
    }
    hooks = s1.derive_hooks(snaps)
    assert hooks["running"]["mechanism"] == "css" and "cls:jp-mod-running" in hooks["running"]["css"]
    assert hooks["error"]["mechanism"] == "css" and "mime:application/vnd.jupyter.stderr" in hooks["error"]["css"]
    assert hooks["not_run"]["mechanism"] == "model" and "prompt:[ ]:" in hooks["not_run"]["dom_text"]
    # ran and stale carry identical observable signatures: neither can be told apart
    assert hooks["ran"]["mechanism"] == "none" and hooks["stale"]["mechanism"] == "none"
    # ...until the model exposes isDirty
    snaps["stale"]["is_dirty"] = True
    assert s1.derive_hooks(snaps)["stale"]["mechanism"] == "model"


def test_selection_classes_are_not_state_hooks(s1):
    a = _snap(classes=["jp-Cell", "jp-mod-active", "jp-mod-selected"])
    b = _snap(classes=["jp-Cell"])
    assert s1.cell_features(a) == s1.cell_features(b)


def test_state_reached_is_ground_truth_from_the_model(s1):
    reached = s1.state_reached
    assert reached("not_run", _snap(), "x") and not reached("not_run", _snap(execution_count=1), "x")
    assert reached("ran", _snap(execution_count=1, output_types=["stream"]), "x")
    assert not reached("ran", _snap(execution_count=1, output_types=["error"]), "x")
    assert reached("running", _snap(execution_state="running"), "x")
    assert reached("running", _snap(prompt_text="[*]:"), "x")
    assert reached("error", _snap(output_types=["error"]), "x")
    assert reached("stale", _snap(execution_count=2, source="edited"), "orig")
    assert not reached("stale", _snap(execution_count=2, source="orig"), "orig")
    assert not reached("ran", None, "x")


def test_reattach_signal_priority(s1):
    f = s1.reattach_signal_from
    assert f({"inViewportChanged": [True], "messages": ["after-attach"], "mutations_added": 3}) == "inViewportChanged"
    assert f({"inViewportChanged": [False], "messages": ["after-attach"], "mutations_added": 3}) == "after-attach-message"
    assert f({"inViewportChanged": [], "messages": [], "mutations_added": 1}) == "dom-mutation"
    assert f({"inViewportChanged": [], "messages": [], "mutations_added": 0}) is None


def _arts(m):
    return {u: {**f, "error": None} for u, f in happy_fields(m).items()}


def test_derive_s1_c_reports_no_sizing_and_still_requires_valid_controls(s1):
    arts = _arts(s1)
    arts["widget_a"]["usable"] = False
    d = s1.derive_outcome_fields(arts)
    assert d["flat"]["widget_branch"] == "S1-C" and d["flat"]["sizing_case"] is None
    assert d["flat"]["measurement_valid"] is True and d["details"]["width_key_status"] is None
    arts["neg_wrong_ctor"]["negative_control_failed_as_required"] = False
    assert s1.derive_outcome_fields(arts)["flat"]["measurement_valid"] is False


def test_derive_branches_and_l_suffix(s1):
    arts = _arts(s1)
    arts["widget_a"]["usable"] = False
    arts["widget_b"]["usable"] = True
    for u in ("split_right", "css_limits", "dock_layout_sizing", "css_limits_refit", "restore_layout_keeps_iframe"):
        arts[u]["widget_source"] = "S1-B"
    arts["css_limits"]["css_limits_honoured"] = False
    arts["dock_layout_sizing"]["dock_layout_sizing_reachable"] = False
    flat = s1.derive_outcome_fields(arts)["flat"]
    assert flat["widget_branch"] == "S1-B" and flat["sizing_branch"] == "S1-L" and flat["d1_branch"] == "S1-B+S1-L"
    assert flat["measurement_valid"] is True and flat["sizing_case"] == "S1-L"


@pytest.mark.parametrize(
    ("unit", "field", "value"),
    [
        ("css_limits", "css_limits_honoured", None),  # drag control failed: inconclusive, not "ignored"
        ("css_limits", "drag_control_ok", False),
        ("dock_layout_sizing", "dock_layout_sizing_reachable", None),
        ("css_limits_refit", "css_limits_refit", None),
        ("restore_layout_keeps_iframe", "restore_layout_keeps_iframe", None),
        ("restore_layout_keeps_iframe", "reload_control_detected", False),  # instrument cannot see a reload
        ("split_right", "split_right_ok", False),
        ("css_limits", "widget_source", "S1-B"),  # units disagree about the widget source
        ("cell_hooks", "all_states_reached", False),
        ("windowing", "windowing_mode", None),
    ],
)
def test_an_uncontrolled_or_inconsistent_measurement_makes_the_run_invalid(s1, unit, field, value):
    arts = _arts(s1)
    assert s1.derive_outcome_fields(arts)["flat"]["measurement_valid"] is True
    arts[unit][field] = value
    assert s1.derive_outcome_fields(arts)["flat"]["measurement_valid"] is False


def test_negative_control_decision_over_a_stubbed_page(s1, monkeypatch):
    monkeypatch.setattr(s1, "open_fixture_notebook", lambda sess, ctx: None)

    class Page:
        def __init__(self, result):
            self.result = result

        def evaluate(self, *_a, **_k):
            return self.result

    class Sess:
        def __init__(self, result):
            self.page = Page(result)

    def run(result):
        return s1.probe_neg_wrong_ctor(Sess(result), None)

    good = {"ok": True, "positive": {"name": "Widget", "structural": True},
            "wrong": [{"name": "Object", "structural": False}, {"name": "leaf", "structural": False}]}
    assert run(good)["negative_control_failed_as_required"] is True
    accepted = {**good, "wrong": good["wrong"] + [{"name": "Decoy", "structural": True}]}
    assert run(accepted)["negative_control_failed_as_required"] is False  # a wrong candidate was accepted
    broken = {**good, "positive": {"name": "Widget", "structural": False}}
    assert run(broken)["negative_control_failed_as_required"] is False  # the check cannot pass at all
    with pytest.raises(RuntimeError):
        run({"ok": False, "reason": "no notebook panel"})


# --------------------------------------------------------------------------- #
# The in-page JS under a JS engine (fake Lumino): positive AND negative controls
# --------------------------------------------------------------------------- #

JS_ENGINE = shutil.which("node") or shutil.which("bun")
needs_js = pytest.mark.skipif(JS_ENGINE is None, reason="needs node or bun")


def _run_js(s1: Any, body: str, tmp_path: Path) -> Any:
    script = tmp_path / "probe_lib_test.js"
    script.write_text(
        "globalThis.window = globalThis;\n"
        "globalThis.document = {getElementById() { return null; }, body: {contains() { return true; }}};\n"
        "globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);\n"
        + s1.S1_JS
        + ";\nconst S = window.__s1;\n"
        + "(async () => {\n"
        + textwrap.dedent(body)
        + "\n})().catch((e) => { console.error(e); process.exit(1); });\n"
    )
    cmd = [JS_ENGINE, "run", str(script)] if Path(JS_ENGINE).name == "bun" else [JS_ENGINE, str(script)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


FAKE_LUMINO = """
class Widget { processMessage() {} onAfterAttach() {} }
class MainAreaWidget extends Widget {}
class DocumentWidget extends MainAreaWidget { onAfterAttach() { super.onAfterAttach(); } }
class NotebookPanel extends DocumentWidget {}
const nb = new NotebookPanel();
nb.node = {classList: {contains: (c) => c === 'jp-NotebookPanel'}};
nb.content = {};
window.jupyterapp = {shell: {widgets() { return [nb][Symbol.iterator](); }}};
"""


@needs_js
def test_js_structural_check_walk_and_negative_control(s1, tmp_path):
    out = _run_js(
        s1,
        FAKE_LUMINO
        + """
        const walk = S.walkNotebook();
        const neg = S.negControl();
        console.log(JSON.stringify({walk, neg}));
        """,
        tmp_path,
    )
    walk, neg = out["walk"], out["neg"]
    assert walk["root_ctor_name"] == "Widget" and walk["structural"] is True
    assert [c["ctor_name"] for c in walk["chain"]] == ["NotebookPanel", "DocumentWidget", "MainAreaWidget", "Widget"]
    assert [c["structural"] for c in walk["chain"]] == [False, False, False, True]
    assert neg["positive"]["structural"] is True  # positive control: the real root passes
    assert neg["wrong"] and all(c["structural"] is False for c in neg["wrong"])  # negative control: all fail
    assert {c["name"] for c in neg["wrong"]} >= {"Object", "Array", "DecoyExtendsRoot"}


@needs_js
def test_js_a_root_without_the_methods_fails_the_structural_check(s1, tmp_path):
    """The instrument can say NO: a shell whose root owns neither method is not accepted."""
    out = _run_js(
        s1,
        FAKE_LUMINO.replace("class Widget { processMessage() {} onAfterAttach() {} }", "class Widget { processMessage() {} }")
        + """
        console.log(JSON.stringify({walk: S.walkNotebook(), neg: S.negControl()}));
        """,
        tmp_path,
    )
    assert out["walk"]["structural"] is False
    assert out["neg"]["positive"]["structural"] is False  # => negative_control_failed_as_required is False


@needs_js
def test_js_layout_sizing_edits_the_widgets_split_area(s1, tmp_path):
    out = _run_js(
        s1,
        """
        const w = {node: {getBoundingClientRect: () => ({x: 0, y: 0, width: 300, height: 100, left: 0, right: 300, top: 0, bottom: 100})}};
        const other = {};
        let restored = null;
        const cfg = {main: {type: 'split-area', orientation: 'vertical', sizes: [1], children: [
          {type: 'split-area', orientation: 'horizontal', sizes: [0.5, 0.5], children: [
            {type: 'tab-area', widgets: [other], currentIndex: 0},
            {type: 'tab-area', widgets: [w], currentIndex: 0}]}]}};
        const dock = {node: {id: 'jp-main-dock-panel', getBoundingClientRect: () => ({x: 0, y: 0, width: 1000, height: 100, left: 0, right: 1000, top: 0, bottom: 100})},
                      saveLayout: () => cfg, restoreLayout: (c) => { restored = c; }};
        window.jupyterapp = {shell: {_dockPanel: dock, widgets() { return [][Symbol.iterator](); }}};
        window.__s1w = w;
        const res = await S.setSplitSizes(0.3);
        console.log(JSON.stringify({res, restored: restored && restored.main.children[0].sizes}));
        """,
        tmp_path,
    )
    res = out["res"]
    assert res["dock_panel_found"] and res["save_layout_ok"] and res["split_area_found"] and res["restore_called"]
    assert res["orientation"] == "horizontal" and res["sizes_before"] == [0.5, 0.5]
    assert out["restored"] == [0.7, 0.3]  # the widget's slot is 0.3, the other gets the rest
    assert abs(res["measured_fraction"] - 0.3) < 1e-9  # 300 px of the 1000 px dock


@needs_js
def test_js_layout_sizing_reports_a_missing_dock_instead_of_throwing(s1, tmp_path):
    out = _run_js(
        s1,
        """
        window.jupyterapp = {shell: {widgets() { return [][Symbol.iterator](); }}};
        window.__s1w = {node: {}};
        console.log(JSON.stringify(await S.setSplitSizes(0.3)));
        """,
        tmp_path,
    )
    assert out["dock_panel_found"] is False and out["restore_called"] is False
