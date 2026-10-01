"""No-browser checks for the K3 runner and its two pre-registrations (backlog #5656, AC-N5, task T6).

``scripts/spikes/261001_reclaim_k3.py`` runs the harness unit ``K3`` once and turns its result into the flat fields that
``261001_reclaim_k3_red.bth.toml`` and ``261001_reclaim_k3_green.bth.toml`` read. Nothing here launches a browser: the harness unit is the
REAL ``repl_smoke.run_scenario`` / ``run_k3`` run in-process against the scripted page of ``test_repl_smoke_resume.py`` (a build that
re-clamps, one that does not, and the faults of the page), so the result file and the stamp are the production ones.

Controls (BATHOS.md): the pre-registered outcomes are evaluated over the fields the runner really writes, for a build without the fix
(RED), a build with it (GREEN) and every way the instrument can be wrong: each outcome label must come out for its case and for no other.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tomllib
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REPL_SMOKE = REPO_ROOT / "scripts" / "repl_smoke.py"
UNIT_RUNNER = REPO_ROOT / "scripts" / "unit_runner.py"
RUNNER_PATH = REPO_ROOT / "scripts" / "spikes" / "261001_reclaim_k3.py"
RED_LAUNCHER = REPO_ROOT / "scripts" / "spikes" / "261001_reclaim_k3_red.py"
GREEN_LAUNCHER = REPO_ROOT / "scripts" / "spikes" / "261001_reclaim_k3_green.py"
RESUME_TESTS = REPO_ROOT / "web-repl" / "tests" / "test_repl_smoke_resume.py"
NOTEBOOK = REPO_ROOT / "web-repl" / "tests" / "fixtures" / "notebooks" / "display_check.ipynb"

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
def rs() -> Any:
    return _load(REPL_SMOKE, "repl_smoke_k3_runner_under_test")


@pytest.fixture(scope="module")
def ur() -> Any:
    return _load(UNIT_RUNNER, "unit_runner_k3_runner_under_test")


@pytest.fixture()
def k3(monkeypatch) -> Any:
    """The runner module, with the harness's hashed environment made deterministic (no chrome, no uv.lock, no Playwright)."""
    module = _load(RUNNER_PATH, "reclaim_k3_under_test")

    def fake_env(rs_mod, dist, base_path, chrome_path):
        ns = SimpleNamespace(serve_dir=Path(dist), base_path=base_path)
        return rs_mod.build_hash_env(ns, chrome_path, driver_fn=lambda: "v" * 64, chrome_version_fn=lambda p: "stub 1.0")

    monkeypatch.setattr(module, "harness_env", fake_env)
    return module


@pytest.fixture(scope="module")
def rt() -> Any:
    """test_repl_smoke_resume.py loaded as a module, for the scripted page (FakeK3 over FakeDock)."""
    return _load(RESUME_TESTS, "resume_tests_for_k3_runner")


@pytest.fixture(scope="module")
def display_nb() -> dict[str, Any]:
    return json.loads(NOTEBOOK.read_text())


# --------------------------------------------------------------------------- #
# A dist, and a stub harness runner that runs the real unit in-process
# --------------------------------------------------------------------------- #


def make_dist(tmp: Path, *, has_fix: bool, name: str = "dist") -> Path:
    dist = tmp / name
    (dist / "shell" / "display").mkdir(parents=True, exist_ok=True)
    (dist / "shell" / "display" / "dock.js").write_text(
        "export function mountDock() {}\n" + ("function reclaimMedium() {}\n" if has_fix else "")
    )
    (dist / "lab").mkdir(exist_ok=True)
    (dist / "lab" / "index.html").write_text("<html>")
    return dist


