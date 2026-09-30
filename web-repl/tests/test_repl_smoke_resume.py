"""AC-42 for the display units: the preemption-safe harness in ``scripts/repl_smoke.py`` (A7).

Epic 260929_notebook-display-design, D16 "Preemption-safe harness design" (Revisions 7-11) and
AC-42. This file loads ``scripts/repl_smoke.py`` BY PATH (import-safe without the PyLabRobot
submodule since A1, Revision 11 C11-3) and tests its PURE FUNCTIONS directly: the unit table
with listed keys and budgets, input hashing, stamp validation and the skip rule, the aggregate
(``reused`` / ``recomputed`` / ``timed_out`` / ``missing`` / ``stale``), the ``--out-dir``
rule, ``--fresh``, ``--aggregate-only`` (never deletes, starts no unit subprocess), and
``run_scenario``'s ordering with injected browser, runner and watchdog seams.

No browser is launched and nothing here measures the product. The fake "unit runner" is the
REAL ``run_scenario`` called in-process with fake sessions and scenarios, so the result and
stamp writers under test are the production ones. Only the ``--scenario`` watchdog cases run
a short-lived child process, started through the real ``unit_runner.run_unit`` (real
``Watchdog``, real ``kill_tree``); their budgets are shrunk through ``run_scenario``'s
``budget_s`` parameter (never a CLI flag: budgets are pre-registered).

The CLI-behaviour cases (the exit-2 ``--out-dir`` rule, ``--aggregate-only``) call
``run_display_check`` (the function behind the flags) with a runner spy and assert the return
code and effects (C11-10).
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import importlib.util
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REPL_SMOKE = REPO_ROOT / "scripts" / "repl_smoke.py"
UNIT_RUNNER = REPO_ROOT / "scripts" / "unit_runner.py"

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
    return _load(REPL_SMOKE, "repl_smoke_resume_under_test")


@pytest.fixture(scope="module")
def ur() -> Any:
    return _load(UNIT_RUNNER, "unit_runner_resume_under_test")


# --------------------------------------------------------------------------- #
# Helpers: a fake hashed environment, fake sessions, spies, an in-process unit runner
# --------------------------------------------------------------------------- #


def make_env(rs: Any, **over: Any) -> Any:
    fields: dict[str, Any] = dict(
        dist="d" * 64, notebook="n" * 64, harness="h" * 64, runner="r" * 64, chrome="c" * 64,
        driver="v" * 64, base_path="/praxis/", chrome_path="/fake/chrome", chrome_version="Fake 1.0",
    )
    fields.update(over)
    return rs.HashEnv(**fields)


class FakeSession:
    """Stands in for the real browser session: ``pageerrors`` and ``close()`` only."""

    def __init__(self, log: list[Any] | None = None, on_close: Callable[[], None] | None = None) -> None:
        self.pageerrors: list[str] = []
        self.log = log if log is not None else []
        self.on_close = on_close

    def close(self) -> None:
        self.log.append("close")
        if self.on_close:
            self.on_close()


class Watchdogs:
    """A watchdog factory spy: real ``unit_runner.Watchdog`` with injected exit/kill seams."""

    def __init__(self, ur: Any, log: list[Any], files: dict[str, Path] | None = None) -> None:
        self.ur, self.log, self.files, self.made = ur, log, files or {}, []

    def __call__(self, budget_s: float, on_expire: Any) -> Any:
        self.log.append(("arm", budget_s, {k: p.exists() for k, p in self.files.items()}))
        wd = self.ur.Watchdog(
            budget_s, on_expire, token="tok",
            exit_fn=lambda code: self.log.append(("watchdog_exit", code)),
            kill_fn=lambda *a, **k: self.log.append("watchdog_kill"),
        )
        self.made.append(wd)
        return wd

    def disarm_all(self) -> None:
        for wd in self.made:
            wd.disarm()


@pytest.fixture()
def wds(ur):
    made: list[Watchdogs] = []

    def make(log: list[Any], files: dict[str, Path] | None = None) -> Watchdogs:
        w = Watchdogs(ur, log, files)
        made.append(w)
        return w

    yield make
    for w in made:
        w.disarm_all()


#: The unit table through sprint B (D16 order): B10 appends D2, D3 and D4.
ALL_IDS = ["D1", "D1-dark", "D2", "D3", "D4"]
#: The D16 budgets in minutes, in table order.
BUDGET_MIN = [6, 5, 12, 8, 6]


def passing_fields(unit: Any) -> dict[str, Any]:
    """A result that holds every listed key (a predicate such as ``AtMost`` gives its ``example()``)."""
    return {k: (v.example() if hasattr(v, "example") else v) for k, v in unit.expected}


def scenario_in_process(rs: Any, ur: Any, wds: Any, unit_id: str, out_dir: Path, env: Any, *,
                        fields: dict[str, Any] | None = None, log: list[Any] | None = None,
                        scenario_fn: Callable[..., dict[str, Any]] | None = None,
                        session: Any = None, **kw: Any) -> int:
    """Run the REAL ``run_scenario`` in this process with every seam faked; returns the exit code
    it would hand to ``os._exit``."""
    log = log if log is not None else []
    unit = rs.UNIT_BY_ID[unit_id]
    files = rs.unit_paths(out_dir, unit_id)

    def default_scenario(sess: Any, u: Any, e: Any) -> dict[str, Any]:
        log.append("scenario")
        return dict(fields if fields is not None else passing_fields(u))

    return rs.run_scenario(
        unit_id, out_dir=out_dir, env_fn=lambda: env,
        session_factory=lambda u, e: session or FakeSession(log),
        scenario_fn=scenario_fn or default_scenario,
        ensure_token_fn=lambda: "tok", watchdog_factory=wds(log, files),
        kill_tree_fn=lambda *a, **k: log.append("kill_tree") or [],
        exit_fn=lambda code: code, **kw,
    )


class InProcessRunner:
    """A fake ``unit_runner``: ``run_unit(argv, timeout_s)`` runs the unit in this process via the
    real ``run_scenario``; every call is recorded (argv, timeout, cwd)."""

    def __init__(self, rs: Any, ur: Any, wds: Any, out_dir: Path, env: Any, *,
                 fields: dict[str, dict[str, Any]] | None = None, timed_out: set[str] | None = None,
                 skip_stamp: set[str] | None = None) -> None:
        self.rs, self.ur, self.wds, self.out, self.env = rs, ur, wds, out_dir, env
        self.fields = fields or {}
        self.timed_out = timed_out or set()
        self.skip_stamp = skip_stamp or set()
        self.calls: list[tuple[list[str], float, Any]] = []

    def run_unit(self, argv: Any, timeout_s: float, *, env: Any = None, cwd: Any = None, grace_s: float = 5.0) -> Any:
        argv = list(argv)
        self.calls.append((argv, timeout_s, cwd))
        uid = argv[argv.index("--scenario") + 1] if "--scenario" in argv else argv[1]
        unit = self.rs.UNIT_BY_ID[uid]
        if uid in self.skip_stamp:  # "killed between the result and the stamp": result only
            paths = self.rs.unit_paths(self.out, uid)
            paths["result"].parent.mkdir(parents=True, exist_ok=True)
            paths["result"].write_text(json.dumps(passing_fields(unit)))
            return self.ur.UnitOutcome(-9, False, False)
        code = scenario_in_process(
            self.rs, self.ur, self.wds, uid, self.out, self.env,
            fields=self.fields.get(uid, passing_fields(unit)),
        )
        if uid in self.timed_out:
            return self.ur.UnitOutcome(-9, True, True)
        return self.ur.UnitOutcome(code, False, False)

    def ids(self) -> list[str]:
        return [a[a.index("--scenario") + 1] if "--scenario" in a else a[1] for a, _, _ in self.calls]


class SpyRunner:
    """A runner that must never be called (``--aggregate-only``, ``--out-dir`` rule)."""

    def __init__(self) -> None:
        self.calls: list[Any] = []

    def run_unit(self, *a: Any, **k: Any) -> Any:
        self.calls.append((a, k))
        raise AssertionError("no unit subprocess may be started here")


def drive(rs: Any, out_dir: Path, env: Any, runner: Any, **kw: Any) -> tuple[dict[str, Any], int]:
    return rs.run_units_driver(
        table=[u for u in rs.UNIT_TABLE if u.check == rs.DISPLAY_CHECK], out_dir=out_dir,
        inputs_for=lambda u: rs.unit_inputs(u, env),
        argv_for=lambda u: ["fake-unit", "--scenario", u.id], runner=runner, cwd="/repo", **kw,
    )


def snapshot_files(out_dir: Path) -> dict[str, bytes]:
    return {str(p.relative_to(out_dir)): p.read_bytes() for p in sorted(out_dir.rglob("*")) if p.is_file()}


# --------------------------------------------------------------------------- #
# The unit table equals D16's (ids, check, budget, listed keys) -- sprint A
# --------------------------------------------------------------------------- #

D1_KEYS = (
    "rail_state_never_run", "rail_state_after_run", "rail_state_while_sleep",
    "rail_state_after_raise", "rail_state_after_edit", "rail_colors_match",
    "prompts_take_no_space", "light_ground", "light_sheet", "exec_count_on_rail", "pageerrors",
)
D1_DARK_KEYS = (
    "rail_state_never_run", "rail_state_after_run", "rail_state_while_sleep",
    "rail_state_after_raise", "rail_state_after_edit", "prompts_take_no_space",
    "rail_colors_match_dark",
)


def test_unit_table_is_d16_through_sprint_b_for_the_chrome_units(rs):
    assert [u.id for u in rs.UNIT_TABLE if u.check == "display-check"] == ALL_IDS
    d1, dark = rs.UNIT_BY_ID["D1"], rs.UNIT_BY_ID["D1-dark"]
    assert (d1.check, d1.budget_s) == ("display-check", 6 * 60)
    assert (dark.check, dark.budget_s) == ("display-check", 5 * 60)
    assert tuple(d1.keys) == D1_KEYS and tuple(dark.keys) == D1_DARK_KEYS


def test_listed_keys_carry_the_ac7_expected_values(rs):
    d1 = dict(rs.UNIT_BY_ID["D1"].expected)
    assert d1["rail_state_never_run"] == "not-run" and d1["rail_state_after_run"] == "ran"
    assert d1["rail_state_while_sleep"] == "running" and d1["rail_state_after_raise"] == "error"
    assert d1["rail_state_after_edit"] == "stale"
    assert d1["light_ground"] == "rgb(238, 241, 244)" and d1["light_sheet"] == "rgb(255, 255, 255)"
    assert d1["rail_colors_match"] is True and d1["prompts_take_no_space"] is True
    assert d1["exec_count_on_rail"] is True and d1["pageerrors"] == []
    dark = dict(rs.UNIT_BY_ID["D1-dark"].expected)
    assert dark["rail_colors_match_dark"] is True and "rail_colors_match" not in dark
    assert all(k in dark for k in D1_DARK_KEYS)


def test_expected_holds_is_strict_about_booleans_and_lists(rs):
    unit = rs.UNIT_BY_ID["D1"]
    ok = passing_fields(unit)
    assert rs.evaluate_unit_result(unit, ok) == ([], [])
    for key, bad in (("prompts_take_no_space", 1), ("prompts_take_no_space", "true"),
                     ("pageerrors", ["boom"]), ("light_ground", "rgb(255, 255, 255)"),
                     ("rail_state_after_run", "not-run")):
        fields = dict(ok, **{key: bad})
        assert rs.evaluate_unit_result(unit, fields) == ([], [key]), (key, bad)


def test_evaluate_reports_missing_and_failing_keys_separately(rs):
    unit = rs.UNIT_BY_ID["D1"]
    fields = passing_fields(unit)
    del fields["light_sheet"]
    fields["rail_state_after_run"] = "not-run"
    assert rs.evaluate_unit_result(unit, fields) == (["light_sheet"], ["rail_state_after_run"])
    assert rs.evaluate_unit_result(unit, None)[0] == list(unit.keys)


def test_unit_files_layout(rs, tmp_path):
    p = rs.unit_paths(tmp_path, "D1-dark")
    assert p["result"] == tmp_path / "result.D1-dark.json"
    assert p["stamp"] == tmp_path / "result.D1-dark.stamp.json"
    assert p["timeout"] == tmp_path / "result.D1-dark.timeout.json"


def test_default_out_dir_is_gitignored_outputs(rs):
    d = rs.default_out_dir("display-check")
    assert d == REPO_ROOT / "outputs" / "repl_smoke" / "display-check"


# --------------------------------------------------------------------------- #
# Inputs hashed: dist, notebook, harness, runner, chrome, args, driver
# --------------------------------------------------------------------------- #

INPUT_NAMES = {"dist", "notebook", "harness", "runner", "chrome", "args", "driver"}


def test_unit_inputs_are_exactly_the_seven_d16_inputs(rs):
    inputs = rs.unit_inputs(rs.UNIT_BY_ID["D1"], make_env(rs))
    assert set(inputs) == INPUT_NAMES
    assert all(len(v) == 64 for v in inputs.values())
    assert inputs["dist"] == "d" * 64 and inputs["driver"] == "v" * 64 and inputs["runner"] == "r" * 64


@pytest.mark.parametrize("field", ["dist", "notebook", "harness", "runner", "chrome", "driver"])
def test_each_env_field_changes_only_its_own_input(rs, field):
    unit = rs.UNIT_BY_ID["D1"]
    a = rs.unit_inputs(unit, make_env(rs))
    b = rs.unit_inputs(unit, make_env(rs, **{field: "0" * 64}))
    assert [k for k in a if a[k] != b[k]] == [field]


def test_args_input_covers_unit_base_path_viewport_and_neg(rs):
    env = make_env(rs)
    d1, dark = rs.UNIT_BY_ID["D1"], rs.UNIT_BY_ID["D1-dark"]
    base = rs.unit_inputs(d1, env)["args"]
    assert rs.unit_inputs(dark, env)["args"] != base, "the unit id is in the args hash"
    assert rs.unit_inputs(d1, make_env(rs, base_path="/"))["args"] != base
    assert rs.unit_inputs(d1, env, neg=("drop-query",))["args"] != base, "a harness-only negative flag is hashed"
    wide = dataclasses.replace(d1, viewports=((1600, 900),))
    assert rs.unit_inputs(wide, env)["args"] != base, "the viewport list is hashed"
    # inputs do not depend on anything else about the unit
    assert rs.unit_inputs(d1, env) == rs.unit_inputs(d1, make_env(rs))


def test_driver_input_change_reaches_the_unit_inputs(rs, ur):
    """Playwright upgrade or lockfile change => a different ``driver`` input => recompute (C8-6)."""
    unit = rs.UNIT_BY_ID["D1"]
    d0 = ur.driver_input(playwright_version="1.62.0", uv_lock_bytes=b"lock-a")
    d1 = ur.driver_input(playwright_version="1.63.0", uv_lock_bytes=b"lock-a")
    d2 = ur.driver_input(playwright_version="1.62.0", uv_lock_bytes=b"lock-b")
    assert len({d0, d1, d2}) == 3
    base = rs.unit_inputs(unit, make_env(rs, driver=d0))
    for other in (d1, d2):
        changed = rs.unit_inputs(unit, make_env(rs, driver=other))
        assert [k for k in base if base[k] != changed[k]] == ["driver"]


def test_build_hash_env_hashes_real_files_and_injected_probes(rs, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "a.txt").write_text("a")
    notebook = tmp_path / "nb.ipynb"
    notebook.write_text("{}")
    harness = tmp_path / "harness.py"
    harness.write_text("# harness")
    runner = tmp_path / "runner.py"
    runner.write_text("# runner")
    args = rs.parse_args(["--display-check", "--serve-dir", str(dist), "--base-path", "praxis"])
    env = rs.build_hash_env(
        args, "/fake/chrome", notebook_path=notebook, harness_path=harness, runner_path=runner,
        driver_fn=lambda: "v" * 64, chrome_version_fn=lambda p: "Fake 9",
    )
    sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
    assert env.notebook == sha(b"{}") and env.harness == sha(b"# harness") and env.runner == sha(b"# runner")
    assert env.chrome == sha(b"/fake/chrome\nFake 9") and env.driver == "v" * 64
    assert env.base_path == "/praxis/", "the normalised base path is what is hashed"
    assert env.dist == hashlib.sha256(f"a.txt\t{sha(b'a')}\n".encode()).hexdigest()


def test_build_hash_env_raises_on_a_missing_dist(rs, tmp_path):
    args = rs.parse_args(["--display-check", "--serve-dir", str(tmp_path / "nope")])
    with pytest.raises(FileNotFoundError):
        rs.build_hash_env(args, "/fake/chrome", driver_fn=lambda: "v" * 64, chrome_version_fn=lambda p: "x")


# --------------------------------------------------------------------------- #
# The --out-dir rule, flag validation, CLI surface
# --------------------------------------------------------------------------- #


def test_out_dir_rule_is_a_pure_function_of_the_arguments(rs, tmp_path):
    other = tmp_path / "copy"
    other.mkdir()
    default = rs.parse_args(["--display-check"])
    assert rs.out_dir_rule_error(default) is None
    assert rs.out_dir_rule_error(rs.parse_args(["--display-check", "--serve-dir", str(other)])) is not None
    assert rs.out_dir_rule_error(rs.parse_args(["--display-check", "--neg", "drop-query"])) is not None
    ok = ["--out-dir", str(tmp_path / "out")]
    assert rs.out_dir_rule_error(rs.parse_args(["--display-check", "--serve-dir", str(other), *ok])) is None
    assert rs.out_dir_rule_error(rs.parse_args(["--display-check", "--neg", "drop-query", *ok])) is None
    # the default serve dir spelled out is still the default (resolved comparison)
    assert rs.out_dir_rule_error(
        rs.parse_args(["--display-check", "--serve-dir", str(rs.DEFAULT_SERVE_DIR)])
    ) is None


@pytest.mark.parametrize(
    "argv",
    [["--serve-dir", "{tmp}"], ["--neg", "drop-query"], ["--serve-dir", "{tmp}", "--scenario", "D1"]],
)
def test_run_display_check_exits_2_before_launching_anything_without_out_dir(rs, tmp_path, argv):
    spy = SpyRunner()
    args = rs.parse_args(["--display-check", *[a.format(tmp=tmp_path) for a in argv]])
    assert rs.run_display_check(args, runner=spy, hash_env=make_env(rs)) == 2
    assert spy.calls == []


def test_conflicting_flags_exit_2(rs, tmp_path):
    out = ["--out-dir", str(tmp_path / "o")]
    for extra in (["--aggregate-only", "--fresh"], ["--aggregate-only", "--scenario", "D1"]):
        args = rs.parse_args(["--display-check", *out, *extra])
        assert rs.run_display_check(args, runner=SpyRunner(), hash_env=make_env(rs)) == 2, extra


def test_unknown_scenario_id_exits_2(rs, tmp_path):
    args = rs.parse_args(["--display-check", "--scenario", "K1a", "--out-dir", str(tmp_path / "o")])
    assert rs.run_display_check(args, runner=SpyRunner(), hash_env=make_env(rs)) == 2


def test_scenario_flag_runs_exactly_that_unit(rs, tmp_path):
    seen: list[Any] = []
    args = rs.parse_args(["--display-check", "--scenario", "D1-dark", "--out-dir", str(tmp_path / "o")])
    rc = rs.run_display_check(
        args, runner=SpyRunner(), hash_env=make_env(rs),
        scenario_entry=lambda unit_id, **kw: seen.append(unit_id) or 0,
    )
    assert rc == 0 and seen == ["D1-dark"]


def test_cli_flags_exist_and_default_correctly(rs):
    args = rs.parse_args(["--display-check"])
    assert args.display_check is True and args.scenario is None and args.fresh is False
    assert args.aggregate_only is False and args.out_dir is None and args.neg == []
    args = rs.parse_args(["--display-check", "--scenario", "D1", "--out-dir", "x", "--fresh"])
    assert (args.scenario, str(args.out_dir), args.fresh) == ("D1", "x", True)


def test_main_routes_display_check_and_lists_it_as_something_to_do(rs, monkeypatch):
    calls: list[Any] = []
    monkeypatch.setattr(rs, "run_display_check", lambda args, **kw: calls.append(args) or 7)
    assert rs.main(["--display-check"]) == 7 and len(calls) == 1
    assert rs.main([]) == 2, "no check flag is still 'nothing to do'"


# --------------------------------------------------------------------------- #
# The persistence-ack context init script (D16 "Persistence gate")
# --------------------------------------------------------------------------- #


def test_persistence_ack_init_script_sets_the_existing_key_to_browser_only(rs):
    script = rs.PERSISTENCE_ACK_INIT_SCRIPT
    assert 'localStorage.setItem("praxis-repl-persistence-ack", "browser-only")' in script
    assert script in rs.display_context_init_scripts(), "every display context carries the ack"
    assert script in rs.display_context_init_scripts(neg=("drop-query",))


# --------------------------------------------------------------------------- #
# run_scenario: order of acts, with injected browser, runner and watchdog seams
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("unit_id", ALL_IDS)
def test_watchdog_armed_once_with_the_table_budget_before_deletion_and_browser(rs, ur, wds, tmp_path, unit_id):
    """C9-4: ensure_token, then the Watchdog at the unit's D16 budget as the FIRST act, before the
    first file deletion and before the fake browser launch."""
    env = make_env(rs)
    log: list[Any] = []
    files = rs.unit_paths(tmp_path, unit_id)
    for p in files.values():  # stale leftovers of an earlier run
        p.write_text("{}")
    launches: list[dict[str, bool]] = []

    def factory(u: Any, e: Any) -> Any:
        log.append("session")
        launches.append({k: p.exists() for k, p in files.items()})
        return FakeSession(log)

    def ensure() -> str:
        log.append("token")
        return "tok"

    unit = rs.UNIT_BY_ID[unit_id]
    rs.run_scenario(
        unit_id, out_dir=tmp_path, env_fn=lambda: log.append("env") or env, session_factory=factory,
        scenario_fn=lambda s, u, e: log.append("scenario") or passing_fields(u),
        ensure_token_fn=ensure, watchdog_factory=wds(log, files),
        kill_tree_fn=lambda *a, **k: [], exit_fn=lambda c: c,
    )
    arms = [e for e in log if isinstance(e, tuple) and e[0] == "arm"]
    assert len(arms) == 1 and arms[0][1] == unit.budget_s
    assert all(arms[0][2].values()), "the stale files still existed when the watchdog was armed"
    assert launches == [{"result": False, "stamp": False, "timeout": False}], "cleared before the browser"
    assert log.index("token") < log.index(arms[0]) < log.index("env") < log.index("session") < log.index("scenario")


def test_result_is_written_before_teardown_and_the_stamp_after_it(rs, ur, wds, tmp_path):
    env = make_env(rs)
    files = rs.unit_paths(tmp_path, "D1")
    seen: dict[str, Any] = {}
    log: list[Any] = []

    def on_close() -> None:
        seen["close"] = (files["result"].exists(), files["stamp"].exists())

    def kill(*a: Any, **k: Any) -> list[int]:
        seen["kill"] = (files["result"].exists(), files["stamp"].exists())
        seen["kill_args"] = a
        return []

    def exit_fn(code: int) -> int:
        seen["exit"] = (code, files["result"].exists(), files["stamp"].exists())
        return code

    code = rs.run_scenario(
        "D1", out_dir=tmp_path, env_fn=lambda: env,
        session_factory=lambda u, e: FakeSession(log, on_close),
        scenario_fn=lambda s, u, e: passing_fields(u), ensure_token_fn=lambda: "tok",
        watchdog_factory=wds(log, files), kill_tree_fn=kill, exit_fn=exit_fn,
    )
    assert code == 0
    assert seen["close"] == (True, False), "result before the browser closes, stamp not yet"
    assert seen["kill"] == (True, False) and seen["kill_args"][1] == "tok" and seen["kill_args"][0] == os.getpid()
    assert seen["exit"] == (0, True, True), "only exit follows the stamp"


def test_stamp_and_result_shape(rs, ur, wds, tmp_path):
    env = make_env(rs)
    code = scenario_in_process(rs, ur, wds, "D1-dark", tmp_path, env)
    files = rs.unit_paths(tmp_path, "D1-dark")
    result = json.loads(files["result"].read_text())
    stamp = json.loads(files["stamp"].read_text())
    unit = rs.UNIT_BY_ID["D1-dark"]
    assert code == 0 and stamp["exit"] == 0
    assert set(stamp) == {"unit", "inputs", "result_sha256", "started", "finished", "exit", "budget_s"}
    assert stamp["unit"] == "D1-dark" and stamp["budget_s"] == unit.budget_s
    assert stamp["inputs"] == rs.unit_inputs(unit, env)
    assert stamp["result_sha256"] == hashlib.sha256(files["result"].read_bytes()).hexdigest()
    assert result["unit"] == "D1-dark" and result["chrome_path"] == "/fake/chrome"
    assert result["pageerrors"] == [] and result["failing_keys"] == [] and result["error"] is None
    assert all(k in result for k in unit.keys)


def test_a_failing_key_gives_stamp_exit_1_and_names_the_key(rs, ur, wds, tmp_path):
    unit = rs.UNIT_BY_ID["D1"]
    fields = passing_fields(unit)
    fields["rail_state_after_run"] = "not-run"
    code = scenario_in_process(rs, ur, wds, "D1", tmp_path, make_env(rs), fields=fields)
    files = rs.unit_paths(tmp_path, "D1")
    assert code == 1 and json.loads(files["stamp"].read_text())["exit"] == 1
    assert json.loads(files["result"].read_text())["failing_keys"] == ["rail_state_after_run"]


def test_a_missing_key_gives_stamp_exit_1(rs, ur, wds, tmp_path):
    fields = passing_fields(rs.UNIT_BY_ID["D1"])
    del fields["exec_count_on_rail"]
    code = scenario_in_process(rs, ur, wds, "D1", tmp_path, make_env(rs), fields=fields)
    assert code == 1
    assert json.loads(rs.unit_paths(tmp_path, "D1")["result"].read_text())["missing_keys"] == ["exec_count_on_rail"]


def test_a_raising_scenario_is_a_complete_unit_with_an_error_finding(rs, ur, wds, tmp_path):
    def boom(s: Any, u: Any, e: Any) -> dict[str, Any]:
        raise ValueError("the probe broke")

    log: list[Any] = []
    code = scenario_in_process(rs, ur, wds, "D1", tmp_path, make_env(rs), scenario_fn=boom, log=log)
    files = rs.unit_paths(tmp_path, "D1")
    result = json.loads(files["result"].read_text())
    assert code == 1 and files["stamp"].exists(), "an error finding is a complete unit"
    assert result["error"]["type"] == "ValueError" and "the probe broke" in result["error"]["message"]
    assert len(result["error"]["traceback_tail"].encode()) <= 4096
    assert "close" in log, "the session is still closed after a raised scenario"


def test_pageerrors_come_from_the_session(rs, ur, wds, tmp_path):
    sess = FakeSession()
    sess.pageerrors.append("Uncaught boom")
    code = scenario_in_process(rs, ur, wds, "D1", tmp_path, make_env(rs), session=sess)
    result = json.loads(rs.unit_paths(tmp_path, "D1")["result"].read_text())
    assert code == 1 and result["pageerrors"] == ["Uncaught boom"] and result["failing_keys"] == ["pageerrors"]


class PwError:
    """Stands in for Playwright's ``Error`` (the ``pageerror`` payload): ``str()`` is the message,
    ``stack`` is the JavaScript stack or None."""

    def __init__(self, message: str, stack: str | None) -> None:
        self.message = message
        self.stack = stack

    def __str__(self) -> str:
        return self.message


def test_pageerror_entry_carries_the_message_and_a_truncated_stack(rs):
    """The recorded entry stays ONE string (the ``pageerrors`` key is still a list of them) and
    now says where the error was thrown. Stack truncated to 600 characters."""
    msg = "Failed to execute 'removeChild' on 'Node'"
    stack = "Error: boom\n    at frame0 (http://x/a.js:1:1)\n" + "x" * 700 + "TAIL"
    entry = rs.format_pageerror(PwError(msg, stack))
    assert isinstance(entry, str)
    assert entry == f"{msg}\n{stack[:600]}"
    assert "TAIL" not in entry, "negative control: the stack beyond 600 characters is cut"
    assert "at frame0" in entry


@pytest.mark.parametrize("stack", [None, ""])
def test_pageerror_entry_without_a_stack_is_just_the_message(rs, stack):
    assert rs.format_pageerror(PwError("Uncaught boom", stack)) == "Uncaught boom"
    assert rs.format_pageerror(ValueError("plain exception, no stack attribute")) == "plain exception, no stack attribute"


def test_display_session_records_pageerrors_through_format_pageerror(rs):
    """The listener is built inside a browser-only constructor, so this reads its source."""
    import inspect

    init_src = inspect.getsource(rs.DisplaySession.__init__)
    listener = [line for line in init_src.splitlines() if '"pageerror"' in line]
    assert len(listener) == 1, listener
    assert "format_pageerror" in listener[0] and "str(exc)" not in listener[0], listener[0]


# --- the theme-change readiness gate (D1 ran apputils:change-theme before it was registered) ---

_THEME_CONDITIONS = {
    "command registered": r"hasCommand\(\s*['\"]apputils:change-theme['\"]\s*\)",
    "app restored": r"__praxisRestored\s*===\s*true",
    "splash gone": r"!\s*document\.getElementById\(\s*['\"]jupyterlab-splash['\"]\s*\)",
}


def _missing_theme_conditions(js: str) -> list[str]:
    """Which of the three readiness conditions the JS does not contain (the checker under test)."""
    import re

    return [name for name, pattern in _THEME_CONDITIONS.items() if not re.search(pattern, js)]


def _without(js: str, condition: str) -> str:
    """A copy of ``js`` that lacks exactly one condition (its pattern's match is blanked out)."""
    import re

    pattern = _THEME_CONDITIONS[condition]
    assert re.search(pattern, js), f"cannot build a negative control: {condition!r} not in the JS"
    return re.sub(pattern, "true", js)


def _unguarded_theme_calls(source: str) -> list[int]:
    """Line numbers of calls taking ``_DC_THEME_JS`` with no earlier ``wait_for_theme_ready(...)``
    call in the same function."""
    tree = ast.parse(source)
    bad = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
        gates = [
            c.lineno for c in calls
            if (isinstance(c.func, ast.Name) and c.func.id == "wait_for_theme_ready")
            or (isinstance(c.func, ast.Attribute) and c.func.attr == "wait_for_theme_ready")
        ]
        for c in calls:
            if any(isinstance(a, ast.Name) and a.id == "_DC_THEME_JS" for a in c.args):
                if not any(g < c.lineno for g in gates):
                    bad.append(c.lineno)
    return bad


def test_theme_ready_js_names_all_three_conditions_and_the_checker_catches_each_omission(rs):
    assert _missing_theme_conditions(rs.THEME_READY_JS) == []
    assert "restored.then(" in rs.THEME_READY_JS, "the restored flag must be armed from jupyterapp.restored"
    for condition in _THEME_CONDITIONS:
        assert _missing_theme_conditions(_without(rs.THEME_READY_JS, condition)) == [condition], condition


def test_theme_ready_js_behaves_in_a_stub_page(rs):
    """Runs the predicate under bun against a fake ``window``/``document``. The three conditions
    come true one at a time, in every order; the JS must be not ready until the third. A copy
    missing one condition is ready too early in the order where that condition comes last
    (negative control per condition)."""
    bun = shutil.which("bun")
    if not bun:
        pytest.skip("bun not installed")
    driver = textwrap.dedent(
        """
        const pred = (0, eval)('(' + JS + ')');
        let resolveRestored; const restored = new Promise(r => { resolveRestored = r; });
        const cmds = new Set(); let splash = true;
        globalThis.window = {jupyterapp: {commands: {hasCommand: n => cmds.has(n)}, restored}};
        globalThis.document = {getElementById: id => (id === 'jupyterlab-splash' && splash ? {} : null)};
        pred();  // the page polls; the first call arms the restored flag
        const out = [];
        for (const ev of ORDER) {
          if (ev === 'command') cmds.add('apputils:change-theme');
          if (ev === 'restored') { resolveRestored(); await restored; await new Promise(r => setTimeout(r, 0)); }
          if (ev === 'splash') splash = false;
          out.push(!!pred());
        }
        console.log(JSON.stringify(out));
        """
    )

    def steps(js: str, order: list[str]) -> list[bool]:
        script = driver.replace("JS", json.dumps(js), 1).replace("ORDER", json.dumps(order))
        done = subprocess.run([bun, "--eval", script], capture_output=True, text=True, timeout=60)
        assert done.returncode == 0, done.stderr
        return json.loads(done.stdout.strip().splitlines()[-1])

    import itertools

    orders = [list(o) for o in itertools.permutations(["command", "restored", "splash"])]
    for order in orders:
        assert steps(rs.THEME_READY_JS, order) == [False, False, True], order
    for condition, last in (("command registered", "command"), ("app restored", "restored"), ("splash gone", "splash")):
        broken = _without(rs.THEME_READY_JS, condition)
        order = [e for e in ("command", "restored", "splash") if e != last] + [last]
        assert steps(broken, order) != [False, False, True], f"negative control passed: {condition}"


def test_wait_for_theme_ready_waits_on_the_js_with_the_navigation_timeout(rs):
    class StubPage:
        def __init__(self) -> None:
            self.calls: list[tuple[tuple, dict]] = []

        def wait_for_function(self, *args: Any, **kwargs: Any) -> None:
            self.calls.append((args, kwargs))

    page = StubPage()
    rs.wait_for_theme_ready(page)
    assert len(page.calls) == 1
    args, kwargs = page.calls[0]
    assert args == (rs.THEME_READY_JS,)
    assert kwargs == {"timeout": rs.DISPLAY_NAV_TIMEOUT_MS}
    rs.wait_for_theme_ready(page, timeout_ms=1234)
    assert page.calls[1][1] == {"timeout": 1234}


def test_every_theme_change_call_is_preceded_by_the_readiness_gate(rs):
    source = REPL_SMOKE.read_text(encoding="utf-8")
    assert _unguarded_theme_calls(source) == []
    # the real file has at least one call site, or the check above proves nothing (anywhere in the
    # file: the sites are the D1 scenario and, from sprint B, the dock-check session's set_theme)
    assert source.count("evaluate(_DC_THEME_JS") >= 1


def test_the_call_site_checker_fires_on_a_synthetic_unguarded_call():
    guarded = "def f(page):\n    wait_for_theme_ready(page)\n    page.evaluate(_DC_THEME_JS, 'x')\n"
    late = "def f(page):\n    page.evaluate(_DC_THEME_JS, 'x')\n    wait_for_theme_ready(page)\n"
    other_fn = "def g(page):\n    wait_for_theme_ready(page)\ndef f(page):\n    page.evaluate(_DC_THEME_JS, 'x')\n"
    missing = "def f(page):\n    page.evaluate(_DC_THEME_JS, 'x')\n"
    assert _unguarded_theme_calls(guarded) == []
    assert _unguarded_theme_calls(late) == [2]
    assert _unguarded_theme_calls(other_fn) == [4]
    assert _unguarded_theme_calls(missing) == [2]


def test_inputs_that_cannot_be_built_exit_2_with_no_stamp(rs, ur, wds, tmp_path):
    log: list[Any] = []

    def bad_env() -> Any:
        raise FileNotFoundError("dist directory not found")

    unit = rs.UNIT_BY_ID["D1"]
    code = rs.run_scenario(
        "D1", out_dir=tmp_path, env_fn=bad_env, session_factory=lambda u, e: FakeSession(log),
        scenario_fn=lambda s, u, e: passing_fields(u), ensure_token_fn=lambda: "tok",
        watchdog_factory=wds(log, rs.unit_paths(tmp_path, "D1")),
        kill_tree_fn=lambda *a, **k: [], exit_fn=lambda c: c,
    )
    assert code == 2 and not rs.unit_paths(tmp_path, "D1")["stamp"].exists()
    assert unit.id == "D1"


# --------------------------------------------------------------------------- #
# The driver: one run_unit per unit, budget + 60 s, no whole-run timeout
# --------------------------------------------------------------------------- #


def test_driver_starts_each_unit_as_its_own_run_unit_with_budget_plus_60(rs, ur, wds, tmp_path):
    env = make_env(rs)
    runner = InProcessRunner(rs, ur, wds, tmp_path, env)
    agg, code = drive(rs, tmp_path, env, runner)
    assert code == 0 and agg["passed"] is True
    assert runner.ids() == ALL_IDS, "table order, exactly one process per unit"
    assert [t for _, t, _ in runner.calls] == [m * 60 + 60 for m in BUDGET_MIN]
    assert all(c == "/repo" for _, _, c in runner.calls)
    assert len(runner.calls) == len([u for u in rs.UNIT_TABLE if u.check == rs.DISPLAY_CHECK]), "no whole-run call"


def test_aggregate_shape_and_d1_dark_subobject(rs, ur, wds, tmp_path):
    env = make_env(rs)
    agg, code = drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    assert code == 0
    for key in ("scenarios", "reused", "recomputed", "timed_out", "missing", "stale"):
        assert key in agg, key
    assert agg["recomputed"] == ALL_IDS and agg["reused"] == []
    assert agg["timed_out"] == [] and agg["missing"] == [] and agg["stale"] == []
    assert set(agg["scenarios"]) == set(ALL_IDS)
    assert agg["d1_dark"] == agg["scenarios"]["D1-dark"] and "rail_colors_match_dark" in agg["d1_dark"]
    written = json.loads((tmp_path / "result.json").read_text())
    assert written["passed"] is True and written["recomputed"] == ALL_IDS


def test_resume_reuses_verified_units_and_records_source_and_hashes(rs, ur, wds, tmp_path):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    spy = SpyRunner()
    agg, code = drive(rs, tmp_path, env, spy)
    assert code == 0 and spy.calls == [] and agg["recomputed"] == []
    assert [r["id"] for r in agg["reused"]] == ALL_IDS
    for rec in agg["reused"]:
        files = rs.unit_paths(tmp_path, rec["id"])
        assert rec["source"] == str(files["result"])
        assert rec["inputs"] == rs.unit_inputs(rs.UNIT_BY_ID[rec["id"]], env)
        assert rec["result_sha256"] == hashlib.sha256(files["result"].read_bytes()).hexdigest()


def test_fresh_ignores_every_stamp(rs, ur, wds, tmp_path):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    runner = InProcessRunner(rs, ur, wds, tmp_path, env)
    agg, code = drive(rs, tmp_path, env, runner, fresh=True)
    assert code == 0 and runner.ids() == ALL_IDS
    assert agg["reused"] == [] and agg["recomputed"] == ALL_IDS


@pytest.mark.parametrize("field", ["dist", "notebook", "harness", "runner", "chrome", "driver"])
def test_a_changed_input_recomputes_the_unit(rs, ur, wds, tmp_path, field):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    env2 = make_env(rs, **{field: "0" * 64})
    runner = InProcessRunner(rs, ur, wds, tmp_path, env2)
    agg, code = drive(rs, tmp_path, env2, runner)
    assert code == 0 and runner.ids() == ALL_IDS and agg["reused"] == []


def test_a_changed_base_path_recomputes_via_the_args_input(rs, ur, wds, tmp_path):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    env2 = make_env(rs, base_path="/")
    runner = InProcessRunner(rs, ur, wds, tmp_path, env2)
    drive(rs, tmp_path, env2, runner)
    assert runner.ids() == ALL_IDS


def test_playwright_version_and_lockfile_changes_recompute_every_unit(rs, ur, wds, tmp_path):
    base = make_env(rs, driver=ur.driver_input(playwright_version="1.62.0", uv_lock_bytes=b"a"))
    drive(rs, tmp_path, base, InProcessRunner(rs, ur, wds, tmp_path, base))
    for pv, lock in (("1.63.0", b"a"), ("1.62.0", b"b")):
        env2 = make_env(rs, driver=ur.driver_input(playwright_version=pv, uv_lock_bytes=lock))
        runner = InProcessRunner(rs, ur, wds, tmp_path, env2)
        agg, _ = drive(rs, tmp_path, env2, runner)
        assert runner.ids() == ALL_IDS, (pv, lock)
        assert agg["reused"] == []
        # put the original stamps back for the next case
        drive(rs, tmp_path, base, InProcessRunner(rs, ur, wds, tmp_path, base))


def test_a_tampered_result_recomputes(rs, ur, wds, tmp_path):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    path = rs.unit_paths(tmp_path, "D1")["result"]
    data = json.loads(path.read_text())
    data["pageerrors"] = []  # a valid-looking edit: same shape, different bytes
    data["tampered"] = True
    path.write_text(json.dumps(data))
    runner = InProcessRunner(rs, ur, wds, tmp_path, env)
    agg, code = drive(rs, tmp_path, env, runner)
    assert runner.ids() == ["D1"] and [r["id"] for r in agg["reused"]] == ALL_IDS[1:] and code == 0


def test_a_failing_key_is_recorded_and_never_reused(rs, ur, wds, tmp_path):
    env = make_env(rs)
    bad = dict(passing_fields(rs.UNIT_BY_ID["D1"]), rail_state_after_run="not-run")
    agg, code = drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env, fields={"D1": bad}))
    assert code == 1 and agg["passed"] is False
    assert [f["id"] for f in agg["failed"]] == ["D1"] and agg["failed"][0]["failing_keys"] == ["rail_state_after_run"]
    # a flaky failure is always retried
    runner = InProcessRunner(rs, ur, wds, tmp_path, env)
    agg2, code2 = drive(rs, tmp_path, env, runner)
    assert runner.ids() == ["D1"] and code2 == 0 and [r["id"] for r in agg2["reused"]] == ALL_IDS[1:]


