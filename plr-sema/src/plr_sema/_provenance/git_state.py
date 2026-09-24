# --- CHERRY-PICK PROVENANCE ------------------------------------------------
# Verbatim copy of cisternal/src/cisternal/telemetry/git_state.py
#   upstream repo:   /home/marielle/projects/cisternal
#   upstream commit: bef4cea712d491d5a84ffbc5d4c3381e747c64d3
#   upstream sha256: 1ffbdfb2c019cd49f6e5663b402df85bddc28007045e0bba174e4b5c0a944823
#   picked:          2026-09-01   license: MIT (same author)
# Copied, not depended on: cisternal is requires-python >=3.13 (praxis/coxswain
# are >=3.10) and cisternal/__init__.py imports cyclopts + fastmcp==4.0.0a2.
# DO NOT EDIT. Drift is enforced by plr-sema/tests/test_fork_drift.py.
# ---------------------------------------------------------------------------
"""git_state: canonical local git provenance capture (spec 260827).

Answers exactly one question -- "what does git say about the repo in front of
me, right now?" -- as a single never-raising, off-hot-path call. This is the
shared substrate other Praxia-family tools (bathos, myxcel) delegate their
local-shellout tier to, rather than each maintaining a slightly-different
subprocess-calling implementation of the same thing.

Cross-boundary propagation (env vars, JSON sidecar files so a cluster node
with no git access to the origin repo can still see its provenance) is
deliberately NOT this module's concern -- that stays myxcel-specific, layered
on top of this primitive rather than folded into it.

Captured once per process at cisternal.init() time (see telemetry/context.py's
git_state_var), never per-event -- shelling out to git on every emit_event()
call would violate the pipeline's off-hot-path design.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

_GIT_TIMEOUT_S = 10

# GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE (etc.) override `-C <path>` repo
# discovery entirely when already set in the calling process's environment
# (e.g. this process is itself running inside a git hook) -- confirmed
# empirically upstream (myxcel._subprocess.clean_git_env). Stripped from
# every git subprocess call below so `-C <path>` reliably targets *this*
# repo, not whatever ambient repo the caller happens to be inside.
_GIT_REPO_LOCATION_ENV_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
)


def _clean_git_env() -> dict[str, str]:
    return {
        k: v for k, v in os.environ.items() if k not in _GIT_REPO_LOCATION_ENV_VARS
    }


@dataclass(frozen=True, slots=True)
class GitState:
    """Snapshot of local git provenance.

    Never partially populated: either every field reflects a real, fresh git
    query (``provenance_source="git"``), or the whole object is one of the two
    failure sentinels -- ``hash="nogit"`` (cwd isn't inside a git work tree) or
    ``hash="unknown"`` (git binary missing, or any other unexpected error).
    """

    hash: str
    branch: str
    dirty: bool
    dirty_content_id: str | None = None
    """Content-addressable id for a dirty working tree: a git tree OID
    computed against a *throwaway* index (git add -A against a temp
    GIT_INDEX_FILE, then write-tree, then discard the temp index) so it
    reflects unstaged and untracked changes too, not just what's already
    staged in the real index. None when the tree isn't dirty, or computation
    was skipped/failed."""

    provenance_source: str = "git"
    """"git" | "nogit" | "unavailable" -- mirrors myxcel's provenance_status
    enum so consumers reconciling channels (see bathos.git) can compare like
    for like."""

    toplevel: str | None = None
    """`git rev-parse --show-toplevel`. Needed by consumers (e.g. bathos) that
    reconcile this against a channel's claimed root; None on any sentinel."""


_NOGIT = GitState(hash="nogit", branch="nogit", dirty=False, provenance_source="nogit")
_UNAVAILABLE = GitState(
    hash="unknown", branch="unknown", dirty=False, provenance_source="unavailable"
)


def _run_git(
    args: list[str], cwd: Path, *, env: dict[str, str] | None = None
) -> str | None:
    """Run a git subcommand; return stripped stdout, or None on any failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
            env=env if env is not None else _clean_git_env(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _git_available_and_in_repo(cwd: Path) -> tuple[bool, bool]:
    """Return (git_binary_available, cwd_is_inside_a_work_tree)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
            env=_clean_git_env(),
        )
    except FileNotFoundError:
        return False, False
    except (OSError, subprocess.TimeoutExpired):
        return True, False
    return True, result.returncode == 0 and result.stdout.strip() == "true"