class StubRunner:
    """Stands in for ``unit_runner.run_unit``: it runs the REAL ``repl_smoke.run_scenario`` for K3 in-process, with ``run_k3`` driving the
    scripted page ``page(...)`` makes (a fresh page each time), so the result and the stamp are the production ones. ``hang`` returns the
    watchdog's outcome without writing anything; ``raises`` makes the scenario raise (an error finding)."""

    def __init__(self, rs, ur, k3, rt, nb, page, *, hang=False, raises=False, pageerrors=()):
        self.rs, self.ur, self.k3, self.rt, self.nb, self.page = rs, ur, k3, rt, nb, page
        self.hang, self.raises, self.pageerrors, self.calls = hang, raises, list(pageerrors), []

    def run_unit(self, argv, timeout, cwd=None):
        rs, ur = self.rs, self.ur
        self.calls.append((list(argv), timeout))
        if self.hang:
            return SimpleNamespace(exit=124, timed_out=True, killed=True)
        args = rs.parse_args(argv[argv.index("--dock-check"):])
        env = self.k3.harness_env(rs, Path(args.serve_dir), args.base_path, args.chrome_path)

        def scenario(session, unit, e):
            if self.raises:
                raise RuntimeError("stub instrument failure")
            return rs.run_k3(self.page(), self.nb)

        errors = self.pageerrors

        class Session:
            pageerrors = list(errors)

            def close(self):
                pass

        made = []

        def watchdog(budget, on_expire):
            wd = ur.Watchdog(budget, on_expire, token="t", exit_fn=lambda c: None, kill_fn=lambda *a, **k: [])
            made.append(wd)
            return wd

        try:
            code = rs.run_scenario(
                args.scenario, out_dir=Path(args.out_dir), env_fn=lambda: env, session_factory=lambda u, e: Session(),
                scenario_fn=scenario, ensure_token_fn=lambda: "t", watchdog_factory=watchdog, kill_tree_fn=lambda *a, **k: [],
                exit_fn=lambda c: c, neg=tuple(args.neg),
            )
        finally:
            for wd in made:
                wd.disarm()
        return SimpleNamespace(exit=code, timed_out=False, killed=False)


@pytest.fixture()
def bed(rs, ur, k3, rt, display_nb, tmp_path, monkeypatch):
    monkeypatch.delenv("BTH_RESULTS_PATH", raising=False)
    results = tmp_path / "bth_results.json"
    monkeypatch.setenv("BTH_RESULTS_PATH", str(results))

    class Bed:
        def stub(self, reclaim, broken=(), **kw):
            dnb = rs.build_dock_notebook(display_nb)
            return StubRunner(rs, ur, k3, rt, display_nb, lambda: rt.FakeK3(rs, dnb, reclaim=reclaim, broken=broken), **kw)

        def args(self, phase, dist, *extra):
            return k3.parse_args(["--dist", str(dist), "--out-dir", str(tmp_path / f"out_{phase}"), *extra], phase=phase)

        def go(self, phase, dist, runner, *extra):
            code = k3.run(self.args(phase, dist, *extra), runner=runner, chrome_path="/fake/chrome")
            flat = json.loads(results.read_text()) if results.exists() else None
            return code, flat

    b = Bed()
    b.results, b.tmp = results, tmp_path
    return b


# --------------------------------------------------------------------------- #
# The pre-registered outcomes, evaluated over the fields the runner writes
# --------------------------------------------------------------------------- #


def _sidecar(phase: str) -> dict[str, Any]:
    return tomllib.loads((REPO_ROOT / "scripts" / "spikes" / f"261001_reclaim_k3_{phase}.bth.toml").read_text())


def _holds(condition: str, flat: dict) -> bool:
    """Evaluate `a = true AND b = false` over the flat fields (the only form the sidecars use)."""
    for clause in condition.split(" AND "):
        name, _, want = clause.partition(" = ")
        if flat.get(name.strip()) is not (want.strip() == "true"):
            return False
    return True


def label(phase: str, flat: dict) -> str | None:
    for name, outcome in _sidecar(phase)["outcomes"].items():
        if _holds(outcome["condition"], flat):
            return name
    return None


def test_red_on_the_build_without_the_fix_is_red_detected(bed, rs):
    dist = make_dist(bed.tmp, has_fix=False)
    code, flat = bed.go("red", dist, bed.stub(reclaim=False))
    assert code == 0 and flat is not None
    assert label("red", flat) == "red_detected", flat
    assert flat["build_has_fix"] is False and flat["build_matches_phase"] is True and flat["measurement_valid"] is True
    assert flat["failing_keys"] == ",".join(k for k in rs.K3_KEYS if k in rs.K3_RED_FALSE)
    assert flat["red_false_keys_all_false"] is True and flat["red_guard_keys_all_true"] is True and flat["all_keys_true"] is False
    assert flat["preconditions_ok"] is True and flat["all_settled"] is True and flat["step_errors"] == 0
    assert flat["n_keys_true"] == 6 and flat["reused"] is False and flat["phase"] == "red"