def test_a_missing_listed_key_is_never_reused(rs, ur, wds, tmp_path):
    env = make_env(rs)
    partial = passing_fields(rs.UNIT_BY_ID["D1-dark"])
    del partial["rail_colors_match_dark"]
    agg, code = drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env, fields={"D1-dark": partial}))
    assert code == 1 and agg["failed"][0]["missing_keys"] == ["rail_colors_match_dark"]
    runner = InProcessRunner(rs, ur, wds, tmp_path, env)
    drive(rs, tmp_path, env, runner)
    assert runner.ids() == ["D1-dark"]


def test_a_stamp_with_nonzero_exit_over_a_passing_result_is_not_reused(rs, ur, wds, tmp_path):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    path = rs.unit_paths(tmp_path, "D1")["stamp"]
    stamp = json.loads(path.read_text())
    stamp["exit"] = 3
    path.write_text(json.dumps(stamp))
    runner = InProcessRunner(rs, ur, wds, tmp_path, env)
    drive(rs, tmp_path, env, runner)
    assert runner.ids() == ["D1"]


def test_runner_killed_between_result_and_stamp_leaves_no_stamp_and_is_recomputed(rs, ur, wds, tmp_path):
    env = make_env(rs)
    runner = InProcessRunner(rs, ur, wds, tmp_path, env, skip_stamp={"D1"})
    agg, code = drive(rs, tmp_path, env, runner)
    files = rs.unit_paths(tmp_path, "D1")
    assert files["result"].exists() and not files["stamp"].exists()
    assert code == 1 and agg["missing"] == ["D1"] and agg["recomputed"] == ALL_IDS[1:]
    again = InProcessRunner(rs, ur, wds, tmp_path, env)
    agg2, code2 = drive(rs, tmp_path, env, again)
    assert again.ids() == ["D1"] and code2 == 0 and agg2["missing"] == []


def test_timed_out_unit_with_no_stamp_is_listed_and_fails_the_aggregate(rs, ur, wds, tmp_path):
    env = make_env(rs)

    class HangRunner(InProcessRunner):
        def run_unit(self, argv: Any, timeout_s: float, **kw: Any) -> Any:
            self.calls.append((list(argv), timeout_s, kw.get("cwd")))
            if "D1" == list(argv)[list(argv).index("--scenario") + 1]:
                return self.ur.UnitOutcome(-9, True, True)  # timed out, wrote nothing
            return super().run_unit(argv, timeout_s, **kw)

    agg, code = drive(rs, tmp_path, env, HangRunner(rs, ur, wds, tmp_path, env))
    assert code == 1 and agg["timed_out"] == ["D1"] and agg["passed"] is False
    files = rs.unit_paths(tmp_path, "D1")
    assert not files["stamp"].exists() and not files["result"].exists()


def test_timeout_marker_without_stamp_is_a_timed_out_unit(rs, tmp_path):
    env = make_env(rs)
    (tmp_path).mkdir(exist_ok=True)
    rs.unit_paths(tmp_path, "D1")["timeout"].write_text(json.dumps({"unit": "D1"}))
    agg, code = drive(rs, tmp_path, env, SpyRunner(), aggregate_only=True)
    assert code == 1 and agg["timed_out"] == ["D1"] and agg["missing"] == ALL_IDS[1:]


def test_run_unit_timeout_over_a_valid_stamp_defers_to_the_stamp_and_warns(rs, ur, wds, tmp_path, caplog):
    env = make_env(rs)
    runner = InProcessRunner(rs, ur, wds, tmp_path, env, timed_out={"D1"})
    with caplog.at_level(logging.WARNING):
        agg, code = drive(rs, tmp_path, env, runner)
    assert code == 0 and agg["timed_out"] == [] and agg["recomputed"] == ALL_IDS
    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("D1" in m and "timed out" in m.lower() for m in messages), messages


def test_aggregate_verdict_is_identical_whether_units_were_reused_or_recomputed(rs, ur, wds, tmp_path):
    env = make_env(rs)
    fields = {"D1": dict(passing_fields(rs.UNIT_BY_ID["D1"]), light_sheet="rgb(0, 0, 0)")}
    fresh_agg, fresh_code = drive(rs, tmp_path / "a", env, InProcessRunner(rs, ur, wds, tmp_path / "a", env, fields=fields))
    ok_first, code_ok = drive(rs, tmp_path / "b", env, InProcessRunner(rs, ur, wds, tmp_path / "b", env))
    reuse_ok, code_reuse = drive(rs, tmp_path / "b", env, SpyRunner())
    assert (code_ok, code_reuse) == (0, 0) and ok_first["passed"] == reuse_ok["passed"] is True
    assert fresh_code == 1 and fresh_agg["passed"] is False
    # D1-dark is judged from its result alone: reused or recomputed, same scenarios entry
    assert ok_first["scenarios"]["D1-dark"] == reuse_ok["scenarios"]["D1-dark"]


# --------------------------------------------------------------------------- #
# --aggregate-only: no unit subprocess, counts missing as failed, NEVER deletes
# --------------------------------------------------------------------------- #


def test_aggregate_only_over_matching_stamps_reuses_them_and_starts_nothing(rs, ur, wds, tmp_path):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    spy = SpyRunner()
    agg, code = drive(rs, tmp_path, env, spy, aggregate_only=True)
    assert code == 0 and spy.calls == [] and agg["passed"] is True
    assert [r["id"] for r in agg["reused"]] == ALL_IDS and agg["recomputed"] == []


def test_aggregate_only_counts_a_missing_unit_as_failed(rs, ur, wds, tmp_path):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    files = rs.unit_paths(tmp_path, "D1-dark")
    files["stamp"].unlink()
    files["result"].unlink()
    before = snapshot_files(tmp_path)
    agg, code = drive(rs, tmp_path, env, SpyRunner(), aggregate_only=True)
    assert code == 1 and agg["missing"] == ["D1-dark"]
    after = snapshot_files(tmp_path)
    assert {k: v for k, v in after.items() if k != "result.json"} == {k: v for k, v in before.items() if k != "result.json"}


def test_aggregate_only_with_a_stale_stamp_lists_it_and_deletes_nothing(rs, ur, wds, tmp_path):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    before = snapshot_files(tmp_path)
    stale_env = make_env(rs, dist="1" * 64)
    agg, code = drive(rs, tmp_path, stale_env, SpyRunner(), aggregate_only=True)
    assert code == 1
    assert [(s["id"], s["mismatched"]) for s in agg["stale"]] == [(i, ["dist"]) for i in ALL_IDS]
    after = snapshot_files(tmp_path)
    for name, data in before.items():
        if name != "result.json":
            assert after[name] == data, f"{name} must be byte-identical after --aggregate-only"


def test_aggregate_only_with_a_different_base_path_makes_every_unit_stale_on_args(rs, ur, wds, tmp_path):
    env = make_env(rs, base_path="/praxis/")
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    agg, code = drive(rs, tmp_path, make_env(rs, base_path="/"), SpyRunner(), aggregate_only=True)
    assert code == 1 and [(s["id"], s["mismatched"]) for s in agg["stale"]] == [(i, ["args"]) for i in ALL_IDS]
    same, code_same = drive(rs, tmp_path, make_env(rs, base_path="/praxis/"), SpyRunner(), aggregate_only=True)
    assert code_same == 0 and len(same["reused"]) == len(ALL_IDS)


def test_run_display_check_aggregate_only_starts_no_unit_and_keeps_files(rs, ur, wds, tmp_path):
    env = make_env(rs)
    out = tmp_path / "out"
    drive(rs, out, env, InProcessRunner(rs, ur, wds, out, env))
    before = snapshot_files(out)
    spy = SpyRunner()
    args = rs.parse_args(["--display-check", "--aggregate-only", "--out-dir", str(out), "--base-path", "/praxis/"])
    assert rs.run_display_check(args, runner=spy, hash_env=env) == 0 and spy.calls == []
    stale_args = rs.parse_args(["--display-check", "--aggregate-only", "--out-dir", str(out), "--base-path", "/other/"])
    assert rs.run_display_check(stale_args, runner=spy, hash_env=make_env(rs, base_path="/other/")) == 1
    after = snapshot_files(out)
    assert all(after[k] == v for k, v in before.items() if k != "result.json")


def test_run_display_check_driver_forwards_the_hashed_arguments(rs, ur, wds, tmp_path):
    env = make_env(rs)
    out = tmp_path / "out"
    runner = InProcessRunner(rs, ur, wds, out, env)
    args = rs.parse_args(["--display-check", "--out-dir", str(out), "--base-path", "/praxis/", "--serve-dir", str(tmp_path)])
    assert rs.run_display_check(args, runner=runner, hash_env=env, unit_argv_prefix=["py", "smoke.py"]) == 0
    for argv, timeout, _ in runner.calls:
        assert argv[:2] == ["py", "smoke.py"] and "--display-check" in argv and "--scenario" in argv
        assert argv[argv.index("--base-path") + 1] == "/praxis/"
        assert argv[argv.index("--out-dir") + 1] == str(out)
        assert argv[argv.index("--serve-dir") + 1] == str(tmp_path)
        assert "--chrome-path" in argv and timeout in {m * 60 + 60 for m in BUDGET_MIN}


# --------------------------------------------------------------------------- #
# --scenario watchdog and teardown: short-lived child processes, real Watchdog + kill_tree
# --------------------------------------------------------------------------- #

CHILD = textwrap.dedent(
    '''
    import atexit, importlib.util, json, os, sys, threading, time
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("rs_child", os.environ["RS_PATH"])
    rs = importlib.util.module_from_spec(spec)
    sys.modules["rs_child"] = rs
    spec.loader.exec_module(rs)
    PLAN = json.loads(os.environ["RS_PLAN"])
    env = rs.HashEnv(**PLAN["env"])
    os.dup2(os.open(PLAN["stdout"], os.O_WRONLY | os.O_CREAT | os.O_APPEND), 1)


    class Session:
        pageerrors = []

        def close(self):
            if PLAN.get("hang_close") == "browser":
                time.sleep(600)
            if PLAN.get("hang_close") == "playwright":
                time.sleep(600)


    def scenario(session, unit, e):
        if PLAN.get("hang_scenario"):
            time.sleep(600)
        fields = dict(unit.expected)
        for k in PLAN.get("drop", []):
            fields.pop(k, None)
        return fields


    if PLAN.get("atexit_hang"):
        atexit.register(time.sleep, 600)
        threading.Thread(target=time.sleep, args=(600,)).start()
    code = rs.run_scenario(
        PLAN["unit"], out_dir=Path(PLAN["out"]), env_fn=lambda: env,
        session_factory=lambda u, e: Session(), scenario_fn=scenario, budget_s=PLAN["budget"],
    )
    sys.exit(code)
    '''
)


def run_child(rs: Any, ur: Any, tmp_path: Path, **plan: Any) -> tuple[Any, float, str]:
    script = tmp_path / "child.py"
    script.write_text(CHILD)
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    stdout_path = tmp_path / "child.stdout"
    plan = {
        "unit": "D1", "out": str(out), "env": dataclasses.asdict(make_env(rs)), "budget": 1.0,
        "stdout": str(stdout_path), **plan,
    }
    env = {k: v for k, v in os.environ.items() if k != "PRAXIS_UNIT_TOKEN"}
    env.update(RS_PATH=str(REPL_SMOKE), RS_PLAN=json.dumps(plan))
    t0 = time.monotonic()
    outcome = ur.run_unit([sys.executable, str(script)], timeout_s=60, env=env, cwd=str(REPO_ROOT))
    elapsed = time.monotonic() - t0
    return outcome, elapsed, stdout_path.read_text() if stdout_path.exists() else ""


def test_scenario_hang_exits_124_with_marker_and_no_stamp_or_result(rs, ur, tmp_path):
    outcome, elapsed, stdout = run_child(rs, ur, tmp_path, hang_scenario=True)
    files = rs.unit_paths(tmp_path / "out", "D1")
    assert outcome.exit == 124 and elapsed < 1 + 5 + 20
    assert not files["stamp"].exists() and not files["result"].exists()
    marker = json.loads(files["timeout"].read_text())
    assert set(marker) == {"unit", "budget_s", "started", "expired"} and marker["unit"] == "D1"
    assert marker["budget_s"] == 1.0
    line = [ln for ln in stdout.splitlines() if ln.startswith("{")][-1]
    assert json.loads(line) == {"unit": "D1", "status": "timeout", "budget_s": 1.0}


@pytest.mark.parametrize("where", ["browser", "playwright"])
def test_hang_in_teardown_exits_124_and_deletes_the_result_it_had_written(rs, ur, tmp_path, where):
    outcome, elapsed, _ = run_child(rs, ur, tmp_path, hang_close=where)
    files = rs.unit_paths(tmp_path / "out", "D1")
    assert outcome.exit == 124 and elapsed < 1 + 5 + 20
    assert not files["stamp"].exists(), "the stamp is committed only after a completed teardown"
    assert not files["result"].exists(), "the watchdog deleted the result written before the hang"
    assert files["timeout"].exists()


def test_timed_out_rerun_clears_the_prior_stamp_and_the_next_resume_recomputes(rs, ur, wds, tmp_path):
    env = make_env(rs)
    out = tmp_path / "out"
    drive(rs, out, env, InProcessRunner(rs, ur, wds, out, env))  # passing run leaves stamps
    old = rs.unit_paths(out, "D1")
    assert old["stamp"].exists() and old["result"].exists()
    outcome, _, _ = run_child(rs, ur, tmp_path, hang_scenario=True)  # same out dir as `out`
    assert outcome.exit == 124
    assert not old["result"].exists() and not old["stamp"].exists()
    runner = InProcessRunner(rs, ur, wds, out, env)
    agg, _ = drive(rs, out, env, runner)
    assert runner.ids() == ["D1"] and [r["id"] for r in agg["reused"]] == ALL_IDS[1:]


def test_nothing_runs_after_the_stamp_but_exit(rs, ur, tmp_path):
    """C9-1: a hanging atexit handler and a blocking non-daemon thread cannot delay the exit
    (only ``os._exit(stamp.exit)`` follows the commit); the exit code is the stamp's."""
    t0 = time.monotonic()
    outcome, elapsed, _ = run_child(rs, ur, tmp_path, atexit_hang=True, drop=["light_sheet"], budget=30.0)
    files = rs.unit_paths(tmp_path / "out", "D1")
    assert outcome.exit == 1 and json.loads(files["stamp"].read_text())["exit"] == 1
    assert elapsed < 20 and time.monotonic() - t0 < 25
    assert files["result"].exists() and not files["timeout"].exists()


def test_child_passing_scenario_exits_0_and_stamps(rs, ur, tmp_path):
    outcome, _, _ = run_child(rs, ur, tmp_path, budget=30.0)
    files = rs.unit_paths(tmp_path / "out", "D1")
    assert outcome.exit == 0 and json.loads(files["stamp"].read_text())["exit"] == 0


# --------------------------------------------------------------------------- #
# The D1 / D1-dark key derivation: a positive control AND negative controls (BATHOS.md)
# --------------------------------------------------------------------------- #

MOONSTONE, ROSE, BRICK = "rgb(47, 104, 130)", "rgb(237, 122, 155)", "rgb(179, 64, 42)"
LIGHT_GREY, DARK_GREY = "rgb(201, 210, 218)", "rgba(255, 255, 255, 0.12)"
TRANSPARENT = "rgba(0, 0, 0, 0)"


def _snap(state: Any, bg: str, *, count: Any = None, content: Any = None, image: str = "none", sheet: str = "rgb(255, 255, 255)") -> dict[str, Any]:
    if content is None:
        content = '""' if count is None else f'"{count}"'
    return {
        "state": state, "exec_attr": "" if count is None else str(count), "before_bg": bg,
        "before_bg_image": image, "before_width": "3px", "after_content": content,
        "sheet_bg": sheet, "model": {"execution_count": count},
    }


def good_raw(*, light: bool) -> dict[str, Any]:
    grey = LIGHT_GREY if light else DARK_GREY
    stale_image = f"repeating-linear-gradient({MOONSTONE} 0px, {MOONSTONE} 5px, rgba(0, 0, 0, 0) 5px, rgba(0, 0, 0, 0) 9px)"
    never = _snap("not-run", grey)
    ran = _snap("ran", MOONSTONE, count=1)
    running = _snap("running", ROSE)
    err = _snap("error", BRICK, count=3)
    stale = _snap("stale", TRANSPARENT, count=4, image=stale_image)
    finals = [never, ran, _snap("ran", MOONSTONE, count=2), err, stale]
    return {
        "never_run": never, "after_run": ran, "while_sleep": running, "after_raise": err, "after_edit": stale,
        "final": finals, "grey_token": grey,
        "prompts": {"input_w": 0, "output_w": 0, "cell_w": 900, "editor_w": 700},
        "ground": "rgb(238, 241, 244)" if light else "rgb(26, 26, 46)", "sheet": "rgb(255, 255, 255)",
        "theme_name": "JupyterLab Light" if light else "JupyterLab Dark",
    }


def test_derive_positive_control_light_all_listed_keys_hold(rs):
    keys = rs.derive_chrome_keys(good_raw(light=True), light=True)
    unit = rs.UNIT_BY_ID["D1"]
    fields = {k: v for k, v in keys.items()}
    fields["pageerrors"] = []
    assert rs.evaluate_unit_result(unit, fields) == ([], []), keys


def test_derive_positive_control_dark_all_listed_keys_hold(rs):
    keys = rs.derive_chrome_keys(good_raw(light=False), light=False)
    assert rs.evaluate_unit_result(rs.UNIT_BY_ID["D1-dark"], keys) == ([], []), keys
    assert "light_ground" not in keys and "rail_colors_match" not in keys


def test_negative_control_no_chrome_js_means_no_state_attribute(rs):
    """AC-39(a)'s mechanism, on synthetic ground truth: the display module never mounted, so no
    cell carries ``data-praxis-cell-state`` and no ``::after`` count exists."""
    raw = good_raw(light=True)
    for snap in (raw["never_run"], raw["after_run"], raw["while_sleep"], raw["after_raise"], raw["after_edit"], *raw["final"]):
        snap.update(state=None, exec_attr=None, after_content="none", before_bg=LIGHT_GREY)
    keys = rs.derive_chrome_keys(raw, light=True)
    missing, failing = rs.evaluate_unit_result(rs.UNIT_BY_ID["D1"], dict(keys, pageerrors=[]))
    assert "rail_state_after_run" in failing and "rail_state_never_run" in failing
    assert "rail_colors_match" in failing and "exec_count_on_rail" in failing


def test_negative_control_wrong_rail_colour_fails_rail_colors_match_only(rs):
    raw = good_raw(light=True)
    raw["after_run"]["before_bg"] = "rgb(1, 2, 3)"
    keys = rs.derive_chrome_keys(raw, light=True)
    assert keys["rail_colors_match"] is False and keys["rail_state_after_run"] == "ran"


@pytest.mark.parametrize(
    "stage,bg", [("never_run", "rgb(1, 2, 3)"), ("while_sleep", MOONSTONE), ("after_raise", ROSE)]
)
def test_each_state_colour_is_checked_individually(rs, stage, bg):
    raw = good_raw(light=True)
    raw[stage]["before_bg"] = bg
    assert rs.derive_chrome_keys(raw, light=True)["rail_colors_match"] is False


def test_stale_rail_is_a_dashed_gradient_not_a_flat_colour(rs):
    raw = good_raw(light=True)
    raw["after_edit"]["before_bg_image"] = "none"  # a flat, non-dashed stale rail
    assert rs.derive_chrome_keys(raw, light=True)["rail_colors_match"] is False
    raw = good_raw(light=True)
    raw["after_edit"]["before_bg"] = MOONSTONE  # solid instead of transparent-with-gradient
    assert rs.derive_chrome_keys(raw, light=True)["rail_colors_match"] is False


def test_dark_grey_must_be_the_computed_border_token(rs):
    raw = good_raw(light=False)
    raw["never_run"]["before_bg"] = LIGHT_GREY  # Light grey in a Dark run
    assert rs.derive_chrome_keys(raw, light=False)["rail_colors_match_dark"] is False
    raw = good_raw(light=False)
    raw["grey_token"] = ""
    assert rs.derive_chrome_keys(raw, light=False)["rail_colors_match_dark"] is False


def test_dark_keys_need_the_dark_theme_and_light_keys_need_the_light_theme(rs):
    raw = good_raw(light=False)
    raw["theme_name"] = "JupyterLab Light"
    assert rs.derive_chrome_keys(raw, light=False)["rail_colors_match_dark"] is False
    raw = good_raw(light=True)
    raw["theme_name"] = "JupyterLab Dark"
    assert rs.derive_chrome_keys(raw, light=True)["rail_colors_match"] is False


def test_prompts_need_zero_width_and_a_live_layout(rs):
    raw = good_raw(light=True)
    raw["prompts"]["input_w"] = 40
    assert rs.derive_chrome_keys(raw, light=True)["prompts_take_no_space"] is False
    raw = good_raw(light=True)
    raw["prompts"]["output_w"] = 1.5
    assert rs.derive_chrome_keys(raw, light=True)["prompts_take_no_space"] is False
    raw = good_raw(light=True)
    raw["prompts"]["output_w"] = 1.0
    assert rs.derive_chrome_keys(raw, light=True)["prompts_take_no_space"] is True
    # vacuity: a prompt that was never found, or a cell with no layout (0 wide), proves nothing
    for change in ({"input_w": None}, {"output_w": None}, {"cell_w": 0}, {"editor_w": 0}):
        raw = good_raw(light=True)
        raw["prompts"].update(change)
        assert rs.derive_chrome_keys(raw, light=True)["prompts_take_no_space"] is False, change


def test_exec_count_on_rail_compares_the_pseudo_element_text_with_the_model(rs):
    raw = good_raw(light=True)
    assert rs.derive_chrome_keys(raw, light=True)["exec_count_on_rail"] is True
    raw["final"][1]["after_content"] = '"9"'  # the rail says 9, the model says 1
    assert rs.derive_chrome_keys(raw, light=True)["exec_count_on_rail"] is False
    raw = good_raw(light=True)
    raw["final"][0]["after_content"] = '"0"'  # a never-run cell must show no count
    assert rs.derive_chrome_keys(raw, light=True)["exec_count_on_rail"] is False
    raw = good_raw(light=True)  # vacuity: no cell has a count at all
    for snap in raw["final"]:
        snap["model"]["execution_count"] = None
        snap["after_content"] = '""'
    assert rs.derive_chrome_keys(raw, light=True)["exec_count_on_rail"] is False


@pytest.mark.parametrize(
    "raw_value,expected",
    [('"3"', "3"), ("'3'", "3"), ('""', ""), ("none", None), ("normal", None), (None, None), ('"12"', "12")],
)
def test_strip_css_content(rs, raw_value, expected):
    assert rs.strip_css_content(raw_value) == expected


def test_light_ground_and_sheet_are_read_from_the_snapshots(rs):
    raw = good_raw(light=True)
    raw["ground"] = "rgb(26, 26, 46)"
    keys = rs.derive_chrome_keys(raw, light=True)
    assert keys["light_ground"] == "rgb(26, 26, 46)" and keys["light_sheet"] == "rgb(255, 255, 255)"
    assert rs.evaluate_unit_result(rs.UNIT_BY_ID["D1"], dict(keys, pageerrors=[]))[1] == ["light_ground"]


# --------------------------------------------------------------------------- #
# Process management lives in unit_runner.py ONLY
# --------------------------------------------------------------------------- #


def test_repl_smoke_kills_nothing_and_writes_units_only_through_unit_runner():
    tree = ast.parse(REPL_SMOKE.read_text())
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            name = node.func.attr
            if name in {"kill", "killpg", "terminate", "send_signal", "pidfd_send_signal"}:
                offenders.append(f"{name} at line {node.lineno}")
    assert offenders == [], f"process killing belongs in scripts/unit_runner.py only: {offenders}"


def test_repl_smoke_loads_unit_runner_by_path_without_touching_sys_path():
    text = REPL_SMOKE.read_text()
    assert "sys.path.insert" not in text and "sys.path.append" not in text
    assert "unit_runner.py" in text


# --------------------------------------------------------------------------- #
# The harness-only in-page helpers (DISPLAY_CHECK_JS), under a JS engine with a fake DOM
# --------------------------------------------------------------------------- #

JS_ENGINE = shutil.which("node") or shutil.which("bun")

JS_DRIVER = textwrap.dedent(
    """
    const fs = require("fs");
    const src = fs.readFileSync(process.env.DC_JS, "utf8");
    globalThis.window = globalThis;
    const mkNode = (attrs, own, before, after, kids) => ({
      _own: own, _before: before, _after: after,
      getAttribute: (k) => (k in attrs ? attrs[k] : null),
      setAttribute: (k, v) => { attrs[k] = String(v); },
      getBoundingClientRect: () => ({ width: own.w ?? 0 }),
      querySelector: (q) => kids[q] ?? null,
      scrollIntoView: () => {},
    });
    const styleOf = (bg, image, content, w) => ({ backgroundColor: bg, backgroundImage: image, width: w, content });
    const cellAttrs = [{ "data-praxis-cell-state": "ran", "data-praxis-exec": "3" }, {}];
    const nodes = [
      mkNode(cellAttrs[0], { backgroundColor: "rgb(255, 255, 255)", w: 900 },
             styleOf("rgb(47, 104, 130)", "none", "none", "3px"), styleOf("rgba(0, 0, 0, 0)", "none", '"3"', "auto"),
             { ".jp-InputPrompt": mkNode({}, { w: 0 }, {}, {}, {}), ".jp-OutputPrompt": mkNode({}, { w: 0.5 }, {}, {}, {}),
               ".jp-InputArea-editor": mkNode({}, { w: 700 }, {}, {}, {}) }),
      mkNode(cellAttrs[1], { backgroundColor: "rgb(255, 255, 255)", w: 900 },
             styleOf("rgb(201, 210, 218)", "none", "none", "3px"), styleOf("rgba(0, 0, 0, 0)", "none", '""', "auto"), {}),
    ];
    globalThis.getComputedStyle = (node, pseudo) =>
      pseudo === "::before" ? node._before : pseudo === "::after" ? node._after : node._own;
    const models = [
      { executionCount: 3, executionState: "idle", outputs: { length: 1, get: () => ({ toJSON: () => ({ output_type: "error" }) }) },
        sharedModel: { getSource: () => "raise x" } },
      { executionCount: null, executionState: "idle", outputs: { length: 0, get: () => null }, sharedModel: { getSource: () => "x = 1" } },
    ];
    let greyBg = "";
    const bodyAttrs = { "data-jp-theme-name": "JupyterLab Light" };
    globalThis.document = {
      contains: () => true,
      body: { getAttribute: (k) => bodyAttrs[k] ?? null, appendChild: () => {} },
      createElement: () => ({
        style: { set backgroundColor(v) { greyBg = v; } }, remove: () => {},
        _own: { get backgroundColor() { return greyBg === "var(--jp-border-color1)" ? "rgb(201, 210, 218)" : ""; } },
      }),
      querySelector: () => null,
    };
    const runs = [];
    window.jupyterapp = {
      shell: { currentWidget: {
        content: { widgets: nodes.map((n) => ({ node: n })), activeCellIndex: 0, node: { _own: { backgroundColor: "rgb(238, 241, 244)" } },
                   model: { cells: { length: 2, get: (i) => models[i] } } },
        sessionContext: { session: { kernel: { status: "idle" } } } } },
      commands: { execute: (cmd) => { runs.push(cmd); return Promise.resolve(); } },
    };
    (0, eval)(src);
    const dc = window.__praxisDisplayCheck;
    (async () => {
      const out = {};
      out.snap0 = dc.snapshot(0);
      out.snap1 = dc.snapshot(1);
      out.theme = dc.themeName();
      out.ready = [dc.cellsReady(2), dc.cellsReady(3)];
      out.kernel = dc.kernelStatus();
      out.marked = dc.markCells();
      out.marks = [cellAttrs[0]["data-dcheck-index"], cellAttrs[1]["data-dcheck-index"]];
      out.done = [dc.modelDone(0), dc.modelDone(1)];
      out.prompts = dc.prompts(0);
      out.ground = dc.ground();
      out.run = dc.runCell(1);
      out.runs = runs;
      out.active = window.jupyterapp.shell.currentWidget.content.activeCellIndex;
      out.hit = (await dc.pollState({ i: 0, want: "ran", ms: 200 })).state;
      const t0 = Date.now();
      out.miss = (await dc.pollState({ i: 1, want: "running", ms: 120 })).state;
      out.miss_ms = Date.now() - t0;
      out.grey = dc.greyToken();
      out.grey_var = greyBg;
      console.log(JSON.stringify(out));
    })();
    """
)


