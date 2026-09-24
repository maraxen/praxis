"""Cluster wiring that the P2.6 jobs got wrong (lesson 469): the bathos
catalog env must reach `bth run`, and the manifest's git block must say when
provenance is unavailable instead of going silently blank."""

import os
import subprocess
from pathlib import Path

import pytest

from praxis_training.finetune.train import _git_state

REPO = Path(__file__).resolve().parents[2]
WRAPPER = REPO / "scripts" / "slurm" / "bth_run.sh"


def test_bth_run_wrapper_exports_catalog_dir():
    env = {k: v for k, v in os.environ.items() if not k.startswith("BTH_")}
    env["PATH"] = os.environ["PATH"]
    out = subprocess.run(["bash", str(WRAPPER), "env"], capture_output=True, text=True,
                         check=True, env=env).stdout
    exported = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    # The values are the remote's absolute paths (only correct on Engaging);
    # the wrapper's job is to make them reach the exec'd command at all.
    assert exported["BTH_PROJECT_SLUG"] == "praxis"
    assert exported["BTH_CATALOG_DIR"].endswith("/.bth/catalog")
    assert exported["BTH_CATALOG_DIR"].startswith(exported["BTH_PROJECT_ROOT"])
    assert "PRAXIS_GIT_SHA" in exported


def test_bth_run_wrapper_forwards_git_override_and_execs_argv():
    env = dict(os.environ, PRAXIS_GIT_SHA="abc123")
    out = subprocess.run(["bash", str(WRAPPER), "sh", "-c", 'echo "$PRAXIS_GIT_SHA:$1"', "_", "arg with space"],
                         capture_output=True, text=True, check=True, env=env).stdout.strip()
    assert out == "abc123:arg with space"


def test_bth_run_wrapper_refuses_empty_command():
    res = subprocess.run(["bash", str(WRAPPER)], capture_output=True, text=True)
    assert res.returncode == 64 and "no command" in res.stderr


def test_bth_run_wrapper_is_syntactically_valid_and_executable():
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)
    assert os.access(WRAPPER, os.X_OK)


def test_git_state_in_repo_reports_git_source():
    g = _git_state(REPO)
    assert g["available"] is True and g["source"] == "git"
    assert len(g["sha"]) == 40


def test_git_state_reports_unavailable_outside_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("PRAXIS_GIT_SHA", raising=False)
    monkeypatch.delenv("PRAXIS_GIT_BRANCH", raising=False)
    g = _git_state(tmp_path)
    assert g["available"] is False and g["sha"] == "" and g["source"] == "none"
    assert "PRAXIS_GIT_SHA" in g["note"]


def test_git_state_honours_submitter_override_outside_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_GIT_SHA", "deadbeef" * 5)
    monkeypatch.setenv("PRAXIS_GIT_BRANCH", "coxswain-p2-pipeline")
    g = _git_state(tmp_path)
    assert g == {
        "sha": "deadbeef" * 5, "branch": "coxswain-p2-pipeline", "dirty": None,
        "available": True, "source": "env:PRAXIS_GIT_SHA",
        "note": g["note"],
    }
    assert "rsync mirror" in g["note"]
