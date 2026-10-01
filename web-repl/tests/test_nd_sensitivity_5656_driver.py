"""No-browser checks for N-g, the re-runnable negative of the deck-layout increment (backlog #5656, AC-N6, task T7).

``scripts/negatives/261001_nd_sensitivity_5656.py`` adds the negative ``g`` to the shared AC-39 driver
``scripts/negatives/260929_nd_sensitivity.py`` WITHOUT editing it (the shared file is a hashed input of the locked sprint A, B and C
runs, A31), the harness unit ``N-g`` in ``scripts/repl_smoke.py`` measures a STOCK split carrying the deck's limits, and
``scripts/spikes/261001_nd_sensitivity_5656.bth.toml`` pre-registers the outcomes. Nothing here launches a browser: it proves the
derivation of the key on the recorded 1440 arrangement, its validity rules, the registration, and the probe plumbing against a stub
harness runner, so that when the real run happens a plumbing bug cannot be mistaken for a finding about Lumino.

Controls (BATHOS.md): every positive (the recorded stock arrangement is detected; a stub harness that fails naming the key passes the
negative) is paired with negatives (a sized arrangement is not detected; a harness that passes, fails another key, cannot pass its own
control, raised or timed out must NOT pass the negative; every validity input, removed, invalidates the measurement).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
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
SHARED_PATH = REPO_ROOT / "scripts" / "negatives" / "260929_nd_sensitivity.py"
DRIVER_PATH = REPO_ROOT / "scripts" / "negatives" / "261001_nd_sensitivity_5656.py"
ENTRY_PATH = REPO_ROOT / "scripts" / "spikes" / "261001_nd_sensitivity_5656.py"
SIDECAR_PATH = ENTRY_PATH.with_suffix(".bth.toml")
#: sha256 of scripts/negatives/260929_nd_sensitivity.py at 98a233ed, the file the locked sprint A, B and C runs hash as `script`.
LOCKED_SHARED_SHA256 = "725b56ae218181389f33d3ecbe811ef7af76cc511155898d8c8a13071fee18d4"

pytestmark = pytest.mark.timeout(120)


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
    return _load(REPL_SMOKE, "repl_smoke_5656_under_test")


@pytest.fixture(scope="module")
def ur() -> Any:
    return _load(UNIT_RUNNER, "unit_runner_5656_under_test")


@pytest.fixture(scope="module")
def drv() -> Any:
    return _load(DRIVER_PATH, "nd_5656_driver_under_test")


# --------------------------------------------------------------------------- #
# The arrangement: literal rectangles
# --------------------------------------------------------------------------- #


def _snap(dock, nbk, deck, *, inner=1440, sizes=(0.5, 0.5), handles=((5, True), (0, False))):
    """One layout snapshot: three rectangles as {left, right, width}, the handles, the viewport, the layout config's split sizes."""

    def box(left, right, width):
        return {"left": left, "right": right, "width": width}

    return {
        "inner_width": inner,
        "rects": {"dock_panel": box(*dock), "notebook_panel": box(*nbk), "deck_panel": box(*deck)},
        "handles": [{"rect": {"width": w}, "classes": ["lm-DockPanel-handle"], "visible": v} for w, v in handles],
        "styles": {"deck_panel": {"max_width": "480px", "min_width": "420px"}},
        "split_sizes": [{"orientation": "horizontal", "sizes": list(sizes)}],
    }


#: RECORDED: outputs/repl_smoke/dock-check/result.K2.json (result_sha256 e0176c978f22f9ca9908ce1213308e5ca11e951b611f64b25ff89e05e178b1e2,
#: dist ba43b338), evidence.medium["1440"].geo_before: 1440x900, file browser open, the deck (480) centred in a 553.5 half, 73.5 px empty.
RECORDED_STOCK_1440 = _snap((285, 1407, 1122), (290, 843.5, 553.5), (885.25, 1365.25, 480))
#: CONSTRUCTED, not recorded: the same widget when its half is 480 / A, A = 1122 - 10 - 5 = 1107, so the notebook has 627 and nothing
#: is empty (dead = 1122 - 627 - 480 - 5 - 10 = 0). Its sizes are the saved config after the harness restored it.
SIZED_CONTROL_1440 = _snap((285, 1407, 1122), (290, 917, 627), (922, 1402, 480), sizes=(627 / 1107, 480 / 1107))
COMPUTED = {"min_width": "420px", "max_width": "480px"}


