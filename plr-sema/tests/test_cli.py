"""`python -m plr_sema check` (spec 261002 §6)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("libcst")

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parent
FIX = PKG / "eval" / "fixtures" / "regions"
CONTRACTS = PKG / "data" / "derived_contracts.json"
SNAPSHOT = PKG / "tests" / "fixtures" / "cli" / "check_json_shape.json"


def run(*args: str, env_extra: dict | None = None):
    import os

    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [sys.executable, "-m", "plr_sema", "check", *args],
        capture_output=True, text=True, cwd=REPO, env=env,
    )


def test_clean_protocol_exits_0() -> None:
    r = run(str(FIX / "straightline_clean.py"), "--contracts", str(CONTRACTS))
    assert r.returncode == 0, r.stdout + r.stderr


def test_will_fail_protocol_exits_1_and_names_the_line() -> None:
    r = run(str(FIX / "for_pickup_no_drop_raises.py"), "--contracts", str(CONTRACTS))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "will_fail" in r.stdout
    assert "for_pickup_no_drop_raises.py:" in r.stdout


def test_syntax_error_exits_2(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("def protocol(:\n")
    r = run(str(bad), "--contracts", str(CONTRACTS))
    assert r.returncode == 2 and "syntax_error" in r.stdout


def test_worst_exit_code_wins() -> None:
    r = run(str(FIX / "straightline_clean.py"), str(FIX / "for_pickup_no_drop_raises.py"),
            "--contracts", str(CONTRACTS))
    assert r.returncode == 1


def test_missing_and_non_utf8_files_exit_2(tmp_path: Path) -> None:
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"def protocol():\n    x = '\xe9'\n")
    for path in (tmp_path / "absent.py", latin):
        r = run(str(path), "--contracts", str(CONTRACTS))
        assert r.returncode == 2, r.stdout + r.stderr
        assert "Traceback" not in r.stderr


def test_contracts_resolve_from_repo_pyproject(monkeypatch) -> None:
    # No --contracts: the root pyproject's [tool.plr-sema] table (cwd = repo root).
    monkeypatch.delenv("PLR_SEMA_CONTRACTS", raising=False)
    r = run(str(FIX / "straightline_clean.py"))
    assert r.returncode == 0, r.stdout + r.stderr


def test_contracts_disabled_exits_2() -> None:
    r = run(str(FIX / "straightline_clean.py"), env_extra={"PLR_SEMA_CONTRACTS": "none"})
    assert r.returncode == 2 and "contracts_unavailable" in r.stdout


def test_function_flag_and_ambiguity(tmp_path: Path) -> None:
    two = tmp_path / "two.py"
    two.write_text("def a(): pass\n\ndef b(): pass\n")
    assert run(str(two), "--contracts", str(CONTRACTS)).returncode == 2
    assert run(str(two), "--function", "a", "--contracts", str(CONTRACTS)).returncode == 0


def _shape(obj):
    if isinstance(obj, dict):
        return {k: _shape(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_shape(obj[0])] if obj else []
    return type(obj).__name__


def test_json_output_shape_is_stable() -> None:
    r = run(str(FIX / "for_pickup_no_drop_raises.py"), "--json", "--contracts", str(CONTRACTS))
    payload = json.loads(r.stdout)
    assert payload["exit_code"] == r.returncode == 1
    assert _shape(payload) == json.loads(SNAPSHOT.read_text(encoding="utf-8"))