def _compute_dirty_content_id(cwd: Path) -> str | None:
    """Content-addressable id for the dirty working tree, never raises.

    Uses a throwaway index (not the repo's real one) so `git add -A` +
    `git write-tree` see the full current working-tree state -- including
    unstaged edits and untracked files -- without mutating anything the
    caller might have staged. Falls back to sha256(git diff HEAD) if the
    tree-OID path fails for any reason.
    """
    try:
        real_index_str = _run_git(["rev-parse", "--git-path", "index"], cwd)
        tmp_index: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".index") as tmp_file:
                tmp_index = Path(tmp_file.name)

            if real_index_str is not None:
                real_index = Path(real_index_str)
                if not real_index.is_absolute():
                    real_index = (cwd / real_index).resolve()
                if real_index.exists():
                    try:
                        shutil.copyfile(real_index, tmp_index)
                    except OSError:
                        pass  # fall through with an empty throwaway index

            env = _clean_git_env() | {"GIT_INDEX_FILE": str(tmp_index)}

            if _run_git(["add", "-A"], cwd, env=env) is None:
                return _diff_sha256_fallback(cwd)

            tree_oid = _run_git(["write-tree"], cwd, env=env)
            if (
                tree_oid is not None
                and len(tree_oid) == 40
                and all(c in "0123456789abcdef" for c in tree_oid)
            ):
                return tree_oid
            return _diff_sha256_fallback(cwd)
        finally:
            if tmp_index is not None:
                tmp_index.unlink(missing_ok=True)
    except Exception:
        return _diff_sha256_fallback(cwd)


def _diff_sha256_fallback(cwd: Path) -> str | None:
    import hashlib

    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "diff", "HEAD"],
            capture_output=True,
            timeout=_GIT_TIMEOUT_S,
            env=_clean_git_env(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return hashlib.sha256(result.stdout).hexdigest()


def capture_git_state(
    cwd: Path | None = None,
    *,
    compute_dirty_content_id: bool = True,
) -> GitState:
    """Capture local git provenance. Never raises.

    Args:
        cwd: Directory to query. Defaults to the current working directory.
        compute_dirty_content_id: When the tree is dirty, also compute a
            content-addressable id (several extra subprocess calls via a
            throwaway index). Set False to skip when that cost isn't worth
            it for the caller.

    Returns:
        GitState. Never None -- degrades to hash="nogit" (not a git repo) or
        hash="unknown" (git unavailable / any unexpected error).
    """
    try:
        resolved_cwd = cwd if cwd is not None else Path.cwd()

        git_available, in_repo = _git_available_and_in_repo(resolved_cwd)
        if not git_available:
            return _UNAVAILABLE
        if not in_repo:
            return _NOGIT

        git_hash = _run_git(["rev-parse", "HEAD"], resolved_cwd)
        branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], resolved_cwd)
        if git_hash is None or branch is None:
            # Inside a work tree but HEAD/branch query failed unexpectedly
            # (e.g. a repo with zero commits yet) -- report unavailable
            # rather than guessing at a partial state.
            return _UNAVAILABLE

        toplevel = _run_git(["rev-parse", "--show-toplevel"], resolved_cwd)
        status_output = _run_git(["status", "--porcelain"], resolved_cwd)
        dirty = bool(status_output)

        dirty_content_id = None
        if dirty and compute_dirty_content_id:
            dirty_content_id = _compute_dirty_content_id(resolved_cwd)

        return GitState(
            hash=git_hash,
            branch=branch,
            dirty=dirty,
            dirty_content_id=dirty_content_id,
            provenance_source="git",
            toplevel=toplevel,
        )
    except Exception:
        # Never raise -- any unexpected failure degrades to the safe sentinel.
        return _UNAVAILABLE
