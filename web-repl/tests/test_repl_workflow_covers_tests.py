"""The REPL gate must run every web-repl test file.

``.github/workflows/repl.yml`` invokes ``web-repl/tests`` one pytest process per
file, deliberately -- those tests manipulate ``sys.path``, cache modules under
synthetic names, and toggle PyLabRobot globals, so sharing an interpreter
invites order-dependent failures. The cost of that decision is a hand-maintained
list, and a hand-maintained list drifts silently: adding a test file does not
add it to CI, and nothing fails to say so.

It had already drifted. On 2026-09-14 five test files existed in the tree and
were run by no workflow at all -- test_build_manifest_coxswain,
test_check_wheel_coherence (added in PR #160 and never wired up),
test_inject_shell_coxswain, test_prune_pyodide, test_viz_highlight_staging --
39 passing tests that CI never executed. A green REPL gate did not mean what it
appeared to mean.

This test is the guard. It is cheap, it has no dependencies beyond the repo
itself, and it fails loudly the moment the two lists disagree in either
direction.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "repl.yml"
TESTS_DIR = REPO_ROOT / "web-repl" / "tests"

_INVOCATION = re.compile(r"pytest\s+web-repl/tests/([A-Za-z0-9_]+\.py)")


def _files_run_by_ci() -> set[str]:
  return set(_INVOCATION.findall(WORKFLOW.read_text()))


def _test_files_on_disk() -> set[str]:
  return {p.name for p in TESTS_DIR.glob("test_*.py")}


def test_workflow_file_exists() -> None:
  """Guard the guard: a moved workflow must not make this test vacuously pass."""
  assert WORKFLOW.is_file(), f"expected the REPL workflow at {WORKFLOW}"
  assert TESTS_DIR.is_dir(), f"expected the web-repl test directory at {TESTS_DIR}"


def test_every_test_file_is_run_by_the_repl_gate() -> None:
  """No test file may exist in the tree without CI running it."""
  missing = sorted(_test_files_on_disk() - _files_run_by_ci())
  assert missing == [], (
    "these web-repl test files are not run by .github/workflows/repl.yml, so "
    "they are never executed in CI -- add a `uv run python -m pytest "
    f"web-repl/tests/<file> -q` line for each: {missing}"
  )


def test_the_gate_does_not_reference_a_missing_test_file() -> None:
  """The converse: a renamed or deleted file must not linger in the workflow.

  pytest exits non-zero on a path that does not exist, so this would break the
  gate rather than pass silently -- but failing here names the file directly
  instead of leaving it to be read out of CI logs.
  """
  phantom = sorted(_files_run_by_ci() - _test_files_on_disk())
  assert phantom == [], (
    ".github/workflows/repl.yml runs test files that do not exist in "
    f"web-repl/tests/: {phantom}"
  )


def test_helper_modules_are_not_treated_as_tests() -> None:
  """web-repl/tests holds non-test helpers; only test_*.py is in scope.

  plr_contract.py is a helper module imported by the contract tests, not a test
  file, and must not be expected in the workflow list.
  """
  assert "plr_contract.py" not in _test_files_on_disk()