def test_red_on_a_dist_that_contains_the_fix_is_invalid_even_though_the_numbers_are_well_formed(bed):
    dist = make_dist(bed.tmp, has_fix=True)
    code, flat = bed.go("red", dist, bed.stub(reclaim=False))
    assert code == 0 and label("red", flat) == "invalid"
    assert flat["build_has_fix"] is True and flat["build_matches_phase"] is False and flat["measurement_valid"] is False


@pytest.mark.parametrize("fault", ["noop_drag", "noop_toggle", "viewport_ignored", "never_settles"])
def test_red_where_an_action_did_nothing_or_a_step_never_settled_is_invalid_never_red_detected(bed, fault):
    dist = make_dist(bed.tmp, has_fix=False)
    code, flat = bed.go("red", dist, bed.stub(reclaim=False, broken=(fault,)))
    assert code == 0 and label("red", flat) == "invalid", (fault, flat["preconditions_ok"], flat["all_settled"])
    assert flat["preconditions_ok"] is False or flat["all_settled"] is False


def test_red_where_a_step_raised_is_invalid(bed):
    dist = make_dist(bed.tmp, has_fix=False)
    code, flat = bed.go("red", dist, bed.stub(reclaim=False, broken=("raise_drag",)))
    assert code == 0 and flat["step_errors"] >= 1 and label("red", flat) == "invalid"


def test_red_where_the_unit_itself_raised_is_invalid(bed):
    dist = make_dist(bed.tmp, has_fix=False)
    code, flat = bed.go("red", dist, bed.stub(reclaim=False, raises=True))
    assert code == 0 and flat["unit_error_free"] is False and flat["keys_present"] is False and label("red", flat) == "invalid"


def test_red_where_the_page_already_re_clamps_is_red_not_as_predicted_a_finding_not_an_instrument_fault(bed):
    """The prediction did not hold (a predicted-false key read true) while every action happened and settled."""
    dist = make_dist(bed.tmp, has_fix=False)
    code, flat = bed.go("red", dist, bed.stub(reclaim=True))
    assert code == 0 and label("red", flat) == "red_not_as_predicted", flat
    assert flat["measurement_valid"] is True and flat["red_false_keys_all_false"] is False and flat["all_keys_true"] is True


def test_red_where_a_guard_key_is_false_is_red_not_as_predicted_and_names_it(bed):
    dist = make_dist(bed.tmp, has_fix=False)
    code, flat = bed.go("red", dist, bed.stub(reclaim=False, broken=("steals_current",)))
    assert code == 0 and label("red", flat) == "red_not_as_predicted"
    assert flat["red_guard_keys_all_true"] is False and flat["k_reclaim_keeps_current_1440"] is False
    assert "reclaim_keeps_current_1440" in flat["failing_keys"].split(",")


def test_green_on_the_build_with_the_fix_is_green(bed):
    dist = make_dist(bed.tmp, has_fix=True)
    code, flat = bed.go("green", dist, bed.stub(reclaim=True))
    assert code == 0 and label("green", flat) == "green", flat
    assert flat["all_keys_true"] is True and flat["n_keys_true"] == 12 and flat["failing_keys"] == ""
    assert flat["build_has_fix"] is True and flat["measurement_valid"] is True and flat["pageerrors_ok"] is True


def test_green_on_a_dist_without_the_fix_is_invalid_not_green_and_not_green_failed(bed):
    dist = make_dist(bed.tmp, has_fix=False)
    code, flat = bed.go("green", dist, bed.stub(reclaim=True))
    assert code == 0 and label("green", flat) == "invalid" and flat["all_keys_true"] is True, "well-formed numbers from the wrong build"