@pytest.mark.skipif(JS_ENGINE is None, reason="no node or bun on PATH")
def test_page_helpers_read_the_attributes_pseudo_styles_and_model(rs, tmp_path):
    js = tmp_path / "dc.js"
    js.write_text(rs.DISPLAY_CHECK_JS)
    driver = tmp_path / "driver.js"
    driver.write_text(JS_DRIVER)
    proc = subprocess.run(
        [JS_ENGINE, str(driver)], env={**os.environ, "DC_JS": str(js)}, capture_output=True, text=True, timeout=60
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    s0, s1 = out["snap0"], out["snap1"]
    assert (s0["state"], s0["exec_attr"]) == ("ran", "3") and s1["state"] is None and s1["exec_attr"] is None
    assert s0["before_bg"] == "rgb(47, 104, 130)" and s0["after_content"] == '"3"' and s0["before_width"] == "3px"
    assert s0["model"]["execution_count"] == 3 and s0["model"]["output_types"] == ["error"]
    assert s1["model"]["execution_count"] is None and s1["model"]["output_types"] == []
    assert s0["sheet_bg"] == "rgb(255, 255, 255)" and s0["model"]["source"] == "raise x"
    assert out["theme"] == "JupyterLab Light" and out["ready"] == [True, False] and out["kernel"] == "idle"
    assert out["marked"] == 2 and out["marks"] == ["0", "1"]
    assert out["done"] == [True, False], "modelDone needs a non-null count and a non-running state"
    assert out["prompts"] == {"input_w": 0, "output_w": 0.5, "cell_w": 900, "editor_w": 700}
    assert out["ground"] == "rgb(238, 241, 244)"
    assert out["run"] == {"dispatched": True} and out["runs"] == ["notebook:run-cell"] and out["active"] == 1
    assert out["hit"] == "ran", "pollState returns the first snapshot in the wanted state"
    assert out["miss"] is None and out["miss_ms"] >= 100, "and the last snapshot once its deadline passes"
    assert out["grey_var"] == "var(--jp-border-color1)" and out["grey"] == "rgb(201, 210, 218)"


def test_display_check_js_is_read_only(rs):
    """The helpers only READ: nothing assigns to the product's DOM state or fires product commands
    except the one ``notebook:run-cell`` the scenario needs, and no product test hook is used."""
    js = rs.DISPLAY_CHECK_JS
    assert "commands.execute('notebook:run-cell')" in js
    assert js.count("commands.execute") == 1
    assert "data-praxis-test" not in js and "__praxis_test" not in js
    for forbidden in ("setSource", "sharedModel.set", "innerHTML", "removeAttribute('data-praxis"):
        assert forbidden not in js, forbidden


# =========================================================================== #
# SPRINT B (B10): the --display-check units D2, D3 and D4 (AC-21 .. AC-26)
#
# Tests first. The scenario BODIES cannot run without a browser and a dist built at the PLR 1.0
# pin (that is B10b, in CI or by the user), so what is proved here is everything that does not
# need one: the unit table with its listed keys, the pure key derivations (each with a positive
# control that can pass AND negative controls that must fail), the fixture notebook's structure,
# the in-page helpers under a JS engine against a fake DOM, and the scenarios' ORDERING against
# a scripted fake driver. The live-browser facts are listed in the B10 report as untested.
# =========================================================================== #

D2_KEYS = (
    # AC-21 (reprs live)
    "repr_cells_ok", "svg_in_dom", "html_bytes_max", "text_plain_matches", "pageerrors",
    # AC-22 (error panels live)
    "error_panels", "error_status", "runall_stops", "other_errors_plain",
    # AC-23 (staleness live)
    "stale_marked", "stale_not_persisted", "unchanged_not_marked", "mark_survives_scroll",
    "earlier_session_marked", "rerun_not_marked", "persistence_gate_never_open",
    # AC-25 (keyboard and text alternative)
    "svg_role_img", "aria_label_equals_summary", "tab_focuses_figure", "arrow_moves", "escape_leaves",
)
D3_KEYS = (
    "no_script_in_bundles", "reopened_branch", "persistence_gate_never_open",
    "svg_in_dom", "liquid_fill_computed",
)
D4_KEYS = ("hc_text_color", "hc_sheet_fill", "hc_palette_untouched")

MOONSTONE_LIVE = "rgb(115, 169, 194)"  # #73A9C2, the liquid fill (brand constant, D3)
ASSAY_PLAIN = "24 of 96 wells hold liquid, 50–150 µL. 2,400 µL in the plate."
HC_THEME = "JupyterLab Dark High Contrast"


def test_unit_table_lists_d2_d3_d4_with_the_d16_budgets_checks_and_listed_keys(rs):
    by = rs.UNIT_BY_ID
    assert [(by[i].check, by[i].budget_s) for i in ("D2", "D3", "D4")] == [
        ("display-check", 12 * 60), ("display-check", 8 * 60), ("display-check", 6 * 60),
    ]
    assert tuple(by["D2"].keys) == D2_KEYS
    assert tuple(by["D3"].keys) == D3_KEYS
    assert tuple(by["D4"].keys) == D4_KEYS
    assert len(set(by["D2"].keys)) == len(by["D2"].keys), "no key listed twice"


def test_unit_table_names_the_acs_each_unit_carries(rs):
    by = rs.UNIT_BY_ID
    assert tuple(by["D2"].acs) == ("AC-21", "AC-22", "AC-23", "AC-25")
    assert tuple(by["D3"].acs) == ("AC-24",) and tuple(by["D4"].acs) == ("AC-26",)


def test_listed_values_follow_ac21_to_ac26(rs):
    d2 = dict(rs.UNIT_BY_ID["D2"].expected)
    for key in D2_KEYS:
        if key not in ("html_bytes_max", "pageerrors"):
            assert d2[key] is True, key
    assert d2["pageerrors"] == [] and d2["html_bytes_max"].example() <= 65_536
    d3 = dict(rs.UNIT_BY_ID["D3"].expected)
    assert d3["reopened_branch"] == "S2-T", "AC-2 recorded s2_b_exec_t: the executed path reopens TRUSTED and live"
    assert d3["liquid_fill_computed"] == MOONSTONE_LIVE
    assert (d3["no_script_in_bundles"], d3["persistence_gate_never_open"], d3["svg_in_dom"]) == (True, True, True)
    assert dict(rs.UNIT_BY_ID["D4"].expected) == {k: True for k in D4_KEYS}


def test_the_recorded_executed_reopen_branch_is_one_named_constant(rs):
    assert rs.EXECUTED_REOPEN_BRANCH == "S2-T"
    assert dict(rs.UNIT_BY_ID["D3"].expected)["reopened_branch"] == rs.EXECUTED_REOPEN_BRANCH


def test_html_bytes_max_is_a_bound_not_an_equality(rs):
    unit = rs.UNIT_BY_ID["D2"]
    ok = passing_fields(unit)
    assert rs.evaluate_unit_result(unit, ok) == ([], [])
    for good in (0, 1, 36_142, 65_536, 65_536.0):
        assert rs.evaluate_unit_result(unit, dict(ok, html_bytes_max=good)) == ([], []), good
    for bad in (65_537, 70_000, None, True, "9000", [9000], float("nan")):
        assert rs.evaluate_unit_result(unit, dict(ok, html_bytes_max=bad)) == ([], ["html_bytes_max"]), bad
    without = dict(ok)
    del without["html_bytes_max"]
    assert rs.evaluate_unit_result(unit, without) == (["html_bytes_max"], [])


def test_a_bound_predicate_gives_a_passing_example_and_survives_json(rs):
    at_most = dict(rs.UNIT_BY_ID["D2"].expected)["html_bytes_max"]
    assert at_most.holds(at_most.example()) and not at_most.holds(at_most.limit + 1)
    assert json.loads(json.dumps(passing_fields(rs.UNIT_BY_ID["D2"])))["html_bytes_max"] == at_most.example()


@pytest.mark.parametrize("unit_id", ["D2", "D3", "D4"])
def test_every_new_key_is_strict_about_its_type(rs, unit_id):
    unit = rs.UNIT_BY_ID[unit_id]
    ok = passing_fields(unit)
    assert rs.evaluate_unit_result(unit, ok) == ([], [])
    for key, want in unit.expected:
        if want is True:  # 1 and "true" are not True
            assert rs.evaluate_unit_result(unit, dict(ok, **{key: 1}))[1] == [key], key
            assert rs.evaluate_unit_result(unit, dict(ok, **{key: "true"}))[1] == [key], key
            assert rs.evaluate_unit_result(unit, dict(ok, **{key: False}))[1] == [key], key
            assert rs.evaluate_unit_result(unit, dict(ok, **{key: None}))[1] == [key], key


def test_new_units_inputs_are_the_seven_d16_inputs_and_hash_the_unit_id(rs):
    env = make_env(rs)
    seen = set()
    for uid in ("D2", "D3", "D4"):
        inputs = rs.unit_inputs(rs.UNIT_BY_ID[uid], env)
        assert set(inputs) == INPUT_NAMES
        seen.add(inputs["args"])
    assert len(seen) == 3 and rs.unit_inputs(rs.UNIT_BY_ID["D1"], env)["args"] not in seen


def test_the_unit_files_of_the_new_units_live_beside_the_others(rs, tmp_path):
    for uid in ("D2", "D3", "D4"):
        p = rs.unit_paths(tmp_path, uid)
        assert p["result"] == tmp_path / f"result.{uid}.json"
        assert p["stamp"] == tmp_path / f"result.{uid}.stamp.json"


@pytest.mark.parametrize("unit_id", ["D2", "D3", "D4"])
def test_scenario_flag_runs_exactly_a_new_unit(rs, tmp_path, unit_id):
    seen: list[Any] = []
    args = rs.parse_args(["--display-check", "--scenario", unit_id, "--out-dir", str(tmp_path / "o")])
    rc = rs.run_display_check(
        args, runner=SpyRunner(), hash_env=make_env(rs),
        scenario_entry=lambda uid, **kw: seen.append(uid) or 0,
    )
    assert rc == 0 and seen == [unit_id]


# --------------------------------------------------------------------------- #
# The fixture notebook: D1's five cells untouched, then the B10 cells
# --------------------------------------------------------------------------- #

NB_PATH = REPO_ROOT / "web-repl" / "tests" / "fixtures" / "notebooks" / "display_check.ipynb"
D1_CELL_IDS = ["d1-never-run", "d1-ran", "d1-sleep", "d1-error", "d1-stale"]
B10_CELL_IDS = [
    "boot", "assemble", "transfers", "pickup", "draw-source", "draw-assay", "draw-tips", "draw-deck",
    "aspirate", "e1", "e2", "e4", "e6", "value-error", "redraw", "marker",
]


@pytest.fixture(scope="module")
def nb() -> dict[str, Any]:
    return json.loads(NB_PATH.read_text())


def _src(cell: dict[str, Any]) -> str:
    return "".join(cell["source"])


def test_fixture_keeps_the_d1_cells_first_and_unchanged_then_the_b10_cells(nb):
    ids = [c["id"] for c in nb["cells"]]
    assert ids == D1_CELL_IDS + B10_CELL_IDS, "D1 addresses cells 0-4 by index: they must not move"
    d1 = {c["id"]: _src(c) for c in nb["cells"][:5]}
    assert d1["d1-ran"] == 'print("d1-ran")' and d1["d1-sleep"] == "import asyncio\nawait asyncio.sleep(3)"
    assert d1["d1-error"] == 'raise ValueError("d1-error")' and d1["d1-stale"] == 'print("d1-stale", 1)'


def test_fixture_cells_are_never_executed_and_carry_no_outputs(nb):
    for cell in nb["cells"]:
        assert cell["cell_type"] == "code" and cell["execution_count"] is None and cell["outputs"] == [], cell["id"]
        assert cell["metadata"] == {}


def test_fixture_cell_ids_are_the_harness_names(rs, nb):
    assert rs.FIXTURE_CELLS == {
        "boot": "boot", "assemble": "assemble", "transfers": "transfers", "pickup": "pickup",
        "draw_source": "draw-source", "draw_assay": "draw-assay", "draw_tips": "draw-tips",
        "draw_deck": "draw-deck", "aspirate": "aspirate", "e1": "e1", "e2": "e2", "e4": "e4", "e6": "e6",
        "value_error": "value-error", "redraw": "redraw", "marker": "marker",
    }
    idx = rs.cell_indices(nb)
    assert idx["d1-never-run"] == 0 and idx["d1-stale"] == 4 and idx["boot"] == 5 and idx["marker"] == len(nb["cells"]) - 1
    assert [idx[i] for i in B10_CELL_IDS] == list(range(5, 5 + len(B10_CELL_IDS)))


def test_cell_indices_refuses_a_duplicated_id_and_require_cells_a_missing_one(rs, nb):
    broken = json.loads(json.dumps(nb))
    broken["cells"][7]["id"] = "boot"
    with pytest.raises(ValueError):
        rs.cell_indices(broken)
    short = {"cells": nb["cells"][:5]}
    assert set(rs.cell_indices(short)) == set(D1_CELL_IDS)
    with pytest.raises(KeyError):
        rs.require_cells(short, "boot")


def test_boot_cell_runs_the_real_kernel_path_and_installs_the_display_idempotently(nb):
    src = _src(next(c for c in nb["cells"] if c["id"] == "boot"))
    assert "import praxis_boot" in src and "await praxis_boot.setup()" in src, "the bootstrap's own once-guarded path"
    assert "praxis.display" in src and ".install()" in src, "install() is idempotent per shell and returns the handle"


def test_setup_cells_build_the_make_fixture_world_at_the_pin(nb):
    cells = {c["id"]: _src(c) for c in nb["cells"]}
    a = cells["assemble"]
    for needle in (
        "from pylabrobot.legacy.liquid_handling import LiquidHandler", "LiquidHandlerChatterboxBackend(num_channels=8)",
        "STARLetDeck()", 'hamilton_96_tiprack_300uL_filter(name="tips_300")', "track=3", "track=9",
        'cor_96_wellplate_360uL_Fb(name="source")', 'cor_96_wellplate_360uL_Fb(name="assay")',
        "set_tip_tracking(True)", "set_volume_tracking(True)", "set_volume(200.0)", "await lh.setup()",
    ):
        assert needle in a, needle
    assert "rails=" not in a, "rails= is the 0.2.2 spelling; the pin says track="
    t = cells["transfers"]
    assert "(1, 50.0), (2, 100.0), (3, 150.0)" in t and "await lh.discard_tips()" in t
    assert cells["pickup"].strip() == 'await lh.pick_up_tips(tips["A4:H4"])'


def test_drawing_cells_display_exactly_one_object_each(nb):
    cells = {c["id"]: _src(c).strip() for c in nb["cells"]}
    assert cells["draw-source"] == "source" and cells["draw-assay"] == "assay"
    assert cells["draw-tips"] == "tips" and cells["draw-deck"] == "deck"


def test_the_aspirate_cell_is_aspirate_only(nb):
    src = _src(next(c for c in nb["cells"] if c["id"] == "aspirate"))
    assert "lh.aspirate(" in src and "lh.dispense(" not in src and "pick_up_tips" not in src and "discard_tips" not in src


def test_error_cells_raise_what_ac22_names_and_only_that(nb):
    cells = {c["id"]: _src(c) for c in nb["cells"]}
    assert 'lh.aspirate(assay["A1:H1"], vols=[80.0] * 8)' in cells["e1"]
    assert "set_volume(400)" in cells["e2"] and "lh.dispense(" in cells["e2"] and 'assay.get_item("A2")' in cells["e2"]
    assert 'lh.pick_up_tips(tips["A5:H5"])' in cells["e4"]
    assert "await lh.discard_tips()" in cells["e6"] and "use_channels=[0]" in cells["e6"] and "lh.aspirate(" in cells["e6"]
    assert cells["value-error"].strip().startswith("raise ValueError(")
    for cid in ("e1", "e2", "e4", "e6", "value-error"):
        assert "try:" not in cells[cid] and "except" not in cells[cid], f"{cid}: the error must reach the shell"


def test_the_redraw_cell_is_self_contained_because_a_restart_loses_the_deck(nb):
    src = _src(next(c for c in nb["cells"] if c["id"] == "redraw"))
    assert 'cor_96_wellplate_360uL_Fb(name="redraw")' in src and src.strip().splitlines()[-1] == "redraw"
    assert "deck" not in src and "lh." not in src, "must not need a name the restart lost"


def test_the_marker_cell_is_a_plain_statement_after_the_error(nb):
    ids = [c["id"] for c in nb["cells"]]
    assert ids.index("marker") > ids.index("e1")
    assert "raise" not in _src(nb["cells"][ids.index("marker")])


def test_fixture_cells_parse_with_top_level_await(nb):
    import ast as _ast

    for cell in nb["cells"]:
        compile(_src(cell), cell["id"], "exec", flags=_ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)


def test_no_cell_writes_a_script_or_touches_the_ack_key(nb):
    text = "\n".join(_src(c) for c in nb["cells"])
    assert "<script" not in text.lower() and "praxis-repl-persistence-ack" not in text


def test_runall_notebook_is_the_pair_derived_from_the_fixture(rs, nb):
    pair = rs.build_runall_notebook(nb)
    assert [c["id"] for c in pair["cells"]] == ["assemble", "transfers", "pickup", "e1", "marker"]
    assert tuple(rs.RUNALL_CELL_IDS) == ("assemble", "transfers", "pickup", "e1", "marker")
    src = {c["id"]: _src(c) for c in nb["cells"]}
    for cell in pair["cells"]:
        assert _src(cell) == src[cell["id"]], "cloned from the fixture, so the notebook hash covers it"
        assert cell["execution_count"] is None and cell["outputs"] == []
    assert pair["metadata"] == nb["metadata"] and pair["nbformat"] == nb["nbformat"]
    assert nb["cells"][0]["id"] == "d1-never-run", "the fixture itself is not mutated"
    assert rs.RUNALL_NOTEBOOK_NAME != rs.DISPLAY_NOTEBOOK_NAME and rs.RUNALL_NOTEBOOK_NAME.endswith(".ipynb")


# --------------------------------------------------------------------------- #
# Synthetic ground truth for the key derivations: a positive control AND negative controls
# (a derivation that can only pass is not a check; BATHOS.md)
# --------------------------------------------------------------------------- #


def stamp(kind: str, resource: Any, *, session: str = "sess-1", rev: Any = 3, exec_: Any = 8) -> dict[str, Any]:
    return {"v": 1, "kind": kind, "resource": resource, "rev": rev, "session": session, "exec": exec_}


def out(*, otype: str = "execute_result", mimes: tuple[str, ...] = ("text/html", "text/plain"),
        html_bytes: int | None = 9_000, plain: str | None = "", st: Any = None, ename: Any = None,
        evalue: Any = None, index: int = 0) -> dict[str, Any]:
    return {"index": index, "output_type": otype, "mimes": list(mimes), "html_bytes": html_bytes,
            "plain": plain, "stamp": st, "ename": ename, "evalue": evalue}


def res(*, found: bool = True, svg: int = 1, changed: int = 0, earlier: int = 0) -> dict[str, Any]:
    return {"found": found, "svg_count": svg, "changed_notices": changed, "earlier_notices": earlier, "text_length": 200}


def report(*, count: Any = 1, state: Any = "ran", outputs: Any = None, res_: Any = None,
           titles: Any = (), perr: int = 0) -> dict[str, Any]:
    return {
        "index": 0, "found": True, "in_document": True, "state": state, "execution_count": count,
        "execution_state": "idle", "outputs": list(outputs or []), "res": res_,
        "error": {"titles": list(titles), "praxis_error_nodes": perr},
    }


def draw_reports(session: str = "sess-1") -> dict[str, dict[str, Any]]:
    def one(kind: str, name: str, plain: str, size: int) -> dict[str, Any]:
        return report(outputs=[out(html_bytes=size, plain=plain, st=stamp(kind, name, session=session))], res_=res())

    return {
        "draw_source": one("plate", "source", "All 96 wells hold liquid, 50–200 µL. 16,800 µL in the plate.", 9_100),
        "draw_assay": one("plate", "assay", ASSAY_PLAIN, 9_300),
        "draw_tips": one("tiprack", "tips_300", "64 of 96 tips left. Columns 1–4 used.", 9_800),
        "draw_deck": one("deck", "deck", "Tip carrier on rail 3, plate carrier on rail 9. 3 pieces of labware.", 36_142),
    }


def test_repr_keys_positive_control_all_hold_and_the_size_is_the_largest_output(rs):
    keys = rs.derive_repr_keys(draw_reports())
    assert keys == {"repr_cells_ok": True, "svg_in_dom": True, "html_bytes_max": 36_142, "text_plain_matches": True}
    unit = rs.UNIT_BY_ID["D2"]
    assert rs.evaluate_unit_result(unit, dict(passing_fields(unit), **keys))[1] == []


def test_repr_negative_control_no_display_installed_means_no_stamp_no_bundle_no_svg(rs):
    """AC-39's mechanism on synthetic ground truth: the formatter was never registered."""
    plain_only = {k: report(outputs=[out(mimes=("text/plain",), html_bytes=None, plain="<PLR object>")], res_=res(svg=0))
                  for k in draw_reports()}
    keys = rs.derive_repr_keys(plain_only)
    assert keys["repr_cells_ok"] is False and keys["svg_in_dom"] is False
    assert keys["text_plain_matches"] is False and keys["html_bytes_max"] is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["draw_deck"]["outputs"][0].update(mimes=["text/html"]),  # no text/plain
        lambda r: r["draw_assay"]["outputs"][0].update(mimes=["text/plain"]),  # no text/html
        lambda r: r["draw_tips"]["outputs"][0].update(stamp=None),  # no stamp
        lambda r: r["draw_tips"]["outputs"][0].update(stamp=stamp("plate", "tips_300")),  # wrong kind
        lambda r: r["draw_assay"]["outputs"][0].update(stamp=stamp("plate", "source")),  # wrong resource
        lambda r: r["draw_source"]["outputs"][0].update(stamp=stamp("plate", "source", rev=None)),  # a plate has a rev
        lambda r: r["draw_source"]["outputs"][0].update(stamp=stamp("plate", "source", session="")),
        lambda r: r["draw_deck"]["outputs"][0].update(stamp={"kind": "deck"}),  # not the D2 stamp
        lambda r: r["draw_deck"].update(outputs=[]),
    ],
)
def test_repr_cells_ok_needs_html_plain_and_the_right_stamp_on_every_cell(rs, mutate):
    reports = draw_reports()
    mutate(reports)
    assert rs.derive_repr_keys(reports)["repr_cells_ok"] is False


def test_svg_in_dom_needs_an_svg_under_every_drawn_output(rs):
    for name in ("draw_source", "draw_assay", "draw_tips", "draw_deck"):
        reports = draw_reports()
        reports[name]["res"] = res(svg=0)
        assert rs.derive_repr_keys(reports)["svg_in_dom"] is False, name
        reports[name]["res"] = res(found=False, svg=0)
        assert rs.derive_repr_keys(reports)["svg_in_dom"] is False, name
        reports[name]["res"] = None
        assert rs.derive_repr_keys(reports)["svg_in_dom"] is False, name


def test_text_plain_matches_is_the_ac9_string_exactly(rs):
    assert rs.ASSAY_TEXT_PLAIN == ASSAY_PLAIN
    for wrong in (ASSAY_PLAIN.replace("–", "-"), ASSAY_PLAIN.replace("µ", "u"), ASSAY_PLAIN + " ", ""):
        reports = draw_reports()
        reports["draw_assay"]["outputs"][0]["plain"] = wrong
        assert rs.derive_repr_keys(reports)["text_plain_matches"] is False, repr(wrong)


def test_html_bytes_max_reports_the_largest_and_is_none_when_any_drawing_is_missing(rs):
    reports = draw_reports()
    reports["draw_assay"]["outputs"][0]["html_bytes"] = 70_000
    assert rs.derive_repr_keys(reports)["html_bytes_max"] == 70_000
    reports = draw_reports()
    reports["draw_tips"]["outputs"] = []
    assert rs.derive_repr_keys(reports)["html_bytes_max"] is None


# -- AC-22 ---------------------------------------------------------------------------------------

HEADINGS = {
    "e1": "Not enough liquid in assay A1:H1.",
    "e2": "Not enough room in assay A2.",
    "e4": "Channel 0 already holds a tip.",
    "e6": "Channel 0 has no tip.",
}


def error_reports() -> dict[str, dict[str, Any]]:
    return {
        cid: report(count=10 + i, state="error", titles=[h], perr=1, outputs=[
            out(otype="display_data", st=stamp("error", None, rev=None)),
            out(otype="error", mimes=(), html_bytes=None, plain=None, ename="TooLittleLiquidError", evalue="x", index=1),
        ])
        for i, (cid, h) in enumerate(HEADINGS.items())
    }


def value_error_report() -> dict[str, Any]:
    return report(count=20, state="error", perr=0, outputs=[
        out(otype="error", mimes=(), html_bytes=None, plain=None, ename="ValueError", evalue="plain")
    ])


def runall_reports() -> dict[str, dict[str, Any]]:
    good = {c: report(count=i + 1) for i, c in enumerate(("assemble", "transfers", "pickup"))}
    good["e1"] = report(count=4, state="error", outputs=[out(otype="error", mimes=(), html_bytes=None, ename="TooLittleLiquidError")])
    good["marker"] = report(count=None, state="not-run")
    return good


def test_error_keys_positive_control(rs):
    assert rs.ERROR_HEADINGS == HEADINGS
    keys = rs.derive_error_keys(error_reports(), value_error_report(), runall_reports())
    assert keys == {"error_panels": True, "error_status": True, "runall_stops": True, "other_errors_plain": True}


@pytest.mark.parametrize("cid", list(HEADINGS))
def test_error_panels_needs_each_heading_verbatim(rs, cid):
    reports = error_reports()
    reports[cid]["error"]["titles"] = [HEADINGS[cid] + " "]
    assert rs.derive_error_keys(reports, value_error_report(), runall_reports())["error_panels"] is False
    reports[cid]["error"]["titles"] = []  # no panel at all: the default traceback only
    assert rs.derive_error_keys(reports, value_error_report(), runall_reports())["error_panels"] is False
    reports[cid]["error"]["titles"] = ["Some other heading", HEADINGS[cid]]  # the heading is the FIRST title
    assert rs.derive_error_keys(reports, value_error_report(), runall_reports())["error_panels"] is False


@pytest.mark.parametrize("cid", list(HEADINGS))
def test_error_status_needs_an_error_output_last_and_the_error_rail(rs, cid):
    reports = error_reports()
    reports[cid]["state"] = "ran"
    assert rs.derive_error_keys(reports, value_error_report(), runall_reports())["error_status"] is False
    reports = error_reports()
    reports[cid]["outputs"] = reports[cid]["outputs"][:1]  # the panel but no error output: Run All would not stop
    assert rs.derive_error_keys(reports, value_error_report(), runall_reports())["error_status"] is False
    reports = error_reports()
    reports[cid]["outputs"].reverse()  # the error output must be the LAST one
    assert rs.derive_error_keys(reports, value_error_report(), runall_reports())["error_status"] is False


def test_runall_stops_needs_the_marker_unrun_and_a_real_run_before_it(rs):
    good = runall_reports()
    assert rs.derive_error_keys(error_reports(), value_error_report(), good)["runall_stops"] is True
    ran_through = runall_reports()
    ran_through["marker"] = report(count=5)  # Run All did NOT stop
    assert rs.derive_error_keys(error_reports(), value_error_report(), ran_through)["runall_stops"] is False
    vacuous = runall_reports()  # nothing ran at all: the marker is null for a trivial reason
    for name in ("assemble", "transfers", "pickup", "e1"):
        vacuous[name] = report(count=None, state="not-run")
    assert rs.derive_error_keys(error_reports(), value_error_report(), vacuous)["runall_stops"] is False
    no_error = runall_reports()
    no_error["e1"] = report(count=4)  # e1 never raised: it proves nothing about stopping
    assert rs.derive_error_keys(error_reports(), value_error_report(), no_error)["runall_stops"] is False


def test_other_errors_plain_needs_the_default_traceback_and_no_praxis_panel(rs):
    keys = rs.derive_error_keys(error_reports(), value_error_report(), runall_reports())
    assert keys["other_errors_plain"] is True
    panelled = value_error_report()
    panelled["error"]["praxis_error_nodes"] = 1
    assert rs.derive_error_keys(error_reports(), panelled, runall_reports())["other_errors_plain"] is False
    silent = report(count=20, state="ran")  # the cell never raised: no default traceback to speak of
    assert rs.derive_error_keys(error_reports(), silent, runall_reports())["other_errors_plain"] is False
    wrong = value_error_report()
    wrong["outputs"][0]["ename"] = "TooLittleLiquidError"
    assert rs.derive_error_keys(error_reports(), wrong, runall_reports())["other_errors_plain"] is False


# -- AC-23 ---------------------------------------------------------------------------------------


def stale_raw() -> dict[str, Any]:
    return {
        "source": res(changed=1), "tips": res(changed=0),
        "persisted": {"file_read_ok": True, "has_outputs": True, "contains_changed": False, "mark_present_before_save": True},
        "after_scroll": res(changed=1), "after_rerender": res(changed=1), "rerender_ok": True,
    }


def test_stale_keys_positive_control(rs):
    assert rs.derive_stale_keys(stale_raw()) == {
        "stale_marked": True, "stale_not_persisted": True, "unchanged_not_marked": True, "mark_survives_scroll": True,
    }


def test_stale_marked_needs_the_notice_in_the_source_output(rs):
    raw = stale_raw()
    raw["source"] = res(changed=0)
    keys = rs.derive_stale_keys(raw)
    assert keys["stale_marked"] is False
    assert keys["unchanged_not_marked"] is False, "with no mark anywhere the machinery is dead: 'unmarked' proves nothing"
    raw["source"] = res(found=False, svg=0, changed=1)
    assert rs.derive_stale_keys(raw)["stale_marked"] is False


def test_unchanged_not_marked_fails_when_the_tip_rack_is_marked(rs):
    raw = stale_raw()
    raw["tips"] = res(changed=1)
    assert rs.derive_stale_keys(raw)["unchanged_not_marked"] is False
    raw["tips"] = res(found=False, svg=0, changed=0)  # a tip rack output that was not found proves nothing
    assert rs.derive_stale_keys(raw)["unchanged_not_marked"] is False


def test_stale_not_persisted_fails_on_a_persisted_mark_and_on_a_vacuous_save(rs):
    raw = stale_raw()
    raw["persisted"]["contains_changed"] = True
    assert rs.derive_stale_keys(raw)["stale_not_persisted"] is False
    for gap in ("file_read_ok", "has_outputs", "mark_present_before_save"):
        raw = stale_raw()
        raw["persisted"][gap] = False  # nothing was saved, or there was no mark to persist: vacuous
        assert rs.derive_stale_keys(raw)["stale_not_persisted"] is False, gap


@pytest.mark.parametrize("field,value", [("after_scroll", res(changed=0)), ("after_scroll", res(changed=2)),
                                          ("after_rerender", res(changed=0)), ("after_rerender", res(changed=2))])
def test_mark_survives_scroll_needs_exactly_one_notice_after_each_disturbance(rs, field, value):
    raw = stale_raw()
    raw[field] = value
    assert rs.derive_stale_keys(raw)["mark_survives_scroll"] is False


def test_mark_survives_scroll_fails_when_the_rerender_never_happened(rs):
    raw = stale_raw()
    raw["rerender_ok"] = False
    assert rs.derive_stale_keys(raw)["mark_survives_scroll"] is False


def session_raw() -> dict[str, Any]:
    return {
        "pre": {"session": "sess-1", "res": res(earlier=1)},
        "rerun": {"session": "sess-2", "res": res(earlier=0)},
    }


def test_session_keys_positive_control(rs):
    assert rs.derive_session_keys(session_raw()) == {"earlier_session_marked": True, "rerun_not_marked": True}


def test_earlier_session_marked_fails_without_the_notice_or_without_a_new_session(rs):
    raw = session_raw()
    raw["pre"]["res"] = res(earlier=0)
    assert rs.derive_session_keys(raw)["earlier_session_marked"] is False
    raw = session_raw()
    raw["rerun"]["session"] = "sess-1"  # the kernel did not really start a new session
    keys = rs.derive_session_keys(raw)
    assert keys["earlier_session_marked"] is False and keys["rerun_not_marked"] is False
    raw = session_raw()
    raw["pre"]["session"] = ""
    assert rs.derive_session_keys(raw)["earlier_session_marked"] is False


def test_rerun_not_marked_is_the_negative_control_and_fails_when_the_new_output_is_marked(rs):
    raw = session_raw()
    raw["rerun"]["res"] = res(earlier=1)
    keys = rs.derive_session_keys(raw)
    assert keys["rerun_not_marked"] is False and keys["earlier_session_marked"] is True
    raw = session_raw()
    raw["rerun"]["res"] = res(found=False, svg=0)  # no re-run output to look at
    assert rs.derive_session_keys(raw)["rerun_not_marked"] is False


# -- the persistence gate ---------------------------------------------------------------------------


def test_persistence_gate_never_open_needs_a_live_monitor_and_no_sighting(rs):
    live = {"monitor": True, "seen": False}
    assert rs.persistence_gate_never_open([live, live]) is True
    assert rs.persistence_gate_never_open([live, {"monitor": True, "seen": True}]) is False
    assert rs.persistence_gate_never_open([{"monitor": False, "seen": False}]) is False, "a dead monitor sees nothing"
    assert rs.persistence_gate_never_open([]) is False, "no reading at all is no evidence"
    assert rs.persistence_gate_never_open([None]) is False


# -- AC-25 -----------------------------------------------------------------------------------------


def keyboard_raw() -> dict[str, Any]:
    return {
        "figure": {"found": True, "role": "img", "in_svg": True, "aria_label": ASSAY_PLAIN, "tabindex": "0"},
        "plain": ASSAY_PLAIN,
        "focus_probe": {"ok": True, "next_is_figure": True},
        "tab": {"is_figure": True},
        "live_tab": "assay A1: 50 µL",
        "live_arrow": "assay A2: 100 µL",
        "escape": {"is_figure": True, "rings": 0},
    }


def test_keyboard_keys_positive_control(rs):
    assert rs.derive_keyboard_keys(keyboard_raw()) == {
        "svg_role_img": True, "aria_label_equals_summary": True, "tab_focuses_figure": True,
        "arrow_moves": True, "escape_leaves": True,
    }


def test_the_arrow_expectation_is_read_from_the_fixture_not_from_the_specs_50(rs):
    """AC-25 says ArrowRight reads "assay A2: 50 µL", but the fixture the same D2 unit asserts against
    AC-9 (24 wells, 50-150 µL, 2,400 µL) has column 2 at 100 µL; the key is derived from the fixture."""
    assert rs.ARROW_RIGHT_LIVE_TEXT == "assay A2: 100 µL"
    raw = keyboard_raw()
    raw["live_arrow"] = "assay A2: 50 µL"
    assert rs.derive_keyboard_keys(raw)["arrow_moves"] is False


@pytest.mark.parametrize("field,value,key", [
    ("figure", {"found": False}, "svg_role_img"),
    ("figure", {"found": True, "role": "figure", "in_svg": True, "aria_label": ASSAY_PLAIN}, "svg_role_img"),
    ("figure", {"found": True, "role": "img", "in_svg": False, "aria_label": ASSAY_PLAIN}, "svg_role_img"),
    ("figure", {"found": True, "role": "img", "in_svg": True, "aria_label": ""}, "aria_label_equals_summary"),
    ("figure", {"found": True, "role": "img", "in_svg": True, "aria_label": "24 of 96 wells"}, "aria_label_equals_summary"),
    ("plain", "", "aria_label_equals_summary"),
    ("focus_probe", {"ok": False}, "tab_focuses_figure"),
    ("tab", {"is_figure": False}, "tab_focuses_figure"),
    ("live_arrow", "assay A1: 50 µL", "arrow_moves"),
    ("live_arrow", None, "arrow_moves"),
    ("escape", {"is_figure": False, "rings": 0}, "escape_leaves"),
    ("escape", {"is_figure": True, "rings": 1}, "escape_leaves"),
])
def test_each_keyboard_key_has_a_negative_control(rs, field, value, key):
    raw = keyboard_raw()
    raw[field] = value
    assert rs.derive_keyboard_keys(raw)[key] is False


def test_arrow_moves_needs_the_live_region_to_have_changed(rs):
    raw = keyboard_raw()
    raw["live_tab"] = raw["live_arrow"]  # ArrowRight changed nothing
    assert rs.derive_keyboard_keys(raw)["arrow_moves"] is False


# -- AC-24 -----------------------------------------------------------------------------------------


def trust_obs(**over: Any) -> dict[str, Any]:
    base = {
        "rendered": True, "output_model_trusted": True, "cell_model_trusted": True, "notebook_model_trusted": True,
        "chosen_mime": "text/html", "svg_count": 1, "live_res_count": 1, "tabindex_count": 1,
        "svg_class_kept": True, "svg_style_kept": True, "summary_visible": True, "plain_visible": False,
    }
    base.update(over)
    return base


@pytest.mark.parametrize("obs,branch", [
    (trust_obs(), "S2-T"),  # trusted, live: the recorded executed-saved-reopened path
    (trust_obs(output_model_trusted=False, cell_model_trusted=False), "S2-A"),  # untrusted, svg keeps class and style
    (trust_obs(output_model_trusted=False, cell_model_trusted=False, svg_style_kept=False), "S2-A'"),
    (trust_obs(output_model_trusted=False, cell_model_trusted=False, svg_class_kept=False, svg_style_kept=False), "S2-A'"),
    (trust_obs(output_model_trusted=False, cell_model_trusted=False, svg_count=0, live_res_count=0, tabindex_count=0,
               svg_class_kept=False, svg_style_kept=False), "S2-B"),
    (trust_obs(output_model_trusted=False, cell_model_trusted=False, chosen_mime="text/plain", svg_count=0,
               live_res_count=0, tabindex_count=0, plain_visible=True), "S2-C"),
])
def test_classify_reopened_branch_names_the_d1_s2_branches(rs, obs, branch):
    assert rs.classify_reopened_branch(obs) == branch


@pytest.mark.parametrize("obs", [
    None, {}, trust_obs(rendered=False),
    trust_obs(output_model_trusted=None), trust_obs(output_model_trusted="yes"),
    trust_obs(cell_model_trusted=False),  # the reads disagree: never guessed
    trust_obs(svg_count=0),  # says trusted but did not render live: not S2-T
    trust_obs(live_res_count=0), trust_obs(tabindex_count=0),
    trust_obs(output_model_trusted=False, cell_model_trusted=False, chosen_mime="text/plain", plain_visible=False),
    trust_obs(output_model_trusted=False, cell_model_trusted=False, chosen_mime="image/png"),
    trust_obs(output_model_trusted=False, cell_model_trusted=False, svg_count=0, summary_visible=False),
])
def test_classify_reopened_branch_never_guesses(rs, obs):
    got = rs.classify_reopened_branch(obs)
    assert got == "unclassified" or (got in ("unrendered",)), got
    assert got not in ("S2-T", "S2-A", "S2-A'", "S2-B", "S2-C")


def d3_raw() -> dict[str, Any]:
    reports = draw_reports()
    return {
        "saved": {"file_read_ok": True, "has_outputs": True, "script_count": 0},
        "reports": reports, "trust": trust_obs(),
        "paints": {"liquid_fill": MOONSTONE_LIVE, "liquid_count": 3, "liquid_attr": "#73A9C2"},
        "gate": [{"monitor": True, "seen": False}, {"monitor": True, "seen": False}],
    }


def test_d3_keys_positive_control_hold_for_the_recorded_branch(rs):
    keys = rs.derive_d3_keys(d3_raw())
    assert keys == {
        "no_script_in_bundles": True, "reopened_branch": "S2-T", "persistence_gate_never_open": True,
        "svg_in_dom": True, "liquid_fill_computed": MOONSTONE_LIVE,
    }
    unit = rs.UNIT_BY_ID["D3"]
    assert rs.evaluate_unit_result(unit, keys) == ([], [])


def test_d3_key_negative_controls(rs):
    raw = d3_raw()
    raw["saved"]["script_count"] = 1
    assert rs.derive_d3_keys(raw)["no_script_in_bundles"] is False
    for gap in ("file_read_ok", "has_outputs"):
        raw = d3_raw()
        raw["saved"][gap] = False  # nothing saved to inspect: never a pass
        assert rs.derive_d3_keys(raw)["no_script_in_bundles"] is False, gap
    raw = d3_raw()
    raw["trust"] = trust_obs(output_model_trusted=False, cell_model_trusted=False, svg_count=0, live_res_count=0,
                             tabindex_count=0, svg_class_kept=False, svg_style_kept=False)
    keys = rs.derive_d3_keys(raw)
    assert keys["reopened_branch"] == "S2-B"
    assert rs.evaluate_unit_result(rs.UNIT_BY_ID["D3"], keys)[1] == ["reopened_branch"]
    raw = d3_raw()
    raw["reports"]["draw_assay"]["res"] = res(svg=0)
    assert rs.derive_d3_keys(raw)["svg_in_dom"] is False
    raw = d3_raw()
    raw["paints"] = {"liquid_fill": "rgb(0, 0, 0)", "liquid_count": 3}
    assert rs.derive_d3_keys(raw)["liquid_fill_computed"] == "rgb(0, 0, 0)"
    assert "liquid_fill_computed" in rs.evaluate_unit_result(rs.UNIT_BY_ID["D3"], rs.derive_d3_keys(raw))[1]
    raw = d3_raw()
    raw["paints"] = {"liquid_fill": None, "liquid_count": 0}
    assert "liquid_fill_computed" in rs.evaluate_unit_result(rs.UNIT_BY_ID["D3"], rs.derive_d3_keys(raw))[1]
    raw = d3_raw()
    raw["gate"] = [{"monitor": True, "seen": True}]
    assert rs.derive_d3_keys(raw)["persistence_gate_never_open"] is False


def test_count_scripts_in_outputs_reads_every_mime_of_every_output_case_insensitively(rs):
    def notebook(*datas: Any) -> dict[str, Any]:
        return {"cells": [{"cell_type": "code", "outputs": [{"output_type": "display_data", "data": d, "metadata": {}}
                                                             for d in datas]}]}

    assert rs.count_scripts_in_outputs(notebook({"text/html": "<p>x</p>", "text/plain": "x"})) == 0
    assert rs.count_scripts_in_outputs(notebook({"text/html": ["<p>", "<script>alert(1)</script>"]})) == 1
    assert rs.count_scripts_in_outputs(notebook({"text/html": "<SCRIPT src=x></SCRIPT>"}, {"text/plain": "<script"})) == 2
    assert rs.count_scripts_in_outputs({"cells": [{"cell_type": "code", "source": "<script", "outputs": []}]}) == 0, (
        "a script in SOURCE is not in a bundle"
    )
    assert rs.count_scripts_in_outputs({}) == 0 and rs.count_scripts_in_outputs(None) == 0


def test_saved_notebook_has_outputs_needs_an_html_bundle_not_just_a_file(rs):
    ok = {"cells": [{"cell_type": "code", "outputs": [{"output_type": "display_data", "data": {"text/html": "<svg/>"}}]}]}
    assert rs.saved_notebook_has_outputs(ok) is True
    assert rs.saved_notebook_has_outputs({"cells": [{"cell_type": "code", "outputs": []}]}) is False
    assert rs.saved_notebook_has_outputs({"cells": []}) is False and rs.saved_notebook_has_outputs(None) is False
    only_stream = {"cells": [{"cell_type": "code", "outputs": [{"output_type": "stream", "text": "x"}]}]}
    assert rs.saved_notebook_has_outputs(only_stream) is False


# -- AC-26 -----------------------------------------------------------------------------------------


def hc_raw() -> tuple[dict[str, Any], dict[str, Any]]:
    a = {
        "theme": HC_THEME, "summary_found": True, "summary_color": "rgb(255, 255, 255)", "font_token": "rgb(255, 255, 255)",
        "sheet_found": True, "sheet_fill": "rgb(0, 0, 0)", "layout_token": "rgb(0, 0, 0)", "inline_fill": "#FFFFFF",
        "praxis_css": "#73A9C2",
    }
    b = {"theme": HC_THEME, "layout_token": "rgb(0, 0, 0)", "praxis_css": "", "blocked": 1}
    return a, b


def test_hc_keys_positive_control(rs):
    assert rs.derive_hc_keys(*hc_raw()) == {"hc_text_color": True, "hc_sheet_fill": True, "hc_palette_untouched": True}
    assert rs.evaluate_unit_result(rs.UNIT_BY_ID["D4"], rs.derive_hc_keys(*hc_raw())) == ([], [])


def test_hc_text_color_negative_controls(rs):
    a, b = hc_raw()
    a["summary_color"] = "rgb(29, 41, 53)"  # the design's light-palette ink leaked into High Contrast
    assert rs.derive_hc_keys(a, b)["hc_text_color"] is False
    a, b = hc_raw()
    a["summary_found"] = False
    assert rs.derive_hc_keys(a, b)["hc_text_color"] is False
    a, b = hc_raw()
    a["font_token"] = ""
    assert rs.derive_hc_keys(a, b)["hc_text_color"] is False
    a, b = hc_raw()
    a["theme"] = "JupyterLab Dark"  # not the High Contrast theme
    assert rs.derive_hc_keys(a, b)["hc_text_color"] is False


