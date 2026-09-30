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


def passing_fields(unit: Any) -> dict[str, Any]:
    return dict(unit.expected)


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
        table=rs.UNIT_TABLE, out_dir=out_dir,
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


def test_unit_table_is_d16_for_sprint_a(rs):
    assert [u.id for u in rs.UNIT_TABLE] == ["D1", "D1-dark"]
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


@pytest.mark.parametrize("unit_id", ["D1", "D1-dark"])
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
    assert runner.ids() == ["D1", "D1-dark"], "table order, exactly one process per unit"
    assert [t for _, t, _ in runner.calls] == [6 * 60 + 60, 5 * 60 + 60]
    assert all(c == "/repo" for _, _, c in runner.calls)
    assert len(runner.calls) == len(rs.UNIT_TABLE), "no whole-run call"


def test_aggregate_shape_and_d1_dark_subobject(rs, ur, wds, tmp_path):
    env = make_env(rs)
    agg, code = drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    assert code == 0
    for key in ("scenarios", "reused", "recomputed", "timed_out", "missing", "stale"):
        assert key in agg, key
    assert agg["recomputed"] == ["D1", "D1-dark"] and agg["reused"] == []
    assert agg["timed_out"] == [] and agg["missing"] == [] and agg["stale"] == []
    assert set(agg["scenarios"]) == {"D1", "D1-dark"}
    assert agg["d1_dark"] == agg["scenarios"]["D1-dark"] and "rail_colors_match_dark" in agg["d1_dark"]
    written = json.loads((tmp_path / "result.json").read_text())
    assert written["passed"] is True and written["recomputed"] == ["D1", "D1-dark"]


def test_resume_reuses_verified_units_and_records_source_and_hashes(rs, ur, wds, tmp_path):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    spy = SpyRunner()
    agg, code = drive(rs, tmp_path, env, spy)
    assert code == 0 and spy.calls == [] and agg["recomputed"] == []
    assert [r["id"] for r in agg["reused"]] == ["D1", "D1-dark"]
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
    assert code == 0 and runner.ids() == ["D1", "D1-dark"]
    assert agg["reused"] == [] and agg["recomputed"] == ["D1", "D1-dark"]


@pytest.mark.parametrize("field", ["dist", "notebook", "harness", "runner", "chrome", "driver"])
def test_a_changed_input_recomputes_the_unit(rs, ur, wds, tmp_path, field):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    env2 = make_env(rs, **{field: "0" * 64})
    runner = InProcessRunner(rs, ur, wds, tmp_path, env2)
    agg, code = drive(rs, tmp_path, env2, runner)
    assert code == 0 and runner.ids() == ["D1", "D1-dark"] and agg["reused"] == []


def test_a_changed_base_path_recomputes_via_the_args_input(rs, ur, wds, tmp_path):
    env = make_env(rs)
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    env2 = make_env(rs, base_path="/")
    runner = InProcessRunner(rs, ur, wds, tmp_path, env2)
    drive(rs, tmp_path, env2, runner)
    assert runner.ids() == ["D1", "D1-dark"]


def test_playwright_version_and_lockfile_changes_recompute_every_unit(rs, ur, wds, tmp_path):
    base = make_env(rs, driver=ur.driver_input(playwright_version="1.62.0", uv_lock_bytes=b"a"))
    drive(rs, tmp_path, base, InProcessRunner(rs, ur, wds, tmp_path, base))
    for pv, lock in (("1.63.0", b"a"), ("1.62.0", b"b")):
        env2 = make_env(rs, driver=ur.driver_input(playwright_version=pv, uv_lock_bytes=lock))
        runner = InProcessRunner(rs, ur, wds, tmp_path, env2)
        agg, _ = drive(rs, tmp_path, env2, runner)
        assert runner.ids() == ["D1", "D1-dark"], (pv, lock)
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
    assert runner.ids() == ["D1"] and [r["id"] for r in agg["reused"]] == ["D1-dark"] and code == 0


def test_a_failing_key_is_recorded_and_never_reused(rs, ur, wds, tmp_path):
    env = make_env(rs)
    bad = dict(passing_fields(rs.UNIT_BY_ID["D1"]), rail_state_after_run="not-run")
    agg, code = drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env, fields={"D1": bad}))
    assert code == 1 and agg["passed"] is False
    assert [f["id"] for f in agg["failed"]] == ["D1"] and agg["failed"][0]["failing_keys"] == ["rail_state_after_run"]
    # a flaky failure is always retried
    runner = InProcessRunner(rs, ur, wds, tmp_path, env)
    agg2, code2 = drive(rs, tmp_path, env, runner)
    assert runner.ids() == ["D1"] and code2 == 0 and [r["id"] for r in agg2["reused"]] == ["D1-dark"]


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
    assert code == 1 and agg["missing"] == ["D1"] and agg["recomputed"] == ["D1-dark"]
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
    assert code == 1 and agg["timed_out"] == ["D1"] and agg["missing"] == ["D1-dark"]


def test_run_unit_timeout_over_a_valid_stamp_defers_to_the_stamp_and_warns(rs, ur, wds, tmp_path, caplog):
    env = make_env(rs)
    runner = InProcessRunner(rs, ur, wds, tmp_path, env, timed_out={"D1"})
    with caplog.at_level(logging.WARNING):
        agg, code = drive(rs, tmp_path, env, runner)
    assert code == 0 and agg["timed_out"] == [] and agg["recomputed"] == ["D1", "D1-dark"]
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
    assert [r["id"] for r in agg["reused"]] == ["D1", "D1-dark"] and agg["recomputed"] == []


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
    assert [(s["id"], s["mismatched"]) for s in agg["stale"]] == [("D1", ["dist"]), ("D1-dark", ["dist"])]
    after = snapshot_files(tmp_path)
    for name, data in before.items():
        if name != "result.json":
            assert after[name] == data, f"{name} must be byte-identical after --aggregate-only"


def test_aggregate_only_with_a_different_base_path_makes_every_unit_stale_on_args(rs, ur, wds, tmp_path):
    env = make_env(rs, base_path="/praxis/")
    drive(rs, tmp_path, env, InProcessRunner(rs, ur, wds, tmp_path, env))
    agg, code = drive(rs, tmp_path, make_env(rs, base_path="/"), SpyRunner(), aggregate_only=True)
    assert code == 1 and [(s["id"], s["mismatched"]) for s in agg["stale"]] == [("D1", ["args"]), ("D1-dark", ["args"])]
    same, code_same = drive(rs, tmp_path, make_env(rs, base_path="/praxis/"), SpyRunner(), aggregate_only=True)
    assert code_same == 0 and len(same["reused"]) == 2


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
        assert "--chrome-path" in argv and timeout in (420, 360)


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
    assert runner.ids() == ["D1"] and [r["id"] for r in agg["reused"]] == ["D1-dark"]


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