def _raw(stock=RECORDED_STOCK_1440, control=SIZED_CONTROL_1440, computed=COMPUTED):
    return copy.deepcopy({"ok": True, "stock": stock, "computed": computed, "sized_control": control, "sized_error": None})


# --------------------------------------------------------------------------- #
# derive_ng_keys / ng_measurement_problem
# --------------------------------------------------------------------------- #


def test_the_recorded_arrangement_is_the_one_the_unit_describes(rs):
    assert rs.real_dead_space(RECORDED_STOCK_1440) == pytest.approx(73.5)
    assert rs.real_dead_space(SIZED_CONTROL_1440) == pytest.approx(0.0)
    assert rs.layout_summary(RECORDED_STOCK_1440)["deck_width"] == 480.0


def test_derive_ng_keys_positive_control_the_recorded_stock_arrangement_is_detected_and_the_control_passes(rs):
    keys = rs.derive_ng_keys(_raw())
    assert keys[rs.NG_KEY] is False, "K3's predicate reports FAILURE on the layout Lumino leaves"
    assert keys["ng_detected"] is True
    assert keys["control_sized_passes"] is True
    assert keys["stock_measures"]["dead_space"] == pytest.approx(73.5) and keys["stock_measures"]["deck"] == 480.0
    assert keys["sized_control_measures"]["dead_space"] == pytest.approx(0.0)
    assert keys["stock_sizes"] == [0.5, 0.5] and keys["computed"] == COMPUTED
    json.dumps(keys)


def test_derive_ng_keys_negative_control_a_stock_arrangement_with_no_empty_strip_is_not_detected(rs):
    """The contradiction case (g_not_detected): a valid even split carrying the limits that nevertheless leaves nothing empty."""
    no_strip = _snap((285, 1407, 1122), (290, 917, 627), (922, 1402, 480), sizes=(0.5, 0.5))
    keys = rs.derive_ng_keys(_raw(stock=no_strip))
    assert keys[rs.NG_KEY] is True and keys["ng_detected"] is False
    sized_at_420 = _snap((285, 1407, 1122), (290, 977, 687), (982, 1402, 420), sizes=(0.5, 0.5))
    assert rs.derive_ng_keys(_raw(stock=sized_at_420))["ng_detected"] is True, "420 is not the wanted 480: still not reclaim_ok"


def test_the_unit_lists_the_predicate_as_its_one_key_which_the_recorded_arrangement_fails(rs):
    unit = rs.UNIT_BY_ID["N-g"]
    assert unit.expected == ((rs.NG_KEY, True),) and unit.check == "dock-check" and unit.acs == ("AC-N6",)
    assert unit.budget_s == 360.0 and unit.viewports == ((1440, 900),) and unit.in_aggregate is False
    assert "N-g" not in [u.id for u in rs.DOCK_AGGREGATE_UNITS], "negative only, like N-d: no CI step, not in the aggregate"
    keys = rs.derive_ng_keys(_raw())
    assert rs.evaluate_unit_result(unit, dict(keys, pageerrors=[])) == ([], [rs.NG_KEY]), "the unit fails BY DESIGN on a stock split"
    sized = rs.derive_ng_keys(_raw(stock=_snap((285, 1407, 1122), (290, 917, 627), (922, 1402, 480))))
    assert rs.evaluate_unit_result(unit, dict(sized, pageerrors=[])) == ([], []), "and passes (a contradicting result) when nothing is empty"


def test_ng_measurement_problem_is_none_for_a_valid_measurement(rs):
    assert rs.ng_measurement_problem(_raw()) is None


@pytest.mark.parametrize("label", ["stock", "sized_control"])
@pytest.mark.parametrize("name", ["dock_panel", "notebook_panel", "deck_panel"])
def test_ng_measurement_is_invalid_when_a_rect_is_missing_in_either_snapshot(rs, drv, label, name):
    raw = _raw()
    del raw[label]["rects"][name]
    assert f"{label}: rects.{name}" in rs.ng_measurement_problem(raw)
    with pytest.raises(rs.DockCheckError, match="N-g measurement invalid"):
        rs.derive_ng_keys(raw)


