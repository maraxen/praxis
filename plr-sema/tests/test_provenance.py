"""Spec 260901 §2.3 / AC-2.1-2.5: provenance layer verification.

Exactly the five tests named in §2.3. AC-2.2 (mechanism-not-wrapper proof),
AC-2.3 (survey_stamp() at repo root), AC-2.4 (header sha256 match, owned by
§5's drift test / T5) and AC-2.5 (ruff exclusion) are demonstrated as
one-off runs in the fixer's report, not encoded as additional permanent test
functions here -- §2.3's bullet list names exactly five tests and AC-2.1
says "all five test_provenance.py tests pass".
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from plr_sema._provenance import git_state

GIT_STATE_PATH = Path(git_state.__file__)


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, env=env)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A real git repo, one commit, clean working tree."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-q"], repo)
    _run(["git", "config", "user.email", "test@example.com"], repo)
    _run(["git", "config", "user.name", "Test"], repo)
    (repo / "tracked.txt").write_text("initial\n")
    _run(["git", "add", "-A"], repo)
    _run(["git", "commit", "-q", "-m", "initial"], repo)
    return repo


def test_git_state_is_stdlib_only() -> None:
    """Spec §2.3: every imported top-level module in git_state.py is
    stdlib. Must walk ALL AST nodes, not just the module body -- hashlib is
    imported function-locally inside _diff_sha256_fallback (git_state.py:172)
    and a module-level-only scan would wrongly report the file as not using
    it, missing exactly the case that matters."""
    tree = ast.parse(GIT_STATE_PATH.read_text(), filename=str(GIT_STATE_PATH))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in sys.stdlib_module_names:
                    offenders.append(top)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                top = node.module.split(".")[0]
                if top not in sys.stdlib_module_names:
                    offenders.append(top)
    assert offenders == [], f"non-stdlib imports found: {offenders}"


@pytest.mark.parametrize("case", ["real_repo", "non_repo", "path_scrubbed"])
def test_capture_never_raises(
    case: str, git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spec §2.3: capture_git_state never raises and degrades to the right
    provenance_source across three environments -- a real repo, a non-repo
    tmp_path, and a PATH-scrubbed env."""
    if case == "real_repo":
        state = git_state.capture_git_state(git_repo)
        assert state.provenance_source == "git"
    elif case == "non_repo":
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()
        state = git_state.capture_git_state(non_repo)
        assert state.provenance_source == "nogit"
    else:
        monkeypatch.setenv("PATH", "")
        state = git_state.capture_git_state(git_repo)
        assert state.provenance_source == "unavailable"
    assert isinstance(state, git_state.GitState)


def test_dirty_content_id_distinguishes_trees(git_repo: Path) -> None:
    """Spec §2.3: the load-bearing test. Clean -> None; two different dirty
    trees -> two different dirty_content_ids. This fails against the old
    git_dirty: bool implementation, which is the point."""
    clean = git_state.capture_git_state(git_repo)
    assert clean.dirty is False
    assert clean.dirty_content_id is None

    (git_repo / "tracked.txt").write_text("edit A\n")
    state_a = git_state.capture_git_state(git_repo)
    assert state_a.dirty is True
    assert state_a.dirty_content_id is not None

    (git_repo / "tracked.txt").write_text("edit B, not A\n")
    state_b = git_state.capture_git_state(git_repo)
    assert state_b.dirty is True
    assert state_b.dirty_content_id is not None

    assert state_a.dirty_content_id != state_b.dirty_content_id
    assert state_a.dirty_content_id != clean.dirty_content_id


def test_dirty_content_id_sees_untracked(git_repo: Path) -> None:
    """Spec §2.3: an untracked-only change must still change
    dirty_content_id -- the assertion the sha256(git diff HEAD) fallback
    cannot satisfy, which pins the throwaway-index path specifically."""
    clean = git_state.capture_git_state(git_repo)
    assert clean.dirty_content_id is None

    (git_repo / "untracked.txt").write_text("new file, never added\n")
    dirty = git_state.capture_git_state(git_repo)
    assert dirty.dirty is True
    assert dirty.dirty_content_id is not None
    assert dirty.dirty_content_id != clean.dirty_content_id


def test_git_env_stripping(
    git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spec §2.3: GIT_DIR poisoning the TEST PROCESS's environment must not
    redirect -C <path> discovery. _clean_git_env() filters the parent's
    os.environ and _run_git builds the subprocess env from that filtered
    copy -- so the poison must land in the test process's os.environ, not a
    subprocess env dict, or the mechanism under test never runs."""
    unrelated = tmp_path / "unrelated-repo"
    unrelated.mkdir()
    _run(["git", "init", "-q"], unrelated)

    monkeypatch.setenv("GIT_DIR", str(unrelated / ".git"))

    state = git_state.capture_git_state(git_repo)
    assert state.toplevel is not None
    assert Path(state.toplevel).resolve() == git_repo.resolve()
