"""No-browser plumbing checks for the AC-39 sensitivity driver (epic 260929_notebook-display-design, A7).

``scripts/negatives/260929_nd_sensitivity.py`` (shared driver) and its sprint A entry
``scripts/spikes/260929_nd_sensitivity_sprint_a.py`` are the pre-registered AC-39(a) run
(sidecar ``.bth.toml``, committed BEFORE any run). Nothing here launches Playwright or Chromium
and nothing here measures a product: it proves the DRIVER, UNIT, STAMP, RESUME, COMPLETENESS and
OUTCOME plumbing against a STUB harness, so that when the real run happens a plumbing bug
cannot be mistaken for a finding.

Every negative unit runs as a REAL subprocess (``unit_runner.run_unit``, real ``Watchdog``, real
stamps); the harness unit the negative starts is a stub launcher that loads the real
``repl_smoke.py`` and calls its real ``run_scenario`` with a fake session, so the harness's own
result and stamp are the production ones and the driver's cross-check of the harness stamp's
inputs (the harness must have served the MUTATED copy) is exercised for real.

Controls (BATHOS.md): a POSITIVE control (a stub harness that fails naming the expected key ->
the negative passes) is always paired with NEGATIVE controls (a harness that passes, fails a
different key, times out, or whose instrument errored -> the negative must NOT pass).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
import tomllib
import uuid
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_PATH = REPO_ROOT / "scripts" / "negatives" / "260929_nd_sensitivity.py"
ENTRY_PATH = REPO_ROOT / "scripts" / "spikes" / "260929_nd_sensitivity_sprint_a.py"
SIDECAR_PATH = ENTRY_PATH.with_suffix(".bth.toml")
REPL_SMOKE = REPO_ROOT / "scripts" / "repl_smoke.py"

pytestmark = pytest.mark.timeout(180)


def _load(path: Path, prefix: str) -> Any:
    name = f"{prefix}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def nd() -> Any:
    return _load(SHARED_PATH, "nd_shared_under_test")


# --------------------------------------------------------------------------- #
# Stub launchers: the real driver code, a stub harness
# --------------------------------------------------------------------------- #

HARNESS_STUB = textwrap.dedent(
    '''
    import importlib.util, json, os, sys, time
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("rs", os.environ["ND_RS"])
    rs = importlib.util.module_from_spec(spec)
    sys.modules["rs"] = rs
    spec.loader.exec_module(rs)
    PLAN = json.loads(os.environ["ND_PLAN"])
    args = rs.parse_args(sys.argv[1:])
    with open(PLAN["log"], "a") as fh:
        fh.write(json.dumps(sys.argv[1:]) + "\\n")
    if PLAN.get("crash"):
        sys.exit(7)  # dies before run_scenario can clear its own files


    class Session:
        pageerrors = []

        def close(self):
            pass


    def scenario(session, unit, env):
        if PLAN.get("hang"):
            time.sleep(600)
        if PLAN.get("raise"):
            raise RuntimeError("stub instrument failure")
        fields = dict(unit.expected)
        for key in PLAN.get("fail", []):
            fields[key] = "WRONG"
        return fields


    env = rs.build_hash_env(
        args, args.chrome_path, driver_fn=lambda: PLAN["driver"],
        chrome_version_fn=lambda p: PLAN["chrome_version"],
    )
    sys.exit(rs.run_scenario(
        args.scenario, out_dir=Path(args.out_dir), env_fn=lambda: env,
        session_factory=lambda u, e: Session(), scenario_fn=scenario, budget_s=PLAN.get("budget"),
    ))
    '''
)

DRIVER_STUB = textwrap.dedent(
    '''
    import importlib.util, json, os, sys

    spec = importlib.util.spec_from_file_location("nd_entry", os.environ["ND_ENTRY"])
    entry = importlib.util.module_from_spec(spec)
    sys.modules["nd_entry"] = entry
    spec.loader.exec_module(entry)
    shared = entry._load_shared()
    FAKE = json.loads(os.environ["ND_FAKE"])
    shared.build_env = lambda args: shared.InputEnv(**FAKE)
    shared.HARNESS_ARGV_PREFIX = [sys.executable, os.environ["ND_HARNESS_STUB"]]
    ut = float(os.environ.get("ND_UNIT_TIMEOUT") or 0) or None
    ht = float(os.environ.get("ND_HARNESS_TIMEOUT") or 0) or None
    sys.exit(entry.main(
        sys.argv[1:], unit_argv_prefix=[sys.executable, os.path.abspath(__file__)],
        unit_timeout_s=ut, harness_timeout_s=ht,
    ))
    '''
)

TARGET = "shell/display/index.js"


class Bed:
    """A pristine tiny dist, the stub launchers, and helpers to run the driver as a subprocess."""

    def __init__(self, nd: Any, tmp: Path) -> None:
        self.nd, self.tmp = nd, tmp
        self.pristine = tmp / "pristine"
        for rel, text in ((TARGET, "// index"), ("shell/display/chrome.js", "// chrome"), ("lab/index.html", "<html>")):
            f = self.pristine / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
        self.neg_root = tmp / "nd-neg"
        self.out = tmp / "out"
        self.log = tmp / "harness.log"
        (tmp / "harness_stub.py").write_text(HARNESS_STUB)
        (tmp / "driver_stub.py").write_text(DRIVER_STUB)
        self.plan: dict[str, Any] = {"log": str(self.log), "driver": "v" * 64, "chrome_version": "stub",
                                     "fail": ["rail_state_after_run"], "budget": 60}
        self.fake: dict[str, Any] = {}
        self.refresh_fake()
        self.results = tmp / "bth_results.json"
        self.unit_timeout = ""
        self.harness_timeout = "60"

    def refresh_fake(self, **over: Any) -> None:
        self.fake = dict(
            script="s" * 64, entry="e" * 64, runner="r" * 64, harness="h" * 64,
            dist_pristine=self.nd.unit_runner.dist_hash(self.pristine), chrome="c" * 64,
            driver=self.plan["driver"], base_path="/praxis/", chrome_path="/fake/chrome", chrome_version="stub",
        )
        self.fake.update(over)

    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k != "PRAXIS_UNIT_TOKEN"}
        env.update(
            ND_ENTRY=str(ENTRY_PATH), ND_RS=str(REPL_SMOKE), ND_PLAN=json.dumps(self.plan),
            ND_FAKE=json.dumps(self.fake), ND_HARNESS_STUB=str(self.tmp / "harness_stub.py"),
            ND_UNIT_TIMEOUT=self.unit_timeout, ND_HARNESS_TIMEOUT=self.harness_timeout,
            BTH_RESULTS_PATH=str(self.results),
        )
        return env

    def cmd(self, *extra: str) -> list[str]:
        return [sys.executable, str(self.tmp / "driver_stub.py"), "--out-dir", str(self.out),
                "--dist", str(self.pristine), "--neg-root", str(self.neg_root), *extra]

    def driver(self, *extra: str) -> tuple[int, dict[str, Any]]:
        proc = subprocess.run(self.cmd(*extra), env=self.env(), capture_output=True, text=True, timeout=170)
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip().startswith("{")]
        assert lines, f"no aggregate JSON.\nstdout={proc.stdout!r}\nstderr={proc.stderr[-3000:]}"
        return proc.returncode, json.loads(lines[-1])

    def harness_runs(self) -> list[list[str]]:
        return [json.loads(ln) for ln in self.log.read_text().splitlines()] if self.log.exists() else []

    def artifact(self, nid: str = "a") -> dict[str, Any]:
        return json.loads(self.nd.unit_paths(self.out, nid)["artifact"].read_text())

    def stamp(self, nid: str = "a") -> dict[str, Any]:
        return json.loads(self.nd.unit_paths(self.out, nid)["stamp"].read_text())


@pytest.fixture()
def bed(nd, tmp_path):
    return Bed(nd, tmp_path)


# --------------------------------------------------------------------------- #
# The negative table and the entry script: sprint A is negative (a) only
# --------------------------------------------------------------------------- #


def test_negative_a_is_the_ac39a_mutation_and_key(nd):
    neg = nd.NEGATIVES["a"]
    assert (neg.harness_flag, neg.harness_unit) == ("--display-check", "D1")
    assert neg.expected_key == "rail_state_after_run" and neg.delete == "shell/display/index.js"
    assert neg.harness_neg == ()
    assert nd.REQUIRED_FIELDS == ("harness_exit", "failing_keys", "outcome")
    assert nd.DEFAULT_NEG_ROOT == Path("/tmp/claude-1000/nd-neg")


def test_entry_script_fixes_the_sprint_a_set_and_loads_the_shared_driver_by_path():
    entry = _load(ENTRY_PATH, "nd_entry_under_test")
    assert entry.NEGATIVES == ("a",) and entry.SPRINT == "a"
    assert entry.SHARED_PATH == SHARED_PATH and SHARED_PATH.is_file()
    assert entry._load_shared() is entry._load_shared(), "loaded once"
    assert "sys.path" not in ENTRY_PATH.read_text().replace("nothing edits sys.path", "")


def test_dry_run_prints_the_plan_and_touches_nothing(tmp_path):
    out = tmp_path / "never"
    proc = subprocess.run(
        [sys.executable, str(ENTRY_PATH), "--dry-run", "--out-dir", str(out), "--neg-root", str(tmp_path / "nr")],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    plan = json.loads(proc.stdout)
    assert [n["id"] for n in plan["negatives"]] == ["a"] and plan["sprint"] == "a"
    neg = plan["negatives"][0]
    assert neg["serve_dir"] == str(tmp_path / "nr" / "a" / "dist") and neg["harness_out_dir"] == str(tmp_path / "nr" / "a" / "out")
    assert plan["budgets"]["a"] == {"harness_budget_s": 360.0, "unit_timeout_s": 600.0, "driver_kill_s": 660.0}
    assert not out.exists() and not (tmp_path / "nr").exists()


def test_default_dirs_are_the_spec_paths(tmp_path):
    proc = subprocess.run([sys.executable, str(ENTRY_PATH), "--dry-run"], capture_output=True, text=True, timeout=60)
    plan = json.loads(proc.stdout)
    assert plan["neg_root"] == "/tmp/claude-1000/nd-neg"
    assert plan["out_dir"] == str(REPO_ROOT / "outputs" / "nd_sensitivity" / "sprint_a")
    assert plan["negatives"][0]["serve_dir"] == "/tmp/claude-1000/nd-neg/a/dist"
    assert plan["negatives"][0]["harness_out_dir"] == "/tmp/claude-1000/nd-neg/a/out"


# --------------------------------------------------------------------------- #
# The dist copy and its mutation (a positive control AND negative controls)
# --------------------------------------------------------------------------- #


def test_virtual_hash_equals_the_real_hash_of_the_mutated_copy(nd, bed):
    neg = nd.NEGATIVES["a"]
    prep = nd.prepare_mutated_dist(bed.pristine, nd.neg_paths(bed.neg_root, "a").dist, neg, bed.neg_root)
    real = nd.unit_runner.dist_hash(nd.neg_paths(bed.neg_root, "a").dist)
    assert prep == {"pristine_has_target": True, "mutated_lacks_target": True}
    assert nd.virtual_mutated_hash(bed.pristine, TARGET) == real
    # negative controls: the virtual hash is not vacuously equal to the pristine one, and a wrong
    # deletion path is a different hash
    assert real != nd.unit_runner.dist_hash(bed.pristine)
    assert nd.virtual_mutated_hash(bed.pristine, "shell/display/chrome.js") != real
    assert nd.virtual_mutated_hash(bed.pristine, None) == nd.unit_runner.dist_hash(bed.pristine)


def test_prepare_never_touches_the_pristine_dist_and_makes_a_real_copy(nd, bed):
    before = nd.unit_runner.dist_hash(bed.pristine)
    dest = nd.neg_paths(bed.neg_root, "a").dist
    nd.prepare_mutated_dist(bed.pristine, dest, nd.NEGATIVES["a"], bed.neg_root)
    assert (bed.pristine / TARGET).is_file() and not (dest / TARGET).exists()
    assert (dest / "shell/display/chrome.js").read_text() == "// chrome"
    (dest / "lab/index.html").write_text("changed in the copy")
    assert nd.unit_runner.dist_hash(bed.pristine) == before, "the copy is independent of the pristine tree"


def test_prepare_starts_from_a_fresh_copy_every_time(nd, bed):
    dest = nd.neg_paths(bed.neg_root, "a").dist
    nd.prepare_mutated_dist(bed.pristine, dest, nd.NEGATIVES["a"], bed.neg_root)
    (dest / "stale-leftover.txt").write_text("from an earlier run")
    nd.prepare_mutated_dist(bed.pristine, dest, nd.NEGATIVES["a"], bed.neg_root)
    assert not (dest / "stale-leftover.txt").exists()


def test_a_mutation_whose_target_is_absent_is_reported_not_silently_applied(nd, bed):
    (bed.pristine / TARGET).unlink()
    prep = nd.prepare_mutated_dist(bed.pristine, nd.neg_paths(bed.neg_root, "a").dist, nd.NEGATIVES["a"], bed.neg_root)
    assert prep["pristine_has_target"] is False, "a mutation that changed nothing must invalidate the run"


def test_prepare_refuses_any_destination_outside_the_negatives_own_dist(nd, bed, tmp_path):
    neg = nd.NEGATIVES["a"]
    for bad in (tmp_path / "elsewhere", bed.neg_root / "b" / "dist", bed.neg_root / "a", bed.pristine / "inside"):
        with pytest.raises(ValueError):
            nd.prepare_mutated_dist(bed.pristine, bad, neg, bed.neg_root)
    assert (bed.pristine / TARGET).is_file()


def test_prepare_raises_on_a_missing_pristine_dist(nd, bed, tmp_path):
    with pytest.raises(FileNotFoundError):
        nd.prepare_mutated_dist(tmp_path / "nope", nd.neg_paths(bed.neg_root, "a").dist, nd.NEGATIVES["a"], bed.neg_root)


# --------------------------------------------------------------------------- #
# The outcome of a negative: exit nonzero AND the expected key among the FAILING keys
# --------------------------------------------------------------------------- #


def _outcome(nd: Any, **over: Any) -> tuple[bool, list[str]]:
    kw: dict[str, Any] = dict(stamp_valid=True, harness_exit=1, failing_keys=["rail_state_after_run", "x"], harness_error=None)
    kw.update(over)
    return nd.negative_outcome(nd.NEGATIVES["a"], **kw)


def test_outcome_positive_control_the_harness_failed_naming_the_key(nd):
    assert _outcome(nd) == (True, [])


@pytest.mark.parametrize(
    "over",
    [
        {"harness_exit": 0},  # the gate did not notice the removal
        {"failing_keys": ["light_ground"]},  # it failed, but not on the required key
        {"failing_keys": []},
        {"harness_exit": 124, "stamp_valid": False, "failing_keys": []},  # a timeout names no key
        {"harness_exit": 1, "stamp_valid": False},  # no valid stamp
        {"harness_error": {"type": "TimeoutError"}},  # the instrument raised: not a detection
        {"harness_exit": None},
    ],
)
def test_outcome_negative_controls_never_pass(nd, over):
    passed, reasons = _outcome(nd, **over)
    assert passed is False and reasons


# --------------------------------------------------------------------------- #
# Driver / unit / stamp / completeness / outcome (real subprocesses, stub harness)
# --------------------------------------------------------------------------- #


def test_positive_control_a_failing_harness_naming_the_key_passes_the_negative(bed, nd):
    code, agg = bed.driver()
    assert code == 0 and agg["all_units_complete"] and agg["outcome_evaluated"]
    assert agg["recomputed"] == ["a"] and agg["reused"] == []
    art, stamp = bed.artifact(), bed.stamp()
    assert art["outcome"] is True and art["harness_exit"] == 1 and "rail_state_after_run" in art["failing_keys"]
    assert art["error"] is None and art["harness_stamp_valid"] is True
    assert art["pristine_has_target"] is True and art["mutated_lacks_target"] is True
    assert stamp["exit"] == 0 and stamp["unit"] == "a" and stamp["timeout_s"] == 600.0
    assert stamp["artifact_sha256"] == nd.sha256_bytes(nd.unit_paths(bed.out, "a")["artifact"].read_bytes())
    assert set(stamp["inputs"]) == {
        "script", "entry", "runner", "harness", "dist_pristine", "dist_mutated", "chrome", "driver", "args",
    }
    assert stamp["inputs"]["dist_mutated"] == nd.virtual_mutated_hash(bed.pristine, TARGET)
    assert stamp["inputs"]["dist_mutated"] != stamp["inputs"]["dist_pristine"]
    flat = json.loads(bed.results.read_text())
    assert flat["measurement_valid"] is True and flat["a_negative_passed"] is True and flat["a_detected"] is True
    assert flat["a_harness_exit"] == 1 and flat["a_expected_key_failed"] is True
    assert flat["all_units_complete"] is True and flat["n_negatives"] == 1 and flat["n_error_units"] == 0


def test_the_harness_runs_only_its_own_unit_on_its_own_dist_and_out_dir(bed, nd):
    bed.driver()
    (argv,) = bed.harness_runs()
    assert argv[:1] == ["--display-check"] and argv[argv.index("--scenario") + 1] == "D1"
    assert argv.count("--scenario") == 1
    assert argv[argv.index("--serve-dir") + 1] == str(bed.neg_root / "a" / "dist") != str(bed.pristine)
    assert argv[argv.index("--out-dir") + 1] == str(bed.neg_root / "a" / "out")
    assert argv[argv.index("--base-path") + 1] == "/praxis/" and "--aggregate-only" not in argv
    assert "--neg" not in argv
    # the harness's records live in the negative's own out dir, never in the default one
    assert (bed.neg_root / "a" / "out" / "result.D1.stamp.json").is_file()
    assert (bed.neg_root / "a" / "dist" / "lab" / "index.html").is_file()
    assert not (bed.neg_root / "a" / "dist" / TARGET).exists() and (bed.pristine / TARGET).is_file()


def test_the_harness_stamp_must_show_it_served_the_mutated_copy(bed, nd):
    """The driver compares the harness stamp's inputs with the ones the MUTATED copy implies; a
    harness that served something else (here: the driver's expectation is off) is not valid."""
    bed.plan["driver"] = "w" * 64  # the harness will hash a different `driver` than the driver expects
    bed.fake["driver"] = "v" * 64
    code, agg = bed.driver()
    art = bed.artifact()
    assert code == 0 and art["harness_stamp_valid"] is False and art["outcome"] is False
    assert json.loads(bed.results.read_text())["measurement_valid"] is False


def test_negative_control_a_harness_that_passes_is_a_missed_negative_but_a_valid_measurement(bed):
    bed.plan["fail"] = []
    code, _ = bed.driver()
    art, flat = bed.artifact(), json.loads(bed.results.read_text())
    assert code == 0 and art["harness_exit"] == 0 and art["outcome"] is False
    assert flat["measurement_valid"] is True and flat["a_negative_passed"] is False and flat["a_detected"] is False
    assert flat["a_harness_exit"] == 0 and flat["a_expected_key_failed"] is False


def test_negative_control_a_harness_that_fails_a_different_key(bed):
    bed.plan["fail"] = ["light_ground"]
    bed.driver()
    art, flat = bed.artifact(), json.loads(bed.results.read_text())
    assert art["harness_exit"] == 1 and art["failing_keys"] == ["light_ground"] and art["outcome"] is False
    assert flat["measurement_valid"] is True and flat["a_expected_key_failed"] is False


def test_a_harness_timeout_never_passes_and_is_an_invalid_measurement(bed):
    bed.plan.update(hang=True, budget=2)  # the harness's own watchdog exits it 124 at 2 s
    code, _ = bed.driver()
    art, flat = bed.artifact(), json.loads(bed.results.read_text())
    assert code == 0, "a timed-out HARNESS is still a complete negative unit"
    assert art["harness_exit"] == 124 and art["harness_stamp_valid"] is False and art["failing_keys"] == []
    assert art["outcome"] is False and flat["measurement_valid"] is False
    assert not (bed.neg_root / "a" / "out" / "result.D1.json").exists(), "the harness watchdog deleted its result"


def test_a_stale_harness_stamp_is_never_judged(bed):
    """The negative unit clears the harness unit's files before launching it: a harness that dies
    before it can clear them itself must not leave an earlier run's (valid-looking) stamp to be read."""
    bed.driver()
    assert bed.artifact()["outcome"] is True and (bed.neg_root / "a" / "out" / "result.D1.stamp.json").is_file()
    bed.plan["crash"] = True
    bed.driver()
    art = bed.artifact()
    assert art["harness_stamp_valid"] is False and art["harness_exit"] == 7 and art["outcome"] is False
    assert json.loads(bed.results.read_text())["measurement_valid"] is False


def test_a_raising_instrument_is_an_error_finding_never_a_detection(bed):
    bed.plan["raise"] = True  # the harness scenario raises: its result carries an error finding
    bed.driver()
    art, flat = bed.artifact(), json.loads(bed.results.read_text())
    assert art["harness_stamp_valid"] is True and art["harness_error"]["type"] == "RuntimeError"
    assert art["outcome"] is False and flat["measurement_valid"] is False


def test_a_mutation_that_removed_nothing_is_an_invalid_measurement(bed):
    (bed.pristine / TARGET).unlink()  # nothing for the mutation to remove
    bed.refresh_fake()
    code, agg = bed.driver()
    assert code == 0 and agg["all_units_complete"] and bed.artifact()["pristine_has_target"] is False
    assert json.loads(bed.results.read_text())["measurement_valid"] is False


def test_a_driver_that_raises_is_a_complete_unit_with_an_error_finding_and_never_reused(bed, nd):
    bed.neg_root.mkdir(parents=True, exist_ok=True)
    (bed.neg_root / "a").write_text("a file where the negative's directory must be")  # the copy cannot be made
    code, agg = bed.driver()
    art = bed.artifact()
    assert code == 0 and agg["all_units_complete"] and agg["recomputed"] == ["a"]
    assert art["error"] is not None and art["outcome"] is False and art["harness_exit"] is None
    assert set(nd.REQUIRED_FIELDS) <= set(art), "pre-registered fields stay present"
    assert bed.stamp()["exit"] == 1
    assert json.loads(bed.results.read_text())["measurement_valid"] is False
    assert json.loads(bed.results.read_text())["n_error_units"] == 1
    # never reused: the next --resume recomputes it (and fails the same way)
    _, agg2 = bed.driver("--resume")
    assert agg2["reused"] == [] and agg2["recomputed"] == ["a"]
    assert bed.harness_runs() == [], "the harness never ran"


def test_teardown_order_result_before_stamp_and_exit_follows_the_stamp(bed, nd):
    bed.driver()
    art_path, stamp_path = nd.unit_paths(bed.out, "a")["artifact"], nd.unit_paths(bed.out, "a")["stamp"]
    assert art_path.stat().st_mtime_ns <= stamp_path.stat().st_mtime_ns
    assert bed.stamp()["finished"] >= bed.artifact()["finished"]


def test_resume_reuses_a_passed_negative_and_records_source_and_hashes(bed):
    bed.driver()
    code, agg = bed.driver("--resume")
    assert code == 0 and agg["recomputed"] == [] and len(agg["reused"]) == 1
    rec = agg["reused"][0]
    assert rec["source"].endswith("units/a.json") and rec["artifact_sha256"] == bed.stamp()["artifact_sha256"]
    assert set(rec["inputs"]) == set(bed.stamp()["inputs"])
    assert len(bed.harness_runs()) == 1, "a reused negative does not run its harness again"
    assert agg["outcome_evaluated"] and json.loads(bed.results.read_text())["a_negative_passed"] is True


def test_without_resume_the_negative_is_recomputed(bed):
    bed.driver()
    _, agg = bed.driver()
    assert agg["recomputed"] == ["a"] and len(bed.harness_runs()) == 2


def test_a_missed_negative_is_always_rerun_on_resume(bed):
    bed.plan["fail"] = []
    bed.driver()
    bed.driver("--resume")
    assert len(bed.harness_runs()) == 2, "a negative whose recorded outcome did not pass is never reused"


@pytest.mark.parametrize("field", ["script", "entry", "runner", "harness", "chrome", "driver", "dist_pristine"])
def test_input_mismatch_forces_a_rerun(bed, field):
    bed.driver()
    bed.refresh_fake(**{field: "0" * 64})
    if field == "driver":
        bed.plan["driver"] = "0" * 64
    _, agg = bed.driver("--resume")
    assert agg["reused"] == [] and agg["recomputed"] == ["a"] and len(bed.harness_runs()) == 2
    assert field in agg["stale"][0]["mismatched"]


def test_a_changed_pristine_dist_changes_both_dist_inputs(bed):
    bed.driver()
    (bed.pristine / "lab/index.html").write_text("<html>v2")
    bed.refresh_fake()
    _, agg = bed.driver("--resume")
    assert agg["recomputed"] == ["a"]
    assert {"dist_pristine", "dist_mutated"} <= set(agg["stale"][0]["mismatched"])


def test_a_unit_that_times_out_is_incomplete_and_no_outcome_is_written(bed, nd):
    bed.plan.update(hang=True, budget=600)  # the stub harness never finishes on its own ...
    bed.harness_timeout = "600"
    bed.unit_timeout = "4"  # ... and the negative unit's own watchdog fires at 4 s
    code, agg = bed.driver()
    assert code == 3 and agg["all_units_complete"] is False and agg["outcome_evaluated"] is False
    assert agg["timed_out"] == ["a"] and agg["incomplete"] == ["a"]
    paths = nd.unit_paths(bed.out, "a")
    assert not paths["stamp"].exists() and not paths["artifact"].exists() and paths["timeout"].exists()
    assert not bed.results.exists(), "an incomplete run writes no bathos result, so no outcome is recorded"


def test_unit_mode_runs_exactly_one_negative_via_run_unit(bed, nd):
    proc = subprocess.run(bed.cmd("--unit", "a"), env=bed.env(), capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert bed.stamp()["exit"] == 0 and len(bed.harness_runs()) == 1


def test_unknown_negative_is_rejected_by_the_cli(bed):
    proc = subprocess.run(bed.cmd("--unit", "z"), env=bed.env(), capture_output=True, text=True, timeout=60)
    assert proc.returncode == 2 and "invalid choice" in proc.stderr


def test_missing_dist_exits_2_before_anything_runs(bed):
    proc_cmd = bed.cmd()
    proc_cmd[proc_cmd.index("--dist") + 1] = str(bed.pristine / "missing")
    env = bed.env()
    # build_env is stubbed in the launcher, so exercise the REAL build_env's failure directly
    proc = subprocess.run(
        [sys.executable, str(ENTRY_PATH), "--out-dir", str(bed.out), "--dist", str(bed.pristine / "missing"),
         "--neg-root", str(bed.neg_root)],
        env={k: v for k, v in env.items() if k != "BTH_RESULTS_PATH"}, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 2 and not bed.results.exists()
    assert not bed.neg_root.exists(), "nothing was copied"


# --------------------------------------------------------------------------- #
# The flat outcome fields
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "exit_code,failing,detected",
    [(1, ["rail_state_after_run"], True), (0, ["rail_state_after_run"], False), (1, ["light_ground"], False),
     (124, [], False), (None, [], False), (1, [], False)],
)
def test_detected_is_nonzero_exit_and_the_expected_key_failing(nd, exit_code, failing, detected):
    art = {"error": None, "harness_stamp_valid": True, "harness_error": None, "pristine_has_target": True,
           "mutated_lacks_target": True, "harness_exit": exit_code, "failing_keys": failing, "outcome": detected}
    assert nd.derive_outcome_fields({"a": art}, {"a": nd.NEGATIVES["a"]})["flat"]["a_detected"] is detected


def test_derive_outcome_fields_validity_is_a_conjunction(nd):
    good = {"error": None, "harness_stamp_valid": True, "harness_error": None, "pristine_has_target": True,
            "mutated_lacks_target": True, "harness_exit": 1, "failing_keys": ["rail_state_after_run"], "outcome": True}
    flat = nd.derive_outcome_fields({"a": good}, {"a": nd.NEGATIVES["a"]})["flat"]
    assert flat["measurement_valid"] is True and flat["a_negative_passed"] is True and flat["a_expected_key_failed"] is True
    assert flat["a_detected"] is True
    for breaker in ({"error": {"type": "X"}}, {"harness_stamp_valid": False}, {"harness_error": {"type": "X"}},
                    {"pristine_has_target": False}, {"mutated_lacks_target": False}, {"harness_exit": 124}):
        art = {**good, **breaker, "outcome": False}
        flat = nd.derive_outcome_fields({"a": art}, {"a": nd.NEGATIVES["a"]})["flat"]
        assert flat["measurement_valid"] is False, breaker


# --------------------------------------------------------------------------- #
# The sidecar pre-registers exactly this design
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def sidecar() -> dict[str, Any]:
    assert SIDECAR_PATH.is_file(), "the sidecar is committed BEFORE the run"
    return tomllib.loads(SIDECAR_PATH.read_text())


def test_sidecar_has_one_outcome_per_negative_and_an_invalid_residual(sidecar):
    outcomes = sidecar["outcomes"]
    assert set(outcomes) == {"a_sensitive", "a_insensitive", "invalid"}
    assert outcomes["invalid"]["is_residual"] is True
    assert not outcomes["a_sensitive"]["is_residual"] and not outcomes["a_insensitive"]["is_residual"]
    assert "measurement_valid = false" in outcomes["invalid"]["condition"]
    for name in ("a_sensitive", "a_insensitive"):
        assert "measurement_valid = true" in outcomes[name]["condition"]
        assert "all_units_complete = true" in outcomes[name]["condition"]
    assert "a_detected = true" in outcomes["a_sensitive"]["condition"]
    assert "a_detected = false" in outcomes["a_insensitive"]["condition"]
    assert sidecar["experiment"]["hypothesis"] and sidecar["experiment"]["stage_name"]


def test_sidecar_result_schema_matches_the_flat_fields_the_driver_writes(sidecar, nd):
    arts = {"a": {"error": None, "harness_stamp_valid": True, "harness_error": None, "pristine_has_target": True,
                  "mutated_lacks_target": True, "harness_exit": 1, "failing_keys": ["rail_state_after_run"], "outcome": True}}
    flat = nd.derive_outcome_fields(arts, {"a": nd.NEGATIVES["a"]})["flat"]
    schema = sidecar["result_schema"]
    assert set(schema) == set(flat)
    kinds = {"bool": bool, "int": int, "str": str}
    for key, value in flat.items():
        assert isinstance(value, kinds[schema[key]]), key


def test_sidecar_design_statement_covers_units_inputs_resume_completeness_and_timeouts(sidecar, nd):
    d = sidecar["design"]
    text = json.dumps(d)
    assert d["unit_list"] == ["a"] and d["driver_unit_runner"] and "run_unit" in text
    for needle in ("driver", "unit_runner.driver_input", "dist_pristine", "dist_mutated", "harness",
                   "/tmp/claude-1000/nd-neg/a/dist/", "/tmp/claude-1000/nd-neg/a/out/", "exit == 0",
                   "error finding", "never reused", "full unit set", "Watchdog", "os._exit", "whole-run timeout"):
        assert needle in text, needle
    assert d["timeouts"]["harness_unit_s"] == 360 and d["timeouts"]["negative_unit_s"] == 600
    assert d["timeouts"]["driver_kill_s"] == 660 and d["timeouts"]["whole_run_timeout"] == "none"
    unit = d["units"]["a"]
    assert unit["required_fields"] == list(nd.REQUIRED_FIELDS)
    assert unit["expected_key"] == "rail_state_after_run" and unit["harness_unit"] == "D1"
    assert unit["mutation"].startswith("remove shell/display/index.js")
    assert d["hashed_inputs"] and any("driver" in h and "uv.lock" in h for h in d["hashed_inputs"])


def test_sidecar_names_its_negative_control_and_its_paired_positive_control(sidecar):
    controls = json.dumps(sidecar["design"]["controls"])
    assert "must FAIL" in controls or "must fail" in controls
    assert "positive" in sidecar["design"]["controls"] and "negative" in sidecar["design"]["controls"]
    assert "test_nd_sensitivity_driver.py" in json.dumps(sidecar["design"])


# --------------------------------------------------------------------------- #
# Sprint B (B10): the same negative (a), its own thin entry script, sidecar and out dir
# --------------------------------------------------------------------------- #

ENTRY_B_PATH = REPO_ROOT / "scripts" / "spikes" / "260929_nd_sensitivity_sprint_b.py"
SIDECAR_B_PATH = ENTRY_B_PATH.with_suffix(".bth.toml")


def test_sprint_b_entry_fixes_negative_a_for_sprint_b_and_loads_the_same_shared_driver():
    assert ENTRY_B_PATH.is_file(), "the sprint B entry script exists (D17: one entry script and sidecar per sprint)"
    entry = _load(ENTRY_B_PATH, "nd_entry_b_under_test")
    assert entry.NEGATIVES == ("a",) and entry.SPRINT == "b"
    assert entry.SHARED_PATH == SHARED_PATH and SHARED_PATH.is_file()
    assert entry._load_shared() is entry._load_shared(), "loaded once"
    assert "sys.path" not in ENTRY_B_PATH.read_text().replace("nothing edits sys.path", "")


def test_sprint_b_dry_run_defaults_to_its_own_out_dir_and_the_spec_dirs(tmp_path):
    proc = subprocess.run([sys.executable, str(ENTRY_B_PATH), "--dry-run"], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr[-2000:]
    plan = json.loads(proc.stdout)
    assert plan["sprint"] == "b" and [n["id"] for n in plan["negatives"]] == ["a"]
    assert plan["out_dir"] == str(REPO_ROOT / "outputs" / "nd_sensitivity" / "sprint_b")
    assert plan["out_dir"] != str(REPO_ROOT / "outputs" / "nd_sensitivity" / "sprint_a"), "never overwrites sprint A's records"
    assert plan["neg_root"] == "/tmp/claude-1000/nd-neg"
    assert plan["negatives"][0]["serve_dir"] == "/tmp/claude-1000/nd-neg/a/dist"
    assert plan["negatives"][0]["harness_out_dir"] == "/tmp/claude-1000/nd-neg/a/out"


def test_sprint_b_entry_runs_end_to_end_against_the_stub_harness_and_records_its_own_sprint(bed, nd):
    """The whole driver path through the SPRINT B entry: positive control (a failing harness naming the
    key passes the negative), the harness run alone on its own dist and out dir, sprint 'b' recorded."""
    base_env = bed.env

    def env_b() -> dict[str, str]:
        e = base_env()
        e["ND_ENTRY"] = str(ENTRY_B_PATH)
        return e

    bed.env = env_b  # type: ignore[method-assign]
    code, agg = bed.driver()
    assert code == 0 and agg["sprint"] == "b" and agg["all_units_complete"] and agg["outcome_evaluated"]
    art = bed.artifact()
    assert art["outcome"] is True and "rail_state_after_run" in art["failing_keys"]
    (argv,) = bed.harness_runs()
    assert argv[:1] == ["--display-check"] and argv[argv.index("--scenario") + 1] == "D1"
    flat = json.loads(bed.results.read_text())
    assert flat["a_negative_passed"] is True and flat["measurement_valid"] is True


@pytest.fixture(scope="module")
def sidecar_b() -> dict[str, Any]:
    assert SIDECAR_B_PATH.is_file(), "the sprint B sidecar is committed BEFORE the run"
    return tomllib.loads(SIDECAR_B_PATH.read_text())


def test_sprint_b_sidecar_pre_registers_the_same_single_negative_with_a_residual(sidecar_b):
    outcomes = sidecar_b["outcomes"]
    assert set(outcomes) == {"a_sensitive", "a_insensitive", "invalid"}
    assert outcomes["invalid"]["is_residual"] is True
    assert "a_detected = true" in outcomes["a_sensitive"]["condition"]
    assert "a_detected = false" in outcomes["a_insensitive"]["condition"]
    for name in ("a_sensitive", "a_insensitive"):
        assert "measurement_valid = true" in outcomes[name]["condition"]
        assert "all_units_complete = true" in outcomes[name]["condition"]
    hyp = sidecar_b["experiment"]["hypothesis"]
    assert "sprint B" in hyp and "rail_state_after_run" in hyp and "shell/display/index.js" in hyp
    assert sidecar_b["experiment"]["stage_name"]


def test_sprint_b_sidecar_result_schema_matches_the_flat_fields_the_driver_writes(sidecar_b, nd):
    arts = {"a": {"error": None, "harness_stamp_valid": True, "harness_error": None, "pristine_has_target": True,
                  "mutated_lacks_target": True, "harness_exit": 1, "failing_keys": ["rail_state_after_run"], "outcome": True}}
    flat = nd.derive_outcome_fields(arts, {"a": nd.NEGATIVES["a"]})["flat"]
    assert set(sidecar_b["result_schema"]) == set(flat)


def test_sprint_b_sidecar_design_names_its_entry_units_timeouts_and_out_dir(sidecar_b, nd):
    d = sidecar_b["design"]
    text = json.dumps(d)
    assert d["unit_list"] == ["a"] and "260929_nd_sensitivity_sprint_b.py" in text
    assert "outputs/nd_sensitivity/sprint_b" in text
    assert d["timeouts"]["harness_unit_s"] == 360 and d["timeouts"]["negative_unit_s"] == 600
    assert d["timeouts"]["whole_run_timeout"] == "none"
    unit = d["units"]["a"]
    assert unit["required_fields"] == list(nd.REQUIRED_FIELDS) and unit["harness_unit"] == "D1"
    assert unit["expected_key"] == "rail_state_after_run" and unit["mutation"].startswith("remove shell/display/index.js")
    for needle in ("unit_runner.driver_input", "dist_pristine", "dist_mutated", "exit == 0", "error finding",
                   "never reused", "full unit set", "Watchdog", "os._exit", "bth run", "B10"):
        assert needle in text or needle in json.dumps(sidecar_b["experiment"]), needle
    controls = json.dumps(d["controls"])
    assert ("must FAIL" in controls or "must fail" in controls) and "positive" in d["controls"] and "negative" in d["controls"]
    assert "test_nd_sensitivity_driver.py" in text


def test_sprint_b_sidecar_is_a_pre_registration_not_a_receipt():
    """It says, in its own words, that no run had happened when it was written."""
    text = SIDECAR_B_PATH.read_text()
    assert "COMMITTED BEFORE ANY RUN" in text and "No browser has been" in text
    assert "bth run --project-slug praxis" in text and "uv run bth" in text, "names the right invocation and the wrong one"


# --------------------------------------------------------------------------- #
# Sprint C (C7): the shared driver's negatives b, c, d and e (AC-39(b)-(e)); pure plumbing, no subprocess
# --------------------------------------------------------------------------- #

SOCKET = "assets/visualizer3d-augmentations/socket.js"
SRC_FILES = (
    "web-repl/shell/display/dock.js", "web-repl/shell/display/index.js",
    "web-repl/overlay/assets/visualizer3d-augmentations/socket.js", "web-repl/overlay/assets/visualizer3d-augmentations/embed.js",
)


def _src_tree(root: Path, extra: dict[str, str] | None = None) -> Path:
    for rel in SRC_FILES:
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("// benign\nexport const x = 1;\n")
    for rel, text in (extra or {}).items():
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    return root


def test_the_sprint_c_negatives_are_the_ac39_b_c_d_e_mutations_and_keys(nd):
    n = nd.NEGATIVES
    assert {"a", "b", "c", "d", "e"} <= set(n)
    b, c, d, e = n["b"], n["c"], n["d"], n["e"]
    assert (b.harness_flag, b.harness_unit, b.expected_key, b.delete, b.harness_neg) == (
        "--dock-check", "K1a", "viewer_resources", SOCKET, ())
    assert (d.harness_flag, d.harness_unit, d.expected_key, d.delete, d.harness_neg) == (
        "--dock-check", "N-d", "panel_width_wide_1600", None, ())
    assert (e.harness_flag, e.harness_unit, e.expected_key, e.delete, e.harness_neg) == (
        "--dock-check", "K1b", "late_iframe", None, ("drop-query",))
    assert c.kind == "grep" and c.harness_unit == "" and c.delete is None
    assert all(n[i].kind == "harness" for i in ("a", "b", "d", "e"))
    assert d.skippable is True and not b.skippable and not e.skippable
    assert ("neg_dropped_queries", "ge1") in e.result_checks, "the drop-query mutation must be shown to have fired"
    assert ("control_formula_passes", "true") in d.result_checks, "the predicate must be shown able to pass"
    assert n["a"].result_checks == () and n["a"].kind == "harness" and n["a"].skippable is False


def test_negative_a_is_unchanged_by_the_sprint_c_extension(nd):
    a = nd.NEGATIVES["a"]
    assert (a.harness_flag, a.harness_unit, a.expected_key, a.delete) == (
        "--display-check", "D1", "rail_state_after_run", "shell/display/index.js")


def test_a_skipped_d_passes_only_where_the_recorded_sizing_case_allows_the_skip(nd):
    d = nd.NEGATIVES["d"]
    base = dict(stamp_valid=True, harness_exit=0, failing_keys=[], harness_error=None)
    assert nd.negative_outcome(d, skipped=True, skip_allowed=True, **base) == (True, [])
    passed, reasons = nd.negative_outcome(d, skipped=True, skip_allowed=False, **base)
    assert passed is False and any("skip" in r for r in reasons), "the >= 1600 key is asserted: a skip is a gate bug"
    # skipped is not a way to pass for any other negative, and not without a valid stamp
    assert nd.negative_outcome(nd.NEGATIVES["e"], skipped=True, skip_allowed=True, **base)[0] is False
    assert nd.negative_outcome(d, skipped=True, skip_allowed=True, **{**base, "stamp_valid": False})[0] is False
    assert nd.negative_outcome(d, skipped=True, skip_allowed=True, **{**base, "harness_error": {"type": "X"}})[0] is False


def test_the_unskipped_d_follows_the_standard_rule(nd):
    d = nd.NEGATIVES["d"]
    ok = dict(stamp_valid=True, harness_exit=1, failing_keys=["panel_width_wide_1600"], harness_error=None)
    assert nd.negative_outcome(d, **ok) == (True, [])
    assert nd.negative_outcome(d, **{**ok, "harness_exit": 0})[0] is False
    assert nd.negative_outcome(d, **{**ok, "failing_keys": ["viewer_height"]})[0] is False


@pytest.mark.parametrize(
    "check,value,holds",
    [(("neg_dropped_queries", "ge1"), 3, True), (("neg_dropped_queries", "ge1"), 1, True), (("neg_dropped_queries", "ge1"), 0, False),
     (("neg_dropped_queries", "ge1"), None, False), (("neg_dropped_queries", "ge1"), True, False),
     (("control_formula_passes", "true"), True, True), (("control_formula_passes", "true"), False, False),
     (("control_formula_passes", "true"), 1, False), (("control_formula_passes", "true"), None, False)],
)
def test_result_checks_are_strict_about_type_and_value(nd, check, value, holds):
    assert nd.result_check_holds(check, {check[0]: value}) is holds
    assert nd.result_check_holds(check, {}) is False, "an absent key proves nothing"


def test_the_grep_negative_passes_on_a_clean_tree_and_its_scan_is_shown_to_see_a_planted_token(nd, tmp_path):
    root = _src_tree(tmp_path / "src")
    fields = nd.probe_grep(argparse.Namespace(source_root=str(root)), nd.NEGATIVES["c"])
    assert fields["outcome"] is True and fields["match_count"] == 0 and fields["harness_exit"] == 1, "grep exits 1: nothing found"
    assert fields["scan_covers_required_files"] is True and fields["scan_control_finds_planted_token"] is True
    assert fields["files_scanned"] == len(SRC_FILES) and fields["failing_keys"] == []
    assert fields["kind"] == "grep" and fields["harness_flag"] is None and fields["harness_unit"] is None


@pytest.mark.parametrize("token", ["__praxis" + "_test", "data-praxis" + "-test"])
@pytest.mark.parametrize("rel", ["web-repl/shell/display/dock.js", "web-repl/shell/display/dock.test.js",
                                 "web-repl/overlay/assets/visualizer3d-augmentations/socket.js"])
def test_the_grep_negative_fails_naming_the_match_when_a_test_hook_is_present(nd, tmp_path, token, rel):
    root = _src_tree(tmp_path / "src", {rel: f"window.{token} = 1;\n"})
    fields = nd.probe_grep(argparse.Namespace(source_root=str(root)), nd.NEGATIVES["c"])
    assert fields["outcome"] is False and fields["match_count"] >= 1 and fields["harness_exit"] == 0
    assert fields["failing_keys"][0].startswith(rel + ":"), fields["failing_keys"]
    assert fields["scan_covers_required_files"] is True, "a hook is a FINDING about the tree, not an invalid measurement"


def test_the_grep_negative_ignores_the_one_exclusion_the_spec_states(nd, tmp_path):
    root = _src_tree(tmp_path / "src", {"web-repl/shell/display/__tests__/fakes.js": "window.__praxis" + "_test = 1;\n"})
    assert nd.probe_grep(argparse.Namespace(source_root=str(root)), nd.NEGATIVES["c"])["outcome"] is True


def test_a_grep_over_a_tree_that_does_not_contain_the_product_files_is_not_a_valid_measurement(nd, tmp_path):
    empty = tmp_path / "empty"
    (empty / "web-repl/shell/display").mkdir(parents=True)
    (empty / "web-repl/overlay/assets/visualizer3d-augmentations").mkdir(parents=True)
    fields = nd.probe_grep(argparse.Namespace(source_root=str(empty)), nd.NEGATIVES["c"])
    assert fields["outcome"] is True and fields["match_count"] == 0, "nothing matched, vacuously"
    assert fields["scan_covers_required_files"] is False
    flat = nd.derive_outcome_fields({"c": {**fields, "error": None}}, {"c": nd.NEGATIVES["c"]})["flat"]
    assert flat["measurement_valid"] is False, "a scan that read none of dock.js, socket.js, embed.js, index.js proves nothing"


def test_a_grep_whose_scan_cannot_see_a_planted_token_is_not_a_valid_measurement(nd, tmp_path, monkeypatch):
    root = _src_tree(tmp_path / "src")
    rs = nd.repl_smoke()
    monkeypatch.setattr(rs, "ac39c_hits", lambda r: [])  # a blind scan
    fields = nd.probe_grep(argparse.Namespace(source_root=str(root)), nd.NEGATIVES["c"])
    assert fields["scan_control_finds_planted_token"] is False
    flat = nd.derive_outcome_fields({"c": {**fields, "error": None}}, {"c": nd.NEGATIVES["c"]})["flat"]
    assert flat["measurement_valid"] is False


def test_a_grep_over_a_missing_source_tree_raises_so_the_unit_records_an_error(nd, tmp_path):
    with pytest.raises(FileNotFoundError):
        nd.probe_grep(argparse.Namespace(source_root=str(tmp_path / "nope")), nd.NEGATIVES["c"])


def test_the_grep_negatives_inputs_hash_the_scanned_sources_and_no_harness_inputs_change(nd, tmp_path):
    root = _src_tree(tmp_path / "src")
    env = nd.InputEnv("s", "e", "r", "h", "dp", "c", "d")
    before = nd.compute_inputs(nd.NEGATIVES["c"], env, "dm", tmp_path / "neg", source_root=root)
    assert "sources" in before
    (root / SRC_FILES[0]).write_text("// changed\n")
    assert nd.compute_inputs(nd.NEGATIVES["c"], env, "dm", tmp_path / "neg", source_root=root)["sources"] != before["sources"]
    harness = nd.compute_inputs(nd.NEGATIVES["a"], env, "dm", tmp_path / "neg")
    assert "sources" not in harness and set(harness) == {
        "script", "entry", "runner", "harness", "dist_pristine", "dist_mutated", "chrome", "driver", "args"}


def _art(**over):
    base = {"error": None, "harness_stamp_valid": True, "harness_error": None, "pristine_has_target": True,
            "mutated_lacks_target": True, "harness_exit": 1, "failing_keys": [], "outcome": True}
    base.update(over)
    return base


def _c_art(**over):
    base = {"error": None, "kind": "grep", "harness_exit": 1, "failing_keys": [], "outcome": True, "match_count": 0,
            "files_scanned": 4, "scan_covers_required_files": True, "scan_control_finds_planted_token": True}
    base.update(over)
    return base


def _arts_bcde(**over):
    arts = {
        "b": _art(failing_keys=["viewer_resources", "canvas_nonblank"]),
        "c": _c_art(),
        "d": _art(failing_keys=["panel_width_wide_1600"], result_checks={"control_formula_passes": True}, skipped=False,
                  skip_allowed=False),
        "e": _art(failing_keys=["late_iframe"], result_checks={"neg_dropped_queries": True}, dropped_queries=4),
    }
    arts.update(over)
    return arts


def _flat(nd, arts):
    chosen = {k: nd.NEGATIVES[k] for k in arts}
    return nd.derive_outcome_fields(arts, chosen)["flat"]


def test_the_flat_fields_for_b_c_d_e_carry_each_negatives_own_verdict(nd):
    flat = _flat(nd, _arts_bcde())
    assert flat["all_units_complete"] is True and flat["n_negatives"] == 4 and flat["n_error_units"] == 0
    assert flat["measurement_valid"] is True
    for nid in ("b", "d", "e"):
        assert flat[f"{nid}_detected"] is True and flat[f"{nid}_expected_key_failed"] is True
        assert flat[f"{nid}_negative_passed"] is True and flat[f"{nid}_harness_exit"] == 1
    assert flat["b_failing_keys"] == "viewer_resources,canvas_nonblank"
    assert flat["c_negative_passed"] is True and flat["c_match_count"] == 0 and flat["c_files_scanned"] == 4
    assert flat["c_harness_exit"] == 1
    assert "c_detected" not in flat and "c_failing_keys" not in flat, "a grep has no harness keys"
    assert flat["d_skipped"] is False and flat["e_dropped_queries"] == 4


def test_each_negative_can_be_missed_independently_without_invalidating_the_run(nd):
    for nid, over in (
        ("b", _art(harness_exit=0, failing_keys=[], outcome=False)),
        ("c", _c_art(match_count=2, failing_keys=["web-repl/shell/display/dock.js:3"], harness_exit=0, outcome=False)),
        ("d", _art(harness_exit=0, failing_keys=[], outcome=False, result_checks={"control_formula_passes": True},
                   skipped=False, skip_allowed=False)),
        ("e", _art(harness_exit=1, failing_keys=["many_reloads"], outcome=False, result_checks={"neg_dropped_queries": True},
                   dropped_queries=2)),
    ):
        flat = _flat(nd, _arts_bcde(**{nid: over}))
        assert flat["measurement_valid"] is True, nid
        assert flat[f"{nid}_negative_passed"] is False, nid
        assert [flat[f"{o}_negative_passed"] for o in "bcde" if o != nid] == [True, True, True], nid


@pytest.mark.parametrize(
    "nid,over",
    [
        ("e", {"result_checks": {"neg_dropped_queries": False}, "dropped_queries": 0}),  # the mutation never fired
        ("d", {"result_checks": {"control_formula_passes": False}}),  # the predicate cannot pass
        ("b", {"pristine_has_target": False}),  # socket.js was not in the pristine dist: the copy changed nothing
        ("b", {"mutated_lacks_target": False}),
        ("e", {"harness_exit": 124}),
        ("d", {"error": {"type": "DockCheckError"}}),
        ("c", {"scan_covers_required_files": False}),
        ("c", {"scan_control_finds_planted_token": False}),
        ("c", {"error": {"type": "FileNotFoundError"}}),
    ],
)
def test_an_invalid_measurement_in_any_one_negative_invalidates_the_whole_run(nd, nid, over):
    arts = _arts_bcde()
    arts[nid] = {**arts[nid], **over}
    assert _flat(nd, arts)["measurement_valid"] is False


def test_a_skipped_d_is_reported_as_skipped_and_its_validity_does_not_need_the_control(nd):
    art = _art(harness_exit=0, failing_keys=[], outcome=True, skipped=True, skip_allowed=True)
    flat = _flat(nd, _arts_bcde(d=art))
    assert flat["d_skipped"] is True and flat["d_negative_passed"] is True and flat["d_detected"] is False
    assert flat["measurement_valid"] is True


def test_the_dry_run_plan_lists_the_kind_of_every_negative(nd):
    args = argparse.Namespace(sprint="c", entry_path=Path("x.py"), dist="d", neg_root="/tmp/claude-1000/nd-neg", out_dir="o")
    # _dry_run prints JSON; the kinds must be in it
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        nd._dry_run(args, {k: nd.NEGATIVES[k] for k in "bcde"})
    plan = json.loads(buf.getvalue())
    assert {n["id"]: n["kind"] for n in plan["negatives"]} == {"b": "harness", "c": "grep", "d": "harness", "e": "harness"}
    assert [n["harness_neg"] for n in plan["negatives"] if n["id"] == "e"] == [["drop-query"]]
