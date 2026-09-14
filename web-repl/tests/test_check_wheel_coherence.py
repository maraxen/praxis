"""R6 / R8 tests for ``web-repl/scripts/check_wheel_coherence.check_untracked``.

``check_untracked(repo_root=...)`` is exercisable against a synthetic scratch
repo (its own docstring says so). These tests build scratch trees under
``tmp_path`` with ``git init`` + ``git add`` and call the function directly --
they never touch this worktree's index.

Context (backlog #5110): git pathspec ``*manifest.json`` matches a PARTIAL
basename, so ``train_manifest.json`` and Coxswain training ``manifest.json``
files (a sibling subproject in this monorepo) were failing GATE G7. R6's
intent is the browser wheel-loader seam only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import check_wheel_coherence  # noqa: E402 -- path setup must precede this import


def _init_scratch(tmp_path: Path) -> Path:
    """A throwaway git repo. Identity is local to this tree, never global."""
    scratch = tmp_path / "repo"
    scratch.mkdir()
    subprocess.run(["git", "init"], cwd=scratch, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(scratch), "config", "user.email", "scratch@example.test"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(scratch), "config", "user.name", "Scratch Test"],
        check=True,
        capture_output=True,
        text=True,
    )
    return scratch


def _track(scratch: Path, rel: str, contents: str = "{}\n") -> None:
    path = scratch / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)
    subprocess.run(
        ["git", "-C", str(scratch), "add", "--", rel],
        check=True,
        capture_output=True,
        text=True,
    )


def _manifest_problems(problems: list[str]) -> list[str]:
    return [p for p in problems if "manifest.json" in p]


def test_training_manifests_are_not_a_coherence_problem(tmp_path: Path) -> None:
    """Test 1: Coxswain training manifests must not trip R6.

    A scratch repo with ``training/out/p26/A/train_manifest.json`` (suffix
    match under the leaky ``*manifest.json`` pathspec), plus genuine
    ``training/out/manifest.json`` and ``training/golden/manifest.json``,
    and NO wheels-directory manifest, yields no manifest-related problem.
    Those files cannot shadow the browser wheel loader.
    """
    scratch = _init_scratch(tmp_path)
    _track(scratch, "training/out/p26/A/train_manifest.json")
    _track(scratch, "training/out/manifest.json")
    _track(scratch, "training/golden/manifest.json")

    problems = check_wheel_coherence.check_untracked(
        repo_root=scratch, gitignore_path=scratch / ".gitignore"
    )
    assert _manifest_problems(problems) == []


def test_tracked_wheels_manifest_is_still_a_problem(tmp_path: Path) -> None:
    """Test 2: R6 is not weakened -- a tracked wheels manifest still fails.

    ``web-repl/overlay/assets/wheels/manifest.json`` is the browser wheel
    loader's only filename seam; a stale tracked copy would shadow the
    built one. Narrowing the arm must not disable this case.
    """
    scratch = _init_scratch(tmp_path)
    _track(scratch, "web-repl/overlay/assets/wheels/manifest.json")

    problems = check_wheel_coherence.check_untracked(
        repo_root=scratch, gitignore_path=scratch / ".gitignore"
    )
    assert _manifest_problems(problems), (
        "tracked web-repl/overlay/assets/wheels/manifest.json must still "
        "be reported; R6 must not be disabled by the #5110 narrowing"
    )


def test_tracked_whl_at_nested_path_is_still_reported(tmp_path: Path) -> None:
    """Test 3: the .whl arm stays repo-wide and is otherwise untouched."""
    scratch = _init_scratch(tmp_path)
    _track(scratch, "vendor/nested/demo-0.0.0-py3-none-any.whl", "not a real wheel\n")

    problems = check_wheel_coherence.check_untracked(
        repo_root=scratch, gitignore_path=scratch / ".gitignore"
    )
    whl_problems = [p for p in problems if ".whl" in p]
    assert whl_problems, "tracked .whl at a nested path must still be reported repo-wide"
    assert "vendor/nested/demo-0.0.0-py3-none-any.whl" in whl_problems[0]


def test_root_level_manifest_json_is_not_a_coherence_problem(tmp_path: Path) -> None:
    """Test 4: a root-level ``manifest.json`` is ignored.

    (a) matches the exact basename ``manifest.json`` (so a root-level file
    is a candidate; a lone ``*/manifest.json`` pathspec would miss it).
    (b) then scopes the arm to the browser wheel output directories
    (``web-repl/overlay/assets/wheels/`` and the stale-spec sibling
    ``praxis/web-client/src/assets/wheels/``). A repo-root ``manifest.json``
    cannot shadow the built wheel-loader seam, so it is not a problem.
    """
    scratch = _init_scratch(tmp_path)
    _track(scratch, "manifest.json")

    problems = check_wheel_coherence.check_untracked(
        repo_root=scratch, gitignore_path=scratch / ".gitignore"
    )
    assert _manifest_problems(problems) == []