def test_ng_measurement_is_invalid_when_a_rect_is_not_numeric_or_the_inset_is_not_the_docks_padding(rs):
    raw = _raw()
    raw["stock"]["rects"]["deck_panel"]["width"] = "480"
    assert "not numeric" in rs.ng_measurement_problem(raw)
    raw = _raw()
    raw["sized_control"]["rects"]["notebook_panel"]["left"] = 340  # inset 55
    assert "inset" in rs.ng_measurement_problem(raw)


@pytest.mark.parametrize("sizes", [(0.3, 0.7), (0.7, 0.3), (0.5, 0.5, 0.0), (0.52, 0.48)])
def test_ng_measurement_is_invalid_on_a_split_that_is_not_an_even_two_way_split(rs, sizes):
    raw = _raw(stock=_snap((285, 1407, 1122), (290, 843.5, 553.5), (885.25, 1365.25, 480), sizes=sizes))
    problem = rs.ng_measurement_problem(raw)
    assert problem is not None and "even two-way split" in problem
    with pytest.raises(rs.DockCheckError):
        rs.derive_ng_keys(raw)


def test_ng_measurement_even_split_tolerance_is_a_hundredth(rs):
    edge = _raw(stock=_snap((285, 1407, 1122), (290, 843.5, 553.5), (885.25, 1365.25, 480), sizes=(0.51, 0.49)))
    assert rs.ng_measurement_problem(edge) is None
    assert rs.ng_measurement_problem(_raw(stock=_snap((285, 1407, 1122), (290, 843.5, 553.5), (885.25, 1365.25, 480), sizes=(0.511, 0.489)))) is not None


def test_ng_measurement_is_invalid_without_a_readable_split_config(rs):
    raw = _raw()
    del raw["stock"]["split_sizes"]
    assert "even two-way split" in rs.ng_measurement_problem(raw)
    raw = _raw()
    raw["stock"]["split_sizes"] = [{"orientation": "vertical", "sizes": [0.5, 0.5]}]
    assert rs.ng_measurement_problem(raw) is not None


@pytest.mark.parametrize("computed", [
    {"min_width": "0px", "max_width": "none"}, {"min_width": "420px", "max_width": "none"}, {"min_width": "420px", "max_width": "500px"},
    {}, None,
])
def test_ng_measurement_is_invalid_when_the_stock_node_does_not_carry_the_decks_limits(rs, computed):
    raw = _raw(computed=computed)
    assert "does not carry the deck's limits" in rs.ng_measurement_problem(raw)


def test_ng_measurement_is_invalid_when_the_control_cannot_pass_the_predicate(rs):
    """The positive control inside the unit: if the SAME widget sized by the harness still fails, the predicate proves nothing."""
    for control in (RECORDED_STOCK_1440, _snap((285, 1407, 1122), (290, 977, 687), (982, 1402, 420))):
        problem = rs.ng_measurement_problem(_raw(control=control))
        assert problem is not None and "control" in problem
    raw = _raw()
    raw["sized_control"] = None
    assert rs.ng_measurement_problem(raw) is not None, "the sizing step raised in the page: no control, no verdict"


def test_ng_measurement_is_invalid_when_the_page_could_not_build_the_widget(rs):
    assert "could not build" in rs.ng_measurement_problem({"ok": False, "error": "no root Lumino Widget constructor"})
    assert rs.ng_measurement_problem(None) is not None and rs.ng_measurement_problem("x") is not None and rs.ng_measurement_problem({}) is not None


def test_ng_validity_does_not_read_the_dead_space_it_judges(rs):
    """A stock snapshot with ANY dead space (here none) is still a valid measurement; validity looks at inputs, not at that output."""
    no_strip = _snap((285, 1407, 1122), (290, 917, 627), (922, 1402, 480), sizes=(0.5, 0.5))
    huge_strip = _snap((285, 1407, 1122), (290, 417, 127), (1042, 1522, 480), sizes=(0.5, 0.5))
    assert rs.ng_measurement_problem(_raw(stock=no_strip)) is None
    assert rs.ng_measurement_problem(_raw(stock=huge_strip)) is None


# --------------------------------------------------------------------------- #
# The harness side: run_ng, the dispatch, the page helper
# --------------------------------------------------------------------------- #


class FakeNg:
    def __init__(self, raw):
        self.raw, self.calls = raw, []

    def open_lab(self):
        self.calls.append("open_lab")

    def seed_and_open(self, name, nb):
        self.calls.append(("seed_and_open", name))

    def run_cell(self, index):
        self.calls.append("run_cell")

    def stock_split_capped(self):
        self.calls.append("stock_split_capped")
        if isinstance(self.raw, Exception):
            raise self.raw
        return self.raw