def test_green_where_the_page_does_not_re_clamp_is_green_failed_with_the_failing_keys(bed, rs):
    dist = make_dist(bed.tmp, has_fix=True)
    code, flat = bed.go("green", dist, bed.stub(reclaim=False))
    assert code == 0 and label("green", flat) == "green_failed"
    assert flat["failing_keys"].split(",") == [k for k in rs.K3_KEYS if k in rs.K3_RED_FALSE]


@pytest.mark.parametrize("fault", ["noop_drag", "never_settles", "reload_on_reclaim", "steals_current", "raise_drag"])
def test_green_after_the_fix_a_swallowed_drag_a_loop_a_reload_or_a_step_error_is_a_finding_not_invalid(bed, fault):
    dist = make_dist(bed.tmp, has_fix=True)
    code, flat = bed.go("green", dist, bed.stub(reclaim=True, broken=(fault,)))
    assert code == 0 and label("green", flat) == "green_failed", (fault, flat["failing_keys"])
    assert flat["all_keys_true"] is False


def test_green_where_the_unit_itself_raised_is_invalid(bed):
    dist = make_dist(bed.tmp, has_fix=True)
    code, flat = bed.go("green", dist, bed.stub(reclaim=True, raises=True))
    assert code == 0 and label("green", flat) == "invalid"


# --------------------------------------------------------------------------- #
# Incomplete units, resume, the environment, the aggregate record
# --------------------------------------------------------------------------- #


def test_a_unit_that_timed_out_leaves_no_outcome_and_exits_3(bed):
    dist = make_dist(bed.tmp, has_fix=False)
    code, flat = bed.go("red", dist, bed.stub(reclaim=False, hang=True))
    assert code == 3 and flat is None, "bathos then records no outcome"
    agg = json.loads((bed.tmp / "out_red" / "result.json").read_text())
    assert agg["unit_complete"] is False and agg["outcome_evaluated"] is False and agg["harness_run"]["timed_out"] is True


def test_the_unit_is_started_once_with_its_budget_plus_sixty_seconds_and_its_own_out_dir(bed, rs):
    dist = make_dist(bed.tmp, has_fix=False)
    stub = bed.stub(reclaim=False)
    bed.go("red", dist, stub)
    assert len(stub.calls) == 1
    argv, timeout = stub.calls[0]
    assert timeout == rs.UNIT_BY_ID["K3"].budget_s + 60 == 660
    assert argv[argv.index("--scenario") + 1] == "K3" and "--dock-check" in argv and "--neg" not in argv
    assert argv[argv.index("--serve-dir") + 1] == str(dist.resolve())
    assert argv[argv.index("--out-dir") + 1] == str(bed.tmp / "out_red" / "k3")
    assert argv[argv.index("--base-path") + 1] == "/praxis/" and "--chrome-path" in argv


def test_the_aggregate_records_the_build_the_inputs_and_the_measures(bed):
    dist = make_dist(bed.tmp, has_fix=False)
    code, flat = bed.go("red", dist, bed.stub(reclaim=False))
    agg = json.loads((bed.tmp / "out_red" / "result.json").read_text())
    assert agg["phase"] == "red" and agg["unit"] == "K3" and agg["reused"] is False and agg["unit_complete"] is True
    assert agg["build"]["has_fix"] is False and len(agg["build"]["dock_js_sha256"]) == 64
    assert sorted(agg["inputs"]) == sorted(["dist", "notebook", "harness", "runner", "chrome", "args", "driver"])
    assert agg["outcome_fields"] == flat
    assert agg["k3_measures"]["open_1440"]["dead_space"] == pytest.approx(73.5) and agg["k3_measures"]["high_1440"]["dead_space"] == pytest.approx(220.0)
    assert set(agg["k3_preconditions"]) and set(agg["k3_settled"]) and agg["result_sha256"] == agg["stamp"]["result_sha256"]


def test_resume_reuses_a_valid_unit_without_starting_anything_and_records_that_it_did(bed):
    dist = make_dist(bed.tmp, has_fix=False)
    first = bed.stub(reclaim=False)
    bed.go("red", dist, first)
    second = bed.stub(reclaim=False)
    code, flat = bed.go("red", dist, second, "--resume")
    assert code == 0 and second.calls == [], "nothing was started"
    assert flat["reused"] is True and label("red", flat) == "red_detected", "a RED unit fails its keys by design and is still reusable"
    agg = json.loads((bed.tmp / "out_red" / "result.json").read_text())
    assert agg["reused"] is True and agg["result_sha256"] and agg["inputs"]["dist"]