def test_hc_sheet_fill_negative_controls(rs):
    a, b = hc_raw()
    a["sheet_fill"] = "rgb(255, 255, 255)"  # the inline light sheet, unmapped
    assert rs.derive_hc_keys(a, b)["hc_sheet_fill"] is False
    a, b = hc_raw()
    a["sheet_found"] = False
    assert rs.derive_hc_keys(a, b)["hc_sheet_fill"] is False
    a, b = hc_raw()
    a["layout_token"] = a["sheet_fill"] = "rgb(255, 255, 255)"  # a match that the inline palette alone explains
    assert rs.derive_hc_keys(a, b)["hc_sheet_fill"] is False


def test_hc_palette_untouched_needs_a_real_block_and_equal_tokens(rs):
    a, b = hc_raw()
    b["layout_token"] = "rgb(1, 1, 1)"  # Praxis CSS changed the theme's own token
    assert rs.derive_hc_keys(a, b)["hc_palette_untouched"] is False
    a, b = hc_raw()
    b["praxis_css"] = "#73A9C2"  # the stylesheet was NOT blocked: the comparison would be vacuous
    assert rs.derive_hc_keys(a, b)["hc_palette_untouched"] is False
    a, b = hc_raw()
    b["blocked"] = 0  # the route never fired
    assert rs.derive_hc_keys(a, b)["hc_palette_untouched"] is False
    a, b = hc_raw()
    a["praxis_css"] = ""  # Praxis CSS never loaded in the measured context
    assert rs.derive_hc_keys(a, b)["hc_palette_untouched"] is False
    a, b = hc_raw()
    b["theme"] = "JupyterLab Dark"
    assert rs.derive_hc_keys(a, b)["hc_palette_untouched"] is False
    a, b = hc_raw()
    a["layout_token"] = b["layout_token"] = ""
    assert rs.derive_hc_keys(a, b)["hc_palette_untouched"] is False


def test_hex_to_rgb_converts_the_inline_palette_attribute(rs):
    assert rs.hex_to_rgb("#FFFFFF") == "rgb(255, 255, 255)" and rs.hex_to_rgb("#73a9c2") == MOONSTONE_LIVE
    assert rs.hex_to_rgb("none") is None and rs.hex_to_rgb(None) is None and rs.hex_to_rgb("#FFF") is None


# --------------------------------------------------------------------------- #
# The small pure helpers: bounded polling, the restart status vocabulary, the blocking route
# --------------------------------------------------------------------------- #


def test_poll_until_returns_the_first_reading_that_holds_and_never_sleeps_past_the_deadline(rs):
    now = [0.0]
    slept: list[float] = []

    def sleep(s: float) -> None:
        slept.append(s)
        now[0] += s

    reads = iter([1, 2, 3, 4])
    value, ok = rs.poll_until(lambda: next(reads), lambda v: v == 3, timeout_s=5.0, interval_s=0.5,
                              clock=lambda: now[0], sleep=sleep)
    assert (value, ok) == (3, True) and slept == [0.5, 0.5]
    now[0] = 0.0
    slept.clear()
    value, ok = rs.poll_until(lambda: "never", lambda v: False, timeout_s=2.0, interval_s=0.5,
                              clock=lambda: now[0], sleep=sleep)
    assert (value, ok) == ("never", False), "the LAST reading comes back with False"
    assert sum(slept) <= 2.0 + 0.5, "bounded by the deadline"


def test_poll_until_reads_once_even_with_a_zero_timeout(rs):
    seen: list[int] = []
    value, ok = rs.poll_until(lambda: seen.append(1) or 7, lambda v: v == 7, timeout_s=0.0, clock=lambda: 0.0,
                              sleep=lambda s: None)
    assert (value, ok) == (7, True) and seen == [1]


@pytest.mark.parametrize("statuses,done", [
    (["restarting", "starting", "idle"], True),
    (["restarting", "busy", "idle"], True),
    (["autorestarting", "idle"], True),
    (["starting", "idle"], True),
    (["idle"], False),  # never restarted: idle before the restart began proves nothing
    (["restarting", "starting"], False),
    (["restarting", "idle", "busy"], False),  # not idle at the end
    ([], False),
])
def test_restart_finished_needs_a_restart_status_then_idle(rs, statuses, done):
    assert rs.restart_finished(statuses) is done


def test_restart_status_vocabulary_is_the_one_the_shell_listens_for(rs):
    assert set(rs.RESTART_STATUSES) == {"starting", "restarting", "autorestarting"}


def test_the_block_handler_records_and_aborts_the_request(rs):
    blocked: list[str] = []

    class Req:
        url = "http://127.0.0.1:1/praxis/assets/theme/praxis-theme.css"

    class Route:
        request = Req()
        aborted = False

        def abort(self) -> None:
            self.aborted = True

    route = Route()
    rs.make_block_handler(blocked)(route)
    assert blocked == [Req.url] and route.aborted is True
    assert rs.THEME_CSS_GLOB.endswith("praxis-theme.css*") and "assets/theme" in rs.THEME_CSS_GLOB


# --------------------------------------------------------------------------- #
# The B10 in-page helpers (DISPLAY_CHECK_OUTPUT_JS), under a JS engine with a fake DOM
# --------------------------------------------------------------------------- #

FAKE_DOM_JS = textwrap.dedent(
    r"""
    globalThis.window = globalThis;
    const attrRe = /\[([\w-]+)(?:="([^"]*)")?\]/g;
    function parseCompound(s) {
      const m = /^([a-zA-Z][\w-]*)?((?:\.[\w-]+|\[[^\]]+\])*)$/.exec(s);
      if (!m) throw new Error("unsupported selector: " + s);
      const classes = [...(m[2].matchAll(/\.([\w-]+)/g))].map((x) => x[1]);
      const attrs = [...(m[2].matchAll(attrRe))].map((x) => [x[1], x[2]]);
      return { tag: m[1] ? m[1].toLowerCase() : null, classes, attrs };
    }
    class El {
      constructor(tag, attrs = {}, kids = [], text = "") {
        this.localName = tag.toLowerCase();
        this.tagName = tag.toUpperCase();
        this.attrs = { ...attrs };
        this.children = [];
        this.parentNode = null;
        this._text = text;
        this._style = {};
        this._vars = {};
        this.style = {};
        this.focusable = true;
        this.visible = true;
        this.scrolled = [];
        for (const k of kids) this.append(k);
      }
      append(k) { k.parentNode = this; this.children.push(k); return k; }
      appendChild(k) { return this.append(k); }
      insertBefore(k, ref) {
        const at = this.children.indexOf(ref);
        k.parentNode = this;
        this.children.splice(at < 0 ? this.children.length : at, 0, k);
        return k;
      }
      getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
      hasAttribute(k) { return k in this.attrs; }
      setAttribute(k, v) { this.attrs[k] = String(v); }
      get classList() { const set = new Set((this.attrs.class || "").split(/\s+/).filter(Boolean)); return { contains: (c) => set.has(c) }; }
      get dataset() {
        const d = {};
        for (const [k, v] of Object.entries(this.attrs)) if (k.startsWith("data-")) d[k.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = v;
        return d;
      }
      get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
      matches(sel) {
        return sel.split(",").some((part) => {
          const c = parseCompound(part.trim());
          if (c.tag && this.localName !== c.tag) return false;
          if (!c.classes.every((k) => this.classList.contains(k))) return false;
          return c.attrs.every(([k, v]) => this.hasAttribute(k) && (v === undefined || this.getAttribute(k) === v));
        });
      }
      walk() { const out = []; for (const c of this.children) { out.push(c, ...c.walk()); } return out; }
      querySelectorAll(sel) { return this.walk().filter((e) => e.matches(sel)); }
      querySelector(sel) { return this.querySelectorAll(sel)[0] ?? null; }
      closest(sel) { let e = this; while (e) { if (e.matches(sel)) return e; e = e.parentNode; } return null; }
      contains(other) { let e = other; while (e) { if (e === this) return true; e = e.parentNode; } return false; }
      focus() { if (this.focusable && !globalThis.__refuseFocus) globalThis.document.activeElement = this; }
      getClientRects() { return this.visible ? [{}] : []; }
      scrollIntoView(o) { this.scrolled.push(o); }
      remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter((c) => c !== this); }
    }
    const body = new El("body");
    const root = new El("html", {}, [body]);
    globalThis.document = {
      activeElement: null, body, documentElement: root,
      querySelectorAll: (s) => body.querySelectorAll(s),
      querySelector: (s) => body.querySelector(s),
      createElement: (t) => new El(t),
      contains: (n) => body.contains(n),
    };
    const TOKENS = {};
    globalThis.getComputedStyle = (el) => {
      const out = { ...el._style, getPropertyValue: (n) => el._vars[n] ?? "" };
      for (const [prop, val] of Object.entries(el.style)) {
        const m = /^var\((--[\w-]+)\)$/.exec(val);
        if (m) out[prop] = TOKENS[m[1]] ?? "";
      }
      return out;
    };
    const ex = (tag, attrs, kids, text) => new El(tag, attrs, kids, text);
    // an indirect eval keeps its const/class declarations local: publish what the driver uses
    Object.assign(globalThis, { ex, El, body, root, TOKENS });
    """
)

OUTPUT_JS_DRIVER = textwrap.dedent(
    r"""
    const fs = require("fs");
    const src = fs.readFileSync(process.env.DC_OUTPUT_JS, "utf8");
    const HEADER = fs.readFileSync(process.env.DC_FAKE_DOM, "utf8");
    (0, eval)(HEADER);
    const CHANGED = "Changed since, see deck panel.";
    const HOSTILE = '<b>&"\'x';
    const stampA = { v: 1, kind: "plate", resource: "assay", rev: 3, session: "sess-1", exec: 8 };
    const stampB = { v: 1, kind: "tiprack", resource: HOSTILE, rev: 1, session: "sess-1", exec: 9 };
    const jsonOf = (o) => o;
    const mkOutputs = (jsons, sets) => ({
      length: jsons.length,
      get: (j) => ({ toJSON: () => jsons[j], trusted: jsons[j].__trusted ?? true }),
      set: (j, v) => { sets.push([j, v]); },
    });
    const sets = [];
    const svgFor = (name, extra = [], tab = "0") => ex("svg", { viewBox: "0 0 1 1", style: "min-width:400px" }, [
      ex("g", { "data-praxis-res": name, role: "img", tabindex: tab, "aria-label": "SENTENCE" }, [
        ex("rect", { class: "sv-plate", fill: "#FFFFFF" }),
        ex("path", { class: "sv-liquid", fill: "#73A9C2" }),
        ...extra,
      ]),
    ]);
    const outputNode = (kids) => ex("div", { class: "jp-OutputArea-child" }, [
      ex("div", { class: "jp-OutputArea-output", "data-mime-type": "text/html" }, kids),
    ]);
    const mkCell = ({ count, state, outputs, kids, source }) => {
      const node = ex("div", { class: "jp-CodeCell", "data-praxis-cell-state": state }, [ex("div", { class: "jp-OutputArea" }, kids)]);
      const jsons = outputs;
      return {
        node,
        model: { executionCount: count, executionState: "idle", outputs: mkOutputs(jsons, sets), trusted: true,
                 sharedModel: { getSource: () => source || "" } },
        outputArea: { widgets: kids.map((k) => ({ node: k })) },
      };
    };
    const html1 = "<p>µ</p>";   // 8 UTF-16 units, 9 UTF-8 bytes
    const notice = (t) => ex("div", { class: "praxis-stale", "data-praxis-stale": "changed" }, [], t);
    const summary = ex("p", { class: "praxis-summary" }, [], "24 of 96 wells hold liquid");
    const assayFig = svgFor("assay");
    const cells = [
      // 0: a drawing cell (S3-A carrier), marked once
      mkCell({ count: 5, state: "ran", outputs: [
        { output_type: "execute_result", data: { "text/html": html1, "text/plain": "SENTENCE" }, metadata: { praxis: stampA } }],
        kids: [outputNode([ex("div", { class: "praxis-out" }, [assayFig, summary]), notice(CHANGED)])] }),
      // 1: an error cell: panel then the error output
      mkCell({ count: 6, state: "error", outputs: [
        { output_type: "display_data", data: { "text/html": "<div/>", "text/plain": "panel" }, metadata: { "text/html": { praxis: { v: 1, kind: "error", resource: null, rev: null, session: "sess-1", exec: 6 } } } },
        { output_type: "error", ename: "TooLittleLiquidError", evalue: "x", traceback: [] }],
        kids: [outputNode([ex("div", { class: "praxis-out praxis-error" }, [
          ex("p", { class: "praxis-error__title" }, [], "Not enough liquid in assay A1:H1."),
          ex("p", { class: "praxis-error__title" }, [], "PyLabRobot raised X")])]), ex("div", { class: "jp-OutputArea-child" }, [])] }),
      // 2: a plain ValueError (no panel)
      mkCell({ count: 7, state: "error", outputs: [{ output_type: "error", ename: "ValueError", evalue: "plain", traceback: [] }],
        kids: [ex("div", { class: "jp-OutputArea-child" }, [ex("pre", {}, [], "ValueError: plain")])] }),
      // 3: never run
      mkCell({ count: null, state: "not-run", outputs: [], kids: [] }),
      // 4: a tip rack with a hostile resource name, two notices (a duplicated mark) and the S3-B carrier
      mkCell({ count: 8, state: "ran", outputs: [
        { output_type: "display_data", data: { "text/html": "<i/>", "text/plain": "T" }, metadata: { "text/html": { praxis: stampB } } }],
        kids: [outputNode([ex("div", { class: "praxis-out" }, [svgFor(HOSTILE)]), notice(CHANGED), notice(CHANGED)])] }),
      // 5: an untrusted, sanitized reopen: no svg, no data-*, chosen mime text/html, the summary survives
      mkCell({ count: null, state: "ran", outputs: [
        { output_type: "display_data", data: { "text/html": "<p/>", "text/plain": "SENTENCE" }, metadata: { praxis: stampA }, __trusted: false }],
        kids: [outputNode([ex("p", { class: "praxis-summary" }, [], "SENTENCE")])] }),
    ];
    cells[5].model.trusted = false;
    cells.push(mkCell({ count: 1, state: "ran", outputs: [], kids: [outputNode([svgFor("notab", [], "-1")])] }));
    const listeners = [];
    const panel = {
      content: { widgets: cells, model: { cells: { length: cells.length, get: (i) => cells[i].model }, trusted: true }, node: ex("div") },
      sessionContext: { statusChanged: { connect: (fn) => listeners.push(fn) }, session: { kernel: { status: "idle" } } },
      context: { model: { dirty: false } },
    };
    body.append(panel.content.node);
    for (const c of cells) body.append(c.node);
    const known = new Set(["kernelmenu:restart"]);
    window.jupyterapp = { shell: { currentWidget: panel }, commands: { hasCommand: (id) => known.has(id) } };
    (0, eval)(src);
    const dc = window.__praxisDisplayCheck;
    const out = {};
    out.stamp_a = dc.stampOf({ metadata: { praxis: stampA } });
    out.stamp_b = dc.stampOf({ metadata: { "text/html": { praxis: stampB } } });
    out.stamp_none = dc.stampOf({ metadata: {} }) ?? null;
    out.stamp_null_first = dc.stampOf({ metadata: { praxis: null, "text/html": { praxis: stampA } } });
    out.r0 = dc.report({ i: 0, res: "assay" });
    out.r1 = dc.report({ i: 1, res: null });
    out.r2 = dc.report({ i: 2, res: null });
    out.r3 = dc.report({ i: 3, res: null });
    out.r4 = dc.report({ i: 4, res: HOSTILE });
    out.r4_miss = dc.report({ i: 4, res: "assay" });
    out.fig = dc.figure({ i: 0, res: "assay" });
    out.fig_miss = dc.figure({ i: 0, res: "nope" });
    out.paints_before = dc.paints({ i: 0, res: "assay" });
    // paints: seed computed styles
    const plate = cells[0].node.querySelector(".sv-plate"), liquid = cells[0].node.querySelector('path[fill="#73A9C2"]');
    plate._style.fill = "rgb(0, 0, 0)";
    liquid._style.fill = "rgb(115, 169, 194)";
    summary._style.color = "rgb(255, 255, 255)";
    out.paints = dc.paints({ i: 0, res: "assay" });
    TOKENS["--jp-layout-color0"] = "rgb(0, 0, 0)";
    TOKENS["--jp-content-font-color0"] = "rgb(255, 255, 255)";
    out.tok_bg = dc.probeColor({ prop: "backgroundColor", token: "--jp-layout-color0" });
    out.tok_color = dc.probeColor({ prop: "color", token: "--jp-content-font-color0" });
    out.tok_unknown = dc.probeColor({ prop: "color", token: "--nope" });
    out.css_before = dc.praxisCss();
    root._vars["--praxis-moonstone"] = " #73A9C2 ";
    out.css_after = dc.praxisCss();
    // the keyboard helpers: a throwaway probe is inserted right before the figure's svg and focused
    const figG = assayFig.children[0];
    out.probe = dc.focusProbe({ i: 0, res: "assay" });
    const probeEl = document.activeElement;
    out.active_is_probe = probeEl && probeEl.hasAttribute("data-dcheck-probe");
    out.probe_precedes_svg = probeEl.parentNode.children.indexOf(probeEl) + 1 === probeEl.parentNode.children.indexOf(assayFig);
    out.is_on_probe = dc.activeIs({ i: 0, res: "assay" });
    figG.focus();
    out.is_after_tab = dc.activeIs({ i: 0, res: "assay" });
    out.removed = dc.removeProbe();
    out.removed_again = dc.removeProbe();
    out.probe_gone = document.querySelectorAll("[data-dcheck-probe]").length;
    out.probe_miss = dc.focusProbe({ i: 0, res: "nope" });
    out.probe_miss_left_nothing = document.querySelectorAll("[data-dcheck-probe]").length;
    // a figure whose own tabindex is -1 is not what Tab reaches next
    out.probe_notab = dc.focusProbe({ i: 6, res: "notab" });
    dc.removeProbe();
    // an element that refuses focus: ok is false, whatever else is true
    globalThis.__refuseFocus = true;
    out.probe_stuck = dc.focusProbe({ i: 0, res: "assay" });
    globalThis.__refuseFocus = false;
    dc.removeProbe();
    out.live_none = dc.liveText();
    const live = ex("div", { "aria-live": "polite", "data-praxis-live": "" }, [], "assay A1: 50 \u00b5L");
    body.append(live);
    out.live = dc.liveText();
    figG.append(ex("rect", { class: "praxis-focus-ring" }));
    out.rings = dc.ringCount({ i: 0, res: "assay" });
    // scroll, rerender
    out.scroll = dc.scrollTo({ i: 0, block: "center" });
    out.scrolled = cells[0].node.scrolled;
    out.rerender = dc.rerender({ i: 0, j: 0 });
    out.rerender_bad = dc.rerender({ i: 3, j: 0 });
    out.sets = sets.map(([j, v]) => [j, v.output_type]);
    // trust reads
    out.trust0 = dc.trust({ i: 0 });
    out.trust5 = dc.trust({ i: 5 });
    out.trust3 = dc.trust({ i: 3 });
    // status log, gate, dialog, commands, dirty
    dc.startStatusLog();
    for (const s of ["restarting", "starting", "idle"]) listeners.forEach((fn) => fn(null, s));
    out.statuses = dc.statusLog();
    out.has_restart = dc.hasCommand("kernelmenu:restart");
    out.has_nope = dc.hasCommand("nope:nope");
    out.dirty = dc.dirty();
    out.dialog = dc.dialogOpen();
    body.append(ex("div", { class: "jp-Dialog" }));
    out.dialog_open = dc.dialogOpen();
    globalThis.sessionStorage = { getItem: (k) => (k === process.env.GATE_KEY ? "1" : null) };
    window.__praxisFirstSaveMonitor = true;
    out.gate_seen_by_storage = dc.gate();
    globalThis.sessionStorage = { getItem: () => null };
    out.gate_quiet = dc.gate();
    delete window.__praxisFirstSaveMonitor;
    out.gate_dead = dc.gate();
    console.log(JSON.stringify(out));
    """
)


