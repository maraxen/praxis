"""AC-42 / AC-40: the CI step design of D16 for the display units (A7).

Epic 260929_notebook-display-design, D16 "CI policy: no reuse across workflow runs" and
AC-42's workflow test. ``.github/workflows/repl.yml`` is parsed (PyYAML) and checked for:

* one step per unit (``--display-check --scenario <id> --base-path /praxis/``) with a
  step-level ``timeout-minutes`` equal to the D16 budget + 2 and ``if: ${{ !cancelled() }}``;
* one ``--aggregate-only`` step per check whose hashed arguments (``--base-path``, and
  ``--serve-dir`` / ``--out-dir`` when present) equal those of every scenario step of that check
  (C8-4: without ``--base-path /praxis/`` every stamp's ``args`` hash mismatches and the gate is
  permanently red), with ``if: ${{ !cancelled() }}``;
* an ``if: always()`` step running ``scripts/unit_runner.py --reap`` without ``--force``
  (C8-1, C9-2), step ``timeout-minutes: 1``;
* an ``actions/upload-artifact`` step with ``if: always()`` covering the out dir, and NO
  ``actions/download-artifact`` step (CI never reuses across workflow runs);
* the job-level ``timeout-minutes`` backstop: at least 45 plus the sum of the scenario step
  timeouts (60 after sprint A);
* both ``paths:`` filters (``push`` and ``pull_request``) listing ``scripts/repl_smoke.py``,
  ``scripts/unit_runner.py``, ``scripts/spikes/**`` and ``scripts/negatives/**`` (C11-11).

The D16 budgets are written out here, not imported from ``repl_smoke.py``: a change to the
unit table must not silently move the CI step timeouts (the unit-table test in
``test_repl_smoke_resume.py`` pins the table to the same numbers).

Sprint B (B10) and sprint C (C7) extend ``BUDGET_MIN`` and ``CHECKS`` with their units.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "repl.yml"

#: D16 unit budgets in minutes, sprint A. CI step timeout = budget + 2.
BUDGET_MIN = {"D1": 6, "D1-dark": 5}
#: check flag -> ordered unit ids that belong to it
CHECKS = {"--display-check": ["D1", "D1-dark"]}
OUT_DIRS = {"--display-check": "outputs/repl_smoke/display-check"}
HASHED_ARGS = ("--base-path", "--serve-dir", "--out-dir", "--neg")
REQUIRED_PATHS = (
    "scripts/repl_smoke.py",
    "scripts/unit_runner.py",
    "scripts/spikes/**",
    "scripts/negatives/**",
)


@pytest.fixture(scope="module")
def wf() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW.read_text())


@pytest.fixture(scope="module")
def steps(wf) -> list[dict[str, Any]]:
    return wf["jobs"]["repl"]["steps"]


def _command_lines(step: dict[str, Any]) -> list[str]:
    """The ``run`` text of a step, joined over backslash continuations, one command per line."""
    text = re.sub(r"\\\n\s*", " ", step.get("run", ""))
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def _smoke_args(step: dict[str, Any]) -> list[str] | None:
    """The argv after ``scripts/repl_smoke.py`` in a step, or None."""
    for line in _command_lines(step):
        tokens = shlex.split(line)
        for i, tok in enumerate(tokens):
            if tok.endswith("scripts/repl_smoke.py"):
                return tokens[i + 1 :]
    return None


def _flag_value(argv: list[str], flag: str) -> str | None:
    return argv[argv.index(flag) + 1] if flag in argv else None


def _scenario_steps(steps: list[dict[str, Any]], check: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for step in steps:
        argv = _smoke_args(step)
        if argv and check in argv and "--scenario" in argv:
            uid = _flag_value(argv, "--scenario")
            assert uid not in out, f"two steps run {check} --scenario {uid}"
            out[uid] = step
    return out


def _aggregate_steps(steps: list[dict[str, Any]], check: str) -> list[dict[str, Any]]:
    found = []
    for step in steps:
        argv = _smoke_args(step)
        if argv and check in argv and "--aggregate-only" in argv:
            found.append(step)
    return found


def _hashed(argv: list[str]) -> dict[str, str | None]:
    return {flag: _flag_value(argv, flag) for flag in HASHED_ARGS}


def _index(steps: list[dict[str, Any]], step: dict[str, Any]) -> int:
    return next(i for i, s in enumerate(steps) if s is step)


def _by_name(steps: list[dict[str, Any]], name: str) -> dict[str, Any]:
    matches = [s for s in steps if s.get("name") == name]
    assert len(matches) == 1, f"expected exactly one step named {name!r}, found {len(matches)}"
    return matches[0]


# --------------------------------------------------------------------------- #
# One step per unit
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_one_step_per_unit_with_the_d16_scenario_command(steps, check):
    found = _scenario_steps(steps, check)
    assert sorted(found) == sorted(CHECKS[check]), "exactly one scenario step per unit of the current sprints"
    for uid, step in found.items():
        argv = _smoke_args(step)
        assert argv == [check, "--scenario", uid, "--base-path", "/praxis/"], (uid, argv)
        assert any(line.startswith("uv run python scripts/repl_smoke.py") for line in _command_lines(step))


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_step_timeout_is_the_budget_plus_two_minutes(steps, check):
    assert len(_scenario_steps(steps, check)) == len(CHECKS[check]), "vacuity guard: the steps exist"
    for uid, step in _scenario_steps(steps, check).items():
        assert step["timeout-minutes"] == BUDGET_MIN[uid] + 2, uid
    if check == "--display-check":
        assert {u: BUDGET_MIN[u] + 2 for u in CHECKS[check]} == {"D1": 8, "D1-dark": 7}


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_scenario_steps_do_not_hide_each_other(steps, check):
    assert len(_scenario_steps(steps, check)) == len(CHECKS[check]), "vacuity guard: the steps exist"
    for uid, step in _scenario_steps(steps, check).items():
        assert step.get("if") == "${{ !cancelled() }}", f"{uid}: one failing unit must not hide the others"


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_scenario_steps_run_in_table_order_after_execute_welcome(steps, check):
    order = [_index(steps, s) for s in (_scenario_steps(steps, check)[u] for u in CHECKS[check])]
    assert order == sorted(order), "units run in the D16 table order"
    welcome = _index(steps, _by_name(steps, "Execute welcome.ipynb"))
    assert min(order) > welcome, "the new steps come after 'Execute welcome.ipynb'"
    tests_step = _index(steps, _by_name(steps, "Tests"))
    assert max(order) < tests_step


# --------------------------------------------------------------------------- #
# The aggregate step: the one whose exit gates the PR
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_one_aggregate_step_per_check_after_its_scenario_steps(steps, check):
    aggs = _aggregate_steps(steps, check)
    assert len(aggs) == 1, f"exactly one {check} --aggregate-only step"
    agg = aggs[0]
    assert agg.get("if") == "${{ !cancelled() }}"
    assert "--scenario" not in _smoke_args(agg)
    assert any(line.startswith("uv run python scripts/repl_smoke.py") for line in _command_lines(agg))
    last_scenario = max(_index(steps, s) for s in _scenario_steps(steps, check).values())
    assert _index(steps, agg) > last_scenario, "the aggregate reads the stamps the scenario steps just wrote"


@pytest.mark.parametrize("check", sorted(CHECKS))
def test_aggregate_hashed_arguments_equal_the_scenario_steps(steps, check):
    """C8-4: --base-path (and --serve-dir/--out-dir when present) identical, or every stamp is stale."""
    agg_args = _hashed(_smoke_args(_aggregate_steps(steps, check)[0]))
    assert agg_args["--base-path"] == "/praxis/", "without it every stamp's args hash mismatches"
    for uid, step in _scenario_steps(steps, check).items():
        assert _hashed(_smoke_args(step)) == agg_args, uid


# --------------------------------------------------------------------------- #
# Reap and upload; no download
# --------------------------------------------------------------------------- #


def _reap_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in steps if any("scripts/unit_runner.py" in line and "--reap" in line for line in _command_lines(s))]


def test_reap_step_is_always_bounded_and_never_forced(steps):
    reaps = _reap_steps(steps)
    assert len(reaps) == 1
    reap = reaps[0]
    assert reap.get("if") == "always()"
    assert reap["timeout-minutes"] == 1
    lines = [ln for ln in _command_lines(reap) if "--reap" in ln]
    assert lines and all("--force" not in ln for ln in lines), "Actions sets CI=true; --force would defeat the guard"
    assert any(ln.startswith("uv run python scripts/unit_runner.py --reap") for ln in lines)


def test_reap_step_runs_after_every_unit_and_aggregate_step(steps):
    reap = _index(steps, _reap_steps(steps)[0])
    for check in CHECKS:
        assert reap > max(_index(steps, s) for s in _scenario_steps(steps, check).values())
        assert reap > _index(steps, _aggregate_steps(steps, check)[0])


def test_upload_step_is_always_and_covers_the_out_dirs(steps):
    uploads = [
        s for s in steps
        if str(s.get("uses", "")).startswith("actions/upload-artifact")
        and s.get("if") == "always()"
        and "outputs/repl_smoke" in str(s.get("with", {}).get("path", ""))
    ]
    assert len(uploads) == 1, "one if: always() upload of the harness out dirs"
    paths = str(uploads[0]["with"]["path"])
    for check in CHECKS:
        assert OUT_DIRS[check] in paths


def test_no_step_downloads_an_earlier_runs_artifacts(wf):
    for job_name, job in wf["jobs"].items():
        for step in job.get("steps", []):
            assert "download-artifact" not in str(step.get("uses", "")), (
                f"{job_name}: CI never reuses across workflow runs (D16); a green gate is evidence from this head"
            )


# --------------------------------------------------------------------------- #
# The job-level backstop and the paths filters
# --------------------------------------------------------------------------- #


def test_job_timeout_is_only_a_backstop_over_the_sum_of_the_step_timeouts(wf, steps):
    total = sum(
        s["timeout-minutes"] for check in CHECKS for s in _scenario_steps(steps, check).values()
    )
    limit = wf["jobs"]["repl"]["timeout-minutes"]
    assert total > 0, "vacuity guard: scenario steps exist"
    assert limit >= 45 + total, "the job timeout must never be the limit that ends a unit"
    for check in CHECKS:  # never turned into a whole-run timeout: every unit step is bounded well below it
        assert all(s["timeout-minutes"] < limit for s in _scenario_steps(steps, check).values())


def test_job_backstop_is_60_after_sprint_a(wf):
    """D16: 60 after sprint A, 92 after sprint B, 137 after sprint C (B10 and C7 update this)."""
    assert wf["jobs"]["repl"]["timeout-minutes"] == 60


def test_the_coxswain_job_keeps_its_own_timeout(wf):
    assert wf["jobs"]["coxswain"]["timeout-minutes"] == 45


@pytest.mark.parametrize("trigger", ["push", "pull_request"])
def test_both_paths_filters_list_the_harness_spike_and_negative_scripts(wf, trigger):
    on = wf.get("on", wf.get(True))
    paths = on[trigger]["paths"]
    for required in REQUIRED_PATHS:
        assert required in paths, f"{trigger}.paths lacks {required!r} (C11-11)"
    assert on["push"]["paths"] == on["pull_request"]["paths"], "the two lists are kept identical"


# --------------------------------------------------------------------------- #
# AC-40 wiring and the two new test files
# --------------------------------------------------------------------------- #


def test_display_check_and_display_js_harness_are_wired(wf):
    text = WORKFLOW.read_text()
    assert text.count("--display-check") >= 1  # AC-40, sprint A
    assert text.count("bun test web-repl/shell/display") >= 1  # AC-40, sprint A


@pytest.mark.parametrize(
    "name", ["test_repl_smoke_resume.py", "test_repl_workflow_scenarios.py", "test_nd_sensitivity_driver.py"]
)
def test_new_test_files_are_wired_in_the_tests_step(steps, name):
    tests = "\n".join(_command_lines(_by_name(steps, "Tests")))
    assert f"uv run python -m pytest web-repl/tests/{name} -q" in tests