@pytest.fixture(scope="module")
def display_nb():
    return json.loads((REPO_ROOT / "web-repl" / "tests" / "fixtures" / "notebooks" / "display_check.ipynb").read_text())


def test_run_ng_boots_no_kernel_and_docks_nothing(rs, display_nb):
    driver = FakeNg(_raw())
    keys = rs.run_ng(driver, display_nb)
    assert driver.calls == ["open_lab", ("seed_and_open", "dock_check.ipynb"), "stock_split_capped"], "no dock() cell, no setup cells"
    assert keys["ng_detected"] is True and keys[rs.NG_KEY] is False


def test_run_ng_raises_on_a_measurement_it_cannot_trust_so_the_unit_records_an_error_finding(rs, display_nb):
    with pytest.raises(rs.DockCheckError, match="N-g measurement invalid"):
        rs.run_ng(FakeNg(_raw(computed={})), display_nb)
    with pytest.raises(rs.DockCheckError, match="could not add"):
        rs.run_ng(FakeNg(rs.DockCheckError("could not add the capped stock split-right widget: 'x'")), display_nb)


def test_run_dock_scenario_dispatches_n_g_to_run_ng(rs, monkeypatch, display_nb):
    calls = []
    monkeypatch.setattr(rs, "DockDriver", lambda session, **k: object())
    for name in ("run_k1a", "run_k1b", "run_k2", "run_k3", "run_nd", "run_ng"):
        monkeypatch.setattr(rs, name, lambda d, f, _n=name, **kw: calls.append(_n) or {"body": _n})
    env = SimpleNamespace()
    assert rs.run_dock_scenario(object(), rs.UNIT_BY_ID["N-g"], env, notebook=display_nb) == {"body": "run_ng"}
    assert calls == ["run_ng"]


def test_the_page_helper_sets_the_decks_limits_before_it_adds_the_widget_and_never_loads_the_viewer(rs):
    js = rs.DOCK_CHECK_JS
    assert "D.stockSplitCapped = async" in js
    body = js.split("D.stockSplitCapped = async")[1].split("\n  };\n")[0]
    assert body.index('node.style.minWidth = "420px"') < body.index("shell.add(widget") and body.index('node.style.maxWidth = "480px"') < body.index("shell.add(widget")
    assert "_dockPanel.fit()" in body and "restoreLayout(config)" in body and "saveLayout()" in body, "fit like dock.js, size by the layout path"
    assert "iframe" not in body, "the arrangement does not depend on a viewer page"
    assert "controllers" not in body and "dockCtl" not in body, "no dock.js controller is touched: the stock widget is the harness's own"
    assert "sized_control" in body and "computed" in body


# --------------------------------------------------------------------------- #
# The driver: registration without editing the locked shared file
# --------------------------------------------------------------------------- #


def test_the_locked_shared_driver_is_byte_identical_to_the_one_the_sprint_runs_hashed(drv):
    assert hashlib.sha256(SHARED_PATH.read_bytes()).hexdigest() == LOCKED_SHARED_SHA256, "A31: never edit the shared driver"
    shared = drv.load_shared()
    assert shared.SCRIPT_PATH == SHARED_PATH.resolve()
    assert hashlib.sha256(shared.SCRIPT_PATH.read_bytes()).hexdigest() == LOCKED_SHARED_SHA256


def test_negative_g_is_registered_in_the_loaded_module_and_is_the_n_g_unit_with_its_control_as_a_validity_check(drv):
    shared = drv.load_shared()
    g = shared.NEGATIVES["g"]
    assert (g.id, g.harness_flag, g.harness_unit, g.expected_key, g.delete, g.kind) == (
        "g", "--dock-check", "N-g", "reclaim_ok_stock_capped_1440", None, "harness"
    )
    assert g.result_checks == (("control_sized_passes", "true"),) and g.skippable is False and g.harness_neg == ()
    assert drv.NEGATIVES == ("g",) and set(shared.NEGATIVES) >= {"a", "b", "c", "d", "e", "g"}, "the earlier negatives are untouched"
    assert shared.NEGATIVES["d"].harness_unit == "N-d"


