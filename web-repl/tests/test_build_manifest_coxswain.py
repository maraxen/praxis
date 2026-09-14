"""build_manifest.py --with-coxswain: the manifest's 'coxswain_assets' key
exists ONLY under the flag, carries sha256 per staged browser asset, and is
verified by verify_manifest. A default manifest stays byte-identical to its
pre-coxswain shape for identical inputs (FR-12/AC-11/RISK-14).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import build_manifest  # noqa: E402 -- path setup must precede this import


def _make_overlay_root(tmp_path: Path) -> tuple[Path, Path]:
    """Scratch web-repl root with a minimal overlay tree (wheels dir must
    exist with one *.whl or build_manifest raises before the flag matters)."""
    web_repl = tmp_path / "web-repl"
    wheels = web_repl / "overlay" / "assets" / "wheels"
    wheels.mkdir(parents=True)
    (wheels / "pkg-1.0.0-py3-none-any.whl").write_bytes(b"not a wheel")
    shims = web_repl / "overlay" / "assets" / "shims"
    shims.mkdir(parents=True)
    (shims / "web_serial_shim.py").write_text("# shim\n")
    return web_repl, web_repl / "overlay"


def test_without_flag_the_manifest_has_no_coxswain_key(tmp_path: Path) -> None:
    web_repl, _ = _make_overlay_root(tmp_path)
    manifest = build_manifest.build_manifest(
        web_repl_root=web_repl, repo_root=tmp_path, dev=True
    )
    assert "coxswain_assets" not in manifest
    assert set(manifest) == {"praxis_git_sha", "wheels", "sources"}


def test_with_flag_tracks_coxswain_assets_with_sha256(tmp_path: Path) -> None:
    web_repl, overlay = _make_overlay_root(tmp_path)
    cx_dir = overlay / "assets" / "coxswain"
    cx_dir.mkdir()
    (cx_dir / "coxswain.css").write_text(".cx-panel { color: #111 }\n")
    manifest = build_manifest.build_manifest(
        web_repl_root=web_repl, repo_root=tmp_path, dev=True, with_coxswain=True
    )
    entries = manifest["coxswain_assets"]
    paths = [e["path"] for e in entries]
    assert paths == ["assets/coxswain/coxswain.css"]
    assert all(len(e["sha256"]) == 64 for e in entries)


def test_with_flag_without_assets_fails_loud(tmp_path: Path) -> None:
    web_repl, _ = _make_overlay_root(tmp_path)
    with pytest.raises(build_manifest.ManifestError, match="does not exist"):
        build_manifest.build_manifest(
            web_repl_root=web_repl, repo_root=tmp_path, dev=True, with_coxswain=True
        )


def test_verify_manifest_checks_coxswain_entries(tmp_path: Path) -> None:
    web_repl, overlay = _make_overlay_root(tmp_path)
    cx_dir = overlay / "assets" / "coxswain"
    cx_dir.mkdir()
    (cx_dir / "a.js").write_text("// a\n")
    manifest = build_manifest.build_manifest(
        web_repl_root=web_repl, repo_root=tmp_path, dev=True, with_coxswain=True
    )
    assert build_manifest.verify_manifest(manifest, web_repl_root=web_repl) == []

    # Drift the file after generation -> verification must name it.
    (cx_dir / "a.js").write_text("// a, mutated\n")
    problems = build_manifest.verify_manifest(manifest, web_repl_root=web_repl)
    assert any("coxswain asset sha256 mismatch" in p for p in problems)


def test_default_and_flagged_manifests_differ_only_in_coxswain_entries(tmp_path: Path) -> None:
    web_repl, overlay = _make_overlay_root(tmp_path)
    cx_dir = overlay / "assets" / "coxswain"
    cx_dir.mkdir()
    (cx_dir / "b.css").write_text("/* b */\n")
    plain = build_manifest.build_manifest(
        web_repl_root=web_repl, repo_root=tmp_path, dev=True
    )
    flagged = build_manifest.build_manifest(
        web_repl_root=web_repl, repo_root=tmp_path, dev=True, with_coxswain=True
    )
    assert "coxswain_assets" not in plain  # default shape untouched
    shared = {k: v for k, v in flagged.items() if k != "coxswain_assets"}
    assert json.dumps(plain, sort_keys=True) == json.dumps(shared, sort_keys=True)