def _run_output_js(rs: Any, tmp_path: Path) -> dict[str, Any]:
    (tmp_path / "out.js").write_text(rs.DISPLAY_CHECK_OUTPUT_JS)
    (tmp_path / "fake_dom.js").write_text(FAKE_DOM_JS)
    (tmp_path / "driver.js").write_text(OUTPUT_JS_DRIVER)
    proc = subprocess.run(
        [JS_ENGINE, str(tmp_path / "driver.js")],
        env={**os.environ, "DC_OUTPUT_JS": str(tmp_path / "out.js"), "DC_FAKE_DOM": str(tmp_path / "fake_dom.js"),
             "GATE_KEY": rs.PERSISTENCE_GATE_SEEN_KEY},
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-3000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def js_out(rs, tmp_path_factory):
    if JS_ENGINE is None:
        pytest.skip("no node or bun on PATH")
    return _run_output_js(rs, tmp_path_factory.mktemp("output_js"))


def test_stamp_of_is_the_d2_expression_and_reads_both_carriers(js_out):
    assert js_out["stamp_a"]["kind"] == "plate", "S3-A: metadata.praxis"
    assert js_out["stamp_b"]["kind"] == "tiprack", 'S3-B: metadata["text/html"].praxis'
    assert js_out["stamp_none"] is None
    assert js_out["stamp_null_first"]["kind"] == "plate", "?? falls through on null exactly like the shell's stampOf"


def test_the_harness_evaluates_the_shells_stamp_expression_verbatim(rs):
    assert 'output.metadata?.praxis ?? output.metadata?.["text/html"]?.praxis' in rs.DISPLAY_CHECK_OUTPUT_JS


def test_report_reads_the_model_outputs_and_the_drawing_node(js_out):
    r0 = js_out["r0"]
    assert (r0["state"], r0["execution_count"], r0["found"]) == ("ran", 5, True)
    (o,) = r0["outputs"]
    assert o["output_type"] == "execute_result" and sorted(o["mimes"]) == ["text/html", "text/plain"]
    assert o["html_bytes"] == 9, "UTF-8 BYTES of the text/html (the cap is bytes, not characters)"
    assert o["plain"] == "SENTENCE" and o["stamp"]["resource"] == "assay" and o["index"] == 0
    assert r0["res"] == {"found": True, "svg_count": 1, "changed_notices": 1, "earlier_notices": 0,
                         "text_length": r0["res"]["text_length"]}
    assert r0["res"]["text_length"] > 0


def test_report_counts_a_duplicated_mark_and_matches_a_hostile_name_without_a_selector(js_out):
    r4 = js_out["r4"]
    assert r4["res"]["found"] is True and r4["res"]["changed_notices"] == 2, "exactly-once needs the COUNT"
    assert r4["outputs"][0]["stamp"]["kind"] == "tiprack", "the S3-B carrier is read through stampOf"
    assert js_out["r4_miss"]["res"]["found"] is False, "another resource's name finds nothing"


def test_report_reads_the_error_panel_title_and_the_absence_of_one(js_out):
    r1, r2 = js_out["r1"], js_out["r2"]
    assert r1["error"] == {"titles": ["Not enough liquid in assay A1:H1.", "PyLabRobot raised X"], "praxis_error_nodes": 1}
    assert [o["output_type"] for o in r1["outputs"]] == ["display_data", "error"]
    assert r1["outputs"][1]["ename"] == "TooLittleLiquidError" and r1["state"] == "error"
    assert r2["error"] == {"titles": [], "praxis_error_nodes": 0}
    assert r2["outputs"][0]["ename"] == "ValueError"
    assert r1["res"] is None, "no resource name asked for: no drawing lookup"


def test_report_of_a_never_run_cell_has_no_count_and_no_outputs(js_out):
    r3 = js_out["r3"]
    assert r3["execution_count"] is None and r3["outputs"] == [] and r3["state"] == "not-run"


def test_figure_reads_role_tabindex_aria_label_and_svg_ancestry(js_out):
    assert js_out["fig"] == {"found": True, "tag": "g", "role": "img", "tabindex": "0", "aria_label": "SENTENCE", "in_svg": True}
    assert js_out["fig_miss"]["found"] is False


def test_paints_read_computed_fill_and_colour_of_the_sheet_liquid_and_summary(js_out):
    before = js_out["paints_before"]
    assert before["sheet_found"] is True and before["liquid_count"] == 1 and before["summary_found"] is True
    assert before["sheet_fill"] is None or before["sheet_fill"] == "", "nothing computed yet: never invented"
    p = js_out["paints"]
    assert p["sheet_fill"] == "rgb(0, 0, 0)" and p["inline_fill"] == "#FFFFFF"
    assert p["liquid_fill"] == "rgb(115, 169, 194)" and p["liquid_attr"] == "#73A9C2" and p["liquid_count"] == 1
    assert p["summary_color"] == "rgb(255, 255, 255)" and p["svg_count"] == 1


def test_probe_color_resolves_a_theme_token_through_a_throwaway_element(js_out):
    assert js_out["tok_bg"] == "rgb(0, 0, 0)" and js_out["tok_color"] == "rgb(255, 255, 255)"
    assert js_out["tok_unknown"] in ("", None)


def test_praxis_css_is_read_from_the_root_custom_property(js_out):
    assert js_out["css_before"] == "" and js_out["css_after"] == "#73A9C2"


def test_focus_probe_puts_a_throwaway_focusable_right_before_the_figure_and_predicts_tabs_next_stop(js_out):
    p = js_out["probe"]
    assert p["ok"] is True and p["next_is_figure"] is True and p["next_tag"] == "g"
    assert js_out["active_is_probe"] is True and js_out["probe_precedes_svg"] is True
    assert js_out["is_on_probe"]["is_figure"] is False and js_out["is_on_probe"]["active_res"] is None
    assert js_out["is_after_tab"]["is_figure"] is True and js_out["is_after_tab"]["active_res"] == "assay"


def test_the_probe_is_removed_and_leaves_nothing_behind(js_out):
    assert js_out["removed"] == 1 and js_out["removed_again"] == 0 and js_out["probe_gone"] == 0
    assert js_out["probe_miss"]["ok"] is False and js_out["probe_miss_left_nothing"] == 0, "no figure: no probe inserted"


def test_focus_probe_reports_a_figure_tab_would_not_reach_and_a_probe_that_refuses_focus(js_out):
    assert js_out["probe_notab"]["ok"] is True and js_out["probe_notab"]["next_is_figure"] is False, (
        "a figure with tabindex -1 is not the next tab stop: the prediction says so"
    )
    assert js_out["probe_stuck"]["ok"] is False, "an element that refuses focus leaves the focus elsewhere"


def test_live_text_and_ring_count(js_out):
    assert js_out["live_none"] is None and js_out["live"] == "assay A1: 50 µL" and js_out["rings"] == 1


def test_scroll_and_rerender_are_the_only_things_that_touch_the_page_or_model(js_out):
    assert js_out["scroll"] == {"ok": True} and js_out["scrolled"] == [{"block": "center"}]
    assert js_out["rerender"] == {"ok": True} and js_out["rerender_bad"]["ok"] is False
    assert js_out["sets"] == [[0, "execute_result"]], "the SAME output re-set: an async re-render, no new content"


def test_trust_reads_carry_what_the_branch_classifier_needs(js_out, rs):
    t0, t5, t3 = js_out["trust0"], js_out["trust5"], js_out["trust3"]
    assert (t0["rendered"], t0["output_model_trusted"], t0["cell_model_trusted"], t0["chosen_mime"]) == (True, True, True, "text/html")
    assert (t0["svg_count"], t0["live_res_count"], t0["tabindex_count"]) == (1, 1, 1)
    assert (t5["output_model_trusted"], t5["cell_model_trusted"], t5["svg_count"], t5["live_res_count"]) == (False, False, 0, 0)
    assert t5["summary_visible"] is True and t5["chosen_mime"] == "text/html"
    assert t3["rendered"] is False
    assert rs.classify_reopened_branch(t0) == "S2-T" and rs.classify_reopened_branch(t5) == "S2-B"
    assert rs.classify_reopened_branch(t3) == "unrendered"


def test_status_log_gate_dialog_commands_and_dirty(js_out):
    assert js_out["statuses"] == ["restarting", "starting", "idle"]
    assert js_out["has_restart"] is True and js_out["has_nope"] is False and js_out["dirty"] is False
    assert js_out["dialog"] is False and js_out["dialog_open"] is True
    assert js_out["gate_seen_by_storage"] == {"monitor": True, "seen": True}, "seen survives a reload via sessionStorage"
    assert js_out["gate_quiet"] == {"monitor": True, "seen": False}
    assert js_out["gate_dead"]["monitor"] is False


def test_output_js_reads_state_and_writes_only_two_things(rs):
    """Nothing here assigns to the product's DOM or fires a product command. The only writes: focus
    (``focusBefore``), a scroll, one same-value ``outputs.set`` (the sanctioned async re-render), the
    status subscription and a throwaway probe element."""
    js = rs.DISPLAY_CHECK_OUTPUT_JS
    assert "commands.execute" not in js, "commands are issued from Python, one named place"
    assert js.count(".outputs.set(") == 1 or js.count("outs.set(") == 1
    for forbidden in ("setSource", "sharedModel.set", "innerHTML", "removeAttribute", "dispatchEvent",
                      "data-praxis-test", "__praxis_test"):
        assert forbidden not in js, forbidden
    assert rs.PERSISTENCE_GATE_SEEN_KEY in js


# -- the context init scripts: the persistence ack AND the first-save monitor -------------------------

GATE_DRIVER = textwrap.dedent(
    r"""
    const fs = require("fs");
    globalThis.window = globalThis;
    const store = {};
    globalThis.sessionStorage = { setItem: (k, v) => { store[k] = v; }, getItem: (k) => store[k] ?? null };
    let dialog = { open: false, hasAttribute: (n) => n === "open" && dialog.open };
    globalThis.document = { querySelector: (s) => (s === "dialog#praxis-persistence-first-save" ? dialog : null) };
    const ticks = [];
    globalThis.setInterval = (fn, ms) => { ticks.push(fn); return ticks.length; };
    (0, eval)(fs.readFileSync(process.env.MONITOR_JS, "utf8"));
    const out = { monitor: window.__praxisFirstSaveMonitor === true, registered: ticks.length >= 1 };
    ticks.forEach((t) => t());
    out.seen_closed = !!window.__praxisFirstSaveSeen || store[process.env.GATE_KEY] === "1";
    dialog.open = true;
    ticks.forEach((t) => t());
    out.seen_open = !!window.__praxisFirstSaveSeen;
    out.stored = store[process.env.GATE_KEY];
    dialog = null;
    ticks.forEach((t) => t());  // an absent dialog must not throw
    console.log(JSON.stringify(out));
    """
)


@pytest.mark.skipif(JS_ENGINE is None, reason="no node or bun on PATH")
def test_first_save_monitor_sees_an_open_dialog_and_survives_its_absence(rs, tmp_path):
    (tmp_path / "monitor.js").write_text(rs.PERSISTENCE_GATE_MONITOR_INIT_SCRIPT)
    (tmp_path / "driver.js").write_text(GATE_DRIVER)
    proc = subprocess.run(
        [JS_ENGINE, str(tmp_path / "driver.js")],
        env={**os.environ, "MONITOR_JS": str(tmp_path / "monitor.js"), "GATE_KEY": rs.PERSISTENCE_GATE_SEEN_KEY},
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-2000:]
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out == {"monitor": True, "registered": True, "seen_closed": False, "seen_open": True, "stored": "1"}


def test_every_display_context_carries_the_ack_and_the_monitor_and_neither_adds_a_product_key(rs):
    scripts = rs.display_context_init_scripts()
    assert rs.PERSISTENCE_ACK_INIT_SCRIPT in scripts and rs.PERSISTENCE_GATE_MONITOR_INIT_SCRIPT in scripts
    assert rs.PERSISTENCE_ACK_INIT_SCRIPT in rs.display_context_init_scripts(neg=("drop-query",))
    assert "localStorage" not in rs.PERSISTENCE_GATE_MONITOR_INIT_SCRIPT, "the monitor writes no product key"
    assert rs.PERSISTENCE_GATE_SEEN_KEY.startswith("__") and "praxis-repl" not in rs.PERSISTENCE_GATE_SEEN_KEY


# --------------------------------------------------------------------------- #
# The scenarios' ORDER and key plumbing, against a scripted fake driver (no browser)
#
# ``FakeWorld`` is a stand-in for the harness's ``DisplayDriver`` (one Playwright page): a "good"
# browser by default, with one switch per fault. It lets the REAL scenario functions run end to
# end, so what is proved is the sequencing (setup before drawing, the aspirate after the keyboard
# reads, the restart before the re-run drawing cell, no cell run after the reload, the Run All in
# its own notebook and last) and that every listed key is produced and can flip. What the page
# actually shows is NOT proved here: that is B10b.
# --------------------------------------------------------------------------- #

DRAW_RES = {"draw-source": "source", "draw-assay": "assay", "draw-tips": "tips_300", "draw-deck": "deck", "redraw": "redraw"}
DRAW_KIND = {"draw-source": "plate", "draw-assay": "plate", "draw-tips": "tiprack", "draw-deck": "deck", "redraw": "plate"}
ERR_CELLS = {"e1", "e2", "e4", "e6"}


class FakeWorld:
    def __init__(self, rs: Any, notebook: dict[str, Any], **faults: Any) -> None:
        self.rs, self.faults = rs, faults
        self.log: list[Any] = []
        self.counts: dict[str, int] = {}
        self.cell_session: dict[str, str] = {}
        self.session = "sess-1"
        self.aspirated = self.redrawn = self.rerendered = self.scrolled = False
        self.next_count = 1
        self.focus = None
        self.live = ""
        self.ring = 0
        self.after_reload = False
        self.blocked: list[str] = []
        self.name = None
        self._open(notebook)

    def _open(self, notebook: dict[str, Any]) -> None:
        self.nb = notebook
        self.ids = [c["id"] for c in notebook["cells"]]

    # -- session ---------------------------------------------------------------------------------
    def open_lab(self) -> None:
        self.log.append("open_lab")

    def set_theme(self, name: str) -> None:
        self.log.append(("theme", name))
        self.theme = name

    def theme_name(self) -> str:
        return getattr(self, "theme", "JupyterLab Dark")

    def seed_and_open(self, name: str, notebook: dict[str, Any]) -> None:
        self.log.append(("open", name))
        self.name = name
        self._open(notebook)
        self.counts, self.cell_session = {}, {}  # a notebook has its own kernel

    def wait_kernel_idle(self) -> None:
        self.log.append("idle")

    # -- cells -------------------------------------------------------------------------------------
    def run_cell(self, index: int) -> None:
        cid = self.ids[index]
        self.log.append(("run", cid))
        if self.faults.get("never_runs") == cid:
            return
        self.counts[cid] = self.next_count
        self.next_count += 1
        self.cell_session[cid] = self.session
        if cid == "aspirate":
            self.aspirated = True
        if cid == "redraw":
            self.redrawn = True

    def _res(self, cid: str) -> dict[str, Any]:
        f = self.faults
        changed = 1 if (self.aspirated and cid in ("draw-source", "draw-deck") and not f.get("no_mark")) else 0
        if cid == "draw-source" and self.rerendered and f.get("mark_lost_on_rerender"):
            changed = 0
        if cid == "draw-source" and self.scrolled and f.get("double_mark_after_scroll"):
            changed = 2
        if cid == "draw-tips" and f.get("tips_marked") and self.aspirated:
            changed = 1
        earlier = 0
        if self.redrawn and self.cell_session.get(cid) != self.session and not f.get("no_earlier"):
            earlier = 1
        if cid == "redraw" and f.get("rerun_marked"):
            earlier = 1
        if self.after_reload:
            changed = earlier = 0
        svg = 0 if (f.get("sanitized") and self.after_reload) else 1
        return res(svg=svg, changed=changed, earlier=earlier)

    def report(self, index: int, res_name: Any = None) -> dict[str, Any]:
        cid = self.ids[index]
        n = self.counts.get(cid)
        if n is None:
            return report(count=None, state="not-run")
        if self.faults.get("setup_error") == cid:
            return report(count=n, state="error", outputs=[out(otype="error", mimes=(), html_bytes=None, ename="ImportError", evalue="boom")])
        if cid in DRAW_RES:
            plain = ASSAY_PLAIN if cid == "draw-assay" else "sentence"
            st = stamp(DRAW_KIND[cid], DRAW_RES[cid], session=self.cell_session[cid])
            size = 36_142 if cid == "draw-deck" else 9_000
            return report(count=n, outputs=[out(html_bytes=size, plain=plain, st=st)], res_=self._res(cid))
        if cid in ERR_CELLS:
            titles = [HEADINGS[cid]] if not self.faults.get("no_panel") else []
            return report(count=n, state="error", titles=titles, perr=len(titles), outputs=[
                out(otype="display_data", st=stamp("error", None, rev=None)),
                out(otype="error", mimes=(), html_bytes=None, ename="TooLittleLiquidError", index=1),
            ])
        if cid == "value-error":
            return report(count=n, state="error", perr=0, outputs=[out(otype="error", mimes=(), html_bytes=None, ename="ValueError")])
        if cid == "marker":
            return report(count=n)
        return report(count=n, outputs=[out(otype="stream", mimes=(), html_bytes=None, plain="ok")])

    def poll(self, read: Any, ok: Any, timeout_s: float) -> Any:
        value = read()
        return value, bool(ok(value))

    # -- keyboard --------------------------------------------------------------------------------------
    def figure(self, index: int, res_name: str) -> dict[str, Any]:
        return {"found": True, "role": "img", "in_svg": True, "aria_label": ASSAY_PLAIN, "tabindex": "0"}

    def focus_probe(self, index: int, res_name: str) -> dict[str, Any]:
        self.log.append("focus_probe")
        ok = not self.faults.get("no_predecessor")
        return {"ok": ok, "next_is_figure": ok, "next_tag": "g" if ok else None}

    def remove_probe(self) -> int:
        self.log.append("remove_probe")
        return 1

    def windowing(self) -> Any:
        return "contentVisibility"

    def press(self, key: str) -> None:
        self.log.append(("press", key))
        f = self.faults
        if key == "Tab" and not f.get("no_predecessor"):
            self.focus, self.live, self.ring = "figure", "assay A1: 50 µL", 1
        elif key == "ArrowRight" and self.focus == "figure" and not f.get("arrow_dead"):
            self.live = "assay A2: 100 µL"
        elif key == "Escape":
            self.ring = 1 if f.get("ring_stays") else 0
            if f.get("escape_blurs"):
                self.focus = None

    def settle(self, ms: float) -> None:
        self.log.append(("settle", ms))

    def live_text(self) -> Any:
        return self.live or None

    def active_is_figure(self, index: int, res_name: str) -> bool:
        return self.focus == "figure"

    def ring_count(self, index: int, res_name: str) -> int:
        return self.ring

    # -- staleness ---------------------------------------------------------------------------------------
    def scroll_to(self, index: int, block: str = "center") -> None:
        self.log.append(("scroll", self.ids[index], block))
        self.scrolled = True

    def rerender(self, index: int, j: int) -> bool:
        self.log.append(("rerender", self.ids[index], j))
        self.rerendered = True
        return not self.faults.get("rerender_fails")

    def save_and_read(self, name: str) -> dict[str, Any]:
        self.log.append(("save", name))
        if self.faults.get("save_fails"):
            return {"ok": False, "content": None}
        html = "<svg></svg>" + ("Changed since, see deck panel." if self.faults.get("persist_mark") else "")
        if self.faults.get("script_in_bundle"):
            html += "<script>1</script>"
        cell = {"cell_type": "code", "outputs": [{"output_type": "display_data", "data": {"text/html": html}}]}
        return {"ok": True, "content": {"cells": [cell]}}

    def restart_kernel(self) -> dict[str, Any]:
        self.log.append("restart")
        if self.faults.get("restart_fails"):
            raise self.rs.DisplayCheckError("the kernel never came back")
        self.session = "sess-1" if self.faults.get("same_session") else "sess-2"
        return {"via": "kernelmenu:restart", "dialog_seen": True, "statuses": ["restarting", "starting", "idle"]}

    def run_all(self) -> None:
        self.log.append("run_all")
        for cid in ("assemble", "transfers", "pickup", "e1") + (("marker",) if self.faults.get("runall_continues") else ()):
            self.counts[cid] = self.next_count
            self.next_count += 1

    # -- trust, paints, gate, reload ----------------------------------------------------------------------
    def trust(self, index: int) -> dict[str, Any]:
        if self.faults.get("sanitized"):
            return trust_obs(output_model_trusted=False, cell_model_trusted=False, svg_count=0, live_res_count=0,
                             tabindex_count=0, svg_class_kept=False, svg_style_kept=False)
        return trust_obs()

    def paints(self, index: int, res_name: str) -> dict[str, Any]:
        hc = self.theme_name() == HC_THEME
        blocked = bool(self.blocked_context)
        return {
            "summary_found": True, "summary_color": "rgb(255, 255, 255)", "sheet_found": True,
            "sheet_fill": "rgb(0, 0, 0)" if hc else "rgb(255, 255, 255)", "inline_fill": "#FFFFFF",
            "liquid_count": 3, "liquid_fill": self.faults.get("liquid_fill", MOONSTONE_LIVE), "liquid_attr": "#73A9C2",
            "svg_count": 1, "blocked": blocked,
        }

    blocked_context = False

    def probe_color(self, prop: str, token: str) -> str:
        if token == "--jp-content-font-color0":
            return "rgb(255, 255, 255)"
        return self.faults.get("layout_token_blocked", "rgb(0, 0, 0)") if self.blocked_context else "rgb(0, 0, 0)"

    def praxis_css(self) -> str:
        return "" if self.blocked_context else "#73A9C2"

    def gate(self) -> dict[str, Any]:
        return {"monitor": not self.faults.get("no_monitor"), "seen": bool(self.faults.get("gate_seen"))}

    def close_panel(self, name: str) -> None:
        self.log.append(("close", name))

    def reload_and_open(self, name: str, notebook: dict[str, Any]) -> None:
        self.log.append("reload")
        self.after_reload = True
        self._open(notebook)
        self.name = name

    def blocked_count(self) -> int:
        return 0 if self.faults.get("route_never_fires") else 1


def _events(world: FakeWorld) -> list[Any]:
    return world.log


def _pos(log: list[Any], item: Any) -> int:
    return log.index(item)


def _first(log: list[Any], pred: Any) -> int:
    return next(i for i, e in enumerate(log) if pred(e))


def _run_d2(rs: Any, nb: dict[str, Any], **faults: Any) -> tuple[dict[str, Any], FakeWorld]:
    world = FakeWorld(rs, nb, **faults)
    keys = rs.run_d2(world, nb)
    return keys, world


def test_d2_positive_control_a_good_browser_holds_every_listed_key(rs, nb):
    keys, world = _run_d2(rs, nb)
    listed = [k for k in D2_KEYS if k != "pageerrors"]
    assert all(k in keys for k in listed), [k for k in listed if k not in keys]
    unit = rs.UNIT_BY_ID["D2"]
    assert rs.evaluate_unit_result(unit, dict(keys, pageerrors=[])) == ([], []), keys


def test_d2_runs_setup_then_draws_then_the_keyboard_then_the_aspirate_then_the_errors(rs, nb):
    _, w = _run_d2(rs, nb)
    runs = [e[1] for e in w.log if isinstance(e, tuple) and e[0] == "run"]
    main = runs[: runs.index("marker")] if "marker" in runs else runs
    order = ["boot", "assemble", "transfers", "pickup", "draw-source", "draw-assay", "draw-tips", "draw-deck",
             "aspirate", "e1", "e2", "e4", "e6", "value-error"]
    idx = [main.index(c) for c in order]
    assert idx == sorted(idx), main
    tab = _first(w.log, lambda e: e == ("press", "Tab"))
    aspirate = _first(w.log, lambda e: e == ("run", "aspirate"))
    assert tab < aspirate, "the keyboard reads use the drawn assay before anything changes"
    assert _pos(w.log, ("press", "Tab")) < _pos(w.log, ("press", "ArrowRight")) < _pos(w.log, ("press", "Escape"))
    assert _pos(w.log, "focus_probe") < _pos(w.log, ("press", "Tab")) < _pos(w.log, "remove_probe")
    assert _pos(w.log, ("press", "Escape")) < _pos(w.log, "remove_probe"), "the probe stays until the keys are read"


def test_d2_never_runs_run_all_on_the_main_notebook_and_does_it_last_in_its_own_notebook(rs, nb):
    keys, w = _run_d2(rs, nb)
    opens = [e for e in w.log if isinstance(e, tuple) and e[0] == "open"]
    assert opens[0] == ("open", rs.DISPLAY_NOTEBOOK_NAME) and opens[-1] == ("open", rs.RUNALL_NOTEBOOK_NAME)
    assert w.log.count("run_all") == 1
    run_all = _pos(w.log, "run_all")
    assert _pos(w.log, opens[-1]) < run_all and run_all == max(i for i, e in enumerate(w.log) if e == "run_all")
    after_pair_open = w.log[_pos(w.log, opens[-1]):]
    assert not [e for e in after_pair_open if isinstance(e, tuple) and e[0] == "run"], (
        "cells of the pair are run by Run All, never one at a time"
    )
    before_pair = w.log[: _pos(w.log, opens[-1])]
    assert "run_all" not in before_pair, "Run All never touches the main notebook's error cells"


def test_d2_restarts_the_kernel_reruns_boot_then_a_self_contained_drawing_cell(rs, nb):
    _, w = _run_d2(rs, nb)
    r = _pos(w.log, "restart")
    later = [e[1] for e in w.log[r:] if isinstance(e, tuple) and e[0] == "run"]
    assert later[:2] == ["boot", "redraw"], later
    earlier_runs = [e[1] for e in w.log[:r] if isinstance(e, tuple) and e[0] == "run"]
    assert "redraw" not in earlier_runs and "value-error" in earlier_runs
    assert _pos(w.log, ("save", rs.DISPLAY_NOTEBOOK_NAME)) < r, "the persisted-mark check happens before the restart"


def test_d2_saves_first_then_scrolls_away_and_back_and_forces_a_rerender(rs, nb):
    """The persisted-mark check runs while the mark is known to be in the DOM, before any disturbance,
    so a lost mark cannot also read as 'not persisted'."""
    _, w = _run_d2(rs, nb)
    away = _first(w.log, lambda e: isinstance(e, tuple) and e[0] == "scroll" and e[1] == "marker")
    back = max(i for i, e in enumerate(w.log) if isinstance(e, tuple) and e[0] == "scroll" and e[1] == "draw-source")
    rerender = _first(w.log, lambda e: isinstance(e, tuple) and e[0] == "rerender" and e[1] == "draw-source")
    save = _pos(w.log, ("save", rs.DISPLAY_NOTEBOOK_NAME))
    assert _pos(w.log, ("run", "aspirate")) < save < away < back < rerender < _pos(w.log, "restart")


def test_d2_a_failing_setup_cell_is_an_error_finding_not_a_misleading_key(rs, nb):
    for cid in ("boot", "assemble", "transfers", "pickup"):
        with pytest.raises(rs.DisplayCheckError) as exc:
            _run_d2(rs, nb, setup_error=cid)
        assert cid in str(exc.value) and "ImportError" in str(exc.value)


def test_d2_a_restart_that_fails_raises_instead_of_passing_the_session_keys(rs, nb):
    with pytest.raises(rs.DisplayCheckError):
        _run_d2(rs, nb, restart_fails=True)


@pytest.mark.parametrize("fault,failing", [
    ({"no_mark": True}, {"stale_marked", "stale_not_persisted", "unchanged_not_marked", "mark_survives_scroll"}),
    ({"tips_marked": True}, {"unchanged_not_marked"}),
    ({"double_mark_after_scroll": True}, {"mark_survives_scroll"}),
    ({"mark_lost_on_rerender": True}, {"mark_survives_scroll"}),
    ({"rerender_fails": True}, {"mark_survives_scroll"}),
    ({"persist_mark": True}, {"stale_not_persisted"}),
    ({"save_fails": True}, {"stale_not_persisted"}),
    ({"no_earlier": True}, {"earlier_session_marked"}),
    ({"same_session": True}, {"earlier_session_marked", "rerun_not_marked"}),
    ({"rerun_marked": True}, {"rerun_not_marked"}),
    ({"gate_seen": True}, {"persistence_gate_never_open"}),
    ({"no_monitor": True}, {"persistence_gate_never_open"}),
    ({"runall_continues": True}, {"runall_stops"}),
    ({"no_panel": True}, {"error_panels"}),
    ({"no_predecessor": True}, {"tab_focuses_figure", "arrow_moves", "escape_leaves"}),
    ({"arrow_dead": True}, {"arrow_moves"}),
    ({"escape_blurs": True}, {"escape_leaves"}),
    ({"ring_stays": True}, {"escape_leaves"}),
])
def test_d2_each_fault_fails_exactly_its_own_keys(rs, nb, fault, failing):
    keys, _ = _run_d2(rs, nb, **fault)
    _missing, failed = rs.evaluate_unit_result(rs.UNIT_BY_ID["D2"], dict(keys, pageerrors=[]))
    assert set(failed) == failing, (fault, failed)


# -- D3 ----------------------------------------------------------------------------------------------------


def _run_d3(rs: Any, nb: dict[str, Any], **faults: Any) -> tuple[dict[str, Any], FakeWorld]:
    world = FakeWorld(rs, nb, **faults)
    return rs.run_d3(world, nb), world


def test_d3_positive_control_holds_every_listed_key(rs, nb):
    keys, _ = _run_d3(rs, nb)
    assert all(k in keys for k in D3_KEYS)
    assert rs.evaluate_unit_result(rs.UNIT_BY_ID["D3"], keys) == ([], []), keys
    assert keys["reopened_branch"] == "S2-T"


def test_d3_executes_its_own_drawing_cells_then_saves_closes_reloads_and_reopens(rs, nb):
    _, w = _run_d3(rs, nb)
    runs = [e[1] for e in w.log if isinstance(e, tuple) and e[0] == "run"]
    assert runs == ["boot", "assemble", "transfers", "draw-source", "draw-assay", "draw-tips", "draw-deck"]
    order = [("save", rs.DISPLAY_NOTEBOOK_NAME), ("close", rs.DISPLAY_NOTEBOOK_NAME), "reload"]
    idx = [_pos(w.log, e) for e in order]
    assert idx == sorted(idx) and idx[0] > _pos(w.log, ("run", "draw-deck"))
    assert not [e for e in w.log[idx[-1]:] if isinstance(e, tuple) and e[0] == "run"], (
        "nothing may be re-run after the reload: the reopened outputs must be the SAVED ones"
    )


def test_d3_scenario_negative_controls(rs, nb):
    for fault, key in (
        ({"script_in_bundle": True}, "no_script_in_bundles"), ({"save_fails": True}, "no_script_in_bundles"),
        ({"sanitized": True}, "reopened_branch"), ({"sanitized": True}, "svg_in_dom"),
        ({"gate_seen": True}, "persistence_gate_never_open"), ({"no_monitor": True}, "persistence_gate_never_open"),
        ({"liquid_fill": "rgb(0, 0, 0)"}, "liquid_fill_computed"),
    ):
        keys, _ = _run_d3(rs, nb, **fault)
        assert key in rs.evaluate_unit_result(rs.UNIT_BY_ID["D3"], keys)[1], (fault, keys)


def test_d3_records_the_other_branches_evidence_without_listing_it(rs, nb):
    keys, _ = _run_d3(rs, nb)
    assert "branch_evidence" in keys and set(keys["branch_evidence"]) >= {"summary_text_visible", "text_plain_visible", "liquid_fill_attr"}
    assert "branch_evidence" not in dict(rs.UNIT_BY_ID["D3"].expected)


# -- D4 ----------------------------------------------------------------------------------------------------


def _run_d4(rs: Any, nb: dict[str, Any], **faults: Any) -> tuple[dict[str, Any], FakeWorld, list[FakeWorld]]:
    a = FakeWorld(rs, nb, **faults)
    made: list[FakeWorld] = []

    def factory() -> FakeWorld:
        b = FakeWorld(rs, nb, **faults)
        b.blocked_context = True
        made.append(b)
        return b

    return rs.run_d4(a, nb, blocked_driver_factory=factory), a, made


def test_d4_positive_control_holds_every_listed_key(rs, nb):
    keys, _, _ = _run_d4(rs, nb)
    assert rs.evaluate_unit_result(rs.UNIT_BY_ID["D4"], keys) == ([], []), keys


def test_d4_uses_two_contexts_and_sets_high_contrast_in_both(rs, nb):
    _, a, made = _run_d4(rs, nb)
    assert len(made) == 1, "exactly one second (blocked) context"
    assert ("theme", HC_THEME) in a.log and ("theme", HC_THEME) in made[0].log
    runs = [e[1] for e in a.log if isinstance(e, tuple) and e[0] == "run"]
    assert runs == ["boot", "assemble", "transfers", "draw-assay"], "the plate the two colour keys read"
    assert not [e for e in made[0].log if isinstance(e, tuple) and e[0] in ("run", "open")], (
        "the blocked context only measures the theme's own token"
    )
    assert _pos(a.log, ("theme", HC_THEME)) < _pos(a.log, ("run", "draw-assay"))


def test_d4_negative_controls(rs, nb):
    keys, _, _ = _run_d4(rs, nb, route_never_fires=True)
    assert keys["hc_palette_untouched"] is False, "a block that never happened proves nothing"
    keys, _, _ = _run_d4(rs, nb, layout_token_blocked="rgb(9, 9, 9)")
    assert keys["hc_palette_untouched"] is False


# -- dispatch ----------------------------------------------------------------------------------------------


def test_run_display_scenario_dispatches_each_unit_to_its_own_body(rs, monkeypatch, nb):
    calls: list[tuple[str, Any]] = []

    class Drv:
        def __init__(self, session: Any, *a: Any, **k: Any) -> None:
            calls.append(("driver", session))

    monkeypatch.setattr(rs, "DisplayDriver", Drv)
    monkeypatch.setattr(rs, "run_chrome_scenario", lambda s, u, e, notebook=None: calls.append(("chrome", u.id)) or {"c": 1})
    monkeypatch.setattr(rs, "run_d2", lambda d, f: calls.append(("d2", type(d).__name__)) or {"k": 2})
    monkeypatch.setattr(rs, "run_d3", lambda d, f: calls.append(("d3", type(d).__name__)) or {"k": 3})
    monkeypatch.setattr(rs, "run_d4", lambda d, f, blocked_driver_factory: calls.append(("d4", callable(blocked_driver_factory))) or {"k": 4})
    session = FakeSession()
    for uid, expect in (("D1", {"c": 1}), ("D1-dark", {"c": 1}), ("D2", {"k": 2}), ("D3", {"k": 3}), ("D4", {"k": 4})):
        assert rs.run_display_scenario(session, rs.UNIT_BY_ID[uid], make_env(rs), notebook=nb) == expect
    kinds = [c[0] for c in calls if c[0] != "driver"]
    assert kinds == ["chrome", "chrome", "d2", "d3", "d4"]
    assert ("d4", True) in calls


def test_run_display_scenario_refuses_a_unit_it_has_no_body_for(rs):
    unit = rs.HarnessUnit("K9", rs.DISPLAY_CHECK, 1.0, ())
    with pytest.raises(rs.DisplayCheckError):
        rs.run_display_scenario(FakeSession(), unit, make_env(rs))


def test_d2_evidence_keeps_the_raw_reports_behind_the_error_keys(rs):
    """A failing `other_errors_plain` (or `error_panels`, `runall_stops`) has to be diagnosable from the result
    file alone: D2's evidence carries the raw plain-error, PLR-error and Run All reports."""
    import inspect

    def missing(source: str) -> list[str]:
        call = source.split("evidence.update(", 1)[1].split('keys["evidence"]', 1)[0]
        return [n for n in ("error_reports", "value_error", "runall") if f"{n}={n}" not in call]

    assert missing(inspect.getsource(rs.run_d2)) == []
    # negative controls: a source without one of them, or without any, is rejected by the same checker
    stripped = inspect.getsource(rs.run_d2).replace("value_error=value_error", "")
    assert missing(stripped) == ["value_error"]
    assert missing('evidence.update(restart=restart)\n keys["evidence"] = evidence') == [
        "error_reports", "value_error", "runall",
    ]


# =========================================================================== #
# Sprint C (C7): the static greps the dock gate closes -- AC-39(c), R19 (AC-41), the extended R21 (AC-31)
# =========================================================================== #
#
# Pure functions over a source tree (no browser). Each has a POSITIVE control on the real tree (it must pass
# now) and a NEGATIVE control on a synthetic tree (a forbidden token planted in it must be found).

R21_SIX = (
    "web-repl/overlay/assets/python/praxis/viz/",
    "web-repl/overlay/assets/visualizer/",
    "web-repl/overlay/assets/visualizer-augmentations/",
    "web-repl/overlay/assets/visualizer3d/",
    "web-repl/overlay/assets/visualizer3d-augmentations/",
    "web-repl/shell/display/dock.js",
)
R21_BASH = (
    """grep -rn "praxis_repl" {paths} | sed 's/``praxis_repl``//g' | grep "praxis_repl"; s=("${{PIPESTATUS[@]}}")\n"""
    """echo "${{s[@]}}"\n"""
)


def _bash_r21(paths: list[str], cwd: Path) -> list[int]:
    out = subprocess.run(
        ["bash", "-c", R21_BASH.format(paths=" ".join(paths))], capture_output=True, text=True, cwd=str(cwd), timeout=120
    )
    return [int(x) for x in out.stdout.strip().splitlines()[-1].split()]


def _mini_tree(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


def test_grep_tree_is_grep_rn_with_include_and_exclude_dir(rs, tmp_path):
    root = _mini_tree(tmp_path, {
        "a/one.js": "x\nfoo bar\n", "a/two.txt": "foo\n", "a/__tests__/t.js": "foo\n", "a/sub/three.js": "no\nfoo\n",
    })
    hits = rs.grep_tree(root, ["a"], r"foo", include=("*.js",), exclude_dirs=("__tests__",))
    assert hits == [("a/one.js", 2, "foo bar"), ("a/sub/three.js", 2, "foo")], "the .txt and the __tests__ file are skipped"
    assert rs.grep_tree(root, ["a"], r"foo") != hits, "without include/exclude the other two files are found too"
    assert rs.grep_tree(root, ["a"], r"absent-token") == []
    with pytest.raises(FileNotFoundError):  # grep exits 2 on an unreadable path; never read as "no hit"
        rs.grep_tree(root, ["nope"], r"foo")


def test_ac39c_no_test_hooks_in_the_product_js_on_the_real_tree(rs):
    """AC-39(c) verbatim: grep -rnE '__praxis_test|data-praxis-test' shell/display + visualizer3d-augmentations
    --include='*.js' --exclude-dir=__tests__ finds nothing. (It used to find dock.test.js's own regex literal.)"""
    assert rs.ac39c_hits(rs.REPO_ROOT) == []


@pytest.mark.parametrize("rel", [
    "web-repl/shell/display/x.js", "web-repl/overlay/assets/visualizer3d-augmentations/y.js", "web-repl/shell/display/x.test.js",
])
@pytest.mark.parametrize("token", ["__praxis_test", "data-praxis-test"])
def test_ac39c_control_finds_a_planted_hook_in_both_trees_and_in_a_test_file(rs, tmp_path, rel, token):
    root = _mini_tree(tmp_path, {
        "web-repl/shell/display/ok.js": "1\n", "web-repl/overlay/assets/visualizer3d-augmentations/ok.js": "1\n",
        rel: f"const a = 1;\nwindow.{token} = 1;\n",
    })
    assert [h[0] for h in rs.ac39c_hits(root)] == [rel]


def test_ac39c_ignores_the_one_exclusion_the_spec_states(rs, tmp_path):
    quiet = _mini_tree(tmp_path, {
        "web-repl/shell/display/ok.js": "1\n", "web-repl/overlay/assets/visualizer3d-augmentations/ok.js": "1\n",
        "web-repl/shell/display/__tests__/t.js": "__praxis_test\n",
    })
    assert rs.ac39c_hits(quiet) == []


def test_r19_requestdevice_and_requestport_are_absent_on_the_real_tree(rs):
    """AC-41 R19: the grep exits 1 EXACTLY -- it finds nothing, and every path exists (2 would be an error)."""
    assert rs.r19_check(rs.REPO_ROOT) == (True, [])


R19_DIRS = (
    "web-repl/overlay/assets/visualizer-augmentations", "web-repl/overlay/assets/visualizer3d-augmentations",
    "web-repl/shell/display",
)


@pytest.mark.parametrize("token", ["requestDevice", "requestPort"])
def test_r19_control_fires_on_either_token(rs, tmp_path, token):
    base = {f"{d}/ok.js": "1\n" for d in R19_DIRS}
    bad = _mini_tree(tmp_path / "bad", {**base, f"{R19_DIRS[1]}/serial.js": f"navigator.serial.{token}();\n"})
    ok, hits = rs.r19_check(bad)
    assert ok is False and [h[0] for h in hits] == [f"{R19_DIRS[1]}/serial.js"]
    assert rs.r19_check(_mini_tree(tmp_path / "clean", base)) == (True, [])


def test_r19_control_a_missing_path_is_not_a_pass(rs, tmp_path):
    ok, _hits = rs.r19_check(tmp_path / "empty")  # grep exits 2 on a missing path
    assert ok is False


def test_r21_extended_passes_on_the_real_tree_and_is_not_vacuous(rs):
    res = rs.r21_extended_check(rs.REPO_ROOT)
    assert res["ok"] is True and res["residual"] == [] and res["paths_exist"] is True
    assert res["first_grep_status"] == 0, "the documentation mentions ARE found (transport.py and viewer3d.py)"
    assert len(res["hits"]) >= 3
    assert {h[0] for h in res["hits"]} <= {
        "web-repl/overlay/assets/python/praxis/viz/transport.py", "web-repl/overlay/assets/python/praxis/viz/viewer3d.py",
    }, "only RST documentation mentions remain after the strip; no code use anywhere on the six paths"


def test_r21_extended_python_form_agrees_with_the_bash_gate_on_the_real_tree(rs):
    assert _bash_r21(list(R21_SIX), rs.REPO_ROOT) == [0, 0, 1]
    assert list(rs.R21_EXTENDED_PATHS) == list(R21_SIX), "the six paths: five directories and dock.js"


def _r21_base_files() -> dict[str, str]:
    return {
        "web-repl/overlay/assets/python/praxis/viz/ok.py": "x = 1\n", "web-repl/overlay/assets/visualizer/ok.js": "1\n",
        "web-repl/overlay/assets/visualizer-augmentations/ok.js": "1\n", "web-repl/overlay/assets/visualizer3d/ok.js": "1\n",
        "web-repl/overlay/assets/visualizer3d-augmentations/ok.js": "1\n", "web-repl/shell/display/dock.js": "1\n",
    }


@pytest.mark.parametrize(
    "rel,text",
    [
        ("web-repl/overlay/assets/visualizer3d/app.js", 'const c = new BroadcastChannel("praxis_repl");\n'),
        ("web-repl/overlay/assets/visualizer3d-augmentations/socket.js", "const c = new BroadcastChannel(`praxis_repl`);\n"),
        ("web-repl/shell/display/dock.js", "const CH = 'praxis_repl';\n"),
        ("web-repl/overlay/assets/python/praxis/viz/viewer3d.py", 'see ``praxis_repl`` and post to "praxis_repl"\n'),
    ],
)
def test_r21_extended_control_fires_on_a_code_use_on_each_new_path_and_the_bash_gate_agrees(rs, tmp_path, rel, text):
    files = _r21_base_files()
    files[rel] = files.get(rel, "") + text
    root = _mini_tree(tmp_path, files)
    res = rs.r21_extended_check(root)
    assert res["ok"] is False and res["residual"], res
    assert _bash_r21(list(R21_SIX), root)[2] == 0, "the spec's bash gate finds the same residual code use"


def test_r21_extended_control_ignores_the_documentation_form(rs, tmp_path):
    files = _r21_base_files()
    files["web-repl/overlay/assets/python/praxis/viz/doc.py"] = '"""NOT ``praxis_repl``."""\n'
    res = rs.r21_extended_check(_mini_tree(tmp_path, files))
    assert res["ok"] is True and res["first_grep_status"] == 0 and res["residual"] == []


def test_r21_extended_control_a_missing_directory_or_dock_js_is_an_error_not_a_pass(rs, tmp_path):
    files = _r21_base_files()
    del files["web-repl/overlay/assets/visualizer3d-augmentations/ok.js"]
    res = rs.r21_extended_check(_mini_tree(tmp_path / "nodir", files))
    assert res["ok"] is False and res["paths_exist"] is False
    files = _r21_base_files()
    del files["web-repl/shell/display/dock.js"]
    res = rs.r21_extended_check(_mini_tree(tmp_path / "nodock", files))
    assert res["ok"] is False and res["paths_exist"] is False


# =========================================================================== #
# Sprint C (C7): the D6 sizing table as a pure function (AC-36 "keyed by the D6 sizing case", AC-39(d) skip rule)
# =========================================================================== #

ASSERTED, RECORDED = "asserted", "recorded-only"
MEDIUM_CATS = ("open_width_1280_1599", "drag_clamp_1280_1599", "fit_after_tier_change_1280_1599")
WIDE_CATS = ("open_width_ge_1600", "fit_after_tier_change_ge_1600", "resize_within_wide")


def _status(rs, hon, reach, refit, keeps=True):
    return rs.width_key_status(
        css_limits_honoured=hon, layout_sizing_reachable=reach, css_limits_refit=refit, restore_layout_keeps_iframe=keeps
    )


def test_sizing_case_names_follow_the_d6_table(rs):
    assert rs.sizing_case(True, True) == "honoured_reachable"
    assert rs.sizing_case(False, True) == "ignored_reachable"
    assert rs.sizing_case(True, False) == "honoured_unreachable"
    assert rs.sizing_case(False, False) == "ignored_unreachable", "S1-L"
    assert rs.SIZING_CASES == ("honoured_reachable", "ignored_reachable", "honoured_unreachable", "ignored_unreachable")


def test_the_width_categories_are_the_six_the_s1_record_names(rs):
    assert tuple(rs.WIDTH_CATEGORIES) == MEDIUM_CATS + WIDE_CATS


@pytest.mark.parametrize("refit", [True, False])
def test_case_honoured_reachable_asserts_every_width_key(rs, refit):
    s = _status(rs, True, True, refit)
    assert s == {c: ASSERTED for c in MEDIUM_CATS + WIDE_CATS}


@pytest.mark.parametrize("refit", [True, False])
def test_case_ignored_reachable_asserts_every_width_key(rs, refit):
    s = _status(rs, False, True, refit)
    assert s == {c: ASSERTED for c in MEDIUM_CATS + WIDE_CATS}


def test_case_honoured_unreachable_with_refit_asserts_every_width_key(rs):
    assert _status(rs, True, False, True) == {c: ASSERTED for c in MEDIUM_CATS + WIDE_CATS}


def test_case_honoured_unreachable_without_refit_asserts_1280_1599_and_records_the_wide_keys_only(rs):
    s = _status(rs, True, False, False)
    assert {c: s[c] for c in MEDIUM_CATS} == {c: ASSERTED for c in MEDIUM_CATS}
    assert {c: s[c] for c in WIDE_CATS} == {c: RECORDED for c in WIDE_CATS}


@pytest.mark.parametrize("refit", [True, False])
def test_case_s1_l_records_every_width_key(rs, refit):
    assert _status(rs, False, False, refit) == {c: RECORDED for c in MEDIUM_CATS + WIDE_CATS}


def test_restore_layout_not_keeping_the_iframe_moves_drag_and_resize_to_the_unreachable_row(rs):
    """Spec AC-36: open-time keys and fit_after_tier_change keep their case status; the drag-clamp keys and
    resize_within_wide take the status of the `unreachable` row for the same CSS column."""
    # CSS ignored -> recorded-only for both
    s = _status(rs, False, True, True, keeps=False)
    assert s["drag_clamp_1280_1599"] == RECORDED and s["resize_within_wide"] == RECORDED
    assert s["open_width_1280_1599"] == ASSERTED and s["open_width_ge_1600"] == ASSERTED
    assert s["fit_after_tier_change_1280_1599"] == ASSERTED and s["fit_after_tier_change_ge_1600"] == ASSERTED
    # CSS honoured -> the 1280-1599 drag is CSS (asserted); resize_within_wide is inline px, asserted iff css_limits_refit
    s = _status(rs, True, True, True, keeps=False)
    assert s["drag_clamp_1280_1599"] == ASSERTED and s["resize_within_wide"] == ASSERTED
    s = _status(rs, True, True, False, keeps=False)
    assert s["drag_clamp_1280_1599"] == ASSERTED and s["resize_within_wide"] == RECORDED
    assert s["open_width_ge_1600"] == ASSERTED, "the open-time keys keep their case status (honoured/reachable: asserted)"


def test_keeps_iframe_true_changes_nothing_relative_to_the_default(rs):
    for hon in (True, False):
        for reach in (True, False):
            for refit in (True, False):
                assert _status(rs, hon, reach, refit, True) == rs.width_key_status(
                    css_limits_honoured=hon, layout_sizing_reachable=reach, css_limits_refit=refit
                )


def test_ac39d_runs_only_where_the_ge_1600_key_is_asserted(rs):
    """D6: AC-39(d) is skipped, and recorded as skipped, wherever the >= 1600 key is recorded-only."""
    assert rs.ac39d_status(_status(rs, True, True, True)) == "run"
    assert rs.ac39d_status(_status(rs, False, True, False)) == "run"
    assert rs.ac39d_status(_status(rs, True, False, True)) == "run"
    assert rs.ac39d_status(_status(rs, True, False, False)) == "skipped", "honoured/unreachable without css_limits_refit"
    assert rs.ac39d_status(_status(rs, False, False, True)) == "skipped", "S1-L"


def test_the_recorded_s1_case_is_honoured_reachable_keeping_the_iframe_and_asserts_everything(rs):
    """AC-1 (S1 run 1e0cab6d): css_limits_honoured, dock_layout_sizing_reachable, css_limits_refit and
    restore_layout_keeps_iframe are all true."""
    assert rs.SIZING_RECORD == {
        "css_limits_honoured": True, "layout_sizing_reachable": True, "css_limits_refit": True,
        "restore_layout_keeps_iframe": True,
    }
    assert rs.sizing_case(rs.SIZING_RECORD["css_limits_honoured"], rs.SIZING_RECORD["layout_sizing_reachable"]) == "honoured_reachable"
    assert rs.SIZING_STATUS == {c: ASSERTED for c in MEDIUM_CATS + WIDE_CATS}
    assert rs.ac39d_status(rs.SIZING_STATUS) == "run"


# -- the wide-tier width formula and the clamp predicates (D6, AC-36) ------------------------------------------


def test_wide_panel_width_expected_is_the_d6_formula(rs):
    assert rs.wide_panel_width_expected(1571.0, 0.0) == 611.0, "main - 960 - padding"
    assert rs.wide_panel_width_expected(1571.0, 20.0) == 591.0
    assert rs.wide_panel_width_expected(1300.0, 0.0) == 420.0, "max(420, ...)"
    assert rs.wide_panel_width_expected(1891.0, 0.0) == 931.0


@pytest.mark.parametrize(
    "panel,ok",
    [(611.0, True), (603.0, True), (619.0, True), (602.9, False), (619.1, False), (785.0, False), (420.0, False), (None, False), ("611", False)],
)
def test_wide_width_ok_is_plus_minus_eight_px_around_the_formula(rs, panel, ok):
    assert rs.wide_width_ok(panel, 1571.0, 0.0) is ok


def test_wide_width_ok_needs_its_measurements(rs):
    assert rs.wide_width_ok(611.0, None, 0.0) is False
    assert rs.wide_width_ok(611.0, 1571.0, None) is False


@pytest.mark.parametrize(
    "width,ok", [(420.0, True), (450.0, True), (480.0, True), (419.0, True), (481.5, True), (417.9, False), (482.1, False), (300.0, False), (None, False)]
)
def test_open_width_ok_is_420_to_480_with_a_subpixel_allowance(rs, width, ok):
    assert rs.open_width_ok(width) is ok


@pytest.mark.parametrize("width,ok", [(420.0, True), (421.9, True), (418.1, True), (300.0, False), (450.0, False), (None, False)])
def test_clamp_low_ok_means_a_drag_to_300_ends_at_420(rs, width, ok):
    assert rs.clamp_low_ok(width) is ok


@pytest.mark.parametrize("width,ok", [(480.0, True), (478.1, True), (481.9, True), (700.0, False), (450.0, False), (None, False)])
def test_clamp_high_ok_means_a_drag_to_700_ends_at_480(rs, width, ok):
    assert rs.clamp_high_ok(width) is ok


# =========================================================================== #
# Sprint C (C7): the dock units in the D16 table -- K1a, K1b, K2, N-d (AC-42 "the driver's unit table equals D16's")
# =========================================================================== #

DOCK_IDS = ["K1a", "K1b", "K2", "N-d"]
DOCK_BUDGET_MIN = [10, 14, 15, 6]
K1A_KEYS = (
    "panel_is_split_right", "viewer_resources", "hello_backend", "canvas_nonblank", "embed_hidden", "pageerrors",  # AC-34
    "click_focuses", "follow_focuses", "follow_off_holds", "follow_skips_null", "preset_directions",
    "follow_keeps_preset",  # AC-35
    "state_updates", "stale_and_panel",  # AC-37
)
#: AC-38's fixed execution order (Revision 6, C6-2; Revision 7): the listed keys run in exactly this order.
K1B_KEYS = (
    "reconnect_after_reload", "preset_survives_reload", "drawer_reconnect", "redock_live", "stop_placeholder",
    "redock_reloads", "late_iframe", "many_reloads", "restart_placeholder",
)
#: AC-36 keys asserted in every D6 sizing case (the drawer keys, the height keys, the notebook cap, the reload count).
K2_ALWAYS = (
    "drawer_overlays", "drawer_no_reflow", "drawer_dismiss_reopen", "tier_up_rehomes", "viewer_height",
    "motion_slot_height", "nb_content_width_1600", "nb_content_width_1920", "iframe_reloads_during_resize",
)
#: The width keys, in K2's step order, each with its D6 family.
K2_WIDTH = (
    ("open_width_1440", "open_width_1280_1599"),
    ("drag_clamp_low_1440", "drag_clamp_1280_1599"),
    ("drag_clamp_high_1440", "drag_clamp_1280_1599"),
    ("fit_after_tier_change_wide", "fit_after_tier_change_ge_1600"),
    ("fit_after_tier_change_medium", "fit_after_tier_change_1280_1599"),
    ("open_width_1280", "open_width_1280_1599"),
    ("drag_clamp_low_1280", "drag_clamp_1280_1599"),
    ("drag_clamp_high_1280", "drag_clamp_1280_1599"),
    ("panel_width_wide_1600", "open_width_ge_1600"),
    ("resize_within_wide", "resize_within_wide"),
    ("panel_width_wide_1920", "open_width_ge_1600"),
)
K2_ALL_KEYS = frozenset(K2_ALWAYS) | {k for k, _ in K2_WIDTH}


def _expected_k2(statuses: dict[str, str]) -> set[str]:
    return set(K2_ALWAYS) | {k for k, cat in K2_WIDTH if statuses[cat] == "asserted"}


def test_unit_table_is_d16_with_the_dock_units_appended_in_table_order(rs):
    assert [u.id for u in rs.UNIT_TABLE] == ALL_IDS + DOCK_IDS
    assert [u.id for u in rs.UNIT_TABLE if u.check == "display-check"] == ALL_IDS
    dock = [rs.UNIT_BY_ID[i] for i in DOCK_IDS]
    assert rs.DOCK_CHECK == "dock-check" and all(u.check == "dock-check" for u in dock)
    assert [u.budget_s for u in dock] == [m * 60 for m in DOCK_BUDGET_MIN], "10, 14, 15 and 6 min (D16)"
    assert [u.acs for u in dock] == [("AC-34", "AC-35", "AC-37"), ("AC-38",), ("AC-36",), ("AC-39",)]


def test_n_d_is_negative_only_and_never_part_of_the_aggregate(rs):
    assert [u.id for u in rs.DOCK_AGGREGATE_UNITS] == ["K1a", "K1b", "K2"]
    assert rs.UNIT_BY_ID["N-d"].in_aggregate is False
    assert all(rs.UNIT_BY_ID[i].in_aggregate for i in ("D1", "D4", "K1a", "K1b", "K2"))


def test_k1a_lists_the_ac34_ac35_ac37_keys(rs):
    assert tuple(rs.UNIT_BY_ID["K1a"].keys) == K1A_KEYS
    exp = dict(rs.UNIT_BY_ID["K1a"].expected)
    assert exp["pageerrors"] == [] and all(exp[k] is True for k in K1A_KEYS if k not in ("pageerrors", "hello_backend"))
    assert rs.UNIT_BY_ID["K1a"].viewports == ((1440, 900),)


def test_hello_backend_holds_for_webgl2_or_webgpu_only(rs):
    want = dict(rs.UNIT_BY_ID["K1a"].expected)["hello_backend"]
    assert rs._holds("WebGL2", want) and rs._holds("WebGPU", want)
    for bad in ("WebGL", "webgl2", "", None, ["WebGL2"], True, 2):
        assert not rs._holds(bad, want), bad
    assert rs._holds(want.example(), want), "the passing example a test builds a result from"


def test_k1b_lists_the_ac38_keys_in_the_fixed_execution_order(rs):
    k1b = rs.UNIT_BY_ID["K1b"]
    assert tuple(k1b.keys) == K1B_KEYS, "AC-38 execution order is the listed-key order"
    assert all(v is True for _, v in k1b.expected) and k1b.viewports == ((1440, 900),)
    assert "pageerrors" not in k1b.keys, "AC-38 names no pageerrors key (the kernel restart ends the run)"


def test_k2_steps_are_the_nine_ordered_steps_starting_at_1152_by_800(rs):
    names = [n for n, _ in rs.K2_STEPS]
    assert names == [
        "drawer", "dismiss_reopen", "tier_up", "medium_1440", "fit", "medium_1280", "wide_1600",
        "resize_within_wide", "wide_1920",
    ]
    assert [v for _, v in rs.K2_STEPS] == [
        (1152, 800), (1152, 800), (1440, 900), (1440, 900), (1600, 900), (1280, 800), (1600, 900), (1920, 900), (1920, 1080),
    ]
    k2 = rs.UNIT_BY_ID["K2"]
    assert k2.viewports == tuple(v for _, v in rs.K2_STEPS) and k2.viewports[0] == (1152, 800)


def test_k2_family_map_covers_every_width_key_and_only_those(rs):
    assert dict(rs.K2_WIDTH_KEYS) == dict(K2_WIDTH)
    assert set(dict(K2_WIDTH).values()) == set(rs.WIDTH_CATEGORIES), "every D6 family has at least one key"


def test_k2_listed_keys_under_the_recorded_case_are_all_asserted(rs):
    k2 = rs.UNIT_BY_ID["K2"]
    assert set(k2.keys) == K2_ALL_KEYS and len(k2.keys) == len(K2_ALL_KEYS), "no duplicates"
    assert rs.k2_expected(rs.SIZING_STATUS) == k2.expected, "the table is built from the recorded AC-1 case"
    exp = dict(k2.expected)
    assert exp["iframe_reloads_during_resize"] == 0 and type(exp["iframe_reloads_during_resize"]) is int
    assert exp["drawer_overlays"] is True and exp["panel_width_wide_1920"] is True
    assert isinstance(exp["viewer_height"], rs.AtLeast) and exp["viewer_height"].limit == 300.0
    assert isinstance(exp["motion_slot_height"], rs.AtMost) and exp["motion_slot_height"].limit == 36.0
    assert isinstance(exp["nb_content_width_1600"], rs.AtMost) and exp["nb_content_width_1600"].limit == 960.0


@pytest.mark.parametrize(
    "hon,reach,refit,keeps",
    [(h, r, f, k) for h in (True, False) for r in (True, False) for f in (True, False) for k in (True, False)],
)
def test_k2_listed_keys_follow_the_d6_sizing_case_asserted_versus_recorded_only(rs, hon, reach, refit, keeps):
    statuses = rs.width_key_status(
        css_limits_honoured=hon, layout_sizing_reachable=reach, css_limits_refit=refit, restore_layout_keeps_iframe=keeps
    )
    listed = {k for k, _ in rs.k2_expected(statuses)}
    assert listed == _expected_k2(statuses)
    # drawer, height, notebook cap and reload keys are asserted in every case (AC-36)
    assert set(K2_ALWAYS) <= listed


def test_k2_under_s1_l_lists_only_the_always_asserted_keys(rs):
    statuses = rs.width_key_status(css_limits_honoured=False, layout_sizing_reachable=False, css_limits_refit=False)
    assert {k for k, _ in rs.k2_expected(statuses)} == set(K2_ALWAYS)


def test_n_d_lists_the_wide_width_key_which_must_fail_or_a_skip(rs):
    n_d = rs.UNIT_BY_ID["N-d"]
    assert n_d.expected == (("panel_width_wide_1600", True),) and n_d.viewports == ((1600, 900),)
    assert rs.nd_expected(rs.SIZING_STATUS) == n_d.expected
    skipped = rs.width_key_status(css_limits_honoured=True, layout_sizing_reachable=False, css_limits_refit=False)
    assert rs.nd_expected(skipped) == (("skipped", True),), "recorded-only >= 1600: AC-39(d) is skipped and says so"


def test_at_least_is_a_lower_bound_that_survives_json_and_rejects_non_numbers(rs):
    bound = rs.AtLeast(300.0)
    assert bound.holds(300.0) and bound.holds(812) and not bound.holds(299.99)
    for bad in (True, False, None, "400", float("nan"), [400]):
        assert not bound.holds(bad), bad
    assert rs._holds(bound.example(), bound) and json.loads(json.dumps(bound.example())) == bound.example()


def test_dock_unit_results_survive_the_unit_runner_path(rs, ur, wds, tmp_path):
    for uid in DOCK_IDS:
        out = tmp_path / uid
        code = scenario_in_process(rs, ur, wds, uid, out, make_env(rs))
        assert code == 0, uid
        stamp = json.loads(rs.unit_paths(out, uid)["stamp"].read_text())
        assert stamp["unit"] == uid and stamp["exit"] == 0 and stamp["budget_s"] == rs.UNIT_BY_ID[uid].budget_s


def test_dock_unit_inputs_are_the_seven_d16_inputs_and_hash_the_viewports_and_neg(rs):
    env = make_env(rs)
    for uid in DOCK_IDS:
        inputs = rs.unit_inputs(rs.UNIT_BY_ID[uid], env)
        assert sorted(inputs) == sorted(["dist", "notebook", "harness", "runner", "chrome", "args", "driver"])
    k1b = rs.UNIT_BY_ID["K1b"]
    assert rs.unit_inputs(k1b, env, ())["args"] != rs.unit_inputs(k1b, env, ("drop-query",))["args"], "AC-39(e): --neg is hashed"
    other = dataclasses.replace(rs.UNIT_BY_ID["K2"], viewports=((1152, 800),))
    assert rs.unit_inputs(rs.UNIT_BY_ID["K2"], env)["args"] != rs.unit_inputs(other, env)["args"]


# =========================================================================== #
# Sprint C (C7): K1a -- AC-34, AC-35, AC-37. The pure key derivation over raw page evidence.
# =========================================================================== #
#
# `derive_k1a_keys(raw)` is pure: it maps what the page reported to the listed keys. Each key has a POSITIVE control
# (synthetic raw evidence that must pass) and NEGATIVE controls (evidence violating, or missing, that one thing must
# fail exactly that key). A precondition that would make a key pass vacuously is itself a negative control.

import copy  # noqa: E402
import math  # noqa: E402


def _dir(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def cam_for(rs, name, at=(100.0, 200.0, 0.0), dist=500.0):
    """A camera ``{from, at}`` looking along exactly the preset's direction."""
    d = _dir(rs.VIEWS[name])
    return {"from": [a + dist * c for a, c in zip(at, d)], "at": list(at)}


def good_k1a(rs):
    return {
        "panel": {"state": "open-connected", "home": "split", "panel_left": 1002.0, "notebook_right": 1000.0},
        "resources": ["deck", "tip_carrier", "tips_300", "plate_carrier", "source", "assay"],
        "hello": {"backend": "WebGL2", "renderer": "ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device))"},
        "canvas": {"diff_pixels": 54000, "total_pixels": 360000, "control_blank": 0.0, "control_marked": 0.05},
        "embed": {".navbar": "none", "#toolbar-left": "none", "#stats-panel": "none", "#sidepanel": "none", "#toolbar": "none"},
        "click": {"footer_before": "No resource focused.", "footer_after": "source",
                  "at_before": [0.0, 0.0, 0.0], "at_after": [120.0, 80.0, 10.0]},
        "follow_on": {"enabled": True, "focused": "assay", "footer": "assay",
                      "at_before": [120.0, 80.0, 10.0], "at_after": [120.0, 160.0, 10.0]},
        "follow_off": {"enabled": False, "footer_before": "assay", "footer_after": "assay",
                       "at_before": [120.0, 160.0, 10.0], "at_after": [120.0, 160.0, 10.0]},
        "follow_null": {"enabled": True, "ledger_resources": [None], "footer_before": "assay", "footer_after": "assay",
                        "at_before": [120.0, 160.0, 10.0], "at_after": [120.0, 160.0, 10.0]},
        "presets": {"top": cam_for(rs, "top"), "front": cam_for(rs, "front"), "iso": cam_for(rs, "iso")},
        "follow_keeps": {"pressed": "top", "camera": cam_for(rs, "top", at=(300.0, 40.0, 5.0)), "footer_before": "assay",
                         "footer_after": "tips_300"},
        "state": {"well": "source_well_0", "before": '{"volume": 200}', "after": '{"volume": 190}'},
        "stale": {"changed_notices": 1, "notice_text": rs.CHANGED_NOTICE, "panel_state": "open-connected"},
    }


K1A_DERIVED = (
    "panel_is_split_right", "viewer_resources", "hello_backend", "canvas_nonblank", "embed_hidden", "click_focuses",
    "follow_focuses", "follow_off_holds", "follow_skips_null", "preset_directions", "follow_keeps_preset", "state_updates",
    "stale_and_panel",
)


def test_views_are_the_renderer_js_vectors_copied_into_the_harness(rs):
    """AC-35: `VIEWS` is copied from renderer.js:117-121; read the real file so the copy cannot drift."""
    src = (rs.REPO_ROOT / "web-repl/overlay/assets/visualizer3d/renderer.js").read_text()
    block = src.split("export const VIEWS = {", 1)[1].split("};", 1)[0]
    found = {}
    for line in block.strip().splitlines():
        m = re.match(r"\s*(\w+): new THREE\.Vector3\(([^)]*)\)", line)
        assert m, line
        found[m.group(1)] = tuple(float(x) for x in m.group(2).split(","))
    assert found == {k: tuple(v) for k, v in rs.VIEWS.items()} and set(found) == {"iso", "top", "front"}


@pytest.mark.parametrize("name", ["iso", "top", "front"])
def test_preset_ok_is_the_normalised_direction_dot_above_0_99(rs, name):
    assert rs.preset_ok(cam_for(rs, name), name) is True
    assert rs.preset_ok(cam_for(rs, name, dist=10.0), name) is True, "a length-independent test"
    for other in {"iso", "top", "front"} - {name}:
        assert rs.preset_ok(cam_for(rs, other), name) is False, (name, other)


def test_preset_ok_rejects_degenerate_and_garbage_cameras(rs):
    assert rs.preset_ok({"from": [1, 1, 1], "at": [1, 1, 1]}, "top") is False, "no direction at all"
    for bad in (None, {}, {"from": [1, 2], "at": [0, 0, 0]}, {"from": ["a", 1, 1], "at": [0, 0, 0]}, {"from": [0, 0, 1]}):
        assert rs.preset_ok(bad, "top") is False, bad
    assert rs.preset_ok(cam_for(rs, "top"), "nope") is False


def test_preset_ok_threshold_is_strict_at_0_99(rs):
    top = _dir(rs.VIEWS["top"])
    def tilted(deg):
        t = math.radians(deg)
        v = [top[0], top[1] * math.cos(t) - top[2] * math.sin(t), top[1] * math.sin(t) + top[2] * math.cos(t)]
        return {"from": v, "at": [0.0, 0.0, 0.0]}
    assert rs.preset_ok(tilted(5.0), "top") is True  # cos 5 deg = 0.9962
    assert rs.preset_ok(tilted(9.0), "top") is False  # cos 9 deg = 0.9877


def test_k1a_positive_control_every_listed_key_holds(rs):
    keys = rs.derive_k1a_keys(good_k1a(rs))
    assert set(K1A_DERIVED) <= set(keys)
    unit = rs.UNIT_BY_ID["K1a"]
    assert rs.evaluate_unit_result(unit, dict(keys, pageerrors=[])) == ([], []), keys
    assert keys["hello_backend"] == "WebGL2", "the page's own string, read from the kernel, not a boolean"


def test_k1a_derive_never_raises_on_empty_or_garbage_evidence_and_fails_every_key(rs):
    for raw in ({}, None, {"panel": None, "canvas": "x", "presets": 3}):
        keys = rs.derive_k1a_keys(raw)
        unit = rs.UNIT_BY_ID["K1a"]
        missing, failing = rs.evaluate_unit_result(unit, dict(keys, pageerrors=[]))
        assert missing == [] and set(failing) == set(K1A_DERIVED), (raw, failing)


def _mut(rs, fn):
    raw = copy.deepcopy(good_k1a(rs))
    fn(raw)
    keys = rs.derive_k1a_keys(raw)
    return rs.evaluate_unit_result(rs.UNIT_BY_ID["K1a"], dict(keys, pageerrors=[]))[1], keys


def _set(path, value):
    def apply(raw):
        d = raw
        for p in path[:-1]:
            d = d[p]
        d[path[-1]] = value
    return apply


@pytest.mark.parametrize(
    "key,fn",
    [
        ("panel_is_split_right", _set(("panel", "home"), "drawer")),
        ("panel_is_split_right", _set(("panel", "panel_left"), 700.0)),
        ("panel_is_split_right", _set(("panel", "state"), "open-waiting")),
        ("panel_is_split_right", _set(("panel", "panel_left"), None)),
        ("viewer_resources", _set(("resources",), ["deck", "assay", "source"])),
        ("viewer_resources", _set(("resources",), ["deck", "assay", "tips_300"])),
        ("viewer_resources", _set(("resources",), None)),
        ("viewer_resources", _set(("resources",), [])),
        ("hello_backend", _set(("hello", "backend"), "WebGL")),
        ("hello_backend", _set(("hello", "backend"), None)),
        ("hello_backend", _set(("hello",), None)),
        ("canvas_nonblank", _set(("canvas", "diff_pixels"), 0)),
        ("canvas_nonblank", _set(("canvas", "diff_pixels"), 3600)),  # exactly 1%: "> 1%" is strict
        ("canvas_nonblank", _set(("canvas", "total_pixels"), 0)),
        ("canvas_nonblank", _set(("canvas", "control_blank"), 0.5)),  # the measurement reads a blank image as drawn
        ("canvas_nonblank", _set(("canvas", "control_marked"), 0.0)),  # ... or cannot see a marked image at all
        ("canvas_nonblank", _set(("canvas",), None)),
        ("embed_hidden", _set(("embed", ".navbar"), "flex")),
        ("embed_hidden", _set(("embed", "#toolbar-left"), "block")),
        ("embed_hidden", _set(("embed", "#stats-panel"), "block")),
        ("embed_hidden", _set(("embed", "#sidepanel"), "block")),
        ("embed_hidden", _set(("embed", "#toolbar"), "block")),
        ("embed_hidden", _set(("embed", "#toolbar"), None)),  # the element was not found: nothing was verified hidden
        ("click_focuses", _set(("click", "at_after"), [0.0, 0.0, 0.0])),
        ("click_focuses", _set(("click", "footer_after"), "assay")),
        ("click_focuses", _set(("click", "footer_before"), "source")),  # already focused: the click proves nothing
        ("click_focuses", _set(("click", "at_before"), None)),
        ("follow_focuses", _set(("follow_on", "footer"), "source")),
        ("follow_focuses", _set(("follow_on", "focused"), "source")),
        ("follow_focuses", _set(("follow_on", "at_after"), [120.0, 80.0, 10.0])),
        ("follow_focuses", _set(("follow_on", "enabled"), False)),
        ("follow_off_holds", _set(("follow_off", "at_after"), [0.0, 0.0, 0.0])),
        ("follow_off_holds", _set(("follow_off", "footer_after"), "tips_300")),
        ("follow_off_holds", _set(("follow_off", "enabled"), True)),  # Follow was never off: vacuous
        ("follow_skips_null", _set(("follow_null", "at_after"), [0.0, 0.0, 0.0])),
        ("follow_skips_null", _set(("follow_null", "footer_after"), "source")),
        ("follow_skips_null", _set(("follow_null", "enabled"), False)),
        ("follow_skips_null", _set(("follow_null", "ledger_resources"), ["assay"])),  # the cell names a resource: not a null cell
        ("follow_skips_null", _set(("follow_null", "ledger_resources"), [None, "assay"])),
        ("follow_skips_null", _set(("follow_null", "ledger_resources"), [])),  # no output at all: vacuous
        ("preset_directions", _set(("presets", "top"), None)),
        ("follow_keeps_preset", _set(("follow_keeps", "camera"), None)),
        ("follow_keeps_preset", _set(("follow_keeps", "footer_after"), "assay")),  # Follow never focused anything new
        ("follow_keeps_preset", _set(("follow_keeps", "pressed"), "front")),
        ("state_updates", _set(("state", "after"), '{"volume": 200}')),
        ("state_updates", _set(("state", "before"), None)),
        ("state_updates", _set(("state", "after"), None)),
        ("state_updates", _set(("state", "well"), "")),
        ("stale_and_panel", _set(("stale", "changed_notices"), 0)),
        ("stale_and_panel", _set(("stale", "notice_text"), "Changed since.")),
        ("stale_and_panel", _set(("stale", "panel_state"), "closed")),
    ],
)
def test_k1a_negative_controls_each_violation_fails_exactly_its_key(rs, key, fn):
    failing, _ = _mut(rs, fn)
    assert failing == [key], failing


@pytest.mark.parametrize("name,other", [("top", "front"), ("front", "iso"), ("iso", "top")])
def test_k1a_preset_directions_fails_when_any_one_preset_points_the_wrong_way(rs, name, other):
    failing, _ = _mut(rs, lambda raw: raw["presets"].__setitem__(name, cam_for(rs, other)))
    assert failing == ["preset_directions"]


def test_k1a_follow_keeps_preset_needs_the_top_direction_not_another_preset(rs):
    failing, _ = _mut(rs, lambda raw: raw["follow_keeps"].__setitem__("camera", cam_for(rs, "iso")))
    assert failing == ["follow_keeps_preset"]


def test_canvas_nonblank_fraction_is_strictly_above_one_percent(rs):
    assert rs.canvas_nonblank({"diff_pixels": 3601, "total_pixels": 360000, "control_blank": 0.0, "control_marked": 0.05}) is True
    assert rs.canvas_nonblank({"diff_pixels": 3600, "total_pixels": 360000, "control_blank": 0.0, "control_marked": 0.05}) is False
    assert rs.canvas_fraction({"diff_pixels": 1, "total_pixels": 4}) == 0.25
    assert rs.canvas_fraction({"diff_pixels": 1, "total_pixels": 0}) is None
    assert rs.canvas_fraction(None) is None


# =========================================================================== #
# Sprint C (C7): K1b -- AC-38. The pure key derivation over the page evidence and the ordered event log.
# =========================================================================== #
#
# The event log is what the harness's in-page monitor saw, in ONE sequence: `bc` (a praxis_viz3d message: kind,
# viewer), `iframe_inserted` / `iframe_removed` / `iframe_load` (deck iframes, with the `viewer` parameter of their
# `src`) and `mark` (a named point the harness drew). Ordering claims are read off `seq`, never off timestamps.


def cam_for_name(name):
    """A camera pointing along a preset direction (no fixture: pure constants)."""
    v = {"iso": (-0.7, -1.0, 0.85), "top": (0.0, -0.001, 1.0), "front": (0.0, -1.0, 0.12)}[name]
    return {"from": [10.0 * c for c in v], "at": [0.0, 0.0, 0.0]}


def ev(seq, type_, **kw):
    return {"seq": seq, "type": type_, **kw}


def redock_events():
    return [
        ev(1, "mark", name="redock_live"),
        ev(2, "bc", kind="close", viewer="v-1"),
        ev(3, "iframe_removed", src_viewer="v-1"),
        ev(4, "bc", kind="announce", viewer="v-2"),
        ev(5, "iframe_inserted", src_viewer="v-2"),
        ev(6, "iframe_load", src_viewer="v-2"),
    ]


def late_events():
    return [
        ev(10, "mark", name="late_iframe_reopen"),
        ev(11, "bc", kind="query", viewer=None),
        ev(12, "bc", kind="announce", viewer="v-9"),
        ev(13, "iframe_inserted", src_viewer="v-9"),
        ev(14, "iframe_load", src_viewer="v-9"),
    ]


def good_k1b(rs):
    return {
        "reconnect": {"iframes_before": 1, "iframes_after": 1, "load_delta": 1, "resources_ok": True},
        "preset": {"pressed": "front", "camera": cam_for(rs, "front"), "iframes": 1, "load_delta": 1, "resources_ok": True},
        "drawer_reconnect": {
            "drawer": {"home": "drawer", "iframes": 1, "load_delta": 1, "resources_ok": True},
            "split": {"home": "split", "iframes": 1, "load_delta": 1, "resources_ok": True},
        },
        "redock_live": {"v1": "v-1", "v2": "v-2", "events": redock_events(), "iframes_final": [{"src_viewer": "v-2"}],
                        "resources_ok": True},
        "stop": {"text": "No deck viewer is running. Run `viewer = await praxis.viz.viewer3d.dock(deck)` in a cell.",
                 "iframes": 0, "state": "open-waiting"},
        "redock_reloads": {"iframes": [{"src_viewer": "v-3"}], "kernel_viewer": "v-3", "resources_ok": True,
                           "state": "open-connected"},
        "late_iframe": {
            "after_tab_close": {"state": "closed", "iframes": 0},
            "after_dock_closed": {"state": "closed", "iframes": 0},
            "events": late_events(), "final": {"state": "open-connected", "iframes": [{"src_viewer": "v-9"}]},
            "resources_ok": True,
        },
        "many_reloads": {"rounds": [{"resources_ok": True, "iframes": 1, "load_delta": 1} for _ in range(6)]},
        "restart": {"text": "No deck viewer is running. Run `viewer = ...` in a cell.", "iframes": 0, "state": "open-waiting",
                    "closes_posted": 0},
    }


def test_k1b_positive_control_every_listed_key_holds_in_the_listed_order(rs):
    keys = rs.derive_k1b_keys(good_k1b(rs))
    unit = rs.UNIT_BY_ID["K1b"]
    assert rs.evaluate_unit_result(unit, keys) == ([], []), keys
    assert list(keys)[: len(K1B_KEYS)] == list(K1B_KEYS), "derived in the AC-38 execution order"


def test_k1b_empty_or_garbage_evidence_fails_every_key_without_raising(rs):
    for raw in ({}, None, {"reconnect": 3, "redock_live": None, "late_iframe": "x"}):
        keys = rs.derive_k1b_keys(raw)
        missing, failing = rs.evaluate_unit_result(rs.UNIT_BY_ID["K1b"], keys)
        assert missing == [] and set(failing) == set(K1B_KEYS), (raw, failing)


def _mutk1b(rs, fn):
    raw = copy.deepcopy(good_k1b(rs))
    fn(raw)
    return rs.evaluate_unit_result(rs.UNIT_BY_ID["K1b"], rs.derive_k1b_keys(raw))[1]


def _events(path, fn):
    """Apply ``fn`` to the event list at ``raw[path[0]]['events']``."""
    def apply(raw):
        raw[path]["events"] = fn(raw[path]["events"])
    return apply


def _drop(seq):
    return lambda events: [e for e in events if e["seq"] != seq]


def _edit(target, **changes):
    return lambda events: [dict(e, **changes) if e["seq"] == target else e for e in events]


def _append(*more):
    return lambda events: events + list(more)


@pytest.mark.parametrize(
    "key,fn",
    [
        # reconnect_after_reload (T16)
        ("reconnect_after_reload", _set(("reconnect", "resources_ok"), False)),
        ("reconnect_after_reload", _set(("reconnect", "iframes_after"), 2)),  # I1: exactly one iframe in the panel DOM
        ("reconnect_after_reload", _set(("reconnect", "iframes_after"), 0)),
        ("reconnect_after_reload", _set(("reconnect", "load_delta"), 0)),  # nothing reloaded: the key would be vacuous
        ("reconnect_after_reload", _set(("reconnect", "iframes_before"), 0)),
        # preset_survives_reload (T16, D12)
        ("preset_survives_reload", _set(("preset", "camera"), None)),
        ("preset_survives_reload", _set(("preset", "camera"), cam_for_name("iso"))),
        ("preset_survives_reload", _set(("preset", "resources_ok"), False)),
        ("preset_survives_reload", _set(("preset", "pressed"), "top")),  # the harness must have pressed Front
        ("preset_survives_reload", _set(("preset", "load_delta"), 0)),
        ("preset_survives_reload", _set(("preset", "iframes"), 2)),
        # drawer_reconnect (T15, twice)
        ("drawer_reconnect", _set(("drawer_reconnect", "drawer", "resources_ok"), False)),
        ("drawer_reconnect", _set(("drawer_reconnect", "split", "resources_ok"), False)),
        ("drawer_reconnect", _set(("drawer_reconnect", "drawer", "home"), "split")),
        ("drawer_reconnect", _set(("drawer_reconnect", "split", "home"), "drawer")),
        ("drawer_reconnect", _set(("drawer_reconnect", "split", "iframes"), 0)),
        ("drawer_reconnect", _set(("drawer_reconnect", "drawer", "load_delta"), 0)),
        # redock_live (T12 -> T6)
        ("redock_live", _set(("redock_live", "resources_ok"), False)),
        ("redock_live", _set(("redock_live", "v2"), "v-1")),  # the new viewer has the old id: nothing was re-docked
        ("redock_live", _set(("redock_live", "v2"), None)),
        ("redock_live", _set(("redock_live", "iframes_final"), [{"src_viewer": "v-2"}, {"src_viewer": "v-2"}])),
        ("redock_live", _set(("redock_live", "iframes_final"), [{"src_viewer": "v-1"}])),
        ("redock_live", _events("redock_live", _drop(2))),  # no close for v1 at all
        ("redock_live", _events("redock_live", _edit(2, viewer="v-0"))),  # a close for another viewer
        ("redock_live", _events("redock_live", _edit(2, seq=5))),  # the close arrives AFTER the announce
        ("redock_live", _events("redock_live", _drop(3))),  # the v1 iframe was never removed
        ("redock_live", _events("redock_live", _edit(3, src_viewer="v-x"))),
        ("redock_live", _events("redock_live", _drop(5))),  # no iframe inserted after the announce
        ("redock_live", _events("redock_live", _edit(5, src_viewer="v-1"))),  # inserted pointing at the old viewer
        ("redock_live", _events("redock_live", _edit(5, src_viewer=None))),
        ("redock_live", _events("redock_live", _append(ev(7, "iframe_inserted", src_viewer="v-2")))),  # two inserts
        ("redock_live", _events("redock_live", _drop(4))),  # no announce
        # stop_placeholder (T12)
        ("stop_placeholder", _set(("stop", "text"), "The deck view lost its connection. Close and reopen the deck panel.")),
        ("stop_placeholder", _set(("stop", "text"), "No deck viewer is running. The deck view lost its connection.")),
        ("stop_placeholder", _set(("stop", "iframes"), 1)),
        ("stop_placeholder", _set(("stop", "text"), "")),
        ("stop_placeholder", _set(("stop", "text"), None)),
        ("stop_placeholder", _set(("stop", "state"), "open-lost")),
        # redock_reloads (T6)
        ("redock_reloads", _set(("redock_reloads", "iframes"), [])),
        ("redock_reloads", _set(("redock_reloads", "iframes"), [{"src_viewer": "v-3"}, {"src_viewer": "v-3"}])),
        ("redock_reloads", _set(("redock_reloads", "kernel_viewer"), "v-4")),  # src names another viewer than the kernel's
        ("redock_reloads", _set(("redock_reloads", "kernel_viewer"), None)),
        ("redock_reloads", _set(("redock_reloads", "resources_ok"), False)),
        ("redock_reloads", _set(("redock_reloads", "state"), "open-waiting")),
        # late_iframe (T17, T3, T4, T6)
        ("late_iframe", _set(("late_iframe", "resources_ok"), False)),
        ("late_iframe", _set(("late_iframe", "after_tab_close"), {"state": "open-connected", "iframes": 0})),
        ("late_iframe", _set(("late_iframe", "after_tab_close"), {"state": "closed", "iframes": 1})),
        ("late_iframe", _set(("late_iframe", "after_dock_closed"), {"state": "open-connected", "iframes": 1})),
        ("late_iframe", _set(("late_iframe", "after_dock_closed"), {"state": "closed", "iframes": 1})),
        ("late_iframe", _events("late_iframe", _drop(11))),  # no query posted after the reopen (AC-39(e)'s mutation)
        ("late_iframe", _events("late_iframe", _edit(11, kind="accept"))),
        ("late_iframe", _events("late_iframe", _drop(12))),  # no announce
        ("late_iframe", _events("late_iframe", _edit(11, seq=12.5))),  # the query comes AFTER the announce
        ("late_iframe", _events("late_iframe", _edit(13, seq=11.5))),  # an iframe inserted before the announce
        ("late_iframe", _events("late_iframe", _edit(13, src_viewer=None))),  # src not yet carrying the viewer id
        ("late_iframe", _events("late_iframe", _edit(13, src_viewer="v-0"))),
        ("late_iframe", _events("late_iframe", _drop(13))),
        ("late_iframe", _set(("late_iframe", "final"), {"state": "open-connected", "iframes": []})),
        ("late_iframe", _set(("late_iframe", "final"), {"state": "open-connected", "iframes": [{"src_viewer": "v-9"}] * 2})),
        ("late_iframe", _set(("late_iframe", "final"), {"state": "open-waiting", "iframes": [{"src_viewer": "v-9"}]})),
        # many_reloads (T16)
        ("many_reloads", _set(("many_reloads", "rounds"), [{"resources_ok": True, "iframes": 1, "load_delta": 1}] * 5)),
        ("many_reloads", _set(("many_reloads", "rounds"), [{"resources_ok": True, "iframes": 1, "load_delta": 1}] * 7)),
        ("many_reloads", _set(("many_reloads", "rounds"), [])),
        ("many_reloads", _set(("many_reloads", "rounds"), [{"resources_ok": True, "iframes": 1, "load_delta": 1}] * 5
                                                          + [{"resources_ok": False, "iframes": 1, "load_delta": 1}])),
        ("many_reloads", _set(("many_reloads", "rounds"), [{"resources_ok": True, "iframes": 1, "load_delta": 1}] * 5
                                                          + [{"resources_ok": True, "iframes": 2, "load_delta": 1}])),
        ("many_reloads", _set(("many_reloads", "rounds"), [{"resources_ok": True, "iframes": 1, "load_delta": 0}] * 6)),
        # restart_placeholder (T25)
        ("restart_placeholder", _set(("restart", "text"), "The deck view lost its connection.")),
        ("restart_placeholder", _set(("restart", "iframes"), 1)),
        ("restart_placeholder", _set(("restart", "closes_posted"), 1)),  # a close drove it: not the restart
        ("restart_placeholder", _set(("restart", "closes_posted"), None)),
        ("restart_placeholder", _set(("restart", "text"), None)),
    ],
)
def test_k1b_negative_controls_each_violation_fails_exactly_its_key(rs, key, fn):
    assert _mutk1b(rs, fn) == [key]


def test_the_ordering_helpers_read_seq_not_list_position(rs):
    """A log whose LIST order is shuffled but whose `seq` is right must give the same verdict."""
    raw = good_k1b(rs)
    raw["redock_live"]["events"] = list(reversed(raw["redock_live"]["events"]))
    raw["late_iframe"]["events"] = list(reversed(raw["late_iframe"]["events"]))
    assert rs.evaluate_unit_result(rs.UNIT_BY_ID["K1b"], rs.derive_k1b_keys(raw)) == ([], [])


def test_redock_live_ok_requires_the_inserted_iframe_to_be_the_only_one_after_the_announce(rs):
    ok = rs.redock_live_ok(good_k1b(rs)["redock_live"])
    assert ok is True
    raw = good_k1b(rs)["redock_live"]
    raw["events"] = redock_events() + [ev(7, "iframe_removed", src_viewer="v-2"), ev(8, "iframe_inserted", src_viewer="v-2")]
    assert rs.redock_live_ok(raw) is False, "a replaced element after the announce is a second insertion"


# =========================================================================== #
# Sprint C (C7): K2 (AC-36) and N-d (AC-39(d)) -- the pure key derivations over the page evidence.
# =========================================================================== #


def good_k2():
    wide = lambda main, panel, nb=960.0: {"nb": nb, "panel": panel, "main": main, "padding": 0.0}  # noqa: E731
    return {
        "drawer": {"nb_before": 1000.0, "nb_open": 1000.0, "position": "fixed", "home": "drawer", "state": "open-connected"},
        "dismiss": {
            "first_open": {"state": "open-connected", "home": "drawer", "iframes": 1},
            "after_close_button": {"state": "closed", "iframes": 0},
            "after_toggle": {"state": "open-connected", "iframes": 1},
            "after_escape": {"state": "closed", "iframes": 0},
            "after_reopen": {"state": "open-connected", "iframes": 1},
        },
        "tier_up": {
            "before": {"home": "drawer", "state": "open-connected", "iframes": 1, "src": "S"},
            "after_up": {"home": "split", "state": "open-connected", "iframes": 1, "src": "S", "split_right": True,
                         "resources_ok": True},
            "back_down": {"home": "drawer", "state": "open-connected", "iframes": 1},
            "after_button_close": {"state": "closed", "iframes": 0},
            "after_up_closed": {"state": "closed", "iframes": 0},
            "reopen": {"home": "split", "state": "open-connected", "iframes": 1},
        },
        "medium": {
            "1440": {"open": 450.0, "drag_low": 420.0, "drag_high": 480.0},
            "1280": {"open": 430.0, "drag_low": 420.0, "drag_high": 480.0},
        },
        "fit": {"wide": {"panel": 611.0, "main": 1571.0, "padding": 0.0}, "medium": {"panel": 450.0}},
        "wide": {"1600": wide(1571.0, 611.0), "1920": wide(1891.0, 931.0)},
        "resize": {"panel": 931.0, "main": 1891.0, "padding": 0.0},
        "reloads": {"drag_1440": 0, "drag_1280": 0, "resize_within_wide": 0},
        "heights": {"viewer": 420.0, "motion": 24.0},
    }


def _k2(rs, raw, record=None):
    return rs.derive_k2_keys(raw, record=record or rs.SIZING_RECORD)


def test_k2_positive_control_every_listed_key_holds(rs):
    keys = _k2(rs, good_k2())
    assert rs.evaluate_unit_result(rs.UNIT_BY_ID["K2"], keys) == ([], []), keys
    assert set(K2_ALL_KEYS) <= set(keys)


def test_k2_names_the_sizing_case_and_lists_each_width_key_as_asserted_or_recorded_only(rs):
    keys = _k2(rs, good_k2())
    assert keys["sizing_case"] == "honoured_reachable"
    assert keys["sizing_record"] == rs.SIZING_RECORD
    status = keys["width_key_status"]
    assert set(status) == {k for k, _ in K2_WIDTH} and set(status.values()) == {"asserted"}
    assert keys["ac39d"] == "run"


def test_k2_recorded_only_keys_are_still_measured_and_reported_but_marked(rs):
    record = {"css_limits_honoured": True, "layout_sizing_reachable": False, "css_limits_refit": False,
              "restore_layout_keeps_iframe": True}
    keys = _k2(rs, good_k2(), record)
    assert keys["sizing_case"] == "honoured_unreachable"
    status = keys["width_key_status"]
    for k in ("panel_width_wide_1600", "panel_width_wide_1920", "resize_within_wide", "fit_after_tier_change_wide"):
        assert status[k] == "recorded-only" and keys[k] is True, k
    for k in ("open_width_1440", "drag_clamp_low_1280", "fit_after_tier_change_medium"):
        assert status[k] == "asserted", k
    assert keys["ac39d"] == "skipped"
    # a recorded-only key can be WRONG without any listed key failing (that is what recorded-only means) ...
    raw = good_k2()
    raw["wide"]["1600"]["panel"] = 800.0
    k2 = rs.UNIT_BY_ID["K2"]
    assert rs.derive_k2_keys(raw, record=record)["panel_width_wide_1600"] is False
    # ... while the listed keys the table was built for under THAT case ignore it
    listed = dict(rs.k2_expected(rs.width_key_status(**record)))
    assert "panel_width_wide_1600" not in listed and k2 is not None


def _mutk2(rs, fn):
    raw = good_k2()
    fn(raw)
    return rs.evaluate_unit_result(rs.UNIT_BY_ID["K2"], _k2(rs, raw))[1]


def _k2set(path, value):
    def apply(raw):
        d = raw
        for p in path[:-1]:
            d = d[p]
        d[path[-1]] = value
    return apply


@pytest.mark.parametrize(
    "key,fn",
    [
        # step 1: drawer_overlays, drawer_no_reflow
        ("drawer_overlays", _k2set(("drawer", "position"), "static")),
        ("drawer_overlays", _k2set(("drawer", "position"), "absolute")),
        ("drawer_overlays", _k2set(("drawer", "home"), "split")),
        ("drawer_overlays", _k2set(("drawer", "state"), "closed")),
        ("drawer_no_reflow", _k2set(("drawer", "nb_open"), 700.0)),
        ("drawer_no_reflow", _k2set(("drawer", "nb_open"), 1001.0)),
        ("drawer_no_reflow", _k2set(("drawer", "nb_before"), None)),
        # step 2: drawer_dismiss_reopen (close button T17, toggle T4 -> T6, Escape T17, then reopen)
        ("drawer_dismiss_reopen", _k2set(("dismiss", "first_open"), {"state": "closed", "home": "drawer", "iframes": 0})),
        ("drawer_dismiss_reopen", _k2set(("dismiss", "after_close_button"), {"state": "closed", "iframes": 1})),
        ("drawer_dismiss_reopen", _k2set(("dismiss", "after_close_button"), {"state": "open-connected", "iframes": 0})),
        ("drawer_dismiss_reopen", _k2set(("dismiss", "after_toggle"), {"state": "open-waiting", "iframes": 0})),
        ("drawer_dismiss_reopen", _k2set(("dismiss", "after_toggle"), {"state": "open-connected", "iframes": 2})),
        ("drawer_dismiss_reopen", _k2set(("dismiss", "after_escape"), {"state": "open-connected", "iframes": 1})),
        ("drawer_dismiss_reopen", _k2set(("dismiss", "after_escape"), {"state": "closed", "iframes": 1})),
        ("drawer_dismiss_reopen", _k2set(("dismiss", "after_reopen"), {"state": "closed", "iframes": 0})),
        # step 3: tier_up_rehomes (T15, T15, T17, T5, T4 -> T6)
        ("tier_up_rehomes", _k2set(("tier_up", "after_up", "home"), "drawer")),
        ("tier_up_rehomes", _k2set(("tier_up", "after_up", "split_right"), False)),
        ("tier_up_rehomes", _k2set(("tier_up", "after_up", "src"), "OTHER")),  # the iframe did not keep its src
        ("tier_up_rehomes", _k2set(("tier_up", "after_up", "iframes"), 2)),
        ("tier_up_rehomes", _k2set(("tier_up", "after_up", "resources_ok"), False)),
        ("tier_up_rehomes", _k2set(("tier_up", "before", "home"), "split")),
        ("tier_up_rehomes", _k2set(("tier_up", "back_down", "home"), "split")),
        ("tier_up_rehomes", _k2set(("tier_up", "after_button_close"), {"state": "open-connected", "iframes": 1})),
        ("tier_up_rehomes", _k2set(("tier_up", "after_up_closed"), {"state": "open-connected", "iframes": 1})),  # T5: stays closed
        ("tier_up_rehomes", _k2set(("tier_up", "after_up_closed"), {"state": "closed", "iframes": 1})),
        ("tier_up_rehomes", _k2set(("tier_up", "reopen"), {"home": "split", "state": "open-waiting", "iframes": 0})),
        ("tier_up_rehomes", _k2set(("tier_up", "reopen"), {"home": "drawer", "state": "open-connected", "iframes": 1})),
        # step 4 and 6: the 1280-1599 keys
        ("open_width_1440", _k2set(("medium", "1440", "open"), 600.0)),
        ("open_width_1440", _k2set(("medium", "1440", "open"), 300.0)),
        ("open_width_1440", _k2set(("medium", "1440", "open"), None)),
        ("drag_clamp_low_1440", _k2set(("medium", "1440", "drag_low"), 300.0)),  # not clamped: the drag went through
        ("drag_clamp_low_1440", _k2set(("medium", "1440", "drag_low"), 450.0)),
        ("drag_clamp_high_1440", _k2set(("medium", "1440", "drag_high"), 700.0)),
        ("drag_clamp_high_1440", _k2set(("medium", "1440", "drag_high"), 450.0)),
        ("open_width_1280", _k2set(("medium", "1280", "open"), 700.0)),
        ("drag_clamp_low_1280", _k2set(("medium", "1280", "drag_low"), 300.0)),
        ("drag_clamp_high_1280", _k2set(("medium", "1280", "drag_high"), 700.0)),
        # step 5: fit_after_tier_change (both tiers)
        ("fit_after_tier_change_wide", _k2set(("fit", "wide", "panel"), 480.0)),  # still the 1440 clamp at 1600
        ("fit_after_tier_change_wide", _k2set(("fit", "wide", "main"), None)),
        ("fit_after_tier_change_medium", _k2set(("fit", "medium", "panel"), 611.0)),  # still the 1600 width at 1440
        ("fit_after_tier_change_medium", _k2set(("fit", "medium", "panel"), None)),
        # step 6: heights
        ("viewer_height", _k2set(("heights", "viewer"), 299.0)),
        ("viewer_height", _k2set(("heights", "viewer"), None)),
        ("motion_slot_height", _k2set(("heights", "motion"), 37.0)),
        ("motion_slot_height", _k2set(("heights", "motion"), None)),
        # step 7 and 9: the >= 1600 keys
        ("nb_content_width_1600", _k2set(("wide", "1600", "nb"), 961.0)),
        ("nb_content_width_1600", _k2set(("wide", "1600", "nb"), None)),
        ("panel_width_wide_1600", _k2set(("wide", "1600", "panel"), 785.0)),  # the stock 50/50 split
        ("panel_width_wide_1600", _k2set(("wide", "1600", "panel"), 420.0)),
        ("panel_width_wide_1600", _k2set(("wide", "1600", "padding"), 40.0)),  # the formula moves with the padding
        ("nb_content_width_1920", _k2set(("wide", "1920", "nb"), 1200.0)),
        ("panel_width_wide_1920", _k2set(("wide", "1920", "panel"), 611.0)),  # the 1600 width carried over to 1920
        ("panel_width_wide_1920", _k2set(("wide", "1920", "panel"), None)),
        # step 8: resize_within_wide and the reload count
        ("resize_within_wide", _k2set(("resize", "panel"), 611.0)),  # not recomputed after the window grew
        ("resize_within_wide", _k2set(("resize", "main"), None)),
        ("iframe_reloads_during_resize", _k2set(("reloads", "resize_within_wide"), 1)),
        ("iframe_reloads_during_resize", _k2set(("reloads", "drag_1440"), 2)),
        ("iframe_reloads_during_resize", _k2set(("reloads", "drag_1280"), 1)),
        ("iframe_reloads_during_resize", _k2set(("reloads", "drag_1280"), None)),  # a window nobody counted
    ],
)
def test_k2_negative_controls_each_violation_fails_exactly_its_key(rs, key, fn):
    assert _mutk2(rs, fn) == [key]


def test_k2_empty_evidence_fails_every_listed_key_without_raising(rs):
    for raw in ({}, None, {"drawer": 3, "wide": None}):
        keys = _k2(rs, raw)
        missing, failing = rs.evaluate_unit_result(rs.UNIT_BY_ID["K2"], keys)
        assert missing == [] and set(failing) == K2_ALL_KEYS, (raw, sorted(set(failing) ^ K2_ALL_KEYS))


def test_k2_iframe_reload_count_is_the_sum_over_the_drags_and_the_resize_and_must_be_int_zero(rs):
    keys = _k2(rs, good_k2())
    assert keys["iframe_reloads_during_resize"] == 0 and type(keys["iframe_reloads_during_resize"]) is int
    raw = good_k2()
    raw["reloads"] = {"drag_1440": 1, "drag_1280": 2, "resize_within_wide": 3}
    assert _k2(rs, raw)["iframe_reloads_during_resize"] == 6
    raw["reloads"] = {"drag_1440": 0.0, "drag_1280": 0, "resize_within_wide": 0}
    assert _k2(rs, raw)["iframe_reloads_during_resize"] is None, "a float or bool count is not a count"


def test_k2_drawer_no_reflow_is_zero_px_with_a_half_pixel_allowance(rs):
    raw = good_k2()
    raw["drawer"]["nb_open"] = 1000.4
    assert _k2(rs, raw)["drawer_no_reflow"] is True
    raw["drawer"]["nb_open"] = 1000.6
    assert _k2(rs, raw)["drawer_no_reflow"] is False


def test_the_resize_windows_are_recorded_even_when_a_width_key_is_recorded_only(rs):
    """AC-36: iframe_reloads_during_resize is asserted in EVERY sizing case, so every case still lists it."""
    for hon in (True, False):
        for reach in (True, False):
            status = rs.width_key_status(css_limits_honoured=hon, layout_sizing_reachable=reach, css_limits_refit=False)
            assert "iframe_reloads_during_resize" in {k for k, _ in rs.k2_expected(status)}


# -- N-d -----------------------------------------------------------------------------------------------------


def good_nd():
    return {"panel": 785.0, "notebook": 786.0, "main": 1571.0, "padding": 0.0}


def test_n_d_stock_even_split_makes_the_wide_width_predicate_report_failure(rs):
    keys = rs.derive_nd_keys(good_nd(), record=rs.SIZING_RECORD)
    assert keys["panel_width_wide_1600"] is False, "a 50/50 split is not max(420, main - 960 - padding)"
    assert keys["skipped"] is False and keys["control_formula_passes"] is True
    assert rs.evaluate_unit_result(rs.UNIT_BY_ID["N-d"], keys) == ([], ["panel_width_wide_1600"]), "it FAILS, by design"


def test_n_d_positive_control_the_predicate_passes_on_the_width_the_formula_gives(rs):
    """Without this the negative could pass because the predicate can never pass."""
    raw = dict(good_nd(), panel=rs.wide_panel_width_expected(1571.0, 0.0))
    # not an even split any more, so this is a control of the PREDICATE only
    assert rs.wide_width_ok(raw["panel"], raw["main"], raw["padding"]) is True
    assert rs.derive_nd_keys(good_nd(), record=rs.SIZING_RECORD)["control_formula_passes"] is True


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update(panel=None),
        lambda r: r.update(panel=0.0),
        lambda r: r.update(main=None),
        lambda r: r.update(main=0.0),
        lambda r: r.update(padding=None),
        lambda r: r.update(notebook=None),
        lambda r: r.update(panel=300.0, notebook=1271.0),  # not an even split: the widget was not split 50/50
        lambda r: r.update(panel=1571.0),
    ],
)
def test_n_d_an_invalid_measurement_is_an_error_never_a_detected_negative(rs, mutate):
    """A None or absurd measurement would make the predicate 'fail' for the wrong reason: the sensitivity run would
    pass vacuously. The unit raises instead (an `error` finding, which never passes a negative's outcome)."""
    raw = good_nd()
    mutate(raw)
    with pytest.raises(rs.DockCheckError):
        rs.derive_nd_keys(raw, record=rs.SIZING_RECORD)


def test_n_d_is_skipped_and_says_so_where_the_ge_1600_key_is_recorded_only(rs):
    record = {"css_limits_honoured": True, "layout_sizing_reachable": False, "css_limits_refit": False,
              "restore_layout_keeps_iframe": True}
    keys = rs.derive_nd_keys({}, record=record)  # nothing is measured when skipped
    assert keys["skipped"] is True and "panel_width_wide_1600" not in keys and keys["skipped_reason"]
    unit = dataclasses.replace(rs.UNIT_BY_ID["N-d"], expected=rs.nd_expected(rs.width_key_status(**record)))
    assert rs.evaluate_unit_result(unit, keys) == ([], [])


# =========================================================================== #
# Sprint C (C7): the dock scenario bodies, the notebook they drive, the session, the in-page helpers, the CLI
# =========================================================================== #
#
# The scenarios take a `driver` so their ORDER and key plumbing are tested against a scripted fake: `FakeDock` is a
# small simulator of the deck panel's state machine (D11) and of the page the iframe holds. A real browser run
# exercises `DockSession`, `DockDriver` and the in-page helpers; none of it runs here.

import ast as _ast  # noqa: E402

DOCK_CELLS = ("boot", "assemble", "pickup", "draw-source", "draw-assay", "draw-tips", "draw-deck", "aspirate",
              "dock", "hello", "viewer-id", "well-name", "ledger", "stop")


@pytest.fixture(scope="module")
def dnb(rs, nb):
    return rs.build_dock_notebook(nb)


def test_dock_notebook_is_the_fixture_cells_then_the_dock_cells_never_executed(rs, nb, dnb):
    assert [c["id"] for c in dnb["cells"]] == list(DOCK_CELLS)
    assert rs.DOCK_CELL_IDS == DOCK_CELLS and rs.DOCK_NOTEBOOK_NAME == "dock_check.ipynb"
    for cell in dnb["cells"]:
        assert cell["cell_type"] == "code" and cell["outputs"] == [] and cell["execution_count"] is None
    src = {c["id"]: c["source"] for c in nb["cells"]}
    for cid in DOCK_CELLS[:8]:  # cloned from the fixture, so its hash covers them
        assert dnb["cells"][DOCK_CELLS.index(cid)]["source"] == src[cid], cid
    assert {k: v for k, v in dnb.items() if k != "cells"} == {k: v for k, v in nb.items() if k != "cells"}


def test_dock_notebook_does_not_mutate_the_fixture_it_was_built_from(rs, nb):
    before = json.dumps(nb, sort_keys=True)
    rs.build_dock_notebook(nb)
    assert json.dumps(nb, sort_keys=True) == before


def test_dock_notebook_refuses_a_fixture_lacking_a_cell_it_clones(rs, nb):
    broken = {**nb, "cells": [c for c in nb["cells"] if c["id"] != "pickup"]}
    with pytest.raises(KeyError):
        rs.build_dock_notebook(broken)


def _dsrc(dnb, cid):
    return "".join(next(c for c in dnb["cells"] if c["id"] == cid)["source"])


def test_dock_cells_parse_with_top_level_await(dnb):
    for cell in dnb["cells"]:
        compile("".join(cell["source"]), cell["id"], "exec", flags=_ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)


def test_dock_cells_say_what_ac34_ac35_ac37_and_ac38_need(dnb):
    assert _dsrc(dnb, "dock") == "from praxis.viz.viewer3d import dock\nviewer = await dock(deck)"
    assert _dsrc(dnb, "stop") == "await viewer.stop()"
    assert _dsrc(dnb, "hello") == "viewer.clients_seen[-1]", "D11: evaluated in a cell, read from the output model"
    assert _dsrc(dnb, "viewer-id") == "viewer.viewer_id"
    assert _dsrc(dnb, "well-name") == 'source.get_well("A1").name', "AC-37: the well name is read from the kernel"
    ledger = _dsrc(dnb, "ledger")
    assert "RunLedger(lh)" in ledger and "with " in ledger and "await lh.aspirate" in ledger
    assert ledger.count("display(") == 0, "the ledger is the cell's ONLY Praxis output (resource null)"


def test_dock_cells_carry_no_test_hook_no_serial_prompt_and_no_repl_channel(dnb):
    blob = json.dumps(dnb)
    for token in ("__praxis" + "_test", "data-praxis" + "-test", "requestDevice", "requestPort", "praxis_repl"):
        assert token not in blob, token


def test_parse_py_repr_reads_what_a_cell_evaluates_to(rs):
    assert rs.parse_py_repr("'v-abc123'") == "v-abc123"
    assert rs.parse_py_repr("{'backend': 'WebGL2', 'renderer': 'ANGLE (SwiftShader)'}") == {
        "backend": "WebGL2", "renderer": "ANGLE (SwiftShader)"}
    assert rs.parse_py_repr('"source_well_0"\n') == "source_well_0"
    for bad in (None, "", "Traceback (most recent call last):\n IndexError", "{'a':", "<object at 0x1>"):
        assert rs.parse_py_repr(bad) is None, bad


# -- the simulator -------------------------------------------------------------------------------------------


POS = {"deck": (0.0, 0.0, 0.0), "tips_300": (10.0, 0.0, 0.0), "source": (20.0, 5.0, 0.0), "assay": (30.0, 5.0, 0.0)}


class FakeDock:
    """A scripted ``DockDriver``: every call is recorded in ``calls``; the state machine is D11's, in miniature.

    ``broken`` names behaviours to break (each one makes a real product fail a real key): ``no_resources`` (the viewer
    page never gets a scene, as with socket.js removed), ``drop_query`` (the harness's ``--neg drop-query``),
    ``no_handle`` (no splitter handle can be found), ``lost_clamp`` (a drag is not clamped), ``reload_on_resize``."""

    def __init__(self, rs: Any, nb: dict[str, Any], *, broken: tuple[str, ...] = (), start=(1440, 900)) -> None:
        self.rs, self.broken = rs, set(broken)
        self.ids = {i: c["id"] for i, c in enumerate(nb["cells"])}
        self.calls: list[tuple[Any, ...]] = []
        self.w, self.h = start
        self.left_open = True
        self.state, self.home, self.seen = "closed", None, False
        self.frames: list[dict[str, Any]] = []
        self.current: str | None = None
        self.kernel_viewer: str | None = None
        self.serial = 0
        self.stopped = False
        self.follow, self.preset, self.footer, self.cam_dir = True, "top", None, "top"
        self.at = (0.0, 0.0, 0.0)
        self.seq, self.events, self.loads_n, self.dropped = 0, [], 0, 0
        self.text = ""
        self.drag_w: float | None = None
        self.stamps = {"draw-source": ["source"], "draw-assay": ["assay"], "draw-tips": ["tips_300"],
                       "draw-deck": ["deck"], "ledger": [None]}
        self.source_changed, self.aspirated = 0, False
        self.cell_text: dict[str, str] = {}
        self.restarted = False
        self.closes_by_restart = 0
        self.tab_closed = 0

    # -- plumbing -----------------------------------------------------------------------------------------
    def _log(self, *call: Any) -> None:
        self.calls.append(call)

    def _ev(self, type_: str, **kw: Any) -> int:
        self.seq += 1
        self.events.append({"seq": self.seq, "type": type_, **kw})
        return self.seq

    @property
    def tier(self) -> str:
        return "wide" if self.w >= 1600 else "medium" if self.w >= 1280 else "drawer"

    def _home_for_tier(self) -> str:
        return "drawer" if self.tier == "drawer" else "split"

    # -- session/driver surface the scenarios use ------------------------------------------------------------
    def open_lab(self) -> None:
        self._log("open_lab")

    def set_theme(self, name: str) -> None:
        self._log("set_theme", name)

    def theme_name(self) -> str:
        return "JupyterLab Light"

    def seed_and_open(self, name: str, nb: dict[str, Any]) -> None:
        self._log("seed_and_open", name)

    def wait_kernel_idle(self) -> None:
        self._log("wait_kernel_idle")

    def settle(self, ms: float) -> None:
        pass

    def poll(self, read: Any, ok: Any, timeout_s: float) -> tuple[Any, bool]:
        value = read()
        for _ in range(3):
            if ok(value):
                return value, True
            value = read()
        return value, bool(ok(value))

    def restart_kernel(self, after_accept: Any = None) -> dict[str, Any]:
        self._log("restart_kernel")
        self.restarted = True
        if self.state in ("open-connected", "open-lost"):  # T25: the viewer's kernel went away
            self._remove_frames()
            self.current, self.state, self.text = None, "open-waiting", NO_VIEWER_TEXT
        out: dict[str, Any] = {"via": "kernelmenu:restart"}
        if after_accept is not None:
            out["watch"] = after_accept()
        return out

    def report(self, index: int, res: str | None = None) -> dict[str, Any]:
        cid = self.ids[index]
        changed = self.source_changed if (cid == "draw-source" and res == "source") else 0
        return {"index": index, "execution_count": 1, "outputs": [],
                "res": {"found": True, "changed_notices": changed, "svg_count": 1}}

    # -- world ----------------------------------------------------------------------------------------------
    def _remove_frames(self) -> None:
        for f in self.frames:
            self._ev("iframe_removed", src_viewer=f["src_viewer"])
        self.frames = []

    def _insert_frame(self, viewer: str) -> None:
        self.frames = [{"src_viewer": viewer, "src": f"x?viewer={viewer}"}]
        self._ev("iframe_inserted", src_viewer=viewer)
        self._ev("iframe_load", src_viewer=viewer)
        self.loads_n += 1

    def _connect(self, viewer: str) -> None:
        self.state, self.text = "open-connected", ""
        self.current = viewer
        self._insert_frame(viewer)

    def _announce(self) -> None:
        if self.kernel_viewer is None or self.stopped:
            return
        self._ev("bc", kind="announce", viewer=self.kernel_viewer)
        if self.state == "closed":
            if not self.seen:
                self.home = self._home_for_tier()
                self._connect(self.kernel_viewer)
        elif self.state in ("open-waiting", "open-lost"):
            self._connect(self.kernel_viewer)
        elif self.current != self.kernel_viewer:
            self._remove_frames()
            self._insert_frame(self.kernel_viewer)
            self.current = self.kernel_viewer
        self.seen = True

    def run_cell(self, index: int) -> None:
        cid = self.ids[index]
        self._log("run_cell", cid)
        if cid == "dock":
            if self.kernel_viewer is not None and not self.stopped:  # dock() stops the previous viewer first
                self._ev("bc", kind="close", viewer=self.kernel_viewer)
                if self.state in ("open-connected", "open-lost") and self.current == self.kernel_viewer:
                    self._remove_frames()
                    self.state, self.current, self.text = "open-waiting", None, NO_VIEWER_TEXT
            self.serial += 1
            self.kernel_viewer, self.stopped = f"v-{self.serial}", False
            self._announce()
        elif cid == "stop":
            if self.kernel_viewer is not None and not self.stopped:
                self.stopped = True
                self._ev("bc", kind="close", viewer=self.kernel_viewer)
                if self.state in ("open-connected", "open-lost") and self.current == self.kernel_viewer:
                    self._remove_frames()
                    self.state, self.current, self.text = "open-waiting", None, NO_VIEWER_TEXT
        elif cid == "aspirate":
            self.aspirated = True
            self.source_changed = 1
        elif cid in ("hello", "viewer-id", "well-name"):
            pass
        if cid == "ledger":
            self.aspirated = True

    def kernel_text(self, index: int) -> str | None:
        cid = self.ids[index]
        self._log("kernel_text", cid)
        if cid == "hello":
            if "no_resources" in self.broken or self.kernel_viewer is None:
                return None
            return repr({"backend": "WebGL2", "renderer": "ANGLE (SwiftShader)"})
        if cid == "viewer-id":
            return repr(self.kernel_viewer)
        if cid == "well-name":
            return repr("source_well_0")
        return None

    def set_viewport(self, w: int, h: int) -> None:
        self._log("set_viewport", w, h)
        old_home = self.home
        self.w, self.h = w, h
        if self.state != "closed":
            new_home = self._home_for_tier()
            if old_home != new_home:  # T10 / T15 / T21: re-homed; a DOM move reloads the iframe
                self.home = new_home
                if self.frames:
                    viewer = self.frames[0]["src_viewer"]
                    self._remove_frames()
                    self._insert_frame(viewer)
            elif "reload_on_resize" in self.broken and self.tier == "wide" and self.frames:
                self.loads_n += 1
                self._ev("iframe_load", src_viewer=self.frames[0]["src_viewer"])
        self.drag_w = None

    def snap(self) -> dict[str, Any]:
        return {"state": self.state, "home": self.home, "tier": self.tier, "follow": self.follow, "focused": self.footer,
                "current": self.current, "preset": self.preset, "seen": self.seen}

    def _main(self) -> float:
        return float(self.w - 29 - (280 if self.left_open else 0))

    def _panel_width(self) -> float | None:
        if self.state == "closed":
            return None
        if self.home == "drawer":
            return 480.0
        if self.tier == "medium":
            return self.drag_w if self.drag_w is not None else 450.0
        return max(420.0, self._main() - 960.0) if self.drag_w is None else self.drag_w

    def facts(self) -> dict[str, Any]:
        pw = self._panel_width()
        main = self._main()
        nb_w = main if self.home != "split" or self.state == "closed" else main - (pw or 0)
        if self.w >= 1600:
            nb_w = min(nb_w, 960.0)
        left = main - (pw or 0) if self.home == "split" else self.w - 480.0
        nb_right = main - (pw or 0) if self.home == "split" else main
        return {
            "present": self.state != "closed", "state": self.state, "position": "fixed" if self.home == "drawer" else "static",
            "panel_rect": None if pw is None else {"left": left, "right": left + pw, "width": pw, "height": 600.0},
            "notebook_panel_rect": {"left": 0.0, "right": nb_right, "width": nb_right, "height": 700.0},
            "nb_content_width": nb_w, "nb_h_padding": 0.0, "main_width": main,
            "frames": [dict(f, height=420.0) for f in self.frames],
            "text": self.text, "footer": self.footer if self.footer else "No resource focused.",
            "follow_checked": self.follow, "pressed": [self.preset], "motion_height": 24.0,
            "left_collapsed": not self.left_open, "inner_width": self.w,
        }

    def resources(self) -> list[str] | None:
        if not self.frames or "no_resources" in self.broken:
            return None if not self.frames else []
        return ["deck", "tip_carrier", "tips_300", "plate_carrier", "source", "assay"]

    def camera(self) -> dict[str, Any] | None:
        if not self.frames or "no_resources" in self.broken:
            return None
        d = _dir(self.rs.VIEWS[self.cam_dir])
        return {"from": [a + 500.0 * c for a, c in zip(self.at, d)], "at": list(self.at)}

    def state_of(self, name: str) -> str | None:
        if not self.frames or "no_resources" in self.broken:
            return None
        return json.dumps({"volume": 190 if self.aspirated else 200})

    def wait_connected(self, timeout_s: float = 10.0) -> bool:
        self._log("wait_connected")
        return self.state == "open-connected" and len(self.frames) == 1 and "no_resources" not in self.broken

    def wait_resources(self, timeout_s: float = 10.0) -> bool:
        self._log("wait_resources")
        return len(self.frames) == 1 and "no_resources" not in self.broken

    def wait_load(self, since: Any, timeout_s: float = 15.0) -> bool:
        self._log("wait_load")
        return isinstance(since, int) and self.loads_n > since

    def _focus(self, name: str) -> None:
        self.footer, self.at, self.cam_dir = name, POS[name], self.preset

    def click_resource(self, index: int, name: str) -> bool:
        self._log("click_resource", self.ids[index], name)
        if self.state != "open-connected" or "no_resources" in self.broken:
            return True
        self._focus(name)
        return True

    def click_cell_input(self, index: int) -> bool:
        cid = self.ids[index]
        self._log("click_cell_input", cid)
        if self.follow and self.state == "open-connected" and "no_resources" not in self.broken:
            res = next((r for r in self.stamps.get(cid, []) if r), None)
            if res:
                self._focus(res)
        return True

    def click_follow(self) -> None:
        self._log("click_follow")
        self.follow = not self.follow

    def click_preset(self, name: str) -> None:
        self._log("click_preset", name)
        self.preset = name
        if self.state == "open-connected" and "no_resources" not in self.broken:
            self.cam_dir = name

    def click_drawer_close(self) -> None:
        self._log("click_drawer_close")
        if self.home == "drawer" and self.state != "closed":
            self._close()

    def press_escape(self) -> None:
        self._log("press_escape")
        if self.home == "drawer" and self.state != "closed":
            self._close()

    def _close(self) -> None:
        self._remove_frames()
        self.state, self.current, self.footer, self.text = "closed", None, None, ""

    def toggle_panel(self) -> None:
        self._log("toggle_panel")
        if self.state != "closed":
            self._close()
            return
        self.home = self._home_for_tier()
        self.state, self.text = "open-waiting", NO_VIEWER_TEXT
        if "drop_query" in self.broken:
            self.dropped += 1
            return
        self._ev("bc", kind="query", viewer=None)
        self._announce()

    def close_deck_tab(self) -> None:
        self._log("close_deck_tab")
        self.tab_closed += 1
        if self.state != "closed" and self.home == "split":
            self._close()

    def drag_splitter_to(self, width: float) -> float | None:
        self._log("drag_splitter_to", width)
        if "no_handle" in self.broken or self.state == "closed" or self.home != "split":
            return None
        if self.tier == "medium" and "lost_clamp" not in self.broken:
            width = min(480.0, max(420.0, width))
        self.drag_w = width
        return width

    def collapse_left(self) -> bool:
        self._log("collapse_left")
        self.left_open = False
        return True

    def reload_frame(self) -> bool:
        self._log("reload_frame")
        if len(self.frames) != 1:
            return False
        self.loads_n += 1
        self._ev("iframe_src", src_viewer=self.frames[0]["src_viewer"])
        self._ev("iframe_load", src_viewer=self.frames[0]["src_viewer"])
        return True

    def loads(self) -> int:
        return self.loads_n

    def mark(self, name: str) -> int:
        self._log("mark", name)
        return self._ev("mark", name=name)

    def events_since(self, seq: int) -> list[dict[str, Any]]:
        return [e for e in self.events if e["seq"] >= seq]

    def embed_hidden(self) -> dict[str, Any]:
        return {sel: "none" for sel in ROOT_SELECTORS}

    def canvas_measure(self) -> dict[str, Any]:
        if "no_resources" in self.broken:
            return {"diff_pixels": 0, "total_pixels": 360000, "control_blank": 0.0, "control_marked": 0.05}
        return {"diff_pixels": 54000, "total_pixels": 360000, "control_blank": 0.0, "control_marked": 0.05}

    def stamp_resources(self, index: int) -> list[Any]:
        return list(self.stamps.get(self.ids[index], []))

    def notice_text(self, index: int, res: str) -> str | None:
        return "Changed since, see deck panel." if self.source_changed and self.ids[index] == "draw-source" else None

    def stock_split(self) -> dict[str, Any]:
        self._log("stock_split")
        return {"panel": 785.0, "notebook": 786.0, "main": 1571.0, "padding": 0.0}

    def neg_dropped(self) -> int:
        return self.dropped


ROOT_SELECTORS = (".navbar", "#toolbar-left", "#stats-panel", "#sidepanel", "#toolbar")
NO_VIEWER_TEXT = "No deck viewer is running. Run `viewer = await praxis.viz.viewer3d.dock(deck)` in a cell."


@pytest.fixture()
def dnbf(rs, nb):
    return rs.build_dock_notebook(nb)


def _calls(d: FakeDock, name: str) -> list[tuple[Any, ...]]:
    return [c for c in d.calls if c[0] == name]


def _evaluate(rs, unit_id, result):
    return rs.evaluate_unit_result(rs.UNIT_BY_ID[unit_id], dict(result, pageerrors=[]))


def test_k1a_scenario_positive_control_every_listed_key_holds(rs, nb, dnbf):
    d = FakeDock(rs, dnbf)
    keys = rs.run_k1a(d, nb)
    assert _evaluate(rs, "K1a", keys) == ([], []), {k: keys.get(k) for k in K1A_DERIVED}
    assert keys["evidence"]["hello"]["backend"] == "WebGL2"
    assert d.calls[:4] == [("open_lab",), ("set_theme", "JupyterLab Light"), ("seed_and_open", "dock_check.ipynb"),
                           ("wait_kernel_idle",)], "AC-34: Light theme, boots and draws and runs dock() itself"


def test_k1a_runs_the_setup_then_the_draws_then_dock_and_reads_the_kernel_not_the_printed_hello(rs, nb, dnbf):
    d = FakeDock(rs, dnbf)
    rs.run_k1a(d, nb)
    runs = [c[1] for c in _calls(d, "run_cell")]
    assert runs[:8] == ["boot", "assemble", "pickup", "draw-source", "draw-assay", "draw-tips", "draw-deck", "dock"]
    assert runs.index("hello") > runs.index("dock") and runs.index("well-name") > runs.index("dock")
    assert runs.index("aspirate") > runs.index("dock"), "AC-37: the aspirate runs AFTER the viewer is live"
    assert runs.index("ledger") < [c[1] for c in d.calls if c[0] == "click_cell_input"].index("draw-tips") + len(runs), "sanity"
    assert ("kernel_text", "hello") in d.calls and ("kernel_text", "well-name") in d.calls


def test_k1a_the_ledger_cell_is_activated_by_a_click_after_it_already_has_its_output(rs, nb, dnbf):
    """`activeCellChanged` fires as the cell is activated. If the ledger were only ever activated by the run that
    produces its output, the output would not exist at that moment and follow_skips_null would pass vacuously."""
    d = FakeDock(rs, dnbf)
    rs.run_k1a(d, nb)
    names = [c[:2] for c in d.calls if c[0] in ("run_cell", "click_cell_input") and c[1] in ("ledger",)]
    assert names[0] == ("run_cell", "ledger") and ("click_cell_input", "ledger") in names
    assert names.index(("click_cell_input", "ledger")) > names.index(("run_cell", "ledger"))
    before_click = [c for c in d.calls[: d.calls.index(("click_cell_input", "ledger"))] if c[0] == "click_cell_input"]
    assert before_click[-1][1] == "draw-tips", "Follow had moved the focus to another resource first"


def test_k1a_follow_off_is_a_real_click_on_the_switch_and_follow_is_turned_back_on(rs, nb, dnbf):
    d = FakeDock(rs, dnbf)
    rs.run_k1a(d, nb)
    assert len(_calls(d, "click_follow")) == 2 and d.follow is True, "off for follow_off_holds, on again for the rest"


def test_k1a_presets_are_pressed_top_front_iso_with_real_clicks(rs, nb, dnbf):
    d = FakeDock(rs, dnbf)
    rs.run_k1a(d, nb)
    assert [c[1] for c in _calls(d, "click_preset")][:3] == ["top", "front", "iso"]
    assert [c[1] for c in _calls(d, "click_preset")][3] == "top", "follow_keeps_preset presses Top again first"


def test_k1a_without_a_scene_the_viewer_resources_key_fails_and_the_scenario_still_finishes(rs, nb, dnbf):
    """AC-39(b): socket.js removed -> the page never gets a scene. The unit must NAME `viewer_resources`, not
    raise (an error finding names no key and could never pass the negative's outcome)."""
    d = FakeDock(rs, dnbf, broken=("no_resources",))
    keys = rs.run_k1a(d, nb)
    missing, failing = _evaluate(rs, "K1a", keys)
    assert missing == [] and "viewer_resources" in failing, failing
    assert "canvas_nonblank" in failing and "hello_backend" in failing


def test_k1a_a_step_that_raises_is_recorded_and_the_other_keys_are_still_produced(rs, nb, dnbf):
    d = FakeDock(rs, dnbf)
    d.embed_hidden = lambda: (_ for _ in ()).throw(rs.DockCheckError("no iframe document"))
    keys = rs.run_k1a(d, nb)
    missing, failing = _evaluate(rs, "K1a", keys)
    assert missing == [] and failing == ["embed_hidden"]
    assert "DockCheckError" in keys["evidence"]["step_errors"]["embed_hidden"]


def test_k1b_scenario_positive_control_every_key_holds_in_the_listed_order(rs, nb, dnbf):
    d = FakeDock(rs, dnbf)
    keys = rs.run_k1b(d, nb)
    assert _evaluate(rs, "K1b", keys) == ([], []), {k: keys.get(k) for k in K1B_KEYS}
    marks = [c[1] for c in _calls(d, "mark") if c[1].startswith("key:")]
    assert marks == ["key:" + k for k in K1B_KEYS], "AC-38 execution order"
    assert keys["evidence"]["recoveries"] == [], "nothing needed recovering"


def test_k1b_action_sequence_follows_the_ac38_execution_order(rs, nb, dnbf):
    d = FakeDock(rs, dnbf)
    rs.run_k1b(d, nb)
    acts = [c for c in d.calls if c[0] in ("run_cell", "reload_frame", "set_viewport", "click_preset", "close_deck_tab",
                                           "toggle_panel", "restart_kernel")]
    flat = [c[1] if c[0] == "run_cell" else c[0] + (":" + str(c[1]) if len(c) > 1 else "") for c in acts]
    setup = ["boot", "assemble", "pickup", "draw-source", "draw-assay", "draw-tips", "draw-deck", "dock", "viewer-id"]
    assert flat[:9] == setup, "the first viewer's id is read once, right after the first dock()"
    tail = flat[9:]
    # reconnect_after_reload: a reload; preset_survives_reload: Front then a reload; drawer_reconnect: 1152 then back to 1440
    assert tail[:4] == ["reload_frame", "click_preset:front", "reload_frame", "set_viewport:1152"]
    assert tail[4] == "set_viewport:1440"
    # redock_live re-runs dock with a LIVE viewer; then the viewer id; stop_placeholder stops; redock_reloads re-docks
    rest = tail[5:]
    assert rest[:2] == ["dock", "viewer-id"]
    assert "stop" in rest and rest.index("stop") > rest.index("dock")
    after_stop = rest[rest.index("stop") + 1:]
    assert after_stop[0] == "dock", "stop_placeholder runs immediately before redock_reloads' dock"
    # late_iframe: tab closed, dock re-run while closed, reopened with the toggle AFTER dock returned
    i_tab = after_stop.index("close_deck_tab")
    assert after_stop[i_tab + 1] == "dock" and after_stop[i_tab + 2] == "toggle_panel"
    # many_reloads: six reloads; restart_placeholder last
    assert after_stop.count("reload_frame") == 6
    assert after_stop[-1] == "restart_kernel" and flat.count("restart_kernel") == 1


def test_k1b_reads_every_iframe_through_the_panel_dom_at_the_moment_of_the_read(rs, nb, dnbf):
    """AC-38 DOM reads: the scenario holds no element between steps; every iframe fact comes from `facts()`."""
    import inspect
    src = inspect.getsource(rs.run_k1b)
    assert "frames" in src and "facts()" in src
    for forbidden in ("query_selector", "locator(", "element_handle", "ElementHandle"):
        assert forbidden not in src, forbidden


def test_k1b_drop_query_negative_fails_late_iframe_and_names_it_with_the_mutation_proven_to_have_fired(rs, nb, dnbf):
    """AC-39(e): with every `query` dropped, reopening gets no announce. late_iframe must fail, and the harness
    records how many queries were actually dropped (a mutation that never fired proves nothing)."""
    d = FakeDock(rs, dnbf, broken=("drop_query",))
    keys = rs.run_k1b(d, nb, neg=("drop-query",))
    missing, failing = _evaluate(rs, "K1b", keys)
    assert missing == [] and failing == ["late_iframe"], failing
    assert keys["neg_dropped_queries"] >= 1
    assert keys["evidence"]["recoveries"] == ["late_iframe"], "later keys still ran, after a recorded re-dock"


def test_k1b_without_the_neg_flag_no_dropped_queries_are_reported(rs, nb, dnbf):
    keys = rs.run_k1b(FakeDock(rs, dnbf), nb)
    assert keys["neg_dropped_queries"] == 0


def test_k1b_a_reload_that_never_repopulates_fails_its_keys_and_does_not_abort(rs, nb, dnbf):
    d = FakeDock(rs, dnbf)
    d.wait_resources = lambda timeout_s=10.0: False
    keys = rs.run_k1b(d, nb)
    missing, failing = _evaluate(rs, "K1b", keys)
    assert missing == [] and {"reconnect_after_reload", "preset_survives_reload", "many_reloads"} <= set(failing)


# -- K2 ---------------------------------------------------------------------------------------------------------


def test_k2_scenario_positive_control_under_the_recorded_case_every_key_holds(rs, nb, dnbf):
    d = FakeDock(rs, dnbf, start=(1152, 800))
    keys = rs.run_k2(d, nb)
    assert _evaluate(rs, "K2", keys) == ([], []), {k: keys.get(k) for k in K2_ALL_KEYS}
    assert keys["sizing_case"] == "honoured_reachable" and set(keys["width_key_status"].values()) == {"asserted"}


def test_k2_uses_one_page_one_kernel_and_one_dock_and_the_nine_ordered_steps(rs, nb, dnbf):
    d = FakeDock(rs, dnbf, start=(1152, 800))
    rs.run_k2(d, nb)
    assert len(_calls(d, "open_lab")) == 1 and len(_calls(d, "seed_and_open")) == 1, "one page"
    assert len(_calls(d, "restart_kernel")) == 0
    assert [c[1] for c in _calls(d, "run_cell")].count("dock") == 1, "one kernel, one dock()"
    sizes = [(c[1], c[2]) for c in _calls(d, "set_viewport")]
    assert sizes == [
        (1440, 900), (1152, 800), (1440, 900),  # step 3: tier_up_rehomes
        (1600, 900), (1440, 900),  # step 5: fit_after_tier_change 1440 -> 1600 -> 1440
        (1280, 800),  # step 6
        (1600, 900),  # step 7
        (1920, 900),  # step 8: resize_within_wide
        (1920, 1080),  # step 9
    ]
    assert len(_calls(d, "collapse_left")) == 1
    order = [c[0] for c in d.calls]
    assert order.index("collapse_left") > max(i for i, c in enumerate(d.calls) if c == ("set_viewport", 1280, 800)), "step 7"
    assert order.index("collapse_left") < order.index("set_viewport", order.index("collapse_left")), "closed before 1600"


def test_k2_reopens_are_through_the_toggle_command_never_a_second_dock(rs, nb, dnbf):
    d = FakeDock(rs, dnbf, start=(1152, 800))
    rs.run_k2(d, nb)
    assert len(_calls(d, "toggle_panel")) >= 8
    assert len(_calls(d, "click_drawer_close")) == 2 and len(_calls(d, "press_escape")) == 1


def test_k2_splitter_drags_go_to_300_and_700_at_1440_and_1280_only(rs, nb, dnbf):
    d = FakeDock(rs, dnbf, start=(1152, 800))
    rs.run_k2(d, nb)
    assert [c[1] for c in _calls(d, "drag_splitter_to")] == [300, 700, 300, 700]


def test_k2_counts_iframe_loads_over_the_drags_and_the_wide_resize_only(rs, nb, dnbf):
    d = FakeDock(rs, dnbf, start=(1152, 800), broken=("reload_on_resize",))
    keys = rs.run_k2(d, nb)
    _, failing = _evaluate(rs, "K2", keys)
    assert failing == ["iframe_reloads_during_resize"], failing
    assert keys["evidence"]["reloads"]["resize_within_wide"] >= 1


def test_k2_a_splitter_that_cannot_be_found_fails_the_drag_keys_and_nothing_else(rs, nb, dnbf):
    d = FakeDock(rs, dnbf, start=(1152, 800), broken=("no_handle",))
    keys = rs.run_k2(d, nb)
    _, failing = _evaluate(rs, "K2", keys)
    assert set(failing) == {"drag_clamp_low_1440", "drag_clamp_high_1440", "drag_clamp_low_1280", "drag_clamp_high_1280"}


def test_k2_an_unclamped_drag_fails_the_clamp_keys(rs, nb, dnbf):
    d = FakeDock(rs, dnbf, start=(1152, 800), broken=("lost_clamp",))
    _, failing = _evaluate(rs, "K2", rs.run_k2(d, nb))
    assert set(failing) == {"drag_clamp_low_1440", "drag_clamp_high_1440", "drag_clamp_low_1280", "drag_clamp_high_1280"}


def test_k2_a_failing_step_is_recorded_and_the_later_steps_still_run(rs, nb, dnbf):
    d = FakeDock(rs, dnbf, start=(1152, 800))
    real = d.drag_splitter_to

    def boom(width):
        if width == 300 and d.w == 1440:
            raise rs.DockCheckError("mouse lost")
        return real(width)

    d.drag_splitter_to = boom
    keys = rs.run_k2(d, nb)
    missing, failing = _evaluate(rs, "K2", keys)
    assert missing == [] and "drag_clamp_low_1440" in failing and "panel_width_wide_1920" not in failing
    assert "mouse lost" in " ".join(keys["evidence"]["step_errors"].values())


def test_k2_recorded_only_keys_do_not_gate_under_another_case_but_are_still_reported(rs, nb, dnbf, monkeypatch):
    record = {"css_limits_honoured": True, "layout_sizing_reachable": False, "css_limits_refit": False,
              "restore_layout_keeps_iframe": True}
    d = FakeDock(rs, dnbf, start=(1152, 800))
    keys = rs.run_k2(d, nb, record=record)
    assert keys["sizing_case"] == "honoured_unreachable" and keys["width_key_status"]["panel_width_wide_1600"] == "recorded-only"
    unit = dataclasses.replace(rs.UNIT_BY_ID["K2"], expected=rs.k2_expected(rs.width_key_status(**record)))
    assert rs.evaluate_unit_result(unit, dict(keys, pageerrors=[])) == ([], [])


# -- N-d ---------------------------------------------------------------------------------------------------------


def test_n_d_scenario_the_stock_split_makes_the_wide_key_fail_and_it_is_the_only_failing_key(rs, nb, dnbf):
    d = FakeDock(rs, dnbf, start=(1600, 900))
    keys = rs.run_nd(d, nb)
    assert _evaluate(rs, "N-d", keys) == ([], ["panel_width_wide_1600"])
    assert [c[0] for c in d.calls][:3] == ["open_lab", "seed_and_open", "stock_split"], "no kernel, no dock(), no dock.js sizing"
    assert ("run_cell", "dock") not in d.calls


def test_n_d_scenario_is_skipped_without_touching_the_browser_where_the_key_is_recorded_only(rs, nb, dnbf):
    record = {"css_limits_honoured": False, "layout_sizing_reachable": False, "css_limits_refit": False,
              "restore_layout_keeps_iframe": True}
    d = FakeDock(rs, dnbf, start=(1600, 900))
    keys = rs.run_nd(d, nb, record=record)
    assert keys["skipped"] is True and _calls(d, "stock_split") == [] and _calls(d, "open_lab") == []


def test_n_d_scenario_an_untrustworthy_measurement_raises_so_the_unit_records_an_error(rs, nb, dnbf):
    d = FakeDock(rs, dnbf, start=(1600, 900))
    d.stock_split = lambda: {"panel": None, "notebook": 786.0, "main": 1571.0, "padding": 0.0}
    with pytest.raises(rs.DockCheckError):
        rs.run_nd(d, nb)


# -- dispatch and the session ------------------------------------------------------------------------------------


def test_run_dock_scenario_dispatches_each_unit_to_its_own_body(rs, monkeypatch, nb):
    calls: list[tuple[str, Any]] = []

    class Drv:
        def __init__(self, session: Any, *a: Any, **k: Any) -> None:
            calls.append(("driver", session))

    monkeypatch.setattr(rs, "DockDriver", Drv)
    for name in ("run_k1a", "run_k1b", "run_k2", "run_nd"):
        monkeypatch.setattr(rs, name, lambda d, f, _n=name, **kw: calls.append((_n, kw)) or {"body": _n})
    session = FakeSession()
    for uid, body in (("K1a", "run_k1a"), ("K1b", "run_k1b"), ("K2", "run_k2"), ("N-d", "run_nd")):
        assert rs.run_dock_scenario(session, rs.UNIT_BY_ID[uid], make_env(rs), notebook=nb) == {"body": body}
    assert [c[0] for c in calls if c[0] != "driver"] == ["run_k1a", "run_k1b", "run_k2", "run_nd"]


def test_run_dock_scenario_passes_the_neg_flags_to_k1b_only(rs, monkeypatch, nb):
    seen: list[Any] = []
    monkeypatch.setattr(rs, "DockDriver", lambda session, **k: object())
    monkeypatch.setattr(rs, "run_k1b", lambda d, f, neg=(): seen.append(neg) or {})
    session = FakeSession()
    session._neg = ("drop-query",)
    rs.run_dock_scenario(session, rs.UNIT_BY_ID["K1b"], make_env(rs), notebook=nb)
    assert seen == [("drop-query",)]


def test_run_dock_scenario_refuses_a_unit_it_has_no_body_for(rs):
    with pytest.raises(rs.DockCheckError):
        rs.run_dock_scenario(FakeSession(), rs.HarnessUnit("Kx", rs.DOCK_CHECK, 1.0, ()), make_env(rs))


@pytest.mark.parametrize(
    "path,full",
    [
        ("/home/u/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome", True),
        ("/home/u/.cache/ms-playwright/chromium-1228/chrome-linux/chrome", True),
        ("/home/u/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell", False),
        ("/x/chromium_headless_shell-1234/chrome-linux/headless_shell", False),
        ("/x/headless_shell", False),
        ("", False),
    ],
)
def test_is_full_chromium_rejects_the_headless_shell_which_has_no_webgl2(rs, path, full):
    assert rs.is_full_chromium(path) is full


def test_dock_launch_args_add_swiftshader_to_the_base_args(rs):
    args = rs.dock_launch_args()
    assert args[: len(rs.BASE_CHROMIUM_ARGS)] == rs.BASE_CHROMIUM_ARGS
    assert args[len(rs.BASE_CHROMIUM_ARGS):] == ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"]


def test_dock_context_init_scripts_always_carry_the_ack_and_the_monitor_and_drop_query_only_on_request(rs):
    base = rs.dock_context_init_scripts(())
    assert rs.PERSISTENCE_ACK_INIT_SCRIPT in base and rs.PERSISTENCE_GATE_MONITOR_INIT_SCRIPT in base
    assert rs.DOCK_MONITOR_INIT_SCRIPT in base and rs.DROP_QUERY_INIT_SCRIPT not in base
    neg = rs.dock_context_init_scripts(("drop-query",))
    assert rs.DROP_QUERY_INIT_SCRIPT in neg and neg[: len(base)] == base


def _fake_playwright(monkeypatch, launched, contexts):
    import types

    class Page:
        def __init__(self):
            self.handlers = {}

        def on(self, name, fn):
            self.handlers[name] = fn

    class Context:
        def __init__(self, kw):
            self.kw, self.scripts, self.page = kw, [], Page()

        def add_init_script(self, script):
            self.scripts.append(script)

        def new_page(self):
            return self.page

    class Browser:
        def new_context(self, **kw):
            ctx = Context(kw)
            contexts.append(ctx)
            return ctx

        def close(self):
            launched.append("close")

    class Chromium:
        def launch(self, **kw):
            launched.append(kw)
            return Browser()

    class PW:
        chromium = Chromium()

        def stop(self):
            launched.append("stop")

    class Starter:
        def start(self):
            return PW()

    mod = types.ModuleType("playwright.sync_api")
    mod.sync_playwright = lambda: Starter()
    mod.TimeoutError = TimeoutError
    pkg = types.ModuleType("playwright")
    pkg.sync_api = mod
    monkeypatch.setitem(sys.modules, "playwright", pkg)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", mod)


def test_dock_session_launches_full_chromium_with_swiftshader_and_the_dock_init_scripts(rs, monkeypatch, tmp_path):
    launched: list[Any] = []
    contexts: list[Any] = []
    _fake_playwright(monkeypatch, launched, contexts)
    serve = tmp_path / "dist"
    serve.mkdir()
    args = rs.parse_args(["--dock-check", "--serve-dir", str(serve), "--out-dir", str(tmp_path / "o"), "--neg", "drop-query",
                          "--scenario", "K1b"])
    env = make_env(rs, chrome_path="/pw/chromium-1243/chrome-linux64/chrome")
    session = rs.DockSession(rs.UNIT_BY_ID["K1b"], args, env)
    try:
        kw = launched[0]
        assert kw["executable_path"] == "/pw/chromium-1243/chrome-linux64/chrome"
        assert kw["args"] == rs.dock_launch_args() and "--use-angle=swiftshader" in kw["args"]
        assert contexts[0].kw == {"viewport": {"width": 1440, "height": 900}}
        assert contexts[0].scripts == rs.dock_context_init_scripts(("drop-query",))
        assert "pageerror" in contexts[0].page.handlers
        assert session.lab_url.endswith("/praxis/lab/index.html") or session.lab_url.endswith("/lab/index.html")
    finally:
        session.close()
    assert launched[-2:] == ["close", "stop"]


def test_dock_session_k2_starts_at_the_first_k2_viewport(rs, monkeypatch, tmp_path):
    launched: list[Any] = []
    contexts: list[Any] = []
    _fake_playwright(monkeypatch, launched, contexts)
    serve = tmp_path / "dist"
    serve.mkdir()
    args = rs.parse_args(["--dock-check", "--serve-dir", str(serve), "--out-dir", str(tmp_path / "o")])
    session = rs.DockSession(rs.UNIT_BY_ID["K2"], args, make_env(rs, chrome_path="/pw/chromium-1243/chrome-linux64/chrome"))
    try:
        assert contexts[0].kw == {"viewport": {"width": 1152, "height": 800}}
    finally:
        session.close()


def test_dock_session_refuses_the_headless_shell_before_it_launches_anything(rs, monkeypatch, tmp_path):
    launched: list[Any] = []
    _fake_playwright(monkeypatch, launched, [])
    args = rs.parse_args(["--dock-check", "--out-dir", str(tmp_path / "o")])
    env = make_env(rs, chrome_path="/pw/chromium_headless_shell-1234/chrome-linux/headless_shell")
    with pytest.raises(rs.DockCheckError):
        rs.DockSession(rs.UNIT_BY_ID["K1a"], args, env)
    assert launched == []


def test_display_session_still_uses_the_stock_launch_args_and_scripts(rs, monkeypatch, tmp_path):
    launched: list[Any] = []
    contexts: list[Any] = []
    _fake_playwright(monkeypatch, launched, contexts)
    serve = tmp_path / "dist"
    serve.mkdir()
    args = rs.parse_args(["--display-check", "--serve-dir", str(serve), "--out-dir", str(tmp_path / "o")])
    session = rs.DisplaySession(rs.UNIT_BY_ID["D1"], args, make_env(rs, chrome_path="/pw/chromium-1243/chrome-linux64/chrome"))
    try:
        assert launched[0]["args"] == rs.chromium_launch_args(offline=False)
        assert contexts[0].scripts == rs.display_context_init_scripts(())
    finally:
        session.close()


# -- the in-page helpers ---------------------------------------------------------------------------------------------


def _js_names(source: str, prefix: str) -> set[str]:
    return set(re.findall(prefix + r"\.(\w+)\s*=", source))


def test_every_page_helper_the_driver_calls_is_defined_in_the_dock_check_js(rs):
    import inspect
    src = inspect.getsource(rs.DockDriver)
    called = set(re.findall(r'_dk\(\s*self\.page,\s*"(\w+)\(', src)) | set(re.findall(r'self\._dk\(\s*"(\w+)\(', src))
    defined = _js_names(rs.DOCK_CHECK_JS, "D")
    assert called, "the driver does call page helpers"
    assert called <= defined, sorted(called - defined)


def test_the_dock_check_js_defines_no_helper_the_driver_never_calls(rs):
    import inspect
    src = inspect.getsource(rs.DockDriver)
    called = set(re.findall(r'_dk\(\s*self\.page,\s*"(\w+)\(', src)) | set(re.findall(r'self\._dk\(\s*"(\w+)\(', src))
    assert _js_names(rs.DOCK_CHECK_JS, "D") <= called, sorted(_js_names(rs.DOCK_CHECK_JS, "D") - called)


def test_harness_page_code_has_no_test_switch_no_serial_prompt_and_no_repl_channel(rs):
    for name in ("DOCK_CHECK_JS", "DOCK_MONITOR_INIT_SCRIPT", "DROP_QUERY_INIT_SCRIPT"):
        text = getattr(rs, name)
        for token in ("__praxis" + "_test", "data-praxis" + "-test", "requestDevice", "requestPort", "praxis_repl"):
            assert token not in text, (name, token)


def test_the_dock_check_js_reads_the_real_selectors_the_product_defines(rs):
    """Every product selector the helpers use is one dock.js (or the vendored page) really defines."""
    dock = (rs.REPO_ROOT / "web-repl/shell/display/dock.js").read_text()
    for token in ("praxis-deck-panel", "praxis-deck-panel__body", "praxis-deck-panel__footer", "praxis-deck-panel__follow",
                  "praxis-deck-panel__views", "praxis-deck-panel__motion", "praxis-deck-panel__close", "praxis-deck-panel__frame",
                  "data-praxis-deck-state", "data-praxis-deck-focus", "aria-checked", "aria-pressed", "praxis:toggle-deck-panel"):
        assert token in dock, token
        assert token in rs.DOCK_CHECK_JS or token in rs.DOCK_MONITOR_INIT_SCRIPT or token in _dock_driver_source(rs), token
    assert 'w.title.label = "Deck"' in dock, "the tab label the close-icon lookup matches"
    assert "__praxisDisplay" in (rs.REPO_ROOT / "web-repl/shell/display/index.js").read_text()
    assert "window.__praxisDisplay" in rs.DOCK_CHECK_JS


def _dock_driver_source(rs) -> str:
    import inspect
    return inspect.getsource(rs.DockDriver) + inspect.getsource(rs.run_k1a) + inspect.getsource(rs.run_k1b)


_BUN = shutil.which("bun") or str(Path.home() / ".bun" / "bin" / "bun")
needs_bun = pytest.mark.skipif(not Path(_BUN).exists(), reason="bun not installed: the in-page code is exercised locally only")


@needs_bun
@pytest.mark.parametrize("name", ["DOCK_CHECK_JS", "DOCK_MONITOR_INIT_SCRIPT", "DROP_QUERY_INIT_SCRIPT"])
def test_in_page_code_parses_as_javascript(rs, tmp_path, name):
    text = getattr(rs, name)
    script = tmp_path / "p.js"
    script.write_text(f"const src = {json.dumps(text)};\ntry {{ new Function(src); }} catch (e) {{\n"
                      f"  try {{ new Function('return (' + src + ')'); }} catch (e2) {{ console.error(String(e2)); process.exit(3); }}\n}}\n")
    done = subprocess.run([_BUN, str(script)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr


_JS_PRELUDE = r"""
const posted = [];
class FakeMO { constructor(cb) { globalThis.__mo = cb; } observe() {} }
globalThis.MutationObserver = FakeMO;
globalThis.window = globalThis; window.top = window;
globalThis.document = { addEventListener() {}, querySelectorAll() { return []; } };
globalThis.location = { href: "http://x/lab/index.html" };
"""


@needs_bun
def test_monitor_init_script_logs_bc_messages_in_one_ordered_sequence(rs, tmp_path):
    js = _JS_PRELUDE + f"""
{rs.DOCK_MONITOR_INIT_SCRIPT}
const other = new BroadcastChannel("praxis_viz3d");
other.postMessage(JSON.stringify({{kind: "announce", viewer: "v-1", deck: "d"}}));
other.postMessage("not json");
other.postMessage(JSON.stringify({{kind: "query"}}));
await new Promise((r) => setTimeout(r, 200));
const log = window.__praxisDockLog;
process.stdout.write(JSON.stringify(log.events.map((e) => [e.seq, e.type, e.kind, e.viewer])) + "\\n");
log.push({{type: "mark", name: "m"}});
process.stdout.write(log.events.at(-1).seq + " " + log.loads + "\\n");
window.__praxisDockChannel.close(); other.close();
"""
    script = tmp_path / "m.mjs"
    script.write_text(js)
    done = subprocess.run([_BUN, str(script)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    first, second = done.stdout.strip().splitlines()[-2:]
    assert json.loads(first) == [[1, "bc", "announce", "v-1"], [2, "bc", "query", None]], "junk is not an event; seq is 1, 2, ..."
    assert second.split() == ["3", "0"]


@needs_bun
def test_drop_query_init_script_drops_query_only_and_counts_what_it_dropped(rs, tmp_path):
    js = _JS_PRELUDE + f"""
{rs.DROP_QUERY_INIT_SCRIPT}
const a = new BroadcastChannel("t1"), b = new BroadcastChannel("t1");
const got = []; b.onmessage = (e) => got.push(e.data);
a.postMessage(JSON.stringify({{kind: "query"}}));
a.postMessage(JSON.stringify({{kind: "announce", viewer: "v"}}));
a.postMessage("plain string");
a.postMessage({{kind: "query"}});
await new Promise((r) => setTimeout(r, 200));
process.stdout.write(JSON.stringify(got) + " " + window.__praxisDropQuery.dropped + "\\n");
a.close(); b.close();
"""
    script = tmp_path / "d.mjs"
    script.write_text(js)
    done = subprocess.run([_BUN, str(script)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    got, dropped = done.stdout.strip().splitlines()[-1].rsplit(" ", 1)
    assert json.loads(got) == [json.dumps({"kind": "announce", "viewer": "v"}, separators=(",", ":")), "plain string"]
    assert dropped == "2", "both the JSON-string query and the object query were dropped"


@needs_bun
def test_init_scripts_do_nothing_in_a_child_frame(rs, tmp_path):
    js = _JS_PRELUDE.replace("window.top = window;", "window.top = {};") + f"""
{rs.DOCK_MONITOR_INIT_SCRIPT}
{rs.DROP_QUERY_INIT_SCRIPT}
process.stdout.write(String(window.__praxisDockLog) + " " + String(window.__praxisDropQuery) + "\\n");
"""
    script = tmp_path / "f.mjs"
    script.write_text(js)
    done = subprocess.run([_BUN, str(script)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().splitlines()[-1] == "undefined undefined", "AC-39(e): the PARENT page only"


# -- the CLI ------------------------------------------------------------------------------------------------------


def test_dock_check_flag_exists_and_main_routes_to_run_dock_check(rs, monkeypatch):
    args = rs.parse_args(["--dock-check"])
    assert args.dock_check is True and args.display_check is False
    calls: list[Any] = []
    monkeypatch.setattr(rs, "run_dock_check", lambda a, **kw: calls.append(a) or 9)
    assert rs.main(["--dock-check"]) == 9 and len(calls) == 1
    assert rs.main([]) == 2


@pytest.mark.parametrize(
    "argv",
    [["--serve-dir", "{tmp}"], ["--neg", "drop-query", "--scenario", "K1b"], ["--serve-dir", "{tmp}", "--scenario", "K1a"]],
)
def test_run_dock_check_exits_2_before_launching_anything_without_out_dir(rs, tmp_path, argv):
    spy = SpyRunner()
    args = rs.parse_args(["--dock-check", *[a.format(tmp=tmp_path) for a in argv]])
    assert rs.run_dock_check(args, runner=spy, hash_env=make_env(rs)) == 2
    assert spy.calls == []


def test_run_dock_check_conflicting_flags_and_unknown_scenarios_exit_2(rs, tmp_path):
    out = ["--out-dir", str(tmp_path / "o")]
    for extra in (["--aggregate-only", "--fresh"], ["--aggregate-only", "--scenario", "K1a"], ["--scenario", "D1"],
                  ["--scenario", "K9"]):
        args = rs.parse_args(["--dock-check", *out, *extra])
        assert rs.run_dock_check(args, runner=SpyRunner(), hash_env=make_env(rs)) == 2, extra


def test_the_drop_query_negative_belongs_to_k1b_alone(rs, tmp_path):
    """AC-39(e): `--dock-check --scenario K1b --neg drop-query`. Any other unit, and the driver, refuse it."""
    out = ["--out-dir", str(tmp_path / "o"), "--neg", "drop-query"]
    for extra in (["--scenario", "K1a"], ["--scenario", "K2"], ["--scenario", "N-d"], []):
        args = rs.parse_args(["--dock-check", *out, *extra])
        assert rs.run_dock_check(args, runner=SpyRunner(), hash_env=make_env(rs)) == 2, extra
    seen: list[Any] = []
    args = rs.parse_args(["--dock-check", *out, "--scenario", "K1b"])
    rc = rs.run_dock_check(args, runner=SpyRunner(), hash_env=make_env(rs),
                           scenario_entry=lambda uid, **kw: seen.append((uid, kw["neg"])) or 0)
    assert rc == 0 and seen == [("K1b", ("drop-query",))]


@pytest.mark.parametrize("uid", DOCK_IDS)
def test_scenario_flag_runs_exactly_that_dock_unit_including_n_d(rs, tmp_path, uid):
    seen: list[Any] = []
    args = rs.parse_args(["--dock-check", "--scenario", uid, "--out-dir", str(tmp_path / "o")])
    rc = rs.run_dock_check(args, runner=SpyRunner(), hash_env=make_env(rs),
                           scenario_entry=lambda unit_id, **kw: seen.append((unit_id, kw["out_dir"], kw["scenario_fn"])) or 0)
    assert rc == 0 and [s[0] for s in seen] == [uid]
    assert seen[0][1] == (tmp_path / "o").resolve() and seen[0][2] is rs.run_dock_scenario


def test_the_default_dock_out_dir_is_gitignored_outputs(rs):
    assert rs.default_out_dir(rs.DOCK_CHECK) == rs.REPO_ROOT / "outputs" / "repl_smoke" / "dock-check"


def drive_dock(rs, out_dir, env, runner, **kw):
    return rs.run_units_driver(
        table=list(rs.DOCK_AGGREGATE_UNITS), out_dir=out_dir, inputs_for=lambda u: rs.unit_inputs(u, env),
        argv_for=lambda u: ["fake-unit", "--scenario", u.id], runner=runner, cwd="/repo", check=rs.DOCK_CHECK, **kw,
    )


def test_the_dock_driver_runs_k1a_k1b_k2_as_one_run_unit_each_and_never_n_d(rs, ur, wds, tmp_path):
    env = make_env(rs)
    out = tmp_path / "out"
    runner = InProcessRunner(rs, ur, wds, out, env)
    args = rs.parse_args(["--dock-check", "--out-dir", str(out), "--base-path", "/praxis/", "--serve-dir", str(tmp_path)])
    assert rs.run_dock_check(args, runner=runner, hash_env=env, unit_argv_prefix=["py", "smoke.py"]) == 0
    assert runner.ids() == ["K1a", "K1b", "K2"], "table order; N-d is never part of the aggregate"
    assert [t for _, t, _ in runner.calls] == [m * 60 + 60 for m in (10, 14, 15)], "budget + 60 s each, no whole-run timeout"
    for argv, _, _ in runner.calls:
        assert argv[:2] == ["py", "smoke.py"] and "--dock-check" in argv and "--display-check" not in argv
        assert argv[argv.index("--base-path") + 1] == "/praxis/" and argv[argv.index("--out-dir") + 1] == str(out)
        assert argv[argv.index("--serve-dir") + 1] == str(tmp_path) and "--chrome-path" in argv
    agg = json.loads((out / "result.json").read_text())
    assert agg["check"] == "dock-check" and set(agg["scenarios"]) == {"K1a", "K1b", "K2"} and agg["passed"] is True
    assert "N-d" not in agg["scenarios"] and agg["sizing_case"] == "honoured_reachable"


def test_the_dock_aggregate_fails_while_any_unit_is_missing_and_n_d_never_rescues_or_fails_it(rs, ur, wds, tmp_path):
    env = make_env(rs)
    out = tmp_path / "out"
    runner = InProcessRunner(rs, ur, wds, out, env, skip_stamp={"K1b"})
    agg, code = drive_dock(rs, out, env, runner)
    assert code == 1 and agg["missing"] == ["K1b"] and agg["recomputed"] == ["K1a", "K2"]
    # an N-d result on disk (it fails its own listed key BY DESIGN) does not touch the verdict
    scenario_in_process(rs, ur, wds, "N-d", out, env, fields={"panel_width_wide_1600": False})
    agg2, code2 = drive_dock(rs, out, env, InProcessRunner(rs, ur, wds, out, env), )
    assert code2 == 0 and agg2["passed"] is True and "N-d" not in agg2["scenarios"]


def test_the_dock_aggregate_only_path_starts_no_unit_and_deletes_nothing(rs, ur, wds, tmp_path):
    env = make_env(rs)
    out = tmp_path / "out"
    drive_dock(rs, out, env, InProcessRunner(rs, ur, wds, out, env))
    before = snapshot_files(out)
    spy = SpyRunner()
    args = rs.parse_args(["--dock-check", "--aggregate-only", "--out-dir", str(out), "--base-path", "/praxis/"])
    assert rs.run_dock_check(args, runner=spy, hash_env=env) == 0 and spy.calls == []
    stale = rs.parse_args(["--dock-check", "--aggregate-only", "--out-dir", str(out), "--base-path", "/other/"])
    assert rs.run_dock_check(stale, runner=spy, hash_env=make_env(rs, base_path="/other/")) == 1
    after = snapshot_files(out)
    assert all(after[k] == v for k, v in before.items() if k != "result.json")


def test_every_dock_unit_arms_its_watchdog_once_with_its_d16_budget_before_any_deletion(rs, ur, tmp_path):
    """The K-unit watchdog is the table's budget (AC-42: armed once, before the first deletion and the browser)."""
    for uid, minutes in zip(DOCK_IDS, DOCK_BUDGET_MIN):
        armed: list[tuple[float, bool]] = []

        class Spy:
            def __init__(self, budget_s, on_expire):
                armed.append((budget_s, (tmp_path / "x").exists()))
                self.wd = ur.Watchdog(budget_s, on_expire, token="t", exit_fn=lambda c: None, kill_fn=lambda *a, **k: [])

            def __getattr__(self, name):
                return getattr(self.wd, name)

        out = tmp_path / uid
        files = rs.unit_paths(out, uid)
        assert rs.run_scenario(
            uid, out_dir=out, env_fn=lambda: make_env(rs), session_factory=lambda u, e: FakeSession(),
            scenario_fn=lambda s, u, e: passing_fields(u), ensure_token_fn=lambda: "t", watchdog_factory=Spy,
            kill_tree_fn=lambda *a, **k: [], exit_fn=lambda c: c,
        ) == 0
        assert armed == [(minutes * 60.0, False)], (uid, armed)
        assert files["stamp"].exists()


# -- the in-page helpers against a minimal fake DOM (bun; the real DOM is only in a browser run) -----------------------


def _run_dock_js(rs, tmp_path, body: str) -> Any:
    """Load DOCK_CHECK_JS into bun with a tiny fake `document`/`window`, run ``body`` (async JS that returns a value) and
    return the JSON it printed."""
    js = f"""
const nodes = {{}};
globalThis.window = globalThis;
window.innerWidth = 1440;
window.__praxisDisplay = {{ controllers: {{ dock: {{ snapshot: () => ({{ state: "closed", home: null }}) }} }} }};
window.jupyterapp = {{ shell: {{ leftCollapsed: false, collapseLeft() {{ this.leftCollapsed = true; }}, currentWidget: null }} }};
globalThis.location = {{ href: "http://x/lab/index.html" }};
globalThis.getComputedStyle = (el) => el.__style || {{ position: "static", display: "block", paddingLeft: "0px", paddingRight: "0px" }};
globalThis.document = {{
  querySelector: (sel) => nodes[sel] || null,
  querySelectorAll: (sel) => nodes[sel + "*"] || [],
  getElementById: (id) => nodes["#" + id] || null,
  contains: (n) => !!n && n.__attached !== false,
}};
const box = (w, h = 10, left = 0) => ({{ left, right: left + w, top: 0, bottom: h, width: w, height: h }});
{rs.DOCK_CHECK_JS}
const D = window.__praxisDockCheck;
const out = await (async () => {{ {body} }})();
process.stdout.write(JSON.stringify(out) + "\\n");
"""
    script = tmp_path / "dock_js.mjs"
    script.write_text(js)
    done = subprocess.run([_BUN, str(script)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


@needs_bun
def test_facts_of_a_closed_panel_reads_closed_from_the_controller_because_the_node_is_not_in_the_document(rs, tmp_path):
    """When the panel is closed its node is detached, so a DOM-only read would give state null and every
    `state == 'closed'` key would fail for the wrong reason."""
    got = _run_dock_js(rs, tmp_path, "return D.facts();")
    assert got["present"] is False and got["state"] == "closed" and got["frames"] == [] and got["text"] == ""
    assert got["left_collapsed"] is False and got["inner_width"] == 1440


@needs_bun
def test_facts_of_an_open_panel_reads_the_dom_the_iframes_and_the_pressed_preset(rs, tmp_path):
    got = _run_dock_js(rs, tmp_path, """
const frame = { getAttribute: (k) => "http://x/assets/visualizer3d/index.html?embed=1&view=top&viewer=v-7",
                getBoundingClientRect: () => box(400, 420) };
const follow = { getAttribute: () => "true" };
const pressed = [{ getAttribute: (k) => "false", textContent: "Iso" }, { getAttribute: (k) => "true", textContent: " Front " }];
const panel = {
  getAttribute: (k) => "open-connected",
  querySelector: (sel) => ({
    ".praxis-deck-panel__body": { textContent: "body text" },
    ".praxis-deck-panel__footer [data-praxis-deck-focus]": { textContent: "source" },
    ".praxis-deck-panel__follow": follow,
    ".praxis-deck-panel__motion": { getBoundingClientRect: () => box(400, 24) },
  }[sel] || null),
  querySelectorAll: (sel) => (sel === "iframe" ? [frame] : sel === ".praxis-deck-panel__views button" ? pressed : []),
  getBoundingClientRect: () => box(450, 600, 990),
  __style: { position: "fixed" },
};
nodes[".praxis-deck-panel"] = panel;
nodes[".jp-NotebookPanel"] = { getBoundingClientRect: () => box(990, 700) };
nodes[".jp-NotebookPanel .jp-Notebook"] = { getBoundingClientRect: () => box(960, 700), __style: { paddingLeft: "4px", paddingRight: "6px" } };
nodes["#jp-main-dock-panel"] = { getBoundingClientRect: () => box(1440, 700) };
return D.facts();
""")
    assert got["state"] == "open-connected" and got["position"] == "fixed" and got["text"] == "body text"
    assert got["frames"] == [{"src": "http://x/assets/visualizer3d/index.html?embed=1&view=top&viewer=v-7",
                              "src_viewer": "v-7", "height": 420}]
    assert got["footer"] == "source" and got["follow_checked"] is True and got["pressed"] == ["front"]
    assert got["panel_rect"]["width"] == 450 and got["notebook_panel_rect"]["right"] == 990
    assert got["nb_content_width"] == 960 and got["nb_h_padding"] == 10 and got["main_width"] == 1440
    assert got["motion_height"] == 24


@needs_bun
def test_the_viewer_reads_go_through_the_iframe_in_the_panel_and_fail_soft_without_one(rs, tmp_path):
    got = _run_dock_js(rs, tmp_path, """
const none = [await D.resources(), await D.camera(), await D.stateOf({ name: "x" })];
const viewer = { resources: () => ["deck", "source"], camera: () => ({ from: [1, 2, 3], at: [0, 0, 0], distance: 3, zoom: 1 }),
                 stateOf: (n) => (n === "source" ? { volume: 190 } : undefined) };
const frame = { getAttribute: () => "x", getBoundingClientRect: () => box(1), contentWindow: { plrViewer: viewer } };
nodes[".praxis-deck-panel"] = { getAttribute: () => "open-connected", querySelector: () => null,
  querySelectorAll: (sel) => (sel === "iframe" ? [frame] : []), getBoundingClientRect: () => box(1) };
return { none, resources: D.resources(), camera: D.camera(), source: D.stateOf({ name: "source" }), nothing: D.stateOf({ name: "nope" }) };
""")
    assert got["none"] == [None, None, None]
    assert got["resources"] == ["deck", "source"] and got["camera"] == {"from": [1, 2, 3], "at": [0, 0, 0]}
    assert got["source"] == '{"volume":190}' and got["nothing"] is None


@needs_bun
def test_canvas_controls_read_a_blank_image_as_zero_and_a_five_percent_marked_one_as_five_percent(rs, tmp_path):
    got = _run_dock_js(rs, tmp_path, "return D.canvasControls({ ground: [238, 241, 244], tol: 6 });")
    assert got["blank"] == {"diff": 0, "total": 10000}
    assert got["marked"]["total"] == 10000 and got["marked"]["diff"] == 500


@needs_bun
def test_cell_helpers_read_the_output_model_text_and_the_stamp_resources(rs, tmp_path):
    got = _run_dock_js(rs, tmp_path, """
const out = (o) => ({ toJSON: () => o });
const cells = [
  { model: { outputs: { length: 2, get: (j) => out([{ output_type: "stream", text: ["hi ", "there"] },
        { output_type: "execute_result", data: { "text/plain": "'v-abc'" } }][j]) } } },
  { model: { outputs: { length: 2, get: (j) => out([
        { output_type: "display_data", data: {}, metadata: { praxis: { resource: null, kind: "ledger" } } },
        { output_type: "display_data", data: {}, metadata: { "text/html": { praxis: { resource: "assay" } } } }][j]) } } },
  { model: { outputs: { length: 1, get: (j) => out({ output_type: "stream", text: "only a stream" }) } } },
];
window.jupyterapp.shell.currentWidget = { content: { widgets: cells } };
return { plain: D.cellText({ i: 0 }), stream: D.cellText({ i: 2 }), stamps: D.stampResources({ i: 1 }), missing: D.cellText({ i: 9 }) };
""")
    assert got == {"plain": "'v-abc'", "stream": "only a stream", "stamps": [None, "assay"], "missing": None}


@needs_bun
def test_marks_and_events_share_one_sequence_and_collapse_left_reports_the_shell_state(rs, tmp_path):
    got = _run_dock_js(rs, tmp_path, """
const log = { seq: 0, events: [], loads: 4, push(e) { this.seq += 1; e.seq = this.seq; this.events.push(e); return e.seq; } };
window.__praxisDockLog = log;
log.push({ type: "bc", kind: "query" });
const seq = D.mark({ name: "m" });
log.push({ type: "iframe_inserted", src_viewer: "v" });
return { seq, since: D.eventsSince({ seq }).map((e) => e.type), loads: D.loads(), collapsed: D.collapseLeft(), again: D.collapseLeft() };
""")
    assert got == {"seq": 2, "since": ["mark", "iframe_inserted"], "loads": 4, "collapsed": True, "again": True}


@needs_bun
def test_the_helpers_that_need_the_monitor_say_so_when_it_is_absent(rs, tmp_path):
    got = _run_dock_js(rs, tmp_path, "return { mark: D.mark({ name: 'x' }), since: D.eventsSince({ seq: 0 }), loads: D.loads(), neg: D.neg() };")
    assert got == {"mark": None, "since": [], "loads": None, "neg": {"dropped": 0}}