def test_resume_recomputes_when_the_dist_changed_or_when_the_result_no_longer_matches_its_stamp(bed):
    dist = make_dist(bed.tmp, has_fix=False)
    bed.go("red", dist, bed.stub(reclaim=False))
    (dist / "lab" / "index.html").write_text("<html>changed")  # a different build: the dist hash differs
    second = bed.stub(reclaim=False)
    code, flat = bed.go("red", dist, second, "--resume")
    assert len(second.calls) == 1 and flat["reused"] is False
    result_file = bed.tmp / "out_red" / "k3" / "result.K3.json"
    result_file.write_text(result_file.read_text() + " ")  # the bytes no longer match the stamp's sha256
    third = bed.stub(reclaim=False)
    code, flat = bed.go("red", dist, third, "--resume")
    assert len(third.calls) == 1 and flat["reused"] is False


def test_without_resume_the_unit_is_always_started_again(bed):
    dist = make_dist(bed.tmp, has_fix=False)
    bed.go("red", dist, bed.stub(reclaim=False))
    again = bed.stub(reclaim=False)
    bed.go("red", dist, again)
    assert len(again.calls) == 1


def test_the_old_files_are_cleared_before_a_rerun_so_a_stale_stamp_is_never_judged(bed):
    dist = make_dist(bed.tmp, has_fix=False)
    bed.go("red", dist, bed.stub(reclaim=False))
    stamp = bed.tmp / "out_red" / "k3" / "result.K3.stamp.json"
    assert stamp.exists()
    code, flat = bed.go("red", dist, bed.stub(reclaim=False, hang=True))
    assert code == 3 and flat is None and not stamp.exists(), "the hung rerun did not inherit the earlier stamp"


def test_a_dist_without_the_display_shell_is_an_environment_error_and_nothing_runs(bed):
    dist = bed.tmp / "empty"
    dist.mkdir()
    stub = bed.stub(reclaim=False)
    code, flat = bed.go("red", dist, stub)
    assert code == 2 and flat is None and stub.calls == []


def test_dist_build_reads_the_token_from_dock_js_only(bed, k3):
    assert k3.dist_build(make_dist(bed.tmp, has_fix=True, name="a"))["has_fix"] is True
    assert k3.dist_build(make_dist(bed.tmp, has_fix=False, name="b"))["has_fix"] is False
    other = make_dist(bed.tmp, has_fix=False, name="c")
    (other / "shell" / "display" / "dock_reclaim.test.js").write_text("reclaimMedium")
    (other / "shell" / "display" / "index.js").write_text("reclaimMedium")
    assert k3.dist_build(other)["has_fix"] is False, "only dock.js decides"
    with pytest.raises(FileNotFoundError):
        k3.dist_build(bed.tmp / "nowhere")


# --------------------------------------------------------------------------- #
# The launchers and the sidecars
# --------------------------------------------------------------------------- #