def test_the_expected_key_is_the_one_the_harness_unit_lists(drv, rs):
    assert drv.EXPECTED_KEY == rs.NG_KEY == rs.UNIT_BY_ID[drv.HARNESS_UNIT].keys[0]


def test_the_dry_run_names_one_unit_with_its_own_dist_and_out_dir(drv, capsys, tmp_path):
    assert drv.main(["--dry-run", "--out-dir", str(tmp_path / "o"), "--neg-root", str(tmp_path / "neg")]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["sprint"] == "5656" and [n["id"] for n in plan["negatives"]] == ["g"]
    g = plan["negatives"][0]
    assert g["harness_unit"] == "N-g" and g["serve_dir"] == str(tmp_path / "neg" / "g" / "dist") and g["harness_out_dir"] == str(tmp_path / "neg" / "g" / "out")
    assert plan["budgets"]["g"] == {"harness_budget_s": 360.0, "unit_timeout_s": 600.0, "driver_kill_s": 660.0}
    assert Path(plan["entry"]) == DRIVER_PATH.resolve(), "the driver file in scripts/negatives (not the launcher) is the run's `entry` input"


def test_the_bathos_visible_entry_launches_the_same_driver(capsys, tmp_path):
    entry = _load(ENTRY_PATH, "nd_5656_entry_under_test")
    assert entry.DRIVER_PATH == DRIVER_PATH.resolve()
    assert entry.main(["--dry-run", "--out-dir", str(tmp_path / "o")]) == 0
    assert json.loads(capsys.readouterr().out)["negatives"][0]["id"] == "g"


# --------------------------------------------------------------------------- #
# The probe against a stub harness runner (real run_scenario, real stamps, real inspect_unit)
# --------------------------------------------------------------------------- #

CHROME_VERSION = "stub 1.0"
DRIVER_HASH = "v" * 64


class StubRunner:
    """Stands in for ``unit_runner.run_unit`` for the HARNESS unit: it runs the real ``repl_smoke.run_scenario`` in-process with a scenario
    that returns ``fields`` (or raises), so the harness's result and stamp are the production ones and the driver's cross-check of the
    stamp's inputs (the harness must have served the copy) is exercised for real."""

    def __init__(self, rs, ur, fields=None, *, raises=False, hang=False):
        self.rs, self.ur, self.fields, self.raises, self.hang, self.argvs = rs, ur, fields, raises, hang, []

    def run_unit(self, argv, timeout, cwd=None):
        rs, ur = self.rs, self.ur
        self.argvs.append(list(argv))
        if self.hang:
            return SimpleNamespace(exit=124, timed_out=True, killed=True)
        args = rs.parse_args([a for a in argv[argv.index("--dock-check"):]])
        env = rs.build_hash_env(
            args, args.chrome_path, dist_hash_fn=lambda d: ur.dist_hash(d), chrome_version_fn=lambda p: CHROME_VERSION,
            driver_fn=lambda: DRIVER_HASH,
        )

        def scenario(session, unit, e):
            if self.raises:
                raise RuntimeError("stub instrument failure")
            return dict(self.fields)

        class Session:
            pageerrors: list[str] = []

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


def _bed(drv, rs, ur, tmp_path):
    shared = drv.load_shared()
    pristine = tmp_path / "pristine"
    for rel, text in (("shell/display/dock.js", "// dock"), ("lab/index.html", "<html>")):
        f = pristine / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    env = shared.InputEnv(
        script="s" * 64, entry="e" * 64, runner="r" * 64, harness="h" * 64, dist_pristine=ur.dist_hash(pristine), chrome="c" * 64,
        driver=DRIVER_HASH, base_path="/praxis/", chrome_path="/fake/chrome", chrome_version=CHROME_VERSION,
    )
    args = argparse.Namespace(dist=pristine, neg_root=tmp_path / "nd-neg")
    return shared, shared.NEGATIVES["g"], env, args


def _detect_fields(rs, **over):
    """What the harness unit returns when it works: the derived keys of the recorded stock arrangement (the predicate FAILS)."""
    return {**rs.derive_ng_keys(_raw()), **over}


def test_probe_positive_control_a_harness_that_fails_naming_the_key_passes_the_negative(rs, ur, drv, tmp_path):
    shared, g, env, args = _bed(drv, rs, ur, tmp_path)
    stub = StubRunner(rs, ur, _detect_fields(rs))
    art = shared.probe_negative(args, g, env, runner=stub)
    assert art["outcome"] is True and art["outcome_reasons"] == []
    assert art["harness_exit"] == 1 and art["failing_keys"] == [rs.NG_KEY] and art["harness_stamp_valid"] is True
    assert art["result_checks"] == {"control_sized_passes": True}
    assert art["harness_argv"][-1] == env.chrome_path or "--chrome-path" in art["harness_argv"]
    argv = stub.argvs[0]
    assert argv[argv.index("--scenario") + 1] == "N-g" and "--dock-check" in argv and "--neg" not in argv
    assert argv[argv.index("--serve-dir") + 1] == str(tmp_path / "nd-neg" / "g" / "dist")
    assert argv[argv.index("--out-dir") + 1] == str(tmp_path / "nd-neg" / "g" / "out")
    flat = shared.derive_outcome_fields({"g": dict(art, error=None)}, {"g": g})["flat"]
    assert flat["measurement_valid"] is True and flat["g_negative_passed"] is True and flat["g_detected"] is True


def test_probe_negative_control_a_harness_that_passes_is_not_a_detection(rs, ur, drv, tmp_path):
    """The contradicting result: the predicate held on the stock arrangement. The unit exits 0, the negative does NOT pass."""
    shared, g, env, args = _bed(drv, rs, ur, tmp_path)
    no_strip = rs.derive_ng_keys(_raw(stock=_snap((285, 1407, 1122), (290, 917, 627), (922, 1402, 480))))
    art = shared.probe_negative(args, g, env, runner=StubRunner(rs, ur, no_strip))
    assert art["harness_exit"] == 0 and art["failing_keys"] == [] and art["outcome"] is False
    assert any("did not fail" in r for r in art["outcome_reasons"])
    flat = shared.derive_outcome_fields({"g": dict(art, error=None)}, {"g": g})["flat"]
    assert flat["measurement_valid"] is True and flat["g_negative_passed"] is False, "g_not_detected, not invalid"


def test_probe_negative_control_an_absent_key_is_not_a_failing_key_and_so_not_a_detection(rs, ur, drv, tmp_path):
    """A scenario that never produced the key (it is MISSING, not failing) must not read as 'the predicate failed'."""
    shared, g, env, args = _bed(drv, rs, ur, tmp_path)
    fields = {k: v for k, v in _detect_fields(rs).items() if k != rs.NG_KEY}
    art = shared.probe_negative(args, g, env, runner=StubRunner(rs, ur, fields))
    assert art["harness_exit"] == 1 and art["missing_keys"] == [rs.NG_KEY] and art["failing_keys"] == []
    assert art["outcome"] is False and any("not among the failing keys" in r for r in art["outcome_reasons"])


def test_probe_negative_control_a_control_that_cannot_pass_invalidates_the_measurement_even_when_the_key_fails(rs, ur, drv, tmp_path):
    shared, g, env, args = _bed(drv, rs, ur, tmp_path)
    art = shared.probe_negative(args, g, env, runner=StubRunner(rs, ur, _detect_fields(rs, control_sized_passes=False)))
    assert art["failing_keys"] == [rs.NG_KEY] and art["result_checks"] == {"control_sized_passes": False}
    flat = shared.derive_outcome_fields({"g": dict(art, error=None)}, {"g": g})["flat"]
    assert flat["measurement_valid"] is False, "a predicate that cannot pass proves nothing"
    absent = dict(_detect_fields(rs))
    del absent["control_sized_passes"]
    art2 = shared.probe_negative(args, g, env, runner=StubRunner(rs, ur, absent))
    assert art2["result_checks"] == {"control_sized_passes": False}


def test_probe_negative_control_a_scenario_that_raised_or_timed_out_is_never_a_detection(rs, ur, drv, tmp_path):
    shared, g, env, args = _bed(drv, rs, ur, tmp_path)
    raised = shared.probe_negative(args, g, env, runner=StubRunner(rs, ur, raises=True))
    assert raised["harness_error"] is not None and raised["outcome"] is False
    flat = shared.derive_outcome_fields({"g": dict(raised, error=None)}, {"g": g})["flat"]
    assert flat["measurement_valid"] is False
    hung = shared.probe_negative(args, g, env, runner=StubRunner(rs, ur, hang=True))
    assert hung["harness_exit"] == 124 and hung["outcome"] is False and hung["harness_stamp_valid"] is False
    assert shared.derive_outcome_fields({"g": dict(hung, error=None)}, {"g": g})["flat"]["measurement_valid"] is False


# --------------------------------------------------------------------------- #
# The pre-registration agrees with the code
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def sidecar():
    return tomllib.loads(SIDECAR_PATH.read_text())


def test_the_sidecar_exists_beside_the_entry_script_and_names_the_three_outcomes_in_order(sidecar):
    assert SIDECAR_PATH.is_file() and SIDECAR_PATH.with_suffix("").with_suffix(".py") == ENTRY_PATH or SIDECAR_PATH.name == ENTRY_PATH.stem + ".bth.toml"
    assert list(sidecar["outcomes"]) == ["invalid", "g_detected", "g_not_detected"], "first match wins: invalid first"
    assert sidecar["outcomes"]["invalid"]["is_residual"] is True
    assert sidecar["outcomes"]["g_detected"]["is_residual"] is False and sidecar["outcomes"]["g_not_detected"]["is_residual"] is False


def test_every_field_the_sidecar_conditions_read_is_a_field_the_driver_writes(sidecar, drv, rs, ur, tmp_path):
    shared, g, env, args = _bed(drv, rs, ur, tmp_path)
    art = shared.probe_negative(args, g, env, runner=StubRunner(rs, ur, _detect_fields(rs)))
    flat = shared.derive_outcome_fields({"g": dict(art, error=None)}, {"g": g})["flat"]
    used = set()
    for outcome in sidecar["outcomes"].values():
        used |= set(re.findall(r"[a-z_]+(?= (?:=|!=|>|<))", outcome["condition"]))
    assert used and used <= set(flat), sorted(used - set(flat))
    assert set(sidecar["result_schema"]) <= set(flat), sorted(set(sidecar["result_schema"]) - set(flat))


def _holds(condition: str, flat: dict) -> bool:
    """Evaluate a condition of the form `a = true AND b = false` over the flat fields (the only form the sidecar uses)."""
    for clause in condition.split(" AND "):
        name, _, want = clause.partition(" = ")
        if flat.get(name.strip()) is not (want.strip() == "true"):
            return False
    return True


def _first_match(sidecar, flat):
    for name, outcome in sidecar["outcomes"].items():
        if _holds(outcome["condition"], flat):
            return name
    return None


def test_the_preregistered_outcomes_pick_the_right_label_for_each_stub_result(sidecar, drv, rs, ur, tmp_path):
    shared, g, env, args = _bed(drv, rs, ur, tmp_path)

    def label(runner):
        art = shared.probe_negative(args, g, env, runner=runner)
        return _first_match(sidecar, shared.derive_outcome_fields({"g": dict(art, error=None)}, {"g": g})["flat"])

    assert label(StubRunner(rs, ur, _detect_fields(rs))) == "g_detected"
    no_strip = rs.derive_ng_keys(_raw(stock=_snap((285, 1407, 1122), (290, 917, 627), (922, 1402, 480))))
    assert label(StubRunner(rs, ur, no_strip)) == "g_not_detected"
    assert label(StubRunner(rs, ur, _detect_fields(rs, control_sized_passes=False))) == "invalid"
    assert label(StubRunner(rs, ur, raises=True)) == "invalid"
    assert label(StubRunner(rs, ur, hang=True)) == "invalid"


def test_the_sidecar_timeouts_are_the_ones_the_driver_computes(sidecar, drv):
    shared = drv.load_shared()
    g = shared.NEGATIVES["g"]
    assert sidecar["design"]["timeouts"]["harness_unit_s"]["g"] == shared.harness_budget_s(g) == 360
    assert sidecar["design"]["timeouts"]["negative_unit_s"]["g"] == shared.unit_budget_s(g) == 600
    assert sidecar["design"]["timeouts"]["driver_kill_s"]["g"] == shared.unit_budget_s(g) + shared.DRIVER_EXTRA_S == 660
    unit = sidecar["design"]["units"]["g"]
    assert (unit["harness_unit"], unit["expected_key"], unit["timeout_s"]) == ("N-g", "reclaim_ok_stock_capped_1440", 600)


def test_the_sidecar_states_that_the_recorded_numbers_came_from_a_run_without_one():
    text = SIDECAR_PATH.read_text()
    assert "NO sidecar" in text and "exploratory" in text and "re-measures" in text