def test_the_launchers_fix_the_phase_and_refuse_the_other_one(capsys):
    red = _load(RED_LAUNCHER, "red_launcher_under_test")
    green = _load(GREEN_LAUNCHER, "green_launcher_under_test")
    assert red.main(["--dry-run"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["phase"] == "red" and plan["must_contain_fix"] is False and plan["unit"] == "K3" and plan["run_unit_timeout_s"] == 660.0
    assert green.main(["--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["must_contain_fix"] is True
    with pytest.raises(SystemExit):
        green.main(["--phase", "red", "--dry-run"])
    with pytest.raises(SystemExit):
        red.main(["--phase", "green", "--dry-run"])


def test_the_bare_runner_requires_a_phase(k3):
    with pytest.raises(SystemExit):
        k3.parse_args([], phase=None)
    assert k3.parse_args(["--phase", "green"], phase=None).phase == "green"


def test_each_sidecar_sits_beside_the_launcher_of_the_same_name():
    for phase, launcher in (("red", RED_LAUNCHER), ("green", GREEN_LAUNCHER)):
        assert launcher.with_suffix(".bth.toml").is_file() and launcher.with_suffix(".bth.toml").name == f"261001_reclaim_k3_{phase}.bth.toml"
    assert not RUNNER_PATH.with_suffix(".bth.toml").exists(), "the bare runner has no sidecar: bathos would refuse an unregistered phase"


def test_the_outcome_order_and_the_residual_flag_of_each_sidecar():
    red, green = _sidecar("red"), _sidecar("green")
    assert list(red["outcomes"]) == ["invalid", "red_detected", "red_not_as_predicted"]
    assert list(green["outcomes"]) == ["invalid", "green", "green_failed"]
    for sc in (red, green):
        assert sc["outcomes"]["invalid"]["is_residual"] is True and all(o["is_residual"] is False for n, o in sc["outcomes"].items() if n != "invalid")


def test_every_field_the_sidecars_read_and_declare_is_a_field_the_runner_writes(bed):
    dist = make_dist(bed.tmp, has_fix=False)
    _, flat = bed.go("red", dist, bed.stub(reclaim=False))
    for phase in ("red", "green"):
        sc = _sidecar(phase)
        used = set()
        for outcome in sc["outcomes"].values():
            used |= set(re.findall(r"[a-z_]+(?= (?:=|!=|>|<))", outcome["condition"]))
        assert used and used <= set(flat), (phase, sorted(used - set(flat)))
        assert set(sc["result_schema"]) == set(flat), (phase, sorted(set(sc["result_schema"]) ^ set(flat)))
        for name, typ in sc["result_schema"].items():
            want = {"bool": bool, "int": int, "str": str}[typ]
            assert type(flat[name]) is want, (phase, name, typ, type(flat[name]))


def test_the_red_sidecar_pre_registers_the_same_key_lists_the_code_uses(rs):
    red = _sidecar("red")
    assert red["design"]["red_false_keys"] == list(rs.K3_RED_FALSE) and red["design"]["red_guard_keys"] == list(rs.K3_RED_GUARD)
    text = red["experiment"]["hypothesis"]
    for key in rs.K3_KEYS:
        assert key in text, key
    for estimate in red["design"]["estimates_never_measured"]:
        assert estimate in rs.K3_RED_FALSE and estimate in text
    assert red["design"]["estimates_never_measured"] == ["reclaim_after_toggle_1440", "reclaim_after_resize_down", "reclaim_after_resize_up"]


def test_the_green_sidecar_lists_the_units_thirteen_keys_in_order(rs):
    assert _sidecar("green")["design"]["listed_keys"] == list(rs.UNIT_BY_ID["K3"].keys)
    text = _sidecar("green")["experiment"]["hypothesis"]
    for key in rs.K3_KEYS:
        assert key in text, key


def test_both_sidecars_state_the_budgets_and_that_the_exploratory_numbers_are_a_prior():
    for phase in ("red", "green"):
        sc = _sidecar(phase)
        assert "600 s" in sc["design"]["timeouts"] and "660 s" in sc["design"]["timeouts"]
        assert sc["design"]["runner"].startswith("scripts/spikes/261001_reclaim_k3.py")
        assert "whole-run timeout" in sc["design"]["statement"]
    header = (REPO_ROOT / "scripts" / "spikes" / "261001_reclaim_k3_red.bth.toml").read_text().split("[experiment]")[0]
    assert "NO sidecar" in header and "PRIOR" in header and "ESTIMATES" in header


@pytest.mark.skipif(shutil.which("bth") is None, reason="bth is not installed")
@pytest.mark.parametrize("phase", ["red", "green"])
def test_bth_validates_the_sidecar(phase):
    path = REPO_ROOT / "scripts" / "spikes" / f"261001_reclaim_k3_{phase}.bth.toml"
    out = subprocess.run(["bth", "validate-sidecar", str(path)], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and json.loads(out.stdout)["validation_ok"] is True, out.stdout + out.stderr


# --------------------------------------------------------------------------- #
# flat_fields directly: each term of the validity and of the verdicts has a case that isolates it
# --------------------------------------------------------------------------- #


def _result(rt, rs, build="stock", **over):
    """A K3 result as the harness writes it: the derived keys of the scripted page's raw evidence, an evidence block and no error."""
    keys = rs.derive_k3_keys(rt._k3_raw(build))
    keys.update({"evidence": {"step_errors": {}}, "error": None, "pageerrors": []})
    keys.update(over)
    return keys


def test_flat_fields_a_step_error_alone_invalidates_a_red_run_but_not_a_green_one(rs, rt, k3):
    result = _result(rt, rs, evidence={"step_errors": {"tier_entry": "DockCheckError: x"}})
    red = k3.flat_fields("red", result, has_fix=False, reused=False, harness_exit=1)
    assert red["step_errors"] == 1 and red["preconditions_ok"] is True and red["all_settled"] is True and red["measurement_valid"] is False
    green = k3.flat_fields("green", _result(rt, rs, "fixed", evidence={"step_errors": {"tier_entry": "x"}}), has_fix=True, reused=False, harness_exit=1)
    assert green["step_errors"] == 1 and green["measurement_valid"] is True


def test_flat_fields_an_error_finding_or_recorded_only_status_alone_invalidates_both_phases(rs, rt, k3):
    for phase, build, has_fix in (("red", "stock", False), ("green", "fixed", True)):
        ok = k3.flat_fields(phase, _result(rt, rs, build), has_fix=has_fix, reused=False, harness_exit=0)
        assert ok["measurement_valid"] is True, phase
        errored = k3.flat_fields(phase, _result(rt, rs, build, error={"type": "RuntimeError"}), has_fix=has_fix, reused=False, harness_exit=1)
        assert errored["unit_error_free"] is False and errored["keys_present"] is True and errored["measurement_valid"] is False, phase
        only = k3.flat_fields(phase, _result(rt, rs, build, reclaim_status="recorded-only"), has_fix=has_fix, reused=False, harness_exit=0)
        assert only["status_asserted"] is False and only["measurement_valid"] is False, phase


def test_flat_fields_one_predicted_false_key_reading_true_is_red_not_as_predicted_the_weak_estimate_case(rs, rt, k3):
    """The likeliest surprise: `reclaim_after_resize_up` (an estimate of 11-20 px) reads inside 2 px, while everything else is as predicted."""
    raw = rt._k3_raw("stock")
    raw["resize_up"]["snap"] = rt._k3_lay(1122, 420.0, inner=1440)  # nothing empty after 1280 -> 1440
    result = rs.derive_k3_keys(raw)
    result.update({"evidence": {"step_errors": {}}, "error": None, "pageerrors": []})
    flat = k3.flat_fields("red", result, has_fix=False, reused=False, harness_exit=1)
    assert flat["k_reclaim_after_resize_up"] is True and flat["measurement_valid"] is True
    assert flat["red_false_keys_all_false"] is False and flat["red_guard_keys_all_true"] is True
    assert label("red", flat) == "red_not_as_predicted"


def test_flat_fields_page_errors_fail_the_guards_and_the_green_verdict_but_not_the_validity(rs, rt, k3):
    red = k3.flat_fields("red", _result(rt, rs, pageerrors=["TypeError: x"]), has_fix=False, reused=False, harness_exit=1)
    assert red["pageerrors_ok"] is False and red["red_guard_keys_all_true"] is False and red["measurement_valid"] is True
    assert label("red", red) == "red_not_as_predicted"
    green = k3.flat_fields("green", _result(rt, rs, "fixed", pageerrors=["TypeError: x"]), has_fix=True, reused=False, harness_exit=1)
    assert green["all_keys_true"] is False and green["n_keys_true"] == 12 and label("green", green) == "green_failed"


def test_flat_fields_a_missing_key_is_not_a_false_key(rs, rt, k3):
    result = _result(rt, rs)
    del result["reclaim_open_1440"]
    flat = k3.flat_fields("red", result, has_fix=False, reused=False, harness_exit=1)
    assert flat["keys_present"] is False and flat["measurement_valid"] is False and label("red", flat) == "invalid"
